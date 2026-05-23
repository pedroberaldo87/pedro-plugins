#!/bin/bash
# StatusLine middleware: extracts context% to state file, then forwards to the original statusLine command.
# Set CLAUDE_STATUSLINE_FORWARD to the original command (e.g. "node /path/to/hud/dist/index.js").
INPUT=$(cat)

JQ=$(command -v jq 2>/dev/null)
if [ -n "$JQ" ]; then
  PCT=$(printf '%s' "$INPUT" | "$JQ" -r '.context_window.used_percentage // empty' 2>/dev/null)
  [ -n "$PCT" ] && printf '%s' "$PCT" > /tmp/claude-context-pct
fi

if [ -n "$CLAUDE_STATUSLINE_FORWARD" ]; then
  printf '%s' "$INPUT" | eval "$CLAUDE_STATUSLINE_FORWARD"
fi
