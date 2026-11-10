#!/usr/bin/env python3
"""test_revisao_fecha_por_problema.py — o cobrador do Artigo 14 da constituição.

ARTIGO 14: a assíntota da revisão é de SEVERIDADE, nunca de gasto. O laço fecha quando
uma rodada COMPLETA não produz achado acima do piso de severidade, confirmada por um
re-sweep independente — e por nenhum outro motivo.

O ARTIGO TEM DOIS LADOS, E ESTE COBRADOR MEDE OS DOIS:

  · a assíntota FICA. "Zero achados" é otimista e falso — parte do que um revisor chama
    de erro é preciosismo que não afeta consistência nem funcionamento, e exigir zero
    obriga quem quer fechar a REBAIXAR achado, corrompendo o instrumento que separa
    defeito de opinião.
  · o GASTO sai. Rodada, token, tempo e dinheiro nunca fecham revisão.

POR QUE ESTE ARQUIVO EXISTE (2026-08-23). O desenho anterior da /qa-loop misturava as
duas leituras erradas: definia o fecho como "para quando não vale mais a pena" (cansaço)
e ancorava a parada em "retornos decrescentes" (taxa de descoberta). Nenhum dos dois é o
critério — o critério é severidade. E havia teto declarado dentro de projeto: um
`max_rounds: 6` viajava em dois `qa-loop.config.md` sem ninguém ter decidido.

O QUE ESTE ARQUIVO COBRA, nos arquivos declarados em ALVOS:

  A · fecho por GASTO (rodada, token, tempo, custo, cansaço) em qualquer forma;
  B · a assíntota descrita como TAXA DE DESCOBERTA em vez de severidade;
  C · teto de rodadas apresentado como critério de fecho;
  D · limite aceito virando permanente sem a marca de ratificação do dono;
  E · o eixo de severidade presente onde o fecho é definido (o critério existe mesmo);
  F · o Artigo 14 citado onde o critério de parada é definido.

O QUE ELE NÃO CONSEGUE MEDIR, dito na cara (Artigo 4): ele lê TEXTO. Não prova que o laço
em execução obedeceu — prova que a instrução escrita não autoriza o contrário. O
comportamento é medido pela telemetria (`stop_reason` por sessão), não aqui. E ele NÃO
detecta a fraude mais grave do artigo (rebaixar P1 para P2 a fim de fechar), que não deixa
rastro no texto: isso é dívida declarada, e o que a mitiga hoje é o árbitro único de
severidade mais a lista de rejeitados com motivo. E ele NÃO alcança teto declarado em
`qa-loop.config.md` de projeto consumidor: ALVOS são arquivos DESTE repositório, e esses
configs vivem no `.claude/` de outros projetos — quem os pega é a revisão de lá. E ele NÃO
alcança os documentos de concepção com `status: approved` + `approved-sig` no frontmatter
(docs/solution-strategy.md, docs/features.md, docs/journeys.md, docs/glossary.md — casa-ok: prosa que cita o caso medido, nao um caminho usado): são
acordo assinado pelo dono, e mexer neles quebraria a assinatura — a frase revogada que
ainda vive lá é ALERTA para o dono re-referendar, nunca conserto deste cobrador.

    python3 scripts/test_revisao_fecha_por_problema.py
    python3 scripts/test_revisao_fecha_por_problema.py --json

stdlib only (requisito do repo).
"""
import argparse
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# Os arquivos que MANDAM num laço de revisão. Entrar aqui é declarar "este texto governa
# como uma revisão fecha". Motor e casca dos dois laços + o contrato do tripé.
ALVOS = [
    "plugins/project-skills/skills/qa-loop/SKILL.md",
    "plugins/project-skills/skills/qa-loop/references/motor.js",
    "plugins/project-skills/skills/sprint/SKILL.md",
    "plugins/project-skills/skills/sprint/references/motor.js",
    "_shared/dimensoes-de-revisao.md",
    # VITRINE E DOC DESCRITIVA — texto que o público lê antes de instalar qualquer
    # coisa, e os docs que descrevem o comportamento. Entraram por ENUMERAÇÃO
    # (2026-08-23), nunca por varredura de *.md: varredura reprovaria a própria
    # docs/constituicao.md, que cita as frases proibidas no ato de revogá-las — a lei  # casa-ok: prosa que cita o caso medido, nao um caminho usado
    # fica FORA de propósito, e a exclusão está documentada aqui.
    "README.md",
    "README.pt-BR.md",
    "plugins/project-skills/skills/qa-loop/EXAMPLE-REPORT.md",
    "plugins/visual/lib/visual_page.py",
    "docs/features.md",  # casa-ok: alvo enumerado do cobrador, nao resolucao de caminho de doc
    "docs/glossary.md",  # casa-ok: alvo enumerado do cobrador, nao resolucao de caminho de doc
    "docs/journeys.md",  # casa-ok: alvo enumerado do cobrador, nao resolucao de caminho de doc
    "docs/solution-strategy.md",  # casa-ok: alvo enumerado do cobrador, nao resolucao de caminho de doc
]

