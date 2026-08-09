#!/usr/bin/env python3
"""Os números de vendoring que architecture.md publica batem com scripts/sync-shared.sh.

A doc dá os comandos que produzem os números; este teste roda o equivalente e cobra
que o texto não tenha ficado para trás.
"""
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOC = RAIZ / ".claude" / "docs" / "architecture.md"


def contagens():
    fonte = (RAIZ / "scripts" / "sync-shared.sh").read_text()
    specs = re.search(r"^SPECS=\((.*?)^\)", fonte, re.S | re.M).group(1)
    pares = [ln.strip().strip('"').split("::") for ln in specs.splitlines()
             if "::" in ln and not ln.strip().startswith("#")]
    return len(pares), len({d for d, _ in pares}), Counter(a for _, a in pares)


def test_doc_publica_as_copias_e_pastas_reais():
    copias, pastas, por_arquivo = contagens()
    doc = DOC.read_text()
    assert f"**{copias} cópias, em {pastas} pastas de destino" in doc, \
        f"doc desatualizada: são {copias} cópias em {pastas} pastas"
    assert f"vendora _shared/ → {copias} cópias em {pastas} pastas" in doc, \
        f"linha do mapa de arquivos desatualizada: {copias}/{pastas}"
    for arquivo, n in por_arquivo.most_common(4):
        assert f"`{arquivo}` ({n})" in doc, \
            f"contribuinte desatualizado: {arquivo} tem {n} cópias"


if __name__ == "__main__":
    test_doc_publica_as_copias_e_pastas_reais()
    print("ok")
    sys.exit(0)
