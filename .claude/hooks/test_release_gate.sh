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

# devolve o TEXTO que o gate imprime (o `gate` acima só dá o rc)
gate_out() {
  ( cd "$R" || exit 0
    printf '{"tool_input":{"command":%s}}' \
      "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1")" \
      | bash "$GATE" 2>&1 )
}

# ── B2 · description divergente entre plugin.json e marketplace.json ────────
# O erro que originou (2026-08-02): quatro descriptions foram reescritas SÓ no
# marketplace.json, e `claude plugin details` mostra a do plugin.json. A vitrine
# nova nunca chegaria a quem instala, e nada acusava.
desc() {
  printf '{"name":"exemplo","version":"%s","description":"%s"}\n' "$1" "$2" \
    > "$R/plugins/exemplo/.claude-plugin/plugin.json"
  printf '{"plugins":[{"name":"exemplo","version":"%s","source":"./plugins/exemplo","description":"%s"}]}\n' "$1" "$3" \
    > "$R/.claude-plugin/marketplace.json"
}

desc 1.0.0 "mesma coisa nos dois" "mesma coisa nos dois"
git -C "$R" add -A >/dev/null; git -C "$R" commit -qm "com description"
printf 'x=2\n' >> "$R/plugins/exemplo/lib/mod.py"
desc 1.1.0 "mesma coisa nos dois" "mesma coisa nos dois"
out=$(gate_out "git commit -m x")
check "description igual nos dois NÃO acusa" \
  "$(printf '%s' "$out" | grep -qc 'DESCRIPTION DIVERGENTE' >/dev/null && echo 0 || echo 1)"

desc 1.2.0 "o que o details mostra" "o que a listagem mostra"
out=$(gate_out "git commit -m x")
check "description divergente ACUSA" \
  "$(printf '%s' "$out" | grep -q 'DESCRIPTION DIVERGENTE' && echo 1 || echo 0)"
check "a mensagem mostra os DOIS textos, pra dar pra escolher" \
  "$(printf '%s' "$out" | grep -q 'o que o details mostra' \
     && printf '%s' "$out" | grep -q 'o que a listagem mostra' && echo 1 || echo 0)"
check "e explica que as duas sao lidas" \
  "$(printf '%s' "$out" | grep -q 'As duas sao lidas' && echo 1 || echo 0)"

# divida antiga nao trava trabalho alheio: o gate so olha o plugin TOCADO
mkdir -p "$R/plugins/outro/.claude-plugin"
printf '{"name":"outro","version":"1.0.0","description":"A"}\n' > "$R/plugins/outro/.claude-plugin/plugin.json"
desc 1.3.0 "igual" "igual"
python3 - "$R" <<'PYEOF'
import json, sys
m = sys.argv[1] + "/.claude-plugin/marketplace.json"
d = json.load(open(m))
d["plugins"].append({"name": "outro", "version": "1.0.0", "source": "./plugins/outro",
                     "description": "B — divergente de proposito"})
json.dump(d, open(m, "w"))
PYEOF
out=$(gate_out "git commit -m x")
check "plugin NAO tocado com description divergente nao trava o commit" \
  "$(printf '%s' "$out" | grep -q 'outro' && echo 0 || echo 1)"


# ── I · gerador de página que não chama a régua de estilo ───────────────────
# O detector mora em scripts/regua_call_check.py e se localiza pela própria pasta,
# então basta copiá-lo pro repo descartável pra ele varrer o staged DE LÁ.
echo "Check I — gerador de HTML sem a régua"
mkdir -p "$R/scripts"
cp "$HERE/../../scripts/regua_call_check.py" "$R/scripts/"
DOCTYPE="<!DOC""TYPE html>"
printf 'def pagina(t):\n    return "%s" + t\n' "$DOCTYPE" > "$R/plugins/exemplo/lib/gerador.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "gerador de mentira SEM a chamada e barrado" \
  "$(printf '%s' "$out" | grep -q 'PÁGINA SEM RÉGUA' && echo 1 || echo 0)"
check "a mensagem aponta o arquivo e o sinal" \
  "$(printf '%s' "$out" | grep -q 'gerador.py' \
     && printf '%s' "$out" | grep -q 'doctype' && echo 1 || echo 0)"

printf 'from regua_texto import erros_de_estilo\n\ndef pagina(t):\n    assert not erros_de_estilo(t, "t", "pagina")\n    return "%s" + t\n' \
  "$DOCTYPE" > "$R/plugins/exemplo/lib/gerador.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "o mesmo gerador COM a chamada passa" \
  "$(printf '%s' "$out" | grep -q 'PÁGINA SEM RÉGUA' && echo 0 || echo 1)"

# divida antiga nao trava trabalho alheio: o check so olha o que ESTE commit traz
printf 'def velho(t):\n    return "%s" + t\n' "$DOCTYPE" > "$R/plugins/exemplo/lib/velho.py"
out=$(gate_out "git commit -m x")
check "gerador antigo FORA do commit nao trava" \
  "$(printf '%s' "$out" | grep -q 'velho.py' && echo 0 || echo 1)"
