#!/usr/bin/env python3
"""O cobrador do motor.js — o arquivo que o disparo do /sprint passa como scriptPath.

Por que existe (2026-08-09): os prompts e schemas do motor só existiam em prosa no
SKILL.md, a casca os traduzia em código a cada disparo, e uma dessas traduções foi
guardada em rascunho e rodou DEPOIS do rename sovai->sprint com o nome velho — sem
nada acusar. Agora o código mora em references/motor.js, e este teste cobra que ele
não divirja das três fontes que o definem:

  A · o esqueleto do SKILL.md (as peças com nome — blocoMax, ledgerCorrida, ...);
  B · a tabela prompt -> PAPEL do SKILL.md (o medidor da autópsia classifica por ela);
  C · os tiers de _shared/r8-tiers.json (a constante T é escrita no arquivo, não lida
      de args — e escrita à mão diverge no primeiro reajuste).

    python3 plugins/project-skills/lib/test_motor_js.py
"""
import json
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
MOTOR = os.path.join(PLUGIN, "skills", "sprint", "references", "motor.js")
SKILL = os.path.join(PLUGIN, "skills", "sprint", "SKILL.md")
TIERS = os.path.join(PLUGIN, "skills", "sprint", "references", "r8-tiers.json")

ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


motor = open(MOTOR, encoding="utf-8").read()
skill = open(SKILL, encoding="utf-8").read()

# O esqueleto ```javascript do SKILL.md é o MESMO laço do motor.js, e o SKILL.md manda
# editar OS DOIS ("quem pega divergência é lib/test_motor_js.py"). Só que não pegava: as
# checagens D e E rodavam sobre o motor.js e mais nada, e o esqueleto ficou para trás —
# medido em 2026-08-09, 15 chamadas de agente sem `label` e nenhum passo de suíte na
# largada. Agora D e E2 rodam sobre os DOIS textos. Ficam de fora E1 (marca da lei) e E3
# (proxy de critério), que moram em corpo de PROMPT: o esqueleto não traz prompt nenhum,
# por desenho, e os dois nunca foram cópia linha a linha um do outro.
_bloco = re.search(r"\n```javascript\n(.*?\n)```\n", skill, re.S)
check("o esqueleto ```javascript existe no SKILL.md", _bloco is not None)
esqueleto = _bloco.group(1) if _bloco else ""
BASE_ESQ = skill[:_bloco.start(1)].count("\n") if _bloco else 0
FONTES = [("motor.js", motor, 0), ("esqueleto do SKILL.md", esqueleto, BASE_ESQ)]

# A · as peças do esqueleto — a MESMA lista da conferência escrita no SKILL.md.
PECAS = ["blocoMax", "naoDespachadas", "idsDoPlano", "congeladas", "esperaChain",
         "saudePrompt", "ledgerCorrida", "impressaoTarefa", "emCirculo",
         "paraPorCausaGlobal", "destravaOuPara", "orfaosDaLargada"]
for peca in PECAS:
    check("peça '%s' está no motor.js" % peca, peca in motor)
    check("peça '%s' segue no esqueleto do SKILL.md" % peca, peca in skill)

# A3 · O DETECTOR DE TRABALHO ÓRFÃO NA LARGADA (F18.1 · R-28). A corrida de 2026-08-13
# entregou 4 tarefas e 3 commits com ZERO passos marcados; a retomada seguinte refaria
# tudo. A rodada 1 pergunta ao disco antes de decompor — e a lista vai para a TELA, nunca
# para o tique.
check("o prompt do detector de órfão existe no motor.js",
      "orfaosPrompt" in motor and "lib/orfaos.py" in motor)
check("o detector roda na rodada 1, ANTES da decomposição",
      motor.find("label: 'orfaos:r1'") > 0
      and motor.find("label: 'orfaos:r1'") < motor.find("orquestradorPrompt({"))
for nome, fonte, _base in FONTES:
    check("a lista de órfãos da largada é impressa (%s)" % nome,
          "orfaosDaLargada" in fonte and "trabalho órfão no disco" in fonte)
check("o detector de órfão está no disco",
      os.path.isfile(os.path.join(PLUGIN, "lib", "orfaos.py")))

# A4 · O ÓRFÃO ENTRA NO MESMO CICLO (F18.2 · R-28). Detectar sem despachar deixaria o
# passo aberto igual; marcar a partir da detecção marcaria no escuro. O caminho é um só:
# tarefa no bloco → revisor por tarefa → suíte → tique com prova.
for nome, fonte, _base in FONTES:
    check("a lista de órfãos chega ao orquestrador (%s)" % nome,
          "orfaos: orfaosDaLargada" in fonte)
check("o orquestrador manda despachar órfão como TAREFA, sem atalho de marcação",
      "TRABALHO ÓRFÃO É TAREFA, NUNCA MARCAÇÃO" in motor
      and "orfaos }) => `PAPEL: ORQUESTRADOR" in motor)
