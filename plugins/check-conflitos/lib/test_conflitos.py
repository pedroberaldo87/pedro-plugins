#!/usr/bin/env python3
"""Bancada do varredor de conflitos. Cada caso reproduz um atropelo real medido.

    python3 test_conflitos.py     # verde = 0
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import conflitos as C  # noqa: E402

FALHAS = []
TOTAL = [0]


def check(nome, cond):
    TOTAL[0] += 1
    print("  %s   %s" % ("ok " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def monta(raiz, arvore):
    """arvore = {"market/plugin/versao": {"skills": {...}, "hooks_json": {...}}}

    `hooks_json` é o CONTEÚDO INTEIRO do arquivo, com o embrulho `{"hooks": …}` que o
    Claude Code exige. A primeira versão desta bancada chamava a chave de `hooks` e
    gravava o valor cru — o arquivo saía sem o embrulho, o varredor lia zero hook, e o
    caso vermelho acusava o programa por um defeito que era da bancada.
    """
    for caminho, conteudo in arvore.items():
        base = os.path.join(raiz, *caminho.split("/"))
        for nome, desc in (conteudo.get("skills") or {}).items():
            d = os.path.join(base, "skills", nome)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
                fh.write("---\nname: %s\ndescription: %s\n---\n\n# %s\n"
                         % (nome, desc, nome))
        hk = conteudo.get("hooks_json")
        if hk is not None:
            d = os.path.join(base, "hooks")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "hooks.json"), "w", encoding="utf-8") as fh:
                json.dump(hk, fh)
        os.makedirs(base, exist_ok=True)


def com_script(raiz, caminho, corpo):
    f = os.path.join(raiz, *caminho.split("/"))
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write(corpo)
    return f


def main():
    print("varredor de conflitos — bancada\n")

    # ── 1 · SÓ A VERSÃO MAIS ALTA CONTA ──────────────────────────────────────
    # A varredura ingênua lia TODA versão do cache e contava a mesma colisão
    # dezoito vezes: o `bootstrap` sozinho tinha 17 versões paradas no disco.
    d = tempfile.mkdtemp(prefix="confl-ver-")
    try:
        monta(d, {"mkt/alfa/1.0.0": {"skills": {"x": "um"}},
                  "mkt/alfa/1.10.0": {"skills": {"x": "dez"}},
                  "mkt/alfa/1.9.0": {"skills": {"x": "nove"}}})
        inst = C.instalados(d)
        check("a versão que roda é a mais alta, e 1.10 > 1.9",
              inst[("mkt", "alfa")]["versao"] == "1.10.0")
        check("as paradas são contadas à parte",
              sorted(inst[("mkt", "alfa")]["outras"]) == ["1.0.0", "1.9.0"])
        check("a skill aparece UMA vez, não uma por versão",
              len(C.skills(inst)) == 1)
        r = C.varre(inst)
        check("cache inchado vira achado próprio", len(r["cache_inchado"]) == 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 2 · NOME REPETIDO ────────────────────────────────────────────────────
    d = tempfile.mkdtemp(prefix="confl-nome-")
    try:
        monta(d, {"mkt/alfa/1.0.0": {"skills": {"setup": "configura o alfa"}},
                  "mkt/beta/1.0.0": {"skills": {"setup": "configura o beta"}},
                  "outro/gama/1.0.0": {"skills": {"unico": "sozinho"}}})
        r = C.varre(C.instalados(d))
        check("duas skills com o mesmo nome são acusadas",
              len(r["nome_repetido"]) == 1 and r["nome_repetido"][0]["nome"] == "setup")
        check("nome único não é acusado",
              all(n["nome"] != "unico" for n in r["nome_repetido"]))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 3 · PALAVRA INTEIRA, NUNCA PEDAÇO DE OUTRA ───────────────────────────
    # A primeira varredura casou "ui" dentro de "constrUI" e devolveu 37 skills
    # como se todas fizessem interface. Falso positivo em massa mata o relatório.
    check("'ui' NÃO casa dentro de construir",
          not C._cita("a skill que vai construir o plano", "ui"))
    check("'ui' casa quando é a palavra",
          C._cita("desenha a ui do aplicativo", "ui"))
    check("'test' NÃO casa dentro de conteste",
          not C._cita("ninguém conteste isso", "test"))
    check("palavra com acento antes não abre fronteira falsa",
          not C._cita("a produção parou", "ução"))

    # ── 4 · SÓ CONTA EVENTO COM MAIS DE UM MARKETPLACE ───────────────────────
    # Dois hooks MEUS no mesmo evento não são conflito: é desenho. O que interessa
    # é quando a origem é diferente e ninguém combinou nada.
    d = tempfile.mkdtemp(prefix="confl-ev-")
    try:
        def H(s):
            return {"hooks_json": {"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": s}]}]}}}
        monta(d, {"mkt/alfa/1.0.0": H("bash ${CLAUDE_PLUGIN_ROOT}/hooks/a.sh"),
                  "mkt/beta/1.0.0": H("bash ${CLAUDE_PLUGIN_ROOT}/hooks/b.sh")})
        r = C.varre(C.instalados(d))
        check("mesmo marketplace no mesmo evento NÃO é conflito",
              not r["evento_disputado"])
        monta(d, {"outro/gama/1.0.0": H("bash ${CLAUDE_PLUGIN_ROOT}/hooks/c.sh")})
        r = C.varre(C.instalados(d))
        check("marketplaces diferentes no mesmo evento É conflito",
              len(r["evento_disputado"]) == 1
              and r["evento_disputado"][0]["evento"] == "Stop")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 5 · QUEM BARRA É LIDO DO SCRIPT, NÃO DO NOME ─────────────────────────
    # `handoff-completeness-gate` tem nome de portão e NÃO barra; `askq-humanize`
    # não tem, e barra. Julgar pelo nome erraria nos dois.
    d = tempfile.mkdtemp(prefix="confl-barra-")
    try:
        mudo = com_script(d, "s/mudo.sh", "#!/bin/sh\necho oi\nexit 0\n")
        duro = com_script(d, "s/duro.sh", '#!/bin/sh\nprintf \'{"permissionDecision":"deny"}\'\n')
        check("script que só fala não é marcado como barra", not C._barra(mudo))
        check("script que devolve recusa é marcado", C._barra(duro))
        check("caminho inexistente não estoura", not C._barra(os.path.join(d, "nao-existe")))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # ── 6 · CACHE AUSENTE NÃO ESTOURA ────────────────────────────────────────
    check("cache que não existe devolve vazio, sem exceção",
          C.instalados("/caminho/que/nao/existe") == {})

    print("\n%d checagem(ns) · %d falha(s)" % (TOTAL[0], len(FALHAS)))
    for f in FALHAS:
        print("   FALHOU: %s" % f)
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main())
