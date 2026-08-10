#!/usr/bin/env python3
"""Suíte da skill spec-to-plan — o aviso vem antes da criação, e o id é próprio.

Duas coisas se provam aqui: que o TEXTO da skill manda imprimir os planos abertos
antes de gravar o plano novo (ordem no arquivo, não só presença das duas frases), e
que o programa que ela chama REALMENTE recusa reaproveitar id existente — a segunda é
comportamento rodado, não citação.
"""

import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, os.pardir, os.pardir, os.pardir))
SKILL = os.path.join(AQUI, os.pardir, "skills", "plan", "SKILL.md")
PLAN_STATE = os.path.join(RAIZ, "plugins", "project-skills", "lib", "plan_state.py")

FALHAS = []


def check(rotulo, cond):
    print(("  ok   " if cond else "  FAIL ") + rotulo)
    if not cond:
        FALHAS.append(rotulo)


print("a skill spec-to-plan")
existe = os.path.isfile(SKILL)
check("existe o arquivo da skill", existe)
texto = open(SKILL, encoding="utf-8").read() if existe else ""

pos_open = texto.find("plan_state.py open")
pos_init = texto.find("plan_state.py init")
check("manda imprimir os planos abertos", pos_open != -1)
check("manda gravar o plano", pos_init != -1)
check("o aviso vem ANTES da gravacao", -1 < pos_open < pos_init)
check("diz que o id e proprio do plano", "id proprio" in texto or "id próprio" in texto)
check("diz que o init recusa renomear id existente",
      "recusa" in texto and "renomear id existente" in texto)


print("o programa que a skill chama")
PLANO = {
    "id": "2026-01-01-teste",
    "title": "Plano de teste da suite",
    "requisitos": [{"id": "S-1", "titulo": "Um requisito", "ca": "um criterio de aceite"}],
    "phases": [{"id": "F1", "title": "Uma fase", "items": [{
        "id": "F1.1", "title": "Uma tarefa que faz uma coisa",
        "desc": "A tarefa existe para a suite ter o que gravar.",
        "requisito": "S-1", "pronto": "o comando roda e devolve zero", "status": "todo"}]}],
}

with tempfile.TemporaryDirectory() as d:
    def roda(plano):
        f = os.path.join(d, "in.json")
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(plano, fh, ensure_ascii=False)
        return subprocess.run([sys.executable, PLAN_STATE, "--dir", d, "init", "--file", f],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              start_new_session=True)

    primeiro = roda(PLANO)
    check("grava o plano novo", primeiro.returncode == 0)

    outro = json.loads(json.dumps(PLANO))
    outro["phases"][0]["items"][0]["title"] = "Outra tarefa com outro nome"
    segundo = roda(outro)
    check("recusa reaproveitar o id com outro conteudo", segundo.returncode != 0)
    check("a recusa diz por que", "recusado" in (segundo.stdout + segundo.stderr))

print("FALHAS: %d" % len(FALHAS))
sys.exit(1 if FALHAS else 0)
