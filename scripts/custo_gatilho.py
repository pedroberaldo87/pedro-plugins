#!/usr/bin/env python3
"""custo_gatilho.py — inventário do custo fixo por sessão dos gatilhos da família.

O `description` de toda skill instalada entra no prompt de TODA sessão, tenha ela
sido invocada ou não. É custo fixo, e é de redação: quem escreve descrição longa
cobra do usuário em toda conversa que ele abrir.

Este script é o inventário desse custo para a família de skills de projeto (o
plugin `project-skills` mais a sabatina), e o cobrador do orçamento: a soma de hoje
tem que ficar ABAIXO do que as mesmas skills custavam espalhadas em plugins
separados. Esse "antes" está congelado em `.claude/custo-gatilho.baseline.json`,
medido no tronco antes da mudança de casa — arquivo que some do tronco não dá para
remedir depois.

Uso:
    python3 scripts/custo_gatilho.py            # inventário, exit 1 se estourar
    python3 scripts/custo_gatilho.py --json

A unidade medida é CARACTERE, que é o que dá para contar sem tokenizer (o repo é
stdlib only). O token estimado sai na tabela como referência humana (~4 caracteres
por token), e nunca é o número que decide.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, ".claude", "custo-gatilho.baseline.json")

# A família: o plugin novo inteiro, mais a sabatina que se juntou a ele.
FAMILIA = [("project-skills", None), ("grill-me", "grill-me")]

DESC = re.compile(r"^description:\s*(.*?)\n(?=\w+:|---)", re.S | re.M)


def _descricao(caminho):
    with open(caminho, encoding="utf-8") as f:
        m = DESC.search(f.read())
    return m.group(1).strip() if m else ""


def inventario():
    """[(caminho relativo, caracteres)] de cada skill da família, em ordem."""
    itens = []
    for plugin, so_esta in FAMILIA:
        base = os.path.join(ROOT, "plugins", plugin, "skills")
        if not os.path.isdir(base):
            continue
        for skill in sorted(os.listdir(base)):
            if so_esta and skill != so_esta:
                continue
            arq = os.path.join(base, skill, "SKILL.md")
            if os.path.isfile(arq):
                itens.append((os.path.relpath(arq, ROOT), len(_descricao(arq))))
    return itens


def confere():
    itens = inventario()
    total = sum(n for _, n in itens)
    with open(BASELINE, encoding="utf-8") as f:
        teto = json.load(f)["total_caracteres"]
    return itens, total, teto


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    itens, total, teto = confere()
    estourou = total >= teto

    if args.json:
        print(json.dumps({
            "por_skill": [{"arquivo": a, "caracteres": n} for a, n in itens],
            "total_caracteres": total, "teto_caracteres": teto,
            "estourou": estourou,
        }, ensure_ascii=False, indent=2))
        return 1 if estourou else 0

    print("Custo fixo por sessão — gatilho das skills da família\n")
    for arq, n in itens:
        print("  %5d ch  ~%4d tok  %s" % (n, n // 4, arq))
    print("\n  soma de hoje ....... %5d ch  (~%d tok)" % (total, total // 4))
    print("  teto (plugins separados) %5d ch  (~%d tok)" % (teto, teto // 4))
    if estourou:
        print("\nESTOUROU em %d caracteres. A família tem que custar MENOS que as skills"
              " espalhadas custavam — encurte o `description` das maiores." % (total - teto + 1))
    else:
        print("\nfolga de %d caracteres (~%d tok)." % (teto - total, (teto - total) // 4))
    return 1 if estourou else 0


if __name__ == "__main__":
    sys.exit(main())
