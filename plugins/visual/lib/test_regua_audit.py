#!/usr/bin/env python3
"""Suíte do regua_audit.py — a régua cobrada na página que já está no disco."""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regua_audit as ra  # noqa: E402
import regua_texto as rt  # noqa: E402

FAILS = []
AQUI = os.path.dirname(os.path.abspath(__file__))


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


LONGO = ("um bullet que passa do teto de cento e quarenta caracteres porque foi escrito "
         "como parágrafo e não como bullet, exatamente a prosa que a régua existe pra recusar")

PAGINA = """<!DOCTYPE html><html><head><style>.x{color:red}</style></head><body>
<div class="wrap"><div class="ident-strip"><span class="ik">Projeto</span></div>
<p class="decision-context">%s</p>
<p>Uma frase. Outra frase no mesmo bloco.</p>
<p>e abre com conectivo de continuação</p>
<ul class="bullets"><li>a</li><li>b</li><li>c</li><li>d</li><li>e</li><li>f</li><li>g</li></ul>
<details class="evidencia"><summary class="evidencia-src">%s</summary>
<pre>%s</pre></details>
<script>var x = "%s";</script>
<p>bullet curto e limpo</p>
</div></body></html>""" % (LONGO, LONGO, LONGO, LONGO)

PLANO = """<!DOCTYPE html><html><body><div class="wrap">
<div class="ident-strip"><span class="ik">Plano</span></div>
<div class="plan-tree"><ul class="pt-items"><li class="pt-item">%s</li>
<li class="pt-item">Uma frase. Outra frase.</li><li>c</li><li>d</li>
<li>e</li><li>f</li><li>g</li></ul></div>
<p>%s</p></div></body></html>""" % (LONGO, LONGO)


BRANCHES = ('<html><head><title>Branches · x</title></head><body>'
            "<p>bullet curto</p></body></html>")


def escreve(d, nome, txt):
    p = os.path.join(d, nome)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)
    return p


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, "-c", "user.email=t@t",
                           "-c", "user.name=t"] + list(args),
                          capture_output=True, text=True)


def repo_de_mentira():
    """Um repo com os geradores dentro: um commitado e mexido, um novo, um parado.

    É a única forma de provar o veredito da árvore de trabalho sem depender do
    estado do repo real, que muda a cada commit de quem roda a suíte.
    """
    d = tempfile.mkdtemp(prefix="regua-audit-git-")
    alvo = "plugins/branches/lib/branch_state.py"
    parado = "plugins/slides/lib/md2deck.py"
    git(d, "init", "-q")
    for rel in (alvo, parado):
        escreve(d, rel, "print('antes')\n")
    git(d, "add", "-A")
    git(d, "commit", "-qm", "base")
    escreve(d, alvo, "print('depois')\nprint('mais uma linha')\n")
    escreve(d, "plugins/visual/lib/visual_page.py", "print('novo')\n")
    return d, alvo


