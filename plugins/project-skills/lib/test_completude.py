#!/usr/bin/env python3
"""Suíte do completude.py — os quatro elos da cadeia, e o que falta em cada um."""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import completude as cp  # noqa: E402

FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


FEATURES = """# Funcionalidades

## E1 O cadastro
- **S-1 Entrar no sistema** · Art. 1 — corpo. CA: o critério.
- **S-2 Sair do sistema** · Art. 1 — corpo. CA: o critério.

## E2 O relatório
- **S-3 Ver o relatório** · Art. 2 — corpo. CA: o critério.
"""


LEI = """# A lei

## Artigo 1 · O cadastro
corpo.

## Artigo 2 · O relatório
corpo.

## Artigo 3 · O que ninguém construiu
corpo.
"""


# a mesma lei, com o placar que ela escreve sobre si mesma. O travessão carrega
# números que NÃO são da lista — é a forma real do placar do projeto.
PLACAR = LEI + """
## O placar de hoje

- **Com cobrador real:** Artigos 1 e 2
- **Sem cobrador:** Artigo 3 — o 1 e o 2 com furo nomeado acima.
"""


def plano(*itens):
    return {"id": "p", "phases": [{"id": "F1", "items": list(itens)}]}


def item(iid, requisito, status="todo", evidence=None):
    return {"id": iid, "requisito": requisito, "status": status,
            "evidence": evidence}


def falta(c, elo, chave):
    for e in c["elos"]:
        if e["elo"] == elo:
            return e["falta"][chave]
    raise KeyError(elo)


def decl(c, elo, chave):
    for e in c["elos"]:
        if e["elo"] == elo:
            return e["declarado"][chave]
    raise KeyError(elo)


