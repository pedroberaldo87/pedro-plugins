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

TOKEN_FILE="$LOG_DIR/.token"

mkdir -p "$LOG_DIR"

# Secret the page must send (X-Visual-Token) so only the generated page — not any
# web page in the browser — can read or write the live-sync state. 0600, created
# only if missing: a daemon restart or a second call keeps it, so a page that is
# already open keeps syncing. visual_page.py and the daemon create it the same way.
ensure_token() {
  if [ -f "$TOKEN_FILE" ] && [ "$(wc -c < "$TOKEN_FILE" | tr -d ' ')" -ge 64 ]; then
    chmod 600 "$TOKEN_FILE" 2>/dev/null || true
    return 0
  fi
  local tmp tok
  tmp="$(umask 077; mktemp "$LOG_DIR/.token.XXXXXX")" || return 0
  tok="$(LC_ALL=C od -An -N32 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n')"
  if [ "${#tok}" -ne 64 ]; then rm -f "$tmp"; return 0; fi
  printf '%s\n' "$tok" > "$tmp"
  chmod 600 "$tmp" 2>/dev/null || true
  # `ln` fails when the file already exists: whoever got there first wins.
  if ! ln "$tmp" "$TOKEN_FILE" 2>/dev/null; then
    [ -s "$TOKEN_FILE" ] || mv -f "$tmp" "$TOKEN_FILE" 2>/dev/null || true
  fi
  rm -f "$tmp"
}

ensure_token

ping_daemon() {
  curl -sf --max-time 1 "http://${HOST}:${PORT}/ping" > /dev/null 2>&1
}

# A daemon from before the token existed answers /ping without `"auth":true` and
# accepts anyone. Replace it; only a process whose command line is visual_server.
ping_has_auth() {
  curl -sf --max-time 1 "http://${HOST}:${PORT}/ping" 2>/dev/null | grep -q '"auth":true'
}

replace_stale_daemon() {
  local pid cmd
  pid="$(curl -sf --max-time 1 "http://${HOST}:${PORT}/ping" 2>/dev/null \
    | sed -n 's/.*"pid":\([0-9][0-9]*\).*/\1/p')"
  [ -n "$pid" ] || return 1
  cmd="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  case "$cmd" in
    *visual_server*) kill "$pid" 2>/dev/null || return 1 ;;
    *) return 1 ;;
  esac
  for _ in 1 2 3 4 5 6 7 8; do
    sleep 0.25
    ping_daemon || return 0
  done
  return 1
}

# Already running (and enforcing the token)? Done.
if ping_daemon; then
  if ping_has_auth; then
    echo "claude-visual-server already running on :${PORT}"
    exit 0
  fi
  if ! replace_stale_daemon; then
    echo "claude-visual-server: a daemon without token check is running on :${PORT} and could not be replaced — live sync stays off" >&2
    exit 0
  fi
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
