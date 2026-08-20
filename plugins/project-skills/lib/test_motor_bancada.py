#!/usr/bin/env python3
"""Bancada do motor — ele RODA contra um plano de mentira, e se afere o que ficou.

Cinco coisas se medem aqui: o plano sai marcado (F9.10), o teto de gasto desliga o motor
(F9.12), o vigia derruba a execucao com o registro mudo alem do limite e sem trabalho
vivo (F9.13 + F9.24), a onda verde fica no historico quando o motor e interrompido no
meio (F9.14), a onda VERMELHA nao vira ponto de salvamento — nada e commitado e o
motor relata pelo nome qual suite quebrou (F9.15) —, e a concepcao errada vira aviso
"precisa de voce" SEM segurar a obra (S-9).

`test_travas_motor.py` cobra que a logica esta ESCRITA no esqueleto. Isso nao prova
que ela funciona: o bloco pode citar `tickPlanPrompt` e nada acontecer no arquivo do
plano. Aqui o esqueleto do SKILL.md e EXECUTADO em Node com os agentes de mentira, e o
papel que marca roda o comando REAL (o mesmo que a skill escreve, extraido dela) contra
um plano de verdade criado num diretorio temporario. O que se afere e o ARQUIVO depois:
quais passos ficaram `done`, e com que prova.

Sem Node ou sem Python o teste NAO inventa aprovacao — falha dizendo o que faltou.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bash_posix import bash_posix  # noqa: E402  — o vendorado ao lado, nunca o PATH pelado

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL_MD = os.path.join(AQUI, "..", "skills", "sprint", "SKILL.md")
PLAN_STATE = os.path.join(AQUI, "plan_state.py")

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
    """O MAIOR bloco ```javascript — o motor. Mesma regra do test_travas_motor."""
    blocos = re.findall(r"```javascript\n(.*?)\n```", texto, re.S)
    return max(blocos, key=len) if blocos else ""


def comando_de_tique(texto):
    """A linha de comando que a skill manda o papel de marcacao rodar.

    Extraida do SKILL.md para o teste rodar O QUE ESTA ESCRITO la — comando copiado
    para dentro do teste envelhece calado e passa a aprovar o que ninguem executa.
    """
    for bloco in re.findall(r"```bash\n(.*?)\n```", texto, re.S):
        for linha in bloco.splitlines():
            # o caminho do marcador deixou de ser cravado e virou BUSCA (F9.51), então
            # ele nasce numa linha e o `tick` roda na seguinte, com a variavel. Casa a
            # linha do tique tanto pelo nome do programa quanto pela variavel que o
            # resolveu — exigir os dois na mesma linha reprovava o conserto.
            if " tick " in linha and ("plan_state.py" in linha or "$MARCADOR" in linha):
                return linha.strip()
    return ""


def comando_de_checkpoint(texto):
    """A linha de comando com que a skill salva a onda verde no historico.

    Mesma regra do tique: extraida do SKILL.md, para a bancada rodar O QUE ESTA
    ESCRITO la — comando copiado para dentro do teste passaria a aprovar um salvamento
    que a skill nao manda mais fazer.
    """
    for bloco in re.findall(r"```bash\n(.*?)\n```", texto, re.S):
        for linha in bloco.splitlines():
            if "git -C" in linha and "commit" in linha:
                return linha.strip()
    return ""


# ── o plano de bancada ───────────────────────────────────────────────────────
PLANO = {
    "id": "2026-08-07-bancada-sprint",
    "title": "Plano de bancada do motor",
    "requisitos": [{"id": "S-18", "titulo": "O plano registra o que o motor fez",
                    "ca": "os passos saem marcados sem ninguem marcar a mao",
                    "epico": "E0 — Bancada"}],
    "phases": [{"id": "F1", "title": "Fase de bancada", "items": [
        {"id": "F1.1", "title": "Passo entregue", "desc": "o executor devolve done",
         "requisito": "S-18", "pronto": "o passo sai marcado com a prova"},
        {"id": "F1.2", "title": "Passo tambem entregue", "desc": "outro executor devolve done",
         "requisito": "S-18", "pronto": "o passo sai marcado com a prova"},
        {"id": "F1.3", "title": "Passo nao entregue", "desc": "o executor devolve done falso",
         "requisito": "S-18", "pronto": "o passo continua aberto"},
        {"id": "F1.4", "title": "Passo que estourou o teto", "desc": "o executor pede espera",
         "requisito": "S-18", "pronto": "o passo continua aberto"},
    ]}],
}

# Os agentes de mentira. O executor de F1.3 devolve `done: false` e o de F1.4 devolve
# `espera: true` — os dois casos que NAO podem sair marcados.
RESULTADOS = {
    "F1.1": {"task_id": "F1.1", "done": True, "summary": "escrevi o arquivo",
             "files_touched": ["a.py"], "anchor": "fim"},
    "F1.2": {"task_id": "F1.2", "done": True, "summary": "ajustei o hook",
             "files_touched": ["b.sh", "c.sh"], "anchor": "fim"},
    "F1.3": {"task_id": "F1.3", "done": False, "summary": "nao consegui",
             "files_touched": [], "anchor": "fim"},
    "F1.4": {"task_id": "F1.4", "done": True, "espera": True, "summary": "estourei o teto",
             "files_touched": ["d.py"], "anchor": "fim"},
}

# ── a alegacao de impossivel (F9.18) ────────────────────────────────────────
# O que o executor diz quando desiste, e o que ele TINHA na mao quando disse. O caso real
# e este: o diagnostico dizia "exige navegador", e o agente tinha navegador.
ALEGACAO = "nao da: exige navegador contra producao"
FERRAMENTAS_A_MAO = ["navegador", "terminal", "leitura de arquivo"]

# ── o replay de cache (F9.35) ────────────────────────────────────────────────
# Retomar a missao REGRAVA veredito: o runtime devolve do cache o que ja tinha sido
# entregue. Duas coisas voltam — a mesma tarefa outra vez, com o mesmo `task_id`, e a
# devolucao do DECOMPOSITOR, que nao e passo nenhum e vem SEM `task_id`. As duas viram
# linha em `results`, e quem contava linha via cinco onde havia tres.
REPLAY_DECOMP_ID = "REPLAY-DECOMP"
REPLAY_DECOMP_RESULT = {"done": True, "summary": "replay da decomposicao vinda do cache",
                        "files_touched": [], "anchor": "fim",
                        "tasks": [{"id": "F1.1"}, {"id": "F1.2"}]}

# ── a concepcao errada (S-9) ─────────────────────────────────────────────────
# O gap que diz "a entrevista errou, o codigo esta certo". Ele tem DUAS promessas no
# motor, e o par abaixo so serve se a UNICA diferenca entre os dois for o `kind` — e o
# controle de `spec` existe pra provar que quem soltou a obra foi o kind, e nao o cenario.
GAP_CONCEPCAO = {"task_id": "F1.1", "kind": "concepcao", "severity": "P0",
                 "problem": "o documento aprovado promete cache local, e o que se descobriu "
                            "e que a origem nao versiona nada"}
GAP_SPEC = dict(GAP_CONCEPCAO, kind="spec")

# ── a obra contradiz o desenho aprovado (S-104) ──────────────────────────────
# A contradicao injetada: o esquema aprovado desenha uma coisa e a obra fez outra. Pelo
# eixo de constituicao ela nasce como gap de `constituicao` e SEGURA a obra; se o errado
# for o desenho, o mesmo texto entra como `concepcao` e vira aviso sem segurar nada.
GAP_DESENHO = {"task_id": "F1.1", "kind": "constituicao", "severity": "P0",
               "problem": "`.claude/docs/blueprint.md` (aprovado) desenha a leitura saindo "
                          "do cache local, e a obra le a origem a cada chamada"}
GAP_DESENHO_CONCEPCAO = dict(GAP_DESENHO, kind="concepcao")

HARNESS = r"""
const { execSync } = require('child_process')
const fs = require('fs')
const CFG = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const CORPO = fs.readFileSync(process.argv[3], 'utf8')

const PRELUDE = `
const DECOMP={}, TASK_RESULT={}, BUILD_REVIEW={}, RESERVA={}, REGUA={}, SUITE_RESULT={}, AUDITOR={}, DOC_TOUCH={}, TICK_RESULT={}, DESAFIO={}, TAREFA_REVIEW={}, DOC_REVIEW={}, SAUDE={}, CHECKPOINT_RESULT={}, DESTRAVE={}, PRODUTIVIDADE={};
const mk = n => (p => Object.assign({ __p: n }, p));
const orquestradorPrompt=mk('decompose'), saudePrompt=mk('saude'),
      decomposePrompt=mk('decompose'), execPrompt=mk('exec'), reviewBuildPrompt=mk('review'),
      runSuitePrompt=mk('suite'), checkpointPrompt=mk('checkpoint'), tickPlanPrompt=mk('tick'),
      docTouchPrompt=mk('docTouch'), colheitaPrompt=mk('colheita'), encerraPrompt=mk('encerra'),
      diagnoseStuckTaskPrompt=mk('diag'), reservaPrompt=mk('reserva'), confirmBuildPrompt=mk('confirm'),
      reguaPrompt=mk('regua'), auditorPrompt=mk('auditor'), desafioCausaPrompt=mk('desafio'),
      revisorTarefaPrompt=mk('revTarefa'), revisorBlocoPrompt=mk('revBloco'),
      revisaoDocPrompt=mk('revDoc'), destravadorPrompt=mk('destrava'),
      pendenciaPrompt=mk('pendencia'), produtividadePrompt=mk('produtividade');
