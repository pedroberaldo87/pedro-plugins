#!/usr/bin/env bash
# PostToolUse(TaskUpdate) — checkpoint do intent-guard. Quando uma task do todo
# vira "completed", o juiz compara pedidos vivos × trabalho recente (git status
# + diff stat). Derivou → decision:block com o desvio nomeado. Máx 1 bloqueio
# por task; estado POR SESSÃO em /tmp (gotcha do context-guard). Fail-open.
set -uo pipefail
# `CLAUDE_CONFIG_DIR` quando definido — o resto do repositório já o respeita, e
# cravar `$HOME` aqui fazia o kill-switch ser GLOBAL de verdade: duas suítes do
# plugin rodando ao mesmo tempo escreviam e apagavam o mesmo arquivo, e a
# vítima mudava a cada rodada. Estado por-execução tem que caber num diretório
# que quem executa escolhe.
MODE_FILE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/intent-guard/mode"
[ -f "$MODE_FILE" ] && [ "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" = "off" ] && exit 0
PY="$(command -v python3)"
"$PY" --version >/dev/null 2>&1 || exit 0
[ -z "$PY" ] && exit 0
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
hj_leitor >/dev/null 2>&1 || { hj_avisa "task-checkpoint"; exit 0; }
LEDGER="${CLAUDE_PLUGIN_ROOT}/lib/ledger.py"
[ -f "$LEDGER" ] || exit 0

INPUT="$(cat 2>/dev/null || true)"
STATUS="$(hj_campo "$INPUT" tool_input.status)"
[ "$STATUS" = "completed" ] || exit 0
SID="$(hj_campo "$INPUT" session_id)"
# Correction A: sem session_id não dá pra escopar por sessão → não age (fail-open)
[ -n "$SID" ] || exit 0
CWD="$(hj_campo "$INPUT" cwd)"; [ -n "$CWD" ] || CWD="$PWD"
TASKID="$(hj_campo "$INPUT" tool_input.taskId)"
[ -n "$TASKID" ] || TASKID="$(hj_campo "$INPUT" tool_input.task_id)"
[ -n "$TASKID" ] || TASKID="?"

# hash em vez de tr — ids distintos não podem colidir na mesma sentinela
TID_H="$(printf '%s' "$TASKID" | cksum | tr ' ' '_')"
BLOCKF="${TMPD}/intent-guard-ckptblock-${SID}-${TID_H}"
[ -f "$BLOCKF" ] && exit 0   # já bloqueou esta task 1x

# Teto por SESSÃO, além do teto por task. Mesmo mecanismo e mesmo número do
# delivery-audit.sh, pra não inventar um segundo padrão.
#
# O teto por task acima não segura nada quando o problema é o pedido ficar vivo pra
# sempre: cada task NOVA ganha aviso limpo e a mesma acusação volta indefinidamente.
# Foi o que aconteceu em 30/07 no mytube — a acusação era FALSA (o pedido tinha sido
# entregue e auditado, o veredito é que nunca foi transcrito) e repetiu a cada task
# concluída pelo resto da sessão. Guarda que repete acusação falsa ensina a ignorar
# guarda, e aí ele não serve nem quando está certo.
CAPF="${TMPD}/intent-guard-ckptcap-${SID}"
CAPN=0; [ -f "$CAPF" ] && CAPN="$(tr -d '[:space:]' < "$CAPF" 2>/dev/null)"
[ "$CAPN" -eq "$CAPN" ] 2>/dev/null || CAPN=0
[ "$CAPN" -ge 2 ] && exit 0

D="$("$PY" "$LEDGER" resolve-dir --cwd "$CWD" 2>/dev/null)" || exit 0
[ -f "$D/off" ] && exit 0
STATE="$("$PY" "$LEDGER" state --cwd "$CWD" --session "$SID" 2>/dev/null)" || exit 0
LIVE="$(hj_campo_json "$STATE" live)"
[ "$(hj_tamanho "$STATE" live)" = "0" ] && exit 0

ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)" || exit 0
WORK="$( { git -C "$ROOT" status --porcelain; git -C "$ROOT" diff --stat HEAD; } 2>/dev/null | head -c 4000)"
[ -z "$WORK" ] && exit 0

