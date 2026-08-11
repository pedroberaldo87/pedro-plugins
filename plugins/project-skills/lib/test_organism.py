#!/usr/bin/env python3
"""Regression test do organism.py — o query engine do gate invertido.

Roda com: python3 -m pytest lib/test_organism.py  (ou python3 lib/test_organism.py)
Sem framework obrigatório: um __main__ que roda asserts e sai !=0 se falhar.
"""
import os
import tempfile

import organism

FIXTURE = """
name: TEST-ORG
modulos: [alpha, beta, gamma]
defaults:
  exclude:
    - "**/.claude/worktrees/**"
    - "legacy/**"
costuras:
  - id: seam-block
    severidade: block
    grep_verificavel: true
    aresta_msg: alpha muda, beta e gamma quebram
    pontas:
      - modulo: alpha
        globs: ["alpha/api.py", "alpha/deep/**"]
        simbolos: ["SHARED_KEY", "def mint"]
      - modulo: beta
        globs: ["beta/client.py"]
        simbolos: ["SHARED_KEY"]
      - modulo: gamma
        globs: ["gamma/x.py"]
        simbolos: ["SHARED_KEY"]
  - id: seam-warn
    severidade: warn
    grep_verificavel: true
    aresta_msg: contrato solto
    pontas:
      - modulo: alpha
        globs: ["alpha/config.yaml"]
        simbolos: ["endpoint"]
      - modulo: beta
        globs: ["beta/reader.py"]
        simbolos: ["endpoint"]
"""


# Amostra com TODOS os recursos que o organism.yaml real usa: folded scalar (>),
# inline lists [a, b], listas de mappings aninhadas, bool, comentários, defaults.
_REAL_ORGANISM_SAMPLE = """
# comentário de topo
name: MEU-MONOREPO
root_doc: .claude/CLAUDE.md
modulos: [tools, mcp, brain, servico]
golden_rule: >
  Isto é UM organismo, não N ilhas.
  Toda ação considera os demais.
defaults:
  exclude:
    - "**/.claude/worktrees/**"
    - "_repos-antigos/**"
costuras:
  - id: identidade-rbac
    severidade: block
    grep_verificavel: true
    aresta_msg: >
      Identidade nasce no tools. mcp e servico herdam.
    pontas:
      - modulo: tools
        globs: ["tools/apps/hub/**", "tools/migrations/*access*"]
        simbolos: ["usuarios_acesso", "/api/exemplo/apps"]
      - modulo: mcp
        globs: ["mcp/access.py"]
        simbolos: ["usuarios_acesso"]
  - id: rede-docker
    severidade: warn
    grep_verificavel: false
    aresta_msg: a rede é do tools
    pontas:
      - modulo: tools
        globs: ["tools/docker-compose.yml"]
        simbolos: ["name: meu-monorepo-tools"]
      - modulo: mcp
        globs: ["mcp/config.py"]
        simbolos: ["app:3030"]
"""


def _write_fixture(root):
    os.makedirs(os.path.join(root, ".claude"))
    with open(os.path.join(root, ".claude", "organism.yaml"), "w", encoding="utf-8") as fh:
        fh.write(FIXTURE)


