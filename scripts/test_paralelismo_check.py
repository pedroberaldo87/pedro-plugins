#!/usr/bin/env python3
"""test_paralelismo_check.py — o cobrador de paralelismo acusa a suíte instável?

O `--flake` do `scripts/run_suites.py` roda a mesma seleção duas vezes ao mesmo
tempo e reprova quem responde coisas diferentes nas duas. Aqui se monta uma suíte
propositalmente instável — duas cópias disputando UM arquivo de chave fixa, o
mesmo defeito que a esteira real teve — e se exige que ela seja nomeada; e uma
esteira só com suíte estável, exigindo silêncio.
"""
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RODADOR = os.path.join(RAIZ, "scripts", "run_suites.py")

ESTAVEL = "import sys; sys.exit(0)\n"

# A disputa, em duas linhas: quem cria o arquivo primeiro passa, quem chega
# depois falha. Uma rodada verde e uma vermelha, garantidas — é exatamente a
# assinatura que o cobrador tem que enxergar.
INSTAVEL = (
    "import os, sys\n"
    "try:\n"
    "    os.close(os.open(os.environ['DISPUTA'], os.O_CREAT | os.O_EXCL | os.O_WRONLY))\n"
    "except FileExistsError:\n"
    "    sys.exit(1)\n"
)


def roda(casa, *extra):
    r = subprocess.run([sys.executable, RODADOR, "--flake", "--janela", "10",
                        "--py", "test_*.py", *extra],
                       cwd=casa, capture_output=True, text=True,
                       env=dict(os.environ, DISPUTA=os.path.join(casa, "disputa.mark")))
    return r.returncode, r.stdout + r.stderr


falhas = 0


def checa(nome, cond, prova):
    global falhas
    print(("  ok   " if cond else "  FALHOU ") + nome)
    if not cond:
        falhas += 1
        print("   ─── saída ───\n" + prova)


with tempfile.TemporaryDirectory() as casa:
    open(os.path.join(casa, "test_estavel.py"), "w").write(ESTAVEL)
    open(os.path.join(casa, "test_instavel.py"), "w").write(INSTAVEL)
    rc, saida = roda(casa)
    checa("acusa a suíte instável", rc == 1 and "INSTÁVEL" in saida
          and "test_instavel.py" in saida.split("instável(is)")[-1], saida)
    checa("não acusa a estável junto",
          "test_estavel.py" not in saida.split("instável(is)")[-1], saida)

with tempfile.TemporaryDirectory() as casa:
    open(os.path.join(casa, "test_estavel.py"), "w").write(ESTAVEL)
    rc, saida = roda(casa)
    checa("fica calado com a esteira estável",
          rc == 0 and "0 instável(is)" in saida, saida)

print("%d falha(s)" % falhas)
sys.exit(1 if falhas else 0)
