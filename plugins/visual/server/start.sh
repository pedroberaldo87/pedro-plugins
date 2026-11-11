#!/usr/bin/env bash
# Start claude-visual-server if not running. Idempotent.
# Called by the /visual skill right before opening an HTML that expects live sync.
# Falls back silently: if Node is missing or daemon fails to start, the HTML
# still works in copy/paste mode.

#   start.sh                 start (or keep) the daemon
#   start.sh --rotate-token  stop our daemon, replace the secret in ~/.claude/visual-state/.token,
#                            start a fresh daemon. Pages generated BEFORE this lose live sync
#                            (they fall back to copy/paste); generate them again after.

set -uo pipefail

ROTATE=0
case "${1:-}" in
  --rotate-token) ROTATE=1 ;;
  "") ;;
  *) echo "usage: start.sh [--rotate-token]" >&2; exit 2 ;;
esac

PORT="${CLAUDE_VISUAL_PORT:-7755}"
HOST=127.0.0.1
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DAEMON="$SCRIPT_DIR/visual_server.mjs"
LOG_DIR="$HOME/.claude/visual-state"
LOG="$LOG_DIR/.daemon.log"

TOKEN_FILE="$LOG_DIR/.token"

mkdir -p "$LOG_DIR"
chmod 700 "$LOG_DIR" 2>/dev/null || true   # the dir holds the secret: owner only

# Secret the page must send (X-Visual-Token) so only the generated page — not any
# web page in the browser — can read or write the live-sync state. 0600, created
# only if missing: a daemon restart or a second call keeps it, so a page that is
# already open keeps syncing. visual_page.py and the daemon create it the same way.
ensure_token() {
  if [ -f "$TOKEN_FILE" ] && tr -d ' \n\r' < "$TOKEN_FILE" | grep -Eq '^[0-9a-f]{64}$'; then
    chmod 600 "$TOKEN_FILE" 2>/dev/null || true
    return 0
  fi
  local tmp tok
  tmp="$(umask 077; mktemp "$LOG_DIR/.token.XXXXXX")" || return 0
  tok="$(LC_ALL=C od -An -N32 -tx1 /dev/urandom 2>/dev/null | tr -d ' \n')"
  if [ "${#tok}" -ne 64 ]; then rm -f "$tmp"; return 0; fi
  printf '%s\n' "$tok" > "$tmp"
  chmod 600 "$tmp" 2>/dev/null || true
  # `ln` fails when the file already exists: whoever got there first wins. A file that
  # is there but is not a valid token is corrupt (the check above said so): replace it.
  if ! ln "$tmp" "$TOKEN_FILE" 2>/dev/null; then
    if ! tr -d ' \n\r' < "$TOKEN_FILE" 2>/dev/null | grep -Eq '^[0-9a-f]{64}$'; then
      mv -f "$tmp" "$TOKEN_FILE" 2>/dev/null || true
    fi
  fi
  rm -f "$tmp"
}

ping_daemon() {
  curl -sf --max-time 1 "http://${HOST}:${PORT}/ping" > /dev/null 2>&1
}

# A daemon from before the token existed answers /ping without `"auth":true` and
# accepts anyone. Replace it; only a process whose command line is visual_server.
ping_has_auth() {
  curl -sf --max-time 1 "http://${HOST}:${PORT}/ping" 2>/dev/null | grep -q '"auth":true'
}

is_windows() {
  case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) return 0 ;; esac
  return 1
}

# Up to 2 s for the port to stop answering.
wait_gone() {
  for _ in 1 2 3 4 5 6 7 8; do
    sleep 0.25
    ping_daemon || return 0
  done
  return 1
}

