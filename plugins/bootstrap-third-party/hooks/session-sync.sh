#!/usr/bin/env bash
# session-sync.sh — SessionStart hook entrypoint.
#
# Runs the full sync cycle when Claude Code starts:
#   1. Cheap remote check (git fetch or ls-remote) — always runs
#   2. If remote advanced OR throttle expired → full sync
#   3. Full sync = pull → apply manifest → snapshot → commit+push (if HAS_SOURCE)
#
# Throttle: skips full sync if last successful sync was <24h ago AND remote
# hasn't advanced. Bypass with PEDRO_PLUGINS_FORCE_SYNC=1.
#
# Exit codes:
#   0 — always (never blocks session startup)

set -uo pipefail

PEDRO_PLUGINS_REPO="${PEDRO_PLUGINS_REPO:-$HOME/PROGRAMACAO/PEDRO/pedro-plugins}"
PLUGIN_CACHE_MARKETPLACE="$HOME/.claude/plugins/marketplaces/pedro-plugins"
LAST_SYNC_FILE="$HOME/.claude/plugins/.pedro-plugins-last-sync"
THROTTLE_SECONDS="${PEDRO_PLUGINS_THROTTLE_SECONDS:-86400}"  # 24h default
FORCE="${PEDRO_PLUGINS_FORCE_SYNC:-}"
VERBOSE="${PEDRO_PLUGINS_VERBOSE:-}"

# Locate lib dir — scripts share via $CLAUDE_PLUGIN_ROOT when run as hook,
# or ../lib when invoked directly
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/hooks/lib" ]; then
  LIB_DIR="$CLAUDE_PLUGIN_ROOT/hooks/lib"
else
  LIB_DIR="$(cd "$(dirname "$0")" && pwd)/lib"
fi

SNAPSHOT_SH="$LIB_DIR/snapshot.sh"
APPLY_SH="$LIB_DIR/apply.sh"
GIT_SYNC_SH="$LIB_DIR/git-sync.sh"

log() { echo "[pedro-plugins/session-sync] $*" >&2; }
info() { echo "[pedro-plugins/session-sync] $*"; }
verbose() { [ -n "$VERBOSE" ] && info "$*"; }

# Detect source repo presence
HAS_SOURCE=0
[ -d "$PEDRO_PLUGINS_REPO/.git" ] && HAS_SOURCE=1

# ---- Step 1: Cheap remote check ----
REMOTE_ADVANCED=0

