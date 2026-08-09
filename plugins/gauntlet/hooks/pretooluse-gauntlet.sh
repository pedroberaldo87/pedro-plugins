#!/bin/bash
# pretooluse-gauntlet.sh — a TRAVA DUPLA do juiz: entrega sem veredito trava o despacho.
#
# PreToolUse em Agent. Enquanto houver missão armada E alguma peça entregue sem juiz,
# o único agente que pode nascer é o juiz de uma peça pendente. Fora disso, é mudo.
#
# Por que existe: a falha que motivou a skill inteira foi um orquestrador que leu
# relatórios de sete construtores e aceitou todos, sem lançar juiz nenhum. A primeira
# versão desta trava resolvia negando TODO sub-agente e mandando o trabalho para um
# motor fechado (a tool Workflow) — e o dono derrubou a caixa fechada (2026-08-09):
# a disputa agora roda como equipe visível, despachada pela própria conversa. O que
# esta versão preserva é o essencial: o esquecimento do juiz continua IMPOSSÍVEL,
# não só proibido — quem responde é o disco (`fecho_check.py pendentes`), nunca a
# memória de quem despacha.
#
# Três saídas, e a diferença entre elas é o disco:
#
#   A) sinal ausente            -> exit 0, mudo. Não há missão.
#   B) missão sem pendência     -> exit 0. Qualquer agente pode nascer.
#   C) entrega sem veredito     -> DENY a tudo que não seja o juiz dela.
#      O juiz se apresenta pelo marcador `[gauntlet:juiz:<peça>]` no prompt.
#
# O sinal é por SESSÃO (`ativo-<session_id>`). Marcador global faria uma sessão em
# gauntlet tirar de toda sessão paralela o direito de despachar sub-agente — é o
# defeito que já mordeu dois outros guardas deste repositório.
#
# FAIL-OPEN em toda borda de infra (sem leitor de evento, sem session_id, sem raiz
# de estado): guarda que trava a sessão por causa da própria infra é pior que guarda
# nenhum.
#
# DEGRADA, não trava: depois de MAX_BLOQUEIOS negações na mesma sessão ele desiste e
# libera, gravando a desistência. O cenário é missão longa com o dono fora — e nele,
# guarda que trava de verdade custa mais do que o defeito que ele evita.
#
# EXPIRA por idade: sessão que morre sem apagar o sinal deixaria o guarda aceso para
# sempre. Passado o prazo, a primeira consulta o remove e registra a linha.
#
# Desligamento: GAUNTLET_GATE=0.

set -u

[ "${GAUNTLET_GATE:-1}" = "0" ] && exit 0

HJ_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null || exit 0
type hj_campo >/dev/null 2>&1 || exit 0
type hj_deny >/dev/null 2>&1 || exit 0
# Sem jq E sem python3 não há como ler o evento. Sair calado aqui é o defeito que o
# leitor de evento existe para corrigir: o guarda tem que dizer que não julgou.
if ! command -v jq >/dev/null 2>&1 && ! { command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; }; then
  type hj_avisa >/dev/null 2>&1 && hj_avisa "pretooluse-gauntlet"
  exit 0
fi

INPUT=$(cat 2>/dev/null)
[ -n "$INPUT" ] || exit 0

SESSION=$(hj_campo "$INPUT" session_id)
[ -n "$SESSION" ] || exit 0

# A casa do sinal é a NEUTRA: é a mesma que a skill acende e a mesma que a barra de
# status lê (`lib/andamento.py`). Pasta com nome de plugin deixava cada motor com um
# sinal só dele, e a barra muda para todos menos um.
RAIZ="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"
[ -d "$RAIZ" ] || exit 0
SINAL="$RAIZ/ativo-$SESSION"
[ -f "$SINAL" ] || exit 0

# O sinal é compartilhado, então quem guarda é o NOME escrito nele: missão de outro
# motor na mesma casa não pode ser negada com a mensagem deste aqui.
[ "$(head -n 1 "$SINAL" 2>/dev/null)" = "gauntlet" ] || exit 0

