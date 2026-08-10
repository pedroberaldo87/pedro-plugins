#!/usr/bin/env bash
# Stop hook — gate de entrega do intent-guard (padrão handoff-completeness-gate).
# Sessão teve trabalho (sentinela do mark-work) E há pedido vivo sem auditoria
# fresca (tree-hash igual ao atual)? → decision:block instruindo a despachar o
# AUDITOR INDEPENDENTE (subagente de contexto virgem, prompt canônico fixo).
# Audit válido no retry → transcreve vereditos deterministicamente e libera.
# Cap: máx 2 bloqueios de Stop por sessão. Fail-open em qualquer erro.
set -uo pipefail
MODE_FILE="$HOME/.claude/intent-guard/mode"
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
hj_leitor >/dev/null 2>&1 || { hj_avisa "delivery-audit"; exit 0; }
LEDGER="${CLAUDE_PLUGIN_ROOT}/lib/ledger.py"
PROMPT_MD="${CLAUDE_PLUGIN_ROOT}/skills/intent-guard/references/auditor-prompt.md"
[ -f "$LEDGER" ] || exit 0

INPUT="$(cat 2>/dev/null || true)"
SID="$(hj_campo "$INPUT" session_id)"
CWD="$(hj_campo "$INPUT" cwd)"; [ -n "$CWD" ] || CWD="$PWD"

# sem session_id não dá pra escopar por sessão → não age
[ -n "$SID" ] || exit 0

# GATILHO = COMMIT NOVO, não fim de turno (decisão de projeto, 2026-07-24).
# Turno é a unidade do Claude; commit é o marco em que o USUÁRIO decidiu que o
# trabalho virou entrega. Cobrar a cada turno interrompia no meio de um ciclo e
# queimava um agente caro por resposta. Sem commit novo desde a última cobrança,
# o gate fica calado — rascunho não é entrega.
ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)" || exit 0
HEAD_NOW="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null)" || exit 0
[ -n "$HEAD_NOW" ] || exit 0
SEENF="${TMPD}/intent-guard-seenhead-${SID}"
HEAD_SEEN=""; [ -f "$SEENF" ] && HEAD_SEEN="$(cat "$SEENF" 2>/dev/null)"
if [ -z "$HEAD_SEEN" ]; then
  # primeira passada da sessão: registra o ponto de partida e não cobra nada
  printf '%s' "$HEAD_NOW" > "$SEENF"
  exit 0
fi
[ "$HEAD_NOW" = "$HEAD_SEEN" ] && exit 0   # nenhum commit novo → nada a cobrar

D="$("$PY" "$LEDGER" resolve-dir --cwd "$CWD" 2>/dev/null)" || exit 0
[ -f "$D/off" ] && exit 0
STATE="$("$PY" "$LEDGER" state --cwd "$CWD" --session "$SID" 2>/dev/null)" || exit 0

# classifica crus pendentes AQUI TAMBÉM (spec: juiz roda a cada gate — plano,
# checkpoint OU entrega — não só no plan-gate). Sessão sem plan mode senão
# nunca classifica e o gate de entrega fica cego pra sempre (live=0 falso).
if [ "$(hj_tamanho "$STATE" pending)" != "0" ]; then
  CLASSIFY_SYS='Você é um classificador automático do intent-guard (NÃO um assistente). Recebe o CADERNO de pedidos do usuário (entradas vivas + prompts crus ainda não classificados). Sua ÚNICA saída é um JSON único:
{"classify":[{"ev":"classify","raw":"r-N","class":"pedido|correcao|restricao|conversa","resumo":"<até 15 palavras>","substitui":"p-K ou null","verify":"git_synced ou null"}]}
REGRAS DE CLASSIFICAÇÃO: classifique CADA cru. "pedido"=instrução acionável nova; "correcao"=muda/refina pedido anterior (aponte substitui quando substituir de fato); "restricao"=limite a respeitar ("sem mexer em X"); "conversa"=papo/aprovação/pergunta sem instrução acionável. Texto colado com marcador visual-decisions: as escolhas e notas são direcionamento (pedido/correcao), não conversa.
VERIFY (escada de custo): use "verify":"git_synced" SOMENTE quando o pedido inteiro se resume a publicar/sincronizar o repositório — "commit push", "sobe pro marketplace", "manda pro git", "garante que subiu". Se o pedido pede QUALQUER outra coisa além disso (implementar, investigar, corrigir, revisar), use null — mesmo que envolva commitar no fim. Na dúvida, null: null custa uma auditoria, um verify errado carimba feito sem conferir o que importa.
Saída: SOMENTE o JSON, nada mais.'
  CLASSIFY_IN="CADERNO — vivos e crus:
$(printf '%s' "$STATE" | head -c 20000)"

  # Marca as chamadas internas: o `claude -p` abaixo dispara os hooks do próprio
  # plugin, e sem isto o prompt do juiz entra no caderno como se fosse do usuário.
  export INTENT_GUARD_INTERNAL=1

  if [ -n "${INTENT_GUARD_JUDGE_CMD:-}" ]; then
    CRAW="$(printf '%s' "$CLASSIFY_IN" | "$INTENT_GUARD_JUDGE_CMD" 2>/dev/null)"; CRC=$?
  else
    CLAUDE_BIN="$(command -v claude 2>/dev/null)"
    if [ -n "$CLAUDE_BIN" ]; then
      CRAW="$(printf '%s' "$CLASSIFY_IN" | "$CLAUDE_BIN" -p --model haiku --system-prompt "$CLASSIFY_SYS" --exclude-dynamic-system-prompt-sections 2>/dev/null)"; CRC=$?
    else
      CRAW=""; CRC=1
    fi
  fi

  # juiz indisponível/ilegível → segue com o que já estava classificado (fail-open,
  # como em todo o resto do plugin) — $STATE fica com o valor lido antes deste bloco
  if [ $CRC -eq 0 ] && [ -n "$CRAW" ]; then
    CPARSED="$(printf '%s' "$CRAW" | "$PY" -c '
