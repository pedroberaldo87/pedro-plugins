#!/usr/bin/env python3
"""Suíte que compara CAMINHO como TEXTO é suíte que reprova código certo — e isto acusa.

O que ele procura, e por que
----------------------------
Em 2026-08-11 seis suítes reprovaram no Windows sem que nada estivesse quebrado:
elas comparavam caminho com `==`, `in`, `startswith` ou `endswith` contra um
literal escrito com barra normal. O mesmo doc com barra invertida e com barra normal é o
mesmo arquivo e textos diferentes, então a asserção mentia — na pior direção, a de
reprovar o que funciona.

A acusação é ESTREITA de propósito: só dispara quando o literal do outro lado
parece um caminho (tem `/` no meio, ou é um nome de arquivo com extensão conhecida).
Comparar duas strings que por acaso têm barra — uma URL, um regex, um trecho de
JSON — não é o defeito, e acusar isso faria o cobrador ser desligado na primeira
semana, que é o destino de todo cobrador barulhento.

Isenção: `caminho-ok: <motivo>` na linha. Sempre com o motivo escrito.

    python3 scripts/caminho_como_texto_check.py            # sai 1 se achar
    python3 scripts/caminho_como_texto_check.py --lista    # só os arquivos varridos
"""

import argparse
import ast
import glob
import os
import sys

