#!/usr/bin/env python3
"""O cobrador do motor.js do /qa-loop — irmão do test_motor_js.py (que cobra o do /sprint).

POR QUE EXISTE (2026-08-10). O motor do `/sprint` virou arquivo do plugin em
2026-08-09; o deste continuou sendo MONTADO PELA CASCA a cada disparo. A
assimetria cobrou na mesma sessão em que foi notada: o passo que apaga o sinal da
barra virou CÓDIGO no sprint (`encerra:barra`) e ficou em PROSA aqui — "ao
entregar o relatório, encerre". Prosa não pega. O sinal do qa-loop ficou aceso
**9h26 depois do fim**, com a barra anunciando missão de pé, e quem viu foi o
dono, não um cobrador.

O que este arquivo cobra:

  A · o motor é ARQUIVO e é JavaScript válido (a casca não o redigita);
  B · a barra ANDA — cada etapa da rodada se registra;
  C · a barra APAGA — o encerramento é o último ato, antes do `return`, e por
      isso alcança todo caminho de saída (rodada limpa, teto, churn, agente mudo);
  D · toda chamada de agente leva `label` próprio (a mesma régua do irmão);
  E · nada de caminho absoluto de máquina.

    python3 plugins/project-skills/lib/test_qa_loop_motor.py
"""
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
MOTOR = os.path.join(PLUGIN, "skills", "qa-loop", "references", "motor.js")
SKILL = os.path.join(PLUGIN, "skills", "qa-loop", "SKILL.md")

ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


# A · o motor existe como arquivo do plugin
check("o motor do qa-loop é ARQUIVO do plugin", os.path.isfile(MOTOR),
      "esperado em %s" % MOTOR)
if not os.path.isfile(MOTOR):
    print("\nFALHOU: %d" % falhas)
    sys.exit(1)

motor = open(MOTOR, encoding="utf-8").read()
skill = open(SKILL, encoding="utf-8").read()

check("meta.name é qa-loop-engine", "name: 'qa-loop-engine'" in motor)

# B · a barra anda: cada etapa da rodada se registra, e o comando é o do módulo
# de andamento (não um `rm` à mão, que deixaria o resto do estado para trás).
check("existe o papel que faz a barra ANDAR", "andaPrompt" in motor and "const anda =" in motor)
etapas = set(re.findall(r"await anda\(r, [`']([a-zç ]+)", motor))
check("as quatro etapas da rodada se registram",
      {"revisando", "planejando", "confirmando"} <= etapas and
      any(e.startswith("consertando") for e in re.findall(r"await anda\(r, [`']([^`'$]+)", motor)),
      "achadas: %s" % sorted(etapas))
check("o registro usa o módulo de andamento, não um comando à mão",
      "lib/andamento.py" in motor and '" onda ' in motor)

# C · a barra apaga, e o encerramento é o ÚLTIMO ato — antes do `return`.
check("existe o papel que APAGA o sinal", "encerraPrompt" in motor and "encerra:barra" in motor)
check("o encerramento chama `andamento.py encerra`", '" encerra ' in motor)
pos_encerra = motor.find("label: 'encerra:barra'")
pos_return = motor.find("\nreturn {")
check("o encerramento vem ANTES do return (alcança todo caminho de saída)",
      0 < pos_encerra < pos_return,
      "encerra=%d return=%d" % (pos_encerra, pos_return))
# O teste que morde: o encerramento não pode estar dentro do `if` da rodada limpa,
# senão teto e churn saem sem apagar — que é exatamente o defeito que o originou.
trecho = motor[max(0, pos_encerra - 900):pos_encerra]
check("o encerramento NÃO está preso ao caminho da rodada limpa",
      "cleanRound ?" in trecho or "cleanRound?" in trecho,
      "o motivo tem que ser derivado, não o passo condicionado")

# D · todo agente sai com rótulo próprio (sem ele a tela nomeia pelo prompt).
linhas = motor.splitlines()
sem_rotulo = [
    "%d: %s" % (i + 1, linha.strip()[:70])
    for i, linha in enumerate(linhas)
    if "phase: '" in linha
    and "label:" not in linha
    and "label:" not in (linhas[i + 1] if i + 1 < len(linhas) else "")
]
check("toda chamada de agente tem label próprio", not sem_rotulo,
      "sem rótulo → %s" % " | ".join(sem_rotulo))

# E · nada de caminho de máquina, e o resolvedor entra por args.
check("sem caminho absoluto de máquina", "/Users/" not in motor)
check("o resolvedor de plugin chega por args (roda fora deste repo)",
      "ARGS.resolvePlugin" in motor)

# F · a SKILL manda usar o ARQUIVO, não redigitar o script.
check("a skill aponta o motor por scriptPath",
      "references/motor.js" in skill and "scriptPath" in skill)