`

const chamadas = []
const checkpoints = []
// O juiz que nao prova que leu (F9.16). `vereditos` registra, na ordem, se a chamada veio
// com o aviso de recusa — e com isso a bancada consegue perguntar se o papel foi RE-RODADO
// e se ele soube por que voltou. `CFG.reviewSemAncora` escolhe o cenario: 'primeira' (a
// primeira volta sem ancora, a segunda com) ou 'sempre' (juiz que nunca prova).
const vereditos = []
const auditorias = []
const investigacoes = []
const desafios = []
// O destravador (F23.9): o que ele recebeu, e se ele disse ter consertado — é o que
// deixa a porta mudar de estado entre a causa e a re-medição.
const destraves = []
let destravou = false
const docs = []
const agentes = []
// F9.57: QUEM foi despachado, na ordem. `agentes` so guarda o papel ('exec'), e com ele
// nao da pra perguntar se o bloco seguinte ao da falha chegou a sair — que e a unica
// pergunta que separa "reagiu antes de a onda terminar" de "reagiu no fim dela".
const executados = []
const phase = () => {}
// `log` e API do runtime igual a `phase`, e a bancada nao a fornecia: o motor que a
// usasse morria aqui com ReferenceError e a bancada acusava "o motor nao rodou" —
// falha de AMBIENTE com a mesma cara de falha de logica. Ela guarda as linhas para
// o teste poder afirmar o que o motor narrou.
const narrado = []
const log = m => { narrado.push(String(m)) }
// O medidor de gasto da bancada: cada agente disparado queima `gastoPorChamada`. E o
// unico jeito de o disjuntor ser exercitado de verdade — com `spent()` fixo em zero
// (como era aqui), o teto nunca e alcancado e a trava passa sem nunca ter armado.
let gastoAcumulado = 0
// `CFG.gastoBase` + `CFG.gastoCaiEm` reproduzem o contador que ANDA PARA TRÁS. No caso
// real o motor entra num turno que JÁ gastou (base alta) e, no meio da corrida, o
// contador do runtime reinicia: `spent()` devolve um número menor que o do arranque, e
// `spent() - inicial` fica negativo — foi assim que uma corrida de 6h relatou
// `gasto: -831562`. Sem a base alta o defeito não aparece, porque a bancada começa do
// zero e a diferença nunca chega a ser negativa.
let chamadasDeGasto = 0
const budget = { spent: () => {
  chamadasDeGasto++
  if (CFG.gastoCaiEm && chamadasDeGasto >= CFG.gastoCaiEm) return gastoAcumulado
  return (CFG.gastoBase || 0) + gastoAcumulado
} }
const parallel = fns => Promise.all(fns.map(f => f()))

// O papel de marcacao roda o comando REAL da skill. E o unico agente com efeito de
// verdade: os outros so devolvem o dado canonico da rodada.
// F9.53: a marcacao virou UM agente para a onda, com N comandos em sequencia. O papel
// recebe `passos: [{taskId, evidencia}]` — nao mais um passo por chamada. E F9.54: ele
// devolve o veredito de CADA passo, porque antes o retorno era descartado e um agente
// que morria calado deixava passo entregue gravado como nao feito.
function tica(p) {
  const passos = p.passos || (p.taskId ? [{ taskId: p.taskId, evidencia: p.evidencia }] : [])
  const marcados = []
  for (const passo of passos) {
    let cmd = CFG.tickCmd
    for (const [k, v] of Object.entries({ '<plugin project-skills>': CFG.pluginSkills, '<raiz>': CFG.raiz,
                                          '$MARCADOR': CFG.pluginSkills + '/lib/plan_state.py',
                                          '<plano>': CFG.planoId, '<taskId>': passo.taskId,
                                          '<evidencia>': passo.evidencia })) {
      cmd = cmd.split(k).join(v)
    }
    chamadas.push({ taskId: passo.taskId, evidencia: passo.evidencia, cmd })
    // Falha de um passo NAO interrompe os seguintes: e o que preserva a recusa
    // individual que o lote perderia. O motivo entra no veredito daquele passo.
    try {
      execSync(cmd, { stdio: 'pipe' })
      marcados.push({ task_id: passo.taskId, ok: true, motivo: '' })
    } catch (e) {
      marcados.push({ task_id: passo.taskId, ok: false,
                      motivo: String((e.stderr || e.stdout || e.message)).slice(0, 200) })
    }
  }
  return { marcados }
}

// O papel que salva a onda, com efeito de verdade tambem: roda o comando REAL da skill
// (extraido dela) no repositorio de bancada. Sem efeito, "salvou" seria so uma string na
// lista de agentes — e o que se quer medir aqui e o que sobrou no HISTORICO depois de o
// motor ser interrompido.
function salva(p) {
  // O motor 0.22.53+ segura a marcacao sem `committed: true` — o stub devolve o
  // veredito de commit aceito, como um gate que aprovou (arvore limpa conta).
  if (!CFG.checkpointCmd) return { committed: true, sha: 'bancada' }
  let cmd = CFG.checkpointCmd
  // A lista de arquivos e a que o papel recebe: a uniao dos `files_touched` das tarefas
  // aprovadas no bloco, mais o arquivo do plano que o tique acabou de marcar.
  const alvos = [...new Set((p.results || []).flatMap(x => x?.files_touched || []))]
  if (p.planPath?.endsWith('.plan.json')) alvos.push(p.planPath)
  // Barra invertida some dentro do bash (vira escape), entao a raiz do Windows entra
  // aqui em barra normal — o git a entende igual nos dois sistemas.
  const raizSh = CFG.raiz.split('\\').join('/')
  for (const [k, v] of Object.entries({ '<raiz>': raizSh, '<r>': String(p.round),
                                        '<b>': String(p.bloco ?? 1),
                                        '<arquivo...>': alvos.map(a => a.split('\\').join('/')).join(' ') })) {
    cmd = cmd.split(k).join(v)
  }
  checkpoints.push({ round: p.round, cmd })
  // O comando da skill e POSIX (`for`/`&&`/`||`), entao precisa de sh — mas no Windows
  // nao existe /bin/sh e o spawn morre com ENOENT antes de rodar. O bash do Git for
  // Windows esta no PATH (e o proprio shell do job do CI), e entende a mesma sintaxe.
  // O comando e POSIX, e no Windows o `bash` PELADO do PATH e o do WSL — que em
  // maquina sem distro responde em UTF-16 e roda `cd C:/...` dentro do namespace do
  // Linux. Quem resolve isso ja existe e e vendorado ao lado: lib/bash_posix.py. O
  // caminho ABSOLUTO vem no CFG; sem ele, /bin/sh (o caso POSIX de sempre).
  execSync(cmd, { stdio: 'pipe', shell: CFG.shell || '/bin/sh' })
  return { committed: true, sha: 'bancada' }
}

// O papel que INVOCA SKILL, com efeito de verdade tambem — igual ao que roda comando.
// No caso honesto a re-projecao acontece: o arquivo da doc daquela onda e ESCRITO, e o
// papel devolve o caminho. Com CFG.docFalso o papel MENTE ter feito: devolve um caminho
// que ninguem escreveu. Os dois passam pela mesma peneira, que e o disco — e e por isso
// que a mentira volta como lista vazia, sem o motor precisar acreditar em ninguem.
function documenta(p) {
  const alegado = CFG.docFalso || ('.claude/docs/onda-' + p.round + '.md')
  if (!CFG.docFalso) {
    fs.mkdirSync(CFG.raiz + '/.claude/docs', { recursive: true })
    fs.writeFileSync(CFG.raiz + '/' + alegado, 'doc re-projetada na onda ' + p.round + '\n')
  }
  const confirmados = [alegado].filter(f => fs.existsSync(CFG.raiz + '/' + f))
  docs.push({ round: p.round, files: p.files, alegados: [alegado], docs: confirmados })
  return { docs: confirmados }
}

async function agent(p, opts) {
  agentes.push(p.__p)
  gastoAcumulado += (CFG.gastoPorChamada || 0)
  switch (p.__p) {
    case 'decompose': return { tasks: CFG.tasks, blockers: [] }
    // A guarda de saúde: aberta por padrão; CFG.portaFechada exercita a parada.
    // O DESTRAVADOR (F23.9) precisa da porta MUDANDO de estado: fechada quando a causa
    // aparece, aberta depois do conserto. Com a resposta fixa, o cenário do conserto
    // que PEGA nunca aconteceria — e é ele que separa "consertou e seguiu" de "morreu".
    // `portaFechaSoNaRemedida` é o cenário do conserto que NÃO pegou: a largada passa
    // (a corrida chega a rodar), e a porta só aparece fechada na re-medição de depois
    // do destravador — que é onde o motor tem de desligar mesmo com ele dizendo que
    // consertou. Sem isso, porta fechada na largada mataria a rodada antes da causa.
    case 'saude': {
      const fechada = CFG.portaFechada === true ||
                      (CFG.portaFechaSoNaRemedida === true && destraves.length > 0)
      return { fechada, motivo: fechada ? 'check determinístico reprovou' : '',
               saida: fechada ? 'gate: 2 achado(s) novo(s)' : '' }
    }
    // O papel que conserta a causa referendada DURANTE a corrida. O cenário escolhe se
    // ele consegue (CFG.destravaOk); `destraves` guarda o que ele recebeu, para a
    // bancada poder perguntar se a CAUSA chegou nele — destravar sem a causa é remendo.
    case 'destrava':
      destraves.push({ causa: p.causa })
      destravou = CFG.destravaOk === true
      return { destravou, oQueFez: 'consertei a causa e commitei sozinho',
               prova: 'suite: 4 ok' }
    // A recusa da reserva vem do cenario. Com ela fixa em `false` (como era aqui) o
    // caminho de saida por `reserva` nunca acontecia na bancada — e ele e o UNICO que
    // sai sem apagar o sinal da sessao, porque o outro motor segue vivo.
    case 'reserva':   return { recusado: CFG.reservaRecusada === true,
                               arquivos: CFG.reservaRecusada ? ['F1.1.txt'] : [] }
    case 'exec':
      executados.push(p.task.id)
      // Executor que nao deixa nada no disco nao permite perguntar onde o trabalho foi
      // parar. Com CFG.escreveNoDisco ele escreve o arquivo da tarefa na raiz do repo.
      // Ele escreve o que DECLARA em `files_touched` — e nada alem disso. E o que deixa
      // medir o commit da onda contra a lista declarada (F9.60): arquivo no historico que
      // ninguem declarou so pode ter vindo de uma varredura da arvore.
      if (CFG.escreveNoDisco && CFG.results[p.task.id]?.done) {
        for (const f of CFG.results[p.task.id].files_touched || []) {
          fs.writeFileSync(CFG.raiz + '/' + f, 'obra de ' + p.task.id + '\n')
        }
      }
      return CFG.results[p.task.id]
    // Os gaps vem do cenario. Com eles fixos em vazio (como era aqui), nenhuma regra do
    // motor que julga gap era exercitada — nem a que vira aviso, nem a que segura a obra.
    case 'review': {
      vereditos.push(!!p.recusado)
      const semAncora = CFG.reviewSemAncora === 'sempre' ||
                        (CFG.reviewSemAncora === 'primeira' && !p.recusado)
      const v = { complete: CFG.reviewComplete !== false, cohesive: true,
                  gaps: CFG.gaps || [],
                  missingTasks: CFG.reviewComplete === false ? ['F1.3'] : [],
                  lawMark: null }
      if (!semAncora) v.anchor = 'ultima linha do que julguei'
      return v
    }
    // O trabalho vivo vem do cenario: fixo em `false` (como era aqui) a metade que
    // separa demora de travamento nunca seria exercitada, do mesmo jeito que o
    // disjuntor com spent() zerado.
    // A COR da suite vem do cenario. Com ela fixa em verde (como era aqui) a onda
    // vermelha nunca acontece, e a metade do F9.15 que RECUSA o salvamento passaria sem
    // nunca ter sido exercitada — mesmo vicio do spent() zerado.
    // A suite da LARGADA (`bloco: 0`, uma vez na rodada 1) mede o repositorio ANTES da
    // missao, e nos cenarios daqui ele comeca verde: o vermelho e da onda. Sem separar
    // as duas, `suiteVerde: false` fecharia a porta na largada e nenhuma onda sairia —
    // o cenario da onda vermelha nunca aconteceria. Quem quiser a largada VERMELHA
    // (a porta fechada antes de qualquer executor) pede por `largadaFalhando`: sem
    // ela o comportamento e o de sempre — largada verde.
    case 'suite':     return { green: p.bloco === 0 ? !(CFG.largadaFalhando || []).length
                                                    : CFG.suiteVerde !== false,
                               failing: p.bloco === 0 ? CFG.largadaFalhando || []
                                                      : CFG.suiteFalhando || [],
                               placar: '4 ok',
                               trabalhoVivo: CFG.trabalhoVivo === true }
    case 'checkpoint': return salva(p)
    // O auditor da alegacao de impossivel (F9.18). O cenario escolhe o desfecho, e o que
    // ele RECEBEU fica registrado: sem isso a bancada nao consegue perguntar se a lente
    // invertida chegou com a lista do que havia a mao.
    case 'auditor':
      auditorias.push({ taskId: p.task && p.task.id, alegacao: p.alegacao,
                        ferramentas: p.ferramentas, tentativas: p.tentativas })
      return { derruba: CFG.auditorDerruba === true, motivo: CFG.auditorMotivo || '',
               naoTentou: CFG.auditorNaoTentou || [], anchor: 'ultima linha do que auditei' }
    case 'docTouch':  return documenta(p)
    case 'tick':      return tica(p)
    // O investigador de tarefa-presa e o desafiador da causa (autopsia 2026-08-09).
    // `desafios` registra o que cada um recebeu; o cenario escolhe em que volta o
    // desafiador referenda (CFG.desafioReferendaNaVolta; 0 = nunca).
    case 'diag':
      investigacoes.push({ taskId: p.task && p.task.id, desafioAnterior: p.desafioAnterior })
      return 'a causa apontada na volta ' + investigacoes.length
    case 'desafio': {
      desafios.push({ taskId: p.task && p.task.id, causa: p.causa })
      const referenda = (CFG.desafioReferendaNaVolta || 0) === desafios.length
      return { procede: referenda, motivo: referenda ? '' : 'a causa nao explica o fato X',
               // o ESCOPO sai do par em acordo, nunca do motor: 'repositorio' e o que
               // dispara o destravador (F23.9). O cenario escolhe.
               escopo: CFG.desafioEscopo || 'tarefa',
               anchor: 'ultima linha da causa que desafiei' }
    }
    // A conferencia final da parada (autopsia 2026-08-09). Sem este caso o papel volta
    // {} sem ancora, o julga recusa duas vezes, e a trava passaria pela bancada sempre
    // no caminho do "nao respondeu" — exercitada pela metade.
    case 'confirm': {
      const v = { complete: !(CFG.confirmGaps || []).length, cohesive: true,
                  gaps: CFG.confirmGaps || [], missingTasks: [] }
      v.anchor = 'ultima linha do que confirmei'
      return v
    }
    // O ciclo por bloco (decisao do dono, 2026-08-09): o revisor por tarefa e o do
    // bloco aprovam por default — o cenario reprova por id (CFG.revTarefaReprova /
    // CFG.revBlocoGaps) para exercitar a retencao no grao novo.
    case 'revTarefa':
      return { aprova: !(CFG.revTarefaReprova || []).includes(p.entrega && p.entrega.task_id),
               gaps: (CFG.revTarefaReprova || []).includes(p.entrega && p.entrega.task_id)
                     ? [{ kind: 'spec', severity: 'P1', problem: 'o pronto nao foi cumprido' }] : [],
               anchor: 'ultima linha da entrega que revisei' }
    case 'revBloco': {
      const v = { complete: true, cohesive: true, gaps: CFG.revBlocoGaps || [],
                  missingTasks: [], lawMark: null }
      v.anchor = 'ultima linha do bloco que revisei'
      return v
    }
    case 'revDoc':
      return { ok: true, consertados: [], gaps: CFG.revDocGaps || [],
               anchor: 'ultima linha da doc que reli' }
    default:          return {}
  }
}

const corpo = CORPO.replace(/^export const meta = \{[\s\S]*?\n\}\n/m, '')
const motor = new Function('args', 'agent', 'phase', 'log', 'budget', 'parallel',
                           'return (async () => {' + PRELUDE + corpo + '})()')
motor(CFG.args, agent, phase, log, budget, parallel).then(saida => {
  fs.writeFileSync(CFG.out, JSON.stringify({ saida, chamadas, checkpoints, docs, agentes, executados, vereditos, auditorias, narrado, investigacoes, desafios, destraves }, null, 2))
}).catch(e => { console.error('MOTOR ESTOUROU: ' + (e && e.stack || e)); process.exit(3) })
"""


def roda_motor(tmp, texto, plan_dir, tick_cmd, plan_path, token_budget=None,
               gasto_por_chamada=0, gasto_cai_em=None, gasto_base=0, max_rounds=2, review_complete=True,
               trabalho_vivo=False, rodadas_mudas_max=None,
               checkpoint_cmd="", escreve_no_disco=False,
               suite_verde=True, suite_falhando=None, largada_falhando=None,
               reserva_recusada=False,
               replay_cache=False, gaps=None,
               espera_dono=None,
               bloco_max=None, leva_max=None,
               review_sem_ancora=None, alegacao_impossivel=None, auditor_derruba=False,
               auditor_motivo="", auditor_nao_tentou=None, doc_falso=None,
               confirm_gaps=None, espera_todos=False, desafio_referenda_na_volta=0,
               rev_tarefa_reprova=None, rev_bloco_gaps=None, rev_doc_gaps=None,
               desafio_escopo=None, destrava_ok=False, porta_fecha_so_na_remedida=False):
    """Executa o esqueleto do SKILL.md com os agentes de mentira. Devolve
    {saida, chamadas, agentes} ou levanta AssertionError com o motivo."""
    corpo = os.path.join(tmp, "motor.js")
    # newline="\n": no Windows a escrita em modo texto vira CRLF, e o recorte do
    # `export const meta` no harness casa `\n}\n` — com \r\n ele nao casa, o `export`
    # sobrevive dentro do new Function e o node morre com "Unexpected token 'export'".
    with open(corpo, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(esqueleto(texto))
    harness = os.path.join(tmp, "harness.js")
    with open(harness, "w", encoding="utf-8") as fh:
        fh.write(HARNESS)
    out = os.path.join(tmp, "saida.json")
    tarefas = [{"id": i["id"], "desc": i["desc"], "requisito": i["requisito"],
                "pronto": i["pronto"], "files": ["%s.txt" % i["id"]],
                "parallelizable": True, "dependsOn": [], "done": False}
               for i in PLANO["phases"][0]["items"]]
    resultados = dict(RESULTADOS)
    if espera_todos:
        # Onda esteril (autopsia 2026-08-09): TODAS as tarefas esperam o dono, entao a
        # fila executavel nasce vazia — que e exatamente o estado das ondas 4 e 5 da
        # corrida real, onde o motor pagou a decomposicao para nao despachar ninguem.
        for tf in tarefas:
            tf["esperaDono"] = "decisao do dono pendente"
        resultados = {}
    if espera_dono:
        # F9.56: F1.3 passa a ESPERAR o dono. Ele sai da fila corretamente, mas volta
        # em `missingTasks` do revisor — e era ai que reincidia e virava diagnostico
        # caro. O cenario existe pra provar que agora nao vira.
        for tf in tarefas:
            if tf["id"] == "F1.3":
                tf["esperaDono"] = espera_dono
        resultados.pop("F1.3", None)
    if alegacao_impossivel:
        # F1.3 (o passo que nao sai) passa a voltar ALEGANDO impossivel, com a lista do
        # que havia a mao — que e o insumo da lente invertida do auditor.
        resultados["F1.3"] = dict(RESULTADOS["F1.3"], impossivel=alegacao_impossivel,
                                  ferramentas=FERRAMENTAS_A_MAO)
    if replay_cache:
        # O plantio: F1.1 e F1.2 voltam do cache uma segunda vez (mesmo `task_id`, mesmo
        # veredito), e a devolucao do decompositor entra na fila como uma linha a mais,
        # sem `task_id`. Nada disso e passo novo — e nenhuma das duas pode contar.
        tarefas = tarefas + [dict(t) for t in tarefas if t["id"] in ("F1.1", "F1.2")] + [
            {"id": REPLAY_DECOMP_ID, "desc": "linha da decomposicao repetida do cache",
             "requisito": "S-43", "pronto": "nao e passo", "files": [],
             "parallelizable": True, "dependsOn": [], "done": False}]
        resultados[REPLAY_DECOMP_ID] = REPLAY_DECOMP_RESULT
    cfg = {
        "tickCmd": tick_cmd,
        "checkpointCmd": checkpoint_cmd,
        "escreveNoDisco": escreve_no_disco,
        "docFalso": doc_falso,
        "suiteVerde": suite_verde,
        "suiteFalhando": suite_falhando or [],
        "largadaFalhando": largada_falhando or [],
        "reservaRecusada": reserva_recusada,
        "shell": bash_posix() or "/bin/sh",
        "pluginSkills": os.path.abspath(os.path.join(AQUI, "..")),
        "raiz": tmp,
        "planoId": PLANO["id"],
        "out": out,
        "trabalhoVivo": trabalho_vivo,
        "gastoPorChamada": gasto_por_chamada,
        "gastoCaiEm": gasto_cai_em,
        "gastoBase": gasto_base,
        "reviewComplete": review_complete,
        "gaps": gaps or [],
        "confirmGaps": confirm_gaps or [],
        "desafioReferendaNaVolta": desafio_referenda_na_volta,
        "desafioEscopo": desafio_escopo,
        "destravaOk": destrava_ok,
        "portaFechaSoNaRemedida": porta_fecha_so_na_remedida,
        "reviewSemAncora": review_sem_ancora,
        "auditorDerruba": auditor_derruba,
        "auditorMotivo": auditor_motivo,
        "auditorNaoTentou": auditor_nao_tentou or [],
        "revTarefaReprova": rev_tarefa_reprova or [],
        "revBlocoGaps": rev_bloco_gaps or [],
        "revDocGaps": rev_doc_gaps or [],
        "results": resultados,
        "tasks": tarefas,
        "args": {"planPath": plan_path, "planText": "plano de bancada", "maxRounds": max_rounds,
                 "tokenBudget": token_budget, "blocoMax": bloco_max,
                 "rodadasMudasMax": rodadas_mudas_max, "levaMax": leva_max,
                 "severityFloor": "P1", "repoRoot": tmp, "churnThreshold": 2,
                 "hasQaLoop": True, "sessionId": "sessao-bancada", "motorId": "motor-bancada",
                 "model": "opus",
                 "tiers": {k: {"effort": "medium"} for k in
                           ("decompose", "coordinate", "executor", "mechanical",
                            "diagnose", "finalize")}},
    }
    cfg_path = os.path.join(tmp, "cfg.json")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)
    proc = subprocess.run(["node", harness, cfg_path, corpo],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=tmp, stdin=subprocess.DEVNULL, start_new_session=True)
    if proc.returncode != 0:
        raise AssertionError("o motor nao rodou: %s" % (proc.stderr.strip() or proc.stdout.strip()))
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


def cria_plano(plan_dir):
    entrada = os.path.join(plan_dir, "_in.json")
    with open(entrada, "w", encoding="utf-8") as fh:
        json.dump(PLANO, fh)
    proc = subprocess.run([sys.executable, PLAN_STATE, "--dir", plan_dir, "init", "--file", entrada],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    if proc.returncode != 0:
        raise AssertionError("o plano de bancada nao foi criado: %s" % proc.stderr.strip())
    return os.path.join(plan_dir, "%s.plan.json" % PLANO["id"])


def bancada(texto, tick_cmd, **kw):
    """Uma rodada de bancada em diretorio proprio, com plano proprio. Cada cenario tem
    o seu — dois cenarios no mesmo plano marcariam passo ja marcado e o `tick` recusaria,
    misturando falha de registro com o que o cenario quer medir. Devolve None se o motor
    nao rodou (e o motivo ja saiu como check reprovado)."""
    tmp = tempfile.mkdtemp(prefix="sprint-bancada-")
    try:
        plan_dir = os.path.join(tmp, ".claude", "plans")
        os.makedirs(plan_dir)
        plan_path = cria_plano(plan_dir)
        try:
            return roda_motor(tmp, texto, plan_dir, tick_cmd, plan_path, **kw)
        except AssertionError as exc:
            check("o motor rodou de ponta a ponta (%s)" % exc, False)
            return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def bancada_git(texto, tick_cmd, ck_cmd, sujeira_no_indice=None, **kw):
    """Uma rodada de bancada dentro de um repositorio git de verdade, com o papel de
    salvamento rodando o comando REAL da skill. Devolve o que rodou MAIS o que sobrou no
    repositorio depois (historico, arvore versionada, o que ficou solto) — que e o unico
    jeito de perguntar se a onda virou ponto de salvamento ou nao. None se o motor nao
    rodou (e o motivo ja saiu como check reprovado)."""
    repo = tempfile.mkdtemp(prefix="sprint-bancada-git-")
    try:
        def git(*args):
            return subprocess.run(["git", "-C", repo] + list(args),
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
        git("init", "-q")
        git("config", "user.email", "bancada@exemplo.invalido")
        git("config", "user.name", "bancada")
        git("commit", "-q", "--allow-empty", "-m", "base")
        plan_dir_g = os.path.join(repo, ".claude", "plans")
        os.makedirs(plan_dir_g)
        plan_path_g = cria_plano(plan_dir_g)
        # Trabalho de OUTRA sessao, ja no indice antes de a onda comecar. O `commit` da
        # onda nao pode carrega-lo: sem pathspec no commit, o indice inteiro entra.
        if sujeira_no_indice:
            with open(os.path.join(repo, sujeira_no_indice), "w", encoding="utf-8") as fh:
                fh.write("trabalho de outra sessao\n")
            git("add", "--", sujeira_no_indice)
        try:
            rodada = roda_motor(repo, texto, plan_dir_g, tick_cmd, plan_path_g,
                                checkpoint_cmd=ck_cmd, escreve_no_disco=True, **kw)
        except AssertionError as exc:
            check("o motor rodou de ponta a ponta (%s)" % exc, False)
            return None
        rodada["log"] = git("log", "--oneline").stdout
        rodada["versionados"] = git("ls-tree", "-r", "--name-only", "HEAD").stdout.split()
        rodada["solto"] = git("status", "--porcelain").stdout
        rodada["commitado"] = git("show", "--stat", "--name-only", "--format=",
                                  "HEAD").stdout.split()
        if sujeira_no_indice:
            rodada["indice"] = git("diff", "--cached", "--name-only").stdout.split()
            with open(os.path.join(repo, sujeira_no_indice), encoding="utf-8") as fh:
                rodada["sujeira"] = fh.read()
        return rodada
    finally:
        shutil.rmtree(repo, ignore_errors=True)


# ── a bancada do motor de REVISAO (/qa-loop) ────────────────────────────────
# O motor de implementacao acima tem o laco decompoe->executa->revisa. O de revisao tem
# o dele — revisa->planeja->conserta->REVISA DE NOVO —, e ate 2026-08-09 ninguem o havia
# EXECUTADO: a prosa dizia que a rodada 2+ reabre sobre os arquivos tocados, e nada
# provava que reabria. Aqui o esqueleto do SKILL.md do /qa-loop roda em Node com os
# agentes de mentira, e o que se afere e o que o revisor RECEBEU em cada volta.
QA_SKILL_MD = os.path.join(AQUI, "..", "skills", "qa-loop", "SKILL.md")

QA_HARNESS = r"""
const fs = require('fs')
const CFG = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const CORPO = fs.readFileSync(process.argv[3], 'utf8')

const PRELUDE = `
const FINDINGS={}, PLAN={}, EXEC_RESULT={}, DESAFIO={};
const mk = n => (p => Object.assign({ __p: n }, p));
const reviewPrompt=mk('review'), planPrompt=mk('plan'), execPrompt=mk('exec'),
      diagnosePrompt=mk('diag'), desafioCausaPrompt=mk('desafio');
