#!/usr/bin/env python3
"""A régua de forma cobrada nas páginas que JÁ estão no disco — e qual regra cada uma quebra.

O validador do `visual_page.py` só alcança página que ainda vai nascer, e só pelo
spec. As centenas de HTML que já estão em `.claude/visual/` (onde o /visual, o
/fallow, o /branches e o /slides escrevem) ficavam fora de qualquer medição — e
"tem prosa nessas páginas" não é achado acionável enquanto ninguém diz QUAL
página, QUAL regra e QUAL trecho.

Este módulo lê o HTML pronto, extrai o texto visível, aplica a régua e imprime
`arquivo · regra · trecho`.

A régua NÃO é redigitada aqui: o texto extraído é entregue ao `erros_de_estilo`
do `regua_texto`, no perfil do artefato, e o que volta é a checagem que
disparou. Uma segunda cópia da régua é exatamente o defeito que este módulo
existe pra pegar: ela divergiria da primeira e cada lado ficaria coerente sozinho.

Fora da régua, conforme `quality-goals.md`: saída crua dentro do bloco de prova
(`<pre>`, a linha de origem da evidência) e as linhas de árvore de plano
desenhadas pelo programa (`.plan-tree`, `.pt-*`). O resto do chrome de página
(script, style, svg, botão, textarea) não é texto autoral e também não entra.

Limite declarado: bloco `raw_html` não deixa marca no HTML renderizado, então o
texto que entrou por ele é auditado como qualquer outro — não há como isentá-lo.

Uso:
    python3 regua_audit.py paginas  [--dir D] [--desde AAAA-MM-DD] [--todos] [--json]
    python3 regua_audit.py veredito [--dir D] [--desde AAAA-MM-DD] [--repo R] [--json]

Exit 1 = há violação (veredito, não crash) — convenção de CLI de lib do repo.

stdlib only (requisito do repo).
"""

import argparse
import json
import os
import subprocess
import sys
import time
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regua_texto as rt  # noqa: E402  — a régua mora lá; cópia dela aqui divergiria
import visual_page as vp  # noqa: E402  — só o `_plural`, que é forma de contagem

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
RESOLVE_DIR = os.path.normpath(os.path.join(HERE, "..", "skills", "visual", "resolve-dir.sh"))

# ── os cinco geradores de página do marketplace ─────────────────────────────
# Cada um escreve HTML por programa; cada um tem um perfil, porque o que fica
# fora da régua muda de gerador pra gerador.
GERADORES = [
    ("plugins/visual/lib/visual_page.py", "relatorio"),
    ("plugins/project-skills/lib/plan_state.py", "plano"),  # acopla-ok: lista de geradores do próprio monorepo, lida pela régua
    ("plugins/fallow/lib/report.py", "fallow"),
    ("plugins/branches/lib/branch_state.py", "branches"),
    ("plugins/slides/lib/md2deck.py", "slides"),
]

# Fora da régua em TODA página: a linha de origem da prova é comando literal, e a
# faixa de identidade é rótulo+valor lado a lado ("Projeto" · "pedro-plugins"),
# não bullet — medir a faixa inteira como uma frase é artefato de extração.
FORA_COMUM = ("evidencia-src", "evidencia-conta", "ident-strip")

PERFIS = {
    # ordem de detecção importa: página de plano também tem a faixa de identidade
    "plano": {"nome": "árvore de plano", "marcas": ('class="plan-tree',),
              "fora": FORA_COMUM + ("plan-tree", "pt-")},
    "slides": {"nome": "deck", "marcas": ('class="deck-chrome',),
               "fora": FORA_COMUM + ("deck-chrome", "counter", "progress", "brand",
                                     "grain", "ambient-glow")},
    "fallow": {"nome": "relatório do fallow", "marcas": ("<title>Fallow ·",),
               "fora": FORA_COMUM},
    "branches": {"nome": "relatório de branches", "marcas": ("<title>Branches ·",),
                 "fora": FORA_COMUM},
    # quatro marcas porque a página do /visual mudou de forma: a faixa de
    # identidade é recente, e as páginas de junho só têm os blocos do template.
    # `doc-integral` é o documento que a página traz por inteiro para que a
    # aprovação de etapa tenha lastro. Medi-lo em bullets seria mandar cortá-lo —
    # e é justamente a versão cortada que a trava da aprovação existe para recusar.
    "relatorio": {"nome": "página do /visual",
                  "marcas": ('class="ident-strip', 'class="decision-card',
                             'class="feedback-item', 'class="feedback-box'),
                  "fora": FORA_COMUM + ("doc-integral",)},
}
ORDEM_DETECCAO = ("plano", "slides", "fallow", "branches", "relatorio")