# G · O MOTOR RODA FORA DESTA CASA (2026-08-23) ─────────────────────────────
# As checagens A-F nasceram do incidente da barra (2026-08-10) e enumeram o que
# já tinha acontecido; portabilidade não estava na lista, e por isso o defeito
# nasceu invisível. Ele custou: stack e regras do marketplace iam CRAVADAS ao
# revisor de qualquer projeto, e o `find test_*.py` do executor, num projeto
# TypeScript, achava ZERO teste do módulo alterado — suíte vazia devolve "nenhum
# teste falhou", `suiteRegressed` nasce false, e o gate de regressão por conserto
# fica cego parecendo verde. Medido: 5 sessões pós-arquivo em projetos JS/TS, 44
# consertos, 0 regressões detectadas. O /sprint já resolvia com `suiteCmd` desde
# 2026-08-13. Estas quatro cobram que não volte.
check("a stack do projeto entra por args (não cravada no prompt)",
      "ARGS.stack" in motor and "STACK_PADRAO" in motor)
check("as regras da casa entram por args (não cravadas no prompt)",
      "ARGS.regrasDaCasa" in motor and "REGRAS_PADRAO" in motor)
check("o comando da suíte entra por args, como no motor irmão do /sprint",
      "ARGS.suiteCmd" in motor)
check("sem declaração, o executor confere se o `find` cobre o que tocou",
      "suiteCmd" in motor and "vier vazia" in motor)
check("a casca lê o comando da suíte do projeto e o passa ao motor",
      "suiteCmd" in skill)

# H · O FINDING REJEITADO PRECISA SAIR COM `id` (2026-08-23) ────────────────
# `rejeitados` é um Set feito de `f.id` dos itens de `rejected`. Com o schema
# aceitando `{motivo:'x'}`, o Set nasce `{undefined}` e NENHUM achado derrubado
# pelo árbitro é descontado de `emAberto`: o relatório fecha dizendo que sobrou
# de pé exatamente o que o juiz já tinha julgado improcedente.
check("o item de `rejected` exige id e motivo no schema PLAN",
      "rejected:{type:'array', items:{type:'object', required:['id','motivo']" in motor)
check("o planejador é mandado devolver o id junto do motivo",
      re.search(r"rejeitado vai em .+rejected.+ com o .+id.+ dele e o motivo", motor) is not None)

# K · O BLOCO DOCUMENTADO NÃO PODE CONTRADIZER O MOTOR (2026-08-23) ─────────
# A própria SKILL declara "quem muda comportamento edita os DOIS", e o Artigo 14
# entrou só no motor: o bloco `javascript` da skill continuava com teto 12 por
# default, com o comentário que ARGUMENTA a favor dele, e com um `return` sem
# `sucesso` — quem lê a doc para decidir comportamento lê o contrário do que roda.
# Não é comparador literal doc↔motor (o bloco é abreviado de propósito): são os
# pontos do Artigo 14, nomeados um a um.
_blocos = re.findall(r"```javascript\n(.*?)```", skill, re.S)
doc = next((b for b in _blocos if "qa-loop-engine" in b), "")
check("o bloco documentado do motor existe na SKILL", bool(doc))
check("o bloco documentado não tem teto de rodadas por default",
      "args.maxRounds || Infinity" in doc and "maxRounds || 12" not in doc)
check("o bloco documentado não argumenta a favor do teto default",
      "Teto de rodadas: default DENTRO do motor" not in doc
      and "SEM TETO POR DEFAULT" in doc)
for campo in ("sucesso:", "severityFloor:", "emAberto,", "abaixoDoPiso,", "vereditoHumano:"):
    check("o `return` documentado devolve %s" % campo.rstrip(":,"), campo in doc)
check("o `stopReason` documentado traz os desfechos novos",
      "teatro-de-duvida" in doc and "agente-mudo" in doc)
# Citar o desfecho no `stopReason` não prova que ele ACONTECE: os dois eram código
# morto no bloco documentado (declarados, lidos no `while` e no relatório, nunca
# atribuídos). Aqui se cobra o ponto em que cada um é LIGADO.
check("o bloco documentado LIGA o teatro-de-dúvida (contador de rodada sem conserto)",
      "rodadasSemConserto = corrections.length === 0" in doc
      and "teatroDeDuvida = true" in doc)
check("o bloco documentado LIGA o agente-mudo (lê a `nota` da última rodada)",
      "rounds[rounds.length - 1].nota" in doc and "nota: 'revisor não respondeu'" in doc)

# I · O LAÇO TEM SAÍDA QUANDO NINGUÉM CONSERTA NADA (2026-08-23) ───────────
# `teatro-de-duvida` estava só na prosa da SKILL, atribuído à casca — que não tem
# como contar: o Workflow é um só e ela só vê `rounds` depois do return. Sem o
# contador no motor, com `maxRounds` = Infinity um P1 roteado para drift volta em
# `openFindings` toda rodada e o laço NÃO TEM SAÍDA. Este é o único teste que
# EXECUTA o motor: o corpo vira função async com `args`/`agent`/`phase`/`log`
# injetados, e o agente dublê devolve achado sempre e conserto nunca.
HARNESS = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const finding = { id: 'F1', file: 'a.js', severity: 'P1', dimension: 'd', problem: 'p', fix_direction: 'fd' }
let voltas = 0
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review') {
    if (++voltas > 6) throw new Error('LACO-SEM-SAIDA')
    return { complete: false, findings: [finding] }
  }
  if (opts.phase === 'Plan') return { bucket1: [], drift: [{ id: 'F1' }], alerts: [], rejected: [] }
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ stopReason: out.stopReason, sucesso: out.sucesso, rodadas: out.rounds.length }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("duas rodadas com achado e zero conserto param o laço em `teatro-de-duvida`",
          saida.get("stopReason") == "teatro-de-duvida" and saida.get("sucesso") is False
          and saida.get("rodadas") == 2,
          "saída=%s erro=%s" % (r.stdout.strip()[:120], r.stderr.strip()[-160:]))
