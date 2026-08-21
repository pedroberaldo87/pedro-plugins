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
PS="$HERE/../../project-skills/lib/plan_state.py"  # acopla-ok: teste roda no monorepo, não na máquina de quem instala
PASS=0; FAIL=0

ROOT=$(mktemp -d "${TMPDIR:-/tmp}/plan-hooks-test.XXXXXX")
trap 'rm -rf "$ROOT"' EXIT
# resolve-dir.sh precisa reconhecer o diretório como projeto (marcador CLAUDE.md)
mkdir -p "$ROOT/proj"; : > "$ROOT/proj/CLAUDE.md"
PLANS="$ROOT/proj/.claude/plans"
mkdir -p "$PLANS"
PHASH=$(printf '%s' "$PLANS" | cksum | cut -d' ' -f1)

# Segundo projeto, este SEM plano nenhum: é onde a cobrança de plano AUSENTE
# tem que sair. Precisa ser outro diretório — o primeiro tem plano ativo, e a
# cobrança some justamente quando há plano.
VAZIO="$ROOT/vazio"
mkdir -p "$VAZIO"; : > "$VAZIO/CLAUDE.md"
PHASH_V=$(printf '%s' "$VAZIO/.claude/plans" | cksum | cut -d' ' -f1)

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

mark_of()  { printf '%s/claude-plan-mark-%s-%s-%s' "${TMPDIR:-/tmp}" "$(id -u)" "$1" "$PHASH"; }
nudge_of() { printf '%s/claude-plan-nudge-%s-%s-%s' "${TMPDIR:-/tmp}" "$(id -u)" "$1" "$PHASH"; }
# a cobrança de plano AUSENTE tem sentinela só dela; 2º argumento = qual projeto
missing_of() { printf '%s/claude-plan-missing-%s-%s-%s' "${TMPDIR:-/tmp}" "$(id -u)" "$1" "${2:-$PHASH}"; }

# transcript falso com N edições em N arquivos DISTINTOS.
# O `file_path` não é enfeite: a métrica das duas cobranças é ARQUIVO distinto,
# e um bloco tool_use sem file_path conta zero — fixture sem ele testa o silêncio.
mk_transcript() {
  local n="$1" f="$ROOT/t-$1.jsonl" i
  : > "$f"
  for ((i=0;i<n;i++)); do
    printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":"/x/a%d.py","old_string":"a","new_string":"b"}}]}}\n' "$i" >> "$f"
  done
  printf '%s' "$f"
}

