#!/usr/bin/env python3
"""plano_saida.py — o veredito da página de propostas vira plano, e só o aprovado.

A página nasce em `proposta.py`, um item por proposta. O veredito volta pelo disco
(`~/.claude/visual-state/latest.json`, em `state.feedback`), em valor de máquina:
`keep` | `change` | `remove`. Este programa é o portão entre aquele retorno e o
plano ticável — a skill não escreve no plano à mão.

O que ele faz com cada veredito:

    keep     → vira passo, com o título da proposta
    change   → vira passo, com o texto que o dono escreveu no campo aberto
    remove   → não vira passo nenhum

Item sem veredito RECUSA a gravação inteira, e o programa diz qual item é pelo
nome: rádio em branco chega no JSON como `val: "keep"` com `touched: false`, e
gravar isso seria transformar silêncio em aprovação.

O `pronto` de cada passo é o `📐 confere:` que a própria proposta declarou — ele
mora no `body` do bloco `item` do spec, não no retorno. Por isso o spec entra em
`--proposta`, casado pelo título.

DEGRADAÇÃO DECLARADA. A conferência contra o schema é do `plan_state.py`, que vive
no plugin `project-skills` e pode não estar na máquina. Sem ele o JSON sai igual
(quem grava é este módulo) e o aviso vai pro `stderr`.

Uso:
    python3 plano_saida.py --retorno ~/.claude/visual-state/latest.json \\
        --proposta spec.json [--dir .claude/plans] [--run run-exemplo]

Saída: 0 gravou · 2 recusou · 2 uso errado. stdlib only (requisito do repo).
"""

import argparse
import datetime
import importlib.util
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
SAIDA = os.path.join(ROOT, ".claude", "plans")
PLAN_STATE = os.path.join(ROOT, "plugins", "project-skills", "lib", "plan_state.py")

FASE = "F1"
VEREDITOS = ("keep", "change", "remove")
MARCA_CONFERE = "📐 confere:"
MARCA_MIRA = "🎯 mira:"

AVISO_DEGRADACAO = (
    "aviso: o plugin project-skills não está nesta máquina (%s) — o plano foi "
    "gravado sem a conferência do plan_state; confira-o à mão antes de executar")


def carregar(caminho):
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
    raise ValueError("retorno sem `feedback`: não é a página de propostas")


def sem_veredito(itens):
    """Os itens que o dono NÃO tocou — ou que voltaram com valor fora do spec."""
    faltam = []
    for n, it in enumerate(itens, 1):
        val = (it.get("val") or "").strip()
        tocado = str(it.get("touched", "")).lower() in ("1", "true")
        if not tocado or val not in VEREDITOS:
            faltam.append((it.get("num") or n, it.get("title") or "(sem título)"))
    return faltam


def criterios(proposta):
    """`{título: (mira, confere)}` a partir dos blocos `item` do spec da página."""
    fora = {}
    if not proposta:
        return fora
    secoes = proposta.get("sections") if isinstance(proposta, dict) else []
    for sec in secoes or []:
        for blk in (sec.get("blocks") or []):
            if not isinstance(blk, dict) or blk.get("kind") != "item":
                continue
            mira = confere = ""
            for linha in (blk.get("body") or []):
                if str(linha).startswith(MARCA_MIRA):
                    mira = str(linha)[len(MARCA_MIRA):].strip()
                elif str(linha).startswith(MARCA_CONFERE):
                    confere = str(linha)[len(MARCA_CONFERE):].strip()
            fora[blk.get("title") or ""] = (mira, confere)
    return fora


def passo_de(n, it, mapa, run):
    titulo_orig = it.get("title") or "(sem título)"
    nota = (it.get("note") or "").strip()
    mira, confere = mapa.get(titulo_orig, ("", ""))
    return {
        "id": "%s.%d" % (FASE, n),
        "title": nota if it["val"] == "change" and nota else titulo_orig,
        "desc": "a autópsia do %s mirou %s" % (run, mira or titulo_orig),
        "pronto": confere or "o medidor deixa de acusar %s" % (mira or titulo_orig),
        "status": "todo",
        "evidence": None,
        "done_at": None,
    }