# Qual perfil da régua vale pra cada gerador. O que não está aqui é página.
PERFIL_REGUA = {"plano": "plano", "slides": "slide"}

R_TETO = "teto-%d" % rt.BULLET_MAX
R_BULLETS = "teto-%d-bullets" % rt.BULLETS_MAX
R_PALAVRAS = "teto-%d-palavras" % rt.SLIDE_PALAVRAS

REGRAS = {
    R_TETO: "teto de %d caracteres" % rt.BULLET_MAX,
    "duas-frases": "duas frases no mesmo bullet",
    "conectivo": "abre com conectivo de continuação",
    R_BULLETS: "mais de %d bullets no bloco" % rt.BULLETS_MAX,
    R_PALAVRAS: "mais de %d palavras no bullet de slide" % rt.SLIDE_PALAVRAS,
    # rede: checagem nova no regua_texto entra na conta com o nome genérico em vez
    # de derrubar a impressão — nenhuma violação some por não ter código aqui.
    "estilo": "outra checagem da régua",
}

# Cada mensagem do `erros_de_estilo` é a checagem que disparou; o código de regra
# sai da marca estável dela. A suíte cobre as cinco, pra que mudança de redação lá
# apareça aqui como falha em vez de virar "estilo".
MARCAS_REGRA = (
    (" caracteres, o teto é ", R_TETO),
    (" bullets, o teto é ", R_BULLETS),
    (" palavras, o teto é ", R_PALAVRAS),
    ("duas frases no mesmo bullet", "duas-frases"),
    ("abre com conectivo", "conectivo"),
)

# ── extração do texto visível ──────────────────────────────────────────────

INLINE = {"span", "code", "strong", "em", "b", "i", "a", "mark", "small", "u",
          "abbr", "sup", "sub", "kbd", "var", "time", "s", "del", "ins", "cite"}
VOID = {"br", "hr", "img", "meta", "link", "input", "source", "col", "area",
        "base", "embed", "param", "track", "wbr"}
# Subárvores que não são texto autoral: chrome, script e a prova literal.
IGNORA = {"script", "style", "svg", "head", "textarea", "select", "noscript",
          "template", "pre", "button"}


def _txt(s):
    """Colapsa o espaço em branco do HTML — o olho lê uma linha, não a indentação."""
    return " ".join(str(s).split())


