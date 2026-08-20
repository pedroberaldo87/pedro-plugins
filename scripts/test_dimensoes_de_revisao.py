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
import re
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


PASTA_DA_REGUA = ".claude/docs"  # casa-ok: fixture de teste, o literal e o dado do caso

# A pasta da régua APONTADA como pasta da régua: solta (aspas, parêntese, espaço, fim)
# ou colada ao documento. Caminho que segue para uma SUBPASTA — `.claude/docs/prototipo/`,  # casa-ok: fixture de teste, o literal e o dado do caso
# a casa do protótipo — aponta OUTRA coisa, e citá-lo não é enumerar a régua. Sem esta
# distinção a régua media o arquivo inteiro: em 2026-08-16 uma linha nova sobre o
# protótipo reprovou duas menções legítimas a 58 linhas dela, e a porta do repositório
# fechou por defeito do medidor, não da obra.
APONTA_A_REGUA = re.compile(re.escape(PASTA_DA_REGUA) + r"(?!/[a-z0-9_-]+/)")


def enumera(txt, doc):
    """A skill enumera `doc` quando aponta a PASTA da régua e cita o NOME do documento.

    Exigir os dois CONTÍGUOS (`.claude/docs/<nome>`) era brecha: um trecho que põe a  # casa-ok: prosa que descreve a casa velha, nao um caminho usado
    pasta numa linha (`docs = os.path.join(cwd, ".claude/docs")`) e os nomes na linha  # casa-ok: prosa que descreve a casa velha, nao um caminho usado
    seguinte enumera igual e passava verde. Citar o `doc_load.py` (o programa) segue
    permitido — ele não escreve a pasta na prosa.
    """
    return bool(APONTA_A_REGUA.search(txt)) and doc in txt


def _skill_de(destino):
    """O `SKILL.md` dono de uma cópia vendorada.

    Duas formas convivem no vendoring: a cópia em `<skill>/references/` (o r8-tiers,
    os antipadrões) e a cópia direto em `<skill>/` (a régua de pergunta). Presumir
    só a primeira faria a suíte falhar por ENDEREÇO no dia em que um consumidor
    usasse a segunda — falha por defeito e falha por convenção não podem ter a
    mesma cara.
    """
    aqui = os.path.join(ROOT, destino, "SKILL.md")
    return aqui if os.path.isfile(aqui) else os.path.join(ROOT, os.path.dirname(destino),
                                                          "SKILL.md")


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

print("\n== o apontamento do Pé 2 não morre na cópia ==")
# O Pé 2 cita `antipadroes-de-teste.md` "ao lado deste arquivo". Onde o tripé é
# vendorado sem o vizinho, o apontamento morre na máquina instalada — que é
# exatamente o modo de falha que o mapa do vendoring já declara em comentário.
VIZINHO = "antipadroes-de-teste.md"
check("o Pé 2 aponta pro vizinho", "ao lado deste arquivo" in src)
for d in DESTINOS:
    rel = os.path.join(d, VIZINHO)
    check("%s existe ao lado do tripé" % rel,
          os.path.isfile(os.path.join(ROOT, d, VIZINHO)),
          "(o apontamento do Pé 2 morre nesta cópia)")

print("\n== as skills APONTAM em vez de repetir ==")
for d in DESTINOS:
    skill = _skill_de(d)
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

print("\n== a régua da enumeração pega pasta e nome SEPARADOS ==")
# Teste NEGATIVO do alargamento: sem isto, a régua podia voltar a exigir contiguidade
# e a suíte ficaria verde por acidente, como ficou enquanto a plan enumerava.
check("pasta e nome em linhas separadas REPROVAM",
      enumera('docs = os.path.join(cwd, ".claude/docs")\nler(docs, "constituicao.md")',  # casa-ok: fixture de teste, o literal e o dado do caso
              "constituicao.md"))
check("pasta e nome contíguos REPROVAM",
      enumera("leia .claude/docs/constituicao.md", "constituicao.md"))  # casa-ok: fixture de teste, o literal e o dado do caso
check("citar só o programa PASSA",
      not enumera("quem lista a régua é o doc_load.py", "constituicao.md"))
check("citar o nome sem a pasta da régua PASSA",
      not enumera("o comando recebe <caminho>/constituicao.md", "constituicao.md"))