# Substring LITERAL das duas linhas que fazem o caminho, não o nome da variável solta:
# com o nome só, apagar o repasse ao orquestrador deixava a asserção verde.
for nome, fonte, _base in FONTES:
    check("órfão reprovado volta ao orquestrador no `missing` (%s)" % nome,
          "...naoTentadasNaRodada, ...reprovadasNosBlocos," in fonte)
    check("só o que passou vai ao tique — o reprovado não é marcado (%s)" % nome,
          "passos: aprovadas.map(t => ({ taskId: t.task_id," in fonte)
check("o motivo do não-marcado fica no relatório da rodada",
      "reprova do revisor de tarefa ou de bloco" in motor)

# A5 · O TIQUE DO ÓRFÃO COBRA MAIS (F18.3 · R-28). Marcar obra achada no disco com a
# prova de quem estava presente é carimbo sem testemunha: o passo de retomada leva
# `--retomada`, e o programa exige veredito do revisor E sha.
for nome, fonte, _base in FONTES:
    check("o tique do órfão vai marcado como retomada (%s)" % nome,
          "retomada: orfaosDaLargada.includes(t.task_id)" in fonte)
    check("a prova do órfão sai do veredito REAL do revisor, não de frase cravada (%s)" % nome,
          "provaDoRevisor(vereditoDaTarefa.get(t.task_id))" in fonte
          and "vereditoDaTarefa.set(entregues[i].task_id, porTarefa[i])" in fonte
          and "commit ${salvo.sha || '?'}" in fonte)
    check("revisor mudo vira prova sem aprovação, que o plan_state recusa (%s)" % nome,
          "retomada SEM veredito do revisor" in fonte)
check("o marcador recebe a ordem de passar --retomada",
      "--retomada" in motor and "retomada: true" in motor)

# A2 · O DESTRAVADOR (F23.9) — o papel que conserta a porta fechada DURANTE a corrida,
# em vez de a corrida morrer nela. Quatro corridas seguidas morreram na mesma classe de
# causa em 2026-08-15, todas destravadas pelo dono em dois minutos na manhã seguinte.
# Sem estas checagens o papel volta a ser prosa numa fonte e ausência na outra.
for nome, fonte, _base in FONTES:
    check("o destravador existe e é chamado (%s)" % nome,
          "destravadorPrompt" in fonte and "destravaOuPara" in fonte)
    check("a causa de repositório passa pelo destravador antes de parar (%s)" % nome,
          "await destravaOuPara(d, t.id)" in fonte)
    check("quem re-mede a porta é a guarda de saúde, não a palavra do destravador (%s)"
          % nome,
          "saude:pos-destrave" in fonte and "remedida.fechada === false" in fonte)
    # F30.1 — o teto passou a ser por CAUSA DISTINTA, não por corrida. O teto por corrida
    # matou a corrida de 2026-08-20 (573k tokens, ZERO passos) numa causa de dois minutos:
    # causa NOVA é mudança de estado, e parar nela era parar por engano. A MESMA causa
    # repetida continua parando — é esse par que estas duas checagens seguram.
    check("a MESMA causa destravada duas vezes ainda para a corrida (%s)" % nome,
          "causasDestravadas.has(chaveDestrave)" in fonte)
    check("causa DISTINTA não é barrada pelo teto de uma tentativa (%s)" % nome,
          "destravesUsados >= 1" not in fonte and "causasDestravadas.add" in fonte)
    check("existe teto de causas distintas, para o destravador não virar laço (%s)" % nome,
          "causasDestravadas.size >=" in fonte)
    check("destravou de verdade ⇒ a causa sai do cache e a corrida segue (%s)" % nome,
          "delete causaCache['@repositorio']" in fonte)


# A3 · O BLOCKER DE DECISÃO VIRA PENDÊNCIA NO PASSO (F12.5 · R-21). O blocker morria
# no relatório do FIM da corrida: o passo continuava `todo` no arquivo do plano e a
# rodada seguinte soltava executor nele de novo. A gravação é código do laço, então
# vale nas DUAS fontes; o corpo do prompt só existe no motor.js, por desenho.
for nome, fonte, _base in FONTES:
    check("a gravação de pendência existe e é chamada (%s)" % nome,
          "gravaPendencias" in fonte and "await gravaPendencias()" in fonte)
    check("ela grava na MESMA rodada — antes da revisão geral e na parada por causa "
          "global (%s)" % nome, fonte.count("await gravaPendencias()") >= 3)
    check("só blocker com passo vira pendência (%s)" % nome,
          "blockers.slice(pendGravadas).filter(b => b.taskId)" in fonte)
    check("o cursor impede regravar o que já desceu (%s)" % nome,
          "pendGravadas = blockers.length" in fonte)
