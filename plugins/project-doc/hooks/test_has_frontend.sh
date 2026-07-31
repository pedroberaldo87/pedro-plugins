#!/usr/bin/env bash
# test_has_frontend.sh — cobre lib-has-frontend.sh (achado F2.2 do plano
# design-como-doc-autoral: design.md só cobra quem tem interface).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/lib-has-frontend.sh"

BACKEND="$(mktemp -d /tmp/hf-backend-XXXXXX)"
FRONT_TSX="$(mktemp -d /tmp/hf-tsx-XXXXXX)"
FRONT_HTML="$(mktemp -d /tmp/hf-html-XXXXXX)"
FRONT_PKG="$(mktemp -d /tmp/hf-pkg-XXXXXX)"
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

echo "test_has_frontend: OK"
