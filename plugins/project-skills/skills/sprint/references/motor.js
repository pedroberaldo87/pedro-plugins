// motor.js — o script COMPLETO do motor do /sprint, pronto para a tool Workflow.
//
// POR QUE ESTE ARQUIVO EXISTE (decisão do dono, 2026-08-09): o esqueleto do motor
// mora no SKILL.md, mas os textos que cada agente recebe (os prompts) e os contratos
// de resposta (os schemas) só existiam em PROSA — e a casca os traduzia em código a
// cada disparo, 436 linhas por vez. Uma dessas traduções foi guardada em rascunho,
// sobreviveu ao rename do plugin e rodou com o nome velho sem nada acusar.
// Agora o disparo passa `scriptPath` apontando para ESTE arquivo, resolvido por nome
// (resolve-plugin.sh project-skills skills/sprint/references/motor.js) — nunca
// copiado para rascunho, nunca redigitado.
//
// Quem cobra que este arquivo não divirja do SKILL.md é lib/test_motor_js.py:
// as peças do esqueleto, os PAPEL: declarados e a constante T contra r8-tiers.json.

export const meta = {
  name: 'sprint-build-engine',
  description: 'Motor de implementação: tier por etapa (R8) — decompose/coordinate/executor/mechanical/diagnose/finalize',
  phases: [{ title: 'Decompor' }, { title: 'Diagnose' }, { title: 'Executar' },
           { title: 'Revisar' }, { title: 'Suíte' }, { title: 'Marcar' },
           { title: 'Salvar' }, { title: 'Doc' }, { title: 'Limpeza' }, { title: 'Confirmar' }],
}

// O parâmetro pode chegar TEXTO (JSON serializado) em vez de objeto — quando isso
// aconteceu, todo campo lido dele virou undefined e o motor morreu na 1ª volta sem
// dizer por quê. Converte ANTES de usar, e o resto do script só fala com ARGS.
const ARGS = typeof args === 'string' ? JSON.parse(args) : args
const RAIZ = ARGS.repoRoot
// Os resolvedores chegam por args porque o repositório do dono NÃO é este marketplace:
// instalado, project-skills mora no cache de plugins, e caminho cravado a partir de
// RAIZ só funcionaria aqui. A casca resolve e passa; o fallback cobre o próprio repo.
const RESOLVE = ARGS.resolvePlugin || `${RAIZ}/plugins/project-skills/lib/resolve-plugin.sh`
const RESOLVE_SKILL = ARGS.resolveSkill || `${RAIZ}/plugins/project-skills/lib/resolve-skill.sh`
const RESOLVE_SPRINT = ARGS.resolveSprintPlugin || `${RAIZ}/plugins/project-skills/skills/sprint/resolve-plugin.sh`

// ───────────────────────── SCHEMAS ─────────────────────────
const DECOMP = { type: 'object', required: ['tasks'], properties: {
  tasks: { type: 'array', items: { type: 'object',
    required: ['id', 'desc', 'requisito', 'pronto', 'files', 'parallelizable', 'done'],
    properties: { id: {type:'string'}, desc: {type:'string'}, requisito: {type:'string'},
      pronto: {type:'string'}, files: {type:'array', items:{type:'string'}},
      parallelizable: {type:'boolean'}, dependsOn: {type:'array', items:{type:'string'}},
      done: {type:'boolean'}, complexity: {type:'string', enum:['standard','mechanical']},
      esperaDono: {type:'string'}, protegido: {type:'string'} } } },
  blockers: { type: 'array', items: { type:'object', required:['what','whyNeedsYou'],
    properties:{ what:{type:'string'}, whyNeedsYou:{type:'string'}, taskId:{type:'string'}, kind:{type:'string'} } } } } }

const TASK_RESULT = { type:'object', required:['task_id','files_touched','summary','done'], properties:{
  task_id:{type:'string'}, files_touched:{type:'array',items:{type:'string'}}, summary:{type:'string'},
  done:{type:'boolean'}, note:{type:'string'}, anchor:{type:'string'}, espera:{type:'boolean'},
  impossivel:{type:'string'}, ferramentas:{type:'array',items:{type:'string'}},
  proposta:{type:'object', properties:{ arquivo:{type:'string'}, antes:{type:'string'}, depois:{type:'string'} }} } }

const BUILD_REVIEW = { type:'object', required:['complete','cohesive','gaps','missingTasks','anchor'], properties:{
  complete:{type:'boolean'}, cohesive:{type:'boolean'},
  gaps:{type:'array',items:{type:'object',required:['kind','severity','problem'],properties:{
    task_id:{type:['string','null']}, kind:{type:'string',enum:['spec','constituicao','concepcao','rastreio','completude','coesao']},
    severity:{type:'string',enum:['P0','P1','P2','P3']}, problem:{type:'string'} }}},
  missingTasks:{type:'array',items:{type:'string'}}, lawMark:{type:['string','null']}, anchor:{type:'string'} } }

const TAREFA_REVIEW = { type:'object', required:['aprova','gaps','anchor'], properties:{
  aprova:{type:'boolean'},
  gaps:{type:'array',items:{type:'object',required:['kind','severity','problem'],properties:{
    kind:{type:'string'}, severity:{type:'string',enum:['P0','P1','P2','P3']}, problem:{type:'string'} }}},
  anchor:{type:'string'} } }

const DOC_REVIEW = { type:'object', required:['ok','consertados','gaps','anchor'], properties:{
  ok:{type:'boolean'}, consertados:{type:'array',items:{type:'string'}},
  gaps:{type:'array',items:{type:'object',required:['arquivo','problem','autoral'],properties:{
    arquivo:{type:'string'}, problem:{type:'string'}, autoral:{type:'boolean'} }}},
  anchor:{type:'string'} } }

const AUDITOR = { type:'object', required:['derruba','motivo','naoTentou','anchor'], properties:{
  derruba:{type:'boolean'}, motivo:{type:'string'}, naoTentou:{type:'array',items:{type:'string'}}, anchor:{type:'string'} } }

const SAUDE = { type:'object', required:['fechada'], properties:{
  fechada:{type:'boolean'}, motivo:{type:'string'}, saida:{type:'string'} } }

const DESAFIO = { type:'object', required:['procede','motivo','anchor'], properties:{
  procede:{type:'boolean'}, motivo:{type:'string'},
  escopo:{type:'string',enum:['tarefa','repositorio']}, anchor:{type:'string'} } }

// Todo campo daqui tem linha correspondente no `runSuitePrompt`. `heartbeat` saiu em
// 2026-08-10: era um número sem descrição no prompt, o agente preencheu com `1` (o valor
// mais barato) e o vigia leu 56 anos de silêncio. Campo em schema que o prompt não
// descreve é convite a valor inventado — vale para todos os schemas deste motor.
const SUITE_RESULT = { type:'object', required:['green','failing'], properties:{
  green:{type:'boolean'}, failing:{type:'array',items:{type:'string'}}, placar:{type:'string'},
  trabalhoVivo:{type:'boolean'} } }

const REGUA = { type:'object', required:['reprovados'], properties:{
  reprovados:{type:'array',items:{type:'object',required:['task_id','motivo'],properties:{
    task_id:{type:'string'}, motivo:{type:'string'} }}} } }

const RESERVA = { type:'object', required:['recusado'], properties:{
  recusado:{type:'boolean'}, arquivos:{type:'array',items:{type:'string'}} } }

const TICK_RESULT = { type:'object', required:['marcados'], properties:{
  marcados:{type:'array',items:{type:'object',required:['task_id','ok'],properties:{
    task_id:{type:'string'}, ok:{type:'boolean'}, motivo:{type:'string'} }}} } }

const DOC_TOUCH = { type:'object', required:['docs'], properties:{
  docs:{type:'array',items:{type:'string'}} } }

// ───────────────────────── PROMPTS ─────────────────────────
const J = o => JSON.stringify(o, null, 1)

// A régua do projeto vem da CASCA (o doc-load roda antes do disparo e passa `regua`
// em args). Sem ela, a instrução é genérica e fail-open: régua ausente não é achado.
const REGUA_DO_PROJETO = (ARGS.regua && ARGS.regua.length)
  ? `A RÉGUA DESTE PROJETO (o doc-load listou estes arquivos como lei — abra e leia cada um; não confie neste resumo):\n${ARGS.regua.map(r => `- ${r}`).join('\n')}\nDocumento minerado vale como MAPA, nunca como régua. Documento de acordo só vale com status: approved.`
  : `A RÉGUA DO PROJETO: a casca não a passou. RODE o doc-load na raiz da missão e julgue contra o que ele listar — não adivinhe nomes de arquivo, porque quem sabe o que vale como régua hoje é o programa. Ele não devolver nada é resposta válida: régua ausente não é achado, e o eixo simplesmente não roda.`

// ── A MARCA DA LEI É COMANDO, NUNCA RECEITA EM PROSA (medido 2026-08-09) ──────
// A instrução era "o cksum do corpo (sem frontmatter) dos arquivos concatenados",
// e quatro revisores da MESMA corrida calcularam quatro marcas do MESMO disco
// (com/sem frontmatter, concatenado/somado, com/sem o tamanho) — o motor registrou
// "a lei mudou durante a missão" DUAS vezes sem a lei ter mudado. O comando sai
// escrito no prompt, montado da régua que o doc-load listou; a marca é a saída
// literal dele, e receita que o modelo interpreta deixou de existir.
const LEI_CMD = (ARGS.regua && ARGS.regua.length)
  ? `cd ${RAIZ} && cat ${ARGS.regua.join(' ')} | cksum`
  : null
const leiMarcaInstr = lawMark => !LEI_CMD
  ? 'Projeto sem régua declarada: devolva `lawMark` null.'
  : lawMark
    ? `MARCA DA LEI FIXADA NA RODADA 1: ${lawMark} — meça contra ELA, não contra o texto de agora. Devolva em \`lawMark\` a SAÍDA LITERAL (uma linha) de: ${LEI_CMD}`
    : `Devolva em \`lawMark\` a SAÍDA LITERAL (uma linha) de: ${LEI_CMD} — rode EXATAMENTE este comando; não invente outra receita, não tire frontmatter, não some por arquivo.`

