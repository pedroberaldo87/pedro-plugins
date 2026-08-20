#!/usr/bin/env python3
"""anti_slop_inventario.py — a varredura anti-slop da codebase inteira (F15.6 · R-25).

A doença que o dono nomeou é uma só: duplicar, cravar e espalhar até virar dívida,
em vez de amarrar num lugar e tornar recursivo. O caminho da doc foi UMA classe
dessa doença — esta varredura caça as outras quatro na codebase inteira, linha a
linha, e devolve o inventário POR CLASSE com contagem, dono (a fonte única que
deveria mandar) e de-para (o que o ponto escreve hoje, o que passaria a perguntar).

Ele MEDE e LISTA. Não conserta nada, e nunca reprova commit: quem morde é o
cobrador de cada classe, que é o passo seguinte (F15.7).

    python3 scripts/anti_slop_inventario.py             # inventário legível
    python3 scripts/anti_slop_inventario.py --json      # o mesmo, para máquina
    python3 scripts/anti_slop_inventario.py --classe A  # só uma classe, com os pontos

O universo varrido é o que o git rastreia, menos o que é saída de ferramenta
(`graphify-out/`), menos os próprios relatórios (`.claude/reports/`) e menos este
arquivo — medir o relatório e o medidor faria a contagem se citar.
"""
import argparse
import json
import os
import re
import subprocess
import sys

