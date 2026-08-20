# shellcheck shell=bash
# Onde mora a doc canônica de um projeto — a versão bash.
#
# Por que existe: o caminho da doc estava cravado em mais de cem pontos, e a
# casa mudou (`docs/` na raiz, visível ao humano; `.claude/docs/` só como
# retrocompatibilidade). Quem precisa do caminho pergunta aqui.
#
# O contrato em prosa (e o irmão em Python) estão em `_shared/casa-da-doc.md`.
#
#   source "$(dirname "$0")/lib-casa-da-doc.sh"
#   CASA=$(casa_da_doc "$RAIZ")                      # a pasta
#   ARQ=$(casa_da_doc "$RAIZ" architecture.md)       # o arquivo dentro dela

# Uso: casa_da_doc <raiz> [parte...]
casa_da_doc() {
  local raiz="${1%/}"; shift
  [ -z "$raiz" ] && raiz="."
  local escolhida="$raiz/docs"
  if [ ! -d "$raiz/docs" ] && [ -d "$raiz/.claude/docs" ]; then
    escolhida="$raiz/.claude/docs"
  fi
  local caminho="$escolhida"
  local parte
  for parte in "$@"; do caminho="$caminho/$parte"; done
  printf '%s\n' "$caminho"
}
