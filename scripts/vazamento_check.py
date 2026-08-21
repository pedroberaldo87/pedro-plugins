#!/usr/bin/env python3
"""vazamento_check.py — nenhum disparo de processo pode deixar filho para trás.

O QUE ACONTECEU, e é por isso que este cobrador existe: em 2026-08-08 uma máquina
acumulou **2125 processos `python3` órfãos** (todos com pai `1`). O gatilho foi um
ciclo — `plano_vs_codigo` executa o critério de um passo, o critério manda rodar o
`medidor`, o medidor roda o `plano_vs_codigo` —, mas o ciclo só multiplicou porque
cada disparo individual já vazava. Eram 155 pontos assim no repositório.

AS DUAS REGRAS, e cada uma tapa um vazamento diferente:

  `stdin=` SEMPRE          Sem isso o filho herda o terminal do pai. Comando que
                           pergunta alguma coisa — `git` pedindo credencial é o caso
                           real — espera para sempre, e o `timeout` NÃO o alcança:
                           ele não estourou, está parado. Vale `subprocess.DEVNULL`
                           (o padrão certo) ou `subprocess.PIPE` quando há `input=`.

  `start_new_session=`     O `timeout` mata o filho direto e deixa o NETO vivo. Quando
                           o filho é um shell, o `python3` que ele abriu fica órfão.
                           Com o grupo próprio dá para derrubar a árvore inteira.

`input=` e `stdin=` juntos é ERRO do Python (`ValueError`), então a chamada com
`input=` fica isenta da primeira regra — quem passa `input` já controla o stdin.

Régua manual:  python3 scripts/vazamento_check.py
Sai 1 e nomeia arquivo:linha de cada disparo que pode vazar.
"""

import argparse
import ast
import glob
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Todo jeito de nascer um processo filho neste repositório.
DISPARO = {
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "subprocess.check_output", "subprocess.check_call",
}
# Estes dois nem aceitam os cuidados: não há como fechar stdin nem criar grupo.
PROIBIDO = {"os.system", "os.popen"}

# `acopla-ok` é a isenção do desacoplamento; aqui a isenção tem nome próprio, porque o
# motivo é outro: o disparo é seguro por uma razão que a análise estática não enxerga.
ISENCAO = "vaza-ok:"


# O LADO JS, e ele existe: o motor de slides, o do gauntlet e o renderizador do archify
# são Node. `spawnSync(..., {stdio: 'inherit'})` herda o terminal do pai pelo MESMO
# motivo do `stdin` ausente em Python — e `spawn` sem `timeout` não tem teto nenhum.
# Regex, e não árvore sintática: não há analisador de JS na stdlib, e trazer um para
# checar três arquivos custaria mais que o defeito. O preço é falso-negativo em código
# muito torto, e ele é aceito — o cobrador aponta onde olhar, não substitui a leitura.
JS_DISPARO = re.compile(r"\b(spawnSync|spawn|execSync|exec|execFileSync|execFile)\s*\(")
# O padrão do `stdio` herdado e o do já consertado vêm da CÓPIA LOCAL de
# `_shared/padroes_vazamento.py` (vendorada por `scripts/sync-shared.sh`), a mesma que
# a quinta lente do /check-skills e a investigação do /lixeiro leem. Três programas
# cobram este defeito, e no dia em que nasceram já divergiam.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from padroes_vazamento import NODE_OK as JS_OK  # noqa: E402
from padroes_vazamento import RISCO as _RISCO  # noqa: E402

JS_HERDA = next(p for p, _c, _h in _RISCO if "stdio" in p.pattern)


# Quando o gate roda no commit, o universo é o do commit — não a árvore inteira.
# Rascunho não rastreado no disco de um agente reprovava o commit de todo mundo.
SO_DO_COMMIT = None  # None = árvore inteira; set = caminhos absolutos que vão no commit


