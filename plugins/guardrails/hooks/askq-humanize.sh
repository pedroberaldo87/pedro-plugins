#!/bin/bash
# askq-humanize.sh — a pergunta com opções só chega no usuário se ela se explicar.
#
# O defeito relatado pelo usuário: a pergunta usa nome que só o modelo conhece, deixa a
# premissa de fora, e a opção vem como rótulo seco sem dizer o que causa. A regra
# contra isso já existe em prosa no CLAUDE.md ("PERGUNTAR SEM ARTEFATO DE APOIO")
# e não pegava — regra em prosa apodrece, recorte não.
#
# Este hook NÃO reescreve a pergunta. Ele devolve pro modelo com a lista do que
# faltou, e o modelo reescreve. Decisão do usuário em 2026-07-30: reescritor por LLM
# custaria espera antes da tela abrir e poderia inventar contexto que o modelo
# nunca teve.
#
# CONTRATO DE GATE (ver .claude/docs/patterns.md → "Contrato dos hooks"):
#   canal      permissionDecision:"deny" em JSON no stdout, com exit 0
#   cap        3 devoluções por sessão — depois vira silêncio
#   desligar   ASKQ_GATE=0
#   fail-open  sem jq, sem python3, sem session_id, sem o lint → exit 0 calado
#
# O julgamento continua sendo do modelo: o lint mede as três coisas MEDÍVEIS
# (nome de código na superfície, opção sem consequência, pergunta seca sem
# artefato). "A premissa está clara?" nenhuma régua responde.
#
# Estado em ~/.claude/guardrails/ — NUNCA dentro do plugin (${CLAUDE_PLUGIN_ROOT}
# é cache reescrito a cada bump de versão).
#
# Input (stdin, JSON): session_id, cwd, tool_name, tool_input{questions[]}.

[ "${ASKQ_GATE:-1}" = "0" ] && exit 0

# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "askq-humanize"; exit 0; }
# O INTERPRETADOR SAI DO HELPER, NÃO DE `command -v python3`. No Windows não
# existe `python3` — só `python` — então o `command -v python3` cravado devolvia
# vazio e o gate desistia (fail-open) em TODA máquina Windows: um guarda instalado
# e morto, que a esteira de portabilidade acusou como "o hook não bloqueia".
# `hj_py` tenta os dois nomes E confere que o binário RESPONDE (o stub da Store
# existe e não roda), que é a mesma checagem que estava aqui em duas linhas.
PY="$(hj_py)" || exit 0

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 0
LINT="$PLUGIN_ROOT/lib/askq_lint.py"
[ -r "$LINT" ] || exit 0

INPUT="$(cat)"
SESSION_ID="$(hj_campo "$INPUT" session_id)"
# Sem session_id não dá pra escopar o cap por sessão, e cap global vaza entre
# sessões concorrentes (o bug do context-guard, v1.2.0). Melhor não frear.
[ -n "$SESSION_ID" ] || exit 0

HOOK_DIR="$HOME/.claude/guardrails"
mkdir -p "$HOOK_DIR" 2>/dev/null
LOG_FILE="$HOOK_DIR/askq.log"

# Rotação, no molde do scope-cop (o log dele já passou de 450 KB).
if [ -f "$LOG_FILE" ]; then
  LC="$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)"
  if [ "$LC" -gt 3000 ] 2>/dev/null; then
    tail -n 1000 "$LOG_FILE" > "$LOG_FILE.tmp" 2>/dev/null && mv "$LOG_FILE.tmp" "$LOG_FILE"
  fi
fi

# Captura o exit code ANTES de qualquer pipe (num pipeline $? é do ÚLTIMO comando).
VIOL="$(printf '%s' "$INPUT" | "$PY" "$LINT" 2>/dev/null)"; RC=$?

# O input CRU vai pro log em toda invocação, limpo ou não. É o que prova que este
# evento dispara de verdade neste tool, e é o insumo pra afinar as réguas sobre
# dado real em vez de sobre suposição de formato.
{
  printf '=== %s · session=%s · rc=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$SESSION_ID" "$RC"
  printf '%s' "$(hj_campo_json "$INPUT" tool_input)" | cut -c1-4000
  [ -n "$VIOL" ] && printf '%s\n' "$VIOL"
} >> "$LOG_FILE" 2>/dev/null

# rc 0 = limpo · rc 1 = violou · qualquer outro = o lint quebrou ⇒ fail-open.
[ "$RC" -eq 1 ] || exit 0

# ── cap anti-loop, escopado por sessão ───────────────────────────────────────
COUNT_FILE="$HOOK_DIR/askq.count.${SESSION_ID}"
find "$HOOK_DIR" -maxdepth 1 -name 'askq.count.*' -mtime +1 -delete 2>/dev/null
MAX_NUDGES=3
COUNT=0
[ -f "$COUNT_FILE" ] && COUNT="$(tr -d '[:space:]' < "$COUNT_FILE" 2>/dev/null)"
case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
[ "$COUNT" -ge "$MAX_NUDGES" ] && exit 0
echo $((COUNT + 1)) > "$COUNT_FILE" 2>/dev/null

MSG="$(cat <<EOF
⛔ A pergunta não se explica sozinha.  (aviso $((COUNT + 1))/${MAX_NUDGES})

$VIOL

O usuário lê SÓ a pergunta na tela. Ele não estava no seu raciocínio, não viu o
arquivo que você abriu, e não sabe o nome que você deu pras coisas. Reescreva:

  1. A PERGUNTA carrega a premissa — o que provocou a decisão e o que está em
     jogo. Em linguagem humana, sem nome de código.
  2. Cada OPÇÃO diz o que ACONTECE se ele escolher. Não "Opção A", não "Rápido":
     a consequência concreta.
  3. Coisa concreta a comparar (código, layout, texto, número) vai em 'preview'
     — ele não adivinha o que você viu.

Se não há como escrever a premissa, não há pergunta a fazer — há investigação.

Desligar este gate nesta sessão: ASKQ_GATE=0
EOF
)"

hj_deny "$MSG"
exit 0
