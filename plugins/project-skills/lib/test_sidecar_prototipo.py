#!/usr/bin/env python3
"""Bancada do FORMATO do sidecar de protótipo (lei: .claude/docs/prototipo/FORMATO.md).

O formato é a fundação: nasce definido e com cobrador ANTES de qualquer consumidor. Aqui o
exemplo escrito no FORMATO é MONTADO num diretório temporário e conferido de verdade — campo a
campo, casa por casa, e a marca do conjunto contra o `cat | cksum` que a spec promete.

A marca do conjunto é o `cksum` POSIX da emenda dos arquivos listados, na ordem do corpo.
Duas receitas para o mesmo número dariam duas respostas, então a de Python é conferida
contra o shell de verdade (quando há um bash que responde).
"""

import importlib.util
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from bash_posix import bash_posix  # noqa: E402
# Fingir o lar é receita única (_shared/lar-fingido.md): trocar só HOME deixa o filho
# escrever no lar REAL no Windows, que lê USERPROFILE primeiro.
from lar_fingido import ambiente  # noqa: E402

spec = importlib.util.spec_from_file_location("doc_load", os.path.join(AQUI, "doc_load.py"))
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)

CASA = ".claude/docs/prototipo/"
CAMPOS = ("natureza", "anexo-de", "design-sig", "status", "conjunto-sig", "marcador-ficticio")
# A parte NORMATIVA do formato mora sob `.claude/docs/`, que o clone RECEBE — a spec de
# concepção fica em `.claude/specs/`, que o .gitignore não rastreia, e ali o cobrador não
# teria o que ler no CI.
FORMATO = os.path.join(AQUI, os.pardir, os.pardir, os.pardir,
                       ".claude", "docs", "prototipo", "FORMATO.md")

SIDECAR = """---
natureza: anexo
anexo-de: design.md
design-sig: 1836471203
status: approved
conjunto-sig: {sig}
marcador-ficticio: FICTICIO
---

## Arquivos

- .claude/docs/prototipo/painel.html
- .claude/docs/prototipo/entrada.html

## Superfícies

- Painel do dia — jornada: acompanhar a obra — procedência: blueprint.md §3
- Entrada de pedido — jornada: registrar um pedido — procedência: blueprint.md §4
"""

TELAS = {"painel.html": "<h1>Painel</h1>\n<p>3 pedidos (FICTICIO)</p>\n",
         "entrada.html": "<h1>Entrada</h1>\n<form>FICTICIO</form>\n"}

ok = falhou = 0


def check(nome, cond, detalhe=""):
    global ok, falhou
    if cond:
        ok += 1
        print(f"  ok   {nome}")
    else:
        falhou += 1
        print(f"  FAIL {nome}")
        if detalhe:
            print(f"       {detalhe}")


def arquivos(caminho):
    """Os caminhos listados no `## Arquivos` do corpo, na ordem em que aparecem."""
    lista, dentro = [], False
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            if linha.startswith("## "):
                dentro = linha.strip() == "## Arquivos"
                continue
            if dentro and linha.strip().startswith("- "):
                lista.append(linha.strip()[2:].strip())
    return lista


def conjunto_sig(raiz, lista):
    """`cksum` POSIX da emenda dos arquivos, na ordem do corpo — o `cat a b | cksum`."""
    crc, n = 0, 0
    for rel in lista:
        with open(os.path.join(raiz, *rel.split("/")), "rb") as fh:
            dados = fh.read()
        for b in dados:
            crc = dl._crc_byte(crc, b)
        n += len(dados)
    while n:
        crc = dl._crc_byte(crc, n & 0xFF)
        n >>= 8
    return (~crc) & 0xFFFFFFFF


def valida(raiz, caminho):
    """Os defeitos de formato do sidecar. Lista vazia = formato válido."""
    erros = []
    fm = dl.frontmatter(caminho)
    for campo in CAMPOS:
        if not fm.get(campo):
            erros.append(f"falta o campo `{campo}` no frontmatter")
    if fm.get("natureza") not in (None, "anexo"):
        erros.append("a natureza do sidecar é `anexo`, e só")
    if fm.get("status") not in ("approved", "ready"):
        erros.append("status é `approved` ou `ready`")
    if fm.get("status") == "ready" and not fm.get("correcao-pendente"):
        erros.append("status `ready` exige `correcao-pendente`")
    lista = arquivos(caminho)
    if not lista:
        erros.append("o corpo não lista arquivo nenhum em `## Arquivos`")
    for rel in lista:
        if not rel.startswith(CASA):
            erros.append(f"fora da casa {CASA}: {rel}")
        elif not os.path.isfile(os.path.join(raiz, *rel.split("/"))):
            erros.append(f"listado e não existe em disco: {rel}")
    if not erros and fm.get("conjunto-sig") != str(conjunto_sig(raiz, lista)):
        erros.append("o `conjunto-sig` gravado diverge do conjunto de hoje — protótipo mudado")
    return erros


