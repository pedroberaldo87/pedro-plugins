# shellcheck shell=bash
# Onde mora a doc canônica de um projeto — a versão bash.
#
# Por que existe: o caminho da doc estava cravado em mais de cem pontos, e a
# casa mudou (`docs/` na raiz, visível ao humano; `.claude/docs/` só como  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
# retrocompatibilidade). Quem precisa do caminho pergunta aqui.
#
# O contrato em prosa (e o irmão em Python) estão em `_shared/casa-da-doc.md`.
#
#   source "$(dirname "$0")/lib-casa-da-doc.sh"
#   CASA=$(casa_da_doc "$RAIZ")                      # a pasta
#   ARQ=$(casa_da_doc "$RAIZ" architecture.md)       # o arquivo dentro dela

# _casa_tem_md <pasta> — a pasta tem pelo menos um .md no primeiro nível (casa habitada)
_casa_tem_md() {
  set -- "$1"/*.md
  [ -e "$1" ]
}

# _casa_tem_doc_da_familia <pasta> — tem documento DESTA família: abre com frontmatter
# e traz `project:` no cabeçalho. É a marca que separa o documento das skills da prosa
# que o dono escreveu à mão — lida, nunca adivinhada. Irmão de `_tem_doc_da_familia`.
_casa_tem_doc_da_familia() {
  local arq
  for arq in "$1"/*.md; do
    [ -e "$arq" ] || continue
    [ "$(head -n 1 "$arq" 2>/dev/null | tr -d "\r")" = "---" ] || continue
    if sed -n "2,40p" "$arq" 2>/dev/null | sed "/^---[[:space:]]*$/q" | grep -q "^project:"; then
      return 0
    fi
  done
  return 1
}

# Uso: casa_da_doc <raiz> [parte...]
casa_da_doc() {
  local raiz="${1%/}"; shift
  [ -z "$raiz" ] && raiz="."
  local escolhida="$raiz/docs"
  local velha="$raiz/.claude/docs"  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
  if [ ! -d "$raiz/docs" ] && [ -d "$velha" ]; then
    escolhida="$velha"
  elif [ -d "$raiz/docs" ] && [ -d "$velha" ]; then
    if ! _casa_tem_md "$raiz/docs" && _casa_tem_md "$velha"; then
      # Exceção 1 (medido em 2026-08-26): docs/ de outro uso, sem nenhum
      # .md, escondia a casa habitada — a VELHA com a doc de verdade responde.
      escolhida="$velha"
    elif _casa_tem_md "$velha" && ! _casa_tem_doc_da_familia "$raiz/docs" && _casa_tem_doc_da_familia "$velha"; then
      # Exceção 2 (medido em 2026-08-28): as DUAS habitadas, cada uma com um
      # tipo de documento — a prosa do dono na nova, os documentos das skills na
      # velha. Sem este desempate as ferramentas liam a nova, não achavam a marca
      # que procuram, e declaravam o projeto SEM documentação nenhuma, em silêncio.
      escolhida="$velha"
    fi
  fi
  local caminho="$escolhida"
  local parte
  for parte in "$@"; do caminho="$caminho/$parte"; done
  printf '%s\n' "$caminho"
}
