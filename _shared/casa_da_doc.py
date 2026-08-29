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


def _tem_doc_da_familia(pasta):
    """A pasta tem documento DESTA família — o que abre com frontmatter e traz `project:`.

    É a marca mecânica que separa o documento das skills (gerado pelo /doc ou escrito
    pelo /start) do que o dono escreveu à mão: prosa em markdown não tem frontmatter, e
    frontmatter de outra ferramenta não tem `project:`. Não se adivinha nada — lê-se o
    cabeçalho.
    """
    try:
        nomes = [n for n in os.listdir(pasta) if n.endswith(".md")]
    except OSError:
        return False
    for nome in nomes:
        try:
            with open(os.path.join(pasta, nome), encoding="utf-8", errors="replace") as fh:
                if fh.readline().strip() != "---":
                    continue
                for _ in range(40):                     # o cabeçalho, nunca o corpo
                    linha = fh.readline()
                    if not linha or linha.strip() == "---":
                        break
                    if linha.startswith("project:"):
                        return True
        except OSError:
            continue
    return False


def casa(raiz, *partes):
    """O caminho da casa da doc de `raiz`, com `partes` juntadas dentro dela.

    Cascata: a casa NOVA se ela existir; senão a VELHA, se existir; senão a
    NOVA — porque doc que ainda não nasceu nasce na casa canônica.

    DUAS exceções medidas, e as duas são sobre a casa VELHA estar habitada:

    1. A NOVA existe sem nenhum .md e a VELHA tem a doc (medido em 2026-08-26):
       uma `docs/` de outro uso na raiz fazia o resolvedor ignorar a casa habitada. (casa-ok: prosa que cita o caso medido, nao um caminho usado)
    2. As DUAS têm .md, cada uma com um tipo de documento (medido em 2026-08-28):
       a NOVA com a prosa que o dono escreveu à mão, a VELHA com os documentos das
       skills. A cascata dava a NOVA, e como a marca que as ferramentas procuram só
       existe na VELHA, elas concluíam que o projeto não tinha documentação nenhuma —
       em silêncio, com cara de sucesso: o `/doc-touch` dizia "nada a tocar" com 277
       arquivos mudados, e o `/doc-load` declarava a lei do projeto AUSENTE com os 16
       documentos no disco. Toda skill que julga obra contra o acordado julgava sem
       régua, achando que régua não havia. O desempate é MECÂNICO, não adivinhado:
       responde a casa que tem documento DESTA família (frontmatter com `project:`).
    """
    raiz = str(raiz)
    nova = os.path.join(raiz, *NOVA)
    velha = os.path.join(raiz, *VELHA)
    if not os.path.isdir(nova):
        escolhida = velha if os.path.isdir(velha) else nova
    elif not os.path.isdir(velha):
        escolhida = nova
    elif not _tem_md(nova):
        escolhida = velha if _tem_md(velha) else nova
    elif _tem_md(velha) and not _tem_doc_da_familia(nova) and _tem_doc_da_familia(velha):
        escolhida = velha
    else:
        escolhida = nova
    return os.path.join(escolhida, *[str(p) for p in partes]) if partes else escolhida
