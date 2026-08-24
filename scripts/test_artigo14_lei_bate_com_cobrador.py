#!/usr/bin/env python3
"""A lei do Artigo 14 só promete o que o cobrador dele mede — e diz o que não mede.

POR QUE EXISTE (2026-08-24). O "Como se cobra" do Artigo 14 anunciava que o cobrador
reprova teto de rodadas "declarado em config de projeto". Ele não reprova: os alvos dele
são cinco arquivos deste repositório, nenhum é config, e os `qa-loop.config.md` que
motivaram a emenda viviam no `.claude/` de OUTROS projetos, fora de qualquer varredura
daqui. Gate que se anuncia capaz do que não é são as duas faltas do Artigo 4 de uma vez:
promessa sem medida, e lacuna não declarada.

O que este arquivo trava:
  1. a lei não promete cobrança de config de projeto enquanto nenhum alvo do cobrador for
     um arquivo de config;
  2. o cobrador declara essa lacuna na seção "O QUE ELE NÃO CONSEGUE MEDIR" do docstring.

    python3 scripts/test_artigo14_lei_bate_com_cobrador.py

stdlib only (requisito do repo).
"""
import importlib.util
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

_spec = importlib.util.spec_from_file_location(
    "cobrador_artigo14", os.path.join(AQUI, "test_revisao_fecha_por_problema.py"))
cobrador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cobrador)

PROMESSA = re.compile(r"config d[eo] projeto", re.IGNORECASE)


def _como_se_cobra():
    with open(os.path.join(RAIZ, "docs", "constituicao.md"), encoding="utf-8") as fh:
        texto = fh.read()
    i = texto.index("**Como se cobra** — `scripts/test_revisao_fecha_por_problema.py`")
    return re.sub(r"\s+", " ", texto[i:texto.index("\n\n", i)])


def caso_lei_nao_promete_o_que_nenhum_alvo_alcanca():
    if any("config" in os.path.basename(a) for a in cobrador.ALVOS):
        return  # passou a medir de verdade: a promessa é legítima
    trecho = _como_se_cobra()
    assert not PROMESSA.search(trecho), \
        "o Artigo 14 promete cobrar teto em config de projeto, mas nenhum ALVO do " \
        "cobrador é config:\n  %s" % trecho


def caso_docstring_declara_a_lacuna():
    doc = re.sub(r"\s+", " ", cobrador.__doc__)
    i = doc.index("O QUE ELE NÃO CONSEGUE MEDIR")
    assert "qa-loop.config.md" in doc[i:], \
        "a seção de não-medição não declara que teto em `qa-loop.config.md` de projeto " \
        "consumidor fica fora da varredura"


def main():
    for caso in (caso_lei_nao_promete_o_que_nenhum_alvo_alcanca,
                 caso_docstring_declara_a_lacuna):
        caso()
        print("  ok · %s" % caso.__name__)
    print("a lei do Artigo 14 bate com o que o cobrador mede — 2 caso(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
