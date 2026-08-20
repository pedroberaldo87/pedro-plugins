#!/usr/bin/env python3
"""Quem SERVIU a segunda opinião — lido do transcrito, não da boca do modelo.

A skill `/2op` pede uma família de modelo; pedido não é garantia. A salvaguarda
antiga mandava o próprio revisor abrir a resposta dizendo qual modelo era — quem
mente sobre a identidade é exatamente quem não pode ser a testemunha disso.

O transcrito da sessão (`~/.claude/projects/<projeto>/<sessão>.jsonl`) grava o
campo `model` em cada turno de assistente. Este cobrador acha o último pedido
`/2op*`, compara o modelo do turno de ANTES (o titular) com o do turno de DEPOIS
(o revisor) e acusa quando são o mesmo: a segunda cabeça não veio.

    python3 plugins/2op/lib/quem_serviu.py [transcrito.jsonl]

Sem argumento, usa o `.jsonl` mais recente do projeto do diretório atual.
Sai 1 quando acusa, 0 quando a troca aconteceu (ou quando não há `/2op` no
transcrito — nada a cobrar).
"""

import glob
import json
import os
import re
import sys

CMD = re.compile(r"/2op(?:-opus|-sonnet)?\b")


def _texto(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(b.get("text", "") for b in c if isinstance(b, dict))
    return ""


def turnos(caminho):
    """(papel, modelo, texto) de cada turno do transcrito, fora de sidechain."""
    saida = []
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                d = json.loads(linha)
            except ValueError:
                continue
            if d.get("isSidechain"):
                continue
            msg = d.get("message") or {}
            papel = msg.get("role") or d.get("type")
            if papel not in ("user", "assistant"):
                continue
            saida.append((papel, msg.get("model"), _texto(msg)))
    return saida


def auditar(caminho):
    """Devolve (comando, titular, revisor, acusacao). acusacao=None ⇒ nada a cobrar."""
    ts = turnos(caminho)
    i = cmd = None
    for k, (papel, _, txt) in enumerate(ts):
        if papel == "user":
            m = CMD.search(txt)
            if m:
                i, cmd = k, m.group(0)
    if i is None:
        return (None, None, None, None)
    titular = next((m for p, m, _ in reversed(ts[:i]) if p == "assistant" and m), None)
    revisor = next((m for p, m, _ in ts[i + 1:] if p == "assistant" and m), None)
    acusacao = None
    if revisor and titular and revisor == titular:
        acusacao = ("%s pediu outra cabeça e quem serviu foi o titular: os dois turnos "
                    "rodaram em %s. Isto não é segunda opinião — é o mesmo modelo se "
                    "corroborando." % (cmd, revisor))
    return (cmd, titular, revisor, acusacao)


def _mais_recente():
    slug = os.getcwd().replace("/", "-")
    padrao = os.path.expanduser("~/.claude/projects/%s/*.jsonl" % slug)
    arquivos = sorted(glob.glob(padrao), key=os.path.getmtime)
    return arquivos[-1] if arquivos else None


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else _mais_recente()
    if not alvo or not os.path.exists(alvo):
        print("transcrito não encontrado: %s" % alvo)
        sys.exit(0)
    cmd, titular, revisor, acusacao = auditar(alvo)
    if cmd is None:
        print("nenhum /2op neste transcrito — nada a cobrar")
        sys.exit(0)
    print("comando: %s · titular: %s · revisor: %s" % (cmd, titular, revisor))
    if acusacao:
        print("ACUSA: %s" % acusacao)
        sys.exit(1)
    print("ok — a segunda cabeça veio")
