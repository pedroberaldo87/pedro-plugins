#!/usr/bin/env python3
"""Ledger do intent-guard — caderno append-only dos pedidos verbatim do usuário.

Eventos (1 JSON/linha em ledger.jsonl):
  raw      {"ev":"raw","id":"r-N","ts":...,"session":"sid","text":"<verbatim>"}
  classify {"ev":"classify","raw":"r-N","id":"p-N","ts":...,"class":"pedido|correcao|restricao|conversa",
            "resumo":"...","substitui":"p-K"|null}
  verdict  {"ev":"verdict","entry":"p-N","ts":...,"verdict":"feito|parcial|nao_feito",
            "mode":"confirmado|inferido","evidence":"...","audit":"audit-X.json"}
  baixa    {"ev":"baixa","entry":"p-N","ts":...,"by":"auditor|usuario|substituido","reason":"..."}
Estado vivo = fold dos eventos. Stdlib only. Consumido pelos hooks shell via CLI.
"""
import argparse
import contextlib

try:
    import fcntl                       # POSIX
except ImportError:                    # Windows não tem fcntl (ver `locked`)
    fcntl = None
import json
import os
import re
import subprocess
import sys
import tempfile
import time

ESPERA_TRAVA_S = 5.0   # teto da espera pela trava (ver `locked`)

# CANAIS DE TEXTO EM UTF-8, SEMPRE. No Windows eles nascem na codificação do sistema
# (cp1252) e o payload do evento — que chega por stdin — é UTF-8: sem isto, todo
# acento do pedido do usuário chega corrompido ao gate, e emoji derruba a escrita.
for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass
from pathlib import Path

MARKERS = ("package.json", "CLAUDE.md", "pyproject.toml", "Cargo.toml", "go.mod", ".git")
CLASSES = ("pedido", "correcao", "restricao", "conversa")


