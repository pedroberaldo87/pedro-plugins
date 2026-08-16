#!/bin/bash
# doc-aprovar.sh — grava o de acordo do dono no frontmatter de um documento autoral.
# Uso: bash doc-aprovar.sh [--marca] <arquivo.md>
#
# POR QUE EXISTE (S-2): `status: approved` + `approved:` dizem QUE o dono aprovou,
# não SOBRE QUAL TEXTO. Este comando calcula a marca do CORPO (`doc_marca`, de
# lib-doc-mark.sh) e grava `approved-sig:` junto — é ela que o gate de plano
# recalcula depois. Aprovação digitada à mão nasce sem marca e o de acordo volta a
# ser sobre um nome de arquivo.
#
# SIDECAR de protótipo (R-22, lei em .claude/docs/prototipo/FORMATO.md): documento
# com `natureza: anexo` no frontmatter é aprovado pela marca do CONJUNTO — o `cksum`
# POSIX da emenda dos arquivos listados em `## Arquivos`, na ordem do corpo. O rito
# grava `conjunto-sig:`; com `--marca` o comando só IMPRIME a marca, sem escrever
# nada — conferência fora do rito não é aprovação.
#
# Ele NÃO decide nada: quem chama só roda isto depois de o dono dizer, com todas as
# letras, que está satisfeito. O corpo não é tocado — a marca mediria outro texto.
set -u

SO_IMPRIME=0
[ "${1:-}" = "--marca" ] && { SO_IMPRIME=1; shift; }
DOC="${1:-}"
[ -n "$DOC" ] && [ -f "$DOC" ] || { echo "uso: bash doc-aprovar.sh [--marca] <arquivo.md>" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$SCRIPT_DIR/lib-doc-mark.sh" || exit 2

# conjunto_marca <sidecar> — o `cat <arquivos> | cksum` da emenda, na ordem do corpo.
# A raiz do projeto é a casa do sidecar menos `.claude/docs/prototipo/`. Arquivo
# listado e ausente é recusa, não marca de conjunto pela metade.
conjunto_marca() {
  local raiz rel alvos=()
  raiz="$(cd "$(dirname "$1")/../../.." && pwd)" || return 1
  while IFS= read -r rel; do
    [ -f "$raiz/$rel" ] || { echo "listado em ## Arquivos e ausente em disco: $rel" >&2; return 1; }
    alvos+=("$raiz/$rel")
  done < <(awk '
    { sub(/\r$/, "") }
    /^## /  { dentro = ($0 == "## Arquivos"); next }
    dentro && /^- / { print substr($0, 3) }
  ' "$1")
  [ "${#alvos[@]}" -gt 0 ] || { echo "o corpo não lista arquivo nenhum em ## Arquivos" >&2; return 1; }
  cat "${alvos[@]}" | cksum | cut -d' ' -f1
}

# Sidecar de protótipo? A natureza mora no frontmatter.
EH_ANEXO=0
if [ "$(head -1 "$DOC" | tr -d '\r')" = "---" ] \
   && sed -n '2,/^---/p' "$DOC" | grep -q '^natureza:[[:space:]]*anexo'; then
  EH_ANEXO=1
fi

if [ "$EH_ANEXO" -eq 1 ]; then
  MARCA=$(conjunto_marca "$DOC") || exit 2
  [ -n "$MARCA" ] || { echo "não deu para calcular a marca do conjunto de $DOC" >&2; exit 2; }
  if [ "$SO_IMPRIME" -eq 1 ]; then printf '%s\n' "$MARCA"; exit 0; fi
  # design-sig (FORMATO.md): a marca de HOJE do documento que sustenta o anexo
  # (`anexo-de`). Sem regravá-la aqui, anexo reaberto por design regravado ficaria
  # reaberto para sempre — o doc-load compararia contra a marca velha eternamente.
  DSIG=""
  ANEXO_DE=$(sed -n '2,/^---/p' "$DOC" | sed -n 's/^anexo-de:[[:space:]]*//p' | head -1 | tr -d ' \r')
  if [ -n "$ANEXO_DE" ]; then
    RAIZ="$(cd "$(dirname "$DOC")/../../.." && pwd)"
    [ -f "$RAIZ/.claude/docs/$ANEXO_DE" ] && DSIG=$(doc_marca "$RAIZ/.claude/docs/$ANEXO_DE")
  fi
  awk -v marca="$MARCA" -v dsig="$DSIG" '
    NR == 1 && $0 == "---" { print; dentro = 1; next }
    dentro && $0 == "---" {
      if (!visto["status"])                     print "status: approved"
      if (!visto["conjunto-sig"])               print "conjunto-sig: " marca
      if (dsig != "" && !visto["design-sig"])   print "design-sig: " dsig
      print; dentro = 0; next
    }
    dentro && /^status:/       { print "status: approved";      visto["status"] = 1;       next }
    dentro && /^conjunto-sig:/ { print "conjunto-sig: " marca;  visto["conjunto-sig"] = 1; next }
    dentro && /^design-sig:/ && dsig != "" { print "design-sig: " dsig; visto["design-sig"] = 1; next }
    { print }
  ' "$DOC" > "$DOC.aprovando" && mv "$DOC.aprovando" "$DOC"
  printf 'de acordo gravado em %s — status: approved · conjunto-sig: %s%s\n' \
    "$DOC" "$MARCA" "${DSIG:+ · design-sig: $DSIG}"
  exit 0
fi

MARCA=$(doc_marca "$DOC")
[ -n "$MARCA" ] || { echo "não deu para calcular a marca de $DOC" >&2; exit 2; }
if [ "$SO_IMPRIME" -eq 1 ]; then printf '%s\n' "$MARCA"; exit 0; fi

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
