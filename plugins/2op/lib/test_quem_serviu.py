#!/usr/bin/env python3
"""Suíte do 2op: ninguém se autodeclara, e o transcrito é quem acusa.

Dois lados. (1) As três SKILL.md não podem mais mandar o revisor abrir dizendo
qual modelo ele é — a testemunha não pode ser o réu; elas apontam para o
cobrador. (2) O cobrador, com transcrito de mentira reproduzindo o caso real:
sessão em Opus chamando /2op-opus, o mesmo modelo dos dois lados.

    python3 plugins/2op/lib/test_quem_serviu.py
"""

import json
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
sys.path.insert(0, AQUI)
import quem_serviu  # noqa: E402

SKILLS = ["2op", "2op-opus", "2op-sonnet"]
PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


def corpo(nome):
    p = os.path.join(ROOT, "plugins/2op/skills", nome, "SKILL.md")
    with open(p, encoding="utf-8") as fh:
        return "---\n".join(fh.read().split("---\n")[2:])


def transcrito(pares, destino):
    """pares = [(papel, modelo, texto)] → arquivo .jsonl como o Claude Code grava."""
    with open(destino, "w", encoding="utf-8") as fh:
        for papel, modelo, texto in pares:
            msg = {"role": papel, "content": [{"type": "text", "text": texto}]}
            if modelo:
                msg["model"] = modelo
            fh.write(json.dumps({"type": papel, "isSidechain": False, "message": msg}) + "\n")
    return destino


print("2op · a identidade sai do transcrito, não da boca do revisor")
for nome in SKILLS:
    c = corpo(nome)
    check("%s: o corpo não manda o revisor se autodeclarar" % nome,
          "Não se declare" in c and "qual modelo você é de fato" not in c)
    check("%s: o corpo aponta o cobrador que lê o transcrito" % nome,
          "quem_serviu.py" in c)
    check("%s: a primeira linha da resposta é só o veredito" % nome,
          "1. **Primeira linha**: o veredito — CONCORDO" in c)

tmp = tempfile.mkdtemp()
# Caso reproduzido: sessão em Opus 5 pedindo /2op-opus e sendo servida por Opus 5.
mesmo = transcrito([
    ("user", None, "revisa isso aí"),
    ("assistant", "claude-opus-5", "fiz o trabalho"),
    ("user", None, "/2op-opus"),
    ("assistant", "claude-opus-5", "CONCORDO"),
], os.path.join(tmp, "mesmo.jsonl"))
cmd, titular, revisor, acusacao = quem_serviu.auditar(mesmo)
check("acusa quem serviu a si mesmo", acusacao is not None, (cmd, titular, revisor))
check("a acusação nomeia o comando e o modelo",
      acusacao and "/2op-opus" in acusacao and "claude-opus-5" in acusacao, acusacao)

trocou = transcrito([
    ("user", None, "revisa isso aí"),
    ("assistant", "claude-opus-5", "fiz o trabalho"),
    ("user", None, "/2op-sonnet"),
    ("assistant", "claude-sonnet-5", "DISCORDO"),
], os.path.join(tmp, "trocou.jsonl"))
check("não acusa quando a segunda cabeça veio", quem_serviu.auditar(trocou)[3] is None)

vazio = transcrito([("user", None, "oi"), ("assistant", "claude-opus-5", "olá")],
                   os.path.join(tmp, "vazio.jsonl"))
check("transcrito sem /2op não tem o que cobrar", quem_serviu.auditar(vazio)[0] is None)

print("\n%d ok, %d FAIL" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
