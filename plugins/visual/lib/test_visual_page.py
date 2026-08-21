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

_h_curta = "\n".join(V.r_evidencia({"src": "cmd", "output": "só uma linha"}, {}))
check("prova CURTA também nasce fechada — sem exceção por tamanho",
      " open>" not in _h_curta, _h_curta)
check("o plural concorda em 1 linha", "1 linha<" in _h_curta and "1 linhas" not in _h_curta,
      _h_curta)

_h_seis = "\n".join(V.r_evidencia({"src": "cmd", "output": "\n".join("l%d" % i for i in range(6))}, {}))
check("6 linhas (o antigo limite) já não abre nada", " open>" not in _h_seis)

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


# ── a página do parecer (F25.2) ────────────────────────────────────────────

print("\n[parecer — aprovável sozinho, item a item, sem item do trabalho]")

_par = spec(slug="parecer-decisao-cache",
            sections=[{"blocks": [dict(EVID),
                                  {"kind": "item", "title": "a 1ª escolha perdeu o juiz"},
                                  {"kind": "item", "title": "a 2ª escolha ele entendeu"}]}])
check("spec do parecer é válido", V.validate(_par) == [], V.validate(_par))
_pag, _ctx = V.build_page(_par, T)
check("o parecer sai com rótulo de aprovação", "✓ Aprovar" in _pag and "✗ Reprovar" in _pag)
check("rótulo de manter/mudar não aparece no parecer", "✓ Manter" not in _pag)
check("cada apontamento tem veredito próprio",
      _ctx["n_items"] == 2 and 'name="fb-1"' in _pag and 'name="fb-2"' in _pag)
check("o rótulo do parecer manda mesmo se o spec pedir outro",
      "✓ Aprovar" in V.build_page(dict(_par, item_labels=["✓ Manter", "a", "b"]), T)[0])

for _intruso in ({"kind": "aprovacao", "etapa": "a spec", "doc_integral": "texto inteiro"},
                 {"kind": "decision", "question": "qual cache?", "context": "o que está em jogo",
                  "options": [{"title": "A", "tradeoff": "custa mais"},
                              {"title": "B", "tradeoff": "custa menos"}]}):
    _errs = V.validate(spec(slug="parecer-x",
                         sections=[{"blocks": [dict(EVID), _intruso]}]))
    check("item do trabalho (%s) é recusado no parecer" % _intruso["kind"],
          any("página de parecer" in e for e in _errs), _errs)
_errs = V.validate(spec(sections=[{"blocks": [
    {"kind": "esquema", "tipo": "glossario",
     "termos": [{"termo": "gate", "desc": "o passo que recusa o commit"}]},
    dict(EVID), {"kind": "aprovacao", "etapa": "a spec",
                 "doc_integral": "texto inteiro"}]}]))
check("fora do parecer a aprovação continua passando", _errs == [], _errs)


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
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
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
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    check("spec inválido sai 2 e explica no stderr",
          r.returncode == 2 and "prova" in r.stderr, (r.returncode, r.stderr))
    check("spec inválido NÃO escreve arquivo", not os.path.exists(os.path.join(td, "x.html")))

    with open(os.path.join(td, "notjson"), "w", encoding="utf-8") as fh:
        fh.write("{isso não é json")
    r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"),
                        "build", "--spec", os.path.join(td, "notjson")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    check("JSON quebrado sai 2 com a linha do erro",
          r.returncode == 2 and "JSON inválido" in r.stderr, r.stderr)

r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"), "schema"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
check("schema imprime o contrato", r.returncode == 0 and "evidencia" in r.stdout
      and "RECUSADO PELO PROGRAMA" in r.stdout)


# ── a régua de estilo: prosa é proibida em página gerada ───────────────────
# O caso que originou tudo: o bloco real do relatório de 2026-08-01, que o dono não
# conseguiu ler. Ver quality-goals.md, "Trade-off já decidido por esta ordem".
print("\n[régua de estilo — prosa proibida]")

PROSA_REAL = ("Das cinco decisões que vazaram na sessão de ontem, quatro nasceram no meio "
              "da implementação — e nenhum campo do plano as teria capturado, porque elas "
              "não existiam quando o plano foi escrito. O que foi construído hoje resolve "
              "a decisão que o autor do plano JÁ SABIA que existia.")

check("a régua vem de FORA — o módulo compartilhado, não uma cópia daqui",
      V.erros_de_estilo.__module__ == "visual_page"
      and V._erros_de_estilo.__module__ == "regua_texto", V._erros_de_estilo.__module__)
check("este gerador DECLARA o perfil que usa", V.PERFIL == "pagina", V.PERFIL)

e = V.erros_de_estilo(PROSA_REAL, "x")
check("o textão real do relatório é REPROVADO", len(e) >= 2, e)
check("reprova por tamanho", any("caracteres" in x for x in e), e)
check("reprova por duas frases", any("duas frases" in x for x in e), e)

