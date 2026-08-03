#!/bin/bash
# pretooluse-plan-gate.sh — plano não nasce sem documentação.
#
# PreToolUse em EnterPlanMode|ExitPlanMode. Três saídas:
#
#   A) projeto SEM documentação nenhuma  -> DENY SEMPRE, manda rodar /start-doc.
#      Único escape: o usuário VERBALIZAR que é pra ignorar — o
#      userpromptsubmit-plan-escape.sh ouve a frase e grava o sentinel de escape.
#      Decisão de projeto (2026-07-26): nega sempre, a não ser que o usuário
#      verbalize que é para ignorar. Por isso NÃO há cap de nudges aqui.
#
#   B) tem doc, mas não foi lida nesta sessão -> DENY (cap de 3), manda ler.
#      Reusa o sentinel que o posttooluse-doc-read.sh já escreve — mesma
#      mecânica do pretooluse-doc-guard.sh, nenhum canal novo.
#
#   C) tem doc e já foi lida -> exit 0, silêncio.
#
#   Antes de B/C, duas recusas sobre o ACORDO (plano "a constituição se cumpre",
#   F3.2 e F5.3) — ter doc não é ter acordo, e era aqui que o gate calava:
#
#   D) doc existe mas a constituição do PROJETO não está fechada -> DENY.
#   E) alguma etapa do acordo está em aberto -> DENY, nomeando qual
#      (arquitetura / interface / jornadas). Vale para projeto novo também: é ele
#      que tem TODAS as etapas em aberto.
#
#   D e E são RECUSA, não nudge: não têm cap (cap faria o gate calar, e o
#   artefato nasceria sem régua do projeto). Ambas honram o MESMO escape verbal
#   do caso A — quem autoriza explicitamente segue autorizando.
#
# EnterPlanMode é o momento certo (antes do plano existir); ExitPlanMode é a
# rede — ela é comprovadamente hookável (visual e intent-guard já a usam) e
# ainda dá tempo, porque o deny volta pro modelo antes do plano chegar ao usuário.
#
# FAIL-OPEN só na borda de INFRA (sem jq, sem como resolver a raiz, não é
# projeto): aí sai 0. Quando dá pra determinar que não há doc, nega — é
# evidência concreta na mão, não erro.

# Kill-switch (2026-07-27, contrato dos hooks): quando este gate atrapalha
# num momento ruim, a saída não pode ser editar o script.
[ "${PLAN_DOC_GATE:-1}" = "0" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

case "$TOOL" in
  EnterPlanMode|ExitPlanMode) : ;;
  *) exit 0 ;;
esac

# ---------------------------------------------------------------------------
# Raiz do projeto — via helper compartilhado com o escape hook. NÃO canonicalize
# aqui (ver o porquê em lib-project-root.sh): o PHASH tem que bater com o do
# posttooluse-doc-read.sh, que recorta a string do file_path. Sem raiz = não é
# projeto (ex.: $HOME solto) -> não há o que gatear.
# ---------------------------------------------------------------------------
. "$SCRIPT_DIR/lib-project-root.sh" 2>/dev/null || exit 0
PROJ=$(project_root "$CWD") || exit 0
[ -z "$PROJ" ] && exit 0

PHASH=$(project_hash "$PROJ")

# ---------------------------------------------------------------------------
# ESCAPE VERBAL (só vale pro caso A). Gravado pelo userpromptsubmit-plan-escape.sh
# quando o usuário diz explicitamente pra ignorar. Por sessão x projeto.
# ---------------------------------------------------------------------------
ESCAPE="/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}"

# ---------------------------------------------------------------------------
# FAIL-OPEN de infra (patterns.md: "só bloqueia com evidência concreta na mão").
# O helper ilegível/ausente NÃO é "projeto sem doc" — é o gate cego. Sem esta
# guarda, um `chmod 000 doc-detect.sh` fazia um projeto TOTALMENTE documentado
# cair no CASO A e ser negado sem cap. Achado da revisão de 2026-07-26.
# ---------------------------------------------------------------------------
[ -r "$SCRIPT_DIR/doc-detect.sh" ] || exit 0

