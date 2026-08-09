#!/usr/bin/env python3
"""A pesquisa de referências declara o custo ANTES e não escreve documento.

Os três defeitos que esta suíte impede:

  1. a pesquisa começava e só no fim se descobria quantos agentes rodaram e
     quanto tempo custou — custo descoberto depois não é custo aceito;
  2. ela rodava sem trava nenhuma, e "muitos agentes lendo a internet" é a
     receita de uma sessão que não termina;
  3. o achado dela caía direto dentro do documento autoral — referência lida
     por máquina virando resposta do dono é exatamente a ficção que o
     /start existe para impedir.

E a skill precisa ser OFERECIDA: etapa que trava por falta de repertório aponta
para ela. Sem esse apontamento a pesquisa só existe por invocação direta.
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(AQUI, "..")
SKILLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                      "project-skills", "skills")

PESQUISA = os.path.join(PLUGIN, "skills", "pesquisa-referencias", "SKILL.md")
START = os.path.join(SKILLS, "start", "SKILL.md")

# As etapas do /start que travam por falta de repertório — o documento de
# cada uma é o contrato, e é por ele que o apontamento é cobrado.
ETAPAS_SEM_REPERTORIO = [
    ("estratégia", "solution-strategy.md"),
    ("arquitetura", "architecture-intent.md"),
    ("interface", "design.md"),
    ("jornadas", "journeys.md"),
]

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def ler(caminho):
    """Lê o contrato com o espaço em branco normalizado.

    A quebra de linha do Markdown é diagramação, não conteúdo.
    """
    if not os.path.exists(caminho):
        return ""
    return " ".join(open(caminho, encoding="utf-8").read().split())


def main():
    print("a skill existe e se declara")
    check("o SKILL.md da pesquisa existe", os.path.exists(PESQUISA))
    pesquisa = ler(PESQUISA)
    start = ler(START)
    check("o nome no frontmatter é pesquisa-referencias",
          "name: pesquisa-referencias" in pesquisa)
    check("a descrição diz que o custo é declarado antes",
          "custo" in pesquisa.split("---")[1] if pesquisa.count("---") >= 2 else False)

    print("a oferta mostra quantos agentes e quanto tempo, e espera o aceite")
    check("a oferta tem seção própria",
          "## A oferta — o custo antes do trabalho" in pesquisa)
    check("a oferta traz o número de agentes", "{N} agentes" in pesquisa)
    check("a oferta traz o tempo estimado", "{T} minutos" in pesquisa)
    check("os dois números saem de uma conta declarada, não de chute",
          "Os dois números saem da conta" in pesquisa)
    check("sem aceite explícito a pesquisa não começa",
          "Sem o aceite explícito, a pesquisa não começa" in pesquisa)
    check("silêncio não é aceite", "Silêncio não é aceite" in pesquisa)
    check("mudou o escopo, a oferta é refeita",
          "A oferta é refeita e reaceita" in pesquisa)

    print("as travas de parada são numeradas, não são boa vontade")
    check("as travas têm seção própria", "## As travas de parada" in pesquisa)
    for trava in ("teto de agentes", "teto de fontes por agente",
                  "teto de tempo", "parada por saturação"):
        check("existe %s" % trava, trava in pesquisa)
    check("a trava estourada para e relata, não pede mais orçamento sozinha",
          "Trava estourada PARA e relata" in pesquisa)

    print("nada do que a pesquisa acha entra em documento aprovado sozinho")
    check("a regra dura tem seção própria",
          "## A REGRA DURA — nada entra em documento aprovado sozinho" in pesquisa)
    check("o achado é insumo de pergunta, nunca resposta",
          "Achado é insumo de pergunta. Achado nunca vira resposta" in pesquisa)
    check("a pesquisa não escreve documento autoral",
          "A pesquisa não escreve documento autoral" in pesquisa)
    check("documento já aprovado não é tocado pela pesquisa",
          "Documento com `status: approved` a pesquisa não toca" in pesquisa)
    check("todo achado carrega a fonte",
          "Todo achado carrega a fonte" in pesquisa)
    check("a pesquisa não aprova nem fecha etapa",
          "A pesquisa não aprova e não fecha etapa" in pesquisa)

    print("o que se lê é projeto aberto e produto pago, com a régua de cada um")
    check("projetos abertos entram nas fontes", "projetos abertos" in pesquisa)
    check("produtos pagos entram nas fontes", "produtos pagos" in pesquisa)
    check("produto pago é lido só pelo que é público",
          "só pelo que é público" in pesquisa)

    print("o /start OFERECE a pesquisa nas etapas que travam")
    check("o start-doc cita a skill pelo nome",
          "`/pesquisa-referencias`" in start)
    check("o start-doc tem a seção de falta de repertório",
          "### Quando falta repertório" in start)
    for etapa, arquivo in ETAPAS_SEM_REPERTORIO:
        check("a etapa de %s aponta para a pesquisa (%s)" % (etapa, arquivo),
              arquivo in start.split("### Quando falta repertório")[-1][:1400])
    check("o start-doc oferece, nunca dispara sozinho",
          "OFEREÇA `/pesquisa-referencias`" in start)
    check("o start-doc repete que o achado não vira resposta",
          "o achado da pesquisa não preenche campo autoral" in start)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
