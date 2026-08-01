#!/bin/bash
# test_plan_hooks.sh — os caminhos SILENCIOSOS dos dois hooks de plano,
# mais o resumo de fim de turno (o "onde nós estamos" em 1-3 bullets).
#
# O que importa aqui não é o aviso aparecer: é ele NÃO aparecer quando não deve.
# Hook que cobra errado é hook que o usuário desliga, e aí ele não cobra nunca.
#
# Roda isolado: cada caso monta seu próprio diretório de planos e seu próprio
# transcript falso em TMPDIR. Uso: bash test_plan_hooks.sh

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SS="$HERE/sessionstart-plan.sh"
ST="$HERE/stop-plan-status.sh"
PS="$HERE/../lib/plan_state.py"
PASS=0; FAIL=0

ROOT=$(mktemp -d "${TMPDIR:-/tmp}/plan-hooks-test.XXXXXX")
trap 'rm -rf "$ROOT"' EXIT
# resolve-dir.sh precisa reconhecer o diretório como projeto (marcador CLAUDE.md)
mkdir -p "$ROOT/proj"; : > "$ROOT/proj/CLAUDE.md"
PLANS="$ROOT/proj/.claude/plans"
mkdir -p "$PLANS"
PHASH=$(printf '%s' "$PLANS" | cksum | cut -d' ' -f1)

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

mark_of()  { printf '%s/claude-plan-mark-%s-%s-%s' "${TMPDIR:-/tmp}" "$(id -u)" "$1" "$PHASH"; }
nudge_of() { printf '%s/claude-plan-nudge-%s-%s-%s' "${TMPDIR:-/tmp}" "$(id -u)" "$1" "$PHASH"; }

# transcript falso com N tool_use de edição
mk_transcript() {
  local n="$1" f="$ROOT/t-$1.jsonl" i
  : > "$f"
  for ((i=0;i<n;i++)); do printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit"}]}}\n' >> "$f"; done
  printf '%s' "$f"
}

mk_plan() {
  # `requisitos`, `pronto` e `requisito` são obrigatórios desde 2026-08-01 em toda
  # tarefa que nasce agora — e num plano de teste todas nascem agora.
  cat > "$ROOT/in.json" <<JSON
{"id":"p-teste","title":"Plano de teste",
 "requisitos":[{"id":"S-1.1","titulo":"Requisito do teste","ca":"o comando sai 0",
                "epico":"E1 — Teste"}],
 "phases":[
 {"id":"F1","title":"Fase um","items":[
   {"id":"F1.1","title":"passo um","desc":"faz a coisa",
    "pronto":"o comando sai 0","requisito":"S-1.1"},
   {"id":"F1.2","title":"passo dois","desc":"faz a outra coisa",
    "pronto":"o comando sai 0","requisito":"S-1.1"}]}]}
JSON
  # SEM silenciar stderr: init recusado tem que quebrar o teste, não sumir
  python3 "$PS" --dir "$PLANS" init --file "$ROOT/in.json" >/dev/null || {
    echo "mk_plan: init recusado — o fixture está fora do schema" >&2
    return 1
  }
}

run_ss()  { printf '{"session_id":"%s","cwd":"%s"}' "$1" "$ROOT/proj" | bash "$SS" 2>/dev/null; }
# O hook de Stop mudou de propósito em 2026-07-27: antes SÓ cobrava o tique,
# agora RESUME sempre que há plano ativo. Então "calar" deixou de significar
# "saída vazia" — significa "sem o bullet de cobrança". Os testes seguem essa
# distinção: `cobranca` isola o bullet, `run_st` continua devolvendo o JSON.
cobranca(){ run_st "$1" "$2" | jq -r '.systemMessage // empty' 2>/dev/null | grep -c 'Nada marcado' | tr -d ' '; }
run_st()  { printf '{"session_id":"%s","cwd":"%s","transcript_path":"%s"}' "$1" "$ROOT/proj" "$2" | bash "$ST" 2>/dev/null; }

echo "SessionStart"
out=$(run_ss s0)
check "sem plano nenhum, não fala nada" "$([ -z "$out" ] && echo 1 || echo 0)"
check "mesmo sem plano, deixa o marco da sessão" "$([ -f "$(mark_of s0)" ] && echo 1 || echo 0)"

