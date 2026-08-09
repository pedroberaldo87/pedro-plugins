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
    alvo = 'python3 "${CLAUDE_PLUGIN_ROOT}/lib/sobras.py" --json'
    sujo = texto.replace(alvo, "git add -A && " + alvo)
    check("a injeção pegou no texto real", sujo != texto)
    p = escrever(sujo)
    achados = autopsia_check.checar(p)
    os.unlink(p)
    check("a rodada que toca arquivo do projeto reprova",
          any("escreve na árvore" in a for a in achados), repr(achados))


def caso_placeholder_nao_declarado_reprova():
    """Placeholder que a prosa não declara reprova; `<run>`, que ela declara, passa."""
    texto = open(autopsia_check.SKILL_PADRAO, encoding="utf-8").read()
    alvo = 'python3 "${CLAUDE_PLUGIN_ROOT}/lib/sobras.py" --json'
    sujo = texto.replace(alvo, 'python3 "<plugin visual>/lib/visual_page.py"')
    check("a injeção pegou no texto real", sujo != texto)
    p = escrever(sujo)
    achados = autopsia_check.checar(p)
    os.unlink(p)
    check("o placeholder mudo do irmão reprova", bool(achados), repr(achados))


def caso_parecer_sem_o_montador_reprova():
    """O caso de 2026-08-09: a rodada entregou o parecer num formato próprio.

    As duas metades da regra são cobradas — a frase que proíbe a prosa no chat e o
    bloco que passa pelo montador, que é quem recusa proposta sem as três partes.
    """
    texto = open(autopsia_check.SKILL_PADRAO, encoding="utf-8").read()
    sem_montador = texto.replace(autopsia_check.MONTADOR, "inventado.py")
    check("a injeção pegou no texto real", sem_montador != texto)
    p = escrever(sem_montador)
    achados = autopsia_check.checar(p)
    os.unlink(p)
    check("skill que larga o montador reprova",
          any("montador" in a for a in achados), repr(achados))

    sem_frase = texto.replace("não sai em prosa no chat", "vai como couber")
    check("a segunda injeção pegou", sem_frase != texto)
    p = escrever(sem_frase)
    achados = autopsia_check.checar(p)
    os.unlink(p)
    check("skill que libera prosa no chat reprova",
          any("prosa" in a for a in achados), repr(achados))


if __name__ == "__main__":
    print("bancada do cobrador da lei da autópsia")
    caso_skill_real_passa()
    caso_trava_ausente_do_texto()
    caso_rodada_toca_arquivo_do_projeto()
    caso_placeholder_nao_declarado_reprova()
    caso_parecer_sem_o_montador_reprova()
    print("\n%s" % ("tudo verde" if not FALHAS else "FALHOU: " + ", ".join(FALHAS)))
    sys.exit(1 if FALHAS else 0)
