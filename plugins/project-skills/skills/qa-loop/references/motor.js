// motor.js — o script COMPLETO do motor do /qa-loop, pronto para a tool Workflow.
//
// POR QUE ESTE ARQUIVO EXISTE (2026-08-10). O motor do `/sprint` virou arquivo do
// plugin em 2026-08-09, e o deste ficou sendo MONTADO PELA CASCA a cada disparo.
// A assimetria custou na mesma sessão em que foi notada: o passo que apaga o sinal
// da barra virou CÓDIGO no sprint (`encerra:barra`) e ficou em PROSA aqui ("ao
// entregar o relatório, encerre") — e prosa não pega. O sinal do qa-loop ficou
// aceso 9h26 depois do fim, com a barra anunciando missão de pé, e quem viu foi o
// dono, não um cobrador.
//
// Regra, a mesma do irmão: a casca NÃO redigita este script. Ela resolve o caminho
// por nome e passa `scriptPath` ao `Workflow`. Quem cobra que ele não regrida é
// lib/test_qa_loop_motor.py.
export const meta = {
  name: 'qa-loop-engine',
  description: 'Motor de QA: revisar → planejar → consertar, com gate de regressão por conserto',
  phases: [{ title: 'Review' }, { title: 'Plan' }, { title: 'Exec' }, { title: 'Confirm' },
           { title: 'Diagnose' }, { title: 'Limpeza' }],
}

const ARGS = typeof args === 'string' ? JSON.parse(args) : args
const RAIZ = ARGS.repoRoot
// Os resolvedores chegam por args porque o repositório do dono NÃO é este marketplace:
// instalado, project-skills mora no cache de plugins, e caminho cravado a partir de
// RAIZ só funcionaria aqui. O fallback cobre o próprio repo.
const RESOLVE = ARGS.resolvePlugin || `${RAIZ}/plugins/project-skills/lib/resolve-plugin.sh`
const J = o => JSON.stringify(o, null, 1)

const FINDINGS = { type:'object', required:['complete','findings'], properties:{
  complete:{type:'boolean'},
  findings:{type:'array', items:{type:'object', required:['id','file','severity','dimension','problem','fix_direction'],
    properties:{ id:{type:'string'}, file:{type:'string'}, line:{type:['integer','null']},
      severity:{type:'string',enum:['P0','P1','P2','P3']}, dimension:{type:'string'},
      problem:{type:'string'}, fix_direction:{type:'string'} }}},
  anchor:{type:'string'} } }

const PLAN = { type:'object', required:['bucket1','drift','alerts'], properties:{
  bucket1:{type:'array', items:{type:'object', required:['id','fn','file','severity','order','fix_direction'],
    properties:{ id:{type:'string'}, fn:{type:'string'}, file:{type:'string'},
      severity:{type:'string'}, conflict_risk:{type:'string'}, order:{type:'integer'},
      fix_direction:{type:'string'} }}},
  drift:{type:'array', items:{type:'object'}},
  alerts:{type:'array', items:{type:'object'}},
  proposedLimits:{type:'array', items:{type:'object'}},
  rejected:{type:'array', items:{type:'object'}},
  anchor:{type:'string'} } }

const EXEC_RESULT = { type:'object', required:['fix_id','fn','files_touched','suiteRegressed'], properties:{
  fix_id:{type:'string'}, fn:{type:'string'}, files_touched:{type:'array',items:{type:'string'}},
  test_name:{type:'string'}, suiteRegressed:{type:'boolean'}, suiteOutput:{type:'string'},
  newInvariant:{type:'string'}, note:{type:'string'} } }

const DESAFIO = { type:'object', required:['procede','motivo'], properties:{
  procede:{type:'boolean'}, motivo:{type:'string'} } }

