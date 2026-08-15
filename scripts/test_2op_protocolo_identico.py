#!/usr/bin/env python3
"""O protocolo de resposta é o MESMO nos três comandos do 2op.

Por que este teste existe. As três skills (`/2op`, `/2op-opus`, `/2op-sonnet`) são o
mesmo comando apontando para famílias de modelo diferentes: só o frontmatter e o nome
da família mudam. Da linha `## Como responder` em diante o texto é idêntico letra por
letra — e nada no repositório comparava as três cópias.

O modo de falha é silencioso e já aconteceu com código neste projeto: alguém acrescenta
uma regra de resposta em um arquivo, os outros dois ficam com a regra velha, e ninguém
vê. Para código a resposta foi `_shared/` mais `scripts/sync-shared.sh --check`; aqui
são três arquivos de 36 linhas, então a resposta mais barata é comparar e reprovar.

O que ele NÃO cobre: o cabeçalho e a abertura, que mudam de propósito — cada arquivo
nomeia a família que pede (`fable`, `opus`, `sonnet`) e a própria barra.

A seção de reconciliação é a exceção declarada, e por isso fecha o bloco comum: as
quatro classes com que o revisor fecha (CONFIRMA · REFUTA · AMPLIA · EMPATA) estão
escritas uma vez só, na skill `2op`, e as duas variantes apontam para lá em vez de
repetir. O teste cobra os dois lados — o texto na titular, o ponteiro nas variantes.

    python3 scripts/test_2op_protocolo_identico.py
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
SKILLS = ["2op", "2op-opus", "2op-sonnet"]
MARCO = "## Como responder"
FIM = "## Reconciliação"
TEATRO = "## Teatro de dúvida"
CLASSES = ["CONFIRMA", "REFUTA", "AMPLIA", "EMPATA"]
FALHAS = []


def texto(nome):
    caminho = os.path.join(ROOT, "plugins", "2op", "skills", nome, "SKILL.md")
    with open(caminho, encoding="utf-8") as fh:
        return (caminho, fh.read())


def protocolo(nome):
    """O bloco comum: de `## Como responder` até a seção de reconciliação."""
    caminho, txt = texto(nome)
    i = txt.find(MARCO)
    if i < 0:
        return (caminho, None)
    j = txt.find(FIM, i)
    return (caminho, txt[i:] if j < 0 else txt[i:j])


def reconciliacao(nome):
    """A seção de reconciliação, do cabeçalho dela até o fim do arquivo."""
    caminho, txt = texto(nome)
    i = txt.find(FIM)
    return (caminho, None if i < 0 else txt[i:])


def cobra_reconciliacao():
    for nome in SKILLS:
        caminho, secao = reconciliacao(nome)
        if secao is None:
            FALHAS.append("%s não tem a seção `%s`" % (caminho, FIM))
            continue
        if nome == SKILLS[0]:
            faltando = [c for c in CLASSES if "**%s**" % c not in secao]
            if faltando:
                FALHAS.append("%s não nomeia em negrito: %s"
                              % (caminho, ", ".join(faltando)))
            else:
                print("  ok   %s escreve as quatro classes: %s"
                      % (nome, " · ".join(CLASSES)))
            # cada classe vem com a conduta, não só o nome
            for c in CLASSES:
                linha = [ln for ln in secao.splitlines() if "**%s**" % c in ln]
                if linha and "—" not in linha[0]:
                    FALHAS.append("%s: a classe %s não diz o que fazer (falta o travessão)"
                                  % (caminho, c))
            continue
        # variante: aponta, não repete
        faltando = [c for c in CLASSES if c not in secao]
        if faltando:
            FALHAS.append("%s não cita as quatro classes: falta %s"
                          % (caminho, ", ".join(faltando)))
        elif "skills/2op/SKILL.md" not in secao:
            FALHAS.append("%s cita as classes mas não aponta para a skill titular"
                          % caminho)
        elif len(secao.splitlines()) > 8:
            FALHAS.append("%s repetiu o protocolo em vez de apontar (%d linhas)"
                          % (caminho, len(secao.splitlines())))
        else:
            print("  ok   %s aponta para a skill titular, sem repetir" % nome)


def cobra_teatro():
    """O sinal de teatro de dúvida — nome + conduta — mora na titular, e as
    variantes apontam. Sem NOME o padrão não é reconhecível na hora: o revisor
    solta a terceira ressalva achando que está sendo rigoroso."""
    caminho, txt = texto(SKILLS[0])
    i = txt.find(TEATRO)
    secao = "" if i < 0 else txt[i:]
    if not secao:
        FALHAS.append("%s não tem a seção `%s`" % (caminho, TEATRO))
        return
    if "segundo `/2op`" not in secao or "acionável" not in secao:
        FALHAS.append("%s não define o sinal (segundo 2op, ressalva, zero acionável)"
                      % caminho)
    elif "validação fantasiada de revisão" not in secao:
        FALHAS.append("%s não nomeia o que o padrão é de verdade" % caminho)
    elif "primeira linha" not in secao or "CONCORDO" not in secao:
        FALHAS.append("%s nomeia o sinal mas não escreve a conduta" % caminho)
    else:
        print("  ok   2op nomeia o teatro de dúvida e escreve a conduta")
    for nome in SKILLS[1:]:
        _, rec = reconciliacao(nome)
        if rec is None or "Teatro de" not in rec:
            FALHAS.append("plugins/2op/skills/%s/SKILL.md não aponta para o "
                          "Teatro de dúvida da titular" % nome)
        else:
            print("  ok   %s aponta para o teatro de dúvida" % nome)


def main():
    blocos = {}
    for nome in SKILLS:
        caminho, bloco = protocolo(nome)
        if bloco is None:
            FALHAS.append("%s não tem a linha `%s`" % (caminho, MARCO))
            continue
        blocos[nome] = bloco
        print("  ok   %s tem o bloco de protocolo (%d linhas)"
              % (nome, bloco.count("\n") + 1))

    distintos = set(blocos.values())
    if len(blocos) == len(SKILLS) and len(distintos) == 1:
        print("  ok   os três protocolos são idênticos letra por letra")
    elif blocos:
        FALHAS.append("os protocolos divergiram: %d versões diferentes entre %s"
                      % (len(distintos), ", ".join(sorted(blocos))))
        base = blocos[SKILLS[0]].splitlines()
        for nome in SKILLS[1:]:
            if nome not in blocos:
                continue
            outro = blocos[nome].splitlines()
            for n, (a, b) in enumerate(zip(base, outro), 1):
                if a != b:
                    print("  FAIL %s difere de %s na linha %d do bloco:\n"
                          "         %s: %s\n         %s: %s"
                          % (nome, SKILLS[0], n, SKILLS[0], a.strip(),
                             nome, b.strip()))
                    break
            else:
                if len(base) != len(outro):
                    print("  FAIL %s tem %d linhas no bloco, %s tem %d"
                          % (nome, len(outro), SKILLS[0], len(base)))

    cobra_reconciliacao()
    cobra_teatro()

    if FALHAS:
        print("\nPROTOCOLO DIVERGENTE: " + " · ".join(FALHAS))
        print("Conserte editando os TRÊS arquivos, ou mude este teste de propósito.")
        return 1
    print("\no protocolo de resposta do 2op é um só, nas três cópias")
    return 0


if __name__ == "__main__":
    sys.exit(main())
