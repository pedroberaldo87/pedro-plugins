#!/usr/bin/env python3
"""run_suites.py — roda as suítes da esteira com TETO DE TEMPO e placar por arquivo.

Por que existe (2026-08-11)
---------------------------
A esteira rodava as suítes num laço de shell com `set -e`: a primeira que falhasse
matava o passo, e as demais nunca eram executadas — cada conserto revelava a
próxima falha, uma por rodada de 4 minutos. Pior: uma suíte que PENDURA deixava o
job no ar por mais de dez minutos sem dizer qual era (o log de um job em andamento
não sai), e a única saída era cancelar às cegas.

Este programa resolve os dois de uma vez:

- **teto por suíte** (`--timeout`, 180 s): quem pendura é morto, aparece como
  TIMEOUT com o nome, e as outras seguem;
- **não para na primeira**: roda todas e devolve o placar completo, então uma
  rodada mostra TODOS os defeitos em vez de um;
- **tempo de cada uma**, para a lentidão aparecer antes de virar travamento.

Sai 1 se alguma falhou ou estourou o teto. Só stdlib, como todo o resto do repo.

    python3 scripts/run_suites.py --py "plugins/*/lib/test_*.py" ...
    python3 scripts/run_suites.py --sh "plugins/*/hooks/test_*.sh" ...
"""
import argparse
import glob
import os
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared"))
from bash_posix import bash_posix  # noqa: E402

for _canal in (sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass


def expande(padroes):
    """Um glob por padrão, e padrão que não casa NADA é erro — foi assim que a
    esteira 'passou' sem executar suíte nenhuma."""
    fora = []
    for pat in padroes:
        casou = sorted(p for p in glob.glob(pat, recursive=True) if os.path.isfile(p))
        if not casou:
            print("::error::nenhum arquivo casou em %s" % pat)
            sys.exit(1)
        print("  %s → %d suíte(s)" % (pat, len(casou)))
        fora.extend(casou)
    return fora


def roda(cmd, alvo, teto):
    """Uma suíte, com teto. A suíte vai para uma SESSÃO PRÓPRIA: quem pendura
    costuma ter aberto filhos, e matar só o pai deixa a árvore de pé segurando o
    job — que é justamente o desfecho que este programa existe para evitar."""
    t0 = time.time()
    p = None
    # A saída vai para um ARQUIVO, não para um cano. Com cano, a leitura só termina
    # quando o último descendente que herdou o descritor o fecha — uma suíte que
    # deixa um neto vivo pendura a leitura DEPOIS de já ter terminado, e o placar
    # a acusa de TIMEOUT sem ela ter demorado nada. Medido: duas suítes de 50 s
    # aparecendo como 180 s. Arquivo não tem escritor a esperar.
    tmp = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
    try:
        p = subprocess.Popen(cmd + [alvo], stdout=tmp, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        p.wait(timeout=teto)
        tmp.seek(0)
        return ("ok" if p.returncode == 0 else "FALHOU"), time.time() - t0, tmp.read()
    except subprocess.TimeoutExpired:
        return "TIMEOUT", time.time() - t0, None
    finally:
        tmp.close()
        if p is not None and p.poll() is None:
            try:                       # Windows não tem killpg/getpgid nem SIGKILL:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)   # AttributeError, não OSError
            except (OSError, AttributeError):
                p.kill()
            try:
                p.wait(timeout=5)
            except Exception:
                pass


def main(argv=None):
    ap = argparse.ArgumentParser()
    # `action="extend"`, não o default: com o default, repetir a bandeira SUBSTITUI
    # a lista anterior, e `--py A --py B` rodava só B — silenciosamente, que é o
    # defeito que este programa existe para não ter.
    ap.add_argument("--py", nargs="*", action="extend", default=[])
    ap.add_argument("--sh", nargs="*", action="extend", default=[])
    ap.add_argument("--timeout", type=float, default=180.0)
    a = ap.parse_args(argv)

    py = sys.executable
    # `bash` do PATH está ERRADO no Windows: lá ele é o do WSL (`System32\bash.exe`),
    # que sem distro instalada responde uma reclamação em UTF-16 — e as ~35 suítes de
    # shell reprovam todas de uma vez, por causa do interpretador. A régua não é estar
    # no PATH, é RESPONDER, e o repositório já tinha a receita (`_shared/bash_posix.py`).
    # Sem nenhum bash que responda, as suítes de shell PULAM declarando: comando de
    # shell sem shell não é falha de quem escreveu o comando.
    sh_alvos = expande(a.sh)
    tarefas = [([py], t) for t in expande(a.py)]
    bash = bash_posix()
    if sh_alvos and bash is None:
        print("  ↷ %d suíte(s) de shell puladas: nenhum bash funcional nesta máquina" % len(sh_alvos))
    else:
        tarefas += [([bash], t) for t in sh_alvos]

    ruins = []
    for cmd, alvo in tarefas:
        estado, seg, saida = roda(cmd, alvo, a.timeout)
        print("  %-8s %6.1fs  %s" % (estado, seg, alvo), flush=True)
        if estado != "ok":
            ruins.append((estado, alvo, saida))

    print("\n%d suíte(s) · %d problema(s)" % (len(tarefas), len(ruins)))
    for estado, alvo, saida in ruins:
        print("\n───────── %s: %s" % (estado, alvo))
        if saida is None:
            print("   (estourou o teto de %.0fs — pendurou)" % a.timeout)
            continue
        for ln in saida.strip().splitlines()[-25:]:
            print("   " + ln[:200])
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