class Extrator(HTMLParser):
    """Devolve os eventos de texto da página, em ordem de documento.

    ("texto", conteúdo, onde) — um bloco de texto visível
    ("lista", itens, onde) — uma `ul`/`ol` e os textos que ela tem dentro
    """

    def __init__(self, fora=()):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.fora = tuple(fora)
        self.eventos = []
        self._pilha = []
        self._pular = 0
        self._buf = []
        self._dono = "?"
        self._listas = []

    def _onde(self, tag, attrs):
        cls = (dict(attrs).get("class") or "").split()
        return tag + ("." + cls[0] if cls else "")

    def _flush(self):
        t = _txt("".join(self._buf))
        self._buf = []
        if t and not self._pular:
            self.eventos.append(("texto", t, self._dono))
            # O item é o `li`, não o bloco de texto: bullet com título e subtítulo
            # é UM bullet, e contá-lo como dois inventaria lista grande demais.
            if self._listas and self._listas[-1][2]:
                self._listas[-1][2][-1].append(t)

    def handle_data(self, data):
        self._buf.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if tag == "br":
                self._flush()
            return
        if tag not in INLINE:
            self._flush()
        cls = (dict(attrs).get("class") or "").split()
        pular = tag in IGNORA or any(c.startswith(self.fora) for c in cls)
        self._pilha.append((tag, pular))
        if pular:
            self._pular += 1
        if tag in ("ul", "ol"):
            self._listas.append([tag, self._onde(tag, attrs), [], self._pular > 0])
        elif tag == "li" and self._listas:
            self._listas[-1][2].append([])
        if tag not in INLINE:
            self._dono = self._onde(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._flush()

    def handle_endtag(self, tag):
        if tag in VOID or not any(f[0] == tag for f in self._pilha):
            return
        if tag not in INLINE:
            self._flush()
        while self._pilha:
            t, pular = self._pilha.pop()
            if pular:
                self._pular -= 1
            if t == tag:
                break
        if tag in ("ul", "ol") and self._listas:
            f = self._listas.pop()
            itens = [" ".join(partes) for partes in f[2] if partes]
            if itens and not f[3]:
                self.eventos.append(("lista", itens, f[1]))


def detectar(txt):
    """Qual gerador escreveu esta página — pela marca que só ele deixa."""
    for k in ORDEM_DETECCAO:
        if any(m in txt for m in PERFIS[k]["marcas"]):
            return k
    return None


# ── a régua, aplicada aos eventos ──────────────────────────────────────────

def regra_de(msg):
    """O código de regra por trás de uma mensagem do `erros_de_estilo`."""
    for marca, regra in MARCAS_REGRA:
        if marca in msg:
            return regra
    return "estilo"


def _detalhe(msg):
    """O miolo da mensagem: o que foi medido, sem o `onde` nem o conselho."""
    corpo = msg.split(": ", 1)[-1]
    return corpo.split(" — ")[0].strip()


def violacoes_de(eventos, perfil="pagina"):
    """A régua do `regua_texto`, chamada sobre o texto que está na tela.

    A lista volta com a contagem de bullets e nada mais: as checagens de cada
    item já vieram pelo evento de texto dele, e reportá-las de novo aqui contaria
    a mesma violação duas vezes.
    """
    out = []
    for ev in eventos:
        if ev[0] == "lista":
            _, itens, onde = ev
            for msg in rt.erros_de_estilo(itens, onde, perfil):
                if regra_de(msg) == R_BULLETS:
                    out.append({"regra": R_BULLETS, "detalhe": _detalhe(msg),
                                "onde": onde, "trecho": itens[0]})
            continue
        _, texto, onde = ev
        for msg in rt.erros_de_estilo(texto, onde, perfil):
            out.append({"regra": regra_de(msg), "detalhe": _detalhe(msg),
                        "onde": onde, "trecho": texto})
    return out


def auditar(caminho):
    """Uma página: perfil, violações e quando ela foi escrita.

    `perfil: None` é página que nenhum dos cinco geradores escreveu (HTML digitado
    à mão, de antes do gerador). Ela volta na lista em vez de sumir: página que
    ninguém auditou é informação, e omiti-la é o defeito que a régua persegue.
    """
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except OSError:
        return None
    perfil = detectar(txt)
    quando = time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(caminho)))
    if perfil is None:
        return {"arquivo": caminho, "perfil": None, "quando": quando, "violacoes": []}
    ex = Extrator(PERFIS[perfil]["fora"])
    ex.feed(txt)
    return {"arquivo": caminho, "perfil": perfil, "quando": quando,
            "violacoes": violacoes_de(ex.eventos, PERFIL_REGUA.get(perfil, "pagina"))}


def varrer(diretorio, desde=None):
    nomes = sorted(n for n in os.listdir(diretorio) if n.endswith(".html"))
    out = []
    for n in nomes:
        r = auditar(os.path.join(diretorio, n))
        if r and (not desde or r["quando"] >= desde):
            out.append(r)
    return out


