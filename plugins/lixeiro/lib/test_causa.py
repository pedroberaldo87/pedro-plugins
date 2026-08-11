#!/usr/bin/env python3
"""Bancada do causa.py — a investigação sabe dizer de onde a sobra veio?

O caso que dá sentido à suíte é o do "não sei": sobra cujo comando não aponta arquivo
nenhum tem que APARECER na lista, com o motivo escrito. Some-la deixaria de fora
justamente o caso difícil, e o relatório diria que está tudo explicado quando não está.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import causa  # noqa: E402

FALHAS = []


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def main():
    print("causa")

    d = tempfile.mkdtemp(prefix="causa-")
    try:
        vaza = os.path.join(d, "vaza.py")
        open(vaza, "w", encoding="utf-8").write("import subprocess\nsubprocess.run(['git','status'])\n")
        r = causa.investiga([{"pid": 4242, "comando": "python3 %s --json" % vaza}])
        check("liga a sobra ao arquivo que a abriu", len(r) == 1 and r[0]["arquivo"] == vaza)
        check("diz em que linha está o defeito", r[0]["linha"] == 2)
        check("explica o motivo em linguagem humana",
              "entrada" in (r[0]["motivo"] or "") or "grupo" in (r[0]["motivo"] or ""))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="causa-limpo-")
    try:
        limpo = os.path.join(d, "limpo.py")
        open(limpo, "w").write(
            "import subprocess\n"
            "subprocess.run(['git','status'], stdin=subprocess.DEVNULL,\n"
            "               start_new_session=True)\n")
        r = causa.investiga([{"pid": 1, "comando": "python3 %s" % limpo}])
        check("arquivo já consertado não recebe culpa de padrão",
              "não deu para dizer" in (r[0]["motivo"] or ""))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    r = causa.investiga([{"pid": 9, "comando": "/usr/bin/algum-binario --flag"}])
    check("sobra sem arquivo identificável APARECE, com o motivo escrito",
          len(r) == 1 and r[0]["arquivo"] is None and r[0]["motivo"])

    check("lista vazia devolve lista vazia, sem estourar", causa.investiga([]) == [])

    # ── ALCANCE — o dígito que o juiz recebe ──────────────────────────────────
    d = tempfile.mkdtemp(prefix="causa-alc-")
    try:
        os.makedirs(os.path.join(d, "hooks"), exist_ok=True)
        alvo = os.path.join(d, "hooks", "meu-hook.py")
        open(alvo, "w", encoding="utf-8").write("x = 1\n")
        open(os.path.join(d, "hooks", "hooks.json"), "w").write(
            '{"hooks": {"Stop": [{"hooks": [{"command": "meu-hook.py"}]}]}}')
        a = causa.alcance([alvo], raiz=d, linhas_mudadas=3)
        check("conta os arquivos tocados", a["arquivos"] == 1)
        check("carrega as linhas mudadas", a["linhas_mudadas"] == 3)
        check("acusa que o arquivo roda em hook", a["em_hook"] == [alvo])
        check("acusa que não há suíte cobrindo", a["sem_suite"] == [alvo])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="causa-suite-")
    try:
        alvo = os.path.join(d, "modulo.py")
        open(alvo, "w", encoding="utf-8").write("x = 1\n")
        open(os.path.join(d, "test_modulo.py"), "w", encoding="utf-8").write("import sys\nsys.exit(0)\n")
        a = causa.alcance([alvo], raiz=d)
        check("acha a suíte que cobre o arquivo", a["tem_suite"] == [alvo])
        rodou, verde, _ = causa.suite_verde(alvo)
        check("roda a suíte e vê o verde", rodou and verde)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="causa-suite-red-")
    try:
        alvo = os.path.join(d, "modulo.py")
        open(alvo, "w", encoding="utf-8").write("x = 1\n")
        open(os.path.join(d, "test_modulo.py"), "w", encoding="utf-8").write("import sys\nsys.exit(1)\n")
        rodou, verde, _ = causa.suite_verde(alvo)
        check("suíte vermelha volta como vermelha", rodou and not verde)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # Plugin de terceiro é o limite mais duro: o conserto não sobrevive à próxima
    # atualização dele, e mexer no código de outro sem avisar é o oposto do combinado.
    d = tempfile.mkdtemp(prefix="causa-terc-")
    try:
        fundo = os.path.join(d, "plugins", "cache", "outro-marketplace", "p", "1.0.0")
        os.makedirs(fundo, exist_ok=True)
        alvo = os.path.join(fundo, "x.py")
        open(alvo, "w", encoding="utf-8").write("x = 1\n")
        a = causa.alcance([alvo], raiz=d)
        check("arquivo de plugin de terceiro é nomeado como tal",
              a["de_terceiro"] == ["outro-marketplace"])
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
