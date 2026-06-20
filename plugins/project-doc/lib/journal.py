#!/usr/bin/env python3
"""
journal.py — coleta multi-fonte + journal append-only + delta do project-doc v3.

A PARTE MECÂNICA da doc (a projeção/julgamento fica no SKILL.md):
  • Coleta a cascata de fontes (RF1):
      tier 2  memory/*.md, .claude/HANDOFF*.md  → raw_kind memory/handoff
      tier 3  git log (mensagens + arquivos)    → raw_kind commit
      tier 4  transcripts .jsonl (via engine)   → raw_kind user_directive/tool_rejection/ask_answer
    (tier 1 = scan de arquivo e tier 5 = perguntar ao humano vivem no SKILL.)
  • Journal append-only (RF2): .claude/.project-doc/findings.jsonl — eventos
    discovered/invalidated/curated; NUNCA reescreve. O estado vivo = fold dos eventos.
  • Delta de 2 direções (RF4): ledger .claude/.project-doc/ledger.json
      forward  = sessões novas + commits novos → discovered
      backward = git diff → findings cujas anchors mudaram → marcados `stale`
                 (re-validação é JULGAMENTO do agente; o lib não auto-invalida)
  • Scrubber + cofre (RF5): roda na escrita do journal (barreira p/ o git). Move o
    VALOR-secreto pro cofre (iCloud), preserva nome/host/porta/contexto.

A camada de transcript vem de collect_engine.py (vendorado como sibling por
scripts/sync-shared.sh). Degrada graciosamente: sem a engine, pula o tier 4.

CLI:
  journal.py update  --project-root D [--session ID]   # delta forward+backward
  journal.py deep    --project-root D                  # minera TODAS as sessões
  journal.py rebuild --project-root D                  # re-fold do journal inteiro
  journal.py fold    --project-root D                  # só imprime findings vivos
  journal.py invalidate --project-root D --id ID --reason "..."   # agente confirma morte
  journal.py scrub-test                                # smoke test do scrubber (stdin)
"""
import argparse, hashlib, json, math, os, re, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from collect_engine import (  # noqa: E402
        anchor_of, collect, cwd_to_projects_subdir, discover_all_transcripts,
        finding_id, read_jsonl, resolve_project_root,
    )
    HAVE_ENGINE = True
