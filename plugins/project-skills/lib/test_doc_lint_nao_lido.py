#!/usr/bin/env python3
"""doc_lint não pode dar verde para o que não leu (3ba4b516 · hsf_e4a9ea6f).

`--docs` com um caminho que não abre, ou um escopo sem doc nenhum, saía com "0 FAIL" e exit 0:
quem rodava o gate lia isso como "doc limpo". Aqui cada caso de leitura vazia sai com exit 2 e a
frase "NÃO LIDO"; o que foi lido continua com o contrato de sempre (exit 0 limpo; o exit 1 de FAIL é do test_doc_lint).

Roda com:  python3 plugins/project-skills/lib/test_doc_lint_nao_lido.py
"""
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(AQUI, "doc_lint.py")
ok = falhas = 0


def checa(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s %s" % (nome, detalhe))


def roda(raiz, *args):
    r = subprocess.run([sys.executable, LINT, "--project-root", raiz] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, timeout=120)
    return r.returncode, r.stdout, r.stderr


def doc(raiz, rel, corpo):
    p = os.path.join(raiz, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(corpo)


with tempfile.TemporaryDirectory(prefix="dlnl-") as td:
    doc(td, "docs/bom.md", "# Limpo\n\nsem ponteiro nem variável.\n")

    rc, out, err = roda(td, "--docs", "docs/bom.md")
    checa("doc lido e limpo: exit 0", rc == 0, "— rc=%s %s" % (rc, out))

    rc, out, err = roda(td, "--docs", "docs/nao-existe.md")
    checa("--docs que não abre: exit 2 (não 0)", rc == 2, "— rc=%s %s" % (rc, out))
    checa("--docs que não abre: diz NÃO LIDO e o caminho",
          "NÃO LIDO" in out + err and "docs/nao-existe.md" in out + err, "— %r %r" % (out, err))

    rc, out, err = roda(td, "--docs", "docs/bom.md", "docs/nao-existe.md")
    checa("um lido e um que não abre: exit 2", rc == 2, "— rc=%s" % rc)

    rc, out, err = roda(td, "--docs", "docs/nao-existe.md", "--json")
    try:
        dado = json.loads(out)
    except ValueError:
        dado = {}
    checa("--json: exit 2 e o caminho em `unread`",
          rc == 2 and dado.get("unread") == ["docs/nao-existe.md"], "— rc=%s %r" % (rc, out))

    os.makedirs(os.path.join(td, "docs", "pasta.md"))
    rc, out, err = roda(td, "--docs", "docs/pasta.md")
    checa("--docs que é pasta: exit 2", rc == 2, "— rc=%s" % rc)

with tempfile.TemporaryDirectory(prefix="dlnl-vazio-") as td:
    rc, out, err = roda(td)
    checa("escopo sem doc nenhum: exit 2, não '0 FAIL' verde", rc == 2, "— rc=%s %s" % (rc, out))
    checa("escopo sem doc nenhum: diz NÃO LIDO", "NÃO LIDO" in out + err, "— %r %r" % (out, err))

print("\n%d ok, %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
