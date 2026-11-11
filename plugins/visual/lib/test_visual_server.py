#!/usr/bin/env python3
"""Suite do daemon do /visual (server/visual_server.mjs) — stdlib, sem framework.

O que protege: o daemon escuta em 127.0.0.1, mas o navegador do usuário também
alcança 127.0.0.1 — qualquer página aberta nele podia ler e sobrescrever o estado
(latest.json, config.json, licoes-clareza.json) que o agente e o scope-cop tratam
como decisão do usuário. A fronteira agora é um token (header X-Visual-Token) +
Origin/Host + Content-Type, e um corpo malformado não derruba o processo.

    python3 plugins/visual/lib/test_visual_server.py
"""

import http.client
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.normpath(os.path.join(HERE, "..", "server", "visual_server.mjs"))
START = os.path.normpath(os.path.join(HERE, "..", "server", "start.sh"))
sys.path.insert(0, HERE)
# A receita do lar fingido é uma cópia vendorada de _shared/ (que mora em hooks/ neste plugin).
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "hooks")))
from bash_posix import bash_posix  # noqa: E402
from lar_fingido import ambiente  # noqa: E402

PASS = FAIL = 0
TOKEN = "a1" * 32  # 64 hex, valor de teste
GOOD = {"Content-Type": "application/json", "X-Visual-Token": TOKEN}


def check(label, cond, extra=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, "" if extra is None else extra))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def home_env(home, **extra):
    return ambiente(home, **extra)


def req(port, method, path, body=None, headers=None):
    """Devolve (status, headers-em-minúsculas, corpo) — None se a conexão caiu."""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        data = r.read().decode("utf-8", "replace")
        return r.status, {k.lower(): v for k, v in r.getheaders()}, data
    except (OSError, http.client.HTTPException):
        return None, {}, ""
    finally:
        c.close()


def start_daemon(home, port):
    p = subprocess.Popen(["node", SERVER], env=home_env(home, CLAUDE_VISUAL_PORT=str(port)),
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                         stdin=subprocess.DEVNULL)
    for _ in range(60):
        time.sleep(0.1)
        if req(port, "GET", "/ping")[0] == 200:
            return p
        if p.poll() is not None:
            break
    raise RuntimeError("daemon não subiu: %s" % (p.stderr.read().decode("utf-8", "replace")
                                                  if p.poll() is not None else "timeout"))


def stop(p):
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    if p and p.stderr:
        p.stderr.close()


def alive(port):
    return req(port, "GET", "/ping")[0] == 200


def post(port, payload, headers=None, raw=None):
    body = raw if raw is not None else json.dumps(payload)
    return req(port, "POST", "/state", body, GOOD if headers is None else headers)


if not shutil.which("node"):
    print("  skip daemon do /visual (node não está no PATH — o daemon é opcional)")
    sys.exit(0)

home = tempfile.mkdtemp(prefix="visual-srv-")
state_dir = os.path.join(home, ".claude", "visual-state")
os.makedirs(state_dir)
with open(os.path.join(state_dir, ".token"), "w") as fh:
    fh.write(TOKEN)
