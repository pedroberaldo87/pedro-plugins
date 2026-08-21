#!/usr/bin/env python3
"""
pattern_check.py — verifica se o projeto segue o padrão project-doc v2 (gen=3.7).

Checks 5 invariantes de disco:
  (a) markers v2 presentes em CLAUDE.md (raiz do projeto — convenção nativa do
      Claude Code; fallback para .claude/CLAUDE.md em projetos mais antigos)
  (b) todo *.md da casa da doc abre com frontmatter YAML `^---\n`
  (c) .claude/.project-doc/findings.jsonl existe
  (d) todo doc tem linha doc-sig no frontmatter (required from new gen)
  (e) gen_found == CURRENT_GEN

CLI:
  pattern_check.py --project-root <root> [--json]   # imprime o dict completo
  pattern_check.py --sig <docfile>                   # imprime só a sig esperada do arquivo
  pattern_check.py --project-root <root> --nested    # inclui checagem de nested-pointer (stub)
"""
import argparse
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from casa_da_doc import casa as casa_da_doc  # noqa: E402  (a doc migrou para docs/; a casa velha é retrocompatível)

CURRENT_GEN = "3.8"

# Regex que casa a abertura do marker: <!-- project-doc:v2 gen=X ... -->
_GEN_RE = re.compile(r"<!--\s*project-doc:v2\s+gen=(\S+)")
# Regex que detecta QUALQUER marker v2 de abertura (com ou sem gen=)
_MARKER_RE = re.compile(r"<!--\s*project-doc:v2[\s>]")
# Regex que detecta o marker de fechamento: <!-- project-doc:v2:end -->
_END_MARKER_RE = re.compile(r"<!--\s*project-doc:v2:end\s*-->")
# doc-sig no frontmatter YAML: linha `doc-sig: <valor>`
_DOCSIG_RE = re.compile(r"^doc-sig:\s*\S+", re.MULTILINE)


# ---------------------------------------------------------------------------
# sig() — assinatura determinística de um doc
# "<project>/<scope_basename_or_app>@gen=<CURRENT_GEN>#<hash8>"
# hash8 = primeiros 8 hex do sha256 do BODY (conteúdo após frontmatter)
# ---------------------------------------------------------------------------
def _extract_frontmatter_and_body(content):
    """Separa frontmatter YAML do body. Devolve (frontmatter_str, body_str).

    Se não houver frontmatter `^---\n...\n---\n`, devolve ('', content inteiro).
    """
    if not content.startswith("---\n"):
        return "", content
    end = content.find("\n---\n", 4)
    if end == -1:
        return "", content
    fm = content[4:end]          # conteúdo entre os dois `---`
    body = content[end + 5:]     # após o `---\n` de fechamento
    return fm, body


def _fm_field(fm, field):
    """Extrai o valor de um campo do frontmatter (sem aspas).

    Tolera os DOIS formatos que os agentes realmente escrevem:
    `field: valor` (inline) e a lista YAML em bloco

        field:
          - a
          - b

    que é a forma natural de YAML e a que a skill grande gera para scopes
    longos. Sem o ramo de bloco, o campo lia '' e o doc ficava INVISÍVEL pro
    índice inverso do touch — nunca era re-projetado, em silêncio.
    A lista em bloco é devolvida como `a, b` (o formato que `_split_scope` já
    consome), então o resto da cadeia não muda.
    """
    m = re.search(r"^" + re.escape(field) + r":[ \t]*(.*)$", fm, re.MULTILINE)
    if not m:
        return ""
    inline = m.group(1).strip().strip('"').strip("'")
    if inline:
        return inline
    # Nada na mesma linha: pode ser lista em bloco. Consome os `- item`
    # subsequentes (recuados) até a próxima chave no mesmo nível.
    items = []
    for line in fm[m.end():].splitlines():
        if not line.strip():
            continue
        stripped = line.lstrip()
        if not stripped.startswith("- "):
            break
        items.append(stripped[2:].strip().strip('"').strip("'"))
    return ", ".join(items)


def _split_scope(scope_raw):
    """Entradas do scope, tolerante aos DOIS formatos reais: `a, b, c` e
    `[a, b, c]` (lista YAML inline). Sem o strip de colchetes, o 1º e o último
    item de todo scope-lista nunca casavam no staleness (bug pré-v3.11)."""
    raw = scope_raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    out = []
    for e in raw.split(","):
        # NÃO fazer .strip("[]") por-entrada: os colchetes do container já saíram
        # acima, e strippar por item mutila rota dinâmica (`app/[slug]` → `app/[slug`),
        # que então nunca casa e ainda vira dead_scope falso.
        e = e.strip().strip("'").strip('"').strip()
        if e and not e.startswith("backup "):
            out.append(e)
    return out


def sig(docfile, project_root=None):
    """Devolve a sig determinística para o arquivo `docfile`.

    project_root é usado apenas para tornar o nome do projeto relativo; se
    omitido, usa o basename do pai de .claude/ se detectável, senão 'project'.
    Nunca falha — em caso de IO error devolve uma sig de conteúdo vazio.
    """
    try:
        with open(docfile, encoding="utf-8") as fh:
            content = fh.read()
    except OSError:
        content = ""

    fm, body = _extract_frontmatter_and_body(content)

    # project: campo `project` do frontmatter ou dirname inferido
    project = _fm_field(fm, "project")
    if not project and project_root:
        project = os.path.basename(os.path.abspath(project_root))
    if not project:
        project = "project"

    # scope: basename do campo `scope` (path completo → basename), ou nome do arquivo
    scope_raw = _fm_field(fm, "scope")
    scope_entries = _split_scope(scope_raw) if scope_raw else []
    if scope_entries:
        # rstrip('/'): scope de DIRETÓRIO ('lib/') daria basename '' e a sig
        # perderia o segmento de identidade.
        scope = os.path.basename(scope_entries[0].rstrip("/")) or scope_entries[0].strip("/")
    else:
        scope = os.path.splitext(os.path.basename(docfile))[0]

    hash8 = hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]
    return "%s/%s@gen=%s#%s" % (project, scope, CURRENT_GEN, hash8)


def doc_set_gen(project_root):
    """A gen do DOC-SET (marker do CLAUDE.md) — NÃO o CURRENT_GEN do código.

    As duas divergem de propósito: o código bumpa a gen quando o motor muda de
    padrão, e o doc-set só passa a valer a nova gen depois de um FULL. Confundir as
    duas é a armadilha que o `--sig` tem por construção (ele carimba sempre a do
    código), e que obrigava quem chamava a corrigir com `sed` depois.
    """
    for cand in (os.path.join(project_root, "CLAUDE.md"),
                 os.path.join(project_root, ".claude", "CLAUDE.md")):
        try:
            with open(cand, encoding="utf-8", errors="replace") as fh:
                m = _GEN_RE.search(fh.read())
        except OSError:
            continue
        if m:
            return m.group(1)
    return None


