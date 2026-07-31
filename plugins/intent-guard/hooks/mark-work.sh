#!/usr/bin/env bash
# PostToolUse(Edit|Write|MultiEdit|NotebookEdit) — marca que ESTA sessão teve
# trabalho de verdade. O gate de entrega (delivery-audit.sh) só age se esta
# sentinela existir: sessão só de conversa nunca é bloqueada no Stop.
set -uo pipefail
MODE_FILE="$HOME/.claude/intent-guard/mode"
[ -f "$MODE_FILE" ] && [ "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" = "off" ] && exit 0
SID="$(cat 2>/dev/null | { command -v jq >/dev/null && jq -r '.session_id // empty'; } 2>/dev/null || true)"
[ -n "$SID" ] && touch "/tmp/intent-guard-work-${SID}" 2>/dev/null
exit 0