def main():
    d = tempfile.mkdtemp(prefix="regua-audit-")
    p1 = escreve(d, "2026-08-03-relatorio.html", PAGINA)
    p2 = escreve(d, "plano-2026-08-03-x-track.html", PLANO)

    # ── detecção de perfil ────────────────────────────────────────────────
    check("detecta a página do /visual", ra.detectar(PAGINA) == "relatorio")
    check("detecta a árvore de plano antes do relatório", ra.detectar(PLANO) == "plano")
    check("HTML de fora não é página nossa", ra.detectar("<html><p>oi</p></html>") is None)
    # as páginas de junho vieram do mesmo template, mas sem a faixa de identidade
    check("página antiga do /visual continua reconhecida",
          ra.detectar('<div class="feedback-item">x</div>') == "relatorio")

    # ── o que a régua alcança, e o que não ────────────────────────────────
    r1 = ra.auditar(p1)
    regras = [v["regra"] for v in r1["violacoes"]]
    trechos = " | ".join(v["trecho"] for v in r1["violacoes"])
    check("acusa o teto de %d" % rt.BULLET_MAX, ra.R_TETO in regras)
    check("acusa duas frases no mesmo bloco", "duas-frases" in regras)
    check("acusa o conectivo de continuação", "conectivo" in regras)
    check("acusa a lista com mais de %d bullets" % rt.BULLETS_MAX, ra.R_BULLETS in regras)
    check("a lista de 7 é contada certa",
          any(v["regra"] == ra.R_BULLETS and v["detalhe"].startswith("7 bullets")
              for v in r1["violacoes"]))
    check("a violação do item não é contada de novo pela lista",
          sum(1 for v in r1["violacoes"] if v["regra"] == ra.R_BULLETS) == 1)
    check("o trecho vem junto do motivo", LONGO[:40] in trechos)
    check("diz ONDE, não só o quê",
          any(v["onde"] == "p.decision-context" for v in r1["violacoes"]))
    check("bullet curto e limpo não vira violação",
          not any("curto e limpo" in v["trecho"] for v in r1["violacoes"]))
    check("saída crua do bloco de prova fica fora da régua",
          sum(1 for v in r1["violacoes"] if v["regra"] == ra.R_TETO) == 1)
    check("script não é texto autoral", "var x" not in trechos)

    r2 = ra.auditar(p2)
    t2 = " | ".join(v["trecho"] for v in r2["violacoes"])
    check("linha de árvore de plano fica fora da régua", LONGO[:40] not in t2 or
          all(v["onde"] != "li.pt-item" for v in r2["violacoes"]))
    check("a lista da árvore não conta bullets",
          not any(v["regra"] == ra.R_BULLETS for v in r2["violacoes"]))
    check("texto fora da árvore continua na régua",
          any(v["regra"] == ra.R_TETO for v in r2["violacoes"]))

    # ── varredura + filtro por data ───────────────────────────────────────
    escreve(d, "mao.html", "<html><body><p>%s</p></body></html>" % LONGO)
    todas = ra.varrer(d)
    check("varre as três páginas", len(todas) == 3)
    check("página digitada à mão volta na lista, sem perfil e sem violação",
          any(p["perfil"] is None and p["violacoes"] == [] for p in todas))
    check("--desde no futuro não devolve nada", ra.varrer(d, "2099-01-01") == [])

    # ── o comando de verdade, pelo caminho real ───────────────────────────
    exe = os.path.join(AQUI, "regua_audit.py")
    r = subprocess.run([sys.executable, exe, "paginas", "--dir", d],
                       capture_output=True, text=True)
    check("`paginas` sai 1 quando há violação", r.returncode == 1)
    check("a saída traz arquivo, regra e trecho",
          "2026-08-03-relatorio.html" in r.stdout and ra.R_TETO in r.stdout
          and LONGO[:30] in r.stdout)
    check("a saída conta por regra", "📊" in r.stdout and "duas-frases" in r.stdout)
    check("a saída declara o que ficou fora do alcance",
          "sem perfil de gerador" in r.stdout)

    limpo = tempfile.mkdtemp(prefix="regua-audit-ok-")
    escreve(limpo, "ok.html", '<html><body><div class="ident-strip">a</div>'
                              "<p>bullet curto</p></body></html>")
    r = subprocess.run([sys.executable, exe, "paginas", "--dir", limpo],
                       capture_output=True, text=True)
    check("`paginas` sai 0 quando não há violação", r.returncode == 0)

    r = subprocess.run([sys.executable, exe, "paginas", "--dir", d, "--json"],
                       capture_output=True, text=True)
    check("--json devolve JSON parseável", r.stdout.lstrip().startswith("["))

    # ── veredito: cada mudança do dia vira conforme/em desacordo ──────────
    linhas = ra.veredito(d, "2026-08-03", ra.REPO)
    check("o veredito cobre os cinco geradores", len(linhas) == len(ra.GERADORES))
    check("todo gerador sai marcado",
          all(x["veredito"] in ra.MARCA for x in linhas))
    check("gerador com mudança e página suja fica em desacordo",
          all(x["veredito"] != "conforme" or x["violacoes"] == 0 for x in linhas))
    check("todo veredito vem com motivo escrito",
          all(x["motivo"].strip() for x in linhas))
    check("mudança sem página do gerador não é declarada conforme",
          all(x["veredito"] != "conforme" or x["paginas"] for x in linhas))

    r = subprocess.run([sys.executable, exe, "veredito", "--dir", d,
                        "--desde", "2026-08-03"], capture_output=True, text=True)
    check("`veredito` imprime os cinco geradores",
          all(g in r.stdout for g, _ in ra.GERADORES))
    check("`veredito` imprime o rótulo e o motivo",
          "motivo:" in r.stdout and ("CONFORME" in r.stdout or "DESACORDO" in r.stdout))

    # ── a régua é UMA só: chamada, nunca redigitada ───────────────────────
    with open(exe, encoding="utf-8") as f:
        fonte = f.read()
    check("o teto não é redigitado aqui", "140" not in fonte.replace("BULLET_MAX", ""))
    check("quem julga o texto é o erros_de_estilo do regua_texto",
          "rt.erros_de_estilo(" in fonte)
    check("nenhuma checagem da régua é reimplementada aqui",
          "_DUAS_FRASES" not in fonte and "_CONECTIVO" not in fonte
          and "re.compile" not in fonte)
    # Se a redação de uma mensagem mudar lá, ela cai no genérico — e esta checagem
    # avisa, em vez de a violação virar "outra checagem da régua" em silêncio.
    AMOSTRAS = [("pagina", LONGO), ("pagina", "Uma frase. Outra frase."),
                ("pagina", "e abre com conectivo"), ("pagina", ["item"] * 7),
                ("slide", " ".join(["palavra"] * (rt.SLIDE_PALAVRAS + 1)))]
    vistas, ok = set(), True
    for perfil, v in AMOSTRAS:
        msgs = rt.erros_de_estilo(v, "x", perfil)
        ok = ok and bool(msgs)
        for m in msgs:
            r_ = ra.regra_de(m)
            vistas.add(r_)
            ok = ok and r_ != "estilo" and r_ in ra.REGRAS
    check("toda mensagem da régua tem código de regra aqui", ok)
    check("as cinco checagens da régua são reconhecidas uma a uma",
          {ra.R_TETO, ra.R_BULLETS, ra.R_PALAVRAS, "duas-frases", "conectivo"} <= vistas)

    # ── veredito: mudança sem commit não pode sumir ───────────────────────
    repo, alvo = repo_de_mentira()
    muds = ra.mudancas(repo, alvo, "2099-01-01")
    check("arquivo modificado e não commitado conta como mudança", len(muds) == 1)
    check("a mudança da árvore diz que não foi commitada",
          bool(muds) and "árvore" in muds[0] and "linhas" in muds[0])
    check("arquivo novo fora do git também conta",
          ra.mudancas(repo, "plugins/visual/lib/visual_page.py", "2099-01-01")
          == ["árvore · arquivo novo, ainda fora do git"])
    check("arquivo intocado continua sem mudança",
          ra.mudancas(repo, "plugins/slides/lib/md2deck.py", "2099-01-01") == [])

    limpo2 = tempfile.mkdtemp(prefix="regua-audit-br-")
    escreve(limpo2, "branches.html", BRANCHES)
    vs = {x["gerador"]: x for x in ra.veredito(limpo2, "2099-01-01", repo)}
    check("gerador mexido sem commit sai julgado, não 'sem mudança'",
          vs[alvo]["veredito"] == "conforme")
    check("o veredito da mudança sem commit vem com motivo",
          "página" in vs[alvo]["motivo"])
    check("gerador intocado continua sem mudança",
          vs["plugins/slides/lib/md2deck.py"]["veredito"] == "sem mudança")

    r = subprocess.run([sys.executable, exe, "veredito", "--dir", limpo2,
                        "--desde", "2099-01-01", "--repo", repo],
                       capture_output=True, text=True)
    check("a saída mostra a mudança que ainda não é commit", "árvore ·" in r.stdout)

    print()
    print("FALHOU: %d" % len(FAILS) if FAILS else "OK")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