mk_plan
out=$(run_ss s1)
check "com plano aberto, injeta contexto" "$(grep -q -- 'plano(s) de implementação ABERTO' <<< "$out" && echo 1 || echo 0)"
check "o contexto traz o progresso" "$(grep -q -- '0/2 passos' <<< "$out" && echo 1 || echo 0)"
check "o contexto traz o caminho do arquivo" "$(grep -q -- 'p-teste.plan.json' <<< "$out" && echo 1 || echo 0)"
check "é JSON de SessionStart válido" "$(printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName == "SessionStart"' >/dev/null 2>&1 && echo 1 || echo 0)"

echo "Stop — a COBRANÇA cala onde tem que calar (o resumo, não)"
T3=$(mk_transcript 3)
T1=$(mk_transcript 1)

rm -f "$(mark_of s2)" "$(nudge_of s2)"
check "sem marco de sessão, não cobra (não dá pra saber o que foi marcado)" "$([ "$(cobranca s2 "$T3")" = "0" ] && echo 1 || echo 0)"

run_ss s3 >/dev/null; rm -f "$(nudge_of s3)"
check "com só 1 edição, não cobra (abaixo do piso de ruído)" "$([ "$(cobranca s3 "$T1")" = "0" ] && echo 1 || echo 0)"

run_ss s4 >/dev/null; rm -f "$(nudge_of s4)"
sleep 1
python3 "$PS" --dir "$PLANS" tick F1.1 --evidencia "bash test_plan_hooks.sh -> ok" >/dev/null 2>&1
check "se marcou um passo nesta sessão, não cobra" "$([ "$(cobranca s4 "$T3")" = "0" ] && echo 1 || echo 0)"

run_ss s5 >/dev/null; rm -f "$(nudge_of s5)"
out=$(printf '{"session_id":"s5","cwd":"%s","transcript_path":"%s","stop_hook_active":true}' "$ROOT/proj" "$T3" | bash "$ST" 2>/dev/null)
check "stop_hook_active=true cala TUDO (anti-loop)" "$([ -z "$out" ] && echo 1 || echo 0)"

run_ss s6 >/dev/null; rm -f "$(nudge_of s6)"
out=$(PLAN_NUDGE=0 run_st s6 "$T3" | jq -r '.systemMessage // empty' 2>/dev/null)
check "PLAN_NUDGE=0 tira a cobrança e MANTÉM o resumo" \
      "$(! grep -q -- 'Nada marcado' <<< "$out" && grep -q -- 'Onde estamos' <<< "$out" && echo 1 || echo 0)"

run_ss s7 >/dev/null; rm -f "$(nudge_of s7)"
check "transcript inexistente não cobra (fail-open)" "$([ "$(cobranca s7 "$ROOT/nao-existe.jsonl")" = "0" ] && echo 1 || echo 0)"

echo "Stop — o aviso, quando é pra avisar"
sleep 1; run_ss s8 >/dev/null; rm -f "$(nudge_of s8)"
out=$(run_st s8 "$T3")
msg=$(printf '%s' "$out" | jq -r '.systemMessage // empty' 2>/dev/null)
check "cobra com 3 edições e nenhum tique" "$(grep -q -- 'Nada marcado' <<< "$msg" && echo 1 || echo 0)"
check "a cobrança diz quantos arquivos foram editados" "$(grep -q -- 'editou 3 arquivos' <<< "$msg" && echo 1 || echo 0)"
check "o resumo vem junto, nomeando o plano" "$(grep -q -- 'Plano de teste' <<< "$msg" && echo 1 || echo 0)"
check "com cobrança, a mensagem NÃO passa de 3 bullets" "$([ "$(grep -c -- '^•' <<< "$msg")" -le 3 ] && echo 1 || echo 0)"
check "a cobrança toma o lugar do 'Falta'" "$(! grep -q -- 'Falta:' <<< "$msg" && echo 1 || echo 0)"
check "cobra 1× por sessão (throttle)" "$([ "$(cobranca s8 "$T3")" = "0" ] && echo 1 || echo 0)"

