#!/usr/bin/env python3
"""Suíte do pr_externo.py — sem rede: o `gh` é trocado por respostas de mentira.

A direção do erro que importa: LIBERAR um PR que devia estar barrado custa o
tempo de quem mantém o projeto alheio. Todo caso duvidoso tem que cair em
bloqueio ou em pedido de confirmação. O contrário (barrar PR para repositório
do próprio usuário, ou comando que só MENCIONA a abertura) também é defeito,
porque ensina a pessoa a desligar a trava.
"""

import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pr_externo as pe  # noqa: E402

FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def estado(res, portao):
    return [e for p, e, _ in res if p == portao][0]


WORKFLOW = """name: CI
on:
  pull_request:
    paths: ['**.rs']
jobs:
  codestyle:
    runs-on: ubuntu-latest
    steps:
      - run: cargo fmt -- --check
# comentário na coluna zero, entre dois jobs
  lint:
    needs: [codestyle]
    steps:
      - uses: actions-rs/cargo@v1
        with:
          command: clippy
          args: --all-targets --all-features -- -D warnings
  test:
    strategy:
      matrix:
        os: [macos-latest]
"""


def dossie_verde():
    return {
        "repo": "dono/projeto", "branch": "fix/x", "base": "main", "dir": ".",
        "natureza": {"tipo": "correcao", "seguranca": "nao", "origem": "proprio"},
        "duplicatas": {"termos": ["a", "b", "c"], "achados": [
            {"tipo": "issue", "numero": 7, "estado": "open", "titulo": "bug", "veredito": "relacionado-nao-resolve"}]},
        "regras": {"arquivos": [{"caminho": "CONTRIBUTING.md", "anotacao": "rodar fmt e clippy"}],
                   "jobs": {"ci/lint": {"opcoes": []}, "ci/test": {"opcoes": []}},
                   "politica_ia": "ausente", "licenca": "MIT"},
        "ci": {"ci/lint": {"branch": 0, "base": 0, "head": "abc"}, "ci/test": {"branch": 0, "base": 0, "head": "abc"}},
        "coerencia": {"head": "abc", "arquivos": ["src/a.rs"], "bloqueios": [], "avisos": [],
                      "precedente": {"numero": 10, "titulo": "t", "arquivos": ["src/a.rs"]}},
        "corpo": {"bloqueios": []},
    }


def com(mudanca):
    d = dossie_verde()
    mudanca(d)
    return pe.avalia(d, "abc")


print("workflow: o que dispara em pull request e quais são os jobs")
jobs = pe.jobs_de_pull_request(WORKFLOW)
check("acha os três jobs, mesmo com comentário na coluna zero entre eles", list(jobs) == ["codestyle", "lint", "test"])
check("chave aninhada (steps, strategy) não vira job", "strategy" not in jobs and "steps" not in jobs)
check("guarda as opções do job de lint", pe.opcoes_do_trecho(jobs["lint"]) == ["--all-features", "--all-targets"])
check("workflow só de push não entra", pe.jobs_de_pull_request("on:\n  push:\n    tags: ['v*']\njobs:\n  b:\n    runs-on: x\n") == {})
check("`branches: [pull_request]` debaixo de push não conta como disparo",
      pe.jobs_de_pull_request("on:\n  push:\n    branches: [pull_request]\njobs:\n  b:\n    runs-on: x\n") == {})
check("on: [push, pull_request] numa linha", list(pe.jobs_de_pull_request("on: [push, pull_request]\njobs:\n  a:\n    runs-on: x\n")) == ["a"])
check("on: pull_request numa linha", list(pe.jobs_de_pull_request("on: pull_request\njobs:\n  a:\n    runs-on: x\n")) == ["a"])
check("jobs: antes de on:", list(pe.jobs_de_pull_request("jobs:\n  a:\n    runs-on: x\non:\n  pull_request:\n")) == ["a"])
check("job escrito numa linha só", list(pe.jobs_de_pull_request("on: pull_request\njobs:\n  a: {runs-on: x}\n  b:\n    runs-on: y\n")) == ["a", "b"])
check("recuo de 4 espaços e fim de linha do Windows",
      list(pe.jobs_de_pull_request("on:\r\n    pull_request:\r\njobs:\r\n    a:\r\n        runs-on: x\r\n")) == ["a"])

