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

# O temporário sai da receita única. `mktemp -d` pelado devolve o `/tmp` do Git Bash:
# esse caminho vira `cwd` da anotação, o `ps` do Windows reporta `C:/Users/.../Temp/...`,
# nada casa e NADA é encerrado — a suíte inteira do encerramento passava a medir vazio
# (.claude/reports/causas-windows-2026-08-15.md).
. "$SCRIPT_DIR/lib-tmpdir.sh" 2>/dev/null
TD=$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
TMP=$(mktemp -d "$TD/lixeiro-hooks-XXXXXX")
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

echo "── /clear não é fim de trabalho ──"
# O que acabou foi a conversa; o terminal, os servidores e a suíte em segundo plano
# seguem sendo do usuário. Como o SessionEnd não tem canal de saída, colher aqui
# matava em silêncio.
( cd "$PROJ" && exec "$PY3" -m http.server 0 >/dev/null 2>&1 ) &
NO_CLEAR=$!
sleep 1.2
rm -f "$TMP/lixeiro/sessao-s-clear.json"
printf '{"session_id":"s-clear","cwd":"%s","tool_input":{"command":"python3 -m http.server 0"}}' "$PROJ" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1
printf '{"session_id":"s-clear","reason":"clear"}' | bash "$SCRIPT_DIR/sessionend-colhe.sh" >/dev/null 2>&1
sleep 0.5
if kill -0 "$NO_CLEAR" 2>/dev/null; then
  ok "o /clear NÃO encerrou o que a sessão tinha aberto"
else
  bad "o /clear NÃO encerrou o que a sessão tinha aberto" "processo vivo" "foi encerrado"
fi
[ -f "$TMP/lixeiro/sessao-s-clear.json" ] && ok "…e o registro sobreviveu ao /clear" \
  || bad "o registro sobrevive ao /clear" "arquivo presente" "apagado — procedência perdida"
# E o fim de verdade, na mesma sessão, ainda encerra.
printf '{"session_id":"s-clear","reason":"prompt_input_exit"}' \
  | bash "$SCRIPT_DIR/sessionend-colhe.sh" >/dev/null 2>&1
sleep 0.5
if kill -0 "$NO_CLEAR" 2>/dev/null; then
  bad "o fim de verdade ainda encerra" "processo morto" "ainda vivo"
  kill -9 "$NO_CLEAR" 2>/dev/null
else
  ok "o fim de verdade ainda encerra o servidor ocioso"
fi

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

echo "── fim de turno: a suíte TRABALHANDO sobrevive, a parada morre ──"
# A prova que faltava no dia 11/08: duas suítes DE VERDADE, uma queimando CPU e
# outra dormindo, ambas anotadas pela mesma sessão. O que separa as duas é só o
# trabalho — antes deste conserto morriam as duas, e a que trabalhava morria seis
# segundos depois de nascer.
# O nome do arquivo é `pytest.py` porque é o COMANDO que classifica: assim o motor
# reconhece um efêmero de verdade, sem a suíte plantar classe na mão.
TRAB="$TMP/proj-turno"; mkdir -p "$TRAB"
cat > "$TRAB/pytest.py" <<'PYEOF'
import sys, time
if sys.argv[1:] and sys.argv[1] == "dorme":
    time.sleep(600)
else:
    fim = time.time() + 600
    x = 0
    while time.time() < fim:
        x += 1
PYEOF
( cd "$TRAB" && exec "$PY3" "$TRAB/pytest.py" trabalha >/dev/null 2>&1 ) &
OCUPADA=$!
( cd "$TRAB" && exec "$PY3" "$TRAB/pytest.py" dorme >/dev/null 2>&1 ) &
PARADA=$!
sleep 1.5
rm -f "$TMP/lixeiro/sessao-s-turno.json"
# Duas anotações, uma por processo — como acontece de verdade, um comando cada.
printf '{"session_id":"s-turno","cwd":"%s","tool_input":{"command":"python3 pytest.py trabalha"}}' "$TRAB" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1
printf '{"session_id":"s-turno","cwd":"%s","tool_input":{"command":"python3 pytest.py dorme"}}' "$TRAB" \
  | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1

# Dois turnos de verdade: o primeiro tira a foto de CPU, o segundo decide. A
# janela de ocioso encolhe para 1 segundo só aqui — uma suíte não pode levar dois
# minutos para provar a colheita.
export LIXEIRO_OCIOSO_MIN=1
printf '{"session_id":"s-turno"}' | bash "$SCRIPT_DIR/stop-colhe-turno.sh" >/dev/null 2>&1
if kill -0 "$OCUPADA" 2>/dev/null && kill -0 "$PARADA" 2>/dev/null; then
  ok "no primeiro turno nada morre — ainda não há foto contra o que comparar"
else
  bad "no primeiro turno nada morre" "as duas vivas" "alguma foi encerrada sem foto"
fi
sleep 2.5
printf '{"session_id":"s-turno"}' | bash "$SCRIPT_DIR/stop-colhe-turno.sh" >/dev/null 2>&1
unset LIXEIRO_OCIOSO_MIN
sleep 0.5
if kill -0 "$OCUPADA" 2>/dev/null; then
  ok "a suíte que estava TRABALHANDO sobreviveu ao fim do turno"
else
  bad "a suíte que estava TRABALHANDO sobreviveu" "processo vivo" "foi encerrada — o defeito voltou"
fi
if kill -0 "$PARADA" 2>/dev/null; then
  bad "a suíte PARADA foi encerrada" "processo morto" "ainda viva (pid $PARADA)"
else
  ok "…e a suíte PARADA foi encerrada, como tem que ser"
