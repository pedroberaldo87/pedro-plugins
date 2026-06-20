#!/usr/bin/env python3
"""
test_journal.py — testes do scrubber + journal/delta do project-doc (lote de correções).

Reproduz cada um dos 5 vazamentos de secret achados no code-review e prova que fecharam,
mais a integridade do cofre, o delta, o backward-delta (self-stale + working-tree),
a colisão de id (64 chars), o self_path_match e a validação de invalidate/curate.

Self-contained: repo git temporário + cofre em /tmp via PROJECT_DOC_COFRE_DIR.
Roda com:  python3 plugins/project-doc/lib/test_journal.py
"""
import os, sys, shutil, subprocess, json, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["PROJECT_DOC_COFRE_DIR"] = "/tmp/pdtest_cofre"
shutil.rmtree("/tmp/pdtest_cofre", ignore_errors=True)
import journal  # noqa: E402

PASS = 0


def check(label, cond):
    global PASS
    assert cond, "FALHOU: " + label
    PASS += 1
    print("  ok ·", label)


# ---------------------------------------------------------------------------
def test_scrubber():
    print("\n== scrubber — os 5 vazamentos ==")
    # #1 PEM colado depois de `key:` + newline (o bug que mutilava o BEGIN e vazava o corpo)
    s, _ = journal.scrub("pem:\n-----BEGIN RSA PRIVATE KEY-----\nMIIBVERYSECRETBODY12345\n-----END RSA PRIVATE KEY-----")
    check("#1 PEM-newline: corpo da chave não vaza", "MIIBVERYSECRETBODY12345" not in s)

    # #2 valor numérico sob chave-secreta
    s, _ = journal.scrub("SECRET_PIN=839271")
    check("#2 numérico: SECRET_PIN redigido", "839271" not in s and "‹cofre:" in s)

    # #3 secret em prosa (o formato dominante de transcript/handoff)
    s, _ = journal.scrub("a senha de produção é hunter2supersecret e pronto")
    check("#3 prosa: senha em frase redigida", "hunter2supersecret" not in s)

    # #4 token de provider sob chave genérica
    s, _ = journal.scrub("GH_PAT=ghp_0123456789abcdefghij0123456789")
    check("#4 provider: ghp_ redigido", "ghp_0123456789abcdefghij0123456789" not in s and "‹cofre:" in s)

    # #5 PUBLIC como substring (REPUBLICAN) não pode suprimir a redação
    s, _ = journal.scrub("REPUBLICAN_SECRET=realvalue123")
    check("#5 PUBLIC word-boundary: REPUBLICAN_SECRET redigido", "realvalue123" not in s)

    print("== scrubber — preserva contexto ==")
    s, _ = journal.scrub("SSH_HOST=1.2.3.4")
    check("host preservado", "1.2.3.4" in s)
    s, _ = journal.scrub("PORT=5432")
    check("porta preservada", "PORT=5432" in s)
    s, _ = journal.scrub("PUBLIC_KEY=foo")
    check("chave pública preservada", "PUBLIC_KEY=foo" in s)
    s, _ = journal.scrub("commit 9f8c2a1b3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f80 fechou")
    check("sha preservado (não vira cofre nem revisar)", "9f8c2a1b3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f80" in s and "‹" not in s)

    print("== scrubber — na dúvida marca ==")
    s, _ = journal.scrub("blob aleatório Zk9bQ2mX7vL4pR8tW1nC6yH3 no meio")
    check("token de alta entropia → ‹revisar?›", "‹revisar?›" in s)


