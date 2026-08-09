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
Roda com:  python3 plugins/project-skills/lib/test_pattern_check.py
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
# scope-staleness (ternário: fresh/stale/unknown) — precisa de fixture git.
# ---------------------------------------------------------------------------
def _git(root, *args, date=None):
    import subprocess
    env = dict(os.environ)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date + "T12:00:00"
    subprocess.run(["git", "-C", root, *args], env=env,
                   capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL, start_new_session=True)


def _doc_with(scope, generated):
    return ("---\ngenerated: %s\nproject: X\nscope: %s\n"
            "doc-sig: X/a@gen=%s#abcd1234\n---\n\n# doc\n" % (generated, scope, CURRENT_GEN))


def test_scope_staleness():
    import shutil
    if not shutil.which("git"):
        print("  (git ausente — pulo scope-staleness)")
        return
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "repo")
        os.makedirs(os.path.join(root, ".claude", "docs"))
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "t@t")
        _git(root, "config", "user.name", "t")
        # arquivo de scope commitado numa data ANTIGA
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "init", date="2026-06-01")

        docpath = os.path.join(root, ".claude", "docs", "arch.md")
        # doc gerado DEPOIS do último commit de a.py → fresh
        with open(docpath, "w") as fh:
            fh.write(_doc_with("a.py", "2026-07-01"))
        st = pattern_check.scope_staleness(root, docpath)
        check("scope fresco (arquivo não mudou desde generated)", st["state"] == "fresh")

        # a.py muda DEPOIS da data de geração → stale
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=2\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "change", date="2026-07-15")
        st = pattern_check.scope_staleness(root, docpath)
        check("scope stale (arquivo do scope mudou após generated)", st["state"] == "stale")
        check("stale lista o arquivo mudado", "a.py" in st["changed"])

        # sem generated: → unknown (fail-LOUD, nunca 'fresco')
        with open(docpath, "w") as fh:
            fh.write("---\nproject: X\nscope: a.py\ndoc-sig: X/a@gen=%s#abcd1234\n---\n\n# doc\n" % CURRENT_GEN)
        st = pattern_check.scope_staleness(root, docpath)
        check("sem generated → unknown (não finge fresco)", st["state"] == "unknown")

    # fora de repo git → unknown
    with tempfile.TemporaryDirectory() as d:
        docpath = os.path.join(d, "x.md")
        with open(docpath, "w") as fh:
            fh.write(_doc_with("a.py", "2026-07-01"))
        st = pattern_check.scope_staleness(d, docpath)
        check("sem git → unknown", st["state"] == "unknown")


