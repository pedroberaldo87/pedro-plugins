#!/usr/bin/env python3
"""Suíte da régua de POR ONDE a pergunta chega — stdlib, sem framework.

O que ela protege: a régua nasce em _shared/ e chega INTEIRA a toda skill que
pergunta ao dono. Três defeitos ela pega: cópia vendorada defasada, cláusula
que sumiu da fonte, e SKILL.md que voltou a repetir o texto em vez de apontar.
Confere também que a régua invoca a skill de página PELO NOME — caminho para
dentro de outro plugin quebra o Artigo 9.

    python3 scripts/test_regua_de_pergunta.py
"""

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
SHARED = os.path.join(ROOT, "_shared")
ARQ = "regua-de-pergunta.md"

FONTE = os.path.join(SHARED, ARQ)
# Os nove destinos: toda skill em que a pergunta ao dono tem OPÇÕES — as que
# usam AskUserQuestion, a grill-me (pergunta em rodadas sem usar a ferramenta) e
# as que param no meio do fluxo pra o dono escolher entre alternativas.
def _destinos_do_vendoring(nome):
    """Os destinos DECLARADOS em scripts/sync-shared.sh, lidos do arquivo.

    A lista era escrita à mão, e o F14.2 a venceu: `start-doc`, `sovai` e `qa-loop`
    mudaram de plugin, os caminhos velhos deixaram de existir, e a suíte ficou
    vermelha por endereço em vez de por defeito. Quem sabe onde cada cópia mora é o
    próprio vendoring — derivar dele faz o próximo rename chegar aqui sozinho.
    """
    sync = os.path.join(ROOT, "scripts", "sync-shared.sh")
    if not os.path.exists(sync):
        # O vendoring é a fonte dos destinos: sem ele não há o que conferir, e a
        # suíte tem que DIZER isso em vez de morrer em traceback — falha por
        # infra ausente e falha por defeito não podem ter a mesma cara.
        raise SystemExit("scripts/sync-shared.sh nao existe — sem ele nao ha "
                         "destino declarado para conferir")
    with open(sync, encoding="utf-8") as fh:
        bloco = re.search(r"^SPECS=\((.*?)^\)", fh.read(), re.S | re.M)
    saida = []
    for linha in (bloco.group(1) if bloco else "").splitlines():
        achou = re.search(r'"([^"]+)::([^"]+)"', linha)
        if achou and achou.group(2) == nome:
            saida.append(achou.group(1))
    return saida


DESTINOS = _destinos_do_vendoring(ARQ)

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

print("\n== a régua nas nove cópias vendoradas ==")
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

print("\n== as nove skills APONTAM em vez de repetir ==")
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