# transcript falso com N edições NO MESMO arquivo — a métrica é arquivo, não chamada
mk_transcript_repet() {
  local n="$1" f="$ROOT/tr-$1.jsonl" i
  : > "$f"
  for ((i=0;i<n;i++)); do
    printf '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":"/x/mesmo.py"}}]}}\n' >> "$f"
  done
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
# o mesmo Stop, mas apontado pro projeto que não tem plano nenhum
run_st_v(){ printf '{"session_id":"%s","cwd":"%s","transcript_path":"%s"}' "$1" "$VAZIO" "$2" | bash "$ST" 2>/dev/null; }
ausente() { run_st_v "$1" "$2" | jq -r '.systemMessage // empty' 2>/dev/null | grep -c 'Sem plano aberto' | tr -d ' '; }

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
# O resumo sai igual; o cabeçalho é que depende de a sessão ter tocado o plano — aqui
# ela não tocou, então ele RELATA ("Plano aberto no projeto") em vez de AFIRMAR
# ("Onde estamos"). Ver a nota em plan_state.py:brief_lines.
check "PLAN_NUDGE=0 tira a cobrança e MANTÉM o resumo" \
      "$(! grep -q -- 'Nada marcado' <<< "$out" && grep -q -- 'Plano aberto no projeto' <<< "$out" && echo 1 || echo 0)"

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
sleep 1; run_ss s9 >/dev/null; rm -f "$(nudge_of s9)" "$(missing_of s9)"
out=$(run_st s9 "$T3" | jq -r '.systemMessage // empty' 2>/dev/null)
check "plano encerrado não cobra mais (nem resumo, nem cobrança de tique)" \
      "$(! grep -q -- 'Onde estamos' <<< "$out" && ! grep -q -- 'Nada marcado' <<< "$out" && echo 1 || echo 0)"
# Encerrou o plano e continuou editando: isso É trabalho sem plano aberto, e a
# cobrança nova assume o lugar. O silêncio de antes era o furo, não a feature.
check "encerrado o plano, seguir editando 3 arquivos cobra plano ausente" \
      "$(grep -q -- 'Sem plano aberto' <<< "$out" && echo 1 || echo 0)"
out=$(run_ss s10)
check "plano encerrado não aparece no começo da sessão" "$([ -z "$out" ] && echo 1 || echo 0)"

echo "Stop — auto-cura do marco (plugin instalado no meio da sessão)"
python3 "$PS" --dir "$PLANS" reopen p-teste >/dev/null 2>&1
rm -f "$(mark_of h1)" "$(nudge_of h1)"
out=$(run_st h1 "$T3" | jq -r '.systemMessage // empty' 2>/dev/null)
# O resumo sai; o cabeçalho é que não afirma, porque esta sessão não marcou plano nenhum
# e o hook passa o id dela ao brief. Ver a nota em plan_state.py:cmd_brief.
check "sem marco, o resumo do plano ativo SAI mesmo assim" \
      "$(grep -q -- 'Plano aberto no projeto' <<< "$out" && echo 1 || echo 0)"
check "e o hook CRIA o marco que faltava" "$([ -f "$(mark_of h1)" ] && echo 1 || echo 0)"
check "no turno seguinte a cobrança já funciona" \
      "$([ "$(cobranca h1 "$T3")" = "1" ] && echo 1 || echo 0)"
rm -f "$(mark_of h1)" "$(nudge_of h1)"

echo "Stop — o resumo de fim de turno"
# a seção anterior encerrou o plano; reabre pra testar o estado "em andamento"
python3 "$PS" --dir "$PLANS" reopen p-teste >/dev/null 2>&1
run_ss r1 >/dev/null
msg=$(run_st r1 "$T1" | jq -r '.systemMessage // empty' 2>/dev/null)
# Sessão que ainda não marcou passo nenhum: o resumo sai, sem afirmar que ela está ali.
check "com plano ativo, o resumo sai" "$(grep -q -- 'Plano aberto no projeto' <<< "$msg" && echo 1 || echo 0)"
# O harness prefixa "Stop says: " na PRIMEIRA linha. Sem uma linha em branco na
# frente, o cabeçalho gruda no prefixo e fica num nível diferente dos bullets.
# O `tr -d '\r'` é por causa do jq do Windows, que escreve stdout em modo TEXTO:
# a linha em branco chega como CR, `head -c 1` vê o CR e o teste reprovava por
# causa do interpretador, não da mensagem.
check "a mensagem abre com linha em branco, pro prefixo do harness não colar" \
      "$(run_st r1 "$T1" | jq -r '.systemMessage' | tr -d '\r' | head -c 1 | grep -q . && echo 0 || echo 1)"
# E marcar um passo é o que devolve a afirmação — este é o par do check acima. O
# CLAUDE_CODE_SESSION_ID tem que ser o da sessão do hook: é ele que grava a marca de
# autoria, e sem isso o tique é indistinguível do de uma sessão vizinha.
CLAUDE_CODE_SESSION_ID=r1 python3 "$PS" --dir "$PLANS" tick F1.1 --evidencia "prova do teste" >/dev/null 2>&1
msg_tocado=$(run_st r1 "$T1" | jq -r '.systemMessage // empty' 2>/dev/null)
check "marcado um passo, o resumo AFIRMA onde estamos" \
      "$(grep -q -- 'Onde estamos' <<< "$msg_tocado" && echo 1 || echo 0)"
# E a marca é de QUEM marcou: a sessão vizinha não herda a afirmação.
msg_vizinha=$(run_st r9 "$T1" | jq -r '.systemMessage // empty' 2>/dev/null)
check "a sessão vizinha NÃO herda a afirmação de quem marcou" \
      "$(! grep -q -- 'Onde estamos' <<< "$msg_vizinha" && echo 1 || echo 0)"
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

echo "Stop — trabalho grande SEM plano nenhum aberto"
# O furo que esta seção fecha: sem plano ativo o `brief` sai vazio, e o hook
# saía calado por isso — trabalho de muitos arquivos sem plano nunca era dito.
TA3=$(mk_transcript 3)
TA2=$(mk_transcript 2)
TR6=$(mk_transcript_repet 6)

rm -f "$(missing_of m1 "$PHASH_V")"
msg=$(run_st_v m1 "$TA3" | jq -r '.systemMessage // empty' 2>/dev/null)
check "3 arquivos e nenhum plano aberto -> cobra" \
      "$(grep -q -- 'Sem plano aberto' <<< "$msg" && echo 1 || echo 0)"
check "a cobrança diz quantos arquivos foram editados" \
      "$(grep -q -- 'editou 3 arquivos' <<< "$msg" && echo 1 || echo 0)"
check "cobra 1× por (sessão, projeto)" "$([ "$(ausente m1 "$TA3")" = "0" ] && echo 1 || echo 0)"

rm -f "$(missing_of m2 "$PHASH_V")"
check "2 arquivos não cobram (abaixo do piso)" "$([ "$(ausente m2 "$TA2")" = "0" ] && echo 1 || echo 0)"

# B1: a métrica é ARQUIVO distinto, não chamada. 6 edições num arquivo só é
# um arquivo — se isto cobrar, o piso virou medida de teimosia.
rm -f "$(missing_of m3 "$PHASH_V")"
check "6 edições no MESMO arquivo não cobram (a métrica é arquivo)" \
      "$([ "$(ausente m3 "$TR6")" = "0" ] && echo 1 || echo 0)"

rm -f "$(missing_of m4 "$PHASH_V")"
out=$(PLAN_NUDGE=0 run_st_v m4 "$TA3")
check "PLAN_NUDGE=0 cala a cobrança de plano ausente" "$([ -z "$out" ] && echo 1 || echo 0)"

rm -f "$(missing_of m5 "$PHASH_V")"
out=$(PLAN_STATUS=0 run_st_v m5 "$TA3")
check "PLAN_STATUS=0 também cala" "$([ -z "$out" ] && echo 1 || echo 0)"

rm -f "$(missing_of m6 "$PHASH_V")"
check "transcript inexistente não cobra (fail-open)" \
      "$([ "$(ausente m6 "$ROOT/nao-existe.jsonl")" = "0" ] && echo 1 || echo 0)"

rm -f "$(missing_of m7 "$PHASH_V")"
out=$(printf '{"session_id":"m7","cwd":"%s","transcript_path":"%s","stop_hook_active":true}' "$VAZIO" "$TA3" | bash "$ST" 2>/dev/null)
check "stop_hook_active=true cala a cobrança nova também (anti-loop)" "$([ -z "$out" ] && echo 1 || echo 0)"

# O outro lado do critério: COM plano aberto, esta cobrança não existe.
python3 "$PS" --dir "$PLANS" reopen p-teste >/dev/null 2>&1
rm -f "$(missing_of m8)" "$(nudge_of m8)"
msg=$(run_st m8 "$TA3" | jq -r '.systemMessage // empty' 2>/dev/null)
check "com plano ABERTO, os mesmos 3 arquivos não cobram plano ausente" \
      "$(! grep -q -- 'Sem plano aberto' <<< "$msg" && echo 1 || echo 0)"
check "e o resumo do plano aberto continua saindo, nomeando o plano" \
      "$(grep -q -- 'Plano de teste' <<< "$msg" && echo 1 || echo 0)"
python3 "$PS" --dir "$PLANS" close p-teste >/dev/null 2>&1

# A guarda do `open --json`, que sem este caso não é cobrada por ninguém:
# motor quebrado dá brief VAZIO igualzinho a "não há plano". Um plano ATIVO com
# JSON válido mas sem `phases` derruba os dois comandos (KeyError, stdout vazio)
# — e sem a guarda o hook acusaria plano ausente com o arquivo de plano ali,
# aberto, na frente dele. Mentir sobre o que existe é pior que calar.
mkdir -p "$VAZIO/.claude/plans"
printf '{"id":"torto","title":"plano sem fases","status":"active"}' > "$VAZIO/.claude/plans/torto.plan.json"
rm -f "$(missing_of m9 "$PHASH_V")"
check "plano ativo porém torto não vira 'plano ausente' (motor quebrado ≠ sem plano)" \
      "$([ "$(ausente m9 "$TA3")" = "0" ] && echo 1 || echo 0)"
rm -f "$VAZIO/.claude/plans/torto.plan.json"

echo "Stop — a régua do canal de texto (perfil hook), nos DOIS textos que saem daqui"
# O systemMessage sai num terminal: `**` chega literal e cabeçalho sem emoji não se
# destaca de nada. Quem cobra é a MESMA régua do gerador de página, pelo perfil `hook`.
# Saída vazia = passou; cada motivo recusado sai numa linha do stderr.
REGUA="$HERE/../lib/regua_texto.py"
regua() { printf '%s\n' "$1" | python3 "$REGUA" --perfil hook --onde "$2" - 2>&1 || :; }
check "a régua está vendorada no plugin (instalado, ele só enxerga a própria pasta)" \
      "$([ -f "$REGUA" ] && echo 1 || echo 0)"

# (1) o resumo de fim de turno
python3 "$PS" --dir "$PLANS" reopen p-teste >/dev/null 2>&1
rm -f "$(missing_of g1)" "$(nudge_of g1)"
RESUMO=$(run_st g1 "$TA3" | jq -r '.systemMessage // empty' 2>/dev/null)
check "o resumo REAL de fim de turno passa na régua" "$([ -z "$(regua "$RESUMO" resumo)" ] && echo 1 || echo 0)"
check "o mesmo resumo com markdown é RECUSADO" \
      "$(regua "$(printf '%s' "$RESUMO" | sed 's/Plano/**Plano**/')" resumo | grep -q markdown && echo 1 || echo 0)"
# O emoji do cabeçalho varia com o estado do plano (📍 / 📋 / ✅ / 🏁) e o texto abre
# com linha em branco (o prefixo do harness), então a mutação tira o primeiro token de
# toda linha que NÃO é bullet — é o cabeçalho, seja ele qual for.
check "o mesmo resumo sem emoji no cabeçalho é RECUSADO" \
      "$(regua "$(printf '%s' "$RESUMO" | sed '/^• /!s/^[^ ]* //')" resumo | grep -q emoji && echo 1 || echo 0)"
python3 "$PS" --dir "$PLANS" close p-teste >/dev/null 2>&1

# (2) o aviso de plano ausente — texto próprio, montado no shell
rm -f "$(missing_of g2 "$PHASH_V")"
AUSENTE=$(run_st_v g2 "$TA3" | jq -r '.systemMessage // empty' 2>/dev/null)
check "o aviso REAL de plano ausente passa na régua" "$([ -z "$(regua "$AUSENTE" ausente)" ] && echo 1 || echo 0)"
check "o mesmo aviso com markdown é RECUSADO" \
      "$(regua "$(printf '%s' "$AUSENTE" | sed 's/Sem plano/**Sem plano**/')" ausente | grep -q markdown && echo 1 || echo 0)"
check "o mesmo aviso sem emoji no cabeçalho é RECUSADO" \
      "$(regua "$(printf '%s' "$AUSENTE" | sed 's/^⚠️ //')" ausente | grep -q emoji && echo 1 || echo 0)"

# F22.12 — a camada de AVISO no lembrete de plano aberto: régua carregada não é
# plano varrido, e quem chega depois do /clear precisa ler isso antes de largar.
check "o lembrete de plano aberto carrega a linha do pré-check vencido" \
      "$(grep -q -- 'pré-check vencido → rode a caça antes de planejar ou' "$HERE/sessionstart-plan.sh" && echo 1 || echo 0)"

rm -f "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed,missing}-"$(id -u)"-g*-"$PHASH" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed,missing}-"$(id -u)"-g*-"$PHASH_V" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed,missing}-"$(id -u)"-s*-"$PHASH" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed,missing}-"$(id -u)"-r*-"$PHASH" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed,missing}-"$(id -u)"-h*-"$PHASH" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed,missing}-"$(id -u)"-m*-"$PHASH" \
      "${TMPDIR:-/tmp}"/claude-plan-{mark,nudge,closed,missing}-"$(id -u)"-m*-"$PHASH_V"
echo
if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"
