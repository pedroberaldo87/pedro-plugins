#!/bin/bash
# Post-Edit/Write hook: runs lint and type-check on edited files
# Supports: JS/TS (ESLint + tsc), Python (ruff + mypy)
# Exit 0 = ok, Exit 2 = block (feedback shown to Claude)
#
# Key design decisions:
# - Searches UPWARD from the edited file for configs (handles monorepos)
# - Supports jsconfig.json for JS type-checking (not just tsconfig.json)
# - ESLint and tsc searches are independent (different roots possible)
# - Python: ruff for lint, mypy for types (both optional)
#
# Portability: jq is resolved via PATH. If it isn't there, the hook fails OPEN
# (exit 0) instead of falling back to a macOS-only path — a missing linter must
# never block an edit, and we don't assume any particular install location.

# Kill-switch e teto (2026-07-27). Este hook devolvia indefinidamente: o caso
# ruim não é o erro que o Claude conserta, é o que ele NÃO consegue consertar
# (regra do linter que briga com o arquivo, falso-positivo da ferramenta) — aí a
# sessão ficava presa e a única saída era editar este script.
[ "${LINT_GATE:-1}" = "0" ] && exit 0

# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "lint-and-typecheck"; exit 0; }

INPUT=$(cat)
FILE_PATH=$(hj_campo "$INPUT" tool_input.file_path)
SESSION_ID=$(hj_campo "$INPUT" session_id)

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

ERRORS=""

# ============================================================
# JS / TS files
# ============================================================
if [[ "$FILE_PATH" =~ \.(ts|tsx|js|jsx|mjs|cjs)$ ]]; then

  # --- ESLint: walk up to find nearest eslint binary ---
  DIR=$(dirname "$FILE_PATH")
  ESLINT_BIN=""
  while [ "$DIR" != "/" ]; do
    if [ -f "$DIR/node_modules/.bin/eslint" ]; then
      ESLINT_BIN="$DIR/node_modules/.bin/eslint"
      break
    fi
    DIR=$(dirname "$DIR")
  done

  if [ -n "$ESLINT_BIN" ]; then
    # ESLint v9 looks for its config relative to cwd, not the file path.
    # cd to the directory where the binary (and config) live so it finds eslint.config.mjs.
    ESLINT_ROOT=$(dirname "$(dirname "$(dirname "$ESLINT_BIN")")")
    # Capture the linter's exit code BEFORE the pipe — `$(cmd | head)` would
    # report head's status (always 0), so the error block never fired.
    LINT_RAW=$(cd "$ESLINT_ROOT" && "$ESLINT_BIN" "$FILE_PATH" --no-warn-ignored 2>&1); RC=$?
    LINT_OUTPUT=$(printf '%s\n' "$LINT_RAW" | head -30)
    if [ "$RC" -ne 0 ] && [ -n "$LINT_OUTPUT" ]; then
      ERRORS="${ERRORS}--- ESLint ---\n${LINT_OUTPUT}\n\n"
    fi
  fi

  # --- Type checking: walk up to find nearest tsconfig.json or jsconfig.json ---
  DIR=$(dirname "$FILE_PATH")
  TSC_CONFIG=""
  TSC_ROOT=""
  while [ "$DIR" != "/" ]; do
    if [ -f "$DIR/tsconfig.json" ]; then
      TSC_CONFIG="tsconfig.json"
      TSC_ROOT="$DIR"
      break
    elif [ -f "$DIR/jsconfig.json" ]; then
      TSC_CONFIG="jsconfig.json"
      TSC_ROOT="$DIR"
      break
    fi
    DIR=$(dirname "$DIR")
  done

  # Find tsc binary: walk up from TSC_ROOT (or file dir if no config)
  TSC_BIN=""
  SEARCH_DIR="${TSC_ROOT:-$(dirname "$FILE_PATH")}"
  while [ "$SEARCH_DIR" != "/" ]; do
    if [ -f "$SEARCH_DIR/node_modules/.bin/tsc" ]; then
      TSC_BIN="$SEARCH_DIR/node_modules/.bin/tsc"
      break
    fi
    SEARCH_DIR=$(dirname "$SEARCH_DIR")
  done

  if [ -n "$TSC_BIN" ] && [ -n "$TSC_CONFIG" ]; then
    TSC_RAW=$(cd "$TSC_ROOT" && "$TSC_BIN" --noEmit -p "$TSC_CONFIG" --pretty 2>&1); RC=$?
    TSC_OUTPUT=$(printf '%s\n' "$TSC_RAW" | head -30)
    if [ "$RC" -ne 0 ] && [ -n "$TSC_OUTPUT" ]; then
      ERRORS="${ERRORS}--- TypeScript ---\n${TSC_OUTPUT}\n"
    fi
  fi