def run():
    with tempfile.TemporaryDirectory() as root:
        _write_fixture(root)
        _, data = organism.find_organism(root)
        assert data and data.get("name") == "TEST-ORG", "find_organism falhou"

        def match(rel):
            return organism.costuras_for_path(root, data, os.path.join(root, rel))

        # 1) ponta alpha da costura block → blast-radius beta+gamma
        h = match("alpha/api.py")
        assert len(h) == 1 and h[0]["id"] == "seam-block", h
        assert h[0]["severidade"] == "block"
        assert h[0]["ponta_tocada"] == "alpha"
        assert sorted(h[0]["blast_radius"]) == ["beta", "gamma"], h[0]["blast_radius"]

        # 2) glob ** recursivo casa em profundidade
        assert match("alpha/deep/a/b/c.py"), "glob ** não casou em profundidade"

        # 3) a outra ponta (beta) → blast-radius alpha+gamma
        h = match("beta/client.py")
        assert h and sorted(h[0]["blast_radius"]) == ["alpha", "gamma"], h

        # 4) arquivo não-costura → zero hits (não dispara em tudo)
        assert match("alpha/random_component.py") == [], "disparou em não-costura"

        # 5) exclude de worktrees e legado
        assert match(".claude/worktrees/wt/alpha/api.py") == [], "worktree não excluído"
        assert match("legacy/alpha/api.py") == [], "legacy não excluído"

        # 6) warn não vira block
        h = match("alpha/config.yaml")
        assert h and h[0]["severidade"] == "warn", h

        # 7) verify-cite: citação válida (linha contém símbolo) vs fantasma vs símbolo ausente
        api = os.path.join(root, "alpha", "api.py")
        os.makedirs(os.path.dirname(api), exist_ok=True)
        with open(api, "w", encoding="utf-8") as fh:
            fh.write("line1\nusa SHARED_KEY aqui\nline3 sem simbolo\n")
        assert organism.verify_cite(root, data, "seam-block", "alpha/api.py:2")["valid"] is True
        assert organism.verify_cite(root, data, "seam-block", "alpha/api.py:3")["valid"] is False  # linha sem símbolo
        assert organism.verify_cite(root, data, "seam-block", "alpha/fantasma.py:1")["valid"] is False
        assert organism.verify_cite(root, data, "seam-block", "alpha/api.py:999")["valid"] is False  # fora do arquivo

        # 8) fora de um organismo → sem dado
        with tempfile.TemporaryDirectory() as empty:
            r, d = organism.find_organism(empty)
            assert r is None and d is None, "achou organismo onde não há"

    # 9) PARIDADE do parser stdlib com PyYAML — o fallback tem que ser À ALTURA.
    # Sem isso, numa máquina sem PyYAML o engine degradaria silenciosamente.
    try:
        import yaml
        for sample in (FIXTURE, _REAL_ORGANISM_SAMPLE):
            assert organism.mini_yaml(sample) == yaml.safe_load(sample), \
                "parser stdlib divergiu do PyYAML"
        print("test_organism: paridade parser-stdlib × PyYAML OK ✓")
    except ImportError:
        # roda mesmo sem PyYAML: prova que o parser stdlib SOZINHO parseia o real.
        d = organism.mini_yaml(_REAL_ORGANISM_SAMPLE)
        assert d["name"] and len(d["costuras"]) >= 2, "parser stdlib falhou sem PyYAML"
        print("test_organism: parser stdlib OK sem PyYAML ✓")

    # 10) casos adversariais (do review do Fable) — paridade estrita + erros explícitos.
    ADVERSARIAL = [
        "k: >-\n  uma linha só\n",              # folded strip (a forma idiomática)
        "k: >+\n  linha\n\n\n",                 # folded keep
        "k: |-\n  a\n  b\n",                    # literal strip
        "k: |+\n  a\n\n",                       # literal keep
        "k: yes\n", "k: no\n", "k: on\n", "k: off\n", "k: NO\n",  # bool YAML 1.1
        "k:\n",                                  # chave vazia → None
        "k: [a, b, c]\n",                       # inline list
        "k: 1.2.3\n",                           # versão → string, não número
        "k: 42\n", "k: true\n",
        "m:\n  a: 1\n  b: [x, y]\n",            # mapping aninhado
        "L:\n  - id: one\n    sev: block\n  - id: two\n    sev: warn\n",  # lista de mappings
    ]
    try:
        import yaml
        for s in ADVERSARIAL:
            got, exp = organism.mini_yaml(s), yaml.safe_load(s)
            assert got == exp, "divergência em %r:\n  mini  =%r\n  pyyaml=%r" % (s, got, exp)
        print("test_organism: %d casos adversariais em paridade com PyYAML ✓" % len(ADVERSARIAL))
    except ImportError:
        for s in ADVERSARIAL:
            organism.mini_yaml(s)  # ao menos não levanta no subconjunto suportado
        print("test_organism: %d casos adversariais parseados (sem PyYAML) ✓" % len(ADVERSARIAL))

    # lista-de-lista está FORA do subconjunto → tem que levantar (não parse errado silencioso)
    raised = False
    try:
        organism.mini_yaml("k:\n  - - a\n")
    except ValueError:
        raised = True
    assert raised, "lista-de-lista deveria levantar ValueError, não parsear errado"

    print("test_organism: todos os asserts passaram ✓")


def _w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


