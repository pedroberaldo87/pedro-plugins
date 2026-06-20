#!/usr/bin/env bash
# Stop hook (rito ATA) — gate de completude do handoff.
# Quando um PRD (HANDOFF.md) acaba de ser escrito (mtime >= manifest), verifica
# DETERMINISTICAMENTE três coisas: (a) que ele referencia cada item forte do manifest ([id]);
# (b) que não sobrou placeholder não-preenchido (qualquer {{...}}, marcador único — sem lista
# paralela); (c) gate PROSPECTIVO de forma — todo passo NÃO-trivial de "## Próximos Passos"
# tem os 5 campos do molde (passo "(trivial)" e seção vazia não bloqueiam).
# Incompleto → decision:block, e o Stop hook
# mantém o Claude trabalhando até completar (cap nativo CLAUDE_CODE_STOP_HOOK_BLOCK_CAP
# evita loop infinito). Fail-open: qualquer erro/edge → exit 0, sem bloquear.
set -uo pipefail
INPUT="$(cat 2>/dev/null || true)"
python3 -c "$(cat <<'PY'
import json, sys, os, glob, hashlib, re

def ok():
    sys.exit(0)

try:
    data = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].strip() else {}
except Exception:
    ok()

cwd = data.get("cwd") or os.getcwd()
session_id = data.get("session_id") or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""

# Localiza o handoff por SESSAO. Como o handoff agora "pertence ao projeto", ele
# pode estar fora do cwd (monorepo aninhado, guarda-chuva). O extrator gravou um
# bilhete /tmp/claude-handoff-target-<sid> com o caminho real + o projeto-raiz.
# Casa-se com o manifest da MESMA sessao (exato), nao "o mais recente por mtime".
prd_path = None
manifest_path = None
if session_id:
    try:
        tgt = json.load(open("/tmp/claude-handoff-target-%s" % session_id))
        hp = tgt.get("handoff_path")
        mp = tgt.get("manifest_path")
        # compat: bilhete de versao antiga sem manifest_path -> deriva do project_root
        if not mp and tgt.get("project_root"):
            mp = os.path.join(tgt["project_root"], ".claude", "ata", "manifest-%s.json" % session_id)
        if hp and mp and os.path.exists(hp) and os.path.exists(mp):
            prd_path, manifest_path = hp, mp
    except Exception:
        pass

if not prd_path:
    # Fallback legado: handoff fixo no cwd + manifest mais recente (single-repo
    # sem bilhete = comportamento identico ao de antes).
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
# não re-disparar para um PRD já aprovado (chave = caminho + sessao + mtime do PRD,
# pra dois modulos salvos no mesmo segundo nao compartilharem o flag)
flagh = hashlib.sha1(("%s|%s|%d" % (prd_path, session_id, int(prd_mtime))).encode()).hexdigest()[:16]
okflag = "/tmp/claude-ata-gate-ok-%s" % flagh
if os.path.exists(okflag):
    ok()
try:
    manifest = json.load(open(manifest_path))
    prd = open(prd_path, encoding="utf-8").read()
except Exception:
    ok()

# Se o handoff foi (re)escrito por OUTRA sessao (header "Session: <sid>" != a nossa),
# ele nao e nosso — outra sessao no mesmo projeto avulso sobrescreveu o HANDOFF.md.
# Nao bloquear: a sessao dona tem o proprio gate/manifest. (Handoff legado sem header
# Session: => sem match => valida normalmente, como antes.)
if session_id:
    mship = re.search(r"(?m)^Session:\s*(\S+)", prd)
    if mship and mship.group(1) != session_id:
        ok()

gate_items = [it for it in manifest.get("items", []) if it.get("gate")]
missing = [it["id"] for it in gate_items if ("[%s]" % it["id"]) not in prd]

# (1) Placeholders nao-preenchidos: marcador unico {{...}} detectado por regex generica.
# Sem mais lista paralela hardcoded pra dessincronizar do template do SKILL.md.
placeholders = sorted(set(re.findall(r"\{\{[^{}]+\}\}", prd)))

# (2) Gate PROSPECTIVO de FORMA: todo passo NAO-trivial de "## Proximos Passos" precisa dos 5
# campos do molde. Parse conservador — so cobra itens com header "### " (o molde); secao vazia
# ou so com prosa ("nada pendente") NAO bloqueia; passo marcado "(trivial)" no titulo dispensa.
REQUIRED = ["**Ação:**", "**Critério de pronto:**", "**Problema:**",
            "**Arquivos prováveis:**", "**Decisão em aberto:**"]
prospective = []
sec = re.search(r"##\s+Próximos Passos\s*\n(.*?)(?=\n##\s|\Z)", prd, re.S)
if sec:
    body_all = sec.group(1)
    heads = list(re.finditer(r"(?m)^###\s+(.+?)\s*$", body_all))
    for i, h in enumerate(heads):
        title = h.group(1)
        if re.search(r"\(trivial\)", title, re.I):
            continue
        seg = body_all[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(body_all)]
        for lbl in REQUIRED:
            mm = re.search(re.escape(lbl) + r"[ \t]*(.*)", seg)
            val = mm.group(1).strip() if mm else ""
            if not val or "{{" in val:
                prospective.append('passo "%s": falta "%s"' % (title.strip()[:48], lbl.strip("*:")))

if not missing and not placeholders and not prospective:
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
    lines.append("Placeholders do template ainda nao preenchidos (substitua os {{...}}): "
                 + ", ".join(placeholders))
if prospective:
    lines.append("Proximos Passos sem os 5 campos do molde (preencha, ou marque o passo como "
                 "'(trivial)' se ele dispensa): " + "; ".join(prospective))
lines.append("Manifest: %s" % manifest_path)
lines.append("Complete o %s e finalize de novo." % prd_path)
print(json.dumps({"decision": "block", "reason": "\n".join(lines)}, ensure_ascii=False))
sys.exit(0)
PY
)" "$INPUT" 2>/dev/null || exit 0
exit 0
