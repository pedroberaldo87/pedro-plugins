#!/bin/bash
# SessionStart hook: clears THIS session's context-guard state — nunca com glob.
# O glob antigo (`-warned-*`) apagava o sentinel de TODAS as sessões, rearmando o
# bloqueio das já-abertas. Agora limpa só a própria sessão.
# Sem jq o session_id sai vazio e o reset apagaria sentinel de outra sessão.
command -v jq >/dev/null 2>&1 || exit 0
SESSION_ID=$(jq -r '.session_id // empty' 2>/dev/null)
[ -n "$SESSION_ID" ] && rm -f "/tmp/claude-context-pct-${SESSION_ID}" "/tmp/claude-context-warned-${SESSION_ID}"
# Prune de arquivos órfãos de sessões mortas (>1 dia) — evita acúmulo em /tmp.
find /tmp -maxdepth 1 -name 'claude-context-pct-*' -mtime +1 -delete 2>/dev/null
find /tmp -maxdepth 1 -name 'claude-context-warned-*' -mtime +1 -delete 2>/dev/null
exit 0
