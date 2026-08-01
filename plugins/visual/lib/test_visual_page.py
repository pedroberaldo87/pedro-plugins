#!/usr/bin/env python3
"""Suite do visual_page.py — stdlib, sem framework (padrão do repo).

O que estes testes protegem é o motivo do módulo existir: as regras de forma que
antes eram prosa na SKILL.md. Cada `check` abaixo corresponde a uma regra que já
falhou (ou falharia) quando dependia de o modelo lembrar.

    python3 plugins/visual/lib/test_visual_page.py
"""

import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import visual_page as V  # noqa: E402

PASS = FAIL = 0
HERE = os.path.dirname(os.path.abspath(__file__))


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


def tpl():
    with open(V.TEMPLATE, encoding="utf-8") as fh:
        return fh.read()


EVID = {"kind": "evidencia", "src": "wc -c arquivo", "output": "  1234 arquivo.html"}


def spec(**over):
    s = {
        "title": "Título da página",
        "ident": {"projeto": "pedro-plugins", "artefato": "A coisa visível", "estado": "gerado"},
        "sections": [{"title": "Seção", "blocks": [dict(EVID)]}],
    }
    s.update(over)
    return s


# ── validação ──────────────────────────────────────────────────────────────

print("\n[validação — o spec ruim é recusado, e recusado por inteiro]")

check("spec mínimo válido passa", V.validate(spec()) == [], V.validate(spec()))

errs = V.validate({"sections": []})
check("faltando title + ident + sections: acusa os três de uma vez",
      len(errs) >= 3 and any("title" in e for e in errs)
      and any("ident" in e for e in errs) and any("sections" in e for e in errs), errs)

errs = V.validate(spec(ident={"projeto": "x", "artefato": "y", "estado": "publicado"}))
check("estado fora do vocabulário é recusado", any("estado" in e for e in errs), errs)

# A regra "mostrar, não descrever", agora mecânica.
s = spec(sections=[{"title": "S", "blocks": [
    {"kind": "item", "title": "Um item pra decidir"}]}])
errs = V.validate(s)
check("item revisável SEM prova na página: RECUSADO",
      any("prova" in e for e in errs), errs)

s = spec(sections=[{"title": "S", "blocks": [
    dict(EVID), {"kind": "item", "title": "Um item pra decidir"}]}])
check("item + evidência com output: aceito", V.validate(s) == [], V.validate(s))

s = spec(sections=[{"title": "S", "blocks": [
    {"kind": "evidencia", "src": "cmd", "output": "   "},
    {"kind": "item", "title": "i"}]}])
errs = V.validate(s)
check("evidência só com espaço em branco NÃO conta como prova",
      any("prova" in e for e in errs), errs)

s = spec(sections=[{"title": "S", "blocks": [
    {"kind": "artefato", "src": "file:///tmp/x.html"},
    {"kind": "item", "title": "i"}]}])
check("artefato embutido conta como prova", V.validate(s) == [], V.validate(s))

errs = V.validate(spec(sections=[{"blocks": [{"kind": "evidencia", "output": "x"}]}]))
check("evidência sem src (procedência) é recusada", any("src" in e for e in errs), errs)

DEC2 = {"kind": "decision", "question": "Qual caminho?", "context": "O que está em jogo.",
        "options": [{"title": "A", "tradeoff": "✔ x · ✘ y"},
                    {"title": "B", "tradeoff": "✔ z · ✘ w"}]}

s = spec(sections=[{"blocks": [dict(EVID), dict(DEC2)]}])
check("decisão com 2 opções autorais é válida", V.validate(s) == [], V.validate(s))

d3 = dict(DEC2, options=DEC2["options"] + [{"title": "C", "tradeoff": "t"}])
errs = V.validate(spec(sections=[{"blocks": [dict(EVID), d3]}]))
check("decisão com 3 opções autorais é recusada (a 3ª é do programa)",
      any("EXATAMENTE 2" in e for e in errs), errs)

errs = V.validate(spec(sections=[{"blocks": [dict(EVID), dict(DEC2, context="")]}]))
check("decisão sem a linha de contexto é recusada", any("context" in e for e in errs), errs)

errs = V.validate(spec(sections=[{"blocks": [dict(
    EVID), {"kind": "decision", "question": "q", "context": "c",
            "options": [{"title": "A"}, {"title": "B", "tradeoff": "t"}]}]}]))
