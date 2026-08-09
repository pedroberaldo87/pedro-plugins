#!/usr/bin/env python3
"""proposta.py — o passo 7 da autópsia sai pela superfície de aprovação, não pelo chat.

Proposta despejada em prosa no terminal não tem onde ser aprovada: o dono lê,
concorda com a terceira e discorda da primeira, e não sobra registro de qual foi
qual. A superfície de aprovação do /visual resolve isso com um veredito POR item —
então aqui a regra é uma só: **um item por proposta**, nunca um item com a lista
toda dentro.

Este programa não escreve HTML. Ele monta o SPEC do /visual e imprime; quem monta a
página é o plugin vizinho, pelo cano:

    python3 proposta.py propostas.json \
      | python3 <…>/visual/lib/visual_page.py build --spec -

Cada proposta carrega o número que ela mira e como esse número será conferido na
rodada seguinte — proposta sem isso é opinião, e sai recusada aqui em vez de virar
item que ninguém consegue cobrar depois.

O JSON de entrada:

    {"run": "run-exemplo",
     "prova": {"src": "medidor.py run-exemplo", "output": "<a saída CRUA>"},
     "propostas": [
       {"defeito": "EXECUTOR gasta 4 turnos por agente",
        "proposta": ["teto de 1 turno por executor"],
        "mira": "EXECUTOR · turnos_por_agente 4.0",
        "confere": "registro.py compara turnos_por_agente do EXECUTOR",
        "sev": "high"}]}
"""

import json
import os
import sys

CAMPOS = ("defeito", "proposta", "mira", "confere")

ROTULOS = ["✓ Aprovar", "✏️ Ajustar", "✗ Descartar"]


def bullets(v):
    return [v] if isinstance(v, str) else list(v or [])


def erros(entrada):
    """Tudo que impede o spec de existir, de uma vez — não um erro por rodada."""
    fora = []
    if not isinstance(entrada, dict):
        return ["a entrada tem que ser um objeto JSON"]
    prova = entrada.get("prova") or {}
    if not str(prova.get("output") or "").strip():
        fora.append("prova.output vazio — a página pede veredito, e pedir decisão "
                    "sem mostrar a prova é o que esta skill existe pra não fazer")
    props = entrada.get("propostas") or []
    if not props:
        fora.append("nenhuma proposta — sem defeito a propor, a rodada acaba sem página")
    for i, p in enumerate(props, 1):
        if not isinstance(p, dict):
            fora.append("proposta %d não é objeto" % i)
            continue
        for c in CAMPOS:
            if not (bullets(p.get(c)) if c == "proposta" else str(p.get(c) or "").strip()):
                fora.append("proposta %d sem '%s' — proposta sem o número que ela mira "
                            "e sem como conferir é opinião, não conserto" % (i, c))
    return fora


def item(p):
    """Uma proposta, um item — o veredito do dono mora NO item, um por defeito."""
    blk = {"kind": "item", "title": p["defeito"],
           "body": bullets(p["proposta"]) + ["🎯 mira: %s" % p["mira"],
                                             "📐 confere: %s" % p["confere"]]}
    if p.get("sev"):
        blk["sev"] = p["sev"]
    return blk


def montar(entrada, projeto=None):
    run = entrada.get("run") or "run"
    props = entrada["propostas"]
    prova = entrada["prova"]
    return {
        "slug": "propostas-%s" % run,
        "title": "Propostas da autópsia — %s" % run,
        "subtitle": "%d proposta(s); o veredito é seu, item a item" % len(props),
        "kicker": "🔬 Autópsia · %d proposta(s)" % len(props),
        "ident": {"projeto": projeto or os.path.basename(os.getcwd()),
                  "artefato": "Propostas da autópsia do run %s" % run,
                  "gerado_de": "improve-workflow/lib/proposta.py",
                  "estado": "gerado"},
        "item_labels": ROTULOS,
        "sections": [
            {"title": "A prova", "blocks": [
                {"kind": "evidencia", "src": prova.get("src") or "medidor.py",
                 "output": prova["output"],
                 "highlight": prova.get("highlight") or ""}]},
            {"title": "As propostas", "blocks": [item(p) for p in props]},
        ],
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("uso: proposta.py <propostas.json|-> | visual_page.py build --spec -",
              file=sys.stderr)
        return 2
    bruto = sys.stdin.read() if argv[0] == "-" else open(argv[0], encoding="utf-8").read()
    try:
        entrada = json.loads(bruto)
    except ValueError as e:
        print("JSON inválido: %s" % e, file=sys.stderr)
        return 2
    ruins = erros(entrada)
    if ruins:
        for r in ruins:
            print("✗ %s" % r, file=sys.stderr)
        return 2
    print(json.dumps(montar(entrada), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
