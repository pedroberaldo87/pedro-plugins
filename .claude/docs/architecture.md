---
generated: 2026-08-03
generated-commit: 0501e63
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
  - plugins/project-doc/lib/doc_lint.py
  - plugins/project-doc/hooks/hooks.json
  - plugins/project-doc/hooks/pretooluse-plan-gate.sh
  - plugins/project-doc/hooks/userpromptsubmit-plan-escape.sh
  - plugins/project-doc/hooks/lib-project-root.sh
  - plugins/intent-guard/lib/ledger.py
  - plugins/visual/server/visual_server.mjs
  - plugins/visual/lib/plan_state.py
  - plugins/visual/lib/cobertura.py
  - plugins/visual/lib/visual_page.py
  - plugins/branches/lib/branch_state.py
  - plugins/slides/lib/md2deck.py
  - plugins/fallow/lib/audit.py
  - plugins/fallow/lib/report.py
  - scripts/hook_contract.py
  - .claude/hook-contract.baseline.json
  - .claude/hooks/release-gate.sh
  - .claude/settings.json
  - plugins/guardrails/hooks/hooks.json
  - plugins/guardrails/hooks/askq-humanize.sh
  - plugins/bootstrap/config/manifest.json
  - plugins/bootstrap/hooks/hooks.json
  - plugins/bootstrap/hooks/stop-prose-ceiling.py
  - plugins/bootstrap/hooks/stop-forma-relato.py
  - plugins/bootstrap/lib/conformance.py
  - plugins/bootstrap/output-styles/clean-style.md
verified-by:
  - scripts/sync-shared.sh
  - scripts/hook_contract.py
  - plugins/bootstrap/lib/test_conformance.py
  - plugins/bootstrap/hooks/test_bootstrap_hooks.sh
  - plugins/project-doc/lib/test_pattern_check.py
  - plugins/project-doc/lib/test_journal.py
  - plugins/project-doc/lib/test_organism.py
  - plugins/project-doc/lib/test_graph_map.py
  - plugins/project-doc/lib/test_doc_lint.py
  - plugins/intent-guard/lib/test_ledger.py
  - plugins/visual/lib/test_plan_state.py
  - plugins/visual/lib/test_visual_page.py
  - plugins/visual/hooks/test_exitplan_gate.sh
  - plugins/handoff/lib/test_handoff_skill.py
  - .claude/hooks/test_release_gate.sh
  - plugins/branches/lib/test_branch_state.py
  - plugins/guardrails/lib/test_askq_lint.py
  - plugins/slides/lib/test_md2deck.py
doc-sig: pedro-plugins/marketplace.json@gen=3.8#20cbab3f
---

# Arquitetura — pedro-plugins

## 1. Visão geral

Marketplace **público** de plugins do Claude Code, distribuído por git e catalogado num
único manifesto (`.claude-plugin/marketplace.json`). Não é uma aplicação: é uma
**biblioteca de comportamento** — skills (instruções em Markdown), hooks (shell + Python
stdlib) e alguns motores auxiliares (um daemon Node, um extrator de transcript).

⚠️ **A história do git foi recriada hoje.** `git log --oneline` nesta rodada devolve
**uma linha só**, um commit órfão, sem ancestral comum com a história anterior
[confirmado — saída do run]:

```
2587006 pedro-plugins: marketplace de plugins para Claude Code
```

Consequência que muda decisão: **todo hash citado em doc antiga deixou de resolver**, e
todo mecanismo que usa `git log`/`git diff` contra um SHA gravado (o `last_commit` do
ledger do journal, o `generated-commit:` do frontmatter, o `green_tree_hash`) cai no
caminho de cold-start em vez de no caminho de delta. Os módulos tratam isso — `journal.py:_commit_reachable`
e `pattern_check.py:_git_commit_resolves` existem exatamente para o SHA órfão — mas o efeito
prático é que a primeira rodada depois do reset re-minera tudo. [confirmado — leitura dos dois
símbolos + `git log` do run]

Ciclo de vida:

```
edita plugins/<nome>/            (skill, hook, lib)
  → bump plugins/<nome>/.claude-plugin/plugin.json .version
  → espelha a mesma version em .claude-plugin/marketplace.json
  → bash scripts/sync-shared.sh   (se tocou _shared/)
  → git commit                    (interceptado por .claude/hooks/release-gate.sh)
  → git push
  → cliente: claude plugin install <nome>@pedro-plugins  /  update
```

Não há build, bundler, lockfile nem CI — `.github/` tem um arquivo só,
`copilot-instructions.md`, que é ponteiro de doc, não workflow [confirmado — `find .github -type f`].
O **único passo de "compilação"** é o vendoring de `_shared/` (§7): copiar arquivos-fonte
compartilhados para dentro de cada plugin consumidor, porque o Claude Code isola plugins
na instalação. [confirmado — cabeçalho de `scripts/sync-shared.sh`]

## 2. Números derivados mecanicamente neste run

Comandos re-executados agora, na árvore de trabalho sobre `2587006`:

```bash
ls -1d plugins/*/ | wc -l                            # 19
ls -1 plugins/*/.claude-plugin/plugin.json | wc -l   # 19
ls -1 plugins/*/skills/*/SKILL.md | wc -l            # 21
ls -1 plugins/*/hooks/hooks.json | wc -l             # 11
find plugins -path '*/lib/*.py' | wc -l              # 47
python3 -c "import json;print(len(json.load(open('.claude-plugin/marketplace.json'))['plugins']))"   # 19
```

- **19 diretórios de plugin · 19 manifestos · 19 entradas no catálogo · 21 skills ·
  **11** plugins com hooks · 47 arquivos `.py` em `lib/`.** [confirmado — os seis comandos
  re-rodados nesta passada de `/doc-touch`; **os dois que mudaram foram o de `hooks.json`,
  de 10 para 11, e o de `lib/`, de 32 para 47**.]
  ⚠️ **O salto de 15 arquivos em `lib/` é quase todo CÓPIA, não código novo**: **9** deles
  são a mesma `regua_texto.py` vendorada, uma por plugin que emite texto (§7). Contar
  `lib/*.py` mede o vendoring junto com o código — a medida de código próprio é
  `find plugins -path '*/lib/*.py' ! -name regua_texto.py ! -name collect_engine.py`.
- **38 registros de hook — 37 do tipo `command` + 1 do tipo `prompt`**, em **37 scripts
  distintos** [confirmado — varredura própria dos 11 `plugins/*/hooks/hooks.json` neste run,
  e `python3 scripts/hook_contract.py` imprime a mesma medida: *"Contrato dos hooks — 38
  registros, 37 scripts distintos"*].
- 21 skills em 19 plugins porque **`graphify-guard` não tem `skills/` nenhum** (é 100% hook —
  o glob `plugins/graphify-guard/skills/*/` não casa nada) e **`project-doc` tem quatro**
  (`design-md`, `doc-touch`, `project-doc`, `start-doc`).
- Régua de fronteira: **quem manda é `marketplace.json`, não `ls plugins/`**. Diretório fora
  do catálogo não é plugin distribuído. Hoje os dois lados batem — 19 × 19, e o
  `conformance.py:check_catalogo` existe justamente pra acusar quando divergirem (§10.2).
- Linguagens: Markdown (as skills), Bash (hooks), Python 3 **stdlib-only**, Node stdlib
  (um daemon, `plugins/visual/server/visual_server.mjs`), JS vendorado de terceiro
  (`plugins/archify/skills/archify/renderers/**`).
- Sem package manager: não há `package.json` nem `requirements.txt` na raiz.

## 3. Estrutura de diretórios

```
.claude-plugin/marketplace.json   catálogo único — nome, source, version, tags, category
plugins/<nome>/                   19 dirs, todos catalogados
_shared/                          fonte-da-verdade do código compartilhado (6 arquivos)
scripts/sync-shared.sh            o "build": vendora _shared/ → 19 cópias em 14 pastas
scripts/hook_contract.py          mede o contrato dos 38 registros de hook (§11)
scripts/public_repo_check.py      cobra a regra de repo público (checagem H do gate)
scripts/regua_call_check.py       cobra que gerador de página chame a régua (checagem I)
.claude/                          documentação + estado + gate LOCAL deste repo
  ├── CLAUDE.md                   índice de roteamento (marker project-doc:v2)
  ├── docs/                       architecture · patterns · data-stores · durability · runtime
  ├── hooks/release-gate.sh       gate mecânico de commit deste monorepo (10 checks: A–I)
  ├── hook-contract.baseline.json o retrato do contrato dos hooks  ← VERSIONADO
  ├── settings.json               registra o release-gate como PreToolUse(Bash)
  └── .project-doc/  plans/  ata/  intent/  visual/  qa-loop/  HANDOFF*.md
                                  estado local da máquina — TODOS gitignorados (§3.1)
graphify-out/                     knowledge graph — gitignorado inteiro, regenerável
AGENTS.md · GEMINI.md · .cursorrules · .windsurfrules · .github/copilot-instructions.md
                                  ponteiros finos p/ outras IAs
docs/superpowers/                 material de terceiro (gitignorado)
pi-plugins/                       ⚠️ CÓPIA UNTRACKED e gitignorada — não é fonte
```

### 3.1 O que fica fora do controle de versão

O `.gitignore` é organizado **por critério, não por ferramenta**, e o critério está escrito
no topo do próprio arquivo [copiado literal]:

> *"Este repositório é PÚBLICO e é instalado por terceiros. A pergunta que decide se um
> arquivo entra não é 'isso é útil?' — é 'isso pertence a QUEM INSTALA, ou pertence a QUEM
> ESCREVEU?'. Só o primeiro sobe."*

A seção 1 do arquivo (`REGISTRO DE TRABALHO`) enumera o que sai por esse critério. As
entradas verificadas nesta rodada com `git check-ignore -v`, com a linha exata de cada uma
[confirmado — saída do run; `git ls-files` sobre esses caminhos volta **0**]:

```
.gitignore:17  .claude/ata/
.gitignore:18  .claude/plans/
.gitignore:21  .claude/.project-doc/
.gitignore:44  graphify-out/
.gitignore:71  pi-plugins/
```

A mesma seção 1 também lista `.claude/HANDOFF*.md`, `.claude/BRIEFING-*.md`,
`.claude/intent/` e `docs/superpowers/`.

⚠️ **Duas consequências mecânicas:**

- **Estado que era garantido pelo `git` depende só do disco.** O `journal.py` segue
  append-only, mas o que o protegia de sumir era o commit. Quem for medir cobertura de
  backup destes caminhos: eles não têm mais a rede do `origin` (ver `durability.md`).
- **O `scope:` dos docs aponta só pra arquivo versionado**, então nada disso entra na conta
  de staleness — o que sumiu foi a fonte, não a régua.

## 4. Anatomia de um plugin

```
plugins/<nome>/
├── .claude-plugin/plugin.json    OBRIGATÓRIO — name, version, description, author{}, homepage
├── skills/<skill>/SKILL.md       frontmatter YAML: name + description (o gatilho)
│   └── references/*.md           material carregado sob demanda pela skill
├── hooks/hooks.json              OBRIGATÓRIO estar em hooks/ — na raiz é ignorado em silêncio
│   └── *.sh | *.py               os scripts, referenciados por ${CLAUDE_PLUGIN_ROOT}/hooks/…
├── lib/*.py                      motor Python stdlib
├── config/                       dados versionados (só bootstrap: manifest.json,
│                                 settings-defaults.json, CLAUDE-global.md)
├── output-styles/*.md            output style distribuído pelo plugin (só bootstrap)
└── server/                       daemon (só visual: visual_server.mjs)
```

`plugin.json` real, copiado de `plugins/bootstrap/.claude-plugin/plugin.json`:

```json
{
  "name": "bootstrap",
  "version": "1.8.5",
  "description": "…",
  "author": { "name": "pedroberaldo87", "email": "tools@viustudio.com.br" },
  "homepage": "https://github.com/pedroberaldo87/pedro-plugins",
  "license": "GPL-3.0"
}
```

`author` **tem que ser objeto** — string é rejeitada pelo schema e bloqueia o install em
silêncio. [inferido — os `plugin.json` lidos usam objeto; a rejeição do schema não foi
exercitada nesta sessão]

Todo caminho dentro de `hooks.json` usa `${CLAUDE_PLUGIN_ROOT}` (literal, copiado dos
`hooks.json` lidos). O gate LOCAL deste repo, em `.claude/settings.json`, usa a outra
variável — `$CLAUDE_PROJECT_DIR` — porque não é um plugin [copiado literal do arquivo]:

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

Saída desta rodada (nome · versão · skills · tem hook):

```
archify         2.11.0  [archify]                                        -
bootstrap       1.10.0  [setup]                                          HOOKS
branches         1.3.0  [branches]                                       HOOKS
context-guard    1.3.4  [setup]                                          HOOKS
fallow           1.2.0  [fallow]                                         -
graphify-guard   1.2.0  [] (sem skills)                                  HOOKS
grill-me         1.1.0  [grill-me]                                       -
grill-with-docs  1.1.0  [grill-with-docs]                                -
guardrails       1.7.0  [setup]                                          HOOKS
handoff          1.8.7  [handoff]                                        HOOKS
improve          1.0.3  [improve]                                        -
intent-guard     0.6.0  [intent-guard]                                   HOOKS
principles       1.0.3  [principles]                                     -
project-doc     3.21.0  [design-md, doc-touch, project-doc, start-doc]   HOOKS
qa-loop          1.8.2  [qa-loop]                                        -
ship             1.4.0  [ship]                                           HOOKS
slides           1.5.0  [slides]                                         -
sovai           1.11.3  [sovai]                                          HOOKS
visual          1.19.1  [visual]                                         HOOKS
```

**Treze dos 19 plugins foram bumpados nos dois commits desta rodada** — `bootstrap`,
`branches`, `fallow`, `graphify-guard`, `grill-me`, `grill-with-docs`, `guardrails`,
`project-doc`, `qa-loop`, `ship`, `slides`, `sovai` e `visual` [confirmado —
`git diff --name-only … -- 'plugins/*/.claude-plugin/plugin.json'` devolve 13 caminhos].
Em **9** deles o bump não veio de código próprio: veio da cópia vendorada de
`regua_texto.py`, a régua de forma que saiu do `visual_page.py` e virou `_shared/` (§7).

⚠️ **Vendorar código compartilhado tem um custo de release que não é óbvio**: a cópia mora
DENTRO do plugin, então mexer em `_shared/` não é uma publicação — são N. Cada consumidor
precisa de bump próprio, senão o cliente segue com a régua velha.

As 19 versões batem com o campo `version` da entrada correspondente em
`.claude-plugin/marketplace.json` [confirmado — comparação mecânica das duas fontes rodada
nesta sessão: `OK 19 entradas`, nenhum `MISMATCH`. É o mesmo par que o gate B+C do
`release-gate.sh` checa].

Terceiros vendorados como plugin próprio: `grill-me` e `grill-with-docs` declaram
`author: {name: "Matt Pocock", homepage: "https://github.com/mattpocock/skills"}` no
`marketplace.json` [confirmado — leitura do catálogo]. `archify` é vendorado de terceiro
[relatado — a atribuição vivia em mensagem de commit da história antiga, que não existe mais
neste repo; o `marketplace.json` de hoje não carrega campo `author` nessa entrada].

## 6. Os 11 plugins com hooks — evento por evento

Inventário gerado neste run lendo os 11 `plugins/*/hooks/hooks.json`
(`evento[matcher] → script (timeout)`):

```
bootstrap        (3 eventos, 5 hooks)
  SessionStart[*]                    → session-sync.sh              (sem timeout)
  PostToolUse[Bash]                  → post-plugin-command.sh       (sem timeout)
  Stop[*]                            → stop-prose-ceiling.py        (10s)
  Stop[*]                            → stop-regua-relato.py         (10s)   ← novo
  Stop[*]                            → stop-forma-relato.py         (30s)

branches         (2 eventos, 2 hooks)
  SessionStart[*]                    → sessionstart-branches.sh     (15s)
  PostToolUse[Bash]                  → posttooluse-push-branch.sh   (15s)

context-guard    (2 eventos, 2 hooks)
  SessionStart[*]                    → context-guard-reset.sh       (5s)
  PostToolUse[*]                     → context-guard.sh             (5s)

graphify-guard   (2 eventos, 2 hooks)
  SessionStart[*]                    → sessionstart-graphify.sh     (10s)
  PreToolUse[Grep|Glob|Bash]         → pretooluse-graphify-guard.sh (10s)

guardrails       (2 eventos, 5 hooks)
  PostToolUse[Edit|Write]            → lint-and-typecheck.sh        (30s)
  PreToolUse[Agent]                  → hook type "prompt" (classificador LLM inline) (15s)
  PreToolUse[Edit|Write]             → scope-cop.sh                 (25s)
  PreToolUse[AskUserQuestion]        → askq-humanize.sh             (10s)
  PreToolUse[Edit|Write]             → pretooluse-artefato-regua.py (10s)   ← novo

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

sovai            (1 evento, 1 hook)                                         ← novo
  PreToolUse[Agent]                  → pretooluse-sovai-motor.sh    (10s)

visual           (3 eventos, 4 hooks)
  SessionStart[*]                    → sessionstart-plan.sh         (10s)
  Stop[*]                            → stop-plan-status.sh          (15s)
  Stop[*]                            → stop-anuncio-sem-acao.py     (20s)
  PreToolUse[ExitPlanMode]           → pre-exitplan-visualize.sh    (10s)
```

Observações de arquitetura:

- **O `bootstrap` tem TRÊS hooks no mesmo evento `Stop`**, e a divisão é por eixo medido, não
  por acaso: `stop-prose-ceiling.py` mede **volume** (quantas linhas de prosa),
  `stop-regua-relato.py` mede **os bullets** (a régua de forma, §7.4) e `stop-forma-relato.py`
  julga o que regex não alcança, chamando um modelo. Os dois primeiros custam zero token e
  rodam em todo turno; o terceiro **só roda quando a resposta é um relato**. A divisão está
  escrita no cabeçalho do do meio, literal: *"teto de prosa -> VOLUME (quantas linhas) / esta
  regua -> os BULLETS"*. Detalhe em §10.2. [confirmado — `plugins/bootstrap/hooks/hooks.json`
  tem os três no array `Stop`, e os três arquivos existem em `plugins/bootstrap/hooks/`]
