#!/bin/bash
# test_espera_com_guarda.sh — suíte do gate de espera com guarda.
#
# Roda o hook DE VERDADE, alimentando o payload de PreToolUse pelo stdin, e olha
# a decisão que sai no stdout. Nada de recalcular a regra aqui.
#
#   bash plugins/sovai/hooks/test_espera_com_guarda.sh

HOOK="$(cd "$(dirname "$0")" && pwd)/pretooluse-espera-com-guarda.sh"

OK=0
FALHA=0

check() {
  local nome="$1" cond="$2" extra="${3:-}"
  if [ "$cond" = "1" ]; then
    OK=$((OK + 1)); echo "  ok   $nome"
  else
    FALHA=$((FALHA + 1)); echo "  FALHA $nome ${extra}"
  fi
}

# O payload é montado por python3 (stdlib) pra não depender de escapar shell na
# mão — o comando de teste tem aspas, `$` e barra.
paylo() {
  python3 -c 'import json,sys; print(json.dumps({"tool_name": sys.argv[1], "tool_input": {"command": sys.argv[2]}, "session_id": sys.argv[3]}))' "$1" "$2" "${3:-sess-teste}"
}

# O gate só vale DENTRO de uma missão: raiz de config falsa, com o sinal de
# missão ativa da sessão de teste. Nunca toca no ~/.claude real.
CFG="$(mktemp -d -t espera-cfg)"
trap 'rm -rf "$CFG"' EXIT
mkdir -p "$CFG/sovai"
: > "$CFG/sovai/ativo-sess-teste"

# Here-string e não pipe: o hook sai antes de ler o stdin em vários caminhos
# (kill-switch, tool que não é Bash), e aí o pipe quebra e o gerador do payload
# despeja BrokenPipeError no terminal.
roda() { # $1 = tool_name, $2 = command   (script sob teste, ou o sabotado em $3)
  CLAUDE_CONFIG_DIR="$CFG" sh "${3:-$HOOK}" <<< "$(paylo "$1" "$2")" 2>/dev/null
}

nega() {
  printf '%s' "$1" \
    | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: print(0); raise SystemExit
print(1 if d.get("hookSpecificOutput",{}).get("permissionDecision")=="deny" else 0)' 2>/dev/null
}

echo "[gate de espera com guarda do sovai]"

# 1 · O CRITÉRIO, lado vermelho: espera sem teto E sem checagem de vida
SEM_GUARDA='while ! grep -q OK /tmp/saida.txt; do sleep 5; done'
OUT=$(roda Bash "$SEM_GUARDA")
check "espera sem teto E sem checagem de vida é RECUSADA" "$(nega "$OUT")" "saiu: $OUT"
check "a recusa nomeia o TETO que falta" \
  "$(printf '%s' "$OUT" | grep -q 'TETO' && echo 1 || echo 0)" "saiu: $OUT"
check "a recusa nomeia a checagem de VIVO que falta" \
  "$(printf '%s' "$OUT" | grep -q 'VIVO' && echo 1 || echo 0)" "saiu: $OUT"
check "a recusa mostra o desligamento" \
  "$(printf '%s' "$OUT" | grep -q 'SOVAI_ESPERA=0' && echo 1 || echo 0)" "saiu: $OUT"

OUT=$(roda Bash 'until [ -s /tmp/resultado.json ]; do sleep 2; done; cat /tmp/resultado.json')
check "until esperando arquivo de saída é RECUSADO" "$(nega "$OUT")" "saiu: $OUT"

OUT=$(roda Bash 'npm test > /tmp/t.log 2>&1 & tail -f /tmp/t.log')
check "tail -f é RECUSADO (por construção não acaba)" "$(nega "$OUT")" "saiu: $OUT"

