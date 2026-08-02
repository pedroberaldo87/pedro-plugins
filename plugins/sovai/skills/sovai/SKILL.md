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

| Knob | Modelo · effort | Onde no motor |
|---|---|---|
| `decompose_model` | Opus · `xhigh` | OPUS #1, **rodada 1** — quebra o plano inteiro em tarefas. |
| `coordinate_model` | Opus · `high` | OPUS #1 nas **rodadas 2+** (só o delta) + OPUS #2 nas rodadas normais. |
| `executor_model` | Opus · `high` | EXECUTORES — tarefa padrão (`complexity` ausente ou `'standard'`). |
| `mechanical_model` | Opus · `medium` | EXECUTORES — tarefa marcada `complexity: 'mechanical'` (renomear, mover arquivo, 1 config, 1 valor — sem julgamento amplo). |
| `diagnose_model` | Opus · `xhigh` | Tarefa reaparece em `missingTasks`/`gaps` por ≥ `churn_threshold` rodadas → diagnóstico de raiz antes de mandar o executor tentar de novo. |
| `finalize_model` | Opus · `xhigh` | **Não consumido no caminho feliz** — a confirmação independente da obra é o `/qa-loop --headless` da etapa seguinte (que mantém o confirm-pass DELE). Só é consumido aqui pela **guarda**: sem `/qa-loop` na máquina, o motor roda um confirm-pass neste tier antes de declarar `built`. |

### Knobs deste motor (a casca passa em `args`)

