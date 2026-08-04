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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regua_texto import (BULLET_MAX, BULLETS_MAX, _cru, bullets_de,  # noqa: E402,F401
                         erros_de_estilo as _erros_de_estilo)

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.normpath(os.path.join(HERE, "..", "skills", "visual", "template.html"))
RESOLVE_DIR = os.path.normpath(os.path.join(HERE, "..", "skills", "visual", "resolve-dir.sh"))

ESTADOS = ("rascunho", "gerado", "noar", "apresentado")
SEV = {"high": "sev-high", "med": "sev-med", "low": "sev-low"}
DEFAULT_ITEM_LABELS = ["✓ Manter", "✏️ Mudar", "✗ Remover"]
CALLOUT_VARIANTS = ("info", "warn", "danger", "ok")

# ── a régua de estilo (quality-goals.md, regime "informação rápida") ────────
# Página gerada é lida com pressa: prosa é PROIBIDA, bullets são a forma. As quatro
# checagens moram em `_shared/regua_texto.py` desde 2026-08-03, porque os outros
# geradores (plano, slide, texto de hook) emitem texto para o mesmo leitor apressado
# e cada um estava livre para inventar a própria forma. O que este gerador faz aqui é
# DECLARAR qual perfil ele usa.
PERFIL = "pagina"


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


def _plural(n, s, p=None):
    """Mesma assinatura do `plan_state._plural` — o texto que o dono lê concorda."""
    return "%d %s" % (n, s if n == 1 else (p or s + "s"))