for _canal in (sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORA = ("graphify-out/", ".claude/reports/", "scripts/anti_slop_inventario")


def universo():
    """Os arquivos de texto que o git rastreia, menos saída de ferramenta."""
    saida = subprocess.run(["git", "-C", RAIZ, "ls-files"],
                           capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, start_new_session=True).stdout
    alvos = []
    for rel in saida.splitlines():
        if not rel or rel.startswith(FORA):
            continue
        caminho = os.path.join(RAIZ, rel)
        try:
            with open(caminho, "r", encoding="utf-8") as fh:
                texto = fh.read()
        except (OSError, UnicodeDecodeError):
            continue  # binário ou ilegível: não é linha de código nem de prosa
        alvos.append((rel, texto))
    return alvos


def _pontos(alvos, padrao, filtro_rel=None):
    """(rel, linha, trecho) de cada casamento — a prova crua de cada contagem."""
    achados = []
    for rel, texto in alvos:
        if filtro_rel and not filtro_rel(rel):
            continue
        for n, linha in enumerate(texto.splitlines(), 1):
            for m in padrao.finditer(linha):
                achados.append((rel, n, m.group(0)))
    return achados


# ── A · caminho de doc cravado ────────────────────────────────────────────────
# O ponto escreve o lugar da doc como texto. Casa antiga (.claude/docs) e casa
# nova (docs/) são a MESMA pergunta, e quem responde tem que ser o resolvedor.
RE_CAMINHO = re.compile(r"\.claude/docs\b|(?<![\w./-])docs/(?=[\w*])")

# ── B · lista duplicada ───────────────────────────────────────────────────────
# O mesmo conjunto de nomes reescrito em vários arquivos. Duas listas caçadas:
# a dos docs canônicos e a dos plugins do catálogo.
DOCS_CANONICOS = ("architecture.md", "patterns.md", "runtime.md",
                  "data-stores.md", "durability.md", "constituicao.md",
                  "quality-goals.md")

# ── C · contagem escrita à mão ────────────────────────────────────────────────
# Número de quantidade cravado em prosa, sendo derivável por comando.
RE_CONTAGEM = re.compile(
    r"\b\d{2,5}\s+(plugins?|cópias|nós|arestas|comunidades|hooks|arquivos|"
    r"checagens|ocorrências|suítes|linhas|itens|pastas|skills)\b")

# ── D · valor copiado ─────────────────────────────────────────────────────────
# O mesmo valor gravado em dois lugares que precisam concordar: a versão de cada
# plugin (plugin.json ↔ marketplace.json) e o código vendorado (_shared ↔ cópia).


def classe_a(alvos):
    pontos = _pontos(alvos, RE_CAMINHO,
                     filtro_rel=lambda r: not r.startswith("_shared/lar_fingido"))
    return {
        "id": "A",
        "nome": "caminho de doc cravado",
        "dono": "_shared/ — o resolvedor único do caminho da doc (F15.1)",
        "de": "o literal `.claude/docs/x.md` ou `docs/x.md` escrito no arquivo",
        "para": "perguntar ao resolvedor: ele tenta docs/ e cai em .claude/docs/",
        "comando": "python3 scripts/anti_slop_inventario.py --classe A | grep -c '^      '",
        "pontos": pontos,
    }


def classe_b(alvos):
    pontos = []
    for rel, texto in alvos:
        quantos = sum(1 for nome in DOCS_CANONICOS if nome in texto)
        if quantos >= 3:
            pontos.append((rel, 0, f"lista de doc canônico ({quantos} nomes)"))
    catalogo = os.path.join(RAIZ, ".claude-plugin", "marketplace.json")
    nomes = []
    try:
        with open(catalogo, encoding="utf-8") as fh:
            nomes = [p["name"] for p in json.load(fh).get("plugins", [])]
    except (OSError, ValueError, KeyError):
        pass
    if nomes:
        for rel, texto in alvos:
            if rel.endswith("marketplace.json"):
                continue
            quantos = sum(1 for n in nomes if n in texto)
            if quantos >= 10:
                pontos.append((rel, 0, f"lista de plugin ({quantos} de {len(nomes)})"))
    return {
        "id": "B",
        "nome": "lista duplicada",
        "dono": ".claude-plugin/marketplace.json (plugins) · o índice do CLAUDE.md (docs)",
        "de": "a mesma enumeração reescrita à mão em cada arquivo que precisa dela",
        "para": "ler a lista da fonte na hora (json/glob), nunca recopiar os nomes",
        "comando": "python3 scripts/anti_slop_inventario.py --classe B | grep -c '^      '",
        "pontos": pontos,
    }


def classe_c(alvos):
    pontos = _pontos(alvos, RE_CONTAGEM,
                     filtro_rel=lambda r: r.endswith(".md"))
    return {
        "id": "C",
        "nome": "contagem escrita à mão",
        "dono": "scripts/readme_counts_check.py — o único que já recalcula da fonte",
        "de": "o número de quantidade cravado na frase e envelhecendo calado",
        "para": "a frase carrega o COMANDO que deriva o número, e um check recalcula",
        "comando": "python3 scripts/anti_slop_inventario.py --classe C | grep -c '^      '",
        "pontos": pontos,
    }


def classe_d(alvos):
    pontos = []
    catalogo = {}
    try:
        with open(os.path.join(RAIZ, ".claude-plugin", "marketplace.json"),
                  encoding="utf-8") as fh:
            catalogo = {p["name"]: p.get("version") for p in json.load(fh)["plugins"]}
    except (OSError, ValueError, KeyError):
        pass
    for rel, texto in alvos:
        if not rel.endswith(".claude-plugin/plugin.json") or rel.startswith(".claude-plugin/"):
            continue
        try:
            dado = json.loads(texto)
        except ValueError:
            continue
        nome, versao = dado.get("name"), dado.get("version")
        estado = "IGUAL" if catalogo.get(nome) == versao else \
                 f"DIVERGE (catálogo diz {catalogo.get(nome)})"
        pontos.append((rel, 0, f"{nome} {versao} · {estado}"))
    mapa = os.path.join(RAIZ, "scripts", "sync-shared.sh")
    try:
        with open(mapa, encoding="utf-8") as fh:
            bloco = re.search(r"^SPECS=\(.*?^\)", fh.read(), re.S | re.M)
        copias = len(re.findall(r"::", bloco.group(0))) if bloco else 0
    except OSError:
        copias = 0
    pontos.append(("scripts/sync-shared.sh", 0,
                   f"{copias} cópias vendoradas de _shared/ (com dono e cobrador)"))
    return {
        "id": "D",
        "nome": "valor copiado",
        "dono": "plugin.json de cada plugin (versão) · _shared/ (código vendorado)",
        "de": "o mesmo valor gravado em dois lugares que precisam concordar",
        "para": "o espelho é feito por programa (bump.py, sync-shared.sh) e conferido",
        "comando": "python3 scripts/anti_slop_inventario.py --classe D | grep -c '^      '",
        "pontos": pontos,
    }


def inventario():
    alvos = universo()
    classes = [classe_a(alvos), classe_b(alvos), classe_c(alvos), classe_d(alvos)]
    for c in classes:
        c["ocorrencias"] = len(c["pontos"])
        c["arquivos"] = len({p[0] for p in c["pontos"]})
    return {"arquivos_varridos": len(alvos), "classes": classes}


def imprime(inv, so_classe=None):
    print(f"varredura: {inv['arquivos_varridos']} arquivos rastreados "
          f"(sem graphify-out/, .claude/reports/ e o próprio medidor)\n")
    for c in inv["classes"]:
        if so_classe and c["id"] != so_classe:
            continue
        print(f"{c['id']} · {c['nome']}")
        print(f"    ocorrências : {c['ocorrencias']} em {c['arquivos']} arquivos")
        print(f"    dono        : {c['dono']}")
        print(f"    de          : {c['de']}")
        print(f"    para        : {c['para']}")
        print(f"    confere com : {c['comando']}")
        if so_classe:
            for rel, linha, trecho in c["pontos"]:
                alvo = f"{rel}:{linha}" if linha else rel
                print(f"      {alvo}  {trecho}")
        print()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--classe", choices=["A", "B", "C", "D"])
    args = ap.parse_args()
    inv = inventario()
    if args.json:
        print(json.dumps(inv, ensure_ascii=False, indent=2))
    else:
        imprime(inv, args.classe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
