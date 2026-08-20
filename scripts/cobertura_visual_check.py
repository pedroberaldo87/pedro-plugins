#!/usr/bin/env python3
"""cobertura_visual_check.py — reprova quando a regra da COBERTURA VISUAL some da lei.

O Artigo 12 da constituição diz que todo fluxo nomeado na documentação tem diagrama e
todo módulo tem o seu, e que o diagrama é camada da documentação canônica. A regra foi
decidida pelo dono e colada no texto canônico — mas texto sem cobrador some calado: o
próximo re-projeto da doc reescreve o arquivo, o artigo evapora, e nenhuma suíte fica
vermelha. Este script é o cobrador: acha o texto canônico, acha o artigo, e confere que
ele ainda diz o que foi decidido.

Uso:
    python3 scripts/cobertura_visual_check.py            # exit 1 se a regra sumiu
    python3 scripts/cobertura_visual_check.py --raiz DIR
    python3 scripts/cobertura_visual_check.py --json

O caminho do texto canônico NÃO é cravado: sai do resolvedor abaixo, que tenta `docs/`
na raiz antes de `.claude/docs/`. Quando o resolvedor único do repositório (F15.1)
existir vendorado, este é o único ponto a trocar.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ponytail: resolvedor local de 4 linhas até o resolvedor único (F15.1) existir —
# a cascata é a mesma que ele vai encapsular, e a troca é neste ponto só.
CASAS = (("docs",), (".claude", "docs"))

# O que o artigo tem que continuar dizendo. Cada sinal é uma parte da decisão do dono:
# a cobertura vale para FLUXO nomeado e para MÓDULO, e a peça coberta é o DIAGRAMA.
SINAIS = (
    ("diagrama", r"diagramas?\b"),
    ("fluxo", r"fluxos?\b"),
    ("módulo", r"m[oó]dulos?\b"),
)
TITULO = re.compile(r"^##\s+Artigo\s+\d+\s*[·.\-]\s*Cobertura visual\s*$", re.M | re.I)


def caminho_constituicao(raiz=ROOT):
    """O texto canônico da lei, na primeira casa que responder. None se não há."""
    for casa in CASAS:
        caminho = os.path.join(raiz, *casa, "constituicao.md")
        if os.path.isfile(caminho):
            return caminho
    return None


def _corpo_do_artigo(texto, inicio):
    """Do fim do título até o próximo `## ` (ou o fim) — o artigo, e só ele."""
    prox = re.search(r"^## ", texto[inicio:], re.M)
    return texto[inicio:inicio + prox.start()] if prox else texto[inicio:]


def confere(raiz=ROOT):
    """Devolve (achados, caminho). Achado = a regra sumiu ou foi esvaziada."""
    caminho = caminho_constituicao(raiz)
    if caminho is None:
        return [{
            "id": "sem-lei",
            "msg": "não há texto canônico da constituição (procurei %s)"
                   % " e ".join(os.path.join(*c, "constituicao.md") for c in CASAS),
            "conserto": "escreva a lei do projeto, ou aponte a casa dela no resolvedor.",
        }], None

    with open(caminho, encoding="utf-8") as f:
        texto = f.read()

    m = TITULO.search(texto)
    if not m:
        return [{
            "id": "artigo-sumiu",
            "msg": "o artigo da Cobertura visual sumiu do texto canônico",
            "conserto": "devolva o artigo `## Artigo N · Cobertura visual` à lei — a "
                        "regra é decisão do dono, não rascunho de plano.",
        }], caminho

    corpo = _corpo_do_artigo(texto, m.end())
    faltam = [nome for nome, padrao in SINAIS
              if not re.search(padrao, corpo, re.I)]
    if faltam:
        return [{
            "id": "artigo-esvaziado",
            "msg": "o artigo existe mas não diz mais o que foi decidido — falta falar "
                   "de: %s" % ", ".join(faltam),
            "conserto": "a regra é: todo fluxo nomeado na documentação tem diagrama e "
                        "todo módulo tem o seu.",
        }], caminho

    return [], caminho


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raiz", default=ROOT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    achados, caminho = confere(args.raiz)

    if args.json:
        print(json.dumps({"achados": achados, "arquivo": caminho},
                         ensure_ascii=False, indent=2))
        return 1 if achados else 0

    if not achados:
        print("cobertura visual — a regra está na lei (%s)"
              % os.path.relpath(caminho, args.raiz))
        return 0

    print("COBERTURA VISUAL SEM LEI — a regra não está mais no texto canônico:")
    for a in achados:
        print("\n  %s\n    %s\n    → %s"
              % (os.path.relpath(caminho, args.raiz) if caminho else "(nenhum arquivo)",
                 a["msg"], a["conserto"]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
