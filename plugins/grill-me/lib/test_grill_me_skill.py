#!/usr/bin/env python3
"""A sabatina pergunta pelo canal que o dono escolher — e nunca pergunta fato a ele.

Os três defeitos que esta suíte impede:

  1. a skill perguntava UMA por vez, sempre, e cada pergunta custava um turno do
     dono — inclusive as que não dependiam da resposta da anterior;
  2. a skill perguntava ao dono coisa que ela mesma podia descobrir no ambiente
     (arquivo, ferramenta), gastando o turno dele com fato em vez de decisão;
  3. a adição local do marketplace (a sabatina não é juíza) sumia toda vez que o
     texto do autor era atualizado por cima.

E um quarto, de forma: citar o plugin irmão por caminho executável
(`CLAUDE_PLUGIN_ROOT/../<irmão>/…`, `plugins/<irmão>/…`) quebra na máquina de
quem instalou, porque o cache do harness instala cada plugin em pasta própria.
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(AQUI, "..", "skills", "grill-me", "SKILL.md")
# A régua de por onde a pergunta chega saiu do SKILL.md e virou contrato de todas
# as skills que perguntam ao dono: fonte em _shared/, cópia vendorada aqui do lado.
REGUA = os.path.join(AQUI, "..", "skills", "grill-me", "regua-de-pergunta.md")

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
    cru = open(SKILL, encoding="utf-8").read()
    skill = ler(SKILL)

    print("o texto do autor esta na versao em rodadas, verbatim")
    check("a arvore de decisao e trabalhada em rodadas",
          "Work the tree in **rounds**" in skill)
    check("a fronteira e o conceito que define a rodada",
          "The **frontier** is every decision whose prerequisites are already settled"
          in skill)
    check("a rodada inteira vai de uma vez",
          "Ask the whole frontier in one round" in skill)
    check("o formato numerado da pergunta esta no texto",
          "❓ **Q1**" in skill and "➡️ <your recommended answer>" in skill)
    check("pergunta que depende de outra ainda aberta fica para a rodada seguinte",
          "belongs to a _later_ round, not this one" in skill)
    check("a sessao acaba quando a fronteira esvazia",
          "The session is done when the frontier is empty" in skill)

    print("fato e trabalho da skill, nunca do dono")
    check("a regra do fato esta escrita",
          "Finding _facts_ is your job, never the user's" in skill)
    check("fato do ambiente vira sub-agente despachado",
          "dispatch a sub-agent to find it" in skill)
    check("a exploracao rodando nao trava o resto da fronteira",
          "ask the rest of the frontier now" in skill)
    check("a decisao continua sendo do dono",
          "The _decisions_ are the user's" in skill)

    print("a pergunta chega por um de dois canais, e quem escolhe e o dono")
    check("a copia vendorada da regua esta ao lado do SKILL.md",
          os.path.isfile(REGUA))
    regua = ler(REGUA) if os.path.isfile(REGUA) else ""
    check("o SKILL.md aponta pra regua em vez de repetir o texto",
          "regua-de-pergunta.md" in skill
          and "_shared/regua-de-pergunta.md" in skill
          and "**Alternativa — uma por vez, na ferramenta nativa de pergunta.**"
          not in skill)
    check("o padrao e a rodada inteira numa pagina, em multipla escolha",
          "**Padrão — a rodada inteira numa página, em múltipla escolha.**" in regua)
    check("a pagina traz opcoes em radio E campo livre",
          "as opções em rádio" in regua and "campo livre" in regua)
    check("a recomendacao entra como sugestao, nao como resposta ja dada",
          "nunca como resposta dada" in regua)
    check("a resposta volta pelo estado que o daemon grava em disco",
          "~/.claude/visual-state/latest.json" in regua
          and "não peça ao usuário para copiar e colar" in regua)
    check("a alternativa e uma por vez na ferramenta nativa",
          "**Alternativa — uma por vez, na ferramenta nativa de pergunta.**" in regua)
    check("quem escolhe o canal e o dono, e sem escolha vale o padrao",
          "**Quem escolhe é o usuário.**" in regua and "use o padrão" in regua)
    check("os dois canais vem antes da adicao do /start-doc",
          em_ordem(skill, ["## Adição local — por onde a pergunta chega",
                           "## Adição local — quando o chamador é o `/start-doc`"]))

    print("o irmao e invocado por nome, nunca por caminho")
    check("nao ha irmao por posicao relativa",
          "CLAUDE_PLUGIN_ROOT" not in cru and "CLAUDE_PLUGIN_ROOT" not in regua)
    check("nao ha caminho para dentro de outro plugin",
          "plugins/" not in cru and "plugins/" not in regua)
    check("a skill de apresentacao e invocada pelo nome",
          "invoque-a **pelo nome**" in regua)
    check("skill ausente na maquina nao quebra a sabatina",
          "caia no canal alternativo e siga" in regua)

    print("a adicao local do marketplace sobreviveu ao texto novo")
    check("a sabatina sabe que e chamada pelas cinco etapas do /start-doc",
          "cinco etapas de acordo" in skill and "/start-doc" in skill)
    check("a sabatina nega o papel de juiz",
          "**Você não é juiz.**" in skill)
    check("quem aprova e o dono, no frontmatter do documento",
          "**Quem aprova é o dono**" in skill
          and "`status: approved`" in skill)
    check("objecao nao resolvida volta pro documento",
          "**Objeção não resolvida volta pro documento**" in skill)
    check("as duas adicoes se declaram do marketplace, e nao do autor",
          skill.count("Esta seção é do marketplace, não do autor original") == 2)

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
