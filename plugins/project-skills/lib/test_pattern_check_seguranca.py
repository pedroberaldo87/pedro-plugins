#!/usr/bin/env python3
"""
test_pattern_check_seguranca.py — regressões de segurança do pattern_check / journal.

Três achados do scan de segurança (repositório clonado e hostil):

  1. `ledger.json` versionado traz `last_commit: "--output=<arquivo>"`. O valor virava
     argumento NU do `git log` e o git sobrescrevia o arquivo do usuário. Agora:
     `last_commit` só vale como hex de 7-64 caracteres, tanto no `load_ledger` quanto
     em cada ponto de uso, e a revisão vai depois de `--end-of-options` (git >= 2.24).
  2. `restamp` gravava via `<doc>.md.tmp` (nome previsível). Um `.tmp` versionado como
     symlink fazia o carimbo escrever FORA do projeto. Agora: mkstemp + os.replace, e
     doc cujo realpath cai fora do projeto é recusado.
  3. `restamp` passava texto derivado do doc (nome do projeto) como TEMPLATE de
     substituição do `re.sub`. `\\1` no nome derrubava o carimbo; agora é callable.

Self-contained: HOME, TMPDIR e a configuração do git ficam num sandbox; nada do
usuário é tocado. Roda com:  python3 plugins/project-skills/lib/test_pattern_check_seguranca.py
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# Sandbox ANTES de importar/rodar qualquer coisa que chame git.
_SANDBOX = tempfile.mkdtemp(prefix="pc-seg-")
atexit.register(shutil.rmtree, _SANDBOX, ignore_errors=True)
for _sub in ("home", "tmp"):
    os.makedirs(os.path.join(_SANDBOX, _sub))
os.environ["HOME"] = os.path.join(_SANDBOX, "home")
os.environ["TMPDIR"] = os.path.join(_SANDBOX, "tmp")
tempfile.tempdir = os.environ["TMPDIR"]
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ["GIT_AUTHOR_NAME"] = os.environ["GIT_COMMITTER_NAME"] = "t"
os.environ["GIT_AUTHOR_EMAIL"] = os.environ["GIT_COMMITTER_EMAIL"] = "t@example.com"

import journal  # noqa: E402
import pattern_check  # noqa: E402

PASS = 0


def check(label, cond):
    global PASS
    assert cond, "FALHOU: " + label
    PASS += 1
    print("  ok ·", label)


def _git(root, *args):
    return subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                          start_new_session=True)


def _repo(base, name="repo"):
    root = os.path.join(base, name)
    os.makedirs(os.path.join(root, ".claude", "docs"))
    _git(root, "init", "-q")
    with open(os.path.join(root, "a.py"), "w", encoding="utf-8") as fh:
        fh.write("x=1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def _head(root):
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _write_ledger(root, last_commit):
    sd = os.path.join(root, ".claude", ".project-doc")
    os.makedirs(sd, exist_ok=True)
    with open(os.path.join(sd, "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump({"mined_sessions": {}, "last_commit": last_commit, "distilled_hashes": {}}, fh)


def _doc(project="X", scope="a.py"):
    return ("---\ngenerated: 2026-01-01\nproject: %s\nscope: %s\n"
            "doc-sig: X/a@gen=%s#abcd1234\n---\n\n# doc\n" % (project, scope, pattern_check.CURRENT_GEN))


def _touch_plan_cli(root):
    """Roda o MESMO caminho do hook Stop (CLI --touch-plan --json). (resultado, stderr)."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "pattern_check.py"),
                        "--project-root", root, "--touch-plan", "--json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, timeout=60)
    return json.loads(r.stdout), r.stderr