def monta(sig="0", telas=None):
    """O exemplo da spec, montado num projeto de mentira. Devolve (raiz, caminho)."""
    raiz = tempfile.mkdtemp(prefix="sidecar-proto-")
    casa = os.path.join(raiz, ".claude", "docs", "prototipo")
    os.makedirs(casa)
    for nome, html in (telas or TELAS).items():
        with open(os.path.join(casa, nome), "w", encoding="utf-8", newline="") as fh:
            fh.write(html)
    caminho = os.path.join(casa, "interface.prototipo.md")
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(SIDECAR.format(sig=sig))
    return raiz, caminho


print("· o exemplo da spec, montado no temporário")
raiz, caminho = monta()
lista = arquivos(caminho)
sig = conjunto_sig(raiz, lista)
raiz, caminho = monta(sig=sig)
check("o exemplo aprovado passa inteiro", valida(raiz, caminho) == [],
      str(valida(raiz, caminho)))
check("os dois arquivos saem do corpo, na ordem", lista == [
    ".claude/docs/prototipo/painel.html", ".claude/docs/prototipo/entrada.html"], str(lista))

print("· a marca do conjunto é a do `cat | cksum` de verdade")
BASH = bash_posix()
if BASH is None:
    print("  pulo  sem bash que responda — o cruzamento com o shell não roda aqui")
else:
    alvos = " ".join(rel for rel in lista)
    r = subprocess.run([BASH, "-c", f"cat {alvos} | cksum"], cwd=raiz,
                       capture_output=True, text=True, env=ambiente(raiz), timeout=30,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    check("Python e shell dão o MESMO número",
          (r.stdout or "").split()[:1] == [str(sig)], f"shell={r.stdout!r} python={sig}")

print("· o formato morde")
r2, c2 = monta(sig=sig, telas=dict(TELAS, **{"painel.html": "<h1>Painel</h1>\n<p>4 pedidos</p>\n"}))
check("trocar uma tela diverge a marca gravada",
      any("protótipo mudado" in e for e in valida(r2, c2)), str(valida(r2, c2)))

r3, c3 = monta(sig=sig)
os.remove(os.path.join(r3, ".claude", "docs", "prototipo", "entrada.html"))
check("arquivo listado e ausente é defeito",
      any("não existe em disco" in e for e in valida(r3, c3)), str(valida(r3, c3)))

r4, c4 = monta(sig=sig)
with open(c4, encoding="utf-8") as fh:
    texto = fh.read()
with open(c4, "w", encoding="utf-8") as fh:
    fh.write(texto.replace("marcador-ficticio: FICTICIO\n", "")
                  .replace("- .claude/docs/prototipo/painel.html", "- docs/painel.html"))
erros = valida(r4, c4)
check("falta de campo e casa errada são acusadas",
      any("marcador-ficticio" in e for e in erros) and any("fora da casa" in e for e in erros),
      str(erros))

print("· o formato escrito viaja com a árvore")
check("a casa existe em disco, rastreada", os.path.isdir(os.path.dirname(FORMATO)), FORMATO)
check("o formato escrito veio no clone", os.path.isfile(FORMATO), FORMATO)
formato_txt = ""
if os.path.isfile(FORMATO):
    with open(FORMATO, encoding="utf-8") as fh:
        formato_txt = fh.read()
check("a casa está escrita no formato", CASA in formato_txt)
check("o exemplo tem todos os campos",
      all(f"{c}:" in formato_txt for c in CAMPOS),
      str([c for c in CAMPOS if f"{c}:" not in formato_txt]))
check("o formato ensina a conferir a marca na mão", "| cksum" in formato_txt)

print(f"{ok} passou · {falhou} falhou")
sys.exit(1 if falhou else 0)
