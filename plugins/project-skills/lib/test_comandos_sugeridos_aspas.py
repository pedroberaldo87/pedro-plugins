#!/usr/bin/env python3
"""Aspas de shell nos comandos que o plan_state e o /start ESCREVEM (P5).

Dois achados do scan, os dois do mesmo molde do motor do /sprint (que tem a suíte
`test_motor_aspas.py`): texto que não é do programa entra num comando de shell sem aspas.

  hsf_d8f1134d — o comando de renovar o pré-check (`plan_state.py`, na recusa do tique)
                 e o cartão de fechamento da frente (`git worktree remove <w>` e
                 `git branch -d <b>`) colavam caminho e nome de branch crus. O plano
                 vem de um repositório; o dono COPIA esses comandos e os roda.
  hsf_a43c635d — `diagrama-blueprint.sh` aceitava `fluxo-*.html`, e num `case` o `*`
                 casa `/` e `..`: `fluxo-x/../../y.html` passava e o HTML saía da pasta.

    python3 plugins/project-skills/lib/test_comandos_sugeridos_aspas.py
"""
import contextlib
import html
import io
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import bash_posix  # noqa: E402
import plan_state as ps  # noqa: E402

PLUGIN = os.path.dirname(AQUI)
BLUEPRINT = os.path.join(PLUGIN, "skills", "start", "diagrama-blueprint.sh")
FAILS = []


def palavras(texto):
    """As palavras que o shell enxergaria, ou None se o texto nem é um comando bem formado."""
    try:
        return shlex.split(texto)
    except ValueError:
        return None


def check(nome, cond, detalhe=""):
    if cond:
        print("  ok   %s" % nome)
    else:
        print("  FAIL %s  %s" % (nome, detalhe))
        FAILS.append(nome)


# Nomes com espaço, apóstrofo, `;`, `$(` e crase: o que quebra aspas ingênuas.
RAIZ_FEIA = "proj o'brien; touch PWNED-raiz $(touch PWNED-sub) `touch PWNED-crase`"


def plano_minimo(plan_id="2026-01-01-teste", frente=None):
    p = {"id": plan_id, "title": "t", "status": "active",
         "phases": [{"id": "F1", "title": "f", "items": [
             {"id": "F1.1", "title": "i", "desc": "d", "pronto": "p", "status": "todo"}]}]}
    if frente:
        p["frente"] = frente
    return p


tmp = tempfile.mkdtemp(prefix="aspas-ps-")
try:
    # ── hsf_d8f1134d · o comando de renovar o pré-check ────────────────────────────
    print("hsf_d8f1134d — o `renova` do portão de pré-check")
    raiz = os.path.join(tmp, RAIZ_FEIA)
    pasta = os.path.join(raiz, ".claude", "plans")
    os.makedirs(pasta)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        ps._gate_precheck(pasta, plano_minimo())
    m = re.search(r"Para ganhar o portão: (.*)", err.getvalue())
    check("o aviso de relatório ausente traz o comando de renovar", bool(m), err.getvalue())
    if m:
        argv = palavras(m.group(1)) or []
        check("o comando de renovar tem 6 palavras: programa, plano, --raiz, raiz, --relatorio",
              len(argv) == 6, repr(argv))
        if len(argv) == 6:
            check("o plano chega inteiro, como UMA palavra",
                  argv[2] == os.path.join(pasta, "2026-01-01-teste.plan.json"), repr(argv))
            check("a raiz chega inteira, como UMA palavra", argv[4] == raiz, repr(argv))

    # ── hsf_d8f1134d · o cartão de fechamento da frente (HTML) ─────────────────────
    print("hsf_d8f1134d — `git worktree remove` e `git branch -d` no cartão da frente")
    w = "/tmp/wt dir/o'brien; touch PWNED-wt $(touch PWNED-sub2)"
    b = "feature/x'; touch PWNED-br #"
    pagina = ps.render_html(plano_minimo(frente={"branch": b, "worktree": w}), "track")
    m1 = re.search(r"<code>git worktree remove (.*?)</code>", pagina)
    m2 = re.search(r"<code>git branch -d (.*?)</code>", pagina)
    check("o cartão traz os dois comandos de limpeza", bool(m1 and m2))
    if m1 and m2:
        check("`git worktree remove` recebe o worktree como UMA palavra de shell",
              palavras(html.unescape(m1.group(1))) == [w], html.unescape(m1.group(1)))
        check("`git branch -d` recebe a branch como UMA palavra de shell",
              palavras(html.unescape(m2.group(1))) == [b], html.unescape(m2.group(1)))
    check("e o HTML continua escapado (nada de `<` ou aspas soltas na página)",
          "<script" not in pagina and "&#x27;" in pagina)

    # ── hsf_a43c635d · o nome do HTML do /start ────────────────────────────────────
    print("hsf_a43c635d — a régua de nome do diagrama-blueprint.sh")
    BASH = bash_posix.bash_posix() or "bash"
    fora = os.path.join(tmp, "fora")
    os.makedirs(fora)
    entrada = os.path.join(tmp, "e.json")
    with open(entrada, "w") as fh:
        fh.write("{}")

    def roda(nome):
        return subprocess.run([BASH, BLUEPRINT, tmp, "workflow", entrada, nome],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", stdin=subprocess.DEVNULL, cwd=tmp)

    for ruim in ("fluxo-x/../../fora/y.html", "fluxo-/etc/passwd.html", "fluxo-..html",
                 "fluxo-a\\b.html", "fluxo-x/y.html", "fluxo-a b.html", "fluxo-$(id).html",
                 "fluxo-a;b.html", "fluxo-\n.html"):
        r = roda(ruim)
        check("recusa (rc=2) o nome %r" % ruim, r.returncode == 2,
              "rc=%d out=%r err=%r" % (r.returncode, r.stdout[:80], r.stderr[:120]))
    for bom in ("organismo.html", "fluxo-pagamento.html", "fluxo-login-2fa.html"):
        r = roda(bom)
        check("não recusa o nome %r (passa da régua; rc!=2)" % bom, r.returncode != 2,
              "rc=%d err=%r" % (r.returncode, r.stderr[:120]))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILS:
    print("FALHOU: %d" % len(FAILS))
    sys.exit(1)
print("OK")
