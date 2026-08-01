#!/bin/bash
# test_release_gate.sh — o release-gate só vale se ele RODAR.
#
# O gate lê o texto do comando pra decidir se age. Enquanto o gatilho era ancorado
# em início-de-linha, quatro formas correntes de commit (`env … git commit`,
# `(git commit …)`, `bash -c "git commit …"`, `VAR=x git commit`) saíam calados e
# levavam junto os oito checks — 7 de 9 commits de uma rodada foram assim.
# Este teste exercita o GATILHO (dispara / não dispara) e o caso `--amend`, que
# acusava bump esquecido de uma version que já estava dentro do commit emendado.
#
# Monta um repo git descartável em TMPDIR, com a mesma forma do monorepo.
# Uso: bash test_release_gate.sh

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/release-gate.sh"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

R=$(mktemp -d "${TMPDIR:-/tmp}/release-gate-test.XXXXXX")
trap 'rm -rf "$R"' EXIT

# repo mínimo com a forma que o gate exige: marketplace.json na raiz + um plugin.
# Sem scripts/ nem hooks/ — assim só os checks B e C entram em cena.
mkdir -p "$R/.claude-plugin" "$R/plugins/exemplo/.claude-plugin" "$R/plugins/exemplo/lib"
ver() {
  printf '{"name":"exemplo","version":"%s"}\n' "$1" > "$R/plugins/exemplo/.claude-plugin/plugin.json"
  printf '{"plugins":[{"name":"exemplo","version":"%s","source":"./plugins/exemplo"}]}\n' "$1" \
    > "$R/.claude-plugin/marketplace.json"
}
ver 1.0.0
printf 'print("oi")\n' > "$R/plugins/exemplo/lib/mod.py"
git -C "$R" init -q
git -C "$R" config user.email t@t.t
git -C "$R" config user.name t
git -C "$R" add -A >/dev/null
git -C "$R" commit -qm base

# roda o gate como PreToolUse, de dentro do repo descartável; devolve o rc
gate() {
  ( cd "$R" || exit 0
    printf '{"tool_input":{"command":%s}}' \
      "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1")" \
      | bash "$GATE" >/dev/null 2>&1 )
  printf '%s' "$?"
}

echo "Gatilho — as formas que TÊM que acordar o gate"
# estado que viola o check C: plugin tocado e version igual à do HEAD
printf 'print("mudou")\n' > "$R/plugins/exemplo/lib/mod.py"
for cmd in \
  'git commit -m "x"' \
  'git add -A && git commit -m "x"' \
  'env FOO=1 git commit -m "x"' \
  '(git commit -m "x")' \
  'bash -c "git commit -m x"' \
  'GIT_AUTHOR_NAME=x git commit -m y' \
  'git -c user.name=x commit -m y' \
  'git commit -am "x"'
do
  check "dispara em: $cmd" "$([ "$(gate "$cmd")" = "2" ] && echo 1 || echo 0)"
done

echo "Gatilho — o que NÃO pode acordar o gate (falso positivo ensina a contornar)"
for cmd in 'git log --grep commit' 'git status' 'git show HEAD --stat' \
           'echo eu falo de commit' 'ls'
do
  check "cala em: $cmd" "$([ "$(gate "$cmd")" = "0" ] && echo 1 || echo 0)"
done

echo "Check C — --amend compara com HEAD~1, não com o commit que está sendo reescrito"
# commit honesto: sobe a version junto com o código
ver 1.0.1
git -C "$R" add -A >/dev/null
git -C "$R" commit -qm "muda o mod e sobe pra 1.0.1"
# agora uma correção a mais, pra entrar no MESMO commit por amend
printf 'print("mudou de novo")\n' > "$R/plugins/exemplo/lib/mod.py"
check "amend não acusa bump de uma version que já está no commit emendado" \
      "$([ "$(gate 'git commit --amend --no-edit')" = "0" ] && echo 1 || echo 0)"
check "mas um commit NOVO com a mesma version segue acusado" \
      "$([ "$(gate 'git commit -m "outra coisa"')" = "2" ] && echo 1 || echo 0)"
check "--amend dentro da MENSAGEM é texto, não amend" \
      "$([ "$(gate 'git commit -m "conserta o --amend do gate"')" = "2" ] && echo 1 || echo 0)"

echo "Fora do monorepo, o gate não opina"
O=$(mktemp -d "${TMPDIR:-/tmp}/outro-repo.XXXXXX")
git -C "$O" init -q
rc=$( cd "$O" && printf '{"tool_input":{"command":"git commit -m x"}}' | bash "$GATE" >/dev/null 2>&1; printf '%s' "$?" )
rm -rf "$O"
check "sem marketplace.json na raiz, sai 0" "$([ "$rc" = "0" ] && echo 1 || echo 0)"

echo
if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"
