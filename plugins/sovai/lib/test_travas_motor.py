#!/usr/bin/env python3
"""As travas que a reescrita de 2026-08-06 instalou no motor do sovai.

Cada check aqui corresponde a um passo do plano `2026-08-06-a-metodologia-vira-mecanismo`
e cobra a MECANICA, nao a boa intencao: a frase tem que estar no lugar que o motor le
(o esqueleto JS ou o texto que o papel recebe), nao numa secao de filosofia.

O que este arquivo NAO cobre, e por que: a metade de EXECUCAO de cada passo — o motor
rodando de ponta a ponta contra um plano de mentira. Isso e teste de integracao e nao cabe
aqui; o que este arquivo garante e que a LOGICA esta escrita no script, com a direcao
segura. Os dois se somam; nenhum substitui o outro. F9.10, F9.12, F9.13, F9.14 e F9.15 ja
tem a metade de bancada: `test_motor_bancada.py` executa o esqueleto e afere o ARQUIVO do
plano, o desligamento por teto de gasto, a derrubada pelo vigia, a onda verde salva no
historico e a onda vermelha que nao salva e denuncia a suite que quebrou.
"""

import json
import os
import re
import shutil
import subprocess
import sys

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "sovai", "SKILL.md")

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def esqueleto(texto):
    """So o bloco ```javascript do motor — regra que vale pro SCRIPT nao pode ser
    cobrada em prosa solta, senao 'esta escrito' vira 'esta mencionado'."""
    # O MAIOR bloco javascript, nao o primeiro: a skill tem mais de um exemplo em JS
    # (o bloco de esforco do F9.1 vem antes), e pegar o primeiro media o arquivo errado.
    blocos = re.findall(r"```javascript\n(.*?)\n```", texto, re.S)
    return max(blocos, key=len) if blocos else ""


def conversao_do_script(js):
    """A linha do esqueleto que normaliza o parametro — extraida do proprio SKILL.md,
    para que o teste rode O QUE ESTA ESCRITO la, e nao uma copia que envelhece."""
    m = re.search(r"^const ARGS = .*$", js, re.M)
    return m.group(0) if m else ""


def bloco_da_fila(js):
    """O trecho do esqueleto que decide QUEM entra na fila — do `parado` ao
    `esperandoVoce`. Recortado do proprio SKILL.md pelo mesmo motivo do
    `conversao_do_script`: o teste roda o que esta escrito la, nao uma copia."""
    i = js.find("const parado = new Set(")
    j = js.find(".map(t => ({ taskId: t.id, motivo: esperaChain.get(t.id) }))")
    if i < 0 or j < 0:
        return ""
    return js[i:j + len(".map(t => ({ taskId: t.id, motivo: esperaChain.get(t.id) }))")]


def roda_a_fila(bloco, decomp_js, blockers_js="[]"):
    """Executa o bloco da fila com uma decomposicao de mentira e devolve o que
    saiu — a fila e a lista de espera. Sem Node o check nao inventa aprovacao."""
    if not bloco:
        return {"erro": "SEM-BLOCO"}
    if not shutil.which("node"):
        return {"erro": "SEM-NODE"}
    prog = ("const blockers = %s; const decomp = %s;\n%s\n"
            "console.log(JSON.stringify({ fila: todo.map(t => t.id), esperandoVoce }))\n"
            % (blockers_js, decomp_js, bloco))
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    if out.returncode != 0:
        return {"erro": out.stderr.strip()[:200]}
    try:
        return json.loads(out.stdout.strip())
    except ValueError:
        return {"erro": "saida ilegivel: %s" % out.stdout.strip()[:200]}


