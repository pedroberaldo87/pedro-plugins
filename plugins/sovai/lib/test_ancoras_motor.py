#!/usr/bin/env python3
"""As quatro portas de agente morto do motor tem que continuar no esqueleto.

Por que este teste existe, e por que ele e uma REDE e nao uma checagem a mais:
o esqueleto do motor mora todo num arquivo so, `skills/sovai/SKILL.md`, e o plano
2026-08-06 tem DEZENOVE passos que reescrevem esse mesmo arquivo. Reescrita grande
apaga o que ninguem esta olhando, e o que estava em risco aqui e justamente o que
ja salvou missao em producao.

O que essas quatro portas evitaram, medido em 2026-08-02: uma execucao morreu com
8 dos 12 agentes JA ENTREGUES e devolveu falha total, porque `review.gaps` foi lido
sem guarda quando `agent()` devolveu null. O trabalho existia em disco; o que se
perdeu foi o relato dele.

A regra que as quatro compartilham: falha de infra degrada a missao, NUNCA fabrica
aprovacao. Por isso o teste cobra as duas metades de cada porta — que ela exista, e
que a DIRECAO dela seja a segura. Guarda presente com direcao trocada e pior que
guarda nenhuma: parece protecao e declara pronto.
"""

import os
import re
import sys

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "sovai", "SKILL.md")

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def bloco(texto, guarda, linhas=8):
    """As `linhas` seguintes a uma guarda `if (!x) {`, pra ler a direcao dela."""
    i = texto.find(guarda)
    if i < 0:
        return ""
    return "\n".join(texto[i:].splitlines()[:linhas])


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()

    print("porta 1 — decompositor morto sai do laco, nao estoura")
    d = bloco(texto, "if (!decomp) {")
    check("a guarda do decompositor existe", bool(d))
    check("ela empurra um blocker", "blockers.push" in d)
    check("a direcao e `break` (sem decomposicao nao ha o que executar)",
          re.search(r"\bbreak\b", d) is not None)

    print("porta 2 — revisor morto NAO declara built")
    r = bloco(texto, "if (!review) {", linhas=7)
    check("a guarda do revisor existe", bool(r))
    check("ela empurra um blocker", "blockers.push" in r)
    check("a direcao e `continue` — a missao degrada, nao morre",
          re.search(r"\bcontinue\b", r) is not None)
    check("a rodada entra no historico com review nulo", "review: null" in r)
    check("a razao esta escrita no arquivo, nao so na cabeca de quem leu",
          "revisor que não respondeu não aprovou nada" in texto)

    print("porta 3 — confirm-pass morto e o caso mais duro")
    c = bloco(texto, "if (!confirm) {", linhas=5)
    check("a guarda do confirm-pass existe", bool(c))
    check("ela empurra um blocker", "blockers.push" in c)
    check("a direcao e `break` — ninguem conferiu a obra",
          re.search(r"\bbreak\b", c) is not None)
    check("o blocker diz que nao e pra considerar entregue",
          "não considere entregue" in c)

    print("porta 4 — executor morto sai do relato pelos DOIS lados")
    check("paralelo e sequencial filtram, nao so o paralelo",
          "builtPar.filter(Boolean).concat(builtSeq.filter(Boolean))" in texto)
    check("o arquivo registra por que filtrar so um lado quebrava",
          "Filtrar só o paralelo" in texto)

    print("a regra geral das quatro continua declarada")
    check("falha de infra degrada, nunca fabrica aprovacao",
          "AGENTE MORTO NÃO PODE DERRUBAR O MOTOR" in texto)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        print("\nEstas frases NAO sao decoracao: cada uma e uma porta que ja impediu")
        print("uma missao de virar falha total. Se voce as removeu numa reescrita,")
        print("recoloque; se as MOVEU, ajuste este teste no mesmo commit.")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
