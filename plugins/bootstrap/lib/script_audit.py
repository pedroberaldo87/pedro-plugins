#!/usr/bin/env python3
"""script_audit.py — quais scripts dos plugins podem rodar sem pedir aprovacao.

POR QUE EXISTE. Os defaults do bootstrap liberam `python3 <script do cache>`
(decisao D-1 do dono: so os scripts dos proprios plugins). Liberar o DIRETORIO
inteiro entregava execucao arbitraria: `precheck_largada.py --suite '<cmd>'`
roda `<cmd>` com `bash -c`. A liberacao certa e POR SCRIPT, e so para o script
que nao executa comando vindo de quem o chama. Este modulo decide isso.

O QUE CONTA COMO "EXECUTA COMANDO". Um script e reprovado (continua pedindo
aprovacao) quando ele, ou um modulo local que ele importa, faz qualquer uma
destas coisas:
  * cria processo (subprocess, os.system/popen/exec*/spawn*, pty, child_process);
  * avalia texto como codigo (eval, exec, compile, vm, new Function);
  * carrega codigo escolhido em tempo de execucao (importlib, __import__, runpy,
    pickle, marshal, ctypes, import() / require() dinamicos);
  * fala com a rede (socket, urllib, http, requests, fetch, net...): argv + rede
    = o canal de saida que a decisao D-1 nao quer abrir;
  * nao da para ler (erro de sintaxe) — na duvida, pede.
A analise e conservadora de proposito: ela erra para o lado de pedir aprovacao.
O que ela NAO prova: que o script e inofensivo. Um script puro ainda pode ler e
escrever arquivo no caminho que receber; D-1 aceita isso (e a coluna `escreve`
do relatorio mostra quais fazem).

COMO O CFGJSON USA. `config/plugin-scripts.json` tem duas listas, geradas por
`--gravar` (um teste cobra que nao envelhecam): os scripts que as skills chamam
e passaram na analise (`scripts`, ganham allow) e os que chamam e NAO passaram
(`pedem_aprovacao`, ganham ask, que vence qualquer allow largo antigo). Na hora do merge, `cfgjson.py` roda `classifica_arquivo`
de novo sobre a copia que esta de fato no cache da maquina: o que mudou e virou
executor deixa de ganhar a regra.

Uso:
  script_audit.py --gravar        regrava config/plugin-scripts.json e o relatorio
  script_audit.py --confere       sai 1 se algum dos dois envelheceu
  script_audit.py --tabela        imprime o relatorio (markdown)
"""
import ast
import json
import os
import re
import subprocess
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
BOOTSTRAP = os.path.dirname(QUI)
LISTA_JSON = os.path.join(BOOTSTRAP, "config", "plugin-scripts.json")
RELATORIO_MD = os.path.join(BOOTSTRAP, "config", "plugin-scripts-audit.md")

# ---- Python -----------------------------------------------------------------
CHAMADAS_EXEC = frozenset("""
os.system os.popen os.execv os.execve os.execl os.execle os.execlp os.execlpe
os.execvp os.execvpe os.spawnl os.spawnle os.spawnlp os.spawnlpe os.spawnv
os.spawnve os.spawnvp os.spawnvpe os.posix_spawn os.posix_spawnp os.startfile
pty.spawn webbrowser.open webbrowser.open_new webbrowser.open_new_tab
runpy.run_path runpy.run_module importlib.import_module __import__ eval exec
compile execfile globals breakpoint
""".split())
# modulos cuja simples importacao ja e capacidade de executar ou de carregar codigo
MODULOS_EXEC = frozenset("""
subprocess pty multiprocessing commands pexpect sh plumbum runpy code pdb ctypes
cffi importlib imp pickle cPickle marshal shelve dill cloudpickle zipimport
pkgutil posix builtins
""".split())
MODULOS_REDE = frozenset("""
socket urllib http requests httpx aiohttp smtplib ftplib telnetlib ssl websocket
websockets xmlrpc socketserver poplib imaplib nntplib webbrowser asyncio
""".split())
# getattr(os, nome) acha `system` sem escreve-lo: acusa getattr/setattr quando o
# alvo e um modulo que executa. getattr(args, nome) (argparse) e inofensivo.
ALVOS_DE_GETATTR = frozenset({"os", "sys", "builtins", "__builtins__", "importlib", "posix",
                              "subprocess", "pty", "runpy"})
# `from urllib import parse` / `import urllib.parse`: so manipula texto de URL
REDE_INOFENSIVA = frozenset({"urllib.parse"})

