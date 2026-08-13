#!/usr/bin/env python3
"""Suite do auditoria_plano.py — a ordem das três auditorias."""

import inspect
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auditoria_plano as ap  # noqa: E402

FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


# o que `cobertura.mapa` devolve quando nada está errado
LIMPO = {"cobertas": ["F1.1"], "sem_requisito": [], "orfaos": [],
         "inexistentes": [], "por_req": {"S-1": ["F1.1"]},
         "sem_jornada": [], "sem_ca": [], "repetidos": [],
         "sem_artigo": [], "decididas": [], "artigos_inexistentes": [],
         "artigos_sem_tarefa": [],
         "sem_peca": [], "pecas_inexistentes": [],
         "sem_passo": [], "passos_sem_funcionalidade": [],
         "jornadas_sem_funcionalidade": [], "epicos_sem_jornada": [],
         "total": 1}


def com(**mudanca):
    m = dict(LIMPO)
    m.update(mudanca)
    return m


AQUI = os.path.dirname(os.path.abspath(__file__))

# Duas rodadas sobre o mesmo plano têm que devolver a MESMA saída, byte a byte —
# senão "o nível 1 está vermelho" vira coisa que depende de quando você perguntou,
# e o laço deixa de ser auditoria para virar sorteio. A comparação é do texto,
# não de igualdade de dicionário: ordem de achado que dança já reprova.
SONDA = (
    "import json,sys;sys.path.insert(0,%r);"
    "import auditoria_plano as ap;"
    "print(json.dumps(ap.rodada(json.load(sys.stdin)), sort_keys=False,"
    " ensure_ascii=False))"
)