check("bullet de 140 passa", V.erros_de_estilo("a" * 140, "x") == [])
check("bullet de 141 reprova", len(V.erros_de_estilo("a" * 141, "x")) == 1)
check("marcação não conta no teto",
      V.erros_de_estilo("`%s`" % ("a" * 140), "x") == [])
check("duas frases no mesmo bullet reprovam",
      any("duas frases" in x for x in V.erros_de_estilo("Rodei a suite. Passou tudo.", "x")))
check("uma frase que termina em ponto NÃO reprova",
      V.erros_de_estilo("Rodei a suite e passou tudo.", "x") == [])
check("reticências não viram duas frases",
      V.erros_de_estilo("o gate desligou... e ninguém viu", "x") == [])
check("decimal não vira duas frases",
      V.erros_de_estilo("são 1.500 itens no plano", "x") == [])
check("`arquivo.py` no meio não vira duas frases",
      V.erros_de_estilo("o `plan_state.py` grava o arquivo", "x") == [])
check("bullet que abre com conectivo reprova",
      any("conectivo" in x for x in V.erros_de_estilo(["ok", "e por isso o gate caiu"], "x")))
check("7 bullets reprovam (teto 6)",
      any("teto é 6" in x for x in V.erros_de_estilo(["b%d" % i for i in range(7)], "x")))
check("6 bullets passam", V.erros_de_estilo(["b%d" % i for i in range(6)], "x") == [])
check("o erro diz QUAL bullet",
      any("bullet 2" in x for x in V.erros_de_estilo(["ok", "a" * 200], "x")))

# a régua tem que morder em TODO campo, não só na consequência
CAMPOS = [
    ({"kind": "text", "text": "a" * 200}, "text"),
    ({"kind": "bullets", "items": ["a" * 200]}, "bullets"),
    ({"kind": "callout", "text": "a" * 200}, "callout"),
    ({"kind": "item", "title": "a" * 200}, "item.title"),
    ({"kind": "item", "title": "ok", "body": "a" * 200}, "item.body"),
    ({"kind": "artefato", "src": "file:///x.png", "procedencia": "a" * 200}, "artefato"),
]
for blk, nome in CAMPOS:
    errs = V._validate_block(blk["kind"], blk, "s1 b1")
    check("a régua morde em %s" % nome, any("caracteres" in x for x in errs), errs)

d = {"kind": "decision", "question": "a" * 200, "context": "ok",
     "options": [{"title": "A", "tradeoff": "b" * 200}, {"title": "B", "tradeoff": "ok"}]}
errs = V._validate_block("decision", d, "s1 b1")
check("a régua morde na pergunta da decisão", any("decision.question" in x for x in errs), errs)
check("a régua morde no tradeoff da opção", any("opção 1 tradeoff" in x for x in errs), errs)

check("prova crua fica FORA da régua (é literal por obrigação)",
      V._validate_block("evidencia", {"kind": "evidencia", "src": "cmd",
                                      "output": "x" * 900}, "s1 b1") == [])
check("raw_html fica fora da régua (é a válvula)",
      V._validate_block("raw_html", {"kind": "raw_html", "html": "<p>%s</p>" % ("a" * 300)},
                        "s1 b1") == [])


# ── o dobrador do tri: colapsa sem esconder ────────────────────────────────
print("\n[tri — o problema fica; consequência e proposta dobram]")

TRI = {"kind": "tri", "problema": "O gate de bump não cobrava a forma do comando",
       "consequencia": ["7 de 9 commits passaram sem bump", "ninguém foi avisado"],
       "proposta": ["tokenizar o comando e ler o subcomando do git"]}
html_tri = "\n".join(V._tri(TRI))

check("o problema fica FORA do details",
      html_tri.index('class="p"') < html_tri.index("<details"), html_tri[:200])
check("consequência fica DENTRO do details",
      html_tri.index("<details") < html_tri.index('class="c"'))
check("proposta fica DENTRO do details",
      html_tri.index("<details") < html_tri.index('class="s"'))
check("o details nasce FECHADO (sem `open`)", "<details class=\"item-detail tri-fold\">" in html_tri)
check("o rótulo promove o primeiro impacto, não uma etiqueta de categoria",
      "7 de 9 commits passaram sem bump" in html_tri and "o que isso causa" not in html_tri,
      html_tri)
check("o rótulo conta o que sobrou dentro", "+1" in html_tri, html_tri)
check("o rótulo diz que o conserto está lá dentro", "como resolver" in html_tri)

_um_só = V._tri({"problema": "p", "consequencia": ["única"], "proposta": ["x"]})
_s1 = next(ln for ln in _um_só if "<summary>" in ln)
check("com uma consequência só, não sai '+0'", "+0" not in _s1, _s1)
check("o rótulo é DERIVADO: muda quando o conteúdo muda",
      "única" in _s1 and "7 de 9 commits" not in _s1, _s1)