print("arquivo de regra")
check("CONTRIBUTING na raiz", pe.e_arquivo_de_regra("CONTRIBUTING.md"))
check("AGENTS.md na raiz (instrução para agente é regra da casa)", pe.e_arquivo_de_regra("AGENTS.md"))
check("modelo de PR em .github", pe.e_arquivo_de_regra(".github/pull_request_template.md"))
check("CONTRIBUTING de uma dependência embutida não é regra do repositório", not pe.e_arquivo_de_regra("vendor/lib/CONTRIBUTING.md"))

print("dado que não pode ir a público")


def classes(texto):
    return set(c for c, _ in pe.varre_segredos(texto))


check("token clássico do GitHub", "chave ou token" in classes("x ghp_" + "a" * 36))
check("token novo do GitHub", "chave ou token" in classes("github_pat_" + "A1" * 20))
check("caminho de máquina", "caminho da sua máquina" in classes("em /Users/" + "fulano/proj"))
check("caminho de máquina no Windows", "caminho da sua máquina" in classes("C:\\Users\\" + "fulano\\x"))
check("conta genérica de esteira não é dado pessoal", classes("/home/" + "runner/work") == set())
check("/home/ dentro de endereço web não é caminho", classes("https://site.com/home/index.html") == set())
check("e-mail pessoal", "e-mail" in classes("fulano@" + "empresa.com.br"))
check("noreply do GitHub é isento", classes("1+x@users.noreply.github.com") == set())
check("'noreply' no nome de um e-mail comum NÃO isenta", "e-mail" in classes("noreply.fulano@" + "gmail.com"))
check("endereço ssh do GitHub não é e-mail", classes("git@github.com:dono/repo.git") == set())
check("rede local", "endereço de rede local" in classes("host 192.168." + "4.5"))
check("nome de aparelho na rede local", "nome de aparelho na rede local" in classes("http://sala" + ".local/"))
check("código comum com .local não é acusado", classes("self.local = threading.local()  # settings.local.json .env.local") == set())
check("caminho de máquina em endereço file://", "caminho da sua máquina" in classes("file:///Users/" + "fulano/x"))
check("texto limpo passa", classes("Loading <Obsession> from <Animotion>") == set())
check("só linha nova do diff conta", pe.linhas_novas("--- a\n+++ b\n-velho\n+novo\n contexto") == "novo")

print("convenção de título de commit")
conv = ["feat: a", "fix(x): b", "docs: c", "chore: d", "Merge pull request #1", "build(deps): bump x from 1 to 2"]
check("histórico em Conventional Commits é reconhecido", pe.convencao_de_titulo(conv) == ("conventional", False))
check("histórico 'área: descrição' é reconhecido", pe.convencao_de_titulo(["mpris: a", "ci: b", "dbus_mpris: c", "docs: d", "config: e"])[0] == "area")
check("histórico livre não vira regra", pe.convencao_de_titulo(["Add x", "Fix y", "update z", "Remove w"]) == (None, False))
check("convenção escrita vale mesmo com histórico bagunçado", pe.convencao_de_titulo(["Add x"], declarada=True) == ("conventional", True))
check("título fora da convenção é acusado", not pe.titulo_segue("update librespot", "conventional"))
check("título dentro da convenção passa", pe.titulo_segue("fix(player): pick the right track", "conventional"))

print("repositório alvo")
check("dono/nome", pe.normaliza_repo("dono/projeto") == "dono/projeto")
check("endereço web", pe.normaliza_repo("https://github.com/dono/projeto.git") == "dono/projeto")
check("endereço ssh", pe.normaliza_repo("git@github.com:dono/projeto.git") == "dono/projeto")
check("variável não resolvida não vira repositório", pe.normaliza_repo("$UP") is None)

