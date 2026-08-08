#!/bin/bash
# Pre-ExitPlanMode hook — o plano só chega no CLI depois de virar HTML COM PROVA
# e de existir como ARQUIVO em .claude/plans/.
#
# Escopado por session_id. NÃO procura plano por mtime (isso casaria plano de
# outra sessão): o conteúdo vem direto de tool_input.plan.
#
# CONTRATO DE GATE (ver .claude/docs/patterns.md → "Contrato dos hooks"):
#   canal      exit 2 com o motivo no stderr
#   cap        3 devoluções por (sessão, projeto) — depois vira silêncio
#   desligar   VISUAL_GATE=0
#   fail-open  sem jq, sem session_id, sem raiz → exit 0 calado
#
# O cap é a lição de 2026-07-27: este era o ÚNICO dos três gates do modo plano
# sem teto e sem kill-switch, e o repo já perdeu um gate por loop infinito neste
# mesmo evento. Depois do teto ele degrada pra aviso — nunca prende.
#
# Input (stdin, JSON): session_id, cwd, transcript_path, tool_name,
# tool_input{plan}, hook_event_name.

[ "${VISUAL_GATE:-1}" = "0" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "pre-exitplan-visualize"; exit 0; }

INPUT=$(cat)
SESSION_ID=$(hj_campo "$INPUT" session_id)
PLAN_CONTENT=$(hj_campo "$INPUT" tool_input.plan)
CWD=$(hj_campo "$INPUT" cwd)

# Sem session_id não dá pra escopar o cap por sessão → não bloqueia (fail-open).
[ -n "$SESSION_ID" ] || exit 0
SESSION_SHORT="${SESSION_ID:0:8}"
[ -n "$CWD" ] || CWD="$PWD"

PLUGIN_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# `$?` = 3 → destino veio da RESERVA (~/Desktop), não deste projeto. O texto do
# aviso morre no 2>/dev/null; o código de saída é o canal que chega até aqui, e
# daqui ele entra no stderr do gate, que é o que o modelo de fato lê.
VISUAL_DIR=$(bash "$PLUGIN_ROOT/skills/visual/resolve-dir.sh" "$CWD" 2>/dev/null); DE_RESERVA=$?
[ -n "$VISUAL_DIR" ] || exit 0
RESERVA_AVISO=""
[ "$DE_RESERVA" = "3" ] && RESERVA_AVISO="
⚠️ '$CWD' não é projeto reconhecido: o HTML e o plano vão para a RESERVA $VISUAL_DIR, uma gaveta por pasta de origem — não para .claude/ de projeto nenhum.
"
mkdir -p "$VISUAL_DIR" 2>/dev/null

# ── cap anti-loop ────────────────────────────────────────────────────────────
# Chaveado por (sessão, projeto): estado global vaza entre sessões concorrentes
# — regra dura do repo, nascida de um bug real do context-guard.
PHASH=$(printf '%s' "$VISUAL_DIR" | cksum | cut -d' ' -f1)
COUNT_FILE="${TMPDIR:-/tmp}/claude-visual-gate-$(id -u)-${SESSION_ID}-${PHASH}"
MAX_NUDGES=3
COUNT=0
[ -f "$COUNT_FILE" ] && COUNT="$(tr -d '[:space:]' < "$COUNT_FILE" 2>/dev/null)"
case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
capped() { [ "$COUNT" -ge "$MAX_NUDGES" ]; }
bump()   { echo $((COUNT + 1)) > "$COUNT_FILE" 2>/dev/null; }

# ── o plano existe como ARQUIVO? ─────────────────────────────────────────────
# Sem isto, toda a maquinaria de plano ticável fica dormente: se o modelo não
# rodar `init`, nada reclama — e o plano volta a viver só na conversa, que é o
# modo de falha que o store veio fechar.
PLANS_DIR=$(bash "$PLUGIN_ROOT/skills/visual/resolve-dir.sh" "$CWD" plans 2>/dev/null)
# O programa do plano mora no plugin `project-skills` — achado pelo NOME, nunca por
# caminho relativo, que o cache do harness quebra. Ausente = a cobrança não roda.
PLAN_STATE=$(CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" bash "$PLUGIN_ROOT/hooks/resolve-plugin.sh" project-skills lib/plan_state.py 2>/dev/null)
HAS_PLAN_FILE=1   # 1 = não checável ou já existe → não cobra
if [ -n "$PLANS_DIR" ] && [ -f "$PLAN_STATE" ] && command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
  OPEN=$(python3 "$PLAN_STATE" --dir "$PLANS_DIR" open --json 2>/dev/null)
  case "$OPEN" in ''|'[]') HAS_PLAN_FILE=0 ;; esac