# ---------------------------------------------------------------------------
def test_scrubber_r2():
    print("\n== scrubber rodada 2 — leaks que sobraram ==")

    def red(label, text, leaked):
        s, _ = journal.scrub(text)
        check(label, leaked not in s)

    red("DB_PASS (chave PASS) redigido", "export DB_PASS=p@ssw0rd!", "p@ssw0rd!")
    red("senha: numérico (assign PT) redigido", "senha: 123456", "123456")
    red("senha= numérico redigido", "senha=123456", "123456")
    red("https conn-string: senha embutida redigida",
        "DATABASE_URL=https://admin:SuperSecret123@db.example.com/app", "SuperSecret123")
    red("Authorization: Bearer <tok> — token redigido (não 'Bearer')",
        "Authorization: Bearer abc123XYZ789longtoken", "abc123XYZ789longtoken")
    red("secret com / na prosa redigido", "the secret is wJalr9K7/MDENG2/bPxRfiCY3", "wJalr9K7/MDENG2/bPxRfiCY3")
    red("password is <mixed curto> redigido", "the password is hunter2longmix9", "hunter2longmix9")
    red("markdown **Password:** redigido", "**Password:** hunter2secretvalue", "hunter2secretvalue")

    # None não quebra
    s, sec = journal.scrub(None)
    check("scrub(None) não quebra", s == "" and sec == [])

    # boundary 19 chars: marca ‹revisar?›
    s, _ = journal.scrub("blob aB3dE6gH9jK2mN5pQ8r solto")  # 19 chars mixed
    check("token 19-char bare → ‹revisar?›", "‹revisar?›" in s)

    # anti-corrupção: dois sinais antes do mesmo token → 1 span só, valor some, sem ›› duplo
    s, sec = journal.scrub("password secret aB3xK9mPq2LwZ7vT4n agora")
    check("dois sinais, mesmo token: valor redigido", "aB3xK9mPq2LwZ7vT4n" not in s)
    check("dois sinais: sem delimitador duplicado", "››" not in s)

    # URL perto de signal NÃO é vaultada (contexto preservado)
    s, _ = journal.scrub("the api key docs at https://example.com/keys ok")
    check("URL perto de signal preservada", "https://example.com/keys" in s)

    # self_path_match: arquivo de raiz homônimo não casa anchor aninhado
    check("self_path_match raiz-homônimo não casa",
          journal.self_path_match("plugins/foo/config.json", {"config.json"}) is False)


# ---------------------------------------------------------------------------
def test_scrubber_r3():
    print("\n== scrubber rodada 3 — scheme genérico, command-subst, over-redação ==")

    def red(label, text, leaked):
        s, _ = journal.scrub(text)
        check(label, leaked not in s)

    def keep(label, text, kept):
        s, _ = journal.scrub(text)
        check(label, kept in s)

    # conn-string com QUALQUER scheme (não-allowlist) → senha redigida
    red("clickhouse:// senha redigida", "clickhouse://user:s3cretPass99@host:9000/db", "s3cretPass99")
    red("mssql:// senha redigida", "mssql://sa:P@ssw0rdMix1@10.0.0.5/db", "P@ssw0rdMix1")
    # command substitution: segredo dentro de $(...) vai inteiro pro cofre
    red("$(...) command-subst redigido", "export TOKEN=$(echo MyRealSecret123)", "MyRealSecret123")

    # over-redação NÃO acontece em chaves que só CONTÊM o keyword como substring
    keep("AUTHOR preservado (não casa AUTH)", "AUTHOR=pedro", "AUTHOR=pedro")
    keep("OAUTH_REDIRECT_URL preservado", "OAUTH_REDIRECT_URL=https://app.com/cb", "https://app.com/cb")
    keep("COMPASS_VERSION preservado (não casa PASS)", "COMPASS_VERSION=1.2.3", "1.2.3")
    keep("CHAVEIRO preservado (não casa CHAVE)", "CHAVEIRO=meucarro", "meucarro")
    # mas a chave-secreta real continua redigida
    red("AUTH_TOKEN ainda redige", "AUTH_TOKEN=abc123secretval", "abc123secretval")
    red("ACCESS_KEY ainda redige", "ACCESS_KEY=AKIA1234567890ABCDEF", "AKIA1234567890ABCDEF")

    # signal DENTRO de valor composto não destrói o valor preservado
    keep("PUBLIC_KEY com 'secret' no valor não é destruído",
         "PUBLIC_KEY=ssh-rsa-not-secret-just-a-value", "just-a-value")

    # GITHUB_TOKEN redige; PUBLIC_KEY preserva
    red("GITHUB_TOKEN redige", "GITHUB_TOKEN=ghp_0123456789abcdefghij0123456789", "ghp_0123456789abcdefghij0123456789")

    # chave colada (sem separador) — termo forte por substring
    red("SECRETVALUE colada redige", "SECRETVALUE=correcthorse", "correcthorse")
    red("APIKEYVALUE colada redige", "APIKEYVALUE=plaintextpw", "plaintextpw")
    red("PASSWORDVALUE colada redige", "PASSWORDVALUE=plainpw", "plainpw")
    # PUBLIC + termo secreto = AINDA secreto (curto-circuito removido)
    red("PUBLIC_SECRET redige (não vaza por causa de PUBLIC)", "PUBLIC_SECRET=topsecret", "topsecret")
    keep("PUBLIC_KEY puro preservado", "PUBLIC_KEY=ssh-rsa-AAAA", "ssh-rsa-AAAA")
    # $(...) aninhado: valor inteiro vai pro cofre, tail não vaza
    red("$() aninhado não trunca", "PASSWORD=$(f $(g) MyPlainPass)", "MyPlainPass")


