#!/bin/bash
# test_lixeiro_hooks.sh — suíte dos quatro hooks do lixeiro, ponta a ponta.
#
# Diferente da suíte do motor (que testa a decisão com processos de mentira),
# esta abre um SERVIDOR DE VERDADE, deixa o hook anotá-lo, roda a colheita e
# exige que ele tenha morrido. É a única prova de que a cadeia inteira — hook,
# registro, casamento, sinal — fecha.
#
# Roda isolada: estado em mktemp, e o único processo encerrado é o que ela abre.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUG="$(dirname "$SCRIPT_DIR")"
PASS=0; FAIL=0

ok()  { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✗ %s\n     esperado: %s\n     obtido:   %s\n' "$1" "$2" "$3"; }

command -v jq >/dev/null 2>&1 || { echo "jq ausente — os hooks são fail-open sem ele e a suíte não mede nada"; exit 1; }
PY3=$(command -v python3) || { echo "python3 ausente"; exit 1; }
# Presença não basta: o stub da Microsoft Store existe como arquivo e não executa.
# Sem esta linha a suíte quebraria lá na frente, com erro que não nomeia a causa.
"$PY3" --version >/dev/null 2>&1 || { echo "python3 existe mas não executa (stub?)"; exit 1; }

TMP=$(mktemp -d)
export CLAUDE_CONFIG_DIR="$TMP"
export CLAUDE_PLUGIN_ROOT="$PLUG"
PROJ="$TMP/projeto-de-teste"
mkdir -p "$PROJ"
trap 'rm -rf "$TMP"' EXIT

echo "── anotação: só o abridor entra no registro ──"
printf '{"session_id":"s1","cwd":"%s","tool_input":{"command":"npm run dev"}}' "$PROJ" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1
N=$(jq '.anotacoes | length' "$TMP/lixeiro/sessao-s1.json" 2>/dev/null)
[ "$N" = "1" ] && ok "servidor anotado" || bad "servidor anotado" "1 anotação" "${N:-nenhum registro}"

printf '{"session_id":"s1","cwd":"%s","tool_input":{"command":"git status"}}' "$PROJ" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1
N=$(jq '.anotacoes | length' "$TMP/lixeiro/sessao-s1.json" 2>/dev/null)
[ "$N" = "1" ] && ok "comando comum NÃO entra no registro" || bad "comando comum NÃO entra" "1 anotação" "$N"

echo "── o hook de anotação não fala com o modelo ──"
SAIDA=$(printf '{"session_id":"s1","cwd":"%s","tool_input":{"command":"npm run dev"}}' "$PROJ" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" 2>/dev/null)
[ -z "$SAIDA" ] && ok "anotação é muda (nada no stdout)" || bad "anotação é muda" "stdout vazio" "$SAIDA"

echo "── ponta a ponta: servidor de verdade, anotado e colhido ──"
# Um servidor HTTP real, dentro do projeto de teste. `http.server` está na lista
# de serviços do motor, e o cwd casa a anotação.
( cd "$PROJ" && exec "$PY3" -m http.server 0 >/dev/null 2>&1 ) &
ALVO=$!
sleep 1.2
if kill -0 "$ALVO" 2>/dev/null; then
  ok "servidor de teste subiu (pid $ALVO)"
else
  bad "servidor de teste subiu" "processo vivo" "morreu antes"
fi

rm -f "$TMP/lixeiro/sessao-s2.json"
printf '{"session_id":"s2","cwd":"%s","tool_input":{"command":"python3 -m http.server 0"}}' "$PROJ" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1
CL=$(jq -r '.anotacoes[0].classe' "$TMP/lixeiro/sessao-s2.json" 2>/dev/null)
[ "$CL" = "servico" ] && ok "o servidor foi classificado como serviço" || bad "classe do servidor" "servico" "$CL"

# Fim de sessão colhe tudo que a sessão anotou, ocioso ou não.
printf '{"session_id":"s2"}' | bash "$SCRIPT_DIR/sessionend-colhe.sh" >/dev/null 2>&1
sleep 0.5
if kill -0 "$ALVO" 2>/dev/null; then
  bad "o fim de sessão encerrou o servidor anotado" "processo morto" "ainda vivo (pid $ALVO)"
  kill -9 "$ALVO" 2>/dev/null
else
  ok "o fim de sessão encerrou o servidor anotado"
fi
[ -f "$TMP/lixeiro/colhido.jsonl" ] && ok "o que morreu ficou registrado para auditoria" \
  || bad "registro de auditoria" "colhido.jsonl existe" "ausente"

echo "── o servidor de OUTRO projeto sobrevive ──"
VIZINHO="$TMP/projeto-vizinho"; mkdir -p "$VIZINHO"
( cd "$VIZINHO" && exec "$PY3" -m http.server 0 >/dev/null 2>&1 ) &
ALHEIO=$!
sleep 1.2
rm -f "$TMP/lixeiro/sessao-s3.json"
printf '{"session_id":"s3","cwd":"%s","tool_input":{"command":"python3 -m http.server 0"}}' "$PROJ" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1
printf '{"session_id":"s3"}' | bash "$SCRIPT_DIR/sessionend-colhe.sh" >/dev/null 2>&1
sleep 0.5
if kill -0 "$ALHEIO" 2>/dev/null; then
  ok "servidor de outro projeto NÃO foi tocado"
else
  bad "servidor de outro projeto NÃO foi tocado" "processo vivo" "foi encerrado — FALSO POSITIVO"
fi
kill -9 "$ALHEIO" 2>/dev/null

echo "── órfão: sessão cujo dono não existe mais ──"
mkdir -p "$TMP/lixeiro"
cat > "$TMP/lixeiro/sessao-morta.json" <<EOF
{"session_id":"morta","dono_pid":4194304,"anotacoes":[
 {"cmd":"npm run dev","cwd":"$PROJ","classe":"servico","em":$(date +%s),"cpu_ultimo_turno":null}]}
EOF
SAIDA=$(printf '{"session_id":"s4"}' | bash "$SCRIPT_DIR/sessionstart-orfaos.sh" 2>/dev/null)
if [ ! -f "$TMP/lixeiro/sessao-morta.json" ]; then
  ok "o registro da sessão morta foi recolhido"
else
  bad "o registro da sessão morta foi recolhido" "arquivo removido" "ainda existe"
fi

echo "── kill-switch e fail-open ──"
SAIDA=$(LIXEIRO=0 printf '{"session_id":"s1"}' | LIXEIRO=0 bash "$SCRIPT_DIR/stop-colhe-turno.sh" 2>&1)
[ -z "$SAIDA" ] && ok "LIXEIRO=0 cala o hook do fim de turno" || bad "LIXEIRO=0 cala" "vazio" "$SAIDA"
printf 'nao é json' | bash "$SCRIPT_DIR/stop-colhe-turno.sh" >/dev/null 2>&1
[ $? -eq 0 ] && ok "entrada ilegível não derruba o hook" || bad "entrada ilegível" "exit 0" "exit $?"
BASH_ABS=$(command -v bash)
SAIDA=$(printf '{"session_id":"s9"}' | PATH=/nao-existe "$BASH_ABS" "$SCRIPT_DIR/stop-colhe-turno.sh" 2>&1)
# Sem jq NEM python3 não há como ler o `session_id` — e desde o requisito W-2 a regra
# é FALAR: hook que sai calado é indistinguível de hook que rodou e liberou (issue #5).
[ -n "$SAIDA" ] && ok "sem ferramenta no PATH, o hook avisa em vez de calar" || bad "sem ferramenta" "aviso" "vazio"

echo "── anti-loop do Stop ──"
SAIDA=$(printf '{"session_id":"s1","stop_hook_active":true}' | bash "$SCRIPT_DIR/stop-colhe-turno.sh" 2>&1)
[ -z "$SAIDA" ] && ok "Stop já ativo não reentra" || bad "anti-loop" "vazio" "$SAIDA"

echo ""
printf 'lixeiro-hooks: %d ok, %d falhas\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