fi

# Há visual desta sessão, modificado nos últimos 5 min?
RECENT_VISUAL=$(find "$VISUAL_DIR" -maxdepth 1 -name "*sess-${SESSION_SHORT}*.html" -mmin -5 2>/dev/null | head -1)

if [ -n "$RECENT_VISUAL" ]; then
  # ── GATE DE PROVA ────────────────────────────────────────────────
  # O arquivo existir não basta: a página tem que MOSTRAR o que sustenta o que
  # ela afirma. Checagem de piso (grep), não de teto — não dá pra verificar se
  # toda afirmação tem origem, mas dá pra barrar a página no vácuo, que é o
  # modo de falha real: decisão pedida sem artefato, sem saída e sem procedência.
  # grep -c já imprime 0 quando não acha (e sai 1) — nada de "|| echo 0", que
  # somaria um segundo zero e quebraria a comparação numérica.
  # `feedback-item pt-phase` fica FORA da conta: é o veredito de fase que o
  # próprio `plan_state.py page --mode approve` desenha — o controle de aprovação
  # de trabalho que ainda não aconteceu, não uma conclusão afirmada. Contá-lo
  # fazia o gate barrar exatamente a página que ele manda gerar duas telas abaixo,
  # e o modelo ficava preso entre duas ordens do mesmo arquivo.
  DECIDE=$(grep 'class="decision-card\|class="feedback-item' "$RECENT_VISUAL" 2>/dev/null \
           | grep -vc 'class="feedback-item pt-phase')
  PROVA=$(grep -c 'class="evidencia"\|class="artefato"\|<pre' "$RECENT_VISUAL" 2>/dev/null)
  VAZIO=$(grep -c 'class="evidencia vazio' "$RECENT_VISUAL" 2>/dev/null)
  ISENTO=$(grep -c 'visual-sem-evidencia:' "$RECENT_VISUAL" 2>/dev/null)
  DECIDE=${DECIDE:-0}; PROVA=${PROVA:-0}; VAZIO=${VAZIO:-0}; ISENTO=${ISENTO:-0}

  if [ "$DECIDE" -gt 0 ] && [ "$ISENTO" -eq 0 ] && { [ "$PROVA" -eq 0 ] || [ "$VAZIO" -gt 0 ]; }; then
    capped && exit 0
    bump
    cat >&2 << EVIDENCIA
⛔ VISUAL GATE — a página pede decisão sem mostrar a prova.  (aviso $((COUNT + 1))/${MAX_NUDGES})

Arquivo: $RECENT_VISUAL
  blocos de decisão .... $DECIDE
  blocos de prova ...... $PROVA   (.evidencia / .artefato / <pre>)
  prova em branco ...... $VAZIO

O usuário lê SÓ esta página. Descrever o que você viu não serve — ele precisa VER
o que te fez concluir. Antes de chamar ExitPlanMode de novo, acrescente:

  1. .ident-strip  — projeto, artefato PELO TÍTULO VISÍVEL, e o estado dele
                     (rascunho / gerado / no ar / já apresentado)
  2. .artefato     — o objeto real embutido:
                     <iframe src="file:///caminho/absoluto/real"></iframe>
                     PROIBIDO fabricar uma versão "corrigida" por find-and-replace
  3. .evidencia    — a saída CRUA que produziu cada número, verbatim, dentro de
                     <pre>, com .evidencia-src dizendo comando · arquivo · quando

Se não há prova pra colar, não há decisão a pedir — há investigação a fazer.

Isento de verdade (ex.: proposta de algo que ainda não existe)? Declare no HTML,
com a razão escrita:
  <!-- visual-sem-evidencia: proposta nova, nada existe ainda pra mostrar -->

Desligar este gate nesta sessão: VISUAL_GATE=0
EVIDENCIA
    exit 2
  fi

  if [ "$HAS_PLAN_FILE" = "0" ]; then
    capped && exit 0
    bump
    cat >&2 << PLANFILE
⛔ VISUAL GATE — o plano tem HTML, mas não existe como ARQUIVO.  (aviso $((COUNT + 1))/${MAX_NUDGES})
${RESERVA_AVISO}
Não há plano ativo em: $PLANS_DIR

Sem o arquivo, o plano volta a viver só na conversa: o /handoff o reconstrói de
um resumo truncado, as fases mudam de nome entre sessões, e ele é dado como
concluído sem estar. Foi assim que planos se perderam antes.

