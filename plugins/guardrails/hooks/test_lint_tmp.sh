#!/bin/bash
# test_lint_tmp.sh — rascunho no temporário do sistema não é barrado pelo lint;
# arquivo de projeto com o mesmo erro continua barrado (quando há ruff na máquina).
HERE="$(cd "$(dirname "$0")" && pwd)"
H="$HERE/lint-and-typecheck.sh"
PASS=0; FAIL=0
check() { if [ "$2" = "1" ]; then PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; else FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; fi; }
# devolve o código de saída do hook: 2 = barrou a edição, 0 = liberou
roda() { printf '{"session_id":"lint-tmp-%s","tool_input":{"file_path":"%s"}}' "$$" "$1" | bash "$H" >/dev/null 2>&1; echo $?; }

RUIM='import sys
l = 1
'
T=$(mktemp -d "${TMPDIR:-/tmp}/lint-tmp.XXXXXX")
P=$(mktemp -d "$HOME/.lint-proj-test.XXXXXX")
trap 'rm -rf "$T" "$P"' EXIT
printf '%s' "$RUIM" > "$T/rascunho.py"
printf '%s' "$RUIM" > "/tmp/lint-tmp-$$.py"
printf '%s' "$RUIM" > "$P/codigo.py"

check "rascunho no TMPDIR não é barrado" "$([ "$(roda "$T/rascunho.py")" = 0 ] && echo 1 || echo 0)"
check "rascunho em /tmp não é barrado" "$([ "$(roda "/tmp/lint-tmp-$$.py")" = 0 ] && echo 1 || echo 0)"
rm -f "/tmp/lint-tmp-$$.py"

if command -v ruff >/dev/null 2>&1; then
  check "arquivo fora do temporário, com o mesmo erro, continua barrado" \
    "$([ "$(roda "$P/codigo.py")" = 2 ] && echo 1 || echo 0)"
else
  echo "  (sem ruff na máquina — o caso barrado não é medido)"
fi

echo ""
[ "$FAIL" -eq 0 ] && { echo "OK ($PASS checks)"; exit 0; }
echo "FALHOU ($FAIL de $((PASS+FAIL)))"; exit 1