const isAccepted = (f, limites) => (limites || []).some(l => l.id === f.id);
const tallyBySev = fs => fs.length;
const revertAndMaybeRedo = async (fix) => { globalThis.__revertidos.push(fix.id) };
`

globalThis.__revertidos = []
const revisoes = []   // o que o REVISOR recebeu em cada volta (round + escopo)
const consertados = []
const agentes = []
const phase = () => {}
const log = () => {}

async function agent(p, opts) {
  if (p.__p === 'review' && p.confirming) {
    // A conferencia dedicada. Ela so acha algo na PRIMEIRA vez (CFG.confirm): repetir o
    // mesmo achado em toda conferencia deixaria o laco girando ate o teto, e o que se
    // quer medir e que UM achado dela reabre o laco.
    agentes.push('confirm')
    const primeira = agentes.filter(a => a === 'confirm').length === 1
    return (primeira && CFG.confirm) || { complete: true, findings: [] }
  }
  agentes.push(p.__p)
  const daVolta = CFG.rodadas[(p.round || 1) - 1] || { findings: [] }
  switch (p.__p) {
    case 'review':
      revisoes.push({ round: p.round, scope: p.scope })
      return { complete: true, findings: daVolta.findings }
    case 'plan':
      // Roteia pro conserto o que o REVISOR daquela volta devolveu — inclusive o que o
      // motor concatenou da conferencia. Ler do cenario aqui esconderia esse caminho.
      return { bucket1: (p.review.findings || []).map(f => ({ id: f.id, file: f.file, fn: f.fn })),
               alerts: [], proposedLimits: [] }
    case 'exec':
      consertados.push(p.fix.id)
      return { fix_id: p.fix.id, files_touched: [p.fix.file],
               suiteRegressed: CFG.regride === p.fix.id, summary: 'consertei ' + p.fix.id }
    default:
      return {}
  }
}

const corpo = CORPO.replace(/^export const meta = \{[\s\S]*?\n\}\n/m, '')
const motor = new Function('args', 'agent', 'phase', 'log',
                           'return (async () => {' + PRELUDE + corpo + '})()')
motor(CFG.args, agent, phase, log).then(saida => {
  fs.writeFileSync(CFG.out, JSON.stringify(
    { saida, revisoes, consertados, agentes, revertidos: globalThis.__revertidos }, null, 2))
}).catch(e => { console.error('MOTOR ESTOUROU: ' + (e && e.stack || e)); process.exit(3) })
"""


def bancada_qa(rodadas, max_rounds=6, confirm=None, regride=None):
    """Executa o esqueleto do /qa-loop com os agentes de mentira. `rodadas` diz o que o
    revisor acha em cada volta. Devolve {saida, revisoes, consertados, agentes} ou None
    (e o motivo ja saiu como check reprovado)."""
    tmp = tempfile.mkdtemp(prefix="qa-bancada-")
    try:
        corpo = os.path.join(tmp, "motor.js")
        with open(corpo, "w", encoding="utf-8", newline="\n") as fh:  # LF: ver roda_motor
            fh.write(esqueleto(open(QA_SKILL_MD, encoding="utf-8").read()))
        harness = os.path.join(tmp, "harness.js")
        with open(harness, "w", encoding="utf-8") as fh:
            fh.write(QA_HARNESS)
        out = os.path.join(tmp, "saida.json")
        cfg = {
            "out": out,
            "rodadas": rodadas,
            "confirm": confirm,
            "regride": regride,
            "args": {"target": "bancada", "severityFloor": "P1", "maxRounds": max_rounds,
                     "churnThreshold": 2, "acceptedLimits": [], "invariants": [],
                     "model": "opus",
                     "tiers": {k: {"effort": "medium"} for k in
                               ("decompose", "coordinate", "executor", "mechanical",
                                "diagnose", "finalize")}},
        }
        cfg_path = os.path.join(tmp, "cfg.json")
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        proc = subprocess.run(["node", harness, cfg_path, corpo], capture_output=True,
                              text=True, encoding="utf-8", errors="replace", cwd=tmp, stdin=subprocess.DEVNULL, start_new_session=True)
        if proc.returncode != 0:
            check("o motor de revisao rodou de ponta a ponta (%s)"
                  % (proc.stderr.strip() or proc.stdout.strip()), False)
            return None
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def estado(plan_path):
    with open(plan_path, encoding="utf-8") as fh:
        plano = json.load(fh)
    return {i["id"]: i for ph in plano["phases"] for i in ph["items"]}


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()

    print("F9.10 — a skill nomeia o comando que marca o plano")
    tick_cmd = comando_de_tique(texto)
    check("o comando de tique esta escrito na skill", bool(tick_cmd))
    check("a prova que ele grava e a do EXECUTOR",
          "`summary` + `files_touched`" in texto and "nunca redigida por quem marca" in texto)

    if not shutil.which("node"):
        check("Node esta na maquina (sem ele a bancada nao roda)", False)
        return 1
    if not tick_cmd:
        return 1

    tmp = tempfile.mkdtemp(prefix="sprint-bancada-")
    try:
        plan_dir = os.path.join(tmp, ".claude", "plans")
        os.makedirs(plan_dir)
        plan_path = cria_plano(plan_dir)

        print("F9.10 — o motor roda em plano de bancada e o plano sai marcado")
        try:
            rodada = roda_motor(tmp, texto, plan_dir, tick_cmd, plan_path)
        except AssertionError as exc:
            check("o motor rodou de ponta a ponta (%s)" % exc, False)
            return 1
        saida, chamadas = rodada["saida"], rodada["chamadas"]
        check("o motor fechou a rodada", saida.get("built") is True)

        itens = estado(plan_path)
        check("F1.1 saiu marcado sem ninguem marcar a mao", itens["F1.1"]["status"] == "done")
        check("F1.2 saiu marcado sem ninguem marcar a mao", itens["F1.2"]["status"] == "done")
        check("a prova gravada e a do executor (o resumo dele)",
              "escrevi o arquivo" in (itens["F1.1"].get("evidence") or ""))
        check("a prova gravada traz os arquivos que o executor tocou",
              "b.sh" in (itens["F1.2"].get("evidence") or "")
              and "c.sh" in (itens["F1.2"].get("evidence") or ""))
        check("quem NAO devolveu done continua aberto",
              itens["F1.3"].get("status") != "done" and not itens["F1.3"].get("evidence"))
        check("quem estourou o teto (espera) continua aberto",
              itens["F1.4"].get("status") != "done" and not itens["F1.4"].get("evidence"))
        check("nenhuma marcacao a mais foi disparada",
              sorted(c["taskId"] for c in chamadas) == ["F1.1", "F1.2"])

        print("F9.10 — plano que nao e arquivo nao e marcado por ninguem")
        # Mesma rodada, com planPath de plano solto: o guarda do script tem que calar o
        # papel de marcacao inteiro (senao ele rodaria o tick contra um plano inexistente).
        tmp2 = tempfile.mkdtemp(prefix="sprint-bancada-solto-")
        try:
            os.makedirs(os.path.join(tmp2, ".claude", "plans"))
            rodada2 = roda_motor(tmp2, texto, plan_dir, tick_cmd,
                                 os.path.join(tmp2, "plano.md"))
            check("com plano fora do arquivo, nada e marcado", rodada2["chamadas"] == [])
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("F9.12 — sem teto, o motor roda ate a trava de voltas (o controle)")
    # O controle existe pra provar que quem desligou o motor na rodada seguinte foi o
    # TETO, e nao a obra ter ficado pronta ou a trava de voltas ter chegado antes.
    solto = bancada(texto, tick_cmd, token_budget=None, gasto_por_chamada=400,
                    max_rounds=3, review_complete=False)
    if solto is None:
        return 1
    check("sem teto, o motor gasta as 3 voltas inteiras", len(solto["saida"]["rounds"]) == 3)
    check("sem teto, quem parou foi a trava de voltas",
          solto["saida"]["stopReason"] == "max-rounds")
    check("sem teto, o gasto e alto e ninguem reclama",
          solto["saida"]["gasto"] > 400 and not any(
              "disjuntor" in (b.get("what") or "") for b in solto["saida"]["blockers"]))

    # ── O GASTO SÓ SOBE (2026-08-15) ───────────────────────────────────────────
    # `budget.spent()` conta o turno inteiro e PODE CAIR no meio da corrida: uma de 6h
    # devolveu `gasto: -831562`. Número negativo não é curiosidade de relatório — é o
    # disjuntor DESARMADO, porque `gasto >= tokenBudget` nunca é verdade com negativo.
    # Aqui o contador cai no meio de propósito, e o teto tem que armar do mesmo jeito.
    print("F9.12 — contador que ANDA PARA TRÁS não desarma o disjuntor")
    caiu = bancada(texto, tick_cmd, token_budget=1000, gasto_por_chamada=400,
                   gasto_base=900000, gasto_cai_em=2, max_rounds=3,
                   review_complete=False)
    if caiu is None:
        return 1
    check("o gasto relatado nunca é negativo", caiu["saida"]["gasto"] >= 0)
    check("com o contador caindo, o disjuntor ainda desliga a missão",
          caiu["saida"]["stopReason"] == "orcamento")

    print("F9.12 — o motor estoura o teto, se desliga sozinho e diz quanto gastou")
    # Mesma missao, mesmo numero de voltas permitido, mesma queima por agente. A UNICA
    # diferenca e o teto — entao toda diferenca de desfecho abaixo e obra do disjuntor.
    est = bancada(texto, tick_cmd, token_budget=1000, gasto_por_chamada=400,
                  max_rounds=3, review_complete=False)
    if est is None:
        return 1
    saida3 = est["saida"]
    check("o motor se desligou antes de gastar as voltas", len(saida3["rounds"]) < 3)
    check("o motivo da parada e o orcamento", saida3["stopReason"] == "orcamento")
    check("ele relata o quanto gastou, em numero", saida3["gasto"] >= 1000)
    disjuntor = [b for b in saida3["blockers"] if "disjuntor" in (b.get("what") or "")]
    check("o desligamento vira Bloqueio, nao silencio", len(disjuntor) == 1)
    # O numero do Bloqueio e o gasto NO INSTANTE em que o disjuntor abriu; o total
    # devolvido carrega ainda o `encerra:barra`, o unico papel que roda depois dele
    # (apagar o sinal da barra e soltar a reserva alcanca TODO caminho de saida).
    m_gasto = re.search(r"gastou (\d+) de 1000 tokens.*rodada 1",
                        disjuntor[0]["what"]) if disjuntor else None
    check("o Bloqueio diz o gasto, o teto e a rodada",
          bool(m_gasto) and 1000 <= int(m_gasto.group(1)) <= saida3["gasto"])
    check("ele nao declara obra construida ao se desligar", saida3["built"] is False)
    # A prova de que o desligamento e EFETIVO: nenhum agente foi disparado depois dele.
    # Trava que grava o motivo e seguisse gastando seria relatorio, nao disjuntor.
    check("nenhum decompositor foi disparado numa segunda volta",
          est["agentes"].count("decompose") == 1)
    check("o disjuntor cortou agente: gastou menos que a rodada sem teto",
          len(est["agentes"]) < len(solto["agentes"]))

    # ── F9.13 + F9.24 ────────────────────────────────────────────────────────────
    # O vigia media TEMPO ate 2026-08-10, e a hora vinha do agente da suite — que numa
    # corrida real devolveu `1`, a conta deu 56 anos de silencio e a missao morreu no
    # minuto seguinte a uma suite verde de 374 testes. Agora ele mede AVANCO: rodada que
    # nao fecha bloco verde nem marca passo e uma rodada muda. Os tres cenarios abaixo
    # mudam UMA coisa cada um em cima da mesma missao — assim a diferenca de desfecho so
    # pode ser obra da condicao que mudou. `rodadasMudasMax=1` derruba na primeira muda;
    # o controle roda com o default (3), que a onda 1 verde ja adia para alem do teto de
    # voltas — e por isso quem para o controle e a trava de voltas, nao o vigia.
    print("F9.13 — com a onda avancando, o vigia nao encosta no motor (o controle)")
    fresco = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                     trabalho_vivo=False)
    if fresco is None:
        return 1
    check("onda que fecha bloco verde: o motor gasta as 3 voltas inteiras",
          len(fresco["saida"]["rounds"]) == 3)
    check("onda que fecha bloco verde: quem parou foi a trava de voltas",
          fresco["saida"]["stopReason"] == "max-rounds")

    print("F9.24 — muda, mas COM trabalho vivo, o vigia nao derruba (demora nao e travamento)")
    # A metade que separa demora de travamento: mesma onda esteril do cenario seguinte,
    # so que a suite diz que ha trabalho rodando. Sem esta metade, o vigia mataria
    # agente no meio de uma suite longa — que foi o motivo de a condicao ser dupla.
    vivo = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                   rodadas_mudas_max=1, suite_verde=False, trabalho_vivo=True)
    if vivo is None:
        return 1
    check("com trabalho vivo, o vigia nao acende o sinal",
          vivo["saida"]["stopReason"] != "vigia")
    check("com trabalho vivo, nenhum Bloqueio do vigia e escrito",
          not any("vigia" in (b.get("what") or "") for b in vivo["saida"]["blockers"]))

    print("F9.13 — rodada muda alem do limite E sem trabalho vivo: o vigia derruba")
    travado = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                      rodadas_mudas_max=1, suite_verde=False, trabalho_vivo=False)
    if travado is None:
        return 1
    saida4 = travado["saida"]
    check("o motor parou antes de gastar as voltas", len(saida4["rounds"]) < 3)
    check("o motivo da parada e o vigia", saida4["stopReason"] == "vigia")
    vig = [b for b in saida4["blockers"] if "vigia" in (b.get("what") or "")]
    check("a derrubada vira Bloqueio, nao silencio", len(vig) == 1)
    check("o Bloqueio diz quantas rodadas passaram sem nada sair",
          bool(vig) and "1 rodada fechou sem nenhum bloco verde" in vig[0]["what"])
    check("o Bloqueio chama a coisa pelo nome: travamento, nao demora",
          bool(vig) and "travamento, não demora" in (vig[0].get("whyNeedsYou") or ""))
    check("ele nao declara obra construida ao ser derrubado", saida4["built"] is False)
    # A prova de que a derrubada e EFETIVA: nenhuma volta seguinte foi aberta. Vigia que
    # gravasse o motivo e deixasse o motor seguir seria relatorio, nao freio.
    check("nenhum decompositor foi disparado numa segunda volta",
          travado["agentes"].count("decompose") == 1)
    check("o vigia cortou agente: menos agentes que a rodada que avancou",
          len(travado["agentes"]) < len(fresco["agentes"]))

    # ── F9.14 ────────────────────────────────────────────────────────────────────
    # Interrupcao de verdade: a mesma missao do cenario do vigia, so que agora o
    # executor DEIXA ARQUIVO no disco e o papel de salvamento roda o comando REAL da
    # skill num repositorio git de bancada. O motor e derrubado na rodada 1 — o que se
    # afere e o que sobrou depois dele morrer: a onda fechada tem que estar no
    # HISTORICO, nao solta na arvore.
    print("F9.14 — motor interrompido no meio deixa a onda fechada no historico")
    ck_cmd = comando_de_checkpoint(texto)
    check("o comando que salva a onda esta escrito na skill", bool(ck_cmd))
    if not ck_cmd:
        return 1
    if not shutil.which("git"):
        check("git esta na maquina (sem ele o historico nao existe)", False)
        return 1

    # A interrupcao vem do DISJUNTOR: a onda 1 fecha verde (e por isso o vigia por
    # avanco nao a derrubaria), e o teto de gasto corta a missao logo depois dela.
    interrompido = bancada_git(texto, tick_cmd, ck_cmd, max_rounds=3, review_complete=False,
                               token_budget=1, gasto_por_chamada=1,
                               sujeira_no_indice="alheio.txt")
    if interrompido is None:
        return 1

    saida5 = interrompido["saida"]
    check("o motor foi mesmo interrompido no meio",
          saida5["stopReason"] == "orcamento" and len(saida5["rounds"]) < 3)
    check("a onda que fechou verde virou ponto de salvamento",
          saida5["rounds"][0].get("checkpoint") is True)
    check("o salvamento aconteceu na onda 1, uma vez so",
          [c["round"] for c in interrompido["checkpoints"]] == [1])

    check("o historico ganhou a onda, com o numero dela", "onda 1" in interrompido["log"])
    check("a obra dos executores esta NO HISTORICO",
          "a.py" in interrompido["versionados"] and "b.sh" in interrompido["versionados"])
    check("o plano marcado tambem entrou no historico",
          any(v.endswith("%s.plan.json" % PLANO["id"]) for v in interrompido["versionados"]))
    check("nada da onda fechada ficou solto no disco",
          "a.py" not in interrompido["solto"] and "b.sh" not in interrompido["solto"])
    # F9.60 — o commit da onda e NOMEADO: `git show --stat` lista so o que o bloco tocou.
    # Com `add -A` a arvore inteira entrava, e o arquivo de quem NAO foi aprovado (F1.4,
    # que estourou o teto) vinha junto — trabalho de fora gravado como se fosse da onda.
    check("o commit da onda lista so os arquivos que ela tocou",
          sorted(interrompido["commitado"]) == sorted(
              ["a.py", "b.sh", "c.sh", ".claude/plans/%s.plan.json" % PLANO["id"]]))
    check("arquivo de fora da onda nao entra no commit (F1.4 estourou o teto)",
          "d.py" not in interrompido["commitado"] and "d.py" in interrompido["solto"])
    # F9.60 — o vazamento pelo INDICE: outra sessao stageou `alheio.txt` antes da onda.
    # `git commit` sem pathspec grava o indice inteiro, e o alheio entrava no commit da
    # onda mesmo com o `add` nomeado.
    check("arquivo que outra sessao apenas stageou nao entra no commit da onda",
          "alheio.txt" not in interrompido["commitado"])
    check("o que era de fora segue staged, para a sessao dona dele",
          "alheio.txt" in interrompido["indice"])
    check("e segue intacto no disco",
          interrompido["sujeira"] == "trabalho de outra sessao\n")
    # O que NAO fechou nao pode ser inventado no historico: F1.3 devolveu
    # `done: false` e o executor nem escreveu o arquivo dele.
    check("o que nao fechou nao aparece no historico",
          "F1.3.txt" not in interrompido["versionados"])

    # ── F9.15 ────────────────────────────────────────────────────────────────────
    # Mesma missao do cenario acima, no mesmo repositorio de bancada, com a MESMA
    # interrupcao. A unica coisa que muda e a COR da suite — entao toda diferenca de
    # desfecho abaixo e obra da recusa de salvar onda vermelha, e nao de outra trava.
    print("F9.15 — onda com suite vermelha nao vira ponto de salvamento")
    vermelha = bancada_git(texto, tick_cmd, ck_cmd, max_rounds=3, review_complete=False,
                           token_budget=1, gasto_por_chamada=1,
                           suite_verde=False,
                           suite_falhando=["test_plan_state.py", "test_andamento.py"])
    if vermelha is None:
        return 1

    saida6 = vermelha["saida"]
    check("a onda vermelha NAO foi marcada como ponto de salvamento",
          saida6["rounds"][0].get("checkpoint") is not True)
    # A prova de que a recusa e EFETIVA: o comando de salvamento nem chegou a rodar.
    # Marcar `checkpoint: false` e commitar assim mesmo seria o carimbo sem a recusa.
    check("nenhum salvamento foi disparado na onda vermelha", vermelha["checkpoints"] == [])
    check("o historico NAO ganhou a onda vermelha", "onda 1" not in vermelha["log"])
    check("a obra da onda vermelha ficou solta, fora do historico",
          "a.py" in vermelha["solto"] and "a.py" not in vermelha["versionados"])

    quebra = [b for b in saida6["blockers"] if "suíte quebrou" in (b.get("what") or "")]
    check("a onda vermelha vira Bloqueio, nao silencio", len(quebra) == 1)
    check("o Bloqueio diz QUAIS suites quebraram, pelo nome",
          bool(quebra) and "test_plan_state.py" in quebra[0]["what"]
          and "test_andamento.py" in quebra[0]["what"])
    check("o Bloqueio diz em que rodada quebrou",
          bool(quebra) and "rodada 1" in quebra[0]["what"])
    check("o Bloqueio manda consertar antes de seguir",
          bool(quebra) and "não vira ponto de salvamento" in (quebra[0].get("whyNeedsYou") or ""))

    # ── F9.32 ────────────────────────────────────────────────────────────────────
    # O checkpoint gravava so CODIGO. Quem executasse a onda seguinte leria a doc do
    # repo de ANTES. Nos MESMOS dois cenarios acima (mesma missao, mesma interrupcao,
    # so a cor da suite muda) se afere agora o par commit+doc: a onda verde produz os
    # dois, nessa ordem; a vermelha nao produz nenhum.
    print("F9.32 — onda verde fecha com commit E doc; onda vermelha, com nenhum dos dois")
    # O check pedia o nome COMPLETO da skill escrito na instrução — e foi exatamente
    # isso que quebrou: a skill mudou de plugin no F14.2, o nome ficou apontando pro
    # antigo, e quatro ondas fecharam verdes sem produzir doc nenhuma. Um teste que
    # exige o nome cravado é um teste que EXIGE o defeito. Agora ele cobra o contrário:
    # que o nome seja descoberto, e que o nome morto não esteja em lugar nenhum.
    check("a skill manda DESCOBRIR o nome da skill de doc, não o escreve à mão",
          "docTouchPrompt" in texto and "resolve-skill.sh" in texto)
    # A busca é pela INSTRUÇÃO de invocar, não pela palavra: a skill conta a história do
    # defeito em prosa, e o nome morto aparece lá de propósito. O que não pode existir é
    # um `skill: "<algo>"` mandando invocar um nome cravado.
    import re as _re
    cravados = _re.findall(r'skill:\s*"([a-z0-9-]+:[a-z0-9-]+)"', texto)
    check("nenhuma invocação usa nome de skill cravado (achados: %s)" % (cravados or "-"),
          not cravados)

    check("a onda verde re-projetou a doc, uma vez so",
          [d["round"] for d in interrompido["docs"]] == [1])
    # A doc pedida e a dos arquivos que ESTA onda tocou — doc do repo inteiro seria o
    # FULL, e doc de arquivo que ninguem tocou e gasto puro.
    tocados = sorted(interrompido["docs"][0]["files"]) if interrompido["docs"] else []
    check("a doc pedida e a dos arquivos que a onda tocou",
          tocados == ["a.py", "b.sh", "c.sh"])
    check("arquivo de quem estourou o teto nao entra (nao e obra fechada)",
          "d.py" not in tocados)
    # A ORDEM e o ponto: commit primeiro, doc depois. Doc antes do commit deixaria o
    # trabalho fora do historico se o touch estourasse.
    ag = interrompido["agentes"]
    check("o commit veio ANTES da doc, nao depois",
          "checkpoint" in ag and "docTouch" in ag
          and ag.index("checkpoint") < ag.index("docTouch"))

    check("a onda vermelha nao re-projetou doc nenhuma", vermelha["docs"] == [])
    check("na onda vermelha nao houve nem commit nem doc",
          vermelha["checkpoints"] == [] and "docTouch" not in vermelha["agentes"])

    # ── S-112 ────────────────────────────────────────────────────────────────────
    # O papel que INVOCA SKILL nao devolvia nada: papel mudo, papel que invocou skill
    # quebrada e papel que MENTE ter feito chegavam iguais ao motor. Agora ele devolve os
    # caminhos que tocou, conferidos no disco — e a onda registra o que ele CONFIRMOU.
    print("S-112 — o papel que invoca skill devolve os caminhos que tocou")
    check("a doc devolvida pelo papel e a que o disco confirma",
          bool(interrompido["docs"]) and interrompido["docs"][0]["docs"] ==
          [".claude/docs/onda-1.md"])
    check("a onda registra o que o papel confirmou, nao a lista que ele recebeu",
          saida5["rounds"][0].get("doc") == [".claude/docs/onda-1.md"])
    check("papel que confirmou a doc nao vira Bloqueio",
          not [b for b in saida5["blockers"] if "não foi confirmada no disco" in (b.get("what") or "")])

    # O papel que MENTE ter feito: mesma missao, mesma onda verde — a UNICA coisa que muda
    # e o papel devolver um caminho que ninguem escreveu. O disco nao confirma, a lista
    # volta vazia, e lista vazia e Bloqueio.
    print("S-112 — papel que devolve caminho que o disco nao confirma vira Bloqueio")
    mentiu = bancada_git(texto, tick_cmd, ck_cmd, max_rounds=1,
                         doc_falso=".claude/docs/nunca-escrita.md")
    if mentiu is None:
        return 1
    saida_m = mentiu["saida"]
    check("o papel foi chamado e alegou ter re-projetado uma doc",
          bool(mentiu["docs"]) and mentiu["docs"][0]["alegados"] ==
          [".claude/docs/nunca-escrita.md"])
    check("o caminho que o disco nao confirma nao entra na lista",
          mentiu["docs"][0]["docs"] == [])
    doc_bloq = [b for b in saida_m["blockers"] if "não foi confirmada no disco" in (b.get("what") or "")]
    check("lista vazia vira Bloqueio, e nao silencio", len(doc_bloq) == 1)
    check("o Bloqueio diz em que rodada a doc nao saiu",
          bool(doc_bloq) and "rodada 1" in doc_bloq[0]["what"])
    check("o Bloqueio diz por que isso custa caro na onda seguinte",
          bool(doc_bloq) and "mapa vencido" in (doc_bloq[0].get("whyNeedsYou") or ""))
    # A mentira NAO derruba a onda: o commit ja esta feito, mesma regra do tique.
    check("a mentira do papel nao desfaz o ponto de salvamento da onda",
          saida_m["rounds"][0].get("checkpoint") is True and mentiu["checkpoints"] != [])

    # ── F9.35 ────────────────────────────────────────────────────────────────────
    # A MESMA missao da primeira rodada, com UMA coisa plantada: o replay do cache.
    # F1.1 e F1.2 voltam uma segunda vez com o mesmo veredito, e a devolucao do
    # decompositor entra como mais uma linha de resultado, sem `task_id`. A contagem
    # tem que enxergar TAREFA, nao linha.
    print("F9.35 — com replay de cache plantado, a contagem devolve tarefas distintas")
    # `bloco_max` cobre a onda inteira de proposito: o retorno por bloco (F9.57) fecharia a
    # onda no F1.3, e as linhas repetidas — que sao o plantio deste cenario — nunca sairiam.
    # O que se mede aqui e a CONTAGEM, nao o corte da onda.
    replay = bancada(texto, tick_cmd, max_rounds=1, replay_cache=True, bloco_max=99)
    if replay is None:
        return 1
    saida7 = replay["saida"]
    linhas = saida7["rounds"][0]["results"] if saida7.get("rounds") else []
    feitas_em_linha = [x for x in linhas if x.get("done")]
    # O plantio so vale se o replay realmente aconteceu: sem esta afericao, a contagem
    # certa poderia ser a de um cenario que nunca teve duplicata nenhuma.
    check("o replay foi mesmo plantado: 5 linhas de resultado fechado para 2 tarefas",
          len(feitas_em_linha) == 5)
    check("a linha da decomposicao chegou mesmo em results, sem task_id",
          any(not x.get("task_id") for x in feitas_em_linha))

    prog = saida7.get("progresso") or {}
    check("a contagem devolve o numero de tarefas distintas, nao de linhas",
          prog.get("feitos") == 2)
    check("a contagem nomeia quais passos fecharam, cada um uma vez",
          sorted(prog.get("passos") or []) == ["F1.1", "F1.2"])
    check("a linha da decomposicao nao entrou na contagem",
          REPLAY_DECOMP_ID not in (prog.get("passos") or []))
    # A telemetria conta a mesma coisa pela mesma regra: 3 tarefas distintas com
    # resultado (F1.1, F1.2, F1.3), e nao as 6 linhas que o replay produziu.
    check("a telemetria da onda conta tarefa distinta, nao linha",
          saida7["telemetry"][0]["tasks"] == 3)
    # E o efeito no disco: o passo repetido nao e marcado duas vezes.
    check("nenhum passo foi marcado duas vezes",
          sorted(c["taskId"] for c in replay["chamadas"]) == ["F1.1", "F1.2"])

    # ── S-9 ──────────────────────────────────────────────────────────────────────
    # A concepcao errada: a execucao descobriu algo que contradiz documento ja aprovado.
    # O motor promete duas coisas, e nenhuma era exercitada — o gap vira aviso "precisa
    # de voce" no relatorio, e NAO segura a obra (segurar empurraria o executor a
    # "consertar" codigo que esta certo).
    print("S-9 — gap de spec com o mesmo texto SEGURA a obra (o controle)")
    trava = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_SPEC])
    if trava is None:
        return 1
    check("com gap de spec, o motor nao declara a obra construida",
          trava["saida"]["built"] is False)
    check("com gap de spec, o executor recebe tarefa numa segunda volta",
          trava["agentes"].count("decompose") == 2)

    print("S-9 — o gap de concepcao vira aviso e NAO segura a obra")
    # Mesmo gap, mesmo texto, mesmo cenario: so o `kind` muda.
    conc = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_CONCEPCAO])
    if conc is None:
        return 1
    saida8 = conc["saida"]
    aviso = [b for b in saida8["blockers"] if "a concepção está errada" in (b.get("what") or "")]
    check("o gap de concepcao vira Bloqueio no relatorio", len(aviso) == 1)
    check("o Bloqueio repete o que a execucao contradisse, com as palavras do revisor",
          bool(aviso) and GAP_CONCEPCAO["problem"] in aviso[0]["what"])
    check("o Bloqueio sai como 'precisa de voce' e propoe reabrir a etapa",
          bool(aviso) and "correcao-pendente" in (aviso[0].get("whyNeedsYou") or "")
          and "reabra a etapa" in (aviso[0].get("whyNeedsYou") or ""))
    check("ele entra na lista de impedidos, que e a que pede acao do dono",
          any("a concepção está errada" in (b.get("what") or "")
              for b in saida8.get("impedidos") or []))
    check("o motor declara a obra construida mesmo assim", saida8["built"] is True)
    check("a onda nao foi segurada: uma volta so", len(saida8["rounds"]) == 1)
    # A regua nova (autopsia 2026-08-09): tarefa ja entregue que volta identica e PULADA,
    # entao a 2a rodada do controle nao re-executa tudo — a conta passa a ser "uma onda
    # inteira de exec no cenario de concepcao", nao "metade do controle".
    check("nenhum executor recebeu tarefa nova por causa dele",
          conc["agentes"].count("decompose") == 1
          and conc["agentes"].count("exec") == len(RESULTADOS))

    # ── S-104 ────────────────────────────────────────────────────────────────────
    # A obra contradiz o desenho aprovado. Injetada a contradicao, o gap tem que NASCER:
    # pelo eixo de constituicao ele segura a obra e devolve tarefa; e quando quem errou
    # foi o desenho, o mesmo texto vira aviso que nomeia o documento contradito.
    print("S-104 — a obra que contradiz o desenho aprovado segura a obra")
    desenho = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_DESENHO])
    if desenho is None:
        return 1
    check("com a obra contradizendo o desenho, o motor nao declara construida",
          desenho["saida"]["built"] is False)
    check("o executor recebe tarefa numa segunda volta",
          desenho["agentes"].count("decompose") == 2)

    print("S-104 — quando quem errou foi o desenho, o aviso nomeia o documento")
    desenho_erra = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_DESENHO_CONCEPCAO])
    if desenho_erra is None:
        return 1
    aviso_des = [b for b in desenho_erra["saida"]["blockers"]
                 if "a concepção está errada" in (b.get("what") or "")]
    check("o aviso nomeia o documento contradito",
          bool(aviso_des) and ".claude/docs/blueprint.md" in aviso_des[0]["what"])
    check("e ele nao segura a obra", desenho_erra["saida"]["built"] is True)

    # ── F9.16 · S-24 ─────────────────────────────────────────────────────────────
    # O juiz prova que leu a coisa inteira: veredito sem a ancora do fim e RECUSADO e o
    # papel roda de novo. Dois cenarios, com o mesmo controle: com ancora (o caminho
    # normal, uma chamada so) e sem ancora (recusa + re-rodada).
    print("F9.16 — veredito COM a ancora passa de primeira (o controle)")
    com_ancora = bancada(texto, tick_cmd, max_rounds=1)
    if com_ancora is None:
        return 1
    check("com a ancora, o revisor e chamado uma vez so",
          com_ancora["agentes"].count("review") == 1)
    check("com a ancora, nenhuma chamada veio marcada como recusa",
          com_ancora["vereditos"] == [False])
    check("com a ancora, o motor fecha a obra", com_ancora["saida"]["built"] is True)

    print("F9.16 — veredito SEM a ancora e recusado e o papel roda de novo")
    sem_ancora = bancada(texto, tick_cmd, max_rounds=1, review_sem_ancora="primeira")
    if sem_ancora is None:
        return 1
    check("sem a ancora, o revisor da MESMA rodada e chamado duas vezes",
          sem_ancora["agentes"].count("review") == 2)
    check("a segunda chamada diz ao juiz por que a primeira foi recusada",
          sem_ancora["vereditos"] == [False, True])
    check("o veredito que voltou com a ancora e o que vale",
          sem_ancora["saida"]["built"] is True)

    print("F9.16 — juiz que nunca prova que leu nao aprova nada")
    nunca = bancada(texto, tick_cmd, max_rounds=1, review_sem_ancora="sempre")
    if nunca is None:
        return 1
    check("o papel foi re-rodado uma vez e parou por ai (nao loopa)",
          nunca["agentes"].count("review") == 2)
    check("duas recusas seguidas nao viram aprovacao",
          nunca["saida"]["built"] is False)
    recusa = [b for b in nunca["saida"]["blockers"]
              if "ncora do fim" in (b.get("what") or "")]
    check("o relatorio diz que o veredito voltou sem a ancora", len(recusa) == 1)
    check("a obra da rodada e tratada como NAO verificada",
          bool(recusa) and "sem revisão" in (recusa[0].get("whyNeedsYou") or "").lower())

    # ── F9.18 · S-26 ─────────────────────────────────────────────────────────────
    # Executor que declara impossivel nao encerra nada sozinho. A alegacao repetida na
    # mesma tarefa convoca o auditor, e os DOIS desfechos sao do script: derruba devolve
    # a tarefa ao loop; confirma encerra como impedimento real, com o motivo escrito.
    # O controle vem primeiro: alegacao de UMA rodada so nao convoca ninguem.
    print("F9.51 — o comando do tique resolve o marcador por NOME, nao por posicao")
    # O caso que custou 8,45M em 2026-08-08: um passo da propria missao moveu
    # `plan_state.py` de plugin, o motor seguiu apontando o lugar velho, e cada agente
    # de marcacao redescobriu o rename sozinho. A prova de que nao volta e o comando
    # nao trazer caminho de plugin escrito a mao.
    # acopla-ok: os dois caminhos aparecem como o que o comando NAO pode conter — e a
    # asserção da ausência; citar o nome é o único jeito de provar que ele sumiu
    caminhos_cravados = ["plugins/visual/lib/plan_state.py",  # acopla-ok: asserção da AUSÊNCIA
                         "plugins/project-skills/lib/plan_state.py"]  # acopla-ok: idem
    check("o comando do tique nao crava caminho de plugin",
          not any(c in tick_cmd for c in caminhos_cravados))
    check("ele resolve o marcador por nome, ou por variavel que o resolveu",
          "resolve-plugin.sh" in texto and ("$MARCADOR" in tick_cmd or "resolve-plugin" in tick_cmd))
    check("e o comando roda a partir da RAIZ, pra busca nao alcancar copia de worktree",
          "cd <raiz>" in tick_cmd or "cd ${ARGS.repoRoot}" in texto)

    print("F9.53 + F9.54 — a marcacao da onda e UM agente, e o veredito volta")
    uma_onda = bancada(texto, tick_cmd, max_rounds=1)
    if uma_onda is None:
        return 1
    marcadores = [a for a in uma_onda["agentes"] if a == "tick"]
    check("a onda com 2 passos entregues disparou UM agente de marcacao, nao dois",
          len(marcadores) == 1)
    saida53 = uma_onda["saida"]
    marcados = (saida53.get("rounds") or [{}])[0].get("marcados") or []
    check("o veredito voltou ao script, com uma entrada por passo",
          len(marcados) == 2)
    check("e cada entrada diz se aquele passo foi marcado",
          all("ok" in m and "task_id" in m for m in marcados))
    # A prova de que o veredito nao e decoracao: o passo marcado com sucesso NAO vira
    # bloqueio, e o plano tem os dois `done`.
    perdidos = [b for b in saida53["blockers"] if "nao voltou no veredito" in (b.get("what") or "")]
    check("passo com veredito ok nao vira bloqueio de perda silenciosa", not perdidos)

    print("F9.56 — quem espera o dono NAO entra na conta de reincidencia")
    espera = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                     espera_dono="o dono precisa escolher a casa da skill")
    if espera is None:
        return 1
    check("nenhum diagnostico foi disparado sobre o passo que espera",
          "diag" not in espera["agentes"])
    saida56 = espera["saida"]
    check("e ele aparece como ESPERANDO VOCE, nao como falha",
          any(e.get("taskId") == "F1.3" for e in (saida56.get("esperandoVoce") or [])))

    print("F9.57 — o passo que falha cedo fecha a onda ANTES de ela terminar")
    # F1.3 volta com `done: false` e ele e o TERCEIRO da fila. Com bloco de 1, o motor tem
    # que reagir ali: F1.4 nao pode ter sido despachado nesta onda.
    cedo = bancada(texto, tick_cmd, max_rounds=1, review_complete=False, bloco_max=1)
    if cedo is None:
        return 1
    check("os blocos ate a falha sairam, na ordem",
          cedo["executados"][:3] == ["F1.1", "F1.2", "F1.3"])
    check("o bloco seguinte ao da falha NAO foi despachado",
          "F1.4" not in cedo["executados"])
    ronda57 = cedo["saida"]["rounds"][-1]
    check("o que nao saiu fica registrado na onda, pelo nome",
          (ronda57.get("naoDespachadas") or []) == ["F1.4"])
    check("e ele nao entra na conta de reincidencia (ninguem o tentou)",
          "diag" not in cedo["agentes"])
    # O controle: o MESMO cenario, com o bloco cobrindo a onda inteira, despacha F1.4. Sem
    # ele, "F1.4 nao saiu" poderia ser efeito do plano, e nao do retorno por bloco.
    onda_inteira = bancada(texto, tick_cmd, max_rounds=1, review_complete=False)
    if onda_inteira is None:
        return 1
    check("com a onda em um bloco so, o mesmo passo SAI (o controle)",
          "F1.4" in onda_inteira["executados"])

    print("F9.61 — o teto da LEVA adia o resto, e o adiado nao vira falha nem some")
    # Sem teto de leva, uma falha no segundo bloco cancelava a leva inteira: numa corrida
    # real, 45 de 53 tarefas foram decompostas pelo papel mais caro do motor para nunca
    # serem despachadas, e 30 voltaram PULADAS por "estado repetido" sem uma tentativa.
    # Aqui a leva e cortada em 2 numa fila de 4: F1.3 e F1.4 ficam para a rodada seguinte.
    leva = bancada(texto, tick_cmd, max_rounds=1, review_complete=False, leva_max=2)
    if leva is None:
        return 1
    ronda61 = leva["saida"]["rounds"][-1]
    check("so a leva da vez foi despachada", leva["executados"] == ["F1.1", "F1.2"])
    check("o adiado fica registrado na onda, pelo nome, separado do que falhou",
          sorted(ronda61.get("adiadas") or []) == ["F1.3", "F1.4"]
          and (ronda61.get("naoDespachadas") or []) == [])
    check("o adiado NAO vira Bloqueio (nem 'pulada', nem falha de ninguem)",
          not [b for b in leva["saida"]["blockers"]
               if b.get("taskId") in ("F1.3", "F1.4")])
    check("e ele nao entra na conta de reincidencia (ninguem o tentou)",
          "diag" not in leva["agentes"])
    # O controle: a MESMA missao sem teto despacha os quatro. Sem ele, "F1.3 nao saiu"
    # poderia ser efeito do plano, e nao do corte da leva.
    check("sem teto de leva, a mesma missao despacha os quatro (o controle)",
          "F1.3" in onda_inteira["executados"] and "F1.4" in onda_inteira["executados"])

    print("F9.61 — revisor generoso NAO fecha a obra com fila adiada")
    # `built` e fato do programa antes de ser juizo do revisor: aqui o revisor devolve
    # `complete: true` (o default da bancada) numa rodada em que o teto de leva adiou
    # F1.3 e F1.4 — o motor tem que seguir para a rodada seguinte e despachar a fila,
    # nunca declarar pronto por cima de tarefa que ninguem viu.
    generoso = bancada(texto, tick_cmd, max_rounds=2, leva_max=2)
    if generoso is None:
        return 1
    check("a rodada 1 com fila adiada NAO declarou built",
          (generoso["saida"]["rounds"][0].get("adiadas") or []) == ["F1.3", "F1.4"]
          and len(generoso["saida"]["rounds"]) == 2)
    check("a fila adiada foi despachada na rodada 2",
          "F1.3" in generoso["executados"] and "F1.4" in generoso["executados"])

    print("F9.18 — alegacao que nao se repetiu nao convoca auditor (o controle)")
    uma_vez = bancada(texto, tick_cmd, max_rounds=1, alegacao_impossivel=ALEGACAO)
    if uma_vez is None:
        return 1
    check("com uma rodada so, nenhum auditor foi convocado",
          "auditor" not in uma_vez["agentes"])
    check("e ninguem encerrou a tarefa como impedimento",
          not [b for b in uma_vez["saida"]["blockers"] if b.get("kind") == "impedimento"])

    print("F9.18 — auditor que DERRUBA a alegacao devolve a tarefa ao loop")
    derruba = bancada(texto, tick_cmd, max_rounds=2, review_complete=False,
                      alegacao_impossivel=ALEGACAO, auditor_derruba=True,
                      auditor_motivo="a ferramenta estava na mao; a causa e outra",
                      auditor_nao_tentou=["navegador"])
    if derruba is None:
        return 1
    saida9 = derruba["saida"]
    check("a alegacao repetida convocou o auditor, uma vez",
          derruba["agentes"].count("auditor") == 1)
    auditoria = derruba["auditorias"][0] if derruba["auditorias"] else {}
    check("o auditor recebeu a alegacao do executor", auditoria.get("alegacao") == ALEGACAO)
    check("o auditor recebeu a lista do que havia a mao",
          auditoria.get("ferramentas") == FERRAMENTAS_A_MAO)
    devolvidas = saida9["rounds"][-1].get("devolvidas") or []
    check("a tarefa derrubada volta pro loop, com o que o auditor apontou",
          [d["taskId"] for d in devolvidas] == ["F1.3"]
          and "a causa e outra" in devolvidas[0]["motivo"])
    check("o auditor que derruba nao encerra nada como impedimento",
          not [b for b in saida9["blockers"] if b.get("kind") == "impedimento"])
    check("e o dono nao e chamado por causa dela",
          not [b for b in (saida9.get("impedidos") or []) if b.get("taskId") == "F1.3"])

    print("F9.18 — auditor que CONFIRMA encerra como impedimento real, com o motivo")
    confirma = bancada(texto, tick_cmd, max_rounds=2, review_complete=False,
                       alegacao_impossivel=ALEGACAO, auditor_derruba=False,
                       auditor_motivo="publicar depende do aval do dono, e a tela so existe publicada")
    if confirma is None:
        return 1
    saida10 = confirma["saida"]
    check("o mesmo cenario convocou o auditor, uma vez",
          confirma["agentes"].count("auditor") == 1)
    impedimento = [b for b in saida10["blockers"] if b.get("kind") == "impedimento"]
    check("a tarefa e encerrada como impedimento real", len(impedimento) == 1)
    check("o impedimento nomeia a tarefa e traz o motivo ESCRITO pelo auditor",
          bool(impedimento) and impedimento[0]["taskId"] == "F1.3"
          and "publicar depende do aval do dono" in impedimento[0]["what"])
    check("o impedimento sai como 'precisa de voce', e nao como falta de tempo",
          any(b.get("taskId") == "F1.3" for b in saida10.get("impedidos") or []))
    check("a tarefa confirmada NAO volta pro loop",
          not (saida10["rounds"][-1].get("devolvidas") or []))
    check("e ela nao sai marcada no plano",
          "F1.3" not in [c["taskId"] for c in confirma["chamadas"]])

    # ── autopsia 2026-08-09: as travas da marcacao e da parada ──────────────────
    # Medido na corrida wf_5438d704: 17 passos marcados em ondas VERMELHAS, 9 com o
    # defeito ja escrito pelo revisor da MESMA onda, e nenhuma conferencia final rodou
    # porque o confirm so existia no caminho feliz sem /qa-loop. Os quatro cenarios
    # abaixo mudam UMA coisa cada um sobre a mesma missao.
    print("autopsia — a causa investigada so entra depois de sobreviver ao desafio")
    # F1.3 reaparece como faltante em toda rodada (review_complete=False) e na 3a onda o
    # churn chega ao limiar: o investigador roda, e o desafiador referenda so na 2a volta.
    acordo = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                     desafio_referenda_na_volta=2)
    if acordo is None:
        return 1
    check("investigador e desafiador loopam ate concordar (2 voltas cada)",
          acordo["agentes"].count("diag") == 2 and acordo["agentes"].count("desafio") == 2)
    check("o desafio da volta 1 VOLTA ao investigador na volta 2",
          len(acordo["investigacoes"]) == 2
          and acordo["investigacoes"][0].get("desafioAnterior") is None
          and acordo["investigacoes"][1].get("desafioAnterior") == "a causa nao explica o fato X")
    check("o desafiador recebeu a causa que julgou",
          bool(acordo["desafios"]) and "causa apontada" in str(acordo["desafios"][0].get("causa")))
    check("a causa referendada entra sem virar disputa",
          not [b for b in acordo["saida"]["blockers"] if b.get("kind") == "causa-em-disputa"])

    print("autopsia — tres voltas sem acordo viram disputa, nunca conserto")
    disputa = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                      desafio_referenda_na_volta=0)
    if disputa is None:
        return 1
    check("o loop parou em 3 voltas, sem vencedor no cansaco",
          disputa["agentes"].count("diag") == 3 and disputa["agentes"].count("desafio") == 3)
    emdisputa = [b for b in disputa["saida"]["blockers"] if b.get("kind") == "causa-em-disputa"]
    check("a disputa vira Bloqueio com as DUAS versoes escritas",
          len(emdisputa) == 1 and "investigador diz" in emdisputa[0]["what"]
          and "desafiador diz" in emdisputa[0]["what"])
    check("a disputa e 'precisa de voce', nomeando a tarefa",
          bool(emdisputa) and emdisputa[0].get("taskId") == "F1.3"
          and "causa em disputa" in (emdisputa[0].get("whyNeedsYou") or ""))

    # ── F23.9 · o DESTRAVADOR: causa de repositorio se conserta NA corrida ──────
    # Quatro corridas seguidas morreram na mesma classe de causa (2026-08-15): um
    # estado que uma suite cobra e ficou para tras. O trabalho estava pronto no disco,
    # o commit nao passava, e a corrida inteira morria — com o dono destravando em dois
    # minutos na manha seguinte. Os dois cenarios abaixo mudam UMA coisa: se o conserto
    # pegou.
    print("F23.9 — causa de repositorio: o destravador conserta, o motor RE-MEDE e segue")
    destravou = bancada(texto, tick_cmd, max_rounds=1, review_complete=False,
                        rev_tarefa_reprova=["F1.1"], desafio_referenda_na_volta=1,
                        desafio_escopo="repositorio", destrava_ok=True)
    if destravou is None:
        return 1
    check("o destravador foi chamado uma vez",
          destravou["agentes"].count("destrava") == 1)
    check("ele recebeu a CAUSA referendada, nao so o pedido de consertar",
          bool(destravou["destraves"])
          and "causa apontada" in str(destravou["destraves"][0].get("causa")))
    check("quem re-mediu a porta foi a guarda de saude, depois do destravador",
          destravou["agentes"].index("destrava") + 1
          < len(destravou["agentes"])
          and destravou["agentes"][destravou["agentes"].index("destrava") + 1] == "saude")
    check("a corrida NAO desligou por causa-global",
          destravou["saida"].get("stopReason") != "causa-global"
          and not [b for b in destravou["saida"]["blockers"]
                   if b.get("kind") == "causa-global"])

    print("F23.9 — conserto que NAO pegou: a palavra do destravador nao abre porta")
    nao_pegou = bancada(texto, tick_cmd, max_rounds=1, review_complete=False,
                        rev_tarefa_reprova=["F1.1"], desafio_referenda_na_volta=1,
                        desafio_escopo="repositorio", destrava_ok=True,
                        porta_fecha_so_na_remedida=True)
    if nao_pegou is None:
        return 1
    global_ = [b for b in nao_pegou["saida"]["blockers"] if b.get("kind") == "causa-global"]
    check("o motor desligou por causa-global mesmo com o destravador dizendo que consertou",
          nao_pegou["saida"].get("stopReason") == "causa-global" and len(global_) == 1)
    check("e o bloqueio diz que a re-medicao continuou fechada",
          bool(global_) and "re-medição" in (global_[0].get("whyNeedsYou") or ""))

    print("ciclo por bloco — o revisor DO BLOCO retem a marcacao; a geral reabre com re-tick")
    GAP_NA_F11 = {"kind": "coesao", "severity": "P1", "task_id": "F1.1",
                  "problem": "a entrega da F1.1 quebrou o cobrador vizinho"}
    # 3a · reprova no BLOCO: F1.1 nao e marcada, e a retencao sai nomeada
    segura = bancada(texto, tick_cmd, max_rounds=1, rev_bloco_gaps=[GAP_NA_F11])
    if segura is None:
        return 1
    marcadas = [c["taskId"] for c in segura["chamadas"]]
    check("F1.1 (reprovada pelo revisor do bloco) ficou FORA da marcacao", "F1.1" not in marcadas)
    check("F1.2 (limpa) foi marcada no mesmo bloco", "F1.2" in marcadas)
    retido = segura["saida"]["rounds"][0].get("naoMarcados") or {}
    check("a retencao sai NOMEADA no registro da onda, com o motivo",
          retido.get("motivo") == "reprova do revisor de tarefa ou de bloco"
          and retido.get("ids") == ["F1.1"])
    check("a retencao e narrada, nao calada",
          any("reprova nos blocos" in n for n in segura.get("narrado") or []))
    # 3b · o revisor POR TAREFA tambem retem, antes mesmo do bloco
    seg2 = bancada(texto, tick_cmd, max_rounds=1, rev_tarefa_reprova=["F1.1"])
    if seg2 is None:
        return 1
    check("a reprova do revisor POR TAREFA tambem segura a marcacao",
          "F1.1" not in [c["taskId"] for c in seg2["chamadas"]])
    # 3c · gap da revisao GERAL sobre passo ja marcado NAO retem: vira RE-TICK
    geral = bancada(texto, tick_cmd, max_rounds=1, gaps=[GAP_NA_F11])
    if geral is None:
        return 1
    check("o passo ja marcado pelo bloco CONTINUA marcado (a geral chega depois)",
          "F1.1" in [c["taskId"] for c in geral["chamadas"]])
    check("o achado da geral vira RE-TICK do mesmo id, nunca id novo",
          geral["saida"]["rounds"][0].get("reticks") == ["F1.1"])
    check("o re-tick e narrado ao dono",
          any("regrava a prova do mesmo id" in n for n in geral.get("narrado") or []))

    print("ciclo por bloco — suite vermelha no bloco nao marca NADA no plano")
    verm2 = bancada(texto, tick_cmd, max_rounds=1, review_complete=False,
                    suite_verde=False, suite_falhando=["test_x.py"])
    if verm2 is None:
        return 1
    check("nenhum tick foi disparado com a suite vermelha", verm2["chamadas"] == [])
    check("o bloco vermelho vira Bloqueio nomeando a suite que quebrou",
          any("a suíte quebrou no bloco" in (b.get("what") or "")
              and "test_x.py" in (b.get("what") or "")
              for b in verm2["saida"]["blockers"]))
    check("bloco vermelho nao vira checkpoint",
          verm2["saida"]["rounds"][0].get("checkpoint") is not True)

    print("largada vermelha — o motor para na PORTA, antes de despachar executor")
    # Ate aqui a suite da largada era verde por construcao no arnes, entao o ramo de
    # porta-fechada do motor nunca rodava na bancada: apagar o `break` deixava a suite
    # verde. Aqui a cor da largada vem do cenario, e o que se afere e o desfecho.
    porta = bancada(texto, tick_cmd, max_rounds=2,
                    largada_falhando=["test_plan_state.py", "test_andamento.py"])
    if porta is None:
        return 1
    fechada = [b for b in porta["saida"]["blockers"]
               if "vermelha antes da missão" in (b.get("what") or "")]
    check("a largada vermelha vira Bloqueio, nao silencio", len(fechada) == 1)
    check("o Bloqueio traz a lista dos testes que ja estavam vermelhos",
          bool(fechada) and "test_plan_state.py" in fechada[0]["what"]
          and "test_andamento.py" in fechada[0]["what"])
    check("o motor se desligou pela porta fechada",
          porta["saida"]["stopReason"] == "porta-fechada")
    check("NENHUM executor foi despachado com a porta fechada",
          porta["executados"] == [] and porta["agentes"].count("exec") == 0)
    check("a largada vermelha nao decompoe o plano nem marca passo",
          porta["agentes"].count("decompose") == 0 and porta["chamadas"] == [])
    # O caminho de parada tambem e caminho de saida do motor: o sinal da barra tem que
    # ser apagado aqui, senao ele fica aceso mentindo depois que a missao morreu. Ate
    # aqui ninguem afirmava isso na bancada — o unico cobrador do despacho era procurar
    # a string `encerra:barra` no arquivo, que passa com a chamada embrulhada em
    # QUALQUER condicao.
    check("a porta fechada ainda apaga o sinal da barra ao sair",
          porta["agentes"].count("encerra") == 1)

    print("reserva recusada — o motor sai SEM apagar o sinal da sessao do outro motor")
    # A excecao unica: `andamento.py encerra <sid>` apaga por SESSAO, e quem a reserva
    # recusou nunca acendeu nada. Encerrar aqui apagaria a barra do motor que segue
    # trabalhando. Sem este cenario, a condicao que protege o outro motor nao tem
    # cobrador nenhum — apagar o `if` deixa a bancada inteira verde.
    recusado = bancada(texto, tick_cmd, max_rounds=2, reserva_recusada=True)
    if recusado is None:
        return 1
    check("o motor se desligou pela reserva",
          recusado["saida"]["stopReason"] == "reserva")
    check("a recusa vira Bloqueio nomeando os arquivos que o outro motor reservou",
          any("outro motor desta sessão já reservou" in (b.get("what") or "")
              and "F1.1.txt" in (b.get("what") or "")
              for b in recusado["saida"]["blockers"]))
    check("NENHUM executor foi despachado com a reserva recusada",
          recusado["executados"] == [] and recusado["agentes"].count("exec") == 0)
    check("o motor recusado pela reserva NAO encerra o estado da sessao",
          recusado["agentes"].count("encerra") == 0)

    print("autopsia — quem para sem terminar roda a conferencia final")
    parada = bancada(texto, tick_cmd, max_rounds=1, review_complete=False,
                     confirm_gaps=[{"task_id": "F1.1", "kind": "spec", "severity": "P1",
                                    "problem": "a conferencia da parada achou a metade que faltou"}])
    if parada is None:
        return 1
    saidap = parada["saida"]
    check("a missao parou sem built", saidap["built"] is False)
    check("a conferencia final rodou na parada", parada["agentes"].count("confirm") == 1)
    check("o relatorio diz QUAL conferencia rodou", saidap.get("conferidoPor") == "confirm-na-parada")
    achado = [b for b in saidap["blockers"] if "conferência final da parada" in (b.get("what") or "")]
    check("o gap da conferencia vira aviso NOMEADO, com a tarefa",
          len(achado) == 1 and achado[0].get("taskId") == "F1.1")

    print("autopsia — parada por ORCAMENTO nao gasta a conferencia, e diz isso")
    teto = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                   token_budget=1000, gasto_por_chamada=400)
    if teto is None:
        return 1
    check("o disjuntor parou e a conferencia NAO foi disparada",
          teto["saida"]["stopReason"] == "orcamento" and teto["agentes"].count("confirm") == 0)
    check("a ausencia nao passa calada: conferidoPor = nenhuma",
          teto["saida"].get("conferidoPor") == "nenhuma")

    print("autopsia — onda esteril encerra a corrida em vez de pagar decomposicao vazia")
    esteril = bancada(texto, tick_cmd, max_rounds=3, review_complete=False, espera_todos=True)
    if esteril is None:
        return 1
    saidae = esteril["saida"]
    check("a corrida encerrou na primeira onda esteril",
          saidae["stopReason"] == "onda-esteril" and len(saidae["rounds"]) == 1)
    check("nenhum executor foi disparado", esteril["executados"] == [])
    check("so UMA decomposicao foi paga", esteril["agentes"].count("decompose") == 1)
    esterilb = [b for b in saidae["blockers"] if "estéril" in (b.get("what") or "")]
    check("o encerramento vira Bloqueio dizendo quantas foram separadas sem sair",
          len(esterilb) == 1
          and re.search(r"[1-9]\d* tarefa\(s\) separadas", esterilb[0]["what"]))

    # ── F25.3: o laco da revisao fecha, e a bancada anda as tres voltas ─────────
    print("F25.3 — feito o conserto, a revisao reabre sobre ele; o laco so fecha limpo")
    voltas = bancada_qa([
        # 1a volta: sweep completo acha o defeito grave e ele vai pro conserto.
        {"findings": [{"id": "f1", "file": "a.py", "fn": "valida", "severity": "P0",
                       "problem": "a entrada invalida passa"}]},
        # 2a volta: a revisao reabre sobre o arquivo que o conserto tocou e acha o RESIDUO
        # — o defeito que o proprio conserto deixou, e que uma rodada so nunca veria.
        {"findings": [{"id": "f2", "file": "a.py", "fn": "valida", "severity": "P1",
                       "problem": "o conserto deixou o caso vazio de fora"}]},
        # 3a volta: nada mais aparece — e e so ai que o laco fecha.
        {"findings": []},
    ])
    if voltas is None:
        return 1
    saidaq = voltas["saida"]
    check("a 1a volta achou e consertou", voltas["consertados"][:1] == ["f1"]
          and len(saidaq["rounds"][0]["corrections"]) == 1)
    escopo2 = (voltas["revisoes"][1] or {}).get("scope") if len(voltas["revisoes"]) > 1 else None
    check("a 2a volta reabriu SOBRE o que foi consertado, nao sobre o material inteiro",
          isinstance(escopo2, dict) and escopo2.get("touchedFiles") == ["a.py"])
    check("a 2a volta achou o residuo e consertou", voltas["consertados"] == ["f1", "f2"])
    check("a 3a volta veio limpa e o laco fechou",
          len(saidaq["rounds"]) == 3 and saidaq["stopReason"] == "no-severe-finding")
    check("a rodada limpa passou pela conferencia dedicada antes de fechar",
          voltas["agentes"].count("confirm") == 1)
    check("nenhuma volta a mais foi paga depois da limpa",
          voltas["agentes"].count("review") == 3)

    print("F25.3 — a rodada que PARECE limpa nao fecha se a conferencia achar algo")
    resto = bancada_qa([{"findings": []}, {"findings": []}],
                       confirm={"complete": True,
                                "findings": [{"id": "f9", "file": "b.py", "fn": "g",
                                              "severity": "P0",
                                              "problem": "o que a barata perdeu"}]})
    if resto is None:
        return 1
    check("o achado da conferencia reabre o laco em vez de fechar",
          len(resto["saida"]["rounds"]) > 1 and "f9" in resto["consertados"])

    # ── F25.4: as duas receitas fecham o laco, e a saida conta as VOLTAS por problema ──
    # O total de rodadas nao distingue um defeito teimoso de tres defeitos de uma volta
    # cada, e sao acoes diferentes. Aqui se afere o numero POR PROBLEMA nos dois motores.
    print("F25.4 — a saida da REVISAO conta as voltas de cada problema ate a rodada limpa")
    teimoso = bancada_qa([
        # o mesmo achado reaparece na 2a volta: o conserto da 1a nao resolveu.
        {"findings": [{"id": "f1", "file": "a.py", "fn": "valida", "severity": "P0",
                       "problem": "a entrada invalida passa"}]},
        {"findings": [{"id": "f1", "file": "a.py", "fn": "valida", "severity": "P0",
                       "problem": "a entrada invalida passa"},
                      {"id": "f2", "file": "b.py", "fn": "g", "severity": "P1",
                       "problem": "o outro caso"}]},
        {"findings": []},
    ])
    if teimoso is None:
        return 1
    porid = {v["id"]: v for v in (teimoso["saida"].get("voltasPorProblema") or [])}
    check("o problema que atravessou duas voltas sai com 2", porid.get("f1", {}).get("voltas") == 2)
    check("o que nasceu na 2a volta e sumiu sai com 1", porid.get("f2", {}).get("voltas") == 1)
    check("cada problema sai com a volta em que apareceu",
          porid.get("f1", {}).get("primeira") == 1 and porid.get("f2", {}).get("primeira") == 2)

    print("F25.4 — a saida da IMPLEMENTACAO conta as mesmas voltas, pelos gaps do revisor")
    duasvoltas = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_SPEC])
    if duasvoltas is None:
        return 1
    vpp = duasvoltas["saida"].get("voltasPorProblema") or []
    check("o gap que sobreviveu as duas rodadas sai contado como 2",
          len(vpp) == 1 and vpp[0]["voltas"] == 2 and vpp[0]["kind"] == "spec")

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
