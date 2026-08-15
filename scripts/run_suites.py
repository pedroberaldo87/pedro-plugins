#!/usr/bin/env python3
"""run_suites.py — roda as suítes da esteira com VIGIA DE PROGRESSO e placar por arquivo.

Por que existe (2026-08-11)
---------------------------
A esteira rodava as suítes num laço de shell com `set -e`: a primeira que falhasse
matava o passo, e as demais nunca eram executadas — cada conserto revelava a
próxima falha, uma por rodada de 4 minutos. Pior: uma suíte que PENDURA deixava o
job no ar por mais de dez minutos sem dizer qual era (o log de um job em andamento
não sai), e a única saída era cancelar às cegas.

Este programa resolve os dois de uma vez:

- **vigia de progresso** (`--janela`, 120 s): a cada janela se pergunta se a suíte
  ainda ANDA — CPU na árvore de processos dela (medido por
  `_shared/vivo-ou-dormindo.sh`) ou saída crescendo. Só quem fica parada nos dois
  sinais, por duas janelas seguidas, é morta: aparece como TRAVOU com o nome, e as
  outras seguem. Teto fixo mediria a máquina, não o código — a mesma suíte passava
  na máquina livre e reprovava na ocupada;
- **não para na primeira**: roda todas e devolve o placar completo, então uma
  rodada mostra TODOS os defeitos em vez de um;
- **tempo de cada uma**, para a lentidão aparecer antes de virar travamento.

Sai 1 se alguma falhou ou travou. Só stdlib, como todo o resto do repo.

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
    esteira 'passou' sem executar suíte nenhuma.

    `SUITE_PULA` (globs separados por espaço) tira arquivos da seleção. Ele existe
    para a esteira rodar em DUAS fases — o grosso em paralelo e o punhado que
    disputa estado global em série — sem que a segunda fase precise reescrever os
    globos da primeira com exceções enumeradas plugin a plugin. Não é lista de
    teste ignorado: quem sai daqui roda na outra fase, e o `suite.sh` soma os dois
    códigos de saída.
    """
    pula = set()
    for g in (os.environ.get("SUITE_PULA") or "").split():
        pula |= {p for p in glob.glob(g, recursive=True) if os.path.isfile(p)}
    fora = []
    for pat in padroes:
        casou = sorted(p for p in glob.glob(pat, recursive=True) if os.path.isfile(p))
        if not casou:
            print("::error::nenhum arquivo casou em %s" % pat)
            sys.exit(1)
        # O glob tem que casar ALGO antes de descontar o que a outra fase leva —
        # senão um `SUITE_PULA` largo demais esconderia um glob que já morreu.
        casou = [c for c in casou if c not in pula]
        print("  %s → %d suíte(s)%s" % (pat, len(casou),
                                        " (fora as da fase serial)" if pula else ""))
        fora.extend(casou)
    return fora


VIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared",
                    "vivo-ou-dormindo.sh")


def cpu_viva(bash, pgid, amostra):
    """A árvore daquele disparo andou de CPU entre duas amostras?

    Quem MEDE é `_shared/vivo-ou-dormindo.sh` — aqui só se pergunta, com o grupo
    de processos como escopo. Segunda redação da mesma medição está proibida: uma
    delas envelheceria calada, e as duas responderiam coisas diferentes sobre a
    mesma máquina.

    Devolve True/False, ou None quando NÃO deu para medir (sem bash, ou o `ps`
    mudo). None não é "vivo" nem "dormindo": é ausência de sinal, e quem chama
    decide com o outro sinal que tem.
    """
    if bash is None:
        return None
    try:
        r = subprocess.run([bash, VIVO, str(amostra), "--grupo", str(pgid)],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           start_new_session=True, timeout=amostra + 30)
    except Exception:
        return None
    fala = (r.stdout or "").strip().splitlines()
    fala = fala[-1] if fala else ""
    if fala == "vivo":
        return True
    if fala == "dormindo":
        return False
    return None


def roda(cmd, alvo, janela, bash):
    """Uma suíte, sob VIGIA DE PROGRESSO — não sob teto de relógio.

    Teto fixo mede a máquina, não o código: o mesmo arquivo passa na máquina
    livre e reprova na ocupada, e o veredito vira sorteio (medido em 2026-08-14,
    três largadas do /sprint derrubadas por suítes que só estavam lentas). Aqui a
    pergunta é outra e é a certa: ela ainda está ANDANDO? Anda quem consome CPU
    na própria árvore de processos OU cresce a saída. Uma suíte só morre quando
    os DOIS sinais ficam parados por duas janelas seguidas — nenhuma delas
    sozinha basta: há suíte que calcula em silêncio, e há suíte que imprime
    esperando I/O.

    A suíte vai para uma SESSÃO PRÓPRIA — o que dá a ela um grupo de processos
    próprio (pgid == pid do disparo), que é justamente o escopo do vigia, e o que
    garante que matar mate a árvore inteira em vez de deixar filho segurando o
    job.
    """
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
        # A amostra de CPU cabe DENTRO da janela: ela é o pedaço da janela em que
        # se olha, não um tempo somado por cima dele.
        amostra = max(1, min(3, int(janela / 4) or 1))
        paradas, escrito = 0, 0
        while True:
            try:
                p.wait(timeout=janela)
                break
            except subprocess.TimeoutExpired:
                pass
            # Tamanho pelo descritor: a posição do OBJETO de arquivo daqui não anda
            # — quem escreve é o filho, com o descritor dele.
            agora = os.fstat(tmp.fileno()).st_size
            cresceu, escrito = agora > escrito, agora
            viva = None if cresceu else cpu_viva(bash, p.pid, amostra)
            if cresceu or viva is True:
                paradas = 0
                continue
            paradas += 1
            # Sem CPU medível (máquina sem bash, `ps` mudo), a saída decide
            # sozinha — e aí com o dobro da paciência, porque é meio sinal.
            if paradas >= (2 if viva is False else 4):
                return "TRAVOU", time.time() - t0, None
        tmp.seek(0)
        return ("ok" if p.returncode == 0 else "FALHOU"), time.time() - t0, tmp.read()
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
    # A JANELA DE MEDIÇÃO, não um teto de relógio: de quanto em quanto tempo se
    # pergunta se a suíte ainda anda. `--timeout` continua aceito para não quebrar
    # comando antigo, e vira janela — o teto fixo saiu de cena (ver `roda`).
    ap.add_argument("--janela", "--timeout", dest="janela", type=float, default=120.0)
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
        futuros = {pool.submit(roda, cmd, alvo, a.janela, bash): alvo for cmd, alvo in tarefas}
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
            print("   (TRAVOU: sem CPU na árvore e sem saída nova por 2 janelas "
                  "de %.0fs — morta pelo vigia)" % a.janela)
            continue
        for ln in linhas_que_importam(saida):
            print("   " + ln[:200])
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
