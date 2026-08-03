#!/usr/bin/env python3
"""Checagem do regua_call_check.py — o gate que impede página fora da régua.

O teste central é o gerador de mentira: um .py que monta HTML e NÃO chama a
régua tem que ser barrado, e o mesmo arquivo com a chamada tem que passar.
Os literais de HTML são montados por concatenação de propósito — assim este
arquivo não vira, ele mesmo, um "gerador" aos olhos do detector.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regua_call_check as G  # noqa: E402

ok = 0
TMP = tempfile.mkdtemp(prefix="regua-call-")


def check(nome, cond):
    global ok
    assert cond, "FALHOU: %s" % nome
    ok += 1


def arquivo(nome, corpo):
    p = os.path.join(TMP, nome)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(corpo)
    return p


DOCTYPE = "<!DOC" + "TYPE html>"
DIV = "<div " + 'class="hd">'
TAG_HTML = "<htm" + "l lang=pt>"
TEMPLATE = "temp" + "late.html"

# ─── o gerador de mentira: monta página, não chama a régua ───────────────────
SEM = "def pagina(t):\n    return '" + DOCTYPE + "' + '" + DIV + "' + t\n"
COM = ("from regua_texto import erros_de_estilo\n\n"
       "def pagina(t):\n"
       "    assert not erros_de_estilo(t, 'titulo', 'pagina')\n"
       "    return '" + DOCTYPE + "' + '" + DIV + "' + t\n")

a = G.analisa(arquivo("gerador_sem.py", SEM))
check("gerador sem a chamada e BARRADO", a is not None)
check("o achado diz o arquivo, a linha e o sinal",
      a and all(k in a for k in ("file", "line", "signal", "excerpt", "fix")))
check("o sinal apontado e o doctype", a and a["signal"] == "doctype")
check("a linha apontada e a que monta o HTML", a and a["line"] == 2)

check("gerador COM a chamada passa", G.analisa(arquivo("gerador_com.py", COM)) is None)

# a chamada vale mesmo vindo depois do HTML — ordem no arquivo não é contrato
TARDE = "def q():\n    return '" + DIV + "'\n"
check("HTML sem chamada nenhuma e BARRADO", G.analisa(arquivo("tarde.py", TARDE)))
check("HTML antes e chamada depois passa",
      G.analisa(arquivo("tarde_ok.py", TARDE + "\nimport regua_texto\n")) is None)

# ─── os quatro sinais mecânicos ──────────────────────────────────────────────
for sid, corpo in (("doctype", "X = '" + DOCTYPE + "'\n"),
                   ("tag-html", "X = '" + TAG_HTML + "'\n"),
                   ("div-com-classe", "X = '" + DIV + "'\n"),
                   ("template-html", "T = os.path.join(D, '" + TEMPLATE + "')\n")):
    achado = G.analisa(arquivo("sinal_%s.py" % sid, corpo))
    check("sinal %s acusa" % sid, achado is not None and achado["signal"] == sid)

# o sinal do template é o literal do arquivo, não a palavra solta
check("'template' sozinho nao e sinal",
      G.analisa(arquivo("so_palavra.py", "T = 'template' + '/x'\n")) is None)

# ─── o que fica fora ─────────────────────────────────────────────────────────
check("arquivo de teste fica fora (HTML em teste e fixture)",
      G.analisa(arquivo("test_falso.py", SEM)) is None)
check("isencao com motivo isenta",
      G.analisa(arquivo("isento.py", "# regua" + "-ok: le HTML alheio, nao emite\n" + SEM))
      is None)
check("isencao sem motivo NAO isenta",
      G.analisa(arquivo("isento_mudo.py", "# regua" + "-ok:\n" + SEM)) is not None)
check("arquivo sem HTML nenhum passa",
      G.analisa(arquivo("neutro.py", "def soma(a, b):\n    return a + b\n")) is None)

# ─── fail-open: sem git resolvível, nada é acusado ───────────────────────────
_orig = G.ROOT
G.ROOT = os.path.join(TMP, "nao-e-repo")
os.makedirs(G.ROOT, exist_ok=True)
check("fora de repo git, zero achado (fail-open)", G.varre(staged=True) == [])
G.ROOT = _orig

# ─── o gate roda de verdade no repo ──────────────────────────────────────────
achados = G.varre()
check("varre() devolve lista", isinstance(achados, list))

shutil.rmtree(TMP, ignore_errors=True)
print("test_regua_call_check: %d asserts ok ✓  (repo: %d gerador(es) fora da régua hoje)"
      % (ok, len(achados)))