def roda_em_node(conv, entrada):
    """Executa a linha de conversao com um `args` de mentira. Sem Node na maquina o
    check nao inventa aprovacao: devolve o motivo, e o teste falha."""
    if not conv:
        return "SEM-CONVERSAO"
    if not shutil.which("node"):
        return "SEM-NODE"
    prog = "const args = %s;\n%s\nconsole.log(ARGS.severityFloor)\n" % (entrada, conv)
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else "ERRO: %s" % out.stderr.strip()


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()
    js = esqueleto(texto)
    check("o esqueleto do motor foi encontrado", len(js) > 2000)

    print("F8.2 — o criterio e julgado antes de soltar quem executa")
    check("criterio ruim vira bloqueio, nao tarefa", "kind: 'criterio'" in texto)
    check("a regua e sobre a ORIGEM do valor, nao o caminho do arquivo",
          "regerar o entregável a partir do dado real" in texto
          and "injetar valor inventado" in texto)

    print("F9.1 — o esforco vai escrito DENTRO do texto do script")
    check("a skill manda gerar o bloco como constante literal",
          "não leia de args.tiers" in texto or "não leia de `args.tiers`" in texto)
    check("a skill diz por que o canal em tempo de execucao caiu",
          "chegava `undefined`" in texto and "matava o motor na primeira volta" in texto)

    print("F9.2 — o motor CHAMA a reserva antes de executar")
    # A peca existia e nenhum motor a chamava. O que se cobra aqui e a CHAMADA no
    # SCRIPT, nao a mencao em prosa: mecanismo descrito e nao invocado foi o defeito.
    check("o motor consulta a reserva no script", "reservaPrompt" in js)
    check("a consulta vem ANTES de soltar executor",
          "reservaPrompt" in js and "agent(execPrompt" in js
          and js.index("reservaPrompt") < js.index("agent(execPrompt"))
    check("o que se reserva e a lista de arquivos da onda",
          "arquivosDaOnda" in js and "t.files || []" in js)
    check("recusado, a onda NAO sai",
          re.search(r"reserva\?\.recusado[\s\S]{0,600}?\bbreak\b", js) is not None)
    check("o bloqueio nomeia os arquivos em disputa", "reserva.arquivos" in js)
    check("a skill nomeia o script e o verbo que o motor roda",
          "reserva-de-arquivos.sh reservar" in texto)
    check("o veredito chega por schema, nao por texto solto",
          "RESERVA" in js and "`RESERVA`" in texto)
    check("quem entrega LIBERA a reserva", "reserva-de-arquivos.sh\" liberar" in texto)
    check("a sessao e o motor chegam ao script pelo args",
          "ARGS.sessionId" in js and "ARGS.motorId" in js)

    print("F9.4/F9.5/F9.8 — as tres regras de quem executa")
    check("conferir no disco e o PRIMEIRO passo",
          "CONFIRA NO DISCO ANTES DE IMPLEMENTAR" in texto)
    check("formatar o projeto inteiro aparece como proibido",
          "FORMATAR O PROJETO INTEIRO É PROIBIDO" in texto)
    check("os comandos proibidos sao nomeados, nao so a categoria",
          "prettier --write ." in texto and "ruff format ." in texto)
    check("a sonda nasce fora do alcance da suite",
          "SONDA DE DEPURAÇÃO NASCE FORA DO ALCANCE DA SUÍTE" in texto)
    check("os nomes que a suite coleta sao nomeados",
          "test_*.py" in texto and "*.spec.ts" in texto)
    check("quem revisa segue a MESMA regra da sonda",
          "O revisor manda a sonda dele para fora do alvo da suíte" in texto)

    print("F9.9 — a janela de tempo da sessao nao da pra observar")
    check("a skill separa as duas coisas",
          "O quanto de conversa já foi usado" in texto
          and "Quanto tempo falta na janela da sessão" in texto)
    check("a skill diz a estrategia de parada que sobra",
          "a estratégia de parada, então, não é temporal" in texto.lower()
          or "A estratégia de parada, então, não é temporal" in texto)

    print("F9.10 — o motor escreve no plano o que fez")
    check("o script tica o plano, e no SCRIPT (nao na prosa)", "tickPlanPrompt" in js)
    check("a marcacao leva a prova do executor",
          "evidencia:" in js and "files_touched" in js)
    check("so tica quem devolveu done", "filter(x => x?.done" in js)
    # Sem o comando escrito, `tickPlanPrompt` e um papel sem acao: o marcador nao tem o
    # que rodar e o plano continua parado. O que roda o comando de verdade e o
    # test_motor_bancada.py; aqui se cobra que ele EXISTE na skill.
    check("a skill nomeia o comando que marca o plano",
          "plan_state.py --dir" in texto and "tick <plano> <taskId> --evidencia" in texto)
    check("a prova gravada e a do executor, nao redigida por quem marca",
          "nunca redigida por quem marca" in texto)

    print("F9.12 — disjuntor por consumo")
    check("o teto existe como knob", "tokenBudget" in js)
    # Casa a linha DO DISJUNTOR, nao a aparicao do nome em qualquer lugar: `gastoInicial`
    # tambem aparece no `return`, entao procurar o nome solto deixava passar um disjuntor
    # medindo o gasto do TURNO em vez do da missao. Furo achado por mutacao, 2026-08-06.
    check("o motor mede o DELTA da missao, nao o gasto do turno",
          re.search(r"const gasto = gastoAgora\(\) - gastoInicial", js) is not None)
    check("estourou, ele PARA", re.search(r"desligadoPor = 'orcamento'[\s\S]{0,400}?\bbreak\b", js) is not None)
    check("o relatorio diz quanto gastou e em que rodada",
          "gastou ${gasto} de ${tokenBudget}" in js)
    # O numero tem que chegar ao relatorio FINAL tambem: desligar sem dizer o quanto
    # queimou deixa o dono sem saber se relanca com teto maior ou se corta a missao.
    check("o gasto entra no relatorio final, nao so no bloqueio",
          "o `gasto` (quanto a missão queimou" in texto)

    print("F9.13 + F9.24 — vigia por tempo, que separa demora de travamento")
    check("o limite de silencio existe", "silenceLimitMs" in js)
    check("a condicao e DUPLA: mudo E sem trabalho vivo",
          "mudo > silenceLimitMs && !suite?.trabalhoVivo" in js)
    check("trabalho vivo esta no schema que a suite devolve", "trabalhoVivo" in texto)
    check("o vigia derruba parando o laco",
          re.search(r"desligadoPor = 'vigia'[\s\S]{0,400}?\bbreak\b", js) is not None)
    check("o blocker distingue travamento de demora",
          "travamento, não demora" in js)

    print("F9.14 + F9.15 — ponto de salvamento por onda, e onda vermelha nao salva")
    check("a suite roda ao fim de CADA onda, dentro do laco", "runSuitePrompt" in js)
    check("onda verde vira checkpoint", "suite.green" in js and "checkpointPrompt" in js)
    check("onda vermelha NAO vira checkpoint",
          js.index("checkpointPrompt") < js.index("a suíte quebrou na rodada"))
    check("a skill nomeia o comando que grava a onda no historico",
          re.search(r"git -C <raiz> add -A && git -C <raiz> commit .*<r>", texto) is not None)
    check("o salvamento e local: o push e uma vez, no fim", "Commit **local e só**" in texto)
    check("a suite morta tambem nao salva (direcao segura)",
          "a suíte da rodada ${r} não respondeu" in js)
    check("o relato diz QUAL suite quebrou", "suite.failing?.join" in js)

    print("F9.16 — quem julga prova que leu a coisa inteira")
    check("o veredito exige a ancora do fim", "âncora do fim" in texto)
    check("veredito sem ancora e RECUSADO", "é **recusado**" in texto)
    check("a ancora entra no schema do executor", "**`anchor`**" in texto)

    print("F9.18 + F9.21 — auditor com a lente invertida")
    check("bloqueio repetido convoca auditor, nao encerra",
          "não encerra nada sozinho" in texto)
    check("o onus e do auditor provar que NAO da", "lente invertida" in texto)
    check("o auditor lista o que o executor nem tentou",
          "quais o executor nem tentou" in texto)
    check("os dois desfechos estao escritos",
          "derruba** a alegação devolve a tarefa ao loop" in texto
          and "confirma** encerra a tarefa como impedimento real" in texto)

    print("F9.19 — o relatorio separa impedimento de falta de tempo")
    check("as duas listas saem separadas do motor",
          "impedidos" in js and "naoDeuTempo" in js)
    check("cada impedimento carrega o motivo", "motivo: b.what" in js)
    check("a diferenca entre os dois esta escrita",
          "impedimento não sai com mais tempo" in js)

    print("F9.20 — quem depende de passo parado nasce parado")
    check("o bloqueio se propaga por transitividade",
          "cresceu" in js and "dependsOn" in js and "parado.add(t.id)" in js)
    check("quem espera sai da fila de execucao",
          "!parado.has(t.id)" in js and "esperando" in js)

    print("F8.4 — passo que espera um ato do dono nao e tentado, e quem depende espera junto")
    check("o campo esta declarado no schema do decompositor",
          "esperaDono?: string" in texto)
    check("o decompositor COPIA do plano, nao julga",
          "o `espera_dono` do passo no `.plan.json` vira `esperaDono`" in texto)
    check("a espera tem secao propria no relatorio, fora de Bloqueios",
          "### Esperando você (não é falha)" in texto)
    # A METADE DE EXECUCAO: o bloco da fila roda de verdade, com uma decomposicao em que
    # F1 espera o dono, F2 depende de F1 e F3 nao depende de ninguem. Cobrar so a frase
    # deixaria passar um motor que escreve a regra e solta o executor assim mesmo.
    bloco = bloco_da_fila(js)
    decomp = ("{ tasks: ["
              "{ id: 'F1', esperaDono: 'publicar o site' },"
              "{ id: 'F2', dependsOn: ['F1'] },"
              "{ id: 'F3', dependsOn: [] }] }")
    saiu = roda_a_fila(bloco, decomp)
    check("o bloco da fila foi encontrado e rodou", "erro" not in saiu)
    check("o passo que espera o dono NAO entra na fila", saiu.get("fila") == ["F3"])
    ev = {x["taskId"]: x["motivo"] for x in saiu.get("esperandoVoce", [])}
    check("os DOIS saem como espera, nao somem", sorted(ev) == ["F1", "F2"])
    check("o motivo de quem espera nomeia o ATO do dono",
          "publicar o site" in ev.get("F1", ""))
    check("o motivo de quem depende nomeia de QUEM depende",
          "F1" in ev.get("F2", "") and "espera você" in ev.get("F2", ""))
    # Tarefa parada por `blocker` ja sai em `impedidos`: repetir aqui mandaria o dono
    # agir duas vezes pelo mesmo motivo.
    so_blocker = roda_a_fila(bloco, "{ tasks: [{ id: 'F1' }] }", "[{ taskId: 'F1' }]")
    check("bloqueio comum sai da fila mas NAO vira espera",
          so_blocker.get("fila") == [] and so_blocker.get("esperandoVoce") == [])

    print("F9.23 — o vigia narra na tela principal")
    check("a narracao e REGUA, nao lista de eventos",
          "Toda mudança de estado vira uma linha" in texto)
    check("rodada sem mudanca fica calada", "fica calada" in texto)
    check("as linhas vem do modulo, nao de prosa improvisada",
          "lib/andamento.py" in texto)
    check("a estimativa por media global esta PROIBIDA por escrito",
          "Nunca estime por média global" in texto)
    check("a medicao que sustenta a proibicao esta colada",
          "660,4s" in texto and "299 transcritos" in texto)
    check("o detector descartado esta registrado com o numero",
          "0 de 282 agentes" in texto)

    print("F9.29 — um executor lento nao segura a rodada inteira parada")
    check("o teto por executor existe como knob", "tetoExecutorMin" in js)
    # O teto so e teto se chegar em quem tem relogio: o script nao tem (o vigia le a hora
    # de ARGS.now). Teto que ficasse so no script nao seria teto de ninguem — por isso o
    # que se cobra aqui e o `tetoMin` DENTRO de todo execPrompt, nao a constante solta.
    check("o teto chega a TODO executor pelo prompt",
          len(re.findall(r"execPrompt\(\{ task: t, tetoMin: tetoExecutorMin \}", js)) == 3)
    check("quem estourou o teto NAO conta como resultado",
          re.search(r"const results = respostas\.filter\(x => !x\.espera\)", js) is not None)
    check("a rodada fecha com quem voltou (o resto do laco usa `results`)",
          "respostas" in js and js.index("const results = respostas") < js.index("reviewBuildPrompt"))
    check("quem esperou volta pro decompositor na volta seguinte",
          "esperaIds" in js and re.search(r"missing: \[\.\.\.new Set\(\[\.\.\.\(review\.missingTasks \|\| \[\]\), \.\.\.esperaIds\]\)\]", js) is not None)
    check("quem esperou sai como falta de TEMPO, com o motivo",
          "passou do teto de ${tetoExecutorMin} min do executor" in js)
    check("o executor recebe a regra por escrito, no texto que ele le",
          "PASSOU DO TETO, PARE E DEVOLVA `espera: true`" in texto)
    check("o campo entra no schema do executor", "**`espera`**" in texto)

    print("F9.28 — o parametro pode chegar como texto, e o motor converte antes de usar")
    check("a conversao esta no SCRIPT, no topo",
          re.search(r"typeof args === 'string' \? JSON\.parse\(args\) : args", js) is not None)
    check("a conversao vem ANTES do primeiro uso do parametro",
          "ARGS =" in js and "ARGS.severityFloor" in js
          and js.index("ARGS =") < js.index("ARGS.severityFloor"))
    check("nenhum uso solto de args. sobrou no script", "args." not in js)
    # As DUAS formas, executadas de verdade: a linha do script roda em Node com o
    # parametro em texto e em objeto, e nos dois casos o campo tem que chegar.
    conv = conversao_do_script(js)
    for forma, entrada in (("texto", '\'{"severityFloor":"P0"}\''),
                           ("objeto", '{ severityFloor: "P0" }')):
        check("com o parametro em %s, o campo chega" % forma,
              roda_em_node(conv, entrada) == "P0")

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK (%d checks)" % TOTAL[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
