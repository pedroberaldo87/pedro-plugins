#!/usr/bin/env bash
# post-plugin-command.sh — PostToolUse hook entrypoint.
#
# Fires after every Bash tool use. If the command was a `claude plugin *`
# mutation (install/uninstall/enable/disable/marketplace add/remove), runs
# snapshot + commit + push immediately — propagates the change without waiting
# for the next SessionStart.
#
# Receives JSON on stdin with the tool invocation details. We only care about
# the `tool_input.command` field.
#
# Only active when the source repo exists. Never throttled.
#
# Exit codes:
#   0 — always (never blocks the Bash tool result)

set -uo pipefail

# Re-entrancy guard: if we're already inside a hook execution (session-sync
# calling apply which runs claude plugin subcommands, or nested PostToolUse),
# exit silently. Prevents recursive execution.
if [ -n "${PEDRO_PLUGINS_HOOK_RUNNING:-}" ]; then
  exit 0
fi
export PEDRO_PLUGINS_HOOK_RUNNING=post-plugin-command

PEDRO_PLUGINS_REPO="${PEDRO_PLUGINS_REPO:-$HOME/pedro-plugins}"

# Locate lib dir
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/hooks/lib" ]; then
  LIB_DIR="$CLAUDE_PLUGIN_ROOT/hooks/lib"
else
  LIB_DIR="$(cd "$(dirname "$0")" && pwd)/lib"
fi

SNAPSHOT_SH="$LIB_DIR/snapshot.sh"
GIT_SYNC_SH="$LIB_DIR/git-sync.sh"

log() { echo "[pedro-plugins/post-tool] $*" >&2; }

# ⚠️ O exit por repo-fonte ausente NÃO vem mais aqui. Ele matava também o aviso de
# cache parado — e o cache incha em QUALQUER máquina, tenha ela o repositório de
# origem ou não. O exit desceu para logo antes do snapshot, que é o único trecho
# que realmente precisa do repositório.

# Read stdin (hook event JSON)
PAYLOAD="$(cat 2>/dev/null || echo "")"
[ -z "$PAYLOAD" ] && exit 0

# Extract command. Claude Code hook payload has tool_input.command for Bash tool.
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o hook não lê o comando — e aí AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "post-plugin-command"; exit 0; }
COMMAND="$(hj_campo "$PAYLOAD" tool_input.command)"
[ -z "$COMMAND" ] && exit 0

# ── O LIXO QUE A INSTALAÇÃO ACABOU DE DEIXAR ──────────────────────────────────
# ANTES dos exits abaixo, e com regex PRÓPRIO, por dois motivos medidos:
#
#   1. `update` não está no match do snapshot — e é justamente ele que mais incha o
#      cache, porque não muda o manifest (só o número da versão).
#   2. o snapshot sai cedo quando o manifest não mudou, e o cache incha do mesmo jeito.
#
# Ele AVISA e OFERECE; nunca apaga. Apagar arquivo não tem volta, e a lista tem que ser
# vista antes. Desligar: PEDRO_CACHE_AVISO=0.
if [ "${PEDRO_CACHE_AVISO:-1}" != "0" ] \
   && echo "$COMMAND" | grep -qE 'claude[[:space:]]+plugin[s]?[[:space:]]+(install|i|update|upgrade|uninstall|remove)' \
   && [ -f "$LIB_DIR/cache-parado.sh" ]; then
  # shellcheck source=/dev/null
  . "$LIB_DIR/cache-parado.sh" 2>/dev/null
  if type cp_total >/dev/null 2>&1; then
    PARADAS="$(cp_total 2>/dev/null || echo 0)"
    if [ "${PARADAS:-0}" -gt 0 ] 2>/dev/null; then
      TOPO="$(cp_parados 2>/dev/null | sort -k3 -rn | head -3 \
              | awk '{printf "%s roda %s (%s paradas) · ", $1, $2, $3}')"
      MSG="🧹 ${PARADAS} versão(ões) de plugin paradas no cache — só a mais alta roda. ${TOPO}Peça \"limpa o cache\" e eu apago tudo que não é a mais alta, mostrando a lista antes."
      if command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
        python3 -c 'import json,sys; print(json.dumps({"systemMessage": sys.argv[1]}))' "$MSG"
      fi
    fi
  fi
fi

# Daqui para baixo é o sync do manifest, e ele SÓ faz sentido com o repositório de
# origem no disco. O aviso de cache acima não depende dele.
if [ ! -d "$PEDRO_PLUGINS_REPO/.git" ]; then
  exit 0
fi

# Match `claude plugin (install|uninstall|enable|disable|marketplace (add|remove|rm))`
if ! echo "$COMMAND" | grep -qE 'claude[[:space:]]+plugin[s]?[[:space:]]+(install|i|uninstall|remove|enable|disable|marketplace[[:space:]]+(add|remove|rm))'; then
  exit 0
fi

# Also skip if the command was about pedro-plugins itself (self-sync loop)
if echo "$COMMAND" | grep -q 'pedro-plugins'; then
  exit 0
fi

# Run snapshot
if [ ! -x "$SNAPSHOT_SH" ]; then
  log "⚠ snapshot.sh não encontrado em $SNAPSHOT_SH"
  exit 0
fi

# Capture stdout only — snapshot.sh prints "changed"/"unchanged" on stdout,
# log messages on stderr. Merging them (2>&1) would create ordering ambiguity
# because `tail -1` might grab a log line instead of the status.
SNAPSHOT_STATUS="$(bash "$SNAPSHOT_SH" 2>/dev/null)"

if [ "$SNAPSHOT_STATUS" != "changed" ]; then
  # Manifest didn't actually change (maybe the command was a no-op)
  exit 0
fi

# Extract a short description of what happened for the commit message.
# Note: the regex uses [a-z]+ which clips plugin names with digits (context7 → context).
# Minor cosmetic issue in commit messages only — semantic state is correct.
ACTION="$(echo "$COMMAND" | grep -oE 'claude[[:space:]]+plugin[s]?[[:space:]]+[a-z]+([[:space:]]+[a-z0-9_-]+)?' | head -1)"
[ -z "$ACTION" ] && ACTION="plugin change"

# Commit + push via git-sync
if [ -x "$GIT_SYNC_SH" ]; then
  bash "$GIT_SYNC_SH" "chore(plugins): $ACTION"
fi

exit 0
