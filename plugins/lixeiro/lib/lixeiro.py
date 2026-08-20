#!/usr/bin/env python3
"""lixeiro.py — o motor da coleta de processos deixados para trás.

A REGRA QUE MANDA EM TODAS: só é candidato o processo cuja ABERTURA foi anotada
por este mesmo mecanismo. Nome de programa NUNCA é critério — nesta máquina há
61 processos sob `node`, entre eles a própria sessão do Claude Code, os serviços
do harness e o navegador. `pkill node` mataria o trabalho junto com o lixo.

O ciclo:
  anota   (PostToolUse)  — o comando abriu processo? grava assinatura + hora + sessão
  colhe   (Stop)         — só morre o que não gastou CPU desde o turno anterior
  colhe   (SessionEnd)   — tudo que a sessão anotou
  varre   (SessionStart) — registro de sessão cujo dono não existe mais

Estado em ~/.claude/lixeiro/ — NUNCA dentro do plugin (que é cache reescrito a
cada bump de versão). Um arquivo por sessão, mais um log do que foi encerrado.

Portabilidade: usa só `ps -eo` (POSIX), sem `etimes` (que o macOS ignora em
silêncio) e sem `pkill`. Sistema sem `ps` utilizável: não encerra nada e sai calado.
No Windows o `ps` do Git Bash mente (formato próprio, pid MSYS) e não há `lsof`:
a enumeração vem de `Get-CimInstance` e a pasta de trabalho do PEB, por ctypes —
tudo em pid nativo, que é o que `os.kill` de lá aceita.
"""

import functools
import json
import os
import re
import signal
import subprocess
import sys
import time

# ── onde o estado mora ──────────────────────────────────────────────────────
def state_dir():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    d = os.path.join(base, "lixeiro")
    os.makedirs(d, exist_ok=True)
    return d


def registro_path(session_id):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "sem-sessao")
    return os.path.join(state_dir(), "sessao-%s.json" % safe)


def log_path():
    return os.path.join(state_dir(), "colhido.jsonl")


# ── o vocabulário: o que é abridor, e de que tipo ───────────────────────────
# EFÊMERO  — devia morrer sozinho ao fim do comando. Continuar vivo JÁ é o defeito.
# SERVIÇO  — existe para ficar de pé. Só morre quando fica ocioso.
# INTOCÁVEL— guarda estado e/ou serve outros trabalhos. Nunca recebe sinal.
EFEMERO = [
    r"\bpytest\b", r"\bvitest\b(?!.*\bwatch\b)", r"\bjest\b", r"\bnpm (run )?test\b",
    r"\btsc\b", r"\bwebpack\b(?!.*\bserve\b)", r"\besbuild\b", r"\bplaywright test\b",
    r"\bgo test\b", r"\bcargo test\b", r"\bmocha\b", r"\bnyc\b",
    # O neto que sobrevive ao pai: matar o `cargo` deixa os `rustc` filhos de pé,
    # dormindo com o lock do diretório de compilação na mão, e a tentativa seguinte
    # parece travada. Sem classe própria eles não casavam com anotação nenhuma e o
    # lixeiro nunca os tocava (medido em 2026-08-13, três órfãos de 14 minutos).
    r"/rustc\b", r"/rustdoc\b",
    # O resto do que uma sessão de Claude Code planta e devia morrer sozinho:
    # build e checagem (Rust, Go, JVM, .NET, C, formatador/linter de cada mundo).
    # `cargo run` NÃO entra: é servidor em desenvolvimento, e a classe dele é a de
    # baixo. `make` só conta como token executável, senão `cmake`/`gmake` de
    # terceiros casariam por substring.
    r"\bcargo (build|check|clippy|fmt)\b", r"\bgo (build|vet|generate)\b",
    r"\bgradle\w* (test|build|check|assemble)\b", r"\bmvn\b.*\b(test|package|verify|compile)\b",
    r"\bdotnet (test|build|publish)\b", r"(?:^|\s)(?:\S*/)?make(?:\s|$)",
    r"\beslint\b", r"\bprettier\b", r"\bruff\b", r"\bmypy\b", r"\bblack\b(?!.*\bserver\b)",
    r"\brspec\b", r"\bphpunit\b", r"\bcypress run\b", r"\btox\b",
    r"\bpip3? install\b", r"\buv (sync|pip|lock)\b",
    # Por stack, o que compila/testa e devia acabar: iOS/macOS, Flutter, C/C++ (o
    # compilador órfão do make, mesmo caso do rustc), Zig, Elixir, JVM (sbt/lein),
    # Haskell, PHP/Ruby (instalação de dependência), JS (instalação e build por
    # gerenciador). O que espera REDE segurando estado remoto (terraform, ansible,
    # git clone, npm publish, rsync) fica FORA de propósito: rede lenta é ociosa
    # e legítima, e a régua de CPU não distingue as duas.
    r"\bxcodebuild\b", r"\bswift (build|test)\b", r"\bflutter (build|test|analyze)\b",
    r"\bninja\b(?!.*\bserve\b)", r"\bbazel (build|test|run)\b", r"\bzig (build|test)\b",
    r"\bmix (test|compile|deps\.get)\b", r"\bsbt\b.*\b(test|compile|package)\b",
    r"(?:^|\s)(?:\S*/)?(?:gcc|g\+\+|clang|clang\+\+|cc1(?:plus)?|ld|lld|swiftc|javac|kotlinc)(?:\s|$)",
    r"\bcabal (build|test)\b", r"\bstack (build|test)\b", r"\bghc\b", r"\bdart compile\b",
    r"\bcomposer (install|update)\b", r"\bbundle (install|exec rspec)\b",
    r"\b(?:yarn|pnpm|npm|bun) (install|ci|run build|build)\b",
    r"\bgem install\b", r"\bpod install\b", r"\bgo mod download\b",
    # Suítes que faltavam por runtime: Deno, Bun, CMake e os runners de JS.
    r"\bdeno test\b", r"\bbun test\b", r"\bctest\b", r"\bnox\b", r"(?:^|\s)ava(?:\s|$)",
    # O build do mundo React/TypeScript: cada framework tem o seu, e todos deviam
    # acabar sozinhos. O dev de cada um está em SERVICO; aqui é só o one-shot.
    r"\b(?:next|vite|astro|gatsby|remix|react-scripts) build\b",
    r"\bturbo (?:run )?(build|test|lint)\b", r"\bnx (build|test|lint|affected)\b",
    # Python além do pytest: gerenciador, checador de tipo e linter.
    r"\bpoetry (install|lock|build)\b", r"\bpyright\b", r"\bflake8\b", r"\bisort\b",
    r"\bpylint\b", r"\bbiome (check|lint|format)\b", r"\bstylelint\b",
    r"\bgolangci-lint\b", r"\brubocop\b", r"\bswiftlint\b", r"\bshellcheck\b",
    # Geradores puros, sem estado remoto: prisma/graphql/protoc geram arquivo
    # local. `migrate` NÃO entra — migração morta no meio é estado pela metade.
    r"\bprisma generate\b", r"\bgraphql-codegen\b", r"\bprotoc\b",
    r"\bdrizzle-kit generate\b",
    # Tauri empacotando, Homebrew instalando, npx criando projeto, e os
    # conversores de mídia/documento que uma sessão dispara e esquece. Todos
    # gastam CPU enquanto trabalham — ocioso aqui é morto de verdade.
    r"\btauri (build|bundle)\b", r"\bbrew (install|upgrade|update|bundle)\b",
    r"\bnpx create-\S+", r"\belectron-builder\b", r"\bbuild-storybook\b",
    r"\bffmpeg\b", r"\bpandoc\b", r"\b(?:pdf|lua|xe)latex\b", r"\bmagick\b",
    r"\bsphinx-build\b", r"\bmkdocs build\b", r"\btypedoc\b",
]
SERVICO = [
    r"\bnext (dev|start)\b", r"\bnext-server\b", r"\bvite\b(?!.*\bbuild\b)",
    r"\bnpm run dev\b", r"\bnodemon\b", r"\bhttp\.server\b", r"\bhttp-server\b",
    r"\buvicorn\b", r"\bgunicorn\b", r"\bflask run\b", r"\brails server\b",
    r"\bstorybook\b", r"\bng serve\b", r"\bserve -s\b",
    # Túnel: `ssh` só conta quando carrega redirecionamento de porta (-L/-R/-D) ou
    # fica de pé sem shell (-N). `ssh servidor` para trabalhar não é abridor, e as
    # letras são MAIÚSCULAS de verdade — `(?-i:…)` desliga o re.I só aqui, senão
    # o `-l usuario` de qualquer ssh viraria serviço.
    r"\bssh\b(?=.*\s(?-i:-[LRDN]))",
    # Servidor por arquivo: `node app.js`. Exige o arquivo — `node` sozinho não
    # significa nada (é o caso que dá nome à regra) e o binário de suíte/build já
    # foi reconhecido antes, porque EFEMERO é consultado primeiro.
    r"\bnode\s+(?:-\S+\s+)*\S+\.[mc]?[jt]s\b",
    # Os outros servidores que uma sessão sobe para ver a coisa funcionando:
    # Django, FastAPI, Laravel, Deno/Bun em watch, `cargo run`, live-reload de Go,
    # Jupyter/Streamlit, tailwind em watch, e túnel de exposição (ngrok e afins).
    r"\bmanage\.py runserver\b", r"\bfastapi (dev|run)\b", r"\bartisan serve\b",
    r"\bdeno (run|serve|task)\b.*\b--watch\b", r"\bbun run dev\b", r"\bcargo run\b",
    r"(?:^|\s)(?:\S*/)?air(?:\s|$)", r"\bjupyter (lab|notebook)\b", r"\bstreamlit run\b",
    r"\btailwindcss\b.*\b--watch\b", r"\bngrok\b", r"\bcloudflared tunnel\b",
    r"\blive-server\b", r"\bwrangler (dev|pages dev)\b",
    # Por stack: PHP embutido, Elixir/Phoenix, JVM em modo dev, .NET em watch,
    # Flutter/React Native rodando no simulador, e o metro bundler deles.
    r"\bphp -S\b", r"\bmix phx\.server\b", r"\bspring-boot:run\b",
    r"\bgradle\w* bootRun\b", r"\bdotnet (run|watch)\b",
    r"\bflutter run\b", r"\bexpo start\b", r"\breact-native start\b",
    # O dev-server do mundo React/TypeScript, framework a framework, mais os
    # executores de TS em watch e o worker de fila do Python.
    r"\breact-scripts start\b", r"\b(?:astro|remix|gatsby) (dev|develop)\b",
    r"\bwebpack(?:-dev-server| serve)\b",
    r"\bts-node-dev\b", r"\btsx watch\b", r"\bdocusaurus start\b",
    r"\bcelery\b.*\bworker\b", r"\bhypercorn\b", r"\bsanic\b",
    # Tauri em desenvolvimento (o `tauri dev` cobre `cargo tauri dev` e o do npm),
    # Electron de projeto, e o `npx serve` de pasta estática.
    r"\btauri dev\b", r"\belectron\b(?!.*Helper)", r"\bnpx serve\b",
    # Geradores de site estático servindo, executores em watch, backends que
    # faltavam, workers de fila, port-forward (mesma família do ssh -L), e os
    # emuladores de nuvem locais — tudo descartável de desenvolvimento.
    r"\bnuxt (dev|start)\b", r"\bember serve\b", r"\beleventy\b.*\b--serve\b",
    r"\bhugo server\b", r"\bjekyll serve\b", r"\bbrowser-sync\b", r"\bmkdocs serve\b",
    r"\bcargo watch\b", r"\bwatchexec\b", r"\bbun\b.*\b--watch\b",
    r"\bdaphne\b", r"\bpuma\b", r"(?:^|\s)(?:\S*/)?go run(?:\s|$)",
    r"\bsidekiq\b", r"\brq worker\b",
    r"\bkubectl port-forward\b", r"\blocaltunnel\b",
    r"\bgradio\b", r"\bmarimo (edit|run)\b", r"\bvoila\b",
    r"\bfirebase emulators\b", r"\bvercel dev\b", r"\bnetlify dev\b",
    r"\bstripe listen\b", r"\bmailpit\b", r"\bazurite\b",
]
# Máquina virtual, serviço de contêiner e o que o próprio harness mantém de pé.
# A decisão de 2026-08-05 foi explícita: o lixeiro NUNCA encosta nestes — reporta.
INTOCAVEL = [
    r"\blimactl\b", r"\bqemu", r"\bcolima\b", r"\bdocker\b", r"\bcontainerd\b",
    r"\bDocker Desktop\b", r"\bollama\b",
    # Banco de dados e fila nativos (fora de contêiner) guardam estado: matar no
    # meio de uma escrita corrompe. `postgres` pega também os workers forkados.
    # `UTM` ficou de fora de propósito: com re.I casaria o `utm_source` de
    # qualquer URL; o app entra pelo caminho `UTM.app`.
    r"\bpostgres\b", r"\bmysqld\b", r"\bmariadbd\b", r"\bmongod\b", r"\bredis-server\b",
    r"\belasticsearch\b", r"\bopensearch\b", r"\bkafka\b", r"\bzookeeper\b",
    r"\brabbitmq\b", r"\bnats-server\b", r"\betcd\b", r"\bclickhouse\b",
    r"\binfluxd\b", r"\bmeilisearch\b", r"\btypesense\b", r"\bminio\b", r"\bmemcached\b",
    r"\bminikube\b", r"\bpodman\b", r"(?:^|\s)kind(?:\s|$)",
    r"\bOrbStack\b", r"\borbstack\b", r"\bvagrant\b", r"UTM\.app",
    # LLM local segura modelo carregado na memória: recarregar custa minutos.
    r"\bllama-server\b", r"\bLM Studio\b",
    # Simulador iOS/Android de pé: derrubar perde o estado do app instalado.
    r"Simulator\.app", r"\bemulator\b.*\B-avd\b",
    # O PROGRAMA claude, não o diretório de configuração dele: `~/.claude/…`
    # aparece em TODO comando que o harness lança (snapshot de shell, arquivo de
    # cwd), e `\bclaude\b` casava nesse caminho — o que tornava intocável tudo
    # que a sessão abria. Só conta quando `claude` é o token executável.
    r"(?:^|\s)(?:\S*/)?claude(?:\s|$)",
    r"\bbg-pty-host\b", r"\bbg-spare\b", r"\bcc-daemon\b",
    r"\bvisual_server\.mjs\b", r"\bnode_modules/\.bin/claude\b",
]

