#!/usr/bin/env python3
"""A suíte do inventário — as duas fontes têm que bater, e a divergência tem que doer.

Duas coisas são checadas: num repositório de mentira montado aqui, uma divergência
plantada (plugin só no catálogo, plugin só no disco) aparece nomeada; e no repositório
DE VERDADE o catálogo e o disco contam o mesmo número de pedaços de leitura.
"""

import json
import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
sys.path.insert(0, AQUI)

from inventario import divergencia, inventario, tabela_de_hooks  # noqa: E402


def monta_falso(base, catalogo, disco, hooks=None):
    os.makedirs(os.path.join(base, ".claude-plugin"))
    with open(os.path.join(base, ".claude-plugin", "marketplace.json"), "w") as fh:
        json.dump({"plugins": [{"name": n} for n in catalogo]}, fh)
    for nome in disco:
        d = os.path.join(base, "plugins", nome, ".claude-plugin")
        os.makedirs(d)
        with open(os.path.join(d, "plugin.json"), "w") as fh:
            json.dump({"name": nome, "version": "0.0.1"}, fh)
    for nome, conf in (hooks or {}).items():
        d = os.path.join(base, "plugins", nome, "hooks")
        os.makedirs(d)
        with open(os.path.join(d, "hooks.json"), "w") as fh:
            json.dump(conf, fh)


def main():
    base = tempfile.mkdtemp(prefix="vistoria-inventario-")
    try:
        monta_falso(
            base,
            catalogo=["alfa", "beta", "fantasma"],
            disco=["alfa", "beta", "orfao"],
            hooks={"alfa": {"hooks": {"SessionStart": [
                {"hooks": [{"type": "command", "command": "primeiro.sh"},
                           {"type": "command", "command": "segundo.sh"}]}]}}},
        )
        so_cat, so_disco = divergencia(base)
        assert so_cat == ["fantasma"], so_cat
        assert so_disco == ["orfao"], so_disco

        inv = inventario(base)
        assert inv["confere"] is False, inv
        assert inv["total_catalogo"] == 3 and inv["total_disco"] == 3, inv

        tab = tabela_de_hooks(base)
        assert [e["comando"] for e in tab["por_evento"]["SessionStart"]] == [
            "primeiro.sh", "segundo.sh"], tab
        # A ordem DENTRO do arquivo é medida; entre plugins não é — e o rótulo
        # que diz isso viaja no dado, não só na prosa.
        assert tab["ordem_entre_plugins"] == "nao-medida", tab
    finally:
        shutil.rmtree(base, ignore_errors=True)

    # O repositório de verdade: as duas fontes contam o mesmo, e nomeiam os mesmos.
    real = inventario(RAIZ)
    assert real["confere"], "catálogo e disco divergem: %s / %s" % (
        real["so_no_catalogo"], real["so_no_disco"])
    assert real["total_disco"] > 0, real
    assert real["hooks_por_evento"]["por_evento"], "nenhum hook lido do disco"
    assert real["hooks_por_evento"]["ordem_entre_plugins"] == "nao-medida", real

    print("test_inventario: 10 checagens verdes (%d pedaços de leitura)" % real["total_disco"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
