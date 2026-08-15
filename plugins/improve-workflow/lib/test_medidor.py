#!/usr/bin/env python3
"""Bancada do medidor.py sobre a fixture de run em ../fixtures/run-exemplo.

O que a fixture existe para provar, e cada item já mentiu num run real:
  - o papel sai do PROMPT (nenhum campo do transcript o traz);
  - streaming NÃO conta turno: 3 linhas com o mesmo requestId são um turno só,
    e o gasto vale a ÚLTIMA linha (a única com o output final);
  - agente que voltou sem resultado aparece, apesar de ter custado.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import medidor  # noqa: E402
import plano_saida  # noqa: E402
import sobras  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "fixtures")
RUN = os.path.join(FIXTURES, "run-exemplo")
RUN_SAO = os.path.join(FIXTURES, "run-sao")
# uma fixture por sinal — o sinal que só acende junto de outro nunca prova nada sozinho
RUN_REPETIDO = os.path.join(FIXTURES, "run-repetido")
RUN_FANTASMA = os.path.join(FIXTURES, "run-fantasma")
RUN_ESPERA = os.path.join(FIXTURES, "run-espera")
RUN_MORTO = os.path.join(FIXTURES, "run-morto")
RUN_VAZIO = os.path.join(FIXTURES, "run-vazio")
# run que o dono interrompeu: transcript e journal param no meio de uma linha
RUN_CORTADO = os.path.join(FIXTURES, "run-cortado")
# o par invertido: do primeiro para o segundo o turno cai e a falha sobe
RUN_PAR_ANTES = os.path.join(FIXTURES, "run-par-antes")
RUN_PAR_DEPOIS = os.path.join(FIXTURES, "run-par-depois")
# o projeto de quem instalou o plugin: sem missão no disco, sem plano, sem irmãos
PROJETO_ALHEIO = os.path.join(FIXTURES, "projeto-alheio")

FALHAS = []


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def caso_papel():
    check("papel sai do 'Você é o X' do prompt",
          medidor.papel_do_prompt("Você é o EXECUTOR (Sonnet). Implemente.") == "EXECUTOR")
    check("sem acento e em caixa alta também casa",
          medidor.papel_do_prompt("VOCE E O REVISOR e ADJUDICADOR (Opus).") == "REVISOR")
    check("papel mecânico se anuncia por marcador, não por nome",
          medidor.papel_do_prompt("Papel MECÂNICO: só grave.") == "MECANICO")
    check("prompt sem papel nenhum não inventa um",
          medidor.papel_do_prompt("Faça o que estiver escrito no plano.") == "DESCONHECIDO")


def caso_papel_declarado():
    """S-123: o papel é DECLARADO pelo motor, não adivinhado por frase. O caso
    REESCREVE o texto do prompt — some o "Você é o X", muda a prosa inteira — e
    pergunta se a classificação fica de pé."""
    original = ("Você é o EXECUTOR (Opus 5). Implemente esta tarefa no repositório.")
    reescrito = ("PAPEL: EXECUTOR\nSubagente de implementação. Faça o que estiver "
                 "escrito na tarefa e devolva o resultado.")
    check("o texto original ainda classifica (o controle)",
          medidor.papel_do_prompt(original) == "EXECUTOR")
    check("com o texto reescrito, a declaração segura a classificação",
          medidor.papel_do_prompt(reescrito) == "EXECUTOR")
    check("a declaração ganha da frase que diria outro papel",
          medidor.papel_do_prompt("PAPEL: MARCAR\nVocê é o EXECUTOR do plano.") == "MARCAR")
    check("prompt reescrito e SEM declaração vira o não-classificado, não um palpite",
          medidor.papel_do_prompt(reescrito.split("\n", 1)[1]) == "DESCONHECIDO")


def caso_agente():
    a = medidor.medir_agente(os.path.join(RUN, "agent-aexec01.jsonl"))
    check("acha o papel do agente", a["papel"] == "EXECUTOR")
    check("3 requestIds em 9 linhas = 3 turnos", a["turnos"] == 3)
    check("output soma só a última linha de cada turno",
          a["tokens"]["output_tokens"] == 50 + 80 + 40)
    check("cache_read é o que mais pesa e não é duplicado",
          a["tokens"]["cache_read_input_tokens"] == 6000)
    check("total é a soma dos quatro campos",
          a["tokens"]["total"] == 120 + 700 + 6000 + 170)


def caso_run():
    r = medidor.medir_run(RUN)
    por_papel = {p["papel"]: p for p in r["papeis"]}
    check("consolida os dois executores num papel só",
          por_papel["EXECUTOR"]["agentes"] == 2 and por_papel["EXECUTOR"]["turnos"] == 5)
    check("turnos/agente do executor", por_papel["EXECUTOR"]["turnos_por_agente"] == 2.5)
    check("papel mecânico com 4 turnos aparece medido",
          por_papel["MECANICO"]["agentes"] == 1
          and por_papel["MECANICO"]["turnos_por_agente"] == 4.0)
    check("papel não anunciado cai em DESCONHECIDO", "DESCONHECIDO" in por_papel)
    check("a tabela vem ordenada do mais caro para o mais barato",
          [p["tokens"]["total"] for p in r["papeis"]]
          == sorted([p["tokens"]["total"] for p in r["papeis"]], reverse=True))
    check("total de agentes bate com os arquivos", r["total"]["agentes"] == 4)
    check("total de turnos é a soma dos papéis",
          r["total"]["turnos"] == sum(p["turnos"] for p in r["papeis"]))
    check("agente que voltou vazio é nomeado", r["resultados_vazios"] == ["aoutro01"])


def sinal(dir_run, nome):
    for s in medidor.medir_run(dir_run)["sinais"]:
        if s["sinal"] == nome:
            return s["casos"]
    raise AssertionError("sinal inexistente: %s" % nome)


def caso_voltas_demais():
    """Primeiro sinal: papel mecânico acima do teto de turnos."""
    doente = {p["papel"]: p for p in medidor.medir_run(RUN)["papeis"]}
    sao = {p["papel"]: p for p in medidor.medir_run(RUN_SAO)["papeis"]}
    check("run com o defeito: mecânico de 4 turnos/agente sai suspeito",
          doente["MECANICO"]["suspeito"] is True)
    check("run são: mecânico dentro do teto não sai suspeito",
          sao["MECANICO"]["turnos_por_agente"] == 2.0
          and sao["MECANICO"]["suspeito"] is False)
    check("papel não mecânico com muitos turnos nunca é suspeito",
          sao["EXECUTOR"]["turnos_por_agente"] == 4.0
          and sao["EXECUTOR"]["suspeito"] is False
          and doente["EXECUTOR"]["suspeito"] is False)
    check("o teto é 2 turnos, como a autópsia mediu",
          medidor.TETO_TURNOS_MECANICO == 2)


def caso_ponteiro():
    """O endereço do trecho, não o trecho: arquivo + linha, e nada do conteúdo."""
    doente = {p["papel"]: p for p in medidor.medir_run(RUN)["papeis"]}
    sao = {p["papel"]: p for p in medidor.medir_run(RUN_SAO)["papeis"]}
    a = medidor.medir_agente(os.path.join(RUN, "agent-aexec01.jsonl"))
    check("cada turno tem a linha onde começa",
          len(a["linhas_dos_turnos"]) == a["turnos"]
          and a["linhas_dos_turnos"] == sorted(a["linhas_dos_turnos"]))
    mec = doente["MECANICO"]["ponteiro"]
    check("papel suspeito aponta pro primeiro turno acima do teto",
          mec["turno"] == medidor.TETO_TURNOS_MECANICO + 1)
    check("o ponteiro é arquivo existente + linha real do arquivo",
          os.path.isfile(mec["arquivo"])
          and 1 <= mec["linha"] <= sum(1 for _ in open(mec["arquivo"], encoding="utf-8")))
    check("papel são aponta pro primeiro turno",
          sao["MECANICO"]["ponteiro"]["turno"] == 1)
    check("o ponteiro é do agente mais falador do papel",
          doente["EXECUTOR"]["ponteiro"]["agente"] == "aexec01")
    check("nenhum campo do ponteiro carrega conteúdo do transcript",
          set(mec) == {"agente", "arquivo", "linha", "turno"})


def caso_comando_repetido():
    """O caso real de 2026-08-08: quatro agentes rodando o mesmo `ls` para
    redescobrir, cada um por si, para onde o arquivo tinha sido movido."""
    casos = sinal(RUN_REPETIDO, "comando_repetido")
    check("o comando redescoberto por 4 agentes acende o sinal",
          any(c["agentes"] == 4 and c["comando"].startswith("ls ") for c in casos))
    check("o caso traz o endereço do primeiro disparo",
          all(os.path.isfile(c["arquivo"]) and c["linha"] >= 1 for c in casos))
    check("run sem comando nenhum não acende", sinal(RUN, "comando_repetido") == [])
    check("dois agentes ainda é coincidência, três é redescoberta",
          medidor.TETO_AGENTES_REPETINDO == 3)


def caso_caminho_fantasma():
    casos = sinal(RUN_FANTASMA, "caminho_fantasma")
    check("a raiz minoritária é acusada, a majoritária é a árvore",
          len(casos) == 1 and casos[0]["raiz"].endswith("/worktrees/velho")
          and casos[0]["raiz_da_arvore"] == "/projeto")
    check("run com uma raiz só não acende", sinal(RUN_REPETIDO, "caminho_fantasma") == [])


def caso_trabalho_fantasma():
    check("passo que saiu esperando o dono e recebeu trabalho depois acende",
          sinal(RUN_ESPERA, "trabalho_fantasma")
          == [{"task_id": "F9", "agente": "adiag01", "tokens": 4300}])
    check("passo que só esperou, sem trabalho depois, não acende",
          sinal(RUN_VAZIO, "trabalho_fantasma") == [])
    # nomear o passo sem somar o gasto deixa o defeito com cara de detalhe
    fantasma = [s for s in medidor.medir_run(RUN_ESPERA)["sinais"]
                if s["sinal"] == "trabalho_fantasma"][0]
    check("o sinal soma o que o trabalho sobre passo parado custou",
          fantasma["tokens"] == 4300)
    limpo = [s for s in medidor.medir_run(RUN_VAZIO)["sinais"]
             if s["sinal"] == "trabalho_fantasma"][0]
    check("sem caso nenhum, o gasto somado é 0", limpo["tokens"] == 0)


def caso_resultado_vazio():
    check("agente que voltou sem valor de retorno acende",
          sinal(RUN_VAZIO, "resultado_vazio") == [{"agente": "amarca01"}])
    check("run sem journal não acende", sinal(RUN_SAO, "resultado_vazio") == [])


def caso_agente_morto():
    check("agente que começou e nunca registrou resultado acende",
          sinal(RUN_MORTO, "agente_morto") == [{"agente": "aexec02"}])
    check("run onde todo mundo concluiu não acende", sinal(RUN_ESPERA, "agente_morto") == [])


def caso_seis_sinais():
    r = medidor.medir_run(RUN)
    check("são seis sinais, sempre os mesmos e sempre na saída",
          [s["sinal"] for s in r["sinais"]]
          == ["voltas_demais", "comando_repetido", "caminho_fantasma",
              "trabalho_fantasma", "resultado_vazio", "agente_morto"])
    check("cada sinal se explica em uma frase", all(s["titulo"] for s in r["sinais"]))
    check("o agente na saída não carrega comando de transcript",
          all("comandos" not in a for a in r["agentes"]))


def caso_run_cortado():
    """Interrupção é o caso comum: o run de 2026-08-08 foi cortado três vezes.
    Medir o que deu e NOMEAR o que faltou — nunca estourar, nunca fingir inteiro."""
    r = medidor.medir_run(RUN_CORTADO)
    check("os turnos que fecharam continuam medidos",
          r["total"]["turnos"] == 2 and r["total"]["tokens"] > 0)
    cortados = {os.path.basename(i["arquivo"]): i["linha"] for i in r["incompleto"]}
    check("o transcript cortado é nomeado com a linha onde parou",
          cortados.get("agent-aexec01.jsonl") == 4)
    check("o journal cortado também é nomeado",
          cortados.get("journal.jsonl") == 4)
    check("o journal lido até onde deu ainda acende o que sabe",
          sinal(RUN_CORTADO, "agente_morto") == [{"agente": "aexec02"}])
    check("run inteiro não tem nada de incompleto",
          medidor.medir_run(RUN)["incompleto"] == [])
    check("run cortado sai com 0, não com estouro", medidor.main([RUN_CORTADO]) == 0)


def caso_par_turno_e_falha():
    """Turno nunca sai sozinho: cada papel publica também a taxa de falha, tirada
    do registro do run. E o par invertido — turno caindo, falha subindo — acende."""
    antes = medidor.medir_run(RUN_PAR_ANTES)
    depois = medidor.medir_run(RUN_PAR_DEPOIS)
    check("todo papel publica o par turno + taxa de falha",
          all("turnos_por_agente" in p and "taxa_falha" in p
              for r in (medidor.medir_run(RUN), antes, depois) for p in r["papeis"]))
    check("a taxa sai do registro do run: 1 de 2 agentes sem entrega = 0.5",
          depois["papeis"][0]["taxa_falha"] == 0.5 and depois["papeis"][0]["falhas"] == 1)
    check("run sem registro nenhum não inventa taxa 0",
          all(p["taxa_falha"] is None for p in medidor.medir_run(RUN_SAO)["papeis"]))
    falhos = medidor.falhas_do_journal(medidor.eventos_do_journal(RUN_ESPERA)[0])
    check("parar no teto e devolver espera não conta como falha",
          "aexec01" not in falhos and "adiag01" in falhos)
    casos = medidor.par_invertido(antes, depois)
    check("turno caindo com falha subindo acende o aviso",
          len(casos) == 1 and casos[0]["papel"] == "EXECUTOR"
          and casos[0]["turnos_por_agente"] == [3.0, 1.0]
          and casos[0]["taxa_falha"] == [0.0, 0.5])
    check("o par no sentido certo — turno subindo, falha caindo — não acende",
          medidor.par_invertido(depois, antes) == [])
    check("a comparação pela linha de comando sai com 0",
          medidor.main([RUN_PAR_DEPOIS, "--contra", RUN_PAR_ANTES]) == 0)


def caso_cli():
    check("run existente sai com 0", medidor.main([RUN]) == 0)
    check("--json sai com 0", medidor.main([RUN, "--json"]) == 0)
    check("run inexistente sai com 2", medidor.main([os.path.join(RUN, "nao-existe")]) == 2)


def _base_falsa(tmp, nomes, projeto="proj", base=None):
    """Um disco de mentira no formato real: <projeto>/<sessão>/subagents/workflows/<run>.
    A ordem de `nomes` é a ordem de mtime — o último é o mais recente."""
    base = base or os.path.join(tmp, "projects")
    for i, nome in enumerate(nomes):
        d = os.path.join(base, projeto, "sessao", "subagents", "workflows", nome)
        os.makedirs(d)
        os.utime(d, (1_000_000 + i * 60, 1_000_000 + i * 60))
    return base


def caso_escolha_do_run():
    """As três situações: sem run nenhum, com vários, e pelo nome."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        vazia = os.path.join(tmp, "projects")
        os.makedirs(vazia)
        dir_run, erro = medidor.resolver_run(base=vazia, projeto="proj")
        check("sem run nenhum não escolhe nada e diz o porquê",
              dir_run is None and erro and "nenhum run" in erro)
        os.environ["CLAUDE_CONFIG_DIR"] = tmp
        try:
            # S-132: a rodada AVISA (o texto acima) e sai zero — quem não pediu
            # run nenhum não errou o uso, só não tem missão medida no disco.
            check("sem run nenhum a rodada avisa e sai com 0", medidor.main([]) == 0)
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]

    with tempfile.TemporaryDirectory() as tmp:
        base = _base_falsa(tmp, ["wf_velho", "wf_meio", "wf_novo"])
        check("com vários, o padrão é o mais recente",
              os.path.basename(medidor.resolver_run(base=base, projeto="proj")[0]) == "wf_novo")
        # basename, não endswith("/..."): no Windows o separador é "\\" e a
        # comparação nunca casava — o mesmo defeito de barra da linha de cima.
        check("o id do run escolhe o run, não o mais recente",
              os.path.basename(medidor.resolver_run("wf_velho", base=base,
                                                    projeto="proj")[0]) == "wf_velho")
        check("id que não existe vira erro, não um palpite",
              medidor.resolver_run("wf_nao_existe", base=base, projeto="proj") == (
                  None, "run não encontrado: wf_nao_existe"))
        check("caminho continua valendo como caminho",
              medidor.resolver_run(RUN, base=base, projeto="proj")[0] == RUN)

    with tempfile.TemporaryDirectory() as tmp:
        # run que existe mas está vazio não é erro: é um aviso e saída zero.
        check("run sem agent-*.jsonl avisa e sai com 0", medidor.main([tmp]) == 0)