# A3b · A VARREDURA DA LARGADA (F12.6 · R-21). A pendência nascida na decomposição
# desta volta tem que descer para o plano ANTES do disparo da onda — não depois — e a
# lista fica no ledger da corrida, que é o que as rodadas seguintes leem.
for nome, fonte, _base in FONTES:
    varredura = fonte.find("A VARREDURA DA LARGADA")
    check("a varredura da largada existe (%s)" % nome, varredura > 0)
    check("ela varre a pendência nova da rodada (%s)" % nome,
          "blockers.slice(pendGravadas).filter(x => x.taskId)" in fonte)
    check("ela lista a pendência nova no ledger da corrida (%s)" % nome,
          "tipo: 'pendencia'" in fonte and "pendência nova na largada" in fonte)
    check("ela roda ANTES do disparo da onda (%s)" % nome,
          0 < varredura < fonte.find("for (const bloco of blocos)")
          and varredura < fonte.find("RESERVA DE ARQUIVOS ENTRE MOTORES"))
    check("a varredura chama a mesma gravação, não uma segunda via (%s)" % nome,
          fonte.count("await gravaPendencias()") >= 4)

# A3c · A PRODUÇÃO DA RODADA NO LEDGER (F16.1 · R-26). O ledger guardava só veredito e
# marcação — quem lia o relatório não sabia o que a rodada PRODUZIU. Agora toda rodada
# grava a medição do que aconteceu, com os quatro campos, no caminho por onde toda saída
# passa (a mesma linha que fecha a conta do vigia).
for nome, fonte, _base in FONTES:
    check("a rodada grava a produção no ledger da corrida (%s)" % nome,
          "tipo: 'producao'" in fonte)
    for campo in ("passosMarcados", "lotesVerdes", "arquivosTocados", "bloqueiosNovos"):
        check("o campo '%s' está na medição da rodada (%s)" % (campo, nome),
              campo + ":" in fonte)
    check("é medição do que aconteceu, não palavra de agente (%s)" % nome,
          "marcadosDaOnda.filter(m => m.ok)" in fonte
          and "blockers.length - bloqueiosAntes" in fonte
          and "[...tocadosDaOnda]" in fonte)
    check("os bloqueios novos são contados a partir da largada da rodada (%s)" % nome,
          "const bloqueiosAntes = blockers.length" in fonte)
    check("ela é gravada no caminho por onde toda saída da rodada passa (%s)" % nome,
          fonte.find("tipo: 'producao'") > fonte.find("rodadasMudas = blocosVerdes.length"))

# A3d · O JUIZ DE CONTEXTO LIMPO PARA A CORRIDA EM FALSO (F16.2 · R-26). Quem está
# dentro do laço não julga o próprio andamento: o motor manda SÓ a medição das últimas
# rodadas (a de F16.1) para um juiz separado, e o veredito 'em falso' desliga a corrida —
# sem teto de número de rodadas, que continua sendo `maxRounds || Infinity`.
for nome, fonte, _base in FONTES:
    check("o motor consulta o juiz de produtividade (%s)" % nome,
          "produtividadePrompt({ medicoes })" in fonte and "schema: PRODUTIVIDADE" in fonte)
    check("o juiz recebe SÓ a medição das últimas rodadas (%s)" % nome,
          "ledgerCorrida.filter(x => x.tipo === 'producao').slice(-3)" in fonte)
    check("o veredito 'em falso' para a corrida (%s)" % nome,
          "parecer?.veredito === 'em falso'" in fonte
          and "desligadoPor = 'em-falso'" in fonte
          and re.search(r"desligadoPor = 'em-falso'.*?\n\s*blockers\.push\(.*?\n.*?\n\s*break", fonte, re.S) is not None)
    check("a parada é do veredito, não de um teto de rodadas (%s)" % nome,
          "medicoes.length >= 2" in fonte and "rodadasMudasMax" not in fonte.split("F16.2")[1].split("holdsBuild")[0])

check("o schema do juiz aceita só produtivo ou em falso",
      "const PRODUTIVIDADE" in motor
      and "enum:['produtivo','em falso']" in motor
      and "required:['veredito','motivo','anchor']" in motor)
_corpo = motor.split("const produtividadePrompt", 1)[-1].split("\nconst ", 1)[0]
check("o prompt do juiz não recebe conclusão de quem roda a corrida",
      "MEDIÇÃO DAS ÚLTIMAS RODADAS" in _corpo
      and "${J(medicoes)}" in _corpo
      and not any(x in _corpo for x in ("J(results", "J(review", "ledger", "resumo do executor")))
check("a corrida sem teto de rodadas continua sendo o padrão",
      "const maxRounds = ARGS.maxRounds || Infinity" in motor)

check("o prompt chama o subcomando `pendencia` do plan_state.py",
      "pendencia ${planIdDe(planPath)} <taskId>" in motor)
