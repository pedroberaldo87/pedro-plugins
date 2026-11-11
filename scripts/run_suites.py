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
import shutil
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


# ── SUÍTE PULADA POR SISTEMA: SÓ COM MOTIVO, SEMPRE EM VOZ ALTA ─────────────
#
# Esta tabela existe por causa de UMA suíte, e de um dano medido. No Windows do CI,
# `plugins/lixeiro/hooks/test_lixeiro_hooks.sh` MATAVA A ESTEIRA INTEIRA: o hook de
# fim de sessão do lixeiro acha a raiz "órfã" do servidor de teste subindo pela
# árvore de processos, e só para nos ancestrais DO PRÓPRIO HOOK. Lá a cadeia do hook
# se quebra no primeiro salto (o pai MSYS já morreu: o `ppid` aponta para um pid que
# não existe mais), a subida atravessa o rodador, o bash do passo, o `Runner.Worker`
# e chega à raiz da máquina — e o SIGTERM cai em cada um. Medido com a morte
# desligada (sonda `debug/win-lixeiro-ancestry`, run 42971755541): os alvos eram o
# `bash scripts/suite.sh`, o `run_suites.py` e, por fim, `lsass.exe`/`svchost.exe`. O
# job saía "verde" sem placar, sem `rc=`, com as ~30 suítes seguintes nunca contadas.
#
# O conserto é do PRODUTO (`lixeiro.py:raiz_orfa`: não subir quando a cadeia do hook
# está quebrada), não do rodador nem do teste — fica fora desta passada e RASTREADO na
# descrição do PR #10 (nota W1). Até lá a suíte não roda no Windows, e o rodador diz
# isso de três jeitos: linha `↷ PULADA`, anotação `::warning::` e a contagem no placar.
# Não é "teste ignorado": entra aqui só quem tem o motivo escrito e o arquivo no disco
# (`test_run_suites_pulas_por_so.py` cobra os dois). `RUN_SUITES_NAO_PULA=1` roda tudo,
# para quem for medir o conserto do produto numa máquina Windows descartável.
PULA_NO_SO = {
    "nt": {
        "plugins/lixeiro/hooks/test_lixeiro_hooks.sh":
            "o lixeiro sobe pela árvore de processos até a raiz órfã do servidor de teste e, no "
            "Windows, a cadeia de ancestrais do hook vem quebrada: o SIGTERM atinge o rodador, o "
            "runner do CI e processos do sistema, e derruba a esteira sem placar (PR #10, nota W1)",
    },
}


def so_atual():
    """`nt` ou `posix`. `RUN_SUITES_SO` existe só para a suíte do rodador encenar o outro
    sistema sem precisar dele."""
    return os.environ.get("RUN_SUITES_SO") or os.name


def pulas_do_so(so=None):
    """alvo normalizado (com `/`) -> motivo, para o sistema dado. POSIX nunca pula nada."""
    if os.environ.get("RUN_SUITES_NAO_PULA"):
        return {}
    return PULA_NO_SO.get(so or so_atual(), {})


def separa_puladas(alvos, so=None):
    """([alvos que rodam], [(alvo, motivo) dos pulados]) — na ordem recebida."""
    pulas = pulas_do_so(so)
    rodam, puladas = [], []
    for a in alvos:
        motivo = pulas.get(a.replace("\\", "/"))
        if motivo:
            puladas.append((a, motivo))
        else:
            rodam.append(a)
    return rodam, puladas


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
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL,
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


_TEMP_MACOS = []


def _temporario_do_macos():
    """O temporário que o `mktemp -d` do macOS usa mesmo com `TMPDIR` trocado, ou "".

    `getconf DARWIN_USER_TEMP_DIR` é a pergunta que o próprio `mktemp` faz; o `os` do
    Python não a expõe. Só o macOS responde; nos outros sistemas não há o que perguntar.
    Perguntado uma vez só: o rodador chama `tetos_de_git` a cada suíte.
    """
    if not _TEMP_MACOS:
        achado = ""
        if sys.platform == "darwin":
            try:
                r = subprocess.run(["getconf", "DARWIN_USER_TEMP_DIR"], capture_output=True,
                                   text=True, timeout=10, stdin=subprocess.DEVNULL,
                                   start_new_session=True)
                if r.returncode == 0:
                    achado = r.stdout.strip()
            except Exception:
                pass
        _TEMP_MACOS.append(achado)
    return _TEMP_MACOS[0]


