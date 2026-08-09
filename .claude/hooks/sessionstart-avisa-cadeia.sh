#!/bin/bash
# sessionstart-avisa-cadeia.sh — avisa, no arranque, que esta máquina roda código VELHO.
#
# POR QUE EXISTE. Em 2026-08-09 o dono revisou, testou e aprovou a versão 0.4.0 do
# `gauntlet` durante uma sessão inteira. O que rodava aqui era a 0.3.2, instalada
# dias antes — a trava que ele acreditava estar de pé não tinha nenhum conserto, e
# nada dizia isso. Editar o repositório NÃO muda o que o harness carrega: ele lê o
# cache em ~/.claude/plugins/, e o cache só troca com `claude plugin update` mais
# um reinício da sessão.
#
# É hook DO REPOSITÓRIO, não do plugin, e o motivo é o público: só quem tem o
# repositório na mão pode comparar as duas versões. Quem apenas instalou o
# marketplace não tem com o que comparar, e para ele o `claude plugin update`
# normal já resolve.
#
# Fala uma vez por sessão e nunca bloqueia. Kill-switch: CADEIA_GATE=0.

[ "${CADEIA_GATE:-1}" = "0" ] && exit 0

IFS= read -r -d '' ENTRADA 2>/dev/null || true

RAIZ="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CHECK="$RAIZ/scripts/cadeia_check.py"
[ -f "$CHECK" ] || exit 0
command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1 || exit 0

# Um aviso por sessão. Sem session_id no payload o PPID separa as sessões — mesma
# regra do sessionstart-deps.sh, e pelo mesmo motivo: repetir a cada arranque de
# subprocesso transformaria o aviso em ruído que ninguém lê.
SID=""
case "$ENTRADA" in
  *'"session_id"'*)
    SID="${ENTRADA#*\"session_id\"}"; SID="${SID#*\"}"; SID="${SID%%\"*}" ;;
esac
[ -n "$SID" ] || SID="sem-id-$PPID"
case "$SID" in *[!A-Za-z0-9._-]*) SID="sem-id-$PPID" ;; esac

MARCA="${TMPDIR:-/tmp}/cadeia-avisou-$SID"
[ -f "$MARCA" ] && exit 0

SAIDA=$(cd "$RAIZ" && python3 "$CHECK" --maquina --quieto 2>/dev/null)
[ -n "$SAIDA" ] || exit 0
: > "$MARCA" 2>/dev/null

# O aviso vai aos DOIS públicos: ao dono, que decide atualizar, e ao modelo, que
# senão passa a sessão testando um código que não é o que está rodando.
TEXTO="⚠️ Esta máquina está rodando código VELHO de plugin — o que você editar no repositório NÃO é o que roda nesta sessão.

$SAIDA

Enquanto não atualizar e reiniciar, teste no repositório vale como leitura de código, nunca como prova de comportamento."

HJ="$RAIZ/_shared/hook-json.sh"
if [ -f "$HJ" ]; then
  # shellcheck source=/dev/null
  . "$HJ" 2>/dev/null
  if type hj_msg_ctx >/dev/null 2>&1; then
    hj_msg_ctx "SessionStart" "$TEXTO"
    exit 0
  fi
fi
printf '%s\n' "$TEXTO" >&2
exit 0