- `guardrails` é o único que usa `"type": "prompt"` (classificador LLM inline no `hooks.json`,
  sem script) — os outros **37** são `"type": "command"`, num total de **38 registros**
  [confirmado, varredura própria neste run; bate com `scripts/hook_contract.py`, que imprime
  *"38 registros, 37 scripts distintos"*].
- **A régua de forma é cobrada por uma PORTA e uma REDE, e nenhuma das duas alcança o que a
  outra alcança.** A porta (`guardrails/hooks/pretooluse-artefato-regua.py`, PreToolUse
  `Edit|Write`) nega **escrever** `.md`/`.html` com prosa corrida dentro de `.claude/visual/`
  ou `.claude/reports/` — vê arquivo, nunca vê o terminal. A rede
  (`bootstrap/hooks/stop-regua-relato.py`, Stop) mede o relato **digitado no terminal** — vê
  o terminal, nunca vê arquivo. O cabeçalho da porta registra por que são duas e não uma:
  *"os dois alcançam coisas diferentes e nenhum alcança as duas… ficar com um só deixaria
  metade do requisito sem lastro"*. Alcance da porta é estreito de propósito: doc, código e
  config ficam fora, *"a régua governa artefato de LEITURA, não todo texto do repositório"*.
  Kill-switches: `ARTEFATO_REGUA=0` e `REGUA_RELATO=0`. [confirmado — leitura dos dois
  cabeçalhos; `python3 plugins/guardrails/hooks/test_artefato_regua.py` → *"23 checks ok, 0
  falhas"* neste run]
- **Dois plugins gateiam o `Agent`, e eles não concorrem — respondem a perguntas opostas.**
  O do `guardrails` é o classificador LLM e existe pra **proteger** Agent Teams: ele nega
  sub-agente avulso **quando o prompt pede Agent Teams**, e libera explicitamente *"tarefa
  one-off sem team_name"*. O do `sovai` (`pretooluse-sovai-motor.sh`, novo em 2026-08-02) nega
  **todo** disparo de sub-agente enquanto a missão estiver armada, porque ali o motor é a tool
  `Workflow`. A distinção importa: a SKILL do sovai afirmava que o guard do `guardrails` a
  protegia, e a regra 3 dele fazia o oposto — prosa descrevendo mecanismo ausente não dá erro.
  O gate do sovai lê um sinal por sessão (`~/.claude/sovai/ativo-<session_id>`), tem cap de 3
  negações e kill-switch `SOVAI_GATE=0`. [confirmado — `plugins/sovai/hooks/test_sovai_gate.sh`
  → `OK (20 checks)` neste run]
- **O `AskUserQuestion` é gateável** (`guardrails/hooks/askq-humanize.sh`). O contrato de gate
  está escrito no cabeçalho do próprio arquivo, copiado literal: *canal* `permissionDecision:"deny"`
  em JSON no stdout com exit 0; *cap* 3 devoluções por sessão; *desligar* `ASKQ_GATE=0`;
  *fail-open* sem `jq`, sem `python3`, sem `session_id` ou sem o lint → exit 0 calado. O hook
  **não reescreve** a pergunta — devolve a lista do que faltou e o modelo reescreve. [confirmado
  — leitura do cabeçalho]
- **Três plugins gateiam o `ExitPlanMode` simultaneamente**: `visual`
  (`pre-exitplan-visualize.sh`), `intent-guard` (`plan-gate.sh`) e `project-doc`
  (`pretooluse-plan-gate.sh`). É defesa em camadas deliberada, mas um plano passa por três
  gates independentes. [confirmado — os três `hooks.json`]
- **Marcar-se como "só aviso" é declaração, não inferência.** O `conformance.py:check_hooks_duplicados`
  reconhece o comentário literal `# conformance: default-warn` no script, e hoje há **exatamente
  um** no repo: `plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh`, com a justificativa
  colada na mesma linha — *"o caminho de deny existe, mas só com `GRAPHIFY_DENY=1`"*. A suíte
  `test_graphify_guard.sh` trava a marca com `grep -c`, pra ela não sumir num refactor.
  [confirmado — `grep -rn "conformance: default-warn"` neste run devolve o script + a linha do teste]
- Kill-switches por env var, todos copiados literal dos arquivos: `PLAN_DOC_GATE`,
  `DOC_GUARD_GATE`, `ORGANISM_GATE`, `DOC_TOUCH_SUGGEST`, `VISUAL_GATE`, `PLAN_STATUS`,
  `PLAN_NUDGE`, `SHIP_GATE`, `LINT_GATE`, `ASKQ_GATE`, `SCOPE_COP_GATE`, `BRANCHES_GATE`,
  `GRAPHIFY_GATE`, `GRAPHIFY_DENY`, `HANDOFF_GATE`, `PROSE_CEILING`, `FORMA_RELATO`,
  `ARTEFATO_REGUA`, `REGUA_RELATO`.
  [confirmado — `grep -rhoE` sobre `plugins/`, `scripts/` e `_shared/` neste run, mais leitura
  direta dos dois `.py` do bootstrap, cujos nomes não aparecem em forma `${…}`]
- Diagnóstico de hook: `claude plugin details <nome>@pedro-plugins` mostra `Hooks (N)`. É o
  único jeito de saber se o `hooks.json` foi carregado — `claude plugin validate` passa mesmo
  com o arquivo no lugar errado. [relatado — regra registrada no `CLAUDE.md` do repo; não
  reexecutada nesta sessão]
  ⚠️ **`N` conta EVENTOS, não scripts, e a linha os nomeia.** O `visual` mostra
  `Hooks (3)  SessionStart, Stop, PreToolUse` tanto com um hook de `Stop` quanto com dois —
  o número não distingue. Para provar que um hook NOVO subiu, compare o `hooks.json` dentro
  de `~/.claude/plugins/cache/<marketplace>/<plugin>/<versão>/` com o do repositório.
  [confirmado — 2026-08-02, ao publicar o segundo hook de `Stop` do `visual`]
- ⚠️ **O que roda é uma CÓPIA em cache, chaveada por número de versão**, em
  `~/.claude/plugins/cache/…/<versão>/` — nunca o diretório de trabalho, mesmo com o
  marketplace apontando para um diretório local. Corrigir um arquivo **depois** do bump
  deixa o cache congelado no estado intermediário, e `plugin update` não tem número novo
  para buscar: o conserto exige outro bump. [confirmado — 2026-08-02, o `hooks.json` de
  `visual 1.14.0` ficou com o registro anterior ao ajuste; resolvido em 1.14.1]

### 6.1 O gate de plano (project-doc) — decisão de arquitetura

**Plano não nasce sem documentação.** Dois hooks e um helper compartilhado implementam isso.

**`pretooluse-plan-gate.sh`** (matcher `EnterPlanMode|ExitPlanMode`). Saídas, copiadas do
cabeçalho e do corpo do arquivo:

- **A — projeto sem documentação nenhuma** (nem `CLAUDE.md`, nem `.claude/docs/`):
  `permissionDecision: "deny"` **sempre**, sem cap, mandando rodar `/start-doc`. Comentário
  literal: *"Decisão de projeto (2026-07-26): nega sempre, a não ser que o usuário verbalize
  que é para ignorar. Por isso NÃO há cap de nudges aqui."*
- **B — tem doc, mas não foi lida nesta sessão**: `deny` com cap (`MAX_NUDGES=3`), reusando o
  sentinel `/tmp/claude-doc-guard-${SESSION}-${PHASH}` que o `posttooluse-doc-read.sh` escreve.
  Um `Read` em qualquer `.claude/docs/*.md` libera.
- **C — tem doc e já foi lida**: `exit 0`, silêncio.
- **Quarto caminho: `CLAUDE.md` escrito à mão sem `.claude/docs/`** não cai no caso A (que
  negaria pra sempre com uma mensagem falsa) — vira caso B com cap próprio (`[ "$C" -ge 3 ]`)
  e oferece `/start-doc` + `/project-doc` depois do plano.

**`userpromptsubmit-plan-escape.sh`** (UserPromptSubmit) é o **escape verbal**. Hook não lê a
conversa, então quem ouve a frase é este, e ele grava o sentinel
`/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}` que o gate honra. Tokens copiados do arquivo:

- Libera: `--sem-doc` · `#sem-doc` (garantidos, inequívocos), ou imperativo + doc
  (`ignora/pula/dispensa/desconsidera/esquece a doc`, `segue sem doc`, …).
- Revoga: `--com-doc` · `exige a doc`.
- Três armadilhas travadas por regex, comentadas no arquivo: fronteira de palavra obrigatória
  (`B='(^|[^[:alnum:]])'`, senão *"estava sem documentação"* liberava), `EXTERNAL_RE` (doc **de
  terceiro** — "ignora a doc DO React" — não libera o gate do projeto), e **ambiguidade resolve
  pro lado seguro** (casou os dois ⇒ não libera; quem quer liberar usa `--sem-doc`).

**`lib-project-root.sh`** existe por um motivo cirúrgico, copiado do arquivo: o `PHASH`
(`cksum` da raiz) é a chave dos sentinels em `/tmp`; se dois hooks derivarem a raiz de formas
diferentes, geram chaves diferentes e o sentinel de um nunca é visto pelo outro — falha
silenciosa. `git rev-parse --show-toplevel` devolve o caminho **físico** (`/private/var/…`)
enquanto `posttooluse-doc-read.sh` recorta a **string** do `file_path` (`/var/…`); no macOS
isso são hashes diferentes. **Regra dura do arquivo, literal: "NUNCA canonicalize (nada de
`git rev-parse`, `realpath`, `pwd -P`)"** — a única normalização permitida é tirar a barra
final, porque `/a/b` e `/a/b/` também dão `cksum` diferente.

