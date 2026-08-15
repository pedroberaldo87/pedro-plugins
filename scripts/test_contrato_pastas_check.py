#!/usr/bin/env python3
"""Suíte do cobrador do contrato de pastas (R-19) — stdlib, sem framework.

Dois defeitos ela pega: cobrador que reprova as casas JÁ EM USO hoje (barulho que
ensina a desligar) e cobrador que deixa passar pasta NOVA fora do contrato — que é
a única coisa que ele existe pra acusar.

    python3 scripts/test_contrato_pastas_check.py
"""

import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import contrato_pastas_check as C  # noqa: E402

PASS = FAIL = 0


def check(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  ok   %s" % label)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (label, extra))


print("\n== o repositório de hoje passa ==")
casa, fora = C.varre()
check("a tabela declara pasta", len(casa) >= 10, "(só %d)" % len(casa))
check("nenhuma casa em uso reprovada", not fora, "(%s)" % fora[:3])
for p in ("docs", "plans", "visual", "archify", "ata", "specs", ".sprint"):
    check("a tabela declara .claude/%s/" % p, p in casa)

print("\n== pasta NOVA fora do contrato é acusada ==")
with tempfile.TemporaryDirectory() as tmp:
    d = os.path.join(tmp, "plugins", "novo", "skills", "novo")
    os.makedirs(d)
    with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8") as fh:
        fh.write(
            "Grave o resultado em `.claude/inventado/x.md`.\n"
            "Estado cross-projeto fica em `~/.claude/tambem-inventado/y.json`.\n"
            "O plano fica em `.claude/plans/<id>.plan.json`.\n"
            "A corrida vai para `.claude/.sprint/corridas.jsonl`.\n"
            "E a escondida em `.claude/.tambem-inventado/z`.\n"
        )
    _, fora = C.varre(tmp)
    pastas = [p for _, _, p in fora]
    check(
        "acusa a pasta nova, com ponto ou sem",
        pastas == ["inventado", ".tambem-inventado"],
        "(achou %s)" % pastas,
    )
    check("não acusa a pasta declarada", "plans" not in pastas)
    check("não acusa a casa do ledger", ".sprint" not in pastas)
    check("não acusa estado sob ~/", "tambem-inventado" not in pastas)

# Quem ESCOLHE pasta de trabalho não é só a prosa da skill: o motor do /sprint e os
# hooks a escolhem em código. Varrendo só Markdown, a pasta nova nascia num `.js` ou
# num `.sh` sem nada acusar — e foi assim que duas casas reais deste repositório
# ficaram fora do contrato até 2026-08-15.
print("\n== o cobrador enxerga o código, não só a prosa da skill ==")
with tempfile.TemporaryDirectory() as tmp:
    d = os.path.join(tmp, "plugins", "novo", "hooks")
    os.makedirs(d)
    with open(os.path.join(d, "motor.js"), "w", encoding="utf-8") as fh:
        fh.write("const dir = repoRoot + '/.claude/so-no-js/';\n")
    with open(os.path.join(d, "gancho.sh"), "w", encoding="utf-8") as fh:
        # o caminho CITADO em shell vem entre aspas: sem elas no prefixo, o estado
        # cross-projeto do harness aparecia como pasta de trabalho não declarada
        fh.write('mkdir -p .claude/so-no-sh/\n'
                 'for c in "$HOME"/.claude/plugins/cache/*; do :; done\n')
    with open(os.path.join(d, "test_gancho.sh"), "w", encoding="utf-8") as fh:
        fh.write("mkdir -p .claude/so-na-suite/\n")   # suíte não escolhe casa
    _, fora = C.varre(tmp)
    pastas = sorted(p for _, _, p in fora)
    check("acusa a pasta que só existe no .js", "so-no-js" in pastas, "(achou %s)" % pastas)
    check("acusa a pasta que só existe no .sh", "so-no-sh" in pastas, "(achou %s)" % pastas)
    check("não acusa o cache do harness citado com aspas", "plugins" not in pastas)
    check("não acusa pasta criada por suíte", "so-na-suite" not in pastas)

print("\n%d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
