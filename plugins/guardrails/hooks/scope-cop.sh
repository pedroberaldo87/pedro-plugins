#!/bin/bash
# scope-cop.sh — v2 (auto-correção)
# Trava de escopo para edições de UI. Julga se a edição proposta é COERENTE com o
# PLANO aprovado (quando há) e/ou com o pedido do usuário. Quando desvia, NEGA a
# edição pra mim (Claude) com o motivo — eu repenso e reimplemento. NUNCA escala
# pro usuário (sem modo "ask"). Circuit breaker evita loop infinito. Fail-open + log.
#
# Decisão por flag: $CFG/guardrails/scope-cop.mode   (CFG = ${CLAUDE_CONFIG_DIR:-$HOME/.claude})
#   deny [default] — bloqueia e manda repensar
#   warn           — só avisa, deixa a edição passar (acrescentado 2026-07-30)
#   off            — desliga por completo
#   (qualquer outro valor: cai no default e o valor ignorado vai pro log)
# O modo "warn" existe porque o gate ficou em "off" desde 02/07, depois de 3 bloqueios
# seguidos: o estado meio-ligado (plugin habilitado, gate off) faz parecer que existe
# trava de escopo onde não existe. Aviso é honesto; silêncio não.
# Auditoria:        $CFG/guardrails/scope-cop.log
# Circuit breaker:  $CFG/guardrails/scope-cop.blockstreak  (nº de BLOCKs seguidos)
#
# Portabilidade: jq/python3 são resolvidos via PATH (fallback no brew Apple-Silicon)
# e o estado mutável vive em $CFG/guardrails/ (por-máquina, fora do cache do
# plugin que ${CLAUDE_PLUGIN_ROOT} reescreve a cada bump de versão).

# Kill-switch (contrato dos hooks, propriedade 3): toda trava se desliga por env var
# <NOME>_GATE=0, sem editar o script. O arquivo de modo é a decisão DURÁVEL (deny |
# warn | off) e mora fora do repo; a env var é o interruptor do momento ruim, que é
# o que a tabela promete a quem chega com o gate atrapalhando. Mesmo molde do
# GRAPHIFY_GATE. Sai antes de ler o stdin — como o graphify-guard.
[ "${SCOPE_COP_GATE:-1}" = "0" ] && exit 0

JQ="$(command -v jq)"
PY="$(command -v python3)"
# Sem jq ou python3 no PATH não dá pra parsear nem julgar — fail-open (não bloqueia).
{ [ -z "$JQ" ] || [ -z "$PY" ]; } && exit 0
# MESMA regra do lib/conformance.py:CLAUDE_DIR e do hooks/lib/apply-config.sh. Com
# $HOME fixo aqui, quem seta CLAUDE_CONFIG_DIR teria o hook lendo o modo numa pasta
# e o conformance varrendo **/*.mode noutra: o gate que o auditor acusa não seria o
# que o hook obedece, e cada lado ficaria coerente sozinho (o mesmo defeito silencioso
# do bypass.log do stop-prose-ceiling).
HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"
mkdir -p "$HOOK_DIR" 2>/dev/null
MODE_FILE="$HOOK_DIR/scope-cop.mode"
LOG_FILE="$HOOK_DIR/scope-cop.log"
STREAK_FILE="$HOOK_DIR/scope-cop.blockstreak"
BYPASS_FILE="$HOOK_DIR/scope-cop.bypass"
MAX_STREAK=3   # após N BLOCKs seguidos, libera 1 edição e reseta (anti-loop)

# Rotação simples do log: acima de 5000 linhas, mantém as últimas 2000 (evita
# que o scope-cop.log cresça indefinidamente — chegou a passar de 450 KB).
if [ -f "$LOG_FILE" ]; then
  LC="$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)"
  if [ "$LC" -gt 5000 ] 2>/dev/null; then
    tail -n 2000 "$LOG_FILE" > "$LOG_FILE.tmp" 2>/dev/null && mv "$LOG_FILE.tmp" "$LOG_FILE"
  fi
fi

# Resolve o binário do claude (PATH do hook pode ser mínimo). Sem claude no PATH
# não há juiz → fail-open na hora da chamada (ver abaixo). Sem path hardcoded de
# app específico — isso amarrava o hook a uma máquina/app.
CLAUDE_BIN="$(command -v claude 2>/dev/null)"

INPUT="$(cat)"

