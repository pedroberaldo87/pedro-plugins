#!/bin/bash
# posttooluse-doc-read.sh — RESOLVE the doc-guard when Claude actually READS a
# project's documentation (a casa da doc or .claude/CLAUDE.md). The PreToolUse
# guard's sentinel now means "the doc was consulted", not "Claude was warned" —
# so the guard keeps nudging on blind searches until the doc is genuinely read,
# then goes quiet. Mirrors the PHASH the guard uses.
# Fail-open: any error → exit 0. Never blocks.

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
hj_leitor >/dev/null 2>&1 || { hj_avisa "posttooluse-doc-read"; exit 0; }
INPUT=$(cat 2>/dev/null)
TOOL=$(hj_campo "$INPUT" tool_name)
[ "$TOOL" = "Read" ] || exit 0
SESSION=$(hj_campo_ou "$INPUT" session_id "")
# payload sem sessão: liberado — o sentinela "unknown" seria compartilhado entre sessões (o defeito do context-guard v1.1)
[ -n "$SESSION" ] || exit 0
FP=$(hj_campo "$INPUT" tool_input.file_path)
[ -z "$FP" ] && exit 0
CWD=$(hj_campo "$INPUT" cwd)
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
  */.claude/docs/*)    PROJ="${FP%%/.claude/docs/*}" ;;  # casa-ok: reconhece o caminho LIDO na entrada, não escreve a casa
  */.claude/CLAUDE.md) PROJ="${FP%/.claude/CLAUDE.md}" ;;
  */CLAUDE.md)         PROJ="${FP%/CLAUDE.md}" ;;
  *) exit 0 ;;
esac
[ -n "$PROJ" ] || exit 0

PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
touch "${TMPD}/claude-doc-guard-${SESSION}-${PHASH}" 2>/dev/null
# Sentinel POR-DOC (furo B): além do do projeto, grava o da doc lida — no
# monorepo o gate exige o sentinel da doc específica do app, não só do projeto.
# Chave = BASENAME da doc: igualdade só pelo nome do arquivo, não pelo path
# absoluto — leitura via './'-relativo ou symlink da raiz hasheia igual (senão
# a busca do app fica trancada mesmo depois de ler a doc certa).
DPHASH=$(printf '%s' "$(basename "$FP")" | cksum | cut -d' ' -f1)
touch "${TMPD}/claude-doc-guard-${SESSION}-${PHASH}-doc-${DPHASH}" 2>/dev/null

# LOUD-NA-LEITURA (decisão de design com o Fable): se o doc que o agente ACABOU
# de ler está DEFASADO, injeta um aviso AGORA — o momento exato do consumo. É
# PostToolUse (injeta contexto, SEM permissionDecision) → estruturalmente incapaz
# de loopar (ao contrário de um deny no Read, que bloquearia a ação que libera o
# sentinel). Só p/ leitura de doc de concern (a casa da doc), não do índice.
case "$FP" in
  */.claude/docs/*) : ;;  # casa-ok: reconhece o caminho LIDO na entrada, não escreve a casa
  *) exit 0 ;;
esac
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATTERN_CHECK_PY="$SCRIPT_DIR/../lib/pattern_check.py"
PY3=$(command -v python3 2>/dev/null)
"$PY3" --version >/dev/null 2>&1 || exit 0
[ -z "$PY3" ] && exit 0
[ -f "$PATTERN_CHECK_PY" ] || exit 0
STALE=$("$PY3" "$PATTERN_CHECK_PY" --project-staleness "$PROJ" 2>/dev/null)
MSG=""
case "$STALE" in
  stale)   . "$SCRIPT_DIR/lib-rodada.sh" 2>/dev/null && rodada_doc "$PROJ"
           MSG="⚠️ A doc que você acabou de ler ($(basename "$FP")) está DEFASADA
• Arquivo(s) do escopo dela mudaram desde a geração
• Trate o conteúdo como HIPÓTESE e confirme no código antes de agir
• Pra atualizar rode /${RODADA_CMD:-doc-touch}
• ${RODADA_MOTIVO:-atraso não medido}" ;;
  unknown) MSG="⚠️ Staleness da doc que você leu ($(basename "$FP")) é INDETERMINADO (sem data/escopo). Não confie cegamente — confirme no código." ;;
esac
[ -z "$MSG" ] && exit 0
hj_ctx PostToolUse "$MSG"
exit 0
