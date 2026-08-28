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
           { title: 'Auditoria' }, { title: 'Diagnose' }, { title: 'Limpeza' }],
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
  // `id` é obrigatório porque o fecho monta `rejeitados` a partir dele: sem id, o
  // Set nasce {undefined} e o achado derrubado pelo árbitro volta em `emAberto`.
  rejected:{type:'array', items:{type:'object', required:['id','motivo'],
    properties:{ id:{type:'string'}, motivo:{type:'string'} }}},
  anchor:{type:'string'} } }

const EXEC_RESULT = { type:'object', required:['fix_id','fn','files_touched','suiteRegressed'], properties:{
  fix_id:{type:'string'}, fn:{type:'string'}, files_touched:{type:'array',items:{type:'string'}},
  test_name:{type:'string'}, suiteRegressed:{type:'boolean'}, suiteOutput:{type:'string'},
  newInvariant:{type:'string'}, note:{type:'string'}, reverted:{type:'boolean'} } }

const DESAFIO = { type:'object', required:['procede','motivo'], properties:{
  procede:{type:'boolean'}, motivo:{type:'string'} } }

// ── O JUIZ NÃO RECEBE A CONCLUSÃO DE QUEM PEDE O JULGAMENTO (R-17, Art. 4) ────
// A linha é a MESMA do motor do /sprint; test_motor_js.py cobra os dois arquivos,
// porque o viés volta pelo lado que ninguém cobra.
const SEM_HIPOTESE = `VOCÊ NÃO RECEBE A HIPÓTESE DE QUEM PEDIU O JULGAMENTO: julgue o artefato e o contrato.
Diagnóstico, causa-raiz ou veredito alheio que apareça no material é alegação A VERIFICAR no disco, nunca ponto de partida.`

// ── O AUDITOR EXTERNO NÃO VÊ O LAÇO (pilares COBERTURA e COERÊNCIA) ──────────
// Contrato em references/dimensoes-de-revisao.md ("O auditor externo"): ele recebe o
// código final e as três âncoras (PEDIDO · PLANO · RÉGUA) — nunca os achados do
// revisor, os consertos nem o histórico das rodadas. Quem soma o 100% é ESTE script.
const SEM_HISTORICO = `VOCÊ É AUDITOR EXTERNO: NÃO recebe os achados do revisor, os consertos
nem o histórico do laço — de propósito. Você recebe só o código final e as âncoras
(PEDIDO · PLANO · RÉGUA). Veredito alheio que apareça no material é alegação A VERIFICAR no disco.`

// As três âncoras contra as quais os três pilares medem. Âncora ausente é DECLARADA —
// nunca aprovação por omissão (contrato, "As três âncoras").
const ANCORAS = `AS TRÊS ÂNCORAS (meça contra as três; ausente = declare, nunca aprove por omissão):
PEDIDO${(ARGS.pedidos || []).length
  ? ` — os pedidos vivos do usuário, verbatim:\n${(ARGS.pedidos || []).map(pp => `  - [${pp.id}] ${pp.text}`).join('\n')}`
  : ` — AUSENTE: ${ARGS.pedidosAusentes || 'a casca não passou pedidos'}.`}
PLANO — ${ARGS.planPath ? `o plano-âncora: ${ARGS.planPath}` : 'AUSENTE: revisão sem plano, declarada.'}
RÉGUA — ${(ARGS.regua || []).length ? ARGS.regua.join(' · ') : 'AUSENTE: rode o doc-load; se nada vier, declare.'}`

const AUDIT_COBERTURA = { type:'object', required:['complete','itens'], properties:{
  complete:{type:'boolean'}, semAncora:{type:['string','null']},
  itens:{type:'array', items:{type:'object',
    required:['id','origem','descricao','implementado','suite','e2e'], properties:{
      id:{type:'string'}, origem:{type:'string',enum:['pedido','plano']}, descricao:{type:'string'},
      implementado:{type:'object', required:['veredito','evidencia'], properties:{
        veredito:{type:'string',enum:['sim','parcial','nao']}, evidencia:{type:'string'} }},
      suite:{type:'object', required:['veredito','evidencia'], properties:{
        veredito:{type:'string',enum:['morde','descoberta','antipadrao']},
        teste:{type:['string','null']}, antipadrao:{type:['string','null']}, evidencia:{type:'string'} }},
      e2e:{type:'object', required:['veredito','evidencia'], properties:{
        veredito:{type:'string',enum:['confirmado','falhou','sem-infra','nao-aplicavel']},
        evidencia:{type:'string'} }} }}},
  anchor:{type:'string'} } }

