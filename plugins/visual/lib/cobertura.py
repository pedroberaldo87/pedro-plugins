#!/usr/bin/env python3
"""O fio entre o requisito (o que o sistema deve fazer) e a tarefa (o que se constrói).

Nasce de uma medição: num projeto real, 5 de 157 tarefas apontavam para algum dos 77
requisitos escritos. As outras 152 não rastreavam para nada, e nada nunca disse isso.
Silêncio é o estado padrão de hoje; este módulo o torna impossível.
"""

import re

# O formato que o dono já escreve à mão:
#   - **S-4.3 Título** · F1 · Art. 6 — corpo. CA: o critério.
REQ_RE = re.compile(r"^- \*\*(S-[\d.]+)\s+([^*]+)\*\*(.*)$", re.M)
EPICO_RE = re.compile(r"^## (E\d+[^\n]*)$", re.M)
CA_RE = re.compile(r"\bCA:\s*(.+?)(?=\n\s*[-#]|\Z)", re.S)
ART_RE = re.compile(r"\b(Art\.\s*\d+[-A-Z]*)")
# o número dentro da citação — "Art. 6" e "Art. 6-A" viram "6" e "6-A"
ART_NUM_RE = re.compile(r"(\d+[-A-Z]*)")
# cada artigo da lei do projeto é um `## Artigo N · nome` no constituicao.md
ARTIGO_H_RE = re.compile(r"^##\s*Artigo\s+(\d+[-A-Z]*)", re.M)
# a jornada de origem, citada no requisito pelo nome que journeys.md dá a ela
JORNADA_RE = re.compile(r"\bJornada:\s*([^·—\n]+)")
# a saída explícita: funcionalidade que o dono assume como escolha dele, sem artigo
# de lei por trás. Escrita como `Decisão: <motivo>`, ela passa marcada, não calada.
DECISAO_RE = re.compile(r"\bDecisão:\s*([^·\n]+)")
# cada jornada do journeys.md é um `## nome` — é o molde que a entrevista escreve
JORNADA_H_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
# a peça da arquitetura pretendida que o requisito diz habitar, citada pelo nome que
# o architecture-intent.md dá a ela
PECA_RE = re.compile(r"\bPeça:\s*([^·—\n]+)")
# as seções do architecture-intent.md, pra saber o que é a lista de peças e o que é
# outra seção do documento (fronteiras, estado, o que ficou de fora)
SECAO_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
# a peça em si: no molde do documento ela é um item de lista `- **{peça}** — {…}`
PECA_ITEM_RE = re.compile(r"^-\s+\*\*(.+?)\*\*", re.M)


def _texto(fonte):
    """`fonte` é o caminho de um .md OU o texto direto. Ausente vira ""."""
    try:
        return open(fonte, encoding="utf-8").read()
    except (OSError, ValueError):
        return fonte if isinstance(fonte, str) and "\n" in fonte else ""


def le_requisitos(fonte):
    """Devolve {id: {titulo, ca, ancora, jornada, epico, repetido}} a partir de um markdown de requisitos.

    `fonte` é o caminho de um .md OU o texto direto. Formato ausente devolve {} —
    projeto sem documento de requisitos não é erro, é o caso comum (ver a regra
    'o requisito é obrigatório; o lugar dele é opcional' na spec §5.1).

    Dois épicos que escrevem o mesmo número são um acidente comum de documento
    grande, e até aqui o segundo apagava o primeiro sem que nada dissesse. Agora
    fica valendo o PRIMEIRO — quem já foi lido e ligado a tarefa — e o número
    ganha `repetido: True`, que `mapa` transforma em acusação.
    """
    txt = _texto(fonte)
    out = {}
    # mapa posição→épico, pra saber sob qual cabeçalho cada requisito caiu
    epicos = [(m.start(), m.group(1)) for m in EPICO_RE.finditer(txt)]
    for m in REQ_RE.finditer(txt):
        rid, titulo, resto = m.group(1), m.group(2).strip(), m.group(3)
        # o corpo vai até o próximo item de lista ou cabeçalho
        fim = txt.find("\n- **", m.end())
        corpo = txt[m.end():fim if fim > 0 else len(txt)]
        ca = CA_RE.search(resto + corpo)
        art = ART_RE.search(resto[:200])
        jor = JORNADA_RE.search(resto)
        pec = PECA_RE.search(resto + corpo)
        dec = DECISAO_RE.search(resto + corpo)
        ep = None
        for pos, nome in epicos:
            if pos < m.start():
                ep = nome
        if rid in out:
            out[rid]["repetido"] = True
            continue
        out[rid] = {"titulo": titulo,
                    "ca": " ".join(ca.group(1).split()) if ca else None,
                    "ancora": art.group(1) if art else None,
                    "jornada": jor.group(1).strip() if jor else None,
                    "peca": pec.group(1).strip() if pec else None,
                    "epico": ep,
                    "decisao": " ".join(dec.group(1).split()) if dec else None,
                    "repetido": False}
    return out


