#!/usr/bin/env python3
"""A concepção do /start-doc tem que fechar por ACORDO, não por fim de roteiro.

Os três defeitos que esta suíte impede:

  1. a entrevista terminava sem aprovação nenhuma registrada — o "de acordo" só
     existia na memória da conversa, e conversa não sobrevive ao /clear;
  2. arquitetura, interface e jornadas não eram etapa: viravam parágrafo solto
     dentro de outro documento, sem documento próprio nem aprovação própria;
  3. a sabatina (grill-me / grill-with-docs) escorregava para juíza da
     constituição — ela é COMO se chega nela, nunca quem a julga.

Os nomes de arquivo das etapas são contrato: quem cobra lacuna lê daqui.
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(AQUI, "..")
RAIZ_PLUGINS = os.path.join(PLUGIN, "..")

KIT = os.path.join(PLUGIN, "skills", "start-doc", "references", "authorial-kit.md")
SKILL = os.path.join(PLUGIN, "skills", "start-doc", "SKILL.md")
DESIGN = os.path.join(PLUGIN, "skills", "design-md", "SKILL.md")
GRILL_ME = os.path.join(RAIZ_PLUGINS, "grill-me", "skills", "grill-me", "SKILL.md")
GRILL_DOCS = os.path.join(RAIZ_PLUGINS, "grill-with-docs", "skills",
                          "grill-with-docs", "SKILL.md")

# Os documentos de etapa, na ordem em que as etapas fecham.
ETAPAS = [
    ("autoral", "quality-goals.md"),
    ("arquitetura", "architecture-intent.md"),
    ("interface", "design.md"),
    ("jornadas", "journeys.md"),
    ("funcionalidades", "features.md"),
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

    A quebra de linha do Markdown é diagramação, não conteúdo: sem isso a suíte
    quebraria só porque uma frase passou a caber em duas linhas.
    """
    return " ".join(open(caminho, encoding="utf-8").read().split())


