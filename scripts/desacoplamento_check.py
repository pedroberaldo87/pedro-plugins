#!/usr/bin/env python3
"""desacoplamento_check.py — cobra o Artigo 9: nada amarra o NOME nem a QUANTIDADE.

Três formas proibidas, e o defeito de cada uma:

1. IRMÃO POR POSIÇÃO — `${CLAUDE_PLUGIN_ROOT}/../<outro>/…`. O cache do harness instala
   cada plugin em pasta própria; `../<irmão>` não resolve na máquina de quem instalou.
   Medido em 2026-08-07: das 4 ocorrências, 2 JÁ estavam quebradas.

2. DEPENDÊNCIA EXECUTÁVEL DE IRMÃO — a skill manda RODAR um arquivo de outro plugin, ou
   monta um caminho para dentro dele. Citar o nome de um plugin em prosa NÃO entra aqui:
   isso é linguagem, não acoplamento. A régua é "o arquivo deixa de funcionar se o outro
   sumir?" — e prosa não deixa. Medido em 2026-08-07: a primeira versão desta régua acusou
   765 ocorrências, quase todas menção em texto; gate que grita assim é desligado na
   primeira hora.

3. CONTAGEM CRAVADA — "os 21 plugins", "as 54 suítes". Envelhece sem avisar. A própria
   constituição carregou **54** enquanto a medição devolvia **60**.

COMO ELE NÃO VIRA GATE DESLIGADO NO PRIMEIRO DIA. Ele compara contra um retrato
(`.claude/desacoplamento.baseline.json`), no mesmo molde do `hook_contract.py`: reprova o
que PIORA, e a dívida existente é paga por passo de plano. Gate que nasce reprovando 87
ocorrências é gate que alguém desliga na primeira hora — e o repo já tem esse precedente
(o `scope-cop` ficou em `off`).

ISENÇÃO: `acopla-ok: <motivo>` na linha, mesmo molde do `public-ok` do Artigo 2. Duas
nascem de fábrica, porque são o oposto do defeito:
  - o próprio índice (`marketplace.json`, `manifest.json`) — existe para listar;
  - narrativa histórica — contar que uma contagem estava errada não é cravar contagem.

Uso:
    python3 scripts/desacoplamento_check.py                  # contra o retrato
    python3 scripts/desacoplamento_check.py --todos          # tudo, inclusive a dívida
    python3 scripts/desacoplamento_check.py --gravar-retrato # congela o estado de hoje
"""

import argparse
import json
import os
import re
import subprocess
import sys

RETRATO = ".claude/desacoplamento.baseline.json"
ISENCAO = re.compile(r"acopla-ok:\s*\S")

# 1 · irmão por posição relativa
IRMAO = re.compile(r"CLAUDE_PLUGIN_ROOT\}?/\.\./([\w-]+)")

# 3 · contagem cravada: número + substantivo de coisa que este repo conta
CONTAGEM = re.compile(
    r"(?<![\w.])(?:\*\*)?(\d{1,4})(?:\*\*)?\s+"
    r"(plugins?|skills?|hooks?|su[íi]tes?|c[óo]pias?|cobradores?|checks?)(?![\w-])",
    re.I)

# O que NÃO é contagem cravada, mesmo casando o padrão acima:
#  - a linha traz o comando que produz o número (número com procedência não envelhece)
#  - a linha é narrativa de um defeito passado
COM_COMANDO = re.compile(r"\$ |`(?:python3|bash|git|grep|ls|wc)\b|\bgrep -c|\bwc -l")
NARRATIVA = re.compile(r"\b(?:dizia|at[ée] 20\d\d-|era \*\*|quando a medi|virou|"
                       r"deixou de|antes de|foi o defeito)\b", re.I)
# `estava errad` e `envelhec` são RAÍZES — a palavra real continua ("estava errada",
# "envelhece"), então elas não podem levar `\b` no fim: o `\b` exigia não-letra logo
# depois e as duas alternativas nunca casavam. Ficam em ramo próprio, sem fecho.
#
# ...e ficam separadas por um segundo motivo: elas são frouxas demais para valer DENTRO da
# documentação. "Envelhece sem avisar" é a frase que a própria doc usa para FALAR de
# contagem cravada; deixá-la isentar ali seria dar à doc um passe que basta escrever a
# palavra para obter — e é justamente na doc que o número envelhece calado (S-58).
NARRATIVA_RAIZ = re.compile(r"\b(?:estava errad|envelhec)", re.I)

