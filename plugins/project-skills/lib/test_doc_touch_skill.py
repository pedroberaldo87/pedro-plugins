#!/usr/bin/env python3
"""A SKILL.md do doc-touch tem que mandar o fluxo pra casa VERSIONADA.

O defeito que isto impede: o passo 2b re-renderizava o diagrama de fluxo na pasta
de sessao (fora do git), e o dono decidiu em 2026-08-13 que fluxo e doc canonica —
mora em `.claude/docs/fluxos/` e entra no commit de conteudo. Sem esta suite, a
prosa do 2b poderia voltar calada pra pasta de sessao e o diagrama sumiria do
historico. (A test_stop_doc_touch.sh cobre OUTRO contrato — o hook de Stop.)
"""

import os

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "doc-touch", "SKILL.md")

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def secao(texto, inicio, fim):
    i = texto.find(inicio)
    if i < 0:
        return ""
    j = texto.find(fim, i)
    return texto[i:j if j > 0 else len(texto)]


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()
    passo_2b = secao(texto, "### 2b ", "### 3 ")
    passo_5 = secao(texto, "### 5 ", "## Invariantes")

    print("o passo 2b existe e liga doc re-projetado a diagrama")
    check("o passo 2b existe", bool(passo_2b))
    check("runtime.md dispara os fluxo-<slug>.html",
          "`runtime.md`" in passo_2b and "fluxo-<slug>.html" in passo_2b)

    print("o fluxo re-renderiza na casa versionada, nunca em pasta de sessao")
    check("o destino do fluxo e .claude/docs/fluxos/",
          ".claude/docs/fluxos/" in passo_2b)
    check("a casa e nomeada como versionada",
          "VERSIONADA" in passo_2b or "versionada" in passo_2b)
    check("o comando resolve o destino com subdir docs/fluxos",
          "resolve-dir.sh" in passo_2b and "docs/fluxos" in passo_2b)
    check("a prosa proibe a pasta de sessao pro fluxo",
          "nunca em pasta de sess" in passo_2b)
    check("a regua do repo publico cobre o HTML versionado",
          "sem caminho absoluto de m" in passo_2b)

    # R-24 (F14.4): a ARQUITETURA visual e canonica pelo mesmo caminho do fluxo.
    # Sem este check o organismo voltava pra pasta de sessao e morria no /clear —
    # dois destinos pro mesmo tipo de artefato e' a divergencia que o cobrador mata.
    print("o organismo re-renderiza na MESMA casa versionada do fluxo")
    check("architecture.md dispara o organismo.html",
          "`architecture.md`" in passo_2b and "organismo.html" in passo_2b)
    check("o organismo tem o mesmo destino versionado do fluxo",
          '"$FLUXOS_DIR/organismo.html"' in passo_2b)
    check("nenhum comando manda o organismo pra pasta de sessao",
          "ARCHIFY_DIR/organismo.html" not in passo_2b)

    print("o passo 5 leva o fluxo re-renderizado pro commit de conteudo")
    check("o passo 5 existe", bool(passo_5))
    check("o git add do conteudo inclui .claude/docs/fluxos/",
          ".claude/docs/fluxos/" in passo_5)

    print()
    if FAILS:
        print("%d FALHA(S):" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        raise SystemExit(1)
    print("TODOS OS TESTES PASSARAM")


if __name__ == "__main__":
    main()
