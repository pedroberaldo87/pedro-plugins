#!/usr/bin/env python3
"""
test_graph_map.py — testes do destilador do knowledge graph (graphify) pro project-doc v3.2.

Prova: fan-in semântico exclui relações estruturais (contains/defines/method), god nodes
respeitam o piso e vêm ordenados, arquivos ranqueiam por fan-in agregado, comunidades nomeadas
dedupam por nome e o ruído repetido (>=4 comunidades) cai em generic, hyperedges filtram por
confiança, e a ausência de grafo degrada gracioso (available=false, sem erro).

Self-contained (grafo mock em memória + dir temporário). Faz também um smoke no grafo real se
houver `graphify-out/graph.json` no repo.

Roda com:  python3 plugins/project-doc/lib/test_graph_map.py
"""
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import graph_map  # noqa: E402

PASS = 0


def check(label, cond):
    global PASS
    assert cond, "FALHOU: " + label
    PASS += 1
    print("  ok ·", label)


def _mock_graph():
    """Grafo node-link mínimo, no formato real (nodes[], links[], hyperedges[])."""
    nodes = [
        {"id": "fa", "label": "a.py", "source_file": "a.py", "source_location": "L1", "community": 0},
        {"id": "f1", "label": "func1()", "source_file": "a.py", "source_location": "L5", "community": 0},
        {"id": "f2", "label": "func2()", "source_file": "a.py", "source_location": "L9", "community": 0},
        {"id": "fb", "label": "b.py", "source_file": "b.py", "source_location": "L1", "community": 1},
        {"id": "f3", "label": "func3()", "source_file": "b.py", "source_location": "L5", "community": 1},
        # 4 comunidades com o MESMO nome → ruído genérico
        {"id": "g2", "label": "meta", "source_file": "p2/plugin.json", "source_location": "L1", "community": 2},
        {"id": "g3", "label": "meta", "source_file": "p3/plugin.json", "source_location": "L1", "community": 3},
        {"id": "g4", "label": "meta", "source_file": "p4/plugin.json", "source_location": "L1", "community": 4},
        {"id": "g5", "label": "meta", "source_file": "p5/plugin.json", "source_location": "L1", "community": 5},
    ]
    links = [
        {"source": "fa", "target": "f1", "relation": "contains", "confidence_score": 1.0},
        {"source": "fa", "target": "f2", "relation": "contains", "confidence_score": 1.0},
        {"source": "fb", "target": "f3", "relation": "contains", "confidence_score": 1.0},
        # f1 é chamado por 3 lugares → fan-in semântico = 3 (god node), total = 4 (com o contains)
        {"source": "f3", "target": "f1", "relation": "calls", "confidence_score": 1.0},
        {"source": "f2", "target": "f1", "relation": "calls", "confidence_score": 1.0},
        {"source": "fb", "target": "f1", "relation": "references", "confidence_score": 0.9},
        # link malformado sem target → deve ser ignorado, não estourar nem contaminar o fan-in
        {"source": "f3", "relation": "calls", "confidence_score": 1.0},
    ]
    hyperedges = [
        {"id": "h1", "label": "High flow", "confidence_score": 0.95, "nodes": ["f1", "f2"]},
        {"id": "h2", "label": "Low flow", "confidence_score": 0.5, "nodes": ["f3"]},
    ]
    return {"nodes": nodes, "links": links, "hyperedges": hyperedges}


def _mock_labels():
    return {"0": "Module A", "1": "Community 99", "2": "Repeated", "3": "Repeated", "4": "Repeated", "5": "Repeated"}


def test_fan_in_excludes_structural():
    print("\n== fan-in semântico exclui estrutura ==")
    m = graph_map.build_map(_mock_graph(), _mock_labels(), god_min=3)
    f1 = next(g for g in m["god_nodes"] if g["id"] == "f1")
    check("f1 fan-in semântico = 3 (contains não conta; link sem target ignorado)", f1["fan_in"] == 3)
    check("f1 fan-in total = 4 (contains conta)", f1["fan_in_total"] == 4)
    check("f1 breakdown por relação preservado", f1["relations_in"].get("calls") == 2 and f1["relations_in"].get("references") == 1)
    check("link sem target não criou nó-fantasma", all(g["id"] is not None for g in m["god_nodes"]))


