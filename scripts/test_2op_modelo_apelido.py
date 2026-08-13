#!/usr/bin/env python3
"""O 2op pede o modelo por APELIDO DE FAMÍLIA, não por ID cravado.

Modo de falha que isso evita, e ele é SILENCIOSO: `model: claude-fable-5` no
frontmatter só troca de modelo se aquele identificador exato existir para quem
instalou. Fora da allowlist da organização — ou em Bedrock/Foundry, onde o
identificador é outro — a troca não acontece, a sessão segue no modelo titular
e o corpo ainda anuncia "Você foi chamado como Fable 5". A mesma armadilha
volta no dia em que sair o modelo seguinte.

Fonte que autoriza o apelido (conferida nesta sessão, Claude Code 2.1.229):
o próprio binário carrega o resolvedor `resolveSkillModelOverride` ao lado de
`resolveModelAliasEnvFree` / `stepDownRestrictedFamilyAliasPick`, e traz a
mensagem literal "Switch to a public model alias (opus, sonnet, fable)".

    python3 scripts/test_2op_modelo_apelido.py
"""

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)

# skill -> apelido de família esperado no campo model
APELIDOS = {"2op": "fable", "2op-opus": "opus", "2op-sonnet": "sonnet"}

# ID cravado: qualquer coisa que pareça um identificador de modelo com versão.
ID_CRAVADO = re.compile(r"claude-[a-z]+-\d")
# Número de versão colado no nome da família, em qualquer lugar do arquivo.
VERSAO_NA_FAMILIA = re.compile(r"\b(Fable|Opus|Sonnet)\s+\d", re.IGNORECASE)

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


print("2op · modelo se pede por apelido de família, não por ID cravado")
for nome, apelido in APELIDOS.items():
    txt = ler(nome)
    linha_model = [ln for ln in txt.splitlines() if ln.startswith("model:")]
    check("%s: tem campo model no frontmatter" % nome, len(linha_model) == 1)
    if linha_model:
        # comentário YAML ao lado guarda a fonte que autoriza o apelido
        valor = linha_model[0][len("model:"):].split("#")[0].strip()
        check("%s: model é o apelido de família '%s'" % (nome, apelido),
              valor == apelido, valor)

    m = ID_CRAVADO.search(txt)
    check("%s: nenhum ID de modelo cravado no arquivo" % nome,
          m is None, m.group(0) if m else "")

    m = VERSAO_NA_FAMILIA.search(txt)
    check("%s: nenhum número de versão colado no nome da família" % nome,
          m is None, m.group(0) if m else "")

# Brinde do mesmo conserto: o catálogo volta a terminar com quebra de linha.
CATALOGO = os.path.join(ROOT, ".claude-plugin/marketplace.json")
with open(CATALOGO, "rb") as fh:
    bruto = fh.read()
check("marketplace.json termina com quebra de linha",
      bruto.endswith(b"\n"), repr(bruto[-4:]))

print("\n%d ok, %d FAIL" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
