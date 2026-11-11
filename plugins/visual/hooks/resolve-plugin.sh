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
#   2. cache do NOSSO marketplace, pelo caminho da raiz — <cache>/pedro-plugins/<nome>/*/<rel>
#   3. cache do NOSSO marketplace, pela configuração    — <config>/plugins/cache/pedro-plugins/<nome>/*/<rel>
# Entre versões, vale a que o harness INSTALOU (`installed_plugins.json`); sem registro,
# a mais alta DENTRO das que são versão de verdade (ver `escolhe_versao`).
#
# POR QUE NENHUMA DAS TRÊS VARRE O CACHE INTEIRO (scan 8e9a3ff2, achado 9). Até aqui a 3ª
# era `cache/*/<nome>/*/<rel>`: qualquer marketplace, a versão mais alta ganha. Quem chama
# EXECUTA o que volta (`exec bash` no SessionStart, `exec_module` no plan_state) — então um
# plugin homônimo de OUTRO marketplace, ou uma cópia esquecida, com a versão que o autor
# escolheu, virava código rodando com os privilégios do usuário. Agora só vale o
# marketplace cujo nome é o do catálogo deste repositório (`MERCADO`, conferido contra
# `.claude-plugin/marketplace.json` por `_shared/test_resolve_plugin.py`). Nome cravado e
# sem curinga, de propósito: `pedro-plugins-fork` e `xpedro-plugins` não casam.
#
# AS TENTATIVAS 1 E 2 TAMBÉM SÃO CRAVADAS (revisão 1 do PR 14). `CLAUDE_PLUGIN_ROOT` é
# variável de ambiente: apontada para `cache/outro/…`, o "irmão" saía de dentro de `outro`.
# Agora a raiz é resolvida (`pwd -P`, então `..` e link não escapam) e só conta se estiver
#   · dentro de `<config>/plugins/cache/pedro-plugins/` — a 2ª parte do cache dali; ou
#   · dentro de um checkout DESTE repositório: algum ancestral tem
#     `.claude-plugin/marketplace.json` cujo PRIMEIRO `"name"` é `pedro-plugins` — a 1ª.
# Raiz em qualquer outro lugar (outro marketplace, pasta solta) não escolhe irmão: cai na
# 3ª, que só olha o cache do nosso marketplace.
#
# A 3ª tentativa continua existindo porque as outras só alcançam o irmão quando
# CLAUDE_PLUGIN_ROOT está no nosso cache ou no repositório; sem a variável, ou com ela
# apontando para fora, só a varredura do cache da configuração o encontra. Ela é rede de
# segurança, não caminho principal — os chamadores do repositório passam CLAUDE_PLUGIN_ROOT.
#
# VERSÃO. Só diretório cujo nome é versão (`1.10.0`, `1.2.3.4`, `2.0.0-beta.1`; ao menos
# `N.N`) entra na escolha — `unknown`, um SHA, `latest` ou resto de build NÃO ganham da
# versão real só por ordenarem depois. Se `<config>/plugins/installed_plugins.json` nomeia a
# versão instalada de `<nome>@pedro-plugins` e a pasta existe, é exatamente ela (versão
# antiga ou não-instalada deixada no disco nunca é devolvida). Sem registro legível, ou com
# registro que aponta para pasta que sumiu, vale a mais alta válida. Pré-release
# (`1.10.0-beta`) fica abaixo da versão final de mesmo número. Limite conhecido: sem
# registro, a mais alta válida em disco pode ser uma versão já desinstalada.

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
VERSAO='^[0-9]+(\.[0-9]+){1,3}([-+][0-9A-Za-z.-]+)?$'
[[ "$REL" =~ ^$SEG(/$SEG)*$ ]] || { echo "resolve-plugin.sh: caminho inválido (só relativo, sem '..')" >&2; exit 2; }

# A versão instalada de `<nome>@$MERCADO` segundo o harness, ou nada. `$1` é a pasta do
# marketplace no cache (`<config>/plugins/cache/pedro-plugins`); o registro mora dois níveis
# acima. Sem jq (nem python) de propósito: o resolvedor roda em hook, e hook não pode
# depender de interpretador extra. Só o ÚLTIMO segmento do `installPath` é aproveitado, e só
# se for versão — o caminho vem sempre da pasta cravada, nunca do texto do registro. No
# Windows o registro escapa a barra invertida (`C:\\Users\\…`): vira `/` antes de comparar.
versao_instalada() {
  local reg="${1%/cache/$MERCADO}/installed_plugins.json" v
  [ -f "$reg" ] || return 0
  v=$(tr '\n' ' ' < "$reg" 2>/dev/null \
      | sed -n "s/.*\"$NOME@$MERCADO\"[[:space:]]*:[[:space:]]*\\[//p" \
      | sed 's/\].*//' \
      | grep -o '"installPath"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 \
      | sed 's/.*:[[:space:]]*"\(.*\)"$/\1/' | sed 's/\\\\/\//g')
  case "$v" in */"$MERCADO"/"$NOME"/*) v="${v##*/}" ;; *) return 0 ;; esac
  [[ "$v" =~ $VERSAO ]] && printf '%s\n' "$v"
}