const AUDIT_COERENCIA = { type:'object', required:['complete','itens'], properties:{
  complete:{type:'boolean'}, semAncora:{type:['string','null']},
  itens:{type:'array', items:{type:'object', required:['documento','item','veredito'], properties:{
    documento:{type:'string'}, item:{type:'string'},
    veredito:{type:'string',enum:['conforme','violado','nao-aplicavel','nao-medido']},
    passagem:{type:['string','null']}, evidencia:{type:['string','null']} }}},
  foraDaConta:{type:'array', items:{type:'object', required:['documento','motivo'], properties:{
    documento:{type:'string'}, motivo:{type:'string',enum:['reaberto','minerado']} }}},
  anchor:{type:'string'} } }

// ── O PROJETO REVISADO NEM SEMPRE É ESTA CASA (2026-08-23) ───────────────────
// Stack, regras da casa e comando de suíte VÊM POR ARGS; o default é este
// repositório, então quem revisa o marketplace não vê diferença nenhuma.
//
// Cravados, eles diziam ao revisor de QUALQUER projeto que ele estava num
// marketplace de Markdown/Bash/Python sem build, e mandavam julgar contra sete
// regras (bump de plugin.json, sync-shared, subprocess...) que só existem aqui.
// Pior: o `find` por test_*.py do execPrompt, num projeto TypeScript, acha ZERO
// teste do módulo alterado — e ainda varre a suíte Python de módulos vizinhos,
// que é a armadilha que os CLAUDE.md de monorepo nomeiam ("vermelho de ambiente
// passando por vermelho de código"). Suíte que não coleta nada devolve "nenhum
// teste falhou", então `suiteRegressed` nascia false e o gate de regressão POR
// CONSERTO — o de maior retorno da skill — ficava cego parecendo verde.
// Medido em 2026-08-23: 5 sessões pós-arquivo, todas em projetos JS/TS, 44
// consertos aplicados e 0 regressões detectadas.
//
// O motor do /sprint já resolvia isto desde 2026-08-13 (`suiteCmd`, l.723 de lá);
// este ficou para trás — a MESMA assimetria que o comentário do topo narra, num
// outro eixo. Cobrador: test_qa_loop_motor.py (checagem F).
const STACK_PADRAO = 'Marketplace PÚBLICO de plugins do Claude Code. Markdown + Bash + Python 3 stdlib. SEM build, SEM CI.'
const REGRAS_PADRAO = [
  'Bump de plugin.json em toda mudança de plugin + espelho no .claude-plugin/marketplace.json (cobrador: scripts/cadeia_check.py --repo).',
  'Todo subprocess nasce com stdin=subprocess.DEVNULL e start_new_session=True (cobrador: scripts/vazamento_check.py).',
  'Nada de caminho absoluto de máquina, nome próprio do dono, e-mail pessoal ou credencial em arquivo rastreado (cobrador: scripts/public_repo_check.py).',
  'Caminho de plugin se resolve por NOME (lib/resolve-plugin.sh, lib/resolve-skill.sh), nunca escrito à mão.',
  'Editou _shared/? rode scripts/sync-shared.sh — as cópias vendoradas defasam.',
  'Contagem cravada em doc é acoplamento: entra o COMANDO que a produz (cobrador: scripts/desacoplamento_check.py).',
  'Estado mutável vai em ~/.claude/, nunca dentro do plugin.',
]
const stack = ARGS.stack || STACK_PADRAO
const regrasDaCasa = (ARGS.regrasDaCasa && ARGS.regrasDaCasa.length) ? ARGS.regrasDaCasa : REGRAS_PADRAO
// null = sem declaração; o execPrompt cai no `find` E manda conferir se ele cobre o
// que foi tocado. A casca lê este comando do CLAUDE.md do projeto e o passa literal.
const suiteCmd = ARGS.suiteCmd || null

