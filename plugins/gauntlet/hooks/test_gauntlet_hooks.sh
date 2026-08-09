#!/bin/bash
# Suíte da trava dupla do gauntlet — o que ela nega, o que deixa passar, onde desiste.
#
# A trava nasceu de uma falha medida: o orquestrador leu sete relatórios de construtor
# e aceitou todos sem lançar juiz. A primeira versão negava TODO sub-agente e mandava
# o trabalho para a tool Workflow; o dono derrubou a caixa fechada (2026-08-09) e a
# trava virou cirúrgica: só nega enquanto houver entrega sem veredito, e só nega quem
# NÃO é o juiz da pendência.
#
#   bash plugins/gauntlet/hooks/test_gauntlet_hooks.sh
#
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
HOOK="$AQUI/pretooluse-gauntlet.sh"
FALHAS=0

ok()   { printf '  ok   %s\n' "$1"; }
bad()  { printf '  FAIL %s\n' "$1"; FALHAS=$((FALHAS+1)); }
diz()  { [ "$2" = "$3" ] && ok "$1" || bad "$1 (esperava '$3', veio '$2')"; }

RAIZ_T=$(mktemp -d)
export CLAUDE_CONFIG_DIR="$RAIZ_T"
mkdir -p "$RAIZ_T/andamento"
SID="sessao-de-teste"

# A missão de laboratório: uma peça `hero` entregue e SEM veredito — a foto exata
# da falha central — e uma `marcas` já julgada, para provar que a trava discrimina.
MISSAO="$RAIZ_T/missao"
mkdir -p "$MISSAO/pecas/hero/r1" "$MISSAO/pecas/marcas/r1"
printf '{"pecas":[{"id":"hero"},{"id":"marcas"}]}' > "$MISSAO/decomposicao.json"
printf '{"peca":"hero","artefatos":[]}' > "$MISSAO/pecas/hero/r1/entrega.json"
printf '{"peca":"marcas","artefatos":[]}' > "$MISSAO/pecas/marcas/r1/entrega.json"
printf '{"peca":"marcas","status":"aprovado"}' > "$MISSAO/pecas/marcas/r1/veredito.json"

arma() { printf 'gauntlet\n%s\n' "$MISSAO" > "$RAIZ_T/andamento/ativo-$SID"; }
evento() { printf '{"session_id":"%s","tool_name":"Agent","tool_input":{"prompt":%s}}' "$1" "$2"; }
roda() { evento "$SID" "$1" | bash "$HOOK" 2>/dev/null; }

echo "SEM MISSÃO — a trava é muda"
SAIDA=$(roda '"qualquer agente"')
diz "sem sinal, não diz nada" "$SAIDA" ""

echo
echo "ENTREGA SEM JUIZ — nada nasce antes do juiz dela"
arma
SAIDA=$(roda '"[gauntlet:construtor:precos] construa a peça"')
case "$SAIDA" in
  *deny*) ok "construtor novo é negado enquanto hero espera juiz" ;;
  *)      bad "construtor novo é negado (veio: ${SAIDA:0:60})" ;;
esac
case "$SAIDA" in
  *hero*) ok "e a negação NOMEIA a peça pendente" ;;
  *)      bad "e a negação nomeia a peça pendente" ;;
esac
case "$SAIDA" in
  *"[gauntlet:juiz:"*) ok "e ensina o marcador que abre a passagem" ;;
  *)                   bad "e ensina o marcador que abre a passagem" ;;
esac
case "$SAIDA" in
  *fecho_check*) ok "e diz onde conferir a pendência — no disco, não na memória" ;;
  *)             bad "e diz onde conferir a pendência" ;;
esac

rm -f "$RAIZ_T/andamento/bloqueios-$SID"
SAIDA=$(roda '"[gauntlet:juiz:hero] julgue a peça hero contra o alvo"')
diz "o juiz da peça pendente passa" "$SAIDA" ""

rm -f "$RAIZ_T/andamento/bloqueios-$SID"
SAIDA=$(roda '"[gauntlet:juiz:marcas] julgue marcas"')
case "$SAIDA" in
  *deny*) ok "juiz de peça JÁ julgada não fura a fila da pendente" ;;
  *)      bad "juiz de peça já julgada não fura a fila" ;;
esac

echo
echo "SEM PENDÊNCIA — a equipe é livre"
printf '{"peca":"hero","status":"aprovado"}' > "$MISSAO/pecas/hero/r1/veredito.json"
rm -f "$RAIZ_T/andamento/bloqueios-$SID"
SAIDA=$(roda '"[gauntlet:construtor:precos] construa"')
diz "com todo veredito no disco, qualquer agente nasce" "$SAIDA" ""
rm -f "$MISSAO/pecas/hero/r1/veredito.json"

