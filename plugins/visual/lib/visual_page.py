#!/usr/bin/env python3
"""Monta a página do /visual a partir de um SPEC JSON — o programa emite o HTML.

Por que existe (medido em 2026-07-29 neste repo): as páginas do /visual que não
eram plano vinham digitadas pelo modelo, 20-31 KB de HTML por página — algo entre
5 e 8 mil tokens de saída cada. A página de plano, emitida por `plan_state.py
page`, gasta zero: o programa escreve.

Isso é a extensão desse mesmo desenho para as outras páginas (decisão,
diagnóstico, relatório). O modelo escreve 2-4 KB de JSON; a forma é do programa.

E forma no programa não é só economia. Seis regras que viviam como prosa na
SKILL.md — e prosa apodrece: a cópia do bloco `.decisions-box` colada na skill JÁ
divergiu do template e quem a seguiu entregou página sem o selo de sync — passam
a ser impossíveis de violar:

  1. nenhum rádio nasce `checked` (pré-marcado nunca dispara onchange: parece
     escolhido e o contador lê 0)
  2. `name` de rádio único por item, numerado pelo programa
  3. `.decisions-box` sai sempre que existe `.decision-card`, e `.feedback-box`
     sempre que existe item revisável — as duas EXTRAÍDAS do template.html, nunca
     redigitadas aqui
  4. ordem fixa: decisions-box antes de feedback-box
  5. toda decisão tem exatamente 3 opções, a 3ª sempre a `.opt-custom`
  6. decisão/item sem nenhuma evidência crua na página é RECUSADO — a regra
     "mostrar, não descrever" deixa de depender de o modelo lembrar

Uso:
    python3 visual_page.py build --spec pagina.json [--out caminho.html]
    python3 visual_page.py schema          # o contrato do spec, pra consultar

stdlib only (requisito do repo).
"""

import argparse
import html
import json
import os
import random
import re
import string
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.normpath(os.path.join(HERE, "..", "skills", "visual", "template.html"))
RESOLVE_DIR = os.path.normpath(os.path.join(HERE, "..", "skills", "visual", "resolve-dir.sh"))

ESTADOS = ("rascunho", "gerado", "noar", "apresentado")
# Prova até este tamanho nasce ABERTA: são 6 linhas, cabem no olho sem empurrar a
# decisão pra fora da tela. Acima disso a página vira scroll de log — e ela existe
# pra decidir. Ver r_evidencia.
LINHAS_ABERTO = 6
SEV = {"high": "sev-high", "med": "sev-med", "low": "sev-low"}
DEFAULT_ITEM_LABELS = ["✓ Manter", "✏️ Mudar", "✗ Remover"]
CALLOUT_VARIANTS = ("info", "warn", "danger", "ok")


class SpecError(Exception):
    pass


# ── texto ──────────────────────────────────────────────────────────────────

def _e(s):
    return html.escape(str("" if s is None else s), quote=True)


