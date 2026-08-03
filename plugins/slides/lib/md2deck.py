#!/usr/bin/env python3
"""Compila um .md em deck HTML — modo A (transcrição) do /slides.

Por que existe: a regra de ouro do modo A é "o texto é do autor, use literal, nunca
invente". Isso não é julgamento, é tradução mecânica — e até aqui era o modelo que
traduzia, digitando cada `<section class="slide">`, com o `check_fidelity.py` conferindo
DEPOIS se ele tinha obedecido. Pagava-se o deck em tokens, mais um passe pra descobrir
se o primeiro mentiu, mais um terceiro quando o checker acusava.

Aqui a fidelidade é **propriedade da construção**: todo texto de corpo sai dos tokens do
.md, escapado, sem passar por geração. As ÚNICAS strings que este programa inventa são
enumeradores (`01`, `02`) e o eyebrow derivado dos headings — e o `check_fidelity.py`
isenta título e rótulo de propósito, porque derivar título de heading é licença explícita
da skill.

O que continua sendo julgamento do modelo: qual componente cada slide usa e onde quebrar
por densidade. Isso entra por `--anota`, um JSON pequeno — não por HTML.

Fluxo:
    python3 md2deck.py fonte.md --plan            # o plano: slide a slide, componente escolhido
    python3 md2deck.py fonte.md --anota a.json    # recompila com as correções de componente
    python3 check_fidelity.py deck.html fonte.md  # a rede, agora redundante por construção

stdlib only (requisito do repo).
"""

import argparse
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from regua_texto import erros_de_estilo as _erros_de_estilo  # noqa: E402

SKILL = os.path.normpath(os.path.join(HERE, "..", "skills", "slides"))
TEMPLATE = os.path.join(SKILL, "assets", "template.html")
THEMES = os.path.join(SKILL, "references", "themes")

MAX_ITEMS = 6          # acima disso, quebra em outro slide (regra de densidade da skill)
STATEMENT_WORDS = 20   # parágrafo curto e solto vira frase de impacto

# A régua de estilo (quality-goals.md, regime "informação rápida"), no perfil que é
# do slide: 140 caracteres cabem numa página e não cabem numa linha lida de longe,
# então quem decide é o teto de palavras. Ela RECUSA o deck — não existe perfil
# frouxo. O programa continua sem reescrever o texto do autor: ele devolve o .md
# com os motivos, e quem corrige a frase é quem a escreveu.
PERFIL = "slide"
REVEAL = (40, 130, 210, 290, 370, 450, 530, 610)

COMPONENTES = ("cover", "divider", "numlist", "idx", "feats", "statement",
               "metric", "pull", "cols")


class DeckError(Exception):
    pass


# ── inline markdown → html (subconjunto fechado) ───────────────────────────