# Tem documentação project-doc? (CLAUDE.md com marker + .claude/docs/)
LINE=$(bash "$SCRIPT_DIR/doc-detect.sh" --one "$PROJ" 2>/dev/null)

if [ -z "$LINE" ]; then
  # -------------------------------------------------------------------------
  # Sem doc project-doc. MAS existe um CLAUDE.md escrito à mão? O doc-detect
  # exige `.claude/docs/` pra reportar, então repo com CLAUDE.md manual e sem a
  # árvore caía aqui e era negado PARA SEMPRE — com uma mensagem que mentia
  # ("sem CLAUDE.md") sobre um arquivo que está lá. É o caso mais comum de repo
  # alheio. Documentação escrita à mão É documentação: trata como CASO B (leia),
  # com cap, e oferece a estruturação. Achado da revisão de 2026-07-26.
  # -------------------------------------------------------------------------
  HANDMD=""
  if   [ -f "$PROJ/CLAUDE.md" ];          then HANDMD="$PROJ/CLAUDE.md"
  elif [ -f "$PROJ/.claude/CLAUDE.md" ];  then HANDMD="$PROJ/.claude/CLAUDE.md"
  fi

  if [ -n "$HANDMD" ]; then
    [ -f "/tmp/claude-doc-guard-${SESSION}-${PHASH}" ] && exit 0
    CF="/tmp/claude-plan-gate-count-${SESSION}-${PHASH}"
    C=0; [ -f "$CF" ] && C="$(cat "$CF" 2>/dev/null)"
    [ "$C" -eq "$C" ] 2>/dev/null || C=0
    [ "$C" -ge 3 ] && exit 0
    echo $((C + 1)) > "$CF"
    MSG="📐 ${PROJ} tem um CLAUDE.md escrito à mão (\`${HANDMD}\`), mas não a documentação estruturada (\`.claude/docs/\`). LEIA o ${HANDMD} antes de planejar — é a única documentação que existe aqui. Depois do plano, ofereça \`/start-doc\` (a intenção do sistema) e \`/project-doc\` (mineração do resto): o CLAUDE.md sozinho não cobre dado, durabilidade nem fluxo. Um Read nele libera este aviso (aviso $((C + 1))/3)."
    jq -n --arg r "$MSG" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
    exit 0
  fi

  # ======================= CASO A — nenhuma documentação =======================
  [ -f "$ESCAPE" ] && exit 0

  # Autoral já começou? (start-doc rodou mas o índice ainda não existe)
  AUTORAL=0
  for f in quality-goals constraints context solution-strategy glossary; do
    [ -f "$PROJ/.claude/docs/${f}.md" ] && AUTORAL=$((AUTORAL + 1))
  done

  ESC_HINT="Este gate nega SEMPRE enquanto não houver doc. O escape é o usuário autorizar explicitamente — o token garantido é \`--sem-doc\` (frases como \"ignora a doc\" também valem, mas o token é inequívoco). Ele revoga com \`--com-doc\`."

  if [ "$AUTORAL" -gt 0 ]; then
    MSG="📐 ${PROJ} tem ${AUTORAL} de 5 documentos autorais, mas ainda não tem índice CLAUDE.md nem doc minerada. Termine com \`/start-doc\` (ele cobra o que falta) e depois rode \`/project-doc\` — aí o plano pode ser feito em cima de algo. Plano sem documentação nasce no vácuo e o erro só aparece na implementação. ${ESC_HINT}"
  else
    MSG="📐 ${PROJ} NÃO tem documentação nenhuma — sem CLAUDE.md, sem .claude/docs/. Antes de planejar, rode \`/start-doc\`: ele entrevista o usuário sobre o que o sistema prioriza, o que é inegociável, onde ele termina, as decisões que explicam o formato e o vocabulário interno. É essa entrevista que guia tudo que vem depois — inclusive este plano. Se houver código, depois dela rode \`/project-doc\` pra minerar o resto. ${ESC_HINT}"
  fi

  jq -n --arg r "$MSG" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
  exit 0