else:
    print("  skip teatro-de-duvida (node ausente)")

# J · O ABANDONO POR AGENTE MUDO TEM DESFECHO PRÓPRIO (2026-08-24) ─────────
# Sem teto por default, `r < Infinity` NUNCA falha — então o desfecho `max-rounds`
# só é alcançado pelos três `break` de agente que não respondeu, e o relatório saía
# culpando "o freio de Infinity rodada(s)", um freio que não existe. O motivo mandado
# à barra vinha pelo mesmo caminho ('teto de rodadas'). O desfecho é `agente-mudo`, e
# o veredito lê a `nota` que a rodada já gravou.
HARNESS_MUDO = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
let motivoDaBarra = null
const agent = async (prompt, opts) => {
  if (opts.label === 'encerra:barra') { motivoDaBarra = /a missão acabou \(([^)]*)\)/.exec(prompt)[1]; return null }
  if (opts.phase === 'Review') return null   // o revisor não respondeu
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', sessionId: 'sess-1',
    tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ stopReason: out.stopReason, sucesso: out.sucesso,
                             veredito: out.vereditoHumano, motivoDaBarra }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_mudo.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_MUDO)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("agente que não respondeu para o laço em `agente-mudo`, e não em teto de rodadas",
          saida.get("stopReason") == "agente-mudo" and saida.get("sucesso") is False,
          "saída=%s erro=%s" % (r.stdout.strip()[:200], r.stderr.strip()[-160:]))
    check("o veredito nomeia o agente mudo e não culpa freio inexistente",
          "revisor não respondeu" in (saida.get("veredito") or "")
          and "freio" not in (saida.get("veredito") or ""),
          "veredito=%s" % (saida.get("veredito"),))
    check("a barra é encerrada pelo mesmo motivo, não por 'teto de rodadas'",
          saida.get("motivoDaBarra") == "revisor não respondeu",
          "motivo=%s" % (saida.get("motivoDaBarra"),))
else:
    print("  skip agente-mudo (node ausente)")

# L · O LIMITE PROPOSTO NÃO SILENCIA O ACHADO NA MESMA CORRIDA (2026-08-24) ─
# `acceptedLimits` era engordado com `plan.proposedLimits` DENTRO do laço, e a
# partir dali o mesmo achado sumia dos dois filtros que consultam a lista — o de
# `severe` (que libera a rodada limpa) e o do fecho (que monta `emAberto`). O
# planejador ganhava, sozinho, o poder de aposentar o próprio achado: propunha o
# limite e a corrida fechava verde. Proposta só vira limite quando o DONO grava em
# `.claude/qa-loop.config.md`; até lá o achado continua contando.
HARNESS_PROPOSTA = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const finding = { id: 'F1', file: 'a.js', severity: 'P1', dimension: 'd', problem: 'p', fix_direction: 'fd' }
let voltas = 0
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review') {
    if (++voltas > 6) throw new Error('LACO-SEM-SAIDA')
    return { complete: true, findings: [finding] }
  }
  if (opts.phase === 'Confirm') return { complete: true, findings: [] }
  if (opts.phase === 'Plan') return { bucket1: [], drift: [], alerts: [], rejected: [],
                                      proposedLimits: [{ id: 'F1', motivo: 'aceito por mim mesmo' }] }
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ stopReason: out.stopReason, sucesso: out.sucesso,
                             emAberto: out.emAberto.map(f => f.id),
                             propostos: (out.proposedLimits || []).map(l => l.id),
                             aceitos: (out.acceptedLimits || []).map(l => l.id) }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_proposta.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_PROPOSTA)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("limite só PROPOSTO não fecha a corrida como limpa nem some do `emAberto`",
          saida.get("emAberto") == ["F1"] and saida.get("sucesso") is False
          and saida.get("stopReason") != "no-severe-finding",
          "saída=%s erro=%s" % (r.stdout.strip()[:200], r.stderr.strip()[-160:]))
    check("a proposta sai no `return` como proposta, e não como limite aceito",
          "F1" in (saida.get("propostos") or []) and saida.get("aceitos") == [],
          "saída=%s" % (r.stdout.strip()[:200],))
else:
    print("  skip limite proposto (node ausente)")

