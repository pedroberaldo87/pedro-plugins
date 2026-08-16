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
sys.path.insert(0, AQUI)
from bash_posix import bash_posix  # noqa: E402
from caminho_igual import igual  # noqa: E402

BASH = bash_posix()


def mesma_lista(achado, esperado):
    """Duas listas de CAMINHO, comparadas como caminho — a barra e do sistema.

    No Windows o `carrega` devolve `.claude\\docs\\x.md` e o esperado escrito
    aqui tem barra normal: o mesmo arquivo, e a igualdade de lista dizia que nao.
    """
    return (len(achado or []) == len(esperado)
            and all(igual(a, b) for a, b in zip(achado, esperado)))
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
LIB_MARK = os.path.join(AQUI, os.pardir, "hooks", "lib-doc-mark.sh").replace(os.sep, "/")


def marca_do_shell(caminho):
    """A marca pela receita do shell. Caminho em barra NORMAL: o Git-Bash do Windows
    engasga com a invertida dentro de aspas simples (ela lá é escape, não separador)."""
    r = subprocess.run(
        [BASH, "-c", f". '{LIB_MARK}' && doc_marca '{caminho.replace(os.sep, '/')}'"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL, start_new_session=True)
    return r.returncode, r.stdout.strip()


raiz = projeto({"constituicao.md": DOC_LEI_READY})
alvo = os.path.join(raiz, ".claude", "docs", "constituicao.md")
py = dl.cksum(alvo)
if BASH is None:
    print("  skip a marca do programa bate com a do lib-doc-mark.sh"
          " (nenhum bash funcional nesta máquina)")
else:
    rc, saida = marca_do_shell(alvo)
    check("a marca do programa bate com a do lib-doc-mark.sh",
          rc == 0 and saida == str(py), f"shell={saida!r} python={py}")

    # O mesmo documento com fim de linha do Windows (CRLF) tem que dar a MESMA marca
    # nas duas receitas — foi por aqui que elas divergiam, um `\r` por linha.
    r_crlf = tempfile.mkdtemp(prefix="doc-load-crlf-")
    os.makedirs(os.path.join(r_crlf, ".claude", "docs"))
    alvo_crlf = os.path.join(r_crlf, ".claude", "docs", "constituicao.md")
    with open(alvo_crlf, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write(DOC_LEI_READY)
    rc_crlf, saida_crlf = marca_do_shell(alvo_crlf)
    check("documento em CRLF: as duas receitas continuam dando a mesma marca",
          rc_crlf == 0 and saida_crlf == str(dl.cksum(alvo_crlf)) == str(py),
          f"shell={saida_crlf!r} python={dl.cksum(alvo_crlf)} lf={py}")

# ── o frontmatter fica FORA da marca ──────────────────────────────────────────
r2 = projeto({"constituicao.md": DOC_LEI_READY.replace("status: ready", "status: approved")})
check("mudar só o frontmatter NÃO muda a marca",
      dl.cksum(os.path.join(r2, ".claude", "docs", "constituicao.md")) == py)

r3 = projeto({"constituicao.md": DOC_LEI_READY.replace("Regra um.", "Regra dois.")})
check("mudar o CORPO muda a marca",
      dl.cksum(os.path.join(r3, ".claude", "docs", "constituicao.md")) != py)

# ── lei: ready vale, draft não ────────────────────────────────────────────────
e = dl.carrega(projeto({"constituicao.md": DOC_LEI_READY}))
check("lei com status ready VALE como régua",
      mesma_lista(e["regua"], [".claude/docs/constituicao.md"]), str(e["regua"]))

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
check("acordo approved com a marca batendo VALE",
      mesma_lista(e["regua"], [".claude/docs/blueprint.md"]), str(e["regua"]))

# ── acordo editado depois do de acordo REABRE ─────────────────────────────────
with open(alvo, encoding="utf-8") as fh:
    txt = fh.read()
with open(alvo, "w", encoding="utf-8") as fh:
    fh.write(txt.replace("Assim funciona.", "Assim funciona, com uma emenda."))
e = dl.carrega(r)
check("acordo editado DEPOIS do de acordo sai da régua", e["regua"] == [], str(e["regua"]))
check("e ele aparece como reaberto",
      mesma_lista(e["reabertos"], [".claude/docs/blueprint.md"]), str(e["reabertos"]))

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

# ── a lacuna sai separada por natureza, e sobe para o TOPO ────────────────────
e = dl.carrega(projeto({"constituicao.md": DOC_LEI_READY}))
check("a lacuna separa lei, acordo e mapa",
      e["ausentes_lei"] == ["quality-goals.md", "constraints.md"]
      and len(e["ausentes_acordo"]) == 8 and len(e["ausentes_minerados"]) == 5,
      f"{e['ausentes_lei']} / {e['ausentes_acordo']} / {e['ausentes_minerados']}")
check("e a soma das três continua sendo o campo de sempre",
      e["ausentes"] == e["ausentes_lei"] + e["ausentes_acordo"] + e["ausentes_minerados"])

linhas = dl.texto(e).splitlines()
check("a lacuna é a PRIMEIRA linha, não o rodapé",
      linhas[0].startswith("⚠️ LACUNA") and "15 de 16" in linhas[0], linhas[0])
check("e cada natureza vem com o comando que a resolve",
      any("lei:" in ln and "/start escreve" in ln for ln in linhas)
      and any("mapa:" in ln and "/doc extrai do código" in ln for ln in linhas),
      "\n".join(linhas[:5]))
check("a lacuna aparece ANTES do que vale como régua",
      linhas.index([ln for ln in linhas if ln.startswith("⚠️ LACUNA")][0])
      < linhas.index("VALE COMO RÉGUA — julgue contra estes, e cite a passagem:"))

completo = {nome: DOC_LEI_READY for nome, _ in dl.LEI}
completo.update({nome: DOC_ACORDO_READY for nome, _ in dl.ACORDO})
completo.update({nome: DOC_MINERADO for nome, _ in dl.MINERADOS})
e = dl.carrega(projeto(completo))
check("projeto com os 16 canônicos em disco não deixa ausente nenhum",
      e["ausentes"] == [], str(e["ausentes"]))
check("projeto completo não inventa lacuna nenhuma",
      "LACUNA" not in dl.texto(e), dl.texto(e)[:120])

# ── dispensa ──────────────────────────────────────────────────────────────────
e = dl.carrega(projeto({"dispensa.md": "---\nmotivo: projeto de uma tarde\n---\n"}))
check("dispensa com motivo é lida", e["dispensa"] and e["dispensa"]["motivo"] == "projeto de uma tarde")
check("e dispensa com motivo escrito CALA a lacuna", "LACUNA" not in dl.texto(e), dl.texto(e)[:120])

e = dl.carrega(projeto({"dispensa.md": "---\nmotivo:\n---\n"}))
check("dispensa SEM motivo aparece com motivo nulo", e["dispensa"]["motivo"] is None)
check("e dispensa sem motivo NÃO cala — a lacuna sobe e diz o que falta escrever",
      dl.texto(e).startswith("⚠️ LACUNA")
      and "dispensa declarada SEM MOTIVO ESCRITO" in dl.texto(e), dl.texto(e)[:200])

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
      p.returncode == 0 and mesma_lista(json.loads(p.stdout)["regua"],
                                        [".claude/docs/constituicao.md"]))

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

# ── a oferta distingue projeto nascendo de projeto maduro (F3.1) ─────────────
# Sem os dois ramos, a lacuna de um projeto com meses de obra mandava o dono para
# uma entrevista do zero — desperdicando o que o repositório já manifesta.
check("a oferta tem o ramo do projeto nascendo", "projeto nascendo" in texto)
check("a oferta tem o ramo do projeto maduro, citando o modo ex-post",
      "projeto maduro" in texto and "`/start ex-post`" in texto)
check("o ramo maduro diz o porquê: inferir e referendar, não entrevistar do zero",
      "referendo" in texto)

# ── o sidecar do protótipo é ANEXO, fora da régua congelada (F13.1) ──────────
DOC_DESIGN = """---
project: teste
authored-by: human
status: approved
approved-sig: SUBSTITUIR
---

# O desenho

Botões azuis.
"""

SIDECAR = """---
natureza: anexo
anexo-de: design.md
design-sig: {design_sig}
status: approved
conjunto-sig: {conjunto_sig}
marcador-ficticio: DADO-FICTICIO
---

## Arquivos

- .claude/docs/prototipo/painel.html
"""


def projeto_com_anexo(tela="<h1>Painel</h1>\n"):
    """Projeto com design.md aprovado (marca batendo) e um sidecar de protótipo válido."""
    r = projeto({"constituicao.md": DOC_LEI_READY, "design.md": DOC_DESIGN})
    design = os.path.join(r, ".claude", "docs", "design.md")
    with open(design, encoding="utf-8") as fh:
        txt = fh.read()
    with open(design, "w", encoding="utf-8") as fh:
        fh.write(txt.replace("SUBSTITUIR", str(dl.cksum(design))))
    casa = os.path.join(r, ".claude", "docs", "prototipo")
    os.makedirs(casa)
    with open(os.path.join(casa, "painel.html"), "w", encoding="utf-8", newline="") as fh:
        fh.write(tela)
    sig = dl._conjunto_sig(r, [".claude/docs/prototipo/painel.html"])
    with open(os.path.join(casa, "interface.prototipo.md"), "w", encoding="utf-8") as fh:
        fh.write(SIDECAR.format(design_sig=dl.cksum(design), conjunto_sig=sig))
    return r


r = projeto_com_anexo()
sem_anexo = dl.carrega(projeto({"constituicao.md": DOC_LEI_READY}))
e = dl.carrega(r)
check("o sidecar entra como anexo, aprovado",
      len(e["anexos"]) == 1 and e["anexos"][0]["vale"]
      and e["anexos"][0]["natureza"] == "anexo"
      and igual(e["anexos"][0]["anexo_de"], "design.md"), str(e["anexos"]))
check("o anexo fica FORA da régua",
      not any("prototipo" in a for a in e["regua"]), str(e["regua"]))
check("e não contamina a marca congelada da lei",
      e["marca_regua"].split("+")[0] == sem_anexo["marca_regua"],
      f"{e['marca_regua']} vs {sem_anexo['marca_regua']}")
check("o texto imprime o anexo na seção própria", "ANEXO" in dl.texto(e), dl.texto(e)[:400])

r2 = projeto_com_anexo()
with open(os.path.join(r2, ".claude", "docs", "prototipo", "painel.html"),
          "w", encoding="utf-8", newline="") as fh:
    fh.write("<h1>Painel mudado</h1>\n")
e = dl.carrega(r2)
check("trocar uma tela ACUSA divergência do conjunto",
      e["anexos"][0]["divergencia_conjunto"] and e["anexos"][0]["reaberto"]
      and not e["anexos"][0]["vale"] and "protótipo mudado" in e["anexos"][0]["motivo"],
      str(e["anexos"]))

r3 = projeto_com_anexo()
design = os.path.join(r3, ".claude", "docs", "design.md")
velho = dl.frontmatter(design)["approved-sig"]
with open(design, encoding="utf-8") as fh:
    txt = fh.read()
txt = txt.replace("Botões azuis.", "Botões verdes.")
with open(design, "w", encoding="utf-8") as fh:
    fh.write(txt)
novo = dl.cksum(design)
with open(design, "w", encoding="utf-8") as fh:
    fh.write(txt.replace(f"approved-sig: {velho}", f"approved-sig: {novo}"))
e = dl.carrega(r3)
check("regravar o de acordo do design REABRE o anexo",
      e["anexos"][0]["reaberto"] and not e["anexos"][0]["divergencia_conjunto"]
      and "regravado" in e["anexos"][0]["motivo"], str(e["anexos"]))
check("o design regravado continua valendo como régua — só o anexo reabriu",
      any(igual(a, ".claude/docs/design.md") for a in e["regua"]), str(e["regua"]))

e = dl.carrega(projeto({"constituicao.md": DOC_LEI_READY}))
check("projeto sem casa de protótipo devolve anexos vazio", e["anexos"] == [])

print()
print(f"{ok} passou · {falhou} falhou")
sys.exit(1 if falhou else 0)
