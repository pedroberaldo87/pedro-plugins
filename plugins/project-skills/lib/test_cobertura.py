#!/usr/bin/env python3
"""Suite do cobertura.py — o fio entre requisito e tarefa."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cobertura as cb  # noqa: E402

FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


PRD = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Jornada: Planejar o dia — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte com impacto explícito.
- **S-4.8 Janela de medicação como slot nobre** · F1 · Art. 6 — tarefa de maior fricção
  na janela matinal. CA: sugestão respeita horário real de medicação.
"""

# dois épicos: um completa um caminho de pessoa, o outro é agrupamento técnico
PRD_EPICOS = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Jornada: Planejar o dia — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte com impacto explícito.

## E7 — Infra de cache (F2)

- **S-7.1 Camada de cache** · F2 · Art. 6 — memória entre execuções.
  CA: segunda execução reaproveita o resultado.
- **S-7.2 Invalidação** · F2 — expira por versão.
  CA: bump de versão descarta o cache.
"""

# um requisito escrito sem critério de aceite — hoje ele fecha sem ninguém perguntar
PRD_SEM_CA = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Jornada: Planejar o dia — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte com impacto explícito.
- **S-4.9 Exportar o dia** · F1 · Jornada: Planejar o dia — gera um resumo em texto.
"""

# dois épicos escrevem o MESMO número — até aqui o segundo apagava o primeiro
PRD_REPETIDO = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Jornada: Planejar o dia — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte com impacto explícito.

## E7 — Infra de cache (F2)

- **S-4.3 Camada de cache** · F2 · Jornada: Planejar o dia — memória entre execuções.
  CA: segunda execução reaproveita o resultado.
"""

# um requisito cita artigo que a lei tem, o outro cita um que ela não tem
PRD_ARTIGOS = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Art. 6 — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte.
- **S-4.9 Exportar o dia** · F1 · Art. 42 — gera um resumo em texto.
  CA: o resumo sai em texto puro.
"""

# três funcionalidades: uma nasce de artigo, uma não nasce de nada, e uma o dono
# assume como escolha dele — esta última passa marcada, não acusada
PRD_SEM_ARTIGO = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Art. 6 — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte.
- **S-4.9 Exportar o dia** · F1 — gera um resumo em texto.
  CA: o resumo sai em texto puro.
- **S-4.10 Atalho de teclado** · F1 — abre o dia com uma tecla.
  Decisão: conforto meu, a lei não pede.
  CA: a tecla abre o dia.
"""

LEI = """\
# Constituição do projeto

## Artigo 6 · Estética
O corpo do artigo.

## Artigo 7 · Clareza da instrução
O corpo do artigo.
"""

# três funcionalidades contra o desenho: uma vive numa peça que existe, uma cita uma
# peça que o desenho não tem, e uma não diz onde vive
PRD_PECAS = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Peça: Motor de plano — custo 1-5 por tarefa.
  CA: dia com orçamento estourado retorna proposta de corte.
- **S-4.9 Exportar o dia** · F1 · Peça: Fila de e-mail — gera um resumo em texto.
  CA: o resumo sai em texto puro.
- **S-4.10 Atalho de teclado** · F1 — abre o dia com uma tecla.
  CA: a tecla abre o dia.
"""

# o desenho da arquitetura pretendida, no molde que a etapa 2 do /start escreve:
# só o item sob "As peças" é peça — fronteira e depósito de estado usam o MESMO item
# de lista em negrito e não podem virar peça
ARQUITETURA = """\
# Arquitetura pretendida

## As peças
- **Motor de plano** — responsável por montar o dia · **serve à meta:** previsibilidade
- **Guarda de estado** — responsável por onde o estado mora · **serve à meta:** durabilidade

## As fronteiras — quem pode chamar quem
- **Motor de plano → Guarda de estado** — pela porta de gravação
- **PROIBIDO: Ninguém chama o banco direto** — quebraria a fronteira do estado

## Onde o estado mora
- **Disco do projeto** — guarda o plano · **escreve:** Guarda de estado · **lê:** todos
"""