const orquestradorPrompt = ({ planPath, planText, round, feedback, ledger }) => `PAPEL: ORQUESTRADOR
Você é o ORQUESTRADOR do motor de implementação. Repositório: ${RAIZ}

Não planeja do zero e NÃO re-arquiteta. Pega a spec abaixo e a quebra em tarefas de
implementação. Buraco que exija decisão de arquitetura vira \`blocker\`, nunca invenção.

SPEC (arquivo: ${planPath}):
${planText}

O arquivo do plano inteiro está em ${planPath} — abra se precisar de contexto de outro passo.

RODADA: ${round}
${round === 1 ? 'Rodada 1: decomponha a spec INTEIRA.' : `Rodada ${round}: re-decomponha SÓ O DELTA do feedback abaixo.\nFEEDBACK DO REVISOR:\n${J(feedback)}`}

LEDGER DA CORRIDA (o que já foi julgado, consertado e confirmado — considere antes de montar a onda):
${J(ledger)}

REGRAS QUE NÃO SE NEGOCIAM:
1. \`id\` é COPIADO do plano, literal. Id que não existe no plano é recusado pelo script e vira Bloqueio — nenhum executor sai nele. Nunca invente sufixo ("-R", "-fix", "-bis").
2. \`requisito\` e \`pronto\` são COPIADOS da spec, nunca redigidos por você. Item sem um dos dois vira \`blocker\`, não tarefa.
3. \`esperaDono\` só existe se o passo no .plan.json trouxer \`espera_dono\` — copie literal. Não invente, não remova.
4. \`protegido\` = o caminho do arquivo que a tarefa toca e que traz \`status: approved\` no frontmatter, mais o motivo. Descubra LENDO O DISCO (grep no frontmatter), nunca por achismo.
5. \`files\` = os caminhos que a tarefa vai tocar. É deles que sai a reserva, o commit e a doc — lista errada perde trabalho.
6. \`complexity: 'mechanical'\` só para operação bem delimitada (renomear, mover, 1 config, 1 valor).
7. Vigie os ANTIPADRÕES conhecidos: porta fechada do repositório · trabalho condenado despachado após causa global · repetição como conserto · julgamento cego do já julgado · isolamento sem fusão declarada · id forjado pelo planejador.

Devolva o JSON do schema.`

const saudePrompt = ({ repoRoot, round }) => `PAPEL: MECANICO
Rodada ${round}. Papel mecânico e SÓ: rode os checks determinísticos da casa a partir de ${repoRoot}
e diga se a porta do repositório está FECHADA (algum deles reprova o estado atual).

Descubra quais existem: os mesmos que o gate de commit do projeto consulta (leia
.claude/hooks/release-gate.sh quando existir; neste marketplace, por exemplo,
python3 scripts/desacoplamento_check.py). Rode cada um, capturando a saída.

Qualquer um que saia com código != 0 sobre o estado ATUAL do repositório ⇒ \`fechada: true\`,
com \`motivo\` (uma linha) e \`saida\` (a saída crua, até 40 linhas).
Check ausente, quebrado por infra, ou que reprova algo que NÃO é do repositório ⇒ \`fechada: false\`.
Fail-open: na dúvida, \`fechada: false\`. Não conserte nada, não edite arquivo nenhum.

ANTES DE TUDO, marque na BARRA que esta rodada começou — um comando, e falhar nele não
derruba nada:

  ANDAMENTO="$(bash "${RESOLVE}" project-skills lib/andamento.py)"
  python3 "$ANDAMENTO" onda ${ARGS.sessionId} ${round} ${ARGS.planPath || ''} --etapa "separando o trabalho" || true`

const reguaPrompt = ({ repoRoot, criterios }) => `PAPEL: MECANICO
Papel mecânico e SÓ, sem julgamento próprio. Para cada par abaixo, rode:

  printf '%s' "<pronto>" | python3 "$(bash "${RESOLVE}" project-skills lib/regua_pronto.py)" --onde <id> -

(a partir de cd ${repoRoot})

PARES:
${J(criterios)}

Devolva em \`reprovados\` os que saíram com exit 1, com \`motivo\` = a linha que o programa imprimiu.
Exit 0 não entra na lista. Programa ausente ou comando quebrado ⇒ \`reprovados: []\` (fail-open).`

const execPrompt = ({ task, tetoMin, buildWarm }) => `PAPEL: EXECUTOR
Você é EXECUTOR. Implemente esta tarefa no repositório ${RAIZ}.

TAREFA:
${J(task)}

TETO: ${tetoMin} minutos. CACHE DE COMPILAÇÃO JÁ QUENTE: ${buildWarm}

REGRAS — cada uma nasceu de trabalho perdido:
1. CONFIRA NO DISCO ANTES DE IMPLEMENTAR. Abra o arquivo do \`pronto\` e veja se ele já está cumprido. Já cumprido ⇒ devolve \`done: true\` com o \`arquivo:linha\` que prova, e não reescreve nada.
2. FORMATAR O PROJETO INTEIRO É PROIBIDO. Nada de \`ruff format .\`, \`prettier --write .\`, \`black .\` sem caminho. Formate só os arquivos que ESTA tarefa tocou, nomeados um a um.
3. SONDA DE DEPURAÇÃO NASCE FORA DO ALCANCE DA SUÍTE. Script temporário vai para o diretório de rascunho da sessão, nunca com nome que a suíte colete (\`test_*.py\`, \`*_test.py\`).
4. PASSOU DO TETO, PARE E DEVOLVA \`espera: true\`. Marque a hora ao começar; chegou no teto sem fechar o \`pronto\`, pare onde está, deixe no disco o que já funciona e devolva \`{done:false, espera:true, note:<em que ponto parou e o que falta>}\`. Isso NÃO é falha.
5. ARQUIVO SOB TRANCA: O ENTREGÁVEL É A PROPOSTA. Tarefa com \`protegido\` ⇒ NÃO edite o arquivo (nem corpo, nem frontmatter). Devolva \`proposta: {arquivo, antes, depois}\` com os dois lados LITERAIS. \`git diff\` vazio ali é o resultado CERTO.
6. CACHE QUENTE: NÃO RECOMPILE DO ZERO se \`buildWarm\` for true.
7. O \`pronto\` É LITERAL — PROXY É PROIBIDO. Se o critério não pode ser cumprido COMO ESCRITO (pré-condição ausente, medição que não existe, decisão congelada do dono), NÃO invente um substituto "equivalente" nem troque o número medido por outro: devolva \`impossivel\` com o motivo. Documentar a troca honestamente não a autoriza — trocar critério é decisão do dono, e o caminho dela é o auditor, nunca a sua caneta.

REGRAS DA CASA do repositório da missão: leia o CLAUDE.md da raiz e obedeça — bump de
versão quando o projeto exigir, estado mutável fora de cache, o estilo que já existe.
${REGUA_DO_PROJETO}

ANTES DE DEVOLVER: rode a verificação que o \`pronto\` nomeia e cole a saída crua no \`summary\`.
\`anchor\` = a última linha não vazia do que você leu para decidir que estava pronto, literal.
\`files_touched\` = todo caminho que você escreveu — é dele que sai o commit; caminho omitido é trabalho que não entra no histórico.`

const reservaPrompt = ({ verbo, sessionId, motorId, files }) => `PAPEL: MECANICO
Papel mecânico e SÓ. Rode, a partir de ${RAIZ}:

  bash "$(bash "${RESOLVE}" project-skills hooks/reserva-de-arquivos.sh)" ${verbo} ${sessionId} ${motorId} ${files.map(f => `'${f}'`).join(' ')}

Devolva o veredito do JSON que saiu: \`recusado: true\` quando veio \`permissionDecision: "deny"\`,
com \`arquivos\` = os caminhos em disputa que a recusa nomeou. Script mudo ou ausente ⇒ \`recusado: false\`.
Sem julgamento próprio: quem decide é o hook, você só transporta.`

const revisorTarefaPrompt = ({ task, entrega, round, bloco, ledger }) => `PAPEL: REVISOR
Revisor POR TAREFA (rodada ${round}, bloco ${bloco}). Escopo: UMA tarefa. Repositório: ${RAIZ}

TAREFA:
${J(task)}

O QUE O EXECUTOR DEVOLVEU:
${J(entrega)}

LEDGER DA CORRIDA (não re-julgue o já julgado):
${J(ledger)}

${REGUA_DO_PROJETO}

Abra o \`pronto\` da tarefa, o \`git diff\` dos arquivos dela, e julgue TRÊS eixos:
1. FIDELIDADE — o critério foi cumprido de verdade, no disco? Rode a verificação que o \`pronto\` nomeia; não acredite no relato. O critério que vale é o LITERAL do plano: entrega que cumpre um critério REESCRITO (proxy, número trocado, medição substituída por outra "equivalente") REPROVA como kind 'spec' ≥ P1 — por mais honesta que a troca esteja documentada no código. Trocar critério é do dono; o executor que não consegue cumprir o literal devolve \`impossivel\`, nunca um substituto.
2. COBERTURA — o teste morde? Reprove os cinco antipadrões: teste que só afirma o que o código acabou de escrever · teste sem assert real · teste que passa com a função esvaziada · fixture que já contém a resposta · teste que não roda (nome fora do padrão de coleta).
3. QUALIDADE — o que saiu respeita a régua acima. Cite a passagem violada.

Tarefa \`protegido\`: o critério INVERTE — proposta com \`antes\` e \`depois\` literais aprova, e o arquivo protegido aparecendo no \`git diff\` REPROVA.

\`anchor\` = a última linha não vazia do que você julgou, literal. Sem ela o veredito é recusado.
Você NÃO conserta nada — só julga.`

const revisorBlocoPrompt = ({ planPath, repoRoot, tasks, entregas, round, bloco, lawMark, ledger }) => `PAPEL: REVISOR
Revisão FINAL do bloco ${bloco} da rodada ${round}. Escopo: as entregas JUNTAS. Repositório: ${repoRoot}

SPEC: ${planPath}

TAREFAS DO BLOCO:
${J(tasks)}

ENTREGAS:
${J(entregas)}

LEDGER DA CORRIDA:
${J(ledger)}

${REGUA_DO_PROJETO}
${leiMarcaInstr(lawMark)}

NÃO herda o veredito do revisor por tarefa: reabra os MESMOS eixos sobre o conjunto —
spec · constituição · rastreio (toda tarefa trouxe \`requisito\` e \`pronto\`?) · completude · COESÃO
(dois arquivos que se contradizem, cobertura que uma tarefa achou que a outra faria).

É o seu de acordo, junto com a suíte verde, que libera marcação, commit e doc deste bloco.
NÃO rode a suíte (outro papel faz) e NÃO cace bug sutil (isso é do /qa-loop depois).
\`anchor\` = a última linha não vazia do que você julgou, literal.`