print("comando que abre PR")


def ab(cmd):
    return pe.aberturas_de_pr(cmd)


check("comando comum não abre PR", ab("git push origin main") == [])
check("gh pr view não abre PR", ab("gh pr view 3 --repo a/b") == [])
check("lê --repo, --head e --body-file", [(x["repo"], x["head"], x["body_file"]) for x in ab('gh pr create --repo dono/projeto --head eu:fix/x --title "t" --body-file c.md')] == [("dono/projeto", "eu:fix/x", "c.md")])
check("gh pr new também abre PR", len(ab("gh pr new -R a/b")) == 1)
check("opção entre gh e pr", [x["repo"] for x in ab("gh -R a/b pr create")] == ["a/b"])
check("opção entre pr e create", [x["repo"] for x in ab("gh pr --repo a/b create")] == ["a/b"])
check("create entre aspas", len(ab("gh pr 'create' -R a/b")) == 1)
check("comando quebrado em duas linhas com barra", [x["repo"] for x in ab("gh pr \\\n  create --repo a/b")] == ["a/b"])
check("o --repo de OUTRO comando da mesma linha não contamina", [x["repo"] for x in ab("gh pr create --repo dono/projeto && gh pr view --repo eu/meu")] == ["dono/projeto"])
check("cd antes do comando é lembrado", [x["cd"] for x in ab("cd ../clone && gh pr create --fill")] == ["../clone"])
check("GH_REPO= na frente vale como alvo", [x["repo"] for x in ab("GH_REPO=a/b gh pr create")] == ["a/b"])
check("bash -c é aberto e lido", [x["repo"] for x in ab("bash -c 'gh pr create -R a/b'")] == ["a/b"])
check("gh api criando PR conta", [(x["repo"], x["via"]) for x in ab("gh api repos/a/b/pulls -f title=t -f head=x -f base=main")] == [("a/b", "gh api")])
check("gh api só LENDO os PRs não conta", ab("gh api repos/a/b/pulls") == [])
check("hub pull-request conta", [x["via"] for x in ab("hub pull-request -m x")] == ["hub"])
check("echo que só MENCIONA o comando não abre PR", ab("echo 'depois rode gh pr create'") == [])
check("mensagem de commit que menciona não abre PR", ab('git commit -m "docs: como usar gh pr create"') == [])
check("grep pelo texto não abre PR", ab("grep -rn 'gh pr create' .") == [])
check("linha de comentário antes do comando não esconde a abertura", [x["repo"] for x in ab("# abre o PR\ngh pr create --repo a/b")] == ["a/b"])
check("comentário no fim da linha anterior não esconde a abertura", [x["repo"] for x in ab("git push -u origin x # envia\ngh pr create -R a/b")] == ["a/b"])
check("dentro de $(…) entre aspas", [x["repo"] for x in ab('URL="$(gh pr create --repo a/b)"')] == ["a/b"])
check("dentro de crases", [x["repo"] for x in ab("U=`gh pr create -R a/b`")] == ["a/b"])
check("dentro de if", [x["repo"] for x in ab("if gh pr create -R a/b; then echo ok; fi")] == ["a/b"])
check("dentro de for … do", [x["repo"] for x in ab("for i in 1; do gh pr create -R a/b; done")] == ["a/b"])
check("dentro de chaves", [x["repo"] for x in ab("{ gh pr create -R a/b; }")] == ["a/b"])
check("atrás de timeout", [x["repo"] for x in ab("timeout 60 gh pr create -R a/b")] == ["a/b"])
check("dentro de eval", [x["repo"] for x in ab("eval 'gh pr create -R a/b'")] == ["a/b"])
check("-R colado no valor", [x["repo"] for x in ab("gh pr create -Ra/b")] == ["a/b"])
check("export GH_REPO vale para o comando seguinte", [x["repo"] for x in ab("export GH_REPO=a/b; gh pr create")] == ["a/b"])
check("pushd conta como mudança de pasta", [x["cd"] for x in ab("pushd ../clone && gh pr create")] == ["../clone"])
check("programa em variável: não dá para ler, pede decisão (None)", ab("$G pr create -R a/b") is None)
check("curl criando PR pela API: pede decisão (None)", ab("curl -X POST https://api.github.com/repos/a/b/pulls -d @x.json") is None)
check("mensagem de commit em várias linhas com #12 não esconde o comando seguinte",
      [x["repo"] for x in ab('git commit -m "fix: x\n\nCloses #12" && gh pr create --repo a/b')] == ["a/b"])
