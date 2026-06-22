#!/bin/bash
# sessionstart-doc.sh — proactive layer (RF8).
# If the session's project has project-doc documentation, inject a heads-up so that
# "how does X work / where is Y" goes to the docs before grep/Explore.
# Fail-open: any error → exit 0 with no output.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

LINES=$(bash "$SCRIPT_DIR/doc-detect.sh" "$CWD" 2>/dev/null)
[ -z "$LINES" ] && exit 0

LIST=""
while IFS=$'\t' read -r TAG PROJ N STALE OOP; do
  [ "$TAG" = "DOC" ] || continue
  FLAG=""
  if [ -n "$STALE" ] && [ "$STALE" -gt 8 ] 2>/dev/null; then
    FLAG=" ⚠️ ${STALE} arquivo(s) mudaram desde a geração — pode estar defasada (/project-doc atualiza)"
  fi
  if [ "$OOP" = "1" ]; then
    FLAG="${FLAG} ⚠️ fora do padrao atual (gen) — nao confie cegamente, considere /project-doc"
  fi
  LIST="${LIST}- ${PROJ}/.claude/CLAUDE.md (${N} doc(s) em .claude/docs/)${FLAG}\n"
done <<< "$LINES"

[ -z "$LIST" ] && exit 0

CTX="📚 Este projeto tem documentação project-doc:\n${LIST}\nAntes de explorar com grep/Glob/Explore, LEIA o índice CLAUDE.md e o doc relevante em .claude/docs/ — cobre stack, arquitetura, gotchas, deploy. A doc é agent-facing (feita pra você consumir). Atualizar: /project-doc."

# expand \n escapes into real newlines, then JSON-encode safely via jq
CTX=$(printf '%b' "$CTX")
jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
exit 0