def le_jornadas(fonte):
    """Os nomes das jornadas de um journeys.md, na ordem em que aparecem.

    `fonte` é o caminho de um .md OU o texto direto. Documento ausente devolve [],
    e [] não acusa ninguém: projeto sem jornadas escritas não é projeto com
    funcionalidade órfã, é projeto que ainda não tem o que cruzar.
    """
    return [m.group(1).strip() for m in JORNADA_H_RE.finditer(_texto(fonte))]


def le_artigos(fonte):
    """Os números dos artigos da lei do projeto, na ordem em que aparecem.

    `fonte` é o caminho do constituicao.md OU o texto direto. Documento ausente
    devolve [], e [] não acusa ninguém: projeto sem lei escrita não é projeto que
    cita artigo errado, é projeto que ainda não tem com o que conferir — a mesma
    regra que `le_jornadas` segue para o journeys.md.
    """
    return [m.group(1) for m in ARTIGO_H_RE.finditer(_texto(fonte))]


def le_pecas(fonte):
    """Os nomes das peças do architecture-intent.md, na ordem em que aparecem.

    Peça é um item `- **{nome}** — {…}` sob a seção `## As peças`, que é o molde
    que a etapa 2 do `/start-doc` escreve. O documento da arquitetura pretendida
    também descreve fronteiras, onde o estado mora e o que ficou de fora, todos
    escritos com o MESMO item de lista em negrito — por isso o corte é a seção, não
    a forma do item: fora de `## As peças` nada vira peça. Documento ausente, ou sem
    essa seção, devolve []: projeto que ainda não desenhou a arquitetura não é
    projeto que a contradiz, é projeto sem com o que cruzar — a mesma regra que
    `le_jornadas` e `le_artigos` seguem.
    """
    txt = _texto(fonte)
    secoes = [(m.start(), m.end(), m.group(1)) for m in SECAO_RE.finditer(txt)]
    out = []
    for i, (_, fim, nome) in enumerate(secoes):
        if "peça" not in nome.casefold():
            continue
        prox = secoes[i + 1][0] if i + 1 < len(secoes) else len(txt)
        for it in PECA_ITEM_RE.finditer(txt[fim:prox]):
            out.append(it.group(1).strip())
    return out


def _num_artigo(ancora):
    """"Art. 6" vira "6". Citação sem número devolve None."""
    m = ART_NUM_RE.search(ancora or "")
    return m.group(1) if m else None


def _chave(nome):
    """Nome de jornada comparado sem depender de espaço a mais nem de caixa."""
    return " ".join((nome or "").split()).casefold()


