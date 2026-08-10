#!/usr/bin/env python3
"""A régua do campo `pronto` — recusa o critério que só se cumpre mexendo no entregável.

O caso que deu origem: um critério mandava o número APARECER no documento. O
executor obedeceu e escreveu o número na mão. Quem errou foi o CRITÉRIO, não
quem executou — e ninguém o julgou antes de soltar o executor.

A régua é sobre a ORIGEM DO VALOR, não sobre o caminho do arquivo:

    PODE     regerar o entregável a partir do dado real — é operação do produto
    NÃO PODE injetar valor inventado dentro do entregável pro critério fechar

Por isso a checagem não proíbe citar o entregável: ela exige que, quando o
critério pede PRESENÇA de algo dentro de um artefato, o mesmo critério diga de
onde o valor vem (gerar, regerar, derivar, renderizar, extrair, "a partir de").
Critério sem origem declarada é bancada, e bancada não entra em coisa que vale.

Uso:
    from regua_pronto import erros_de_pronto
    errs = erros_de_pronto(item["pronto"], "F2.3")

    printf '%s' "$PRONTO" | python3 regua_pronto.py --onde F2.3 -

Exit 1 = o critério é bancada (veredito, não crash). stdlib only (requisito do repo).
"""

import re
import sys

# CANAIS DE TEXTO EM UTF-8, SEMPRE. No Windows eles nascem na codificação do sistema
# (cp1252) e o payload do evento — que chega por stdin — é UTF-8: sem isto, todo
# acento do pedido do usuário chega corrompido ao gate, e emoji derruba a escrita.
for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

# Artefato que um humano lê e que um executor consegue EDITAR à mão — é aí que a
# injeção de valor cabe. Tela, banco e processo ficam de fora: não se digita neles.
_ENTREGAVEL = re.compile(
    r"\.(md|html?|json|csv|txt|pdf|docx?|xlsx?|ya?ml)\b"
    r"|\b(relat[óo]rio|documento|doc|documenta[çc][ãa]o|p[áa]gina|readme|changelog"
    r"|slide|apresenta[çc][ãa]o|planilha|arquivo)\b",
    re.I)

# Verbo de PRESENÇA: o critério fecha quando o texto está lá, sem dizer quem o pôs.
_PRESENCA = re.compile(
    r"\b(aparece|aparecem|consta|constam|cont[ée]m|cita|citam|menciona|mencionam"
    r"|traz|trazem|mostra|mostram|exibe|exibem|lista|listam|documenta|documentam"
    r"|est[áa] (?:escrit[oa]|list[oa]d[oa]|document[oa]d[oa]|l[áa])"
    r"|est[ãa]o (?:escrit[oa]s|list[oa]d[oa]s|document[oa]d[oa]s|l[áa]))\b",
    re.I)

# Origem do valor declarada: o entregável NASCE do dado, não da mão de quem executa.
_ORIGEM = re.compile(
    r"\b(gera|geram|gerad[oa]s?|gerar|regera|regeram|regerad[oa]s?|regerar"
    r"|deriva|derivam|derivad[oa]s?|derivar|renderiza|renderizad[oa]s?|renderizar"
    r"|extrai|extra[íi]d[oa]s?|extrair|recalcula|recalculad[oa]s?|calculad[oa]s?"
    r"|a partir d[aeo])\b",
    re.I)


# Efeito que só existe FORA deste processo: outro processo, outro repositório, outra
# máquina, outro agente. Ninguém o observa de dentro da bancada — só o mundo real.
_FORA_DO_PROCESSO = re.compile(
    r"\b(commit(a|am|ar|ad[oa]s?)?|push(a|am|ar|ad[oa]s?)?|deploy(a|ar|ad[oa]s?)?"
    r"|publica(m|r|d[oa]s?)?|remoto|origin|outra m[áa]quina|skill|hook"
    r"|subprocess|processo filho|daemon)\b",
    re.I)

# A prova oferecida FINGE a chamada: o verde vem do dublê, não do efeito acontecendo.
_SIMULACAO = re.compile(
    r"\b(mock(s|ad[oa]s?|ar|a|am)?|stub(s|ad[oa]s?)?|fake(s)?|dubl[êe]"
    r"|monkeypatch(ed|ar|ad[oa]s?)?|simula(m|r|d[oa]s?)?|finge|fingid[oa]s?"
    r"|dry[- ]run)\b",
    re.I)