def main():
    print("== elo 1 · feature → requisito ==")
    c = cp.cadeia(FEATURES, [])
    check("as features saem na ordem do documento",
          c["features"] == ["E1 O cadastro", "E2 O relatório"])
    check("feature que nenhum requisito detalha não aparece aqui (todas têm)",
          falta(c, "feature → requisito", "feature_sem_requisito") == [])

    vazia = FEATURES + "\n## E3 O que ninguém especificou\n"
    c = cp.cadeia(vazia, [])
    check("feature escrita sem requisito nenhum é acusada",
          falta(c, "feature → requisito", "feature_sem_requisito")
          == ["E3 O que ninguém especificou"])

    solto = "- **S-9 Fora de feature** · Art. 1 — corpo. CA: o critério.\n" + FEATURES
    c = cp.cadeia(solto, [])
    check("requisito escrito fora de feature nenhuma é acusado",
          falta(c, "feature → requisito", "requisito_sem_feature") == ["S-9"])

    c = cp.cadeia("", [])
    check("sem documento de features não há acusação de elo 1",
          falta(c, "feature → requisito", "feature_sem_requisito") == []
          and falta(c, "feature → requisito", "requisito_sem_feature") == [])

    print("== elo 2 · requisito → tarefa ==")
    c = cp.cadeia(FEATURES, [plano(item("F1.1", "S-1"))])
    check("requisito que nenhuma tarefa atende sai nomeado",
          falta(c, "requisito → tarefa", "requisito_sem_tarefa") == ["S-2", "S-3"])
    c = cp.cadeia(FEATURES, [plano(item("F1.1", ""), item("F1.2", "S-77"))])
    check("tarefa sem requisito sai nomeada",
          falta(c, "requisito → tarefa", "tarefa_sem_requisito") == ["F1.1"])
    check("tarefa que aponta requisito inexistente sai nomeada",
          falta(c, "requisito → tarefa", "requisito_inexistente")
          == [("F1.2", "S-77")])

    todas = [plano(item("F1.1", "S-1"), item("F1.2", "S-2"), item("F1.3", "S-3"))]
    artigos = cp.cobertura.le_artigos(LEI)
    c = cp.cadeia(FEATURES, todas, artigos=artigos)
    check("artigo da lei que nenhuma tarefa representa sai com número e título",
          falta(c, "requisito → tarefa", "artigo_sem_tarefa")
          == ["3 · O que ninguém construiu"])
    c = cp.cadeia(FEATURES, todas)
    check("sem a lei em mãos não há artigo a cobrar",
          falta(c, "requisito → tarefa", "artigo_sem_tarefa") == [])

    print("== o que a lei declara que ninguém cobre ==")
    check("os números saem da marca do texto, não do código",
          cp.cobertura.le_sem_cobrador(PLACAR) == {"3"})
    check("lei sem a linha do placar não declara nada",
          cp.cobertura.le_sem_cobrador(LEI) == set())
    provadas = [plano(item("F1.1", "S-1", "done", "a suíte passou, 12 de 12"),
                      item("F1.2", "S-2", "done", "a suíte passou, 12 de 12"),
                      item("F1.3", "S-3", "done", "a suíte passou, 12 de 12"))]
    c = cp.cadeia(FEATURES, provadas, artigos=artigos,
                  sem_cobrador=cp.cobertura.le_sem_cobrador(PLACAR))
    check("artigo sem cobrador sai declarado, não como furo",
          falta(c, "requisito → tarefa", "artigo_sem_tarefa") == []
          and decl(c, "requisito → tarefa", "artigo_sem_cobrador")
          == ["3 · O que ninguém construiu"])
    check("e ele NÃO entra na conta do verde: a cadeia fecha completa",
          c["completa"] is True)
    check("mas a declaração aparece no resumo, ao lado do elo completo",
          "⚪ 1 artigo_sem_cobrador" in cp.resumo(c))
    c = cp.cadeia(FEATURES, todas, artigos=artigos, sem_cobrador={"9"})
    check("artigo COM cobrador continua sendo furo",
          falta(c, "requisito → tarefa", "artigo_sem_tarefa")
          == ["3 · O que ninguém construiu"]
          and c["completa"] is False)

    dois = [plano(item("F1.1", "S-1")),
            {"id": "q", "phases": [{"id": "F2", "items": [item("F2.1", "S-2"),
                                                          item("F2.2", "S-3")]}]}]
    c = cp.cadeia(FEATURES, dois)
    check("requisito coberto por OUTRO plano não é órfão",
          falta(c, "requisito → tarefa", "requisito_sem_tarefa") == [])

    print("== elo 3 · tarefa → prova ==")
    p = plano(item("F1.1", "S-1", "done", "rodei a suíte e ela passou"),
              item("F1.2", "S-2", "done", "curta"),
              item("F1.3", "S-3", "done", None),
              item("F1.4", "S-1", "doing"))
    c = cp.cadeia(FEATURES, [p])
    check("tique com prova de verdade não é acusado",
          "F1.1" not in falta(c, "tarefa → prova", "tique_sem_prova"))
    check("tique com prova curta demais é acusado",
          "F1.2" in falta(c, "tarefa → prova", "tique_sem_prova"))
    check("tique sem prova nenhuma é acusado",
          "F1.3" in falta(c, "tarefa → prova", "tique_sem_prova"))
    check("tarefa não marcada é pendência, não mentira",
          falta(c, "tarefa → prova", "tarefa_pendente") == ["F1.4"]
          and "F1.4" not in falta(c, "tarefa → prova", "tique_sem_prova"))

    encerrado = dict(plano(item("F9.1", "S-1"),
                           item("F9.2", "S-2", "done", "curta")),
                     id="q", status="abandoned")
    c = cp.cadeia(FEATURES, [encerrado])
    check("passo pendente de plano encerrado não é tarefa_pendente",
          falta(c, "tarefa → prova", "tarefa_pendente") == [])
    check("mas tique sem prova em plano encerrado continua sendo mentira",
          falta(c, "tarefa → prova", "tique_sem_prova") == ["F9.2"])
    vivo = dict(plano(item("F8.1", "S-1")), id="v", status="active")
    check("e o plano vivo continua acusando a pendência dele",
          falta(cp.cadeia(FEATURES, [vivo, encerrado]),
                "tarefa → prova", "tarefa_pendente") == ["F8.1"])

    # plano abandonado não cobre requisito nenhum: se ele credita cobertura no
    # elo 2 e a pendência dele some no elo 3, a cadeia fecha verde sem uma
    # tarefa feita e sem uma prova.
    abandonado = dict(plano(item("F7.1", "S-1"), item("F7.2", "S-2"),
                            item("F7.3", "S-3")),
                      id="a", status="abandoned")
    c = cp.cadeia(FEATURES, [abandonado], **{
        "artigos": cp.cobertura.le_artigos(PLACAR),
        "sem_cobrador": cp.cobertura.le_sem_cobrador(PLACAR)})
    check("plano abandonado não credita cobertura de requisito",
          falta(c, "requisito → tarefa", "requisito_sem_tarefa")
          == ["S-1", "S-2", "S-3"])
    check("e a cadeia com só um plano abandonado NÃO fecha completa",
          c["completa"] is False)
    check("plano concluído continua creditando cobertura",
          falta(cp.cadeia(FEATURES, [dict(plano(
              item("F6.1", "S-1", "done", "a suíte passou, 12 de 12"),
              item("F6.2", "S-2", "done", "a suíte passou, 12 de 12"),
              item("F6.3", "S-3", "done", "a suíte passou, 12 de 12")),
              id="d", status="done")]),
              "requisito → tarefa", "requisito_sem_tarefa") == [])

    # `close` grava `abandoned` em QUALQUER encerramento parcial, e o que ficou
    # PROVADO ali é trabalho feito: descartar o plano inteiro acusava de órfão
    # requisito que tem tarefa pronta com prova.
    parcial = dict(plano(item("F5.1", "S-1", "done", "a suíte passou, 12 de 12"),
                         item("F5.2", "S-2", "done", "a suíte passou, 12 de 12"),
                         item("F5.3", "S-3")),
                   id="x", status="abandoned")
    check("do plano abandonado, só o passo provado credita cobertura",
          falta(cp.cadeia(FEATURES, [parcial]),
                "requisito → tarefa", "requisito_sem_tarefa") == ["S-3"])

    # o `status` do plano é escrito pelo modelo, não só pelo `close`: um plano
    # gravado `done` carregando passo `todo` existe em disco. Se o `done`
    # creditasse inteiro, esse passo cobriria requisito no elo 2 e sumiria no
    # elo 3 — o requisito sairia verde sem uma linha de prova.
    done_com_pendente = dict(plano(
        item("F4.1", "S-1", "done", "a suíte passou, 12 de 12"),
        item("F4.2", "S-2", "done", "a suíte passou, 12 de 12"),
        item("F4.3", "S-3")), id="w", status="done")
    c = cp.cadeia(FEATURES, [done_com_pendente])
    check("do plano concluído com passo pendente, só o provado credita cobertura",
          falta(c, "requisito → tarefa", "requisito_sem_tarefa") == ["S-3"])
    check("e a pendência dele não conta no elo 3, como em qualquer plano encerrado",
          falta(c, "tarefa → prova", "tarefa_pendente") == [])

    print("== a cadeia inteira ==")
    completo = plano(item("F1.1", "S-1", "done", "a suíte passou, 12 de 12"),
                     item("F1.2", "S-2", "done", "a suíte passou, 12 de 12"),
                     item("F1.3", "S-3", "done", "a suíte passou, 12 de 12"))
    lei_em_maos = {"artigos": cp.cobertura.le_artigos(PLACAR),
                   "sem_cobrador": cp.cobertura.le_sem_cobrador(PLACAR)}
    c = cp.cadeia(FEATURES, [completo], **lei_em_maos)
    check("cadeia sem furo nenhum sai completa", c["completa"] is True)
    check("e os três elos saem completos",
          [e["completo"] for e in c["elos"]] == [True, True, True])
    check("o resumo diz elo por elo", cp.resumo(c).count("✅") == 3)

    c = cp.cadeia(FEATURES, [plano(item("F1.1", "S-1"))])
    check("um furo em qualquer elo derruba a cadeia", c["completa"] is False)
    check("e o resumo nomeia o elo furado", "🔴 requisito → tarefa" in cp.resumo(c))
    check("a saída carrega o cruzamento que a produziu, para conferência",
          c["cobertura"]["total"] == 1)

    print("== o motor não conhece caminho deste repositório ==")
    fonte = open(cp.__file__, encoding="utf-8").read()
    check("nenhum caminho absoluto de máquina no motor",
          "/Users/" not in fonte and "plugins/project-skills" not in fonte)

    print("== documento ausente é lacuna nomeada, nunca verde ==")
    c = cp.cadeia("/nao/existe/features.md", [completo], **lei_em_maos)
    check("features.md ausente sai nomeado",
          c["lacunas"] == ["features.md ausente"])
    check("e a cadeia NÃO fecha completa", c["completa"] is False)
    # o elo 1 e o elo 3 ficam VERDES sobre o documento ausente — é justamente o
    # verde vazio que a lacuna desmente, e sem ela a saída dizia "completo".
    check("os elos que o documento ausente esvaziou saem verdes mesmo assim",
          [e["completo"] for e in c["elos"]] == [True, False, True])
    check("o resumo nomeia a lacuna antes dos elos",
          cp.resumo(c).splitlines()[0] == "🔴 lacuna — features.md ausente")
    check("documento vazio conta igual ao ausente",
          cp.cadeia("   ", [completo], **lei_em_maos)["lacunas"]
          == ["features.md ausente"])
    c = cp.cadeia(FEATURES, [completo])
    check("a lei ausente também sai nomeada",
          c["lacunas"] == ["constituicao.md ausente"] and c["completa"] is False)
    c = cp.cadeia("/nao/existe/features.md", [completo])
    check("os dois ausentes saem os dois",
          c["lacunas"] == ["features.md ausente", "constituicao.md ausente"])

    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "features.md")
        open(md, "w", encoding="utf-8").write(FEATURES)
        lei = os.path.join(d, "constituicao.md")
        open(lei, "w", encoding="utf-8").write(PLACAR)
        planos = os.path.join(d, "plans")
        os.makedirs(planos)
        with open(os.path.join(planos, "p.plan.json"), "w", encoding="utf-8") as fh:
            json.dump(completo, fh)
        r = subprocess.run([sys.executable, cp.__file__, md, planos, lei, "--json"],
                           capture_output=True, text=True, cwd=d,
                           stdin=subprocess.DEVNULL, start_new_session=True)
        check("a linha de comando roda de outra pasta e sai 0 na cadeia completa",
              r.returncode == 0)
        check("e devolve a cadeia em JSON",
              json.loads(r.stdout)["completa"] is True)
        r = subprocess.run([sys.executable, cp.__file__, md, os.path.join(d, "vazio"),
                            lei], capture_output=True, text=True, cwd=d,
                           stdin=subprocess.DEVNULL, start_new_session=True)
        check("pasta de planos ausente sai 1 e nomeia o elo furado",
              r.returncode == 1 and "requisito → tarefa" in r.stdout)
        r = subprocess.run([sys.executable, cp.__file__,
                            os.path.join(d, "nao-existe.md"), planos, lei],
                           capture_output=True, text=True, cwd=d,
                           stdin=subprocess.DEVNULL, start_new_session=True)
        check("caminho errado do features.md sai 1 e nomeia a lacuna",
              r.returncode == 1 and "🔴 lacuna — features.md ausente" in r.stdout
              and "✅ completo" not in r.stdout)
        r = subprocess.run([sys.executable, cp.__file__, md, planos],
                           capture_output=True, text=True, cwd=d,
                           stdin=subprocess.DEVNULL, start_new_session=True)
        check("sem a lei no comando sai 1 e nomeia a lacuna",
              r.returncode == 1 and "🔴 lacuna — constituicao.md ausente" in r.stdout)

    print()
    print("FALHOU: %d" % len(FAILS) if FAILS else "OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