rm -f "$R/plugins/exemplo/lib/velho.py" "$R/plugins/exemplo/lib/gerador.py" "$R/scripts/regua_call_check.py"


# ── D2 · a suíte de _shared/ roda no commit ─────────────────────────────────
# O check D varre plugins/<nome>/lib/test_*.py e o F varre plugins/<nome>/hooks/test_*.sh.
# _shared/test_*.py não casa com nenhum dos dois globs, então a suíte que DEFINE o
# comportamento do código compartilhado dependia de alguém lembrar de rodá-la à mão.
echo "Check D2 — a suíte de _shared/"
mkdir -p "$R/_shared"
printf 'import sys\nprint("a régua deixou passar")\nsys.exit(1)\n' > "$R/_shared/test_quebrado.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "suíte vermelha em _shared/ barra o commit" \
  "$(printf '%s' "$out" | grep -q 'test_quebrado.py' && echo 1 || echo 0)"
check "e a mensagem traz a saída real do teste" \
  "$(printf '%s' "$out" | grep -q 'a régua deixou passar' && echo 1 || echo 0)"

printf 'import sys\nsys.exit(0)\n' > "$R/_shared/test_quebrado.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "a mesma suíte verde não barra" \
  "$(printf '%s' "$out" | grep -q 'test_quebrado.py' && echo 0 || echo 1)"

# commit que NÃO toca _shared/ não paga o custo (mesma regra dos checks D, E e I)
printf 'import sys\nsys.exit(1)\n' > "$R/_shared/test_quebrado.py"
git -C "$R" add -A >/dev/null
git -C "$R" commit -qm "suite vermelha ja no HEAD"
printf 'x=3\n' >> "$R/plugins/exemplo/lib/mod.py"
out=$(gate_out "git commit -m x")
check "_shared/ intocado pelo commit não é varrido" \
  "$(printf '%s' "$out" | grep -q 'test_quebrado.py' && echo 0 || echo 1)"


# ── L · função nova que ninguém chama ───────────────────────────────────────
# De quatro passos reprovados numa rodada, três tinham código bom que caminho nenhum
# invocava. Peça que não roda não deixa suíte vermelha — sem este check, nada acusa.
echo "Check L — peça escrita que ninguém chama"
mkdir -p "$R/scripts"
cp "$HERE/../../scripts/fiscal_de_bancada.py" "$R/scripts/"
printf 'def peca_que_ninguem_invoca():\n    return 1\n' > "$R/plugins/exemplo/lib/peca.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "funcao nova sem chamador barra o commit" \
  "$(printf '%s' "$out" | grep -q 'PEÇA SEM CHAMADOR' && echo 1 || echo 0)"
check "a mensagem aponta o arquivo e a funcao" \
  "$(printf '%s' "$out" | grep -q 'peca.py' \
     && printf '%s' "$out" | grep -q 'peca_que_ninguem_invoca' && echo 1 || echo 0)"

printf 'from peca import peca_que_ninguem_invoca\n\nprint(peca_que_ninguem_invoca())\n' \
  > "$R/plugins/exemplo/lib/consumidor.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "a mesma peca LIGADA a um chamador passa" \
  "$(printf '%s' "$out" | grep -q 'PEÇA SEM CHAMADOR' && echo 0 || echo 1)"
rm -f "$R/plugins/exemplo/lib/peca.py" "$R/plugins/exemplo/lib/consumidor.py"


# ── M · aviso escrito no canal que todo consumidor joga fora ────────────────
# O defeito real: a recusa da reserva de arquivos saía pelo canal de erro, e os
# caminhos que chamavam o script fechavam a chamada com `2>/dev/null`. O aviso
# existia, tinha teste, e não chegava a ninguém — nada ficava vermelho por isso.
echo "Check M — aviso no canal que ninguém lê"
printf 'echo "a reserva recusou" >&2\n' > "$R/plugins/exemplo/lib/avisador.sh"
printf 'bash plugins/exemplo/lib/avisador.sh 2>/dev/null\n' > "$R/plugins/exemplo/lib/chama.sh"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "aviso cujo unico consumidor descarta o canal barra o commit" \
  "$(printf '%s' "$out" | grep -q 'AVISO NO VAZIO' && echo 1 || echo 0)"
check "a mensagem aponta o arquivo que avisa no vazio" \
  "$(printf '%s' "$out" | grep -q 'avisador.sh' && echo 1 || echo 0)"

# basta UM consumidor que não descarta: o aviso volta a existir
printf 'bash plugins/exemplo/lib/avisador.sh\n' >> "$R/plugins/exemplo/lib/chama.sh"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "o mesmo aviso com um consumidor que escuta passa" \
  "$(printf '%s' "$out" | grep -q 'AVISO NO VAZIO' && echo 0 || echo 1)"
rm -f "$R/plugins/exemplo/lib/avisador.sh" "$R/plugins/exemplo/lib/chama.sh" \
      "$R/scripts/fiscal_de_bancada.py"

echo
if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"
