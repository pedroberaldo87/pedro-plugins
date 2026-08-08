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

CAMPOS = ("cobrador", "regra", "gravidade", "onde", "o_que", "prova")

GRAVIDADES = ("alta", "media", "baixa")


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
