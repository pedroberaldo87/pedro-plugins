#!/usr/bin/env python3
"""Checagem do plano_vs_codigo.py — o script que acusa plano e código discordando.

O teste central é a divergência plantada: um passo ABERTO cujo critério de pronto
já está satisfeito no disco tem que ser acusado, e o mesmo plano com o critério
ainda por cumprir tem que sair 0. Os planos são montados num diretório temporário
— nenhum plano real do repositório é lido aqui.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plano_vs_codigo as P  # noqa: E402

ok = 0
TMP = tempfile.mkdtemp(prefix="plano-vs-codigo-")
PLANS = os.path.join(TMP, "plans")
FAKE_ROOT = os.path.join(TMP, "repo")
os.makedirs(PLANS)
os.makedirs(os.path.join(FAKE_ROOT, "lib"))


def check(nome, cond):
    global ok
    assert cond, "FALHOU: %s" % nome
    ok += 1


def plano(nome, itens):
    p = os.path.join(PLANS, nome + ".plan.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"id": nome, "title": nome,
                   "phases": [{"id": "F1", "title": "f", "items": itens}]},
                  fh, ensure_ascii=False)
    return p


def passo(pid, pronto, status="todo"):
    return {"id": pid, "title": pid, "desc": "", "pronto": pronto,
            "status": status, "evidence": None, "done_at": None}


def limpa():
    for f in os.listdir(PLANS):
        os.remove(os.path.join(PLANS, f))


# o arquivo que o critério de caminho procura JÁ existe no disco de mentira
with open(os.path.join(FAKE_ROOT, "lib", "pronto.py"), "w") as fh:
    fh.write("a = 1\nb = 2\nc = 3\n")


def rodar():
    return P.main([PLANS, "--root", FAKE_ROOT])


# ─── a divergência plantada: passo aberto, critério já cumprido ──────────────
plano("divergente-comando", [passo("F1.1", "`test -f lib/pronto.py` sai 0")])
check("comando que JA passa com o passo aberto e ACUSADO", rodar() == 1)
limpa()

plano("divergente-caminho", [passo("F1.2", "lib/pronto.py:3")])
check("caminho que JA existe com o passo aberto e ACUSADO", rodar() == 1)
limpa()

# ─── o plano coerente: o trabalho ainda não entrou ──────────────────────────
plano("coerente-comando", [passo("F1.3", "`test -f lib/ainda_nao.py` sai 0")])
check("comando que ainda falha sai 0", rodar() == 0)
limpa()

plano("coerente-caminho", [passo("F1.4", "lib/ainda_nao.py:1")])
check("caminho inexistente sai 0", rodar() == 0)
limpa()

plano("linha-alem-do-fim", [passo("F1.5", "lib/pronto.py:99")])
check("arquivo existe mas nao tem a linha: sai 0", rodar() == 0)
limpa()

# ─── passo já fechado não é auditado ─────────────────────────────────────────
plano("fechado", [passo("F1.6", "`test -f lib/pronto.py` sai 0", status="done")])
check("passo done nao entra na varredura", rodar() == 0)
check("passo done nao aparece nos achados", P.varre(PLANS, FAKE_ROOT) == [])
limpa()

# ─── prosa: reportada como não verificável, nunca como coerente ─────────────
plano("prosa", [passo("F1.7", "a linguagem e a estetica servem pra voce")])
a = P.varre(PLANS, FAKE_ROOT)
check("prosa nao vira veredito", a[0]["veredito"] == "nao-verificavel")
check("prosa e classificada como prosa", a[0]["forma"] == "prosa")
check("prosa sozinha sai 0", rodar() == 0)
limpa()

# ─── a conjunção: critério com vários trechos entre crases ──────────────────
# O falso-positivo que este bloco fecha: julgar pelo PRIMEIRO trecho acusava
# divergência num critério cujas outras cláusulas ainda nem existem no disco.
plano("conjuncao-so-a-primeira", [
    passo("F1.9", "`test -f lib/pronto.py` sai 0; "
                  "`test -f lib/ainda_nao.py` tambem")])
a = P.varre(PLANS, FAKE_ROOT)
check("conjuncao com uma clausula por cumprir NAO e divergente",
      a[0]["veredito"] == "nao-verificavel")
check("conjuncao incompleta sai 0", rodar() == 0)
limpa()

plano("conjuncao-inteira", [
    passo("F1.10", "`test -f lib/pronto.py` sai 0; "
                   "`test -d lib` tambem")])
check("conjuncao com TODAS as clausulas cumpridas e acusada", rodar() == 1)
limpa()

# comando com efeito colateral não roda — e também não vira "coerente"
plano("perigoso", [passo("F1.8", "`rm -rf lib` sai 0")])
a = P.varre(PLANS, FAKE_ROOT)
check("comando com efeito colateral e nao-verificavel",
      a[0]["veredito"] == "nao-verificavel")
check("o arquivo do disco de mentira continua la",
      os.path.isfile(os.path.join(FAKE_ROOT, "lib", "pronto.py")))
limpa()

# ─── o achado nomeia onde está a divergência ─────────────────────────────────
plano("nomeia", [passo("F9.9", "lib/pronto.py")])
a = [x for x in P.varre(PLANS, FAKE_ROOT) if x["veredito"] == "divergente"]
check("o achado diz plano, id, status e criterio",
      a and all(a[0][k] for k in ("plano", "id", "status", "pronto")))
check("o achado aponta o plano certo", a[0]["plano"] == "nomeia.plan.json")
limpa()

# ─── um divergente no meio de vários coerentes ainda reprova ────────────────
plano("misto", [passo("F1.1", "lib/ainda_nao.py"),
                passo("F1.2", "a prosa que ninguem checa"),
                passo("F1.3", "lib/pronto.py")])
check("um divergente entre coerentes reprova", rodar() == 1)
limpa()

# ─── o script roda de verdade contra os planos do repo ───────────────────────
reais = P.varre()
check("varre() do repo devolve lista", isinstance(reais, list))

shutil.rmtree(TMP, ignore_errors=True)
print("test_plano_vs_codigo: %d asserts ok ✓  (repo: %d passo(s) aberto(s), "
      "%d divergência(s) hoje)"
      % (ok, len(reais), len([x for x in reais if x["veredito"] == "divergente"])))
