#!/usr/bin/env python3
"""test_readme_counts_check.py — o cobrador tem que pegar NOME errado, não só número.

O README já dizia "3 desligados" (número certo) listando dois nomes errados: quem
instala liga o plugin errado e o gate passava, porque só conferia contagem.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import readme_counts_check as rcc  # noqa: E402

REAIS = rcc._manifest_desligados_nomes()
NOMES = ", ".join("`%s`" % n for n in REAIS)

MOLDE = """Resultado esperado numa máquina zerada: **9 plugins ligados + 9 desligados de fábrica**
(%s), mais os marketplaces de terceiros do manifest.

Nove vêm **desligados de fábrica** na receita do `bootstrap` e você liga se quiser:
%s.
Ligar: `claude plugin enable <nome>@pedro-plugins`.
"""


def _achados_de(texto):
    achados, nao_medidas = [], []
    rcc._confere_nomes(texto, achados, nao_medidas)
    assert not nao_medidas, nao_medidas
    return achados


def test_nome_desligado_errado_reprova():
    errado = MOLDE % ("`intent-guard`", "`intent-guard`")
    ids = {a["id"] for a in _achados_de(errado)}
    assert ids == {"desligados-nomes-setup", "desligados-nomes-plugins"}, ids


def test_nome_desligado_certo_passa():
    assert _achados_de(MOLDE % (NOMES, NOMES)) == []


def test_passagem_sumida_reprova():
    assert len(_achados_de("README sem a passagem nenhuma.")) == 2


def test_readme_do_repo_esta_em_dia():
    with open(rcc.README, encoding="utf-8") as f:
        assert _achados_de(f.read()) == []


# ── a frase das skills: quantas skills, e quantos plugins trazem uma só ───────
#
# Entrou porque o README passou verde afirmando "20 trazem uma só" com 18 plugins
# de uma skill — a frase se contradizia sozinha (20+2+3+11 dá 36, não as 34 que
# ela mesma afirma) e nenhuma afirmação do gate media skill.

def _numeros_de(texto):
    achados, nao_medidas = [], []
    rcc._confere_numeros(texto, achados, nao_medidas)
    assert not nao_medidas, nao_medidas
    return achados


def _readme():
    with open(rcc.README, encoding="utf-8") as f:
        return f.read()


def test_quantidade_de_skills_errada_reprova():
    reais = rcc._skills()
    certo = "Os %d plugins somam **%d skills** — %d trazem uma só" % reais
    errado = certo.replace("— %d " % reais[2], "— %d " % (reais[2] + 2))
    ids = {a["id"] for a in _numeros_de(_readme().replace(certo, errado))}
    assert "skills" in ids, ids


def test_frase_das_skills_sumida_reprova():
    ids = {a["id"] for a in _numeros_de("README sem a frase nenhuma.")}
    assert "skills" in ids, ids


def test_numeros_do_readme_do_repo_batem():
    assert _numeros_de(_readme()) == []


if __name__ == "__main__":
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            fn()
            print("ok %s" % nome)
    print("todos verdes")