def restamp(project_root, docs, today=None):
    """Carimba os docs recém-projetados: `generated`, `generated-commit`, `doc-sig`.

    Existe por um problema de ovo-e-galinha que este repo já pagou 3 vezes
    (commits `16211ae`, `b9028c3`, `8d7a5a0`): **um doc não consegue citar o commit
    que o contém.** Quando código e doc entram no MESMO commit, o carimbo só pode
    apontar pro commit anterior — e aí a janela de staleness enxerga a mudança que a
    própria doc acabou de descrever e a declara defasada. A saída é um segundo
    commit, só de carimbo, e é esse rito que este verbo automatiza.

    Três regras que vieram de defeito:
      - **gen do DOC-SET, não do código** (ver `doc_set_gen`). Chamar `--sig` cru
        bumpava a gen no `/doc-touch`, violando o invariante "gen não bumpa".
      - **`doc-sig` é sha256 do CORPO** — recomputada aqui a partir do corpo, depois
        de o frontmatter estar final, senão a sig mente.
      - **doc autoral é intocável.** `authored-by: human` no frontmatter (território
        do `/start`) é PULADO, nunca re-carimbado.

    A lista de docs é EXPLÍCITA de propósito: carimbar um doc que ninguém
    re-projetou escreveria `generated: hoje` sobre trabalho que não aconteceu.

    Devolve {"commit": sha|None, "stamped": [...], "skipped": [{doc, reason}],
             "error": str|None}. Não escreve nada quando `error` está setado.
    """
    project_root = os.path.abspath(project_root)
    out = {"commit": None, "stamped": [], "skipped": [], "error": None}
    if today is None:
        import time
        today = time.strftime("%Y-%m-%d")

    import subprocess
    try:
        r = subprocess.run(["git", "-C", project_root, "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        head = r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        head = ""
    if not head:
        # Fail-LOUD: sem HEAD o carimbo não tem como ficar correto, e carimbo
        # parcial é pior que carimbo velho — não escreve nada.
        out["error"] = ("não consegui resolver o HEAD do git em %s — nada foi carimbado "
                        "(carimbo pela metade é pior que carimbo velho)" % project_root)
        return out
    out["commit"] = head

    gen = doc_set_gen(project_root)
    for doc in docs:
        path = doc if os.path.isabs(doc) else os.path.join(project_root, doc)
        rel = os.path.relpath(path, project_root).replace(os.sep, "/")
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            out["skipped"].append({"doc": rel, "reason": "ilegível: %s" % exc})
            continue
        fm, body = _extract_frontmatter_and_body(content)
        if not content.startswith("---"):
            out["skipped"].append({"doc": rel, "reason": "sem frontmatter — não é doc project-doc"})
            continue
        if re.search(r"^authored-by:\s*human\b", fm, re.MULTILINE):
            out["skipped"].append({"doc": rel, "reason": "doc autoral (authored-by: human)"})
            continue

        new_sig = sig(path, project_root)
        if gen:
            new_sig = re.sub(r"@gen=[^#]*#", "@gen=%s#" % gen, new_sig, count=1)

        fm2 = fm
        fm2 = re.sub(r"^generated:.*$", "generated: %s" % today, fm2, count=1, flags=re.MULTILINE)
        if re.search(r"^generated-commit:", fm2, re.MULTILINE):
            fm2 = re.sub(r"^generated-commit:.*$", "generated-commit: %s" % head,
                         fm2, count=1, flags=re.MULTILINE)
        else:
            fm2 = re.sub(r"^generated:.*$",
                         "generated: %s\ngenerated-commit: %s" % (today, head),
                         fm2, count=1, flags=re.MULTILINE)
        if re.search(r"^doc-sig:", fm2, re.MULTILINE):
            fm2 = re.sub(r"^doc-sig:.*$", "doc-sig: %s" % new_sig,
                         fm2, count=1, flags=re.MULTILINE)
        else:
            fm2 = fm2.rstrip("\n") + "\ndoc-sig: %s\n" % new_sig

        novo = "---\n" + fm2.strip("\n") + "\n---\n" + body
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(novo)
            os.replace(tmp, path)
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            out["skipped"].append({"doc": rel, "reason": "falhou ao gravar: %s" % exc})
            continue
        out["stamped"].append({"doc": rel, "generated": today,
                               "generated_commit": head, "doc_sig": new_sig})
    return out


# ---------------------------------------------------------------------------
# check_pattern() — retorna o dict de resultado
# ---------------------------------------------------------------------------
def check_pattern(project_root):
    """Verifica se o projeto segue o padrão project-doc.

    Retorna dict:
      {
        in_pattern: bool,
        gen_found:  str | None,
        gen_current: str,
        violations: [str],
        docs: [{path, sig, gen}],
      }

    Fail-safe: nunca levanta exceção; erros de IO viram violations.
    """
    result = {
        "in_pattern": False,
        "gen_found": None,
        "gen_current": CURRENT_GEN,
        "violations": [],
        "docs": [],
    }

    # CLAUDE.md: prefere quem CARREGA o marker project-doc:v2 — cobre projetos
    # com os DOIS arquivos (um CLAUDE.md na raiz escrito à mão + o real, gerado
    # pelo project-doc, aninhado em .claude/ — visto na prática: ACME-APP).
    # Sem marker em nenhum, cai pra raiz-depois-aninhado (raiz é a convenção
    # nativa do Claude Code — é de lá que o harness carrega as instruções do
    # projeto). Bug real corrigido aqui: só checar .claude/CLAUDE.md fazia todo
    # projeto com CLAUDE.md na raiz (ex.: Cybersec) reportar in_pattern=False
    # incondicionalmente, mesmo com a doc em dia.
    root_md = os.path.join(project_root, "CLAUDE.md")
    nested_md = os.path.join(project_root, ".claude", "CLAUDE.md")

    def _has_v2_marker(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return bool(_MARKER_RE.search(fh.read()))
        except OSError:
            return False

    if _has_v2_marker(root_md):
        claude_md = root_md
    elif _has_v2_marker(nested_md):
        claude_md = nested_md
    elif os.path.isfile(root_md):
        claude_md = root_md
    else:
        claude_md = nested_md

    # --- Lê o CLAUDE.md ---
    try:
        with open(claude_md, encoding="utf-8") as fh:
            claude_content = fh.read()
    except OSError:
        result["violations"].append("(a) CLAUDE.md não encontrado ou ilegível (raiz ou .claude/)")
        return result

    # --- (a) markers v2 presentes (abertura E fechamento) ---
    claude_md_rel = os.path.relpath(claude_md, project_root)
    if not _MARKER_RE.search(claude_content):
        result["violations"].append(f"(a) marker <!-- project-doc:v2 --> ausente em {claude_md_rel}")
    else:
        # extrai gen do marker de abertura
        m = _GEN_RE.search(claude_content)
        if m:
            result["gen_found"] = m.group(1)
        if not _END_MARKER_RE.search(claude_content):
            result["violations"].append(f"(a) marker <!-- project-doc:v2:end --> ausente em {claude_md_rel}")

    # --- (c) journal findings.jsonl existe ---
    journal_path = os.path.join(project_root, ".claude", ".project-doc", "findings.jsonl")
    if not os.path.isfile(journal_path):
        result["violations"].append("(c) .claude/.project-doc/findings.jsonl não existe")

    # --- (b) e (d) — verifica cada *.md da casa da doc ---
    docs_dir = casa_da_doc(project_root)
    doc_files = []
    try:
        for name in sorted(os.listdir(docs_dir)):
            if name.endswith(".md"):
                doc_files.append(os.path.join(docs_dir, name))
    except OSError:
        pass   # docs_dir inexistente é silenciado — não é invariante obrigatória

    for dpath in doc_files:
        try:
            with open(dpath, encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            result["violations"].append("(b) ilegível: %s" % dpath)
            continue

        rel = os.path.relpath(dpath, project_root)

        # (b) abre com frontmatter `^---\n`
        if not content.startswith("---\n"):
            result["violations"].append("(b) frontmatter YAML ausente em %s" % rel)

        # (d) linha doc-sig no frontmatter
        fm, _ = _extract_frontmatter_and_body(content)
        if not _DOCSIG_RE.search(fm):
            result["violations"].append("(d) doc-sig ausente no frontmatter de %s" % rel)

        doc_sig = sig(dpath, project_root=project_root)
        result["docs"].append({"path": rel, "sig": doc_sig, "gen": result["gen_found"]})

    # --- (e) gen_found == CURRENT_GEN ---
    if result["gen_found"] is None:
        result["violations"].append("(e) gen= ausente no marker project-doc:v2")
    elif result["gen_found"] != CURRENT_GEN:
        result["violations"].append(
            "(e) gen desatualizado: encontrado=%s esperado=%s" % (result["gen_found"], CURRENT_GEN)
        )

    # Organismo: condicional, NÃO entra em violations (não afeta in_pattern).
    result["organism"] = check_organism(project_root)

    result["in_pattern"] = len(result["violations"]) == 0
    return result


# ---------------------------------------------------------------------------
# Nested-pointer invariant stub (wired by t3a)
# ---------------------------------------------------------------------------
def check_nested_pointers(project_root, docs_result):
    """Stub: verifica nested-pointer markers em apps/*/CLAUDE.md.

    Se algum apps/*/CLAUDE.md carregar o marker `nested-pointer`, todo app que
    tem doc deve ter um nested pointer sig atualizado. Enquanto nenhum app
    carregar o marker, não falha (não adiciona violations) — evita falsos
    positivos antes do wiring completo.

    Retorna lista de violations adicionais (vazia até a feature ser ativada).
    """
    violations = []
    apps_dir = os.path.join(project_root, "apps")
    if not os.path.isdir(apps_dir):
        return violations

    nested_marker = re.compile(r"<!--\s*nested-pointer\b")
    apps_with_marker = []

    try:
        for app_name in sorted(os.listdir(apps_dir)):
            app_claude = os.path.join(apps_dir, app_name, "CLAUDE.md")
            if not os.path.isfile(app_claude):
                continue
            try:
                with open(app_claude, encoding="utf-8") as fh:
                    content = fh.read()
                if nested_marker.search(content):
                    apps_with_marker.append(app_name)
            except OSError:
                continue
    except OSError:
        return violations

    # Se nenhum app tem o marker → feature não ativada → não falha
    if not apps_with_marker:
        return violations

    # Feature ativada: todo app com doc deve ter nested pointer sig atualizado.
    # (implementação completa pendente — wired por t3a)
    for app_name in apps_with_marker:
        app_doc = next(
            (d for d in docs_result if ("apps/%s" % app_name) in d.get("path", "")),
            None,
        )
        if app_doc is None:
            violations.append(
                "(nested) app %s tem marker nested-pointer mas não tem doc na casa da doc" % app_name
            )

    return violations


# ---------------------------------------------------------------------------
# check_organism — validação CONDICIONAL do .claude/organism.yaml
# ---------------------------------------------------------------------------
def check_organism(project_root):
    """Valida o organism.yaml SE presente. Condicional (padrão do CONDITIONAL
    invariant): ausência NÃO é violação e NÃO afeta in_pattern (um organism.yaml
    malformado não deve forçar deep-rebuild da doc, que é ortogonal). Só avisa.

    Retorna {present, valid, warnings[]}.
    """
    path = os.path.join(project_root, ".claude", "organism.yaml")
    if not os.path.isfile(path):
        return {"present": False, "valid": True, "warnings": []}
    warnings = []
    try:
        import organism  # mesmo loader do engine: PyYAML se houver, senão parser stdlib
        data = organism.load_yaml_file(path)
    except Exception as e:
        return {"present": True, "valid": False, "warnings": ["organism.yaml ilegível: %s" % e]}

    if not data.get("name"):
        warnings.append("organism.yaml sem 'name'")
    costuras = data.get("costuras")
    if not isinstance(costuras, list) or not costuras:
        warnings.append("organism.yaml sem 'costuras' (lista não-vazia)")
        costuras = []
    seen_ids = set()
    for i, c in enumerate(costuras):
        cid = c.get("id")
        tag = cid or ("#%d" % i)
        if not cid:
            warnings.append("costura %s sem 'id'" % tag)
        elif cid in seen_ids:
            warnings.append("costura id duplicado: %s" % cid)
        else:
            seen_ids.add(cid)
        if c.get("severidade") not in ("block", "warn"):
            warnings.append("costura %s: severidade deve ser block|warn" % tag)
        if not (c.get("aresta_msg") or "").strip():
            warnings.append("costura %s sem 'aresta_msg' (curada por humano)" % tag)
        pontas = c.get("pontas")
        if not isinstance(pontas, list) or len(pontas) < 2:
            warnings.append("costura %s precisa de >=2 pontas (é cross-módulo)" % tag)
            pontas = pontas if isinstance(pontas, list) else []
        for p in pontas:
            if not p.get("modulo"):
                warnings.append("costura %s: ponta sem 'modulo'" % tag)
            if not (isinstance(p.get("globs"), list) and p.get("globs")):
                warnings.append("costura %s: ponta '%s' sem 'globs'" % (tag, p.get("modulo")))
    return {"present": True, "valid": len(warnings) == 0, "warnings": warnings}


# ---------------------------------------------------------------------------
# scope_staleness — staleness TERNÁRIO por scope (não por contagem de arquivos).
#
# Design (com o Fable): o heurístico antigo (contagem >8 desde a data) era cego a
# QUAIS arquivos e fail-open (sem data → "fresco"). Aqui:
#   - fresh    = nenhum arquivo do `scope:` do doc mudou desde `generated:`.
#   - stale    = algum arquivo do scope mudou (o doc pode mentir).
#   - unknown  = sem git, sem `generated:`, ou sem `scope:` → NÃO finge "fresco".
# Proxy barato p/ arquivo-novo-fora-do-scope (Parte B adiada): arquivo ADD nos
# DIRETÓRIOS do scope desde a data → sinaliza "scope pode estar incompleto".
# ARG_MAX-safe: 1 git log restrito ao subtree do doc, interseção em Python.
# Limitações herdadas/documentadas: --since só-data tem folga de até 24h; rename
# não é seguido; scope relativo à base do doc (o dir que contém .claude/).
# ---------------------------------------------------------------------------
_GEN_DATE_RE = re.compile(r"^generated:\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)
# generated-commit: SHA opcional (v3.11) — quando presente e resolvível, staleness
# usa `git diff <sha>..HEAD` (precisão de commit) em vez da janela por data, o que
# evita o doc re-acusar stale no MESMO dia de um touch (a janela --since=00:00
# repegaria os commits da manhã). Ausência NÃO é violação (CONDITIONAL, sem gen bump).
_GEN_COMMIT_RE = re.compile(r"^generated-commit:\s*[\"']?([0-9a-f]{7,40})", re.MULTILINE)


def _git_commit_resolves(root, sha):
    import subprocess
    try:
        r = subprocess.run(["git", "-C", root, "cat-file", "-e", sha + "^{commit}"],
                           capture_output=True, timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        return r.returncode == 0
    except Exception:
        return False


def _git_diff_names(root, range_or_sha, subtree, added_only=False, cached=False,
                    worktree=False):
    """Paths (root-relativos POSIX) do `git diff`. None em erro (≠ set vazio)."""
    import subprocess
    args = ["git", "-C", root, "diff", "--name-only"]
    if added_only:
        args.append("--diff-filter=A")
    if cached:
        args.append("--cached")
    if range_or_sha and not worktree and not cached:
        args.append(range_or_sha)
    args.append("--")
    args.append(subtree if subtree else ".")
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, stdin=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        return None
    if r.returncode != 0:
        return None  # idem _git_log_since: erro ≠ "nada mudou"
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def _doc_base(root, docpath):
    """Dir-base contra o qual o `scope:` do doc resolve = o dir que contém .claude/.
    Ex.: <root>/finance/<casa da doc>/db.md → base rel 'finance'; <root>/.claude/... → ''."""
    rel = os.path.relpath(os.path.abspath(docpath), root).replace(os.sep, "/")
    marker = "/.claude/"
    idx = ("/" + rel).find(marker)
    if idx < 0:
        return ""
    return ("/" + rel)[1:idx]  # '' para a raiz


def _git_log_since(root, date, subtree, added_only=False):
    """Paths (root-relativos POSIX) tocados desde `date`, restrito a `subtree`
    ('' = repo todo). added_only → só arquivos ADD (--diff-filter=A). [] em erro."""
    import subprocess
    args = ["git", "-C", root, "log", "--since=%s 00:00:00" % date,
            "--name-only", "--pretty=format:"]
    if added_only:
        args.insert(4, "--diff-filter=A")
    args.append("--")
    args.append(subtree if subtree else ".")
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20, stdin=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        return None  # git ausente/erro → unknown, não fresco
    # returncode≠0 (dubious ownership, revisão inválida, repo corrompido) devolve
    # stdout VAZIO — sem esta checagem viraria "nenhum arquivo mudou" = fresco,
    # exatamente o "nunca finge fresco" que esta camada promete.
    if r.returncode != 0:
        return None
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def scope_staleness(root, docpath):
    """Retorna {state: fresh|stale|unknown, changed:[...], scope_maybe_incomplete: bool,
    new_files:[...], generated: str|None}."""
    root = os.path.abspath(root)
    res = {"state": "unknown", "changed": [], "scope_maybe_incomplete": False,
           "new_files": [], "generated": None}
    # exists, não isdir: em git worktree e submódulo o .git é um ARQUIVO
    # ('gitdir: ...'). Com isdir a feature morria em silêncio nesses layouts.
    if not os.path.exists(os.path.join(root, ".git")):
        return res  # não é repo git → unknown
    try:
        with open(docpath, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError:
        return res
    fm, _ = _extract_frontmatter_and_body(content)
    m = _GEN_DATE_RE.search(fm)
    if not m:
        return res  # sem generated: → unknown (fail-LOUD, não "fresco")
    date = m.group(1)
    res["generated"] = date
    scope_raw = _fm_field(fm, "scope")
    if not scope_raw:
        return res  # sem scope → unknown
    base = _doc_base(root, docpath)
    prefix = (base + "/") if base else ""
    # v3.11: usa o resolvedor com fallback de módulo (docs em modules/<m>/ têm
    # scope relativo ao módulo) + filtro de não-paths — antes, essas entradas
    # nunca casavam e o doc parecia mais "fresh" do que era.
    scope_files = set(_scope_entries(root, docpath))
    if not scope_files:
        scope_files = {prefix + e for e in _split_scope(scope_raw)}
    scope_dirs = {os.path.dirname(f) for f in scope_files if os.path.dirname(f)}

    # v3.11: generated-commit tem precedência (precisão de commit; evita re-stale
    # no mesmo dia do touch). Fallback: janela por data (comportamento clássico).
    mc = _GEN_COMMIT_RE.search(fm)
    changed = added = None
    if mc and _git_commit_resolves(root, mc.group(1)):
        rng = mc.group(1) + "..HEAD"
        changed = _git_diff_names(root, rng, base)
        added = _git_diff_names(root, rng, base, added_only=True)
    if changed is None:
        changed = _git_log_since(root, date, base)
        added = None
    if changed is None:
        return res  # git falhou → unknown
    # Interseção de strings ignorava entrada de DIRETÓRIO ('lib/') e glob
    # ('src/*.py') — `changed` só tem arquivos, então um doc policiado por dir
    # NUNCA ficava stale (sub-detecção silenciosa, o pior modo de falha aqui).
    hit = sorted({p for p in changed
                  for e in scope_files if _scope_match(e, p, root)})
    # proxy: arquivo ADD nos diretórios do scope, fora do scope
    if added is None:
        added = _git_log_since(root, date, base, added_only=True) or set()
    added = added or set()
    new_in_dirs = sorted(f for f in added
                         if os.path.dirname(f) in scope_dirs and f not in scope_files)

    res["changed"] = hit
    res["new_files"] = new_in_dirs
    res["scope_maybe_incomplete"] = bool(new_in_dirs)
    res["state"] = "stale" if hit else "fresh"
    return res


# ---------------------------------------------------------------------------
# docs_for_paths / touch_plan (v3.11) — o índice INVERSO do scope, base do modo
# incremental (skill doc-touch). Matching EXATO (não o suffix-match frouxo dos
# anchors do journal): scope entries normalizados via _doc_base → root-relativo
# POSIX → igualdade; entrada-dir → prefix-match; entrada com '*' → fnmatch.
# ---------------------------------------------------------------------------
def _enumerate_scoped_docs(root):
    """Todos os docs project-doc com frontmatter, root-relativos POSIX.
    Cobre a casa da doc inteira (recursivo, pega modules/) e, em organismo,
    a casa da doc de cada módulo (docs pending-migration ainda não conformados)."""
    root = os.path.abspath(root)
    found = []
    bases = [casa_da_doc(root)]
    try:
        import organism
        _oroot, data = organism.find_organism(root)
        for mod in (data or {}).get("modulos") or []:
            bases.append(casa_da_doc(os.path.join(root, mod)))
    except Exception:
        pass
    for base in bases:
        if not os.path.isdir(base):
            continue
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                if not name.endswith(".md"):
                    continue
                p = os.path.join(dirpath, name)
                # Só doc project-doc (tem frontmatter). Um README/nota solto em
                # a casa da doc não é gerada pela skill e não deve ser lintada
                # nem policiado por staleness.
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        if not fh.read(4).startswith("---"):
                            continue
                except OSError:
                    continue
                found.append(os.path.relpath(p, root).replace(os.sep, "/"))
    return sorted(set(found))


_MODULE_DOC_RE = re.compile(r"(?:^|/)\.claude/docs/modules/([^/]+)/")  # casa-ok: o cobrador da doc reconhece a casa antiga de propósito (é o que ele varre)


def _module_prefix_of_doc(root, docpath_abs):
    """Se o doc vive em modules/<m>/ da casa da doc, devolve '<m>/' (fallback de
    resolução — os agentes escrevem o scope desses docs relativo ao MÓDULO)."""
    rel = os.path.relpath(os.path.abspath(docpath_abs), root).replace(os.sep, "/")
    m = _MODULE_DOC_RE.search("/" + rel)
    return (m.group(1) + "/") if m else ""


def _looks_like_path(entry):
    """Filtra açúcar humano do scope ('settings', '003', 'x.py (voice)'):
    entrada com espaço/parêntese ou número puro não é path verificável."""
    if " " in entry or "(" in entry or ")" in entry:
        return False
    if re.fullmatch(r"\d+", entry):
        return False
    return True


def _scope_entries(root, docpath_abs, resolve=True, field="scope"):
    """Entradas do scope normalizadas root-relativas. [] se sem frontmatter/scope.
    resolve=True aplica o fallback de módulo (entrada que não existe na raiz mas
    existe sob o módulo do doc → prefixa o módulo) e filtra não-paths.
    `field` permite ler `verified-by:` com a MESMA normalização do `scope:` — sem
    isso o consumidor teria que reimplementar o split + fallback de módulo, e é
    reimplementação de função barata que deriva em silêncio (o defeito da v3.16.0)."""
    try:
        with open(docpath_abs, encoding="utf-8", errors="replace") as fh:
            fm, _ = _extract_frontmatter_and_body(fh.read())
    except OSError:
        return []
    scope_raw = _fm_field(fm, field)
    if not scope_raw:
        return []
    base = _doc_base(root, docpath_abs)
    prefix = (base + "/") if base else ""
    entries = [prefix + e for e in _split_scope(scope_raw)]
    if not resolve:
        return entries
    modp = _module_prefix_of_doc(root, docpath_abs)
    out = []
    for e in entries:
        if not _looks_like_path(e):
            continue
        if os.path.exists(os.path.join(root, e)) or "*" in e:
            out.append(e)
        elif modp and os.path.exists(os.path.join(root, modp + e)):
            out.append(modp + e)
        else:
            out.append(e)  # mantém — vira dead_scope detectável
    return out


def _scope_match(entry, path, root):
    """entry casa path? Exato; dir (sufixo '/' ou dir real) → prefix; '*' → fnmatch."""
    if entry == path:
        return True
    if "*" in entry or "?" in entry:
        # fnmatch deixa '*' atravessar '/' (lib/*.py casaria lib/a/b/c.py).
        # '**' segue recursivo; '*' fica preso a um segmento.
        import fnmatch
        if "**" in entry:
            return fnmatch.fnmatch(path, entry.replace("**", "*"))
        if path.count("/") != entry.count("/"):
            return False
        return fnmatch.fnmatch(path, entry)
    if entry.endswith("/"):
        return path.startswith(entry)
    if os.path.isdir(os.path.join(root, entry)):
        return path.startswith(entry.rstrip("/") + "/")
    return False


def docs_for_paths(root, changed_paths):
    """Inverso do scope: {doc_rel: {"files": [paths do changed que o doc cobre]}}.
    changed_paths: iterable de paths root-relativos POSIX."""
    root = os.path.abspath(root)
    changed = [p.replace(os.sep, "/") for p in changed_paths]
    result = {}
    for doc_rel in _enumerate_scoped_docs(root):
        entries = _scope_entries(root, os.path.join(root, doc_rel))
        if not entries:
            continue
        hits = sorted({p for p in changed for e in entries if _scope_match(e, p, root)})
        if hits:
            result[doc_rel] = {"files": hits}
    return result


def touch_plan(root):
    """Plano determinístico do modo incremental (doc-touch). READ-ONLY no ledger.
    changed = working tree ∪ staged ∪ last_commit..HEAD (mesma composição do
    backward-delta do journal — journal.py run_update)."""
    root = os.path.abspath(root)
    res = {"changed": [], "docs": {}, "pending_docs": [], "seam_review": [],
           "unscoped_new": [], "dead_scope": [], "ledger_last_commit": None}
    if not os.path.exists(os.path.join(root, ".git")):  # worktree: .git é arquivo
        return res
    changed = set()
    for kw in ({"worktree": True}, {"cached": True}):
        got = _git_diff_names(root, None, "", **kw)
        if got:
            changed |= got
    last_commit = None
    try:
        import journal
        last_commit = journal.load_ledger(root).get("last_commit")
    except Exception:
        pass
    res["ledger_last_commit"] = last_commit
    if last_commit and _git_commit_resolves(root, last_commit):
        got = _git_diff_names(root, last_commit + "..HEAD", "")
        if got:
            changed |= got
    # docs nunca são "código mudado" pro touch
    changed = {p for p in changed
               if "/.claude/" not in ("/" + p) and not p.startswith(".claude/")}
    res["changed"] = sorted(changed)
    res["docs"] = docs_for_paths(root, changed)

    # "já tocado": o doc foi escrito DEPOIS de todos os arquivos que o afetam →
    # já absorveu essas mudanças. Sem isso o plano nunca encolhe enquanto o
    # trabalho não é commitado (o git diff segue mostrando os mesmos arquivos),
    # o touch repetido vira no-op e o hook re-sugere pra sempre. mtime é o único
    # sinal disponível pro working tree (git não datou nada ainda).
    for doc_rel, info in res["docs"].items():
        try:
            doc_mtime = os.path.getmtime(os.path.join(root, doc_rel))
        except OSError:
            info["already_current"] = False
            continue
        newest = 0.0
        for f in info["files"]:
            try:
                newest = max(newest, os.path.getmtime(os.path.join(root, f)))
            except OSError:
                pass
        info["already_current"] = bool(newest) and doc_mtime > newest
    res["pending_docs"] = sorted(d for d, i in res["docs"].items()
                                 if not i.get("already_current"))

    # seam_review: costuras tocadas → módulos do blast-radius (revisar, não re-projetar)
    try:
        import organism
        _oroot, data = organism.find_organism(root)
        if data:
            seen = {}
            for p in changed:
                for c in organism.costuras_for_path(root, data, os.path.join(root, p)):
                    cid = c.get("id")
                    if cid and cid not in seen:
                        seen[cid] = {"costura": cid,
                                     "blast_radius": c.get("blast_radius") or [],
                                     "via": p}
            res["seam_review"] = list(seen.values())
    except Exception:
        pass

    # unscoped_new: arquivo mudado em dir-de-scope de algum doc, mas fora do scope
    # dead_scope: entrada de scope sem arquivo no disco (rename/deleção)
    all_scope_files, all_scope_dirs = set(), set()
    all_verified = set()
    for doc_rel in _enumerate_scoped_docs(root):
        docpath = os.path.join(root, doc_rel)
        for e in _scope_entries(root, docpath):
            if "*" not in e:
                all_scope_files.add(e)
                d = os.path.dirname(e)
                if d:
                    all_scope_dirs.add(d)
                if not os.path.exists(os.path.join(root, e)) and not e.endswith("/"):
                    res["dead_scope"].append({"doc": doc_rel, "entry": e})
        # `verified-by:` NÃO é lacuna de cobertura. Uma suíte pertence ao
        # verified-by do doc que ela prova, nunca ao scope — botá-la no scope
        # faria o doc virar stale a cada edição de teste. Sem esta exclusão o
        # unscoped_new acusa TODA suíte do repo, e um consumidor que use "há
        # arquivo fora de escopo?" como sinal (a escalada touch→FULL do
        # doc-touch) escalaria sempre que nascesse um test_*.
        all_verified |= {e for e in _scope_entries(root, docpath, field="verified-by")
                         if "*" not in e}
    res["unscoped_new"] = sorted(
        p for p in changed
        if p not in all_scope_files and p not in all_verified
        and os.path.dirname(p) in all_scope_dirs)

    # Idade do último FULL, em dias. O FULL é o único que avança
    # ledger.last_commit (o touch é read-only nele), então a data desse commit É
    # a data do último FULL. Exposto como DADO pra a escalada touch→FULL ser
    # mecânica em vez de julgamento do modelo. None = não resolvível (sem
    # ledger, sem git, SHA órfão) — o consumidor trata como "não sei", jamais
    # como "recente".
    res["last_full_age_days"] = _commit_age_days(root, last_commit)
    return res


def _commit_age_days(root, sha):
    """Idade em dias (float) do commit, ou None se não resolvível."""
    if not sha:
        return None
    import subprocess
    import time
    try:
        r = subprocess.run(["git", "-C", root, "log", "-1", "--format=%ct", sha],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        return max(0.0, (time.time() - int(r.stdout.strip())) / 86400.0)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# project_staleness — staleness TERNÁRIO por-projeto, BARATO (1 git log).
# Pros hooks (SessionStart/guard): não roda scope_staleness por-doc (seria N git
# logs por sessão). Agrega: data mais ANTIGA entre os docs + UNIÃO dos scopes, 1
# git log desde essa data restrito ao subtree do projeto, interseção em Python.
# Devolve 'fresh' | 'stale' | 'unknown' (nunca finge fresco sem sinal).
# ---------------------------------------------------------------------------
def _find_git_root(start):
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def project_staleness(project_dir):
    project_dir = os.path.abspath(project_dir)
    # RECURSIVO: os docs v3.x vivem também em modules/<m>/ da casa da doc. Um
    # listdir raso amostrava só os docs de topo e concluía fresh/unknown pelo
    # subconjunto errado.
    try:
        docs = [os.path.join(project_dir, d)
                for d in _enumerate_scoped_docs(project_dir)]
    except Exception:
        return "unknown"
    if not docs:
        return "unknown"
    git_root = _find_git_root(project_dir)
    if not git_root:
        return "unknown"
    subtree = os.path.relpath(project_dir, git_root).replace(os.sep, "/")
    subtree = "" if subtree == "." else subtree

    # v3.16: agrupa por BASE DE COMPARAÇÃO, honrando `generated-commit:` — a mesma
    # precedência que o `scope_staleness` (por doc) já aplicava. Antes, esta função
    # usava SÓ a janela por data, com granularidade de DIA: um /doc-touch seguido de
    # commit no mesmo dia deixava o hook do SessionStart gritando "DEFASADA" sobre
    # doc que acabou de nascer — e ela é justamente a versão que os hooks consomem,
    # então quem via o aviso falso era sempre o humano. Medido em 2026-07-29: os 5
    # docs deste repo davam `fresh` um por um e `stale` aqui, no mesmo instante.
    # Custo: 1 git call por generated-commit DISTINTO (na prática 1, porque o touch
    # carimba todos juntos), mais 1 pela janela de data se algum doc não tiver commit.
    by_commit = {}   # sha  -> entradas de scope dos docs carimbados nele
    by_date = {}     # data -> entradas de scope dos docs sem commit resolvível
    for dp in docs:
        try:
            with open(dp, encoding="utf-8", errors="replace") as fh:
                fm, _ = _extract_frontmatter_and_body(fh.read())
        except OSError:
            continue
        scope_raw = _fm_field(fm, "scope")
        if not scope_raw:
            continue
        # mesmo resolvedor do por-doc (v3.11): cobre scope relativo a módulo e
        # descarta entrada que não é path. `_split_scope` cru só entra no fallback.
        entries = set(_scope_entries(git_root, dp))
        if not entries:
            base = _doc_base(git_root, dp)
            prefix = (base + "/") if base else ""
            entries = {prefix + e for e in _split_scope(scope_raw)}
        if not entries:
            continue
        mc = _GEN_COMMIT_RE.search(fm)
        if mc and _git_commit_resolves(git_root, mc.group(1)):
            by_commit.setdefault(mc.group(1), set()).update(entries)
            continue
        m = _GEN_DATE_RE.search(fm)
        if m:
            by_date.setdefault(m.group(1), set()).update(entries)
        # doc sem generated E sem commit resolvível é imensurável: fica de fora,
        # como sempre ficou. Se NENHUM doc for mensurável, cai no unknown abaixo.
    if not by_commit and not by_date:
        return "unknown"  # fail-LOUD: sem generated/scope → indeterminado, não fresco

    def _hits(changed, entries):
        # `_scope_match`, não interseção crua de strings: `changed` só tem ARQUIVOS,
        # então entrada de DIRETÓRIO ('lib/') ou glob ('src/*.py') nunca casaria por
        # igualdade e o doc jamais ficaria stale — a mesma sub-detecção silenciosa
        # que o `scope_staleness` já havia consertado, e que aqui tinha sobrevivido.
        return any(_scope_match(e, p, git_root) for p in changed for e in entries)

    for sha, entries in by_commit.items():
        changed = _git_diff_names(git_root, sha + "..HEAD", subtree)
        if changed is None:
            return "unknown"
        if _hits(changed, entries):
            return "stale"
    for date, entries in by_date.items():
        changed = _git_log_since(git_root, date, subtree)
        if changed is None:
            return "unknown"
        if _hits(changed, entries):
            return "stale"
    return "fresh"


# ---------------------------------------------------------------------------
# rodada — QUAL das duas rodadas de doc cabe, decidido pela MEDIDA do atraso.
# Antes isto era prosa em três hooks mandando o dono escolher entre "incremental
# e barato" e "mineração completa" — escolha que ninguém tem como fazer sem medir
# a idade da doc. Aqui a idade é medida (generated-commit, senão generated:) e a
# rodada sai junto com o número que a sustentou.
# ---------------------------------------------------------------------------
LIMITE_FULL_DIAS = 30


def rodada(project_dir):
    """Escolhe a rodada de doc pelo atraso medido.

    Devolve (skill, dias, motivo) — `skill` é o NOME da skill (`doc` ou
    `doc-touch`), nunca o nome de invocação: a skill já mudou de plugin uma vez,
    e quem chama descobre o prefixo com `resolve-skill.sh`.
    `dias` é a idade do doc MAIS ATRASADO do
    projeto, ou None quando nada é mensurável — e aí a rodada é a completa,
    porque não há incremento a fazer sobre o que nunca foi minerado.
    """
    project_dir = os.path.abspath(project_dir)
    try:
        docs = [os.path.join(project_dir, d)
                for d in _enumerate_scoped_docs(project_dir)]
    except Exception:
        docs = []
    git_root = _find_git_root(project_dir)
    idades = []
    for dp in docs:
        try:
            with open(dp, encoding="utf-8", errors="replace") as fh:
                fm, _ = _extract_frontmatter_and_body(fh.read())
        except OSError:
            continue
        idade = None
        mc = _GEN_COMMIT_RE.search(fm)
        if mc and git_root:
            idade = _commit_age_days(git_root, mc.group(1))
        if idade is None:
            m = _GEN_DATE_RE.search(fm)
            if m:
                try:
                    import datetime
                    d = datetime.date(*[int(x) for x in m.group(1).split("-")])
                    idade = max(0.0, (datetime.date.today() - d).days)
                except ValueError:
                    idade = None
        if idade is not None:
            idades.append(idade)
    if not idades:
        return ("doc", None,
                "nenhuma doc com data mensurável — a rodada completa é a que minera do zero")
    dias = int(max(idades))
    if dias > LIMITE_FULL_DIAS:
        return ("doc", dias,
                "a doc mais atrasada tem %d dias, acima do teto de %d — drift antigo pede mineração completa"
                % (dias, LIMITE_FULL_DIAS))
    return ("doc-touch", dias,
            "a doc mais atrasada tem %d dias, dentro do teto de %d — o incremental dá conta"
            % (dias, LIMITE_FULL_DIAS))


# ---------------------------------------------------------------------------
# census — mundo-aberto + staleness. Delega a classificação ao organism.py e
# anexa o staleness por doc canônico/pending. Base do gate de policiamento.
# ---------------------------------------------------------------------------
def census(root):
    root = os.path.abspath(root)
    import organism
    cen = organism.census(root)
    for d in cen["docs"]:
        # staleness só faz sentido pra doc project-doc com scope (canônico/pending)
        if d["kind"] in ("canonical", "pending-migration") and not d["path"].endswith("CLAUDE.md"):
            st = scope_staleness(root, os.path.join(root, d["path"]))
            d["staleness"] = st["state"]
            d["changed"] = st["changed"]
            d["scope_maybe_incomplete"] = st["scope_maybe_incomplete"]
    return cen


def conformance_plan(root):
    """Dry-run: o que a conformação FARIA (read-only). Não escreve nada.
    migrate = módulos com doc pending → gerar modules/{m}/ + router + arquivar.
    archive = órfãos (leftover). collide = colisão direta c/ output do run (gate)."""
    cen = census(root)
    by_mod = {}
    orphans = []
    for d in cen["docs"]:
        if d["kind"] == "pending-migration":
            by_mod.setdefault(d["module"], []).append(d["path"])
        elif d["kind"] == "orphan":
            orphans.append(d["path"])
    migrate = [{"module": m, "docs": sorted(ds),
                "target": ".claude/docs/modules/%s/" % m,  # casa-ok: o cobrador da doc reconhece a casa antiga de propósito (é o que ele varre)
                "router": "%s/.claude/CLAUDE.md" % m} for m, ds in sorted(by_mod.items())]
    stale = [d["path"] for d in cen["docs"]
             if d.get("staleness") == "stale"]
    unknown = [d["path"] for d in cen["docs"]
               if d.get("staleness") == "unknown" and d["kind"] == "canonical"]
    return {
        "root": cen["root"], "organism": cen["organism"], "name": cen["name"],
        "summary": cen["summary"],
        "migrate": migrate, "archive_orphans": sorted(orphans),
        "stale_canonical": sorted(p for p in stale
                                  if p.startswith(".claude/")),
        "stale_pending": sorted(p for p in stale
                                if not p.startswith(".claude/")),
        "unknown_staleness": sorted(unknown),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="project-doc pattern checker (gen=%s)" % CURRENT_GEN)
    ap.add_argument("--project-root", default=None,
                    help="raiz do projeto (padrão: CWD)")
    ap.add_argument("--json", action="store_true",
                    help="imprime resultado como JSON (padrão: texto legível)")
    ap.add_argument("--sig", metavar="DOCFILE", default=None,
                    help="imprime só a sig esperada de DOCFILE e sai")
    ap.add_argument("--nested", action="store_true",
                    help="inclui checagem de nested-pointer (stub)")
    ap.add_argument("--census", action="store_true",
                    help="mundo-aberto: classifica toda doc project-doc do repo + staleness")
    ap.add_argument("--plan", action="store_true",
                    help="dry-run da conformação de organismo (o que MIGRARIA/arquivaria; read-only)")
    ap.add_argument("--project-staleness", metavar="DIR", default=None,
                    help="imprime fresh|stale|unknown do projeto DIR (barato, p/ hooks) e sai")
    ap.add_argument("--rodada", metavar="DIR", default=None,
                    help="mede o atraso da doc de DIR e imprime 'comando<TAB>dias<TAB>motivo' "
                         "(doc-touch ou project-doc) — a escolha que era prosa nos hooks")
    ap.add_argument("--touch-plan", action="store_true",
                    help="plano do modo incremental (doc-touch): diff da sessão → docs afetados (read-only)")
    ap.add_argument("--restamp", metavar="DOC", nargs="+", default=None,
                    help="carimba os docs LISTADOS: generated=hoje, generated-commit=HEAD, "
                         "doc-sig recomputada preservando a gen do doc-set. É o 2º commit do "
                         "rito do doc-touch (um doc não cita o commit que o contém)")
    args = ap.parse_args()

    # --- modo --restamp: o 2º commit do rito, sem receita de sed pra lembrar ---
    if args.restamp:
        root = os.path.abspath(args.project_root or os.getcwd())
        out = restamp(root, args.restamp)
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            if out["error"]:
                print("ERRO: %s" % out["error"], file=sys.stderr)
            else:
                print("Carimbado em %s (gen do doc-set preservada):" % out["commit"])
                for s in out["stamped"]:
                    print("  %-40s %s" % (s["doc"], s["doc_sig"]))
            for s in out["skipped"]:
                print("  PULADO %-34s %s" % (s["doc"], s["reason"]), file=sys.stderr)
        return 1 if out["error"] else 0

    # --- modo --touch-plan: base determinística da skill doc-touch ---
    if args.touch_plan:
        root = os.path.abspath(args.project_root or os.getcwd())
        try:
            out = touch_plan(root)
        except Exception as exc:
            print("ERRO em touch-plan: %s" % exc, file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            print("Touch plan — %s" % root)
            print("  changed: %d arquivo(s)" % len(out["changed"]))
            pend = out.get("pending_docs", list(out["docs"]))
            if pend:
                print("  A TOCAR (%d):" % len(pend))
                for d in pend:
                    print("    - %s  ← %s" % (d, ", ".join(out["docs"][d]["files"][:4])))
            else:
                print("  nenhum doc a tocar")
            done = [d for d in out["docs"] if d not in pend]
            if done:
                print("  já atualizados (doc mais novo que os arquivos): %d" % len(done))
            if out["seam_review"]:
                print("  costuras tocadas (revisar): %s" % ", ".join(
                    s["costura"] for s in out["seam_review"]))
            if out["unscoped_new"]:
                print("  fora de escopo (candidatos a adicionar): %d" % len(out["unscoped_new"]))
            if out["dead_scope"]:
                print("  scope morto (rename/deleção): %d entrada(s)" % len(out["dead_scope"]))
        return 0

    # --- modo --rodada: a escolha curta-vs-completa, medida em vez de perguntada ---
    if args.rodada:
        try:
            cmd, dias, motivo = rodada(args.rodada)
        except Exception:
            cmd, dias, motivo = ("doc-touch", None, "atraso não medido")
        print("%s\t%s\t%s" % (cmd, "" if dias is None else dias, motivo))
        return 0

    # --- modo --project-staleness: ternário barato pros hooks ---
    if args.project_staleness:
        try:
            print(project_staleness(args.project_staleness))
        except Exception:
            print("unknown")
        return 0

    # --- modo --census / --plan: policiamento mundo-aberto (read-only) ---
    if args.census or args.plan:
        root = os.path.abspath(args.project_root or os.getcwd())
        try:
            out = conformance_plan(root) if args.plan else census(root)
        except Exception as exc:
            print("ERRO em %s: %s" % ("plan" if args.plan else "census", exc), file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        elif args.plan:
            print("Conformação de organismo — DRY-RUN (nada foi escrito)")
            print("  organismo: %s (%s)" % (out.get("name"), out["root"]))
            print("  summary:   %s" % out["summary"])
            if out["migrate"]:
                print("  MIGRAR (%d módulos com doc legado → modules/{m}/ + router):" % len(out["migrate"]))
                for m in out["migrate"]:
                    print("    - %-10s %d doc(s) → %s" % (m["module"], len(m["docs"]), m["target"]))
            if out["archive_orphans"]:
                print("  ARQUIVAR órfãos (%d):" % len(out["archive_orphans"]))
                for p in out["archive_orphans"]:
                    print("    - %s" % p)
            if out["stale_canonical"] or out["stale_pending"]:
                print("  STALE por scope: %d canônico(s), %d pending" % (
                    len(out["stale_canonical"]), len(out["stale_pending"])))
            if out["unknown_staleness"]:
                print("  staleness INDETERMINADO (sem generated/scope): %d canônico(s)" % len(out["unknown_staleness"]))
        else:
            print("Census — %s" % out["root"])
            print("  summary: %s" % out["summary"])
            for kind in ("orphan", "pending-migration"):
                items = [d for d in out["docs"] if d["kind"] == kind]
                if items:
                    print("  %s (%d):" % (kind, len(items)))
                    for d in items[:20]:
                        extra = (" [%s]" % d["staleness"]) if d.get("staleness") else ""
                        print("    - %s%s" % (d["path"], extra))
        return 0

    # --- modo --sig: imprime só a assinatura de um arquivo ---
    if args.sig:
        docfile = os.path.abspath(args.sig)
        root = args.project_root or os.getcwd()
        try:
            s = sig(docfile, project_root=root)
            print(s)
            return 0
        except Exception as exc:
            print("ERRO ao calcular sig: %s" % exc, file=sys.stderr)
            return 1

    root = os.path.abspath(args.project_root or os.getcwd())

    try:
        result = check_pattern(root)
    except Exception as exc:
        print("ERRO inesperado em check_pattern: %s" % exc, file=sys.stderr)
        return 1

    # stub nested-pointer check
    if args.nested:
        extra = check_nested_pointers(root, result.get("docs", []))
        if extra:
            result["violations"].extend(extra)
            result["in_pattern"] = False

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "OK" if result["in_pattern"] else "FORA DO PADRÃO"
        print("project-doc pattern: %s  (gen_found=%s  current=%s)" % (
            status, result["gen_found"], result["gen_current"]))
        if result["violations"]:
            print("Violations:")
            for v in result["violations"]:
                print("  - " + v)
        if result["docs"]:
            print("Docs (%d):" % len(result["docs"]))
            for d in result["docs"]:
                print("  %s  sig=%s" % (d["path"], d["sig"]))

    return 0 if result["in_pattern"] else 1


if __name__ == "__main__":
    sys.exit(main())
