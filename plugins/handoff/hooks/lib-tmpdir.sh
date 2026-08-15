#!/bin/sh
# lib-tmpdir.sh — o diretório temporário DO SISTEMA, resolvido num lugar só.
#
# Por que existe: hook que escreve `/tmp/...` literal grava no lugar errado em
# máquina onde o temporário não é `/tmp` — no Git Bash do Windows o temporário é
# a pasta Temp da conta, e `/tmp` pode não existir nem ser gravável. Quem grava
# sentinel de sessão pergunta aqui em vez de assumir.
#
# ⚠️ FONTE DA VERDADE: `_shared/lib-tmpdir.sh`. As cópias dentro dos plugins são
# vendoradas por `scripts/sync-shared.sh` — editar a cópia deixa as outras defasadas.
#
# Uso:  . "$(dirname "$0")/lib-tmpdir.sh"
#       SENTINELA="$(td_tmpdir)/claude-algo-$SESSION_ID"

# td_tmpdir — TMPDIR quando definido, senão `/tmp`. Devolve o caminho com as
# barras invertidas do Windows viradas para a barra normal (o mesmo tratamento
# que `scripts/test_paths_normalize.sh` já trava para a raiz do plugin) e SEM
# barra final, porque quem chama concatena `/nome` em seguida.
td_tmpdir() {
  # TMPDIR, TMP, TEMP, e só então `/tmp`. O Windows define TMP e TEMP e NÃO define
  # TMPDIR: com só o primeiro na cascata, o Git Bash caía no `/tmp` — que ali é
  # caminho do SHELL, não do sistema. Quem recebia esse caminho e era nativo (o
  # `python3` do Windows) resolvia `/tmp/x` como `C:\tmp\x`, que não existe, e o
  # arquivo nascia num lugar que quem escreveu não conseguia mais achar.
  _td_dir=${TMPDIR:-${TMP:-${TEMP:-/tmp}}}
  _td_dir=$(printf '%s' "$_td_dir" | tr '\\' /)
  while [ "$_td_dir" != "/" ] && [ "${_td_dir%/}" != "$_td_dir" ]; do
    _td_dir=${_td_dir%/}
  done
  [ -n "$_td_dir" ] || _td_dir=/tmp
  # A cascata acima ainda cai no `/tmp` do SHELL quando NENHUMA das três está
  # definida — foi o que aconteceu no runner do Windows (medido em 2026-08-15:
  # `mktemp -d "$(td_tmpdir)"/ig-cap-XXXXXX` devolveu `/tmp/ig-cap-P0Q4jT`, e o
  # `python3` nativo que recebeu esse caminho por STDIN o resolveu como
  # `C:\tmp\...`). `cygpath` só existe onde há essa tradução a fazer, e traduz
  # tanto o `/tmp` do shell quanto um caminho que já é do Windows.
  if command -v cygpath >/dev/null 2>&1; then
    _td_win=$(cygpath -m "$_td_dir" 2>/dev/null)
    [ -n "$_td_win" ] && _td_dir=${_td_win%/}
  fi
  printf '%s' "$_td_dir"
}
