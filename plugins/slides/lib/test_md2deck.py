#!/usr/bin/env python3
"""Suite do md2deck.py — stdlib, sem framework (padrão do repo).

O check que mais importa é o último grupo: o deck compilado passa pelo
`check_fidelity.py` REAL, que é o gate que a skill sempre rodou à mão. Se a
fidelidade é propriedade da construção, esse gate nunca mais pode acusar.

    python3 plugins/slides/lib/test_md2deck.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md2deck as M  # noqa: E402

PASS = FAIL = 0
HERE = os.path.dirname(os.path.abspath(__file__))
CHECK_FID = os.path.join(HERE, "..", "skills", "slides", "scripts", "check_fidelity.py")


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


MD = """\
# Agentes de código na prática

- Público — times de produto
- Duração — 40 minutos

# Fase 1

## O que mudou no fluxo de trabalho

- Prompt avulso virou skill versionada no repositório
- Revisão manual virou gate mecânico no commit
- Documentação escrita virou documentação minerada

## O salto de escala

O custo por tarefa caiu de 10 → 40 unidades de trabalho por hora.

## Uma frase que resume tudo

Contexto é o recurso escasso, não inteligência.

## Os quatro pilares do método

- Skills — instruções versionadas que o agente carrega sob demanda
- Hooks — gates que rodam no harness, fora do julgamento do modelo
- Journal — memória append-only que sobrevive ao fim da sessão
- Grafo — mapa de dependências consultado antes de qualquer busca cega

## O que cada camada entrega

- **Determinismo** o programa emite, o modelo decide
- **Rastreabilidade** toda conclusão aponta pra saída que a produziu

## Lista longa demais pra um slide

