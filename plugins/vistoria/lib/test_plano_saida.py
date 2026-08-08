#!/usr/bin/env python3
"""Suíte do gerador do plano da vistoria.

Três coisas carregam o passo, e as três são checadas aqui contra os programas de
verdade (nada de dublê): o `plan_state` DESENHA os dois passos e ACEITA o critério
de cada um, o `plano_vs_codigo` LÊ o arquivo sem erro, e — com o `plan_state` fora
do alcance — o JSON continua saindo válido, com o aviso de degradação impresso.

    python3 plugins/vistoria/lib/test_plano_saida.py

stdlib only (requisito do repo).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import plano_saida  # noqa: E402

ROOT = plano_saida.ROOT
DATA = "2026-01-02"

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def um(cobrador, regra, onde, o_que, prova):
    return {"cobrador": cobrador, "regra": regra, "gravidade": "alta",
            "onde": onde, "o_que": o_que, "prova": prova}


AMOSTRA = [
    um("hook-contract", "R1-cap-ausente", "plugins/alfa/hooks/x.sh:12",
       "bloqueia e não tem teto de devoluções", "exit 2"),
    um("desacoplamento", "citacao-executavel", "plugins/beta/skills/beta/SKILL.md:40",
       "cita o programa de outro plugin", "python3 plugins/alfa/lib/y.py"),
]


def roda(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, start_new_session=True, **kw)


def gera(destino):
    return subprocess.run(
        [sys.executable, os.path.join(AQUI, "plano_saida.py"),
         "--dir", destino, "--data", DATA],
        input=json.dumps(AMOSTRA), cwd=ROOT, capture_output=True, text=True,
        start_new_session=True)


def main():
    print("test_plano_saida")
    tmp = tempfile.mkdtemp(prefix="vistoria-plano-")
    try:
        # --- o caminho de verdade: achados pelo stdin, caminho no stdout ------------
        saida = gera(tmp)
        caminho = saida.stdout.strip()
        checa("o comando sai 0", saida.returncode == 0, saida.stderr[-400:])
        checa("grava vistoria-<data>.plan.json",
              caminho == os.path.join(tmp, "vistoria-%s.plan.json" % DATA), repr(caminho))
        checa("com o visual na máquina não há aviso de degradação",
              "aviso:" not in saida.stderr, repr(saida.stderr[-200:]))

        plano = json.load(open(caminho, encoding="utf-8")) if os.path.isfile(caminho) else {}
        itens = [it for ph in plano.get("phases", []) for it in ph["items"]]
        checa("um passo por achado marcado", len(itens) == len(AMOSTRA), str(len(itens)))
        checa("id fixo por passo, na ordem em que foram marcados",
              [it["id"] for it in itens] == ["F1.1", "F1.2"],
              repr([it.get("id") for it in itens]))
        checa("todo passo tem critério de pronto",
              all(str(it.get("pronto") or "").strip() for it in itens))

        # --- o plan_state DESENHA os dois passos com o critério ---------------------
        r = roda([sys.executable, os.path.join(ROOT, "plugins/project-skills/lib/plan_state.py"),  # acopla-ok: o critério do passo manda rodar ESTE programa, e dublê não provaria a árvore
                  "--dir", tmp, "render", "--format", "text",
                  "vistoria-%s" % DATA])
        checa("plan_state render sai 0", r.returncode == 0, r.stderr[-400:])
        checa("a árvore traz os dois passos",
              "F1.1" in r.stdout and "F1.2" in r.stdout, r.stdout[-300:])
        # O `pronto` NÃO é desenhado na árvore — `plan_state._detalhe` só mostra
        # prova, pendência, espera do dono ou a linha didática. Quem julga o critério
        # é o schema do mesmo módulo, e é ele que este bloco cobra: o plano volta
        # pelo leitor do plan_state com o critério inteiro e sem erro de forma.
        lido_ps = roda([sys.executable, "-c", (
            "import sys,json;sys.path.insert(0,'plugins/project-skills/lib');"  # acopla-ok: o julgamento do critério é do schema do plan_state, lido no original
            "import plan_state as p;"
            "pl=p.pick_plan(%r,'vistoria-%s');"
            "print(json.dumps({'errs':p.erros_do_plano(pl),"
            "'prontos':[i['pronto'] for _,i in p.iter_items(pl)]}))" % (tmp, DATA))])
        volta = json.loads(lido_ps.stdout) if lido_ps.returncode == 0 else {}
        checa("o plan_state aceita o critério de cada passo",
              volta.get("errs") == [], repr(volta.get("errs", lido_ps.stderr[-300:])))
        checa("o critério de cada passo volta inteiro pelo leitor do plan_state",
              volta.get("prontos") == [it["pronto"] for it in itens],
              repr(volta.get("prontos")))

        # --- o plano_vs_codigo LÊ o plano sem erro ---------------------------------
        r2 = roda([sys.executable, os.path.join(ROOT, "scripts/plano_vs_codigo.py"),
                   tmp, "--json"])
        checa("plano_vs_codigo lê o plano sem erro", r2.returncode in (0, 1),
              "rc=%s %s" % (r2.returncode, r2.stderr[-400:]))
        try:
            lido = json.loads(r2.stdout)
        except ValueError:
            lido = None
        checa("plano_vs_codigo devolve JSON com os passos",
              isinstance(lido, (dict, list)), repr(r2.stdout[-200:]))

        # --- DEGRADAÇÃO: sem o plan_state na máquina, o JSON sai e o aviso sai -----
        escondido = plano_saida.PLAN_STATE + ".ausente-no-teste"
        os.rename(plano_saida.PLAN_STATE, escondido)
        try:
            tmp2 = tempfile.mkdtemp(prefix="vistoria-plano-degradado-")
            deg = gera(tmp2)
            c2 = deg.stdout.strip()
            checa("sem o visual, a geração ainda sai 0", deg.returncode == 0,
                  deg.stderr[-400:])
            checa("sem o visual, o JSON sai válido",
                  os.path.isfile(c2) and json.load(open(c2, encoding="utf-8"))["id"]
                  == "vistoria-%s" % DATA, repr(c2))
            checa("sem o visual, o aviso de degradação é impresso",
                  "aviso:" in deg.stderr and "plan_state" in deg.stderr,
                  repr(deg.stderr[-200:]))
            shutil.rmtree(tmp2, ignore_errors=True)
        finally:
            os.rename(escondido, plano_saida.PLAN_STATE)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%s" % ("FALHOU: " + ", ".join(falhas) if falhas else "tudo verde"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
