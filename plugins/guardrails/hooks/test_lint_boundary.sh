#!/bin/bash
# test_lint_boundary.sh — o lint pós-edição só roda binário que mora DENTRO do projeto
# (achado 3 do scan de segurança, plano P7).
#
# O hook roda sem passar pelo prompt do Bash. Antes, ele subia a árvore até `/` atrás de
# node_modules/.bin/eslint, tsc e de um config do mypy, e executava o primeiro que achasse:
# um eslint plantado num ANCESTRAL do repo rodava, e `plugins = x.py` no mypy.ini carregava
# código do repo. Aqui os binários são FALSOS: cada um cria um marcador se (e só se) rodar.
HERE="$(cd "$(dirname "$0")" && pwd)"
H="$HERE/lint-and-typecheck.sh"
PASS=0; FAIL=0
check() { # check <nome> <esperado> <obtido>
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); printf '  ok   %s\n' "$1"
  else FAIL=$((FAIL+1)); printf '  FAIL %s — esperado %s, obtido %s\n' "$1" "$2" "$3"; fi
}

# Fora do temporário de propósito: o hook libera tudo que mora em /tmp, /var/folders e $TMPDIR.
W=$(mktemp -d "$HOME/.lint-boundary.XXXXXX")
trap 'rm -rf "$W"' EXIT
M="$W/marcas"; mkdir -p "$M"
FAKEBIN="$W/fakebin"; mkdir -p "$FAKEBIN"

fake() { # fake <caminho> <marcador> — binário que registra que rodou e reprova
  mkdir -p "$(dirname "$1")"
  printf '#!/bin/bash\ntouch "%s"\necho "erro falso"\nexit 1\n' "$2" > "$1"
  chmod +x "$1"
}
mkrepo() { mkdir -p "$1"; (cd "$1" && git init -q . && git -c user.email=lint@exemplo.invalido -c user.name=bancada commit -q --allow-empty -m x 2>/dev/null); }
roda() { # roda <arquivo> -> código de saída do hook (2 = barrou, 0 = liberou)
  printf '{"session_id":"lint-bound-%s","tool_input":{"file_path":"%s"}}' "$$" "$1" \
    | PATH="$FAKEBIN:$PATH" bash "$H" >/dev/null 2>&1
  echo $?
}
rodou() { [ -e "$M/$1" ] && echo sim || echo nao; }

# ── ESLint ────────────────────────────────────────────────────────────────
# eslint num ANCESTRAL do repo: não pode rodar.
mkdir -p "$W/fora"; fake "$W/fora/node_modules/.bin/eslint" "$M/eslint-ancestral"
mkrepo "$W/fora/proj"; echo 'var a = 1;' > "$W/fora/proj/a.js"
check "eslint de um ancestral do repo NÃO roda (exit)" 0 "$(roda "$W/fora/proj/a.js")"
check "eslint de um ancestral do repo NÃO roda (marcador)" nao "$(rodou eslint-ancestral)"

# eslint do PRÓPRIO projeto: continua rodando (é o uso normal).
mkrepo "$W/dentro"; fake "$W/dentro/node_modules/.bin/eslint" "$M/eslint-dentro"
echo 'var a = 1;' > "$W/dentro/a.js"
check "eslint do próprio projeto continua rodando (exit)" 2 "$(roda "$W/dentro/a.js")"
check "eslint do próprio projeto continua rodando (marcador)" sim "$(rodou eslint-dentro)"

# monorepo: eslint na raiz do git, arquivo num subpacote — continua achando.
mkrepo "$W/mono"; fake "$W/mono/node_modules/.bin/eslint" "$M/eslint-mono"
mkdir -p "$W/mono/pkg/src"; echo 'var a = 1;' > "$W/mono/pkg/src/a.js"
check "eslint na raiz do monorepo ainda é achado a partir do subpacote" 2 "$(roda "$W/mono/pkg/src/a.js")"