# --- freio POR SESSÃO (2026-07-27) ---
# O contador de BLOCKs seguidos morava num arquivo só (`scope-cop.blockstreak`),
# compartilhado por todas as sessões. Com duas sessões abertas no mesmo projeto,
# os BLOCKs de uma contavam pro freio da outra: o circuit breaker disparava na
# sessão errada e liberava uma edição SEM julgar o escopo dela. É a mesma classe
# de bug que já mordeu o context-guard (estado global entre sessões, v1.2.0).
# Sem session_id (entrada estranha), cai no arquivo global de antes — pior que
# por-sessão, melhor que não frear.
SCOPE_SID="$(printf '%s' "$INPUT" | ${JQ:-jq} -r '.session_id // empty' 2>/dev/null)"
if [ -n "$SCOPE_SID" ]; then
  STREAK_FILE="$HOOK_DIR/scope-cop.blockstreak.${SCOPE_SID}"
  BYPASS_FILE="$HOOK_DIR/scope-cop.bypass.${SCOPE_SID}"
  # Poda: sessão morre e o arquivo fica. Mesma janela do context-guard.
  find "$HOOK_DIR" -maxdepth 1 -name 'scope-cop.blockstreak.*' -mtime +1 -delete 2>/dev/null
  find "$HOOK_DIR" -maxdepth 1 -name 'scope-cop.bypass.*' -mtime +1 -delete 2>/dev/null
fi

# --- modo (default deny; "off" desliga a trava por completo) ---
# Lê só se o arquivo existe — numa máquina nova ele não existe, e o redirect `<`
# vazaria "No such file or directory" no stderr (o 2>/dev/null no tr não pega a
# falha de abertura do redirect).
MODE=""
[ -f "$MODE_FILE" ] && MODE="$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)"
# Conjunto FECHADO: deny | warn | off (vazio/ausente = default, máquina nova). Valor
# fora dele é erro de digitação ("wanr", "ask") — segue no default, mas registrado:
# agora que o modo tem 3 estados, errar a grafia entrega o gate MAIS severo
# justamente a quem pediu o mais brando, que é o que o "warn" nasceu pra evitar.
MODE_IGNORADO=""
case "$MODE" in
  off) exit 0 ;;
  deny|warn|"") : ;;
  *) MODE_IGNORADO="$MODE" ;;
esac
[ "$MODE" = "warn" ] || MODE="deny"

# --- campos do tool ---
FILE_PATH="$(printf '%s' "$INPUT" | "$JQ" -r '.tool_input.file_path // empty')"
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

# Rastro do modo inválido — aqui, depois dos filtros baratos, e não na leitura: o
# matcher é Edit|Write, então registrar lá cima escreveria uma linha por edição de
# QUALQUER arquivo e afogaria a auditoria (o log rotaciona em 5000 linhas).
if [ -n "$MODE_IGNORADO" ]; then
  printf '%s | %s | MODE:invalido | valor ignorado="%s" em %s (use deny|warn|off) | %s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$MODE" "$MODE_IGNORADO" "$MODE_FILE" "$FILE_PATH" >> "$LOG_FILE"
fi

# --- circuit breaker: lê o nº de BLOCKs consecutivos ---
STREAK=""
[ -f "$STREAK_FILE" ] && STREAK="$(tr -d '[:space:]' < "$STREAK_FILE" 2>/dev/null)"
[ "$STREAK" -eq "$STREAK" ] 2>/dev/null || STREAK=0

