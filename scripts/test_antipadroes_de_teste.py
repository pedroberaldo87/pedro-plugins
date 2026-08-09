#!/usr/bin/env python3
"""Suíte do contrato dos cinco antipadrões de teste — stdlib, sem framework.

O que ela protege: os cinco nascem em _shared/ e chegam INTEIROS às duas skills
que mandam testar. Cópia vendorada defasada (ou um antipadrão que sumiu da
fonte) é o defeito que esta suíte pega — e ela confere o texto nas DUAS cópias,
não só na fonte.

    python3 scripts/test_antipadroes_de_teste.py
"""

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
SHARED = os.path.join(ROOT, "_shared")
ARQ = "antipadroes-de-teste.md"

FONTE = os.path.join(SHARED, ARQ)


def _destinos_do_vendoring(nome):
    """Os destinos DECLARADOS em scripts/sync-shared.sh, lidos do arquivo.

    A lista era escrita à mão aqui, e o F14.2 a venceu: `qa-loop` mudou de plugin,
    o caminho velho deixou de existir e a suíte passou a morrer em FileNotFoundError
    — vermelha por endereço, não por defeito. Quem sabe onde cada cópia mora é o
    próprio vendoring; derivar dele faz o próximo rename chegar aqui sozinho.
    """
    sync = os.path.join(ROOT, "scripts", "sync-shared.sh")
    with open(sync, encoding="utf-8") as fh:
        bloco = re.search(r"^SPECS=\((.*?)^\)", fh.read(), re.S | re.M)
    saida = []
    for linha in (bloco.group(1) if bloco else "").splitlines():
        m = re.search(r'"([^"]+)::([^"]+)"', linha)
        if m and m.group(2) == nome:
            saida.append(m.group(1))
    return saida


DESTINOS = _destinos_do_vendoring(ARQ)
COPIAS = [os.path.join(ROOT, d, ARQ) for d in DESTINOS]
# A skill que consome a cópia é a pasta acima de `references/`, quando há uma.
SKILLS = [os.path.join(ROOT, d[:-len("/references")] if d.endswith("/references") else d,
                       "SKILL.md") for d in DESTINOS]

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