# Arquivos que EXISTEM para listar ou para descrever o repositório — isentos por natureza.
# A documentação em `.claude/docs/` cita plugin pelo nome porque o trabalho dela é esse;
# acusá-la seria acusar o próprio mapa de ser um mapa.
INDICES = ("marketplace.json", "manifest.json", "settings-defaults.json",
           "portability.yml", "hooks.json")
# `.claude/` inteiro descreve ou retrata o repositório: doc, retrato de gate, registro de
# limite. Acusar um retrato de citar o que ele retrata é acusar o termômetro pela febre.
DIRS_ISENTOS = (".claude/", "README.md", "scripts/")

# ...mas a isenção é de NOME, não de NÚMERO. Descrever o repositório obriga a citar os
# plugins pelo nome; não obriga a cravar quantos são. É justamente na doc que a contagem
# envelhece em silêncio — a própria constituição carregou **54** enquanto a medição
# devolvia **60**. Então a pasta da documentação sai da isenção da contagem cravada, e o
# que entra no lugar do número é o comando que o produz (S-58).
DOC = ".claude/docs/"


def isento_de_contagem(rel):
    return rel.startswith(DIRS_ISENTOS) and not rel.startswith(DOC)


def eh_narrativa(rel, linha):
    """A linha conta um defeito passado — e por isso não crava contagem nova.

    As raízes frouxas (`envelhec`, `estava errad`) valem em todo lugar MENOS na pasta da
    documentação, onde elas são vocabulário corrente e não narrativa.
    """
    if NARRATIVA.search(linha):
        return True
    return bool(NARRATIVA_RAIZ.search(linha)) and not rel.startswith(DOC)

# DEPENDÊNCIA EXECUTÁVEL: o nome do irmão aparece dentro de um caminho ou de uma invocação.
# É isto que quebra quando o outro plugin não está na máquina — e só isto.
def _rx_dependencia(p):
    n = re.escape(p)
    return re.compile(
        r"plugins/%s/"                       # caminho dentro do repo
        r"|/%s/(?:lib|hooks|skills)/"        # caminho para dentro do irmão
        r"|\.\./%s\b"                        # irmão por posição
        r"|skill:\s*[\"']%s[\"']"             # invocação nominal da skill
        % (n, n, n, n))


# O MESMO defeito escrito a partir da raiz do repositório: `plugins/<qualquer>/lib/…`.
# A régua por NOME acima só pega irmão que existe nesta cópia — e foi justamente um nome
# que deixou de existir no lugar citado (o arquivo mudou de plugin) que quebrou o motor.
# Na máquina de quem instalou não existe pasta `plugins/`: o caminho não resolve, ponto.
# Caminho de artefato do PROJETO (`scripts/…`, `.claude/…`) não começa por `plugins/` e
# segue passando.
RAIZ = re.compile(r"(?<![\w./-])plugins/([\w-]+)/(?:lib|hooks|skills)/")


