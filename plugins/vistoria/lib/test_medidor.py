#!/usr/bin/env python3
"""Suíte do medidor da vistoria.

Dois testes carregam o passo: a contagem por cobrador tem que bater com a saída
individual do script correspondente (o medidor não pode inventar nem perder
achado no caminho), e achado sem prova tem que ser RECUSADO pelo validador — não
aceito como achado fraco.

    python3 plugins/vistoria/lib/test_medidor.py

Roda os 9 cobradores de verdade, duas vezes cada (o medidor e o script sozinho),
então leva minutos. stdlib only (requisito do repo).
"""

import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from achado import AchadoInvalido, achado, erros_de_achado, valida  # noqa: E402
import medidor  # noqa: E402

ROOT = medidor.ROOT

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def roda_json(*args):
    saida = subprocess.run([sys.executable, os.path.join(ROOT, args[0])] + list(args[1:]),
                           cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    return json.loads(saida.stdout)


def contagens_individuais():
    """Quantos achados CADA script sozinho reporta — a referência da comparação."""
    orfas = medidor._importa("scripts/suites_orfas.py", "suites_orfas_ref")
    fora, _t, _p = orfas.orfas(ROOT)
    regua = medidor._importa("plugins/visual/lib/regua_pronto.py", "regua_pronto_ref")
    n_regua = sum(len(regua.erros_de_pronto(p, pid))
                  for _n, pid, p in medidor._passos_abertos())
    return {
        "hook-contract": len(roda_json("scripts/hook_contract.py", "--json")["findings"]),
        "desacoplamento": len(roda_json("scripts/desacoplamento_check.py",
                                        "--json", "--todos")["todos"]),
        "public-repo": len(roda_json("scripts/public_repo_check.py", "--json")["findings"]),
        "regua-call": len(roda_json("scripts/regua_call_check.py", "--json")["findings"]),
        "readme-counts": len(roda_json("scripts/readme_counts_check.py", "--json")["achados"]),
        "suites-orfas": len(fora or []),
        "plano-vs-codigo": len([a for a in roda_json("scripts/plano_vs_codigo.py", "--json")
                                if a["veredito"] == "divergente"]),
        "regua-pronto": n_regua,
        "conformance": len(roda_json("plugins/bootstrap/lib/conformance.py",
                                     "--json")["desvios"]),
    }


def main():
    print("test_medidor")

    # --- o validador: prova é porta, não enfeite ---------------------------------
    try:
        achado(cobrador="x", regra="r", onde="a.py:1", o_que="algo", prova="")
        checa("achado sem prova é recusado", False, "o construtor aceitou prova vazia")
    except AchadoInvalido as e:
        checa("achado sem prova é recusado", "prova" in str(e), str(e))

    sem_campo = {"cobrador": "x", "regra": "r", "gravidade": "media",
                 "onde": "a.py:1", "o_que": "algo"}
    checa("achado sem o CAMPO prova é recusado",
          erros_de_achado(sem_campo) == ["campo ausente: prova"],
          repr(erros_de_achado(sem_campo)))
    try:
        valida(sem_campo)
        checa("valida() levanta em achado sem prova", False, "passou")
    except AchadoInvalido:
        checa("valida() levanta em achado sem prova", True)

    checa("achado com prova passa",
          erros_de_achado(achado(cobrador="x", regra="r", onde="a.py:1",
                                 o_que="algo", prova="exit 2")) == [])

    # --- a medição ----------------------------------------------------------------
    achados, falhas_cob = medidor.mede()
    checa("nenhum cobrador ficou sem medir", not falhas_cob, repr(falhas_cob))
    checa("a medição devolve N>0 achados", len(achados) > 0, str(len(achados)))
    ruins = [a for a in achados if erros_de_achado(a)]
    checa("todo achado sai válido", not ruins, repr(ruins[:2]))

    por_cobrador = {nome: 0 for nome, _fn in medidor.COBRADORES}
    for a in achados:
        por_cobrador[a["cobrador"]] += 1

    ref = contagens_individuais()
    for nome in ref:
        checa("contagem de %s bate com o script sozinho" % nome,
              por_cobrador[nome] == ref[nome],
              "medidor=%d script=%d" % (por_cobrador[nome], ref[nome]))

    # --- a saída de linha de comando ---------------------------------------------
    saida = subprocess.run([sys.executable, os.path.join(AQUI, "medidor.py"),
                            "suites-orfas", "hook-contract", "--json"],
                           cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    d = json.loads(saida.stdout)
    checa("--json com filtro devolve só os cobradores pedidos",
          {a["cobrador"] for a in d} <= {"suites-orfas", "hook-contract"},
          repr({a["cobrador"] for a in d}))

    print("\n%s" % ("FALHOU: " + ", ".join(falhas) if falhas else "tudo verde"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
