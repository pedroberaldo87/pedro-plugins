#!/usr/bin/env python3
"""custo_check.py — reprova afirmação de custo em hook que não diz QUANDO nem SOBRE QUANTO.

Um comentário de hook que diz "~6ms, aceito" vira lei sem prazo de validade. O caso
real está em `plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh`: a poda foi
aprovada com "~6ms com ~1500 entradas, aceito", a máquina cresceu para 343.936
entradas e o mesmo código passou a custar 16s POR CHAMADA — o número não estava
errado quando foi feito, envelheceu. Número solto não envelhece à vista de ninguém;
número com data e tamanho de amostra, sim.

O que este script cobra: todo comentário de hook que afirma custo (uma duração perto
de uma palavra de custo — custa, leva, gasta, overhead, por chamada) tem que trazer,
no MESMO bloco de comentário, a data da medição e o tamanho da amostra.

O que conta é sinal MECÂNICO, não julgamento:
  - duração    → `~50ms`, `0,6s`, `16s`, `4min`, `100s`
  - custo      → custo/custa/custou/custava, leva/levava/levou, gasta, overhead,
                 "por chamada", "zero token"
  - data       → `2026-08-14` ou `31/07`
  - amostra    → número + substantivo contável (1500 entradas, 559 arquivos…),
                 ou a palavra "amostra"/"n="

Uso:
    python3 scripts/custo_check.py              # varre os hooks da casa
    python3 scripts/custo_check.py --conformes  # + a lista de quem já cumpre
    python3 scripts/custo_check.py --json
    python3 scripts/custo_check.py <arquivo>…   # varre caminhos avulsos

Isenção: afirmação que não é medição ganha `# custo-ok: <motivo>` na própria linha.
O motivo é obrigatório.

stdlib only (requisito do repo).
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZES = [".claude/hooks", "plugins"]
EXTS = (".sh", ".bash", ".py")

DURACAO = re.compile(r"~?\d+(?:[.,]\d+)?\s*(?:ms|s|seg|segundos?|min\d*|minutos?|h)\b")
CUSTO = re.compile(
    r"\bcust(?:o|os|a|am|ou|ava|avam)\b|\blev(?:a|am|ava|avam|ou|aram)\b"
    r"|\bgast(?:a|am|ou|ava)\b|\boverhead\b|por chamada|zero token",
    re.I,
)
DATA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}(?:/\d{2,4})?\b")
AMOSTRA = re.compile(
    r"\bamostra\b|\bn\s*=\s*\d|~?\d[\d.,]*\s+"
    r"(?:entradas|arquivos|linhas|chamadas|sess\w+|commits|rodadas|su[ií]tes|"
    r"casos|n[óo]s|itens|plugins|projetos|repos|turnos|processos)\b",
    re.I,
)
ISENCAO = re.compile(r"custo-ok:\s*\S")

CONSERTO = ("acrescentar no mesmo bloco a data da medição (2026-08-14) e o tamanho "
            "da amostra que produziu o número (ex.: 'com ~1500 entradas')")


def comentario(linha):
    return linha.lstrip().startswith("#")


def blocos(linhas):
    """→ [(inicio, [linhas])] de cada bloco contíguo de comentário."""
    out, atual, ini = [], [], 0
    for n, linha in enumerate(linhas, 1):
        if comentario(linha):
            if not atual:
                ini = n
            atual.append(linha)
        elif atual:
            out.append((ini, atual))
            atual = []
    if atual:
        out.append((ini, atual))
    return out


def analisa(full, path=None):
    """→ (achados, conformes) das afirmações de custo do arquivo."""
    path = path or full
    try:
        with open(full, encoding="utf-8") as fh:
            linhas = fh.readlines()
    except (UnicodeDecodeError, OSError):
        return [], []

    achados, conformes = [], []
    for ini, bloco in blocos(linhas):
        texto = "".join(bloco)
        for i, linha in enumerate(bloco):
            if not (DURACAO.search(linha) and CUSTO.search(linha)):
                continue
            if ISENCAO.search(linha):
                continue
            item = {"file": path, "line": ini + i,
                    "excerpt": linha.strip().lstrip("#").strip()[:120]}
            faltas = []
            if not DATA.search(texto):
                faltas.append("data da medição")
            if not AMOSTRA.search(texto):
                faltas.append("tamanho da amostra")
            if faltas:
                item["missing"] = faltas
                item["fix"] = CONSERTO
                achados.append(item)
            else:
                conformes.append(item)
    return achados, conformes


def alvos_padrao():
    out = []
    for raiz in RAIZES:
        for dirpath, _, nomes in os.walk(os.path.join(ROOT, raiz)):
            if os.path.basename(dirpath) != "hooks" and "/hooks/" not in dirpath + "/":
                continue
            for nome in nomes:
                if nome.endswith(EXTS):
                    out.append(os.path.relpath(os.path.join(dirpath, nome), ROOT))
    return sorted(out)


def varre(alvos=None):
    achados, conformes = [], []
    for path in (alvos or alvos_padrao()):
        full = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if not os.path.isfile(full):
            continue
        a, c = analisa(full, path)
        achados += a
        conformes += c
    return achados, conformes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conformes", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("alvos", nargs="*")
    args = ap.parse_args()

    achados, conformes = varre(args.alvos)

    if args.json:
        print(json.dumps({"ok": not achados, "count": len(achados),
                          "findings": achados, "conformes": conformes},
                         ensure_ascii=False, indent=1))
        return 1 if achados else 0

    if conformes or args.conformes:
        print("custo-check: %d afirmação(ões) em conformidade (data + amostra)"
              % len(conformes))
        if args.conformes:
            for c in conformes:
                print("  %s:%d — %s" % (c["file"], c["line"], c["excerpt"]))

    if not achados:
        print("custo-check: OK — nenhuma afirmação de custo sem data e sem amostra")
        return 0

    print("custo-check: %d afirmação(ões) de custo sem prova\n" % len(achados))
    for a in achados:
        print("  %s:%d — falta %s" % (a["file"], a["line"], " e ".join(a["missing"])))
        print("    %s" % a["excerpt"])
    print("\n  conserto: %s" % CONSERTO)
    print("  isenção legítima: acrescente `# custo-ok: <motivo>` na linha.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                      # fail-open: erro de infra não trava commit
        print("custo-check: não rodou (%s) — seguindo" % e, file=sys.stderr)
        sys.exit(0)
