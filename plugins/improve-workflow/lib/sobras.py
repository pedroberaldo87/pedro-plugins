#!/usr/bin/env python3
"""sobras.py — o que a missão deixou no disco e não entra em relatório nenhum.

O relatório do motor conta as tarefas. Três coisas sobrevivem ao fim da missão e
não aparecem em lugar nenhum — some entre uma missão e a próxima, e só reaparece
como defeito:

  worktree  — cópia de trabalho parada. Quem procura arquivo pelo NOME acha ela
              antes do original, e ela é uma versão anterior do mesmo programa.
  reserva   — trava de arquivos de um motor que morreu sem liberar. Ela só expira
              quando OUTRO motor esbarra nela; até lá, ninguém a vê.
  processo  — servidor/suíte que o agente subiu e ficou de pé depois que o pai
              morreu (reparentado para o init).

O comando ACHA e MEDE. Não remove nada: o julgamento é de quem lê.

    python3 sobras.py [--raiz <projeto>] [--json]
"""

import argparse
import json
import os
import subprocess
import sys
import time


def _git(raiz, *args):
    try:
        r = subprocess.run(["git", "-C", raiz] + list(args), stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=30,
                           start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout if r.returncode == 0 else ""


def _bytes_da_pasta(caminho):
    total = 0
    for base, _, arqs in os.walk(caminho):
        for f in arqs:
            try:
                total += os.lstat(os.path.join(base, f)).st_size
            except OSError:
                pass
    return total


# ── worktree ────────────────────────────────────────────────────────────────
def worktrees(raiz, porcelain=None):
    """Toda cópia de trabalho que não é a principal. A primeira linha do
    `--porcelain` é sempre o worktree principal — as outras é que sobraram."""
    saida = _git(raiz, "worktree", "list", "--porcelain") if porcelain is None else porcelain
    caminhos = [ln[9:].strip() for ln in saida.splitlines() if ln.startswith("worktree ")]
    fora = []
    for c in caminhos[1:]:
        existe = os.path.isdir(c)
        fora.append({
            "natureza": "worktree",
            "o_que": c,
            "tamanho": _bytes_da_pasta(c) if existe else 0,
            "unidade": "bytes",
            "detalhe": "registrado no git mas a pasta sumiu" if not existe else "cópia parada no disco",
        })
    return fora


# ── reserva ─────────────────────────────────────────────────────────────────
def reservas(dir_reservas=None, agora=None, ttl_min=None):
    """Reserva de arquivos mais velha que o TTL — o motor dela morreu sem liberar.

    Mesmo TTL do `reserva-de-arquivos.sh` (720 min), pela mesma razão: a missão
    que ele protege é longa por definição."""
    if dir_reservas is None:
        base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        dir_reservas = os.path.join(base, "sovai", "reservas")
    ttl_min = int(os.environ.get("SOVAI_RESERVA_TTL_MIN", 720)) if ttl_min is None else ttl_min
    agora = time.time() if agora is None else agora
    if not os.path.isdir(dir_reservas):
        return []
    fora = []
    for nome in sorted(os.listdir(dir_reservas)):
        if not nome.endswith(".files"):
            continue
        p = os.path.join(dir_reservas, nome)
        try:
            idade_min = (agora - os.stat(p).st_mtime) / 60.0
            linhas = [ln for ln in open(p, encoding="utf-8").read().splitlines() if ln.strip()]
        except OSError:
            continue
        if idade_min <= ttl_min:
            continue
        fora.append({
            "natureza": "reserva",
            "o_que": nome[:-len(".files")],
            "tamanho": len(linhas),
            "unidade": "arquivos travados",
            "detalhe": "parada há %d h — recusa todo motor que encostar nesses arquivos"
                       % (idade_min / 60),
        })
    return fora


# ── processo ────────────────────────────────────────────────────────────────
def _ps():
    try:
        r = subprocess.run(["ps", "-eo", "pid,ppid,rss,command"], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=30, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return ""
    return r.stdout if r.returncode == 0 else ""


def processos(raiz, ps_texto=None, meu_pid=None):
    """Processo que nomeia este projeto e cujo pai já morreu (PPID 1).

    O pai morto é o que separa a sobra do trabalho vivo: enquanto o agente que
    subiu o servidor está de pé, o servidor é dele. Reparentado para o init, não
    é de ninguém, e ninguém vai fechá-lo.

    ponytail: casa o projeto pelo caminho na LINHA DE COMANDO, não pelo cwd real
    do processo — `lsof` por pid é caro e não é portátil. Processo que entrou no
    diretório e não repete o caminho escapa; se isso passar a doer, ler o cwd."""
    texto = _ps() if ps_texto is None else ps_texto
    meu = os.getpid() if meu_pid is None else meu_pid
    raiz = os.path.abspath(raiz)
    fora = []
    for ln in texto.splitlines()[1:]:
        campos = ln.split(None, 3)
        if len(campos) < 4:
            continue
        try:
            pid, ppid, rss = int(campos[0]), int(campos[1]), int(campos[2])
        except ValueError:
            continue
        cmd = campos[3]
        if ppid != 1 or pid == meu or raiz not in cmd:
            continue
        fora.append({
            "natureza": "processo",
            "o_que": "pid %d · %s" % (pid, cmd[:120]),
            "tamanho": rss,
            "unidade": "KB de memória",
            "detalhe": "pai já morreu (PPID 1) e ele continua de pé",
        })
    return fora


def varre(raiz=None):
    raiz = os.path.abspath(raiz or os.getcwd())
    return worktrees(raiz) + reservas() + processos(raiz)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--raiz", default=os.getcwd())
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    r = varre(a.raiz)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 1 if r else 0
    if not r:
        print("sobras: nenhuma — a missão não deixou worktree, reserva nem processo para trás")
        return 0
    print("SOBRAS DA MISSÃO — %d, e nenhuma delas entra em relatório nenhum:\n" % len(r))
    for x in r:
        print("  [%s] %s" % (x["natureza"], x["o_que"]))
        print("      %s %s · %s" % (x["tamanho"], x["unidade"], x["detalhe"]))
    print("\nNada foi removido: o que fazer com cada uma é leitura de quem está aqui.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
