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


def test_classe_a_conta_so_codigo_executavel():
    """F30.6 — prosa e retrato citam o caminho de propósito; só código executável conta.

    Medido em 2026-08-20: com prosa dentro, a classe A dava 718 pontos e o zero que o
    F15.2 exige era inalcançável por construção — a doc que ENSINA onde a documentação
    mora precisa escrever o lugar. O recorte é do escopo, não da régua.
    """
    import anti_slop_inventario as m
    alvos = [
        ("plugins/x/lib/motor.py", "abre('.claude/docs/architecture.md')"),
        ("plugins/x/hooks/guarda.sh", "ler docs/patterns.md"),
        (".claude/CLAUDE.md", "a doc canônica mora em .claude/docs/ e responde ali"),
        (".claude/desacoplamento.baseline.json", '{"trecho": "docs/runtime.md"}'),
    ]
    pontos = m.classe_a(alvos)["pontos"]
    achados = sorted({p[0] for p in pontos})
    assert achados == ["plugins/x/hooks/guarda.sh", "plugins/x/lib/motor.py"], achados


def test_isencao_so_vale_com_motivo_escrito():
    """Marcador pelado é o mesmo defeito com um carimbo em cima — continua contando."""
    import anti_slop_inventario as m
    com_motivo = [("plugins/x/lib/a.py", "p = '.claude/docs/x.md'  # casa-ok: é o texto do erro")]
    pelado = [("plugins/x/lib/b.py", "p = '.claude/docs/x.md'  # casa-ok:")]
    assert m.classe_a(com_motivo)["pontos"] == []
    assert len(m.classe_a(pelado)["pontos"]) == 1