check("opção sem tradeoff (consequência) é recusada",
      any("tradeoff" in e for e in errs), errs)

errs = V.validate(spec(sections=[{"blocks": [
    {"kind": "tri", "problema": "p", "consequencia": "c"}]}]))
check("tri sem a proposta é recusado", any("proposta" in e for e in errs), errs)

errs = V.validate(spec(sections=[{"blocks": [{"kind": "inventado"}]}]))
check("kind desconhecido é recusado", any("desconhecido" in e for e in errs), errs)

errs = V.validate(spec(sections=[{"blocks": [
    {"kind": "chart", "rounds": [{"label": "R1", "p0": "3"}]}]}]))
check("chart com contagem em string é recusado (não coage silenciosamente)",
      any("inteiro" in e for e in errs), errs)

errs = V.validate(spec(item_labels=["só", "dois"]))
check("item_labels fora de 3 rótulos é recusado", any("item_labels" in e for e in errs), errs)


# ── as garantias estruturais ───────────────────────────────────────────────

print("\n[garantias estruturais — o que o programa torna impossível]")

T = tpl()
s = spec(sections=[{"title": "S", "blocks": [
    dict(EVID),
    {"kind": "item", "title": "Primeiro", "tri": {"problema": "p", "consequencia": "c",
                                                 "proposta": "s"}},
    {"kind": "item", "title": "Segundo"},
    {"kind": "item", "title": "Terceiro"}]}])
page, ctx = V.build_page(s, T)

inputs = re.findall(r"<input\b[^>]*>", page)
check("nenhum rádio nasce marcado",
      inputs and not any(re.search(r"\bchecked\b", i) for i in inputs), inputs[:2])
names = re.findall(r'<input type="radio" name="(fb-\d+)"', page)
check("um name de rádio por item, sem repetir entre itens",
      sorted(set(names)) == ["fb-1", "fb-2", "fb-3"] and len(names) == 9, names)
check("nenhum item nasce com classe state-*", not re.search(r'class="feedback-item[^"]*state-', page))
check("data-num numerado pelo programa",
      re.findall(r'class="feedback-item" data-num="(\d)"', page) == ["1", "2", "3"])
check("3 itens contados no ctx", ctx["n_items"] == 3, ctx)

check("feedback-box entra sozinha quando há item", 'class="feedback-box"' in page)
check("decisions-box NÃO entra quando não há decisão", 'class="decisions-box"' not in page)

s2 = spec(sections=[{"blocks": [dict(EVID), dict(DEC2), {"kind": "item", "title": "i"}]}])
page2, ctx2 = V.build_page(s2, T)
check("decisions-box entra sozinha quando há decisão", 'class="decisions-box"' in page2)
check("decisions-box vem ANTES da feedback-box",
      page2.index('class="decisions-box"') < page2.index('class="feedback-box"'))
check("a caixa de decisões trouxe o selo de live-sync (foi EXTRAÍDA do template)",
      'id="live-indicator"' in page2)
check("a caixa de fechamento trouxe o contador",
      'id="fb-done"' in page2 and 'id="fb-total"' in page2)

opts = re.findall(r'<div class="opt(?:\s[^"]*)?"', page2)
check("toda decisão sai com 3 opções", len(opts) == 3, opts)
check("a 3ª é a saída de emergência", 'class="opt opt-custom"' in page2)
check("a opção usa h3 — é onde o JS lê a escolha do usuário",
      page2.count("<h3>A</h3>") == 1 and page2.count("<h3>B</h3>") == 1)
check("o handler é o selectOpt real do template", 'onclick="selectOpt(this)"' in page2)
check("a decisão tem a linha de contexto", 'class="decision-context"' in page2)

check("token de sessão do live-sync injetado", "window.VISUAL_SESSION" in page2)
check("CSS e JS do template intactos",
      page2.count("function selectOpt") == 1 and page2.count("function onFbChange") == 1)


# ── escape ─────────────────────────────────────────────────────────────────

print("\n[escape — texto do modelo é prosa livre, nunca markup]")

s = spec(title='Um <script>alert(1)</script> & "aspas"',
         sections=[{"title": "S", "blocks": [
             {"kind": "evidencia", "src": "cmd <x>",
              "output": '<img onerror=alert(1)> & "isso é prova crua"'},
             {"kind": "item", "title": "Item <b>com</b> tag"}]}])