def test_touch_and_generated_commit():
    """v3.11: generated-commit vence a janela por data; docs_for_paths mapeia o
    inverso do scope (exato/dir/glob/lista-YAML); touch_plan é read-only."""
    import shutil
    import subprocess
    if not shutil.which("git"):
        print("  (git ausente — pulo touch/generated-commit)")
        return
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "repo")
        os.makedirs(os.path.join(root, ".claude", "docs"))
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "t@t")
        _git(root, "config", "user.name", "t")
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=1\n")
        os.makedirs(os.path.join(root, "pkg"))
        with open(os.path.join(root, "pkg", "b.py"), "w") as fh:
            fh.write("y=1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "init", date="2026-06-01")
        # a.py muda HOJE (data do commit = hoje real)
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=2\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "hoje")
        head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True).stdout.strip()
        import datetime
        today = datetime.date.today().isoformat()

        # POR DATA: doc gerado hoje + commit de hoje → stale (janela 00:00 repega)
        docpath = os.path.join(root, ".claude", "docs", "arch.md")
        with open(docpath, "w") as fh:
            fh.write(_doc_with("a.py", today))
        st = pattern_check.scope_staleness(root, docpath)
        check("por DATA: commit de hoje re-suja o doc de hoje", st["state"] == "stale")

        # POR COMMIT: generated-commit = HEAD → fresh (diff HEAD..HEAD vazio)
        with open(docpath, "w") as fh:
            fh.write("---\ngenerated: %s\ngenerated-commit: %s\nproject: X\n"
                     "scope: a.py\ndoc-sig: X/a@gen=%s#abcd1234\n---\n\n# doc\n"
                     % (today, head[:12], CURRENT_GEN))
        st = pattern_check.scope_staleness(root, docpath)
        check("por COMMIT: generated-commit=HEAD → fresh no mesmo dia",
              st["state"] == "fresh")

        # docs_for_paths — formatos: lista YAML [a, b], dir, glob
        d2 = os.path.join(root, ".claude", "docs", "two.md")
        with open(d2, "w") as fh:
            fh.write("---\ngenerated: %s\nproject: X\nscope: [a.py, pkg/]\n"
                     "doc-sig: s\n---\n\n# t\n" % today)
        m = pattern_check.docs_for_paths(root, ["a.py"])
        check("inverso: a.py mapeia os 2 docs", len(m) == 2)
        m = pattern_check.docs_for_paths(root, ["pkg/b.py"])
        check("inverso: entrada-dir casa por prefixo",
              ".claude/docs/two.md" in m and len(m) == 1)
        m = pattern_check.docs_for_paths(root, ["nope.py"])
        check("inverso: arquivo fora de todo scope → vazio", m == {})

        # _split_scope tolera lista YAML com colchetes (bug pré-3.11)
        ents = pattern_check._split_scope("[a.py, b.py]")
        check("_split_scope tira colchetes do 1º/último item",
              ents == ["a.py", "b.py"])

        # touch_plan: read-only no ledger + mapeia mudança de working tree
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=3\n")  # working tree, não commitado
        ledger_dir = os.path.join(root, ".claude", ".project-doc")
        os.makedirs(ledger_dir, exist_ok=True)
        ledger_file = os.path.join(ledger_dir, "ledger.json")
        with open(ledger_file, "w") as fh:
            fh.write('{"last_commit": "%s", "mined_sessions": {}}' % head)
        before = open(ledger_file).read()
        tp = pattern_check.touch_plan(root)
        check("touch_plan mapeia mudança do working tree",
              "a.py" in tp["changed"] and len(tp["docs"]) == 2)
        check("touch_plan é read-only no ledger",
              open(ledger_file).read() == before)

        # idempotência: doc mais NOVO que os arquivos = já absorveu → sai do
        # pending (senão o touch repetido é no-op e o hook re-sugere pra sempre)
        import time
        time.sleep(0.02)
        for dp in (".claude/docs/arch.md", ".claude/docs/two.md"):
            os.utime(os.path.join(root, dp), None)
        tp2 = pattern_check.touch_plan(root)
        check("doc mais novo que o arquivo sai do pending_docs",
              tp2["pending_docs"] == [] and len(tp2["docs"]) == 2)
        time.sleep(0.02)
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=4\n")  # trabalho NOVO depois do touch
        tp3 = pattern_check.touch_plan(root)
        check("trabalho novo após o touch volta pro pending_docs",
              len(tp3["pending_docs"]) == 2)

        # --- unscoped_new NÃO acusa quem está no verified-by (v3.18.0) --------
        # REGRESSÃO: `unscoped_new` só enxergava `scope:`, então acusava TODA
        # suíte do repo (elas pertencem a `verified-by:`). Neste repo eram 11 de
        # 11 acusações falsas. Um consumidor que use "há arquivo fora de escopo?"
        # como gatilho escalaria a cada nascimento de test_*.
        with open(os.path.join(root, "pkg", "test_b.py"), "w") as fh:
            fh.write("assert 1\n")
        # `git add`: a janela do touch é working-tree ∪ staged, e `git diff` NÃO
        # lista untracked — arquivo novo só aparece depois de entrar no índice.
        _git(root, "add", "pkg/test_b.py")
        tp4 = pattern_check.touch_plan(root)
        check("unscoped_new acusa suíte que não está em verified-by nenhum",
              "pkg/test_b.py" in tp4["unscoped_new"])
        with open(d2, "w") as fh:
            fh.write("---\ngenerated: %s\nproject: X\nscope: [a.py, pkg/]\n"
                     "verified-by:\n  - pkg/test_b.py\ndoc-sig: s\n---\n\n# t\n"
                     % today)
        tp5 = pattern_check.touch_plan(root)
        check("unscoped_new PARA de acusar depois do verified-by",
              "pkg/test_b.py" not in tp5["unscoped_new"])
        check("...e o arquivo de scope segue mapeado (não matei o inverso)",
              ".claude/docs/two.md" in pattern_check.docs_for_paths(root, ["pkg/b.py"]))

        # --- last_full_age_days: dado pra a escalada touch→FULL --------------
        # O FULL é o único que avança ledger.last_commit, então a data desse
        # commit É a data do último FULL. Sem este campo a decisão touch-vs-FULL
        # viraria julgamento do modelo.
        age = tp5.get("last_full_age_days")
        check("last_full_age_days sai como número pro ledger que resolve",
              isinstance(age, float) and age >= 0)
        check("...e o commit é de HOJE, logo idade < 1 dia", age < 1.0)
        with open(ledger_file, "w") as fh:
            fh.write('{"last_commit": "deadbeef" "mined_sessions": {}}')  # JSON quebrado
        check("ledger ilegível → last_full_age_days None (não finge recente)",
              pattern_check.touch_plan(root).get("last_full_age_days") is None)


