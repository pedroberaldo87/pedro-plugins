#!/bin/bash
# posttooluse-anota.sh — anota na origem o comando que pode ter aberto processo.
#
# É a base de tudo: sem esta anotação, nenhum processo é candidato à colheita.
# O motor decide se o comando é abridor; este hook só entrega o que aconteceu.
#
#   evento     PostToolUse[Bash]
#   canal      nenhum — este hook não fala com ninguém, só grava
#   fail-open  dependência ausente, entrada ilegível ou motor sumido → exit 0
#   desliga    LIXEIRO=0
#
# ⚠️ Nunca imprima nada aqui. O canal do PostToolUse entra no contexto do modelo,
# e um hook que anota não tem o que dizer a ele — quem fala é o do fim do turno.

[ "${LIXEIRO:-1}" = "0" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "posttooluse-anota"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
[ -n "$PY3" ] || exit 0
"$PY3" --version >/dev/null 2>&1 || exit 0

MOTOR="${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py"
[ -f "$MOTOR" ] || exit 0

INPUT=$(cat 2>/dev/null)
[ -n "$INPUT" ] || exit 0

CMD=$(hj_campo "$INPUT" tool_input.command)
[ -n "$CMD" ] || exit 0
CWD=$(hj_campo "$INPUT" cwd)
SID=$(hj_campo "$INPUT" session_id)
[ -n "$SID" ] || exit 0

# O dono da sessão: o processo do harness, que é o avô deste hook. É por ele que
# a varredura de órfãos sabe, depois, que a sessão morreu sem colher.
DONO=$(ps -o ppid= -p "$PPID" 2>/dev/null | tr -d ' ')

"$PY3" "$MOTOR" anota --sessao "$SID" --cmd "$CMD" --cwd "$CWD" \
  ${DONO:+--dono "$DONO"} >/dev/null 2>&1 || :
exit 0