# A segunda linha do sinal é o diretório da missão — é nele que a pendência mora.
# A barra de status lê só a primeira linha (`andamento.py:_motor` usa readline),
# então a segunda é canal livre. Sem ela, ou sem o diretório no disco, FAIL-OPEN:
# guarda que trava por causa da própria infra é pior que guarda nenhum.
MISSAO="$(sed -n 2p "$SINAL" 2>/dev/null)"
[ -n "$MISSAO" ] && [ -d "$MISSAO" ] || exit 0

# O sinal expira por idade. A janela é larga de propósito: a missão que ele protege
# é longa por definição, e encurtá-la mataria execução legítima em andamento.
TTL_MIN="${GAUNTLET_TTL_MIN:-720}"
AGORA=$(date +%s 2>/dev/null || echo 0)
NASCEU=$(date -r "$SINAL" +%s 2>/dev/null || stat -c %Y "$SINAL" 2>/dev/null || echo "$AGORA")
if [ "$AGORA" -gt 0 ] && [ $(( (AGORA - NASCEU) / 60 )) -gt "$TTL_MIN" ]; then
  rm -f "$SINAL" "$RAIZ/bloqueios-$SESSION"
  printf '%s expirou apos %s min\n' "$SINAL" "$TTL_MIN" >> "$RAIZ/expirados.log" 2>/dev/null
  exit 0
fi

# A pergunta é do DISCO, nunca da memória: qual peça está entregue e sem juiz?
# Sem python que execute, ou com o conferente fora do lugar, FAIL-OPEN falando.
LIB="$HJ_DIR/../lib/fecho_check.py"
[ -f "$LIB" ] || exit 0
PY=$(hj_py 2>/dev/null) || exit 0
PENDENTES=$("$PY" "$LIB" pendentes "$MISSAO" 2>/dev/null)
[ -n "$PENDENTES" ] || exit 0

# Há pendência. O único agente com passagem é o juiz de uma peça pendente — ele se
# apresenta pelo marcador no próprio prompt, que é a única coisa que o evento traz.
PROMPT=$(hj_campo "$INPUT" tool_input.prompt)
while IFS= read -r PECA; do
  [ -n "$PECA" ] || continue
  case "$PROMPT" in
    *"[gauntlet:juiz:$PECA]"*) exit 0 ;;
  esac
done <<EOF_PECAS
$PENDENTES
EOF_PECAS

CONTADOR="$RAIZ/bloqueios-$SESSION"
N=$(cat "$CONTADOR" 2>/dev/null || echo 0)
case "$N" in ''|*[!0-9]*) N=0 ;; esac
MAX="${GAUNTLET_MAX_BLOQUEIOS:-3}"

if [ "$N" -ge "$MAX" ]; then
  printf '%s desistiu apos %s negacoes\n' "$SESSION" "$N" >> "$RAIZ/desistencias.log" 2>/dev/null
  exit 0
fi

printf '%s' $(( N + 1 )) > "$CONTADOR" 2>/dev/null

LISTA=$(printf '%s' "$PENDENTES" | tr '\n' ' ')
hj_deny "⛔ Trava dupla do gauntlet: há entrega SEM JUIZ, e nada mais nasce antes dele.

Peça(s) entregue(s) esperando veredito: $LISTA

Foi assim que sete construtores foram aceitos sem juiz nenhum — a skill existe por
causa disso. Despache AGORA o juiz da peça pendente, com o marcador no prompt:

  [gauntlet:juiz:<peça>]

O juiz nasce cego: sem lista de defeitos, forma juízo antes de ler o relatório do
construtor, e o veredito é nulo sem os dois registros (o nosso e o do alvo).

Conferir a pendência: python3 <plugin>/lib/fecho_check.py pendentes <a missão>
Se este bloqueio estiver errado, o desligamento é GAUNTLET_GATE=0."
exit 0
