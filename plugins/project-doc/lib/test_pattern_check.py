#!/usr/bin/env python3
"""
test_pattern_check.py — testes do pattern_check (invariantes a–e + sig determinística).

Cobre:
  - doc in-pattern → in_pattern True (sem violations)
  - doc sem frontmatter → falha invariante (b)
  - gen desatualizado → falha invariante (e)
  - sig determinística: duas chamadas com o mesmo arquivo → resultado idêntico
  - journal ausente → falha invariante (c)
  - doc-sig ausente no frontmatter → falha invariante (d)

Self-contained: tudo em /tmp via tempfile; nenhum arquivo real é modificado.
Roda com:  python3 plugins/project-doc/lib/test_pattern_check.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pattern_check  # noqa: E402

PASS = 0


def check(label, cond):
    global PASS
    assert cond, "FALHOU: " + label
    PASS += 1
    print("  ok ·", label)


# ---------------------------------------------------------------------------
# helpers de fixture
# ---------------------------------------------------------------------------

CURRENT_GEN = pattern_check.CURRENT_GEN
OLD_GEN = "3.5"  # versão anterior para testar invariante (e)

# CLAUDE.md mínimo "in-pattern"
_CLAUDE_MD_OK = """\
# CLAUDE.md
<!-- project-doc:v2 gen={gen} -->
Some content here.
<!-- project-doc:v2:end -->
""".format(gen=CURRENT_GEN)

# doc .md mínimo válido (com frontmatter + doc-sig)
_DOC_OK = """\
---
project: testproject
scope: architecture
doc-sig: testproject/architecture@gen={gen}#00000000
---
# Architecture
Body text here.
""".format(gen=CURRENT_GEN)

# doc sem frontmatter (viola invariante b)
_DOC_NO_FRONTMATTER = """\
# Architecture
Body text here — no frontmatter.
"""

# doc com frontmatter mas sem doc-sig (viola invariante d)
_DOC_NO_DOCSIG = """\
---
project: testproject
scope: architecture
---
# Architecture
Body without doc-sig field.
"""


def _make_project(tmpdir, claude_md=_CLAUDE_MD_OK, doc_content=_DOC_OK,
                  with_journal=True, gen=CURRENT_GEN):
    """Monta estrutura mínima de projeto em tmpdir e retorna o root."""
    root = tmpdir
    claude_dir = os.path.join(root, ".claude")
    docs_dir = os.path.join(claude_dir, "docs")
    proj_doc_dir = os.path.join(claude_dir, ".project-doc")

    os.makedirs(docs_dir, exist_ok=True)
    if with_journal:
        os.makedirs(proj_doc_dir, exist_ok=True)
        open(os.path.join(proj_doc_dir, "findings.jsonl"), "w").close()

    with open(os.path.join(claude_dir, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write(claude_md)

    if doc_content is not None:
        with open(os.path.join(docs_dir, "architecture.md"), "w", encoding="utf-8") as fh:
            fh.write(doc_content)

    return root


# ---------------------------------------------------------------------------
def test_in_pattern():
    print("\n== check_pattern — doc in-pattern passa ==")
    with tempfile.TemporaryDirectory() as d:
        # doc precisa de doc-sig real; a sig calculada pode diferir do campo,
        # mas a invariante (d) só checa se a LINHA doc-sig EXISTE, não o valor.
        root = _make_project(d)
        r = pattern_check.check_pattern(root)
        check("in_pattern True quando tudo correto", r["in_pattern"] is True)
        check("sem violations", r["violations"] == [])
        check("gen_found == CURRENT_GEN", r["gen_found"] == CURRENT_GEN)
        check("doc listado em docs[]", len(r["docs"]) == 1)


# ---------------------------------------------------------------------------
def test_invariant_b_no_frontmatter():
    print("\n== check_pattern — doc sem frontmatter viola (b) ==")
    with tempfile.TemporaryDirectory() as d:
        root = _make_project(d, doc_content=_DOC_NO_FRONTMATTER)
        r = pattern_check.check_pattern(root)
        check("in_pattern False", r["in_pattern"] is False)
        check("violation (b) presente",
              any("(b)" in v for v in r["violations"]))


# ---------------------------------------------------------------------------
def test_invariant_e_old_gen():
    print("\n== check_pattern — gen desatualizado viola (e) ==")
    old_claude_md = """\
