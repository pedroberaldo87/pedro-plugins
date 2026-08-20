#!/usr/bin/env python3
"""Suite do andamento: relogio, estimativa por memoria do projeto, avanco da suite.

O contrapeso que mais importa aqui e o NEGATIVO: comando sem historico neste
projeto NAO pode sair com numero. Numero inventado e pior que numero nenhum,
porque cria expectativa e ninguem sabe que ele foi chutado.

Os placares testados sao os TRES formatos medidos em 299 transcripts reais deste
repositorio, mais o do pytest — nada de formato imaginado.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

# O bash que RESPONDE, não o do PATH: no Windows o do PATH é o do WSL, que sem
# distro fala UTF-16 e chega como stdout vazio — a suíte reprovaria o comando
# certo por causa do interpretador. Módulo compartilhado (_shared/bash_posix.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bash_posix import bash_posix  # noqa: E402

BASH = bash_posix() or "bash"


FAILS = []


def _blocos_do_sinal(skill_md):
    """Os blocos ```bash da SKILL.md que mexem no sinal `ativo-<sid>`, em ordem.

    O teste roda o que ESTA ESCRITO na skill, nao uma copia dele aqui: skill que
    manda acender o sinal noutra casa quebra este teste, que e o ponto.
    """
    with open(skill_md, encoding="utf-8") as fh:
        texto = fh.read()
    return [b for b in re.findall(r"```bash\n(.*?)```", texto, re.S)
            if "ativo-$CLAUDE_CODE_SESSION_ID" in b]


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
    a.ESTADO = os.path.join(tmp, "sprint")

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
              a.linha_andamento(cmd, proj, 30).startswith("Rodando há"))
        check("a linha de andamento com o anterior em TEXTO devolve linha, nao erro",
              "sem avanço" in a.linha_andamento(
                  cmd, proj, 30, "10 passou · 5 falhou", "10 passou · 5 falhou"))

        print("a narracao sai em portugues acentuado")
        check("'rodando ha' sai com acento", "Rodando há" in a.linha_andamento(cmd, proj, 30))
        check("o veredito de avanco sai com cedilha",
              "avanç" in a.linha_andamento(cmd, proj, 30, "10 passou · 5 falhou", p1))
        check("a linha do silencio vivo sai acentuada",
              a.linha_silencio(20 * 60, True) ==
              "Rodando há 20 min — trabalho vivo, não é travamento")
        check("a linha do travamento sai acentuada",
              a.linha_silencio(20 * 60, False) ==
              "Travamento: nada mudou há 20 min e não há trabalho vivo")

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
              vivo is not None and vivo.startswith("Rodando há 20 min"))
        check("COM sinal de vida a linha nega o travamento com todas as letras",
              vivo is not None and "não é travamento" in vivo)
        check("SEM sinal de vida a tela chama de travamento",
              travado is not None and travado.startswith("Travamento"))
        check("SEM sinal de vida nao sai 'rodando ha'",
              travado is not None and "Rodando há" not in travado)
        check("as duas linhas sao textos diferentes", vivo != travado)
        check("silencio curto nao narra nada nos dois casos",
              a.linha_silencio(60, True) is None and a.linha_silencio(60, False) is None)
        check("sem silencio medido (missao recem-armada) nao narra",
              a.linha_silencio(None, False) is None)
        check("o limite e o mesmo do vigia do motor: 12 min",
              a.LIMITE_SILENCIO == 12 * 60
              and a.linha_silencio(12 * 60, True) is None
              and a.linha_silencio(12 * 60 + 1, True) is not None)

        # A BARRA e a unica superficie que FICA. Ate aqui ela dizia SEM SINAL nos
        # dois casos: a suite de 20 min rodando normalmente aparecia igualzinha ao
        # travamento. Abaixo, so o arquivo de trabalho vivo muda entre os cenarios
        # — o silencio e o mesmo, com a mesma idade.
        print("a barra separa demora legitima de travamento")
        base = os.path.join(tmp, "barra")
        os.makedirs(base)
        agora = time.time()
        ativo = os.path.join(base, "ativo-s1")
        open(ativo, "w", encoding="utf-8").close()
        os.utime(ativo, (agora - 3000, agora - 3000))
        with open(os.path.join(base, "sinal-s1"), "w", encoding="utf-8") as fh:
            fh.write(str(agora - 20 * 60))
        trabalho = os.path.join(base, "trabalho-s1")

        travado = a.linha_motor("s1", base, agora)
        check("sem trabalho vivo a barra chama de SEM SINAL",
              travado is not None and "SEM SINAL" in travado)

        with open(trabalho, "w", encoding="utf-8") as fh:
            fh.write(str(agora - 20 * 60))
        vivo = a.linha_motor("s1", base, agora)
        check("com trabalho vivo a barra diz ha quanto tempo esta rodando",
              vivo is not None and "Rodando há 20 min" in vivo)
        check("com trabalho vivo a barra NAO diz SEM SINAL",
              vivo is not None and "SEM SINAL" not in vivo)
        check("as duas linhas da barra sao textos diferentes", vivo != travado)
        check("a barra continua trazendo a idade da missao nos dois casos",
              "Missão há" in vivo and "Missão há" in travado)

        # Comando de pe ha 3 segundos nao explica silencio de 20 minutos.
        with open(trabalho, "w", encoding="utf-8") as fh:
            fh.write(str(agora - 3))
        check("trabalho recente demais nao vira alibi do silencio longo",
              "SEM SINAL" in (a.linha_motor("s1", base, agora) or ""))

        # Silencio curto segue sendo so um numero, com ou sem trabalho vivo.
        with open(os.path.join(base, "sinal-s1"), "w", encoding="utf-8") as fh:
            fh.write(str(agora - 70))
        with open(trabalho, "w", encoding="utf-8") as fh:
            fh.write(str(agora - 60))
        curto = a.linha_motor("s1", base, agora)
        check("silencio curto na barra nao vira nem demora nem travamento",
              "Último sinal há 70s" in curto and "Rodando há" not in curto)

        # O RELOGIO E A ESTIMATIVA DA FERRAMENTA CHEGAM A BARRA (F9.26). Ate aqui
        # `linha_disparo`/`estimativa` montavam os dois e nenhuma tela os recebia. A
        # barra nao adivinha nada: le o comando e o projeto que QUEM EXECUTA gravou
        # no `trabalho-<sid>`, e so por isso consegue chamar `estimativa()`.
        with open(trabalho, "w", encoding="utf-8") as fh:
            fh.write("%s\n%s\n%s\n" % (agora - 45, cmd, proj))
        com_est = a.linha_motor("s1", base, agora)
        check("a barra traz o tempo decorrido da ferramenta",
              "Ferramenta há 45s" in com_est)
        check("a barra traz a estimativa quando ela existe",
              "usual ~%s" % a._dur(a.estimativa(proj, cmd)) in com_est)

        # Comando sem historico NESTE projeto sai sem numero — a mesma regra do
        # modulo inteiro: relogio sozinho e honesto, numero inventado nao.
        with open(trabalho, "w", encoding="utf-8") as fh:
            fh.write("%s\n%s\n%s\n" % (agora - 45, "comando-que-nunca-rodou", proj))
        sem_est = a.linha_motor("s1", base, agora)
        check("comando sem historico chega a barra sem estimativa",
              "Ferramenta há 45s" in sem_est and "usual ~" not in sem_est)

        # O PLACAR DA ONDA (F9.27). O motor pedia o campo `placar` do SUITE_RESULT e
        # o descartava: nenhuma tela dizia se a suite andou de uma onda para a
        # seguinte. Aqui ele e registrado por sessao, comparado com o da onda
        # anterior por `avanco()`, e o veredito chega a barra e ao cartao.
        print("o placar da suite, comparado entre ondas")
        check("a primeira onda nao compara com nada",
              "primeiro placar" in a.onda("s1", "139 passou · 0 falhou", base))
        check("onda que repete o placar sai como sem avanco",
              "sem avanço" in a.onda("s1", "139 passou · 0 falhou", base))
        check("a linha crua da suite vai junto",
              "139 passou · 0 falhou" in a.linha_placar("s1", base))
        check("onda que melhora sai como avancou",
              "avançou" in a.onda("s1", "141 passou · 0 falhou", base))
        check("saida sem placar nao registra onda nenhuma",
              a.onda("s1", "compilando...", base) is None
              and "141 passou" in a.linha_placar("s1", base))
        check("sessao sem onda nenhuma nao inventa linha",
              a.linha_placar("s-sem-onda", base) is None)
        check("o placar comparado aparece na BARRA",
              "sem avanço" in (a.onda("s1", "141 passou · 0 falhou", base) or "")
              and "sem avanço" in a.linha_motor("s1", base, agora))

        # Registro no formato velho (so o carimbo) nao inventa relogio de ferramenta.
        with open(trabalho, "w", encoding="utf-8") as fh:
            fh.write(str(agora - 60))
        check("registro sem comando deixa a barra como era",
              "Ferramenta há" not in (a.linha_motor("s1", base, agora) or ""))

        # A PASTA DE ESTADO NAO PODE TER O NOME DE UM PLUGIN SO (F17.2). O modulo
        # ja e chamado por quatro plugins; a casa e neutra e e uma so — a cascata
        # de leitura da pasta antiga saiu junto com o rename de 2026-08-09.
        print("a casa do estado e neutra")
        neutra = os.path.join(tmp, "andamento")
        a.ESTADO = neutra
        proj_n, cmd_n = "/casa/projeto-mudanca", "bash suite-nova.sh"
        a.registrar(proj_n, cmd_n, 20)
        nome_n = os.path.basename(a._arquivo(proj_n))
        check("o historico de duracao NASCE na pasta neutra",
              os.path.exists(os.path.join(neutra, nome_n)))

        # A LINHA NOMEIA QUEM A ACENDEU (F17.3). Ate aqui ela dizia `sprint` fixo,
        # e era a unica funcao do modulo presa a um plugin. O nome vem do PROPRIO
        # sinal — dois motores diferentes na MESMA sessao produzem duas linhas.
        print("a linha da missão nomeia o motor que acendeu o sinal")
        casa = os.path.join(tmp, "motores")
        os.makedirs(casa)
        aceso = os.path.join(casa, "ativo-sm")

        with open(aceso, "w", encoding="utf-8") as fh:
            fh.write("qa-loop\n")
        primeiro = a.linha_motor("sm", casa, agora)
        check("o primeiro motor aparece pelo nome dele",
              (primeiro or "").startswith("🚀 Qa-loop · Missão há"))

        with open(aceso, "w", encoding="utf-8") as fh:
            fh.write("vistoria\n")
        segundo = a.linha_motor("sm", casa, agora)
        check("o segundo motor na mesma sessão aparece pelo nome dele",
              (segundo or "").startswith("🚀 Vistoria · Missão há"))
        check("as duas linhas da mesma sessão não se confundem",
              primeiro != segundo and "qa-loop" not in (segundo or ""))

        # Sinal aceso do jeito antigo (vazio, ou com carimbo que nao e nome) nao
        # inventa motor: continua sendo a execucao continua, que e quem acendia.
        open(aceso, "w", encoding="utf-8").close()
        check("sinal sem nome continua saindo como a execução contínua",
              (a.linha_motor("sm", casa, agora) or "").startswith("🚀 %s · Missão há" % a.MOTOR_PADRAO.capitalize()))
        with open(aceso, "w", encoding="utf-8") as fh:
            fh.write("1")
        check("carimbo no lugar do nome não vira nome de motor",
              (a.linha_motor("sm", casa, agora) or "").startswith("🚀 %s · Missão há" % a.MOTOR_PADRAO.capitalize()))

        # OS OUTROS MOTORES ACENDEM O MESMO SINAL (F17.4). O laço de qualidade e o
        # de disputa disparavam workflow e nao acendiam nada: a barra ficava muda
        # justamente nas missoes longas. Aqui o teste RODA o bloco que esta escrito
        # na SKILL.md de cada um — se a casa do sinal mudar la, isto quebra aqui.
        print("os outros motores acendem o mesmo sinal, e ele some quando apagam")
        skills = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "..")
        for motor, skill_md in (
                ("qa-loop", os.path.join(skills, "project-skills", "skills",
                                         "qa-loop", "SKILL.md")),
                ("gauntlet", os.path.join(skills, "gauntlet", "skills",
                                          "gauntlet", "SKILL.md"))):
            casa_motor = os.path.join(tmp, "casa-" + motor)
            os.makedirs(casa_motor)
            blocos = _blocos_do_sinal(skill_md)
            check("%s: a SKILL.md tem o bloco que acende o sinal" % motor,
                  bool(blocos))
            env = dict(os.environ, CLAUDE_CONFIG_DIR=casa_motor,
                       CLAUDE_CODE_SESSION_ID="s-" + motor)
            subprocess.run([BASH, "-c", blocos[0]], env=env, check=True,
                           stdin=subprocess.DEVNULL, start_new_session=True)

            casa_sinal = os.path.join(casa_motor, "andamento")
            linha = a.linha_motor("s-" + motor, casa_sinal)
            check("%s: a linha da barra NASCE com o nome dele" % motor,
                  (linha or "").startswith("🚀 %s · Missão há" % motor.capitalize()))

            # E SOME quando o sinal é apagado. No laço de qualidade quem apaga é o
            # segundo bloco da própria skill (o `rm -f` da entrega) e é ele que roda
            # aqui; na disputa quem apaga é a conferência verde, e essa remoção já
            # tem caso próprio (`gauntlet/lib/test_fecho_check.py`, "o fecho verde
            # apaga o sinal") — aqui vale o mesmo caminho, removido.
            if len(blocos) > 1:
                subprocess.run([BASH, "-c", "\n".join(blocos)], env=env,
                               check=True, stdin=subprocess.DEVNULL,
                               start_new_session=True)
            else:
                os.remove(os.path.join(casa_sinal, "ativo-s-" + motor))
            check("%s: sem sinal a linha SOME da barra" % motor,
                  a.linha_motor("s-" + motor, casa_sinal) is None)

        # O PEDIDO DE VER O ANDAMENTO (F17.6). Quem roda e o bloco escrito na
        # SKILL.md de monitorar — se o comando de la mudar, isto quebra aqui.
        print("o pedido de ver o andamento imprime o estado lido do DISCO")
        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(raiz, "skills", "monitorar", "SKILL.md"),
                  encoding="utf-8") as fh:
            blocos = re.findall(r"```bash\n(.*?)```", fh.read(), re.S)
        check("a SKILL.md de monitorar tem o bloco do comando",
              bool(blocos) and "andamento.py" in blocos[0])

        casa_mon = os.path.join(tmp, "casa-monitorar")
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=raiz,
                   CLAUDE_CONFIG_DIR=casa_mon)
        vazio = subprocess.run([BASH, "-c", blocos[0]], env=env,
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               stdin=subprocess.DEVNULL, start_new_session=True)
        check("sem missão de pé o comando diz isso e sai bem",
              vazio.returncode == 0 and "nenhuma missão de pé" in vazio.stdout)

        os.makedirs(os.path.join(casa_mon, "andamento"))
        with open(os.path.join(casa_mon, "andamento", "ativo-s-mon"),
                  "w", encoding="utf-8") as fh:
            fh.write("qa-loop\n")
        vivo = subprocess.run([BASH, "-c", blocos[0]], env=env,
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, start_new_session=True)
        check("com missão de pé imprime a sessão e o motor lidos do disco",
              "s-mon" in vivo.stdout and "🚀 Qa-loop · Missão há" in vivo.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── A DOC DA ONDA VIRA REGISTRO EM DISCO (S-111) ────────────────────────────
    tmp_doc = tempfile.mkdtemp()
    try:
        a.doc_da_onda("s-doc", 2, [".claude/docs/architecture.md"], tmp_doc)  # casa-ok: fixture de teste, o literal e o dado do caso
        reg = a.ultima_doc("s-doc", tmp_doc)
        check("grava os caminhos confirmados por sessão",
              reg.get("docs") == [".claude/docs/architecture.md"]  # casa-ok: fixture de teste, o literal e o dado do caso
              and str(reg.get("round")) == "2")
        check("lista vazia não escreve nada",
              a.doc_da_onda("s-vazia", 3, [], tmp_doc) == []
              and not os.path.exists(os.path.join(tmp_doc, "doc-s-vazia")))
        check("diretório impossível é fail-open, não exceção",
              a.doc_da_onda("s-ro", 1, ["x.md"],
                            os.path.join(tmp_doc, "doc-s-doc", "sub")) == ["x.md"])
        cli = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "andamento.py"),
             "doc", "s-cli", "4", "a.md", "b.md"],
            env=dict(os.environ, CLAUDE_CONFIG_DIR=tmp_doc),
            stdin=subprocess.DEVNULL, start_new_session=True,
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        check("a CLI que o papel de doc chama grava na casa do estado",
              cli.returncode == 0
              and a.ultima_doc("s-cli", os.path.join(tmp_doc, "andamento")
                               ).get("docs") == ["a.md", "b.md"])
    finally:
        shutil.rmtree(tmp_doc, ignore_errors=True)

    # ── O `encerra` SÓ APAGA O SINAL DE QUEM É DONO DELE ────────────────────────
    # `ativo-<sid>` é compartilhado de propósito: sprint, qa-loop e gauntlet gravam
    # o MESMO arquivo, cada um com o próprio nome na linha 1 — é assim que o gate
    # `pretooluse-motor-arma.sh` decide se age (`DONO=$(head -n 1 …)`). O `encerra`
    # apagava sem ler nada, então o sprint terminando derrubava a barra e o estado
    # da missão do gauntlet que seguia viva na mesma sessão.
    print("o encerra confere de quem é o sinal antes de apagar")
    tmp_dono = tempfile.mkdtemp()
    try:
        andamento_py = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "andamento.py")
        casa = os.path.join(tmp_dono, "andamento")
        os.makedirs(casa)

        def _acende(sid, dono):
            for prefixo in ("ativo-", "onda-"):
                with open(os.path.join(casa, prefixo + sid), "w",
                          encoding="utf-8") as fh:
                    fh.write(dono + "\n")

        def _encerra(*args):
            return subprocess.run(
                [sys.executable, andamento_py, "encerra", *args],
                env=dict(os.environ, CLAUDE_CONFIG_DIR=tmp_dono),
                stdin=subprocess.DEVNULL, start_new_session=True,
                capture_output=True, text=True, encoding="utf-8", errors="replace")

        _acende("s-dono", "gauntlet")
        alheio = _encerra("s-dono", "sprint")
        check("dono divergente sai 0 (fail-open: o comando é chamado com || echo)",
              alheio.returncode == 0)
        check("e NÃO apaga o sinal do outro motor",
              os.path.exists(os.path.join(casa, "ativo-s-dono"))
              and os.path.exists(os.path.join(casa, "onda-s-dono")))

        # A vizinha é do MESMO dono e fica de pé: o `encerra` apaga por SESSÃO, e
        # apagar por dono derrubaria a barra de toda sessão do mesmo motor.
        _acende("s-vizinha", "gauntlet")
        proprio = _encerra("s-dono", "gauntlet")
        check("o dono certo apaga o sinal e o estado da missão",
              proprio.returncode == 0
              and not [x for x in os.listdir(casa) if "s-dono" in x])
        check("e NÃO encosta na outra sessão do mesmo motor",
              sorted(x for x in os.listdir(casa) if "s-vizinha" in x)
              == ["ativo-s-vizinha", "onda-s-vizinha"])

        _acende("s-legado", "sprint")
        legado = _encerra("s-legado")
        check("sem nome de dono o comando segue apagando (chamador antigo)",
              legado.returncode == 0
              and not [x for x in os.listdir(casa) if "s-legado" in x])
    finally:
        shutil.rmtree(tmp_dono, ignore_errors=True)

    # ── A ONDA EM CURSO E O PROGRESSO DO PLANO NA BARRA ─────────────────────────
    # A barra dizia ha quanto tempo a missao estava de pe, nunca em que ponto ela
    # estava: `missao ha 2h14` nao separa a primeira volta da decima.
    print("a onda em curso e o progresso do plano")
    tmp_onda = tempfile.mkdtemp()
    try:
        plano = os.path.join(tmp_onda, "p.plan.json")
        with open(plano, "w", encoding="utf-8") as fh:
            json.dump({"phases": [
                {"id": "F1", "items": [{"id": "F1.1", "status": "done"},
                                       {"id": "F1.2", "status": "done"},
                                       {"id": "F1.3", "status": "todo"}]}]}, fh)
        a.marca_onda("s-onda", "5", plano, tmp_onda)
        check("a onda e o progresso do plano viram uma linha só",
              a.linha_onda("s-onda", tmp_onda) == "Onda 5 · 2/3")
        a.marca_onda("s-so-onda", "2", None, tmp_onda)
        check("sem plano a barra diz a onda e não inventa placar",
              a.linha_onda("s-so-onda", tmp_onda) == "Onda 2")
        a.marca_onda("s-torto", "3", os.path.join(tmp_onda, "nao-existe.json"),
                     tmp_onda)
        check("plano ilegível tira o placar, nunca a onda",
              a.linha_onda("s-torto", tmp_onda) == "Onda 3")
        check("sessão sem onda registrada não inventa linha",
              a.linha_onda("s-nada", tmp_onda) is None)

        # A DOC DA ONDA CHEGA A UMA TELA. O registro de S-111 existia e ninguem o
        # lia — registro que nenhuma tela mostra nao prova nada a ninguem.
        with open(os.path.join(tmp_onda, "ativo-s-doc"), "w",
                  encoding="utf-8") as fh:
            fh.write("sprint\n")
        sem_doc = a.painel(tmp_onda)
        a.doc_da_onda("s-doc", 2, ["a.md", "b.md"], tmp_onda)
        com_doc = a.painel(tmp_onda)
        check("a doc da onda aparece no painel de 'como vai?'",
              any("📄 doc da onda: 2" in x for x in com_doc)
              and not any("doc da onda" in x for x in sem_doc))

        agora = time.time()
        aceso = os.path.join(tmp_onda, "ativo-s-onda")
        with open(aceso, "w", encoding="utf-8") as fh:
            fh.write("sprint\n")
        os.utime(aceso, (agora - 4020, agora - 4020))
        linha = a.linha_motor("s-onda", tmp_onda, agora)
        check("a onda chega à BARRA, com o ícone e o separador do desenho",
              "🌊 Onda 5 · 2/3" in linha and "  │  " in linha)
        check("missão de mais de uma hora sai em horas, não em minutos",
              "Missão há 1h07" in linha)
    finally:
        shutil.rmtree(tmp_onda, ignore_errors=True)

    # ── O SINAL DA SESSÃO MORTA É VARRIDO POR QUEM DESENHA A BARRA ──────────
    # O gate do motor já expirava sinal velho, mas só quando ALGUÉM CONSULTAVA —
    # e quem consulta é a sessão que acendeu. Sessão morta nunca mais pergunta,
    # então o sinal dela nunca expirava: medido em 2026-08-09, CINCO sinais órfãos
    # vivos ao mesmo tempo, o mais velho de 75 horas, todos dizendo "Missão há 75h"
    # na barra. A barra é o único processo que roda com frequência garantida em
    # toda sessão viva — por isso a varredura é dela.
    tmp_exp = tempfile.mkdtemp()
    try:
        morta, viva = "sessao-morta", "sessao-viva"
        for s in (morta, viva):
            for p in ("ativo-", "onda-", "placar-", "doc-"):
                with open(os.path.join(tmp_exp, p + s), "w", encoding="utf-8") as fh:
                    fh.write("motor\n")
        antigo = time.time() - 75 * 3600
        for p in ("ativo-", "onda-", "placar-", "doc-"):
            os.utime(os.path.join(tmp_exp, p + morta), (antigo, antigo))

        check("a sessão VIVA continua desenhando a linha",
              a.linha_motor(viva, tmp_exp) is not None)
        check("a sessão MORTA some da barra", a.linha_motor(morta, tmp_exp) is None)
        check("o sinal da sessão morta foi APAGADO do disco",
              not os.path.exists(os.path.join(tmp_exp, "ativo-" + morta)))
        check("o estado da sessão morta vai junto (onda, placar, doc)",
              not [x for x in os.listdir(tmp_exp) if morta in x])
        check("nada da sessão viva foi tocado",
              len([x for x in os.listdir(tmp_exp) if viva in x]) == 4)
        check("a expiração fica registrada, não some calada",
              "morta" in open(os.path.join(tmp_exp, "expirados.log"),
                              encoding="utf-8").read())
    finally:
        shutil.rmtree(tmp_exp, ignore_errors=True)

    # ── O VIGIA OLHA VIDA, NÃO SÓ IDADE ─────────────────────────────────────
    # A trava de incêndio (12h) é lenta demais para o que o dono viu na tela:
    # "SEM SINAL há 6h02" com a missão já terminada, e ainda seis horas até ela
    # agir. O segundo critério mata em 2h — mas exige as DUAS pontas (narrador
    # calado E nada de pé), porque cada uma sozinha mente: suíte de 20 min cala
    # o narrador sem a missão morrer, e `trabalho-` esquecido finge vida eterna.
    tmp_vig = tempfile.mkdtemp()
    try:
        agora = time.time()

        def cria(sid, idade_h, mudo_min=None, trabalho_min=None):
            p = os.path.join(tmp_vig, "ativo-" + sid)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("gauntlet\n")
            t = agora - idade_h * 3600
            os.utime(p, (t, t))
            if mudo_min is not None:
                s = os.path.join(tmp_vig, "sinal-" + sid)
                with open(s, "w", encoding="utf-8") as fh:
                    fh.write("x")
                ts = agora - mudo_min * 60
                os.utime(s, (ts, ts))
            if trabalho_min is not None:
                with open(os.path.join(tmp_vig, "trabalho-" + sid), "w",
                          encoding="utf-8") as fh:
                    fh.write("%d\npytest\nproj\n" % int(agora - trabalho_min * 60))

        cria("viva-narrando", 2, mudo_min=1)                       # fala agora
        cria("morta-muda", 10, mudo_min=360)                       # 6h calada, nada de pé
        cria("suite-longa", 3, mudo_min=180, trabalho_min=175)     # calada, MAS rodando
        cria("velha", 80, mudo_min=1)                              # fala, mas 80h de idade
        cria("nunca-narrou", 3)                                    # sem sinal-: só a idade
        mortos = set(a.expira_sinais(tmp_vig, agora))

        check("a missão calada há 6h morre pelo vigia, sem esperar as 12h",
              "morta-muda" in mortos)
        check("a suíte longa SOBREVIVE — está calada, mas tem ferramenta de pé",
              "suite-longa" not in mortos)
        check("quem está narrando agora sobrevive", "viva-narrando" not in mortos)
        check("a trava de incêndio de 12h continua valendo", "velha" in mortos)
        check("sem `sinal-` no disco, só a idade decide — e ela não estourou",
              "nunca-narrou" not in mortos)
        log = open(os.path.join(tmp_vig, "expirados.log"), encoding="utf-8").read()
        check("o registro diz QUAL critério agiu (mudo × idade)",
              "\tmudo\t" in log and "\tidade\t" in log)
    finally:
        shutil.rmtree(tmp_vig, ignore_errors=True)

    # ── A BARRA ACOMPANHA O BLOCO, NÃO SÓ A ONDA ────────────────────────────
    # Pedido do dono, 2026-08-09: "as ondas, os blocos e assim por diante. Tudo."
    # Uma onda de três blocos leva quinze minutos, e a barra ficava parada em
    # `Onda 2` o tempo todo — quem olha não sabe se avançou ou travou.
    tmp_blc = tempfile.mkdtemp()
    try:
        with open(os.path.join(tmp_blc, "ativo-s-bloco"), "w", encoding="utf-8") as fh:
            fh.write("sprint\n")
        a.marca_onda("s-bloco", 2, None, tmp_blc)
        check("sem bloco, a linha continua exatamente a de antes",
              a.linha_onda("s-bloco", tmp_blc) == "Onda 2")
        a.marca_onda("s-bloco", 2, None, tmp_blc, etapa="executando", bloco=3)
        check("com bloco e etapa, os dois aparecem na linha",
              a.linha_onda("s-bloco", tmp_blc) == "Onda 2 bloco 3 · executando")
        check("e chegam à BARRA junto do resto",
              "🌊 Onda 2 bloco 3 · executando" in a.linha_motor("s-bloco", tmp_blc))
    finally:
        shutil.rmtree(tmp_blc, ignore_errors=True)

    print("duas execuções na mesma sessão: quem termina primeiro NÃO apaga o aviso da outra")
    # O caso medido em 2026-08-12. O aviso da barra é por SESSÃO e a reserva de
    # arquivos é por sessão E execução; quem encerrava conferia só o DONO, então
    # duas execuções do mesmo dono se apagavam entre si. A barra ficou muda com
    # trabalho de pé, e a trava que impede despachar por fora desarmou junto.
    tmp_duas = tempfile.mkdtemp()
    try:
        a.arma("s-duas", "sprint", "exec-1", tmp_duas)
        a.arma("s-duas", "sprint", "exec-2", tmp_duas)
        check("as duas execuções ficam registradas, sem duplicar",
              a.execucoes("s-duas", tmp_duas) == [("sprint", "exec-1"), ("sprint", "exec-2")])
        check("armar a mesma execução de novo não duplica a linha",
              a.arma("s-duas", "sprint", "exec-2", tmp_duas) ==
              [("sprint", "exec-1"), ("sprint", "exec-2")])
        check("o aviso guarda o dono na primeira linha, como o gate espera",
              open(os.path.join(tmp_duas, "ativo-s-duas"),
                   encoding="utf-8").readline().strip() == "sprint")

    finally:
        shutil.rmtree(tmp_duas, ignore_errors=True)

    print("o comando de encerrar só derruba o aviso quando não sobra execução de pé")
    # O comando é o que o motor chama de verdade no último ato dele, então é ele
    # que precisa provar o conserto — a função sozinha não cobre o caminho real.
    casa = tempfile.mkdtemp()
    estado = os.path.join(casa, "andamento")
    try:
        os.makedirs(estado, exist_ok=True)
        a.arma("s-cli", "sprint", "exec-1", estado)
        a.arma("s-cli", "sprint", "exec-2", estado)
        amb = dict(os.environ, CLAUDE_CONFIG_DIR=casa)
        primeiro = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(a.__file__), "andamento.py"),
             "encerra", "s-cli", "sprint", "exec-1"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=amb,
            stdin=subprocess.DEVNULL, start_new_session=True)
        check("encerrar a primeira diz que outra continua de pé",
              "ainda de pé" in primeiro.stdout)
        check("e o aviso da barra continua no disco",
              os.path.exists(os.path.join(estado, "ativo-s-cli")))
        check("só a execução encerrada saiu do registro",
              a.execucoes("s-cli", estado) == [("sprint", "exec-2")])
        ultimo = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(a.__file__), "andamento.py"),
             "encerra", "s-cli", "sprint", "exec-2"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=amb,
            stdin=subprocess.DEVNULL, start_new_session=True)
        check("encerrar a última apaga o aviso",
              "encerrada na barra" in ultimo.stdout
              and not os.path.exists(os.path.join(estado, "ativo-s-cli")))
    finally:
        shutil.rmtree(casa, ignore_errors=True)

    print("id que não está registrado NÃO apaga nada, e diz isso")
    # Quem escreve o id na mão é a casca, no retorno da chamada do motor. Colar o
    # `motor-…` do exemplo saía com a MESMA linha do caso legítimo ("encerrada; N
    # ainda de pé"), então o sinal ficava aceso sem ninguém perceber.
    casa_id = tempfile.mkdtemp()
    estado_id = os.path.join(casa_id, "andamento")
    try:
        os.makedirs(estado_id, exist_ok=True)
        a.arma("s-id", "sprint", "motor-real-123", estado_id)
        errado = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(a.__file__), "andamento.py"),
             "encerra", "s-id", "sprint", "motor-…"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, CLAUDE_CONFIG_DIR=casa_id),
            stdin=subprocess.DEVNULL, start_new_session=True)
        check("o aviso diz que nada foi apagado, e mostra quem está de pé",
              "NADA foi apagado" in errado.stdout and "motor-real-123" in errado.stdout)
        check("o registro fica intacto",
              a.execucoes("s-id", estado_id) == [("sprint", "motor-real-123")])
        certo = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(a.__file__), "andamento.py"),
             "encerra", "s-id", "sprint", "motor-real-123"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, CLAUDE_CONFIG_DIR=casa_id),
            stdin=subprocess.DEVNULL, start_new_session=True)
        check("com o id certo, o aviso cai",
              "encerrada na barra" in certo.stdout
              and not os.path.exists(os.path.join(estado_id, "ativo-s-id")))
    finally:
        shutil.rmtree(casa_id, ignore_errors=True)

    print("aviso apagado com execução viva é REACESO pela varredura da barra")
    # A metade que faltava: `expira_sinais` apagava aviso velho sem execução, e
    # nada devolvia o aviso que caiu cedo demais. Sem isto, o conserto do
    # encerramento não alcança o aviso já perdido nem o motor que morreu de vez.
    tmp_res = tempfile.mkdtemp()
    try:
        a.arma("s-res", "sprint", "exec-viva", tmp_res)
        os.remove(os.path.join(tmp_res, "ativo-s-res"))
        check("o aviso sumiu, mas a execução continua registrada",
              not os.path.exists(os.path.join(tmp_res, "ativo-s-res"))
              and a.execucoes("s-res", tmp_res) == [("sprint", "exec-viva")])
        check("a varredura devolve o aviso ao disco",
              a.ressuscita_sinais(tmp_res) == ["s-res"]
              and os.path.exists(os.path.join(tmp_res, "ativo-s-res")))
        check("e o dono reaceso é o da primeira execução registrada",
              open(os.path.join(tmp_res, "ativo-s-res"),
                   encoding="utf-8").readline().strip() == "sprint")
        check("rodar de novo não reacende nada, porque o aviso já está de pé",
              a.ressuscita_sinais(tmp_res) == [])

        # registro velho NÃO reacende: seria ressuscitar o que a outra varredura mata
        velho = os.path.join(tmp_res, "motorid-s-velha")
        with open(velho, "w", encoding="utf-8") as fh:
            fh.write("sprint\texec-antiga\n")
        antigo = time.time() - (a.TTL_SINAL_MIN + 60) * 60
        os.utime(velho, (antigo, antigo))
        check("registro mais velho que o teto do aviso não reacende nada",
              a.ressuscita_sinais(tmp_res) == []
              and not os.path.exists(os.path.join(tmp_res, "ativo-s-velha")))
        check("e o registro velho é apagado, em vez de ficar tentando para sempre",
              not os.path.exists(velho))
    finally:
        shutil.rmtree(tmp_res, ignore_errors=True)

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