# --- log helper ---
log_line() {
  local verdict="$1"
  local ts; ts="$(date '+%Y-%m-%d %H:%M:%S')"
  local req_s diff_s
  # tr '\n|' ' /' — também troca o pipe por barra: o log é '|'-delimitado, então
  # um '|' no pedido/diff quebraria o parsing das colunas.
  req_s="$(printf '%s' "$USER_REQ" | tr '\n|' ' /' | cut -c1-140)"
  diff_s="$(printf '%s' "$EDIT_DESC" | tr '\n|' ' /' | cut -c1-140)"
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
found_exit = ""    # ## Approved Plan: (scan textual, fallback)
found_struct = ""  # toolUseResult.plan do ExitPlanMode (estrutural, preferido)
found_visual = ""  # bloco /visual colado pelo usuário
try:
    for line in open(sys.argv[1], encoding='utf-8'):
        try: o = json.loads(line)
        except Exception: continue
        msg = o.get("message", {})
        c = msg.get("content") if isinstance(msg, dict) else None
        # (1) ## Approved Plan: (ExitPlanMode) vive em tool_result/assistant — varre TUDO.
        blobs = []
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
        # Fonte ESTRUTURAL (preferida): o resultado do ExitPlanMode grava
        # toolUseResult como dict {plan, planWasEdited, ...}. Texto solto no
        # transcript não consegue forjar isso — o scan por marcador abaixo é
        # só fallback pra transcripts antigos, e sofre de auto-envenenamento
        # (qualquer tool output citando "## Approved Plan" vira "o plano").
        tur = o.get("toolUseResult")
        if isinstance(tur, dict) and isinstance(tur.get("plan"), str) and tur["plan"].strip():
            found_struct = tur["plan"].strip()
            continue
        for t in blobs:
            # Fallback textual. O header varia: "## Approved Plan:" ou
            # "## Approved Plan (edited by user):" — casa o prefixo e corta
            # depois do ':' que fecha o header.
            i = t.rfind("## Approved Plan")
            if i >= 0:
                j = t.find(":", i)
                if j >= 0:
                    found_exit = t[j+1:].strip()
        # (2) /visual NÃO passa pelo ExitPlanMode — a aprovação mora no bloco que o usuário
        # COLA (começa com '<!-- visual-{approve|feedback|decisions} v1 -->'). Lê SÓ o texto
        # que o usuário digitou/colou (string OU blocos type=='text' do topo); tool_result
        # também é type=user e ecoa o marcador via outputs de comando/doc da skill — por
        # isso é excluído. Marcador COMPLETO ('v1 -->') evita casar prosa solta.
        if o.get("type") == "user":
            utext = ""
            if isinstance(c, str):
                utext = c
            elif isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str):
                        utext += b["text"]
            # Marcador no INÍCIO da mensagem = paste real do /visual. Enterrado (ex.: a doc
            # da skill injeta blocos de exemplo lá pelo char 23k) é citação, não aprovação.
            for mk in ("<!-- visual-approve v1 -->", "<!-- visual-feedback v1 -->", "<!-- visual-decisions v1 -->"):
                j = utext.find(mk)
                if 0 <= j <= 200:
                    found_visual = utext[j:].strip()
except Exception:
    pass
# Precedência: o paste /visual (mensagem do usuário, gated por posição — sinal mais
# confiável e o fluxo primário do usuário) vence o plano estrutural do ExitPlanMode
# (toolUseResult.plan, que texto solto não forja), que por sua vez vence o scan
# textual '## Approved Plan:' — este pode ser ecoado por outputs de comando.
found = found_visual or found_struct or found_exit
# Plano inteiro (não só os 3500 primeiros): planos multi-item passavam disso, o juiz
# não via os itens finais nem o Sumário Executivo (que fica no fim) e bloqueava
# edições legítimas de itens 2+ como "fora do plano". 20k cobre planos grandes.
print(found[:20000])
PY
)"
fi

# Fallback: plano aprovado via /visual por live-sync ("ok" sem colar o bloco). O daemon
# do /visual grava o estado em ~/.claude/visual-state/latest.json (docTitle + itens +
# verdito). Usa só se o transcript não trouxe plano E o estado é fresco (< 2h) — evita
# herdar plano de outra sessão antiga.
VISUAL_STATE="$HOME/.claude/visual-state/latest.json"
if [ -z "$PLAN" ] && [ -f "$VISUAL_STATE" ]; then
  PLAN="$("$PY" - "$VISUAL_STATE" <<'PY'
import json, os, sys, time
p = sys.argv[1]
try:
    if time.time() - os.path.getmtime(p) > 7200:
        print(""); sys.exit(0)
    o = json.load(open(p, encoding='utf-8'))
    st = o.get("state", o)
    fb = st.get("feedback") or []
    approved = [f for f in fb if f.get("val") in ("keep", "change") and f.get("title")]
    if not approved:
        print(""); sys.exit(0)
    out = ["(plano aprovado via /visual: " + str(o.get("docTitle") or "") + ")"]
    for f in approved:
        out.append("- " + str(f.get("title"))[:300] + " — aprovado")
    print("\n".join(out)[:20000])
except Exception:
    print("")
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
  # Deixa um rastro de que a liberação foi por circuit breaker (escopo NÃO julgado
  # desta vez) — durável, pro Claude e pro usuário saberem que a trava abriu mão aqui.
  printf '%s | liberado após %s BLOCKs seguidos (anti-loop) | %s\n' \
    "$(date '+%Y-%m-%d %H:%M:%S')" "$STREAK" "${FILE_PATH:-?}" > "$BYPASS_FILE"
  log_line "PASS:circuit-breaker" "liberado após $STREAK BLOCKs seguidos (anti-loop) — escopo NÃO validado"
  exit 0
