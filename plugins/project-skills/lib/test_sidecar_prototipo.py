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
marcador-ficticio: DADO-FICTICIO
---

## Arquivos

- .claude/docs/prototipo/painel.html
- .claude/docs/prototipo/entrada.html

## Superfícies

- Painel do dia — jornada: acompanhar a obra — procedência: blueprint.md §3
- Entrada de pedido — jornada: registrar um pedido — procedência: blueprint.md §4
- lacuna: governança — jornada: acompanhar a obra — motivo: sem papel de admin neste sistema
"""

# As superfícies OBRIGATÓRIAS (F13.5): o que a prática sempre ignora. Cobradas por
# jornada no rito; aqui o cobrador de presença confere que a lei as escreve e que a
# lacuna declarada carrega motivo.
OBRIGATORIAS = ("erro", "vazio", "carregando", "configuração", "governança")

TELAS = {"painel.html": "<h1>Painel</h1>\n<p>3 pedidos (DADO-FICTICIO)</p>\n",
         "entrada.html": "<h1>Entrada</h1>\n<form>DADO-FICTICIO</form>\n"}

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


def _secao(caminho, titulo):
    """As linhas `- ...` de uma seção `## <titulo>` do corpo, na ordem."""
    lista, dentro = [], False
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            if linha.startswith("## "):
                dentro = linha.strip() == "## " + titulo
                continue
            if dentro and linha.strip().startswith("- "):
                lista.append(linha.strip()[2:].strip())
    return lista


def arquivos(caminho):
    """Os caminhos listados no `## Arquivos` do corpo, na ordem em que aparecem."""
    return _secao(caminho, "Arquivos")


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
    if fm.get("marcador-ficticio") not in (None, "DADO-FICTICIO"):
        erros.append("o marcador é o token literal `DADO-FICTICIO`, e só (decisão do dono)")
    lista = arquivos(caminho)
    if not lista:
        erros.append("o corpo não lista arquivo nenhum em `## Arquivos`")
    for rel in lista:
        if not rel.startswith(CASA):
            erros.append(f"fora da casa {CASA}: {rel}")
        elif not os.path.isfile(os.path.join(raiz, *rel.split("/"))):
            erros.append(f"listado e não existe em disco: {rel}")
    for sup in _secao(caminho, "Superfícies"):
        if sup.startswith("lacuna:") and "motivo:" not in sup:
            erros.append(f"lacuna declarada sem motivo: {sup}")
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
    fh.write(texto.replace("marcador-ficticio: DADO-FICTICIO\n", "")
                  .replace("- .claude/docs/prototipo/painel.html", "- docs/painel.html"))
erros = valida(r4, c4)
check("falta de campo e casa errada são acusadas",
      any("marcador-ficticio" in e for e in erros) and any("fora da casa" in e for e in erros),
      str(erros))

r5, c5 = monta(sig=sig)
with open(c5, encoding="utf-8") as fh:
    texto = fh.read()
with open(c5, "w", encoding="utf-8") as fh:
    fh.write(texto.replace(" — motivo: sem papel de admin neste sistema", ""))
check("lacuna declarada sem motivo é defeito",
      any("lacuna declarada sem motivo" in e for e in valida(r5, c5)), str(valida(r5, c5)))

# F13.13 — o marcador é o TOKEN LITERAL, não um valor livre: valor inventado no campo
# faria a conferência por onda grepar a palavra errada e o fictício vazar calado.
r7, c7 = monta(sig=sig)
with open(c7, encoding="utf-8") as fh:
    texto = fh.read()
with open(c7, "w", encoding="utf-8") as fh:
    fh.write(texto.replace("marcador-ficticio: DADO-FICTICIO", "marcador-ficticio: FAKE"))
check("marcador diferente do token literal é defeito",
      any("token literal" in e for e in valida(r7, c7)), str(valida(r7, c7)))

print("· o consumidor da completude lê a mesma lista de superfícies")
import completude  # noqa: E402
check("as três superfícies do exemplo saem com jornada e marca de lacuna",
      completude.le_superficies(caminho) == [("acompanhar a obra", False),
                                             ("registrar um pedido", False),
                                             ("acompanhar a obra", True)],
      str(completude.le_superficies(caminho)))

print("· o sidecar do esquema (F13.10): diagrama promovido, com procedência citada")
# A lei já diz "um por etapa (<etapa>.prototipo.md)": o diagrama da etapa 5 entra pelo
# MESMO formato, com `anexo-de: blueprint.md` — nada de formato paralelo.
ESQUEMA = """---
natureza: anexo
anexo-de: blueprint.md
design-sig: 77
status: approved
conjunto-sig: {sig}
marcador-ficticio: DADO-FICTICIO
---

## Arquivos

- .claude/docs/prototipo/organismo.html

## Superfícies

- Organismo — jornada: o ciclo inteiro — procedência: blueprint.md §2
"""
r6 = tempfile.mkdtemp(prefix="sidecar-esquema-")
casa6 = os.path.join(r6, ".claude", "docs", "prototipo")
os.makedirs(casa6)
with open(os.path.join(casa6, "organismo.html"), "w", encoding="utf-8", newline="") as fh:
    fh.write("<svg>ciclo (DADO-FICTICIO)</svg>\n")
c6 = os.path.join(casa6, "esquema.prototipo.md")
with open(c6, "w", encoding="utf-8") as fh:
    fh.write(ESQUEMA.format(sig="0"))
sig6 = conjunto_sig(r6, arquivos(c6))
with open(c6, "w", encoding="utf-8") as fh:
    fh.write(ESQUEMA.format(sig=sig6))
check("o sidecar do esquema passa no MESMO validador, sem formato paralelo",
      valida(r6, c6) == [], str(valida(r6, c6)))
check("a linha do diagrama cita a procedência no blueprint",
      any("procedência: blueprint.md" in s for s in _secao(c6, "Superfícies")),
      str(_secao(c6, "Superfícies")))

SKILL = os.path.join(AQUI, os.pardir, "skills", "start", "SKILL.md")
skill_txt = ""
if os.path.isfile(SKILL):
    with open(SKILL, encoding="utf-8") as fh:
        skill_txt = fh.read()
check("a etapa 5 promove o diagrama ao sidecar `esquema.prototipo.md`, ancorado no blueprint",
      "esquema.prototipo.md" in skill_txt and "anexo-de: blueprint.md" in skill_txt)
check("a skill exige a procedência citada e declara a degradação sem archify",
      "procedência citada" in skill_txt and "não nasce sidecar do esquema" in skill_txt
      and "DEGRADADO" in skill_txt)

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
check("as cinco superfícies obrigatórias estão escritas na lei",
      all(s in formato_txt for s in OBRIGATORIAS),
      str([s for s in OBRIGATORIAS if s not in formato_txt]))
check("a lei cobra as superfícies POR JORNADA e escreve a forma da lacuna com motivo",
      "POR JORNADA" in formato_txt
      and "- lacuna: <superfície> — jornada:" in formato_txt
      and "motivo:" in formato_txt)
check("a lei escreve o token literal do marcador e o grep por onda nos arquivos de produto",
      "marcador-ficticio: DADO-FICTICIO" in formato_txt
      and "conferência por onda" in formato_txt
      and "PRODUTO" in formato_txt)

print(f"{ok} passou · {falhou} falhou")
sys.exit(1 if falhou else 0)
