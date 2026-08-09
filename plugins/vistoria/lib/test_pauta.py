#!/usr/bin/env python3
"""Suíte da pauta do leitor — a forma da pergunta é cobrada por programa.

Três coisas carregam o passo, e nenhuma delas é opinião:

  1. toda pergunta exige prova colada — o marcador 'cole a linha' ou 'cole as duas';
  2. nenhuma pergunta usa verbo aberto (avalie, considere, analise…) — verbo aberto
     devolve ensaio, e ensaio não vira achado;
  3. as letras a, b, d e e do gabarito têm cada uma ao menos uma pergunta mapeada.

Mais o congelamento: as fixtures a, b, d e f existem no disco com o defeito dentro.

E o TETO da lente cruzada: ela consome as FICHAS, nunca os textos. O teto por pedaço é
300 palavras (pauta-leitor.md), a soma tem o teto TETO_SOMA, e a rodada na fixture f
produz o achado cruzado com as duas linhas do evento Stop coladas.

    python3 plugins/vistoria/lib/test_pauta.py

stdlib only (requisito do repo).
"""

import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from achado import achado, erros_de_achado  # noqa: E402
from test_verificador import verifica  # noqa: E402

PLUGIN = os.path.dirname(AQUI)
REFS = os.path.join(PLUGIN, "skills", "vistoria", "references")
PAUTA = os.path.join(REFS, "pauta-leitor.md")
PAUTA_CRUZADA = os.path.join(REFS, "pauta-cruzamento.md")
FIXTURES = os.path.join(PLUGIN, "fixtures")
PLUGINS = os.path.dirname(PLUGIN)

# O teto por pedaço vem da pauta do leitor; a soma é ele vezes o número de pedaços
# (um pedaço = um plugin do marketplace). É este número que a lente cruzada carrega
# na cabeça em vez dos textos inteiros — a comparação com o wc -w dos textos reais
# é o próprio ganho do passo, e está checada abaixo.
#
# TROCA DE NÚMERO, REGISTRADA ONDE SE MEDE: o critério de pronto original pedia a soma
# das fichas REAIS (~4-6 mil palavras projetadas) contra as 77.767 palavras dos textos
# de instrução. Ficha de plugin real não existe: o leitor por agente está congelado por
# decisão do dono, então o que a soma mede hoje são as DUAS fichas de fixture coladas em
# pauta-cruzamento.md (soma ~126 palavras). O contraste com os textos virou o proxy
# `TETO_SOMA * 10 <= textos`, que compara o TETO declarado — não a soma real. Descongelar
# o leitor por agente e gerar fichas de plugin real reabre a medição original.
TETO_FICHA = 300
TETO_SOMA = TETO_FICHA * len([d for d in os.listdir(PLUGINS)
                              if os.path.isdir(os.path.join(PLUGINS, d))])

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
        cab = re.match(r"^### ([PX]\d+) · \[([a-i])\] (.*)$", linha)
        if cab:
            atual = [cab.group(1), cab.group(2), cab.group(3) + "\n"]
            blocos.append(atual)
        elif linha.startswith("### ") or linha.startswith("## "):
            atual = None
        elif atual is not None:
            atual[2] += linha + "\n"
    return [(r, letra, corpo.replace("*", "").replace("`", "").lower())
            for r, letra, corpo in blocos]


def fichas_da_pauta(caminho):
    """As fichas congeladas coladas na pauta cruzada — os blocos ```json com `pedaco`."""
    texto = open(caminho, encoding="utf-8").read()
    achadas = []
    for bruto in re.findall(r"```json\n(.*?)```", texto, re.S):
        dados = json.loads(bruto)
        if "pedaco" in dados:
            achadas.append((dados, len(bruto.split())))
    return achadas


def linhas_com(raiz, arquivos, objeto):
    """As citações 'arquivo:linha: trecho' onde o objeto aparece — a prova colada.

    A lente cruzada só abre os arquivos que a FICHA aponta, e só quando a resposta é SIM.
    """
    citacoes = []
    for ref in dict.fromkeys(arquivos):  # as duas fichas citam o mesmo arquivo de ordem
        arquivo = ref.split(":")[0]
        caminho = os.path.join(raiz, arquivo)
        if not os.path.exists(caminho):
            continue
        for n, linha in enumerate(open(caminho, encoding="utf-8").read().splitlines(), 1):
            if objeto in linha:
                citacoes.append("%s:%d: %s" % (arquivo, n, linha.strip()))
    return citacoes