CLASSES = (("efemero", EFEMERO), ("servico", SERVICO))

# Quanto tempo de relógio um processo precisa passar SEM gastar CPU para o fim do
# turno o considerar abandonado. Não é uma constante de gosto: abaixo disso a
# colheita confunde a suíte que espera o banco de dados subir com a que travou.
# Ajustável porque uma suíte não pode levar dois minutos para provar a colheita.
try:
    OCIOSO_MIN = int(os.environ.get("LIXEIRO_OCIOSO_MIN") or 120)
except ValueError:
    OCIOSO_MIN = 120
# Quanto tempo separa as duas leituras de CPU do fim de sessão. Precisa ser longo
# o bastante para uma suíte trabalhando aparecer, e curto o bastante para não
# atrasar o fechamento da sessão.
OCIOSO_ESPERA = 1.5


@functools.lru_cache(maxsize=8192)
def classifica(cmd):
    """Devolve 'efemero', 'servico', 'intocavel' ou None. Intocável vence tudo.

    'intocavel' é CLASSIFICAÇÃO, não autorização: reconhecer o `docker compose up`
    serve para ele constar com procedência no relatório. Quem recusa o sinal é
    `eh_intocavel`, consultado em `casa`, no `inventario` e no `encerra` — e essa
    recusa não muda aqui.

    Memoizada porque o inventário a chama uma vez por (anotação × processo) — com
    dezenas de sessões anotadas isso passa de um milhão de chamadas, cada uma
    varrendo as três listas de padrões. O resultado depende só do texto, então o
    cache é seguro: mesmo comando, mesma classe, sempre."""
    for pat in INTOCAVEL:
        if re.search(pat, cmd, re.I):
            return "intocavel"
    for nome, pats in CLASSES:
        for pat in pats:
            if re.search(pat, cmd, re.I):
                return nome
    return None


@functools.lru_cache(maxsize=8192)
def eh_intocavel(cmd):
    return any(re.search(p, cmd, re.I) for p in INTOCAVEL)


@functools.lru_cache(maxsize=4096)
def _real(caminho):
    """`os.path.realpath` memoizado. Ele toca o disco a cada chamada, e `casa` o
    invoca duas vezes por par (anotação × processo) — era o custo mais caro do
    laço, acima até das expressões regulares."""
    return os.path.realpath(caminho)


# ── ler a tabela de processos ───────────────────────────────────────────────
def _seg_etime(s):
    """[[DD-]HH:]MM:SS -> segundos. Formato POSIX do ps, igual em macOS e Linux."""
    dias = 0
    if "-" in s:
        d, s = s.split("-", 1)
        dias = int(d)
    partes = [int(x) for x in s.split(":")]
    while len(partes) < 3:
        partes.insert(0, 0)
    h, m, seg = partes
    return dias * 86400 + h * 3600 + m * 60 + seg


def _seg_cputime(s):
    """[HH:]MM:SS[.cc] -> segundos (float). O tempo de CPU já consumido."""
    partes = s.split(":")
    try:
        partes = [float(x) for x in partes]
    except ValueError:
        return 0.0
    while len(partes) < 3:
        partes.insert(0, 0.0)
    return partes[0] * 3600 + partes[1] * 60 + partes[2]


