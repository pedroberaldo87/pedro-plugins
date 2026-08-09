#!/usr/bin/env python3
"""Bancada do plano_saida.py — só o aprovado vira passo, e silêncio não é aprovação.

Os dois defeitos que esta suíte existe pra pegar:

  · o descartado entrando no plano junto com o aprovado;
  · o rádio em branco (`val: "keep"` com `touched: false`) virando passo — que é
    silêncio lido como aprovação.

O plano gravado é conferido contra o schema do `plan_state` pelo próprio módulo,
então um plano que sai do disco aqui é um plano que o `tick` consegue marcar.
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plano_saida  # noqa: E402

FALHAS = []


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def spec():
    return {"sections": [{"title": "As propostas", "blocks": [
        {"kind": "item", "title": "PAPEL1 gasta turno demais por agente",
         "body": ["teto de 1 turno por agente",
                  "🎯 mira: PAPEL1 · turnos_por_agente 4.0",
                  "📐 confere: registro.py compara turnos_por_agente na rodada seguinte"]},
        {"kind": "item", "title": "PAPEL2 gasta turno demais por agente",
         "body": ["teto de 1 turno por agente",
                  "🎯 mira: PAPEL2 · turnos_por_agente 4.0",
                  "📐 confere: registro.py compara turnos_por_agente na rodada seguinte"]},
        {"kind": "item", "title": "PAPEL3 gasta turno demais por agente",
         "body": ["teto de 1 turno por agente",
                  "🎯 mira: PAPEL3 · turnos_por_agente 4.0",
                  "📐 confere: registro.py compara turnos_por_agente na rodada seguinte"]},
    ]}]}


def retorno(itens):
    return {"state": {"feedback": itens}}


def item(num, val, touched=True, note=""):
    return {"num": str(num), "title": "PAPEL%d gasta turno demais por agente" % num,
            "val": val, "touched": touched, "note": note}


def roda(dados, tmp, proposta=True):
    ret = os.path.join(tmp, "retorno.json")
    with open(ret, "w", encoding="utf-8") as fh:
        json.dump(dados, fh)
    argv = ["--retorno", ret, "--dir", os.path.join(tmp, "plans"), "--run", "run-exemplo"]
    if proposta:
        sp = os.path.join(tmp, "spec.json")
        with open(sp, "w", encoding="utf-8") as fh:
            json.dump(spec(), fh)
        argv += ["--proposta", sp]
    exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plano_saida.py")
    return subprocess.run([sys.executable, exe] + argv, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, start_new_session=True)


def caso_so_o_aprovado():
    print("\n· só o aprovado vira passo")
    with tempfile.TemporaryDirectory() as tmp:
        r = roda(retorno([item(1, "keep"), item(2, "remove"),
                          item(3, "change", note="teto de 2 turnos, não de 1")]), tmp)
        check("gravou", r.returncode == 0)
        arqs = os.listdir(os.path.join(tmp, "plans"))
        check("um arquivo de plano no disco", len(arqs) == 1)
        plano = json.load(open(os.path.join(tmp, "plans", arqs[0]), encoding="utf-8"))
        passos = plano["phases"][0]["items"]
        check("dois passos — o descartado ficou de fora", len(passos) == 2)
        titulos = [p["title"] for p in passos]
        check("o descartado não está no plano",
              not any("PAPEL2" in t for t in titulos))
        check("o `change` entrou com o texto do dono",
              "teto de 2 turnos, não de 1" in titulos)
        check("o `pronto` é o `confere` da proposta",
              all("registro.py compara" in p["pronto"] for p in passos))
        check("os ids são posicionais e fixos",
              [p["id"] for p in passos] == ["F1.1", "F1.2"])
        check("a contagem sai no stdout", "1 descartado(s)" in r.stdout)


def caso_sem_veredito():
    print("\n· item sem veredito recusa a gravação inteira")
    with tempfile.TemporaryDirectory() as tmp:
        r = roda(retorno([item(1, "keep"),
                          item(2, "keep", touched=False),
                          item(3, "remove")]), tmp)
        check("recusou", r.returncode == 2)
        check("nomeia o item que ficou em branco", "PAPEL2" in r.stderr)
        check("nada foi gravado", not os.path.isdir(os.path.join(tmp, "plans")))


def caso_tudo_descartado():
    print("\n· descartar tudo não gera plano vazio")
    with tempfile.TemporaryDirectory() as tmp:
        r = roda(retorno([item(1, "remove"), item(2, "remove")]), tmp)
        check("recusou", r.returncode == 2)
        check("nada foi gravado", not os.path.isdir(os.path.join(tmp, "plans")))


def caso_retorno_alheio():
    print("\n· retorno que não é da página de propostas")
    with tempfile.TemporaryDirectory() as tmp:
        r = roda({"state": {"decisions": []}}, tmp)
        check("recusou", r.returncode == 2)
        check("diz o motivo", "feedback" in r.stderr)


def caso_extrair():
    print("\n· o retorno chega em três formatos")
    itens = [item(1, "keep")]
    check("lista solta", plano_saida.extrair_retorno(itens) == itens)
    check("`feedback` na raiz",
          plano_saida.extrair_retorno({"feedback": itens}) == itens)
    check("`state.feedback`", plano_saida.extrair_retorno(retorno(itens)) == itens)


def main():
    print("plano_saida")
    caso_so_o_aprovado()
    caso_sem_veredito()
    caso_tudo_descartado()
    caso_retorno_alheio()
    caso_extrair()
    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