# Our own daemon (one that enforces the token) stops when asked with a signature made from
# the token: this works the same on every OS and needs no pid. Only the signature is sent
# (HMAC-SHA256 over the current time, the daemon accepts it for 30 s), never the token: this
# request goes to whatever answers on the port. Not ours, or a token that no longer
# matches → non-zero, and the caller falls back to identifying the process.
stop_via_token() {
  local tok sig
  command -v node > /dev/null 2>&1 || return 1
  tok="$(tr -d ' \n\r' < "$TOKEN_FILE" 2>/dev/null || true)"
  printf '%s' "$tok" | grep -Eq '^[0-9a-f]{64}$' || return 1
  ping_has_auth || return 1
  # The secret goes to node by environment, not argv (argv is visible to other users).
  sig="$(VISUAL_TOKEN="$tok" node -e '
    const t = String(Date.now());
    const h = require("node:crypto").createHmac("sha256", process.env.VISUAL_TOKEN)
      .update("shutdown." + t).digest("hex");
    process.stdout.write(t + "." + h);' 2>/dev/null)" || return 1
  curl -sf --max-time 2 -X POST -H "X-Visual-Shutdown: $sig" -H 'Content-Type: application/json' \
    -d '{}' "http://${HOST}:${PORT}/shutdown" > /dev/null 2>&1 || return 1
  wait_gone
}

# Command line of a pid, empty if unknown. Git Bash's `ps` shows MSYS processes only, never
# a native Windows node.exe, so there the question goes to Windows (PowerShell, or wmic on
# machines without it). MSYS2_ARG_CONV_EXCL stops Git Bash from rewriting `/value` as a path.
cmdline_of() {
  local pid="$1" out=""
  if is_windows; then
    export MSYS2_ARG_CONV_EXCL='*'
    if command -v powershell.exe > /dev/null 2>&1; then
      out="$(powershell.exe -NoProfile -NonInteractive -Command \
        "(Get-CimInstance Win32_Process -Filter 'ProcessId=${pid}').CommandLine" 2>/dev/null || true)"
    fi
    if [ -z "$(printf '%s' "$out" | tr -d ' \r\n')" ] && command -v wmic > /dev/null 2>&1; then
      out="$(wmic process where "ProcessId=${pid}" get CommandLine /value 2>/dev/null \
        | sed -n 's/^CommandLine=//p' || true)"
    fi
    # Quotes, CR and backslashes out, lower case: `"C:\Program Files\nodejs\node.exe" C:\x\visual_server.mjs`
    # becomes `c:/program files/nodejs/node.exe c:/x/visual_server.mjs`.
    printf '%s' "$out" | tr -d '\r"' | tr '\\' '/' | tr 'A-Z' 'a-z' | sed 's/^ *//; s/ *$//' | head -n 1
  else
    ps -p "$pid" -o command= 2>/dev/null || true
  fi
}

kill_pid() {
  local pid="$1"
  if is_windows; then
    # SIGTERM is a hard stop for a native Windows process, and node can send it; Git Bash's
    # own `kill` only knows MSYS pids.
    node -e 'process.kill(Number(process.argv[1]))' "$pid" 2>/dev/null && return 0
    MSYS2_ARG_CONV_EXCL='*' taskkill /PID "$pid" /F > /dev/null 2>&1
  else
    kill "$pid" 2>/dev/null
  fi
}

replace_stale_daemon() {
  local pid cmd
  # Ours and current: ask it to stop. Anything else (a daemon without the token check, or
  # one whose token we no longer hold) is identified by its command line before it is killed.
  stop_via_token && return 0
  pid="$(curl -sf --max-time 1 "http://${HOST}:${PORT}/ping" 2>/dev/null \
    | sed -n 's/.*"pid":\([0-9][0-9]*\).*/\1/p')"
  [ -n "$pid" ] || return 1
  cmd="$(cmdline_of "$pid")"
  # Only `node <path>/visual_server.mjs` (any plugin version's copy). A substring match
  # would also stop `vim …/visual_server.mjs` if a squatter on the port reported its pid.
  case "$cmd" in
    node\ *visual_server.mjs|*/node\ *visual_server.mjs) kill_pid "$pid" || return 1 ;;
    node.exe\ *visual_server.mjs|*/node.exe\ *visual_server.mjs)
      is_windows && { kill_pid "$pid" || return 1; } || return 1 ;;
    *) return 1 ;;
  esac
  wait_gone
}

# Explicit rotation: the daemon holds the token in memory, so ours has to stop before the
# file is replaced. If the process on the port is not ours, leave the token alone.
if [ "$ROTATE" = 1 ]; then
  if ping_daemon && ! replace_stale_daemon; then
    echo "claude-visual-server: could not stop the daemon on :${PORT} — token NOT rotated" >&2
    exit 1
  fi
  rm -f "$TOKEN_FILE"
  echo "claude-visual-server: token rotated — open pages lose live sync; generate them again"
fi

ensure_token

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
