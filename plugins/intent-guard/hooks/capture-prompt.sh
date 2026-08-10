#!/usr/bin/env bash
set -uo pipefail
# UserPromptSubmit — grava o prompt do usuário VERBATIM no caderno. Zero LLM, zero
# julgamento (quem separa pedido de conversa é o juiz, no gate seguinte).
# Fail-open: QUALQUER erro → exit 0; nunca atrapalha o prompt.
INPUT="$(cat 2>/dev/null || true)"
# Anti-reentrância: os gates chamam `claude -p` como juiz, e essa sub-invocação
# dispara ESTE hook com o prompt do JUIZ. Sem o guard, o caderno do usuário se
# auto-polui com os próprios prompts internos do plugin (visto no smoke E2E).
[ -n "${INTENT_GUARD_INTERNAL:-}" ] && exit 0
MODE_FILE="$HOME/.claude/intent-guard/mode"
[ -f "$MODE_FILE" ] && [ "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" = "off" ] && exit 0
PY="$(command -v python3)"
if [ -z "$PY" ] || ! "$PY" --version >/dev/null 2>&1; then
  # sem python3 o caderno fica sem o pedido — fala pelos dois canais em vez de calar
  # (o corpo deste hook é Python embutido; o leitor hook-json.sh empresta só o aviso)
  . "$(printf '%s' "${0%/*}" | tr '\\' /)/hook-json.sh" 2>/dev/null && hj_avisa "intent-guard/capture-prompt"
  exit 0
fi
LEDGER="${CLAUDE_PLUGIN_ROOT}/lib/ledger.py"
[ -f "$LEDGER" ] || exit 0
printf '%s' "$INPUT" | "$PY" -c '
import json, os, subprocess, sys
ledger = sys.argv[1]
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
prompt = data.get("prompt") or ""
cwd = data.get("cwd") or os.getcwd()
sid = data.get("session_id") or ""
if not prompt.strip():
    sys.exit(0)
d = subprocess.run([sys.executable, ledger, "resolve-dir", "--cwd", cwd],
                   capture_output=True, text=True, timeout=10).stdout.strip()
if d and os.path.exists(os.path.join(d, "off")):
    sys.exit(0)
subprocess.run([sys.executable, ledger, "record-raw", "--cwd", cwd,
                "--session", sid, "--text-stdin"],
               input=prompt, text=True, timeout=10)
' "$LEDGER" 2>/dev/null || true
exit 0
