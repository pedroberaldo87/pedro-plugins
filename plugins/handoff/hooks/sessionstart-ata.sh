#!/usr/bin/env bash
# SessionStart hook (rito ATA) — grava o caminho do transcript da sessão num
# sentinel no diretório do usuário (~/.claude/handoff/) para a skill handoff (que NÃO recebe session_id, pois skill ≠ hook)
# achar o .jsonl certo via extract_ata.py --auto.
# Fail-open: qualquer erro → exit 0, nunca atrapalha o início da sessão.
# Sem python3 não há o que rodar aqui — o corpo inteiro do hook é Python.
if ! command -v python3 >/dev/null 2>&1 || ! python3 --version >/dev/null 2>&1; then
  # sem python3 o sentinel do transcript não é gravado e o /handoff --auto perde a
  # descoberta — fala pelos dois canais em vez de calar (o leitor empresta só o aviso)
  . "$(printf '%s' "${0%/*}" | tr '\\' /)/hook-json.sh" 2>/dev/null && hj_avisa "handoff/sessionstart-ata"
  exit 0
fi
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
    # O sentinel é um PONTEIRO que o /handoff --auto segue: mora no diretório do USUÁRIO
    # (0700, arquivo 0600), nunca no temporário compartilhado, onde outro usuário local
    # previa o nome e plantava o arquivo. Mesmo caminho de collect_engine.sentinel_path().
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    pasta = os.path.join(base, "handoff")
    os.makedirs(pasta, mode=0o700, exist_ok=True)
    os.chmod(pasta, 0o700)          # o mode do makedirs passa pelo umask; pasta antiga é apertada
    alvo = os.path.join(pasta, "claude-ata-session-%s" % h)
    # temp + rename: nunca segue um symlink plantado no lugar do alvo, e o arquivo nasce 0600
    tmp = "%s.%d.tmp" % (alvo, os.getpid())
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(rec, fh)
    os.replace(tmp, alvo)
except OSError:
    pass
PY
)" "$INPUT" 2>/dev/null || true
exit 0