# frontmatter de doc project-doc (tem doc-sig — o que classify exige)
_PD_DOC = "---\ngenerated: 2026-07-01\nproject: X\nscope: a.py\ndoc-sig: X/a@gen=3.6#abcd1234\n---\n\n# doc\n"
_V2_CLAUDE = "banner autoral grande\n" * 50 + "\n<!-- project-doc:v2 gen=3.6 -->\n# idx\n<!-- project-doc:v2:end -->\n"
_ROUTER_CLAUDE = "<!-- project-doc:module-router gen=3.6 sig=abcd1234 -->\n# finance router\n"
_AUTHORAL_CLAUDE = "# meu projeto\n\nescrito à mão, sem marker.\n"


def test_census():
    """Census 4-classes + filtro de ruído, contra um layout que reproduz o real."""
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "org")
        _w(os.path.join(root, ".claude", "organism.yaml"),
           "name: Org\nmodulos: [finance, mcp]\ncosturas:\n  - id: x\n    severidade: warn\n    aresta_msg: y\n    pontas:\n      - modulo: finance\n        globs: ['finance/**']\n      - modulo: mcp\n        globs: ['mcp/**']\n")
        # canônico: índice + doc de costura + miolo de mcp já migrado + router de mcp
        _w(os.path.join(root, ".claude", "CLAUDE.md"), _V2_CLAUDE)
        _w(os.path.join(root, ".claude", "docs", "architecture.md"), _PD_DOC)
        _w(os.path.join(root, ".claude", "docs", "modules", "mcp", "api.md"), _PD_DOC)
        _w(os.path.join(root, "mcp", ".claude", "CLAUDE.md"), _ROUTER_CLAUDE)
        # pending: finance ainda não migrado (sem modules/finance/)
        _w(os.path.join(root, "finance", ".claude", "docs", "database.md"), _PD_DOC)
        _w(os.path.join(root, "finance", ".claude", "CLAUDE.md"), _V2_CLAUDE)
        # orphan: mcp já migrado (modules/mcp existe) mas sobrou doc no módulo
        _w(os.path.join(root, "mcp", ".claude", "docs", "api.md"), _PD_DOC)
        # autoral: CLAUDE.md sem marker → fora da jurisdição
        _w(os.path.join(root, "sub", "CLAUDE.md"), _AUTHORAL_CLAUDE)
        # archived: sob _archive/
        _w(os.path.join(root, "_archive", "old", ".claude", "docs", "z.md"), _PD_DOC)
        # RUÍDO (não pode aparecer no census):
        _w(os.path.join(root, "node_modules", "p", ".claude", "docs", "n.md"), _PD_DOC)
        _w(os.path.join(root, ".claude", "worktrees", "wt", ".claude", "docs", "w.md"), _PD_DOC)
        _w(os.path.join(root, "_repos-antigos", "r", ".claude", "docs", "o.md"), _PD_DOC)

        cen = organism.census(root)
        klass = {c["path"]: c["kind"] for c in cen["docs"]}

        def K(p):
            return klass.get(p.replace("/", os.sep).replace(os.sep, "/"))

        assert cen["organism"] is True, "organismo não detectado"
        assert K(".claude/CLAUDE.md") == "canonical", K(".claude/CLAUDE.md")
        assert K(".claude/docs/architecture.md") == "canonical"
        assert K(".claude/docs/modules/mcp/api.md") == "canonical"
        assert K("mcp/.claude/CLAUDE.md") == "canonical", "router não é canônico: %s" % K("mcp/.claude/CLAUDE.md")
        assert K("finance/.claude/docs/database.md") == "pending-migration", K("finance/.claude/docs/database.md")
        assert K("finance/.claude/CLAUDE.md") == "pending-migration", "índice legado do módulo: %s" % K("finance/.claude/CLAUDE.md")
        assert K("mcp/.claude/docs/api.md") == "orphan", "leftover pós-migração: %s" % K("mcp/.claude/docs/api.md")
        assert K("sub/CLAUDE.md") == "authoral", "CLAUDE.md sem marker deve ser autoral: %s" % K("sub/CLAUDE.md")
        assert K("_archive/old/.claude/docs/z.md") == "legacy-archived"
        # ruído: NENHUM desses paths existe no census
        for noisy in ("node_modules/p/.claude/docs/n.md",
                      ".claude/worktrees/wt/.claude/docs/w.md",
                      "_repos-antigos/r/.claude/docs/o.md"):
            assert noisy not in klass, "ruído vazou no census: %s" % noisy
        print("test_organism: census 4-classes + filtro de ruído ✓")