print("\n== nenhuma skill de revisão ENUMERA documento de régua ==")
for d in DESTINOS:
    skill = os.path.join(ROOT, os.path.dirname(d), "SKILL.md")
    rel = os.path.relpath(skill, ROOT)
    if not os.path.isfile(skill):
        continue
    txt = ler(skill)
    for doc in DOCS_QUE_SO_O_PROGRAMA_LISTA:
        check("%s não enumera %s" % (rel, doc), not enumera(txt, doc),
              "(a lista de régua sai do doc_load.py, nunca da prosa)")

print("\n== a premissa anti-drift está no cardápio da família ==")
# Sem cobrador a premissa é intenção, não regra (constituição, "a cláusula que
# manda em todas") — e ela é justamente a que impede este contrato de virar duas
# prosas divergentes. O cardápio é a skill-índice da família.
CARDAPIO = os.path.join(ROOT, "plugins", "project-skills", "skills",
                        "project-skills", "SKILL.md")
if not os.path.isfile(CARDAPIO):
    check("o cardápio da família existe", False)
else:
    card = ler(CARDAPIO)
    for label, trecho in [
        ("a premissa tem título próprio", "## A premissa anti-drift"),
        ("nada que duas skills sabem é escrito duas vezes",
         "Nada que duas skills precisam saber é escrito em duas skills"),
        ("a duplicata falha em SILÊNCIO", "falha **em silêncio**"),
        ("forma 1 — dado vira json compartilhado", "`_shared/<nome>.json`"),
        ("forma 2 — contrato em prosa vira md vendorado", "`_shared/<nome>.md`"),
        ("forma 3 — o que muda sozinho vira programa", "manda **rodar** o programa"),
        ("toda fonte compartilhada nasce com cobrador",
         "**Toda fonte compartilhada nasce com cobrador**"),
        ("a pergunta que fecha", "já\nestá escrito em outro lugar?"),
    ]:
        check("cardápio: %s" % label, trecho in card, "(faltou %r)" % trecho)

print("\n== nenhuma SKILL.md monta caminho de projeto à mão ==")
# Irmão do check acima: enumerar o NOME do documento e montar a PASTA a partir do
# cwd são o mesmo defeito — a skill decidindo onde a doc mora. O trecho do Passo 3
# da `plan` alimentava o resolvedor do programa com `os.getcwd()/.claude/plans` e
# via `artigos (0)` sempre que o cwd não era a raiz (repro: rodando de dentro de
# plugins/project-skills/, 0 artigos; com `c.resolve_dir()`, 9).


def monta_caminho_a_mao(txt):
    """Trecho que constrói a pasta de projeto em vez de pedi-la ao programa.

    Julga o TEXTO INTEIRO, como o `enumera` vizinho: exigir os dois na MESMA linha
    era a mesma brecha da contiguidade — `cwd = os.getcwd()` numa linha e
    `os.path.join(cwd, ".claude/docs")` na outra monta o caminho igual e passava  # casa-ok: prosa que descreve a casa velha, nao um caminho usado
    verde.
    """
    if "getcwd(" not in txt or ".claude" not in txt:
        return []
    return [ln.strip() for ln in txt.splitlines()
            if ".claude" in ln or "getcwd(" in ln]


check("montar .claude a partir do cwd REPROVA",
      monta_caminho_a_mao('d = os.path.join(os.getcwd(), ".claude", "plans")'))
check("cwd e .claude em linhas SEPARADAS REPROVAM",
      monta_caminho_a_mao('cwd = os.getcwd()\np = os.path.join(cwd, ".claude/docs")'))  # casa-ok: fixture de teste, o literal e o dado do caso
check("pedir a pasta ao resolvedor do programa PASSA",
      not monta_caminho_a_mao("d = c.resolve_dir()"))
for base, _dirs, arqs in os.walk(os.path.join(ROOT, "plugins")):
    if "SKILL.md" not in arqs:
        continue
    skill = os.path.join(base, "SKILL.md")
    ruins = monta_caminho_a_mao(ler(skill))
    check("%s não monta caminho de projeto" % os.path.relpath(skill, ROOT),
          not ruins, "(%s)" % "; ".join(ruins))

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