fi

# ============ CASO D/E — a doc existe, o ACORDO é que pode não existir ============
# F3.2: a constituição do projeto (`quality-goals.md`) é a régua DESTE projeto —
#   o que ele prioriza quando não dá pra ter tudo. Sem ela fechada, o caminho que
#   produz artefato roda sem critério de forma nenhum. Até hoje o gate calava.
# F5.3: as etapas do acordo (arquitetura → interface → jornadas). Cobradas SEMPRE,
#   não só de quem já tem um dos documentos: enquanto a cobrança dependia de existir
#   arquivo, projeto novo — os 5 autorais escritos e nenhum architecture-intent nem
#   journeys — nunca era negado, que é exatamente o caso que o gate existe para pegar.
#   Quem não quer o regime autoriza pelo escape verbal, que é decisão do usuário.
# Marca de aprovação: a do contrato autoral (`references/authorial-kit.md`), não uma
#   nova — `status: approved` no frontmatter e nenhum `[PENDENTE]` no corpo.
# ---------------------------------------------------------------------------
DOCS_DIR="$PROJ/.claude/docs"

# acordado <arquivo> — documento autoral com o de acordo do usuário registrado.
# `approved`, não `ready`: no contrato autoral `ready` é "escrito" (a própria skill
# promove sozinha quando o último `[PENDENTE]` sai) e `approved` é "o dono deu o de
# acordo", que nenhuma máquina escreve por conta própria. Gate de ACORDO cobra o segundo.
acordado() {
  [ -f "$1" ] || return 1
  grep -qi '^status:[[:space:]]*approved' "$1" 2>/dev/null || return 1
  ! grep -q '\[PENDENTE\]' "$1" 2>/dev/null
}

if [ ! -f "$ESCAPE" ]; then
  # ---- D) constituição do projeto ----
  if ! acordado "$DOCS_DIR/quality-goals.md"; then
    if [ -f "$DOCS_DIR/quality-goals.md" ]; then
      QG_WHY="está em aberto (falta status: approved, ou há [PENDENTE] no corpo)"
    else
      QG_WHY="não existe"
    fi
    # A mensagem sai no perfil "hook" da régua (_shared/regua_texto.py): cabeçalho com
    # emoji, bullets de uma frase, sem markdown — o canal não renderiza crase nem `**`.
    MSG="📐 Plano barrado: a constituição deste projeto não está acordada.
• .claude/docs/quality-goals.md ${QG_WHY}
• é ela que diz o que este sistema prioriza quando não dá pra ter tudo
• sem ela o plano nasce sem régua, e o trade-off vira preferência sua
• rode /start-doc quality-goals e feche o acordo com o usuário
• recusa sem cap: o usuário libera com --sem-doc e revoga com --com-doc"
    jq -n --arg r "$MSG" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
    exit 0
  fi

  # ---- E) as etapas do acordo ----
  # design.md (interface) só entra pra quem TEM tela — mesma regra do
  # sessionstart-doc.sh. Sem a lib, a etapa de interface simplesmente não é
  # cobrada; o resto do gate não pode morrer junto (patterns.md §5.3).
  if ! . "$SCRIPT_DIR/lib-has-frontend.sh" 2>/dev/null; then
    has_frontend() { return 1; }
  fi
  # `architecture-intent`, não `solution-strategy`: o documento da etapa 2 no contrato
  # autoral é o desenho pretendido; a estratégia é da etapa 1, junto com os 5 universais.
  ETAPAS="arquitetura:architecture-intent jornadas:journeys"
  has_frontend "$PROJ" && ETAPAS="arquitetura:architecture-intent interface:design jornadas:journeys"

  ABERTAS=""
  for E in $ETAPAS; do
    acordado "$DOCS_DIR/${E#*:}.md" || ABERTAS="${ABERTAS}${ABERTAS:+, }${E%%:*} (${E#*:}.md)"
  done

  if [ -n "$ABERTAS" ]; then
    MSG="📐 Plano barrado: o acordo com o usuário tem etapa em aberto.