fi

# ============================================================
# Python files
# ============================================================
if [[ "$FILE_PATH" =~ \.py$ ]]; then

  # --- Ruff: lint ---
  if command -v ruff &>/dev/null; then
    RUFF_RAW=$(ruff check "$FILE_PATH" 2>&1); RC=$?
    RUFF_OUTPUT=$(printf '%s\n' "$RUFF_RAW" | head -30)
    if [ "$RC" -ne 0 ] && [ -n "$RUFF_OUTPUT" ]; then
      ERRORS="${ERRORS}--- Ruff ---\n${RUFF_OUTPUT}\n\n"
    fi
  fi

  # --- Mypy: type check (only if mypy is installed and config exists) ---
  DIR=$(dirname "$FILE_PATH")
  HAS_MYPY_CONFIG=false
  while [ "$DIR" != "/" ]; do
    if [ -f "$DIR/mypy.ini" ] || [ -f "$DIR/setup.cfg" ] || [ -f "$DIR/pyproject.toml" ]; then
      HAS_MYPY_CONFIG=true
      break
    fi
    DIR=$(dirname "$DIR")
  done

  if [ "$HAS_MYPY_CONFIG" = true ] && command -v mypy &>/dev/null; then
    MYPY_RAW=$(mypy "$FILE_PATH" --no-error-summary 2>&1); RC=$?
    MYPY_OUTPUT=$(printf '%s\n' "$MYPY_RAW" | head -30)
    if [ "$RC" -ne 0 ] && [ -n "$MYPY_OUTPUT" ]; then
      ERRORS="${ERRORS}--- Mypy ---\n${MYPY_OUTPUT}\n"
    fi
  fi
fi

# ============================================================
# Report
# ============================================================
if [ -n "$ERRORS" ]; then
  # Teto por (arquivo, sessão): 3 devoluções e depois vira aviso. O erro continua
  # visível — só para de prender. Sem session_id não dá pra escopar o teto, então
  # bloqueia como antes (o comportamento seguro é o que já existia).
  if [ -n "$SESSION_ID" ]; then
    FHASH=$(printf '%s' "$FILE_PATH" | cksum | cut -d' ' -f1)
    COUNT_FILE="${TMPDIR:-/tmp}/claude-lint-gate-$(id -u)-${SESSION_ID}-${FHASH}"
    MAX_NUDGES=3
    COUNT=0
    [ -f "$COUNT_FILE" ] && COUNT="$(tr -d '[:space:]' < "$COUNT_FILE" 2>/dev/null)"
    case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
    if [ "$COUNT" -ge "$MAX_NUDGES" ]; then
      echo -e "⚠️ Lint/type errors persistem em $FILE_PATH após $MAX_NUDGES devoluções — liberando a edição pra não prender a sessão. Os erros continuam de pé:\n\n$ERRORS" >&2
      exit 0
    fi
    echo $((COUNT + 1)) > "$COUNT_FILE" 2>/dev/null
    find "${TMPDIR:-/tmp}" -maxdepth 1 -name "claude-lint-gate-$(id -u)-*" -mtime +1 -delete 2>/dev/null
    echo -e "Lint/type errors after edit to $FILE_PATH:\n\n$ERRORS\n(aviso $((COUNT + 1))/${MAX_NUDGES} · desligar: LINT_GATE=0)" >&2
    exit 2
  fi
  echo -e "Lint/type errors after edit to $FILE_PATH:\n\n$ERRORS" >&2
  exit 2
fi

exit 0