// ── O JUIZ NÃO RECEBE A CONCLUSÃO DE QUEM PEDE O JULGAMENTO (R-17, Art. 4) ────
// A linha é a MESMA do motor do /sprint; test_motor_js.py cobra os dois arquivos,
// porque o viés volta pelo lado que ninguém cobra.
const SEM_HIPOTESE = `VOCÊ NÃO RECEBE A HIPÓTESE DE QUEM PEDIU O JULGAMENTO: julgue o artefato e o contrato.
Diagnóstico, causa-raiz ou veredito alheio que apareça no material é alegação A VERIFICAR no disco, nunca ponto de partida.`

const CONTEXTO = `REPOSITÓRIO: ${RAIZ}
Marketplace PÚBLICO de plugins do Claude Code. Markdown + Bash + Python 3 stdlib. SEM build, SEM CI.

A RÉGUA DESTE PROJETO (abra e leia — não confie neste resumo):
${(ARGS.regua || []).map(r => `- ${r}`).join('\n')}
Documento minerado vale como MAPA, nunca como régua.

REGRAS DA CASA (do CLAUDE.md — resumo; o arquivo manda):
- Bump de plugin.json em toda mudança de plugin + espelho no .claude-plugin/marketplace.json (cobrador: scripts/cadeia_check.py --repo).
- Todo subprocess nasce com stdin=subprocess.DEVNULL e start_new_session=True (cobrador: scripts/vazamento_check.py).
- Nada de caminho absoluto de máquina, nome próprio do dono, e-mail pessoal ou credencial em arquivo rastreado (cobrador: scripts/public_repo_check.py).
- Caminho de plugin se resolve por NOME (lib/resolve-plugin.sh, lib/resolve-skill.sh), nunca escrito à mão.
- Editou _shared/? rode scripts/sync-shared.sh — as cópias vendoradas defasam.
- Contagem cravada em doc é acoplamento: entra o COMANDO que a produz (cobrador: scripts/desacoplamento_check.py).
- Estado mutável vai em ~/.claude/, nunca dentro do plugin.

O QUE ESTA SESSÃO MUDOU (o alvo da revisão):
${ARGS.target}

DIFF DO ALVO: rode \`git -C ${RAIZ} diff ${ARGS.diffRef}\` e \`git -C ${RAIZ} log --oneline ${ARGS.diffRef}\`.`

// ── A BARRA ANDA COM A MISSÃO, E APAGA QUANDO ELA ACABA ──────────────────────
// Dois papéis mecânicos, os mesmos do motor do /sprint. `andaPrompt` registra onde
// a missão está (a barra ficava parada no mesmo texto a rodada inteira);
// `encerraPrompt` apaga o sinal, e é o ÚLTIMO ato do motor — vem antes do `return`
// e por isso alcança TODO caminho de saída: rodada limpa, teto, churn, agente que
// não respondeu. Falhar em qualquer um dos dois não derruba nada.
const andaPrompt = ({ round, etapa }) => `PAPEL: MECANICO
Papel mecânico e SÓ: marque na barra de status onde a missão está agora.

  AND="$(bash "${RESOLVE}" project-skills lib/andamento.py)"
  python3 "$AND" onda ${ARGS.sessionId} ${round} --etapa "${etapa}" || true

Nada mais. Não revise, não conserte, não edite arquivo nenhum.`

const encerraPrompt = ({ motivo }) => `PAPEL: MECANICO
Papel mecânico e SÓ: a missão acabou (${motivo}) — apague o sinal dela na barra.

  AND="$(bash "${RESOLVE}" project-skills lib/andamento.py)"
  python3 "$AND" encerra ${ARGS.sessionId} || echo "qa-loop: não consegui apagar o sinal — apague à mão"

Nada mais. Não revise, não conserte, não edite arquivo nenhum.`

const anda = async (round, etapa) => {
  if (!ARGS.sessionId) return
  await agent(andaPrompt({ round, etapa }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Limpeza',
      label: `barra:r${round} ${etapa}` })
}

