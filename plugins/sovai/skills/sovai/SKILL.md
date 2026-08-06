---
name: sovai
description: Modo de execução contínua — Claude executa um plano ou tarefa multi-etapa do começo ao fim sem pausas, sem checkpoints, sem perguntas de confirmação. Toma as decisões necessárias para seguir e anota cada uma. O usuário estará indisponível durante a execução; ele revisa tudo no relatório final e refatora se necessário. Use quando o usuário disser "sovai", "sova", "executa até o fim", "vai sem parar", "não me consulte", "eu não estarei disponível", "modo autônomo", ou variação clara de "executa sozinho enquanto eu não tô". Não disparar para tarefas curtas que terminam num turno — a skill existe para missões em que interrupção custa caro porque o usuário não está disponível para responder.
---

# Sovai — Execução Contínua

O usuário vai ficar indisponível. Reconheça com uma linha (`modo sovai ativo, começando`) e comece. Daqui em diante, silêncio até o relatório final.

## Contrato

**Faz:**
- Executa o plano (ou a tarefa) do começo ao fim, sem pausar — através do **motor decompõe→executa→revisa** (Workflow; ver _Execução_)
- Toma todas as decisões necessárias para seguir e **anota cada uma**
- Verifica antes de declarar feito — regras globais do CLAUDE.md continuam valendo
- Ao final, atualiza a doc (`doc-touch`, que escala pro FULL sozinho se precisar) e faz commit + push do trabalho — ver **Persistência**

**Não faz:**
- Pergunta de confirmação no meio ("posso seguir?", "X ou Y?")
- Checkpoint intermediário pedindo aval
- Reporte de progresso parcial — silêncio é o esperado
- Ação destrutiva ou irreversível fora do escopo do plano (drop de banco em produção, force push em main, rotação de credencial real, deploy fora do combinado) — registra como pendência

## Bloqueios

Se um item não puder ser feito como pedido, **não invente workaround silencioso**. Pula o item, anota o bloqueio com o que faltou, e segue para o próximo. A regra global "Entrega 100% ou Para e Conversa" continua valendo — o "Para e Conversa" vira "Pula e Anota" porque o usuário está indisponível, mas a entrega ainda precisa ser honesta.

## Execução — motor decompõe → executa → revisa (Workflow)

A execução do plano **não roda solo no loop principal** — roda como **um Workflow determinístico** (a tool `Workflow`), mesmo padrão do `/qa-loop`: **motor = Workflow, casca = esta skill**. Três papéis, cada um no **tier certo pra etapa** (R8 — mesma tabela do `/qa-loop`, mesmos nomes de knob), e os freios (parada, paralelismo, fidelidade) são **lógica do script (JS)** — não "o Opus lembrar a regra a cada volta". É um **pipeline fechado**, por isso Workflow e não Agent Team.

### O sinal que arma o gate (obrigatório, e é a PRIMEIRA coisa)

Antes de disparar o Workflow, acenda o sinal; ao entregar o relatório, apague. É ele que faz o gate existir:

```bash
SOVAI_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"
mkdir -p "$SOVAI_DIR"
: > "$SOVAI_DIR/ativo-$CLAUDE_CODE_SESSION_ID"          # ao armar a missão
rm -f "$SOVAI_DIR"/{ativo,bloqueios}-"$CLAUDE_CODE_SESSION_ID"   # ao entregar
```

Enquanto o sinal está aceso, `plugins/sovai/hooks/pretooluse-sovai-motor.sh` **nega** todo disparo de sub-agente e manda rodar o Workflow. Fora do sovai ele é mudo. Desligamento: `SOVAI_GATE=0`.

⚠️ **Esqueceu de apagar o sinal, a sessão inteira fica sem despachar sub-agente.** Apagar é parte da entrega, não faxina opcional.

### Por que o gate precisou nascer

A frase que ficou aqui de 2026-08-01 até 2026-08-02 dizia que *"o guard `PreToolUse(Agent)` acorda a cada disparo"*. **Não acordava.** O guard que existe é o do `guardrails`, e ele foi escrito para **proteger** Agent Teams — a regra 3 dele libera explicitamente *"tarefa one-off sem team_name"*, que é exatamente a forma pela qual o `/sovai` descambava. A skill se apoiava numa proteção inexistente, e ninguém tinha como saber: prosa descrevendo mecanismo ausente não dá erro.

**O gate degrada, não trava.** Depois de 3 negações na mesma sessão ele desiste, libera e grava a desistência em `desistencias.log`. O motivo é o cenário: missão longa, dono ausente. Se a inferência de que o Workflow não passa por aqui estiver errada, a missão continua manca em vez de morrer parada.

## Modelo & effort por etapa (R8) — contrato em `references/r8-tiers.md`

O tier de cada etapa (modelo · effort · knob) e a semântica dos knobs são o **contrato R8 compartilhado** com o `/qa-loop`, vendorado em **`references/r8-tiers.md`** (fonte: `_shared/r8-tiers.md` — não editar a cópia à mão; `scripts/sync-shared.sh --check` pega drift). A tabela completa (Etapa · Modelo · Effort · Knob + o que cada knob significa + a regra de tier por rodada) está lá.

**É TUDO Opus 5** (contrato R8 desde 2026-07-26, vale pros dois motores): os seis knobs rodam `model: 'opus'` e só o **`effort`** varia por etapa. Aqui isso pesa dobrado — o `/sovai` roda com o usuário indisponível, sem checkpoint humano pra pegar execução rasa.

