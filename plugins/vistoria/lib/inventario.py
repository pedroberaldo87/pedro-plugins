#!/usr/bin/env python3
"""O inventário da vistoria — quantos pedaços de leitura, e qual evento dispara o quê.

Um **pedaço de leitura** é um plugin: a mesma unidade que a pauta do leitor entrega
a um leitor de cada vez (`skills/vistoria/references/pauta-leitor.md`). A conta sai de DUAS fontes
que existem por motivos diferentes e podem discordar:

  * o **catálogo** — `.claude-plugin/marketplace.json`, a fonte da verdade da
    distribuição, o que um terceiro instala;
  * o **disco** — `plugins/*/` com `.claude-plugin/plugin.json`, o que está escrito
    aqui dentro.

Plugin no disco e fora do catálogo não chega em ninguém; plugin no catálogo e fora
do disco quebra o install. As duas listas divergirem é achado, não detalhe — por
isso o inventário devolve as duas e a diferença, em vez de escolher uma em silêncio.

A tabela evento→hooks lê cada `plugins/*/hooks/hooks.json` **na ordem de registro**, e
essa ordem vale POR ARQUIVO: dentro de um mesmo `hooks.json`, a ordem em que os comandos
aparecem é a que o inventário reproduz. **Entre plugins diferentes a ordem NÃO é medida** —
a lista de um evento é montada varrendo as pastas de `plugins/` em ordem alfabética, que não
tem relação nenhuma com a ordem em que o harness dispara os hooks. Por isso a tabela sai
rotulada (`ordem_entre_plugins: "nao-medida"`): quem quiser afirmar quem bloqueia primeiro
tem que medir o harness antes.

Uso:
    python3 plugins/vistoria/lib/inventario.py --json

stdlib only (requisito do repo).
"""

import argparse
import json
import os
import sys


def pedacos_do_catalogo(raiz="."):
    """Os nomes de plugin que o catálogo distribui, na ordem em que ele os lista."""
    caminho = os.path.join(raiz, ".claude-plugin", "marketplace.json")
    with open(caminho, encoding="utf-8") as fh:
        cat = json.load(fh)
    return [p["name"] for p in cat.get("plugins", [])]


def pedacos_do_disco(raiz="."):
    """Os plugins que existem no disco — pasta em `plugins/` com manifesto próprio."""
    base = os.path.join(raiz, "plugins")
    nomes = []
    for nome in sorted(os.listdir(base)):
        if os.path.isfile(os.path.join(base, nome, ".claude-plugin", "plugin.json")):
            nomes.append(nome)
    return nomes


def divergencia(raiz="."):
    """(só no catálogo, só no disco). Listas vazias = as duas fontes concordam."""
    cat, disco = set(pedacos_do_catalogo(raiz)), set(pedacos_do_disco(raiz))
    return sorted(cat - disco), sorted(disco - cat)


def tabela_de_hooks(raiz="."):
    """{"por_evento": {evento: [(plugin, comando)…]}, "ordem_entre_plugins": "nao-medida"}.

    Dentro de um `hooks.json` a lista sai na ordem de registro. Entre plugins ela sai na
    ordem alfabética das pastas — daí o rótulo, que viaja junto com o dado.
    """
    tabela = {}
    for nome in pedacos_do_disco(raiz):
        caminho = os.path.join(raiz, "plugins", nome, "hooks", "hooks.json")
        if not os.path.isfile(caminho):
            continue
        with open(caminho, encoding="utf-8") as fh:
            conf = json.load(fh)
        for evento, grupos in conf.get("hooks", {}).items():
            for grupo in grupos:
                for h in grupo.get("hooks", []):
                    tabela.setdefault(evento, []).append(
                        {"plugin": nome, "comando": h.get("command", "")})
    return {"por_evento": tabela, "ordem_entre_plugins": "nao-medida"}


def inventario(raiz="."):
    cat = pedacos_do_catalogo(raiz)
    disco = pedacos_do_disco(raiz)
    so_cat, so_disco = divergencia(raiz)
    return {
        "pedacos_catalogo": cat,
        "pedacos_disco": disco,
        "total_catalogo": len(cat),
        "total_disco": len(disco),
        "so_no_catalogo": so_cat,
        "so_no_disco": so_disco,
        "confere": not so_cat and not so_disco,
        "hooks_por_evento": tabela_de_hooks(raiz),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", default=".", help="raiz do repositório (padrão: cwd)")
    ap.add_argument("--json", action="store_true", help="despeja o inventário cru")
    args = ap.parse_args()

    inv = inventario(args.raiz)
    if args.json:
        json.dump(inv, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    print("pedaços de leitura: %d no catálogo, %d no disco"
          % (inv["total_catalogo"], inv["total_disco"]))
    for rotulo, lista in (("só no catálogo", inv["so_no_catalogo"]),
                          ("só no disco", inv["so_no_disco"])):
        if lista:
            print("%s: %s" % (rotulo, ", ".join(lista)))
    hooks = inv["hooks_por_evento"]
    for evento, entradas in sorted(hooks["por_evento"].items()):
        print("%s (%d, ordem entre plugins: %s): %s"
              % (evento, len(entradas), hooks["ordem_entre_plugins"],
                 ", ".join(e["plugin"] for e in entradas)))
    return 0 if inv["confere"] else 1


if __name__ == "__main__":
    sys.exit(main())
