#!/usr/bin/env python3
"""test_script_audit.py — o analisador que decide quais scripts dos plugins rodam sem pedir.

Cada caso monta um script de mentira e confere a classe que o analisador da.
O que importa aqui e o lado perigoso: tudo o que executa comando, avalia codigo, carrega
codigo escolhido em tempo de execucao ou fala com a rede TEM que sair de `puro` — inclusive
quando o executor mora num modulo local que o script importa.
"""
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import script_audit

falhas = 0
casos = 0


def check(nome, ok, detalhe=""):
    global falhas, casos
    casos += 1
    if ok:
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


def classe(arquivos, principal, ext=".py"):
    """Escreve `arquivos` ({nome: texto}) num plugin de mentira e classifica `principal`."""
    with tempfile.TemporaryDirectory() as t:
        for nome, texto in arquivos.items():
            cam = os.path.join(t, nome)
            os.makedirs(os.path.dirname(cam), exist_ok=True)
            with open(cam, "w", encoding="utf-8") as f:
                f.write(texto)
        return script_audit.classifica_arquivo(os.path.join(t, principal), t)["classe"]


print("── python: o que executa comando ou codigo ──")
PURO = "import json, sys\nprint(json.dumps(sys.argv[1:]))\n"
check("script que so le argv e imprime e puro", classe({"a.py": PURO}, "a.py") == "puro")
casos_exec = {
    "import subprocess": "import subprocess\nsubprocess.run(['ls'])\n",
    "subprocess com alias": "import subprocess as sp\nsp.call('ls', shell=True)\n",
    "from subprocess import run": "from subprocess import run\nrun(['ls'])\n",
    "os.system": "import os\nos.system('ls')\n",
    "from os import system": "from os import system\nsystem('ls')\n",
    "os.popen": "import os\nos.popen('ls')\n",
    "os.execv": "import os\nos.execv('/bin/sh', ['sh'])\n",
    "__import__": "__import__('os').system('ls')\n",
    "eval": "import sys\neval(sys.argv[1])\n",
    "exec": "import sys\nexec(sys.stdin.read())\n",
    "compile": "import sys\ncompile(sys.argv[1], 'x', 'exec')\n",
    "importlib": "import importlib\nimportlib.import_module('os')\n",
    "runpy": "import runpy\nrunpy.run_path('x.py')\n",
    "pickle": "import pickle, sys\npickle.load(open(sys.argv[1], 'rb'))\n",
    "ctypes": "import ctypes\n",
    "multiprocessing": "import multiprocessing\n",
    "getattr(os, nome)": "import os, sys\ngetattr(os, sys.argv[1])('ls')\n",
    "__builtins__": "__builtins__.__dict__['ev' + 'al']('1')\n",
    "pty.spawn": "import pty\npty.spawn('sh')\n",
}
for nome, texto in casos_exec.items():
    check("executa: %s" % nome, classe({"a.py": texto}, "a.py") == "executa", classe({"a.py": texto}, "a.py"))

print("── python: o que e inofensivo continua puro ──")
check("getattr(args, nome) de argparse e puro",
      classe({"a.py": "import argparse\na = argparse.Namespace()\ngetattr(a, 'x', None)\n"}, "a.py") == "puro")
check("palavra 'subprocess' em docstring e comentario nao acusa",
      classe({"a.py": '"""nao roda subprocess nenhum"""\n# eval(x) so no comentario\nx = "os.system"\n'}, "a.py") == "puro")
check("urllib.parse so manipula texto de URL",
      classe({"a.py": "from urllib.parse import quote\nprint(quote('a b'))\n"}, "a.py") == "puro")
check("from urllib import parse tambem", classe({"a.py": "from urllib import parse\n"}, "a.py") == "puro")
check("escrever arquivo nao e executar comando (so e anotado na coluna 'escreve')",
      classe({"a.py": "import sys\nopen(sys.argv[1], 'w').write('x')\n"}, "a.py") == "puro")

print("── python: rede e ilegivel ──")
check("urllib.request e rede", classe({"a.py": "import urllib.request\n"}, "a.py") == "rede")
check("socket e rede", classe({"a.py": "import socket\n"}, "a.py") == "rede")
check("http.server e rede", classe({"a.py": "from http.server import HTTPServer\n"}, "a.py") == "rede")
check("erro de sintaxe e ilegivel (na duvida, pede)", classe({"a.py": "def (:\n"}, "a.py") == "ilegivel")