# o programa que a gravação chama tem que existir com esse nome — prompt apontando
# para subcomando inexistente falharia calado, uma recusa por passo, corrida afora.
_plan_state = open(os.path.join(PLUGIN, "lib", "plan_state.py"), encoding="utf-8").read()
check("plan_state.py tem o subcomando `pendencia`",
      'sub.add_parser("pendencia"' in _plan_state and "def cmd_pendencia" in _plan_state)

# B · a tabela prompt -> PAPEL do SKILL.md, cobrada no arquivo executável.
PAPEIS = {
    "orquestradorPrompt": "ORQUESTRADOR", "execPrompt": "EXECUTOR",
    "reviewBuildPrompt": "REVISOR", "confirmBuildPrompt": "CONFIRMADOR",
    "auditorPrompt": "AUDITOR", "diagnoseStuckTaskPrompt": "DIAGNOSTICO",
    "desafioCausaPrompt": "DESAFIADOR", "reguaPrompt": "MECANICO",
    "saudePrompt": "MECANICO", "reservaPrompt": "MECANICO",
    "checkpointPrompt": "MECANICO", "docTouchPrompt": "MECANICO",
    "colheitaPrompt": "MECANICO", "tickPlanPrompt": "MARCAR",
    "runSuitePrompt": "SUITE", "pendenciaPrompt": "MARCAR",
    "produtividadePrompt": "PRODUTIVIDADE",
}
for nome, papel in PAPEIS.items():
    m = re.search(r"const %s = [^`]*`PAPEL: (\w+)" % nome, motor)
    check("%s abre com PAPEL: %s" % (nome, papel),
          m is not None and m.group(1) == papel,
          "achado: %s" % (m.group(1) if m else "prompt sem a declaração"))

# os revisores de tarefa e de bloco também são REVISOR (não estão na tabela por nome)
for nome in ("revisorTarefaPrompt", "revisorBlocoPrompt"):
    m = re.search(r"const %s = [^`]*`PAPEL: (\w+)" % nome, motor)
    check("%s abre com PAPEL: REVISOR" % nome, m is not None and m.group(1) == "REVISOR")

# C · a constante T contra os tiers vendorados — escrita à mão diverge calada.
tiers = json.load(open(TIERS, encoding="utf-8"))["tiers"]
m = re.search(r"const T = \{(.*?)\}\s*\n", motor, re.S)
check("a constante T existe no motor.js", m is not None)
if m:
    for knob in ("decompose", "coordinate", "executor", "mechanical", "diagnose", "finalize"):
        esperado = tiers[knob]["effort"]
        got = re.search(r"%s: \{effort:'(\w+)'\}" % knob, m.group(0))
        check("T.%s = %s (igual ao r8-tiers.json)" % (knob, esperado),
              got is not None and got.group(1) == esperado,
              "no arquivo: %s" % (got.group(1) if got else "ausente"))

# o nome do motor e a ausência do nome morto — o defeito que pariu este arquivo.
check("meta.name é sprint-build-engine", "name: 'sprint-build-engine'" in motor)
check("nenhum 'sovai' sobrevive no motor.js", "sovai" not in motor.lower())

# o commit da onda sai com o prefixo novo (o suite_congela compara literal).
check("o checkpoint commita como 'sprint: onda'", "sprint: onda" in motor)

# O commit vem ANTES da marcação e segura o tick (decisão do dono, 2026-08-13):
# o gate que recusava o commit era engolido pelo `|| true` DEPOIS de o passo já
# estar done no plano — plano dizendo feito, git sem o código (achado da revisão
# pré-corrida). O salvamento agora devolve CHECKPOINT_RESULT e o script só marca
# com committed: true.
check("CHECKPOINT_RESULT existe com committed obrigatório",
      "CHECKPOINT_RESULT" in motor and "required:['committed']" in motor)
for nome, texto in (("motor.js", motor), ("esqueleto do SKILL.md", skill)):
    # A âncora é o RÓTULO da chamada, não a fase: `phase: 'Marcar'` deixou de ser
    # exclusivo do tique quando a gravação de pendência (F12.5) passou a usar a mesma
    # fase, e ela é DEFINIDA antes do laço de blocos — a ordem media as duas coisas
    # erradas. O que esta checagem cobra continua sendo o par commit→tique do bloco.
    salvar, marcar = texto.find("label: `commit r"), texto.find("label: `marcar r")
    check("o commit roda antes da marcação (%s)" % nome, 0 <= salvar < marcar,
          "Salvar@%d Marcar@%d" % (salvar, marcar))
    check("o salvamento devolve o veredito no schema (%s)" % nome,
          "schema: CHECKPOINT_RESULT" in texto)
    check("commit recusado segura o tick do bloco (%s)" % nome,
          "salvo.committed !== true" in texto and "foi RECUSADO" in texto)
    # O canal do commit aguenta o gate: sem timeout explícito a chamada de Bash
    # morria aos 2min default enquanto o gate re-media a árvore (2026-08-14:
    # 3h20 de corrida, zero commits). Recusa é resultado; canal morto não é.
    check("a chamada do commit pede timeout de 600000 (%s)" % nome,
          "timeout: 600000" in texto)