# ---------------------------------------------------------------------------
# Achado 1 — last_commit do ledger não vira opção do git
# ---------------------------------------------------------------------------
def test_ledger_last_commit_nao_injeta_opcao_no_git():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        vitima = os.path.join(d, "vitima.txt")

        # (a) o arquivo NÃO existe: o git não pode criá-lo
        _write_ledger(root, "--output=" + vitima)
        res, err = _touch_plan_cli(root)
        check("ledger '--output=<arq>': arquivo não é criado", not os.path.exists(vitima))
        check("ledger '--output=<arq>': idade do último FULL = null (não sei)",
              res.get("last_full_age_days") is None)
        check("ledger '--output=<arq>': ignorado COM aviso no stderr",
              "last_commit" in err and "ignor" in err.lower())
        check("ledger '--output=<arq>': o valor hostil não é ecoado como last_commit",
              res.get("ledger_last_commit") is None)

        # (b) o arquivo EXISTE: o conteúdo não pode ser truncado
        with open(vitima, "w", encoding="utf-8") as fh:
            fh.write("conteudo do usuario\n")
        pattern_check.touch_plan(root)
        pattern_check._commit_age_days(root, "--output=" + vitima)
        check("ledger '--output=<arq>': arquivo existente fica intacto",
              open(vitima, encoding="utf-8").read() == "conteudo do usuario\n")

        # (c) as mesmas guardas no journal (mesmo ledger, outro leitor)
        check("journal.load_ledger descarta last_commit que não é hex",
              journal.load_ledger(root)["last_commit"] is None)
        check("journal._commit_reachable recusa valor com cara de opção",
              journal._commit_reachable(root, "--output=" + vitima) is False)
        journal.run_update(root)
        check("journal.run_update com ledger hostil: arquivo existente fica intacto",
              open(vitima, encoding="utf-8").read() == "conteudo do usuario\n")


def test_ledger_com_commit_valido_continua_dando_idade():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        head = _head(root)
        _write_ledger(root, head)
        res, err = _touch_plan_cli(root)
        check("commit de 40 hex: idade em dias continua saindo",
              isinstance(res.get("last_full_age_days"), float))
        check("commit de 40 hex: ledger_last_commit é o próprio sha",
              res.get("ledger_last_commit") == head)
        check("commit de 40 hex: nenhum aviso", "ignor" not in err.lower())
        _write_ledger(root, head[:7])
        check("sha abreviado (7 hex) também vale",
              isinstance(pattern_check.touch_plan(root).get("last_full_age_days"), float))
        check("load_ledger aceita hex válido",
              journal.load_ledger(root)["last_commit"] == head[:7])


def test_valores_invalidos_de_last_commit():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        ruins = ["--output=x", "-n1", "HEAD", "abc", "ABCDEF0123", "g" * 40, "a" * 65,
                 "abc1234 --output=x", "abc1234\n", "abc1234\n\n", 123456789, ["abc1234"], {"a": 1}, ""]
        for v in ruins:
            _write_ledger(root, v)
            got = journal.load_ledger(root)["last_commit"]
            check("load_ledger(%r) → None" % (v,), got is None)
            check("_commit_age_days(%r) → None" % (v,),
                  pattern_check._commit_age_days(root, v) is None)


def test_valid_sha_exige_fullmatch():
    """`$` aceitava uma quebra de linha final; o contrato é hex puro de 7-64 caracteres."""
    for mod in (journal, pattern_check):
        nome = mod.__name__
        check("%s.valid_sha('abc1234\\n') → False" % nome, mod.valid_sha("abc1234\n") is False)
        check("%s.valid_sha('abc1234') → True" % nome, mod.valid_sha("abc1234") is True)
        check("%s.valid_sha('a'*64) → True" % nome, mod.valid_sha("a" * 64) is True)
    # as duas cópias não podem divergir (cada módulo guarda a sua de propósito)
    amostras = ["abc1234", "abc1234\n", "ABC1234", "a" * 6, "a" * 7, "a" * 64, "a" * 65, "", " abc1234",
                "abc1234 ", "--output=x", 7, None]
    check("journal.valid_sha e pattern_check.valid_sha concordam em todas as amostras",
          all(journal.valid_sha(v) == pattern_check.valid_sha(v) for v in amostras))


