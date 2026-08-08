#!/usr/bin/env python3
"""Bancada do vazamento_check — o cobrador acusa quem pode deixar filho para trás?

O caso que dá sentido à suíte é o ÚLTIMO: a chamada com `input=` NÃO pode ser acusada
por falta de `stdin`, porque passar os dois é `ValueError` no Python. Sem esse caso o
cobrador acusaria trabalho correto, e ninguém acredita em cobrador que grita à toa.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vazamento_check as vc  # noqa: E402

FALHAS = []


def check(nome, cond):
    print(("  ok   " if cond else "  FAIL ") + nome)
    if not cond:
        FALHAS.append(nome)


def monta(d, arquivos):
    for rel, txt in arquivos.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(txt)


def varre_em(d):
    """Aponta o cobrador para uma árvore de mentira e devolve o que ele achou."""
    antes = vc.RAIZ
    vc.RAIZ = d
    try:
        return vc.varre(d)
    finally:
        vc.RAIZ = antes


def main():
    print("vazamento_check")

    d = tempfile.mkdtemp(prefix="vaz-nu-")
    try:
        monta(d, {"scripts/x.py": "import subprocess\nsubprocess.run(['git','status'])\n"})
        r = varre_em(d)
        check("disparo sem nenhum cuidado é acusado", len(r) == 1)
        check("a acusação nomeia os dois que faltam",
              r and "stdin=" in r[0]["falta"] and "start_new_session" in r[0]["falta"])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vaz-meio-")
    try:
        monta(d, {"scripts/x.py":
                  "import subprocess\n"
                  "subprocess.run(['git','status'], stdin=subprocess.DEVNULL)\n"})
        r = varre_em(d)
        check("com stdin mas sem grupo próprio, ainda é acusado", len(r) == 1)
        check("e a acusação diz que falta só o grupo",
              r and "stdin=" not in r[0]["falta"] and "start_new_session" in r[0]["falta"])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vaz-ok-")
    try:
        monta(d, {"scripts/x.py":
                  "import subprocess\n"
                  "subprocess.run(['git','status'], stdin=subprocess.DEVNULL,\n"
                  "               start_new_session=True)\n"})
        check("disparo com os dois cuidados passa", varre_em(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vaz-os-")
    try:
        monta(d, {"scripts/x.py": "import os\nos.system('ls')\n"})
        r = varre_em(d)
        check("os.system é acusado sempre — não aceita cuidado nenhum",
              len(r) == 1 and "subprocess" in r[0]["falta"])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vaz-isento-")
    try:
        monta(d, {"scripts/x.py":
                  "import subprocess\n"
                  "# vaza-ok: o comando é um literal que sempre termina\n"
                  "subprocess.run(['true'])\n"})
        check("a isenção com motivo escrito na linha de cima vale", varre_em(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # O caso que impede o falso-positivo: `input=` e `stdin=` juntos é ValueError no
    # Python, então quem passa `input` já controla o stdin e não pode ser cobrado por
    # ele. Sem este caso o cobrador mandaria escrever código que estoura.
    d = tempfile.mkdtemp(prefix="vaz-input-")
    try:
        monta(d, {"scripts/x.py":
                  "import subprocess\n"
                  "subprocess.run(['cat'], input='oi', start_new_session=True)\n"})
        check("chamada com input= não é cobrada por stdin", varre_em(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # O LADO JS. O motor de slides, o do gauntlet e o renderizador do archify são Node,
    # e `stdio: 'inherit'` herda o terminal pelo mesmo motivo do `stdin` ausente em
    # Python. O terceiro caso é o que pegou o falso-negativo real: o valor chega por
    # DEFAULT (`options.stdio || 'inherit'`), e a primeira versão deste cobrador não via.
    d = tempfile.mkdtemp(prefix="vaz-js-")
    try:
        monta(d, {"plugins/p/bin/x.mjs":
                  "import {spawnSync} from 'node:child_process';\n"
                  "spawnSync('node', ['a.js'], { stdio: 'inherit' });\n"})
        r = varre_em(d)
        check("em JS, stdio inherit é acusado", len(r) == 1 and "inherit" in r[0]["falta"])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vaz-js-ok-")
    try:
        monta(d, {"plugins/p/bin/x.mjs":
                  "import {spawnSync} from 'node:child_process';\n"
                  "spawnSync('node', ['a.js'], { stdio: ['ignore','inherit','inherit'] });\n"})
        check("em JS, stdin fechado com saída herdada passa", varre_em(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vaz-js-def-")
    try:
        monta(d, {"plugins/p/bin/x.mjs":
                  "import {spawnSync} from 'node:child_process';\n"
                  "spawnSync(cmd, args, {\n"
                  "  cwd: opts.cwd,\n"
                  "  stdio: opts.stdio || 'inherit',\n"
                  "});\n"})
        check("em JS, o inherit que chega por DEFAULT também é acusado",
              len(varre_em(d)) == 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="vaz-real-")
    try:
        monta(d, {"plugins/p/lib/y.py": "import subprocess\nsubprocess.Popen(['ls'])\n"})
        r = varre_em(d)
        check("varre plugins/ também, não só scripts/", len(r) == 1)
        check("e reconhece Popen como disparo", r and r[0]["chamada"] == "subprocess.Popen")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