check("--body em várias linhas com #12 continua sendo lido como abertura",
      [(x["repo"], x["body"]) for x in ab('gh pr create --repo a/b --body "um\nFixes #12"')] == [("a/b", "um\nFixes #12")])
check("script entregue a um shell por heredoc é lido", [x["repo"] for x in ab("bash <<'EOF'\ngh pr create --repo a/b\nEOF")] == ["a/b"])
check("$(…) dentro de aspas simples não é executado, logo não conta", ab("echo 'use $(gh pr create -R a/b) depois'") in ([], None))
check("gh api com -X GET e filtro não é abertura", ab("gh api repos/a/b/pulls -X GET -f state=closed") == [])
check("gh api comentando num PR existente não é abertura", ab("gh api repos/a/b/pulls/12/comments -f body='ok'") == [])
check("gh api editando um PR existente não é abertura", ab("gh api repos/a/b/pulls/12 -X PATCH -f title=t") == [])
check("curl POST para outro site com /pulls no caminho não vira dúvida", ab("curl -X POST https://x.dev/api/pulls") == [])
check("corpo de heredoc que cita o comando NÃO é comando", ab("cat > b.md <<'EOF'\nrode gh pr create --repo a/b\nEOF") == [])
check("heredoc com apóstrofo e menção não vira dúvida", ab("cat > b.md <<EOF\nit's how you run gh pr create\nEOF") == [])
check("comando comum com 'pulls' no meio não vira dúvida", ab("grep -rn pulls src/ && npm run prebuild") == [])
check("aspas abertas num comando que parece abrir PR: não dá para ler (None)", ab("gh pr create --title 'x") is None)
check("aspas abertas num comando comum: nada", ab("echo 'x") == [])

print("veredito")
check("dossiê completo libera", pe.liberado(pe.avalia(dossie_verde(), "abc")))
check("dossiê vazio bloqueia", not pe.liberado(pe.avalia({"repo": "a/b", "branch": "x"})))
check("dossiê com zero achados, zero regras e zero verificações NÃO libera",
      not pe.liberado(com(lambda d: (d["duplicatas"].update(achados=[]), d["regras"].update(arquivos=[], jobs={}), d.update(ci={})))))
