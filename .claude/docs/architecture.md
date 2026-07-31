---
generated: 2026-07-31
generated-commit: a57ea6e
project: pedro-plugins
scope:
  - .claude-plugin/marketplace.json
  - scripts/sync-shared.sh
  - _shared/collect_engine.py
  - _shared/green-cache.sh
  - _shared/r8-tiers.md
  - plugins/project-doc/lib/journal.py
  - plugins/project-doc/lib/pattern_check.py
  - plugins/project-doc/lib/organism.py
  - plugins/project-doc/lib/graph_map.py
  - plugins/project-doc/hooks/hooks.json
  - plugins/project-doc/hooks/pretooluse-plan-gate.sh
  - plugins/project-doc/hooks/userpromptsubmit-plan-escape.sh
  - plugins/project-doc/hooks/lib-project-root.sh
  - plugins/intent-guard/lib/ledger.py
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/lib/plan_state.py
  - scripts/hook_contract.py
  - plugins/branches/lib/branch_state.py
  - .claude/hook-contract.baseline.json
  - plugins/bootstrap/config/manifest.json
  - .claude/hooks/release-gate.sh
  - .claude/settings.json
  - plugins/guardrails/hooks/hooks.json
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/bootstrap/output-styles/clean-style.md
  - plugins/bootstrap/lib/conformance.py
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
verified-by:
  - scripts/sync-shared.sh
  - .claude/hooks/release-gate.sh
  - plugins/project-doc/hooks/test_plan_gate.sh
  - plugins/project-doc/lib/test_pattern_check.py
  - plugins/project-doc/lib/test_journal.py
  - plugins/project-doc/lib/test_organism.py
  - plugins/project-doc/lib/test_graph_map.py
  - plugins/project-doc/lib/test_doc_lint.py
  - plugins/intent-guard/lib/test_ledger.py
  - plugins/visual/lib/test_plan_state.py
  - plugins/visual/hooks/test_plan_hooks.sh
  - scripts/test_hook_contract.py
  - plugins/branches/lib/test_branch_state.py
  - plugins/branches/hooks/test_branch_hooks.sh
doc-sig: pedro-plugins/marketplace.json@gen=3.8#db4ecc8f
---

# Arquitetura — pedro-plugins

## 1. Visão geral

Marketplace **privado** de plugins do Claude Code, distribuído por git e catalogado num
único manifesto (`.claude-plugin/marketplace.json`). Não é uma aplicação: é uma
**biblioteca de comportamento** — skills (instruções em Markdown), hooks (shell + Python
stdlib) e alguns motores auxiliares (um daemon Node, um extrator de transcript).

O ciclo de vida é:

```
edita plugins/<nome>/            (skill, hook, lib)
  → bump plugins/<nome>/.claude-plugin/plugin.json .version
  → espelha a mesma version em .claude-plugin/marketplace.json
  → bash scripts/sync-shared.sh   (se tocou _shared/)
  → git commit                    (interceptado por .claude/hooks/release-gate.sh)
  → git push
  → cliente: claude plugin install <nome>@pedro-plugins  /  update
```

Não há build, bundler, lockfile nem CI. O **único passo de "compilação"** é o vendoring
de `_shared/` (§7): copiar arquivos-fonte compartilhados para dentro de cada plugin
consumidor, porque o Claude Code isola plugins na instalação. [confirmado — comentário
de cabeçalho de `scripts/sync-shared.sh`]

## 2. Stack e números (derivados mecanicamente neste run)

Comandos re-executados nesta rodada, na árvore de trabalho sobre `ff32947`:

```bash
ls -1d plugins/*/ | wc -l                       # 19  (diretórios de plugin)
ls -1 plugins/*/.claude-plugin/plugin.json | wc -l   # 19  (manifestos)
ls -1 plugins/*/skills/*/SKILL.md | wc -l       # 21  (skills)
ls -1 plugins/*/hooks/hooks.json | wc -l        # 10  (plugins com hook)
python3 -c "import json;print(len(json.load(open('.claude-plugin/marketplace.json'))['plugins']))"   # 19
```

- **19 plugins distribuídos**, **19 entradas** no marketplace, **21 skills distribuídas**,
  **10 plugins com hooks**, **33 registros de hook** — 32 do tipo `command` + 1 do tipo
  `prompt` [derivado nesta rodada varrendo os 10 `plugins/*/hooks/hooks.json`; bate com
  `python3 scripts/hook_contract.py`, que imprime *"33 registros, 32 scripts distintos"*].
  Eram 32/31 até 2026-07-30; o `+1` é o `Stop` novo do `bootstrap` (§10.2).
- ⚠️ **`ls plugins/` e o catálogo só passaram a bater em `ff32947`.** Antes dele havia
  **20** diretórios para **19** entradas: um plugin feito sob medida para um cliente existia
  no disco, nunca entrou no `marketplace.json` e foi apagado inteiro (4 arquivos, 201 linhas)
  no mesmo commit que preparou o repo para ser presenteado [confirmado — `git show --stat
  ff32947` restrito ao diretório dele lista `.claude-plugin/plugin.json`, o `SKILL.md` da
  skill e os dois `references/*.md`].
  A régua que sobra: **quem manda é `marketplace.json`, não `ls plugins/`** — diretório fora
  do catálogo não é plugin distribuído, é rascunho, e some sem que nada quebre.
- As 21 `SKILL.md` no disco são exatamente as **21 distribuídas**.
- 21 skills em 19 plugins porque **`graphify-guard` não tem `skills/` nenhum** (é 100%
  hook) e **`project-doc` tem quatro** (`project-doc`, `doc-touch`, `start-doc` e
  `design-md`, este último absorvido do plugin homônimo em 2026-07-28).
- Linguagens: Markdown (as skills), Bash (hooks), Python 3 **stdlib-only**, Node stdlib
  (um daemon, `plugins/visual/server/visual_server.mjs`), JS vendorado de terceiro
  (`plugins/archify/skills/archify/renderers/**`).
- Sem package manager: não há `package.json` nem `requirements.txt` na raiz.

## 3. Estrutura de diretórios

```
.claude-plugin/marketplace.json   catálogo único — nome, source, version, tags, category
plugins/<nome>/                   19 dirs, todos catalogados
_shared/                          fonte-da-verdade do código compartilhado (3 arquivos)
scripts/sync-shared.sh            o "build": vendora _shared/ → 6 destinos
scripts/hook_contract.py          mede o contrato dos 33 registros de hook (§11) — usado pelo gate de commit
.claude/                          documentação + estado + gate LOCAL deste repo
  ├── CLAUDE.md                   índice de roteamento (marker project-doc:v2)
  ├── docs/                       architecture · patterns · data-stores · durability · runtime
  ├── hooks/release-gate.sh       gate mecânico de commit deste monorepo (7 checks: A–G)
  ├── hook-contract.baseline.json o retrato do contrato dos hooks  ← VERSIONADO
  ├── settings.json               registra o release-gate como PreToolUse(Bash)
  └── .project-doc/  plans/  ata/  intent/  visual/  qa-loop/  HANDOFF*.md
                                  estado local da máquina — TODOS gitignorados (§3.1)
graphify-out/                     knowledge graph — gitignorado inteiro, regenerável
AGENTS.md · GEMINI.md · .cursorrules · .windsurfrules   ponteiros finos p/ outras IAs
docs/superpowers/                 material de terceiro
pi-plugins/                       ⚠️ CÓPIA OBSOLETA UNTRACKED — não é fonte (§12)
```

### 3.1 O que saiu do controle de versão em `ff32947`

O commit que preparou o repo pra ser presenteado tirou **cinco conjuntos** do índice
(`git rm -r --cached`: os arquivos ficam no disco, só param de ser distribuídos) e os
declarou no `.gitignore` [confirmado — `git check-ignore -v` nesta rodada devolve a linha
exata de cada um, e `git ls-files` sobre os cinco caminhos volta **vazio**]:

```
.gitignore:28  graphify-out/          (grafo inteiro — regenerável com `graphify update`)
.gitignore:35  .claude/.project-doc/  (journal findings.jsonl + ledger.json + backups)
.gitignore:38  .claude/ata/           (memória de sessão: LOG-*.md + manifest-*.json)
.gitignore:39  .claude/plans/         (os planos ticáveis do §11)
.gitignore:40  .claude/HANDOFF*.md    (handoffs de sessão)
```

A linha que separa os dois lados é **"pertence ao repo ou pertence a esta cópia de
trabalho?"**. Journal, ledger, atas, handoffs e planos são o rastro de *quem trabalhou
aqui* — quem clona o marketplace quer os plugins, não o diário de bordo do autor. O grafo
sai pelo outro motivo: é derivado, e cada rodada de doc o reconstrói.

⚠️ **Duas consequências mecânicas, e as duas mudam decisão:**

- **Estado que era garantido pelo `git` passou a depender só do disco.** O `journal.py`
  segue append-only, mas o que o protegia de sumir era o commit. Quem for medir cobertura
  de backup destes cinco caminhos: eles não têm mais a rede do `origin` (ver `durability.md`).
- **O `scope:` dos docs continua apontando pra arquivos versionados**, então nada disso
  entra na conta de staleness — o que sumiu foi a fonte, não a régua.

## 4. Anatomia de um plugin

```
plugins/<nome>/
├── .claude-plugin/plugin.json    OBRIGATÓRIO — name, version, description, author{}, homepage
├── skills/<skill>/SKILL.md       frontmatter YAML: name + description (o gatilho)
│   └── references/*.md           material carregado sob demanda pela skill
├── hooks/hooks.json              OBRIGATÓRIO estar em hooks/ — na raiz é ignorado em silêncio
│   └── *.sh                      os scripts, referenciados por ${CLAUDE_PLUGIN_ROOT}/hooks/…
├── lib/*.py                      motor Python stdlib (project-doc, intent-guard, fallow, handoff, visual, branches, slides, guardrails, bootstrap)
├── config/                       dados versionados (só bootstrap: manifest.json, settings-defaults.json)
├── output-styles/*.md            output style distribuído pelo plugin (só bootstrap: clean-style.md — §10.2)
└── server/                       daemon (só visual: visual_server.mjs, start.sh)
```

`plugin.json` real, copiado de `plugins/project-doc/.claude-plugin/plugin.json`:

```json
{
  "name": "project-doc",
  "version": "3.18.3",
  "description": "…",
  "author": { "name": "pedro-plugins", "email": "tools@viustudio.com.br" },
  "homepage": "https://github.com/pedroberaldo87/pedro-plugins"
}
```

`author` **tem que ser objeto** — string é rejeitada pelo schema e bloqueia o install em
silêncio. [relatado — memory `marketplace-validation-gotchas`; o `plugin.json` lido acima
usa objeto, consistente com o relato]

Todo caminho dentro de `hooks.json` usa `${CLAUDE_PLUGIN_ROOT}` (literal, copiado dos 10
`hooks.json`). O gate LOCAL deste repo, em `.claude/settings.json`, usa a outra variável —
`$CLAUDE_PROJECT_DIR` — porque não é um plugin:

```json
{ "hooks": { "PreToolUse": [ { "matcher": "Bash", "hooks": [
  { "type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/release-gate.sh", "timeout": 60 } ] } ] } }
```

## 5. Catálogo dos 19 plugins distribuídos

Gerado neste run com:

```bash
for p in plugins/*/; do n=$(basename $p);
  v=$(python3 -c "import json;print(json.load(open('$p.claude-plugin/plugin.json'))['version'])");
  sk=$(ls -1d $p/skills/*/ 2>/dev/null | xargs -n1 basename | tr '\n' ',');
  hk=$([ -f "$p/hooks/hooks.json" ] && echo HOOKS || echo -);
  echo "$n v$v [$sk] $hk"; done
```

Saída desta rodada (nome · versão · skills · tem hook) — **19 linhas, e a mesma lista de
nomes que o `marketplace.json` traz, na mesma ordem** [confirmado — comparação mecânica dos
dois lados rodada aqui]:

```
archify         2.11.0  [archify]                                        -
bootstrap        1.8.1  [setup]                                          HOOKS
branches         1.0.1  [branches]                                       HOOKS
context-guard    1.3.2  [setup]                                          HOOKS
fallow           1.0.6  [fallow]                                         -
graphify-guard   1.1.3  [] (sem skills)                                  HOOKS
grill-me         1.0.0  [grill-me]                                       -
grill-with-docs  1.0.0  [grill-with-docs]                                -
guardrails       1.5.1  [setup]                                          HOOKS
handoff          1.8.4  [handoff]                                        HOOKS
improve          1.0.2  [improve]                                        -
intent-guard     0.5.3  [intent-guard]                                   HOOKS
principles       1.0.1  [principles]                                     -
project-doc     3.18.3  [design-md, doc-touch, project-doc, start-doc]   HOOKS
qa-loop          1.7.1  [qa-loop]                                        -
ship             1.3.8  [ship]                                           HOOKS
slides           1.3.1  [slides]                                         -
sovai            1.8.1  [sovai]                                          -
visual           1.8.5  [visual]                                         HOOKS
```

Três subiram em 2026-07-29: `slides` (1.2.0→1.3.0) e `visual` (1.7.4→1.8.0) ganharam `lib/`
com um emissor de HTML (§8.7), e `qa-loop` (1.6.0→1.7.0) passou a **consumir** o emissor do
`visual` em vez de mandar o modelo desenhar o SVG do gráfico de severidade à mão.

Três subiram em 2026-07-30, o `bootstrap` duas vezes:

- `bootstrap` **1.0.2 → 1.3.3** — o maior salto de uma rodada só no repo — ao ganhar três
  componentes novos (`output-styles/clean-style.md`, o `Stop` hook `hooks/stop-prose-ceiling.py`
  e `lib/conformance.py`, descritos em §10.2); e depois **1.3.3 → 1.5.0**, quando os três
  ganharam suíte, o estado passou a honrar `CLAUDE_CONFIG_DIR` e a checagem de hooks
  duplicados passou a contar bloqueio em vez de registro (§10.2).
- `guardrails` **1.3.0 → 1.3.1**, corrigindo o falso-positivo de `CamelCase` do
  `askq_lint.py` que barrou a **primeira** pergunta real do gate (§6); e **1.3.1 → 1.4.0**,
  que deu ao `scope-cop.sh` um terceiro modo, `warn` — antes só havia `deny` e `off`, e o
  gate estava `off` com o plugin habilitado. O comentário do arquivo nomeia o motivo:
  *"o estado meio-ligado (plugin habilitado, gate off) faz parecer que existe trava de
  escopo onde não existe. Aviso é honesto; silêncio não."* [confirmado — `scope-cop.sh`,
  `[ "$MODE" = "warn" ] || MODE="deny"` + o ramo `VERDICT=block && MODE=warn` que emite
  `additionalContext` e zera o `blockstreak`]
- `graphify-guard` **1.0.2 → 1.1.0**, que trocou o `deny` por `additionalContext` no
  caminho padrão do `pretooluse-graphify-guard.sh` (bloqueio volta com `GRAPHIFY_DENY=1`).
  O motivo é a colisão descrita em §10.2: dois plugins negavam a **mesma** primeira busca
  da sessão.

