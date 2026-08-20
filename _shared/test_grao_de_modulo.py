#!/usr/bin/env python3
"""Suíte do grão de módulo — um caso sintético por classe A-E.

Cada caso monta em tempdir a forma que o survey de 2026-08-19 mediu em
repositório real, e cobra classe, grão e a decisão do dono (A/B/C têm
diagrama por módulo; D/E só o organismo).

    python3 _shared/test_grao_de_modulo.py
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "grao_de_modulo", os.path.join(AQUI, "grao-de-modulo.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
classificar = _mod.classificar

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s%s" % (label, " — %s" % extra if extra else ""))


def toca(raiz, *caminhos):
    for c in caminhos:
        p = os.path.join(raiz, c)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").close()


def caso_A():
    """Coleção de unidades nomeadas: plugins/ com 4 irmãs comparáveis."""
    with tempfile.TemporaryDirectory() as raiz:
        for u in ("alfa", "beta", "gama", "delta"):
            toca(raiz, "plugins/%s/skill.md" % u, "plugins/%s/hook.sh" % u)
        r = classificar(raiz)
        check("A: classe", r["classe"] == "A", json.dumps(r))
        check("A: 4 unidades com o tronco no nome",
              sorted(r["unidades"]) == ["plugins/alfa", "plugins/beta",
                                        "plugins/delta", "plugins/gama"], json.dumps(r))
        check("A: diagrama por módulo", r["diagrama_por_modulo"] is True)


def caso_B():
    """Monorepo declarado: 'workspaces' no package.json vence qualquer árvore."""
    with tempfile.TemporaryDirectory() as raiz:
        with open(os.path.join(raiz, "package.json"), "w") as f:
            json.dump({"workspaces": ["apps/*", "packages/*"]}, f)
        toca(raiz, "apps/site/package.json", "apps/admin/package.json",
             "packages/ui/package.json")
        r = classificar(raiz)
        check("B: classe", r["classe"] == "B", json.dumps(r))
        check("B: unidades saem do MANIFESTO",
              sorted(r["unidades"]) == ["apps/admin", "apps/site", "packages/ui"],
              json.dumps(r))
        check("B: diagrama por módulo", r["diagrama_por_modulo"] is True)


def caso_C():
    """Dois lados que conversam: backend/ e frontend/ com manifesto próprio."""
    with tempfile.TemporaryDirectory() as raiz:
        toca(raiz, "backend/requirements.txt", "backend/main.py",
             "frontend/package.json", "frontend/index.html", "docker/compose.yml")
        r = classificar(raiz)
        check("C: classe", r["classe"] == "C", json.dumps(r))
        check("C: unidades são os lados",
              set(r["unidades"]) >= {"backend", "frontend"}, json.dumps(r))
        check("C: diagrama por módulo", r["diagrama_por_modulo"] is True)


def caso_D():
    """App em camadas: src/ único, >= 100 arquivos, subpastas NÃO comparáveis."""
    with tempfile.TemporaryDirectory() as raiz:
        toca(raiz, *["src/components/c%03d.ts" % i for i in range(95)])
        toca(raiz, "src/utils/u.ts", "src/hooks/h.ts", "src/index.ts",
             "README.md", "tsconfig.json")
        r = classificar(raiz)
        check("D: classe", r["classe"] == "D", json.dumps(r))
        check("D: sem unidades", r["unidades"] == [])
        check("D: SEM diagrama de módulo", r["diagrama_por_modulo"] is False)


def caso_E():
    """Projeto pequeno: < 100 arquivos, sem pasta estruturante."""
    with tempfile.TemporaryDirectory() as raiz:
        toca(raiz, "main.py", "config.py", "README.md")
        r = classificar(raiz)
        check("E: classe", r["classe"] == "E", json.dumps(r))
        check("E: SEM diagrama de módulo", r["diagrama_por_modulo"] is False)


def caso_precedencia():
    """Manifesto de workspace (B) vence a coleção (A): a precedência É a regra."""
    with tempfile.TemporaryDirectory() as raiz:
        with open(os.path.join(raiz, "package.json"), "w") as f:
            json.dump({"workspaces": ["apps/*"]}, f)
        for u in ("um", "dois", "tres"):
            toca(raiz, "apps/%s/package.json" % u, "apps/%s/index.js" % u)
        r = classificar(raiz)
        check("precedência: B antes de A", r["classe"] == "B", json.dumps(r))


def caso_cli():
    """A linha de comando devolve o mesmo JSON — é assim que as skills consomem."""
    with tempfile.TemporaryDirectory() as raiz:
        toca(raiz, "main.py")
        out = subprocess.run(
            [sys.executable, os.path.join(AQUI, "grao-de-modulo.py"), raiz],
            capture_output=True, text=True, timeout=60,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )
        check("cli: exit 0", out.returncode == 0, out.stderr)
        r = json.loads(out.stdout)
        check("cli: JSON com as 4 chaves",
              set(r) == {"classe", "grao", "unidades", "diagrama_por_modulo"},
              out.stdout)


for caso in (caso_A, caso_B, caso_C, caso_D, caso_E, caso_precedencia, caso_cli):
    print(caso.__name__)
    caso()

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
