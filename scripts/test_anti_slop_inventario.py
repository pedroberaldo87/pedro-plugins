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
        # A classe A foi ZERADA (F15.2: todo ponto adotou o resolvedor); zero ali é o
        # estado certo, e o padrão dela segue guardado pelo teste de fixture abaixo
        # (test_classe_a_conta_so_codigo_executavel). Nas demais, zero = regex quebrada.
        if c["id"] != "A":
            assert c["ocorrencias"] > 0, f"classe {c['id']} sem achado: padrão quebrado?"


def test_versao_do_catalogo_bate_com_a_do_plugin():
    """Classe D é a única com cobrador — se divergir, o release-gate já reprovaria."""
    d = [c for c in inv.inventario()["classes"] if c["id"] == "D"][0]
    divergem = [p for p in d["pontos"] if "DIVERGE" in p[2]]
    assert not divergem, divergem


def test_classe_a_conta_so_codigo_executavel():
    """F30.6 — prosa e retrato citam o caminho de propósito; só código executável conta.

    Medido em 2026-08-20: com prosa dentro, a classe A dava 718 pontos e o zero que o
    F15.2 exige era inalcançável por construção — a doc que ENSINA onde a documentação
    mora precisa escrever o lugar. O recorte é do escopo, não da régua.
    """
    import anti_slop_inventario as m
    alvos = [
        ("plugins/x/lib/motor.py", "abre('.claude/docs/architecture.md')"),  # casa-ok: fixture de teste, o literal e o dado do caso
        ("plugins/x/hooks/guarda.sh", "ler docs/patterns.md"),  # casa-ok: fixture de teste, o literal e o dado do caso
        (".claude/CLAUDE.md", "a doc canônica mora em .claude/docs/ e responde ali"),  # casa-ok: fixture de teste, o literal e o dado do caso
        (".claude/desacoplamento.baseline.json", '{"trecho": "docs/runtime.md"}'),  # casa-ok: fixture de teste, o literal e o dado do caso
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


def test_toda_classe_tem_situacao_com_dono_e_teto():
    """F15.7 — ou a fonte única existe em código, ou a dívida está declarada com dono.

    Classe sem uma das duas é a própria doença dentro do medidor: inventário de gaveta.
    """
    for c in inv.inventario()["classes"]:
        sit = c["situacao"]
        assert "IMPLEMENTADA" in sit or "DECLARADA" in sit, (c["id"], sit)
        assert isinstance(c["teto"], int), c["id"]
        # dono nomeado = um arquivo que existe de verdade no repositório
        alvos = [t.strip("`,;.") for t in sit.split() if "/" in t or t.endswith(".json")]
        existe = [a for a in alvos if os.path.exists(os.path.join(inv.RAIZ, a))]
        assert existe, (c["id"], alvos)


def test_check_acusa_reincidencia_da_classe():
    """O teto é o que morde: uma ocorrência a mais na classe reprova, com o nome dela."""
    import subprocess
    dado = inv.inventario()
    assert inv.checa(dado) == 0, "a codebase de hoje já está acima do teto"
    dado["classes"][2]["ocorrencias"] = dado["classes"][2]["teto"] + 1
    dado["classes"][2]["reincidiu"] = True
    assert inv.checa(dado) == 1
    r = subprocess.run([sys.executable, os.path.join(inv.RAIZ, "scripts",
                                                     "anti_slop_inventario.py"), "--check"],
                       cwd=inv.RAIZ, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_o_comando_de_cada_classe_roda_de_verdade():
    """"Conferível por comando" só vale se o comando escrito na ficha EXECUTA.

    B e D crashavam em `--classe X` (os pontos deles têm 3 campos, não 4) — a ficha
    prometia uma conferência que morria com ValueError.
    """
    import subprocess
    for c in inv.inventario()["classes"]:
        r = subprocess.run(c["comando"], shell=True, cwd=inv.RAIZ,
                           capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, start_new_session=True)
        assert not r.stderr.strip(), (c["id"], r.stderr[-400:])
        assert r.stdout.strip() == str(c["ocorrencias"]), \
            (c["id"], r.stdout.strip(), c["ocorrencias"])


if __name__ == "__main__":
    for _nome, _fn in sorted(globals().items()):
        if _nome.startswith("test_") and callable(_fn):
            _fn()
            print("  ok", _nome)
    print("ok")
