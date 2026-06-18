#!/usr/bin/env bash
# Stop hook (rito ATA) — gate de completude do handoff.
# Quando um PRD (HANDOFF.md) acaba de ser escrito (mtime >= manifest), verifica
# DETERMINISTICAMENTE que ele referencia cada item forte do manifest ([id]) e não
# deixou placeholders do template. Incompleto → decision:block, e o Stop hook
# mantém o Claude trabalhando até completar (cap nativo CLAUDE_CODE_STOP_HOOK_BLOCK_CAP
# evita loop infinito). Fail-open: qualquer erro/edge → exit 0, sem bloquear.
set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"
python3 -c "$(cat <<'PY'
import json, sys, os, glob, hashlib

def ok():
    sys.exit(0)

try:
    data = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].strip() else {}
except Exception:
    ok()

cwd = data.get("cwd") or os.getcwd()
prd_path = os.path.join(cwd, ".claude", "HANDOFF.md")
ata_dir = os.path.join(cwd, ".claude", "ata")
if not os.path.exists(prd_path) or not os.path.isdir(ata_dir):
    ok()
manis = glob.glob(os.path.join(ata_dir, "manifest-*.json"))
if not manis:
    ok()
manifest_path = max(manis, key=os.path.getmtime)
try:
    prd_mtime = os.path.getmtime(prd_path)
    man_mtime = os.path.getmtime(manifest_path)
except OSError:
    ok()
# só age quando o PRD foi (re)escrito DEPOIS do extrator gerar o manifest
if prd_mtime < man_mtime - 1:
    ok()
# não re-disparar para um PRD já aprovado (sentinel por mtime do PRD)
flagh = hashlib.sha1(("%s|%d" % (cwd, int(prd_mtime))).encode()).hexdigest()[:16]
okflag = "/tmp/claude-ata-gate-ok-%s" % flagh
if os.path.exists(okflag):
    ok()
try:
    manifest = json.load(open(manifest_path))
    prd = open(prd_path, encoding="utf-8").read()
except Exception:
    ok()

gate_items = [it for it in manifest.get("items", []) if it.get("gate")]
missing = [it["id"] for it in gate_items if ("[%s]" % it["id"]) not in prd]
PLACEHOLDERS = ["_pendente_", "{1-3 sentences", "{Why this", "{What was discussed",
                "{Concrete actions", "{Por tema", "{VERBATIM", "{Architecture",
                "{Preferences", "{absolute path}", "{YYYY-MM-DD", "LOG-<sessão>.md",
                "<sessão>"]
placeholders = [p for p in PLACEHOLDERS if p in prd]

if not missing and not placeholders:
    try:
        open(okflag, "w").close()
    except OSError:
        pass
    ok()

lines = ["HANDOFF incompleto — o gate do rito ATA travou (o PRD ainda nao esta 100%)."]
if missing:
    lines.append("Itens do LOG NAO referenciados no PRD (cite [id] na secao apropriada): "
                 + ", ".join(missing))
if placeholders:
    lines.append("Placeholders do template ainda nao preenchidos: " + ", ".join(placeholders))
lines.append("Manifest: %s" % manifest_path)
lines.append("Complete o .claude/HANDOFF.md e finalize de novo.")
print(json.dumps({"decision": "block", "reason": "\n".join(lines)}, ensure_ascii=False))
sys.exit(0)
PY
)" "$INPUT" 2>/dev/null || exit 0
exit 0