# três funcionalidades contra o desenho de funcionamento: uma aponta um passo do ciclo,
# uma aponta um passo que o desenho não tem, e uma não aponta passo nenhum
PRD_PASSOS = """\
## E4 — Planner determinístico (F1)

- **S-4.3 Orçamento de energia** · F1 · Passo: o sistema monta o dia — custo 1-5.
  CA: dia com orçamento estourado retorna proposta de corte.
- **S-4.9 Exportar o dia** · F1 · Passo: o sistema manda o dia por e-mail — resumo.
  CA: o resumo sai em texto puro.
- **S-4.10 Atalho de teclado** · F1 — abre o dia com uma tecla.
  CA: a tecla abre o dia.
"""

# o desenho de funcionamento, no molde que a etapa 5 do /start escreve: só o item
# numerado sob "O ciclo, do começo ao fim" é passo, e a proveniência (`← arquivo:linha`)
# não faz parte do texto do passo
BLUEPRINT = """\
# Como o sistema funciona

## O ciclo, do começo ao fim
1. o sistema monta o dia  ← journeys.md:4
2. o sistema avisa quem tem medicação na janela  ← journeys.md:9

## As peças que participam, e o que cada uma decide
1. Motor de plano — decide a ordem  ← architecture-intent.md:6
"""

JOURNEYS = """\
# Jornadas

## Planejar o dia
- **Ator:** quem toma a medicação

## Revisar a semana
- **Ator:** a mesma pessoa, no domingo
"""