# M · O VEREDITO DE SUCESSO NÃO PODE DIZER "NENHUM ACHADO" COM ACHADO NA MESA ─
# (2026-08-24) `drift` é destino LEGÍTIMO: o P1 achado na rodada 1 sai para o
# planejador do plano, não vira conserto, e a rodada 2 fecha limpa. Aí o motor
# devolve `sucesso:true` com `emAberto:[F1 · P1]` — e o veredito lido pelo dono
# dizia "nenhum achado acima de P1", a frase mais falsa possível diante da lista
# que vai logo abaixo dela no relatório. O escopo é a HONESTIDADE DO TEXTO: se
# `emAberto` não está vazio, o veredito conta quantos ficaram e diz que estão na
# mesa do dono. `sucesso`/`cleanRound` NÃO mudam — virar drift em bloqueio é
# decisão de desenho do dono.
HARNESS_DRIFT = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const finding = { id: 'F1', file: 'a.js', severity: 'P1', dimension: 'd', problem: 'p', fix_direction: 'fd' }
let voltas = 0
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review') {
    if (++voltas > 6) throw new Error('LACO-SEM-SAIDA')
    return voltas === 1 ? { complete: false, findings: [finding] } : { complete: true, findings: [] }
  }
  if (opts.phase === 'Confirm') return { complete: true, findings: [] }
  if (opts.phase === 'Auditoria') return opts.label.includes('cobertura')
    ? { complete: true, semAncora: 'harness sem plano nem pedido', itens: [] }
    : { complete: true, semAncora: 'harness sem régua', itens: [], foraDaConta: [] }
  if (opts.phase === 'Plan') return { bucket1: [], drift: [{ id: 'F1' }], alerts: [], rejected: [] }
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ sucesso: out.sucesso, veredito: out.vereditoHumano,
                             emAberto: out.emAberto.map(f => f.id) }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_drift.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_DRIFT)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    veredito = saida.get("veredito") or ""
    check("o cenário reproduz: rodada limpa com achado acima do piso ainda de pé",
          saida.get("sucesso") is True and saida.get("emAberto") == ["F1"],
          "saída=%s erro=%s" % (r.stdout.strip()[:200], r.stderr.strip()[-160:]))
    check("o veredito de sucesso NÃO afirma 'nenhum achado' com `emAberto` cheio",
          "nenhum achado" not in veredito, "veredito=%s" % veredito)
    check("o veredito de sucesso conta os que ficaram acima do piso na mesa do dono",
          "1 achado(s) acima do piso" in veredito and "mesa do dono" in veredito,
          "veredito=%s" % veredito)
else:
    print("  skip veredito com drift aberto (node ausente)")

# N · RODADA ESTÉRIL TAMBÉM CONTA COMO RODADA SEM CONSERTO (2026-08-24) ────
# O contador do teatro-de-dúvida exigia achado na rodada para incrementar: com um
# revisor devolvendo `{complete:false, findings:[]}` o contador ZERAVA toda volta e,
# com `maxRounds` = Infinity, nada quebrava o `while` — medido, 51 rodadas até o
# harness lançar exceção. Rodada sem achado E sem conserto é ainda menos produtiva
# que rodada com achado e zero conserto; conta igual. A rodada LIMPA não é atingida:
# ela sai por `cleanRound` (break) antes de chegar ao contador — é o que a checagem M
# prova, fechando `sucesso:true` em 2 rodadas.
HARNESS_ESTERIL = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
let voltas = 0
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review') {
    if (++voltas > 6) throw new Error('LACO-SEM-SAIDA')
    return { complete: false, findings: [] }
  }
  if (opts.phase === 'Plan') return { bucket1: [], drift: [], alerts: [], rejected: [] }
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ stopReason: out.stopReason, sucesso: out.sucesso, rodadas: out.rounds.length }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_esteril.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_ESTERIL)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("revisor que não acha nada e não conserta nada para em 2 rodadas, sem sucesso",
          saida.get("stopReason") == "teatro-de-duvida" and saida.get("sucesso") is False
          and saida.get("rodadas") == 2,
          "saída=%s erro=%s" % (r.stdout.strip()[:200], r.stderr.strip()[-160:]))
else:
    print("  skip rodada estéril (node ausente)")

# O · AS DUAS LISTAS DO FECHO TÊM CARREGADOR NO RELATÓRIO (2026-08-24) ──────
# O motor promete, nos próprios comentários, que a casca "abre o relatório com esta
# lista" (`emAberto`) e que `abaixoDoPiso` "acompanha SEMPRE" — mas comentário de
# motor a casca não lê. A "Estrutura do relatório" mapeava quatro fontes e nenhuma
# era essas duas: achado acima do piso que sobrou não tinha seção onde aparecer, e a
# faixa de status redigitava veredito em vez de imprimir o `vereditoHumano` do fecho.
estrutura = skill[skill.find("Estrutura do relatório (no topo → fundo):"):
                  skill.find("- **Fechamento** (`feedback-box`)")]
check("a estrutura do relatório existe na SKILL", bool(estrutura))
check("a faixa de status imprime o `vereditoHumano` do `return`, literal",
      "`vereditoHumano`" in estrutura)
check("os achados acima do piso que sobraram têm carregador (`emAberto`)",
      "`emAberto`" in estrutura)
