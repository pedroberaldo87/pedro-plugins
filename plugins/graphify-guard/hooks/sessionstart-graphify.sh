#!/bin/bash
# sessionstart-graphify.sh — proactive layer.
# If the session's project has graphify knowledge graph(s), inject a heads-up so that
# architecture/dependency questions go to `graphify query` before grep/Explore.
# Fail-open: any error → exit 0 with no output.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

LINES=$(bash "$SCRIPT_DIR/graphify-detect.sh" "$CWD" 2>/dev/null)
[ -z "$LINES" ] && exit 0

STALE_ANY=0
LIST=""
while IFS=$'\t' read -r TAG PROJ STATE N DATE; do
  [ "$TAG" = "GRAPH" ] || continue
  if [ "$STATE" = "stale" ]; then
    STALE_ANY=1
    LIST="${LIST}- ${PROJ} (⚠️ defasado: ${N} arquivo(s) mudaram desde ${DATE})\n"
  else
    LIST="${LIST}- ${PROJ} (atualizado, build ${DATE})\n"
  fi
done <<< "$LINES"

[ -z "$LIST" ] && exit 0

CTX="🕸️ Este projeto tem knowledge graph(s) graphify:\n${LIST}\nPara perguntas de arquitetura, dependências, blast radius ou \"como funciona X\", CONSULTE o grafo ANTES de grep/Explore:\n  cd <projeto> && graphify query \"sua pergunta\"\nOutros comandos: graphify path \"A\" \"B\" · graphify explain \"Nó\". O grafo é mapa, não verdade — aponta onde olhar; confirme a causa-raiz lendo o código real."
if [ "$STALE_ANY" = "1" ]; then
  CTX="${CTX}\n⚠️ Há grafo defasado acima. Ofereça ao Pedro rodar \`graphify --update\` (re-extrai só o que mudou, é barato) antes de confiar nas respostas do grafo."
fi

# expand \n escapes into real newlines, then JSON-encode safely via jq
CTX=$(printf '%b' "$CTX")
jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
exit 0