def _saida(mapa, semente):
    """A auditoria rodada de fora, com a semente de hash do Python trocada.

    Duas chamadas no mesmo processo não provam nada sobre `set` e `dict`: é a
    semente diferente que faz aparecer qualquer ordem herdada de hash.
    """
    env = dict(os.environ, PYTHONHASHSEED=semente)
    p = subprocess.run([sys.executable, "-c", SONDA % AQUI],
                       input=json.dumps(mapa), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
    return p.stdout


def main():
    print("auditoria_plano")

    # nível 1 vermelho E nível 2 também: só o 1 sai
    r = ap.audita(com(pecas_inexistentes=[("S-1", "Fila que não existe")],
                      orfaos=["S-9"]))
    check("nível 1 vermelho é reportado", r["nivel1"]["vermelho"])
    check("com o nível 1 vermelho, não há resultado de nível 2",
          "nivel2" not in r)
    check("nem de nível 3", "nivel3" not in r)
    check("e a parada diz onde parou", r["parou_em"] == 1)

    # O artigo da lei que nenhuma tarefa representa NÃO julga ESTE plano. A conta é de
    # PROJETO — a lei inteira contra a UNIÃO dos planos, que é o que `completude.py`
    # faz —, e o mapa que chega aqui é de um plano só: medi-la no nível 1 deixaria todo
    # plano parcial vermelho para sempre, os níveis 2 e 3 inalcançáveis, e o laço
    # inventando tarefa de um artigo que este plano nunca se propôs a tratar.
    r = ap.audita(com(artigos_sem_tarefa=["7 · Clareza da instrução"]))
    check("artigo da lei sem tarefa não deixa o nível 1 vermelho",
          not r["nivel1"]["vermelho"])
    check("e o plano segue até o nível 3", r["parou_em"] == 3 and "nivel3" in r)
    check("nenhum achado do plano fala de artigo sem tarefa",
          not any("artigo da lei que nenhuma tarefa" in a
                  for a in r["nivel1"]["achados"] + r["nivel2"]["achados"]))
    check("e ele também não vira bloqueio de rodada",
          not ap.rodada(com(artigos_sem_tarefa=["7 · Clareza da instrução"]))
              ["bloqueios"])

    # nível 1 verde: o 2 roda, e acha
    r = ap.audita(com(orfaos=["S-9"]))
    check("nível 1 verde libera o nível 2", not r["nivel1"]["vermelho"])
    check("o nível 2 devolve resultado", "nivel2" in r)
    check("e ele acusa o requisito sem tarefa",
          any("S-9" in a for a in r["nivel2"]["achados"]))
    check("nível 2 vermelho não libera o nível 3", "nivel3" not in r)
    check("a parada é o nível 2", r["parou_em"] == 2)

    # tudo verde: o 3 aparece, e aparece como julgamento pendente
    r = ap.audita(LIMPO)
    check("com 1 e 2 verdes, o nível 3 aparece", "nivel3" in r)
    check("e ele não se declara verde sozinho",
          r["nivel3"]["pendente"] and not r["nivel3"].get("vermelho"))

    # os três pés do nível 3 — nomeados, e cada um com o que o reprova
    pes = r["nivel3"]["pes"]
    check("o nível 3 sai com os três pés, não com uma nota só", len(pes) == 3)
    check("e os três são os de dimensoes-de-revisao.md, nesta ordem",
          [p["pe"] for p in pes] ==
          ["qualidade", "cobertura por finalidade", "coerência com a régua"])
    check("cada pé diz o que o reprova",
          all(p.get("reprova", "").strip() for p in pes))
    check("qualidade reprova bug, e manda lint/type-check pro portão mecânico",
          "bug" in pes[0]["reprova"] and "portão mecânico" in pes[0]["reprova"])
    check("cobertura reprova finalidade sem teste que morda",
          "MORDA" in pes[1]["reprova"] and "MUTAÇÃO" in pes[1]["reprova"])
    check("a régua reprova por passagem violada, e ausência dela não é achado",
          "doc-load" in pes[2]["reprova"]
          and "Ausência de régua não é achado" in pes[2]["reprova"])
    check("a rodada mecânica está limpa", r["parou_em"] == 3)

    # cada balde cai no nível certo
    check("requisito sem critério é nível 2",
          "nivel2" in ap.audita(com(sem_ca=["S-1"])))
    check("funcionalidade sem peça é nível 1",
          "nivel2" not in ap.audita(com(sem_peca=["S-1"])))

    # os três baldes do nível 1 — quem segue pro conserto e quem devolve a pergunta
    r = ap.audita(com(inexistentes=["S-9"]))["nivel1"]
    check("sem classificação escrita, o achado é plano-errado",
          [a["alvo"] for a in r["baldes"]["plano-errado"]] == ["S-9"])
    check("plano-errado segue pro conserto", r["conserta"] == ["S-9"])
    check("e não devolve pergunta nenhuma ao dono",
          not r["devolve_ao_dono"] and r["perguntas"] == [])

    r = ap.audita(com(artigos_inexistentes=["S-9"],
                      classificacao={"S-9": "doc-vencida"}))["nivel1"]
    check("doc-vencida cai no balde dela",
          [a["alvo"] for a in r["baldes"]["doc-vencida"]] == ["S-9"])
    check("doc-vencida não vai pro conserto", r["conserta"] == [])
    check("doc-vencida devolve a pergunta ao dono",
          r["devolve_ao_dono"] and any("S-9" in p for p in r["perguntas"]))

    r = ap.audita(com(pecas_inexistentes=[("S-9", "Fila")],
                      classificacao={"S-9 Fila": "doc-em-conflito"}))["nivel1"]
    check("doc-em-conflito cai no balde dele",
          [a["alvo"] for a in r["baldes"]["doc-em-conflito"]] == ["S-9 Fila"])
    check("doc-em-conflito não vai pro conserto", r["conserta"] == [])
    check("doc-em-conflito devolve a pergunta ao dono",
          r["devolve_ao_dono"] and any("Fila" in p for p in r["perguntas"]))

    # um achado de cada: a pergunta pendente para o laço mesmo havendo conserto
    r = ap.audita(com(inexistentes=["S-1"], sem_artigo=["S-2"],
                      classificacao={"S-2": "doc-vencida"}))["nivel1"]
    check("com pergunta pendente, o laço para mesmo tendo o que consertar",
          r["conserta"] == ["S-1"] and r["devolve_ao_dono"])

    # a parada do laço: rodada limpa é conta, não interpretação
    r = ap.rodada(com(orfaos=["S-9"]))
    check("achado de severidade real deixa a rodada suja", not r["limpa"])
    check("e ele aparece nomeado como bloqueio",
          any("S-9" in b for b in r["bloqueios"]))

    r = ap.rodada(com(orfaos=["S-9"]), limites_aceitos=["S-9"])
    check("achado dentro do limite aceito não bloqueia",
          r["limpa"] and r["bloqueios"] == [])

    r = ap.rodada(com(artigos_inexistentes=["S-9"],
                      classificacao={"S-9": "doc-vencida"}),
                  limites_aceitos=["S-9"])
    check("pergunta pendente ao dono não fecha a rodada nem com limite aceito",
          not r["limpa"])

    # fixture de duas rodadas: a primeira acha, a segunda fecha
    laco = ap.laco([com(orfaos=["S-9"]), LIMPO])
    check("o laço fecha na segunda rodada", laco["fechou_em"] == 2)
    check("a primeira rodada não estava limpa", not laco["rodadas"][0]["limpa"])
    check("a segunda estava", laco["rodadas"][1]["limpa"])
    check("e o laço não roda mais que as rodadas que teve",
          len(laco["rodadas"]) == 2)

    laco = ap.laco([com(orfaos=["S-9"]), com(orfaos=["S-9"])])
    check("sem rodada limpa, o laço não declara fechamento",
          laco["fechou_em"] is None and not laco["limpa"])

    # o ciclo: quem monta entrega o mapa, quem audita é o programa
    montagens = []

    def monta(anterior):
        montagens.append(anterior)
        return com(orfaos=["S-9"]) if anterior is None else LIMPO

    c = ap.ciclo(monta)
    check("o ciclo fecha na rodada limpa", c["fechou_em"] == 2 and c["limpa"])
    check("cada montagem virou uma rodada auditada",
          len(montagens) == len(c["rodadas"]) == 2)
    check("a montagem seguinte recebe a rodada anterior",
          montagens[0] is None and montagens[1] is c["rodadas"][0])

    # quem monta não assina o veredito: o mapa que se declara limpo é auditado igual
    c = ap.ciclo(lambda _: com(orfaos=["S-9"], limpa=True, bloqueios=[]),
                 maximo=1)
    check("veredito escrito pelo montador não fecha o ciclo",
          not c["limpa"] and c["fechou_em"] is None)
    check("e o auditor acusa o achado assim mesmo",
          any("S-9" in b for b in c["rodadas"][0]["bloqueios"]))

    c = ap.ciclo(lambda _: com(orfaos=["S-9"]), maximo=3)
    check("sem rodada limpa, o ciclo para no máximo e não declara fechamento",
          len(c["rodadas"]) == 3 and c["fechou_em"] is None)

    # o desvio que pularia o auditor não existe — é linha de código, não recomendação
    corpo = [linha.strip() for linha in
             inspect.getsource(ap.ciclo).splitlines() if linha.strip()]
    i = [n for n, linha in enumerate(corpo) if linha.startswith("mapa = ")][0]
    check("o auditor é a linha imediatamente seguinte à da montagem",
          corpo[i + 1].startswith("r = rodada("))

    # as duas auditorias mecânicas são determinísticas: mesma entrada, mesma saída
    cheio1 = com(artigos_inexistentes=["S-4", "S-2"],
                 pecas_inexistentes=["S-7"],
                 inexistentes=["S-9", "S-1", "S-15", "S-11", "S-8", "S-3"],
                 repetidos=["S-3"], sem_artigo=["S-5"],
                 sem_jornada=["F2.1"], sem_peca=["F1.2"],
                 sem_passo=["F3.3"],
                 classificacao={"S-2": "doc-vencida",
                                "S-7": "doc-em-conflito"})
    cheio2 = com(orfaos=["S-9", "S-2", "S-15", "S-11", "S-8", "S-3"],
                 sem_requisito=["F1.4", "F1.1", "F2.7", "F3.2", "F1.9", "F4.5"],
                 sem_ca=["S-6"], jornadas_sem_funcionalidade=["J2"],
                 passos_sem_funcionalidade=["P3"], epicos_sem_jornada=["E1"])

    for rotulo, mapa in (("nível 1", cheio1), ("nível 2", cheio2)):
        a, b = ap.rodada(mapa), ap.rodada(mapa)
        check("%s: duas rodadas no mesmo processo dão a mesma saída" % rotulo,
              json.dumps(a, sort_keys=False) == json.dumps(b, sort_keys=False))
        primeira = _saida(mapa, "1")
        check("%s: a rodada devolveu saída" % rotulo, primeira.strip() != "")
        check("%s: duas rodadas com semente de hash diferente batem byte a byte"
              % rotulo, primeira == _saida(mapa, "2"))

    check("a sonda de determinismo pegou o nível 1 vermelho",
          ap.rodada(cheio1)["parou_em"] == 1)
    check("e o nível 2 vermelho com o 1 verde",
          ap.rodada(cheio2)["parou_em"] == 2)

    print()
    print("FALHOU: %d" % len(FAILS) if FAILS else "OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