# Onde o critério de fecho é DEFINIDO — estes carregam as checagens E e F.
DEFINEM_PARADA = [
    "plugins/project-skills/skills/qa-loop/SKILL.md",
    "plugins/project-skills/skills/qa-loop/references/motor.js",
]

# (A) — fecho por GASTO. O que o dono cortou: "o que NÃO pode ter é o teto por gasto de
# rodadas ou tokens".
FRASES_DE_GASTO = [
    "não vale mais a pena",
    "nao vale mais a pena",
    "vale a pena parar",
    "cansou",
    "ficou caro",
    "gastou demais",
    "economizar rodada",
    "economizar token",
    "orçamento de rodadas",
    "orcamento de rodadas",
    "por custo",
]

# (B) — a assíntota lida como TAXA DE DESCOBERTA. Estas frases descrevem quantidade de
# achados caindo, e o dono foi explícito: "Não tem a ver com 'rendendo menos' em termos de
# achar erros (...). Tem a ver com SEVERIDADE."
FRASES_DE_TAXA = [
    "retornos decrescentes",
    "retorno decrescente",
    "está rendendo menos",
    "esta rendendo menos",
    "rendendo menos",
    "achando cada vez menos",
    "convergiu o suficiente",
]

# (C) — teto como CRITÉRIO de fecho (e não como freio declarado).
FRASES_DE_TETO_COMO_CRITERIO = [
    "para ao atingir o teto",
    "fecha ao atingir o teto",
    "para quando bate o teto",
    "teto atingido → sucesso",
    "teto = fecho",
]

# A isenção é EXPLÍCITA, nunca adivinhada. Mesmo padrão do `# regua-ok:` do
# regua_call_check.py. POR QUE NÃO É HEURÍSTICA DE NEGAÇÃO (medido 2026-08-23): a primeira
# versão procurava marcas tipo "nunca"/"não é"/"não vale" perto da frase, e falhou na prova
# de mutação — "não vale" CANCELA a própria frase proibida "não vale mais a pena", e "não é"
# é tão comum que anistiava quase toda linha. Isenção adivinhada não é isenção, é buraco.
MARCA_DE_ISENCAO = "artigo14-ok"
JANELA_DE_ISENCAO = 3  # a marca abre o parágrafo; o markdown quebra a frase depois dela.

# (D) — limite aceito permanente exige ratificação do dono.
MARCAS_DE_LIMITE = ["accepted-limit", "acceptedlimits", "limite aceito", "proposedlimits"]
MARCAS_DE_RATIFICACAO = ["ratific", "o dono", "usuário move", "usuario move", "dono move",
                         "propõe", "propoe", "nunca grava permanente"]

# (E) — o eixo do fecho tem que ser severidade, e ela tem que estar nomeada.
MARCAS_DE_SEVERIDADE = ["severidade", "severity_floor", "severityfloor", "floor", "p0", "p1"]

achados = []


def falha(arquivo, linha, regra, trecho):
    achados.append({"arquivo": arquivo, "linha": linha, "regra": regra,
                    "trecho": trecho.strip()[:160]})


def normaliza(s):
    return s.lower()


