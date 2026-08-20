#!/usr/bin/env python3
"""Caminho de doc cravado fora do resolvedor — o cobrador da classe A (F15.3).

Quem decide onde a documentação de um projeto mora é o resolvedor único:
`_shared/casa_da_doc.py` (Python) e `_shared/lib-casa-da-doc.sh` (bash). Código
executável que escreve esse caminho como TEXTO decide de novo, sozinho, e no dia em
que a casa mudar ele fica para trás — foi assim que o caminho acabou cravado em
centenas de pontos.

A medição NÃO é reescrita aqui: é a mesma de `anti_slop_inventario.classe_a`
(só `.py/.sh/.js/.mjs`, isenção `casa-ok: <motivo>` na linha, com motivo escrito),
e o teto é o mesmo `TETO["A"]` de lá. Um medidor, um número — dois seriam a doença.

Dívida antiga passa, ponto NOVO reprova: escrever um caminho cravado num arquivo a
mais deixa isto vermelho.

    python3 scripts/casa_da_doc_check.py        # sai 1 se passou do teto
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import anti_slop_inventario as asi  # noqa: E402  (precisa do sys.path acima)

for _canal in (sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass


def conta(alvos=None):
    """Quantos pontos de caminho cravado existem hoje (alvos: (rel, texto))."""
    return len(asi.classe_a(alvos if alvos is not None else asi.universo())["pontos"])


def main(alvos=None):
    quantos = conta(alvos)
    teto = asi.TETO["A"]
    if quantos <= teto:
        return 0
    print(f"❌ CAMINHO DE DOC CRAVADO — {quantos} pontos contra o teto de {teto}: "
          f"{quantos - teto} a mais que a dívida medida.")
    print("   resolvedor : _shared/casa_da_doc.py  ·  _shared/lib-casa-da-doc.sh")
    print("   saída      : pergunte o caminho ao resolvedor em vez de escrevê-lo,")
    print("                ou isente a linha com `casa-ok: <motivo>` — com o motivo.")
    print("   onde       : python3 scripts/anti_slop_inventario.py --classe A")
    return 1


if __name__ == "__main__":
    sys.exit(main())