except ImportError:
    HAVE_ENGINE = False
    def anchor_of(text, n=64):
        return re.sub(r"\s+", " ", (text or "")).strip().lower()[:n]
    # MANTER idêntica a collect_engine.finding_id: id = hash(texto completo normalizado + kind).
    # Hashear o texto inteiro (não a âncora de 64 chars) evita colisão entre falas que só
    # compartilham o prefixo. Qualquer divergência aqui re-chavearia o journal.
    def finding_id(text, raw_kind):
        norm = re.sub(r"\s+", " ", (text or "")).strip().lower()
        return hashlib.sha1(("%s|%s" % (norm, raw_kind)).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Estado: .claude/.project-doc/  (versionado — é o veículo do conhecimento)
# ---------------------------------------------------------------------------
def state_dir(project_root):
    return os.path.join(project_root, ".claude", ".project-doc")


def journal_path(project_root):
    return os.path.join(state_dir(project_root), "findings.jsonl")


def ledger_path(project_root):
    return os.path.join(state_dir(project_root), "ledger.json")


def load_ledger(project_root):
    try:
        with open(ledger_path(project_root), encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError):
        d = {}
    # mined_sessions é {sid: mtime_do_jsonl} — re-minera uma sessão que CRESCEU desde a última
    # vez (não só "vista uma vez"), o que evita perder falas adicionadas depois numa sessão que
    # deixou de ser a ativa. Migra o formato antigo (lista) → mtime 0 (força re-mineração).
    ms = d.get("mined_sessions")
    if isinstance(ms, list):
        ms = {sid: 0 for sid in ms}
    elif not isinstance(ms, dict):
        ms = {}
    d["mined_sessions"] = ms
    d.setdefault("last_commit", None)
    d.setdefault("distilled_hashes", {})
    return d


def save_ledger(project_root, ledger):
    os.makedirs(state_dir(project_root), exist_ok=True)
    with open(ledger_path(project_root), "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2)


def read_events(project_root):
    return read_jsonl(journal_path(project_root)) if HAVE_ENGINE else _read_jsonl_fallback(journal_path(project_root))


def _read_jsonl_fallback(path):
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        pass
    return out


def append_events(project_root, events):
    if not events:
        return 0
    os.makedirs(state_dir(project_root), exist_ok=True)
    with open(journal_path(project_root), "a", encoding="utf-8") as fh:
        for e in events:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return len(events)


def fold(events):
    """Estado vivo = fold dos eventos por id, em ordem de append (cronológica).

    discovered cria; invalidated mata (sem apagar o discovered); curated sobrepõe
    o texto. Um id invalidado permanece morto mesmo que re-apareça num discovered
    posterior — o backward delta só invalida quando o código contradiz, então a
    morte é definitiva até uma curadoria/rediscovery explícita revivê-lo.
    """
    state = {}
    for e in events:
        ev = e.get("ev")
        if ev == "discovered":
            fid = e.get("id")
            if fid and fid not in state:
                state[fid] = {"id": fid, "raw_kind": e.get("raw_kind"),
                              "text": e.get("text", ""), "anchors": e.get("anchors", []),
                              "source": e.get("source", {}), "scrubbed": e.get("scrubbed", False),
                              "status": "live", "curated": None}
        elif ev == "invalidated":
            t = e.get("target")
            if t in state:
                state[t]["status"] = "invalidated"
                state[t]["invalid_reason"] = e.get("reason", "")
        elif ev == "curated":
            t = e.get("target")
            if t in state:
                state[t]["curated"] = e.get("text", "")
    return state


def live_findings(state):
    out = []
    for f in state.values():
        if f["status"] != "live":
            continue
        g = dict(f)
        if g.get("curated"):
            g["text"] = g["curated"]
        out.append(g)
    out.sort(key=lambda f: (f.get("source") or {}).get("ts", ""))
    return out


# ---------------------------------------------------------------------------
# Scrubber + cofre (RF5) — a barreira entre conversa-verbatim e git.
# SCORER EM CAMADAS (cada span redigido vira ‹cofre:…› e é pulado pelas seguintes):
#   1. estruturado: PEM → connection string → JWT → prefixos de provider
#   2. chave=valor de UMA linha (chave-secreta; numérico incluso; PUBLIC só palavra inteira)
#   3. prosa: palavra-secreta perto de um token de alta entropia (o input dominante)
#   4. na dúvida: token de alta entropia ⇒ marca ‹revisar?› (preserva, sinaliza p/ check #10)
# Política: nomes e contexto SIM, valores NÃO. Host/IP/porta/path/sha/uuid: preservados.
# ---------------------------------------------------------------------------
# Chave-secreta detectada por TOKEN (split em [^A-Za-z0-9]), não substring — senão AUTH casa
# AUTHOR/OAUTH, PASS casa COMPASS/BYPASS, CHAVE casa CHAVEIRO (over-redação de valor benigno).
SECRET_WORDS = frozenset({
    "SECRET", "SENHA", "SENHAS", "PASSWORD", "PASSWORDS", "PASSWD", "PASS", "PASSPHRASE", "PWD",
    "TOKEN", "TOKENS", "AUTH", "CREDENTIAL", "CREDENTIALS", "CREDENCIAL", "CREDENCIAIS",
    "CHAVE", "CHAVES", "BEARER", "APIKEY", "PAT"})
# Termos distintivos o bastante p/ casar por SUBSTRING (pega chave colada SECRETVALUE/APIKEYVALUE
# que o match-por-token perderia; colisão com palavra comum, tipo SECRETARY, é rara e a redação é
# segura). Os fracos (PASS/AUTH/...) ficam só no token-match acima (senão AUTH casaria AUTHOR).
STRONG_SECRET = ("SECRET", "PASSWORD", "PASSWD", "PASSPHRASE", "APIKEY",
                 "CREDENTIAL", "CREDENCIAL", "CREDENCIAIS",
                 # formas COLADAS (camelCase→upper) que o match-por-token perderia:
                 "PRIVATEKEY", "MASTERKEY", "ACCESSKEY", "SIGNINGKEY", "ENCRYPTIONKEY",
                 "AUTHTOKEN", "ACCESSTOKEN", "REFRESHTOKEN", "APITOKEN")
# Qualificadores que, junto de KEY, formam chave-secreta composta (API_KEY, ACCESS_KEY, ...).
KEY_QUALIFIER = frozenset({"API", "ACCESS", "SESSION", "PRIVATE", "SIGNING", "SECRET",
                           "ENCRYPTION", "AES", "RSA", "CLIENT", "REFRESH", "MASTER"})
# Sufixo que torna a chave um LOCALIZADOR/rótulo, não o valor-secreto: PASSWORD_POLICY_URL,
# SECRET_FILE, TOKEN_NAME — o valor é uma URL/path/nome (contexto), não a credencial.
NON_SECRET_SUFFIX = frozenset({
    "URL", "URI", "LINK", "ENDPOINT", "HOST", "HOSTNAME", "PORT", "USER", "USERNAME", "NAME",
    "PATH", "FILE", "DIR", "DOC", "DOCS", "POLICY", "HINT", "LABEL", "ID", "TYPE", "ALGO",
    "ALGORITHM", "ENABLED", "EXPIRY", "EXPIRES", "TTL", "COUNT", "VERSION"})
# Placeholders óbvios — NÃO inclui número puro (numérico sob chave-secreta É secret).
PLACEHOLDER_RE = re.compile(
    r"^(\$\{.*\}|<.*>|x{2,}|\*{2,}|\.\.\.|changeme|placeholder|example|sample|"
    r"your[_-].*|none|null|true|false)$", re.I)
# key=value numa ÚNICA linha: [^\S\n]* não atravessa \n (senão um `k:`\n antes de um PEM o mutilava).
# val captura command-substitution ($(...) / `...`) como unidade (o segredo mora lá dentro, com
# espaços) antes de cair no token sem-espaço padrão.
ASSIGN_RE = re.compile(
    # `pre` = chave (com aspas opcionais, p/ JSON "password":) + separador, preservado na saída.
    r"(?P<pre>[\"']?(?P<key>[A-Za-z][A-Za-z0-9_.\-]{1,40})[\"']?[^\S\n]*[:=][^\S\n]*)"
    # valor entre aspas é capturado COM as aspas (e pode conter a aspa oposta), depois
    # command-subst até EOL, backtick, e por fim o token sem-espaço. O token nu inclui aspas
    # ([^\s], não [^\s"']) — senão aspa no meio/aberta cortava o valor e vazava o resto.
    r"(?P<val>\"[^\"\n]*\"|'[^'\n]*'|\$\([^\n]*|`[^\n]*|[^\s]+)")
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]+")
PEM_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----")
# Connection string com credencial embutida: QUALQUER scheme (allowlist deixava clickhouse/mssql/
# … vazar, já que as camadas 3/4 pulam tokens com '://').
# usuário OPCIONAL ([^\s:@/]*): redis://:senha@ / amqp://:senha@ (forma padrão sem user) vazavam.
CONN_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.\-]*://[^\s:@/]*:(?P<pw>[^\s:@/]+)@")
# Palavra-esquema que NÃO é o segredo (o token seguinte é): `Authorization: Bearer <tok>`.
SCHEME_WORD_RE = re.compile(r"(?:bearer|token|basic|bot|apikey)", re.I)
# Par JSON/dict `"chave": "valor"` — casa o par INTERNO em qualquer profundidade (o ASSIGN
# falha no JSON aninhado de uma linha porque a chave externa engole o par interno via finditer
# não-sobreposto). jval NÃO atravessa {}[] (senão a chave externa o engoliria de novo).
JSON_PAIR_RE = re.compile(
    r"""(["'])(?P<jkey>[A-Za-z][A-Za-z0-9_.\-]{1,40})\1\s*:\s*"""
    r"""(?P<jval>"[^"\n]*"|'[^'\n]*'|[^\s,{}\[\]]+)""")
