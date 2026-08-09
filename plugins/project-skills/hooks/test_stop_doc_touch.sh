#!/bin/bash
# test_stop_doc_touch.sh — a sugestão do fim de turno, e a FORMA dela.
#
# O hook fala num systemMessage, que sai num terminal e não num renderizador de
# markdown: `**` chega literal na tela e uma linha de 177 caracteres com a lista
# de docs no meio não se lê no fim de um turno. Quem cobra isso é a MESMA régua
# do gerador de página (`lib/regua_texto.py`), pelo perfil `hook`.
#
# Isolamento total: projeto falso em mktemp, com git próprio. Nenhum projeto real
# é tocado, e o sentinel de sessão é podado no trap.

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$HERE/stop-doc-touch.sh"
REGUA="$HERE/../lib/regua_texto.py"
PASS=0; FAIL=0

ok()    { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()   { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
check() { if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

ROOT=$(mktemp -d "${TMPDIR:-/tmp}/doc-touch-test.XXXXXX")
SESS="dt-$$"
trap 'rm -rf "$ROOT"; rm -f "${TMPDIR:-/tmp}"/claude-doc-touch-"$(id -u)"-"$SESS"-*' EXIT

# Cache falso de plugin: o nome de invocação da rodada se DESCOBRE (resolve-skill.sh),
# e a suíte não pode depender do que ESTA máquina tem instalado.
FAKE="$ROOT/cfg/plugins/cache/mkt/project-skills/1.0.0"
mkdir -p "$FAKE/lib" "$FAKE/skills/doc" "$FAKE/skills/doc-touch"
# ...e o IRMÃO de onde ela vem também se acha por NOME (Artigo 9), nunca por posição.
RS_SRC=$(CLAUDE_PLUGIN_ROOT="$HERE/.." "$HERE/resolve-plugin.sh" \
           project-skills lib/resolve-skill.sh) || {
  printf 'SKIP: project-skills não está nesta máquina\n'; exit 0; }
cp "$RS_SRC" "$FAKE/lib/"
: > "$FAKE/skills/doc/SKILL.md"; : > "$FAKE/skills/doc-touch/SKILL.md"
unset CLAUDE_PLUGIN_ROOT
export CLAUDE_CONFIG_DIR="$ROOT/cfg"

# Projeto com doc project-doc cujo `scope:` cobre dois arquivos JÁ COMMITADOS e
# depois modificados — é assim que o `touch_plan` enxerga trabalho pendente.
PROJ="$ROOT/proj"
mkdir -p "$PROJ/lib" "$PROJ/.claude/docs"
git -C "$PROJ" init -q -b main
git -C "$PROJ" config user.email "teste@exemplo.dev"
git -C "$PROJ" config user.name "Teste"
printf 'a = 1\n' > "$PROJ/lib/a.py"
printf 'b = 1\n' > "$PROJ/lib/b.py"
cat > "$PROJ/.claude/docs/architecture.md" <<'DOC'
---
generated: 2026-01-01
project: proj
scope: lib/a.py, lib/b.py
---
# Arquitetura
DOC
git -C "$PROJ" add -A >/dev/null 2>&1
git -C "$PROJ" commit -q -m inicio
# O doc precisa ser MAIS VELHO que os arquivos, senão o plano o dá por já tocado.
touch -t 202601010000 "$PROJ/.claude/docs/architecture.md"
printf 'a = 2\n' > "$PROJ/lib/a.py"
printf 'b = 2\n' > "$PROJ/lib/b.py"

run() { # $1 = session_id → stdout cru do hook
  printf '{"session_id":"%s","cwd":"%s"}' "$1" "$PROJ" | bash "$HOOK" 2>/dev/null
}
msg() { printf '%s' "$1" | jq -r '.systemMessage // empty' 2>/dev/null; }

echo "a sugestão — quando é pra falar"
OUT=$(run "$SESS")
M=$(msg "$OUT")
check "sessão com 2 arquivos cobertos por doc: sugere" "$(printf '%s' "$M" | grep -q 'doc-touch' && echo 1 || echo 0)"
check "diz quantos arquivos e quantas docs" "$(printf '%s' "$M" | grep -q '2 arquivo(s) tocados, cobertos por 1 doc(s)' && echo 1 || echo 0)"
check "nomeia a doc afetada" "$(printf '%s' "$M" | grep -q 'architecture.md' && echo 1 || echo 0)"
check "NUNCA emite decision:block" "$(printf '%s' "$OUT" | grep -q '"decision"' && echo 0 || echo 1)"
check "sugere 1× por (sessão, projeto)" "$([ -z "$(run "$SESS")" ] && echo 1 || echo 0)"

echo "a rodada é medida, não perguntada — os dois desfechos"
# O doc do fixture é de 2026-01-01: atraso muito acima do teto de 30 dias.
check "doc velha: manda a rodada COMPLETA, com o plugin descoberto" "$(printf '%s' "$M" | grep -q '/project-skills:doc pra atualizar' && echo 1 || echo 0)"
check "doc velha: não escreve o nome de skill que não existe" "$(printf '%s' "$M" | grep -qE '/project-doc|/start-doc' && echo 0 || echo 1)"
check "doc velha: mostra o número que sustentou a escolha" "$(printf '%s' "$M" | grep -qE 'tem [0-9]+ dias' && echo 1 || echo 0)"
check "doc velha: não manda o dono escolher entre as duas" "$(printf '%s' "$M" | grep -q ':doc-touch' && echo 0 || echo 1)"
# Sem resolvedor na máquina, a sugestão ainda NOMEIA a rodada — só sem o prefixo.
MF=$(msg "$(CLAUDE_CONFIG_DIR="$ROOT/vazio" run "$SESS-semcache")")
check "sem resolvedor: cai no nome cru da skill" "$(printf '%s' "$MF" | grep -q '/doc pra atualizar' && echo 1 || echo 0)"
# Mesma sessão de trabalho, doc carimbada HOJE: o atraso cabe no incremental.
sed -i.bak "s/^generated: .*/generated: $(date +%Y-%m-%d)/" "$PROJ/.claude/docs/architecture.md"
rm -f "$PROJ/.claude/docs/architecture.md.bak"
touch -t 202601010000 "$PROJ/.claude/docs/architecture.md"
M2=$(msg "$(run "$SESS-nova")")
check "doc de hoje: manda a rodada CURTA, com o plugin descoberto" "$(printf '%s' "$M2" | grep -q '/project-skills:doc-touch' && echo 1 || echo 0)"
check "doc de hoje: mostra o número que sustentou a escolha" "$(printf '%s' "$M2" | grep -qE 'tem [0-9]+ dias' && echo 1 || echo 0)"
check "doc de hoje: a sugestão medida passa na régua" "$([ -z "$(printf '%s\n' "$M2" | python3 "$REGUA" --perfil hook --onde "sugestão de doc-touch" - 2>&1)" ] && echo 1 || echo 0)"

echo "a sugestão — o silêncio"
check "DOC_TOUCH_SUGGEST=0: cala" "$([ -z "$(printf '{"session_id":"%s-off","cwd":"%s"}' "$SESS" "$PROJ" | DOC_TOUCH_SUGGEST=0 bash "$HOOK" 2>/dev/null)" ] && echo 1 || echo 0)"
VAZIO="$ROOT/sem-doc"; mkdir -p "$VAZIO"
check "projeto sem .claude/docs: cala" "$([ -z "$(printf '{"session_id":"%s-x","cwd":"%s"}' "$SESS" "$VAZIO" | bash "$HOOK" 2>/dev/null)" ] && echo 1 || echo 0)"

echo "a régua do canal de texto (perfil hook)"
# Saída vazia = passou; cada motivo recusado sai numa linha do stderr.
regua() { printf '%s\n' "$1" | python3 "$REGUA" --perfil hook --onde "sugestão de doc-touch" - 2>&1 || :; }
check "a régua está vendorada no plugin (instalado, ele só enxerga a própria pasta)" "$([ -f "$REGUA" ] && echo 1 || echo 0)"
check "a sugestão REAL do hook passa na régua" "$([ -z "$(regua "$M")" ] && echo 1 || echo 0)"
check "a mesma sugestão com markdown é RECUSADA" "$(regua "$(printf '%s' "$M" | sed 's/doc-touch:/**doc-touch:**/')" | grep -q markdown && echo 1 || echo 0)"
check "a mesma sugestão sem emoji no cabeçalho é RECUSADA" "$(regua "$(printf '%s' "$M" | sed 's/^📝 //')" | grep -q emoji && echo 1 || echo 0)"

echo
if [ "$FAIL" -gt 0 ]; then echo "FALHOU: $FAIL de $((PASS+FAIL))"; exit 1; fi
echo "OK ($PASS checks)"
