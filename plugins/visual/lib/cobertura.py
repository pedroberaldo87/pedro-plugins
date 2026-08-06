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
# a jornada de origem, citada no requisito pelo nome que journeys.md dá a ela
JORNADA_RE = re.compile(r"\bJornada:\s*([^·—\n]+)")
# cada jornada do journeys.md é um `## nome` — é o molde que a entrevista escreve
JORNADA_H_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)


def _texto(fonte):
    """`fonte` é o caminho de um .md OU o texto direto. Ausente vira ""."""
    try:
        return open(fonte, encoding="utf-8").read()
    except (OSError, ValueError):
        return fonte if isinstance(fonte, str) and "\n" in fonte else ""


def le_requisitos(fonte):
    """Devolve {id: {titulo, ca, ancora, jornada, epico}} a partir de um markdown de requisitos.

    `fonte` é o caminho de um .md OU o texto direto. Formato ausente devolve {} —
    projeto sem documento de requisitos não é erro, é o caso comum (ver a regra
    'o requisito é obrigatório; o lugar dele é opcional' na spec §5.1).
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
        ep = None
        for pos, nome in epicos:
            if pos < m.start():
                ep = nome
        out[rid] = {"titulo": titulo,
                    "ca": " ".join(ca.group(1).split()) if ca else None,
                    "ancora": art.group(1) if art else None,
                    "jornada": jor.group(1).strip() if jor else None,
                    "epico": ep}
    return out


def le_jornadas(fonte):
    """Os nomes das jornadas de um journeys.md, na ordem em que aparecem.

    `fonte` é o caminho de um .md OU o texto direto. Documento ausente devolve [],
    e [] não acusa ninguém: projeto sem jornadas escritas não é projeto com
    funcionalidade órfã, é projeto que ainda não tem o que cruzar.
    """
    return [m.group(1).strip() for m in JORNADA_H_RE.finditer(_texto(fonte))]


def _chave(nome):
    """Nome de jornada comparado sem depender de espaço a mais nem de caixa."""
    return " ".join((nome or "").split()).casefold()


def mapa(plan, reqs, jornadas=None):
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
    return {"cobertas": cobertas, "sem_requisito": sem_req, "orfaos": orfaos,
            "inexistentes": inexistentes, "por_req": por_req,
            "sem_jornada": sem_jornada, "sem_ca": sem_ca,
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
    if m.get("sem_ca"):
        partes.append("🔴 %s sem critério" % _pl(len(m["sem_ca"]), "requisito"))
    if m.get("jornadas_sem_funcionalidade"):
        partes.append("🔵 %s sem funcionalidade"
                      % _pl(len(m["jornadas_sem_funcionalidade"]), "jornada"))
    if m["inexistentes"]:
        partes.append("⛔ %d citando requisito inexistente" % len(m["inexistentes"]))
    return " · ".join(partes)
