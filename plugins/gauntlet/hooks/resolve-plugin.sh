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
#   3. cache do NOSSO marketplace — <config>/plugins/cache/pedro-plugins/<nome>/*/<rel>
# Entre versões, sai a MAIS ALTA (`sort -V`): cache com 1.9.0 e 1.10.0 tem que dar 1.10.0.
#
# POR QUE A 3ª TENTATIVA NÃO VARRE O CACHE INTEIRO (scan 8e9a3ff2, achado 9). Até aqui ela
# era `cache/*/<nome>/*/<rel>`: qualquer marketplace, a versão mais alta ganha. Quem chama
# EXECUTA o que volta (`exec bash` no SessionStart, `exec_module` no plan_state) — então um
# plugin homônimo de OUTRO marketplace, ou uma cópia esquecida, com a versão que o autor
# escolheu, virava código rodando com os privilégios do usuário. Agora só vale o
# marketplace cujo nome é o do catálogo deste repositório (`MERCADO`, conferido contra
# `.claude-plugin/marketplace.json` por `_shared/test_resolve_plugin.py`). Nome cravado e
# sem curinga, de propósito: `pedro-plugins-fork` e `xpedro-plugins` não casam.
#
# A 3ª tentativa continua existindo (e não foi removida) porque a 2ª só alcança o irmão
# quando CLAUDE_PLUGIN_ROOT está no cache; sem a variável, ou com ela apontando para fora
# do cache, só a varredura do cache da configuração o encontra. Ela é rede de segurança,
# não caminho principal — os chamadores do repositório passam CLAUDE_PLUGIN_ROOT.
# Limite conhecido: dentro do NOSSO marketplace continua valendo a versão mais alta em
# disco, instalada ou não — fechar isso pede ler o `installed_plugins.json` do harness.

NOME="${1:?uso: resolve-plugin.sh <nome-do-plugin> <caminho/dentro/dele>}"
REL="${2:?uso: resolve-plugin.sh <nome-do-plugin> <caminho/dentro/dele>}"
RAIZ="${CLAUDE_PLUGIN_ROOT:-}"
# O nome do marketplace deste repositório (`"name"` do `.claude-plugin/marketplace.json`).
# Cravado: o plugin instalado só enxerga a própria pasta, o catálogo não viaja com ele.
MERCADO="pedro-plugins"

# NOME e REL viram caminho de um arquivo que o chamador EXECUTA. Nome de plugin é um
# segmento só e REL é relativo, sem `.`/`..` entre os segmentos (um `..` sairia da pasta do
# plugin e do marketplace). Fora disso, sai com 2 (3 é "não achei" — recusar não é isso).
# Cada segmento começa por letra, dígito ou `_`: `..`, `.` e curinga não passam.
SEG='[A-Za-z0-9_][A-Za-z0-9._-]*'
[[ "$NOME" =~ ^$SEG$ ]] || { echo "resolve-plugin.sh: nome de plugin inválido" >&2; exit 2; }
[[ "$REL" =~ ^$SEG(/$SEG)*$ ]] || { echo "resolve-plugin.sh: caminho inválido (só relativo, sem '..')" >&2; exit 2; }

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
  ACHADO=$(mais_alto "$CACHE"/"$MERCADO"/"$NOME"/*/"$REL")
fi

[ -n "$ACHADO" ] && [ -f "$ACHADO" ] || exit 3
printf '%s\n' "$ACHADO"
