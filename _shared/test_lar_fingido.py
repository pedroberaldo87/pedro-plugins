#!/usr/bin/env python3
"""Suíte da receita de fingir o lar — e o cobrador de quem finge à mão.

Duas coisas aqui. A primeira é o comportamento das duas metades (Python e bash):
as quatro variáveis do lar saem juntas, senão o Windows ignora o lar fingido. A
segunda é a varredura — receita sem cobrador vira a segunda cópia de sempre.

    python3 _shared/test_lar_fingido.py
"""

import glob
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import lar_fingido  # noqa: E402
from bash_posix import bash_posix  # noqa: E402

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


# ── os três arquivos do contrato existem ───────────────────────────────────

print("\n[o contrato — prosa, Python e bash, os três]")

for nome in ("lar-fingido.md", "lar_fingido.py", "lib-lar-fingido.sh"):
    check("%s existe em _shared" % nome, os.path.isfile(os.path.join(AQUI, nome)))

# ── a metade Python ────────────────────────────────────────────────────────

print("\n[Python — as quatro variáveis do lar saem juntas]")

env = lar_fingido.ambiente("/lar/de/mentira", PATH="/bin")
check("HOME aponta pro lar fingido", env["HOME"] == "/lar/de/mentira")
check("USERPROFILE também (é ele que o Windows lê primeiro)",
      env["USERPROFILE"] == "/lar/de/mentira", env.get("USERPROFILE"))
check("HOMEDRIVE vazio e HOMEPATH no lar (o 2º caminho do Windows)",
      env["HOMEDRIVE"] == "" and env["HOMEPATH"] == "/lar/de/mentira")
check("o extra do chamador entra", env["PATH"] == "/bin")
check("o resto do ambiente continua lá", "PATH" in env and len(env) > 4)

# E o que interessa de verdade: o filho resolve o `~` para o lar fingido — a
# prova que o `HOME` sozinho não dá no Windows.
r = subprocess.run([sys.executable, "-c",
                    "import os;print(os.path.expanduser('~'))"],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", stdin=subprocess.DEVNULL, start_new_session=True,
                   env=lar_fingido.ambiente(os.path.join(RAIZ, "nao-existe-lar")))
check("o filho resolve o ~ para o lar fingido",
      r.stdout.strip() == os.path.join(RAIZ, "nao-existe-lar"), r.stdout.strip())

# ── a metade bash ──────────────────────────────────────────────────────────

print("\n[bash — a mesma receita, mesmo resultado]")

BASH = bash_posix()
if BASH is None:
    check("bash POSIX disponível", False, "(sem bash — a metade bash não foi medida)")
else:
    prova = (
        'source "%s/lib-lar-fingido.sh"\n'
        'lar_fingido /lar/de/mentira env | grep -E "^(HOME|USERPROFILE|HOMEDRIVE|HOMEPATH)=" | sort\n'
    ) % AQUI
    r = subprocess.run([BASH, "-c", prova], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    saiu = r.stdout.strip().splitlines()
    check("lar_fingido põe as quatro no comando que roda",
          saiu == ["HOME=/lar/de/mentira", "HOMEDRIVE=",
                   "HOMEPATH=/lar/de/mentira", "USERPROFILE=/lar/de/mentira"], repr(saiu))

    prova2 = (
        'source "%s/lib-lar-fingido.sh"\n'
        'lar_fingido_exporta /outro/lar\n'
        'env | grep -E "^(HOME|USERPROFILE|HOMEPATH)=" | sort\n'
    ) % AQUI
    r2 = subprocess.run([BASH, "-c", prova2], capture_output=True, text=True,
                        encoding="utf-8", errors="replace",
                        stdin=subprocess.DEVNULL, start_new_session=True)
    saiu2 = r2.stdout.strip().splitlines()
    check("lar_fingido_exporta vale do ponto em diante",
          saiu2 == ["HOME=/outro/lar", "HOMEPATH=/outro/lar",
                    "USERPROFILE=/outro/lar"], repr(saiu2))

# ── o cobrador: ninguém finge o lar à mão ──────────────────────────────────

print("\n[cobrador — quem troca HOME sem a receita reprova]")

ALVOS = ("plugins/*/lib/test_*.py", "plugins/*/hooks/test_*.py",
         "plugins/*/hooks/test_*.sh", "plugins/*/lib/test_*.sh",
         "scripts/*.py", "_shared/test_*.py", ".claude/hooks/test_*.sh")
# `HOME=` no começo da linha ou depois de espaço/`;`/`(`/`{` — a atribuição.
# `"$HOME/x"` e `FAKEHOME=` não casam, e não devem: o que reprova é fingir.
AMAO = re.compile(r'(^|[\s;({|])(HOME|USERPROFILE|HOMEPATH)=')
NOSSOS = ("lar_fingido.py", "lib-lar-fingido.sh", "test_lar_fingido.py")

achados = []
for pat in ALVOS:
    for caminho in sorted(glob.glob(os.path.join(RAIZ, pat))):
        if os.path.basename(caminho) in NOSSOS:
            continue
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for n, linha in enumerate(fh, 1):
                if AMAO.search(linha) and "lar-fingido: ok" not in linha:
                    achados.append("%s:%d" % (os.path.relpath(caminho, RAIZ), n))

check("nenhuma suíte finge o lar à mão", not achados,
      "\n       " + "\n       ".join(achados))

print("\n%d passou · %d falhou" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
