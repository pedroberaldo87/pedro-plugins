#!/usr/bin/env python3
"""O fio morto — script de hook que nenhum caminho chama.

Hook é código que só roda porque ALGUÉM o registrou: o `hooks.json` do plugin aponta
para ele, ou outro script o carrega. Script de hook que nenhum arquivo do repositório
sequer menciona pelo nome não roda nunca — e continua ali, pedindo manutenção e
sendo lido como se valesse.

Esta lente lista todo script sob uma pasta `hooks/` e procura o nome dele em todo o
resto do repositório. Zero menção = fio morto.

Uso:
    python3 plugins/vistoria/lib/fio_morto.py                  # contra o retrato
    python3 plugins/vistoria/lib/fio_morto.py --todos          # tudo
    python3 plugins/vistoria/lib/fio_morto.py --gravar-retrato # congela hoje
    python3 plugins/vistoria/lib/fio_morto.py --root <dir>     # varre outra raiz

stdlib only (requisito do repo).
"""

import argparse
import json
import os
import re
import sys

RETRATO = ".claude/fio-morto.baseline.json"

EXTS = (".py", ".sh", ".js", ".json", ".md", ".txt", ".yml", ".yaml", ".html")
IGNORA_DIR = (".git", "node_modules", "__pycache__", ".venv")

# Suíte de hook não é registrada em `hooks.json` — quem a chama é a esteira, pelo globo.
# Acusá-la de não ter chamador seria acusar o globo de não citar nome.
EH_SUITE = re.compile(r"(?:^test_.*|.*_test)\.(sh|py)$")


def arquivos(root):
    saida = []
    for base, dirs, nomes in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORA_DIR]
        for n in nomes:
            if n.endswith(EXTS):
                saida.append(os.path.relpath(os.path.join(base, n), root))
    return sorted(saida)


def _texto(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def eh_hook(rel):
    partes = rel.split(os.sep)
    return "hooks" in partes[:-1] and rel.endswith((".sh", ".py")) \
        and not EH_SUITE.match(partes[-1])


def varre(root="."):
    """Devolve a lista de achados. Cada um é um dict estável, comparável com o retrato."""
    # O retrato guarda o CAMINHO de cada fio morto, e caminho contém o nome do script:
    # varrê-lo faria o retrato passar por chamador, e o achado sumiria na rodada
    # seguinte à própria gravação. Termômetro não tem febre.
    todos = [r for r in arquivos(root) if r != RETRATO]
    textos = {r: _texto(root, r) for r in todos}

    achados = []
    for rel in [r for r in todos if eh_hook(r)]:
        base = os.path.basename(rel)
        # O próprio arquivo não conta como chamador de si mesmo.
        if any(base in t for o, t in textos.items() if o != rel):
            continue
        achados.append({"forma": "hook-sem-chamador", "arquivo": rel, "linha": 0,
                        "alvo": base,
                        "trecho": "0 menção a %s em %d arquivo(s) da raiz"
                                  % (base, len(todos) - 1)})
    return achados


def chave(a):
    return "%s|%s" % (a["forma"], a["arquivo"])


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

    print("fio morto — %d hook(s) sem chamador no total" % len(achados))
    for x in (achados if a.todos else novos):
        print("\n%s  nenhum arquivo o registra nem o carrega" % x["arquivo"])
        print("   %s" % x["trecho"])
    if a.todos:
        return 1 if achados else 0
    if not novos:
        print("\nNenhum fio morto NOVO além do retrato.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
