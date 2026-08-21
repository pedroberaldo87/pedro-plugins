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

# SEM `pipefail`, E DE PROPÓSITO. Quase toda asserção daqui é
# `printf '%s' "$out" | grep -q ...`: o `grep -q` sai no primeiro casamento e
# fecha o cano, o `printf` que ainda estava escrevendo leva SIGPIPE, e com
# `pipefail` o status da pipeline vira o do printf — a asserção reprova por ter
# ACERTADO cedo demais. Depende de quem termina primeiro, então falha ora aqui
# ora ali (medido em 2026-08-20: "e diz que bump são TRÊS arquivos" caindo com
# `write error: Broken pipe` só na segunda de três rodadas simultâneas). Quem
# responde a pergunta destas pipelines é sempre o comando da DIREITA.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
GATE="$HERE/release-gate.sh"
PASS=0; FAIL=0

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

# ── O PORTÃO AQUI NÃO TEM PRESSA ────────────────────────────────────────────
# O gate carrega um freio de relógio próprio (`PORTAO_DEADLINE`, release-gate.sh)
# para não morrer calado quando o harness o mata: passado o prazo ele PARA NO MEIO
# e recusa por não ter conseguido medir. Isso é certo em produção e é veneno numa
# bancada — com a máquina ocupada, o freio disparava no meio da rodada e derrubava
# justamente os checks do fim (medido em 2026-08-20: "função nova sem chamador" e
# "a mensagem nomeia o plano e o passo" caindo em rodadas diferentes, enquanto a
# mesma suíte sozinha fechava 68/68). O que se mede aqui é o VEREDITO do portão,
# nunca quanto ele demora; sem prazo, o resultado deixa de depender da máquina.
export PORTAO_DEADLINE_S=0

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

# ── B3 · a TABELA do catálogo em architecture.md acompanha o bump ───────────
# O defeito, medido DUAS vezes na madrugada de 2026-08-15: o bump que o próprio
# portão exige defasa a linha do plugin na tabela que architecture.md publica,
# `test_doc_catalogo_plugins.py` reprova, a esteira fica VERMELHA, e o motor do
# /sprint morre na porta de TODA rodada. O espelho eram dois arquivos e sempre
# foram três.
tabela() {
  mkdir -p "$R/.claude/docs"  # casa-ok: fixture de teste, o literal e o dado do caso
  printf 'exemplo    %s  [uma] HOOKS\n' "$1" > "$R/.claude/docs/architecture.md"  # casa-ok: fixture de teste, o literal e o dado do caso
}

desc 2.0.0 "igual" "igual"; tabela 2.0.0
git -C "$R" add -A >/dev/null; git -C "$R" commit -qm "com tabela"
printf 'y=3\n' >> "$R/plugins/exemplo/lib/mod.py"
desc 2.1.0 "igual" "igual"; tabela 2.1.0
out=$(gate_out "git commit -m x")
check "tabela em dia com o bump NÃO acusa" \
  "$(printf '%s' "$out" | grep -qc 'TABELA DO CATÁLOGO DEFASADA' >/dev/null && echo 0 || echo 1)"

printf 'z=4\n' >> "$R/plugins/exemplo/lib/mod.py"
desc 2.2.0 "igual" "igual"   # o bump sai, a tabela fica em 2.1.0
out=$(gate_out "git commit -m x")
check "tabela defasada ACUSA" \
  "$(printf '%s' "$out" | grep -q 'TABELA DO CATÁLOGO DEFASADA' && echo 1 || echo 0)"
check "a mensagem mostra os dois números, doc e disco" \
  "$(printf '%s' "$out" | grep -q 'doc=2.1.0' \
     && printf '%s' "$out" | grep -q 'disco=2.2.0' && echo 1 || echo 0)"
check "e diz que bump são TRÊS arquivos" \
  "$(printf '%s' "$out" | grep -q 'TRÊS arquivos' && echo 1 || echo 0)"

