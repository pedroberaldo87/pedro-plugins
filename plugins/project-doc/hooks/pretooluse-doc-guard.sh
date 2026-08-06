#!/bin/bash
# pretooluse-doc-guard.sh — gate (RF8).
# When a blind search (Grep/Glob, Bash grep|rg|find|..., or a code-EXPLORING Task
# subagent) is about to run in a project that has project-doc documentation, DENY
# it and redirect to .claude/docs/. The deny lists the actual docs and flags
# staleness. Mirrors graphify-guard; separate sentinel.
# Fail-open: any error → exit 0 (action proceeds).
#
# PRIMARY decision: SENTINEL-FILE
#   posttooluse-doc-read.sh writes <temp>/claude-doc-guard-${SESSION}-${PHASH} the
#   moment Claude reads any file under .claude/docs/ or .claude/CLAUDE.md. The
#   guard checks for that sentinel; if present → doc was consulted → pass.
#   Sem sentinel, a busca é negada SEMPRE — não há porta de escape por contagem
#   (MAX_NUDGES caiu em 2026-08-04: os agentes atravessavam depois de 3 avisos).
#
# MONOREPO: if the searched path is under apps/{app}/ and
#   .claude/docs/apps/{app}.md exists, the nudge cites that specific doc.
#
# OUT_OF_PATTERN: 5th column from doc-detect.sh --one is included in the nudge.

# Kill-switch (2026-07-27, contrato dos hooks): quando este gate atrapalha
# num momento ruim, a saída não pode ser editar o script.
[ "${DOC_GUARD_GATE:-1}" = "0" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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
hj_leitor >/dev/null 2>&1 || { hj_avisa "pretooluse-doc-guard"; exit 0; }

INPUT=$(cat 2>/dev/null)
TOOL=$(hj_campo "$INPUT" tool_name)
SESSION=$(hj_campo_ou "$INPUT" session_id unknown)
CWD=$(hj_campo "$INPUT" cwd)
[ -z "$CWD" ] && CWD="$PWD"

# Candidate dirs this search/exploration might touch (CWD always in play).
CANDS="$CWD"
case "$TOOL" in
  Grep|Glob)
    P=$(hj_campo "$INPUT" tool_input.path)
    [ -n "$P" ] && CANDS="$CANDS
