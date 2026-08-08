#!/usr/bin/env bash
# Suíte do resolve-skill.sh — bash puro, sem framework (padrão do repo).
#
# O que ela protege é o defeito que o script existe para matar: skill que mudou de
# plugin e continuou sendo pedida pelo nome antigo. O cache é montado à mão em cada
# caso, porque o defeito real morava justamente numa borda dele — versão velha de um
# plugin ainda servindo a skill que já mudou de casa.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
ALVO="$HERE/resolve-skill.sh"
OK=0; FALHA=0

check() {
  if [ "$2" = "$3" ]; then OK=$((OK+1)); printf '  ok   %s\n' "$1"
  else FALHA=$((FALHA+1)); printf '  FAIL %s\n       esperado=%s\n       obtido  =%s\n' "$1" "$3" "$2"; fi
}

# Um cache de mentira, com o layout real: <cache>/<marketplace>/<plugin>/<versao>/skills/<skill>/
BASE=$(mktemp -d "${TMPDIR:-/tmp}/resolve-skill-test.XXXXXX")
trap 'rm -rf "$BASE"' EXIT
export CLAUDE_CONFIG_DIR="$BASE"
CACHE="$BASE/plugins/cache"

cria() {  # cria <marketplace> <plugin> <versao> <skill>
  mkdir -p "$CACHE/$1/$2/$3/skills/$4"
  printf -- '---\nname: %s\n---\n' "$4" > "$CACHE/$1/$2/$3/skills/$4/SKILL.md"
}

echo "[o caso simples]"
cria mkt alfa 1.0.0 fazer-coisa
check "acha o plugin que serve a skill" "$(bash "$ALVO" fazer-coisa)" "alfa:fazer-coisa"

echo
echo "[skill que não existe em lugar nenhum]"
saida=$(bash "$ALVO" nao-existe); rc=$?
check "não imprime nada" "$saida" ""
check "sai com 3, o mesmo contrato do resolve-plugin" "$rc" "3"

echo
echo "[a skill mudou de plugin — o defeito medido em 2026-08-08]"
# `velho` serviu a skill até a 2.0.0 e parou; `novo` a serve desde a 0.1.0.
# O cache guarda as duas versões de `velho`, e é isso que fazia a busca ingênua
# devolver os dois plugins — com o nome antigo ganhando por vir primeiro.
cria mkt velho 1.0.0 mudou
cria mkt velho 2.0.0 mudou
mkdir -p "$CACHE/mkt/velho/3.0.0/skills/outra"   # 3.0.0 é a ativa, e NÃO tem a skill
cria mkt novo 0.1.0 mudou
check "a versão ATIVA do plugin velho não serve mais, então ele não conta" \
      "$(bash "$ALVO" mudou)" "novo:mudou"

echo
echo "[ordenação de versão é numérica, não alfabética]"
mkdir -p "$CACHE/mkt/gama/9.0.0/skills/some"
cria mkt gama 10.0.0 fica
check "10.0.0 é mais alta que 9.0.0" "$(bash "$ALVO" fica)" "gama:fica"

echo
echo "[cache inexistente não derruba]"
CLAUDE_CONFIG_DIR="$BASE/nao-existe" saida=$(bash "$ALVO" qualquer); rc=$?
check "sem cache: silêncio e código 3" "$saida:$rc" ":3"

echo
printf '%d ok · %d falha(s)\n' "$OK" "$FALHA"
[ "$FALHA" -eq 0 ]
