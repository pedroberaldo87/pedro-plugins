#!/bin/bash
# test_exitplan_gate.sh — o gate de ExitPlanMode não pode brigar consigo mesmo.
#
# Dois modos de falha, os dois já aconteceram:
#   1. o gate barrava a página que ele mesmo manda gerar (`page --mode approve`),
#      e o modelo ficava preso entre duas ordens do mesmo arquivo;
#   2. o gate ditava um JSON de plano que o `init` recusava, então seguir a
#      instrução ao pé da letra dava exit 2.
# O teste 2 não confere texto: ele RECORTA o JSON da mensagem do gate e manda pro
# init de verdade. Documentação que mente quebra o teste.
#
# Roda isolado em TMPDIR. Uso: bash test_exitplan_gate.sh

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/pre-exitplan-visualize.sh"
PS="$HERE/../lib/plan_state.py"
PASS=0; FAIL=0

ROOT=$(mktemp -d "${TMPDIR:-/tmp}/exitplan-gate-test.XXXXXX")
trap 'rm -rf "$ROOT"' EXIT
mkdir -p "$ROOT/proj/.claude/plans" "$ROOT/proj/.claude/visual"
: > "$ROOT/proj/CLAUDE.md"
PROJ="$ROOT/proj"
PLANS="$PROJ/.claude/plans"
VIS="$PROJ/.claude/visual"

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

# o cap é por (sessão, projeto): zerar entre casos senão o 4º caso vira silêncio
PHASH=$(printf '%s' "$VIS" | cksum | cut -d' ' -f1)
zera_cap() { rm -f "${TMPDIR:-/tmp}/claude-visual-gate-$(id -u)-$1-$PHASH"; }

# roda o gate e devolve "<exit>|<stderr>"
run_gate() {
  local sid="$1" out rc
  zera_cap "$sid"
  out=$(printf '{"session_id":"%s","cwd":"%s","tool_name":"ExitPlanMode","tool_input":{"plan":"o plano"}}' \
        "$sid" "$PROJ" | bash "$GATE" 2>&1 >/dev/null)
  rc=$?
  printf '%s|%s' "$rc" "$out"
}

mk_plan() {
  cat > "$ROOT/in.json" <<'JSON'
{"id":"p-gate","title":"Plano do gate",
 "requisitos":[{"id":"S-1.1","titulo":"Requisito do teste","ca":"o comando sai 0",
                "epico":"E1 — Teste"}],
 "phases":[
 {"id":"F1","title":"Fase um","items":[
   {"id":"F1.1","title":"passo um","desc":"faz a coisa",
    "pronto":"o comando sai 0","requisito":"S-1.1"}]},
 {"id":"F2","title":"Fase dois","items":[
   {"id":"F2.1","title":"passo dois","desc":"faz a outra coisa",
    "pronto":"o comando sai 0","requisito":"S-1.1"}]}]}
JSON
  python3 "$PS" --dir "$PLANS" init --file "$ROOT/in.json" >/dev/null || {
    echo "mk_plan: init recusado — o fixture está fora do schema" >&2; return 1; }
}

echo "Gate de prova — a página gerada pelo próprio plan_state.py passa"
mk_plan || exit 1
python3 "$PS" --dir "$PLANS" page --mode approve \
        --out "$VIS/2026-01-01-sess-aaaaaaaa-plan.html" >/dev/null
r=$(run_gate aaaaaaaa-1111)
check "árvore de aprovação gerada não é barrada por falta de prova" \
      "$(! grep -q 'pede decisão sem mostrar a prova' <<< "$r" && echo 1 || echo 0)"
check "e o gate sai 0 (a página tem plano em arquivo)" \
      "$([ "${r%%|*}" = "0" ] && echo 1 || echo 0)"

echo "Gate de prova — segue barrando decisão escrita à mão sem prova"
cp "$VIS/2026-01-01-sess-aaaaaaaa-plan.html" "$VIS/2026-01-01-sess-bbbbbbbb-plan.html"
# um .decision-card colado na mesma página: agora há conclusão afirmada, e ela
# continua sem nada que a sustente
printf '<div class="decision-card">escolha A ou B</div>\n' >> "$VIS/2026-01-01-sess-bbbbbbbb-plan.html"
r=$(run_gate bbbbbbbb-2222)
check "decision-card sem prova ainda é barrado" \
      "$(grep -q 'pede decisão sem mostrar a prova' <<< "$r" && echo 1 || echo 0)"
