#!/bin/bash
# StatusLine middleware: extracts context% to a PER-SESSION state file, then forwards
# to the original statusLine command. Set CLAUDE_STATUSLINE_FORWARD to the original
# command (e.g. "node /path/to/hud/dist/index.js").
#
# ⚠️ PER-SESSION state (não global): o statusLine de QUALQUER sessão renderiza no mesmo
# host; um arquivo global (/tmp/claude-context-pct) era sobrescrito pela última sessão a
# renderizar, então uma sessão cheia (80%) fazia o guard bloquear TODAS as outras. O
# estado agora é /tmp/claude-context-pct-<session_id> — cada sessão só lê o próprio %.
INPUT=$(cat)

JQ=$(command -v jq 2>/dev/null)
if [ -n "$JQ" ]; then
  PCT=$(printf '%s' "$INPUT" | "$JQ" -r '.context_window.used_percentage // empty' 2>/dev/null)
  SID=$(printf '%s' "$INPUT" | "$JQ" -r '.session_id // empty' 2>/dev/null)
  # Sem session_id → não grava (fail-safe: guard sem arquivo da sessão = não dispara).
  [ -n "$PCT" ] && [ -n "$SID" ] && printf '%s' "$PCT" > "/tmp/claude-context-pct-${SID}"
fi

if [ -n "$CLAUDE_STATUSLINE_FORWARD" ]; then
  printf '%s' "$INPUT" | eval "$CLAUDE_STATUSLINE_FORWARD"
fi
