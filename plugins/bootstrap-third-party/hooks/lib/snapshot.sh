#!/usr/bin/env bash
# snapshot.sh — regenerates manifest.json from current Claude Code state.
#
# Reads: `claude plugin list`, `claude plugin marketplace list`
# Writes: $PEDRO_PLUGINS_REPO/plugins/bootstrap-third-party/skills/bootstrap-third-party/manifest.json
#
# Only runs if source repo exists. Silent no-op otherwise.
# Filters out `pedro-plugins` marketplace (never self-sync).
#
# Exit codes:
#   0 — success (manifest up-to-date or regenerated)
#   1 — error (jq missing, write failed, etc)

set -euo pipefail

PEDRO_PLUGINS_REPO="${PEDRO_PLUGINS_REPO:-$HOME/PROGRAMACAO/PEDRO/pedro-plugins}"
MANIFEST_PATH="$PEDRO_PLUGINS_REPO/plugins/bootstrap-third-party/skills/bootstrap-third-party/manifest.json"
KNOWN_MARKETPLACES="$HOME/.claude/plugins/known_marketplaces.json"

log() { echo "[pedro-plugins/snapshot] $*" >&2; }

# Early exit if no source repo
if [ ! -d "$PEDRO_PLUGINS_REPO/.git" ]; then
  exit 0
fi

# Required tools
command -v jq >/dev/null 2>&1 || { log "error: jq not found in PATH"; exit 1; }
command -v claude >/dev/null 2>&1 || { log "error: claude CLI not found in PATH"; exit 1; }

if [ ! -f "$KNOWN_MARKETPLACES" ]; then
  log "error: $KNOWN_MARKETPLACES not found"
  exit 1
fi

# Parse `claude plugin list` output into a JSON array of {name, marketplace, enabled}
# Output format is:
#   ❯ <plugin>@<marketplace>
#     Version: ...
#     Scope: ...
#     Status: ✔ enabled | ✘ disabled
#
# Plugins installed at multiple scopes appear twice — dedupe by (plugin, marketplace).
PLUGIN_STATE="$(claude plugin list 2>/dev/null | awk '
  /^  ❯ / {
    # Extract "plugin@marketplace"
    gsub(/^  ❯ /, ""); gsub(/[[:space:]]+$/, "")
    current = $0
    next
  }
  /^    Status:/ {
    status = ($0 ~ /enabled/) ? "true" : "false"
    print current "\t" status
    current = ""
  }
' | sort -u)"

if [ -z "$PLUGIN_STATE" ]; then
  log "warning: claude plugin list returned no plugins"
fi

# Build JSON of plugins per marketplace, respecting enabled state.
# Filter out pedro-plugins marketplace entirely.
PLUGINS_JSON="$(printf '%s\n' "$PLUGIN_STATE" | awk -F'\t' '
  NF == 2 {
    split($1, parts, "@")
    plugin = parts[1]
    marketplace = parts[2]
    if (marketplace == "pedro-plugins") next
    key = marketplace
    if (!(key in seen)) {
      seen[key] = 1
      order[++count] = key
    }
    entries[key] = entries[key] (entries[key] ? "," : "") \
      "{\"name\":\"" plugin "\",\"enabled\":" $2 "}"
  }
  END {
    printf "{"
    for (i = 1; i <= count; i++) {
      if (i > 1) printf ","
      printf "\"%s\":[%s]", order[i], entries[order[i]]
    }
    printf "}"
  }
')"

# Build marketplaces array by joining known_marketplaces.json with PLUGINS_JSON.
# Filter out pedro-plugins. Sort alphabetically by marketplace name. Sort plugins alphabetically within.
NEW_MANIFEST="$(jq -n \
  --slurpfile marketplaces "$KNOWN_MARKETPLACES" \
  --argjson plugins "$PLUGINS_JSON" \
  '{
    version: 1,
    description: "Third-party Claude Code marketplaces and plugins Pedro uses. Auto-synced via bootstrap-third-party hooks.",
    marketplaces: (
      $marketplaces[0]
      | to_entries
      | map(select(.key != "pedro-plugins"))
      | sort_by(.key)
      | map({
          name: .key,
          source: (
            if .value.source.source == "github" then .value.source.repo
            else .value.source.url
            end
          ),
          sourceType: .value.source.source,
          plugins: (
            ($plugins[.key] // [])
            | sort_by(.name)
          )
        })
    )
  }')"

# Compare with existing manifest. Skip write if identical.
if [ -f "$MANIFEST_PATH" ]; then
  OLD_NORMALIZED="$(jq -S . "$MANIFEST_PATH" 2>/dev/null || echo "{}")"
  NEW_NORMALIZED="$(echo "$NEW_MANIFEST" | jq -S .)"
  if [ "$OLD_NORMALIZED" = "$NEW_NORMALIZED" ]; then
    # No changes
    echo "unchanged"
    exit 0
  fi
fi

# Write new manifest atomically
TMP_FILE="$(mktemp)"
echo "$NEW_MANIFEST" | jq . > "$TMP_FILE"
mv "$TMP_FILE" "$MANIFEST_PATH"

log "manifest regenerated: $MANIFEST_PATH"
echo "changed"
exit 0
