#!/usr/bin/env python3
"""Onde mora a doc canônica de um projeto — a versão Python.

Por que existe: o caminho da doc estava cravado em mais de cem pontos, e a casa
mudou (`docs/` na raiz, visível ao humano; `.claude/docs/` só como
retrocompatibilidade). Caminho cravado é a doença que o dono nomeou AI SLOP:
duplicar até virar dívida. Aqui é o único lugar que decide.

O contrato em prosa (e o irmão em bash) estão em `_shared/casa-da-doc.md`.

    from casa_da_doc import casa
    casa(raiz)                      # <raiz>/docs  ou  <raiz>/.claude/docs
    casa(raiz, "architecture.md")   # o arquivo dentro da casa que vale
"""

import os

__all__ = ["casa", "NOVA", "VELHA"]

NOVA = ("docs",)              # a casa canônica: visível na raiz
VELHA = (".claude", "docs")   # a casa antiga: retrocompatibilidade


def casa(raiz, *partes):
    """O caminho da casa da doc de `raiz`, com `partes` juntadas dentro dela.

    Cascata: a casa NOVA se ela existir; senão a VELHA, se existir; senão a
    NOVA — porque doc que ainda não nasceu nasce na casa canônica.
    """
    raiz = str(raiz)
    nova = os.path.join(raiz, *NOVA)
    velha = os.path.join(raiz, *VELHA)
    escolhida = nova if os.path.isdir(nova) or not os.path.isdir(velha) else velha
    return os.path.join(escolhida, *[str(p) for p in partes]) if partes else escolhida