check "e devolve exit 2" "$([ "${r%%|*}" = "2" ] && echo 1 || echo 0)"

echo "Gate de prova — prova em branco continua sendo barrada"
cp "$VIS/2026-01-01-sess-aaaaaaaa-plan.html" "$VIS/2026-01-01-sess-cccccccc-plan.html"
{ printf '<div class="decision-card">escolha A ou B</div>\n'
  printf '<div class="evidencia vazio"><pre></pre></div>\n'; } >> "$VIS/2026-01-01-sess-cccccccc-plan.html"
r=$(run_gate cccccccc-3333)
check "evidencia vazio não conta como prova" \
      "$(grep -q 'pede decisão sem mostrar a prova' <<< "$r" && echo 1 || echo 0)"

echo "O JSON que o gate ENSINA é aceito pelo init"
# recorta o primeiro objeto JSON da mensagem e manda pro init de verdade
extrai_json() {
  python3 - "$1" <<'PY'
import json, sys
txt = sys.argv[1]
i = txt.find('{"id"')
if i < 0:
    sys.exit(1)
obj, _ = json.JSONDecoder().raw_decode(txt[i:])
print(json.dumps(obj))
PY
}

# caminho FEEDBACK: nenhum HTML desta sessão
r=$(run_gate dddddddd-4444)
if extrai_json "${r#*|}" > "$ROOT/do-gate-feedback.json" 2>/dev/null; then
  ok "o bloco sem-HTML traz um JSON de plano recortável"
  rm -rf "$ROOT/plans-fb"; mkdir -p "$ROOT/plans-fb"
  python3 "$PS" --dir "$ROOT/plans-fb" init --file "$ROOT/do-gate-feedback.json" >/dev/null 2>"$ROOT/err-fb"
  check "e o init o aceita" "$([ ! -s "$ROOT/err-fb" ] && echo 1 || echo 0)"
  [ -s "$ROOT/err-fb" ] && sed 's/^/       /' "$ROOT/err-fb"
else
  bad "o bloco sem-HTML traz um JSON de plano recortável"
  bad "e o init o aceita"
fi

# caminho PLANFILE: há HTML da sessão, mas nenhum plano em arquivo
python3 "$PS" --dir "$PLANS" close p-gate >/dev/null 2>&1
cp "$VIS/2026-01-01-sess-aaaaaaaa-plan.html" "$VIS/2026-01-01-sess-eeeeeeee-plan.html"
r=$(run_gate eeeeeeee-5555)
check "sem plano em arquivo, o gate cobra o arquivo" \
      "$(grep -q 'não existe como ARQUIVO' <<< "$r" && echo 1 || echo 0)"
if extrai_json "${r#*|}" > "$ROOT/do-gate-planfile.json" 2>/dev/null; then
  ok "o bloco sem-ARQUIVO traz um JSON de plano recortável"
  rm -rf "$ROOT/plans-pf"; mkdir -p "$ROOT/plans-pf"
  python3 "$PS" --dir "$ROOT/plans-pf" init --file "$ROOT/do-gate-planfile.json" >/dev/null 2>"$ROOT/err-pf"
  check "e o init o aceita" "$([ ! -s "$ROOT/err-pf" ] && echo 1 || echo 0)"
  [ -s "$ROOT/err-pf" ] && sed 's/^/       /' "$ROOT/err-pf"
else
  bad "o bloco sem-ARQUIVO traz um JSON de plano recortável"
  bad "e o init o aceita"
fi

echo "Kill-switch e fail-open"
r=$(zera_cap ffffffff-6666; printf '{"session_id":"ffffffff-6666","cwd":"%s","tool_name":"ExitPlanMode","tool_input":{"plan":"x"}}' "$PROJ" \
    | VISUAL_GATE=0 bash "$GATE" 2>&1 >/dev/null; printf '|%s' "$?")
check "VISUAL_GATE=0 cala tudo" "$([ "${r##*|}" = "0" ] && [ -z "${r%|*}" ] && echo 1 || echo 0)"

out=$(printf '{"cwd":"%s","tool_name":"ExitPlanMode","tool_input":{"plan":"x"}}' "$PROJ" | bash "$GATE" 2>&1 >/dev/null)
check "sem session_id, não bloqueia (fail-open)" "$([ -z "$out" ] && echo 1 || echo 0)"

for s in aaaaaaaa-1111 bbbbbbbb-2222 cccccccc-3333 dddddddd-4444 eeeeeeee-5555 ffffffff-6666; do
  zera_cap "$s"
done
echo
if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"
