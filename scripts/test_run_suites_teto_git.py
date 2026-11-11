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
tetos = [os.path.realpath(t) for t in os.environ.get("GIT_CEILING_DIRECTORIES", "").split(os.pathsep) if t]
for var in ("TESTE_TMP_DO_SISTEMA", "TESTE_TMP_DO_MACOS"):
    if not os.environ.get(var):
        continue
    esperado = os.path.realpath(os.environ[var])
    if esperado not in tetos:
        print("GIT_CEILING_DIRECTORIES=%r não inclui %s=%r" % (tetos, var, esperado))
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

    # D) `realpath` do teto. Com TMPDIR que é LINK para um repo alheio (no macOS o `/var`
    # do temporário é link para `/private/var`), o git resolve sozinho os tetos que vêm
    # antes de qualquer entrada vazia; mas quem tem uma entrada vazia na lista (o git a
    # trata como "não resolva os links dos seguintes") faz o teto do rodador valer
    # SEM resolução. Só o `realpath` do rodador fecha esse caso: sem ele o git sobe pelo
    # link até o repo alheio. Medido com git 2.50.1; sem entrada vazia o git já resolveria
    # sozinho e o `realpath` seria invisível.
    elo = os.path.join(obra, "elo-para-alheio")
    try:
        if os.name != "posix":
            raise NotImplementedError                # a semântica da entrada vazia é de POSIX
        os.symlink(alheio, elo)
    except (OSError, NotImplementedError):
        elo = None
    if elo:
        env = dict(os.environ, TMPDIR=elo, TMP=elo, TEMP=elo, GIT_CEILING_DIRECTORIES=os.pathsep)
        r = subprocess.run([sys.executable, RODADOR, "--py", suite_a], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, start_new_session=True, cwd=RAIZ, env=env)
        check("TMPDIR que é link para um repo alheio, com entrada vazia no teto do dono: "
              "o teto do rodador vale resolvido (realpath)", r.returncode == 0,
              (r.stdout + r.stderr)[-400:])

    # B) O teto inclui o temporário do SISTEMA, não só o da esteira: no macOS o
    # `mktemp -d` sem modelo ignora o TMPDIR e cai nele.
    suite_b = os.path.join(obra, "test_teto_sistema.py")
    with open(suite_b, "w", encoding="utf-8") as fh:
        fh.write(SUITE_TETO_DO_SISTEMA)
    # TMPDIR aponta para outra pasta de propósito: se o teto só olhasse o TMPDIR, o
    # temporário "de verdade" do macOS ficaria de fora e este caso reprovaria.
    outro = os.path.join(obra, "outro-tmp")
    os.makedirs(outro)
    env_b = {"TMPDIR": outro, "TMP": outro, "TEMP": outro, "TESTE_TMP_DO_SISTEMA": outro}
    if sys.platform == "darwin":
        # É o `mktemp -d` sem modelo que ignora o TMPDIR; quem responde é o getconf.
        env_b["TESTE_TMP_DO_MACOS"] = subprocess.run(
            ["getconf", "DARWIN_USER_TEMP_DIR"], capture_output=True, text=True,
            stdin=subprocess.DEVNULL).stdout.strip()
    codigo, saida = roda_rodador(suite_b, env_b)
    check("o teto inclui o temporário do sistema (o do TMPDIR e, no macOS, o do getconf)", codigo == 0, saida[-400:])

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
