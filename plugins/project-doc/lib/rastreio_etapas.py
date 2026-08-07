#!/usr/bin/env python3
"""rastreio_etapas.py — o que as etapas aprovadas deixaram sem dono.

Duas pontas soltas nascem sozinhas na concepção, e nenhuma delas dói na hora:

  1. **funcionalidade sem origem** — item de `features.md` que não aponta a jornada,
     a meta ou a peça aprovada que o pediu. É ideia que entrou pela janela;
  2. **jornada sem funcionalidade** — jornada aprovada em `journeys.md` que nenhum
     item de `features.md` realiza. É percurso que ninguém constrói.

Este programa só CONTA. Ele lê os dois documentos, devolve as duas listas em JSON e
não escreve em lugar nenhum — quem fecha a etapa é o dono, e conferência que altera
documento aprovado reabriria a etapa pela marca (`approved-sig`).

Os formatos que ele lê são os moldes do
`skills/start-doc/references/authorial-kit.md` (documentos 8 e 9):

    journeys.md   ## {nome da jornada}
    features.md   ### F-{n} · {nome}
                  - **Origem:** {jornada · meta · peça · decisão do dono}

Uso:
    python3 rastreio_etapas.py <dir com os .claude/docs, ou o próprio .claude/docs>

stdlib only (requisito do repo).
"""

import json
import os
import re
import sys
import unicodedata

FEATURES = "features.md"
JOURNEYS = "journeys.md"

_ITEM = re.compile(r"^###\s+(.+?)\s*$")
_JORNADA = re.compile(r"^##\s+(.+?)\s*$")
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


def conferir(docs_dir):
    """As duas listas do que ficou sem dono. Nada é escrito."""
    fpath = os.path.join(docs_dir, FEATURES)
    jpath = os.path.join(docs_dir, JOURNEYS)
    out = {
        "docs": docs_dir,
        "features_lidas": os.path.exists(fpath),
        "journeys_lidas": os.path.exists(jpath),
        "funcionalidades_sem_origem": [],
        "jornadas_sem_funcionalidade": [],
    }

    itens = funcionalidades(_ler(fpath)) if out["features_lidas"] else []
    nomes = jornadas(_ler(jpath)) if out["journeys_lidas"] else []

    for it in itens:
        if _VAZIO.match(it["origem"].strip()):
            out["funcionalidades_sem_origem"].append(it["nome"])

    corpo = _norm("\n".join(it["bloco"] + "\n" + it["nome"] for it in itens))
    for nome in nomes:
        if _norm(nome) not in corpo:
            out["jornadas_sem_funcionalidade"].append(nome)

    out["contagem"] = {
        "funcionalidades": len(itens),
        "jornadas": len(nomes),
        "funcionalidades_sem_origem": len(out["funcionalidades_sem_origem"]),
        "jornadas_sem_funcionalidade": len(out["jornadas_sem_funcionalidade"]),
    }
    out["sem_dono"] = (out["contagem"]["funcionalidades_sem_origem"]
                       + out["contagem"]["jornadas_sem_funcionalidade"])
    return out


def resolver(caminho):
    """Aceita a raiz do projeto ou o próprio `.claude/docs`."""
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
