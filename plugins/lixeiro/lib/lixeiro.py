#!/usr/bin/env python3
"""lixeiro.py — o motor da coleta de processos deixados para trás.

A REGRA QUE MANDA EM TODAS: só é candidato o processo cuja ABERTURA foi anotada
por este mesmo mecanismo. Nome de programa NUNCA é critério — nesta máquina há
61 processos sob `node`, entre eles a própria sessão do Claude Code, os serviços
do harness e o navegador. `pkill node` mataria o trabalho junto com o lixo.

O ciclo:
  anota   (PostToolUse)  — o comando abriu processo? grava assinatura + hora + sessão
  colhe   (Stop)         — efêmero vivo morre; serviço só morre se ficou ocioso
  colhe   (SessionEnd)   — tudo que a sessão anotou
  varre   (SessionStart) — registro de sessão cujo dono não existe mais

Estado em ~/.claude/lixeiro/ — NUNCA dentro do plugin (que é cache reescrito a
cada bump de versão). Um arquivo por sessão, mais um log do que foi encerrado.

Portabilidade: usa só `ps -eo` (POSIX), sem `etimes` (que o macOS ignora em
silêncio) e sem `pkill`. Sistema sem `ps` utilizável: não encerra nada e sai calado.
"""

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
]
SERVICO = [
    r"\bnext (dev|start)\b", r"\bnext-server\b", r"\bvite\b(?!.*\bbuild\b)",
    r"\bnpm run dev\b", r"\bnodemon\b", r"\bhttp\.server\b", r"\bhttp-server\b",
    r"\buvicorn\b", r"\bgunicorn\b", r"\bflask run\b", r"\brails server\b",
    r"\bstorybook\b", r"\bng serve\b", r"\bserve -s\b",
]
# Máquina virtual, serviço de contêiner e o que o próprio harness mantém de pé.
# A decisão de 2026-08-05 foi explícita: o lixeiro NUNCA encosta nestes — reporta.
INTOCAVEL = [
    r"\blimactl\b", r"\bqemu", r"\bcolima\b", r"\bdocker\b", r"\bcontainerd\b",
    r"\bDocker Desktop\b", r"\bollama\b",
    r"\bclaude\b", r"\bbg-pty-host\b", r"\bbg-spare\b", r"\bcc-daemon\b",
    r"\bvisual_server\.mjs\b", r"\bnode_modules/\.bin/claude\b",
]

CLASSES = (("efemero", EFEMERO), ("servico", SERVICO))


def classifica(cmd):
    """Devolve 'efemero', 'servico' ou None. Intocável vence tudo."""
    for pat in INTOCAVEL:
        if re.search(pat, cmd, re.I):
            return None
    for nome, pats in CLASSES:
        for pat in pats:
            if re.search(pat, cmd, re.I):
                return nome
    return None


def eh_intocavel(cmd):
    return any(re.search(p, cmd, re.I) for p in INTOCAVEL)


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


def processos():
    """Lista de dicts {pid, ppid, idade, cpu, rss, cmd}. Lista vazia = não sei ler,
    e não saber ler significa não encerrar nada (fail-safe, não fail-open cego)."""
    try:
        out = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,etime=,time=,rss=,args="],
            capture_output=True, text=True, timeout=10,
        )
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


def vivo(pid):
    """Vive de verdade? Processo já encerrado mas ainda não colhido pelo pai
    (estado Z) responde ao sinal 0 como se estivesse vivo — e isso faria a
    colheita concluir que o encerramento falhou, e escalar para o sinal forte
    à toa. Por isso o zumbi conta como morto."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    try:
        out = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)],
                             capture_output=True, text=True, timeout=5)
        estado = out.stdout.strip()
        if estado.startswith("Z"):
            return False
    except (OSError, subprocess.SubprocessError):
        pass
    return True


def ancestrais(pid, procs):
    """Cadeia de pais do pid. É o que impede o mecanismo de se matar: nada que
    esteja acima do próprio hook na árvore pode receber sinal."""
    por_pid = {p["pid"]: p for p in procs}
    cadeia, atual, guarda = set(), pid, 0
    while atual and atual > 1 and guarda < 64:
        cadeia.add(atual)
        p = por_pid.get(atual)
        if not p:
            break
        atual = p["ppid"]
        guarda += 1
    cadeia.add(pid)
    return cadeia


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


def anota(session_id, comando, cwd, dono_pid=None):
    """Registra que ESTE comando pode ter aberto processo. Devolve a classe, ou
    None quando o comando não é abridor (e aí nada é gravado)."""
    classe = classifica(comando or "")
    if not classe:
        return None
    reg = le_registro(session_id)
    if dono_pid:
        reg["dono_pid"] = int(dono_pid)
    reg.setdefault("anotacoes", []).append({
        "cmd": (comando or "")[:400],
        "cwd": cwd or "",
        "classe": classe,
        "em": time.time(),
        "cpu_ultimo_turno": None,
    })
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


def cwd_de(pid):
    """Pasta de trabalho do processo. É a prova mais forte de que ele pertence ao
    projeto anotado — mais forte que o texto do comando, que muitas vezes não
    carrega o caminho (`next-server (v16.2.11)` é o exemplo desta máquina).
    Sem `lsof`, devolve None e o casamento cai para o texto do comando."""
    if pid in _CWD_CACHE:
        return _CWD_CACHE[pid]
    val = None
    try:
        out = subprocess.run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                             capture_output=True, text=True, timeout=5)
        for linha in out.stdout.splitlines():
            if linha.startswith("n/"):
                val = linha[1:]
    except (OSError, subprocess.SubprocessError):
        val = None
    _CWD_CACHE[pid] = val
    return val


def _sob(caminho, raiz):
    """O caminho está dentro da raiz? Compara as DUAS formas de cada um, porque
    no macOS `/var/folders/...` e `/private/var/folders/...` são a mesma pasta e
    chegam por vias diferentes: a anotação traz o caminho como o shell o viu, e
    o `lsof` devolve o resolvido. Sem isto, nenhum processo em pasta temporária
    casa a própria anotação — e a colheita nunca acontece."""
    if not caminho or not raiz:
        return False
    formas_raiz = {raiz.rstrip("/"), os.path.realpath(raiz).rstrip("/")}
    formas_cam = {caminho.rstrip("/"), os.path.realpath(caminho).rstrip("/")}
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
        if raiz in proc["cmd"] or os.path.realpath(raiz).rstrip("/") in proc["cmd"]:
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

    modo 'turno'   — efêmero vivo (lixo certo) + serviço ocioso desde o turno anterior
    modo 'sessao'  — tudo que a sessão anotou e ainda vive
    """
    procs = processos() if procs is None else procs
    if not procs:
        return []
    reg = le_registro(session_id)
    eu = ancestrais(os.getpid(), procs)
    achados = []
    for anot in reg.get("anotacoes", []):
        for p in procs:
            if p["pid"] in eu:
                continue                      # trava de suicídio
            if not casa(anot, p):
                continue
            if modo == "sessao":
                achados.append((anot, p, "fim de sessão"))
            elif anot.get("classe") == "efemero":
                achados.append((anot, p, "suíte/build que devia ter terminado"))
            elif anot.get("classe") == "servico":
                antes = anot.get("cpu_ultimo_turno")
                if antes is not None and p["cpu"] <= antes + 0.5 and p["idade"] > 120:
                    achados.append((anot, p, "servidor sem uso desde o turno anterior"))
    return achados


