---
name: qa-loop
description: Use quando o usuário quer revisar código num loop com critério de parada ASSINTÓTICO EM SEVERIDADE — fecha quando uma rodada completa não traz nada acima do piso de severidade, nunca porque gastou rodadas, tempo ou tokens (Artigo 14 da constituição). Zero achados não é o alvo, porque parte do que se chama de erro é preciosismo que não afeta consistência nem funcionamento. Ancora no plano de implementação — cada finding vira implementação, plan-drift ou plano-falho, e só implementação é consertada, com regression gate por conserto. Duas fases, o julgamento por severidade e um gate absoluto que exige lint, type, unit e integração verdes no repo inteiro. O que fica abaixo do piso sai listado; o que fica acima só escapa com ratificação do dono. Substitui as skills antigas qa, rev6 e iterate. Trigger em "/qa-loop", "qa", "audita o plano", "tá 100%", "revisa isso", "loopa o review", "revisa até valer a pena".
---

# /qa-loop — Loop de review→conserto disciplinado

## Antes de tudo — a régua e os princípios (o par obrigatório)

Antes de revisar uma linha de código, rode o par, nesta ordem — é ele que substitui a antiga instrução em
prosa "leia a constituição e o quality-goals do projeto":

1. **A régua do projeto** — a skill `doc-load` (invoque pela Skill tool; fora dela:
   `python3 "$(bash "<plugin project-skills>/lib/resolve-plugin.sh" project-skills lib/doc_load.py)" --project-root "$PWD"`).
   Ela diz o que vale como régua HOJE — a lei com `ready`/`approved`, o acordo só com
   `approved`, o minerado como mapa — e o que está ausente, sem fingir.
2. **Os princípios genéricos** — a skill `principles` em modo `review`, quando instalada
   na máquina. Ausente: siga sem ela, dizendo isso no relato.

Em conflito, **a régua do projeto ganha** — princípio genérico não revoga a lei da casa.

Revisa código num loop com parada **assintótica em SEVERIDADE**: fecha quando uma rodada completa
não traz nada **acima do piso** — nunca porque gastou rodadas, tempo ou dinheiro (**Artigo 14**).
Ancora no **plano de implementação**: o código não pode "melhorar" e afastar do que foi combinado.

Substitui três skills: o esqueleto de loop multi-agente do antigo `/qa`, as lentes paralelas do
antigo `/rev6`, e a disciplina de regression-gate + baseline do antigo `/iterate` — tudo num fluxo só.

## A ideia central (por que existe) — Artigo 14 da constituição

**O critério de fecho é ASSINTÓTICO, e a assíntota é de SEVERIDADE:**

> **uma rodada COMPLETA que não produz nenhum achado acima do piso de severidade,
> confirmada por um re-sweep independente.**

**Por que assintótico, e não "zero erros".** Zero achados é otimista e, pior, falso: boa parte
do que um revisor chama de erro é **preciosismo que não afeta consistência nem funcionamento**
— naming, gosto, micro-refator. Num problema de espaço de input infinito (scrubber/parser/
ranker/regex/prompt) um finder adversarial sempre produz mais um desses. Exigir zero
transformaria gosto de revisor em bloqueio e obrigaria quem quer fechar a **rebaixar** achado —
corrompendo o único instrumento que separa defeito de opinião. A assíntota é a admissão honesta
de que a cauda existe e **não importa**; o que importa é o que está **acima do piso**.

**O que a assíntota NÃO é** — as duas leituras tortas, as duas já cometidas aqui:

<!-- artigo14-ok: nomeia as leituras erradas para poder proibi-las -->
- **Não é taxa de descoberta caindo.** "Está rendendo menos", "as últimas rodadas acharam
  pouco" não são critério. Uma rodada que acha UM P0 é rodada que não fecha, mesmo que as três
  anteriores tenham achado vinte P3 cada.
- **Não é gasto.** Rodada, token, tempo e dinheiro **nunca** fecham revisão. Não há teto de
  rodadas como critério, e teto não se declara dentro do projeto.

**E nunca é licença para rebaixar.** Mover um achado de P1 para P2 a fim de alcançar o fecho é
fraudar o critério — a falta mais grave do artigo, porque não deixa rastro: o relatório fica
verde e o defeito fica de pé.

O que fica **abaixo do piso** sai **listado** no relatório, com severidade e local: some do
bloqueio, nunca da vista. O que fica **acima** e não vai ser consertado só escapa por uma porta:
**o dono ratifica** um limite aceito, com motivo escrito.

O grosso da disciplina segue sendo **não gerar regressão ao consertar** — é ali que mora o maior
retorno. (Esse é o eixo do julgamento. O outro eixo — os checks objetivos lint/type/unit/
integração — é **absoluto** e vive na Fase Gate; ver "As duas fases".)

<!-- artigo14-ok: cita o texto revogado para registrar de onde a emenda veio -->
> Emendado em 2026-08-23. O desenho anterior misturava as duas leituras erradas ao mesmo tempo:
> definia o fecho como *"para quando não vale mais a pena"* (cansaço) e ancorava a parada em
> *"retornos decrescentes"* (taxa de descoberta). E havia teto declarado dentro de projeto — um
> `max_rounds: 6` viajava em dois `qa-loop.config.md` sem ninguém ter decidido, um deles
> chamando-o de "default" quando o default era 12. Medido numa revisão real com teto 4: a quarta
> rodada ainda abriu 7 achados, **1 deles P1** — acima do piso, portanto rodada que não fecha; o
> teto teria encerrado assim mesmo. Cobrador: `scripts/test_revisao_fecha_por_problema.py`.

## A arquitetura em uma frase — motor = Workflow, casca = skill

O **motor** (revisar → planejar → consertar → checar, em N rodadas) roda como **um único Workflow
determinístico** (a tool `Workflow`). Cada papel é um agente no tier certo — **todos Opus 5**, o que muda
por etapa é o `effort`: **Opus Revisor** (independente) acha, **Opus Planejador** (adversarial, árbitro
único) adjudica, **Opus Executor** conserta um fix por vez. O gate de regressão, o gate de severidade, o churn detector e a parada são
**lógica do script (código JS)** — não "o Opus lembrar de aplicar a regra a cada rodada".

A **casca** (esta skill, no loop principal Opus) faz só o que o Workflow **não consegue**: os 2 toques
humanos. O Workflow roda em background e **não pergunta nada no meio**, então:
1. **Antes** de disparar o Workflow — classifica o domínio (pergunta 1× se ambíguo) e lê o journal.
2. **Depois** do Workflow retornar — gera o relatório HTML + journal e pede a nota 0-10.

> Invocar `/qa-loop` **é** o opt-in pra orquestração multi-agente — a skill instrui a chamar `Workflow`.
> Por que Workflow e não sub-agente solto: sub-agente solto seria o Opus disparando Task ad-hoc (a regra
> global do usuário condena, e o guard `PreToolUse(Agent)` acorda a cada fix). Por que não Agent Team: o fluxo é um
> pipeline fechado, não conversa aberta entre teammates. Workflow dá determinismo + telemetria + resumível.

## As duas fases — máquina assintótica + gate absoluto

A skill roda **duas fases com lógicas próprias que convivem** — não uma máquina só. Cada finding pertence
a UMA delas, e cada fase tem seu próprio critério de "pronto". Confundir as duas é o erro que esta seção
existe pra matar: tratar um erro de type como "finding de severidade rebaixável", ou tratar um cheiro de
código como "tem que zerar".

**Fase de Julgamento** — revisão de código, aderência ao plano (os 3 buckets), findings de
**severidade variável** (P0-P3), limites aceitos **ratificados pelo dono**, e fecho **só quando não
sobrou problema procedente em aberto** (Artigo 14 — jamais por esforço gasto). **E o fecho dela exige
os TRÊS PILARES** (contrato em `references/dimensoes-de-revisao.md`): QUALIDADE fecha pela assíntota de
severidade; COBERTURA e COERÊNCIA fecham por **100%**, medidos por **auditores externos isolados** que
rodam no candidato a fecho — a conta do 100% é do script do motor, nunca do auditor, e tudo se mede
contra as três âncoras (PEDIDO · PLANO · CONSTITUIÇÃO). **e2e/Playwright vive
aqui**: cobertura parcial e honesta, vira *actionable* no relatório — **não bloqueia**. É todo o corpo
desta skill (os passos abaixo descrevem ela).

**Fase Gate** — lint, type-check, teste unitário, teste de integração e afins. **Absolutista: 100% verde
no repo inteiro ou não passou.** Binário. Sem severidade, sem julgamento, sem accepted-limit, sem "não vale
a pena". É portão. Os checks **nunca foram** da fase assintótica — são a Fase Gate. Detalhe operacional no
Passo 8.0 (gate de saída) + na seção "Detecção de rede".

> As fases **não são sequenciais no tempo**. O gate é **invariante de saída**, protegido continuamente pelo
> regression-net por-fix do motor (a suíte roda a cada conserto). A skill só declara **sucesso da sessão**
> quando AS DUAS fecham: a Fase Assintótica chega a uma **rodada limpa** (seu evento interno — zero achado
> acima do piso, confirmado pelo re-sweep) E a Fase Gate fica 100% verde. "Rodada limpa" é o desfecho do motor; "sucesso da sessão" é das
> duas juntas. Gate vermelho **nunca** é sucesso — a casca seta `stopReason='gate-red'`.

## Input

```
/qa-loop <alvo> [--plan=<path>] [--floor=P1] [--max-rounds=6] [--domain=auto] [--headless]
```

- `<alvo>` — caminho/pasta, diff ref (`HEAD~3..HEAD`, `staged`), PR (`#123`), ou descrição natural do que foi implementado.
- `--plan` — o plano de implementação a auditar contra (`.claude/plans/*.md`, `docs/specs/*.md`). Se ausente, tenta achar o plano mais recente; se não houver, roda em modo "review sem plano" (sem o bucket plan-drift/plan-flaw, só implementação — e avisa que está sem âncora).
- Knobs (todos com default, abaixo).

## Modelo & effort por etapa (R8) — contrato em `references/r8-tiers.md`

**É TUDO Opus 5** (contrato R8 desde 2026-07-26): os seis knobs rodam `model: 'opus'` e o que dispara no
tier certo pro PESO da decisão é o **`effort`**, e **o valor não mora aqui**: ele vem de
`references/r8-tiers.json`, que a casca carrega e passa no `args` do Workflow. A semântica dos knobs é o **contrato R8 compartilhado** com o `/sprint`, vendorado em
**`references/r8-tiers.md`** (fonte: `_shared/r8-tiers.md` — não editar a cópia à mão;
`scripts/sync-shared.sh --check` pega drift). Trocar o tier de uma etapa lá vale pros dois motores. A tabela
completa (Etapa · Modelo · Effort · Knob + o que cada knob significa + a regra de tier por rodada) está no
arquivo. Abaixo, só **onde cada knob entra NESTE motor** (revisa→planeja→conserta):

| Knob | Onde no motor |
|---|---|
| `decompose_model` | REVIEW + PLAN da **rodada 1** (sweep completo + plano pesado). |
| `coordinate_model` | REVIEW + PLAN das **rodadas 2+** (caça-regressão + delta). |
| `executor_model` | EXEC — aplica 1 fix do bucket 1 por vez. |
| `mechanical_model` | Fila objetiva da **Fase Gate** (Passo 8.0) — lint/type/unit/integração, sem julgamento. |
| `diagnose_model` | Escalada de **churn** — mesma função regrediu ≥ `churn_threshold` → diagnóstico de raiz, não mais remendo. |
| `finalize_model` | **Confirm-pass** — antes de declarar rodada limpa, um re-sweep completo dedicado roda aqui; não confia no resultado mais barato (`coordinate_model`) da rodada que pareceu limpa. |

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

## Parâmetros / knobs

