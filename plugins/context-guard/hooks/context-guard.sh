#!/bin/bash
# PostToolUse hook: blocks workflow when context exceeds threshold.
# Reads context% from /tmp/claude-context-pct (written by the statusLine wrapper).
# Fires once per session — per-session sentinel prevents repeated blocking.
THRESHOLD="${CLAUDE_CONTEXT_THRESHOLD:-80}"
STATE="/tmp/claude-context-pct"

# Extract session_id from hook stdin for per-session sentinel
SESSION_ID=$(jq -r '.session_id // "unknown"' 2>/dev/null)
SENTINEL="/tmp/claude-context-warned-${SESSION_ID}"

[ -f "$SENTINEL" ] && exit 0

PCT=$(cat "$STATE" 2>/dev/null)
[ -z "$PCT" ] && exit 0

PCT_INT="${PCT%.*}"

if [ "$PCT_INT" -ge "$THRESHOLD" ] 2>/dev/null; then
  touch "$SENTINEL"
  printf '{"continue":false,"stopReason":"⚠️ CONTEXTO EM %s%%. Rode /handoff pra preservar a sessão antes de continuar."}\n' "$PCT_INT"
fi