const reviewBuildPrompt = ({ planPath, planText, repoRoot, decomp, results, round, lawMark, protegidas, files, ledger }) => `PAPEL: REVISOR
Revisão GERAL da obra, rodada ${round}. Repositório: ${repoRoot}

Você julga O QUE ESTÁ NO REPOSITÓRIO, no escopo destes arquivos (nunca o repo inteiro —
achado sobre trabalho alheio vira conserto que ninguém pediu):
${J(files)}

SPEC (${planPath}):
${planText}

DECOMPOSIÇÃO (é MEIO, não contrato final):
${J(decomp)}

RESULTADOS:
${J(results)}

TAREFAS SOB TRANCA (critério INVERTIDO — proposta literal aprova, arquivo tocado reprova):
${J(protegidas)}

LEDGER DA CORRIDA:
${J(ledger)}

${REGUA_DO_PROJETO}
${leiMarcaInstr(lawMark)}

CINCO EIXOS:
- spec — a spec saiu, mesmo no que a decomposição não previu? (kind: 'spec', nasce ≥ P1)
- constituição — o que saiu viola a lei acima? Cite a passagem. (kind: 'constituicao')
- rastreio — toda tarefa decomposta trouxe \`requisito\` e \`pronto\`? (kind: 'rastreio', nasce ≥ P1)
- completude — toda tarefa decomposta saiu? (kind: 'completude'; o que não saiu vai em \`missingTasks\`)
- coesão — as peças integram, sem se contradizer? (kind: 'coesao')

Se a execução descobriu algo que CONTRADIZ um documento de concepção já aprovado, isso é
kind: 'concepcao' — e você NUNCA reescreve documento aprovado.

NÃO rode a suíte, NÃO cace bug sutil — isso é do /qa-loop depois.
\`anchor\` = a última linha não vazia do que você julgou, literal.`

const revisaoDocPrompt = ({ repoRoot, files, round }) => `PAPEL: REVISOR
Revisão GERAL da doc, rodada ${round}. Repositório: ${repoRoot}

ARQUIVOS QUE ESTA ONDA TOCOU:
${J(files)}

Releia INTEIROS os documentos de ${repoRoot}/.claude/docs/ afetados por esses arquivos (pelo
campo \`scope:\` do frontmatter de cada doc), mais o índice ${repoRoot}/.claude/CLAUDE.md.
Procure: contradição com o repositório de AGORA, e conflito entre reescritas de blocos diferentes.

- Doc MINERADA errada você CONSERTA na hora e devolve o caminho em \`consertados\` (conferido no disco).
- Doc AUTORAL (frontmatter \`authored-by: human\`) você NUNCA toca:
  vira gap com \`autoral: true\`, que o dono resolve.

\`anchor\` = a última linha não vazia do que você julgou, literal.`

const confirmBuildPrompt = ({ planPath, planText, repoRoot, decomp, results, lawMark }) => `PAPEL: CONFIRMADOR
Confirmação independente da obra. Repositório: ${repoRoot}

Você é a ÚNICA segunda checagem que vai existir. Não confie em nenhum veredito anterior:
abra o disco e confira você mesmo.

SPEC (${planPath}):
${planText}

DECOMPOSIÇÃO:
${J(decomp)}

RESULTADOS:
${J(results)}

${REGUA_DO_PROJETO}
${leiMarcaInstr(lawMark)}

Mesmos cinco eixos do revisor (spec · constituição · rastreio · completude · coesão), medidos
contra o que está NO DISCO. Rode a verificação que cada \`pronto\` nomeia.
\`anchor\` = a última linha não vazia do que você julgou, literal.`

const auditorPrompt = ({ task, ledger, alegacao, ferramentas, onus, cobra, tentativas }) => `PAPEL: AUDITOR
Repositório: ${RAIZ}

Um executor alegou, por ${tentativas} rodadas seguidas, que esta tarefa não tem como sair.

TAREFA:
${J(task)}

ALEGAÇÃO: ${alegacao}
FERRAMENTAS QUE HAVIA À MÃO: ${J(ferramentas)}
LEDGER DA CORRIDA:
${J(ledger)}

ÔNUS: ${onus}
${cobra}

Já aconteceu de um executor declarar impossível o que ele conseguia fazer com a ferramenta que
já tinha na mão. \`derruba: true\` devolve a tarefa ao loop; \`derruba: false\` a encerra como
impedimento real, e aí o \`motivo\` é o que o dono vai ler.
\`anchor\` = a última linha não vazia do que você leu para decidir, literal.`

const diagnoseStuckTaskPrompt = ({ task, attempts, desafioAnterior }) => `PAPEL: DIAGNOSTICO
Repositório: ${RAIZ}

Esta tarefa não sai do lugar há ${attempts} rodada(s):
${J(task)}

PARE e investigue a CAUSA REAL. Não descreva o sintoma e não mande consertar onde o defeito
apareceu — remendo no ponto de aparição deixa de pé todos os outros pontos com a mesma raiz.
${desafioAnterior ? `\nUM DESAFIADOR DERRUBOU A SUA CAUSA ANTERIOR:\n${desafioAnterior}\nResponda a isso: ou explique o fato que ele apontou, ou aponte outra causa.` : ''}

Devolva, em texto: a causa raiz, a prova dela (arquivo:linha, saída crua), e o que precisa mudar
para destravar — dizendo se isso vale só para ESTA tarefa ou para o REPOSITÓRIO inteiro.`

const desafioCausaPrompt = ({ task, causa }) => `PAPEL: DESAFIADOR
Repositório: ${RAIZ}

TAREFA:
${J(task)}

CAUSA QUE O INVESTIGADOR APONTOU:
${causa}

Seu papel é PROVAR QUE ELA ESTÁ ERRADA: aponte o fato que ela não explica, o caminho que ela
ignora, ou a causa concorrente mais simples. Vá ao disco conferir.

- \`procede: false\` ⇒ o \`motivo\` carrega o que derruba a causa.
- \`procede: true\` ⇒ você referenda, e aí declare o \`escopo\`: 'tarefa' (só esta) ou
  'repositorio' (mata QUALQUER trabalho novo, não só esta tarefa).

\`anchor\` = a última linha não vazia do que você leu, literal.`

const runSuitePrompt = ({ repoRoot, round, bloco }) => `PAPEL: SUITE
Rodada ${round}. Papel mecânico e SÓ. cd ${repoRoot} e rode a suíte do repositório —
a que o projeto declara (CLAUDE.md, Makefile, package.json); sem declaração, a LISTA
sai deste comando, IGUAL em toda rodada da missão:

  find ${repoRoot} -path '*/node_modules' -prune -o -path '*/.git' -prune -o \\( -name 'test_*.py' -o -name 'test_*.sh' \\) -print | sort

"Os diretórios do trabalho desta missão" NÃO é critério: foi assim que a rodada 1 de uma
corrida real rodou 43 testes, a rodada 2 rodou 120, e um vermelho PRÉ-EXISTENTE do repo
apareceu no meio da onda como se fosse desta missão — matando o bloco.

Rode TODOS, some os resultados, e devolva:
- \`green\` = true só se NENHUM saiu com código != 0.
- \`failing\` = os caminhos que falharam.
- \`placar\` = uma linha crua no formato "N passou · M falhou".
- \`trabalhoVivo\` = true se há processo de build/servidor ainda rodando na máquina.
Não conserte nada. Suíte que não existe não é falha.

ANTES de rodar a suíte, marque o BLOCO na barra — é o passo que faz a barra andar
DENTRO da onda, e não só a cada onda nova (pedido do dono, 2026-08-09: uma onda de
três blocos deixava a barra parada quinze minutos no mesmo texto):

  ANDAMENTO="$(bash "${RESOLVE}" project-skills lib/andamento.py)"
  python3 "$ANDAMENTO" onda ${ARGS.sessionId} ${round} ${ARGS.planPath || ''} --bloco ${bloco} --etapa "suíte" || true`

const tickPlanPrompt = ({ planPath, passos }) => `PAPEL: MARCAR
Papel mecânico e SÓ: gravar no plano os passos que acabaram de sair.

PASSOS (a \`evidencia\` é a do executor — COPIE, não redija):
${J(passos)}

Rode UM COMANDO POR PASSO, em sequência:

  MARCADOR="$(bash "${RESOLVE}" project-skills lib/plan_state.py)"
  cd ${RAIZ} && python3 "$MARCADOR" --dir ${RAIZ}/.claude/plans tick <taskId> --evidencia "<evidencia>"

(o plano é ${planPath}; se o comando pedir qual plano, use o id do arquivo)

Falha de um passo NÃO interrompe os seguintes. Recusa do tick é resultado legítimo: entra no
veredito daquele passo com \`ok: false\` e o \`motivo\` = a linha que o programa imprimiu.

Terminado, registre a volta:
  ANDAMENTO="$(bash "${RESOLVE}" project-skills lib/andamento.py)"
  python3 "$ANDAMENTO" onda ${ARGS.sessionId} <rodada> ${planPath}
Falhar aqui não derruba nada.`

const checkpointPrompt = ({ repoRoot, round, bloco, results, planPath }) => `PAPEL: MECANICO
Papel mecânico e SÓ: gravar no histórico do git o que o bloco ${bloco} da onda ${round} produziu.

ARQUIVOS (a união dos \`files_touched\` das entregas aprovadas, MAIS o plano):
${J([...new Set(results.flatMap(x => x?.files_touched || []))].concat(planPath && planPath.endsWith('.plan.json') ? [planPath] : []))}

Rode, a partir de ${repoRoot}:

  OK=""; for f in <arquivo...>; do git -C ${repoRoot} add -- "$f" && OK="$OK $f" || echo "sprint: o git recusou $f — fica fora do ponto de salvamento da onda ${round}"; done; [ -n "$OK" ] && git -C ${repoRoot} commit -q -m "sprint: onda ${round} bloco ${bloco} verde" -- $OK || true

REGRAS:
- Os arquivos são NOMEADOS, nunca \`add -A\`: varrer a árvore engoliria trabalho de outra sessão.
- O \`commit\` também vai por caminho, não só o \`add\` — commit sem pathspec grava o índice inteiro.
- \`add\` que recusa um caminho não derruba o commit dos outros.
- Árvore limpa ⇒ nada a commitar, e isso não é falha.
- Projeto com gate de commit: gate que RECUSA é resultado legítimo — relate na saída, não force, não use --no-verify.`