check("a prova do tique carrega o sha do commit", "commit ${salvo.sha" in motor)

# nada de caminho cravado de máquina — o repo do dono não é este marketplace.
check("sem caminho absoluto de máquina", "/Users/" not in motor)

# E · As três travas da autópsia de 2026-08-09 (corrida wf_cd3fe221) — cada uma
# nasceu de um defeito medido, e regra só em prosa foi como os três entraram.
#
# E1 · A marca da lei é COMANDO literal, nunca receita interpretável: a receita em
# prosa ("cksum do corpo") rendeu QUATRO marcas do mesmo disco na mesma corrida e
# dois avisos falsos de "a lei mudou".
check("a marca da lei sai de comando literal (leiMarcaInstr + cksum)",
      "leiMarcaInstr" in motor and "| cksum" in motor
      and "corpo (sem frontmatter) dos arquivos de lei" not in motor)
# E2 · A suíte roda na largada e o vermelho pré-existente fecha a porta — três
# rodadas morreram em cima de um teste que já estava quebrado antes da missão.
for fonte, texto, _base in FONTES:
    check("a suíte roda na largada e vermelho pré-existente é porta fechada (%s)" % fonte,
          "suite:largada" in texto and "vermelha antes da missão" in texto)
# E2b · A porta fechada não oferece saída que o programa não tem: o motor não lê
# flag de isenção nem lista de teste ignorado, então mandar o dono "isentar" é
# despachá-lo atrás de um botão inexistente. A mensagem só nomeia o que existe.
for fonte, texto, _base in FONTES:
    check("a porta fechada não oferece isenção inexistente (%s)" % fonte,
          "isente" not in texto and "isentar" not in texto)
# E2c · A suíte de BLOCO diz qual bloco. O esqueleto chamava `runSuitePrompt` sem
# `bloco`, e assinatura divergente é exatamente o que o dono lê como fonte do laço.
for fonte, texto, _base in FONTES:
    check("a suíte de bloco passa `bloco: b` (%s)" % fonte,
          "round: r, bloco: b, suiteCmd" in texto)
# E2d · O COMANDO DECLARADO E O TETO CHEGAM AOS PAPÉIS MECÂNICOS (2026-08-13).
# O planText nunca alcança saúde nem suíte, por construção: um agente de saúde rodou o
# comando proibido da casa como primeira ação — a instrução não tinha como chegar nele —
# e ficou 58 min num log congelado, invisível pro vigia, que só conta rodadas FECHADAS.
for fonte, texto, _base in FONTES:
    check("a saúde recebe suiteCmd e teto (%s)" % fonte,
          "saudePrompt({ repoRoot: ARGS.repoRoot, round: r, suiteCmd, tetoMin: tetoMecanicoMin })" in texto)
    check("a suíte da largada recebe suiteCmd e teto (%s)" % fonte,
          "round: r, bloco: 0, suiteCmd, tetoMin: tetoMecanicoMin })" in texto)
    check("tetoMecanicoMin existe com default (%s)" % fonte,
          "ARGS.tetoMecanicoMin || 10" in texto and "ARGS.suiteCmd || null" in texto)
# O corpo dos prompts só existe no motor.js (o esqueleto não traz prompt nenhum):
check("saudePrompt proíbe improvisar comando e manda ler a declaração do projeto",
      "NUNCA improvise um comando de suíte" in motor)
check("os papéis mecânicos têm teto de relógio com parada escrita",
      motor.count("PROIBIDO laço de espera") >= 2
      and "teto de ${tetoMin} min estourado" in motor)
check("runSuitePrompt roda o comando declarado literal quando ele existe",
      "o COMANDO DECLARADO DA CASA, literal" in motor)
# E3 · O `pronto` é literal: executor que não alcança o critério devolve
# `impossivel`, nunca um proxy — um passo fechou com a medição original jamais
# feita porque o executor documentou a troca e a auto-concedeu.
check("proxy de critério é proibido no executor e reprovado no revisor",
      "PROXY É PROIBIDO" in motor and "critério REESCRITO" in motor)

# E5 · A TRANCA HERDA (F13.6 · R-22). HTML nunca tem frontmatter, e sem herança o
# executor edita protótipo aprovado sem nada acusar: o decompositor tem que tratar
# arquivo citado por doc sob tranca como protegido. O corpo do prompt só existe no
# motor.js, por desenho — o esqueleto não traz prompt nenhum.
check("a tranca herda: arquivo citado por doc sob tranca é protegido",
      "A TRANCA HERDA" in motor
      and "arquivo citado por doc sob tranca é protegido" in motor
      and "herda a tranca do doc que o cita" in motor)