# Prefixos de provider de alta confiança (token inteiro), pegos em QUALQUER lugar (prosa incl.).
PROVIDER_RE = re.compile(
    r"(?:AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}"
    r"|gh[posu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-[A-Za-z0-9]{20,}|sk_live_[A-Za-z0-9]{16,}|sk_test_[A-Za-z0-9]{16,}|rk_live_[A-Za-z0-9]{16,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|glpat-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,}|ya29\.[A-Za-z0-9_-]{20,})")
# Camada 3 (prosa): palavra que sinaliza segredo logo antes do valor.
SIGNAL_RE = re.compile(
    r"\b(senhas?|passwords?|passwd|secrets?|tokens?|api[\s_-]?keys?|"
    r"credenci(?:al|ais)|credentials?|chaves?|bearer)\b", re.I)
# Allowlist benigno (camada 4, SEM sinal por perto) — preserva sha/hex, uuid, IPv4, path, versão.
BENIGN_RE = re.compile(
    r"^(?:[0-9a-fA-F]{7,40}"
    r"|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|\d{1,3}(?:\.\d{1,3}){3}"
    r"|[\w.\-/]+\.[A-Za-z0-9]{1,6}"
    r"|\d[\d.,:_-]*)$")
# Contexto a preservar MESMO logo após uma palavra-sinal (camada 3): path, arquivo de extensão
# CONHECIDA, IP, uuid, versão/número. Hex-puro-com-letras NÃO entra: depois de "token is" ele é
# o segredo, não um sha de contexto (essa é a diferença pra BENIGN_RE da camada 4).
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_NUMVER_RE = re.compile(r"^\d[\d.,:_-]*$")
KNOWN_EXT = frozenset({
    "py", "js", "ts", "tsx", "jsx", "mjs", "cjs", "md", "json", "yaml", "yml", "toml", "cfg",
    "ini", "html", "css", "scss", "sql", "go", "rs", "rb", "java", "sh", "bash", "txt", "png",
    "jpg", "jpeg", "gif", "svg", "webp", "pdf", "csv", "xml", "log", "lock", "env", "conf",
    "pem", "pub", "gz", "zip", "tar", "tgz", "db", "sqlite"})


def _is_context_token(core):
    # NÃO inclui '/' aqui: um slash-secret de alta entropia (wJalr/K7.../...) é tratado pela
    # lógica is_cred (que exige _looks_random p/ tokens com '/'); um path de baixa entropia
    # cai como não-cred e é preservado de qualquer forma.
    if _UUID_RE.match(core) or _IPV4_RE.match(core) or _NUMVER_RE.match(core):
        return True
    m = re.search(r"\.([A-Za-z0-9]{1,6})$", core)
    return bool(m and m.group(1).lower() in KNOWN_EXT)
# Token candidato na prosa: começa em alfanumérico (sem pontuação à esquerda), permite
# caracteres especiais internos (p@ssw0rd!), mín. 4 chars.
PROSE_TOK_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9@!#$%^&*_+./=~-]{3,}")
LONGTOK_RE = re.compile(r"[^\s\"'`,;‹›]{16,}")  # candidato à marcação por dúvida (exclui ‹› de placeholder)
# Stopwords (PT+EN) puladas ao procurar o valor depois da palavra-sinal.
STOPWORDS = {"de", "do", "da", "is", "e", "the", "a", "o", "and", "or", "to", "for",
             "was", "são", "será", "em", "no", "na", "que", "of", "um", "uma", "with", "are"}


