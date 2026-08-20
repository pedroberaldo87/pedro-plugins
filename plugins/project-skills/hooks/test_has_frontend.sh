#!/usr/bin/env bash
# test_has_frontend.sh — cobre lib-has-frontend.sh (achado F2.2 do plano
# design-como-doc-autoral: design.md só cobra quem tem interface).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$(cd "$(dirname "$0")" && pwd)/lib-tmpdir.sh"
. "$HERE/lib-has-frontend.sh"

# O temporário vem de `td_tmpdir`, nunca de `/tmp` cravado: no Git Bash do
# Windows `/tmp` é caminho do SHELL, e o `ledger.py`/`python3` que recebe esse
# `cwd` é o Python nativo — ele resolve `/tmp/x` como `C:\tmp\x`, que não
# existe. O ledger nascia noutro lugar e o `grep` do teste não achava nada.
BACKEND="$(mktemp -d "$(td_tmpdir)"/hf-backend-XXXXXX)"
FRONT_TSX="$(mktemp -d "$(td_tmpdir)"/hf-tsx-XXXXXX)"
FRONT_HTML="$(mktemp -d "$(td_tmpdir)"/hf-html-XXXXXX)"
FRONT_PKG="$(mktemp -d "$(td_tmpdir)"/hf-pkg-XXXXXX)"
trap 'rm -rf "$BACKEND" "$FRONT_TSX" "$FRONT_HTML" "$FRONT_PKG"' EXIT

# 1. backend puro (só .py) → não tem interface
git -C "$BACKEND" init -q
echo "print(1)" > "$BACKEND/main.py"
git -C "$BACKEND" add -A && git -C "$BACKEND" -c user.email=t@t -c user.name=t commit -qm i
! has_frontend "$BACKEND"
echo "1. backend puro: sem interface OK"

# 2. .tsx versionado → tem interface
git -C "$FRONT_TSX" init -q
echo "export default 1" > "$FRONT_TSX/App.tsx"
git -C "$FRONT_TSX" add -A && git -C "$FRONT_TSX" -c user.email=t@t -c user.name=t commit -qm i
has_frontend "$FRONT_TSX"
echo "2. .tsx: tem interface OK"

# 3. index.html versionado → tem interface
git -C "$FRONT_HTML" init -q
echo "<html></html>" > "$FRONT_HTML/index.html"
git -C "$FRONT_HTML" add -A && git -C "$FRONT_HTML" -c user.email=t@t -c user.name=t commit -qm i
has_frontend "$FRONT_HTML"
echo "3. index.html: tem interface OK"

# 4. package.json com react (mesmo sem arquivo .tsx ainda) → tem interface
mkdir -p "$FRONT_PKG"
printf '{"dependencies":{"react":"^18.0.0"}}' > "$FRONT_PKG/package.json"
has_frontend "$FRONT_PKG"
echo "4. package.json com react: tem interface OK"

# 5. dir inexistente → não trava, retorna sem interface
! has_frontend "/tmp/nao-existe-hf-XXXXX"
echo "5. dir inexistente: fail-safe OK"

# 6. protótipo rastreado em .claude/docs/prototipo NÃO flipa o detector (F13.3):  # casa-ok: fixture de teste, o literal e o dado do caso
#    é documentação da interface, não a interface — backend com protótipo segue backend.
PROTO="$(mktemp -d "$(td_tmpdir)"/hf-proto-XXXXXX)"
trap 'rm -rf "$BACKEND" "$FRONT_TSX" "$FRONT_HTML" "$FRONT_PKG" "$PROTO"' EXIT
git -C "$PROTO" init -q
echo "print(1)" > "$PROTO/main.py"
mkdir -p "$PROTO/.claude/docs/prototipo"  # casa-ok: fixture de teste, o literal e o dado do caso
echo "<html></html>" > "$PROTO/.claude/docs/prototipo/index.html"  # casa-ok: fixture de teste, o literal e o dado do caso
echo "export default 1" > "$PROTO/.claude/docs/prototipo/App.tsx"  # casa-ok: fixture de teste, o literal e o dado do caso
git -C "$PROTO" add -A -f && git -C "$PROTO" -c user.email=t@t -c user.name=t commit -qm i
! has_frontend "$PROTO"
echo "6. protótipo em .claude/docs: sem interface OK"  # casa-ok: fixture de teste, o literal e o dado do caso

echo "test_has_frontend: OK"
