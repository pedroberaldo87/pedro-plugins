#!/usr/bin/env bash
# test_plan_gate.sh — juiz mockado por env var; testa allow/deny/cap.
set -euo pipefail
# O hook grava no temporário DO SISTEMA — a suíte pergunta pelo mesmo caminho
# que ele, em vez de assumir /tmp.
# shellcheck source=/dev/null
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-tmpdir.sh"
TMPD=$(td_tmpdir)
HERE="$(cd "$(dirname "$0")" && pwd)"
export CLAUDE_PLUGIN_ROOT="$(dirname "$HERE")"
REPO="$(mktemp -d /tmp/ig-pg-XXXXXX)"; git -C "$REPO" init -q
trap 'rm -rf "$REPO" "$TMPD"/intent-guard-plandeny-pgsid' EXIT
L="$CLAUDE_PLUGIN_ROOT/lib/ledger.py"
printf 'export CSV com ;' | python3 "$L" record-raw --cwd "$REPO" --session pgsid --text-stdin

mkin() { python3 -c 'import json,sys; print(json.dumps({"session_id":"pgsid","cwd":sys.argv[1],"tool_name":"ExitPlanMode","tool_input":{"plan":sys.argv[2]}}))' "$@"; }

# 1. juiz diz que falta cobertura → exit 2 e classify aplicado
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_judge_miss.sh"
cat > "$HERE/mock_judge_miss.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null
echo '{"classify":[{"ev":"classify","raw":"r-1","class":"pedido","resumo":"export CSV ;","substitui":null}],"missing":[{"id":"p-1","resumo":"export CSV ;"}]}'
EOF
chmod +x "$HERE/mock_judge_miss.sh"
set +e; mkin "$REPO" 'plano que ignora o csv' | bash "$HERE/plan-gate.sh"; RC=$?; set -e
[ "$RC" = 2 ]
python3 "$L" state --cwd "$REPO" | grep -q '"p-1"'   # classify foi aplicado mesmo com deny

# 2. juiz diz coberto → exit 0
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_judge_ok.sh"
cat > "$HERE/mock_judge_ok.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null; echo '{"classify":[],"missing":[]}'
EOF
chmod +x "$HERE/mock_judge_ok.sh"
mkin "$REPO" 'plano com export csv separador ;' | bash "$HERE/plan-gate.sh"

# 3. cap: 2 denies já dados → 3ª tentativa NÃO bloqueia mesmo com missing
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_judge_miss2.sh"
cat > "$HERE/mock_judge_miss2.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null; echo '{"classify":[],"missing":[{"id":"p-1","resumo":"x"}]}'
EOF
chmod +x "$HERE/mock_judge_miss2.sh"
echo 2 > "$TMPD"/intent-guard-plandeny-pgsid
mkin "$REPO" 'plano qualquer' | bash "$HERE/plan-gate.sh"   # exit 0 = passou

# 4. sem pedidos vivos nem pendentes → nem chama juiz (judge inexistente não pode quebrar)
REPO2="$(mktemp -d /tmp/ig-pg2-XXXXXX)"; git -C "$REPO2" init -q
export INTENT_GUARD_JUDGE_CMD="/nao/existe"
mkin "$REPO2" 'plano' | bash "$HERE/plan-gate.sh"
rm -rf "$REPO2" "$HERE"/mock_judge_*.sh

# 5. sem session_id → exit 0 (fail-open), nunca cria nosid file
REPO3="$(mktemp -d /tmp/ig-pg3-XXXXXX)"; git -C "$REPO3" init -q
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_judge_miss3.sh"
cat > "$HERE/mock_judge_miss3.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null; echo '{"classify":[],"missing":[{"id":"p-1","resumo":"x"}]}'
EOF
chmod +x "$HERE/mock_judge_miss3.sh"
python3 "$L" record-raw --cwd "$REPO3" --session '' --text-stdin <<<'entrada sem session_id'
# mkin sem session_id: omit session_id field
NOID_JSON="$(python3 -c 'import json,sys; print(json.dumps({"cwd":sys.argv[1],"tool_name":"ExitPlanMode","tool_input":{"plan":sys.argv[2]}}))' "$REPO3" 'plano')"
set +e; echo "$NOID_JSON" | bash "$HERE/plan-gate.sh"; RC=$?; set -e
[ "$RC" = 0 ]   # deve passar (fail-open)
[ ! -f "$TMPD"/intent-guard-plandeny-nosid ]   # nunca cria file com nosid
rm -rf "$REPO3" "$HERE"/mock_judge_miss3.sh

echo "test_plan_gate: OK"