# ---- JavaScript ---------------------------------------------------------------
RE_JS_EXEC = re.compile(
    r"child_process|\bexecSync\b|\bspawnSync\b|\bexecFile\b|\bspawn\s*\(|\bfork\s*\("
    r"|\beval\s*\(|new\s+Function\b|\bFunction\s*\("
    r"|node:vm|['\"]vm['\"]|\bvm\.(?:run|Script|compile)"
    r"|worker_threads|node:cluster|['\"]cluster['\"]|process\.binding|process\.dlopen"
    r"|WebAssembly|\bimport\s*\(\s*[^'\"\s]|\brequire\s*\(\s*[^'\"\s]"
    r"|\bimport\s*\(\s*['\"](?!\.)|\brequire\.resolve\b|module\.constructor|createRequire")
RE_JS_REDE = re.compile(
    r"from\s+['\"](?:node:)?(?:http|https|http2|net|dgram|dns|tls)['\"]"
    r"|require\(\s*['\"](?:node:)?(?:http|https|http2|net|dgram|dns|tls)['\"]\s*\)"
    r"|\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|navigator\.sendBeacon")
RE_JS_IMPORT_LOCAL = re.compile(
    r"""(?:from\s+|import\s*\(?\s*|require\(\s*)['"](\.{1,2}/[^'"]+)['"]""")

ESCRITA_PY = re.compile(r"""open\([^)]*['"][wax+][bt+]?['"]|\.write_text\(|\.write_bytes\(|os\.(?:remove|unlink|rename|replace|rmdir|makedirs|mkdir)\(|shutil\.|\.mkdir\(|\.unlink\(""")
ESCRITA_JS = re.compile(r"writeFile|appendFile|createWriteStream|rmSync|unlink|mkdirSync|renameSync|copyFileSync|\.cp\(")


