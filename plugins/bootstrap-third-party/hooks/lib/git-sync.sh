#!/usr/bin/env bash
# git-sync.sh — commits and pushes manifest.json changes in the source repo.
#
# Usage: git-sync.sh <commit-message>
#
# Behavior:
#   - Only commits manifest.json (never stages other files)
#   - If no changes in manifest.json → no-op
#   - On push rejection: pull --rebase --autostash → retry push once
#   - On any git failure: visible warning, exit 0 (never blocks caller)
#
# Exit codes:
#   0 — always (errors are warnings, not failures)

set -uo pipefail

PEDRO_PLUGINS_REPO="${PEDRO_PLUGINS_REPO:-$HOME/PROGRAMACAO/PEDRO/pedro-plugins}"
MANIFEST_REL="plugins/bootstrap-third-party/skills/bootstrap-third-party/manifest.json"
COMMIT_MSG="${1:-chore(plugins): snapshot @ $(hostname -s) $(date +%Y-%m-%d)}"

log() { echo "[pedro-plugins/git-sync] $*" >&2; }
info() { echo "[pedro-plugins/git-sync] $*"; }

if [ ! -d "$PEDRO_PLUGINS_REPO/.git" ]; then
  # No source repo — nothing to sync. Silent.
  exit 0
fi

cd "$PEDRO_PLUGINS_REPO" || { log "error: cannot cd to $PEDRO_PLUGINS_REPO"; exit 0; }

# Check if manifest has changes
if git diff --quiet --exit-code "$MANIFEST_REL" 2>/dev/null; then
  # Also check staged changes
  if git diff --cached --quiet --exit-code "$MANIFEST_REL" 2>/dev/null; then
    # No changes at all
    exit 0
  fi
fi

# Stage manifest only
if ! git add "$MANIFEST_REL" 2>&1; then
  log "⚠ git add failed — estado local preservado, sincronização pausada"
  exit 0
fi

# Commit
if ! git commit -m "$COMMIT_MSG" --only "$MANIFEST_REL" >/dev/null 2>&1; then
  # Nothing to commit (race with another process) or hook rejection
  if [ -z "$(git diff --cached --name-only)" ]; then
    # Empty commit — nothing actually changed
    exit 0
  fi
  log "⚠ git commit failed — estado local preservado, sincronização pausada"
  exit 0
fi

info "✓ commit: $COMMIT_MSG"

# Check if there's a remote to push to
if ! git remote get-url origin >/dev/null 2>&1; then
  info "⚠ sem remote 'origin' configurado — commit local apenas"
  exit 0
fi

# Push
PUSH_OUTPUT="$(git push 2>&1)"
PUSH_EXIT=$?

if [ "$PUSH_EXIT" -eq 0 ]; then
  info "✓ pushed"
  exit 0
fi

# Push failed — check if it's a rejection (remote ahead) or network/auth issue
if echo "$PUSH_OUTPUT" | grep -qE "rejected|non-fast-forward"; then
  info "remote avançou — tentando rebase + retry"
  if git pull --rebase --autostash 2>&1 | tail -3; then
    PUSH_OUTPUT="$(git push 2>&1)"
    PUSH_EXIT=$?
    if [ "$PUSH_EXIT" -eq 0 ]; then
      info "✓ pushed (após rebase)"
      exit 0
    fi
  else
    log "⚠ rebase falhou — conflito em $MANIFEST_REL, resolva manualmente:"
    log "   cd $PEDRO_PLUGINS_REPO && git status"
    exit 0
  fi
fi

# Any other failure (no network, SSH, auth)
log "⚠ git push falhou — commit local preservado, próximo sync vai tentar de novo"
log "   motivo: $(echo "$PUSH_OUTPUT" | head -3 | tr '\n' ' ')"
exit 0
