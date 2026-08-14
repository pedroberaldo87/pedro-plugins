#!/usr/bin/env python3
"""Suíte da SELEÇÃO do run_suites.py — medir nada nunca sai verde (F17.2).

Esta suíte nasceu de dano medido, não de zelo: em 2026-08-13 a casca do `/sprint`
passou `python3 scripts/run_suites.py` ao motor como comando da suíte do projeto,
sem `--py` nem `--sh`. O programa imprimiu `0 suíte(s) · 0 problema(s)` e saiu
ZERO — então a guarda de saúde e a suíte da largada do motor declararam a corrida
verde tendo medido NADA. A corrida gastou 87 minutos e não marcou um passo.

A régua contra glob-que-não-casa já existia dentro do `expande()`, mas um nível
fundo demais: sem NENHUM padrão o laço dele não itera. É esse vão que os casos
abaixo fecham.

    python3 scripts/test_run_suites_selecao.py
"""

import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RODADOR = os.path.join(RAIZ, "scripts", "run_suites.py")
ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ✓ %s" % nome)
    else:
        falhas += 1
        print("  ✗ %s%s" % (nome, ("\n      %s" % detalhe) if detalhe else ""))


def roda(*args):
    """Dispara o rodador e devolve (exit, stdout+stderr).

    `stdin` fechado e sessão própria pela mesma regra do repositório: disparo que
    pode deixar filho para trás é o que o `vazamento_check.py` cobra.
    """
    r = subprocess.run([sys.executable, RODADOR, *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, start_new_session=True, cwd=RAIZ)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


print("F17.2 — seleção vazia reprova, nunca sai verde")

# A) O caso que custou a corrida: nenhum padrão.
codigo, saida = roda()
check("sem --py e sem --sh o rodador REPROVA", codigo != 0,
      "exit=%d — se for 0, o comando volta a poder mentir verde ao motor" % codigo)
check("a recusa diz que faltou seleção", "nenhuma seleção" in saida, saida[:200])
check("a recusa aponta onde está a esteira canônica", "portability.yml" in saida,
      saida[:200])
# O texto explica POR QUE é erro — sem isso, quem lê acha que é frescura de
# argumento e contorna com um glob qualquer, que é como a doença volta.
check("a recusa explica que sair verde sem medir é o defeito",
      "sem medir" in saida, saida[:200])

# B) O contrário — a seleção legítima continua funcionando, e MEDE.
# Este é o par que faz o caso A morder: sem ele, um rodador que reprovasse SEMPRE
# passaria nos três primeiros checks.
#
# ⚠️ O ALVO NUNCA É ESTA SUÍTE. Apontar o rodador para o próprio arquivo que o
# dispara é recursão infinita — esta suíte roda o rodador, que roda esta suíte,
# que roda o rodador. Aconteceu de verdade na primeira escrita deste teste, e só
# apareceu quando a mutação (reverter o conserto do caso A) deixou a chamada
# seguir em frente. O alvo é uma suíte VIZINHA, barata e que não dispara nada.
codigo, saida = roda("--py", "scripts/test_crlf.py"
                     if os.path.exists(os.path.join(RAIZ, "scripts", "test_crlf.py"))
                     else "_shared/test_regua_texto.py")
check("com seleção o rodador volta a rodar (não reprova por reprovar)",
      "suíte(s)" in saida and "nenhuma seleção" not in saida, saida[:200])

# C) A régua velha, a do glob que não casa nada, continua de pé — o conserto do
# vão de cima não pode ter afrouxado o nível de baixo.
codigo, saida = roda("--py", "nao/existe/glob/nenhum_*.py")
check("glob que não casa nada continua reprovando", codigo != 0,
      "exit=%d" % codigo)
check("e diz qual padrão não casou", "nenhum arquivo casou" in saida, saida[:200])

print("\nrun_suites-seleção: %d ok, %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
