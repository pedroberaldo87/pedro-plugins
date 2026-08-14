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
import concurrent.futures
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



# O que a suíte imprime de errado costuma ficar no MEIO, não no fim: ela lista
# dezenas de casos verdes depois do que falhou. Cortar pelas últimas 25 linhas
# escondia justamente o erro — aconteceu com `test_doc_load`, cujo relatório saiu
# com 23 linhas de `ok` e nenhuma da falha.
MARCAS = ("FAIL", "FALHOU", "✗", "Traceback", "Error", "error:", "AssertionError",
          "not found", "No such file")


def linhas_que_importam(saida, teto=25):
    """As linhas que explicam a falha, e o fim como contexto — nessa ordem."""
    linhas = saida.strip().splitlines()
    marcadas = [ln for ln in linhas if any(m in ln for m in MARCAS)]
    if not marcadas:
        return linhas[-teto:]
    # a falha primeiro; o resto do teto vai para o fim da saída, que costuma
    # trazer o placar ("N passou · M falhou")
    corte = marcadas[:teto - 5] if len(marcadas) > teto - 5 else marcadas
    fim = [ln for ln in linhas[-(teto - len(corte)):] if ln not in corte]
    return corte + (["   …"] if fim else []) + fim


def main(argv=None):
    ap = argparse.ArgumentParser()
    # `action="extend"`, não o default: com o default, repetir a bandeira SUBSTITUI
    # a lista anterior, e `--py A --py B` rodava só B — silenciosamente, que é o
    # defeito que este programa existe para não ter.
    ap.add_argument("--py", nargs="*", action="extend", default=[])
    ap.add_argument("--sh", nargs="*", action="extend", default=[])
    ap.add_argument("--timeout", type=float, default=180.0)
    # Quantas suítes ao mesmo tempo. O padrão vem do número de núcleos porque o
    # gargalo é DISPARAR PROCESSO, não calcular: no Windows criar processo custa
    # perto de dez vezes o do macOS, e as suítes de shell disparam às centenas.
    # Sequencial, o job foi de 23m42s a 26m28s em três rodadas — subindo, porque
    # suíte consertada para de falhar na hora e passa a rodar até o fim.
    ap.add_argument("--jobs", type=int, default=0)
    a = ap.parse_args(argv)

    # SELEÇÃO VAZIA É ERRO, NUNCA VERDE (F17.2). A régua do glob-que-não-casa já
    # existia dentro do `expande()`, um nível fundo demais: sem NENHUM `--py` e
    # NENHUM `--sh` o laço dele nem itera, `tarefas` fica vazia, e o programa
    # imprimia "0 suíte(s) · 0 problema(s)" e saía ZERO. Medido em 2026-08-13: foi
    # esse o comando que a casca do /sprint passou ao motor como `suiteCmd`, e a
    # guarda de saúde e a suíte da largada declararam a corrida verde tendo medido
    # NADA — 87 minutos e nenhum passo marcado. Medidor que não mede tem que dizer
    # que não mediu; dizer verde é a doença que a fase F17 cura.
    if not a.py and not a.sh:
        print("::error::nenhuma seleção: passe --py e/ou --sh com os globs das suítes.\n"
              "  A esteira canônica deste repositório está em .github/workflows/portability.yml\n"
              "  (o mesmo comando que o CI roda). Rodar sem seleção mediria ZERO suíte, e\n"
              "  sair verde sem medir nada é pior que não rodar.", file=sys.stderr)
        return 2

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

    jobs = a.jobs or min(8, (os.cpu_count() or 2))
    print("  rodando %d suíte(s) com até %d ao mesmo tempo" % (len(tarefas), jobs))

    # Uma suíte por thread: o trabalho é esperar processo, não calcular, então
    # thread basta e não há estado do interpretador a compartilhar. Cada suíte já
    # roda em sessão própria e escreve numa saída própria — o que elas dividem é o
    # DISCO, e é por isso que o número não sobe indefinidamente: suíte que monta
    # árvore em disco fica mais lenta se houver dez fazendo o mesmo.
    ruins = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futuros = {pool.submit(roda, cmd, alvo, a.timeout): alvo for cmd, alvo in tarefas}
        for fut in concurrent.futures.as_completed(futuros):
            alvo = futuros[fut]
            estado, seg, saida = fut.result()
            print("  %-8s %6.1fs  %s" % (estado, seg, alvo), flush=True)
            if estado != "ok":
                ruins.append((estado, alvo, saida))
    # A ordem de conclusão é a de quem terminou primeiro; o RELATÓRIO sai em ordem
    # de nome, para que duas rodadas sejam comparáveis linha a linha.
    ruins.sort(key=lambda x: x[1])

    print("\n%d suíte(s) · %d problema(s)" % (len(tarefas), len(ruins)))
    for estado, alvo, saida in ruins:
        print("\n───────── %s: %s" % (estado, alvo))
        if saida is None:
            print("   (estourou o teto de %.0fs — pendurou)" % a.timeout)
            continue
        for ln in linhas_que_importam(saida):
            print("   " + ln[:200])
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
