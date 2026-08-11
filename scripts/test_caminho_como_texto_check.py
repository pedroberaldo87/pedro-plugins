#!/usr/bin/env python3
"""Cobra as DUAS pontas da receita de caminho: o comparador e quem o exige.

Sem a segunda ponta o cobrador é decorativo — e a régua anti-tautologia da casa é
justamente esta: um caso que SABOTA o alvo e exige que a suíte reprove. Se ela
continuar verde com o alvo quebrado, ela não estava medindo nada.
"""

import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(RAIZ, "_shared"))
sys.path.insert(0, AQUI)
import caminho_igual as ci  # noqa: E402
import caminho_como_texto_check as cc  # noqa: E402

OK = [0]
FAILS = []


def check(nome, cond):
    OK[0] += 1
    print("  %s %s" % ("ok  " if cond else "FALHOU", nome))
    if not cond:
        FAILS.append(nome)


def main():
    print("a receita — as duas barras descrevem o mesmo caminho")
    sep = os.sep
    a = sep.join([".claude", "docs", "blueprint.md"])
    check("o caminho do sistema iguala o escrito com barra normal",
          ci.igual(a, ".claude/docs/blueprint.md"))
    check("barra final não muda o caminho", ci.igual("a/b/", "a/b"))
    check("caminho diferente continua diferente", not ci.igual("a/b", "a/c"))
    check("None não iguala caminho nenhum", not ci.igual(None, "a"))
    check("contem acha o segmento", ci.contem(a, ".claude/docs"))
    check("contem NÃO casa pedaço de palavra (lib ≠ biblioteca)",
          not ci.contem(sep.join(["x", "biblioteca", "y"]), "lib"))
    check("termina_em conta segmento, não letra",
          not ci.termina_em(sep.join(["p", "meu-x.py"]), "x.py"))
    check("termina_em aceita o sufixo de verdade", ci.termina_em(a, "docs/blueprint.md"))

    print("o cobrador — o que ele acusa, e o que ele deixa em paz")
    check("literal com barra e extensão parece caminho",
          cc.parece_caminho(".claude/docs/x.md"))
    check("nome de branch NÃO parece caminho", not cc.parece_caminho("feat/squash"))
    check("frase com barra dentro NÃO parece caminho",
          not cc.parece_caminho("morto · src/a.ts: prob_h"))
    check("URL NÃO parece caminho", not cc.parece_caminho("https://x/y.md"))
    check("extensão solta NÃO parece caminho", not cc.parece_caminho(".html"))

    print("o repositório de hoje está limpo")
    arquivos, fora = cc.varre(RAIZ)
    check("a varredura alcança as suítes (não é glob vazio)", len(arquivos) > 40)
    check("nenhuma comparação de caminho por texto cru", fora == [])

    print("prova anti-tautologia — com o defeito plantado, o cobrador REPROVA")
    d = tempfile.mkdtemp(prefix="cct-")
    try:
        os.makedirs(os.path.join(d, "plugins", "x", "lib"))
        alvo = os.path.join(d, "plugins", "x", "lib", "test_plantado.py")
        with open(alvo, "w", encoding="utf-8") as fh:
            fh.write("import os\n"
                     "caminho = os.path.abspath('.')\n"
                     "assert caminho == '.claude/docs/x.md'\n")
        _, achados = cc.varre(d)
        check("o defeito plantado é acusado", len(achados) == 1)
        check("...e a acusação nomeia o literal",
              bool(achados) and ".claude/docs/x.md" in achados[0][2])

        # E a isenção declarada silencia — senão o cobrador vira obstáculo.
        with open(alvo, "w", encoding="utf-8") as fh:
            fh.write("import os\n"
                     "caminho = os.path.abspath('.')\n"
                     "assert caminho == '.claude/docs/x.md'  # caminho-ok: exemplo do teste\n")
        _, isentos = cc.varre(d)
        check("isenção declarada silencia o achado", isentos == [])
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)

    print("o comparador roda sozinho pela linha de comando")
    r = subprocess.run([sys.executable, os.path.join(RAIZ, "_shared", "caminho_igual.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    check("a demo do caminho_igual sai 0", r.returncode == 0)

    print()
    if FAILS:
        print("FALHOU (%d de %d):" % (len(FAILS), OK[0]))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK (%d checks)" % OK[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
