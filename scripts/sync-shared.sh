#!/usr/bin/env bash
# sync-shared.sh — vendora _shared/ para dentro de cada plugin consumidor.
#
# Por que vendoring e não import em runtime: o Claude Code isola plugins na
# instalação — só plugins/<nome>/ vai pro cache, sem variável cross-plugin. O
# código compartilhado é COPIADO antes do commit (o "build" deste monorepo).
# Fonte-da-verdade = _shared/; as cópias nos plugins são derivadas.
#
# Uso:
#   scripts/sync-shared.sh           # vendora (copia _shared/ -> cada plugin)
#   scripts/sync-shared.sh --check   # NÃO copia; falha (exit 1) se houver drift
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/_shared"

# subpasta de destino (relativa à raiz do repo) por plugin consumidor
CONSUMERS=(
  "plugins/handoff/lib"
  "plugins/project-doc/lib"
)
FILES=("collect_engine.py")

check_mode=0
[[ "${1:-}" == "--check" ]] && check_mode=1

status=0
for dest in "${CONSUMERS[@]}"; do
  [[ $check_mode -eq 1 ]] || mkdir -p "$ROOT/$dest"
  for f in "${FILES[@]}"; do
    src="$SRC/$f"
    dst="$ROOT/$dest/$f"
    if [[ ! -f "$src" ]]; then
      echo "ERRO: fonte ausente: _shared/$f" >&2
      exit 2
    fi
    if [[ $check_mode -eq 1 ]]; then
      if ! cmp -s "$src" "$dst"; then
        echo "DRIFT: $dest/$f difere de _shared/$f"
        status=1
      fi
    else
      cp "$src" "$dst"
      echo "vendored: _shared/$f -> $dest/$f"
    fi
  done
done

if [[ $check_mode -eq 1 ]]; then
  [[ $status -eq 0 ]] && echo "OK: cópias vendored idênticas a _shared/"
else
  echo "OK: vendoring concluído (${#CONSUMERS[@]} plugin(s))."
fi
exit $status
