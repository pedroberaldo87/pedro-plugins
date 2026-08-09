#!/usr/bin/env python3
"""
doc_lint.py — lint MECÂNICO de conteúdo dos docs project-doc (v3.11).

Verifica afirmações da doc contra o repo real — as classes de erro que a
auditoria de 2026-07-22 mostrou serem 68% do drift:

  1. env-var cross-check — nome UPPER_SNAKE citado na doc que NENHUM arquivo do
     repo lê como env nem contém como identificador → FAIL (se env-shaped) /
     WARN. O árbitro é o repo (3 camadas), sem denylist mágica.
  2. hash de commit — token hex que não resolve em `git cat-file` → FAIL (se a
     linha fala de commit) / WARN (pode ser finding_id do journal).
  3. ponteiro arquivo:N — arquivo inexistente ou N > nº de linhas → FAIL
     (ponteiro comprovadamente morto). Vivo → 1 WARN brando por doc.
  3b. ponteiro para arquivo que existe SÓ no disco de quem escreveu (ausente do
     tronco — não commitado) → FAIL. Sem isto a doc afirma sobre uma migration
     que ninguém mais tem, e quem lê a doc destrava o deploy no escuro.
  4. contagem vs lista no próprio doc — "N itens" seguido de lista com M≠N → WARN.

Escape hatch: `<!-- lint:ignore TOKEN -->` inline no doc, ou uma linha por
token em `.claude/.project-doc/lint-allow.txt`.

CLI:
  python3 doc_lint.py --project-root <root> [--docs a.md b.md] [--json]
Exit 1 se houver FAIL.

Roda só sobre o BODY (frontmatter fora — o hash8 da doc-sig confundiria o
check 2). Stdlib-puro.
"""
import argparse
import json
import os
import re
import subprocess
import sys

from pattern_check import (_extract_frontmatter_and_body,
                           _enumerate_scoped_docs, _scope_entries)

# --- check 1: env-var ---
CANDIDATE_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,}(?:_[A-Z0-9]+)+\b")
# Só sufixos que praticamente SÓ existem em env var. `_ID`, `_API`, `_MODE`,
# `_PATH`, `_ENV`, `_URL` saíram: são sufixos de substantivo tanto quanto de env
# (SESSION_ID, BASE_URL, DEBUG_MODE, REST_API vinham de campo JSON/coluna de
# banco e viravam FAIL) — reintroduziam a classe de falso-positivo que o
# FORMA_PAGAMENTO já tinha exposto. Esses caem em WARN.
ENV_SHAPED_RE = re.compile(
    r"(_TOKEN|_SECRET|_PASSWORD|_PASSWD|_APIKEY|_DSN)$"
    r"|_API_KEY$|_ACCESS_KEY$"
    r"|^(DB_|PG_|SMTP_|AWS_|OAUTH2?_|NEXT_PUBLIC_|MCP_|GF_)")