def test_revisao_vai_depois_de_end_of_options():
    """Se o git entende --end-of-options (>= 2.24), a revisão nunca é lida como opção."""
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        probe = _git(root, "log", "-1", "--format=%H", "--end-of-options", "HEAD")
        if probe.returncode != 0:
            print("  (git sem --end-of-options — a validação hex segura sozinha)")
            return
        check("o probe de --end-of-options funciona neste git",
              pattern_check._end_of_options() == ["--end-of-options"])
        seen = []
        real = subprocess.run

        def espiao(args, *a, **kw):
            seen.append(list(args))
            return real(args, *a, **kw)

        subprocess.run = espiao
        try:
            pattern_check._commit_age_days(root, _head(root))
        finally:
            subprocess.run = real
        logs = [a for a in seen if "log" in a]
        check("git log da idade usa --end-of-options antes do sha",
              bool(logs) and logs[-1].index("--end-of-options") < logs[-1].index(_head(root)))


# ---------------------------------------------------------------------------
# Achado 2 — restamp grava de forma segura
# ---------------------------------------------------------------------------
def test_restamp_nao_segue_tmp_symlink():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        docp = os.path.join(root, ".claude", "docs", "arch.md")
        with open(docp, "w", encoding="utf-8") as fh:
            fh.write(_doc())
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "doc")
        vitima = os.path.join(d, "vitima.txt")
        with open(vitima, "w", encoding="utf-8") as fh:
            fh.write("conteudo do usuario\n")
        os.symlink(vitima, docp + ".tmp")

        out = pattern_check.restamp(root, [".claude/docs/arch.md"])  # casa-ok: fixture de teste
        check("restamp com <doc>.tmp symlink: carimbou o doc", len(out["stamped"]) == 1)
        check("o alvo do symlink .tmp não foi escrito",
              open(vitima, encoding="utf-8").read() == "conteudo do usuario\n")
        check("o doc recebeu o carimbo", "generated-commit:" in open(docp, encoding="utf-8").read())
        check("o symlink .tmp continua lá, intocado", os.path.islink(docp + ".tmp"))
        sobras = [n for n in os.listdir(os.path.dirname(docp)) if n.endswith(".tmp") and n != "arch.md.tmp"]
        check("nenhum temporário aleatório sobra", sobras == [])

        # revisão autoral usa o mesmo idioma
        autoral = os.path.join(root, ".claude", "docs", "autoral.md")
        with open(autoral, "w", encoding="utf-8") as fh:
            fh.write("---\nauthored-by: human\ngenerated: 2026-01-01\nscope: a.py\n---\ncorpo\n")
        os.symlink(vitima, autoral + ".tmp")
        out = pattern_check.restamp(root, [".claude/docs/autoral.md"], revisado=True)  # casa-ok: fixture de teste
        check("revisão autoral com .tmp symlink: carimbou", len(out["stamped"]) == 1)
        check("revisão autoral: alvo do symlink intocado",
              open(vitima, encoding="utf-8").read() == "conteudo do usuario\n")


def test_restamp_recusa_doc_fora_do_projeto():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        fora = os.path.join(d, "fora.md")
        original = _doc()
        with open(fora, "w", encoding="utf-8") as fh:
            fh.write(original)
        link = os.path.join(root, ".claude", "docs", "ponte.md")
        os.symlink(fora, link)
        out = pattern_check.restamp(root, [".claude/docs/ponte.md"])  # casa-ok: fixture de teste
        check("doc cujo realpath cai fora do projeto é pulado", out["stamped"] == [] and len(out["skipped"]) == 1)
        check("o motivo diz que está fora do projeto", "fora do projeto" in out["skipped"][0]["reason"])
        check("o arquivo de fora fica byte-idêntico", open(fora, encoding="utf-8").read() == original)
        out = pattern_check.restamp(root, [fora])
        check("caminho absoluto fora do projeto também é pulado", out["stamped"] == [])

        # symlink que fica DENTRO do projeto continua valendo: grava no alvo, mantém o link
        real = os.path.join(root, ".claude", "docs", "real.md")
        with open(real, "w", encoding="utf-8") as fh:
            fh.write(_doc())
        dentro = os.path.join(root, ".claude", "docs", "apelido.md")
        os.symlink(real, dentro)
        out = pattern_check.restamp(root, [".claude/docs/apelido.md"])  # casa-ok: fixture de teste
        check("symlink para dentro do projeto: carimbado", len(out["stamped"]) == 1)
        check("o symlink continua symlink", os.path.islink(dentro))
        check("o alvo recebeu o carimbo", "generated-commit:" in open(real, encoding="utf-8").read())