check("os não-bloqueantes saem de `abaixoDoPiso`, não de texto redigitado",
      "`abaixoDoPiso`" in estrutura)

# P · O QUE O CONFIRM-PASS ACHA NA RODADA QUE FECHA NÃO PODE SUMIR (2026-08-24) ─
# O fecho varria só `x.review.findings`, e o ramo da rodada limpa empurra `confirm`
# num campo separado. Resultado: tudo o que o confirm-pass achou ABAIXO do piso na
# rodada que fecha a corrida sumia do relatório — contra o Artigo 14 ("some do
# bloqueio, nunca da vista") e contra o comentário do próprio bloco. O ramo
# discordante já fundia as duas listas; o limpo não.
HARNESS_CONFIRM = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const p3 = { id: 'C1', file: 'a.js', severity: 'P3', dimension: 'd', problem: 'p', fix_direction: 'fd' }
let voltas = 0
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review') {
    if (++voltas > 6) throw new Error('LACO-SEM-SAIDA')
    return { complete: true, findings: [] }
  }
  if (opts.phase === 'Confirm') return { complete: true, findings: [p3] }
  if (opts.phase === 'Auditoria') return opts.label.includes('cobertura')
    ? { complete: true, semAncora: 'harness sem plano nem pedido', itens: [] }
    : { complete: true, semAncora: 'harness sem régua', itens: [], foraDaConta: [] }
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ sucesso: out.sucesso, veredito: out.vereditoHumano,
                             abaixoDoPiso: out.abaixoDoPiso.map(f => f.id),
                             emAberto: out.emAberto.map(f => f.id) }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_confirm.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_CONFIRM)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("o achado abaixo do piso visto só pelo confirm-pass é LISTADO, não some",
          saida.get("abaixoDoPiso") == ["C1"] and saida.get("sucesso") is True
          and saida.get("emAberto") == [],
          "saída=%s erro=%s" % (r.stdout.strip()[:200], r.stderr.strip()[-160:]))
else:
    print("  skip achado do confirm-pass (node ausente)")

# Q · CONSERTO QUE QUEBRA A SUÍTE NÃO É "O LAÇO DEIXOU DE ATACAR" (2026-08-24) ─
# `rodadasSemConserto` conta `corrections.length === 0`, e conserto que REGRIDE a
# suíte nunca entra em `corrections`. Com dois fixes regredindo em funções DIFERENTES
# o churn fica 1/2 em cada chave, `churnEscalated` não dispara, e a corrida saía por
# `teatro-de-duvida` com o veredito dizendo "NENHUM virou conserto" — diagnóstico
# invertido: o laço atacou, quebrou a suíte duas vezes e nada foi consertado. Desfecho
# próprio: `regressao-total`, e o veredito nomeia a suíte quebrada.
HARNESS_REGRESSAO = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
let voltas = 0
let motivoDaBarra = null
const agent = async (prompt, opts) => {
  if (opts.label === 'encerra:barra') { motivoDaBarra = /a missão acabou \(([^)]*)\)/.exec(prompt)[1]; return null }
  if (opts.phase === 'Review') {
    if (++voltas > 6) throw new Error('LACO-SEM-SAIDA')
    return { complete: false, findings: [{ id: 'F' + voltas, file: 'a.js', severity: 'P1',
                                           dimension: 'd', problem: 'p', fix_direction: 'fd' }] }
  }
  // cada rodada conserta uma função DIFERENTE: o churn por chave fica 1/2 e não escala
  if (opts.phase === 'Plan') return { bucket1: [{ id: 'F' + voltas, file: 'a.js', fn: 'fn' + voltas,
                                                  severity: 'P1', order: 1 }], drift: [], alerts: [], rejected: [] }
  if (opts.phase === 'Exec') return { fix_id: 'F' + voltas, fn: 'fn' + voltas, files_touched: ['a.js'],
                                      suiteRegressed: true }
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', sessionId: 'sess-1',
    tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ stopReason: out.stopReason, sucesso: out.sucesso,
                             veredito: out.vereditoHumano, rodadas: out.rounds.length, motivoDaBarra }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_regressao.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_REGRESSAO)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    veredito = saida.get("veredito") or ""
    check("duas rodadas em que TODO conserto regrediu param em `regressao-total`",
          saida.get("stopReason") == "regressao-total" and saida.get("sucesso") is False
          and saida.get("rodadas") == 2,
          "saída=%s erro=%s" % (r.stdout.strip()[:220], r.stderr.strip()[-160:]))
    check("o veredito nomeia a suíte quebrada, e não 'nenhum virou conserto'",
          "suíte" in veredito and "NENHUM virou conserto" not in veredito,
          "veredito=%s" % veredito)
    check("a barra é encerrada pelo motivo certo, não por 'teatro de dúvida'",
          saida.get("motivoDaBarra") == "conserto regrediu a suíte",
          "motivo=%s" % (saida.get("motivoDaBarra"),))
else:
    print("  skip regressão total (node ausente)")

