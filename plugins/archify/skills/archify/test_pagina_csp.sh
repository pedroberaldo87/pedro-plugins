#!/bin/bash
# test_pagina_csp.sh — a página que o archify gera não pede nada à rede e traz CSP (c72f37da).
#
# O achado (hsf_dc7dd174): a página abria uma folha de estilo do Google Fonts ao ser aberta
# (vaza o IP e o momento de quem lê, e aceita o que o terceiro devolver) e não trazia
# Content-Security-Policy. Aqui: nenhuma página tracked — modelo, exemplo, diagrama da casa —
# referencia host externo em <link>/<script src>, e todas trazem a CSP restritiva
# (`default-src 'none'`, sem rede: `connect-src 'none'`, `img-src` só data:/blob:).
# Se há node, o render de verdade também é medido.
#
# Uso: bash plugins/archify/skills/archify/test_pagina_csp.sh
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../../../.." && pwd)"
FALHAS=0
ok()    { printf '  ok   %s\n' "$1"; }
falha() { printf '  FALHA %s\n     %s\n' "$1" "$2"; FALHAS=$((FALHAS + 1)); }

confere() { # arquivo
  local f="$1" rel="${1#$RAIZ/}"
  if grep -Eq '<(link|script)[^>]*(href|src)="https?://' "$f"; then
    falha "$rel: sem <link>/<script> externo" "$(grep -Eo '<(link|script)[^>]*(href|src)="https?://[^"]*' "$f" | head -1)"
  else
    ok "$rel: sem <link>/<script> externo"
  fi
  if grep -Eq 'fonts\.(googleapis|gstatic)\.com' "$f"; then
    falha "$rel: não fala com o Google Fonts" "referência ao Google Fonts"
  else
    ok "$rel: não fala com o Google Fonts"
  fi
  local csp
  csp="$(grep -Eo '<meta http-equiv="Content-Security-Policy" content="[^"]*"' "$f" | head -1)"
  local d faltou=""
  for d in "default-src 'none'" "connect-src 'none'" "img-src data: blob:" "base-uri 'none'" "form-action 'none'"; do
    case "$csp" in *"$d"*) ;; *) faltou="$faltou [$d]" ;; esac
  done
  case "$csp" in *"default-src *"*|*"connect-src *"*|*" http:"*|*" https:"*) faltou="$faltou [curinga ou host externo]" ;; esac
  if [ -z "$csp" ]; then faltou=" meta ausente"; fi
  if [ -z "$faltou" ]; then ok "$rel: traz a CSP restritiva"
  else falha "$rel: traz a CSP restritiva" "falta:$faltou"; fi
}

PAGINAS=("$AQUI/assets/template.html" "$AQUI"/templates/*.html "$AQUI"/examples/*.html "$RAIZ"/docs/fluxos/*.html)
for f in "${PAGINAS[@]}"; do
  [ -f "$f" ] && confere "$f"
done

# A CSP vem antes de qualquer elemento que busque recurso: meta de CSP só vale para o que vem DEPOIS.
primeiro="$(grep -n '<meta http-equiv="Content-Security-Policy"' "$AQUI/assets/template.html" | head -1 | cut -d: -f1)"
script="$(grep -n '<script' "$AQUI/assets/template.html" | head -1 | cut -d: -f1)"
if [ -n "$primeiro" ] && [ -n "$script" ] && [ "$primeiro" -lt "$script" ]; then
  ok "assets/template.html: a CSP precede o primeiro <script>"
else
  falha "assets/template.html: a CSP precede o primeiro <script>" "csp=${primeiro:-nenhuma} script=${script:-?}"
fi

# O render de verdade (precisa de node).
if command -v node >/dev/null 2>&1; then
  TRAB="$(mktemp -d)"; trap 'rm -rf "$TRAB"' EXIT
  ( cd "$TRAB" && node "$AQUI/bin/archify.mjs" render architecture "$AQUI/examples/web-app.architecture.json" "$TRAB/out.html" >/dev/null 2>&1 )
  if [ -f "$TRAB/out.html" ]; then
    confere "$TRAB/out.html"
  else
    falha "render do exemplo" "o archify não gerou a página"
  fi
else
  echo "  (sem node nesta máquina — só as páginas tracked foram medidas)"
fi

if [ "$FALHAS" -eq 0 ]; then echo "OK"; exit 0; fi
echo "$FALHAS falha(s)"; exit 1
