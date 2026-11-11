#!/usr/bin/env python3
"""Suíte da SUBIDA DE DIRETÓRIO dos hooks — todo laço que sobe a árvore tem que terminar.

Por que existe: quatro hooks sobem do `cwd` até achar a doc, o grafo ou a raiz do projeto,
com `while [ "$d" != "/" ]; do d=$(dirname "$d"); done`. No Windows o caminho vem como
`C:/Users/...` e NUNCA vira `/`: `dirname C:/` devolve `C:/` e `dirname .` devolve `.`. O
laço girava para sempre. Em produção isso trava a busca do usuário (o PreToolUse não
volta); no CI do Windows foram três suítes penduradas por dez minutos cada
(`test_sessionstart_doc.sh`, `test_graphify_guard.sh`, e quem as chamasse), caladas, até
o vigia matá-las — e o job seguia "verde" porque o rodador morria antes.

O defeito é de LEXICOGRAFIA, não de sistema: `dirname` é puramente textual, então um `cwd`
de drive (`C:/nada/aqui`) reproduz o laço eterno também no macOS e no Linux. É isso que
esta suíte faz — e cada caso tem teto de relógio, porque o sintoma do defeito é não voltar.

    python3 scripts/test_hooks_subida_termina.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "_shared"))
from bash_posix import bash_posix  # noqa: E402

TETO = 20  # segundos: um hook que sobe 3 níveis volta em milissegundos
ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ✓ %s" % nome)
    else:
        falhas += 1
        print("  ✗ %s%s" % (nome, ("\n      %s" % detalhe) if detalhe else ""))


# O processo roda numa pasta VAZIA e fora de qualquer repositório: o `dirname` de `C:/x` acaba em
# `.`, e `.` é o diretório atual — dentro deste clone ele acharia o `.git` e a subida terminaria
# por sorte, escondendo o defeito.
VAZIA = tempfile.mkdtemp(prefix="subida-")


def roda_bash(args, entrada=""):
    """(voltou?, rc, saida). `voltou=False` é o defeito: o laço não terminou no teto."""
    env = dict(os.environ, HOME=os.path.join(VAZIA, "nao-existe-home"),
               GIT_CEILING_DIRECTORIES=os.path.dirname(VAZIA))
    args = [os.path.join(RAIZ, a) if a.startswith("plugins/") else a for a in args]
    try:
        r = subprocess.run([BASH, *args], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", input=entrada, timeout=TETO, cwd=VAZIA, env=env,
                           start_new_session=True)
    except subprocess.TimeoutExpired:
        return False, None, ""
    return True, r.returncode, (r.stdout or "") + (r.stderr or "")


# No Windows o `bash` do PATH pode ser o do WSL: a receita da casa é um bash que RESPONDE.
BASH = bash_posix()
if BASH is None:
    print("  ↷ pulada: nenhum bash funcional nesta máquina (os hooks são bash)")
    sys.exit(0)

# Caminho de drive que não existe: nenhum marcador a achar, e `dirname` nunca chega a `/`.
CWD = "C:/nao/existe/aqui"

print("lib-project-root.sh: project_root sobe e DESISTE, não gira")
if True:
    voltou, rc, saida = roda_bash(
        ["-c", '. "$1"; project_root "$2"; echo "rc=$?"', "x",
         os.path.join(RAIZ, "plugins/project-skills/hooks/lib-project-root.sh"), CWD])
    check("project_root de um cwd de drive sem projeto volta (teto %ds)" % TETO, voltou)
    check("…e responde 'não achei' (rc=1), em vez de inventar uma raiz", voltou and "rc=1" in saida, saida)

payload_busca = json.dumps({"session_id": "subida-1", "cwd": CWD, "tool_name": "Grep",
                            "tool_input": {"pattern": "foo", "path": CWD}})

print("os hooks que usam a subida")
for nome, caminho, entrada in (
    ("pretooluse-doc-guard.sh", "plugins/project-skills/hooks/pretooluse-doc-guard.sh", payload_busca),
    ("pretooluse-graphify-guard.sh", "plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh", payload_busca),
    ("stop-doc-touch.sh", "plugins/project-skills/hooks/stop-doc-touch.sh",
     json.dumps({"session_id": "subida-2", "cwd": CWD})),
):
    voltou, rc, saida = roda_bash([caminho], entrada)
    check("%s com cwd de drive volta (teto %ds)" % (nome, TETO), voltou)
    check("%s sai 0 (fail-open: não achou projeto, não opina)" % nome, voltou and rc == 0, "rc=%s %s" % (rc, saida[:200]))

shutil.rmtree(VAZIA, ignore_errors=True)
print("\n%d ok · %d falha(s)" % (ok, falhas))
sys.exit(1 if falhas else 0)
