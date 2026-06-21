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
#   language/theme/autoCompactEnabled → defaults win
#   statusLine              → resolved to the context-guard writer on THIS machine (runtime glob)
#   enabledPlugins / extraKnownMarketplaces / hooks → UNTOUCHED (owned by plugin sync)
#   settings.local.json     → NEVER touched
#
# Exit: 0 ok, 1 error.

set -uo pipefail

JQ="$(command -v jq)"; [ -z "$JQ" ] && { echo "[bootstrap/config] jq required — install it first"; exit 1; }

# Locate the plugin's config dir
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/config" ]; then
  CFG_DIR="$CLAUDE_PLUGIN_ROOT/config"
else
  CFG_DIR="$(cd "$(dirname "$0")/../../config" 2>/dev/null && pwd)"
fi
DEFAULTS="$CFG_DIR/settings-defaults.json"
CLAUDE_SRC="$CFG_DIR/CLAUDE-global.md"

SETTINGS="$HOME/.claude/settings.json"
mkdir -p "$HOME/.claude"

[ -f "$DEFAULTS" ] || { echo "[bootstrap/config] settings-defaults.json não encontrado em $CFG_DIR"; exit 1; }
"$JQ" empty "$DEFAULTS" 2>/dev/null || { echo "[bootstrap/config] settings-defaults.json inválido"; exit 1; }

# --- 1. Merge settings-defaults into settings.json ---
CURRENT="{}"
if [ -f "$SETTINGS" ]; then
  "$JQ" empty "$SETTINGS" 2>/dev/null || { echo "[bootstrap/config] settings.json local inválido — abortando (não sobrescrevo)"; exit 1; }
  CURRENT="$(cat "$SETTINGS")"
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
fi

# shellcheck disable=SC2016,SC2015  # aspas simples = programa jq ($cur/$def/$d são vars do jq); o "A && mv || {cleanup}" é o cleanup intencional no erro do mv
echo "$CURRENT" | "$JQ" --slurpfile d "$DEFAULTS" '
  . as $cur
  | ($d[0]) as $def
  | .env = (($cur.env // {}) * ($def.env // {}))
  | .permissions = ($cur.permissions // {})
  | .permissions.allow = (((($cur.permissions.allow) // []) + (($def.permissions.allow) // [])) | unique)
  | .permissions.deny  = (((($cur.permissions.deny)  // []) + (($def.permissions.deny)  // [])) | unique)
  | .permissions.defaultMode = ($cur.permissions.defaultMode // $def.permissions.defaultMode)
  | .language = ($def.language // $cur.language)
  | .theme = ($def.theme // $cur.theme)
  | .autoCompactEnabled = (if ($def.autoCompactEnabled != null) then $def.autoCompactEnabled else $cur.autoCompactEnabled end)
  | .permissions |= (if .defaultMode == null then del(.defaultMode) else . end)
  | (if .language == null then del(.language) else . end)
  | (if .theme == null then del(.theme) else . end)
  | (if .autoCompactEnabled == null then del(.autoCompactEnabled) else . end)
' > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS" || { rm -f "$SETTINGS.tmp"; echo "[bootstrap/config] merge falhou — settings.json intacto"; exit 1; }
echo "[bootstrap/config] ✓ settings.json: env + permissions (union) + flags aplicados"

# --- 2. Resolve statusLine to the context-guard writer on THIS machine ---
# nullglob loop (not `ls -d $glob`): survives no-match (no literal `*`) and paths
# with spaces; last iteration wins = latest version dir (glob sorts ascending).
CG_RESOLVED=""
shopt -s nullglob 2>/dev/null
for f in "${CLAUDE_CONFIG_DIR:-$HOME/.claude}"/plugins/cache/pedro-plugins/context-guard/*/hooks/context-guard-writer.sh; do
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
  # shellcheck disable=SC2016  # $cmd é variável do jq (passada via --arg), não do shell
  "$JQ" --arg cmd "$SL_CMD" '.statusLine = {type:"command", command:$cmd}' "$SETTINGS" > "$SETTINGS.tmp" \
    && mv "$SETTINGS.tmp" "$SETTINGS" \
    && echo "[bootstrap/config] ✓ statusLine resolvido (glob runtime do context-guard)"
else
  echo "[bootstrap/config] ⚠ context-guard não encontrado — statusLine não alterado (instale context-guard e rode de novo)"
fi

# --- 3. Copy the global CLAUDE.md ---
if [ -f "$CLAUDE_SRC" ]; then
  [ -f "$HOME/.claude/CLAUDE.md" ] && cp "$HOME/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md.bak.$(date +%Y%m%d%H%M%S)"
  cp "$CLAUDE_SRC" "$HOME/.claude/CLAUDE.md"
  echo "[bootstrap/config] ✓ CLAUDE.md global aplicado"
fi

echo "[bootstrap/config] ✓ done — settings.local.json NÃO foi tocado"
exit 0
