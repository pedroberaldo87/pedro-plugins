#!/bin/bash
# PreToolUse hook: blocks deploy commands if the relevant tests fail.
# Fires on every Bash tool call; only acts when the command looks like a deploy.
# Exit 0 = allow, Exit 2 = block (message shown to Claude)
#
# Two modes:
#   1. Per-app gate (preferred) — if the project has scripts/run_app_tests.sh,
#      run it for the app(s) being deployed. That script owns venv + scope +
#      e2e exclusion, so a monorepo deploy of one app only runs that app's
#      tests in the right interpreter (not the whole repo on the system python).
#   2. Legacy whole-suite — projects without that script keep the old behavior.

# Fail-open if jq is missing (marketplace convention — patterns.md:28). Resolve
# via PATH instead of a hardcoded Homebrew path so the gate actually fires on
# Intel macs / Linux / fresh bootstrap machines, not just this one.
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

if [ -z "$COMMAND" ] || [ -z "$CWD" ]; then
  exit 0
fi

# ============================================================
# Detect if this is a deploy command
# ============================================================
is_deploy=false

# PM2
if echo "$COMMAND" | grep -qE '(^|\s)pm2\s+(restart|reload|deploy|start)'; then
  is_deploy=true
fi

# Docker compose (build + up implies deploy)
if echo "$COMMAND" | grep -qE '(docker-compose|docker compose).*(--build|-d)'; then
  is_deploy=true
fi

# Vercel / Netlify
if echo "$COMMAND" | grep -qE '(vercel\s+--prod|netlify\s+deploy.*--prod)'; then
  is_deploy=true
fi

# deploy.sh / Makefile deploy target
if echo "$COMMAND" | grep -qE '(\.\/deploy\.sh|bash deploy\.sh|sh deploy\.sh|make\s+(deploy|prod|release))'; then
  is_deploy=true
fi

# SSH-based deploy patterns
if echo "$COMMAND" | grep -qE 'ssh\s+.*\s+(git pull|pm2|docker|deploy)'; then
  is_deploy=true
fi

if [ "$is_deploy" = false ]; then
  exit 0
fi

# Cache verde (fail-open): suite já passou 100% neste exato tree-hash → pula a
# re-execução. Qualquer edição muda o hash e invalida; vermelho nunca grava.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/green-cache.sh" ] && . "$SCRIPT_DIR/green-cache.sh"

