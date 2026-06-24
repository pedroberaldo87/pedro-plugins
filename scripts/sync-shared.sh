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

# Cada spec é "destino::arquivo" — qual arquivo de _shared/ vai pra qual subpasta.
# Mapa explícito (não "todos os FILES em todos os CONSUMERS") porque consumidores
# diferentes vendoram arquivos diferentes: a engine de coleta vai pro lib/ do
# handoff+project-doc; a tabela R8 vai pro references/ do sovai+qa-loop.
SPECS=(
  "plugins/handoff/lib::collect_engine.py"
  "plugins/project-doc/lib::collect_engine.py"
  "plugins/sovai/skills/sovai/references::r8-tiers.md"
  "plugins/qa-loop/skills/qa-loop/references::r8-tiers.md"
)

check_mode=0
[[ "${1:-}" == "--check" ]] && check_mode=1

status=0
for spec in "${SPECS[@]}"; do
  dest="${spec%%::*}"
  f="${spec##*::}"
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
    mkdir -p "$ROOT/$dest"
    cp "$src" "$dst"
    echo "vendored: _shared/$f -> $dest/$f"
  fi
done

if [[ $check_mode -eq 1 ]]; then
  [[ $status -eq 0 ]] && echo "OK: cópias vendored idênticas a _shared/"
else
  echo "OK: vendoring concluído (${#SPECS[@]} cópia(s))."
fi
exit $status