for _canal in (sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Onde procurar. Suíte primeiro, porque é onde o defeito nasce e onde ele mente.
ALVOS = ("plugins/*/lib/test_*.py", "plugins/*/hooks/test_*.py",
         "scripts/test_*.py", "_shared/test_*.py")

# Extensões que fazem um literal sem barra ainda parecer caminho ("x.py", "a.json").
EXTS = (".py", ".sh", ".md", ".json", ".mjs", ".js", ".html", ".yml", ".yaml", ".jsonl")

# Os métodos de string que comparam caminho por texto quando o argumento é caminho.
METODOS = ("startswith", "endswith")

ISENCAO = "caminho-ok:"


# Onde um caminho deste repositório costuma começar. Sem esta âncora, `feat/squash`
# (nome de branch) e `mkt/alfa` (texto de prosa) entram na conta — e a primeira
# varredura devolveu 217 achados, dos quais quase nenhum era o defeito.
PREFIXOS = (".claude", ".github", "plugins/", "scripts/", "_shared/", "~/", "./",
            "lib/", "hooks/", "skills/", "docs/", "graphify-out/")


def parece_caminho(v):
    """O literal descreve um caminho DESTE repositório? Estreito de propósito.

    Três exigências juntas, e as três existem para calar falso positivo medido:

    - **sem espaço e sem `·`** — literal com espaço é frase que contém uma barra
      (`"morto · src/a.ts: prob_h"`), não um caminho;
    - **com separador no meio** — `".html"` sozinho é extensão, não caminho, e
      `endswith(".html")` é uso legítimo;
    - **ancorado**: ou termina em extensão conhecida, ou começa onde um caminho
      deste repositório começa. `feat/squash` é nome de branch e não passa por
      nenhuma das duas.
    """
    if not isinstance(v, str) or not v.strip():
        return False
    if v.startswith(("http://", "https://", "//")):
        return False          # URL não é caminho de arquivo
    if "\\" in v:
        return False          # já escrito com a barra do Windows: quem fez, sabia
    if any(c in v for c in " \t·:'\"<>|"):
        return False          # frase, não caminho
    if "/" not in v.strip("/"):
        return False          # sem separador no meio não há barra a divergir
    return v.endswith(EXTS) or v.startswith(PREFIXOS)


# O outro lado da comparação precisa VIR do sistema de arquivos. Sem esta exigência
# a varredura acusa `"..." in skill_md` — procurar o texto ".claude/docs/x.md" DENTRO  # casa-ok: o exemplo é o próprio objeto da checagem
# de um documento, onde a barra é sempre `/` e nada diverge. Medido: de 52 achados,
# só os que casam aqui eram o defeito.
FONTES = ("os.path", "os.listdir", "os.getcwd", "os.walk", "os.scandir",
          "tempfile", "glob.glob", "pathlib", "abspath", "realpath", "normpath",
          "expanduser", "dirname", "basename", "relpath")
NOMES = ("caminho", "path", "dir", "arquivo", "file", "alvo", "destino", "raiz", "root")


def _vem_do_disco(no):
    """Esse nó carrega caminho vindo do sistema de arquivos (e não texto lido)?"""
    txt = ast.dump(no)
    if any(f in txt for f in FONTES):
        return True
    # nome de variável que anuncia caminho — `caminho`, `d["caminho"]`, `r[0]["path"]`
    alvos = [n.id for n in ast.walk(no) if isinstance(n, ast.Name)]
    alvos += [n.attr for n in ast.walk(no) if isinstance(n, ast.Attribute)]
    alvos += [n.value for n in ast.walk(no)
              if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    return any(any(k in str(a).lower() for k in NOMES) for a in alvos)


def _literais(no):
    """Os literais de string dentro de um nó — direto ou numa lista/tupla."""
    if isinstance(no, ast.Constant) and isinstance(no.value, str):
        return [no.value]
    if isinstance(no, (ast.List, ast.Tuple)):
        out = []
        for e in no.elts:
            out.extend(_literais(e))
        return out
    return []


def achados_em(caminho):
    try:
        fonte = open(caminho, encoding="utf-8").read()
    except OSError:
        return []
    try:
        arvore = ast.parse(fonte)
    except SyntaxError:
        return []
    linhas = fonte.splitlines()
    fora = []

    def isento(n):
        i = getattr(n, "lineno", 0) - 1
        return 0 <= i < len(linhas) and ISENCAO in linhas[i]

    for n in ast.walk(arvore):
        # a == "x/y"  ·  a != "x/y"
        if isinstance(n, ast.Compare) and not isento(n):
            for op, dir_ in zip(n.ops, n.comparators):
                if isinstance(op, (ast.Eq, ast.NotEq, ast.In, ast.NotIn)):
                    # no `in`, o literal é o AGULHA (esquerda) e o palheiro é a
                    # direita; no `==` o literal costuma ser a direita.
                    lit, outro = ((n.left, dir_) if isinstance(op, (ast.In, ast.NotIn))
                                  else (dir_, n.left))
                    if not _vem_do_disco(outro):
                        continue
                    for v in _literais(lit):
                        if parece_caminho(v):
                            fora.append((n.lineno, "compara com %r" % v))
        # a.startswith("x/y")  ·  a.endswith("x/y")
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in METODOS and n.args and not isento(n)
                and _vem_do_disco(n.func.value)):
            for v in _literais(n.args[0]):
                if parece_caminho(v):
                    fora.append((n.lineno, "%s(%r)" % (n.func.attr, v)))
    return fora


def varre(raiz=RAIZ):
    arquivos = []
    for pat in ALVOS:
        arquivos.extend(sorted(glob.glob(os.path.join(raiz, pat))))
    fora = []
    for f in arquivos:
        for lin, o_que in achados_em(f):
            fora.append((os.path.relpath(f, raiz), lin, o_que))
    return arquivos, fora


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--lista", action="store_true")
    a = ap.parse_args(argv)
    arquivos, fora = varre()
    if a.lista:
        for f in arquivos:
            print(os.path.relpath(f, RAIZ))
        return 0
    print("caminho-como-texto: %d arquivo(s) varrido(s)" % len(arquivos))
    if not fora:
        print("nenhuma comparação de caminho por texto cru.")
        return 0
    print("\n⛔ %d comparação(ões) de caminho feita(s) como TEXTO:" % len(fora))
    for f, lin, o_que in fora:
        print("  %s:%d  %s" % (f, lin, o_que))
    print("\nUse `_shared/caminho_igual.py` (igual/contem/termina_em) — ele normaliza")
    print("os dois lados. Isenção legítima: `caminho-ok: <motivo>` na linha.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