echo
echo "A SAÍDA DE EMERGÊNCIA — trava que trava com o dono fora custa mais que o defeito"
rm -f "$RAIZ_T/andamento/bloqueios-$SID"
for _ in 1 2 3; do roda '"sem marcador"' >/dev/null; done
SAIDA=$(roda '"sem marcador"')
case "$SAIDA" in
  *deny*) bad "depois do teto de negações, ela desiste e libera (ainda nega)" ;;
  *)      ok "depois do teto de negações, ela desiste e libera" ;;
esac
case "$SAIDA" in
  *systemMessage*DESISTIU*) ok "e a desistência AVISA na conversa, não só no log" ;;
  *)                        bad "e a desistência avisa na conversa (veio: ${SAIDA:0:60})" ;;
esac
case "$SAIDA" in
  *hero*) ok "e o aviso nomeia a entrega que segue sem veredito" ;;
  *)      bad "e o aviso nomeia a entrega que segue sem veredito" ;;
esac
[ -s "$RAIZ_T/andamento/desistencias.log" ] \
  && ok "e a desistência fica registrada" \
  || bad "e a desistência fica registrada"

echo
echo "O SINAL ÓRFÃO — sessão que morre sem apagar não acende a trava para sempre"
rm -f "$RAIZ_T/andamento/bloqueios-$SID" "$RAIZ_T/andamento/desistencias.log"
arma
touch -t 202001010000 "$RAIZ_T/andamento/ativo-$SID" 2>/dev/null
SAIDA=$(roda '"sem marcador"')
diz "sinal vencido não nega nada" "$SAIDA" ""
[ ! -f "$RAIZ_T/andamento/ativo-$SID" ] \
  && ok "e o sinal vencido é removido" \
  || bad "e o sinal vencido é removido"
[ -s "$RAIZ_T/andamento/expirados.log" ] \
  && ok "e a expiração fica registrada" \
  || bad "e a expiração fica registrada"

echo
echo "O DESLIGAMENTO — quem discorda tem por onde sair"
arma
rm -f "$RAIZ_T/andamento/bloqueios-$SID"
SAIDA=$(evento "$SID" '"sem marcador"' | GAUNTLET_GATE=0 bash "$HOOK" 2>/dev/null)
diz "com GAUNTLET_GATE=0 ela não nega nada" "$SAIDA" ""

echo
echo "O SINAL É POR SESSÃO — uma missão aqui não trava a sessão do vizinho"
rm -f "$RAIZ_T/andamento/bloqueios-$SID"
SAIDA=$(evento "outra-sessao" '"sem marcador"' | bash "$HOOK" 2>/dev/null)
diz "sessão sem missão passa, mesmo com a vizinha armada" "$SAIDA" ""

echo
echo "A CASA DO SINAL É COMPARTILHADA — quem guarda é o NOME escrito nele"
printf 'qa-loop\n%s\n' "$MISSAO" > "$RAIZ_T/andamento/ativo-$SID"
rm -f "$RAIZ_T/andamento/bloqueios-$SID"
SAIDA=$(roda '"sem marcador"')
diz "missão de outro motor na mesma casa não é negada por esta trava" "$SAIDA" ""

echo
echo "FAIL-OPEN — trava que trava por causa da própria infra é pior que trava nenhuma"
arma
rm -f "$RAIZ_T/andamento/bloqueios-$SID"
SAIDA=$(printf '%s' '{"tool_name":"Agent"}' | bash "$HOOK" 2>/dev/null)
diz "evento sem identificação de sessão não nega" "$SAIDA" ""
SAIDA=$(printf '' | bash "$HOOK" 2>/dev/null)
diz "evento vazio não nega" "$SAIDA" ""
SAIDA=$(evento "$SID" '"x"' | CLAUDE_CONFIG_DIR="$RAIZ_T/nao-existe" bash "$HOOK" 2>/dev/null)
diz "sem a raiz de estado no disco, não nega" "$SAIDA" ""
printf 'gauntlet\n' > "$RAIZ_T/andamento/ativo-$SID"
SAIDA=$(roda '"sem marcador"')
diz "sinal sem o diretório da missão na 2ª linha não nega" "$SAIDA" ""
printf 'gauntlet\n%s\n' "$RAIZ_T/missao-que-nao-existe" > "$RAIZ_T/andamento/ativo-$SID"
SAIDA=$(roda '"sem marcador"')
diz "sinal apontando missão que não está no disco não nega" "$SAIDA" ""

rm -rf "$RAIZ_T"
echo
if [ "$FALHAS" -gt 0 ]; then
  echo "trava dupla do gauntlet: $FALHAS falha(s)"
  exit 1
fi
echo "trava dupla do gauntlet: tudo verde"