# symlink dentro do projeto que aponta pra FORA: o binário resolvido não é do projeto.
mkrepo "$W/link"; mkdir -p "$W/link/node_modules/.bin"
fake "$W/alvo-externo/eslint" "$M/eslint-symlink"
ln -s "$W/alvo-externo/eslint" "$W/link/node_modules/.bin/eslint"
echo 'var a = 1;' > "$W/link/a.js"
# No Git Bash do Windows, `ln -s` sem privilégio COPIA o arquivo: não há symlink pra testar.
# O caso é pulado COM aviso, nunca em silêncio — e só quando o link não nasceu de verdade.
if [ -L "$W/link/node_modules/.bin/eslint" ]; then
  check "eslint que é symlink pra fora do projeto NÃO roda" nao "$(roda "$W/link/a.js" >/dev/null; rodou eslint-symlink)"
else
  printf '  skip eslint que é symlink pra fora do projeto (este sistema não cria symlink com ln -s)\n'
fi

# arquivo fora de qualquer git: só o diretório do próprio arquivo vale, nunca o pai.
mkdir -p "$W/semgit/pai"; fake "$W/semgit/node_modules/.bin/eslint" "$M/eslint-semgit"
echo 'var a = 1;' > "$W/semgit/pai/a.js"
check "sem git: eslint do diretório pai NÃO roda" nao "$(roda "$W/semgit/pai/a.js" >/dev/null; rodou eslint-semgit)"

# ── tsc ───────────────────────────────────────────────────────────────────
mkdir -p "$W/tsfora"; fake "$W/tsfora/node_modules/.bin/tsc" "$M/tsc-ancestral"
mkrepo "$W/tsfora/proj"; echo '{}' > "$W/tsfora/proj/tsconfig.json"; echo 'export const a = 1;' > "$W/tsfora/proj/a.ts"
check "tsc de um ancestral do repo NÃO roda" nao "$(roda "$W/tsfora/proj/a.ts" >/dev/null; rodou tsc-ancestral)"

mkrepo "$W/tsdentro"; fake "$W/tsdentro/node_modules/.bin/tsc" "$M/tsc-dentro"
echo '{}' > "$W/tsdentro/tsconfig.json"; echo 'export const a = 1;' > "$W/tsdentro/a.ts"
check "tsc do próprio projeto continua rodando" 2 "$(roda "$W/tsdentro/a.ts")"

# ── mypy ──────────────────────────────────────────────────────────────────
fake "$FAKEBIN/mypy" "$M/mypy"
# plugin declarado no config: carregar código do repo → o hook não roda mypy.
mkrepo "$W/pyplug"; printf '[mypy]\nplugins = evil_plugin.py\n' > "$W/pyplug/mypy.ini"
echo 'x = 1' > "$W/pyplug/a.py"
rm -f "$M/mypy"; roda "$W/pyplug/a.py" >/dev/null
check "mypy.ini com plugins= NÃO dispara o mypy" nao "$(rodou mypy)"

mkrepo "$W/pyplug2"; printf '[tool.mypy]\nplugins = ["evil_plugin"]\n' > "$W/pyplug2/pyproject.toml"
echo 'x = 1' > "$W/pyplug2/a.py"
rm -f "$M/mypy"; roda "$W/pyplug2/a.py" >/dev/null
check "pyproject [tool.mypy] com plugins NÃO dispara o mypy" nao "$(rodou mypy)"

# controle: config do mypy SEM plugin continua rodando.
mkrepo "$W/pyok"; printf '[mypy]\nstrict = True\n' > "$W/pyok/mypy.ini"
echo 'x = 1' > "$W/pyok/a.py"
rm -f "$M/mypy"
check "mypy.ini sem plugin continua rodando (exit)" 2 "$(roda "$W/pyok/a.py")"
check "mypy.ini sem plugin continua rodando (marcador)" sim "$(rodou mypy)"

# config do mypy num ANCESTRAL do repo (fora do git): não vale como config do projeto.
mkdir -p "$W/pyfora"; printf '[mypy]\nstrict = True\n' > "$W/pyfora/mypy.ini"
mkrepo "$W/pyfora/proj"; echo 'x = 1' > "$W/pyfora/proj/a.py"
rm -f "$M/mypy"; roda "$W/pyfora/proj/a.py" >/dev/null
check "config do mypy acima da raiz do git NÃO conta" nao "$(rodou mypy)"

echo ""
[ "$FAIL" -eq 0 ] && { echo "OK ($PASS checks)"; exit 0; }
echo "FALHOU ($FAIL de $((PASS+FAIL)))"; exit 1