def erros_de_estilo(v, onde):
    """A régua no perfil DESTE gerador — a definição mora em `regua_texto.py`.

    Fora do alcance de propósito: `evidencia.output` (saída crua é literal por
    obrigação) e `raw_html`. Ver quality-goals.md, "A régua de estilo".
    """
    return _erros_de_estilo(v, onde, PERFIL)


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

    # A régua vale para TODO texto da página, inclusive o que não mora em bloco.
    for f in ("title", "subtitle", "tldr", "kicker"):
        if spec.get(f):
            errs.extend(erros_de_estilo(spec.get(f), "spec.%s" % f))
    for ei, it in enumerate(spec.get("exec") or [], 1):
        if isinstance(it, dict):
            for f in ("title", "como", "porque", "toca", "text"):
                if it.get(f):
                    errs.extend(erros_de_estilo(it.get(f), "exec %d %s" % (ei, f)))

    kinds = []
    for si, sec in enumerate(spec.get("sections") or [], 1):
        if not isinstance(sec, dict):
            errs.append("seção %d não é objeto" % si)
            continue
        if sec.get("title"):
            errs.extend(erros_de_estilo(sec.get("title"), "seção %d título" % si))
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
        for f in ("procedencia", "alt"):
            if blk.get(f):
                errs.extend(erros_de_estilo(blk.get(f), "%s: artefato.%s" % (where, f)))
    elif k == "tri":
        # Colapsar não é amputar: consequência e proposta ficam atrás do clique, mas
        # continuam OBRIGATÓRIAS. O gate só mudou de lugar, não de exigência.
        for f in ("problema", "consequencia", "proposta"):
            if not bullets_de(blk.get(f)):
                errs.append("%s: tri sem '%s' — as três partes são obrigatórias" % (where, f))
            errs.extend(erros_de_estilo(blk.get(f), "%s: tri.%s" % (where, f)))
    elif k == "item":
        if not str(blk.get("title") or "").strip():
            errs.append("%s: item sem 'title'" % where)
        errs.extend(erros_de_estilo(blk.get("title"), "%s: item.title" % where))
        for f in ("body", "paragraphs"):
            if blk.get(f):
                errs.extend(erros_de_estilo(blk.get(f), "%s: item.%s" % (where, f)))
        det = blk.get("detail") or {}
        if isinstance(det, dict):
            for f in ("summary", "paragraphs"):
                if det.get(f):
                    errs.extend(erros_de_estilo(det.get(f), "%s: detail.%s" % (where, f)))
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
        for f in ("question", "context"):
            errs.extend(erros_de_estilo(blk.get(f), "%s: decision.%s" % (where, f)))
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
            if isinstance(o, dict):
                for f in ("title", "body", "tradeoff"):
                    if o.get(f):
                        errs.extend(erros_de_estilo(o.get(f), "%s: opção %d %s"
                                                    % (where, oi, f)))
    elif k == "chart":
        if blk.get("title"):
            errs.extend(erros_de_estilo(blk.get("title"), "%s: chart.title" % where))
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
        errs.extend(erros_de_estilo(blk.get("text"), "%s: callout.text" % where))
    elif k == "text":
        errs.extend(erros_de_estilo(blk.get("text"), "%s: text" % where))
    elif k == "bullets":
        errs.extend(erros_de_estilo(blk.get("items") or [], "%s: bullets" % where))
    elif k == "raw_html":
        # Válvula declarada: layout excepcional. Fora da régua de propósito.
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

    **Sem exceção por tamanho desde 2026-08-02.** A antiga `LINHAS_ABERTO = 6`
    deixava prova curta nascer aberta, e o dono contou na tela quatro blocos
    abertos (4, 1, 6 e 3 linhas) que não pediu pra ver. "Isso é pequeno, não
    atrapalha" é a exceção que sempre volta.

    Sobrou uma válvula, e ela só abre: `aberto: true` no bloco, pra quando ESTA
    prova é o ponto da página. Fechar não tem válvula — seria onde esconder.
    Bloco vazio não chega aqui: o validador recusa evidência sem `output`.
    """
    txt = _e(blk.get("output"))
    hl = blk.get("highlight")
    if hl:
        # <mark> na linha que decide — aplicado ao texto JÁ escapado
        txt = txt.replace(_e(hl), "<mark>%s</mark>" % _e(hl), 1)
    linhas = str(blk.get("output") or "").count("\n") + 1
    return ['  <details class="evidencia"%s>' % (" open" if blk.get("aberto") else ""),
            '    <summary class="evidencia-src">%s'
            '<span class="evidencia-conta">%s</span>'
            '<span class="evidencia-chev">›</span></summary>'
            % (_rich(blk.get("src")), _plural(linhas, "linha")),
            "    <pre>%s</pre>" % txt,
            "  </details>"]


def r_artefato(blk, ctx):
    """O artefato real, encolhido no fluxo do documento — com saída para ver grande.

    Pequeno é a escolha certa no meio da página: artefato em tamanho natural quebra
    a leitura e empurra a decisão pra fora da tela. O que faltava era a SAÍDA. Dois
    botões, porque resolvem coisas diferentes: **tela cheia** é ler agora sem perder
    o lugar na página; **nova janela** é deixar aberto e comparar com o resto.

    A nova janela é `<a target="_blank">`, não `window.open()`: bloqueador de popup
    mata o segundo e não o primeiro, e a página é aberta em `file://`, onde a
    política é mais restritiva ainda.
    """
    src = str(blk.get("src"))
    inner = ('    <img src="%s" alt="%s">' % (_e(src), _e(blk.get("alt") or "artefato"))
             if src.startswith("data:image") or re.search(r"\.(png|jpe?g|gif|webp|svg)$", src, re.I)
             else '    <iframe src="%s" loading="lazy"></iframe>' % _e(src))
    return ['  <div class="artefato">',
            '    <div class="artefato-bar"><span class="real">artefato real</span>'
            "<span>%s</span>" % _rich(blk.get("procedencia") or src),
            '      <span class="art-acoes">'
            '<button type="button" onclick="artefatoTelaCheia(this)" '
            'title="Ver em tela cheia (Esc volta)">⛶ tela cheia</button>'
            '<a class="art-btn" href="%s" target="_blank" rel="noopener" '
            'title="Abrir numa janela nova">↗ nova janela</a></span>' % _e(src),
            "    </div>",
            inner,
            "  </div>"]


def r_callout(blk, ctx):
    return ['  <div class="callout %s">%s</div>'
            % (_e(blk.get("variant", "info")), _rich(blk.get("text")))]


def _tri_parte(cls, icone, rotulo, bullets, indent):
    """Uma das três partes. Um bullet só sai como linha; vários saem como lista."""
    corpo = ("<ul class=\"tri-bullets\">%s</ul>"
             % "".join("<li>%s</li>" % _rich(b) for b in bullets)
             if len(bullets) > 1 else _rich(bullets[0] if bullets else ""))
    return ('%s<div class="%s"><span class="ic">%s</span><span>'
            '<span class="lbl">%s</span>%s</span></div>'
            % (indent, cls, icone, rotulo, corpo))


def _tri(t, indent="  ", sev=None, mostra_problema=True):
    """O problema fica VISÍVEL; consequência e proposta nascem fechadas.

    Por que assim (quality-goals.md): a régua antiga mandava as três partes ficarem
    fora do `<details>` pra impedir que um problema fosse escondido — e o efeito foi
    obrigar toda seção de bloqueio a nascer aberta (89% do último relatório vinha
    exposto de cara). O invariante que importava sobrevive: **a posição é do
    programa, não de quem escreve**. O que mudou foi qual é a posição.

    O rótulo do que está fechado é DERIVADO do conteúdo, nunca escrito à parte.
    Ele promove o primeiro impacto — o texto real que está lá dentro, já sujeito
    à régua de estilo — e conta quanto sobrou. Duas propriedades de uma vez:

      - **denuncia**: o rótulo fala DESTE problema, não da categoria dele.
        "o que isso causa" era a mesma etiqueta em todo bloco da página, e uma
        etiqueta que não muda não ajuda ninguém a decidir se abre.
      - **não esconde**: como é promoção de conteúdo, e não campo separado, não
        existe onde amaciar. Rótulo livre seria o novo lugar de esconder — um
        problema grave viraria "impacto pontual" e ninguém abriria.

    A palavra "detalhes" não aparece: não denuncia nada. Nome de campo do schema
    ("consequência", "proposta") também não vaza pra superfície fechada.

    `sev` colore a régua lateral do card (high=danger, med=warn, low=roxo);
    vem do próprio tri ou é herdado do item que o embute.
    """
    cons = bullets_de(t.get("consequencia"))
    prop = bullets_de(t.get("proposta"))
    prob = bullets_de(t.get("problema"))
    sev = t.get("sev") or sev
    cls = "tri tri-%s" % sev if sev in SEV else "tri"

    # O rótulo promove o primeiro impacto e conta o que sobrou.
    lede = cons[0] if cons else (prop[0] if prop else "")
    resto = max(0, len(cons) - 1)
    mais = "+%d &nbsp;·&nbsp; como resolver" % resto if resto else "como resolver"

    return [
        '%s<div class="%s">' % (indent, cls),
        ] + ([_tri_parte("p", "🔴", "O problema", prob, indent + "  ")]
             if mostra_problema else []) + [
        '%s  <details class="item-detail tri-fold">' % indent,
        '%s    <summary><span class="read-dot"></span>'
        '<span class="fold-lede">⚡ %s</span>'
        '<span class="fold-mais">%s</span>'
        '<span class="dchev">›</span></summary>' % (indent, _rich(lede), mais),
        _tri_parte("c", "⚡", "A consequência", cons, indent + "    "),
        _tri_parte("s", "✅", "A proposta", prop, indent + "    "),
        "%s  </details>" % indent,
        "%s</div>" % indent,
    ]


def r_tri(blk, ctx):
    """Tri solto com veredito inline: aceitar/ajustar/recusar + comentário.

    Um bloqueio sobre o qual se decide não é informação — é um item de decisão.
    Mesmo contrato do `item` (radios fb-N + onFbChange + textarea), para o JS de
    feedback e o copy funcionarem. O problema vira o título do feedback-head, e o
    corpo do tri não o repete (`mostra_problema=False`).
    """
    ctx["n_items"] += 1
    n = ctx["n_items"]
    lk, lc, lr = ctx["item_labels"]
    prob = bullets_de(blk.get("problema"))
    titulo = re.sub(r"<[^>]+>", "", _rich(prob[0])) if prob else "Bloqueio"
    sev = blk.get("sev")
    sev_html = (' <span class="sev %s">%s</span>'
                % (SEV[sev], _e(blk.get("sev_label") or sev))) if sev in SEV else ""
    out = ['  <div class="feedback-item" data-num="%d" data-title="%s">'
           % (n, _e(titulo)),
           '    <div class="feedback-head">',
           '      <span class="feedback-num">%d</span>' % n,
           '      <span class="feedback-title">%s%s</span>' % (_rich(titulo), sev_html),
           '      <div class="feedback-radios">']
    for val, lbl in (("keep", lk), ("change", lc), ("remove", lr)):
        out.append('        <label><input type="radio" name="fb-%d" value="%s" '
                   'onchange="onFbChange(this)"> %s</label>' % (n, val, _e(lbl)))
    out += ["      </div>", "    </div>"]
    out += _tri(blk, indent="    ", sev=sev, mostra_problema=False)
    out.append('    <textarea class="feedback-textarea" placeholder="O que mudar..."></textarea>')
    out.append("  </div>")
    return out


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
        out += _tri(blk["tri"], indent="    ", sev=blk.get("sev"))
    corpo = bullets_de(blk.get("body"))
    if len(corpo) > 1:
        out.append('    <ul class="tri-bullets">%s</ul>'
                   % "".join("<li>%s</li>" % _rich(b) for b in corpo))
    elif corpo:
        out.append("    <p>%s</p>" % _rich(corpo[0]))
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
        <p>Nenhuma das duas serve — escreve a sua aqui.</p>
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

def _placar(spec):
    """Contagem agregada, sempre aberta, computada do próprio conteúdo.

    Com o corpo dos bloqueios atrás de um clique, precisa existir uma superfície que
    o programa escreve e o redator não: quantos problemas a página carrega. Esconder
    um passa a exigir omiti-lo do spec inteiro — que é um vetor mais caro e visível
    do que rebaixá-lo pra dentro de um `<details>`.
    """
    tris = 0
    sevs = {"high": 0, "med": 0, "low": 0}
    for sec in (spec.get("sections") or []):
        if not isinstance(sec, dict):
            continue
        for b in (sec.get("blocks") or []):
            if not isinstance(b, dict):
                continue
            if b.get("kind") == "tri" or (b.get("kind") == "item" and b.get("tri")):
                tris += 1
                if b.get("sev") in sevs:
                    sevs[b["sev"]] += 1
    if not tris:
        return []
    partes = ["<strong>%s</strong> apontado%s" % (_plural(tris, "problema"),
                                                  "" if tris == 1 else "s")]
    graves = sevs["high"]
    if graves:
        partes.append("<strong>%s</strong>" % _plural(graves, "grave"))
    partes.append("corpo de cada um a um clique" if tris > 1 else "o corpo a um clique")
    return ['  <div class="callout warn">%s</div>' % " · ".join(partes)]


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
    out += _placar(spec)

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

A RÉGUA DE ESTILO — vale para TODO campo de texto abaixo (prosa é proibida):
  ≤ 140 caracteres por bullet (marcação não conta) · uma frase por bullet ·
  não abra bullet com "e/mas/que/porque/então/ou seja/além disso" · máx. 6 por bloco
  FORA da régua: evidencia.output (prova é literal) e raw_html (a válvula)
  Estourar não é aviso: sai 2 e NÃO escreve a página. O teto manda quebrar em
  bullets, nunca encolher a informação.

BLOCOS (campo "kind"):
  text       {"text": "uma frase. aceita `code` e **negrito**", "intro": false}
  bullets    {"items": ["…"], "problema": false}
  evidencia  {"src": "comando · projeto · quando", "output": "a saída CRUA",
              "highlight": "trecho que decide"}          ← output vazio é RECUSADO
  artefato   {"src": "file:///abs ou data:image/...", "procedencia": "…", "alt": "…"}
  callout    {"variant": "info|warn|danger|ok", "text": "…"}
  tri        {"problema": "uma linha — fica VISÍVEL",
              "consequencia": ["bullet", "bullet"],    ← nasce FECHADA
              "proposta":     ["bullet"],              ← nasce FECHADA
              "sev": "high|med|low"}                   ← opcional; colore a régua do card
             o rótulo do dobrador é fixo, do programa ("⚡ o que isso causa · ✅ como resolver")
  item       {"title": "que tipo de coisa aconteceu + a providência, 1 linha",
              "sev": "high|med|low", "sev_label": "…",
              "tri": {…}, "body": "…" ou ["bullet", "bullet"],
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
  a 3ª opção "Outra — eu especifico" · escape de todo texto · token de sessão do live-sync ·
  o dobrador do tri e seu rótulo derivado · o placar de problemas no topo ·
  os botões de tela cheia e janela nova na barra do artefato
RECUSADO PELO PROGRAMA:
  decisão/veredito sem nenhuma prova na página · bloco de evidência vazio ·
  decisão com 2 ou 4 opções · tri incompleto · prosa em qualquer campo de texto
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
