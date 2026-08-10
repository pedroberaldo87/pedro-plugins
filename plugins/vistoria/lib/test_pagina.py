#!/usr/bin/env python3
"""Suíte da página de achados da vistoria.

O teste que carrega o passo é a contagem: a página tem que trazer UM checkbox
por achado do JSON. Página com achado a menos é decisão tomada sem o item na
frente — o defeito que ninguém percebe olhando a tela.

    python3 plugins/vistoria/lib/test_pagina.py

stdlib only (requisito do repo).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import pagina  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def um(cobrador, o_que, prova, onde="a/b.sh:1", regra="R1"):
    return {"cobrador": cobrador, "regra": regra, "gravidade": "alta",
            "onde": onde, "o_que": o_que, "prova": prova}


AMOSTRA = [
    um("hook-contract", "bloqueia e não tem teto de devoluções", "exit 2"),
    um("hook-contract", "usa jq sem guarda de ausência", "| jq -r"),
    um("desacoplamento", "afirmação acoplada ao código: 21 skills", "- **21 skills**"),
]


def conta_checkbox(texto):
    return len(re.findall(r"<input[^>]+type=\"checkbox\"", texto))


def main():
    print("test_pagina")

    # O destino é sempre um tempdir do teste: a página da rodada real do projeto não
    # pode ser sobrescrita por suíte rodando.
    tmp = tempfile.mkdtemp(prefix="vistoria-pagina-")

    # --- o caminho de verdade: JSON pelo stdin, caminho no stdout -----------------
    saida = subprocess.run([sys.executable, os.path.join(AQUI, "pagina.py"),
                            "--dir", tmp],
                           input=json.dumps(AMOSTRA), cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
    caminho = saida.stdout.strip()
    checa("o comando sai 0", saida.returncode == 0, saida.stderr[-300:])
    checa("imprime o caminho do HTML dentro do --dir pedido",
          caminho.startswith(tmp + os.sep) and caminho.endswith(".html"), repr(caminho))
    checa("o arquivo existe no disco", os.path.isfile(caminho), repr(caminho))

    texto = open(caminho, encoding="utf-8").read() if os.path.isfile(caminho) else ""
    checa("um checkbox por achado do JSON",
          conta_checkbox(texto) == len(AMOSTRA),
          "página=%d json=%d" % (conta_checkbox(texto), len(AMOSTRA)))

    # --- a prova está EMBUTIDA, não descrita --------------------------------------
    checa("a prova de cada achado está colada na página",
          all(a["prova"].replace("&", "&amp;") in texto for a in AMOSTRA),
          "faltou: %r" % [a["prova"] for a in AMOSTRA if a["prova"] not in texto])

    # --- e nasce fechada: nenhum <pre> fora de <details>, nenhum details aberto ----
    checa("a prova nasce dentro de <details> fechado",
          texto.count("<details><summary>") == 2 * len(AMOSTRA)
          and "<details open" not in texto
          and len(re.findall(r"<details><summary>[^<]*</summary><pre>", texto)) == len(AMOSTRA),
          "details=%d pre-em-details=%d"
          % (texto.count("<details><summary>"),
             len(re.findall(r"<details><summary>[^<]*</summary><pre>", texto))))

    # --- agrupada por lente -------------------------------------------------------
    checa("uma seção por lente, com a contagem da lente",
          "hook-contract — 2 achado(s)" in texto and "desacoplamento — 1 achado(s)" in texto)

    # --- a régua da forma ---------------------------------------------------------
    lentes = pagina.por_lente(AMOSTRA)
    checa("o texto autoral da página passa na régua compartilhada",
          pagina.erros_da_pagina(lentes) == [], repr(pagina.erros_da_pagina(lentes)))

    # --- achado com marcação não vira HTML ----------------------------------------
    veneno = [um("x", "tag no texto", "<script>alerta()</script>")]
    p2 = pagina.escreve(veneno, os.path.join(tmp, "veneno"))
    t2 = open(p2, encoding="utf-8").read()
    checa("prova com tag é escapada, não injetada",
          "<script>alerta()" not in t2 and "&lt;script&gt;alerta()" in t2)
    checa("o caso de um achado só ainda tem um checkbox", conta_checkbox(t2) == 1,
          str(conta_checkbox(t2)))

    # --- duas rodadas no mesmo dia deixam DOIS arquivos ---------------------------
    # A página do piloto foi sobrescrita pela vistoria seguinte porque o nome só
    # tinha a data. Duas escritas seguidas têm que sobreviver as duas.
    doisdir = os.path.join(tmp, "duas")
    p_a = pagina.escreve(AMOSTRA, doisdir)
    p_b = pagina.escreve(AMOSTRA, doisdir)
    checa("duas escritas seguidas deixam dois arquivos",
          p_a != p_b and os.path.isfile(p_a) and os.path.isfile(p_b)
          and len(os.listdir(doisdir)) == 2, "%r %r" % (p_a, p_b))
    p_c = pagina.escreve(AMOSTRA, doisdir, "piloto-leitor")
    checa("a rodada nomeada aparece no nome do arquivo",
          os.path.basename(p_c).endswith("-piloto-leitor.html"), os.path.basename(p_c))

    # --- o descarte aparece no rodapé --------------------------------------------
    # `_descartes` era lido por ninguém: o que o cobrador não conseguiu provar sumia
    # da página, e o lote encolhia sem que o dono soubesse.
    dsc = [{"o_que": "afirmação sem par de citações", "motivo": "prova sem arquivo:linha"}]
    saida3 = subprocess.run([sys.executable, os.path.join(AQUI, "pagina.py"),
                             "--dir", os.path.join(tmp, "dsc")],
                            input=json.dumps({"achados": AMOSTRA, "_descartes": dsc}),
                            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                            start_new_session=True)
    t3 = open(saida3.stdout.strip(), encoding="utf-8").read() if saida3.returncode == 0 else ""
    checa("o descarte do JSON sai listado no rodapé da página",
          "descartado por falta de prova — 1 achado(s)" in t3
          and "prova sem arquivo:linha" in t3, saida3.stderr[-300:])
    checa("sem descarte, nenhum rodapé de descarte na página",
          "descartado por falta de prova" not in texto)

    shutil.rmtree(tmp, ignore_errors=True)

    print("\n%s" % ("FALHOU: " + ", ".join(falhas) if falhas else "tudo verde"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
