#!/usr/bin/env python3
"""test_custo_check.py — o caso que fez o cobrador nascer.

O comentário "~6ms com ~1500 entradas, aceito" envelheceu junto com a máquina e
virou 16s por chamada. Afirmação de custo sem data e sem tamanho de amostra é
número que ninguém consegue reavaliar — é isso que estes casos prendem.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import custo_check  # noqa: E402

FALHAS = []


def check(nome, obtido, esperado):
    ok = obtido == esperado
    print("%s %s" % ("✓" if ok else "✗", nome))
    if not ok:
        print("    esperado: %r\n    obtido:   %r" % (esperado, obtido))
        FALHAS.append(nome)


def analisa(texto):
    """Escreve o trecho num .sh temporário e devolve (achados, conformes)."""
    with tempfile.NamedTemporaryFile("w", suffix=".sh", encoding="utf-8",
                                     delete=False) as fh:
        fh.write(texto)
        tmp = fh.name
    try:
        return custo_check.analisa(tmp, "amostra.sh")
    finally:
        os.unlink(tmp)


print("── o caso do graphify-guard: número sem prova cai, com prova passa ──")

sem_prova = "# A poda custa ~6ms, aceito.\nfind /tmp -delete\n"
a, c = analisa(sem_prova)
check("comentário sem data e sem amostra é achado", len(a), 1)
check("e o achado nomeia as DUAS faltas",
      a[0]["missing"] if a else None, ["data da medição", "tamanho da amostra"])
check("e ele não entra na lista de conformes", len(c), 0)

com_prova = ("# A poda custa ~6ms com ~1500 entradas (medido em 2026-08-14).\n"
             "find /tmp -delete\n")
a, c = analisa(com_prova)
check("com data + amostra no mesmo comentário, não é achado", len(a), 0)
check("e ele entra na lista de conformes", len(c), 1)

print("── a prova pode morar em outra linha do MESMO bloco ──")
bloco = ("# Medido em 2026-08-14, com 343.936 entradas no topo do temporário:\n"
         "# a poda levava 16s por chamada.\n")
a, c = analisa(bloco)
check("bloco contíguo conta como um só contexto de prova", (len(a), len(c)), (0, 1))

partido = ("# Medido em 2026-08-14, com 343.936 entradas no topo do temporário.\n"
           "ls\n"
           "# A poda levava 16s por chamada.\n")
a, _ = analisa(partido)
check("prova em bloco separado NÃO vale", len(a), 1)

print("── faltas parciais ──")
a, _ = analisa("# Custo medido em 2026-08-07: ~0,6s.\n")
check("só data → falta a amostra", a[0]["missing"] if a else None,
      ["tamanho da amostra"])
a, _ = analisa("# Com 1500 entradas o hook custa ~6ms.\n")
check("só amostra → falta a data", a[0]["missing"] if a else None,
      ["data da medição"])

print("── o que NÃO é afirmação de custo ──")
a, _ = analisa("# Locks obsoletos (>5min) são quebrados.\n")
check("duração sem palavra de custo passa batido", len(a), 0)
a, _ = analisa("# O portão custa caro em todo commit.\n")
check("palavra de custo sem duração passa batido", len(a), 0)
a, _ = analisa('check "custo por chamada" "$(grep -c \'~6ms\' "$H")" "1"\n')
check("linha de código, não comentário, fica fora", len(a), 0)
a, _ = analisa("# A poda custa ~6ms.  # custo-ok: herdado, remedido em F21\n")
check("isenção com motivo silencia a linha", len(a), 0)

print("── a árvore real: é aqui que este teste vira o portão ──")
achados, conformes = custo_check.varre()
# Sem esta linha o cobrador seria prosa: ele acharia os 5 achados reais e nada ficaria
# vermelho. O glob `scripts/test_*.py` do suite.sh já coleta este arquivo, então esta
# asserção é o gate — não há gate novo a inventar.
check("nenhuma afirmação de custo sem data e sem amostra na árvore real",
      ["%s:%d" % (a["file"], a["line"]) for a in achados], [])
check("varredura padrão devolve conformes",
      len(conformes) > 0, True)
check("o hook do graphify-guard está entre os conformes",
      any(c["file"].endswith("pretooluse-graphify-guard.sh") for c in conformes), True)
check("achado e conforme são conjuntos disjuntos",
      set((a["file"], a["line"]) for a in achados)
      & set((c["file"], c["line"]) for c in conformes), set())

print()
if FALHAS:
    print("FALHOU: %d caso(s) — %s" % (len(FALHAS), "; ".join(FALHAS)))
    sys.exit(1)
print("test_custo_check: todos os casos passaram")