const CONTEXTO = `REPOSITÓRIO: ${RAIZ}
${stack}

A RÉGUA DESTE PROJETO (abra e leia — não confie neste resumo):
${(ARGS.regua || []).map(r => `- ${r}`).join('\n')}
Documento minerado vale como MAPA, nunca como régua.

REGRAS DA CASA (resumo; o CLAUDE.md do projeto manda):
${regrasDaCasa.map(r => `- ${r}`).join('\n')}

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
Gerar não é julgar — o Revisor achou, VOCÊ carimba a severidade. Finding rejeitado vai em \`rejected\` com o \`id\` dele e o motivo.
EXCEÇÃO — finding com id \`AUD-*\` vem da auditoria externa dos pilares (a conta é do
script, booleana): você NÃO o rebaixa e NÃO o rejeita — roteie TODOS ao bucket1.

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
3. RODE A SUÍTE INTEIRA do repositório, não só o teste novo —
${suiteCmd
  ? `   o COMANDO DECLARADO DA CASA, literal, e SÓ ele:\n\n     ${suiteCmd}\n\n   Não amplie, não substitua, não troque por um \`find\` seu: num monorepo, varrer a\n   raiz roda a suíte de módulos que esta mudança não toca e faz vermelho de ambiente\n   passar por vermelho de código.`
  : `   a que o projeto declara (CLAUDE.md, Makefile, package.json, pyproject.toml); sem\n   declaração, a LISTA sai deste comando:\n\n     for t in $(find ${RAIZ} -path '*/node_modules' -prune -o -path '*/.git' -prune -o \\( -name 'test_*.py' -o -name 'test_*.sh' \\) -print | sort); do ... done\n\n   ANTES de aceitar essa lista, CONFIRA que ela cobre os arquivos que você tocou. Se\n   ela vier vazia para eles, ela NÃO é a suíte deste projeto: ache a declarada e use-a.\n   Lista vazia devolve "nenhum teste falhou", e aí \`suiteRegressed\` mente verde.`}
   Some os resultados. \`suiteRegressed\` = true se QUALQUER teste que passava antes falhou agora.
4. SUÍTE VERMELHA POR SUA CAUSA ⇒ DESFAÇA VOCÊ MESMO. Se \`suiteRegressed\` for true, REVERTA sua própria
   edição — todo arquivo que você tocou, o teste novo inclusive — ANTES de responder, e devolva
   \`reverted: true\`. Ninguém desfaz por você: sem \`reverted: true\` o laço registra que a edição
   quebrada FICOU DE PÉ na árvore e precisa de decisão do dono.
5. REGRAS DA CASA que valem no conserto:
${regrasDaCasa.map(r => `   - ${r}`).join('\n')}

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

const auditCoberturaPrompt = () => `PAPEL: AUDITOR DE COBERTURA (pilar 2)
${SEM_HISTORICO}

${ANCORAS}

REPOSITÓRIO: ${RAIZ}
${stack}
O ALVO (o código final sob auditoria): ${ARGS.target}
DIFF: rode \`git -C ${RAIZ} diff ${ARGS.diffRef}\`.

COBERTURA NÃO É SÓ TESTE — é implementação COMPLETA (contrato: as cinco lentes).
ENUMERE TODO item do escopo a partir das âncoras (cada finalidade/requisito do PEDIDO e
do PLANO que o alvo devia entregar). Para CADA item, meça TRÊS lentes no disco:
- implementado — o código do item existe e faz o que o item pede? \`sim\` | \`parcial\` | \`nao\`.
- suite — existe teste que MORDE o item? \`morde\` | \`descoberta\` (sem teste) | \`antipadrao\`
  (teste que existe e não morde — os cinco antipadrões de antipadroes-de-teste.md). Nas
  travas de segurança, a prova é MUTAÇÃO: desligue numa cópia e exija que a suíte acuse.
- e2e — EXECUTE a confirmação direta do funcionamento esperado: interface = a jornada real
  (Playwright, olhando o RESULTADO na tela, não só o DOM); CLI/biblioteca = rode o programa
  real de ponta a ponta. \`confirmado\` | \`falhou\` | \`sem-infra\` (não há como executar
  neste projeto) | \`nao-aplicavel\` (item sem comportamento executável — diga o motivo).
As lentes "revisado" e "auditado" são conta DESTE script, não sua.
\`evidencia\` de cada lente: o que você rodou/leu, literal (comando + saída, arquivo:linha).
Sem NENHUMA âncora (nem pedido, nem plano, nem régua): \`semAncora\` com o motivo, itens [].
\`anchor\` = a última linha não vazia do último arquivo que você leu, literal.`

const auditCoerenciaPrompt = () => `PAPEL: AUDITOR DE COERÊNCIA (pilar 3)
${SEM_HISTORICO}

${ANCORAS}

REPOSITÓRIO: ${RAIZ}
${stack}
O ALVO (o código final sob auditoria): ${ARGS.target}
DIFF: rode \`git -C ${RAIZ} diff ${ARGS.diffRef}\`.

PERCORRA A RÉGUA INTEIRA, ITEM A ITEM — artigo por artigo, restrição por restrição,
seção por seção de CADA documento que a régua lista. Rode o doc-load do projeto quando a
lista acima não bastar. Para cada item: \`conforme\` | \`violado\` (cite a \`passagem\` e a
\`evidencia\` no código) | \`nao-aplicavel\` (com o motivo em \`evidencia\`) | \`nao-medido\`
(não conseguiu medir — diga por quê; NUNCA omita o item da lista).
Documento REABERTO ou MINERADO não entra na conta: vai em \`foraDaConta\` com o motivo.
As restrições do PEDIDO (o que o usuário mandou NÃO mexer) também são itens: confira que
o alvo as respeitou.
Sem régua E sem pedido: \`semAncora\` com o motivo, itens [].
\`anchor\` = a última linha não vazia do último arquivo que você leu, literal.`

