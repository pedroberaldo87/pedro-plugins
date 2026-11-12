#!/usr/bin/env python3
"""Suite do pino do fallow — stdlib, sem framework (padrão do repo).

    python3 plugins/fallow/lib/test_fallow_pin.py

P7 · achado 4: o /fallow rodava `npx -y fallow` (a última versão do registro) com o
projeto analisado como diretório de trabalho. O npm lê o `.npmrc` DO PROJETO e prefere
um `node_modules/.bin/fallow` do projeto, então um repositório hostil escolhia o
binário que o /fallow executava. Aqui o `subprocess.run` é trocado por um espião: a
prova é o argv, o diretório e o ambiente que o `npx` receberia — o fallow real não roda.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FAILS = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (" %s" % (extra,) if not cond else ""))
    if not cond:
        FAILS.append(label)


PROJ = os.path.realpath(tempfile.mkdtemp(prefix="fallow-pin-proj-"))
CHAMADAS = []


class _Resp:
    stdout = "{}"
    stderr = ""
    returncode = 0


def espiao(cmd, **kw):
    CHAMADAS.append({"cmd": list(cmd), "cwd": kw.get("cwd"), "env": kw.get("env")})
    return _Resp()


sys.argv = ["audit.py", PROJ]          # o audit.py lê a raiz do argv ao ser importado
import report as R
import audit as A
import fallow_cmd

R.subprocess.run = espiao
A.subprocess.run = espiao

R.run_fallow("dead-code", PROJ)
A.fallow_unused_files()
A.fallow_unused_exports()

check("três chamadas ao npx foram vistas (report + audit x2)", len(CHAMADAS) == 3,
      str(len(CHAMADAS)))

versao = fallow_cmd.FALLOW_VERSION
for c in CHAMADAS:
    cmd = c["cmd"]
    quem = " ".join(cmd[:5])
    pino = [a for a in cmd if re.fullmatch(r"fallow@\d+\.\d+\.\d+", a)]
    check("versão exata fixada no argv (%s)" % quem, len(pino) == 1, str(cmd))
    check("o pino é o FALLOW_VERSION declarado (%s)" % quem,
          bool(versao) and pino == ["fallow@" + versao], "%s vs %s" % (pino, versao))
    check("nenhum `fallow` solto, sem versão (%s)" % quem, "fallow" not in cmd, str(cmd))
    check("scripts de ciclo de vida desligados (%s)" % quem, "--ignore-scripts" in cmd,
          str(cmd))
    cwd = os.path.realpath(c["cwd"]) if c["cwd"] else ""
    dentro = cwd == PROJ or cwd.startswith(PROJ + os.sep)
    check("cwd NÃO é o projeto analisado: o .npmrc dele não vale (%s)" % quem,
          bool(cwd) and not dentro, repr(c["cwd"]))
    check("o projeto vai por -r, absoluto (%s)" % quem,
          "-r" in cmd and os.path.realpath(cmd[cmd.index("-r") + 1]) == PROJ, str(cmd))

# o SKILL.md instrui o agente a rodar o mesmo binário: o pino tem que ser UM só
skill = os.path.join(HERE, "..", "skills", "fallow", "SKILL.md")
with open(skill, encoding="utf-8") as fh:
    texto = fh.read()
soltos = re.findall(r"npx (?:-y |--yes |--ignore-scripts )*fallow(?!@)\b", texto)
check("SKILL.md não manda rodar `npx fallow` sem versão", not soltos, str(soltos[:3]))
fixados = set(re.findall(r"fallow@(\d+\.\d+\.\d+)", texto))
check("SKILL.md usa a mesma versão do código", fixados == {versao}, "%s vs %s" % (fixados, versao))

shutil.rmtree(PROJ, ignore_errors=True)
print("test_fallow_pin: %d falha(s)" % len(FAILS))
sys.exit(1 if FAILS else 0)