def mapa(plan, reqs, jornadas=None, artigos=None, pecas=None):
    """Os quatro estados do fio. Nenhum é silencioso — todos viram lista.

    `jornadas` é a lista de nomes que `le_jornadas` devolveu. Com ela o cruzamento
    corre nas DUAS direções: funcionalidade que não cita caminho de pessoa nenhum —
    ou que cita um que o documento não tem — cai em `sem_jornada`; jornada que
    nenhuma funcionalidade atende cai em `jornadas_sem_funcionalidade`; épico cujas
    funcionalidades todas ficaram sem caminho de pessoa cai em `epicos_sem_jornada`.
    Sem ela (None ou vazia) esses baldes ficam vazios: não há com o que cruzar, e acusar
    todo mundo seria ruído, não cobrança.

    `sem_ca` não depende de jornada nenhuma: requisito escrito sem critério de aceite
    é acusado sempre, porque sem critério não há como dizer se ele foi atendido.

    `artigos` é a lista que `le_artigos` devolveu. Com ela a citação de artigo deixa
    de ser só extraída e passa a ser conferida: requisito que aponta para artigo que
    a lei não tem cai em `artigos_inexistentes`. Sem ela (None ou vazia) o balde fica
    vazio — sem lei escrita não há com o que cruzar, e acusar seria ruído.

    `pecas` é a lista que `le_pecas` devolveu. Com ela o plano deixa de nascer contra a
    memória de quem o monta: requisito que não diz em que peça da arquitetura ele vive
    cai em `sem_peca`, e requisito que cita uma peça que o desenho não tem cai em
    `pecas_inexistentes` — a contradição entre o plano e a arquitetura pretendida, que
    até aqui não aparecia em lugar nenhum. Sem ela os dois baldes ficam vazios, pela
    mesma regra dos outros cruzamentos.
    """
    cobertas, sem_req, inexistentes, por_req = [], [], [], {}
    for ph in plan.get("phases", []):
        for it in ph.get("items", []):
            rid = str(it.get("requisito", "")).strip()
            if not rid:
                sem_req.append(it["id"])
                continue
            if rid not in reqs:
                inexistentes.append((it["id"], rid))
                continue
            cobertas.append(it["id"])
            por_req.setdefault(rid, []).append(it["id"])
    orfaos = sorted(r for r in reqs if r not in por_req)
    nomes = {_chave(j) for j in (jornadas or [])}
    sem_jornada = sorted(r for r, d in reqs.items()
                         if nomes and _chave(d.get("jornada")) not in nomes)
    citadas = {_chave(d.get("jornada")) for d in reqs.values()}
    jornadas_sem_func = [j for j in (jornadas or [])
                         if reqs and _chave(j) not in citadas]
    # épico em que NENHUMA funcionalidade veio de um caminho de pessoa não é
    # entrega: é agrupamento técnico. A ordem é a de aparição no documento.
    ordem, ligado = [], {}
    for d in reqs.values():
        ep = d.get("epico")
        if not ep:
            continue
        if ep not in ligado:
            ordem.append(ep)
            ligado[ep] = False
        if _chave(d.get("jornada")) in nomes:
            ligado[ep] = True
    epicos_sem_jornada = [e for e in ordem if not ligado[e]] if nomes else []
    # requisito sem critério de aceite não é requisito: é intenção. Hoje ele fecha
    # sem que nem o lembrete de conferir apareça — daqui em diante ele é contado.
    sem_ca = sorted(r for r, d in reqs.items() if not d.get("ca"))
    # número escrito duas vezes: só uma das descrições sobreviveu à leitura, e a
    # tarefa que aponta para ele está atendendo a metade que ficou. Isso é contado.
    repetidos = sorted(r for r, d in reqs.items() if d.get("repetido"))
    # citar a lei sem que ninguém confira é o mesmo silêncio que este módulo combate:
    # com a lei em mãos, o artigo que ela não tem vira acusação.
    numeros = set(artigos or [])
    artigos_inexistentes = sorted(
        (r, d["ancora"]) for r, d in reqs.items()
        if numeros and d.get("ancora") and _num_artigo(d["ancora"]) not in numeros)
    # funcionalidade que não nasce de artigo nenhum é funcionalidade sem motivo escrito:
    # ninguém sabe dizer por que ela existe. Ela passa a ser contada — salvo quando o
    # dono a declara como escolha dele (`Decisão: <motivo>`), e aí ela passa MARCADA,
    # em `decididas`, em vez de calada. Sem a lei em mãos os dois baldes ficam vazios,
    # pela mesma regra dos outros cruzamentos: sem com o que cruzar, não há acusação.
    sem_artigo = sorted(r for r, d in reqs.items()
                        if numeros and not d.get("ancora") and not d.get("decisao"))
    decididas = sorted(r for r, d in reqs.items()
                       if numeros and not d.get("ancora") and d.get("decisao"))
    # o desenho da arquitetura pretendida entra no cruzamento pelas duas pontas: quem
    # não diz em que peça vive, e quem diz uma que o desenho não tem.
    nomes_pecas = {_chave(p) for p in (pecas or [])}
    sem_peca = sorted(r for r, d in reqs.items()
                      if nomes_pecas and not d.get("peca"))
    pecas_inexistentes = sorted(
        (r, d["peca"]) for r, d in reqs.items()
        if nomes_pecas and d.get("peca") and _chave(d["peca"]) not in nomes_pecas)
    return {"cobertas": cobertas, "sem_requisito": sem_req, "orfaos": orfaos,
            "inexistentes": inexistentes, "por_req": por_req,
            "sem_jornada": sem_jornada, "sem_ca": sem_ca,
            "repetidos": repetidos,
            "sem_artigo": sem_artigo, "decididas": decididas,
            "artigos_inexistentes": artigos_inexistentes,
            "sem_peca": sem_peca, "pecas_inexistentes": pecas_inexistentes,
            "jornadas_sem_funcionalidade": jornadas_sem_func,
            "epicos_sem_jornada": epicos_sem_jornada,
            "total": len(cobertas) + len(sem_req) + len(inexistentes)}