def _le(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def _nome_chamada(no):
    f = no.func
    if isinstance(f, ast.Name):
        return f.id
    partes = []
    while isinstance(f, ast.Attribute):
        partes.append(f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        partes.append(f.id)
        return ".".join(reversed(partes))
    return None


def _modulos_locais(raiz, nomes):
    """Arquivos .py dentro de `raiz` cujo nome de modulo esta em `nomes`."""
    alvo = {n.split(".")[-1] for n in nomes if n}
    achados = []
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git", "__pycache__")]
        for f in fn:
            if f.endswith(".py") and f[:-3] in alvo:
                achados.append(os.path.join(dp, f))
    return achados


def _escaneia_py(caminho):
    """-> (motivos_exec, motivos_rede, modulos_importados, escreve)"""
    src = _le(caminho)
    arvore = ast.parse(src)
    ex, rede, imps = set(), set(), set()
    dotados = set()          # nomes completos importados (urllib.parse, os.path...)
    for n in ast.walk(arvore):
        if isinstance(n, ast.Import):
            for a in n.names:
                imps.add(a.name)
                dotados.add(a.name)
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ""
            imps.add(base)
            dotados.add(base)
            for a in n.names:
                imps.add(a.name)
                comp = (base + "." + a.name).strip(".")
                dotados.add(comp)
                if comp in CHAMADAS_EXEC:
                    ex.add("from-import " + comp)
        elif isinstance(n, ast.Name) and n.id == "__builtins__":
            ex.add("acesso a __builtins__")
        elif isinstance(n, ast.Call):
            nome = _nome_chamada(n)
            if nome in CHAMADAS_EXEC:
                ex.add("chamada " + nome)
            elif nome in ("getattr", "setattr") and n.args:
                alvo = n.args[0]
                if isinstance(alvo, ast.Name) and alvo.id in ALVOS_DE_GETATTR:
                    ex.add("chamada %s(%s, ...)" % (nome, alvo.id))
    for i in imps:
        if i.split(".")[0] in MODULOS_EXEC:
            ex.add("import " + i.split(".")[0])
    for d in dotados:
        topo = d.split(".")[0]
        if topo not in MODULOS_REDE or any(d == ok or d.startswith(ok + ".") for ok in REDE_INOFENSIVA):
            continue
        # `from urllib import parse` aparece como `urllib` + `urllib.parse`
        if d == "urllib" and "urllib.parse" in dotados and not (dotados & {"urllib.request", "urllib.error", "urllib.response"}):
            continue
        rede.add("import " + d)
    return ex, rede, imps, bool(ESCRITA_PY.search(src))


def _escaneia_js(caminho):
    src = _le(caminho)
    # tira comentarios de linha e de bloco para nao acusar texto de documentacao
    limpo = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    limpo = re.sub(r"(?m)^\s*//.*$", "", limpo)
    ex = {m.group(0).strip() for m in RE_JS_EXEC.finditer(limpo)}
    rede = {m.group(0).strip() for m in RE_JS_REDE.finditer(limpo)}
    locais = RE_JS_IMPORT_LOCAL.findall(limpo)
    return ex, rede, locais, bool(ESCRITA_JS.search(limpo))


def classifica_arquivo(caminho, raiz_plugin):
    """Classifica UM script.

    Devolve {"classe": "puro"|"executa"|"rede"|"ilegivel", "motivos": [...],
             "escreve": bool}. `raiz_plugin` limita onde os modulos locais sao
    procurados. Transitivo: o que o modulo importado faz, o script faz.
    """
    visto = set()
    motivos = []
    rede_total = []
    escreve = False
    ilegivel = False
    fila = [os.path.abspath(caminho)]
    raiz_plugin = os.path.abspath(raiz_plugin)
    while fila:
        atual = fila.pop()
        if atual in visto:
            continue
        visto.add(atual)
        rotulo = "" if atual == os.path.abspath(caminho) else os.path.relpath(atual, raiz_plugin) + ": "
        try:
            if atual.endswith(".py"):
                ex, rede, imps, esc = _escaneia_py(atual)
                for m in _modulos_locais(raiz_plugin, imps):
                    fila.append(os.path.abspath(m))
            else:
                ex, rede, locais, esc = _escaneia_js(atual)
                for rel in locais:
                    alvo = os.path.normpath(os.path.join(os.path.dirname(atual), rel))
                    for cand in (alvo, alvo + ".mjs", alvo + ".js", alvo + ".cjs",
                                 os.path.join(alvo, "index.js"), os.path.join(alvo, "index.mjs")):
                        if os.path.isfile(cand):
                            fila.append(cand)
                            break
        except (OSError, SyntaxError, ValueError, UnicodeDecodeError, RecursionError) as e:
            ilegivel = True
            motivos.append("%snao consegui ler (%s)" % (rotulo, type(e).__name__))
            continue
        motivos += [rotulo + m for m in sorted(ex)]
        rede_total += [rotulo + m for m in sorted(rede)]
        escreve = escreve or esc
    if ilegivel:
        classe = "ilegivel"
    elif motivos:
        classe = "executa"
    elif rede_total:
        classe = "rede"
    else:
        classe = "puro"
    return {"classe": classe, "motivos": motivos + rede_total, "escreve": escreve}


# ---- o repositorio ------------------------------------------------------------
def _git_ls(raiz_repo):
    r = subprocess.run(["git", "-C", raiz_repo, "ls-files", "plugins"],
                       capture_output=True, text=True, encoding="utf-8")
    return [l for l in r.stdout.splitlines() if l]


def raiz_do_repo():
    cand = os.path.dirname(os.path.dirname(BOOTSTRAP))
    return cand if os.path.isdir(os.path.join(cand, "_shared")) and os.path.isdir(os.path.join(cand, "plugins")) else None


def _texto_que_chama(raiz_repo, arquivos):
    """Por plugin, o texto onde o MODELO le qual script rodar: skills, comandos,
    agentes e as mensagens dos hooks. Quem so existe em teste nao aparece."""
    por_plugin = {}
    for f in arquivos:
        partes = f.split("/")
        base = partes[-1]
        if len(partes) < 3:
            continue
        doc = base.endswith(".md") and ("skills" in partes or "commands" in partes or "agents" in partes)
        hook = "hooks" in partes and base.endswith(".sh") and not base.startswith("test_")
        if doc or hook or base in ("hooks.json", "package.json"):
            try:
                por_plugin[partes[1]] = por_plugin.get(partes[1], "") + "\n" + _le(os.path.join(raiz_repo, f))
            except (OSError, UnicodeDecodeError):
                pass
    return por_plugin


def varre_repo(raiz_repo):
    """Todos os scripts de plugins/ com classe e se alguma skill/hook o cita."""
    arquivos = _git_ls(raiz_repo)
    citados = _texto_que_chama(raiz_repo, arquivos)
    linhas = []
    for f in sorted(arquivos):
        if "node_modules" in f or not re.search(r"\.(py|mjs|js|cjs)$", f):
            continue
        partes = f.split("/")
        plugin, rel = partes[1], "/".join(partes[2:])
        base = partes[-1]
        if base.startswith("test_") or base == "__init__.py":
            continue
        raiz_plugin = os.path.join(raiz_repo, "plugins", plugin)
        info = classifica_arquivo(os.path.join(raiz_repo, f), raiz_plugin)
        info.update({"plugin": plugin, "script": rel,
                     "citado": base in citados.get(plugin, ""),
                     "interprete": "python3" if base.endswith(".py") else "node"})
        linhas.append(info)
    return linhas


def lista_permitida(linhas):
    return [{"plugin": l["plugin"], "script": l["script"], "interprete": l["interprete"]}
            for l in linhas if l["citado"] and l["classe"] == "puro"]


def _tabela(linhas):
    cont = {}
    for l in linhas:
        cont[l["classe"]] = cont.get(l["classe"], 0) + 1
    perm = [l for l in linhas if l["citado"] and l["classe"] == "puro"]
    out = ["# Auditoria dos scripts dos plugins (gerado por lib/script_audit.py — nao edite)", "",
           "Regra gerada so para o script **citado por skill ou hook** e **sem executar comando, "
           "carregar codigo ou usar rede**. Os demais continuam pedindo aprovacao.", "",
           "Scripts analisados: %d · liberados: %d · executam comando/carregam codigo: %d · "
           "usam rede: %d · ilegiveis: %d"
           % (len(linhas), len(perm), cont.get("executa", 0), cont.get("rede", 0), cont.get("ilegivel", 0)),
           "", "| plugin | script | citado | classe | escreve arquivo | por que |", "|---|---|---|---|---|---|"]
    for l in linhas:
        por_que = "; ".join(l["motivos"][:4]) + (" …" if len(l["motivos"]) > 4 else "")
        dec = {"puro": ("liberado" if l["citado"] else "puro, nao citado"),
               "executa": "executa", "rede": "rede", "ilegivel": "ilegivel"}[l["classe"]]
        out.append("| %s | `%s` | %s | %s | %s | %s |" % (
            l["plugin"], l["script"], "sim" if l["citado"] else "não", dec,
            "sim" if l["escreve"] else "não", por_que or "—"))
    return "\n".join(out) + "\n"


def lista_que_pede(linhas):
    """Scripts citados que executam comando (ou usam rede): ganham uma regra de ask,
    que vence qualquer allow largo que a maquina ainda tenha de versoes antigas."""
    return [{"plugin": l["plugin"], "script": l["script"]}
            for l in linhas if l["citado"] and l["classe"] != "puro"]


def _json_da_lista(linhas):
    return json.dumps({"_": "gerado por lib/script_audit.py --gravar; nao edite a mao",
                       "scripts": lista_permitida(linhas),
                       "pedem_aprovacao": lista_que_pede(linhas)},
                      ensure_ascii=False, indent=2) + "\n"


def main(argv):
    modo = argv[1] if len(argv) > 1 else ""
    if modo not in ("--gravar", "--confere", "--tabela"):
        print(__doc__.split("Uso:")[1].strip(), file=sys.stderr)
        return 2
    raiz = raiz_do_repo()
    if raiz is None:
        print("script_audit: preciso do repositorio (plugins/ + _shared/) ao lado", file=sys.stderr)
        return 2
    linhas = varre_repo(raiz)
    lista, tabela = _json_da_lista(linhas), _tabela(linhas)
    if modo == "--tabela":
        sys.stdout.write(tabela)
        return 0
    if modo == "--gravar":
        for caminho, conteudo in ((LISTA_JSON, lista), (RELATORIO_MD, tabela)):
            with open(caminho, "w", encoding="utf-8", newline="\n") as f:
                f.write(conteudo)
        print("gravado: %s e %s (%d liberados)" % (os.path.relpath(LISTA_JSON, raiz),
                                                   os.path.relpath(RELATORIO_MD, raiz),
                                                   len(lista_permitida(linhas))))
        return 0
    velho = []
    for caminho, conteudo in ((LISTA_JSON, lista), (RELATORIO_MD, tabela)):
        try:
            atual = _le(caminho)
        except OSError:
            atual = None
        if atual != conteudo:
            velho.append(os.path.relpath(caminho, raiz))
    if velho:
        print("desatualizado: %s — rode: python3 plugins/bootstrap/lib/script_audit.py --gravar" % ", ".join(velho))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