**Cinco plugins subiram na noite de 2026-07-30, em três commits que são o mesmo movimento visto
de ângulos diferentes** — o repo auditando o trabalho do próprio dia, inclusive o de minutos
atrás:

- `32cfe28` — **20 fixes de um loop de QA** sobre o commit anterior (`781e923`), aplicados de
  uma vez: `bootstrap` **1.5.0 → 1.5.1**, `graphify-guard` **1.1.0 → 1.1.1**, `guardrails`
  **1.4.0 → 1.5.0** e `project-doc` **3.18.0 → 3.18.1**. O alvo dominante foi o
  `check_hooks_duplicados` do `conformance.py` (§10.2) — a checagem **nasceu no commit
  anterior e já estava errada em quatro pontos**. O `guardrails` foi o único a subir minor,
  porque o `scope-cop.sh` ganhou comportamento novo, não conserto (§6).
- `a134e9c` — `intent-guard` **0.4.1 → 0.5.0**, a catraca do gate de entrega (§8.5).
- `6c5e1f9` — `intent-guard` **0.5.0 → 0.5.1**, 14 minutos depois: **o conserto anterior quebrou
  a própria suíte, e o verde foi declarado em cima de uma medição furada.** A mensagem do commit
  nomeia as duas causas separadamente, e as duas valem registro porque nenhuma é sobre
  `intent-guard`:
  - **A medição:** `rc=$?` lido **depois de um pipe** devolve o status do *último* comando da
    pipeline (o `tail`), não o do script. O `rc` real era `1` e apareceu como `0`. Erro de shell
    que transforma suíte vermelha em suíte verde — o pior tipo, porque some justamente onde se
    procura evidência.
  - **O defeito:** `test_task_checkpoint.sh` encadeia 3 bloqueios de drift na **mesma** sessão, e
    o teto por sessão novo (§8.5) silencia o 3º. O teste codificava o comportamento antigo. Pior:
    **`/tmp/intent-guard-ckptcap-<sid>` é estado FORA do `$REPO` temporário da suíte**, então
    sobrevivia entre execuções e a segunda rodada reprovava por lixo, não por defeito. O `trap`
    passou a limpá-lo, os casos que medem outra coisa zeram o contador antes, e o teto ganhou
    caso próprio (*"2 avisos saem, o 3º é silêncio"*). [confirmado — suíte executada nesta
    rodada, `rc=0`]
  - ⚠️ **Achado pré-existente, deixado no lugar por cirurgia:** `plugins/intent-guard/hooks/mock_ck_*.sh`
    são **versionados E gerados/apagados pela própria suíte**, então rodar o teste **suja a
    árvore de trabalho**. Neste plugin específico isso é pior do que parece — árvore suja é
    exatamente o que invalida o veredito do `intent-guard` (`tree_hash`, §8.5). O conserto de
    fundo (gerar em `mktemp` em vez de versionar) ficou para o usuário decidir.

**Dois bumps a mais do `bootstrap` depois disso, e os dois são sobre o repo virar presente:**

- `1999796` — `bootstrap` **1.5.1 → 1.6.0**: o output style deixou de se chamar pelo nome do
  dono. O arquivo passou a se chamar `output-styles/clean-style.md`
  (`name: Clean Style`), e o `CLAUDE-global.md` trocou as menções ao nome próprio por "o usuário"
  [confirmado — grep do nome do dono em `plugins/bootstrap/config/CLAUDE-global.md` nesta rodada
  não devolve nada]. É **minor, não patch**, porque o identificador é contrato: máquina com
  o `"outputStyle"` antigo em `settings.json` passa a divergir até o `apply-config.sh` rodar.
- `575c33e` — `bootstrap` **1.6.0 → 1.7.0**: dependência externa de plugin virou categoria
  declarada no manifest e checagem do conformance (§10.3).

**E `ff32947` fechou o movimento — o commit que torna o repo presenteável.** Ele é o único
da série que muda o que o marketplace *é*, não o que ele faz:

- **O plugin sob medida para um cliente foi apagado inteiro** (§2): 4 arquivos, 201 linhas,
  um plugin que nunca esteve no catálogo e que carregava vocabulário daquele projeto.
- **A receita passou a declarar o próprio marketplace** — `pedro-plugins` virou o
  **primeiro** item de `.marketplaces` em `config/manifest.json`, com endereço **HTTPS**
  (`https://github.com/pedroberaldo87/pedro-plugins.git`, não `git@`, porque quem recebe o
  presente não tem chave SSH no repo) e os **19** plugins listados um a um (§10).
- **A desinstalação virou opt-in** no `apply.sh` e o `settings-defaults.json` perdeu o
  `defaultMode: auto` (§10.4). São as duas pontas do mesmo raciocínio: um setup que roda
  de um hook de `SessionStart` não pode remover software nem baixar a guarda de aprovação
  na máquina de outra pessoa.
- **Nome próprio saiu de dentro do produto** — o `bootstrap` já tinha trocado o nome do
  output style em `1999796`; aqui o mesmo tratamento chegou às referências e testes do
  organismo (`plugins/project-doc/`), à `SKILL.md` do `/visual` e aos exemplos do
  `clean-style.md`, que passaram a usar hostname e serviço fictícios.

Todas as 19 versões acima batem com o campo `version` da entrada correspondente em
`.claude-plugin/marketplace.json` [confirmado — comparação mecânica das duas fontes rodada
nesta sessão: **19 de 19 `OK`** (19 `plugin.json` no disco × 19 entradas no
marketplace). É o mesmo par que o gate B do `release-gate.sh`
checa — os seis bumps dos três commits acima aparecem no diff **em pares**, uma linha no
`plugin.json` e outra no `marketplace.json`, nunca sozinhos].

Terceiros vendorados como plugin próprio: `grill-me` e `grill-with-docs` declaram
`author: {name: "Matt Pocock", homepage: "https://github.com/mattpocock/skills"}` no
`marketplace.json`; `archify` é vendorado de `tt-a1i/archify` (MIT) [relatado — mensagem
de commit `36b833cfea9b4a16`].

## 6. Os 10 plugins com hooks — evento por evento

Listagem gerada lendo os 10 `plugins/*/hooks/hooks.json` neste run. **33 entradas de hook**
no total, distribuídas assim (`evento[matcher] → script (timeout)`):

```
branches         (2 eventos, 2 hooks)
  SessionStart[*]                    → sessionstart-branches.sh     (15s)
  PostToolUse[Bash]                  → posttooluse-push-branch.sh   (15s)

bootstrap        (3 eventos, 3 hooks)
  SessionStart[*]                    → session-sync.sh              (sem timeout)
  PostToolUse[Bash]                  → post-plugin-command.sh       (sem timeout)
  Stop[*]                            → stop-prose-ceiling.py        (10s)   ← único hook em Python direto

context-guard    (2 eventos, 2 hooks)
  SessionStart[*]                    → context-guard-reset.sh       (5s)
  PostToolUse[*]                     → context-guard.sh             (5s)

graphify-guard   (2 eventos, 2 hooks)
  SessionStart[*]                    → sessionstart-graphify.sh     (10s)
  PreToolUse[Grep|Glob|Bash]         → pretooluse-graphify-guard.sh (10s)

guardrails       (2 eventos, 4 hooks)
  PostToolUse[Edit|Write]            → lint-and-typecheck.sh        (30s)
  PreToolUse[Agent]                  → hook type "prompt" (LLM classifier inline) (15s)
  PreToolUse[Edit|Write]             → scope-cop.sh                 (25s)
  PreToolUse[AskUserQuestion]        → askq-humanize.sh             (10s)

handoff          (3 eventos, 3 hooks)
  SessionStart[*]                    → sessionstart-ata.sh          (10s)
  PreToolUse[TeamCreate]             → teamcreate-nudge.sh          (10s)
  Stop[*]                            → handoff-completeness-gate.sh (30s)

intent-guard     (4 eventos, 5 hooks)
  UserPromptSubmit[*]                → capture-prompt.sh            (10s)
  PreToolUse[ExitPlanMode]           → plan-gate.sh                 (60s)
  PostToolUse[TaskUpdate]            → task-checkpoint.sh           (60s)
  PostToolUse[Edit|Write|MultiEdit|NotebookEdit] → mark-work.sh     (5s)
  Stop[*]                            → delivery-audit.sh            (60s)

project-doc      (5 eventos, 8 hooks)   ← o maior; ver §6.1
  SessionStart[*]                    → sessionstart-organism.sh     (10s)
  SessionStart[*]                    → sessionstart-doc.sh          (10s)
  PreToolUse[Grep|Glob|Bash|Agent]   → pretooluse-doc-guard.sh      (10s)
  PreToolUse[Edit|Write|MultiEdit]   → pretooluse-organism-gate.sh  (10s)
  PreToolUse[EnterPlanMode|ExitPlanMode] → pretooluse-plan-gate.sh  (10s)
  UserPromptSubmit[*]                → userpromptsubmit-plan-escape.sh (10s)
  PostToolUse[Read]                  → posttooluse-doc-read.sh      (10s)
  Stop[*]                            → stop-doc-touch.sh            (15s)

ship             (1 evento, 1 hook)
  PreToolUse[Bash]                   → pre-deploy-test-check.sh     (120s)

visual           (3 eventos, 3 hooks)
  SessionStart[*]                    → sessionstart-plan.sh         (10s)
  Stop[*]                            → stop-plan-status.sh          (15s)
  PreToolUse[ExitPlanMode]           → pre-exitplan-visualize.sh    (10s)
```

Observações de arquitetura:

- `guardrails` é o único que usa `"type": "prompt"` (um classificador LLM inline no
  `hooks.json`, sem script) — os outros **32** são `"type": "command"`, num total de **33
  registros** [confirmado, derivado nesta rodada varrendo os 10 `plugins/*/hooks/hooks.json`;
  bate com o `scripts/hook_contract.py`, que reporta *"33 registros, 32 scripts distintos"*].
- **O `AskUserQuestion` também é gateável** (`guardrails/hooks/askq-humanize.sh`, 2026-07-30)
  — e agora está **confirmado em runtime**, não mais inferido da doc do harness. O hook grava
  o `tool_input` cru em `~/.claude/guardrails/askq.log` a cada invocação justamente pra fechar
  essa lacuna, e o arquivo existe com **36 linhas** [confirmado — `wc -l
  ~/.claude/guardrails/askq.log` nesta rodada]. A estreia também entregou o primeiro defeito:
  o lint barrou a **primeira pergunta real** porque `\b[A-Z][a-z]+[A-Z][a-z]` casa `"GitHub"`.
  O conserto (v1.3.1) tirou as duas regex de camel e pôs `askq_lint.py:camel_suspeitas()`,
  que acha maiúscula interna e filtra contra o frozenset `NOMES_PROPRIOS` — **um lugar só pra
  afrouxar**. É a mesma classe do falso-positivo de data consertado no commit anterior, e
  apareceu na estreia, que é quando ele custa mais caro: gate que erra na primeira pergunta é
  gate que o usuário desliga na segunda.
- **O `scope-cop.sh` passou a resolver a pasta de estado pela MESMA expressão do verificador
  (guardrails v1.5.0)** — `HOOK_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/guardrails"`, no lugar
  de `$HOME` fixo. O comentário do arquivo nomeia o defeito que isso evita e o classifica: com
  `$HOME` fixo, quem seta `CLAUDE_CONFIG_DIR` teria *"o hook lendo o modo numa pasta e o
  conformance varrendo `**/*.mode` noutra"* — **o gate que o auditor acusa não seria o que o
  hook obedece, e cada lado ficaria coerente sozinho**. É explicitamente *"o mesmo defeito
  silencioso do `bypass.log` do `stop-prose-ceiling`"* (§10.2): a segunda ocorrência da mesma
  classe em dois dias, o que a promove de caso a padrão. Duas travas vieram junto: o
  kill-switch `SCOPE_COP_GATE=0` (propriedade 3 do contrato de hook, §11) avaliado **antes de
  ler o stdin**, e o vocabulário de modo virou **conjunto fechado** — `off` sai, `deny|warn|""`
  seguem, e qualquer outro valor (`"wanr"`, `"ask"`) cai no default **e vira linha
  `MODE:invalido` no log**, porque *"agora que o modo tem 3 estados, errar a grafia entrega o
  gate MAIS severo justamente a quem pediu o mais brando"*. O rastro é escrito **depois** dos
  filtros baratos, de propósito: o matcher é `Edit|Write`, e logar na leitura daria uma linha
  por edição de qualquer arquivo. [confirmado — `scope-cop.sh` nesta rodada; suíte
  `plugins/guardrails/hooks/test_scope_cop.sh`, **15 checks**, executada e verde]
- **Três plugins gateiam o `ExitPlanMode` simultaneamente**: `visual`
  (`pre-exitplan-visualize.sh`), `intent-guard` (`plan-gate.sh`) e `project-doc`
  (`pretooluse-plan-gate.sh`). É defesa em camadas deliberada, mas significa que um plano
  passa por três gates independentes. [confirmado — os três `hooks.json`]
- Diagnóstico de hook: `claude plugin details <nome>@pedro-plugins` mostra `Hooks (N)`.
  É o único jeito de saber se o `hooks.json` foi carregado — `claude plugin validate`
  passa mesmo com o arquivo no lugar errado. [relatado — commit `9389c512eb23addc`,
  causa-raiz "só carrega de `hooks/hooks.json`, não da raiz"]

### 6.1 O gate de plano (project-doc v3.13.0 / gen 3.8) — decisão de arquitetura

Novidade desta rodada: **plano não nasce sem documentação**. Dois hooks novos e um helper
compartilhado implementam isso.

**`pretooluse-plan-gate.sh`** (matcher `EnterPlanMode|ExitPlanMode`). Três saídas,
copiadas do cabeçalho do arquivo:

- **A — projeto sem documentação nenhuma** (nem `CLAUDE.md`, nem `.claude/docs/`):
  `permissionDecision: "deny"` **sempre**, sem cap de avisos, mandando rodar `/start-doc`.
  Comentário literal: *"Decisão de projeto (2026-07-26): nega sempre, a não ser que o usuário
  verbalize que é para ignorar. Por isso NÃO há cap de nudges aqui."*
- **B — tem doc, mas não foi lida nesta sessão**: `deny` com **cap de 3** (`MAX_NUDGES=3`),
  reusando o sentinel `/tmp/claude-doc-guard-${SESSION}-${PHASH}` que o
  `posttooluse-doc-read.sh` escreve. Um `Read` em qualquer `.claude/docs/*.md` libera.
- **C — tem doc e já foi lida**: `exit 0`, silêncio.

Um quarto caminho foi acrescentado por revisão: **`CLAUDE.md` escrito à mão sem
`.claude/docs/`** não cai no caso A (que negaria para sempre com uma mensagem falsa) — vira
caso B com cap, e oferece `/start-doc` + `/project-doc` depois do plano.

