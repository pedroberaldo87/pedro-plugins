#!/usr/bin/env python3
"""worktree_orfao_check.py — cópia de trabalho parada é caminho de execução silencioso.

O QUE ACONTECEU, e é por isso que este cobrador existe: em 2026-08-08 uma autópsia
descobriu que **14 de 41 marcações do motor rodaram um binário que não é o da árvore**.
Sete delas passaram por um `plan_state.py` **548 linhas mais velho**, sem as funções de
recusa — o validador que existe para barrar marcação sem prova. Ninguém escolheu isso: os
agentes procuraram o arquivo pelo nome, o `find` alcançou as cópias em
`.claude/worktrees/`, e a resposta errada estava lá, plausível.

**As cópias não eram desobediência.** Elas nasceram em 06/08, entre 02:46 e 19:09, e a
regra que proíbe isolar entrou às 20:03 do mesmo dia. A regra proibiu criar novas e
**não varreu as velhas** — e cópia proibida que fica no disco continua sendo *executável*.

A régua que sai daqui, e ela vale além deste caso:

    Regra nova que proíbe um artefato nasce com a varredura do que já existe,
    no mesmo commit. Senão o artefato proibido continua ao alcance de quem busca.

Este é o caso especial de desenvolver o harness COM o harness: uma versão anterior dele
fica no disco, e quem procura por nome acha a antiga antes da atual.

Régua manual:  python3 scripts/worktree_orfao_check.py
Sai 1 e nomeia cada cópia parada, com o que há dentro.
"""

import argparse
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Onde este repositório põe cópia de trabalho. Não é varredura de disco: só o lugar que
# o próprio harness usa — vasculhar a máquina inteira é assunto do /check-skills.
ONDE = os.path.join(".claude", "worktrees")


def _git(*args, cwd=None):
    try:
        r = subprocess.run(["git", "-C", cwd or RAIZ] + list(args),
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=30, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout if r.returncode == 0 else ""


def varre(raiz=None):
    """[{caminho, sujos, ramo, tem_codigo}] — as cópias paradas, com o que há nelas."""
    raiz = raiz or RAIZ
    base = os.path.join(raiz, ONDE)
    if not os.path.isdir(base):
        return []
    fora = []
    for nome in sorted(os.listdir(base)):
        wt = os.path.join(base, nome)
        if not os.path.isdir(wt):
            continue
        sujos = [ln for ln in _git("status", "--porcelain", cwd=wt).splitlines() if ln.strip()]
        ramo = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt).strip()
        # O que torna a cópia PERIGOSA não é existir: é ter programa dentro, porque é
        # isso que a busca por nome alcança.
        tem_codigo = False
        for b, _, fs in os.walk(wt):
            if ".git" in b:
                continue
            if any(f.endswith((".py", ".sh", ".mjs", ".js")) for f in fs):
                tem_codigo = True
                break
        fora.append({"caminho": os.path.join(ONDE, nome), "sujos": len(sujos),
                     "ramo": ramo, "tem_codigo": tem_codigo})
    return fora


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    r = varre()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 1 if r else 0
    if not r:
        print("worktree-orfao: OK — nenhuma cópia de trabalho parada no disco")
        return 0
    print("CÓPIA DE TRABALHO PARADA — %d, e cada uma é caminho de execução silencioso:\n" % len(r))
    for x in r:
        marca = "⚠️ COM CÓDIGO DENTRO" if x["tem_codigo"] else "sem código"
        print("  %s  ramo=%s · %d arquivo(s) sujo(s) · %s"
              % (x["caminho"], x["ramo"] or "?", x["sujos"], marca))
    print("\nQuem procura um arquivo pelo NOME alcança a cópia antes do original — e a")
    print("cópia é uma versão anterior do mesmo programa. Confira o que há dentro e remova:")
    print("  git worktree remove --force <caminho>   ·   git branch -D <ramo>")
    return 1


if __name__ == "__main__":
    sys.exit(main())