- Primeiro item da lista longa que precisa quebrar
- Segundo item da lista longa que precisa quebrar
- Terceiro item da lista longa que precisa quebrar
- Quarto item da lista longa que precisa quebrar
- Quinto item da lista longa que precisa quebrar
- Sexto item da lista longa que precisa quebrar
- Sétimo item da lista longa que precisa quebrar
- Oitavo item da lista longa que precisa quebrar
"""


def build_tmp(md=MD, anota=None, tema="viu"):
    td = tempfile.mkdtemp()
    p = os.path.join(td, "fonte.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(md)
    out, pl, n = M.build(p, tema, anota or {})
    return p, out, pl, n


# ── parse ──────────────────────────────────────────────────────────────────

print("\n[parse — o esqueleto sai dos headings]")

blocos = M.parse_md(MD)
N_HEADINGS = 8   # 2 h1 + 6 h2 no MD acima
N_BULLETS = 19   # 2 + 3 + 4 + 2 + 8
check("headings reconhecidos", sum(1 for b in blocos if b["t"] == "h") == N_HEADINGS,
      sum(1 for b in blocos if b["t"] == "h"))
check("bullets reconhecidos", sum(1 for b in blocos if b["t"] == "li") == N_BULLETS,
      sum(1 for b in blocos if b["t"] == "li"))

slides = M.agrupar(blocos)
check("um slide por heading", len(slides) == N_HEADINGS, len(slides))
check("a seção é herdada pelos slides de conteúdo",
      slides[2]["secao"] == "Fase 1" and slides[2]["level"] == 2, slides[2]["secao"])

b = M.parse_md("- a\n\n```py\nx = 1\ny = 2\n```\n")
check("bloco de código vira 'code', não parágrafo reescrito",
      any(x["t"] == "code" and x["text"] == "x = 1\ny = 2" for x in b), b)
check("linha de tabela não entra como fala do autor",
      not any(x["t"] == "p" for x in M.parse_md("| a | b |\n|---|---|\n")))


# ── escolha de componente ──────────────────────────────────────────────────

print("\n[escolha de componente — a regra do mapa da skill]")

pl = M.plano(slides, {})
por_head = {p["heading"]: p["component"] for p in pl}
check("1º h1 é a capa", pl[0]["component"] == "cover", pl[0])
check("h1 seguinte é section divider", por_head["Fase 1"] == "divider", por_head)
check("bullets curtos → numlist",
      por_head["O que mudou no fluxo de trabalho"] == "numlist", por_head)
check("bullets 'nome — descrição' → idx",
      por_head["Os quatro pilares do método"] == "idx", por_head)
check("2-3 bullets com lead em negrito → feats",
      por_head["O que cada camada entrega"] == "feats", por_head)
check("parágrafo curto solto → statement",
      por_head["Uma frase que resume tudo"] == "statement", por_head)
check("parágrafo com X → Y → metric", por_head["O salto de escala"] == "metric", por_head)

longo = next(p for p in pl if p["itens"] == 8)
check("lista de 8 quebra em 2 slides (densidade)", longo["slides_gerados"] == 2, longo)

pl2 = M.plano(slides, {"Os quatro pilares do método": {"component": "numlist"}})
check("anotação sobrepõe a heurística",
      {p["heading"]: p["component"] for p in pl2}["Os quatro pilares do método"] == "numlist")
pl3 = M.plano(slides, {"Lista longa demais pra um slide": {"split": 3}})
check("anotação muda o ponto de quebra",
      next(p for p in pl3 if p["itens"] == 8)["slides_gerados"] == 3)

try:
    M.plano(slides, {"Fase 1": {"component": "carrossel"}})
    check("componente inexistente é recusado com a lista do que existe", False)
except M.DeckError as e:
    check("componente inexistente é recusado com a lista do que existe",
          "carrossel" in str(e) and "numlist" in str(e))


# ── emissão ────────────────────────────────────────────────────────────────

print("\n[emissão — o HTML sai com o vocabulário real do template]")

src, out, pl, n = build_tmp()
deck = open(out, encoding="utf-8").read()

check("nenhum placeholder sobrou", not re.findall(r"__[A-Z_]+__", deck))
# NÃO basta a string existir: ela tem que estar FORA de comentário, senão o deck sai
# branco com fonte serif e nada acusa. Foi o bug real de 2026-07-29 — o replace global
# injetava o :root dentro do /* __THEME_CSS__ : … */ e o primeiro */ do tema fechava.
estilo = "\n".join(re.findall(r"<style>(.*?)</style>", deck, re.S))
sem_com = re.sub(r"/\*.*?\*/", "", estilo, flags=re.S)
check("o tema entrou (paleta do viu)", "--bg-body:#0f172a" in sem_com.replace(" ", ""))
check("o :root do tema está ATIVO, fora de comentário", ":root" in sem_com)
check("nenhum comentário do template sobrou carregando placeholder",
      "__THEME_CSS__" not in deck and "__FONT_LINKS__" not in deck)
check("o <link> de fonte não saiu duplicado (uma vez, não dentro de comentário)",
      deck.count("fonts.googleapis.com/css2") == 1,
      deck.count("fonts.googleapis.com/css2"))
check("a marca do tema entrou", "VIU Studio" in deck)
check("uma section por slide", deck.count('<section class="slide') == n, (deck.count('<section class="slide'), n))
check("capa presente", '<section class="slide cover">' in deck)
check("divider com número de seção", '<div class="section-num' in deck and ">01<" in deck)
check("numlist emitido", 'class="numlist' in deck)
check("idx emitido", 'class="idx' in deck)
check("feats emitido", 'class="feats' in deck)
check("statement emitido", 'class="statement' in deck)
check("metric emitido com os dois números",
      'class="metric' in deck and '<span class="from">10</span>' in deck
      and '<span class="to">40</span>' in deck)
check("reveals escalonados", "--d:40ms" in deck and "--d:130ms" in deck and "--d:210ms" in deck)
check("eyebrow carrega a seção", 'class="eyebrow' in deck and "Fase 1" in deck)

# no feats o negrito É o título (vira <h3>), então o teste do negrito-em-corpo
# roda num numlist, que é onde a marcação tem que sobreviver
check("feats usa o negrito como título, não como texto com asteriscos",
      "<h3>Determinismo</h3>" in deck and "**Determinismo**" not in deck)
_, out_b, _, _ = build_tmp("# T\n\n## Corpo com marcacao\n\n"
                           "- item com **negrito** e `codigo` no meio da frase inteira\n"
                           "- segundo item pra virar lista de verdade aqui tambem\n")
db = open(out_b, encoding="utf-8").read()
check("negrito no corpo de um numlist vira <strong>",
      "<strong>negrito</strong>" in db and "**negrito**" not in db)
check("`código` no corpo vira <code>", "<code>codigo</code>" in db)

# a lista de 8 virou 2 slides, e a numeração NÃO reinicia
check("numeração continua no slide seguinte da quebra",
      '<span class="nn">07</span>' in deck and '<span class="nn">08</span>' in deck)

# o conteúdo do autor não é duplicado quando o slide quebra
check("parágrafo não é repetido no 2º pedaço da quebra",
      deck.count("Contexto é o recurso escasso") == 1)


# ── escape ─────────────────────────────────────────────────────────────────

print("\n[escape — o .md pode ter qualquer caractere]")

_, out2, _, _ = build_tmp("# Deck & <cia>\n\n## Um <script>alert(1)</script> no meio\n\n"
                          "- item com & e < e > que precisa aparecer literal\n")
d2 = open(out2, encoding="utf-8").read()
corpo = d2[d2.index("<body"):]
check("tag do .md não vira tag no deck", "<script>alert(1)</script>" not in corpo)
check("entidade escapada aparece", "&lt;script&gt;" in corpo)
check("& do título escapado no <title>", "Deck &amp; &lt;cia&gt;" in d2)


# ── tema e erros ───────────────────────────────────────────────────────────

print("\n[tema e erros — falha com a razão na mão]")

t = M.ler_tema("viu")
check("tema traz os 4 valores", all(t.values()) and "--font-head" in t["__THEME_CSS__"])
try:
    M.ler_tema("nao-existe")
    check("tema inexistente lista os que existem", False)
except M.DeckError as e:
    check("tema inexistente lista os que existem", "viu" in str(e))

with tempfile.TemporaryDirectory() as td:
    vazio = os.path.join(td, "vazio.md")
    with open(vazio, "w", encoding="utf-8") as fh:
        fh.write("só prosa, nenhum heading\n")
    try:
        M.build(vazio)
        check("md sem heading nenhum é recusado", False)
    except M.DeckError as e:
        check("md sem heading nenhum é recusado", "heading" in str(e))


# ── CLI ────────────────────────────────────────────────────────────────────

print("\n[CLI]")

src, out, pl, n = build_tmp()
r = subprocess.run([sys.executable, os.path.join(HERE, "md2deck.py"), src, "--plan"],
                   capture_output=True, text=True)
check("--plan devolve JSON com o componente de cada slide", r.returncode == 0
      and len(json.loads(r.stdout)) == N_HEADINGS, r.stderr[:200])
check("--plan não escreve nada",
      not os.path.exists(os.path.splitext(src)[0] + "-x.html"))

r = subprocess.run([sys.executable, os.path.join(HERE, "md2deck.py"), src,
                    "--out", os.path.join(os.path.dirname(src), "d.html")],
                   capture_output=True, text=True)
check("build sai 0 e imprime o caminho", r.returncode == 0 and "d.html" in r.stdout,
      (r.returncode, r.stderr[:200]))

r = subprocess.run([sys.executable, os.path.join(HERE, "md2deck.py"), src, "--tema", "xpto"],
                   capture_output=True, text=True)
check("tema inválido sai 2", r.returncode == 2 and "xpto" in r.stderr)


# ── o gate que a skill sempre rodou à mão ──────────────────────────────────

print("\n[fidelidade — o check_fidelity.py REAL, sobre o deck compilado]")

src, out, pl, n = build_tmp()
r = subprocess.run([sys.executable, CHECK_FID, out, src], capture_output=True, text=True)
check("deck compilado passa no check_fidelity sem nenhum trecho suspeito",
      r.returncode == 0, r.stdout[-600:])

# e a prova de que o checker não está cego: enfiar prosa que não existe na fonte reprova
with open(out, encoding="utf-8") as fh:
    sujo = fh.read().replace("</body>",
                             '<section class="slide"><div class="inner"><p>'
                             "Esta frase foi inventada pelo modelo e nao existe na fonte "
                             "de jeito nenhum</p></div></section></body>")
sujo_path = out.replace(".html", "-sujo.html")
with open(sujo_path, "w", encoding="utf-8") as fh:
    fh.write(sujo)
r = subprocess.run([sys.executable, CHECK_FID, sujo_path, src], capture_output=True, text=True)
check("o mesmo checker REPROVA prosa inventada (não passou por estar cego)",
      r.returncode == 1 and "inventada" in r.stdout, (r.returncode, r.stdout[-300:]))


print("\n%d passou · %d falhou" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
