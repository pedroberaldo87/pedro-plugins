#!/bin/bash
# posttooluse-doc-read.sh — RESOLVE the doc-guard when Claude actually READS a
# project's documentation (.claude/docs/* or .claude/CLAUDE.md). The PreToolUse
# guard's sentinel now means "the doc was consulted", not "Claude was warned" —
# so the guard keeps nudging on blind searches until the doc is genuinely read,
# then goes quiet. Mirrors the PHASH the guard uses.
# Fail-open: any error → exit 0. Never blocks.

command -v jq >/dev/null 2>&1 || exit 0
INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL" = "Read" ] || exit 0
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
FP=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$FP" ] && exit 0
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"
# Normalize to ABSOLUTE — the guard derives PROJ absolute (find_doc_up/doc-detect),
# so a relative file_path here would hash to a different PHASH and never resolve
# the sentinel (guard would nudge forever).
case "$FP" in /*) : ;; *) FP="$CWD/$FP" ;; esac

# Only a project-doc file resolves the guard. Derive the project dir so the
# sentinel matches the one the guard checks. CLAUDE.md at project ROOT (Claude
# Code's native convention) resolves it too, not just the nested .claude/CLAUDE.md —
# order matters: the more specific nested pattern is tried first.
case "$FP" in
  */.claude/docs/*)    PROJ="${FP%%/.claude/docs/*}" ;;
  */.claude/CLAUDE.md) PROJ="${FP%/.claude/CLAUDE.md}" ;;
  */CLAUDE.md)         PROJ="${FP%/CLAUDE.md}" ;;
  *) exit 0 ;;
esac
[ -n "$PROJ" ] || exit 0

PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
touch "/tmp/claude-doc-guard-${SESSION}-${PHASH}" 2>/dev/null

# LOUD-NA-LEITURA (decisão de design com o Fable): se o doc que o agente ACABOU
# de ler está DEFASADO, injeta um aviso AGORA — o momento exato do consumo. É
# PostToolUse (injeta contexto, SEM permissionDecision) → estruturalmente incapaz
# de loopar (ao contrário de um deny no Read, que bloquearia a ação que libera o
# sentinel). Só p/ leitura de doc de concern (.claude/docs/*), não do índice.
case "$FP" in
  */.claude/docs/*) : ;;
  *) exit 0 ;;
esac
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATTERN_CHECK_PY="$SCRIPT_DIR/../lib/pattern_check.py"
PY3=$(command -v python3 2>/dev/null)
[ -z "$PY3" ] && exit 0
[ -f "$PATTERN_CHECK_PY" ] || exit 0
STALE=$("$PY3" "$PATTERN_CHECK_PY" --project-staleness "$PROJ" 2>/dev/null)
MSG=""
case "$STALE" in
  stale)   MSG="⚠️ A doc que você acabou de ler ($(basename "$FP")) está DEFASADA: arquivo(s) do escopo dela mudaram desde a geração. Trate o conteúdo como HIPÓTESE — confirme no código antes de agir. Pra atualizar: **/doc-touch** (incremental e barato — o caso comum, quando a defasagem vem do trabalho recente) ou **/project-doc** (mineração completa — drift antigo/amplo, doc nunca minerada, ou último FULL há +30 dias)." ;;
  unknown) MSG="⚠️ Staleness da doc que você leu ($(basename "$FP")) é INDETERMINADO (sem data/escopo). Não confie cegamente — confirme no código." ;;
esac
[ -z "$MSG" ] && exit 0
jq -n --arg c "$MSG" \
  '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$c}}' 2>/dev/null
exit 0