def em_ordem(texto, marcas):
    """As marcas aparecem no texto, e nesta ordem."""
    pos = -1
    for m in marcas:
        i = texto.find(m, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def main():
    kit = ler(KIT)
    skill = ler(SKILL)
    design = ler(DESIGN)

    print("o kit define as etapas de acordo, na ordem, com documento proprio")
    check("as quatro etapas aparecem na ordem autoral, arquitetura, interface, jornadas",
          em_ordem(kit, ["**Acordo autoral**", "**Acordo de arquitetura**",
                         "**Acordo de interface**", "**Acordo de jornadas**"]))
    for etapa, arquivo in ETAPAS:
        check("a etapa de %s tem documento proprio (%s)" % (etapa, arquivo),
              arquivo in kit)
    check("os nomes de arquivo sao declarados contrato",
          "Os nomes de arquivo acima são o contrato" in kit)
    check("architecture-intent.md nao se confunde com o architecture.md minerado",
          "`architecture-intent.md` não é `architecture.md`" in kit)
    check("journeys.md nao se confunde com o runtime.md minerado",
          "`journeys.md` não é `runtime.md`" in kit)
    check("os dois documentos novos trazem roteiro e molde",
          kit.count("**Roteiro:**") >= 7 and kit.count("**Molde:**") >= 6)

    print("a entrevista termina produzindo a lista de funcionalidades, aprovada")
    check("a etapa de funcionalidades entra na tabela, depois das quatro",
          em_ordem(kit, ["**Acordo autoral**", "**Acordo de arquitetura**",
                         "**Acordo de interface**", "**Acordo de jornadas**",
                         "**Acordo de funcionalidades**"]))
    check("a lista e derivada do que ja foi aprovado nas etapas anteriores",
          "derivada do que já foi aprovado" in kit)
    check("a etapa de funcionalidades tem roteiro e molde proprios",
          kit.count("**Roteiro:**") >= 9 and kit.count("**Molde:**") >= 9)
    check("a lista so fecha com o de acordo do dono, como as outras",
          "A skill propõe, o dono decide" in kit
          and "A skill propõe, o dono decide" in skill)
    check("a skill aceita `features` como documento avulso",
          "`features`" in skill)
    check("a tabela de etapas da skill tem a linha de funcionalidades",
          "**Funcionalidades**" in skill)

    print("o de acordo fica gravado DENTRO do documento")
    check("o frontmatter do contrato tem o campo approved:",
          "approved: {YYYY-MM-DD}" in kit)
    check("status admite approved",
          "status: draft | ready | approved" in kit)
    check("maquina nenhuma escreve approved: sozinha",
          "`approved:` nenhuma máquina escreve sozinha" in kit)
    check("silencio nao vale como aprovacao",
          "Silêncio não é aprovação" in kit and "Silêncio não é aprovação" in skill)
    check("o design.md carrega o mesmo par por cima dos tokens",
          "`status:` / `approved:` entra **por cima** dos tokens" in kit)

    print("etapa aprovada aceita correcao pendente sem reabrir (F3.2)")
    check("o frontmatter do contrato tem o campo correcao-pendente:",
          "correcao-pendente: {" in kit)
    check("a correcao pendente vive no frontmatter, nunca no corpo",
          "no frontmatter, nunca no corpo" in kit)
    check("o kit diz que a correcao pendente nao reabre a etapa",
          "não reabre a etapa" in kit)
    check("a skill manda registrar a correcao em vez de reabrir a etapa",
          "correcao-pendente:" in skill and "não reabra a etapa" in skill)

    print("a etapa so fecha depois de apresentar e REAPRESENTAR")
    check("o kit manda apresentar o documento inteiro, nao um resumo",
          "Apresentar o documento inteiro" in kit)
    check("o kit manda reapresentar sem teto de rodadas",
          "REAPRESENTAR" in kit and "teto de rodadas" in kit)
    check("a skill tem o passo de apresentar/sabatinar/colher o de acordo",
          "### 5 · Apresentar, sabatinar e colher o de acordo" in skill)
    check("a skill manda reapresentar sem teto de rodadas",
          "REAPRESENTE" in skill and "teto de rodadas" in skill)
    check("escrever nao fecha a etapa",
          "não fecha** a etapa" in kit and "não fecha** a etapa" in skill)

    print("a sabatina e o caminho de fechar CADA etapa, e nao e juiza")
    check("a regra de fechamento vale para toda etapa",
          "Cada etapa fecha do mesmo jeito" in skill)
    check("o kit aponta grill-me e grill-with-docs como o caminho",
          "/grill-me" in kit and "/grill-with-docs" in kit)
    check("a skill aponta grill-me e grill-with-docs como o caminho",
          "/grill-me" in skill and "/grill-with-docs" in skill)
    check("o kit nega o papel de juiz a sabatina",
          "A sabatina não é juíza" in kit)
    check("a skill nega o papel de juiz a sabatina",
          "A sabatina não julga o documento" in skill
          and "A sabatina não é juíza" in skill)
    check("a etapa seguinte nao comeca com a anterior aberta",
          "a etapa continua aberta e a próxima não começa" in skill)

    print("a etapa de interface reaproveita a skill design-md, sem duplicar")
    check("o design-md se declara a etapa de interface do /start-doc",
          "etapa de interface do `/start-doc`" in design)
    check("o design-md grava o mesmo par de aprovacao",
          "`status: approved`" in design and "`approved: {YYYY-MM-DD}`" in design)
    check("lint limpo nao e aprovacao",
          "Lint limpo não é aprovação" in design)
    check("nao existe documento de interface paralelo",
          "Não existe documento paralelo de interface" in design)
    check("a skill start-doc nao reescreve a spec do DESIGN.md",
          "não duplique a spec do formato aqui" in skill)

    print("os modos e o relatorio enxergam as etapas novas")
    check("os nomes de doc aceitos incluem architecture-intent e journeys",
          "`architecture-intent`" in skill and "`journeys`" in skill)
    check("o relatorio tem uma linha de de-acordo por etapa",
          "**Passo 5/7:** De acordo" in skill)
    check("etapa escrita e nao aprovada conta como lacuna no modo gaps",
          "Etapa escrita e não aprovada conta como lacuna" in skill)

    print("as duas sabatinas sabem que nao sao juizas")
    if not (os.path.exists(GRILL_ME) and os.path.exists(GRILL_DOCS)):
        # Só o repositório tem os plugins irmãos lado a lado; o cache de um
        # plugin instalado tem apenas o project-doc. Contrato de irmão só é
        # checável onde os dois moram.
        print("  --   plugins irmaos ausentes (fora do repo) — 4 checagens puladas")
    else:
        for nome, caminho in (("grill-me", GRILL_ME), ("grill-with-docs", GRILL_DOCS)):
            texto = ler(caminho)
            check("%s: sabe que e chamada pelas cinco etapas do /start-doc" % nome,
                  "cinco etapas de acordo" in texto and "/start-doc" in texto)
            check("%s: nega o papel de juiz e devolve a aprovacao ao dono" % nome,
                  "Você não é juiz" in texto and "Quem aprova é o dono" in texto)

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
