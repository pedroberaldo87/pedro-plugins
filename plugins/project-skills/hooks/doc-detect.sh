#!/bin/bash
# doc-detect.sh — shared helper: detect project-doc documentation (CLAUDE.md + .claude/docs/).
#
# CLAUDE.md location: Claude Code's native convention is project ROOT (confirmed
# empirically — that's where the harness actually loads project instructions from);
# some older project-doc runs wrote it nested at .claude/CLAUDE.md. Both are accepted
# (root checked first) — see find_claude_md(). Fixing a real bug: the detection used
# to hardcode .claude/CLAUDE.md only, so it silently found nothing for root-CLAUDE.md
# projects (e.g. Cybersec) and could escalate up to an unrelated ancestor directory.
#
# Two modes:
#   doc-detect.sh <dir>          → descend up to 3 levels, list every project with a doc
#   doc-detect.sh --one <proj>   → report only <proj> (used by the guard)
#
# Emits TSV lines: DOC<TAB>project_dir<TAB>n_docs<TAB>staleness<TAB>out_of_pattern
# (4th column = staleness TERNÁRIO: fresh | stale | unknown — scope-based, via
# pattern_check.py. 'unknown' = indeterminado (sem git/generated/scope): fail-LOUD,
# nunca finge fresco. Substitui a antiga CONTAGEM de arquivos.)
# (5th column = out_of_pattern: 1 if pattern_check reports in_pattern=false; 0 otherwise.
# Fails open: python missing / lib missing / any error → 0, never blocks the caller.)
# Fail-open: any error → no output, exit 0. Never blocks the caller.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERN_CHECK_PY="$SCRIPT_DIR/../lib/pattern_check.py"
# A casa da doc mudou de lugar (docs/ na raiz); quem precisa do caminho pergunta
# ao resolvedor, nunca crava. Sem ele, este detector responde "projeto sem doc".
# shellcheck source=/dev/null
. "$SCRIPT_DIR/lib-casa-da-doc.sh"

# find_claude_md <project_dir> — prints the CLAUDE.md path. Prefers whichever
# location actually carries the project-doc:v2 marker (handles projects that have
# BOTH — e.g. a hand-written root CLAUDE.md alongside the real, project-doc-
# generated nested one, seen in the wild: ACME-APP). Falls back to
# root-then-nested existence when neither/the check is inconclusive. Prints
# nothing if neither exists.
find_claude_md() {
  local PROJ="$1"
  local ROOT_MD="$PROJ/CLAUDE.md" NESTED_MD="$PROJ/.claude/CLAUDE.md"
  if [ -f "$ROOT_MD" ] && grep -q 'project-doc:v2' "$ROOT_MD" 2>/dev/null; then
    printf '%s' "$ROOT_MD"; return
  fi
  if [ -f "$NESTED_MD" ] && grep -q 'project-doc:v2' "$NESTED_MD" 2>/dev/null; then
    printf '%s' "$NESTED_MD"; return
  fi
  if [ -f "$ROOT_MD" ]; then
    printf '%s' "$ROOT_MD"
  elif [ -f "$NESTED_MD" ]; then
    printf '%s' "$NESTED_MD"
  fi
}

# doc_out_of_pattern <project_dir> — returns 1 if in_pattern=false, 0 otherwise.
# Fails open: python missing / lib missing / any error → 0.
doc_out_of_pattern() {
  local PROJ="$1"
  [ -f "$PATTERN_CHECK_PY" ] || { echo 0; return; }
  local PY3
  PY3=$(command -v python3 2>/dev/null)
  "$PY3" --version >/dev/null 2>&1 || { echo 0; return; }
  [ -z "$PY3" ] && { echo 0; return; }
  local JSON IN_PAT
  JSON=$("$PY3" "$PATTERN_CHECK_PY" --project-root "$PROJ" --json 2>/dev/null)
  # Note: pattern_check.py exits 1 when out_of_pattern — that is not an error here;
  # bail only if JSON is empty (crash / missing lib / permission error).
  [ -z "$JSON" ] && { echo 0; return; }
  IN_PAT=$(printf '%s' "$JSON" | grep -o '"in_pattern": *[^,}]*' | grep -o 'true\|false' | head -1)
  if [ "$IN_PAT" = "false" ]; then echo 1; else echo 0; fi
}

