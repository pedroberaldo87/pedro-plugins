#!/usr/bin/env python3
"""
graph_map.py — destila o knowledge graph (graphify) num MAPA enxuto pra casca do project-doc.

O grafo (`graphify-out/graph.json`) tem milhares de nós/arestas (2.4MB no marketplace) — grande
demais pra casca engolir inline. Este helper lê o grafo + os labels de comunidade e devolve um
JSON compacto que dirige a leitura profunda do v3.2:

  - files       → arquivos-fonte ranqueados por fan-in (cada agente-concern lê os de maior fan-in 1º)
  - god_nodes   → funções/símbolos centrais (fan-in semântico >= god_min) a destacar na doc
  - communities → módulos nomeados (de .graphify_labels.json), dedupados, ruído estrutural à parte
  - hyperedges  → workflows multi-nó de alta confiança (>= hyper_min) → architecture.md / auditoria

Fan-in é computado de `links[].target` (formato node-link do NetworkX). A relação `contains`
(arquivo-contém-símbolo, ~85% das arestas) é ESTRUTURAL e vira ruído no ranking de importância,
então o fan-in semântico a exclui; o fan-in total é exposto à parte.

Degrada gracioso: sem grafo, devolve {"available": false} (a casca cai no comportamento v3.1).

Roda com:  python3 plugins/project-doc/lib/graph_map.py --project-root <root>
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

# Relações que são "estrutura", não "importância" — excluídas do fan-in semântico.
STRUCTURAL_RELATIONS = {"contains", "defines", "method"}
# Nome de comunidade compartilhado por >= este nº de comunidades = metadado repetido (ruído), não módulo.
GENERIC_COMMUNITY_MIN = 4


def graph_paths(project_root):
    """Caminhos canônicos do grafo dentro do projeto."""
    out = os.path.join(project_root, "graphify-out")
    return (
        os.path.join(out, "graph.json"),
        os.path.join(out, ".graphify_labels.json"),
    )


def load_graph(project_root):
    """Lê graph.json + labels. Devolve (graph, labels) ou (None, None) se ausente/ilegível."""
    graph_path, labels_path = graph_paths(project_root)
    if not os.path.isfile(graph_path):
        return None, None
    try:
        with open(graph_path, encoding="utf-8") as fh:
            graph = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None, None
    labels = {}
    if os.path.isfile(labels_path):
        try:
            with open(labels_path, encoding="utf-8") as fh:
                labels = json.load(fh)
        except (json.JSONDecodeError, OSError):
            labels = {}
    return graph, labels


def _is_named(label):
    """Um label de comunidade é 'nomeado' se não for o placeholder 'Community NNN'."""
    return bool(label) and not label.strip().lower().startswith("community ")


def build_map(graph, labels, god_min=3, hyper_min=0.85, top_files=40, top_gods=60):
    """Destila o grafo carregado num mapa compacto. Pura função sobre dados — testável."""
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])
    hyper = graph.get("hyperedges", [])

    id2node = {n.get("id"): n for n in nodes if n.get("id") is not None}

    # --- fan-in por nó (total e semântico) + breakdown por relação ---
    fan_total = Counter()
    fan_sem = Counter()
    rel_in = defaultdict(Counter)
    for link in links:
        tgt = link.get("target")
        if tgt is None:
            continue
        rel = link.get("relation", "")
        fan_total[tgt] += 1
        rel_in[tgt][rel] += 1
        if rel not in STRUCTURAL_RELATIONS:
            fan_sem[tgt] += 1

    # --- god nodes: fan-in semântico alto ---
    god_nodes = []
    for nid, score in fan_sem.most_common():
        if score < god_min:
            break
        n = id2node.get(nid, {})
        god_nodes.append({
            "id": nid,
            "label": n.get("label", nid),
            "source_file": n.get("source_file"),
            "source_location": n.get("source_location"),
            "fan_in": score,
            "fan_in_total": fan_total[nid],
            "relations_in": dict(rel_in[nid]),
        })
    god_nodes = god_nodes[:top_gods]  # capa ANTES de derivar god_ids → files[].god_nodes bate com god_nodes[] exibido
    god_ids = {g["id"] for g in god_nodes}

    # --- arquivos ranqueados por fan-in semântico agregado ---
    file_fan = Counter()
    file_nodes = defaultdict(int)
    file_gods = defaultdict(list)
    for n in nodes:
        sf = n.get("source_file")
        if not sf:
            continue
        file_nodes[sf] += 1
        file_fan[sf] += fan_sem.get(n.get("id"), 0)
        if n.get("id") in god_ids:
            file_gods[sf].append(n.get("label", n.get("id")))
    files = [
        {
            "source_file": sf,
            "fan_in": fan,
            "node_count": file_nodes[sf],
            "god_nodes": file_gods.get(sf, []),
        }
        for sf, fan in file_fan.most_common()
    ]

    # --- comunidades nomeadas, dedupadas por nome ---
    comm_members = defaultdict(list)
    for n in nodes:
        c = n.get("community")
        if c is not None:
            comm_members[str(c)].append(n)
    by_name = defaultdict(lambda: {"community_ids": [], "size": 0, "files": Counter()})
    for cid, members in comm_members.items():
        name = labels.get(cid) or labels.get(str(cid))
        if not _is_named(name):
            continue
        agg = by_name[name]
        agg["community_ids"].append(cid)
        agg["size"] += len(members)
        for m in members:
            if m.get("source_file"):
                agg["files"][m["source_file"]] += 1
    communities, generic_communities = [], []
    for name, agg in sorted(by_name.items(), key=lambda kv: kv[1]["size"], reverse=True):
        entry = {
            "label": name,
            "size": agg["size"],
            "community_ids": agg["community_ids"],
            "files": [f for f, _ in agg["files"].most_common(5)],
        }
        if len(agg["community_ids"]) >= GENERIC_COMMUNITY_MIN:
            generic_communities.append({"label": name, "count": len(agg["community_ids"])})
        else:
            communities.append(entry)

    # --- hyperedges de alta confiança ---
    hyperedges = []
    for h in sorted(hyper, key=lambda x: x.get("confidence_score", 0), reverse=True):
        score = h.get("confidence_score", 0)
        if score < hyper_min:
            continue
        node_labels = [id2node.get(nid, {}).get("label", nid) for nid in h.get("nodes", [])]
        src_files = sorted({
            id2node.get(nid, {}).get("source_file")
            for nid in h.get("nodes", [])
            if id2node.get(nid, {}).get("source_file")
        })
        hyperedges.append({
            "id": h.get("id"),
            "label": h.get("label"),
            "confidence_score": score,
            "nodes": node_labels,
            "source_files": src_files,
        })

    return {
        "available": True,
        "stats": {
            "nodes": len(nodes),
            "links": len(links),
            "hyperedges_total": len(hyper),
            "communities_named": len(communities),
            "god_nodes": len(god_nodes),
        },
        "params": {"god_min": god_min, "hyper_min": hyper_min},
        "files": files[:top_files],
        "god_nodes": god_nodes,
        "communities": communities,
        "generic_communities": generic_communities,
        "hyperedges": hyperedges,
    }


def run(project_root, god_min=3, hyper_min=0.85):
    """Carrega + destila. Devolve {available: false} se não houver grafo."""
    graph, labels = load_graph(project_root)
    if graph is None:
        graph_path, _ = graph_paths(project_root)
        return {"available": False, "reason": "graph.json ausente ou ilegível", "expected_path": graph_path}
    return build_map(graph, labels, god_min=god_min, hyper_min=hyper_min)


def main():
    ap = argparse.ArgumentParser(description="project-doc graph map — destila o grafo graphify pra casca")
    ap.add_argument("--project-root", required=True, help="raiz do projeto (contém graphify-out/)")
    ap.add_argument("--god-min", type=int, default=3, help="fan-in semântico mínimo pra god node")
    ap.add_argument("--hyper-min", type=float, default=0.85, help="confidence_score mínimo pra hyperedge")
    args = ap.parse_args()
    result = run(args.project_root, god_min=args.god_min, hyper_min=args.hyper_min)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("available") else 0  # ausência de grafo NÃO é erro (degrada gracioso)


if __name__ == "__main__":
    sys.exit(main())
