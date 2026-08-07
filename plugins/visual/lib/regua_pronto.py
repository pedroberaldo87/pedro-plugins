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


def erros_de_pronto(v, onde):
    """Os motivos pelos quais este critério de aceite é bancada. Lista vazia = passa."""
    t = str(v or "").strip()
    if not t:
        return []
    if not (_PRESENCA.search(t) and _ENTREGAVEL.search(t)):
        return []
    if _ORIGEM.search(t):
        return []
    return ["%s: o critério fecha com o valor DENTRO do entregável e não diz de onde "
            "ele vem — escrever à mão cumpre; diga o que REGERA o artefato a partir "
            "do dado real" % onde]


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
    errs = erros_de_pronto(sys.stdin.read(), onde)
    for e in errs:
        sys.stderr.write("%s\n" % e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
