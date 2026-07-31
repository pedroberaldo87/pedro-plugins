#!/bin/bash
# stop-plan-status.sh — "onde nós estamos", ao fim de cada turno.
#
# Emite 1-3 bullets curtos com o progresso do plano ativo, e — quando tudo
# fechou — uma confirmação INEQUÍVOCA de conclusão. O texto NÃO mora aqui:
# vem de `plan_state.py brief`, porque texto em heredoc de shell não é testável
# e este mesmo texto precisa servir pro hook e pra quem chamar na mão.
#
# Dobra também a cobrança do tique (era o stop-plan-nudge.sh): quando a sessão
# escreveu código e não marcou nada, entra UM bullet a mais, 1× por sessão.
# Um hook só em vez de dois — dois `systemMessage` no mesmo Stop competiriam.
#
# CONTRATO DE GATE (.claude/docs/patterns.md → §5.3):
#   canal      systemMessage (informa, não bloqueia — nunca emite decision:block)
#   cap        n/a (não bloqueia); a COBRANÇA é 1× por (sessão, projeto)
#   desligar   PLAN_STATUS=0  (e PLAN_NUDGE=0 desliga só a cobrança)
#   fail-open  sem jq, sem python3, sem plano → exit 0 calado
#
# O silêncio é o comportamento normal: sem plano ativo, não fala nada.

[ "${PLAN_STATUS:-1}" = "0" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
PY3=$(command -v python3 2>/dev/null)
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
# Stop disparado por stop_hook já ativo → sai (anti-loop).
ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$ACTIVE" = "true" ] && exit 0

SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAN_STATE="$SCRIPT_DIR/../lib/plan_state.py"
[ -f "$PLAN_STATE" ] || exit 0

PLANS_DIR=$(bash "$SCRIPT_DIR/../skills/visual/resolve-dir.sh" "$CWD" plans 2>/dev/null)
[ -d "$PLANS_DIR" ] || exit 0

PHASH=$(printf '%s' "$PLANS_DIR" | cksum | cut -d' ' -f1)
MARK="${TMPDIR:-/tmp}/claude-plan-mark-$(id -u)-${SESSION}-${PHASH}"

# O marco da sessão também data o "encerrado AGORA": plano fechado depois dele
# merece a confirmação final; fechado semanas atrás, não. Sem marco, só o ativo.
# AUTO-CURA (2026-07-28): antes, sem marco este hook perdia a confirmação de
# conclusão e a cobrança — calados pra sempre naquela sessão. Acontecia sempre
# que o plugin era instalado ou atualizado NO MEIO da sessão: o SessionStart,
# que cria o marco, já tinha passado.
#
# Regra geral que saiu daqui: hook que depende de OUTRO hook ter rodado é
# frágil. Se o pré-requisito é um arquivo barato, crie-o você mesmo.
MARCO_NOVO=0
if [ ! -f "$MARK" ]; then
  touch "$MARK" 2>/dev/null
  MARCO_NOVO=1
  # Recém-criado: tudo que fechou ANTES deste instante fica de fora desta vez,
  # e é o certo — não dá pra afirmar que fechou "nesta sessão".
fi
SINCE=""
[ -f "$MARK" ] && SINCE=$("$PY3" -c "import os,sys;print(os.path.getmtime(sys.argv[1]))" "$MARK" 2>/dev/null)

# O "já confirmei o encerramento" mora por (sessão, projeto): sem isso o 🏁
# reaparecia a cada turno até a sessão acabar.
SEEN="${TMPDIR:-/tmp}/claude-plan-closed-$(id -u)-${SESSION}-${PHASH}"

# ── a cobrança do tique ──────────────────────────────────────────────────────
# Só entra quando: há marco, nenhum *.plan.json foi tocado nesta sessão, e o
# transcript mostra 3+ edições. 1× por (sessão, projeto) — cobrar todo turno
# transforma o aviso em ruído, e ruído a gente aprende a ignorar.
NUDGE=""
# MARCO_NOVO=1 → o marco nasceu AGORA, então "nada foi marcado desde o marco"
# é verdade vazia: não houve intervalo. Cobrar aqui seria acusar sem base.
# A partir do turno seguinte há intervalo de verdade e a cobrança volta.
if [ "${PLAN_NUDGE:-1}" != "0" ] && [ "$MARCO_NOVO" = "0" ] && [ -f "$MARK" ] \
   && [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  SENTINEL="${TMPDIR:-/tmp}/claude-plan-nudge-$(id -u)-${SESSION}-${PHASH}"
  if [ ! -f "$SENTINEL" ]; then
    TICKED=0
    for f in "$PLANS_DIR"/*.plan.json; do
      [ -e "$f" ] || continue
      [ "$f" -nt "$MARK" ] && TICKED=1 && break
    done
    if [ "$TICKED" = "0" ]; then
      EDITS=$(grep -oE '"name":"(Edit|Write|MultiEdit|NotebookEdit)"' "$TRANSCRIPT" 2>/dev/null | wc -l | tr -d ' ')
      case "$EDITS" in ''|*[!0-9]*) EDITS=0 ;; esac
      if [ "$EDITS" -ge 3 ]; then
        touch "$SENTINEL" 2>/dev/null
        NUDGE="⚠️ **Nada marcado nesta sessão**, e ela editou ${EDITS} arquivos. Marque o que terminou com \`tick <id> --evidencia\` — senão o próximo Claude herda um plano que mente."
      fi
    fi
  fi
fi

# O brief compõe TUDO — inclusive a cobrança — porque o teto de 3 bullets é do
# pedido do usuário e precisa viver num lugar testável, não em concatenação aqui.
if [ -n "$SINCE" ]; then
  BRIEF=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" brief --closed-since "$SINCE" \
            --mark-seen "$SEEN" ${NUDGE:+--nudge "$NUDGE"} 2>/dev/null)
else
  BRIEF=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" brief ${NUDGE:+--nudge "$NUDGE"} 2>/dev/null)
fi
[ -z "$BRIEF" ] && exit 0

jq -n --arg m "$BRIEF" '{systemMessage:$m}' 2>/dev/null
exit 0
