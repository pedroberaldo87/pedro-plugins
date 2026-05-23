#!/bin/bash
# StatusLine wrapper: extracts context% to state file, then pipes to claude-hud.
# This script replaces the statusLine command in settings.json.
# It reads the same JSON stdin that Claude Code sends to the statusLine.
INPUT=$(cat)

# Extract context percentage
JQ=$(command -v jq 2>/dev/null)
if [ -n "$JQ" ]; then
  PCT=$(printf '%s' "$INPUT" | "$JQ" -r '.context_window.used_percentage // empty' 2>/dev/null)
  [ -n "$PCT" ] && printf '%s' "$PCT" > /tmp/claude-context-pct
fi

# Forward to claude-hud (if installed)
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
PLUGIN_DIR=$(ls -d "${CLAUDE_DIR}"/plugins/cache/claude-hud/claude-hud/*/ 2>/dev/null \
  | awk -F/ '{ print $(NF-1) "\t" $0 }' \
  | sort -t. -k1,1n -k2,2n -k3,3n -k4,4n \
  | tail -1 | cut -f2-)

NODE=$(command -v node 2>/dev/null)
if [ -n "$PLUGIN_DIR" ] && [ -n "$NODE" ]; then
  printf '%s' "$INPUT" | "$NODE" "${PLUGIN_DIR}dist/index.js"
fi
