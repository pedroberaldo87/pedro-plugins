#!/bin/bash
# pretooluse-organism-gate.sh — o GATE INVERTIDO (pré-Edit).
#
# Quando você vai editar um arquivo que é PONTA de uma costura do organism.yaml,
# o SISTEMA afirma a aresta ("isso toca mcp e servico") e te obriga a engajar.
# Você NÃO produz o mapa (o modelo ancorado no módulo o preencheria do mesmo
# viés) — o sistema afirma, você endereça ou refuta com citação verificável.
#
# Design (revisado com o Fable, 4 rodadas):
# - Nasce no PRÉ-EDIT, não no ExitPlanMode: lá um gate bloqueante idêntico já
#   MORREU por loop infinito (plan-verification-gate.sh, removido). E o Edit tem
#   input estruturado (file_path) → zero NLP de prosa.
# - ANTI-LOOP INEGOCIÁVEL: no máximo 1 deny por (costura, sessão). 2º toque na
#   mesma costura passa (degrada, loga) — é o que o gate morto não tinha.
# - Só severidade=block dá deny. warn apenas loga (R12).
# - Refutação: escreva /tmp/claude-organism-gate-<sess>/<id>.cite com "arquivo:linha";
#   no próximo toque o hook valida por grep (organism.py verify-cite). Válida →
#   silencia de vez; inválida → loga, mas o anti-loop já impede travar.
# - Log jsonl de TODO disparo desde o dia 1 (sem métrica não se distingue
#   "gate funciona" de "agente aprendeu a ackar no automático").
# - Fail-open: qualquer erro → exit 0 (a ação passa). Nunca trava por bug do hook.

# Kill-switch (2026-07-27, contrato dos hooks): quando este gate atrapalha
# num momento ruim, a saída não pode ser editar o script.
[ "${ORGANISM_GATE:-1}" = "0" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORGANISM_PY="$SCRIPT_DIR/../lib/organism.py"
command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
[ -f "$ORGANISM_PY" ] || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
case "$TOOL" in Edit|Write|MultiEdit) : ;; *) exit 0 ;; esac

SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"
FP=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$FP" ] && exit 0
case "$FP" in /*) : ;; *) FP="$CWD/$FP" ;; esac

# Never gate our own state writes (or /tmp scratch) — avoids self-trigger loops.
case "$FP" in /tmp/*|*/claude-organism-gate/*) exit 0 ;; esac

# Ask the engine what this path touches. Fail-open on any glitch.
MATCH=$(python3 "$ORGANISM_PY" match "$FP" 2>/dev/null)
[ -z "$MATCH" ] && exit 0
printf '%s' "$MATCH" | jq -e '.organism == true and (.hits | length > 0)' >/dev/null 2>&1 || exit 0

ROOT=$(printf '%s' "$MATCH" | jq -r '.root')
STATE_DIR="/tmp/claude-organism-gate-${SESSION}"
# Se não der pra criar o state, NÃO bloqueia (senão o .denied nunca grava e todo
# edit re-denia = loop infinito, o cenário que matou o gate anterior). Fail-open.
mkdir -p "$STATE_DIR" 2>/dev/null || exit 0
[ -w "$STATE_DIR" ] || exit 0
LOG="$STATE_DIR/log.jsonl"
TS=$(date -u +%FT%TZ 2>/dev/null || echo "")

log_line() { # id severidade outcome
  printf '{"ts":"%s","tool":"%s","file":"%s","costura":"%s","sev":"%s","outcome":"%s"}\n' \
    "$TS" "$TOOL" "${FP#$ROOT/}" "$1" "$2" "$3" >> "$LOG" 2>/dev/null
}

# Iterate hits. Accumulate deny reasons for block costuras not yet denied/resolved.
DENY_MSG=""
NHITS=$(printf '%s' "$MATCH" | jq -r '.hits | length')
i=0
while [ "$i" -lt "$NHITS" ]; do
  ID=$(printf '%s' "$MATCH" | jq -r ".hits[$i].id")
  SEV=$(printf '%s' "$MATCH" | jq -r ".hits[$i].severidade")
  MSG=$(printf '%s' "$MATCH" | jq -r ".hits[$i].aresta_msg")
  BLAST=$(printf '%s' "$MATCH" | jq -r ".hits[$i].blast_radius | join(\", \")")
  i=$((i + 1))

  # Already resolved this session (endereçou ou refutou com citação válida)?
  [ -f "$STATE_DIR/${ID}.resolved" ] && { log_line "$ID" "$SEV" "resolved-skip"; continue; }

  # Refutation channel: a .cite file the agent wrote → verify by grep.
  if [ -f "$STATE_DIR/${ID}.cite" ]; then
    CITE=$(cat "$STATE_DIR/${ID}.cite" 2>/dev/null)
    VRES=$(python3 "$ORGANISM_PY" verify-cite "$ROOT" "$ID" "$CITE" 2>/dev/null)
    if printf '%s' "$VRES" | jq -e '.valid == true' >/dev/null 2>&1; then
      touch "$STATE_DIR/${ID}.resolved" 2>/dev/null
      log_line "$ID" "$SEV" "refuted-valid"
      continue
    else
      log_line "$ID" "$SEV" "refuted-invalid"
      # falls through — invalid refutation doesn't resolve, but anti-loop below still applies
    fi
  fi

  if [ "$SEV" != "block" ]; then
    log_line "$ID" "$SEV" "warn-logged"   # warn nunca bloqueia (walking skeleton)
    continue
  fi

  # block: ANTI-LOOP — at most one deny per (costura, session).
  if [ -f "$STATE_DIR/${ID}.denied" ]; then
    log_line "$ID" "$SEV" "pass-after-deny"
    continue
  fi

  # First block hit → this is THE deny for this costura this session.
  touch "$STATE_DIR/${ID}.denied" 2>/dev/null
  log_line "$ID" "$SEV" "deny"
  DENY_MSG="${DENY_MSG}
• [${ID}] ${MSG}
  → blast-radius: ${BLAST}."
done

[ -z "$DENY_MSG" ] && exit 0

REASON="🧬 GATE DO ORGANISMO — você está tocando uma COSTURA cross-módulo do organismo:
${DENY_MSG}

Isto NÃO é 'pare'. É 'não trate como ilha': antes de seguir, decida conscientemente o impacto na outra ponta.
Para prosseguir, escolha um:
  (a) ENDEREÇAR — considere os módulos do blast-radius e repita a ação (este é o ÚNICO deny desta costura nesta sessão; a repetição passa).
  (b) REFUTAR com prova — se tem certeza que NÃO afeta, escreva a citação e repita:
        echo 'caminho/arquivo:linha' > ${STATE_DIR}/<costura_id>.cite
      (o hook valida que a linha contém um símbolo real da costura; citação falsa é rejeitada e logada)."

jq -n --arg r "$REASON" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
