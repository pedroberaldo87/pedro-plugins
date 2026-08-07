#!/usr/bin/env python3
"""Suíte do contrato dos cinco antipadrões de teste — stdlib, sem framework.

O que ela protege: os cinco nascem em _shared/ e chegam INTEIROS às duas skills
que mandam testar. Cópia vendorada defasada (ou um antipadrão que sumiu da
fonte) é o defeito que esta suíte pega — e ela confere o texto nas DUAS cópias,
não só na fonte.

    python3 _shared/test_antipadroes_de_teste.py
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
ARQ = "antipadroes-de-teste.md"

FONTE = os.path.join(AQUI, ARQ)
COPIAS = [
    os.path.join(ROOT, "plugins/qa-loop/skills/qa-loop/references", ARQ),
    os.path.join(ROOT, "plugins/visual/skills/visual/references", ARQ),
]
SKILLS = [
    os.path.join(ROOT, "plugins/qa-loop/skills/qa-loop/SKILL.md"),
    os.path.join(ROOT, "plugins/visual/skills/visual/SKILL.md"),
]

# Os cinco, como o dono os ditou. Título do bloco + a prova concreta que o
# acompanha — sem a prova o item vira slogan, e slogan não muda comportamento.
CINCO = [
    ("1 · Passa com e sem a mudança", "restaure, veja VERDE"),
    ("2 · Espera um texto que o código nunca escreve", "3 plano aberto"),
    ("3 · Só experimenta o caminho que dá certo", "desligar o guarda passa calado"),
    ("4 · Mede a coisa errada", "acusou quatro"),
    ("5 · Vai pro segundo plano com espera pelo resultado", "travou execução pra sempre"),
]

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


def ler(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


print("\n== os cinco na fonte ==")
if not os.path.isfile(FONTE):
    print("  FAIL fonte ausente: _shared/%s" % ARQ)
    sys.exit(1)
src = ler(FONTE)
for titulo, prova in CINCO:
    check("fonte tem '%s'" % titulo, titulo in src)
    check("fonte tem a prova de '%s'" % titulo, prova in src, "(faltou %r)" % prova)

print("\n== os cinco nas duas cópias vendoradas ==")
for c in COPIAS:
    rel = os.path.relpath(c, ROOT)
    if not os.path.isfile(c):
        check("cópia existe: %s" % rel, False)
        continue
    txt = ler(c)
    for titulo, prova in CINCO:
        check("%s tem '%s'" % (rel, titulo), titulo in txt)
        check("%s tem a prova de '%s'" % (rel, titulo), prova in txt)
    check("%s idêntica à fonte" % rel, txt == src)

print("\n== as duas skills APONTAM em vez de repetir ==")
for s in SKILLS:
    rel = os.path.relpath(s, ROOT)
    txt = ler(s)
    check("%s aponta pra references/%s" % (rel, ARQ), "references/%s" % ARQ in txt)
    check("%s nomeia a fonte _shared/" % rel, "_shared/%s" % ARQ in txt)

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
