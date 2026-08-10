#!/usr/bin/env python3
"""Bancada do doc_load.py — a régua do projeto, carregada por programa.

O caso que manda: a marca tem que bater com a do `lib-doc-mark.sh`. Duas receitas para o
mesmo texto dariam dois números, e a comparação da missão longa nunca fecharia.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("doc_load", os.path.join(AQUI, "doc_load.py"))
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)

ok = falhou = 0


def check(nome, cond, detalhe=""):
    global ok, falhou
    if cond:
        ok += 1
        print(f"  ok   {nome}")
    else:
        falhou += 1
        print(f"  FAIL {nome}")
        if detalhe:
            print(f"       {detalhe}")


def projeto(docs):
    """Cria um projeto de mentira com os documentos pedidos. Devolve a raiz."""
    raiz = tempfile.mkdtemp(prefix="doc-load-")
    os.makedirs(os.path.join(raiz, ".claude", "docs"))
    for nome, conteudo in docs.items():
        with open(os.path.join(raiz, ".claude", "docs", nome), "w", encoding="utf-8") as fh:
            fh.write(conteudo)
    return raiz


DOC_LEI_READY = """---
project: teste
authored-by: human
status: ready
---

# A lei

Regra um.
"""

DOC_LEI_DRAFT = DOC_LEI_READY.replace("status: ready", "status: draft")

DOC_ACORDO_READY = """---
project: teste
authored-by: human
status: ready
---

# O esquema

Assim funciona.
"""

DOC_ACORDO_APPROVED = """---
project: teste
authored-by: human
status: approved
approved: 2026-08-09
approved-sig: SUBSTITUIR
---

# O esquema

Assim funciona.
"""

DOC_MINERADO = """---
project: teste
generated: 2026-08-09
---

# A estrutura de hoje

