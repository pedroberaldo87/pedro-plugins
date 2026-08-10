#!/bin/bash
# sessionstart-doc.sh — proactive layer (RF8).
# If the session's project has project-doc documentation, inject a heads-up so that
# "how does X work / where is Y" goes to the docs before grep/Explore.
# Fail-open: any error → exit 0 with no output.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "sessionstart-doc"; exit 0; }

# A detecção de interface é opcional: se a lib sumir, o aviso de doc autoral apenas
# deixa de contar design.md — o resto do hook (o heads-up da doc minerada) não depende
# dela e NÃO pode morrer junto. É a isenção "uso local já degradado dispensa guarda no
# topo" de .claude/docs/patterns.md §5.3: um `exit 0` aqui mataria trabalho alheio.
if ! . "$SCRIPT_DIR/lib-has-frontend.sh" 2>/dev/null; then
  has_frontend() { return 1; }
fi

INPUT=$(cat 2>/dev/null)
CWD=$(hj_campo "$INPUT" cwd)
[ -z "$CWD" ] && CWD="$PWD"
SID=$(hj_campo_ou "$INPUT" session_id unknown)

LINES=$(bash "$SCRIPT_DIR/doc-detect.sh" "$CWD" 2>/dev/null)

# ---------------------------------------------------------------------------
# NENHUM projeto documentado sob o cwd. Antes de sair calado: isto é um projeto?
# Se for, a ausência de doc não é neutra — é a lacuna que o /start resolve, e
# é ela que o gate de plano vai barrar. Avisar aqui evita o usuário descobrir só
# quando tentar planejar. Fail-open: sem raiz de projeto, sai calado como antes.
# ---------------------------------------------------------------------------
if [ -z "$LINES" ]; then
  . "$SCRIPT_DIR/lib-project-root.sh" 2>/dev/null || exit 0
  PROJ=$(project_root "$CWD") || exit 0
  [ -z "$PROJ" ] && exit 0

  # `doc-detect.sh <dir>` só DESCE; `project_root` SOBE. Com o cwd numa subpasta,
  # o modo descida não enxerga a doc que vive na RAIZ — e este ramo declarava
  # "não tem documentação nenhuma" sobre um repo documentado, contradizendo o
  # plan-gate no mesmo turno. Reconsulte a raiz antes de afirmar ausência.
  # Achado da revisão de 2026-07-26.
  LINES=$(bash "$SCRIPT_DIR/doc-detect.sh" --one "$PROJ" 2>/dev/null)
  if [ -n "$LINES" ]; then
    CWD="$PROJ"          # deixa o fluxo normal (abaixo) reportar a doc da raiz
  else
  # ---- a raiz também não tem doc: aí sim a ausência é real ----
  # F7.4: aqui a oferta da metodologia é o PADRÃO, não uma sugestão que depende
  # do humor da sessão. Ela só cala quando o usuário disse, com todas as letras,
  # que não vamos segui-la NESTE projeto — e essa recusa vale para sempre, não
  # para uma sessão, então mora em ~/.claude/ (dentro do plugin seria cache
  # reescrito a cada bump) chaveada pela mesma raiz que o gate de plano usa.
  # Fail-open: HOME ilegível ⇒ a recusa não é vista e a oferta sai de novo —
  # insistir incomoda, travar a sessão não é opção.
  RECUSA="${HOME}/.claude/doc/sem-metodologia-$(project_hash "$PROJ")"
  [ -f "$RECUSA" ] && exit 0
  # design.md só entra na conta de quem TEM interface (F2.2) — backend puro, CLI
  # e este marketplace não devem ser cobrados por doc de design que não se aplica.
  AUTORAIS_DOCS="quality-goals constraints context solution-strategy glossary"
  has_frontend "$PROJ" && AUTORAIS_DOCS="$AUTORAIS_DOCS design"
  N_AUTORAIS=$(printf '%s\n' $AUTORAIS_DOCS | wc -l | tr -d ' ')
  AUTORAL=0; FALTAM=""
  for f in $AUTORAIS_DOCS; do
    if [ -f "$PROJ/.claude/docs/${f}.md" ]; then
      AUTORAL=$((AUTORAL + 1))
    else
      FALTAM="${FALTAM}${FALTAM:+, }${f}"
    fi
  done

  # Tem código pra minerar depois? Só muda o texto do próximo passo, não a oferta.
  NFILES=$(cd "$PROJ" 2>/dev/null && git ls-files 2>/dev/null | wc -l | tr -d ' ')
  [ -z "$NFILES" ] && NFILES=0

  if [ "$AUTORAL" -eq 0 ]; then
    CTX="📐 ${PROJ} não tem documentação nenhuma — sem CLAUDE.md, sem .claude/docs/.\n\nProjeto novo começa PELA concepção: OFEREÇA o \`/start\`. Ele entrevista o usuário sobre o que o sistema prioriza, o que é inegociável, onde ele termina, as decisões que explicam o formato e o vocabulário interno. Essa entrevista vem ANTES da mineração — é ela que guia tudo depois, inclusive a sua leitura do código.\nSão cinco etapas de acordo, uma de cada vez: o autoral, a arquitetura, a interface (só se houver tela), as jornadas e a lista de funcionalidades. Cada etapa é apresentada numa página com o texto integral à vista, e o de acordo é colhido ALI — não no chat, e nunca sobre um resumo."
    if [ "$NFILES" -gt 0 ]; then
      CTX="${CTX}\nDepois dela, \`/doc\` minera o resto (${NFILES} arquivo(s) versionado(s) aqui)."
    else
      CTX="${CTX}\nO projeto ainda não tem código versionado — por ora só o autoral faz sentido; \`/doc\` fica pra quando houver o que minerar."
    fi
    CTX="${CTX}\n\n⚠️ O gate de plano BARRA planos neste projeto enquanto não houver doc. Escape só se o usuário disser explicitamente pra ignorar."
    CTX="${CTX}\nSeguir sem a concepção NÃO é o padrão — só vale se o usuário disser que não vamos segui-la neste projeto. Quando ele disser isso (e só então), grave a recusa e pare de oferecer:\n  mkdir -p \"$(dirname "$RECUSA")\" && touch \"${RECUSA}\"\nPra voltar a oferecer, apague esse arquivo."
  else
    CTX="📐 ${PROJ} tem ${AUTORAL} de ${N_AUTORAIS} documentos autorais, mas nenhum índice CLAUDE.md.\nFalta: ${FALTAM}.\n\nOFEREÇA \`/start\` pra fechar as lacunas e, se houver código, \`/doc\` em seguida.\n\n⚠️ O gate de plano BARRA planos aqui enquanto não houver índice."
  fi

  CTX=$(printf '%b' "$CTX")
  hj_ctx SessionStart "$CTX"
  exit 0
  fi
