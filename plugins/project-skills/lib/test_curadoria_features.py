#!/usr/bin/env python3
"""
test_curadoria_features.py — o portão da etapa 5 do /start.

Dois casos que decidem tudo:
  · POSITIVO — todos os itens voltaram com veredito ⇒ grava `features.md`, com o
    `change` entrando pelo texto que o dono escreveu e o `remove` na seção
    "Deixado de fora de propósito".
  · NEGATIVO — um rádio ficou em branco (chega no JSON como `val: "keep"` com
    `touched: false`) ⇒ recusa, nomeia o item, e NÃO cria o arquivo.

Roda com:  python3 plugins/project-skills/lib/test_curadoria_features.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import curadoria_features as cf  # noqa: E402

PASS = 0


def check(label, cond):
    global PASS
    assert cond, "FALHOU: " + label
    PASS += 1
    print("  ok ·", label)


def _retorno(itens):
    return {"state": {"feedback": itens}}


def _rodar(tmp, itens, proposta=None):
    ret = os.path.join(tmp, "latest.json")
    with open(ret, "w", encoding="utf-8") as fh:
        json.dump(_retorno(itens), fh)
    saida = os.path.join(tmp, "docs", "features.md")
    argv = [__file__, "--retorno", ret, "--saida", saida]
    if proposta is not None:
        pcam = os.path.join(tmp, "spec.json")
        with open(pcam, "w", encoding="utf-8") as fh:
            json.dump(proposta, fh)
        argv += ["--proposta", pcam]
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cf.main(argv)
    return code, saida, out.getvalue(), err.getvalue()


def test_positivo():
    print("\n== positivo — todos com veredito, grava ==")
    tmp = tempfile.mkdtemp(prefix="curadoria_ok_")
    try:
        itens = [
            {"num": "1", "title": "Importar extrato OFX", "val": "keep",
             "touched": True, "note": ""},
            {"num": "2", "title": "Categorizar por regra", "val": "change",
             "touched": True, "note": "Categorizar por regra E por aprendizado do histórico"},
            {"num": "3", "title": "Compartilhar carteira", "val": "remove",
             "touched": True, "note": "não é pra ser multiusuário na v1"},
        ]
        proposta = {"blocks": [
            {"title": "Importar extrato OFX",
             "detail": "\"eu jogo o extrato do banco e ele entende\" — journeys.md"},
            {"title": "Categorizar por regra", "detail": "goals.md · meta 2"},
        ]}
        code, saida, out, err = _rodar(tmp, itens, proposta)
        check("saiu 0", code == 0)
        check("gravou o arquivo", os.path.exists(saida))
        corpo = open(saida, encoding="utf-8").read()
        check("keep entrou", "### F-1 · Importar extrato OFX" in corpo)
        check("change entrou com o texto literal do dono",
              "### F-2 · Categorizar por regra E por aprendizado do histórico" in corpo)
        check("remove NÃO entrou como funcionalidade",
              "### F-3" not in corpo)
        check("remove foi pra seção de fora, com o motivo",
              "## Deixado de fora de propósito" in corpo
              and "não é pra ser multiusuário na v1" in corpo)
        check("origem veio do spec da página",
              "- **Origem:** \"eu jogo o extrato do banco e ele entende\" — journeys.md"
              in corpo)
        check("relatório conta os vereditos", "1 keep · 1 change · 1 remove" in out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_negativo_radio_em_branco():
    print("\n== negativo — rádio em branco recusa ==")
    tmp = tempfile.mkdtemp(prefix="curadoria_no_")
    try:
        itens = [
            {"num": "1", "title": "Importar extrato OFX", "val": "keep",
             "touched": True, "note": ""},
            # o que o template manda quando ninguém clicou: val "keep", touched falso
            {"num": "2", "title": "Categorizar por regra", "val": "keep",
             "touched": False, "note": ""},
        ]
        code, saida, out, err = _rodar(tmp, itens)
        check("saiu 2", code == 2)
        check("NÃO gravou nada", not os.path.exists(saida))
        check("nomeou o item sem veredito", "Categorizar por regra" in err)
        check("não acusou o item que tem veredito",
              "Importar extrato OFX" not in err)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_veredito_fora_do_spec():
    print("\n== negativo — valor fora dos três do spec ==")
    tmp = tempfile.mkdtemp(prefix="curadoria_val_")
    try:
        itens = [{"num": "1", "title": "Exportar CSV", "val": "talvez",
                  "touched": True, "note": ""}]
        code, saida, out, err = _rodar(tmp, itens)
        check("saiu 2", code == 2)
        check("NÃO gravou nada", not os.path.exists(saida))
        check("nomeou o item", "Exportar CSV" in err)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_frontmatter_existente_preservado():
    print("\n== o frontmatter de um features.md já gravado não é reescrito ==")
    tmp = tempfile.mkdtemp(prefix="curadoria_fm_")
    try:
        os.makedirs(os.path.join(tmp, "docs"))
        saida = os.path.join(tmp, "docs", "features.md")
        with open(saida, "w", encoding="utf-8") as fh:
            fh.write("---\nauthored-by: human\nstatus: approved\n"
                     "approved: 2026-08-01\n---\n\n# Funcionalidades\n")
        ret = os.path.join(tmp, "latest.json")
        with open(ret, "w", encoding="utf-8") as fh:
            json.dump(_retorno([{"num": "1", "title": "Exportar CSV",
                                 "val": "keep", "touched": True, "note": ""}]), fh)
        out = io.StringIO()
        with redirect_stdout(out):
            code = cf.main([__file__, "--retorno", ret, "--saida", saida])
        check("saiu 0", code == 0)
        corpo = open(saida, encoding="utf-8").read()
        check("aprovação anterior preservada", "approved: 2026-08-01" in corpo)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_positivo()
    test_negativo_radio_em_branco()
    test_veredito_fora_do_spec()
    test_frontmatter_existente_preservado()
    print("\n%d checagens OK" % PASS)