Os **6 model-knobs** (`decompose_model`, `coordinate_model`, `executor_model`, `mechanical_model`,
`diagnose_model`, `finalize_model`) com seus defaults de modelo/effort vivem no contrato R8
(`references/r8-tiers.md`) — não repito os defaults aqui pra não reintroduzir o drift. Os knobs de
**comportamento** do loop:

| Knob | Default | O que faz |
|---|---|---|
| `severity_floor` | `P1` | Conserta P0/P1; P2/P3 viram candidato a accepted-limit. **Load-bearing**: define "finding de severidade real". |
| `max_rounds` | `null` (SEM TETO) | **NÃO é critério de fecho — Artigo 14 proíbe fechar por gasto.** Quem fecha é a assíntota de severidade. Sem valor, o laço roda até a rodada limpa, e é assim que deve ser. Existe só como **freio de emergência de quem invoca** (laço preso num defeito de ambiente), e aí bater nele é **FALHA**, com a lista do que ficou acima do piso. **NUNCA se declara no `qa-loop.config.md` do projeto** — número escrito antes de saber o que a obra tem envelhece calado e vira lei sem dono (medido: um `max_rounds: 6` viajava em dois configs sem ninguém ter decidido). **Clampado pela camada de rede** no motor: Camada 4 → 2, Camada 5 → 1 — este clamp é sobre **risco de estrago** (sem suíte, cada fix é aposta cega e mais voltas multiplicam a aposta), jamais sobre custo. |
| `domain` | `auto` | `auto` infere; `convergent` (tem comando pass/fail objetivo) ou `asymptotic`. |
| `regression_gate` | `on` | Sempre on — é o coração. |
| `triage_threshold` | `2` | Com ≥2 findings (ou qualquer alargamento de regra), o PLAN vira tabela formal; com 1, decisão inline. |
| `churn_threshold` | `2` | ≥N regressões auto-infligidas na mesma função → escala pro `diagnose_model` (para de remendar). |
| `headless` | `off` | Modo não-interativo (pro `/sprint`) — nunca pergunta, alertas de plano não viram fix. |

Precedência (R3): **flag de invocação > `.claude/qa-loop.config.md` do projeto > default acima.**

## Fluxo

```dot
digraph qa_loop {
    rankdir=TB;
    "Start" [shape=doublecircle];
    "CASCA: 0. domínio + lê journal" [shape=box];
    "CASCA: 1. contrato + baseline + rede" [shape=box];
    "WORKFLOW: motor (Fase Assintótica)" [shape=box, style=filled];
    "CASCA: 8.0 FASE GATE (lint/type/unit/integração — 100% repo)" [shape=diamond];
    "CASCA: 8. relatório HTML + journal + nota" [shape=doublecircle];

    "Start" -> "CASCA: 0. domínio + lê journal" -> "CASCA: 1. contrato + baseline + rede";
    "CASCA: 1. contrato + baseline + rede" -> "WORKFLOW: motor (Fase Assintótica)";
    "WORKFLOW: motor (Fase Assintótica)" -> "CASCA: 8.0 FASE GATE (lint/type/unit/integração — 100% repo)";
    "CASCA: 8.0 FASE GATE (lint/type/unit/integração — 100% repo)" -> "CASCA: 8.0 FASE GATE (lint/type/unit/integração — 100% repo)" [label="vermelho → conserta (fila objetiva, mechanical_model) → re-roda"];
    "CASCA: 8.0 FASE GATE (lint/type/unit/integração — 100% repo)" -> "CASCA: 8. relatório HTML + journal + nota" [label="travou → gate-red (BLOQUEANTE)"];
    "CASCA: 8.0 FASE GATE (lint/type/unit/integração — 100% repo)" -> "CASCA: 8. relatório HTML + journal + nota" [label="verde / gate vazio declarado"];
}
```

O loop interno (dentro do Workflow), por rodada:

```dot
digraph motor {
    rankdir=TB;
    "REVIEW (decompose/coordinate_model)" [shape=box];
    "Gate severidade (JS)" [shape=diamond];
    "CONFIRM (finalize_model, medium)" [shape=box, style=filled];
    "PLAN (decompose/coordinate_model)" [shape=box];
    "EXEC (executor_model)" [shape=box];
    "Gate regressão (JS)" [shape=diamond];
    "Reverte (refaz no tier da rodada)" [shape=box];
    "DIAGNOSE (diagnose_model, medium)" [shape=box, style=filled];
    "PARA — rodada limpa" [shape=doublecircle];
    "Próxima rodada" [shape=box];

    "REVIEW (decompose/coordinate_model)" -> "Gate severidade (JS)";
    "Gate severidade (JS)" -> "CONFIRM (finalize_model, medium)" [label="parece limpa (rodada completa, 0 severo)"];
    "CONFIRM (finalize_model, medium)" -> "PARA — rodada limpa" [label="confirma limpa"];
    "CONFIRM (finalize_model, medium)" -> "PLAN (decompose/coordinate_model)" [label="achou algo que a rodada barata perdeu"];
    "Gate severidade (JS)" -> "PLAN (decompose/coordinate_model)" [label="há P0/P1"];
    "PLAN (decompose/coordinate_model)" -> "EXEC (executor_model)";
    "EXEC (executor_model)" -> "Gate regressão (JS)";
    "Gate regressão (JS)" -> "Reverte (refaz no tier da rodada)" [label="suíte vermelha, churn<teto"];
    "Gate regressão (JS)" -> "DIAGNOSE (diagnose_model, medium)" [label="churn>=teto"];
    "Reverte (refaz no tier da rodada)" -> "EXEC (executor_model)";
    "Gate regressão (JS)" -> "Próxima rodada" [label="verde / fim do bucket"];
    "Próxima rodada" -> "REVIEW (decompose/coordinate_model)";
}
```

Tier por rodada: **rodada 1** = `decompose_model` (planejamento inicial); **rodadas 2+** =
`coordinate_model` (coordenação rotineira). O nó CONFIRM é dedicado — sempre `finalize_model`, nunca o
tier da rodada que pareceu limpa. DIAGNOSE também é dedicado — sempre `diagnose_model`, disparado só
quando o churn escala (mesma função regredindo repetidamente). O que separa os dois dedicados da rodada
é o **contexto limpo**: cada um reabre o problema do zero, independentemente do tier que estiver valendo.

---

## CASCA — Passo 0.0 · Trava de alvo em movimento (ANTES de ler uma linha de código)

Revisar código que **outro motor da mesma sessão ainda está escrevendo** produz acusação falsa: o
Revisor lê o arquivo no meio de um conserto, aponta o defeito que o outro já corrigiu, e o Executor
"conserta" por cima do trabalho vivo. Por isso a revisão **reserva** os arquivos que vai ler, pelo mesmo
mecanismo que o `/sprint` usa entre motores — e se a lista **cruza** com a de um motor vivo, ela **recusa**.

**Rode isto antes do Passo 0**, com `ARQUIVOS_DO_REVIEW` = a lista de arquivos que esta revisão vai ler,
**um por linha** (do alvo: `git diff --name-only <alvo>`), e `CLAUDE_SESSION_ID` = o id desta sessão:

```bash
RESERVA="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/qa-loop/resolve-plugin.sh" project-skills hooks/reserva-de-arquivos.sh)"
[ -n "$RESERVA" ] && sh "$RESERVA" reservar "${CLAUDE_SESSION_ID}" qa-loop $ARQUIVOS_DO_REVIEW
```

- **Saiu `"permissionDecision":"deny"`** → **PARE a skill aqui**. Não leia arquivo, não dispare o
  Workflow, não abra relatório. Mostre ao usuário o `permissionDecisionReason` **inteiro** — ele nomeia o
  motor vivo e os arquivos que cruzaram, e é essa a explicação de por que a revisão recusou. Ofereça as
  duas saídas que o próprio motivo dá: esperar o outro motor terminar, ou reduzir `<alvo>` a arquivos que
  não encostem na lista dele.
- **Saída muda** → reservado, segue pro Passo 0.
- **Saída vazia do resolvedor** (`/sprint` não instalado nesta máquina) → não há motor com quem colidir; segue. Fail-open, como
  todo gate deste repo.

Ao terminar (Passo 8, inclusive em `gate-red` ou abandono), **libere** — reserva que não é liberada
recusa a próxima revisão até expirar:

```bash
RESERVA="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/qa-loop/resolve-plugin.sh" project-skills hooks/reserva-de-arquivos.sh)"
[ -n "$RESERVA" ] && sh "$RESERVA" liberar "${CLAUDE_SESSION_ID}" qa-loop
```

## CASCA — Passo 0 · Classificar domínio + ler journal

**Toda sessão roda AS DUAS fases** (ver "As duas fases"). A pergunta de domínio NÃO roteia a skill pra um
lado só — ela faz duas coisas: define o **conteúdo da Fase Gate** E calibra o teto da Fase Assintótica.

**Pergunta binária e barata:** "existe UM comando objetivo com pass/fail (testes/build/lint/type/um curl com `jq -e`)?"

- **Convergente** — sim, há checks objetivos. Eles **compõem a Fase Gate** (Passo 8.0): lint/type/unit/
  integração rodam ao fim como portão absoluto (100% verde no repo inteiro, ou `stopReason='gate-red'`).
  Quanto mais forte a suíte, mais forte o gate; o alvo objetivo também dá teto alto pra Fase Assintótica.
