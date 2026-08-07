#!/usr/bin/env python3
"""Suíte do regua_pronto.py — o critério de aceite que só se cumpre mexendo no entregável."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regua_pronto as rp  # noqa: E402

FAILS = []
AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(AQUI, "..", "skills", "visual", "SKILL.md"))


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


# O caso real: o critério mandou o número aparecer no documento, e o executor
# obedeceu escrevendo o número na mão.
BANCADA = [
    "o número de nós aparece no CLAUDE.md",
    "a contagem consta no relatório",
    "o documento cita as 6 fontes",
    "os três plugins estão listados na documentação",
    "a planilha contém o total do mês",
]

# O mesmo valor, mas com a origem declarada: o artefato NASCE do dado real.
OK = [
    "`graphify update --force` regera o índice e o número de nós no CLAUDE.md sai dele",
    "o relatório é gerado por `python3 lib/report.py` e a contagem aparece nele",
    "a planilha é derivada do banco e contém o total do mês",
    "`python3 lib/test_x.py` sai 0",
    "a tela mostra o botão de aprovar",
    "commit com o sha do conserto",
    "",
]


def main():
    print("regua_pronto")

    for t in BANCADA:
        errs = rp.erros_de_pronto(t, "F2.3")
        check("recusa: %s" % t, len(errs) == 1)
        if errs:
            check("  o motivo nomeia o passo e o defeito",
                  errs[0].startswith("F2.3:") and "entregável" in errs[0])

    for t in OK:
        check("passa: %r" % t, rp.erros_de_pronto(t, "F2.3") == [])

    # A linha de comando: é por ela que um .sh ou um gate cobra a mesma régua.
    exe = os.path.join(AQUI, "regua_pronto.py")
    r = subprocess.run([sys.executable, exe, "--onde", "F2.3", "-"],
                       input=BANCADA[0], capture_output=True, text=True)
    check("CLI sai 1 no critério de bancada", r.returncode == 1)
    check("CLI diz o motivo no stderr", "entregável" in r.stderr)
    r = subprocess.run([sys.executable, exe, "--onde", "F2.3", "-"],
                       input=OK[0], capture_output=True, text=True)
    check("CLI sai 0 e cala quando a origem está declarada",
          r.returncode == 0 and r.stderr == "")

    # A régua vale na hora de ESCREVER o plano — então ela mora na skill que o escreve.
    doc = open(SKILL, encoding="utf-8").read()
    check("a skill do /visual carrega a régua do `pronto`",
          "A régua do `pronto`" in doc)
    check("a skill diz o que PODE — regerar a partir do dado real",
          "regerar o entregável a partir do dado real" in doc)
    check("a skill diz o que NÃO PODE — injetar valor no entregável",
          "injetar valor inventado dentro do entregável" in doc)
    check("a skill aponta quem cobra", "regua_pronto.py" in doc)

    print()
    print("FALHOU: %d" % len(FAILS) if FAILS else "OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
