#!/bin/bash
# pretooluse-doc-guard.sh — gate (RF8).
# When a blind search (Grep/Glob, Bash grep|rg|find|..., or a code-EXPLORING Task
# subagent) is about to run in a project that has project-doc documentation, DENY
# it and redirect to .claude/docs/. The deny lists the actual docs and flags
# staleness. Mirrors graphify-guard; separate sentinel.
# Fail-open: any error → exit 0 (action proceeds).
#
# PRIMARY decision: SENTINEL-FILE
#   posttooluse-doc-read.sh writes /tmp/claude-doc-guard-${SESSION}-${PHASH} the
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
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

# Candidate dirs this search/exploration might touch (CWD always in play).
CANDS="$CWD"
case "$TOOL" in
  Grep|Glob)
    P=$(printf '%s' "$INPUT" | jq -r '.tool_input.path // empty' 2>/dev/null)
    [ -n "$P" ] && CANDS="$CANDS
$P"
    ;;
  Bash)
    CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    # only intercept blind text/file search; everything else passes
    printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]_])(grep|egrep|fgrep|rg|ripgrep|ag|ack|find)([^[:alnum:]_]|$)' || exit 0
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
    ST=$(printf '%s' "$INPUT" | jq -r '.tool_input.subagent_type // empty' 2>/dev/null)
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
while IFS= read -r c; do
  [ -z "$c" ] && continue
  # Normalize to absolute
  case "$c" in /*) : ;; *) c="$CWD/$c" ;; esac
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

# ---------------------------------------------------------------------------
# SENTINEL-FILE check (PRIMARY decision)
# posttooluse-doc-read.sh writes /tmp/claude-doc-guard-${SESSION}-${PHASH}
# the moment Claude reads any file under .claude/docs/ or .claude/CLAUDE.md.
# Check for that sentinel; if present → doc was consulted → pass (exit 0).
# Fail-open: any I/O issue → sentinel absent → continue to nudge.
# ---------------------------------------------------------------------------
PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
SENTINEL="/tmp/claude-doc-guard-${SESSION}-${PHASH}"
if [ -f "$SENTINEL" ]; then
  exit 0
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

# App-specific nudge vs generic nudge
if [ -n "$APP_NAME" ] && [ -n "$APP_DOC" ]; then
  APPMSG=" Para o app '${APP_NAME}', leia o doc específico em .claude/docs/apps/${APP_NAME}.md."
  READ_TARGET="${PROJ}/.claude/docs/apps/${APP_NAME}.md"
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

MSG="📚 ${PROJ} tem documentação project-doc (${N} doc(s) em .claude/docs/).${DOCLIST}${APPMSG} Antes de busca cega ou de delegar exploração, leia ${READ_TARGET}.${STALEMSG}${OOPMSG} Use a ferramenta Read em qualquer arquivo de .claude/docs/ ou .claude/CLAUDE.md; isso registra um sentinel e esta ação será liberada automaticamente na próxima tentativa. A busca fica bloqueada até a doc ser lida."

jq -n --arg r "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
