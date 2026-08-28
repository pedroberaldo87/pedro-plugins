#!/usr/bin/env python3
"""Onde mora a doc canônica de um projeto — a versão Python.

Por que existe: o caminho da doc estava cravado em mais de cem pontos, e a casa
mudou (`docs/` na raiz, visível ao humano; `.claude/docs/` só como  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
retrocompatibilidade). Caminho cravado é a doença que o dono nomeou AI SLOP:
duplicar até virar dívida. Aqui é o único lugar que decide.

O contrato em prosa (e o irmão em bash) estão em `_shared/casa-da-doc.md`.

    from casa_da_doc import casa
    casa(raiz)                      # <raiz>/docs  ou  <raiz>/.claude/docs  # casa-ok: o resolvedor e a suite dele sao o unico lugar que pode escrever a casa
    casa(raiz, "architecture.md")   # o arquivo dentro da casa que vale
"""

import os

__all__ = ["casa", "NOVA", "VELHA"]

NOVA = ("docs",)              # a casa canônica: visível na raiz
VELHA = (".claude", "docs")   # a casa antiga: retrocompatibilidade


def _tem_md(pasta):
    """A pasta tem pelo menos um .md no primeiro nível — é casa habitada."""
    try:
        return any(n.endswith(".md") for n in os.listdir(pasta))
    except OSError:
        return False


def casa(raiz, *partes):
    """O caminho da casa da doc de `raiz`, com `partes` juntadas dentro dela.

    Cascata: a casa NOVA se ela existir; senão a VELHA, se existir; senão a
    NOVA — porque doc que ainda não nasceu nasce na casa canônica.
    Exceção medida (outro projeto, 2026-08-26): a NOVA existe sem nenhum .md
    e a VELHA tem a doc de verdade — uma `docs/` de outro uso na raiz fazia (casa-ok: prosa que cita o caso medido, nao um caminho usado)
    o resolvedor ignorar a casa habitada. Nesse caso a VELHA responde.
    """
    raiz = str(raiz)
    nova = os.path.join(raiz, *NOVA)
    velha = os.path.join(raiz, *VELHA)
    if not os.path.isdir(nova):
        escolhida = velha if os.path.isdir(velha) else nova
    elif os.path.isdir(velha) and not _tem_md(nova) and _tem_md(velha):
        escolhida = velha
    else:
        escolhida = nova
    return os.path.join(escolhida, *[str(p) for p in partes]) if partes else escolhida
