#!/bin/bash
# Suíte do pretooluse-barra-pr-externo.sh — o invólucro em shell. A decisão (alvo,
# dossiê) é do motor e está coberta em lib/test_pr_externo.py; aqui se prova só o que é
# do shell: sair calado no comando comum, repassar o bloqueio, pedir confirmação quando
# o motor pede ou QUEBRA, respeitar o teto por sessão e o kill-switch.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$DIR/pretooluse-barra-pr-externo.sh"
FALHAS=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

confere() { # rótulo, esperado, obtido
  if [ "$2" = "$3" ]; then echo "  ok   $1"; else echo "  FAIL $1 (esperado $2, veio $3)"; FALHAS=$((FALHAS + 1)); fi
}

# gh de mentira: o repositório alvo existe e quem envia NÃO tem escrita nele.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/gh" <<'GH'
#!/bin/bash
[ -f "$GH_QUEBRADO" ] && { echo "gh: connection refused" >&2; exit 1; }
case "$*" in
  *".permissions"*) echo '{"push": false}' ;;
  *) echo '{}' ;;
esac
GH
chmod +x "$TMP/bin/gh"

roda() { # comando do evento, [sessão] -> código de saída do hook
  printf '{"session_id":"%s","tool_input":{"command":"%s"},"cwd":"%s"}' "${2:-s1}" "$1" "$TMP" \
    | PATH="$TMP/bin:$PATH" PR_EXTERNO_DIR="$TMP/dossies" TMPDIR="$TMP" GH_QUEBRADO="$TMP/quebrado" \
      bash "$HOOK" >"$TMP/out" 2>"$TMP/err"
  echo $?
}
pediu() { grep -q '"permissionDecision": *"ask"' "$TMP/out"; echo $?; }
CRIAR='gh pr create --repo dono/projeto --head eu:fix/x'

confere "comando comum sai 0" 0 "$(roda 'git status')"
confere "comando comum não escreve nada" "" "$(cat "$TMP/err" "$TMP/out")"
confere "abertura de PR para terceiro sem dossiê sai 2" 2 "$(roda "$CRIAR")"
grep -q "dono/projeto" "$TMP/err"; confere "a mensagem nomeia o repositório" 0 $?
confere "segunda tentativa na mesma sessão ainda sai 2" 2 "$(roda "$CRIAR")"
confere "passado o teto, para de barrar" 0 "$(roda "$CRIAR")"
confere "…e entrega a decisão ao usuário, não libera calada" 0 "$(pediu)"
grep -q "dono/projeto" "$TMP/out"; confere "…com o motivo dentro do pedido" 0 $?
confere "outra sessão tem o próprio teto" 2 "$(roda "$CRIAR" s2)"
confere "outro motivo (outra branch) na mesma sessão volta a barrar" 2 "$(roda 'gh pr create --repo dono/projeto --head eu:outra')"

touch "$TMP/quebrado"
confere "GitHub fora do ar: sai 0…" 0 "$(roda "$CRIAR" s3)"
confere "…mas pedindo confirmação, nunca liberando calado" 0 "$(pediu)"
rm -f "$TMP/quebrado"

confere "kill-switch no ambiente desliga" 0 "$(PR_EXTERNO_GATE=0 roda "$CRIAR" s4)"
confere "…sem pedir nada" 1 "$(pediu)"

# o motor quebrando (python que explode) vira pedido de confirmação, não passagem livre
mkdir -p "$TMP/falso/hooks" "$TMP/falso/lib"
cp "$HOOK" "$TMP/falso/hooks/"
echo 'raise SystemExit(1)' > "$TMP/falso/lib/pr_externo.py"
printf '{"session_id":"s5","tool_input":{"command":"%s"},"cwd":"%s"}' "$CRIAR" "$TMP" \
  | TMPDIR="$TMP" bash "$TMP/falso/hooks/pretooluse-barra-pr-externo.sh" >"$TMP/out" 2>"$TMP/err"
confere "motor quebrado: sai 0…" 0 $?
confere "…pedindo confirmação ao usuário" 0 "$(pediu)"

echo
if [ "$FALHAS" -gt 0 ]; then echo "$FALHAS falha(s)"; exit 1; fi
echo "tudo ok"
