#!/usr/bin/env python3
"""Suíte da régua de POR ONDE a pergunta chega — stdlib, sem framework.

O que ela protege: a régua nasce em _shared/ e chega INTEIRA a toda skill que
pergunta ao dono. Três defeitos ela pega: cópia vendorada defasada, cláusula
que sumiu da fonte, e SKILL.md que voltou a repetir o texto em vez de apontar.
Confere também que a régua invoca a skill de página PELO NOME — caminho para
dentro de outro plugin quebra o Artigo 9.

    python3 _shared/test_regua_de_pergunta.py
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
ARQ = "regua-de-pergunta.md"

FONTE = os.path.join(AQUI, ARQ)
# Os quatro destinos: as três skills que usam AskUserQuestion mais a grill-me,
# que pergunta em rodadas sem usar a ferramenta.
DESTINOS = [
    "plugins/grill-me/skills/grill-me",
    "plugins/project-doc/skills/start-doc",
    "plugins/handoff/skills/handoff",
    "plugins/lixeiro/skills/faxina",
]

# Cada cláusula da régua, como o dono a ditou.
CLAUSULAS = [
    ("o padrão é a rodada inteira numa página",
     "**Padrão — a rodada inteira numa página, em múltipla escolha.**"),
    ("a página tem opções em rádio", "as opções em rádio"),
    ("a página tem campo livre", "campo livre"),
    ("a recomendação é sugestão, não resposta dada", "nunca como\n  resposta dada"),
    ("a skill de página é invocada pelo nome", "invoque-a **pelo nome**"),
    ("skill ausente na máquina não trava", "caia\n    no canal alternativo e siga"),
    ("a resposta é colhida do estado em disco", "~/.claude/visual-state/latest.json"),
    ("não se pede copiar e colar", "não peça ao usuário para copiar e colar"),
    ("opção sem o conteúdo concreto não vale", "**Pergunta sem apoio não vale.**"),
    ("a alternativa é a ferramenta nativa, uma por vez",
     "**Alternativa — uma por vez, na ferramenta nativa de pergunta.**"),
    ("quem escolhe o canal é o dono", "**Quem escolhe é o usuário.**"),
    ("sem escolha dita, vale o padrão", "use o padrão"),
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


print("\n== a régua na fonte ==")
if not os.path.isfile(FONTE):
    print("  FAIL fonte ausente: _shared/%s" % ARQ)
    sys.exit(1)
src = ler(FONTE)
for label, trecho in CLAUSULAS:
    check("fonte: %s" % label, trecho in src, "(faltou %r)" % trecho)
check("a régua NÃO monta caminho pra dentro de outro plugin", "plugins/" not in src)

print("\n== a régua nas quatro cópias vendoradas ==")
for d in DESTINOS:
    c = os.path.join(ROOT, d, ARQ)
    rel = os.path.join(d, ARQ)
    if not os.path.isfile(c):
        check("cópia existe: %s" % rel, False)
        continue
    txt = ler(c)
    for label, trecho in CLAUSULAS:
        check("%s: %s" % (rel, label), trecho in txt)
    check("%s idêntica à fonte" % rel, txt == src)

print("\n== as quatro skills APONTAM em vez de repetir ==")
for d in DESTINOS:
    s = os.path.join(ROOT, d, "SKILL.md")
    rel = os.path.join(d, "SKILL.md")
    if not os.path.isfile(s):
        check("SKILL.md existe: %s" % rel, False)
        continue
    txt = ler(s)
    check("%s aponta pra %s" % (rel, ARQ), ARQ in txt)
    check("%s nomeia a fonte _shared/" % rel, "_shared/%s" % ARQ in txt)
    check("%s não repete o texto da régua" % rel,
          "**Alternativa — uma por vez, na ferramenta nativa de pergunta.**" not in txt)

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
