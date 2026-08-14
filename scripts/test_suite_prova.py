#!/usr/bin/env python3
"""Suíte da PROVA da esteira — verde só viaja com a árvore que foi medida.

Por que existe: o gate de commit passou a consumir a prova que `scripts/suite.sh`
grava no green-cache, para não re-medir o que a esteira acabou de medir (sem isso o
portão custava 20min nesta máquina e a chamada de commit do motor morria aos 2min —
3h20 de corrida, zero commits, medido em 2026-08-14). Prova é atalho poderoso: se
ela for gravada uma vez a mais do que deve, o portão para de olhar código que
ninguém rodou. Os três casos abaixo trancam as três formas de isso acontecer.

  1. esteira VERMELHA não grava        — o óbvio, e o mais grave se falhar
  2. árvore que MUDOU no meio não grava — o que foi medido não é o que está no disco
  3. esteira verde com árvore parada GRAVA — senão o atalho não existe

O cenário é um repositório de mentira com uma suíte controlada: nada aqui toca o
registro real (`GREEN_SUITE_DIR` aponta para um diretório descartável) nem a árvore
de verdade.

    python3 scripts/test_suite_prova.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ✓ %s" % nome)
    else:
        falhas += 1
        print("  ✗ %s%s" % (nome, ("  → " + detalhe) if detalhe else ""))


def monta(raiz):
    """Repositório de mentira com a forma mínima que o suite.sh espera."""
    os.makedirs(os.path.join(raiz, "_shared"), exist_ok=True)
    os.makedirs(os.path.join(raiz, "scripts"), exist_ok=True)
    for nome in ("green-cache.sh",):
        shutil.copy(os.path.join(RAIZ, "_shared", nome),
                    os.path.join(raiz, "_shared", nome))
    subprocess.run(["git", "init", "-q"], cwd=raiz, check=True,
                   stdin=subprocess.DEVNULL, start_new_session=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=raiz, check=True,
                   stdin=subprocess.DEVNULL, start_new_session=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=raiz, check=True,
                   stdin=subprocess.DEVNULL, start_new_session=True)
    with open(os.path.join(raiz, "arquivo.txt"), "w") as f:
        f.write("base\n")
    subprocess.run(["git", "add", "-A"], cwd=raiz, check=True,
                   stdout=subprocess.DEVNULL,
                   stdin=subprocess.DEVNULL, start_new_session=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=raiz, check=True,
                   stdin=subprocess.DEVNULL, start_new_session=True)


def escreve_esteira(raiz, corpo_da_medicao):
    """Grava um suite.sh com o MESMO fecho do real, e a medição parametrizada.

    O fecho (retrato antes, comparação depois, mark condicional) é copiado do
    arquivo real: é ele que está sob teste. Só a parte que "roda as suítes" é
    trocada por um corpo controlado, para o caso poder decidir o RC e mexer (ou
    não) na árvore no meio da rodada.
    """
    real = open(os.path.join(RAIZ, "scripts", "suite.sh"), encoding="utf-8").read()
    corte = real.index("# ── A PROVA VIAJA COM A ÁRVORE")
    fecho = real[corte:]
    with open(os.path.join(raiz, "scripts", "suite.sh"), "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env bash\nset -uo pipefail\n")
        f.write('RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"\ncd "$RAIZ"\n')
        # o mesmo retrato-antes do arquivo real
        f.write('ARVORE_ANTES=""\n')
        f.write('if [ -f "$RAIZ/_shared/green-cache.sh" ]; then\n')
        f.write('  . "$RAIZ/_shared/green-cache.sh" 2>/dev/null || true\n')
        f.write('  type green_tree_hash >/dev/null 2>&1 && '
                'ARVORE_ANTES=$(green_tree_hash "$RAIZ" 2>/dev/null || true)\n')
        f.write("fi\n")
        f.write(corpo_da_medicao)
        f.write("\n" + fecho)


def roda(raiz, registro):
    env = dict(os.environ, GREEN_SUITE_DIR=registro)
    return subprocess.run(["bash", os.path.join(raiz, "scripts", "suite.sh")],
                          cwd=raiz, env=env, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, start_new_session=True)


def tem_prova(raiz, registro):
    """Consulta o registro do jeito que o portão consulta: green_cache_check full."""
    env = dict(os.environ, GREEN_SUITE_DIR=registro)
    r = subprocess.run(
        ["bash", "-c",
         '. "$1/_shared/green-cache.sh" && green_cache_check "$1" full',
         "_", raiz],
        env=env, capture_output=True, text=True,
        stdin=subprocess.DEVNULL, start_new_session=True)
    return r.returncode == 0


print("A prova da esteira — verde só viaja com a árvore que foi medida\n")

# ── 1 · esteira VERMELHA não grava ──────────────────────────────────────────
base = tempfile.mkdtemp(prefix="suite-prova-vermelha-")
reg = tempfile.mkdtemp(prefix="registro-")
try:
    monta(base)
    escreve_esteira(base, "RC=1\n")   # mediu e reprovou
    r = roda(base, reg)
    check("esteira vermelha não grava prova", not tem_prova(base, reg))
    check("e sai com o código de falha", r.returncode == 1, "rc=%d" % r.returncode)
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(reg, ignore_errors=True)

# ── 2 · árvore que MUDOU durante a rodada não grava ─────────────────────────
# É o caso real que motivou a guarda: outra sessão (ou o próprio motor) editando
# enquanto a esteira mede. O que foi medido não é o que está no disco no fim.
base = tempfile.mkdtemp(prefix="suite-prova-mudou-")
reg = tempfile.mkdtemp(prefix="registro-")
try:
    monta(base)
    escreve_esteira(base, 'RC=0\necho "editado no meio da rodada" >> "$RAIZ/arquivo.txt"\n')
    r = roda(base, reg)
    check("árvore mudada no meio não grava prova", not tem_prova(base, reg))
    check("e a esteira DIZ que não gravou, em vez de calar",
          "ÁRVORE MUDOU" in r.stdout, r.stdout.strip()[-120:])
    check("o veredito verde da esteira é preservado (a prova é atalho, não veredito)",
          r.returncode == 0, "rc=%d" % r.returncode)
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(reg, ignore_errors=True)

# ── 3 · esteira verde com árvore parada GRAVA ───────────────────────────────
base = tempfile.mkdtemp(prefix="suite-prova-verde-")
reg = tempfile.mkdtemp(prefix="registro-")
try:
    monta(base)
    escreve_esteira(base, "RC=0\n")
    r = roda(base, reg)
    check("esteira verde com árvore parada grava a prova", tem_prova(base, reg),
          r.stdout.strip()[-120:])
    check("e anuncia a gravação nomeando a árvore",
          "prova da esteira gravada" in r.stdout, r.stdout.strip()[-120:])
finally:
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(reg, ignore_errors=True)

print("\n%d ok / %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
