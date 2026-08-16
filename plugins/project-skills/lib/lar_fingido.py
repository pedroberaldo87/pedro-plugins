#!/usr/bin/env python3
"""A receita de FINGIR O LAR para um processo filho — a versão Python.

Por que existe: teste que troca só `HOME` finge o lar no Unix e NÃO finge no
Windows. Lá o `expanduser` do Python lê `USERPROFILE` primeiro (e `HOMEDRIVE` +
`HOMEPATH` depois), e só cai no `HOME` se nenhum dos dois existir — então o
processo filho vai escrever no lar REAL de quem roda a suíte. As quatro variáveis
andam juntas ou não andam.

O contrato em prosa (e o irmão em bash) estão em `_shared/lar-fingido.md`.

    env = ambiente(lar, CLAUDE_CONFIG_DIR=os.path.join(lar, ".claude"))
    subprocess.run(cmd, env=env)
"""

import os

__all__ = ["ambiente"]


def ambiente(lar, base=None, **extra):
    """O ambiente do processo filho com o lar apontando para `lar`.

    `base` é o ambiente de partida (padrão: `os.environ`); `extra` são as demais
    variáveis do caso — `CLAUDE_CONFIG_DIR`, `PATH`, o que for.
    """
    lar = str(lar)
    env = dict(os.environ if base is None else base)
    env.update(HOME=lar, USERPROFILE=lar, HOMEDRIVE="", HOMEPATH=lar)
    env.update({k: str(v) for k, v in extra.items()})
    return env