check("natureza não declarada bloqueia", estado(com(lambda d: d.pop("natureza")), "natureza") == "bloqueio")
check("falha de segurança nunca vai por PR público", estado(com(lambda d: d["natureza"].update(seguranca="sim")), "natureza") == "bloqueio")
check("funcionalidade nova sem aval bloqueia", estado(com(lambda d: d["natureza"].update(tipo="funcionalidade")), "natureza") == "bloqueio")
check("funcionalidade nova com aval passa", estado(com(lambda d: d["natureza"].update(tipo="funcionalidade", aval="https://x/1")), "natureza") == "ok")
check("código de terceiro sem licença declarada bloqueia", estado(com(lambda d: d["natureza"].update(origem="terceiro")), "natureza") == "bloqueio")
check("projeto com CLA e sem assinatura bloqueia", estado(com(lambda d: d["regras"].update(exige_cla=True)), "natureza") == "bloqueio")
check("repositório sem licença vira aviso", estado(com(lambda d: d["regras"].update(licenca=None)), "natureza") == "aviso")
check("menos de três termos de busca bloqueia", estado(com(lambda d: d["duplicatas"].update(termos=["a"])), "duplicatas") == "bloqueio")
check("busca sem nenhum resultado bloqueia", estado(com(lambda d: d["duplicatas"].update(achados=[])), "duplicatas") == "bloqueio")
check("resultado sem classificar bloqueia", estado(com(lambda d: d["duplicatas"]["achados"][0].update(veredito=None)), "duplicatas") == "bloqueio")
check("já existe quem resolve: bloqueia", estado(com(lambda d: d["duplicatas"]["achados"][0].update(veredito="resolve")), "duplicatas") == "bloqueio")
check("regra achada e não anotada bloqueia", estado(com(lambda d: d["regras"]["arquivos"][0].pop("anotacao")), "regras") == "bloqueio")
check("política de IA não declarada bloqueia", estado(com(lambda d: d["regras"].update(politica_ia=None)), "regras") == "bloqueio")
check("repositório que proíbe IA bloqueia", estado(com(lambda d: d["regras"].update(politica_ia="proibe")), "regras") == "bloqueio")
check("verificação não rodada bloqueia", estado(com(lambda d: d["ci"].pop("ci/test")), "ci") == "bloqueio")
check("verificação rodada em commit antigo bloqueia", estado(com(lambda d: d["ci"]["ci/lint"].update(head="velho")), "ci") == "bloqueio")
check("falha só na branch bloqueia", estado(com(lambda d: d["ci"]["ci/lint"].update(branch=101)), "ci") == "bloqueio")
check("falha sem comparar com o original bloqueia", estado(com(lambda d: d["ci"]["ci/lint"].update(branch=101, base=None)), "ci") == "bloqueio")
check("original que nem chegou a rodar (127) não vira 'já falhava'", estado(com(lambda d: d["ci"]["ci/lint"].update(branch=101, base=127)), "ci") == "bloqueio")
check("tempo estourado nos dois lados (124) bloqueia", estado(com(lambda d: d["ci"]["ci/lint"].update(branch=124, base=124)), "ci") == "bloqueio")
res = com(lambda d: d["ci"]["ci/lint"].update(branch=101, base=101))
check("falha que já existia no original vira aviso", estado(res, "ci") == "aviso")
check("aviso não impede a liberação", pe.liberado(res))
check("uma dispensa com motivo vira aviso", estado(com(lambda d: d["ci"].update({"ci/test": {"dispensa": "só Windows", "branch": None, "base": None}})), "ci") == "aviso")
check("dispensar TODAS as verificações bloqueia", estado(com(lambda d: d.update(ci={j: {"dispensa": "x", "branch": None, "base": None} for j in d["regras"]["jobs"]})), "ci") == "bloqueio")
check("sem precedente bloqueia", estado(com(lambda d: d["coerencia"].update(precedente=None)), "coerencia") == "bloqueio")
check("diff mudou depois do exame bloqueia", estado(pe.avalia(dossie_verde(), "outro"), "coerencia") == "bloqueio")
check("descrição reprovada bloqueia", not pe.liberado(com(lambda d: d["corpo"].update(bloqueios=["x"]))))

print("exame do diff num repositório de mentira")
tmp = os.path.realpath(tempfile.mkdtemp(prefix="pr-externo-test-"))
os.environ["PR_EXTERNO_DIR"] = os.path.join(tmp, "dossies")
R = os.path.join(tmp, "r")
PESSOAL = "fulano@" + "empresa.com.br"


def g(*args, email="1+eu@users.noreply.github.com"):
    cod, out = pe.roda(["git", "-c", "user.name=t", "-c", "user.email=" + email, "-c", "commit.gpgsign=false"] + list(args), cwd=R)
    assert cod == 0, out
    return out


def escreve(nome, texto):
    with open(os.path.join(R, nome), "w") as f:
        f.write(texto)