def tetos_de_git(casa):
    """Os diretórios acima dos quais o git NÃO procura repositório (GIT_CEILING_DIRECTORIES).

    Suíte que cria uma pasta temporária e pergunta ao git onde está o projeto espera
    "em lugar nenhum". Se algum ancestral do temporário for um repositório — um `.git`
    esquecido na pasta de temporários do sistema, um `TMPDIR` dentro de um clone — o git
    sobe até lá e responde com ele, e a suíte passa a depender do que existe fora do
    repositório de quem roda. Medido numa máquina de trabalho: onze suítes vermelhas por
    um `.git` solto no temporário do usuário, todas verdes no CI.

    O teto vale para o temporário do sistema (que o `mktemp -d` do macOS usa mesmo com
    `TMPDIR` trocado) e para a pasta-mãe da casa própria da suíte. Repositório criado
    DENTRO deles continua achado: o teto fecha a subida, não o git. O caminho vai
    resolvido (`realpath`) porque o git compara com o caminho real, e `/var` no macOS é
    link para `/private/var`.
    """
    candidatos = [os.path.dirname(casa), tempfile.gettempdir(), _temporario_do_macos()]
    tetos = []
    for c in candidatos:
        if c:
            real = os.path.realpath(c)
            if real not in tetos:
                tetos.append(real)
    # O teto que o dono já tinha continua valendo: o do rodador entra junto, não no lugar.
    antigo = os.environ.get("GIT_CEILING_DIRECTORIES")
    if antigo:
        tetos.insert(0, antigo)
    return os.pathsep.join(tetos)


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
    # ── CADA SUÍTE NO PRÓPRIO TEMPORÁRIO ────────────────────────────────────
    # A CAUSA das suítes instáveis, apurada em 2026-08-20: a chave do estado que
    # elas escrevem é um id de sessão CRAVADO no código (`dasid`, `sess-x`,
    # `cksid`…) e a casa é o temporário do sistema, o mesmo para todo mundo. Duas
    # esteiras de pé — duas sessões de agente, ou o CI ao lado do terminal — e uma
    # apaga o arquivo que a outra acabou de escrever; a suíte acusada muda a cada
    # rodada, que é a assinatura de disputa, não de defeito. Serializar não
    # resolvia: a colisão é da CHAVE, não da ordem. Trocar todos os ids por nome
    # sorteado seria o mesmo conserto repetido em cinco arquivos e esquecido no
    # sexto — aqui a casa é que passa a ser própria, e o id fixo deixa de importar.
    # As três variáveis andam juntas porque o Windows lê TMP/TEMP e não TMPDIR.
    casa = tempfile.mkdtemp(prefix="suite-")
    # O git também não pode subir do temporário para um repositório alheio (ver
    # `tetos_de_git`): sem isso, a suíte lê o que existe FORA do repositório de quem roda.
    ambiente = dict(os.environ, TMPDIR=casa, TMP=casa, TEMP=casa,
                    GIT_CEILING_DIRECTORIES=tetos_de_git(casa))
    try:
        p = subprocess.Popen(cmd + [alvo], stdout=tmp, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True,
                             env=ambiente)
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
        # Só DEPOIS de a árvore morrer: apagar a casa embaixo de um processo vivo
        # deixaria a suíte escrevendo em diretório que não existe mais.
        shutil.rmtree(casa, ignore_errors=True)



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
    # ── COBRADOR DE PARALELISMO (F19.3) ─────────────────────────────────────
    # Roda a MESMA seleção duas vezes, as duas ao mesmo tempo no mesmo pool, e
    # reprova só quem responde coisas diferentes nas duas: passou numa e falhou na
    # outra. Isso é INSTABILIDADE — a suíte disputa alguma coisa com a cópia dela
    # (arquivo de chave fixa, porta, diretório compartilhado) —, e é o defeito que
    # a casa própria de temporário veio matar. Suíte que falha nas DUAS não é
    # assunto daqui: é obra ruim, e quem a acusa é a esteira normal.
    ap.add_argument("--flake", action="store_true")
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
    py_alvos, puladas = separa_puladas(expande(a.py))
    sh_alvos, puladas_sh = separa_puladas(expande(a.sh))
    puladas += puladas_sh
    for alvo, motivo in puladas:
        print("  ↷ PULADA no %s: %s\n      motivo: %s" % (so_atual(), alvo, motivo), flush=True)
        print("::warning::suíte pulada no %s: %s — %s" % (so_atual(), alvo, motivo), flush=True)
    tarefas = [([py], t) for t in py_alvos]
    bash = bash_posix()
    if sh_alvos and bash is None:
        print("  ↷ %d suíte(s) de shell puladas: nenhum bash funcional nesta máquina" % len(sh_alvos))
    else:
        tarefas += [([bash], t) for t in sh_alvos]

    if a.flake:
        tarefas += list(tarefas)   # as duas rodadas disputam o mesmo pool
    jobs = a.jobs or min(8, (os.cpu_count() or 2))
    print("  rodando %d suíte(s) com até %d ao mesmo tempo" % (len(tarefas), jobs))

    # Uma suíte por thread: o trabalho é esperar processo, não calcular, então
    # thread basta e não há estado do interpretador a compartilhar. Cada suíte já
    # roda em sessão própria e escreve numa saída própria — o que elas dividem é o
    # DISCO, e é por isso que o número não sobe indefinidamente: suíte que monta
    # árvore em disco fica mais lenta se houver dez fazendo o mesmo.
    ruins = []
    vereditos = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        futuros = {pool.submit(roda, cmd, alvo, a.janela, bash): alvo for cmd, alvo in tarefas}
        for fut in concurrent.futures.as_completed(futuros):
            alvo = futuros[fut]
            estado, seg, saida = fut.result()
            print("  %-8s %6.1fs  %s" % (estado, seg, alvo), flush=True)
            vereditos.setdefault(alvo, []).append(estado)
            if estado != "ok":
                ruins.append((estado, alvo, saida))

    if a.flake:
        instaveis = sorted(alvo for alvo, v in vereditos.items() if len(set(v)) > 1)
        print("\n%d suíte(s) rodadas 2x · %d instável(is)" % (len(vereditos), len(instaveis)))
        for alvo in instaveis:
            print("   INSTÁVEL  %s  (rodada 1: %s · rodada 2: %s)"
                  % (alvo, vereditos[alvo][0], vereditos[alvo][1]))
        if instaveis:
            print("\n   Veredito que muda entre duas rodadas simultâneas não é obra ruim: é\n"
                  "   DISPUTA. Procure estado de chave fixa (arquivo com id cravado, porta,\n"
                  "   diretório compartilhado) que as duas cópias escrevem.")
        return 1 if instaveis else 0
    # A ordem de conclusão é a de quem terminou primeiro; o RELATÓRIO sai em ordem
    # de nome, para que duas rodadas sejam comparáveis linha a linha.
    ruins.sort(key=lambda x: x[1])

    # flush em TODA linha do relatório: no Windows do CI o processo perdia o resumo
    # inteiro (runs 32491657813 · 32493288667 · 32494014937 — as suítes saíam, o
    # placar não, e o passo seguia como se o rc fosse 0).
    print("\n%d suíte(s) · %d problema(s)" % (len(tarefas), len(ruins)), flush=True)
    if puladas:
        print("%d suíte(s) PULADA(S) neste sistema, com motivo (linhas '↷ PULADA' acima): %s"
              % (len(puladas), ", ".join(a for a, _ in puladas)), flush=True)
    for estado, alvo, saida in ruins:
        print("\n───────── %s: %s" % (estado, alvo), flush=True)
        if saida is None:
            print("   (TRAVOU: sem CPU na árvore e sem saída nova por 2 janelas "
                  "de %.0fs — morta pelo vigia)" % a.janela, flush=True)
            continue
        for ln in linhas_que_importam(saida):
            print("   " + ln[:200], flush=True)
    return 1 if ruins else 0


if __name__ == "__main__":
    rc = main()
    # A última palavra do rodador, dita por ele mesmo: quem lê o log sabe que o
    # processo CHEGOU ao fim (no Windows do CI ele morria no meio sem dizer nada).
    print("run_suites: veredito rc=%d" % rc, flush=True)
    sys.exit(rc)
