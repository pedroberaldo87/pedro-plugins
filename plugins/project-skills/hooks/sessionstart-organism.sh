#!/bin/bash
# sessionstart-organism.sh — consciência de ORGANISMO desde a abertura da sessão.
#
# Se o cwd está dentro de um organismo (tem .claude/organism.yaml no cwd ou num
# ancestral), injeta um heads-up que enquadra o trabalho como UM organismo, não
# N ilhas — com a regra de ouro e as costuras conhecidas. É o vetor "hooks" do
# de-silo: o pertencimento não depende do agente ir ler a doc-mestra.
#
# NÃO substitui o gate (pré-Edit) — este é o enquadramento passivo no início;
# o gate é o checkpoint ativo no momento do edit. Camadas complementares.
# Fail-open: qualquer erro → exit 0 sem output.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORGANISM_PY="$SCRIPT_DIR/../lib/organism.py"
command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
python3 --version >/dev/null 2>&1 || exit 0
[ -f "$ORGANISM_PY" ] || exit 0

INPUT=$(cat 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

BRIEF=$(python3 "$ORGANISM_PY" brief "$CWD" 2>/dev/null)
[ -z "$BRIEF" ] && exit 0
printf '%s' "$BRIEF" | jq -e '.organism == true' >/dev/null 2>&1 || exit 0

NAME=$(printf '%s' "$BRIEF" | jq -r '.name // "este organismo"')
NMOD=$(printf '%s' "$BRIEF" | jq -r '.modulos | length')
MODS=$(printf '%s' "$BRIEF" | jq -r '.modulos | join(", ")')
RULE=$(printf '%s' "$BRIEF" | jq -r '.golden_rule // empty')
# Lista das costuras: "• id (sev): modA↔modB↔..."
SEAMS=$(printf '%s' "$BRIEF" | jq -r '.costuras[] | "  • \(.id) (\(.severidade)): \(.modulos | join(" ↔ "))"')

CTX="🧬 Você está no organismo **${NAME}** — NÃO é uma coleção de projetos isolados. São ${NMOD} módulos (${MODS}) que se integram e se enxergam.
Regra de ouro: ${RULE}
Costuras conhecidas (mexeu numa ponta, cheque a outra — o gate te avisa no 1º edit de cada uma):
${SEAMS}
Nunca raciocine sobre um módulo como ilha. A doc-mestra do todo está em .claude/CLAUDE.md; as costuras vivem em .claude/organism.yaml."

CTX=$(printf '%b' "$CTX")
jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
exit 0