rm -f "$R/.claude/docs/architecture.md"  # casa-ok: fixture de teste, o literal e o dado do caso
printf 'w=5\n' >> "$R/plugins/exemplo/lib/mod.py"
desc 2.3.0 "igual" "igual"
out=$(gate_out "git commit -m x")
check "projeto SEM a tabela não é acusado (fail-open)" \
  "$(printf '%s' "$out" | grep -qc 'TABELA DO CATÁLOGO DEFASADA' >/dev/null && echo 0 || echo 1)"

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
check "detector saudável não entra na lista NÃO MEDIDO" \
  "$(printf '%s' "$out" | grep -q 'rodou sem medir' && echo 0 || echo 1)"

# R-27 · o detector explode por dentro: a confissão de fail-open (stderr + saída 0)
# evaporava porque o portão só lê o código de saída. Sabota o main() do detector
# REAL e cobra que a checagem apareça como não medida — e nunca como bloqueio.
cat > "$R/scripts/regua_call_check.py" <<PYEOF
import sys
sys.path.insert(0, "$HERE/../../scripts")
import regua_call_check as G
def _explode():
    raise RuntimeError("sabotagem")
G.main = _explode
sys.exit(G.cli())
PYEOF
out=$(gate_out "git commit -m x")
check "detector que explode NAO barra o commit como pagina sem regua" \
  "$(printf '%s' "$out" | grep -q 'PÁGINA SEM RÉGUA' && echo 0 || echo 1)"
check "a explosao vira linha NÃO MEDIDO no veredito (nao zero mudo)" \
  "$(printf '%s' "$out" | grep 'NÃO MEDIDO' -A 30 | grep -q 'rodou sem medir' && echo 1 || echo 0)"
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


# ── D · cache verde: mesma árvore não re-roda a suíte ───────────────────────
# O portão levava minutos e o harness o matava no teto — commit passando sem gate
# nenhum. Quem paga o tempo é a suíte dos plugins tocados, e ela é DETERMINÍSTICA
# no estado da árvore: mesma árvore, mesmo resultado. A prova aqui não é o relógio
# (que mede rápido em repo de brinquedo), é o CONTADOR: a suíte anota cada vez que
# roda, num arquivo FORA da árvore (dentro dela, o contador mudaria a chave).
echo "Check D — cache verde (tree-hash, TTL 24h)"
GC=$(mktemp -d "${TMPDIR:-/tmp}/green-suite-test.XXXXXX")
trap 'rm -rf "$R" "$GC"' EXIT
export GREEN_SUITE_DIR="$GC/registro"
CONTADOR="$GC/rodadas"
: > "$CONTADOR"
git -C "$R" rm -q -f _shared/test_quebrado.py >/dev/null 2>&1
mkdir -p "$R/_shared"
cp "$HERE/../../_shared/green-cache.sh" "$R/_shared/"
printf 'open(%s, "a").write("x\\n")\n' "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$CONTADOR")" \
  > "$R/plugins/exemplo/lib/test_conta.py"
git -C "$R" add -A >/dev/null

gate_out "git commit -m x" >/dev/null
check "1ª rodada roda a suíte do plugin tocado" \
  "$([ "$(wc -l < "$CONTADOR")" -eq 1 ] && echo 1 || echo 0)"

T0=$SECONDS
gate_out "git commit -m x" >/dev/null
T2=$(( SECONDS - T0 ))
check "2ª rodada na MESMA árvore fecha por HIT — a suíte não re-roda" \
  "$([ "$(wc -l < "$CONTADOR")" -eq 1 ] && echo 1 || echo 0)"
check "e a 2ª rodada fecha em menos de 60s (medido: ${T2}s)" \
  "$([ "$T2" -lt 60 ] && echo 1 || echo 0)"

printf 'x=9\n' >> "$R/plugins/exemplo/lib/mod.py"
git -C "$R" add -A >/dev/null
gate_out "git commit -m x" >/dev/null
check "árvore mudada invalida o HIT e re-roda tudo" \
  "$([ "$(wc -l < "$CONTADOR")" -eq 2 ] && echo 1 || echo 0)"

# suíte VERMELHA nunca grava verde: a rodada seguinte, na mesma árvore, roda de novo
printf 'import sys\nopen(%s, "a").write("x\\n")\nsys.exit(1)\n' \
  "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$CONTADOR")" \
  > "$R/plugins/exemplo/lib/test_conta.py"