print("── python: o executor mora em outro modulo ──")
check("importa modulo local que usa subprocess → executa",
      classe({"a.py": "import ajuda\najuda.f()\n", "ajuda.py": "import subprocess\ndef f():\n    subprocess.run(['ls'])\n"}, "a.py") == "executa")
check("from modulo import → executa",
      classe({"a.py": "from ajuda import f\n", "lib/ajuda.py": "import os\ndef f(c):\n    os.system(c)\n"}, "a.py") == "executa")
check("a cadeia de dois saltos tambem → executa",
      classe({"a.py": "import b\n", "b.py": "import c\n", "c.py": "import subprocess\n"}, "a.py") == "executa")
check("import circular nao trava", classe({"a.py": "import b\n", "b.py": "import a\n"}, "a.py") == "puro")
check("modulo local puro → puro", classe({"a.py": "import b\n", "b.py": PURO}, "a.py") == "puro")

print("── javascript ──")
JS_PURO = "import fs from 'node:fs';\nconsole.log(process.argv.slice(2));\n"
check("mjs que so le e imprime e puro", classe({"a.mjs": JS_PURO}, "a.mjs") == "puro")
for nome, texto in {
    "child_process": "import { spawn } from 'node:child_process';\n",
    "execSync": "const { execSync } = require('child_process');\nexecSync('ls');\n",
    "eval": "eval(process.argv[2]);\n",
    "new Function": "new Function(process.argv[2])();\n",
    "import() dinamico": "const m = await import(process.argv[2]);\n",
    "require dinamico": "require(process.argv[2]);\n",
    "vm": "import vm from 'node:vm';\n",
}.items():
    check("js executa: %s" % nome, classe({"a.mjs": texto}, "a.mjs") == "executa", classe({"a.mjs": texto}, "a.mjs"))
check("js fetch e rede", classe({"a.mjs": "await fetch('https://example.com');\n"}, "a.mjs") == "rede")
check("js http e rede", classe({"a.mjs": "import http from 'node:http';\n"}, "a.mjs") == "rede")
check("js importa modulo local com child_process → executa",
      classe({"a.mjs": "import { f } from './b.mjs';\n", "b.mjs": "import { spawn } from 'node:child_process';\n"}, "a.mjs") == "executa")
check("palavra eval( em comentario js nao acusa",
      classe({"a.mjs": "// nao usa eval(x)\n/* spawn( */\nconsole.log(1);\n"}, "a.mjs") == "puro")

print("── a arvore real ──")
raiz = script_audit.raiz_do_repo()
if raiz is None:
    print("  skip  sem o repositorio ao lado (rodando de dentro do cache)")
else:
    linhas = {(l["plugin"], l["script"]): l for l in script_audit.varre_repo(raiz)}
    pre = linhas[("project-skills", "lib/precheck_largada.py")]
    check("precheck_largada.py (bash -c do --suite/--gate) → executa", pre["classe"] == "executa", pre)
    check("quem importa o precheck herda: completude.py → executa",
          linhas[("project-skills", "lib/completude.py")]["classe"] == "executa")
    check("sec.py (subprocess + rede) → executa", linhas[("sec", "lib/sec.py")]["classe"] == "executa")
    check("lixeiro.py → executa", linhas[("lixeiro", "lib/lixeiro.py")]["classe"] == "executa")
    check("visual_server.mjs (servidor http) nao e liberado", linhas[("visual", "server/visual_server.mjs")]["classe"] != "puro")
    check("quem_serviu.py (stdlib, sem processo) → puro", linhas[("2op", "lib/quem_serviu.py")]["classe"] == "puro")
    check("cfgjson.py importa o analisador (que chama git) → executa, e nao e liberado",
          linhas[("bootstrap", "lib/cfgjson.py")]["classe"] == "executa")
    liberados = script_audit.lista_permitida(script_audit.varre_repo(raiz))
    check("nenhum liberado e executor", all(linhas[(e["plugin"], e["script"])]["classe"] == "puro" for e in liberados))
    check("ha liberados (a lista nao ficou vazia)", len(liberados) >= 10, len(liberados))

print("\n%d ok · %d FAIL" % (casos - falhas, falhas))
sys.exit(1 if falhas else 0)
