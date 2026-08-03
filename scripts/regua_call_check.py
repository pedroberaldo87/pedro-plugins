#!/usr/bin/env python3
"""regua_call_check.py — reprova gerador de página que não passa pela régua.

A régua de estilo (`_shared/regua_texto.py`, vinda de `.claude/docs/quality-goals.md`)
só vale para o texto que passa por ela. Um gerador novo monta HTML, emite texto
autoral e ninguém percebe que ele nasceu fora da regra — foi assim que cada
gerador ficou livre para inventar a própria forma. Este script é o gate: se o
arquivo Python monta página, ele tem que chamar o módulo compartilhado.

O que conta como "monta página" é sinal MECÂNICO, não julgamento: literal de
DOCTYPE, `<html`, `<div class=`, ou uso de um `template.html`.
O que conta como "chama a régua" também: importar `regua_texto` ou chamar
`erros_de_estilo`.

Uso:
    python3 scripts/regua_call_check.py              # varre os .py rastreados
    python3 scripts/regua_call_check.py --staged     # só o que está staged (pre-commit)
    python3 scripts/regua_call_check.py --json
    python3 scripts/regua_call_check.py <arquivo>…   # varre caminhos avulsos

Isenção: arquivo que casa o sinal sem ser gerador de texto ganha uma linha
`# regua-ok: <motivo>`. O motivo é obrigatório — isenção sem justificativa não vale.
Arquivo `test_*.py` fica fora: HTML dentro de teste é fixture, não emissão.

stdlib only (requisito do repo).
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sinal de que o arquivo MONTA página. Cada um foi visto no código real deste repo:
# md2deck aponta pro template.html, plan_state e branch_state costuram `<div class=`,
# report.py do fallow monta o documento inteiro.
SINAIS = [
    ("doctype", re.compile(r"<!\s*doctype\s+html", re.I)),
    ("tag-html", re.compile(r"<html[\s>]", re.I)),
    ("div-com-classe", re.compile(r"<div\s+class\s*=")),
    ("template-html", re.compile(r"template\.html")),
]

# Sinal de que ele PASSA pela régua: a importação do módulo compartilhado ou a
# chamada dela. As duas formas contam — `visual_page.py` importa e reexporta.
CHAMADA = re.compile(r"\bregua_texto\b|\berros_de_estilo\b")

ISENCAO = re.compile(r"regua-ok:\s*(\S.*?)\s*(?:-->)?\s*$")

CONSERTO = ("importar `erros_de_estilo` de regua_texto e cobrar cada campo de "
            "texto autoral antes de montar o HTML")


def arquivos(staged, alvos):
    """Os .py a varrer. Fail-open: sem git resolvível, devolve lista vazia."""
    if alvos:
        return list(alvos)
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged \
        else ["git", "ls-files"]
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    except OSError:
        return []
    if out.returncode != 0:
        return []
    return [p for p in out.stdout.splitlines() if p.endswith(".py")]


def analisa(full, path=None):
    """→ achado (dict) se o arquivo monta página sem chamar a régua, senão None."""
    path = path or full
    base = os.path.basename(path)
    if not base.endswith(".py") or base.startswith("test_"):
        return None
    try:
        with open(full, encoding="utf-8") as fh:
            linhas = fh.readlines()
    except (UnicodeDecodeError, OSError):
        return None

    achado = None
    for n, linha in enumerate(linhas, 1):
        if ISENCAO.search(linha):
            return None
        if CHAMADA.search(linha):
            return None
        if achado is None:
            for sid, padrao in SINAIS:
                m = padrao.search(linha)
                if m:
                    achado = {"file": path, "line": n, "signal": sid,
                              "match": m.group(0)[:40], "fix": CONSERTO,
                              "excerpt": linha.strip()[:120]}
                    break
    return achado


def varre(staged=False, alvos=None):
    achados = []
    for path in arquivos(staged, alvos):
        full = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if not os.path.isfile(full):
            continue
        a = analisa(full, path)
        if a:
            achados.append(a)
    return achados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("alvos", nargs="*")
    args = ap.parse_args()

    achados = varre(args.staged, args.alvos)

    if args.json:
        print(json.dumps({"ok": not achados, "count": len(achados),
                          "findings": achados}, ensure_ascii=False, indent=1))
        return 1 if achados else 0

    if not achados:
        print("regua-call-check: OK — todo gerador de página chama a régua")
        return 0

    print("regua-call-check: %d gerador(es) de página fora da régua\n" % len(achados))
    for a in achados:
        print("  %s:%d — monta HTML (%s) e não chama a régua"
              % (a["file"], a["line"], a["signal"]))
        print("    %s" % a["excerpt"])
    print("\n  conserto: %s" % CONSERTO)
    print("  a régua e os perfis estão em _shared/regua_texto.py")
    print("  isenção legítima: acrescente `# regua-ok: <motivo>` no arquivo.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                      # fail-open: erro de infra não trava commit
        print("regua-call-check: não rodou (%s) — seguindo" % e, file=sys.stderr)
        sys.exit(0)