JUDGE_SYS='Você é um verificador automático do intent-guard (NÃO um assistente). Recebe os PEDIDOS VIVOS do usuário, o PLANO ABERTO (se houver, já aprovado pelo usuário) e o TRABALHO RECENTE (git status + diff stat). Uma task do todo acabou de ser concluída. Julgue: o trabalho serve aos pedidos vivos, ou DERIVOU (está construindo outra coisa, contradizendo restrição, ou ignorando os pedidos)? Trabalho que corresponde a uma fase do PLANO ABERTO NÃO é drift — o plano já foi aprovado. Progresso PARCIAL é ok — drift é só abandono/contradição CLARA. Na dúvida: ok. Saída: SOMENTE {"verdict":"ok|drift","reason":"<1 frase pt-BR nomeando o desvio>"}'

# O plano de implementação (se houver um aberto) é contexto que o juiz não tinha:
# trabalho que corresponde a uma fase aprovada não é "outra coisa", é o combinado.
# Lê o JSON direto (sem depender do script do plugin visual — cada plugin tem seu
# próprio CLAUDE_PLUGIN_ROOT, "../visual" não é garantidamente um irmão).
PLAN_BRIEF="$("$PY" -c '
import json, glob, sys
for f in glob.glob(sys.argv[1] + "/*.plan.json"):
    try:
        p = json.load(open(f))
    except Exception:
        continue
    if p.get("status") in ("done", "abandoned"):
        continue
    for ph in p.get("phases", []):
        items = ph.get("items", [])
        if any(i.get("status") != "done" for i in items):
            print("%s — fase em curso: %s" % (p.get("title", p.get("id", "?")), ph.get("title", ph.get("id", "?"))))
            break
    else:
        continue
    break
' "$ROOT/.claude/plans" 2>/dev/null)"

JUDGE_IN="PEDIDOS VIVOS:
$(printf '%s' "$LIVE" | head -c 20000)

PLANO ABERTO (aprovado pelo usuário, se houver):
${PLAN_BRIEF:-nenhum}

TRABALHO RECENTE (task ${TASKID} concluída):
$WORK"

# Marca as chamadas internas: o `claude -p` abaixo dispara os hooks do próprio
# plugin, e sem isto o prompt do juiz entra no caderno como se fosse do usuário.
export INTENT_GUARD_INTERNAL=1

if [ -n "${INTENT_GUARD_JUDGE_CMD:-}" ]; then
  # Correction B: use stdin transport, identical to mock path
  RAW="$(printf '%s' "$JUDGE_IN" | "$INTENT_GUARD_JUDGE_CMD" 2>/dev/null)"; RC=$?
else
  CLAUDE_BIN="$(command -v claude 2>/dev/null)"; [ -z "$CLAUDE_BIN" ] && exit 0
  # Correction B: use stdin instead of positional arg, cap LIVE at 20000 chars
  RAW="$(printf '%s' "$JUDGE_IN" | "$CLAUDE_BIN" -p --model haiku --system-prompt "$JUDGE_SYS" --exclude-dynamic-system-prompt-sections 2>/dev/null)"; RC=$?
fi
{ [ $RC -ne 0 ] || [ -z "$RAW" ]; } && exit 0

read -r VERDICT REASON < <(printf '%s' "$RAW" | "$PY" -c '
import json, re, sys
raw = sys.stdin.read()
v, r = "", ""
for m in re.finditer(r"\{.*?\}", raw, re.S):
    try:
        o = json.loads(m.group(0))
    except Exception:
        continue
    if isinstance(o, dict) and o.get("verdict") in ("ok", "drift"):
        v = o["verdict"]; r = (o.get("reason") or "").replace("\n", " ")
        break
print(v, r)
')
[ "$VERDICT" = "drift" ] || exit 0

touch "$BLOCKF" 2>/dev/null
echo $((CAPN + 1)) > "$CAPF" 2>/dev/null
# A lista sai do `python3` que este gate já exige, não do `jq`.
LIVELIST="$(printf '%s' "$LIVE" | "$PY" -c 'import json,sys
try:
    vivos = json.loads(sys.stdin.read() or "[]")
except Exception:
    sys.exit(0)
sys.stdout.write("; ".join("%s %s" % (v.get("id"), v.get("resumo")) for v in vivos))' 2>/dev/null)"
hj_block "intent-guard (checkpoint): a task ${TASKID} concluiu, mas o trabalho parece DERIVAR dos pedidos do usuário.
- ${REASON}.
- Pedidos vivos: ${LIVELIST}.
- Realinhe antes de seguir — desvio intencional/combinado segue, explicado na entrega."
exit 0
