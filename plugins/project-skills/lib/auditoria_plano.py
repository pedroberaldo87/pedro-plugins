#!/usr/bin/env python3
"""As três auditorias do plano, num programa só, na ordem — e a ordem é `if`.

Precedência escrita em prosa é precedência que a rodada seguinte ignora: alguém lê
"o nível 2 só depois do 1", acha o nível 1 ruidoso e vai direto medir cobertura de
spec contra um plano que contradiz a lei do projeto. Aqui a ordem não é recomendação:
com o nível 1 vermelho a função RETORNA, e a chave `nivel2` não existe na saída. Não
há resultado de nível 2 para ler, então não há como lê-lo fora de hora.

A entrada é o dicionário que `cobertura.mapa` devolve — não o caminho de arquivo
nenhum. Quem lê documento é o cruzamento; este módulo só ordena o que ele apurou, e
por isso não conhece a pasta de plugin vizinho nenhum.
"""

import re

# Nível 1 — o plano contradiz a documentação canônica. Cada balde é um jeito de
# contradizer: citar o que a lei/arquitetura/desenho não tem, ou não citar nada.
#
# `artigos_sem_tarefa` NÃO entra aqui, e não é esquecimento: ele mede a lei INTEIRA
# contra a união dos planos, e o mapa que chega neste módulo é de UM plano só. Medido
# aqui, todo plano parcial fica vermelho para sempre — os níveis 2 e 3 viram
# inalcançáveis e o laço passa a inventar tarefa de artigo que este plano nunca se
# propôs a tratar. Quem faz essa conta de projeto é `completude.py`, sobre a união.
NIVEL1 = [
    ("pronto_sem_espera",
     "o pronto depende de ato do dono e não declara espera_dono"),
    ("artigos_inexistentes", "cita artigo que a lei não tem"),
    ("pecas_inexistentes", "cita peça que a arquitetura não tem"),
    ("inexistentes", "cita requisito que não existe"),
    ("repetidos", "número de requisito escrito duas vezes"),
    ("sem_artigo", "não nasce de artigo nenhum da lei"),
    ("sem_jornada", "não nasce de caminho de pessoa nenhum"),
    ("sem_peca", "não diz em que peça da arquitetura vive"),
    ("sem_passo", "não atende passo nenhum do ciclo"),
]

# Nível 2 — a spec aprovada cabe inteira no plano. Aqui não há contradição: há
# pedaço da spec que ninguém atende, e tarefa que não atende pedaço nenhum.
NIVEL2 = [
    ("orfaos", "requisito que nenhuma tarefa atende"),
    ("sem_requisito", "tarefa que não atende requisito nenhum"),
    ("sem_ca", "requisito sem critério de aceite"),
    ("jornadas_sem_funcionalidade", "jornada que nenhuma funcionalidade atende"),
    ("passos_sem_funcionalidade", "passo do ciclo que ninguém atende"),
    ("epicos_sem_jornada", "épico sem caminho de pessoa nenhum"),
]

# Nível 3 — julgamento de agente. Não é uma pergunta só: são os TRÊS PÉS de
# `_shared/dimensoes-de-revisao.md`, com o nome e o critério de lá, não redigidos de
# novo. Saírem nomeados é o que impede o agente de medir um e achar que mediu a
# coerência inteira — pé que ele não mediu, ele declara que não mediu.
NIVEL3 = [
    ("qualidade",
     "o que está escrito está certo? Reprova: bug, regressão, contrato quebrado "
     "entre as pontas, caso de borda, segurança. Lint, type-check e teste vermelho "
     "NÃO entram aqui — são do portão mecânico."),
    ("cobertura por finalidade",
     "o que foi construído tem como falhar calado? Reprova: finalidade da spec sem "
     "teste que MORDA — o que existe cai num dos cinco antipadrões, ou não existe "
     "teste nenhum. A prova de que morde é a MUTAÇÃO, não a leitura."),
    ("coerência com a régua",
     "a obra respeita o que o projeto acordou? Reprova: passagem citada de lei ou "
     "acordo que a obra viola — o que vale como régua é o que o doc-load lista, e "
     "mapa minerado nunca reprova. Ausência de régua não é achado."),
]


# Os três baldes do nível 1 — a mesma contradição tem três causas possíveis, e só uma
# delas se conserta sozinha. O plano errado se reescreve; a doc vencida e a doc em
# conflito são pergunta para o dono, porque mexer em documento canônico para calar um
# achado é o jeito mais rápido de perder a lei do projeto.
PLANO_ERRADO = "plano-errado"
DOC_VENCIDA = "doc-vencida"
DOC_EM_CONFLITO = "doc-em-conflito"