const docTouchPrompt = ({ repoRoot, round, files, sessionId }) => `PAPEL: MECANICO
Papel mecânico e SÓ: re-projetar a doc dos arquivos que a onda ${round} tocou.

ARQUIVOS:
${J(files)}

1. Descubra o nome de invocação:  bash "${RESOLVE_SKILL}" doc-touch
2. INVOQUE a skill com esse nome exato (ferramenta Skill), passando a lista acima.
   Nunca escreva o prefixo do plugin à mão — ele já mudou de casa uma vez e quatro ondas
   fecharam sem produzir doc nenhuma por causa disso.
3. Terminado, CONFIRA CADA CAMINHO NO DISCO (\`test -f\`) e devolva em \`docs\` só os que existem.
   Caminho que você não achou fica de fora, mesmo que a skill diga ter escrito.
4. Grave a lista:  python3 "$(bash "${RESOLVE}" project-skills lib/andamento.py)" doc ${sessionId} ${round} <caminho...>
   Falhar aqui não derruba a onda.

Raiz: ${repoRoot}. Quem decide touch-vs-FULL é o próprio touch — ele escala e segue, sem perguntar.`

// ── O MOTOR APAGA O PRÓPRIO SINAL AO SAIR (pedido do dono, 2026-08-09) ───────
// O `rm` do sinal era passo da CASCA, em prosa — e a casca só o roda no caminho
// feliz. Motor que para por teto, por vigia, por disjuntor ou por onda estéril
// deixava a barra dizendo "missão de pé" pelo resto da sessão. Medido no mesmo
// dia: CINCO sinais órfãos vivos, o mais velho de 75 horas.
// É o ÚLTIMO papel do motor, e é um comando só — de propósito. A objeção que vale
// para a colheita ("agente disparado depois do disjuntor desfaz o desligamento")
// não vale aqui: apagar o sinal é instantâneo e é justamente o que o desligamento
// precisa para não deixar rastro.
// A reserva de arquivos é a OUTRA metade do par: ela mora em outro diretório
// (`andamento/reservas/<sid>__<motor>.files`), e nem `encerra` nem `expira_sinais`
// a tocam. Sem esta segunda linha ela fica de pé até o TTL de 12h, barrando outro
// motor da mesma sessão nos mesmos arquivos.
const encerraPrompt = ({ sessionId, motorId, motivo }) => `PAPEL: MECANICO
Papel mecânico e SÓ: a missão acabou (${motivo}) — apague o sinal dela na barra de status
e solte a reserva de arquivos desta missão.

  ANDAMENTO="$(bash "${RESOLVE}" project-skills lib/andamento.py)"
  python3 "$ANDAMENTO" encerra ${sessionId} sprint ${motorId} || echo "sprint: não consegui apagar o sinal — apague à mão"
  bash "$(bash "${RESOLVE}" project-skills hooks/reserva-de-arquivos.sh)" liberar ${sessionId} ${motorId} \\
    || echo "sprint: não consegui soltar a reserva — ela expira sozinha em 12h"

Nada mais. Não conserte, não commite, não edite arquivo nenhum.`

const colheitaPrompt = ({ repoRoot, round }) => `PAPEL: MECANICO
Papel mecânico e SÓ (onda ${round}, raiz ${repoRoot}). Rode:

  LIXEIRO="$(bash "${RESOLVE_SPRINT}" lixeiro lib/lixeiro.py)"
  if [ -n "$LIXEIRO" ]; then
    python3 "$LIXEIRO" colhe-turno --sessao ${ARGS.sessionId} \\
      || echo "sprint: a colheita falhou em $LIXEIRO — segue sem colher"
  fi

Sempre \`colhe-turno\`, nunca \`colhe-sessao\`. Lixeiro ausente ⇒ segue calado.
Falha da colheita não derruba nada.`

// ───────────────────────── MOTOR ─────────────────────────
const sevRank = s => ({ P0:3, P1:2, P2:1, P3:0 }[s] ?? 0)
const floor = sevRank(ARGS.severityFloor || 'P1')
// SEM TETO DE RODADAS por default (decisão do dono, 2026-08-13): missão de
// implementação vai do começo ao fim — um milhão de passos se preciso. Quem para é
// comportamento: built, vigia (rodadas sem avanço), disjuntor, porta fechada. O
// número só existe se a casca o passar de propósito.
const maxRounds = ARGS.maxRounds || Infinity
const churnThreshold = ARGS.churnThreshold || 2
const touchesShared = (t, lote) => lote.some(o => o.id !== t.id && o.files?.some(f => t.files?.includes(f)))
const rounds = []; const blockers = []
let built = false, r = 0
const tokenBudget = ARGS.tokenBudget || null
const rodadasMudasMax = ARGS.rodadasMudasMax || 3
const tetoExecutorMin = ARGS.tetoExecutorMin || 20
const buildWarm = ARGS.buildWarm === true
let rodadasMudas = 0
let trabalhoVivoEm = 0
let desligadoPor = null
const gastoAgora = () => budget.spent()
const gastoInicial = budget.spent()
let feedback = null
let lawMark = null
const taskChurn = {}
const impossivelChurn = {}
const marcadosNaMissao = new Set()

// ── O LEDGER DA CORRIDA (autópsia 2026-08-09, decisão do dono) ───────────────
const ledgerCorrida = []
const trilho = () => ledgerCorrida.slice(-30)

// ── REPETIR SEM MUDANÇA DE ESTADO É PROIBIDO (autópsia 2026-08-09) ───────────
const impressaoTarefa = {}
const estouraramTeto = new Set()
let fpRodadaAnterior = null

// ── O CACHE DE CAUSA (decisão do dono, 2026-08-09) ────────────────────────────
const causaCache = {}
const chaveDeCausa = t => ((t?.files || []).join('|') || t?.id || '?')
// ── TODA CAUSA GANHA ESCOPO, E ESCOPO DE REPOSITÓRIO PARA O MOTOR (autópsia) ──
const paraPorCausaGlobal = (d, taskId) => {
  desligadoPor = 'causa-global'
  blockers.push({ taskId, kind: 'causa-global',
    what: `causa confirmada com escopo de REPOSITÓRIO: ${String(d.causa).slice(0, 300)}`,
    whyNeedsYou: 'todo trabalho novo morreria na mesma porta — o motor parou no mesmo turno; destrave e relance' })
}
const investigaCausa = async (task, attempts) => {
  const chave = causaCache['@repositorio'] ? '@repositorio' : chaveDeCausa(task)
  if (causaCache[chave]) return { ...causaCache[chave], deCache: true }
  let causa = null, desafio = null, acordo = false
  for (let volta = 1; volta <= 3 && !acordo; volta++) {
    causa = await agent(diagnoseStuckTaskPrompt({ task, attempts,
        desafioAnterior: desafio?.motivo || null }),
      { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose',
        label: `causa:${task?.id || '?'} v${volta}` })
    if (!causa) break
    desafio = await julga(desafioCausaPrompt({ task, causa }),
      { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose',
        label: `desafia:${task?.id || '?'} v${volta}`, schema: DESAFIO })
    // desafiador mudo não referenda: sem veredito, a causa NÃO entra como consenso
    acordo = desafio ? desafio.procede === true : false
  }
  const escopo = desafio?.escopo === 'repositorio' ? 'repositorio' : 'tarefa'
  const out = acordo ? { causa, desafiada: true, escopo }
                     : { causa: null, disputa: { investigador: String(causa || 'sem resposta').slice(0, 200),
                                                 desafiador: String(desafio?.motivo || 'sem veredito').slice(0, 200) } }
  if (acordo) {
    causaCache[escopo === 'repositorio' ? '@repositorio' : chave] = out
    ledgerCorrida.push({ r, tipo: 'causa', taskId: task?.id, escopo,
                         resumo: String(causa).slice(0, 160) })
  }
  return out
}

// gerado por references/r8_tiers.py args — não digite à mão, não leia de args em
// tempo de execução. test_motor_js.py confere estes valores contra r8-tiers.json.
const T = { decompose: {effort:'high'}, coordinate: {effort:'medium'},
            executor: {effort:'medium'}, mechanical: {effort:'low'},
            diagnose: {effort:'medium'}, finalize: {effort:'medium'} }
const tierFor = round => ({ model: ARGS.model,
  effort: round === 1 ? T.decompose.effort : T.coordinate.effort })

// ── VEREDITO SEM A ÂNCORA DO FIM É RECUSADO (F9.16 · S-24) ──────────────────
const RECUSA = '\n\n⚠️ RECUSADO: o veredito anterior voltou SEM a âncora do fim e foi recusado — devolva em `anchor` a última linha não vazia do que você julgou, literal.'
const julga = async (prompt, opts) => {
  for (let tentativa = 1; tentativa <= 2; tentativa++) {
    // o rótulo da 2ª volta diz POR QUE ela existe: sem isso a tela mostra o mesmo
    // nome duas vezes e a recusa por âncora fica indistinguível de trabalho repetido.
    const v = await agent(tentativa === 1 ? prompt : prompt + RECUSA,
      tentativa === 1 ? opts : { ...opts, label: `${opts?.label || 'juiz'} ↻ sem âncora` })
    if (!v) return null
    if (v.anchor) return v
  }
  return null
}

