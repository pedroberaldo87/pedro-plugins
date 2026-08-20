#!/usr/bin/env python3
"""Suíte do frente_orfa_check (F31.4): três órfãs reproduzidas + repo limpo calado.

Cada cenário nasce num repo git de verdade, em diretório temporário — nada de
mock de saída de git: o defeito que o check caça mora no estado real do repo.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(AQUI, "frente_orfa_check.py")

FAILS = []


def check(label, cond):
    print("  %s %s" % ("ok  " if cond else "FAIL", label))
    if not cond:
        FAILS.append(label)


def git(root, *args):
    subprocess.run(["git", "-C", root] + list(args), check=True,
                   capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)


def repo_novo(base, nome):
    root = os.path.join(base, nome)
    os.makedirs(root)
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "suite@example.com")
    git(root, "config", "user.name", "suite")
    open(os.path.join(root, "a.txt"), "w").write("a\n")
    git(root, "add", "a.txt")
    git(root, "commit", "-q", "-m", "raiz")
    return root


def grava_plano(root, plan_id, status="active", frente=None):
    pasta = os.path.join(root, ".claude", "plans")
    os.makedirs(pasta, exist_ok=True)
    plano = {"id": plan_id, "status": status}
    if frente:
        plano["frente"] = frente
    with open(os.path.join(pasta, "%s.plan.json" % plan_id), "w",
              encoding="utf-8") as f:
        json.dump(plano, f)


def roda(root):
    r = subprocess.run([sys.executable, CHECK, root],
                       capture_output=True, text=True, encoding="utf-8",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    return r.returncode, r.stdout


def main():
    base = tempfile.mkdtemp(prefix="frente-orfa-")
    try:
        # ---- repo limpo: só a main, nada declarado → CALADO ----
        print("repo limpo fica calado")
        limpo = repo_novo(base, "limpo")
        rc, out = roda(limpo)
        check("sai 0", rc == 0)
        check("sem uma linha de saída", out.strip() == "")

        # ---- caso 1: branch local que nenhum plano ativo declara ----
        print("caso 1: branch local órfã")
        r1 = repo_novo(base, "caso1")
        git(r1, "branch", "frente/2026-01-01-x")
        git(r1, "branch", "frente/2026-01-01-y")
        # a declarada por plano ATIVO não é órfã; a outra é
        grava_plano(r1, "2026-01-01-x",
                    frente={"branch": "frente/2026-01-01-x", "worktree": "/nx"})
        rc, out = roda(r1)
        check("sai 1", rc == 1)
        check("acusa a não-declarada", "frente/2026-01-01-y" in out)
        check("cala sobre a declarada",
              "branch local órfã: frente/2026-01-01-x" not in out)

        # ---- caso 2: worktree com caminho sumido / missão fechada ----
        print("caso 2: worktree órfã")
        r2 = repo_novo(base, "caso2")
        git(r2, "branch", "frente/2026-01-01-a")
        git(r2, "branch", "frente/2026-01-01-b")
        wt_sumida = os.path.join(base, "wt-sumida")
        wt_fechada = os.path.join(base, "wt-fechada")
        git(r2, "worktree", "add", wt_sumida, "frente/2026-01-01-a")
        git(r2, "worktree", "add", wt_fechada, "frente/2026-01-01-b")
        shutil.rmtree(wt_sumida)                       # o caminho não existe mais
        grava_plano(r2, "2026-01-01-a", frente={
            "branch": "frente/2026-01-01-a", "worktree": wt_sumida})
        grava_plano(r2, "2026-01-01-b", status="done", frente={
            "branch": "frente/2026-01-01-b", "worktree": wt_fechada})
        rc, out = roda(r2)
        check("sai 1", rc == 1)
        check("acusa o caminho sumido", "não existe mais" in out
              and "wt-sumida" in out)
        check("acusa a missão fechada", "wt-fechada" in out
              and "missão fechada" in out)

        # ---- caso 3: branch remota com zero commits fora da main ----
        print("caso 3: branch remota órfã")
        r3 = repo_novo(base, "caso3")
        bare = os.path.join(base, "origin.git")
        subprocess.run(["git", "init", "-q", "--bare", bare], check=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
        git(r3, "remote", "add", "origin", bare)
        git(r3, "push", "-q", "origin", "main")
        # merged: nasce da main sem commit novo → zero fora da main
        git(r3, "branch", "frente/merged")
        git(r3, "push", "-q", "origin", "frente/merged")
        # viva: tem commit que a main não tem → NÃO se acusa como remota órfã
        git(r3, "checkout", "-q", "-b", "frente/viva")
        open(os.path.join(r3, "b.txt"), "w").write("b\n")
        git(r3, "add", "b.txt")
        git(r3, "commit", "-q", "-m", "obra")
        git(r3, "push", "-q", "origin", "frente/viva")
        git(r3, "checkout", "-q", "main")
        # origin/HEAD encurta para só "origin" no for-each-ref — não pode acusar
        git(r3, "remote", "set-head", "origin", "main")
        # os planos ativos declaram as duas LOCAIS (o caso aqui é só a remota)
        grava_plano(r3, "m", frente={"branch": "frente/merged", "worktree": "/n1"})
        grava_plano(r3, "v", frente={"branch": "frente/viva", "worktree": "/n2"})
        rc, out = roda(r3)
        check("sai 1", rc == 1)
        check("acusa a remota já contida na main",
              "branch remota órfã: origin/frente/merged" in out)
        check("cala sobre a remota com commit próprio",
              "branch remota órfã: origin/frente/viva" not in out)
        check("cala sobre origin/HEAD (que encurta para 'origin')",
              "órfã: origin —" not in out)
    finally:
        shutil.rmtree(base, ignore_errors=True)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
