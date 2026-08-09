#!/usr/bin/env python3
"""Suíte dos apelidos das skills da família de projeto.

Apelido é a palavra que o dono realmente digita. A FAMÍLIA SE DESCOBRE LENDO A PASTA
`skills/` — nenhuma lista de nomes aqui dentro (Artigo 9): a versão anterior desta suíte
trazia seis nomes escritos à mão e já nascia vencida, sem cobrar `monitorar` nem
`project-skills`, as duas skills que estavam sem apelido nenhum.

Três coisas se provam, todas derivadas do disco:

1. toda skill da pasta declara pelo menos um termo entre aspas na `description` — é por
   esses termos que o dono chama a skill sem lembrar o nome em inglês;
2. toda skill declara pelo menos um termo que NÃO é o próprio nome — apelido que repete o
   nome não é apelido, é o nome;
3. nenhum termo é declarado por duas skills da família — apelido disputado é apelido que
   não chama ninguém em particular.

⚠️ O QUE ESTA SUÍTE **NÃO** PROVA. Ela lê texto: garante que o apelido está declarado e é
exclusivo dentro da família. Quem escolhe a skill quando o dono digita é um modelo, lendo
as descriptions de TODAS as skills carregadas na máquina — inclusive as de fora deste
marketplace. A prova de roteamento de verdade é rodar o harness de cabeça (`claude -p
"<apelido>" --plugin-dir <este plugin>`) e ver qual skill a chamada invoca; ela depende de
modelo e de que mais está instalado, então não cabe numa suíte determinística.
"""

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.join(AQUI, os.pardir, "skills")

FALHAS = []


def check(rotulo, cond):
    print(("  ok   " if cond else "  FAIL ") + rotulo)
    if not cond:
        FALHAS.append(rotulo)


def familia():
    """As skills que moram no plugin — lidas do disco, nunca de cor."""
    return sorted(
        d
        for d in os.listdir(SKILLS)
        if os.path.isfile(os.path.join(SKILLS, d, "SKILL.md"))
    )


def termos(skill):
    """Termos entre aspas da description — o que o dono digita, sem a barra."""
    texto = open(os.path.join(SKILLS, skill, "SKILL.md"), encoding="utf-8").read()
    m = re.search(r"^description:(.*?)^---", texto, re.S | re.M)
    if not m:
        return set()
    return {t.lstrip("/").strip().lower() for t in re.findall(r'"([^"]+)"', m.group(1))}


nomes = familia()
check("a pasta skills/ tem skill para conferir", bool(nomes))

print("cada skill da pasta declara como o dono a chama")
declarados = {}
for skill in nomes:
    declarados[skill] = termos(skill)
    check("%s declara algum termo digitável" % skill, bool(declarados[skill]))
    check(
        "%s declara apelido além do próprio nome" % skill,
        bool(declarados[skill] - {skill.lower()}),
    )

print("nenhum apelido é disputado dentro da família")
for skill in nomes:
    for a in declarados[skill]:
        outras = [s for s in nomes if s != skill and a in declarados[s]]
        check("%r só chama %s" % (a, skill), not outras)

print()
if FALHAS:
    print("%d falhou" % len(FALHAS))
    sys.exit(1)
print("ok os apelidos chamam cada um a sua skill")