os.makedirs(os.path.join(R, "src"))
g("init", "-q", "-b", "main")
escreve("src/a.rs", "fn a() {\n    1\n}\n")
escreve("src/b.rs", "fn b() {\n    2\n}\n")
escreve("src/meu arquivo.rs", "fn c() {}\n")
g("add", "-A")
g("commit", "-q", "-m", "base")
g("checkout", "-q", "-b", "fix/x")
escreve("src/a.rs", "fn a() {\n    3\n}\n")
escreve("src/b.rs", "fn b() {\n        2\n}\n")  # só espaço
escreve("src/meu arquivo.rs", "fn c() { 1 }\n")
os.makedirs(os.path.join(R, ".claude"))
escreve(".claude/notas.md", "resto\n")
g("add", "-A")
g("commit", "-q", "-m", "update a", email=PESSOAL)
pe.grava({"repo": "dono/projeto", "branch": "fix/x", "base": "main", "dir": R,
          "regras": {"arquivos": [], "jobs": {"ci/lint": {"opcoes": ["--all-features"], "trecho": "args: --all-features"}},
                     "convencao_titulo": "conventional", "convencao_escrita": True, "exige_dco": True,
                     "modelo_pr": ["## Motivation", "## Testing"], "tamanho_mediano": 40}})
ID = ["--repo", "dono/projeto", "--branch", "fix/x"]


def chama(*argv):
    velho, sys.stdout = sys.stdout, io.StringIO()
    try:
        try:
            cod = pe.main(list(argv))
        except SystemExit as e:
            cod = e.code
    finally:
        saida, sys.stdout = sys.stdout.getvalue(), velho
    return cod, saida


chama("coerencia", *ID, "--ref-base", "main")
coe = pe.le("dono/projeto", "fix/x")["coerencia"]
bl = " | ".join(coe["bloqueios"])
check("lista os arquivos tocados, inclusive nome com espaço", "src/meu arquivo.rs" in coe["arquivos"] and "src/a.rs" in coe["arquivos"])
check("acusa o arquivo mudado só em espaço", "src/b.rs" in bl.split("formatação: ")[1].split(" | ")[0])
check("arquivo com espaço no nome e mudança real NÃO é acusado de formatação", "meu arquivo" not in bl.split("formatação: ")[1].split(" | ")[0])
check("acusa pasta de ferramenta de IA no diff", ".claude/notas.md" in bl)
check("acusa e-mail pessoal no autor do commit", "e-mail pessoal" in bl)
check("acusa falta de Signed-off-by quando o projeto exige", "Signed-off-by" in bl)
check("acusa título fora da convenção escrita", "convenção escrita" in bl)
check("avisa que não há teste tocado", any("teste" in v for v in coe["avisos"]))
chama("coerencia", *ID, "--ref-base", "main", "--email-publico-ok")
check("com o de acordo do usuário, o e-mail deixa de bloquear", "e-mail pessoal" not in " ".join(pe.le("dono/projeto", "fix/x")["coerencia"]["bloqueios"]))

print("verificação automática")
cod, saida = chama("ci", "ci/lint", *ID, "--cmd", "true")
check("comando sem a opção que o workflow usa é recusado", cod not in (0, None) and "--all-features" in str(cod))
check("e nada é gravado", "ci" not in pe.le("dono/projeto", "fix/x"))
chama("ci", "ci/lint", *ID, "--cmd", "true --all-features", "--dir-base", R)
item = pe.le("dono/projeto", "fix/x")["ci"]["ci/lint"]
check("com a opção, roda na branch e no original e grava o commit", (item["branch"], item["base"]) == (0, 0) and item["head"] == pe.head_de({"dir": R, "branch": "fix/x"}))
check("comando que estoura o teto devolve 124", pe.roda("sleep 5", shell=True, teto=1)[0] == 124)
check("comando ausente devolve 127", pe.roda(["comando-que-nao-existe-xyz"])[0] == 127)

print("descrição do PR")
corpo = os.path.join(tmp, "corpo.md")
with open(corpo, "w") as f:
    f.write("Arruma o bug.\n\nTestado em /Users/" + "fulano/x\n")
