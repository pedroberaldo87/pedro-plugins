#!/bin/bash
# posttooluse-doc-read.sh — RESOLVE the doc-guard when Claude actually READS a
# project's documentation (.claude/docs/* or .claude/CLAUDE.md). The PreToolUse
# guard's sentinel now means "the doc was consulted", not "Claude was warned" —
# so the guard keeps nudging on blind searches until the doc is genuinely read,
# then goes quiet. Mirrors the PHASH the guard uses.
# Fail-open: any error → exit 0. Never blocks.

command -v jq >/dev/null 2>&1 || exit 0
INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL" = "Read" ] || exit 0
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
FP=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$FP" ] && exit 0
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"
# Normalize to ABSOLUTE — the guard derives PROJ absolute (find_doc_up/doc-detect),
# so a relative file_path here would hash to a different PHASH and never resolve
# the sentinel (guard would nudge forever).
case "$FP" in /*) : ;; *) FP="$CWD/$FP" ;; esac

# Only a project-doc file resolves the guard. Derive the project dir (the part
# before /.claude/) so the sentinel matches the one the guard checks.
case "$FP" in
  */.claude/docs/*)    PROJ="${FP%%/.claude/docs/*}" ;;
  */.claude/CLAUDE.md) PROJ="${FP%/.claude/CLAUDE.md}" ;;
  *) exit 0 ;;
esac
[ -n "$PROJ" ] || exit 0

PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
touch "/tmp/claude-doc-guard-${SESSION}-${PHASH}" 2>/dev/null
exit 0