def _universo_do_commit():
    """staged ∪ tracked-modificado — o mesmo universo que o release-gate declara."""
    achados = set()
    for cmd in (["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                ["git", "diff", "--name-only", "--diff-filter=ACMR"]):
        r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, start_new_session=True)
        achados |= {os.path.join(RAIZ, x) for x in r.stdout.splitlines() if x}
    return achados


def _arquivos(ext=("py",)):
    padroes = []
    for e in ext:
        padroes += ["plugins/**/*.%s" % e, "scripts/*.%s" % e, "_shared/*.%s" % e]
    for p in padroes:
        for f in glob.glob(os.path.join(RAIZ, p), recursive=True):
            if "__pycache__" in f or "/node_modules/" in f:
                continue
            if SO_DO_COMMIT is not None and os.path.realpath(f) not in SO_DO_COMMIT:
                continue
            yield f


def _varre_js(raiz):
    """Disparo em Node que herda o terminal do pai — o mesmo defeito, outra linguagem."""
    achados = []
    for f in sorted(_arquivos(("mjs", "js"))):
        try:
            linhas = open(f, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        rel = os.path.relpath(f, raiz or RAIZ)
        for i, linha in enumerate(linhas, 1):
            if not JS_DISPARO.search(linha):
                continue
            # a chamada em JS costuma abrir opções nas linhas seguintes
            bloco = "\n".join(linhas[max(0, i - 2):i + 8])
            if ISENCAO in bloco:
                continue
            if JS_HERDA.search(bloco) and not JS_OK.search(bloco):
                achados.append({"arquivo": rel, "linha": i, "chamada": "node:child_process",
                                "falta": "stdio 'inherit' herda o terminal — use 'pipe' ou 'ignore'"})
    return achados


def varre(raiz=None):
    """[{arquivo, linha, chamada, falta}] — vazio quando nada pode vazar."""
    achados = []
    for f in sorted(_arquivos()):
        try:
            src = open(f, encoding="utf-8", errors="replace").read()
            arv = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        linhas = src.splitlines()
        rel = os.path.relpath(f, raiz or RAIZ)
        for n in ast.walk(arv):
            if not isinstance(n, ast.Call):
                continue
            alvo = ast.unparse(n.func)
            if alvo not in DISPARO and alvo not in PROIBIDO:
                continue
            # a isenção vale na linha da chamada ou na de cima
            volta = "\n".join(linhas[max(0, n.lineno - 2):n.lineno])
            if ISENCAO in volta:
                continue
            if alvo in PROIBIDO:
                achados.append({"arquivo": rel, "linha": n.lineno, "chamada": alvo,
                                "falta": "não tem como fechar stdin nem criar grupo — use subprocess"})
                continue
            kw = {k.arg for k in n.keywords}
            falta = []
            if "stdin" not in kw and "input" not in kw:
                falta.append("stdin=")
            if "start_new_session" not in kw:
                falta.append("start_new_session=True")
            if falta:
                achados.append({"arquivo": rel, "linha": n.lineno, "chamada": alvo,
                                "falta": " e ".join(falta)})
    return achados + _varre_js(raiz)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true")
    p.add_argument("--staged", action="store_true",
                   help="só os arquivos que vão no commit (staged ∪ tracked-modificado)")
    a = p.parse_args(argv)
    if a.staged:
        globals()["SO_DO_COMMIT"] = {os.path.realpath(x) for x in _universo_do_commit()}
    r = varre()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    elif not r:
        print("vazamento-check: OK — nenhum disparo de processo pode deixar filho para trás")
    else:
        print("VAZAMENTO — %d disparo(s) podem deixar processo para trás:\n" % len(r))
        for x in r:
            print("  %s:%s  %s — falta %s" % (x["arquivo"], x["linha"], x["chamada"], x["falta"]))
        print("\nO conserto: stdin=subprocess.DEVNULL e start_new_session=True no disparo,")
        print("e os.killpg no finally quando houver timeout. Isenção: `%s <motivo>` na linha." % ISENCAO)
    return 1 if r else 0


if __name__ == "__main__":
    sys.exit(main())
