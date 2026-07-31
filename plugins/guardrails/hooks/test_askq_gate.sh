#!/bin/bash
# Suite do askq-humanize.sh — a FIAÇÃO, não as réguas.
#
# As réguas têm suite própria (lib/test_askq_lint.py, 40 checks). Aqui só o que
# historicamente quebrou nos hooks deste repo: cap, kill-switch, fail-open e o
# canal de saída.
#
# Isolamento total: HOME aponta pra um mktemp, então nem o log nem o contador
# reais são tocados. Sem isso a suite mexeria em ~/.claude/guardrails do usuário.

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/askq-humanize.sh"
FAKE_HOME="$(mktemp -d)"
trap 'rm -rf "$FAKE_HOME"' EXIT

PASS=0; FAIL=0
check() {
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1))
  else FAIL=$((FAIL + 1)); printf '  ✗ %s — esperava %s, veio %s\n' "$1" "$3" "$2" >&2; fi
}

# Roda o hook com HOME isolado e devolve o veredito. Saída vazia = allow (jq sobre
# entrada vazia não emite nem o default).
run() {
  local out
  out="$(printf '%s' "$1" | HOME="$FAKE_HOME" ASKQ_GATE="${ASKQ_GATE:-1}" bash "$HOOK" 2>/dev/null)"
  [ -z "$out" ] && { echo allow; return; }
  printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null
}

SID="test-$$"
OK_OPTS='[{"label":"Manter como está","description":"Nada muda hoje e o problema volta na próxima rodada."},{"label":"Trocar agora","description":"Custa uma hora e fecha o furo de uma vez, sem voltar."}]'
OK_Q='O relatório da semana deve sair com os números da semana passada ou esperar o fechamento de amanhã?'

payload() { # $1=question  $2=options-json  $3=session
  jq -nc --arg q "$1" --argjson o "$2" --arg s "$3" \
    '{session_id:$s, tool_name:"AskUserQuestion",
      tool_input:{questions:[{question:$q, header:"Escopo", options:$o}]}}'
}

echo "── canal de saída ──"
SUJA="$(payload 'Qual das duas?' '[{"label":"A","description":""},{"label":"B","description":""}]' "$SID")"
check "pergunta seca e sem consequência é DEVOLVIDA" "$(run "$SUJA")" "deny"

LIMPA="$(payload "$OK_Q" "$OK_OPTS" "$SID-limpa")"
check "pergunta que se explica PASSA" "$(run "$LIMPA")" "allow"

# A mensagem tem que citar o que faltou — acusação sem o trecho ensina a ignorar.
MSG="$(printf '%s' "$SUJA" | HOME="$FAKE_HOME" bash "$HOOK" 2>/dev/null | jq -r '.hookSpecificOutput.permissionDecisionReason')"
case "$MSG" in *"não diz o que ACONTECE"*) R=sim ;; *) R=nao ;; esac
check "a devolução cita a violação concreta" "$R" "sim"
case "$MSG" in *"ASKQ_GATE=0"*) R=sim ;; *) R=nao ;; esac
check "a devolução ensina a desligar o gate" "$R" "sim"

echo "── kill-switch ──"
check "ASKQ_GATE=0 libera mesmo a pergunta suja" \
  "$(ASKQ_GATE=0 run "$(payload 'Qual das duas?' '[{"label":"A","description":""}]' "$SID-off")")" "allow"

echo "── fail-open ──"
check "sem session_id não bloqueia" \
  "$(run '{"tool_name":"AskUserQuestion","tool_input":{"questions":[{"question":"Qual?","options":[{"label":"A","description":""}]}]}}')" "allow"
check "JSON quebrado não bloqueia" "$(run 'nao sou json')" "allow"
check "tool_input sem questions não bloqueia" \
  "$(run "{\"session_id\":\"$SID-b\",\"tool_input\":{}}")" "allow"
check "questions com forma estranha não bloqueia" \
  "$(run "{\"session_id\":\"$SID-c\",\"tool_input\":{\"questions\":\"x\"}}")" "allow"

echo "── cap anti-loop, escopado por sessão ──"
CAPSID="cap-$$"
CAPQ="$(payload 'Qual das duas?' '[{"label":"A","description":""}]' "$CAPSID")"
check "1ª devolução"  "$(run "$CAPQ")" "deny"
check "2ª devolução"  "$(run "$CAPQ")" "deny"
check "3ª devolução"  "$(run "$CAPQ")" "deny"
check "4ª vira silêncio (degrada, não prende)" "$(run "$CAPQ")" "allow"
# Outra sessão começa do zero — o cap não vaza entre sessões.
check "sessão nova NÃO herda o cap esgotado" \
  "$(run "$(payload 'Qual das duas?' '[{"label":"A","description":""}]' "outra-$$")")" "deny"

echo "── log do input cru ──"
LOGF="$FAKE_HOME/.claude/guardrails/askq.log"
check "o log existe" "$([ -f "$LOGF" ] && echo sim || echo nao)" "sim"
case "$(cat "$LOGF" 2>/dev/null)" in *'"questions"'*) R=sim ;; *) R=nao ;; esac
check "o log guarda o tool_input cru" "$R" "sim"
case "$(cat "$LOGF" 2>/dev/null)" in *"$SID-limpa"*) R=sim ;; *) R=nao ;; esac
check "loga também a pergunta LIMPA (é a prova de que o evento dispara)" "$R" "sim"

echo "── anti-tautologia ──"
# Sabota a régua e exige que a suite sinta. Sem isto, um hook que sempre liberasse
# passaria em todos os casos "allow" acima.
SAB="$(mktemp -d)"; cp -R "$(dirname "$HOOK")/.." "$SAB/g"
sed -i.bak 's/^MIN_DESC = 30/MIN_DESC = 0/' "$SAB/g/lib/askq_lint.py"
OUT="$(printf '%s' "$SUJA" | HOME="$FAKE_HOME" bash "$SAB/g/hooks/askq-humanize.sh" 2>/dev/null)"
case "$OUT" in *"não diz o que ACONTECE"*) R=sim ;; *) R=nao ;; esac
rm -rf "$SAB"
check "com MIN_DESC=0 a régua da consequência fica MUDA" "$R" "nao"

printf '── %d passou · %d falhou ──\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