git -C "$R" add -A >/dev/null
gate_out "git commit -m x" >/dev/null
gate_out "git commit -m x" >/dev/null
check "suíte vermelha não vira HIT — roda nas duas rodadas" \
  "$([ "$(wc -l < "$CONTADOR")" -eq 4 ] && echo 1 || echo 0)"

# GREEN_SUITE_DIR segue exportado até o fim: sem ele, as rodadas seguintes gravariam
# no registro real de ~/.claude/green-suite — teste não suja estado de máquina.
git -C "$R" rm -q -f plugins/exemplo/lib/test_conta.py >/dev/null 2>&1


# ── A prova da esteira: "full" pula os quatro blocos de suíte ───────────────
# scripts/suite.sh verde grava "full"; o portão, com a prova na mão, não re-mede
# (o custo real era o bloco J: 1084s de UMA das 40 suítes de scripts/, medido 2026-08-14).
# O contador prova o pulo; o GLOB VAZIO prova que o pulo é do bloco INTEIRO — o
# repo de brinquedo não tem os quatro globs, então J de pé sempre acusa vazio.
echo "A prova da esteira — full pula D, D2, F e J; árvore mudada derruba a prova"
mkdir -p "$R/scripts"
CONTJ="$GC/rodadas-j"
: > "$CONTJ"
printf '#!/bin/bash\necho x >> %s\nexit 0\n' \
  "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$CONTJ")" \
  > "$R/scripts/test_conta.sh"
git -C "$R" add -A >/dev/null

out=$(gate_out "git commit -m x")
check "sem a prova, o J roda a suíte de scripts/" \
  "$([ "$(wc -l < "$CONTJ")" -ge 1 ] && echo 1 || echo 0)"
check "e acusa GLOB VAZIO nos globs sem arquivo — o J está mesmo de pé" \
  "$(printf '%s' "$out" | grep -q 'GLOB VAZIO' && echo 1 || echo 0)"

# a esteira "fecha verde" e grava a prova — o mesmo mark que scripts/suite.sh faz
: > "$CONTJ"
( cd "$R" && . _shared/green-cache.sh && green_cache_mark "$R" full suite.sh ) >/dev/null 2>&1
out=$(gate_out "git commit -m x")
check "com a prova full, o J não roda — contador parado" \
  "$([ "$(wc -l < "$CONTJ")" -eq 0 ] && echo 1 || echo 0)"
check "e sem GLOB VAZIO — o bloco foi pulado inteiro, não remendado" \
  "$(printf '%s' "$out" | grep -q 'GLOB VAZIO' && echo 0 || echo 1)"

printf 'x=11\n' >> "$R/plugins/exemplo/lib/mod.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "árvore mudada derruba a prova e o J volta a rodar" \
  "$([ "$(wc -l < "$CONTJ")" -ge 1 ] && echo 1 || echo 0)"
git -C "$R" rm -q -f scripts/test_conta.sh >/dev/null 2>&1


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


# ── N · acoplamento NOVO entre plugins ──────────────────────────────────────
# O cobrador não tem modo --staged: ele varre o repo inteiro e compara com o retrato.
# É o retrato que separa a dívida antiga (passa) do acoplamento novo (barra) — sem ele,
# o gate nasceria reprovando o repositório inteiro e alguém o desligaria na primeira hora.
echo "Check N — acoplamento entre plugins"
mkdir -p "$R/scripts" "$R/.claude" "$R/plugins/alfa/skills/alfa" "$R/plugins/beta/lib"
cp "$HERE/../../scripts/desacoplamento_check.py" "$R/scripts/"
printf 'print("beta")\n' > "$R/plugins/beta/lib/x.py"
printf 'A divida antiga: rode plugins/beta/lib/x.py e veja.\n' \
  > "$R/plugins/alfa/skills/alfa/SKILL.md"
git -C "$R" add -A >/dev/null
( cd "$R" && python3 scripts/desacoplamento_check.py --gravar-retrato >/dev/null )

