#!/usr/bin/env bash
# Start claude-visual-server if not running. Idempotent.
# Called by the /visual skill right before opening an HTML that expects live sync.
# Falls back silently: if Node is missing or daemon fails to start, the HTML
# still works in copy/paste mode.

set -uo pipefail

PORT="${CLAUDE_VISUAL_PORT:-7755}"
HOST=127.0.0.1
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DAEMON="$SCRIPT_DIR/visual_server.mjs"
LOG_DIR="$HOME/.claude/visual-state"
LOG="$LOG_DIR/.daemon.log"

mkdir -p "$LOG_DIR"

ping_daemon() {
  curl -sf --max-time 1 "http://${HOST}:${PORT}/ping" > /dev/null 2>&1
}

# Already running? Done.
if ping_daemon; then
  echo "claude-visual-server already running on :${PORT}"
  exit 0
fi

# Need Node.
if ! command -v node > /dev/null 2>&1; then
  echo "claude-visual-server: node not in PATH — skipping live sync" >&2
  exit 0  # Soft fail: skill keeps working via copy/paste.
fi

# Spawn detached so skill can continue and not inherit the daemon process tree.
nohup env CLAUDE_VISUAL_PORT="$PORT" node "$DAEMON" >> "$LOG" 2>&1 &
disown || true

# Wait briefly for it to come up.
for _ in 1 2 3 4 5 6 7 8; do
  sleep 0.25
  if ping_daemon; then
    echo "claude-visual-server started on :${PORT}"
    exit 0
  fi
done

echo "claude-visual-server: failed to start within 2s (see $LOG)" >&2
exit 0  # Still soft-fail — skill continues without live sync.