def test_dirty_propagation():
    """dirty = módulo direto ∪ blast-radius da costura (Fase 3 lazy)."""
    data = {
        "modulos": ["finance", "mcp", "servico"],
        "costuras": [{
            "id": "rede", "severidade": "warn", "aresta_msg": "y",
            "pontas": [
                {"modulo": "finance", "globs": ["finance/**"]},
                {"modulo": "mcp", "globs": ["mcp/**"]},
            ],
        }],
    }
    root = "/tmp/pdtest_dirty_root"  # não precisa existir (core é puro)
    # mudou só arquivo do finance → finance direto + mcp por propagação; servico limpo
    dirty = organism.dirty_modules_from_changes(root, data, ["finance/src/x.ts"])
    assert "finance" in dirty, "finance direto: %s" % dirty
    assert "mcp" in dirty, "mcp deveria sujar por propagação da costura: %s" % dirty
    assert "servico" not in dirty, "servico não tem costura com finance: %s" % dirty
    # mudança fora de qualquer módulo/costura → nenhum sujo
    assert organism.dirty_modules_from_changes(root, data, ["README.md"]) == [], "README não suja ninguém"
    print("test_organism: dirty-modules + propagação por costura ✓")


_ORG_COM_REGRA = """name: MEU-ORG
modulos: [alpha]
golden_rule: >
  Isto é UM organismo, não N ilhas.
  Toda ação considera os demais.
costuras: []
"""

_QG = """---
generated: 2026-08-06
project: MEU-ORG
authored-by: human
status: approved
approved: 2026-08-06
---

# Metas de qualidade

> Ordem de prioridade quando não dá para ter tudo.

## A ordem

1. **integridade do dado** — nenhum registro se perde
2. **disponibilidade** — o sistema fica no ar
"""

_CONSTRAINTS = """---
generated: 2026-08-06
project: MEU-ORG
authored-by: human
status: draft
---

# Restrições

## Técnicas
- **Python 3.11 travado** — a imagem base não sobe · **dura**
- **{restrição}** — {por quê} · **{dura | datada}**
- **auth** — [PENDENTE]
"""

_MINERADA = """---
generated: 2026-08-06
project: MEU-ORG
scope: alpha/**
doc-sig: X/a@gen=3.6#abcd1234
---

# Arquitetura

- **isto é minerado** — não é herança
"""


_BLUEPRINT = """---
generated: 2026-08-06
project: MEU-ORG
authored-by: human
status: approved
approved: 2026-08-06
---

# Desenho do sistema

- O pedido entra pela borda e só o worker toca o banco
"""


def test_blueprint_herda():
    """S-67: o desenho do sistema (blueprint.md) é herança ao lado das jornadas, e
    cada item sai com a fonte apontada linha a linha."""
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "org")
        _w(os.path.join(root, ".claude", "organism.yaml"), _ORG_COM_REGRA)
        _w(os.path.join(root, ".claude", "docs", "blueprint.md"), _BLUEPRINT)
        alpha = os.path.join(root, "alpha")
        os.makedirs(alpha)

        itens = organism.inherited(alpha)["itens"]
        bp = [i for i in itens if i["tipo"] == "desenho-do-sistema"]
        assert len(bp) == 1, itens
        assert "só o worker toca o banco" in bp[0]["texto"], bp
        assert bp[0]["fonte"].startswith(".claude/docs/blueprint.md:"), bp
        assert organism.cite_ok(root, bp[0])["valid"] is True, bp
    print("test_organism: blueprint.md entra na herança com fonte por linha (S-67) ✓")