# mexer na linha JÁ retratada — reindentar e empurrá-la pra baixo — não é acoplamento novo
printf 'Um paragrafo novo no topo.\n\n   A divida antiga:  rode plugins/beta/lib/x.py e veja.\n' \
  > "$R/plugins/alfa/skills/alfa/SKILL.md"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "mexer na linha ja retratada, sem acoplamento novo, passa" \
  "$(printf '%s' "$out" | grep -q 'ACOPLAMENTO NOVO' && echo 0 || echo 1)"

# uma citação executável a MAIS, que o retrato não conhece
printf 'Um paragrafo novo no topo.\n\n   A divida antiga:  rode plugins/beta/lib/x.py e veja.\nE agora rode tambem plugins/beta/lib/x.py de outro jeito.\n' \
  > "$R/plugins/alfa/skills/alfa/SKILL.md"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "acoplamento novo entre plugins barra o commit" \
  "$(printf '%s' "$out" | grep -q 'ACOPLAMENTO NOVO' && echo 1 || echo 0)"
check "a mensagem aponta o arquivo e o irmao citado" \
  "$(printf '%s' "$out" | grep -q 'plugins/alfa/skills/alfa/SKILL.md' \
     && printf '%s' "$out" | grep -q 'dependencia-de-irmao' && echo 1 || echo 0)"
rm -rf "$R/plugins/alfa" "$R/plugins/beta" "$R/scripts/desacoplamento_check.py" \
       "$R/.claude"

# ── R-25b · caminho de doc cravado fora do resolvedor ───────────────────────
# O teto do cobrador é ABSOLUTO — e desde o F15.2 ele é ZERO no repositório de
# verdade. Para provar o caso "dívida declarada passa", o primeiro passo SIMULA um
# teto de 1 (a dívida declarada); depois o teto volta a zero e o gate barra.
echo "Check R-25b — caminho de doc cravado"
mkdir -p "$R/scripts"
cp "$HERE/../../scripts/anti_slop_inventario.py" "$HERE/../../scripts/casa_da_doc_check.py" \
   "$R/scripts/"
python3 - "$R/scripts/anti_slop_inventario.py" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(re.sub(r'"A": \d+', '"A": 1', s, count=1))
PY
rm -rf "$R/scripts/__pycache__"   # pyc do mesmo segundo esconderia o teto novo
# o caminho nasce em dois pedaços: inteiro nesta linha, ele seria o próprio defeito
printf 'abrir("%s")\n' ".claude""/docs/architecture.md" > "$R/plugins/exemplo/lib/crava.py"
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "dentro do teto, caminho cravado nao barra (divida declarada passa)" \
  "$(printf '%s' "$out" | grep -q 'CAMINHO DE DOC CRAVADO' && echo 0 || echo 1)"

python3 - "$R/scripts/anti_slop_inventario.py" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(re.sub(r'"A": \d+', '"A": 0', s, count=1))
PY
rm -rf "$R/scripts/__pycache__"   # pyc do mesmo segundo esconderia o teto novo
git -C "$R" add -A >/dev/null
out=$(gate_out "git commit -m x")
check "acima do teto, o gate barra o commit pelo cobrador do caminho" \
  "$(printf '%s' "$out" | grep -q 'CAMINHO DE DOC CRAVADO' && echo 1 || echo 0)"
check "a mensagem aponta o resolvedor unico" \
  "$(printf '%s' "$out" | grep -q '_shared/casa_da_doc.py' && echo 1 || echo 0)"
rm -f "$R/plugins/exemplo/lib/crava.py" "$R/scripts/casa_da_doc_check.py" \
      "$R/scripts/anti_slop_inventario.py"

# ── O · plano e código discordando ──────────────────────────────────────────
# O cobrador existia e nenhum portão o consultava. Aqui ele vale: um passo ABERTO
# cujo critério de pronto o disco já cumpre barra o commit. E o critério de VÁRIAS
# cláusulas — o falso-positivo do F11.9 — não pode ser julgado pela primeira.
echo "Check O — plano atrasado contra o código"
mkdir -p "$R/scripts" "$R/.claude/plans"
cp "$HERE/../../scripts/plano_vs_codigo.py" "$R/scripts/"
printf 'ja_existe = 1\n' > "$R/plugins/exemplo/lib/feito.py"
plano() {
  printf '{"id":"p","title":"p","phases":[{"id":"F1","title":"f","items":[{"id":"F1.1","title":"t","desc":"","pronto":%s,"status":"todo","evidence":null,"done_at":null}]}]}\n' \
    "$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1")" \
    > "$R/.claude/plans/teste.plan.json"
}

