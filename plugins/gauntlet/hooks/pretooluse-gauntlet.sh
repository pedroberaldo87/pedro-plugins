#!/bin/bash
# pretooluse-gauntlet.sh — enquanto o gauntlet está de pé, quem julga é o motor.
#
# PreToolUse em Agent. Nega o disparo de sub-agente ENQUANTO houver missão armada,
# e é mudo fora dela.
#
# Por que existe: a falha que motivou a skill inteira foi um orquestrador que leu
# relatórios de sete construtores e aceitou todos, sem lançar juiz nenhum. A skill
# proíbe isso por escrito — e proibição por escrito foi exatamente o que falhou nas
# duas sessões reais. Este hook torna a proibição mecânica: com missão de pé, o
# caminho de sub-agente avulso não existe.
#
# Duas saídas, e a diferença entre elas é um arquivo:
#
#   A) sinal ausente  -> exit 0, mudo. Não há missão; sub-agente aqui não é assunto deste.
#   B) sinal presente -> DENY, mandando passar pelo motor.
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

INPUT=$(cat 2>/dev/null)
[ -n "$INPUT" ] || exit 0

SESSION=$(hj_campo "$INPUT" session_id)
[ -n "$SESSION" ] || exit 0

RAIZ="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/gauntlet"
[ -d "$RAIZ" ] || exit 0
SINAL="$RAIZ/ativo-$SESSION"
[ -f "$SINAL" ] || exit 0

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

CONTADOR="$RAIZ/bloqueios-$SESSION"
N=$(cat "$CONTADOR" 2>/dev/null || echo 0)
case "$N" in ''|*[!0-9]*) N=0 ;; esac
MAX="${GAUNTLET_MAX_BLOQUEIOS:-3}"

if [ "$N" -ge "$MAX" ]; then
  printf '%s desistiu apos %s negacoes\n' "$SESSION" "$N" >> "$RAIZ/desistencias.log" 2>/dev/null
  exit 0
fi

printf '%s' $(( N + 1 )) > "$CONTADOR" 2>/dev/null

hj_deny "⛔ Há uma missão do gauntlet de pé, e nela quem julga é o motor.

Sub-agente avulso não entra: foi assim que sete construtores foram aceitos sem
juiz nenhum, e a skill existe por causa disso. O laço — construtor, juiz, e o
julgamento em disco — roda pela tool Workflow, com o motor de references/motor.js.

Era só uma leitura, um parecer de UM agente? Então é um Workflow de um agente()
só, não o motor inteiro.

Terminou a missão? Quem apaga o sinal é a conferência verde:
  python3 <plugin>/lib/fecho_check.py fecho <a missao>

Se este bloqueio estiver errado, o desligamento é GAUNTLET_GATE=0."
exit 0
