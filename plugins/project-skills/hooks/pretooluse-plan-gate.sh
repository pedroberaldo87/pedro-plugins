#!/bin/bash
# pretooluse-plan-gate.sh — plano não nasce sem documentação.
#
# PreToolUse em EnterPlanMode|ExitPlanMode. Três saídas:
#
#   A) projeto SEM documentação nenhuma  -> DENY SEMPRE, manda rodar /start.
#      Dois escapes: o usuário VERBALIZAR que é pra ignorar — o
#      userpromptsubmit-plan-escape.sh ouve a frase e grava o sentinel de escape —
#      ou a DISPENSA REGISTRADA (S-105): `dispensa.md` na casa da doc com `motivo:`
#      no frontmatter. Ausência silenciosa e dispensa deliberada tinham a mesma
#      cara; agora só a segunda tem arquivo, e só ela libera entre sessões.
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
#   D) doc existe mas as METAS DE QUALIDADE do projeto não estão fechadas -> DENY.
#      (o nome "constituição" é de `constituicao.md` na casa da doc, contra o qual os
#      revisores medem — dois arquivos com o mesmo nome de lei mandam o leitor
#      abrir o errado, F1.3.)
#   D2) a CONSTITUIÇÃO do projeto existe mas não está acordada -> DENY nomeando-a
#      (S-4). Ela é a lei contra a qual os revisores medem; em rascunho, o plano
#      nasce medido por um texto que o dono nunca sancionou. Só é cobrada quando o
#      arquivo existe — nenhuma skill gera constituição, exigi-la de todo projeto
#      seria recusa sem saída.
#   E) alguma etapa do acordo está em aberto -> DENY, nomeando qual
#      (arquitetura / interface / jornadas / funcionalidades). Vale para projeto novo também: é ele
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
hj_leitor >/dev/null 2>&1 || { hj_avisa "pretooluse-plan-gate"; exit 0; }

INPUT=$(cat 2>/dev/null)
TOOL=$(hj_campo "$INPUT" tool_name)
SESSION=$(hj_campo_ou "$INPUT" session_id "")
# payload sem sessão: liberado — o sentinela "unknown" seria compartilhado entre sessões (o defeito do context-guard v1.1)
[ -n "$SESSION" ] || exit 0
CWD=$(hj_campo "$INPUT" cwd)

# ── PORTÃO ÚNICO DE ExitPlanMode (F14.5 · decisão de 2026-08-08) ─────────────
# Três plugins respondiam ao MESMO evento, cada um com o próprio bloqueio — três
# devoluções encadeadas para o mesmo plano, cada uma paga em turno. O dono do
# portão é a família de projeto: os outros dois deixam de se registrar e são
# CHAMADOS daqui, por nome de plugin, na ordem pedido → doc → página. Fail-open
# por peça: plugin ausente na máquina não derruba o portão — cada guarda que
# existir roda; quem não existir simplesmente não cobra.
if [ "$TOOL" = "ExitPlanMode" ] && [ "${PLAN_PORTAO_UNICO:-1}" != "0" ]; then
  RESOLVE="$CLAUDE_PLUGIN_ROOT/hooks/resolve-plugin.sh"
  for PECA in "intent-guard hooks/plan-gate.sh" "visual hooks/pre-exitplan-visualize.sh"; do
    ALVO=$(bash "$RESOLVE" $PECA 2>/dev/null) || continue
    [ -f "$ALVO" ] || continue
    SAIDA=$(printf '%s' "$INPUT" | CLAUDE_PLUGIN_ROOT="$(dirname "$(dirname "$ALVO")")" bash "$ALVO" 2>&1)
    RC=$?
    if [ "$RC" -eq 2 ]; then printf '%s\n' "$SAIDA" >&2; exit 2; fi
    case "$SAIDA" in *permissionDecision*deny*|*'"decision"'*block*) printf '%s\n' "$SAIDA"; exit 0;; esac
  done
