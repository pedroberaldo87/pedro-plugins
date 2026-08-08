#!/usr/bin/env python3
"""Suite da fila de entrada do plano.

O contrapeso que mais importa: passo que JA existe no plano nao pode ser sobrescrito pela
entrada. Sobrescrever apagaria `status` e `evidence` de um passo ja fechado — que e
exatamente a perda que a fila existe para evitar.
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_entrada as pe  # noqa: E402

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def plano_base():
    return {
        "id": "p-teste", "title": "plano de teste",
        "requisitos": [{"id": "S-1", "titulo": "ja existe", "ca": "x"}],
        "phases": [
            {"id": "F1", "title": "fase um", "items": [
                {"id": "F1.1", "title": "ja feito", "desc": "d", "requisito": "S-1",
                 "pronto": "p", "status": "done", "evidence": "a prova que nao pode sumir"}]},
            {"id": "F2", "title": "fase dois", "items": [
                {"id": "F2.1", "title": "aberto", "desc": "d", "requisito": "S-1", "pronto": "p"}]},
        ],
    }


def main():
    d = tempfile.mkdtemp(prefix="entrada-")
    try:
        plans = os.path.join(d, "plans")
        entrada = os.path.join(plans, "entrada")
        os.makedirs(entrada)
        pcam = os.path.join(plans, "p-teste.plan.json")
        json.dump(plano_base(), open(pcam, "w", encoding="utf-8"), ensure_ascii=False)

        print("o caso normal — acrescenta requisito e passo")
        p = plano_base()
        acresc, ignor, erros = pe.incorpora(p, {
            "para_o_plano": "p-teste",
            "requisitos_novos": [{"id": "S-9", "titulo": "novo", "ca": "y"}],
            "itens_novos": [{"id": "F2.5", "fase": "F2", "title": "novo passo", "desc": "d",
                             "requisito": "S-9", "pronto": "p"}]})
        check("o requisito novo entra", any("S-9" in x for x in acresc))
        check("o passo novo entra na fase certa", any("F2.5 -> F2" in x for x in acresc))
        check("sem erro no caminho normal", erros == [])
        check("o passo aparece mesmo na fase F2",
              any(i["id"] == "F2.5" for i in p["phases"][1]["items"]))

        print("passo ja feito NAO e sobrescrito — a prova dele nao pode sumir")
        p = plano_base()
        acresc, ignor, erros = pe.incorpora(p, {
            "para_o_plano": "p-teste",
            "itens_novos": [{"id": "F1.1", "fase": "F1", "title": "TENTATIVA DE TROCA",
                             "desc": "d", "requisito": "S-1", "pronto": "p"}]})
        it = p["phases"][0]["items"][0]
        check("o passo existente e ignorado, nao acrescentado", acresc == [])
        check("e o motivo e dito", any("ja existe" in x for x in ignor))
        check("o titulo antigo continua", it["title"] == "ja feito")
        check("o status continua done", it.get("status") == "done")
        check("a PROVA continua no lugar", it.get("evidence") == "a prova que nao pode sumir")

        print("requisito repetido tambem nao duplica")
        p = plano_base()
        acresc, ignor, _ = pe.incorpora(p, {
            "requisitos_novos": [{"id": "S-1", "titulo": "outro texto", "ca": "z"}]})
        check("nao duplica o requisito", len(p["requisitos"]) == 1)
        check("e o titulo original fica", p["requisitos"][0]["titulo"] == "ja existe")

        print("fase inexistente e RECUSADA — criar fase seria re-arquitetar")
        p = plano_base()
        acresc, ignor, erros = pe.incorpora(p, {
            "itens_novos": [{"id": "F7.1", "fase": "F7", "title": "orfao", "desc": "d",
                             "requisito": "S-1", "pronto": "p"}]})
        check("o passo orfao nao entra", acresc == [])
        check("o erro nomeia a fase que falta", any("F7" in x for x in erros))

        print("a fase sai do id quando o campo `fase` nao vem")
        p = plano_base()
        acresc, _, erros = pe.incorpora(p, {
            "itens_novos": [{"id": "F2.9", "title": "sem campo fase", "desc": "d",
                             "requisito": "S-1", "pronto": "p"}]})
        check("F2.9 cai na F2 pelo prefixo do id", any("F2.9 -> F2" in x for x in acresc))

        print("a forma singular (`item`/`requisito`) tambem e aceita")
        p = plano_base()
        acresc, _, _ = pe.incorpora(p, {
            "requisito": {"id": "S-8", "titulo": "singular", "ca": "y"},
            "item": {"id": "F1.7", "fase": "F1", "title": "singular", "desc": "d",
                     "requisito": "S-8", "pronto": "p"}})
        check("requisito singular entra", any("S-8" in x for x in acresc))
        check("item singular entra", any("F1.7" in x for x in acresc))

        print("so os campos do schema passam — lixo da entrada nao vaza pro plano")
        p = plano_base()
        pe.incorpora(p, {"itens_novos": [
            {"id": "F2.6", "fase": "F2", "title": "t", "desc": "d", "requisito": "S-1",
             "pronto": "p", "nota_do_relato": "isto nao e campo de plano",
             "medicao": "nem isto"}]})
        novo = [i for i in p["phases"][1]["items"] if i["id"] == "F2.6"][0]
        check("campo estranho nao entra no plano", "nota_do_relato" not in novo)
        check("mas o que e do schema entra", novo["pronto"] == "p")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK (%d checks)" % TOTAL[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
