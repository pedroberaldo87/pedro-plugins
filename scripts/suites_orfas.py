#!/usr/bin/env python3
"""Suíte rastreada que nenhum globo da esteira alcança é órfã — e isto a acusa.

POR QUE EXISTE. O Artigo 5 da constituição exige que "toda suíte rastreada rode em
algum gate; nenhum arquivo de teste fica órfão de cobrador". Até 2026-08-07 a prova
disso era um NÚMERO ESCRITO no próprio artigo — "são 54, e a soma dos sete globos
também dá 54". Número escrito envelhece: no dia em que isto nasceu a contagem real
era 60, e a lei ainda dizia 54.

A troca, decidida pelo dono: a lei para de cravar quantos e passa a exigir que os
dois lados BATAM. Quem confere é este script, não a memória de quem escreve — e o
resultado não depende de ninguém atualizar texto nenhum.

O que ele compara:
  - o que o git rastreia:  git ls-files | grep -E '(^|/)test_'
  - o que a esteira roda:  os globos de .github/workflows/portability.yml

Órfã = rastreada e fora de todos os globos. Sai 1 e lista cada uma.

O caminho inverso — globo que não casa nada — já é coberto pela própria esteira
(`nenhum arquivo casou em $pat` reprova lá). Aqui não se duplica isso.
"""

import fnmatch
import os
import re
import subprocess
import sys

ESTEIRA = ".github/workflows/portability.yml"


def rastreadas(root):
    """Os arquivos de teste que o git conhece. Sem git, devolve None (não acusa)."""
    try:
        out = subprocess.run(["git", "-C", root, "ls-files"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return sorted(caminho for caminho in out.stdout.splitlines()
                  if re.search(r"(^|/)test_[^/]*\.(py|sh)$", caminho))


def globos(root):
    """Os padrões que a esteira roda, lidos da linha `roda <runner> '<glob>' …`.

    Lidos do arquivo, nunca copiados para cá: cópia de lista é a mesma dívida que
    o número escrito no artigo — ela defasa e ninguém percebe.
    """
    caminho = os.path.join(root, ESTEIRA)
    try:
        with open(caminho, encoding="utf-8") as fh:
            texto = fh.read()
    except OSError:
        return None
    pats = []
    for linha in texto.splitlines():
        s = linha.strip()
        if not s.startswith("roda "):
            continue
        pats.extend(re.findall(r"'([^']+)'", s))
    return [p for p in pats if "test_" in p]


def orfas(root="."):
    tests = rastreadas(root)
    pats = globos(root)
    if tests is None or pats is None:
        return None, tests, pats
    fora = [t for t in tests if not any(fnmatch.fnmatch(t, p) for p in pats)]
    return fora, tests, pats


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    fora, tests, pats = orfas(root)

    if fora is None:
        # Sem git ou sem a esteira não dá para julgar, e não julgar significa não
        # acusar ninguém — mesma direção segura do resto do repositório.
        print("sem git ou sem %s — não há o que comparar" % ESTEIRA)
        return 0

    print("suítes rastreadas: %d · globos da esteira: %d" % (len(tests), len(pats)))
    for p in pats:
        n = sum(1 for t in tests if fnmatch.fnmatch(t, p))
        print("  %-34s → %d" % (p, n))

    if not fora:
        print("\nNenhuma órfã: toda suíte rastreada casa algum globo da esteira.")
        return 0

    print("\n⛔ %d suíte(s) rastreada(s) que a esteira NÃO roda:" % len(fora))
    for t in fora:
        print("   %s" % t)
    print("\nOu ela entra num globo de %s, ou sai do git." % ESTEIRA)
    return 1


if __name__ == "__main__":
    sys.exit(main())
