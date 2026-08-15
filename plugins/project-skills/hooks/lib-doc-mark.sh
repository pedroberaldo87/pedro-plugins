#!/bin/bash
# lib-doc-mark.sh — a MARCA do texto aprovado de um documento autoral.
# Feito para ser SOURCED (não executa nada por conta própria).
#
# POR QUE EXISTE (S-2): `status: approved` diz que o dono deu o de acordo, mas não
# diz SOBRE QUAL TEXTO. Editar o corpo depois da aprovação deixava a etapa fechada
# com um conteúdo que ninguém aprovou. A marca fecha esse buraco: a aprovação grava
# `approved-sig:` no frontmatter, e quem cobra recalcula e compara.
#
# REGRA: a marca é do CORPO, nunca do arquivo inteiro. O frontmatter carrega a
# própria marca (e a data, e o status) — incluí-lo faria a marca mudar ao ser
# gravada, e nada bateria com nada.
#
# `cksum` e `awk`, não `sha256sum`: POSIX está em toda máquina, o resto não —
# e o hook que depende de ferramenta ausente é o hook que cega em silêncio.

# doc_corpo <arquivo> — o texto abaixo do frontmatter YAML (sem frontmatter: tudo).
#
# O `\r` final cai ANTES de qualquer outra regra: no Windows o mesmo documento chega
# com fim de linha CRLF, e sem isto a receita do shell somava um byte a mais por linha
# que a do Python (que corta o `\r` ao separar as linhas) — duas marcas para um texto só.
# De quebra, `---\r` volta a ser reconhecido como cerca do frontmatter.
doc_corpo() {
  awk '
    { sub(/\r$/, "") }
    NR == 1 && $0 == "---" { dentro = 1; next }
    dentro && $0 == "---"  { dentro = 0; next }
    dentro                 { next }
    { print }
  ' "$1" 2>/dev/null
}

# doc_marca <arquivo> — a marca do corpo. Saída vazia = não deu para calcular
# (arquivo ilegível, `cksum` ausente): quem chama trata como borda de infra.
doc_marca() {
  [ -r "$1" ] || return 1
  doc_corpo "$1" | cksum 2>/dev/null | cut -d' ' -f1
}

# doc_marca_registrada <arquivo> — o `approved-sig:` gravado na aprovação, ou nada.
doc_marca_registrada() {
  sed -n 's/^approved-sig:[[:space:]]*//p' "$1" 2>/dev/null | head -1 | tr -d ' \r'
}
