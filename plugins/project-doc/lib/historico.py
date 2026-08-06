#!/usr/bin/env python3
"""historico.py — o arquivo histórico que nasce ao lado de cada documento autoral.

O documento canônico só tem o que vale HOJE. Item reescrito não é apagado: ele sai
do canônico e vai para `<doc>.historico.md`, na mesma pasta, com os três dados que
tornam a mudança auditável — a **data**, o **contexto** (o que estava acontecendo) e
a **decisão** que o mudou. Sem os três, a entrada não é escrita: histórico sem o
porquê é entulho, e entulho ninguém lê.

Por que ao lado, e não num diretório de arquivo morto: o histórico é do documento,
não do projeto. Quem abre `quality-goals.md` acha `quality-goals.historico.md` na
mesma listagem — não precisa saber que existe uma convenção.

Contrato de saída (a forma do arquivo) está em
`skills/start-doc/references/authorial-kit.md`, seção "Contrato de saída".

Uso:
    from historico import reescrever, listar, caminho_historico
    reescrever(doc, antigo, novo, contexto="...", decisao="...")

    python3 historico.py reescrever <doc> --antigo T --novo T \\
        --contexto "..." --decisao "..." [--data YYYY-MM-DD]
    python3 historico.py listar <doc>

stdlib only (requisito do repo).
"""

import argparse
import datetime
import json
import os
import re
import sys

# ── a forma do arquivo (o contrato) ────────────────────────────────────────
SUFIXO = ".historico.md"
_SAIU = "**Saiu do canônico:**"
_ENTROU = "**Entrou no lugar:**"
_INDENT = "    "          # bloco indentado: guarda o texto literal, cerca de código inclusive
_RESUMO_MAX = 70          # o resumo do cabeçalho é rótulo, não conteúdo

_CABECALHO = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+·\s+(.*)$")
_CONTEXTO = re.compile(r"^-\s+\*\*Contexto:\*\*\s+(.*)$")
_DECISAO = re.compile(r"^-\s+\*\*Decisão:\*\*\s+(.*)$")


def caminho_historico(doc_path):
    """`.../quality-goals.md` → `.../quality-goals.historico.md` (mesma pasta)."""
    base = os.path.basename(doc_path)
    raiz = base[:-3] if base.endswith(".md") else base
    return os.path.join(os.path.dirname(doc_path), raiz + SUFIXO)


def _uma_linha(txt):
    return " ".join((txt or "").split())


def _resumo(texto):
    primeira = _uma_linha(texto.strip().split("\n")[0])
    primeira = primeira.lstrip("#-*0123456789. ").strip() or "item sem título"
    if len(primeira) > _RESUMO_MAX:
        primeira = primeira[:_RESUMO_MAX - 1].rstrip() + "…"
    return primeira


def _indentar(texto):
    return "\n".join(_INDENT + ln if ln.strip() else "" for ln in texto.split("\n"))


def _desindentar(linhas):
    fora = [ln[len(_INDENT):] if ln.startswith(_INDENT) else ln for ln in linhas]
    while fora and not fora[0].strip():
        fora.pop(0)
    while fora and not fora[-1].strip():
        fora.pop()
    return "\n".join(fora)


def _preambulo(doc_path):
    """O cabeçalho do arquivo histórico — nasce autoral, como o documento que serve."""
    return (
        "---\n"
        "generated: %s\n"
        "authored-by: human\n"
        "scope: []\n"
        "---\n"
        "\n"
        "# Histórico — `%s`\n"
        "\n"
        "> O que saiu do documento canônico, e por quê. O canônico só guarda o que vale\n"
        "> hoje; cada item reescrito vem parar aqui com a data, o contexto e a decisão\n"
        "> que o mudou. Ninguém apaga entrada daqui — corrigir é escrever a próxima.\n"
        % (datetime.date.today().isoformat(), os.path.basename(doc_path))
    )


def entrada_markdown(data, contexto, decisao, texto, substituido_por):
    """O bloco de uma reescrita, na forma que o `listar` sabe ler de volta."""
    return (
        "\n## %s · %s\n"
        "\n"
        "- **Contexto:** %s\n"
        "- **Decisão:** %s\n"
        "\n"
        "%s\n"
        "\n"
        "%s\n"
        "\n"
        "%s\n"
        "\n"
        "%s\n"
        % (data, _resumo(texto), contexto, decisao,
           _SAIU, _indentar(texto), _ENTROU, _indentar(substituido_por))
    )


