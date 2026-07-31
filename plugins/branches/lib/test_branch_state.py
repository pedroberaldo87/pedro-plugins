#!/usr/bin/env python3
"""Suite do branch_state.py — repositórios de mentira, uma forma de merge cada.

O que importa aqui é a DIREÇÃO do erro. Classificar de menos ("olhe antes"
numa branch que já está mergeada) custa um clique a mais. Classificar de mais
("segura" numa branch com trabalho exclusivo) apaga o trabalho que o usuário
esqueceu de mergear — que é exatamente o caso que dói, e o motivo de o módulo
existir. Todo caso ambíguo tem que cair no lado caro.

Os quatro formatos que produzem "não mergeada" no `git branch --merged` e que
o classificador tem que distinguir:
    merge normal   -> merged     (o git vê)
    squash-merge   -> equivalent (o git NÃO vê — é o buraco)
    rebase/cherry  -> equivalent (idem)
    trabalho real  -> unique     (NÃO apagar)
"""

import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import branch_state as bs  # noqa: E402

FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


class Repo(object):
    """Repositório temporário, com identidade própria pra não depender da global."""

    def __init__(self, base="main"):
        self.path = tempfile.mkdtemp(prefix="branch-state-test-")
        self.g("init", "-q", "-b", base)
        self.g("config", "user.email", "teste@exemplo.dev")
        self.g("config", "user.name", "Teste")
        self.base = base
        self.commit("primeiro", "README.md", "inicio\n")

    def g(self, *a):
        return subprocess.run(("git", "-C", self.path) + a,
                              capture_output=True, text=True)

    def commit(self, msg, fname, body):
        with open(os.path.join(self.path, fname), "w", encoding="utf-8") as fh:
            fh.write(body)
        self.g("add", "-A")
        self.g("commit", "-q", "-m", msg)
        return self.g("rev-parse", "HEAD").stdout.strip()

    def branch(self, name):
        self.g("checkout", "-q", "-b", name)

    def co(self, name):
        self.g("checkout", "-q", name)

    def cat(self, name):
        res = bs.classify(self.path)
        for b in res["branches"]:
            if b["name"] == name:
                return b
        return None

    def close(self):
        shutil.rmtree(self.path, ignore_errors=True)