def cruza(fa, fb, raiz):
    """A lente cruzada rodando sobre duas FICHAS: o achado de X1/X2, ou None.

    Consome `manda`, `proibe`, `objetos` e `eventos` — nunca o texto dos pedaços. A
    correspondência evento → pedaços sai do campo `eventos`; conferi-la contra o disco é
    trabalho de `lib/inventario.py`, não desta função.
    """
    for objeto in fa["objetos"]:
        if objeto not in fb["objetos"]:
            continue
        manda = [o for o in fa["manda"] if objeto in o]
        proibe = [o for o in fb["proibe"] if objeto in o]
        if not (manda and proibe):
            continue
        eventos = sorted(set(fa["eventos"]) & set(fb["eventos"]))
        prova = linhas_com(raiz, fa["arquivos"] + fb["arquivos"], objeto)
        return achado(
            cobrador="cruzamento",
            regra="X1-ordem-oposta-no-mesmo-objeto",
            gravidade="alta",
            onde=prova[0],
            o_que=("%s manda %r e %s proíbe %r sobre %s%s"
                   % (fa["pedaco"], manda[0], fb["pedaco"], proibe[0], objeto,
                      "; os dois registram em %s" % ", ".join(eventos) if eventos else "")),
            prova="\n".join(prova),
        )
    return None


def cruzamento(cheques):
    """A rodada da lente cruzada na fixture f, com a suíte cobrando o resultado."""
    print("\nLente cruzada — fixture f")
    fichas = fichas_da_pauta(PAUTA_CRUZADA)
    cheques("a pauta cruzada cola as duas fichas da fixture f", len(fichas) == 2,
            "fichas encontradas: %d" % len(fichas))
    if len(fichas) != 2:
        return

    # O teto: a soma das fichas reais, medida como wc -w, fica abaixo do teto declarado.
    gordas = [f["pedaco"] for f, palavras in fichas if palavras > TETO_FICHA]
    cheques("nenhuma ficha passa do teto de %d palavras" % TETO_FICHA, not gordas,
            str(gordas))
    soma = sum(palavras for _f, palavras in fichas)
    # A soma medida é a das fichas de FIXTURE, não a das fichas de plugin real que o
    # critério de pronto pedia — o leitor por agente está congelado (ver o bloco do teto).
    cheques("a soma das fichas de fixture fica abaixo do teto de %d" % TETO_SOMA,
            soma <= TETO_SOMA,
            "soma %d (fichas de fixture; ficha real depende do leitor por agente)" % soma)

    # O ganho: o teto da soma é ordens de grandeza menor que os textos que a lente NÃO lê.
    textos = 0
    for raiz, _dirs, arquivos in os.walk(PLUGINS):
        for nome in arquivos:
            if nome == "SKILL.md":
                textos += len(open(os.path.join(raiz, nome),
                                   encoding="utf-8").read().split())
    cheques("o teto da soma cabe em 1/10 das palavras dos textos de instrução",
            TETO_SOMA * 10 <= textos, "teto %d contra %d palavras" % (TETO_SOMA, textos))

    a = cruza(fichas[0][0], fichas[1][0], PLUGIN)
    cheques("a lente cruzada devolve achado na fixture f", a is not None, "None")
    if a is None:
        return
    cheques("o achado passa pelo validador de lib/achado.py",
            not erros_de_achado(a), str(erros_de_achado(a)))

    stop = [c for c in a["prova"].splitlines() if "ordem-de-registro.json" in c]
    cheques("a prova cola as duas linhas do evento Stop", len(stop) == 2, str(stop))
    cheques("a prova cola a instrução dos dois pedaços",
            any("skill-um.md" in c for c in a["prova"].splitlines())
            and any("skill-dois.md" in c for c in a["prova"].splitlines()), a["prova"])

    veredito, motivo = verifica(a, PLUGIN)
    cheques("o achado cruzado sai rotulado pelo verificador",
            veredito == "CONFIRMADO", "%s — %s" % (veredito, motivo))


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

    print("\nPauta da lente cruzada")
    if not os.path.exists(PAUTA_CRUZADA):
        checa("a pauta cruzada existe", False, PAUTA_CRUZADA)
    else:
        cruzados = perguntas(open(PAUTA_CRUZADA, encoding="utf-8").read())
        checa("a pauta cruzada tem pergunta", len(cruzados) > 0,
              "nenhum bloco '### X<n> · [letra]'")
        sem_prova = [r for r, _l, corpo in cruzados
                     if not any(m in corpo for m in MARCADORES)]
        checa("toda pergunta cruzada exige o par de citações", not sem_prova,
              "sem marcador %s: %s" % (list(MARCADORES), sem_prova))
        abertos = [(r, v) for r, _l, corpo in cruzados for v in VERBOS_ABERTOS
                   if re.search(r"\b%s\b" % v, corpo)]
        checa("nenhuma pergunta cruzada usa verbo aberto", not abertos, str(abertos))
        cruzamento(checa)

    print("\n%s (%d falha(s))" % ("VERDE" if not falhas else "VERMELHO", len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