def _rich(s):
    """Escapa e depois reabre um subconjunto mínimo de markdown.

    Só `code` e **negrito**. Existe pra o spec não precisar carregar tags HTML —
    se o modelo escrevesse HTML dentro do JSON, a gente teria trocado de sintaxe
    sem trocar de problema.
    """
    out = _e(s)
    out = re.sub(r"`([^`]+)`", r'<code class="inline">\1</code>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


# ── extração dos blocos canônicos do template ──────────────────────────────

def extract_block(tpl, cls):
    """Recorta `<div class="...cls...">…</div>` do template, balanceando divs.

    É EXTRAÍDO, não redigitado: foi uma cópia redigitada em prosa que divergiu do
    template e produziu página sem `.live-indicator`. Se a classe sumir do
    template, isso levanta — nunca emite a página sem a caixa.
    """
    m = re.search(r'<div class="[^"]*\b%s\b[^"]*">' % re.escape(cls), tpl)
    if not m:
        raise SpecError("bloco .%s não encontrado em %s — template mudou?" % (cls, TEMPLATE))
    start = m.start()
    depth = 0
    for tag in re.finditer(r"<div\b|</div>", tpl[start:]):
        depth += 1 if tag.group(0) != "</div>" else -1
        if depth == 0:
            return tpl[start:start + tag.end()]
    raise SpecError("bloco .%s não fecha no template" % cls)


# ── validação ──────────────────────────────────────────────────────────────

def validate(spec):
    """Devolve TODOS os erros de forma de uma vez (como o plan_state.validate)."""
    errs = []
    if not isinstance(spec, dict):
        return ["o spec tem que ser um objeto JSON"]

    for f in ("title", "sections"):
        if not spec.get(f):
            errs.append("campo obrigatório ausente: %s" % f)

    ident = spec.get("ident") or {}
    if not isinstance(ident, dict) or not ident.get("projeto") or not ident.get("artefato"):
        errs.append("ident.projeto e ident.artefato são obrigatórios — a faixa de "
                    "identidade responde 'de que se trata' antes da decisão")
    est = ident.get("estado", "gerado") if isinstance(ident, dict) else "gerado"
    if est not in ESTADOS:
        errs.append("ident.estado inválido: %r (use %s)" % (est, "|".join(ESTADOS)))

    kinds = []
    for si, sec in enumerate(spec.get("sections") or [], 1):
        if not isinstance(sec, dict):
            errs.append("seção %d não é objeto" % si)
            continue
        for bi, blk in enumerate(sec.get("blocks") or [], 1):
            where = "seção %d bloco %d" % (si, bi)
            if not isinstance(blk, dict) or not blk.get("kind"):
                errs.append("%s: sem 'kind'" % where)
                continue
            k = blk["kind"]
            kinds.append(k)
            errs.extend(_validate_block(k, blk, where))

    tem_pedido = "decision" in kinds or "item" in kinds
    tem_prova = any(
        b.get("kind") == "evidencia" and str(b.get("output") or "").strip()
        for sec in (spec.get("sections") or []) if isinstance(sec, dict)
        for b in (sec.get("blocks") or []) if isinstance(b, dict)
    ) or any(
        b.get("kind") in ("artefato", "chart")
        for sec in (spec.get("sections") or []) if isinstance(sec, dict)
        for b in (sec.get("blocks") or []) if isinstance(b, dict)
    )
    if tem_pedido and not tem_prova:
        errs.append("a página pede decisão/veredito mas não tem prova nenhuma "
                    "(nenhum bloco 'evidencia' com output, 'artefato' ou 'chart'). "
                    "Sem prova pra mostrar não há decisão a pedir — há investigação a fazer.")

    labels = spec.get("item_labels") or DEFAULT_ITEM_LABELS
    if not (isinstance(labels, list) and len(labels) == 3):
        errs.append("item_labels tem que ser uma lista de 3 rótulos (keep/change/remove)")
    return errs


def _validate_block(k, blk, where):
    errs = []
    if k == "evidencia":
        if not str(blk.get("output") or "").strip():
            errs.append("%s: evidencia sem 'output' — bloco de prova vazio não vai "
                        "pra página; cole a saída crua ou remova o bloco" % where)
        if not str(blk.get("src") or "").strip():
            errs.append("%s: evidencia sem 'src' (comando · arquivo · quando)" % where)
    elif k == "artefato":
        if not str(blk.get("src") or "").strip():
            errs.append("%s: artefato sem 'src' (caminho absoluto file:// ou data:)" % where)
    elif k == "tri":
        for f in ("problema", "consequencia", "proposta"):
            if not str(blk.get(f) or "").strip():
                errs.append("%s: tri sem '%s' — as três partes são obrigatórias" % (where, f))
    elif k == "item":
        if not str(blk.get("title") or "").strip():
            errs.append("%s: item sem 'title'" % where)
        if blk.get("sev") and blk["sev"] not in SEV:
            errs.append("%s: sev inválido %r (use high|med|low)" % (where, blk["sev"]))
        if blk.get("tri"):
            errs.extend(_validate_block("tri", blk["tri"], where + " (tri do item)"))
    elif k == "decision":
        if not str(blk.get("question") or "").strip():
            errs.append("%s: decision sem 'question'" % where)
        if not str(blk.get("context") or "").strip():
            errs.append("%s: decision sem 'context' — a linha que diz o que está "
                        "em jogo, em linguagem humana" % where)
        opts = blk.get("options") or []
        if len(opts) != 2:
            errs.append("%s: decision precisa de EXATAMENTE 2 opções — a 3ª "
                        "('Outra — eu especifico') é acrescentada pelo programa" % where)
        for oi, o in enumerate(opts, 1):
            if not isinstance(o, dict) or not str(o.get("title") or "").strip():
                errs.append("%s: opção %d sem 'title'" % (where, oi))
            elif not str(o.get("tradeoff") or "").strip():
                errs.append("%s: opção %d sem 'tradeoff' — a consequência de "
                            "escolher ela" % (where, oi))
    elif k == "chart":
        rounds = blk.get("rounds") or []
        if not rounds:
            errs.append("%s: chart sem 'rounds'" % where)
        for ri, r in enumerate(rounds, 1):
            if not isinstance(r, dict) or not str(r.get("label") or "").strip():
                errs.append("%s: rodada %d sem 'label'" % (where, ri))
                continue
            for key in ("p0", "p1", "p2", "p3"):
                v = r.get(key, 0)
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    errs.append("%s: rodada %s.%s tem que ser inteiro >= 0 (veio %r)"
                                % (where, r.get("label"), key, v))
    elif k == "callout":
        if blk.get("variant", "info") not in CALLOUT_VARIANTS:
            errs.append("%s: callout variant inválida %r (use %s)"
                        % (where, blk.get("variant"), "|".join(CALLOUT_VARIANTS)))
    elif k in ("text", "bullets", "raw_html"):
        pass
    else:
        errs.append("%s: kind desconhecido %r" % (where, k))
    return errs


# ── renderizadores de bloco ────────────────────────────────────────────────

def r_text(blk, ctx):
    cls = ' class="section-intro"' if blk.get("intro") else ""
    return ["  <p%s>%s</p>" % (cls, _rich(blk.get("text")))]


def r_bullets(blk, ctx):
    cls = "bullets problema" if blk.get("problema") else "bullets"
    out = ['  <ul class="%s">' % cls]
    out += ["    <li>%s</li>" % _rich(i) for i in (blk.get("items") or [])]
    out.append("  </ul>")
    return out


def r_evidencia(blk, ctx):
    """A prova NASCE FECHADA — a linha de origem é o que se clica pra abrir.

    O motivo é do dono: 'este tipo de artefato anexado é bem-vindo, mas o ideal é
    que seja algo colapsável que começa colapsado. que eu possa abrir SE EU QUISER'.
    Saída crua de 30 linhas empurra a decisão pra fora da tela — e a página existe
    pra decidir, não pra ler log.

    Duas exceções, as duas por segurança:
      - `aberto: true` no bloco — quem escreveu diz que ESTA prova é o ponto da página;
      - saída curta (≤ LINHAS_ABERTO), que não empurra nada.
    O bloco VAZIO continua aberto e gritando: esconder ausência de prova seria o
    oposto do que o componente existe pra fazer.
    """
    txt = _e(blk.get("output"))
    hl = blk.get("highlight")
    if hl:
        # <mark> na linha que decide — aplicado ao texto JÁ escapado
        txt = txt.replace(_e(hl), "<mark>%s</mark>" % _e(hl), 1)
    linhas = str(blk.get("output") or "").count("\n") + 1
    aberto = bool(blk.get("aberto")) or linhas <= LINHAS_ABERTO
    return ['  <details class="evidencia"%s>' % (" open" if aberto else ""),
            '    <summary class="evidencia-src">%s'
            '<span class="evidencia-conta">%d linhas</span>'
            '<span class="evidencia-chev">›</span></summary>'
            % (_rich(blk.get("src")), linhas),
            "    <pre>%s</pre>" % txt,
            "  </details>"]


def r_artefato(blk, ctx):
    src = str(blk.get("src"))
    inner = ('    <img src="%s" alt="%s">' % (_e(src), _e(blk.get("alt") or "artefato"))
             if src.startswith("data:image") or re.search(r"\.(png|jpe?g|gif|webp|svg)$", src, re.I)
             else '    <iframe src="%s" loading="lazy"></iframe>' % _e(src))
    return ['  <div class="artefato">',
            '    <div class="artefato-bar"><span>artefato real</span>'
            "<span>%s</span></div>" % _rich(blk.get("procedencia") or src),
            inner,
            "  </div>"]


def r_callout(blk, ctx):
    return ['  <div class="callout %s">%s</div>'
            % (_e(blk.get("variant", "info")), _rich(blk.get("text")))]


def _tri(t, indent="  "):
    return [
        '%s<div class="tri">' % indent,
        '%s  <div class="p"><span class="ic">🔴</span><span>'
        '<span class="lbl">O problema</span>%s</span></div>' % (indent, _rich(t.get("problema"))),
        '%s  <div class="c"><span class="ic">⚡</span><span>'
        '<span class="lbl">A consequência</span>%s</span></div>' % (indent, _rich(t.get("consequencia"))),
        '%s  <div class="s"><span class="ic">✅</span><span>'
        '<span class="lbl">A proposta</span>%s</span></div>' % (indent, _rich(t.get("proposta"))),
        "%s</div>" % indent,
    ]


def r_tri(blk, ctx):
    return _tri(blk)


def r_item(blk, ctx):
    """`.feedback-item` — o veredito mora NO item, nunca numa segunda tabela.

    A numeração e o `name` do rádio saem do contador do programa, então não há
    como dois itens compartilharem `name` (o bug em que marcar o #7 desmarcava
    o #3) e não há como um rádio nascer `checked`.
    """
    ctx["n_items"] += 1
    n = ctx["n_items"]
    lk, lc, lr = ctx["item_labels"]
    sev = (' <span class="sev %s">%s</span>'
           % (SEV[blk["sev"]], _e(blk.get("sev_label") or blk["sev"]))) if blk.get("sev") else ""
    out = ['  <div class="feedback-item" data-num="%d" data-title="%s">'
           % (n, _e(re.sub(r"<[^>]+>", "", _rich(blk.get("title"))))),
           '    <div class="feedback-head">',
           '      <span class="feedback-num">%d</span>' % n,
           '      <span class="feedback-title">%s%s</span>' % (_rich(blk.get("title")), sev),
           '      <div class="feedback-radios">']
    for val, lbl in (("keep", lk), ("change", lc), ("remove", lr)):
        out.append('        <label><input type="radio" name="fb-%d" value="%s" '
                   'onchange="onFbChange(this)"> %s</label>' % (n, val, _e(lbl)))
    out += ["      </div>", "    </div>"]
    if blk.get("tri"):
        out += _tri(blk["tri"], indent="    ")
    if blk.get("body"):
        out.append("    <p>%s</p>" % _rich(blk["body"]))
    det = blk.get("detail")
    if det:
        out += ['    <details class="item-detail">',
                '      <summary><span class="read-dot"></span> %s '
                '<span class="dchev">›</span></summary>' % _rich(det.get("summary") or "detalhes"),
                '      <div class="detail-body">']
        for p in (det.get("paragraphs") or []):
            out.append("        <p>%s</p>" % _rich(p))
        out += ["      </div>", "    </details>"]
    out.append('    <textarea class="feedback-textarea" placeholder="O que mudar..."></textarea>')
    out.append("  </div>")
    return out


# Handler e markup copiados do demo do template.html — `selectOpt` é o nome real da
# função, e `getDecisionSelections()` lê o título da escolha em `h3`. Emitir `h4`
# aqui faria a escolha do usuário chegar ao Claude como "Selecionado".
OPT_ATTRS = ('role="radio" tabindex="0" aria-checked="false" onclick="selectOpt(this)" '
             "onkeydown=\"if(event.key==='Enter'||event.key===' ')"
             '{event.preventDefault();selectOpt(this);}"')

CUSTOM_OPT = """      <div class="opt opt-custom" %s>
        <h3>Outra — eu especifico</h3>
        <p>Nenhuma das duas serve? Escreve a sua aqui.</p>
        <textarea class="opt-custom-input" placeholder="A minha alternativa é..."
                  onclick="event.stopPropagation()" onkeydown="event.stopPropagation()"></textarea>
      </div>""" % OPT_ATTRS


def r_decision(blk, ctx):
    """Bloco de decisão: 2 opções autorais + a 3ª sempre a saída de emergência."""
    ctx["n_decisions"] += 1
    out = ['  <div class="decision-card">',
           '    <div class="pill">⚡ Decisão %d</div>' % ctx["n_decisions"],
           '    <h3 class="decision-q">%s</h3>' % _rich(blk.get("question")),
           '    <p class="decision-context">%s</p>' % _rich(blk.get("context")),
           '    <div class="options" role="radiogroup">']
    for o in blk["options"]:
        cls = "opt recommended" if o.get("recommended") else "opt"
        out.append('      <div class="%s" %s>' % (cls, OPT_ATTRS))
        if o.get("svg"):
            out.append('        <span class="opt-illustration">%s</span>' % o["svg"])
        out += ["        <h3>%s</h3>" % _rich(o.get("title")),
                "        <p>%s</p>" % _rich(o.get("body") or o.get("tradeoff")),
                '        <div class="tradeoff">%s</div>' % _rich(o.get("tradeoff")),
                "      </div>"]
    out.append(CUSTOM_OPT)
    out += ["    </div>", "  </div>"]
    return out


def r_chart(blk, ctx):
    """Barras empilhadas P0-P3 por rodada + a linha de severidade real (P0+P1).

    Coordenada de barra é aritmética, não julgamento: barra fora de escala não dá
    erro, dá uma conclusão errada sobre retornos decrescentes — que é a única
    leitura pra qual este gráfico existe.
    """
    rounds = blk["rounds"]
    keys = ("p0", "p1", "p2", "p3")
    cores = {"p0": "var(--danger)", "p1": "var(--warn)",
             "p2": "var(--accent)", "p3": "var(--text-dim)"}
    totals = [sum(int(r.get(k, 0)) for k in keys) for r in rounds]
    top = max(totals + [1])

    W, H = 720, 280
    pad_l, pad_b, pad_t, pad_r = 44, 40, 16, 12
    plot_w, plot_h = W - pad_l - pad_r, H - pad_t - pad_b
    step = plot_w / float(len(rounds))
    bar_w = min(56.0, step * 0.6)

    def y(v):
        return pad_t + plot_h - (plot_h * v / float(top))

    out = ['  <div class="diagram">',
           '    <svg viewBox="0 0 %d %d" role="img" aria-label="findings por severidade '
           'por rodada" style="width:100%%;height:auto">' % (W, H)]
    # eixo + grade
    for frac in (0.0, 0.5, 1.0):
        gv = top * frac
        out.append('      <line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="currentColor" '
                   'stroke-opacity="0.16" stroke-width="1"/>' % (pad_l, y(gv), W - pad_r, y(gv)))
        out.append('      <text x="%d" y="%.1f" font-size="11" fill="currentColor" '
                   'fill-opacity="0.55" text-anchor="end">%d</text>'
                   % (pad_l - 6, y(gv) + 4, int(round(gv))))
    # barras
    pts = []
    for i, r in enumerate(rounds):
        cx = pad_l + step * i + step / 2.0
        x = cx - bar_w / 2.0
        acc = 0
        for k in keys:
            v = int(r.get(k, 0))
            if v:
                h = plot_h * v / float(top)
                out.append('      <rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                           'fill="%s" fill-opacity="0.85" rx="2"><title>%s %s: %d</title></rect>'
                           % (x, y(acc + v), bar_w, h, cores[k], _e(r["label"]), k.upper(), v))
            acc += v
        pts.append((cx, y(int(r.get("p0", 0)) + int(r.get("p1", 0)))))
        out.append('      <text x="%.1f" y="%d" font-size="12" fill="currentColor" '
                   'fill-opacity="0.7" text-anchor="middle">%s</text>'
                   % (cx, H - pad_b + 18, _e(r["label"])))
    # linha de severidade real
    out.append('      <polyline fill="none" stroke="var(--accent)" stroke-width="2" '
               'points="%s"/>' % " ".join("%.1f,%.1f" % p for p in pts))
    for cx, cy in pts:
        out.append('      <circle cx="%.1f" cy="%.1f" r="3.5" fill="var(--accent)"/>' % (cx, cy))
    out.append("    </svg>")
    legenda = " · ".join("<strong>%s</strong>" % k.upper() for k in keys)
    out.append('    <p class="cap">%s empilhados · linha = severidade real (P0+P1)%s</p>'
               % (legenda, " · " + _rich(blk["title"]) if blk.get("title") else ""))
    out.append("  </div>")
    return out


def r_raw_html(blk, ctx):
    """A válvula. Página excepcional (layout novo, SVG sob medida) não pode ficar
    impossível só porque o spec não previu — senão a gente troca token por
    engessamento."""
    return ["  " + str(blk.get("html") or "")]


RENDERERS = {"text": r_text, "bullets": r_bullets, "evidencia": r_evidencia,
             "artefato": r_artefato, "callout": r_callout, "tri": r_tri, "item": r_item,
             "decision": r_decision, "chart": r_chart, "raw_html": r_raw_html}


# ── a página ───────────────────────────────────────────────────────────────

def build_body(spec, tpl):
    ctx = {"n_items": 0, "n_decisions": 0,
           "item_labels": spec.get("item_labels") or DEFAULT_ITEM_LABELS}
    ident = spec.get("ident") or {}
    out = ['<div class="wrap">', '  <div class="ident-strip">']
    for k, label in (("projeto", "Projeto"), ("artefato", "Artefato"), ("gerado_de", "Gerado de")):
        if ident.get(k):
            v = ("<code class=\"inline\">%s</code>" % _e(ident[k])) if k == "gerado_de" else _e(ident[k])
            out.append('    <span><span class="ik">%s</span><span class="iv">%s</span></span>'
                       % (label, v))
    out.append('    <span class="estado estado-%s">%s</span>'
               % (_e(ident.get("estado", "gerado")), _e(ident.get("estado", "gerado"))))
    out.append("  </div>")

    if spec.get("kicker"):
        out.append('  <div class="pill">%s</div>' % _rich(spec["kicker"]))
    out.append("  <h1>%s</h1>" % _rich(spec["title"]))
    if spec.get("subtitle"):
        out.append('  <p class="subtitle">%s</p>' % _rich(spec["subtitle"]))
    if spec.get("chips"):
        out.append('  <div class="meta-chips">')
        for i, c in enumerate(spec["chips"]):
            out.append('    <span class="chip%s">%s</span>'
                       % (" primary" if i == 0 and spec.get("chip_primary") else "", _rich(c)))
        out.append("  </div>")
    if spec.get("tldr"):
        out += ['  <div class="tldr">', '    <span class="tldr-emoji">%s</span>'
                % _e(spec.get("tldr_emoji") or "🎯"),
                "    <div>%s</div>" % _rich(spec["tldr"]), "  </div>"]

    for i, sec in enumerate(spec["sections"], 1):
        out.append("  <section>")
        if sec.get("title"):
            out += ['    <div class="section-head"><span class="section-num">%d</span>'
                    "<h2>%s</h2></div>" % (i, _rich(sec["title"]))]
        for blk in (sec.get("blocks") or []):
            out += RENDERERS[blk["kind"]](blk, ctx)
        out.append("  </section>")

    if spec.get("exec"):
        out.append('  <div class="exec">')
        out.append("    <h2>📋 %s</h2>" % _rich(spec.get("exec_title") or "Sumário"))
        for i, it in enumerate(spec["exec"], 1):
            out += ['    <div class="exec-item">',
                    '      <h4><span class="elabel">%d ·</span> %s</h4>' % (i, _rich(it.get("title")))]
            for key, lbl in (("como", "🔧 Como"), ("porque", "💡 Por quê"), ("toca", "📁 Toca em")):
                if it.get(key):
                    out.append('      <div class="label-row"><span class="lk">%s</span>'
                               '<span class="lv">%s</span></div>' % (lbl, _rich(it[key])))
            if it.get("text"):
                out.append("      <p>%s</p>" % _rich(it["text"]))
            out.append("    </div>")
        out.append("  </div>")

    # As duas caixas: sempre extraídas do template, nesta ordem.
    if ctx["n_decisions"]:
        out.append(extract_block(tpl, "decisions-box"))
    if ctx["n_items"]:
        out.append(extract_block(tpl, "feedback-box"))
    out.append("</div>")
    return "\n".join(out) + "\n", ctx


def build_page(spec, tpl=None):
    errs = validate(spec)
    if errs:
        raise SpecError("spec inválido:\n  - " + "\n  - ".join(errs))
    if tpl is None:
        if not os.path.exists(TEMPLATE):
            raise SpecError("template.html não encontrado em %s" % TEMPLATE)
        with open(TEMPLATE, encoding="utf-8") as fh:
            tpl = fh.read()
    body, ctx = build_body(spec, tpl)
    token = spec.get("session") or "%s-%s" % (
        time.strftime("%Y%m%d%H%M"),
        "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6)))
    i = tpl.index("<body>")
    j = tpl.index("<script>", i)
    page = (tpl[:i] + '<body>\n<script>window.VISUAL_SESSION = "%s";</script>\n' % token
            + body + tpl[j:])
    page = re.sub(r"<title>.*?</title>",
                  "<title>%s</title>" % _e(spec.get("doc_title") or
                                           re.sub(r"<[^>]+>", "", _rich(spec["title"]))),
                  page, count=1, flags=re.S)
    return page, ctx


def default_out(spec):
    slug = spec.get("slug") or re.sub(r"[^a-z0-9]+", "-",
                                      str(spec["title"]).lower()).strip("-")[:48] or "visual"
    r = subprocess.run(["bash", RESOLVE_DIR, os.getcwd()], capture_output=True, text=True)
    d = (r.stdout or "").strip()
    if not d:
        raise SpecError("não consegui resolver o diretório do /visual — passe --out")
    return os.path.join(d, "%s-%s.html" % (time.strftime("%Y-%m-%d"), slug))


def cmd_build(args):
    raw = sys.stdin.read() if args.spec == "-" else open(args.spec, encoding="utf-8").read()
    try:
        spec = json.loads(raw)
    except ValueError as e:
        raise SpecError("JSON inválido: %s" % e)
    page, ctx = build_page(spec)
    out = args.out or default_out(spec)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(out)
    sys.stderr.write("✅ %d bytes · %d itens revisáveis · %d decisões\n"
                     % (len(page), ctx["n_items"], ctx["n_decisions"]))
    return 0


def cmd_schema(args):
    print(SCHEMA_DOC)
    return 0


SCHEMA_DOC = """\
SPEC do /visual — o modelo escreve ISTO, o programa escreve o HTML.

{
  "slug": "decisao-cache",                  # opcional; entra no nome do arquivo
  "title": "O h1 da página",
  "doc_title": "…",                         # opcional; default = title (vai no <title>)
  "subtitle": "uma linha",
  "kicker": "🔍 Auditoria · 3 achados",      # opcional (.pill)
  "chips": ["📄 12 arquivos", "⏱ 4 min"],    # opcional
  "chip_primary": true,                      # destaca o 1º chip
  "tldr": "a frase que resolve a página",   # opcional
  "tldr_emoji": "🎯",
  "ident": {                                 # OBRIGATÓRIO
    "projeto": "pedro-plugins",
    "artefato": "o nome VISÍVEL da coisa (nunca id interno)",
    "gerado_de": "comando ou origem",        # opcional
    "estado": "rascunho|gerado|noar|apresentado"
  },
  "item_labels": ["✓ Manter", "✏️ Mudar", "✗ Remover"],   # relabel (ex: "✓ Vira ação")
  "sections": [ { "title": "…", "blocks": [ … ] } ],
  "exec": [ {"title": "…", "como": "…", "porque": "…", "toca": "…"} ],
  "exec_title": "Sumário"
}

BLOCOS (campo "kind"):
  text       {"text": "prosa. aceita `code` e **negrito**", "intro": false}
  bullets    {"items": ["…"], "problema": false}
  evidencia  {"src": "comando · projeto · quando", "output": "a saída CRUA",
              "highlight": "trecho que decide"}          ← output vazio é RECUSADO
  artefato   {"src": "file:///abs ou data:image/...", "procedencia": "…", "alt": "…"}
  callout    {"variant": "info|warn|danger|ok", "text": "…"}
  tri        {"problema": "…", "consequencia": "…", "proposta": "…"}
  item       {"title": "…", "sev": "high|med|low", "sev_label": "…",
              "tri": {…}, "body": "…",
              "detail": {"summary": "…", "paragraphs": ["…"]}}
  decision   {"question": "…", "context": "o que está em jogo, humano",
              "options": [{"title": "…", "body": "o que é a opção",
                           "tradeoff": "✔ … · ✘ a consequência",
                           "svg": "<svg viewBox='0 0 100 60'…>",   # opcional, ilustra
                           "recommended": true}, {…}]}    ← EXATAMENTE 2; a 3ª é automática
  chart      {"title": "…", "rounds": [{"label": "R1", "p0": 2, "p1": 5, "p2": 8, "p3": 3}]}
  raw_html   {"html": "<…>"}                              ← a válvula; use pouco

GARANTIDO PELO PROGRAMA (não escreva à mão, não precisa lembrar):
  faixa de identidade · numeração e name único dos rádios · nenhum rádio pré-marcado ·
  .decisions-box quando há decisão · .feedback-box quando há item · a ordem das duas ·
  a 3ª opção "Outra — eu especifico" · escape de todo texto · token de sessão do live-sync
RECUSADO PELO PROGRAMA:
  decisão/veredito sem nenhuma prova na página · bloco de evidência vazio ·
  decisão com 2 ou 4 opções · tri incompleto
"""


def main(argv=None):
    p = argparse.ArgumentParser(prog="visual_page.py", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("build", help="monta a página a partir do spec e imprime o caminho")
    q.add_argument("--spec", default="-", help="arquivo JSON, ou - pra stdin")
    q.add_argument("--out", help="caminho de saída (default: cascata do /visual)")
    q.set_defaults(fn=cmd_build)
    q = sub.add_parser("schema", help="imprime o contrato do spec")
    q.set_defaults(fn=cmd_schema)
    args = p.parse_args(argv)
    try:
        return args.fn(args)
    except SpecError as e:
        sys.stderr.write("⛔ %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
