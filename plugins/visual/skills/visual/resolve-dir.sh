#!/bin/bash
# resolve-dir.sh — decide ONDE um artefato de skill é salvo, no projeto de quem usa.
#
# ⚠️ FONTE DA VERDADE: `_shared/resolve-dir.sh`. As cópias dentro dos plugins são
# vendoradas por `scripts/sync-shared.sh` — editar a cópia deixa as outras defasadas.
#
# Cascata de 3 níveis (para no primeiro que bater):
#   1. Raiz do repositório git  → <raiz-git>/.claude/<subdir>
#   2. Projeto reconhecido por marcador (package.json, CLAUDE.md, etc.),
#      subindo a partir do cwd e parando ANTES de $HOME → <dir>/.claude/<subdir>
#   3. Fallback Desktop → ~/Desktop/claude-<subdir>
#
# Uso:   resolve-dir.sh <cwd> [subdir]
#        subdir default = "visual". Passe "plans" para o store de planos
#        (ver lib/plan_state.py) ou "archify" para os diagramas do /archify —
#        mesma cascata, outro diretório. Cada família de artefato tem a própria
#        pasta: misturar diagrama com relatório e plano é o que faz o usuário
#        não achar o que gerou ontem.
# Saída: caminho absoluto do diretório-alvo no stdout (já criado com mkdir -p).
#
# Quem chama: o hook pre-exitplan-visualize.sh, a invocação manual do /visual, o
# motor de plano e a skill /archify — todos por aqui, pra nunca divergirem.

CWD="${1:-$PWD}"
SUB="${2:-visual}"
DESKTOP="$HOME/Desktop/claude-$SUB"

resolve() {
  # Nível 1 — raiz do repositório git (robusto: cobre worktrees/submodules)
  if [ -d "$CWD" ]; then
    git_root=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$git_root" ]; then
      printf '%s\n' "$git_root/.claude/$SUB"
      return
    fi
  fi

  # Nível 2 — sobe procurando marcador de projeto, parando antes de $HOME e /
  dir="$CWD"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "$HOME" ]; do
    if [ -e "$dir/package.json" ] || [ -e "$dir/CLAUDE.md" ] || \
       [ -e "$dir/pyproject.toml" ] || [ -e "$dir/Cargo.toml" ] || \
       [ -e "$dir/go.mod" ] || [ -d "$dir/graphify-out" ] || [ -d "$dir/.git" ]; then
      printf '%s\n' "$dir/.claude/$SUB"
      return
    fi
    dir=$(dirname "$dir")
  done

  # Nível 3 — fallback Desktop (comportamento legado)
  printf '%s\n' "$DESKTOP"
}

TARGET=$(resolve)
mkdir -p "$TARGET" 2>/dev/null
printf '%s\n' "$TARGET"
