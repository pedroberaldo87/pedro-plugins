#!/bin/bash
# diagrama-blueprint.sh — desenha o diagrama da etapa 5 do /start pelo `archify`.
#
# A etapa 5 descrevia o diagrama em prosa e não executava nada: quem lia acreditava
# que o desenho nascia, e ele nunca nascia. Este script é o mecanismo.
#
# Uso:   diagrama-blueprint.sh <raiz-do-projeto> <workflow|architecture> <entrada.json> <nome.html>
#        ex.: diagrama-blueprint.sh "$PWD" workflow /tmp/ciclo.json organismo.html
# Saída: o caminho absoluto do HTML no stdout e código 0 quando desenhou;
#        a linha de DEGRADADO no stdout e código 3 quando o `archify` não está
#        nesta máquina — a etapa NÃO trava, mas o relatório diz em voz alta.
#
# O `archify` é achado pelo NOME (resolve-plugin.sh), nunca por caminho relativo:
# no cache do harness o vizinho mora em <cache>/<marketplace>/<plugin>/<versão>/.
#
# A régua de nome é a do `archify`, sem emenda: `organismo.html` para o sistema
# inteiro e `fluxo-<slug>.html` para cada fluxo que o `blueprint.md` NOMEIA. Nome
# estável significa sobrescrever — a revisão 5b passa por cima do mesmo arquivo.

RAIZ="${1:?uso: diagrama-blueprint.sh <raiz> <tipo> <entrada.json> <nome.html>}"
TIPO="${2:?uso: diagrama-blueprint.sh <raiz> <tipo> <entrada.json> <nome.html>}"
ENTRADA="${3:?uso: diagrama-blueprint.sh <raiz> <tipo> <entrada.json> <nome.html>}"
NOME="${4:?uso: diagrama-blueprint.sh <raiz> <tipo> <entrada.json> <nome.html>}"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Os sub-scripts rodam no MESMO bash que este: no Windows o `bash` do PATH é o do
# WSL, e chamar por nome trocaria o interpretador no meio do caminho.
BASH="${BASH:-bash}"

case "$NOME" in
  organismo.html|fluxo-*.html) ;;
  *) printf 'nome fora da régua do archify: %s (use organismo.html ou fluxo-<slug>.html)\n' "$NOME" >&2
     exit 2 ;;
esac

BIN=$("$BASH" "$AQUI/resolve-plugin.sh" archify skills/archify/bin/archify.mjs 2>/dev/null)
DIR_SH=$("$BASH" "$AQUI/resolve-plugin.sh" archify skills/archify/resolve-dir.sh 2>/dev/null)
if [ -z "$BIN" ] || [ -z "$DIR_SH" ]; then
  printf 'DEGRADADO: `archify` ausente nesta máquina — %s não foi desenhado; o blueprint.md sozinho fecha a etapa.\n' "$NOME"
  exit 3
fi

DESTINO=$("$BASH" "$DIR_SH" "$RAIZ" archify 2>/dev/null)
[ -n "$DESTINO" ] || exit 1

node "$BIN" render "$TIPO" "$ENTRADA" "$DESTINO/$NOME" >/dev/null 2>&1 || exit 1
[ -f "$DESTINO/$NOME" ] || exit 1
printf '%s\n' "$DESTINO/$NOME"
