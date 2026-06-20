#!/usr/bin/env bash
# apply.sh — applies manifest.json to local Claude Code state.
#
# Reads manifest from the first available source (in order):
#   1. Source repo (dev machine with local clone)
#   2. $CLAUDE_PLUGIN_ROOT (set by Claude Code when running as a hook)
#   3. Plugin dir relative to this script (direct invocation within cache)
#   4. Marketplace cache (consume-only with git-source marketplace)
#   5. Plugin cache glob (consume-only with path-source marketplace)
#
# Compares with current state and runs claude plugin * commands to converge.
#
# Operations (in order):
#   1. Add missing marketplaces
#   2. Install missing plugins
#   3. Uninstall plugins that are in a managed marketplace but not in manifest
#   4. Enable/disable plugins to match manifest state
#
# Never touches unmanaged marketplaces or plugins. Filters pedro-plugins always.
#
# Exit codes:
#   0 — success, zero individual failures
#   N — N individual operations failed (capped at 200)
#   255 — fatal error (manifest missing, jq missing, etc)
#
# IMPORTANT: callers MUST check exit code before trusting post-apply state.
# A non-zero exit means the current local state diverges from the manifest's
# intent and should NOT be used as a source of truth for snapshots.

set -uo pipefail

PEDRO_PLUGINS_REPO="${PEDRO_PLUGINS_REPO:-$HOME/PROGRAMACAO/PEDRO/pedro-plugins}"
KNOWN_MARKETPLACES="$HOME/.claude/plugins/known_marketplaces.json"

REL_MANIFEST="config/manifest.json"
SOURCE_MANIFEST="$PEDRO_PLUGINS_REPO/plugins/bootstrap/$REL_MANIFEST"
HOOK_MANIFEST="${CLAUDE_PLUGIN_ROOT:-}/$REL_MANIFEST"
SCRIPT_MANIFEST="$(cd "$(dirname "$0")/../.." 2>/dev/null && pwd)/$REL_MANIFEST"
MKT_CACHE_MANIFEST="$HOME/.claude/plugins/marketplaces/pedro-plugins/plugins/bootstrap/$REL_MANIFEST"

log() { echo "[pedro-plugins/apply] $*" >&2; }
info() { echo "[pedro-plugins/apply] $*"; }

# Required tools
command -v jq >/dev/null 2>&1 || { log "error: jq not found"; exit 255; }
command -v claude >/dev/null 2>&1 || { log "error: claude CLI not found"; exit 255; }

# Locate manifest — walk through candidates, pick first that exists
MANIFEST=""
for candidate in "$SOURCE_MANIFEST" "$HOOK_MANIFEST" "$SCRIPT_MANIFEST" "$MKT_CACHE_MANIFEST"; do
  if [ -n "$candidate" ] && [ -f "$candidate" ]; then
    MANIFEST="$candidate"
    break
  fi
done

# Last resort: glob the plugin cache (handles path-source marketplaces)
if [ -z "$MANIFEST" ]; then
  for candidate in "$HOME"/.claude/plugins/cache/pedro-plugins/bootstrap/*/$REL_MANIFEST; do
    if [ -f "$candidate" ]; then
      MANIFEST="$candidate"
      break
    fi
  done
fi

if [ -z "$MANIFEST" ]; then
  log "error: manifest not found. Tried:"
  log "  source:       $SOURCE_MANIFEST"
  log "  hook:         $HOOK_MANIFEST"
  log "  script:       $SCRIPT_MANIFEST"
  log "  mkt-cache:    $MKT_CACHE_MANIFEST"
  log "  plugin-cache: ~/.claude/plugins/cache/pedro-plugins/bootstrap/*/$REL_MANIFEST"
  exit 255
fi

# Validate manifest
if ! jq empty "$MANIFEST" 2>/dev/null; then
  log "error: manifest is not valid JSON: $MANIFEST"
  exit 255
fi

if [ ! -f "$KNOWN_MARKETPLACES" ]; then
  log "error: $KNOWN_MARKETPLACES not found"
  exit 255
fi

# Counters for summary
ADDED_MKT=0
INSTALLED=0
UNINSTALLED=0
ENABLED=0
DISABLED=0
FAILURES=0

# Helper: run a claude plugin command and track failures
run_claude() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    info "✓ $desc"
  else
    log "✗ FAILED: $desc (command: $*)"
    FAILURES=$((FAILURES + 1))
  fi
}

# -------- Step 1: Add missing marketplaces --------
# Get list of marketplaces in manifest
MANIFEST_MKTS="$(jq -r '.marketplaces[] | .name + "|" + .source' "$MANIFEST")"

# Get list of already-known marketplaces
KNOWN_MKT_NAMES="$(jq -r 'keys[]' "$KNOWN_MARKETPLACES")"

while IFS='|' read -r mkt_name mkt_source; do
  [ -z "$mkt_name" ] && continue
  if ! echo "$KNOWN_MKT_NAMES" | grep -qx "$mkt_name"; then
    run_claude "add marketplace $mkt_name" claude plugin marketplace add "$mkt_source"
    ADDED_MKT=$((ADDED_MKT + 1))
  fi
done <<< "$MANIFEST_MKTS"

# Refresh known marketplaces view after adds
KNOWN_MKT_NAMES="$(jq -r 'keys[]' "$KNOWN_MARKETPLACES" 2>/dev/null || echo "")"

