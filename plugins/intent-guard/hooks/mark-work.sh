#!/usr/bin/env bash
# PostToolUse(Edit|Write|MultiEdit|NotebookEdit) — marca que ESTA sessão teve
# trabalho de verdade. O gate de entrega (delivery-audit.sh) só age se esta
# sentinela existir: sessão só de conversa nunca é bloqueada no Stop.
set -uo pipefail
MODE_FILE="$HOME/.claude/intent-guard/mode"
[ -f "$MODE_FILE" ] && [ "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" = "off" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois não há session_id — e aí o hook AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
# Diretório temporário DO SISTEMA — perguntado, nunca assumido (ver lib-tmpdir.sh).
# shellcheck source=/dev/null
. "$HJ_DIR/lib-tmpdir.sh" 2>/dev/null
TMPD=$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
type hj_campo >/dev/null 2>&1 || exit 0
INPUT="$(cat 2>/dev/null || true)"
hj_leitor >/dev/null 2>&1 || { hj_avisa "mark-work"; exit 0; }
SID="$(hj_campo "$INPUT" session_id)"
[ -n "$SID" ] && touch "${TMPD}/intent-guard-work-${SID}" 2>/dev/null
exit 0
