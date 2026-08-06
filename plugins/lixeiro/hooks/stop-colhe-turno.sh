#!/bin/bash
# stop-colhe-turno.sh — a coleta do fim de turno, e o aviso do que sobrou.
#
# Por que o fim do TURNO e não só o fim da sessão (decisão de 2026-08-05): sessão
# interrompida no tapa nunca chega ao fim formal, e o lixo ficaria de pé até a
# abertura seguinte. Mas o fim do turno é justamente quando o servidor do turno
# ainda serve ao próximo — então aqui a colheita é SELETIVA:
#
#   efêmero (suíte, build) ainda vivo  → é lixo certo, morre
#   serviço com CPU parada desde o turno anterior → ocioso, morre
#   serviço com CPU subindo           → está em uso, SOBREVIVE
#
# A foto de CPU do turno é tirada DEPOIS da colheita, para o próximo turno ter
# contra o que comparar.
#
#   evento     Stop
#   canal      systemMessage — só quando algo foi encerrado ou o teto foi passado
#   fail-open  dependência ausente ou motor sumido → exit 0, nada morre
#   desliga    LIXEIRO=0 (tudo) · LIXEIRO_TURNO=0 (só a coleta do turno)

[ "${LIXEIRO:-1}" = "0" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "stop-colhe-turno"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
[ -n "$PY3" ] || exit 0
"$PY3" --version >/dev/null 2>&1 || exit 0

MOTOR="${CLAUDE_PLUGIN_ROOT}/lib/lixeiro.py"
[ -f "$MOTOR" ] || exit 0

INPUT=$(cat 2>/dev/null)
# Stop disparado por outro hook de Stop já ativo → sai (anti-loop).
[ "$(hj_campo "$INPUT" stop_hook_active)" = "true" ] && exit 0
SID=$(hj_campo "$INPUT" session_id)
[ -n "$SID" ] || exit 0

MORTOS="[]"
if [ "${LIXEIRO_TURNO:-1}" != "0" ]; then
  MORTOS=$("$PY3" "$MOTOR" colhe-turno --sessao "$SID" 2>/dev/null) || MORTOS="[]"
fi
[ -n "$MORTOS" ] || MORTOS="[]"

# A foto de CPU para o próximo turno comparar. Sem ela, todo serviço pareceria
# ocioso na volta seguinte e seria derrubado no primeiro fim de turno.
"$PY3" "$MOTOR" marca-cpu --sessao "$SID" >/dev/null 2>&1 || :

MSG=$(printf '%s' "$MORTOS" | "$PY3" -c '
import json, sys
try:
    mortos = json.load(sys.stdin)
except Exception:
    sys.exit(0)
if not mortos:
    sys.exit(0)
mb = sum(m.get("rss_mb", 0) for m in mortos)
alvo = mortos[0].get("cmd", "")[:60]
if len(mortos) == 1:
    print("🧹 Encerrei 1 processo aberto por esta sessão, liberando %d MB." % mb)
else:
    print("🧹 Encerrei %d processos que ficaram abertos, somando %d MB." % (len(mortos), mb))
' 2>/dev/null)

# O aviso do que NÃO é colhível — o lixo sem procedência, que só a faxina manual
# encerra. Uma vez por sessão e só acima do teto: o objetivo é você saber que a
# memória está indo embora, não receber a mesma contagem a cada turno.
AVISADO="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/lixeiro/avisado-$(printf '%s' "$SID" | tr -c 'A-Za-z0-9_.-' '_')"
if [ -z "$MSG" ] && [ ! -f "$AVISADO" ] && [ "${LIXEIRO_AVISO:-1}" != "0" ]; then
  AVISO=$("$PY3" "$MOTOR" inventario --idade-min "${LIXEIRO_IDADE_AVISO:-1800}" 2>/dev/null | "$PY3" -c '
import json, os, sys
try:
    itens = json.load(sys.stdin)
except Exception:
    sys.exit(0)
soltos = [i for i in itens if i.get("classe") != "intocavel"]
mb = sum(i.get("rss_mb", 0) for i in soltos)
teto_n = int(os.environ.get("LIXEIRO_TETO_N", "4"))
teto_mb = int(os.environ.get("LIXEIRO_TETO_MB", "400"))
if len(soltos) >= teto_n or mb >= teto_mb:
    print("🗑 %d processos de desenvolvimento parados somam %d MB de memória." % (len(soltos), mb))
    print("🧹 Nenhum foi aberto por esta sessão — rode /faxina para escolher o que encerrar.")
' 2>/dev/null)
  if [ -n "$AVISO" ]; then
    MSG="$AVISO"
    : > "$AVISADO" 2>/dev/null || :
  fi
fi

[ -n "$MSG" ] && hj_msg "$MSG"
exit 0