# E6 · FONTE DE LEITURA ≠ ARQUIVO DE ESCRITA (F13.11 · R-22). O protótipo aprovado é
# insumo direto da implementação: a decomposição o entrega em `fontes`, separado de
# `files`, e o executor pode copiar markup dele mas nunca editá-lo. Sem a distinção,
# ou o protótipo entra em `files` (e vira escrita), ou some do prompt (e o executor
# reinventa a tela). Schema sem descrição no prompt é convite a valor inventado.
check("o schema da decomposição tem o campo `fontes` separado de `files`",
      "fontes: {type:'array', items:{type:'string'}}" in motor)
check("o decompositor separa a fonte de leitura dos arquivos de escrita",
      "FONTE DE LEITURA, SEPARADA DA ESCRITA (R-22)" in motor
      and "entra em \\`fontes\\`, NUNCA em \\`files\\`" in motor)
check("o executor copia markup da fonte mas não a edita",
      "`fontes` É LEITURA, NUNCA ESCRITA (R-22)" in motor.replace("\\`", "`")
      and "NÃO edite a fonte" in motor
      and "fonte não entra em \\`files_touched\\`" in motor)

# R-17 · O JUIZ NÃO RECEBE A CONCLUSÃO DE QUEM PEDE O JULGAMENTO (Art. 4). A linha
# vale nos DOIS motores — cobrar só o do /sprint deixa o viés voltar pelo /qa-loop.
SEM_HIPOTESE = "VOCÊ NÃO RECEBE A HIPÓTESE DE QUEM PEDIU O JULGAMENTO"
motor_qa = open(os.path.join(PLUGIN, "skills", "qa-loop", "references", "motor.js"),
                encoding="utf-8").read()
for _nome, _texto in [("motor.js do sprint", motor), ("motor.js do qa-loop", motor_qa)]:
    check("a proibição de receber a hipótese de quem pediu está declarada (%s)" % _nome,
          SEM_HIPOTESE in _texto and "${SEM_HIPOTESE}" in _texto)

# E4 · TRABALHO VIVO É MEDIDO, NÃO JULGADO (F17.4). A linha antiga pedia ao agente
# `true se há processo de build/servidor ainda rodando` — julgamento por foto, que não
# separa quem trabalha de quem está pendurado há uma hora, e que desarmava o vigia. A
# medida agora sai de duas amostras de CPU ACUMULADA, e a falta de medida NÃO vale por
# sinal de vida. As duas frases vivem nos DOIS arquivos (o prompt no motor.js, o
# contrato do schema no SKILL.md) — divergir aqui é o defeito voltando por um lado só.
for _nome, _texto in [("motor.js", motor), ("SKILL.md", skill)]:
    check("trabalho vivo sai do medidor de duas amostras (%s)" % _nome,
          "vivo-ou-dormindo.sh" in _texto
          and "CPU ACUMULADO" in _texto and "DUAS AMOSTRAS SEPARADAS" in _texto)
    check("medidor que não mediu não vale por sinal de vida (%s)" % _nome,
          "MEDIDOR QUE NÃO MEDIU" in _texto and "nao-medido" in _texto)
check("a linha de julgamento por foto saiu do prompt da suíte",
      "true se há processo de build/servidor ainda rodando" not in motor)

# E4.1 · O MEDIDOR LÊ NÚMERO EM LOCALE NEUTRO. O tempo do `ps` vem com ponto decimal e
# o `awk` o interpreta pelo locale: em pt_BR `"33.94"` é lido como `33`, e a fração é a
# única coisa que anda entre duas amostras a 3s (`0:00.43` → `0:00.48`). Sem isto o
# delta dá zero e o medidor responde "dormindo" com o processo trabalhando — o vigia
# desarmado justamente na máquina de quem usa. Vale nas DUAS cópias (fonte e vendorada).
import os as _os
# lib/ → project-skills/ → plugins/ → raiz: são QUATRO níveis. Parar em três aponta
# para `plugins/`, os dois arquivos não são encontrados, e a checagem reprova por
# caminho errado em vez de por defeito — falso vermelho é tão ruim quanto falso verde.
_raiz = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                       "..", "..", ".."))
for _rel in ("_shared/vivo-ou-dormindo.sh",
             "plugins/project-skills/lib/vivo-ou-dormindo.sh"):
    _cam = _os.path.join(_raiz, _rel)
    check("o medidor existe para ser medido (%s)" % _rel, _os.path.exists(_cam), _cam)
    _src = open(_cam, encoding="utf-8").read() if _os.path.exists(_cam) else ""
    check("o medidor fixa locale neutro para ler número (%s)" % _rel,
          "export LC_ALL=C" in _src)