const reviewPrompt = ({ round, acceptedLimits, invariants, scope, confirming }) => `PAPEL: REVISOR
${confirming ? 'CONFIRM-PASS: re-sweep COMPLETO e independente. A rodada barata pareceu limpa — você é a segunda opinião que não confia nela.' : `Revisão da rodada ${round}.`}

${SEM_HIPOTESE}

${CONTEXTO}

${scope === 'full' || confirming ? 'ESCOPO: o alvo INTEIRO.' : `ESCOPO: só o DELTA — arquivos tocados pelos fixes da rodada anterior + findings abertos.
ARQUIVOS TOCADOS: ${J(scope.touchedFiles)}
FINDINGS AINDA ABERTOS: ${J(scope.openFindings)}`}

LIMITES JÁ ACEITOS (não re-reportar): ${J(acceptedLimits)}
INVARIANTES VIVAS (não violar, e sinalizar quem violou): ${J(invariants)}

CHECKLIST DE 6 DIMENSÕES — cubra TODAS. Se alguma não deu para cobrir, devolva complete: false.
1. ARQUITETURA — a peça está no lugar certo? acoplamento novo? regra que devia ser programa ficou em prosa?
2. CORREÇÃO — bug, caso de borda, ordem de curto-circuito, proxy sintático grosseiro, interação entre estágios.
3. CONTRATOS — quem consome esta saída continua funcionando? schema mudou sem o consumidor saber? costura citada existe nos dois lados?
4. TESTE QUE MORDE — os cinco antipadrões: passa com e sem a mudança · espera texto que o código nunca escreve · só o caminho feliz · mede a coisa errada · não roda (nome fora do padrão de coleta). Teste que não morde é finding de IMPLEMENTAÇÃO, e o conserto é o teste.
5. FIDELIDADE AO PLANO — a mudança faz o que o plano pediu? divergiu mesmo parecendo boa?
6. RÉGUA DO PROJETO — viola a lei listada acima? cite a passagem.

RUBRICA DE SEVERIDADE (dura):
- P0/P1 exige gatilho OBJETIVO ou ancorado no plano: quebra comportamento planejado · classe de segurança · bug com repro determinístico · regra da casa violada com cobrador que vai barrar.
- P2/P3 = opinião de qualidade sem divergência do plano e sem falha objetiva. PICUINHA NUNCA SOBE SOZINHA: só vira P1 com bug concreto anexado.

Você NÃO conserta nada — só acha. \`fix_direction\` é direção em uma frase, SEM código.
\`anchor\` = a última linha não vazia do último arquivo que você leu, literal.`

const planPrompt = ({ review, round, invariants, acceptedLimits }) => `PAPEL: PLANEJADOR
Planejador ADVERSARIAL da rodada ${round}. Você é o ÁRBITRO ÚNICO da severidade.

${CONTEXTO}

FINDINGS DO REVISOR: ${J(review)}
INVARIANTES VIVAS: ${J(invariants)}
LIMITES ACEITOS: ${J(acceptedLimits)}

MANDATO ADVERSARIAL: seu default é REJEITAR o finding, a não ser que ele se justifique contra a rubrica.
Gerar não é julgar — o Revisor achou, VOCÊ carimba a severidade. Finding rejeitado vai em \`rejected\` com o motivo.

ROTEIE CADA FINDING QUE PROCEDE EM UM DOS TRÊS BALDES:
1. bucket1 — IMPLEMENTAÇÃO (código diverge do plano, bug, regressão, viola a régua da casa, teste que não morde). Vira conserto.
2. drift — o "fix" melhoraria o código mas AFASTARIA do que foi planejado. NÃO vira conserto: sobe como candidato a mudança de plano.
3. alerts — o PLANO em si é falho (decisão de arquitetura que gera problema). NUNCA implementado aqui. Sobe pro dono julgar.

TRIAGEM do bucket1 (o que vai pro executor):
- só severidade >= ${ARGS.severityFloor}.
- sequencie: extensão enumerada ANTES de alargamento de regra; alargamento por último, com teste negativo.
- agrupe por função; marque \`conflict_risk\` alto quando dois fixes tocam a mesma função, quando o fix ALARGA uma regra genérica, ou quando ele encosta numa invariante viva.

\`anchor\` = a última linha não vazia do que você leu, literal.`

