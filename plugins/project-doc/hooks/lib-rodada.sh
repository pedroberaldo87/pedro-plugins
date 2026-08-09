#!/bin/bash
# lib-rodada.sh — qual rodada de doc cabe, decidida por medida e não por prosa.
#
# Os três hooks que falam de doc defasada mandavam o dono escolher entre a rodada
# curta (a incremental) e a completa (a que minera do zero) por um parágrafo de
# critérios. Ninguém escolhe sem medir. Aqui o pattern_check mede a idade da doc
# mais atrasada e devolve a rodada JÁ escolhida, com o número que a sustentou.
#
# O NOME DE INVOCAÇÃO SE DESCOBRE. O medidor devolve o NOME da skill (`doc` ou
# `doc-touch`); quem manda o dono rodar precisa de `<plugin>:<skill>`, e esse
# prefixo não se escreve à mão — as duas skills já mudaram de plugin uma vez, e
# o nome escrito virou pedido de skill inexistente. Quem resolve é o
# `resolve-skill.sh` do project-skills, achado por NOME com o resolve-plugin.sh.
#
# Uso:  rodada_doc "<projeto>"   →  define RODADA_CMD e RODADA_MOTIVO
# Fail-open: python3 ausente/quebrado → a rodada curta, sem número; resolvedor
# ausente → o nome cru da skill, que ao menos nomeia o que rodar.

# Mede o atraso e escolhe a rodada. Devolve o NOME da skill em RODADA_CMD.
_rodada_medir() {
  local proj="$1"
  local py pc out
  py=$(command -v python3 2>/dev/null) || return 0
  [ -n "$py" ] || return 0
  "$py" --version >/dev/null 2>&1 || return 0
  pc="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/pattern_check.py"
  [ -f "$pc" ] || return 0
  out=$("$py" "$pc" --rodada "$proj" 2>/dev/null) || return 0
  [ -n "$out" ] || return 0
  RODADA_CMD=$(printf '%s' "$out" | cut -f1)
  RODADA_MOTIVO=$(printf '%s' "$out" | cut -f3)
  [ -n "$RODADA_CMD" ] || RODADA_CMD="doc-touch"
  return 0
}

# O nome de invocação de uma skill, descoberto. Saída: `<plugin>:<skill>` quando
# o resolvedor acha, o nome cru quando não.
rodada_nome() {
  local skill="$1" dir rs full
  dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  rs=$("$dir/resolve-plugin.sh" project-skills lib/resolve-skill.sh 2>/dev/null)
  if [ -n "$rs" ]; then
    full=$(bash "$rs" "$skill" 2>/dev/null)
    [ -n "$full" ] && skill="$full"
  fi
  printf '%s' "$skill"
}

rodada_doc() {
  RODADA_CMD="doc-touch"
  RODADA_MOTIVO="atraso não medido (sem python3 ou sem o medidor)"
  _rodada_medir "$1"
  RODADA_CMD=$(rodada_nome "$RODADA_CMD")
  return 0
}
