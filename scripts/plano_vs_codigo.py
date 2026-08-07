#!/usr/bin/env python3
"""plano_vs_codigo.py — acusa passo ABERTO cujo critério de pronto JÁ está satisfeito.

Um passo que continua "todo" no plano depois de o trabalho ter entrado no código
faz a sessão seguinte refazer tudo do zero. Este script lê os planos
(`.claude/plans/*.plan.json`, JSON direto — não importa `plan_state.py`), pega
cada passo que não está `done`, e pergunta ao disco se o critério do campo
`pronto` já se cumpre. Se cumpre, plano e código discordam.

O campo `pronto` tem três formas neste repositório, e só duas são julgáveis:

  1. COMANDO — o texto abre com um trecho entre crases: "`bash x.sh` sai 0 …".
     Roda o comando na raiz do projeto; sair 0 quer dizer critério cumprido.
  2. CAMINHO — o texto inteiro é um `arquivo` ou `arquivo:linha`. Confere a
     existência (e, com linha, que o arquivo tenha aquela linha).
  3. PROSA — qualquer outra coisa. NÃO dá para automatizar, e chamar de
     "coerente" o que não foi checado é pior do que não checar: some do radar
     com cara de conferido. Sai como "não verificável" e não decide nada.

Comando com efeito colateral aparente (escrita, remoção, rede, git que altera)
também vira "não verificável" — uma checagem não muda o repositório que audita.

Saída: 0 quando nada diverge, 1 quando há divergência.

Uso:
    python3 scripts/plano_vs_codigo.py                 # os planos deste repo
    python3 scripts/plano_vs_codigo.py <dir-de-planos>
    python3 scripts/plano_vs_codigo.py --json

stdlib only (requisito do repo).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(AQUI)
PLANOS = os.path.join(ROOT, ".claude", "plans")

# comando entre crases logo no começo do critério
RE_COMANDO = re.compile(r"^\s*`([^`]+)`")
# o critério INTEIRO é um caminho, com ou sem :linha
RE_CAMINHO = re.compile(r"^\s*`?([\w./@-]+/[\w./@-]+\.\w+)(?::(\d+))?`?\s*$")
# o que uma checagem não roda
PERIGO = re.compile(
    r"(^|[;&|\s])(rm|mv|cp|install|curl|wget|ssh|scp|npm|pip|claude)\b"
    r"|>\s*\S|\bgit\s+(commit|push|add|checkout|reset|clean|rebase|merge|tag)\b"
)

TIMEOUT = 30


def _itens(no):
    """Todo passo do plano, em qualquer nível de aninhamento."""
    if isinstance(no, dict):
        if "pronto" in no and "id" in no:
            yield no
        for v in no.values():
            for it in _itens(v):
                yield it
    elif isinstance(no, list):
        for v in no:
            for it in _itens(v):
                yield it


def classifica(pronto):
    """('comando'|'caminho'|'prosa', payload)."""
    m = RE_CAMINHO.match(pronto)
    if m:
        return "caminho", (m.group(1), int(m.group(2)) if m.group(2) else None)
    m = RE_COMANDO.match(pronto)
    if m:
        return "comando", m.group(1).strip()
    return "prosa", None


def cumprido_caminho(alvo, root):
    caminho, linha = alvo
    p = os.path.join(root, caminho)
    if not os.path.isfile(p):
        return False
    if linha is None:
        return True
    with open(p, "r", encoding="utf-8", errors="replace") as fh:
        return sum(1 for _ in fh) >= linha


def cumprido_comando(cmd, root):
    """True/False se deu para julgar; None quando o comando não é rodável."""
    if PERIGO.search(cmd):
        return None
    try:
        r = subprocess.run(cmd, shell=True, cwd=root, timeout=TIMEOUT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    return r.returncode == 0


def avalia(item, root):
    """Devolve o veredito de um passo aberto: divergente, coerente ou opaco."""
    forma, alvo = classifica(item.get("pronto") or "")
    if forma == "caminho":
        cumprido = cumprido_caminho(alvo, root)
    elif forma == "comando":
        cumprido = cumprido_comando(alvo, root)
    else:
        cumprido = None
    if cumprido is None:
        veredito = "nao-verificavel"
    elif cumprido:
        veredito = "divergente"
    else:
        veredito = "coerente"
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "status": item.get("status"),
        "pronto": item.get("pronto"),
        "forma": forma,
        "veredito": veredito,
    }


def varre(plans_dir=PLANOS, root=ROOT):
    achados = []
    for f in sorted(glob.glob(os.path.join(plans_dir, "*.plan.json"))):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                plano = json.load(fh)
        except (ValueError, OSError):
            continue
        for item in _itens(plano):
            if item.get("status") == "done":
                continue
            a = avalia(item, root)
            a["plano"] = os.path.basename(f)
            achados.append(a)
    return achados


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plans_dir", nargs="?", default=PLANOS)
    ap.add_argument("--root", default=None,
                    help="raiz onde os critérios são conferidos (padrão: raiz do repo)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = args.root or ROOT
    achados = varre(args.plans_dir, root)
    divergentes = [a for a in achados if a["veredito"] == "divergente"]
    opacos = [a for a in achados if a["veredito"] == "nao-verificavel"]

    if args.json:
        print(json.dumps(achados, ensure_ascii=False, indent=2))
    else:
        for a in divergentes:
            print("DIVERGE  %s %s — o passo está %s, mas o critério já se cumpre: %s"
                  % (a["plano"], a["id"], a["status"], a["pronto"]))
        print("plano_vs_codigo: %d passo(s) aberto(s) · %d divergência(s) · "
              "%d não verificável(is)" % (len(achados), len(divergentes), len(opacos)))
    return 1 if divergentes else 0


if __name__ == "__main__":
    sys.exit(main())