# F · A BARRA DE STATUS ANDA COM A MISSÃO, E APAGA QUANDO ELA ACABA.
#
# Dois defeitos que o dono viu na tela em 2026-08-09. (1) O sinal ficava aceso
# depois do fim: o `rm` era passo da CASCA, que só roda no caminho feliz — motor
# que para por teto, vigia, disjuntor ou onda estéril deixava a barra mentindo, e
# havia CINCO sinais órfãos vivos, o mais velho de 75 horas. (2) A barra andava só
# por onda: numa onda de três blocos ela ficava quinze minutos no mesmo texto.
# O DESPACHO é código do laço, então vale para as DUAS fontes; o corpo do prompt
# (o `andamento.py`, a barra por bloco) só existe no motor.js, por desenho — o
# esqueleto não traz prompt nenhum.
for fonte, texto, _base in FONTES:
    check("o motor apaga o próprio sinal ao sair, em todo caminho que é dele (%s, ver F3)" % fonte,
          "encerraPrompt({" in texto and "encerra:barra" in texto)
check("a barra anda por BLOCO, não só por onda",
      "--bloco ${bloco}" in motor and "--etapa" in motor)

# F2 · O ENCERRAMENTO SOLTA O PAR INTEIRO: sinal da barra E reserva de arquivos.
# `andamento.py encerra` não toca `~/.claude/andamento/reservas/<sid>__<motor>.files`
# (outro diretório, outro prefixo), e `expira_sinais` também não. Nos caminhos sem
# casca (teto, vigia, disjuntor, onda estéril, porta fechada) a reserva ficava de pé
# até o TTL de 12h, barrando outro motor da mesma sessão nos mesmos arquivos.
_corpo_encerra = motor.split("const encerraPrompt")[1].split("const colheitaPrompt")[0]
# A chamada do sinal tem que estar DENTRO do corpo do encerramento: `andamento.py`
# aparece em cinco outros pontos do motor.js, então procurar no arquivo inteiro
# deixava a checagem verde mesmo com a linha do encerramento apagada.
check("o encerramento chama o andamento.py",
      "andamento.py" in _corpo_encerra and "encerra ${sessionId}" in _corpo_encerra,
      "encerraPrompt não chama `andamento.py encerra <sid>` — o sinal fica aceso")
check("o encerramento libera também a reserva de arquivos",
      "reserva-de-arquivos.sh" in _corpo_encerra and "liberar" in _corpo_encerra
      and "${motorId}" in _corpo_encerra,
      "encerraPrompt só apaga o sinal — a reserva fica de pé até o TTL")
# F3 · MOTOR RECUSADO PELA RESERVA NÃO APAGA O ESTADO DA SESSÃO.
# `andamento.py encerra <sid>` apaga por SESSÃO (ativo-/onda-/placar-/sinal-/…), não
# por motor. O motor B que a reserva recusou nunca reservou nada e nunca acendeu nada:
# se ele encerrasse ao sair, apagaria o sinal do motor A, que continua trabalhando, e a
# barra de A sumiria da tela (pretooluse-motor-arma.sh desarma sem o sinal).
for fonte, texto, _base in FONTES:
    _pre_encerra = texto.split("await agent(encerraPrompt(")[0][-500:]
    check("motor recusado pela reserva sai sem encerrar o estado da sessão (%s)" % fonte,
          "desligadoPor !== 'reserva'" in _pre_encerra,
          "o dispatch de encerra:barra é incondicional — apaga a barra do outro motor da sessão")

    check("a chamada do encerramento passa o motorId (%s)" % fonte,
          "encerraPrompt({ sessionId: ARGS.sessionId" in texto
          and "motorId: ARGS.motorId" in texto.split("encerraPrompt({")[-1].split("})")[0])

# D · TODO agente sai com rótulo próprio na tela de andamento.
#
# Sem `label`, a tela de progresso nomeia o agente pelo COMEÇO do prompt — e como todo
# prompt do motor abre com `PAPEL: X` (a regra da autópsia), sete papéis apareciam como
# "PAPEL: DIAGNOSTICO Repositório: /Users/…" cortado, indistinguíveis entre si. O dono
# perdia a governança justamente onde ela importa: qual tarefa está em diagnóstico, em
# que volta do desafio, qual rodada está decompondo.
#
# A varredura ancora na CHAMADA (`agent(` / `julga(`) e exige `label:` dentro dos
# parênteses dela. A âncora velha era a linha com `phase: '` — só aspa simples, e só o
# par de linhas em volta: derrubar o rótulo do executor escrevendo `phase: "Executar"`
# saía verde, e chamada sem `phase:` nenhum era invisível.
def _chamadas_sem_label(texto):
    achados = []
    for m in re.finditer(r"\b(?:agent|julga)\(", texto):
        ini_linha = texto.rfind("\n", 0, m.start()) + 1
        if texto[ini_linha:m.start()].lstrip().startswith(("//", "*")):
            continue  # menção em comentário não é chamada
        i, prof = m.end(), 1
        while i < len(texto) and prof:
            prof += (texto[i] == "(") - (texto[i] == ")")
            i += 1
        if "label:" not in texto[m.start():i]:
            achados.append("%d: %s" % (texto[:m.start()].count("\n") + 1,
                                       texto[ini_linha:m.start() + 60].strip()[:70]))
    return achados


