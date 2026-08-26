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

# Uso: casa_da_doc <raiz> [parte...]
casa_da_doc() {
  local raiz="${1%/}"; shift
  [ -z "$raiz" ] && raiz="."
  local escolhida="$raiz/docs"
  if [ ! -d "$raiz/docs" ] && [ -d "$raiz/.claude/docs" ]; then  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
    escolhida="$raiz/.claude/docs"  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
  elif [ -d "$raiz/docs" ] && [ -d "$raiz/.claude/docs" ] \
       && ! _casa_tem_md "$raiz/docs" && _casa_tem_md "$raiz/.claude/docs"; then  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
    # Exceção medida (outro projeto, 2026-08-26): docs/ de outro uso, sem nenhum
    # .md, escondia a casa habitada — a VELHA com a doc de verdade responde.
    escolhida="$raiz/.claude/docs"  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
  fi
  local caminho="$escolhida"
  local parte
  for parte in "$@"; do caminho="$caminho/$parte"; done
  printf '%s\n' "$caminho"
}
