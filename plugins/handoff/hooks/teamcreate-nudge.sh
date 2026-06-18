#!/usr/bin/env bash
# PreToolUse hook (matcher TeamCreate) — nudge do rito ATA ao montar um clã.
# Lembra de consolidar o PRD antes de espalhar teammates (eles só herdam o
# HANDOFF.md, não o contexto vivo). Fail-open: SEMPRE allow; só injeta o lembrete.
set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"
python3 -c "$(cat <<'PY'
import json, sys
msg = ("Rito ATA: teammates so herdam o que esta no HANDOFF.md (o PRD), nao o contexto "
       "vivo desta sessao. Se ha decisoes/direcionamentos que eles precisam, rode /handoff "
       "(SAVE) primeiro para consolidar PRD + LOG. Ao fim do cla, o /handoff do lead agrega "
       "os transcripts dos teammates no LOG.")
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": msg,
        "additionalContext": msg,
    }
}, ensure_ascii=False))
PY
)" "$INPUT" 2>/dev/null || exit 0
exit 0
