#!/usr/bin/env python3
"""A SKILL.md do /doc tem que OFERECER a migracao da casa da doc (F15.8).

O defeito que isto impede: projeto com a doc na casa velha (`.claude/docs/`, sem
`docs/` na raiz) rodava o /doc e seguia calado — a casa antiga se perpetuava, e o
dono nunca via a oferta. A decisao dele (2026-08-16) foi migrar todos, cada um
quando o /doc rodar nele e ele aceitar — pergunta por AskUserQuestion, com o
de-para visivel. Sem esta suite, o passo pode sumir da prosa sem ninguem notar.
"""

import os

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "doc", "SKILL.md")

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()
    i = texto.find("1b. ")
    passo = texto[i:texto.find("\n2. ", i)] if i >= 0 else ""

    print("o passo da casa da doc existe dentro do Process (F15.8)")
    check("o passo 1b esta no Process, logo depois de identificar a raiz", bool(passo))
    check("ele nomeia a casa antiga e a casa nova",
          ".claude/docs/" in passo and "docs/" in passo)

    print("a deteccao pergunta ao resolvedor, nunca a caminho cravado")
    check("o resolvedor Python e nomeado", "casa_da_doc.py" in passo)
    check("a proibicao do caminho cravado esta escrita",
          "nunca caminho cravado" in passo)

    print("a oferta chega por AskUserQuestion, com o de-para visivel")
    check("a pergunta e AskUserQuestion", "AskUserQuestion" in passo)
    check("o de-para vai visivel na opcao", "de-para" in passo and "preview" in passo)
    check("as duas saidas existem: migrar e ficar como esta",
          "migrar agora" in passo and "ficar como está" in passo)
    check("nada se move sem o dono responder",
          "nada se move" in passo)

    print("\n%d check(s), %d falha(s)" % (8, len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