page, _ = V.build_page(s, T)
body = page[page.index("<h1>"):page.index('class="feedback-box"')]
check("tag no título vira texto", "<script>alert(1)</script>" not in body
      and "&lt;script&gt;" in body)
check("tag na saída crua vira texto", "<img onerror" not in body and "&lt;img" in body)
check("aspas escapadas no atributo data-title", 'data-title="Item' in page)
check("markdown mínimo funciona: `code` vira code.inline",
      '<code class="inline">' in V._rich("olha o `x` aqui"))
check("markdown mínimo funciona: **negrito** vira strong",
      "<strong>x</strong>" in V._rich("olha o **x** aqui"))
check("markdown não reabre tag escapada",
      V._rich("`<b>`") == '<code class="inline">&lt;b&gt;</code>', V._rich("`<b>`"))
check("highlight aplicado no texto JÁ escapado",
      "<mark>&lt;b&gt;</mark>" in "\n".join(
          V.r_evidencia({"src": "s", "output": "x <b> y", "highlight": "<b>"}, {})))


# ── a prova nasce fechada ──────────────────────────────────────────────────
#
# Saída crua de 30 linhas empurra a decisão pra fora da tela — e a página existe
# pra decidir, não pra ler log. Pedido do dono: "que eu possa abrir SE EU QUISER".

print("\n[evidência colapsável]")
_longa = "\n".join("linha %d" % i for i in range(30))
_h_longa = "\n".join(V.r_evidencia({"src": "cmd", "output": _longa}, {}))
check("prova longa nasce FECHADA", "<details class=\"evidencia\">" in _h_longa)
check("e não traz o atributo open", " open>" not in _h_longa)
check("a origem virou o que se clica", "<summary class=\"evidencia-src\">" in _h_longa)
check("mostra quantas linhas tem, fechada", "30 linhas" in _h_longa)

_h_curta = "\n".join(V.r_evidencia({"src": "cmd", "output": "1 linha só"}, {}))
check("prova curta nasce ABERTA (não empurra nada)", " open>" in _h_curta)

_h_forcada = "\n".join(V.r_evidencia({"src": "cmd", "output": _longa, "aberto": True}, {}))
check("'aberto: true' força a longa a abrir", " open>" in _h_forcada)

check("o conteúdo continua lá, fechado ou não", "linha 29" in _h_longa)
check("as classes que o CSS precisa são emitidas",
      "evidencia-conta" in _h_longa and "evidencia-chev" in _h_longa)


# ── rótulos relabelados (o /qa-loop) ───────────────────────────────────────

print("\n[relabel — o /qa-loop troca os rótulos, nunca os valores]")

s = spec(item_labels=["✓ Vira ação", "✏️ Ação c/ ajuste", "✗ Descartar"],
         sections=[{"blocks": [dict(EVID), {"kind": "item", "title": "achado"}]}])
page, _ = V.build_page(s, T)
check("rótulo visível troca", "✓ Vira ação" in page)
check("valor de máquina NÃO troca",
      'value="keep"' in page and 'value="change"' in page and 'value="remove"' in page)


# ── o gráfico ──────────────────────────────────────────────────────────────

print("\n[gráfico — aritmética de barra é do programa]")

rounds = [{"label": "R1", "p0": 2, "p1": 6, "p2": 4, "p3": 1},
          {"label": "R2", "p0": 0, "p1": 3, "p2": 5, "p3": 2},
          {"label": "R3", "p0": 0, "p1": 1, "p2": 2, "p3": 0}]
svg = "\n".join(V.r_chart({"rounds": rounds}, {}))
n_nao_zero = sum(1 for r in rounds for k in ("p0", "p1", "p2", "p3") if r.get(k, 0))
check("uma barra por severidade não-zero (nada de rect de altura 0)",
      svg.count("<rect") == n_nao_zero == 9, (svg.count("<rect"), n_nao_zero))
check("um rótulo por rodada",
      all(">%s</text>" % r["label"] in svg for r in rounds))
check("a linha de severidade real tem um ponto por rodada",
      svg.count("<circle") == 3)
ys = [float(m) for m in re.findall(r'<polyline[^>]*points="([^"]+)"', svg)[0]
      .replace(",", " ").split()[1::2]]