# o arnês da própria varredura — os dois disfarces que passavam pela âncora velha.
_ARNES = [
    ("chamada em aspa dupla sem label",
     'const x = await agent(p({ a: 1 }),\n  { model: m, phase: "Executar", schema: S })\n', 1),
    ("chamada com `phase:` vindo de variável, sem label",
     "const x = await agent(p({ a: 1 }),\n  { model: m, phase: fase, schema: S })\n", 1),
    ("chamada com label continua verde",
     "const x = await julga(p({ a: 1 }),\n  { model: m, phase: fase, label: `x:1`, schema: S })\n", 0),
]
for _nome, _trecho, _esperado in _ARNES:
    _got = _chamadas_sem_label(_trecho)
    check("o arnês da varredura pega: %s" % _nome, len(_got) == _esperado,
          "achados: %s" % _got)

for fonte, texto, base in FONTES:
    sem_rotulo = ["%d: %s" % (base + int(a.split(":", 1)[0]), a.split(":", 1)[1].strip())
                  for a in _chamadas_sem_label(texto)]
    check("toda chamada de agente tem label próprio (%s)" % fonte, not sem_rotulo,
          "sem rótulo → %s" % " | ".join(sem_rotulo))

# F30.4 — o gap do revisor DE BLOCO tem que passar pelo floor de severidade, igual ao do
# revisor por tarefa e ao veredito final. A omissão custou uma corrida inteira em
# 2026-08-20: um gap P3 cujo texto dizia "Não bloqueia o commit deste bloco" bloqueou o
# commit do bloco, e 13 arquivos com a suíte verde ficaram fora do histórico. A checagem
# olha o TRECHO do revisor de bloco, não o arquivo todo: o `sevRank(...) >= floor` já
# aparece em outros dois lugares, e procurar no arquivo inteiro passaria verde sem o fix.
_trecho_bloco = motor.split("const reprovadasNoBloco")[0].split("2 · REVISÃO DO BLOCO")[-1] \
    + "const reprovadasNoBloco" + motor.split("const reprovadasNoBloco")[1][:600]
check("o gap do revisor de bloco passa pelo floor de severidade (motor.js)",
      "sevRank(g.severity) >= floor" in _trecho_bloco
      and ".filter(segura)" in _trecho_bloco,
      "gap P3 do revisor de bloco não pode bloquear o commit do bloco")
check("o filtro do revisor de bloco segura spec e rastreio em qualquer severidade (motor.js)",
      "g.kind === 'spec'" in _trecho_bloco and "g.kind === 'rastreio'" in _trecho_bloco)
check("o esqueleto do SKILL.md carrega o mesmo filtro",
      ".filter(segura)" in skill and "const segura = g =>" in skill)

# sintaxe: o arquivo tem que ser JavaScript válido (quando node existe na máquina).
if shutil.which("node"):
    r = subprocess.run(["node", "--check", MOTOR], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    check("node --check passa", r.returncode == 0, r.stderr.strip()[:120])
else:
    print("  skip node --check (node ausente)")

print()
if falhas:
    print("FALHOU: %d" % falhas)
    sys.exit(1)
print("test_motor_js: %d checagens verdes" % ok)


# F30.2 e F30.3 — as duas curas de 2026-08-20, e elas moram em corpo de PROMPT. Pela
# mesma razão de E1 e E3, rodam sobre o motor.js e mais nada: o esqueleto do SKILL.md
# não traz prompt, por desenho. A prosa que as descreve no SKILL.md é cobrada logo
# abaixo, contra o texto da skill, que é onde ela vive.
check("o papel da suíte confere a prova gravada antes de rodar (motor.js)",
      "green_cache_check" in motor)
check("a conferência da prova é fail-open — ausente ou velha, roda normalmente (motor.js)",
      "fail-open" in motor and "green_cache_check" in motor)
check("existe rodapé com teto de turnos para papel mecânico (motor.js)",
      "RODAPE_MECANICO" in motor and "no máximo 2 turnos" in motor)
check("o rodapé mecânico exige a raiz do projeto em todo comando (motor.js)",
      "RAIZ OBRIGATÓRIA" in motor)
check("os papéis mecânicos carregam o rodapé — todos, não um (motor.js)",
      motor.count("${RODAPE_MECANICO(") >= 6)
check("o SKILL.md descreve o rodapé mecânico e a prova reaproveitada",
      "RODAPE_MECANICO" in skill and "green_cache_check" in skill)