def inline(s):
    """Escapa e reabre só **negrito**, *itálico*, `código` e [link](url).

    Nada aqui cria ou remove palavra — é a mesma frase do .md com marcação.
    """
    out = html.escape(s, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", out)
    return out


def txt(s):
    """Só o texto, sem marcação — pra contar palavras e casar anotação."""
    return re.sub(r"\s+", " ", re.sub(r"[*`]", "", s)).strip()


# ── parse do .md ───────────────────────────────────────────────────────────

def parse_md(src):
    """Devolve a lista de blocos: headings, bullets e parágrafos, na ordem.

    Deliberadamente simples: heading ATX, bullet de um nível, parágrafo. Bloco de
    código e tabela viram parágrafo literal — nunca são reescritos.
    """
    blocos = []
    fence = None
    buf = []

    def flush():
        if buf:
            blocos.append({"t": "p", "text": " ".join(buf).strip()})
            del buf[:]

    for linha in src.splitlines():
        if fence is not None:
            if linha.strip().startswith(fence):
                blocos.append({"t": "code", "text": "\n".join(buf)})
                del buf[:]
                fence = None
            else:
                buf.append(linha)
            continue
        m = re.match(r"^(```+|~~~+)", linha.strip())
        if m:
            flush()
            fence = m.group(1)[:3]
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if m:
            flush()
            blocos.append({"t": "h", "level": len(m.group(1)), "text": m.group(2).strip()})
            continue
        m = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$", linha)
        if m:
            flush()
            blocos.append({"t": "li", "text": m.group(1).strip()})
            continue
        if not linha.strip():
            flush()
            continue
        if re.match(r"^\s*(\|.*\||-{3,}|={3,})\s*$", linha):
            flush()
            continue                      # separador / linha de tabela: não é fala do autor
        buf.append(linha.strip())
    flush()
    if fence is not None:
        blocos.append({"t": "code", "text": "\n".join(buf)})
    return blocos


# ── agrupamento em slides ──────────────────────────────────────────────────

def agrupar(blocos):
    """Um slide por heading. `#` é seção; `##`/`###` é slide de conteúdo."""
    slides = []
    secao = None
    atual = None
    for b in blocos:
        if b["t"] == "h":
            if atual:
                slides.append(atual)
            if b["level"] == 1:
                secao = b["text"]
                atual = {"h": b["text"], "level": 1, "secao": secao, "corpo": [], "subs": []}
            else:
                atual = {"h": b["text"], "level": b["level"], "secao": secao,
                         "corpo": [], "subs": []}
            continue
        if atual is None:
            atual = {"h": None, "level": 0, "secao": None, "corpo": [], "subs": []}
        atual["corpo"].append(b)
    if atual:
        slides.append(atual)
    return [s for s in slides if s["h"] or s["corpo"]]


PAR_RE = re.compile(r"\s+[—–]\s+|:\s+")


def escolher(slide, i):
    """A regra de escolha, do mapa 'tipo de conteúdo → componente' da skill.

    Errar aqui não estraga o deck — o `--plan` mostra a escolha e o `--anota` a
    corrige. O que não pode errar é o TEXTO, e esse não passa por escolha nenhuma.
    """
    lis = [b for b in slide["corpo"] if b["t"] == "li"]
    ps = [b for b in slide["corpo"] if b["t"] == "p"]
    if slide["level"] == 1:
        return "cover" if i == 0 else "divider"
    if not lis and not ps:
        return "divider"
    if not lis and len(ps) == 1:
        if re.search(r"\d[\d.,]*\s*(?:→|->|=>)\s*\d", txt(ps[0]["text"])):
            return "metric"
        return "statement" if len(txt(ps[0]["text"]).split()) <= STATEMENT_WORDS else "pull"
    if lis:
        if 2 <= len(lis) <= 3 and all(re.match(r"^\*\*[^*]+\*\*", b["text"]) for b in lis):
            return "feats"
        if 3 <= len(lis) <= 8 and all(PAR_RE.search(txt(b["text"])) for b in lis):
            return "idx"
        return "numlist"
    return "pull"


def erros_de_estilo(v, onde):
    """A régua no perfil DESTE gerador — a definição mora em `regua_texto.py`."""
    return _erros_de_estilo(v, onde, PERFIL)


def desvios_de_estilo(pl):
    """O que no deck não cabe num slide, medido — uma linha por desvio.

    Devolve em vez de levantar para poder ser testado. Quem recusa é o `build`.
    """
    desvios = []
    for p in pl:
        onde = p["heading"] or "slide %d" % p["i"]
        for pedaco in p["_pedacos"]:
            desvios += erros_de_estilo([txt(b["text"]) for b in pedaco], onde)
        for b in p["_slide"]["corpo"]:
            if b["t"] == "p":
                desvios += erros_de_estilo(txt(b["text"]), "%s: parágrafo" % onde)
    return desvios


def plano(slides, anota):
    out = []
    for i, s in enumerate(slides):
        a = anota.get(s["h"] or "", {})
        comp = a.get("component") or escolher(s, i)
        if comp not in COMPONENTES:
            raise DeckError("componente %r não existe (anotação de %r). Existem: %s"
                            % (comp, s["h"], ", ".join(COMPONENTES)))
        lis = [b for b in s["corpo"] if b["t"] == "li"]
        limite = int(a.get("split") or MAX_ITEMS)
        pedacos = [lis[k:k + limite] for k in range(0, len(lis), limite)] or [[]]
        out.append({"i": i, "heading": s["h"], "level": s["level"], "secao": s["secao"],
                    "component": comp, "itens": len(lis),
                    "slides_gerados": len(pedacos), "hl": a.get("hl"),
                    "_slide": s, "_pedacos": pedacos})
    return out


# ── emissão ────────────────────────────────────────────────────────────────

def titulo_html(texto, hl):
    """O título, com uma palavra pintada se a anotação pedir. Não muda o texto."""
    out = inline(texto)
    if hl:
        alvo = html.escape(hl, quote=False)
        if alvo in out:
            out = out.replace(alvo, '<span class="hl">%s</span>' % alvo, 1)
    return out


def eyebrow(p, k=0):
    """`Seção · Subseção` — a navegação mental, derivada dos headings."""
    if not p["secao"] or p["secao"] == p["heading"]:
        return ""
    return ('    <div class="eyebrow reveal" style="--d:%dms">'
            '<span class="ln"></span> %s</div>'
            % (REVEAL[min(k, len(REVEAL) - 1)], inline(p["secao"])))


def emitir(p, seq, num_secao):
    """Emite as `<section class="slide">` de um item do plano."""
    comp = p["component"]
    s = p["_slide"]
    ps = [b for b in s["corpo"] if b["t"] == "p"]
    codes = [b for b in s["corpo"] if b["t"] == "code"]
    saida = []

    if comp == "cover":
        linhas = ['<section class="slide cover"><div class="inner">']
        if s["secao"]:
            linhas.append('    <div class="kicker reveal" style="--d:60ms">'
                          '<span class="d"></span> %s</div>' % inline(s["secao"]))
        linhas.append('    <h1 class="reveal" style="--d:150ms">%s</h1>'
                      % titulo_html(p["heading"] or "", p["hl"]))
        itens = [b for b in s["corpo"] if b["t"] == "li"]
        if itens or ps:
            linhas.append('    <div class="kvs reveal" style="--d:320ms">')
            for b in (itens or ps):
                t = b["text"]
                m = PAR_RE.split(txt(t), 1)
                if len(m) == 2:
                    linhas.append('      <span class="kv"><span class="kn">%s</span> %s</span>'
                                  % (inline(m[0]), inline(m[1])))
                else:
                    linhas.append('      <span class="kv">%s</span>' % inline(t))
            linhas.append("    </div>")
        linhas.append("</div></section>")
        return ["\n".join(linhas)]

    if comp == "divider":
        linhas = ['<section class="slide"><div class="inner">',
                  '    <div class="section-num reveal" style="--d:40ms">%02d</div>' % num_secao]
        if s["secao"] and s["secao"] != p["heading"]:
            linhas.append('    <div class="eyebrow reveal" style="--d:130ms">'
                          '<span class="ln"></span> %s</div>' % inline(s["secao"]))
        linhas.append('    <h2 class="title reveal" style="--d:210ms">%s</h2>'
                      % titulo_html(p["heading"] or "", p["hl"]))
        for b in ps[:1]:
            linhas.append('    <div class="lead reveal" style="--d:290ms">%s</div>'
                          % inline(b["text"]))
        linhas.append("</div></section>")
        return ["\n".join(linhas)]

    for n, pedaco in enumerate(p["_pedacos"]):
        linhas = ['<section class="slide"><div class="inner">']
        eb = eyebrow(p, 0)
        if eb:
            linhas.append(eb)
        if p["heading"]:
            linhas.append('    <h2 class="title reveal" style="--d:130ms">%s</h2>'
                          % titulo_html(p["heading"], p["hl"]))
        k = 2
        # parágrafos só no primeiro pedaço — repetir seria duplicar a fala do autor
        if n == 0:
            for b in ps:
                cls = "statement" if comp == "statement" else ("pull" if comp == "pull" else "lead")
                if comp == "metric":
                    m = re.search(r"([\d.,]+\S*)\s*(?:→|->|=>)\s*([\d.,]+\S*)", txt(b["text"]))
                    if m:
                        resto = txt(b["text"])[m.end():].strip(" .·—–")
                        linhas.append('    <div class="metric reveal" style="--d:%dms">'
                                      '<span class="from">%s</span>'
                                      '<span class="arr"><i class="fa-solid fa-arrow-right-long">'
                                      '</i></span><span class="to">%s</span>'
                                      % (REVEAL[k], inline(m.group(1)), inline(m.group(2))))
                        if resto:
                            linhas.append('      <span class="unit">%s</span>' % inline(resto))
                        linhas.append("    </div>")
                        k += 1
                        continue
                linhas.append('    <div class="%s reveal" style="--d:%dms">%s</div>'
                              % (cls, REVEAL[min(k, len(REVEAL) - 1)], inline(b["text"])))
                k += 1
        if pedaco:
            if comp == "idx":
                linhas.append('    <div class="idx reveal" style="--d:%dms">'
                              % REVEAL[min(k, len(REVEAL) - 1)])
                for j, b in enumerate(pedaco, 1):
                    partes = PAR_RE.split(b["text"], 1)
                    nome, ex = (partes + [""])[:2]
                    linhas.append('      <div class="row"><span class="n">%02d</span>'
                                  '<span class="name">%s</span><span class="ex">%s</span></div>'
                                  % (j + n * len(pedaco), inline(nome.strip()), inline(ex.strip())))
                linhas.append("    </div>")
            elif comp == "feats":
                linhas.append('    <div class="feats f%d mt">' % min(max(len(pedaco), 2), 3))
                for j, b in enumerate(pedaco):
                    m = re.match(r"^\*\*([^*]+)\*\*\s*(.*)$", b["text"])
                    tit, resto = (m.group(1), m.group(2)) if m else (b["text"], "")
                    linhas.append('      <div class="feat reveal" style="--d:%dms">'
                                  % REVEAL[min(k + j, len(REVEAL) - 1)])
                    linhas.append("        <h3>%s</h3>" % inline(tit.strip()))
                    if resto.strip(" —–:"):
                        linhas.append("        <p>%s</p>" % inline(resto.strip(" —–:")))
                    linhas.append("      </div>")
                linhas.append("    </div>")
            else:
                linhas.append('    <ul class="numlist reveal" style="--d:%dms">'
                              % REVEAL[min(k, len(REVEAL) - 1)])
                for j, b in enumerate(pedaco, 1):
                    partes = PAR_RE.split(b["text"], 1)
                    if len(partes) == 2 and len(txt(partes[1]).split()) <= 12:
                        corpo = "%s <small>%s</small>" % (inline(partes[0].strip()),
                                                          inline(partes[1].strip()))
                    else:
                        corpo = inline(b["text"])
                    linhas.append('      <li><span class="nn">%02d</span>'
                                  '<span class="tx">%s</span></li>'
                                  % (j + n * MAX_ITEMS, corpo))
                linhas.append("    </ul>")
        if n == 0:
            for b in codes:
                linhas.append('    <div class="def reveal" style="--d:%dms"><pre>%s</pre></div>'
                              % (REVEAL[min(k + 1, len(REVEAL) - 1)],
                                 html.escape(b["text"], quote=False)))
        linhas.append("</div></section>")
        saida.append("\n".join(linhas))
    return saida


# ── tema ───────────────────────────────────────────────────────────────────

def ler_tema(nome):
    path = os.path.join(THEMES, "%s.md" % nome)
    if not os.path.exists(path):
        disp = sorted(f[:-3] for f in os.listdir(THEMES) if f.endswith(".md"))
        raise DeckError("tema %r não existe. Existem: %s" % (nome, ", ".join(disp)))
    src = open(path, encoding="utf-8").read()

    def fence(placeholder):
        m = re.search(r"##\s+`%s`\s*\n+```[a-z]*\n(.*?)```" % re.escape(placeholder), src, re.S)
        return m.group(1).rstrip() if m else None

    def valor(placeholder):
        m = re.search(r"##\s+`%s`\s*\n+`([^`]+)`" % re.escape(placeholder), src)
        return m.group(1).strip() if m else None

    t = {"__FONT_LINKS__": fence("__FONT_LINKS__"), "__THEME_CSS__": fence("__THEME_CSS__"),
         "__BRAND__": valor("__BRAND__"), "__THEME_COLOR__": valor("__THEME_COLOR__")}
    falta = [k for k, v in t.items() if not v]
    if falta:
        raise DeckError("tema %r não define: %s (veja 'Como criar um tema novo' em %s)"
                        % (nome, ", ".join(falta), path))
    return t


# ── build ──────────────────────────────────────────────────────────────────

def build(md_path, tema="viu", anota=None, out=None):
    src = open(md_path, encoding="utf-8").read()
    blocos = parse_md(src)
    if not any(b["t"] == "h" for b in blocos):
        raise DeckError("nenhum heading em %s — o deck sai do esqueleto de headings do "
                        ".md (`#` vira seção, `##`/`###` vira slide). Sem heading não há "
                        "onde cortar os slides, e cortar por conta própria seria inventar "
                        "estrutura que o autor não escreveu." % md_path)
    slides = agrupar(blocos)
    pl = plano(slides, anota or {})
    # A régua recusa o deck em vez de avisar: aviso no stderr sai junto do caminho
    # do HTML, e ninguém volta pra corrigir uma frase de um comando que deu certo.
    desvios = desvios_de_estilo(pl)
    if desvios:
        raise DeckError("deck recusado pela régua de estilo:\n  - "
                        + "\n  - ".join(desvios))

    secoes = 0
    html_slides = []
    seq = 0
    for p in pl:
        if p["component"] == "divider":
            secoes += 1
        for bloco in emitir(p, seq, secoes):
            html_slides.append(bloco)
            seq += 1

    t = ler_tema(tema)
    if not os.path.exists(TEMPLATE):
        raise DeckError("template não encontrado em %s" % TEMPLATE)
    page = open(TEMPLATE, encoding="utf-8").read()

    titulo = txt(pl[0]["heading"] or os.path.basename(md_path))
    primeiro_p = next((txt(b["text"]) for s in slides for b in s["corpo"] if b["t"] == "p"), "")
    subs = {"__TITLE__": html.escape(titulo, quote=True),
            "__OG_DESC__": html.escape(primeiro_p[:180], quote=True),
            "__SLIDES__": "\n\n".join(html_slides)}
    subs.update(t)

    # O template DOCUMENTA dois placeholders dentro de comentários:
    #   <!-- __FONT_LINKS__ : injected by the theme … -->
    #   /* __THEME_CSS__ : the theme's :root block … */
    # Substituir dentro deles é o bug que deixou o deck branco: o `:root{…}` caía
    # dentro do `/* */`, e o primeiro `*/` do PRÓPRIO tema (`/* fonts */`) fechava o
    # comentário no meio, matando a paleta e as fontes inteiras. O HTML não reclama —
    # só sai sem estilo. Some com os comentários ANTES de substituir.
    page = re.sub(r"[ \t]*<!--\s*__FONT_LINKS__\s*:.*?-->\n?", "", page, flags=re.S)
    page = re.sub(r"[ \t]*/\*\s*__THEME_CSS__\s*:.*?\*/\n?", "", page, flags=re.S)

    for k, v in subs.items():
        page = page.replace(k, v)
    sobrou = re.findall(r"__[A-Z_]+__", page)
    if sobrou:
        raise DeckError("placeholder não substituído: %s" % ", ".join(sorted(set(sobrou))))
    # o tema tem que valer DE VERDADE: fora de comentário, dentro do <style>
    estilo = "\n".join(re.findall(r"<style>(.*?)</style>", page, re.S))
    sem_comentario = re.sub(r"/\*.*?\*/", "", estilo, flags=re.S)
    if ":root" not in sem_comentario or "--bg-body" not in sem_comentario:
        raise DeckError("o CSS do tema não ficou ativo (caiu dentro de comentário?) — "
                        "o deck sairia sem paleta e sem fonte")

    if out is None:
        out = os.path.splitext(md_path)[0] + ".html"
    try:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(page)
    except OSError as e:
        alt = os.path.join(os.path.expanduser("~/Desktop"),
                           os.path.basename(os.path.splitext(md_path)[0]) + ".html")
        sys.stderr.write("⚠️  não deu pra escrever em %s (%s) — caindo pro Desktop\n" % (out, e))
        with open(alt, "w", encoding="utf-8") as fh:
            fh.write(page)
        out = alt
    return out, pl, seq


def main(argv=None):
    ap = argparse.ArgumentParser(prog="md2deck.py", description=__doc__.split("\n")[0])
    ap.add_argument("fonte", help="o .md de origem")
    ap.add_argument("--tema", default="viu")
    ap.add_argument("--out", help="destino (default: ao lado do .md, mesmo nome-base)")
    ap.add_argument("--anota", help="JSON de anotação por heading "
                                    '{"Heading": {"component": "...", "hl": "...", "split": N}}')
    ap.add_argument("--plan", action="store_true",
                    help="só imprime o plano em JSON (slide a slide) e sai")
    args = ap.parse_args(argv)

    try:
        anota = json.load(open(args.anota, encoding="utf-8")) if args.anota else {}
        if args.plan:
            slides = agrupar(parse_md(open(args.fonte, encoding="utf-8").read()))
            pl = plano(slides, anota)
            print(json.dumps([{k: v for k, v in p.items() if not k.startswith("_")}
                              for p in pl], ensure_ascii=False, indent=2))
            return 0
        out, pl, n = build(args.fonte, args.tema, anota, args.out)
        print(out)
        sys.stderr.write("✅ %d slides de %d headings · tema %s\n" % (n, len(pl), args.tema))
        return 0
    except DeckError as e:
        sys.stderr.write("⛔ %s\n" % e)
        return 2
    except (OSError, ValueError) as e:
        sys.stderr.write("⛔ %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