# onde o CÓDIGO lê env (lado R do árbitro)
ENV_READ_PATTERNS = [
    re.compile(r"process\.env\.([A-Z][A-Z0-9_]+)"),
    re.compile(r"process\.env\[[\"']([A-Z][A-Z0-9_]+)[\"']\]"),
    re.compile(r"os\.environ(?:\.get)?[\[\(][\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(r"os\.getenv\([\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(r"\bgetenv\(\s*[\"']([A-Z][A-Z0-9_]+)[\"']"),
    re.compile(r"import\.meta\.env\.([A-Z][A-Z0-9_]+)"),
    re.compile(r"\$\{([A-Z][A-Z0-9_]+)[}:\-]"),
    re.compile(r"^\s*(?:-\s*)?([A-Z][A-Z0-9_]+)=", re.MULTILINE),      # compose env / .env / shell
    re.compile(r"^\s*ENV\s+([A-Z][A-Z0-9_]+)", re.MULTILINE),          # Dockerfile
    re.compile(r"^\s*Environment=\"?([A-Z][A-Z0-9_]+)=", re.MULTILINE),  # systemd
]
# Aceita QUALQUER token (hash minúsculo, path com / e .), não só UPPER_SNAKE —
# o escape hatch é prometido no SKILL para os 3 checks, e o char class antigo
# só cobria o de env var.
IGNORE_INLINE_RE = re.compile(r"<!--\s*lint:ignore\s+([^>]+?)\s*-->")

# --- check 2: commit hash ---
# (?<![0-9a-f-]) / (?![0-9a-f-]): não casar SEGMENTO de UUID
# (550e8400-e29b-...) — vira ruído de "hash não resolve".
HEX_RE = re.compile(r"(?<![0-9a-f-])[0-9a-f]{7,40}(?![0-9a-f-])")
# Alternação AGRUPADA: sem o grupo, o \b só ligava no 1º e no último termo —
# "emergency" casava 'merge' e escalava WARN→FAIL.
COMMIT_CONTEXT_RE = re.compile(r"(?i)\b(?:commit|merge|rebase|revert|cherry|hash)\b")
# Nem todo hex citado é commit: a doc também cita blob/tree/objeto git (ex.
# "blob `a655f48b`" — sobreviveu no tree). Esses resolvem em `cat-file -t` mas
# NÃO em `<sha>^{commit}` — sem esta guarda, viram falso-positivo.
NON_COMMIT_OBJ_RE = re.compile(r"(?i)\b(?:blob|tree|árvore|objeto)\b")

# --- check 3: ponteiro arquivo:N ---
# Exige que o path tenha `/` OU um nome que não seja "Tecnologia.js" — sem isso
# `Node.js:20` / `Next.js:14` (tecnologia:versão) viravam FAIL "arquivo não existe".
# A validação final de existência acontece no check; aqui só evitamos o ruído
# óbvio de nome capitalizado sem diretório.
POINTER_RE = re.compile(
    r"(?<![\w/])((?:[\w.\[\]-]+/)+[\w.\[\]-]+\.(?:py|ts|tsx|js|mjs|yml|yaml|sh|conf|json|sql|prisma|md|toml|alloy|service|timer)"
    r"|[a-z_][\w.\[\]-]*\.(?:py|ts|tsx|mjs|yml|yaml|sh|conf|sql|prisma|toml|alloy|service|timer)):(\d+)")

# --- check 4: contagem vs lista ---
# Negrito é OPCIONAL — a docstring promete "N declarado vs M itens", e exigir
# `**` fazia o check ignorar `3 checks: ...` em texto normal.
COUNT_RE = re.compile(r"(?:\*\*)?(\d+)\s+([a-zA-Zçãõéáíóú-]+)(?:\*\*)?\s*[—:(]")

TEXT_EXTS = {".py", ".ts", ".tsx", ".js", ".mjs", ".jsx", ".json", ".yml", ".yaml",
             ".sh", ".bash", ".zsh", ".conf", ".env", ".example", ".sample", ".toml",
             ".sql", ".prisma", ".md", ".txt", ".alloy", ".service", ".timer",
             ".cfg", ".ini", ".tf", ".Dockerfile", ""}
MAX_FILE_BYTES = 512 * 1024


def _git_ls_files(root):
    """Arquivos versionados. **None** (≠ []) quando o git não respondeu — a
    diferença é load-bearing: com [] o lint concluiria "nada existe no repo" e
    acusaria TODO token e TODO ponteiro. None faz os checks 1 e 3 se calarem."""
    try:
        r = subprocess.run(["git", "-C", root, "ls-files"], capture_output=True,
                           text=True, timeout=30, errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def _git_head_files(root):
    """Arquivos que estão NO TRONCO (commitados em HEAD), do root e de cada git
    root aninhado (com o prefixo do caminho). **None** quando o git não respondeu
    ou o repo não tem commit — igual ao `_git_ls_files`, "não sei" não pode virar
    acusação. Diferente do índice (`ls-files`): arquivo só staged, ou nem isso,
    NÃO está no tronco — foi assim que uma migration não commitada virou
    afirmação de doc e destravou um deploy."""
    def _ls_tree(groot):
        try:
            r = subprocess.run(["git", "-C", groot, "ls-tree", "-r", "--name-only",
                                "-z", "HEAD"], capture_output=True, text=True,
                               timeout=30, errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
        except Exception:
            return None
        if r.returncode != 0:
            return None
        return [x for x in r.stdout.split("\0") if x.strip()]

    own = _ls_tree(root)
    if own is None:
        return None
    head = set(own)
    for groot in _nested_git_roots(root):
        if os.path.abspath(groot) == os.path.abspath(root):
            continue
        nested = _ls_tree(groot)
        if not nested:
            continue
        pref = os.path.relpath(groot, root)
        head.update(os.path.join(pref, x) for x in nested)
    return head


def build_repo_index(root):
    """Uma passada no repo: (R = nomes lidos como env, D = tokens presentes em
    qualquer arquivo não-doc, F = lista de arquivos p/ resolução de sufixo).
    O repo é o árbitro do check 1."""
    env_read, defined = set(), set()
    all_files = _git_ls_files(root)
    if all_files is None:
        return None, None, None  # git mudo → checks 1 e 3 desligam (fail-open)
    for rel in all_files:
        if "/.claude/" in ("/" + rel) or rel.startswith(".claude/"):
            continue  # doc não é evidência de doc
        ext = os.path.splitext(rel)[1]
        base = os.path.basename(rel)
        if ext not in TEXT_EXTS and base != "Dockerfile" and not base.startswith(".env"):
            continue
        p = os.path.join(root, rel)
        try:
            if os.path.getsize(p) > MAX_FILE_BYTES:
                continue
            with open(p, encoding="utf-8", errors="ignore") as fh:
                txt = fh.read()
        except OSError:
            continue
        for pat in ENV_READ_PATTERNS:
            for m in pat.finditer(txt):
                env_read.add(m.group(1))
        for m in CANDIDATE_RE.finditer(txt):
            defined.add(m.group(0))
    return env_read, defined, all_files




_NLINES_CACHE = {}


def _journal_id_prefixes(root):
    """Prefixos (7/8/16 chars) dos finding_ids do journal — a doc os cita como
    'finding b1219541' e eles NÃO são commits; sem isso o check 2 vira ruído."""
    prefixes = set()
    p = os.path.join(root, ".claude", ".project-doc", "findings.jsonl")
    try:
        with open(p, encoding="utf-8", errors="ignore") as fh:
            for ln in fh:
                m = re.search(r'"id"\s*:\s*"([0-9a-f]{8,40})"', ln)
                if m:
                    fid = m.group(1)
                    prefixes.update({fid[:7], fid[:8], fid})
    except OSError:
        pass
    return prefixes


def _load_allowlist(root):
    allow = set()
    p = os.path.join(root, ".claude", ".project-doc", "lint-allow.txt")
    try:
        # errors="replace": arquivo salvo em latin-1 levantaria UnicodeDecodeError
        # (que é ValueError, não OSError) e derrubaria o lint inteiro.
        with open(p, encoding="utf-8", errors="replace") as fh:
            for ln in fh:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    allow.add(ln)
    except OSError:
        pass
    return allow


def _nested_git_roots(root):
    """git roots aninhados (repos-legado importados, ex. _repos-antigos/*) —
    um hash citado na doc pode ser história legítima de um repo pré-migração."""
    roots = [root]
    try:
        for d1 in sorted(os.listdir(root)):
            p1 = os.path.join(root, d1)
            if not os.path.isdir(p1) or d1.startswith("."):
                continue
            if os.path.isdir(os.path.join(p1, ".git")):
                roots.append(p1)
            else:
                for d2 in sorted(os.listdir(p1)):
                    p2 = os.path.join(p1, d2)
                    if os.path.isdir(os.path.join(p2, ".git")):
                        roots.append(p2)
    except OSError:
        pass
    return roots


def _commit_batch_check(root, tokens):
    """{token: bool(resolve como commit em QUALQUER git root do projeto)}.
    Um subprocess por git root (não por token)."""
    if not tokens:
        return {}
    toks = sorted(tokens)
    res = {t: False for t in toks}
    any_git_ok = False
    for groot in _nested_git_roots(root):
        pending = [t for t in toks if not res[t]]
        if not pending:
            break
        try:
            inp = "".join(t + "^{commit}\n" for t in pending)
            out = subprocess.run(["git", "-C", groot, "cat-file", "--batch-check"],
                                 input=inp, capture_output=True, text=True,
                                 timeout=20, start_new_session=True).stdout.splitlines()
        except Exception:
            continue
        # Só conta como consulta VÁLIDA se o git respondeu 1 linha por token.
        # Sem isso (dir não é repo, git quebrado), stdout vazio faria TODO hash
        # virar FAIL — um lint tem que falhar-ABERTO, nunca acusar por erro de
        # ambiente.
        if len(out) != len(pending):
            continue
        any_git_ok = True
        for t, line in zip(pending, out):
            if "missing" not in line and "ambiguous" not in line:
                res[t] = True
    if not any_git_ok:
        return {t: True for t in toks}  # nenhuma consulta válida → não acusar
    return res


def lint_doc(root, doc_rel, env_read, defined, allow, all_files=None,
             journal_ids=None, head_files=None):
    """Findings de UM doc: [{check, severity, line, token, msg}]."""
    p = os.path.join(root, doc_rel)
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        return []
    _fm, body = _extract_frontmatter_and_body(content)
    fm_lines = content[:len(content) - len(body)].count("\n")
    lines = body.splitlines()
    ignores = set(allow)
    for m in IGNORE_INLINE_RE.finditer(body):
        for tok in re.split(r"[ ,]+", m.group(1)):
            if tok:
                ignores.add(tok)

    findings = []

    # --- check 1: env-var (só com índice do repo; sem git não há árbitro) ---
    seen1 = set()
    for i, ln in enumerate([] if env_read is None else lines):
        for m in CANDIDATE_RE.finditer(ln):
            tok = m.group(0)
            if tok in seen1 or tok in ignores:
                continue
            seen1.add(tok)
            if tok in env_read or tok in defined:
                continue
            # fragmento de var composta: a doc cita 'CLIENT_SECRET' de
            # 'APP_OAUTH_CLIENT_SECRET' — prosa encurtada, não erro
            if any(v.endswith("_" + tok) for v in env_read):
                continue
            # env-shaped = SÓ pela forma do nome (sufixo/prefixo). O critério de
            # contexto (±2 linhas) gerava FAIL em enum/coluna de banco
            # (FORMA_PAGAMENTO) — identificador real que só vive no DB.
            env_shaped = bool(ENV_SHAPED_RE.search(tok))
            findings.append({
                "check": "env-var", "severity": "FAIL" if env_shaped else "WARN",
                "line": fm_lines + i + 1, "token": tok,
                "msg": "`%s` não existe em NENHUM arquivo do repo%s" % (
                    tok, " (env-shaped)" if env_shaped else ""),
            })

    # --- check 2: commit hash (batch no fim) ---
    hash_hits = []  # (line_idx, token)
    seen2 = set()
    for i, ln in enumerate(lines):
        for m in HEX_RE.finditer(ln):
            tok = m.group(0)
            if tok in seen2 or tok in ignores:
                continue
            if not (re.search(r"\d", tok) and re.search(r"[a-f]", tok)):
                continue
            seen2.add(tok)
            if journal_ids and tok in journal_ids:
                continue  # é finding_id do journal citado em prosa, não commit
            if NON_COMMIT_OBJ_RE.search(ln):
                continue  # a linha declara blob/tree — não é claim de commit
            hash_hits.append((i, tok))
    resolved = _commit_batch_check(root, {t for _, t in hash_hits})
    for i, tok in hash_hits:
        if resolved.get(tok, True):
            continue
        is_commit_ctx = bool(COMMIT_CONTEXT_RE.search(lines[i]))
        findings.append({
            "check": "commit-hash", "severity": "FAIL" if is_commit_ctx else "WARN",
            "line": fm_lines + i + 1, "token": tok,
            "msg": "hash `%s` não resolve como commit no repo" % tok,
        })

    # --- check 3: ponteiro arquivo:N (idem — sem índice, não acusa) ---
    scope = _scope_entries(root, p)
    modp = ""
    m = re.search(r"(?:^|/)\.claude/docs/modules/([^/]+)/", "/" + doc_rel)
    if m:
        modp = m.group(1) + "/"
    pointer_warned = False
    seen3 = set()
    for i, ln in enumerate([] if all_files is None else lines):
        for pm in POINTER_RE.finditer(ln):
            f, n = pm.group(1), int(pm.group(2))
            key = (f, n)
            if key in seen3 or f in ignores or "..." in f:
                continue  # '...' = elipse de prosa, não path
            seen3.add(key)
            # resolução: raiz → módulo do doc → dirname de entradas do scope → sufixo
            cands = [f, modp + f] + [os.path.join(os.path.dirname(s), f) for s in scope[:6]]
            if all_files:
                suf = "/" + f.lstrip("/")
                cands += [x for x in all_files if ("/" + x).endswith(suf)]
            # confinamento ao root: '../outro-repo/x.py:1' não pode ser
            # declarado "vivo" (é leitura só, mas o veredito seria mentira).
            existing = []
            for c in cands:
                ap = os.path.join(root, c)
                if not os.path.isfile(ap):
                    continue
                try:
                    if not os.path.realpath(ap).startswith(os.path.realpath(root) + os.sep):
                        continue
                except OSError:
                    continue
                existing.append(c)
            if not existing:
                findings.append({
                    "check": "pointer", "severity": "FAIL",
                    "line": fm_lines + i + 1, "token": "%s:%d" % (f, n),
                    "msg": "arquivo `%s` do ponteiro não existe" % f,
                })
                continue

            # --- check 3b: existe no disco, mas está fora do tronco ---
            # O arquivo só existe na máquina de quem escreveu a doc: quem clona o
            # repo não o tem. `head_files is None` = git mudo → não acusa.
            if head_files is not None and not any(
                    os.path.normpath(c) in head_files for c in existing):
                findings.append({
                    "check": "not-in-trunk", "severity": "FAIL",
                    "line": fm_lines + i + 1, "token": "%s:%d" % (f, n),
                    "msg": "`%s` existe no disco mas NÃO está no tronco "
                           "(não commitado) — a doc afirma sobre arquivo que "
                           "quem clona o repo não tem" % existing[0],
                })
                continue

            # Path parcial é AMBÍGUO quando vários arquivos casam o sufixo
            # (`auth.py`, `brain/docker-compose.yml`). Só é ponteiro morto se
            # NENHUM candidato existente comporta a linha N — senão a doc está
            # certa e quem errou foi a resolução.
            # _nlines devolve None em erro de IO (permissão, NFS): "não sei" NÃO
            # pode virar 0 e fabricar "ponteiro morto: tem 0 linhas".
            # Memoizado: o mesmo arquivo é citado por vários ponteiros.
            def _nlines(c):
                # chave ABSOLUTA: relativa colidiria entre roots diferentes no
                # mesmo processo (o mesmo 'app/main.py' de dois repos)
                ap = os.path.join(root, c)
                if ap in _NLINES_CACHE:
                    return _NLINES_CACHE[ap]
                try:
                    with open(ap, "rb") as fh:
                        v = fh.read().count(b"\n") + 1
                except OSError:
                    v = None
                _NLINES_CACHE[ap] = v
                return v
            sizes = [(c, _nlines(c)) for c in existing]
            if all(v is None for _, v in sizes):
                continue  # nenhum candidato legível → não acusa
            target = next((c for c, v in sizes if v is not None and n <= v), None)
            if target is not None:
                nlines = n  # algum candidato comporta a linha → vivo
            else:
                target, nlines = next((c, v) for c, v in sizes if v is not None)
            if n > nlines:
                findings.append({
                    "check": "pointer", "severity": "FAIL",
                    "line": fm_lines + i + 1, "token": "%s:%d" % (f, n),
                    "msg": "ponteiro morto: `%s` tem %d linhas (< %d)" % (target, nlines, n),
                })
            elif not pointer_warned:
                pointer_warned = True
                findings.append({
                    "check": "pointer", "severity": "WARN",
                    "line": fm_lines + i + 1, "token": "%s:%d" % (f, n),
                    "msg": "doc usa ponteiro por nº de linha — prefira arquivo+símbolo (1 aviso por doc)",
                })

    # --- check 4: contagem vs lista imediatamente abaixo ---
    for i, ln in enumerate(lines):
        cm = COUNT_RE.search(ln)
        if not cm:
            continue
        n_claimed = int(cm.group(1))
        # conta bullets/itens de lista logo abaixo (até linha em branco dupla/heading)
        j, items = i + 1, 0
        # itens inline na MESMA linha (`a`, `b`, `c`)
        inline = len(re.findall(r"`[^`]+`", ln))
        while j < len(lines) and j <= i + n_claimed + 6:
            s = lines[j].strip()
            if s.startswith("#"):
                break
            if re.match(r"^[-*]\s", s):
                items += 1
            elif not s and items:
                break
            j += 1
        counted = items if items else inline
        if counted and 2 <= n_claimed <= 60 and counted != n_claimed and abs(counted - n_claimed) <= max(3, n_claimed // 3):
            findings.append({
                "check": "count", "severity": "WARN",
                "line": fm_lines + i + 1, "token": "%d vs %d" % (n_claimed, counted),
                "msg": "doc afirma %d %s mas a lista adjacente tem %d item(ns)" % (
                    n_claimed, cm.group(2), counted),
            })
    return findings


def lint(root, docs=None):
    root = os.path.abspath(root)
    env_read, defined, all_files = build_repo_index(root)
    allow = _load_allowlist(root)
    journal_ids = _journal_id_prefixes(root)
    head_files = _git_head_files(root)
    doc_list = docs if docs else _enumerate_scoped_docs(root)
    results = []
    fails = warns = 0
    for doc_rel in doc_list:
        fnd = lint_doc(root, doc_rel, env_read, defined, allow, all_files,
                       journal_ids, head_files)
        if fnd:
            results.append({"path": doc_rel, "findings": fnd})
            fails += sum(1 for f in fnd if f["severity"] == "FAIL")
            warns += sum(1 for f in fnd if f["severity"] == "WARN")
    return {"docs": results, "fails": fails, "warns": warns,
            "docs_checked": len(doc_list)}


def main():
    ap = argparse.ArgumentParser(description="doc-lint mecânico (project-doc v3.11)")
    ap.add_argument("--project-root", default=None)
    ap.add_argument("--docs", nargs="*", default=None,
                    help="docs específicos (root-relativos); default: todos")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root or os.getcwd())
    out = lint(root, args.docs)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("doc-lint — %d doc(s), %d FAIL, %d WARN" % (
            out["docs_checked"], out["fails"], out["warns"]))
        for d in out["docs"]:
            print("  %s" % d["path"])
            for f in d["findings"]:
                print("    [%s] %s L%d — %s" % (f["severity"], f["check"], f["line"], f["msg"]))
    return 1 if out["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
