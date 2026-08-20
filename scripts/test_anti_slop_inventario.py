#!/usr/bin/env python3
"""O inventário anti-slop mede o que diz medir — as 4 classes, e a contagem = os pontos."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anti_slop_inventario as inv  # noqa: E402


def test_quatro_classes_com_dono_e_de_para():
    dado = inv.inventario()
    assert dado["arquivos_varridos"] > 100, dado["arquivos_varridos"]
    assert [c["id"] for c in dado["classes"]] == ["A", "B", "C", "D"]
    for c in dado["classes"]:
        assert c["dono"] and c["de"] and c["para"] and c["comando"], c["id"]
        assert c["ocorrencias"] == len(c["pontos"]), c["id"]
        assert c["ocorrencias"] > 0, f"classe {c['id']} sem achado: padrão quebrado?"


def test_versao_do_catalogo_bate_com_a_do_plugin():
    """Classe D é a única com cobrador — se divergir, o release-gate já reprovaria."""
    d = [c for c in inv.inventario()["classes"] if c["id"] == "D"][0]
    divergem = [p for p in d["pontos"] if "DIVERGE" in p[2]]
    assert not divergem, divergem


if __name__ == "__main__":
    test_quatro_classes_com_dono_e_de_para()
    test_versao_do_catalogo_bate_com_a_do_plugin()
    print("ok")
