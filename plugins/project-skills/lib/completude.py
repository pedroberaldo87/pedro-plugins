#!/usr/bin/env python3
"""A cadeia inteira: feature → requisito → tarefa → prova do tique.

`cobertura.py` liga requisito a tarefa e para aí — o elo de cima (a feature que
ninguém especificou) e o de baixo (a tarefa marcada sem prova) não aparecem em
lugar nenhum. Aqui a cadeia sai com os quatro elos, e cada elo devolve o que
falta NELE: dizer "falta cobertura" sem dizer em que ponto do fio ela falta é o
mesmo silêncio que o cruzamento existe pra acabar.

Nada aqui reparseia markdown nem lê plano à mão: a feature e o requisito saem do
`cobertura`, a tarefa e a prova saem do `plan_state`. Duas leituras do mesmo
arquivo divergem, e a que diverge é sempre a mais nova.

O módulo não conhece caminho de repositório nenhum — recebe a fonte das features
e a pasta dos planos de quem chama.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cobertura  # noqa: E402
import plan_state  # noqa: E402

# a feature é o cabeçalho `## E1 …` do features.md — a camada acima do requisito,
# que o `cobertura` já sabe achar mas só usa como rótulo de agrupamento.
FEATURE_RE = cobertura.EPICO_RE


def le_features(fonte):
    """Os nomes das features, na ordem do documento.

    `fonte` é o caminho do features.md OU o texto direto, a mesma regra do
    `cobertura`. Documento ausente devolve [] — e [] não acusa ninguém.
    """
    return [m.group(1).strip() for m in FEATURE_RE.finditer(cobertura._texto(fonte))]


def lacunas(features, cruzamentos):
    """Os documentos que a medição precisava ler e não achou, nomeados.

    A regra do "[] não acusa ninguém" nasceu para o projeto que ainda não
    escreveu o documento — e ela transformava caminho errado em verde: a medição
    apontada para um features.md inexistente lia "", não achava feature nenhuma,
    não achava requisito nenhum, e imprimia "completo". Ausência não é cadeia
    cumprida; é medição que não aconteceu, e o nome do que falta sai aqui.

    O documento vazio conta igual ao ausente: os dois deixam o cruzamento sem o
    que cruzar, e distinguir os dois não muda o que o dono tem que fazer.
    """
    out = []
    if not cobertura._texto(features).strip():
        out.append("features.md ausente")
    if not cruzamentos.get("artigos"):
        out.append("constituicao.md ausente")
    return out


def _plano_unico(planos):
    """Os planos do projeto lidos como um só, para o cruzamento que já existe.

    `cobertura.mapa` recebe UM plano. O projeto tem vários, e requisito atendido
    por outro plano é requisito atendido — juntar as fases é o que impede a
    cadeia de acusar órfão que na verdade está coberto na porta ao lado.
    """
    return {"phases": [ph for p in planos for ph in p.get("phases", [])]}


def cadeia(features, planos, **cruzamentos):
    """Os quatro elos, cada um com o que falta nele.

    `features` é o caminho do features.md ou o texto; `planos` é a lista que
    `plan_state.list_plans` devolve. `cruzamentos` são os argumentos extras de
    `cobertura.mapa` (jornadas, artigos, peças, passos), repassados intactos.

    Elo 1 — feature → requisito: feature escrita que nenhum requisito detalha, e
    requisito escrito fora de feature nenhuma. Sem features no documento os dois
    baldes ficam vazios: sem com o que cruzar não há acusação — e é por isso que
    o documento que falta sai nomeado em `lacunas`, e sozinho já derruba
    `completa`. Balde vazio por ausência não é elo cumprido.

    Elo 2 — requisito → tarefa: é o `cobertura.mapa`, citado, não recalculado.
    Sai também o artigo da lei que nenhuma tarefa representa (`artigo_sem_tarefa`),
    cada um com o número e o título — `"6 · Estética"`, como `cobertura.le_artigos`
    devolve, porque "6" sozinho não diz a ninguém o que ficou de fora. Sem
    `artigos=` entre os cruzamentos o balde fica vazio: sem lei em mãos não há
    artigo a cobrar. O artigo que a própria lei declara sem cobrador não entra aí:
    ele sai em `declarado` (`artigo_sem_cobrador`), que é o que o programa não sabe
    medir — declarado sempre, contado nunca, nem como furo nem como verde.

    Elo 3 — tarefa → prova: `plan_state` já exige prova no tique, então aqui é
    leitura. Tarefa marcada como feita com prova ausente ou curta demais é
    MENTIRA (`tique_sem_prova`); tarefa que ainda não foi marcada é só trabalho
    que falta (`tarefa_pendente`) — misturar as duas apagaria a única das duas
    que é defeito.
    """
    falta_doc = lacunas(features, cruzamentos)
    reqs = cobertura.le_requisitos(features)
    nomes = le_features(features)
    m = cobertura.mapa(_plano_unico(planos), reqs, **cruzamentos)

    detalhada = {d.get("epico") for d in reqs.values()}
    feature_sem_requisito = [f for f in nomes if f not in detalhada]
    requisito_sem_feature = sorted(r for r, d in reqs.items()
                                   if nomes and not d.get("epico"))

    tique_sem_prova, tarefa_pendente = [], []
    for p in planos:
        for _, it in plan_state.iter_items(p):
            prova = str(it.get("evidence") or "").strip()
            if it.get("status") == "done":
                if len(prova) < plan_state.EVIDENCE_MIN:
                    tique_sem_prova.append(it["id"])
            else:
                tarefa_pendente.append(it["id"])

    elos = [
        {"elo": "feature → requisito",
         "falta": {"feature_sem_requisito": feature_sem_requisito,
                   "requisito_sem_feature": requisito_sem_feature}},
        {"elo": "requisito → tarefa",
         "falta": {"requisito_sem_tarefa": m["orfaos"],
                   "tarefa_sem_requisito": m["sem_requisito"],
                   "requisito_inexistente": m["inexistentes"],
                   "artigo_sem_tarefa": m["artigos_sem_tarefa"]},
         "declarado": {"artigo_sem_cobrador": m["artigos_sem_cobrador"]}},
        {"elo": "tarefa → prova",
         "falta": {"tique_sem_prova": tique_sem_prova,
                   "tarefa_pendente": tarefa_pendente}},
    ]
    for e in elos:
        e.setdefault("declarado", {})
        e["completo"] = not any(e["falta"].values())
    return {"features": nomes, "requisitos": sorted(reqs),
            "elos": elos, "cobertura": m, "lacunas": falta_doc,
            "completa": not falta_doc and all(e["completo"] for e in elos)}


def resumo(c):
    """Uma linha por elo, nomeando o elo e quanto falta nele."""
    # a lacuna vem ANTES dos elos: ela diz que a medição não aconteceu, e elo
    # verde medido sobre documento ausente é o verde que ela desmente.
    linhas = ["🔴 lacuna — %s" % doc for doc in c.get("lacunas", [])]
    for e in c["elos"]:
        if e["completo"]:
            linhas.append("✅ %s — completo" % e["elo"])
        else:
            falhas = ", ".join("%d %s" % (len(v), k)
                               for k, v in e["falta"].items() if v)
            linhas.append("🔴 %s — %s" % (e["elo"], falhas))
        # o que o programa não sabe medir sai JUNTO do elo, verde ou vermelho: elo
        # completo com declaração pendurada é elo completo NAQUILO QUE SE MEDE, e
        # esconder a declaração no verde é o "cem por cento" que ela desmente.
        for k, v in e.get("declarado", {}).items():
            if v:
                linhas.append("   ⚪ %d %s — depende de julgamento, fora da conta"
                              % (len(v), k))
    return "\n".join(linhas)


def main(argv):
    if len(argv) < 3:
        print("uso: completude.py <features.md> <pasta-dos-planos> "
              "[<constituicao.md>] [--json]", file=sys.stderr)
        return 2
    # a lei entra por argumento porque sem ela a medição não fecha: ausente, ela
    # sai nomeada em `lacunas` em vez de virar balde vazio que ninguém lê.
    lei = argv[3] if len(argv) > 3 and not argv[3].startswith("--") else ""
    c = cadeia(argv[1], plan_state.list_plans(argv[2]),
               artigos=cobertura.le_artigos(lei),
               sem_cobrador=cobertura.le_sem_cobrador(lei))
    if "--json" in argv:
        print(json.dumps(c, ensure_ascii=False, indent=2))
    else:
        print(resumo(c))
    return 0 if c["completa"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
