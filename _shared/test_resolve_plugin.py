#!/usr/bin/env python3
"""test_resolve_plugin.py — cobra o `_shared/resolve-plugin.sh`.

Ele existe porque `${CLAUDE_PLUGIN_ROOT}/../<irmao>/…` so resolve rodando do repositorio:
o cache do harness guarda `<cache>/<marketplace>/<plugin>/<versao>/`, e ali o irmao esta
dois niveis acima e atras de um segmento de versao. Por isso nada aqui compara string com
string — cada check EXECUTA o script contra uma arvore de mentira montada no layout real.

E cobra tambem as copias: o plugin instalado so enxerga a propria pasta, entao resolvedor
que nao chegou pela copia e resolvedor que nao existe na maquina de quem instalou.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from bash_posix import bash_posix  # noqa: E402

BASH = bash_posix()
FONTE = os.path.join(AQUI, "resolve-plugin.sh")
RAIZ = os.path.dirname(AQUI)
# Os consumidores declarados no `scripts/sync-shared.sh`.
COPIAS = ("plugins/project-skills/skills/sprint/resolve-plugin.sh",  # acopla-ok: o destino da cópia É o que este teste confere
          "plugins/project-skills/skills/qa-loop/resolve-plugin.sh",  # acopla-ok: idem
          "plugins/project-skills/skills/start/resolve-plugin.sh")  # acopla-ok: idem

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    print("  %s %s" % ("ok  " if cond else "FALHOU", label))
    if not cond:
        FAILS.append(label)


def poe(caminho):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("alvo\n")


def resolve(layout, nome="lixeiro", rel="lib/lixeiro.py", pede=None, via_home=False,
            sem_raiz=False):
    """Monta a arvore, roda o script, devolve (codigo, stdout limpo, o caminho existe?).

    `nome`/`rel` sao o que a arvore CONTEM; `pede` e o par que o script vai PROCURAR
    (default: o mesmo). Separar os dois e o que permite pedir um vizinho parecido e
    provar que ele nao casa. O terceiro item vem daqui de dentro porque a arvore some
    no `finally` — conferir o arquivo depois do retorno seria conferir o vazio.
    """
    p_nome, p_rel = pede or (nome, rel)
    raiz = tempfile.mkdtemp(prefix="resolve-plugin-")
    try:
        if layout == "repo":
            root = os.path.join(raiz, "plugins", "sprint")
            poe(os.path.join(raiz, "plugins", nome, rel))
        elif layout == "cache":
            root = os.path.join(raiz, "pedro-plugins", "sprint", "1.13.0")
            for v in ("1.9.0", "1.10.0", "1.8.2"):
                poe(os.path.join(raiz, "pedro-plugins", nome, v, rel))
        elif layout == "outro-marketplace":
            # O irmao existe, mas veio de OUTRO marketplace: nem o irmao direto nem o
            # `../../` do proprio marketplace o alcancam — so a varredura do cache. A
            # varredura so vale para o marketplace DESTE repositorio (Achado 9).
            root = os.path.join(raiz, "pedro-plugins", "sprint", "1.13.0")
            poe(os.path.join(raiz, "config", "plugins", "cache",
                             "outro", nome, "2.0.0", rel))
        elif layout in ("cache-nosso-e-alheio", "cache-so-alheio-mais-alto",
                        "cache-so-nosso", "cache-nome-parecido"):
            # A raiz do chamador NAO esta no cache (rodando de fora do harness, ou
            # CLAUDE_PLUGIN_ROOT apontando para outra pasta): so a varredura do cache
            # da config alcanca o irmao. O que ela pode devolver e o ponto do teste.
            root = os.path.join(raiz, "solto", "sprint")
            cache = os.path.join(raiz, "config", "plugins", "cache")
            if layout in ("cache-nosso-e-alheio", "cache-so-nosso"):
                poe(os.path.join(cache, "pedro-plugins", nome, "1.0.0", rel))
            if layout in ("cache-nosso-e-alheio", "cache-so-alheio-mais-alto"):
                poe(os.path.join(cache, "zz-alheio", nome, "9.9.9", rel))  # ordena DEPOIS do nosso: ganha o sort -V
            if layout == "cache-nome-parecido":
                # marketplace de nome PARECIDO com o nosso nao e o nosso
                poe(os.path.join(cache, "pedro-plugins-fork", nome, "9.9.9", rel))
                poe(os.path.join(cache, "xpedro-plugins", nome, "9.9.9", rel))
        else:
            root = os.path.join(raiz, "pedro-plugins", "sprint", "1.13.0")
        os.makedirs(root, exist_ok=True)
        amb = dict(os.environ)
        casa = os.path.join(raiz, "home")
        os.makedirs(casa, exist_ok=True)
        amb.update({"CLAUDE_PLUGIN_ROOT": root,
                    "CLAUDE_CONFIG_DIR": os.path.join(raiz, "config"),
                    "HOME": casa, "USERPROFILE": casa})
        if via_home:
            amb.pop("CLAUDE_CONFIG_DIR")
            # o cache da config de mentira passa a morar no HOME de mentira
            ant = os.path.join(raiz, "config", "plugins")
            if os.path.isdir(ant):
                os.makedirs(os.path.join(casa, ".claude"), exist_ok=True)
                shutil.move(ant, os.path.join(casa, ".claude", "plugins"))
        if sem_raiz:
            amb.pop("CLAUDE_PLUGIN_ROOT")
        # BASH, nunca "bash": no Windows o `bash` do PATH é o do WSL, que sem distro
        # instalada responde uma reclamação em UTF-16 — e as checagens reprovavam o
        # RESOLVEDOR por causa do interpretador. Ver `_shared/bash_posix.py`.
        out = subprocess.run([BASH, FONTE, p_nome, p_rel],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=amb, stdin=subprocess.DEVNULL, start_new_session=True)
        saida = out.stdout.strip()
        return out.returncode, saida, bool(saida) and os.path.isfile(saida)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)


def casos_que_executam():
    """Os checks que rodam o resolvedor de verdade contra arvores de mentira."""
    rc, saida, existe = resolve("repo")
    check("rodando do repositorio, o irmao direto resolve", rc == 0)
    check("e o caminho devolvido existe de verdade", existe)

    rc, saida, existe = resolve("cache")
    check("no layout do cache do marketplace, resolve", rc == 0 and existe)
    check("entre as versoes do cache, sai a MAIS ALTA",
          saida.endswith("/lixeiro/1.10.0/lib/lixeiro.py"))

    # Achado 9 (scan 8e9a3ff2): a varredura do cache so vale para o marketplace DESTE
    # repositorio. Plugin de mesmo nome vindo de OUTRO marketplace nao e o irmao —
    # executar o script dele, so porque a versao e mais alta, e o defeito.
    rc, saida, _ = resolve("outro-marketplace")
    check("irmao de OUTRO marketplace NAO e devolvido", saida == "")
    check("...e a ausencia sai com 3, igual a plugin fora da maquina", rc == 3)

    rc, saida, existe = resolve("cache-nosso-e-alheio")
    check("varredura do cache: o do nosso marketplace resolve", rc == 0 and existe)
    check("...mesmo havendo o alheio com versao MAIS ALTA (9.9.9)",
          saida.endswith("/cache/pedro-plugins/lixeiro/1.0.0/lib/lixeiro.py"))

    rc, saida, _ = resolve("cache-so-alheio-mais-alto")
    check("so o alheio no cache: nada resolve", rc == 3 and saida == "")

    rc, saida, _ = resolve("cache-nome-parecido")
    check("marketplace de nome PARECIDO com o nosso nao conta (sem curinga no nome)",
          rc == 3 and saida == "")

    # `existe` fica de fora aqui: no Windows o bash devolve o HOME em forma POSIX
    # (`/tmp/...`), que o Python nao abre. Quem prova a origem e o trecho do caminho.
    rc, saida, _ = resolve("cache-nosso-e-alheio", via_home=True)
    check("sem CLAUDE_CONFIG_DIR, o cache vem de $HOME/.claude e vale a mesma regra",
          rc == 0 and "/home/.claude/plugins/cache/pedro-plugins/lixeiro/1.0.0/" in saida.replace("\\", "/"))

    rc, saida, existe = resolve("cache-nosso-e-alheio", sem_raiz=True)
    check("sem CLAUDE_PLUGIN_ROOT, so o do nosso marketplace resolve",
          rc == 0 and existe and "/cache/pedro-plugins/" in saida)
    rc, saida, _ = resolve("cache-so-alheio-mais-alto", sem_raiz=True)
    check("sem CLAUDE_PLUGIN_ROOT, so o alheio no cache: nada resolve",
          rc == 3 and saida == "")

    # NOME e REL entram em caminho de arquivo que o chamador EXECUTA: so nome simples de
    # plugin e caminho relativo sem `..` valem (o arquivo existe na arvore em todos os casos
    # abaixo, entao o unico motivo de nao resolver e a validacao).
    rc, saida, existe = resolve("repo", rel="lib/lixeiro.py", pede=("lixeiro", "lib/lixeiro.py"))
    check("controle: NOME e REL validos continuam resolvendo", rc == 0 and existe)
    for rotulo, par in (
        ("REL com '..'", ("lixeiro", "lib/../lib/lixeiro.py")),
        ("REL que sobe para fora do plugin", ("lixeiro", "../lixeiro/lib/lixeiro.py")),
        ("REL absoluto", ("lixeiro", "/etc/passwd")),
        ("REL com '.' como segmento", ("lixeiro", "lib/./lixeiro.py")),
        ("REL com curinga", ("lixeiro", "lib/*.py")),
        ("NOME '..'", ("..", "plugins/lixeiro/lib/lixeiro.py")),
        ("NOME com barra", ("plugins/lixeiro", "lib/lixeiro.py")),
        ("NOME com curinga", ("lix*eira", "lib/lixeiro.py")),
        ("NOME maiusculo/espaco", ("Lixeiro x", "lib/lixeiro.py")),
    ):
        rc, saida, _ = resolve("repo", pede=par)
        check("%s e recusado (sai com 2, sem caminho)" % rotulo, rc == 2 and saida == "")

    rc, saida, _ = resolve("ausente")
    check("plugin fora da maquina nao devolve caminho nenhum", saida == "")
    check("...e sinaliza a ausencia no codigo de saida (3), sem gritar", rc == 3)

    # Nome que nao e o do irmao nao pode casar por acaso: o resolvedor procura a PASTA
    # com aquele nome, nao um pedaco de caminho parecido.
    rc, saida, _ = resolve("cache", pede=("lixeira", "lib/lixeiro.py"))
    check("nome parecido nao resolve o plugin errado", rc == 3 and saida == "")

    # Arquivo pedido que nao existe DENTRO do irmao instalado: ausencia igual, nao
    # caminho quebrado devolvido como se fosse bom.
    rc, saida, _ = resolve("cache", pede=("lixeiro", "lib/nao-existe.py"))
    check("arquivo inexistente dentro do irmao devolve ausencia, nao caminho quebrado",
          rc == 3 and saida == "")


def main():
    print("resolve-plugin.sh — o irmao entra pelo NOME, nunca pela posicao")

    # Sem bash que responda, os casos que EXECUTAM o resolvedor pulam declarando —
    # as copias vendoradas continuam conferidas, porque isso e leitura de arquivo.
    # Gate que nao consegue medir diz que nao mediu (Artigo 4).
    if BASH is None:
        print("  skip os casos que executam o resolvedor (nenhum bash funcional aqui)")
    else:
        casos_que_executam()

    print("o nome do marketplace cravado no resolvedor e o do catalogo")
    with open(os.path.join(RAIZ, ".claude-plugin", "marketplace.json"), encoding="utf-8") as fh:
        nome_mkt = json.load(fh)["name"]
    corpo_fonte = open(FONTE, encoding="utf-8").read()
    check("MERCADO=\"%s\" no resolvedor bate com .claude-plugin/marketplace.json" % nome_mkt,
          'MERCADO="%s"' % nome_mkt in corpo_fonte)

    print("as copias vendoradas — sem elas o resolvedor nao existe na maquina instalada")
    corpo = open(FONTE, encoding="utf-8").read()
    for rel in COPIAS:
        caminho = os.path.join(RAIZ, rel)
        existe = os.path.isfile(caminho)
        check("a copia chegou em %s" % rel, existe)
        check("...e ela e identica a fonte em _shared/",
              existe and open(caminho, encoding="utf-8").read() == corpo)

    print()
    if FAILS:
        print("FALHOU (%d de %d):" % (len(FAILS), TOTAL[0]))
        for f in FAILS:
            print("  - %s" % f)
        sys.exit(1)
    print("OK (%d checks)" % TOTAL[0])


if __name__ == "__main__":
    main()
