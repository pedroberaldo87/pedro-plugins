#!/usr/bin/env python3
"""curadoria_features.py — o retorno da curadoria vira `features.md`, ou não vira nada.

A etapa 5 é a única em que a skill fala primeiro: ela DERIVA a lista de funcionalidades
dos documentos já aprovados e leva item a item pro dono, numa página do `/visual`. O
veredito volta pelo disco (`~/.claude/visual-state/latest.json`, em `state.feedback`),
em valor de máquina: `keep` | `change` | `remove`.

Este programa é o portão entre aquele retorno e o documento. Ele **recusa gravar**
`features.md` enquanto existir item sem veredito, e diz qual é o item pelo nome — porque
rádio em branco chega no JSON como `val: "keep"` com `touched: false`, e gravar isso
seria transformar silêncio em aprovação. Quem decide é o dono, item a item.

O que ele grava, quando todos têm veredito:

    keep     → entra em `features.md` com o título proposto
    change   → entra com o texto que o dono escreveu no campo aberto, literal
    remove   → vai pra seção "Deixado de fora de propósito", com o motivo dele

A **Origem** (a passagem literal do documento aprovado que motivou o item) não vem no
retorno — ela mora no `detail` do bloco `item` da página. Passe o mesmo spec.json em
`--proposta` e ela é casada pelo título; sem ele, a origem nasce `[PENDENTE]`.

Uso:
    python3 curadoria_features.py --retorno ~/.claude/visual-state/latest.json \\
        --saida .claude/docs/features.md [--proposta {spec.json}]

Saída: 0 gravou · 2 recusou (nomeando o item sem veredito) · 2 uso errado.
stdlib only (requisito do repo).
"""

import argparse
import json
import os
import sys

VEREDITOS = ("keep", "change", "remove")

FRONTMATTER = """---
authored-by: human
status: draft
reviewed:
approved:
---
"""


def _carregar(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def extrair_retorno(dado):
    """Aceita o `latest.json` inteiro, o `state` solto ou a lista de feedback."""
    if isinstance(dado, list):
        return dado
    if isinstance(dado, dict):
        if isinstance(dado.get("feedback"), list):
            return dado["feedback"]
        estado = dado.get("state")
        if isinstance(estado, dict) and isinstance(estado.get("feedback"), list):
            return estado["feedback"]
    raise ValueError("retorno sem `feedback`: não é a página de curadoria")


def sem_veredito(itens):
    """Os itens que o dono NÃO tocou — ou que voltaram com valor fora do spec."""
    faltam = []
    for n, it in enumerate(itens, 1):
        val = (it.get("val") or "").strip()
        tocado = str(it.get("touched", "")).lower() in ("1", "true")
        if not tocado or val not in VEREDITOS:
            faltam.append((it.get("num") or n, it.get("title") or "(sem título)"))
    return faltam


def origens(proposta):
    """`{título: passagem literal}` a partir dos blocos `item` do spec da página."""
    if not proposta:
        return {}
    blocos = proposta.get("blocks") if isinstance(proposta, dict) else proposta
    fora = {}
    for blk in blocos or []:
        if isinstance(blk, dict) and blk.get("title"):
            fora[blk["title"]] = (blk.get("detail") or "").strip()
    return fora


def montar(itens, mapa_origem, frontmatter=FRONTMATTER):
    dentro, deixados = [], []
    for it in itens:
        titulo = it.get("title") or "(sem título)"
        nota = (it.get("note") or "").strip()
        if it["val"] == "remove":
            deixados.append((titulo, nota or "[PENDENTE]"))
        else:
            texto = nota if it["val"] == "change" and nota else titulo
            dentro.append((texto, mapa_origem.get(titulo) or "[PENDENTE]"))

    linhas = [frontmatter.rstrip("\n"), "", "# Funcionalidades", ""]
    for n, (texto, origem) in enumerate(dentro, 1):
        linhas += ["### F-%d · %s" % (n, texto), "- **Origem:** %s" % origem, ""]
    if deixados:
        linhas += ["## Deixado de fora de propósito", ""]
        for titulo, motivo in deixados:
            linhas += ["### %s" % titulo, "- **Motivo:** %s" % motivo, ""]
    return "\n".join(linhas).rstrip("\n") + "\n"


def _frontmatter_existente(caminho):
    """Documento já gravado mantém o frontmatter dele — a aprovação não é nossa."""
    if not os.path.exists(caminho):
        return FRONTMATTER
    with open(caminho, encoding="utf-8") as fh:
        texto = fh.read()
    if texto.startswith("---"):
        fim = texto.find("\n---", 3)
        if fim >= 0:
            return texto[:fim + 4]
    return FRONTMATTER


def main(argv):
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("--retorno", required=True, help="JSON do retorno da página")
    ap.add_argument("--saida", required=True, help="caminho do features.md")
    ap.add_argument("--proposta", help="spec.json da página (dá a Origem de cada item)")
    args = ap.parse_args(argv[1:])

    try:
        itens = extrair_retorno(_carregar(args.retorno))
    except (OSError, ValueError, json.JSONDecodeError) as erro:
        print("RECUSADO: %s" % erro, file=sys.stderr)
        return 2

    if not itens:
        print("RECUSADO: retorno vazio — nenhum item foi curado.", file=sys.stderr)
        return 2

    faltam = sem_veredito(itens)
    if faltam:
        print("RECUSADO: %d item(ns) sem veredito — nada foi gravado em %s"
              % (len(faltam), args.saida), file=sys.stderr)
        for num, titulo in faltam:
            print("  · item %s · %s" % (num, titulo), file=sys.stderr)
        print("Rádio em branco não é `keep`: leve estes de volta pro dono.",
              file=sys.stderr)
        return 2

    proposta = _carregar(args.proposta) if args.proposta else None
    corpo = montar(itens, origens(proposta), _frontmatter_existente(args.saida))
    pasta = os.path.dirname(os.path.abspath(args.saida))
    if pasta:
        os.makedirs(pasta, exist_ok=True)
    with open(args.saida, "w", encoding="utf-8") as fh:
        fh.write(corpo)

    vereditos = [it["val"] for it in itens]
    print("gravado %s · %d keep · %d change · %d remove"
          % (args.saida, vereditos.count("keep"), vereditos.count("change"),
             vereditos.count("remove")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
