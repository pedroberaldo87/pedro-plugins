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
         "paraPorCausaGlobal", "destravaOuPara"]
for peca in PECAS:
    check("peça '%s' está no motor.js" % peca, peca in motor)
    check("peça '%s' segue no esqueleto do SKILL.md" % peca, peca in skill)

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
    check("uma tentativa por corrida — a segunda seria repetir sem mudar o estado (%s)"
          % nome, "destravesUsados >= 1" in fonte)
    check("destravou de verdade ⇒ a causa sai do cache e a corrida segue (%s)" % nome,
          "delete causaCache['@repositorio']" in fonte)

# B · a tabela prompt -> PAPEL do SKILL.md, cobrada no arquivo executável.
PAPEIS = {
    "orquestradorPrompt": "ORQUESTRADOR", "execPrompt": "EXECUTOR",
    "reviewBuildPrompt": "REVISOR", "confirmBuildPrompt": "CONFIRMADOR",
    "auditorPrompt": "AUDITOR", "diagnoseStuckTaskPrompt": "DIAGNOSTICO",
    "desafioCausaPrompt": "DESAFIADOR", "reguaPrompt": "MECANICO",
    "saudePrompt": "MECANICO", "reservaPrompt": "MECANICO",
    "checkpointPrompt": "MECANICO", "docTouchPrompt": "MECANICO",
    "colheitaPrompt": "MECANICO", "tickPlanPrompt": "MARCAR",
    "runSuitePrompt": "SUITE",
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
    salvar, marcar = texto.find("phase: 'Salvar'"), texto.find("phase: 'Marcar'")
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