- **Assintótico** (default pra heurística — scrubber/parser/ranker/regex/prompt/classificador/"achar todos
  os bugs") — não há um comando único que dê pass/fail no review; governa o gate de **severidade** da
  Fase de Julgamento. **Não muda o critério de fecho:** ele segue sendo "não sobrou problema procedente
  em aberto" (Artigo 14) — domínio infinito autoriza o dono a ratificar limite, nunca o laço a desistir.
  **É o caso primário desta skill.** **O domínio NÃO decide se há
  Fase Gate:** se o projeto tem checks objetivos (até um scrubber tem lint+unit), eles compõem a Fase Gate
  absoluta igual ao caso convergente — o domínio só muda o teto/severidade da fase assintótica. Só SEM nenhum
  check objetivo a **Fase Gate fica vazia, declarada honesto** — nunca finge gate.

Se ambíguo e **não headless**, pergunta 1× ao usuário. Se headless, assume `asymptotic` (mais conservador).

**Por onde a pergunta chega quem escolhe é o usuário** — a régua dos dois canais (página de
decisão em múltipla escolha, ou a ferramenta nativa uma por vez) está em
**`regua-de-pergunta.md`**, ao lado deste arquivo (fonte: `_shared/regua-de-pergunta.md`, cópia
derivada; não editar à mão).

**Lê o journal (R7)** antes de disparar o motor: do `.claude/qa-loop.config.md` do projeto puxa os
`accepted_limits` ratificados + as `invariants` vivas; de `~/.claude/qa-loop/journal/learnings.md` puxa
os aprendizados cross-projeto que afinam os prompts do Revisor/Planejador. Tudo isso vira **args do Workflow**.

> ⚠️ Erro que mata o loop: tratar assintótico como convergente → loop infinito. A pergunta tem que ser real, não um carimbo.

## CASCA — Passo 1 · Declarar contrato + baseline + rede de regressão

Fixa e **anuncia no header**: teto de rodadas (safety-cap), `severity_floor`, o plano-âncora, e a **camada de
rede de regressão** disponível (ver Guard-rails → Detecção de rede). Snapshot do nº de erros de
lint/typecheck ANTES da rodada 1 (`baseline_errors`) — é o que a **rede de regressão DURANTE o loop** usa pra
pegar regressão estrutural (não piorar o baseline mid-loop). ⚠️ Isso é a rede in-loop, **NÃO o gate**: a
**Fase Gate de saída** (Passo 8.0) exige lint/type/unit/integração **absolutamente 0** no fim, pré-existentes
incluídos — o baseline tolera no meio, o gate não tolera no fim. Declara honestamente o blast-radius que a rede
NÃO cobre. Esses valores entram nos args do Workflow.

---

## O sinal da missão (obrigatório, ANTES de disparar o Workflow)

Enquanto o motor roda, o loop principal fica em idle e a tela não diz se há trabalho de pé. O
sinal é o que faz a barra de status dizer — `lib/andamento.py:linha_motor` lê o nome escrito
dentro dele e desenha a linha; sem sinal, não há linha nenhuma.

```bash
ADIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/andamento"
mkdir -p "$ADIR"
printf 'qa-loop\n' > "$ADIR/ativo-$CLAUDE_CODE_SESSION_ID"     # ao disparar o Workflow
```

**E o motor ANDA na barra, rodada a rodada.** A barra parada em `Onda 2` por quinze minutos
não diz se avançou ou travou — então cada rodada do motor registra onde está, e o comando é
um só (falhar nele não derruba nada):

```bash
AND="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/andamento.py)"
python3 "$AND" onda "$CLAUDE_CODE_SESSION_ID" <rodada> --etapa "revisando" || true
```

As etapas deste motor, na ordem: `revisando` · `planejando` · `consertando` · `confirmando` ·
`gate`. O `--bloco N` existe para quem trabalha em blocos (o motor do `/sprint`); aqui a
rodada basta.

Ao entregar o relatório (Passo 8), **encerre** — e é `encerra`, não `rm`, porque o estado da
missão é mais que o sinal (onda, placar, doc e trabalho em curso ficavam para trás e
reapareciam na barra de quem reusasse o id):

```bash
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/andamento.py)" encerra "$CLAUDE_CODE_SESSION_ID" qa-loop
```

⚠️ **Encerre também quando NÃO houve relatório** — gate vermelho, motor que não respondeu,
abandono, alvo em movimento no Passo 0.0. Sinal esquecido deixa a barra mentindo missão de pé
pelo resto da sessão, e a rede embaixo (a varredura da barra, `andamento.py:expira_sinais`)
só age depois de **12 horas**. Medido em 2026-08-09: cinco sinais órfãos vivos ao mesmo
tempo, o mais velho de 75 horas.

A casa é a **neutra** (`andamento/`), a mesma que os outros motores acendem: é o único jeito
de a barra falar de qualquer motor em vez de um só.

---

## WORKFLOW — o motor (loop de rodadas)

### O motor é COPIADO daqui, não reescrito a partir daqui

🔴 **Esta seção já se chamou "esqueleto de referência — o princípio, não código imutável",
e essa frase custou o mesmo defeito duas vezes.** O motor do `/sprint` virou arquivo do
plugin em 2026-08-09 justamente por isso; o deste ficou sendo montado pela casca a cada
disparo, e a assimetria cobrou em 2026-08-10: o passo que **apaga o sinal da barra** virou
código lá (`encerra:barra`) e ficou em **prosa** aqui — *"ao entregar o relatório,
encerre"*. Prosa não pega. O sinal do qa-loop ficou aceso **9h26 depois do fim**, a barra
anunciando missão de pé, e quem viu foi o dono, não um cobrador.

**O executável é `references/motor.js`**, resolvido por nome e passado direto ao `Workflow`:

```bash
MOTOR="$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills skills/qa-loop/references/motor.js)"
# Workflow({ scriptPath: MOTOR, args: {...} })
```

Nunca copie o `motor.js` para rascunho, nunca o redigite, nunca "melhore" na hora. A casca
só monta os `args` — e passa **`resolvePlugin`** (o caminho absoluto do resolvedor,
descoberto por `resolve-plugin.sh`) e **`sessionId`**, porque é dele que saem o registro da
barra e o encerramento. Sem `sessionId` os dois papéis simplesmente não rodam, e o sinal
volta a depender de alguém lembrar.

### O motor não sabe em que projeto está — a casca é quem conta (obrigatório)

Três `args` descrevem o projeto REVISADO, e sem eles o motor assume **este** repositório.
A casca os lê do `CLAUDE.md` do projeto da missão e os passa:

| arg | o que é | sem ele |
|---|---|---|
| `stack` | uma linha: linguagem, framework, se tem build/CI | o revisor de um app Next.js é informado de que está num marketplace de Markdown/Bash/Python |
| `regrasDaCasa` | as regras do projeto com seus cobradores | o revisor julga contra as sete regras deste repo (bump de `plugin.json`, `sync-shared`…), que lá não existem |
| `suiteCmd` | **o comando de teste declarado pelo projeto, literal** | o executor cai num `find` por `test_*.py` que, num projeto TypeScript, acha ZERO teste do módulo alterado — e num monorepo ainda varre a suíte de módulos vizinhos |
| `pedidos` | **a âncora PEDIDO**: os pedidos vivos do usuário, verbatim, lidos do caderno do `intent-guard` | os auditores medem só contra plano e régua, e a intenção dita fica sem cobrador |
| `pedidosAusentes` | o motivo declarado quando não há pedidos (plugin ausente, caderno vazio) | a ausência viraria aprovação por omissão — proibido pelo contrato dos pilares |
| `lentesDispensadas` | lentes de COBERTURA que o **dono ratificou** dispensar no `qa-loop.config.md` (ex.: `e2e` num projeto sem interface) | projeto sem infra E2E fecharia sempre em "não medida", sem porta de decisão |

**Como a casca lê a âncora PEDIDO (fail-open, obrigatório):** resolva o caderno pelo nome
e leia o estado; qualquer falha vira ausência **declarada**, nunca silêncio:

```bash
RAIZ="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"   # a raiz do projeto REVISADO
LEDGER="$(bash "${CLAUDE_PLUGIN_ROOT}/skills/qa-loop/resolve-plugin.sh" intent-guard lib/ledger.py 2>/dev/null)" || LEDGER=""  # artigo8-ok: o harness injeta CLAUDE_PLUGIN_ROOT quando a skill roda
if [ -n "$LEDGER" ] && [ -f "$LEDGER" ]; then
  PEDIDOS_JSON="$(python3 "$LEDGER" state --cwd "$RAIZ" --session "$CLAUDE_CODE_SESSION_ID" 2>/dev/null)" || PEDIDOS_JSON=""  # artigo8-ok: o harness injeta CLAUDE_CODE_SESSION_ID quando a skill roda
fi
# PEDIDOS_JSON vazio → args.pedidos = [] e args.pedidosAusentes = "intent-guard não instalado" (ou "caderno vazio")
# com conteúdo → args.pedidos = lista {id, resumo, text} dos vivos (live + standing), verbatim
```

**`suiteCmd` é o que sustenta o gate de regressão por conserto**, que esta skill chama de
maior retorno. Suíte que não coleta nada devolve "nenhum teste falhou", `suiteRegressed`
nasce `false`, e o gate fica cego **parecendo verde**. Medido em 2026-08-23: 5 sessões
desde que o motor virou arquivo, todas em projetos JS/TS, **44 consertos e 0 regressões
detectadas**. O motor do `/sprint` recebe `suiteCmd` desde 2026-08-13 pelo mesmo motivo —
este ficou para trás, que é a mesma assimetria narrada no topo do `motor.js`, noutro eixo.

Quem cobra que o arquivo não regrida é **`lib/test_qa_loop_motor.py`**: o encerramento tem
que vir antes do `return` (para alcançar teto e churn, não só a rodada limpa), cada etapa
tem que registrar onde está, toda chamada de agente tem que levar `label`, e **stack,
regras e comando de suíte têm que entrar por `args`** em vez de cravados no prompt.

O bloco abaixo é a **fonte documentada** do laço — quem muda comportamento edita os DOIS.
Os três schemas (`FINDINGS`, `PLAN`, `EXEC_RESULT`) são o que torna os gates determinísticos:
o script lê campos estruturados, não texto solto.

```javascript
export const meta = {
  name: 'qa-loop-engine',
  description: 'Motor de QA: tier por etapa (R8) — decompose/coordinate/executor/mechanical/diagnose/finalize',
  phases: [{ title: 'Review' }, { title: 'Plan' }, { title: 'Exec' }, { title: 'Confirm' },
           { title: 'Auditoria' }],
}

// args (vindos da casca): { target, planPath, severityFloor, maxRounds, domain,
//   safetyLayer, churnThreshold, acceptedLimits[], invariants[], learnings,
//   stack, regrasDaCasa[], suiteCmd,     // <- os três que descrevem o projeto REVISADO;
//   pedidos[], pedidosAusentes,          // <- a âncora PEDIDO (ledger do intent-guard; fail-open declarado)
//   lentesDispensadas[] }                // <- SÓ o que o dono ratificou no qa-loop.config.md
//   sem os três do projeto o motor assume ESTE repositório (ver a tabela acima)
const sevRank = s => ({P0:3, P1:2, P2:1, P3:0}[s] ?? 0)
const floor = sevRank(args.severityFloor || 'P1')
const acceptedLimits = args.acceptedLimits || []   // RATIFICADO pelo dono (args) — é ESTA que os filtros leem
// PILARES 2 e 3 — o estado que a auditoria externa preenche. A conta é do script.
const lentesDispensadas = args.lentesDispensadas || []   // RATIFICADO pelo dono, igual aos limites
let auditCob = null, auditCoe = null
let cobStatus = 'nao-rodou', coeStatus = 'nao-rodou'
let furosCobertura = [], violadosCoerencia = [], auditoriaNaoMedida = false
const proposedLimits = []                          // PROPOSTO pelo planejador — sai no return, não silencia achado
let invariants = args.invariants || []
const churn = {}                 // { 'arquivo:função': nº de regressões }
const causaCache = {}            // causa referendada por chave — a mesma raiz não paga duas investigações
const causaDisputada = []        // o desfecho de cada escalada: causa referendada, ou a disputa com as duas versões
// chave do churn = arquivo:função. Só o nome da função colidiria entre arquivos
// (dois `validate()` em módulos diferentes) e escalaria o diagnóstico caro cedo demais.
const churnKey = fix => `${fix.file || '?'}:${fix.fn || '?'}`
const rounds = []
let cleanRound = false, churnEscalated = false, teatroDeDuvida = false, r = 0, rodadasSemConserto = 0
let regressaoTotal = false, rodadasSoRegressao = 0
let touchedLastRound = [], openFindings = []   // delta pro REVIEW das rodadas 2+

// ── ARTIGO 14 · A ASSÍNTOTA É DE SEVERIDADE, NUNCA DE GASTO ──────────────────
// `cleanRound` é o ÚNICO desfecho que é sucesso, e ele é ASSINTÓTICO: rodada completa
// sem nenhum achado ACIMA DO PISO (`severityFloor`), com o confirm-pass concordando.
// Os outros desfechos são FALHA — o `return` os devolve com `sucesso: false`.
//
// SEM TETO POR DEFAULT (era 12; o dono cortou em 2026-08-23: "o que NÃO pode ter é o
// teto por gasto de rodadas ou tokens"). `maxRounds` só existe quando quem invoca passa
// um, como freio de emergência para laço preso em defeito de ambiente. O clamp por
// camada de rede abaixo NÃO é gasto: sem suíte, cada fix é aposta cega e mais voltas
// multiplicam o ESTRAGO — é risco, e por isso sobrevive ao artigo.
const LAYER_CAP = { 4: 2, 5: 1 }
const churnThreshold = args.churnThreshold || 2
const capDaCamada = LAYER_CAP[args.safetyLayer]
const maxRounds = Math.min(args.maxRounds || Infinity, capDaCamada ?? Infinity)
// Quem foi que limitou? O veredito do fecho não pode chamar o clamp de "freio":
// freio é gasto, clamp é risco de estrago, e trocar um pelo outro apaga a causa.
const limitePorCamada = capDaCamada !== undefined && capDaCamada <= (args.maxRounds || Infinity)

// Tier por rodada (R8): rodada 1 = decompose_model (sweep completo); rodadas 2+ =
// coordinate_model (caça-regressão + delta). Os valores chegam em args.tiers, servidos
// de references/r8-tiers.json pela casca — nunca literais aqui.
const T = args.tiers
const tierFor = round => ({ model: args.model,
  effort: round === 1 ? T.decompose.effort : T.coordinate.effort })

while (!cleanRound && r < maxRounds && !churnEscalated && !teatroDeDuvida) {
  r++; phase(`Rodada ${r}`)
  const tier = tierFor(r)

  // REVIEW — 1 Opus Revisor INDEPENDENTE, no tier da rodada. Checklist das dimensões
  // de references/dimensoes-de-revisao.md (a lista viva mora lá; 1 agente, nunca um por
  // dimensão) — a última é cobertura por finalidade: o que o plano pede tem teste
  // que MORDE? É a única que enxerga o teste AUSENTE; as outras julgam o que existe.
  // Rodada 1 = sweep completo do material inteiro (decompose_model);
  // 2+ = DELTA (coordinate_model): só os arquivos tocados pelos fixes da rodada anterior
  // + findings abertos — caça-regressão, não releitura do material inteiro.
  const review = await agent(reviewPrompt({ round: r, acceptedLimits, invariants,
      scope: r === 1 ? 'full' : { touchedFiles: touchedLastRound, openFindings } }),
    { model: tier.model, effort: tier.effort, phase: 'Review', schema: FINDINGS, agentType: 'voltagent-qa-sec:code-reviewer' })

  // Agente que não respondeu sai do laço deixando a `nota` — é ela que vira o desfecho
  // `agente-mudo` lá embaixo. No motor o mesmo guard existe para o confirm-pass e para
  // o planejador; aqui um basta para mostrar de onde a nota vem.
  if (!review) {
    rounds.push({ r, review: null, nota: 'revisor não respondeu' })
    break
  }

  // GATE de severidade (JS) — sobre rodada COMPLETA (todo ângulo retornou).
  const severe = review.findings.filter(f =>
    sevRank(f.severity) >= floor && !isAccepted(f, acceptedLimits))

  if (review.complete && severe.length === 0) {
    // CONFIRM — finalize_model (Opus medium, R8 "revisão final e integração"). Re-sweep
    // completo DEDICADO antes de declarar limpa — não confia no resultado mais barato
    // (coordinate_model) da rodada que pareceu limpa.
    const confirm = await agent(reviewPrompt({ round: r, acceptedLimits, invariants, confirming: true }),
      { model: args.model, effort: T.finalize.effort, phase: 'Confirm', schema: FINDINGS, agentType: 'voltagent-qa-sec:security-auditor' })   // finalize_model
    const confirmSevere = confirm.findings.filter(f =>
      sevRank(f.severity) >= floor && !isAccepted(f, acceptedLimits))
    if (confirm.complete && confirmSevere.length === 0) {
      rounds.push({ r, review, confirm, corrections: [], regressions: 0, alerts: [] })
      cleanRound = true; break
    }
    // o confirm-pass achou algo que a rodada barata perdeu — processa, não ignora.
    review.findings = review.findings.concat(confirm.findings)
  }

  // PLAN — Opus Planejador ADVERSARIAL = árbitro único (R2), no MESMO tier da rodada.
  // Adjudica "procede?" contra a rubrica, roteia nos 3 buckets, triagem por severidade
  // E risco-de-conflito, sequencia. Rodada 1 (decompose_model) pesada; 2+ (coordinate_model) = só o DELTA.
  const plan = await agent(planPrompt({ review, round: r, invariants, acceptedLimits }),
    { model: tier.model, effort: tier.effort, phase: 'Plan', schema: PLAN, agentType: 'voltagent-qa-sec:error-detective' })

  // EXEC — executor_model (Opus medium, R8 all-Opus), SÓ bucket 1, EM SÉRIE (o gate roda a
  // suíte entre fixes; pares de risco exigem ordem).
  const corrections = []; let regressions = 0
  for (const fix of plan.bucket1) {
    const res = await agent(execPrompt({ fix, invariants, safetyLayer: args.safetyLayer }),
      { model: args.model, effort: T.executor.effort, phase: 'Exec', schema: EXEC_RESULT, agentType: 'voltagent-core-dev:backend-developer' })   // executor_model
    // GATE de regressão (JS) — quem decide keep/revert é o SCRIPT, nunca o executor.
    if (res.suiteRegressed) {
      const k = churnKey(fix)
      regressions++; churn[k] = (churn[k] || 0) + 1
      // por reincidência (churn) OU por GRAVIDADE (decisão do dono, 2026-08-09): fix P0
      // que regrediu investiga a causa na PRIMEIRA queda — defeito grave não espera
      // voltar para merecer investigação. O cache segura o custo: causa referendada
      // nesta sessão não reabre, e a escalada seguinte a recebe pronta.
      if (causaCache[k]) {
        causaDisputada.push({ fn: k, ...causaCache[k], deCache: true })
        churnEscalated = true; break
      }
      if (churn[k] >= churnThreshold || fix.severity === 'P0') {
        // DIAGNOSE — diagnose_model (Opus medium, R8 "diagnóstico após falhas repetidas").
        // Não é mais "refaz cirúrgico" — é a causa raiz do acoplamento que faz a mesma
        // função regredir de novo a cada tentativa.
        //
        // ── A CAUSA NÃO ENTRA SEM SOBREVIVER AO DESAFIO (autópsia 2026-08-09) ──
        // Mesmo mecanismo do motor de implementação (/sprint): quem investiga PARA na
        // causa real; um desafiador a recebe com a ordem de PROVAR QUE ESTÁ ERRADA; os
        // dois trocam (o desafio da volta anterior volta ao investigador) até concordarem.
        // Três voltas sem acordo não escolhem vencedor — a disputa sobe no relatório com
        // as duas versões, porque conserto sobre causa disputada é remendo com etiqueta.
        let causa = null, desafio = null, acordo = false
        for (let volta = 1; volta <= 3 && !acordo; volta++) {
          causa = await agent(diagnosePrompt({ fix, churnCount: churn[k], invariants,
              desafioAnterior: desafio?.motivo || null }),
            { model: args.model, effort: T.diagnose.effort, phase: 'Diagnose', agentType: 'voltagent-qa-sec:architect-reviewer' })   // diagnose_model
          if (!causa) break
          desafio = await agent(desafioCausaPrompt({ fix, causa }),
            { model: args.model, effort: T.diagnose.effort, phase: 'Diagnose', schema: DESAFIO, agentType: 'voltagent-qa-sec:architect-reviewer' })
          acordo = desafio ? desafio.procede === true : false   // desafiador mudo não referenda
        }
        const desfecho = { fn: k, causa: acordo ? causa : null,
          disputa: acordo ? null : { investigador: String(causa || 'sem resposta').slice(0, 300),
                                     desafiador: String(desafio?.motivo || 'sem veredito').slice(0, 300) } }
        if (acordo) causaCache[k] = desfecho
        causaDisputada.push(desfecho)
        churnEscalated = true; break
      }
      // quem desfaz é o EXECUTOR (o `execPrompt` manda), e a afirmação só sai se ele confirmar
      log(res.reverted ? `fix ${fix.id} regrediu a suíte — o executor desfez a própria edição, churn …`
                       : `fix ${fix.id} regrediu a suíte e a edição FICOU DE PÉ … — precisa de decisão`)
    } else {
      corrections.push(res)
      if (res.newInvariant) invariants.push(res.newInvariant)   // invariante viva pras próximas rodadas
    }
  }

  proposedLimits.push(...(plan.proposedLimits || []))   // proposta ≠ limite: só o dono ratifica (R6)
  touchedLastRound = corrections.flatMap(c => c.files_touched || [])  // delta do REVIEW da próxima rodada
  openFindings = review.findings.filter(f => !corrections.some(c => c.fix_id === f.id))
  // `drift` e `rejected` entram AQUI porque o fecho os lê de `rounds`: sem `rejected`
  // gravado, o Set de rejeitados lá embaixo nasce vazio e todo achado derrubado pelo
  // árbitro volta a aparecer em `emAberto`.
  rounds.push({ r, review, plan, corrections, regressions, alerts: plan.alerts || [],
    drift: plan.drift || [], rejected: plan.rejected || [] })

  // TEATRO DE DÚVIDA — conta rodada SEM CONSERTO, com ou sem achado (rodada limpa não
  // chega aqui: sai por `cleanRound` antes). Sem este contador, com `maxRounds` Infinity
  // um P1 roteado para drift volta em `openFindings` toda rodada e o laço não tem saída.
  rodadasSemConserto = corrections.length === 0 ? rodadasSemConserto + 1 : 0
  // REGRESSÃO TOTAL ≠ teatro de dúvida — conserto que quebra a suíte NÃO entra em
  // `corrections`; a rodada caía no contador acima e o dono lia "NENHUM
  // virou conserto", com o laço tendo atacado e quebrado. Desfecho próprio.
  rodadasSoRegressao = (corrections.length === 0 && regressions > 0) ? rodadasSoRegressao + 1 : 0
  if (rodadasSoRegressao >= 2) regressaoTotal = true
  if (rodadasSemConserto >= 2) teatroDeDuvida = true
}

// ABANDONO POR AGENTE MUDO ≠ FREIO DE RODADAS — sem teto por default, `r < Infinity`
// nunca falha, e os `break` de agente mudo eram os únicos que caíam em `max-rounds`,
// fazendo o relatório culpar "o freio de Infinity rodada(s)". A `nota` é o motivo.
const agenteMudo = (rounds.length && rounds[rounds.length - 1].nota) || null

// VOLTAS POR PROBLEMA (F25.4) — quantas rodadas cada achado levou até sumir. Sai do que já
// está em `rounds`: da volta em que o problema apareceu até a última em que ainda aparecia.
// O relatório dizia só "3 rodadas" — número da sessão, não do defeito; sem este
// ninguém via QUAL problema custou as três, que é a leitura para a qual o laço existe.
const voltasPorProblema = []
const porId = {}
for (const x of rounds)
  for (const f of (x.review?.findings || [])) {
    if (!porId[f.id]) voltasPorProblema.push(porId[f.id] =
      { id: f.id, file: f.file, problem: f.problem, primeira: x.r, voltas: 0 })
    porId[f.id].voltas = x.r - porId[f.id].primeira + 1
  }

// O QUE FICOU DE PÉ, EM DUAS LISTAS (Artigo 14): achado não consertado, não rejeitado
// pelo árbitro e não aceito vai para `emAberto` se está ACIMA do piso (segura o fecho)
// ou para `abaixoDoPiso` (não bloqueia, mas é LISTADO — some do bloqueio, nunca da vista).
const consertados = new Set(rounds.flatMap(x => (x.corrections || []).map(c => c.fix_id)))
const rejeitados = new Set(rounds.flatMap(x => (x.rejected || []).map(f => f.id)))
const emAberto = [], abaixoDoPiso = [], jaListado = new Set()
for (const x of rounds)
  for (const f of (x.review?.findings || [])) {
    if (consertados.has(f.id) || rejeitados.has(f.id) || jaListado.has(f.id)) continue
    if (isAccepted(f, acceptedLimits)) continue
    jaListado.add(f.id)
    const item = { id: f.id, file: f.file, line: f.line, severity: f.severity,
                   problem: f.problem, fix_direction: f.fix_direction, vistoNaRodada: x.r }
    ;(sevRank(f.severity) >= floor ? emAberto : abaixoDoPiso).push(item)
  }

return {
  rounds, acceptedLimits, proposedLimits, invariants, churn,
  voltasPorProblema,   // por achado: em que volta apareceu e quantas levou até a rodada limpa
  causaDisputada,   // escaladas de churn: causa referendada pelo desafiador, ou as duas versões em disputa
  planFlawAlerts: rounds.flatMap(x => x.alerts),
  // as guardas não são zelo: a rodada de agente mudo empurra `{ r, review: null, nota }`
  // — sem elas o próprio fecho estoura no caminho que este bloco documenta acima.
  telemetry: rounds.map(x => ({ round: x.r, corrections: (x.corrections || []).length,
    regressions: x.regressions || 0, findings_by_sev: tallyBySev(x.review?.findings) })),
  // OS TRÊS PILARES (contrato: references/dimensoes-de-revisao.md). A rodada limpa é
  // CANDIDATA a fecho: dois auditores ISOLADOS (SEM_HISTORICO — não veem achados nem
  // histórico; recebem código final + as três âncoras PEDIDO·PLANO·RÉGUA) rodam entre o
  // confirm e o `cleanRound = true`. Schemas AUDIT_COBERTURA (itens do escopo × lentes
  // implementado/suite/e2e; 'revisado' e 'auditado' são conta do script) e
  // AUDIT_COERENCIA (régua item a item: conforme|violado|nao-aplicavel|nao-medido, com
  // `foraDaConta` para reaberto/minerado). QUEM SOMA O 100% É O SCRIPT (`furosDe`):
  // furo vira finding AUD-* (o árbitro não rebaixa nem rejeita — garantia no script) e o
  // laço REABRE; `e2e: sem-infra` sem `lentesDispensadas` ratificada fecha DECLARADO
  // ("COBERTURA NÃO MEDIDA NA LENTE E2E", sucesso: false); âncora ausente = 'sem-ancora'
  // declarado; auditor mudo nunca fecha.
  pilares: { qualidade: { status: cleanRound ? 'assintota-alcancada' : 'nao-fechou' },
             cobertura: { status: cobStatus, furos: furosCobertura, dispensadas: lentesDispensadas },
             coerencia: { status: coeStatus, violados: violadosCoerencia, foraDaConta: [] } },
  stopReason: cleanRound ? 'no-severe-finding'
    : auditoriaNaoMedida ? 'cobertura-nao-medida'
    : churnEscalated ? 'churn-escalated'
    : regressaoTotal ? 'regressao-total'
    : teatroDeDuvida ? 'teatro-de-duvida' : agenteMudo ? 'agente-mudo' : 'max-rounds',
  // Artigo 14: só a rodada limpa é sucesso. Teto, churn, teatro de dúvida e agente mudo
  // são FALHA, e a casca as reporta como "a revisão NÃO terminou", com `emAberto` na
  // frente do relatório. `abaixoDoPiso` acompanha SEMPRE, inclusive no sucesso.
  sucesso: cleanRound === true,
  severityFloor: args.severityFloor || 'P1',
  emAberto,
  abaixoDoPiso,
  vereditoHumano: cleanRound
    // `emAberto` pode ter item MESMO na rodada limpa (drift/alerts são destinos
    // legítimos e não viram conserto), então o sucesso confere a lista antes de
    // afirmar "nenhum achado".
    ? (emAberto.length
        ? `rodada limpa, mas ${emAberto.length} achado(s) acima do piso ficaram na mesa do dono (roteados para plano/drift, não consertados)`
        : `nenhum achado acima de ${args.severityFloor || 'P1'}`) +
      (abaixoDoPiso.length ? ` · ${abaixoDoPiso.length} abaixo do piso, listados e não bloqueantes` : '')
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
            ? `A REVISÃO NÃO TERMINOU — a rede de segurança deste projeto é Camada ${args.safetyLayer}, então cada conserto é aposta cega e mais voltas multiplicam o ESTRAGO: o laço parou em ${maxRounds} rodada(s) por RISCO, não por gasto, com ${emAberto.length} achado(s) acima do piso ainda de pé`
            : `A REVISÃO NÃO TERMINOU — o freio de ${maxRounds} rodada(s) agiu com ${emAberto.length} achado(s) acima do piso ainda de pé`,
}
```

**Schemas (JSON Schema, resumidos):**
- `FINDINGS` — `{ complete: boolean, findings: [{ id, file, line, severity: 'P0'|'P1'|'P2'|'P3', dimension, problem, fix_direction }] }`. `complete=false` se algum ângulo não retornou → NUNCA conta como rodada limpa.
- `PLAN` — `{ bucket1: [{ id, fn, severity, conflict_risk, order, fix_direction }], drift: [...], alerts: [...], proposedLimits: [...], invariants: [...] }`.
- `EXEC_RESULT` — `{ fix_id, fn, files_touched: [...], test_name, suiteRegressed: boolean, newInvariant?, note }`.
- `DESAFIO` — `{ procede: bool, motivo }`, devolvido por `desafioCausaPrompt` (`diagnose_model`). O desafiador recebe o fix escalado e a **causa** que o investigador apontou, com a ordem de **derrubá-la**: `procede: false` traz em `motivo` o fato que a causa não explica ou a concorrente mais simples — e volta ao investigador na próxima volta (`desafioAnterior`). `procede: true` referenda. Três voltas sem acordo → a disputa sai em `causaDisputada` com as duas versões, e o relatório a apresenta como decisão do dono; desafiador mudo **não referenda**.

> Os `agentType: voltagent-*` nos spawns são otimização de persona — se o agent type não existir na
> máquina, spawne sem `agentType` (o motor não depende deles).

### Os passos do motor, em detalhe

**REVIEW = 1 Opus Revisor (R1), no tier da rodada (R8).** Um único Opus cobre **o tripé inteiro como
CHECKLIST** — **não** um agente por dimensão. O que ele mede está em
**`references/dimensoes-de-revisao.md`** (fonte: `_shared/dimensoes-de-revisao.md` — não editar a
cópia à mão; `scripts/sync-shared.sh --check` pega drift): qualidade (as dimensões), cobertura por
finalidade e coerência com a régua. **Leia o arquivo antes do sweep** — a lista não é repetida aqui,
e é a MESMA que o `/sprint` usa ao revisar durante a construção.
**Rodada 1** roda em `decompose_model` (high — sweep completo): recebe **o material inteiro** + o
**plano-âncora** + os accepted-limits vivos (não re-reportar) + as invariantes vivas (não violar).
**Rodadas 2+** rodam em `coordinate_model` (medium) e recebem **o DELTA, não o material inteiro**: os arquivos
tocados pelos fixes da rodada anterior + os findings ainda abertos + accepted-limits/invariantes (pequenos) —
caça-regressão nas mudanças + ângulos frescos sobre elas. Formato de cada finding:
`P{0-3} — {arquivo:linha} — {problema} — {direção de fix, SEM código}`. Inclui sempre **duas âncoras** (nas
rodadas 2+, as duas restritas ao delta):
- **Plano** — "compare contra o PLANO: sinalize onde a implementação DIVERGE do planejado, mesmo que o código
  pareça bom".
- **Régua** — o Pé 3 de `references/dimensoes-de-revisao.md`: rode o `doc-load` e julgue contra TUDO
  que ele listar, citando o documento e a passagem violada. A lista de documentos **não é escrita
  aqui nem lá** — quem a produz é o programa. Sem régua no projeto o eixo **não roda** e o REVIEW
  segue só com o plano; ausência não é finding. **Quando o que
  a implementação descobriu contradiz um documento de concepção já aprovado** (`status: approved`), o finding
  sobe assim mesmo: a entrevista é que errou, não o código. O PLAN o roteia pro bucket 3 como proposta de
  **reabrir a etapa** — nunca pra fila de conserto.

**Regra dura:** se algum ângulo do checklist não foi coberto → `complete=false`, jamais "achou zero".

**CONFIRM = Opus dedicado em `finalize_model` (medium, R8 "revisão final e integração").** Quando uma rodada
parece limpa (`complete && severe.length===0`), o motor NÃO declara vitória direto — dispara um re-sweep
completo independente em `finalize_model`, sempre medium, **mesmo que a rodada que pareceu limpa tenha rodado
em `coordinate_model`**. Só confirma limpa se o confirm-pass TAMBÉM achar zero; senão os findings do
confirm-pass entram no PLAN da mesma rodada — o resultado mais barato nunca tem a palavra final.

**PLAN = Opus Planejador adversarial, árbitro único (R2), no MESMO tier da rodada.** Entre "achou" e
"consertar". 4 sub-passos: (a) consolida + dedup os findings; (b) **rotula cada um por BUCKET** (impl /
plan-drift / plan-flaw); (c) triagem do bucket 1 por severidade **e risco de conflito** (3 sinais checáveis
ANTES de editar — dois fixes na mesma função / fix que ALARGA regra genérica / fix que viola invariante viva);
(d) sequencia (extensão-enumerada primeiro, alargamento por último com negative-tests, agrupa por função).
**Mandato adversarial:** default a REJEITAR um finding (ou um accepted-limit) a não ser que se justifique
contra a rubrica. **Gerar ≠ julgar** — o Revisor acha, o Planejador é quem carimba a severidade (mata a
oscilação entre rodadas). Rodada 1 (`decompose_model`) = plano pesado; 2+ (`coordinate_model`) processam só o
DELTA.

**EXEC = Opus Executor em `executor_model` (R1).** SÓ bucket 1, **um fix por vez**, na ordem do PLAN:
(1) **test-first (red)** — escreve o teste que reproduz o finding e vê falhar; o teste recebe **nome com a
invariante** (`test_atravessa_placeholder_pro_par_aws`); (2) **fix cirúrgico** — menor mudança, **extensão
enumerada > alargamento de regra**; (3) **roda a SUÍTE INTEIRA**; (4) reporta. O executor **nunca** toca
bucket 2/3. Ele ser Opus **não** relaxa nenhuma dessas travas: o papel é estreito por design, não por
limitação de modelo.

**GATE de regressão (código, não LLM).** O `EXEC_RESULT.suiteRegressed` é objetivo (a suíte passou ou não).
Vermelho → o **executor desfaz a própria edição** e confirma em `reverted` (sem confirmação, o log diz que a
edição FICOU DE PÉ e precisa de decisão) + `churn++`; o Planejador (no tier da rodada) decide refazer cirúrgico (troca difuso
por extensão enumerada / exceção mais específica) — até `churn_threshold`. A partir do threshold, escala pra
`diagnose_model` (Opus medium, R8 "diagnóstico após falhas repetidas"): não é mais "refaz cirúrgico", é achar
a causa raiz do acoplamento. **Quem decide keep/revert é sempre o script + o Planejador, nunca o executor
que fez o fix** (executar o desfazer é dele; DECIDIR não) — é separação de papel, não desconfiança de modelo (agora os dois são Opus).

**Bucket 2 (plan-drift) e bucket 3 (plan-flaw)** nunca viram edição do executor (R4 e a constraint central abaixo).

---

## CONSTRAINT CENTRAL — QA ancorado no plano (3 buckets)

**Onde cada documento de projeto mora, e quem tem direito de escrevê-lo** — as pastas, o
frontmatter e a tabela de quem escreve e quem lê — está em `contrato-familia.md`, ao lado deste
arquivo (fonte: `_shared/contrato-familia.md`). Este loop **lê** a lei; nunca a escreve.

A skill **não é só review de código** — audita **fidelidade ao plano e à constituição do projeto** a cada
rodada. Todo finding é roteado em **3 buckets** no PLAN:

1. **Implementação** — código diverge do plano, **viola a régua que o `doc-load` listou**, deixa uma
   finalidade sem teste que morda, tem bug, ou regride. → fila de conserto (EXEC,
   com gate). Violar a régua é divergência igual às outras: entra pela rubrica de severidade normal,
   sem faixa própria. Os três são os pés de `references/dimensoes-de-revisao.md`.
2. **Plan-drift (R4)** — um "fix" otimizaria o código mas **afastaria o comportamento do que foi pedido/planejado**. → **restaura pro plano automaticamente** E o desvio sobe no bucket de alertas como **candidato a mudança-de-plano** pro usuário julgar. O plano vence a "melhoria", mesmo que o agente ache que faz sentido mudar. Drift é uma **classe de regressão** — não pausa.
3. **Plano/arquitetura falho** — o **plano em si** é falho (decisão de arquitetura que gera problema crítico). → **bucket de ALERTA**. NUNCA consertado/implementado no loop. Sobe pro usuário no relatório: "apresento e julgamos". É insumo pro planejamento, não trabalho de QA.
   - **Sub-caso — a concepção errou, não o plano:** o que a implementação descobriu contradiz um documento de concepção já aprovado (`status: approved`). O alerta vira **proposta de reabrir a etapa**: nomeia o documento, a passagem contradita e a linha `correcao-pendente: {o que precisa mudar}` que o **dono** grava no frontmatter. O loop **nunca edita o documento** — nem o corpo (mexer nele reabre a etapa pela marca do de acordo e congela o planejamento) nem o frontmatter. Propor é do loop; escrever e reaprovar é do dono.

> A skill **enforça** o plano; não o **redesenha**. Só o bucket 1 vira edição. "QA é QA."

## Rubrica de severidade (R2) — 3 faixas, escrita, aplicada pelo árbitro único

- **P0/P1 (acima do floor)** — exige gatilho **objetivo** OU **ancorado no plano**: quebra comportamento do
  plano · classe de segurança (secret, injection, authz) · bug com repro determinístico. *(Falha objetiva de
  lint/type/unit/integração NÃO entra nesta escada — é da **Fase Gate**, absoluta e separada.)*
- **P2/P3 (abaixo do floor)** — opinião de qualidade **sem** divergência do plano e **sem** falha objetiva
  (naming, gosto, micro-refator). **Picuinha nunca sobe sozinha** — só vira P1 com bug concreto anexado.
- O **Opus Planejador é o ÁRBITRO ÚNICO** que aplica a rubrica. Não são N LLMs cada um carimbando — é um juiz,
  rubrica escrita, severidade comparável entre rodadas (e na telemetria).

### Os cinco antipadrões de teste — contrato em `references/antipadroes-de-teste.md`

Teste que não morde é **finding de implementação**, não observação de estilo — e o conserto
é o teste, não o código. Os cinco jeitos de um teste passar sem servir pra nada (passa com
e sem a mudança · espera texto que o código nunca escreve · só o caminho feliz · mede a
coisa errada · segundo plano com espera pelo resultado), cada um com o caso real que o
originou e como evitar, estão em **`references/antipadroes-de-teste.md`** (fonte:
`_shared/antipadroes-de-teste.md` — não editar a cópia à mão; `scripts/sync-shared.sh
--check` pega drift). **Leia o arquivo antes do sweep de review**: a mesma lista é citada
pela régua do `pronto` do `/visual`, porque o critério erra antes do teste.

## Config em 3 camadas (R3) — `.claude/qa-loop.config.md` (VERSIONADO)

Fora da pasta ignorada `.claude/qa-loop/`. Versionado de propósito — viaja com o projeto. Contém:
- **Knobs** do projeto (floor, max_rounds, churn_threshold) que sobrescrevem o default.
- **Rubrica do projeto** — ajustes de severidade específicos do alvo.
- **Accepted-limits permanentes** (ratificados pelo usuário — ver R6) + **invariantes vivas**.
- **Flags de invocação** padrão.

Precedência: **flag > config do projeto > default da skill.**

## Critério de parada — Artigo 14: assíntota de SEVERIDADE, nunca gasto

**Há UM desfecho que é sucesso, e ele exige as DUAS fases fechadas.**

**Fase de Julgamento — o ÚNICO fecho legítimo (a assíntota):**
- uma rodada INTEIRA completou (`complete=true`) E produziu ZERO findings **acima do piso de
  severidade** (`severity_floor`) que não estejam resolvidos ou anistiados pelo dono, **E o
  confirm-pass dedicado (`finalize_model`) concordou** — rodada limpa nunca é declarada só pelo
  resultado mais barato (`coordinate_model`) que pareceu limpo.
- **Achado abaixo do piso NÃO segura o fecho.** Ele é listado no relatório com severidade e
  local, e pronto. Isso não é desistir: é a definição correta do alvo — preciosismo que não
  afeta consistência nem funcionamento nunca foi o que a revisão está procurando.
- **Achado acima do piso SEMPRE segura o fecho**, por mais barato que pareça ignorá-lo, e por
  mais voltas que o laço já tenha dado.

**Todo o resto é FALHA, e sai do laço com a lista do que ficou acima do piso:**
- **[FALHA]** `max-rounds` (o teto `max_rounds`), quando quem invocou passou um. **Isto não é "parou", é "não
  terminou"** — o relatório abre com o que ficou acima do piso, e o dono decide: outra volta ou
  anistia explícita. **Sem teto passado, este desfecho não existe**, que é o normal.
- **[FALHA]** churn escalou (≥`churn_threshold` regressões na mesma função) → passa por
  `diagnose_model` e vira `churn-escalated`, com a causa (ou a disputa) no relatório. **Não é
  parada por esforço:** é o sinal de que remendar ali está gerando estrago, e a saída é
  investigar a causa raiz — mais trabalho, não menos.
- **[FALHA]** `regressao-total` — a rodada tentou consertos e TODOS regrediram a suíte. O
  relatório nomeia a suíte quebrada e nunca diz que nenhum achado virou conserto: viraram, e
  cada um quebrou o que estava de pé.
- **[FALHA]** `teatro-de-duvida` — duas rodadas com achado e ZERO conserto. Não é parada por
  esforço: é o laço ter deixado de atacar problema. Ver a seção "Teatro de dúvida".
- **[FALHA]** `agente-mudo` — um agente do laço devolveu vazio e a rodada não pôde ser julgada.
  Silêncio de agente nunca vira rodada limpa.
- **[FALHA]** `cobertura-nao-medida` — a auditoria externa do pilar COBERTURA não conseguiu medir a
  lente E2E (o projeto não tem como executar a confirmação direta) e o dono ainda não ratificou a
  dispensa. **Não é parada por esforço:** é o laço declarando que uma lente da aprovação ficou sem
  medição — girar mais uma volta não a mediria, porque não há conserto de executor para infra ausente.
  O veredito abre com "COBERTURA NÃO MEDIDA NA LENTE E2E" e a decisão é do dono: ratificar a dispensa
  em `lentesDispensadas` do `qa-loop.config.md`, ou mandar criar a infra.
- **[FALHA]** `gate-red` — ver abaixo.

**Fase Gate — condição ABSOLUTA de sucesso:**
- **Sucesso EXIGE a Fase Gate 100% verde** (lint/type/unit/integração no repo inteiro, incluindo
  pré-existentes). Vermelho → vira fila de conserto; se travar, `stopReason='gate-red'` (fracasso
  explícito, **nunca** sucesso). e2e/Playwright **NÃO** entra aqui — vira actionable.
- Projeto sem checks objetivos → Fase Gate **vazia, declarada honesto** (não é sucesso fingido nem gate-red).

> **Não há teto por default, e teto nunca é critério.** Ele existe só como freio de quem invoca,
> para um laço preso em defeito de ambiente não rodar a noite inteira, e bater nele é falha. Teto
> **não se declara dentro do projeto** — número escrito antes de saber o que a obra tem envelhece
> calado e vira lei sem dono (medido: um `max_rounds: 6` viajava em dois `qa-loop.config.md` sem
> ninguém ter decidido, e um deles ainda o chamava de "default" quando o default era 12).

## O eixo é severidade. Gasto NUNCA entra na conta.

**Tokens, tempo e número de rodadas são números PASSIVOS no journal** — nunca eixo de parada,
nunca framing de "custo". Um achado acima do piso obriga outra volta, e o preço disso não entra
na conta. O que legitimamente tira um achado da frente é só isto:

- ele está **abaixo do piso de severidade** — vai para a lista, não para o bloqueio; ou
- ele foi **resolvido** (com teste que morde e a suíte verde); ou
- o árbitro julgou que **não procede**, e escreveu o motivo em `rejected`; ou
- o **dono ratificou** um limite aceito, com o motivo, no `qa-loop.config.md`.

**O que NUNCA tira um achado da frente:** rebaixar a severidade dele para caber num desses.
Essa é a fraude do critério, e é a falta mais grave do Artigo 14 porque não deixa rastro — o
relatório fica verde e o defeito fica de pé. A rubrica e o árbitro único existem exatamente
para que a severidade não seja negociada pelo cansaço de quem quer fechar.

### Teatro de dúvida — o sinal de duas rodadas com achado e zero acionável

**O sinal, nomeado:** duas rodadas seguidas produziram findings e NENHUM deles virou conserto —
todos caíram em plan-drift, plano-falho, limite proposto ou P2 documentado. Isso não é convergência:
é **validação fantasiada de revisão**. O loop está pagando rodada para carimbar o que já estava lá,
e a rodada limpa que vier depois vale zero, porque nada foi mexido entre uma e outra.

**Não confunda com o Artigo 14.** Parar aqui não é parar por esforço: é parar porque o laço **deixou
de produzir conserto**, ou seja, está rodando sem atacar problema nenhum. Por isso o desfecho é
`teatro-de-duvida` e é **FALHA** — com os achados que ficaram de pé indo para a mesa do dono.

**A conduta, escrita** — quem conta é o MOTOR, dentro do laço. A casca não tem como contar: o
Workflow é um só e ela só vê `rounds` depois do return, quando a terceira rodada já foi paga.

1. Na segunda rodada seguida sem nenhum acionável, **PARE o loop** — o motor não dispara a
   terceira rodada e devolve `stopReason: 'teatro-de-duvida'` com `sucesso: false`.
2. O relatório abre nomeando o sinal — *teatro de dúvida* — e diz para onde os achados foram
   (quantos viraram plan-drift, quantos plano-falho, quantos limite, quantos P2).
3. **Isso não é sucesso.** A Fase Gate continua obrigatória, e a parada é reportada como
   `teatro-de-duvida`, ao lado de `gate-red` e do teto — nunca como rodada limpa.
4. Se o dono quiser continuar, o próximo ciclo muda de eixo (outro alvo, outro tripé) ou muda o
   plano — repetir o mesmo review no mesmo alvo produz o mesmo teatro.

---

## CASCA — Passo 8 · Fase Gate (saída) + Relatório (humano) + Journal (agêntico) — R7

Quando o Workflow retorna, a casca executa a **Fase Gate** e SÓ ENTÃO produz os artefatos.

### Passo 8.0 · FASE GATE — o portão absoluto de saída

Antes de qualquer relatório, a casca roda os **checks objetivos do projeto** como portão binário:

- **Cache verde (consulta → grava):** `source "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/green-cache.sh)"`. Antes de rodar a
  fila, `green_cache_check <repo-root> full`: **HIT** → declara o gate verde via cache e **reporta** no
  relatório ("gate 100% via cache — tree `<hash>`, gravado por `<writer>` às `<ts>`") sem re-executar.
  **MISS** → roda a fila normal; ao fechar 100% verde, `green_cache_mark <repo-root> full qa-loop-gate`.
  **Gate vermelho nunca grava.** Falha do helper (sem git, fora de repo) → MISS silencioso, roda tudo.
  Cache HIT não é burla: é a mesma fila, verde, no mesmo tree-hash — qualquer edição invalida.
- **O que roda:** lint + type-check + teste unitário + teste de integração. **A detecção reusa as camadas
  já definidas** (ver "Detecção de rede"): unit/integração = Camada 1; lint/type = Camada 3. **e2e marcado**
  (`@pytest.mark.e2e`, specs Playwright, script `e2e`) é **EXCLUÍDO daqui** → vira actionable na Fase
  Assintótica (lento demais e dependente de ambiente pra ser portão). ⚠️ **Fora do portão ≠ fora da
  aprovação**: E2E é lente obrigatória do pilar COBERTURA (a auditoria externa do motor, contrato em
  `references/dimensoes-de-revisao.md`) — sem infra E2E o fecho sai "COBERTURA NÃO MEDIDA NA LENTE E2E"
  até o dono ratificar a dispensa no `qa-loop.config.md`.
- **Escopo: repo inteiro, absoluto.** Exige TODO o lint/type/unit/integração do repo **100% verde —
  incluindo erros pré-existentes não-relacionados à revisão**. "Tá errado = corrige = fim." Sem severidade,
  sem limite aceito, sem desconto por esforço gasto. (Mesma disciplina do `/ship`, rodada mais cedo.) Se o
  projeto oferece um runner com escopo próprio (`scripts/run_app_tests.sh`, target de Makefile,
  `pnpm --filter`, `cargo test -p`), use-o **pra rodar no ambiente certo** — nunca pra encolher o que
  precisa passar; em monorepo de múltiplos ambientes é o que evita falso-vermelho de import.
- **Vermelho → conserta em `mechanical_model` (fila objetiva, FORA do roteamento de buckets).** Erro de
  lint/type/unit/integração é objetivo e determinístico — não precisa do julgamento de severidade do
  REVIEW→PLAN, nem do effort caro do `executor_model`. Vai direto pra uma fila de conserto em
  `mechanical_model` (R8, "operações mecânicas e bem delimitadas" — mesmo regression gate por
  conserto), re-roda o gate, até verde. **Não passa pelos 3 buckets** (esses são pro review subjetivo da fase
  assintótica). Se travar de verdade (erro que exige decisão de arquitetura), **NÃO declara sucesso** — e o
  conserto que travou escala pra `diagnose_model` (medium) antes de virar `gate-red`.
- **Quem seta o `stopReason` FINAL é a CASCA, não o motor.** O motor (Workflow) reporta o stopReason da fase
  assintótica (`no-severe-finding` / `cobertura-nao-medida` / `churn-escalated` / `regressao-total` /
  `teatro-de-duvida` / `agente-mudo` / `max-rounds` — os sete que o `return` produz); a casca, pós-gate, computa o stopReason
  da sessão — **promove a `gate-red`** quando o gate trava vermelho, e mantém o do motor quando o gate fecha
  verde. O relatório **lidera** com "GATE VERMELHO — bloqueante" sempre que `gate-red`.
- **Transparência (anti-violação-de-surgical-changes).** O conserto repo-wide é real, mas o relatório
  **separa duas pilhas** — "consertos da revisão" vs "débito pré-existente que precisei zerar pro gate ficar
  verde" — cada uma com seu diff, pra o usuário ver e reverter o que quiser.
- **Sem checks no projeto → Fase Gate vazia, declarada honesto** ("sem checks objetivos — só a fase
  assintótica rodou"). Nunca finge portão.

Passada a Fase Gate, a casca produz **DOIS artefatos com públicos distintos**:

### (A) Relatório HUMANO — gerador de actionables, via a skill `/visual` como parceira

**INVOQUE a skill `/visual`** pra renderizar (não reimplemente template nem daemon): o `/visual` já traz a
hierarquia, o "pedido se explica sozinho", o vocabulário banido, o daemon de live-sync e a semântica de copy.
Você passa o conteúdo estruturado (do `return` do Workflow); o `/visual` resolve template + daemon + path + abre.
**Visual ausente na máquina** (resolvedor devolve vazio): o relatório não some — grave o mesmo conteúdo em
`.claude/reports/<data>-qa-loop.md` e diga na entrega que a página não abriu por falta do plugin.

**A página é EMITIDA por programa, não digitada** (desde o `visual` v1.8.0). Você escreve um **spec JSON** e
roda `python3 <visual>/lib/visual_page.py build --spec <f>`; o contrato dos blocos sai de
`visual_page.py schema`. Isso não é detalhe de forma — é o que garante, sem depender de você lembrar, as duas
regras duras desta seção: **nenhum `feedback-item` nasce selecionado** e o contador começa em `0 de N`.
A estrutura abaixo mapeia assim: faixa de status → bloco `callout`; gráfico → bloco `chart`; cada actionable →
bloco `item` (com `tri` quando for bloqueio) e `item_labels: ["✓ Vira ação", "✏️ Ação c/ ajuste", "✗ Descartar"]`;
fechamento → automático. **O build recusa** relatório que peça veredito sem nenhuma prova na página.

Estrutura do relatório (no topo → fundo):
- **Faixa de STATUS DA FASE GATE (topo de tudo, read-only):** verde "gate 100% — N checks" ou vermelho
  "GATE VERMELHO — bloqueante" (`stopReason='gate-red'`). Se houve conserto repo-wide, **separa duas pilhas**
  com diff — "consertos da revisão" vs "débito pré-existente zerado" — pra o usuário revisar/reverter. Fica
  ACIMA de tudo: um gate vermelho é a primeira coisa que ele vê. **O veredito da faixa é o `vereditoHumano`
  do `return`, impresso LITERAL** — não redigite frase de desfecho: o motor já conta os que ficaram e sabe se
  foi rodada limpa, teto, teatro de dúvida ou agente mudo. **Colada nela, a lista `emAberto`** (achados ACIMA
  do piso que sobraram de pé, cada um com id · severidade · arquivo), read-only — é a promessa central do fecho
  e não tem outra seção onde caber.
- **Gráfico único — findings por severidade: NÃO desenhe o SVG.** Emita o bloco `chart` do spec, com uma
  entrada por rodada: `{"kind":"chart","rounds":[{"label":"R1","p0":2,"p1":6,"p2":4,"p3":1}, …]}`. Os números
  saem direto do `return` do Workflow; o programa desenha as barras empilhadas P0/P1/P2/P3 e sobrepõe a linha de
  severidade real (P0+P1) — a composição E a queda no mesmo lugar. Um gráfico só, porque com 4-5 rodadas dois
  lado a lado apertam. **Por que é do programa:** coordenada de barra é aritmética sobre número que você já
  recebeu pronto, e barra fora de escala **não dá erro** — dá a conclusão errada sobre a queda da severidade
  ao longo das voltas, que é a única leitura pra qual este gráfico existe. Contagem em string é recusada pelo build (nada de coerção
  silenciosa). + **tabela por rodada** com as considerações **DENTRO da linha** (colapsável, o `detail` do item),
  NÃO um listão depois. Read-only.
- **Voltas por problema (logo abaixo do gráfico, read-only):** uma linha por achado do
  `voltasPorProblema` do `return` — o problema, o arquivo, em que volta apareceu e **quantas voltas
  levou até a rodada limpa**. É a leitura que o total de rodadas esconde: três rodadas podem ser um
  defeito teimoso ou três defeitos de uma volta cada, e as duas pedem ação diferente. O número sai do
  motor pronto; não o recalcule lendo as rodadas.
- **4 categorias de ACTIONABLE** — o que sobe pro usuário deixa de ser "alerta genérico" e vira 4 seções, cada
  achado um **`feedback-item` SELECIONÁVEL** (os valores internos `keep`/`change`/`remove` ficam, mas os labels
  viram **"✓ Vira ação" / "✏️ Ação c/ ajuste" / "✗ Descartar"** — o `/visual` autoriza relabelar). Cada item é
  **auto-explicável**: título humano (1 linha, sem jargão de código) + porquê/impacto (1-2 linhas) + onde (path);
  o detalhe técnico fica no colapsável.
  - **Estado inicial NEUTRO (regra dura): todo `feedback-item` nasce SEM seleção — sem radio `checked`, sem classe
    `state-*`.** Nenhuma categoria entra pré-marcada como "✓ Vira ação", e isso vale **especialmente pras Sugestões**:
    o loop ter PROPOSTO um refator/drift NÃO é "sim" do usuário — é candidato a decisão dele. Razão dupla: (1) força a
    decisão ativa (não assume "sim" sem querer); (2) mantém o contador honesto — ele conta `input:checked`, então
    pré-marcar só a APARÊNCIA (classe `state-keep` sem `checked`) dessincroniza: o item parece selecionado e o contador
    segue em **0**. O progresso começa em **0 de N** e só sobe no clique.

  O mapeamento (a partir do `return`):
  1. **Importantes — recomendação** ← `planFlawAlerts` P0/P1 (decisões de arquitetura do plano: "apresento e julgamos") — **inclui a proposta de reabrir a etapa** quando a concepção errou, com o documento, a passagem e a linha `correcao-pendente:` sugerida.
  2. **Sugestões de melhoria** ← `plan-drift` (candidatos a mudança de plano) + refators propostos pelo loop.
  3. **Limitações atuais** (não quebram, mas importam) ← `proposedLimits` (propostos, à espera da ratificação do dono) + churn hotspots.
  4. **Extras** (opcionais) ← `abaixoDoPiso` do `return` (os P2/P3 documentados — picuinhas abaixo do floor,
     nice-to-have). Acompanha SEMPRE, inclusive quando a corrida fecha em sucesso: some do bloqueio, nunca da vista.
- **Fechamento** (`feedback-box`): progresso + observação geral + botões "Aprovar tudo" / "Copiar feedback".

**Seleção live → próximo plano (o ciclo fecha aqui).** O usuário marca os itens, diz **"ok"**, e a casca lê
`~/.claude/visual-state/latest.json` (o daemon do `/visual`) e **monta o próximo plano só com os itens marcados
"✓ Vira ação" / "✏️ Ação c/ ajuste"** (a nota do "ajuste" entra como refinamento). Copy/paste é o fallback
quando o daemon está off. É assim que o relatório de QA vira o INPUT do próximo plano, sem retrabalho.

Polish: densidade controlada (sem parágrafo longo), hierarquia por cor + `sev`-tag, cada categoria com peso
visual distinto. Linguagem humana. (Ver `EXAMPLE-REPORT.html`.)

Se não headless, pergunta o **veredito 0-10** do usuário (1 pergunta opcional/skipável) — a âncora subjetiva.

### (B) Journal AGÊNTICO — markdown verborrágico, pra "futuro-eu" (3 camadas)

NÃO é pro usuário ler — é o agente passando informação pra ele mesmo do futuro **melhorar a skill**. (Ver `EXAMPLE-JOURNAL.md`.)

1. **Telemetria quantitativa** — JSONL append-only, 1 linha/sessão, pra calibrar nº de loops/rubrica. Os números
   **saem do `return` do Workflow** — não é contabilidade extra.
   - **Por projeto:** `<projeto>/.claude/qa-loop/telemetry.jsonl` (no `.gitignore`).
   - **Agregado cross-projeto:** `~/.claude/qa-loop/journal/telemetry.jsonl` (sobrevive a reinstalar o plugin).
2. **Aprendizado da SKILL** — `~/.claude/qa-loop/journal/learnings.md` (cross-projeto, acumula): findings
   exaustivos sobre onde o **próprio PROCESSO de QA** acertou/errou + **AÇÃO concreta pra futuro-eu**. Ex.:
   "o usuário rebaixou P1→P2 num finding de naming → AÇÃO: rubrica — naming enganoso só é P1 com bug concreto";
   "regressão escapou do gate porque o teste-red não cobria a interação entre estágios → o checklist do Revisor
   precisa de uma linha sobre interação". Registra também o que FUNCIONOU (pra não regredir o prompt).
3. **Memória de QA do PROJETO** — versionada, junto da config (`.claude/qa-loop.config.md`): invariantes vivas,
   accepted-limits ratificados, churn hotspots (funções acopladas), plan-flaws recorrentes.

### O loop fecha: a skill LÊ o journal no INÍCIO de cada sessão (passo 0)

A memória do projeto semeia os accepted-limits + invariantes; os aprendizados da skill afinam a rubrica/prompt.
É assim que "melhora com o uso" — **agêntico + humano-no-loop** (os aprendizados viram refino da skill pelo
agente e pelo usuário, periodicamente). **Zero auto-tuning automático no v1.** (Por que não autoresearch: o método do Karpathy
depende de UMA métrica escalar barata e comparável entre runs, que review NÃO tem; o keep/discard dele já existe
aqui no lugar certo — é o regression gate, que decide por teste objetivo.)

Schema da telemetria (1 objeto por linha):
```json
{"ts":"<ISO>","target":"<path/desc>","domain":"asymptotic","severity_floor":"P1","max_rounds_config":6,"rounds_run":3,"corrections_per_round":[5,1,0],"last_round_with_severe_finding":2,"regressions_self_inflicted":1,"accepted_limits":1,"plan_flaw_alerts":1,"tokens_per_round":[...],"stop_reason":"no-severe-finding","user_score_0_10":null}
```
`last_round_with_severe_finding` (mediana entre sessões assintóticas) é a resposta empírica ao "3 loops?".

---

## Guard-rails operacionais

### Regression gate por conserto (o maior ROI)
A suíte inteira a cada conserto converte 4 dos 5 mecanismos de regressão de "descoberto 3 rodadas depois" em
"falha na mesma edição". É o GATE de regressão do motor. Não pule, não bata só o teste novo.

### Os 5 mecanismos de regressão (operacionalizados)
- **A — alargamento de escopo:** consertar um falso-negativo alargando uma regra genérica cria falso-positivo em outro canto. → **extensão enumerada > alargamento**; negative-tests logo após. Prevenido no PLAN.
- **B — ordem de curto-circuito:** exceção (early-return) antes da regra principal engole o caso de interseção. → ordene checagens positivas fortes ANTES das exceções; teste a interseção. Pego pelo gate.
- **C — proxy sintático grosseiro:** uma propriedade superficial (tem "/", é numérico) usada como semântica vale pros dois lados da fronteira. → combine sinais; na dúvida, inverta o default pro lado seguro. Pego pelo gate.
- **D — conflito entre correções:** a correção K+n viola a invariante da correção K. → teste **nomeado com a invariante**; suíte inteira a cada conserto. Prevenido no PLAN (invariantes vivas) + pego pelo gate.
- **E — interação entre estágios:** um estágio deixa resíduo que outro consome. → cada estágio neutraliza o que processou; teste a INTERAÇÃO entre estágios. Pego pelo gate.

### Detecção de rede — DOIS usos da mesma detecção
As camadas abaixo são detectadas UMA vez e servem a **dois propósitos distintos**:
1. **Regression net DURANTE o loop** (Fase Assintótica) — a suíte roda a cada conserto pra pegar regressão
   auto-infligida na hora. Aqui "cumprir 100%" = **honestidade 100%** sobre a rede, nunca fingir segurança;
   com rede fraca, baixa o teto e declara o blast-radius não-coberto.
2. **Fase Gate de SAÍDA** (Passo 8.0) — portão absoluto: **só as Camadas 1 e 3** (unit/integração + lint/type)
   compõem o gate e têm que estar 100% verdes no repo pra declarar sucesso. A Camada 2 (caracterização, escopo
   parcial) e a Camada 4 (e2e, dependente de ambiente) ficam **de FORA** do gate — são da Fase de Julgamento.
   Aqui NÃO há teto nem desconto por esforço — é binário. (O teto só limita o nº de rodadas da Fase de
   Julgamento quando a rede de regressão é fraca; não toca o gate.)

Detecte na ordem:

- **Camada 1 — Suíte de testes (unit + integração).** Detecta: `test` script em **package.json** · jest/vitest/mocha em devDependencies · `pytest` em **pyproject.toml**/**setup.cfg** · **Cargo.toml**→`cargo test` · **go.mod**→`go test ./...` · target `test` em **Makefile**. **→ compõe a Fase Gate (absoluta).** e2e marcado (`@pytest.mark.e2e`) é separado daqui → Camada 4.
- **Camada 2 — Testes-de-caracterização gerados** dos próprios teste-red do gate. Cobre SÓ os findings já tocados — declara isso. Net da Fase Assintótica (não é portão absoluto). Começa vazia (rodada 1 roda com menos rede).
- **Camada 3 — Lint + typecheck.** Detecta: **eslint.config.\***/**.eslintrc.\***/**biome.json**→lint; **tsconfig.json**/**pyproject.toml**(ruff/mypy/pyright)→typecheck. **→ compõe a Fase Gate (absoluta).** Era "net teto 2" — virou portão: um erro de type não é net fraco, é falha binária.
- **Camada 4 — Jornada Playwright / e2e** (alvo com UX). Print + análise da tela (não só DOM). Cobre só o caminho roteirizado. **Fase Assintótica** — vira actionable, **não bloqueia** (lento e dependente de ambiente). Teto 2.
- **Camada 5 — Sem rede objetiva.** Fase Gate **vazia, declarada honesto**. A Fase Assintótica NÃO roda como se houvesse proteção ("sem testes, sem lint/types, sem jornada — cada conserto é aposta cega; rodo no máx 1 rodada de críticos e paro"). Teto 1.

A camada escolhida (e o que ela não cobre) é arg do Workflow (`safetyLayer`), entra no header da rodada e no
relatório. Os tetos das Camadas 4 e 5 **não são conselho ao modelo** — o motor clampa `maxRounds` por
`LAYER_CAP`, então rede fraca não consegue gastar 6 rodadas de aposta cega nem que o prompt esqueça a regra.

### Churn detector
Por **FUNÇÃO** (não arquivo): conta edições + regressões auto-infligidas. ≥`churn_threshold` regressões na mesma
função → **escala** (para de remendar; sinaliza "acoplamento alto: refatora pra detectores independentes OU aceita
os limites"). É lógica do script do motor. **E a gravidade também escala** (decisão do dono, 2026-08-09): fix P0
que regrediu investiga a causa na PRIMEIRA queda, sem esperar reincidir — com o cache de causa por chave
`arquivo:função`, para a mesma raiz não pagar duas investigações na mesma sessão.

### Accepted-limits (R6) — proposto, nunca enterrado sozinho
Vivo, **ancorado ao alvo**. O loop **PROPÕE** (`plan.proposedLimits`); o Planejador adjudica se procede; mas só
vira **PERMANENTE** quando o usuário move pra `.claude/qa-loop.config.md`. **Critério explícito de entrada** (é
<!-- artigo14-ok: nomeia o abuso que a ratificação do dono existe para impedir -->
genuinamente espaço-de-input-infinito? ou só difícil?) — não é o lixo do que cansou de consertar; um bug real
classificado como limite some pra sempre. **Headless propõe + reporta, nunca grava permanente.**

**É AQUI que o Artigo 14 encosta.** O limite aceito é a ÚNICA porta legítima para um achado
procedente ficar sem conserto — e ela é do **dono**, não do laço. O loop nunca grava permanente,
nunca "aceita para poder fechar", e a rodada limpa que depende de um limite não-ratificado não é
rodada limpa: o achado segue em `emAberto` e o desfecho segue sendo falha.

**Finding de Fase Gate (lint/type/unit/integração vermelho) é INELEGÍVEL a accepted-limit** — erro objetivo
nunca vira "limite aceito" nem P2 rebaixado. Só findings da Fase Assintótica podem virar limite; o gate é
absoluto por definição.

### Findings arquiteturais (não viram teste-red)
"A abordagem é frágil", "acoplamento alto", "naming enganoso" não reproduzem por teste determinístico. →
**excluídos do regression gate; só reportados** (viram bucket plan-flaw / alerta, ou P2 documentado). Nunca
consertados automaticamente sem rede.

---

## Modo headless (pro /sprint)

Com `--headless`: o loop NUNCA pergunta nada (auto-classifica domínio como assintótico se ambíguo, usa os
defaults, pula o veredito 0-10). **Alertas de plan-flaw continuam NÃO virando fix** — ficam no relatório pro
usuário revisar depois. Headless ≠ licença pra re-planejar nem pra ratificar accepted-limit. O relatório da
`/qa-loop` vira a seção final de QA do report do `/sprint`.

**A Fase Gate (absoluta) vale em headless também** — o gate vermelho não pergunta nada, mas entra no
relatório como bloqueante (`stopReason='gate-red'`), virando item de "Bloqueios (precisam de você)" no
report do `/sprint`. Conserto de fundamento (lint/type/unit/integração) está no mandato do headless; re-planejar
um plan-flaw, não.

## Fronteira com a `/completude` (defeito aqui; elo aberto lá)

Esta skill pergunta _"o código construído tem defeito?"_ — bug, regressão, lint/type/test,
fidelidade ao plano. Ela lê **código**. A `/completude` pergunta _"sobrou alguém de fora?"_ —
funcionalidade sem requisito, requisito sem tarefa, tarefa marcada sem prova, artigo da lei
que nenhuma tarefa carrega — e lê **documento**, por programa, no projeto inteiro.

Não se substituem e não se cobrem: gate verde aqui não diz que a cadeia fecha, e cadeia
fechada lá não diz que o código está certo. **Elo aberto da `/completude` não é finding
desta skill** — não vira fix, não vira plan-flaw, não entra no relatório como bloqueio daqui.
A ordem usual é `/qa-loop` primeiro (o código está certo?) e `/completude` por último, antes
de declarar a frente pronta.

## Quando NÃO usar

- Sem nada implementado pra revisar → recuse.
- Aplicar fix sem rede de regressão E sem aceitar o teto-1 da Camada 5 → declare a cegueira, não finja.
- Tarefa puramente convergente de 1 passo que você já sabe consertar → só conserte, não embrulhe num loop.

## Regras de segurança

- Nunca declarar "rodada limpa" sem `complete=true` (todos os ângulos do checklist cobertos).
- **Nunca declarar SUCESSO com a Fase Gate vermelha.** lint/type/unit/integração do repo têm que estar 100%
  verdes (incluindo pré-existentes); se travar, `stopReason='gate-red'`, nunca "sucesso". Erro objetivo nunca
  vira accepted-limit nem P2 rebaixado.
- **Fase Gate é repo-inteiro-absoluto, mas com transparência:** o relatório separa "conserto da revisão" de
  "débito pré-existente zerado" (com diff) — conserto repo-wide nunca é silencioso (respeita surgical-changes).
- Nunca consertar um finding de bucket plan-drift no sentido que afasta do plano; nunca implementar um plan-flaw.
- Nunca rodar como se houvesse rede de regressão quando não há (Camada 5 é declaração explícita, não fallback silencioso).
- O fecho é a assíntota de SEVERIDADE (Artigo 14): enquanto houver achado **acima do piso**, o
  laço continua — não importa quantas voltas já deu, quanto custou ou quanto tempo levou. Teto,
  quando quem invoca passa um, é freio de emergência, e bater nele é FALHA.
- Quem decide keep/revert de um fix é o script + o Planejador, **nunca o agente que fez o fix** — mesmo com
  todo mundo em Opus 5, o gate é separação de papel, não desconfiança de modelo.

## Racionalizações — a desculpa refutada antes de você dá-la

Cada frase abaixo já fechou um loop cedo demais. Se você se ouvir pensando a da esquerda,
a resposta já está dada:

- **"a rodada veio limpa, então está 100%"** → rodada limpa quer dizer que nada acima do piso
  apareceu NESTA volta, não que o código esteja correto. O relatório diz o que a assíntota
  alcançou, nunca "não há mais defeito".
- **"sobrou só P2, dá pra encerrar"** → **este está certo, e é o critério** — P2 abaixo do piso
  vai para a lista e não segura o fecho. O que é proibido é o passo seguinte: **rebaixar** um P1
  para P2 a fim de chegar nesse estado. Severidade quem decide é a rubrica e o árbitro único,
  nunca a vontade de fechar.
<!-- artigo14-ok: nomeia as desculpas para refutá-las -->
- **"já rodei bastante, o retorno está caindo"** → **Artigo 14: isso não é a assíntota.** A
  assíntota é de severidade, não de quantidade de achados. Uma rodada que traz um P0 não fecha,
  mesmo que as três anteriores só tenham trazido P3.
- **"está ficando caro / gastando muito token"** → gasto nunca é eixo de parada. Se o preço
  virou o problema, quem decide encurtar é o dono, avisado, e a decisão sai no relatório.
- **"o teto chegou, então terminei"** → teto atingido é `max-rounds`, que é **FALHA**. Entregue a
  lista do que ficou acima do piso e diga que a revisão não terminou.
- **"esse lint já estava vermelho antes de eu chegar"** → a Fase Gate é repo-inteiro-absoluto.
  Débito pré-existente vermelho é gate vermelho, e `stopReason='gate-red'`.
- **"eu fiz o conserto, eu mesmo confiro que ficou bom"** → quem faz o fix nunca decide
  keep/revert. É separação de papel, não desconfiança de modelo.
- **"o achado é arquitetural, não dá pra testar, então ignoro"** → achado arquitetural não
  vira teste-red, vira accepted-limit **proposto ao dono**. Enterrar sozinho é proibido.
