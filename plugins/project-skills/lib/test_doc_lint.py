#!/usr/bin/env python3
"""Testes do doc_lint.py — repo fake em tmpdir, uma fixture por camada de veredito."""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc_lint  # noqa: E402

PASSED = 0


# ── A IDENTIDADE DO GIT É UMA RECEITA SÓ ─────────────────────────────────────
# O git exige AS DUAS identidades (autor e committer) para commitar. Este arquivo
# tinha TRÊS chamadas de `git commit` e três formas diferentes: uma com `--author`
# mais o committer no ambiente, e duas só com o committer. As duas últimas
# funcionavam na máquina de quem escreveu porque o `~/.gitconfig` global preenchia
# a outra ponta — e saíam com código 128 em runner limpo, derrubando a suíte num
# CalledProcessError que não diz "faltou user.email". Consertar uma por vez foi o
# que fez a esteira quebrar duas vezes seguidas no mesmo arquivo.
GIT_ID = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
          "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git_commit(td, msg):
    """Um commit na fixture, com identidade própria e sem depender do ambiente."""
    subprocess.run(["git", "-C", td, "commit", "-qm", msg, "--no-gpg-sign"],
                   check=True, env={**os.environ, **GIT_ID},
                   stdin=subprocess.DEVNULL, start_new_session=True)


def check(name, cond):
    global PASSED
    if not cond:
        print("  FALHOU · %s" % name)
        sys.exit(1)
    print("  ok · %s" % name)
    PASSED += 1


