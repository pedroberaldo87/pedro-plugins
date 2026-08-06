#!/usr/bin/env python3
"""A SKILL.md do qa-loop tem que ancorar o review em DUAS coisas, não em uma.

O defeito que isto impede: o revisor comparava só contra o plano, então código que
cumpria o plano e violava as metas de qualidade do projeto passava limpo. A suíte
cobra os dois pontos onde a âncora de constituição precisa aparecer — e cobra que
a régua fique NO PROJETO (arquivo lido na rodada), não copiada aqui dentro.
"""

import os
import re
import sys

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "qa-loop", "SKILL.md")

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def secao(texto, inicio, fim):
    i = texto.find(inicio)
    if i < 0:
        return ""
    j = texto.find(fim, i)
    return texto[i:j if j > 0 else len(texto)]


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()

    review = secao(texto, "**REVIEW = 1 Opus Revisor", "**CONFIRM =")
    bucket1 = secao(texto, "## CONSTRAINT CENTRAL", "2. **Plan-drift")
    bucket3 = secao(texto, "3. **Plano/arquitetura falho", "> A skill **enforça**")

    print("o prompt do REVIEW carrega as duas ancoras")
    check("o REVIEW existe na skill", bool(review))
    check("manda comparar contra o PLANO", "PLANO" in review and "DIVERGE" in review)
    check("manda ler `.claude/docs/quality-goals.md` do projeto",
          ".claude/docs/quality-goals.md" in review)
    check("a regua e lida do projeto, nao copiada na skill",
          "nunca copiado" in review or "nunca copiada" in review)
    check("fail-open: sem o arquivo o eixo nao roda e nao vira finding",
          "não roda" in review and "não é finding" in review)

    print("o bucket 1 aceita violacao de constituicao como conserto")
    check("a constraint central existe", bool(bucket1))
    check("bucket 1 cita a constituicao alem do plano",
          "constituição" in bucket1 and "quality-goals.md" in bucket1)

    print("a execucao avisa que a entrevista errou, sem mexer no documento")
    check("o REVIEW manda subir o que contradiz a concepcao aprovada",
          "concepção" in review and "reabrir a etapa" in review)
    check("o bucket 3 existe", bool(bucket3))
    check("o alerta propoe reabrir a etapa", "reabrir a etapa" in bucket3)
    check("o alerta indica a linha correcao-pendente, gravada pelo dono",
          "correcao-pendente:" in bucket3)
    check("o loop nunca edita o documento de concepcao",
          "nunca edita o documento" in bucket3)

    print("a regua do projeto nao foi copiada pra dentro da skill")
    # As quatro checagens de estilo vivem no quality-goals.md do projeto; se
    # aparecerem aqui, a skill passou a carregar uma cópia que defasa.
    check("nao ha copia do teto de 140 caracteres",
          not re.search(r"140 caracteres por bullet", texto))

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
