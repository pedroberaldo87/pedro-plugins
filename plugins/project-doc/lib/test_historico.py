#!/usr/bin/env python3
"""Regression test do historico.py — o arquivo histórico ao lado do documento autoral.

Roda com: python3 lib/test_historico.py  (ou python3 -m pytest lib/test_historico.py)
Sem framework obrigatório: um __main__ que roda asserts e sai !=0 se falhar.
"""
import json
import os
import subprocess
import sys
import tempfile

import historico

DOC = """---
generated: 2026-08-01
authored-by: human
status: approved
---

# Metas de qualidade

## A ordem

1. **velocidade** — entregar rápido é o que manda aqui
2. **custo** — a conta de infra tem teto
"""

ITEM = "1. **velocidade** — entregar rápido é o que manda aqui"
NOVO = "1. **integridade do dado** — nada pode ser perdido em silêncio"


def _projeto():
    d = tempfile.mkdtemp(prefix="pdtest_historico_")
    doc = os.path.join(d, "quality-goals.md")
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write(DOC)
    return doc


def test_reescrever_move_com_os_tres_dados():
    doc = _projeto()
    r = historico.reescrever(
        doc, ITEM, NOVO,
        contexto="a entrevista de metas foi refeita depois do primeiro incidente",
        decisao="perder dado passou a doer mais que atrasar entrega",
        data="2026-08-06",
    )

    canonico = open(doc, encoding="utf-8").read()
    assert NOVO in canonico, "o novo item tem que estar no canônico:\n%s" % canonico
    assert ITEM not in canonico, "o item antigo NÃO pode sobrar no canônico:\n%s" % canonico

    hist_path = historico.caminho_historico(doc)
    assert hist_path == r["historico"], "o retorno aponta o histórico: %s" % r
    assert os.path.exists(hist_path), "o histórico nasce ao lado do doc: %s" % hist_path
    assert os.path.dirname(hist_path) == os.path.dirname(doc), "ao lado, não em outra pasta"

    bruto = open(hist_path, encoding="utf-8").read()
    assert "authored-by: human" in bruto, "o histórico também é autoral:\n%s" % bruto

    entradas = historico.listar(doc)
    assert len(entradas) == 1, "uma reescrita, uma entrada: %s" % entradas
    e = entradas[0]
    assert e["data"] == "2026-08-06", "dado 1 — a data: %s" % e
    assert e["contexto"].startswith("a entrevista de metas"), "dado 2 — o contexto: %s" % e
    assert e["decisao"].startswith("perder dado passou"), "dado 3 — a decisão: %s" % e
    assert e["texto"] == ITEM, "o texto antigo vai literal: %r" % e["texto"]
    assert e["substituido_por"] == NOVO, "aponta o que entrou no lugar: %s" % e
    print("test_historico: reescrita move o antigo com data, contexto e decisão ✓")


def test_item_ausente_nao_escreve_nada():
    doc = _projeto()
    antes = open(doc, encoding="utf-8").read()
    try:
        historico.reescrever(doc, "item que nunca existiu", NOVO,
                             contexto="x", decisao="y", data="2026-08-06")
        raise AssertionError("item ausente tinha que levantar")
    except ValueError as e:
        assert "não encontrado" in str(e), "mensagem diz o que houve: %s" % e
    assert open(doc, encoding="utf-8").read() == antes, "canônico intacto"
    assert not os.path.exists(historico.caminho_historico(doc)), "histórico não nasce em erro"
    print("test_historico: item ausente recusa e não escreve ✓")


def test_item_ambiguo_recusa():
    doc = _projeto()
    with open(doc, "a", encoding="utf-8") as fh:
        fh.write("\n" + ITEM + "\n")
    try:
        historico.reescrever(doc, ITEM, NOVO, contexto="x", decisao="y", data="2026-08-06")
        raise AssertionError("item ambíguo tinha que levantar")
    except ValueError as e:
        assert "2 vezes" in str(e), "diz quantas vezes apareceu: %s" % e
    print("test_historico: item que aparece 2 vezes é ambíguo e recusa ✓")


