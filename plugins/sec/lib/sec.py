#!/usr/bin/env python3
"""sec.py — o que vem de fora está limpo? Projeto aberto + esta máquina.

Por que existe
--------------
O ataque de cadeia de suprimentos não mexe no seu código: ele entra pelo que você
BAIXA. Alguém toma a conta do autor de um pacote popular, publica uma versão com
código malicioso, e todo `npm install` naquela janela leva o veneno junto. O mesmo
vale para ação de CI apontada por tag (a tag é movida para um commit malicioso),
servidor MCP chamado por `npx` sem versão (roda a última publicada a cada sessão)
e plugin de terceiro com hook (código que roda sozinho).

Este módulo NÃO revisa código. Ele faz o inventário do que vem de fora e confere
cada item contra bases públicas:

    OSV (api.osv.dev)                 falha conhecida + malware (GHSA, PYSEC, MAL-)
    OSV dump de GitHub Actions        a API de consulta não casa ação por versão
                                      (testado: tj-actions 45.0.7 volta vazio), o
                                      dump traz as faixas e a conta é feita aqui
    Aikido Intel (malware-list)       malware recém-detectado, antes de virar GHSA
    Aikido Intel (intel.aikido.dev)   falha corrigida em silêncio, sem CVE nem GHSA —
                                      o OSV não tem (testado: AIKIDO-2024-10001 → 404).
                                      Sem API aberta: lê o JSON embutido na página de
                                      cada pacote (/packages/<npm|pypi>/<nome>)
    nodejs.org/dist/index.json        correção de segurança do Node na mesma linha
    registro npm                      última versão publicada do Claude Code

Os quatro níveis
----------------
    malicioso   pacote envenenado — remover e trocar senhas/tokens da máquina
    falha       falha conhecida com versão corrigida (ou sem correção publicada)
    cadeia      porta aberta: sem versão fixa, sem lockfile, terceiro com hook
    velho       só desatualizado

Fonte fora do ar NUNCA vira verde: a seção sai "NÃO VERIFICADO" e o comando termina
com código 2. Só stdlib. Nada aqui instala, atualiza ou apaga — só mede.
"""

import argparse
import concurrent.futures
import fnmatch
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regua_texto import erros_de_estilo as _erros_de_estilo  # noqa: E402

PERFIL = "pagina"

OSV_API = os.environ.get("SEC_OSV_API", "https://api.osv.dev")
OSV_DUMP = os.environ.get("SEC_OSV_DUMP", "https://osv-vulnerabilities.storage.googleapis.com")
AIKIDO = os.environ.get("SEC_AIKIDO", "https://malware-list.aikido.dev")
AIKIDO_INTEL = os.environ.get("SEC_AIKIDO_INTEL", "https://intel.aikido.dev")
NODE_INDEX = os.environ.get("SEC_NODE_INDEX", "https://nodejs.org/dist/index.json")
NPM_REGISTRY = os.environ.get("SEC_NPM_REGISTRY", "https://registry.npmjs.org")
CACHE_DIR = os.environ.get("SEC_CACHE_DIR", os.path.join(os.path.expanduser("~"), ".claude", "sec-cache"))
CACHE_TTL = 6 * 3600
LOTE_OSV = 1000  # teto documentado do /v1/querybatch

NIVEIS = ("malicioso", "falha", "cadeia", "velho")
PULAR_DIRS = {"node_modules", ".git", ".venv", "venv", "env", "dist", "build", ".next",
              "__pycache__", ".tox", ".mypy_cache", "vendor", "target", ".claude",
              # Exemplo de teste não é instalado: sem isto, rodar o /sec num repositório com
              # suíte de segurança acusa como "malicioso" o pacote envenenado DE PROPÓSITO.
              "fixtures", "__fixtures__", "testdata"}


class SecError(Exception):
    pass


# ── rede e cache ────────────────────────────────────────────────────────────