def project_root(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5, stdin=subprocess.DEVNULL, start_new_session=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    d = os.path.abspath(cwd)
    home = os.path.expanduser("~")
    while d and d not in (home, "/"):
        if any(os.path.exists(os.path.join(d, m)) for m in MARKERS):
            return d
        d = os.path.dirname(d)
    return None


def intent_dir(cwd):
    root = project_root(cwd)
    if root:
        # If git returned the real path different from cwd, reconcile by checking
        # if cwd itself is a git root
        if os.path.realpath(cwd) == os.path.realpath(root):
            # cwd is the git root, return with cwd form (preserves original path)
            return os.path.join(cwd, ".claude", "intent")
        return os.path.join(root, ".claude", "intent")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", os.path.abspath(cwd)).strip("-")
    return os.path.join(os.path.expanduser("~/.claude/intent"), slug)


def ensure_exclude(cwd):
    """Ignore LOCAL (.git/info/exclude) — nunca toca arquivo versionado do repo.
    Usa `git rev-parse --git-path` em vez de isdir(.git/): num worktree, .git é
    um FILE apontando pro gitdir real, não um diretório."""
    root = project_root(cwd)
    if not root:
        return
    try:
        r = subprocess.run(["git", "-C", root, "rev-parse", "--git-path", "info/exclude"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5, stdin=subprocess.DEVNULL, start_new_session=True)
        if r.returncode != 0 or not r.stdout.strip():
            return
        p = r.stdout.strip()
        if not os.path.isabs(p):
            p = os.path.join(root, p)
    except Exception:
        return
    line = ".claude/intent/"
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        cur = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
        if line not in cur:
            with open(p, "a", encoding="utf-8") as f:
                if cur and not cur.endswith("\n"):
                    f.write("\n")
                f.write(line + "\n")
    except OSError:
        pass


def load(d):
    evs = []
    p = os.path.join(d, "ledger.jsonl")
    if not os.path.exists(p):
        return evs
    try:
        for ln in open(p, encoding="utf-8"):
            try:
                evs.append(json.loads(ln))
            except Exception:
                continue
    except OSError:
        pass
    return evs


@contextlib.contextmanager
def locked(d):
    """Trava exclusiva pra load+append atômico — evita r-N/p-N duplicados quando
    hooks concorrentes chamam record-raw/apply.

    Duas implementações, porque `fcntl` é POSIX e NÃO EXISTE no Windows (o `import`
    no topo derrubava o módulo inteiro lá, e com ele todo comando do intent-guard):

    - com `fcntl`: `flock`, que é o caminho testado e o de sempre;
    - sem ele: **diretório de trava**, criado com `os.mkdir`, que é atômico em
      qualquer sistema de arquivos — quem cria, entra; quem não cria, espera.

    ⚠️ NÃO use `msvcrt.locking` aqui. Foi a primeira tentativa e ela PENDUROU o job
    do Windows na esteira (de 50 s para mais de 10 min): `LK_LOCK` espera pelo
    bloqueio, e sobre o primeiro byte de um arquivo de trava recém-criado — vazio —
    não se comporta como o `flock`.

    A espera tem teto (`ESPERA_TRAVA_S`) e a trava tem idade máxima: processo morto
    no meio deixaria o diretório para trás e travaria todo mundo para sempre. Passou
    do teto, segue SEM a trava — id duplicado é incômodo visível, missão pendurada é
    dano. O invariante que isto protege está em `test_ledger.py:test_concurrent_record_raw`.
    """
    os.makedirs(d, exist_ok=True)
    if fcntl is not None:
        with open(os.path.join(d, "ledger.lock"), "a+", encoding="utf-8") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        return

    trava = os.path.join(d, "ledger.lock.d")
    limite = time.time() + ESPERA_TRAVA_S
    meu = False
    # O TETO É CHECADO NO TOPO, e não depois do `except`. Com ele lá embaixo, o
    # `continue` do caminho "trava órfã removida" pulava a checagem: se outro
    # processo recriasse a trava nesse intervalo, o laço girava sem limite. Foi o
    # que pendurou o job do Windows (de 45 s para mais de 10 min) — pela segunda
    # vez, e pelo mesmo motivo: espera sem teto absoluto.
    while time.time() < limite:
        try:
            os.mkdir(trava)
            meu = True
            break
        except FileExistsError:
            try:                      # trava órfã de processo morto não é eterna
                if time.time() - os.path.getmtime(trava) > ESPERA_TRAVA_S:
                    os.rmdir(trava)
            except OSError:
                pass
            time.sleep(0.02)          # segue sem trava se o teto estourar
    try:
        yield
    finally:
        if meu:
            try:
                os.rmdir(trava)
            except OSError:
                pass


def append(d, ev):
    os.makedirs(d, exist_ok=True)
    ev.setdefault("ts", int(time.time()))
    with open(os.path.join(d, "ledger.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def next_id(evs, prefix):
    n = 0
    for e in evs:
        i = str(e.get("id", ""))
        if i.startswith(prefix + "-"):
            try:
                n = max(n, int(i.split("-", 1)[1]))
            except ValueError:
                pass
    return "%s-%d" % (prefix, n + 1)


def fold(evs, session=None):
    """Estado vivo do caderno. `session` FILTRA pending/live para os pedidos
    daquela sessão — sem isso, sessões paralelas no mesmo projeto (Prisma numa,
    Workplace noutra) compartilham a lista de vivos e o gate de uma cobra os
    pedidos da outra. Bug real observado num monorepo: uma única auditoria
    cobrou 3 frentes de 3 sessões. `entries` continua completo — o /intent-guard
    status mostra tudo, o filtro é só para quem COBRA."""
    raws = {e["id"]: e for e in evs if e.get("ev") == "raw" and e.get("id")}
    entries = {}
    classified = set()
    for e in evs:
        ev = e.get("ev")
        if ev == "classify":
            classified.add(e.get("raw"))
            if e.get("class") in ("pedido", "correcao", "restricao") and e.get("id"):
                raw = raws.get(e.get("raw"), {})
                entries[e["id"]] = {"id": e["id"], "class": e["class"],
                                    "resumo": e.get("resumo", ""),
                                    "text": raw.get("text", ""),
                                    "session": raw.get("session", ""),
                                    "status": "vivo", "verdicts": []}
                sub = e.get("substitui")
                if sub and sub in entries and entries[sub]["status"] == "vivo":
                    entries[sub]["status"] = "substituido"
            elif e.get("class") == "conversa":
                pass  # descartado — mas fica visível no journal pro /intent-guard status
        elif ev == "verdict" and e.get("entry") in entries:
            entries[e["entry"]]["verdicts"].append(
                {k: e.get(k) for k in ("verdict", "mode", "evidence", "audit", "ts")})
        elif ev == "baixa" and e.get("entry") in entries:
            if entries[e["entry"]]["status"] == "vivo":
                entries[e["entry"]]["status"] = "baixado:" + str(e.get("by", "?"))
    pending = [raws[i] for i in raws if i not in classified]
    if session:
        pending = [r for r in pending if r.get("session") == session]
    pending.sort(key=lambda r: r.get("ts", 0))
    vivos = [v for v in entries.values() if v["status"] == "vivo"]
    if session:
        vivos = [v for v in vivos if v.get("session") == session]
    # Restrição não CONCLUI — ela vale enquanto valer. Misturada aos pedidos, nunca
    # saía da lista de "a fazer" e dava a impressão de trabalho parado; e o gate
    # cobrava dela um veredito que um auditor escreveu ser impossível: "o cumprimento
    # dela na conversa não é auditável por mim, por desenho". Sai da cobrança e vira
    # CONTAGEM (ver furos_da_regua) — quem consome `live` cobra só o que se conclui.
    live = [v for v in vivos if v["class"] != "restricao"]
    standing = [v for v in vivos if v["class"] == "restricao"]
    live.sort(key=lambda v: int(v["id"].split("-", 1)[1]))
    standing.sort(key=lambda v: int(v["id"].split("-", 1)[1]))
    return {"pending": pending, "live": live, "standing": standing, "entries": entries}


# Artefatos que a PRÓPRIA auditoria cria ao executar o código (o prompt canônico
# OBRIGA o auditor a rodar o que der pra rodar). Sem excluí-los, auditar muda o
# tree e o veredito nasce vencido — o gate nunca fecha, bate o cap e libera SEM
# auditoria, o oposto do propósito. O hash protege contra CÓDIGO alterado depois
# da auditoria; lixo de execução não é código.
# ponytail: lista fixa dos suspeitos comuns; se aparecer um artefato novo, some aqui.
EXEC_ARTIFACTS = (
    "__pycache__", "*.pyc", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".DS_Store", "*.log", ".coverage", "htmlcov",
    # JS/TS: hoje quase sempre gitignorados (medido em projeto Node real: nao mudam o
    # hash), mas projeto que VERSIONA build cairia no mesmo defeito. Preventivo.
    "dist", "build", ".vite", ".next", ".turbo",
    "playwright-report", "test-results", "coverage",
)


def tree_hash(cwd):
    """Hash do working tree INCLUINDO untracked (técnica do green-cache):
    index temporário + read-tree HEAD + add -A + write-tree.
    Artefato de execução (EXEC_ARTIFACTS) fica de fora — ver comentário acima."""
    root = project_root(cwd)
    if not root:
        return ""
    try:
        r = subprocess.run(["git", "-C", root, "rev-parse", "--git-dir"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5, stdin=subprocess.DEVNULL, start_new_session=True)
        if r.returncode != 0:
            return ""
    except Exception:
        return ""
    fd, idx = tempfile.mkstemp(prefix="intent-guard-idx-")
    os.close(fd)
    env = dict(os.environ, GIT_INDEX_FILE=idx)
    try:
        subprocess.run(["git", "-C", root, "read-tree", "HEAD"],
                       env=env, capture_output=True, timeout=15, stdin=subprocess.DEVNULL, start_new_session=True)
        excludes = [":(exclude)%s" % p for p in EXEC_ARTIFACTS]
        excludes += [":(exclude)**/%s" % p for p in EXEC_ARTIFACTS]
        subprocess.run(["git", "-C", root, "add", "-A", "--", "."] + excludes,
                       env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL, start_new_session=True)
        r = subprocess.run(["git", "-C", root, "write-tree"],
                           env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, stdin=subprocess.DEVNULL, start_new_session=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""
    finally:
        try:
            os.unlink(idx)
        except OSError:
            pass


def _arquivos_citados(audit):
    """Caminhos que os vereditos citam como prova. Só conta o que EXISTE no repo —
    a evidência é texto livre e cita comando, número e frase solta junto."""
    txt = " ".join(str(v.get("evidence", "")) for v in audit.get("verdicts", [])
                   if isinstance(v, dict))
    achados = set()
    for tok in re.split(r"[\s,;:()\[\]{}'\"`]+", txt):
        tok = tok.strip().rstrip(".").split(":")[0]
        if len(tok) > 3 and "/" in tok or (tok.count(".") == 1 and len(tok) > 4):
            achados.add(tok.lstrip("./"))
    return achados


def _arquivos_mexidos(cwd, hash_antigo):
    """Arquivos que mudaram entre o tree auditado e agora. None quando não dá pra
    saber (hash órfão, sem git) — quem chama trata None como 'reprova', porque
    não-saber nunca pode virar aprovação."""
    root = project_root(cwd)
    if not root or not hash_antigo:
        return None
    try:
        atual = tree_hash(cwd)
        if not atual:
            return None
        r = subprocess.run(["git", "-C", root, "diff", "--name-only",
                            hash_antigo, atual],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        if r.returncode != 0:
            return None
        return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}
    except Exception:
        return None


def audit_check(cwd, path, session=None):
    why = []
    try:
        audit = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "why": ["audit ilegível: %s" % e]}
    cur = tree_hash(cwd)
    if cur and audit.get("tree_hash") != cur:
        # Mudou o tree — mas mudou O QUÊ? O consumo só acontece no Stop seguinte, então
        # agir sobre um achado da PRÓPRIA auditoria vencia o veredito que acabara de
        # chegar (o auditor apontou i18n morto, o agente removeu, o veredito morreu).
        # Só reprova se o que mudou toca algum arquivo que o veredito citou como prova.
        # Sem arquivo citado dá pra identificar, mantém a reprovação de antes.
        citados = _arquivos_citados(audit)
        mexidos = _arquivos_mexidos(cwd, audit.get("tree_hash"))
        if not citados or mexidos is None or (citados & mexidos):
            why.append("tree mudou depois da auditoria (veredito vencido)")
    verdicts = {v.get("entry"): v for v in audit.get("verdicts", []) if isinstance(v, dict)}
    st = fold(load(intent_dir(cwd)), session)

    # O conjunto validado é o conjunto PERGUNTADO, não o que estiver vivo agora.
    #
    # O gate grava <arquivo>.escopo no instante do bloqueio com os ids que ele pôs no
    # bloco DADOS. Sem isso, cada mensagem que o usuário manda entre auditar e consumir
    # entrava na conta e o veredito nascia impossível de aprovar — a catraca só crescia
    # (medido 30/07: 33 pedidos vivos cobrados de uma auditoria que perguntou por 1).
    # Arquivo antigo não tem sidecar: cai no comportamento de antes, nada quebra.
    alvo = [e["id"] for e in st["live"]]
    try:
        with open(path + ".escopo", encoding="utf-8") as f:
            perguntados = json.load(f)
        if isinstance(perguntados, list) and perguntados:
            vivos = set(alvo)
            # só cobra o que foi perguntado E continua vivo — pedido já baixado no meio
            # do caminho não precisa de veredito.
            alvo = [i for i in perguntados if i in vivos]
    except Exception:
        pass

    por_id = {e["id"]: e for e in st["live"]}
    for eid in alvo:
        e = por_id.get(eid)
        if e is None:
            continue
        v = verdicts.get(e["id"])
        if not v:
            why.append("pedido vivo %s sem veredito" % e["id"])
            continue
        if v.get("verdict") not in ("feito", "parcial", "nao_feito"):
            why.append("%s: verdict inválido" % e["id"])
        if v.get("mode") not in ("confirmado", "inferido"):
            why.append("%s: mode inválido" % e["id"])
        if len(str(v.get("evidence", "")).strip()) < 10:
            why.append("%s: evidência vazia/rasa" % e["id"])
    return {"ok": not why, "why": why}


def apply_audit(cwd, path, session=None):
    """Transcreve vereditos do audit file pro ledger (determinístico — o agente
    principal não toca no caderno). feito+confirmado → baixa automática.
    EXPERIMENTAL (decisão de projeto, 2026-07-24): pode migrar pra baixa só-manual."""
    marker = path + ".applied"
    if os.path.exists(marker):
        return
    d = intent_dir(cwd)
    try:
        audit = json.load(open(path, encoding="utf-8"))
    except Exception:
        return
    live_ids = {e["id"] for e in fold(load(d), session)["live"]}
    fname = os.path.basename(path)
    for v in audit.get("verdicts", []):
        if not isinstance(v, dict) or v.get("entry") not in live_ids:
            continue
        append(d, {"ev": "verdict", "entry": v["entry"], "verdict": v.get("verdict"),
                   "mode": v.get("mode"), "evidence": str(v.get("evidence", ""))[:2000],
                   "audit": fname})
        if v.get("verdict") == "feito" and v.get("mode") == "confirmado":
            append(d, {"ev": "baixa", "entry": v["entry"], "by": "auditor",
                       "reason": "feito+confirmado (%s) [EXPERIMENTAL]" % fname})
    try:
        open(marker, "w", encoding="utf-8").close()
    except OSError:
        pass


def cmd_apply(cwd):
    d = intent_dir(cwd)
    evs = load(d)
    for ln in sys.stdin:
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except Exception:
            continue
        if e.get("ev") != "classify" or e.get("class") not in CLASSES:
            continue
        if not any(r.get("ev") == "raw" and r.get("id") == e.get("raw") for r in evs):
            continue
        if any(c.get("ev") == "classify" and c.get("raw") == e.get("raw") for c in evs):
            continue  # já classificado — juiz repetiu, ignora
        if e["class"] != "conversa":
            e["id"] = next_id(evs, "p")
        e = {k: e.get(k) for k in ("ev", "raw", "id", "class", "resumo", "substitui", "verify")}
        # SEGURANÇA: `verify` é uma ESCOLHA de catálogo, nunca um comando. O juiz
        # é um LLM — deixá-lo escrever shell que o hook executa seria injeção de
        # comando por design. Qualquer valor fora do catálogo vira None.
        if e.get("verify") not in RECIPES:
            e["verify"] = None
        append(d, e)
        evs = load(d)


def recipe_git_synced(cwd):
    """'commit push', 'sobe pro marketplace', 'sincroniza' — o pedido inteiro é
    'o remoto tem o que eu tenho'. Devolve (ok, evidência) ou (None, motivo) se
    não der pra decidir (aí sobe pro auditor caro)."""
    root = project_root(cwd)
    if not root:
        return None, "não é projeto git"
    try:
        br = subprocess.run(["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        if br.returncode != 0:
            return None, "sem branch"
        branch = br.stdout.strip()
        up = subprocess.run(["git", "-C", root, "rev-parse", "--abbrev-ref",
                             "%s@{upstream}" % branch],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        if up.returncode != 0 or not up.stdout.strip():
            return None, "branch sem upstream"
        upstream = up.stdout.strip()
        subprocess.run(["git", "-C", root, "fetch", "-q", "origin", branch],
                       capture_output=True, timeout=60, stdin=subprocess.DEVNULL, start_new_session=True)
        h = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, start_new_session=True).stdout.strip()
        r = subprocess.run(["git", "-C", root, "rev-parse", upstream],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, start_new_session=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", root, "status", "--porcelain",
                                "--untracked-files=no"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, stdin=subprocess.DEVNULL, start_new_session=True).stdout.strip()
    except Exception as e:
        return None, "erro de git: %s" % e
    if not h or not r:
        return None, "hash vazio"
    if h != r:
        return False, ("HEAD %s != %s %s — há commit local não publicado (ou remoto à frente)"
                       % (h[:8], upstream, r[:8]))
    if dirty:
        return False, ("HEAD == %s (%s), mas há mudança rastreada não commitada:\n%s"
                       % (upstream, h[:8], dirty[:400]))
    return True, ("git rev-parse HEAD == %s == %s; git status (tracked) limpo — "
                  "commit e push confirmados" % (upstream, h[:8]))


# Catálogo FECHADO de verificações mecânicas. O juiz só ESCOLHE uma chave daqui;
# ele nunca escreve o comando. Começa com uma só — a que cobria 4 dos 7 pedidos
# medidos numa sessão real. ponytail: adicionar receita nova só quando um pedido
# real precisar, não por antecipação.
RECIPES = {"git_synced": recipe_git_synced}


def cmd_verify(cwd, session=None):
    """Escada de custo, degrau 0: resolve por CÓDIGO os vivos que têm receita,
    antes de gastar um agente. Grava verdict+baixa nos que passam. Imprime JSON
    {"resolved":[...],"failed":[...],"remaining":N} — quem sobra vai pro auditor."""
    d = intent_dir(cwd)
    evs = load(d)
    st = fold(evs, session)
    recipe_of = {}
    for e in evs:
        if e.get("ev") == "classify" and e.get("id") and e.get("verify") in RECIPES:
            recipe_of[e["id"]] = e["verify"]
    resolved, failed = [], []
    for entry in st["live"]:
        name = recipe_of.get(entry["id"])
        if not name:
            continue
        ok, ev_txt = RECIPES[name](cwd)
        if ok is None:
            continue  # indecidível → deixa pro auditor
        append(d, {"ev": "verdict", "entry": entry["id"],
                   "verdict": "feito" if ok else "nao_feito",
                   "mode": "confirmado", "evidence": "[%s] %s" % (name, ev_txt[:1500]),
                   "audit": "recipe:%s" % name})
        if ok:
            append(d, {"ev": "baixa", "entry": entry["id"], "by": "receita",
                       "reason": "verificado por %s (sem LLM)" % name})
            resolved.append({"entry": entry["id"], "recipe": name, "evidence": ev_txt[:400]})
        else:
            failed.append({"entry": entry["id"], "recipe": name, "evidence": ev_txt[:400]})
    remaining = len(fold(load(d), session)["live"])
    return {"resolved": resolved, "failed": failed, "remaining": remaining}


def furos_da_regua():
    """(total, desde a última olhada, marca). Os dois números saem do MESMO log —
    append-only —, então mostrar os dois não custa nada e não obriga a escolher entre
    perder o histórico e perder a leitura do que é novo.

    Duas fontes, que é onde a régua de forma deixa rastro: o guarda mecânico registra
    em bypass.log a resposta que furou o teto (ele desiste após 2 bloqueios pra não
    travar a sessão), e o juiz registra em batidas.log o veredito de cada julgamento.
    """
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    marca = claude / "state" / "intent-guard" / "olhado"
    try:
        desde = float(marca.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        desde = 0.0
    total = novos = fontes = 0
    for log, e_furo in ((claude / "state" / "prose-ceiling" / "bypass.log", lambda d: True),
                        (claude / "state" / "forma-relato" / "batidas.log",
                         lambda d: d.get("motivo") == "julgou" and d.get("veredito") != "passa")):
        try:
            linhas = log.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue  # log ausente ≠ zero furo — quem conta as fontes é `fontes`
        fontes += 1
        for ln in linhas:
            try:
                dd = json.loads(ln)
            except ValueError:
                continue
            if not e_furo(dd):
                continue
            total += 1
            if float(dd.get("ts") or 0) > desde:
                novos += 1
    return total, novos, fontes, marca


def cmd_status(cwd):
    d = intent_dir(cwd)
    evs = load(d)
    st = fold(evs)
    print("caderno: %s" % os.path.join(d, "ledger.jsonl"))
    print("\nVIVOS (%d):" % len(st["live"]))
    for e in st["live"]:
        print("  %s [%s] (sessão %s) %s — %r" % (
            e["id"], e["class"], (e.get("session") or "?")[:8], e["resumo"], e["text"][:80]))
    if st["standing"]:
        total, novos, fontes, marca = furos_da_regua()
        print("\nCOBRANÇAS PERMANENTES (%d) — não concluem, então não entram na conta acima:"
              % len(st["standing"]))
        for e in st["standing"]:
            print("  %s %s — %r" % (e["id"], e["resumo"], e["text"][:80]))
        if fontes:
            print("  régua de forma furada: %d vez(es) no total · %d desde a última vez que você olhou"
                  % (total, novos))
        else:
            print("  régua de forma furada: SEM REGISTRO nesta máquina — os guardas não deixaram "
                  "rastro,\n  e isso não quer dizer zero furo; quer dizer que ninguém sabe.")
        try:
            marca.parent.mkdir(parents=True, exist_ok=True)
            marca.write_text(str(time.time()), encoding="utf-8")
        except OSError:
            pass  # fail-open: não poder marcar nunca derruba o status
    done = [e for e in st["entries"].values() if e["status"] != "vivo"]
    print("\nRESOLVIDOS/ARQUIVADOS (%d):" % len(done))
    for e in done:
        print("  %s [%s] %s → %s" % (e["id"], e["class"], e["resumo"], e["status"]))
    conv = [e for e in evs if e.get("ev") == "classify" and e.get("class") == "conversa"]
    print("\nDESCARTADOS como conversa (%d) — confira se algum era pedido:" % len(conv))
    raws = {r.get("id"): r for r in evs if r.get("ev") == "raw"}
    for e in conv:
        print("  %s: %r" % (e.get("raw"), raws.get(e.get("raw"), {}).get("text", "")[:80]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["resolve-dir", "record-raw", "state", "apply",
                                    "baixa", "tree-hash", "audit-check", "apply-audit",
                                    "verify", "status"])
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--session", default="")
    ap.add_argument("--text-stdin", action="store_true")
    ap.add_argument("--id", default="")
    ap.add_argument("--by", default="usuario")
    ap.add_argument("--reason", default="")
    ap.add_argument("--file", default="")
    a = ap.parse_args(argv)
    d = intent_dir(a.cwd)

    # Fail-open: erros de I/O (.claude/intent inacessível/cheio/read-only)
    # degradam silenciosamente para MUTATING, ou com fallback JSON para READ.
    try:
        if a.cmd == "resolve-dir":
            print(d)
        elif a.cmd == "record-raw":
            text = sys.stdin.read() if a.text_stdin else ""
            if text.strip():
                ensure_exclude(a.cwd)
                with locked(d):
                    append(d, {"ev": "raw", "id": next_id(load(d), "r"),
                               "session": a.session, "text": text})
        elif a.cmd == "state":
            print(json.dumps(fold(load(d), a.session or None), ensure_ascii=False))
        elif a.cmd == "apply":
            with locked(d):
                cmd_apply(a.cwd)
        elif a.cmd == "baixa":
            if a.id:
                append(d, {"ev": "baixa", "entry": a.id, "by": a.by, "reason": a.reason})
        elif a.cmd == "tree-hash":
            print(tree_hash(a.cwd))
        elif a.cmd == "audit-check":
            print(json.dumps(audit_check(a.cwd, a.file, a.session or None), ensure_ascii=False))
        elif a.cmd == "apply-audit":
            apply_audit(a.cwd, a.file, a.session or None)
        elif a.cmd == "verify":
            with locked(d):
                print(json.dumps(cmd_verify(a.cwd, a.session or None), ensure_ascii=False))
        elif a.cmd == "status":
            cmd_status(a.cwd)
    except Exception:
        # Degradação: comandos de escrita silenciam; leitura fallback seguro.
        if a.cmd in ("record-raw", "apply", "baixa", "apply-audit"):
            pass  # Silencioso — ledger indisponível, continua adiante.
        elif a.cmd in ("state", "audit-check", "verify"):
            fb = ({"pending": [], "live": [], "entries": {}} if a.cmd == "state"
                  else {"ok": False, "why": ["erro interno"]} if a.cmd == "audit-check"
                  # verify falhando NÃO pode resolver pedido nenhum: devolve tudo
                  # pro auditor caro (degradar pro caro é seguro; pro barato não).
                  else {"resolved": [], "failed": [], "remaining": -1})
            print(json.dumps(fb, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