A ordem de `project_root()` é deliberada: 1º ancestral com `CLAUDE.md`/`.claude/CLAUDE.md`
(casa o PHASH de quem escreve o sentinel de leitura), e só depois marcador de projeto
(`.git`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `.claude`) — que cobre o
caso "projeto sem documentação nenhuma", onde só importa gate e escape concordarem entre si.

**Fail-open só na borda de infra**: sem `jq`, sem raiz resolvível, ou com `doc-detect.sh`
ilegível → `exit 0`. Essa última guarda está comentada no arquivo como achado de revisão: sem
ela, um `chmod 000 doc-detect.sh` fazia um projeto **totalmente documentado** cair no caso A e
ser negado sem cap.

Suíte dedicada: `plugins/project-doc/hooks/test_plan_gate.sh`.

## 7. A engine compartilhada vendorada (`_shared/`)

`_shared/` tem seis arquivos-fonte [confirmado — `ls -1 _shared/` neste run, fora o
`test_regua_texto.py` e o `__pycache__`]:

```
collect_engine.py   green-cache.sh   regua_texto.py
r8-tiers.json       r8_tiers.py      r8-tiers.md  (gerado do json)
```

O porquê do vendoring, copiado do cabeçalho de
`scripts/sync-shared.sh`: *"o Claude Code isola plugins na instalação — só `plugins/<nome>/`
vai pro cache, sem variável cross-plugin. O código compartilhado é COPIADO antes do commit
(o 'build' deste monorepo). Fonte-da-verdade = `_shared/`; as cópias nos plugins são
derivadas."*

O mapa `SPECS` (destino::arquivo), copiado literal:

```bash
SPECS=(
  "plugins/handoff/lib::collect_engine.py"
  "plugins/project-doc/lib::collect_engine.py"
  # O contrato R8: os DADOS (.json) + o servidor (.py) + a vista humana (.md, gerada
  # do json). A skill instalada só enxerga a própria pasta, então a casca lê o tier
  # da cópia local e passa em args — nenhum SKILL.md carimba o valor.
  "plugins/sovai/skills/sovai/references::r8-tiers.json"
  "plugins/qa-loop/skills/qa-loop/references::r8-tiers.json"
  "plugins/sovai/skills/sovai/references::r8_tiers.py"
  "plugins/qa-loop/skills/qa-loop/references::r8_tiers.py"
  "plugins/sovai/skills/sovai/references::r8-tiers.md"
  "plugins/qa-loop/skills/qa-loop/references::r8-tiers.md"
  "plugins/visual/lib::regua_texto.py"
  "plugins/branches/lib::regua_texto.py"
  "plugins/fallow/lib::regua_texto.py"
  "plugins/slides/lib::regua_texto.py"
  # Os emissores de hook: o .sh chama a régua pela linha de comando, e o plugin
  # instalado só enxerga a própria pasta — sem cópia aqui, a régua some em produção.
  "plugins/bootstrap/lib::regua_texto.py"
  "plugins/guardrails/lib::regua_texto.py"
  "plugins/project-doc/lib::regua_texto.py"
  "plugins/ship/lib::regua_texto.py"
  "plugins/graphify-guard/lib::regua_texto.py"
  "plugins/ship/hooks::green-cache.sh"
  "plugins/qa-loop/lib::green-cache.sh"
)
```

**19 cópias, em 14 pastas de destino, de 6 arquivos-fonte** — a `regua_texto.py` sozinha
responde por **9** delas [confirmado — `sed -n '/^SPECS=(/,/^)/p' scripts/sync-shared.sh |
grep -c '::'` devolve `19`; o mesmo recorte com `| sed 's/.*"\(.*\)::.*/\1/' | sort -u | wc -l`
devolve `14`]. É um mapa explícito, não "todos os arquivos em todos os consumidores", porque
consumidores diferentes vendoram arquivos diferentes. `--check` não copia: roda `cmp -s` e sai
1 com `DRIFT: …` se alguma cópia divergir. Verificado neste run:

```
$ bash scripts/sync-shared.sh --check
OK: cópias vendored idênticas a _shared/
```

**`journal.py` NÃO é vendorado** — só `collect_engine.py` é. [confirmado — o `SPECS` acima e
`find plugins -path '*/lib/*.py'`, que mostra `journal.py` apenas em `plugins/project-doc/lib/`]

### 7.1 `collect_engine.py` — a camada de coleta

Concentra tudo que é mecânica de transcript, **sem nenhum julgamento de LLM**:

- **Resolução de workspace** — `resolve_project_root()` sobe até o 1º ancestral que é fronteira
  de projeto. `WORKSPACE_FILES` (copiado literal) = `pnpm-workspace.yaml`, `turbo.json`,
  `nx.json`, `lerna.json`, `go.work`; `MODULE_CONTAINERS` = `apps`, `packages`, `services`,
  `libs`, `modules`. `detect_modules()` + `_module_candidates()` varrem os containers com poda
  backend/frontend.
- **`infer_scope()`** — projeto-raiz dominante dos arquivos editados; devolve `from_edits` e
  `project_root_is_boundary` justamente pra skill saber quando o destino foi chutado pelo cwd
  e precisa de confirmação humana.
- **Descoberta de transcript** — `discover_transcript()` em 3 níveis: `session_id` explícito
  (determinístico, o nome do `.jsonl` **é** o session_id) → sentinel legado por cwd → `.jsonl`
  mais recente do cwd. `discover_all_transcripts()` faz pré-filtro por nome-de-slug e só então
  abre o arquivo pra confirmar o `cwd` real — evita abrir centenas de transcripts à toa.
- **`collect()`** — itens crus por record; marca `gate: True` só no que é fala do humano.
- **`finding_id(text, raw_kind)`** = `sha1(texto completo normalizado + kind)[:16]`. Usa o texto
  **inteiro**, não a âncora truncada — duas falas com o mesmo prefixo colidiriam e a 2ª sumiria
  do journal.

Tolerância a falha explícita: `read_jsonl` usa `errors="replace"` e pula linha JSON corrompida
sem derrubar a rodada.

### 7.2 `green-cache.sh` — cache de suite verde

Registro compartilhado de "a suite passou verde **neste estado exato da árvore**". Feito pra
ser `source`ado. Consumidores nomeados no cabeçalho: Fase Gate do `qa-loop` (grava), `ship §2.5`
(consulta+grava) e o hook `pre-deploy-test-check.sh` do `ship`.

Semântica não-negociável, copiada do cabeçalho:

- Fail-open na direção **segura**: qualquer erro → MISS → a suite roda.
- **Gate vermelho NUNCA grava.**
- Chave = tree-hash do git **incluindo untracked**, via `GIT_INDEX_FILE` temporário +
  `read-tree HEAD` + `add -A` + `write-tree`. `git stash create` e `HEAD + diff` não servem:
  ignoram untracked → falso HIT.
- TTL de 24h **por linha** (epoch gravado no registro, não mtime do arquivo — um mark novo não
  pode ressuscitar registro vencido). Prune de arquivos >7d no mark.

Env vars, copiadas literal: `GREEN_SUITE_DIR` (default `$HOME/.claude/green-suite`) e
`GREEN_SUITE_TTL_SECS` (default `86400`). API: `green_tree_hash`, `green_cache_check`,
`green_cache_mark`; scope é `"full"` ou `"app:<nome>"`, e `full` satisfaz qualquer consulta.

### 7.3 `r8-tiers.json` + `r8_tiers.py` — o contrato de tier virou DADO

Contrato único de "que modelo/effort em cada etapa", compartilhado pelos dois motores
(`/sovai` decompõe→executa→revisa; `/qa-loop` revisa→planeja→conserta). **É tudo Opus** — o
modelo saiu da equação e só o `effort` varia por etapa.

⚠️ **Desde 2026-08-03 a fonte da verdade é o JSON, não o markdown.** O `r8-tiers.md` passou a
ser **gerado** (`r8_tiers.py render`) e **nenhum SKILL.md carimba o valor** — a casca lê o JSON
da cópia vendorada e passa em `args`, e o script usa `args.tiers.executor.effort` em vez de um
literal. O defeito que originou a inversão está medido no cabeçalho do módulo, literal: *"trocar
seis valores custou 45 substituições em dois SKILL.md, três saíram invertidas e duas
sobreviveram a dois verificadores. A causa não era descuido — era o número morar em quinze
lugares."*

Os 6 tiers, lidos do JSON neste run [confirmado — `python3 -c` sobre `_shared/r8-tiers.json`,
`revised: 2026-08-03`, `model: opus`, `api_default_effort: high`]:

```
decompose   high      coordinate  medium    executor   medium
mechanical  low       diagnose    medium    finalize   medium
```

O fundamento, copiado do próprio JSON: *"O guia de migração manda varrer para baixo a partir do
padrão da API, que é `high`"* e *"Effort não encurta resposta — mexer nele move raciocínio, não
tamanho visível"*. Regra por rodada: rodada 1 usa `decompose`; rodadas 2+ usam `coordinate` e
processam só o delta; **CONFIRM e DIAGNOSE são sempre agentes dedicados**, em qualquer rodada.