fi
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
# A casa da doc sai do resolvedor único (contrato em _shared/casa-da-doc.md).
. "$SCRIPT_DIR/lib-casa-da-doc.sh" 2>/dev/null || exit 0
CASA=$(casa_da_doc "$PROJ")
CASA_REL="${CASA#"$PROJ"/}"
[ -z "$PROJ" ] && exit 0

PHASH=$(project_hash "$PROJ")

# ---------------------------------------------------------------------------
# ESCAPE VERBAL (só vale pro caso A). Gravado pelo userpromptsubmit-plan-escape.sh
# quando o usuário diz explicitamente pra ignorar. Por sessão x projeto.
# ---------------------------------------------------------------------------
ESCAPE="${TMPD}/claude-plan-gate-escape-${SESSION}-${PHASH}"

# ---------------------------------------------------------------------------
# DISPENSA REGISTRADA (S-105). Dispensar a fundação é ATO, não ausência: quem
# dispensa deixa `dispensa.md` na casa da doc com `motivo:` no frontmatter. É
# documento, não sentinel de sessão — dura entre sessões, vai pro git e o próximo
# humano lê por que este projeto planeja sem concepção. Arquivo sem `motivo:`
# preenchido NÃO é dispensa: segue tratado como ausência, e o gate diz isso.
# ---------------------------------------------------------------------------
DISPENSA="$CASA/dispensa.md"
DISPENSA_MOTIVO=""
[ -f "$DISPENSA" ] && DISPENSA_MOTIVO=$(sed -n 's/^motivo:[[:space:]]*//p' "$DISPENSA" 2>/dev/null | head -1)

# liberado — o gate não cobra a fundação: escape verbal desta sessão OU dispensa registrada.
liberado() { [ -f "$ESCAPE" ] || [ -n "$DISPENSA_MOTIVO" ]; }

# ---------------------------------------------------------------------------
# FAIL-OPEN de infra (patterns.md: "só bloqueia com evidência concreta na mão").
# O helper ilegível/ausente NÃO é "projeto sem doc" — é o gate cego. Sem esta
# guarda, um `chmod 000 doc-detect.sh` fazia um projeto TOTALMENTE documentado
# cair no CASO A e ser negado sem cap. Achado da revisão de 2026-07-26.
# ---------------------------------------------------------------------------
[ -r "$SCRIPT_DIR/doc-detect.sh" ] || exit 0

# Tem documentação project-doc? (CLAUDE.md com marker + a casa da doc)
LINE=$(bash "$SCRIPT_DIR/doc-detect.sh" --one "$PROJ" 2>/dev/null)

if [ -z "$LINE" ]; then
  # -------------------------------------------------------------------------
  # Sem doc project-doc. MAS existe um CLAUDE.md escrito à mão? O doc-detect
  # exige a casa da doc pra reportar, então repo com CLAUDE.md manual e sem a
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
    [ -f "${TMPD}/claude-doc-guard-${SESSION}-${PHASH}" ] && exit 0
    CF="${TMPD}/claude-plan-gate-count-${SESSION}-${PHASH}"
    C=0; [ -f "$CF" ] && C="$(cat "$CF" 2>/dev/null)"
    [ "$C" -eq "$C" ] 2>/dev/null || C=0
    [ "$C" -ge 3 ] && exit 0
    echo $((C + 1)) > "$CF"
    MSG="📐 ${PROJ} tem um CLAUDE.md escrito à mão e nenhuma doc estruturada (aviso $((C + 1))/3).
