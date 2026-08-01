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


def le_requisitos(fonte):
    """Devolve {id: {titulo, ca, ancora, epico}} a partir de um markdown de requisitos.

    `fonte` é o caminho de um .md OU o texto direto. Formato ausente devolve {} —
    projeto sem documento de requisitos não é erro, é o caso comum (ver a regra
    'o requisito é obrigatório; o lugar dele é opcional' na spec §5.1).
    """
    try:
        txt = open(fonte, encoding="utf-8").read()
    except (OSError, ValueError):
        txt = fonte if isinstance(fonte, str) and "\n" in fonte else ""
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
        ep = None
        for pos, nome in epicos:
            if pos < m.start():
                ep = nome
        out[rid] = {"titulo": titulo,
                    "ca": " ".join(ca.group(1).split()) if ca else None,
                    "ancora": art.group(1) if art else None,
                    "epico": ep}
    return out


def mapa(plan, reqs):
    """Os quatro estados do fio. Nenhum é silencioso — todos viram lista."""
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
    return {"cobertas": cobertas, "sem_requisito": sem_req, "orfaos": orfaos,
            "inexistentes": inexistentes, "por_req": por_req,
            "total": len(cobertas) + len(sem_req) + len(inexistentes)}


def resumo(m):
    """A linha única. Um só programa calcula; todos os lugares leem dela."""
    def _pl(n, s, p=None):
        return "%d %s" % (n, s if n == 1 else (p or s + "s"))

    partes = [_pl(m["total"], "tarefa"),
              "%d com requisito" % len(m["cobertas"]),
              "%d sem" % len(m["sem_requisito"]),
              "%s sem tarefa" % _pl(len(m["orfaos"]), "requisito")]
    if m["inexistentes"]:
        partes.append("⛔ %d citando requisito inexistente" % len(m["inexistentes"]))
    return " · ".join(partes)