# ---------------------------------------------------------------------------
def test_scrubber_r4():
    print("\n== scrubber rodada 4 — glued keys, URL-suffix, $() fundo ==")

    def red(label, text, leaked):
        s, _ = journal.scrub(text)
        check(label, leaked not in s)

    def keep(label, text, kept):
        s, _ = journal.scrub(text)
        check(label, kept in s)

    red("PRIVATEKEY colada redige", "PRIVATEKEY=letmein", "letmein")
    red("MASTERKEY colada redige", "MASTERKEY=correcthorse", "correcthorse")
    red("AUTHTOKEN colada redige", "AUTHTOKEN=plainsecretvalue", "plainsecretvalue")
    keep("PUBLICKEY colada preservada", "PUBLICKEY=ssh-rsa-AAAA", "ssh-rsa-AAAA")
    # sufixo localizador: URL/FILE/NAME não é o segredo
    keep("PASSWORD_POLICY_URL preserva a URL", "PASSWORD_POLICY_URL=https://wiki.corp/pw", "https://wiki.corp/pw")
    keep("SECRET_FILE preserva o path", "SECRET_FILE=/etc/app/secret.pem", "/etc/app/secret.pem")
    # mas o segredo de verdade segue redigido
    red("API_KEY (sem sufixo) ainda redige", "API_KEY=realtokenvalue123", "realtokenvalue123")
    # $() fundo (3 níveis) não vaza o tail
    red("$() 3 níveis não vaza", "PASSWORD=$(a $(b $(echo hunter)))", "hunter")
    red("$() com espaços fundo não vaza", "PASSWORD=$(a $(b $(echo MyPlainPass) ) )", "MyPlainPass")
    # valor entre aspas contendo a aspa OPOSTA (quebrava o ASSIGN antes)
    red("aspas duplas com ' interna redige tudo", "DB_TOKEN=\"p4ss'w0rd9\"", "p4ss'w0rd9")
    red("aspas simples com \" interna redige tudo", "CREDENTIAL='aaa1bbb2\"ddd4eee5'", "aaa1bbb2\"ddd4eee5")
    red("valor entre aspas com espaços redige tudo", 'PASSWORD="s3cr3t value com espaços"', "s3cr3t value com espaços")
    # tail após aspa interna não sobra
    s, _ = journal.scrub("SECRET=\"aB3xK9pQ7'mZ2wL5vR8nThQ\"")
    check("sem tail vazado após aspa interna", "mZ2wL5vR8nThQ" not in s)
    # aspa NO MEIO de valor não-citado: nada vaza
    red("aspa no meio não vaza tail", "SECRET=p4ss\"w0rd\"S3cr3tT0k3nXYZ", "S3cr3tT0k3nXYZ")
    red("aspa no meio (token curto) não vaza", "TOKEN=abc\"defS3cr3tValue9", "defS3cr3tValue9")
    # aspa de abertura não-terminada: valor curto não vaza
    red("aspa aberta não-terminada não vaza", "SECRET=\"ab12c", "ab12c")
    # backtick no meio do valor não vaza o tail
    red("backtick no meio não vaza", "SECRET=`a`Zk9Lm2Qw8Xy4Bv7Nc3", "Zk9Lm2Qw8Xy4Bv7Nc3")
    red("backtick command-subst com espaço não vaza", "PASSWORD=`echo secretvalue123`", "secretvalue123")
    # valor longo (>500) não trunca/vaza o tail
    longval = "aB3" + ("xY7z" * 130)            # ~523 chars sem espaço
    s, _ = journal.scrub("SECRET=" + longval)
    check("valor longo não vaza tail", longval[-30:] not in s and "‹cofre:" in s)
    # conn-string com usuário VAZIO (redis/amqp) — senha redigida
    red("redis://:senha@ (user vazio) redige", "DATABASE_URL=redis://:Sup3rR3disPass@cache:6379", "Sup3rR3disPass")
    red("amqp://:senha@ em prosa redige", "fila em amqp://:R4bb1tSecret@mq:5672/v", "R4bb1tSecret")


