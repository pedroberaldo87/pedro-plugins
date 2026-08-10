#!/usr/bin/env python3
"""O formato do achado da vistoria — e o porteiro que recusa achado sem prova.

Um achado é uma acusação. Acusação sem o trecho que a sustenta não vira achado
fraco: não vira achado nenhum. Por isso `prova` é campo obrigatório como
qualquer outro, e o construtor levanta em vez de emitir um item pela metade.

    from achado import achado, erros_de_achado, AchadoInvalido

    a = achado(cobrador="hook-contract", regra="R1-cap-ausente",
               onde="ship/pre-deploy-test-check.sh:363",
               o_que="bloqueia e não tem teto de devoluções",
               prova="exit 2")

stdlib only (requisito do repo).
"""

import json
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

CAMPOS = ("cobrador", "regra", "gravidade", "onde", "o_que", "prova")

GRAVIDADES = ("alta", "media", "baixa")

# As lentes de LEITURA — as que saem de um agente lendo instrução, não de um programa
# medindo. Delas a pauta exige o PAR de citações literais dentro da prova.
LIDOS = ("leitor", "cruzamento")

CITACAO = re.compile(r"[\w./-]+\.\w+:\d+")


class AchadoInvalido(ValueError):
    """O item não é um achado — falta campo, ou falta a prova."""


def erros_de_achado(a):
    """Os motivos pelos quais este dicionário não é um achado. Lista vazia = passa."""
    errs = []
    if not isinstance(a, dict):
        return ["não é um dicionário: %r" % type(a).__name__]
    for campo in CAMPOS:
        if campo not in a:
            errs.append("campo ausente: %s" % campo)
        elif not str(a[campo] or "").strip():
            errs.append("campo vazio: %s" % campo)
    if "gravidade" in a and a["gravidade"] not in GRAVIDADES:
        errs.append("gravidade fora de %s: %r" % (list(GRAVIDADES), a["gravidade"]))
    return errs


def valida(a):
    """Devolve o achado se ele é um achado; levanta AchadoInvalido se não é."""
    errs = erros_de_achado(a)
    if errs:
        raise AchadoInvalido("; ".join(errs))
    return a


def erros_de_lote(achados):
    """Os erros de uma lista inteira, já com a régua extra do achado LIDO.

    Achado que veio de LEITURA (um agente lendo a instrução) precisa do PAR de
    citações literais na prova — é a pauta que exige as duas pontas, e a leitura
    sem as duas é opinião. Achado MEDIDO vem de programa: a saída crua é a prova.
    """
    errs = []
    for i, a in enumerate(achados):
        for e in erros_de_achado(a):
            errs.append("achado %d: %s" % (i, e))
        if isinstance(a, dict) and a.get("cobrador") in LIDOS:
            if len(CITACAO.findall(str(a.get("prova") or ""))) < 2:
                errs.append("achado %d: achado LIDO sem par de citações arquivo:linha "
                            "na prova" % i)
    return errs


def achado(cobrador, regra, onde, o_que, prova, gravidade="media"):
    """Monta um achado já validado — sem prova não sai item."""
    return valida({
        "cobrador": cobrador,
        "regra": regra,
        "gravidade": gravidade,
        "onde": onde,
        "o_que": o_que,
        "prova": prova,
    })


def main(argv=None):
    """`--validar [arquivo.json]` (ou o JSON pelo stdin): sai 0 se o lote é achado."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--validar" not in argv:
        sys.stderr.write("uso: achado.py --validar [arquivo.json]  (ou JSON no stdin)\n")
        return 2
    alvos = [a for a in argv if not a.startswith("--")]
    with (open(alvos[0], encoding="utf-8") if alvos else sys.stdin) as fh:
        dados = json.load(fh)
    achados = dados.get("achados", dados) if isinstance(dados, dict) else dados
    errs = erros_de_lote(achados)
    for e in errs:
        sys.stderr.write(e + "\n")
    if errs:
        return 1
    print("%d achado(s) válido(s)" % len(achados))
    return 0


if __name__ == "__main__":
    sys.exit(main())
