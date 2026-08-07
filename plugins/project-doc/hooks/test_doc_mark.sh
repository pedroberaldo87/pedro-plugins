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

echo
printf '%s passaram · %s falharam\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