def test_scrubber_r5():
    print("\n== scrubber rodada 5 — prosa: hex/filename é segredo, path/known-ext é contexto ==")

    def red(label, text, leaked):
        s, _ = journal.scrub(text)
        check(label, leaked not in s)

    def keep(label, text, kept):
        s, _ = journal.scrub(text)
        check(label, kept in s)

    red("hex puro após 'token is' redige", "rotated the api key, new token is 9f86d081884c7d65", "9f86d081884c7d65")
    red("valor filename-shaped (ext desconhecida) após 'password is' redige", "the password is Tr0ub4dor.x99", "Tr0ub4dor.x99")
    keep("arquivo de ext CONHECIDA após sinal é contexto", "the api key is in config.json here", "config.json")
    keep("path após sinal é contexto", "the secret is at /etc/app/key.pem", "/etc/app/key.pem")
    keep("versão após sinal é contexto", "the token format is 1.2.3 ok", "1.2.3")
    # layer 4 (SEM sinal) ainda preserva sha de contexto
    keep("sha sem sinal preservado (contexto)", "fixed in commit 9f86d081884c7d65a1b2 today", "9f86d081884c7d65a1b2")


def test_scrubber_r6():
    print("\n== scrubber rodada 6 — placeholder não esconde o secret seguinte ==")

    def red(label, text, leaked):
        s, _ = journal.scrub(text)
        check(label, leaked not in s)

    def keep(label, text, kept):
        s, _ = journal.scrub(text)
        check(label, kept in s)

    AWS = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    red("par AWS: secret-access-key após o id (placeholder) redige",
        "aws secret access key AKIAIOSFODNN7EXAMPLE " + AWS + " done", AWS)
    red("sk- antes do slash-secret não esconde",
        "credentials sk-abcdefghij0123456789ABCDxyz " + AWS, AWS)
    # slash-secret de alta entropia SEM sinal por perto → ao menos marca ‹revisar?› (não some)
    s, _ = journal.scrub("blob " + AWS + " no fim")
    check("slash-secret sem sinal → ‹revisar?›", "‹revisar?›" in s)
    # path de código (baixa entropia) NÃO é marcado
    keep("path de código preservado (sem flag)", "see src/components/Widget.tsx for detail", "src/components/Widget.tsx")