chama("corpo", corpo, *ID)
b = " | ".join(pe.le("dono/projeto", "fix/x")["corpo"]["bloqueios"])
check("sem Fixes #N bloqueia", "issue" in b)
check("caminho de máquina na descrição bloqueia", "dado seu" in b)
check("título do modelo de PR ausente bloqueia", "Motivation" in b)
check("descrição curta demais bloqueia", "curta" in b)
BOM = ("Fixes #7.\n\n## Motivation\nPicking a track inside a playlist played the first one instead of the chosen one.\n\n"
       "## Testing\nBefore: loads track 1. After: loads the picked track. Ran the three CI jobs locally on both sides.\n")
with open(corpo, "w") as f:
    f.write(BOM)
chama("corpo", corpo, *ID, "--titulo", "fix: pick the right track")
c = pe.le("dono/projeto", "fix/x")["corpo"]
check("descrição completa passa e o arquivo fica amarrado por hash", c["bloqueios"] == [] and c["sha256"] == pe.sha_do_arquivo(corpo))

print("qual dossiê recebe o comando")
aqui = os.getcwd()
os.chdir(R)
check("sem --repo/--branch, vale o dossiê do clone e da branch atuais", chama("classificar", "resolve", "1", "--motivo", "x")[0] != 0 and
      pe.dossie_atual(type("A", (), {"repo": None, "branch": None})())["repo"] == "dono/projeto")
os.chdir(tmp)
cod, _ = chama("veredito")
check("fora de um clone com dossiê, o comando recusa em vez de pegar outro dossiê", cod not in (0, 1))
os.chdir(aqui)

print("trava: abertura de PR")
gh_json_real, gh_real = pe.gh_json, pe.gh
PERM = ("ok", {"push": False})
VISTO = {}


def gh_json_falso(args, cwd=None):
    if args[:2] == ["repo", "view"]:
        VISTO["cwd"] = cwd
        return "ok", {"nameWithOwner": "eu/projeto", "parent": {"owner": {"login": "dono"}, "name": "projeto"}}
    if args[:1] == ["api"] and args[-2:] == ["-q", ".permissions"]:
        return PERM
    return "erro", None


pe.gh_json = gh_json_falso


def hook(comando):
    velho_in, velho_err = sys.stdin, sys.stderr
    sys.stdin, sys.stderr = io.StringIO(json.dumps({"tool_input": {"command": comando}, "cwd": R})), io.StringIO()
    try:
        return pe.cmd_hook(None), sys.stderr.getvalue()
    finally:
        sys.stdin, sys.stderr = velho_in, velho_err


CRIAR = "gh pr create --repo dono/projeto --head eu:fix/x --title t --body-file " + corpo
check("comando que não abre PR passa calado", hook("git status") == (pe.SEGUE, ""))
check("menção em texto passa calada", hook("echo 'rode gh pr create'") == (pe.SEGUE, ""))
cod, msg = hook(CRIAR)
check("dossiê com portão fechado barra", cod == pe.BARRA)
check("a mensagem nomeia o repositório e os portões fechados", "dono/projeto" in msg and "coerencia" in msg)
check("branch sem dossiê barra", hook("gh pr create --repo dono/projeto --head eu:outra")[0] == pe.BARRA)

# deixa o dossiê verde de verdade, para este commit
d = pe.le("dono/projeto", "fix/x")
h = pe.head_de(d)
d.update(natureza={"tipo": "correcao", "seguranca": "nao", "origem": "proprio"},
         duplicatas={"termos": ["a", "b", "c"], "achados": [{"tipo": "issue", "numero": 7, "veredito": "nao-relacionado"}]})