def _fm_sig(texto):
    for linha in texto.splitlines():
        if linha.startswith("doc-sig:"):
            return linha.split(":", 1)[1].strip()
    return None


def test_restamp_sig_de_symlink_usa_o_nome_do_link():
    """Sem `scope:` o escopo da sig vem do NOME do arquivo. O verificador calcula a sig sobre o
    caminho do link; o carimbo tem de usar o mesmo nome (não o do alvo), senão nunca casa."""
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        docs = os.path.join(root, ".claude", "docs")
        sem_scope = "---\ngenerated: 2026-01-01\nproject: P\ndoc-sig: P/x@gen=%s#abcd1234\n---\n\n# doc\n" % (
            pattern_check.CURRENT_GEN)
        alvo = os.path.join(docs, "bar.md")
        link = os.path.join(docs, "foo.md")
        with open(alvo, "w", encoding="utf-8") as fh:
            fh.write(sem_scope)
        os.symlink(alvo, link)
        out = pattern_check.restamp(root, [".claude/docs/foo.md"])  # casa-ok: fixture de teste
        check("symlink sem scope: carimbado", len(out["stamped"]) == 1)
        check("o symlink continua symlink", os.path.islink(link))
        gravada = _fm_sig(open(alvo, encoding="utf-8").read())
        check("a sig gravada usa o nome do link (P/foo), não o do alvo", gravada.startswith("P/foo@gen="))
        check("a sig gravada é a que o verificador calcula sobre o link",
              gravada == pattern_check.sig(link, root))
        check("a sig devolvida pelo restamp é a gravada", out["stamped"][0]["doc_sig"] == gravada)


def test_restamp_symlink_fica_dentro_da_pasta_de_docs():
    """Um symlink só é seguido se o alvo for um .md dentro da pasta de docs; apontar para outro
    arquivo do projeto (ledger.json, README fora da doc) não pode reescrever esse arquivo."""
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        docs = os.path.join(root, ".claude", "docs")
        alvos_ruins = {
            "ledger": os.path.join(root, ".claude", ".project-doc", "ledger.json"),
            "readme": os.path.join(root, "README.md"),
            "texto": os.path.join(docs, "dados.txt"),
        }
        os.makedirs(os.path.dirname(alvos_ruins["ledger"]), exist_ok=True)
        for nome, alvo in alvos_ruins.items():
            with open(alvo, "w", encoding="utf-8") as fh:
                fh.write(_doc())
            link = os.path.join(docs, "link-%s.md" % nome)
            os.symlink(alvo, link)
            out = pattern_check.restamp(root, [".claude/docs/link-%s.md" % nome])  # casa-ok: fixture de teste
            check("symlink → %s: pulado" % nome, out["stamped"] == [] and len(out["skipped"]) == 1)
            check("symlink → %s: o alvo fica byte-idêntico" % nome,
                  open(alvo, encoding="utf-8").read() == _doc())
        # subpasta da própria pasta de docs continua valendo
        os.makedirs(os.path.join(docs, "modules"))
        sub = os.path.join(docs, "modules", "m.md")
        with open(sub, "w", encoding="utf-8") as fh:
            fh.write(_doc())
        os.symlink(sub, os.path.join(docs, "atalho.md"))
        out = pattern_check.restamp(root, [".claude/docs/atalho.md"])  # casa-ok: fixture de teste
        check("symlink → .md em subpasta da pasta de docs: carimbado", len(out["stamped"]) == 1)
        check("o alvo na subpasta recebeu o carimbo", "generated-commit:" in open(sub, encoding="utf-8").read())


