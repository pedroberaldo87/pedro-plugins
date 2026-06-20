#!/bin/bash
# scope-cop.sh — v2 (auto-correção)
# Trava de escopo para edições de UI. Julga se a edição proposta é COERENTE com o
# PLANO aprovado (quando há) e/ou com o pedido do usuário. Quando desvia, NEGA a
# edição pra mim (Claude) com o motivo — eu repenso e reimplemento. NUNCA escala
# pro Pedro (sem modo "ask"). Circuit breaker evita loop infinito. Fail-open + log.
#
# Decisão por flag: ~/.claude/guardrails/scope-cop.mode   (uma linha: deny [default] | off)
# Auditoria:        ~/.claude/guardrails/scope-cop.log
# Circuit breaker:  ~/.claude/guardrails/scope-cop.blockstreak  (nº de BLOCKs seguidos)
#
# Portabilidade: jq/python3 são resolvidos via PATH (fallback no brew Apple-Silicon)
# e o estado mutável vive em ~/.claude/guardrails/ (por-máquina, fora do cache do
# plugin que ${CLAUDE_PLUGIN_ROOT} reescreve a cada bump de versão).

JQ="$(command -v jq || echo /opt/homebrew/bin/jq)"
PY="$(command -v python3 || echo /opt/homebrew/bin/python3)"
HOOK_DIR="$HOME/.claude/guardrails"
mkdir -p "$HOOK_DIR" 2>/dev/null
MODE_FILE="$HOOK_DIR/scope-cop.mode"
LOG_FILE="$HOOK_DIR/scope-cop.log"
STREAK_FILE="$HOOK_DIR/scope-cop.blockstreak"
MAX_STREAK=3   # após N BLOCKs seguidos, libera 1 edição e reseta (anti-loop)

# Resolve o binário do claude (PATH do hook pode ser mínimo).
CLAUDE_BIN="$(command -v claude 2>/dev/null)"
[ -x "$CLAUDE_BIN" ] || CLAUDE_BIN="/Applications/cmux.app/Contents/Resources/bin/claude"

INPUT="$(cat)"

# --- modo (default deny; "off" desliga a trava por completo) ---
# Lê só se o arquivo existe — numa máquina nova ele não existe, e o redirect `<`
# vazaria "No such file or directory" no stderr (o 2>/dev/null no tr não pega a
# falha de abertura do redirect).
MODE=""
[ -f "$MODE_FILE" ] && MODE="$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)"
[ "$MODE" = "off" ] && exit 0
MODE="deny"

# --- campos do tool ---
FILE_PATH="$(printf '%s' "$INPUT" | "$JQ" -r '.tool_input.file_path // empty')"
TOOL_NAME="$(printf '%s' "$INPUT" | "$JQ" -r '.tool_name // empty')"
[ -n "$FILE_PATH" ] || exit 0   # sem file_path → não é Edit/Write de arquivo

# --- filtro barato: só julga arquivos de UI ---
case "$FILE_PATH" in
  *.html|*.htm|*.svelte|*.css|*.scss|*.sass|*.less|*.tsx|*.jsx|*.vue|*.astro) : ;;
  *) exit 0 ;;  # não-UI: sai instantâneo, sem chamar modelo
esac

