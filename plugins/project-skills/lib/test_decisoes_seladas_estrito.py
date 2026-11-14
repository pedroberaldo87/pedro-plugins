#!/usr/bin/env python3
"""A consulta ao registro de decisões seladas não casa frouxo (7fab4b4e · hsf_a03bf1f4).

O registro é um arquivo do repositório; num clone ele chega de fora. A consulta casava por
substring crua (uma fala de uma palavra, ou um pedaço de palavra, "respondia" qualquer pergunta)
e por sobreposição que só media a PERGUNTA (uma fala inchada de palavras cobria qualquer coisa).
Aqui cada porta frouxa é fechada, e os casos legítimos — a frase exata responde, a pergunta reescrita
vira sugestão.

Roda com:  python3 plugins/project-skills/lib/test_decisoes_seladas_estrito.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decisoes_seladas import consultar, selar, sugerir  # noqa: E402

ok = falhas = 0


def checa(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


def com_fala(fala):
    raiz = tempfile.mkdtemp(prefix="seladas-estrito-")
    selar(raiz, fala=fala, fonte="teste", data="2026-01-01")
    return raiz


print("== portas frouxas fechadas")
r = com_fala("final")
checa("fala de UMA palavra não responde pergunta nenhuma",
      consultar(r, "o deploy final pode apagar o banco de produção?") == [])

r = com_fala("log de erro")
checa("a frase só casa em fronteira de palavra (catalog ≠ log)",
      consultar(r, "posso apagar o catalog de erro do cliente?") == [])

r = com_fala(" ".join(chr(97 + i) + "orvo" for i in range(26)) +
             " apagar banco produção migração")
checa("fala inchada de palavras não cobre pergunta que cita 3 delas",
      consultar(r, "posso apagar o banco de produção?") == [])

r = com_fala("sempre que for apagar o banco de produção avisar antes de qualquer migração ou "
             "limpeza geral dos servidores")
checa("pergunta curta dentro de uma fala longa não casa por substring",
      consultar(r, "apagar o banco") == [])

print("== o uso legítimo segue funcionando")
FALA = "tudo que puder decidir no final, decido no final"
r = com_fala(FALA)
checa("a frase exata responde", len(consultar(r, FALA)) == 1)
checa("a frase exata, em maiúsculas e sem acento, responde",
      len(consultar(r, "TUDO QUE PUDER DECIDIR NO FINAL, DECIDO NO FINAL")) == 1)
# 7fab4b4e: só a chave exata RESPONDE; a reescrita e a frase dentro de pergunta maior são
# SUGESTÃO (o dono vê e decide) — a prova está em test_decisoes_seladas_chave_exata.py.
checa("a pergunta reescrita com outras palavras é sugerida, não respondida",
      consultar(r, "essa decisão do destino de deploy pode ficar para o final?") == []
      and len(sugerir(r, "essa decisão do destino de deploy pode ficar para o final?")) == 1)
checa("a frase dentro de uma pergunta maior é sugerida, não respondida",
      consultar(r, "lembra que tudo que puder decidir no final, decido no final? posso adiar?") == []
      and len(sugerir(r, "lembra que tudo que puder decidir no final, decido no final? posso adiar?")) == 1)
checa("pergunta sem relação continua indo ao dono",
      consultar(r, "quantos servidores o cliente contratou?") == [])

print("\n%d ok, %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