# O marcador que ABRE a linha (citação `>`, bullet, `#` de título, `//` de comentário JS)
# some ANTES do colapso de espaço. Medido 2026-08-23: só colapsar `\s+` NÃO resolve, porque
# entre "retornos" e "decrescentes" partidos num blockquote sobra o `>` — e a frase proibida
# continua invisível. Só o começo da linha é limpo; `>` no meio da prosa fica.
ABERTURA_DE_LINHA = re.compile(r"^[\s>*+#-]*(?://+\s*)?[\s>*+#-]*")


def normaliza_arquivo(texto):
    """Devolve (texto normalizado do arquivo inteiro, mapa offset→nº da linha 1-based)."""
    partes, mapa = [], []
    for n, ln in enumerate(texto.splitlines(), 1):
        corpo = " ".join(ABERTURA_DE_LINHA.sub("", normaliza(ln)).split())
        if not corpo:
            continue
        if partes:
            partes.append(" ")
            mapa.append(n)
        partes.append(corpo)
        mapa.extend([n] * len(corpo))
    return "".join(partes), mapa


def isento(linhas, i):
    janela = linhas[max(0, i - JANELA_DE_ISENCAO):i + 1]
    return any(MARCA_DE_ISENCAO in normaliza(v) for v in janela)


def checa_frases(rel, texto, frases, regra):
    linhas = texto.splitlines()
    baixo, mapa = normaliza_arquivo(texto)
    vistos = set()
    for frase in frases:
        de = baixo.find(frase)
        while de != -1:
            n = mapa[de]                       # a linha onde a frase COMEÇA
            if not isento(linhas, n - 1) and n not in vistos:
                vistos.add(n)
                falha(rel, n, regra, linhas[n - 1])
            de = baixo.find(frase, de + 1)


def checa_d(rel, texto):
    baixo = normaliza(texto)
    if not any(m in baixo for m in MARCAS_DE_LIMITE):
        return
    if not any(m in baixo for m in MARCAS_DE_RATIFICACAO):
        falha(rel, 0, "D · limite aceito sem exigir ratificação do dono",
              "fala de limite aceito mas não exige o aval de quem paga a conta")


def checa_e(rel, texto):
    baixo = normaliza(texto)
    if not any(m in baixo for m in MARCAS_DE_SEVERIDADE):
        falha(rel, 0, "E · define fecho sem nomear o eixo de SEVERIDADE",
              "a assíntota do Artigo 14 é de severidade — ela tem que estar escrita")


def checa_f(rel, texto):
    if "Artigo 14" not in texto:
        falha(rel, 0, "F · define fecho sem citar o Artigo 14",
              "quem define o critério de parada cita a lei que o governa")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    lidos = 0
    for rel in ALVOS:
        caminho = os.path.join(RAIZ, rel)
        if not os.path.isfile(caminho):
            falha(rel, 0, "alvo declarado não existe",
                  "ALVOS cita um arquivo que sumiu — atualize a lista ou restaure o arquivo")
            continue
        with open(caminho, encoding="utf-8") as fh:
            texto = fh.read()
        lidos += 1
        checa_frases(rel, texto, FRASES_DE_GASTO,
                     "A · fecho por GASTO (rodada/token/tempo/custo)")
        checa_frases(rel, texto, FRASES_DE_TAXA,
                     "B · assíntota como TAXA DE DESCOBERTA, não como severidade")
        checa_frases(rel, texto, FRASES_DE_TETO_COMO_CRITERIO,
                     "C · teto de rodadas apresentado como critério de fecho")
        checa_d(rel, texto)
        if rel in DEFINEM_PARADA:
            checa_e(rel, texto)
            checa_f(rel, texto)

    if args.json:
        print(json.dumps({"lidos": lidos, "achados": achados}, ensure_ascii=False, indent=1))
    else:
        print("Artigo 14 · assíntota de SEVERIDADE, nunca de gasto — %d arquivo(s) medido(s)" % lidos)
        for a in achados:
            onde = "%s:%s" % (a["arquivo"], a["linha"]) if a["linha"] else a["arquivo"]
            print("  FAIL %s" % onde)
            print("       %s" % a["regra"])
            print("       %s" % a["trecho"])
        if not achados:
            print("  sem achados — o fecho é por severidade, e nenhum laço fecha por gasto")

    return 1 if achados else 0


if __name__ == "__main__":
    sys.exit(main())