os.chmod(os.path.join(state_dir, ".token"), 0o600)
port = free_port()
proc = None
try:
    proc = start_daemon(home, port)
    latest = os.path.join(state_dir, "latest.json")
    sess = lambda n: os.path.join(state_dir, n + ".json")  # noqa: E731
    rec = {"session": "abcd1234", "docTitle": "t", "state": {"feedback": [{"val": "keep"}]}}

    print("\n[escrita — POST /state exige o token]")
    st, _, _ = post(port, rec, headers={"Content-Type": "application/json"})
    check("POST sem token → 403", st == 403, st)
    check("POST sem token não grava nada",
          not os.path.exists(latest) and not os.path.exists(sess("abcd1234")))
    st, _, _ = post(port, rec, headers=dict(GOOD, **{"X-Visual-Token": "b2" * 32}))
    check("POST com token errado → 403", st == 403, st)
    st, _, _ = post(port, rec, headers=dict(GOOD, **{"X-Visual-Token": TOKEN[:-1]}))
    check("POST com token truncado → 403", st == 403, st)
    check("token errado não grava nada", not os.path.exists(latest))

    print("\n[Content-Type — text/plain atravessa CORS sem preflight]")
    st, _, _ = post(port, None, headers={"Content-Type": "text/plain", "X-Visual-Token": TOKEN},
                    raw=json.dumps(rec))
    check("POST text/plain com token → 415", st == 415, st)
    st, _, _ = post(port, None, headers={"X-Visual-Token": TOKEN}, raw=json.dumps(rec))
    check("POST sem Content-Type → 415", st == 415, st)
    check("415 não grava nada", not os.path.exists(latest))

    print("\n[leitura — GET /state exige o token]")
    st, _, _ = req(port, "GET", "/state?session=abcd1234")
    check("GET /state sem token → 403", st == 403, st)
    st, _, _ = req(port, "GET", "/state?session=abcd1234", headers={"X-Visual-Token": "c3" * 32})
    check("GET /state com token errado → 403", st == 403, st)

    print("\n[corpo malformado não derruba o daemon]")
    for label, kw in (
        ("body `null`", dict(raw="null")),
        ("body `[]`", dict(raw="[]")),
        ("body `42`", dict(raw="42")),
        ("body `\"x\"`", dict(raw='"x"')),
        ("JSON inválido", dict(raw="{nope")),
        ("session=null", dict(payload={"session": None})),
        ("session=123", dict(payload={"session": 123})),
        ("session={}", dict(payload={"session": {}})),
        ("session ausente", dict(payload={"state": {}})),
    ):
        st, _, _ = post(port, kw.get("payload"), raw=kw.get("raw"))
        check("%s → 400" % label, st == 400, st)
        check("%s: daemon segue de pé" % label, alive(port))
    st, _, _ = post(port, {"session": "abcd1234", "state": "string"})
    check("state que não é objeto → 400", st == 400, st)
    st, _, _ = req(port, "POST", "/state", "x" * (300 * 1024), GOOD)
    check("corpo acima de 256 KB não derruba o daemon", alive(port))
    check("nada disso gravou", not os.path.exists(latest) and not os.path.exists(sess("abcd1234")))

    print("\n[nomes reservados — sessão não vira outro arquivo de estado]")
    for name in ("latest", "config", "licoes-clareza", "LATEST", "Config"):
        st, _, _ = post(port, {"session": name, "state": {}})
        check("session=%r → 400" % name, st == 400, st)
    check("nenhum arquivo reservado foi criado",
          not any(os.path.exists(sess(n)) for n in ("latest", "config", "licoes-clareza")))
    with open(sess("config"), "w") as fh:
        fh.write('{"keep": true}')
    st, _, _ = post(port, {"session": "config", "state": {"x": 1}})
    with open(sess("config")) as fh:
        check("config.json existente fica intacto", fh.read() == '{"keep": true}' and st == 400)
    os.remove(sess("config"))
    st, _, _ = req(port, "GET", "/state?session=latest", headers=GOOD)
    check("GET ?session=latest não é alias de leitura → 400", st == 400, st)

    print("\n[caminho feliz — token + JSON]")
    st, _, _ = post(port, rec)
    check("token válido + JSON → 200", st == 200, st)
    check("gravou <session>.json e latest.json",
          os.path.exists(sess("abcd1234")) and os.path.exists(latest))
    with open(latest) as fh:
        got = json.load(fh)
    check("latest.json tem o formato que o scope-cop lê (docTitle + state.feedback)",
          got.get("docTitle") == "t" and got["state"]["feedback"][0]["val"] == "keep"
          and got.get("session") == "abcd1234")
    st, _, data = req(port, "GET", "/state?session=abcd1234", headers={"X-Visual-Token": TOKEN})
    check("GET /state com token → 200 e devolve o registro",
          st == 200 and json.loads(data)["session"] == "abcd1234", st)
    st, _, _ = req(port, "GET", "/state?session=naoexiste", headers={"X-Visual-Token": TOKEN})
    check("sessão inexistente → 404", st == 404, st)

    print("\n[Origin e Host]")
    for o in ("https://example.com", "http://example.com:7755", "http://127.0.0.1:1",
              "http://localhost.example.com:%d" % port):
        st, hd, _ = post(port, rec, headers=dict(GOOD, Origin=o))
        check("POST com Origin %s e token válido → 403" % o, st == 403, st)
        check("  …sem cabeçalho CORS de volta", "access-control-allow-origin" not in hd, hd)
    st, hd, _ = req(port, "GET", "/state?session=abcd1234",
                    headers={"X-Visual-Token": TOKEN, "Origin": "https://example.com"})
    check("GET com Origin estranho → 403 e sem CORS",
          st == 403 and "access-control-allow-origin" not in hd, (st, hd))
    st, hd, _ = req(port, "GET", "/ping", headers={"Origin": "https://example.com"})
    check("/ping com Origin estranho → 403", st == 403, st)
    st, hd, _ = post(port, rec, headers=dict(GOOD, Origin="null"))
    check("Origin `null` (página file://) com token → 200", st == 200, st)
    check("  …ecoa exatamente `null`, nunca `*`",
          hd.get("access-control-allow-origin") == "null", hd)
    st, hd, _ = post(port, rec, headers=dict(GOOD, Origin="http://127.0.0.1:%d" % port))
    check("Origin do próprio daemon → 200", st == 200, st)
    st, hd, _ = post(port, rec, headers=dict(GOOD, Origin="http://localhost:%d" % port))
    check("Origin localhost do próprio daemon → 200", st == 200, st)
    st, hd, _ = post(port, rec)
    check("sem Origin (curl/hook) com token → 200 e sem CORS",
          st == 200 and "access-control-allow-origin" not in hd, (st, hd))
    st, _, _ = post(port, rec, headers=dict(GOOD, Host="attacker.example.com"))
    check("Host estranho (DNS rebinding) → 403", st == 403, st)

    print("\n[preflight — a página file:// manda header custom + JSON]")
    st, hd, _ = req(port, "OPTIONS", "/state", headers={
        "Origin": "null", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-visual-token"})
    check("preflight de `null` → 204", st == 204, st)
    check("  …ecoa `null`", hd.get("access-control-allow-origin") == "null", hd)
    check("  …libera Content-Type e X-Visual-Token",
          "x-visual-token" in hd.get("access-control-allow-headers", "").lower()
          and "content-type" in hd.get("access-control-allow-headers", "").lower(), hd)
    st, hd, _ = req(port, "OPTIONS", "/state", headers={
        "Origin": "https://example.com", "Access-Control-Request-Method": "POST"})
    check("preflight de origem estranha → 403 e sem CORS",
          st == 403 and "access-control-allow-origin" not in hd, (st, hd))

    print("\n[/ping]")
    st, hd, data = req(port, "GET", "/ping")
    info = json.loads(data) if st == 200 else {}
    check("/ping segue aberto para o start.sh (sem Origin)", st == 200 and info.get("status") == "ok")
    check("/ping declara que exige token (start.sh reconhece daemon antigo)",
          info.get("auth") is True, info)
    check("nenhuma resposta usa Access-Control-Allow-Origin: *",
          hd.get("access-control-allow-origin") != "*")
finally:
    stop(proc)

# ── o daemon cria o token sozinho (0600) quando não existe ──────────────────
print("\n[token — gerado quando falta]")
home2 = tempfile.mkdtemp(prefix="visual-srv2-")
port2 = free_port()
proc2 = None
try:
    proc2 = start_daemon(home2, port2)
    tok_path = os.path.join(home2, ".claude", "visual-state", ".token")
    check("daemon criou .token", os.path.isfile(tok_path))
    tok = open(tok_path).read().strip() if os.path.isfile(tok_path) else ""
    check("token tem 64 hex", len(tok) == 64 and all(c in "0123456789abcdef" for c in tok), tok)
    if os.name == "posix" and os.path.isfile(tok_path):
        check("permissão 0600", stat.S_IMODE(os.stat(tok_path).st_mode) == 0o600,
              oct(os.stat(tok_path).st_mode))
    st, _, _ = req(port2, "POST", "/state", json.dumps({"session": "abcd1234", "state": {}}),
                   {"Content-Type": "application/json", "X-Visual-Token": tok})
    check("o token gerado autoriza", st == 200, st)
finally:
    stop(proc2)
    shutil.rmtree(home2, ignore_errors=True)

# ── start.sh: gera o token (0600), é idempotente e não gira o token ─────────
print("\n[start.sh]")
BASH = bash_posix()
if BASH is None or not shutil.which("node") or not shutil.which("curl"):
    print("  skip start.sh (bash, node ou curl indisponível nesta máquina)")
else:
    home3 = tempfile.mkdtemp(prefix="visual-srv3-")
    port3 = free_port()
    env3 = home_env(home3, CLAUDE_VISUAL_PORT=str(port3))
    tok_path = os.path.join(home3, ".claude", "visual-state", ".token")
    try:
        r = subprocess.run([BASH, START], env=env3, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=30)
        check("start.sh sobe o daemon", r.returncode == 0 and alive(port3), r.stdout + r.stderr)
        tok = open(tok_path).read().strip() if os.path.isfile(tok_path) else ""
        check("start.sh deixou um token de 64 hex",
              len(tok) == 64 and all(c in "0123456789abcdef" for c in tok), tok)
        if os.name == "posix" and os.path.isfile(tok_path):
            check("token 0600", stat.S_IMODE(os.stat(tok_path).st_mode) == 0o600)
        st, _, _ = req(port3, "POST", "/state", json.dumps({"session": "abcd1234", "state": {}}),
                       {"Content-Type": "application/json", "X-Visual-Token": tok})
        check("o daemon aceita o token do start.sh", st == 200, st)
        r = subprocess.run([BASH, START], env=env3, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=30)
        check("segunda chamada é no-op e não gira o token",
              r.returncode == 0 and open(tok_path).read().strip() == tok)
    finally:
        pid = None
        st, _, data = req(port3, "GET", "/ping")
        if st == 200:
            pid = json.loads(data).get("pid")
        if pid:
            try:
                os.kill(pid, 15)
            except OSError:
                pass
        time.sleep(0.3)
        shutil.rmtree(home3, ignore_errors=True)

    # daemon de antes do token: /ping sem `auth` e aceita qualquer um — start.sh troca.
    print("\n[start.sh — daemon antigo sem token]")
    home4 = tempfile.mkdtemp(prefix="visual-srv4-")
    port4 = free_port()
    old = os.path.join(home4, "visual_server_old.mjs")
    with open(old, "w") as fh:
        fh.write("import http from 'node:http';\n"
                 "http.createServer((q, r) => { r.writeHead(200, {'Access-Control-Allow-Origin': '*'});"
                 " r.end(JSON.stringify({status: 'ok', pid: process.pid, port: %d})); })"
                 ".listen(%d, '127.0.0.1');\n" % (port4, port4))
    oldp = subprocess.Popen(["node", old], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL)
    try:
        for _ in range(40):
            time.sleep(0.1)
            if alive(port4):
                break
        env4 = home_env(home4, CLAUDE_VISUAL_PORT=str(port4))
        r = subprocess.run([BASH, START], env=env4, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=30)
        st, _, data = req(port4, "GET", "/ping")
        check("start.sh troca o daemon sem token pelo novo",
              st == 200 and json.loads(data).get("auth") is True and oldp.poll() is not None,
              r.stdout + r.stderr)
    finally:
        if oldp.poll() is None:
            oldp.kill()
        st, _, data = req(port4, "GET", "/ping")
        if st == 200:
            try:
                os.kill(json.loads(data)["pid"], 15)
            except (OSError, KeyError, ValueError):
                pass
        time.sleep(0.3)
        shutil.rmtree(home4, ignore_errors=True)

shutil.rmtree(home, ignore_errors=True)
print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