if [ "$HAS_SOURCE" -eq 1 ]; then
  # Has source repo — use git fetch
  if git -C "$PEDRO_PLUGINS_REPO" remote get-url origin >/dev/null 2>&1; then
    if git -C "$PEDRO_PLUGINS_REPO" fetch --quiet 2>/dev/null; then
      LOCAL_HEAD="$(git -C "$PEDRO_PLUGINS_REPO" rev-parse HEAD 2>/dev/null || echo "")"
      REMOTE_HEAD="$(git -C "$PEDRO_PLUGINS_REPO" rev-parse @{u} 2>/dev/null || echo "")"
      if [ -n "$LOCAL_HEAD" ] && [ -n "$REMOTE_HEAD" ] && [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
        # Check if remote is actually ahead (not just diverged)
        if git -C "$PEDRO_PLUGINS_REPO" merge-base --is-ancestor "$LOCAL_HEAD" "$REMOTE_HEAD" 2>/dev/null; then
          REMOTE_ADVANCED=1
          verbose "remote ahead — forcing sync"
        fi
      fi
    else
      verbose "git fetch failed — offline?"
    fi
  else
    verbose "no remote configured — skipping fetch"
  fi
elif [ -d "$PLUGIN_CACHE_MARKETPLACE/.git" ]; then
  # No source repo, but marketplace cache exists
  if git -C "$PLUGIN_CACHE_MARKETPLACE" fetch --quiet 2>/dev/null; then
    LOCAL_HEAD="$(git -C "$PLUGIN_CACHE_MARKETPLACE" rev-parse HEAD 2>/dev/null || echo "")"
    REMOTE_HEAD="$(git -C "$PLUGIN_CACHE_MARKETPLACE" rev-parse @{u} 2>/dev/null || echo "")"
    if [ -n "$LOCAL_HEAD" ] && [ -n "$REMOTE_HEAD" ] && [ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]; then
      REMOTE_ADVANCED=1
      verbose "marketplace cache behind — forcing sync"
    fi
  fi
fi

# ---- Step 2: Throttle check ----
if [ "$REMOTE_ADVANCED" -eq 0 ] && [ -z "$FORCE" ] && [ -f "$LAST_SYNC_FILE" ]; then
  LAST_SYNC_MTIME="$(stat -f %m "$LAST_SYNC_FILE" 2>/dev/null || stat -c %Y "$LAST_SYNC_FILE" 2>/dev/null || echo 0)"
  NOW="$(date +%s)"
  AGE=$((NOW - LAST_SYNC_MTIME))
  if [ "$AGE" -lt "$THROTTLE_SECONDS" ]; then
    verbose "throttled (last sync ${AGE}s ago, limit ${THROTTLE_SECONDS}s)"
    exit 0
  fi
fi

# ---- Step 3: Full sync ----

# 3a. Pull source repo (if present)
if [ "$HAS_SOURCE" -eq 1 ]; then
  if git -C "$PEDRO_PLUGINS_REPO" remote get-url origin >/dev/null 2>&1; then
    PULL_OUTPUT="$(git -C "$PEDRO_PLUGINS_REPO" pull --rebase --autostash 2>&1)"
    PULL_EXIT=$?
    if [ "$PULL_EXIT" -ne 0 ]; then
      if echo "$PULL_OUTPUT" | grep -qiE "conflict|cannot pull"; then
        log "⚠ git pull conflict em $PEDRO_PLUGINS_REPO — sync pausado"
        log "   resolva manualmente: cd $PEDRO_PLUGINS_REPO && git status"
        # Try to abort any in-progress rebase
        git -C "$PEDRO_PLUGINS_REPO" rebase --abort 2>/dev/null || true
        exit 0
      else
        log "⚠ git pull falhou (rede/auth?) — usando manifest local"
      fi
    else
      verbose "git pull ok"
    fi
  fi
fi

# 3b. Update marketplace cache (so apply can read fresh manifest)
if claude plugin marketplace list 2>/dev/null | grep -q "pedro-plugins"; then
  if [ "$HAS_SOURCE" -eq 0 ]; then
    # Only bother updating cache if we rely on it (no source repo)
    claude plugin marketplace update pedro-plugins >/dev/null 2>&1 || verbose "marketplace update failed"
  fi
fi

# 3c. Apply manifest to local state
if [ ! -x "$APPLY_SH" ]; then
  log "⚠ apply.sh não encontrado em $APPLY_SH"
  exit 0
fi

APPLY_OUTPUT="$(bash "$APPLY_SH" 2>&1)"
echo "$APPLY_OUTPUT"

# 3d. Snapshot + commit + push (only if HAS_SOURCE)
if [ "$HAS_SOURCE" -eq 1 ] && [ -x "$SNAPSHOT_SH" ]; then
  SNAPSHOT_RESULT="$(bash "$SNAPSHOT_SH" 2>&1)"
  SNAPSHOT_STATUS="$(echo "$SNAPSHOT_RESULT" | tail -1)"
  if [ "$SNAPSHOT_STATUS" = "changed" ]; then
    verbose "manifest changed locally — committing"
    if [ -x "$GIT_SYNC_SH" ]; then
      bash "$GIT_SYNC_SH" "chore(plugins): sync @ $(hostname -s) $(date +%Y-%m-%d)"
    fi
  fi
fi

# ---- Step 4: Update sync timestamp ----
touch "$LAST_SYNC_FILE"

exit 0
