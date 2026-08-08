#!/usr/bin/env python3
"""Incorpora ao plano o que ficou na fila de entrada enquanto o motor o segurava.

POR QUE EXISTE. Enquanto o motor roda, ele escreve no `.plan.json` (marca os passos que
fecharam). Editar o mesmo arquivo por baixo dele e a corrida classica: um dos dois lados
perde. A saida foi escrever o passo novo num arquivo a parte, em `.claude/plans/entrada/`,
e incorporar depois.

So que "incorporar depois" e uma PROMESSA, e promessa nao e mecanismo: se a sessao cai, o
arquivo fica no disco e ninguem o le. Foi exatamente assim que trabalho se perdeu antes
neste projeto. Este script transforma a promessa em comando.

FORMATO DE UM ARQUIVO DE ENTRADA (todos os campos alem de `para_o_plano` sao opcionais):

    {
      "para_o_plano": "<id do plano>",
      "requisitos_novos": [ {id, titulo, ca}, ... ],
      "requisito":        {id, titulo, ca},          # forma singular, aceita tambem
      "itens_novos":      [ {id, fase, title, desc, requisito, pronto}, ... ],
      "item":             {id, fase, ...}            # forma singular, aceita tambem
    }

REGRAS DE SEGURANCA, e cada uma existe por um motivo:
  - id ja presente no plano NAO e sobrescrito. O plano manda; a entrada so acrescenta.
    Sobrescrever apagaria o `status` e a prova de um passo que ja fechou.
  - passo cuja fase nao existe e RECUSADO, com o nome da fase. Criar fase sozinho seria
    re-arquitetar o plano, que nao e trabalho deste script.
  - o arquivo incorporado vai para `entrada/incorporados/`, nao e apagado. O registro do
    que entrou vale mais que a pasta limpa.
  - `--check` nao escreve nada: diz o que entraria. Use antes de incorporar de verdade.
"""

import argparse
import glob
import json
import os
import shutil
import sys


def carrega(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def itens_de(entrada):
    """Aceita as duas formas — `itens_novos` (lista) e `item` (singular)."""
    out = list(entrada.get("itens_novos") or [])
    if entrada.get("item"):
        out.append(entrada["item"])
    return out


def requisitos_de(entrada):
    out = list(entrada.get("requisitos_novos") or [])
    if entrada.get("requisito"):
        out.append(entrada["requisito"])
    return out


def fase_do_item(it):
    """A fase vem do campo `fase` ou, na falta dele, do prefixo do id (F9.32 -> F9)."""
    return it.get("fase") or str(it.get("id", "")).split(".")[0]


def incorpora(plano, entrada):
    """Devolve (acrescentados, ignorados, erros). NAO grava — quem grava e o chamador."""
    acresc, ignor, erros = [], [], []

    ids_req = {r["id"] for r in plano.get("requisitos", [])}
    for r in requisitos_de(entrada):
        if r["id"] in ids_req:
            ignor.append("requisito %s (ja existe)" % r["id"])
            continue
        plano.setdefault("requisitos", []).append(r)
        ids_req.add(r["id"])
        acresc.append("requisito %s" % r["id"])

    fases = {ph["id"]: ph for ph in plano.get("phases", [])}
    ids_it = {i["id"] for ph in plano.get("phases", []) for i in ph.get("items", [])}
    for it in itens_de(entrada):
        iid = it.get("id")
        if iid in ids_it:
            # O plano manda. Sobrescrever apagaria status e prova de um passo fechado.
            ignor.append("passo %s (ja existe no plano)" % iid)
            continue
        fid = fase_do_item(it)
        if fid not in fases:
            erros.append("passo %s: a fase '%s' nao existe no plano" % (iid, fid))
            continue
        limpo = {k: v for k, v in it.items()
                 if k in ("id", "title", "desc", "requisito", "pronto", "grupo", "pendencia")}
        fases[fid]["items"].append(limpo)
        ids_it.add(iid)
        acresc.append("passo %s -> %s" % (iid, fid))
    return acresc, ignor, erros


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=".claude/plans", help="diretorio dos planos")
    ap.add_argument("--plano", help="id do plano; sem isto, usa o `para_o_plano` de cada entrada")
    ap.add_argument("--check", action="store_true", help="so mostra o que entraria")
    a = ap.parse_args()

    entrada_dir = os.path.join(a.dir, "entrada")
    arquivos = sorted(glob.glob(os.path.join(entrada_dir, "*.json")))
    if not arquivos:
        print("nada na fila de entrada (%s)" % entrada_dir)
        return 0

    total_acresc = total_err = 0
    for caminho in arquivos:
        try:
            entrada = carrega(caminho)
        except ValueError as exc:
            print("⛔ %s: json invalido — %s" % (os.path.basename(caminho), exc))
            total_err += 1
            continue

        pid = a.plano or entrada.get("para_o_plano")
        if not pid:
            print("⛔ %s: sem `para_o_plano` e sem --plano" % os.path.basename(caminho))
            total_err += 1
            continue
        pcaminho = os.path.join(a.dir, "%s.plan.json" % pid)
        if not os.path.exists(pcaminho):
            print("⛔ %s: plano '%s' nao existe" % (os.path.basename(caminho), pid))
            total_err += 1
            continue

        plano = carrega(pcaminho)
        acresc, ignor, erros = incorpora(plano, entrada)

        print("\n📥 %s -> %s" % (os.path.basename(caminho), pid))
        for x in acresc:
            print("   + %s" % x)
        for x in ignor:
            print("   = %s" % x)
        for x in erros:
            print("   ⛔ %s" % x)
        total_err += len(erros)

        if a.check:
            continue
        if erros:
            print("   nao gravei: conserte os erros acima e rode de novo")
            continue
        if acresc:
            tmp = pcaminho + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(plano, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, pcaminho)
            total_acresc += len(acresc)
        # Move mesmo sem acrescentar nada: entrada ja incorporada nao volta pra fila.
        destino = os.path.join(entrada_dir, "incorporados")
        os.makedirs(destino, exist_ok=True)
        shutil.move(caminho, os.path.join(destino, os.path.basename(caminho)))
        print("   arquivado em entrada/incorporados/")

    if a.check:
        print("\n(--check: nada foi gravado)")
    else:
        print("\n%d item(ns) incorporado(s)" % total_acresc)
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
