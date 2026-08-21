#!/usr/bin/env python3
"""doc_load.py — carrega a documentação canônica do projeto e diz o que vale como RÉGUA.

POR QUE EXISTE: a instrução "leia a constituição e o quality-goals do projeto onde a
missão roda; se houver blueprint.md e features.md com `status: approved`, entram na mesma
régua; arquivo ausente não é achado" estava COPIADA em prosa dentro de cada skill que
julga alguma coisa. Prosa copiada diverge no primeiro conserto, e a divergência é
silenciosa — nenhum dos lados está errado sozinho (patterns.md §1.6a).

Aqui a regra é UMA, e é programa:
  - quem é canônico e de que natureza (autoral · minerado · derivado · dispensa)
  - o que vale como régua HOJE (`status: approved` no autoral; minerado vale como mapa)
  - a MARCA do corpo do que vale, para a missão congelar a lei na primeira volta
  - o que está ausente, dito em voz alta em vez de fingido

A receita da marca é a MESMA de `hooks/lib-doc-mark.sh` (cksum do CORPO, sem o
frontmatter) — não porque é elegante, mas porque duas receitas dariam duas marcas para o
mesmo texto, e aí a comparação nunca fecharia.

Fail-open na direção honesta: projeto sem casa da doc devolve lista vazia e sai 0.
Ausência de documento não derruba a execução, mas também não passa calada: a lacuna sobe
ao TOPO da saída, dizendo quantos documentos faltam e qual skill escreve cada natureza
(`/start` para lei e acordo, `/doc` para o mapa). Só uma dispensa com motivo ESCRITO cala
o alarme — dispensa sem motivo é cobrada na mesma linha.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from casa_da_doc import casa as casa_da_doc  # noqa: E402  (a doc migrou para docs/; a casa velha é retrocompatível)

# Quem é canônico, e a natureza de cada um. A ordem é a de leitura: a lei primeiro.
# Fonte: _shared/contrato-familia.md, seção "Os documentos".
# LEI — vale como régua com `ready` OU `approved`; só `draft` fica de fora. É o
# comportamento que as skills já tinham em prosa ("leia a constituição do projeto"), e
# torná-lo mais estrito aqui apagaria o eixo de constituição de todo projeto que ainda
# não formalizou o de acordo — conserto que quebra o que funciona não é conserto.
LEI = [
    ("constituicao.md", "a lei do projeto — o que o sistema tem que ser"),
    ("quality-goals.md", "a ordem de prioridade quando não dá para ter tudo"),
    ("constraints.md", "o que o projeto não pode fazer"),
]

# ACORDO — as etapas de concepção. Estas SÓ valem com `approved`, porque medir a obra
# contra rascunho reprova obra certa (a regra que já estava escrita nas duas skills de
# motor). `ready` aqui é "escrito", e escrito não é acordado.
ACORDO = [
    ("context.md", "o que o projeto é, para quem"),
    ("solution-strategy.md", "a estratégia escolhida"),
    ("glossary.md", "as palavras do domínio"),
    ("architecture-intent.md", "as peças pretendidas, e onde cada coisa mora"),
    ("design.md", "o sistema visual, quando há interface"),
    ("journeys.md", "os caminhos de pessoa que o projeto atende"),
    ("blueprint.md", "o esquema de funcionamento acordado"),
    ("features.md", "a lista de funcionalidades acordada"),
]

MINERADOS = [
    ("architecture.md", "a estrutura de hoje, projetada do código"),
    ("patterns.md", "as convenções e as armadilhas medidas"),
    ("data-stores.md", "todo depósito de dado, dentro e fora do repositório"),
    ("durability.md", "quem copia cada depósito, e o que não tem cobertura"),
    ("runtime.md", "os fluxos ponta a ponta"),
]

DISPENSA = "dispensa.md"

# A CASA do protótipo (lei: prototipo/FORMATO.md, na casa da doc). O sidecar de lá é ANEXO:
# natureza própria, fora de `regua`/`marca_regua` — o protótipo muda de tela sem mudar a
# lei, e contaminar a marca congelada faria toda missão longa acusar lei mexida à toa.
CASA_PROTOTIPO = ("prototipo",)
SUFIXO_SIDECAR = ".prototipo.md"


def corpo(caminho):
    """O texto abaixo do frontmatter YAML. Sem frontmatter: o arquivo inteiro.

    Mesma regra do `doc_corpo` de lib-doc-mark.sh — o frontmatter fica DE FORA porque ele
    carrega a própria marca, e incluí-lo faria a marca mudar ao ser gravada.
    """
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            linhas = fh.read().splitlines()
    except OSError:
        return None
    if not linhas or linhas[0].strip() != "---":
        return "\n".join(linhas)
    for i in range(1, len(linhas)):
        if linhas[i].strip() == "---":
            return "\n".join(linhas[i + 1:])
    return "\n".join(linhas)


_TABELA = None


def _tabela():
    global _TABELA
    if _TABELA is None:
        pol = 0x04C11DB7
        t = []
        for i in range(256):
            c = i << 24
            for _ in range(8):
                c = ((c << 1) ^ pol) if (c & 0x80000000) else (c << 1)
                c &= 0xFFFFFFFF
            t.append(c)
        _TABELA = t
    return _TABELA


def _crc_byte(crc, byte):
    return ((crc << 8) & 0xFFFFFFFF) ^ _tabela()[((crc >> 24) ^ byte) & 0xFF]


def cksum(caminho):
    """A marca do corpo pela receita do `cksum` POSIX, byte a byte."""
    texto = corpo(caminho)
    if texto is None:
        return None
    # `doc_corpo | cksum` alimenta o cksum com as linhas do corpo, cada uma com \n.
    dados = ("\n".join(texto.splitlines()) + "\n").encode("utf-8") if texto.strip() else b""
    crc = 0
    for b in dados:
        crc = _crc_byte(crc, b)
    n = len(dados)
    while n:
        crc = _crc_byte(crc, n & 0xFF)
        n >>= 8
    return (~crc) & 0xFFFFFFFF


def frontmatter(caminho):
    """Os campos do frontmatter YAML, chave por chave. Sem frontmatter: dicionário vazio.

    Parser deliberadamente burro: só `chave: valor` de primeiro nível, que é tudo o que o
    contrato da família usa. Lista e aninhamento saem como texto cru — quem precisar deles
    lê o arquivo, não este campo.
    """
    campos = {}
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            linhas = fh.read().splitlines()
    except OSError:
        return campos
    if not linhas or linhas[0].strip() != "---":
        return campos
    for linha in linhas[1:]:
        if linha.strip() == "---":
            break
        if not linha or linha[0] in " \t-#":
            continue
        if ":" not in linha:
            continue
        chave, _, valor = linha.partition(":")
        campos[chave.strip()] = valor.strip()
    return campos


def le_documento(raiz, nome, natureza, papel):
    caminho = casa_da_doc(raiz, nome)
    if not os.path.isfile(caminho):
        return None
    fm = frontmatter(caminho)
    status = fm.get("status", "")
    autoral = fm.get("authored-by", "") == "human"
    m = cksum(caminho)
    # A régua: autoral só vale com o de acordo do dono; minerado vale como MAPA, nunca
    # como lei. `ready` é "escrito", e escrito não é acordado (contrato-familia.md).
    if natureza == "lei":
        vale = status in ("ready", "approved")
        motivo = ("a lei do projeto, escrita e válida" if vale
                  else f"status é '{status or 'sem status'}' — rascunho não é lei")
    elif natureza == "acordo":
        vale = status == "approved"
        motivo = ("de acordo do dono" if vale
                  else f"status é '{status or 'sem status'}', e só 'approved' vale como régua")
    else:
        vale = False
        motivo = "documento minerado — vale como mapa do que existe, nunca como régua"
    # Marca gravada diferente do corpo de hoje: alguém editou depois do de acordo. Só o
    # documento de ACORDO reabre por isso — a lei não passa pelo rito de aprovação.
    gravada = fm.get("approved-sig", "")
    reaberto = bool(natureza == "acordo" and vale and gravada and str(m) != gravada)
    return {
        "arquivo": os.path.relpath(caminho, raiz),
        "natureza": natureza,
        "papel": papel,
        "status": status or None,
        "autoral": autoral,
        "vale_como_regua": vale and not reaberto,
        "motivo": "editado depois do de acordo — a etapa reabriu" if reaberto else motivo,
        "marca": m,
        "marca_gravada": gravada or None,
        "reaberto": reaberto,
        "correcao_pendente": fm.get("correcao-pendente") or None,
    }


def _arquivos_do_sidecar(caminho):
    """Os caminhos do `## Arquivos` do corpo, na ordem em que aparecem."""
    lista, dentro = [], False
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for linha in fh:
                if linha.startswith("## "):
                    dentro = linha.strip() == "## Arquivos"
                    continue
                if dentro and linha.strip().startswith("- "):
                    lista.append(linha.strip()[2:].strip())
    except OSError:
        pass
    return lista


def _conjunto_sig(raiz, lista):
    """A marca do CONJUNTO: `cksum` POSIX da emenda dos arquivos, na ordem do corpo
    (o `cat a b | cksum` do FORMATO). Arquivo ausente devolve None — sem conjunto inteiro
    não há marca a comparar, e fingir uma inventaria divergência ou acordo falso."""
    crc, n = 0, 0
    for rel in lista:
        try:
            with open(os.path.join(raiz, *rel.split("/")), "rb") as fh:
                dados = fh.read()
        except OSError:
            return None
        for b in dados:
            crc = _crc_byte(crc, b)
        n += len(dados)
    while n:
        crc = _crc_byte(crc, n & 0xFF)
        n >>= 8
    return (~crc) & 0xFFFFFFFF


def le_anexos(raiz):
    """Os sidecars de protótipo da casa, cada um como ANEXO — nunca como régua.

    Dois gatilhos reabrem o anexo, e os dois saem nomeados:
      - divergência do CONJUNTO: o `conjunto-sig` gravado não bate com a emenda dos
        arquivos de hoje — alguém mexeu no protótipo depois do de acordo;
      - de acordo do design REGRAVADO: o `design-sig` gravado não bate com a marca de
        hoje do documento que o sustenta (`anexo-de`) — o design mudou por baixo.
    """
    casa = casa_da_doc(raiz, *CASA_PROTOTIPO)
    if not os.path.isdir(casa):
        return []
    anexos = []
    for nome in sorted(os.listdir(casa)):
        if not nome.endswith(SUFIXO_SIDECAR):
            continue
        caminho = os.path.join(casa, nome)
        fm = frontmatter(caminho)
        status = fm.get("status", "")
        anexo_de = fm.get("anexo-de", "")
        lista = _arquivos_do_sidecar(caminho)
        conjunto_hoje = _conjunto_sig(raiz, lista) if lista else None
        gravada = fm.get("conjunto-sig", "")
        diverge = bool(gravada) and (conjunto_hoje is None or str(conjunto_hoje) != gravada)
        design_sig = fm.get("design-sig", "")
        design_hoje = cksum(casa_da_doc(raiz, anexo_de)) if anexo_de else None
        regravado = bool(design_sig) and design_hoje is not None and str(design_hoje) != design_sig
        reaberto = diverge or regravado
        vale = status == "approved" and not reaberto
        if reaberto:
            motivo = ("o conjunto de hoje diverge do `conjunto-sig` gravado — protótipo mudado"
                      if diverge else
                      "o de acordo do design foi regravado — o `design-sig` não bate mais")
        elif vale:
            motivo = "anexo aprovado, fora da régua congelada"
        else:
            motivo = f"status é '{status or 'sem status'}', e só 'approved' vale como acordo"
        anexos.append({
            "arquivo": os.path.relpath(caminho, raiz),
            "natureza": "anexo",
            "anexo_de": anexo_de or None,
            "status": status or None,
            "vale": vale,
            "divergencia_conjunto": diverge,
            "reaberto": reaberto,
            "motivo": motivo,
            "correcao_pendente": fm.get("correcao-pendente") or None,
        })
    return anexos


def carrega(raiz):
    docs = []
    # Ausência de lei e ausência de etapa de concepção não se corrigem do mesmo jeito —
    # por isso a lacuna sai separada por natureza. `ausentes` continua sendo a soma das
    # três, na mesma ordem de sempre, para quem já lê esse campo.
    faltam = {"lei": [], "acordo": [], "minerado": []}
    for natureza, lista in (("lei", LEI), ("acordo", ACORDO), ("minerado", MINERADOS)):
        for nome, papel in lista:
            d = le_documento(raiz, nome, natureza, papel)
            (docs.append(d) if d else faltam[natureza].append(nome))
    ausentes = faltam["lei"] + faltam["acordo"] + faltam["minerado"]

    disp = casa_da_doc(raiz, DISPENSA)
    dispensa = None
    if os.path.isfile(disp):
        fm = frontmatter(disp)
        dispensa = {"arquivo": os.path.relpath(disp, raiz), "motivo": fm.get("motivo") or None}

    regua = [d for d in docs if d["vale_como_regua"]]
    anexos = le_anexos(raiz)
    # A marca da missão: a soma das marcas do que vale como régua, na ordem de leitura.
    # É ela que a execução contínua congela na primeira volta — lei editada no meio da
    # missão muda este número, e a mudança aparece em vez de passar calada.
    marca_regua = "+".join(str(d["marca"]) for d in regua) if regua else None
    return {
        "raiz": os.path.abspath(raiz),
        "documentos": docs,
        "regua": [d["arquivo"] for d in regua],
        "marca_regua": marca_regua,
        "ausentes": ausentes,
        "ausentes_lei": faltam["lei"],
        "ausentes_acordo": faltam["acordo"],
        "ausentes_minerados": faltam["minerado"],
        "dispensa": dispensa,
        # O anexo fica FORA de `regua` e de `marca_regua` de propósito: protótipo que
        # muda de tela não é lei mexida, e contaminá-la dispararia alarme falso.
        "anexos": anexos,
        "reabertos": [d["arquivo"] for d in docs if d["reaberto"]],
        "correcoes_pendentes": [
            {"arquivo": d["arquivo"], "o_que_falta": d["correcao_pendente"]}
            for d in docs if d["correcao_pendente"]
        ],
    }


CANONICOS = len(LEI) + len(ACORDO) + len(MINERADOS)


def _alarme(estado):
    """A lacuna, no topo e com o comando que a resolve. Vazia quando não há o que dizer.

    Sobe SEMPRE que falta qualquer canônico — no rodapé, ao lado de nada que se pudesse
    fazer, a lacuna era lida como enfeite. Dispensa com motivo escrito continua calando.
    """
    if not estado["ausentes"] or (estado["dispensa"] and estado["dispensa"]["motivo"]):
        return []
    linhas = [f"⚠️ LACUNA — {len(estado['ausentes'])} de {CANONICOS} documentos canônicos "
              "não existem neste projeto:"]
    for rotulo, chave, skill in (
        ("lei", "ausentes_lei", "/start escreve"),
        ("acordo", "ausentes_acordo", "/start escreve"),
        ("mapa", "ausentes_minerados", "/doc extrai do código"),
    ):
        if estado[chave]:
            linhas.append(f"   {rotulo}: {' · '.join(estado[chave])}  →  {skill}")
    if estado["dispensa"]:
        linhas.append("   dispensa declarada SEM MOTIVO ESCRITO — escreva o motivo para calar isto")
    linhas.append("")
    return linhas


def texto(estado):
    linhas = _alarme(estado)
    if not estado["documentos"]:
        linhas.append("nenhum documento canônico na casa da doc — não há régua a carregar")
        if estado["dispensa"]:
            linhas.append(f"  dispensa declarada: {estado['dispensa']['motivo'] or 'SEM MOTIVO ESCRITO'}")
        return "\n".join(linhas)

    linhas.append(f"documentação canônica de {estado['raiz']}")
    linhas.append("")
    linhas.append("VALE COMO RÉGUA — julgue contra estes, e cite a passagem:")
    if estado["regua"]:
        for d in estado["documentos"]:
            if d["vale_como_regua"]:
                linhas.append(f"  ✅ {d['arquivo']:<34} {d['papel']}")
    else:
        linhas.append("  (nenhum — nenhum documento autoral chegou a 'approved')")
    linhas.append("")
    linhas.append("MAPA — leia para se situar, nunca para reprovar:")
    for d in estado["documentos"]:
        if not d["vale_como_regua"]:
            marca = "⚠️" if d["reaberto"] else "  "
            linhas.append(f"  {marca} {d['arquivo']:<34} {d['motivo']}")
    if estado["anexos"]:
        linhas.append("")
        linhas.append("ANEXO — o protótipo, fora da régua congelada (nunca entra na marca):")
        for a in estado["anexos"]:
            marca = "✅" if a["vale"] else "⚠️"
            linhas.append(f"  {marca} {a['arquivo']:<34} {a['motivo']}")
    if estado["reabertos"]:
        linhas.append("")
        linhas.append("REABERTOS — editados depois do de acordo, não valem como régua:")
        for a in estado["reabertos"]:
            linhas.append(f"  ⚠️ {a}")
    if estado["correcoes_pendentes"]:
        linhas.append("")
        linhas.append("CORREÇÃO PENDENTE declarada pelo dono:")
        for c in estado["correcoes_pendentes"]:
            linhas.append(f"  📝 {c['arquivo']}: {c['o_que_falta']}")
    linhas.append("")
    linhas.append(f"marca da régua: {estado['marca_regua'] or '(sem régua)'}")
    return "\n".join(linhas)


def main(argv=None):
    p = argparse.ArgumentParser(description="carrega a documentação canônica do projeto")
    p.add_argument("--project-root", default=".", help="a raiz do projeto (default: .)")
    p.add_argument("--json", action="store_true", help="devolve o estado inteiro em JSON")
    p.add_argument("--marca", action="store_true", help="imprime só a marca da régua")
    args = p.parse_args(argv)

    raiz = args.project_root
    if not os.path.isdir(raiz):
        print(f"doc-load: {raiz} não é um diretório", file=sys.stderr)
        return 2
    estado = carrega(raiz)
    if args.marca:
        print(estado["marca_regua"] or "")
        return 0
    print(json.dumps(estado, ensure_ascii=False, indent=1) if args.json else texto(estado))
    return 0


if __name__ == "__main__":
    sys.exit(main())