def rastreados(root):
    try:
        out = subprocess.run(["git", "-C", root, "ls-files"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    return [f for f in out.stdout.splitlines()
            if f.endswith((".md", ".sh", ".py", ".json", ".yml"))]


def plugins_de(root):
    d = os.path.join(root, "plugins")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def dono_do(caminho):
    """De que plugin este arquivo é. Citar a si mesmo nunca é acoplamento."""
    p = caminho.split("/")
    return p[1] if len(p) > 2 and p[0] == "plugins" else None


def varre(root="."):
    """Devolve a lista de achados. Cada um é um dict estável, comparável com o retrato."""
    plugs = plugins_de(root)
    if not plugs:
        return []
    # `(?<![\w/-])nome(?![\w-])`: não casa dentro de caminho nem de palavra maior
    por_nome = {p: _rx_dependencia(p) for p in plugs}
    achados = []

    for rel in rastreados(root):
        # O próprio retrato guarda o TRECHO de cada achado, então varrê-lo faz o gate
        # acusar o retrato de conter o que ele retrata — e cada regravação acrescentaria
        # uma camada nova. Termômetro não tem febre.
        if rel == RETRATO:
            continue
        base = os.path.basename(rel)
        eh_indice = base in INDICES or rel.startswith(DIRS_ISENTOS)
        dono = dono_do(rel)
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                linhas = fh.read().splitlines()
        except OSError:
            continue

        for n, linha in enumerate(linhas, 1):
            if ISENCAO.search(linha):
                continue

            m = IRMAO.search(linha)
            if m:
                achados.append({"forma": "irmao-por-posicao", "arquivo": rel, "linha": n,
                                "alvo": m.group(1), "trecho": linha.strip()[:120]})

            if not eh_indice:
                alvos = [p for p, rx in por_nome.items() if p != dono and rx.search(linha)]
                # mesma forma, mesmo achado: o caminho a partir da raiz que cita um irmão
                # conhecido já entrou acima, e não pode entrar duas vezes.
                alvos += [m.group(1) for m in RAIZ.finditer(linha)
                          if m.group(1) != dono and m.group(1) not in alvos]
                for p in alvos:
                    achados.append({"forma": "dependencia-de-irmao", "arquivo": rel, "linha": n,
                                    "alvo": p, "trecho": linha.strip()[:120]})

            if rel.endswith(".md") and not isento_de_contagem(rel) \
                    and not COM_COMANDO.search(linha) \
                    and not eh_narrativa(rel, linha):
                for c in CONTAGEM.finditer(linha):
                    achados.append({"forma": "contagem-cravada", "arquivo": rel, "linha": n,
                                    "alvo": "%s %s" % (c.group(1), c.group(2)),
                                    "trecho": linha.strip()[:120]})
    return achados


def chave(a):
    """Identidade de um achado: forma, arquivo, alvo e o TRECHO — nunca a linha.

    A linha fica de fora porque acrescentar um parágrafo no topo empurraria todo achado
    abaixo, e o gate acusaria dezenas de "novos" que são os mesmos de sempre — retrato que
    vira ruído é retrato que alguém desliga.

    O trecho ENTRA porque sem ele a chave fica grossa demais: uma segunda dependência para
    o mesmo irmão, no mesmo arquivo, colidiria com a primeira e passaria despercebida.
    Furo achado pela própria suíte, 2026-08-07.

    O trecho entra normalizado (espaços colapsados) para que reindentar não conte como
    acoplamento novo.
    """
    trecho = " ".join((a.get("trecho") or "").split())
    return "%s|%s|%s|%s" % (a["forma"], a["arquivo"], a["alvo"], trecho)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--todos", action="store_true", help="mostra tudo, inclusive a dívida")
    ap.add_argument("--gravar-retrato", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    achados = varre(a.root)
    caminho = os.path.join(a.root, RETRATO)

    if a.gravar_retrato:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        # Duas linhas idênticas em arquivos diferentes dão chaves diferentes, mas a mesma
        # linha repetida dentro do mesmo arquivo dá a MESMA chave — e o retrato é um
        # conjunto de chaves, não um diário de ocorrências. Gravar a repetição só engorda
        # o arquivo e faz a contagem impressa aqui divergir da que o gate compara.
        conjunto = sorted(set(chave(x) for x in achados))
        with open(caminho, "w", encoding="utf-8") as fh:
            json.dump(conjunto, fh, ensure_ascii=False, indent=1)
        print("retrato gravado: %d achado(s) em %s" % (len(conjunto), RETRATO))
        return 0

    conhecidos = set()
    if not a.todos:
        try:
            with open(caminho, encoding="utf-8") as fh:
                conhecidos = set(json.load(fh))
        except (OSError, ValueError):
            conhecidos = set()

    novos = [x for x in achados if chave(x) not in conhecidos]

    if a.json:
        print(json.dumps({"todos": achados, "novos": novos}, ensure_ascii=False))
        return 1 if novos else 0

    por_forma = {}
    for x in achados:
        por_forma.setdefault(x["forma"], []).append(x)
    print("Artigo 9 · desacoplamento — %d achado(s) no total" % len(achados))
    for forma in ("irmao-por-posicao", "dependencia-de-irmao", "contagem-cravada"):
        n = len(por_forma.get(forma, []))
        print("  %-20s %3d" % (forma, n))

    if a.todos:
        for x in achados:
            print("\n%s:%d  [%s → %s]" % (x["arquivo"], x["linha"], x["forma"], x["alvo"]))
            print("   %s" % x["trecho"])
        return 1 if achados else 0

    if not conhecidos:
        print("\n(sem retrato em %s — nada a comparar. Grave com --gravar-retrato)" % RETRATO)
        return 0
    if not novos:
        print("\nNenhum acoplamento NOVO além do retrato. A dívida existente é paga por plano.")
        return 0
    print("\n⛔ %d acoplamento(s) NOVO(S), fora do retrato:" % len(novos))
    for x in novos:
        print("\n%s:%d  [%s → %s]" % (x["arquivo"], x["linha"], x["forma"], x["alvo"]))
        print("   %s" % x["trecho"])
    print("\nO Artigo 9 diz o que entra no lugar de cada forma. Isenção legítima:")
    print("acrescente `acopla-ok: <motivo>` na linha.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