def marca_cpu(session_id, procs=None):
    """Fotografa o tempo de CPU de cada serviço anotado. É o que, no turno
    seguinte, distingue o servidor EM USO do servidor esquecido — sem isso o
    fim de turno derrubaria o servidor que o próximo turno ia usar."""
    procs = processos() if procs is None else procs
    if not procs:
        return
    reg = le_registro(session_id)
    mudou = False
    for anot in reg.get("anotacoes", []):
        if anot.get("classe") != "servico":
            continue
        for p in procs:
            if casa(anot, p):
                anot["cpu_ultimo_turno"] = p["cpu"]
                mudou = True
                break
    if mudou:
        grava_registro(reg)


def encerra(pid, grace=3.0):
    """Pede para terminar; só força se ele ignorar. Devolve como morreu, ou None."""
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return None
    fim = time.time() + grace
    while time.time() < fim:
        if not vivo(pid):
            return "TERM"
        time.sleep(0.15)
    try:
        os.kill(pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        return "TERM"
    time.sleep(0.2)
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
    mortos = []
    for anot, p, motivo in candidatos(session_id, modo):
        if dry_run:
            mortos.append({"pid": p["pid"], "cmd": p["cmd"], "rss_mb": round(p["rss"] / 1024),
                           "motivo": motivo, "sinal": "(simulado)"})
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
    """Anotação sem processo vivo correspondente não tem mais o que colher."""
    procs = processos()
    if not procs:
        return
    reg = le_registro(session_id)
    vivas = [a for a in reg.get("anotacoes", []) if any(casa(a, p) for p in procs)]
    if len(vivas) != len(reg.get("anotacoes", [])):
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
        if not dry_run:
            try:
                os.remove(registro_path(sid))
            except OSError:
                pass
    return mortos


# ── o inventário da faxina manual: TUDO, com ou sem procedência ─────────────
def inventario(idade_min=600):
    """Candidatos para a faxina manual. Aqui entra o que NÃO tem procedência —
    e por isso este caminho nunca encerra sozinho: só lista, o usuário escolhe."""
    procs = processos()
    if not procs:
        return []
    eu = ancestrais(os.getpid(), procs)
    anotados = set()
    for nome in os.listdir(state_dir()):
        if nome.startswith("sessao-") and nome.endswith(".json"):
            sid = nome[7:-5]
            for anot in le_registro(sid).get("anotacoes", []):
                for p in procs:
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
        itens.append({
            "pid": p["pid"], "cmd": p["cmd"][:300], "rss_mb": round(p["rss"] / 1024),
            "idade_min": round(p["idade"] / 60), "cpu_s": round(p["cpu"], 1),
            "classe": "intocavel" if intocavel else classe,
            "procedencia": "anotado" if p["pid"] in anotados else "sem dono conhecido",
        })
    itens.sort(key=lambda x: (-x["rss_mb"], -x["idade_min"]))
    return itens


# ── linha de comando ────────────────────────────────────────────────────────
def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("uso: lixeiro.py anota|colhe|orfaos|marca-cpu|inventario|encerra [...]")
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
        print(json.dumps(mortos, ensure_ascii=False))
        return 0

    if cmd == "orfaos":
        mortos = colhe_orfaos(exceto=sid, dry_run=dry)
        print(json.dumps(mortos, ensure_ascii=False))
        return 0

    if cmd == "inventario":
        idade = 600
        for i, a in enumerate(argv):
            if a == "--idade-min" and i + 1 < len(argv):
                idade = int(argv[i + 1])
        print(json.dumps(inventario(idade), ensure_ascii=False, indent=1))
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