def _shannon(s):
    if not s:
        return 0.0
    counts = {}
    for c in s:
        counts[c] = counts.get(c, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _looks_random(tok):
    return (len(tok) >= 16 and _shannon(tok) >= 3.5
            and bool(re.search(r"[A-Za-z]", tok)) and bool(re.search(r"\d", tok)))


def _is_benign(tok):
    return bool(BENIGN_RE.match(tok))


def _is_placeholder(v):
    v = (v or "").strip()
    return not v or bool(PLACEHOLDER_RE.match(v))


def _vhash(val):
    return hashlib.sha1(val.encode("utf-8")).hexdigest()[:8]


def _is_secret_key(key):
    """True se o NOME da chave indica segredo.

    Sem curto-circuito de PUBLIC: PUBLIC_KEY não tem termo secreto nem KEY+qualificador, então
    cai no return False naturalmente; já PUBLIC_SECRET TEM 'SECRET' (forte) → segredo. O antigo
    `if PUBLIC: return False` vazava PUBLIC_SECRET.
    """
    up = key.upper()
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", up) if t]
    if toks and toks[-1] in NON_SECRET_SUFFIX:  # *_URL/_FILE/_NAME = localizador, não o segredo
        return False
    if any(w in up for w in STRONG_SECRET):     # termo distintivo → substring (SECRETVALUE etc.)
        return True
    if any(t in SECRET_WORDS for t in toks):    # termo fraco → só por token (AUTH ≠ AUTHOR)
        return True
    if "KEY" in toks and any(t in KEY_QUALIFIER for t in toks):   # API_KEY, ACCESS_KEY, ...
        return True
    return False


def scrub(text):
    """Scorer em camadas. Devolve (texto_scrubbed, [(cofre_key, valor)]).

    cofre_key = "<LABEL>:<8hex(valor)>" — o placeholder ‹cofre:LABEL:hash› e a linha do
    cofre carregam o hash do valor, então o mapeamento placeholder→valor é sempre exato
    (mesma chave com 2 valores não colide; mesmo valor dedupa).
    """
    text = text or ""   # None guard — candidato malformado não derruba o scrub
    secrets = []

    def stash(label, val):
        key = "%s:%s" % (label, _vhash(val))
        secrets.append((key, val))
        return "‹cofre:%s›" % key

    # --- Camada 1: estruturado. PEM PRIMEIRO (antes do ASSIGN, p/ o `k:`+\n não mutilar). ---
    text = PEM_RE.sub(lambda m: stash("PRIVATE_KEY", m.group(0)), text)

    def repl_conn(m):
        ph = stash("DB_PASSWORD", m.group("pw"))
        s = m.group(0)
        return s[:m.start("pw") - m.start()] + ph + s[m.end("pw") - m.start():]
    text = CONN_RE.sub(repl_conn, text)
    text = JWT_RE.sub(lambda m: stash("JWT", m.group(0)), text)
    text = PROVIDER_RE.sub(lambda m: stash("TOKEN", m.group(0)), text)

    # --- Camada 1.5: pares JSON/dict aninhados ("chave":"valor") em qualquer profundidade ---
    def repl_json(m):
        jkey, jval = m.group("jkey"), m.group("jval")
        if "‹cofre:" in jval or not _is_secret_key(jkey):
            return m.group(0)
        if len(jval) >= 2 and jval[0] in "\"'" and jval[-1] == jval[0]:
            q, inner = jval[0], jval[1:-1]
        else:
            q, inner = "", jval
        if SCHEME_WORD_RE.fullmatch(inner) or _is_placeholder(inner):
            return m.group(0)
        prefix = m.group(0)[:m.start("jval") - m.start()]   # preserva `"chave": `
        return prefix + q + stash(jkey, inner) + q
    text = JSON_PAIR_RE.sub(repl_json, text)

    # --- Camada 2: chave=valor de uma linha ---
    def repl_assign(m):
        key, val = m.group("key"), m.group("val")
        if "‹cofre:" in val:
            return m.group(0)
        if not _is_secret_key(key):
            return m.group(0)
        # destaca aspas: o valor interno pode conter a aspa oposta (DB_TOKEN="p4ss'w0rd").
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            q, inner = val[0], val[1:-1]
        else:
            q, inner = "", val
        # inner = palavra-esquema (Bearer) OU placeholder/markdown (**) → deixa a camada 3 pegar.
        if SCHEME_WORD_RE.fullmatch(inner) or _is_placeholder(inner):
            return m.group(0)
        return "%s%s%s%s" % (m.group("pre"), q, stash(key, inner), q)
    text = ASSIGN_RE.sub(repl_assign, text)

    # --- Camadas 3+4: span-based num único rebuild (evita índices deslocando) ---
    spans = []  # (start, end, replacement)
    # Mascara os ‹…› já redigidos (senão a palavra-sinal dentro de ‹cofre:API_KEY:…›
    # dispararia em cima do próprio hash). _covered = dentro de placeholder OU de span já criado
    # (impede dois sinais reivindicarem o mesmo token → corrupção/duplicação).
    protected = [(m.start(), m.end()) for m in re.finditer(r"‹[^›]*›", text)]

    def _covered(s, e):
        return (any(not (e <= ps or s >= pe) for ps, pe in protected)
                or any(not (e <= ss or s >= ee) for ss, ee, _ in spans))

    # 3) prosa: por palavra-sinal, acha o VALOR na janela. Prefere token credencial-shaped
    #    (redige → cofre); se só houver palavra comum longa, marca ‹revisar?› (na dúvida).
    for sm in SIGNAL_RE.finditer(text):
        if _covered(sm.start(), sm.end()):
            continue
        # O sinal precisa ser uma PALAVRA-rótulo (seguida de espaço/:/=), não um pedaço de um
        # valor composto: em `PUBLIC_KEY=ssh-not-secret-just`, "secret" é seguido de "-" → ignora
        # (senão a camada 3 redigiria "just", destruindo um valor que a camada 2 preservou).
        if text[sm.end():sm.end() + 1] not in ("", " ", "\t", "\n", ":", "=", "\"", "'"):
            continue
        # Sinal que é CHAVE estruturada já redigida (seguido de :/= e o valor já é ‹cofre›, ex.
        # JSON "password":‹cofre›): o valor desta chave já foi tratado — NÃO varrer, senão a
        # camada pegaria o valor do par VIZINHO ("host":"prod-db-7"). Sinal em prosa seguido de
        # placeholder por ESPAÇO (credentials ‹cofre› wJalr…) não casa aqui → segue normal.
        if re.match(r"""["']?[^\S\n]*[:=][^\S\n]*["']?‹cofre:""", text[sm.end():sm.end() + 40]):
            continue
        wstart = sm.end()
        # janela fixa: _covered() já pula tokens DENTRO de placeholder, então NÃO truncar no 1º ‹
        # — senão um provider-token redigido entre o sinal e o secret real (par AWS id+secret)
        # escondia o secret seguinte.
        wend = wstart + 160
        cred = plain = None
        for tm in PROSE_TOK_RE.finditer(text[wstart:wend]):
            core = tm.group(0).rstrip(".,:;")
            s = wstart + tm.start()
            e = s + len(core)
            if (not core or core.lower() in STOPWORDS or _is_context_token(core)
                    or _covered(s, e) or "://" in core or core[:1] == "/" or core[:2] in ("./", "~/")):
                continue
            has_special = bool(re.search(r"[^A-Za-z0-9/]", core))
            mixed = bool(re.search(r"\d", core)) and bool(re.search(r"[A-Za-z]", core))
            if "/" in core:
                is_cred = _looks_random(core)        # slash só é secret se for de fato aleatório (não path)
            else:
                is_cred = _looks_random(core) or has_special or (mixed and len(core) >= 6)
            if is_cred:
                cred = (s, e, core)
                break
            if plain is None and len(core) >= 12 and "/" not in core:
                plain = (s, e, core)
        if cred:
            spans.append((cred[0], cred[1], stash(sm.group(0).lower(), cred[2])))
        elif plain:                                  # palavra longa após o sinal: flag, não vault
            spans.append((plain[0], plain[1], plain[2] + "‹revisar?›"))

    # 4) na dúvida: token de alta entropia (≥16) não coberto → marca (não apaga, não vaza).
    # Não pula '/' em bloco (path de baixa entropia já cai fora por _is_benign / _looks_random);
    # senão um slash-secret de alta entropia sem sinal por perto (wJalr/K7.../...) passava batido.
    for tm in LONGTOK_RE.finditer(text):
        core = tm.group(0).rstrip(".,:;)]}")
        s, e = tm.start(), tm.start() + len(core)
        if _is_benign(core) or "://" in core or _covered(s, e):
            continue
        if _looks_random(core):
            spans.append((s, e, core + "‹revisar?›"))

    for s, e, rep in sorted(spans, key=lambda x: x[0], reverse=True):
        text = text[:s] + rep + text[e:]
    return text, secrets


def cofre_paths(project_root):
    # Override explícito (testes + máquina sem iCloud) > iCloud > fallback local gitignored.
    env = os.environ.get("PROJECT_DOC_COFRE_DIR")
    icloud = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
    if env:
        base = env
    elif os.path.isdir(icloud):
        base = os.path.join(icloud, "Cofre")
    else:
        base = os.path.join(project_root, ".claude", "secrets", "_local_cofre")
    # Nome pelo PATH COMPLETO (não só basename) — dois projetos de mesmo nome não colidem.
    pr = os.path.abspath(project_root)
    slug = "%s-%s" % (os.path.basename(pr) or "projeto", hashlib.sha1(pr.encode("utf-8")).hexdigest()[:8])
    return base, os.path.join(base, "%s.env" % slug)


def ensure_gitignore(project_root, entry):
    # Só faz sentido (e só não polui) num repo git — .git pode ser dir ou file (worktree).
    if not os.path.exists(os.path.join(project_root, ".git")):
        return
    gi = os.path.join(project_root, ".gitignore")
    content = ""
    try:
        with open(gi, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        pass
    if entry in content.splitlines():
        return
    sep = "" if (content == "" or content.endswith("\n")) else "\n"
    with open(gi, "a", encoding="utf-8") as fh:
        fh.write(sep + entry + "\n")


def stash_secrets(secrets, project_root):
    """Desvia valores pro cofre, dedup por (label,valor). Garante o gitignore ANTES de escrever."""
    if not secrets:
        return None
    # Protege primeiro: no fallback local o cofre cai dentro do repo — gitignore antes da escrita.
    ensure_gitignore(project_root, ".claude/secrets/")
    base, cofre = cofre_paths(project_root)
    os.makedirs(base, exist_ok=True)
    existing = set()
    if os.path.exists(cofre):
        try:
            for line in open(cofre, encoding="utf-8"):
                if "=" in line:
                    existing.add(line.split("=", 1)[0].strip())
        except OSError:
            pass
    with open(cofre, "a", encoding="utf-8") as fh:
        for key, val in secrets:
            if key in existing:
                continue
            # uma linha por secret — escapa newline (PEM é multilinha) p/ não quebrar o .env
            esc = val.replace("\\", "\\\\").replace("\n", "\\n")
            fh.write("%s=%s\n" % (key, esc))
            existing.add(key)
    # symlink no repo (gitignored) → cofre; recria se stale (cofre mudou de lugar).
    secrets_dir = os.path.join(project_root, ".claude", "secrets")
    os.makedirs(secrets_dir, exist_ok=True)
    link = os.path.join(secrets_dir, "ops.env")
    try:
        if os.path.lexists(link):
            if not os.path.islink(link) or os.readlink(link) != cofre:
                os.unlink(link)
                os.symlink(cofre, link)
        else:
            os.symlink(cofre, link)
    except OSError:
        pass
    return cofre


# ---------------------------------------------------------------------------
# Anchors — tokens de path no texto, p/ o backward delta cruzar com git diff.
# ---------------------------------------------------------------------------
ANCHOR_RE = re.compile(
    r"(?:[\w.\-]+/)+[\w.\-]+\.\w+"
    r"|[\w.\-]+\.(?:py|js|ts|tsx|jsx|md|sh|json|ya?ml|toml|cfg|ini|html|css|sql|go|rs|rb|java)\b")


def extract_anchors(text):
    return sorted(set(m.group(0) for m in ANCHOR_RE.finditer(text or "")))[:8]


# ---------------------------------------------------------------------------
# git helpers
# ---------------------------------------------------------------------------
def git(project_root, *args):
    try:
        r = subprocess.run(["git", "-C", project_root, *args],
                           capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def git_head(project_root):
    return git(project_root, "rev-parse", "HEAD").strip() or None


def _commit_reachable(project_root, sha):
    """True se `sha` ainda existe no repo. Um rebase/amend/reset órfana o last_commit do ledger;
    usá-lo como base de range (`orfão..HEAD`) faz o git sair 128 e perderíamos TODOS os commits."""
    return bool(git(project_root, "rev-parse", "--verify", "--quiet", "%s^{commit}" % sha).strip())


# ---------------------------------------------------------------------------
# Coletores por tier → candidatos crus {id, raw_kind, text, anchors, source}
# ---------------------------------------------------------------------------
def _candidate(raw_kind, text, source, anchors=None):
    text = (text or "").strip()
    if not text:
        return None
    return {"id": finding_id(text, raw_kind), "raw_kind": raw_kind, "text": text,
            "anchors": anchors if anchors is not None else extract_anchors(text),
            "source": source}


def collect_memory(project_root):
    """tier 2 — cada memory/*.md é um fato (o sistema de memória já garante 1/arquivo)."""
    out = []
    mem_dir = os.path.join(cwd_to_projects_subdir(project_root), "memory") if HAVE_ENGINE else None
    if not mem_dir or not os.path.isdir(mem_dir):
        return out
    for name in sorted(os.listdir(mem_dir)):
        if not name.endswith(".md") or name == "MEMORY.md":
            continue
        path = os.path.join(mem_dir, name)
        try:
            raw = open(path, encoding="utf-8").read()
        except OSError:
            continue
        body = re.sub(r"^---\n.*?\n---\n", "", raw, flags=re.S).strip()  # tira frontmatter
        ts = _iso(os.path.getmtime(path))
        c = _candidate("memory", body, {"type": "memory", "ref": name, "ts": ts})
        if c:
            out.append(c)
    return out


HANDOFF_SECTIONS = ("Findings & Gotchas", "Findings", "Gotchas", "Discussões e Decisões",
                    "Detalhes Técnicos", "Contexto Extra")


def collect_handoffs(project_root):
    """tier 2 — bullets das seções de conhecimento dos HANDOFF*.md."""
    out = []
    claude = os.path.join(project_root, ".claude")
    if not os.path.isdir(claude):
        return out
    import glob as _glob
    for path in sorted(_glob.glob(os.path.join(claude, "HANDOFF*.md"))):
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            continue
        ref = os.path.basename(path)
        ts = _iso(os.path.getmtime(path))
        in_section = False
        for line in text.splitlines():
            h = re.match(r"^#{2,3}\s+(.*)", line)
            if h:
                in_section = any(s.lower() in h.group(1).lower() for s in HANDOFF_SECTIONS)
                continue
            if not in_section:
                continue
            b = re.match(r"^\s*[-*]\s+(.*)", line)
            if b and len(b.group(1).strip()) > 20:
                c = _candidate("handoff", b.group(1), {"type": "handoff", "ref": ref, "ts": ts})
                if c:
                    out.append(c)
    return out


def collect_commits(project_root, since=None):
    """tier 3 — mensagens de commit (subject+body) + arquivos tocados como anchors."""
    out = []
    rng = ("%s..HEAD" % since) if since else "HEAD"
    fmt = "%H%x1f%cI%x1f%s%x1f%b%x1e"
    # Delta (since setado): sem teto — o range last..HEAD é pequeno e não pode perder commit.
    # Cold-start (since=None, full history): teto alto + aviso (sem corte silencioso).
    if since:
        log = git(project_root, "log", "--no-merges", "--pretty=format:" + fmt, rng)
        entries = [e for e in log.split("\x1e") if e.strip()]
    else:
        CAP = 1000
        # pede CAP+1 p/ saber se truncou DE VERDADE (count==CAP não é truncamento — o fmt põe
        # um \x1e depois de cada commit, inclusive o último).
        log = git(project_root, "log", "--no-merges", "-n", str(CAP + 1), "--pretty=format:" + fmt, rng)
        entries = [e for e in log.split("\x1e") if e.strip()]
        if len(entries) > CAP:
            entries = entries[:CAP]
            print("collect_commits: cold-start truncado em %d commits; os mais antigos não viraram "
                  "findings (rode --deep depois ou aumente o teto)." % CAP, file=sys.stderr)
    for entry in entries:
        parts = entry.strip().split("\x1f")
        if len(parts) < 3:
            continue
        sha, cdate, subj = parts[0], parts[1], parts[2]
        body = parts[3] if len(parts) > 3 else ""
        files = [f for f in git(project_root, "show", "--name-only", "--pretty=format:", sha).splitlines() if f.strip()]
        text = (subj + ("\n" + body if body.strip() else "")).strip()
        c = _candidate("commit", text, {"type": "commit", "ref": sha[:12], "ts": cdate}, anchors=files[:8])
        if c:
            out.append(c)
    return out


def collect_transcripts(project_root, mined_sessions, active_session=None, deep=False):
    """tier 4 — minera sessões novas OU que cresceram (mtime > último minerado) + a ativa.

    mined_sessions = {sid: mtime}. seen = {sid: mtime_atual}. Re-minerar por mtime (em vez de
    'já vista') garante que falas adicionadas a uma sessão depois que ela deixou de ser a ativa
    ainda entrem na próxima rodada — sem precisar de --deep.
    """
    if not HAVE_ENGINE:
        return [], {}
    seen = {}
    out = []
    for tp in discover_all_transcripts(project_root):
        sid = os.path.splitext(os.path.basename(tp))[0]
        try:
            mtime = os.path.getmtime(tp)
        except OSError:
            continue
        seen[sid] = mtime
        grew = mtime > mined_sessions.get(sid, -1.0)
        if not deep and not grew and sid != active_session:
            continue
        for it in collect(read_jsonl(tp), source_tag="transcript"):
            if not it.get("gate"):
                continue
            if it["kind"] == "ask_answer":
                text = "P: %s\nR: %s" % (it.get("question", ""), it.get("answer", ""))
            else:
                text = it.get("text", "") or ""
            c = _candidate(it["kind"], text, {"type": "transcript", "ref": sid, "ts": it.get("ts", "")})
            if c:
                out.append(c)
    return out, seen


def _iso(unix_ts):
    import datetime
    return datetime.datetime.utcfromtimestamp(unix_ts).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Orquestração: delta → scrubber → append → fold
# ---------------------------------------------------------------------------
def run_update(project_root, active_session=None, deep=False, rebuild=False):
    events_existing = read_events(project_root)
    state = fold(events_existing)
    if rebuild:
        return {"mode": "rebuild", "new_events": 0, "live_count": len(live_findings(state)),
                "stale_ids": [], "live": live_findings(state)}

    ledger = load_ledger(project_root)
    known_ids = set(state.keys())
    head = git_head(project_root)

    # last_commit órfão (rebase/amend/reset reescreveu a história) → trata como cold-start,
    # senão `git log orfão..HEAD` sai 128 e perderíamos todos os commits do range.
    last_commit = ledger.get("last_commit")
    if last_commit and not _commit_reachable(project_root, last_commit):
        last_commit = None

    # --- forward: junta candidatos de todas as fontes ---
    candidates = []
    candidates += collect_memory(project_root)
    candidates += collect_handoffs(project_root)
    candidates += collect_commits(project_root, since=None if deep else last_commit)
    tx, seen = collect_transcripts(project_root, ledger.get("mined_sessions", {}),
                                   active_session=active_session, deep=deep)
    candidates += tx

    # --- novos (id inédito no journal): scrubber → discovered ---
    now = int(time.time())
    new_events = []
    added_ids = set()
    for c in candidates:
        if c["id"] in known_ids or c["id"] in added_ids:
            continue
        scrubbed_text, secrets = scrub(c["text"])
        if secrets:
            stash_secrets(secrets, project_root)
        new_events.append({"ev": "discovered", "id": c["id"], "raw_kind": c["raw_kind"],
                           "text": scrubbed_text, "anchors": c["anchors"], "source": c["source"],
                           "scrubbed": bool(secrets), "ts": now})
        added_ids.add(c["id"])

    # --- backward: anchors tocadas por mudanças recentes → marca stale (julgamento é do agente).
    # Mudanças = commits novos (last..HEAD) UNIÃO working-tree (edição ainda não commitada,
    # o fluxo típico de mexer no código e rodar antes de commitar). Só sinaliza findings
    # PRÉ-existentes (state) — nunca auto-marca os recém-descobertos nesta mesma rodada.
    stale_ids = []
    changed = set()
    if last_commit and head and last_commit != head:
        changed |= {f for f in git(project_root, "diff", "%s..HEAD" % last_commit, "--name-only").splitlines() if f.strip()}
    changed |= {f for f in git(project_root, "diff", "--name-only").splitlines() if f.strip()}
    changed |= {f for f in git(project_root, "diff", "--cached", "--name-only").splitlines() if f.strip()}
    if changed:
        for fid, f in state.items():  # state = fold(events_existing): só os pré-existentes
            if f["status"] != "live":
                continue
            if any(self_path_match(a, changed) for a in (f.get("anchors") or [])):
                stale_ids.append(fid)

    append_events(project_root, new_events)
    # atualiza ledger: mtime atual de cada sessão vista; last_commit = HEAD
    if seen:
        ledger["mined_sessions"].update(seen)
    if head:
        ledger["last_commit"] = head
    save_ledger(project_root, ledger)

    # final_state = fold do que já temos em memória (events_existing + new_events) — não re-lê
    # o journal do disco (era a 3ª leitura/2º fold por rodada).
    final_state = fold(events_existing + new_events)
    live = live_findings(final_state)
    return {"mode": "deep" if deep else "update", "new_events": len(new_events),
            "live_count": len(live), "stale_ids": stale_ids, "live": live}


def self_path_match(anchor, changed_paths):
    """anchor casa um path mudado por SUFIXO de caminho. Basename puro (sem '/') é
    ambíguo — só casa se EXATAMENTE 1 arquivo mudado tem aquele nome; senão não marca
    (evita 'config.json'/'index.ts' marcarem stale qualquer arquivo homônimo no monorepo)."""
    a = (anchor or "").lstrip("./")
    if not a:
        return False
    if "/" in a:
        # Só a direção "o anchor é sufixo do path mudado". A inversa (a.endswith('/'+p))
        # deixava um arquivo de raiz homônimo (changed='config.json') casar um anchor aninhado
        # (plugins/foo/config.json) — exatamente o falso-positivo que o guard quer evitar.
        for p in changed_paths:
            p = p.lstrip("./")
            if p == a or p.endswith("/" + a):
                return True
        return False
    hits = [p for p in changed_paths if os.path.basename(p.rstrip("/")) == a]
    return len(hits) == 1


def run_invalidate(project_root, fid, reason):
    # Erra alto se o id não existe — id errado não pode gravar evento órfão e fingir sucesso.
    if fid not in fold(read_events(project_root)):
        return {"mode": "invalidate", "error": "id não encontrado no journal", "id": fid}
    # reason vai pro journal git-tracked → passa pelo scrubber (mesma barreira do discovered).
    reason_scrubbed, secrets = scrub(reason or "agente: contradito pelo código")
    if secrets:
        stash_secrets(secrets, project_root)
    append_events(project_root, [{"ev": "invalidated", "target": fid,
                                  "reason": reason_scrubbed, "ts": int(time.time())}])
    state = fold(read_events(project_root))
    return {"mode": "invalidate", "id": fid, "alive": (state.get(fid, {}).get("status") == "live"),
            "live_count": len(live_findings(state))}


def run_curate(project_root, fid, text):
    """Edição humana de um finding — vira evento curated; a projeção a respeita."""
    if fid not in fold(read_events(project_root)):
        return {"mode": "curate", "error": "id não encontrado no journal", "id": fid}
    # texto curado vai pro journal git-tracked → MESMA barreira do scrubber que o discovered.
    text_scrubbed, secrets = scrub(text)
    if secrets:
        stash_secrets(secrets, project_root)
    append_events(project_root, [{"ev": "curated", "target": fid, "text": text_scrubbed, "ts": int(time.time())}])
    state = fold(read_events(project_root))
    return {"mode": "curate", "id": fid, "live_count": len(live_findings(state))}


def main():
    ap = argparse.ArgumentParser(description="project-doc journal/delta")
    ap.add_argument("mode", choices=["update", "deep", "rebuild", "fold", "invalidate", "curate", "scrub-test"])
    ap.add_argument("--project-root", default=None)
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--session", default=None)
    ap.add_argument("--id", default=None)
    ap.add_argument("--reason", default=None)
    ap.add_argument("--text", default=None)
    args = ap.parse_args()

    if args.mode == "scrub-test":
        text = sys.stdin.read()
        scrubbed, secrets = scrub(text)
        print(json.dumps({"scrubbed": scrubbed, "secrets_keys": [k for k, _ in secrets]},
                         ensure_ascii=False, indent=2))
        return 0

    project_root = args.project_root or (resolve_project_root(args.cwd) if HAVE_ENGINE else None) or os.path.abspath(args.cwd)

    if args.mode == "invalidate":
        if not args.id:
            print("ERRO: --id obrigatório no modo invalidate", file=sys.stderr)
            return 2
        res = run_invalidate(project_root, args.id, args.reason)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 1 if res.get("error") else 0

    if args.mode == "curate":
        if not args.id or args.text is None:
            print("ERRO: --id e --text obrigatórios no modo curate", file=sys.stderr)
            return 2
        res = run_curate(project_root, args.id, args.text)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 1 if res.get("error") else 0

    if args.mode == "fold":
        state = fold(read_events(project_root))
        print(json.dumps({"mode": "fold", "live_count": len(live_findings(state)),
                          "live": live_findings(state)}, ensure_ascii=False, indent=2))
        return 0

    res = run_update(project_root, active_session=args.session,
                     deep=(args.mode == "deep"), rebuild=(args.mode == "rebuild"))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
