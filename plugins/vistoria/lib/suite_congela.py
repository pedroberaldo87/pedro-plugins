#!/usr/bin/env python3
"""A suíte que congela o defeito — o teste espera uma frase que ninguém escreve.

Um teste que compara a saída do programa com uma frase LITERAL só vale enquanto o
programa escrever aquela frase. Trocada a mensagem e não trocado o teste, sobra um
`assert` órfão: ele passa ou falha por outro motivo qualquer, e ninguém percebe que
a linha parou de cobrar o que ela dizia cobrar.

Esta lente extrai todo literal de string comparado dentro de um `assert` das suítes
(`ast` nas suítes Python, regex nas de shell) e procura esse literal no código-alvo —
tudo que não é suíte. Literal que o repositório inteiro nunca PRODUZ vira achado.

Uso:
    python3 plugins/vistoria/lib/suite_congela.py                  # contra o retrato
    python3 plugins/vistoria/lib/suite_congela.py --todos          # tudo
    python3 plugins/vistoria/lib/suite_congela.py --gravar-retrato # congela hoje
    python3 plugins/vistoria/lib/suite_congela.py --root <dir>     # varre outra raiz

stdlib only (requisito do repo).
"""

import argparse
import ast
import json
import os
import re
import sys

RETRATO = ".claude/suite-congela.baseline.json"

EXTS = (".py", ".sh", ".js", ".json", ".md", ".txt", ".yml", ".yaml", ".html")
IGNORA_DIR = (".git", "node_modules", "__pycache__", ".venv")

# Suíte é o arquivo cujo NOME diz que é suíte — o mesmo par de formas que a esteira roda.
EH_SUITE = re.compile(r"(?:^test_.*|.*_test)\.(py|sh)$")

# Nas suítes de shell não há árvore para andar: o literal esperado aparece no argumento
# do `grep`. É esta a parte regex da lente.
GREP_LITERAL = re.compile(r"""grep\s+(?:-\w+\s+)*['"]([^'"]{8,})['"]""")

# Literal curto ("ok", "0"), gabarito de formato ("%s de %d") e template ("{nome}") não
# são frase que o programa escreve — são pedaço. Procurar pedaço só produz ruído.
TEM_PALAVRA = re.compile(r"[A-Za-zÀ-ÿ]{3}")


def interessa(lit):
    """Este literal é uma frase que o programa deveria PRODUZIR?"""
    s = (lit or "").strip()
    if len(s) < 8 or not TEM_PALAVRA.search(s):
        return False
    return "%" not in s and "{" not in s and "\n" not in s


def arquivos(root):
    """Todo arquivo de texto sob a raiz, em caminho relativo."""
    achados = []
    for base, dirs, nomes in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORA_DIR]
        for n in nomes:
            if n.endswith(EXTS):
                achados.append(os.path.relpath(os.path.join(base, n), root))
    return sorted(achados)


def _texto(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def literais_py(fonte):
    """(literal, linha) de todo str comparado dentro de um `assert`."""
    try:
        arv = ast.parse(fonte)
    except SyntaxError:
        return []
    saida = []
    for no in ast.walk(arv):
        if not isinstance(no, ast.Assert):
            continue
        for filho in ast.walk(no.test):
            if isinstance(filho, ast.Constant) and isinstance(filho.value, str):
                saida.append((filho.value, getattr(filho, "lineno", no.lineno)))
    return saida


def literais_sh(fonte):
    saida = []
    for n, linha in enumerate(fonte.splitlines(), 1):
        for m in GREP_LITERAL.finditer(linha):
            saida.append((m.group(1), n))
    return saida


def varre(root="."):
    """Devolve a lista de achados. Cada um é um dict estável, comparável com o retrato."""
    todos = arquivos(root)
    suites = [r for r in todos if EH_SUITE.match(os.path.basename(r))]
    alvo = "\n".join(_texto(root, r) for r in todos
                     if r not in suites and not r.endswith(os.path.basename(RETRATO)))

    achados = []
    for rel in suites:
        fonte = _texto(root, rel)
        linhas = fonte.splitlines()
        pares = literais_py(fonte) if rel.endswith(".py") else literais_sh(fonte)
        vistos = set()
        for lit, n in pares:
            if not interessa(lit) or lit in vistos:
                continue
            vistos.add(lit)
            if lit in alvo:
                continue
            trecho = linhas[n - 1].strip()[:120] if 0 < n <= len(linhas) else lit[:120]
            achados.append({"forma": "assert-orfao", "arquivo": rel, "linha": n,
                            "alvo": lit[:120], "trecho": trecho})
    return achados


def chave(a):
    """Identidade do achado: forma, arquivo e o literal — nunca a linha.

    Pelo mesmo motivo do `desacoplamento_check`: acrescentar um caso no topo da suíte
    empurraria todos os de baixo, e o retrato acusaria como novo o que é o mesmo de
    sempre.
    """
    return "%s|%s|%s" % (a["forma"], a["arquivo"], " ".join(a["alvo"].split()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--gravar-retrato", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    achados = varre(a.root)
    caminho = os.path.join(a.root, RETRATO)

    if a.gravar_retrato:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        conjunto = sorted(set(chave(x) for x in achados))
        with open(caminho, "w", encoding="utf-8") as fh:
            json.dump(conjunto, fh, ensure_ascii=False, indent=1)
        print("retrato gravado: %d achado(s) em %s" % (len(conjunto), RETRATO))
        return 0

    conhecidos = set()
    if not a.todos:
        try:
            with open(caminho, encoding="utf-8") as fh:
                conhecidos = set(json.load(fh))
        except (OSError, ValueError):
            conhecidos = set()

    novos = [x for x in achados if chave(x) not in conhecidos]

    if a.json:
        print(json.dumps({"todos": achados, "novos": novos}, ensure_ascii=False))
        return 1 if novos else 0

    print("suíte que congela o defeito — %d assert(s) órfão(s) no total" % len(achados))
    mostrar = achados if a.todos else novos
    for x in mostrar:
        print("\n%s:%d  espera uma frase que nada no código escreve" % (x["arquivo"], x["linha"]))
        print("   %s" % x["trecho"])
    if a.todos:
        return 1 if achados else 0
    if not novos:
        print("\nNenhum assert órfão NOVO além do retrato.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