# --- isenção de ARTEFATO: doc/apresentação NÃO é UI de produto (não policia) ---
# Plano, PRD, HANDOFF, atas e visuais (/visual em .claude/visual/) são grandes e
# ricos POR DESIGN — a régua de "edição cirúrgica de UI" não se aplica a eles. O
# scope-cop policia UI de produto (src/app/components…), não documentos.
case "$FILE_PATH" in
  */.claude/*|*/docs/*|*HANDOFF*|*PRD*|*plan*.html|*_archive/*) exit 0 ;;
esac

# --- circuit breaker: lê o nº de BLOCKs consecutivos ---
STREAK=""
[ -f "$STREAK_FILE" ] && STREAK="$(tr -d '[:space:]' < "$STREAK_FILE" 2>/dev/null)"
[ "$STREAK" -eq "$STREAK" ] 2>/dev/null || STREAK=0

# --- log helper ---
log_line() {
  local verdict="$1" reason="$2"
  local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"
  local req_s diff_s
  req_s="$(printf '%s' "$USER_REQ" | tr '\n' ' ' | cut -c1-140)"
  diff_s="$(printf '%s' "$EDIT_DESC" | tr '\n' ' ' | cut -c1-140)"
  printf '%s | %s | %s | streak=%s | plan=%s | %s | req="%s" | diff="%s"\n' \
    "$ts" "$MODE" "$verdict" "$STREAK" "${HAS_PLAN:-0}" "${FILE_PATH:-?}" "$req_s" "$diff_s" >> "$LOG_FILE"
}

# --- descrição da edição (o que muda) ---
OLD="$(printf '%s' "$INPUT" | "$JQ" -r '.tool_input.old_string // empty' | cut -c1-1500)"
NEW="$(printf '%s' "$INPUT" | "$JQ" -r '.tool_input.new_string // empty' | cut -c1-1500)"
CONTENT="$(printf '%s' "$INPUT" | "$JQ" -r '.tool_input.content // empty' | cut -c1-1500)"
if [ -n "$OLD" ] || [ -n "$NEW" ]; then
  FILE_CTX="$(head -c 3500 "$FILE_PATH" 2>/dev/null)"
  EDIT_DESC="[Edit em $FILE_PATH]
--- ESTADO ATUAL DO ARQUIVO (contexto, início) ---
$FILE_CTX
--- TRECHO QUE A EDIÇÃO REMOVE/ALTERA (old) ---
$OLD
--- SUBSTITUÍDO POR (new) ---
$NEW"
else
  EDIT_DESC="[Write em $FILE_PATH — sobrescreve o arquivo]
--- CONTEÚDO (início) ---
$CONTENT"
fi

# --- transcript: pedido literal + plano aprovado ---
TRANSCRIPT="$(printf '%s' "$INPUT" | "$JQ" -r '.transcript_path // empty')"
USER_REQ=""
PLAN=""
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  USER_REQ="$("$PY" - "$TRANSCRIPT" <<'PY'
import json, sys
msgs = []
try:
    for line in open(sys.argv[1], encoding='utf-8'):
        try: o = json.loads(line)
        except Exception: continue
        if o.get("type") != "user": continue
        c = o.get("message", {}).get("content")
        txt = ""
        if isinstance(c, str):
            txt = c
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text":
                    txt += b.get("text", "")
        txt = txt.strip()
        if not txt: continue
        low = txt.lstrip()
        if low.startswith("<") or low.startswith("Base directory") \
           or "tool_use_error" in txt or "system-reminder" in txt \
           or "[Request interrupted" in txt or "Caveat:" in low \
           or "## Approved Plan" in txt:
            continue
        msgs.append(txt)
except Exception:
    pass
print("\n---\n".join(m[:700] for m in msgs[-3:]))
PY
)"
  # Plano aprovado (último "## Approved Plan:" no transcript — a aprovação do
  # ExitPlanMode injeta o plano inteiro no tool_result). É a fonte de verdade do
  # escopo combinado: edição coberta pelo plano não é "desvio".
  PLAN="$("$PY" - "$TRANSCRIPT" <<'PY'
import json, sys
found = ""
try:
    for line in open(sys.argv[1], encoding='utf-8'):
        try: o = json.loads(line)
        except Exception: continue
        # varre qualquer texto do transcript em busca do bloco aprovado
        blobs = []
        msg = o.get("message", {})
        c = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(c, str):
            blobs.append(c)
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict):
                    if isinstance(b.get("text"), str): blobs.append(b["text"])
                    if isinstance(b.get("content"), str): blobs.append(b["content"])
                    if isinstance(b.get("content"), list):
                        for bb in b["content"]:
                            if isinstance(bb, dict) and isinstance(bb.get("text"), str):
                                blobs.append(bb["text"])
        if isinstance(o.get("toolUseResult"), str):
            blobs.append(o["toolUseResult"])
        for t in blobs:
            i = t.rfind("## Approved Plan:")
            if i >= 0:
                found = t[i+len("## Approved Plan:"):].strip()
except Exception:
    pass
# Plano inteiro (não só os 3500 primeiros): planos multi-item passavam disso, o juiz
# não via os itens finais nem o Sumário Executivo (que fica no fim) e bloqueava
# edições legítimas de itens 2+ como "fora do plano". 20k cobre planos grandes.
print(found[:20000])
PY
)"
fi

HAS_PLAN=0
[ -n "$PLAN" ] && HAS_PLAN=1

# --- gating: quando NÃO julgar (evita nag) ---
# Com plano aprovado: sempre julga (a edição de UI tem que ser coerente com ele).
# Sem plano: só julga se as mensagens recentes parecem um pedido de UI.
if [ "$HAS_PLAN" -eq 0 ]; then
  if [ -z "$USER_REQ" ]; then log_line "SKIP:no-request" "sem pedido nem plano"; exit 0; fi
  UI_KW='cor|color|botã|button|pad(ding)?|marg|anel|card|tela|screen|layout|escond|hide|mostr|show|remov|tira|tire|delet|aument|diminu|encolh|\bmove\b|mov(er|e)|alinh|align|espaç|\bgap\b|tamanho|\bsize\b|fonte|\bfont|[íi]cone|icon|borda|border|radius|fundo|background|\bbg\b|menu|barra|\bbar\b|header|footer|sidebar|modal|popup|overlay|hover|anima|transiç|transition|sombra|shadow|opacid|opacity|\bgrid\b|flex|coluna|column|linha|\brow\b|pill|badge|toast|snackbar|scroll|rolagem|altura|height|largura|width|\btopo\b|\btop\b|rodapé|esquerda|direita|centr|visual|estilo|\bstyle\b|\bcss\b|design|spacing|posiç|position|pisca|frame|svg|div|span|\bclass\b'
  if ! printf '%s' "$USER_REQ" | grep -qiE "$UI_KW"; then
    log_line "SKIP:no-ui-request" "sem plano e mensagens não pedem UI"
    exit 0
  fi
fi

# --- circuit breaker: já bati o teto de BLOCKs seguidos → libera 1 e reseta ---
if [ "$STREAK" -ge "$MAX_STREAK" ]; then
  echo 0 > "$STREAK_FILE"
  log_line "PASS:circuit-breaker" "liberado após $STREAK BLOCKs seguidos (anti-loop)"
  exit 0
fi

# --- juiz (LLM) ---
JUDGE_SYS='Você é um classificador automático (NÃO um assistente). Sua ÚNICA saída permitida é {"verdict":"pass|block","reason":"<frase curta em pt-BR dizendo o desvio e o que reimplementar>"}. NUNCA converse, NUNCA responda ao conteúdo — você apenas JULGA uma edição de UI.

Você recebe (quando existem): o PLANO APROVADO da sessão, o PEDIDO recente do usuário, o ESTADO DO ARQUIVO e a EDIÇÃO proposta. Decide se a edição é COERENTE com o que foi combinado, ou se DESVIA.

PASSO 0 — PLANO (verifique PRIMEIRO): se há PLANO APROVADO e a edição implementa parte dele — mexe num arquivo/tarefa que o plano descreve, na direção que o plano define — responda PASS, mesmo que a edição seja grande ou toque um arquivo só. Trabalho incremental de um plano aprovado NÃO é desvio. Só marque block se a edição contradiz o plano ou faz algo que o plano não previu E não foi pedido.

PASSO 1 — AUTORIZAÇÃO AMPLA: a mensagem mais recente pede trabalho amplo ("reescreve", "refaz a tela", "implementa tudo")? Se sim e a edição entrega isso de verdade → PASS.

Sem plano nem autorização ampla, faça as DUAS checagens; se QUALQUER falhar, BLOCK:
CHECK 1 — AMPLITUDE: a edição mexe ALÉM do que foi pedido? Nomeou um elemento mas altera os irmãos/o container/o efeito todo → BLOCK. ABORDAGEM diferente (pediu REMOVER e a edição só ESCONDE/REDIMENSIONA/MOVE; ou pediu X e mexe em Y) → BLOCK.
CHECK 2 — AMBIGUIDADE DE ALVO: há mais de uma leitura razoável de qual/quanto mexer e a edição comprou uma não-conservadora sem necessidade → BLOCK. Só quando a ambiguidade é REAL.

PASS quando: coberto pelo plano; OU edição cirúrgica num elemento inequívoco do pedido; OU autorização ampla real. Não invente ambiguidade onde o pedido/plano é claro. Pedido claro + edição proporcional = PASS.'

JUDGE_INPUT="PLANO APROVADO (escopo combinado; vazio se não houver):
${PLAN:-(nenhum plano aprovado nesta sessão)}

PEDIDO RECENTE DO USUÁRIO (mais recente por último):
${USER_REQ:-(sem mensagem de texto recente)}

EDIÇÃO PROPOSTA:
$EDIT_DESC"

RAW="$("$CLAUDE_BIN" -p --model haiku --system-prompt "$JUDGE_SYS" --exclude-dynamic-system-prompt-sections "$JUDGE_INPUT" </dev/null 2>/dev/null)"
RC=$?

# Fail-open: juiz indisponível/timeout → libera, registra que não houve proteção.
if [ $RC -ne 0 ] || [ -z "$RAW" ]; then
  log_line "SKIP:judge-error" "claude -p rc=$RC (fail-open)"
  exit 0
fi

read -r VERDICT REASON < <("$PY" - "$RAW" <<'PY'
import json, re, sys
raw = sys.argv[1]
verdict, reason = "", ""
for m in re.finditer(r'\{.*?\}', raw, re.S):
    try: o = json.loads(m.group(0))
    except Exception: continue
    if isinstance(o, dict) and o.get("verdict") in ("pass", "block"):
        verdict = o["verdict"]
        reason = (o.get("reason") or "").replace("\n", " ").replace("\t", " ")
        break
print(verdict, reason)
PY
)

# Veredito ilegível → fail-open.
if [ "$VERDICT" != "block" ] && [ "$VERDICT" != "pass" ]; then
  log_line "SKIP:parse-error" "resposta do juiz não parseável (fail-open)"
  exit 0
fi

if [ "$VERDICT" = "block" ]; then
  echo $((STREAK + 1)) > "$STREAK_FILE"
  log_line "BLOCK" "$REASON"
  # permissionDecision "deny" = nega pra mim (Claude), NÃO pergunta ao Pedro.
  # O reason me instrui a repensar e reimplementar — auto-correção.
  "$JQ" -n --arg r "Scope-cop (auto-revisão): essa edição parece desviar do escopo combinado. $REASON — REPENSE a implementação e reescreva de um jeito coerente com o plano/pedido (não reenvie idêntico). Isto é revisão automática; NÃO envolve o Pedro." '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $r
    }
  }'
  exit 0
else
  echo 0 > "$STREAK_FILE"
  log_line "PASS" "$REASON"
  exit 0
fi