const sevRank = s => ({P0:3, P1:2, P2:1, P3:0}[s] ?? 0)
const floor = sevRank(ARGS.severityFloor || 'P1')
// RATIFICADO ≠ PROPOSTO (2026-08-24). `acceptedLimits` é SÓ o que o dono já gravou em
// `.claude/qa-loop.config.md` e chega por args — é a lista que os dois filtros consultam
// (o de `severe`, que libera a rodada limpa, e o do fecho, que monta `emAberto`).
// O que o planejador propõe fica AQUI, separado, e sai no `return` como proposta: engordar
// a de cima dentro da corrida dava ao planejador o poder de aposentar o próprio achado —
// ele propunha o limite e, da rodada seguinte em diante, o mesmo P1 sumia dos dois filtros
// e a corrida fechava verde sem ninguém ter ratificado nada.
const acceptedLimits = ARGS.acceptedLimits || []
const proposedLimits = []
let invariants = ARGS.invariants || []
const churn = {}
const causaCache = {}
const causaDisputada = []
const churnKey = fix => `${fix.file || '?'}:${fix.fn || '?'}`
const rounds = []
let cleanRound = false, churnEscalated = false, teatroDeDuvida = false, r = 0, rodadasSemConserto = 0
let regressaoTotal = false, rodadasSoRegressao = 0
let touchedLastRound = [], openFindings = []

// ── ARTIGO 14 · A ASSÍNTOTA É DE SEVERIDADE, NUNCA DE GASTO ──────────────────
// `cleanRound` é o ÚNICO desfecho que é sucesso, e ele é ASSINTÓTICO: rodada
// completa sem nenhum achado ACIMA DO PISO (`severityFloor`), com o confirm-pass
// independente concordando. Achado abaixo do piso não segura o laço — é preciosismo
// que não afeta consistência nem funcionamento, e exigir zero obrigaria a rebaixar
// achado para poder fechar, que é fraudar o próprio critério.
//
// Os outros dois desfechos (`max-rounds`, `churn-escalated`) são FALHA — o `return`
// os devolve com `sucesso: false` e a lista do que ficou acima do piso, e a casca NÃO
// pode apresentá-los como revisão feita.
//
// SEM TETO POR DEFAULT (era 12; o dono cortou em 2026-08-23: "o que NÃO pode ter é o
// teto por gasto de rodadas ou tokens"). `maxRounds` só existe quando quem invoca passa
// um, como freio de emergência para laço preso em defeito de ambiente. O clamp por
// camada de rede abaixo NÃO é gasto: sem suíte, cada fix é aposta cega e mais voltas
// multiplicam o ESTRAGO — é risco, e por isso sobrevive ao artigo.
const LAYER_CAP = { 4: 2, 5: 1 }
const churnThreshold = ARGS.churnThreshold || 2
const capDaCamada = LAYER_CAP[ARGS.safetyLayer]
const maxRounds = Math.min(ARGS.maxRounds || Infinity, capDaCamada ?? Infinity)
// Quem foi que limitou? O veredito do fecho não pode chamar o clamp de "freio":
// freio é gasto, clamp é risco de estrago, e trocar um pelo outro apaga a causa.
const limitePorCamada = capDaCamada !== undefined && capDaCamada <= (ARGS.maxRounds || Infinity)
const T = ARGS.tiers
const tierFor = round => ({ model: ARGS.model, effort: round === 1 ? T.decompose.effort : T.coordinate.effort })
const isAccepted = (f, limits) => (limits || []).some(l => (l.id && l.id === f.id) || (l.file && l.file === f.file && l.problem === f.problem))

// ── PILARES 2 e 3 · a conta do 100% é DESTE script, nunca do auditor ─────────
// Dispensa de lente é RATIFICAÇÃO do dono (qa-loop.config.md → args), mesma porta dos
// acceptedLimits: o laço nunca dispensa sozinho para poder fechar.
const lentesDispensadas = ARGS.lentesDispensadas || []
const furosDe = it => {
  const f = []
  if (it.implementado.veredito !== 'sim') f.push('implementado')
  if (it.suite.veredito !== 'morde') f.push('suite')
  if (!['confirmado', 'nao-aplicavel', 'sem-infra'].includes(it.e2e.veredito)) f.push('e2e')
  if (!(it.implementado.evidencia && it.suite.evidencia && it.e2e.evidencia)) f.push('auditado')
  return f.filter(l => !lentesDispensadas.includes(l)).map(lente => ({ item: it.id, lente, descricao: it.descricao }))
}
let auditCob = null, auditCoe = null
let cobStatus = 'nao-rodou', coeStatus = 'nao-rodou'
let furosCobertura = [], violadosCoerencia = [], auditoriaNaoMedida = false
let audSeq = 0

