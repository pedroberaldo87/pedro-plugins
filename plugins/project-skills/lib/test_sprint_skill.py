#!/usr/bin/env python3
"""A SKILL.md do sprint tem que cobrar `requisito` e `pronto` em cada tarefa.

O defeito que isto impede: a decomposicao entregava tarefa sem dizer que requisito
ela atende nem o que conta como feito. O executor cumpria o que quisesse e o revisor
nao tinha regua — a falta passava calada. A suite cobra os tres pontos onde o par
precisa aparecer: o schema DECOMP (obrigatorio, copiado da spec), o prompt do #1
(campo da spec, nunca redigido pelo decompositor) e o BUILD_REVIEW (eixo de rastreio
que reprova, com o script segurando o gap acima do floor).
"""

import os
import sys

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "sprint", "SKILL.md")

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

    # O papel #1 virou ORQUESTRADOR (autopsia 2026-08-09, decisao do dono).
    decompositor = secao(texto, "- **OPUS #1 — Orquestrador.", "- **EXECUTORES")
    revisor = secao(texto, "- **OPUS #2 — Revisor de construção.", "- **DIAGNÓSTICO")
    schema_decomp = secao(texto, "- `DECOMP` —", "- `TASK_RESULT`")
    schema_review = secao(texto, "- `BUILD_REVIEW` —", "\n\nO `stopReason`")

    print("o schema DECOMP declara os dois campos como obrigatorios")
    check("o schema DECOMP existe", bool(schema_decomp))
    check("a tarefa carrega `requisito` e `pronto`",
          "requisito, pronto" in schema_decomp)
    check("os dois sao obrigatorios",
          "obrigatórios" in schema_decomp)
    check("sao copiados da spec, nao redigidos pelo decompositor",
          "copiados da spec" in schema_decomp and "não redigidos" in schema_decomp)

    print("o prompt do #1 manda copiar da spec e bloquear quando falta")
    check("o papel do #1 existe", bool(decompositor))
    check("o #1 marca `requisito` e `pronto` na tarefa",
          "`requisito`" in decompositor and "`pronto`" in decompositor)
    check("os dois saem da spec, nunca redigidos ali",
          "saem da spec" in decompositor and "nunca redigidos aqui" in decompositor)
    check("item da spec sem os dois vira Bloqueio, nao tarefa",
          "não vira tarefa" in decompositor and "Bloqueio" in decompositor)

    print("o BUILD_REVIEW carrega o eixo e a skill descreve a reprovacao")
    check("o schema BUILD_REVIEW existe", bool(schema_review))
    check("o kind 'rastreio' esta no schema", "'rastreio'" in schema_review)
    check("o gap de rastreio nasce >= severityFloor",
          "severityFloor" in secao(schema_review, "`kind: 'rastreio'`", "`kind: 'spec'`"))
    check("o revisor lista o eixo de rastreio", "rastreio" in revisor)
    check("a skill descreve a reprovacao da tarefa sem os campos",
          "sem `requisito` ou sem `pronto`" in revisor and "reprova" in revisor)
    check("o script segura o gap de rastreio no filtro (nao so a prosa)",
          "g.kind === 'rastreio'" in texto)

    # A armacao ensinava `rm -f {ativo,bloqueios}-$sid`, que alcanca 2 dos 8 prefixos
    # de estado — onda-, placar-, doc-, sinal-, trabalho- ficavam pra tras.
    armacao = secao(texto, "### O sinal que arma o gate", "### Por que o gate precisou nascer")
    print("a armacao do sinal ensina a MESMA receita de encerramento do passo 3")
    check("a secao de armacao existe", bool(armacao))
    check("a armacao nao ensina mais `rm -f` do sinal",
          "rm -f" not in armacao)
    check("a armacao manda `arma <sid> sprint <motor>`",
          'arma "$CLAUDE_CODE_SESSION_ID" sprint "$SPRINT_MOTOR_ID"' in armacao)
    check("a armacao nao acende o sinal com printf no arquivo",
          "printf" not in armacao.replace("`printf`", ""))
    check("a armacao manda `encerra <sid> sprint`",
          'encerra "$CLAUDE_CODE_SESSION_ID" sprint' in armacao)
    check("a prosa da expiracao cobra o `encerra`, nao o `rm`",
          "não te dispensa do `encerra`" in armacao)

    # Sem isto o bullet da fronteira some na proxima edicao e o revisor de
    # construcao volta a tratar buraco de projeto inteiro como gap da missao.
    fronteira = secao(texto, "### Fronteira com o `/qa-loop`",
                      "### O ciclo curto é por BLOCO")
    print("a fronteira com a /completude esta escrita")
    check("a secao de fronteira existe", bool(fronteira))
    check("o bullet diz que a /completude cobre quem sobrou de fora",
          "**A `/completude` (fora da missão) garante que não SOBROU ninguém de fora**"
          in fronteira)
    check("o bullet nega que elo da /completude vire gap daqui",
          "Não é dele, e não vira gap aqui." in fronteira)
    check("o resumo tem a linha da /completude",
          'completude = "sobrou alguém de fora?"' in fronteira)

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
