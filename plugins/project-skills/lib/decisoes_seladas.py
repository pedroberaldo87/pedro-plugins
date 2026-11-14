#!/usr/bin/env python3
"""As decisões seladas — o registro que impede a mesma pergunta duas vezes (F22.6 · R-32).

A mesma pergunta parou corridas 4 vezes em dias diferentes, e "tudo que puder
decidir no final, decido no final" já estava dito e ninguém consultava. O conserto
é um registro POR PROJETO das decisões que o dono JÁ tomou: uma linha por decisão
(fala literal + data + fonte), grep-ável — a frase-chave inteira mora numa linha
só, porque partida em duas o grep não acha (medido num projeto real).

Quem consulta: TODO papel antes de perguntar qualquer coisa ao dono — o pré-check
de largada, o prompt de pendência do motor, a casca. A régua compartilhada
(`_shared/regua-de-pergunta.md`) carrega a instrução; este arquivo carrega o
mecanismo. Decisão nova tomada em qualquer pergunta entra no registro na hora.

O registro vive em `.claude/decisoes-seladas.md` na raiz do PROJETO consumidor —
nunca dentro do plugin (cache reescrito a cada bump) — e é doc: entra no commit.

Uso:
    from decisoes_seladas import selar, consultar, sugerir, caminho
    selar(raiz, fala="posso adiar a escolha do provedor para o final?",
          fonte="colheita da execução 12", data="2026-08-19")
    achadas = consultar(raiz, "Posso adiar a escolha do provedor para o final?")
    # achadas != [] ⇒ a pergunta NÃO vai ao dono: a linha achada É a resposta. Só a CHAVE EXATA
    # (a fala, normalizada, é a própria pergunta) responde — o registro é um arquivo do repositório.
    parecidas = sugerir(raiz, "essa decisão do provedor pode ficar para o final?")
    # parecidas: SUGESTÃO. Mostre a fala ao dono ao lado da pergunta; nunca aplique sozinho.

    python3 decisoes_seladas.py selar <raiz> --fala F --fonte S [--data AAAA-MM-DD]
    python3 decisoes_seladas.py consultar <raiz> "<pergunta>"
        # exit 0 = a linha responde · exit 1 = nenhuma; linhas "SUGESTÃO" (stdout) não são resposta
    python3 decisoes_seladas.py indice <raiz>

stdlib only (requisito do repo).
"""

import argparse
import datetime
import os
import re
import sys
import unicodedata

from escrita_segura import anexa_texto_seguro

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


def _radicais(texto):
    """As 4 primeiras letras de cada palavra que conta — 'decisão', 'decidir' e
    'decido' viram o mesmo radical, senão a pergunta reescrita não acha a decisão."""
    return {t[:4] for t in _tokens(texto)}


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
    # o registro é versionado: um symlink no nome dele não redireciona a gravação (cf35688f)
    anexa_texto_seguro(arq, (CABECALHO + "\n" if novo else "") + linha + "\n", raiz=raiz)
    return linha


def _chave(texto):
    """A frase-chave normalizada: minúsculas, sem acento, só palavras e números, um espaço entre elas."""
    return " ".join(re.findall(r"[a-z0-9]+", _normaliza(texto)))


def _contem(texto, frase):
    """`frase` aparece em `texto` INTEIRA e em fronteira de palavra (log ≠ catalog)."""
    return re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(frase), texto) is not None


def _fala_da(linha):
    fala = re.search(r'"(.*)"', linha)
    return fala.group(1) if fala else linha


def consultar(raiz, pergunta):
    """As linhas que RESPONDEM a pergunta. [] = a pergunta segue ao dono.

    O registro é um arquivo do REPOSITÓRIO — num clone ele chega de fora, então uma linha dele não
    pode decidir por casamento frouxo o que o dono ainda não respondeu (7fab4b4e). Só responde a
    linha cuja frase-chave, normalizada (caixa, acento, pontuação), é a própria pergunta. O que
    casa de leve sai de `sugerir`: o chamador MOSTRA ao dono, nunca aplica.
    """
    alvo = _chave(pergunta)
    if not alvo:
        return []
    return [linha for linha in _linhas_de_decisao(raiz) if _chave(_fala_da(linha)) == alvo]


def sugerir(raiz, pergunta):
    """As linhas que PARECEM tratar da pergunta, mais forte primeiro — sugestão, nunca resposta.

    Quem chama mostra a fala ao dono ao lado da pergunta e deixa ele decidir. Não inclui as linhas
    que `consultar` já devolve. Casa por:
      1. a frase-chave inteira dentro da pergunta, em fronteira de palavra, e com pelo menos
         2 palavras que contam (uma fala de uma palavra não parece com nada);
      2. a pergunta inteira dentro da fala, nas mesmas condições e sem ser um pedaço pequeno
         de uma fala longa (as palavras da pergunta têm que ser metade ou mais das da fala);
      3. sobreposição de radicais — a pergunta reescrita com outras palavras de enchimento —,
         medida nos DOIS sentidos: a pergunta tem que trazer pelo menos metade da fala.
    """
    alvo = _radicais(pergunta)
    perg_norm = _normaliza(pergunta)
    perg_tok = _tokens(pergunta)
    exatas = set(consultar(raiz, pergunta))
    achadas = []
    for linha in _linhas_de_decisao(raiz):
        if linha in exatas:
            continue
        fala = _fala_da(linha)
        fala_norm = _normaliza(fala)
        fala_tok = _tokens(fala)
        if fala_norm and len(fala_tok) >= 2 and _contem(perg_norm, fala_norm):
            achadas.append((1.0, linha))
            continue
        if (perg_norm and len(perg_tok) >= 2 and len(perg_tok) * 2 >= len(fala_tok)
                and _contem(fala_norm, perg_norm)):
            achadas.append((1.0, linha))
            continue
        seus = _radicais(fala)
        if not alvo or not seus:
            continue
        comum = len(alvo & seus)
        # ponytail: limiar fixo de 2 radicais, 30% da pergunta e 50% da fala. Aqui o falso-positivo
        # custa só uma linha a mais na tela do dono (ele julga); o falso-negativo, a pergunta
        # repetida. Aperte se registro grande começar a sugerir tudo.
        if comum >= 2 and comum / len(alvo) >= 0.3 and comum / len(seus) >= 0.5:
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

    p = sub.add_parser("consultar", help="a decisão que responde a pergunta (chave exata); exit 1 = nenhuma, com sugestões marcadas")
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
            # sugestão não é resposta: sai marcada, e o exit 1 manda a pergunta ao dono
            for linha in sugerir(args.raiz, args.pergunta):
                print("SUGESTÃO (não é resposta — mostre ao dono, que decide): %s" % linha)
            print("nenhuma decisão selada responde — a pergunta segue ao dono",
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