def test_scrubber_r7():
    print("\n== scrubber rodada 7 — chave JSON entre aspas ==")

    def red(label, text, leaked):
        s, _ = journal.scrub(text)
        check(label, leaked not in s)

    red('JSON "password": "val" redige', '{"password": "RealSecretValue9999"}', "RealSecretValue9999")
    red('JSON "api_key":"val" redige', '{"api_key":"realkeyvalue12345"}', "realkeyvalue12345")
    red("YAML/py 'secret': 'val' redige", "config = {'secret': 'realval123xyz'}", "realval123xyz")
    red('JSON "db_password" minúsculo redige', '"db_password": "Hunter2ProdValue"', "Hunter2ProdValue")
    # JSON ANINHADO numa linha — chave externa não-secreta engolia o par interno
    red("JSON aninhado 1 linha redige o interno", '{"db":{"password":"839271"}}', "839271")
    red("JSON aninhado c/ espaços redige", '{"redis": {"password": "R3disPass99"}}', "R3disPass99")
    red("JSON aninhado em log redige", 'loaded {"svc":{"api_key":"realkey9988"}} at boot', "realkey9988")
    # singular PT "credencial"
    red("prosa 'a credencial é X' redige", "gerei a credencial Acc3ssC0d3xyz999 pro staging", "Acc3ssC0d3xyz999")
    # JSON: o valor do par VIZINHO não-secreto é preservado (não roubado pelo sinal da chave)
    s, _ = journal.scrub('{"password":"s3cr3tval99","host":"prod-db-7"}')
    check("vizinho não-secreto preservado", "prod-db-7" in s)
    check("o secret do par foi redigido", "s3cr3tval99" not in s)


def test_curate_scrub():
    print("\n== curate/invalidate passam pelo scrubber ==")
    T = "/tmp/pdtest_curate"
    shutil.rmtree(T, ignore_errors=True)
    os.makedirs(os.path.join(T, ".claude", ".project-doc"))
    journal.state_dir = lambda pr: os.path.join(T, ".claude", ".project-doc")
    # planta um finding direto no journal
    journal.append_events(T, [{"ev": "discovered", "id": "abc123", "raw_kind": "handoff",
                               "text": "orig", "anchors": [], "source": {"ts": "x"}, "scrubbed": False, "ts": 1}])
    journal.run_curate(T, "abc123", "nota curada com DB_PASSWORD=Hunter2ProdValue88 colado")
    body = open(os.path.join(T, ".claude", ".project-doc", "findings.jsonl"), encoding="utf-8").read()
    check("curate NÃO grava secret cru no journal git-tracked", "Hunter2ProdValue88" not in body)
    st = journal.fold(journal.read_events(T))
    live = journal.live_findings(st)
    check("curate aplicou o texto scrubbed", any("‹cofre:" in f["text"] for f in live))
    shutil.rmtree(T, ignore_errors=True)


def test_orphan_commit():
    print("\n== journal — last_commit órfão (rebase/amend) re-minera ==")
    T = "/tmp/pdtest_orphan"
    shutil.rmtree(T, ignore_errors=True)
    os.makedirs(os.path.join(T, ".claude", ".project-doc"))
    journal.state_dir = lambda pr: os.path.join(T, ".claude", ".project-doc")
    subprocess.run(["git", "-C", T, "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", T, "config", "user.email", "t@t"], check=True, capture_output=True)
    subprocess.run(["git", "-C", T, "config", "user.name", "t"], check=True, capture_output=True)
    open(os.path.join(T, "a.py"), "w").write("x\n")
    subprocess.run(["git", "-C", T, "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", T, "commit", "-qm", "feat: real commit subject"], check=True, capture_output=True)
    # ledger com last_commit órfão (sha que não existe)
    journal.save_ledger(T, {"mined_sessions": {}, "last_commit": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                            "distilled_hashes": {}})
    r = journal.run_update(T)
    check("commit órfão → re-minera (não perde commits)", r["new_events"] >= 1)
    shutil.rmtree(T, ignore_errors=True)


def test_engine_robust():
    print("\n== engine — tolerância a .jsonl não-UTF8 ==")
    import tempfile
    sys.path.insert(0, "/Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins/_shared")
    import collect_engine
    d = tempfile.mkdtemp()
    p = os.path.join(d, "bad.jsonl")
    with open(p, "wb") as fh:
        fh.write(b'{"type":"user","message":{"content":"ok"}}\n')
        fh.write(b'\x8e\x8f garbage non-utf8 \xff\xfe\n')
        fh.write(b'{"type":"user"}\n')
    recs = collect_engine.read_jsonl(p)            # não pode levantar UnicodeDecodeError
    check("read_jsonl tolera byte não-UTF8 (não quebra)", isinstance(recs, list) and len(recs) >= 1)
    cwd = collect_engine._first_cwd(p)             # idem
    check("_first_cwd tolera byte não-UTF8", cwd is None or isinstance(cwd, str))
    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