Três verbos, todos lendo o mesmo JSON — `args` (o dicionário que a casca passa ao Workflow),
`render` (a tabela markdown) e `check` (falha se o markdown divergir do JSON, ou se um SKILL.md
voltar a carimbar um `effort` literal). O `check` é a **checagem A2 do release-gate**
[confirmado — `python3 _shared/r8_tiers.py check` → *"OK: R8 servido de
`_shared/r8-tiers.json`, sem cópia carimbada em SKILL.md"* neste run].

⚠️ **A regex `LITERAL` exige `model:` na mesma linha do `effort:`**, e isso é desenho: sem essa
âncora, o `effort: "low"` que o `/fallow` escreve no relatório dele — que não tem nada com o R8
— seria barrado por um gate de outro assunto.

### 7.4 `regua_texto.py` — a régua de forma, com perfil por artefato

As quatro checagens de forma (≤ 140 caracteres por bullet, uma frase por bullet, sem conectivo
de continuação abrindo, no máximo 6 bullets por bloco) **nasceram dentro do `visual_page.py` e
valiam só para a página**. Saíram de lá em 2026-08-03 porque os outros geradores — plano,
slide, texto de hook, relato do terminal — emitem texto que o mesmo humano lê com a mesma
pressa, e cada um estava livre para inventar a própria forma.

**Perfil, não régua única — e perfil não é exceção.** O cabeçalho é explícito: *"Não existe
perfil frouxo: os quatro cobram as quatro checagens. O que o perfil declara é o que, NAQUELE
artefato, não é redação."* Os cinco:

```
pagina     página, relatório, diagnóstico          140 / 6 bullets
plano      a árvore desenhada pelo programa fica FORA da régua
slide      ≤ 20 palavras por bullet, além do resto
hook       sem markdown (o canal não renderiza); cabeçalho abre com emoji
contexto   200 / 20 bullets — canal `additionalContext`, lido pelo modelo
```

Cada número tem procedência escrita no arquivo: `BULLET_MAX = 140` é *"o teto que o
`plan_state.DESC_MAX` já cobra (máx real medido: 137)"*, `SLIDE_PALAVRAS = 20` é o
`md2deck.STATEMENT_WORDS`, `HOOK_LINHAS = 6` é *"o orçamento do fim de turno
(`stop-plan-status.sh`)"*. O perfil `contexto` é o mais folgado **por eixo declarado**: ele
carrega inventário, e *"inventário cortado esconde item"*.

O consumidor **declara o perfil e não redigita a régua**. O `visual_page.py` hoje tem uma
constante só — `PERFIL = "pagina"` — e importa `erros_de_estilo`; os emissores de hook em Bash
chamam pela linha de comando (`printf '%s' "$MSG" | python3 regua_texto.py --perfil hook -`).
**Quatorze arquivos chamam a régua** neste run — 8 em Python (`import`) e 6 em Bash (a linha
`REGUA="$SCRIPT_DIR/../lib/regua_texto.py"`) [confirmado — `grep -rln` por
`import regua_texto|erros_de_estilo` e `grep -rn regua_texto --include='*.sh'` sobre
`plugins/`, descontando as cópias vendoradas e os testes].

**Duas redes cobram que ninguém escape:**

- **`scripts/regua_call_check.py` (checagem I do release-gate)** — se um `.py` monta página, ele
  tem que chamar o módulo. O sinal é mecânico, não julgamento: literal de `DOCTYPE`, `<html`,
  `<div class=` ou uso de `template.html` de um lado; `import regua_texto` ou `erros_de_estilo`
  do outro. Isenção exige motivo escrito na linha (`# regua-ok: <motivo>`). O gate só olha o que
  ESTE commit traz — **gerador antigo fora da régua não trava ninguém, gerador tocado agora é
  barrado na porta**. [confirmado — `python3 scripts/regua_call_check.py` → *"OK — todo gerador
  de página chama a régua"*, `count: 0`]
- **`plugins/visual/lib/regua_audit.py`** — audita o HTML que **já está no disco** em
  `.claude/visual/`, que o validador do `visual_page.py` nunca alcança (ele só vê spec de página
  que ainda vai nascer). Imprime `arquivo · regra · trecho`, porque *"tem prosa nessas páginas"
  não é achado acionável enquanto ninguém diz QUAL página, QUAL regra e QUAL trecho*. A régua
  **não é redigitada** ali: o texto extraído volta pro `erros_de_estilo`, e o cabeçalho nomeia o
  motivo — *"uma segunda cópia da régua é exatamente o defeito que este módulo existe pra pegar:
  ela divergiria da primeira e cada lado ficaria coerente sozinho"*. Limite declarado: bloco
  `raw_html` não deixa marca no HTML renderizado, então não há como isentá-lo.

## 8. Módulos Python e dependências

Inventário mecânico (`find plugins -path '*/lib/*.py'` → **47 arquivos**), agrupados. As
**9 cópias de `regua_texto.py`** aparecem à parte porque são vendoring, não código do plugin
(§7.4):

```
plugins/project-doc/lib/   collect_engine.py (vendorado) · journal.py · pattern_check.py
                           organism.py · graph_map.py · doc_lint.py
                           + test_{journal,pattern_check,organism,graph_map,doc_lint,
                                   start_doc_skill}.py
plugins/handoff/lib/       collect_engine.py (vendorado) · extract_ata.py
                           + test_handoff_skill.py
plugins/intent-guard/lib/  ledger.py + test_ledger.py
plugins/fallow/lib/        audit.py · report.py + test_report.py
plugins/visual/lib/        plan_state.py · cobertura.py · visual_page.py · regua_audit.py
                           + test_{plan_state,cobertura,visual_page,regua_audit}.py
plugins/slides/lib/        md2deck.py + test_md2deck.py
plugins/branches/lib/      branch_state.py + test_branch_state.py
plugins/guardrails/lib/    askq_lint.py + test_askq_lint.py
plugins/bootstrap/lib/     conformance.py + test_conformance.py
plugins/qa-loop/lib/       test_qa_loop_skill.py          (+ green-cache.sh, vendorado)
plugins/sovai/lib/         test_sovai_skill.py

regua_texto.py (vendorado) em bootstrap · branches · fallow · graphify-guard · guardrails
                           · project-doc · ship · slides · visual   ← 9 cópias idênticas
```

**Grafo de import interno** (derivado de leitura dos imports não-stdlib — todos lazy, dentro de
função, exceto o do `doc_lint`):

```
doc_lint.py      → pattern_check   (import de topo: _extract_frontmatter_and_body, …)
pattern_check.py → organism        (find_organism, costuras_for_path)
pattern_check.py → journal         (touch_plan lê journal.load_ledger → last_commit)
journal.py       → collect_engine  (try/except ImportError → HAVE_ENGINE, degrada sem tier 4)
organism.py      → yaml (PyYAML)   (try/except ImportError → mini_yaml stdlib)
plan_state.py    → cobertura       (import lazy em 5 pontos: _requisitos_do_projeto,
                                    cmd_cobertura, brief_lines, _render_valor, _html_valor)
visual_page.py   → regua_texto     (import de TOPO, via sys.path.insert do próprio dir —
plan_state.py    → regua_texto      a cópia vendorada mora ao lado; ver §7.4)
branch_state.py  → regua_texto
md2deck.py       → regua_texto
regua_audit.py   → regua_texto
```

⚠️ **A aresta pra `regua_texto` é a única que atravessa plugin**, e ela só funciona porque a
cópia mora dentro de cada `lib/`. O `sys.path.insert(0, dirname(__file__))` no topo dos
importadores existe por isso: **não há import cross-plugin no Claude Code**, e um
`from _shared.regua_texto import …` quebraria em toda máquina que instalou o plugin.

Os dois `try/except ImportError` são a mesma decisão de arquitetura: **stdlib-puro é requisito,
não preferência**. `journal.py` redefine `anchor_of`/`finding_id` idênticos ao `collect_engine`
quando ele falta, com comentário explícito de que qualquer divergência re-chavearia o journal.
`organism.py` traz um parser YAML de subconjunto testado **por paridade com PyYAML** — e que
**levanta erro** em construção fora do subconjunto, nunca produz parse errado silencioso.

### 8.1 `journal.py` — journal append-only + scrubber

- **Estado**: `.claude/.project-doc/findings.jsonl` (eventos) + `ledger.json`
  (`mined_sessions` como `{sid: mtime}`, `last_commit`, `distilled_hashes`).
- **`fold(events)`** é o estado vivo, e é um god node do grafo (§9): `discovered` cria,
  `invalidated` mata (sem apagar), `curated` sobrepõe o texto. Um id invalidado **permanece
  morto** mesmo que reapareça num `discovered` posterior — a morte é definitiva até uma
  curadoria explícita revivê-lo. [confirmado — leitura da função]
- **Delta de duas direções**: forward = sessões novas/que cresceram + commits novos; backward =
  `git diff` (working tree ∪ staged ∪ `last_commit..HEAD`) cruzado com as `anchors` → marca
  `stale`. **O lib nunca auto-invalida** — re-validação é julgamento do agente.
- **`self_path_match()`** trava o falso-positivo do monorepo: basename puro sem `/` só casa se
  **exatamente 1** arquivo mudado tem aquele nome.
- **Robustez de git**: `_commit_reachable()` — um rebase/amend órfã o `last_commit` e
  `git log orfão..HEAD` sai 128, perdendo todos os commits; o código trata como cold-start.
  ⚠️ Depois do reset de história desta rodada é exatamente esse ramo que vale.
- **Scrubber em 4 camadas**, a barreira entre conversa-verbatim e git: (1) estruturado
  (PEM → connection string → JWT → prefixos de provider), (2) `chave=valor` de uma linha +
  pares JSON aninhados, (3) prosa (palavra-sinal + token de alta entropia), (4) na dúvida,
  marca `‹revisar?›` — preserva, não vaza. Política escrita no arquivo: **nomes e contexto SIM,
  valores NÃO**; host/IP/porta/path/sha/uuid preservados. O valor vai pro cofre e o doc fica
  com `‹cofre:LABEL:hash8›`.
- **Cofre**: `PROJECT_DOC_COFRE_DIR` (override explícito) > iCloud
  (`~/Library/Mobile Documents/com~apple~CloudDocs/Cofre`) > fallback local
  `.claude/secrets/_local_cofre`. `ensure_gitignore()` roda **antes** da escrita, porque no
  fallback o cofre cai dentro do repo.

### 8.2 `pattern_check.py` — o contrato de "doc no padrão"

`CURRENT_GEN = "3.8"` (copiado literal). Cinco invariantes de disco, do docstring: (a) markers
`<!-- project-doc:v2 gen=X -->` e `:end` no `CLAUDE.md`, (b) frontmatter YAML em todo
`.claude/docs/*.md`, (c) `findings.jsonl` existe, (d) linha `doc-sig:` no frontmatter,
(e) `gen_found == CURRENT_GEN`.

`sig(docfile)` = `"<project>/<scope_basename>@gen=<CURRENT_GEN>#<sha256(body)[:8]>"`. **O hash8
é do corpo e independe da gen; só o rótulo `@gen=` vem do código** — daí a armadilha: `--sig`
sempre carimba o `CURRENT_GEN` do código. É por isso que existe `doc_set_gen()` (lê a gen do
MARKER do `CLAUDE.md`) e que `restamp()` reimpõe essa gen sobre a sig antes de gravar.
[confirmado — `sig()` usa `CURRENT_GEN` incondicionalmente; `restamp()` faz
`re.sub(r"@gen=[^#]*#", …)` com a gen do doc-set]

`restamp()` é o verbo que resolve um problema de ovo-e-galinha nomeado no próprio docstring:
**um doc não consegue citar o commit que o contém**. Quando código e doc entram no mesmo commit,
o carimbo só pode apontar pro anterior, e a janela de staleness enxerga a própria mudança que a
doc descreve. Três regras vieram de defeito: gen do DOC-SET (não do código), `doc-sig`
recomputada do corpo **depois** do frontmatter final, e **doc autoral é intocável**
(`authored-by: human` é pulado). Falha ALTO: sem `HEAD` resolvível não escreve nada
(*"carimbo pela metade é pior que carimbo velho"*).

Camadas por cima do contrato:

- **`scope_staleness()`** — ternário `fresh|stale|unknown`, **nunca finge fresco**. Usa
  `generated-commit:` (precisão de commit) quando resolvível, senão a janela por `generated:`.
  `git log` com falha devolve `None` (unknown), não set vazio.
- **`_scope_entries()`** (god node) — normaliza as entradas do scope pra root-relativo POSIX,
  aplica o fallback de módulo e filtra "açúcar humano" via `_looks_like_path()`. O parâmetro
  `field=` deixa ler `verified-by:` com a MESMA normalização — o comentário do arquivo diz por
  quê: *"sem isso o consumidor teria que reimplementar o split + fallback de módulo, e é
  reimplementação de função barata que deriva em silêncio"*.
- **`_extract_frontmatter_and_body()`** (god node) — a fatiadora `---\n…\n---\n` usada por
  `sig`, `restamp`, `scope_staleness`, `_scope_entries` e pelo `doc_lint`. Sem frontmatter
  devolve `('', conteúdo inteiro)`, então nada quebra em arquivo solto.
- **`docs_for_paths()` / `touch_plan()`** — o **índice inverso do scope**, base do `/doc-touch`:
  dado o diff, quais docs cobrem quais arquivos. `touch_plan` devolve `already_current` (doc mais
  novo que os arquivos que o afetam), `seam_review` (costuras tocadas → blast-radius),
  `unscoped_new`, `dead_scope` e `last_full_age_days`.
  - **`verified-by:` é excluído do `unscoped_new`** de propósito: uma suíte pertence ao
    `verified-by` do doc que ela prova, nunca ao scope — senão o doc viraria stale a cada edição
    de teste e a escalada touch→FULL dispararia sempre que nascesse um `test_*`.
  - **`last_full_age_days`** é o que dá autonomia de touch-vs-FULL a quem chama. O FULL é o
    **único** que avança `ledger.last_commit` (o touch é read-only nele), então a data desse
    commit *é* a data do último FULL. `None` = não resolvível — o consumidor trata como "não
    sei", nunca como "recente".

### 8.3 `organism.py` — costuras de monorepo

Parser + query engine do `.claude/organism.yaml`, que é **dado curado**: o módulo só lê e
responde três perguntas (`match`, `marker`, `verify-cite`). Princípio escrito no cabeçalho:
**"SISTEMA afirma, agente refuta"** — o módulo produz a afirmação (o que o path toca) e o gate
exige que a refutação cite algo real. Fail-open na borda: sem `organism.yaml`, `match` devolve
`[]` e o hook deixa passar. `classify_doc()` e `census()` sustentam a conformação de organismo
(§8.2 do `runtime.md`).

### 8.4 `graph_map.py` — o grafo destilado pra casca

Destila `graphify-out/graph.json` num mapa compacto que dirige a leitura profunda da skill.
Decisões que importam, copiadas do arquivo:

- `STRUCTURAL_RELATIONS = {"contains", "defines", "method"}` — relação estrutural vira ruído no
  ranking de importância, então o **fan-in semântico** a exclui; o fan-in total fica exposto à parte.
- `build_map(..., top_files=40, top_gods=60)` — o corte de god nodes é **teto do programa**, não
  medição do repo, e o `god_ids` é derivado **depois** do corte pra `files[].god_nodes` bater com
  a lista exibida.
- `GENERIC_COMMUNITY_MIN = 4` — nome de comunidade repetido em 4+ comunidades é metadado
  repetido, não módulo; vai pra `generic_communities`.
- Sem grafo, devolve `{"available": false}` e sai **0**: *"ausência de grafo NÃO é erro (degrada
  gracioso)"*.

### 8.5 `ledger.py` (intent-guard) — caderno de pedidos

Caderno append-only dos pedidos verbatim do usuário, `1 JSON/linha` em `ledger.jsonl`, com
quatro eventos: `raw`, `classify`, `verdict`, `baixa`. Estado vivo = `fold` dos eventos, mesma
forma arquitetural do `journal.py`.

- **`fold` devolve DUAS listas de vivos, não uma** (`0.6.0`): `live` são os pedidos e as
  correções — o que **conclui** e portanto pode ser cobrado por veredito; `standing` são as
  entradas de classe `restricao`, que não concluem porque valem enquanto valerem. O comentário
  do arquivo dá o motivo dos dois lados: misturada aos pedidos a restrição *"nunca saía da lista
  de 'a fazer' e dava a impressão de trabalho parado"*, e o gate cobrava dela um veredito
  *"impossível: o cumprimento dela na conversa não é auditável por mim, por desenho"*. O retorno
  é `{"pending", "live", "standing", "entries"}`, e **todo consumidor que cobra lê só `live`** —
  `ledger.py:audit_check`, `ledger.py:apply_audit`, `ledger.py:cmd_verify` (inclusive o contador
  `remaining`) e a lista VIVOS do `ledger.py:cmd_status`. O `standing` aparece num bloco
  separado, rotulado *"COBRANÇAS PERMANENTES (N) — não concluem, então não entram na conta acima"*.
  [confirmado — leitura de `fold` e mapeamento mecânico dos 7 usos de `["live"]` para as funções
  que os contêm, neste run]
- **Restrição vira CONTAGEM, não lista de pendência** — `ledger.py:furos_da_regua` conta quantas
  vezes a régua de forma foi furada, lendo dois logs append-only: `~/.claude/state/prose-ceiling/bypass.log`
  (o guarda mecânico do teto de prosa) e `~/.claude/state/forma-relato/batidas.log` (o juiz de
  forma, contando só `motivo == "julgou"` com veredito diferente de `passa`). Devolve
  `(total, novos, fontes, marca)` — os dois números saem do mesmo log, então não é preciso
  escolher entre perder o histórico e perder o que é novo, e `fontes == 0` distingue *"log
  ausente"* de *"zero furo"*. [confirmado — leitura da função]
- **`intent_dir(cwd)`** (god node) é o resolvedor de onde o caderno mora: raiz do git →
  `<root>/.claude/intent`; sem raiz, cai num slug do path absoluto sob `~/.claude/intent/`.
  O ramo que compara `os.path.realpath(cwd) == os.path.realpath(root)` existe pra preservar a
  **grafia** do caminho quando o cwd já é a raiz — mesma classe de problema do `PHASH` do §6.1.
- **`append(d, ev)`** (god node) é a única porta de escrita, e ela grava sob `locked()`
  (`fcntl`) — sessões concorrentes escrevem no mesmo arquivo.
- **`ensure_exclude()`** ignora o caderno em `.git/info/exclude` (ignore LOCAL), **nunca** no
  `.gitignore` versionado do projeto alheio. Usa `git rev-parse --git-path info/exclude` porque
  num worktree o `.git` é um arquivo, não um diretório.
- **`tree_hash()`** + `EXEC_ARTIFACTS` — o veredito de entrega compara estado de árvore, e
  artefato de execução é filtrado pra não invalidar o veredito.
- Escada de custo: `RECIPES = {"git_synced": recipe_git_synced}` — pedido com receita mecânica é
  resolvido por CÓDIGO, sem agente. O juiz só ESCOLHE de um catálogo fechado.

### 8.6 `visual_server.mjs` — o único daemon

Node stdlib puro, HTTP local. Constantes copiadas literal: `PORT = Number(process.env.CLAUDE_VISUAL_PORT || 7755)`,
`HOST = '127.0.0.1'`, `STATE_DIR = ~/.claude/visual-state`, `IDLE_TIMEOUT_MS = 30 min`,
`MAX_BODY_SIZE = 256 KB`, `SESSION_RE = /^[a-zA-Z0-9_-]{4,64}$/`. O CORS é `'*'` com a
justificativa colada no código: *"only listens on 127.0.0.1 so only local contexts reach it;
`file://` shows up as origin `null`, handled by '*'"*.

### 8.7 `plan_state.py`, `cobertura.py`, `visual_page.py`, `md2deck.py` — o HTML sai de programa, não de token

Quatro módulos, uma decisão. O cabeçalho do `visual_page.py` traz a medida que a motivou: as
páginas do `/visual` digitadas pelo modelo custavam **20-31 KB de HTML por página**, algo entre
5 e 8 mil tokens de saída cada; a página de plano, emitida por programa, gasta zero.

- **`plan_state.py`** transforma o plano de implementação em ARQUIVO
  (`.claude/plans/<id>.plan.json`), não em conversa. O argumento está no docstring e é
  estrutural, não de disciplina: todo consumidor re-derivava o plano por LLM, e re-derivação por
  LLM é lossy — encurta, renomeia fase e chuta se já foi executado. A correção: o modelo AUTORA
  uma vez (`init`) e daí em diante só MARCA (`tick`, que **recusa sem prova**, `EVIDENCE_MIN = 8`).
  Quem desenha a árvore é o programa. `PlanError` (god node) é a exceção única de todos os
  verbos; `DESC_MAX = 140` é limite de schema *"porque a linha didática é o produto do arquivo"*.
  O módulo tem **1404 linhas** e **11 subcomandos** — `init`, `tick`, `state`, `render`, `page`,
  `brief`, `cobertura`, `reabrir`, `open`, `close`, `reopen` [confirmado — `wc -l` e
  `grep -c 'add_parser('` neste run devolvem `1404` e `11`].
  - **O `merge` era a causa comum de quatro defeitos, e o conserto é uma regra só: o que o
    `init` não trouxe vem do arquivo.** A versão anterior preservava uma lista fixa de campos no
    nó e apenas `created` e `status` no topo do plano — então o segundo `init` apagava, calado, o
    bloco `requisitos` (a fonte que as tarefas citam), o `closed_at` e o `detail` da fase. Apagar
    de propósito continua possível e agora é uniforme: **declare a chave vazia**. [confirmado —
    `plan_state.py:merge`, laço `for key, valor in stored.items()`]
  - **Apagar a `pendencia` deixou de ser o jeito de destravar o tique**, porque o próprio `merge`
    a ressuscitava e a tarefa travava pra sempre. Quem resolve agora é o REGISTRO: `decidido`
    com uma `escolha` preenchida faz `plan_state.py:cmd_tick` passar, e a pergunta original fica
    no arquivo — é dela que o `reabrir` vive. [confirmado]
  - **`status: "done"` escrito à mão passou a ser recusado no `init`** quando a `evidence` não
    chega a `EVIDENCE_MIN`: o teto da prova é o mesmo dos dois lados, senão o `tick` cobra prova
    e o `init` a contorna. [confirmado — `plan_state.py:erros_do_plano`]
  - **`plan_state.py:le_plano`** é a única porta de leitura de um plano: arquivo ilegível vira
    `PlanError` dizendo QUAL arquivo e QUAL erro, em vez de traceback. Quem LISTA
    (`list_plans`) segue engolindo o arquivo torto, pra que um byte errado não derrube a
    listagem dos outros. [confirmado]
  - **`plan_state.py:_detalhe`** é a regra ÚNICA da linha de baixo do item, lida pelas duas
    vistas e pelos dois formatos: a prova quando o passo está feito, `⛔ falta decidir: …`
    quando uma decisão trava o tique, a linha didática no resto. Enquanto eram duas cópias, a
    pendência era invisível justo na vista em que o dono aprova o plano. [confirmado]
  - **O validador foi partido em dois** porque quem MARCA precisa separar defeito da própria
    tarefa de defeito alheio, e uma exceção derruba tudo junto: `plan_state.py:erros_do_plano`
    **devolve a lista**, `plan_state.py:validate` a levanta como `PlanError`. É essa divisão que
    deixa o `tick` validar sem congelar o plano inteiro por causa de uma tarefa torta (§5 do
    `runtime.md`).
  - **A tarefa ganhou cinco campos**, todos opcionais no schema mas dois deles cobrados em tarefa
    nova (parâmetro `exigir` de `erros_do_plano`): `requisito` (o id do requisito que ela atende,
    **exatamente um** — *"tarefa que atende dois requisitos são duas tarefas: é essa regra que
    torna a tarefa atômica"*), `pronto` (como se prova que terminou), `grupo` (a natureza do
    trabalho), `pendencia` (a decisão que falta, e que **recusa o tique** enquanto nenhuma
    `decidido.escolha` a responder) e `decidido` (o registro da decisão tomada, que `plan_state.py:cmd_reabrir` desfaz
    devolvendo a pergunta ao campo `pendencia`). Teto de tamanho por campo, copiado do código:
    `pronto` e `pendencia` em `DESC_MAX`, `grupo` e `requisito` em 40.
  - **Duas vistas sobre os mesmos itens** — `execucao` (fase → tarefa, a de sempre) e `valor`
    (épico → requisito → grupo → tarefa). A segunda é **derivada, nunca armazenada**: o arquivo
    guarda fase→tarefa e a vista junta com o documento de requisitos. Texto sai por
    `plan_state.py:_render_valor`, HTML por `plan_state.py:_html_valor` — e neste, ao contrário
    do resto do `/visual`, **tudo nasce fechado** em `<details>`, com as marcas de atenção
    (⛔ pendência, ⚠️ bloqueado) somando para cima em `plan_state.py:_marcas` pra que a dobra não
    esconda o problema junto com o resto.
  - **A vista de valor sem eixo passou a DIZER isso em vez de sair vazia.** Medido em 14 planos
    reais: nenhum declara `requisito`, e a vista saía em branco — o que, num plano de 157
    tarefas, afirma por omissão que não há trabalho. `plan_state.py:_sem_eixo` detecta a
    situação (há plano, não há nenhuma tarefa com requisito), a página abre com o aviso e as
    tarefas são desenhadas sob um nó **"sem requisito"**, agrupadas por `grupo`. A lista de ids
    "tarefas sem requisito" some nesse caso, porque a árvore acima JÁ é ela inteira. [confirmado]
  - **`--mode approve --vista valor` é RECUSADO.** O veredito (Manter/Mudar/Remover) mora na
    FASE, e a vista de valor não desenha fase nenhuma: a página saía com a caixa de fechamento,
    os dois botões e ZERO item revisável, e o "Aprovar tudo" devolvia uma aprovação que ninguém
    deu. `plan_state.py:cmd_page` levanta `PlanError` explicando onde aprovar e como só ler.
    [confirmado]
  - **O resumo de fim de turno parou de afirmar prova sem olhar a prova.**
    `plan_state.py:brief_lines` dizia *"cada um com prova anexada"* por construção; hoje o
    trecho só entra depois de `plan_state.py:_com_prova` percorrer os passos feitos e conferir
    a `evidence`. [confirmado]
  - **Onde os requisitos são procurados** — cascata em `plan_state.py:_requisitos_do_projeto`:
    bloco `requisitos` no próprio plano (`_requisitos_do_plano`) → `$PLAN_REQS` → `docs/PRD.md` →
    `docs/REQUISITOS.md` → `{}`. **Nenhum documento não é erro**, é o caso comum — inclusive o
    deste repositório, que não tem PRD. A regra escrita no código: *"o requisito é obrigatório;
    o LUGAR dele é opcional"*.
- **`cobertura.py`** (novo) é o fio entre o requisito e a tarefa, e cabe em **79 linhas**
  [confirmado — `wc -l`]. `cobertura.py:le_requisitos` lê o formato que o dono já escreve à mão
  (`- **S-4.3 Título** · F1 · Art. 6 — corpo. CA: ...`) e devolve `{id: {titulo, ca, ancora, epico}}`;
  `cobertura.py:mapa` cruza com as tarefas do plano e nomeia **quatro estados** — coberto, tarefa
  sem requisito (trabalho que ninguém pediu), requisito sem tarefa (pedido que ninguém planejou)
  e citação a requisito inexistente. O quarto **não é aviso: é erro que recusa gravar**, tratado
  em `plan_state.py:validate`. O docstring traz a medição que originou o módulo: num projeto
  real, 5 de 157 tarefas apontavam para algum dos 77 requisitos escritos — *"silêncio é o estado
  padrão de hoje; este módulo o torna impossível"*. `cobertura.py:resumo` é a linha única que
  todos os consumidores imprimem, pra que um só programa calcule o número.
- **`visual_page.py`** converte seis regras que viviam como prosa na SKILL.md em coisas
  impossíveis de violar — entre elas "nenhum rádio nasce `checked`", "`name` único por item",
  "ordem fixa decisions-box antes de feedback-box" e **"decisão/item sem nenhuma evidência crua
  na página é RECUSADO"**. O motivo escrito: *"prosa apodrece: a cópia do bloco `.decisions-box`
  colada na skill JÁ divergiu do template"*.
  - **O bloco de prova virou `<details>` que NASCE FECHADO**, com a contagem de linhas no
    cabeçalho clicável (`visual_page.py:r_evidencia`). Saída crua longa empurrava a decisão pra
    fora da tela, e a página existe pra decidir, não pra ler log. **Sem exceção por tamanho
    desde 2026-08-02**: a antiga `LINHAS_ABERTO = 6` deixava prova curta nascer aberta, e o dono
    mediu na tela quatro blocos abertos (4, 1, 6 e 3 linhas) que ele não pediu para ver. Sobrou
    uma válvula só: `"aberto": true` no spec força abrir — **revelar mais nunca esconde**, então
    esta é segura de deixar na mão de quem escreve. Bloco vazio não chega aqui: o validador
    recusa evidência sem `output`. [confirmado — `test_visual_page.py`, 3 checks]
  - **`r_artefato()` emite a saída para ver o artefato grande.** A moldura fica pequena de
    propósito no fluxo do documento — artefato em tamanho natural quebra a leitura e empurra a
    decisão pra fora da tela —, e desde 2026-08-02 a barra carrega dois botões escritos pelo
    programa: **tela cheia** (a moldura INTEIRA em fullscreen, com a procedência junto, `Esc`
    volta) e **nova janela**. Três decisões, cada uma por um modo de falha: o link é
    `<a target="_blank">` e não `window.open()` porque bloqueador de popup mata o segundo e a
    página roda em `file://`; `.artefato:fullscreen` traz `background` próprio porque o
    navegador pinta branco por padrão e o tema escuro piscaria; sem Fullscreen API o clique cai
    em abrir-em-aba, nunca fica sem resposta. [confirmado — `test_visual_page.py`, 11 checks]
  - **`erros_de_estilo()` recusa prosa em TODO campo de texto do spec** — título, corpo,
    pergunta, aviso, sumário. Quatro checagens: ≤ 140 caracteres por bullet, uma frase por
    bullet, sem conectivo de continuação abrindo, no máximo 6 bullets por bloco. Estourar é
    `exit 2` **sem escrever a página**, com a lista inteira de erros de uma vez. As regras e a
    calibração estão em `patterns.md §2.7`; o princípio que as gerou, no doc autoral
    `quality-goals.md`. [confirmado — `test_visual_page.py`, 25 checks]
    ⚠️ **Desde 2026-08-03 a régua não mora mais aqui** — ela é `_shared/regua_texto.py` (§7.4),
    e o que sobrou neste módulo é a **declaração de perfil**: uma constante, `PERFIL = "pagina"`.
    A função homônima local continua existindo, mas só delega. O motivo é o mesmo que criou o
    módulo: enquanto a régua vivia dentro do gerador de página, plano, slide e texto de hook
    ficavam livres para inventar a própria forma. [confirmado — `git diff` do commit `5288bc5`
    sobre `visual_page.py`: as constantes e as regexes saíram, entrou o `from regua_texto import`]
  - **`_tri()` dobra o corpo do problema e DERIVA o rótulo do dobrador.** O problema fica
    visível; consequência e proposta nascem fechadas, em `<ul>`. O texto do `<summary>` é o
    primeiro bullet da consequência mais a contagem do resto — promoção de conteúdo, não campo
    à parte, que seria onde amaciar um problema grave. `_placar()` acrescenta a contagem
    agregada no topo, sempre aberta. Medido na mesma página antes e depois: **89% → 46% de
    texto exposto de cara**. [confirmado — `test_visual_page.py`, 22 checks]
  - **`_plural()` existe DUAS vezes** — `visual_page.py:90` e `plan_state.py:727`, mesma
    assinatura, 2 linhas cada [confirmado — `grep -rn '^def _plural' --include='*.py' plugins/`
    devolve exatamente esses dois neste run]. Não é descuido: importar `plan_state` inteiro por
    um formatador de duas linhas custa mais que copiá-lo. Mesma lógica das três cópias de `_e()`
    logo abaixo.
- **`_e()`** (god node) é o escape de HTML, e ele existe **três vezes** no repo —
  `visual_page.py`, `plan_state.py` e `branch_state.py`. São implementações independentes, uma
  por emissor de HTML, não uma função compartilhada. [confirmado — `grep -rn --include='*.py'
  '^def _e\('` neste run devolve os três]

### 8.8 `branch_state.py` — quais branches dá pra apagar

O problema, medido no cabeçalho: **`git branch --merged` mente por omissão** — só enxerga merge
por ancestralidade, e squash-merge (o botão padrão do GitHub) produz sha novo. **`classify()`**
(god node) devolve três categorias: `merged` (o git já reconhece), `equivalent` (conteúdo já na
base por patch-id — exatamente o que o `--merged` perde) e `unique` (tem commit que só existe
ali). A terceira é a razão de o módulo não apagar nada sozinho: *"uma limpeza em bloco mataria
justamente o que você esqueceu de mergear"*. O único verbo que ESCREVE é `prune`, e ele exige
nomes explícitos, cria tag de resgate antes de cada remoção e recusa branch com trabalho
exclusivo. `BASE_FALLBACKS = ("main", "master", "trunk", "develop")`, `PARADA_DIAS = 30`.

### 8.9 `doc_lint.py` — lint mecânico do conteúdo da doc

Verifica afirmações da doc contra o repo real, nas quatro classes que o cabeçalho enumera:
env-var citada que nenhum arquivo lê, hash de commit que não resolve em `git cat-file`, ponteiro
`arquivo:N` morto, e contagem "N itens" seguida de lista com M≠N. Escape hatch: `<!-- lint:ignore TOKEN -->`
inline ou uma linha por token em `.claude/.project-doc/lint-allow.txt`. Roda só sobre o BODY —
o frontmatter fora, porque o hash8 da `doc-sig` confundiria o check de commit.

⚠️ **Depois do reset de história, o check 2 deste lint vira o mais barulhento do repo**: todo
hash citado em doc antiga deixou de resolver. [inferido — o mecanismo foi lido, o lint não foi
executado sobre os docs nesta rodada]

## 9. O knowledge graph como mapa de arquitetura

Medido neste run com `python3 plugins/project-doc/lib/graph_map.py --project-root .`:

```
stats: {'nodes': 3791, 'links': 4961, 'hyperedges_total': 12,
        'communities_named': 30, 'god_nodes': 60}
files listados: 40      hyperedges que passam o filtro: 6
source_file distintos nos nós: 259
built_at_commit: 2587006652a46b1c53272ccf53f117be8d6c634f
```

Como ler esses números:

- ⚠️ **Eles valem para `2587006` e só.** Todo modo que ESCREVE doc roda `graphify update --force`
  antes, então mudam a cada rodada. O que é utilizável é o par número + `built_at_commit`.
- ⚠️ **Os 60 god nodes são o TETO, não uma medição** — `graph_map.py:build_map` corta em
  `top_gods=60`; o número não sobe nem que o repo dobre. Idem `files`, cortado em `top_files=40`.
- ⚠️ **Dos 12 hyperedges do grafo, 6 sobrevivem** ao filtro `hyper_min=0.85`.
- Comunidades nomeadas desta extração incluem `Fallow Report Generation`, `Marketplace Registry
  & Plugin Config`, `Documentation System (CLAUDE.md)`, `Context-Guard & Handoff Bridge`,
  `Graphify-Guard Net`, `Hook Config (PreToolUse)` e `Project-Doc Generator`.
- **É mapa, não verdade** — aponta onde olhar; confirme no código real.

Um god node deste grafo merece leitura como sintoma, não como componente: **`check()`**. Ele
aparece definido em nove arquivos diferentes, todos suítes de teste, e nunca em código de
produção [confirmado — `grep -rn --include='*.py' '^def check\('` neste run devolve
`test_conformance.py`, `test_askq_lint.py`, `test_md2deck.py`, `test_plan_state.py`,
`test_visual_page.py`, `test_journal.py`, `test_graph_map.py`, `test_doc_lint.py`,
`test_pattern_check.py`, `test_branch_state.py`, `test_hook_contract.py`,
`test_public_repo_check.py`]. O fan-in alto dele não é acoplamento: é o **idioma de suíte deste
repo** — sem framework, uma função `check(label, cond)` por arquivo, contador de ok/FAIL e uma
linha de resumo no fim. `areas()` e `_make_project()` são a mesma coisa em escala menor: helpers
de fixture dentro de `test_conformance.py` e `test_pattern_check.py`.

## 10. A receita de instalação — o manifest do bootstrap

`plugins/bootstrap/config/manifest.json` é a receita do que uma máquina nova instala. Chaves de
topo, lidas neste run: `version`, `description`, `marketplaces`, `skills`, `ferramentas_externas`.

Os marketplaces declarados, com quantos plugins cada um traz e quais nascem **desligados**
[derivado mecanicamente do arquivo neste run]:

```
pedro-plugins             19 plugins   desligados: graphify-guard, intent-guard
agent-browser              1
claude-hud                 1
claude-plugins-official   14 plugins   desligados: claude-md-management, explanatory-output-style,
                                                   github, security-guidance, sonatype-guide
obsidian-skills            1
openai-codex               1
ponytail                   1
voltagent-subagents       10 plugins   TODOS desligados
```

O próprio `pedro-plugins` é o **primeiro** item de `.marketplaces` e declara os 19 plugins um a
um — é isso que o `check_catalogo` compara contra o `marketplace.json` (§10.2).

### 10.1 Dependência externa de plugin — a terceira categoria do manifest

`ferramentas_externas.itens` lista binários que **plugins deste marketplace** precisam e que não
são instaláveis via marketplace. Hoje há um item, copiado literal:

```json
{"comando": "graphify", "pacote": "graphifyy",
 "instalar": "uv tool install graphifyy", "alternativa": "pipx install graphifyy",
 "licenca": "MIT", "requerido_por": ["graphify-guard"],
 "porque": "o graphify-guard procura graphify-out/graph.json e redireciona busca cega pro grafo;
            sem o binario ninguem cria esse diretorio e o guarda vira decorativo"}
```

A nota do bloco fixa a política: *"O bootstrap NAO instala sozinho — a skill setup confere e
oferece; o conformance acusa plugin habilitado com dependencia faltando (mesmo padrao do gate
meio-ligado)."* O `conformance.py:check_ferramentas_externas` **só cobra quando o plugin que
precisa está LIGADO** — quem não usa não é incomodado.

#### A statusLine é uma CADEIA de dois elos, e o de trás sai em silêncio

O `claude-hud` já era instalado pelo manifest, como marketplace e plugin. O que faltava era o
tratamento que o `graphify` tem: **alguém acusar quando ele está ligado e não está fazendo nada**.

A cadeia tem papéis distintos, e essa distinção é o cerne [confirmado — `ELOS_STATUSLINE` em
`conformance.py`]:

```
statusLine.command → context-guard-writer.sh   (ESCRITOR: grava o % da sessão)
                       └ encaminha via CLAUDE_STATUSLINE_FORWARD
                          → claude-hud/dist/index.js   (RENDERIZADOR: desenha a barra)
```

🔴 **Perder o escritor não quebra a tela** — e é exatamente por isso que passou. Medido em
2026-08-02 nesta máquina: `context-guard` habilitado, writer fora do comando, e o único
`/tmp/claude-context-pct-*` existente era um **fixture de teste de três dias antes**. Nenhuma
sessão real gravou. O guarda do context-guard depende desse arquivo para disparar; sem ele
nunca disparou, e a barra continuou perfeita o tempo todo.

`conformance.py:check_statusline_meio_ligada` cobra isso. Duas decisões de desenho que valem
copiar [confirmado — `test_conformance.py`, 6 casos]:

- **Procura no comando E no forward.** Olhar só o `statusLine.command` acusaria o renderizador
  toda vez que ele fosse o forward — que é o arranjo normal. Falso-positivo ensina a ignorar.
- **Cada elo carrega o próprio `conserto`**, porque o conserto é diferente por papel: o escritor
  volta com `/context-guard:setup`, o renderizador com `/claude-hud:setup`.

⚠️ **Trocar o `statusLine.command` sem mover o antigo para o forward mata o elo de trás.** Foi a
causa aqui, e o conserto preservou o comando anterior **inteiro** no forward — inclusive o
cálculo de `COLUMNS`, que se perderia se o forward fosse remontado à mão.

### 10.2 O contrato de forma (bootstrap v1.10.0) — regra, mecanismo e verificador

Quatro peças, cada uma cobrindo o buraco da anterior — a (2b) nasceu em 2026-08-03.

**(1) A regra — `output-styles/clean-style.md`.** Frontmatter copiado literal:

```yaml
name: Clean Style
description: Resultado primeiro, prosa com teto, prova colada sem teto. …
keep-coding-instructions: true
force-for-plugin: true
```

O teto está escrito uma vez só, em prosa: *"até 6 linhas de prosa no total — 1 de resultado, até
4 de explicação, 1 de próximo passo. Esse é o único teto de tamanho que existe."* A prova vai
colada em bloco de código e **não conta no teto**. O arquivo também carrega a calibração que o
justifica: 71 respostas aprovadas contra 154 rejeitadas, e *"tamanho, bullets, header e primeira
linha são estatisticamente iguais nos dois grupos — forma não separa"*.

**(2) O mecanismo mecânico — `hooks/stop-prose-ceiling.py`** (Stop, 10s). Zero token. Conta
linhas de PROSA da última mensagem do assistente, tirando bloco de código e linha de tabela, e
bloqueia com `exit 2`. Constantes copiadas literal: `TETO_PADRAO = 6`, `MAX_BLOQUEIOS = 2`.

- **O teto nasce LIGADO.** `PROSE_CEILING_MAX` só AJUSTA o número — `0` ou lixo cai no padrão.
  Desligar exige `PROSE_CEILING=0`, que derruba o hook inteiro e é visível. O comentário registra
  por que a regra é essa: *"em 2026-07-30 este teto foi transformado em opt-in… A variavel nunca
  foi definida, entao o guarda ficou inerte e a primeira resposta seguinte ja estourou. Premissa
  que nasce desligada nao e premissa — e comentario."*
- Além do teto, três verificações sempre ligadas: **retórica no meio** (regex `RETORICA` com
  *"vale notar"*, *"dito isso"*, *"em outras palavras"*, *"deixa eu explicar"*, …), **menu de
  opções no fim** (*"decida e diga qual escolheu"*) e — **novidade desta rodada** — **veredito na
  1ª linha para pergunta fechada**.
- **A regra da pergunta fechada** tem três regexes e a interação entre elas é o desenho:
  `PERGUNTA_FECHADA` casa no FIM do texto do usuário (últimos 200 chars) coisas como
  `confirma|garante|passou|rodou|funciona|resolveu|terminou|fechou|pode|vale|preciso saber`;
  `PERGUNTA_ABERTA` **exclui** o caso em que um pronome interrogativo abre a frase
  (`como|por que|o que|qual|quando|onde|quem|quanto|explica|descreve`), porque *"'como faz pra
  funcionar?' pede explicacao, nao sim/nao — sem esta exclusao o guarda cobrava veredito de
  tudo"*; e `ABRE_COM_VEREDITO` aceita a primeira linha quando ela começa por
  `sim|nao|confirmo|nenhum|zero|passou|falhou|funciona|resolvido|pronto|feito|em parte|parcial|
  ainda nao|confirmado|inferido|depende`. Só reprova quando fechada **e não** aberta **e** a 1ª
  linha não abre com veredito. O comentário nomeia o caso real que a gerou: *"a resposta trouxe a
  varredura inteira, com prova, e nao dizia sim nem nao — e a devolutiva foi 'voce nao me
  respondeu'"*. [confirmado — leitura das três regexes e do bloco `if pergunta and …`]
- **Duas travas de honestidade.** `batida()` registra **TODA execução**, não só as que barram —
  o comentário explica: sem isso *"'o guarda nao rodou' e 'o guarda rodou e aprovou' sao
  indistinguiveis"*. E depois de `MAX_BLOQUEIOS` o hook **desiste** (senão trava a sessão), mas
  grava a desistência em `bypass.log` — teto conhecido, nunca silencioso.
- `CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))`, e o
  comentário marca que é a **MESMA** regra do `lib/conformance.py:CLAUDE_DIR`: com `Path.home()`
  fixo, quem usa `CLAUDE_CONFIG_DIR` teria o hook escrevendo num lugar e o verificador lendo
  noutro — *"e o relatorio dizia 'nenhuma resposta furou o teto' com o teto furado"*.

**(2b) A régua nos BULLETS — `hooks/stop-regua-relato.py`** (Stop, 10s). **Nova nesta rodada.**
Zero token, como o vizinho. O buraco que ela fecha está escrito no cabeçalho: *"o canal do CLI
era o unico fora do alcance da regua… o relato que o modelo digita na resposta chegava ao dono
sem passar por regua nenhuma"*.

- **Divisão de trabalho declarada, pra não haver guarda em dobro**, literal do arquivo:
  *"teto de prosa -> VOLUME (quantas linhas) / esta regua -> os BULLETS (as linhas que abrem
  com •, - ou *)"*.
