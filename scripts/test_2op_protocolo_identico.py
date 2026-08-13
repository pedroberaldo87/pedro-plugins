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

    python3 scripts/test_2op_protocolo_identico.py
"""

import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
SKILLS = ["2op", "2op-opus", "2op-sonnet"]
MARCO = "## Como responder"
FALHAS = []


def protocolo(nome):
    """O bloco comum: de `## Como responder` até o fim do arquivo."""
    caminho = os.path.join(ROOT, "plugins", "2op", "skills", nome, "SKILL.md")
    with open(caminho, encoding="utf-8") as fh:
        txt = fh.read()
    i = txt.find(MARCO)
    return (caminho, None if i < 0 else txt[i:])


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

    if FALHAS:
        print("\nPROTOCOLO DIVERGENTE: " + " · ".join(FALHAS))
        print("Conserte editando os TRÊS arquivos, ou mude este teste de propósito.")
        return 1
    print("\no protocolo de resposta do 2op é um só, nas três cópias")
    return 0


if __name__ == "__main__":
    sys.exit(main())