def test_cofre():
    print("\n== cofre — integridade ==")
    shutil.rmtree("/tmp/pdtest_cofre", ignore_errors=True)
    T = "/tmp/pdtest_proj"
    shutil.rmtree(T, ignore_errors=True)
    os.makedirs(T)
    # #7: mesma chave, dois valores → ambos no cofre, placeholders distintos
    s1, sec1 = journal.scrub("API_KEY=valuomyzAAAAAAAA111")
    s2, sec2 = journal.scrub("API_KEY=valuomyzBBBBBBBB222")
    journal.stash_secrets(sec1, T)
    journal.stash_secrets(sec2, T)
    _, cofre = journal.cofre_paths(T)
    body = open(cofre, encoding="utf-8").read()
    check("#7 dois valores da mesma chave coexistem no cofre",
          "valuomyzAAAAAAAA111" in body and "valuomyzBBBBBBBB222" in body)
    check("#7 placeholders distintos (hash do valor)", s1 != s2 and "‹cofre:API_KEY:" in s1)

    # #8: dois projetos de mesmo basename → arquivos de cofre distintos
    _, c_a = journal.cofre_paths("/tmp/aaa/client")
    _, c_b = journal.cofre_paths("/tmp/bbb/client")
    check("#8 basename igual → cofre distinto (path no nome)", c_a != c_b)
    shutil.rmtree(T, ignore_errors=True)


# ---------------------------------------------------------------------------
def test_finding_id():
    print("\n== finding_id — sem colisão de 64 chars ==")
    prefix = "x" * 64
    a = journal.finding_id(prefix + " rejeitar email vazio", "user_directive")
    b = journal.finding_id(prefix + " rejeitar senha curta", "user_directive")
    check("#11 textos com mesmo prefixo de 64 → ids diferentes", a != b)


# ---------------------------------------------------------------------------
def test_self_path_match():
    print("\n== self_path_match — precisão ==")
    check("#10 basename ambíguo (2 hits) não casa",
          journal.self_path_match("config.json", {"a/config.json", "b/config.json"}) is False)
    check("#10 basename único casa",
          journal.self_path_match("config.json", {"a/config.json"}) is True)
    check("#10 sufixo de path casa",
          journal.self_path_match("lib/journal.py", {"plugins/project-doc/lib/journal.py"}) is True)
    check("#10 path não-relacionado não casa",
          journal.self_path_match("lib/journal.py", {"other/x.py"}) is False)


# ---------------------------------------------------------------------------
def _git(T, *a):
    subprocess.run(["git", "-C", T, *a], check=True, capture_output=True)


