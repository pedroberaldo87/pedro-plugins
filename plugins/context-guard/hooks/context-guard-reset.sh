#!/bin/bash
# SessionStart hook: clears THIS session's context-guard state — nunca com glob.
# O glob antigo (`-warned-*`) apagava o sentinel de TODAS as sessões, rearmando o
# bloqueio das já-abertas. Agora limpa só a própria sessão.
# Sem jq o session_id sai vazio e o reset apagaria sentinel de outra sessão.
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "context-guard-reset"; exit 0; }
# Diretório temporário DO SISTEMA — perguntado, nunca assumido (ver lib-tmpdir.sh).
# shellcheck source=/dev/null
. "$HJ_DIR/lib-tmpdir.sh" 2>/dev/null
TMPD=$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
SESSION_ID=$(hj_campo "$(cat)" session_id)
[ -n "$SESSION_ID" ] && rm -f "${TMPD}/claude-context-pct-${SESSION_ID}" "${TMPD}/claude-context-warned-${SESSION_ID}"
# Prune de arquivos órfãos de sessões mortas (>1 dia) — evita acúmulo no temporário.
# A barra final é obrigatória: no macOS o temporário pode ser symlink, e o find não
# atravessa symlink dado como argumento sem ela.
find "$TMPD/" -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete 2>/dev/null
find "$TMPD/" -maxdepth 1 -name 'claude-context-warned-*' -mtime +1 -delete 2>/dev/null
exit 0
