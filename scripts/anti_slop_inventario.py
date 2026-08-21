#!/usr/bin/env python3
"""anti_slop_inventario.py — a varredura anti-slop da codebase inteira (F15.6 · R-25).

A doença que o dono nomeou é uma só: duplicar, cravar e espalhar até virar dívida,
em vez de amarrar num lugar e tornar recursivo. O caminho da doc foi UMA classe
dessa doença — esta varredura caça as outras quatro na codebase inteira, linha a
linha, e devolve o inventário POR CLASSE com contagem, dono (a fonte única que
deveria mandar) e de-para (o que o ponto escreve hoje, o que passaria a perguntar).

Ele MEDE, LISTA e — desde o F15.7 — ACUSA REINCIDÊNCIA. Cada classe carrega a
situação dela (fonte única implementada, ou dívida declarada com dono nomeado) e um
TETO: a contagem do dia em que a classe foi inventariada. `--check` reprova quando a
classe passa do teto, ou seja, quando alguém acrescentou ocorrência nova da mesma
doença. Ele nunca conserta nada — teto só desce, e quem o abaixa é o conserto.

    python3 scripts/anti_slop_inventario.py             # inventário legível
    python3 scripts/anti_slop_inventario.py --json      # o mesmo, para máquina
    python3 scripts/anti_slop_inventario.py --classe A  # só uma classe, com os pontos
    python3 scripts/anti_slop_inventario.py --check     # reincidência: sai 1 se subiu

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

# O TETO DE CADA CLASSE — a contagem medida em 2026-08-20 (commit b9b3823), no molde do
# `.claude/desacoplamento.baseline.json`: dívida antiga passa, ocorrência NOVA reprova.
# Ele só desce, e quem o abaixa é o conserto que apagou pontos: baixou de verdade, edite
# aqui junto. Subir número aqui é legalizar reincidência — se for decisão do dono, ela
# vem escrita no relatório da classe, nunca só neste dicionário.
# B abaixou de 45 para 42 quando o retrato de baseline saiu da varredura (F28.3):
# retrato não é lista recopiada à mão, é medida gravada — a catraca desce junto.
# A abaixou de 319 para 114 na varredura do F15.2: os pontos que eram fixture de teste
# ganharam a isenção `casa-ok:` com motivo escrito, e a catraca desceu junto — o que resta
# é código de produção que ainda escreve a casa em vez de perguntar ao resolvedor.
# Antes disso, A abaixou de 322 para 319 quando a migração da doc (F15.5) apagou três pontos:
# a catraca desce junto com o conserto, senão a folga engole a próxima reincidência
# — foi exatamente isso que fez o cobrador do F15.3 passar verde numa mutação real
# (conta 319, teto 322, mutante 320: cabia na folga).
TETO = {"A": 0, "B": 42, "C": 138, "D": 24}

# A SITUAÇÃO DE CADA CLASSE (F15.7): ou a fonte única existe em código, ou a dívida está
# declarada com dono nomeado. Não há terceira opção — classe sem uma das duas é o próprio
# defeito que o inventário caça, agora dentro do medidor.
SITUACAO = {
    "A": ("fonte única IMPLEMENTADA — `_shared/casa_da_doc.py`, contrato em "
          "`_shared/casa-da-doc.md`, é o único que decide onde a doc mora; os 114 pontos "
          "de produção foram adotados (F15.2) e o teto zero impede o primeiro novo"),
    "B": ("dívida DECLARADA — dono: `.claude-plugin/marketplace.json` para a lista de "
          "plugin (existe e ninguém pergunta a ela) e `plugins/project-skills/lib/"
          "doc_load.py` para a lista de doc canônico (LEI/ACORDO/MINERADOS)"),
    "C": ("dívida DECLARADA — dono: `scripts/readme_counts_check.py`, que já recalcula da "
          "fonte, hoje só sobre o README (10 das 138); estendê-lo aos docs é o conserto"),
    "D": ("fonte única IMPLEMENTADA e cobrada — `scripts/bump.py` espelha a versão, "
          "`scripts/sync-shared.sh --check` acusa cópia defasada, e o release-gate morde"),
}
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
    """(rel, nº da linha, trecho, linha inteira) de cada casamento — a prova crua."""
    achados = []
    for rel, texto in alvos:
        if filtro_rel and not filtro_rel(rel):
            continue
        for n, linha in enumerate(texto.splitlines(), 1):
            for m in padrao.finditer(linha):
                # a LINHA vai junto: é nela que mora o marcador de isenção, e o trecho
                # casado sozinho nunca o carrega (F30.6)
                achados.append((rel, n, m.group(0), linha))
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


# O que CONTA como caminho cravado (F30.6, decisão de 2026-08-20): só CÓDIGO
# EXECUTÁVEL. Prosa e retrato de baseline citam o caminho de propósito — a doc que
# ENSINA onde a documentação mora precisa escrever o lugar, e o retrato do
# desacoplamento guarda o texto do achado. Medido em 2026-08-20: com prosa dentro,
# a classe A dava 718 pontos e o zero que o F15.2 exige era inalcançável por
# construção. Isenção pontual ganha `casa-ok: <motivo>` na linha, no molde do
# `acopla-ok` do Artigo 9.
EXECUTAVEL = (".py", ".sh", ".js", ".mjs")
ISENCAO_CASA = "casa-ok:"


def _e_executavel(rel):
    return rel.endswith(EXECUTAVEL)


def classe_a(alvos):
    pontos = _pontos(alvos, RE_CAMINHO,
                     filtro_rel=lambda r: (_e_executavel(r)
                                           and not r.startswith("_shared/lar_fingido")))
    # A isenção declarada sai da conta — e SÓ vale com motivo escrito. Marcador pelado
    # é o mesmo defeito que ele evita, com um carimbo em cima: continua contando.
    def _isento(linha):
        i = linha.find(ISENCAO_CASA)
        return i >= 0 and linha[i + len(ISENCAO_CASA):].strip() != ""
    pontos = [p for p in pontos if not _isento(p[3])]
    return {
        "id": "A",
        "nome": "caminho de doc cravado em código executável",
        "dono": "_shared/casa_da_doc.py — o resolvedor único do caminho da doc (F15.1)",
        "de": "o literal `.claude/docs/x.md` ou `docs/x.md` dentro de .py/.sh/.js",
        "para": "perguntar ao resolvedor: ele tenta docs/ e cai em .claude/docs/",
        "escopo": ("só código executável (%s); prosa e baseline citam o caminho de "
                   "propósito. Isenção pontual: `%s <motivo>` na linha."
                   % (" ".join(EXECUTAVEL), ISENCAO_CASA)),
        "comando": "python3 scripts/anti_slop_inventario.py --classe A | grep -c '^      '",
        "pontos": pontos,
    }


def classe_b(alvos):
    # Retrato de baseline cita os nomes POR CONSTRUÇÃO — é o que ele é: a medida
    # gravada de um achado por plugin/skill. Mesma decisão que a classe A tomou em
    # 2026-08-20 para prosa e baseline; aqui a classe B ganha o par dela, senão todo
    # cobrador novo que grave um retrato estoura o teto sem ter duplicado nada.
    alvos = [(rel, texto) for rel, texto in alvos if not rel.endswith(".baseline.json")]
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
        c["situacao"] = SITUACAO[c["id"]]
        c["teto"] = TETO[c["id"]]
        c["reincidiu"] = c["ocorrencias"] > c["teto"]
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
        print(f"    situação    : {c['situacao']}")
        print(f"    teto        : {c['teto']}"
              + ("  ⚠️ REINCIDIU" if c["reincidiu"] else ""))
        print(f"    confere com : {c['comando']}")
        if so_classe:
            for ponto in c["pontos"]:
                # B e D descrevem o arquivo inteiro e não carregam a linha crua que
                # A e C guardam para a isenção — o ponto é lido por índice, não desempacotado
                rel, linha, trecho = ponto[0], ponto[1], ponto[2]
                alvo = f"{rel}:{linha}" if linha else rel
                print(f"      {alvo}  {trecho}")
        print()


def checa(inv):
    """Sai 1 quando alguma classe passou do teto — reincidência da mesma doença."""
    piores = [c for c in inv["classes"] if c["reincidiu"]]
    if not piores:
        return 0
    for c in piores:
        print(f"❌ REINCIDÊNCIA na classe {c['id']} · {c['nome']}: "
              f"{c['ocorrencias']} ocorrências contra o teto de {c['teto']}")
        print(f"   dono   : {c['dono']}")
        print(f"   onde   : {c['comando']}")
        print(f"   saída  : some com a ocorrência nova, ou pergunte ao dono da classe")
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--classe", choices=["A", "B", "C", "D"])
    ap.add_argument("--check", action="store_true",
                    help="reprova (sai 1) a classe que passou do teto")
    args = ap.parse_args()
    inv = inventario()
    if args.check:
        return checa(inv)
    if args.json:
        print(json.dumps(inv, ensure_ascii=False, indent=2))
    else:
        imprime(inv, args.classe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