• falta fechar: ${ABERTAS}
• a ordem é constituição, arquitetura, interface, jornadas, e só então o plano
• cada etapa é um documento autoral com status: approved e sem [PENDENTE]
• plano sobre jornada não acordada implementa a jornada que VOCÊ imaginou
• rode /start-doc; recusa sem cap, o usuário libera com --sem-doc"
    jq -n --arg r "$MSG" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
    exit 0
  fi
fi

# ======================= CASO B/C — a doc existe =======================
SENTINEL="/tmp/claude-doc-guard-${SESSION}-${PHASH}"
[ -f "$SENTINEL" ] && exit 0        # CASO C: já foi lida nesta sessão

# CASO B: existe e não foi lida. Cap compartilhado com o doc-guard — o contrato
# anti-loop do repo é absoluto (o gate degrada, nunca trava de verdade).
MAX_NUDGES=3
COUNT_FILE="/tmp/claude-plan-gate-count-${SESSION}-${PHASH}"
COUNT=0
[ -f "$COUNT_FILE" ] && COUNT="$(cat "$COUNT_FILE" 2>/dev/null)"
[ "$COUNT" -eq "$COUNT" ] 2>/dev/null || COUNT=0
[ "$COUNT" -ge "$MAX_NUDGES" ] && exit 0
echo $((COUNT + 1)) > "$COUNT_FILE"

N=$(printf '%s' "$LINE" | cut -f3)
STALE=$(printf '%s' "$LINE" | cut -f4)
OOP=$(printf '%s' "$LINE" | cut -f5)

DOCLIST=$(for f in "$PROJ/.claude/docs"/*.md; do [ -e "$f" ] && basename "$f"; done | paste -sd ', ' -)
[ -n "$DOCLIST" ] && DOCLIST=" Docs: ${DOCLIST}."

STALEMSG=""
case "$STALE" in
  stale)   STALEMSG=" ⚠️ A DOC ESTÁ DEFASADA: arquivo(s) do escopo mudaram desde a geração. Leia, mas trate como HIPÓTESE — e considere \`/doc-touch\` (incremental, barato) ANTES de planejar, senão o plano nasce em cima de fato velho." ;;
  unknown) STALEMSG=" ⚠️ staleness indeterminado (doc sem data/escopo) — não confie cegamente." ;;
esac
[ "$OOP" = "1" ] && STALEMSG="${STALEMSG} ⚠️ a doc não segue o padrão atual do gerador — pode estar incompleta; \`/project-doc\` reconstrói."

if [ -f "${PROJ}/CLAUDE.md" ] && grep -q 'project-doc:v2' "${PROJ}/CLAUDE.md" 2>/dev/null; then
  CLAUDE_MD_PATH="${PROJ}/CLAUDE.md"
elif [ -f "${PROJ}/.claude/CLAUDE.md" ] && grep -q 'project-doc:v2' "${PROJ}/.claude/CLAUDE.md" 2>/dev/null; then
  CLAUDE_MD_PATH="${PROJ}/.claude/CLAUDE.md"
elif [ -f "${PROJ}/CLAUDE.md" ]; then
  CLAUDE_MD_PATH="${PROJ}/CLAUDE.md"
else
  CLAUDE_MD_PATH="${PROJ}/.claude/CLAUDE.md"
fi

NUDGE_NO=$((COUNT + 1))
MSG="📐 Você está prestes a fazer um plano em ${PROJ}, que TEM documentação (${N} doc(s)) — e ela ainda não foi lida nesta sessão.${DOCLIST} Leia ${CLAUDE_MD_PATH} e o(s) doc(s) do assunto do plano ANTES de planejar: plano feito sem a doc repete decisão já tomada e ignora gotcha já conhecido.${STALEMSG} Um Read em qualquer arquivo de .claude/docs/ ou no CLAUDE.md libera automaticamente (aviso ${NUDGE_NO}/${MAX_NUDGES} — depois disso silencio)."

jq -n --arg r "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