import json, re, sys
raw = sys.stdin.read()
for m in re.finditer(r"\{.*\}", raw, re.S):
    try:
        o = json.loads(m.group(0))
    except Exception:
        continue
    if isinstance(o, dict) and "classify" in o:
        print(json.dumps(o, ensure_ascii=False)); break
' 2>/dev/null)"
    if [ -n "$CPARSED" ]; then
      hj_itens "$CPARSED" classify | "$PY" "$LEDGER" apply --cwd "$CWD" 2>/dev/null
      STATE="$("$PY" "$LEDGER" state --cwd "$CWD" --session "$SID" 2>/dev/null)" || exit 0
    fi
  fi
fi

# ESCADA DE CUSTO, degrau 0: resolve por CÓDIGO os pedidos que têm receita
# mecânica (ex.: "commit push" → compara os hashes) antes de gastar um agente.
# Numa sessão real, 4 de 7 pedidos eram isso — cada um custava ~50k tokens.
"$PY" "$LEDGER" verify --cwd "$CWD" --session "$SID" >/dev/null 2>&1
STATE="$("$PY" "$LEDGER" state --cwd "$CWD" --session "$SID" 2>/dev/null)" || exit 0

LIVE="$(hj_campo_json "$STATE" live)"
if [ "$(hj_tamanho "$STATE" live)" = "0" ]; then
  printf '%s' "$HEAD_NOW" > "$SEENF"   # cobrança fechada sem agente: marco avança
  rm -f "${TMPD}/intent-guard-stopdeny-${SID}"
  exit 0
fi

# procura audit válido (mais novo primeiro); válido → transcreve e libera
while IFS= read -r AUD; do
  [ -f "$AUD" ] || continue
  OK="$(hj_campo "$("$PY" "$LEDGER" audit-check --cwd "$CWD" --session "$SID" --file "$AUD" 2>/dev/null)" ok)"
  if [ "$OK" = "true" ]; then
    "$PY" "$LEDGER" apply-audit --cwd "$CWD" --session "$SID" --file "$AUD" 2>/dev/null
    printf '%s' "$HEAD_NOW" > "$SEENF"   # cobrança fechada: marco avança pro commit auditado
    rm -f "${TMPD}/intent-guard-stopdeny-${SID}"
    exit 0
  fi
done < <(ls -t "$D"/audit-*.json 2>/dev/null)

# cap anti-loop: máx 2 bloqueios de Stop por sessão
DENYF="${TMPD}/intent-guard-stopdeny-${SID}"
N=0; [ -f "$DENYF" ] && N="$(tr -d '[:space:]' < "$DENYF" 2>/dev/null)"; [ "$N" -eq "$N" ] 2>/dev/null || N=0
[ "$N" -ge 2 ] && exit 0
echo $((N + 1)) > "$DENYF"

H="$("$PY" "$LEDGER" tree-hash --cwd "$CWD" 2>/dev/null)"
TS="$(date +%s)"
OUTP="$D/audit-${TS}.json"
# O texto dos vivos sai do `python3` que este gate já exige, não do `jq`.
LIVETXT="$(printf '%s' "$LIVE" | "$PY" -c 'import json,sys
try:
    vivos = json.loads(sys.stdin.read() or "[]")
except Exception:
    sys.exit(0)
print("\n".join("%s [%s] %s — verbatim: %s" % (v.get("id"), v.get("class"), v.get("resumo"), v.get("text")) for v in vivos))' 2>/dev/null | head -c 6000)"

# ESCOPO DA PERGUNTA — gravado AQUI, pelo gate, não ecoado pelo auditor.
#
# O bloqueio pergunta pelos vivos DESTE instante, mas o consumo só acontece no Stop
# seguinte — e entre um e outro cada mensagem do usuário vira pedido vivo novo. Antes,
# audit_check exigia veredito de TODO vivo no instante da leitura, então o veredito
# nascia impossível de aprovar e o pedido ficava vivo para sempre (catraca: medido em
# 30/07 com 33 pedidos acumulados que nenhum auditor foi encarregado de julgar).
# Pedido que chegou DEPOIS não é responsabilidade deste veredito — vira o próximo
# bloqueio, que é o comportamento desejado.
# Sidecar e não campo dentro do JSON porque o arquivo ainda não existe: quem o escreve
# é o auditor. Depender do modelo ecoar a lista seria trocar mecanismo por exortação.
printf '%s' "$LIVE" | "$PY" -c 'import json,sys
try:
    vivos = json.loads(sys.stdin.read() or "[]")
except Exception:
    sys.exit(0)
sys.stdout.write(json.dumps([v.get("id") for v in vivos], separators=(",", ":")))' > "${OUTP}.escopo" 2>/dev/null
hj_block "intent-guard (gate de entrega): há pedido(s) vivo(s) do usuário sem auditoria independente — você NÃO pode declarar entregue na confiança. FAÇA AGORA: (1) leia ${PROMPT_MD}; (2) despache UM subagente (Agent tool, general-purpose) cujo prompt é o texto do arquivo VERBATIM + o bloco DADOS abaixo (não reescreva nem resuma o prompt canônico); (3) espere o veredito; (4) tente encerrar de novo — o gate valida e transcreve sozinho; (5) mostre a tabela de vereditos ao usuário (via /visual se passar de 10 linhas).
DADOS
projeto: ${CWD}
saida: ${OUTP}
tree_hash: ${H}
pedidos vivos:
${LIVETXT}"
exit 0
