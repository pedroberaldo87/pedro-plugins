#!/bin/bash
# sessionend-colhe.sh — a colheita completa, no fim da sessão.
#
# Aqui não há discriminador: tudo que ESTA sessão anotou e ainda vive é
# encerrado, ocioso ou não. A sessão acabou; o servidor que ela abriu não serve
# mais a ninguém.
#
#   evento     SessionEnd
#   canal      nenhum — a sessão está fechando, não há a quem falar; o registro
#              do que morreu fica em ~/.claude/lixeiro/colhido.jsonl
#   fail-open  dependência ausente ou motor sumido → exit 0, nada morre
#   desliga    LIXEIRO=0

[ "${LIXEIRO:-1}" = "0" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "sessionend-colhe"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
[ -n "$PY3" ] || exit 0
"$PY3" --version >/dev/null 2>&1 || exit 0

MOTOR="${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py"
[ -f "$MOTOR" ] || exit 0

INPUT=$(cat 2>/dev/null)
SID=$(hj_campo "$INPUT" session_id)
[ -n "$SID" ] || exit 0

# `/clear` e `resume` NÃO são fim de trabalho: o que acabou foi a conversa, e o
# terminal, os servidores e a suíte em segundo plano seguem sendo do usuário.
# Colher aqui matava a suíte de quem só quis limpar o contexto — e sem canal de
# saída neste evento, matava em silêncio.
RAZAO=$(hj_campo "$INPUT" reason)
case "$RAZAO" in clear|resume) exit 0 ;; esac

# Quem apaga o registro é o motor, e só quando não sobrou processo de pé: o que
# foi poupado por estar trabalhando precisa da procedência para a varredura de
# órfãos terminar o serviço na abertura seguinte.
"$PY3" "$MOTOR" colhe-sessao --sessao "$SID" >/dev/null 2>&1 || :
exit 0
