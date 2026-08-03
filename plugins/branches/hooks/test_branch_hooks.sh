#!/bin/bash
# test_branch_hooks.sh — os dois hooks do /branches, com foco no SILÊNCIO.
#
# Aviso que aparece quando não devia é pior que aviso que falta: o usuário
# desliga, e aí ele não avisa nunca mais. Por isso a maioria dos casos aqui
# fixa o que os hooks NÃO podem falar.
#
# Isolamento total: cada caso monta o próprio repositório em TMPDIR, com
# identidade git própria. Nenhum projeto real é tocado.

set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SS="$HERE/sessionstart-branches.sh"
PU="$HERE/posttooluse-push-branch.sh"
PASS=0; FAIL=0

ok()    { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()   { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
check() { if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

ROOT=$(mktemp -d "${TMPDIR:-/tmp}/branch-hooks-test.XXXXXX")
trap 'rm -rf "$ROOT"; rm -f "${TMPDIR:-/tmp}"/claude-branch-ask-"$(id -u)"-t*' EXIT

novo_repo() {   # $1 = nome; ecoa o caminho
  local r="$ROOT/$1"
  mkdir -p "$r"
  git -C "$r" init -q -b main
  git -C "$r" config user.email "teste@exemplo.dev"
  git -C "$r" config user.name "Teste"
  echo inicio > "$r/README.md"
  git -C "$r" add -A >/dev/null 2>&1
  git -C "$r" commit -q -m primeiro
  printf '%s' "$r"
}
com_branch() { # $1 = repo, $2 = branch, $3 = arquivo
  git -C "$1" checkout -q -b "$2"
  echo conteudo > "$1/$3"
  git -C "$1" add -A >/dev/null 2>&1
  git -C "$1" commit -q -m "trabalho em $2"
}

ss()  { printf '{"cwd":"%s"}' "$1" | bash "$SS" 2>/dev/null; }
push() { printf '{"session_id":"%s","cwd":"%s","tool_input":{"command":"%s"}}' \
           "$2" "$1" "${3:-git push}" | bash "$PU" 2>/dev/null; }
msg()  { printf '%s' "$1" | jq -r '.systemMessage // .hookSpecificOutput.additionalContext // empty' 2>/dev/null; }

echo "SessionStart — o silêncio"
R=$(novo_repo so-tronco)
check "repo só com o tronco: cala" "$([ -z "$(ss "$R")" ] && echo 1 || echo 0)"

R=$(novo_repo recente)
com_branch "$R" feat/hoje a.txt
git -C "$R" checkout -q main
check "branch criada hoje: cala (limiar de 30 dias)" "$([ -z "$(ss "$R")" ] && echo 1 || echo 0)"

D=$(mktemp -d "$ROOT/nao-repo.XXXXXX")
check "fora de repositório git: cala" "$([ -z "$(ss "$D")" ] && echo 1 || echo 0)"

R=$(novo_repo desligado)
com_branch "$R" feat/x b.txt
git -C "$R" checkout -q main
out=$(printf '{"cwd":"%s"}' "$R" | BRANCHES_GATE=0 BRANCHES_DIAS=0 bash "$SS" 2>/dev/null)
check "BRANCHES_GATE=0: cala" "$([ -z "$out" ] && echo 1 || echo 0)"

R=$(novo_repo na-branch)
com_branch "$R" feat/atual c.txt
out=$(printf '{"cwd":"%s"}' "$R" | BRANCHES_DIAS=0 bash "$SS" 2>/dev/null)
check "não cobra a branch em que você ESTÁ" "$(printf '%s' "$(msg "$out")" | grep -q 'feat/atual' && echo 0 || echo 1)"

echo "SessionStart — quando é pra falar"
R=$(novo_repo com-parada)
com_branch "$R" feat/velha d.txt
git -C "$R" checkout -q main
out=$(printf '{"cwd":"%s"}' "$R" | BRANCHES_DIAS=0 bash "$SS" 2>/dev/null)
m=$(msg "$out")
check "avisa que há branch parada" "$(printf '%s' "$m" | grep -q 'branch(es) parada' && echo 1 || echo 0)"
check "nomeia a branch" "$(printf '%s' "$m" | grep -q 'feat/velha' && echo 1 || echo 0)"
check "aponta o /branches pro detalhe" "$(printf '%s' "$m" | grep -q '/branches' && echo 1 || echo 0)"
check "diz como desligar" "$(printf '%s' "$m" | grep -q 'BRANCHES_GATE=0' && echo 1 || echo 0)"
check "é additionalContext, não bloqueio" "$(printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName == "SessionStart"' >/dev/null 2>&1 && echo 1 || echo 0)"
check "NUNCA emite decision:block" "$(printf '%s' "$out" | grep -q '"decision"' && echo 0 || echo 1)"

echo "PostToolUse — o silêncio"
R=$(novo_repo push-repo)
com_branch "$R" feat/entregue e.txt
check "comando que não é push: cala" "$([ -z "$(push "$R" t1 'ls -la')" ] && echo 1 || echo 0)"
check "'git pushd' não conta como push" "$([ -z "$(push "$R" t1 'git pushd algo')" ] && echo 1 || echo 0)"
out=$(printf '{"session_id":"t1","cwd":"%s","tool_input":{"command":"git push"},"tool_response":{"success":false}}' "$R" | bash "$PU" 2>/dev/null)
check "push que FALHOU: cala" "$([ -z "$out" ] && echo 1 || echo 0)"
out=$(printf '{"session_id":"t2","cwd":"%s","tool_input":{"command":"git push"}}' "$R" | BRANCHES_GATE=0 bash "$PU" 2>/dev/null)
check "BRANCHES_GATE=0: cala" "$([ -z "$out" ] && echo 1 || echo 0)"

R2=$(novo_repo push-tronco)
check "push estando no tronco: cala" "$([ -z "$(push "$R2" t3)" ] && echo 1 || echo 0)"

R3=$(novo_repo push-mergeada)
com_branch "$R3" feat/ja-foi f.txt
git -C "$R3" checkout -q main
git -C "$R3" merge -q --no-ff -m merge feat/ja-foi
git -C "$R3" checkout -q feat/ja-foi
check "push em branch cujo conteúdo JÁ está no tronco: cala" "$([ -z "$(push "$R3" t4)" ] && echo 1 || echo 0)"

echo "PostToolUse — quando é pra falar"
m=$(msg "$(push "$R" t5)")
check "push em branch com trabalho: pergunta" "$(printf '%s' "$m" | grep -q 'Push feito' && echo 1 || echo 0)"
check "nomeia a branch e o tronco" "$(printf '%s' "$m" | grep -q 'feat/entregue' && printf '%s' "$m" | grep -q 'main' && echo 1 || echo 0)"
check "oferece os dois caminhos, sem decidir" "$(printf '%s' "$m" | grep -q 'Merge no main agora' && printf '%s' "$m" | grep -q 'fica aberta' && echo 1 || echo 0)"
check "pergunta 1× por (branch, sessão)" "$([ -z "$(push "$R" t5)" ] && echo 1 || echo 0)"
check "mas em OUTRA sessão pergunta de novo" "$([ -n "$(push "$R" t6)" ] && echo 1 || echo 0)"

echo "PostToolUse — a régua do canal de texto (perfil hook)"
# O canal do systemMessage é terminal, não markdown. Sem este caso, o texto volta a
# crescer em parágrafo e a ganhar `**` — foi o que aconteceu nos três emissores antes
# de 2026-08-03. Quem cobra é a MESMA régua do gerador de página, pelo perfil `hook`.
REGUA="$HERE/../lib/regua_texto.py"
# Saída vazia = passou; cada motivo recusado sai numa linha do stderr.
regua() { printf '%s\n' "$1" | python3 "$REGUA" --perfil hook --onde "aviso de push" - 2>&1 || :; }
m7=$(msg "$(push "$R" t7)")
check "a régua está vendorada no plugin (instalado, ele só enxerga a própria pasta)" "$([ -f "$REGUA" ] && echo 1 || echo 0)"
check "o aviso REAL do hook passa na régua" "$([ -z "$(regua "$m7")" ] && echo 1 || echo 0)"
check "o mesmo aviso com markdown é RECUSADO" "$(regua "$(printf '%s' "$m7" | sed 's/Push feito/**Push feito**/')" | grep -q markdown && echo 1 || echo 0)"
check "o mesmo aviso sem emoji no cabeçalho é RECUSADO" "$(regua "$(printf '%s' "$m7" | sed 's/^🌿 //')" | grep -q emoji && echo 1 || echo 0)"

echo
if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"
