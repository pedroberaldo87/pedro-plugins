#!/usr/bin/env bash
# test_hooks_capture.sh — roda os hooks com stdin JSON fake e confere o efeito.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export CLAUDE_PLUGIN_ROOT="$(dirname "$HERE")"
REPO="$(mktemp -d /tmp/ig-cap-XXXXXX)"
git -C "$REPO" init -q
# preserva um kill-switch real do usuário, se existir
MODE_BAK=""
[ -f ~/.claude/intent-guard/mode ] && MODE_BAK="$(cat ~/.claude/intent-guard/mode)"
restore() {
  rm -rf "$REPO" /tmp/intent-guard-work-testsid
  if [ -n "$MODE_BAK" ]; then echo "$MODE_BAK" > ~/.claude/intent-guard/mode; else rm -f ~/.claude/intent-guard/mode; fi
}
trap restore EXIT

mkjson() { python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"prompt":sys.argv[3]}))' "$@"; }

# 1. prompt vira raw verbatim
mkjson testsid "$REPO" 'adiciona export CSV; não mexe no layout' | bash "$HERE/capture-prompt.sh" || true
grep -q 'não mexe no layout' "$REPO/.claude/intent/ledger.jsonl"

# 2. prompt vazio não grava
N1=$(wc -l < "$REPO/.claude/intent/ledger.jsonl")
mkjson testsid "$REPO" '   ' | bash "$HERE/capture-prompt.sh" || true
[ "$(wc -l < "$REPO/.claude/intent/ledger.jsonl")" = "$N1" ]

# 3. kill-switch off → não grava
mkdir -p ~/.claude/intent-guard
echo off > ~/.claude/intent-guard/mode
mkjson testsid "$REPO" 'outro pedido' | bash "$HERE/capture-prompt.sh" || true
[ "$(wc -l < "$REPO/.claude/intent/ledger.jsonl")" = "$N1" ]
rm -f ~/.claude/intent-guard/mode

# 4. stdin lixo → exit 0 (fail-open)
echo 'não é json' | bash "$HERE/capture-prompt.sh" || true

# 5. mark-work: toca a sentinela por sessão
printf '%s' '{"session_id":"testsid","cwd":"'"$REPO"'"}' | bash "$HERE/mark-work.sh" || true
[ -f /tmp/intent-guard-work-testsid ]

# 6. large prompt (~500KB): não perde via E2BIG
LARGE_PROMPT=$(python3 -c 'print("x" * 500000)')
mkjson testsid "$REPO" "$LARGE_PROMPT" | bash "$HERE/capture-prompt.sh" || true
LAST_LEN=$(python3 -c "
import json
with open('$REPO/.claude/intent/ledger.jsonl') as f:
    last = f.readlines()[-1]
    obj = json.loads(last)
    print(len(obj.get('text', '')))
")
[ "$LAST_LEN" = "500000" ]

# 7. REGRESSÃO (smoke E2E 2026-07-24): os gates chamam `claude -p` como juiz, e
# essa sub-invocação dispara ESTE hook com o prompt do juiz. Sem o guard de
# reentrância o caderno do usuário se enche dos prompts internos do próprio plugin.
N_BEFORE=$(wc -l < "$REPO/.claude/intent/ledger.jsonl")
mkjson testsid "$REPO" 'CADERNO — vivos e crus: [prompt interno do juiz]' \
  | INTENT_GUARD_INTERNAL=1 bash "$HERE/capture-prompt.sh"
[ "$(wc -l < "$REPO/.claude/intent/ledger.jsonl")" = "$N_BEFORE" ] || { echo "FALHA: prompt interno do juiz entrou no caderno"; exit 1; }
# e sem a var, o mesmo prompt É gravado (prova que o teste não passa por acidente)
mkjson testsid "$REPO" 'CADERNO — vivos e crus: [prompt interno do juiz]' | bash "$HERE/capture-prompt.sh"
[ "$(wc -l < "$REPO/.claude/intent/ledger.jsonl")" -gt "$N_BEFORE" ] || { echo "FALHA: guard bloqueou prompt legítimo"; exit 1; }

echo "test_hooks_capture: OK"
