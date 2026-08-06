#!/bin/bash
# test_context_guard_writer.sh — suíte do middleware de statusLine.
#
# Ele roda a CADA render da barra de status, então errar aqui é errar o tempo
# todo. A suíte trava três coisas:
#   1. o context% continua saindo por sessão (o bug do estado global já custou
#      bloqueio em massa: uma sessão cheia barrava todas as outras);
#   2. o uso da janela de 5h é gravado GLOBAL, porque o limite é da conta;
#   3. payload sem os campos, ilegível ou sem ferramenta não cria lixo nem quebra.
#
# Roda isolada: estado em mktemp, e o encaminhamento é desligado.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
W="$SCRIPT_DIR/context-guard-writer.sh"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✗ %s\n     esperado: %s\n     obtido:   %s\n' "$1" "$2" "$3"; }

command -v jq >/dev/null 2>&1 || { echo "jq ausente — o writer é fail-open sem ele e a suíte não mede nada"; exit 1; }

# O encaminhamento para a barra original não é objeto deste teste; sem desligar,
# o comando do ambiente real vaza para dentro da suíte e polui a saída.
unset CLAUDE_STATUSLINE_FORWARD

# O writer grava no temporário DO SISTEMA — a suíte pergunta pelo mesmo caminho
# que ele, em vez de assumir /tmp (que nem sempre é o temporário da máquina).
# shellcheck source=/dev/null
. "$SCRIPT_DIR/lib-tmpdir.sh"
TMPD=$(td_tmpdir)

novo_tmp() { CLAUDE_CONFIG_DIR=$(mktemp -d); export CLAUDE_CONFIG_DIR; }
roda() { printf '%s' "$1" | bash "$W" 2>/dev/null; }

echo "── o uso da janela de 5h ──"
novo_tmp
roda '{"session_id":"s1","context_window":{"used_percentage":42},"five_hour":{"used_percentage":93,"resets_at":"2026-08-06T03:50:00Z"}}'
F="$CLAUDE_CONFIG_DIR/context-guard/five-hour.json"
PCT=$(jq -r '.pct' "$F" 2>/dev/null)
[ "$PCT" = "93" ] && ok "grava o percentual da janela de 5h" || bad "percentual da janela" "93" "${PCT:-nada}"
RST=$(jq -r '.resets_at' "$F" 2>/dev/null)
[ "$RST" = "2026-08-06T03:50:00Z" ] && ok "grava quando a janela reseta" || bad "resets_at" "2026-08-06T03:50:00Z" "${RST:-nada}"
LIDO=$(jq -r '.lido_em' "$F" 2>/dev/null)
case "$LIDO" in
  20*T*Z) ok "carimba a hora da leitura (dado velho é detectável)" ;;
  *) bad "carimba a hora da leitura" "data ISO" "${LIDO:-nada}" ;;
esac

echo "── o campo alternativo (utilization) também é aceito ──"
novo_tmp
roda '{"session_id":"s1","five_hour":{"utilization":77}}'
PCT=$(jq -r '.pct' "$CLAUDE_CONFIG_DIR/context-guard/five-hour.json" 2>/dev/null)
[ "$PCT" = "77" ] && ok "aceita utilization quando não há used_percentage" || bad "utilization" "77" "${PCT:-nada}"

echo "── o estado da janela é GLOBAL, não por sessão ──"
novo_tmp
roda '{"session_id":"sessao-A","five_hour":{"used_percentage":10}}'
roda '{"session_id":"sessao-B","five_hour":{"used_percentage":88}}'
N=$(ls "$CLAUDE_CONFIG_DIR/context-guard/" | grep -c 'five-hour')
PCT=$(jq -r '.pct' "$CLAUDE_CONFIG_DIR/context-guard/five-hour.json" 2>/dev/null)
[ "$N" = "1" ] && ok "duas sessões escrevem no MESMO arquivo (o limite é da conta)" \
  || bad "arquivo único" "1 arquivo" "$N"
[ "$PCT" = "88" ] && ok "o último a renderizar manda — é o valor mais recente" || bad "valor corrente" "88" "$PCT"

echo "── o context% continua POR SESSÃO ──"
novo_tmp
roda '{"session_id":"sess-x","context_window":{"used_percentage":31}}'
roda '{"session_id":"sess-y","context_window":{"used_percentage":72}}'
X=$(cat "$TMPD/claude-context-pct-sess-x" 2>/dev/null)
Y=$(cat "$TMPD/claude-context-pct-sess-y" 2>/dev/null)
{ [ "$X" = "31" ] && [ "$Y" = "72" ]; } && ok "cada sessão lê o próprio contexto (31 e 72)" \
  || bad "contexto por sessão" "31 e 72" "$X e $Y"
rm -f "$TMPD/claude-context-pct-sess-x" "$TMPD/claude-context-pct-sess-y"

echo "── nada cria lixo: sem os campos, ilegível, sem ferramenta ──"
novo_tmp
roda '{"session_id":"s2","context_window":{"used_percentage":10}}'
[ ! -e "$CLAUDE_CONFIG_DIR/context-guard/five-hour.json" ] \
  && ok "payload sem a janela de 5h não cria arquivo" \
  || bad "sem five_hour" "nenhum arquivo" "arquivo criado"

novo_tmp
roda '{"session_id":"s3","five_hour":null}'
[ ! -e "$CLAUDE_CONFIG_DIR/context-guard/five-hour.json" ] \
  && ok "janela nula não cria arquivo" || bad "five_hour null" "nenhum arquivo" "arquivo criado"

novo_tmp
roda 'isto não é json'
RC=$?
[ "$RC" -eq 0 ] && ok "entrada ilegível não derruba a barra de status" || bad "entrada ilegível" "exit 0" "exit $RC"
[ ! -e "$CLAUDE_CONFIG_DIR/context-guard/five-hour.json" ] \
  && ok "entrada ilegível não cria arquivo" || bad "ilegível" "nenhum arquivo" "arquivo criado"

novo_tmp
BASH_ABS=$(command -v bash)
printf '{"session_id":"s4","five_hour":{"used_percentage":50}}' | PATH=/nao-existe "$BASH_ABS" "$W" >/dev/null 2>&1
[ ! -e "$CLAUDE_CONFIG_DIR/context-guard/five-hour.json" ] \
  && ok "sem ferramenta no PATH, não grava nada (fail-open)" || bad "sem jq" "nenhum arquivo" "arquivo criado"

echo "── o encaminhamento para a barra original continua acontecendo ──"
novo_tmp
SAIDA=$(printf '{"session_id":"s5","five_hour":{"used_percentage":5}}' \
  | CLAUDE_STATUSLINE_FORWARD='cat' bash "$W" 2>/dev/null)
case "$SAIDA" in
  *'"session_id":"s5"'*) ok "o payload é repassado intacto para a barra original" ;;
  *) bad "repasse do payload" "o JSON de entrada" "${SAIDA:-vazio}" ;;
esac

echo ""
printf 'context-guard-writer: %d ok, %d falhas\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