check("a linha DESCE quando P0+P1 cai (8 → 3 → 1)", ys[0] < ys[1] < ys[2], ys)
# altura por rodada = soma das barras que compartilham o mesmo x
por_x = {}
for x, h in re.findall(r'<rect x="([\d.]+)"[^>]*height="([\d.]+)"', svg):
    por_x[float(x)] = por_x.get(float(x), 0.0) + float(h)
alturas = [por_x[k] for k in sorted(por_x)]
tot = [sum(r.get(k, 0) for k in ("p0", "p1", "p2", "p3")) for r in rounds]
check("uma pilha por rodada", len(alturas) == len(rounds), (alturas, tot))
check("altura da pilha proporcional ao total da rodada",
      all(abs(alturas[i] / alturas[0] - tot[i] / float(tot[0])) < 0.01
          for i in range(len(rounds))), (alturas, tot))
check("rodada toda zerada não divide por zero",
      "<svg" in "\n".join(V.r_chart({"rounds": [{"label": "R1"}]}, {})))
check("chart conta como prova",
      V.validate(spec(sections=[{"blocks": [
          {"kind": "chart", "rounds": rounds}, {"kind": "item", "title": "i"}]}])) == [])


# ── a válvula e a extração ─────────────────────────────────────────────────

print("\n[válvula e extração]")

s = spec(sections=[{"blocks": [dict(EVID), {"kind": "raw_html",
                                            "html": '<div class="diagram">livre</div>'}]}])
page, _ = V.build_page(s, T)
check("raw_html passa sem escapar (é a válvula)", '<div class="diagram">livre</div>' in page)

try:
    V.extract_block("<html><body>nada aqui</body></html>", "decisions-box")
    check("extração levanta quando o bloco sumiu do template", False)
except V.SpecError as e:
    check("extração levanta quando o bloco sumiu do template", "decisions-box" in str(e))

check("extração balanceia divs aninhadas",
      V.extract_block('<div class="x"><div class="in"></div></div>tail', "x")
      == '<div class="x"><div class="in"></div></div>')


# ── CLI ────────────────────────────────────────────────────────────────────

print("\n[CLI — o caminho que a skill usa de verdade]")

with tempfile.TemporaryDirectory() as td:
    sp = os.path.join(td, "spec.json")
    out = os.path.join(td, "pagina.html")
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(spec(sections=[{"title": "S", "blocks": [
            dict(EVID), dict(DEC2), {"kind": "item", "title": "i"}]}]), fh)
    r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"),
                        "build", "--spec", sp, "--out", out],
                       capture_output=True, text=True)
    check("build sai 0 e imprime o caminho", r.returncode == 0 and out in r.stdout,
          (r.returncode, r.stdout, r.stderr))
    check("o arquivo saiu com a página inteira",
          os.path.exists(out) and os.path.getsize(out) > 40000, os.path.getsize(out)
          if os.path.exists(out) else "ausente")

    bad = os.path.join(td, "bad.json")
    with open(bad, "w", encoding="utf-8") as fh:
        json.dump({"title": "x", "ident": {"projeto": "p", "artefato": "a"},
                   "sections": [{"blocks": [{"kind": "item", "title": "i"}]}]}, fh)
    r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"),
                        "build", "--spec", bad, "--out", os.path.join(td, "x.html")],
                       capture_output=True, text=True)
    check("spec inválido sai 2 e explica no stderr",
          r.returncode == 2 and "prova" in r.stderr, (r.returncode, r.stderr))
    check("spec inválido NÃO escreve arquivo", not os.path.exists(os.path.join(td, "x.html")))

    with open(os.path.join(td, "notjson"), "w", encoding="utf-8") as fh:
        fh.write("{isso não é json")
    r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"),
                        "build", "--spec", os.path.join(td, "notjson")],
                       capture_output=True, text=True)
    check("JSON quebrado sai 2 com a linha do erro",
          r.returncode == 2 and "JSON inválido" in r.stderr, r.stderr)

r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"), "schema"],
                   capture_output=True, text=True)
check("schema imprime o contrato", r.returncode == 0 and "evidencia" in r.stdout
      and "RECUSADO PELO PROGRAMA" in r.stdout)


print("\n%d passou · %d falhou" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