def _doc_with_commit(scope, generated, sha=None):
    fm = "---\ngenerated: %s\n" % generated
    if sha:
        fm += "generated-commit: %s\n" % sha
    fm += ("project: X\nscope: %s\ndoc-sig: X/a@gen=%s#abcd1234\n---\n\n# doc\n"
           % (scope, CURRENT_GEN))
    return fm


def test_project_staleness_honra_generated_commit():
    """v3.16 — o AGREGADO (o que os hooks consomem) tinha divergido do por-doc em
    dois pontos, e os dois eram sub/super-detecção silenciosa:

      1. ignorava `generated-commit:` e usava só a janela por DATA (granularidade
         de dia) → doc-touch + commit no mesmo dia = hook gritando "DEFASADA"
         sobre doc que acabou de nascer. Medido no repo real em 2026-07-29: 5
         docs `fresh` um por um e `stale` no agregado, no mesmo instante.
      2. interseção CRUA de strings em vez de `_scope_match` → doc policiada por
         DIRETÓRIO ('lib/') ou glob nunca ficava stale aqui.
    """
    import shutil
    import subprocess
    if not shutil.which("git"):
        print("  (git ausente — pulo project-staleness)")
        return

    def head(root):
        return subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True).stdout.strip()

    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "repo")
        docs = os.path.join(root, ".claude", "docs")
        os.makedirs(os.path.join(root, "lib"))
        os.makedirs(docs)
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "t@t")
        _git(root, "config", "user.name", "t")
        for f in ("a.py", "lib/b.py"):
            with open(os.path.join(root, f), "w") as fh:
                fh.write("x=1\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "toca a.py e lib/b.py", date="2026-07-15")
        sha1 = head(root)

        docpath = os.path.join(docs, "arch.md")

        # (1) O DEFEITO: doc carimbada NO commit que tocou o scope, no mesmo dia.
        # A janela por data pega o próprio commit que a doc documenta.
        with open(docpath, "w") as fh:
            fh.write(_doc_with_commit("a.py", "2026-07-15", sha1))
        check("agregado: carimbado no commit do scope → fresh (era stale pela janela de dia)",
              pattern_check.project_staleness(root) == "fresh")
        check("agregado concorda com o por-doc",
              pattern_check.project_staleness(root)
              == pattern_check.scope_staleness(root, docpath)["state"])

        # (2) commit NOVO depois do carimbo → os dois têm que dizer stale
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=2\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "muda a.py depois do carimbo", date="2026-07-15")
        check("agregado: commit novo no scope → stale",
              pattern_check.project_staleness(root) == "stale")
        check("agregado segue concordando com o por-doc",
              pattern_check.project_staleness(root)
              == pattern_check.scope_staleness(root, docpath)["state"])

        # (3) FALLBACK: doc SEM generated-commit continua na janela por data
        with open(docpath, "w") as fh:
            fh.write(_doc_with_commit("a.py", "2026-07-15"))
        check("agregado: sem generated-commit cai na janela por data → stale",
              pattern_check.project_staleness(root) == "stale")

        # (4) commit inexistente no carimbo → NÃO confia nele, cai pra data
        with open(docpath, "w") as fh:
            fh.write(_doc_with_commit("a.py", "2026-07-15", "0" * 40))
        check("agregado: generated-commit que não resolve cai pra data (não finge fresco)",
              pattern_check.project_staleness(root) == "stale")

        # (5) DEFEITO 2: scope por DIRETÓRIO. Carimba no HEAD e muda lib/b.py.
        with open(docpath, "w") as fh:
            fh.write(_doc_with_commit("lib/", "2026-07-15", head(root)))
        check("agregado: scope por diretório, nada mudou → fresh",
              pattern_check.project_staleness(root) == "fresh")
        with open(os.path.join(root, "lib", "b.py"), "w") as fh:
            fh.write("x=3\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "muda lib/b.py", date="2026-07-15")
        check("agregado: arquivo DENTRO de scope-diretório → stale "
              "(interseção crua de strings nunca pegava)",
              pattern_check.project_staleness(root) == "stale")

        # (6) doc sem generated E sem commit → imensurável; nada mensurável = unknown
        with open(docpath, "w") as fh:
            fh.write("---\nproject: X\nscope: a.py\n"
                     "doc-sig: X/a@gen=%s#abcd1234\n---\n\n# doc\n" % CURRENT_GEN)
        check("agregado: nenhum doc mensurável → unknown (nunca fresco)",
              pattern_check.project_staleness(root) == "unknown")

        # (7) DOIS docs com carimbos DIFERENTES: um grupo por sha, stale se QUALQUER um
        with open(docpath, "w") as fh:
            fh.write(_doc_with_commit("a.py", "2026-07-15", head(root)))   # fresco
        with open(os.path.join(docs, "outro.md"), "w") as fh:
            fh.write(_doc_with_commit("lib/", "2026-07-15", sha1))          # defasado
        check("agregado: dois carimbos distintos → stale se QUALQUER doc estiver",
              pattern_check.project_staleness(root) == "stale")

    # (8) fora de repo git → unknown
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude", "docs"))
        with open(os.path.join(d, ".claude", "docs", "x.md"), "w") as fh:
            fh.write(_doc_with_commit("a.py", "2026-07-01"))
        check("agregado: sem git → unknown", pattern_check.project_staleness(d) == "unknown")


def test_restamp():
    """v3.17 — o verbo que automatiza o 2º commit do rito do doc-touch.

    Existe porque um doc não consegue citar o commit que o contém: código e doc no
    MESMO commit ⇒ o carimbo só pode apontar pro anterior ⇒ a janela de staleness vê
    a mudança que a própria doc descreve e a chama de defasada. Este repo pagou isso
    3× (16211ae, b9028c3, 8d7a5a0) antes de virar comando.
    """
    import shutil
    import subprocess
    if not shutil.which("git"):
        print("  (git ausente — pulo restamp)")
        return

    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "repo")
        docs = os.path.join(root, ".claude", "docs")
        os.makedirs(docs)
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "t@t")
        _git(root, "config", "user.name", "t")
        with open(os.path.join(root, "a.py"), "w") as fh:
            fh.write("x=1\n")
        # CLAUDE.md carrega a gen do DOC-SET, que aqui está ATRÁS do código de propósito
        with open(os.path.join(root, "CLAUDE.md"), "w") as fh:
            fh.write("# C\n<!-- project-doc:v2 gen=%s -->\nx\n<!-- project-doc:v2:end -->\n" % OLD_GEN)
        docpath = os.path.join(docs, "arch.md")
        with open(docpath, "w") as fh:
            fh.write(_doc_with("a.py", "2026-01-01"))
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "codigo + doc no MESMO commit", date="2026-07-20")
        head = subprocess.run(["git", "-C", root, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True).stdout.strip()

        # o cenário do defeito: a doc foi escrita NESTE commit e aponta pra antes dele
        check("antes do restamp: doc se acusa de defasada sobre o próprio commit",
              pattern_check.scope_staleness(root, docpath)["state"] == "stale")

        out = pattern_check.restamp(root, [".claude/docs/arch.md"])
        check("restamp devolve o HEAD carimbado", out["commit"] == head)
        check("restamp carimbou 1 doc, sem pular nada",
              len(out["stamped"]) == 1 and not out["skipped"])
        check("depois do restamp: fresh (é o rito automatizado)",
              pattern_check.scope_staleness(root, docpath)["state"] == "fresh")
        check("agregado também fica fresh",
              pattern_check.project_staleness(root) == "fresh")

        fm = open(docpath, encoding="utf-8").read()
        check("generated-commit gravado no frontmatter", "generated-commit: %s" % head in fm)

        # A ARMADILHA: `--sig` cru carimba o CURRENT_GEN do CÓDIGO. O restamp tem que
        # preservar a gen do DOC-SET, senão viola o invariante "gen não bumpa" do touch.
        check("doc_set_gen lê a gen do CLAUDE.md, não a do código",
              pattern_check.doc_set_gen(root) == OLD_GEN != CURRENT_GEN)
        check("doc-sig preserva a gen do DOC-SET (não bumpa pra a do código)",
              "@gen=%s#" % OLD_GEN in fm and "@gen=%s#" % CURRENT_GEN not in fm)
        check("e o `--sig` cru continua carimbando a do CÓDIGO (a armadilha existe)",
              "@gen=%s#" % CURRENT_GEN in pattern_check.sig(docpath, root))

        # doc-sig é sha256 do CORPO: recomputada, tem que casar com o corpo atual
        esperado = pattern_check.sig(docpath, root).split("#")[1]
        check("doc-sig#hash8 casa com o corpo depois de reescrever o frontmatter",
              ("#" + esperado) in fm)

        # doc AUTORAL é intocável
        autoral = os.path.join(docs, "quality-goals.md")
        with open(autoral, "w") as fh:
            fh.write("---\ngenerated: 2026-01-01\nauthored-by: human\nproject: X\n"
                     "scope: a.py\ndoc-sig: X/a@gen=%s#abcd1234\n---\n\n# meu\n" % OLD_GEN)
        antes = open(autoral, encoding="utf-8").read()
        out = pattern_check.restamp(root, [".claude/docs/quality-goals.md"])
        check("doc autoral (authored-by: human) é PULADO",
              not out["stamped"] and out["skipped"][0]["reason"].startswith("doc autoral"))
        check("doc autoral fica byte-idêntico", open(autoral, encoding="utf-8").read() == antes)

        # arquivo sem frontmatter não é doc project-doc
        solto = os.path.join(docs, "nota.md")
        with open(solto, "w") as fh:
            fh.write("# nota solta\n")
        out = pattern_check.restamp(root, [".claude/docs/nota.md"])
        check("arquivo sem frontmatter é pulado, não corrompido",
              not out["stamped"] and "frontmatter" in out["skipped"][0]["reason"]
              and open(solto, encoding="utf-8").read() == "# nota solta\n")

        # doc inexistente não derruba a rodada
        out = pattern_check.restamp(root, [".claude/docs/nao-existe.md"])
        check("doc inexistente é pulado com motivo", out["skipped"] and not out["stamped"])

    # fora de repo git: fail-LOUD e NÃO escreve nada
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude", "docs"))
        dp = os.path.join(d, ".claude", "docs", "x.md")
        with open(dp, "w") as fh:
            fh.write(_doc_with("a.py", "2026-01-01"))
        antes = open(dp, encoding="utf-8").read()
        out = pattern_check.restamp(d, [".claude/docs/x.md"])
        check("sem git: erro explícito, nada carimbado", out["error"] and not out["stamped"])
        check("sem git: arquivo intocado (carimbo pela metade é pior que velho)",
              open(dp, encoding="utf-8").read() == antes)


def test_census_classifies_and_no_crash():
    """census() e conformance_plan() rodam sem crashar num layout mínimo de organismo."""
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "org")
        os.makedirs(os.path.join(root, ".claude", "docs"))
        with open(os.path.join(root, ".claude", "organism.yaml"), "w") as fh:
            fh.write("name: Org\nmodulos: [finance]\ncosturas:\n  - id: x\n    severidade: warn\n    aresta_msg: y\n    pontas:\n      - modulo: finance\n        globs: ['finance/**']\n      - modulo: mcp\n        globs: ['mcp/**']\n")
        os.makedirs(os.path.join(root, "finance", ".claude", "docs"))
        with open(os.path.join(root, "finance", ".claude", "docs", "db.md"), "w") as fh:
            fh.write(_doc_with("src/x.ts", "2026-07-01"))
        plan = pattern_check.conformance_plan(root)
        check("plan detecta 1 módulo a migrar (finance)",
              len(plan["migrate"]) == 1 and plan["migrate"][0]["module"] == "finance")
        check("plan aponta target modules/finance/",
              plan["migrate"][0]["target"] == ".claude/docs/modules/finance/")