Abaixo, **onde cada knob entra NESTE motor** (decompõe→executa→revisa):

| Knob | Onde no motor |
|---|---|
| `decompose_model` | OPUS #1, **rodada 1** — quebra o plano inteiro em tarefas. |
| `coordinate_model` | OPUS #1 nas **rodadas 2+** (só o delta) + OPUS #2 nas rodadas normais. |
| `executor_model` | EXECUTORES — tarefa padrão (`complexity` ausente ou `'standard'`). |
| `mechanical_model` | EXECUTORES — tarefa marcada `complexity: 'mechanical'` (renomear, mover arquivo, 1 config, 1 valor — sem julgamento amplo). |
| `diagnose_model` | Tarefa reaparece em `missingTasks`/`gaps` por ≥ `churn_threshold` rodadas → diagnóstico de raiz antes de mandar o executor tentar de novo. |
| `finalize_model` | **Não consumido no caminho feliz** — a confirmação independente da obra é o `/qa-loop --headless` da etapa seguinte (que mantém o confirm-pass DELE). Só é consumido aqui pela **guarda**: sem `/qa-loop` na máquina, o motor roda um confirm-pass neste tier antes de declarar `built`. |

### Como o tier chega ao motor (obrigatório, antes de disparar o Workflow)

O valor do `effort` **não vive nesta skill**. Rode isto e passe o resultado dentro do
`args` do Workflow, junto com os outros parâmetros:

```bash
python3 "<skill_dir>/references/r8_tiers.py" args
# -> { "model": "opus", "tiers": { "decompose": {"effort": "high"}, ... } }
```

O script então lê `args.tiers.<knob>.effort` e nunca um literal. Se `args.tiers` chegar
`undefined` o motor morre na primeira volta, e essa é a falha certa: um default carimbado
no script seria mais uma cópia do valor, que é justamente o defeito que o contrato R8
existe pra impedir. Trocar um tier é editar `_shared/r8-tiers.json` e rodar
`scripts/sync-shared.sh` — nenhum `SKILL.md` muda.

### Knobs deste motor (a casca passa em `args`)

