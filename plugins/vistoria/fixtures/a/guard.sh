#!/usr/bin/env bash
# ARQUIVO DE MENTIRA CONGELADO — fixture da letra (a). NÃO CONSERTAR.
# Este guard recusa exatamente a espera que o SKILL.md ao lado manda fazer.
set -euo pipefail

comando=${1:-}

case "$comando" in
  *"suite"*|*"suíte"*)
    echo "recusado: esperar a suíte terminar é proibido nesta sessão" >&2
    exit 2
    ;;
esac

exit 0