while (!cleanRound && r < maxRounds && !churnEscalated && !teatroDeDuvida) {
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
    // O confirm-pass entra na MESMA lista da rodada, inclusive quando ela fecha limpa:
    // o fecho varre `review.findings`, e achado abaixo do piso some do bloqueio, nunca da vista.
    if (confirm) review.findings = (review.findings || []).concat(confirm.findings || [])
    if (confirm && confirm.complete && confirmSevere.length === 0) {
      // ── AUDITORIA EXTERNA (pilares COBERTURA e COERÊNCIA) ──────────────────
      // A rodada limpa é CANDIDATA a fecho, não fecho: os dois auditores isolados
      // rodam aqui, e quem soma o 100% é este script. Reprovou → os furos viram
      // findings e o laço reabre; código que mudou é veredito vencido, então o
      // próximo candidato re-audita do zero.
      await anda(r, 'auditando')
      auditCob = await agent(auditCoberturaPrompt(),
        { model: ARGS.model, effort: T.finalize.effort, phase: 'Auditoria',
          label: `audit:cobertura r${r}`, schema: AUDIT_COBERTURA })
      auditCoe = await agent(auditCoerenciaPrompt(),
        { model: ARGS.model, effort: T.finalize.effort, phase: 'Auditoria',
          label: `audit:coerencia r${r}`, schema: AUDIT_COERENCIA })
      if (!auditCob || !auditCoe) {
        rounds.push({ r, review, confirm, auditCob, auditCoe,
          nota: 'auditor externo não respondeu — NÃO declaro rodada limpa' })
        break
      }
      if (!auditCob.complete || !auditCoe.complete) {
        rounds.push({ r, review, confirm, auditCob, auditCoe,
          nota: 'auditoria externa incompleta — NÃO declaro rodada limpa' })
        break
      }

      const itensCob = auditCob.itens || []
      const itensCoe = auditCoe.itens || []
      furosCobertura = auditCob.semAncora ? [] : itensCob.flatMap(furosDe)
      violadosCoerencia = auditCoe.semAncora ? []
        : itensCoe.filter(i => i.veredito === 'violado' || i.veredito === 'nao-medido')
      const semInfraE2E = !auditCob.semAncora && !lentesDispensadas.includes('e2e')
        && itensCob.some(it => it.e2e.veredito === 'sem-infra')
      // Auditor que não enumerou nada não auditou — lista vazia COM âncora reprova.
      const cobVazia = !auditCob.semAncora && itensCob.length === 0
      const coeVazia = !auditCoe.semAncora && itensCoe.length === 0

      cobStatus = auditCob.semAncora ? 'sem-ancora'
        : (furosCobertura.length || cobVazia) ? 'reprovada'
        : semInfraE2E ? 'nao-medida-lente-e2e' : 'aprovada'
      coeStatus = auditCoe.semAncora ? 'sem-ancora'
        : (violadosCoerencia.length || coeVazia) ? 'reprovada' : 'aprovada'

      // Furo consertável vira finding e o laço reabre — fila de conserto normal.
      const audFindings = []
      for (const fu of furosCobertura)
        audFindings.push({ id: `AUD-C${++audSeq}`, file: fu.item, line: null, severity: 'P1',
          dimension: 'auditoria-cobertura',
          problem: `item "${fu.descricao || fu.item}" com a lente ${fu.lente} furada`,
          fix_direction: fu.lente === 'suite' ? 'escreva o teste que morde o item'
            : fu.lente === 'e2e' ? 'faça a jornada real confirmar o funcionamento esperado'
            : 'complete a implementação do item' })
      for (const vi of violadosCoerencia)
        audFindings.push({ id: `AUD-K${++audSeq}`, file: vi.documento, line: null, severity: 'P1',
          dimension: 'auditoria-coerencia',
          problem: `${vi.documento} · "${vi.item}": ${vi.veredito}${vi.passagem ? ` — ${vi.passagem}` : ''}`,
          fix_direction: vi.veredito === 'violado' ? 'conserte o código até conformar com o item'
            : 'meça o item e traga a prova' })
      if (cobVazia) audFindings.push({ id: `AUD-C${++audSeq}`, file: '(escopo)', line: null,
        severity: 'P1', dimension: 'auditoria-cobertura',
        problem: 'auditor de cobertura devolveu zero itens com âncora presente — não auditou',
        fix_direction: 're-audite enumerando o escopo das âncoras' })
      if (coeVazia) audFindings.push({ id: `AUD-K${++audSeq}`, file: '(régua)', line: null,
        severity: 'P1', dimension: 'auditoria-coerencia',
        problem: 'auditor de coerência devolveu zero itens com régua presente — não auditou',
        fix_direction: 're-audite percorrendo a régua item a item' })

      if (audFindings.length) {
        review.findings = (review.findings || []).concat(audFindings)
      } else if (semInfraE2E) {
        // Não há conserto de executor para infra ausente: girar o laço seria teatro.
        // Fecha DECLARADO — "COBERTURA NÃO MEDIDA NA LENTE E2E" — e a decisão é do
        // dono: ratificar a dispensa no qa-loop.config.md ou mandar criar a infra.
        rounds.push({ r, review, confirm, auditCob, auditCoe, corrections: [], regressions: 0, alerts: [] })
        auditoriaNaoMedida = true; break
      } else {
        rounds.push({ r, review, confirm, auditCob, auditCoe, corrections: [], regressions: 0, alerts: [] })
        cleanRound = true; break
      }
    }
    if (!confirm) {
      rounds.push({ r, review, confirm: null, nota: 'confirm-pass não respondeu — NÃO declaro rodada limpa' })
      break
    }
  }

  await anda(r, 'planejando')
  const plan = await agent(planPrompt({ review, round: r, invariants, acceptedLimits }),
    { model: tier.model, effort: tier.effort, phase: 'Plan', label: `plan:r${r}`, schema: PLAN })

  if (!plan) {
    rounds.push({ r, review, plan: null, nota: 'planejador não respondeu' })
    break
  }

  // Garantia do script (não da prosa): finding AUD-* fora do bucket1 volta para ele.
  // O gate dos pilares é booleano do script — o árbitro não tem alçada sobre ele.
  for (const f of (review.findings || []).filter(x => /^AUD-/.test(x.id))) {
    if (!(plan.bucket1 || []).some(b => b.id === f.id)) {
      plan.bucket1 = plan.bucket1 || []
      plan.bucket1.push({ id: f.id, fn: '?', file: f.file, severity: f.severity,
        order: plan.bucket1.length + 1000, fix_direction: f.fix_direction })
      plan.rejected = (plan.rejected || []).filter(rj => rj.id !== f.id)
    }
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
      // QUEM DESFAZ É O EXECUTOR, E SÓ ELE SABE SE DESFEZ (2026-08-24). Nada aqui reverte
      // arquivo; enquanto isto logava "revertido", a edição quebrada ficava na árvore e se
      // empilhava rodada após rodada — sem teto por default, para sempre — com o operador
      // lendo o contrário. A afirmação agora depende da confirmação do `execPrompt`.
      log(res.reverted
        ? `fix ${fix.id} regrediu a suíte — o executor desfez a própria edição, churn ${churn[k]}/${churnThreshold}`
        : `fix ${fix.id} regrediu a suíte e a edição FICOU DE PÉ (o executor não confirmou ter desfeito) — precisa de decisão, churn ${churn[k]}/${churnThreshold}`)
    } else {
      corrections.push(res)
      if (res.newInvariant) invariants.push(res.newInvariant)
    }
  }

  proposedLimits.push(...(plan.proposedLimits || []))
  touchedLastRound = corrections.flatMap(c => c.files_touched || [])
  openFindings = (review.findings || []).filter(f => !corrections.some(c => c.fix_id === f.id))
  rounds.push({ r, review, plan, corrections, regressions, alerts: plan.alerts || [], drift: plan.drift || [], rejected: plan.rejected || [] })

  // ── TEATRO DE DÚVIDA · duas rodadas com achado e ZERO conserto ──────────────
  // Quem conta é o MOTOR, não a casca: o Workflow é um só e a casca só vê `rounds`
  // depois do return — na hora em que a terceira rodada já teria sido paga. Não
  // fere o Artigo 14: não é parar por esforço, é parar porque o laço deixou de
  // produzir conserto (achado sai todo para drift/alerts/limite/P2). Sem isto, com
  // `maxRounds` = Infinity o mesmo P1 roteado para drift volta em `openFindings`
  // toda rodada e o laço não tem saída.
  // Conta rodada SEM CONSERTO, com ou sem achado: exigir achado fazia o contador
  // zerar quando o revisor devolvia lista vazia sem `complete`, e aí nada quebrava
  // o `while` (medido: 51 rodadas). Rodada estéril é ainda menos produtiva que
  // rodada com achado e zero conserto. A rodada limpa não passa por aqui — sai por
  // `cleanRound` antes.
  rodadasSemConserto = corrections.length === 0 ? rodadasSemConserto + 1 : 0
  // Rodada em que TODO conserto tentado REGREDIU a suíte NÃO é o laço deixando de
  // atacar — ele atacou e quebrou. Conserto que regride some de `corrections` (só o
  // ramo `else` empurra), então a rodada caía no contador acima e o dono lia "NENHUM
  // virou conserto", o diagnóstico invertido. Com dois fixes regredindo em funções
  // DIFERENTES o churn fica 1/2 em cada chave e `churnEscalated` não pega. Desfecho
  // próprio, que nomeia a suíte quebrada.
  rodadasSoRegressao = (corrections.length === 0 && regressions > 0) ? rodadasSoRegressao + 1 : 0
  if (rodadasSoRegressao >= 2) regressaoTotal = true
  if (rodadasSemConserto >= 2) teatroDeDuvida = true
}