def erros_de_pronto(v, onde):
    """Os motivos pelos quais este critério de aceite é bancada. Lista vazia = passa."""
    t = str(v or "").strip()
    if not t:
        return []
    if _FORA_DO_PROCESSO.search(t) and _SIMULACAO.search(t):
        return ["%s: o efeito prometido acontece FORA deste processo e a única prova "
                "oferecida SIMULA a chamada — o verde vem do dublê, não do efeito; "
                "diga o que observa o efeito no mundo real" % onde]
    if not (_PRESENCA.search(t) and _ENTREGAVEL.search(t)):
        return []
    if _ORIGEM.search(t):
        return []
    return ["%s: o critério fecha com o valor DENTRO do entregável e não diz de onde "
            "ele vem — escrever à mão cumpre; diga o que REGERA o artefato a partir "
            "do dado real" % onde]


# O critério que chegou PELA METADE: crase aberta, reticências, ou uma frase que
# para num conectivo. É a assinatura do texto cortado no meio — foi assim que o
# `pronto` de duas tarefas chegou ao disco cortado em 400 caracteres.
_PENDURADO = re.compile(
    r"(,|\.\.\.|…|\b(e|ou|que|de|do|da|dos|das|com|em|no|na|nos|nas|para|pra)\b)$",
    re.I)

# Corte por LIMITE DE CARACTERE não respeita fim de frase: ele cai no meio de uma
# palavra, e aí nenhum conectivo casa. Duas assinaturas que sobram: parêntese/aspa
# que abriu e não fechou, e palavra terminada em letra que não termina palavra em
# português (…caminh, …trabalh, …conj). O trecho entre crases sai antes: comando
# de verdade tem parêntese solto dentro (regex, `rgba\(`).
_CODIGO = re.compile(r"`[^`]*`")
# ponytail: 4 letras cobrem o corte que escapa hoje; ampliar só com medição no disco
_MEIO_DE_PALAVRA = re.compile(r"[A-Za-zÀ-ÿ][hjqv]$")


def criterio_cortado(v, onde):
    """O critério chegou cortado no meio? Lista vazia = passa.

    Fica FORA de `erros_de_pronto` de propósito: o texto que já estava no disco é
    isento da régua de REDAÇÃO na regravação, e um critério truncado precisa ser
    recusado toda vez — pela metade ele não diz o que provar.
    """
    t = str(v or "").strip()
    if not t:
        return []
    if t.count("`") % 2:
        return ["%s: o critério tem crase sem fechar — chegou cortado no meio do "
                "comando; escreva o critério inteiro" % onde]
    if _PENDURADO.search(t):
        return ["%s: o critério para no meio da frase (…%s) — chegou cortado; "
                "escreva o critério inteiro" % (onde, t[-24:])]
    fora = _CODIGO.sub(" ", t).rstrip()
    if fora.count("(") != fora.count(")"):
        return ["%s: o critério tem parêntese sem fechar (…%s) — chegou cortado; "
                "escreva o critério inteiro" % (onde, t[-24:])]
    if fora.count('"') % 2:
        return ["%s: o critério tem aspa sem fechar (…%s) — chegou cortado; "
                "escreva o critério inteiro" % (onde, t[-24:])]
    if _MEIO_DE_PALAVRA.search(fora):
        return ["%s: o critério acaba no meio de uma palavra (…%s) — chegou cortado "
                "por limite de caractere; escreva o critério inteiro" % (onde, t[-24:])]
    return []


# ── linha de comando: como um .sh ou um gate cobra a MESMA régua ───────────

_USO = "uso: regua_pronto.py [--onde ROTULO] -   (o texto do `pronto` na stdin)\n"


def _main(argv):
    onde, tem_stdin = "pronto", False
    it = iter(argv)
    for a in it:
        if a == "--onde":
            onde = next(it, "")
        elif a == "-":
            tem_stdin = True
        else:
            sys.stderr.write(_USO)
            return 2
    if not tem_stdin:
        sys.stderr.write(_USO)
        return 2
    texto = sys.stdin.read()
    errs = criterio_cortado(texto, onde) + erros_de_pronto(texto, onde)
    for e in errs:
        sys.stderr.write("%s\n" % e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