# R · O CLAMP POR CAMADA DE REDE NÃO É TETO POR GASTO (2026-08-24) ─────────
# Com `safetyLayer: 5` (projeto sem suíte) o `LAYER_CAP` corta o laço em 1 rodada,
# e o veredito saía "o freio de 1 rodada(s) agiu" — enquadramento de teto por GASTO,
# exatamente o que o Artigo 14 proíbe, e que apaga a causa real: sem suíte que prove
# o conserto, cada volta a mais é aposta cega e multiplica o ESTRAGO. O texto que o
# dono lê tem que nomear a camada e o risco; o freio de quem invoca continua sendo
# outro caso, com outra frase.
HARNESS_CAMADA = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const finding = { id: 'F1', file: 'a.js', severity: 'P1', dimension: 'd', problem: 'p', fix_direction: 'fd' }
let voltas = 0
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review') {
    if (++voltas > 6) throw new Error('LACO-SEM-SAIDA')
    return { complete: false, findings: [finding] }
  }
  if (opts.phase === 'Plan') return { bucket1: [], drift: [{ id: 'F1' }], alerts: [], rejected: [] }
  return null
}
const e = { effort: 'm' }
const corrida = async extra => await motor(
  { repoRoot: '/x', model: 'm', ...extra,
    tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
const porCamada = await corrida({ safetyLayer: 5 })
voltas = 0
const porQuemInvoca = await corrida({ maxRounds: 1 })
console.log(JSON.stringify({
  camada: { stopReason: porCamada.stopReason, sucesso: porCamada.sucesso,
            rodadas: porCamada.rounds.length, veredito: porCamada.vereditoHumano },
  invocador: { veredito: porQuemInvoca.vereditoHumano } }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_camada.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_CAMADA)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    camada = saida.get("camada") or {}
    v_camada = camada.get("veredito") or ""
    v_invoc = (saida.get("invocador") or {}).get("veredito") or ""
    check("o cenário reproduz: Camada 5 clampa o laço em 1 rodada, sem sucesso",
          camada.get("rodadas") == 1 and camada.get("sucesso") is False
          and camada.get("stopReason") == "max-rounds",
          "saída=%s erro=%s" % (r.stdout.strip()[:220], r.stderr.strip()[-200:]))
    check("o veredito do clamp NÃO enquadra como freio por gasto de rodadas",
          "freio" not in v_camada, "veredito=%s" % v_camada)
    check("o veredito do clamp nomeia a camada de rede e o risco de estrago",
          "Camada 5" in v_camada and "ESTRAGO" in v_camada,
          "veredito=%s" % v_camada)
    check("o teto passado por quem invoca continua saindo como freio, e é outra frase",
          "freio de 1 rodada(s)" in v_invoc and v_invoc != v_camada,
          "veredito=%s" % v_invoc)
else:
    print("  skip clamp por camada (node ausente)")

# S · O MOTOR NÃO AFIRMA REVERSÃO QUE NINGUÉM FEZ (2026-08-24) ─────────────
# A SKILL manda `revertAndMaybeRedo` e o motor logava "revertido" — mas nada no
# motor desfaz nada, e o `execPrompt` não tinha passo de desfazer. Sem teto por
# default, a edição quebrada se empilha rodada após rodada enquanto o operador lê
# "revertido". Quem desfaz é o EXECUTOR, e a afirmação só sai quando ele confirma.
HARNESS_REVERSAO = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const e = { effort: 'm' }
const corrida = async reverted => {
  const linhas = []
  let promptDoExec = null
  const agent = async (prompt, opts) => {
    if (opts.phase === 'Review') return { complete: false, findings: [{ id: 'F1', file: 'a.js',
      severity: 'P1', dimension: 'd', problem: 'p', fix_direction: 'fd' }] }
    if (opts.phase === 'Plan') return { bucket1: [{ id: 'F1', file: 'a.js', fn: 'fn1', severity: 'P1', order: 1 }],
                                        drift: [], alerts: [], rejected: [] }
    if (opts.phase === 'Exec') { promptDoExec = prompt
      return { fix_id: 'F1', fn: 'fn1', files_touched: ['a.js'], suiteRegressed: true, ...(reverted === null ? {} : { reverted }) } }
    return null
  }
  await motor({ repoRoot: '/x', model: 'm', maxRounds: 1,
    tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
    agent, () => {}, m => linhas.push(m))
  return { linhas, promptDoExec }
}
const semConfirmar = await corrida(null)
const confirmado = await corrida(true)
console.log(JSON.stringify({ semConfirmar: semConfirmar.linhas, confirmado: confirmado.linhas,
                             promptDoExec: semConfirmar.promptDoExec }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_reversao.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_REVERSAO)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    sem = " ".join(saida.get("semConfirmar") or [])
    com = " ".join(saida.get("confirmado") or [])
    prompt_exec = saida.get("promptDoExec") or ""
    check("sem confirmação do executor, o log NÃO afirma que a edição foi revertida",
          bool(sem) and "revertid" not in sem,
          "log=%s erro=%s" % (sem[:200], r.stderr.strip()[-160:]))
    check("sem confirmação, o log diz que a edição FICOU DE PÉ e precisa de decisão",
          "FICOU DE PÉ" in sem, "log=%s" % sem[:200])
    check("com `reverted: true` do executor, o log afirma que a edição foi desfeita",
          "desfez" in com or "revertid" in com, "log=%s" % com[:200])
    check("o `execPrompt` ORDENA desfazer a própria edição quando a suíte regride",
          "DESFA" in prompt_exec.upper() and "reverted" in prompt_exec,
          "prompt sem o passo de desfazer")
    check("`reverted` é campo do schema que o executor devolve",
          "reverted:{type:'boolean'}" in motor or "reverted: {type: 'boolean'}" in motor)
    check("o veredito de regressão total não afirma reversão que ninguém confirmou",
          "quebrou a suíte e foi revertido" not in motor)
else:
    print("  skip reversão confirmada (node ausente)")

# R · OS PILARES COBERTURA E COERÊNCIA — AUDITORIA EXTERNA NO CANDIDATO A FECHO ─
# (2026-08-28, ordem do dono) Todo revisor mede três pilares contra três âncoras.
# A rodada limpa é CANDIDATA: dois auditores isolados rodam antes do fecho, e quem
# soma o 100% é o script. Checagens de TEXTO primeiro; os cenários executam depois.
check("o schema AUDIT_COBERTURA existe, com as lentes",
      "AUDIT_COBERTURA" in motor and "'sem-infra'" in motor and "'antipadrao'" in motor)
check("o schema AUDIT_COERENCIA existe, com os vereditos item a item",
      "AUDIT_COERENCIA" in motor and "'violado'" in motor and "'nao-medido'" in motor)
check("o auditor é ISOLADO: o bloco SEM_HISTORICO existe",
      "SEM_HISTORICO" in motor and "NÃO recebe os achados do revisor" in motor)
audit_prompts = motor[motor.find("const auditCoberturaPrompt"):motor.find("const sevRank")]
check("os prompts de auditoria não interpolam o histórico do laço",
      audit_prompts and "review" not in audit_prompts and "openFindings" not in audit_prompts
      and "rounds" not in audit_prompts)
check("a conta do 100% é do script (furosDe + filtros em JS)",
      "furosDe" in motor and "furosCobertura" in motor
      and "i.veredito === 'violado' || i.veredito === 'nao-medido'" in motor)
check("as três âncoras entram por args e a ausência é DECLARADA",
      "ARGS.pedidos" in motor and "pedidosAusentes" in motor and "AUSENTE" in motor)
check("dispensa de lente é ratificação do dono, por args",
      "lentesDispensadas" in motor and "ARGS.lentesDispensadas" in motor)
check("cobertura sem infra E2E tem veredito literal e nunca sucesso silencioso",
      "COBERTURA NÃO MEDIDA NA LENTE E2E" in motor and "auditoriaNaoMedida" in motor)
check("o return devolve os três pilares",
      "pilares:" in motor and "qualidade:" in motor and "cobertura:" in motor and "coerencia:" in motor)
check("finding AUD-* não é rebaixado nem rejeitado pelo árbitro (garantia no script)",
      "/^AUD-/" in motor and "AUD-*" in motor)

# R1 · auditoria reprova → o laço REABRE → fecha na tentativa seguinte com 100%.
HARNESS_AUDITORIA = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const lenteOk = { veredito: 'sim', evidencia: 'ev' }
const itemFuro = { id: 'S-1', origem: 'plano', descricao: 'a finalidade', implementado: lenteOk,
  suite: { veredito: 'descoberta', teste: null, antipadrao: null, evidencia: 'sem teste' },
  e2e: { veredito: 'confirmado', evidencia: 'jornada ok' } }
const itemOk = { ...itemFuro, suite: { veredito: 'morde', teste: 't', antipadrao: null, evidencia: 'ev' } }
let audits = 0, voltas = 0
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review' || opts.phase === 'Confirm') {
    if (++voltas > 12) throw new Error('LACO-SEM-SAIDA')
    return { complete: true, findings: [] }
  }
  if (opts.phase === 'Auditoria') {
    if (opts.label.includes('cobertura'))
      return { complete: true, semAncora: null, itens: [++audits === 1 ? itemFuro : itemOk] }
    return { complete: true, semAncora: null, foraDaConta: [],
             itens: [{ documento: 'constituicao.md', item: 'Artigo 1', veredito: 'conforme',
                       passagem: null, evidencia: 'ev' }] }
  }
  if (opts.phase === 'Plan') return { bucket1: [], drift: [], alerts: [], rejected: [] }
  if (opts.phase === 'Exec') return { fix_id: 'AUD-C1', fn: 'f', files_touched: ['a.js'], suiteRegressed: false }
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm', planPath: 'p.md',
    tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ sucesso: out.sucesso, stopReason: out.stopReason,
  rodadas: out.rounds.length, cob: out.pilares.cobertura.status, coe: out.pilares.coerencia.status,
  veredito: out.vereditoHumano }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_auditoria.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_AUDITORIA)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("auditoria com furo NÃO fecha a rodada limpa — o laço reabre e conserta",
          saida.get("sucesso") is True and saida.get("rodadas", 0) >= 2
          and saida.get("cob") == "aprovada" and saida.get("coe") == "aprovada",
          "saída=%s erro=%s" % (r.stdout.strip()[:200], r.stderr.strip()[-200:]))
    check("o veredito de sucesso declara o estado dos dois pilares auditados",
          "auditoria externa" in (saida.get("veredito") or ""),
          "veredito=%s" % (saida.get("veredito"),))
else:
    print("  skip auditoria reprova-e-reabre (node ausente)")

# R2 · sem infraestrutura E2E e sem dispensa: fecha DECLARADO, nunca sucesso.
HARNESS_SEMINFRA = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const item = { id: 'S-1', origem: 'plano', descricao: 'a finalidade',
  implementado: { veredito: 'sim', evidencia: 'ev' },
  suite: { veredito: 'morde', teste: 't', antipadrao: null, evidencia: 'ev' },
  e2e: { veredito: 'sem-infra', evidencia: 'projeto sem playwright' } }
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review' || opts.phase === 'Confirm') return { complete: true, findings: [] }
  if (opts.phase === 'Auditoria') return opts.label.includes('cobertura')
    ? { complete: true, semAncora: null, itens: [item] }
    : { complete: true, semAncora: null, foraDaConta: [],
        itens: [{ documento: 'constituicao.md', item: 'Artigo 1', veredito: 'conforme', passagem: null, evidencia: 'ev' }] }
  return null
}
const e = { effort: 'm' }
const roda = async dispensa => motor(
  { repoRoot: '/x', model: 'm', planPath: 'p.md', lentesDispensadas: dispensa,
    tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
const sem = await roda([])
const com = await roda(['e2e'])
console.log(JSON.stringify({
  semSucesso: sem.sucesso, semStop: sem.stopReason, semCob: sem.pilares.cobertura.status,
  semVeredito: sem.vereditoHumano,
  comSucesso: com.sucesso, comCob: com.pilares.cobertura.status, comVeredito: com.vereditoHumano }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_seminfra.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_SEMINFRA)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("lente E2E sem infra e sem dispensa: fecha declarado, `sucesso: false`",
          saida.get("semSucesso") is False and saida.get("semStop") == "cobertura-nao-medida"
          and saida.get("semCob") == "nao-medida-lente-e2e",
          "saída=%s erro=%s" % (r.stdout.strip()[:240], r.stderr.strip()[-160:]))
    check("o veredito sem dispensa traz o literal do contrato",
          "COBERTURA NÃO MEDIDA NA LENTE E2E" in (saida.get("semVeredito") or ""),
          "veredito=%s" % (saida.get("semVeredito"),))
    check("com a dispensa RATIFICADA em args, a lente sai da conta e o fecho declara isso",
          saida.get("comSucesso") is True and saida.get("comCob") == "aprovada"
          and "dispensada" in (saida.get("comVeredito") or ""),
          "saída=%s" % (r.stdout.strip()[:240],))
else:
    print("  skip lente E2E sem infra (node ausente)")

# R3 · auditor mudo nunca fecha.
HARNESS_AUDMUDO = r"""
import fs from 'node:fs'
const src = fs.readFileSync(process.argv[2], 'utf8').replace('export const meta', 'const meta')
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const motor = new AsyncFunction('args', 'agent', 'phase', 'log', src)
const agent = async (prompt, opts) => {
  if (opts.phase === 'Review' || opts.phase === 'Confirm') return { complete: true, findings: [] }
  if (opts.phase === 'Auditoria') return null
  return null
}
const e = { effort: 'm' }
const out = await motor(
  { repoRoot: '/x', model: 'm',
    tiers: { decompose: e, coordinate: e, finalize: e, executor: e, diagnose: e, mechanical: e } },
  agent, () => {}, () => {})
console.log(JSON.stringify({ sucesso: out.sucesso, stopReason: out.stopReason, veredito: out.vereditoHumano }))
"""

if shutil.which("node"):
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        h = os.path.join(d, "harness_audmudo.mjs")
        open(h, "w", encoding="utf-8").write(HARNESS_AUDMUDO)
        r = subprocess.run(["node", h, MOTOR], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", stdin=subprocess.DEVNULL, start_new_session=True, timeout=60)
    saida = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check("auditor mudo nunca fecha: `sucesso: false` e o motivo nomeado",
          saida.get("sucesso") is False
          and "auditor externo não respondeu" in (saida.get("veredito") or ""),
          "saída=%s erro=%s" % (r.stdout.strip()[:200], r.stderr.strip()[-160:]))
else:
    print("  skip auditor mudo (node ausente)")

# sintaxe: tem que ser JavaScript válido (quando node existe na máquina).
if shutil.which("node"):
    r = subprocess.run(["node", "--check", MOTOR], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    check("node --check passa", r.returncode == 0, r.stderr.strip()[:160])
else:
    print("  skip node --check (node ausente)")

print()
if falhas:
    print("FALHOU: %d" % falhas)
    sys.exit(1)
print("test_qa_loop_motor: %d checagens verdes" % ok)