plano '`test -f plugins/exemplo/lib/feito.py` sai 0'
out=$(gate_out "git commit -m x")
check "passo aberto com o critério já cumprido barra o commit" \
  "$(printf '%s' "$out" | grep -q 'PLANO ATRASADO' && echo 1 || echo 0)"
check "a mensagem nomeia o plano e o passo" \
  "$(printf '%s' "$out" | grep -q 'teste.plan.json' \
     && printf '%s' "$out" | grep -q 'F1.1' && echo 1 || echo 0)"

plano '`test -f plugins/exemplo/lib/ainda_nao.py` sai 0'
out=$(gate_out "git commit -m x")
check "critério ainda por cumprir não barra" \
  "$(printf '%s' "$out" | grep -q 'PLANO ATRASADO' && echo 0 || echo 1)"

plano '`test -f plugins/exemplo/lib/feito.py` sai 0; `test -f plugins/exemplo/lib/ainda_nao.py` tambem'
out=$(gate_out "git commit -m x")
check "critério de duas cláusulas não é julgado pela primeira (o caso F11.9)" \
  "$(printf '%s' "$out" | grep -q 'PLANO ATRASADO' && echo 0 || echo 1)"

rm -rf "$R/.claude/plans" "$R/scripts/plano_vs_codigo.py" \
       "$R/plugins/exemplo/lib/feito.py"

# ── R-27 · checador ausente entra na lista NÃO MEDIDO ───────────────────────
# Cada bloco do gate só roda se o arquivo do cobrador existe: apagado ou renomeado,
# ele deixava de medir EM SILÊNCIO. Agora a ausência tem nome no veredito.
echo "R-27 — checador apagado aparece na lista NÃO MEDIDO"
mkdir -p "$R/scripts"
cp "$HERE/../../scripts/public_repo_check.py" "$R/scripts/"
out=$(gate_out "git commit -m x")
check "checador PRESENTE não entra na lista" \
  "$(printf '%s' "$out" | grep 'NÃO MEDIDO' -A 30 | grep -q 'public_repo_check.py' && echo 0 || echo 1)"
rm -f "$R/scripts/public_repo_check.py"
out=$(gate_out "git commit -m x")
check "checador APAGADO tem o nome impresso na lista NÃO MEDIDO" \
  "$(printf '%s' "$out" | grep -q 'NÃO MEDIDO' \
     && printf '%s' "$out" | grep 'NÃO MEDIDO' -A 30 | grep -q 'public_repo_check.py' && echo 1 || echo 0)"

echo
echo "Heredoc — o corpo não é comando (fricção medida 3× em 2026-08-09)"
# Um script Python colado num heredoc cujo TEXTO contém as palavras do gatilho
# bloqueava a edição inteira. O corpo sai do recorte; o comando em volta continua.
printf 'print("mudou de novo")\n' > "$R/plugins/exemplo/lib/mod.py"
CMD_HEREDOC=$(printf '%s\n' 'python3 - <<CORPO' 's = "as palavras git commit dentro do corpo"' 'CORPO')
rc=$(gate "$CMD_HEREDOC")
[ "$rc" = "0" ] && { PASS=$((PASS+1)); echo "  ok   corpo de heredoc não dispara o gatilho"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL corpo de heredoc disparou o gatilho (rc=$rc)"; }
CMD_DEPOIS=$(printf '%s\n' 'python3 - <<CORPO' 'qualquer coisa' 'CORPO' 'git commit -m "de verdade"')
rc=$(gate "$CMD_DEPOIS")
[ "$rc" = "2" ] && { PASS=$((PASS+1)); echo "  ok   o comando real DEPOIS do heredoc continua disparando"; } \
  || { FAIL=$((FAIL+1)); echo "  FAIL o comando depois do heredoc não disparou (rc=$rc)"; }
git -C "$R" checkout -q -- plugins/exemplo/lib/mod.py 2>/dev/null || true

if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"

