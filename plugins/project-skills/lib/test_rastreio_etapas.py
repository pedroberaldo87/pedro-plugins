#!/usr/bin/env python3
"""Regression test do rastreio_etapas.py — a terceira ponta solta.

O que ele prova: passo do ciclo de `blueprint.md` que nenhum item de `features.md`
atende sai NOMEADO na lista, e passo que uma funcionalidade cita verbatim não sai.

Roda com: python3 lib/test_rastreio_etapas.py
Sem framework obrigatório: um __main__ que roda asserts e sai !=0 se falhar.
"""
import os
import tempfile

import rastreio_etapas

JOURNEYS = """---
status: approved
---

## O cliente acompanha o pedido
Ele quer saber onde está a encomenda.
"""

FEATURES = """---
status: approved
---

### F-1 · Tela de acompanhamento
- **Origem:** jornada "O cliente acompanha o pedido"
- Atende o passo: o sistema mostra o estado atual do pedido.
"""

BLUEPRINT = """---
status: approved
---

## O ciclo, do começo ao fim
1. o sistema mostra o estado atual do pedido  ← journeys.md:4
2. o sistema avisa o cliente por mensagem quando o estado muda  ← journeys.md:5
"""


def _projeto(tmp):
    docs = os.path.join(tmp, ".claude", "docs")
    os.makedirs(docs)
    for nome, corpo in (("journeys.md", JOURNEYS),
                        ("features.md", FEATURES),
                        ("blueprint.md", BLUEPRINT)):
        with open(os.path.join(docs, nome), "w", encoding="utf-8") as fh:
            fh.write(corpo)
    return docs


def test_passo_orfao_sai_nomeado():
    with tempfile.TemporaryDirectory() as tmp:
        out = rastreio_etapas.conferir(_projeto(tmp))

    assert out["blueprint_lidas"] is True, "o blueprint tem que ser lido"
    orfaos = out["passos_sem_funcionalidade"]
    assert orfaos == [
        "o sistema avisa o cliente por mensagem quando o estado muda"
    ], orfaos
    assert out["contagem"]["passos"] == 2, out["contagem"]
    assert out["contagem"]["passos_sem_funcionalidade"] == 1, out["contagem"]
    assert out["sem_dono"] == 1, out


def test_sem_blueprint_nao_inventa_ponta():
    with tempfile.TemporaryDirectory() as tmp:
        docs = _projeto(tmp)
        os.remove(os.path.join(docs, "blueprint.md"))
        out = rastreio_etapas.conferir(docs)

    assert out["blueprint_lidas"] is False, out
    assert out["passos_sem_funcionalidade"] == [], out
    assert out["sem_dono"] == 0, out


if __name__ == "__main__":
    test_passo_orfao_sai_nomeado()
    test_sem_blueprint_nao_inventa_ponta()
    print("OK — a terceira lista acusa o passo órfão pelo nome")
