#!/bin/bash
# resolve-plugin.sh — acha um arquivo dentro de OUTRO plugin pelo NOME dele.
#
# ⚠️ FONTE DA VERDADE: `_shared/resolve-plugin.sh`. As cópias dentro dos plugins são
# vendoradas por `scripts/sync-shared.sh` — editar a cópia deixa as outras defasadas.
#
# O DEFEITO QUE ELE MATA (Artigo 9). Escrever `${CLAUDE_PLUGIN_ROOT}/../<irmão>/…`
# amarra o vizinho à POSIÇÃO dele no disco. Isso vale rodando do repositório, onde os
# plugins são pastas irmãs — e não vale na máquina de quem instalou, porque o cache do
# harness guarda `<cache>/<marketplace>/<plugin>/<versão>/`: falta um nível E há um
# segmento de versão no meio. Medido em 2026-08-07: das 4 ocorrências no repo, 2 já
# estavam quebradas em install real.
#
# Uso:   resolve-plugin.sh <nome-do-plugin> <caminho/dentro/dele>
#        ex.: resolve-plugin.sh lixeiro lib/lixeiro.py
# Saída: o caminho absoluto no stdout e código 0 quando existe;
#        NADA no stdout e código 3 quando o plugin não está nesta máquina.
#
# Ausência não é erro: quem chama testa a saída vazia e segue calado — plugin irmão é
# camada a mais, nunca pré-requisito. Por isso o silêncio, e por isso o código 3 (o
# mesmo contrato do `resolve-dir.sh`: stdout é o dado, `$?` é o sinal).
#
# Três tentativas, na ordem, para na primeira que bate:
#   1. irmão direto            — <root>/../<nome>/<rel>            (rodando do repositório)
#   2. cache do MESMO marketplace — <root>/../../<nome>/*/<rel>    (instalado)
#   3. qualquer marketplace do cache — <config>/plugins/cache/*/<nome>/*/<rel>
# Entre versões, sai a MAIS ALTA (`sort -V`): cache com 1.9.0 e 1.10.0 tem que dar 1.10.0.

NOME="${1:?uso: resolve-plugin.sh <nome-do-plugin> <caminho/dentro/dele>}"
REL="${2:?uso: resolve-plugin.sh <nome-do-plugin> <caminho/dentro/dele>}"
RAIZ="${CLAUDE_PLUGIN_ROOT:-}"

# O primeiro caminho existente do glob, e entre versões a mais alta.
mais_alto() {
  ls -d "$@" 2>/dev/null | sort -V | tail -1
}

ACHADO=""
if [ -n "$RAIZ" ]; then
  [ -f "$RAIZ/../$NOME/$REL" ] && ACHADO="$RAIZ/../$NOME/$REL"
  [ -z "$ACHADO" ] && ACHADO=$(mais_alto "$RAIZ"/../../"$NOME"/*/"$REL")
fi
if [ -z "$ACHADO" ]; then
  CACHE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache"
  ACHADO=$(mais_alto "$CACHE"/*/"$NOME"/*/"$REL")
fi

[ -n "$ACHADO" ] && [ -f "$ACHADO" ] || exit 3
printf '%s\n' "$ACHADO"
