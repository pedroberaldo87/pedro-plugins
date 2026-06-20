#!/bin/bash
# doc-detect.sh — shared helper: detect project-doc documentation (.claude/CLAUDE.md + .claude/docs/).
#
# Two modes:
#   doc-detect.sh <dir>          → descend up to 3 levels, list every project with a doc
#   doc-detect.sh --one <proj>   → report only <proj> (used by the guard)
#
# Emits TSV lines: DOC<TAB>project_dir<TAB>n_docs
# Fail-open: any error → no output, exit 0. Never blocks the caller.

# doc_line <project_dir> — print one TSV line if project_dir has a project-doc CLAUDE.md.
doc_line() {
  local PROJ="$1"
  [ -f "$PROJ/.claude/CLAUDE.md" ] || return 1
  local N
  N=$(find "$PROJ/.claude/docs" -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  printf 'DOC\t%s\t%s\n' "$PROJ" "${N:-0}"
}

# --one mode: just report the given project dir.
if [ "$1" = "--one" ]; then
  doc_line "$2"
  exit 0
fi

# descend mode: scan <dir> + up to a few levels for .claude/CLAUDE.md.
ROOT="${1:-$PWD}"
[ -d "$ROOT" ] || exit 0

DOC_FILES=$(find "$ROOT" -maxdepth 6 -type d \( -name node_modules -o -name .git \) -prune \
  -o -type f -path '*/.claude/CLAUDE.md' -print 2>/dev/null)
[ -z "$DOC_FILES" ] && exit 0

while IFS= read -r CMD; do
  [ -z "$CMD" ] && continue
  PROJ=$(dirname "$(dirname "$CMD")")   # project dir = parent of .claude
  doc_line "$PROJ"
done <<< "$DOC_FILES"
exit 0