$P"
    ;;
  Bash)
    CMD=$(hj_campo "$INPUT" tool_input.command)
    # only intercept blind text/file search; everything else passes
    # Wrappers de comando inambíguos (sudo/time/xargs/env/nohup/command) disparam em
    # posição de comando, tolerando tokens de opção entre o wrapper e a palavra de busca
    # (xargs -I{} grep, sudo -u root grep) — trade-off aceito: falso-positivo raro quando
    # um token não-opção real separa wrapper de grep (ex.: xargs kill grep).
    # Posição de comando NÃO é só início de linha: crase, abre-chave de bloco e as palavras
    # do/then também abrem comando, e antes da palavra de busca ainda cabem prefixo de
    # variável (VAR=1 grep) e prefixo de caminho (/usr/bin/grep, ./bin/grep). Tudo isso
    # ancora — o que continua NÃO ancorando é o espaço solto, que é o que mantém a prosa
    # ("echo \"use grep\"") passando. Trade-off aceito: prosa com 'do'/'then' antes da
    # palavra ("please do grep") vira falso-positivo. bash -c/sh -c segue passando (exige
    # parsing de string). Regra espelhada em graphify-guard/hooks/pretooluse-graphify-guard.sh.
    printf '%s' "$CMD" | grep -Eq '(^|[;&|(){}`]|(^|[[:space:]])(do|then)[[:space:]])[[:space:]]*([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*((sudo|time|xargs|env|nohup|command)[[:space:]]+([^[:space:];|()]+[[:space:]]+)*)?((\.{0,2}/)[^[:space:]]*/)?(grep|egrep|fgrep|rg|ripgrep|ag|ack|find)([^[:alnum:]_]|$)' || exit 0
    # set -f: tokenize WITHOUT glob-expanding — otherwise "*.json" in the command
    # would list the hook's own CWD and create bogus candidates. Tokens with stray
    # quotes are harmless: the [ -e ] test below drops anything that isn't a real path.
    set -f
    for tok in $CMD; do
      case "$tok" in -*) continue ;; esac
      cand="$tok"; case "$cand" in /*) : ;; *) cand="$CWD/$tok" ;; esac
      [ -e "$cand" ] && CANDS="$CANDS
$cand"
    done
    set +f
    ;;
  Agent|Task)
    # The subagent-spawn tool is "Agent" (legacy alias "Task"). Only nudge
    # code-EXPLORING subagents — they grep/read on your behalf and otherwise
    # never see the docs. Specialized agents (review, statusline, etc.) pass
    # untouched so the guard doesn't nag.
    ST=$(hj_campo "$INPUT" tool_input.subagent_type)
    case "$ST" in
      Explore|general-purpose|Plan|claude|"") : ;;
      *) exit 0 ;;
    esac
    # Task carries no path → the CWD candidate (already set) is what we check.
    ;;
  *)
    exit 0
    ;;
esac

# Nearest ancestor of a dir that owns project-doc documentation.
# Checks BOTH CLAUDE.md locations (root — Claude Code's native convention — and
# the older nested .claude/CLAUDE.md) so it stops at the project itself instead
# of overshooting to an unrelated ancestor (e.g. $HOME) when CLAUDE.md is at root.
find_doc_up() {
  local d="$1"
  case "$d" in /*) : ;; *) d="$CWD/$d" ;; esac
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    { [ -f "$d/CLAUDE.md" ] || [ -f "$d/.claude/CLAUDE.md" ]; } && { printf '%s' "$d"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}

# 1) check each candidate by walking up
PROJ=""
while IFS= read -r c; do
  [ -z "$c" ] && continue
  p=$(find_doc_up "$c") && { PROJ="$p"; break; }
done <<EOF
$CANDS
EOF

# 2) container fallback: descend from CWD to catch docs living in subprojects
if [ -z "$PROJ" ]; then
  LINE0=$(bash "$SCRIPT_DIR/doc-detect.sh" "$CWD" 2>/dev/null | head -1)
  [ -n "$LINE0" ] && PROJ=$(printf '%s' "$LINE0" | cut -f2)
fi

# No doc covers this → let it through.
[ -z "$PROJ" ] && exit 0

# ---------------------------------------------------------------------------
# MONOREPO detection: check if any candidate is under $PROJ/apps/{app}/.
# If .claude/docs/apps/{app}.md exists → use it as the target doc.
# ---------------------------------------------------------------------------
APP_DOC=""
APP_NAME=""
ROOT_COVERED=0
while IFS= read -r c; do
  [ -z "$c" ] && continue
  # Normalize to absolute
  case "$c" in /*) : ;; *) c="$CWD/$c" ;; esac
  # Candidate covers the monorepo ROOT (grep -r foo . / find . com cwd na raiz)
  case "$c" in "$PROJ"|"$PROJ/.") ROOT_COVERED=1 ;; esac
  # Check if candidate is under $PROJ/apps/<something>/
  suffix="${c#${PROJ}/apps/}"
  if [ "$suffix" != "$c" ]; then
    # extract the app name (first path component after apps/)
    a="${suffix%%/*}"
    [ -z "$a" ] && continue
    candidate_doc="$PROJ/.claude/docs/apps/${a}.md"
    if [ -f "$candidate_doc" ]; then
      APP_DOC="$candidate_doc"
      APP_NAME="$a"
      break
    fi
  fi
done <<EOF
$CANDS
EOF

# Monorepo ROOT doc: a busca da raiz (ROOT_COVERED, sem APP_DOC) varre todos os
# apps — exige o sentinel por-doc do índice raiz; sem índice, o CLAUDE.md
# (basename "CLAUDE.md" casa com a raiz E a aninhada, então nunca tranca).
ROOT_DOC=""
if [ -d "$PROJ/.claude/docs/apps" ]; then
  if [ -f "$PROJ/.claude/docs/index.md" ]; then
    ROOT_DOC="$PROJ/.claude/docs/index.md"
  elif [ -f "$PROJ/CLAUDE.md" ]; then
    ROOT_DOC="$PROJ/CLAUDE.md"
  else
    ROOT_DOC="$PROJ/.claude/CLAUDE.md"
  fi
fi

# ---------------------------------------------------------------------------
# SENTINEL-FILE check (PRIMARY decision)
# posttooluse-doc-read.sh writes <temp>/claude-doc-guard-${SESSION}-${PHASH}
# the moment Claude reads any file under .claude/docs/ or .claude/CLAUDE.md.
# Check for that sentinel; if present → doc was consulted → pass (exit 0).
# Fail-open: any I/O issue → sentinel absent → continue to nudge.
# ---------------------------------------------------------------------------
PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
SENTINEL="${TMPD}/claude-doc-guard-${SESSION}-${PHASH}"
if [ -f "$SENTINEL" ]; then
  # Monorepo (furo B): o sentinel do projeto libera, MAS exige o da doc do app.
  if [ -z "$APP_DOC" ]; then
    # Furo B parcial (R5): busca na RAÍZ do monorepo varre todos os apps — o
    # sentinel do projeto (queimado ao ler a doc de QUALQUER app) não basta.
    # Exige o sentinel por-doc do índice raiz (ou do CLAUDE.md, sem índice);
    # doc de app NÃO destrava a busca da raiz.
    if [ -n "$ROOT_DOC" ] && [ "$ROOT_COVERED" = "1" ]; then
      DPHASH=$(printf '%s' "$(basename "$ROOT_DOC")" | cksum | cut -d' ' -f1)
      [ -f "${TMPD}/claude-doc-guard-${SESSION}-${PHASH}-doc-${DPHASH}" ] && exit 0
    else
      exit 0
    fi
  else
    # Chave = basename (espelha o posttooluse): imune à grafia do path.
    DPHASH=$(printf '%s' "$(basename "$APP_DOC")" | cksum | cut -d' ' -f1)
    [ -f "${TMPD}/claude-doc-guard-${SESSION}-${PHASH}-doc-${DPHASH}" ] && exit 0
  fi
fi

# ---------------------------------------------------------------------------
# Build deny message. Sem contador: enquanto o sentinel não existir (a doc não
# foi lida), TODA busca cega é negada. A saída é ler a doc — o sentinel libera
# na próxima tentativa. A porta de escape MAX_NUDGES caiu em 2026-08-04: depois
# de 3 avisos os agentes atravessavam e exploravam sem nunca abrir a doc — a
# disciplina que a constituição proíbe ("por derivação, não por disciplina").
# ---------------------------------------------------------------------------
LINE=$(bash "$SCRIPT_DIR/doc-detect.sh" --one "$PROJ" 2>/dev/null)
[ -z "$LINE" ] && exit 0
N=$(printf '%s' "$LINE" | cut -f3)
STALE=$(printf '%s' "$LINE" | cut -f4)
OOP=$(printf '%s' "$LINE" | cut -f5)

# List the real docs so the nudge is actionable (not just "read the index").
DOCLIST=$(for f in "$PROJ/.claude/docs"/*.md; do [ -e "$f" ] && basename "$f"; done | paste -sd ', ' -)
[ -n "$DOCLIST" ] && DOCLIST=" Docs: ${DOCLIST}."

# Staleness flag (TERNÁRIO por-scope): louder quando vermelho. NÃO muda a decisão
# (o contrato anti-loop é absoluto — o gate degrada, nunca trava de verdade; ver
# organism.md). Só o TEXTO do aviso escala.
STALEMSG=""
case "$STALE" in
  stale)   STALEMSG=" ⚠️ ESTA DOC ESTÁ DEFASADA: arquivo(s) do escopo mudaram desde a geração — leia mas trate como HIPÓTESE, confirme no código, e considere /project-doc." ;;
  unknown) STALEMSG=" ⚠️ staleness indeterminado (doc sem data/escopo) — não confie cegamente." ;;
esac

# Out-of-pattern flag (5th column from doc-detect.sh --one)
OOPMSG=""
if [ "$OOP" = "1" ]; then
  OOPMSG=" ⚠️ out_of_pattern=true: o projeto não segue o padrão project-doc v2 atual — doc pode estar incompleta ou desatualizada."
fi

# App-specific nudge vs monorepo-root nudge vs generic nudge
RELEASE_HINT=" Use a ferramenta Read em qualquer arquivo de .claude/docs/ ou .claude/CLAUDE.md; isso registra um sentinel e esta ação será liberada automaticamente na próxima tentativa."
if [ -n "$APP_NAME" ] && [ -n "$APP_DOC" ]; then
  APPMSG=" Para o app '${APP_NAME}', leia o doc específico em .claude/docs/apps/${APP_NAME}.md."
  READ_TARGET="${PROJ}/.claude/docs/apps/${APP_NAME}.md"
elif [ -n "$ROOT_DOC" ] && [ "$ROOT_COVERED" = "1" ]; then
  RDN="${ROOT_DOC#${PROJ}/}"
  APPMSG=" Para busca na raiz do monorepo, leia ${RDN}."
  READ_TARGET="${ROOT_DOC}"
  RELEASE_HINT=" Use a ferramenta Read em ${RDN}; só ele libera a busca da raiz — doc de app não destrava o monorepo."
else
  APPMSG=""
  # Point at whichever CLAUDE.md actually carries the project-doc:v2 marker
  # (handles projects with BOTH a hand-written root file and the real, nested
  # project-doc-generated one — e.g. ACME-APP); falls back to root-then-
  # nested existence. A hardcoded .claude/CLAUDE.md here would tell Claude to
  # read a file that doesn't exist for root-CLAUDE.md projects (e.g. Cybersec).
  if [ -f "${PROJ}/CLAUDE.md" ] && grep -q 'project-doc:v2' "${PROJ}/CLAUDE.md" 2>/dev/null; then
    CLAUDE_MD_PATH="${PROJ}/CLAUDE.md"
  elif [ -f "${PROJ}/.claude/CLAUDE.md" ] && grep -q 'project-doc:v2' "${PROJ}/.claude/CLAUDE.md" 2>/dev/null; then
    CLAUDE_MD_PATH="${PROJ}/.claude/CLAUDE.md"
  elif [ -f "${PROJ}/CLAUDE.md" ]; then
    CLAUDE_MD_PATH="${PROJ}/CLAUDE.md"
  else
    CLAUDE_MD_PATH="${PROJ}/.claude/CLAUDE.md"
  fi
  READ_TARGET="${CLAUDE_MD_PATH} e o doc relevante em .claude/docs/"
fi

MSG="📚 ${PROJ} tem documentação project-doc (${N} doc(s) em .claude/docs/).${DOCLIST}${APPMSG} Antes de busca cega ou de delegar exploração, leia ${READ_TARGET}.${STALEMSG}${OOPMSG}${RELEASE_HINT} A busca fica bloqueada até a doc ser lida."

hj_deny "$MSG"
exit 0
