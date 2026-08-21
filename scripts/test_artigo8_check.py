#!/usr/bin/env python3
"""A suíte do cobrador do Artigo 8 — inclusive a prova anti-tautologia.

A régua da casa: cada padrão tem um caso que SABOTA a skill de mentira e exige
que o cobrador reprove. E a sabotagem é ancorada na LINHA que ela remove — o
teste guarda a linha literal, tira ela do arquivo, e o veredito tem que virar.
Se a suíte continuar verde com a skill sabotada, ela não estava medindo nada.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import artigo8_check as a8  # noqa: E402

OK = [0]
FAILS = []


def check(nome, cond):
    OK[0] += 1
    print("  %s %s" % ("ok  " if cond else "FALHOU", nome))
    if not cond:
        FAILS.append(nome)


def regras(src):
    return sorted(f["rule"] for f in a8.julga("x", src, "x/SKILL.md"))


# ── o que ele lê, e o que ele deixa em paz ───────────────────────────────────
print("o recorte: só bloco de comando conta")
check("bloco de comando é lido",
      regras("```bash\npython3 plugins/x/lib/y.py\n```\n") == ["A1-caminho-local"])
check("bloco de python NÃO é comando de terminal",
      regras("```python\nimport plugins/x/lib\n```\n") == [])
check("crase em linha de prosa TAMBÉM é comando (a forma dominante nas skills)",
      regras("rode `python3 plugins/x/lib/y.py`\n") == ["A1-caminho-local"])
check("crase que não abre com executável continua sendo prosa",
      regras("edite o `plugins/x/plugin.json` e o `<nome-do-plugin>`\n") == [])
check("crase inline com $VAR nua reprova",
      regras('rode `python3 "${CLAUDE_PLUGIN_ROOT}/lib/x.py"`\n') == ["A3-variavel-vazia"])
check("crase inline com placeholder que a MESMA linha só mostra não se autodefine",
      regras("rode `git tag <nome-da-tag>` agora\n") == ["A2-placeholder-orfao"])
check("...mas definido em OUTRA linha de prosa, passa",
      regras("O <nome-da-tag> é o que você escolher.\nrode `git tag <nome-da-tag>`\n") == [])
check("isenção na linha de prosa silencia o comando em crase",
      regras("rode `python3 plugins/x/lib/y.py`  <!-- artigo8-ok: exemplo interno -->\n") == [])
check("comentário dentro do bloco não é comando",
      regras("```bash\n# veja plugins/x/lib/y.py\n```\n") == [])

print("os três padrões")
check("A1 — caminho que só existe neste repositório",
      "A1-caminho-local" in regras("```sh\nbash plugins/ship/hooks/z.sh\n```\n"))
check("A2 — placeholder que ninguém define",
      regras("```bash\ngit tag <nome-da-tag>\n```\n") == ["A2-placeholder-orfao"])
check("A2 — placeholder definido na prosa do arquivo passa",
      regras("<nome-da-tag> é o nome que você escolher.\n"
             "```bash\ngit tag <nome-da-tag>\n```\n") == [])
check("A3 — variável que ninguém deriva no bloco",
      regras('```bash\npython3 "$CLAUDE_PLUGIN_ROOT/lib/x.py"\n```\n') == ["A3-variavel-vazia"])
check("A3 — variável derivada no próprio bloco passa",
      regras('```bash\nROOT=$(git rev-parse --show-toplevel)\npython3 "$ROOT/lib/x.py"\n```\n') == [])
check("A3 — variável do ambiente de qualquer máquina passa",
      regras('```bash\ncat "$HOME/.claude/settings.json"\n```\n') == [])
check("redirecionamento não é placeholder", regras("```bash\nsort < a.txt\n```\n") == [])
check("isenção declarada silencia o achado",
      regras("```bash\npython3 plugins/x/lib/y.py  # artigo8-ok: exemplo interno\n```\n") == [])

# ── sabotagem ancorada na LINHA que ela remove ───────────────────────────────
print("prova anti-tautologia — a skill sabotada REPROVA")
LINHA_QUE_DEFINE = "O `<nome-da-tag>` é o nome que você escolher para a tag."
SKILL_SA = ("---\nname: x\n---\n"
            + LINHA_QUE_DEFINE + "\n"
            "```bash\ngit tag <nome-da-tag>\n```\n")
check("com a linha que define o placeholder, o cobrador aprova", regras(SKILL_SA) == [])
sabotada = "\n".join(ln for ln in SKILL_SA.splitlines() if ln != LINHA_QUE_DEFINE) + "\n"
check("removida a linha `%s`, o cobrador reprova" % LINHA_QUE_DEFINE,
      regras(sabotada) == ["A2-placeholder-orfao"])

# ── o retrato: dívida antiga passa, padrão novo barra ────────────────────────
print("o retrato — só o que PIOROU reprova")
TMP = tempfile.mkdtemp(prefix="a8-")
try:
    d = os.path.join(TMP, "plugins", "x", "skills", "x")
    os.makedirs(d)
    alvo = os.path.join(d, "SKILL.md")
    with open(alvo, "w", encoding="utf-8") as fh:
        fh.write("```bash\npython3 plugins/x/lib/velho.py\n```\n")
    velho = a8.varre(TMP)
    check("a varredura acha a dívida antiga", len(velho["findings"]) == 1)
    conhecidos = {a8.chave(f) for f in velho["findings"]}

    with open(alvo, "a", encoding="utf-8") as fh:
        fh.write("```bash\npython3 plugins/x/lib/novo.py\n```\n")
    agora = a8.varre(TMP)
    novos = [f for f in agora["findings"] if a8.chave(f) not in conhecidos]
    check("o achado NOVO aparece", len(novos) == 1)
    check("...e a dívida antiga não volta a reprovar",
          len(agora["findings"]) == 2 and novos[0]["quote"].endswith("novo.py"))

    # a linha anda sem o achado virar novo — a identidade não pode ser a linha
    with open(alvo, "w", encoding="utf-8") as fh:
        fh.write("prosa nova\n\n```bash\npython3 plugins/x/lib/velho.py\n```\n")
    desloc = a8.varre(TMP)
    check("achado que só mudou de linha continua sendo o mesmo",
          all(a8.chave(f) in conhecidos for f in desloc["findings"]))

    # ── a catraca DESCE: conserto abaixa o retrato ───────────────────────────
    base_tmp = os.path.join(TMP, "baseline.json")
    with open(base_tmp, "w", encoding="utf-8") as fh:
        json.dump(agora, fh)
    with open(alvo, "w", encoding="utf-8") as fh:
        fh.write("```bash\npython3 plugins/x/lib/velho.py\n```\n")   # o novo foi consertado
    orig_raiz, orig_base = a8.RAIZ, a8.BASELINE
    a8.RAIZ, a8.BASELINE = TMP, base_tmp
    try:
        rc = a8.main(["--check"])
    finally:
        a8.RAIZ, a8.BASELINE = orig_raiz, orig_base
    with open(base_tmp, encoding="utf-8") as fh:
        rebaixado = json.load(fh)
    check("--check com dívida consertada sai 0", rc == 0)
    check("...e o retrato DESCE junto (o ponto consertado sai)",
          len(rebaixado["findings"]) == 1)

    # e o texto reintroduzido depois volta a REPROVAR — a catraca fechou a porta
    with open(alvo, "a", encoding="utf-8") as fh:
        fh.write("```bash\npython3 plugins/x/lib/novo.py\n```\n")
    revolta = a8.varre(TMP)
    conhecidos2 = {a8.chave(f) for f in rebaixado["findings"]}
    check("texto reintroduzido depois do conserto REPROVA de novo",
          [f for f in revolta["findings"] if a8.chave(f) not in conhecidos2])
finally:
    shutil.rmtree(TMP, ignore_errors=True)

# ── a linha de comando ───────────────────────────────────────────────────────
print("a linha de comando")
r = subprocess.run([sys.executable, os.path.join(AQUI, "artigo8_check.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   cwd=RAIZ, stdin=subprocess.DEVNULL, start_new_session=True)
check("--check contra o retrato do repo sai 0 (nada piorou)", r.returncode == 0)
check("...e diz quantas skills varreu", "skills varridas" in r.stdout)
r = subprocess.run([sys.executable, os.path.join(AQUI, "artigo8_check.py"), "--json"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   cwd=RAIZ, stdin=subprocess.DEVNULL, start_new_session=True)
check("--json sai medida crua legível", json.loads(r.stdout)["skills"] > 10)
with open(a8.BASELINE, encoding="utf-8") as fh:
    base = json.load(fh)
check("o retrato gravado tem os mesmos achados de hoje",
      len(base["findings"]) == len(a8.varre()["findings"]))

print()
if FAILS:
    print("FALHOU (%d de %d):" % (len(FAILS), OK[0]))
    for f in FAILS:
        print("  - %s" % f)
    sys.exit(1)
print("test_artigo8_check: %d asserts ok ✓" % OK[0])