Antes de chamar ExitPlanMode de novo:

  1. Escreva o plano em JSON. Todo passo NOVO precisa dos quatro campos — sem
     "requisito" e "pronto" o init recusa o arquivo inteiro:

     {"id": "meu-plano", "title": "Meu plano",
      "requisitos": [{"id": "S-1.1", "titulo": "o que o usuário ganha",
                      "ca": "como se aceita isso", "epico": "E1 — Nome do épico"}],
      "phases": [{"id": "F1", "title": "Fase um", "items": [
        {"id": "F1.1", "title": "passo um",
         "desc": "uma linha didática de no máximo 140 chars",
         "pronto": "COMO se prova que este passo terminou",
         "requisito": "S-1.1"}]}]}

  2. python3 <plugin project-skills>/lib/plan_state.py init --file <arquivo.json>
  3. Daí em diante NUNCA reescreva o plano — só marque:
     python3 <plugin project-skills>/lib/plan_state.py tick F1.2 --evidencia "<prova>"

A árvore da página sai de 'plan_state.py page --mode approve' — não a escreva à
mão, senão ela muda de aparência a cada rodada.

Plano que de fato não precisa de arquivo (pergunta pontual, ajuste de uma linha)?
Desligue este gate nesta sessão: VISUAL_GATE=0
PLANFILE
    exit 2
  fi

  cat >&2 << FEEDBACK
📊 Visual HTML da sessão atual já existe: $RECENT_VISUAL
Prova: $PROVA bloco(s) · plano em arquivo. Prossiga com a apresentação.
FEEDBACK
  exit 0
fi

# Sem visual desta sessão — bloqueia e instrui.
capped && exit 0
bump
TODAY=$(date +%Y-%m-%d)
SUGGESTED_FILENAME="${TODAY}-sess-${SESSION_SHORT}-plan.html"
SUGGESTED_PATH="$VISUAL_DIR/${SUGGESTED_FILENAME}"

cat >&2 << FEEDBACK
📊 VISUAL GATE — plano desta sessão precisa virar HTML antes de ir pro CLI.  (aviso $((COUNT + 1))/${MAX_NUDGES})
${RESERVA_AVISO}
Session ID: $SESSION_ID (prefix: $SESSION_SHORT)

CONTEÚDO DO PLANO (fonte de verdade — use ESTE conteúdo literal, NÃO leia arquivos .md de outras sessões):

--- BEGIN PLAN ---
$PLAN_CONTENT
--- END PLAN ---

Passos obrigatórios ANTES de chamar ExitPlanMode de novo:

1. Invoque a skill 'visual' (Skill tool com name='visual')
2. Grave o plano como ARQUIVO (é o que o faz sobreviver ao /clear e ao handoff).
   Todo passo NOVO precisa de "requisito" e "pronto" — sem eles o init recusa:

   {"id": "meu-plano", "title": "Meu plano",
    "requisitos": [{"id": "S-1.1", "titulo": "o que o usuário ganha",
                    "ca": "como se aceita isso", "epico": "E1 — Nome do épico"}],
    "phases": [{"id": "F1", "title": "Fase um", "items": [
      {"id": "F1.1", "title": "passo um",
       "desc": "uma linha didática de no máximo 140 chars",
       "pronto": "COMO se prova que este passo terminou",
       "requisito": "S-1.1"}]}]}

   python3 <plugin project-skills>/lib/plan_state.py init --file <plano.json>
3. Monte a página a partir dele (não escreva a árvore à mão):
   python3 <plugin project-skills>/lib/plan_state.py page --mode approve
4. Salve/abra em: $SUGGESTED_PATH
   (o filename DEVE conter "sess-${SESSION_SHORT}" — o hook reconhece por isso)
5. SÓ DEPOIS chame ExitPlanMode de novo.

Regras não-negociáveis:
- NÃO apresente o plano ao usuário no CLI ainda.
- NÃO resuma o plano em texto na resposta.
- NÃO use o conteúdo de qualquer .md encontrado — use APENAS o PLAN acima.

A PÁGINA TEM QUE MOSTRAR, NÃO DESCREVER (o gate confere isto na volta):
- .ident-strip: projeto, artefato pelo título visível, e o estado dele.
- .artefato: o objeto real embutido (<iframe src="file:///caminho/absoluto">).
- .evidencia: a saída CRUA de cada número, em <pre>, com comando · arquivo · quando.
- Ordem: artefato -> 4-5 bullets do que é -> prova -> 2-3 bullets do problema -> decisão.
- Se não há prova pra colar, não há decisão a pedir — há investigação a fazer.

Desligar este gate nesta sessão: VISUAL_GATE=0
FEEDBACK
exit 2
