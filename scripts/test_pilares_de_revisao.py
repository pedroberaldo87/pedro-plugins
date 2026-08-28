#!/usr/bin/env python3
"""test_pilares_de_revisao.py — o cobrador dos TRÊS PILARES da revisão.

ORDEM DO DONO (2026-08-28, verbatim no essencial): todo revisor de código dos plugins
(qa-loop, sprint e qualquer futuro) mede TRÊS PILARES contra TRÊS ÂNCORAS
(PEDIDO · PLANO · CONSTITUIÇÃO):

  · QUALIDADE  — aprovação/parada assintótica por SEVERIDADE (Artigo 14; cobrador
                 irmão: test_revisao_fecha_por_problema.py — este arquivo NÃO o repete);
  · COBERTURA  — 100%: cada item do escopo com as CINCO LENTES fechadas (implementado ·
                 revisado · suíte que morde · E2E com confirmação direta · auditado),
                 medido por AUDITOR EXTERNO isolado; a conta do 100% é do SCRIPT;
  · COERÊNCIA  — 100%: a régua inteira, item a item, zero VIOLADO e zero NÃO-MEDIDO,
                 pelo mesmo desenho de auditor.

O IRMÃO cobra as frases PROIBIDAS de fecho; ESTE cobra a PRESENÇA das peças — schema,
conta em JS, isolamento, desfechos declarados. Ele lê TEXTO (Artigo 4, dito na cara):
prova que a instrução escrita carrega as peças, não que a execução as obedeceu — isso é
da telemetria e dos harnesses de lib/test_qa_loop_motor.py.

    python3 scripts/test_pilares_de_revisao.py
"""
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

MOTORES = [
    "plugins/project-skills/skills/qa-loop/references/motor.js",
    "plugins/project-skills/skills/sprint/references/motor.js",
]
CASCAS = [
    "plugins/project-skills/skills/qa-loop/SKILL.md",
    "plugins/project-skills/skills/sprint/SKILL.md",
]
CONTRATO = "_shared/dimensoes-de-revisao.md"

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


def ler(rel):
    with open(os.path.join(RAIZ, rel), encoding="utf-8") as fh:
        return fh.read()


print("\n== o contrato declara os pilares e as âncoras ==")
c = ler(CONTRATO)
for label, trecho in [
    ("a seção dos pilares existe", "## Os três pilares"),
    ("COBERTURA fecha por 100% com as cinco lentes", "cinco lentes"),
    ("o FURO nomeia item e lente", "FURO, nomeando item e lente"),
    ("quem soma o 100% é o script", "quem soma o 100% é o script"),
    ("a seção das âncoras existe", "## As três âncoras"),
    ("âncora ausente é declarada, nunca aprovação por omissão",
     "nunca vira aprovação por omissão"),
    ("a seção do auditor externo existe", "## O auditor externo"),
    ("E2E fora do portão, dentro da aprovação", "fora do portão mecânico"),
    ("o veredito literal da lente E2E ausente", "COBERTURA NÃO MEDIDA NA LENTE E2E"),
    ("reaberto/minerado fora da conta, declarados", "FORA da conta do 100%"),
]:
    check("contrato: %s" % label, trecho in c, "(faltou %r)" % trecho)

for rel in MOTORES:
    print("\n== %s ==" % rel)
    m = ler(rel)
    check("schema AUDIT_COBERTURA com as lentes e vereditos",
          "AUDIT_COBERTURA" in m and "'sem-infra'" in m and "'antipadrao'" in m
          and "'descoberta'" in m)
    check("schema AUDIT_COERENCIA item a item",
          "AUDIT_COERENCIA" in m and "'violado'" in m and "'nao-medido'" in m
          and "foraDaConta" in m)
    check("o auditor é isolado (SEM_HISTORICO presente)",
          "SEM_HISTORICO" in m and "NÃO recebe os achados do revisor" in m)
    check("as três âncoras entram por args, com ausência declarada",
          "ARGS.pedidos" in m and "pedidosAusentes" in m and "AUSENTE" in m)
    check("a conta do 100% é do script (furosDe em JS)",
          "furosDe" in m and "furosCobertura" in m
          and "i.veredito === 'violado' || i.veredito === 'nao-medido'" in m)
    check("dispensa de lente é ratificação do dono, por args",
          "ARGS.lentesDispensadas" in m)
    check("lente E2E sem infra tem o veredito literal do contrato",
          "COBERTURA NÃO MEDIDA NA LENTE E2E" in m)
    check("auditor mudo nunca fecha",
          "auditoria externa dos pilares não respondeu" in m
          or "auditor externo não respondeu" in m)
    check("o return devolve os três pilares",
          "pilares:" in m and "cobertura:" in m and "coerencia:" in m)
    # Isolamento é checagem NEGATIVA: os prompts de auditoria não interpolam o
    # histórico do laço. O recorte vai do primeiro prompt de auditor até o fim do
    # segundo (o template literal fecha em backtick + quebra dupla).
    ini = m.find("const auditCoberturaPrompt")
    fim = m.find("`\n\n", m.find("const auditCoerenciaPrompt"))
    trecho = m[ini:fim] if ini != -1 and fim != -1 else ""
    check("os prompts de auditoria não interpolam review/rounds/openFindings/trilho",
          bool(trecho) and not re.search(r"\breview\b|\bopenFindings\b|\brounds\b|trilho\(", trecho),
          "(recorte %d..%d)" % (ini, fim))

print("\n== as cascas leem a âncora PEDIDO com fail-open ==")
for rel in CASCAS:
    s = ler(rel)
    check("%s: fail-open do caderno de pedidos declarado" % rel,
          "pedidosAusentes" in s and "intent-guard" in s)
    check("%s: dispensa de lente documentada como ratificação" % rel,
          "lentesDispensadas" in s)

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
