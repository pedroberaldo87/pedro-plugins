#!/bin/bash
# resolve-dir.sh — decide ONDE os HTMLs da skill /visual são salvos.
#
# Cascata de 3 níveis (para no primeiro que bater):
#   1. Raiz do repositório git  → <raiz-git>/.claude/visual
#   2. Projeto reconhecido por marcador (package.json, CLAUDE.md, etc.),
#      subindo a partir do cwd e parando ANTES de $HOME → <dir>/.claude/visual
#   3. Fallback Desktop → ~/Desktop/claude-visual
#
# Uso:   resolve-dir.sh <cwd>
# Saída: caminho absoluto do diretório-alvo no stdout (já criado com mkdir -p).
#
# Single source of truth: tanto o hook pre-exitplan-visualize.sh quanto a
# invocação manual do /visual chamam ESTE script, pra nunca divergirem.

CWD="${1:-$PWD}"
DESKTOP="$HOME/Desktop/claude-visual"

resolve() {
  # Nível 1 — raiz do repositório git (robusto: cobre worktrees/submodules)
  if [ -d "$CWD" ]; then
    git_root=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$git_root" ]; then
      printf '%s\n' "$git_root/.claude/visual"
      return
    fi
  fi

  # Nível 2 — sobe procurando marcador de projeto, parando antes de $HOME e /
  dir="$CWD"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "$HOME" ]; do
    if [ -e "$dir/package.json" ] || [ -e "$dir/CLAUDE.md" ] || \
       [ -e "$dir/pyproject.toml" ] || [ -e "$dir/Cargo.toml" ] || \
       [ -e "$dir/go.mod" ] || [ -d "$dir/graphify-out" ] || [ -d "$dir/.git" ]; then
      printf '%s\n' "$dir/.claude/visual"
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
