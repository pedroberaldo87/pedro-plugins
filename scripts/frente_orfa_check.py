#!/usr/bin/env python3
"""Frente sem dono não se fecha sozinha — e isto a acusa (R-42, F31.4).

POR QUE EXISTE. A medição de 2026-08-20 achou 7 branches locais e 5 remotas
órfãs, e uma worktree de sessão morta havia 3 dias. Frente que nenhum plano
ativo declara é trabalho que ninguém vai fundir nem descartar — fica apodrecendo
até o deploy reclamar. O rito de fechamento (passo 2b da persistência do sprint)
fecha a frente da MISSÃO CORRENTE; o que ele não alcança é a frente que sobrou
de missão passada. Este script varre exatamente esse resto.

Os três casos que ele acusa:

  1. branch local fora da main que NENHUM plano ativo declara como frente;
  2. worktree registrada cujo caminho não existe, ou que nenhum plano ativo
     declara (a missão dela já fechou — ou nunca foi registrada);
  3. branch remota com ZERO commits fora da main — já está inteira no tronco,
     só o nome ficou de pé.

Plano ativo = `.claude/plans/*.plan.json` com `status: "active"` (ausente conta
como ativo — na dúvida, NÃO acusar: falso órfão derruba frente viva).

⚠️ NÃO entra no release-gate, de propósito: branch viva durante a missão é
estado legítimo, e um gate aqui bloquearia todo commit de bloco da própria
frente. Quem roda é o passo de persistência do sprint (relatório, nunca
bloqueio) e quem quiser à mão:

    python3 scripts/frente_orfa_check.py [raiz]   # sai 1 se achou órfã

Fail-open: sem git, sem remoto, sem pasta de planos — cala e sai 0. Acusação
sem medição confiável é pior que medição nenhuma.
"""

import glob
import json
import os
import subprocess
import sys

for _canal in (sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def _git(root, *args):
    """Roda git na raiz dada; falha (sem git, fora de repo) devolve None."""
    try:
        out = subprocess.run(["git", "-C", root] + list(args),
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def branch_main(root):
    """A main de verdade do projeto (origin/HEAD), fallback main → master."""
    out = _git(root, "symbolic-ref", "--quiet", "--short",
               "refs/remotes/origin/HEAD")
    if out and out.strip():
        return out.strip().split("/", 1)[-1]
    for nome in ("main", "master"):
        if _git(root, "show-ref", "--verify", "--quiet",
                "refs/heads/%s" % nome) is not None:
            return nome
    return "main"


def frentes_ativas(root):
    """(branches, worktrees) que algum plano ATIVO declara como frente.

    Plano ilegível não derruba a varredura: JSON quebrado se pula — acusar por
    causa de arquivo torto seria culpar a branch pelo defeito do plano.
    """
    branches, worktrees = set(), set()
    for caminho in glob.glob(os.path.join(root, ".claude", "plans",
                                          "*.plan.json")):
        try:
            with open(caminho, encoding="utf-8") as f:
                plano = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(plano, dict):
            continue
        if plano.get("status", "active") != "active":
            continue
        fr = plano.get("frente")
        if not isinstance(fr, dict):
            continue
        if fr.get("branch"):
            branches.add(fr["branch"])
        if fr.get("worktree"):
            worktrees.add(os.path.realpath(fr["worktree"]))
    return branches, worktrees


def orfas(root):
    """A lista de acusações, uma linha por órfã. Vazia = repo limpo."""
    achados = []
    main = branch_main(root)
    declaradas, worktrees_ativas = frentes_ativas(root)

    # 1. branch local fora da main que nenhum plano ativo declara
    out = _git(root, "for-each-ref", "refs/heads",
               "--format=%(refname:short)")
    if out is None:
        return []          # sem git não há o que medir — fail-open
    for branch in out.split():
        if branch != main and branch not in declaradas:
            achados.append("branch local órfã: %s — nenhum plano ativo a "
                           "declara como frente" % branch)

    # 2. worktree registrada: caminho sumido, ou missão já fechada
    out = _git(root, "worktree", "list", "--porcelain") or ""
    caminhos = [linha[len("worktree "):] for linha in out.splitlines()
                if linha.startswith("worktree ")]
    raiz_real = os.path.realpath(root)
    for caminho in caminhos:
        real = os.path.realpath(caminho)
        if real == raiz_real:
            continue       # a árvore principal não é frente
        if not os.path.isdir(caminho):
            achados.append("worktree órfã: %s — o caminho não existe mais"
                           % caminho)
        elif real not in worktrees_ativas:
            achados.append("worktree órfã: %s — nenhum plano ativo a declara "
                           "(missão fechada ou nunca registrada)" % caminho)

    # 3. branch remota com zero commits fora da main
    out = _git(root, "for-each-ref", "refs/remotes",
               "--format=%(refname:short)") or ""
    for ref in out.split():
        if "/" not in ref:
            continue       # `origin/HEAD` encurta para só `origin` — não é branch
        curto = ref.split("/", 1)[-1]
        if curto in ("HEAD", main):
            continue
        fora = _git(root, "rev-list", "--count", ref, "^%s" % main)
        if fora is not None and fora.strip() == "0":
            achados.append("branch remota órfã: %s — zero commits fora da "
                           "%s, já está inteira no tronco" % (ref, main))
    return achados


def main_cli(argv):
    root = argv[1] if len(argv) > 1 else os.getcwd()
    achados = orfas(root)
    if not achados:
        return 0           # repo limpo fica calado
    print("frente_orfa_check: %d frente(s) órfã(s)" % len(achados))
    for linha in achados:
        print("  - %s" % linha)
    print("→ fechar é o rito 2b da persistência do sprint; à mão: "
          "tag de resgate → merge/descartar → worktree remove → branch -d")
    return 1


if __name__ == "__main__":
    sys.exit(main_cli(sys.argv))
