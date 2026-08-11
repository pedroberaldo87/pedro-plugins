#!/usr/bin/env bash
set -euo pipefail
# O hook grava no temporário DO SISTEMA — a suíte pergunta pelo mesmo caminho
# que ele, em vez de assumir /tmp.
# shellcheck source=/dev/null
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-tmpdir.sh"
TMPD=$(td_tmpdir)
HERE="$(cd "$(dirname "$0")" && pwd)"
export CLAUDE_PLUGIN_ROOT="$(dirname "$HERE")"
# O temporário vem de `td_tmpdir`, nunca de `/tmp` cravado: no Git Bash do
# Windows `/tmp` é caminho do SHELL, e o `ledger.py`/`python3` que recebe esse
# `cwd` é o Python nativo — ele resolve `/tmp/x` como `C:\tmp\x`, que não
# existe. O ledger nascia noutro lugar e o `grep` do teste não achava nada.
REPO="$(mktemp -d "$(td_tmpdir)"/ig-ck-XXXXXX)"; git -C "$REPO" init -q
# A identidade e LOCAL deste repo de mentira: o runner da esteira nao tem
# `user.email` global, e o `git commit` de baixo saía `fatal: empty ident name`
# com codigo 128 — o job inteiro morria ali, no Linux, desde sempre. Suite que
# cria o proprio repo nao pode depender do ~/.gitconfig de quem a roda.
git -C "$REPO" config user.email "ck@exemplo.invalido"
git -C "$REPO" config user.name "bancada"
trap 'rm -rf "$REPO"; rm -f "$TMPD"/intent-guard-ckptblock-cksid-* "$TMPD"/intent-guard-ckptcap-cksid' EXIT
# o cap por sessao (v0.5.0) e estado FORA do $REPO: sem limpar aqui ele sobrevive
# entre execucoes e a suite reprova na segunda rodada por lixo, nao por defeito.
rm -f "$TMPD"/intent-guard-ckptcap-cksid
L="$CLAUDE_PLUGIN_ROOT/lib/ledger.py"

# Create initial commit so git has history
echo "test" > "$REPO/test.txt"
git -C "$REPO" add test.txt
git -C "$REPO" commit -q -m "initial"

printf 'export CSV' | python3 "$L" record-raw --cwd "$REPO" --session cksid --text-stdin
printf '%s' '{"ev":"classify","raw":"r-1","class":"pedido","resumo":"export CSV","substitui":null}' | python3 "$L" apply --cwd "$REPO"

mkin() { python3 -c 'import json,sys; print(json.dumps({"session_id":"cksid","cwd":sys.argv[1],"tool_name":"TaskUpdate","tool_input":{"taskId":"7","status":sys.argv[2]}}))' "$@"; }

# 1. status != completed → silêncio
OUT="$(mkin "$REPO" in_progress | bash "$HERE/task-checkpoint.sh")"
[ -z "$OUT" ]

# 2. drift → decision:block (make a change to trigger git status)
echo "modified" > "$REPO/test.txt"
cat > "$HERE/mock_ck_drift.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null; echo '{"verdict":"drift","reason":"nenhum diff toca o export CSV"}'
EOF
chmod +x "$HERE/mock_ck_drift.sh"
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_ck_drift.sh"
OUT="$(mkin "$REPO" completed | bash "$HERE/task-checkpoint.sh")"
echo "$OUT" | grep -q '"decision"'
echo "$OUT" | grep -q 'export CSV'

# 3. mesma task de novo → 1 bloqueio por task, agora silêncio
OUT="$(mkin "$REPO" completed | bash "$HERE/task-checkpoint.sh")"
[ -z "$OUT" ]

# 4. ok → silêncio (task nova, com mudança nova)
echo "another change" > "$REPO/test.txt"
cat > "$HERE/mock_ck_ok.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null; echo '{"verdict":"ok","reason":""}'
EOF
chmod +x "$HERE/mock_ck_ok.sh"
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_ck_ok.sh"
OUT="$(python3 -c 'import json;print(json.dumps({"session_id":"cksid","cwd":"'"$REPO"'","tool_name":"TaskUpdate","tool_input":{"taskId":"8","status":"completed"}}))' | bash "$HERE/task-checkpoint.sh")"
[ -z "$OUT" ]

# 5. EXTRA (Correction A): input JSON sem session_id + drift mock → output vazio (fail-open)
echo "third change" > "$REPO/test.txt"
OUT="$(python3 -c 'import json;print(json.dumps({"cwd":"'"$REPO"'","tool_name":"TaskUpdate","tool_input":{"taskId":"9","status":"completed"}}))' | bash "$HERE/task-checkpoint.sh")"
[ -z "$OUT" ]