fi

LIST=""
while IFS=$'\t' read -r TAG PROJ N STALE OOP; do
  [ "$TAG" = "DOC" ] || continue
  FLAG=""
  case "$STALE" in
    stale)   FLAG=" ⚠️ DEFASADA — arquivo(s) do escopo mudaram desde a geração; trate como hipótese e confirme no código (/doc atualiza)" ;;
    unknown) FLAG=" ⚠️ staleness indeterminado (sem data/escopo na doc) — não confie cegamente" ;;
  esac
  if [ "$OOP" = "1" ]; then
    FLAG="${FLAG} ⚠️ fora do padrao atual (gen) — nao confie cegamente, considere /doc"
  fi
  # CLAUDE.md pode estar na raiz (convenção nativa do Claude Code) ou aninhado
  # (.claude/CLAUDE.md, projetos mais antigos) — prefere quem tem o marker v2
  # (cobre projeto com os dois arquivos, ex.: ACME-APP), senão raiz-depois-aninhado.
  if [ -f "${PROJ}/CLAUDE.md" ] && grep -q 'project-doc:v2' "${PROJ}/CLAUDE.md" 2>/dev/null; then
    CLAUDE_MD_DISPLAY="${PROJ}/CLAUDE.md"
  elif [ -f "${PROJ}/.claude/CLAUDE.md" ] && grep -q 'project-doc:v2' "${PROJ}/.claude/CLAUDE.md" 2>/dev/null; then
    CLAUDE_MD_DISPLAY="${PROJ}/.claude/CLAUDE.md"
  elif [ -f "${PROJ}/CLAUDE.md" ]; then
    CLAUDE_MD_DISPLAY="${PROJ}/CLAUDE.md"
  else
    CLAUDE_MD_DISPLAY="${PROJ}/.claude/CLAUDE.md"
  fi
  LIST="${LIST}- ${CLAUDE_MD_DISPLAY} (${N} doc(s) em .claude/docs/)${FLAG}\n"

  # ---------------------------------------------------------------------------
  # F1: minerado-sem-autoral. Projeto TEM doc (passou pelo ramo acima), mas os
  # 5 autorais (quality-goals, constraints, context, solution-strategy,
  # glossary) nunca foram preenchidos. Achado da sessão 871f9573: este ramo
  # nunca contava autoral — só o ramo "sem doc nenhuma" acima contava.
  # CONTRATO DE GATE (.claude/docs/patterns.md → §5.3):
  #   canal      additionalContext (informa, não bloqueia)
  #   cap        1x por (sessão, projeto) — escopado por session_id
  #   desligar   DOC_AUTORAL_GATE=0
  #   fail-open  já garantido pelo `command -v jq` no topo do arquivo
  # ---------------------------------------------------------------------------
  if [ "${DOC_AUTORAL_GATE:-1}" != "0" ]; then
    AUTORAIS_DOCS="quality-goals constraints context solution-strategy glossary"
    has_frontend "${PROJ}" && AUTORAIS_DOCS="$AUTORAIS_DOCS design"
    AUTORAL=0; FALTAM=""
    for f in $AUTORAIS_DOCS; do
      if [ -f "${PROJ}/.claude/docs/${f}.md" ]; then
        AUTORAL=$((AUTORAL + 1))
      else
        FALTAM="${FALTAM}${FALTAM:+, }${f}"
      fi
    done
    if [ "$AUTORAL" -eq 0 ]; then
      PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
      MARK="${TMPDIR:-/tmp}/claude-doc-autoral-nudge-$(id -u)-${SID}-${PHASH}"
      if [ ! -f "$MARK" ]; then
        touch "$MARK" 2>/dev/null
        N_AUTORAIS=$(printf '%s\n' $AUTORAIS_DOCS | wc -l | tr -d ' ')
        LIST="${LIST}⚠️ ${PROJ} tem doc minerada mas ZERO dos ${N_AUTORAIS} autorais (${FALTAM}) — a regra existe (project-doc/start), mas nunca foi cobrada aqui. OFEREÇA \`/start gaps\`. Desliga com DOC_AUTORAL_GATE=0.\n"
      fi
    fi
  fi
