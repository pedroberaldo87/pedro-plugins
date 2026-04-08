#!/usr/bin/env bash
# post-plugin-command.sh — PostToolUse hook entrypoint.
#
# Fires after every Bash tool use. If the command was a `claude plugin *`
# mutation (install/uninstall/enable/disable/marketplace add/remove), runs
# snapshot + commit + push immediately — propagates the change without waiting
# for the next SessionStart.
#
# Receives JSON on stdin with the tool invocation details. We only care about
# the `tool_input.command` field.
#
# Only active when the source repo exists. Never throttled.
#
# Exit codes:
#   0 — always (never blocks the Bash tool result)

set -uo pipefail

PEDRO_PLUGINS_REPO="${PEDRO_PLUGINS_REPO:-$HOME/PROGRAMACAO/PEDRO/pedro-plugins}"

# Locate lib dir
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/hooks/lib" ]; then
  LIB_DIR="$CLAUDE_PLUGIN_ROOT/hooks/lib"
else
  LIB_DIR="$(cd "$(dirname "$0")" && pwd)/lib"
fi

SNAPSHOT_SH="$LIB_DIR/snapshot.sh"
GIT_SYNC_SH="$LIB_DIR/git-sync.sh"

log() { echo "[pedro-plugins/post-tool] $*" >&2; }

# Early exit: no source repo → nothing to commit
if [ ! -d "$PEDRO_PLUGINS_REPO/.git" ]; then
  exit 0
fi

# Read stdin (hook event JSON)
PAYLOAD="$(cat 2>/dev/null || echo "")"
[ -z "$PAYLOAD" ] && exit 0

# Extract command. Claude Code hook payload has tool_input.command for Bash tool.
COMMAND="$(echo "$PAYLOAD" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")"
[ -z "$COMMAND" ] && exit 0

# Match `claude plugin (install|uninstall|enable|disable|marketplace (add|remove|rm))`
if ! echo "$COMMAND" | grep -qE 'claude[[:space:]]+plugin[s]?[[:space:]]+(install|i|uninstall|remove|enable|disable|marketplace[[:space:]]+(add|remove|rm))'; then
  exit 0
fi

# Also skip if the command was about pedro-plugins itself (self-sync loop)
if echo "$COMMAND" | grep -q 'pedro-plugins'; then
  exit 0
fi

# Run snapshot
if [ ! -x "$SNAPSHOT_SH" ]; then
  log "⚠ snapshot.sh não encontrado em $SNAPSHOT_SH"
  exit 0
fi

# Capture stdout only — snapshot.sh prints "changed"/"unchanged" on stdout,
# log messages on stderr. Merging them (2>&1) would create ordering ambiguity
# because `tail -1` might grab a log line instead of the status.
SNAPSHOT_STATUS="$(bash "$SNAPSHOT_SH" 2>/dev/null)"

if [ "$SNAPSHOT_STATUS" != "changed" ]; then
  # Manifest didn't actually change (maybe the command was a no-op)
  exit 0
fi

# Extract a short description of what happened for the commit message.
# Note: the regex uses [a-z]+ which clips plugin names with digits (context7 → context).
# Minor cosmetic issue in commit messages only — semantic state is correct.
ACTION="$(echo "$COMMAND" | grep -oE 'claude[[:space:]]+plugin[s]?[[:space:]]+[a-z]+([[:space:]]+[a-z0-9_-]+)?' | head -1)"
[ -z "$ACTION" ] && ACTION="plugin change"

# Commit + push via git-sync
if [ -x "$GIT_SYNC_SH" ]; then
  bash "$GIT_SYNC_SH" "chore(plugins): $ACTION @ $(hostname -s)"
fi

exit 0
