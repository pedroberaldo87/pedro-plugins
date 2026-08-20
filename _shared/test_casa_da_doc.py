#!/usr/bin/env python3
"""Suíte do resolvedor da casa da doc — a cascata nos dois cenários de casa.

Um projeto com `docs/` na raiz e um projeto só com `.claude/docs/` respondem  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
caminhos diferentes, e as duas metades (Python e bash) têm que concordar: duas
implementações da mesma cascata que divergem são a dívida de novo, com sotaque.

    python3 _shared/test_casa_da_doc.py
"""

import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from bash_posix import bash_posix  # noqa: E402
from casa_da_doc import casa  # noqa: E402

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


def em_bash(raiz, *partes):
    if BASH is None:
        return None
    prova = 'source "%s/lib-casa-da-doc.sh"\ncasa_da_doc %s\n' % (
        AQUI, " ".join('"%s"' % p for p in (raiz,) + partes))
    r = subprocess.run([BASH, "-c", prova], capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    return r.stdout.strip()


BASH = bash_posix()

# ── os três arquivos do contrato existem ───────────────────────────────────

print("\n[o contrato — prosa, Python e bash, os três]")

for nome in ("casa-da-doc.md", "casa_da_doc.py", "lib-casa-da-doc.sh"):
    check("%s existe em _shared" % nome, os.path.isfile(os.path.join(AQUI, nome)))

# ── as duas metades da premissa, escritas no cardápio ──────────────────────

print("\n[a premissa inteira — doc visível, segredo escondido]")

PROSA = open(os.path.join(AQUI, "casa-da-doc.md"), encoding="utf-8").read()

check("a doc canônica mora em docs/ na raiz, visível", "`docs/` na raiz" in PROSA)
check("o segredo mora em .claude/secrets/, escondida", ".claude/secrets/" in PROSA)
check("a pasta do segredo fica fora do git (gitignore, não só o ponto no nome)",
      ".gitignore" in PROSA and "fora do git" in PROSA)

# ── a premissa chega às skills que decidem onde a doc nasce ────────────────

# Contrato em prosa sem cobrador de PRESENÇA vira contrato que ninguém lê: o
# cardápio da família e a pauta de concepção são os dois pontos onde a premissa
# encontra quem escreve doc. Os dois APONTAM para este arquivo — repetir a prosa
# aqui é o drift que a premissa anti-drift proíbe.

print("\n[a premissa nos dois SKILL.md — cardápio da família e pauta de concepção]")

RAIZ = os.path.dirname(AQUI)
SKILLS = os.path.join(RAIZ, "plugins", "project-skills", "skills")

for rotulo, rel in (
    ("cardápio da família", os.path.join("project-skills", "SKILL.md")),
    ("pauta de concepção", os.path.join("start", "SKILL.md")),
):
    caminho = os.path.join(SKILLS, rel)
    if not os.path.isfile(caminho):
        check("%s existe" % rotulo, False, caminho)
        continue
    txt = open(caminho, encoding="utf-8").read()
    check("%s: a doc visível nasce em docs/ na raiz" % rotulo,
          "`docs/` na raiz" in txt)
    check("%s: o segredo mora em .claude/secrets/, fora do git" % rotulo,
          ".claude/secrets/" in txt and "fora do git" in txt)
    check("%s: aponta para o contrato em vez de repetir a prosa" % rotulo,
          "_shared/casa-da-doc.md" in txt)

with tempfile.TemporaryDirectory() as tmp:
    nova = os.path.join(tmp, "casa-nova")
    velha = os.path.join(tmp, "casa-velha")
    ambas = os.path.join(tmp, "casa-dupla")
    vazia = os.path.join(tmp, "sem-casa")
    os.makedirs(os.path.join(nova, "docs"))
    os.makedirs(os.path.join(velha, ".claude", "docs"))
    os.makedirs(os.path.join(ambas, "docs"))
    os.makedirs(os.path.join(ambas, ".claude", "docs"))
    os.makedirs(vazia)

    # ── cenário 1: a casa canônica, docs/ na raiz ──────────────────────────

    print("\n[cenário 1 — projeto com docs/ na raiz]")

    check("a pasta é <raiz>/docs", casa(nova) == os.path.join(nova, "docs"), casa(nova))
    check("o arquivo cai dentro dela",
          casa(nova, "architecture.md") == os.path.join(nova, "docs", "architecture.md"),
          casa(nova, "architecture.md"))
    check("subpasta também (fluxos/)",
          casa(nova, "fluxos", "f.html") == os.path.join(nova, "docs", "fluxos", "f.html"))

    # ── cenário 2: a casa antiga, só .claude/docs/ ─────────────────────────  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa

    print("\n[cenário 2 — projeto só com .claude/docs/ (retrocompatibilidade)]")  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa

    check("a pasta é <raiz>/.claude/docs",  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
          casa(velha) == os.path.join(velha, ".claude", "docs"), casa(velha))
    check("o arquivo cai dentro dela",
          casa(velha, "architecture.md")
          == os.path.join(velha, ".claude", "docs", "architecture.md"))

    # ── os dois desempates ─────────────────────────────────────────────────

    print("\n[desempate — as duas casas, e nenhuma casa]")

    check("com as duas, a canônica ganha", casa(ambas) == os.path.join(ambas, "docs"),
          casa(ambas))
    check("sem nenhuma, a doc nasce na canônica",
          casa(vazia) == os.path.join(vazia, "docs"), casa(vazia))
    check("o resolvedor não cria pasta nenhuma",
          not os.path.isdir(os.path.join(vazia, "docs")))

    # ── a metade bash responde o mesmo ─────────────────────────────────────

    print("\n[bash — a mesma cascata, mesmo resultado]")

    if BASH is None:
        check("bash POSIX disponível", False, "(sem bash — a metade bash não foi medida)")
    else:
        for rotulo, raiz, partes in (
            ("casa nova", nova, ()),
            ("casa velha", velha, ()),
            ("as duas casas", ambas, ()),
            ("sem casa", vazia, ()),
            ("arquivo na casa velha", velha, ("architecture.md",)),
            ("subpasta na casa nova", nova, ("fluxos", "f.html")),
        ):
            esperado = casa(raiz, *partes)
            check("bash concorda com Python — %s" % rotulo,
                  em_bash(raiz, *partes) == esperado, em_bash(raiz, *partes))

        check("bash tolera raiz com barra no fim",
              em_bash(nova + "/") == os.path.join(nova, "docs"), em_bash(nova + "/"))

print("\n%d passou · %d falhou" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