- **O perfil é `pagina` por DERIVAÇÃO, não por escolha** — o `regua_texto.py` define esse perfil
  como *«página, relatório, diagnóstico»*, e o relato de fim de turno é um relatório. O
  comentário barra explicitamente o outro candidato: **não** é o perfil `hook`, porque aquele
  proíbe `**` e crase por o canal do emissor de hook não renderizar markdown — e o canal do CLI
  renderiza.
- Bloco de código é PROVA e fica fora, como no vizinho. `MAX_BLOQUEIOS = 2` por resposta,
  estado em `REGUA_RELATO_STATE` (default `<CLAUDE_DIR>/state/regua-relato`), kill-switch
  `REGUA_RELATO=0`, fail-open em toda borda de infra.

**(3) O juiz de forma — `hooks/stop-forma-relato.py`** (Stop, 30s). É o
que regex não alcança: *"Nenhum padrao distingue '6 linhas densas' de '6 linhas vazias' — para
isso precisa de um leitor."*

- **Julga só a FORMA, em quatro critérios** nomeados no docstring: `limpeza` (sobra frase que não
  carrega fato?), `clareza` (dá pra agir depois de ler uma vez?), `didatica` (linguagem humana ou
  jargão?), `escaneabilidade` (o olho acha o resultado sem ler tudo?).