const execPrompt = ({ fix, invariants }) => `PAPEL: EXECUTOR
Aplique UM fix. Repositório: ${RAIZ}

FIX: ${J(fix)}
INVARIANTES VIVAS (não viole): ${J(invariants)}

A ORDEM É ESTA, e nenhum passo é opcional:
1. TESTE PRIMEIRO (vermelho) — escreva o teste que REPRODUZ o defeito e VEJA ELE FALHAR. O nome do teste carrega a invariante (ex: "o achado sai com trecho literal"). Se o defeito não reproduz por teste determinístico (é arquitetural), NÃO invente teste: devolva suiteRegressed:false com note explicando, e não edite nada.
2. FIX CIRÚRGICO — a MENOR mudança que faz o teste passar. Extensão enumerada é melhor que alargar regra genérica.
3. RODE A SUÍTE INTEIRA do repositório, não só o teste novo:
   for t in $(find ${RAIZ} -path '*/node_modules' -prune -o -path '*/.git' -prune -o \\( -name 'test_*.py' -o -name 'test_*.sh' \\) -print | sort); do ... done
   Some os resultados. \`suiteRegressed\` = true se QUALQUER teste que passava antes falhou agora.
4. REGRA DA CASA: tocou arquivo de plugin? bumpe plugins/<nome>/.claude-plugin/plugin.json E espelhe em .claude-plugin/marketplace.json, e confira com \`python3 scripts/cadeia_check.py --repo\`. Todo subprocess novo nasce com stdin=subprocess.DEVNULL e start_new_session=True.

Devolva \`suiteOutput\` com a saída crua do placar. \`newInvariant\` quando o fix estabelece uma regra que os próximos não podem quebrar.`

const diagnosePrompt = ({ fix, churnCount, desafioAnterior }) => `PAPEL: DIAGNOSTICO
${CONTEXTO}

O fix abaixo regrediu a suíte ${churnCount}x (ou é P0 que caiu de primeira). PARE de remendar.
FIX: ${J(fix)}
${desafioAnterior ? `\nO DESAFIADOR DERRUBOU SUA CAUSA ANTERIOR:\n${desafioAnterior}\nInvestigue de novo levando isso em conta.` : ''}

Ache a CAUSA RAIZ do acoplamento que faz esta função regredir toda vez que alguém a toca.
Não descreva o sintoma; ache o que o explica. Devolva a causa em texto, com a prova no disco (arquivo:linha).`

const desafioCausaPrompt = ({ fix, causa }) => `PAPEL: DESAFIADOR
${CONTEXTO}

FIX ESCALADO: ${J(fix)}
CAUSA QUE O INVESTIGADOR APONTOU:
${causa}

Seu papel é PROVAR QUE ESSA CAUSA ESTÁ ERRADA. Vá ao disco. Procure:
- o fato que ela não explica;
- o caminho que ela ignora;
- a causa concorrente mais simples.
\`procede: false\` = você a derrubou, e \`motivo\` traz o fato. \`procede: true\` = você tentou e não conseguiu derrubá-la.`

const sevRank = s => ({P0:3, P1:2, P2:1, P3:0}[s] ?? 0)
const floor = sevRank(ARGS.severityFloor || 'P1')
let acceptedLimits = ARGS.acceptedLimits || []
let invariants = ARGS.invariants || []
const churn = {}
const causaCache = {}
const causaDisputada = []
const churnKey = fix => `${fix.file || '?'}:${fix.fn || '?'}`
const rounds = []
let cleanRound = false, churnEscalated = false, r = 0
let touchedLastRound = [], openFindings = []