def dir_padrao():
    r = subprocess.run(["bash", RESOLVE_DIR, os.getcwd()], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    return (r.stdout or "").strip() or os.path.join(REPO, ".claude", "visual")


# ── saída ──────────────────────────────────────────────────────────────────

def _corte(s, n=96):
    s = _txt(s)
    return s if len(s) <= n else s[:n - 1] + "…"


def _linha_viol(v):
    return "    • %s · %s · %s" % (v["regra"], v["detalhe"], v["onde"])


def imprime_paginas(res, todos=False):
    total = sum(len(r["violacoes"]) for r in res)
    sem_perfil = [r for r in res if r["perfil"] is None]
    print("🔍 Régua de forma · %s · %s"
          % (vp._plural(len(res), "página"), vp._plural(total, "violação", "violações")))
    print()
    for r in res:
        nome = os.path.basename(r["arquivo"])
        vs = r["violacoes"]
        if r["perfil"] is None:
            continue
        if not vs:
            print("✅ %s · %s" % (nome, PERFIS[r["perfil"]]["nome"]))
            continue
        print("⚠️  %s · %s · %s" % (nome, PERFIS[r["perfil"]]["nome"],
                                    vp._plural(len(vs), "violação", "violações")))
        mostra = vs if todos else vs[:3]
        for v in mostra:
            print(_linha_viol(v))
            print('      "%s"' % _corte(v["trecho"]))
        if len(vs) > len(mostra):
            print("    ⋯ e mais %d nesta página (--todos)" % (len(vs) - len(mostra)))
    por_regra = {}
    for r in res:
        for v in r["violacoes"]:
            por_regra[v["regra"]] = por_regra.get(v["regra"], 0) + 1
    print()
    print("📊 %s · %d com violação"
          % (vp._plural(len(res), "página"), sum(1 for r in res if r["violacoes"])))
    for k in sorted(por_regra, key=lambda x: -por_regra[x]):
        print("    • %s — %s: %d" % (k, REGRAS[k], por_regra[k]))
    if sem_perfil:
        print("    • ❔ %s sem perfil de gerador — digitada à mão, fora do alcance"
              % vp._plural(len(sem_perfil), "página"))


# ── veredito F4.1: as mudanças do dia nos cinco geradores ──────────────────

def _git(repo, *args):
    r = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    return (r.stdout or "") if r.returncode == 0 else ""


def sem_commit(repo, caminho):
    """A mudança que está na árvore de trabalho e ainda não virou commit.

    Sem isto o veredito só enxergava commit, e o trabalho do dia ainda não
    commitado saía como "sem mudança" — o pior veredito possível, porque é
    silêncio sobre arquivo que mudou.
    """
    st = [ln for ln in _git(repo, "status", "--porcelain", "--", caminho).splitlines()
          if ln.strip()]
    if not st:
        return []
    codigo = st[0][:2].strip()
    if codigo == "??":
        return ["árvore · arquivo novo, ainda fora do git"]
    n = _git(repo, "diff", "HEAD", "--numstat", "--", caminho).split()
    quanto = "+%s/-%s linhas" % (n[0], n[1]) if len(n) >= 2 else "mudança não commitada"
    return ["árvore · %s · %s" % (codigo, quanto)]


def mudancas(repo, caminho, desde):
    """Os commits do dia MAIS o que está na árvore de trabalho, sem commit."""
    log = _git(repo, "log", "--since=%s 00:00" % desde, "--pretty=format:%h %s",
               "--", caminho)
    return ([ln for ln in log.splitlines() if ln.strip()]
            + sem_commit(repo, caminho))


def veredito(diretorio, desde, repo):
    """Cada mudança do dia num gerador vira conforme/em desacordo, com o motivo.

    Mudança é commit do dia OU arquivo mexido na árvore de trabalho — trabalho que
    ainda não virou commit é o caso normal na hora de auditar, não a exceção.

    O motivo não é opinião: é a página que aquele gerador escreveu, auditada pela
    régua. Sem página escrita depois da mudança, cai na página mais recente dele —
    mesma régua, artefato mais velho, e a idade vai dita no motivo.

    O julgado é a PÁGINA, e as mudanças do dia herdam o veredito dela — atribuir a
    violação ao commit exigiria saber qual linha do gerador escreveu aquele texto,
    e isso a página não conta. Por isso o motivo nomeia sempre arquivo e trecho.
    """
    todas = varrer(diretorio)
    linhas = []
    for caminho, perfil in GERADORES:
        muds = mudancas(repo, caminho, desde)
        if not muds:
            linhas.append({"gerador": caminho, "perfil": perfil, "mudancas": [],
                           "veredito": "sem mudança",
                           "motivo": "nem commit desde %s nem mudança na árvore" % desde,
                           "trecho": "", "paginas": [], "violacoes": 0})
            continue
        pags = [p for p in todas if p["perfil"] == perfil and p["quando"] >= desde]
        velha = False
        if not pags:
            candidatas = [p for p in todas if p["perfil"] == perfil]
            pags = sorted(candidatas, key=lambda p: p["quando"])[-1:]
            velha = True
        if not pags:
            linhas.append({"gerador": caminho, "perfil": perfil, "mudancas": muds,
                           "veredito": "em desacordo",
                           "motivo": "nenhuma página deste gerador no disco — não verificável",
                           "trecho": "", "paginas": [], "violacoes": 0})
            continue
        viols = [(p, v) for p in pags for v in p["violacoes"]]
        idade = (" · página de %s, anterior à mudança" % pags[0]["quando"]) if velha else ""
        nomes = [os.path.basename(p["arquivo"]) for p in pags]
        if viols:
            p, v = viols[0]
            linhas.append({"gerador": caminho, "perfil": perfil, "mudancas": muds,
                           "veredito": "em desacordo",
                           "motivo": "%s em %s%s" % (v["regra"], os.path.basename(p["arquivo"]),
                                                     idade),
                           "trecho": _corte(v["trecho"], 90),
                           "paginas": nomes, "violacoes": len(viols)})
        else:
            linhas.append({"gerador": caminho, "perfil": perfil, "mudancas": muds,
                           "veredito": "conforme",
                           "motivo": "%s sem violação%s"
                                     % (vp._plural(len(pags), "página"), idade),
                           "trecho": "", "paginas": nomes, "violacoes": 0})
    return linhas


MARCA = {"conforme": "✅ CONFORME", "em desacordo": "❌ EM DESACORDO",
         "sem mudança": "⬜ SEM MUDANÇA"}


def imprime_veredito(linhas, desde):
    print("⚖️  Veredito · mudanças de %s nos cinco geradores de página" % desde)
    print("   mudança = commit do dia ou arquivo mexido na árvore de trabalho")
    print("   o julgado é a página que cada gerador escreve · a mudança do dia herda o veredito dela")
    print()
    for reg in linhas:
        print("%s · %s" % (MARCA[reg["veredito"]], reg["gerador"]))
        print("    • motivo: %s" % reg["motivo"])
        if reg["trecho"]:
            print('      "%s"' % reg["trecho"])
        for m in reg["mudancas"]:
            print("    • mudança: %s" % _corte(m, 110))
    print()
    print("📊 %d conforme · %d em desacordo · %d sem mudança"
          % (sum(1 for x in linhas if x["veredito"] == "conforme"),
             sum(1 for x in linhas if x["veredito"] == "em desacordo"),
             sum(1 for x in linhas if x["veredito"] == "sem mudança")))


# ── CLI ────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(description="a régua de forma nas páginas do disco")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("paginas", help="audita as páginas e diz qual regra cada uma quebra")
    a.add_argument("--dir")
    a.add_argument("--desde", help="só páginas escritas em/depois de AAAA-MM-DD")
    a.add_argument("--todos", action="store_true", help="toda violação, não só 3 por página")
    a.add_argument("--json", action="store_true")

    b = sub.add_parser("veredito", help="conforme/em desacordo por mudança do dia")
    b.add_argument("--dir")
    b.add_argument("--desde", default=time.strftime("%Y-%m-%d"))
    b.add_argument("--repo", default=REPO)
    b.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    d = args.dir or dir_padrao()
    if not os.path.isdir(d):
        print("não achei o diretório de páginas: %s" % d, file=sys.stderr)
        return 2

    if args.cmd == "paginas":
        res = varrer(d, args.desde)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            imprime_paginas(res, args.todos)
        return 1 if any(r["violacoes"] for r in res) else 0

    linhas = veredito(d, args.desde, args.repo)
    if args.json:
        print(json.dumps(linhas, ensure_ascii=False, indent=2))
    else:
        imprime_veredito(linhas, args.desde)
    return 1 if any(x["veredito"] == "em desacordo" for x in linhas) else 0


if __name__ == "__main__":
    sys.exit(main())
