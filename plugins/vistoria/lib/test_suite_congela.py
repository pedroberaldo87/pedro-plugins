#!/usr/bin/env python3
"""Suíte da lente `suite_congela`.

O que ela carrega: a fixture (e) tem que ser ACHADA — o assert que espera uma frase
que o programa ao lado não escreve —, o assert que espera uma frase que o programa
ESCREVE não pode virar achado, e o retrato tem que calar o que já foi visto (segunda
rodada com zero achado novo).

    python3 plugins/vistoria/lib/test_suite_congela.py

stdlib only (requisito do repo).
"""

import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import suite_congela  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(AQUI), "fixtures", "e")

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def roda(*args):
    return subprocess.run([sys.executable, os.path.join(AQUI, "suite_congela.py")] + list(args),
                          capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          start_new_session=True)


def main():
    # --- a fixture (e) --------------------------------------------------------------
    p = roda("--root", FIXTURE, "--todos", "--json")
    d = json.loads(p.stdout)
    achados = d["todos"]
    checa("a fixture (e) devolve exatamente 1 assert órfão", len(achados) == 1,
          repr([a["arquivo"] for a in achados]))
    checa("o achado aponta a suíte congelada da fixture",
          bool(achados) and achados[0]["arquivo"].endswith("_test.py"),
          repr(achados[:1]))
    checa("o achado carrega a linha do assert como prova",
          bool(achados) and achados[0]["trecho"].startswith("assert "),
          repr(achados[0]["trecho"]) if achados else "sem achado")
    checa("o assert que espera a frase que o programa ESCREVE não vira achado",
          all("recusado:" not in a["alvo"] for a in achados),
          repr([a["alvo"] for a in achados]))
    checa("sai 1 quando acha", p.returncode == 1, "returncode=%d" % p.returncode)

    # --- o filtro de literal ---------------------------------------------------------
    checa("literal curto não interessa", not suite_congela.interessa("ok"))
    checa("gabarito de formato não interessa",
          not suite_congela.interessa("%s achados de %d"))
    checa("frase de verdade interessa",
          suite_congela.interessa("bloqueado: o arquivo violou a norma"))

    # --- o retrato cala a segunda rodada ---------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = os.path.join(tmp, "e")
        subprocess.run(["cp", "-R", FIXTURE, raiz], check=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
        g = roda("--root", raiz, "--gravar-retrato")
        checa("grava o retrato", g.returncode == 0 and "retrato gravado" in g.stdout,
              g.stdout.strip())
        segunda = roda("--root", raiz)
        checa("a segunda rodada termina com zero achado novo",
              segunda.returncode == 0 and "NOVO além do retrato" in segunda.stdout,
              segunda.stdout.strip())

    print("\n%s" % ("FALHOU: " + ", ".join(falhas) if falhas else "tudo verde"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