def _http(url, corpo=None, timeout=60):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(url, data=dados, headers={
        "Content-Type": "application/json", "User-Agent": "pedro-plugins-sec"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _cache(nome, buscar):
    """Bytes de `buscar()`, guardados por CACHE_TTL. Falha de rede sobe — sem cache velho."""
    raiz = os.path.realpath(CACHE_DIR)
    caminho = os.path.realpath(os.path.join(raiz, nome))
    # O nome pode trazer pedaço de resposta de rede (id do OSV): nada resolve para fora da pasta.
    if caminho == raiz or os.path.commonpath([raiz, caminho]) != raiz:
        raise ValueError("nome de cache fora da pasta do cache: %r" % nome)
    try:
        if time.time() - os.path.getmtime(caminho) < CACHE_TTL:
            with open(caminho, "rb") as fh:
                return fh.read()
    except OSError:
        pass
    dados = buscar()
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(dados)
    os.replace(tmp, caminho)
    return dados


class Fontes(object):
    """Status de cada fonte externa. Qualquer erro aqui vira NÃO VERIFICADO no relatório."""

    def __init__(self):
        self.status = {}

    def usar(self, nome, fn):
        try:
            r = fn()
            self.status.setdefault(nome, "ok")
            return r
        except (urllib.error.URLError, OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
            self.status[nome] = "indisponível (%s)" % (getattr(e, "reason", None) or e)
            return None

    def falhas(self):
        return {k: v for k, v in self.status.items() if v != "ok"}


# ── versões ─────────────────────────────────────────────────────────────────

def _vt(v, pad=0):
    # ponytail: comparação simplificada (números + sufixo de pré-lançamento menor que o
    # final). Não implementa PEP 440 nem semver inteiros — basta para dizer se uma
    # versão está antes ou depois de um "fixed". Caso exótico: trocar por `packaging`.
    v = str(v).strip().lstrip("vV").split("+")[0]
    principal, _, pre = v.partition("-")
    nums = []
    for p in principal.split("."):
        m = re.match(r"\d+", p)
        nums.append(int(m.group()) if m else 0)
        if m and m.end() < len(p) and not pre:
            pre = p[m.end():]  # 1.0rc1 (PyPI)
    return nums + [pad] * (6 - len(nums)), pre


def cmp_ver(a, b, pad_a=0):
    na, pa = _vt(a, pad_a)
    nb, pb = _vt(b)
    if na != nb:
        return -1 if na < nb else 1
    if pa == pb:
        return 0
    if not pa:
        return 1
    if not pb:
        return -1
    return -1 if pa < pb else 1


def afeta(aff, atual, pad=0):
    """A versão `atual` cai em alguma faixa do bloco `affected` do OSV?"""
    if atual in aff.get("versions", []):
        return True
    for r in aff.get("ranges", []):
        if r.get("type") not in ("SEMVER", "ECOSYSTEM"):
            continue
        ini = None
        for ev in r.get("events", []):
            if "introduced" in ev:
                ini = ev["introduced"]
            elif ini is not None and ("fixed" in ev or "last_affected" in ev):
                fim = ev.get("fixed") or ev["last_affected"]
                c = cmp_ver(atual, fim, pad)
                if (ini == "0" or cmp_ver(atual, ini, pad) >= 0) and (
                        c < 0 or ("last_affected" in ev and c == 0)):
                    return True
                ini = None
        if ini is not None and (ini == "0" or cmp_ver(atual, ini, pad) >= 0):
            return True
    return False


def versao_corrigida(vuln, eco, nome, atual):
    """A menor versão 'fixed' acima da atual, para este pacote. None = sem correção."""
    cands = []
    for a in vuln.get("affected", []):
        p = a.get("package", {})
        if p.get("ecosystem") != eco or _norm(eco, p.get("name", "")) != _norm(eco, nome):
            continue
        for r in a.get("ranges", []):
            for ev in r.get("events", []):
                f = ev.get("fixed")
                if f and cmp_ver(f, atual) > 0:
                    cands.append(f)
    if not cands:
        return None
    melhor = cands[0]
    for c in cands[1:]:
        if cmp_ver(c, melhor) < 0:
            melhor = c
    return melhor


def _norm(eco, nome):
    if eco == "PyPI":
        return re.sub(r"[-_.]+", "-", nome).lower()
    return nome


# ── leitores do projeto ─────────────────────────────────────────────────────

def ler_package_lock(caminho):
    with open(caminho, encoding="utf-8") as fh:
        d = json.load(fh)
    if not isinstance(d, dict):
        raise SecError("package-lock sem objeto na raiz")
    if "packages" not in d:
        raise SecError("lockfileVersion %s sem a seção packages (npm 6) — não suportado"
                       % d.get("lockfileVersion"))
    if not isinstance(d["packages"], dict):
        raise SecError("package-lock com a seção packages que não é um objeto")
    out = []
    for chave, p in d["packages"].items():
        if not isinstance(p, dict):
            raise SecError("package-lock com entrada de packages que não é um objeto (%s)" % chave)
        if "node_modules/" not in chave or p.get("link") or not p.get("version"):
            continue
        nome = chave.rsplit("node_modules/", 1)[1]
        real = p.get("name")   # alias (`"x": "npm:real@1"`): a chave é o apelido, `name` é o pacote
        out.append(("npm", real if isinstance(real, str) and real else nome, p["version"]))
    return out


def _nome_versao(spec):
    """'@scope/x@1.2.3' -> ('@scope/x', '1.2.3'); o @ do escopo não conta."""
    i = spec.rfind("@")
    if i <= 0:
        return None
    return spec[:i], spec[i + 1:]


def ler_pnpm_lock(caminho):
    with open(caminho, encoding="utf-8") as fh:
        linhas = fh.read().splitlines()
    ver = next((ln.split(":", 1)[1].strip().strip("'\"") for ln in linhas
                if ln.startswith("lockfileVersion:")), "")
    if not ver.startswith("9"):
        raise SecError("pnpm lockfileVersion %s — só a 9.x é lida" % ver)
    out, dentro = [], False
    for ln in linhas:
        if not ln.strip():
            continue
        if not ln.startswith(" "):
            dentro = ln.startswith("packages:")
            continue
        if dentro and ln.startswith("  ") and not ln.startswith("   ") and ln.rstrip().endswith(":"):
            nv = _nome_versao(ln.strip()[:-1].strip("'\"").split("(")[0])
            if nv and re.match(r"\d", nv[1]):
                out.append(("npm",) + nv)
    return out


NOME_NPM = re.compile(r"^(@[A-Za-z0-9~._-]+/)?[A-Za-z0-9~._-]+$")


def ler_yarn_lock(caminho):
    """yarn v1 (`version "1.2.3"`) e berry (`version: 1.2.3` + `resolution: "x@npm:1.2.3"`)."""
    with open(caminho, encoding="utf-8") as fh:
        texto = fh.read()
    out = set()
    for bloco in re.split(r"\n(?=\S)", texto):
        cab, _, corpo = bloco.partition("\n")
        if cab.startswith(("#", "__metadata")) or not cab.rstrip().endswith(":"):
            continue
        mv = re.search(r'^\s+version:?\s+"?([^"\s]+)"?', corpo, re.M)
        if not mv:
            continue
        mr = re.search(r'^\s+resolution:\s+"?([^"\n]+?)"?$', corpo, re.M)
        if mr:  # berry: só o que veio do registro npm
            nv = _nome_versao(mr.group(1).replace("@npm:", "@"))
            if "@npm:" in mr.group(1) and nv:
                out.add(("npm", nv[0], mv.group(1)))
            continue
        primeiro = cab.rstrip()[:-1].split(",")[0].strip().strip('"')
        nv = _nome_versao(primeiro)
        if nv and "@npm:" in nv[0]:   # `apelido@npm:real@^1`: quem foi instalado é o `real`
            real = nv[0].split("@npm:", 1)[1]
            if not NOME_NPM.match(real):
                raise SecError("yarn.lock: alias que o /sec não sabe ler (%s)" % primeiro)
            nv = (real, nv[1])
        if nv:
            out.add(("npm", nv[0], mv.group(1)))
    return sorted(out)


def ler_toml_lock(caminho):
    """uv.lock e poetry.lock: [[package]] name/version. Fonte local/git fica de fora."""
    with open(caminho, "rb") as fh:
        d = tomllib.load(fh)
    out = []
    for p in d.get("package", []):
        src = p.get("source") or {}
        if src and not ("registry" in src or src.get("type") == "legacy"):
            continue
        out.append(("PyPI", p["name"], p["version"]))
    return out


def ler_requirements(caminho):
    fixos, soltos = [], []
    with open(caminho, encoding="utf-8") as fh:
        for bruta in fh:
            ln = bruta.split("#")[0].strip().rstrip("\\").strip()
            if not ln or ln.startswith(("-", "git+", "http")) or "://" in ln:
                continue
            ln = ln.split(";")[0].strip()
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*==\s*([^\s,]+)$", ln)
            if m:
                fixos.append(("PyPI", m.group(1), m.group(3)))
            elif re.match(r"^[A-Za-z0-9]", ln):
                soltos.append(re.split(r"[\[<>=!~ ]", ln)[0])
    return fixos, soltos


USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^'\"\s#]+)", re.M)


def ler_workflow(caminho):
    """Ações `dono/repo[/caminho]@ref`. Ação local (./) e docker:// ficam de fora."""
    with open(caminho, encoding="utf-8") as fh:
        texto = fh.read()
    out = []
    for u in USES.findall(texto):
        if u.startswith(("./", "docker://")) or "@" not in u:
            continue
        alvo, ref = u.rsplit("@", 1)
        partes = alvo.split("/")
        if len(partes) >= 2:
            out.append(("/".join(partes[:2]), ref))
    return out


RUNNERS = {"npx": "npm", "bunx": "npm", "uvx": "PyPI", "pipx": "PyPI"}


def ler_mcp(servidores):
    """Servidor MCP chamado por runner de pacote: (nome, eco, pacote, versão|None)."""
    out = []
    if servidores is None:
        return out
    if not isinstance(servidores, dict):
        raise SecError("mcpServers não é um objeto")
    for nome, s in servidores.items():
        if not isinstance(s, dict):
            raise SecError("servidor MCP %r não é um objeto" % nome)
        if not isinstance(s.get("args", []), list):
            raise SecError("servidor MCP %r com args que não é uma lista" % nome)
        cmd = os.path.basename(str(s.get("command", "")))
        eco = RUNNERS.get(cmd)
        args = [a for a in s.get("args", []) if isinstance(a, str)]
        if cmd in ("pnpm", "yarn") and args[:1] == ["dlx"]:
            eco, args = "npm", args[1:]
        if not eco:
            continue
        if cmd == "pipx" and args[:1] == ["run"]:
            args = args[1:]
        spec = next((a for a in args if not a.startswith("-")), None)
        if not spec:
            continue
        if eco == "PyPI":
            pac, _, ver = spec.partition("==")
        else:
            nv = _nome_versao(spec)
            pac, ver = nv if nv else (spec, "")
        out.append((nome, eco, pac, ver or None))
    return out


def inventario_projeto(raiz):
    """Tudo que o projeto puxa de fora. Devolve (pacotes, acoes, avisos)."""
    pacotes, acoes, avisos = [], [], []
    lockfiles = {"package-lock.json": ler_package_lock, "npm-shrinkwrap.json": ler_package_lock,
                 "pnpm-lock.yaml": ler_pnpm_lock, "yarn.lock": ler_yarn_lock,
                 "uv.lock": ler_toml_lock, "poetry.lock": ler_toml_lock}
    for d, subdirs, arqs in os.walk(raiz):
        subdirs[:] = [s for s in subdirs if s not in PULAR_DIRS and not s.startswith(".")
                      or s == ".github"]
        rel = os.path.relpath(d, raiz)
        for a in arqs:
            caminho = os.path.join(d, a)
            # "onde" é texto do relatório e entra na chave dos itens: sempre com "/",
            # como o resto da saída. `normpath` no Windows devolveria `pnpm\pnpm-lock.yaml`.
            onde = os.path.normpath(os.path.join(rel, a)).replace(os.sep, "/")
            try:
                if a in lockfiles:
                    pacotes += [(e, n, v, onde) for e, n, v in lockfiles[a](caminho)]
                elif fnmatch.fnmatch(a, "requirements*.txt"):
                    fixos, soltos = ler_requirements(caminho)
                    pacotes += [(e, n, v, onde) for e, n, v in fixos]
                    if soltos:
                        avisos.append(item("projeto", "cadeia", onde,
                                           "%d pacote(s) sem versão fixa: cada instalação pega o que estiver publicado no dia." % len(soltos),
                                           onde=onde, conserto="fixar com == (pip-compile ou uv pip compile)",
                                           citacao=", ".join(soltos[:12])))
                elif rel.replace(os.sep, "/").endswith(".github/workflows") and a.endswith((".yml", ".yaml")):
                    acoes += [(n, r, onde) for n, r in ler_workflow(caminho)]
            except (SecError, ValueError, KeyError, AttributeError, TypeError, RecursionError,
                    UnicodeDecodeError, tomllib.TOMLDecodeError) as e:
                avisos.append(item("projeto", "cadeia", onde,
                                   "Arquivo de pacotes que o /sec não sabe ler: NÃO VERIFICADO.",
                                   onde=onde, citacao=str(e), nao_verificado=True))
    if os.path.exists(os.path.join(raiz, "package.json")) and not any(
            os.path.exists(os.path.join(raiz, f)) for f in
            ("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "bun.lock")):
        avisos.append(item("projeto", "cadeia", "package.json",
                           "Projeto sem lockfile: cada instalação pode trazer versão nova, inclusive uma envenenada.",
                           onde="package.json", conserto="rodar a instalação e versionar o lockfile gerado"))
    mcp = os.path.join(raiz, ".mcp.json")
    if os.path.exists(mcp):
        try:
            with open(mcp, encoding="utf-8") as fh:
                d = json.load(fh)
            if not isinstance(d, dict):
                raise SecError(".mcp.json sem objeto na raiz")
            lidos = ler_mcp(d.get("mcpServers", {}))
        except (SecError, ValueError, OSError, RecursionError) as e:
            lidos = []
            avisos.append(item("projeto", "cadeia", ".mcp.json",
                               "Arquivo de pacotes que o /sec não sabe ler: NÃO VERIFICADO.",
                               onde=".mcp.json", citacao=str(e), nao_verificado=True))
        return pacotes, acoes, avisos, [(n, e, p, v, ".mcp.json") for n, e, p, v in lidos]
    return pacotes, acoes, avisos, []


# ── achados ─────────────────────────────────────────────────────────────────

def item(frente, nivel, alvo, motivo, onde="", conserto="", citacao="", ids=(), nao_verificado=False):
    return {"frente": frente, "nivel": nivel, "alvo": alvo, "motivo": motivo, "onde": onde,
            "conserto": conserto, "citacao": citacao, "ids": list(ids),
            "nao_verificado": nao_verificado, "chave": "%s|%s|%s" % (frente, alvo, onde)}


def _aikido(fontes, eco):
    arq = {"npm": "malware_predictions.json", "PyPI": "malware_pypi.json"}[eco]

    def baixar():
        lista = json.loads(_cache("aikido-" + arq, lambda: _http("%s/%s" % (AIKIDO, arq))))
        todas, por_versao = {}, {}
        for x in lista:
            n = _norm(eco, x["package_name"])
            if x["version"] == "*":
                todas[n] = x["reason"]
            else:
                por_versao[(n, x["version"])] = x["reason"]
        return todas, por_versao
    return fontes.usar("Aikido Intel (%s)" % eco, baixar)


# ── Aikido Intel: as falhas que o OSV não tem ───────────────────────────────
#
# A página de cada pacote (`/packages/npm/<nome>`, `/packages/pypi/<nome>`) traz, no
# JSON que o Nuxt embute (`__NUXT_DATA__`), o registro completo de cada falha: faixas
# vulneráveis, versão que corrige e o CVE/GHSA relacionado — vazio nas corrigidas em
# silêncio (11 de 31 numa amostra de 2026-10-26). Uma página por pacote USADO, não as
# 6.626 do site: a carga completa custava ~21 min e ~625 MB por máquina (medido).

AIKIDO_ECO = {"npm": ("npm", "js"), "PyPI": ("pypi", "python")}  # caminho na URL, `language` do registro
AIKIDO_CAMPOS = ("cve", "package_name", "language", "vulnerable_ranges", "patch_versions",
                 "related_cve_id", "severity", "desc_short")


def _desachata(arr):
    """O formato `devalue` do Nuxt: lista plana em que objetos apontam por índice."""
    memo = {}

    def h(i):
        if i in memo:
            return memo[i]
        v = arr[i]
        if isinstance(v, dict):
            r = memo[i] = {}
            for k, x in v.items():
                r[k] = h(x) if isinstance(x, int) else x
            return r
        if isinstance(v, list):
            if v and v[0] in ("Reactive", "ShallowReactive", "Ref", "ShallowRef", "EmptyRef", "EmptyShallowRef"):
                r = h(v[1]) if len(v) > 1 else None
            elif v and v[0] in ("Set", "Map", "Date", "RegExp", "BigInt", "null", "NuxtError"):
                r = None
            else:
                r = [h(x) if isinstance(x, int) else x for x in v]
        else:
            r = v
        memo[i] = r
        return r
    return h(0)


def aikido_registros(html):
    """Os registros AIKIDO-… de uma página. Página sem o JSON embutido = o site mudou → ValueError."""
    m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("página sem __NUXT_DATA__ — o formato do site mudou")
    out, pilha = {}, [_desachata(json.loads(m.group(1)))]
    while pilha:
        o = pilha.pop()
        if isinstance(o, dict):
            if str(o.get("cve", "")).startswith("AIKIDO-") and "vulnerable_ranges" in o:
                out[o["cve"]] = {k: o.get(k) for k in AIKIDO_CAMPOS}
            pilha.extend(o.values())
        elif isinstance(o, list):
            pilha.extend(o)
    return sorted(out.values(), key=lambda r: r["cve"])


def _http_pagina(url):
    req = urllib.request.Request(url, headers={"User-Agent": "pedro-plugins-sec", "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=60) as r:
        corpo = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            corpo = gzip.decompress(corpo)
    return corpo.decode("utf-8")


def _aikido_vulns(fontes, pacotes):
    """{(eco, nome_norm): [registros]} das páginas dos pacotes usados. Página que falha fica
    de fora SÓ ela, e a fonte sai como NÃO VERIFICADO com a contagem — nunca verde."""
    alvos = sorted({(e, _norm(e, n)) for e, n in pacotes if e in AIKIDO_ECO})

    def um(alvo):
        e, n = alvo
        caminho, _ = AIKIDO_ECO[e]
        url = "%s/packages/%s/%s" % (AIKIDO_INTEL, caminho, urllib.parse.quote(n, safe="@/"))
        nome_cache = "aikido-intel/%s/%s.json" % (caminho, urllib.parse.quote(n, safe=""))
        try:
            return alvo, json.loads(_cache(nome_cache, lambda: json.dumps(
                aikido_registros(_http_pagina(url))).encode())), None
        except (urllib.error.URLError, OSError, ValueError) as ex:
            return alvo, [], "%s: %s" % (n, getattr(ex, "reason", None) or ex)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(um, alvos))
    erros = [err for _, _, err in res if err]
    if erros:
        fontes.status["Aikido Intel (vulnerabilidades)"] = "%d de %d pacotes sem resposta (%s)" % (
            len(erros), len(alvos), "; ".join(erros[:3]))
    elif alvos:
        fontes.status.setdefault("Aikido Intel (vulnerabilidades)", "ok")
    return {alvo: regs for alvo, regs, _ in res}


def aikido_afeta(reg, versao):
    """Faixas da Aikido são fechadas nas duas pontas; `*` no teto = sem correção ainda."""
    for faixa in reg.get("vulnerable_ranges") or []:
        if len(faixa) != 2:
            continue
        lo, hi = faixa
        if cmp_ver(versao, lo) >= 0 and (hi == "*" or cmp_ver(versao, hi) <= 0):
            return True
    return False


def aikido_correcao(reg, versao):
    acima = [p for p in reg.get("patch_versions") or [] if cmp_ver(p, versao) > 0]
    return min(acima, key=lambda p: _vt(p)) if acima else None


def _osv_ids(fontes, consultas):
    """{(eco, nome, versão): [ids]} via /v1/querybatch em lotes, seguindo paginação."""
    def rodar():
        achado = {}
        for i in range(0, len(consultas), LOTE_OSV):
            lote = consultas[i:i + LOTE_OSV]
            corpo = {"queries": [{"package": {"name": n, "ecosystem": e}, "version": v} for e, n, v in lote]}
            res = json.loads(_http(OSV_API + "/v1/querybatch", corpo))["results"]
            for (e, n, v), r in zip(lote, res):
                ids = [x["id"] for x in r.get("vulns", [])]
                tok = r.get("next_page_token")
                while tok:
                    q = {"package": {"name": n, "ecosystem": e}, "version": v, "page_token": tok}
                    rr = json.loads(_http(OSV_API + "/v1/query", q))
                    ids += [x["id"] for x in rr.get("vulns", [])]
                    tok = rr.get("next_page_token")
                if ids:
                    achado[(e, n, v)] = ids
        return achado
    return fontes.usar("OSV", rodar)


ID_OSV = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")


def _id_osv_valido(i):
    """GHSA-…, PYSEC-…, MAL-…, CVE-…: letras, dígitos, `.`, `_`, `:` e `-`, sem `..`."""
    return bool(ID_OSV.match(i)) and ".." not in i


def _osv_detalhes(fontes, ids):
    """{id: registro}. Registro que a base apagou (404) fica de fora SÓ ele — o pacote dele sai
    com o id à vista para conferência à mão. Erro de rede continua derrubando o OSV inteiro."""
    def um(i):
        if not _id_osv_valido(i):   # id vem da rede: nunca vira caminho nem URL
            return i, None
        try:
            return i, json.loads(_cache("vulns/%s.json" % i, lambda: _http("%s/v1/vulns/%s" % (OSV_API, i))))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return i, None
            raise

    def rodar():
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            return {i: v for i, v in ex.map(um, sorted(ids)) if v is not None}
    return fontes.usar("OSV", rodar) or {}


def _malicioso(v):
    # Sinal estrutural, nunca a palavra "malicious" no texto: a falha comum fala de
    # "site malicioso" (o atacante) — e o vite 6.4.3 saía como pacote envenenado.
    # MAL- = base de pacotes maliciosos da OpenSSF; CWE-506 = código malicioso embutido
    # (é como o GHSA do event-stream 3.3.6 vem marcado, sem MAL- nenhum).
    return (v["id"].startswith("MAL-") or any(a.startswith("MAL-") for a in v.get("aliases") or [])
            or "CWE-506" in ((v.get("database_specific") or {}).get("cwe_ids") or []))


SEV = {"CRITICAL": 4, "HIGH": 3, "MODERATE": 2, "MEDIUM": 2, "LOW": 1}


def checar_pacotes(fontes, frente, pacotes):
    """pacotes: [(eco, nome, versão, onde)] → itens malicioso/falha (+ cadeia p/ protestware)."""
    onde = {}
    for e, n, v, o in pacotes:
        onde.setdefault((e, n, v), [])
        if o not in onde[(e, n, v)]:
            onde[(e, n, v)].append(o)
    if not onde:
        return []
    itens = []
    vistos = set()
    for eco in sorted({e for e, _, _ in onde}):
        ak = _aikido(fontes, eco)
        if ak is None:
            continue
        todas, por_versao = ak
        for (e, n, v), os_ in onde.items():
            if e != eco:
                continue
            motivo = todas.get(_norm(e, n)) or por_versao.get((_norm(e, n), v))
            if not motivo:
                continue
            vistos.add((e, n, v))
            if motivo == "MALWARE":
                itens.append(item(frente, "malicioso", "%s %s %s" % (e, n, v),
                                  "Marcado como malware pela Aikido Intel.",
                                  onde=", ".join(os_), ids=["aikido:" + motivo],
                                  conserto="remover; trocar senhas e tokens desta máquina"))
            else:
                itens.append(item(frente, "cadeia", "%s %s %s" % (e, n, v),
                                  "Marcado como %s pela Aikido Intel: faz algo além do anunciado." % motivo.lower(),
                                  onde=", ".join(os_), ids=["aikido:" + motivo],
                                  conserto="avaliar troca por alternativa"))
    ids = _osv_ids(fontes, sorted(onde))
    detalhes = _osv_detalhes(fontes, {i for lista in ids.values() for i in lista}) if ids else {}
    ids = ids or {}
    # Aikido: só o que o OSV não trouxe pelo mesmo id (o registro AIKIDO- costuma citar o CVE/GHSA).
    av = _aikido_vulns(fontes, {(e, n) for e, n, _ in onde})
    extras = {}
    for (e, n, v) in onde:
        conhecidos = set(ids.get((e, n, v), []))
        for x in (detalhes.get(i) for i in ids.get((e, n, v), [])):
            conhecidos.update((x or {}).get("aliases") or [])
        novos = [r for r in av.get((e, _norm(e, n)), [])
                 if (r.get("language") or "").lower() == AIKIDO_ECO[e][1] and aikido_afeta(r, v)
                 and r["cve"] not in conhecidos and (r.get("related_cve_id") or "") not in conhecidos]
        if novos:
            extras[(e, n, v)] = novos
    for (e, n, v) in sorted(set(ids) | set(extras)):
        lista = ids.get((e, n, v), [])
        novos = extras.get((e, n, v), [])
        vulns = [detalhes[i] for i in lista if i in detalhes]
        mal = [x for x in vulns if _malicioso(x)]
        alvo = "%s %s %s" % (e, n, v)
        if mal:
            if (e, n, v) in vistos and any(i["alvo"] == alvo and i["nivel"] == "malicioso" for i in itens):
                itens = [i for i in itens if not (i["alvo"] == alvo and i["nivel"] == "malicioso")]
            itens.append(item(frente, "malicioso", alvo, "Versão marcada como maliciosa em base pública.",
                              onde=", ".join(onde[(e, n, v)]), ids=[x["id"] for x in mal],
                              citacao=mal[0].get("summary") or "",
                              conserto="remover; trocar senhas e tokens desta máquina"))
            continue
        fixes = [versao_corrigida(x, e, n, v) for x in vulns] + [aikido_correcao(r, v) for r in novos]
        alvo_fix = None
        if fixes and all(fixes):
            alvo_fix = fixes[0]
            for f in fixes[1:]:
                if cmp_ver(f, alvo_fix) > 0:
                    alvo_fix = f
        sev = max([SEV.get((x.get("database_specific") or {}).get("severity", "").upper(), 0) for x in vulns]
                  + [SEV.get((r.get("severity") or "").upper(), 0) for r in novos], default=0)
        nome_sev = {4: "crítica", 3: "alta", 2: "média", 1: "baixa"}.get(sev, "sem nota")
        faltam = [i for i in lista if i not in detalhes]
        if faltam:
            conserto = "registro sem detalhe no OSV (%s): conferir à mão" % ", ".join(faltam[:3])
        elif alvo_fix:
            conserto = "subir para %s" % alvo_fix
        else:
            conserto = "sem versão corrigida publicada para todas: avaliar troca"
        silenciosas = sum(1 for r in novos if not r.get("related_cve_id"))
        motivo = "%d falha(s) conhecida(s), pior gravidade %s." % (len(lista) + len(novos), nome_sev)
        if silenciosas:
            motivo = "%d falha(s) conhecida(s), %d sem alerta oficial (achada pela Aikido), pior gravidade %s." % (
                len(lista) + len(novos), silenciosas, nome_sev)
        itens.append(item(frente, "falha", alvo, motivo,
                          onde=", ".join(onde[(e, n, v)]), ids=lista + [r["cve"] for r in novos],
                          citacao=" · ".join(([(x.get("summary") or x["id"]) for x in vulns]
                                              + [r.get("desc_short") or r["cve"] for r in novos])[:3]),
                          conserto=conserto))
    return itens


def checar_acoes(fontes, acoes):
    """Ações do CI: tag/branch móvel é porta aberta; versão em faixa do dump do OSV é falha."""
    itens = []
    por_acao = {}
    for n, ref, o in acoes:
        por_acao.setdefault((n, ref), []).append(o)
    sha = re.compile(r"^[0-9a-f]{40}$")
    for (n, ref), os_ in sorted(por_acao.items()):
        if not sha.match(ref):
            itens.append(item("projeto", "cadeia", "ação %s@%s" % (n, ref),
                              "Ação apontada por tag: quem controla o repositório da ação pode trocar o código por trás dela.",
                              onde=", ".join(sorted(set(os_))),
                              conserto="fixar pelo SHA do commit (comentário com a tag ao lado)"))
    if not por_acao:
        return itens
    zipado = fontes.usar("OSV (GitHub Actions)", lambda: _cache(
        "osv-github-actions.zip", lambda: _http(OSV_DUMP + "/GitHub%20Actions/all.zip")))
    if zipado is None:
        return itens
    vulns = []
    with zipfile.ZipFile(io.BytesIO(zipado)) as z:
        for f in z.namelist():
            vulns.append(json.loads(z.read(f)))
    for (n, ref), os_ in sorted(por_acao.items()):
        if sha.match(ref) or not re.match(r"^v?\d", ref):
            continue
        partes = len(ref.lstrip("vV").split("."))
        pad = 10 ** 9 if partes < 3 else 0  # "v45" = a última 45.x.y que existir
        hits = []
        for v in vulns:
            for a in v.get("affected", []):
                if a.get("package", {}).get("name", "").lower() == n.lower() and afeta(a, ref.lstrip("vV"), pad):
                    hits.append(v)
                    break
        if not hits:
            continue
        mal = [h for h in hits if _malicioso(h)]
        fix = [versao_corrigida(h, "GitHub Actions", n, ref.lstrip("vV")) for h in hits]
        fix = [f for f in fix if f]
        conserto = ("subir para %s ou acima, fixando pelo SHA" % max(fix, key=lambda f: _vt(f))
                    if fix else "sem versão corrigida publicada: avaliar troca")
        if mal:
            conserto += "; trocar os segredos que o CI usa"
        itens.append(item("projeto", "malicioso" if mal else "falha", "ação %s@%s" % (n, ref),
                          "Esta versão da ação já rodou código malicioso." if mal else
                          "%d falha(s) conhecida(s) nesta versão da ação." % len(hits),
                          onde=", ".join(sorted(set(os_))), ids=[h["id"] for h in hits],
                          citacao=" · ".join(h.get("summary") or h["id"] for h in hits[:3]),
                          conserto=conserto))
    return itens


def checar_mcp(fontes, frente, servidores):
    """[(nome, eco, pacote, versão|None, onde)] → cadeia (sem versão) + pacotes a conferir."""
    itens, pacotes = [], []
    for nome, eco, pac, ver, onde in servidores:
        if not ver or ver in ("latest", "*"):
            itens.append(item(frente, "cadeia", "MCP %s (%s)" % (nome, pac),
                              "Servidor MCP sem versão fixa: roda a última publicada a cada sessão, com acesso aos seus arquivos.",
                              onde=onde, conserto="fixar a versão no comando (pacote@x.y.z)"))
        else:
            pacotes.append((eco, pac, ver, "%s (MCP %s)" % (onde, nome)))
    return itens, pacotes


# ── máquina ─────────────────────────────────────────────────────────────────

def _rodar(fontes, cmd, timeout=60, cwd=None):
    """stdout do comando; None se ele não existe nesta máquina. Estourar o tempo ou falhar
    ao abrir vira NÃO VERIFICADO daquela parte — nunca derruba a varredura inteira."""
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        r = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, timeout=timeout, cwd=cwd)
    except subprocess.TimeoutExpired:
        fontes.status[" ".join(cmd[:2])] = "não respondeu em %ds" % timeout
        return None
    except OSError as e:
        fontes.status[" ".join(cmd[:2])] = "não abriu (%s)" % e
        return None
    return r.stdout


def _home(*p):
    return os.path.join(os.path.expanduser("~"), *p)


def _json_arquivo(caminho):
    try:
        with open(caminho, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


MARKETPLACE_OFICIAL = "anthropics/claude-plugins-official"


def checar_plugins():
    itens = []
    inst = _json_arquivo(_home(".claude", "plugins", "installed_plugins.json")) or {}
    mkts = _json_arquivo(_home(".claude", "plugins", "known_marketplaces.json")) or {}
    bloq = _json_arquivo(_home(".claude", "plugins", "blocklist.json")) or {}
    bloqueados = {b.get("plugin"): b for b in bloq.get("plugins", [])}
    for chave, entradas in sorted((inst.get("plugins") or {}).items()):
        mkt = chave.split("@", 1)[1] if "@" in chave else ""
        src = (mkts.get(mkt) or {}).get("source") or {}
        if chave in bloqueados and bloqueados[chave].get("reason") == "security":
            itens.append(item("maquina", "malicioso", "plugin %s" % chave,
                              "Plugin na lista de bloqueio de segurança do Claude Code.",
                              onde="~/.claude/plugins/blocklist.json",
                              citacao=bloqueados[chave].get("text", ""),
                              conserto="claude plugin uninstall %s" % chave))
        if src.get("source") == "directory" or src.get("repo") == MARKETPLACE_OFICIAL:
            continue
        for e in entradas:
            base = e.get("installPath") or ""
            # Hook e MCP podem vir em arquivo próprio OU declarados no plugin.json (o ponytail
            # declara os hooks inline — só olhar hooks/hooks.json deixava ele de fora).
            manif = _json_arquivo(os.path.join(base, ".claude-plugin", "plugin.json")) or {}
            roda = [x for x, f, k in (("hooks", os.path.join(base, "hooks", "hooks.json"), "hooks"),
                                      ("servidor MCP", os.path.join(base, ".mcp.json"), "mcpServers"))
                    if os.path.exists(f) or manif.get(k)]
            if roda:
                origem = src.get("repo") or src.get("url") or mkt
                itens.append(item("maquina", "cadeia", "plugin %s" % chave,
                                  "Plugin de terceiro que roda código sozinho (%s); cada atualização dele entra sem revisão." % " e ".join(roda),
                                  onde=origem, conserto="manter só se você confia no autor; senão desinstalar"))
    return itens


def checar_claude_code(fontes):
    saida = _rodar(fontes, ["claude", "--version"])
    if not saida:
        return [], []
    local = saida.split()[0]
    itens = []
    ultima = fontes.usar("registro npm", lambda: json.loads(
        _http(NPM_REGISTRY + "/@anthropic-ai%2Fclaude-code/latest"))["version"])
    if ultima and cmp_ver(local, ultima) < 0:
        itens.append(item("maquina", "velho", "Claude Code %s" % local,
                          "Há versão mais nova publicada: %s." % ultima,
                          onde="claude --version", conserto="claude update"))
    return itens, [("npm", "@anthropic-ai/claude-code", local, "claude --version")]


def checar_node(fontes):
    saida = _rodar(fontes, ["node", "--version"])
    if not saida:
        return []
    local = saida.strip()
    idx = fontes.usar("nodejs.org", lambda: json.loads(_cache("node-index.json", lambda: _http(NODE_INDEX))))
    if not idx:
        return []
    major = local.lstrip("v").split(".")[0]
    seg = [x["version"] for x in idx if x.get("security") and x["version"].lstrip("v").split(".")[0] == major
           and cmp_ver(x["version"], local) > 0]
    if not seg:
        return []
    alvo = max(seg, key=lambda v: _vt(v))
    return [item("maquina", "falha", "Node %s" % local,
                 "Há correção de segurança publicada na mesma linha do Node.",
                 onde="node --version", conserto="atualizar para %s ou acima" % alvo)]


QUARENTENA_MOTIVO = ("Instala versão publicada há minutos; pacote envenenado costuma ser "
                     "derrubado em horas, e esperar um dia fecha essa janela.")


def checar_quarentena_pnpm(fontes, frente, cwd):
    """pnpm ≥10.16 tem `minimumReleaseAge` (minutos); no 11 o padrão virou 1440.
    `pnpm config get` já soma usuário + .npmrc + pnpm-workspace.yaml da pasta (testado)."""
    v = _rodar(fontes, ["pnpm", "--version"], cwd=cwd)
    if not v:
        return []
    v = v.strip()
    val = (_rodar(fontes, ["pnpm", "config", "get", "minimumReleaseAge"], cwd=cwd) or "").strip()
    minutos = int(val) if val.isdigit() else (1440 if cmp_ver(v, "11.0.0") >= 0 else 0)
    if minutos > 0:
        return []
    if cmp_ver(v, "10.16.0") < 0:
        conserto = "atualizar o pnpm (a trava existe a partir do 10.16) e ligar minimumReleaseAge=1440"
    elif frente == "projeto":
        conserto = "minimumReleaseAge: 1440 no pnpm-workspace.yaml"
    elif cmp_ver(v, "11.0.0") >= 0:
        conserto = "tirar o minimumReleaseAge=0 da configuração (o padrão do pnpm 11 já é 1 dia)"
    else:  # testado no 10.33: --global grava minimum-release-age=1440 em ~/.config/pnpm/rc
        conserto = "pnpm config set minimumReleaseAge 1440 --global"
    return [item(frente, "cadeia", "pnpm %s sem quarentena de versão nova" % v, QUARENTENA_MOTIVO,
                 onde="pnpm config get minimumReleaseAge", conserto=conserto)]


def checar_quarentena_npm(fontes):
    """npm ≥11.10 tem `min-release-age` (DIAS). Lido direto do ~/.npmrc: há relato de
    `npm config get` devolver null com o valor no arquivo."""
    v = _rodar(fontes, ["npm", "--version"])
    if not v:
        return []
    v = v.strip()
    if cmp_ver(v, "11.10.0") < 0:
        return [item("maquina", "cadeia", "npm %s sem quarentena de versão nova" % v, QUARENTENA_MOTIVO,
                     onde="npm --version",
                     conserto="npm install -g npm@latest (a trava existe a partir do 11.10); depois min-release-age=1 no ~/.npmrc")]
    try:
        with open(_home(".npmrc"), encoding="utf-8") as fh:
            dias = [ln.split("=", 1)[1].strip() for ln in fh
                    if ln.split("=", 1)[0].strip() == "min-release-age" and "=" in ln]
    except OSError:
        dias = []
    if dias and dias[-1].isdigit() and int(dias[-1]) > 0:
        return []
    return [item("maquina", "cadeia", "npm %s sem quarentena de versão nova" % v, QUARENTENA_MOTIVO,
                 onde="~/.npmrc", conserto="min-release-age=1 no ~/.npmrc")]


def inventario_maquina(fontes):
    pacotes, itens = [], []
    itens += checar_plugins()
    itens += checar_quarentena_pnpm(fontes, "maquina", os.path.expanduser("~"))
    itens += checar_quarentena_npm(fontes)
    cc_itens, cc_pac = checar_claude_code(fontes)
    itens += cc_itens
    pacotes += cc_pac
    itens += checar_node(fontes)
    cfg = _json_arquivo(_home(".claude.json"))
    cfg = cfg if isinstance(cfg, dict) else {}
    blocos = [("~/.claude.json", cfg.get("mcpServers"))]
    projetos = cfg.get("projects")
    for proj, pc in sorted((projetos if isinstance(projetos, dict) else {}).items()):
        blocos.append(("~/.claude.json (projeto %s)" % os.path.basename(proj),
                       pc.get("mcpServers") if isinstance(pc, dict) else None))
    servidores = []
    for onde_cfg, bloco in blocos:
        try:
            servidores += [(n, e, p, v, onde_cfg) for n, e, p, v in ler_mcp(bloco)]
        except SecError as ex:   # arquivo fora do formato: avisa e segue com os outros
            itens.append(item("maquina", "cadeia", onde_cfg,
                              "Arquivo de pacotes que o /sec não sabe ler: NÃO VERIFICADO.",
                              onde=onde_cfg, citacao=str(ex), nao_verificado=True))
    mi, mp = checar_mcp(fontes, "maquina", servidores)
    itens += mi
    pacotes += mp
    try:
        g = _rodar(fontes, ["npm", "ls", "-g", "--depth=0", "--json"])
        for n, d in sorted((json.loads(g).get("dependencies") or {}).items() if g else []):
            if d.get("version"):
                pacotes.append(("npm", n, d["version"], "npm -g"))
    except ValueError:
        fontes.status["npm -g"] = "saída ilegível do npm ls -g"
    try:
        px = _rodar(fontes, ["pipx", "list", "--json"])
        for n, v in sorted((json.loads(px).get("venvs") or {}).items() if px else []):
            m = v["metadata"]["main_package"]
            pacotes.append(("PyPI", m["package"], m["package_version"], "pipx"))
    except (ValueError, KeyError):
        fontes.status["pipx"] = "saída ilegível do pipx list"
    if sys.platform == "darwin":
        try:
            b = _rodar(fontes, ["brew", "outdated", "--json=v2"], timeout=180)
            if b:
                d = json.loads(b)
                nomes = [x["name"] for x in d.get("formulae", []) + d.get("casks", [])]
                if nomes:
                    itens.append(item("maquina", "velho", "Homebrew: %d desatualizado(s)" % len(nomes),
                                      "Programas do Homebrew com versão nova; o Homebrew não traz base de falhas.",
                                      onde="brew outdated", conserto="brew upgrade",
                                      citacao=", ".join(nomes[:20]) + (" …" if len(nomes) > 20 else "")))
        except ValueError:
            fontes.status["brew"] = "saída ilegível do brew outdated"
    itens += checar_pacotes(fontes, "maquina", pacotes)
    return itens, len(pacotes)


# ── varredura ───────────────────────────────────────────────────────────────

def varrer(projeto=None, maquina=True):
    fontes = Fontes()
    itens, contagem = [], {}
    if projeto:
        pacotes, acoes, avisos, mcp = inventario_projeto(projeto)
        mi, mp = checar_mcp(fontes, "projeto", mcp)
        itens += avisos + mi
        itens += checar_pacotes(fontes, "projeto", pacotes + mp)
        itens += checar_acoes(fontes, acoes)
        if os.path.exists(os.path.join(projeto, "pnpm-lock.yaml")):
            itens += checar_quarentena_pnpm(fontes, "projeto", projeto)
        contagem["projeto"] = len({(e, n, v) for e, n, v, _ in pacotes + mp}) + len({(n, r) for n, r, _ in acoes})
    if maquina:
        mi, n = inventario_maquina(fontes)
        itens += mi
        contagem["maquina"] = n
    itens.sort(key=lambda i: (NIVEIS.index(i["nivel"]), i["frente"], i["alvo"]))
    return {"projeto": os.path.abspath(projeto) if projeto else None, "itens": itens,
            "conferidos": contagem, "fontes": fontes.status, "falhas": fontes.falhas()}


# ── relatório ───────────────────────────────────────────────────────────────

def _e(t):
    return (str(t or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))


def _uma_linha(t):
    """Texto de uma linha só. O que vem do repo escaneado (nome de servidor MCP, nome de arquivo)
    chega ao bloco 'Copiar os marcados', que o agente lê linha por linha: uma quebra ali forjaria
    um item que ninguém marcou."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+", " ", str(t or ""))


def erros_de_estilo(v, onde):
    """A régua no perfil DESTE gerador. Fora dela: citação de base pública e nome de pacote."""
    return _erros_de_estilo(v, onde, PERFIL)


ROTULO = {"malicioso": ("🔴", "Malicioso — remover já", "dg"),
          "falha": ("🟠", "Falha conhecida — atualizar", "warn"),
          "cadeia": ("🟡", "Porta aberta — fechar quando puder", "ac"),
          "velho": ("⚪", "Só desatualizado", "mut")}

HTML_CSS = """
:root{--bg:#1A1625;--card:#2A2438;--deep:#221D2E;--tx:#F0EDF5;--dim:#A599B5;
--mut:#7A7089;--ac:#FFD166;--ok:#7FD1AE;--warn:#FFA88C;--dg:#FF6B8A;
--bd:rgba(255,255,255,.08)}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font:16px/1.6 -apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:980px;margin:0 auto;padding:56px 28px 160px}
h1{font-size:34px;font-weight:800;letter-spacing:-.02em;margin-bottom:6px}
.sub{color:var(--dim);font-size:15px;margin-bottom:22px}
.ident{background:var(--deep);border:1px solid var(--bd);border-left:3px solid var(--ok);
border-radius:12px;padding:12px 16px;margin-bottom:22px;font-size:13px;color:var(--dim)}
.ident b{color:var(--tx)}
.nv{background:rgba(255,107,138,.12);border:1px solid var(--dg);border-radius:12px;padding:14px 18px;margin-bottom:22px}
.nv b{color:var(--dg)}
.grp{background:var(--card);border:1px solid var(--bd);border-radius:18px;padding:18px 20px;margin-bottom:16px}
.grp h2{font-size:16px;margin-bottom:12px;display:flex;gap:8px}
.grp.dg{border-left:3px solid var(--dg)}.grp.warn{border-left:3px solid var(--warn)}
.grp.ac{border-left:3px solid var(--ac)}.grp.mut{border-left:3px solid var(--mut)}
.it{display:flex;gap:11px;align-items:flex-start;padding:10px 0;border-top:1px solid var(--bd)}
.it:first-of-type{border-top:none}
.it input{margin-top:4px;width:16px;height:16px;accent-color:var(--ok);cursor:pointer;flex:none}
.it .nm{font-weight:650;font-size:14.5px;font-family:ui-monospace,Menlo,monospace}
.it .fr{font-size:11px;color:var(--mut);margin-left:6px}
.it .wy{color:var(--dim);font-size:13px;line-height:1.5}
.it .fx{color:var(--ok);font-size:13px}
.it .ct{color:var(--mut);font-size:12px;font-family:ui-monospace,Menlo,monospace;margin-top:3px}
.vazio{color:var(--ok)}
.foot{position:sticky;bottom:0;background:linear-gradient(transparent,var(--bg) 26%);
padding:22px 0 8px;margin-top:24px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
button{background:var(--ok);color:#1A1625;border:0;border-radius:11px;padding:11px 20px;
font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}
button.gh{background:transparent;color:var(--tx);border:1px solid var(--bd)}
#cnt{color:var(--dim);font-size:13px}
"""

HTML_JS = """
function marcados(){return [...document.querySelectorAll('.it input:checked')].map(i=>i.dataset.linha)}
function upd(){const n=marcados().length;
 document.getElementById('cnt').textContent = n===0 ? 'nenhum marcado'
   : (n===1 ? '1 item marcado' : n+' itens marcados');}
function copiar(btn){const b=marcados();
 if(!b.length){btn.textContent='nada marcado';setTimeout(()=>btn.textContent='📋 Copiar os marcados',1600);return;}
 const t='<!-- sec-corrigir v1 -->\\n🛡️ **Corrigir estes itens:**\\n'
   + b.map(x=>'- '+x).join('\\n') + '\\n<!-- /sec-corrigir -->';
 navigator.clipboard.writeText(t).then(()=>{const o=btn.textContent;
   btn.textContent='✓ copiado';setTimeout(()=>btn.textContent=o,1600);});}
function todos(v){document.querySelectorAll('.it input').forEach(i=>i.checked=v);upd();}
document.addEventListener('change',e=>{if(e.target.matches('.it input'))upd();});
document.addEventListener('DOMContentLoaded',upd);
"""


def render_html(res, stamp):
    errs = []
    for i in res["itens"]:
        errs.extend(erros_de_estilo(i["motivo"], "item %s: motivo" % i["alvo"]))
    if errs:
        raise SecError("relatório recusado pela régua de estilo:\n  - " + "\n  - ".join(errs))

    def linha(i):
        frente = "projeto" if i["frente"] == "projeto" else "máquina"
        txt = "[%s] %s — %s" % (i["nivel"], i["alvo"], i["conserto"] or i["motivo"])
        if i["onde"]:
            txt += " (em %s)" % i["onde"]
        txt = _uma_linha(txt)
        ids = " · ".join(i["ids"][:6]) + (" …" if len(i["ids"]) > 6 else "")
        cit = " — ".join(x for x in (ids, i["citacao"]) if x)
        marca = " checked" if i["nivel"] in ("malicioso", "falha") and not i["nao_verificado"] else ""
        return ("<div class='it'><input type='checkbox' data-linha='%s'%s>"
                "<div><div class='nm'>%s<span class='fr'>%s%s</span></div>"
                "<div class='wy'>%s</div>%s%s</div></div>"
                % (_e(txt), marca, _e(i["alvo"]), frente, (" · " + _e(i["onde"])) if i["onde"] else "",
                   _e(i["motivo"]),
                   ("<div class='fx'>→ %s</div>" % _e(i["conserto"])) if i["conserto"] else "",
                   ("<div class='ct'>%s</div>" % _e(cit)) if cit else ""))

    partes = []
    if res["falhas"]:
        partes.append("<div class='nv'><b>NÃO VERIFICADO</b> — estas fontes não responderam, então "
                      "o que dependia delas não foi conferido (nada abaixo é verde por omissão):<br>%s</div>"
                      % "<br>".join("%s: %s" % (_e(k), _e(v)) for k, v in sorted(res["falhas"].items())))
    for nv in NIVEIS:
        grupo = [i for i in res["itens"] if i["nivel"] == nv]
        if not grupo:
            continue
        emo, titulo, cls = ROTULO[nv]
        partes.append("<div class='grp %s'><h2><span>%s</span><span>%s (%d)</span></h2>%s</div>"
                      % (cls, emo, titulo, len(grupo), "".join(linha(i) for i in grupo)))
    if not res["itens"]:
        partes.append("<div class='grp'><h2 class='vazio'>✅ Nenhum apontamento nas fontes que responderam</h2></div>")

    conf = " &nbsp;·&nbsp; ".join("<b>%d</b> itens %s conferidos" % (v, "do projeto" if k == "projeto" else "da máquina")
                                  for k, v in sorted(res["conferidos"].items(), reverse=True))
    proj = os.path.basename(res["projeto"]) if res["projeto"] else "—"
    return ("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>/sec · %s</title><style>%s</style></head><body><div class='wrap'>"
            "<div class='ident'><b>Projeto</b> %s &nbsp;·&nbsp; %s &nbsp;·&nbsp; <b>Medido em</b> %s "
            "&nbsp;·&nbsp; <b>Fontes</b> OSV, Aikido Intel, nodejs.org, registro npm</div>"
            "<h1>O que vem de fora está limpo?</h1>"
            "<p class='sub'>Marque o que quer corrigir e copie. Esta página não instala nem remove nada.</p>%s"
            "<div class='foot'><button onclick='copiar(this)'>📋 Copiar os marcados</button>"
            "<button class='gh' onclick='todos(true)'>marcar todos</button>"
            "<button class='gh' onclick='todos(false)'>desmarcar</button>"
            "<span id='cnt'></span></div>"
            "</div><script>%s</script></body></html>"
            % (_e(proj), HTML_CSS, _e(proj), conf, _e(stamp), "".join(partes), HTML_JS))


def resolve_visual_dir(raiz):
    r = subprocess.run(["git", "-C", raiz, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return os.path.join(r.stdout.strip(), ".claude", "visual")
    return os.path.join(os.path.expanduser("~"), "Desktop", "claude-visual")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="Cadeia de suprimentos: projeto + máquina.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nome in ("scan", "report"):
        p = sub.add_parser(nome)
        p.add_argument("--projeto", default=None, help="pasta do projeto (padrão: a atual)")
        p.add_argument("--sem-projeto", action="store_true")
        p.add_argument("--sem-maquina", action="store_true")
        if nome == "report":
            p.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    projeto = None if a.sem_projeto else (a.projeto or os.getcwd())
    try:
        res = varrer(projeto, maquina=not a.sem_maquina)
        if a.cmd == "scan":
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            page = render_html(res, time.strftime("%Y-%m-%d %H:%M"))
            out = a.out or os.path.join(resolve_visual_dir(projeto or os.getcwd()),
                                        "%s-sec.html" % time.strftime("%Y-%m-%d"))
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(page)
            print(out)
    except SecError as e:
        print("sec: %s" % e, file=sys.stderr)
        return 1
    return 2 if res["falhas"] else 0


if __name__ == "__main__":
    sys.exit(main())