| Knob | Default | O que faz |
|---|---|---|
| `maxRounds` | `5` | **Trava de incêndio, não meta.** Teto de voltas do #1↔#2; estourou, o que faltou vira Bloqueio. |
| `severityFloor` | `P1` | Gap abaixo do floor não segura a obra de pé (vira nota no relatório, não nova rodada). |
| `churnThreshold` | `2` | Mesma tarefa reaparecendo N rodadas **seguidas** → escala pro `diagnose_model`. |
| `hasQaLoop` | detectado | `false` liga o **confirm-pass** em `finalize_model` antes de declarar `built` (ver a guarda no #2). A casca detecta se a skill `qa-loop` está disponível e passa o booleano — nunca deixa `undefined`, senão a guarda nunca arma. |

Precedência: flag da invocação > default acima. A casca **sempre** materializa os quatro antes de disparar o Workflow — `maxRounds` ausente faz o `while` do motor não rodar nenhuma volta e devolver "pronto" sem ter construído nada.

- **OPUS #1 — Decompositor.** NÃO planeja do zero. Pega o **plano que você deixou** e o quebra em tarefas de implementação, marcando para cada uma os **arquivos que toca**, se é **paralelizável**, de quais tarefas **depende**, e se é `complexity: 'mechanical'` (operação bem delimitada) ou `'standard'`. Rodada 1 = `decompose_model` (plano inteiro); rodadas 2+ (re-decompõe só o delta do feedback do #2) = `coordinate_model`. Re-arquitetar é proibido (mesma regra do "não replanejar no headless"); buraco no plano que exija decisão de arquitetura vira **Bloqueio**, nunca invenção silenciosa.
- **EXECUTORES (Opus 5) — Implementam as tarefas.** Tarefa padrão = `executor_model` (Opus `high`); `complexity: 'mechanical'` = `mechanical_model` (Opus `medium`). Independentes rodam **em paralelo**; dependentes, **em série** na ordem do #1. Duas tarefas paralelas que tocam o mesmo arquivo → `isolation: 'worktree'` (senão se atropelam). Tarefa única ou missão sequencial pura → o Workflow degenera pra um executor por vez, sem cerimônia (o fan-out é ganho só quando há independência real).
- **OPUS #2 — Revisor de construção.** Trata a decomposição do #1 como **contrato** e só checa se ele foi **cumprido**: toda tarefa decomposta saiu? (completude) · as peças paralelas integram, sem se contradizer? (coesão). **Não julga se a decomposição é fiel ao plano-macro** — isso é exclusivo do `/qa-loop` (etapa seguinte, bucket 1 dele). Roda em `coordinate_model`; quando completude+coesão batem, declara `built=true` **direto** — quem re-checa do zero é o `/qa-loop --headless` que roda logo em seguida (Fase Gate + confirm-pass dele). **Guarda (armada no script, não só na prosa):** com `hasQaLoop=false` o motor roda um **confirm-pass dedicado** em `finalize_model` (Opus `xhigh`) antes de declarar `built` — sem `/qa-loop` adiante, fechar no veredito de `coordinate_model` seria declarar pronto sem nenhuma segunda checagem. Devolve **feedback estruturado pro #1**, que re-decompõe **só o delta** (o que faltou / precisa refazer) na volta seguinte. A seta de volta #2→#1 é o coração do motor.
- **DIAGNÓSTICO — escalada de tarefa-presa.** Se a MESMA tarefa reaparece em `missingTasks`/`gaps` por ≥ `churn_threshold` rodadas seguidas (default 2, mesmo limiar do `/qa-loop`), o motor escala ANTES de mandar o executor tentar de novo: um diagnóstico dedicado em `diagnose_model` (Opus xhigh, R8 "diagnóstico após falhas repetidas") investiga a causa raiz (dependência não mapeada, arquivo errado, premissa furada) em vez de repetir o mesmo pedido esperando resultado diferente. O diagnóstico entra no `feedback` da próxima rodada do #1.

### Fronteira com o `/qa-loop` (ângulos separados, sem retrabalho)

Os dois loops olham coisas **diferentes** — e isso vai **escrito no prompt de cada papel** pra não duplicarem trabalho:

- **Este loop (#1↔#2) garante que está CONSTRUÍDO** — completude + coesão de montagem, medidas **contra a decomposição do #1 (o contrato)**, não contra o plano-macro. Pergunta: _"a decomposição virou código inteiro e coerente?"_. **NÃO** julga fidelidade ao plano-macro, **NÃO** caça bug sutil, **NÃO** roda a suíte, **NÃO** mexe em lint/type.
- **O `/qa-loop` (etapa seguinte) garante que está CORRETO** — bug, regressão, lint/type/test, segurança, e fidelidade ao **plano-macro** (os 3 buckets dele). Pergunta: _"o código construído tem defeito?"_.

Resumo: **#2 = "está pronto?" · qa-loop = "está certo?"**. O motor de implementação fecha quando a obra está de pé; o qa-loop entra **depois** pra procurar defeito. Sem sobreposição: completude/coesão aqui, correção lá.

### Freio do loop (não é "até o #2 ficar feliz")

Revisão é poço sem fundo (mesma disciplina do review-loop: parada por retorno decrescente, não "até zero"). O loop #1↔#2 para no **primeiro** que ocorrer:
- **[primário]** #2 reporta `complete && cohesive` e **zero gap de fidelidade** acima do floor de severidade → obra de pé, segue pro QA.
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
// 'shared' = a tarefa colide em arquivo com OUTRA paralela do MESMO lote → isola em worktree
const touchesShared = (t, lote) => lote.some(o => o.id !== t.id && o.files?.some(f => t.files?.includes(f)))
const rounds = []; const blockers = []
let built = false, r = 0
let feedback = null   // do #2 pro #1 na volta seguinte (a seta de volta)
const taskChurn = {}  // { task_id: nº de rodadas seguidas reaparecendo em missingTasks/gaps }

// Tier por rodada (R8 — tabela única com /qa-loop): rodada 1 = decompose_model (xhigh,
// planejamento inicial); rodadas 2+ = coordinate_model (high, coordenação rotineira).
const tierFor = round => round === 1
  ? { model: 'opus', effort: 'xhigh' }   // decompose_model
  : { model: 'opus', effort: 'high' }    // coordinate_model

while (!built && r < maxRounds) {
  r++; phase(`Rodada ${r}`)
  const tier = tierFor(r)

  // DECOMPOR — Opus #1, no tier da rodada. r==1: decompõe o plano inteiro; r>1: só o
  // DELTA do feedback. NUNCA re-arquiteta; buraco que exige decisão de arquitetura
  // vira blocker (não vira tarefa).
  const decomp = await agent(decomposePrompt({ planPath: args.planPath, planText: args.planText, round: r, feedback }),
    { model: tier.model, effort: tier.effort, phase: 'Decompor', schema: DECOMP })
  if (decomp.blockers?.length) blockers.push(...decomp.blockers)

  // DIAGNÓSTICO de tarefa-presa — antes de tentar de novo, escala quem já reaparece
  // ≥ churnThreshold rodadas seguidas pro diagnose_model (xhigh): causa raiz, não repetição.
  const diagnoses = []
  for (const t of decomp.tasks) {
    if (taskChurn[t.id] >= churnThreshold) {
      const diag = await agent(diagnoseStuckTaskPrompt({ task: t, attempts: taskChurn[t.id] }),
        { model: 'opus', effort: 'xhigh', phase: 'Diagnose' })   // diagnose_model (contrato R8)
      diagnoses.push({ task_id: t.id, diagnosis: diag })
    }
  }

  // EXECUTAR — Opus 5 em todo tier (R8). executor_model (padrão) ou mechanical_model
  // (tarefa marcada complexity:'mechanical' — operação bem delimitada, sem julgamento
  // amplo). Só o effort varia; o modelo é sempre opus.
  const todo = decomp.tasks.filter(t => !t.done)
  const par = todo.filter(t => t.parallelizable && !(t.dependsOn?.length))
  const seq = todo.filter(t => !t.parallelizable || (t.dependsOn?.length))
  const execTier = t => t.complexity === 'mechanical'
    ? { model: 'opus', effort: 'medium' }    // mechanical_model
    : { model: 'opus', effort: 'high' }      // executor_model
  const builtPar = await parallel(par.map(t => () =>
    agent(execPrompt({ task: t }), {
      model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT,
      isolation: touchesShared(t, par) ? 'worktree' : undefined })))
  const builtSeq = []
  for (const t of seq) builtSeq.push(await agent(execPrompt({ task: t }),
    { model: execTier(t).model, effort: execTier(t).effort, phase: 'Executar', schema: TASK_RESULT }))
  const results = builtPar.filter(Boolean).concat(builtSeq)

  // REVISAR — Opus #2, no tier da rodada (coordinate_model). Contra a DECOMPOSIÇÃO:
  // completude + coesão + fidelidade. NÃO roda a suíte nem caça bug — isso é o /qa-loop depois.
  const review = await agent(reviewBuildPrompt({ decomp, results, round: r }),
    { model: tier.model, effort: tier.effort, phase: 'Revisar', schema: BUILD_REVIEW })

  // churn de tarefa — conta rodadas SEGUIDAS, não acumuladas. Set por rodada: 2 gaps na
  // mesma tarefa contam 1, e quem NÃO reapareceu ZERA. Sem o zerar, uma tarefa resolvida
  // na rodada 3 ainda dispararia o diagnóstico caro na 5 por causa do placar antigo.
  const stuck = new Set([...(review.missingTasks || []), ...(review.gaps || []).map(g => g.task_id)])
  for (const t of decomp.tasks) taskChurn[t.id] = stuck.has(t.id) ? (taskChurn[t.id] || 0) + 1 : 0

  rounds.push({ r, decomp, results, review, diagnoses })
  const gaps = (review.gaps || []).filter(g => sevRank(g.severity) >= floor)

  // BUILT — no caminho feliz a confirmação independente é o /qa-loop --headless da etapa
  // seguinte (Fase Gate + confirm-pass DELE), então aqui declara direto. SEM qa-loop na
  // máquina (hasQaLoop=false) não existe segunda checagem lá na frente: o motor NÃO pode
  // fechar no veredito barato da rodada — roda o confirm-pass dedicado em finalize_model.
  if (review.complete && review.cohesive && gaps.length === 0) {
    if (args.hasQaLoop === false) {
      const confirm = await agent(confirmBuildPrompt({ decomp, results }),
        { model: 'opus', effort: 'xhigh', phase: 'Confirmar', schema: BUILD_REVIEW })   // finalize_model
      rounds[rounds.length - 1].confirm = confirm
      const confirmGaps = (confirm.gaps || []).filter(g => sevRank(g.severity) >= floor)
      if (!confirm.complete || !confirm.cohesive || confirmGaps.length) {
        // o confirm achou o que a rodada barata perdeu — processa, não ignora
        feedback = { gaps: confirm.gaps, missing: confirm.missingTasks, diagnoses }
        continue
      }
    }
    built = true; break
  }
  feedback = { gaps: review.gaps, missing: review.missingTasks, diagnoses }   // alimenta o DECOMPOR da próxima volta
}

return {
  rounds, built, blockers,
  stopReason: built ? 'build-complete' : 'max-rounds',
  telemetry: rounds.map(x => ({ round: x.r, tasks: x.results.length, gaps: x.review.gaps.length })),
}
```

**Schemas (JSON Schema, resumidos):**
- `DECOMP` — `{ tasks: [{ id, desc, files: [...], parallelizable: bool, dependsOn: [id...], done: bool, complexity?: 'standard'|'mechanical' }], blockers: [{ what, whyNeedsYou }] }`. `complexity: 'mechanical'` = operação bem delimitada (renomear, mover arquivo, 1 config, 1 valor); ausente/`'standard'` = tarefa normal.
- `TASK_RESULT` — `{ task_id, files_touched: [...], summary, done: bool, note }`.
- `BUILD_REVIEW` — `{ complete: bool, cohesive: bool, gaps: [{ task_id, severity: 'P0'|'P1'|'P2'|'P3', problem }], missingTasks: [id...] }`.

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
