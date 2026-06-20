#!/bin/bash
# pretooluse-doc-guard.sh — safety net (RF8).
# When a blind search (Grep/Glob, or Bash running grep|rg|find|...) is about to run in a project
# that has project-doc documentation, DENY it once per session and redirect to .claude/docs/.
# Mirrors the graphify-guard; uses a SEPARATE sentinel so graph and doc each nudge at most once
# per session (≤1 block per source). Covers the monorepo-container case.
# Fail-open: any error → exit 0 (search proceeds).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

# Build the list of candidate dirs that this search might touch.
CANDS="$CWD"
case "$TOOL" in
  Grep|Glob)
    P=$(printf '%s' "$INPUT" | jq -r '.tool_input.path // empty' 2>/dev/null)
    [ -n "$P" ] && CANDS="$CANDS
$P"
    ;;
  Bash)
    CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    # only intercept blind text/file search; everything else passes
    printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]_])(grep|egrep|fgrep|rg|ripgrep|ag|ack|find)([^[:alnum:]_]|$)' || exit 0
    for tok in $CMD; do
      case "$tok" in -*) continue ;; esac
      cand="$tok"; case "$cand" in /*) : ;; *) cand="$CWD/$tok" ;; esac
      [ -e "$cand" ] && CANDS="$CANDS
$cand"
    done
    ;;
  *)
    exit 0
    ;;
esac

# Once-per-session: separate sentinel from the graphify guard.
SENTINEL="/tmp/claude-doc-guard-${SESSION}"
[ -f "$SENTINEL" ] && exit 0

# Nearest ancestor of a dir that owns project-doc documentation.
find_doc_up() {
  local d="$1"
  case "$d" in /*) : ;; *) d="$CWD/$d" ;; esac
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    [ -f "$d/.claude/CLAUDE.md" ] && { printf '%s' "$d"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}

# 1) check each candidate by walking up
PROJ=""
while IFS= read -r c; do
  [ -z "$c" ] && continue
  p=$(find_doc_up "$c") && { PROJ="$p"; break; }
done <<EOF
$CANDS
EOF

# 2) container fallback: descend from CWD to catch docs living in subprojects
if [ -z "$PROJ" ]; then
  LINE0=$(bash "$SCRIPT_DIR/doc-detect.sh" "$CWD" 2>/dev/null | head -1)
  [ -n "$LINE0" ] && PROJ=$(printf '%s' "$LINE0" | cut -f2)
fi

# No doc covers this search → let it through WITHOUT burning the sentinel.
[ -z "$PROJ" ] && exit 0

LINE=$(bash "$SCRIPT_DIR/doc-detect.sh" --one "$PROJ" 2>/dev/null)
[ -z "$LINE" ] && exit 0
N=$(printf '%s' "$LINE" | cut -f3)

# We're about to nudge — mark it so the rest of the session is silent.
touch "$SENTINEL" 2>/dev/null

MSG="📚 ${PROJ} tem documentação project-doc (${N} doc(s) em .claude/docs/). Antes de busca cega (grep/glob/find), leia o índice ${PROJ}/.claude/CLAUDE.md e o doc relevante em .claude/docs/ — cobre stack, arquitetura, gotchas, deploy. Se a doc não cobrir o que precisa, refaça esta busca — este aviso é único por sessão."

jq -n --arg r "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
