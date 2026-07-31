#!/bin/bash
# sessionstart-branches.sh — avisa que há branch parada, sem virar relatório.
#
# Só a CONTAGEM, e só quando há o que dizer. O relatório inteiro é o `/branches`
# — se este hook listasse tudo, viraria parede de texto no começo de toda
# sessão e você aprenderia a pular. Aviso que se ignora não avisa nada.
#
# CONTRATO DE GATE (.claude/docs/patterns.md → §5.3):
#   canal      additionalContext — INFORMA, nunca bloqueia
#   cap        n/a (não bloqueia); só fala quando há branch parada
#   desligar   BRANCHES_GATE=0
#   fail-open  sem jq, sem python3, fora de repo → exit 0 calado

[ "${BRANCHES_GATE:-1}" = "0" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
PY3=$(command -v python3 2>/dev/null)
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BS="$SCRIPT_DIR/../lib/branch_state.py"
[ -f "$BS" ] || exit 0

ROOT=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$ROOT" ] || exit 0

OUT=$("$PY3" "$BS" --repo "$ROOT" stale --dias "${BRANCHES_DIAS:-30}" 2>/dev/null)
[ -n "$OUT" ] || exit 0

CTX=$(printf '%s' "$OUT" | jq -r '
  "🌿 Este projeto tem \(.paradas) branch(es) parada(s) há mais de \(.dias) dias"
  + (if .seguras > 0 then " — \(.seguras) dela(s) já com o conteúdo no \(.base), ou seja, seguras de apagar." else "." end)
  + "\n   " + (.nomes | join(" · "))
  + "\n\nRode /branches pra ver a classificação com a prova de cada uma (o que só existe"
  + " naquela branch aparece antes de você marcar). Nada é apagado sem você marcar,"
  + " e toda branch apagada vira uma tag de resgate.\n"
  + "   Não quer este aviso? BRANCHES_GATE=0"' 2>/dev/null)
[ -n "$CTX" ] || exit 0

jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}' 2>/dev/null
exit 0