_summary_tri = next(ln for ln in V._tri(TRI) if "<summary>" in ln)
check("nome de campo do schema não vaza pro rótulo fechado",
      "consequência" not in _summary_tri and "proposta" not in _summary_tri, _summary_tri)
check("a contagem de bullets saiu do rótulo (ocupava espaço sem informar)",
      "2 bullets" not in html_tri and "1 bullet" not in html_tri)
check("a palavra 'detalhes' não aparece (não denuncia nada)", "detalhes" not in html_tri)
check("sem sev o card sai neutro", 'class="tri">' in html_tri, html_tri[:80])
check("sev no tri colore a régua do card (classe própria, não .sev-*)",
      'class="tri tri-med"' in "\n".join(V._tri(dict(TRI, sev="med"))))
check("item com sev propaga a régua pro tri embutido",
      'class="tri tri-high"' in "\n".join(V.r_item(
          {"kind": "item", "title": "x", "sev": "high", "tri": dict(TRI)},
          {"n_items": 0, "item_labels": ("✓", "✏️", "✗")})))
check("vários bullets viram lista", "<ul class=\"tri-bullets\">" in html_tri)
check("um bullet só NÃO vira lista",
      html_tri.count("<ul class=\"tri-bullets\">") == 1)

# colapsar não é amputar: as três partes seguem obrigatórias
for falta in ("consequencia", "proposta", "problema"):
    incompleto = {k: v for k, v in TRI.items() if k != falta}
    errs = V._validate_block("tri", incompleto, "s1 b1")
    check("tri sem %s continua sendo RECUSADO" % falta,
          any("sem '%s'" % falta in x for x in errs), errs)

check("lista vazia conta como ausente",
      any("sem 'consequencia'" in x
          for x in V._validate_block("tri", dict(TRI, consequencia=[]), "s1 b1")))


# ── o placar agregado: escrito pelo programa, sempre aberto ────────────────
print("\n[placar — a superfície que o redator não escreve]")

SPEC_PLACAR = {"title": "t", "ident": {"projeto": "p", "artefato": "a"},
               "sections": [{"blocks": [
                   dict(TRI, sev="high"),
                   {"kind": "item", "title": "x", "sev": "med", "tri": TRI},
                   EVID]}]}
placar = "\n".join(V._placar(SPEC_PLACAR))
check("conta todos os problemas, dobrados ou não", "<strong>2 problemas</strong>" in placar, placar)
check("conta os graves à parte", "<strong>1 grave</strong>" in placar, placar)
_um = V._placar({"sections": [{"blocks": [{"kind": "tri", "problema": "p",
                                           "consequencia": ["c"], "proposta": ["s"]}]}]})
check("o placar concorda no singular",
      "<strong>1 problema</strong> apontado ·" in "\n".join(_um)
      and "o corpo a um clique" in "\n".join(_um), _um)
check("diz que o corpo está a um clique", "clique" in placar)
check("página sem problema não ganha placar",
      V._placar({"sections": [{"blocks": [EVID]}]}) == [])

pagina, _ = V.build_page(SPEC_PLACAR, tpl())
i_placar = pagina.index('class="callout warn"')
check("o placar sai ANTES da primeira seção", i_placar < pagina.index("<section>"))
check("o placar não nasce dentro de nenhum details",
      "<details" not in pagina[pagina.index('<div class="wrap">'):i_placar])

# a medida que originou tudo: quanto da página fica atrás de um clique
corpo = pagina[pagina.index('<div class="wrap">'):]
corpo = re.sub(r"<script.*?</script>", "", corpo, flags=re.S)
# A nota desta página sai da conta pelo mesmo motivo do <script>: ela não é
# conteúdo que o leitor veio ler, é o rodapé onde ele avalia a página. Contá-la
# faria toda página parecer menos colapsada só porque o rodapé cresceu, e a régua
# aqui mede a ocultação do CONTEÚDO.
corpo = re.sub(r'<div class="qualidade-box">.*?</div>\s*(?=</div>|$)', "", corpo, flags=re.S)


def _texto(s):
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


fechado = sum(len(_texto(x)) for x in
              re.findall(r"<details(?![^>]*\bopen\b)[^>]*>.*?</details>", corpo, flags=re.S))
total = len(_texto(corpo))
check("mais de um terço do texto nasce atrás de um clique",
      fechado > total / 3.0, "%d de %d" % (fechado, total))
visivel = corpo
for x in re.findall(r"<details(?![^>]*\bopen\b)[^>]*>.*?</details>", corpo, flags=re.S):
    visivel = visivel.replace(x, "")
check("o problema aparece sem precisar clicar",
      "O gate de bump não cobrava a forma do comando" in _texto(visivel))
check("a consequência NÃO aparece sem clicar",
      "7 de 9 commits passaram sem bump" not in _texto(visivel))


# ── o artefato encolhido precisa de saída pra ser visto grande ──────────────
print("\n[artefato — ver em tela cheia e em janela nova]")

