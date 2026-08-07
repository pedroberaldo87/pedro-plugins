#!/bin/bash
# Suíte do guarda do gauntlet — o que ele nega, o que ele deixa passar, e onde desiste.
#
# A trava que ele implementa nasceu de uma falha medida: o orquestrador leu sete
# relatórios de construtor e aceitou todos sem lançar juiz. Proibir por escrito foi o
# que já falhou; aqui a proibição é o hook.
#
#   bash plugins/gauntlet/hooks/test_gauntlet_hooks.sh

set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
HOOK="$AQUI/pretooluse-gauntlet.sh"
FALHAS=0

ok()   { printf '  ok   %s\n' "$1"; }
bad()  { printf '  FAIL %s\n' "$1"; FALHAS=$((FALHAS+1)); }
diz()  { [ "$2" = "$3" ] && ok "$1" || bad "$1 (esperava '$3', veio '$2')"; }

RAIZ_T=$(mktemp -d)
export CLAUDE_CONFIG_DIR="$RAIZ_T"
mkdir -p "$RAIZ_T/gauntlet"
SID="sessao-de-teste"
EVENTO='{"session_id":"'"$SID"'","tool_name":"Agent"}'

roda() { printf '%s' "$EVENTO" | bash "$HOOK" 2>/dev/null; }

echo "SEM MISSÃO — o guarda é mudo"
SAIDA=$(roda)
diz "sem sinal, não diz nada" "$SAIDA" ""

echo
echo "COM MISSÃO DE PÉ — o caminho de sub-agente avulso não existe"
: > "$RAIZ_T/gauntlet/ativo-$SID"
SAIDA=$(roda)
case "$SAIDA" in
  *deny*) ok "com sinal aceso, o disparo é negado" ;;
  *)      bad "com sinal aceso, o disparo é negado (veio: ${SAIDA:0:60})" ;;
esac
case "$SAIDA" in
  *Workflow*) ok "e a negação diz por onde o trabalho passa" ;;
  *)          bad "e a negação diz por onde o trabalho passa" ;;
esac
case "$SAIDA" in
  *fecho_check*) ok "e diz quem apaga o sinal — não é quem conduz" ;;
  *)             bad "e diz quem apaga o sinal" ;;
esac

echo
echo "A SAÍDA DE EMERGÊNCIA — guarda que trava com o dono fora custa mais que o defeito"
for _ in 1 2 3; do roda >/dev/null; done
SAIDA=$(roda)
diz "depois do teto de negações, ele desiste e libera" "$SAIDA" ""
[ -s "$RAIZ_T/gauntlet/desistencias.log" ] \
  && ok "e a desistência fica registrada" \
  || bad "e a desistência fica registrada"

echo
echo "O SINAL ÓRFÃO — sessão que morre sem apagar não acende o guarda para sempre"
rm -f "$RAIZ_T/gauntlet/bloqueios-$SID" "$RAIZ_T/gauntlet/desistencias.log"
: > "$RAIZ_T/gauntlet/ativo-$SID"
# Envelhece o sinal para além do prazo, sem esperar 12 horas.
touch -t 202001010000 "$RAIZ_T/gauntlet/ativo-$SID" 2>/dev/null
SAIDA=$(roda)
diz "sinal vencido não nega nada" "$SAIDA" ""
[ ! -f "$RAIZ_T/gauntlet/ativo-$SID" ] \
  && ok "e o sinal vencido é removido" \
  || bad "e o sinal vencido é removido"
[ -s "$RAIZ_T/gauntlet/expirados.log" ] \
  && ok "e a expiração fica registrada" \
  || bad "e a expiração fica registrada"

echo
echo "O DESLIGAMENTO — quem discorda tem por onde sair"
: > "$RAIZ_T/gauntlet/ativo-$SID"
rm -f "$RAIZ_T/gauntlet/bloqueios-$SID"
SAIDA=$(printf '%s' "$EVENTO" | GAUNTLET_GATE=0 bash "$HOOK" 2>/dev/null)
diz "com GAUNTLET_GATE=0 ele não nega nada" "$SAIDA" ""

echo
echo "O SINAL É POR SESSÃO — uma missão aqui não trava a sessão do vizinho"
rm -f "$RAIZ_T/gauntlet/bloqueios-$SID"
OUTRO='{"session_id":"outra-sessao","tool_name":"Agent"}'
SAIDA=$(printf '%s' "$OUTRO" | bash "$HOOK" 2>/dev/null)
diz "sessão sem missão passa, mesmo com a vizinha armada" "$SAIDA" ""

echo
echo "FAIL-OPEN — guarda que trava por causa da própria infra é pior que guarda nenhum"
SAIDA=$(printf '%s' '{"tool_name":"Agent"}' | bash "$HOOK" 2>/dev/null)
diz "evento sem identificação de sessão não nega" "$SAIDA" ""
SAIDA=$(printf '' | bash "$HOOK" 2>/dev/null)
diz "evento vazio não nega" "$SAIDA" ""
SAIDA=$(printf '%s' "$EVENTO" | CLAUDE_CONFIG_DIR="$RAIZ_T/nao-existe" bash "$HOOK" 2>/dev/null)
diz "sem a raiz de estado no disco, não nega" "$SAIDA" ""

rm -rf "$RAIZ_T"
echo
if [ "$FALHAS" -gt 0 ]; then
  echo "guarda do gauntlet: $FALHAS falha(s)"
  exit 1
fi
echo "guarda do gauntlet: tudo verde"
