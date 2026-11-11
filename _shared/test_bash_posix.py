#!/usr/bin/env python3
"""test_bash_posix.py — cobra o `_shared/bash_posix.py` onde ele escolhe QUEM executar.

O achado 39 do scan 8e9a3ff2: `shutil.which("bash")` no Windows procura primeiro a PASTA
CORRENTE, e no POSIX uma entrada vazia ou "." do PATH faz o mesmo. Um `bash`/`bash.bat`
deixado num repositório aberto era executado (o único crivo era imprimir `VIVO`, que um
programa plantado imprime). Cada check aqui EXECUTA o helper num processo novo, com o
cwd e o PATH montados — o cache do módulo (`_BASH`) não deixa reusar o processo.
"""

import os
import stat
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
NT = os.name == "nt"
NOME_FALSO = "bash.bat" if NT else "bash"
CORPO_FALSO = "@echo off\r\necho VIVO\r\n" if NT else "#!/bin/sh\necho VIVO\n"

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    print("  %s %s" % ("ok  " if cond else "FALHOU", label))
    if not cond:
        FAILS.append(label)


def planta(pasta):
    """Um 'bash' que passa no crivo do helper (imprime VIVO) numa pasta."""
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, NOME_FALSO)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        f.write(CORPO_FALSO)
    os.chmod(caminho, os.stat(caminho).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return caminho


def escolhe(cwd, path):
    """O que `bash_posix()` devolve num processo novo, com este cwd e este PATH."""
    amb = dict(os.environ, PATH=path)
    amb.pop("NoDefaultCurrentDirectoryInExePath", None)
    out = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, %r); from bash_posix import bash_posix; "
         "print(bash_posix() or '')" % AQUI],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=cwd, env=amb, stdin=subprocess.DEVNULL, timeout=60)
    return out.stdout.strip()


def mesmo(a, b, base):
    """Mesmo arquivo; `a` relativo (o que o helper devolve do PATH) vale a partir de `base`."""
    a = a if os.path.isabs(a) else os.path.join(base, a)
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def main():
    print("bash_posix — a pasta corrente nunca escolhe o interpretador")
    raiz = tempfile.mkdtemp(prefix="bash-posix-")
    try:
        projeto = os.path.join(raiz, "projeto-aberto")
        plantado = planta(projeto)
        path_real = os.environ.get("PATH", "")

        # No POSIX o `.` / vazio / relativo no PATH é o que traz a pasta corrente; no
        # Windows ela entra sozinha, sem nenhuma entrada no PATH.
        variantes = [("PATH normal (no Windows a pasta corrente entra sozinha)", path_real)]
        if not NT:
            variantes += [
                ("PATH com '.' na frente", os.pathsep.join([".", path_real])),
                ("PATH com entrada vazia na frente", os.pathsep + path_real),
                ("PATH com a pasta relativa 'bin-local'", os.pathsep.join(["bin-local", path_real])),
            ]
        planta(os.path.join(projeto, "bin-local"))
        for rotulo, path in variantes:
            achado = escolhe(projeto, path)
            check("%s: o bash plantado no cwd NAO e devolvido" % rotulo,
                  not (achado and (mesmo(achado, plantado, projeto) or
                                   mesmo(achado, os.path.join(projeto, "bin-local", NOME_FALSO),
                                         projeto))))

        # O crivo nao pode virar 'recusa tudo': bash em pasta ABSOLUTA do PATH continua valendo.
        if not NT:
            absoluta = os.path.join(raiz, "ferramentas")
            valido = planta(absoluta)
            achado = escolhe(projeto, os.pathsep.join([absoluta, path_real]))
            check("bash numa pasta absoluta do PATH continua sendo escolhido",
                  bool(achado) and mesmo(achado, valido, projeto))

            # E o cwd na lista nao esconde o bash legitimo que vem depois no PATH.
            achado = escolhe(projeto, os.pathsep.join([".", absoluta]))
            check("com '.' antes, o bash legitimo do PATH ainda e achado",
                  bool(achado) and mesmo(achado, valido, projeto))
    finally:
        import shutil
        shutil.rmtree(raiz, ignore_errors=True)

    print()
    if FAILS:
        print("FALHOU (%d de %d):" % (len(FAILS), TOTAL[0]))
        for f in FAILS:
            print("  - %s" % f)
        sys.exit(1)
    print("OK (%d checks)" % TOTAL[0])


if __name__ == "__main__":
    main()