def reescrever(doc_path, antigo, novo, contexto, decisao, data=None):
    """Move `antigo` do canônico para o histórico e põe `novo` no lugar.

    Levanta ValueError (sem escrever nada) quando o item não está no documento,
    quando aparece mais de uma vez (qual deles?), ou quando falta contexto/decisão.
    """
    contexto, decisao = _uma_linha(contexto), _uma_linha(decisao)
    if not contexto:
        raise ValueError("contexto é obrigatório: sem ele a entrada não diz por que mudou")
    if not decisao:
        raise ValueError("decisão é obrigatória: sem ela a entrada não diz o que mudou o item")
    if not (antigo or "").strip():
        raise ValueError("o item antigo é obrigatório")
    if not (novo or "").strip():
        raise ValueError("o item novo é obrigatório: isto arquiva reescrita, não remoção")
    if antigo == novo:
        raise ValueError("o item novo é idêntico ao antigo — não houve reescrita")

    with open(doc_path, encoding="utf-8") as fh:
        canonico = fh.read()
    ocorrencias = canonico.count(antigo)
    if ocorrencias == 0:
        raise ValueError("item não encontrado em %s" % os.path.basename(doc_path))
    if ocorrencias > 1:
        raise ValueError("item aparece %d vezes em %s — recorte um trecho único"
                         % (ocorrencias, os.path.basename(doc_path)))

    data = data or datetime.date.today().isoformat()
    hist_path = caminho_historico(doc_path)
    nasceu = not os.path.exists(hist_path)

    # Histórico primeiro: se a escrita do canônico falhar, sobra registro a mais,
    # nunca item perdido.
    with open(hist_path, "a", encoding="utf-8") as fh:
        if nasceu:
            fh.write(_preambulo(doc_path))
        fh.write(entrada_markdown(data, contexto, decisao, antigo, novo))

    with open(doc_path, "w", encoding="utf-8") as fh:
        fh.write(canonico.replace(antigo, novo, 1))

    return {
        "doc": doc_path,
        "historico": hist_path,
        "criou_historico": nasceu,
        "entrada": {
            "data": data,
            "contexto": contexto,
            "decisao": decisao,
            "texto": antigo,
            "substituido_por": novo,
        },
    }


def listar(doc_path):
    """As entradas do histórico do documento, em ordem de escrita. Sem arquivo → []."""
    hist_path = caminho_historico(doc_path)
    if not os.path.exists(hist_path):
        return []
    with open(hist_path, encoding="utf-8") as fh:
        linhas = fh.read().split("\n")

    entradas, atual, alvo, buffer = [], None, None, []

    def fecha():
        if atual is not None and alvo:
            atual[alvo] = _desindentar(buffer)

    for linha in linhas:
        cab = _CABECALHO.match(linha)
        if cab:
            fecha()
            atual = {"data": cab.group(1), "resumo": cab.group(2).strip(),
                     "contexto": "", "decisao": "", "texto": "", "substituido_por": ""}
            entradas.append(atual)
            alvo, buffer = None, []
            continue
        if atual is None:
            continue
        if linha.strip() == _SAIU:
            fecha()
            alvo, buffer = "texto", []
            continue
        if linha.strip() == _ENTROU:
            fecha()
            alvo, buffer = "substituido_por", []
            continue
        if alvo:
            buffer.append(linha)
            continue
        m = _CONTEXTO.match(linha)
        if m:
            atual["contexto"] = m.group(1).strip()
            continue
        m = _DECISAO.match(linha)
        if m:
            atual["decisao"] = m.group(1).strip()
    fecha()
    return entradas


def main(argv):
    ap = argparse.ArgumentParser(prog="historico.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")

    r = sub.add_parser("reescrever", help="move um item do canônico para o histórico")
    r.add_argument("doc")
    r.add_argument("--antigo", required=True)
    r.add_argument("--novo", required=True)
    r.add_argument("--contexto", required=True)
    r.add_argument("--decisao", required=True)
    r.add_argument("--data")

    li = sub.add_parser("listar", help="as entradas do histórico, em JSON")
    li.add_argument("doc")

    args = ap.parse_args(argv[1:])
    if args.cmd == "reescrever":
        try:
            print(json.dumps(reescrever(args.doc, args.antigo, args.novo,
                                        args.contexto, args.decisao, args.data),
                             ensure_ascii=False))
        except (ValueError, OSError) as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            return 2
        return 0

    if args.cmd == "listar":
        print(json.dumps({"historico": caminho_historico(args.doc),
                          "entradas": listar(args.doc)}, ensure_ascii=False))
        return 0

    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