fi

# --- sem binário do claude → não há juiz → fail-open (não bloqueia) ---
if [ -z "$CLAUDE_BIN" ] || [ ! -x "$CLAUDE_BIN" ]; then
  log_line "SKIP:no-claude-bin" "claude não encontrado no PATH (fail-open)"
  exit 0
fi

# --- juiz (LLM) ---
JUDGE_SYS='Você é um classificador automático (NÃO um assistente). Sua ÚNICA saída permitida é {"verdict":"pass|block","reason":"<frase curta em pt-BR dizendo o desvio e o que reimplementar>"}. NUNCA converse, NUNCA responda ao conteúdo — você apenas JULGA uma edição de UI.

Você recebe (quando existem): o PLANO APROVADO da sessão, o PEDIDO recente do usuário, o ESTADO DO ARQUIVO e a EDIÇÃO proposta. Decide se a edição é COERENTE com o que foi combinado, ou se DESVIA.

PASSO 0 — PLANO (verifique PRIMEIRO): se há PLANO APROVADO e a edição implementa parte dele — mexe num arquivo/tarefa que o plano descreve, na direção que o plano define — responda PASS, mesmo que a edição seja grande ou toque um arquivo só. Trabalho incremental de um plano aprovado NÃO é desvio. Só marque block se a edição contradiz o plano ou faz algo que o plano não previu E não foi pedido. IMPORTANTE: quando o bloco PLANO APROVADO está presente, o usuário JÁ o aprovou formalmente (o texto vem do registro estrutural do ExitPlanMode aprovado, que é posterior às mensagens soltas) — NUNCA conclua que "o plano não foi aprovado" nem exija nova aprovação; mensagens antigas do usuário (ex.: "stop", perguntas de método) NÃO revogam a aprovação.

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

if [ "$VERDICT" = "block" ] && [ "$MODE" = "warn" ]; then
  echo 0 > "$STREAK_FILE"          # em aviso não há streak: nada foi bloqueado
  log_line "WARN" "$REASON"
  # O par systemMessage + additionalContext porque o aviso interessa aos DOIS
  # públicos, e cada um tem seu canal: additionalContext vira attachment pro
  # Claude, mas o transcript filtra `hook_additional_context` da renderização —
  # sozinho ele deixaria o usuário no mesmo silêncio do modo "off". systemMessage
  # não é filtrado. Mesmo padrão do ship/hooks/pre-deploy-test-check.sh.
  # Cabeçalho com emoji e um bullet por ideia: o canal é terminal, não markdown, e
  # parágrafo de 180 caracteres no meio da conversa é o que ensina a desligar o gate.
  AVISO="🚧 Scope-cop (aviso, não bloqueio) — esta edição parece desviar do escopo combinado
• ${REASON}
• Confira se o desvio é intencional; nada foi bloqueado.
• Bloquear de novo: escreva 'deny' em ${MODE_FILE}"
  # A régua do canal (perfil `hook`, de quality-goals.md). Defeito de forma não cala um
  # aviso: o motivo vai pro stderr e o texto sai assim mesmo. Régua ausente → silêncio.
  REGUA="$(cd "$(dirname "$0")" && pwd)/../lib/regua_texto.py"
  [ -f "$REGUA" ] && printf '%s\n' "$AVISO" | "$PY" "$REGUA" --perfil hook --onde "aviso do scope-cop" - || :
  "$JQ" -n --arg r "$AVISO" '{
    systemMessage: $r,
    hookSpecificOutput: { hookEventName: "PreToolUse", additionalContext: $r }
  }'
  exit 0
fi

if [ "$VERDICT" = "block" ]; then
  echo $((STREAK + 1)) > "$STREAK_FILE"
  log_line "BLOCK" "$REASON"
  # permissionDecision "deny" = nega pra mim (Claude), NÃO pergunta ao usuário.
  # O reason me instrui a repensar e reimplementar — auto-correção.
  # shellcheck disable=SC2016  # as aspas simples são do programa jq; $REASON é interpolado via --arg, fora delas
  "$JQ" -n --arg r "Scope-cop (auto-revisão): essa edição parece desviar do escopo combinado. $REASON — REPENSE a implementação e reescreva de um jeito coerente com o plano/pedido (não reenvie idêntico). Isto é revisão automática; NÃO envolve o usuário." '{
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