_ART = {"kind": "artefato", "src": "file:///tmp/proto.html",
        "procedencia": "protótipo que escrevi agora"}
_h_art = "\n".join(V.r_artefato(_ART, {}))

check("tem botão de tela cheia", "artefatoTelaCheia(this)" in _h_art, _h_art)
check("tem link de janela nova", 'target="_blank"' in _h_art)
check("o link aponta pro artefato, não pra página",
      'href="file:///tmp/proto.html"' in _h_art, _h_art)
check("janela nova leva rel=noopener", 'rel="noopener"' in _h_art)
check("os botões ficam na BARRA, não sobre o artefato",
      _h_art.index("art-acoes") < _h_art.index("<iframe"), _h_art)
check("o selo 'artefato real' ganhou a classe que o CSS estiliza",
      'class="real"' in _h_art)

_h_img = "\n".join(V.r_artefato({"kind": "artefato", "src": "file:///tmp/tela.png"}, {}))
check("imagem também ganha as duas saídas",
      "artefatoTelaCheia" in _h_img and 'target="_blank"' in _h_img)

_T = tpl()
check("o handler existe no template (senão o onclick chama o vazio)",
      "function artefatoTelaCheia" in _T)
check("o CSS pinta o fundo em fullscreen (senão pisca branco)",
      ".artefato:fullscreen" in _T)
check("o fallback abre em aba quando não há Fullscreen API",
      "requestFullscreen" in _T and "window.open" in _T)

_pg, _ = V.build_page(spec(sections=[{"blocks": [dict(EVID), dict(_ART)]}]), _T)
check("na página montada, o botão e o handler coexistem",
      "artefatoTelaCheia(this)" in _pg and "function artefatoTelaCheia" in _pg)


# ── a aprovação de etapa: o documento inteiro à vista ──────────────────────
#
# A aprovação não é colhida sobre um resumo. O texto integral vai PRA PÁGINA, e os
# cards ficam por cima como índice. Sem o texto integral, não há aprovação a gravar.

print("\n[aprovação — o veredito só é colhido com o documento inteiro na página]")

DOC = ("Etapa 3 — o gate de release\n\n"
       "O gate roda no commit e avalia staged mais tracked-modificados.\n"
       "Quem não bumpa a versão não passa.\n"
       "A prova é a saída crua do próprio gate.\n")

APROV = {"kind": "aprovacao", "etapa": "Etapa 3 — o gate de release",
         "doc_integral": DOC,
         "cards": [{"title": "O que o gate cobra", "ancora": "Quem não bumpa a versão não passa."}]}

# O esquema vem ANTES do texto integral (F29.2): a página de aprovação de documento
# abre pelo desenho, e o documento inteiro fica atrás dele.
ESQUEMA_ANTES = {"kind": "esquema", "tipo": "fluxo", "retorno": "volta valendo",
                 "passos": [{"titulo": "Commit", "subs": ["o gate acorda"]},
                            {"titulo": "Gate", "subs": ["mede staged e modificado"]},
                            {"titulo": "Release", "subs": ["a versão propaga"]}]}
COM_ESQ = [{"blocks": [dict(ESQUEMA_ANTES), dict(APROV)]}]

check("aprovação com o texto integral é aceita",
      V.validate(spec(sections=COM_ESQ)) == [],
      V.validate(spec(sections=COM_ESQ)))

_errs_sem_esq = V.validate(spec(sections=[{"blocks": [dict(APROV)]}]))
check("aprovação de documento SEM esquema à frente é recusada",
      any("sem bloco 'esquema' antes" in x for x in _errs_sem_esq), _errs_sem_esq)
_errs_ordem = V.validate(spec(sections=[{"blocks": [dict(APROV), dict(ESQUEMA_ANTES)]}]))
check("esquema DEPOIS do texto integral não conta — a ordem é a régua",
      any("sem bloco 'esquema' antes" in x for x in _errs_ordem), _errs_ordem)

for falta in ({}, {"doc_integral": ""}, {"doc_integral": "   \n  "}):
    errs = V._validate_block("aprovacao", dict(APROV, **falta) if falta
                             else {k: v for k, v in APROV.items() if k != "doc_integral"},
                             "s1 b1")
    check("aprovação sem o texto integral (%r) é RECUSADA" % (falta.get("doc_integral"),),
          any("doc_integral" in x for x in errs), errs)

errs = V._validate_block("aprovacao", dict(APROV, etapa=""), "s1 b1")
check("aprovação sem 'etapa' é recusada", any("etapa" in x for x in errs), errs)

errs = V._validate_block("aprovacao", dict(
    APROV, cards=[{"title": "índice torto", "ancora": "linha que não existe no doc"}]), "s1 b1")
check("card cujo índice aponta pro nada é recusado", any("ancora" in x for x in errs), errs)

errs = V._validate_block("aprovacao", dict(APROV, cards=[{"ancora": "Quem não bumpa a versão não passa."}]),
                         "s1 b1")
check("card sem título é recusado", any("title" in x for x in errs), errs)

