#!/usr/bin/env bash
# PreToolUse(ExitPlanMode) — trava do plano do intent-guard.
# 1) Juiz classifica os prompts crus novos (pedido/correcao/restricao/conversa).
# 2) Confere: cada pedido/correção VIVO está coberto no plano? Falta → exit 2
#    com a lacuna nomeada (o plano volta pro Claude antes de chegar no usuário).
# Teto anti-loop: máx 2 devoluções por sessão (lição do plan-verification-gate,
# removido por loop infinito de reescrita). Fail-open em qualquer erro.
set -uo pipefail
MODE_FILE="$HOME/.claude/intent-guard/mode"
[ -f "$MODE_FILE" ] && [ "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" = "off" ] && exit 0
PY="$(command -v python3)"
"$PY" --version >/dev/null 2>&1 || exit 0
[ -z "$PY" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
# Diretório temporário DO SISTEMA — perguntado, nunca assumido (ver lib-tmpdir.sh).
# shellcheck source=/dev/null
. "$HJ_DIR/lib-tmpdir.sh" 2>/dev/null
TMPD=$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "plan-gate"; exit 0; }
LEDGER="${CLAUDE_PLUGIN_ROOT}/lib/ledger.py"
[ -f "$LEDGER" ] || exit 0

INPUT="$(cat 2>/dev/null || true)"
SID="$(hj_campo "$INPUT" session_id)"
CWD="$(hj_campo "$INPUT" cwd)"
PLAN="$(hj_campo "$INPUT" tool_input.plan)"
[ -n "$CWD" ] || CWD="$PWD"
[ -n "$PLAN" ] || exit 0

# Sem session_id não há como escopar o cap por sessão → não bloqueia (fail-open).
# Risco: state mutável em /tmp é global entre sessões. Nunca criamos fallback "nosid".
[ -n "$SID" ] || exit 0

D="$("$PY" "$LEDGER" resolve-dir --cwd "$CWD" 2>/dev/null)" || exit 0
[ -f "$D/off" ] && exit 0
STATE="$("$PY" "$LEDGER" state --cwd "$CWD" --session "$SID" 2>/dev/null)" || exit 0
N_PEND="$(hj_tamanho "$STATE" pending)"
N_LIVE="$(hj_tamanho "$STATE" live)"
[ "$N_PEND" = "0" ] && [ "$N_LIVE" = "0" ] && exit 0

# --- juiz (mockável em teste via INTENT_GUARD_JUDGE_CMD) ---
# Marca as chamadas internas: o `claude -p` abaixo dispara os hooks do próprio
# plugin, e sem isto o prompt do juiz entra no caderno como se fosse do usuário.
export INTENT_GUARD_INTERNAL=1
JUDGE_SYS='Você é um classificador automático do intent-guard (NÃO um assistente). Recebe o CADERNO de pedidos do usuário (entradas vivas + prompts crus ainda não classificados) e um PLANO de implementação. Sua ÚNICA saída é um JSON único:
{"classify":[{"ev":"classify","raw":"r-N","class":"pedido|correcao|restricao|conversa","resumo":"<até 15 palavras>","substitui":"p-K ou null"}],"missing":[{"id":"p-N","resumo":"..."}]}
REGRAS DE CLASSIFICAÇÃO: classifique CADA cru. "pedido"=instrução acionável nova; "correcao"=muda/refina pedido anterior (aponte substitui quando substituir de fato); "restricao"=limite a respeitar ("sem mexer em X"); "conversa"=papo/aprovação/pergunta sem instrução acionável. Texto colado com marcador visual-decisions: as escolhas e notas são direcionamento (pedido/correcao), não conversa.
REGRAS DE COBERTURA: para cada pedido/correcao vivo (incluindo os que você acabou de classificar), o PLANO cobre? Cobre = alguma parte do plano realiza aquilo. Restrição só entra em missing se o plano CONTRADIZ ela. Na dúvida, considere coberto (missing é pra lacuna CLARA). Ids de missing são os ids p-N das entradas vivas; para cru recém-classificado sem id ainda, use o raw id r-N.
Saída: SOMENTE o JSON, nada mais.'

JUDGE_IN="CADERNO — vivos e crus:
$(printf '%s' "$STATE" | head -c 20000)

PLANO PROPOSTO:
$(printf '%s' "$PLAN" | head -c 20000)"

if [ -n "${INTENT_GUARD_JUDGE_CMD:-}" ]; then
  RAW="$(printf '%s' "$JUDGE_IN" | "$INTENT_GUARD_JUDGE_CMD" 2>/dev/null)"; RC=$?
else
  CLAUDE_BIN="$(command -v claude 2>/dev/null)"
  [ -z "$CLAUDE_BIN" ] && exit 0
  RAW="$(printf '%s' "$JUDGE_IN" | "$CLAUDE_BIN" -p --model haiku --system-prompt "$JUDGE_SYS" --exclude-dynamic-system-prompt-sections 2>/dev/null)"; RC=$?
fi
{ [ $RC -ne 0 ] || [ -z "$RAW" ]; } && exit 0

PARSED="$(printf '%s' "$RAW" | "$PY" -c '
import json, re, sys
raw = sys.stdin.read()
for m in re.finditer(r"\{.*\}", raw, re.S):
    try:
        o = json.loads(m.group(0))
    except Exception:
        continue
    if isinstance(o, dict) and "missing" in o:
        print(json.dumps(o, ensure_ascii=False)); break
' 2>/dev/null)"
[ -z "$PARSED" ] && exit 0

# aplica as classificações SEMPRE (mesmo que vá negar — conhecimento não se perde)
hj_itens "$PARSED" classify | "$PY" "$LEDGER" apply --cwd "$CWD" 2>/dev/null

# A lista sai do `python3` que este gate já exige, não do `jq`.
MISSING="$(hj_itens "$PARSED" missing | "$PY" -c 'import json,sys
faltas = []
for ln in sys.stdin:
    ln = ln.strip()
    if not ln:
        continue
    try:
        o = json.loads(ln)
    except Exception:
        continue
    faltas.append("%s: %s" % (o.get("id"), o.get("resumo")))
sys.stdout.write("; ".join(faltas))' 2>/dev/null)"
[ -z "$MISSING" ] && exit 0

# --- teto anti-loop: máx 2 devoluções por sessão ---
DENYF="${TMPD}/intent-guard-plandeny-${SID}"
N=0; [ -f "$DENYF" ] && N="$(tr -d '[:space:]' < "$DENYF" 2>/dev/null)"; [ "$N" -eq "$N" ] 2>/dev/null || N=0
if [ "$N" -ge 2 ]; then
  exit 0   # cap batido: vira aviso implícito, não prende o fluxo
fi
echo $((N + 1)) > "$DENYF"
echo "intent-guard (trava do plano): o plano NÃO cobre pedido(s) vivo(s) do usuário: ${MISSING}. Revise o plano pra cobrir (ou explicar por que não) ANTES de apresentar. Pedidos vivos: rode 'python3 ${LEDGER} status --cwd ${CWD}'." >&2
exit 2