fi
kill -9 "$OCUPADA" "$PARADA" 2>/dev/null

echo "── agente de bancada: o que ele abre entra no registro da sessão dona ──"
# O agente que um workflow solta tem sessão PRÓPRIA, e o processo dele nasce
# dentro do processo da sessão que o soltou. Aqui a suíte encena isso: o registro
# da "dona" tem como dono um ancestral ESTRITO do harness que o hook enxerga
# (a suíte confirmou acima que ele grava o pid de quem a lançou).
mkdir -p "$TMP/lixeiro"
rm -f "$TMP/lixeiro/sessao-"*.json
AVO=$(ps -o ppid= -p "$PPID" 2>/dev/null | tr -d ' ')
if [ -z "$AVO" ] || [ "$AVO" -le 1 ] 2>/dev/null; then
  echo "  (pulado: sem avô na árvore desta suíte — nada a encenar)"
else
  printf '{"session_id":"dona","dono_pid":%s,"anotacoes":[]}' "$AVO" > "$TMP/lixeiro/sessao-dona.json"
  ( cd "$PROJ" && exec "$PY3" -m http.server 0 >/dev/null 2>&1 ) &
  BANCADA=$!
  sleep 1.2
  printf '{"session_id":"agente-de-bancada","cwd":"%s","tool_input":{"command":"python3 -m http.server 0"}}' "$PROJ" \
    | bash "$SCRIPT_DIR/posttooluse-anota.sh" >/dev/null 2>&1
  AG=$(jq -r '.anotacoes[0].agente // empty' "$TMP/lixeiro/sessao-dona.json" 2>/dev/null)
  [ "$AG" = "agente-de-bancada" ] && ok "a anotação do agente aparece na sessão dona, com a origem" \
    || bad "anotação do agente na sessão dona" "agente-de-bancada" "${AG:-nada no registro da dona}"
  [ ! -f "$TMP/lixeiro/sessao-agente-de-bancada.json" ] \
    && ok "nada ficou preso num registro que só o agente enxerga" \
    || bad "registro só do agente" "não existe" "$(jq -c '.anotacoes' "$TMP/lixeiro/sessao-agente-de-bancada.json" 2>/dev/null)"
  # A prova que importa: quem colhe é a DONA, sem nunca ter visto o comando.
  printf '{"session_id":"dona"}' | bash "$SCRIPT_DIR/sessionend-colhe.sh" >/dev/null 2>&1
  sleep 0.5
  if kill -0 "$BANCADA" 2>/dev/null; then
    bad "a sessão dona colhe o servidor que o agente subiu" "processo morto" "ainda vivo (pid $BANCADA)"
    kill -9 "$BANCADA" 2>/dev/null
  else
    ok "a sessão dona colhe o servidor que o agente subiu"
  fi
fi

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

echo "── a causa do que sobrou ──"
# O hook não só encerra: ele diz POR QUE aquilo sobrou. Sem isso a colheita limpa e o
# defeito fica, então no turno seguinte tudo volta — foi assim que uma máquina chegou a
# 2125 processos órfãos em 2026-08-08. Aqui a colheita é SIMULADA (`LIXEIRO_MORTOS_TESTE`),
# porque plantar processo de verdade numa bancada é pior que não testar.
CAUSA_DIR=$(mktemp -d "$TD/lixeiro-causa-XXXXXX")
printf 'import subprocess\nsubprocess.run(["git","status"])\n' > "$CAUSA_DIR/vaza.py"
MORTOS_JSON="[{\"pid\": 4242, \"rss_mb\": 12, \"cmd\": \"python3 $CAUSA_DIR/vaza.py\"}]"
SAIDA=$(printf '{"session_id":"s-causa"}' \
  | LIXEIRO_MORTOS_TESTE="$MORTOS_JSON" CLAUDE_PROJECT_DIR="$CAUSA_DIR" \
    bash "$SCRIPT_DIR/stop-colhe-turno.sh" 2>&1)
case "$SAIDA" in
  *"motivo de terem sobrado"*) ok "a colheita vem com o motivo do que sobrou" ;;
  *) bad "causa no anúncio" "o motivo junto" "$SAIDA" ;;
esac
case "$SAIDA" in
  *"vaza.py:2"*) ok "a causa aponta arquivo e linha" ;;
  *) bad "arquivo:linha da causa" "vaza.py:2" "$SAIDA" ;;
esac
case "$SAIDA" in
  *"/faxina"*) ok "a causa diz o que fazer a seguir" ;;
  *) bad "próximo passo" "aponta /faxina" "$SAIDA" ;;
esac
# Desligar a investigação não pode desligar a colheita: são notícias diferentes, e quem
# só quer menos texto no terminal continua precisando saber que processos morreram.
SAIDA=$(printf '{"session_id":"s-causa2"}' \
  | LIXEIRO_CAUSA=0 LIXEIRO_MORTOS_TESTE="$MORTOS_JSON" CLAUDE_PROJECT_DIR="$CAUSA_DIR" \
    bash "$SCRIPT_DIR/stop-colhe-turno.sh" 2>&1)
case "$SAIDA" in
  *"motivo de terem sobrado"*) bad "LIXEIRO_CAUSA=0" "sem a causa" "$SAIDA" ;;
  *"Caminhão do lixo"*) ok "LIXEIRO_CAUSA=0 cala a causa e mantém a colheita" ;;
  *) bad "LIXEIRO_CAUSA=0" "colheita ainda anunciada" "$SAIDA" ;;
esac
rm -rf "$CAUSA_DIR"

echo ""
printf 'lixeiro-hooks: %d ok, %d falhas\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
