#!/usr/bin/env python3
"""A skill /completude é invocável, roda o PROGRAMA e mostra os DOIS lados.

Três defeitos que esta suíte impede:

  1. skill que "mede completude" a olho — sem chamar `lib/completude.py`, a
     contagem volta a ser opinião do modelo;
  2. relatório de um lado só — a cadeia verde escondendo os artigos da lei que
     ninguém representou (ou o contrário) é o "cem por cento" que a medição
     existe para desmentir;
  3. o que falta contado sem ser NOMEADO — "3 requisitos órfãos" sem os três
     identificadores é a mesma omissão de sempre.

E o quarto, o que fez F1.1 existir: a skill REPETIR os eixos do tripé em vez de
apontar para a cópia vendorada. Duas prosas do mesmo contrato divergem.
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(AQUI, os.pardir)
SKILL = os.path.join(PLUGIN, "skills", "completude", "SKILL.md")
TRIPE = os.path.join(PLUGIN, "skills", "completude", "references",
                     "dimensoes-de-revisao.md")
MOTOR = os.path.join(PLUGIN, "lib", "completude.py")

FALHAS = []


def check(rotulo, cond):
    print(("  ok   " if cond else "  FAIL ") + rotulo)
    if not cond:
        FALHAS.append(rotulo)


def ler(caminho):
    """Lê com o espaço em branco normalizado — quebra de linha é diagramação."""
    if not os.path.exists(caminho):
        return ""
    return " ".join(open(caminho, encoding="utf-8").read().split())


def main():
    print("a skill existe e é invocável")
    check("o SKILL.md existe", os.path.exists(SKILL))
    texto = ler(SKILL)
    check("o nome no frontmatter é completude", "name: completude" in texto)
    check("o apelido que o dono digita está declarado",
          "o que falta pra fechar" in texto)

    print("ela roda o PROGRAMA, não o olho")
    check("o motor existe no disco", os.path.exists(MOTOR))
    check("a skill chama lib/completude.py", "lib/completude.py" in texto)
    check("a chamada usa a raiz do plugin instalado",
          "${CLAUDE_PLUGIN_ROOT}" in texto)
    check("o código de saída é o veredito", "código de saída" in texto)
    check("os caminhos saem do /doc-load, não de cor", "/doc-load" in texto)

    print("o sidecar de protótipo entra como 4º posicional (F13.9)")
    check("a chamada de exemplo passa o sidecar como 4º posicional",
          "<caminho>/.claude/docs/prototipo/<etapa>.prototipo.md" in texto)  # casa-ok: fixture de teste, o literal e o dado do caso
    check("a skill nomeia o argumento como sidecar de protótipo",
          "sidecar de protótipo" in texto)
    check("a lista do /doc-load cobre os quatro caminhos",
          "Os quatro caminhos saem do `/doc-load`" in texto)
    check("sidecar ausente não autoriza omitir o argumento",
          "passe o caminho mesmo assim" in texto)

    print("os DOIS lados aparecem, sempre")
    check("a apresentação tem seção própria",
          "## Como apresentar — os DOIS lados, sempre" in texto)
    check("lado 1 é a cadeia", "**Lado 1 — a cadeia**" in texto)
    check("lado 2 é a lei", "**Lado 2 — a lei**" in texto)
    check("lado limpo também aparece",
          "ele aparece dizendo que está limpo" in texto)
    for elo in ("feature → requisito", "requisito → tarefa", "tarefa → prova"):
        check("o elo %s é nomeado" % elo, elo in texto)
    check("o artigo sai com número E título", "6 · Estética" in texto)
    check("o artigo sem cobrador fica fora da conta",
          "fora da conta" in texto)
    check("documento ausente não vira verde",
          "não vira verde" in texto)

    print("o que falta é NOMEADO item a item")
    check("item sem nome não conta", "Item sem nome não conta" in texto)
    check("nada de porcentagem", "Nada de porcentagem" in texto)
    check("a skill mede e não conserta", "Não conserte nada aqui" in texto)

    print("a fronteira está escrita nos DOIS vizinhos")
    check("tem seção de fronteira", "## Fronteira" in texto)
    check("diz em que momento roda", "de alguém dizer \"pronto\"" in texto)
    check("aponta o /qa-loop", "Não é do `/qa-loop`" in texto)
    check("aponta o revisor de construção",
          "revisor de construção (OPUS #2 do `/sprint`)" in texto)

    print("o tripé é APONTADO, nunca repetido")
    check("a cópia vendorada do tripé está na pasta da skill",
          os.path.exists(TRIPE))
    check("a skill aponta para a cópia local",
          "references/dimensoes-de-revisao.md" in texto)
    # repetir os eixos é o defeito que F1.1 matou: se os títulos dos três pés
    # aparecem escritos aqui, a segunda cópia da prosa nasceu.
    for pe in ("Pé 1 · Qualidade", "Pé 3 · Coerência com a régua"):
        check("a skill não copia o eixo %r" % pe, pe not in texto)

    # A seção de racionalizações: a desculpa fica REFUTADA no texto antes de o
    # modelo dá-la. Sem cobrador, a próxima edição a apaga e ninguém percebe.
    print("as racionalizações estão refutadas por escrito")
    check("a skill tem a seção de racionalizações",
          "## Racionalizações" in texto)
    check("a desculpa da cadeia verde está refutada",
          "a cadeia está verde" in texto)
    check("a desculpa do arredondamento está refutada",
          "arredonda pra 100%" in texto)
    check("a desculpa do órfão irrelevante está refutada",
          "esses órfãos são irrelevantes" in texto)
    check("a desculpa de consertar de passagem está refutada",
          "já que estou aqui, conserto" in texto)

    print()
    if FALHAS:
        print("FALHOU: %d" % len(FALHAS))
        for f in FALHAS:
            print("  - " + f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