- **O gatilho é medido no próprio texto, e é estreito de propósito.** `e_relato()` exige as duas
  coisas: pelo menos um bloco de código (a prova colada) **E** `MIN_PROSA = 2` linhas de prosa
  fora dos blocos. O comentário registra a calibração: *"um relato bom e CURTO — o exemplo
  canonico tem 2 linhas de prosa e 4 de prova. Exigir 4 de prosa deixava passar exatamente os
  relatos que dao certo."* Resposta curta e conversa não chegam ao modelo — *"mandar cada uma
  para um modelo custaria ~4,5s em cada uma delas"*.
- **O veredito é de uma linha só**, formato fechado no prompt: `PASSA` ou
  `REPROVA: <o defeito em ate 12 palavras, no imperativo>`. O prompt manda ser severo — *"na
  duvida entre PASSA e REPROVA, escolha REPROVA"* — e isenta a prova: *"Bloco de codigo e PROVA:
  nao conta como excesso, e a ausencia dele nao reprova."*
- **Anti-recursão explícita.** O subprocesso `claude -p` herdaria os hooks deste marketplace e
  chamaria o juiz de novo, então o filho roda com `FORMA_RELATO="interno"` — que desliga **sem
  sujar o log**. `FORMA_RELATO=0` é outra coisa: é o kill-switch do dono, e esse **grava batida**.