def test_god_nodes_threshold_and_order():
    print("\n== god nodes: piso + ordem ==")
    m = graph_map.build_map(_mock_graph(), _mock_labels(), god_min=3)
    ids = [g["id"] for g in m["god_nodes"]]
    check("só f1 é god node (fan-in>=3)", ids == ["f1"])
    m2 = graph_map.build_map(_mock_graph(), _mock_labels(), god_min=10)
    check("god_min alto → nenhum god node", m2["god_nodes"] == [])


def test_files_ranked():
    print("\n== arquivos ranqueados por fan-in agregado ==")
    m = graph_map.build_map(_mock_graph(), _mock_labels(), god_min=3)
    files = [f["source_file"] for f in m["files"]]
    check("a.py vem antes de b.py (fan-in agregado maior)", files.index("a.py") < files.index("b.py"))
    a = next(f for f in m["files"] if f["source_file"] == "a.py")
    check("a.py agrega fan-in do god node (3)", a["fan_in"] == 3)
    check("a.py lista func1() como god node do arquivo", "func1()" in a["god_nodes"])


def test_communities_dedup_and_generic():
    print("\n== comunidades: dedup + generic + ignora Community NNN ==")
    m = graph_map.build_map(_mock_graph(), _mock_labels(), god_min=3)
    names = [c["label"] for c in m["communities"]]
    check("Module A entra como comunidade útil", "Module A" in names)
    check("'Community 99' (placeholder) ignorado", "Community 99" not in names)
    check("'Repeated' (4 comunidades) NÃO entra como útil", "Repeated" not in names)
    generic = [c["label"] for c in m["generic_communities"]]
    check("'Repeated' classificado como generic com count=4", "Repeated" in generic and m["generic_communities"][0]["count"] == 4)


def test_hyperedges_threshold():
    print("\n== hyperedges: filtro por confiança + resolve labels ==")
    m = graph_map.build_map(_mock_graph(), _mock_labels(), hyper_min=0.85)
    ids = [h["id"] for h in m["hyperedges"]]
    check("só h1 passa (>=0.85)", ids == ["h1"])
    check("nodes resolvidos pra labels", set(m["hyperedges"][0]["nodes"]) == {"func1()", "func2()"})
    check("source_files resolvidos dos nodes (dedup+sort)", m["hyperedges"][0]["source_files"] == ["a.py"])


def test_graceful_degradation():
    print("\n== degradação graciosa (sem grafo) ==")
    tmp = tempfile.mkdtemp(prefix="gmtest_")
    try:
        r = graph_map.run(tmp)
        check("sem graphify-out → available=False", r["available"] is False)
        check("sem grafo informa o path esperado", r["expected_path"].endswith("graphify-out/graph.json"))
        # grafo ilegível também degrada, não estoura
        out = os.path.join(tmp, "graphify-out")
        os.makedirs(out)
        with open(os.path.join(out, "graph.json"), "w") as fh:
            fh.write("{ not valid json")
        r2 = graph_map.run(tmp)
        check("graph.json corrompido → available=False (não levanta)", r2["available"] is False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_real_graph_smoke():
    print("\n== smoke no grafo real (se existir) ==")
    repo = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
    graph_path, _ = graph_map.graph_paths(repo)
    if not os.path.isfile(graph_path):
        print("  (pulado — sem grafo real no repo)")
        return
    r = graph_map.run(repo)
    check("grafo real disponível", r["available"] is True)
    check("stats com nós e links", r["stats"]["nodes"] > 0 and r["stats"]["links"] > 0)
    check("arquivos ranqueados não-vazios", len(r["files"]) > 0)
    # a saída é JSON-serializável (a casca consome via stdout)
    json.dumps(r)
    check("mapa é JSON-serializável", True)


if __name__ == "__main__":
    test_fan_in_excludes_structural()
    test_god_nodes_threshold_and_order()
    test_files_ranked()
    test_communities_dedup_and_generic()
    test_hyperedges_threshold()
    test_graceful_degradation()
    test_real_graph_smoke()
    print("\nTODOS OS %d CHECKS PASSARAM" % PASS)