def resumo(m):
    """A linha única. Um só programa calcula; todos os lugares leem dela."""
    def _pl(n, s, p=None):
        return "%d %s" % (n, s if n == 1 else (p or s + "s"))

    partes = [_pl(m["total"], "tarefa"),
              "%d com requisito" % len(m["cobertas"]),
              "%d sem" % len(m["sem_requisito"]),
              "%s sem tarefa" % _pl(len(m["orfaos"]), "requisito")]
    if m.get("sem_jornada"):
        partes.append("🔴 %s sem jornada" % _pl(len(m["sem_jornada"]), "funcionalidade"))
    if m.get("epicos_sem_jornada"):
        partes.append("🔴 %s sem jornada" % _pl(len(m["epicos_sem_jornada"]), "épico"))
    if m.get("sem_artigo"):
        partes.append("🔴 %s sem artigo da lei"
                      % _pl(len(m["sem_artigo"]), "funcionalidade"))
    if m.get("decididas"):
        partes.append("⚪ %s por decisão declarada"
                      % _pl(len(m["decididas"]), "funcionalidade"))
    if m.get("sem_peca"):
        partes.append("🔴 %s sem peça da arquitetura"
                      % _pl(len(m["sem_peca"]), "funcionalidade"))
    if m.get("sem_ca"):
        partes.append("🔴 %s sem critério" % _pl(len(m["sem_ca"]), "requisito"))
    if m.get("jornadas_sem_funcionalidade"):
        partes.append("🔵 %s sem funcionalidade"
                      % _pl(len(m["jornadas_sem_funcionalidade"]), "jornada"))
    if m.get("repetidos"):
        partes.append("⛔ %s com número repetido" % _pl(len(m["repetidos"]), "requisito"))
    if m.get("artigos_inexistentes"):
        partes.append("⛔ %s citando artigo que a lei não tem"
                      % _pl(len(m["artigos_inexistentes"]), "requisito"))
    if m.get("pecas_inexistentes"):
        partes.append("⛔ %s citando peça que a arquitetura não tem"
                      % _pl(len(m["pecas_inexistentes"]), "requisito"))
    if m["inexistentes"]:
        partes.append("⛔ %d citando requisito inexistente" % len(m["inexistentes"]))
    return " · ".join(partes)