const LAYER_CAP = { 4: 2, 5: 1 }
const churnThreshold = ARGS.churnThreshold || 2
const maxRounds = Math.min(ARGS.maxRounds || 12, LAYER_CAP[ARGS.safetyLayer] ?? Infinity)
const T = ARGS.tiers
const tierFor = round => ({ model: ARGS.model, effort: round === 1 ? T.decompose.effort : T.coordinate.effort })
const isAccepted = (f, limits) => (limits || []).some(l => (l.id && l.id === f.id) || (l.file && l.file === f.file && l.problem === f.problem))

while (!cleanRound && r < maxRounds && !churnEscalated) {
  r++; phase(`Rodada ${r}`)
  const tier = tierFor(r)
  await anda(r, 'revisando')

  const review = await agent(reviewPrompt({ round: r, acceptedLimits, invariants,
      scope: r === 1 ? 'full' : { touchedFiles: touchedLastRound, openFindings } }),
    { model: tier.model, effort: tier.effort, phase: 'Review',
      label: r === 1 ? 'review:r1 (sweep completo)' : `review:r${r} (delta)`, schema: FINDINGS })

  if (!review) {
    rounds.push({ r, review: null, nota: 'revisor não respondeu' })
    break
  }

  const severe = (review.findings || []).filter(f => sevRank(f.severity) >= floor && !isAccepted(f, acceptedLimits))

  if (review.complete && severe.length === 0) {
    await anda(r, 'confirmando')
    const confirm = await agent(reviewPrompt({ round: r, acceptedLimits, invariants, scope: 'full', confirming: true }),
      { model: ARGS.model, effort: T.finalize.effort, phase: 'Confirm',
        label: `confirm:r${r}`, schema: FINDINGS })
    const confirmSevere = confirm ? (confirm.findings || []).filter(f => sevRank(f.severity) >= floor && !isAccepted(f, acceptedLimits)) : null
    if (confirm && confirm.complete && confirmSevere.length === 0) {
      rounds.push({ r, review, confirm, corrections: [], regressions: 0, alerts: [] })
      cleanRound = true; break
    }
    if (!confirm) {
      rounds.push({ r, review, confirm: null, nota: 'confirm-pass não respondeu — NÃO declaro rodada limpa' })
      break
    }
    review.findings = (review.findings || []).concat(confirm.findings || [])
  }

  await anda(r, 'planejando')
  const plan = await agent(planPrompt({ review, round: r, invariants, acceptedLimits }),
    { model: tier.model, effort: tier.effort, phase: 'Plan', label: `plan:r${r}`, schema: PLAN })

  if (!plan) {
    rounds.push({ r, review, plan: null, nota: 'planejador não respondeu' })
    break
  }

  const corrections = []; let regressions = 0
  if ((plan.bucket1 || []).length) await anda(r, `consertando (${plan.bucket1.length})`)
  for (const fix of (plan.bucket1 || []).slice().sort((a, b) => (a.order || 0) - (b.order || 0))) {
    const res = await agent(execPrompt({ fix, invariants }),
      { model: ARGS.model, effort: T.executor.effort, phase: 'Exec',
        label: `exec:${fix.id} (${fix.severity})`, schema: EXEC_RESULT })
    if (!res) { regressions++; continue }
    if (res.suiteRegressed) {
      const k = churnKey(fix)
      regressions++; churn[k] = (churn[k] || 0) + 1
      if (causaCache[k]) { causaDisputada.push({ fn: k, ...causaCache[k], deCache: true }); churnEscalated = true; break }
      if (churn[k] >= churnThreshold || fix.severity === 'P0') {
        let causa = null, desafio = null, acordo = false
        for (let volta = 1; volta <= 3 && !acordo; volta++) {
          causa = await agent(diagnosePrompt({ fix, churnCount: churn[k], desafioAnterior: desafio?.motivo || null }),
            { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose', label: `causa:${fix.id} v${volta}` })
          if (!causa) break
          desafio = await agent(desafioCausaPrompt({ fix, causa }),
            { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose', label: `desafia:${fix.id} v${volta}`, schema: DESAFIO })
          acordo = desafio ? desafio.procede === true : false
        }
        const desfecho = { fn: k, causa: acordo ? causa : null,
          disputa: acordo ? null : { investigador: String(causa || 'sem resposta').slice(0, 300),
                                     desafiador: String(desafio?.motivo || 'sem veredito').slice(0, 300) } }
        if (acordo) causaCache[k] = desfecho
        causaDisputada.push(desfecho)
        churnEscalated = true; break
      }
      log(`fix ${fix.id} regrediu a suíte — revertido, churn ${churn[k]}/${churnThreshold}`)
    } else {
      corrections.push(res)
      if (res.newInvariant) invariants.push(res.newInvariant)
    }
  }

  acceptedLimits = acceptedLimits.concat(plan.proposedLimits || [])
  touchedLastRound = corrections.flatMap(c => c.files_touched || [])
  openFindings = (review.findings || []).filter(f => !corrections.some(c => c.fix_id === f.id))
  rounds.push({ r, review, plan, corrections, regressions, alerts: plan.alerts || [], drift: plan.drift || [], rejected: plan.rejected || [] })
}

const voltasPorProblema = []
const porId = {}
for (const x of rounds)
  for (const f of ((x.review && x.review.findings) || [])) {
    if (!porId[f.id]) voltasPorProblema.push(porId[f.id] =
      { id: f.id, file: f.file, problem: f.problem, severity: f.severity, primeira: x.r, voltas: 0 })
    porId[f.id].voltas = x.r - porId[f.id].primeira + 1
  }

const tally = fs => (fs || []).reduce((a, f) => { a[f.severity] = (a[f.severity] || 0) + 1; return a }, {})

// ── ÚLTIMO ATO: apagar o sinal da barra ─────────────────────────────────────
// Vem DEPOIS de tudo e ANTES do return, então alcança TODO caminho de saída —
// rodada limpa, teto de rodadas, churn escalado, revisor ou planejador que não
// respondeu. A casca continua apagando também (Passo 8), e a barra varre o que
// passar dos dois (`andamento.py:expira_sinais`). Foram TRÊS camadas porque cada
// uma sozinha falha, e esta é a que faltava: sem ela, o sinal do qa-loop ficou
// aceso 9h26 depois do fim, medido em 2026-08-10.
if (ARGS.sessionId) {
  await agent(encerraPrompt({ motivo: cleanRound ? 'rodada limpa'
                                     : churnEscalated ? 'churn escalado' : 'teto de rodadas' }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Limpeza', label: 'encerra:barra' })
}

return {
  rounds: rounds.map(x => ({ r: x.r, complete: x.review?.complete,
    findings: (x.review?.findings || []).length, bySev: tally(x.review?.findings),
    corrections: (x.corrections || []).length, regressions: x.regressions || 0,
    alerts: (x.alerts || []).length, drift: (x.drift || []).length, rejected: (x.rejected || []).length,
    nota: x.nota })),
  detalhe: rounds,
  acceptedLimits, invariants, churn, voltasPorProblema, causaDisputada,
  planFlawAlerts: rounds.flatMap(x => x.alerts || []),
  driftItems: rounds.flatMap(x => x.drift || []),
  telemetry: rounds.map(x => ({ round: x.r, corrections: (x.corrections || []).length,
    regressions: x.regressions || 0, findings_by_sev: tally(x.review?.findings) })),
  stopReason: cleanRound ? 'no-severe-finding' : churnEscalated ? 'churn-escalated' : 'max-rounds',
}