| Knob | Default | O que faz |
|---|---|---|
| `maxRounds` | `5` | **Trava de incêndio, não meta.** Teto de voltas do #1↔#2; estourou, o que faltou vira Bloqueio. |
| `severityFloor` | `P1` | Gap abaixo do floor não segura a obra de pé (vira nota no relatório, não nova rodada). |
| `churnThreshold` | `2` | Mesma tarefa reaparecendo N rodadas **seguidas** → escala pro `diagnose_model`. |
| `hasQaLoop` | detectado | `false` liga o **confirm-pass** em `finalize_model` antes de declarar `built` (ver a guarda no #2). A casca detecta se a skill `qa-loop` está disponível e passa o booleano — nunca deixa `undefined`, senão a guarda nunca arma. |

Precedência: flag da invocação > default acima. A casca **sempre** materializa os quatro antes de disparar o Workflow — `maxRounds` ausente faz o `while` do motor não rodar nenhuma volta e devolver "pronto" sem ter construído nada.

- **OPUS #1 — Decompositor.** NÃO planeja do zero. Pega o **plano que você deixou** e o quebra em tarefas de implementação, marcando para cada uma os **arquivos que toca**, se é **paralelizável**, de quais tarefas **depende**, e se é `complexity: 'mechanical'` (operação bem delimitada) ou `'standard'`. Cada tarefa carrega também o **`requisito`** que ela atende e o **`pronto`** que a declara feita — **os dois saem da spec, copiados; nunca redigidos aqui**. Executor não cumpre critério que não recebeu, e critério inventado pelo decompositor faz o revisor medir contra a régua errada. Item da spec que não traz os dois **não vira tarefa: vira Bloqueio** (`whyNeedsYou` = qual dos dois falta). Rodada 1 = `decompose_model` (plano inteiro); rodadas 2+ (re-decompõe só o delta do feedback do #2) = `coordinate_model`. Re-arquitetar é proibido (mesma regra do "não replanejar no headless"); buraco no plano que exija decisão de arquitetura vira **Bloqueio**, nunca invenção silenciosa.
- **EXECUTORES (Opus 5) — Implementam as tarefas.** Tarefa padrão = `executor_model`; `complexity: 'mechanical'` = `mechanical_model`. Independentes rodam **em paralelo**; dependentes, **em série** na ordem do #1. Tarefa única ou missão sequencial pura → o Workflow degenera pra um executor por vez, sem cerimônia (o fan-out é ganho só quando há independência real).

⚠️ **`isolation: 'worktree'` é PROIBIDO neste motor.** A regra anterior mandava isolar em worktree duas tarefas paralelas que tocassem o mesmo arquivo, e ela **queimou uma execução inteira em 2026-08-06**: 72 agentes para 25 tarefas, 15 delas executadas **3 vezes cada**, 8 diagnósticos de tarefa-presa, e 49 worktrees com trabalho dentro que ninguém leu.

O mecanismo da falha, e ele é estrutural, não um deslize: o executor termina dentro da cópia isolada, **e nada traz a cópia de volta**. O revisor (#2) confere no repositório de verdade, não encontra o trabalho, marca a tarefa como não-feita, e o decompositor (#1) manda refazer — para sempre, porque refazer também vai para uma cópia nova. O motor não tem como perceber: o sintoma que ele vê ("essa tarefa não sai do lugar") é indistinguível de executor incompetente, e por isso ele escala para o `diagnose_model` — gastando ainda mais.

**Colisão de arquivo se resolve dividindo o LOTE, nunca dividindo o repositório.** Dentro de uma onda, quem colide vai em sub-lotes seriais; todo mundo escreve no mesmo repo, e o revisor enxerga tudo. É mais lento só no caso raro de colisão real, e é sempre correto.

A regra geral que sobrou disto: **isolamento sem fusão declarada é dívida com cara de cuidado.** Se um dia este motor voltar a isolar, o passo que traz de volta nasce no mesmo commit — e o revisor precisa saber onde olhar.
- **OPUS #2 — Revisor de construção.** Julga a obra **contra a spec** — o plano que a casca passou em `planPath`/`planText`, e que o motor entrega ao #2 igual como entrega ao #1. A decomposição do #1 é **meio**, não fonte da verdade: revisar contra ela é circuito fechado, onde quem decompõe errado é aprovado errado. Cinco eixos: **spec** (a spec saiu, mesmo no que a decomposição não previu?) · **constituição** (o que saiu respeita as metas de qualidade autorais do projeto?) · **rastreio** (toda tarefa decomposta trouxe `requisito` e `pronto`?) · **completude** (toda tarefa decomposta saiu?) · **coesão** (as peças paralelas integram, sem se contradizer?). Desvio de spec vira gap de `kind: 'spec'` e **nasce em severidade ≥ floor**; se vier abaixo, o script o segura assim mesmo — senão sairia do filtro de severidade e passaria calado. **Eixo de rastreio:** tarefa decomposta sem `requisito` ou sem `pronto` **reprova** — vira gap de `kind: 'rastreio'`, que nasce em severidade ≥ floor e é segurado pelo script igual ao de spec. Tarefa sem requisito não tem contra o que ser medida, e sem `pronto` quem executa decide sozinho o que é "feito": nenhuma das duas passa calada. **Eixo de constituição:** o revisor **lê `.claude/docs/constituicao.md` e `.claude/docs/quality-goals.md` do projeto onde a missão está rodando** e sinaliza onde a implementação VIOLA o que está escrito lá. O arquivo é aberto na rodada, **nunca copiado para dentro desta skill** — a régua é a do projeto que instalou, e cópia em prosa defasa. Violação vira gap de `kind: 'constituicao'` pela rubrica de severidade normal, sem faixa própria. **A marca da lei é congelada na primeira volta:** o revisor devolve em `lawMark` a marca do texto que leu (o `cksum` do corpo dos dois arquivos, mesma receita da aprovação), o motor fixa a da rodada 1 e passa ela de volta nas seguintes — o #2 mede contra a lei fixada, nunca contra o texto novo. Lei editada no meio da missão vira **aviso no relatório** (Bloqueio "precisa de você"), porque as rodadas anteriores foram medidas contra o texto antigo; o que não pode acontecer é a régua trocar calada e duas rodadas da mesma missão medirem contra textos diferentes. **Projeto sem esse arquivo: o eixo simplesmente não roda** e a revisão segue com os outros quatro — ausência de constituição não é gap. **Quando a concepção está errada, e não o código:** o mesmo eixo cobre o caso em que o que a execução descobriu contradiz um documento de concepção já aprovado (`status: approved`) — a entrevista errou, o código está certo. Vira gap de `kind: 'concepcao'`, e o revisor **nunca reescreve documento aprovado** — nem o corpo (mexer nele reabre a etapa pela marca do de acordo) nem o frontmatter. O gap sobe como **aviso no relatório** (Bloqueio "precisa de você") propondo **reabrir a etapa**: nomeia o documento, a passagem contradita e a linha `correcao-pendente: {o que precisa mudar}` que o dono grava no frontmatter e cobra até reapresentar e reaprovar. Propor é do motor, escrever é do dono. Continua **não** caçando bug sutil nem rodando a suíte — profundidade de correção é do `/qa-loop` (etapa seguinte). Roda em `coordinate_model`; quando os cinco eixos batem, declara `built=true` **direto** — quem re-checa do zero é o `/qa-loop --headless` que roda logo em seguida (Fase Gate + confirm-pass dele). **Guarda (armada no script, não só na prosa):** com `hasQaLoop=false` o motor roda um **confirm-pass dedicado** em `finalize_model` antes de declarar `built` — sem `/qa-loop` adiante, fechar no veredito de `coordinate_model` seria declarar pronto sem nenhuma segunda checagem. Devolve **feedback estruturado pro #1**, que re-decompõe **só o delta** (o que faltou / precisa refazer) na volta seguinte. A seta de volta #2→#1 é o coração do motor.
- **DIAGNÓSTICO — escalada de tarefa-presa.** Se a MESMA tarefa reaparece em `missingTasks`/`gaps` por ≥ `churn_threshold` rodadas seguidas (default 2, mesmo limiar do `/qa-loop`), o motor escala ANTES de mandar o executor tentar de novo: um diagnóstico dedicado em `diagnose_model` (R8, "diagnóstico após falhas repetidas") investiga a causa raiz (dependência não mapeada, arquivo errado, premissa furada) em vez de repetir o mesmo pedido esperando resultado diferente. O diagnóstico entra no `feedback` da próxima rodada do #1.

### Fronteira com o `/qa-loop` (a spec é comum; o ângulo, não)

Os dois loops leem a **mesma spec** e perguntam coisas **diferentes** — e isso vai **escrito no prompt de cada papel** pra não duplicarem trabalho:

- **Este loop (#1↔#2) garante que está CONSTRUÍDO** — spec + constituição + rastreio + completude + coesão de montagem, medidas **contra a spec** e contra a `constituicao.md` e o `quality-goals.md` do projeto; a decomposição do #1 entra como meio (previu tudo? saiu tudo?), nunca como contrato final. Pergunta: _"a spec virou código inteiro e coerente?"_. **NÃO** caça bug sutil, **NÃO** roda a suíte, **NÃO** mexe em lint/type.
- **O `/qa-loop` (etapa seguinte) garante que está CORRETO** — bug, regressão, lint/type/test, segurança, e fidelidade ao plano com **profundidade de correção** (os 3 buckets dele). Pergunta: _"o código construído tem defeito?"_.

Resumo: **#2 = "está de pé, e é o que a spec pediu?" · qa-loop = "está certo?"**. O motor de implementação fecha quando a obra está de pé; o qa-loop entra **depois** pra procurar defeito. A spec é o eixo dos dois — o que muda é montagem aqui, defeito lá.

### Freio do loop (não é "até o #2 ficar feliz")

Revisão é poço sem fundo (mesma disciplina do review-loop: parada por retorno decrescente, não "até zero"). O loop #1↔#2 para no **primeiro** que ocorrer:
- **[primário]** #2 reporta `complete && cohesive` e **zero gap** acima do floor de severidade — gap de spec e de rastreio contam sempre, estejam onde estiverem na escala → obra de pé, segue pro QA.
- **[trava]** atingiu `maxRounds` (safety-cap, **não** meta) → o que faltou vira **Bloqueio (precisa de você)** no relatório.

### Esqueleto do motor (referência — o princípio, não código imutável)

A casca dispara a tool `Workflow` com o script abaixo. Os três schemas (`DECOMP`, `TASK_RESULT`, `BUILD_REVIEW`) são o que torna os gates determinísticos: o script lê campos estruturados, não texto solto.

```javascript
export const meta = {
  name: 'sovai-build-engine',
  description: 'Motor de implementação: tier por etapa (R8) — decompose/coordinate/executor/mechanical/diagnose/finalize',
  phases: [{ title: 'Decompor' }, { title: 'Diagnose' }, { title: 'Executar' },
           { title: 'Revisar' }, { title: 'Confirmar' }],
}

// args (da casca): { planPath, planText, maxRounds, severityFloor, repoRoot,
//                    churnThreshold, hasQaLoop }
const sevRank = s => ({ P0:3, P1:2, P2:1, P3:0 }[s] ?? 0)
const floor = sevRank(args.severityFloor || 'P1')
// default DENTRO do motor: sem isso, args.maxRounds undefined faz `r < undefined` ser
// false na 1ª volta — o motor devolveria "nada construído" em silêncio.
const maxRounds = args.maxRounds || 5
const churnThreshold = args.churnThreshold || 2
// 'shared' = a tarefa colide em arquivo com OUTRA do MESMO lote → vai em sub-lote SERIAL.
// NUNCA em worktree: o trabalho ficaria na cópia e o revisor confere no repo real (ver acima).
const touchesShared = (t, lote) => lote.some(o => o.id !== t.id && o.files?.some(f => t.files?.includes(f)))
const rounds = []; const blockers = []
let built = false, r = 0
let feedback = null   // do #2 pro #1 na volta seguinte (a seta de volta)
let lawMark = null    // marca da lei do projeto, CONGELADA na rodada 1 (ver o pino abaixo)
const taskChurn = {}  // { task_id: nº de rodadas seguidas reaparecendo em missingTasks/gaps }

// Tier por rodada (R8): rodada 1 = decompose_model (planejamento inicial); rodadas 2+
// = coordinate_model (coordenação rotineira). Os valores chegam em args.tiers, servidos
// de references/r8-tiers.json pela casca — nunca literais aqui.
const T = args.tiers
const tierFor = round => ({ model: args.model,
  effort: round === 1 ? T.decompose.effort : T.coordinate.effort })

while (!built && r < maxRounds) {
  r++; phase(`Rodada ${r}`)
  const tier = tierFor(r)

  // DECOMPOR — Opus #1, no tier da rodada. r==1: decompõe o plano inteiro; r>1: só o
  // DELTA do feedback. NUNCA re-arquiteta; buraco que exige decisão de arquitetura
  // vira blocker (não vira tarefa).
  const decomp = await agent(decomposePrompt({ planPath: args.planPath, planText: args.planText, round: r, feedback }),
    { model: tier.model, effort: tier.effort, phase: 'Decompor', schema: DECOMP })
  // Decompositor morto derruba a rodada inteira (não há tarefa a executar). Sai do laço em
  // vez de estourar — o que já foi construído nas rodadas anteriores continua valendo.
  if (!decomp) {
    blockers.push({ what: `decompositor da rodada ${r} não respondeu`,
                    whyNeedsYou: 'sem decomposição não há o que executar nesta volta' })
    break
  }
  if (decomp.blockers?.length) blockers.push(...decomp.blockers)

  // DIAGNÓSTICO de tarefa-presa — antes de tentar de novo, escala quem já reaparece
  // ≥ churnThreshold rodadas seguidas pro diagnose_model (medium): causa raiz, não repetição.
  const diagnoses = []
  for (const t of decomp.tasks) {
    if (taskChurn[t.id] >= churnThreshold) {
      const diag = await agent(diagnoseStuckTaskPrompt({ task: t, attempts: taskChurn[t.id] }),
        { model: args.model, effort: T.diagnose.effort, phase: 'Diagnose' })   // diagnose_model
      diagnoses.push({ task_id: t.id, diagnosis: diag })
    }
  }

  // EXECUTAR — Opus 5 em todo tier (R8). executor_model (padrão) ou mechanical_model
  // (tarefa marcada complexity:'mechanical' — operação bem delimitada, sem julgamento
  // amplo). Só o effort varia; o modelo é sempre opus.
  const todo = decomp.tasks.filter(t => !t.done)
  const par = todo.filter(t => t.parallelizable && !(t.dependsOn?.length))
  const seq = todo.filter(t => !t.parallelizable || (t.dependsOn?.length))
  const execTier = t => ({ model: args.model,
    effort: t.complexity === 'mechanical' ? T.mechanical.effort : T.executor.effort })
  // quem NÃO colide vai junto; quem colide vai depois, um de cada vez, no MESMO repo
  const livres = par.filter(t => !touchesShared(t, par))
  const colidem = par.filter(t => touchesShared(t, par))
  const builtPar = await parallel(livres.map(t => () =>
    agent(execPrompt({ task: t }), {
      model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT })))
  for (const t of colidem) builtPar.push(await agent(execPrompt({ task: t }),
    { model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT }))
  const builtSeq = []
  for (const t of seq) builtSeq.push(await agent(execPrompt({ task: t }),
    { model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT }))
  // Os DOIS lados filtram: `parallel()` devolve null pra thunk que falhou, e o executor
  // sequencial devolve null pelo mesmo motivo (agente morto). Filtrar só o paralelo deixava
  // um `null` entrar em `results` e virar `TypeError` no revisor — a tarefa some do relato
  // em vez de reaparecer em `missingTasks`, que é o caminho que a manda de volta pro #1.
  const results = builtPar.filter(Boolean).concat(builtSeq.filter(Boolean))

  // REVISAR — Opus #2, no tier da rodada (coordinate_model). Contra a SPEC (o plano vai
  // junto, igual ao #1): spec + constituição + rastreio + completude + coesão. A decomposição
  // entra como meio, não como contrato. O eixo de rastreio reprova tarefa decomposta sem
  // `requisito` ou sem `pronto` (gap kind:'rastreio'). O eixo de constituição manda LER
  // `<repoRoot>/.claude/docs/constituicao.md` e o `quality-goals.md` na rodada (nunca
  // uma cópia daqui) e é
  // fail-open: arquivo ausente = eixo não roda, e isso NÃO vira gap.
  // NÃO roda a suíte nem caça bug — isso é o /qa-loop depois.
  // `lawMark` vai junto: na rodada 1 é null (o #2 calcula e devolve); nas seguintes é a
  // marca FIXADA, contra a qual ele mede — não contra o texto que estiver no disco agora.
  const review = await agent(reviewBuildPrompt({ planPath: args.planPath, planText: args.planText, repoRoot: args.repoRoot, decomp, results, round: r, lawMark }),
    { model: tier.model, effort: tier.effort, phase: 'Revisar', schema: BUILD_REVIEW })

  // AGENTE MORTO NÃO PODE DERRUBAR O MOTOR. `agent()` devolve null quando o subagente
  // morre por erro terminal (limite de sessão, erro de API depois dos retries) ou quando o
  // usuário o pula. Sem esta guarda, `review.gaps` levanta TypeError e o script inteiro
  // aborta — perdendo TODAS as rodadas já concluídas. Medido em 2026-08-02: uma execução
  // deste motor morreu exatamente assim, com 8 dos 12 agentes já entregues, e o resultado
  // veio como falha total em vez de "faltaram 4".
  //
  // A direção segura é NÃO declarar built: revisor que não respondeu não aprovou nada.
  // Vira blocker e o loop segue — a missão degrada, não morre.
  if (!review) {
    blockers.push({ what: `revisor da rodada ${r} não respondeu`,
                    whyNeedsYou: 'a obra desta rodada ficou SEM revisão — trate como não verificada' })
    rounds.push({ r, decomp, results, review: null, diagnoses })
    feedback = { gaps: [], missing: [], diagnoses }
    continue
  }

  // MARCA DA LEI — congelada na 1ª volta. Sem o pino, cada rodada media contra o
  // arquivo que estivesse no disco naquele instante: editar a constituição no meio da
  // missão trocava a régua CALADA, e a rodada 1 e a 4 aprovavam coisas diferentes sem
  // ninguém saber. O pino é do motor, não da memória do revisor.
  if (review.lawMark) {
    if (lawMark === null) lawMark = review.lawMark
    else if (review.lawMark !== lawMark) {
      // Não troca o pino: a missão segue medindo contra a lei fixada, e a mudança vira
      // aviso no relatório pro dono julgar o que fazer com as rodadas já aprovadas.
      blockers.push({ what: `a lei do projeto mudou durante a missão (marca ${lawMark} → ${review.lawMark}, rodada ${r})`,
                      whyNeedsYou: 'as rodadas anteriores foram medidas contra o texto antigo — confira o que mudou antes de aceitar a obra' })
    }
  }

  // A CONCEPÇÃO ERROU — a execução descobriu algo que contradiz um documento já
  // aprovado. O motor NÃO reescreve documento do dono: o gap vira aviso no relatório
  // propondo reabrir a etapa (a linha `correcao-pendente:` que ELE grava), e não volta
  // pro #1 — não há o que o executor conserte no código.
  for (const g of (review.gaps || []).filter(g => g.kind === 'concepcao')) {
    blockers.push({ what: `a concepção está errada: ${g.problem}`,
                    whyNeedsYou: 'reabra a etapa — grave `correcao-pendente:` no frontmatter do documento e reaprove; nenhum documento foi alterado aqui' })
  }

  // Executor morto entra pela mesma porta: `results` já vem filtrado com `.filter(Boolean)`,
  // então a tarefa dele reaparece como faltante no próximo `missingTasks` e volta pro #1.

  // churn de tarefa — conta rodadas SEGUIDAS, não acumuladas. Set por rodada: 2 gaps na
  // mesma tarefa contam 1, e quem NÃO reapareceu ZERA. Sem o zerar, uma tarefa resolvida
  // na rodada 3 ainda dispararia o diagnóstico caro na 5 por causa do placar antigo.
  const stuck = new Set([...(review.missingTasks || []), ...(review.gaps || []).map(g => g.task_id)])
  for (const t of decomp.tasks) taskChurn[t.id] = stuck.has(t.id) ? (taskChurn[t.id] || 0) + 1 : 0

  rounds.push({ r, decomp, results, review, diagnoses })
  // desvio de spec e falta de requisito/pronto seguram a obra SEMPRE: nascem em severidade
  // >= floor, e se o revisor devolver abaixo o script os mantém no filtro. Sem isso um gap
  // de spec P2/P3 sairia da conta e passaria calado — o freio é do script, não da memória
  // do revisor.
  // gap de concepção sai do filtro por decisão: ele já virou aviso acima, e segurar a obra
  // por ele empurraria o motor a "consertar" código que está certo.
  const holdsBuild = g => g.kind !== 'concepcao' && (g.kind === 'spec' || g.kind === 'rastreio' || sevRank(g.severity) >= floor)
  const gaps = (review.gaps || []).filter(holdsBuild)

  // BUILT — no caminho feliz a confirmação independente é o /qa-loop --headless da etapa
  // seguinte (Fase Gate + confirm-pass DELE), então aqui declara direto. SEM qa-loop na
  // máquina (hasQaLoop=false) não existe segunda checagem lá na frente: o motor NÃO pode
  // fechar no veredito barato da rodada — roda o confirm-pass dedicado em finalize_model.
  if (review.complete && review.cohesive && gaps.length === 0) {
    if (args.hasQaLoop === false) {
      const confirm = await agent(confirmBuildPrompt({ planPath: args.planPath, planText: args.planText, repoRoot: args.repoRoot, decomp, results, lawMark }),
        { model: args.model, effort: T.finalize.effort, phase: 'Confirmar', schema: BUILD_REVIEW })   // finalize_model
      rounds[rounds.length - 1].confirm = confirm
      // Mesma guarda do revisor, e aqui a direção segura é mais dura ainda: este pass é a
      // ÚNICA segunda checagem que existe quando não há /qa-loop adiante. Ele não responder
      // significa que ninguém confirmou nada — declarar `built` seria dar por pronto no
      // veredito de um agente que morreu.
      if (!confirm) {
        blockers.push({ what: 'o confirm-pass não respondeu',
                        whyNeedsYou: 'sem /qa-loop e sem confirm, NADA checou a obra — não considere entregue' })
        break
      }
      const confirmGaps = (confirm.gaps || []).filter(holdsBuild)
      if (!confirm.complete || !confirm.cohesive || confirmGaps.length) {
        // o confirm achou o que a rodada barata perdeu — processa, não ignora
        feedback = { gaps: confirm.gaps.filter(g => g.kind !== 'concepcao'), missing: confirm.missingTasks, diagnoses }
        continue
      }
    }
    built = true; break
  }
  // sem o gap de concepção: ele é aviso pro dono, não tarefa pro #1 re-decompor.
  feedback = { gaps: review.gaps.filter(g => g.kind !== 'concepcao'), missing: review.missingTasks, diagnoses }   // alimenta o DECOMPOR da próxima volta
}

return {
  rounds, built, blockers, lawMark,   // lawMark = a lei contra a qual a missão INTEIRA foi medida
  stopReason: built ? 'build-complete' : 'max-rounds',
  telemetry: rounds.map(x => ({ round: x.r, tasks: x.results.length, gaps: x.review.gaps.length })),
}
```

**Schemas (JSON Schema, resumidos):**
- `DECOMP` — `{ tasks: [{ id, desc, requisito, pronto, files: [...], parallelizable: bool, dependsOn: [id...], done: bool, complexity?: 'standard'|'mechanical' }], blockers: [{ what, whyNeedsYou }] }`. **`requisito` e `pronto` são obrigatórios** — `requisito` = o item da spec que a tarefa atende, `pronto` = o critério de feito dele, **os dois copiados da spec, não redigidos pelo decompositor** (o executor não tem como cumprir o que não recebe, e critério inventado aqui vira régua falsa no #2). Item da spec sem um dos dois vira `blocker`, não tarefa. `complexity: 'mechanical'` = operação bem delimitada (renomear, mover arquivo, 1 config, 1 valor); ausente/`'standard'` = tarefa normal.
- `TASK_RESULT` — `{ task_id, files_touched: [...], summary, done: bool, note }`.
- `BUILD_REVIEW` — `{ complete: bool, cohesive: bool, gaps: [{ task_id, kind: 'spec'|'constituicao'|'concepcao'|'rastreio'|'completude'|'coesao', severity: 'P0'|'P1'|'P2'|'P3', problem }], missingTasks: [id...], lawMark: string|null }`. **`lawMark`** = a marca da lei que ESTA rodada leu — o `cksum` do corpo de `.claude/docs/constituicao.md` + `.claude/docs/quality-goals.md` (mesma receita da marca de aprovação; corpo, sem frontmatter). Projeto sem esses arquivos devolve `null` e o pino nunca arma. O motor congela a marca da rodada 1 e a devolve ao revisor nas seguintes; marca diferente da fixada **não** troca a régua — vira aviso no relatório (Bloqueio "precisa de você"). `kind: 'rastreio'` = tarefa decomposta chegou **sem `requisito` ou sem `pronto`** — nasce em severidade **≥ `severityFloor`** e o script o segura no filtro mesmo se vier abaixo (mesmo tratamento do gap de spec), porque tarefa sem os dois campos não é medível por ninguém depois. `kind: 'spec'` = o que a spec pede não saiu (ou saiu diferente), **mesmo com a decomposição cumprida** — nasce em severidade **≥ `severityFloor`** (P1 por default) e o script o mantém no filtro mesmo se vier abaixo, senão o gap sai da conta e passa calado. `kind: 'constituicao'` = o que saiu viola a `.claude/docs/constituicao.md` ou o `.claude/docs/quality-goals.md` do projeto — severidade normal (o filtro de floor vale), e `problem` cita a passagem violada, porque a régua vive no arquivo lido na rodada, não aqui. Sem esse arquivo no projeto, este `kind` simplesmente não aparece. `kind: 'concepcao'` = o que a execução descobriu contradiz um documento de concepção já aprovado — **não segura a obra** (o executor não tem o que consertar no código), sai do filtro e vira aviso no relatório propondo reabrir a etapa, com a linha `correcao-pendente:` sugerida em `problem`. `task_id` de gap de spec ou de constituição pode ser `null`: o buraco que a decomposição não previu não tem tarefa a que pertencer.

O `stopReason`, os `blockers` e a telemetria entram no relatório final (`### Verificação` e `### Bloqueios`). Terminado o motor (`built` ou teto), segue direto pro **QA final** abaixo — que é onde defeito é caçado.

## QA final (antes do relatório)

Terminada a execução e **ANTES** de montar o relatório, rode a skill `/qa-loop` em **modo headless** sobre o que você implementou, passando o plano como âncora:

```
/qa-loop <mudanças desta sessão> --plan=<plano> --headless
```

Como o usuário está indisponível, o headless nunca pergunta nada. Trate os 3 buckets assim:
- **Implementação** (bug / divergência do plano) → conserta no loop. Você já tem mandato de executar o plano; o regression gate por conserto é a rede que evita as regressões auto-infligidas.
- **Plan-drift** (um "fix" afastaria do plano em UX/backend/proposta) → **reverte pro plano**. Não "melhore" pra longe do combinado.
- **Plano/arquitetura falho** → **NÃO implemente**. Vira item de "Bloqueios (precisam de você)" no relatório. Headless **não** é licença pra re-planejar.

O relatório do `/qa-loop` (loops rodados, correções, regressões pegas, alertas de plano) vira a seção `### QA` do relatório final.

**Se a skill `qa-loop` não estiver disponível** (foi o que você passou como `hasQaLoop=false` ao motor): o confirm-pass do motor já cobriu "está construído", mas **ninguém checou "está correto"**. Rode você mesmo o gate objetivo do projeto (lint · type · unit · integração, 100% verde no repo) e registre o resultado na `### Verificação`; o que não deu pra checar vai pra `### Bloqueios` dizendo **o que ficou sem cobertura** — nunca "QA ok".

## Persistência — doc + commit/push (antes do relatório)

Passada a QA e **ANTES** de montar o relatório, persista o trabalho. Esta é a última etapa de execução; o relatório só descreve o que já está salvo.

1. **Atualiza a doc.** Invoque a skill **`doc-touch`** (Skill tool, `skill: "project-doc:doc-touch"`) — **não** o `project-doc` FULL. Uma execução autônoma costuma mexer em arquivos, e a doc tem que refletir a realidade antes de você fechar; mas o caso comum é diff que cabe no `scope:` de 2-4 docs, e reminerar o repo inteiro pra isso é gasto puro. (Não "digite /doc-touch" — invoque a skill.)

   **Quem decide touch-vs-FULL é o próprio touch, não você.** O passo 1 dele calcula `last_full_age_days` (a data de `ledger.last_commit`, que só o FULL avança) e **escala pro FULL sozinho** se passou de 30 dias ou se o número não resolve. Aqui você está em modo autônomo: o touch escala **e segue**, sem perguntar. Não tente antecipar a decisão — a informação nasce lá, e mecanizar "isso é estrutural?" daqui é chutar.
2. **Commit + push.** Stage do que esta sessão mudou, commit com mensagem no padrão do repo (`feat(...)`/`fix(...)`/`docs(...)`, 1 linha) e push pra **branch atual**.
   - **Nunca** `--force`; **nunca** push direto numa branch protegida (`main`/`master`) — se a sessão estiver nela, crie uma branch de feature antes (mesma regra do "force push em main" do Contrato) e registre como decisão.
   - Árvore limpa (nada pra commitar) → pula e anota "nada a persistir".
   - Falha de push (sem remote, sem auth, rejeição) → **não force**; registra como `Bloqueio (precisa de você)` com o erro real e segue pro relatório (o commit local fica feito).

3. **Apaga o sinal do sovai.** É o par do `mkdir` da seção _Execução_, e é obrigatório:

   ```bash
   rm -f "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"/{ativo,bloqueios}-"$CLAUDE_CODE_SESSION_ID"
   ```

   Deixar aceso faz a sessão inteira continuar sem poder despachar sub-agente **depois** de a missão acabar — o gate não sabe que você terminou, só sabe do arquivo.

O hash do commit + resultado do push entram na `### Verificação`; a doc regenerada é um item de `### Feito`.

## Relatório Final

O relatório é a única coisa que o usuário lê desta sessão — e ele lê **depois**, pra revisar tudo e refatorar. Por isso ele sai como uma **superfície de revisão em HTML**, não como textão no CLI.

### Conteúdo (backbone — sempre o mesmo)

Cinco seções. Monte este conteúdo PRIMEIRO; a forma de entrega (HTML ou markdown) vem depois.

```
## Sovai — terminei

### Feito
- [só o que foi verificado]

### Decisões tomadas
- [decisão]: [razão em 1 linha]

### Bloqueios (precisam de você)
- [item pulado]: [o que faltou]

### Verificação
- [o que rodou, e o resultado — incluindo doc atualizada (doc-touch ou FULL, e qual dos dois), commit e push]

### QA (qa-loop)
- [loops rodados + critério de parada · correções aplicadas · regressões pegas na hora]
- [⚠️ alertas de plano/arquitetura que NÃO implementei — pra você julgar]
```

### Entrega via /visual (titular)

Se a Skill **`visual`** estiver entre as suas skills disponíveis, **invoque-a** (Skill tool, `skill: "visual"`) e renderize o relatório como HTML. (Não "digite /visual" — invoque a skill.) `visual` é **dependência recomendada** do sovai; instale os dois juntos.

Por que HTML: o relatório é longo e completo, e o usuário vai **revisar item a item e refatorar**. O `/visual` tem o componente exato pra isso — veredito inline (`.feedback-item`: ✓ Manter / ✏️ Mudar / ✗ Remover) que ele marca enquanto lê.

**Mapeamento seção → componente** (instrua o /visual a montar a superfície de revisão):

No spec, **`item_labels: ["✓ Manter", "✏️ Mudar", "✗ Remover"]`** — NUNCA "✓ Vira ação" (esse é do relatório do /qa-loop: lá cada achado vira ação no próximo plano).

- **Bloqueios (precisam de você)** → **topo**, prioridade máxima. Default: `.callout` severidade alta (um bloqueio é "não consegui X porque faltou Y" — sem ramificação). **Só** vire `.decision-card` se houver escolha A/B **genuína** já clara — nunca fabrique duas opções pra preencher o card (regra anti-"chutar"). Os ⚠️ alertas de plano/arquitetura do qa-loop entram aqui (normalmente `.callout`; só decision-card se for binário de verdade).
- **Feito** → cada item = `.feedback-item` com veredito inline + profundidade em `<details>`. O usuário revisa enquanto lê.
- **Decisões tomadas** → cada decisão = `.feedback-item` (o usuário aprova ou marca pra rever) + razão em 1 linha.
- **Verificação** → `.callout` (ok/danger): o que rodou + resultado. Read-only.
- **QA (qa-loop)** → `.callout`/seção: loops, correções, regressões, alertas. Read-only.
- `.exec` no fim + **caixa de fechamento**: no caso comum (feedback-items + callouts) só `feedback-box`; `decisions-box` só se houver decision-card de verdade. As caixas são **só fechamento** (progresso + observação + botões) — **nunca re-listam os itens** (anti-pattern "duas tabelas").

**Retorno do feedback é assíncrono.** O usuário está fora e esta sessão termina quando o relatório sai — então **não** conte com live-sync ("ele diz ok e o Claude lê"). O HTML guarda os vereditos em `localStorage`; quando ele voltar (provável sessão nova), clica "Copiar feedback"/"Copiar escolhas" e cola pra dirigir o refactor. O daemon do /visual pode subir (é inócuo), mas o caminho confiável é copy/paste.

**CLI mínimo** (o /visual proíbe duplicar o conteúdo no CLI): emita só

```
Sovai terminou. Relatório completo no browser: <path>
⚠️ Bloqueios (precisam de você): <título 1> · <título 2>   ← só os títulos, se houver
```

Os títulos dos bloqueios são um **índice** (não o conteúdo) — segurança, porque bloqueio é crítico e o usuário precisa vê-los mesmo sem abrir o browser. Nada além disso no CLI.

### Fallback (markdown)

Se a Skill `visual` **não** estiver disponível, emita o **relatório markdown completo** (o bloco de conteúdo acima, com as 5 seções preenchidas) direto no CLI. É um fallback à altura: entrega 100% da mesma informação — só a apresentação degrada, não o conteúdo.

Detalhe técnico só se o usuário pedir depois.