while (!built && r < maxRounds) {
  r++; phase(`Rodada ${r}`)
  const tier = tierFor(r)

  // ── GUARDA CATCHALL DE SAÚDE (autópsia 2026-08-09, decisão do dono) ─────────
  const saude = await agent(saudePrompt({ repoRoot: ARGS.repoRoot, round: r }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Decompor',
      label: `saude:r${r}`, schema: SAUDE })
  if (saude?.fechada) {
    desligadoPor = 'porta-fechada'
    blockers.push({ what: `a porta do repositório está fechada: ${saude.motivo}`,
                    whyNeedsYou: `nenhuma onda sai com a porta fechada — todo trabalho novo morreria nela. Prova:\n${saude.saida || '(sem saída)'}` })
    break
  }

  // ── SUÍTE NA LARGADA: vermelho PRÉ-EXISTENTE aparece na PORTA (2026-08-09) ──
  // Medido: a rodada 1 de uma corrida real fechou verde (43 testes, o recorte que
  // o agente escolheu), a rodada 2 rodou o conjunto inteiro (120) e quebrou num
  // teste que JÁ estava vermelho ANTES da missão — três rodadas morreram em cima
  // de um defeito que não era desta obra. A suíte que os blocos vão cobrar roda
  // UMA vez aqui, ANTES de qualquer executor: vermelha na largada é porta fechada
  // com a lista colada, nunca descoberta no meio da onda. Fail-open: agente mudo
  // não fecha nada — o gate real continua sendo a suíte do bloco.
  if (r === 1) {
    const base = await agent(runSuitePrompt({ repoRoot: ARGS.repoRoot, round: r, bloco: 0 }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Decompor',
        label: 'suite:largada', schema: SUITE_RESULT })
    if (base && base.green === false) {
      desligadoPor = 'porta-fechada'
      blockers.push({ what: `a suíte do repositório JÁ está vermelha antes da missão: ${(base.failing || []).join(' · ') || base.placar || 'sem lista'}`,
                      whyNeedsYou: 'o vermelho é pré-existente, não desta obra — conserte esses testes e relance o /sprint; o motor não tem lista de teste ignorado, e nenhum bloco fecha verde em cima de suíte que já nasceu vermelha' })
      break
    }
  }

  // ORQUESTRAR — rodada 1 decompõe o plano inteiro; rodadas 2+ só o delta.
  const decomp = await agent(orquestradorPrompt({ planPath: ARGS.planPath, planText: ARGS.planText, round: r, feedback,
                                                  ledger: trilho() }),
    { model: tier.model, effort: tier.effort, phase: 'Decompor',
      label: r === 1 ? 'orquestrar:r1 (plano inteiro)' : `orquestrar:r${r} (delta)`, schema: DECOMP })
  if (!decomp) {
    blockers.push({ what: `orquestrador da rodada ${r} não respondeu`,
                    whyNeedsYou: 'sem decomposição não há o que executar nesta volta' })
    break
  }
  if (decomp.blockers?.length) blockers.push(...decomp.blockers)

  // ── O ID DA TAREFA TEM QUE EXISTIR NO PLANO (F9.58) ─────────────────────────
  const idsDoPlano = new Set(ARGS.planIds || [])
  if (idsDoPlano.size) {
    const forjados = decomp.tasks.filter(t => !idsDoPlano.has(t.id))
    for (const t of forjados) {
      blockers.push({ taskId: t.id, kind: 'id-inexistente',
        what: `o orquestrador criou a tarefa ${t.id}, que não existe no plano`,
        whyNeedsYou: `nenhum executor foi solto nela — se o trabalho é real, ele precisa de um passo no plano com id próprio` })
    }
    decomp.tasks = decomp.tasks.filter(t => idsDoPlano.has(t.id))
  }

  // ── QUEM ESPERA O DONO SAI DA DECOMPOSIÇÃO, NÃO SÓ DA FILA (F9.59) ──────────
  const congeladas = decomp.tasks.filter(t => t.esperaDono)
  if (congeladas.length) {
    log(`${congeladas.length} tarefa(s) esperam você e saíram da decomposição desta rodada`)
  }

  // ── A RÉGUA DO `pronto` É COBRADA POR CÓDIGO, NÃO SÓ NA PROSA (F8.2 · S-14) ──
  const regua = await agent(reguaPrompt({ repoRoot: ARGS.repoRoot,
                                          criterios: decomp.tasks.map(t => ({ id: t.id, pronto: t.pronto })) }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Decompor',
      label: `regua:r${r} (${decomp.tasks.length} criterios)`, schema: REGUA })
  const bancada = new Map((regua?.reprovados || []).map(x => [x.task_id, x.motivo]))
  for (const t of decomp.tasks.filter(t => bancada.has(t.id))) {
    blockers.push({ taskId: t.id, kind: 'criterio',
                    what: `o critério de aceite de ${t.id} é bancada: ${bancada.get(t.id)}`,
                    whyNeedsYou: `nenhum executor foi solto nesta tarefa — reescreva o \`pronto\` do passo "${t.requisito || t.id}" na spec para dizer o que REGERA o artefato a partir do dado real, e rode o motor de novo` })
  }
  decomp.tasks = decomp.tasks.filter(t => !bancada.has(t.id))

  // DIAGNÓSTICO de tarefa-presa — causa raiz, não repetição.
  // ── A CAUSA APONTADA NÃO ENTRA SEM SOBREVIVER AO DESAFIO (autópsia) ─────────
  const diagnoses = []
  for (const t of decomp.tasks) {
    if (taskChurn[t.id] >= churnThreshold) {
      const d = await investigaCausa(t, taskChurn[t.id])
      if (d.causa) {
        diagnoses.push({ task_id: t.id, diagnosis: d.causa, desafiada: true, deCache: !!d.deCache })
        if (d.escopo === 'repositorio') { paraPorCausaGlobal(d, t.id); break }
      } else {
        blockers.push({ taskId: t.id, kind: 'causa-em-disputa',
          what: `a causa de ${t.id} não sobreviveu ao desafio: investigador diz "${d.disputa?.investigador || 'sem resposta'}" · desafiador diz "${d.disputa?.desafiador || 'sem veredito'}"`,
          whyNeedsYou: 'três voltas de investigação e desafio sem acordo — causa em disputa não vira conserto; decida qual versão vale ou aponte a terceira' })
      }
    }
  }
  if (desligadoPor === 'causa-global') break

  // EXECUTAR — QUEM DEPENDE DE PASSO PARADO NASCE PARADO (F9.20).
  const parado = new Set(blockers.map(b => b.taskId).filter(Boolean))
  for (const t of decomp.tasks) if (t.esperaDono) parado.add(t.id)
  let cresceu = true
  while (cresceu) {
    cresceu = false
    for (const t of decomp.tasks) {
      if (!parado.has(t.id) && (t.dependsOn || []).some(d => parado.has(d))) {
        parado.add(t.id); cresceu = true
      }
    }
  }
  const todo = decomp.tasks.filter(t => !t.done && !parado.has(t.id))

  // ── PARA OU PULA — repetir sem mudança de estado é proibido (autópsia) ──────
  const fpDe = t => JSON.stringify([t.pronto, (t.files || []).slice().sort(),
    (feedback?.gaps || []).filter(g => g.task_id === t.id).map(g => g.problem).sort()])
  const puladas = []
  const fpNova = {}
  // Quem o motor NÃO despachou na rodada anterior volta com a impressão idêntica — mesmo
  // `pronto`, mesmos arquivos, zero gaps, porque ninguém a tocou. Sem esta isenção, 30
  // tarefas foram PULADAS por "estado repetido" sem nunca terem sido tentadas uma vez, e
  // cada uma virou um bloqueio mandando o dono "mudar o que a tarefa recebe" (2026-08-10).
  const naoTentadoAntes = new Set(feedback?.naoDespachadas || [])
  for (const t of [...todo]) {
    const fp = fpDe(t)
    if ((taskChurn[t.id] || 0) > 0 || (impossivelChurn[t.id] || 0) > 0 ||
        estouraramTeto.has(t.id) || naoTentadoAntes.has(t.id)) {
      fpNova[t.id] = fp
      continue
    }
    if (impressaoTarefa[t.id] === fp) {
      puladas.push(t.id)
      todo.splice(todo.indexOf(t), 1)
      blockers.push({ taskId: t.id, kind: 'pulada',
        what: `a tarefa ${t.id} voltou com a MESMA impressão de estado da tentativa anterior e foi PULADA`,
        whyNeedsYou: 'repetir sem mudança de estado não conserta nada — mude o que a tarefa recebe (spec, conserto, destrava) e relance' })
    } else fpNova[t.id] = fp
  }
  Object.assign(impressaoTarefa, fpNova)
  if (puladas.length) log(`puladas por estado repetido: ${puladas.join(' · ')}`)

  // ── A LEVA TAMBÉM TEM TETO, NÃO SÓ O BLOCO (autópsia 2026-08-10) ────────────
  // `blocoMax` limitava o bloco e nada limitava a LEVA: numa corrida real ela teve 53
  // tarefas, o segundo bloco falhou, e a regra de falhar cedo cancelou 45 de uma vez —
  // decompostas pelo papel mais caro do motor para nunca serem despachadas. Falhar cedo
  // é certo em leva curta; em leva de 53 é desastre. O que passa do teto NÃO é falha:
  // é a fila da rodada seguinte. O corte vem DEPOIS do "para ou pula" de propósito:
  // antes dele, a frente da fila que já foi entregue (e que o decompositor devolveu de
  // novo) ocuparia as vagas da leva toda rodada, e a fila adiada nunca andaria — as
  // puladas têm que sair ANTES de contar as vagas. A impressão de quem foi adiado está
  // protegida pela isenção `naoTentadoAntes` acima, então o adiado não é pulado na volta.
  const levaMax = ARGS.levaMax || 12
  const adiadas = todo.length > levaMax ? todo.splice(levaMax) : []
  if (adiadas.length) log(`leva cortada em ${levaMax}: ${adiadas.length} tarefa(s) ficam para a rodada seguinte`)

  // ESPERA APARECE COMO ESPERA, NÃO COMO FALHA (F8.4 · S-23).
  const esperaChain = new Map(decomp.tasks.filter(t => t.esperaDono)
    .map(t => [t.id, `espera um ato seu: ${t.esperaDono}`]))
  let herdou = true
  while (herdou) {
    herdou = false
    for (const t of decomp.tasks) {
      const de = (t.dependsOn || []).filter(d => esperaChain.has(d))
      if (!esperaChain.has(t.id) && de.length) {
        esperaChain.set(t.id, `depende de ${de.join(' · ')}, que espera você`); herdou = true
      }
    }
  }
  const esperandoVoce = decomp.tasks.filter(t => !t.done && esperaChain.has(t.id))
    .map(t => ({ taskId: t.id, motivo: esperaChain.get(t.id) }))

  // ── ONDA ESTÉRIL ENCERRA A CORRIDA (autópsia 2026-08-09) ────────────────────
  // `adiadas` na conta: a leva cortada pelo teto NÃO é onda vazia. Sem esta metade, uma
  // rodada em que as 12 da vez foram todas puladas encerraria a corrida dizendo "nenhuma
  // executável" com dezenas de tarefas ainda na fila, que é o mesmo abandono em silêncio
  // que o teto de leva veio consertar.
  if (decomp.tasks.length && !todo.length && !adiadas.length) {
    desligadoPor = 'onda-esteril'
    rounds.push({ r, decomp, results: [], review: null, esperandoVoce })
    blockers.push({ what: `onda ${r} estéril: ${decomp.tasks.length} tarefa(s) separadas e nenhuma executável — tudo parado por blocker ou espera`,
                    whyNeedsYou: 'mais rodada repete o mesmo vazio pelo mesmo preço — destrave o que espera você, ou recorte a missão' })
    break
  }

  // ── RESERVA DE ARQUIVOS ENTRE MOTORES (F9.2) ────────────────────────────────
  const arquivosDaOnda = [...new Set(todo.flatMap(t => t.files || []))]
  if (arquivosDaOnda.length) {
    const reserva = await agent(reservaPrompt({ verbo: 'reservar', sessionId: ARGS.sessionId,
                                                motorId: ARGS.motorId, files: arquivosDaOnda }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Executar',
        label: `reserva:r${r} (${arquivosDaOnda.length} arquivos)`, schema: RESERVA })
    if (reserva?.recusado) {
      desligadoPor = 'reserva'
      blockers.push({ what: `outro motor desta sessão já reservou: ${(reserva.arquivos || []).join(' · ')}`,
                      whyNeedsYou: 'dois motores no mesmo arquivo é um apagando o trabalho do outro — espere o outro terminar (ele libera ao sair) ou recorte a missão para arquivos que não encostem nos dele' })
      break
    }
  }
  const execTier = t => ({ model: ARGS.model,
    effort: t.complexity === 'mechanical' ? T.mechanical.effort : T.executor.effort })
  // ── O RETORNO AO ORQUESTRADOR É POR BLOCO, NÃO POR ONDA INTEIRA (F9.57 · S-141) ──
  const blocoMax = ARGS.blocoMax || 4
  const blocos = []
  for (let i = 0; i < todo.length; i += blocoMax) blocos.push(todo.slice(i, i + blocoMax))
  const respostas = []
  const naoDespachadas = []
  let blocoQueFalhou = null
  let b = 0, ultimaSuite = null
  const blocosVerdes = [], marcadosDaOnda = [], reprovadasNosBlocos = [], docsDaOnda = []
  for (const bloco of blocos) {
    if (blocoQueFalhou) { naoDespachadas.push(...bloco.map(t => t.id)); continue }
    const par = bloco.filter(t => t.parallelizable && !(t.dependsOn?.length))
    const seq = bloco.filter(t => !t.parallelizable || (t.dependsOn?.length))
    // quem NÃO colide vai junto; quem colide vai depois, um de cada vez, no MESMO repo.
    // NUNCA em worktree: o trabalho ficaria na cópia e o revisor confere no repo real.
    const livres = par.filter(t => !touchesShared(t, par))
    const colidem = par.filter(t => touchesShared(t, par))
    const builtPar = await parallel(livres.map(t => () =>
      agent(execPrompt({ task: t, tetoMin: tetoExecutorMin, buildWarm }), {
        model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', label: `exec:${t.id}`, schema: TASK_RESULT })))
    for (const t of colidem.concat(seq)) builtPar.push(await agent(execPrompt({ task: t, tetoMin: tetoExecutorMin, buildWarm }),
      { model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', label: `exec:${t.id}`, schema: TASK_RESULT }))
    const doBloco = builtPar.filter(Boolean)
    respostas.push(...doBloco)
    const falhou = doBloco.filter(x => x.done === false || x.impossivel)
    if (falhou.length || doBloco.length < bloco.length) {
      blocoQueFalhou = falhou.map(x => x.task_id)
    }

    // ── O CICLO CURTO FECHA NO BLOCO (decisão do dono, 2026-08-09) ────────────
    b++
    const entregues = [...new Map(doBloco.filter(x => x?.done && !x.espera && x.task_id)
      .map(x => [x.task_id, x])).values()]
    if (!entregues.length) continue

    // 1 · REVISOR POR TAREFA
    const porTarefa = await parallel(entregues.map(x => () =>
      julga(revisorTarefaPrompt({ task: decomp.tasks.find(t => t.id === x.task_id),
                                  entrega: x, round: r, bloco: b, ledger: trilho() }),
        { model: ARGS.model, effort: T.coordinate.effort, phase: 'Revisar',
          label: `rev-tarefa:${x.task_id}`, schema: TAREFA_REVIEW })))
    const reprovadasNaTarefa = new Set()
    for (let i = 0; i < entregues.length; i++) {
      const v = porTarefa[i]
      if (!v) continue
      if (!v.aprova) {
        reprovadasNaTarefa.add(entregues[i].task_id)
        if ((v.gaps || []).some(g => sevRank(g.severity) >= floor)) {
          const d = await investigaCausa(decomp.tasks.find(t => t.id === entregues[i].task_id), 1)
          if (d.causa && d.escopo === 'repositorio') paraPorCausaGlobal(d, entregues[i].task_id)
          if (d.causa) diagnoses.push({ task_id: entregues[i].task_id, diagnosis: d.causa,
                                        desafiada: true, deCache: !!d.deCache })
          else if (d.disputa) blockers.push({ taskId: entregues[i].task_id, kind: 'causa-em-disputa',
            what: `a causa do achado grave de ${entregues[i].task_id} não sobreviveu ao desafio: investigador diz "${d.disputa.investigador}" · desafiador diz "${d.disputa.desafiador}"`,
            whyNeedsYou: 'causa em disputa não vira conserto — decida qual versão vale ou aponte a terceira' })
        }
      }
    }
    for (let i = 0; i < entregues.length; i++) if (porTarefa[i])
      ledgerCorrida.push({ r, tipo: 'veredito', taskId: entregues[i].task_id,
                           resumo: `revisor-tarefa r${r}b${b}: ${porTarefa[i].aprova ? 'aprovou' : 'reprovou'}` })
    if (desligadoPor === 'causa-global') break
    const aprovadasTarefa = entregues.filter(x => !reprovadasNaTarefa.has(x.task_id))
    reprovadasNosBlocos.push(...reprovadasNaTarefa)
    if (!aprovadasTarefa.length) { blocoQueFalhou = [...reprovadasNaTarefa]; continue }

    // 2 · REVISÃO DO BLOCO — não herda o veredito por tarefa.
    const revBloco = await julga(revisorBlocoPrompt({ planPath: ARGS.planPath, repoRoot: ARGS.repoRoot,
        tasks: aprovadasTarefa.map(x => decomp.tasks.find(t => t.id === x.task_id)),
        entregas: aprovadasTarefa, round: r, bloco: b, lawMark, ledger: trilho() }),
      { model: ARGS.model, effort: T.coordinate.effort, phase: 'Revisar',
        label: `rev-bloco:r${r}b${b}`, schema: BUILD_REVIEW })
    if (revBloco) ledgerCorrida.push({ r, tipo: 'veredito', taskId: null,
      resumo: `revisor-bloco r${r}b${b}: ${(revBloco.gaps || []).length} gap(s), ${(revBloco.missingTasks || []).length} faltante(s)` })
    const reprovadasNoBloco = new Set(revBloco
      ? [...(revBloco.gaps || []).map(g => g.task_id), ...(revBloco.missingTasks || [])].filter(Boolean)
      : aprovadasTarefa.map(x => x.task_id))
    reprovadasNosBlocos.push(...[...reprovadasNoBloco].filter(id => !reprovadasNaTarefa.has(id)))
    const aprovadas = aprovadasTarefa.filter(x => !reprovadasNoBloco.has(x.task_id))
    if (!aprovadas.length) continue

    // 3 · SUÍTE INTEIRA — vermelha fecha a onda aqui, e nada deste bloco é marcado.
    const suiteB = await agent(runSuitePrompt({ repoRoot: ARGS.repoRoot, round: r, bloco: b }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Suíte', label: `suite:r${r}b${b}`, schema: SUITE_RESULT })
    // trabalho vivo protege a rodada em que foi VISTO, e só ela: guardar a última suíte
    // qualquer fazia a suíte VERMELHA que fecha o bloco apagar o `trabalhoVivo` da verde
    // anterior, e guardar a última que declarou vivo o deixaria valendo para sempre.
    if (suiteB?.trabalhoVivo) trabalhoVivoEm = r
    ultimaSuite = suiteB
    if (!suiteB || !suiteB.green) {
      blockers.push({ what: `a suíte quebrou no bloco ${b} da rodada ${r}: ${suiteB?.failing?.join(' · ') || 'sem veredito'}`,
                      whyNeedsYou: 'bloco vermelho não vira ponto de salvamento — o conserto volta pelo orquestrador' })
      blocoQueFalhou = aprovadas.map(x => x.task_id)
      continue
    }

    // 4 · MARCAÇÃO + COMMIT + DOC + COLHEITA — no grão do bloco.
    if (ARGS.planPath?.endsWith('.plan.json')) {
      const tick = await agent(tickPlanPrompt({ planPath: ARGS.planPath,
        passos: aprovadas.map(t => ({ taskId: t.task_id,
          evidencia: `${t.summary} · ${(t.files_touched || []).join(' ')}` })) }),
        { model: ARGS.model, effort: T.mechanical.effort, phase: 'Marcar',
          label: `marcar r${r}b${b} (${aprovadas.length})`, schema: TICK_RESULT })
      const vistos = new Map((tick?.marcados || []).map(m => [m.task_id, m]))
      for (const t of aprovadas) {
        const v = vistos.get(t.task_id)
        if (!v) blockers.push({ taskId: t.task_id,
          what: `o passo ${t.task_id} foi ENTREGUE mas não voltou no veredito da marcação`,
          whyNeedsYou: 'o trabalho está no disco e o plano diz que não — marque à mão com a prova do executor' })
        else if (!v.ok) blockers.push({ taskId: t.task_id,
          what: `a marcação de ${t.task_id} foi recusada: ${v.motivo || 'sem motivo'}`,
          whyNeedsYou: 'recusa por decisão em aberto é legítima — resolva a pendência do passo e marque' })
        else {
          marcadosNaMissao.add(t.task_id)
          ledgerCorrida.push({ r, tipo: 'marcado', taskId: t.task_id,
                               resumo: `marcado no plano r${r}b${b}` })
        }
      }
      marcadosDaOnda.push(...(tick?.marcados || []))
    }
    await agent(checkpointPrompt({ repoRoot: ARGS.repoRoot, round: r, bloco: b, results: aprovadas, planPath: ARGS.planPath }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Salvar', label: `commit r${r}b${b}` })
    blocosVerdes.push({ bloco: b, feitos: aprovadas.map(x => x.task_id), placar: suiteB.placar })
    const tocadosB = [...new Set(aprovadas.flatMap(x => x?.files_touched || []))]
    if (tocadosB.length) {
      const doc = await agent(docTouchPrompt({ repoRoot: ARGS.repoRoot, round: r, files: tocadosB, sessionId: ARGS.sessionId }),
        { model: ARGS.model, effort: T.mechanical.effort, phase: 'Doc', label: `doc r${r}b${b}`, schema: DOC_TOUCH })
      docsDaOnda.push(...(doc?.docs || []))
      if (!(doc?.docs || []).length) blockers.push({
        what: `a doc do bloco ${b} da rodada ${r} não foi confirmada no disco`,
        whyNeedsYou: 'o próximo bloco vai decidir por um mapa vencido — re-projete a doc destes arquivos' })
    }
    await agent(colheitaPrompt({ repoRoot: ARGS.repoRoot, round: r }),
      { model: ARGS.model, effort: T.mechanical.effort, phase: 'Limpeza', label: `limpeza r${r}b${b}` })
  }

  // A CONTA DO VIGIA FECHA AQUI, com os blocos da onda já sabidos — e não lá embaixo,
  // porque os caminhos que fazem `continue` no meio pulariam a contagem justo nas rodadas
  // que não produziram nada (revisor mudo, por exemplo). O que zera é o BLOCO VERDE, não
  // a marcação: `marcadosDaOnda` guarda também o passo que o plano RECUSOU marcar, e
  // recusa não é avanço. Marcação só acontece depois de suíte verde, então todo passo
  // marcado de verdade já tem um bloco verde a lhe corresponder aqui.
  rodadasMudas = blocosVerdes.length ? 0 : rodadasMudas + 1

  if (desligadoPor === 'causa-global') {
    rounds.push({ r, decomp, results: respostas.filter(x => !x.espera), review: null,
                  diagnoses, checkpoint: blocosVerdes.length > 0, blocos: blocosVerdes,
                  feitos: blocosVerdes.flatMap(x => x.feitos),
                  marcados: marcadosDaOnda, doc: docsDaOnda })
    break
  }

  // ── UM EXECUTOR LENTO NÃO SEGURA A RODADA (F9.29) ───────────────────────────
  // NÃO TENTADO = o que o bloco cancelado engoliu + o que o teto de leva adiou. A volta
  // precisa distinguir isto de "tentado e falhou": é a identidade que se perdia na fusão
  // com o resto do `missing`, e sem ela a regra de pular condenava quem nunca saiu.
  const naoTentadasNaRodada = [...naoDespachadas, ...adiadas.map(t => t.id)]
  const esperaIds = respostas.filter(x => x.espera).map(x => x.task_id)
  for (const id of esperaIds) estouraramTeto.add(id)
  const results = respostas.filter(x => !x.espera)

  // ── BLOQUEIO REPETIDO CONVOCA O AUDITOR (F9.18 · S-26) ──────────────────────
  const devolvidasPeloAuditor = []
  const alegam = new Set(results.filter(x => x.impossivel).map(x => x.task_id))
  for (const t of todo) impossivelChurn[t.id] = alegam.has(t.id) ? (impossivelChurn[t.id] || 0) + 1 : 0
  for (const x of results.filter(x => x.impossivel && impossivelChurn[x.task_id] >= churnThreshold)) {
    const parecer = await julga(auditorPrompt({ task: decomp.tasks.find(t => t.id === x.task_id),
                                                ledger: trilho(),
                                                alegacao: x.impossivel, ferramentas: x.ferramentas || [],
                                                onus: 'invertido — cabe a VOCÊ provar que não dá; o executor não precisa provar que dá',
                                                cobra: 'diga em naoTentou quais das ferramentas acima o executor nem tentou',
                                                tentativas: impossivelChurn[x.task_id] }),
      { model: ARGS.model, effort: T.diagnose.effort, phase: 'Diagnose', label: `auditor:${x.task_id}`, schema: AUDITOR })
    x.done = false
    if (!parecer || parecer.derruba) {
      impossivelChurn[x.task_id] = 0
      devolvidasPeloAuditor.push({ taskId: x.task_id,
        motivo: parecer ? `o auditor derrubou a alegação: ${parecer.motivo}` : 'o auditor não respondeu — a alegação não foi confirmada',
        naoTentou: parecer?.naoTentou || [] })
    } else {
      blockers.push({ taskId: x.task_id, kind: 'impedimento',
        what: `impedimento real em ${x.task_id}, confirmado pelo auditor: ${parecer.motivo}`,
        whyNeedsYou: 'a alegação do executor foi auditada com a lente invertida e confirmada — não sai com mais uma rodada' })
    }
  }

  // ── ARQUIVO SOB TRANCA: O ENTREGÁVEL É A PROPOSTA (F8.5) ────────────────────
  const protegidas = new Set(decomp.tasks.filter(t => t.protegido).map(t => t.id))
  for (const x of results.filter(x => protegidas.has(x.task_id))) {
    if (!x.proposta?.antes || !x.proposta?.depois) {
      x.done = false
      blockers.push({ taskId: x.task_id,
                      what: `a tarefa ${x.task_id} toca arquivo sob tranca e voltou sem proposta com antes e depois literais`,
                      whyNeedsYou: 'sem o texto literal dos dois lados não há o que aplicar — o arquivo continua intocado, que é o certo' })
    } else {
      blockers.push({ taskId: x.task_id,
                      what: `proposta para ${x.proposta.arquivo} (sob tranca): ${x.summary}`,
                      whyNeedsYou: `nenhum arquivo foi alterado — git diff vazio aqui é o resultado CERTO; aplicar é seu, porque o de acordo é seu.\nANTES:\n${x.proposta.antes}\nDEPOIS:\n${x.proposta.depois}` })
    }
  }

  // REVISÃO GERAL DA OBRA — julga o repositório no escopo dos arquivos da onda.
  const filesDaOnda = [...new Set(results.flatMap(x => x?.files_touched || []))]
  const review = await julga(reviewBuildPrompt({ planPath: ARGS.planPath, planText: ARGS.planText, repoRoot: ARGS.repoRoot, decomp, results, round: r, lawMark, protegidas: [...protegidas], files: filesDaOnda, ledger: trilho() }),
    { model: tier.model, effort: tier.effort, phase: 'Revisar', label: `rev-geral:r${r}`, schema: BUILD_REVIEW })

  // AGENTE MORTO NÃO PODE DERRUBAR O MOTOR.
  if (!review) {
    blockers.push({ what: `revisor da rodada ${r} não respondeu, ou voltou duas vezes sem a âncora do fim`,
                    whyNeedsYou: 'a obra desta rodada ficou SEM revisão — trate como não verificada' })
    rounds.push({ r, decomp, results, review: null, diagnoses, espera: esperaIds, esperandoVoce,
                  devolvidas: devolvidasPeloAuditor, naoDespachadas,
                  adiadas: adiadas.map(t => t.id) })
    feedback = { gaps: [], missing: [...esperaIds, ...naoTentadasNaRodada, ...devolvidasPeloAuditor.map(d => d.taskId)],
                 naoDespachadas: naoTentadasNaRodada,
                 diagnoses, devolvidas: devolvidasPeloAuditor, blocoQueFalhou }
    continue
  }

  // MARCA DA LEI — congelada na 1ª volta.
  if (review.lawMark) {
    if (lawMark === null) lawMark = review.lawMark
    else if (review.lawMark !== lawMark) {
      blockers.push({ what: `a lei do projeto mudou durante a missão (marca ${lawMark} → ${review.lawMark}, rodada ${r})`,
                      whyNeedsYou: 'as rodadas anteriores foram medidas contra o texto antigo — confira o que mudou antes de aceitar a obra' })
    }
  }

  // ── ACHADO SOBRE PASSO JÁ MARCADO → RE-TICK, NUNCA ID NOVO ──────────────────
  const reticks = [...new Set((review.gaps || []).map(g => g.task_id)
    .filter(id => id && marcadosNaMissao.has(id)))]
  if (reticks.length) log(`revisão geral reabriu passo já marcado: ${reticks.join(' · ')} — o conserto regrava a prova do mesmo id`)

  // ── REVISÃO GERAL DA DOC (decisão do dono, 2026-08-09) ──────────────────────
  if (filesDaOnda.length) {
    const revDoc = await julga(revisaoDocPrompt({ repoRoot: ARGS.repoRoot, files: filesDaOnda, round: r }),
      { model: ARGS.model, effort: T.coordinate.effort, phase: 'Revisar',
        label: `rev-doc:r${r}`, schema: DOC_REVIEW })
    if (revDoc) {
      for (const g of (revDoc.gaps || []).filter(g => g.autoral)) {
        blockers.push({ what: `a doc AUTORAL contradiz o repositório: ${g.problem} (${g.arquivo})`,
                        whyNeedsYou: 'documento seu — nenhum agente o corrige; atualize ou grave correcao-pendente: no frontmatter' })
      }
    } else {
      blockers.push({ what: `a revisão geral da doc da rodada ${r} não respondeu`,
                      whyNeedsYou: 'os documentos desta onda ficaram sem a releitura inteira — confira antes de confiar neles' })
    }
  }

  // A CONCEPÇÃO ERROU — aviso ao dono, nunca conserto de código.
  for (const g of (review.gaps || []).filter(g => g.kind === 'concepcao')) {
    blockers.push({ what: `a concepção está errada: ${g.problem}`,
                    whyNeedsYou: 'reabra a etapa — grave `correcao-pendente:` no frontmatter do documento e reaprove; nenhum documento foi alterado aqui' })
  }

  // ── QUEM NUNCA FOI TENTADO NÃO REINCIDE (F9.56) ─────────────────────────────
  const naoTentado = new Set([...parado, ...esperaChain.keys(), ...naoTentadasNaRodada])
  const stuck = new Set([...(review.missingTasks || []), ...(review.gaps || []).map(g => g.task_id)]
                        .filter(id => id && !naoTentado.has(id)))
  for (const t of decomp.tasks) taskChurn[t.id] = stuck.has(t.id) ? (taskChurn[t.id] || 0) + 1 : 0
  ledgerCorrida.push({ r, tipo: 'veredito', taskId: null,
    resumo: `revisão geral r${r}: ${(review.gaps || []).length} gap(s), ${(review.missingTasks || []).length} faltante(s)` })

  // ── CORRIDA EM CÍRCULO — o detector genérico (autópsia 2026-08-09) ──────────
  const fpRodada = JSON.stringify([[...stuck].sort(),
    (review.gaps || []).map(g => `${g.task_id || '-'}:${g.kind}`).sort(),
    diagnoses.map(d => d.task_id).sort()])
  const emCirculo = stuck.size > 0 && blocosVerdes.length === 0 && fpRodada === fpRodadaAnterior
  fpRodadaAnterior = blocosVerdes.length === 0 ? fpRodada : null

  rounds.push({ r, decomp, results, review, diagnoses, espera: esperaIds, esperandoVoce,
                devolvidas: devolvidasPeloAuditor, naoDespachadas,
                adiadas: adiadas.map(t => t.id) })   // fila da rodada seguinte, não falha

  // ── O SALVAMENTO ACONTECEU POR BLOCO — a onda só CONSOLIDA o registro ───────
  rounds[rounds.length - 1].placar = ultimaSuite?.placar
  rounds[rounds.length - 1].checkpoint = blocosVerdes.length > 0
  rounds[rounds.length - 1].blocos = blocosVerdes
  rounds[rounds.length - 1].feitos = blocosVerdes.flatMap(x => x.feitos)
  rounds[rounds.length - 1].marcados = marcadosDaOnda
  rounds[rounds.length - 1].doc = docsDaOnda
  rounds[rounds.length - 1].reticks = reticks
  if (reprovadasNosBlocos.length) {
    rounds[rounds.length - 1].naoMarcados = { motivo: 'reprova do revisor de tarefa ou de bloco',
                                              ids: [...new Set(reprovadasNosBlocos)] }
    log(`não marcados por reprova nos blocos: ${[...new Set(reprovadasNosBlocos)].join(' · ')}`)
  }

  if (emCirculo) {
    desligadoPor = 'corrida-em-circulo'
    blockers.push({ what: `corrida em círculo: a rodada ${r} terminou com a MESMA impressão de estado da rodada anterior`,
                    whyNeedsYou: 'mais rodada repete o mesmo resultado pelo mesmo preço — destrave o que os achados apontam e relance' })
    break
  }

  // ── DISJUNTOR POR CONSUMO (F9.12) ───────────────────────────────────────────
  const gasto = gastoAgora() - gastoInicial
  if (tokenBudget && gasto >= tokenBudget) {
    desligadoPor = 'orcamento'
    blockers.push({ what: `disjuntor: a missão gastou ${gasto} de ${tokenBudget} tokens e se desligou na rodada ${r}`,
                    whyNeedsYou: 'o que faltou está nas tarefas abertas do plano — relance com teto maior se valer' })
    break
  }

  // ── VIGIA POR AVANÇO (F9.13 + F9.24) ────────────────────────────────────────
  // O vigia media TEMPO e o script não tem relógio: `Date.now()` lança em script de
  // Workflow, então a hora vinha do agente da suíte, que numa corrida real devolveu
  // `heartbeat: 1` — a conta deu 56 anos de silêncio e matou a missão no minuto seguinte
  // a uma suíte verde de 374 testes, com 10 das 12 rodadas por usar (autópsia 2026-08-10).
  // Sinal de vida agora é AVANÇO, que o motor mede sozinho: rodada que fecha bloco
  // verde zera a conta (a linha que conta fica logo depois do laço de blocos). A metade
  // que fala em minutos é do gancho de andamento (`lib/andamento.py:linha_silencio`),
  // que roda em Python e TEM relógio.
  if (rodadasMudas >= rodadasMudasMax && trabalhoVivoEm < r) {
    desligadoPor = 'vigia'
    blockers.push({ what: `vigia: ${rodadasMudas} ${rodadasMudas === 1 ? 'rodada fechou' : 'rodadas seguidas fecharam'} sem nenhum bloco verde e sem nenhum passo marcado, e não há trabalho vivo na máquina`,
                    whyNeedsYou: 'travamento, não demora — o último estado salvo é o checkpoint da rodada anterior' })
    break
  }

  const holdsBuild = g => g.kind !== 'concepcao' && (g.kind === 'spec' || g.kind === 'rastreio' || sevRank(g.severity) >= floor)
  const gaps = (review.gaps || []).filter(holdsBuild)

  // `built` é FATO do programa antes de ser juízo do revisor: rodada com tarefa não
  // tentada (bloco cancelado ou fila adiada pelo teto de leva) não declara obra pronta
  // nem que o revisor a declare — ele julga o que viu, e o que não foi despachado ele
  // não viu. Sem esta guarda, um "complete" generoso encerraria a missão com a fila cheia.
  if (!naoTentadasNaRodada.length && review.complete && review.cohesive && gaps.length === 0) {
    if (ARGS.hasQaLoop === false) {
      const confirm = await julga(confirmBuildPrompt({ planPath: ARGS.planPath, planText: ARGS.planText, repoRoot: ARGS.repoRoot, decomp, results, lawMark }),
        { model: ARGS.model, effort: T.finalize.effort, phase: 'Confirmar',
          label: `confirmar:r${r}`, schema: BUILD_REVIEW })
      rounds[rounds.length - 1].confirm = confirm
      if (!confirm) {
        blockers.push({ what: 'o confirm-pass não respondeu, ou voltou duas vezes sem a âncora do fim',
                        whyNeedsYou: 'sem /qa-loop e sem confirm, NADA checou a obra — não considere entregue' })
        break
      }
      const confirmGaps = (confirm.gaps || []).filter(holdsBuild)
      if (!confirm.complete || !confirm.cohesive || confirmGaps.length) {
        feedback = { gaps: confirm.gaps.filter(g => g.kind !== 'concepcao'), missing: confirm.missingTasks,
                     naoDespachadas: naoTentadasNaRodada, diagnoses }
        continue
      }
    }
    built = true; break
  }
  feedback = { gaps: review.gaps.filter(g => g.kind !== 'concepcao'),
               missing: [...new Set([...(review.missingTasks || []), ...esperaIds,
                                     ...naoTentadasNaRodada, ...reprovadasNosBlocos,
                                     ...devolvidasPeloAuditor.map(d => d.taskId)])],
               naoDespachadas: naoTentadasNaRodada,
               reticks,
               diagnoses, devolvidas: devolvidasPeloAuditor, blocoQueFalhou }
}

// ── A CONFERÊNCIA FINAL RODA MESMO NA PARADA (autópsia 2026-08-09) ────────────
let conferidoPor = built ? (ARGS.hasQaLoop === false ? 'confirm-pass' : 'qa-loop da etapa seguinte') : 'nenhuma'
const entregouAlgo = rounds.some(x => (x.feitos || []).length)
if (!built && entregouAlgo && desligadoPor !== 'orcamento') {
  const ultima = rounds[rounds.length - 1]
  const confirmFinal = await julga(confirmBuildPrompt({ planPath: ARGS.planPath, planText: ARGS.planText,
      repoRoot: ARGS.repoRoot, decomp: ultima.decomp,
      results: rounds.flatMap(x => x.results || []).filter(Boolean), lawMark }),
    { model: ARGS.model, effort: T.finalize.effort, phase: 'Confirmar', label: 'confirm-na-parada', schema: BUILD_REVIEW })
  rounds[rounds.length - 1].confirmFinal = confirmFinal
  if (!confirmFinal) {
    blockers.push({ what: 'a missão parou no meio e a conferência final não respondeu',
                    whyNeedsYou: 'nada checou o que as ondas entregaram — trate os passos marcados como não conferidos' })
  } else {
    conferidoPor = 'confirm-na-parada'
    for (const g of (confirmFinal.gaps || [])) {
      blockers.push({ taskId: g.task_id || undefined,
        what: `a conferência final da parada achou defeito${g.task_id ? ` em ${g.task_id}` : ''}: ${g.problem}`,
        whyNeedsYou: 'a missão já parou — este conserto vira tarefa no plano, não sai sozinho' })
    }
  }
}

// O QUE FALTOU, SEPARADO POR MOTIVO (F9.19).
const impedidos = blockers.filter(b => b.whyNeedsYou).map(b => ({ ...b, motivo: b.what }))
const naoDeuTempo = rounds.length
  ? [...(rounds[rounds.length - 1].review?.missingTasks || []).map(id => ({ taskId: id })),
     ...(rounds[rounds.length - 1].espera || []).map(id => ({ taskId: id, motivo: `passou do teto de ${tetoExecutorMin} min do executor` }))]
  : []
// ESPERA NÃO É FALHA (F8.4).
const esperandoVoce = rounds.length ? (rounds[rounds.length - 1].esperandoVoce || []) : []

// PROGRESSO DA MISSÃO (F9.35) — passos DISTINTOS fechados, nunca linhas de resultado.
const passosFeitos = [...new Set(rounds.flatMap(x => x.feitos || []))]

// VOLTAS POR PROBLEMA (F25.4)
const voltasPorProblema = []
const porGap = {}
for (const x of rounds)
  for (const g of (x.review?.gaps || [])) {
    const k = `${g.task_id || '-'}:${g.kind}`
    if (!porGap[k]) voltasPorProblema.push(porGap[k] =
      { taskId: g.task_id || null, kind: g.kind, problem: g.problem, primeira: x.r, voltas: 0 })
    porGap[k].voltas = x.r - porGap[k].primeira + 1
  }

// ── ÚLTIMO ATO: apagar o sinal da barra ─────────────────────────────────────
// Vem DEPOIS de tudo e ANTES do return, então alcança TODO caminho de saída —
// obra pronta, teto, vigia, disjuntor, onda estéril, causa global. A casca
// continua apagando também (cinto e suspensório); e a barra varre o que passar
// dos dois (`andamento.py:expira_sinais`).
//
// UMA EXCEÇÃO, e só uma: o motor que a RESERVA recusou. `andamento.py encerra` apaga
// por SESSÃO, não por motor — quem sai por `reserva` nunca reservou nem acendeu nada,
// e encerrar aqui apagaria o sinal do OUTRO motor da mesma sessão, que segue vivo (a
// barra dele sumiria: `pretooluse-motor-arma.sh` desarma sem o sinal).
if (desligadoPor !== 'reserva')
  await agent(encerraPrompt({ sessionId: ARGS.sessionId, motorId: ARGS.motorId,
                              motivo: desligadoPor || (built ? 'obra de pé' : 'teto de rodadas') }),
    { model: ARGS.model, effort: T.mechanical.effort, phase: 'Limpeza', label: 'encerra:barra' })

return {
  rounds, built, blockers, lawMark,
  ledger: ledgerCorrida,
  voltasPorProblema,
  progresso: { feitos: passosFeitos.length, passos: passosFeitos },
  impedidos,
  naoDeuTempo,
  esperandoVoce,
  gasto: gastoAgora() - gastoInicial,
  stopReason: desligadoPor || (built ? 'build-complete' : 'max-rounds'),
  conferidoPor,
  telemetry: rounds.map(x => ({ round: x.r,
                                tasks: new Set((x.results || []).filter(t => t?.task_id)
                                                               .map(t => t.task_id)).size,
                                gaps: x.review?.gaps.length ?? null,
                                checkpoint: !!x.checkpoint })),
}