def test_restamp_preserva_modo_do_arquivo():
    if os.name == "nt":
        return
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        docp = os.path.join(root, ".claude", "docs", "arch.md")
        with open(docp, "w", encoding="utf-8") as fh:
            fh.write(_doc())
        os.chmod(docp, 0o640)
        pattern_check.restamp(root, [".claude/docs/arch.md"])  # casa-ok: fixture de teste
        check("mkstemp cria 0600 mas o modo original (0640) é preservado",
              (os.stat(docp).st_mode & 0o777) == 0o640)


# ---------------------------------------------------------------------------
# Achado 3 — texto do doc nunca é template de re.sub
# ---------------------------------------------------------------------------
def test_restamp_nome_de_projeto_com_barra_invertida():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        docs = os.path.join(root, ".claude", "docs")
        for nome, projeto in (("um.md", "a\\1b"), ("dois.md", "c\\g<0>d"), ("tres.md", "e\\")):
            with open(os.path.join(docs, nome), "w", encoding="utf-8") as fh:
                fh.write(_doc(project=projeto))
        with open(os.path.join(root, "CLAUDE.md"), "w", encoding="utf-8") as fh:
            fh.write("# C\n<!-- project-doc:v2 gen=3.\\1 -->\nx\n<!-- project-doc:v2:end -->\n")
        out = pattern_check.restamp(root, [".claude/docs/um.md", ".claude/docs/dois.md",  # casa-ok: fixture de teste
                                           ".claude/docs/tres.md"])  # casa-ok: fixture de teste
        check("três nomes com barra invertida: os três carimbados", len(out["stamped"]) == 3)
        check("nenhum pulado nem erro", out["skipped"] == [] and out["error"] is None)
        um = open(os.path.join(docs, "um.md"), encoding="utf-8").read()
        dois = open(os.path.join(docs, "dois.md"), encoding="utf-8").read()
        tres = open(os.path.join(docs, "tres.md"), encoding="utf-8").read()
        check("\\1 no nome vai LITERAL pra doc-sig", "doc-sig: a\\1b/a.py@gen=3.\\1#" in um)
        check("\\g<0> no nome vai LITERAL, sem expandir", "doc-sig: c\\g<0>d/a.py@gen=3.\\1#" in dois)
        check("barra final solta não quebra", "doc-sig: e\\/a.py@gen=3.\\1#" in tres)


def test_restamp_re_error_vira_pulado_nao_crash():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        docp = os.path.join(root, ".claude", "docs", "arch.md")
        with open(docp, "w", encoding="utf-8") as fh:
            fh.write(_doc())
        import re
        real_sub = re.sub

        def quebrado(*a, **kw):
            raise re.error("invalid group reference")

        pattern_check.re.sub = quebrado
        try:
            out = pattern_check.restamp(root, [".claude/docs/arch.md"])  # casa-ok: fixture de teste
        finally:
            pattern_check.re.sub = real_sub
        check("re.error no carimbo: reportado como pulado", len(out["skipped"]) == 1 and out["stamped"] == [])
        check("o motivo cita o carimbo recusado", "re" in out["skipped"][0]["reason"].lower())
        check("o doc fica intacto", open(docp, encoding="utf-8").read() == _doc())


if __name__ == "__main__":
    if not shutil.which("git"):
        print("  (git ausente — pulo)")
        sys.exit(0)
    test_ledger_last_commit_nao_injeta_opcao_no_git()
    test_ledger_com_commit_valido_continua_dando_idade()
    test_valores_invalidos_de_last_commit()
    test_valid_sha_exige_fullmatch()
    test_revisao_vai_depois_de_end_of_options()
    test_restamp_nao_segue_tmp_symlink()
    test_restamp_recusa_doc_fora_do_projeto()
    test_restamp_sig_de_symlink_usa_o_nome_do_link()
    test_restamp_symlink_fica_dentro_da_pasta_de_docs()
    test_restamp_preserva_modo_do_arquivo()
    test_restamp_nome_de_projeto_com_barra_invertida()
    test_restamp_re_error_vira_pulado_nao_crash()
    print("\nTODOS OS %d CHECKS PASSARAM" % PASS)
