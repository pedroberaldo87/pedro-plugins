#!/usr/bin/env bash
# SessionStart hook (rito ATA) — grava o caminho do transcript da sessão num
# sentinel /tmp para a skill handoff (que NÃO recebe session_id, pois skill ≠ hook)
# achar o .jsonl certo via extract_ata.py --auto.
# Fail-open: qualquer erro → exit 0, nunca atrapalha o início da sessão.
set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"
python3 -c "$(cat <<'PY'
import json, sys, os, hashlib
try:
    data = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].strip() else {}
except Exception:
    data = {}
cwd = data.get("cwd") or os.getcwd()
# hash IDÊNTICO ao de extract_ata.py: sha1(cwd utf-8)[:12]
h = hashlib.sha1(cwd.encode("utf-8")).hexdigest()[:12]
rec = {
    "session_id": data.get("session_id", ""),
    "transcript_path": data.get("transcript_path", ""),
    "cwd": cwd,
    "source": data.get("source", ""),
}
try:
    with open("/tmp/claude-ata-session-%s" % h, "w") as fh:
        json.dump(rec, fh)
except OSError:
    pass
PY
)" "$INPUT" 2>/dev/null || true
exit 0
