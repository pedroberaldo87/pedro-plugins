#!/usr/bin/env python3
"""Suíte da lente `fio_morto`.

O que ela carrega: a fixture (c) tem que ser ACHADA — o script de hook que nenhum
`hooks.json` registra —, o hook que ESTÁ registrado não pode virar achado, suíte de
hook não conta como fio morto (quem a chama é o globo da esteira, que não cita nome),
e o retrato tem que calar o que já foi visto.

    python3 plugins/vistoria/lib/test_fio_morto.py

stdlib only (requisito do repo).
"""

import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import fio_morto  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(AQUI), "fixtures", "c")

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def roda(*args):
    return subprocess.run([sys.executable, os.path.join(AQUI, "fio_morto.py")] + list(args),
                          capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          start_new_session=True)


def main():
    # --- a fixture (c) --------------------------------------------------------------
    p = roda("--root", FIXTURE, "--todos", "--json")
    achados = json.loads(p.stdout)["todos"]
    checa("a fixture (c) devolve exatamente 1 hook sem chamador", len(achados) == 1,
          repr([a["arquivo"] for a in achados]))
    checa("o achado é o script que nenhum hooks.json registra",
          bool(achados) and achados[0]["alvo"].endswith(".sh")
          and "registrado" not in achados[0]["alvo"],
          repr(achados[:1]))
    checa("o achado carrega a medição como prova",
          bool(achados) and "0 menção" in achados[0]["trecho"],
          repr(achados[0]["trecho"]) if achados else "sem achado")
    checa("sai 1 quando acha", p.returncode == 1, "returncode=%d" % p.returncode)

    # --- quem NÃO é fio morto --------------------------------------------------------
    checa("script fora de hooks/ não é candidato",
          not fio_morto.eh_hook(os.path.join("lib", "solto.sh")))
    checa("suíte de hook não é candidata",
          not fio_morto.eh_hook(os.path.join("hooks", "test_guarda.sh")))
    checa("script dentro de hooks/ é candidato",
          fio_morto.eh_hook(os.path.join("hooks", "guarda.sh")))

    # --- o retrato cala a segunda rodada ---------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        raiz = os.path.join(tmp, "c")
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