def test_inherited():
    """S-12: o app dentro do organismo herda o que foi escrito DE PROPÓSITO na
    raiz, e cada item herdado sai com a fonte citada (arquivo:linha real)."""
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "org")
        _w(os.path.join(root, ".claude", "organism.yaml"), _ORG_COM_REGRA)
        _w(os.path.join(root, ".claude", "docs", "quality-goals.md"), _QG)
        _w(os.path.join(root, ".claude", "docs", "constraints.md"), _CONSTRAINTS)
        _w(os.path.join(root, ".claude", "docs", "architecture.md"), _MINERADA)
        alpha = os.path.join(root, "alpha")
        os.makedirs(alpha)

        got = organism.inherited(alpha)
        assert got["organism"] is True, got
        assert got["modulo"] == "alpha", got
        itens = got["itens"]
        assert itens, "nada herdado"

        # a regra de ouro do organismo é herança
        regra = [i for i in itens if i["tipo"] == "regra-de-ouro"]
        assert len(regra) == 1, regra
        assert "organismo" in regra[0]["texto"], regra

        textos = [i["texto"] for i in itens]
        assert any("integridade do dado" in t for t in textos), textos
        assert any("Python 3.11 travado" in t for t in textos), textos
        # doc minerada (sem authored-by: human) não é herança
        assert not any("isto é minerado" in t for t in textos), textos
        # molde não preenchido e lacuna aberta não são "escrito de propósito"
        assert not any("{restrição}" in t for t in textos), textos
        assert not any("PENDENTE" in t for t in textos), textos

        # CRITÉRIO DE PRONTO: todo item traz a fonte citada, e a citação é real
        for i in itens:
            assert ":" in (i.get("fonte") or ""), "item sem fonte: %s" % i
            ok = organism.cite_ok(root, i)
            assert ok["valid"] is True, "fonte não confere: %s → %s" % (i, ok)

        # o próprio organismo não herda de si: na raiz não há item
        assert organism.inherited(root)["itens"] == [], organism.inherited(root)

    # fora de organismo → nada (fail-open)
    with tempfile.TemporaryDirectory() as empty:
        assert organism.inherited(empty)["organism"] is False
    print("test_organism: herança com fonte citada por item (S-12) ✓")


def test_apresentacao_item_a_item():
    """S-12: a ABERTURA apresenta o herdado ITEM A ITEM, e a lista sai da entrada
    REAL — uma linha por item, cada uma com o texto e a fonte que o organismo tem.
    Não basta a skill mencionar: o programa é que escreve a lista."""
    with tempfile.TemporaryDirectory() as d:
        root = os.path.join(d, "org")
        _w(os.path.join(root, ".claude", "organism.yaml"), _ORG_COM_REGRA)
        _w(os.path.join(root, ".claude", "docs", "quality-goals.md"), _QG)
        _w(os.path.join(root, ".claude", "docs", "constraints.md"), _CONSTRAINTS)
        alpha = os.path.join(root, "alpha")
        os.makedirs(alpha)

        info = organism.inherited(alpha)
        itens = info["itens"]
        assert len(itens) >= 3, itens

        texto = organism.render_inherited(info)
        linhas = texto.split("\n")
        # cabeçalho + 1 linha por item + a pergunta de conferência
        numeradas = [ln for ln in linhas if ln[:1].isdigit()]
        assert len(numeradas) == len(itens), (numeradas, itens)
        for n, item in enumerate(itens, 1):
            esperado = "%d. [%s] %s  <- %s" % (n, item["tipo"], item["texto"], item["fonte"])
            assert esperado in linhas, "item %d não foi apresentado: %r\n%s" % (n, esperado, texto)
        assert str(len(itens)) in linhas[0], linhas[0]
        assert "UM A UM" in linhas[0], linhas[0]

        # a lista veio da ENTRADA, não de texto fixo: item novo no doc → linha nova
        _w(os.path.join(root, ".claude", "docs", "constraints.md"),
           _CONSTRAINTS + "\n- Sem serviço pago no caminho crítico\n")
        texto2 = organism.render_inherited(organism.inherited(alpha))
        assert "Sem serviço pago no caminho crítico" in texto2, texto2
        assert len([ln for ln in texto2.split("\n") if ln[:1].isdigit()]) == len(itens) + 1, texto2

        # a raiz não herda de si → nada a apresentar
        assert organism.render_inherited(organism.inherited(root)) == ""

    with tempfile.TemporaryDirectory() as empty:  # fora de organismo
        assert organism.render_inherited(organism.inherited(empty)) == ""
    print("test_organism: abertura apresenta o herdado item a item (S-12) ✓")


def test_organism_engine():  # entrada pytest
    run()
    test_census()
    test_dirty_propagation()
    test_inherited()
    test_blueprint_herda()
    test_apresentacao_item_a_item()


if __name__ == "__main__":
    run()
    test_census()
    test_dirty_propagation()
    test_inherited()
    test_blueprint_herda()
    test_apresentacao_item_a_item()