# A pasta de versão de `<nome>` em `$1` (marketplace no cache): a instalada, ou a mais alta
# entre as que são versão de verdade. Imprime o arquivo `<versão>/<rel>` se existir.
escolhe_versao() {
  local base="$1" ver d n core suf flag linhas="" i p1 p2 p3 p4
  ver=$(versao_instalada "$base")
  if [ -n "$ver" ] && [ -d "$base/$NOME/$ver" ]; then
    [ -f "$base/$NOME/$ver/$REL" ] && printf '%s\n' "$base/$NOME/$ver/$REL"
    return 0
  fi
  for d in "$base/$NOME"/*; do
    [ -d "$d" ] || continue
    n="${d##*/}"
    [[ "$n" =~ $VERSAO ]] || continue
    core="${n%%[-+]*}"; suf="${n#"$core"}"
    case "$suf" in -*) flag=0 ;; *) flag=1 ;; esac    # pré-release < final
    IFS=. read -r p1 p2 p3 p4 <<< "$core"
    for i in "$p1" "$p2" "${p3:-0}" "${p4:-0}"; do [ "${#i}" -le 8 ] || continue 2; done
    linhas="$linhas$(printf '%08d.%08d.%08d.%08d' $((10#$p1)) $((10#$p2)) $((10#${p3:-0})) $((10#${p4:-0})))|$flag|$n"$'\n'
  done
  [ -n "$linhas" ] || return 0
  n=$(printf '%s' "$linhas" | LC_ALL=C sort | tail -1)
  # A mais alta VÁLIDA manda: se ela não tem o arquivo, versão antiga não o empresta.
  [ -f "$base/$NOME/${n##*|}/$REL" ] && printf '%s\n' "$base/$NOME/${n##*|}/$REL"
}

# O catálogo em `$1/.claude-plugin/marketplace.json` é o DESTE repositório?
catalogo_nosso() {
  local arq="$1/.claude-plugin/marketplace.json"
  [ -f "$arq" ] || return 1
  [ "$(tr '\n' ' ' < "$arq" 2>/dev/null \
       | sed -n 's/^[^"]*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')" = "$MERCADO" ]
}

ACHADO=""
if [ -n "$RAIZ" ]; then
  R=$(cd "$RAIZ" 2>/dev/null && pwd -P)
  # Git Bash devolve `/c/Users/…`, que o Python do chamador não abre: no Windows o caminho
  # sai na forma mista (`C:/Users/…`), que o bash e o Python aceitam. Sem `cygpath`, é POSIX.
  if [ -n "$R" ] && command -v cygpath >/dev/null 2>&1; then R=$(cygpath -m "$R"); fi
  case "$R" in
    */plugins/cache/"$MERCADO"/*)
      # Dentro do cache do NOSSO marketplace: só ele, nunca o vizinho de outro.
      ACHADO=$(escolhe_versao "${R%%/plugins/cache/$MERCADO/*}/plugins/cache/$MERCADO") ;;
    ?*)
      # Fora do cache: só vale se for um checkout deste repositório (catálogo na raiz).
      D="$R"; N=0
      while [ -n "$D" ] && [ "$N" -lt 64 ]; do
        if [ -f "$D/.claude-plugin/marketplace.json" ]; then
          if catalogo_nosso "$D"; then
            [ -f "${R%/*}/$NOME/$REL" ] && ACHADO="${R%/*}/$NOME/$REL"
          fi
          break
        fi
        P="${D%/*}"
        [ "$P" = "$D" ] || [ "$D" = "/" ] && break     # `C:` e `/` não têm pai
        D="${P:-/}"; N=$((N + 1))
      done ;;
  esac
fi
if [ -z "$ACHADO" ]; then
  CACHE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache"
  ACHADO=$(escolhe_versao "$CACHE/$MERCADO")
fi

[ -n "$ACHADO" ] && [ -f "$ACHADO" ] || exit 3
printf '%s\n' "$ACHADO"
