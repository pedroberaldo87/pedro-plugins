#!/usr/bin/env python3
"""Os dois templates de diagrama trazem a seção de extensão declarada.

O que não cabe no vocabulário-base tem que entrar DECLARADO — tipo da base mais
uma `tag` que nomeia o papel extra —, nunca desenhado à parte. A seção é um card
dos templates; sem cobrador ela some na primeira edição e o desenho ad-hoc volta.
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATES = RAIZ / "plugins" / "archify" / "skills" / "archify" / "templates"
ESQUEMA_COMUM = TEMPLATES.parent / "schemas" / "common.schema.json"
NOMES = ["arquitetura.template", "fluxo.template"]
TITULO = "Extensão declarada"


def tipos_da_base():
    comum = json.loads(ESQUEMA_COMUM.read_text(encoding="utf-8"))
    return set(comum["$defs"]["componentType"]["enum"])


def card_de_extensao(nome):
    dados = json.loads((TEMPLATES / f"{nome}.json").read_text(encoding="utf-8"))
    achados = [c for c in dados.get("cards", []) if c["title"] == TITULO]
    assert len(achados) == 1, \
        f"{nome}.json: esperava um card '{TITULO}', achei {len(achados)}"
    return achados[0]


def test_os_dois_templates_tem_a_secao_de_extensao():
    for nome in NOMES:
        card = card_de_extensao(nome)
        assert len(card["items"]) >= 2, \
            f"{nome}.json: a seção de extensão precisa da regra e de um caso extra"


def test_o_caso_extra_declara_tipo_da_base_e_tag():
    base = tipos_da_base()
    for nome in NOMES:
        itens = card_de_extensao(nome)["items"]
        casos = [i for i in itens if '"type"' in i and '"tag"' in i]
        assert casos, \
            f"{nome}.json: nenhum caso extra exemplificado com \"type\" e \"tag\""
        for caso in casos:
            tipo = re.search(r'"type":\s*"([^"]+)"', caso).group(1)
            assert tipo in base, \
                f"{nome}.json: o caso extra usa tipo '{tipo}', fora do vocabulário-base"
            tag = re.search(r'"tag":\s*"([^"]+)"', caso).group(1)
            assert tag.strip(), f"{nome}.json: o caso extra tem tag vazia"


def test_a_prova_renderizada_mostra_a_secao():
    for nome in NOMES:
        html = (TEMPLATES / f"{nome}.html").read_text(encoding="utf-8")
        assert TITULO in html, \
            f"{nome}.html: renderizado antes da seção de extensão — re-renderize"


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            try:
                fn()
                print(f"ok   {nome}")
            except AssertionError as erro:
                falhas += 1
                print(f"FAIL {nome}: {erro}")
    sys.exit(1 if falhas else 0)