errs = V._validate_block("aprovacao", dict(APROV, etapa="a" * 200), "s1 b1")
check("a régua morde na etapa", any("caracteres" in x for x in errs), errs)
check("o texto integral fica FORA da régua (é o documento, não bullet)",
      V._validate_block("aprovacao", dict(APROV, doc_integral="x" * 900, cards=[]),
                        "s1 b1") == [])

_pg_ap, _ctx_ap = V.build_page(spec(sections=COM_ESQ), T)
check("o texto integral está na página, verbatim",
      "A prova é a saída crua do próprio gate." in _pg_ap)
check("a página carrega o documento INTEIRO, não um trecho",
      V._integral_presente(_pg_ap, DOC), "texto integral ausente")
check("o veredito é colhido na própria página (rádios + caixa de fechamento)",
      'name="fb-1"' in _pg_ap and 'class="feedback-box"' in _pg_ap)
check("os valores de máquina são os de sempre",
      'value="keep"' in _pg_ap and 'value="change"' in _pg_ap and 'value="remove"' in _pg_ap)
check("os rótulos falam de aprovação", "✓ Aprovar" in _pg_ap, V.APROVACAO_LABELS)
check("o card fica POR CIMA do texto integral (é índice, não conteúdo)",
      _pg_ap.index("O que o gate cobra") < _pg_ap.index("A prova é a saída crua"))
check("o card navega pra âncora dentro do documento",
      'href="#aprov-1-1"' in _pg_ap and 'id="aprov-1-1"' in _pg_ap, "âncora não ligada")
check("aprovação conta como pedido COM prova (o doc é a prova)",
      V.validate(spec(sections=[{"blocks": [dict(ESQUEMA_ANTES), dict(APROV),
                                            {"kind": "item", "title": "i"}]}])) == [])

# o critério de pronto, no caminho que a skill usa de verdade
with tempfile.TemporaryDirectory() as td:
    sem = os.path.join(td, "sem-integral.json")
    alvo = os.path.join(td, "aprovacao.html")
    with open(sem, "w", encoding="utf-8") as fh:
        json.dump(spec(sections=[{"blocks": [
            {"kind": "aprovacao", "etapa": "Etapa 3", "doc_integral": ""}]}]), fh)
    r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"),
                        "build", "--spec", sem, "--out", alvo], capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    check("sem texto integral: sai 2, explica, e NÃO escreve a página",
          r.returncode == 2 and "doc_integral" in r.stderr and not os.path.exists(alvo),
          (r.returncode, r.stderr))

check("o schema publica o bloco de aprovação",
      "aprovacao" in V.SCHEMA_DOC and "doc_integral" in V.SCHEMA_DOC)

# ── A nota DESTA PÁGINA (2026-08-08) ───────────────────────────────────────────
# Ela existe pra a próxima página sair melhor, e por isso sai em TODA página: o
# leitor pode achar ruim justamente a que não pede nada, e essa é a que nunca
# receberia nota se a caixa dependesse de haver decisão.
_so_texto = V.build_page(spec(sections=[{"blocks": [{"kind": "text", "text": "nada a decidir"}]}]), T)[0]
check("a nota sai mesmo na página sem decisão e sem item",
      'class="qualidade-box"' in _so_texto)
check("os três eixos saem, com os nomes que o dono escolheu",
      all(('data-eixo="%s"' % e) in _so_texto
          for e in ("clareza", "escaneabilidade", "detalhamento")))
check("cada eixo tem os três votos e nenhum vem marcado",
      _so_texto.count('class="qual-voto"') == 9 and "qual-voto escolhido" not in _so_texto)
check("o campo livre existe, e é opcional",
      'id="qual-livre"' in _so_texto)
check("a nota viaja no live-sync, não só no botão de copiar",
      "qualidade: getQualidade()" in _so_texto)
check("a nota entra no que os botões copiam",
      "Nota desta página" in _so_texto)
check("a nota é a ÚLTIMA caixa — não disputa com a decisão",
      _so_texto.rindex('class="qualidade-box"') >
      max(_so_texto.rfind('class="decisions-box"'), _so_texto.rfind('class="feedback-box"')))

_com_tudo = V.build_page(spec(sections=[{"blocks": [
    {"kind": "evidencia", "src": "s", "output": "o"},
    {"kind": "decision", "question": "q", "context": "c",
     "options": [{"title": "a", "tradeoff": "t"}, {"title": "c", "tradeoff": "d"}]}]}]), T)[0]
check("com decisão na página, a nota continua saindo uma vez só",
      _com_tudo.count('class="qualidade-box"') == 1)

