#!/bin/bash
# sessionstart-lembra-missao.sh — a missão que ficou pela metade volta a existir no arranque.
#
# POR QUE EXISTE. A segunda metade da falha que originou a skill foi de MEMÓRIA, e
# está medida em `references/porque.md`: houve vereditos REPROVADO em aberto, o dono
# mandou ~35 direcionamentos em duas horas, e o estado "o hero ainda está reprovado"
# evaporou — porque vivia na conversa, e a conversa foi atropelada.
#
# O disco resolveu metade disso: o veredito virou arquivo. Faltava a outra metade —
# alguém LER esse arquivo quando a sessão recomeça. Sem isto, a missão fica no disco
# e ninguém lembra dela; o sinal expira em 12 horas e some calado, e o trabalho de
# uma disputa inteira vira pasta esquecida.
#
# Ele não retoma nada sozinho: imprime onde a missão parou e deixa a decisão com o
# dono. Motor que se reinicia sozinho no arranque é como se perde controle de uma
# disputa que gasta agente.
#
# Kill-switch: GAUNTLET_GATE=0 (o mesmo da trava — é o mesmo motor).

[ "${GAUNTLET_GATE:-1}" = "0" ] && exit 0

IFS= read -r -d '' ENTRADA 2>/dev/null || true

HJ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null || exit 0
type hj_campo >/dev/null 2>&1 || exit 0
# Sem jq E sem python3 não há como ler o evento, e sair calado aqui apagaria a missão
# do arranque sem ninguém saber — que é exatamente a falha de memória que este hook
# existe para corrigir. A regra da casa é FALAR.
if ! command -v jq >/dev/null 2>&1 && ! { command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; }; then
  type hj_avisa >/dev/null 2>&1 && hj_avisa "sessionstart-lembra-missao"
  exit 0
fi

SESSION=$(hj_campo "$ENTRADA" session_id 2>/dev/null)
RAIZ="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"
[ -d "$RAIZ" ] || exit 0

# A missão pode ser desta sessão (que voltou) ou de outra que morreu. As duas
# interessam: a segunda é justamente a que ninguém lembra.
MISSAO=""
for SINAL in "$RAIZ"/ativo-*; do
  [ -f "$SINAL" ] || continue
  [ "$(head -n 1 "$SINAL" 2>/dev/null)" = "gauntlet" ] || continue
  CANDIDATA="$(sed -n 2p "$SINAL" 2>/dev/null)"
  [ -n "$CANDIDATA" ] && [ -d "$CANDIDATA" ] || continue
  MISSAO="$CANDIDATA"
  # O sinal da própria sessão ganha a vez: é a missão que o dono estava tocando.
  case "$SINAL" in *"ativo-$SESSION") break ;; esac
done
[ -n "$MISSAO" ] || exit 0

LIB="$HJ_DIR/../lib/fecho_check.py"
[ -f "$LIB" ] || exit 0
PY=$(hj_py 2>/dev/null) || exit 0

MAPA=$("$PY" "$LIB" mapa "$MISSAO" 2>/dev/null) || exit 0
[ -n "$MAPA" ] || exit 0
PEND=$("$PY" "$LIB" pendentes "$MISSAO" 2>/dev/null | tr '\n' ' ')

RECADO="🏁 Há uma missão de gauntlet ABERTA no disco — ela sobreviveu ao fim da sessão anterior.

$MAPA"
[ -n "$PEND" ] && RECADO="$RECADO
⚠️ Entrega(s) esperando juiz: $PEND — despache o juiz antes de qualquer outro agente."
RECADO="$RECADO

Retomar é continuar de onde o mapa diz; encerrar é rodar o fecho. Pergunte ao dono qual dos dois — não escolha por ele."

if type hj_msg_ctx >/dev/null 2>&1; then
  hj_msg_ctx "SessionStart" "$RECADO"
  exit 0
fi
printf '%s\n' "$RECADO" >&2
exit 0