def make_repo(td):
    subprocess.run(["git", "-C", td, "init", "-q"], check=True, stdin=subprocess.DEVNULL, start_new_session=True)
    os.makedirs(os.path.join(td, ".claude", "docs"), exist_ok=True)
    os.makedirs(os.path.join(td, "app"), exist_ok=True)
    with open(os.path.join(td, "app", "main.py"), "w", encoding="utf-8") as fh:
        fh.write("import os\n" * 3 + 'X = os.environ["REAL_API_KEY"]\n'
                 "TABLE_NAME = 'user_data'\nMY_CONSTANT_X = 1\n" + "# pad\n" * 10)
    with open(os.path.join(td, "compose.yml"), "w", encoding="utf-8") as fh:
        fh.write("services:\n  app:\n    environment:\n      - COMPOSE_VAR=${COMPOSE_VAR}\n")
    subprocess.run(["git", "-C", td, "add", "-A"], check=True, stdin=subprocess.DEVNULL, start_new_session=True)
    git_commit(td, "init")
    return subprocess.run(["git", "-C", td, "rev-parse", "HEAD"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True).stdout.strip()


def write_doc(td, name, body):
    p = os.path.join(td, ".claude", "docs", name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("---\ngenerated: 2026-07-22\nproject: t\nscope: [app/main.py]\n---\n\n" + body)
    return ".claude/docs/" + name  # casa-ok: fixture de teste, o literal e o dado do caso


def flat(out, doc):
    for d in out["docs"]:
        if d["path"] == doc:
            return d["findings"]
    return []


def main():
    with tempfile.TemporaryDirectory() as td:
        head = make_repo(td)

        # --- check 1: env-var, as 4 camadas ---
        doc = write_doc(td, "env.md", "\n".join([
            "- `REAL_API_KEY` lida pelo app",          # em R → ok
            "- `COMPOSE_VAR` do compose",              # em R (compose) → ok
            "- `MY_CONSTANT_X` e a tabela",            # em D (identificador real) → skip
            "- `GHOST_API_KEY` fantasma",              # ∉D, env-shaped → FAIL
            "- `GHOST_PLAIN_NAME` fantasma sem forma",  # ∉D, sem forma → WARN
            "- `IGNORED_SECRET_KEY` <!-- lint:ignore IGNORED_SECRET_KEY -->",  # ignore → nada
            "- fragmento `API_KEY` de REAL_API_KEY",   # sufixo de var real → skip
        ]))
        out = doc_lint.lint(td, [doc])
        f = flat(out, doc)
        toks = {(x["token"], x["severity"]) for x in f if x["check"] == "env-var"}
        check("env: fantasma env-shaped = FAIL", ("GHOST_API_KEY", "FAIL") in toks)
        check("env: fantasma sem forma = WARN", ("GHOST_PLAIN_NAME", "WARN") in toks)
        check("env: lida no código não acusa", not any(t == "REAL_API_KEY" for t, _ in toks))
        check("env: compose não acusa", not any(t == "COMPOSE_VAR" for t, _ in toks))
        check("env: identificador do repo não acusa", not any(t == "MY_CONSTANT_X" for t, _ in toks))
        check("env: lint:ignore respeitado", not any(t == "IGNORED_SECRET_KEY" for t, _ in toks))
        check("env: sufixo de var real não acusa", not any(t == "API_KEY" for t, _ in toks))

        # --- check 2: commit hash ---
        doc2 = write_doc(td, "hash.md", "\n".join([
            "- corrigido no commit `%s`" % head[:8],       # resolve → ok
            "- quebrado no commit `deadbeef1`",             # não resolve + ctx commit → FAIL
            "- finding `abc123f9` do journal",              # não resolve, sem ctx → WARN
        ]))
        out = doc_lint.lint(td, [doc2])
        f = flat(out, doc2)
        hs = {(x["token"], x["severity"]) for x in f if x["check"] == "commit-hash"}
        check("hash: resolvível não acusa", not any(t == head[:8] for t, _ in hs))
        check("hash: inexistente c/ contexto = FAIL", ("deadbeef1", "FAIL") in hs)
        check("hash: inexistente sem contexto = WARN", ("abc123f9", "WARN") in hs)

        # --- check 3: ponteiro ---
        doc3 = write_doc(td, "ptr.md", "\n".join([
            "- vivo em `app/main.py:2`",        # existe, N ok → só o WARN brando
            "- morto em `app/main.py:9999`",    # N > linhas → FAIL
            "- fantasma `app/nope.py:3`",       # arquivo não existe → FAIL
            "- parcial `main.py:2`",            # sufixo único → resolve, ok
        ]))
        out = doc_lint.lint(td, [doc3])
        f = flat(out, doc3)
        ps = [(x["token"], x["severity"]) for x in f if x["check"] == "pointer"]
        check("ptr: morto (N>linhas) = FAIL", ("app/main.py:9999", "FAIL") in ps)
        check("ptr: arquivo inexistente = FAIL", ("app/nope.py:3", "FAIL") in ps)
        check("ptr: sufixo único resolve", not any(t == "main.py:2" and s == "FAIL" for t, s in ps))
        check("ptr: 1 WARN brando por doc", sum(1 for _, s in ps if s == "WARN") == 1)

        # --- check 3b: ponteiro para arquivo fora do tronco (não commitado) ---
        # O caso real: a sessão criou a migration, documentou, e o deploy foi
        # destravado com base numa doc que fala de arquivo que ninguém mais tem.
        os.makedirs(os.path.join(td, "migrations"), exist_ok=True)
        with open(os.path.join(td, "migrations", "0007_add_col.sql"), "w", encoding="utf-8") as fh:
            fh.write("ALTER TABLE user_data ADD COLUMN x int;\n" * 4)
        doc7 = write_doc(td, "trunk.md", "\n".join([
            "- a migration `migrations/0007_add_col.sql:2` já subiu",  # não commitada → FAIL
            "- e o app em `app/main.py:2`",                            # commitado → não acusa
        ]))
        out = doc_lint.lint(td, [doc7])
        f = flat(out, doc7)
        nt = [(x["token"], x["severity"]) for x in f if x["check"] == "not-in-trunk"]
        check("tronco: arquivo não commitado = FAIL",
              ("migrations/0007_add_col.sql:2", "FAIL") in nt)
        check("tronco: arquivo commitado não acusa",
              not any(t.startswith("app/main.py") for t, _ in nt))
        check("tronco: FAIL entra no veredito do lint", out["fails"] >= 1)
        # e some assim que o arquivo entra no tronco
        subprocess.run(["git", "-C", td, "add", "-A"], check=True, stdin=subprocess.DEVNULL, start_new_session=True)
        git_commit(td, "mig")
        out = doc_lint.lint(td, [doc7])
        check("tronco: depois do commit, não acusa mais",
              not any(x["check"] == "not-in-trunk" for x in flat(out, doc7)))

        # --- check 4: contagem vs lista ---
        doc4 = write_doc(td, "count.md", "\n".join([
            "**3 modos** — os modos:", "- a", "- b", "- c", "- d", "",
        ]))
        out = doc_lint.lint(td, [doc4])
        f = flat(out, doc4)
        check("count: 3 declarado vs 4 itens = WARN",
              any(x["check"] == "count" and x["severity"] == "WARN" for x in f))

        # --- fail-OPEN: erro de ambiente nunca vira acusação (regressão) ---
        with tempfile.TemporaryDirectory() as nogit:
            r = doc_lint._commit_batch_check(nogit, {"deadbeef", "abc1234f"})
            check("fail-open: fora de repo git, nenhum hash é acusado",
                  all(r.values()))

        # --- blob/tree não é claim de commit ---
        doc5 = write_doc(td, "blob.md", "- o arquivo sobreviveu no tree (blob `abc9876f`)")
        out = doc_lint.lint(td, [doc5])
        check("blob declarado não vira FAIL de commit",
              not any(x["check"] == "commit-hash" for x in flat(out, doc5)))

        # --- ponteiro ambíguo: vivo em QUALQUER candidato = não é morto ---
        os.makedirs(os.path.join(td, "deep", "app"), exist_ok=True)
        with open(os.path.join(td, "deep", "app", "main.py"), "w", encoding="utf-8") as fh:
            fh.write("# pad\n" * 80)   # 81 linhas; o app/main.py da raiz tem ~16
        subprocess.run(["git", "-C", td, "add", "-A"], check=True, stdin=subprocess.DEVNULL, start_new_session=True)
        git_commit(td, "deep")
        doc6 = write_doc(td, "amb.md", "- ver `app/main.py:70`")
        out = doc_lint.lint(td, [doc6])
        check("ponteiro ambíguo vivo no candidato certo não vira FAIL",
              not any(x["check"] == "pointer" and x["severity"] == "FAIL"
                      for x in flat(out, doc6)))

        # --- fail-open GLOBAL: sem git, checks 1 e 3 se calam (não acusam) ---
        with tempfile.TemporaryDirectory() as nogit:
            os.makedirs(os.path.join(nogit, ".claude", "docs"))
            dp = os.path.join(nogit, ".claude", "docs", "x.md")
            with open(dp, "w", encoding="utf-8") as fh:
                fh.write("---\ngenerated: 2026-01-01\nproject: T\nscope: a.py\n"
                         "doc-sig: s\n---\n\n- `MINHA_APP_TOKEN` e `src/hub/main.py:12`\n")
            o = doc_lint.lint(nogit)
            check("sem git: nenhum FAIL fabricado (env-var + ponteiro calam)",
                  o["fails"] == 0)

        # --- falsos positivos de regex ---
        check("substantivo com _ID/_URL/_MODE não é env-shaped (só WARN)",
              not any(doc_lint.ENV_SHAPED_RE.search(t)
                      for t in ("SESSION_ID", "BASE_URL", "DEBUG_MODE", "REST_API")))
        check("_TOKEN/_SECRET seguem env-shaped",
              all(doc_lint.ENV_SHAPED_RE.search(t)
                  for t in ("MINHA_APP_TOKEN", "APP_SECRET")))
        check("'emergency' não conta como contexto de commit",
              not doc_lint.COMMIT_CONTEXT_RE.search("emergency fix"))
        check("POINTER_RE não casa tecnologia:versão (Node.js:20)",
              not doc_lint.POINTER_RE.findall("roda Node.js:20 e Next.js:14"))
        check("POINTER_RE segue casando path real",
              doc_lint.POINTER_RE.findall("ver src/app/main.py:12"))
        check("lint:ignore aceita hash minúsculo e path",
              doc_lint.IGNORE_INLINE_RE.findall("<!-- lint:ignore a1b2c3d -->") != [])

        # --- allowlist de arquivo ---
        os.makedirs(os.path.join(td, ".claude", ".project-doc"), exist_ok=True)
        with open(os.path.join(td, ".claude", ".project-doc", "lint-allow.txt"), "w", encoding="utf-8") as fh:
            fh.write("GHOST_API_KEY\n")
        out = doc_lint.lint(td, [doc])
        f = flat(out, doc)
        check("allowlist de arquivo suprime FAIL",
              not any(x["token"] == "GHOST_API_KEY" for x in f))

    test_fail_open_property()
    print("\nTODOS OS %d CHECKS PASSARAM" % PASSED)


def test_fail_open_property():
    """PROPRIEDADE, não caso: nenhuma função que toca git pode ACUSAR quando o
    ambiente falha. Falha-fechado apareceu 4× em 2 rodadas de revisão (batch-check,
    ls-files, _nlines, returncode) — este teste é a rede pra classe inteira, pra
    não depender de alguém lembrar a cada função nova.

    Contrato: sem git / git quebrado ⇒ lint não produz FAIL, e staleness devolve
    'unknown' (nunca 'fresh', que seria fingir que está em dia)."""
    import shutil
    import sys as _sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import pattern_check as pc

    doc = ("---\ngenerated: 2026-01-01\ngenerated-commit: abc1234\nproject: T\n"
           "scope: [a.py, lib/]\ndoc-sig: s\n---\n\n"
           "- `MINHA_APP_TOKEN` em `src/hub/main.py:12`, commit `deadbeef`\n")

    def build(td, mode):
        os.makedirs(os.path.join(td, ".claude", "docs"))
        with open(os.path.join(td, ".claude", "docs", "x.md"), "w", encoding="utf-8") as fh:
            fh.write(doc)
        if mode == "git-quebrado":       # .git existe mas é lixo → git exit≠0
            os.makedirs(os.path.join(td, ".git"))
            with open(os.path.join(td, ".git", "HEAD"), "w", encoding="utf-8") as fh:
                fh.write("lixo\n")
        elif mode == "worktree-falso":   # .git é ARQUIVO apontando pra lugar nenhum
            with open(os.path.join(td, ".git"), "w", encoding="utf-8") as fh:
                fh.write("gitdir: /nao/existe\n")

    for mode in ("sem-git", "git-quebrado", "worktree-falso"):
        with tempfile.TemporaryDirectory() as td:
            build(td, mode)
            out = doc_lint.lint(td)
            check("fail-open [%s]: lint não fabrica FAIL" % mode, out["fails"] == 0)
            st = pc.scope_staleness(td, os.path.join(td, ".claude", "docs", "x.md"))
            check("fail-open [%s]: staleness nunca finge 'fresh'" % mode,
                  st["state"] in ("unknown", "stale"))
            tp = pc.touch_plan(td)
            check("fail-open [%s]: touch_plan não inventa trabalho" % mode,
                  isinstance(tp.get("pending_docs"), list))
    del shutil, _sys


if __name__ == "__main__":
    main()