- **FAIL-OPEN em tudo que não for reprovação explícita**: sem `claude` no PATH, timeout
  (`TIMEOUT_S = 25`), `rc != 0`, saída vazia ou veredito ilegível → passa. *"Guarda que trava a
  sessao por infra e pior que guarda nenhum."*
- **Estado com variável própria**, e o comentário diz por quê: `FORMA_RELATO_STATE` existe porque
  *"isolar o teste via CLAUDE_CONFIG_DIR tirava a credencial do `claude -p` junto, e o juiz
  passava a aprovar tudo por fail-open"*. Default: `<CLAUDE_DIR>/state/forma-relato`.
  Modelo: `FORMA_RELATO_MODEL` (default `haiku`).
- **Teto conhecido, medido e escrito no arquivo**: com um `CLAUDE_CONFIG_DIR` sem credencial o
  `claude -p` sai com `rc=1` e "Not logged in", e o juiz aprova tudo em silêncio. O sintoma fica
  na batida como `juiz sem resposta`, e é isso que a checagem (3) abaixo cobra.

**(4) O verificador — `lib/conformance.py`.** Compara o estado VIVO da máquina contra o contrato
versionado, **em modo relatório: nunca escreve nada**. Decisão de projeto no docstring: *"a
ferramenta mostra o desvio, quem le decide."* Sai 0 conforme / 1 com desvio, e nunca bloqueia.

`Report.desvio(area, o_que, evidencia, conserto)` e `Report.conforme(area, o_que)` (os dois god
nodes desta fatia) são o formato único de saída: **todo desvio carrega evidência E o comando que
corrige**, e nenhuma checagem imprime nada por conta própria.

A lista de checagens, copiada literal da constante `CHECAGENS`:

```python
CHECAGENS = [check_plugins, check_claude_md, check_teto_unico,
             check_output_style, check_skills, check_hooks_duplicados,
             check_gates_enganosos, check_teto_rodou, check_juiz_rodou, check_bypass_teto,
             check_ferramentas_externas, check_catalogo]
```

As que carregam decisão de arquitetura:

