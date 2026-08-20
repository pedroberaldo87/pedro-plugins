#!/usr/bin/env python3
"""Suíte da segunda opinião — stdlib, sem framework.

O que ela protege: a skill /2op é chamada com um pedido de modelo, não com uma
garantia. Quando o titular da sessão já é o mesmo modelo pedido (caso comum:
sessão em claude-opus-5[1m] chamando /2op-opus), o corpo que AFIRMA "você é o
Opus 5" fabrica confiança — o titular lê o CONCORDO no próximo prompt como
corroboração independente de outra cabeça. Mandar o revisor se autodeclarar não
resolvia (a testemunha era o réu): quem confere é `plugins/2op/lib/quem_serviu.py`,
que lê o campo `model` do transcrito e acusa quando o titular serviu a si mesmo.

    python3 scripts/test_2op_identidade.py
"""

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
SKILLS = ["2op", "2op-opus", "2op-sonnet"]

# O que o corpo não pode dizer: identidade afirmada como fato.
AFIRMA_IDENTIDADE = re.compile(r"Você é o \*\*\w+ 5\*\*")
# Aviso preso a condição que o revisor não consegue avaliar: o transcrito não
# rotula qual modelo escreveu cada turno anterior, então "se for da mesma
# família do modelo que produziu o trabalho acima" nunca dispara — guarda de
# aparência. A declaração tem que ser incondicional.
CONDICIONAL_INVERIFICAVEL = re.compile(
    r"se\s+for\s+da\s+mesma\s+família", re.UNICODE)
# O termo observável: a família que a skill PEDIU, escrita literal no corpo.
FAMILIA_PEDIDA = {"2op": "Fable", "2op-opus": "Opus", "2op-sonnet": "Sonnet"}

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


def ler(nome):
    p = os.path.join(ROOT, "plugins/2op/skills", nome, "SKILL.md")
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def corpo_e_descricao(txt):
    partes = txt.split("---\n")
    frontmatter = partes[1]
    corpo = "---\n".join(partes[2:])
    desc = [ln for ln in frontmatter.splitlines() if ln.startswith("description:")][0]
    return corpo, desc[len("description:"):].strip()


sys.path.insert(0, os.path.join(ROOT, "plugins/check-skills/lib"))
import varredura  # noqa: E402

print("2op · identidade não se afirma, se confere")
for nome in SKILLS:
    corpo, desc = corpo_e_descricao(ler(nome))
    m = AFIRMA_IDENTIDADE.search(corpo)
    check("%s: o corpo não afirma a identidade do modelo" % nome,
          m is None, m.group(0) if m else "")
    c = CONDICIONAL_INVERIFICAVEL.search(corpo)
    check("%s: o aviso não depende de condição que o revisor não pode conferir" % nome,
          c is None, c.group(0) if c else "")
    check("%s: o corpo não pede autodeclaração — quem confere é o transcrito" % nome,
          "quem_serviu.py" in corpo and "qual modelo você é de fato" not in corpo)
    check("%s: o corpo escreve literal a família que a skill pediu" % nome,
          "**%s**" % FAMILIA_PEDIDA[nome] in corpo)
    # Invariante viva, nos DOIS estados possíveis. Enquanto o arquivo proíbe o modelo
    # de invocar, a lente 8 do check-skills isenta a skill e a frase pode falar com
    # quem digita a barra. Se essa proibição sair, a lente volta a cobrar — e aí a
    # description precisa da frase de situação. Travar só num dos dois estados foi o
    # que fez esta asserção reprovar uma description honesta.
    caminho = os.path.join(ROOT, "plugins/2op/skills", nome, "SKILL.md")
    isenta = varredura._so_do_usuario(caminho)
    check("%s: ou o modelo é proibido de invocar, ou a description casa a lente 8" % nome,
          isenta or varredura.SITUACAO.search(desc) is not None, desc)
    check("%s: a description diz ao usuário qual barra digitar" % nome,
          "/%s" % nome in desc, desc)

print("\n%d ok, %d FAIL" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