// ── ABANDONO POR AGENTE MUDO ≠ FREIO DE RODADAS (2026-08-24) ────────────────
// Sem teto por default, `r < Infinity` nunca falha: os três `break` de agente que
// não respondeu eram os ÚNICOS que chegavam ao desfecho `max-rounds`, e o relatório
// saía culpando "o freio de Infinity rodada(s)". A `nota` que a própria rodada já
// gravou é o motivo — só ela existe nesses três caminhos.
const agenteMudo = (rounds.length && rounds[rounds.length - 1].nota) || null

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
                                     : auditoriaNaoMedida ? 'cobertura não medida (lente E2E)'
                                     : churnEscalated ? 'churn escalado'
                                     : regressaoTotal ? 'conserto regrediu a suíte'
                                     : teatroDeDuvida ? 'teatro de dúvida'
                                     : agenteMudo || 'teto de rodadas' }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Limpeza', label: 'encerra:barra' })
}

// ── O QUE FICOU DE PÉ, EM DUAS LISTAS (Artigo 14) ───────────────────────────
// A assíntota é de severidade, então o que sobra se separa em DOIS destinos, e
// confundi-los é o defeito que este bloco existe para impedir:
//   · `emAberto`  — ACIMA do piso e ainda de pé (nem consertado, nem rejeitado pelo
//                   árbitro, nem coberto por limite aceito). A casca abre o relatório
//                   com esta lista. ATENÇÃO: ela pode ter item MESMO na rodada limpa —
//                   `drift` e `alerts` são destinos legítimos, e o achado que sai por
//                   eles não vira conserto e não reaparece na rodada seguinte. Por isso
//                   o veredito de sucesso NUNCA afirma "nenhum achado" sem conferir esta
//                   lista: quando ela tem item, ele conta quantos ficaram na mesa do dono.
//   · `abaixoDoPiso` — preciosismo que não afeta consistência nem funcionamento.
//                   NÃO segura o fecho, mas é LISTADO: some do bloqueio, nunca da
//                   vista. Enterrar isto em silêncio seria o outro extremo do erro.
const consertados = new Set(rounds.flatMap(x => (x.corrections || []).map(c => c.fix_id)))
const rejeitados = new Set(rounds.flatMap(x => (x.rejected || []).map(f => f.id)))
const emAberto = []
const abaixoDoPiso = []
const jaListado = new Set()
for (const x of rounds)
  for (const f of ((x.review && x.review.findings) || [])) {
    if (consertados.has(f.id) || rejeitados.has(f.id) || jaListado.has(f.id)) continue
    if (isAccepted(f, acceptedLimits)) continue
    jaListado.add(f.id)
    const item = { id: f.id, file: f.file, line: f.line, severity: f.severity,
                   problem: f.problem, fix_direction: f.fix_direction, vistoNaRodada: x.r }
    if (sevRank(f.severity) >= floor) emAberto.push(item)
    else abaixoDoPiso.push(item)
  }