# ── o build cobra as 4 conferências sozinho (2026-08-08) ──────────────────────
# Elas viviam como um passo escrito na SKILL.md, e a lição da própria rodada que
# as criou é que regra em prosa não pega. Avisa, não recusa: são pontos a
# conferir, e o julgamento continua sendo de quem escreve.
with tempfile.TemporaryDirectory() as td:
    _sujo = os.path.join(td, "sujo.json")
    _alvo = os.path.join(td, "p.html")
    with open(_sujo, "w", encoding="utf-8") as fh:
        json.dump(spec(sections=[{"blocks": [
            {"kind": "text", "text": "a leitura fica cara e nem sempre compensa"},
            dict(EVID), {"kind": "text", "text": "o disco enche."}]}]), fh)
    r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"),
                        "build", "--spec", _sujo, "--out", _alvo],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                       start_new_session=True)
    check("o build roda as 4 conferências sem ninguém pedir",
          "custo-sem-unidade" in r.stderr, r.stderr[-200:])
    check("elas AVISAM, não recusam — a página é escrita assim mesmo",
          r.returncode == 0 and os.path.exists(_alvo), (r.returncode, _alvo))

with tempfile.TemporaryDirectory() as td:
    _limpo = os.path.join(td, "limpo.json")
    with open(_limpo, "w", encoding="utf-8") as fh:
        json.dump(spec(sections=[{"blocks": [
            dict(EVID), {"kind": "text", "text": "Isso enche o disco todo mês."}]}]), fh)
    r = subprocess.run([sys.executable, os.path.join(HERE, "visual_page.py"),
                        "build", "--spec", _limpo, "--out", os.path.join(td, "p.html")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                       start_new_session=True)
    check("spec limpo não ganha aviso nenhum", "ponto(s) a conferir" not in r.stderr,
          r.stderr[-200:])

# Variável de cor que não existe não dá erro: dá texto sem cor, que passa por
# escolha de design. Foi o que aconteceu com `--muted` (o nome certo é
# `--text-mute`) em três lugares do bloco de nota, achado só na revisão.
_css = tpl()
_defin = set(re.findall(r'^\s*(--[a-z-]+):', _css, re.M))
_usadas = set(re.findall(r'var\((--[a-z-]+)\)', _css))
check("toda variável de cor usada está definida no template",
      not (_usadas - _defin), sorted(_usadas - _defin))

# Sombra colorida é o brilho que denuncia interface feita por máquina: elevação
# se faz com preto translúcido, e "qual foi a escolha" se sinaliza com borda,
# fundo e o ✓ — nunca com halo. Foco de teclado usa `outline`, que é anel, não
# sombra. Eram 4 halos de accent + 1 do selo de sincronia.
_halos = [ln.strip() for ln in _css.splitlines()
          if "box-shadow" in ln and re.search(r'rgba\(\s*(?!0\s*,\s*0\s*,\s*0)', ln)]
check("nenhum box-shadow do template usa cor (só elevação neutra)", not _halos, _halos)
check("o card escolhido continua sinalizado sem halo (borda + fundo + ✓)",
      re.search(r'\.opt\.selected\s*{[^}]*border-color: var\(--accent\)', _css)
      and '.opt.selected::after' in _css)
check("o foco por teclado continua visível (anel de outline)",
      "outline: 2px solid var(--accent)" in _css)

# Barra colorida grossa na lateral do card é o segundo tique mais reconhecível de
# interface feita por máquina. O que a barra CARREGAVA (aviso, problema, sucesso,
# severidade) passou pra moldura inteira de 1px na mesma cor — sai na captura do
# mesmo jeito. Sobra `border-left` só como fio de 1px neutro: o trilho da árvore.
_barras = [ln.strip() for ln in _css.splitlines()
           if re.search(r'border-left(-color)?\s*:', ln)
           and not re.search(r'border-left:\s*1px solid var\(--border(-strong)?\)', ln)]
check("nenhuma borda lateral grossa ou colorida no template", not _barras, _barras)
for _cls, _cor in [(".callout.warn", "--warn"), (".callout.danger", "--danger"),
                   (".callout.ok", "--ok"), (".tri.tri-med", "--warn"),
                   (".tri.tri-low", "--accent-2"), (".evidencia.vazio", "--danger")]:
    check("%s continua legível por cor na captura (moldura na cor do estado)" % _cls,
          re.search(re.escape(_cls) + r'\s*{[^}]*border-color: var\(%s\)' % _cor, _css))

# A miniatura do `srcdoc` é a FOTO do layout antigo que a página cita como
# passado: consertar a borda dela falsificaria a ilustração. O conferidor de
# design lê o arquivo como texto e não distingue a interface da foto dela, então
# cada linha da foto carrega a isenção com o motivo escrito — se alguém tirar a
# isenção, ou a foto, este check cai junto.
_foto = [ln for ln in _css.splitlines()
         if "border-top:3px solid" in ln and "&lt;div" in ln]
check("as duas linhas da foto do layout antigo continuam no template", len(_foto) == 2, _foto)
check("cada linha da foto carrega a isenção declarada do conferidor de design",
      all("impeccable-disable-line border-accent-on-rounded --" in ln for ln in _foto), _foto)

# Barra de progresso é a exceção legítima do conferidor: crescer de largura é
# exatamente o que ela comunica, e a alternativa por `transform` esticaria o
# texto dentro dela. Cada uma das três carrega a isenção com o motivo escrito —
# se alguém tirar a isenção, ou a barra, este check cai junto.
_barras_prog = [ln for ln in _css.splitlines() if "transition: width" in ln]
check("as três barras de progresso continuam no template", len(_barras_prog) == 3,
      _barras_prog)
check("cada barra de progresso carrega a isenção declarada do conferidor de design",
      all("impeccable-disable-line layout-transition --" in ln for ln in _barras_prog),
      _barras_prog)

# ── esquema: os 6 desenhos nativos ─────────────────────────────────────────
#
# Os seis nasceram como HTML artesanal dentro de `raw_html` — 230 linhas de
# desenho redigitadas por página. O que estes checks protegem é que cada um saia
# do PROGRAMA: se algum voltar a depender de `raw_html`, o teste do fim da seção
# cai, porque a página inteira é montada sem nenhum bloco de válvula.

print("\n[esquema — os 6 desenhos vêm do programa, não de raw_html artesanal]")

ESQ = {
    "escada": {"kind": "esquema", "tipo": "escada", "nota": "quem está mais acima vence",
               "itens": [{"titulo": "Nada se perde", "sub": "falhou? alerta com os dados"},
                         {"titulo": "Reversível", "sub": "nasce pausado"}]},
    "quadrantes": {"kind": "esquema", "tipo": "quadrantes",
                   "grupos": [{"titulo": "QUEM MANDA",
                               "itens": [{"marca": "🔒", "texto": "o dono opera a conta"}]},
                              {"titulo": "TÉCNICA",
                               "itens": [{"marca": "⏳", "texto": "sem build"}]}]},
    "mapa": {"kind": "esquema", "tipo": "mapa",
             "caixas": [{"id": "ads", "titulo": "Anúncios", "sub": "de fora", "x": 40, "y": 20},
                        {"id": "lp", "titulo": "As páginas", "sub": "este repo", "x": 300,
                         "y": 200}],
             "setas": [{"de": "ads", "para": "lp", "rotulo": "clique"}]},
    "fluxo": {"kind": "esquema", "tipo": "fluxo", "retorno": "volta valendo",
              "passos": [{"titulo": "Anúncio", "subs": ["só quem já busca"]},
                         {"titulo": "Página", "subs": ["uma por intenção"]},
                         {"titulo": "Funil", "subs": ["o dono do lead"]}]},
    "glossario": {"kind": "esquema", "tipo": "glossario",
                  "termos": [{"termo": "MQL", "desc": "o lead que o dono marcou como bom"}],
                  "falsos": [{"termo": "“conversão”", "errado": "formulário preenchido",
                              "certo": "o lead marcado à mão"}]},
    "placar": {"kind": "esquema", "tipo": "placar", "nota": "o que cada peça obedece",
               "linhas": [{"n": "1", "titulo": "A lei manda", "estado": "ok", "obs": "em dia"},
                          {"n": "2", "titulo": "Nada some", "estado": "divida",
                           "obs": "sem cobrador"}]},
}

check("os 6 tipos do desenho estão registrados",
      sorted(V.ESQUEMAS) == ["escada", "fluxo", "glossario", "mapa", "placar", "quadrantes"],
      sorted(V.ESQUEMAS))

for _tipo, _blk in ESQ.items():
    _s = spec(sections=[{"title": "S", "blocks": [dict(EVID), dict(_blk)]}])
    check("esquema %s: spec válido passa" % _tipo, V.validate(_s) == [], V.validate(_s))
    _pg, _ = V.build_page(_s, T)
    _corpo = "".join(V.RENDERERS["esquema"](_blk, {"n_items": 0}))
    check("esquema %s: sai desenho de verdade na página (svg ou grid)" % _tipo,
          '<div class="diagram">' in _corpo and ("<svg" in _corpo or "display:flex" in _corpo),
          _corpo[:120])
    check("esquema %s: nenhum trecho vem de fora (sem rede, sem lib)" % _tipo,
          "http" not in _corpo and "<script" not in _corpo)
    check("esquema %s: o conteúdo do spec chega na página" % _tipo,
          _corpo in _pg or _corpo.strip() in _pg.replace("\n", ""))

# Legenda curta é o motivo do bloco existir: "só quem já busca" não é frase e não
# tem que virar uma. A régua de estilo cobra os outros blocos e passa longe deste.
_curto = dict(ESQ["fluxo"])
_curto["passos"] = [{"titulo": "Anúncio", "subs": ["e só quem já busca — sem ponto final"]},
                    {"titulo": "Página", "subs": ["x" * 200]}]
check("o texto de dentro do desenho é isento da régua de estilo",
      V.validate(spec(sections=[{"blocks": [dict(EVID), _curto]}])) == [])
check("mas a régua continua valendo no bloco vizinho",
      any("bullets" in e for e in V.validate(spec(sections=[{"blocks": [
          dict(EVID), _curto, {"kind": "bullets", "items": ["e " + "y" * 200]}]}]))))

check("tipo desconhecido é recusado com a lista dos que existem",
      any("escada|fluxo" in e for e in
          V.validate(spec(sections=[{"blocks": [dict(EVID),
                                                {"kind": "esquema", "tipo": "pizza"}]}]))))
check("desenho sem conteúdo é recusado",
      any("desenho vazio" in e for e in
          V.validate(spec(sections=[{"blocks": [dict(EVID),
                                                {"kind": "esquema", "tipo": "escada",
                                                 "itens": []}]}]))))
check("caixa do mapa sem posição é recusada",
      any("sem 'y'" in e for e in V.validate(spec(sections=[{"blocks": [
          dict(EVID), {"kind": "esquema", "tipo": "mapa",
                       "caixas": [{"id": "a", "titulo": "A", "x": 10}]}]}]))))
check("seta que aponta pra caixa que não existe é recusada",
      any("caixa inexistente" in e for e in V.validate(spec(sections=[{"blocks": [
          dict(EVID), {"kind": "esquema", "tipo": "mapa",
                       "caixas": [{"id": "a", "titulo": "A", "x": 10, "y": 10}],
                       "setas": [{"de": "a", "para": "zz"}]}]}]))))
check("estado fora do vocabulário do placar é recusado",
      any("'estado'" in e for e in V.validate(spec(sections=[{"blocks": [
          dict(EVID), {"kind": "esquema", "tipo": "placar",
                       "linhas": [{"titulo": "T", "estado": "mais_ou_menos"}]}]}]))))

# A prova de que nenhum dos seis ficou dependendo da válvula: uma página com os
# seis juntos, e zero `raw_html` no spec.
_seis = spec(sections=[{"title": "Os seis", "blocks": [dict(EVID)] + [dict(b) for b in
                                                                     ESQ.values()]}])
check("os 6 numa página só: nenhum bloco raw_html no spec",
      not any(b.get("kind") == "raw_html" for b in _seis["sections"][0]["blocks"]))
_pg6, _ = V.build_page(_seis, T)
check("os 6 numa página só: a página é escrita e traz 6 caixas de desenho",
      _pg6.count('<div class="diagram">') == 6, _pg6.count('<div class="diagram">'))
check("os 6 numa página só: cor do desenho sai do tema, não de hex fixo",
      "var(--accent)" in _pg6 and not re.search(r'(rect|text)[^>]*fill="#', _pg6))


# ── a regra que só vive na SKILL.md ────────────────────────────────────────
# A página de aprovação de documento sem desenho na frente é textão. A regra é
# de prosa (o programa não sabe qual documento está sendo aprovado), então o que
# a suíte cobra é a PRESENÇA dela — e do vocabulário por tipo, que é a parte que
# some primeiro quando alguém reescreve a seção.

print("\n[SKILL.md — a seção da página de aprovação de documento]")

with open(os.path.join(HERE, "..", "skills", "visual", "SKILL.md"), encoding="utf-8") as fh:
    SKILL = fh.read()

check("a seção existe",
      "### Página de aprovação de documento — o esquema vem ANTES do texto" in SKILL)
check("a regra da ordem está escrita",
      "vem ANTES do bloco `aprovacao`" in SKILL)
check("o doc_integral continua obrigatório",
      "O `doc_integral` **continua obrigatório**" in SKILL)
check("sem esquema à frente reprova",
      "Página de aprovação sem esquema à frente é textão e reprova." in SKILL)
check("aponta pro bloco que já existe, não reinventa desenho",
      "plugins/visual/lib/visual_page.py" in SKILL and "r_esquema" in SKILL)
_sec = SKILL.split("### Página de aprovação de documento")[1].split("\n### ")[0]
for _t in sorted(V.ESQUEMAS):
    check("vocabulário por tipo: %s aparece na seção" % _t, "`%s`" % _t in _sec)
# O mapa documento→tipo mora no PROGRAMA e sai por `visual_page.py schema` — a seção
# aponta o comando em vez de repetir a lista, que é onde ela envelhecia calada.
check("a seção manda buscar o mapa no comando, não decorar a lista",
      "visual_page.py" in _sec and '"$VP" schema' in _sec)
_saida_schema = subprocess.run(
    [sys.executable, os.path.join(HERE, "visual_page.py"), "schema"],
    capture_output=True, text=True, stdin=subprocess.DEVNULL,
    start_new_session=True).stdout
for _d, _tipo, _ in V.ESQUEMA_POR_DOC:
    check("documento mapeado na saída do schema: %s" % _d,
          _d in _saida_schema and _tipo in V.ESQUEMAS)
check("todo documento canônico do mapa tem tipo que o programa sabe desenhar",
      all(tp in V.ESQUEMAS for _, tp, _ in V.ESQUEMA_POR_DOC))


print("\n%d passou · %d falhou" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
