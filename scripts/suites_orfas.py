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

# A esteira mudou de casa em 2026-08-14 (F17.3): os globos saíram de dentro do
# workflow e passaram a viver em `scripts/suite.sh`, que o CI invoca. As DUAS
# ficam na lista, na ordem de hoje primeiro — pelo mesmo motivo que o leitor
# abaixo entende dois formatos: leitor de fonte não deve quebrar no dia em que a
# fonte se muda, deve procurar onde ela pode estar. Um cobrador que lê zero globo
# acusa TODA suíte do repositório como órfã.
ESTEIRAS = ("scripts/suite.sh", ".github/workflows/portability.yml")
ESTEIRA = ESTEIRAS[0]   # compatibilidade com quem importa o nome antigo


def rastreadas(root):
    """Os arquivos de teste que o git conhece. Sem git, devolve None (não acusa)."""
    try:
        out = subprocess.run(["git", "-C", root, "ls-files"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return sorted(caminho for caminho in out.stdout.splitlines()
                  if re.search(r"(^|/)test_[^/]*\.(py|sh)$", caminho))


def globos(root):
    """Os padrões que a esteira roda, lidos do próprio arquivo dela.

    Lidos do arquivo, nunca copiados para cá: cópia de lista é a mesma dívida que
    o número escrito no artigo — ela defasa e ninguém percebe.

    ⚠️ **Reconhece as DUAS formas**, e a segunda é a de hoje. Até 2026-08-10 as
    suítes rodavam num laço de shell (`roda <runner> '<glob>' …`); desde então
    rodam por `scripts/run_suites.py --py '<glob>' … --sh '<glob>' …`. Quando o
    formato mudou e este leitor só conhecia o antigo, ele passou a ler ZERO globo
    — e um cobrador que lê zero globo acusa TODA suíte do repositório como órfã.
    A forma velha fica reconhecida de propósito: leitor de formato não deve
    quebrar no dia em que o formato muda, deve entender os dois e continuar.
    """
    texto = None
    for rel in ESTEIRAS:
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                t = fh.read()
        except OSError:
            continue
        # A primeira fonte que REALMENTE declara globo vence. Só existir não basta:
        # depois do F17.3 o workflow continua no disco, mas sem a lista dentro —
        # aceitar o arquivo pela existência faria o cobrador ler zero e acusar tudo.
        if "test_" in t and ("run_suites.py" in t or t.strip().startswith("roda ")
                             or re.search(r"^\s*roda ", t, re.M)):
            texto = t
            break
    if texto is None:
        return None
    pats = []
    dentro = False
    for linha in texto.splitlines():
        s = linha.strip()
        if s.startswith("roda "):                       # forma antiga: laço de shell
            pats.extend(re.findall(r"'([^']+)'", s))
            continue
        if "run_suites.py" in s:                        # forma de hoje
            dentro = True
        if dentro:
            pats.extend(re.findall(r"'([^']+)'", s))
            if not s.endswith("\\"):
                dentro = False
    # ⚠️ A esteira pode ter MAIS DE UMA invocação — desde 2026-08-14 ela roda em duas
    # fases (o grosso em paralelo, e as que disputam estado global em série). Um
    # leitor que parasse na primeira leria só metade dos globos e acusaria a outra
    # metade de órfã: 28 suítes de hook de uma vez. O laço acima já percorre o
    # arquivo inteiro; o que falta é pegar o globo que mora numa VARIÁVEL, que é como
    # a lista das seriais é declarada (`SERIAIS='...'`), fora de qualquer invocação.
    for m in re.finditer(r"^[A-Z_]+='([^']+)'", texto, re.M):
        if "test_" in m.group(1):
            pats.append(m.group(1))
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
