#!/bin/bash
# sessionstart-orfaos.sh — a rede que pega quem morreu sem colher.
#
# Sessão que caiu, foi limpa ou fechou no tapa nunca chega ao fim formal, e o
# registro dela fica para trás com processos ainda de pé — foi assim que dois
# servidores do mesmo projeto chegaram a 2h38 e 1h07 de vida na medição de
# 2026-08-05. Aqui, registro cuja sessão dona não responde mais vira lixo.
#
#   evento     SessionStart
#   canal      systemMessage — só quando algo foi encerrado
#   fail-open  dependência ausente ou motor sumido → exit 0, nada morre
#   desliga    LIXEIRO=0 (tudo) · LIXEIRO_ORFAOS=0 (só esta varredura)

[ "${LIXEIRO:-1}" = "0" ] && exit 0
[ "${LIXEIRO_ORFAOS:-1}" = "0" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "sessionstart-orfaos"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
[ -n "$PY3" ] || exit 0
"$PY3" --version >/dev/null 2>&1 || exit 0

MOTOR="${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py"
[ -f "$MOTOR" ] || exit 0

INPUT=$(cat 2>/dev/null)
SID=$(hj_campo "$INPUT" session_id)

MORTOS=$("$PY3" "$MOTOR" orfaos ${SID:+--sessao "$SID"} 2>/dev/null) || exit 0
[ -n "$MORTOS" ] || exit 0

MSG=$(printf '%s' "$MORTOS" | "$PY3" -c '
import json, sys
try:
    mortos = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not mortos:
    sys.exit(0)
mb = sum(m.get("rss_mb", 0) for m in mortos)
print("🚚💨 Caminhão do lixo passando ♻️")
print("   Sessão anterior deixou %d processo(s) de pé — encerrei, %d MB de volta." % (len(mortos), mb))
' 2>/dev/null)

[ -n "$MSG" ] && hj_msg "$MSG"
exit 0