- LEIA o ${HANDMD} antes de planejar — é a única documentação que existe aqui.
- Um Read nele libera este aviso.
- Depois do plano, ofereça \`/start\` (a intenção) e \`/doc\` (a mineração do resto)."
    hj_deny "$MSG"
    exit 0
  fi

  # ======================= CASO A — nenhuma documentação =======================
  liberado && exit 0

  # Autoral já começou? (start-doc rodou mas o índice ainda não existe)
  AUTORAL=0
  for f in quality-goals constraints context solution-strategy glossary; do
    [ -f "$CASA/${f}.md" ] && AUTORAL=$((AUTORAL + 1))
  done

  # Dispensa escrita sem motivo é ausência com arquivo em cima: dizer só "não tem
  # documentação nenhuma" mandaria o dono procurar um arquivo que está lá.
  [ -f "$DISPENSA" ] && ESC_HINT="- Existe ${CASA_REL}/dispensa.md sem \`motivo:\` no frontmatter — sem motivo não é dispensa.
"

  ESC_HINT="${ESC_HINT}- O gate nega enquanto não houver doc; o escape é o usuário autorizar com \`--sem-doc\` (revoga com \`--com-doc\`).
- Para dispensar de vez, registre \`${CASA_REL}/dispensa.md\` com \`motivo:\` no frontmatter — dispensa é ato registrado."

  if [ "$AUTORAL" -gt 0 ]; then
    MSG="📐 ${PROJ} tem ${AUTORAL} de 5 documentos autorais, sem índice CLAUDE.md e sem doc minerada.
- Termine com \`/start\` (ele cobra o que falta) e rode \`/doc\` na sequência.
- Plano sem documentação nasce no vácuo; o erro só aparece na implementação.
${ESC_HINT}"
  else
    MSG="📐 ${PROJ} NÃO tem documentação nenhuma — sem CLAUDE.md, sem ${CASA_REL}/.
- Rode \`/start\` antes de planejar: a entrevista dele guia tudo que vem depois, inclusive este plano.
- Havendo código, rode \`/doc\` depois dela para minerar o resto.
${ESC_HINT}"
  fi

  hj_deny "$MSG"
  exit 0
fi

# ============ CASO D/E — a doc existe, o ACORDO é que pode não existir ============
# F3.2: as metas de qualidade (`quality-goals.md`) são a régua DESTE projeto —
#   o que ele prioriza quando não dá pra ter tudo. Sem ela fechada, o caminho que
#   produz artefato roda sem critério de forma nenhum. Até hoje o gate calava.
# F5.3: as etapas do acordo (arquitetura → interface → jornadas → funcionalidades). Cobradas SEMPRE,
#   não só de quem já tem um dos documentos: enquanto a cobrança dependia de existir
#   arquivo, projeto novo — os 5 autorais escritos e nenhum architecture-intent nem
#   journeys — nunca era negado, que é exatamente o caso que o gate existe para pegar.
#   Quem não quer o regime autoriza pelo escape verbal, que é decisão do usuário.
# Marca de aprovação: a do contrato autoral (`references/authorial-kit.md`), não uma
#   nova — `status: approved` no frontmatter e nenhum `[PENDENTE]` no corpo.
# F2.2: e o `approved-sig:` gravado na aprovação tem que bater com o corpo de agora
#   (`lib-doc-mark.sh`). Editar depois do de acordo reabre a etapa — o de acordo é
#   sobre um TEXTO, não sobre um nome de arquivo.
# ---------------------------------------------------------------------------
DOCS_DIR="$CASA"

# F2.2/S-2: `approved` diz que o dono deu o de acordo, não SOBRE QUAL TEXTO. Sem a
# marca, editar o corpo depois da aprovação deixava a etapa fechada com um conteúdo
# que ninguém aprovou. Helper ausente/ilegível é borda de INFRA: a marca deixa de ser
# cobrada e o resto do gate segue (patterns.md §5.3) — nunca reabrir etapa às cegas.
if ! . "$SCRIPT_DIR/lib-doc-mark.sh" 2>/dev/null; then
  doc_marca()            { return 1; }
  doc_marca_registrada() { return 1; }
  # Sem o helper não dá pra separar frontmatter de corpo: o arquivo inteiro vira o
  # corpo, que é o comportamento conservador de antes do F3.2 (cobra o marcador em
  # qualquer linha) — na dúvida, cobra, nunca fecha etapa às cegas.
  doc_corpo()            { cat "$1" 2>/dev/null; }
fi

# divergiu <arquivo> — o corpo de agora não é o que foi aprovado. Falso quando não há
# marca gravada (documento aprovado antes de a marca existir) e quando não dá pra
# calcular: os dois são "nada a afirmar", e afirmação sem prova aqui barra projeto sadio.
divergiu() {
  _REG=$(doc_marca_registrada "$1" 2>/dev/null)
  [ -n "$_REG" ] || return 1
  _AGORA=$(doc_marca "$1" 2>/dev/null)
  [ -n "$_AGORA" ] || return 1
  [ "$_REG" != "$_AGORA" ]
}

# acordado <arquivo> — documento autoral com o de acordo do usuário registrado.
# `approved`, não `ready`: no contrato autoral `ready` é "escrito" (a própria skill
# promove sozinha quando o último `[PENDENTE]` sai) e `approved` é "o dono deu o de
# acordo", que nenhuma máquina escreve por conta própria. Gate de ACORDO cobra o segundo.
# F3.2: o marcador de lacuna é cobrado no CORPO, não no arquivo inteiro. Corpo com
# `[PENDENTE]` é etapa não escrita e segue reabrindo. No FRONTMATTER, o mesmo marcador
# aparece dentro de `correcao-pendente:` — o registro de um ajuste achado DEPOIS do de
# acordo — e ali ele não derruba a aprovação: a etapa continua valendo no texto que o
# dono aprovou, e a correção sai contada no aviso, em vez de congelar todo plano até
# uma nova aprovação.
acordado() {
  [ -f "$1" ] || return 1
  grep -qi '^status:[[:space:]]*approved' "$1" 2>/dev/null || return 1
  doc_corpo "$1" | grep -q '\[PENDENTE\]' && return 1
  ! divergiu "$1"
}

# correcoes_pendentes <arquivo> — quantas correções o documento declara em aberto.
# Elas moram no frontmatter porque a marca do de acordo é do CORPO (lib-doc-mark.sh):
# registrar a correção no corpo mudaria a marca e reabriria a etapa, que é justamente
# o que o F3.2 tira do caminho.
correcoes_pendentes() {
  _N=$(grep -c '^correcao-pendente:[[:space:]]*[^[:space:]]' "$1" 2>/dev/null)
  [ "$_N" -eq "$_N" ] 2>/dev/null || _N=0
  printf '%s' "$_N"
}

# correcao_texto <arquivo> — a primeira correção declarada, para o aviso nomear o que é.
correcao_texto() {
  sed -n 's/^correcao-pendente:[[:space:]]*//p' "$1" 2>/dev/null | head -1
}

# Contagem de correções pendentes (F3.2). Fora do bloco porque o escape verbal pula a
# apuração inteira, e o aviso lá embaixo lê estas duas variáveis de todo jeito.
CORR_N=0
CORR_LISTA=""

if ! liberado; then
  # ---- D) metas de qualidade do projeto ----
  if ! acordado "$DOCS_DIR/quality-goals.md"; then
    if divergiu "$DOCS_DIR/quality-goals.md"; then
      QG_WHY="mudou depois do de acordo, e o texto de agora não é o aprovado"
    elif [ -f "$DOCS_DIR/quality-goals.md" ]; then
      QG_WHY="está em aberto (falta status: approved, ou há [PENDENTE] no corpo)"
    else
      QG_WHY="não existe"
    fi
    # A mensagem sai no perfil "hook" da régua (_shared/regua_texto.py): cabeçalho com
    # emoji, bullets de uma frase, sem markdown — o canal não renderiza crase nem `**`.
    MSG="📐 Plano barrado: as metas de qualidade deste projeto não estão acordadas.
• ${CASA_REL}/quality-goals.md ${QG_WHY}
• são elas que dizem o que este sistema prioriza quando não dá pra ter tudo
• sem elas o plano nasce sem régua, e o trade-off vira preferência sua
• rode /start quality-goals e feche o acordo com o usuário
• recusa sem cap: o usuário libera com --sem-doc e revoga com --com-doc"
    hj_deny "$MSG"
    exit 0
  fi

  # ---- D2) a lei do projeto (S-4) ----
  # `constituicao.md` na casa da doc é o documento contra o qual os revisores medem — em
  # conflito com qualquer outro doc, ele ganha. Lei em rascunho é lei que ninguém acordou:
  # o plano nasceria medido por um texto que o dono nunca sancionou.
  # Cobrada SÓ quando o arquivo existe: nenhuma skill gera constituição (o /start
  # escreve os 5 autorais, e ela não está entre eles), então exigi-la de todo projeto
  # seria uma recusa sem saída. Quem escreveu a lei, fecha o acordo sobre ela.
  LEI="$DOCS_DIR/constituicao.md"
  if [ -f "$LEI" ] && ! acordado "$LEI"; then
    if divergiu "$LEI"; then
      LEI_WHY="mudou depois do de acordo, e o texto de agora não é o aprovado"
    else
      LEI_WHY="está em rascunho (falta status: approved, ou há [PENDENTE] no corpo)"
    fi
    MSG="📐 Plano barrado: a constituição deste projeto não está acordada.
• ${CASA_REL}/constituicao.md ${LEI_WHY}
• é a lei do projeto: em conflito com qualquer outro documento, ela ganha
• plano medido por lei que o dono não sancionou vale o que vale o rascunho
• feche o acordo sobre a constituição e volte a planejar
• recusa sem cap: o usuário libera com --sem-doc e revoga com --com-doc"
    hj_deny "$MSG"
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
  # S-5: `funcionalidades` (features.md) é a etapa 5 — a lista que a entrevista propõe
  # e o dono cura. Ela é DERIVADA das quatro anteriores, por isso entra por último, e
  # é cobrada pela mesma régua de divergência por marca que as outras.
  # S-70: `esquema` (blueprint.md) é o desenho de como o sistema funciona. Ele entra
  # ANTES de `funcionalidades` porque a lista é derivada dele, e é cobrado pela mesma
  # régua de divergência por marca que as outras etapas.
  ETAPAS="arquitetura:architecture-intent jornadas:journeys esquema:blueprint funcionalidades:features"
  has_frontend "$PROJ" && ETAPAS="arquitetura:architecture-intent interface:design jornadas:journeys esquema:blueprint funcionalidades:features"

  ABERTAS=""
  for E in $ETAPAS; do
    acordado "$DOCS_DIR/${E#*:}.md" && continue
    POR=""
    divergiu "$DOCS_DIR/${E#*:}.md" && POR=" mudou depois do de acordo"
    ABERTAS="${ABERTAS}${ABERTAS:+, }${E%%:*} (${E#*:}.md)${POR}"
  done

  if [ -n "$ABERTAS" ]; then
    MSG="📐 Plano barrado: o acordo com o usuário tem etapa em aberto.
• falta fechar: ${ABERTAS}
• a ordem é metas de qualidade, arquitetura, interface, jornadas, esquema, funcionalidades, e só então o plano
• cada etapa é um documento aprovado, sem [PENDENTE], e com o corpo que a aprovação marcou
• plano sobre jornada não acordada implementa a jornada que VOCÊ imaginou
• rode /start; recusa sem cap, o usuário libera com --sem-doc"
    hj_deny "$MSG"
    exit 0
  fi

  # ---- F3.2) etapa fechada COM correção pendente — cobra, não trava ----
  # Correção achada depois do de acordo não derruba a aprovação inteira: a etapa vale
  # pelo texto aprovado e a pendência vira contagem visível. Sem isto, o único jeito de
  # registrar um ajuste era reabrir a etapa, e o planejamento congelava até reaprovar.
  for A in quality-goals $(for E in $ETAPAS; do printf '%s\n' "${E#*:}"; done); do
    ADOC="$DOCS_DIR/${A}.md"
    AN=$(correcoes_pendentes "$ADOC")
    [ "$AN" -gt 0 ] 2>/dev/null || continue
    CORR_N=$((CORR_N + AN))
    CORR_LISTA="${CORR_LISTA}
• ${A}.md: $(correcao_texto "$ADOC")"
  done
fi

# ======================= CASO B/C — a doc existe =======================
SENTINEL="${TMPD}/claude-doc-guard-${SESSION}-${PHASH}"
if [ -f "$SENTINEL" ]; then         # CASO C: já foi lida nesta sessão
  # F3.2: o plano segue, mas não em silêncio quando há correção pendente — ela fica
  # cobrada em cada plano até ser fechada, que é o preço de não travar o planejamento.
  if [ "$CORR_N" -gt 0 ] 2>/dev/null; then
    CORR_TXT="${CORR_N} correções pendentes"
    [ "$CORR_N" = 1 ] && CORR_TXT="1 correção pendente"
    hj_msg_ctx PreToolUse "📐 O plano segue, com ${CORR_TXT} em etapa já acordada.${CORR_LISTA}
• a etapa continua valendo pelo texto aprovado, e a correção fica cobrada até fechar
• feche cada uma com /start, que reescreve o trecho e regrava o de acordo"
  fi
  exit 0
fi

# CASO B: existe e não foi lida. Cap compartilhado com o doc-guard — o contrato
# anti-loop do repo é absoluto (o gate degrada, nunca trava de verdade).
MAX_NUDGES=3
COUNT_FILE="${TMPD}/claude-plan-gate-count-${SESSION}-${PHASH}"
COUNT=0
[ -f "$COUNT_FILE" ] && COUNT="$(cat "$COUNT_FILE" 2>/dev/null)"
[ "$COUNT" -eq "$COUNT" ] 2>/dev/null || COUNT=0
[ "$COUNT" -ge "$MAX_NUDGES" ] && exit 0
echo $((COUNT + 1)) > "$COUNT_FILE"

N=$(printf '%s' "$LINE" | cut -f3)
STALE=$(printf '%s' "$LINE" | cut -f4)
OOP=$(printf '%s' "$LINE" | cut -f5)

DOCLIST=$(for f in "$CASA"/*.md; do [ -e "$f" ] && basename "$f"; done | paste -sd ', ' -)
[ -n "$DOCLIST" ] && DOCLIST=" Docs: ${DOCLIST}."

STALEMSG=""
case "$STALE" in
  stale)   . "$SCRIPT_DIR/lib-rodada.sh" 2>/dev/null && rodada_doc "$PROJ"
           STALEMSG="
⚠️ A DOC ESTÁ DEFASADA: arquivo(s) do escopo mudaram desde a geração
• Leia, mas trate como HIPÓTESE, senão o plano nasce em cima de fato velho
• Rode /${RODADA_CMD:-doc-touch} ANTES de planejar
• ${RODADA_MOTIVO:-atraso não medido}" ;;
  unknown) STALEMSG="
⚠️ Staleness indeterminado (doc sem data/escopo) — não confie cegamente" ;;
esac
[ "$OOP" = "1" ] && { . "$SCRIPT_DIR/lib-rodada.sh" 2>/dev/null
                      STALEMSG="${STALEMSG}
⚠️ A doc não segue o padrão atual do gerador e pode estar incompleta
• Rode /$(rodada_nome doc 2>/dev/null || echo doc) pra reconstruir do zero"; }

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
MSG="📐 ${PROJ} TEM documentação (${N} doc(s)) e ela ainda não foi lida nesta sessão.${DOCLIST}
- Leia ${CLAUDE_MD_PATH} e o(s) doc(s) do assunto ANTES de planejar.
- Plano sem a doc repete decisão já tomada e ignora gotcha conhecido.
- Um Read em ${CASA_REL}/ ou no CLAUDE.md libera (aviso ${NUDGE_NO}/${MAX_NUDGES} — depois, silêncio).${STALEMSG}"

hj_deny "$MSG"
exit 0
