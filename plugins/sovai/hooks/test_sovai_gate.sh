#!/bin/bash
# test_sovai_gate.sh — suíte do gate que mantém o /sovai no motor Workflow.
#
# Roda o hook DE VERDADE, com o payload que o harness manda, e olha a decisão
# que sai no stdout. Nada de recalcular a regra aqui: recalcular à mão foi
# exatamente o que mascarou o bug de path na 1ª rodada do plan-gate.
#
#   bash plugins/sovai/hooks/test_sovai_gate.sh

HOOK="$(cd "$(dirname "$0")" && pwd)/pretooluse-sovai-motor.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

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

payload() { # $1 = tool, $2 = session
  printf '{"tool_name":"%s","session_id":"%s","tool_input":{"prompt":"faz aí"}}' "$1" "$2"
}

roda() { # stdin = payload; ecoa stdout do hook
  CLAUDE_CONFIG_DIR="$TMP" bash "$HOOK" 2>/dev/null
}

# Lê a decisão pelo jq, não por grep de string: o `jq -n` do hook emite JSON
# formatado, então procurar `"permissionDecision":"deny"` colado nunca casaria.
nega() {
  printf '%s' "$1" \
    | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1 \
    && echo 1 || echo 0
}

SID="sessao-de-teste-1"
ESTADO="$TMP/sovai"
mkdir -p "$ESTADO"

echo "[gate do motor do sovai]"

# 1 · fora do sovai o gate é mudo — sub-agente aqui é assunto de outro guard
OUT=$(payload Agent "$SID" | roda)
check "sem o sinal, libera e não escreve nada" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 2 · com o sinal, nega
: > "$ESTADO/ativo-$SID"
OUT=$(payload Agent "$SID" | roda)
check "com o sinal, NEGA o disparo de sub-agente" "$(nega "$OUT")" "saiu: $OUT"
check "a razão manda rodar o Workflow" \
  "$(printf '%s' "$OUT" | grep -q 'Workflow' && echo 1 || echo 0)"
check "a razão diz que Agent Teams também não serve" \
  "$(printf '%s' "$OUT" | grep -q 'Agent Teams' && echo 1 || echo 0)"
check "a razão mostra o desligamento" \
  "$(printf '%s' "$OUT" | grep -q 'SOVAI_GATE=0' && echo 1 || echo 0)"
check "quem nega sai com exit 0 (o veredito vem do JSON)" \
  "$(payload Agent "$SID" | roda >/dev/null; [ $? -eq 0 ] && echo 1 || echo 0)"

# 3 · o sinal é POR SESSÃO — o defeito que já mordeu context-guard e scope-cop
OUT=$(payload Agent "outra-sessao" | roda)
check "sinal de OUTRA sessão não vaza pra esta" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 4 · fora do escopo: o hook não opina sobre outras tools
OUT=$(payload Write "$SID" | roda)
check "tool que não é Agent passa em silêncio" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 5 · kill-switch
OUT=$(payload Agent "$SID" | CLAUDE_CONFIG_DIR="$TMP" SOVAI_GATE=0 bash "$HOOK" 2>/dev/null)
check "SOVAI_GATE=0 cala o gate" "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 6 · fail-open nas bordas de infra
OUT=$(printf '{"tool_name":"Agent"}' | roda)
check "sem session_id, não bloqueia (fail-open)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(printf 'isso não é json' | roda)
check "payload quebrado não bloqueia (fail-open)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(payload Agent "$SID" | CLAUDE_CONFIG_DIR="$TMP" PATH="/nonexistent" bash "$HOOK" 2>/dev/null)
check "sem jq no PATH, não bloqueia (fail-open)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 6b · o cap: o gate degrada em vez de travar a missão
CAPSID="sessao-do-cap"
: > "$ESTADO/ativo-$CAPSID"
N_NEGOU=0
for _ in 1 2 3 4 5; do
  OUT=$(payload Agent "$CAPSID" | roda)
  [ "$(nega "$OUT")" = "1" ] && N_NEGOU=$((N_NEGOU + 1))
done
check "nega 3 vezes e DESISTE na 4ª (gate degrada, não trava)" \
  "$([ "$N_NEGOU" -eq 3 ] && echo 1 || echo 0)" "negou $N_NEGOU de 5"
check "a desistência deixa rastro em log (não é silenciosa)" \
  "$([ -s "$ESTADO/desistencias.log" ] && echo 1 || echo 0)"
check "o contador do cap é por sessão" \
  "$([ -f "$ESTADO/bloqueios-$CAPSID" ] && echo 1 || echo 0)"

# 6c · lixo no contador não vira erro de shell
printf 'não é número' > "$ESTADO/bloqueios-$CAPSID"
OUT=$(payload Agent "$CAPSID" | roda)
check "contador corrompido é sanitizado e o gate volta a negar" "$(nega "$OUT")" "saiu: $OUT"

# 7 · anti-tautologia: sabotar o gate tem que fazer a suíte reprovar
SAB="$TMP/sabotado.sh"
sed 's/^\[ -f "\$SINAL" \] || exit 0$/[ -f "$SINAL" ] \&\& exit 0/' "$HOOK" > "$SAB"
OUT=$(payload Agent "$SID" | CLAUDE_CONFIG_DIR="$TMP" bash "$SAB" 2>/dev/null)
check "gate sabotado (inverte o teste do sinal) DEIXA de negar" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "o sabotado ainda negou — o teste #2 é tautológico"

# 8 · o registro no hooks.json existe e aponta pro arquivo certo
HJ="$(dirname "$HOOK")/hooks.json"
check "hooks.json mora em hooks/ (na raiz é ignorado em silêncio)" \
  "$([ -f "$HJ" ] && echo 1 || echo 0)"
check "hooks.json registra PreToolUse com matcher Agent" \
  "$(jq -e '.hooks.PreToolUse[0].matcher == "Agent"' "$HJ" >/dev/null 2>&1 && echo 1 || echo 0)"
check "hooks.json aponta pro script deste teste" \
  "$(jq -r '.hooks.PreToolUse[0].hooks[0].command' "$HJ" 2>/dev/null \
     | grep -q 'pretooluse-sovai-motor.sh' && echo 1 || echo 0)"

echo
if [ "$FALHA" -eq 0 ]; then
  echo "OK ($OK checks)"
  exit 0
fi
echo "FALHOU ($FALHA de $((OK + FALHA)))"
exit 1