# O que o dono é chamado a decidir em cada balde que para o laço.
PERGUNTA = {
    DOC_VENCIDA: "a doc não acompanhou o que já existe — quem muda é a doc ou o plano?",
    DOC_EM_CONFLITO: "dois documentos canônicos discordam — qual deles vale?",
}


# O vocabulário do ato do dono — o que só ele pode fazer (`plan/SKILL.md`, passo 5,
# classe 1). Tarefa cujo `pronto` pede um destes e não declara `espera_dono` é tarefa
# que trava a noite: o executor chega no critério, não tem como cumpri-lo, e a rodada
# queima. Quem declarou a espera passa — a espera é justamente a declaração.
# ponytail: casamento por prefixo, sem análise de frase — "aprova" dentro de outra
# oração acusa junto; se o ruído incomodar, o passo seguinte é olhar a oração do verbo.
ATO_DO_DONO = re.compile(
    r"deploy|publica|aprova|credencia|acesso|compra", re.IGNORECASE)


def _pronto_sem_espera(mapa):
    """Ids das tarefas cujo `pronto` pede ato do dono sem espera declarada.

    A lista de tarefas chega em `tarefas` (o que o `.plan.json` tem: `id`, `pronto`,
    `espera_dono`). Sem ela o balde fica vazio, como todo cruzamento sem com o que
    cruzar — acusar todo mundo seria ruído, não cobrança.
    """
    out = []
    for t in mapa.get("tarefas") or []:
        if str(t.get("espera_dono") or "").strip():
            continue
        if ATO_DO_DONO.search(str(t.get("pronto") or "")):
            out.append(str(t.get("id")))
    return out


def _alvo(item):
    return " ".join(str(p) for p in item) if isinstance(item, tuple) else str(item)


def _achados(mapa, baldes):
    """Uma linha por item acusado, com o nome do balde que o acusou."""
    out = []
    for chave, motivo in baldes:
        for item in mapa.get(chave) or []:
            out.append("%s — %s" % (_alvo(item), motivo))
    return out


def _nivel(mapa, baldes):
    achados = _achados(mapa, baldes)
    return {"achados": achados, "vermelho": bool(achados)}


def _classifica(mapa):
    """Cada achado de nível 1 num dos três baldes, com quem segue e quem para.

    A causa não se deduz do achado: "cita artigo que a lei não tem" tanto pode ser
    plano inventando artigo quanto lei atrasada. Quem já sabe a causa escreve em
    `classificacao` (alvo → balde); o que ninguém classificou é plano errado, que é
    a única causa que o laço tem autoridade para consertar sozinho.
    """
    dito = mapa.get("classificacao") or {}
    baldes = {PLANO_ERRADO: [], DOC_VENCIDA: [], DOC_EM_CONFLITO: []}
    perguntas = []
    for chave, motivo in NIVEL1:
        for item in mapa.get(chave) or []:
            alvo = _alvo(item)
            classe = dito.get(alvo, PLANO_ERRADO)
            if classe not in baldes:
                classe = PLANO_ERRADO
            baldes[classe].append({"alvo": alvo, "motivo": motivo})
            if classe in PERGUNTA:
                perguntas.append("%s — %s: %s" % (alvo, motivo, PERGUNTA[classe]))
    return {"baldes": baldes,
            "conserta": [a["alvo"] for a in baldes[PLANO_ERRADO]],
            "perguntas": perguntas,
            "devolve_ao_dono": bool(perguntas)}


def audita(mapa, limites_aceitos=()):
    """Roda os níveis na ordem e para no primeiro vermelho.

    O `nivel1` vem com os achados já repartidos em `baldes`: `conserta` é o que o laço
    segue consertando, e `devolve_ao_dono` com `perguntas` é o que o para — doc vencida
    e doc em conflito não se consertam por conta própria.

    Devolve sempre `nivel1` e `parou_em`. `nivel2` só existe quando o nível 1 está
    verde; `nivel3` só quando os dois estão. O nível 3 é julgamento de agente, então
    o programa não o declara verde: ele sai `pendente`, com os três pés nomeados e o
    critério que reprova cada um, para o agente preencher.

    `limites_aceitos` é a lista de alvos cujo achado o dono aceitou com motivo
    escrito (`.claude/limites-aceitos.md`). Achado aceito continua LISTADO — a
    transparência não se negocia — mas deixa de segurar a descida e sai de
    `conserta`: sem isso, dois aceitos no nível 1 deixavam o nível 2 sem medir
    para sempre, e o laço tentava consertar o que o dono mandou não consertar.
    """
    mapa = dict(mapa or {})
    mapa["pronto_sem_espera"] = _pronto_sem_espera(mapa)
    aceitos = set(limites_aceitos or ())

    def _vivos(nivel):
        return [a for a in nivel["achados"] if a.split(" — ")[0] not in aceitos]

    n1 = _nivel(mapa, NIVEL1)
    n1.update(_classifica(mapa))
    n1["conserta"] = [a for a in n1["conserta"] if a not in aceitos]
    vivos1 = _vivos(n1)
    n1["vermelho"] = bool(vivos1)
    if vivos1:
        return {"nivel1": n1, "parou_em": 1}

    n2 = _nivel(mapa, NIVEL2)
    vivos2 = _vivos(n2)
    n2["vermelho"] = bool(vivos2)
    if vivos2:
        return {"nivel1": n1, "nivel2": n2, "parou_em": 2}

    return {"nivel1": n1, "nivel2": n2,
            "nivel3": {"pendente": True,
                       "nota": "coerência do plano — julgamento de agente",
                       "pes": [{"pe": nome, "reprova": criterio}
                               for nome, criterio in NIVEL3]},
            "parou_em": 3}


