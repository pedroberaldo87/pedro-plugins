#!/usr/bin/env python3
"""A VITRINE pública também obedece ao Artigo 14 — e o cobrador tem que alcançá-la.

POR QUE EXISTE (2026-08-23). O cobrador do Artigo 14 devolvia "sem achados" enquanto o
README.md do marketplace PÚBLICO — a primeira coisa que qualquer pessoa lê — anunciava que
a /qa-loop "para por retornos decrescentes, não por zero erros". Ele era cego porque ALVOS
só enumerava skill e motor: texto de vitrine não estava na lista, e o que não está na
lista não é medido.

A extensão é por ENUMERAÇÃO, nunca por varredura genérica de *.md: varredura reprovaria a
própria docs/constituicao.md, que as cita no ato de revogá-las (casa-ok: prosa que cita o caso medido, nao um caminho usado).

O que este arquivo trava:
  1. os três textos de vitrine estão dentro de ALVOS (o cobrador enxerga a vitrine);
  2. rodar o cobrador inteiro nos alvos vivos continua limpo;
  3. a seção "O QUE ELE NÃO CONSEGUE MEDIR" declara a lacuna que sobra (docs assinados).

    python3 scripts/test_vitrine_nao_promete_fecho_por_taxa.py

stdlib only (requisito do repo).
"""
import importlib.util
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "cobrador_artigo14", os.path.join(AQUI, "test_revisao_fecha_por_problema.py"))
cobrador = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cobrador)

VITRINE = [
    "README.md",
    "README.pt-BR.md",
    "plugins/project-skills/skills/qa-loop/EXAMPLE-REPORT.md",
    "plugins/visual/lib/visual_page.py",
]


def caso_vitrine_esta_nos_alvos():
    faltam = [f for f in VITRINE if f not in cobrador.ALVOS]
    assert not faltam, "o cobrador do Artigo 14 é cego a texto de vitrine: %s" % faltam


def caso_alvos_vivos_limpos():
    del cobrador.achados[:]
    assert cobrador.main() == 0, \
        "os alvos vivos do Artigo 14 estão sujos:\n%s" % cobrador.achados


def caso_lacuna_dos_docs_assinados_declarada():
    doc = cobrador.__doc__ or ""
    assert "approved-sig" in doc, \
        "Artigo 4: gate que não mede tem que dizer que não mediu — falta declarar os " \
        "docs com approved-sig, fora do alcance do cobrador"


def main():
    for caso in (caso_vitrine_esta_nos_alvos,
                 caso_alvos_vivos_limpos,
                 caso_lacuna_dos_docs_assinados_declarada):
        caso()
        print("  ok · %s" % caso.__name__)
    print("a vitrine pública não promete fecho por taxa — 3 caso(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