d["regras"].update(politica_ia="ausente", licenca="MIT", exige_dco=False)
d["coerencia"].update(bloqueios=[], precedente={"numero": 10, "titulo": "t", "arquivos": ["src/a.rs"]}, head=h)
pe.grava(d)
cod, msg = hook(CRIAR)
check("dossiê liberado: a trava pede a confirmação do usuário (ele lê o diff antes)", cod == pe.PERGUNTA and "LIBERADO" in msg)
os.environ["PR_EXTERNO_CONFIRMA"] = "0"
check("com a confirmação desligada pelo usuário, segue", hook(CRIAR)[0] == pe.SEGUE)
check("sem --body-file barra (a descrição não foi a conferida)", hook("gh pr create --repo dono/projeto --head eu:fix/x --fill")[0] == pe.BARRA)
check("--body escrito na linha barra", hook("gh pr create --repo dono/projeto --head eu:fix/x --body 'oi'")[0] == pe.BARRA)
outro = os.path.join(tmp, "outro.md")
with open(outro, "w") as f:
    f.write(BOM + "linha a mais\n")
check("--body-file de OUTRO arquivo barra", hook(CRIAR.replace(corpo, outro))[0] == pe.BARRA)
check("gh api criando o PR barra (não dá para conferir a descrição)", hook("gh api repos/dono/projeto/pulls -f title=t -f head=eu:fix/x -f base=main")[0] == pe.BARRA)
check("título com dado pessoal barra", hook(CRIAR.replace("--title t", "--title /Users/" + "fulano/x"))[0] == pe.BARRA)
VISTO.clear()
check("sem --repo: descobre o alvo pelo fork e libera igual", hook("gh pr create --head eu:fix/x --body-file " + corpo)[0] == pe.SEGUE)
check("…e pergunta ao gh na pasta do COMANDO, não na do hook", VISTO.get("cwd") == R)
hook("cd sub && gh pr create --head eu:fix/x --body-file " + corpo)
check("cd antes do comando muda a pasta da pergunta", VISTO.get("cwd") == os.path.join(R, "sub"))

d = pe.le("dono/projeto", "fix/x")
d["duplicatas"]["achados"].append({"tipo": "pr", "numero": 99, "veredito": None})
pe.grava(d)
check("dossiê piorou depois do veredito: a trava reavalia e barra", hook(CRIAR)[0] == pe.BARRA)
d["duplicatas"]["achados"].pop()
pe.grava(d)
escreve("src/a.rs", "fn a() {\n    4\n}\n")
g("commit", "-q", "-am", "fix: outro")
check("commit novo depois do exame: barra", hook(CRIAR)[0] == pe.BARRA)

g("checkout", "-q", "--detach", "HEAD~1")
check("pasta parada num commit que não é o da branch: as provas não valem, barra", hook(CRIAR)[0] == pe.BARRA)
check("…e os comandos de prova recusam rodar fora da branch", chama("veredito", *ID)[0] not in (0, 1))
g("checkout", "-q", "fix/x")
d = pe.le("dono/projeto", "fix/x")
d["dir"] = os.path.join(tmp, "sumiu")
pe.grava(d)
check("pasta do dossiê sumiu: barra, não libera com prova velha", hook(CRIAR)[0] == pe.BARRA)
d["dir"] = R
pe.grava(d)

PERM = ("ok", {"push": True})
check("repositório em que o usuário tem escrita não é PR externo", hook(CRIAR) == (pe.SEGUE, ""))
PERM = ("erro", None)
check("GitHub sem resposta: pergunta ao usuário, NÃO libera", hook(CRIAR)[0] == pe.PERGUNTA)
PERM = ("ok", {"push": False})
check("alvo ilegível (variável): pergunta ao usuário", hook("gh pr create --repo $UP")[0] == pe.PERGUNTA)
check("comando ilegível que parece abrir PR: pergunta ao usuário", hook("gh pr create --title 'x")[0] == pe.PERGUNTA)
os.environ["PR_EXTERNO_GATE"] = "0"
check("PR_EXTERNO_GATE=0 no ambiente desliga a trava", hook(CRIAR)[0] == pe.SEGUE)
del os.environ["PR_EXTERNO_GATE"]
del os.environ["PR_EXTERNO_CONFIRMA"]

pe.gh_json, pe.gh = gh_json_real, gh_real
shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILS:
    print("%d FALHA(S):" % len(FAILS))
    for f in FAILS:
        print("  - " + f)
    sys.exit(1)
print("tudo ok")
