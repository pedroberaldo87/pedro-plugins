#!/usr/bin/env python3
"""Bancada do cobrador da lei da autópsia — um caso para cada metade da lei."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autopsia_check  # noqa: E402

FALHAS = []


def check(nome, cond, detalhe=""):
    print("  %s  %s%s" % ("ok  " if cond else "FAIL", nome,
                          "" if cond else "  → " + detalhe))
    if not cond:
        FALHAS.append(nome)


def escrever(texto):
    fd, p = tempfile.mkstemp(suffix="-SKILL.md")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(texto)
    return p


def caso_skill_real_passa():
    achados = autopsia_check.checar(autopsia_check.SKILL_PADRAO)
    check("a skill real passa", not achados, "\n".join(achados))


def caso_trava_ausente_do_texto():
    texto = open(autopsia_check.SKILL_PADRAO, encoding="utf-8").read()
    sem_trava = texto.replace("reprove toda proposta que troque robustez por economia",
                              "prefira a proposta mais barata")
    p = escrever(sem_trava)
    achados = autopsia_check.checar(p)
    os.unlink(p)
    check("a trava ausente do texto reprova",
          any("trava de robustez" in a for a in achados), repr(achados))


def caso_rodada_toca_arquivo_do_projeto():
    texto = open(autopsia_check.SKILL_PADRAO, encoding="utf-8").read()
    sujo = texto.replace("python3 plugins/improve-workflow/lib/sobras.py --json",
                         "git add -A && python3 plugins/improve-workflow/lib/sobras.py --json")
    p = escrever(sujo)
    achados = autopsia_check.checar(p)
    os.unlink(p)
    check("a rodada que toca arquivo do projeto reprova",
          any("escreve na árvore" in a for a in achados), repr(achados))


if __name__ == "__main__":
    print("bancada do cobrador da lei da autópsia")
    caso_skill_real_passa()
    caso_trava_ausente_do_texto()
    caso_rodada_toca_arquivo_do_projeto()
    print("\n%s" % ("tudo verde" if not FALHAS else "FALHOU: " + ", ".join(FALHAS)))
    sys.exit(1 if FALHAS else 0)
