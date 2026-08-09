#!/bin/bash
# doc-aprovar.sh — grava o de acordo do dono no frontmatter de um documento autoral.
# Uso: bash doc-aprovar.sh <arquivo.md>
#
# POR QUE EXISTE (S-2): `status: approved` + `approved:` dizem QUE o dono aprovou,
# não SOBRE QUAL TEXTO. Este comando calcula a marca do CORPO (`doc_marca`, de
# lib-doc-mark.sh) e grava `approved-sig:` junto — é ela que o gate de plano
# recalcula depois. Aprovação digitada à mão nasce sem marca e o de acordo volta a
# ser sobre um nome de arquivo.
#
# Ele NÃO decide nada: quem chama só roda isto depois de o dono dizer, com todas as
# letras, que está satisfeito. O corpo não é tocado — a marca mediria outro texto.
set -u

DOC="${1:-}"
[ -n "$DOC" ] && [ -f "$DOC" ] || { echo "uso: bash doc-aprovar.sh <arquivo.md>" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/lib-doc-mark.sh" || exit 2

MARCA=$(doc_marca "$DOC")
[ -n "$MARCA" ] || { echo "não deu para calcular a marca de $DOC" >&2; exit 2; }

awk -v hoje="$(date +%F)" -v marca="$MARCA" '
  NR == 1 && $0 == "---" { print; dentro = 1; next }
  dentro && $0 == "---" {
    if (!visto["status"])       print "status: approved"
    if (!visto["approved"])     print "approved: " hoje
    if (!visto["approved-sig"]) print "approved-sig: " marca
    print; dentro = 0; next
  }
  dentro && /^status:/       { print "status: approved";     visto["status"] = 1;       next }
  dentro && /^approved:/     { print "approved: " hoje;      visto["approved"] = 1;     next }
  dentro && /^approved-sig:/ { print "approved-sig: " marca; visto["approved-sig"] = 1; next }
  { print }
' "$DOC" > "$DOC.aprovando" && mv "$DOC.aprovando" "$DOC"

printf 'de acordo gravado em %s — status: approved · approved-sig: %s\n' "$DOC" "$MARCA"
