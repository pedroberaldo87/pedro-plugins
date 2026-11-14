#!/usr/bin/env python3
"""Suíte da escolha de projeto do handoff quando a sessão edita mais de um.

A contagem de edições não diz de quem é a missão: quem conserta a ferramenta edita mais
nela do que no projeto que pediu o conserto. A ordem é cwd → único com plano aberto →
contagem, e só a contagem marca `project_ambiguous` (a skill pergunta).

    python3 plugins/handoff/lib/test_collect_scope.py
"""

import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from collect_engine import infer_scope  # noqa: E402

PASS = FAIL = 0


def check(label, obtido, esperado):
    global PASS, FAIL
    if obtido == esperado:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s\n       esperado=%r\n       obtido  =%r" % (label, esperado, obtido))


def projeto(base, nome, plano=None):
    raiz = os.path.realpath(os.path.join(base, nome))
    os.makedirs(os.path.join(raiz, ".claude", "plans"))
    subprocess.run(["git", "init", "-q", raiz], check=True)
    if plano:
        with open(os.path.join(raiz, ".claude", "plans", "p.plan.json"), "w", encoding="utf-8") as fh:
            json.dump({"status": plano}, fh)
    return raiz


def edits(raiz, n):
    return [os.path.join(raiz, "f%d.txt" % i) for i in range(n)]


def main():
    with tempfile.TemporaryDirectory() as base:
        missao = projeto(base, "missao", "active")
        ferramenta = projeto(base, "ferramenta", "done")
        fora = os.path.realpath(base)

        print("[cwd no projeto da missão, mais edições na ferramenta]")
        s = infer_scope(edits(ferramenta, 24) + edits(missao, 3), missao)
        check("o cwd decide", s["project_root"], missao)
        check("sem pergunta", s["project_ambiguous"], False)

        print("[cwd fora dos dois, um só com plano aberto]")
        s = infer_scope(edits(ferramenta, 24) + edits(missao, 3), fora)
        check("o plano aberto decide", s["project_root"], missao)
        check("sem pergunta", s["project_ambiguous"], False)

        print("[cwd fora, nenhum com plano aberto]")
        outro = projeto(base, "outro")
        s = infer_scope(edits(ferramenta, 5) + edits(outro, 2), fora)
        check("cai na contagem", s["project_root"], ferramenta)
        check("e manda perguntar", s["project_ambiguous"], True)

        print("[um projeto só]")
        s = infer_scope(edits(ferramenta, 2), fora)
        check("o único editado", s["project_root"], ferramenta)
        check("sem pergunta", s["project_ambiguous"], False)

    print("\ncollect_scope: %d ok, %d falha(s)" % (PASS, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
