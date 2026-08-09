#!/usr/bin/env python3
"""Bancada do sobras.py — um caso por natureza, e o caso limpo.

Uma natureza por caso porque as três somem por motivos DIFERENTES: o worktree é
pasta, a reserva é arquivo velho, o processo é pai morto. Uma suíte que só testa
o total passaria com duas varreduras quebradas.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sobras  # noqa: E402

FALHAS = []


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def _git(d, *args):
    subprocess.run(["git", "-C", d] + list(args), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   stdin=subprocess.DEVNULL, start_new_session=True)


def caso_worktree():
    d = tempfile.mkdtemp(prefix="sobras-wt-")
    try:
        repo = os.path.join(d, "repo")
        os.makedirs(repo)
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@t")
        _git(repo, "config", "user.name", "t")
        open(os.path.join(repo, "a.py"), "w").write("x = 1\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "um")

        check("repo sem worktree extra não acusa nada", sobras.worktrees(repo) == [])

        wt = os.path.join(d, "copia")
        _git(repo, "worktree", "add", "-q", "-b", "sobra", wt)
        r = sobras.worktrees(repo)
        # No macOS o git devolve o caminho real (/private/var/…) e o tempfile dá
        # o link (/var/…) — comparar cru reprovaria por causa do symlink.
        check("acha a cópia de trabalho parada",
              len(r) == 1 and os.path.realpath(r[0]["o_que"]) == os.path.realpath(wt))
        check("diz o tamanho dela em bytes",
              r[0]["unidade"] == "bytes" and r[0]["tamanho"] > 0)

        shutil.rmtree(wt)
        r = sobras.worktrees(repo)
        check("worktree registrado com a pasta sumida ainda aparece",
              len(r) == 1 and "sumiu" in r[0]["detalhe"] and r[0]["tamanho"] == 0)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def caso_reserva():
    d = tempfile.mkdtemp(prefix="sobras-res-")
    try:
        nova = os.path.join(d, "sessao__motor-a.files")
        open(nova, "w").write("a.py\nb.py\n")
        check("reserva recente não é sobra", sobras.reservas(d, ttl_min=720) == [])

        velha = os.path.join(d, "sessao__motor-b.files")
        open(velha, "w").write("x.py\ny.py\nz.py\n")
        antes = time.time() - 800 * 60
        os.utime(velha, (antes, antes))
        r = sobras.reservas(d, ttl_min=720)
        check("acha a reserva presa", len(r) == 1 and r[0]["o_que"] == "sessao__motor-b")
        check("diz o tamanho dela em arquivos travados",
              r[0]["tamanho"] == 3 and r[0]["unidade"] == "arquivos travados")

        check("diretório de reservas inexistente não quebra",
              sobras.reservas(os.path.join(d, "nao-existe")) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)


PS = """  PID  PPID    RSS COMMAND
  101     1  40960 node /proj/alvo/server.js
  102  9999  81920 node /proj/alvo/vivo.js
  103     1  10240 node /outro/projeto/server.js
  777     1  20480 python3 /proj/alvo/eu.py
"""


def caso_processo():
    r = sobras.processos("/proj/alvo", ps_texto=PS, meu_pid=777)
    check("acha só o processo órfão deste projeto", len(r) == 1 and "pid 101" in r[0]["o_que"])
    check("diz o tamanho dele em memória",
          r[0]["tamanho"] == 40960 and r[0]["unidade"] == "KB de memória")
    check("processo com pai vivo não é sobra", all("102" not in x["o_que"] for x in r))
    check("órfão de outro projeto não é sobra desta missão",
          all("103" not in x["o_que"] for x in r))
    check("o próprio processo da varredura nunca se acusa",
          all("777" not in x["o_que"] for x in r))
    check("ps mudo não quebra a varredura", sobras.processos("/proj/alvo", ps_texto="") == [])


def caso_relatorio():
    d = tempfile.mkdtemp(prefix="sobras-rel-")
    try:
        os.environ["CLAUDE_CONFIG_DIR"] = d
        check("projeto limpo sai com 0", sobras.main(["--raiz", d]) == 0)
        res = os.path.join(d, "sovai", "reservas")
        os.makedirs(res)
        p = os.path.join(res, "s__m.files")
        open(p, "w").write("a.py\n")
        antes = time.time() - 800 * 60
        os.utime(p, (antes, antes))
        check("achou sobra ⇒ sai com 1", sobras.main(["--raiz", d, "--json"]) == 1)
    finally:
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("sobras")
    caso_worktree()
    caso_reserva()
    caso_processo()
    caso_relatorio()
    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
