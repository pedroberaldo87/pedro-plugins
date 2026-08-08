#!/usr/bin/env python3
"""Suíte do contrato da família — stdlib, sem framework.

O que ela protege: o contrato (pastas, documentos, frontmatter, quem escreve e
quem lê) nasce em _shared/ e chega INTEIRO às skills da família. Três defeitos
ela pega: cópia vendorada defasada, cláusula que sumiu da fonte, e SKILL.md que
não aponta pra cópia local.

    python3 scripts/test_contrato_familia.py
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
ARQ = "contrato-familia.md"
FONTE = os.path.join(ROOT, "_shared", ARQ)

# As quatro skills da família: as duas que ESCREVEM documento e as duas que
# leem a lei que elas produzem.
DESTINOS = [
    "plugins/project-doc/skills/start-doc",
    "plugins/project-doc/skills/project-doc",
    "plugins/sovai/skills/sovai",
    "plugins/qa-loop/skills/qa-loop",
]

# Cada cláusula do contrato, pelo que ela decide.
CLAUSULAS = [
    ("a pasta canônica dos documentos", "`.claude/docs/`"),
    ("a pasta do log de decisões", "`.claude/docs/decisions/`"),
    ("a pasta dos planos", "`.claude/plans/`"),
    ("o índice e os ponteiros ficam na raiz", "ficam na **raiz do projeto**"),
    ("os autorais das seis etapas", "`architecture-intent.md`"),
    ("os minerados", "`runtime.md`"),
    ("o irmão histórico", "`<nome>.historico.md`"),
    ("a trava de escrita", "authored-by: human"),
    ("o de acordo e a marca do corpo", "approved-sig"),
    ("quem grava o de acordo", "hooks/doc-aprovar.sh"),
    ("minerado não pede de acordo", "Documento minerado não usa"),
    ("a tabela de quem escreve e quem lê", "## Quem escreve e quem lê"),
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


print("\n== o contrato na fonte ==")
if not os.path.isfile(FONTE):
    print("  FAIL fonte ausente: _shared/%s" % ARQ)
    sys.exit(1)
src = ler(FONTE)
for label, trecho in CLAUSULAS:
    check("fonte: %s" % label, trecho in src, "(faltou %r)" % trecho)

print("\n== o contrato nas quatro cópias vendoradas ==")
for d in DESTINOS:
    rel = os.path.join(d, ARQ)
    c = os.path.join(ROOT, rel)
    if not os.path.isfile(c):
        check("cópia existe: %s" % rel, False)
        continue
    check("%s idêntica à fonte" % rel, ler(c) == src)

print("\n== as quatro skills APONTAM pra cópia local ==")
for d in DESTINOS:
    rel = os.path.join(d, "SKILL.md")
    s = os.path.join(ROOT, rel)
    if not os.path.isfile(s):
        check("SKILL.md existe: %s" % rel, False)
        continue
    txt = ler(s)
    check("%s aponta pra %s" % (rel, ARQ), ARQ in txt)
    check("%s nomeia a fonte _shared/" % rel, "_shared/%s" % ARQ in txt)

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
