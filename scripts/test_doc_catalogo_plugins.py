#!/usr/bin/env python3
"""A tabela de plugins que architecture.md publica bate com o disco, linha a linha.

Por que existe (2026-08-13). O `--touch-plan` decide o que re-projetar comparando a
data do doc com a data dos arquivos do `scope:`. Isso responde *quando*, e o defeito
é *o quê*: duas sessões commitando em sequência produzem um doc carimbado DEPOIS do
commit da outra sem nunca tê-lo lido, e a partir daí ele sai do `pending_docs` e vira
invisível. Medido: `architecture.md` saiu com `already_current=True` publicando
`bootstrap 1.17.10` e `check-skills 0.7.2` contra `1.17.11` e `0.7.3` no disco, e sem
a linha do `2op`, que já existia.

Nenhum critério temporal fecha essa porta — nem trocar a data pelo `generated-commit:`,
porque um doc carimbado no commit certo pode ter a tabela errada do mesmo jeito. O que
fecha é reler a saída do comando que o próprio doc publica logo acima da tabela.

Irmão de `scripts/test_doc_vendoring_counts.py`, com uma diferença que a tabela impõe:
lá se cobram frases literais de um parágrafo; aqui são 22 linhas que mudam a cada bump,
então a comparação é linha a linha e a falha nomeia QUAL plugin divergiu — teste que só
diz "não bate" é teste que ninguém sabe consertar.

    python3 scripts/test_doc_catalogo_plugins.py
"""

import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(RAIZ, ".claude", "docs", "architecture.md")
ABERTURA = "Saída desta rodada (nome · versão · skills · tem hook):"
FALHAS = []


def do_disco():
    """{plugin: (version, [skills], tem_hook)} — o equivalente ao comando do doc."""
    fora = {}
    base = os.path.join(RAIZ, "plugins")
    for nome in sorted(os.listdir(base)):
        manifesto = os.path.join(base, nome, ".claude-plugin", "plugin.json")
        if not os.path.exists(manifesto):
            continue
        with open(manifesto, encoding="utf-8") as fh:
            versao = json.load(fh).get("version")
        pasta = os.path.join(base, nome, "skills")
        # só DIRETÓRIO é skill — o `ls -1d */` do comando publicado ignora arquivo solto
        skills = sorted(n for n in os.listdir(pasta)
                        if os.path.isdir(os.path.join(pasta, n))) \
            if os.path.isdir(pasta) else []
        hook = os.path.exists(os.path.join(base, nome, "hooks", "hooks.json"))
        fora[nome] = (versao, skills, hook)
    return fora


def do_doc():
    """{plugin: (version, [skills], tem_hook)} lido do bloco publicado. Erro → None."""
    with open(DOC, encoding="utf-8") as fh:
        texto = fh.read()
    i = texto.find(ABERTURA)
    if i < 0:
        FALHAS.append("architecture.md não tem a linha `%s`" % ABERTURA)
        return None
    abre = texto.find("```", i)
    fecha = texto.find("```", abre + 3)
    if abre < 0 or fecha < 0:
        FALHAS.append("o bloco da tabela não fecha com ``` em architecture.md")
        return None
    fora = {}
    linha_re = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]*)\]\s*(HOOKS|-)?\s*$")
    for linha in texto[abre + 3:fecha].strip("\n").splitlines():
        if not linha.strip():
            continue
        m = linha_re.match(linha)
        if not m:
            FALHAS.append("linha da tabela fora do formato: %r" % linha[:70])
            continue
        nome, versao, skills, hook = m.groups()
        fora[nome] = (versao,
                      [s for s in skills.split(",") if s],
                      hook == "HOOKS")
    return fora


def descreve(v):
    versao, skills, hook = v
    return "%s [%s] %s" % (versao, ",".join(skills), "HOOKS" if hook else "-")


def conserta(disco):
    """--fix: reescreve o bloco publicado com o que está no disco AGORA.

    Existe porque a mesma falha matou três corridas do /sprint: quem bumpa a versão
    lembra do plugin.json e do marketplace.json, esquece a tabela, e a esteira fica
    vermelha para todo mundo. Quem sabe montar a tabela é este arquivo — pedir para
    o autor rodar o comando na mão e colar a saída era pedir o passo que ele acabou
    de esquecer.
    """
    with open(DOC, encoding="utf-8") as fh:
        texto = fh.read()
    i = texto.find(ABERTURA)
    abre = texto.find("```", i)
    fecha = texto.find("```", abre + 3)
    if i < 0 or abre < 0 or fecha < 0:
        print("não achei o bloco da tabela em architecture.md — conserte à mão")
        return 1
    # o espaço fora do `%-28s` é o que separa lista de skills longa do HOOKS: com o
    # preenchimento sozinho, a lista que estoura a coluna cola no marcador
    linhas = ["%-18s%7s  %-28s %s" % (nome, v[0], "[%s]" % ",".join(v[1]),
                                      "HOOKS" if v[2] else "-")
              for nome, v in sorted(disco.items())]
    novo = texto[:abre + 3] + "\n" + "\n".join(l.rstrip() for l in linhas) \
        + "\n" + texto[fecha:]
    with open(DOC, "w", encoding="utf-8") as fh:
        fh.write(novo)
    print("tabela reescrita com os %d plugins do disco" % len(disco))
    return 0


def main():
    disco = do_disco()
    if "--fix" in sys.argv:
        return conserta(disco)
    doc = do_doc()
    if doc is None:
        print("\n".join("  FAIL " + f for f in FALHAS))
        print("\nCATÁLOGO ILEGÍVEL: " + " · ".join(FALHAS))
        return 1

    print("  ok   a tabela foi lida: %d linha(s) no doc, %d plugin(s) no disco"
          % (len(doc), len(disco)))

    for nome in sorted(set(disco) | set(doc)):
        if nome not in doc:
            FALHAS.append("%s existe no disco e não está na tabela" % nome)
            print("  FAIL %s: no disco (%s), ausente da tabela" % (nome, descreve(disco[nome])))
        elif nome not in disco:
            FALHAS.append("%s está na tabela e não existe no disco" % nome)
            print("  FAIL %s: na tabela (%s), ausente do disco" % (nome, descreve(doc[nome])))
        elif disco[nome] != doc[nome]:
            FALHAS.append("%s divergiu" % nome)
            print("  FAIL %s:\n         doc:   %s\n         disco: %s"
                  % (nome, descreve(doc[nome]), descreve(disco[nome])))

    if FALHAS:
        print("\nCATÁLOGO DEFASADO em: " + ", ".join(FALHAS))
        print("Conserte com `python3 scripts/test_doc_catalogo_plugins.py --fix`, que\n"
              "reescreve o bloco com o disco de agora — é o mesmo comando que\n"
              "architecture.md publica logo acima da tabela, sem a colagem na mão.")
        return 1
    print("  ok   os %d plugins batem em version, skills e hook" % len(disco))
    print("\na tabela de architecture.md é a saída do comando que ela mesma publica")
    return 0


if __name__ == "__main__":
    sys.exit(main())
