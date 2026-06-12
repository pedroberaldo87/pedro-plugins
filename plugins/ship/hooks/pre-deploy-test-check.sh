#!/bin/bash
# PreToolUse hook: blocks deploy commands if the test suite has failures
# Fires on every Bash tool call; only acts when the command looks like a deploy
# Exit 0 = allow, Exit 2 = block (message shown to Claude)

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | /opt/homebrew/bin/jq -r '.tool_input.command // empty')
CWD=$(echo "$INPUT" | /opt/homebrew/bin/jq -r '.cwd // empty')

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

# ============================================================
# Deploy detected — run tests first
# ============================================================
TEST_CMD=""
TEST_RUNNER=""
TEST_DIR=""
SEARCH_DIR="$CWD"

while [ "$SEARCH_DIR" != "/" ]; do
  # package.json with a real test script
  if [ -f "$SEARCH_DIR/package.json" ]; then
    HAS_TEST=$(/opt/homebrew/bin/jq -r '.scripts.test // empty' "$SEARCH_DIR/package.json" 2>/dev/null)
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

# Run the tests
TEST_OUTPUT=$(cd "$TEST_DIR" && eval "$TEST_CMD" 2>&1)
TEST_EXIT=$?

if [ $TEST_EXIT -ne 0 ]; then
  TRUNCATED=$(echo "$TEST_OUTPUT" | tail -40)
  echo -e "🚫 Deploy bloqueado — testes falhando ($TEST_RUNNER em $TEST_DIR)\n\nCorreja os testes antes de fazer deploy. Falhas:\n\n$TRUNCATED" >&2
  exit 2
fi

exit 0