def main():
    print("resolução do tronco")
    r = Repo()
    check("acha 'main' quando o remoto não diz", bs.resolve_base(r.path) == "main")
    r.close()
    r = Repo(base="master")
    check("acha 'master' num repo antigo", bs.resolve_base(r.path) == "master")
    r.close()
    r = Repo()
    try:
        bs.resolve_base(r.path, "nao-existe")
        check("base inexistente é recusada", False)
    except bs.BranchError as exc:
        check("base inexistente é recusada", "não existe" in str(exc))
    r.close()

    print("merge normal — o git vê")
    r = Repo()
    r.branch("feat/normal")
    r.commit("trabalho", "a.txt", "a\n")
    r.co("main")
    r.g("merge", "-q", "--no-ff", "-m", "merge", "feat/normal")
    b = r.cat("feat/normal")
    check("merge normal -> merged", b["category"] == "merged")
    r.close()

    print("squash-merge — O BURACO do --merged")
    r = Repo()
    r.branch("feat/squash")
    r.commit("trabalho", "b.txt", "conteudo\n")
    r.co("main")
    r.g("merge", "-q", "--squash", "feat/squash")
    r.g("commit", "-q", "-m", "squash: trabalho")
    merged = r.g("branch", "--merged", "main").stdout
    check("o git --merged NEGA a branch (é o defeito que motivou o módulo)",
          "feat/squash" not in merged)
    b = r.cat("feat/squash")
    check("mas o classificador diz equivalent", b["category"] == "equivalent")
    check("e explica que o --merged não vê", "--merged NÃO vê" in b["why"])
    r.close()

    print("rebase/cherry-pick — mesmo conteúdo, sha novo")
    # A main tem que DIVERGIR antes: com ela ancestral, o cherry-pick reproduz
    # o commit idêntico (mesmo pai, mesma árvore) e o sha nem muda — não é o
    # caso que a gente quer testar.
    r = Repo()
    r.branch("feat/cherry")
    sha = r.commit("trabalho cereja", "c.txt", "cereja\n")
    r.co("main")
    r.commit("main seguiu sozinha", "z.txt", "z\n")
    r.g("cherry-pick", sha)
    novo = r.g("rev-parse", "HEAD").stdout.strip()
    check("o cherry-pick criou um sha DIFERENTE", novo != sha)
    check("e o git --merged nega a branch",
          "feat/cherry" not in r.g("branch", "--merged", "main").stdout)
    b = r.cat("feat/cherry")
    check("cherry-pick -> equivalent", b["category"] == "equivalent")
    r.close()

    print("trabalho de verdade — NÃO apagar")
    r = Repo()
    r.branch("feat/viva")
    r.commit("trabalho exclusivo", "d.txt", "so aqui\n")
    r.co("main")
    r.commit("outra coisa na main", "e.txt", "outra\n")
    b = r.cat("feat/viva")
    check("commit exclusivo -> unique", b["category"] == "unique")
    check("diz quantos são exclusivos", "1 de 1 commit só existe aqui" in b["why"])
    check("mostra o assunto do commit órfão",
          b["orphans"]["commits"][0]["subject"] == "trabalho exclusivo")
    check("mostra o arquivo que só existe lá",
          "d.txt" in b["orphans"]["commits"][0]["files"])
    r.close()

    print("meio-termo: parte mergeada, parte não")
    r = Repo()
    r.branch("feat/meio")
    sha1 = r.commit("um", "f1.txt", "1\n")
    r.commit("dois", "f2.txt", "2\n")
    r.co("main")
    r.commit("main seguiu sozinha", "z.txt", "z\n")   # força divergência real
    r.g("cherry-pick", sha1)
    b = r.cat("feat/meio")
    check("com 1 de 2 exclusivo -> unique (o lado caro)", b["category"] == "unique")
    check("a contagem é do exclusivo, não do total",
          b["orphans"]["unique"] == 1 and b["orphans"]["total"] == 2)
    r.close()

    print("branch sem nada à frente")
    r = Repo()
    r.branch("feat/parada")
    r.co("main")
    r.commit("main andou", "g.txt", "g\n")
    b = r.cat("feat/parada")
    # o `git --merged` já pega este caso (a branch é ancestral); o ramo
    # `ahead == 0` do módulo é a rede pra quando esse comando falha.
    check("nada à frente -> merged", b["category"] == "merged")
    check("registra que está atrás", b["behind"] >= 1)
    r.close()

    print("metadados que o relatório usa")
    r = Repo()
    r.branch("feat/meta")
    r.commit("x", "h.txt", "h\n")
    b = r.cat("feat/meta")
    check("marca a branch em que estamos", b["is_head"] is True)
    check("marca que não tem remoto", b["upstream"] is None)
    check("idade sai em dias, do relógio", b["dias"] == 0)
    check("o tronco não entra na lista",
          all(x["name"] != "main" for x in bs.classify(r.path)["branches"]))
    r.close()

    print("ordenação — o que exige atenção vem primeiro")
    r = Repo()
    r.branch("feat/segura")
    r.co("main")
    r.branch("feat/perigosa")
    r.commit("exclusivo", "i.txt", "i\n")
    r.co("main")
    cats = [b["category"] for b in bs.classify(r.path)["branches"]]
    check("unique vem antes de merged", cats.index("unique") < cats.index("merged"))
    r.close()

    print("bordas")
    d = tempfile.mkdtemp(prefix="nao-repo-")
    try:
        check("diretório que não é repo é reconhecido", bs.is_repo(d) is False)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    r = Repo()
    res = bs.classify(r.path)
    check("repo só com o tronco devolve lista vazia", res["branches"] == [])
    check("mesmo assim informa o tronco", res["base"] == "main")
    r.close()

    print("stale — a contagem que o hook usa")
    r = Repo()
    r.branch("feat/nova")
    r.commit("hoje", "j.txt", "j\n")
    r.co("main")
    res = bs.classify(r.path)
    recentes = [b for b in res["branches"] if (b["dias"] or 0) >= 30]
    check("branch de hoje não conta como parada", recentes == [])
    r.close()

    print("prune — o único verbo que apaga, e suas três travas")

    class A(object):
        def __init__(self, repo, branches, **kw):
            self.repo, self.branches, self.base = repo, branches, None
            self.force = kw.get("force", False)
            self.dry_run = kw.get("dry_run", False)

    def prune_erro(repo, branches, **kw):
        try:
            bs.cmd_prune(A(repo, branches, **kw))
            return None
        except bs.BranchError as exc:
            return str(exc)

    r = Repo()
    r.branch("feat/viva")
    r.commit("trabalho que só existe aqui", "p1.txt", "p\n")
    r.co("main")
    r.commit("main andou", "p2.txt", "m\n")
    err = prune_erro(r.path, ["feat/viva"])
    check("RECUSA apagar branch com trabalho exclusivo", err is not None and "só existe" in err)
    check("e mostra o que seria perdido", "trabalho que só existe aqui" in (err or ""))
    check("a branch continua lá depois da recusa",
          "feat/viva" in r.g("branch").stdout)
    r.close()

    r = Repo()
    r.branch("feat/aqui")
    err = prune_erro(r.path, ["feat/aqui"])
    check("RECUSA apagar a branch em que você está", err is not None and "em que você está" in err)
    r.close()

    r = Repo()
    err = prune_erro(r.path, ["nao-existe"])
    check("RECUSA nome que não existe", err is not None and "não existe" in err)
    err = prune_erro(r.path, ["main"])
    check("RECUSA apagar o tronco", err is not None)
    r.close()

    r = Repo()
    r.branch("feat/segura")
    r.commit("x", "p3.txt", "x\n")
    r.co("main")
    r.g("merge", "-q", "--no-ff", "-m", "merge", "feat/segura")
    check("dry-run não apaga nada",
          bs.cmd_prune(A(r.path, ["feat/segura"], dry_run=True)) == 0
          and "feat/segura" in r.g("branch").stdout)
    bs.cmd_prune(A(r.path, ["feat/segura"]))
    check("apaga a segura de verdade", "feat/segura" not in r.g("branch").stdout)
    tags = r.g("tag").stdout
    check("e deixa a TAG DE RESGATE", "archive/feat/segura-" in tags)
    tag = [t for t in tags.splitlines() if t.startswith("archive/")][0]
    r.g("branch", "feat/segura", tag)
    check("dá pra ressuscitar com um comando", "feat/segura" in r.g("branch").stdout)
    r.close()

    r = Repo()
    r.branch("feat/forcada")
    r.commit("exclusivo", "p4.txt", "e\n")
    r.co("main")
    r.commit("main andou", "p5.txt", "m\n")
    bs.cmd_prune(A(r.path, ["feat/forcada"], force=True))
    check("--force apaga mesmo com trabalho exclusivo",
          "feat/forcada" not in r.g("branch").stdout)
    check("mas a tag de resgate SAI DO MESMO JEITO",
          "archive/feat/forcada-" in r.g("tag").stdout)
    r.close()

    print("relatório HTML")
    r = Repo()
    r.branch("feat/segura")
    r.co("main")
    r.g("merge", "-q", "--no-ff", "-m", "m", "feat/segura")
    r.branch("feat/risco")
    r.commit("exclusivo", "h1.txt", "h\n")
    r.co("main")
    r.commit("main andou", "h2.txt", "m\n")
    out = os.path.join(r.path, "rel.html")
    bs.cmd_report(A(r.path, [], **{}) if False else type("X", (), {
        "repo": r.path, "base": None, "out": out})())
    html = open(out, encoding="utf-8").read()
    check("gera HTML autocontido", html.startswith("<!DOCTYPE html") and "<style>" in html)
    check("a segura nasce MARCADA", "data-br='feat/segura' checked" in html)
    check("a de risco nasce DESMARCADA",
          "data-br='feat/risco' checked" not in html and "data-br='feat/risco'" in html)
    check("mostra o commit órfão da de risco", "exclusivo" in html)
    check("explica a tag de resgate", "archive/" in html)
    check("não depende de rede", "http://" not in html and "https://" not in html)
    r.close()

    print("varredura de vários repositórios")
    root = tempfile.mkdtemp(prefix="scan-root-")
    try:
        for nome in ("proj-a", "proj-b"):
            sub = os.path.join(root, nome)
            os.makedirs(sub)
            rr = Repo()
            for item in os.listdir(rr.path):
                shutil.move(os.path.join(rr.path, item), os.path.join(sub, item))
            shutil.rmtree(rr.path, ignore_errors=True)
            subprocess.run(("git", "-C", sub, "checkout", "-q", "-b", "feat/x"),
                           capture_output=True)
        achados = bs.scan(root)
        check("acha os 2 repositórios da pasta", len(achados) == 2)
        check("classifica cada um", all("branches" in a for a in achados))
        os.makedirs(os.path.join(root, "proj-a", "node_modules", "lixo"))
        check("não desce em node_modules", len(bs.scan(root)) == 2)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
