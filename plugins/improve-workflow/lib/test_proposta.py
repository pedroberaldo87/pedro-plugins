#!/usr/bin/env python3
"""Bancada do proposta.py — a contagem de itens da página contra o número de propostas.

O defeito que esta suíte existe pra pegar é o item-balaio: três propostas dentro de
um item só, com um veredito único. Contar `feedback-item` no HTML de verdade (o
mesmo montador que a rodada usa) é a única prova de que cada proposta ganhou a
própria linha de aprovação.
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proposta  # noqa: E402

VISUAL_PAGE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "visual", "lib", "visual_page.py"))

FALHAS = []


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def entrada(n):
    return {
        "run": "run-exemplo",
        "prova": {"src": "medidor.py run-exemplo",
                  "output": "EXECUTOR  2 agentes  8 turnos  4.0 turnos/agente"},
        "propostas": [
            {"defeito": "PAPEL%d gasta turno demais por agente" % i,
             "consequencia": ["cada tarefa do papel %d paga turno que não rende" % i],
             "proposta": ["teto de 1 turno por agente no papel %d" % i],
             "mira": "PAPEL%d · turnos_por_agente 4.0" % i,
             "confere": "registro.py compara turnos_por_agente na rodada seguinte",
             "sev": "high"}
            for i in range(1, n + 1)],
    }


def pagina(spec, tmp):
    caminho = os.path.join(tmp, "p.html")
    r = subprocess.run([sys.executable, VISUAL_PAGE, "build", "--spec", "-",
                        "--out", caminho],
                       input=json.dumps(spec), capture_output=True, text=True,
                       start_new_session=True)
    if r.returncode != 0:
        return None, r.stderr
    with open(caminho, encoding="utf-8") as f:
        return f.read(), r.stderr


def caso_um_item_por_proposta():
    import tempfile
    if not os.path.exists(VISUAL_PAGE):
        check("visual_page.py ao lado (sem ele não há página pra contar)", False)
        return
    with tempfile.TemporaryDirectory(prefix="proposta-") as tmp:
        for n in (1, 3):
            html, err = pagina(proposta.montar(entrada(n), projeto="teste"), tmp)
            if html is None:
                check("página de %d propostas monta" % n, False)
                print(err)
                continue
            check("%d proposta(s) ⇒ %d item(ns) na página" % (n, n),
                  html.count('class="feedback-item"') == n)
            check("%d proposta(s) ⇒ %d bloco(s) trino (problema·consequência·proposta)" % (n, n),
                  html.count('class="tri tri-') + html.count('class="tri"') == n)


def caso_recusa_sem_consequencia():
    sem = entrada(1)
    del sem["propostas"][0]["consequencia"]
    check("proposta sem consequência é recusada (template trino obrigatório)",
          any("consequencia" in e for e in proposta.erros(sem)))


def caso_recusa():
    sem_numero = entrada(1)
    del sem_numero["propostas"][0]["mira"]
    check("proposta sem o número que mira é recusada",
          any("mira" in e for e in proposta.erros(sem_numero)))
    sem_prova = entrada(1)
    sem_prova["prova"]["output"] = ""
    check("página sem prova é recusada",
          any("prova.output" in e for e in proposta.erros(sem_prova)))
    check("entrada boa não tem erro", proposta.erros(entrada(2)) == [])


def caso_prova_diz_o_que_estraga():
    """A régua da própria casa (clareza.py) reprovava TODA página deste programa."""
    sys.path.insert(0, os.path.dirname(VISUAL_PAGE))
    try:
        import clareza
    except ImportError:
        check("clareza.py ao lado (sem ele não há régua pra passar)", False)
        return
    for n in (1, 3):
        achados = clareza.revisao_do_spec(proposta.montar(entrada(n), projeto="teste"))
        check("%d proposta(s): a prova vem seguida do que ela estraga" % n,
              not any(c == "prova-sem-estrago" for c, _m in achados))


def main():
    print("proposta")
    caso_um_item_por_proposta()
    caso_recusa()
    caso_recusa_sem_consequencia()
    caso_prova_diz_o_que_estraga()
    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