done <<< "$LINES"

[ -z "$LIST" ] && exit 0

# Se estamos dentro de um organismo, reenquadra: os itens abaixo são MÓDULOS de
# UM organismo, não N projetos-ilha (o sessionstart-organism.sh já deu o banner).
HEADER="📚 Este projeto tem documentação project-doc:"
ORG_MARK=$(python3 "$SCRIPT_DIR/../lib/organism.py" marker "$CWD" 2>/dev/null)
if [ -n "$ORG_MARK" ] && [ "$(hj_campo "$ORG_MARK" organism)" = "true" ]; then
  ORG_NAME=$(hj_campo_ou "$ORG_MARK" name "o organismo")
  HEADER="📚 Docs por módulo do organismo ${ORG_NAME} (o todo vive em .claude/CLAUDE.md da raiz — NÃO trate como projetos isolados):"
fi

CTX="${HEADER}\n${LIST}\nAntes de explorar com grep/Glob/Explore, LEIA o índice CLAUDE.md e o doc relevante em .claude/docs/ — cobre stack, arquitetura, gotchas, deploy. A doc é agent-facing (feita pra você consumir). Atualizar: /doc."

# expand \n escapes into real newlines, then JSON-encode safely via jq
CTX=$(printf '%b' "$CTX")
hj_ctx SessionStart "$CTX"
exit 0
