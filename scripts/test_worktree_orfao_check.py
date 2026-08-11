#!/usr/bin/env python3
"""Bancada do worktree_orfao_check — ele acha a cópia parada, e não grita à toa?

O caso que dá sentido à suíte é o do `tem_codigo`: cópia parada COM programa dentro é a
que a busca por nome alcança, e foi ela que fez 7 marcações rodarem um validador 548
linhas mais velho. Cópia sem código incomoda no disco; cópia com código muda o resultado.
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import worktree_orfao_check as W  # noqa: E402

FALHAS = []


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo] + list(args), stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)


def repo_com_worktree(com_codigo, sujo):
    """Um repositório de mentira com uma cópia de trabalho parada dentro."""
    d = tempfile.mkdtemp(prefix="wt-orfao-")
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    open(os.path.join(d, "leiame.md"), "w", encoding="utf-8").write("base\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "base")
    wt = os.path.join(d, ".claude", "worktrees", "wf_teste-1")
    os.makedirs(os.path.dirname(wt), exist_ok=True)
    git(d, "worktree", "add", "-q", "-b", "worktree-teste", wt)
    if com_codigo:
        open(os.path.join(wt, "programa.py"), "w", encoding="utf-8").write("x = 1\n")
        git(wt, "add", "-A")
        git(wt, "commit", "-qm", "com codigo")
    if sujo:
        open(os.path.join(wt, "leiame.md"), "w", encoding="utf-8").write("mexido\n")
    return d


def main():
    print("worktree_orfao_check")

    d = tempfile.mkdtemp(prefix="wt-limpo-")
    try:
        check("repositório sem cópia parada devolve vazio", W.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = repo_com_worktree(com_codigo=True, sujo=True)
    try:
        r = W.varre(d)
        check("acha a cópia parada", len(r) == 1)
        check("nomeia o caminho dela", r and ".claude/worktrees/wf_teste-1" in r[0]["caminho"])
        check("conta o que está sujo dentro", r and r[0]["sujos"] == 1)
        check("marca que há CÓDIGO dentro — é isso que a busca alcança",
              r and r[0]["tem_codigo"] is True)
        check("diz em que ramo ela está", r and r[0]["ramo"] == "worktree-teste")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # Cópia limpa e sem programa ainda é acusada — ela é caminho de execução em potencial
    # assim que alguém escrever algo lá —, mas o relatório a distingue da perigosa.
    d = repo_com_worktree(com_codigo=False, sujo=False)
    try:
        r = W.varre(d)
        check("cópia limpa e sem código também é acusada", len(r) == 1)
        check("mas ela sai marcada como SEM código", r and r[0]["tem_codigo"] is False)
        check("e com zero sujos", r and r[0]["sujos"] == 0)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