def caso_run_de_outra_missao():
    """F6.5, medido em 2026-08-15: o mais recente do DISCO era de outra missão, e a
    autópsia leu transcript que fala de arquivos que não existem aqui. O run desta
    missão chega pelo ID, e run que mora na pasta de outro projeto é RECUSADO."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        base = _base_falsa(tmp, ["wf_daqui"], projeto="proj")
        # o de fora é criado DEPOIS: no disco inteiro ele é o mais recente
        _base_falsa(tmp, ["wf_de_fora"], projeto="outro-proj", base=base)
        os.utime(os.path.join(base, "outro-proj", "sessao", "subagents", "workflows",
                              "wf_de_fora"), (2_000_000, 2_000_000))
        dir_run, erro = medidor.resolver_run(base=base, projeto="proj")
        check("o padrão é o run desta missão, não o mais recente do disco",
              erro is None and os.path.basename(dir_run) == "wf_daqui")
        _, erro = medidor.resolver_run("wf_de_fora", base=base, projeto="proj")
        check("run de outra missão pedido pelo id é recusado, e o dono é nomeado",
              erro is not None and "outra missão" in erro and "outro-proj" in erro)
        check("nada de outra missão é medido: a recusa não devolve diretório",
              medidor.resolver_run("wf_de_fora", base=base, projeto="proj")[0] is None)
        check("o mesmo id, medido de dentro da missão dona, resolve",
              os.path.basename(medidor.resolver_run("wf_de_fora", base=base,
                                                    projeto="outro-proj")[0]) == "wf_de_fora")
    # A entrada é um caminho JÁ absoluto na máquina que roda — `/tmp/a.b/c` não é
    # absoluto no Windows (`ntpath.isabs` devolve False), o `abspath` colava a letra do
    # drive na frente, e a asserção reprovava só nos runners de lá. O que se mede aqui
    # é a troca de pontuação por traço, não a forma do caminho: então o caminho vem de
    # `os.path.abspath`, que é absoluto em qualquer sistema.
    absoluto = os.path.abspath(os.path.join("a.b", "c"))
    check("o nome da pasta do projeto é o caminho absoluto sem pontuação",
          medidor.projeto_atual(absoluto)
          == re.sub(r"[^A-Za-z0-9]", "-", absoluto))


def caso_projeto_alheio():
    """S-132: a rodada no projeto de quem INSTALOU o plugin — sem missão no
    disco, sem plano e sem os plugins irmãos. Ela diz o que não pôde medir e sai
    ZERO; travar ali seria acusar defeito onde não houve nem medição."""
    anterior = os.environ.get("CLAUDE_CONFIG_DIR")
    os.environ["CLAUDE_CONFIG_DIR"] = PROJETO_ALHEIO
    try:
        _, erro = medidor.resolver_run()
        check("o medidor nomeia o que não pôde medir",
              bool(erro) and "nenhum run no disco" in erro)
        check("o medidor sai com 0", medidor.main([]) == 0)
        check("a varredura de sobras avisa e sai com 0", sobras.main([]) == 0)
        check("run PEDIDO pelo nome e inexistente continua sendo uso errado (2)",
              medidor.main(["wf_nao_existe"]) == 2)
    finally:
        if anterior is None:
            del os.environ["CLAUDE_CONFIG_DIR"]
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = anterior

    # sem o irmão `project-skills` na máquina, a gravação do plano perde a
    # conferência de schema — e o programa DIZ isso em vez de fingir que conferiu.
    _, aviso = plano_saida.confere_com_plan_state(
        {}, os.path.join(PROJETO_ALHEIO, "plan_state.py"))
    check("sem os irmãos, a gravação do plano avisa que não conferiu", bool(aviso))


def main():
    print("medidor")
    caso_papel()
    caso_papel_declarado()
    caso_agente()
    caso_run()
    caso_voltas_demais()
    caso_ponteiro()
    caso_comando_repetido()
    caso_caminho_fantasma()
    caso_trabalho_fantasma()
    caso_resultado_vazio()
    caso_agente_morto()
    caso_seis_sinais()
    caso_run_cortado()
    caso_par_turno_e_falha()
    caso_cli()
    caso_escolha_do_run()
    caso_run_de_outra_missao()
    caso_projeto_alheio()
    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