# A enumeração nativa do Windows, num comando só. O `ps` que existe lá é o do
# Git Bash: ele ignora `-eo` e devolve o formato fixo dele, com pid MSYS que não
# é o pid do sistema — parseá-lo como POSIX leria PGID como etime e WINPID como
# time (provado na sonda probe/windows-cwd, run 31958904558). `Get-CimInstance`
# devolve tudo que o motor usa, já em pid nativo, que é o que `os.kill` aceita.
_PS1_ENUM = (
    "Get-CimInstance Win32_Process | ForEach-Object { "
    "$idade = 0; if ($_.CreationDate) { $idade = [int](((Get-Date) - $_.CreationDate).TotalSeconds) }; "
    "$cpu = [int](($_.UserModeTime + $_.KernelModeTime) / 1e7); "
    "$rss = [int]($_.WorkingSetSize / 1024); "
    "Write-Output ($_.ProcessId.ToString() + '|' + $_.ParentProcessId + '|' + "
    "$idade + '|' + $cpu + '|' + $rss + '|' + $_.CommandLine) }"
)


def _processos_nt():
    """`processos()` do Windows, via PowerShell (sempre presente). CPU em segundos
    INTEIROS — o bastante para o discriminador de ocioso (0,05s de folga), e imune
    ao separador decimal da localidade, que em pt-BR imprimiria `1,5`."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS1_ENUM],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    procs = []
    for linha in out.stdout.splitlines():
        campos = linha.split("|", 5)
        if len(campos) < 6:
            continue
        pid, ppid, idade, cpu, rss, cmd = campos
        try:
            procs.append({
                "pid": int(pid), "ppid": int(ppid),
                "idade": int(idade), "cpu": float(cpu),
                "rss": int(rss), "cmd": cmd.strip(),
            })
        except ValueError:
            continue
    return procs


def processos():
    """Lista de dicts {pid, ppid, idade, cpu, rss, cmd}. Lista vazia = não sei ler,
    e não saber ler significa não encerrar nada (fail-safe, não fail-open cego)."""
    if os.name == "nt":
        return _processos_nt()
    try:
        out = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,etime=,time=,rss=,args="],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10,
            stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    procs = []
    for linha in out.stdout.splitlines():
        campos = linha.split(None, 5)
        if len(campos) < 6:
            continue
        pid, ppid, etime, cputime, rss, cmd = campos
        try:
            procs.append({
                "pid": int(pid), "ppid": int(ppid),
                "idade": _seg_etime(etime), "cpu": _seg_cputime(cputime),
                "rss": int(rss), "cmd": cmd.strip(),
            })
        except ValueError:
            continue
    return procs


_PS_CACHE = {}
_PS_LIDO = False
_PS_OK = False


def _tabela_ps():
    """`stat` e `tty` de TODOS os processos numa chamada só.

    Mesma medida do `_carrega_cwds`, pelo mesmo motivo: `vivo()` e
    `_sem_terminal()` chamavam `ps -p <pid>` uma vez por processo, com teto de
    5s cada. Numa varredura de centenas de processos isso é o que fazia o
    `resumo` demorar minutos. Um `ps -eo` cobre a máquina inteira.

    O cache é uma FOTO do instante da leitura: `invalida_ps()` a descarta, e
    quem precisa de leitura fresca (a colheita, entre um sinal e o próximo)
    chama isso antes de perguntar de novo."""
    global _PS_LIDO, _PS_OK
    _PS_LIDO = True
    # No Windows o `ps` do Git Bash ignora `-eo` e sai com rc=0 no formato dele:
    # a tabela nasceria de pids MSYS, que não são os pids que o motor usa. Cache
    # vazio, mas a leitura é BOA: lá não existe terminal de controle, e "nenhum
    # processo tem tty" é RESPOSTA, não ignorância. Sem o `_PS_OK`, `_sem_terminal`
    # respondia "tem terminal" para todo mundo e a varredura do inventário parava
    # de apontar suspeito e órfão no Windows inteiro (8 casos da suíte, run
    # 32325412887) — foi este o defeito que e13a850 introduziu.
    if os.name == "nt":
        _PS_OK = True
        return
    try:
        out = subprocess.run(["ps", "-eo", "pid=,stat=,tty="],
                             capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=15, stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return
    _PS_OK = True
    for linha in out.stdout.splitlines():
        campos = linha.split()
        if len(campos) < 2:
            continue
        try:
            _PS_CACHE[int(campos[0])] = (campos[1], campos[2] if len(campos) > 2 else "")
        except ValueError:
            continue


def invalida_ps():
    """Descarta a foto do `ps`. Chame entre dois momentos em que o estado do
    processo pode ter mudado — encerrar e conferir se morreu, por exemplo."""
    global _PS_LIDO, _PS_OK
    _PS_LIDO = False
    _PS_OK = False
    _PS_CACHE.clear()


def _ps_de(pid):
    if not _PS_LIDO:
        _tabela_ps()
    return _PS_CACHE.get(pid)


def _vivo_nt(pid):
    """`vivo()` do Windows. `os.kill(pid, 0)` lá NÃO é sonda: qualquer sinal fora
    dos dois CTRL_* vira TerminateProcess — perguntar "está vivo?" MATARIA o
    processo. A pergunta certa é abrir o handle e ESPERAR ZERO SEGUNDO por ele:
    o encerramento no Windows é assíncrono, e o código de saída já aparece
    enquanto as threads ainda estão saindo — quem só lê o código responde
    "morreu" antes de o processo cair. O handle só é sinalizado no fim de
    verdade."""
    import ctypes
    try:
        k32 = ctypes.windll.kernel32
    except AttributeError:
        return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x00100000
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, int(pid))
    if not h:
        return k32.GetLastError() == 5   # acesso negado: existe, só não é nosso
    try:
        # Quem responde é a ESPERA DE ZERO SEGUNDO, não o código de saída.
        # `TerminateProcess` é assíncrono: o código de saída já aparece enquanto as
        # threads ainda estão saindo, e `GetExitCodeProcess` dizia "morreu" cedo
        # demais — `encerra()` voltava "TERM" e o `Popen.poll()` de quem esperava
        # ainda devolvia None, ou seja, o processo NÃO tinha caído (medido no
        # runner: `encerra -> 'TERM' em 0.6s` com `poll=None`, run 32326254747).
        # O objeto do processo só é sinalizado quando ele acabou de verdade.
        return k32.WaitForSingleObject(h, 0) != 0   # 0 = WAIT_OBJECT_0 = terminou
    finally:
        k32.CloseHandle(h)


def vivo(pid):
    """Vive de verdade? Processo já encerrado mas ainda não colhido pelo pai
    (estado Z) responde ao sinal 0 como se estivesse vivo — e isso faria a
    colheita concluir que o encerramento falhou, e escalar para o sinal forte
    à toa. Por isso o zumbi conta como morto."""
    if os.name == "nt":
        return _vivo_nt(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    dados = _ps_de(pid)
    if dados and dados[0].startswith("Z"):
        return False
    return True


def _cadeia(pid, procs):
    """A linhagem do pid, do mais próximo ao mais distante: [ele, pai, avô, …]."""
    por_pid = {p["pid"]: p for p in procs}
    ordem, atual, guarda = [], pid, 0
    while atual and atual > 1 and guarda < 64:
        if atual not in ordem:
            ordem.append(atual)
        p = por_pid.get(atual)
        if not p:
            break
        atual = p["ppid"]
        guarda += 1
    if pid not in ordem:
        ordem.insert(0, pid)
    return ordem


def ancestrais(pid, procs):
    """Cadeia de pais do pid. É o que impede o mecanismo de se matar: nada que
    esteja acima do próprio hook na árvore pode receber sinal."""
    return set(_cadeia(pid, procs))


def peso_arvore(procs, campo="rss"):
    """pid -> valor do processo MAIS o de toda a descendência dele.

    Com `rss`: memória em KB. O pai costuma ser um lançador de 5 MB que segura
    gigabytes de filhos, e quem olha só o RSS dele não vê o peso que encerrá-lo
    devolve à máquina.

    Com `cpu`: o trabalho que a ÁRVORE fez, em segundos. É esse o número que diz
    se uma suíte está trabalhando — quem lança (`cargo`, `npm exec`, o `zsh -c`
    que o harness usa) fica parado esperando enquanto o filho queima CPU, e olhar
    só o lançador o faz parecer ocioso quando a suíte está a todo vapor."""
    total = {p["pid"]: p[campo] for p in procs}
    por_pid = {p["pid"]: p for p in procs}
    for p in procs:
        visto = {p["pid"]}
        atual, guarda = p["ppid"], 0
        while atual and atual > 1 and atual not in visto and guarda < 64:
            visto.add(atual)
            if atual not in total:
                break
            total[atual] += p[campo]
            pai = por_pid.get(atual)
            if not pai:
                break
            atual = pai["ppid"]
            guarda += 1
    return total


# ── o registro ──────────────────────────────────────────────────────────────
def le_registro(session_id):
    p = registro_path(session_id)
    if not os.path.exists(p):
        return {"session_id": session_id, "dono_pid": None, "anotacoes": []}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"session_id": session_id, "dono_pid": None, "anotacoes": []}


def grava_registro(reg):
    p = registro_path(reg.get("session_id"))
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(reg, fh, ensure_ascii=False)
    os.replace(tmp, p)


def sessao_dona(harness_pid, procs=None):
    """A sessão que MANDOU abrir, quando quem abriu foi um agente de bancada.

    O agente que um workflow solta tem sessão própria — e, com ela, registro
    próprio, que a sessão que o soltou nunca consulta: o servidor que ele sobe
    fica de pé sem constar em inventário nenhum. Mas o processo dele nasce
    DENTRO do processo da sessão que o soltou. Quando o `dono_pid` de outro
    registro é ancestral ESTRITO do harness deste agente, o trabalho é daquela
    sessão, e é lá que a anotação tem que morar.

    Devolve o session_id da dona mais próxima, ou None — e None significa
    deixar a anotação onde nasceu. Não saber de quem é o trabalho nunca pode
    mudar o dono dele.
    """
    if not harness_pid:
        return None
    procs = processos() if procs is None else procs
    if not procs:
        return None
    try:
        acima = _cadeia(int(harness_pid), procs)[1:]
    except (TypeError, ValueError):
        return None
    if not acima:
        return None
    melhor = None
    for nome in os.listdir(state_dir()):
        if not nome.startswith("sessao-") or not nome.endswith(".json"):
            continue
        reg = le_registro(nome[7:-5])
        dono = reg.get("dono_pid")
        if not dono:
            continue
        try:
            i = acima.index(int(dono))
        except ValueError:
            continue
        if melhor is None or i < melhor[0]:
            melhor = (i, reg.get("session_id") or nome[7:-5])
    return melhor[1] if melhor else None


def anota(session_id, comando, cwd, dono_pid=None):
    """Registra que ESTE comando pode ter aberto processo. Devolve a classe, ou
    None quando o comando não é abridor (e aí nada é gravado)."""
    classe = classifica(comando or "")
    if not classe:
        return None
    # Agente de bancada: a anotação vai para o registro de quem o soltou, senão
    # ela nasce num registro que morre com o agente e ninguém colhe.
    agente = None
    dona = sessao_dona(dono_pid)
    if dona and dona != session_id:
        agente, session_id = session_id, dona
    reg = le_registro(session_id)
    if dono_pid and not agente:
        reg["dono_pid"] = int(dono_pid)
    entrada = {
        "cmd": (comando or "")[:400],
        "cwd": cwd or "",
        "classe": classe,
        "em": time.time(),
        "cpu_ultimo_turno": None,
    }
    if agente:
        entrada["agente"] = agente
    reg.setdefault("anotacoes", []).append(entrada)
    # Teto: registro não é histórico, é lista de pendências. 200 é folgado para
    # uma sessão longa e impede o arquivo crescer sem fim.
    reg["anotacoes"] = reg["anotacoes"][-200:]
    grava_registro(reg)
    return classe


# ── casar anotação com processo vivo ────────────────────────────────────────
_TOKEN = re.compile(r"[A-Za-z0-9_./@-]+")


def _marcas(cmd):
    """Tokens que identificam o comando: caminho de projeto, nome de binário,
    porta. Descarta o ruído de shell (aspas, redireção, flags soltas)."""
    brutos = _TOKEN.findall(cmd or "")
    marcas = set()
    for t in brutos:
        if len(t) < 3 or t.startswith("-"):
            continue
        if t in ("bash", "sh", "zsh", "-c", "cd", "&&", "npx", "run", "exec", "the"):
            continue
        marcas.add(t.rstrip("/"))
    return marcas


_CWD_CACHE = {}
_CWD_TODOS = False


def _carrega_cwds():
    """UMA chamada de `lsof` para a máquina inteira, em vez de uma por processo.

    Medido em 2026-08-13: a varredura chamava `lsof -p <pid>` em série, com teto
    de 5s CADA. Numa máquina com centenas de processos vivos isso é centenas de
    chamadas enfileiradas — e processo dormindo em chamada de sistema (o caso
    dos `rustc` no funil do `syspolicyd`) é justamente o que faz `lsof` esperar
    o teto inteiro. O `resumo` levava minutos e parecia travado.

    `-Fpn` imprime blocos `p<pid>` seguidos de `n<caminho>`; sem `-p` ele cobre
    todos os processos de uma vez. Falha ou ausência do `lsof` deixa o cache
    vazio, e cada consulta cai no caminho antigo — degrada, não quebra."""
    global _CWD_TODOS
    _CWD_TODOS = True
    if os.name == "nt":     # sem lsof lá; `cwd_de` tem caminho próprio, por pid
        return
    try:
        out = subprocess.run(["lsof", "-d", "cwd", "-Fpn"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=20, stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return
    atual = None
    for linha in out.stdout.splitlines():
        if linha.startswith("p"):
            try:
                atual = int(linha[1:])
            except ValueError:
                atual = None
        elif linha.startswith("n/") and atual is not None:
            _CWD_CACHE.setdefault(atual, linha[1:])


def _cwd_nt(pid):
    """Pasta de trabalho no Windows, lida do PEB do próprio processo — não há
    `lsof` lá, e nem `wmic` nem `tasklist` devolvem cwd. O caminho foi provado
    com dado real de um runner (sonda probe/windows-cwd, run 31958835356):
    NtQueryInformationProcess dá o PEB; PEB+0x20 aponta os ProcessParameters;
    +0x38 é CurrentDirectory.DosPath (UNICODE_STRING). Offsets de x64 — noutra
    arquitetura devolve None, e não saber a pasta protege o processo.
    Sai normalizado (`C:/…`, sem barra final), a forma que a anotação usa."""
    import ctypes
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        return None
    try:
        k32 = ctypes.windll.kernel32
        ntdll = ctypes.windll.ntdll
    except AttributeError:
        return None
    h = k32.OpenProcess(0x0410, False, int(pid))  # QUERY_INFORMATION | VM_READ
    if not h:
        return None
    try:
        class _PBI(ctypes.Structure):
            _fields_ = [("ExitStatus", ctypes.c_void_p),
                        ("PebBaseAddress", ctypes.c_void_p),
                        ("AffinityMask", ctypes.c_void_p),
                        ("BasePriority", ctypes.c_void_p),
                        ("UniqueProcessId", ctypes.c_void_p),
                        ("InheritedFromUniqueProcessId", ctypes.c_void_p)]
        pbi = _PBI()
        devolvido = ctypes.c_ulong()
        if ntdll.NtQueryInformationProcess(h, 0, ctypes.byref(pbi),
                                           ctypes.sizeof(pbi), ctypes.byref(devolvido)) != 0:
            return None
        if not pbi.PebBaseAddress:
            return None

        def ler(addr, tam):
            buf = ctypes.create_string_buffer(tam)
            lidos = ctypes.c_size_t()
            if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, tam,
                                         ctypes.byref(lidos)):
                return None
            return buf.raw

        ptr_pp = ler(pbi.PebBaseAddress + 0x20, 8)
        if not ptr_pp:
            return None
        pp = int.from_bytes(ptr_pp, "little")
        us = ler(pp + 0x38, 16)
        if not us:
            return None
        tam = int.from_bytes(us[0:2], "little")
        ptr = int.from_bytes(us[8:16], "little")
        if not ptr or not tam:
            return None
        bruto = ler(ptr, min(tam, 4096))
        if not bruto:
            return None
        return bruto.decode("utf-16-le", "replace").replace("\\", "/").rstrip("/")
    finally:
        k32.CloseHandle(h)


def cwd_de(pid):
    """Pasta de trabalho do processo. É a prova mais forte de que ele pertence ao
    projeto anotado — mais forte que o texto do comando, que muitas vezes não
    carrega o caminho (`next-server (v16.2.11)` é o exemplo desta máquina).
    Sem `lsof`, devolve None e o casamento cai para o texto do comando.
    No Windows a fonte é outra (`_cwd_nt`), mas o contrato é o mesmo."""
    if os.name == "nt":
        if pid not in _CWD_CACHE:
            try:
                _CWD_CACHE[pid] = _cwd_nt(pid)
            except OSError:
                _CWD_CACHE[pid] = None
        return _CWD_CACHE[pid]
    if not _CWD_TODOS:
        _carrega_cwds()
    if pid in _CWD_CACHE:
        return _CWD_CACHE[pid]
    val = None
    try:
        out = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5, stdin=subprocess.DEVNULL, start_new_session=True)
        for linha in out.stdout.splitlines():
            if linha.startswith("n/"):
                val = linha[1:]
    except (OSError, subprocess.SubprocessError):
        val = None
    _CWD_CACHE[pid] = val
    return val


# O rascunho que o harness dá a cada sessão: uma pasta em /tmp cujo nome é o id
# da sessão. Quem trabalha lá dentro está, por construção, trabalhando PARA
# aquela sessão — e isso vale como procedência sem nenhuma anotação. Exige a
# forma do id (uuid) para não confundir com qualquer pasta chamada `scratchpad`.
_RASCUNHO_DE_SESSAO = re.compile(
    r"/claude-[^/]+/[^/]+/([0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12})/scratchpad(?:/|$)")
# O PROGRAMA claude na linha de comando (o mesmo critério do intocável): é o que
# prova que a sessão dona do rascunho ainda está de pé.
_PROGRAMA_CLAUDE = re.compile(r"(?:^|\s)(?:\S*/)?claude(?:\s|$)")


def sessao_do_rascunho(caminho):
    """O id da sessão dona do rascunho, lido do próprio caminho, ou None."""
    m = _RASCUNHO_DE_SESSAO.search(caminho or "")
    return m.group(1) if m else None


def _sessao_existe(sid, pid, procs):
    """A sessão dona do rascunho ainda está de pé? Duas provas, e basta UMA —
    a dúvida sempre protege o processo. (1) o registro dela tem dono vivo;
    (2) o processo nasceu dentro de um `claude` que ainda vive — necessária
    porque o registro só passa a existir na primeira anotação, e sessão que
    ainda não anotou nada não pode ser dada por morta."""
    dono = le_registro(sid).get("dono_pid")
    try:
        if dono and vivo(int(dono)):
            return True
    except (TypeError, ValueError):
        pass
    por_pid = {p["pid"]: p for p in procs}
    for acima in _cadeia(pid, procs)[1:]:
        p = por_pid.get(acima)
        if p and _PROGRAMA_CLAUDE.search(p["cmd"]):
            return True
    return False


def orfao_de_rascunho(pid, procs):
    """O processo trabalha no rascunho de uma sessão que não existe mais? Devolve
    o id daquela sessão — procedência suficiente por si só, sem anotação nenhuma:
    o servidor que ficou de pé lá dentro não tem mais a quem servir."""
    sid = sessao_do_rascunho(cwd_de(pid))
    if not sid or _sessao_existe(sid, pid, procs):
        return None
    return sid


def _sob(caminho, raiz):
    """O caminho está dentro da raiz? Compara as DUAS formas de cada um, porque
    no macOS `/var/folders/...` e `/private/var/folders/...` são a mesma pasta e
    chegam por vias diferentes: a anotação traz o caminho como o shell o viu, e
    o `lsof` devolve o resolvido. Sem isto, nenhum processo em pasta temporária
    casa a própria anotação — e a colheita nunca acontece."""
    if not caminho or not raiz:
        return False
    if os.name == "nt":
        # NTFS não distingue caixa, e `C:\…` e `C:/…` são a mesma pasta.
        caminho = caminho.replace("\\", "/").lower()
        raiz = raiz.replace("\\", "/").lower()
    formas_raiz = {raiz.rstrip("/"), _real(raiz).rstrip("/")}
    formas_cam = {caminho.rstrip("/"), _real(caminho).rstrip("/")}
    for r in formas_raiz:
        for c in formas_cam:
            if c == r or c.startswith(r + "/"):
                return True
    return False


def casa(anotacao, proc):
    """O processo veio desta anotação? Exige TRÊS coincidências, não uma:
      (1) a classe do comando dele é a mesma da anotação;
      (2) nasceu DEPOIS da anotação — idade menor que o tempo desde ela;
      (3) pertence ao MESMO projeto — a pasta anotada aparece no comando dele,
          ou a pasta de trabalho real dele está sob ela.

    A terceira é a que impede o falso positivo que importa. Sem ela, `pytest` e
    `tests` bastariam para uma anotação de um projeto casar a suíte de outro —
    e foi exatamente o que a suíte pegou quando o critério era só tokens comuns.
    Anotação sem pasta e processo sem caminho no comando: NÃO casa (não saber
    de quem é o processo tem que significar deixá-lo vivo)."""
    if eh_intocavel(proc["cmd"]):
        return False
    if classifica(proc["cmd"]) != anotacao.get("classe"):
        return False
    desde = time.time() - anotacao.get("em", 0)
    # 30s de folga para o relógio e para o processo que demora a subir
    if proc["idade"] > desde + 30:
        return False

    raiz = (anotacao.get("cwd") or "").rstrip("/")
    if raiz:
        # As duas formas do caminho, pelo mesmo motivo de `_sob`
        if raiz in proc["cmd"] or _real(raiz).rstrip("/") in proc["cmd"]:
            return True
        real = cwd_de(proc["pid"])
        if real and _sob(real, raiz):
            return True
        # A pasta é conhecida e o processo não é dela: decisão fechada, sem
        # cair para heurística de token (que foi o que produziu o falso positivo).
        return False

    # Sem pasta anotada, sobra o texto: exige marca forte (caminho ou arquivo)
    # em comum, nunca palavra genérica como `tests` ou `pytest`.
    comuns = _marcas(anotacao.get("cmd", "")) & _marcas(proc["cmd"])
    return any(("/" in c or "." in c) for c in comuns)


# ── decidir e encerrar ──────────────────────────────────────────────────────
def candidatos(session_id, modo, procs=None, agora=None):
    """Devolve [(anotacao, proc, motivo)] do que PODE ser encerrado neste modo.

    modo 'turno'   — só o que NÃO trabalhou desde o turno anterior, suíte ou servidor
    modo 'sessao'  — tudo que a sessão anotou e ainda vive (quem está trabalhando
                     é poupado depois, em `colhe`, que mede a CPU ao vivo)

    A regra do turno é uma só, e vale igual para as duas classes: morre quem tem
    foto de CPU do turno anterior e não gastou CPU nenhuma desde então. Ela nasceu
    de um estrago real — enquanto "efêmero vivo era lixo certo", uma suíte lançada
    em segundo plano morria no fim do MESMO turno (medido: `cargo test` encerrado
    6 segundos depois de começar), porque o fim do turno é justamente quando o
    agente estaciona o trabalho longo para continuar conversando. Ocioso é a única
    prova de abandono que não confunde trabalho em curso com lixo.

    E ocioso se mede em TEMPO DE RELÓGIO, não em turnos: dois turnos podem estar a
    três segundos um do outro (o usuário digita "ok" e o agente devolve), e "não
    gastou CPU desde o turno anterior" viraria "não gastou CPU em três segundos" —
    o que mata a suíte parada esperando o banco subir. Por isso o que conta é a
    última vez que ele foi visto TRABALHANDO, e ela precisa ter no mínimo
    OCIOSO_MIN segundos.
    """
    agora = time.time() if agora is None else agora
    procs = processos() if procs is None else procs
    if not procs:
        return []
    reg = le_registro(session_id)
    eu = ancestrais(os.getpid(), procs)
    cpu_arvore = peso_arvore(procs, "cpu")
    achados = []
    for anot in reg.get("anotacoes", []):
        # Anotação de intocável existe para relatar, nunca para colher. `casa` já
        # barra o processo intocável; isto barra a anotação, para que a classe
        # nova não dependa de uma trava só.
        if anot.get("classe") == "intocavel":
            continue
        for p in procs:
            if p["pid"] in eu:
                continue                      # trava de suicídio
            if not casa(anot, p):
                continue
            if modo == "sessao":
                achados.append((anot, p, "fim de sessão"))
                continue
            antes = anot.get("cpu_ultimo_turno")
            # Comparar CPU só faz sentido entre leituras do MESMO processo. Uma
            # anotação casa mais de um processo ao longo da sessão (a suíte roda
            # de novo, o servidor reinicia), e o segundo nasce com a CPU zerada:
            # sem esta linha ele seria lido como "o primeiro, que parou de
            # trabalhar" — e morreria no meio do serviço.
            if antes is None or anot.get("cpu_pid") != p["pid"]:
                continue
            if cpu_arvore.get(p["pid"], p["cpu"]) > antes + 0.5:
                continue
            if p["idade"] <= OCIOSO_MIN:
                continue
            visto = anot.get("cpu_visto_em")
            if visto is None or agora - visto <= OCIOSO_MIN:
                continue
            achados.append((anot, p, "suíte parada desde o turno anterior"
                            if anot.get("classe") == "efemero"
                            else "servidor sem uso desde o turno anterior"))
    return achados


def marca_cpu(session_id, procs=None, agora=None):
    """Anota a última vez que cada processo anotado foi visto TRABALHANDO — o
    tempo de CPU da ÁRVORE dele, e o instante da leitura. É o que, no turno
    seguinte, distingue o que está em uso do que foi esquecido: sem isso o fim de
    turno derrubaria o servidor que o próximo turno ia usar, e a suíte que ainda
    estava rodando.

    A foto só se RENOVA quando a CPU subiu. Renovar a cada turno, sem olhar,
    zeraria o relógio do ocioso a cada troca de mensagem — e numa conversa de
    turnos curtos nada nunca completaria os OCIOSO_MIN segundos parados, isto é,
    o lixo de verdade jamais seria colhido.

    E cada processo é fotografado por UMA anotação só. Duas suítes do mesmo
    projeto casam as duas anotações, e sem esta regra ambas fotografavam o
    primeiro processo — a segunda ficava eternamente sem foto própria, e o que ela
    abriu nunca era colhido. Quem já tem foto reivindica o seu processo primeiro,
    para a correspondência não trocar de dono a cada turno."""
    agora = time.time() if agora is None else agora
    procs = processos() if procs is None else procs
    if not procs:
        return
    cpu_arvore = peso_arvore(procs, "cpu")
    reg = le_registro(session_id)
    anotacoes = reg.get("anotacoes", [])
    tomados, par, mudou = set(), {}, False
    # 1ª volta: quem já tinha foto fica com o mesmo processo, se ele ainda casa.
    # 2ª volta: o resto pega o primeiro processo que sobrou.
    for reivindica in (True, False):
        for i, anot in enumerate(anotacoes):
            if i in par:
                continue
            for p in procs:
                if p["pid"] in tomados or not casa(anot, p):
                    continue
                if reivindica and anot.get("cpu_pid") != p["pid"]:
                    continue
                par[i] = p
                tomados.add(p["pid"])
                break
    for i, p in par.items():
        anot = anotacoes[i]
        agora_cpu = cpu_arvore.get(p["pid"], p["cpu"])
        antes = anot.get("cpu_ultimo_turno")
        trocou = anot.get("cpu_pid") != p["pid"]
        if antes is None or trocou or agora_cpu > antes + 0.5 or anot.get("cpu_visto_em") is None:
            anot["cpu_ultimo_turno"] = agora_cpu
            anot["cpu_visto_em"] = agora
            anot["cpu_pid"] = p["pid"]
            mudou = True
    if mudou:
        grava_registro(reg)


def trabalhando(pids, procs=None, espera=None):
    """Quais destes pids estão gastando CPU AGORA — duas leituras da árvore, com
    uma pausa no meio.

    É a única prova possível onde não existe foto do turno anterior para comparar:
    o fim de sessão, que pode chegar no meio do trabalho. A colheita de fim de
    sessão não discriminava nada, e por isso encerrava a suíte em andamento de
    quem só apertou /clear — a conversa foi descartada, a máquina não."""
    pids = set(pids)
    if not pids:
        return set()
    procs = processos() if procs is None else procs
    if not procs:
        return set()
    antes = peso_arvore(procs, "cpu")
    time.sleep(OCIOSO_ESPERA if espera is None else espera)
    depois = peso_arvore(processos(), "cpu")
    # 0,05s de CPU em 1,5s de relógio: ~3% de um núcleo. Suíte rodando passa disso
    # com folga; servidor parado esperando conexão, não.
    return {p for p in pids if depois.get(p, 0.0) > antes.get(p, 0.0) + 0.05}


def raiz_orfa(pid, procs=None, protegidos=None):
    """O topo da árvore a que o pid pertence, quando esse topo é ÓRFÃO — pai
    igual a 1 ou pai que nem consta na tabela. Senão, o próprio pid.

    Matar a folha não resolve: o lançador que continua de pé sobe outra no lugar
    (sete sinais na folha derrubaram setenta e oito processos e a árvore voltou).
    Quem cai é a raiz. A subida para ANTES de qualquer processo protegido — a
    trava de ancestral continua valendo, e nada acima do próprio motor recebe
    sinal — e antes de máquina virtual ou contêiner. E se a subida parou por uma
    dessas barreiras, a raiz encontrada não é órfã: aí o alvo volta a ser o pid
    original, para nunca sinalizar o pai vivo de outra árvore."""
    procs = processos() if procs is None else procs
    if not procs:
        return pid
    protegidos = ancestrais(os.getpid(), procs) if protegidos is None else protegidos
    por_pid = {p["pid"]: p for p in procs}
    if pid not in por_pid:
        return pid
    raiz, guarda = pid, 0
    while guarda < 64:
        guarda += 1
        ppid = por_pid[raiz]["ppid"]
        pai = por_pid.get(ppid)
        if ppid <= 1 or pai is None:
            return raiz          # chegou no topo: a raiz é órfã
        if ppid in protegidos or eh_intocavel(pai["cmd"]):
            break
        raiz = ppid
    return pid


def _descendentes(pid, procs):
    """Todo processo abaixo do pid na árvore."""
    filhos = {}
    for p in procs:
        filhos.setdefault(p["ppid"], []).append(p)
    fila, achados, vistos, guarda = [pid], [], {pid}, 0
    while fila and guarda < 4096:
        guarda += 1
        atual = fila.pop()
        for f in filhos.get(atual, []):
            if f["pid"] in vistos:
                continue
            vistos.add(f["pid"])
            achados.append(f)
            fila.append(f["pid"])
    return achados


def encerra(pid, grace=3.0, procs=None):
    """Pede para terminar a árvore do pid; só força quem ignorar. Devolve como
    a raiz morreu, ou None.

    O sinal vai para a RAIZ ÓRFÃ (ver `raiz_orfa`), e depois a descendência que
    sobreviveu é varrida uma a uma — matar o pai reparenta o filho para o init
    em vez de derrubá-lo, e o que sobra é exatamente o processo que ninguém mais
    reconhece. Intocável e protegido nunca recebem sinal, nem como descendente."""
    procs = processos() if procs is None else procs
    protegidos = ancestrais(os.getpid(), procs)
    alvo = raiz_orfa(pid, procs, protegidos)
    sinal = _sinaliza(alvo, grace)
    if sinal is None and alvo != pid:
        sinal = _sinaliza(pid, grace)
    for f in _descendentes(alvo, procs):
        if f["pid"] in protegidos or eh_intocavel(f["cmd"]):
            continue
        if vivo(f["pid"]):
            _sinaliza(f["pid"], grace)
    return sinal


def _sinaliza(pid, grace=3.0):
    """Pede para terminar; só força se ele ignorar. Devolve como morreu, ou None."""
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return None
    fim = time.time() + grace
    while time.time() < fim:
        # A foto do `ps` é do instante em que foi lida; aqui o estado MUDA a cada
        # volta, e ler o cache velho faria o zumbi passar por vivo para sempre.
        invalida_ps()
        if not vivo(pid):
            return "TERM"
        time.sleep(0.15)
    # O Windows não tem SIGKILL — `signal.SIGTERM` lá já é encerramento forçado
    # (TerminateProcess), então o segundo golpe é o mesmo sinal. Sem este getattr
    # o módulo INTEIRO morria de AttributeError no primeiro processo teimoso.
    try:
        os.kill(pid, getattr(signal, "SIGKILL", signal.SIGTERM))
    except (OSError, ProcessLookupError):
        return "TERM"
    time.sleep(0.2)
    invalida_ps()
    return "KILL" if not vivo(pid) else None


def registra_colheita(itens):
    if not itens:
        return
    try:
        with open(log_path(), "a", encoding="utf-8") as fh:
            for it in itens:
                fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    except OSError:
        pass


def colhe(session_id, modo, dry_run=False):
    """Encerra o que este modo autoriza. Devolve a lista do que morreu."""
    alvos = candidatos(session_id, modo)
    if modo == "sessao" and alvos:
        # No fim da sessão não há foto do turno anterior para consultar: mede-se
        # ao vivo. O que estiver trabalhando fica de pé, e a anotação dele
        # sobrevive — é a varredura de órfãos da abertura seguinte que termina o
        # serviço, quando aí sim não houver mais a quem servir.
        ocupados = trabalhando([p["pid"] for _, p, _ in alvos])
        alvos = [t for t in alvos if t[1]["pid"] not in ocupados]
    # Entre ler a tabela e mandar o sinal passa tempo — e no fim de sessão passa
    # mais, porque a medição ao vivo dorme no meio. Se o alvo morrer sozinho nesse
    # intervalo, o sistema pode ter dado o número dele a OUTRO processo, e o sinal
    # iria para um inocente. A releitura confirma que o pid ainda é quem era.
    # Sem alvo não há sinal a conferir — e este caminho roda a CADA fim de turno,
    # então a releitura só acontece quando vai haver disparo.
    agora_cmd = {} if (dry_run or not alvos) else {p["pid"]: p["cmd"] for p in processos()}
    mortos = []
    for anot, p, motivo in alvos:
        if dry_run:
            mortos.append({"pid": p["pid"], "cmd": p["cmd"], "rss_mb": round(p["rss"] / 1024),
                           "motivo": motivo, "sinal": "(simulado)"})
            continue
        if agora_cmd.get(p["pid"]) != p["cmd"]:
            continue
        sinal = encerra(p["pid"])
        if sinal:
            mortos.append({"pid": p["pid"], "cmd": p["cmd"][:300], "rss_mb": round(p["rss"] / 1024),
                           "motivo": motivo, "sinal": sinal, "sessao": session_id,
                           "em": time.strftime("%Y-%m-%dT%H:%M:%S")})
    if not dry_run:
        registra_colheita(mortos)
        _limpa_anotacoes_mortas(session_id)
    return mortos


def _limpa_anotacoes_mortas(session_id):
    """Anotação sem processo vivo correspondente não tem mais o que colher — mas
    só depois de DUAS rodadas sem casar. Não casar não é prova de que o processo
    não existe: o servidor pode estar subindo, o `lsof` pode ter falhado, a
    janela de idade pode ter escorregado. Como a coleta de fim de turno roda
    logo depois da anotação, descartar na primeira rodada apagava a procedência
    do processo que ainda ia aparecer — e sem procedência ele nunca mais seria
    candidato. A anotação sobrevive a uma rodada e some na seguinte."""
    procs = processos()
    if not procs:
        return
    reg = le_registro(session_id)
    antes = reg.get("anotacoes", [])
    vivas = []
    for a in antes:
        if any(casa(a, p) for p in procs):
            a["rodadas_sem_processo"] = 0
            vivas.append(a)
            continue
        a["rodadas_sem_processo"] = a.get("rodadas_sem_processo", 0) + 1
        if a["rodadas_sem_processo"] < 2:
            vivas.append(a)
    reg["anotacoes"] = vivas
    grava_registro(reg)


# ── órfãos: sessão que morreu sem colher ────────────────────────────────────
def sessoes_orfas():
    """Registros cujo dono (o processo da sessão) não responde mais."""
    orfas = []
    for nome in os.listdir(state_dir()):
        if not nome.startswith("sessao-") or not nome.endswith(".json"):
            continue
        try:
            with open(os.path.join(state_dir(), nome), encoding="utf-8") as fh:
                reg = json.load(fh)
        except (OSError, ValueError):
            continue
        dono = reg.get("dono_pid")
        if dono and vivo(int(dono)):
            continue
        if not reg.get("anotacoes"):
            continue
        orfas.append(reg.get("session_id") or nome[7:-5])
    return orfas


def colhe_orfaos(exceto=None, dry_run=False):
    mortos = []
    for sid in sessoes_orfas():
        if exceto and sid == exceto:
            continue
        mortos.extend(colhe(sid, "sessao", dry_run=dry_run))
        # Mesmo cuidado do fim de sessão: o registro só some quando não sobrou
        # processo de pé. O que foi poupado por estar trabalhando precisa
        # continuar tendo dono conhecido, senão nenhuma varredura futura o
        # reconhece. Anotação sem processo vivo não segura o arquivo — ela some
        # sozinha, pelo caminho normal.
        if not dry_run and not candidatos(sid, "sessao"):
            try:
                os.remove(registro_path(sid))
            except OSError:
                pass
    return mortos


# ── varredura: achar o que a anotação não viu ───────────────────────────────
# Onde mora binário de sistema e de aplicativo de janela. NÃO é critério de nome
# — é critério de LUGAR, e existe só para não gastar `lsof` com processo que
# nunca teve pasta de projeto (o navegador roda com a pasta em `/`). Nesta
# máquina isso corta 642 processos de longa vida para 66 candidatos a olhar.
_LUGAR_DE_SISTEMA = re.compile(r"^/(?:System|usr|bin|sbin|Library|Applications)/")


def _sem_terminal(pid):
    """Ninguém está olhando para ele? Processo com terminal de controle está
    preso a uma janela aberta — é o shell do usuário, ou o comando que ele está
    rodando à mão. Suspeito é o que ficou SOLTO. Não dá para responder (sem `ps`
    utilizável): trata como se tivesse terminal, porque a dúvida tem que
    proteger o processo, nunca acusá-lo."""
    dados = _ps_de(pid)
    if dados is None:
        # Pid fora da tabela com a leitura BOA é o mesmo caso do `ps -p <pid>`
        # que imprimia vazio: sem terminal. Leitura ruim (sem `ps` utilizável)
        # protege o processo, que é a regra escrita acima.
        return _PS_OK
    return dados[1] in ("??", "?", "-", "")


def _procedencia_minerada(procs):
    """O que os registros sabem, para a varredura reconstruir procedência sem
    depender da anotação: os pids das sessões MORTAS e as pastas que elas
    tocaram. Sessão viva fica de fora de propósito — o que ela subiu é trabalho
    em curso (o servidor de ferramenta que ela usa agora nasceu dentro dela e
    não tem anotação nenhuma), e trabalho em curso não é lixo."""
    donos, raizes = set(), set()
    for nome in os.listdir(state_dir()):
        if not nome.startswith("sessao-") or not nome.endswith(".json"):
            continue
        reg = le_registro(nome[7:-5])
        try:
            if reg.get("dono_pid") and not vivo(int(reg["dono_pid"])):
                donos.add(int(reg["dono_pid"]))
        except (TypeError, ValueError):
            pass
        for anot in reg.get("anotacoes", []):
            raiz = (anot.get("cwd") or "").rstrip("/")
            if raiz:
                raizes.add(raiz)
    return donos, raizes


def suspeitos(procs, anotados, eu, idade_min=3600):
    """Processo de longa vida que NENHUMA anotação explica — o que a anotação
    deixou passar. A anotação pega no pulo: comando que o harness não viu, filho
    que trocou de linha de comando, servidor que virou solto do pai. Para achá-lo
    sem cair no nome de programa (a regra que manda), a varredura exige PROVA de
    procedência minerada, uma das quatro:

      linhagem — ele nasceu dentro do processo de uma sessão que já MORREU;
      pasta    — a pasta de trabalho real dele está sob um projeto que alguma
                 sessão anotou ter tocado;
      órfão    — o pai dele sumiu (foi adotado pelo init, ou nem consta na tabela)
                 e o COMANDO dele carrega um projeto que a sessão anotou;
      rascunho — a pasta de trabalho dele está no rascunho de uma sessão que não
                 existe mais, e rascunho de sessão morta não tem mais a quem servir.

    A prova do órfão existe porque o processo velho de pai perdido não tem linhagem
    para consultar, e a pasta de trabalho dele nem sempre é legível — sem ela, o
    programa que ninguém reconhece some da lista em vez de aparecer, e some
    justamente o caso que interessa. Ele entra rotulado `sem classe conhecida`:
    a lista mostra que não se sabe o que é, em vez de esconder.

    Sem uma das quatro, o processo não entra: `ps` de longa vida sem filtro é a
    máquina inteira (765 processos aqui, com navegador, tocador de música e os
    serviços do sistema). E, com qualquer uma delas, ainda precisa estar sem
    terminal de controle — o que tem janela aberta atrás está sendo usado agora.
    Devolve [(proc, pista, classe)] — LISTA, nunca sinal: suspeito é assunto da
    faxina manual, onde quem decide é o usuário."""
    achados = []
    donos, raizes = _procedencia_minerada(procs)
    por_pid = {p["pid"]: p for p in procs}
    for p in procs:
        if p["pid"] in eu or p["pid"] in anotados or p["idade"] < idade_min:
            continue
        if classifica(p["cmd"]):
            continue          # tem classe: já entra no inventário com o nome dela
        acima = set(_cadeia(p["pid"], procs)[1:])
        if acima & donos and _sem_terminal(p["pid"]):
            achados.append((p, "nasceu dentro de uma sessão e nenhuma anotação o explica",
                            "suspeito"))
            continue
        exe = (p["cmd"].split() or [""])[0]
        if _LUGAR_DE_SISTEMA.match(exe):
            continue
        if orfao_de_rascunho(p["pid"], procs) and _sem_terminal(p["pid"]):
            achados.append((p, "trabalha no rascunho de uma sessão que não existe mais",
                            "sem classe conhecida"))
            continue
        if not raizes:
            continue
        real = cwd_de(p["pid"])
        if real and any(_sob(real, r) for r in raizes) and _sem_terminal(p["pid"]):
            achados.append((p, "trabalha dentro de um projeto que a sessão tocou", "suspeito"))
            continue
        # Pai perdido: adotado pelo init, ou pai que nem consta na tabela. Aqui a
        # prova de procedência é o texto do comando — mas só o caminho do projeto
        # anotado serve, nunca o nome do programa (a regra que manda).
        orfao = p["ppid"] <= 1 or p["ppid"] not in por_pid
        if orfao and _casa_raiz_no_texto(p["cmd"], raizes) and _sem_terminal(p["pid"]):
            achados.append((p, "o pai sumiu e o comando aponta para um projeto que a sessão tocou",
                            "sem classe conhecida"))
    return achados


def _casa_raiz_no_texto(cmd, raizes):
    """Alguma pasta anotada aparece no comando? As DUAS formas de cada raiz, pelo
    mesmo motivo de `_sob` (o `/private/var` do macOS)."""
    for r in raizes:
        if r and (r in cmd or _real(r).rstrip("/") in cmd):
            return True
    return False


# ── o inventário da faxina manual: TUDO, com ou sem procedência ─────────────
def inventario(idade_min=600, idade_suspeito=3600, procs=None):
    """Candidatos para a faxina manual. Aqui entra o que NÃO tem procedência —
    e por isso este caminho nunca encerra sozinho: só lista, o usuário escolhe."""
    procs = processos() if procs is None else procs
    if not procs:
        return []
    eu = ancestrais(os.getpid(), procs)
    arvore = peso_arvore(procs)
    # Só processo da MESMA classe da anotação pode casar (é a 1ª exigência de
    # `casa`), então o laço olha essa fatia em vez da máquina inteira. Sem isto
    # são (sessões × anotações × processos) chamadas — passou de um milhão nesta
    # máquina, e era o que fazia a faxina levar minutos.
    por_classe = {}
    for p in procs:
        por_classe.setdefault(classifica(p["cmd"]), []).append(p)
    anotados = set()
    for nome in os.listdir(state_dir()):
        if nome.startswith("sessao-") and nome.endswith(".json"):
            sid = nome[7:-5]
            for anot in le_registro(sid).get("anotacoes", []):
                for p in por_classe.get(anot.get("classe"), []):
                    if casa(anot, p):
                        anotados.add(p["pid"])
    itens = []
    for p in procs:
        if p["pid"] in eu or p["idade"] < idade_min:
            continue
        classe = classifica(p["cmd"])
        intocavel = eh_intocavel(p["cmd"])
        if not classe and not intocavel:
            continue
        # Quem tem classe mas nenhuma anotação ainda pode ter procedência: o
        # rascunho da sessão morta em que ele trabalha diz de quem ele era.
        if p["pid"] in anotados:
            procedencia = "anotado"
        elif orfao_de_rascunho(p["pid"], procs):
            procedencia = "órfão — rascunho de sessão que não existe mais"
        else:
            procedencia = "sem dono conhecido"
        itens.append({
            "pid": p["pid"], "cmd": p["cmd"][:300], "rss_mb": round(p["rss"] / 1024),
            "arvore_mb": round(arvore.get(p["pid"], p["rss"]) / 1024),
            "idade_min": round(p["idade"] / 60), "cpu_s": round(p["cpu"], 1),
            "classe": "intocavel" if intocavel else classe,
            "procedencia": procedencia,
        })
    # A varredura entra DEPOIS e em faixa própria: o que ela acha não tem classe
    # nem anotação, e por isso não pode se misturar com quem tem procedência.
    for p, pista, classe_v in suspeitos(procs, anotados, eu, max(idade_min, idade_suspeito)):
        itens.append({
            "pid": p["pid"], "cmd": p["cmd"][:300], "rss_mb": round(p["rss"] / 1024),
            "arvore_mb": round(arvore.get(p["pid"], p["rss"]) / 1024),
            "idade_min": round(p["idade"] / 60), "cpu_s": round(p["cpu"], 1),
            "classe": classe_v,
            "procedencia": "sem anotação — achado pela varredura",
            "pista": pista,
        })
    itens.sort(key=lambda x: (-x["arvore_mb"], -x["rss_mb"], -x["idade_min"]))
    return itens


# ── a família: quinze linhas iguais viram uma decisão só ────────────────────
def agrupa(itens):
    """Junta numa entrada só os processos IDÊNTICOS — mesmo comando, mesma
    classe, mesma procedência. Quinze trabalhadores do mesmo compilador são uma
    decisão, não quinze: o usuário responde por família, e o que ele precisa ver
    é quantos são e quanto pesam somados.

    A memória própria (`rss_mb`) SOMA — é memória de verdade, uma por processo.
    A da árvore não soma: dois membros da mesma família podem estar um dentro do
    outro, e somar contaria o mesmo filho duas vezes. Fica o maior da família,
    que é o pior caso real.

    `pids` vem inteiro: é ele que o passo de encerrar recebe."""
    grupos, ordem = {}, []
    for it in itens:
        chave = (it["cmd"], it["classe"], it["procedencia"])
        g = grupos.get(chave)
        if g is None:
            g = {"cmd": it["cmd"], "classe": it["classe"],
                 "procedencia": it["procedencia"], "n": 0, "pids": [],
                 "rss_mb": 0, "arvore_mb": 0, "idade_min": 0}
            if it.get("pista"):
                g["pista"] = it["pista"]
            grupos[chave] = g
            ordem.append(g)
        g["n"] += 1
        g["pids"].append(it["pid"])
        g["rss_mb"] += it["rss_mb"]
        g["arvore_mb"] = max(g["arvore_mb"], it["arvore_mb"])
        g["idade_min"] = max(g["idade_min"], it["idade_min"])
    ordem.sort(key=lambda g: (-g["rss_mb"], -g["arvore_mb"], -g["idade_min"]))
    return ordem


def _mb(v):
    return "%.1f GB" % (v / 1024.0) if v >= 1024 else "%d MB" % v


def _idade(minutos):
    if minutos >= 1440:
        return "%dd" % (minutos // 1440)
    if minutos >= 60:
        return "%dh" % (minutos // 60)
    return "%dmin" % minutos


def resumo_terminal(itens, teto_pids=8):
    """O inventário agrupado, pronto para o terminal. Este é o caminho PADRÃO da
    faxina: com centenas de processos, a página custa caro para dizer o que cabe
    em vinte linhas — a página passa a ser pedida, não automática."""
    grupos = agrupa(itens)
    if not grupos:
        return "Nada de pé para faxinar."
    n = sum(g["n"] for g in grupos)
    linhas = ["%d processos em %d famílias · %s de memória própria"
              % (n, len(grupos), _mb(sum(g["rss_mb"] for g in grupos)))]
    for g in grupos:
        vezes = ("%d×" % g["n"]) if g["n"] > 1 else "  1"
        linhas.append("")
        linhas.append("%4s  %8s  árvore %8s  %-6s  %s  %s"
                      % (vezes, _mb(g["rss_mb"]), _mb(g["arvore_mb"]),
                         _idade(g["idade_min"]), g["classe"], g["procedencia"]))
        linhas.append("      %s" % g["cmd"][:140])
        if g.get("pista"):
            linhas.append("      pista: %s" % g["pista"])
        pids = " ".join(str(p) for p in g["pids"][:teto_pids])
        if g["n"] > teto_pids:
            pids += " … (+%d)" % (g["n"] - teto_pids)
        linhas.append("      pids: %s" % pids)
    return "\n".join(linhas)


# ── linha de comando ────────────────────────────────────────────────────────
def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("uso: lixeiro.py anota|colhe|orfaos|marca-cpu|resumo|inventario|encerra [...]")
        return 0
    cmd = argv[1]
    dry = "--dry-run" in argv
    sid = os.environ.get("LIXEIRO_SESSION") or ""
    for i, a in enumerate(argv):
        if a == "--sessao" and i + 1 < len(argv):
            sid = argv[i + 1]

    if cmd == "anota":
        comando = cwd = ""
        dono = None
        for i, a in enumerate(argv):
            if a == "--cmd" and i + 1 < len(argv):
                comando = argv[i + 1]
            if a == "--cwd" and i + 1 < len(argv):
                cwd = argv[i + 1]
            if a == "--dono" and i + 1 < len(argv):
                dono = argv[i + 1]
        classe = anota(sid, comando, cwd, dono)
        print(classe or "")
        return 0

    if cmd == "marca-cpu":
        marca_cpu(sid)
        return 0

    if cmd in ("colhe", "colhe-turno", "colhe-sessao"):
        modo = "sessao" if cmd == "colhe-sessao" else ("turno" if cmd == "colhe-turno" else
                                                       (argv[2] if len(argv) > 2 and not argv[2].startswith("-") else "turno"))
        mortos = colhe(sid, modo, dry_run=dry)
        # O registro morre com a sessão — MENOS quando sobrou processo de pé, e aí
        # ele é a única procedência que a varredura de órfãos vai ter na abertura
        # seguinte. Apagá-lo sempre (o que o hook fazia) transformava todo processo
        # poupado em processo sem dono conhecido, que nenhuma colheita mais encerra.
        if modo == "sessao" and not dry and not candidatos(sid, "sessao"):
            try:
                os.remove(registro_path(sid))
            except OSError:
                pass
        print(json.dumps(mortos, ensure_ascii=False))
        return 0

    if cmd == "orfaos":
        mortos = colhe_orfaos(exceto=sid, dry_run=dry)
        print(json.dumps(mortos, ensure_ascii=False))
        return 0

    if cmd in ("inventario", "resumo"):
        idade = 600
        idade_susp = 3600
        for i, a in enumerate(argv):
            if a == "--idade-min" and i + 1 < len(argv):
                idade = int(argv[i + 1])
            if a == "--idade-suspeito" and i + 1 < len(argv):
                idade_susp = int(argv[i + 1])
        itens = inventario(idade, idade_susp)
        # `resumo` é o caminho padrão da faxina (terminal, agrupado por família).
        # `inventario` continua devolvendo o JSON cru — é o que o hook de fim de
        # turno lê, e é o que alimenta a página quando ela for PEDIDA.
        if cmd == "resumo":
            print(resumo_terminal(itens))
        else:
            print(json.dumps(itens, ensure_ascii=False, indent=1))
        return 0

    if cmd == "encerra":
        # Encerra pids explícitos — é o caminho da faxina manual, onde quem
        # escolheu foi o usuário. Ainda assim as travas valem.
        procs = processos()
        eu = ancestrais(os.getpid(), procs)
        por_pid = {p["pid"]: p for p in procs}
        feitos = []
        for a in argv[2:]:
            if not a.isdigit():
                continue
            pid = int(a)
            p = por_pid.get(pid)
            if not p or pid in eu or eh_intocavel(p["cmd"]):
                continue
            sinal = encerra(pid) if not dry else "(simulado)"
            if sinal:
                feitos.append({"pid": pid, "cmd": p["cmd"][:300], "rss_mb": round(p["rss"] / 1024),
                               "sinal": sinal, "motivo": "faxina manual",
                               "em": time.strftime("%Y-%m-%dT%H:%M:%S")})
        if not dry:
            registra_colheita(feitos)
        print(json.dumps(feitos, ensure_ascii=False))
        return 0

    print("comando desconhecido: %s" % cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
