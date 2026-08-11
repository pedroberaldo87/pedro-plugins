#!/usr/bin/env bash
# test_hooks_capture.sh — roda os hooks com stdin JSON fake e confere o efeito.
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
REPO="$(mktemp -d "$(td_tmpdir)"/ig-cap-XXXXXX)"
git -C "$REPO" init -q
# CONFIG PROPRIO, e e isso que torna a suite segura ao lado das outras. Ela mexia
# no kill-switch do usuario, com backup e restauracao — e duas suites deste plugin
# rodando ao mesmo tempo escreviam e apagavam o MESMO arquivo: a vitima mudava a
# cada rodada, e o sintoma era uma delas morrendo em 1,5s sem relacao com o que
# testava. Backup nao resolve corrida; diretorio proprio resolve.
export CLAUDE_CONFIG_DIR="$REPO/.config-claude"
mkdir -p "$CLAUDE_CONFIG_DIR"
restore() {
  rm -rf "$REPO" "$TMPD"/intent-guard-work-testsid
}
trap restore EXIT

# O PROMPT VAI POR STDIN, NÃO POR ARGUMENTO. No Linux cada argumento isolado tem
# teto de 128 KB (MAX_ARG_STRLEN) — metade do que o caso 6 aqui embaixo manda de
# propósito. Era o próprio teste que provava "prompt grande não se perde"
# morrendo de Argument list too long, e só no Linux: o macOS aceita ~1 MB e a
# esteira ficava verde aqui e vermelha lá. O `printf` é embutido no bash, então
# não passa pela mesma porta.
mkjson() {
  printf '%s' "$3" | python3 -c 'import json,sys; print(json.dumps({"session_id":sys.argv[1],"cwd":sys.argv[2],"prompt":sys.stdin.read()}))' "$1" "$2"
}

# 1. prompt vira raw verbatim
mkjson testsid "$REPO" 'adiciona export CSV; não mexe no layout' | bash "$HERE/capture-prompt.sh" || true
grep -q 'não mexe no layout' "$REPO/.claude/intent/ledger.jsonl"

# 2. prompt vazio não grava
N1=$(wc -l < "$REPO/.claude/intent/ledger.jsonl")
mkjson testsid "$REPO" '   ' | bash "$HERE/capture-prompt.sh" || true
[ "$(wc -l < "$REPO/.claude/intent/ledger.jsonl")" = "$N1" ]

# 3. kill-switch off → não grava
mkdir -p "$CLAUDE_CONFIG_DIR/intent-guard"
echo off > "$CLAUDE_CONFIG_DIR/intent-guard/mode"
mkjson testsid "$REPO" 'outro pedido' | bash "$HERE/capture-prompt.sh" || true
[ "$(wc -l < "$REPO/.claude/intent/ledger.jsonl")" = "$N1" ]
rm -f "$CLAUDE_CONFIG_DIR/intent-guard/mode"

# 4. stdin lixo → exit 0 (fail-open)
echo 'não é json' | bash "$HERE/capture-prompt.sh" || true

# 5. mark-work: toca a sentinela por sessão
printf '%s' '{"session_id":"testsid","cwd":"'"$REPO"'"}' | bash "$HERE/mark-work.sh" || true
[ -f "$TMPD"/intent-guard-work-testsid ]

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