# CLAUDE.md
<!-- project-doc:v2 gen={gen} -->
content
<!-- project-doc:v2:end -->
""".format(gen=OLD_GEN)
    with tempfile.TemporaryDirectory() as d:
        root = _make_project(d, claude_md=old_claude_md)
        r = pattern_check.check_pattern(root)
        check("in_pattern False", r["in_pattern"] is False)
        check("gen_found == OLD_GEN", r["gen_found"] == OLD_GEN)
        check("violation (e) presente",
              any("(e)" in v for v in r["violations"]))


# ---------------------------------------------------------------------------
def test_sig_deterministic():
    print("\n== sig — determinística (mesma entrada → mesma saída) ==")
    with tempfile.TemporaryDirectory() as d:
        docs_dir = os.path.join(d, ".claude", "docs")
        os.makedirs(docs_dir)
        docfile = os.path.join(docs_dir, "architecture.md")
        with open(docfile, "w", encoding="utf-8") as fh:
            fh.write(_DOC_OK)

        s1 = pattern_check.sig(docfile, project_root=d)
        s2 = pattern_check.sig(docfile, project_root=d)
        check("sig idêntica em duas chamadas consecutivas", s1 == s2)
        check("sig contém gen=CURRENT_GEN", ("gen=" + CURRENT_GEN) in s1)
        check("sig contém hash8 (# presente)", "#" in s1)

        # sha256 é determinístico pelo body; altera o body → sig diferente
        with open(docfile, "w", encoding="utf-8") as fh:
            fh.write(_DOC_OK + "\nExtra line.\n")
        s3 = pattern_check.sig(docfile, project_root=d)
        check("body diferente => sig diferente", s1 != s3)


# ---------------------------------------------------------------------------
def test_invariant_c_missing_journal():
    print("\n== check_pattern — journal ausente viola (c) ==")
    with tempfile.TemporaryDirectory() as d:
        root = _make_project(d, with_journal=False)
        r = pattern_check.check_pattern(root)
        check("in_pattern False", r["in_pattern"] is False)
        check("violation (c) presente",
              any("(c)" in v for v in r["violations"]))


# ---------------------------------------------------------------------------
def test_invariant_d_missing_docsig():
    print("\n== check_pattern — doc-sig ausente viola (d) ==")
    with tempfile.TemporaryDirectory() as d:
        root = _make_project(d, doc_content=_DOC_NO_DOCSIG)
        r = pattern_check.check_pattern(root)
        check("in_pattern False", r["in_pattern"] is False)
        check("violation (d) presente",
              any("(d)" in v for v in r["violations"]))


# ---------------------------------------------------------------------------
def test_sig_not_self_referential_for_claude_md():
    """Invariante F1: sig() de CLAUDE.md (sem frontmatter) NÃO aparece dentro
    do próprio arquivo — logo grep da sig no transcript nunca casa via
    sig_in_transcript; a liberação correta é o sentinel de disco.
    """
    print("\n== sig — CLAUDE.md sem frontmatter: sig não está no arquivo ==")
    with tempfile.TemporaryDirectory() as d:
        claude_dir = os.path.join(d, ".claude")
        os.makedirs(claude_dir, exist_ok=True)
        claude_md = os.path.join(claude_dir, "CLAUDE.md")
        content = _CLAUDE_MD_OK  # sem frontmatter YAML
        with open(claude_md, "w", encoding="utf-8") as fh:
            fh.write(content)

        s = pattern_check.sig(claude_md, project_root=d)
        check("sig não vazia para CLAUDE.md sem frontmatter", bool(s))
        check("sig não está dentro do arquivo (não auto-referencial)", s not in content)


# ---------------------------------------------------------------------------
def test_invariant_a_missing_end_marker():
    """Invariante (a): marcador de abertura sem <!-- project-doc:v2:end --> vviola (a)."""
    print("\n== check_pattern — end marker ausente viola (a) ==")
    # CLAUDE.md com abertura mas sem <!-- project-doc:v2:end -->
    claude_md_no_end = """\
# CLAUDE.md
<!-- project-doc:v2 gen={gen} -->
Some content here.
""".format(gen=CURRENT_GEN)
    with tempfile.TemporaryDirectory() as d:
        root = _make_project(d, claude_md=claude_md_no_end)
        r = pattern_check.check_pattern(root)
        check("in_pattern False quando end marker ausente", r["in_pattern"] is False)
        check("violation (a) presente (end marker)",
              any("(a)" in v and "end" in v for v in r["violations"]))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_in_pattern()
    test_invariant_b_no_frontmatter()
    test_invariant_e_old_gen()
    test_sig_deterministic()
    test_invariant_c_missing_journal()
    test_invariant_d_missing_docsig()
    test_sig_not_self_referential_for_claude_md()
    test_invariant_a_missing_end_marker()
    print("\nTODOS OS %d CHECKS PASSARAM" % PASS)