return {
  rounds: rounds.map(x => ({ r: x.r, complete: x.review?.complete,
    findings: (x.review?.findings || []).length, bySev: tally(x.review?.findings),
    corrections: (x.corrections || []).length, regressions: x.regressions || 0,
    alerts: (x.alerts || []).length, drift: (x.drift || []).length, rejected: (x.rejected || []).length,
    nota: x.nota })),
  detalhe: rounds,
  acceptedLimits, proposedLimits, invariants, churn, voltasPorProblema, causaDisputada,
  // Os três pilares (contrato em references/dimensoes-de-revisao.md). A conta do 100%
  // dos pilares 2-3 é deste script; o auditor só mede. Âncora ausente sai declarada.
  pilares: {
    qualidade: { status: cleanRound ? 'assintota-alcancada' : 'nao-fechou' },
    cobertura: { status: cobStatus, furos: furosCobertura,
                 dispensadas: lentesDispensadas,
                 itens: (auditCob && auditCob.itens || []).length,
                 semAncora: (auditCob && auditCob.semAncora) || null },
    coerencia: { status: coeStatus, violados: violadosCoerencia,
                 foraDaConta: (auditCoe && auditCoe.foraDaConta) || [],
                 itens: (auditCoe && auditCoe.itens || []).length,
                 semAncora: (auditCoe && auditCoe.semAncora) || null },
  },
  planFlawAlerts: rounds.flatMap(x => x.alerts || []),
  driftItems: rounds.flatMap(x => x.drift || []),
  telemetry: rounds.map(x => ({ round: x.r, corrections: (x.corrections || []).length,
    regressions: x.regressions || 0, findings_by_sev: tally(x.review?.findings) })),
  stopReason: cleanRound ? 'no-severe-finding'
    : auditoriaNaoMedida ? 'cobertura-nao-medida'
    : churnEscalated ? 'churn-escalated'
    : regressaoTotal ? 'regressao-total'
    : teatroDeDuvida ? 'teatro-de-duvida' : agenteMudo ? 'agente-mudo' : 'max-rounds',
  // Artigo 14: só a rodada limpa (assíntota de severidade alcançada) é sucesso. Teto e
  // churn são FALHA, e a casca as reporta como "a revisão NÃO terminou", com `emAberto`
  // na frente do relatório. `abaixoDoPiso` acompanha SEMPRE, inclusive no sucesso.
  sucesso: cleanRound === true,
  severityFloor: ARGS.severityFloor || 'P1',
  emAberto,
  abaixoDoPiso,
  vereditoHumano: cleanRound
    ? (emAberto.length
        ? `rodada limpa, mas ${emAberto.length} achado(s) acima do piso ficaram na mesa do dono (roteados para plano/drift, não consertados)`
        : `nenhum achado acima de ${ARGS.severityFloor || 'P1'}`) +
      (abaixoDoPiso.length ? ` · ${abaixoDoPiso.length} abaixo do piso, listados e não bloqueantes` : '') +
      ` · auditoria externa: cobertura ${cobStatus}, coerência ${coeStatus}` +
      (lentesDispensadas.length ? ` (lente(s) ${lentesDispensadas.join(', ')} dispensada(s) por ratificação do dono)` : '')
    : auditoriaNaoMedida
      ? `COBERTURA NÃO MEDIDA NA LENTE E2E — o projeto não tem como executar a confirmação direta; ratifique a dispensa no qa-loop.config.md ou mande criar a infra (coerência: ${coeStatus})`
    : churnEscalated
      ? 'A REVISÃO NÃO TERMINOU — o mesmo ponto regrediu a cada tentativa e a investigação de causa assumiu'
      : regressaoTotal
        ? `A REVISÃO NÃO TERMINOU — em duas rodadas seguidas TODO conserto tentado quebrou a suíte (o laço atacou, não desistiu), com ${emAberto.length} achado(s) acima do piso ainda de pé`
      : teatroDeDuvida
        ? `A REVISÃO NÃO TERMINOU — duas rodadas seguidas acharam problema e NENHUM virou conserto (teatro de dúvida), com ${emAberto.length} achado(s) acima do piso na mesa do dono`
        : agenteMudo
          ? `A REVISÃO NÃO TERMINOU — ${agenteMudo}, com ${emAberto.length} achado(s) acima do piso ainda de pé`
          // Só sobram estes quando `maxRounds` é finito: com o default Infinity, `r < maxRounds`
          // nunca falha e a saída sem conserto é sempre um dos casos acima. E são DOIS,
          // porque quem limitou muda a causa: o clamp da camada de rede é RISCO (sem suíte
          // o conserto não tem prova), o teto de quem invoca é freio de emergência.
          : limitePorCamada
            ? `A REVISÃO NÃO TERMINOU — a rede de segurança deste projeto é Camada ${ARGS.safetyLayer}, então cada conserto é aposta cega e mais voltas multiplicam o ESTRAGO: o laço parou em ${maxRounds} rodada(s) por RISCO, não por gasto, com ${emAberto.length} achado(s) acima do piso ainda de pé`
            : `A REVISÃO NÃO TERMINOU — o freio de ${maxRounds} rodada(s) agiu com ${emAberto.length} achado(s) acima do piso ainda de pé`,
}