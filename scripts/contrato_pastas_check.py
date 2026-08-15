#!/usr/bin/env python3
"""Cobrador do contrato de pastas — R-19.

Toda pasta de trabalho de um projeto tem casa declarada numa fonte só: a tabela
"As pastas" de `_shared/contrato-familia.md`. Este check lê essa tabela e acusa
qualquer `.claude/<pasta>/` citada por uma SKILL.md que não esteja lá.

O que NÃO conta: caminho sob `~/` ou `$HOME` (estado cross-projeto, que não é
pasta de trabalho) e o que aparece dentro de bloco de código de shell continua
contando — citar é citar.

    python3 scripts/contrato_pastas_check.py            # 0 = limpo, 1 = pasta fora do contrato
"""

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
CONTRATO = os.path.join(ROOT, "_shared", "contrato-familia.md")

# `~/.claude/x/` e `$HOME/.claude/x/` ficam de fora pelo grupo de prefixo. As aspas
# entram no grupo porque em shell o caminho vem citado (`"$HOME"/.claude/…`), e sem
# elas o prefixo não casava: o estado cross-projeto do harness aparecia como pasta de
# trabalho não declarada.
CITACAO = re.compile(
    r"""(~|\$HOME|\{HOME\}|CLAUDE_CONFIG_DIR[:\-\w]*\})?["']?(/?)"""
    r"""\.claude/(\.?[a-z0-9][a-z0-9_-]*)/""")


def declaradas(texto):
    """As pastas da tabela 'As pastas' — só as linhas de tabela daquela seção."""
    trecho = texto.split("## As pastas", 1)
    if len(trecho) < 2:
        return set()
    corpo = trecho[1].split("\n## ", 1)[0]
    return {
        m.group(3)
        for linha in corpo.splitlines()
        if linha.startswith("|")
        for m in CITACAO.finditer(linha)
    }


# Quem ESCOLHE pasta de trabalho não é só a prosa da skill: o motor do /sprint e os
# hooks a escolhem em código, e varrer só Markdown deixava justamente eles de fora —
# a pasta nova nasceria num `.js` ou num `.sh` sem nada acusar. Suíte fica de fora de
# propósito: teste cria e apaga pasta temporária o tempo todo, e cobrá-lo aqui viraria
# ruído em cima de quem não escolhe nada.
LIDOS = ("SKILL.md", ".js", ".sh", ".py")


def _e_fonte(nome):
    if nome == "SKILL.md":
        return True
    if nome.startswith("test_") or nome.endswith(("_test.py", ".test.js")):
        return False
    return nome.endswith((".js", ".sh", ".py"))


def skills(raiz):
    for base, dirs, arqs in os.walk(os.path.join(raiz, "plugins")):
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for a in arqs:
            if _e_fonte(a):
                yield os.path.join(base, a)


def varre(raiz=ROOT):
    with open(CONTRATO, encoding="utf-8") as fh:
        casa = declaradas(fh.read())
    fora = []
    for arq in sorted(skills(raiz)):
        with open(arq, encoding="utf-8") as fh:
            for n, linha in enumerate(fh, 1):
                for m in CITACAO.finditer(linha):
                    if m.group(1) or m.group(3) in casa:
                        continue
                    fora.append((os.path.relpath(arq, raiz), n, m.group(3)))
    return casa, fora


if __name__ == "__main__":
    casa, fora = varre()
    print("contrato: %d pastas declaradas" % len(casa))
    for arq, n, pasta in fora:
        print("  FORA DO CONTRATO  .claude/%s/  %s:%d" % (pasta, arq, n))
    if fora:
        print(
            "\n%d citação(ões) de pasta não declarada. Declare a casa na tabela "
            "'As pastas' de _shared/contrato-familia.md (e rode scripts/sync-shared.sh)."
            % len(fora)
        )
        sys.exit(1)
    print("ok — nenhuma pasta de trabalho fora do contrato")
