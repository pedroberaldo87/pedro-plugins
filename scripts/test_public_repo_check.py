#!/usr/bin/env python3
"""Checagem do public_repo_check.py — o gate que impede dado pessoal de subir.

Nenhum termo real aparece neste arquivo. Ele é versionado e público: escrever aqui
a lista de nomes que o gate procura seria o vazamento que o gate existe pra impedir.
Os termos de teste são fictícios, gravados num arquivo temporário e carregados dele.

As strings que casam as regras ESTRUTURAIS são montadas por concatenação — o gate lê
linha a linha, então "fulano@" + "g" + "mail.com" não dispara ao varrer este próprio arquivo.
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import public_repo_check as G  # noqa: E402

ok = 0

TERMOS_FICTICIOS = """
# nome-proprio
Fulano!-plugins
Sobrenome

# cliente-ou-sistema-interno
cliente-alfa
SISTEMA-BETA
tabela_gama

# hostname-de-maquina
maquina-de-casa
"""


def check(nome, cond):
    global ok
    assert cond, "FALHOU: %s" % nome
    ok += 1


def casa(regras, rid, texto):
    for r, padrao, _, _ in regras:
        if r == rid:
            return bool(re.search(padrao, texto))
    raise AssertionError("regra inexistente: %s" % rid)


# ─── termos: carregados de arquivo, nunca do código ──────────────────────────
with tempfile.NamedTemporaryFile("w", suffix=".terms", delete=False,
                                 encoding="utf-8") as fh:
    fh.write(TERMOS_FICTICIOS)
    tmp_terms = fh.name

_orig = G.TERMS_FILE
G.TERMS_FILE = tmp_terms
regras_termo, tem = G.carrega_termos()
G.TERMS_FILE = _orig
regras = regras_termo + G.REGRAS_ESTRUTURAIS

check("arquivo de termos presente vira True", tem)
check("as 3 secoes viraram regra", {r[0] for r in regras_termo} == {
    "nome-proprio", "cliente-ou-sistema-interno", "hostname-de-maquina"})
check("nenhuma regra de termo no codigo versionado", G.REGRAS_ESTRUTURAIS and all(
    r[0] not in ("nome-proprio", "cliente-ou-sistema-interno", "hostname-de-maquina")
    for r in G.REGRAS_ESTRUTURAIS))

# ausente → nenhuma regra de termo, e o chamador sabe disso
G.TERMS_FILE = os.path.join(tempfile.gettempdir(), "nao-existe-mesmo.terms")
vazio, tem_nao = G.carrega_termos()
G.TERMS_FILE = _orig
check("sem arquivo, zero regra de termo", vazio == [])
check("sem arquivo, o flag avisa", tem_nao is False)

# ─── nome próprio: pega a pessoa, respeita a exceção ─────────────────────────
check("pega o nome", casa(regras, "nome-proprio", "veja se o Fulano perde informacao"))
check("pega o sobrenome", casa(regras, "nome-proprio", '"name": "Fulano Sobrenome"'))
check("case-insensitive", casa(regras, "nome-proprio", "o FULANO decide"))
check("excecao protege o projeto", not casa(regras, "nome-proprio", "instale o Fulano-plugins"))

# ─── cliente e máquina ───────────────────────────────────────────────────────
check("pega cliente", casa(regras, "cliente-ou-sistema-interno", "a grade do cliente-alfa"))
check("pega sistema", casa(regras, "cliente-ou-sistema-interno", "no SISTEMA-BETA isso quebra"))
check("pega tabela", casa(regras, "cliente-ou-sistema-interno", "a tabela_gama herda"))
check("pega hostname", casa(regras, "hostname-de-maquina", "commit @ maquina-de-casa"))
check("nao pega palavra alheia", not casa(regras, "cliente-ou-sistema-interno", "o cliente ligou"))

# ─── estruturais: valem sem saber nome de ninguém ────────────────────────────
U, H = "/Users/", "/home/"
check("pega conta em /Users", casa(regras, "caminho-de-maquina", 'root: "%sfulano/PROJ"' % U))
check("pega conta em /home", casa(regras, "caminho-de-maquina", "cd %sfulano/app" % H))
check("ignora var de ambiente", not casa(regras, "caminho-de-maquina", '"$TMP%s.claude/g"' % H))
check("ignora interpolacao", not casa(regras, "caminho-de-maquina", "${VAR}%sshare/x" % U))
check("ignora placeholder", not casa(regras, "caminho-de-maquina", "salvo em %s<usuario>/x" % U))

check("pega provedor pessoal", casa(regras, "email-pessoal", "owner: fulano@" + "g" + "mail.com"))
check("ignora dominio proprio", not casa(regras, "email-pessoal", "owner: tools" + "@empresa.com.br"))

check("pega token de host git", casa(regras, "credencial", "T=gh" + "p_" + "a" * 36))
check("pega chave privada", casa(regras, "credencial", "-----BEGIN RSA PRIVATE" + " KEY-----"))
check("pega senha em url", casa(regras, "credencial", "postgres://u:senha" + "@host/db"))
check("ignora o exemplo publicado pela AWS", not casa(regras, "credencial", "AKIA" + "IOSFODNN7EXAMPLE"))

# ─── isenção só vale com motivo escrito ──────────────────────────────────────
check("isencao com motivo isenta", G.ISENCAO.search("x = 1  # public" + "-ok: fixture"))
check("isencao em markdown isenta", G.ISENCAO.search("txt <!-- public" + "-ok: registro -->"))
check("isencao sem motivo NAO isenta", not G.ISENCAO.search("x = 1  # public" + "-ok:"))

# ─── o gate roda de verdade no repo ──────────────────────────────────────────
achados = G.varre()
check("varre() devolve lista", isinstance(achados, list))
if achados:
    check("achado tem os campos que o conserto exige",
          all(k in achados[0] for k in ("file", "line", "rule", "fix")))
    check("achado NAO carrega o trecho nem o casado (nada de segredo ecoado)",
          "excerpt" not in achados[0] and "match" not in achados[0])

# ─── o gate de ponta a ponta, num repositório descartável ────────────────────
# A cópia do script vai para <repo>/scripts/ — a raiz do gate é a pasta do script, então
# ele varre ESTE repositório de mentira e não o verdadeiro. Todo conteúdo que casa uma
# regra é montado por concatenação (o gate lê linha a linha).
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public_repo_check.py")
POSIX = os.name != "nt"


def _rm(func, path, _exc):  # git deixa objeto somente-leitura (Windows)
    os.chmod(path, stat.S_IWRITE)
    func(path)


def repo_de_mentira(com_git=True, termos=None):
    raiz = tempfile.mkdtemp(prefix="prc-")
    os.makedirs(os.path.join(raiz, "scripts"))
    shutil.copy(SCRIPT, os.path.join(raiz, "scripts", "public_repo_check.py"))
    if termos is not None:
        with open(os.path.join(raiz, "scripts", "public_repo_terms"), "w",
                  encoding="utf-8") as fh:
            fh.write(termos)
    if com_git:
        roda_git(raiz, "init", "-q")
        roda_git(raiz, "config", "core.quotePath", "true")  # o default, dito em voz alta
    return raiz


def env_limpo(**extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull)
    env.pop("CI", None)
    env.update(extra)
    return env


def roda_git(raiz, *args):
    subprocess.run(["git", "-C", raiz] + list(args), check=True, capture_output=True,
                   env=env_limpo(), stdin=subprocess.DEVNULL)


def escreve(raiz, nome, texto):
    with open(os.path.join(raiz, nome), "w", encoding="utf-8") as fh:
        fh.write(texto)


def gate(raiz, *args, **env):
    r = subprocess.run([sys.executable, os.path.join(raiz, "scripts", "public_repo_check.py")]
                       + list(args), cwd=raiz, capture_output=True, stdin=subprocess.DEVNULL,
                       env=env_limpo(**env), timeout=120)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


CAMINHO_RUIM = "cd %sfulano/app\n" % H  # casa "caminho-de-maquina"
TOKEN = "gh" + "p_" + "a" * 36
TERMO = "zzfulanozz"
TERMOS_MIN = "# nome-proprio\n%s\n" % TERMO

# (1) caminho com caractere não-ASCII: o git cita (relat\303\263rio.md) e o gate pulava.
rep = repo_de_mentira(termos=TERMOS_MIN)
try:
    escreve(rep, "relatório.md", CAMINHO_RUIM)
    roda_git(rep, "add", "relatório.md")
    rc, out, _ = gate(rep)
    check("caminho nao-ASCII: varredura cheia acha o achado", rc == 1 and "caminho-de-maquina" in out)
    rc, out, _ = gate(rep, "--staged")
    check("caminho nao-ASCII: --staged acha o achado", rc == 1 and "caminho-de-maquina" in out)
    if POSIX:
        escreve(rep, "com\ttab.md", CAMINHO_RUIM)
        roda_git(rep, "add", "com\ttab.md")
        rc, out, _ = gate(rep)
        check("caminho com TAB tambem e varrido", out.count("caminho-de-maquina") >= 1
              and "2 ocorr" in out)
finally:
    shutil.rmtree(rep, onerror=_rm)

# (2) arquivo de termos ausente: o gate NAO pode dizer so "OK".
rep = repo_de_mentira()
try:
    escreve(rep, "limpo.md", "nada aqui\n")
    roda_git(rep, "add", "limpo.md")
    rc, out, err = gate(rep, CI="true")
    check("sem termos, em CI: falha (exit != 0)", rc != 0)
    check("sem termos, em CI: diz na saida padrao que os termos NAO rodaram",
          "TERMOS NÃO RODARAM" in out and "OK — nenhum" not in out)
    rc, out, err = gate(rep)
    check("sem termos, local: nao falha", rc == 0)
    check("sem termos, local: aviso ALTO na saida padrao, sem o OK limpo",
          "TERMOS NÃO RODARAM" in out and "OK — nenhum" not in out)
    rc, out, err = gate(rep, "--so-estruturais", CI="true")
    check("--so-estruturais em CI: passa", rc == 0)
    check("--so-estruturais em CI: a saida ainda diz que os termos nao rodaram",
          "TERMOS NÃO RODARAM" in out and "--so-estruturais" in out)
    rc, out, _ = gate(rep, "--json", CI="true")
    dado = json.loads(out)
    check("--json sem termos em CI: ok=false e terms_checked=false",
          rc != 0 and dado["ok"] is False and dado["terms_checked"] is False)
    escreve(rep, "scripts/public_repo_terms", TERMOS_MIN)
    rc, out, _ = gate(rep, CI="true")
    check("com termos, em CI: passa sem aviso", rc == 0 and "NÃO RODARAM" not in out
          and "OK — nenhum" in out)
finally:
    shutil.rmtree(rep, onerror=_rm)

# (3) o gate nunca ecoa o segredo nem o termo: arquivo:linha e nome da regra, só.
rep = repo_de_mentira(termos=TERMOS_MIN)
try:
    escreve(rep, "seg.txt", "T=%s\nfale com %s hoje\n" % (TOKEN, TERMO))
    roda_git(rep, "add", "seg.txt")
    for args in ((), ("--staged",)):
        rc, out, err = gate(rep, *args)
        tudo = out + err
        check("segredo achado: exit 1", rc == 1)
        check("segredo: arquivo:linha e regra aparecem",
              "seg.txt:1" in tudo and "credencial" in tudo and "seg.txt:2" in tudo
              and "nome-proprio" in tudo)
        check("segredo NAO e ecoado", "a" * 10 not in tudo and "T=" not in tudo)
        check("termo NAO e ecoado", TERMO not in tudo and "fale com" not in tudo)
    rc, out, err = gate(rep, "--json")
    check("--json: sem segredo, sem termo, sem texto da linha",
          TOKEN not in out and "a" * 10 not in out and TERMO not in out
          and "fale com" not in out and "excerpt" not in out and '"match"' not in out)
    dado = json.loads(out)
    check("--json: continua dizendo onde", dado["count"] == 2
          and {(f["file"], f["line"], f["rule"]) for f in dado["findings"]}
          == {("seg.txt", 1, "credencial"), ("seg.txt", 2, "nome-proprio")})
finally:
    shutil.rmtree(rep, onerror=_rm)

# (4) git falhando não vira "OK": sem repositório (e sem subir para um repo de fora).
rep = repo_de_mentira(com_git=False, termos=TERMOS_MIN)
try:
    teto = os.path.dirname(rep)  # git nao procura .git acima da pasta do pai
    for args in ((), ("--staged",), ("--json",)):
        rc, out, err = gate(rep, *args, GIT_CEILING_DIRECTORIES=teto)
        check("git falhou %s: exit != 0 e sem OK" % (args,),
              rc != 0 and "OK — nenhum" not in out and '"ok": true' not in out)
        check("git falhou %s: a falha e dita" % (args,), "git" in (out + err).lower())
finally:
    shutil.rmtree(rep, onerror=_rm)

# (5) arquivo que existe mas nao abre: nao pode sumir da conta.
if POSIX and hasattr(os, "geteuid") and os.geteuid() != 0:
    rep = repo_de_mentira(termos=TERMOS_MIN)
    try:
        escreve(rep, "fechado.md", "nada\n")
        roda_git(rep, "add", "fechado.md")
        os.chmod(os.path.join(rep, "fechado.md"), 0)
        rc, out, err = gate(rep)
        check("arquivo ilegivel: exit != 0 e nome na saida",
              rc != 0 and "fechado.md" in out and "OK — nenhum" not in out)
    finally:
        os.chmod(os.path.join(rep, "fechado.md"), stat.S_IRUSR | stat.S_IWUSR)
        shutil.rmtree(rep, onerror=_rm)

# (6) test_sem_jq.sh: o sandbox nasce de mktemp -d (0700) e some num trap — nome previsivel
# em /tmp deixava outra conta plantar bin/<ferramenta> antes do teste montar o PATH.
with open(os.path.join(os.path.dirname(SCRIPT), "test_sem_jq.sh"), encoding="utf-8") as fh:
    sem_jq = fh.read()
atrib = [l for l in sem_jq.splitlines() if re.match(r"\s*SANDBOX=", l)]
check("test_sem_jq.sh atribui SANDBOX uma vez", len(atrib) == 1)
check("SANDBOX vem de mktemp -d", "mktemp -d" in atrib[0])
check("SANDBOX nao carrega o PID ($$) no nome", "$$" not in atrib[0])
check("existe trap de limpeza do SANDBOX",
      re.search(r"^\s*trap\s+.*rm -rf.*SANDBOX.*(EXIT|0)", sem_jq, re.M) is not None)
check("nao ha mais mkdir -p do SANDBOX nu", 'mkdir -p "$SANDBOX" ' not in sem_jq
      and 'mkdir -p "$SANDBOX"\n' not in sem_jq)

os.unlink(tmp_terms)
print("test_public_repo_check: %d asserts ok ✓  (repo: %d ocorrência(s) hoje)"
      % (ok, len(achados)))