# 6. EXTRA (sentinel collision test): taskIds "a.b" e "a/b" distintos
#    → devem gerar sentinelas diferentes na mesma sessão
cat > "$HERE/mock_ck_drift.sh" <<'EOF'
#!/usr/bin/env bash
cat >/dev/null; echo '{"verdict":"drift","reason":"nenhum diff toca o export CSV"}'
EOF
chmod +x "$HERE/mock_ck_drift.sh"
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_ck_drift.sh"

echo "another fresh change" > "$REPO/test.txt"
OUT="$(python3 -c 'import json;print(json.dumps({"session_id":"cksid","cwd":"'"$REPO"'","tool_name":"TaskUpdate","tool_input":{"taskId":"a.b","status":"completed"}}))' | bash "$HERE/task-checkpoint.sh")"
echo "$OUT" | grep -q '"decision"'  # primeira drift de "a.b" → block
echo "drift block 1 OK"

# --- teto por sessao (v0.5.0): 2 avisos por sessao, o 3o e silencio ---
# Antes so havia teto por TASK, entao cada task nova ganhava aviso limpo e a mesma
# acusacao repetia pelo resto da sessao — no relato de 30/07 a acusacao era FALSA e
# repetiu a cada task concluida. Guarda que repete acusacao falsa ensina a ignorar.
rm -f "$TMPD"/intent-guard-ckptcap-cksid "$TMPD"/intent-guard-ckptblock-cksid-*
for i in 1 2 3; do
  O="$(python3 -c 'import json,sys;print(json.dumps({"session_id":"cksid","cwd":"'"$REPO"'","tool_name":"TaskUpdate","tool_input":{"taskId":"cap'"$i"'","status":"completed"}}))' | bash "$HERE/task-checkpoint.sh")"
  if [ "$i" -le 2 ]; then
    echo "$O" | grep -q '"decision"' || { echo "FALHOU: aviso $i devia sair"; exit 1; }
  else
    [ -z "$O" ] || { echo "FALHOU: 3o aviso devia ser silencio, veio: $O"; exit 1; }
  fi
done
echo "cap por sessao OK (2 avisos, 3o silencioso)"


# mesma sessão, taskId diferente "a/b", mesmo drift mock
echo "yet another change" > "$REPO/test.txt"
rm -f "$TMPD"/intent-guard-ckptcap-cksid   # isola: este caso nao mede o teto
OUT2="$(python3 -c 'import json;print(json.dumps({"session_id":"cksid","cwd":"'"$REPO"'","tool_name":"TaskUpdate","tool_input":{"taskId":"a/b","status":"completed"}}))' | bash "$HERE/task-checkpoint.sh")"
echo "$OUT2" | grep -q '"decision"'  # segunda drift de "a/b" → block (sentinelas distintas, não colidem)
echo "drift block 2 OK (sentinelas não colidiram)"

# 7. EXTRA: plano aberto em .claude/plans/ entra no contexto do juiz (achado da
#    sessão 871f9573 — o juiz não enxergava planos aprovados e acusava drift neles)
mkdir -p "$REPO/.claude/plans"
cat > "$REPO/.claude/plans/x.plan.json" <<'EOF'
{"id":"x","title":"Plano de teste","status":"active",
 "phases":[{"id":"F1","title":"Fase em curso","items":[{"id":"F1.1","status":"todo"}]}]}
EOF
CAPTURE="$HERE/captured_judge_in.txt"
cat > "$HERE/mock_ck_capture.sh" <<EOF
#!/usr/bin/env bash
cat > "$CAPTURE"; echo '{"verdict":"ok","reason":""}'
EOF
chmod +x "$HERE/mock_ck_capture.sh"
export INTENT_GUARD_JUDGE_CMD="$HERE/mock_ck_capture.sh"
echo "plan-aware change" > "$REPO/test.txt"
python3 -c 'import json;print(json.dumps({"session_id":"cksid","cwd":"'"$REPO"'","tool_name":"TaskUpdate","tool_input":{"taskId":"plan-1","status":"completed"}}))' | bash "$HERE/task-checkpoint.sh" >/dev/null
grep -q "PLANO ABERTO" "$CAPTURE"
grep -q "Fase em curso" "$CAPTURE"
echo "plan context in judge OK"

# sem plano nenhum → "nenhum"
rm -rf "$REPO/.claude/plans"
echo "plan-free change" > "$REPO/test.txt"
python3 -c 'import json;print(json.dumps({"session_id":"cksid","cwd":"'"$REPO"'","tool_name":"TaskUpdate","tool_input":{"taskId":"plan-2","status":"completed"}}))' | bash "$HERE/task-checkpoint.sh" >/dev/null
grep -q "PLANO ABERTO.*$" "$CAPTURE" && grep -A1 "PLANO ABERTO" "$CAPTURE" | grep -q "nenhum"
echo "plan-free fallback OK"

rm -f "$HERE"/mock_ck_*.sh "$CAPTURE"
echo "test_task_checkpoint: OK"
