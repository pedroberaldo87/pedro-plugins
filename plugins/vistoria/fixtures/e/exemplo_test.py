#!/usr/bin/env python3
# ARQUIVO DE MENTIRA CONGELADO — fixture da letra (e): assert órfão. NÃO CONSERTAR.
# O nome termina em `_test.py`, e não começa com `test_`, para não entrar na esteira
# de verdade: esta suíte existe para ser ACHADA, nunca para rodar.
from exemplo import recusa


def test_recusa():
    # A frase abaixo era a mensagem antiga. O programa ao lado escreve outra.
    assert recusa() == "bloqueado: o arquivo violou a norma interna"


def test_prefixo():
    assert "recusado:" in recusa()
