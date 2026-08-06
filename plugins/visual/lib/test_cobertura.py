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
    open(p, "w").write(PRD)

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
    open(j, "w").write(JOURNEYS)
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
    open(pe, "w").write(PRD_EPICOS)
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
    open(pc, "w").write(PRD_SEM_CA)
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
