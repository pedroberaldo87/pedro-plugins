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
sys.path.insert(0, str(RAIZ / "_shared"))
from casa_da_doc import casa  # noqa: E402  (precisa do sys.path acima)

DOC = Path(casa(RAIZ, "architecture.md"))


def contagens():
    fonte = (RAIZ / "scripts" / "sync-shared.sh").read_text(encoding="utf-8")
    specs = re.search(r"^SPECS=\((.*?)^\)", fonte, re.S | re.M).group(1)
    pares = [ln.strip().strip('"').split("::") for ln in specs.splitlines()
             if "::" in ln and not ln.strip().startswith("#")]
    return len(pares), len({d for d, _ in pares}), Counter(a for _, a in pares)


def test_doc_publica_as_copias_e_pastas_reais():
    copias, pastas, por_arquivo = contagens()
    doc = DOC.read_text(encoding="utf-8")
    assert f"**{copias} cópias, em {pastas} pastas de destino" in doc, \
        f"doc desatualizada: são {copias} cópias em {pastas} pastas"
    assert f"vendora _shared/ → {copias} cópias em {pastas} pastas" in doc, \
        f"linha do mapa de arquivos desatualizada: {copias}/{pastas}"
    for arquivo, n in por_arquivo.most_common(4):
        assert f"`{arquivo}` ({n})" in doc, \
            f"contribuinte desatualizado: {arquivo} tem {n} cópias"


def test_doc_publica_o_numero_de_arquivos_fonte():
    """Os DOIS lugares que contam _shared/ dizem o mesmo número, e é o real.

    A §2 ('fonte-da-verdade do compartilhado (N arquivos-fonte)') e a §7
    ('de N arquivos-fonte') citavam 17 e 20 ao mesmo tempo. Número em doc sem
    cobrador é o mesmo defeito que fez a tabela de plugins defasar.
    """
    fontes = len([p for p in (RAIZ / "_shared").iterdir()
                  if p.is_file() and not p.name.startswith(".")])
    doc = DOC.read_text(encoding="utf-8")
    achados = set(re.findall(r"(\d+) arquivos-fonte", doc))
    assert achados == {str(fontes)}, \
        f"_shared/ tem {fontes} arquivos-fonte; a doc diz {sorted(achados)}"


def test_doc_nao_publica_medicao_divergente_da_frase():
    """O parêntese 'medido nesta rodada' repete os números dos comandos."""
    copias, pastas, _ = contagens()
    doc = DOC.read_text(encoding="utf-8")
    assert f"devolvem `{copias}` e `{pastas}`" in doc, \
        f"medição do parêntese desatualizada: são {copias} e {pastas}"


if __name__ == "__main__":
    test_doc_publica_as_copias_e_pastas_reais()
    test_doc_publica_o_numero_de_arquivos_fonte()
    test_doc_nao_publica_medicao_divergente_da_frase()
    print("ok")
    sys.exit(0)