echo "Stop — plano encerrado some do radar"
python3 "$PS" --dir "$PLANS" close p-teste >/dev/null 2>&1
sleep 1; run_ss s9 >/dev/null; rm -f "$(nudge_of s9)"
out=$(run_st s9 "$T3")
check "plano encerrado não cobra mais" "$([ -z "$out" ] && echo 1 || echo 0)"
out=$(run_ss s10)
check "plano encerrado não aparece no começo da sessão" "$([ -z "$out" ] && echo 1 || echo 0)"

echo "Stop — auto-cura do marco (plugin instalado no meio da sessão)"
python3 "$PS" --dir "$PLANS" reopen p-teste >/dev/null 2>&1
rm -f "$(mark_of h1)" "$(nudge_of h1)"
out=$(run_st h1 "$T3" | jq -r '.systemMessage // empty' 2>/dev/null)
check "sem marco, o resumo do plano ativo SAI mesmo assim" \
      "$(grep -q -- 'Onde estamos' <<< "$out" && echo 1 || echo 0)"
check "e o hook CRIA o marco que faltava" "$([ -f "$(mark_of h1)" ] && echo 1 || echo 0)"
check "no turno seguinte a cobrança já funciona" \
      "$([ "$(cobranca h1 "$T3")" = "1" ] && echo 1 || echo 0)"
rm -f "$(mark_of h1)" "$(nudge_of h1)"

echo "Stop — o resumo de fim de turno"
# a seção anterior encerrou o plano; reabre pra testar o estado "em andamento"
python3 "$PS" --dir "$PLANS" reopen p-teste >/dev/null 2>&1
run_ss r1 >/dev/null
msg=$(run_st r1 "$T1" | jq -r '.systemMessage // empty' 2>/dev/null)
check "com plano ativo, resume onde estamos" "$(grep -q -- 'Onde estamos' <<< "$msg" && echo 1 || echo 0)"
check "o resumo cabe em no máximo 3 bullets" "$([ "$(grep -c -- '^•' <<< "$msg")" -le 3 ] && echo 1 || echo 0)"
check "o resumo diz o progresso" "$(grep -q -- 'Feito:' <<< "$msg" && echo 1 || echo 0)"
check "o resumo diz onde estamos agora" "$(grep -q -- 'Agora:' <<< "$msg" && echo 1 || echo 0)"
check "o resumo diz o que falta" "$(grep -q -- 'Falta:' <<< "$msg" && echo 1 || echo 0)"

out=$(PLAN_STATUS=0 run_st r1 "$T1")
check "PLAN_STATUS=0 cala o resumo inteiro" "$([ -z "$out" ] && echo 1 || echo 0)"

python3 "$PS" --dir "$PLANS" tick F1.2 --evidencia "bash test_plan_hooks.sh -> ok" >/dev/null 2>&1
run_ss r2 >/dev/null; rm -f "$(nudge_of r2)"
msg=$(run_st r2 "$T1" | jq -r '.systemMessage // empty' 2>/dev/null)
check "com tudo marcado, a mensagem é INEQUÍVOCA" "$(grep -q -- 'CONCLUÍDO' <<< "$msg" && echo 1 || echo 0)"
check "e ela diz que há prova em cada passo" "$(grep -q -- 'prova anexada' <<< "$msg" && echo 1 || echo 0)"

sleep 1; run_ss r3 >/dev/null; rm -f "$(nudge_of r3)"
python3 "$PS" --dir "$PLANS" close p-teste >/dev/null 2>&1
msg=$(run_st r3 "$T1" | jq -r '.systemMessage // empty' 2>/dev/null)
check "encerrado NESTA sessão -> confirma uma vez" "$(grep -q -- 'PLANO ENCERRADO' <<< "$msg" && echo 1 || echo 0)"
rm -f "$(mark_of r4)"
out=$(run_st r4 "$T1")
check "encerrado e sem marco -> silêncio (não vira lembrete eterno)" "$([ -z "$out" ] && echo 1 || echo 0)"

rm -f "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed}-"$(id -u)"-s*-"$PHASH" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed}-"$(id -u)"-r*-"$PHASH" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed}-"$(id -u)"-h*-"$PHASH"
echo
if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"
