#!/usr/bin/env python3
"""test_resolve_plugin.py — cobra o `_shared/resolve-plugin.sh`.

Ele existe porque `${CLAUDE_PLUGIN_ROOT}/../<irmao>/…` so resolve rodando do repositorio:
o cache do harness guarda `<cache>/<marketplace>/<plugin>/<versao>/`, e ali o irmao esta
dois niveis acima e atras de um segmento de versao. Por isso nada aqui compara string com
string — cada check EXECUTA o script contra uma arvore de mentira montada no layout real.

E cobra tambem as copias: o plugin instalado so enxerga a propria pasta, entao resolvedor
que nao chegou pela copia e resolvedor que nao existe na maquina de quem instalou.
"""

import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
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
    with open(caminho, "w") as f:
        f.write("alvo\n")


def resolve(layout, nome="lixeiro", rel="lib/lixeiro.py", pede=None):
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
            # `../../` do proprio marketplace o alcancam — so a varredura do cache.
            root = os.path.join(raiz, "pedro-plugins", "sprint", "1.13.0")
            poe(os.path.join(raiz, "config", "plugins", "cache",
                             "outro", nome, "2.0.0", rel))
        else:
            root = os.path.join(raiz, "pedro-plugins", "sprint", "1.13.0")
        os.makedirs(root, exist_ok=True)
        amb = dict(os.environ)
        amb.update({"CLAUDE_PLUGIN_ROOT": root,
                    "CLAUDE_CONFIG_DIR": os.path.join(raiz, "config")})
        out = subprocess.run(["bash", FONTE, p_nome, p_rel],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", env=amb, stdin=subprocess.DEVNULL, start_new_session=True)
        saida = out.stdout.strip()
        return out.returncode, saida, bool(saida) and os.path.isfile(saida)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)


def main():
    print("resolve-plugin.sh — o irmao entra pelo NOME, nunca pela posicao")

    rc, saida, existe = resolve("repo")
    check("rodando do repositorio, o irmao direto resolve", rc == 0)
    check("e o caminho devolvido existe de verdade", existe)

    rc, saida, existe = resolve("cache")
    check("no layout do cache do marketplace, resolve", rc == 0 and existe)
    check("entre as versoes do cache, sai a MAIS ALTA",
          saida.endswith("/lixeiro/1.10.0/lib/lixeiro.py"))

    rc, saida, existe = resolve("outro-marketplace")
    check("irmao vindo de OUTRO marketplace tambem e achado", rc == 0 and existe)
    check("e o achado e o do cache, com a versao dele",
          saida.endswith("/outro/lixeiro/2.0.0/lib/lixeiro.py"))

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
