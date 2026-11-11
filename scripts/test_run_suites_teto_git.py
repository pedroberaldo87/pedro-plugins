#!/usr/bin/env python3
"""Suíte do TETO DE GIT do run_suites.py — o temporário da suíte não pode ser de um repo alheio.

Por que existe: uma suíte que cria uma pasta temporária e pergunta ao git "onde está o
projeto?" (`rev-parse --show-toplevel`, ou o hook que faz isso por ela) espera ouvir
"em lugar nenhum". Se algum diretório ACIMA do temporário for um repositório — um `.git`
esquecido na pasta de temporários do sistema, um `TMPDIR` dentro de um clone, um `/tmp`
versionado —, o git sobe até lá e responde com esse repositório. Num Mac de trabalho isso
derrubou onze suítes verdes no CI (`test_grao_de_modulo`, `test_resolve_dir`, os hooks de
plano…), todas por dependerem do que existe fora do repositório de quem roda.

O consertador é o rodador: ele passa `GIT_CEILING_DIRECTORIES` às suítes, apontando o
temporário do sistema e a pasta-mãe da casa própria de cada suíte. O git não sobe para
dentro deles; repositório criado DENTRO do temporário (o que as suítes de git montam)
continua sendo achado normalmente.

    python3 scripts/test_run_suites_teto_git.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RODADOR = os.path.join(RAIZ, "scripts", "run_suites.py")
ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ✓ %s" % nome)
    else:
        falhas += 1
        print("  ✗ %s%s" % (nome, ("\n      %s" % detalhe) if detalhe else ""))


# A suíte de mentira, que roda DENTRO do rodador. Ela é escrita em disco porque o
# rodador só sabe disparar arquivos.
SUITE_ISOLADA = r'''
import os, subprocess, sys, tempfile
d = tempfile.mkdtemp()                       # cai na casa própria que o rodador deu
r = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True,
                   text=True, stdin=subprocess.DEVNULL)
if r.returncode == 0:
    print("o git achou um repositório ACIMA do temporário: " + r.stdout.strip())
    sys.exit(1)
# Um repositório criado DENTRO do temporário tem que continuar sendo achado: o teto
# fecha a subida, não o git.
subprocess.run(["git", "init", "-q", d], check=True, stdin=subprocess.DEVNULL)
r = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True,
                   text=True, stdin=subprocess.DEVNULL)
if r.returncode != 0:
    print("o teto escondeu o repositório do próprio temporário")
    sys.exit(1)
'''

SUITE_TETO_DO_SISTEMA = r'''
import os, sys
esperado = os.path.realpath(os.environ["TESTE_TMP_DO_SISTEMA"])
tetos = [os.path.realpath(t) for t in os.environ.get("GIT_CEILING_DIRECTORIES", "").split(os.pathsep) if t]
if esperado not in tetos:
    print("GIT_CEILING_DIRECTORIES=%r não inclui o temporário do sistema %r" % (tetos, esperado))
    sys.exit(1)
'''


def roda_rodador(suite, env_extra):
    env = dict(os.environ, **env_extra)
    env.pop("GIT_CEILING_DIRECTORIES", None)
    r = subprocess.run([sys.executable, RODADOR, "--py", suite], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                       start_new_session=True, cwd=RAIZ, env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


print("run_suites — o git não sobe do temporário da suíte para um repositório alheio")

obra = tempfile.mkdtemp(prefix="teto-obra-")     # onde moram as suítes de mentira
alheio = tempfile.mkdtemp(prefix="teto-alheio-")  # o "temporário do sistema" com um repo dentro
try:
    subprocess.run(["git", "init", "-q", alheio], check=True, stdin=subprocess.DEVNULL)

    # A) TMPDIR da esteira é filho de um repositório alheio (o `.git` esquecido).
    suite_a = os.path.join(obra, "test_isolada.py")
    with open(suite_a, "w", encoding="utf-8") as fh:
        fh.write(SUITE_ISOLADA)
    codigo, saida = roda_rodador(suite_a, {"TMPDIR": alheio, "TMP": alheio, "TEMP": alheio})
    check("temporário dentro de um repo alheio: a suíte não enxerga o repo", codigo == 0,
          saida[-400:])

    # B) O teto inclui o temporário do SISTEMA, não só o da esteira: no macOS o
    # `mktemp -d` sem modelo ignora o TMPDIR e cai nele.
    suite_b = os.path.join(obra, "test_teto_sistema.py")
    with open(suite_b, "w", encoding="utf-8") as fh:
        fh.write(SUITE_TETO_DO_SISTEMA)
    codigo, saida = roda_rodador(suite_b, {"TESTE_TMP_DO_SISTEMA": tempfile.gettempdir()})
    check("o teto inclui o temporário do sistema", codigo == 0, saida[-400:])

    # C) Teto que o dono já pôs não é pisado: o do rodador entra junto.
    suite_c = os.path.join(obra, "test_teto_do_dono.py")
    with open(suite_c, "w", encoding="utf-8") as fh:
        fh.write(
            "import os, sys\n"
            "tetos = os.environ.get('GIT_CEILING_DIRECTORIES', '').split(os.pathsep)\n"
            "sys.exit(0 if os.environ['TESTE_TETO_DO_DONO'] in tetos else 1)\n")
    dono = os.path.join(obra, "teto-do-dono")
    env = dict(os.environ, TESTE_TETO_DO_DONO=dono, GIT_CEILING_DIRECTORIES=dono)
    r = subprocess.run([sys.executable, RODADOR, "--py", suite_c], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                       start_new_session=True, cwd=RAIZ, env=env)
    check("o teto que o dono já pôs é preservado", r.returncode == 0, (r.stdout + r.stderr)[-400:])
finally:
    shutil.rmtree(obra, ignore_errors=True)
    shutil.rmtree(alheio, ignore_errors=True)

print()
if falhas:
    print("FALHOU: %d" % falhas)
    sys.exit(1)
print("test_run_suites_teto_git: %d checagens verdes" % ok)