**`userpromptsubmit-plan-escape.sh`** (UserPromptSubmit) é o **escape verbal**. Hook não lê
a conversa, então quem ouve a frase é este, e ele grava o sentinel
`/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}` que o gate honra. Tokens literais do
arquivo:

- Libera: `--sem-doc` · `#sem-doc` (garantidos, inequívocos), ou imperativo + doc
  (`ignora a doc`, `pula a documentação`, `segue sem doc`, …).
- Revoga: `--com-doc` · `exige a doc`.
- Três armadilhas travadas por regex (comentadas no arquivo): fronteira de palavra
  obrigatória (`estava sem documentação` não libera), `EXTERNAL_RE` (doc **de terceiro** —
  "ignora a doc DO React" — não libera o gate do projeto), e **ambiguidade resolve pro
  lado seguro** (casou os dois ⇒ não libera; quem quer liberar usa `--sem-doc`).

**`lib-project-root.sh`** existe por um motivo cirúrgico, copiado do arquivo: o `PHASH`
(`cksum` da raiz) é a chave dos sentinels em `/tmp`; se dois hooks derivarem a raiz de
formas diferentes, geram chaves diferentes e o sentinel de um nunca é visto pelo outro —
falha silenciosa. `git rev-parse --show-toplevel` devolve o caminho **físico**
(`/private/var/…`) enquanto `posttooluse-doc-read.sh` recorta a **string** do `file_path`
(`/var/…`); no macOS isso são hashes diferentes. **Regra dura do arquivo: NUNCA
canonicalize** (nada de `git rev-parse`, `realpath`, `pwd -P`).

A ordem de resolução de `project_root()` também é deliberada: 1º ancestral com
`CLAUDE.md`/`.claude/CLAUDE.md` (casa o PHASH de quem escreve o sentinel de leitura), e só
depois marcador de projeto (`.git`, `package.json`, `pyproject.toml`, `Cargo.toml`,
`go.mod`, `.claude`) — que cobre o caso "projeto sem documentação nenhuma", onde só importa
gate e escape concordarem entre si.

**Fail-open só na borda de infra**: sem `jq`, sem raiz resolvível, ou com
`doc-detect.sh` ilegível → `exit 0`. Essa última guarda é um achado de revisão registrado
no arquivo: sem ela, um `chmod 000 doc-detect.sh` fazia um projeto **totalmente
documentado** cair no caso A e ser negado sem cap.

Suite dedicada: `plugins/project-doc/hooks/test_plan_gate.sh`.

## 7. A engine compartilhada vendorada (`_shared/`)

`_shared/` tem exatamente 3 arquivos-fonte. O porquê do vendoring, copiado do cabeçalho de
`scripts/sync-shared.sh`: *"o Claude Code isola plugins na instalação — só `plugins/<nome>/`
vai pro cache, sem variável cross-plugin. O código compartilhado é COPIADO antes do commit
(o 'build' deste monorepo). Fonte-da-verdade = `_shared/`; as cópias nos plugins são
derivadas."*

O mapa `SPECS` (destino::arquivo), copiado literal:

```bash
SPECS=(
  "plugins/handoff/lib::collect_engine.py"
  "plugins/project-doc/lib::collect_engine.py"
  "plugins/sovai/skills/sovai/references::r8-tiers.md"
  "plugins/qa-loop/skills/qa-loop/references::r8-tiers.md"
  "plugins/ship/hooks::green-cache.sh"
  "plugins/qa-loop/lib::green-cache.sh"
)
```

**6 cópias.** É um mapa explícito, não "todos os arquivos em todos os consumidores",
porque consumidores diferentes vendoram arquivos diferentes. `--check` não copia: roda
`cmp -s` e sai 1 com `DRIFT: …` se alguma cópia divergir. Verificado neste run:
`bash scripts/sync-shared.sh --check` → `OK: cópias vendored idênticas a _shared/`.

**`journal.py` NÃO é vendorado** — só `collect_engine.py` é. [confirmado — o `SPECS` acima
e `find plugins -path '*/lib/*.py'`, que mostra `journal.py` apenas em
`plugins/project-doc/lib/`. Confirma o finding `2264721a17ea67c4`, que corrigia um plano
v3.1 errado.]

### 7.1 `collect_engine.py` — a camada de coleta

Extraído de `plugins/handoff/lib/extract_ata.py` (que carregava o schema do `.jsonl`
verificado em dados reais). Concentra tudo que é mecânica de transcript, **sem nenhum
julgamento de LLM**:

