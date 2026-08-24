#!/usr/bin/env python3
"""A frase proibida partida ao meio pelo markdown TEM que ser acusada.

POR QUE EXISTE (2026-08-23). O cobrador do Artigo 14 varria LINHA A LINHA. O markdown
quebra parágrafo onde quiser, e num bloco de citação a quebra ainda insere um `>` no
começo da linha seguinte — então "retornos decrescentes" escrito como

    > ... (seu evento interno — retornos
    > decrescentes) E a Fase Gate ...

não casava com nenhuma das duas linhas, e sobreviveu no bloco VIVO do SKILL.md por uma
revisão inteira. Colapsar espaço não resolve sozinho: entre "retornos" e "decrescentes"
existe o `>` do marcador. Ele sai ANTES do colapso.

O que este arquivo trava:
  1. a frase partida em duas linhas é achada, e o achado aponta a linha de ONDE ELA COMEÇA;
  2. a isenção `artigo14-ok` continua valendo na janela de 3 linhas, medida na linha REAL;
  3. os arquivos vivos do repositório continuam limpos.

    python3 scripts/test_artigo14_frase_partida.py

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


def varre(texto, frases):
    del cobrador.achados[:]
    cobrador.checa_frases("fake.md", texto, frases, "regra de teste")
    return list(cobrador.achados)


PARTIDA = (
    "linha um\n"
    "\n"
    "> fecha quando a rodada rende só o que já se sabia — retornos\n"
    "> decrescentes) e o gate fica verde.\n"
)

ISENTA = (
    "<!-- artigo14-ok: nomeia a leitura errada para poder proibi-la -->\n"
    "> a assíntota NÃO é taxa de descoberta: \"retornos\n"
    "> decrescentes\" nunca foi o critério.\n"
)


def caso_frase_partida_e_acusada():
    achados = varre(PARTIDA, cobrador.FRASES_DE_TAXA)
    assert len(achados) == 1, "a frase partida em duas linhas passou batido: %r" % achados
    assert achados[0]["linha"] == 3, \
        "o achado tem que apontar a linha onde a frase COMEÇA, veio %r" % achados[0]["linha"]


def caso_isencao_sobrevive_na_linha_real():
    assert varre(ISENTA, cobrador.FRASES_DE_TAXA) == [], \
        "a marca artigo14-ok na janela de 3 linhas tem que anistiar a frase partida"


def caso_frase_inteira_numa_linha_ainda_e_acusada():
    achados = varre("nada\nisso para quando não vale mais a pena, e pronto\n",
                    cobrador.FRASES_DE_GASTO)
    assert len(achados) == 1 and achados[0]["linha"] == 2, achados


def caso_arquivos_vivos_limpos():
    del cobrador.achados[:]
    assert cobrador.main() == 0, \
        "os alvos vivos do Artigo 14 estão sujos:\n%s" % cobrador.achados


def main():
    for caso in (caso_frase_partida_e_acusada,
                 caso_isencao_sobrevive_na_linha_real,
                 caso_frase_inteira_numa_linha_ainda_e_acusada,
                 caso_arquivos_vivos_limpos):
        caso()
        print("  ok · %s" % caso.__name__)
    print("frase partida ao meio pelo markdown é acusada — 4 caso(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