def test_scope_bloco_yaml():
    """Scope escrito como lista YAML EM BLOCO (`scope:\\n  - a\\n  - b`) tem que
    ser lido igual à forma inline. Antes o `_fm_field` só olhava a mesma linha do
    campo, devolvia '' e o doc sumia do índice inverso — nunca era re-projetado
    pelo /doc-touch, em silêncio (4 dos 75 docs de um monorepo real estavam assim,
    incluindo patterns.md e database.md)."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "src"))
        for name in ("a.py", "b.py"):
            with open(os.path.join(d, "src", name), "w") as fh:
                fh.write("x=1\n")
        docpath = os.path.join(d, "doc.md")
        with open(docpath, "w") as fh:
            fh.write(
                "---\n"
                "generated: 2026-07-01\n"
                "project: X\n"
                "scope:\n"
                "  - src/a.py\n"
                "  - src/b.py\n"
                "doc-sig: X/a@gen=%s#abcd1234\n"
                "---\n\n# doc\n" % CURRENT_GEN
            )
        entries = pattern_check._scope_entries(d, docpath)
        check("scope em bloco YAML é lido", entries == ["src/a.py", "src/b.py"])

        fm, _ = pattern_check._extract_frontmatter_and_body(open(docpath).read())
        check("campo inline não regride com o ramo de bloco",
              pattern_check._fm_field(fm, "generated") == "2026-07-01")
        check("campo após a lista continua legível",
              pattern_check._fm_field(fm, "doc-sig").endswith("#abcd1234"))


def test_verified_by_do_patterns_nomeia_as_suites_de_hook():
    """As 3 suítes que provam as afirmações novas do patterns.md (canal de hook,
    GRAPHIFY_DENY, aposentadoria de órfão da skill) têm que estar no
    `verified-by:` DELE. O doc rotula essas afirmações [confirmado]; se a lista
    de provas não nomear o programa que confirma, o rótulo vira palavra dada.
    Efeito mecânico: `unscoped_new` acusa toda suíte fora de verified-by, então
    a defasagem também faz o /doc-touch escalar pra FULL sem motivo.

    Único teste do arquivo que LÊ repo real (não escreve nada) — a invariante é
    sobre o conteúdo do patterns.md deste marketplace."""
    root = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    docpath = os.path.join(root, ".claude", "docs", "patterns.md")
    check("patterns.md do repo existe", os.path.exists(docpath))
    verified = set(pattern_check._scope_entries(root, docpath, field="verified-by"))
    scope = set(pattern_check._scope_entries(root, docpath))
    suites = ("plugins/guardrails/hooks/test_scope_cop.sh",
              "plugins/graphify-guard/hooks/test_graphify_guard.sh",
              "plugins/guardrails/hooks/test_setup_skill.sh")
    for s in suites:
        check("a suíte existe no disco: " + s, os.path.exists(os.path.join(root, s)))
        check("patterns.md nomeia no verified-by: " + s, s in verified)
        # anti-tautologia: pôr suíte no `scope:` NÃO resolve — faria o doc virar
        # stale a cada edição de teste (mesma razão do comentário em
        # pattern_check.py:unscoped_new).
        check("...e NÃO no scope (suíte é prova, não fonte): " + s, s not in scope)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_in_pattern()
    test_scope_bloco_yaml()
    test_invariant_b_no_frontmatter()
    test_invariant_e_old_gen()
    test_sig_deterministic()
    test_invariant_c_missing_journal()
    test_invariant_d_missing_docsig()
    test_sig_not_self_referential_for_claude_md()
    test_invariant_a_missing_end_marker()
    test_scope_staleness()
    test_touch_and_generated_commit()
    test_project_staleness_honra_generated_commit()
    test_restamp()
    test_census_classifies_and_no_crash()
    test_verified_by_do_patterns_nomeia_as_suites_de_hook()
    print("\nTODOS OS %d CHECKS PASSARAM" % PASS)
