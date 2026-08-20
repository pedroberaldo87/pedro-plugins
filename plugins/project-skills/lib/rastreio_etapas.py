#!/usr/bin/env python3
"""rastreio_etapas.py — o que as etapas aprovadas deixaram sem dono.

As pontas soltas nascem sozinhas na concepção, e nenhuma delas dói na hora:

  1. **funcionalidade sem origem** — item de `features.md` que não aponta a jornada,
     a meta ou a peça aprovada que o pediu. É ideia que entrou pela janela;
  2. **jornada sem funcionalidade** — jornada aprovada em `journeys.md` que nenhum
     item de `features.md` realiza. É percurso que ninguém constrói;
  3. **passo do desenho sem funcionalidade** — passo do ciclo de `blueprint.md` que
     nenhum item de `features.md` atende. É desenho acordado que ninguém constrói.

Este programa só CONTA. Ele lê `features.md`, `journeys.md` e `blueprint.md`, devolve
a lista de funcionalidade sem origem, a de jornada sem funcionalidade e a de passo do
desenho sem funcionalidade em JSON e não escreve em lugar nenhum — quem fecha a etapa
é o dono, e conferência que altera
documento aprovado reabriria a etapa pela marca (`approved-sig`).

Os formatos que ele lê são os moldes do
`skills/start/references/authorial-kit.md` (documentos 8, 9 e 10):

    journeys.md   ## {nome da jornada}
    features.md   ### F-{n} · {nome}
                  - **Origem:** {jornada · meta · peça · decisão do dono}
    blueprint.md  ## O ciclo, do começo ao fim
                  1. {o que acontece}  ← {arquivo}:{linha}

A régua do passo é a mesma da jornada: a funcionalidade que o atende **cita a passagem
verbatim** (é a regra do kit — toda linha aponta a passagem que a originou), então passo
cujo texto não aparece em `features.md` é passo que ninguém pegou.

Uso:
    python3 rastreio_etapas.py <a raiz do projeto, ou a própria casa da doc>

stdlib only (requisito do repo).
"""

import json
import os
import re
import sys
import unicodedata

FEATURES = "features.md"
JOURNEYS = "journeys.md"
BLUEPRINT = "blueprint.md"

_ITEM = re.compile(r"^###\s+(.+?)\s*$")
_JORNADA = re.compile(r"^##\s+(.+?)\s*$")
_PASSO = re.compile(r"^\s*\d+[.)]\s+(.+?)\s*$")
# O molde do blueprint (documento 10) começa o ciclo nesta seção.
_CICLO = "o ciclo"
_ORIGEM = re.compile(r"^\s*[-*]\s+\*\*Origem:\*\*\s*(.*)$")
# Placeholder do molde (`{jornada de ...}`) e lacuna declarada não são origem.
_VAZIO = re.compile(r"^(\[PENDENTE\]|\{.*\}|—|-|)$")


def _norm(txt):
    """Minúscula, sem acento, espaço colapsado — para comparar nome de jornada."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", txt)
                         if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.lower().split())


def _ler(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def _sem_frontmatter(texto):
    if texto.startswith("---"):
        fim = texto.find("\n---", 3)
        if fim >= 0:
            return texto[fim + 4:]
    return texto


def funcionalidades(texto):
    """[{'nome', 'origem', 'bloco'}] — um por `### ...` do corpo de features.md.

    A seção "Deixado de fora de propósito" usa bullet, não `###`: o que ficou de
    fora de propósito tem dono (a decisão do dono) e não é pendência.
    """
    itens = []
    atual = None
    for linha in _sem_frontmatter(texto).splitlines():
        m = _ITEM.match(linha)
        if m:
            atual = {"nome": m.group(1).strip(), "origem": "", "bloco": []}
            itens.append(atual)
            continue
        if linha.startswith("## "):
            atual = None
            continue
        if atual is None:
            continue
        atual["bloco"].append(linha)
        mo = _ORIGEM.match(linha)
        if mo and not atual["origem"]:
            atual["origem"] = mo.group(1).strip()
    for it in itens:
        it["bloco"] = "\n".join(it["bloco"])
    return itens


def jornadas(texto):
    """[nome] — um por `## ...` do corpo de journeys.md."""
    nomes = []
    for linha in _sem_frontmatter(texto).splitlines():
        if linha.startswith("### "):
            continue
        m = _JORNADA.match(linha)
        if m:
            nomes.append(m.group(1).strip())
    return nomes


def passos(texto):
    """[texto do passo] — um por item numerado da seção "O ciclo, do começo ao fim".

    A proveniência (`← arquivo:linha`) fica de fora: ela aponta de onde o passo veio,
    não o que ele é.
    """
    lista = []
    dentro = False
    for linha in _sem_frontmatter(texto).splitlines():
        if linha.startswith("## "):
            dentro = _norm(linha[3:]).startswith(_CICLO)
            continue
        if not dentro:
            continue
        m = _PASSO.match(linha)
        if m:
            lista.append(m.group(1).split("←")[0].strip())
    return lista


def conferir(docs_dir):
    """Funcionalidade sem origem, jornada sem funcionalidade e passo do desenho sem
    funcionalidade — o que ficou sem dono. Nada é escrito."""
    fpath = os.path.join(docs_dir, FEATURES)
    jpath = os.path.join(docs_dir, JOURNEYS)
    bpath = os.path.join(docs_dir, BLUEPRINT)
    out = {
        "docs": docs_dir,
        "features_lidas": os.path.exists(fpath),
        "journeys_lidas": os.path.exists(jpath),
        "blueprint_lidas": os.path.exists(bpath),
        "funcionalidades_sem_origem": [],
        "jornadas_sem_funcionalidade": [],
        "passos_sem_funcionalidade": [],
    }

    itens = funcionalidades(_ler(fpath)) if out["features_lidas"] else []
    nomes = jornadas(_ler(jpath)) if out["journeys_lidas"] else []
    ciclo = passos(_ler(bpath)) if out["blueprint_lidas"] else []

    for it in itens:
        if _VAZIO.match(it["origem"].strip()):
            out["funcionalidades_sem_origem"].append(it["nome"])

    corpo = _norm("\n".join(it["bloco"] + "\n" + it["nome"] for it in itens))
    for nome in nomes:
        if _norm(nome) not in corpo:
            out["jornadas_sem_funcionalidade"].append(nome)
    for passo in ciclo:
        if _norm(passo) not in corpo:
            out["passos_sem_funcionalidade"].append(passo)

    out["contagem"] = {
        "funcionalidades": len(itens),
        "jornadas": len(nomes),
        "passos": len(ciclo),
        "funcionalidades_sem_origem": len(out["funcionalidades_sem_origem"]),
        "jornadas_sem_funcionalidade": len(out["jornadas_sem_funcionalidade"]),
        "passos_sem_funcionalidade": len(out["passos_sem_funcionalidade"]),
    }
    out["sem_dono"] = (out["contagem"]["funcionalidades_sem_origem"]
                       + out["contagem"]["jornadas_sem_funcionalidade"]
                       + out["contagem"]["passos_sem_funcionalidade"])
    return out


def resolver(caminho):
    """Aceita a raiz do projeto ou a própria casa da doc."""
    caminho = os.path.abspath(caminho or ".")
    dentro = os.path.join(caminho, ".claude", "docs")
    return dentro if os.path.isdir(dentro) else caminho


def main(argv):
    if len(argv) > 2 or (len(argv) == 2 and argv[1] in ("-h", "--help")):
        print(__doc__)
        return 2
    docs = resolver(argv[1] if len(argv) == 2 else ".")
    print(json.dumps(conferir(docs), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
