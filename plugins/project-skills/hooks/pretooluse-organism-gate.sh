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
# - Refutação: escreva <temporário>/claude-organism-gate-<sess>/<id>.cite com "arquivo:linha";
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
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
# Diretório temporário DO SISTEMA — perguntado, nunca assumido (ver lib-tmpdir.sh).
# shellcheck source=/dev/null
. "$HJ_DIR/lib-tmpdir.sh" 2>/dev/null
TMPD=$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "pretooluse-organism-gate"; exit 0; }
command -v python3 >/dev/null 2>&1 || exit 0
python3 --version >/dev/null 2>&1 || exit 0
[ -f "$ORGANISM_PY" ] || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(hj_campo "$INPUT" tool_name)
case "$TOOL" in Edit|Write|MultiEdit) : ;; *) exit 0 ;; esac

SESSION=$(hj_campo_ou "$INPUT" session_id "")
# payload sem sessão: liberado — o sentinela "unknown" seria compartilhado entre sessões (o defeito do context-guard v1.1)
[ -n "$SESSION" ] || exit 0
CWD=$(hj_campo "$INPUT" cwd)
[ -z "$CWD" ] && CWD="$PWD"
FP=$(hj_campo "$INPUT" tool_input.file_path)
[ -z "$FP" ] && exit 0
case "$FP" in /*) : ;; *) FP="$CWD/$FP" ;; esac

# Never gate our own state writes (or temp scratch) — avoids self-trigger loops.
# Os DOIS caminhos do temporário: o lógico e o físico. No macOS o temporário é
# symlink e a tool pode entregar a versão já resolvida — comparar só um lado
# deixaria o rascunho passar pelo gate.
TMPD_P=$(cd "$TMPD" 2>/dev/null && pwd -P)
[ -n "$TMPD_P" ] || TMPD_P="$TMPD"
case "$FP" in "$TMPD"/*|"$TMPD_P"/*|*/claude-organism-gate/*) exit 0 ;; esac

# Ask the engine what this path touches. Fail-open on any glitch.
MATCH=$(python3 "$ORGANISM_PY" match "$FP" 2>/dev/null)
[ -z "$MATCH" ] && exit 0
[ "$(hj_campo "$MATCH" organism)" = "true" ] || exit 0
[ "$(hj_tamanho "$MATCH" hits)" -gt 0 ] 2>/dev/null || exit 0

ROOT=$(hj_campo "$MATCH" root)
STATE_DIR="${TMPD}/claude-organism-gate-${SESSION}"
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
NHITS=$(hj_tamanho "$MATCH" hits)
i=0
while [ "$i" -lt "$NHITS" ]; do
  ID=$(hj_campo "$MATCH" "hits.$i.id")
  SEV=$(hj_campo "$MATCH" "hits.$i.severidade")
  MSG=$(hj_campo "$MATCH" "hits.$i.aresta_msg")
  BLAST=$(hj_lista "$MATCH" "hits.$i.blast_radius")
  i=$((i + 1))

  # Already resolved this session (endereçou ou refutou com citação válida)?
  [ -f "$STATE_DIR/${ID}.resolved" ] && { log_line "$ID" "$SEV" "resolved-skip"; continue; }

  # Refutation channel: a .cite file the agent wrote → verify by grep.
  if [ -f "$STATE_DIR/${ID}.cite" ]; then
    CITE=$(cat "$STATE_DIR/${ID}.cite" 2>/dev/null)
    VRES=$(python3 "$ORGANISM_PY" verify-cite "$ROOT" "$ID" "$CITE" 2>/dev/null)
    if [ "$(hj_campo "$VRES" valid)" = "true" ]; then
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

hj_deny "$REASON"
exit 0
