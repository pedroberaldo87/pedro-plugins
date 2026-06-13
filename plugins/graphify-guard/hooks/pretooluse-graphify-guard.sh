#!/bin/bash
# pretooluse-graphify-guard.sh — safety net.
# When a blind search (Grep/Glob, or Bash running grep|rg|find|...) is about to run inside
# a project that has a graphify graph, DENY it once per session and redirect to `graphify query`.
# Fail-open: any error → exit 0 (search proceeds).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

# Decide the search target dir + whether this call is a "blind search" at all.
TARGET="$CWD"
case "$TOOL" in
  Grep|Glob)
    P=$(printf '%s' "$INPUT" | jq -r '.tool_input.path // empty' 2>/dev/null)
    [ -n "$P" ] && TARGET="$P"
    ;;
  Bash)
    CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    # only intercept blind text/file search; everything else (incl. `graphify ...`) passes
    printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]_])(grep|egrep|fgrep|rg|ripgrep|ag|ack|find)([^[:alnum:]_]|$)' || exit 0
    ;;
  *)
    exit 0
    ;;
esac

# Make TARGET absolute (Grep/Glob paths may be relative to CWD).
case "$TARGET" in
  /*) : ;;
  *)  TARGET="$CWD/$TARGET" ;;
esac

# Once-per-session: if we've already nudged, let everything through.
SENTINEL="/tmp/claude-graphify-guard-${SESSION}"
[ -f "$SENTINEL" ] && exit 0

# Find the nearest ancestor of TARGET that owns a graph (cheap: stat while walking up).
PROJ=""
d="$TARGET"
while [ -n "$d" ] && [ "$d" != "/" ]; do
  if [ -f "$d/graphify-out/graph.json" ]; then PROJ="$d"; break; fi
  d=$(dirname "$d")
done

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