def test_journal_cycle():
    print("\n== journal — delta / backward / invalidate ==")
    T = "/tmp/pdtest_repo"
    shutil.rmtree(T, ignore_errors=True)
    os.makedirs(os.path.join(T, ".claude"))
    journal.state_dir = lambda pr: os.path.join(T, ".claude", ".project-doc")  # estado fora do repo real
    _git(T, "init", "-q"); _git(T, "config", "user.email", "t@t"); _git(T, "config", "user.name", "t")
    open(os.path.join(T, "rules.py"), "w").write("rule v1\n")
    _git(T, "add", "-A"); _git(T, "commit", "-qm", "init rules.py")
    open(os.path.join(T, ".claude", "HANDOFF.md"), "w").write(
        "# Handoff\n## Findings & Gotchas\n"
        "- O hook vai em hooks/hooks.json, nunca na raiz — comportamento ligado a rules.py do projeto\n")
    _git(T, "add", "-A"); _git(T, "commit", "-qm", "add handoff")

    r1 = journal.run_update(T)
    check("delta run1 descobre findings", r1["new_events"] >= 3)
    r2 = journal.run_update(T)
    check("delta idempotente (run2 = 0)", r2["new_events"] == 0)

    hf = [f for f in r2["live"] if f["raw_kind"] == "handoff"][0]

    # backward via COMMIT: muda rules.py e commita
    open(os.path.join(T, "rules.py"), "w").write("rule v2\n")
    _git(T, "add", "-A"); _git(T, "commit", "-qm", "change rules.py")
    r3 = journal.run_update(T)
    new_commit_ids = [e for e in r3["stale_ids"]]
    check("#8 backward não auto-marca a finding de commit nova",
          hf["id"] in r3["stale_ids"]
          and not any(f["raw_kind"] == "commit" and f["source"]["ts"] and f["id"] in r3["stale_ids"]
                      and "change rules.py" in f["text"] for f in r3["live"]))
    check("#9 backward marca o handoff pré-existente (commit)", hf["id"] in r3["stale_ids"])

    # backward via WORKING-TREE: edição não commitada
    open(os.path.join(T, "rules.py"), "w").write("rule v3 uncommitted\n")
    r4 = journal.run_update(T)
    check("#9 backward marca via working-tree (sem commit novo)", hf["id"] in r4["stale_ids"])

    # invalidate id bom × id ruim
    bad = journal.run_invalidate(T, "deadbeefdeadbeef", "x")
    check("#14 invalidate em id inexistente → erro", bad.get("error") is not None)
    good = journal.run_invalidate(T, hf["id"], "rules.py mudou")
    check("#14 invalidate em id real → mata", good.get("alive") is False)
    cur_bad = journal.run_curate(T, "naoexiste00000000", "texto")
    check("#14 curate em id inexistente → erro", cur_bad.get("error") is not None)

    # journal só cresce: discovered preservado
    events = [json.loads(l) for l in open(os.path.join(T, ".claude", ".project-doc", "findings.jsonl")) if l.strip()]
    evs = [e["ev"] for e in events if e.get("id") == hf["id"] or e.get("target") == hf["id"]]
    check("journal só cresce (discovered + invalidated coexistem)", "discovered" in evs and "invalidated" in evs)
    shutil.rmtree(T, ignore_errors=True)


# ---------------------------------------------------------------------------
def test_scrubber_jwt():
    print("\n== scrubber — JWT (classe do PRD que estava sem fixture) ==")
    # canário bem-formado (header.payload.signature); NÃO é token real.
    jwt = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
           "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkNhbmFyaW8ifQ."
           "s1gn4tur3CanarioDummyABCDEF0123")
    payload = "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkNhbmFyaW8ifQ"

    # (a) JWT após palavra-sinal → corpo some e vira ‹cofre:JWT:…›
    s, _ = journal.scrub("o token de sessão é " + jwt + " e expira amanhã")
    check("JWT: payload não sobrevive", payload not in s)
    check("JWT: vira placeholder de cofre JWT", "‹cofre:JWT:" in s)

    # (a2) JWT isolado, SEM palavra-sinal por perto → a camada 1 (JWT_RE) pega sozinha
    s, _ = journal.scrub("deploy log: " + jwt + " fim")
    check("JWT: redigido sem depender de palavra-sinal", jwt not in s and "‹cofre:JWT:" in s)

    # (b) fronteira: 'eyJ' curto sem os 3 segmentos NÃO é JWT → preservado intacto
    s, _ = journal.scrub("o id eyJabc não é um token completo")
    check("quase-JWT curto preservado (não casa JWT_RE)", "eyJabc" in s and "‹" not in s)

    # (b2) fronteira: 2 segmentos (falta a assinatura) não vira ‹cofre:JWT› — JWT_RE exige 3
    s, _ = journal.scrub("header eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ sem assinatura")
    check("2-segmentos não vira ‹cofre:JWT› (regex exige 3)", "‹cofre:JWT:" not in s)


if __name__ == "__main__":
    test_scrubber()
    test_scrubber_r2()
    test_scrubber_r3()
    test_scrubber_r4()
    test_scrubber_r5()
    test_scrubber_r6()
    test_scrubber_r7()
    test_scrubber_jwt()
    test_curate_scrub()
    test_orphan_commit()
    test_engine_robust()
    test_cofre()
    test_finding_id()
    test_self_path_match()
    test_journal_cycle()
    print("\nTODOS OS %d CHECKS PASSARAM" % PASS)