def _bloqueios(resultado, limites_aceitos):
    """Achados de severidade real que limite aceito nenhum cobre.

    Severidade real é nível 1 e nível 2 — o nível 3 é julgamento de agente e não
    entra na conta. O limite aceito é escrito por alvo, e o alvo é o começo da
    linha do achado, antes do travessão.
    """
    aceitos = set(limites_aceitos or ())
    out = []
    for nivel in ("nivel1", "nivel2"):
        for achado in (resultado.get(nivel) or {}).get("achados") or []:
            if achado.split(" — ")[0] in aceitos:
                continue
            out.append(achado)
    return out


def rodada(mapa, limites_aceitos=()):
    """Uma rodada do laço: audita e já diz, em campo, se ela fechou.

    `limpa` é conta feita sobre os achados desta rodada, não frase que alguém lê
    e interpreta: sobrou bloqueio, ou há pergunta pendente ao dono, a rodada não
    está limpa. Sem isso o laço não termina — alguém desiste em silêncio e o
    resultado parece pronto.
    """
    r = audita(mapa, limites_aceitos)
    r["limites_aceitos"] = list(limites_aceitos or ())
    r["bloqueios"] = _bloqueios(r, limites_aceitos)
    r["limpa"] = not r["bloqueios"] and not r["nivel1"]["devolve_ao_dono"]
    return r


# O veredito é campo que o auditor escreve. Se ele viesse no mapa, quem monta assinaria
# a própria aprovação — então o que a montagem entrega é limpo destas chaves antes de
# entrar na auditoria.
VEREDITO = ("nivel1", "nivel2", "nivel3", "parou_em",
            "bloqueios", "limpa", "limites_aceitos")


def _so_o_apurado(mapa):
    return {k: v for k, v in (mapa or {}).items() if k not in VEREDITO}


def ciclo(monta, limites_aceitos=(), maximo=5):
    """O laço como script: monta, audita na linha seguinte, para na rodada limpa.

    `monta` é de fora — recebe a rodada anterior (`None` na primeira) e devolve o mapa.
    Quem monta não audita: o mapa entra pelo `_so_o_apurado`, que apaga qualquer
    veredito escrito nele, e a nota de aprovação sai do `rodada`, sempre. Entre a
    montagem e a auditoria não há `if` nenhum — não é recomendação de ordem, é a linha
    de baixo. A parada é a rodada limpa; `maximo` só impede o laço infinito, e estourá-lo
    é não ter fechado.
    """
    rodadas = []
    anterior = None
    for _ in range(maximo):
        mapa = _so_o_apurado(monta(anterior))
        r = rodada(mapa, limites_aceitos)
        rodadas.append(r)
        if r["limpa"]:
            break
        anterior = r
    fechou = bool(rodadas) and rodadas[-1]["limpa"]
    return {"rodadas": rodadas,
            "limpa": fechou,
            "fechou_em": len(rodadas) if fechou else None}


def laco(mapas, limites_aceitos=()):
    """Roda uma rodada por mapa e para na primeira que fecha.

    A decisão de rodar de novo sai dos achados da rodada anterior — a que acabou
    de rodar. Acabaram os mapas sem rodada limpa, `fechou_em` é `None`: o laço
    não fechou, e não há como declarar que fechou.

    É o `ciclo` com a montagem já feita: a lista de mapas é o montador. Um laço só,
    para que não exista um segundo caminho em que a auditoria fique de fora.
    """
    mapas = list(mapas)
    return ciclo(lambda _: mapas.pop(0), limites_aceitos, maximo=len(mapas))
