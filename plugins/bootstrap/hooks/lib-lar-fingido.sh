# shellcheck shell=bash
# A receita de FINGIR O LAR para um processo filho — a versão bash.
#
# Por que existe: trocar só `HOME` finge o lar no Unix e NÃO finge no Windows —
# o `expanduser` do Python lê `USERPROFILE` primeiro, e o filho vai escrever no
# lar REAL de quem roda a suíte. As quatro variáveis andam juntas.
#
# O contrato em prosa (e o irmão em Python) estão em `_shared/lar-fingido.md`.
#
#   source "$(dirname "$0")/lib-lar-fingido.sh"
#   printf '%s' "$PAYLOAD" | lar_fingido "$TMP/home" bash "$HOOK"
#   lar_fingido "$TMP/home" env -u CLAUDE_CONFIG_DIR bash "$BLOCO"

# Roda o comando com o lar fingido. Uso: lar_fingido <dir> <comando...>
lar_fingido() {
  local lar="$1"; shift
  HOME="$lar" USERPROFILE="$lar" HOMEDRIVE="" HOMEPATH="$lar" "$@"
}

# Exporta o lar fingido para o resto do script. Uso: lar_fingido_exporta <dir>
lar_fingido_exporta() {
  export HOME="$1" USERPROFILE="$1" HOMEDRIVE="" HOMEPATH="$1"
}
