#!/usr/bin/env bash
# apply-config.sh — applies the versioned global config (config/settings-defaults.json
# + config/CLAUDE-global.md) onto THIS machine's ~/.claude. Idempotent, backs up,
# and NEVER touches settings.local.json (which may hold secrets).
#
# This is the "config layer" the old bootstrap-third-party never had. The plugin
# auto-syncs marketplaces+plugins via hooks; THIS is run on demand (once per new
# machine) by /bootstrap:setup.
#
# Merge policy (merge, not blind overwrite):
#   env                     → defaults win (ensures AGENT_TEAMS=1, CONTEXT_THRESHOLD, etc.)
#   permissions.allow/deny  → UNION (machine keeps its own + gains the defaults)
#   permissions.defaultMode → keep local, else default
#   language/theme/autoCompactEnabled/outputStyle → defaults win
#   statusLine              → resolved to the context-guard writer on THIS machine (runtime glob)
#   enabledPlugins / extraKnownMarketplaces / hooks → UNTOUCHED (owned by plugin sync)
#   settings.local.json     → NEVER touched
#
# Exit: 0 ok, 1 error.

set -uo pipefail

# O PYTHON, NAO O JQ. O jq nao vem no Windows nem no macOS de fabrica, e era
# aqui que a instalacao morria: sem ele este script saia 1 e a maquina ficava
# sem config nenhuma. O Python ja e dependencia dura de todo o resto, e o
# `lib/cfgjson.py` faz as mesmas contas (com teste que compara com o jq).
# O resolvedor testa EXECUCAO, nao presenca: no Windows existe um `python3` de
# mentira, da loja da Microsoft, que responde uma propaganda em vez de rodar.
PY=""
for _c in python3 python; do
  _p="$(command -v "$_c" 2>/dev/null)" || _p=""
  [ -n "$_p" ] && "$_p" --version >/dev/null 2>&1 && { PY="$_p"; break; }
done
[ -z "$PY" ] && { echo "[bootstrap/config] python3 required — install it first"; exit 1; }
CFGJSON="$(cd "$(dirname "$0")/../../lib" 2>/dev/null && pwd)/cfgjson.py"
[ -f "$CFGJSON" ] || { echo "[bootstrap/config] lib/cfgjson.py nao encontrado"; exit 1; }

# Locate the plugin's config dir
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/config" ]; then
  CFG_DIR="$CLAUDE_PLUGIN_ROOT/config"
else
  CFG_DIR="$(cd "$(dirname "$0")/../../config" 2>/dev/null && pwd)"
fi
DEFAULTS="$CFG_DIR/settings-defaults.json"
CLAUDE_SRC="$CFG_DIR/CLAUDE-global.md"

# CLAUDE_CONFIG_DIR e a MESMA regra usada nas linhas do statusLine abaixo e no
# lib/conformance.py. Com $HOME fixo aqui, quem seta a variavel via o script
# escrever na config real enquanto acha que esta mexendo noutra — medido em
# 2026-07-30 num smoke de instalacao limpa: a pasta alvo ficou vazia e o
# ~/.claude de verdade foi sobrescrito.
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS="$CLAUDE_DIR/settings.json"
mkdir -p "$CLAUDE_DIR"

[ -f "$DEFAULTS" ] || { echo "[bootstrap/config] settings-defaults.json não encontrado em $CFG_DIR"; exit 1; }
"$PY" "$CFGJSON" valida "$DEFAULTS" 2>/dev/null || { echo "[bootstrap/config] settings-defaults.json inválido"; exit 1; }

# --- 1. Merge settings-defaults into settings.json ---
CURRENT="{}"
if [ -f "$SETTINGS" ]; then
  "$PY" "$CFGJSON" valida "$SETTINGS" 2>/dev/null || { echo "[bootstrap/config] settings.json local inválido — abortando (não sobrescrevo)"; exit 1; }
  CURRENT="$(cat "$SETTINGS")"
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
fi

printf '%s' "$CURRENT" > "$SETTINGS.cur" \
  && "$PY" "$CFGJSON" merge-settings "$SETTINGS.cur" "$DEFAULTS" > "$SETTINGS.tmp" \
  && mv "$SETTINGS.tmp" "$SETTINGS" \
  && rm -f "$SETTINGS.cur" \
  || { rm -f "$SETTINGS.tmp" "$SETTINGS.cur"; echo "[bootstrap/config] merge falhou — settings.json intacto"; exit 1; }
echo "[bootstrap/config] ✓ settings.json: env + permissions (union) + flags aplicados"

# --- 2. Resolve statusLine to the context-guard writer on THIS machine ---
# nullglob loop (not `ls -d $glob`): survives no-match (no literal `*`) and paths
# with spaces; last iteration wins = latest version dir (glob sorts ascending).
CG_RESOLVED=""
shopt -s nullglob 2>/dev/null
for f in "$CLAUDE_DIR"/plugins/cache/pedro-plugins/context-guard/*/hooks/context-guard-writer.sh; do
  CG_RESOLVED="$f"
done
shopt -u nullglob 2>/dev/null
if [ -z "$CG_RESOLVED" ] && [ -n "${PEDRO_PLUGINS_REPO:-}" ] && [ -f "$PEDRO_PLUGINS_REPO/plugins/context-guard/hooks/context-guard-writer.sh" ]; then
  CG_RESOLVED="$PEDRO_PLUGINS_REPO/plugins/context-guard/hooks/context-guard-writer.sh"
fi
if [ -n "$CG_RESOLVED" ]; then
  # Runtime-resolving command (glob) so it survives context-guard version bumps.
  # shellcheck disable=SC2016  # string literal de propósito: o $(...) é resolvido em runtime pelo Claude Code, não aqui
  SL_CMD='bash "$(ls -d ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache/pedro-plugins/context-guard/*/hooks/context-guard-writer.sh 2>/dev/null | tail -1)"'
  # O RELOGIO DA BARRA. A cadeia ja produz a linha do motor, mas quem redesenha a
  # barra e o harness, e por padrao ele so redesenha em EVENTO (tecla, turno,
  # troca de modelo): com o trabalho correndo em segundo plano e o dono sem
  # digitar nada, a linha congela no valor da ultima tecla. `refreshInterval` e a
  # unica alavanca que existe do nosso lado — o proprio schema do settings a
  # descreve como "re-run the status line command every N seconds in addition to
  # event-driven updates". 10s porque a duracao da linha e contada em segundos
  # (`andamento.py:_dur`), entao a 10s ela muda visivelmente sem por a cadeia
  # inteira (writer + python + renderizador) de pe a cada segundo.
  "$PY" "$CFGJSON" statusline "$SETTINGS" "$SL_CMD" > "$SETTINGS.tmp" \
    && mv "$SETTINGS.tmp" "$SETTINGS" \
    && echo "[bootstrap/config] ✓ statusLine resolvido (glob runtime do context-guard)"
else
  echo "[bootstrap/config] ⚠ context-guard não encontrado — statusLine não alterado (instale context-guard e rode de novo)"
fi

# --- 3. Copy the global CLAUDE.md ---
if [ -f "$CLAUDE_SRC" ]; then
  [ -f "$CLAUDE_DIR/CLAUDE.md" ] && cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md.bak.$(date +%Y%m%d%H%M%S)"
  cp "$CLAUDE_SRC" "$CLAUDE_DIR/CLAUDE.md"
  echo "[bootstrap/config] ✓ CLAUDE.md global aplicado"
fi

echo "[bootstrap/config] ✓ done — settings.local.json NÃO foi tocado"
exit 0
