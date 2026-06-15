#!/bin/bash
# pretooluse-graphify-guard.sh — safety net.
# When a blind search (Grep/Glob, or Bash running grep|rg|find|...) is about to run in a project
# that has a graphify graph, DENY it once per session and redirect to `graphify query`.
# Covers the monorepo-container case: even when cwd is a container (e.g. /VIU) with no graph of its
# own, it inspects the search path tokens and descends to find graphs in subprojects.
# Fail-open: any error → exit 0 (search proceeds).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

# Build the list of candidate dirs that this search might touch. Always include CWD; add the
# explicit search path (Grep/Glob) or any path-like token from the command (Bash).
CANDS="$CWD"
case "$TOOL" in
  Grep|Glob)
    P=$(printf '%s' "$INPUT" | jq -r '.tool_input.path // empty' 2>/dev/null)
    [ -n "$P" ] && CANDS="$CANDS
$P"
    ;;
  Bash)
    CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    # only intercept blind text/file search; everything else (incl. `graphify ...`) passes
    printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]_])(grep|egrep|fgrep|rg|ripgrep|ag|ack|find)([^[:alnum:]_]|$)' || exit 0
    # add command tokens that exist as paths, so `grep -r x VIUSTUDIO-TOOLS/` fires from /VIU
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

# Once-per-session: if we've already nudged, let everything through.
SENTINEL="/tmp/claude-graphify-guard-${SESSION}"
[ -f "$SENTINEL" ] && exit 0

# Nearest ancestor of a dir that owns a graph (cheap: stat while walking up).
find_graph_up() {
  local d="$1"
  case "$d" in /*) : ;; *) d="$CWD/$d" ;; esac
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    [ -f "$d/graphify-out/graph.json" ] && { printf '%s' "$d"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}

# 1) check each candidate by walking up
PROJ=""
while IFS= read -r c; do
  [ -z "$c" ] && continue
  p=$(find_graph_up "$c") && { PROJ="$p"; break; }
done <<EOF
$CANDS
EOF

# 2) container fallback: descend from CWD to catch graphs living in subprojects
if [ -z "$PROJ" ]; then
  LINE0=$(bash "$SCRIPT_DIR/graphify-detect.sh" "$CWD" 2>/dev/null | head -1)
  [ -n "$LINE0" ] && PROJ=$(printf '%s' "$LINE0" | cut -f2)
fi

# No graph covers this search → let it through WITHOUT burning the sentinel.
[ -z "$PROJ" ] && exit 0

LINE=$(bash "$SCRIPT_DIR/graphify-detect.sh" --one "$PROJ" 2>/dev/null)
[ -z "$LINE" ] && exit 0

STATE=$(printf '%s' "$LINE" | cut -f3)
N=$(printf '%s' "$LINE" | cut -f4)
DATE=$(printf '%s' "$LINE" | cut -f5)

# We're about to nudge — mark it so the rest of the session is silent.
touch "$SENTINEL" 2>/dev/null

MSG="🕸️ Há knowledge graph graphify em ${PROJ}. Antes de busca cega (grep/glob/find), consulte o grafo: cd ${PROJ} && graphify query \"o que você procura\" (ou graphify explain \"Nó\" / graphify path \"A\" \"B\")."
if [ "$STATE" = "stale" ]; then
  MSG="${MSG} ⚠️ Grafo defasado (${N} arquivo(s) desde ${DATE}) — considere oferecer \`graphify --update\` ao Pedro antes de confiar nele."
fi
MSG="${MSG} Se o grafo não cobrir o que precisa, refaça esta busca — este aviso é único por sessão."

jq -n --arg r "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
