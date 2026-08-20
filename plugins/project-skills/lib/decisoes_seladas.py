#!/usr/bin/env python3
"""As decisões seladas — o registro que impede a mesma pergunta duas vezes (F22.6 · R-32).

A mesma pergunta parou corridas 4 vezes em dias diferentes, e "tudo que puder
decidir no final, decido no final" já estava dito e ninguém consultava. O conserto
é um registro POR PROJETO das decisões que o dono JÁ tomou: uma linha por decisão
(fala literal + data + fonte), grep-ável — a frase-chave inteira mora numa linha
só, porque partida em duas o grep não acha (medido na LifeOrchestra).

Quem consulta: TODO papel antes de perguntar qualquer coisa ao dono — o pré-check
de largada, o prompt de pendência do motor, a casca. A régua compartilhada
(`_shared/regua-de-pergunta.md`) carrega a instrução; este arquivo carrega o
mecanismo. Decisão nova tomada em qualquer pergunta entra no registro na hora.

O registro vive em `.claude/decisoes-seladas.md` na raiz do PROJETO consumidor —
nunca dentro do plugin (cache reescrito a cada bump) — e é doc: entra no commit.

Uso:
    from decisoes_seladas import selar, consultar, caminho
    selar(raiz, fala="tudo que puder decidir no final, decido no final",
          fonte="colheita da execução 12", data="2026-08-19")
    achadas = consultar(raiz, "posso adiar essa decisão para o final?")
    # achadas != [] ⇒ a pergunta NÃO vai ao dono: a linha achada É a resposta.

    python3 decisoes_seladas.py selar <raiz> --fala F --fonte S [--data AAAA-MM-DD]
    python3 decisoes_seladas.py consultar <raiz> "<pergunta>"   # exit 1 = sem linha
    python3 decisoes_seladas.py indice <raiz>

stdlib only (requisito do repo).
"""

import argparse
import datetime
import os
import re
import sys
import unicodedata

ARQUIVO = os.path.join(".claude", "decisoes-seladas.md")

CABECALHO = """\
# Decisões seladas

Uma linha por decisão do dono: `- [data] "fala literal" — fonte: <onde foi dita>`.
Consulte ANTES de perguntar qualquer coisa ao dono; linha achada É a resposta.
A frase-chave fica inteira numa linha só — partida em duas, o grep não acha.
"""

# Palavras que não distinguem decisão nenhuma — fora da comparação.
_VAZIAS = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das", "em",
    "no", "na", "nos", "nas", "e", "ou", "que", "se", "por", "para", "pra",
    "com", "sem", "ao", "aos", "à", "às", "é", "ser", "foi", "vai", "tem",
    "há", "não", "nao", "sim", "eu", "ele", "ela", "isso", "esse", "essa",
    "este", "esta", "qual", "quais", "como", "quando", "onde", "posso",
    "pode", "deve", "devo", "sobre", "mais", "já", "ja", "só", "so",
}


def caminho(raiz):
    return os.path.join(raiz, ARQUIVO)


def _normaliza(texto):
    """minúsculas e sem acento — 'decisão' e 'DECISAO' são a mesma palavra."""
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return "".join(c for c in texto if not unicodedata.combining(c))


def _tokens(texto):
    return {t for t in re.findall(r"[a-z0-9]+", _normaliza(texto))
            if len(t) > 2 and t not in _VAZIAS}


def _linhas_de_decisao(raiz):
    arq = caminho(raiz)
    if not os.path.isfile(arq):
        return []
    with open(arq, encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f if ln.startswith("- [")]


def selar(raiz, fala, fonte, data=None):
    """Grava UMA linha nova. Devolve a linha gravada (ou a já existente — sem dobro)."""
    if "\n" in fala or "\r" in fala:
        raise ValueError("fala com quebra de linha: partida em duas, o grep não acha")
    if not fala.strip() or not fonte.strip():
        raise ValueError("decisão sem fala ou sem fonte não sela nada")
    data = data or datetime.date.today().isoformat()
    linha = '- [%s] "%s" — fonte: %s' % (data, fala.strip(), fonte.strip())
    for existente in _linhas_de_decisao(raiz):
        if _normaliza(fala.strip()) in _normaliza(existente):
            return existente
    arq = caminho(raiz)
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    novo = not os.path.isfile(arq)
    with open(arq, "a", encoding="utf-8") as f:
        if novo:
            f.write(CABECALHO + "\n")
        f.write(linha + "\n")
    return linha


def consultar(raiz, pergunta):
    """As linhas que já respondem a pergunta, mais forte primeiro. [] = pergunta segue.

    Casa por frase inteira (a pergunta contém a frase-chave, ou vice-versa) ou por
    sobreposição de palavras significativas — a pergunta re-escrita com outras
    palavras de enchimento ainda acha a mesma decisão.
    """
    alvo = _tokens(pergunta)
    perg_norm = _normaliza(pergunta)
    achadas = []
    for linha in _linhas_de_decisao(raiz):
        fala = re.search(r'"(.*)"', linha)
        fala = fala.group(1) if fala else linha
        fala_norm = _normaliza(fala)
        if fala_norm and (fala_norm in perg_norm or perg_norm in fala_norm):
            achadas.append((1.0, linha))
            continue
        seus = _tokens(linha)
        if not alvo or not seus:
            continue
        comum = len(alvo & seus)
        # ponytail: limiar fixo de metade das palavras da pergunta; ajuste se
        # falso-positivo aparecer em registro grande.
        if comum >= 2 and comum / len(alvo) >= 0.5:
            achadas.append((comum / len(alvo), linha))
    achadas.sort(key=lambda par: -par[0])
    return [linha for _, linha in achadas]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("selar", help="grava uma decisão nova (uma linha)")
    p.add_argument("raiz")
    p.add_argument("--fala", required=True, help="a fala literal do dono")
    p.add_argument("--fonte", required=True, help="onde a fala foi dita")
    p.add_argument("--data", help="AAAA-MM-DD; default hoje")

    p = sub.add_parser("consultar", help="acha decisão já tomada; exit 1 = nenhuma")
    p.add_argument("raiz")
    p.add_argument("pergunta")

    p = sub.add_parser("indice", help="imprime o índice: uma linha por decisão")
    p.add_argument("raiz")

    args = ap.parse_args(argv)
    if args.cmd == "selar":
        try:
            print(selar(args.raiz, args.fala, args.fonte, args.data))
        except ValueError as e:
            print("decisoes_seladas: %s" % e, file=sys.stderr)
            return 2
        return 0
    if args.cmd == "consultar":
        achadas = consultar(args.raiz, args.pergunta)
        for linha in achadas:
            print(linha)
        if not achadas:
            print("nenhuma decisão selada cobre — a pergunta segue ao dono",
                  file=sys.stderr)
            return 1
        return 0
    if args.cmd == "indice":
        for linha in _linhas_de_decisao(args.raiz):
            print(linha)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