# 2 · O CRITÉRIO, lado verde: espera COM as duas guardas passa
COM_GUARDA='for _ in $(seq 1 60); do kill -0 "$PID" 2>/dev/null || break; [ -s /tmp/saida.txt ] && break; sleep 2; done'
OUT=$(roda Bash "$COM_GUARDA")
check "espera COM teto e COM checagem de vida PASSA (hook mudo)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 3 · meia guarda não é guarda — as duas condições, ou nenhuma serve
OUT=$(roda Bash 'i=0; while [ "$i" -lt 30 ]; do [ -s /tmp/s.txt ] && break; i=$((i+1)); sleep 1; done')
check "teto SEM checagem de vida ainda é recusado" "$(nega "$OUT")" "saiu: $OUT"
OUT=$(roda Bash 'while kill -0 "$PID" 2>/dev/null; do sleep 1; done')
check "checagem de vida SEM teto ainda é recusada" "$(nega "$OUT")" "saiu: $OUT"

# 4 · mudo fora do alvo — o gate não pode atrapalhar comando comum
OUT=$(roda Bash 'python3 plugins/sovai/lib/x.py && echo pronto')
check "comando sem espera nenhuma passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(roda Bash 'sleep 3')
check "sleep solto (sem laço) passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(roda Edit "$SEM_GUARDA")
check "outra tool que não Bash passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 4b · ESCOPO — fora de missão o gate não opina. O dono na frente do terminal
#      roda `tail -f app.log` o dia inteiro; recusar isso obrigaria o
#      desligamento global, que apagaria junto a proteção DENTRO da missão.
OUT=$(CLAUDE_CONFIG_DIR="$CFG" sh "$HOOK" <<< "$(paylo Bash "$SEM_GUARDA" sess-sem-missao)" 2>/dev/null)
check "SEM sinal de missão ativa, até a espera ruim passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(CLAUDE_CONFIG_DIR="$CFG" sh "$HOOK" <<< "$(paylo Bash 'tail -f /tmp/app.log' sess-sem-missao)" 2>/dev/null)
check "SEM sinal, tail -f do dono passa mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(CLAUDE_CONFIG_DIR="$CFG" sh "$HOOK" <<< "$(paylo Bash 'tail -f /tmp/app.log' sess-teste)" 2>/dev/null)
check "COM sinal, o MESMO tail -f é recusado" "$(nega "$OUT")" "saiu: $OUT"

# 5 · kill-switch
OUT=$(CLAUDE_CONFIG_DIR="$CFG" SOVAI_ESPERA=0 sh "$HOOK" <<< "$(paylo Bash "$SEM_GUARDA")" 2>/dev/null)
check "SOVAI_ESPERA=0 desliga o gate" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 6 · o gate está LIGADO no caminho do produto (hooks.json), não só no teste
HJ="$(cd "$(dirname "$0")" && pwd)/hooks.json"
check "hooks.json chama o gate em PreToolUse(Bash)" \
  "$(python3 -c 'import json,sys
d=json.load(open(sys.argv[1]))
for g in d["hooks"]["PreToolUse"]:
    if g.get("matcher")=="Bash" and any("pretooluse-espera-com-guarda.sh" in h.get("command","") for h in g["hooks"]):
        print(1); break
else: print(0)' "$HJ" 2>/dev/null)"

# 7 · anti-tautologia: sabotar a regra tem que fazer a suíte reprovar
SAB="$(mktemp -t espera-sabotada)"
trap 'rm -f "$SAB"; rm -rf "$CFG"' EXIT
sed 's/^\[ "\$EH_ESPERA" = "1" \] || exit 0$/[ "$EH_ESPERA" = "1" ] || exit 0; exit 0/' "$HOOK" > "$SAB"
OUT=$(roda Bash "$SEM_GUARDA" "$SAB")
check "gate sabotado (não julga a guarda) DEIXA de recusar" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "o sabotado ainda recusou — o teste #1 é tautológico"

echo
if [ "$FALHA" -eq 0 ]; then
  echo "OK ($OK checks)"
  exit 0
fi
echo "FALHOU ($FALHA de $((OK + FALHA)))"
exit 1
