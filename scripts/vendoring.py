#!/usr/bin/env python3
"""Onde cada arquivo de `_shared/` foi vendorado — lido do próprio vendoring.

Existe porque a lista de destinos era escrita à mão dentro de cada suíte, e o
rename de 2026-08 a venceu: três skills mudaram de plugin, os caminhos velhos
deixaram de existir, e as suítes ficaram vermelhas por ENDEREÇO em vez de por
defeito. Quem sabe onde cada cópia mora é `scripts/sync-shared.sh` — derivar
dele faz o próximo rename chegar às suítes sozinho.

Módulo, não suíte: importar um arquivo de teste executaria os asserts dele.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYNC = os.path.join(ROOT, "scripts", "sync-shared.sh")


def destinos(nome):
    """As pastas que recebem cópia de `<nome>`, na ordem em que o mapa as declara.

    Sem o vendoring não há destino a conferir, e a suíte que chamar isto tem que
    DIZER isso em vez de morrer em traceback: falha por infra ausente e falha por
    defeito não podem ter a mesma cara.
    """
    if not os.path.exists(SYNC):
        raise SystemExit("scripts/sync-shared.sh nao existe — sem ele nao ha "
                         "destino declarado para conferir")
    with open(SYNC, encoding="utf-8") as fh:
        bloco = re.search(r"^SPECS=\((.*?)^\)", fh.read(), re.S | re.M)
    saida = []
    for linha in (bloco.group(1) if bloco else "").splitlines():
        achou = re.search(r'"([^"]+)::([^"]+)"', linha)
        if achou and achou.group(2) == nome:
            saida.append(achou.group(1))
    return saida
