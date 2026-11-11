#!/bin/bash
# test_saida_meta.sh — `meta.output` de um diagrama NÃO escolhe onde o archify escreve (P6).
#
# O achado (hsf_61a97b5d, e a ponta do hsf_a43c635d no cli.mjs): `archify render <tipo> <json>`
# sem o 4º argumento escrevia no `meta.output` do JSON, que vem de um repositório clonado e
# podia ser `../../x.html`, um caminho absoluto ou um symlink plantado. Um argumento de saída
# EXPLÍCITO continua sendo escolha de quem chama; só o `meta.output` ganha a régua: caminho
# relativo, sem `..`, terminado em `.html`, dentro da pasta de trabalho e sem symlink.
#
# Uso: bash plugins/archify/skills/archify/test_saida_meta.sh

set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
FALHAS=0

ok()    { printf '  ok   %s\n' "$1"; }
falha() { printf '  FALHA %s\n     %s\n' "$1" "$2"; FALHAS=$((FALHAS + 1)); }

if ! command -v node >/dev/null 2>&1; then
  echo "  (sem node nesta máquina — o archify é Node; nada a medir)"
  exit 0
fi

BASE=$(mktemp -d)
trap 'rm -rf "$BASE"' EXIT
EXEMPLO="$AQUI/examples/web-app.architecture.json"
[ -f "$EXEMPLO" ] || { falha "exemplo do archify" "ausente: $EXEMPLO"; exit 1; }

# Uma cópia do exemplo com o `meta.output` pedido (o JSON é escrito pelo node, sem aspas na mão).
faz_json() { # destino output
  node -e '
    const fs = require("fs");
    const d = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
    d.meta.output = process.argv[3];
    fs.writeFileSync(process.argv[2], JSON.stringify(d));
  ' "$EXEMPLO" "$1" "$2"
}

roda() { # pasta-de-trabalho json [saida-explicita]
  ( cd "$1" && node "$AQUI/bin/archify.mjs" render architecture "$2" ${3:+"$3"} 2>&1 )
}

TRAB="$BASE/trab"
mkdir -p "$TRAB"

# 1) o caso honesto continua: nome simples e subpasta relativa
faz_json "$BASE/ok.json" "saida-ok.html"
roda "$TRAB" "$BASE/ok.json" >/dev/null
[ -f "$TRAB/saida-ok.html" ] && ok "meta.output simples grava na pasta de trabalho" \
  || falha "meta.output simples grava na pasta de trabalho" "arquivo ausente"

faz_json "$BASE/sub.json" "sub/pasta/saida.html"
roda "$TRAB" "$BASE/sub.json" >/dev/null
[ -f "$TRAB/sub/pasta/saida.html" ] && ok "meta.output com subpasta relativa grava" \
  || falha "meta.output com subpasta relativa grava" "arquivo ausente"

# 2) o que a régua recusa — e que NÃO pode ter escrito nada fora
recusa() { # rotulo output arquivo-que-nao-pode-nascer
  faz_json "$BASE/mau.json" "$2"
  OUT=$(roda "$TRAB" "$BASE/mau.json")
  RC=$?
  if [ -e "$3" ]; then falha "$1" "o arquivo de fora nasceu: $3"; return; fi
  case "$OUT" in *"Refusing meta.output"*) ok "$1" ;; *) falha "$1" "sem a recusa dita: $OUT" ;; esac
  [ "$RC" -ne 0 ] || true
}
recusa "meta.output com .. é recusado" "../fora.html" "$BASE/fora.html"
recusa "meta.output com .. no meio é recusado" "sub/../../fora2.html" "$BASE/fora2.html"
recusa "meta.output absoluto é recusado" "$BASE/absoluto.html" "$BASE/absoluto.html"
recusa "meta.output que não é .html é recusado" "script.sh" "$TRAB/script.sh"

# 3) symlink plantado: o alvo do link não é sobrescrito
echo intacta > "$BASE/vitima.txt"
if ln -s "$BASE/vitima.txt" "$TRAB/elo.html" 2>/dev/null && [ -L "$TRAB/elo.html" ]; then
  faz_json "$BASE/elo.json" "elo.html"
  OUT=$(roda "$TRAB" "$BASE/elo.json")
  [ "$(cat "$BASE/vitima.txt")" = "intacta" ] && ok "meta.output que é symlink não sobrescreve o alvo" \
    || falha "meta.output que é symlink não sobrescreve o alvo" "vítima mudou: $OUT"
  mkdir -p "$BASE/alvo-pasta"
  ln -s "$BASE/alvo-pasta" "$TRAB/pasta-elo"
  faz_json "$BASE/pasta.json" "pasta-elo/x.html"
  roda "$TRAB" "$BASE/pasta.json" >/dev/null
  [ ! -e "$BASE/alvo-pasta/x.html" ] && ok "meta.output dentro de pasta-symlink que sai não escreve fora" \
    || falha "meta.output dentro de pasta-symlink que sai não escreve fora" "nasceu $BASE/alvo-pasta/x.html"
else
  echo "  (sem symlink nesta plataforma — casos de link pulados)"
fi

# 4) o argumento de saída EXPLÍCITO segue sendo escolha de quem chama
faz_json "$BASE/exp.json" "../ignorado.html"
roda "$TRAB" "$BASE/exp.json" "$BASE/explicito.html" >/dev/null
[ -f "$BASE/explicito.html" ] && ok "o 4º argumento explícito continua valendo, onde o chamador quiser" \
  || falha "o 4º argumento explícito continua valendo" "arquivo ausente"

echo
if [ "$FALHAS" -gt 0 ]; then
  echo "FALHOU: $FALHAS"
  exit 1
fi
echo "OK"