def test_contexto_e_decisao_sao_obrigatorios():
    for kwargs in ({"contexto": "  ", "decisao": "y"}, {"contexto": "x", "decisao": ""}):
        doc = _projeto()
        try:
            historico.reescrever(doc, ITEM, NOVO, data="2026-08-06", **kwargs)
            raise AssertionError("faltando dado tinha que levantar: %s" % kwargs)
        except ValueError as e:
            assert "obrigat" in str(e), "mensagem nomeia o dado que falta: %s" % e
        assert ITEM in open(doc, encoding="utf-8").read(), "canônico intacto"
    print("test_historico: contexto e decisão em branco recusam ✓")


def test_duas_reescritas_acumulam():
    doc = _projeto()
    historico.reescrever(doc, ITEM, NOVO, contexto="c1", decisao="d1", data="2026-08-06")
    historico.reescrever(doc, "2. **custo** — a conta de infra tem teto",
                         "2. **custo** — sem teto declarado por enquanto",
                         contexto="c2", decisao="d2", data="2026-08-07")
    entradas = historico.listar(doc)
    assert len(entradas) == 2, "a segunda não sobrescreve a primeira: %s" % entradas
    assert [e["data"] for e in entradas] == ["2026-08-06", "2026-08-07"], entradas
    assert entradas[0]["contexto"] == "c1" and entradas[1]["decisao"] == "d2", entradas
    print("test_historico: entradas acumulam em ordem ✓")


def test_texto_com_bloco_de_codigo_volta_literal():
    d = tempfile.mkdtemp(prefix="pdtest_historico_fence_")
    doc = os.path.join(d, "solution-strategy.md")
    item = "### um repositório só\n\n```bash\nls plugins/\n```"
    with open(doc, "w", encoding="utf-8") as fh:
        fh.write("# Estratégia\n\n" + item + "\n")
    historico.reescrever(doc, item, "### serviços separados",
                         contexto="c", decisao="d", data="2026-08-06")
    e = historico.listar(doc)[0]
    assert e["texto"] == item, "round-trip literal, inclusive a cerca: %r" % e["texto"]
    print("test_historico: texto com cerca de código volta literal ✓")


def test_cli():
    doc = _projeto()
    lib = os.path.dirname(os.path.abspath(historico.__file__))
    p = subprocess.run(
        [sys.executable, os.path.join(lib, "historico.py"), "reescrever", doc,
         "--antigo", ITEM, "--novo", NOVO,
         "--contexto", "refeita a entrevista", "--decisao", "integridade subiu",
         "--data", "2026-08-06"],
        capture_output=True, text=True)
    assert p.returncode == 0, "CLI reescrever devia sair 0: %s %s" % (p.returncode, p.stderr)
    out = json.loads(p.stdout)
    assert out["entrada"]["data"] == "2026-08-06", out

    p = subprocess.run(
        [sys.executable, os.path.join(lib, "historico.py"), "listar", doc],
        capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    entradas = json.loads(p.stdout)["entradas"]
    assert len(entradas) == 1 and entradas[0]["decisao"] == "integridade subiu", entradas

    # item ausente: sai !=0 e diz o motivo em JSON (nunca stacktrace crua)
    p = subprocess.run(
        [sys.executable, os.path.join(lib, "historico.py"), "reescrever", doc,
         "--antigo", "nada disso", "--novo", "x", "--contexto", "c", "--decisao", "d"],
        capture_output=True, text=True)
    assert p.returncode != 0, "erro tem que sair !=0"
    assert "error" in json.loads(p.stdout), p.stdout
    print("test_historico: CLI reescrever/listar ✓")


def test_contrato_no_authorial_kit():
    """O contrato do arquivo histórico é escrito onde os dois consumidores leem."""
    kit = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(historico.__file__))),
                       "skills", "start-doc", "references", "authorial-kit.md")
    texto = open(kit, encoding="utf-8").read()
    secao = texto.split("## Contrato de saída (vale para todos)")[1].split("\n## ")[0]
    for termo in ("historico.md", "contexto", "decisão", "historico.py"):
        assert termo in secao, "o contrato tem que citar %r na seção de contrato de saída" % termo
    print("test_historico: contrato do histórico está no authorial-kit ✓")


def run():
    test_reescrever_move_com_os_tres_dados()
    test_item_ausente_nao_escreve_nada()
    test_item_ambiguo_recusa()
    test_contexto_e_decisao_sao_obrigatorios()
    test_duas_reescritas_acumulam()
    test_texto_com_bloco_de_codigo_volta_literal()
    test_cli()
    test_contrato_no_authorial_kit()


def test_historico_engine():  # entrada pytest
    run()


if __name__ == "__main__":
    run()
