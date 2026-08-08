#!/usr/bin/env python3
"""Suíte da pauta do leitor — a forma da pergunta é cobrada por programa.

Três coisas carregam o passo, e nenhuma delas é opinião:

  1. toda pergunta exige prova colada — o marcador 'cole a linha' ou 'cole as duas';
  2. nenhuma pergunta usa verbo aberto (avalie, considere, analise…) — verbo aberto
     devolve ensaio, e ensaio não vira achado;
  3. as letras a, b, d e e do gabarito têm cada uma ao menos uma pergunta mapeada.

Mais o congelamento: as fixtures a, b, d e f existem no disco com o defeito dentro.

    python3 plugins/vistoria/lib/test_pauta.py

stdlib only (requisito do repo).
"""

import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
PAUTA = os.path.join(PLUGIN, "skills", "vistoria", "references", "pauta-leitor.md")
FIXTURES = os.path.join(PLUGIN, "fixtures")

MARCADORES = ("cole a linha", "cole as duas")
VERBOS_ABERTOS = ("avalie", "avaliar", "considere", "considerar",
                  "analise", "analisar", "reflita", "julgue", "opine")
LETRAS_EXIGIDAS = ("a", "b", "d", "e")
FIXTURES_EXIGIDAS = ("a", "b", "d", "f")

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def perguntas(texto):
    """Os blocos de pergunta da pauta: (rótulo, letra, corpo em texto plano)."""
    blocos = []
    atual = None
    for linha in texto.splitlines():
        cab = re.match(r"^### (P\d+) · \[([a-i])\] (.*)$", linha)
        if cab:
            atual = [cab.group(1), cab.group(2), cab.group(3) + "\n"]
            blocos.append(atual)
        elif linha.startswith("### ") or linha.startswith("## "):
            atual = None
        elif atual is not None:
            atual[2] += linha + "\n"
    return [(r, letra, corpo.replace("*", "").replace("`", "").lower())
            for r, letra, corpo in blocos]


def main():
    print("Pauta do leitor")
    if not os.path.exists(PAUTA):
        checa("a pauta existe", False, PAUTA)
        return 1
    texto = open(PAUTA, encoding="utf-8").read()
    blocos = perguntas(texto)
    checa("a pauta tem pergunta", len(blocos) > 0, "nenhum bloco '### P<n> · [letra]'")

    sem_prova = [r for r, _l, corpo in blocos
                 if not any(m in corpo for m in MARCADORES)]
    checa("toda pergunta exige prova colada", not sem_prova,
          "sem marcador %s: %s" % (list(MARCADORES), sem_prova))

    abertos = [(r, v) for r, _l, corpo in blocos for v in VERBOS_ABERTOS
               if re.search(r"\b%s\b" % v, corpo)]
    checa("nenhuma pergunta usa verbo aberto", not abertos, str(abertos))

    letras = {letra for _r, letra, _c in blocos}
    faltando = [x for x in LETRAS_EXIGIDAS if x not in letras]
    checa("as letras a, b, d e e do gabarito têm pergunta", not faltando,
          "sem pergunta: %s" % faltando)

    # O detector morde: uma pergunta plantada com verbo aberto e sem prova reprova.
    planta = perguntas("### P99 · [a] Avalie a coerência\nConsidere o arquivo inteiro.\n")
    _r, _l, corpo = planta[0]
    mordeu = (not any(m in corpo for m in MARCADORES)
              and any(re.search(r"\b%s\b" % v, corpo) for v in VERBOS_ABERTOS))
    checa("o detector morde a pergunta plantada", mordeu, corpo)

    faltam = [x for x in FIXTURES_EXIGIDAS
              if not (os.path.isdir(os.path.join(FIXTURES, x))
                      and os.listdir(os.path.join(FIXTURES, x)))]
    checa("as fixtures a, b, d e f estão congeladas no disco", not faltam,
          "vazias ou ausentes: %s" % faltam)

    print("\n%s (%d falha(s))" % ("VERDE" if not falhas else "VERMELHO", len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