# ============================================================
# Mode 1 — per-app gate (preferred when the project provides it)
# ============================================================
GATE="$CWD/scripts/run_app_tests.sh"
if [ -x "$GATE" ] && echo "$COMMAND" | grep -qE 'deploy\.sh'; then
  # Apps listed after deploy.sh, trimmed at the first shell separator; flags out.
  ARGS=$(echo "$COMMAND" | sed -E 's/.*deploy\.sh//; s/[;&|].*//')
  ARGS=$(echo "$ARGS" | tr ' ' '\n' | grep -vE '^(-|$)' | tr '\n' ' ')

  # An app "has tests" if it has a pytest dir OR is a Node app that declares a
  # real `test` script (vitest/jest) — those tests live in __tests__/colocated,
  # with no tests/ dir for the prober to find. run_app_tests.sh runs the right
  # runner per app; this just decides whether to invoke it.
  node_has_test_script() {
    [ -f "$1" ] || return 1
    local t
    t=$(jq -r '.scripts.test // empty' "$1" 2>/dev/null)
    [ -n "$t" ] && ! echo "$t" | grep -q 'no test specified'
  }
  app_has_tests() {
    [ -d "$CWD/tests/$1" ] && return 0
    [ -d "$CWD/apps/$1/tests" ] && return 0
    node_has_test_script "$CWD/apps/$1/package.json"
  }
  discover_apps() {
    { for d in "$CWD"/tests/*/; do [ -d "$d" ] && basename "$d"; done
      for d in "$CWD"/apps/*/tests; do [ -d "$d" ] && basename "$(dirname "$d")"; done
      for p in "$CWD"/apps/*/package.json; do
        node_has_test_script "$p" && basename "$(dirname "$p")"
      done
    } | sort -u
  }

  if [ -z "$(echo "$ARGS" | tr -d '[:space:]')" ]; then
    APPS=$(discover_apps)   # full deploy → gate every app that has tests
  else
    APPS="$ARGS"
  fi

  FAILED=""
  RAN=""
  for app in $APPS; do
    app_has_tests "$app" || continue
    if type green_cache_check >/dev/null 2>&1 && green_cache_check "$CWD" "app:$app"; then
      RAN="$RAN $app(cache)"
      continue
    fi
    RAN="$RAN $app"
    if ! ( cd "$CWD" && bash scripts/run_app_tests.sh "$app" ); then
      FAILED="$FAILED $app"
    else
      type green_cache_mark >/dev/null 2>&1 && green_cache_mark "$CWD" "app:$app" ship-hook
    fi
  done

  if [ -n "$FAILED" ]; then
    echo "🚫 Deploy bloqueado — testes do(s) app(s) falhando:$FAILED" >&2
    echo "" >&2
    echo "Rode local e corrija:  bash scripts/run_app_tests.sh <app>" >&2
    echo "(testes que precisam de produção ficam fora do gate via @pytest.mark.e2e)" >&2
    exit 2
  fi
  [ -n "$RAN" ] && echo "✅ Gate de testes ok:$RAN" >&2
  exit 0
fi

# ============================================================
# Mode 2 — legacy whole-suite runner (projects without the per-app gate)
# ============================================================
TEST_CMD=""
TEST_RUNNER=""
TEST_DIR=""
SEARCH_DIR="$CWD"

while [ "$SEARCH_DIR" != "/" ]; do
  # package.json with a real test script
  if [ -f "$SEARCH_DIR/package.json" ]; then
    HAS_TEST=$(jq -r '.scripts.test // empty' "$SEARCH_DIR/package.json" 2>/dev/null)
    if [ -n "$HAS_TEST" ] && ! echo "$HAS_TEST" | grep -q 'no test specified'; then
      TEST_CMD="CI=true npm test"
      TEST_RUNNER="npm test"
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # pytest
  if [ -f "$SEARCH_DIR/pyproject.toml" ] || [ -f "$SEARCH_DIR/pytest.ini" ] || [ -f "$SEARCH_DIR/setup.cfg" ]; then
    if command -v pytest &>/dev/null; then
      TEST_CMD="pytest"
      TEST_RUNNER="pytest"
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # Cargo
  if [ -f "$SEARCH_DIR/Cargo.toml" ]; then
    if command -v cargo &>/dev/null; then
      TEST_CMD="cargo test"
      TEST_RUNNER="cargo test"
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # Go
  if [ -f "$SEARCH_DIR/go.mod" ]; then
    if command -v go &>/dev/null; then
      TEST_CMD="go test ./..."
      TEST_RUNNER="go test"
      TEST_DIR="$SEARCH_DIR"
      break
    fi
  fi

  # Makefile with test target
  if [ -f "$SEARCH_DIR/Makefile" ] && grep -q '^test:' "$SEARCH_DIR/Makefile" 2>/dev/null; then
    TEST_CMD="make test"
    TEST_RUNNER="make test"
    TEST_DIR="$SEARCH_DIR"
    break
  fi

  SEARCH_DIR=$(dirname "$SEARCH_DIR")
done

if [ -z "$TEST_CMD" ]; then
  echo "⚠️  pre-deploy-test-check: nenhum test runner detectado — deploy permitido sem verificação." >&2
  exit 0
fi

# Green cache: whole suite already passed at this exact tree state → allow.
if type green_cache_check >/dev/null 2>&1 && green_cache_check "$TEST_DIR" full; then
  echo "✅ Cache verde: suite já passou 100% neste tree-hash — deploy liberado sem re-execução." >&2
  exit 0
fi

# Run the tests
TEST_OUTPUT=$(cd "$TEST_DIR" && eval "$TEST_CMD" 2>&1)
TEST_EXIT=$?

if [ $TEST_EXIT -ne 0 ]; then
  TRUNCATED=$(echo "$TEST_OUTPUT" | tail -40)
  echo -e "🚫 Deploy bloqueado — testes falhando ($TEST_RUNNER em $TEST_DIR)\n\nCorreja os testes antes de fazer deploy. Falhas:\n\n$TRUNCATED" >&2
  exit 2
fi

type green_cache_mark >/dev/null 2>&1 && green_cache_mark "$TEST_DIR" full ship-hook

exit 0
