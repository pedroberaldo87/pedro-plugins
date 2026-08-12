#!/usr/bin/env python3
"""Suíte do TRIPÉ da revisão — stdlib, sem framework.

O que ela protege: o mínimo que toda revisão mede (qualidade · cobertura por
finalidade · coerência com a régua) nasce em `_shared/dimensoes-de-revisao.md` e
chega INTEIRO às skills que revisam. Quatro defeitos ela pega:

  1. cópia vendorada defasada (o texto da skill instalada diverge da fonte);
  2. pé ou dimensão que sumiu da fonte;
  3. SKILL.md que voltou a REPETIR a lista em vez de apontar para o contrato;
  4. SKILL.md que voltou a ENUMERAR documento de projeto por nome — o drift que
     custou caro: uma skill citava quatro documentos e o `doc_load.py` já listava
     onze, e nenhum dos dois lados ficava errado sozinho.

    python3 scripts/test_dimensoes_de_revisao.py
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
ARQ = "dimensoes-de-revisao.md"
FONTE = os.path.join(ROOT, "_shared", ARQ)

sys.path.insert(0, AQUI)
from vendoring import destinos                      # noqa: E402

# As cláusulas do contrato, como o dono as ditou. Cada uma existe porque um
# defeito real passou por não estar escrita.
CLAUSULAS = [
    ("o tripé é MÍNIMO, não preferência", "é\nmínimo"),
    ("revisão que não mediu um pé DECLARA isso", "declara que não mediu"),
    ("pé 1 é qualidade", "## Pé 1 · Qualidade"),
    ("pé 2 é cobertura por finalidade", "## Pé 2 · Cobertura por finalidade"),
    ("pé 3 é coerência com a régua", "## Pé 3 · Coerência com a régua"),
    ("o checklist tem as sete dimensões", "| 7 | **cobertura por finalidade** |"),
    ("o pé 2 julga o teste que EXISTE", "O teste que EXISTE serve?"),
    ("…e o teste que NÃO existe", "**O teste que NÃO existe.**"),
    ("finalidade sem rede não cai em antipadrão", "**não cai em antipadrão**"),
    ("a prova de que o teste morde é a mutação", "é a MUTAÇÃO, não a leitura"),
    ("o pé 3 manda rodar o doc-load", "Rode o `doc-load` e julgue contra TUDO"),
    ("o contrato NÃO enumera documento de projeto",
     "não enumera documento de projeto, de propósito"),
    ("ausência de régua não é achado", "**Ausência não é achado.**"),
    ("a lei é fixada na primeira volta", "fixada na primeira volta"),
    ("lint/type/teste vermelho não é este pé", "O que NÃO conta como este pé"),
]

# Nome de documento de projeto que NENHUMA skill de revisão pode enumerar: quem
# diz o que vale como régua é o programa, na hora.
DOCS_QUE_SO_O_PROGRAMA_LISTA = [
    "constituicao.md", "quality-goals.md", "blueprint.md", "features.md",
    "constraints.md", "journeys.md", "solution-strategy.md",
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


print("\n== o tripé na fonte ==")
if not os.path.isfile(FONTE):
    print("  FAIL fonte ausente: _shared/%s" % ARQ)
    sys.exit(1)
src = ler(FONTE)
for label, trecho in CLAUSULAS:
    check("fonte: %s" % label, trecho in src, "(faltou %r)" % trecho)

DESTINOS = destinos(ARQ)
check("o vendoring declara ao menos dois consumidores", len(DESTINOS) >= 2,
      "(achei %d)" % len(DESTINOS))

print("\n== as cópias vendoradas ==")
for d in DESTINOS:
    c = os.path.join(ROOT, d, ARQ)
    rel = os.path.join(d, ARQ)
    if not os.path.isfile(c):
        check("cópia existe: %s" % rel, False)
        continue
    check("%s idêntica à fonte" % rel, ler(c) == src)

print("\n== as skills APONTAM em vez de repetir ==")
for d in DESTINOS:
    # a skill mora um nível acima de references/
    skill = os.path.join(ROOT, os.path.dirname(d), "SKILL.md")
    rel = os.path.relpath(skill, ROOT)
    if not os.path.isfile(skill):
        check("SKILL.md existe: %s" % rel, False)
        continue
    txt = ler(skill)
    check("%s aponta pra %s" % (rel, ARQ), ARQ in txt)
    check("%s nomeia a fonte _shared/" % rel, "_shared/%s" % ARQ in txt)
    # Repetir o contrato é o drift que ele existe pra matar: a tabela de
    # dimensões e os títulos dos pés só podem morar na fonte.
    check("%s não repete a tabela de dimensões" % rel,
          "| 7 | **cobertura por finalidade** |" not in txt)
    check("%s não repete os títulos dos pés" % rel,
          "## Pé 1 · Qualidade" not in txt)

print("\n== nenhuma skill de revisão ENUMERA documento de régua ==")
for d in DESTINOS:
    skill = os.path.join(ROOT, os.path.dirname(d), "SKILL.md")
    rel = os.path.relpath(skill, ROOT)
    if not os.path.isfile(skill):
        continue
    txt = ler(skill)
    for doc in DOCS_QUE_SO_O_PROGRAMA_LISTA:
        # `.claude/docs/<nome>` é a forma que denuncia a enumeração; citar o
        # doc_load.py (o programa) continua permitido e é o caminho certo.
        marca = ".claude/docs/%s" % doc
        check("%s não enumera %s" % (rel, doc), marca not in txt,
              "(a lista de régua sai do doc_load.py, nunca da prosa)")

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