- **Resolução de workspace** — `resolve_project_root()` sobe até o 1º ancestral que é
  fronteira de projeto (`.git` **ou** monorepo formal via `WORKSPACE_FILES` =
  `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, `go.work`, ou
  `workspaces` no `package.json`, ou `[workspace]` no `Cargo.toml`). `detect_modules()` +
  `_module_candidates()` varrem `MODULE_CONTAINERS` (`apps`, `packages`, `services`,
  `libs`, `modules`) com poda backend/frontend: `apps/x/{client,server}` vira **1** módulo,
  não 2.
- **`infer_scope()`** — projeto-raiz dominante dos arquivos editados; devolve
  `from_edits` e `project_root_is_boundary` justamente para a skill saber quando o destino
  foi **chutado pelo cwd** e precisa de confirmação humana.
- **Descoberta de transcript** — `discover_transcript()` em 3 níveis: `session_id`
  explícito (determinístico, o nome do `.jsonl` **é** o session_id) → sentinel legado por
  cwd em `/tmp/claude-ata-session-<sha1[:12]>` → `.jsonl` mais recente do cwd.
  `discover_all_transcripts()` faz pré-filtro por nome-de-slug (o encoding cwd→slug é
  determinístico: `[^A-Za-z0-9]` → `-`) e só então abre o arquivo pra confirmar o `cwd`
  real — evita abrir centenas de transcripts à toa.
- **`collect()`** — itens crus por record. Marca `gate: True` só no que é **fala do
  humano** (`user_directive`, `tool_rejection`, `ask_answer`); `plan`, `task`,
  `assistant_text` e `diagram` entram com `gate: False`.
- **`finding_id(text, raw_kind)`** = `sha1(texto completo normalizado + kind)[:16]`. Usa o
  texto **inteiro**, não a âncora truncada de 64 chars — duas falas distintas com o mesmo
  prefixo colidiriam e a 2ª sumiria do journal.

Tolerância a falha é explícita: `read_jsonl` usa `errors="replace"` e pula linha JSON
corrompida sem derrubar a rodada.

### 7.2 `green-cache.sh` — cache de suite verde

Registro compartilhado de "a suite passou verde **neste estado exato da árvore**". Feito
pra ser `source`ado. Consumidores: Fase Gate do `qa-loop` (grava), `ship §2.5`
(consulta+grava) e o hook `pre-deploy-test-check.sh` do `ship`.

Semântica não-negociável (copiada do cabeçalho):

- Fail-open na direção **segura**: qualquer erro → MISS → a suite roda.
- **Gate vermelho NUNCA grava.**
- Chave = tree-hash do git **incluindo untracked**, via `GIT_INDEX_FILE` temporário +
  `read-tree HEAD` + `add -A` + `write-tree`. `git stash create` e `HEAD + diff` não
  servem: ignoram untracked → falso HIT.
- TTL de 24h **por linha** (epoch gravado no registro, não mtime do arquivo — um mark novo
  não pode ressuscitar registro vencido). Prune de arquivos >7d no mark.

Env vars (copiadas literal): `GREEN_SUITE_DIR` (default `$HOME/.claude/green-suite`) e
`GREEN_SUITE_TTL_SECS` (default `86400`). API: `green_tree_hash`, `green_cache_check`,
`green_cache_mark`; scope é `"full"` ou `"app:<nome>"`, e `full` satisfaz qualquer consulta.

### 7.3 `r8-tiers.md` — contrato de tier

Tabela única de "que modelo/effort em cada etapa", compartilhada pelos dois motores
(`/sovai` decompõe→executa→revisa; `/qa-loop` revisa→planeja→conserta). **É tudo Opus** desde
2026-07-26 — o modelo saiu da equação e **só o `effort` varia por etapa**. Os 6 knobs, com os
nomes copiados do arquivo: `decompose_model` (Opus xhigh), `coordinate_model` (Opus high),
`executor_model` (Opus high), `mechanical_model` (Opus medium), `diagnose_model` (Opus
xhigh), `finalize_model` (Opus xhigh). A justificativa está no próprio arquivo: os dois
motores rodam com o humano fora do loop, e execução barata custa mais em retrabalho do que
economiza em token.

Regra de tier por rodada: rodada 1 = `decompose_model`; rodadas 2+ = `coordinate_model` (só
o delta); **CONFIRM e DIAGNOSE são sempre dedicados** e nunca herdam o tier mais barato da
rodada que os disparou.

O cabeçalho do arquivo carrega a trava de vendoring: *"FONTE DA VERDADE: `_shared/r8-tiers.md`
— NÃO editar as cópias vendoradas."*

## 8. Módulos Python e dependências

Inventário mecânico (`find plugins -path '*/lib/*.py'`), **29 arquivos**, agrupados:

```
plugins/project-doc/lib/   collect_engine.py (vendorado) · journal.py · pattern_check.py
                           organism.py · graph_map.py · doc_lint.py
                           + test_{journal,pattern_check,organism,graph_map,doc_lint}.py
plugins/handoff/lib/       collect_engine.py (vendorado) · extract_ata.py
plugins/intent-guard/lib/  ledger.py + test_ledger.py
plugins/fallow/lib/        audit.py · report.py
plugins/visual/lib/        plan_state.py · visual_page.py
                           + test_{plan_state,visual_page}.py
plugins/slides/lib/        md2deck.py + test_md2deck.py
plugins/branches/lib/      branch_state.py + test_branch_state.py
plugins/guardrails/lib/    askq_lint.py + test_askq_lint.py
plugins/bootstrap/lib/     conformance.py + test_conformance.py
```

`plugins/slides/lib/` nasceu em 2026-07-29 — o plugin era 100% skill+assets antes. Os dois
módulos novos (`visual_page.py`, `md2deck.py`) são a mesma decisão de arquitetura, descrita
em §8.7 e §11. `plugins/bootstrap/lib/` nasceu em 2026-07-30 e foi por algumas horas o
**único `lib/` do repo sem `test_*.py` nenhum** — o que importava porque o gate D do
`release-gate.sh` só roda `plugins/<nome>/lib/test_*.py`, então commit que só tocasse o
`bootstrap` não executava teste nenhum. Fechado na v1.4.0 com duas suítes:
`plugins/bootstrap/lib/test_conformance.py` (**8 checks**) e
`plugins/bootstrap/hooks/test_bootstrap_hooks.sh` (**9 checks**). Só a primeira entra no
gate D; a shell segue fora, como todas as suítes shell do repo.
**`test_conformance.py` foi de 8 para 36 checks no `32cfe28`**, e o salto tem causa: o loop
de QA achou **quatro** defeitos no `check_hooks_duplicados` que a suíte de 8 não pegava
(§10.2). Suíte que só cobre o caminho feliz mede a intenção, não o mecanismo.
Hoje são **52 checks em 25 funções `teste_*`** — 39 até a v1.7.0 (os 3 daquele salto vieram
com `check_ferramentas_externas`, num caso só que exercita as duas pontas da regra "só cobra
quem usa": plugin desligado não cobra; ligado sem o binário é acusado, com o comando de
instalar no conserto), e **+13 em `ff32947`**, cobrindo as duas capacidades novas do §10.2 —
ausente × desligado e `check_catalogo`, este último com o caso *"sem catalogo na maquina,
zero desvio de catalogo"*, que é a metade da régua que impede o verificador de acusar quem
só não tem o marketplace instalado. A shell subiu junto: `test_bootstrap_hooks.sh` foi de
**9 para 19 checks**, e o último deles é *"2a rodada e idempotente"*.
[confirmado — as duas executadas nesta rodada: `python3 plugins/bootstrap/lib/test_conformance.py`
→ `52 ok · 0 FAIL`; `bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh` → `19 ok · 0 FAIL`].

**Grafo de import interno** (derivado de `grep` dos imports não-stdlib neste run — todos
lazy, dentro de função, exceto o do `doc_lint`):

```
doc_lint.py      → pattern_check   (import de topo: _extract_frontmatter_and_body, …)
pattern_check.py → organism        (check_organism, _enumerate_scoped_docs, touch_plan, census)
pattern_check.py → journal         (touch_plan lê ledger.load_ledger → last_commit)
journal.py       → collect_engine  (try/except ImportError → HAVE_ENGINE, degrada sem tier 4)
organism.py      → yaml (PyYAML)   (try/except ImportError → mini_yaml stdlib)
```

Os dois `try/except ImportError` são a mesma decisão de arquitetura: **stdlib-puro é
requisito, não preferência**. `journal.py` redefine `anchor_of`/`finding_id` idênticos ao
`collect_engine` quando ele falta (com comentário explícito de que qualquer divergência
re-chavearia o journal). `organism.py` traz um parser YAML de subconjunto testado **por
paridade com PyYAML** — e que **levanta erro** em construção fora do subconjunto, nunca
produz parse errado silencioso.

### 8.1 `journal.py` — journal append-only + scrubber

- **Estado versionado**: `.claude/.project-doc/findings.jsonl` (eventos) +
  `ledger.json` (`mined_sessions` como `{sid: mtime}`, `last_commit`, `distilled_hashes`).
- **`fold(events)`** é o estado vivo: `discovered` cria, `invalidated` mata (sem apagar),
  `curated` sobrepõe o texto. Um id invalidado **permanece morto** mesmo que reapareça num
  `discovered` posterior.
- **Delta de duas direções**: forward = sessões novas/que cresceram + commits novos;
  backward = `git diff` (working tree ∪ staged ∪ `last_commit..HEAD`) cruzado com as
  `anchors` → marca `stale`. **O lib nunca auto-invalida** — re-validação é julgamento do
  agente.
- **`self_path_match()`** trava o falso-positivo do monorepo: basename puro sem `/` só casa
  se **exatamente 1** arquivo mudado tem aquele nome (senão `config.json` marcaria stale
  qualquer homônimo).
- **Robustez de git**: `_commit_reachable()` — um rebase/amend órfã o `last_commit` e
  `git log orfão..HEAD` sai 128, perdendo todos os commits; o código trata como cold-start.
- **Scrubber em 4 camadas**, a barreira entre conversa-verbatim e git: (1) estruturado
  (PEM → connection string → JWT → prefixos de provider), (2) `chave=valor` de uma linha +
  pares JSON aninhados, (3) prosa (palavra-sinal + token de alta entropia), (4) na dúvida,
  marca `‹revisar?›` — preserva, não vaza. Política: **nomes e contexto SIM, valores NÃO**;
  host/IP/porta/path/sha/uuid preservados. O valor vai pro cofre e o doc fica com
  `‹cofre:LABEL:hash8›`.
- **Cofre**: `PROJECT_DOC_COFRE_DIR` (override explícito) > iCloud
  (`~/Library/Mobile Documents/com~apple~CloudDocs/Cofre`) > fallback local
  `.claude/secrets/_local_cofre`. `ensure_gitignore()` roda **antes** da escrita, porque no
  fallback o cofre cai dentro do repo.

### 8.2 `pattern_check.py` — o contrato de "doc no padrão"

`CURRENT_GEN = "3.8"` (copiado literal). Cinco invariantes de disco: (a) markers
`<!-- project-doc:v2 gen=X -->` e `:end` no `CLAUDE.md`, (b) frontmatter YAML em todo
`.claude/docs/*.md`, (c) `findings.jsonl` existe, (d) linha `doc-sig:` no frontmatter,
(e) `gen_found == CURRENT_GEN`.

`sig(docfile)` = `"<project>/<scope_basename>@gen=<CURRENT_GEN>#<sha256(body)[:8]>"`. **O
hash8 é do corpo e independe da gen; só o rótulo `@gen=` vem do código** — daí a armadilha
já registrada: `--sig` sempre carimba o `CURRENT_GEN` do código, então quem tem "gen não
bumpa" como invariante (`/doc-touch`) precisa reimpor a gen antes de gravar. [confirmado —
`sig()` usa `CURRENT_GEN` incondicionalmente; casa com o gotcha `49939599bbbce05d`]

Camadas por cima do contrato:

- **`scope_staleness()`** — ternário `fresh|stale|unknown`, **nunca finge fresco**. Usa
  `generated-commit:` (precisão de commit) quando resolvível, senão a janela por
  `generated:`. `git log` com `returncode != 0` devolve `None` (unknown), não set vazio.
- **`docs_for_paths()` / `touch_plan()`** — o **índice inverso do scope**, base do
  `/doc-touch`: dado o diff, quais docs cobrem quais arquivos. Inclui `already_current`
  (doc mais novo que os arquivos que o afetam), `seam_review` (costuras tocadas →
  blast-radius), `unscoped_new`, `dead_scope` e **`last_full_age_days`**.
  - **`last_full_age_days` (v3.18.0)** é o que dá autonomia de touch-vs-FULL a quem chama.
    O FULL é o **único** que avança `ledger.last_commit` (o touch é read-only nele), então
    a data desse commit *é* a data do último FULL. `>30` ou `null` ⇒ o `doc-touch` escala
    pro FULL no **passo 1**, antes de re-projetar nada; em headless (`/sovai`) escala e
    segue, sem perguntar. **Um sinal só, de propósito** — os outros dois candidatos foram
    testados e reprovados: `unscoped_new` exige por definição que o arquivo esteja num dir
    **já coberto** (escalaria a cada `test_*` novo), e "arquivo fora do scope de todo doc"
    é alto num repo **saudável** (medido: 41 de 79 arquivos mudados aqui, com o touch sendo
    a escolha certa). Mecanizar "isso é estrutural?" é o precedente do
    `commits_after > 0 or edits_after >= 3`.
  - **`unscoped_new` respeita `verified-by:` (v3.18.0)** — antes só enxergava `scope:` e por
    isso acusava **toda** suíte do repo (suíte pertence a `verified-by:`; botá-la no `scope`
    faria o doc virar stale a cada edição de teste). Eram **11 de 11** acusações falsas.
    `_scope_entries()` ganhou o parâmetro `field` para que o consumidor **não reimplemente**
    o split + fallback de módulo — foi essa reimplementação que fez o `project_staleness`
    derivar na v3.16.0.
- **`project_staleness()`** — a versão barata que **os hooks** consomem; roda **recursivo**
  para pegar `.claude/docs/modules/`. **Reescrita na v3.16.0 (2026-07-29)** porque tinha
  derivado da irmã caprichada: agregava a **data mais antiga** e a **união** dos scopes,
  ignorando `generated-commit`, e casava por interseção crua de strings. Hoje agrupa por
  **base de comparação** — um bucket por `generated-commit` distinto (1 git call cada; na
  prática 1, porque o touch carimba todos juntos), mais um bucket pela janela de data pros
  docs sem carimbo resolvível — e casa com `_scope_match`, igual ao por-doc. Continua
  barata e continua fail-LOUD: git com erro ⇒ `unknown`, nunca `fresh`. O que o defeito
  causava e por que ele é uma classe, não um caso, está em `patterns.md §7 → project-doc`.
- **`restamp()` / `doc_set_gen()`** (v3.17.0) — o carimbo do `/doc-touch` virou verbo:
  `generated`, `generated-commit` e `doc-sig` de uma vez, com a gen lida do **doc-set**
  (marker do `CLAUDE.md`), não o `CURRENT_GEN` do código — o `--sig` cru bumpa a gen por
  construção e violava o invariante "gen não bumpa". Pula doc autoral e arquivo sem
  frontmatter; sem HEAD resolvível **não escreve nada** (carimbo parcial é pior que
  carimbo velho). Existe porque **um doc não consegue citar o commit que o contém**: o
  rito é commit do conteúdo → `restamp` → commit do carimbo, e este repo o fez à mão 3×
  antes de automatizar.
- **`census()` / `conformance_plan()`** — delegam a classificação ao `organism.py`.

### 8.3 `organism.py` — costuras de monorepo

Lê o dado **curado** `.claude/organism.yaml` e responde perguntas: `match <abs_path>` (que
costuras o path toca + blast-radius), `marker`, `brief`, `census`, `dirty`, `verify-cite`.

O princípio, copiado do cabeçalho: **"SISTEMA afirma, agente refuta"** — este módulo só
produz a afirmação; a refutação do agente é validada por `verify_cite()`, que exige
`arquivo:linha` real cuja linha contenha um símbolo daquela costura. É barreira contra
citação-fantasma, não contra refutação sofisticada-errada (teto assumido do mecanismo).

`census()` classifica toda doc project-doc do repo em 4 classes: `canonical`,
`legacy-archived`, `pending-migration` (doc de módulo listado **sem** contraparte em
`modules/{m}/` — a migrar, **nunca arquivar cego**) e `orphan`. `CLAUDE.md` **sem** marker
= autoral → fora da jurisdição. `CENSUS_PRUNE` (incluindo `.project-doc`, `worktrees`,
`_repos-antigos`) é load-bearing: um furo faz o agente ler doc velha com carimbo de fresco.

`dirty_modules_from_changes()` é o núcleo puro do modo lazy: dirty = módulos cujos arquivos
mudaram **∪** blast-radius das costuras tocadas. Só regenera módulos reais (uma ponta pode
nomear um conceito curado que não é diretório).

### 8.4 `graph_map.py` — o grafo destilado pra casca

`graphify-out/graph.json` tem milhares de nós — grande demais pra casca engolir inline.
Este módulo destila num JSON compacto: `files` (ranqueados por fan-in), `god_nodes`,
`communities` (nomeadas, dedupadas) e `hyperedges` (≥ `hyper_min`, default 0.85).

Decisão técnica central: **fan-in semântico exclui `STRUCTURAL_RELATIONS = {"contains",
"defines", "method"}`**, porque `contains` (arquivo-contém-símbolo) é ~85% das arestas e
vira ruído no ranking de importância. Sem grafo devolve `{"available": false}` e a casca
degrada. `GENERIC_COMMUNITY_MIN = 4`: um nome compartilhado por ≥4 comunidades é metadado
repetido, não módulo.

### 8.5 `ledger.py` (intent-guard) — caderno de pedidos

Mesma forma arquitetural do `journal.py` — eventos append-only + `fold` —, mas para
pedidos verbatim: `raw` → `classify` → `verdict` → `baixa`. Diferenças que valem registro:

- **Lock `fcntl.flock`** em `locked()`, porque hooks concorrentes chamavam `record-raw`
  e geravam `r-N`/`p-N` duplicados.
- **`fold(evs, session)` filtra por sessão** os `pending`/`live`. Sem isso, sessões
  paralelas no mesmo projeto compartilham a lista de vivos e o gate de uma cobra os pedidos
  da outra (bug real observado).
- **`tree_hash()`** usa a técnica do green-cache, mas com `EXEC_ARTIFACTS` excluídos
  (`__pycache__`, `node_modules`, `.pytest_cache`, `*.log`, …) — o prompt canônico obriga o
  auditor a **executar** o código, e sem a exclusão a auditoria mudava a árvore e o veredito
  nascia vencido. **Na v0.5.0 a lista deixou de ser só de Python** e ganhou `dist`, `build`,
  `.vite`, `.next`, `.turbo`, `playwright-report`, `test-results` e `coverage`. É preventivo e
  o comentário diz por quê: hoje esses caminhos são quase sempre gitignorados (*"medido em
  projeto Node real: nao mudam o hash"*), mas **projeto que VERSIONA build cairia no mesmo
  defeito** — a exclusão é da classe "artefato de execução", e a classe é maior que o Python.
- **A catraca do gate de entrega, e o sidecar `.escopo` (v0.5.0).** É o defeito mais caro que o
  plugin já teve, e a forma do conserto é a decisão de arquitetura. O gate bloqueia listando os
  pedidos vivos **daquele instante**, mas o consumo do veredito só acontece no `Stop` seguinte —
  e cada mensagem do usuário no meio vira pedido vivo novo. Como `audit_check` cobrava veredito de
  **todo** vivo no instante da leitura, **o veredito nascia impossível de aprovar e o buraco só
  crescia**. Medido neste repo, ao vivo: a auditoria mais recente
  (`.claude/intent/audit-1785436084.json`) julgou **1** pedido (`p-62`) e é reprovada com **34**
  linhas `"pedido vivo … sem veredito"`, de `p-12` a `p-68` — nenhum deles foi encarregado a
  nenhum auditor. O conserto: `delivery-audit.sh` grava `<arquivo>.escopo` (um array JSON de
  ids) no **instante do bloqueio**, e `audit_check` valida apenas `perguntados ∩ vivos`.
  - **Por que sidecar e não campo dentro do JSON**, copiado do hook: o arquivo de auditoria
    *"ainda não existe quando o gate roda"* — quem o escreve é o auditor. **Depender do modelo
    ecoar a lista seria trocar mecanismo por exortação**, que é a mesma escolha do `plan_state`
    (o programa emite, o modelo não redigita).
  - **Compatibilidade por ausência:** sem sidecar, `alvo` continua sendo *todos* os vivos —
    o comportamento de antes. Nada retroage e nada quebra.
  - **O veredito não vence mais com o conserto que ele mesmo pediu.** Antes, `tree_hash`
    diferente ⇒ *"veredito vencido"*, então agir sobre um achado da própria auditoria matava o
    veredito que acabara de chegar. Hoje `_arquivos_citados()` extrai da evidência os caminhos
    que existem no repo, `_arquivos_mexidos()` faz `git diff` entre os dois trees, e só reprova
    se houver interseção. **`_arquivos_mexidos()` devolve `None` quando não dá pra saber** (hash
    órfão, sem git) e o chamador trata `None` como reprova — a mesma regra do `scope_staleness`:
    não-saber nunca vira aprovação.
  - **Teto por sessão no `task-checkpoint.sh`**, além do teto por task que já existia. O teto por
    task não segurava nada, porque cada task nova ganhava aviso limpo e a mesma acusação (que
    era **falsa** — o pedido tinha sido entregue e auditado, o veredito é que nunca foi
    transcrito) voltava pelo resto da sessão. `/tmp/intent-guard-ckptcap-${SID}`, teto 2 — **o
    mesmo mecanismo e o mesmo número do `delivery-audit.sh`, de propósito, "pra não inventar um
    segundo padrão"**. O motivo escrito no arquivo é o princípio: *"Guarda que repete acusação
    falsa ensina a ignorar guarda, e aí ele não serve nem quando está certo."*
    ⚠️ **Foi o único item da v0.5.0 que quebrou algo:** a suíte `test_task_checkpoint.sh` encadeia
    3 bloqueios na mesma sessão e codificava o comportamento sem teto. Consertada na v0.5.1
    (§5), com caso próprio para o teto e limpeza do contador no `trap`.
  - **O que NÃO foi feito, e é decisão:** nenhuma baixa retroativa dos vivos acumulados. Dar
    baixa em massa seria declarar entregue o que nenhum auditor julgou — o oposto do propósito
    do guarda. Eles drenam sozinhos no próximo bloqueio.
  [confirmado — `audit-check` executado nesta rodada nos dois caminhos: com um `.escopo` de teste
  contendo `["p-62"]` o mesmo arquivo devolve `{"ok": true, "why": []}`; sem o sidecar, `ok=false`
  com 34 reprovações. Suíte `test_ledger.py` verde, com os casos novos "pedido que chegou depois",
  "compatibilidade sem sidecar" e "o conserto que se autodestrói"]
- **Escada de custo** (`cmd_verify`): antes de gastar um agente, resolve por código os
  pedidos que têm receita mecânica. `RECIPES = {"git_synced": recipe_git_synced}` — catálogo
  **fechado**. Comentário de segurança literal: *"`verify` é uma ESCOLHA de catálogo, nunca
  um comando. O juiz é um LLM — deixá-lo escrever shell que o hook executa seria injeção de
  comando por design."* Qualquer valor fora do catálogo vira `None`.
- **Estado**: `.claude/intent/` ignorado via `.git/info/exclude` (ignore **local**, nunca
  toca arquivo versionado do repo), resolvido por `git rev-parse --git-path info/exclude`
  porque num worktree `.git` é arquivo, não diretório.

### 8.6 `visual_server.mjs` — o único daemon

Servidor HTTP local, **zero deps externas** (Node stdlib). Bind **só em `127.0.0.1`**, porta
`CLAUDE_VISUAL_PORT` (default `7755`). Escreve o estado vindo do browser em
`~/.claude/visual-state/<session>.json` + um ponteiro `latest.json` para o Claude ler sem
saber o token. Guardas: `MAX_BODY_SIZE` 256 KB, `SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/`,
auto-shutdown por ociosidade em 30 min, e `EADDRINUSE` → `process.exit(0)` (outra instância
já roda; `start.sh` trata como sucesso). `Access-Control-Allow-Origin: *` é deliberado e
comentado: só escuta em loopback, e `file://` aparece como origin `null`.

### 8.7 `visual_page.py` e `md2deck.py` — o HTML sai de programa, não de token

Os dois módulos mais novos (2026-07-29) resolvem o mesmo problema em dois plugins, e o
número que os motivou foi medido no repo: as páginas do `/visual` que **não** eram plano
vinham digitadas pelo modelo, com 20 a 31 KB de HTML de corpo por página. A página de
plano, emitida por `plan_state.py page`, gastava zero.

**`plugins/visual/lib/visual_page.py`** — `build --spec <json>` + `schema`. Dez tipos de
bloco (`text`, `bullets`, `evidencia`, `artefato`, `callout`, `tri`, `item`, `decision`,
`chart`, `raw_html`); `validate()` devolve **todos** os erros de forma de uma vez, como o
`plan_state.validate`. Duas decisões carregam o módulo:

- **As caixas canônicas são EXTRAÍDAS do `template.html`**, por `extract_block()`, que acha
  o `<div class="…">` e balanceia `<div>`/`</div>`. Não são redigitadas ali — e o motivo
  está registrado: havia uma cópia do bloco `.decisions-box` colada em prosa na SKILL.md
  que **já tinha divergido** do template (faltava o `.live-indicator`), então quem a
  seguisse entregava página sem o selo de live-sync. Classe ausente do template ⇒
  `SpecError`, nunca página incompleta.
- **O que era prosa virou invariante:** nenhum rádio nasce `checked`, `name` único por item
  numerado pelo programa, `.decisions-box` sai sempre que há `decision` e `.feedback-box`
  sempre que há `item`, ordem fixa entre as duas, 3 opções por decisão com a 3ª sempre a
  `.opt-custom`, escape de todo texto. E recusa (`exit 2`, sem escrever): decisão/veredito
  **sem nenhuma prova na página**, evidência vazia, decisão com 2 ou 4 opções, `tri`
  incompleto.

O bloco `chart` desenha as barras empilhadas P0-P3 por rodada + a linha de severidade real
(P0+P1) do relatório do `/qa-loop`: coordenada de barra é aritmética, e barra fora de escala
não dá erro — dá a conclusão errada sobre retornos decrescentes. Um contrato fica acoplado
ao JS do template: a opção usa `<h3>`, porque `getDecisionSelections()` lê o título da
escolha em `h3`; emitir `h4` faria a escolha do usuário chegar como `"Selecionado"`.

**`plugins/slides/lib/md2deck.py`** — compilador do **modo A (transcrição)** do `/slides`.
A regra de ouro daquele modo é "use o texto literal do `.md`, nunca invente"; era tradução
mecânica feita por inferência, com o `check_fidelity.py` conferindo **depois**. Agora o
texto de corpo sai dos tokens do `.md` sem passar por geração: as únicas strings que o
programa cria são enumeradores (`01`, `02`) e o eyebrow derivado dos headings — exatamente
o que o checker isenta. `--plan` imprime o storyboard em JSON (heading, componente, itens,
quantos slides aquele heading gera) e `--anota` recebe o que **é** julgamento: componente
por slide e ponto de quebra por densidade. Nove componentes implementados (`cover`,
`divider`, `numlist`, `idx`, `feats`, `statement`, `metric`, `pull`, `cols`); componente
fora da lista é recusado com a lista inteira. O modo B (explicador) segue autoral — o
conteúdo lá **é** o produto do julgamento.

Suites: `test_visual_page.py` (60 checks) e `test_md2deck.py` (50 checks, que rodam o
`check_fidelity.py` real nos dois sentidos). O gotcha que as duas passaram a cobrir está em
`patterns.md §6` — **teste de presença não é teste de efeito**.

## 9. O knowledge graph como mapa de arquitetura

Números do mapa destilado nesta rodada (`.claude/.project-doc/.run-graphmap.json`,
produzido por `graph_map.py` sobre `graphify-out/graph.json`):

```
nodes 6497 · links 7400 · hyperedges 6 · comunidades nomeadas 30 · god nodes 60
```

Vs. a rodada anterior (`7219 · 8167 · 12`): a queda de nós/arestas é o **`pi-plugins/` saindo
do corpus** (gitignorado em 2026-07-28, §12.2) — some a cópia duplicada, não código real. Os
hyperedges caem de 12 para 6 por **filtro do `build_map()`**, não por perda: o `graph.json` cru
segue com 12.

**Top fan-in semântico por arquivo** — o ranking abaixo é da rodada anterior, quando
`pi-plugins/` ainda entrava no corpus e suas entradas eram ruído a descartar (§12.2). Hoje esse
ruído **não existe mais**, então o ranking está desatualizado *para melhor*: qualquer entrada de
`pi-plugins/` que apareça aqui já não é produzida pelo grafo atual.

```
plugins/archify/skills/archify/renderers/shared/geometry.mjs   227
plugins/project-doc/lib/journal.py                              89
plugins/archify/skills/archify/renderers/shared/cli.mjs         86
plugins/archify/skills/archify/renderers/shared/utils.mjs       73
plugins/project-doc/lib/pattern_check.py                        66
plugins/intent-guard/lib/ledger.py                              46
plugins/project-doc/lib/organism.py                             43
_shared/collect_engine.py                                       42   (= as 4 cópias vendoradas, 42 cada)
plugins/fallow/lib/audit.py                                     37
```

Leitura: o repo tem **dois centros de gravidade** — os renderers do `archify` (JS
vendorado de terceiro, altíssimo fan-in interno) e o `lib/` do `project-doc`. O
`collect_engine.py` aparece 5× com fan-in idêntico (42) porque **é o vendoring**: fonte +
4 cópias. É a assinatura do build no grafo.

**God nodes** (fan-in semântico ≥3, os 60 primeiros). Em `plugins/`, os de topo são
`asArray()` (32) e `labelPoint()`/`isFinitePoint()`/`cleanCrossingProblems()` em
`geometry.mjs`, `esc()` (26) e `textUnits()` (17) em `utils.mjs`, `animateAttr()` (15) e
`focusEdgeAttrs()` (14) em `cli.mjs`, `check()` (15) em `test_journal.py`, `fold()` (7) em
`journal.py`, `append()` (7) em `ledger.py`. Os `check()` de teste no topo são artefato do
estilo de suite (um helper por arquivo), não acoplamento real.

**Comunidades nomeadas** — 30 no total; as maiores por tamanho, com o arquivo-âncora:

```
67  Hook Config (SessionStart/PostToolUse)   plugins/context-guard/hooks/hooks.json
55  Slides Deck Generation
54  Fallow Report Generation                 plugins/project-doc/lib/journal.py
53  Slides Fidelity Checker                  slides/.../check_provenance.py, check_fidelity.py
38  Documentation System (CLAUDE.md)         .claude/docs/*, .claude/CLAUDE.md, .github/copilot-instructions.md
17  Marketplace Registry & Plugin Config
 9  Context-Guard & Handoff Bridge           context-guard.sh, context-guard-writer.sh, handoff/plugin.json
 9  Fallow Liveness & Convergence            fallow/lib/{audit,report}.py
 9  Graphify-Guard Net                       graphify-detect.sh, pretooluse-graphify-guard.sh
 8  Marketplace Manifest Metadata            .claude-plugin/marketplace.json
 8  Project-Doc Generator
 7  Grill Design Review · 7 Iterate Convergence Loop
 6  Bootstrap & Marketplace Sync · 6 Hook Config (PreToolUse) · 6 PreToolUse Hooks & Visual Daemon
```

Duas comunidades têm rótulo enganoso — "Fallow Report Generation" ancorada em
`journal.py` e "Visual Auto-Mode Config" ancorada em `collect_engine.py`. É **mapa, não
verdade**: o rótulo é gerado por LLM sobre um cluster estrutural. Confirme no código.
Uma comunidade nomeada (`QA & Rev6 Parallel Review`, arquivo `plugins/qa/skills/qa/SKILL.md`)
aponta para um plugin que **não existe mais** — `qa` foi substituído por `qa-loop`
[confirmado — `ls plugins/` não tem `qa`].

**Hyperedges de alta confiança** (workflows multi-nó, `confidence_score ≥ 0.85`) — os 6
que o mapa reteve:

```
0.95  Bootstrap Sync Cycle (pull → apply → snapshot → commit/push)
0.95  Cross-Tool Doc Routing to CLAUDE.md   (.claude/CLAUDE.md, AGENTS.md, GEMINI.md, copilot-instructions.md)
0.95  Context-Guard StatusLine/State-File Bridge   (context-guard-writer.sh)
0.85  visual live-sync pipeline: skill, daemon starter, daemon, gate hook
0.85  slides deck generation: skill, template, layout map, theme, fidelity check
0.85  ship test gate: skill flow, hooks config, enforcing hook script
```

Esses seis são a melhor descrição curta da arquitetura de comportamento do repo: cada um é
um **circuito completo** skill ↔ hook ↔ artefato, que nenhuma leitura de arquivo isolado
mostra.

## 10. A receita de instalação — o manifest do bootstrap

`plugins/bootstrap/config/manifest.json` (`version: 1`) tem hoje **5 chaves de topo** —
`version`, `description`, `marketplaces`, `skills` e `ferramentas_externas` — e só as três
primeiras são geradas pelo `snapshot.sh`; as outras duas são mantidas à mão (§10.1, §10.3).
Declara **8 marketplaces** que o `session-sync.sh` sincroniza, com **48 entradas de plugin
no total — 31 ligadas e 17 desligadas**. Estado derivado nesta rodada lendo o JSON:

```
pedro-plugins             19 plugins   ← O PRÓPRIO REPO (novo em ff32947), 17 on / 2 off
                                       archify · bootstrap · branches · context-guard
                                       fallow · graphify-guard(off) · grill-me
                                       grill-with-docs · guardrails · handoff · improve
                                       intent-guard(off) · principles · project-doc
                                       qa-loop · ship · slides · sovai · visual
agent-browser              1 plugin    agent-browser
claude-hud                 1 plugin    claude-hud
claude-plugins-official   14 plugins   claude-md-management(off) · code-review · code-simplifier
                                       context7 · explanatory-output-style(off) · figma
                                       frontend-design · github(off) · playwright
                                       security-guidance(off) · skill-creator
                                       sonatype-guide(off) · superpowers · swift-lsp
obsidian-skills            1 plugin    obsidian
openai-codex               1 plugin    codex
ponytail                   1 plugin    ponytail
voltagent-subagents       10 plugins   voltagent-{biz,core-dev,data-ai,dev-exp,domains,
                                       infra,lang,meta,qa-sec,research} — TODOS off
```

**A entrada `pedro-plugins` é a mudança estrutural de `ff32947`, não mais uma linha.** Até
ali o manifest era só o retrato dos **terceiros**: quem instalava o `bootstrap` ganhava
`superpowers`, `codex` e `ponytail`, e tinha que instalar à mão, um por um, os 19 plugins
do repo em que o `bootstrap` mora. Três detalhes da entrada carregam decisão:

- **`source` é HTTPS, não `git@`** (`https://github.com/pedroberaldo87/pedro-plugins.git`).
  A forma SSH exige chave cadastrada no repo — funciona pro dono e falha em silêncio pra
  qualquer outra pessoa, que é exatamente quem a receita precisa atender.
- **Dois nascem `enabled: false`** — `graphify-guard` e `intent-guard`. Não é opinião sobre
  qualidade: o `graphify-guard` depende de um binário externo que o marketplace não instala
  (§10.3) e o `intent-guard` se descreve como `EXPERIMENTAL` na própria entrada do catálogo.
  Pela regra do parágrafo seguinte, isso **instala e desliga** — ligar depois é um comando
  (`claude plugin enable <nome>@pedro-plugins`), não uma reinstalação.
- **A promessa vestigial da `description` virou verdade.** O texto *"The pedro-plugins entry
  is manually maintained and preserved across snapshots"* estava no arquivo desde antes, sem
  entrada nenhuma pra sustentá-la (era a divergência 5 do §12). Agora ela existe, e sobrevive
  ao `snapshot.sh` porque o filtro do §10.1 tira `pedro-plugins` do bloco auto-gerado e
  recopia a entrada escrita à mão.

⚠️ **O manifest é receita, não espelho da máquina — e as duas coisas divergem aqui agora.**
O `conformance.py` desta máquina acusa `graphify-guard` e `intent-guard` **ligados** contra
um manifest que os quer desligados [confirmado — `python3 plugins/bootstrap/lib/conformance.py`
nesta rodada, exit `1`, desvios 1 e 2 na área `plugins`]. É o comportamento correto do
verificador: ele mostra o desvio e não conserta. Quem quiser a máquina igual à receita roda
o `disable`; quem quiser a receita igual à máquina edita o manifest.

**`enabled: false` não é ausência.** A entrada continua no manifest — o `bootstrap:setup`
sabe que aquele plugin existe e foi deliberadamente desligado — e só some do
`enabledPlugins`. Os 10 `voltagent-*` e o `explanatory-output-style` passaram a `false` no
commit `fe4f832` (*"chore(plugins): claude plugin disable @ host-a"*, 2026-07-30),
que é **snapshot automático**: o que ele registra é o `claude plugin disable` que alguém
rodou na máquina, não uma edição do arquivo. O motivo não está escrito em lugar nenhum do
repo [não verificado — só a data, que é a mesma do output style de §10.2 (então ainda com o
nome antigo), poucos commits antes dele].

### ✅ 10.1 · O manifest que ENCOLHIA sozinho — causa achada e fechada (v1.4.1)

O defeito registrado nas rodadas anteriores: commits gerados pelo próprio `session-sync.sh`
e já pushados pro origin apagavam entradas de plugin do manifest (`2bbc4ac`: 22 → 13, com
dois marketplaces declarados e **vazios**) e depois as traziam de volta (`fe4f832`: 13 → 29)
sem ninguém editar o arquivo. Não era outra máquina sobrescrevendo a verdade: era o snapshot
desta máquina sub-reportando o que ela própria tem.

**A causa foi medida, não inferida, e é externa ao repo: `claude plugin list` devolve saída
incompleta de vez em quando.** Cinco chamadas seguidas na mesma máquina deram 49, 15, 49, 49
e 49 linhas `Status:` (4790 bytes vs 1537 na truncada). O snapshot gravava fielmente a
amostra da vez — daí encolher e voltar sozinho. [relatado — mensagem do commit `222aca5`, que
carrega a medição; o comentário de `hooks/lib/snapshot.sh` repete a mesma medição no código]

O conserto está no `snapshot.sh` e são **duas guardas de escopos diferentes**:

1. **A união com o manifest anterior virou ADITIVA** — entrada nova entra, o `enabled` da
   amostra vence, **entrada ausente FICA** (`group_by(.name) | map(if length > 1 then .[1]
   else .[0] end)`). Como não dá pra distinguir "desinstalado" de "a CLI não listou desta
   vez", desinstalar de verdade passa a ser **edição explícita do manifest**. Se o total
   encolher mesmo assim, sai `log "warning: manifest encolheu $VELHO_N -> $NOVO_N"`.
2. **`PRESERVED_KEYS` inverteu a lógica e virou `GENERATED_KEYS`** (`["version",
   "description","marketplaces"]`): a lista passou a ser do que o script **gera**, e tudo que
   não está nela é preservado. A versão anterior listava o que salvar (`jq '{skills}'`) e
   por isso consertava o caso deixando a classe viva. O comentário do arquivo nomeia a
   diferença: *"chave nova mantida à mão sobrevive sem ninguém precisar lembrar de vir aqui;
   só quem passa a GERAR uma chave nova mexe nesta lista."*
   ✅ **A inversão foi exercitada de verdade em `575c33e`:** `ferramentas_externas` (§10.3)
   entrou no manifest **sem uma linha de mudança no `snapshot.sh`**, e sobrevive porque não
   está em `GENERATED_KEYS`. Com a lógica antiga (lista do que salvar) seria a terceira chave
   a sumir sozinha no primeiro `SessionStart`. [confirmado — `GENERATED_KEYS` lido nesta
   rodada continua `["version","description","marketplaces"]`, e o diff de `575c33e` não toca
   `snapshot.sh`]

O próprio defeito comeu duas entradas dentro desta janela: `352e8d5` levou o manifest de
**29 → 27** (sumiram `voltagent-qa-sec` e `voltagent-research`) e `222aca5` as devolveu junto
com o conserto. As entradas de terceiro seguem **29** desde então; o total do arquivo hoje é
**48**, porque `ff32947` somou as 19 do próprio `pedro-plugins` (§10) — que **não** vêm da
amostra da CLI e por isso não estão sujeitas a este defeito [confirmado — contagem por
marketplace rodada nesta rodada: 8 marketplaces, 19 + 29 = 48 entradas].

⚠️ **A guarda aditiva cobre plugin, não marketplace.** A união roda dentro de
`.marketplaces | map(...)`, e a lista de marketplaces vem do `known_marketplaces.json`
(`--slurpfile marketplaces "$KNOWN_MARKETPLACES"`), não da amostra da CLI — então um
marketplace ausente dessa fonte não tem entrada nova para receber os plugins antigos.
[inferido — leitura do `snapshot.sh` nesta rodada; não reproduzido] `session-sync.sh`
continua pulando o snapshot só quando `apply.sh` sai ≠ 0 (ver `durability.md §1.1`).

**A chave `skills` (2026-07-30) é declaração, não instalação.** `skills.permitidas` lista as
**19** skills soltas de `~/.claude/skills` que o usuário aceita. O `_nota` do próprio arquivo é
explícito: *"O bootstrap NAO as instala — a lista existe pro conformance acusar skill nao
declarada."* Quem a consome é `plugins/bootstrap/lib/conformance.py:check_skills`, que
compara os dois lados e reporta `intrusas` (instalada e não declarada) e `sumidas`
(declarada e não instalada). É o primeiro pedaço do manifest que não descreve marketplace.

### 10.2 · O contrato de forma (bootstrap v1.3.0 → v1.7.0) — regra, mecanismo e verificador

Três componentes novos em 2026-07-30, e a arquitetura está na divisão entre eles: o output
style é a **regra** (ponderável, entra no prompt de sistema), o Stop hook é o **mecanismo**
(bloqueia depois do fato) e o conformance é o **verificador** (só reporta).

- **`output-styles/clean-style.md`** — a regra. Frontmatter: `name: Clean Style`,
  `keep-coding-instructions: true`, `force-for-plugin: true`. Um teto único e explícito —
  *"até 6 linhas de prosa no total"* —, com a exceção que carrega o desenho: *"Bloco de prova
  não conta nessas 6 linhas e não tem tamanho máximo. Quando prova e teto competem, a prova
  ganha."* O corpo é calibrado com medição, não com opinião: *"Medi 71 respostas que o usuário
  aprovou contra 154 que ele rejeitou. Tamanho, bullets, header e primeira linha são
  estatisticamente iguais nos dois grupos — forma não separa."* A ativação é dupla:
  `force-for-plugin: true` no style e `"outputStyle": "Clean Style"` em
  `config/settings-defaults.json`, aplicado por `hooks/lib/apply-config.sh` na lista de flags
  em que *"defaults win"*.
  ⚠️ **O identificador do style é acoplamento de seis pontas, e a v1.6.0 mediu isso.** Trocar
  o identificador antigo (o nome próprio do dono) por `Clean Style` exigiu mexer em seis
  lugares de uma vez: o nome do arquivo, o
  `name:` do frontmatter, `config/settings-defaults.json`, os dois pontos de
  `lib/conformance.py:check_output_style` (arquivo e valor esperado), `lib/test_conformance.py`,
  `config/CLAUDE-global.md` e a `skills/setup/SKILL.md`. Nenhum tipo, nenhum import — só
  strings casando por igualdade em arquivos que não se conhecem. O motivo da troca é de
  distribuição, não técnico: **o marketplace vai ser presenteado, e nome próprio de pessoa
  não é presenteável — comportamento é.**
- **`hooks/stop-prose-ceiling.py`** — o mecanismo, e o **único hook do repo invocado como
  `python3 …` direto** em vez de um `.sh`. Registrado em `hooks/hooks.json` no evento `Stop`
  (10s) [confirmado — wiring lido nesta rodada]. Lê o `.jsonl` do transcript de trás pra
  frente, conta linhas de prosa depois de remover bloco de código cercado e linha de tabela,
  e sai `exit 2` acima de `TETO`. Também pega dois padrões nomeados na calibração: retórica
  de ligação (`RETORICA`, 11 alternativas de topo — *"vale notar"*, *"dito isso"*,
  *"ou seja,"*, *"o que eu fiz foi"*, …) e menu de opções no fim
  (*"decida e diga qual escolheu"*).
  ⚠️ **Desde `ff32947` o teto de LINHAS é opt-in, e as outras duas reprovações não.**
  `TETO = int(_TETO_ENV) if _TETO_ENV.isdigit() else None` — sem `PROSE_CEILING_MAX` numérico
  no ambiente **não existe teto de tamanho**, e o `if TETO is not None and len(prosa) > TETO`
  simplesmente não acusa. Retórica e menu de opções continuam ligados sempre. A razão está na
  docstring do arquivo: contar linha *"e preferencia de estilo do dono, nao regra universal"*
  — e um hook que barra por tamanho na máquina de quem recebe o marketplace é imposição, não
  ferramenta. `PROSE_CEILING=0` segue desligando tudo. [confirmado — smoke nesta rodada, hook
  real com transcript sintético de 9 linhas de prosa: **sem** a variável → `exit 0` mudo;
  **com** `PROSE_CEILING_MAX=6` → `exit 2` com *"9 linhas de prosa, o teto e 6"*; e uma
  resposta de 1 linha com *"Vale notar"* → `exit 2` **sem** a variável]
  Kill-switch `PROSE_CEILING=0`; fail-open em payload ilegível. Desde a v1.4.0 o diretório
  de estado sai de `CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))`,
  **a mesma linha do `conformance.py:CLAUDE_DIR`** — com `Path.home()` fixo, quem usa
  `CLAUDE_CONFIG_DIR` fazia o hook escrever num lugar e o verificador ler noutro, e o
  relatório dizia *"nenhuma resposta furou o teto"* com o teto furado. O par
  escritor/leitor virou teste (`test_conformance.py`: *"o hook escreve o furo DENTRO de
  `CLAUDE_CONFIG_DIR`"* + *"o conformance LE o furo que o hook escreveu"*).
- **`lib/conformance.py`** — o verificador. **Modo relatório, nunca escreve nada**
  (*"Decisao de projeto (2026-07-30): a ferramenta mostra o desvio, quem le decide."*); sai `0` conforme,
  `1` com desvio, e não bloqueia. **Dez** checagens em `CHECAGENS`: `check_plugins`,
  `check_claude_md`, `check_teto_unico`, `check_output_style`, `check_skills`,
  `check_hooks_duplicados`, `check_gates_enganosos`, `check_bypass_teto`,
  `check_ferramentas_externas` (a nona, v1.7.0 — §10.3) e `check_catalogo` (a décima,
  `ff32947` — abaixo) [confirmado — lista lida do `conformance.py` nesta rodada].
  Duas capacidades novas entraram em `ff32947`, e as duas fecham buracos do tipo
  "ninguém compara os dois lados":
  - **AUSENTE deixou de ser confundido com DESLIGADO.** `_refs_instaladas()` lê
    `<config>/plugins/installed_plugins.json` — formato conferido na máquina,
    `{"plugins": {"<nome>@<mkt>": [ …instalações… ]}}` — e `check_plugins` passou a
    distinguir *"não instalado nesta máquina"* (conserto: `claude plugin install`) de
    *"instalado e no estado errado"* (conserto: `enable`/`disable`). O conserto antigo era
    literalmente inexecutável no primeiro caso: `claude plugin enable` num plugin que nunca
    foi instalado falha. Fonte ausente ou ilegível ⇒ `None` ⇒ volta ao comportamento antigo,
    que só enxerga `enabledPlugins` — fail-open, porque a ferramenta é só relatório.
  - **`check_catalogo` compara a receita com o catálogo publicado.** Plugin que entra no
    `.claude-plugin/marketplace.json` e **não** entra em `config/manifest.json` nunca chega
    a máquina nenhuma, e nada mais no repo cruzava as duas listas. Ele resolve onde mora o
    catálogo nesta máquina por `_catalogo_publicado()`: primeiro o registro vivo
    (`<config>/plugins/known_marketplaces.json` → marketplace de diretório lê no próprio
    diretório, `git`/`github` lê o clone em `plugins/marketplaces/`), e só então o fallback
    repo-relativo pra quem roda de dentro do checkout. **Máquina sem o marketplace instalado
    sai calada**, não acusa. Hoje a área sai `conforme` [confirmado — a linha `conforme:` do
    run desta rodada termina em `dependencia · catalogo`].

Quatro decisões deste bloco valem registro porque são o mesmo raciocínio do resto do repo:

- **Anti-loop com o furo AUDITADO, não silencioso.** `MAX_BLOQUEIOS = 2` por resposta; ao
  estourar, o hook desiste (bloquear pra sempre trava a sessão) **mas grava a desistência**
  em `~/.claude/state/prose-ceiling/bypass.log`, e `check_bypass_teto` mostra ao usuário
  quantas vezes o teto foi furado. É a mesma forma do `MAX_NUDGES` do §11, com o registro
  que os outros gates não têm.
- **A chave do contador é `sha1(session_id + texto INTEIRO)`.** O comentário do arquivo diz
  por quê: com `texto[:200]`, *"duas respostas diferentes que começam igual dividiam o mesmo
  orçamento — e o output style manda a 1ª linha ser estável, então a colisão era o caso
  comum, não a exceção"*. A regra de forma **produziu** a colisão que o mecanismo sofria.
- **Teto conhecido e escrito no próprio arquivo:** como todo hook de plugin, ele só carrega
  no `SessionStart` — *"sessao ja aberta no momento da instalacao fica descoberta ate o
  proximo `/clear`"*.
- **Colisão de gate se mede por BLOQUEIO, e a declaração vence a inferência (v1.5.0).**
  `check_hooks_duplicados` contava **registro** de `PreToolUse` por ferramenta, então acusava
  colisão onde só havia aviso. Hoje ele abre o script de cada registro e pergunta se aquilo
  bloqueia — `bloqueia()` procura `permissionDecision` + `"deny"` ou `exit 2`, **mas antes
  procura o comentário `# conformance: default-warn` no próprio script**, que desliga a
  contagem. É o padrão "explícito vence heurística de texto": hoje há **uma** declaração
  dessas no repo, em `plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh`, no
  comentário logo acima do ramo `GRAPHIFY_DENY` (*"o caminho de deny existe, mas só com
  `GRAPHIFY_DENY=1`"*) [confirmado — `grep -rn "conformance: default-warn" plugins/` nesta
  rodada devolve só esse arquivo + o próprio `conformance.py`]. Ilegível ⇒ `return True`, assume o pior — fail-open na direção de **acusar**, não
  de calar. A mensagem de desvio mudou junto e virou julgamento explícito do humano:
  *"colisao so e DEFEITO quando os gates tem o MESMO proposito … Gates com propositos
  distintos no mesmo evento sao camadas, nao duplicatas"* — o repo tem três gates no
  `ExitPlanMode` de propósito (§6).
- **…e a checagem acima nasceu errada em quatro pontos, todos no caminho "que script é este
  token?" (v1.5.1).** Vale registrar porque os quatro são a **mesma** causa: o resolvedor era
  `c.replace('"'," ").split()` + `tok.split("CLAUDE_PLUGIN_ROOT}/")[-1]`, e todo token com `/`
  virava alvo. (1) `<script>.sh 2>/dev/null` partia em dois, e o fantasma `2>/dev/null` caía no
  `except OSError` — que **assume o pior** — anulando o `default-warn` que o script declarava;
  (2) o split era literal em `CLAUDE_PLUGIN_ROOT}/`, então a forma **sem chaves**
  (`$CLAUDE_PLUGIN_ROOT/…`) resolvia 100% fantasma; (3) `raiz / token` com token **absoluto**
  descarta a raiz (semântica do `pathlib`), e um arquivo de fora do plugin passava a ditar o
  veredito de bloqueio. Hoje existe `alvo(raiz, tok)`: exige a marca `${CLAUDE_PLUGIN_ROOT}/`
  **ou** `$CLAUDE_PLUGIN_ROOT/`, tokeniza com `shlex.split` (que entende aspa simples, *"igual
  ao shell"*, com fallback pro split cru quando a aspa não fecha) e só aceita o que
  `is_file()` **e** tem a raiz do plugin entre os `parents`. A lição que vale além do caso: um
  verificador que **assume o pior em erro** precisa de um resolvedor **exato**, senão o
  fail-safe vira gerador de falso-positivo — o pessimismo defensivo só é seguro sobre entrada
  bem-definida. (4) O quarto defeito virou checagem nova em `check_gates_enganosos`: **dois
  `.mode` homônimos em pastas diferentes**. Só um vale (o hook lê o de `<config>/guardrails/`),
  os outros são inertes, e **editar o inerte não muda nada e não avisa** — o defeito é a
  *existência* do duplicado, não o valor dele. O `~/.claude/hooks/scope-cop.mode` inerte foi
  aposentado no mesmo commit [confirmado — `ls` nesta rodada: *No such file or directory*].

⚠️ **Os três componentes nasceram sem suíte, e isso durou de 1.3.0 a 1.4.0** — o
`release-gate.sh` só executa `plugins/<nome>/lib/test_*.py`, então commit que só tocasse o
`bootstrap` não rodava teste nenhum. Os quatro bumps de 1.3.0 a 1.3.3 numa mesma tarde
(`3ef0bb8` *"o furo do teto de prosa deixa de ser silencioso"*, `7b0357d` *"contador
anti-loop colidia entre respostas diferentes"*) são a assinatura disso no log. A v1.4.0
fechou com `lib/test_conformance.py` (8 checks) e `hooks/test_bootstrap_hooks.sh` (9 checks)
— e o defeito que motivou a rodada foi achado por **smoke de instalação limpa**, não pelas
suítes: `hooks/lib/apply-config.sh` misturava `$HOME` fixo com `CLAUDE_CONFIG_DIR`, e rodar
com a variável setada deixava a pasta-alvo vazia **sobrescrevendo o `~/.claude` real**
[relatado — mensagem do commit `352e8d5`].

O bootstrap também versiona a config global da máquina:
`plugins/bootstrap/config/settings-defaults.json` e `config/CLAUDE-global.md`, aplicados
por `hooks/lib/apply-config.sh`. Os 4 helpers em `hooks/lib/` (`git-sync.sh`, `apply.sh`,
`apply-config.sh`, `snapshot.sh`) são exatamente as 4 etapas do hyperedge "Bootstrap Sync
Cycle". ⚠️ **A cópia do `CLAUDE.md` é de mão única, repo → máquina**: o `snapshot.sh`
regenera o manifest mas não traz o `CLAUDE.md` de volta, então regra escrita direto em
`~/.claude/CLAUDE.md` some no próximo `apply-config.sh` — é por isso que `check_claude_md`
mostra o que só existe de cada lado e **não prescreve direção**.

### 10.3 · Dependência externa de plugin (bootstrap v1.7.0) — a terceira categoria do manifest

Até a v1.6.0 o manifest só sabia de duas coisas: **o que o bootstrap instala** (marketplaces
e plugins) e **o que ele apenas declara pra conferência** (`skills.permitidas`, §10.1). A
v1.7.0 abriu a terceira: **binário que um plugin DESTE repo exige e que o marketplace não
tem como instalar.** A chave de topo nova é `ferramentas_externas`, com `_nota` + `itens`;
hoje há **1 item** [confirmado — leitura do JSON nesta rodada].

O único item é `graphify` (pacote `graphifyy` no PyPI, MIT, `uv tool install graphifyy` com
`pipx` como alternativa), `requerido_por: ["graphify-guard"]`. O campo `porque` é a razão
inteira de a categoria existir, e está escrita no próprio dado: *"o graphify-guard procura
`graphify-out/graph.json` e redireciona busca cega pro grafo; sem o binario ninguem cria esse
diretorio e o guarda vira decorativo"*.

**É a mesma classe de defeito do gate meio-ligado do §6, um nível acima.** Lá o gate estava
`off` com o plugin habilitado; aqui o plugin está habilitado e íntegro, e o que falta é
**fora do repo**. Nos dois casos o sintoma é idêntico e é o pior possível: o componente
existe, não reclama, e não protege. A checagem que fecha isso é
`conformance.py:check_ferramentas_externas` — cruza `requerido_por` com os
`enabledPlugins` **ligados** de `settings.json` e só então testa `shutil.which(comando)`.
Duas decisões de desenho:

- **Só cobra quem usa.** Plugin desligado não gera desvio — a checagem retorna antes do
  `which`. Sem isso, todo mundo que não usa grafo levaria um desvio permanente e aprenderia
  a ignorar o relatório inteiro.
- **O bootstrap continua não instalando nada disso.** A `skills/setup/SKILL.md` ganhou o
  passo **2c** com a ordem explícita: *"Não instale por conta própria. Ofereça o comando ao
  usuário e explique o que ele destrava"* — e nomeia a saída alternativa honesta: *"Se ele
  não usa grafo, o caminho certo é desligar o `graphify-guard` no manifest, não instalar o
  binário."* Mesma postura do verificador: mostra o desvio, o humano decide.

### 10.4 · O setup deixou de ser invasivo (`ff32947`) — duas travas, uma regra

O `bootstrap` roda de um hook de `SessionStart`. Isso significa que **tudo que ele faz,
ele faz sem ninguém pedir, na abertura de uma sessão qualquer** — e é essa propriedade,
não o conteúdo de cada passo, que `ff32947` levou a sério.

**1 · Desinstalar virou opt-in.** O passo 3 do `hooks/lib/apply.sh` removia todo plugin que
estivesse num marketplace declarado e **não** no manifest. Hoje ele coleta os candidatos
numa passada pura (`UNINSTALL_CANDIDATES`, sem efeito colateral) e só age dentro de
`if [ "${BOOTSTRAP_UNINSTALL_UNMANAGED:-0}" = "1" ]` — e aí com `--keep-data`. Sem a
variável, imprime *"desinstalação DESLIGADA — N plugin(s) seriam removidos: …"* e não mexe
em nada. O racional está no cabeçalho do arquivo e é aritmético, não filosófico: *"a
marketplace oficial da Anthropic entrega centenas de plugins enquanto o manifest declara um
punhado, então uma rodada sem guarda desinstalaria tudo que o manifest não nomeia, a partir
de um hook de SessionStart."* `pedro-plugins` continua filtrado em qualquer caso.
[confirmado — `apply.sh` lido nesta rodada; a `skills/setup/SKILL.md` repete a regra no
passo 1: *"Sem a variável o script apenas LISTA o que seria removido"*]

**2 · A config global parou de baixar a guarda.** `config/settings-defaults.json` perdeu o
`defaultMode: "auto"` — hoje `permissions` tem exatamente **duas** chaves, `allow` (141
entradas) e `deny` (19), e **nenhum** `defaultMode` [confirmado — leitura do JSON nesta
rodada]. Saíram também da allowlist os quatro comandos que aprovavam a si mesmos por
categoria: `Bash(eval*)`, `Bash(ssh*)`, `Bash(curl*)` e `Bash(export*)`. `eval` e `export`
executam string arbitrária; `ssh` e `curl` são a fronteira da máquina para fora. Sobraram os
específicos que não têm essa propriedade — `Bash(ssh-add*)`, por exemplo, segue na allow.
A `SKILL.md` do setup escreve o contrato em letra: *"o modo de aprovação continua o que já
estava nesta máquina, e o setup nunca liga aprovação automática."*

**A regra que as duas compartilham:** *automação que roda sem ser chamada só pode ADICIONAR.*
Remover software e afrouxar aprovação são atos com consequência que o dono da máquina não
pediu — viram flag explícita (`BOOTSTRAP_UNINSTALL_UNMANAGED=1`) ou saem do produto. É a
mesma postura do `conformance.py` ("mostra o desvio, você decide"), aplicada um degrau antes:
o verificador não conserta, e agora o aplicador também não destrói.

## 11. Decisões de arquitetura

- **Vendoring em vez de import em runtime.** O isolamento de plugin do Claude Code não
  permite referência cross-plugin; a alternativa (duplicar à mão) apodrece. Custo aceito:
  um passo de build manual, gateado no commit. [confirmado — `sync-shared.sh` + gate A do
  `release-gate.sh`]

- **`version` = chave de propagação; `gen` = gatilho de reconstrução.** São desacopladas de
  propósito: `plugin.json.version` bumpa a **cada** mudança (senão o cliente nunca recebe);
  `CURRENT_GEN` do `pattern_check.py` só bumpa quando a doc antiga vira base
  não-confiável. Hoje: `project-doc` v3.18.3, `gen 3.8` — a `version` andou de 3.13.0 até
  aqui sem que a `gen` mudasse, que é exatamente o desacoplamento pretendido.
  [confirmado — `pattern_check.py`
  e `plugin.json`]

- **Gate mecânico > prosa no CLAUDE.md.** `.claude/hooks/release-gate.sh` intercepta
  `git commit` e checa **7** invariantes que antes eram só texto — as letras são as do
  próprio arquivo: (A) vendoring em drift, (B) espelho `plugin.json` ↔ `marketplace.json`,
  (C) bump esquecido (version idêntica à do `HEAD`), (D) `test_*.py` dos plugins tocados,
  (E) contrato dos hooks vs. o retrato congelado, (G) `gen=` defasado no marker das skills
  do `project-doc`, (F) `test_*.sh` dos plugins tocados. O detalhe de cada um está em
  `patterns.md §5.2`. Bloqueia com `exit 2` e a mensagem no
  stderr. **Fail-open em erro de infra** (sem git/python3, fora do repo) — "só bloqueia com
  evidência concreta na mão". **Limite conhecido e comentado no próprio script: untracked
  NÃO entra** no conjunto de arquivos, porque sem `git add` não é commitado (incluí-lo dava
  falso-positivo com estado de runtime, ex.: `visual/skills/visual/config.json`).

- **A regra de forma da resposta é distribuída em três peças separadas, e é de propósito.**
  Introduzido no `bootstrap` v1.3.0 (2026-07-30, §10.2): a **regra** vai no output style
  `output-styles/clean-style.md` (entra no prompt de sistema, é ponderável e o modelo pode errar);
  o **mecanismo** vai no `Stop` hook `stop-prose-ceiling.py` (mede prosa e devolve `exit 2`,
  só sabe contar); o **verificador** vai em `lib/conformance.py` (compara máquina viva ×
  contrato versionado e **não escreve nada**). Separar existe porque cada peça tem um teto
  próprio: o style não é executável, o hook não entende conteúdo, e o conformance não decide.
  Duas consequências ficaram registradas no código em vez de na prosa: o furo do anti-loop
  vira linha em `bypass.log` em vez de silêncio, e a checagem `check_teto_unico` proíbe
  **mais de uma** regra numérica de linhas — a causa-raiz nomeada da verbosidade foi ter
  três tetos válidos ao mesmo tempo, com o mais permissivo vencendo.
  ⚠️ **A separação sobreviveu à distribuição, mas o teto de linhas não** (§10.2, `ff32947`):
  ele virou opt-in por `PROSE_CEILING_MAX`, enquanto retórica e menu de opções seguem
  sempre ligados. É o critério que a divisão em três peças permitiu enxergar — **preferência
  de estilo se declara e se desliga; defeito de forma se barra** —, e ele só pôde ser
  aplicado a uma das três peças porque elas não são a mesma coisa.

- **O que o marketplace NÃO instala vira DADO declarado, não suposição.** Introduzido no
  `bootstrap` v1.7.0 (§10.3): binário externo exigido por um plugin daqui ganhou a chave
  `ferramentas_externas` no manifest e a checagem `check_ferramentas_externas`. A decisão
  tem três metades e cada uma nega uma alternativa mais fácil: **(1)** declarar em dado, não
  em código, porque dependência nova é um objeto JSON e não um `if`; **(2)** cobrar só
  quando o plugin que precisa está **ligado**, porque desvio permanente em quem não usa o
  recurso corrói a confiança no relatório inteiro — o custo de um verificador é a atenção
  que ele consome, não o tempo que ele leva; **(3)** **não instalar**, mesmo sabendo o
  comando exato. A skill oferece e explica; o humano decide, e desligar o plugin é uma
  resposta tão válida quanto instalar o binário. É a mesma postura do conformance ("mostra o
  desvio, você decide") estendida pra fora do repo.

- **Identificador em contrato distribuído é acoplamento invisível, e o repo pagou pra ver.**
  Trocar o nome do output style, que era o nome próprio do dono, pra `Clean Style` (v1.6.0, §10.2) exigiu editar
  seis arquivos que não se referenciam: o nome do arquivo, o `name:` do frontmatter, o
  `settings-defaults.json`, dois pontos do `conformance.py`, o `test_conformance.py`, o
  `CLAUDE-global.md` e a `SKILL.md` do setup. Nenhum import, nenhum tipo — só strings
  casando por igualdade. **Nada no repo detecta esse conjunto**: o `release-gate.sh` gateia
  vendoring, versão e teste, não coerência de identificador. Quem introduzir o próximo
  contrato por string deve assumir que a única rede é o `conformance.py` acusando depois.

- **Estado mutável mora em `~/.claude/…`, nunca dentro do plugin.** O cache
  `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão. Aplicado em
  `~/.claude/green-suite/` (green-cache), `~/.claude/visual-state/` (visual server) e
  `~/.claude/intent/<slug>` (ledger, quando não há projeto git).

- **Estado por-sessão em `/tmp` tem que ser chaveado por `session_id`.** Arquivo global
  vaza entre sessões concorrentes. Aplicado nos sentinels do plan gate
  (`/tmp/claude-plan-gate-{escape,count}-${SESSION}-${PHASH}`) e no filtro por sessão do
  `ledger.fold()`. A regra nasceu de um bug real do `context-guard` [relatado — memory
  `context-guard-global-state-bug`; o código atual do plan gate a segue, confirmado].

- **Enumeração vinda de CLI externa é AMOSTRA, não verdade — a fusão é aditiva.**
  Introduzido no `bootstrap` v1.4.1 (§10.1) depois de medir `claude plugin list` devolvendo
  saída truncada em 1 de 5 chamadas. A regra que ficou no código: quando não dá pra
  distinguir "sumiu" de "a fonte não listou desta vez", **ausência não é evidência de
  remoção** — a entrada fica e remover vira ato explícito de humano. É a mesma família do
  `scope_staleness()` do `pattern_check.py`, que devolve `unknown` em vez de `fresh` quando
  o `git log` falha: o sistema **nunca converte falta de dado em afirmação**.

- **Fail-open, mas na direção segura, e a direção muda por gate.** No green-cache, erro →
  MISS → a suite roda. No plan gate, erro **de infra** → passa; mas "consegui determinar que
  não há doc" → **nega**, porque aí há evidência. No `cmd_verify` do intent-guard, falha →
  devolve tudo pro auditor caro ("degradar pro caro é seguro; pro barato não").

- **Anti-loop é absoluto: o gate degrada, nunca trava.** `MAX_NUDGES=3` no plan gate e no
  doc-guard; 1 deny por (costura, sessão) no organism gate. Um gate bloqueante idêntico no
  `ExitPlanMode` já morreu por loop infinito no passado [relatado — findings
  `76352a3aefbb63ca` / `d78d77b0a2eec97b`]. O código atual **volta a hookar
  `ExitPlanMode`**, mas com cap e com a justificativa escrita no arquivo ("é
  comprovadamente hookável — visual e intent-guard já a usam") [confirmado —
  `pretooluse-plan-gate.sh`].

- **O plano de implementação é ARQUIVO, e o agente só o MARCA.** Introduzido no `visual`
  v1.5.0. `<raiz>/.claude/plans/<id>.plan.json` (versionado) guarda fases/passos com **id
  fixo** (`F2.3`), uma linha didática por passo (≤140 chars, exigida pelo schema) e o estado
  de cada um. `plugins/visual/lib/plan_state.py` tem 7 verbos (`init`, `tick`, `state`,
  `render`, `page`, `open`, `close`/`reopen`) e duas travas que são a razão de existir:
  `init` **recusa** um id existente com título diferente (renomear exige `--rename` explícito)
  e `tick` **recusa** sem `--evidencia`. A árvore HTML e a página inteira saem de `render`/`page`,
  não do modelo — é isso que impede o plano de mudar de nome ou de aparência entre renders.
  O motivo está registrado no cabeçalho do módulo: até aqui o plano só existia no transcript e
  todo consumidor o re-derivava por LLM — em `extract_ata.py:build_prospective()`, a
  atribuição de `last_plan` guarda `"excerpt": txt[:1200]` e a de `last_plan["likely_executed"]`
  decide conclusão com `commits_after > 0 or edits_after >= 3`. [confirmado —
  `plan_state.py` + `plugins/visual/lib/test_plan_state.py`, 55 checks]

- **Artefato de apresentação é EMITIDO por programa; o modelo escreve o insumo.**
  Generalização, em 2026-07-29, da decisão do plano acima. Vale hoje em três lugares: a
  árvore/página do plano (`plan_state.py page`), a página do `/visual` a partir de um spec
  JSON (`visual_page.py build`), e o deck do modo transcrição do `/slides` a partir do `.md`
  (`md2deck.py`). O raciocínio é o mesmo nos três: **regra de forma escrita em prosa
  apodrece, e o defeito é silencioso.** A prova de que apodrece está no repo — uma cópia do
  bloco `.decisions-box` colada na SKILL.md do `/visual` divergiu do `template.html` e quem a
  seguia entregava página sem o selo de live-sync; e a primeira versão da página desta mesma
  rodada, escrita à mão, usou três classes CSS (`.exec-title`, `.label`, `.lead`) que **não
  existem** no template. Classe inexistente não dá erro: dá bloco sem estilo que passa por
  escolha de design. Custo medido **naquela página específica**: 12390 bytes de markup
  digitado → 3141 bytes de sintaxe JSON. **Não é fator fixo** — o ganho é só na estrutura
  (prosa e saída crua pesam igual nos dois lados), então página com muita estrutura economiza
  mais e página quase toda texto economiza menos; nos arquivos em disco a mesma comparação dá
  ~2,1×. Uma re-medição independente com **outro** spec deu 16480/11665/4815 bytes: a direção
  se confirma, o fator não se reproduz. Quem precisar do número pra uma decisão, meça o caso. **Limite aceito e deliberado:** o que é julgamento continua no
  modelo — o conteúdo, a ordem, o componente de cada slide, a linguagem humana da decisão —, e
  cada emissor tem uma válvula (`raw_html` no `/visual`, `--anota` no `/slides`) porque
  trocar token por engessamento seria trocar um problema por outro. [confirmado — os dois
  módulos + 110 checks entre `test_visual_page.py` e `test_md2deck.py`]

- **Contrato de hook é MEDIDO, não combinado.** Introduzido em 2026-07-27, depois
  de a varredura mostrar que os 3 gates do `ExitPlanMode` divergiam em cap,
  kill-switch, canal e resolução de binário — **porque não havia onde o contrato
  estivesse escrito**. `scripts/hook_contract.py` (stdlib) lê os **33 registros**
  (32 scripts distintos, re-medido nesta rodada) e mede 5 propriedades: canal de saída, cap anti-loop (escopado por
  sessão), kill-switch, binário por `command -v`, e fail-open. O texto do contrato
  e as 4 isenções nomeadas vivem em `patterns.md §5.3`; o **check E** do
  `release-gate.sh` compara com `.claude/hook-contract.baseline.json` e barra só o
  que **piorou** — achado já aceito não trava ninguém, que é o que impede a regra
  de apodrecer. A varredura levou o repo de **20 achados a 3**, e os 3 restantes
  são isenções escritas. ⚠️ O checker é **grep sofisticado, não verdade**: 5 das 12
  acusações caíram na conferência no código, e uma delas era ele *inventando* um
  teto que não existia. Os 5 casos viraram teste (`scripts/test_hook_contract.py`,
  28 checks). [confirmado — checker + suite executados neste run]

- **Branch é limpa por CONTEÚDO, não por ancestralidade.** O `branches` v1.0.0
  existe porque `git branch --merged` — a ferramenta que todos usam — só enxerga
  merge por ancestral. Squash-merge e rebase reescrevem o commit com sha novo, e
  a branch original aparece como não-mergeada **com o conteúdo inteiro no
  tronco**. Medido aqui: `docs/readme` era negada pelo `--merged` e tinha o
  commit na main. Como a lista mistura "já foi" com "ainda não foi", ninguém
  apaga nada, e a pilha cresce até o deploy reclamar. `branch_state.py` compara
  por patch-id (`git cherry`) e devolve três categorias: `merged`, `equivalent` (o que
  o `--merged` perde) e `unique` (trabalho de verdade). **Nada é apagado
  sem marcação humana**, e toda remoção cria antes a tag `archive/<branch>-<data>`
  — o `prune` aborta se não conseguir criá-la. [confirmado — 48 checks em
  `test_branch_state.py`, 4 formas de merge cobertas]

- **O sistema afirma, o agente refuta com citação verificada.** Vale para o organism gate
  (`verify_cite`) e para o gate de entrega do intent-guard (veredito
  `confirmado`/`inferido` com evidência de ≥10 chars, checado por `audit_check`). O agente
  nunca preenche o formulário do próprio viés.

- **Escada de custo antes de gastar LLM.** `cmd_verify` resolve por código o que tem receita
  mecânica; o juiz LLM só **escolhe** de um catálogo fechado, nunca escreve comando.

- **Stdlib-puro é requisito.** Python: zero dependências externas nas 4 libs. Node: só
  stdlib no daemon. PyYAML é *opcional* com paridade testada — a razão está no commit
  `12dd07402ee78dfd`: uma dependência dura de PyYAML fazia o gate **fail-open em silêncio**
  numa máquina limpa (instala, nada funciona).

- **Documentação agent-facing com ponteiros finos.** Um índice (`CLAUDE.md`), docs por
  concern em `.claude/docs/`, e `AGENTS.md`/`GEMINI.md`/`.cursorrules`/`.windsurfrules`
  apenas apontando pra lá. É o hyperedge "Cross-Tool Doc Routing".

## 12. Divergências vivas

Encontradas neste run, cada uma com o comando/arquivo que a prova:

1. ~~**`metadata.description` do marketplace diz "19 plugins"; há 20 entradas.**~~
   **RESOLVIDA em 2026-07-28.** Verificado neste run: a descrição diz `19` e
   `len(plugins) == 19` — batem. A divergência sumiu porque as duas pontas foram mexidas
   juntas (saíram dois plugins do catálogo, e a descrição foi ajustada no mesmo commit).
   **A causa não foi removida:** nenhum gate cobre o texto da descrição, então ela volta
   na próxima vez que alguém mexer só na lista. Continua sendo trabalho manual.

2. ~~**`pi-plugins/` é untracked, obsoleto e NÃO está gitignorado.**~~
   **RESOLVIDA em 2026-07-28**, pela segunda decisão registrada ("Ignorar (gitignore)",
   `be869abe8721ffbf`), que enfim saiu do papel. Verificado neste run:
   `git check-ignore -v pi-plugins/` → `.gitignore:53:pi-plugins/`, e `git status` não
   mostra mais `?? pi-plugins/`. O conserto estava **preso** havia 17 dias num commit que
   só existia em duas branches (`e61e456af`); foi trazido pra `main` por cherry-pick.
   O diretório **segue no disco** (só deixou de ser rastreado), então a poluição do grafo
   por fan-in duplicado continua — o alerta do `CLAUDE.md` sobre isso vale.

3. **`AGENTS.md`, `GEMINI.md` e `.cursorrules` mandam ler `CLAUDE.md` na raiz — que não
   existe neste repo.** `ls CLAUDE.md` → *No such file or directory* (reconfirmado neste
   run); o índice real é `.claude/CLAUDE.md`. Os ponteiros levam a lugar nenhum para quem
   os obedece literalmente. **Única das três ainda viva.**

4. **Docstring do `pattern_check.py` diz `gen=3.7`, o código diz `3.8`.** Linha 3 do
   módulo vs `CURRENT_GEN = "3.8"` (linha 25). O código manda; a docstring ficou pra trás
   no bump da v3.13.0.

5. ~~**`manifest.json` do bootstrap promete uma entrada que não tem.**~~
   **RESOLVIDA em `ff32947`.** A `description` sempre afirmou *"The pedro-plugins entry is
   manually maintained and preserved across snapshots"* sem que a entrada existisse.
   Verificado nesta rodada: `.marketplaces` tem **8** entradas e a **primeira** é
   `pedro-plugins`, com `source` HTTPS e os 19 plugins (§10). A promessa deixou de ser
   vestigial. **A causa também foi endereçada**, e num lugar diferente do texto: a checagem
   nova `conformance.py:check_catalogo` (§10.2) compara catálogo publicado × receita e acusa
   plugin que entrou num e não no outro — era exatamente esse par que ninguém conferia.

6. **`plugins/visual/skills/visual/config.json` é estado mutável de runtime dentro do
   plugin** — untracked (`git status`: `?? plugins/visual/skills/visual/config.json`),
   ao lado do `config.default.json` versionado. Contraria a regra do §11 ("estado mutável
   mora em `~/.claude/`"): o cache `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump, então
   o modo auto do `/visual` se perde na atualização. É também o caso que motivou a
   exclusão de untracked no `release-gate.sh`.

7. **Uma comunidade nomeada do grafo aponta pra `plugins/qa/`, que não existe.** O plugin
   `qa` foi substituído por `qa-loop`; o rótulo sobreviveu ao refresh do grafo. Reforça
   que comunidade nomeada é mapa, não verdade.

## 13. Verificação

Tudo abaixo foi **executado** nesta rodada, no commit `5ce0c1b`:

```bash
bash scripts/sync-shared.sh --check          # OK: cópias vendored idênticas a _shared/
for t in plugins/*/lib/test_*.py; do python3 "$t"; done
#   plugins/intent-guard/lib/test_ledger.py         OK
#   plugins/project-doc/lib/test_doc_lint.py        OK
#   plugins/project-doc/lib/test_graph_map.py       OK
#   plugins/project-doc/lib/test_journal.py         OK
#   plugins/project-doc/lib/test_organism.py        OK
#   plugins/project-doc/lib/test_pattern_check.py   OK
```

**6 suites Python** (todas verdes) e **5 suites shell**:
`plugins/intent-guard/hooks/test_{delivery_audit,hooks_capture,plan_gate,task_checkpoint}.sh`
e `plugins/project-doc/hooks/test_plan_gate.sh` (esta última **não foi executada** neste
run — só inventariada).

[TODO: rodar as 5 suites shell e registrar o resultado — nenhuma delas está no gate D do
`release-gate.sh`, que só varre `plugins/<nome>/lib/test_*.py`]

**Acréscimo desta rodada** — as duas suítes novas do `bootstrap`, executadas aqui:

```bash
python3 plugins/bootstrap/lib/test_conformance.py     # 8 ok · 0 FAIL   (exit 0)
bash    plugins/bootstrap/hooks/test_bootstrap_hooks.sh  # 9 ok · 0 FAIL   (exit 0)
python3 scripts/hook_contract.py | head -1            # 33 registros, 32 scripts distintos
```

A shell cobre o hook de prosa (teto, prova isenta, retórica, kill-switch, colisão de
contador, fail-open) **e** o `snapshot.sh` (*"chave arbitraria sobrevive ao snapshot"*,
*"skills sobrevive ao snapshot"*); a Python cobre as checagens do `conformance.py` **e** o
par escritor/leitor do `bypass.log` sob `CLAUDE_CONFIG_DIR` (§10.2).

### 13.1 · O inventário de suítes dobrou (2026-07-30, noite)

Contagem mecânica desta rodada — o *inventário*, não uma execução completa:

```bash
ls -1 plugins/*/lib/test_*.py scripts/test_*.py | wc -l   # 13  (Python)
ls -1 plugins/*/hooks/test_*.sh              | wc -l      # 15  (shell)
```

**13 suítes Python** (12 em `plugins/*/lib/` + `scripts/test_hook_contract.py`) e **15 shell**.
O texto acima, de **6 e 5**, é o retrato de `5ce0c1b` e ficou para trás: o repo passou de 11
para 28 suítes sem que o gate de commit mudasse de forma. **A assimetria continua exatamente
a mesma e é o fato durável aqui — o gate D do `release-gate.sh` só varre
`plugins/<nome>/lib/test_*.py`, então as 15 shell (mais da metade do inventário) seguem fora
de qualquer gate mecânico e só rodam quando alguém as chama.**

Três nasceram no `32cfe28`, todas **executadas nesta rodada e verdes**:

```bash
bash plugins/graphify-guard/hooks/test_graphify_guard.sh  # ── 37 passou · 0 falhou ──
bash plugins/guardrails/hooks/test_scope_cop.sh           # ── 15 passou · 0 falhou ──
bash plugins/guardrails/hooks/test_setup_skill.sh         # ── 29 ok, 0 falha(s) ──
python3 plugins/bootstrap/lib/test_conformance.py         # 36 ok · 0 FAIL   (era 8)
python3 plugins/intent-guard/lib/test_ledger.py           # test_ledger: OK
python3 plugins/project-doc/lib/test_pattern_check.py     # TODOS OS 84 CHECKS PASSARAM
python3 scripts/hook_contract.py | head -1                # 33 registros, 32 scripts distintos
```

Mais duas, do `intent-guard`, executadas depois do `6c5e1f9`:

```bash
bash plugins/intent-guard/hooks/test_task_checkpoint.sh    # rc=0
```

**Re-medição desta rodada, sobre `ff32947`** — o inventário não mudou de tamanho, as duas
suítes do `bootstrap` sim (§8, §10.2):

```bash
ls -1 plugins/*/lib/test_*.py scripts/test_*.py | wc -l   # 13   (inalterado)
ls -1 plugins/*/hooks/test_*.sh              | wc -l      # 15   (inalterado)
python3 plugins/bootstrap/lib/test_conformance.py         # 52 ok · 0 FAIL   (era 39)
bash    plugins/bootstrap/hooks/test_bootstrap_hooks.sh   # 19 ok · 0 FAIL   (era 9)
bash    scripts/sync-shared.sh --check                    # OK: cópias vendored idênticas a _shared/
python3 scripts/hook_contract.py | head -1                # 33 registros, 32 scripts distintos
```

⚠️ **`test_setup_skill.sh` levou mais de 2 minutos** e estourou o timeout padrão na primeira
tentativa — é a única suíte do repo que não roda em segundos. Quem a chamar num script com
timeout precisa saber disso.

⚠️ **Duas armadilhas ao rodar suíte shell neste repo, ambas medidas em `6c5e1f9` (§5):**
- **`rc=$?` depois de um pipe lê o status do último comando da pipeline**, não o do script.
  `bash suite.sh | tail -3; echo $?` reporta o `tail`. Foi assim que uma suíte vermelha foi
  declarada verde aqui. Use `PIPESTATUS[0]`, ou rode sem pipe.
- **Suíte que grava estado em `/tmp` fora do seu repo temporário contamina a própria segunda
  execução.** O `test_task_checkpoint.sh` reprovava na 2ª rodada por lixo
  (`/tmp/intent-guard-ckptcap-<sid>`), não por defeito. **A regra "estado por-sessão em `/tmp`
  chaveado por `session_id`" (§11) protege sessões concorrentes e, exatamente pela mesma razão,
  vaza entre execuções de teste** — o `trap` da suíte precisa limpar o que ela deposita fora do
  `$REPO`.
- **`plugins/intent-guard/hooks/mock_ck_*.sh` são versionados e a suíte os gera/apaga**, então
  rodá-la deixa a árvore suja. Ver §5.

Duas coisas mudaram de natureza junto com os números:

- **O contrato de hook continua em 33/32.** Nenhum registro novo entrou; o que mudou nos hooks
  desta janela (`scope-cop.sh`, `task-checkpoint.sh`, `delivery-audit.sh`) foi **conteúdo**, não
  wiring. Contagem estável com comportamento mudando é exatamente o caso em que a suíte importa
  mais que o inventário.
- **Uma suíte passou a gatear o conteúdo de um doc.** `test_pattern_check.py:
  test_verified_by_do_patterns_nomeia_as_suites_de_hook` é o **único teste do arquivo que lê o
  repo real** (não escreve nada) e exige que as três suítes novas estejam no `verified-by:` do
  `patterns.md` — **e explicitamente NÃO no `scope:`**, com o motivo anti-tautologia escrito no
  próprio teste: suíte no `scope` faria o doc virar `stale` a cada edição de teste. É a regra
  de `unscoped_new` (§8.2) virando teste executável em cima da documentação.