Existe isto.
"""

print("bancada do doc_load")
print()

# ── a marca é a MESMA do shell ────────────────────────────────────────────────
raiz = projeto({"constituicao.md": DOC_LEI_READY})
alvo = os.path.join(raiz, ".claude", "docs", "constituicao.md")
py = dl.cksum(alvo)
shell = subprocess.run(
    ["sh", "-c", f". {AQUI}/../hooks/lib-doc-mark.sh && doc_marca '{alvo}'"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
check("a marca do programa bate com a do lib-doc-mark.sh",
      shell.returncode == 0 and shell.stdout.strip() == str(py),
      f"shell={shell.stdout.strip()!r} python={py}")

# ── o frontmatter fica FORA da marca ──────────────────────────────────────────
r2 = projeto({"constituicao.md": DOC_LEI_READY.replace("status: ready", "status: approved")})
check("mudar só o frontmatter NÃO muda a marca",
      dl.cksum(os.path.join(r2, ".claude", "docs", "constituicao.md")) == py)

r3 = projeto({"constituicao.md": DOC_LEI_READY.replace("Regra um.", "Regra dois.")})
check("mudar o CORPO muda a marca",
      dl.cksum(os.path.join(r3, ".claude", "docs", "constituicao.md")) != py)

# ── lei: ready vale, draft não ────────────────────────────────────────────────
e = dl.carrega(projeto({"constituicao.md": DOC_LEI_READY}))
check("lei com status ready VALE como régua", e["regua"] == [".claude/docs/constituicao.md"], str(e["regua"]))

e = dl.carrega(projeto({"constituicao.md": DOC_LEI_DRAFT}))
check("lei com status draft NÃO vale como régua", e["regua"] == [], str(e["regua"]))
check("e o motivo diz que rascunho não é lei",
      any("rascunho não é lei" in d["motivo"] for d in e["documentos"]),
      str([d["motivo"] for d in e["documentos"]]))

# ── acordo: só approved vale ──────────────────────────────────────────────────
e = dl.carrega(projeto({"blueprint.md": DOC_ACORDO_READY}))
check("acordo com status ready NÃO vale como régua", e["regua"] == [], str(e["regua"]))

r = projeto({"blueprint.md": DOC_ACORDO_APPROVED})
alvo = os.path.join(r, ".claude", "docs", "blueprint.md")
real = dl.cksum(alvo)
with open(alvo, encoding="utf-8") as fh:
    txt = fh.read()
with open(alvo, "w", encoding="utf-8") as fh:
    fh.write(txt.replace("SUBSTITUIR", str(real)))
e = dl.carrega(r)
check("acordo approved com a marca batendo VALE", e["regua"] == [".claude/docs/blueprint.md"], str(e["regua"]))

# ── acordo editado depois do de acordo REABRE ─────────────────────────────────
with open(alvo, encoding="utf-8") as fh:
    txt = fh.read()
with open(alvo, "w", encoding="utf-8") as fh:
    fh.write(txt.replace("Assim funciona.", "Assim funciona, com uma emenda."))
e = dl.carrega(r)
check("acordo editado DEPOIS do de acordo sai da régua", e["regua"] == [], str(e["regua"]))
check("e ele aparece como reaberto", e["reabertos"] == [".claude/docs/blueprint.md"], str(e["reabertos"]))

# ── minerado nunca é régua ────────────────────────────────────────────────────
e = dl.carrega(projeto({"architecture.md": DOC_MINERADO}))
check("documento minerado NUNCA vale como régua", e["regua"] == [], str(e["regua"]))
check("e ele aparece no mapa, com o motivo",
      any(d["arquivo"].endswith("architecture.md") and "mapa" in d["motivo"] for d in e["documentos"]))

# ── ausência não é erro ───────────────────────────────────────────────────────
e = dl.carrega(projeto({}))
check("projeto sem documento nenhum devolve régua vazia", e["regua"] == [])
check("e nomeia os ausentes em vez de calar", len(e["ausentes"]) >= 10, str(len(e["ausentes"])))
check("a marca da régua é nula quando não há régua", e["marca_regua"] is None, str(e["marca_regua"]))

vazio = tempfile.mkdtemp(prefix="doc-load-sem-claude-")
e = dl.carrega(vazio)
check("projeto sem .claude/docs/ não estoura", e["documentos"] == [])

# ── a marca da régua muda quando a lei muda ───────────────────────────────────
a = dl.carrega(projeto({"constituicao.md": DOC_LEI_READY}))["marca_regua"]
b = dl.carrega(projeto({"constituicao.md": DOC_LEI_READY.replace("Regra um.", "Regra três.")}))["marca_regua"]
check("editar a lei muda a marca da régua", a != b, f"{a} vs {b}")
check("a marca da régua junta os documentos que valem, em ordem",
      dl.carrega(projeto({"constituicao.md": DOC_LEI_READY,
                          "quality-goals.md": DOC_LEI_READY}))["marca_regua"].count("+") == 1)

# ── correção pendente aparece ─────────────────────────────────────────────────
com_pendencia = DOC_LEI_READY.replace("status: ready",
                                      "status: ready\ncorrecao-pendente: o artigo 3 contradiz o disco")
e = dl.carrega(projeto({"constituicao.md": com_pendencia}))
check("correção pendente declarada pelo dono aparece",
      e["correcoes_pendentes"] and "artigo 3" in e["correcoes_pendentes"][0]["o_que_falta"],
      str(e["correcoes_pendentes"]))

# ── dispensa ──────────────────────────────────────────────────────────────────
e = dl.carrega(projeto({"dispensa.md": "---\nmotivo: projeto de uma tarde\n---\n"}))
check("dispensa com motivo é lida", e["dispensa"] and e["dispensa"]["motivo"] == "projeto de uma tarde")
e = dl.carrega(projeto({"dispensa.md": "---\nmotivo:\n---\n"}))
check("dispensa SEM motivo aparece com motivo nulo", e["dispensa"]["motivo"] is None)

# ── o comando de linha ────────────────────────────────────────────────────────
r = projeto({"constituicao.md": DOC_LEI_READY})
p = subprocess.run([sys.executable, os.path.join(AQUI, "doc_load.py"), "--project-root", r],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
check("o comando sai 0 e diz o que vale como régua",
      p.returncode == 0 and "VALE COMO RÉGUA" in p.stdout and "constituicao.md" in p.stdout,
      p.stdout[:200])

p = subprocess.run([sys.executable, os.path.join(AQUI, "doc_load.py"), "--project-root", r, "--json"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
check("--json devolve JSON válido com a régua dentro",
      p.returncode == 0 and json.loads(p.stdout)["regua"] == [".claude/docs/constituicao.md"])

p = subprocess.run([sys.executable, os.path.join(AQUI, "doc_load.py"), "--project-root", r, "--marca"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
check("--marca imprime só o número", p.returncode == 0 and p.stdout.strip().isdigit(), p.stdout[:80])

p = subprocess.run([sys.executable, os.path.join(AQUI, "doc_load.py"), "--project-root", "/nao/existe"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
check("raiz inexistente reprova em voz alta, não em silêncio",
      p.returncode == 2 and "não é um diretório" in p.stderr, f"rc={p.returncode} {p.stderr[:80]}")

# ── a skill declara o par com principles ──────────────────────────────────────
skill = os.path.join(AQUI, "..", "skills", "doc-load", "SKILL.md")
texto = open(skill, encoding="utf-8").read() if os.path.isfile(skill) else ""
check("a receita existe", bool(texto))
check("a receita manda rodar principles logo depois", "/principles" in texto)
check("a receita diz quem ganha no conflito", "ganha o `/doc-load`" in texto)
check("a receita traz a tabela de etapas", "`/principles review`" in texto)

print()
print(f"{ok} passou · {falhou} falhou")
sys.exit(1 if falhou else 0)