def plano_de(itens, mapa, run, data=None):
    """O plano inteiro, em memória — só os aprovados. `remove` fica de fora."""
    data = data or datetime.date.today().isoformat()
    aprovados = [it for it in itens if it["val"] != "remove"]
    passos = [passo_de(n, it, mapa, run) for n, it in enumerate(aprovados, 1)]
    return {
        "id": "autopsia-%s" % data,
        "title": "Autópsia de %s — %d proposta(s) aprovada(s)" % (data, len(passos)),
        "created": data,
        "status": "active",
        "phases": [{
            "id": FASE,
            "title": "Propostas aprovadas na autópsia de %s" % data,
            "items": passos,
        }],
    }


def confere_com_plan_state(plano, caminho=PLAN_STATE):
    """Confere contra o schema do `plan_state`, quando ele está na máquina.

    Devolve `(erros, aviso)`. `aviso` preenchido = a conferência NÃO aconteceu.
    """
    if not os.path.isfile(caminho):
        return [], AVISO_DEGRADACAO % caminho
    spec = importlib.util.spec_from_file_location("plan_state_da_autopsia", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.erros_do_plano(plano), ""


def escreve(itens, mapa, run, saida=SAIDA, data=None):
    """Grava o plano e devolve `(caminho, aviso)`. Aviso vazio = houve conferência."""
    plano = plano_de(itens, mapa, run, data)
    do_schema, aviso = confere_com_plan_state(plano)
    if do_schema:
        raise ValueError("o plano não passa no schema: " + "; ".join(do_schema))
    os.makedirs(saida, exist_ok=True)
    caminho = os.path.join(saida, "%s.plan.json" % plano["id"])
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(plano, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return caminho, aviso


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--retorno", required=True, help="JSON do retorno da página")
    ap.add_argument("--proposta", help="spec.json da página (dá o `confere` de cada item)")
    ap.add_argument("--dir", default=SAIDA, help="onde gravar (padrão: .claude/plans)")
    ap.add_argument("--run", default="run", help="o run que a autópsia leu")
    ap.add_argument("--data", default=None, help="a data do plano (padrão: hoje)")
    args = ap.parse_args(argv)

    try:
        itens = extrair_retorno(carregar(args.retorno))
    except (OSError, ValueError) as erro:
        print("RECUSADO: %s" % erro, file=sys.stderr)
        return 2
    if not itens:
        print("RECUSADO: retorno vazio — nenhuma proposta foi julgada.", file=sys.stderr)
        return 2

    faltam = sem_veredito(itens)
    if faltam:
        print("RECUSADO: %d item(ns) sem veredito — nada foi gravado no plano"
              % len(faltam), file=sys.stderr)
        for num, titulo in faltam:
            print("  · item %s · %s" % (num, titulo), file=sys.stderr)
        print("Rádio em branco não é `keep`: leve estes de volta pro dono.",
              file=sys.stderr)
        return 2

    if all(it["val"] == "remove" for it in itens):
        print("RECUSADO: o dono descartou tudo — não há passo pra gravar.",
              file=sys.stderr)
        return 2

    mapa = criterios(carregar(args.proposta) if args.proposta else None)
    try:
        caminho, aviso = escreve(itens, mapa, args.run, args.dir, args.data)
    except ValueError as erro:
        print("RECUSADO: %s" % erro, file=sys.stderr)
        return 2
    if aviso:
        sys.stderr.write(aviso + "\n")
    vals = [it["val"] for it in itens]
    print("%s · %d aprovado(s) · %d descartado(s)"
          % (caminho, len(vals) - vals.count("remove"), vals.count("remove")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
