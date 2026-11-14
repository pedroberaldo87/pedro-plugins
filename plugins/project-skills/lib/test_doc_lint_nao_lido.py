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
    doc(td, "notas/bom.md", "# Limpo\n\nsem ponteiro nem variável.\n")

    rc, out, err = roda(td, "--docs", "notas/bom.md")
    checa("doc lido e limpo: exit 0", rc == 0, "— rc=%s %s" % (rc, out))

    rc, out, err = roda(td, "--docs", "notas/nao-existe.md")
    checa("--docs que não abre: exit 2 (não 0)", rc == 2, "— rc=%s %s" % (rc, out))
    checa("--docs que não abre: diz NÃO LIDO e o caminho",
          "NÃO LIDO" in out + err and "notas/nao-existe.md" in out + err, "— %r %r" % (out, err))

    rc, out, err = roda(td, "--docs", "notas/bom.md", "notas/nao-existe.md")
    checa("um lido e um que não abre: exit 2", rc == 2, "— rc=%s" % rc)

    rc, out, err = roda(td, "--docs", "notas/nao-existe.md", "--json")
    try:
        dado = json.loads(out)
    except ValueError:
        dado = {}
    checa("--json: exit 2 e o caminho em `unread`",
          rc == 2 and dado.get("unread") == ["notas/nao-existe.md"], "— rc=%s %r" % (rc, out))

    os.makedirs(os.path.join(td, "docs", "pasta.md"))
    rc, out, err = roda(td, "--docs", "notas/pasta.md")
    checa("--docs que é pasta: exit 2", rc == 2, "— rc=%s" % rc)

    # quem lê só o stdout (log de CI, hook que captura uma stream) não pode ver um resumo verde
    rc, out, err = roda(td, "--docs", "notas/nao-existe.md")
    checa("--docs que não abre: o STDOUT diz NÃO LIDO e o caminho",
          "NÃO LIDO" in out and "notas/nao-existe.md" in out, "— %r" % out)
    checa("--docs que não abre: o STDOUT não traz o resumo verde '0 FAIL, 0 WARN'",
          "0 FAIL, 0 WARN" not in out, "— %r" % out)
    rc, out, err = roda(td, "--docs", "notas/bom.md", "notas/nao-existe.md")
    checa("um lido e um que não abre: o STDOUT diz NÃO LIDO e o caminho",
          "NÃO LIDO" in out and "notas/nao-existe.md" in out, "— %r" % out)
    rc, out, err = roda(td, "--docs", "notas/bom.md")
    checa("doc lido e limpo: o resumo segue como sempre", "1 doc(s), 0 FAIL, 0 WARN" in out, "— %r" % out)

with tempfile.TemporaryDirectory(prefix="dlnl-vazio-") as td:
    rc, out, err = roda(td)
    checa("escopo sem doc nenhum: exit 2, não '0 FAIL' verde", rc == 2, "— rc=%s %s" % (rc, out))
    checa("escopo sem doc nenhum: diz NÃO LIDO", "NÃO LIDO" in out + err, "— %r %r" % (out, err))
    checa("escopo sem doc nenhum: o STDOUT diz NÃO LIDO, não o resumo verde",
          "NÃO LIDO" in out and "0 FAIL, 0 WARN" not in out, "— %r" % out)

# Quem CHAMA o gate precisa saber o que o exit 2 quer dizer: sem isso, "o lint não rodou" é lido como erro
# de infraestrutura e ignorado, e o verde que não houve passa para o relatório.
RAIZ_PLUGIN = os.path.join(AQUI, "..")
for rel in ("skills/doc-touch/SKILL.md", "skills/doc/SKILL.md", "skills/doc/references/verification.md"):
    with open(os.path.join(RAIZ_PLUGIN, rel), encoding="utf-8") as fh:
        corpo = fh.read()
    i = corpo.find("doc_lint.py")
    trecho = corpo[i:i + 1800]
    checa("%s: o gate doc-lint diz o que o exit 2 (NÃO LIDO) significa" % rel,
          i >= 0 and "NÃO LIDO" in trecho and "exit 2" in trecho, "— trecho sem NÃO LIDO / exit 2")

print("\n%d ok, %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