# doc_staleness <project_dir> — TERNÁRIO por-scope: fresh|stale|unknown.
# Delega ao pattern_check.py (scope-based, tered): stale = arquivo do `scope:` de
# algum doc mudou desde `generated:`; unknown = sem git/sem generated/sem scope
# (fail-LOUD — NUNCA finge "fresco"); fresh = scope intacto. Substitui o antigo
# heurístico de CONTAGEM (>8) que era cego a QUAIS arquivos e fail-open silencioso.
# Fail-open só na borda de erro do python (→ unknown, visível), nunca "fresco".
doc_staleness() {
  local PROJ="$1" PY3 OUT
  PY3=$(command -v python3 2>/dev/null)
  "$PY3" --version >/dev/null 2>&1 || { echo unknown; return; }
  [ -z "$PY3" ] && { echo unknown; return; }
  [ -f "$PATTERN_CHECK_PY" ] || { echo unknown; return; }
  OUT=$("$PY3" "$PATTERN_CHECK_PY" --project-staleness "$PROJ" 2>/dev/null)
  case "$OUT" in fresh|stale|unknown) echo "$OUT" ;; *) echo unknown ;; esac
}

# doc_line <project_dir> — print one TSV line if project_dir has a project-doc CLAUDE.md
# (root or nested) AND a casa-da-doc dir — the dir requirement keeps an arbitrary
# hand-written root CLAUDE.md (no project-doc docs) from being reported as a project-doc
# project now that root is checked too.
doc_line() {
  local PROJ="$1" CLAUDE_MD
  CLAUDE_MD=$(find_claude_md "$PROJ")
  [ -z "$CLAUDE_MD" ] && return 1
  local CASA
  CASA=$(casa_da_doc "$PROJ")
  [ -d "$CASA" ] || return 1
  local N STALE OOP
  N=$(find "$CASA" -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
  STALE=$(doc_staleness "$PROJ")
  OOP=$(doc_out_of_pattern "$PROJ")
  printf 'DOC\t%s\t%s\t%s\t%s\n' "$PROJ" "${N:-0}" "${STALE:-0}" "${OOP:-0}"
}

# --one mode: just report the given project dir.
if [ "$1" = "--one" ]; then
  doc_line "$2"
  exit 0
fi

# descend mode: scan <dir> + up to a few levels for CLAUDE.md (root or nested).
ROOT="${1:-$PWD}"
[ -d "$ROOT" ] || exit 0

# Noise filter (LOAD-BEARING): worktrees/_repos-antigos/.next/backups duplicam a
# árvore de docs ~10x — sem podar, o hook surfacearia uma cópia legada/de-worktree
# como projeto fresco (o agente leria doc de 2025 com carimbo de atual). Casa o
# CENSUS_PRUNE do organism.py (fonte única do filtro; se um mudar, alinhe o outro).
DOC_FILES=$(find "$ROOT" -maxdepth 6 -type d \( \
    -name node_modules -o -name .git -o -name _repos-antigos -o -name .next \
    -o -name worktrees -o -name backups -o -name .project-doc -o -name legacy-pre-migracao \
  \) -prune \
  -o -type f -name 'CLAUDE.md' -print 2>/dev/null)
[ -z "$DOC_FILES" ] && exit 0

SEEN=""
while IFS= read -r CMD; do
  [ -z "$CMD" ] && continue
  case "$CMD" in
    */.claude/CLAUDE.md) PROJ=$(dirname "$(dirname "$CMD")") ;;   # project dir = parent of .claude
    *)                   PROJ=$(dirname "$CMD") ;;                # root CLAUDE.md
  esac
  case "$SEEN" in *"|${PROJ}|"*) continue ;; esac   # dedupe (a project can have both)
  SEEN="${SEEN}|${PROJ}|"
  doc_line "$PROJ"
done <<< "$DOC_FILES"
exit 0