# -------- Step 2 & 3 & 4: Compute plugin deltas --------
# Parse current installed state (dedup across scopes) via claude plugin list
CURRENT_STATE="$(claude plugin list 2>/dev/null | awk '
  /^  ❯ / { gsub(/^  ❯ /, ""); gsub(/[[:space:]]+$/, ""); current = $0; next }
  /^    Status:/ {
    status = ($0 ~ /enabled/) ? "true" : "false"
    print current "\t" status
    current = ""
  }
' | sort -u)"

# Build manifest plugin list: "plugin@marketplace\tenabled"
MANIFEST_PLUGINS="$(jq -r '
  .marketplaces[]
  | .name as $mkt
  | .plugins[]
  | .name + "@" + $mkt + "\t" + (.enabled | tostring)
' "$MANIFEST")"

# Build set of managed marketplaces (for scoping uninstalls)
MANAGED_MKTS="$(jq -r '.marketplaces[].name' "$MANIFEST")"

# -------- Step 2: Install missing plugins --------
while IFS=$'\t' read -r plugin_ref want_enabled; do
  [ -z "$plugin_ref" ] && continue
  if ! echo "$CURRENT_STATE" | awk -F'\t' -v p="$plugin_ref" '$1 == p { found=1 } END { exit !found }'; then
    run_claude "install $plugin_ref" claude plugin install "$plugin_ref"
    INSTALLED=$((INSTALLED + 1))
  fi
done <<< "$MANIFEST_PLUGINS"

# Refresh state after installs
CURRENT_STATE="$(claude plugin list 2>/dev/null | awk '
  /^  ❯ / { gsub(/^  ❯ /, ""); gsub(/[[:space:]]+$/, ""); current = $0; next }
  /^    Status:/ {
    status = ($0 ~ /enabled/) ? "true" : "false"
    print current "\t" status
    current = ""
  }
' | sort -u)"

# -------- Step 3: Uninstall plugins in managed marketplaces but not in manifest --------
while IFS=$'\t' read -r plugin_ref current_enabled; do
  [ -z "$plugin_ref" ] && continue
  # Extract marketplace
  plugin_mkt="${plugin_ref##*@}"
  # Skip pedro-plugins (self)
  [ "$plugin_mkt" = "pedro-plugins" ] && continue
  # Only consider plugins in managed marketplaces
  if ! echo "$MANAGED_MKTS" | grep -qx "$plugin_mkt"; then
    continue
  fi
  # Check if in manifest
  if ! echo "$MANIFEST_PLUGINS" | awk -F'\t' -v p="$plugin_ref" '$1 == p { found=1 } END { exit !found }'; then
    run_claude "uninstall $plugin_ref" claude plugin uninstall "$plugin_ref"
    UNINSTALLED=$((UNINSTALLED + 1))
  fi
done <<< "$CURRENT_STATE"

# Refresh state after uninstalls
CURRENT_STATE="$(claude plugin list 2>/dev/null | awk '
  /^  ❯ / { gsub(/^  ❯ /, ""); gsub(/[[:space:]]+$/, ""); current = $0; next }
  /^    Status:/ {
    status = ($0 ~ /enabled/) ? "true" : "false"
    print current "\t" status
    current = ""
  }
' | sort -u)"

# -------- Step 4: Reconcile enabled/disabled state --------
while IFS=$'\t' read -r plugin_ref want_enabled; do
  [ -z "$plugin_ref" ] && continue
  # Current state from refreshed list
  current_enabled="$(echo "$CURRENT_STATE" | awk -F'\t' -v p="$plugin_ref" '$1 == p { print $2; exit }')"
  [ -z "$current_enabled" ] && continue  # Not installed (install may have failed earlier)
  if [ "$current_enabled" != "$want_enabled" ]; then
    if [ "$want_enabled" = "true" ]; then
      run_claude "enable $plugin_ref" claude plugin enable "$plugin_ref"
      ENABLED=$((ENABLED + 1))
    else
      run_claude "disable $plugin_ref" claude plugin disable "$plugin_ref"
      DISABLED=$((DISABLED + 1))
    fi
  fi
done <<< "$MANIFEST_PLUGINS"

# -------- Summary --------
TOTAL_CHANGES=$((ADDED_MKT + INSTALLED + UNINSTALLED + ENABLED + DISABLED))

if [ "$TOTAL_CHANGES" -eq 0 ] && [ "$FAILURES" -eq 0 ]; then
  info "✓ plugins em dia (nada a fazer)"
else
  SUMMARY=""
  [ "$ADDED_MKT"  -gt 0 ] && SUMMARY="$SUMMARY +$ADDED_MKT marketplaces,"
  [ "$INSTALLED"  -gt 0 ] && SUMMARY="$SUMMARY +$INSTALLED plugins,"
  [ "$UNINSTALLED" -gt 0 ] && SUMMARY="$SUMMARY -$UNINSTALLED plugins,"
  [ "$ENABLED"    -gt 0 ] && SUMMARY="$SUMMARY +$ENABLED enabled,"
  [ "$DISABLED"   -gt 0 ] && SUMMARY="$SUMMARY +$DISABLED disabled,"
  SUMMARY="${SUMMARY%,}"
  info "✓ sync aplicado:$SUMMARY"
  if [ "$FAILURES" -gt 0 ]; then
    log "⚠ $FAILURES operações falharam — veja o log acima"
  fi
fi

# Exit with failure count (capped at 200 to stay below shell reserved range 126-165)
# 0 = clean success, N = N failed operations.
# Callers use this to decide whether local state is safe to snapshot back upstream.
if [ "$FAILURES" -gt 200 ]; then
  exit 200
fi
exit "$FAILURES"
