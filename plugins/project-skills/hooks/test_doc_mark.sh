#!/bin/bash
# test_doc_mark.sh — suíte da MARCA do texto aprovado (S-2).
# Roda isolado em um diretório temporário; não toca projeto nenhum.
# Uso: bash test_doc_mark.sh
#
# O que ela prova é COMPORTAMENTO, não redação: monta um documento, aprova pelo
# comando, mexe no CORPO e exige que a marca mude; mexe só no FRONTMATTER e exige
# que ela NÃO mude. Teste que confere frase em SKILL.md não pega marca errada.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APROVAR="$SCRIPT_DIR/doc-aprovar.sh"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/lib-doc-mark.sh"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  ✗ %s\n     esperado: %s\n     obtido:   %s\n' "$1" "$2" "$3"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

DOC="$TMP/journeys.md"
escreve() { # escreve <status> <corpo>
  printf -- '---\nauthored-by: human\nstatus: %s\nscope: []\n---\n# Jornadas\n%s\n' "$1" "$2" > "$DOC"
}

echo "── Marca do texto aprovado ──"

# 1) o comando grava as três linhas do de acordo
escreve draft "O visitante entra e vê o catálogo."
OUT=$(bash "$APROVAR" "$DOC" 2>&1)
grep -q '^status: approved$' "$DOC" \
  && ok "doc-aprovar grava status: approved" \
  || bad "doc-aprovar grava status: approved" "status: approved" "$OUT"

grep -q "^approved: $(date +%F)$" "$DOC" \
  && ok "doc-aprovar grava a data de hoje" \
  || bad "doc-aprovar grava a data de hoje" "approved: $(date +%F)" "$(grep '^approved:' "$DOC")"

SIG=$(doc_marca_registrada "$DOC")
[ -n "$SIG" ] && ok "doc-aprovar grava approved-sig" \
  || bad "doc-aprovar grava approved-sig" "uma marca" "vazio"

# 2) a marca gravada é a do corpo de agora (é isto que o gate recalcula)
[ "$SIG" = "$(doc_marca "$DOC")" ] \
  && ok "a marca gravada bate com o corpo recém-aprovado" \
  || bad "a marca gravada bate com o corpo recém-aprovado" "$(doc_marca "$DOC")" "$SIG"

# 3) MEXER NO CORPO MUDA A MARCA — o coração do S-2
perl -0pi -e 's/vê o catálogo/vê o catálogo e paga na hora/' "$DOC"
[ "$(doc_marca "$DOC")" != "$SIG" ] \
  && ok "corpo alterado depois do de acordo: a marca DIVERGE do approved-sig" \
  || bad "corpo alterado depois do de acordo: a marca DIVERGE do approved-sig" \
         "marca != $SIG" "marca == $SIG"

# 4) mexer SÓ no frontmatter não muda a marca — senão nem gravá-la seria possível,
#    e `correcao-pendente:` reabriria a etapa que ela existe para manter fechada
bash "$APROVAR" "$DOC" >/dev/null 2>&1        # reaprova o corpo novo
SIG2=$(doc_marca_registrada "$DOC")
awk '/^scope: \[\]$/ { print "correcao-pendente: trocar paga por confirma" } { print }' "$DOC" > "$DOC.x" && mv "$DOC.x" "$DOC"
grep -q '^correcao-pendente:' "$DOC" || bad "fixture: correcao-pendente entrou" "linha no frontmatter" "ausente"
[ "$(doc_marca "$DOC")" = "$SIG2" ] \
  && ok "linha nova no frontmatter: a marca NÃO muda" \
  || bad "linha nova no frontmatter: a marca NÃO muda" "$SIG2" "$(doc_marca "$DOC")"

# 5) o corpo restaurado ao texto aprovado volta a bater — a divergência é do TEXTO,
#    não um carimbo de "foi tocado"
CORPO_APROVADO=$(doc_corpo "$DOC")
awk '/^correcao-pendente:/ { next } { print }' "$DOC" > "$DOC.x" && mv "$DOC.x" "$DOC"
[ "$(doc_marca "$DOC")" = "$SIG2" ] && [ "$(doc_corpo "$DOC")" = "$CORPO_APROVADO" ] \
  && ok "corpo intacto: a marca continua batendo com o approved-sig" \
  || bad "corpo intacto: a marca continua batendo" "$SIG2" "$(doc_marca "$DOC")"

# 6) documento sem frontmatter: a marca é do arquivo inteiro (não fica vazia)
printf '# Sem frontmatter\ntexto\n' > "$TMP/solto.md"
[ -n "$(doc_marca "$TMP/solto.md")" ] \
  && ok "documento sem frontmatter: a marca ainda é calculável" \
  || bad "documento sem frontmatter: a marca ainda é calculável" "uma marca" "vazio"

echo "── Marca do conjunto (sidecar de protótipo, R-22) ──"

# Fixture: um projeto de mentira com a casa .claude/docs/prototipo/ e duas telas.  # casa-ok: fixture de teste, o literal e o dado do caso
CASA="$TMP/proj/.claude/docs/prototipo"  # casa-ok: fixture de teste, o literal e o dado do caso
mkdir -p "$CASA"
printf '<h1>Painel</h1>\n<p>3 pedidos (FICTICIO)</p>\n' > "$CASA/painel.html"
printf '<h1>Entrada</h1>\n<form>FICTICIO</form>\n'      > "$CASA/entrada.html"
SC="$CASA/interface.prototipo.md"
cat > "$SC" <<'EOF'
---
natureza: anexo
anexo-de: design.md
design-sig: 1836471203
status: ready
correcao-pendente: trocar o rótulo do painel
conjunto-sig: 0
marcador-ficticio: FICTICIO
---

