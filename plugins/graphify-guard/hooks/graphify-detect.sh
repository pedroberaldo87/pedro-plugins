#!/bin/bash
# graphify-detect.sh — shared helper: detect graphify knowledge graph(s) and report freshness.
#
# Two modes:
#   graphify-detect.sh <dir>          → descend up to 3 levels, list every graphify-out/ found
#   graphify-detect.sh --one <proj>   → report only <proj>/graphify-out/ (used by the guard)
#
# Emits TSV lines: GRAPH<TAB>project_dir<TAB>fresh|stale<TAB>n_changed<TAB>build_date
# Fail-open: any error → no output, exit 0. Never blocks the caller.

# Source-file extensions that count as "newer than the graph" → graph is stale.
SRC_EXT=( -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' \
  -o -name '*.mjs' -o -name '*.cjs' -o -name '*.py' -o -name '*.go' \
  -o -name '*.rs' -o -name '*.java' -o -name '*.rb' -o -name '*.php' \
  -o -name '*.vue' -o -name '*.svelte' -o -name '*.sql' -o -name '*.md' )

PRUNE=( -name node_modules -o -name .git -o -name graphify-out \
  -o -name dist -o -name build -o -name .next -o -name .venv )

# freshness_line <project_dir> — print one TSV line if project_dir has a graph.
freshness_line() {
  local PROJ="$1"
  local GJSON="$PROJ/graphify-out/graph.json"
  [ -f "$GJSON" ] || return 1
  local DATE N STATE
  DATE=$(stat -f "%Sm" -t "%Y-%m-%d" "$GJSON" 2>/dev/null \
    || stat -c "%y" "$GJSON" 2>/dev/null | cut -d' ' -f1)
  # count source files newer than the graph (capped at 200 for speed)
  N=$(find "$PROJ" \( "${PRUNE[@]}" \) -prune -o -type f \( "${SRC_EXT[@]}" \) \
        -newer "$GJSON" -print 2>/dev/null | head -200 | wc -l | tr -d ' ')
  if [ "${N:-0}" -gt 0 ] 2>/dev/null; then STATE="stale"; else STATE="fresh"; fi
  printf 'GRAPH\t%s\t%s\t%s\t%s\n' "$PROJ" "$STATE" "${N:-0}" "${DATE:-?}"
}

# --one mode: just report the given project dir.
if [ "$1" = "--one" ]; then
  freshness_line "$2"
  exit 0
fi

# descend mode: scan <dir> + up to 3 levels for graphify-out/ dirs.
ROOT="${1:-$PWD}"
[ -d "$ROOT" ] || exit 0

GRAPH_DIRS=$(find "$ROOT" -maxdepth 3 \( -name node_modules -o -name .git \) -prune \
  -o -type d -name graphify-out -print 2>/dev/null)
[ -z "$GRAPH_DIRS" ] && exit 0

while IFS= read -r GDIR; do
  [ -z "$GDIR" ] && continue
  [ -f "$GDIR/graph.json" ] || continue
  freshness_line "$(dirname "$GDIR")"
done <<< "$GRAPH_DIRS"
exit 0
