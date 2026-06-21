#!/bin/bash
# pretooluse-doc-guard.sh — safety net (RF8).
# When a blind search (Grep/Glob, Bash grep|rg|find|..., or a code-EXPLORING Task
# subagent) is about to run in a project that has project-doc documentation, DENY
# it once per (session × project) and redirect to .claude/docs/. The nudge lists
# the actual docs and flags staleness. Mirrors graphify-guard; separate sentinel.
# Fail-open: any error → exit 0 (action proceeds).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

# Candidate dirs this search/exploration might touch (CWD always in play).
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
    # set -f: tokenize WITHOUT glob-expanding — otherwise "*.json" in the command
    # would list the hook's own CWD and create bogus candidates. Tokens with stray
    # quotes are harmless: the [ -e ] test below drops anything that isn't a real path.
    set -f
    for tok in $CMD; do
      case "$tok" in -*) continue ;; esac
      cand="$tok"; case "$cand" in /*) : ;; *) cand="$CWD/$tok" ;; esac
      [ -e "$cand" ] && CANDS="$CANDS
$cand"
    done
    set +f
    ;;
  Agent|Task)
    # The subagent-spawn tool is "Agent" (legacy alias "Task"). Only nudge
    # code-EXPLORING subagents — they grep/read on your behalf and otherwise
    # never see the docs. Specialized agents (review, statusline, etc.) pass
    # untouched so the guard doesn't nag.
    ST=$(printf '%s' "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)
    case "$ST" in
      Explore|general-purpose|Plan|claude|"") : ;;
      *) exit 0 ;;
    esac
    # Task carries no path → the CWD candidate (already set) is what we check.
    ;;
  *)
    exit 0
    ;;
esac

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

# No doc covers this → let it through.
[ -z "$PROJ" ] && exit 0

# Sentinel = "doc consulted (or gave up)" — per (session × PROJECT). It is set
# when Claude actually READS the doc (posttooluse-doc-read.sh touches it), OR
# after MAX_NUDGES blind searches. So the guard INSISTS until the doc is read,
# then goes quiet — without nagging forever when the doc is irrelevant.
PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
SENTINEL="/tmp/claude-doc-guard-${SESSION}-${PHASH}"
[ -f "$SENTINEL" ] && exit 0

MAX_NUDGES=3
COUNT_FILE="/tmp/claude-doc-guard-count-${SESSION}-${PHASH}"
COUNT=0
[ -f "$COUNT_FILE" ] && COUNT="$(cat "$COUNT_FILE" 2>/dev/null)"
[ "$COUNT" -eq "$COUNT" ] 2>/dev/null || COUNT=0
if [ "$COUNT" -ge "$MAX_NUDGES" ]; then
  touch "$SENTINEL" 2>/dev/null   # gave up after MAX_NUDGES without a doc read
  exit 0
fi
echo $((COUNT + 1)) > "$COUNT_FILE"

LINE=$(bash "$SCRIPT_DIR/doc-detect.sh" --one "$PROJ" 2>/dev/null)
[ -z "$LINE" ] && exit 0
N=$(printf '%s' "$LINE" | cut -f3)
STALE=$(printf '%s' "$LINE" | cut -f4)
NUDGE_NO=$((COUNT + 1))

# List the real docs so the nudge is actionable (not just "read the index").
DOCLIST=$(for f in "$PROJ/.claude/docs"/*.md; do [ -e "$f" ] && basename "$f"; done | paste -sd ', ' -)
[ -n "$DOCLIST" ] && DOCLIST=" Docs: ${DOCLIST}."

# Staleness flag: the doc may not reflect current code.
STALEMSG=""
if [ -n "$STALE" ] && [ "$STALE" -gt 8 ] 2>/dev/null; then
  STALEMSG=" ⚠️ ${STALE} arquivo(s) mudaram desde a geração da doc — pode estar defasada; confirme no código e considere /project-doc."
fi

MSG="📚 ${PROJ} tem documentação project-doc (${N} doc(s) em .claude/docs/).${DOCLIST} Antes de busca cega ou de delegar exploração, leia o índice ${PROJ}/.claude/CLAUDE.md e o doc relevante em .claude/docs/.${STALEMSG} Eu paro de avisar assim que você LER a doc (Read em .claude/docs/ ou no CLAUDE.md); se ela não cobrir o que precisa, refaça a ação (aviso ${NUDGE_NO}/${MAX_NUDGES} — depois disso eu silencio)."

jq -n --arg r "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
