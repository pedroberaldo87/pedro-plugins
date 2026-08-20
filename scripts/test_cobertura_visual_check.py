#!/usr/bin/env python3
"""Cobra o cobrador da cobertura visual — inclusive por SABOTAGEM.

Cobrador que só é exercitado com a lei intacta não prova nada: o caso que vale é o
que APAGA o artigo do texto canônico e exige vermelho. E o texto canônico é achado
pelo resolvedor, então a lei mudar de casa (`docs/` na raiz) não pode cegar o check.
"""

import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import cobertura_visual_check as cvc  # noqa: E402

ARTIGO = """# A lei

## Artigo 11 · Outra coisa

texto qualquer.

## Artigo 12 · Cobertura visual

**O que exige** — Todo fluxo nomeado na documentação tem diagrama, e todo módulo tem
o seu.

## Artigo 13 · Mais uma

fim.
"""

OK = [0]
FAILS = []


def check(nome, cond):
    OK[0] += 1
    print("  %s %s" % ("ok  " if cond else "FALHOU", nome))
    if not cond:
        FAILS.append(nome)


def escreve(raiz, casa, texto):
    pasta = os.path.join(raiz, *casa)
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, "constituicao.md"), "w", encoding="utf-8") as f:
        f.write(texto)


def main():
    print("o resolvedor — a lei responde nas duas casas")
    for casa in cvc.CASAS:
        with tempfile.TemporaryDirectory() as raiz:
            escreve(raiz, casa, ARTIGO)
            achados, caminho = cvc.confere(raiz)
            check("lei em %s passa" % "/".join(casa), achados == [])
            check("lei em %s é o arquivo achado" % "/".join(casa),
                  caminho is not None and os.path.isfile(caminho))

    with tempfile.TemporaryDirectory() as raiz:
        escreve(raiz, ("docs",), ARTIGO)
        escreve(raiz, (".claude", "docs"), ARTIGO.replace("Cobertura visual", "Nada"))
        achados, _ = cvc.confere(raiz)
        check("docs/ na raiz ganha de .claude/docs", achados == [])  # casa-ok: fixture de teste, o literal e o dado do caso

    print("a sabotagem — a regra some e o check tem que ficar vermelho")
    with tempfile.TemporaryDirectory() as raiz:
        sem = ARTIGO.replace("## Artigo 12 · Cobertura visual", "## Artigo 12 · Outra")
        escreve(raiz, ("docs",), sem)
        achados, _ = cvc.confere(raiz)
        check("artigo apagado reprova",
              [a["id"] for a in achados] == ["artigo-sumiu"])

    with tempfile.TemporaryDirectory() as raiz:
        vazio = ARTIGO.replace("Todo fluxo nomeado na documentação tem diagrama, e "
                               "todo módulo tem\no seu.", "vale o bom senso.")
        escreve(raiz, ("docs",), vazio)
        achados, _ = cvc.confere(raiz)
        check("artigo esvaziado (sem diagrama/fluxo/módulo) reprova",
              [a["id"] for a in achados] == ["artigo-esvaziado"])

    with tempfile.TemporaryDirectory() as raiz:
        achados, caminho = cvc.confere(raiz)
        check("projeto sem lei nenhuma reprova, e diz que não achou arquivo",
              [a["id"] for a in achados] == ["sem-lei"] and caminho is None)

    print("a lei DESTE repositório")
    achados, caminho = cvc.confere(RAIZ)
    check("a constituição do repo passa (%s)" % achados, achados == [])
    check("o main sai 0 no repo", cvc.main(["--raiz", RAIZ]) == 0)

    print("\n%d checks, %d falha(s)" % (OK[0], len(FAILS)))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
