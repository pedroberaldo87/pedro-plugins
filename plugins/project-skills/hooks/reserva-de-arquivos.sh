#!/bin/sh
# reserva-de-arquivos.sh — dois motores da mesma sessão param de disputar os
# mesmos arquivos.
#
# Por que existe: no /sovai mais de um motor pode estar vivo ao mesmo tempo na
# mesma sessão. Sem nada no meio, os dois escrevem os MESMOS arquivos e um
# apaga o trabalho do outro — o dono está ausente, então ninguém vê acontecer.
#
# A regra é uma só: quem vai trabalhar REGISTRA antes a lista de arquivos que
# vai tocar. O segundo motor que chegar com uma lista que CRUZA com a de um
# motor vivo é RECUSADO. Lista disjunta passa — o gate não serializa a sessão,
# só separa quem se encosta.
#
#   reserva-de-arquivos.sh reservar <sessao> <motor> <arquivo> [<arquivo>...]
#   reserva-de-arquivos.sh liberar  <sessao> <motor>
#
# Saída, no protocolo de hook deste repo: MUDO quando reserva (exit 0), e um
# `permissionDecision: deny` com o motivo quando recusa (exit 0 também — o
# veredito vem do JSON, não do código de saída).
#
# Estado: um arquivo por (sessão, motor) em ${CLAUDE_CONFIG_DIR:-~/.claude}/sovai/
# reservas/, uma linha por caminho. NUNCA dentro do plugin: ${CLAUDE_PLUGIN_ROOT}
# é cache reescrito a cada bump de versão.
#
# A RESERVA EXPIRA POR IDADE, e o desenho é o mesmo que o sinal `ativo-<sid>`
# ganhou em 2026-08-06 (SOVAI_TTL_MIN em pretooluse-motor-arma.sh): expira,
# APAGA, e deixa linha em log. Motor que morre sem liberar deixaria uma reserva
# órfã, e reserva órfã que não expira recusa todo motor seguinte PARA SEMPRE —
# é o defeito do sinal com outro nome.
#
# FAIL-OPEN em toda borda de infra (sem argumento, sem raiz de estado, sem
# leitor de JSON): gate que trava a sessão por infra é pior que gate nenhum.

# Kill-switch (contrato dos hooks deste repo).
[ "${SOVAI_RESERVA:-1}" = "0" ] && exit 0

HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
# Sem como EMITIR a recusa não há recusa a fazer — libera.
type hj_deny >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "reserva-de-arquivos"; exit 0; }

VERBO="$1"; SESSAO="$2"; MOTOR="$3"
[ -n "$VERBO" ] && [ -n "$SESSAO" ] && [ -n "$MOTOR" ] || exit 0
shift 3

# O nome do arquivo de estado não pode carregar o que o chamador mandou: `/` ou
# `..` num id viraria escrita fora do diretório de estado.
limpa() { printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '_'; }

ESTADO="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"
RESERVAS="$ESTADO/reservas"
# A disputa que existe é DENTRO da sessão, e a reserva é por sessão pela mesma
# razão que o sinal `ativo-<sid>`: marcador global foi o defeito que mordeu o
# context-guard e o scope-cop — uma sessão trabalhando faria toda sessão
# paralela ser recusada nos arquivos dela.
EU="$(limpa "$SESSAO")"
MINHA="$RESERVAS/${EU}__$(limpa "$MOTOR").files"

mkdir -p "$RESERVAS" 2>/dev/null || exit 0

case "$VERBO" in
  liberar)
    rm -f "$MINHA" 2>/dev/null
    exit 0
    ;;
  reservar) ;;
  *) exit 0 ;;
esac

[ "$#" -gt 0 ] || exit 0            # sem lista não há o que reservar

LISTA=$(printf '%s\n' "$@")

# 12h, como o sinal: a missão que isto protege é longa por definição (o dono
# está ausente), e janela curta liberaria arquivo no meio de uma escrita viva.
SOVAI_RESERVA_TTL_MIN="${SOVAI_RESERVA_TTL_MIN:-720}"

CRUZOU=""
DONO=""
for OUTRA in "$RESERVAS/${EU}__"*.files; do
  [ -f "$OUTRA" ] || continue       # glob sem casar vem literal
  [ "$OUTRA" = "$MINHA" ] && continue

  # Expiração — reserva velha não recusa, e some. Apaga em vez de só ignorar:
  # ignorada, ela ressuscitaria na consulta seguinte.
  if [ -n "$(find "$OUTRA" -mmin +"$SOVAI_RESERVA_TTL_MIN" 2>/dev/null)" ]; then
    printf '%s reserva expirou apos %s min · %s\n' \
      "$(date -u +%FT%TZ)" "$SOVAI_RESERVA_TTL_MIN" "${OUTRA##*/}" \
      >> "$ESTADO/reservas-expiradas.log" 2>/dev/null
    rm -f "$OUTRA" 2>/dev/null
    continue
  fi

  # Casamento por LINHA INTEIRA e texto literal: `grep` solto trataria o
  # caminho como regex e faria `a/b.sh` casar com `a/bXsh`.
  CRUZOU=$(printf '%s\n' "$LISTA" | grep -F -x -f "$OUTRA" 2>/dev/null)
  if [ -n "$CRUZOU" ]; then
    DONO="${OUTRA##*/}"; DONO="${DONO%.files}"
    break
  fi
done

if [ -n "$CRUZOU" ]; then
  hj_deny "⛔ Estes arquivos já estão reservados por outro motor vivo desta sessão ($DONO):

$CRUZOU

Dois motores escrevendo o mesmo arquivo é um apagando o trabalho do outro, sem
ninguém por perto pra ver. Espere o outro motor terminar (ele libera a reserva
ao sair), ou recorte esta tarefa para uma lista de arquivos que não encoste na
dele.

Se este bloqueio estiver errado, o desligamento é SOVAI_RESERVA=0."
  exit 0
fi

printf '%s\n' "$LISTA" > "$MINHA" 2>/dev/null
exit 0
