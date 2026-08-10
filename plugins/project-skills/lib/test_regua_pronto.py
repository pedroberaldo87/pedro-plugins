#!/usr/bin/env python3
"""Suíte do regua_pronto.py — o critério de aceite que só se cumpre mexendo no entregável."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regua_pronto as rp  # noqa: E402

FAILS = []
AQUI = os.path.dirname(os.path.abspath(__file__))
# A skill que ESCREVE o plano ainda mora no plugin `visual` (a mudança de casa dela
# é outro passo). Sem ele na máquina, o bloco que a lê é pulado.
SKILL = os.path.normpath(os.path.join(AQUI, "..", "..", "visual", "skills", "visual",
                                      "SKILL.md"))


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

# O segundo caso: o efeito prometido acontece FORA do processo (commit, push, arquivo
# em outra máquina, skill invocada) e a única prova oferecida é a bancada que finge a
# chamada. O teste fica verde sem que o efeito tenha acontecido uma vez.
SIMULADA = [
    "o commit é feito, provado por um mock do git",
    "o push chega no remoto, verificado com um fake do subprocess",
    "a skill é invocada — o teste usa um stub da chamada",
    "o hook dispara o processo filho, com monkeypatch do runner",
    "o binário chega na outra máquina, simulado pela bancada",
]

# O mesmo valor, mas com a origem declarada: o artefato NASCE do dado real.
OK = [
    "`graphify update --force` regera o índice e o número de nós no CLAUDE.md sai dele",
    "o relatório é gerado por `python3 lib/report.py` e a contagem aparece nele",
    "a planilha é derivada do banco e contém o total do mês",
    "`python3 lib/test_x.py` sai 0",
    "a tela mostra o botão de aprovar",
    "commit com o sha do conserto",
    "`git log -1 --format=%H` mostra o sha do commit no repositório de verdade",
    "o teste usa um mock do relógio e sai 0",
    "",
]


# Critérios reais de .claude/plans cortados em 140 caracteres — o corte por limite
# cai no meio da palavra, e nenhum conectivo casa lá.
CORTADO = [
    "o gauntlet decide qual dos dois entrega, e o veredito diz porque nenhum dos "
    "dois — com teste dos dois caminh",
    "`python3 plugins/vistoria/lib/pagina.py` abre a página com a legenda "  # acopla-ok: fixture
    "(a contagem por tipo",
    'o relatório traz o campo "origem',
]

# O mesmo texto INTEIRO, e os casos que a régua nova não pode confundir com corte:
# parêntese solto DENTRO de crase é comando de verdade.
INTEIRO = [
    "o gauntlet decide qual dos dois entrega, e o veredito diz porque nenhum dos "
    "dois — com teste dos dois caminhos",
    "`python3 plugins/vistoria/lib/pagina.py` abre a página com a legenda "  # acopla-ok: fixture
    "(a contagem por tipo)",
    'o relatório traz o campo "origem" preenchido',
    "`grep -cE 'rgba\\(' template.html` não devolve halo colorido, e a suíte sai verde",
    "o ciclo cita os decks, e um teste prova que mexer na origem marca o deck",
]


def main():
    print("regua_pronto")

    for t in BANCADA:
        errs = rp.erros_de_pronto(t, "F2.3")
        check("recusa: %s" % t, len(errs) == 1)
        if errs:
            check("  o motivo nomeia o passo e o defeito",
                  errs[0].startswith("F2.3:") and "entregável" in errs[0])

    for t in SIMULADA:
        errs = rp.erros_de_pronto(t, "F9.5")
        check("recusa (finge a chamada): %s" % t, len(errs) == 1)
        if errs:
            check("  o motivo nomeia o passo e a simulação",
                  errs[0].startswith("F9.5:") and "SIMULA" in errs[0])

    for t in OK:
        check("passa: %r" % t, rp.erros_de_pronto(t, "F2.3") == [])

    # O corte por LIMITE DE CARACTERE: cai no meio da palavra, onde conectivo e
    # reticências não casam. Textos reais de .claude/plans cortados em 140.
    for t in CORTADO:
        check("cortado: %r" % t[-34:], len(rp.criterio_cortado(t, "F9.61")) == 1)
    for t in INTEIRO:
        check("inteiro passa: %r" % t[-34:], rp.criterio_cortado(t, "F9.61") == [])

    # A linha de comando: é por ela que um .sh ou um gate cobra a mesma régua.
    exe = os.path.join(AQUI, "regua_pronto.py")
    r = subprocess.run([sys.executable, exe, "--onde", "F2.3", "-"],
                       input=BANCADA[0], capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
    check("CLI sai 1 no critério de bancada", r.returncode == 1)
    check("CLI diz o motivo no stderr", "entregável" in r.stderr)
    r = subprocess.run([sys.executable, exe, "--onde", "F9.5", "-"],
                       input=SIMULADA[0], capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
    check("CLI sai 1 no critério provado por simulação", r.returncode == 1)
    r = subprocess.run([sys.executable, exe, "--onde", "F2.3", "-"],
                       input=OK[0], capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
    check("CLI sai 0 e cala quando a origem está declarada",
          r.returncode == 0 and r.stderr == "")

    # A régua vale na hora de ESCREVER o plano — então ela mora na skill que o escreve.
    if not os.path.exists(SKILL):
        print("a régua na skill — pulada: o plugin `visual` não está nesta máquina")
    else:
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