## Arquivos

- .claude/docs/prototipo/painel.html
- .claude/docs/prototipo/entrada.html
EOF
ESPERADA=$(cat "$CASA/painel.html" "$CASA/entrada.html" | cksum | cut -d' ' -f1)

# 7) fora do rito: --marca IMPRIME a marca do conjunto e não escreve um byte
ANTES=$(cat "$SC")
OUT=$(bash "$APROVAR" --marca "$SC" 2>&1)
[ "$OUT" = "$ESPERADA" ] \
  && ok "--marca imprime a marca do conjunto (cat | cksum)" \
  || bad "--marca imprime a marca do conjunto (cat | cksum)" "$ESPERADA" "$OUT"
[ "$(cat "$SC")" = "$ANTES" ] \
  && ok "--marca não escreve no sidecar" \
  || bad "--marca não escreve no sidecar" "arquivo intacto" "arquivo alterado"

# 8) o rito grava conjunto-sig e o status vira approved
bash "$APROVAR" "$SC" >/dev/null 2>&1
grep -q "^conjunto-sig: $ESPERADA$" "$SC" \
  && ok "o rito grava conjunto-sig no sidecar" \
  || bad "o rito grava conjunto-sig no sidecar" "conjunto-sig: $ESPERADA" "$(grep '^conjunto-sig:' "$SC")"
grep -q '^status: approved$' "$SC" \
  && ok "o rito aprova o sidecar (status: approved)" \
  || bad "o rito aprova o sidecar (status: approved)" "status: approved" "$(grep '^status:' "$SC")"

# 9) trocar uma tela diverge a marca gravada — o conjunto aprovado é DESTE conteúdo
printf '<h1>Painel</h1>\n<p>4 pedidos</p>\n' > "$CASA/painel.html"
NOVA=$(bash "$APROVAR" --marca "$SC" 2>&1)
[ "$NOVA" != "$ESPERADA" ] \
  && ok "tela alterada: a marca do conjunto diverge da gravada" \
  || bad "tela alterada: a marca do conjunto diverge da gravada" "marca != $ESPERADA" "marca == $NOVA"

# 10) arquivo listado e ausente: o rito RECUSA, não aprova conjunto pela metade
rm "$CASA/entrada.html"
if bash "$APROVAR" "$SC" >/dev/null 2>&1; then
  bad "arquivo listado e ausente: o rito recusa" "exit != 0" "exit 0"
else
  ok "arquivo listado e ausente: o rito recusa"
fi

# 11) CICLO do design regravado (F13.2): design muda → doc-load reabre o anexo →
#     o rito reaprova (regravando TAMBÉM o design-sig) → o anexo fecha de novo.
DOC_LOAD="$SCRIPT_DIR/../lib/doc_load.py"
reaberto() { # imprime True/False do campo `reaberto` do único anexo
  python3 -c '
import json, subprocess, sys
estado = json.loads(subprocess.run(
    [sys.executable, sys.argv[1], "--project-root", sys.argv[2], "--json"],
    capture_output=True, text=True).stdout)
print(estado["anexos"][0]["reaberto"])' "$DOC_LOAD" "$TMP/proj"
}
printf '<h1>Entrada</h1>\n<form>FICTICIO</form>\n' > "$CASA/entrada.html"   # restaura a tela do teste 10
printf -- '---\nauthored-by: human\nstatus: approved\n---\n# Design\nUma tela.\n' > "$TMP/proj/.claude/docs/design.md"  # casa-ok: fixture de teste, o literal e o dado do caso
bash "$APROVAR" "$SC" >/dev/null 2>&1                                        # aprova com o design de agora
[ "$(reaberto)" = "False" ] \
  && ok "ciclo: anexo recém-aprovado nasce fechado" \
  || bad "ciclo: anexo recém-aprovado nasce fechado" "reaberto=False" "reaberto=$(reaberto)"
printf -- '---\nauthored-by: human\nstatus: approved\n---\n# Design\nDuas telas.\n' > "$TMP/proj/.claude/docs/design.md"  # casa-ok: fixture de teste, o literal e o dado do caso
[ "$(reaberto)" = "True" ] \
  && ok "ciclo: design regravado reabre o anexo" \
  || bad "ciclo: design regravado reabre o anexo" "reaberto=True" "reaberto=$(reaberto)"
bash "$APROVAR" "$SC" >/dev/null 2>&1                                        # o rito reaprova
grep -q '^design-sig: [0-9]' "$SC" \
  && ok "ciclo: o rito regrava o design-sig no sidecar" \
  || bad "ciclo: o rito regrava o design-sig no sidecar" "design-sig numérico" "$(grep '^design-sig:' "$SC")"
[ "$(reaberto)" = "False" ] \
  && ok "ciclo: reaprovado, o anexo fecha de novo" \
  || bad "ciclo: reaprovado, o anexo fecha de novo" "reaberto=False" "reaberto=$(reaberto)"

# 12) documento autoral comum: --marca imprime a marca do corpo, sem escrever
escreve draft "O visitante entra e vê o catálogo."
OUT=$(bash "$APROVAR" --marca "$DOC" 2>&1)
[ "$OUT" = "$(doc_marca "$DOC")" ] && ! grep -q '^approved-sig:' "$DOC" \
  && ok "--marca no doc autoral imprime a marca do corpo e não aprova" \
  || bad "--marca no doc autoral imprime a marca do corpo e não aprova" "$(doc_marca "$DOC")" "$OUT"

echo
printf '%s passaram · %s falharam\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
