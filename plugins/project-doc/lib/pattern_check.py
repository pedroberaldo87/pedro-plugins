#!/usr/bin/env python3
"""
pattern_check.py — verifica se o projeto segue o padrão project-doc v2 (gen=3.6).

Checks 5 invariantes de disco:
  (a) markers v2 presentes em .claude/CLAUDE.md
  (b) todo .claude/docs/*.md abre com frontmatter YAML `^---\n`
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

CURRENT_GEN = "3.6"

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
    """Extrai o valor de um campo `field: valor` do frontmatter (sem aspas)."""
    m = re.search(r"^" + re.escape(field) + r":\s*(.+)$", fm, re.MULTILINE)
    if not m:
        return ""
    return m.group(1).strip().strip('"').strip("'")


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
    if scope_raw:
        scope = os.path.basename(scope_raw.split(",")[0].strip())
    else:
        scope = os.path.splitext(os.path.basename(docfile))[0]

    hash8 = hashlib.sha256(body.encode("utf-8")).hexdigest()[:8]
    return "%s/%s@gen=%s#%s" % (project, scope, CURRENT_GEN, hash8)


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

    claude_md = os.path.join(project_root, ".claude", "CLAUDE.md")

    # --- Lê o CLAUDE.md ---
    try:
        with open(claude_md, encoding="utf-8") as fh:
            claude_content = fh.read()
    except OSError:
        result["violations"].append("(a) .claude/CLAUDE.md não encontrado ou ilegível")
        return result

    # --- (a) markers v2 presentes (abertura E fechamento) ---
    if not _MARKER_RE.search(claude_content):
        result["violations"].append("(a) marker <!-- project-doc:v2 --> ausente em .claude/CLAUDE.md")
    else:
        # extrai gen do marker de abertura
        m = _GEN_RE.search(claude_content)
        if m:
            result["gen_found"] = m.group(1)
        if not _END_MARKER_RE.search(claude_content):
            result["violations"].append("(a) marker <!-- project-doc:v2:end --> ausente em .claude/CLAUDE.md")

    # --- (c) journal findings.jsonl existe ---
    journal_path = os.path.join(project_root, ".claude", ".project-doc", "findings.jsonl")
    if not os.path.isfile(journal_path):
        result["violations"].append("(c) .claude/.project-doc/findings.jsonl não existe")

    # --- (b) e (d) — verifica cada .claude/docs/*.md ---
    docs_dir = os.path.join(project_root, ".claude", "docs")
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
                "(nested) app %s tem marker nested-pointer mas não tem doc em .claude/docs/" % app_name
            )

    return violations


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
    args = ap.parse_args()

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