def main():
    d = tempfile.mkdtemp(prefix="cob-")
    p = os.path.join(d, "PRD.md")
    open(p, "w", encoding="utf-8").write(PRD)

    reqs = cb.le_requisitos(p)
    check("acha os 2 requisitos", sorted(reqs) == ["S-4.3", "S-4.8"])
    check("extrai o critério de aceite",
          "proposta de corte" in reqs["S-4.3"]["ca"])
    check("extrai o artigo da lei", reqs["S-4.8"]["ancora"] == "Art. 6")
    check("requisito sem artigo fica com None", reqs["S-4.3"]["ancora"] is None)
    check("liga ao épico", reqs["S-4.3"]["epico"].startswith("E4"))

    plan = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"},
        {"id": "F1.2", "title": "b", "desc": "d", "requisito": "S-4.3"},
        {"id": "F1.3", "title": "c", "desc": "d"},
        {"id": "F1.4", "title": "e", "desc": "d", "requisito": "S-9.9"}]}]}
    m = cb.mapa(plan, reqs)
    check("2 tarefas cobertas", len(m["cobertas"]) == 2)
    check("1 tarefa sem requisito", m["sem_requisito"] == ["F1.3"])
    check("1 requisito órfão", m["orfaos"] == ["S-4.8"])
    check("1 citação inexistente", m["inexistentes"] == [("F1.4", "S-9.9")])
    check("agrupa por requisito", m["por_req"]["S-4.3"] == ["F1.1", "F1.2"])

    # o cruzamento com as jornadas, nas DUAS direções
    j = os.path.join(d, "journeys.md")
    open(j, "w", encoding="utf-8").write(JOURNEYS)
    jornadas = cb.le_jornadas(j)
    check("acha as 2 jornadas", jornadas == ["Planejar o dia", "Revisar a semana"])
    check("lê a jornada de origem do requisito",
          reqs["S-4.3"]["jornada"] == "Planejar o dia")
    check("requisito sem jornada citada fica com None", reqs["S-4.8"]["jornada"] is None)

    mj = cb.mapa(plan, reqs, jornadas)
    check("1 funcionalidade sem jornada de origem", mj["sem_jornada"] == ["S-4.8"])
    check("1 jornada que nenhuma funcionalidade atende",
          mj["jornadas_sem_funcionalidade"] == ["Revisar a semana"])
    rj = cb.resumo(mj)
    check("o resumo acusa as duas direções",
          "1 funcionalidade sem jornada" in rj and "1 jornada sem funcionalidade" in rj)

    # o épico que nenhuma funcionalidade liga a um caminho de pessoa
    pe = os.path.join(d, "PRD-epicos.md")
    open(pe, "w", encoding="utf-8").write(PRD_EPICOS)
    reqs_e = cb.le_requisitos(pe)
    plan_e = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"},
        {"id": "F2.1", "title": "b", "desc": "d", "requisito": "S-7.1"},
        {"id": "F2.2", "title": "c", "desc": "d", "requisito": "S-7.2"}]}]}
    me = cb.mapa(plan_e, reqs_e, jornadas)
    check("1 épico sem jornada de origem",
          [e.split(" ")[0] for e in me["epicos_sem_jornada"]] == ["E7"])
    check("o resumo acusa o épico sem jornada",
          "1 épico sem jornada" in cb.resumo(me))

    # o requisito escrito sem critério de aceite
    pc = os.path.join(d, "PRD-sem-ca.md")
    open(pc, "w", encoding="utf-8").write(PRD_SEM_CA)
    reqs_c = cb.le_requisitos(pc)
    check("requisito sem critério fica com None", reqs_c["S-4.9"]["ca"] is None)
    plan_c = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"},
        {"id": "F1.2", "title": "b", "desc": "d", "requisito": "S-4.9"}]}]}
    mc = cb.mapa(plan_c, reqs_c, jornadas)
    check("1 requisito sem critério de aceite", mc["sem_ca"] == ["S-4.9"])
    check("o resumo acusa o requisito sem critério",
          "1 requisito sem critério" in cb.resumo(mc))
    check("requisito com critério não é acusado", "S-4.3" not in mc["sem_ca"])

    # o número escrito duas vezes — some uma descrição, e isso tem que aparecer
    pr = os.path.join(d, "PRD-repetido.md")
    open(pr, "w", encoding="utf-8").write(PRD_REPETIDO)
    reqs_r = cb.le_requisitos(pr)
    check("o número repetido fica marcado", reqs_r["S-4.3"]["repetido"] is True)
    check("vale a PRIMEIRA descrição, não a segunda",
          reqs_r["S-4.3"]["titulo"] == "Orçamento de energia")
    plan_r = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"}]}]}
    mr = cb.mapa(plan_r, reqs_r, jornadas)
    check("1 requisito com número repetido", mr["repetidos"] == ["S-4.3"])
    check("o resumo acusa o número repetido",
          "1 requisito com número repetido" in cb.resumo(mr))
    check("número escrito uma vez só não é acusado",
          cb.mapa(plan, reqs, jornadas)["repetidos"] == []
          and "repetido" not in cb.resumo(cb.mapa(plan, reqs, jornadas)))

    # a citação de artigo conferida contra a lei do projeto
    pa = os.path.join(d, "PRD-artigos.md")
    open(pa, "w", encoding="utf-8").write(PRD_ARTIGOS)
    lei = os.path.join(d, "constituicao.md")
    open(lei, "w", encoding="utf-8").write(LEI)
    reqs_a = cb.le_requisitos(pa)
    artigos = cb.le_artigos(lei)
    check("acha os 2 artigos da lei", artigos == ["6", "7"])
    plan_a = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"},
        {"id": "F1.2", "title": "b", "desc": "d", "requisito": "S-4.9"}]}]}
    ma = cb.mapa(plan_a, reqs_a, jornadas, artigos)
    check("1 requisito citando artigo que a lei não tem",
          ma["artigos_inexistentes"] == [("S-4.9", "Art. 42")])
    check("o resumo acusa o artigo inexistente",
          "1 requisito citando artigo que a lei não tem" in cb.resumo(ma))
    # sem a lei em mãos não há com o que cruzar — ninguém é acusado
    ma0 = cb.mapa(plan_a, reqs_a, jornadas)
    check("sem a lei, ninguém é acusado de citar artigo",
          ma0["artigos_inexistentes"] == []
          and "artigo" not in cb.resumo(ma0))
    check("documento da lei ausente devolve []",
          cb.le_artigos(os.path.join(d, "nao-existe.md")) == [])

    # a funcionalidade que não nasce de artigo nenhum — e a saída declarada
    psa = os.path.join(d, "PRD-sem-artigo.md")
    open(psa, "w", encoding="utf-8").write(PRD_SEM_ARTIGO)
    reqs_sa = cb.le_requisitos(psa)
    check("lê a decisão declarada",
          (reqs_sa["S-4.10"]["decisao"] or "").startswith("conforto meu"))
    check("quem não declarou fica com None", reqs_sa["S-4.9"]["decisao"] is None)
    plan_sa = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"},
        {"id": "F1.2", "title": "b", "desc": "d", "requisito": "S-4.9"},
        {"id": "F1.3", "title": "c", "desc": "d", "requisito": "S-4.10"}]}]}
    msa = cb.mapa(plan_sa, reqs_sa, jornadas, artigos)
    check("1 funcionalidade sem artigo da lei", msa["sem_artigo"] == ["S-4.9"])
    check("a declarada passa marcada, não acusada", msa["decididas"] == ["S-4.10"])
    check("o resumo acusa a funcionalidade sem artigo",
          "1 funcionalidade sem artigo da lei" in cb.resumo(msa))
    check("e marca a declarada como decisão sua",
          "1 funcionalidade por decisão declarada" in cb.resumo(msa))
    # sem a lei em mãos não há com o que cruzar — ninguém é acusado nem marcado
    msa0 = cb.mapa(plan_sa, reqs_sa, jornadas)
    check("sem a lei, ninguém é acusado de nascer sem artigo",
          msa0["sem_artigo"] == [] and msa0["decididas"] == []
          and "sem artigo" not in cb.resumo(msa0))

    # o cruzamento com as peças da arquitetura pretendida, nas duas pontas
    pp = os.path.join(d, "PRD-pecas.md")
    open(pp, "w", encoding="utf-8").write(PRD_PECAS)
    arq = os.path.join(d, "architecture-intent.md")
    open(arq, "w", encoding="utf-8").write(ARQUITETURA)
    reqs_p = cb.le_requisitos(pp)
    pecas = cb.le_pecas(arq)
    check("acha as 2 peças do desenho", pecas == ["Motor de plano", "Guarda de estado"])
    check("fronteira escrita fora da seção de peças não vira peça",
          not [p for p in pecas if "banco direto" in p])
    check("depósito de estado, escrito no mesmo formato, não vira peça",
          "Disco do projeto" not in pecas)
    check("lê a peça que o requisito diz habitar",
          reqs_p["S-4.3"]["peca"] == "Motor de plano")
    check("requisito sem peça citada fica com None", reqs_p["S-4.10"]["peca"] is None)
    plan_p = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"},
        {"id": "F1.2", "title": "b", "desc": "d", "requisito": "S-4.9"},
        {"id": "F1.3", "title": "c", "desc": "d", "requisito": "S-4.10"}]}]}
    mp = cb.mapa(plan_p, reqs_p, jornadas, artigos, pecas)
    check("1 funcionalidade sem peça da arquitetura", mp["sem_peca"] == ["S-4.10"])
    check("1 requisito citando peça que a arquitetura não tem",
          mp["pecas_inexistentes"] == [("S-4.9", "Fila de e-mail")])
    check("quem cita peça que existe não é acusado",
          "S-4.3" not in mp["sem_peca"]
          and "S-4.3" not in [r for r, _ in mp["pecas_inexistentes"]])
    rp = cb.resumo(mp)
    check("o resumo acusa a funcionalidade sem peça",
          "1 funcionalidade sem peça da arquitetura" in rp)
    check("o resumo acusa a peça inexistente",
          "1 requisito citando peça que a arquitetura não tem" in rp)
    # sem o desenho em mãos não há com o que cruzar — ninguém é acusado
    mp0 = cb.mapa(plan_p, reqs_p, jornadas, artigos)
    check("sem o desenho, ninguém é acusado de peça",
          mp0["sem_peca"] == [] and mp0["pecas_inexistentes"] == []
          and "peça" not in cb.resumo(mp0))
    check("documento da arquitetura ausente devolve []",
          cb.le_pecas(os.path.join(d, "nao-existe.md")) == [])

    # o cruzamento com o desenho de funcionamento, nas DUAS direções
    ppa = os.path.join(d, "PRD-passos.md")
    open(ppa, "w", encoding="utf-8").write(PRD_PASSOS)
    bp = os.path.join(d, "blueprint.md")
    open(bp, "w", encoding="utf-8").write(BLUEPRINT)
    reqs_pa = cb.le_requisitos(ppa)
    ciclo = cb.le_passos(bp)
    check("acha os 2 passos do ciclo",
          ciclo == ["o sistema monta o dia",
                    "o sistema avisa quem tem medicação na janela"])
    check("item numerado fora da seção do ciclo não vira passo",
          not [p for p in ciclo if "Motor de plano" in p])
    check("lê o passo do ciclo que o requisito atende",
          reqs_pa["S-4.3"]["passo"] == "o sistema monta o dia")
    check("requisito sem passo citado fica com None", reqs_pa["S-4.10"]["passo"] is None)
    plan_pa = {"id": "p", "title": "t", "phases": [{"id": "F1", "title": "f", "items": [
        {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-4.3"},
        {"id": "F1.2", "title": "b", "desc": "d", "requisito": "S-4.9"},
        {"id": "F1.3", "title": "c", "desc": "d", "requisito": "S-4.10"}]}]}
    mpa = cb.mapa(plan_pa, reqs_pa, jornadas, artigos, pecas, ciclo)
    check("2 funcionalidades sem passo do ciclo — a que não cita e a que cita um que não existe",
          mpa["sem_passo"] == ["S-4.10", "S-4.9"])
    check("1 passo do ciclo que nenhuma funcionalidade atende",
          mpa["passos_sem_funcionalidade"]
          == ["o sistema avisa quem tem medicação na janela"])
    check("quem aponta passo que existe não é acusado", "S-4.3" not in mpa["sem_passo"])
    rpa = cb.resumo(mpa)
    check("o resumo acusa as duas direções do ciclo",
          "2 funcionalidades sem passo do ciclo" in rpa
          and "1 passo do ciclo sem funcionalidade" in rpa)
    # sem o desenho em mãos não há com o que cruzar — ninguém é acusado
    mpa0 = cb.mapa(plan_pa, reqs_pa, jornadas, artigos, pecas)
    check("sem o desenho de funcionamento, ninguém é acusado de passo",
          mpa0["sem_passo"] == [] and mpa0["passos_sem_funcionalidade"] == []
          and "passo" not in cb.resumo(mpa0))
    check("documento do desenho ausente devolve []",
          cb.le_passos(os.path.join(d, "nao-existe.md")) == [])

    # sem documento de jornadas não há com o que cruzar — e [] não acusa ninguém
    m0 = cb.mapa(plan, reqs)
    check("sem jornadas, ninguém é acusado",
          m0["sem_jornada"] == [] and m0["jornadas_sem_funcionalidade"] == []
          and m0["epicos_sem_jornada"] == [])
    check("e o resumo não fala de jornada", "jornada" not in cb.resumo(m0))
    check("todos com critério, o resumo cala", "critério" not in cb.resumo(m0))
    check("documento de jornadas ausente devolve []",
          cb.le_jornadas(os.path.join(d, "nao-existe.md")) == [])

    r = cb.resumo(m)
    check("o resumo traz os quatro números",
          all(x in r for x in ("4 tarefas", "2 com requisito", "1 sem", "1 requisito sem")))
    # o plural vem do helper, não de "(s)" fixo — texto que o dono lê não escreve "(s)"
    um = cb.resumo({"total": 1, "cobertas": [], "sem_requisito": ["F1.1"],
                    "orfaos": ["S-1.1"], "inexistentes": [], "por_req": {}})
    check("plural concorda no singular", "1 tarefa ·" in um and "1 requisito sem" in um)
    check("e no plural", "4 tarefas" in r)

    print()
    print("FALHOU: %d" % len(FAILS) if FAILS else "OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
