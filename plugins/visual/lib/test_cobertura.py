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

- **S-4.3 Orçamento de energia** · F1 — custo 1-5 por tarefa. CA: dia com orçamento
  estourado retorna proposta de corte com impacto explícito.
- **S-4.8 Janela de medicação como slot nobre** · F1 · Art. 6 — tarefa de maior fricção
  na janela matinal. CA: sugestão respeita horário real de medicação.
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
