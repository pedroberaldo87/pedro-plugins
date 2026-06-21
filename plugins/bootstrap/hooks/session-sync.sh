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

# Re-entrancy guard: if we're already running (from a parent hook invocation
# or from the PostToolUse hook firing on subprocess claude plugin commands),
# exit silently. Prevents recursive execution.
if [ -n "${PEDRO_PLUGINS_HOOK_RUNNING:-}" ]; then
  exit 0
fi
export PEDRO_PLUGINS_HOOK_RUNNING=session-sync

PEDRO_PLUGINS_REPO="${PEDRO_PLUGINS_REPO:-$HOME/PROGRAMACAO/PEDRO/pedro-plugins}"
KNOWN_MARKETPLACES="$HOME/.claude/plugins/known_marketplaces.json"
PLUGIN_CACHE_MARKETPLACE="$HOME/.claude/plugins/marketplaces/pedro-plugins"
LAST_SYNC_FILE="$HOME/.claude/plugins/.pedro-plugins-last-sync"
LOCK_DIR="$HOME/.claude/plugins/.pedro-plugins-sync.lock"
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

# Acquire lock to prevent concurrent syncs from multiple Claude Code sessions.
# Using mkdir for atomic semantics (POSIX-portable, no flock dependency).
# Lock is auto-released on exit via trap. Stale locks (>5min old) are broken.
if [ -d "$LOCK_DIR" ]; then
  LOCK_AGE=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || stat -c %Y "$LOCK_DIR" 2>/dev/null || echo 0) ))
  if [ "$LOCK_AGE" -gt 300 ]; then
    verbose "stale lock (${LOCK_AGE}s old) — breaking"
    rmdir "$LOCK_DIR" 2>/dev/null || true
  fi
fi
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  verbose "another sync in progress — skipping"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT INT TERM

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
      REMOTE_HEAD="$(git -C "$PEDRO_PLUGINS_REPO" rev-parse "@{u}" 2>/dev/null || echo "")"
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
    REMOTE_HEAD="$(git -C "$PLUGIN_CACHE_MARKETPLACE" rev-parse "@{u}" 2>/dev/null || echo "")"
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
        # Pull failed for a non-conflict reason (network, auth, disk).
        # If we KNEW remote had new commits (from the earlier fetch), abort:
        # applying a stale manifest would silently miss other machines' changes
        # for up to 24h. Better to retry on next session.
        if [ "$REMOTE_ADVANCED" -eq 1 ]; then
          log "⚠ git pull falhou e sabemos que remote avançou — sync abortado"
          log "   NÃO atualizando timestamp: próxima sessão vai tentar de novo imediatamente"
          log "   motivo: $(echo "$PULL_OUTPUT" | head -3 | tr '\n' ' ')"
          exit 0
        fi
        log "⚠ git pull falhou (rede/auth?) — usando manifest local (remote estava sincronizado)"
      fi
    else
      verbose "git pull ok"
    fi
  fi
fi

# 3b. Update marketplace cache (so apply can read fresh manifest)
# Use jq on known_marketplaces.json instead of grep (word-boundary safe)
if [ -f "$KNOWN_MARKETPLACES" ] && jq -e '."pedro-plugins"' "$KNOWN_MARKETPLACES" >/dev/null 2>&1; then
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
APPLY_EXIT=$?
echo "$APPLY_OUTPUT"

# 3d. Snapshot + commit + push (only if HAS_SOURCE and apply was clean)
#
# CRITICAL: if apply had ANY failures, we skip snapshot entirely.
# Why: snapshot would regenerate the manifest from the current (divergent) state,
# and git-sync would commit+push it — effectively propagating the failed-apply
# state as "new truth" to all other machines. A transient install failure on
# one machine could uninstall a plugin from all machines. NEVER do that.
#
# If apply failed, we also update the timestamp so we don't retry on every
# single session (which would be thrashy). Next scheduled sync (or manual
# PEDRO_PLUGINS_FORCE_SYNC=1) will retry.
if [ "$APPLY_EXIT" -ne 0 ]; then
  if [ "$APPLY_EXIT" -eq 255 ]; then
    log "⚠ apply teve erro fatal — snapshot pulado, estado local preservado"
  else
    log "⚠ apply teve $APPLY_EXIT operação(ões) com falha — snapshot pulado pra evitar propagação de estado degradado"
    log "   investigue as falhas acima e rode 'PEDRO_PLUGINS_FORCE_SYNC=1 bash $(basename "$0")' pra tentar novamente"
  fi
  touch "$LAST_SYNC_FILE"
  exit 0
fi

if [ "$HAS_SOURCE" -eq 1 ] && [ -x "$SNAPSHOT_SH" ]; then
  # Capture stdout only — snapshot.sh prints "changed"/"unchanged" on stdout,
  # log messages on stderr. Merging them creates ordering ambiguity.
  SNAPSHOT_STATUS="$(bash "$SNAPSHOT_SH" 2>/dev/null)"
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
