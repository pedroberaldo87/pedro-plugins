#!/usr/bin/env python3
"""Suite do andamento: relogio, estimativa por memoria do projeto, avanco da suite.

O contrapeso que mais importa aqui e o NEGATIVO: comando sem historico neste
projeto NAO pode sair com numero. Numero inventado e pior que numero nenhum,
porque cria expectativa e ninguem sabe que ele foi chutado.

Os placares testados sao os TRES formatos medidos em 299 transcripts reais deste
repositorio, mais o do pytest — nada de formato imaginado.
"""

import os
import shutil
import sys
import tempfile

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def main():
    tmp = tempfile.mkdtemp(prefix="andamento-")
    os.environ["CLAUDE_CONFIG_DIR"] = tmp
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import andamento as a
    a.ESTADO = os.path.join(tmp, "sovai")

    try:
        print("o placar sai da saida CRUA, nos formatos que existem de verdade")
        check("formato '139 passou · 0 falhou'",
              a.placar("...\n139 passou · 0 falhou\n") == {
                  "passou": 139, "falhou": 0, "linha": "139 passou · 0 falhou"})
        check("formato 'OK (56 checks)'", a.placar("OK (56 checks)")["passou"] == 56)
        check("formato '17 ok / 0 falhas'", a.placar("17 ok / 0 falhas")["passou"] == 17)
        check("formato do pytest", a.placar("12 passed, 3 failed")["falhou"] == 3)
        check("saida sem placar devolve None", a.placar("compilando...") is None)
        # Falso-positivo medido num motor real em 2026-08-06: o texto que DOCUMENTA o
        # formato foi lido como se fosse o placar daquele agente.
        check("prosa que FALA de placar nao vira placar",
              a.placar("**`placar`** = a linha crua (`139 passou · 0 falhou`)") is None)
        check("mas a linha crua logo abaixo da prosa ainda e lida",
              a.placar("`139 passou · 0 falhou` e o formato\n139 passou · 0 falhou")["passou"] == 139)
        check("le o placar do FIM, nao o do meio",
              a.placar("2 passou · 0 falhou\nrodando mais\n40 passou · 1 falhou")["passou"] == 40)

        print("estimativa vem da memoria DESTE projeto — e so dela")
        proj = "/casa/projeto-a"
        cmd = "python3 lib/test_x.py"
        check("comando novo NAO tem estimativa", a.estimativa(proj, cmd) is None)
        check("a linha de disparo diz que e a primeira vez",
              "sem estimativa" in a.linha_disparo(cmd, proj))
        a.registrar(proj, cmd, 30)
        a.registrar(proj, cmd, 40)
        a.registrar(proj, cmd, 50)
        check("com historico, a estimativa e a mediana", a.estimativa(proj, cmd) == 40)
        check("a linha de disparo passa a trazer o numero",
              "~40s" in a.linha_disparo(cmd, proj))
        check("a linha de disparo SEMPRE traz o relogio",
              a.linha_disparo(cmd, proj)[2] == ":" and a.linha_disparo(cmd, proj)[5] == ":")
        check("memoria de OUTRO projeto nao vaza pra este",
              a.estimativa("/casa/projeto-b", cmd) is None)
        check("guarda no maximo as 5 ultimas",
              len(a.registrar(proj, cmd, 60) or []) <= 5
              and len(a.registrar(proj, cmd, 70)) == 5)

        print("o mesmo comando com caminho temporario conta como o mesmo")
        a.registrar(proj, "pytest /tmp/xyz123/t.py", 10)
        check("caminho temporario vira curinga",
              a.estimativa(proj, "pytest /tmp/outro456/t.py") == 10)

        print("avanco: dois placares iguais seguidos e o sinal de 'nao andou'")
        p1 = a.placar("10 passou · 5 falhou")
        p2 = a.placar("10 passou · 5 falhou")
        p3 = a.placar("14 passou · 1 falhou")
        p4 = a.placar("6 passou · 9 falhou")
        check("placar identico duas vezes = sem avanco", a.avanco(p1, p2) == "sem avanço")
        check("mais passando = avancou", a.avanco(p1, p3) == "avançou")
        check("menos passando = regrediu", a.avanco(p1, p4) == "regrediu")
        check("so o numero de falhas caindo ja e avanco",
              a.avanco(a.placar("10 passou · 5 falhou"),
                       a.placar("10 passou · 2 falhou")) == "avançou")
        check("sem placar nenhum nao inventa veredito", a.avanco(p1, None) == "sem placar")
        check("o primeiro placar nao e comparado com nada",
              a.avanco(None, p1) == "primeiro placar")

        # O chamador real rele o placar da rodada anterior do disco, e nem sempre o
        # que volta e dicionario: as vezes e a linha CRUA que a suite imprimiu.
        # Assumir a estrutura estourava em cima do proprio narrador.
        print("o placar anterior tambem pode chegar como TEXTO, e ai nao estoura")
        check("anterior em texto: mesmo placar = sem avanco",
              a.avanco("10 passou · 5 falhou", p2) == "sem avanço")
        check("anterior em texto: placar melhor = avancou",
              a.avanco("10 passou · 5 falhou", p3) == "avançou")
        check("os DOIS lados em texto tambem valem",
              a.avanco("10 passou · 5 falhou", "6 passou · 9 falhou") == "regrediu")
        check("texto SEM placar nenhum no anterior = primeiro placar",
              a.avanco("compilando...", p1) == "primeiro placar")
        check("entrada que nao e placar nem texto nao derruba",
              a.avanco(12345, p1) == "primeiro placar")

        print("a narracao do meio da execucao")
        check("cala quando nao ha nada a dizer",
              a.linha_andamento("comando-novo-nunca-visto", proj, 12) is None)
        check("passar do dobro do usual e dito com todas as letras",
              "passou do dobro" in a.linha_andamento(cmd, proj, 200))
        check("dentro do usual nao alarma",
              "passou do dobro" not in a.linha_andamento(cmd, proj, 30))
        linha = a.linha_andamento(cmd, proj, 30, "10 passou · 5 falhou", p1)
        check("o placar entra na linha com o veredito de avanco",
              "10 passou · 5 falhou" in linha and "sem avanço" in linha)
        check("a linha diz ha quanto tempo roda",
              a.linha_andamento(cmd, proj, 30).startswith("rodando há"))
        check("a linha de andamento com o anterior em TEXTO devolve linha, nao erro",
              "sem avanço" in a.linha_andamento(
                  cmd, proj, 30, "10 passou · 5 falhou", "10 passou · 5 falhou"))

        print("a narracao sai em portugues acentuado")
        check("'rodando ha' sai com acento", "rodando há" in a.linha_andamento(cmd, proj, 30))
        check("o veredito de avanco sai com cedilha",
              "avanç" in a.linha_andamento(cmd, proj, 30, "10 passou · 5 falhou", p1))
        check("a linha do silencio vivo sai acentuada",
              a.linha_silencio(20 * 60, True) ==
              "rodando há 20 min — trabalho vivo, não é travamento")
        check("a linha do travamento sai acentuada",
              a.linha_silencio(20 * 60, False) ==
              "travamento: nada mudou há 20 min e não há trabalho vivo")

        print("duracao longa sai em minutos, nao em segundos crus")
        check("90s+ vira minutos", "min" in a.linha_andamento(cmd, proj, 200))

        # A prova de que os DOIS casos de silencio longo sao distinguiveis. Um so
        # numero muda entre eles — o sinal de vida — entao toda diferenca de texto
        # abaixo e obra dele, e nao de outra condicao.
        print("silencio longo: demora legitima e travamento nao saem iguais")
        MUDO = 20 * 60
        vivo = a.linha_silencio(MUDO, True)
        travado = a.linha_silencio(MUDO, False)
        check("COM sinal de vida a tela diz ha quanto tempo esta rodando",
              vivo is not None and vivo.startswith("rodando há 20 min"))
        check("COM sinal de vida a linha nega o travamento com todas as letras",
              vivo is not None and "não é travamento" in vivo)
        check("SEM sinal de vida a tela chama de travamento",
              travado is not None and travado.startswith("travamento"))
        check("SEM sinal de vida nao sai 'rodando ha'",
              travado is not None and "rodando há" not in travado)
        check("as duas linhas sao textos diferentes", vivo != travado)
        check("silencio curto nao narra nada nos dois casos",
              a.linha_silencio(60, True) is None and a.linha_silencio(60, False) is None)
        check("sem silencio medido (missao recem-armada) nao narra",
              a.linha_silencio(None, False) is None)
        check("o limite e o mesmo do vigia do motor: 12 min",
              a.LIMITE_SILENCIO == 12 * 60
              and a.linha_silencio(12 * 60, True) is None
              and a.linha_silencio(12 * 60 + 1, True) is not None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

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
