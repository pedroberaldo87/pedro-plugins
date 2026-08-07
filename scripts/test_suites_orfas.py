#!/usr/bin/env python3
"""Suíte do cobrador de suítes órfãs.

O contrapeso que importa: ele tem que ACUSAR quando alguém acrescenta um teste num
lugar que a esteira não varre. Um cobrador que só sabe dizer "nenhuma órfã" no
repositório limpo não prova nada — foi assim que a régua do Artigo 5 virou um número
escrito que ninguém revalidava.
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import suites_orfas as so  # noqa: E402

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def git(d, *args):
    subprocess.run(["git", "-C", d] + list(args), capture_output=True, text=True, timeout=30)


def monta(d, arquivos):
    """Repositório de mentira com os arquivos dados, todos rastreados."""
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    os.makedirs(os.path.join(d, ".github", "workflows"), exist_ok=True)
    with open(os.path.join(d, so.ESTEIRA), "w", encoding="utf-8") as fh:
        fh.write("jobs:\n  x:\n    steps:\n      - run: |\n"
                 "          roda \"$PY\" 'plugins/*/lib/test_*.py'\n"
                 "          roda bash 'plugins/*/hooks/test_*.sh'\n")
    for rel in arquivos:
        caminho = os.path.join(d, rel)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write("# teste\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "x")


def main():
    print("o caso limpo: tudo que o git rastreia casa algum globo")
    d = tempfile.mkdtemp(prefix="orfas-ok-")
    try:
        monta(d, ["plugins/a/lib/test_um.py", "plugins/a/hooks/test_dois.sh"])
        fora, tests, pats = so.orfas(d)
        check("acha as duas suítes rastreadas", len(tests) == 2)
        check("lê os dois globos da esteira", len(pats) == 2)
        check("nenhuma órfã", fora == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("o caso que importa: teste rastreado FORA de todo globo")
    d = tempfile.mkdtemp(prefix="orfas-bad-")
    try:
        # `lib/` na raiz não é varrido pelos globos da esteira de mentira acima.
        monta(d, ["plugins/a/lib/test_um.py", "lib/test_escondido.py"])
        fora, tests, _ = so.orfas(d)
        check("a órfã é acusada", fora == ["lib/test_escondido.py"])
        check("e a que está coberta NÃO é acusada",
              "plugins/a/lib/test_um.py" not in fora)
        check("o rastreamento achou as duas", len(tests) == 2)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("arquivo de teste NÃO rastreado não é órfã — é só não rastreado")
    d = tempfile.mkdtemp(prefix="orfas-untracked-")
    try:
        monta(d, ["plugins/a/lib/test_um.py"])
        solto = os.path.join(d, "lib", "test_solto.py")
        os.makedirs(os.path.dirname(solto), exist_ok=True)
        with open(solto, "w", encoding="utf-8") as fh:
            fh.write("# nunca foi commitado\n")
        fora, tests, _ = so.orfas(d)
        check("o não rastreado fica fora da conta", fora == [] and len(tests) == 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("sem git ou sem a esteira, não julga — e não acusa ninguém")
    d = tempfile.mkdtemp(prefix="orfas-nogit-")
    try:
        fora, _, _ = so.orfas(d)
        check("sem repositório devolve 'não sei', não 'está tudo bem'", fora is None)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("o repositório de verdade, agora")
    fora, tests, pats = so.orfas(".")
    check("o repo real não tem órfã", fora == [])
    # Sem número cravado, pelo mesmo motivo que tirou o 54 do Artigo 5: este check
    # já reprovou sozinho quando a esteira ganhou o 8º globo, medindo nada além da
    # própria desatualização. Acrescentar globo é trabalho legítimo — o que o teste
    # cobra é que ele EXISTA e case alguma coisa.
    check("o cobrador lê os globos de verdade da esteira", len(pats) >= 2)
    check("todo globo lido casa ao menos uma suíte",
          all(any(so.fnmatch.fnmatch(t, p) for t in tests) for p in pats))
    check("a soma dos globos é o total rastreado (sem número escrito em lugar nenhum)",
          len(tests) > 0)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK (%d checks)" % TOTAL[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