- **`check_juiz_rodou` — a checagem nova desta rodada.** Lê `<CLAUDE_DIR>/state/forma-relato/batidas.log`
  e existe por um motivo declarado no docstring: *"O juiz de forma e fail-open por desenho: sem
  esta checagem, 'nao esta barrando' e 'nao esta rodando' voltam a ser indistinguiveis — o
  defeito original do teto."* Três saídas: (a) log ausente → *"o juiz de forma nunca executou"*,
  com o conserto apontando pro array `Stop` do `hooks.json` (*"hook fora dele e ignorado em
  silencio, e `claude plugin validate` passa mesmo assim"*); (b) `juiz sem resposta` > `julgou`
  → *"o juiz esta mudo"*, com a causa provável nomeada (credencial, `claude -p` com `rc=1`) e a
  régua de teste `claude -p --model haiku ok`; (c) última batida há mais de 24h → mudo por
  inatividade. **Só cobra de quem tem o `bootstrap` habilitado** — numa máquina sem o plugin não
  há guarda pra rodar, e acusar ali seria desvio inventado. [confirmado — leitura da função
  inteira; a suíte exercita os quatro ramos, ver §13]
- **`check_teto_rodou`** é o gêmeo mecânico, lendo `state/prose-ceiling/batidas.log`, e o
  docstring guarda a medição que criou a categoria: *"uma resposta de 9 linhas passou as 09:21 e
  o primeiro registro de bloqueio no disco era das 09:36… esta checagem chegou a carimbar
  'nenhuma resposta furou o teto' com o guarda mudo."*
- **`check_hooks_duplicados`** compara **por ferramenta**, não por string de matcher (o matcher é
  uma alternância). Do cache só vale a versão mais alta de cada plugin. E **só conta quem
  BLOQUEIA**: `bloqueia()` procura `permissionDecision`+`"deny"` ou `exit 2`, respeita o marcador
  `# conformance: default-warn`, e **assume o pior quando não consegue ler o arquivo**.
  `alvo()` só aceita token que carregue `${CLAUDE_PLUGIN_ROOT}/` (ou sem chaves) **e** resolva
  pra um script existente sob a raiz do plugin — os comentários registram os dois defeitos que
  isso fechou: `'<script>.sh 2>/dev/null'` virava dois alvos e o fantasma caía no "assume o pior",
  e token absoluto escapava da raiz porque `raiz / "/abs"` devolve `/abs`. O conserto sugerido
  **não manda cortar**: *"colisao so e DEFEITO quando os gates tem o MESMO proposito… Este item e
  para VOCE julgar, nao para cortar no automatico."*
- **`check_gates_enganosos`** pega duas coisas: gate marcado `off` no disco com o plugin dele
  ainda habilitado, e **`.mode` homônimo em duas pastas** — *"o defeito e a EXISTENCIA do
  duplicado, nao o valor dele — editar o inerte nao muda comportamento nenhum e nao avisa"*.
  Quando nenhuma cópia mora na pasta que ele sabe ler, ele **recusa eleger um vencedor**, porque
  o conserto apontaria pra uma pasta que nem existe.
- **`check_plugins`** distingue **AUSENTE de DESLIGADO** lendo `plugins/installed_plugins.json`
  (`_refs_instaladas`), porque `claude plugin enable` num plugin não instalado falha. Sem essa
  fonte, `None` → fail-open pro comportamento antigo.
- **`check_skills`** trata "declarada e não instalada" como **nota, não desvio**, e a
  justificativa é sobre quem recebe o repo: *"em maquina de outra pessoa isso viraria uma
  acusacao por skill que ela nunca pediu — e desvio permanente em quem nao usa ensina a ignorar o
  relatorio inteiro"*.
- **`check_catalogo`** compara o `marketplace.json` publicado contra a receita: plugin no catálogo
  que não está no manifest *"nunca chega em maquina nenhuma — e ninguem descobre, porque nada
  mais compara os dois lados"*. **Máquina sem o marketplace instalado sai calado.**
- **`check_claude_md`** mostra o diff mas **não prescreve a direção**, e oferece os dois `cp`:
  *"quem edita o repo de proposito quer o contrario de quem escreveu uma regra nova na maquina"*.
- Uma checagem que estoura **não derruba o relatório**: o loop do `main()` pega `Exception` e
  transforma em desvio da área `interno`.

## 11. Decisões de arquitetura

Cada uma é uma regra que sobreviveu a um defeito, com o arquivo e o símbolo onde ela mora.

- **O estado vem do arquivo, nunca do julgamento do modelo.** É a mesma forma em quatro
  módulos: `journal.py:fold`, `ledger.py:fold`, `plan_state.py` (autora uma vez, marca depois) e
  `conformance.py` (lê a máquina, não pergunta). Onde há LLM no caminho — o juiz de forma, o
  auditor de entrega do intent-guard — ele **escolhe de um conjunto fechado** ou emite **uma
  linha em formato fixo**, nunca redige o estado.
- **Fail-open na borda de infra; fail-loud quando há evidência.** Todo hook sai 0 sem `jq`, sem
  `python3`, sem raiz resolvível. Mas `pattern_check.restamp` **recusa escrever** sem `HEAD`
  (*"carimbo pela metade e pior que carimbo velho"*) e `scope_staleness` devolve `unknown` em vez
  de `fresh` quando o git falha. A direção do fail depende de qual erro é mais caro.
- **Guarda que não registra execução é indistinguível de guarda ausente.** Nasceu de uma medição
  (§10.2) e hoje é padrão: `stop-prose-ceiling.py:batida`, `stop-forma-relato.py:batida` e
  `stop-regua-relato.py:batida` gravam **toda** execução, e `check_teto_rodou` /
  `check_juiz_rodou` transformam a ausência em desvio.
  ⚠️ **A régua dos bullets grava `batidas.log` e `bypass.log` como os vizinhos, mas ainda não tem
  checagem no `conformance.py`** — se ela ficar muda, ninguém acusa. [confirmado — `CHECAGENS`
  não lista nada de `regua-relato`; o hook escreve em `state/regua-relato/`]
  O corolário: teto conhecido (o hook desiste após 2 bloqueios) vira **número visível**
  (`bypass.log` → `check_bypass_teto`), nunca silêncio.
- **Estado mutável mora em `~/.claude/…`, nunca dentro do plugin** — `${CLAUDE_PLUGIN_ROOT}` é
  cache reescrito a cada bump. E estado por-sessão em `/tmp` **tem que** ser chaveado por
  `session_id`, senão sessões concorrentes se contaminam (o escape do gate de plano, o cap de
  nudges, o anti-loop dos dois Stop hooks).
- **Uma expressão só para resolver caminho, compartilhada pelos dois lados.**
  `hooks/lib-project-root.sh` para os hooks do gate de plano; `CLAUDE_DIR` idêntico entre
  `stop-prose-ceiling.py` e `lib/conformance.py`. Quando os lados divergem, **cada um fica
  coerente sozinho e o conjunto mente** — que é a falha mais cara porque não aparece em teste
  isolado.
- **Vendoring com fonte-da-verdade declarada e drift checável.** `_shared/` é a fonte; as 19
  cópias são derivadas; `sync-shared.sh --check` acusa divergência e o gate A do commit roda isso.
- **Regra que vale para um artefato vale para todos os que o mesmo humano lê — então ela sai do
  gerador.** A régua de forma nasceu dentro do `visual_page.py` e virou `_shared/regua_texto.py`
  com **perfil por artefato** (§7.4). O corolário é o desenho: *"não existe perfil frouxo — o que
  o perfil declara é o que, NAQUELE artefato, não é redação"*. Uma segunda cópia da régua seria o
  defeito, não a solução: *"ela divergiria da primeira e cada lado ficaria coerente sozinho"*.
- **Contrato que muda de valor vira DADO, não prosa.** O R8 morava carimbado em SKILL.md, e
  trocar seis valores custou 45 substituições com três invertidas (§7.3). Hoje é
  `_shared/r8-tiers.json`: a vista humana é **gerada**, a casca **passa em `args`**, e a checagem
  A2 do commit barra quem voltar a carimbar. É a mesma regra do bullet acima, aplicada a número
  em vez de forma.
- **Stdlib-puro é requisito, não preferência.** Os dois `try/except ImportError` (`journal.py` →
  `collect_engine`, `organism.py` → PyYAML) existem porque a máquina do cliente pode não ter
  nada. O fallback de YAML **levanta erro** fora do subconjunto suportado em vez de produzir
  parse errado silencioso.
- **Regra em prosa apodrece; recorte não.** Está escrito em três lugares independentes:
  `askq-humanize.sh` (*"a regra… já existe em prosa no CLAUDE.md e não pegava"*), `visual_page.py`
  (*"a cópia do bloco colada na skill JÁ divergiu do template"*) e o `.gitignore` do repo
  (*"368 ocorrências do nome do dono entraram enquanto isto era só um parágrafo"*).
- **O gate compara com um retrato, não exige zero.** O gate E do `release-gate.sh` usa
  `.claude/hook-contract.baseline.json` e só barra o que **PIOROU** — o comentário do arquivo
  explica: *"os achados que já existiam e foram aceitos não travam ninguém, mas hook novo que
  bloqueia sem teto, sem botão de desligar ou com binário fixo é barrado"*. É o que impede a
  regra de apodrecer por ser severa demais.

## 12. Divergências vivas

- ⚠️ **O baseline do contrato de hooks está com a contagem velha.** O arquivo versionado
  registra `entries: 31, scripts: 30` e 3 achados; a medição de hoje dá **38 registros / 37
  scripts** com os mesmos 3 achados. O gate E passa porque ele compara **achados**, não
  contagem — mas o retrato numérico não descreve mais o repo. [confirmado — leitura do JSON +
  `python3 scripts/hook_contract.py --baseline .claude/hook-contract.baseline.json` neste run,
  que imprime *"Nenhum achado. Todos os hooks batem com o contrato."*]
- ⚠️ **Um achado 🔴 ALTA aceito, não resolvido**: `ship/pre-deploy-test-check.sh` bloqueia com
  `exit 2` e não tem teto de devoluções (`R1-cap-ausente`, linha 352 do relatório). Está no
  baseline, então não trava commit — mas continua sendo o único hook do repo que pode devolver
  para sempre.
- ⚠️ **`pi-plugins/` no disco, untracked e gitignorado** (`.gitignore:71`). Não é fonte de nada;
  quem der `grep` na raiz do repo vai encontrar código duplicado que não é distribuído.
- ⚠️ **A atribuição de terceiro do `archify` não está mais em lugar nenhum rastreável.**
  `grill-me` e `grill-with-docs` carregam `author` no `marketplace.json`; a entrada do `archify`
  não. A procedência vivia em mensagem de commit, e a história foi recriada. [confirmado —
  leitura do catálogo]
- ⚠️ **Os três `Stop` do bootstrap têm o mesmo teto conhecido de carga** (`stop-prose-ceiling.py`,
  `stop-regua-relato.py` e `stop-forma-relato.py`):
  como todo hook de plugin, só carregam no `SessionStart`, então sessão já aberta no momento da
  instalação fica descoberta até o próximo `/clear`. Está escrito no cabeçalho do primeiro e é
  o conserto que o `check_teto_rodou` sugere.

## 13. Verificação

Todas as suítes `plugins/*/lib/test_*.py` executadas nesta rodada, saída literal da última linha
de cada uma:

```
plugins/bootstrap/lib/test_conformance.py    :: 59 ok · 0 FAIL
plugins/branches/lib/test_branch_state.py    :: OK
plugins/guardrails/lib/test_askq_lint.py     :: ── 47 passou · 0 falhou ──
plugins/intent-guard/lib/test_ledger.py      :: test_ledger: OK
plugins/project-doc/lib/test_doc_lint.py     :: TODOS OS 35 CHECKS PASSARAM
plugins/project-doc/lib/test_graph_map.py    :: TODOS OS 23 CHECKS PASSARAM
plugins/project-doc/lib/test_journal.py      :: TODOS OS 123 CHECKS PASSARAM
plugins/project-doc/lib/test_organism.py     :: test_organism: dirty-modules + propagação por costura ✓
plugins/project-doc/lib/test_pattern_check.py:: TODOS OS 84 CHECKS PASSARAM
plugins/slides/lib/test_md2deck.py           :: 50 passou · 0 falhou
plugins/visual/lib/test_plan_state.py        :: OK
plugins/visual/lib/test_visual_page.py       :: 60 passou · 0 falhou
```

⚠️ **Falta uma suíte nessa lista** e a ausência é de data, não de defeito: `plugins/visual/lib/test_cobertura.py`
nasceu depois daquele run. Executada agora, junto com as duas que cobrem o resto do código novo
desta rodada [confirmado — as três rodadas nesta passada de `/doc-touch`]:

```
plugins/visual/lib/test_cobertura.py         :: OK
plugins/visual/lib/test_plan_state.py        :: OK
plugins/intent-guard/lib/test_ledger.py      :: test_ledger: OK
```

Mais duas verificações rodadas aqui:

```
$ bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh   →  52 ok · 0 FAIL
$ bash scripts/sync-shared.sh --check                    →  OK: cópias vendored idênticas a _shared/
```

**As cinco suítes que nasceram com a régua de forma** (§7.4), executadas nesta passada
[confirmado — saída literal de cada uma]:

```
$ python3 _shared/test_regua_texto.py                    →  71 passou · 0 falhou
$ python3 scripts/test_regua_call_check.py               →  18 asserts ok ✓ (0 gerador fora da régua hoje)
$ python3 plugins/visual/lib/test_regua_audit.py         →  OK
$ python3 plugins/guardrails/hooks/test_artefato_regua.py →  23 checks ok, 0 falhas
$ python3 _shared/r8_tiers.py check                      →  OK: R8 servido de _shared/r8-tiers.json
```

**Três suítes nasceram na rodada de consertos**, e as três cobrem exatamente o que não tinha
teste: os dois gates e a leitura do arquivo de plano pela skill de handoff. Saída literal
[confirmado — as três executadas nesta passada de `/doc-touch`]:

```
$ bash    .claude/hooks/test_release_gate.sh              →  OK (30 checks)
$ bash    plugins/visual/hooks/test_exitplan_gate.sh      →  OK (12 checks)
$ python3 plugins/handoff/lib/test_handoff_skill.py       →  OK (7 asserções `ok`)
```

⚠️ **`.claude/hooks/test_release_gate.sh` fica FORA dos dois globs do check D/F** — ela mora em
`.claude/hooks/`, não em `plugins/<nome>/`, então nenhum commit a dispara automaticamente.
É a mesma exceção que já vale para as duas suítes de `scripts/`. [confirmado — a régua do
gate está em `patterns.md` §5.2]

### 13.1 As duas suítes que cobrem o código novo desta rodada

- **`plugins/bootstrap/lib/test_conformance.py` — 59 checks em 27 funções `teste_*`**
  [confirmado — `grep -c "^def teste_"` neste run devolve `27`; a execução imprime `59 ok`]. A
  função `teste_juiz_de_forma_mudo()` exercita os **quatro** ramos do `check_juiz_rodou`, com os
  rótulos copiados literal do arquivo: *"acusa juiz que nunca executou"*, *"acusa fail-open por
  juiz sem resposta"*, *"acusa juiz parado ha mais de 24h"* e *"nao cobra juiz de quem nao
  instalou o bootstrap"*. Esse último é a metade da régua que impede o verificador de acusar
  quem simplesmente não tem o plugin.
- **`plugins/bootstrap/hooks/test_bootstrap_hooks.sh` — 52 checks** [confirmado — execução
  nesta passada; eram 36 antes do bloco novo `-- regua de estilo nos bullets do relato`, que
  cobre o `stop-regua-relato.py` da §10.2 (2b)], com um bloco dedicado ao
  juiz (`-- juiz de forma do relato`). Ele tem uma proteção que merece registro, porque é a
  única defesa contra um teste verde falso: como o juiz é fail-open, **um juiz mudo aprovaria
  todos os casos e a suíte ficaria verde sem ter testado nada**. Por isso, além de
  *"relato bom passa"* (exit 0) e *"relato ruim reprova"* (exit 2), há um check explícito
  — *"o juiz respondeu de verdade (nao foi fail-open)"* — que reprova com
  `FAIL juiz mudo — o verde acima nao vale`. O bloco inteiro é pulado (`skip`) quando não há
  `claude` no PATH. [confirmado — leitura do arquivo + execução]

### 13.2 Contrato dos hooks

```
$ python3 scripts/hook_contract.py
Contrato dos hooks — 38 registros, 37 scripts distintos
  ship/pre-deploy-test-check.sh      🔴 ALTA   R1-cap-ausente   bloqueia (exit2) e não tem teto:352
  bootstrap/session-sync.sh          🟡 MÉDIA  R5-sem-failopen  usa jq sem guarda de ausência
  project-doc/sessionstart-doc.sh    🟡 MÉDIA  R5-sem-failopen  usa python3 sem guarda de ausência
Total: 3 achado(s) — 1 alta · 2 média · 0 baixa
```

O rodapé da própria ferramenta é a régua de como usar isso: *"Cada achado é ONDE OLHAR, não
veredito. Confira no arquivo antes de consertar."*

⚠️ **Os dois registros novos desta rodada entraram sem produzir achado** —
`stop-regua-relato.py` e `pretooluse-artefato-regua.py` têm kill-switch (`REGUA_RELATO`,
`ARTEFATO_REGUA`), cap (`MAX_BLOQUEIOS = 2` no primeiro) e fail-open em toda borda, que são
exatamente as propriedades 2, 3 e 5 que o scanner mede. **O total subiu de 36 para 38 e a lista
de achados continua com os mesmos 3** [confirmado — a saída acima, re-executada nesta passada,
contra a contagem dos `hooks.json` em `8c315ba`, que dá 36].
