---
generated: 2026-06-20
project: pedro-plugins
scope:
  - .claude-plugin/marketplace.json
  - plugins/*/.claude-plugin/plugin.json
  - plugins/*/hooks/hooks.json
  - plugins/bootstrap/config/manifest.json
  - plugins/project-doc/lib/journal.py
  - _shared/collect_engine.py
  - README.md
---

# Architecture

## Visão Geral

- Marketplace privado de plugins para **Claude Code**. Monorepo: cada subpasta em `plugins/` é um plugin independente (skills, hooks, automações), distribuído via `.claude-plugin/marketplace.json` na raiz.
- **17 plugins** (todos versionados; marketplace.json e cada `plugin.json` batem 1:1 — verificado, zero drift de versão).
- Quem usa: o próprio Pedro (e os agentes que consultam esta doc). Repo **privado** — `git@github.com:pedroberaldo87/pedro-plugins.git`. Sem licença pública.
- Doc é **agent-facing**: escrita de agente pra agente (Claude/GPT/etc. consultam mais que humanos).
- Workflows-chave:
  - **Pegar um plugin:** `claude plugin marketplace add <git-url>` → `claude plugin install <nome>@pedro-plugins`.
  - **Máquina nova (setup inteiro):** instala `bootstrap` → `/bootstrap:setup` (sincroniza marketplaces+plugins de terceiros do manifest E aplica config global versionada).
  - **Publicar uma mudança:** edita o plugin → **bumpa `version` no `plugin.json` E espelha no `marketplace.json`** → `claude plugin validate` → commit + push → merge na `main` (o que replica entre máquinas é a `main`).
- Dois subsistemas com lógica real (não só markdown) vivem em Python:
  - **Engine de coleta/journal** (`project-doc` + `handoff`) — minera transcripts/git/handoffs/memory, scrubber de segredos, journal append-only.
  - **Engine de relatório/auditoria** (`fallow`) — lê o JSON do Fallow e gera relatório+auditoria.

## Stack

- **Linguagem:** Markdown (skills + docs) + Shell (hooks) + Python 3 (engines do project-doc/handoff/fallow).
- **Runtime:** Claude Code (plugin host). Hooks shell; engines Python via `python3` no PATH; `jq` no setup. Sem Node como dependência de plugin (o `visual` sobe um daemon `.mjs` em runtime, mas não é build).
- **Package manager:** nenhum. **Build:** nenhum.
- **Hosting / distribuição:** GitHub (`pedroberaldo87/pedro-plugins`), instalado via CLI de plugin do Claude Code.
- **Knowledge graph:** `graphify-out/` (extração AST, refresh 2026-06-20 pós-rename `bootstrap-third-party`→`bootstrap`; ~2967 nós / 3084 arestas / 222 comunidades por backup; backups datados em `graphify-out/<data>/`).

## Estrutura de Diretórios

```
pedro-plugins/
├── .claude-plugin/
│   └── marketplace.json        # catálogo: 1 entrada por plugin (name, source, version, category, tags)
├── plugins/                    # 17 plugins independentes (ver Catálogo)
│   └── <nome>/
│       ├── .claude-plugin/
│       │   └── plugin.json      # identidade: name, version, description, author
│       ├── hooks/               # (8 dos 17) automações
│       │   ├── hooks.json       #   ⚠️ AQUI (subpasta), nunca na raiz do plugin
│       │   └── *.sh / *.py      #   scripts dos hooks
│       ├── skills/<nome>/
│       │   └── SKILL.md         # instrução da skill (o nome da pasta vira o comando)
│       ├── lib/                 # (fallow, handoff, project-doc) código Python
│       ├── config/              # (bootstrap) manifest + config global versionada
│       ├── references/          # (raiox, slides) docs auxiliares da skill
│       └── server/              # (visual) daemon de live-sync
├── _shared/
│   └── collect_engine.py       # FONTE-DA-VERDADE da engine de coleta (vendorada nos plugins)
├── scripts/
│   └── sync-shared.sh          # vendora _shared/collect_engine.py → lib/ de cada consumidor
├── graphify-out/               # knowledge graph (versionado; cache/ e paths de máquina gitignorados)
├── .claude/                    # doc do PRÓPRIO repo (CLAUDE.md, docs/, journal, ata, handoffs)
├── README.md
├── AGENTS.md · GEMINI.md · .cursorrules · .windsurfrules · .github/copilot-instructions.md  # ponteiros finos p/ outras IAs
└── .gitignore
```

## Catálogo dos Plugins

17 plugins. Versões REAIS lidas de `plugins/*/.claude-plugin/plugin.json` (e batem com `marketplace.json`).

### Sessão & continuidade

- **handoff** `v1.7.0` — Continuidade de sessão em um comando: detecta o estado e roteia (contexto cheio → salva PRD + LOG verbatim; sessão recém-limpa → retoma). Workspace-aware (resolve a fronteira `.git`). `category: productivity`. ⚙️ hooks.
- **context-guard** `v1.1.1` — Auto-interrompe o workflow quando o context window passa de um threshold (default 80%); ponte statusLine↔PostToolUse via arquivo temp; encaminha para qualquer statusLine via `CLAUDE_STATUSLINE_FORWARD`. Use junto com `handoff`. `category: productivity`. ⚙️ hooks.
- **sovai** `v1.3.0` — Modo de execução contínua: roda um plano do início ao fim sem pausas; pula bloqueios (sem workaround silencioso), registra decisões, roda `/qa-loop --headless`, atualiza a doc (`/project-doc`) e faz commit + push do trabalho, entrega relatório via `/visual`. `category: productivity`.

### Planejamento & review

- **qa-loop** `v1.2.1` — Loop de review→conserto que para por **retornos decrescentes**, não por zero. Motor = Workflow determinístico (Opus revisa → Opus planeja/adjudica → Sonnet conserta; gate/churn/parada em código). 3 buckets (implementação / plan-drift / plano-falho); relatório humano (HTML via `/visual`) + journal agêntico. **Substituiu e apagou** `qa`, `rev6`, `iterate`. `category: dev-tools`.
- **grill-me** `v1.0.0` — Entrevista implacável, uma pergunta por vez, sobre um plano até esgotar a árvore de decisões. *Autor: Matt Pocock.* `category: dev-tools`.
- **grill-with-docs** `v1.0.0` — Igual ao `grill-me`, mas confronta contra o domain model (CONTEXT.md, ADRs) e atualiza as docs inline. *Autor: Matt Pocock.* `category: dev-tools`.
- **principles** `v1.0.0` — Carrega `PRINCIPIOS-SISTEMAS.md`, mapeia categorias ao contexto, gera guia WHY+HOW. Modos planning e review. `category: dev-tools`.

### Documentação & conhecimento

- **project-doc** `v3.3.0` — Gera sistema de documentação a partir de TODA a evidência (arquivos, handoffs, memory, grafo, git log, transcripts), num journal append-only versionado, projetado em índice `CLAUDE.md` + `.claude/docs/*.md` + ponteiros finos. Scrubber move segredos pro cofre. FULL/`--deep` mineram via Workflow e LEEM o código real por fan-in do grafo. `category: productivity`. ⚙️ hooks.
- **graphify-guard** `v1.0.1` — Garante que os knowledge graphs do `graphify` sejam consultados. SessionStart avisa quando há grafo; PreToolUse redireciona grep/glob/find cego para `graphify query` (1×/sessão). Fail-open, monorepo-aware. **Único plugin sem `skills/` — puramente hooks.** `category: productivity`. ⚙️ hooks.

### Dev, deploy & limpeza

- **ship** `v1.0.1` — Fluxo de deploy: lint → type-check → commit → push → deploy. PreToolUse gateia deploy com teste quebrado (reconhece apps Python e Node). `category: dev-tools`. ⚙️ hooks.
- **guardrails** `v1.1.0` — Guardrails globais de edição como hooks: lint & type-check pós-edição, scope-cop LLM (Haiku) que bloqueia edições de UI fora do plano, e guard de uso indevido de Agent Teams. Portável — substitui hooks hand-rolled no `~/.claude/settings.json`. Rode `/guardrails:setup` 1×/máquina. `category: dev-tools`. ⚙️ hooks.
- **fallow** `v1.0.2` — Roda o Fallow (analisador estático JS/TS), classifica achados por tipo e confiança, audita pra pegar falsos-positivos (cron, rota HTTP, import dinâmico), entrega relatório HTML interativo. Limpeza com rede de segurança. `category: dev-tools`.
- **improve** `v1.0.0` — Implementa rodadas de melhoria iterativa lendo `IMPROVEMENT_PROGRAM.md` + issues do GitHub com label `autoresearch`. `category: dev-tools`.

### Apresentação visual

- **visual** `v1.2.0` — Transforma textão do CLI em views HTML dark-theme interativas, abertas no browser com live-sync via daemon local; salva em `<projeto>/.claude/visual/`. Modo auto renderiza planos/decisões/diagnósticos (PreToolUse em ExitPlanMode). `category: productivity`. ⚙️ hooks.
- **slides** `v1.1.0` — Outline em markdown → deck HTML single-file nível keynote (tema VIU default), adaptativo (desktop rico / mobile sem JS), fidelidade estrita ao texto. `category: productivity`.

### Setup de máquina

- **bootstrap** `v1.0.0` — Prepara máquina nova: auto-sincroniza marketplaces e plugins de terceiros via hooks E aplica config global versionada (env, permissões, flags, CLAUDE.md global, statusLine resolvido por máquina). Rode `/bootstrap:setup` 1×/máquina. **Substituiu `bootstrap-third-party`.** `category: productivity`. ⚙️ hooks.

### Domínio VIU

- **raiox** `v0.2.0` — RAIOX: inteligência replicável de canais do YouTube pra VIU Studio. Orquestra o pipeline viu-raiox (fetch público → fact store DuckDB → módulos de análise code-only → validação de números órfãos) por config YAML de canal. Honesty Rule: todo número citável nasce em JSON gerado por código. `category: dev-tools`.

## Plugins com Hooks Automáticos

**8 dos 17** plugins têm `hooks/hooks.json` (verificado — nenhum `hooks.json` solto na raiz de plugin; o bug histórico está corrigido). O hook de plugin dispara em **qualquer projeto** uma vez instalado — é o mecanismo de "hook global que replica entre máquinas".

- **bootstrap** — `SessionStart` → `session-sync.sh` (pull + apply manifest + snapshot + commit/push, com lock + re-entrancy guard); `PostToolUse(Bash)` → `post-plugin-command.sh` (snapshot imediato após `claude plugin` commands).
- **context-guard** — `SessionStart` → `context-guard-reset.sh` (reset do estado, timeout 5s); `PostToolUse` → `context-guard.sh` (lê o % de contexto e interrompe acima do threshold).
- **graphify-guard** — `SessionStart` → `sessionstart-graphify.sh` (heads-up se há grafo + freshness); `PreToolUse(Grep|Glob|Bash)` → `pretooluse-graphify-guard.sh` (redireciona busca cega pro `graphify query`, 1×/sessão).
- **guardrails** — `PostToolUse(Edit|Write)` → `lint-and-typecheck.sh` (ruff/lint+typecheck no arquivo editado; BLOQUEIA em erro); `PreToolUse(Agent)` → hook tipo `prompt` (juiz inline que NEGA Agent usado como substituto de Agent Teams); `PreToolUse(Edit|Write)` → `scope-cop.sh` (juiz Haiku que nega edição de UI fora do plano aprovado; reconhece plano via ExitPlanMode E via `/visual`).
- **handoff** — `SessionStart` → `sessionstart-ata.sh` (discovery do transcript da sessão); `Stop` → `handoff-completeness-gate.sh` (bloqueia o Stop até o PRD cobrir cada item forte; valida só o handoff da própria sessão via header `Session:`); `PreToolUse(TeamCreate)` → `teamcreate-nudge.sh` (lembra de consolidar antes do clã).
- **project-doc** — `SessionStart` → `sessionstart-doc.sh` (aviso doc-first + flag de defasagem); `PreToolUse(Grep|Glob|Bash|Agent)` → `pretooluse-doc-guard.sh` (insiste em ler a doc antes de explorar; teto de 3 nudges); `PostToolUse(Read)` → `posttooluse-doc-read.sh` (resolve o sentinel quando a doc é LIDA).
- **ship** — `PreToolUse(Bash)` → `pre-deploy-test-check.sh` (intercepta comandos de deploy — pm2/docker compose/vercel/netlify/`deploy.sh`/`make deploy` — roda o suite e sai com código 2 se algo falhar; gateia por app no monorepo).
- **visual** — `PreToolUse(ExitPlanMode)` → `pre-exitplan-visualize.sh` (intercepta o ExitPlanMode pra renderizar o plano como HTML antes de despejar no CLI).

## Dependências Críticas / Modulos

- **Engine de coleta compartilhada (`_shared/collect_engine.py`).** Fonte-da-verdade; **vendorada** (não importada em runtime) pra `lib/` de cada consumidor via `scripts/sync-shared.sh`, porque o Claude Code isola cada plugin no cache (sem import cross-plugin). Consumidores: `handoff` (`lib/extract_ata.py`) e `project-doc` (`lib/journal.py`). Decisão do monorepo: pasta neutra `_shared/`, runtime autônomo, degradação graciosa se a engine sumir. Cobre: leitura/discovery de transcript (single + multi-slug), resolução de project-root/módulos (avulso / monorepo / guarda-chuva), `collect()` de itens crus, `finding_id` estável.
  - **GOTCHA:** só `collect_engine.py` é vendorado — `journal.py` vive **só** em `plugins/project-doc/lib/`. Não há 2 cópias de `journal.py`.

- **Journal + scrubber (`plugins/project-doc/lib/journal.py`).** Camada mecânica do project-doc v3. Estado em `.claude/.project-doc/` (**versionado** — é o veículo do conhecimento entre máquinas; transcripts são locais e não viajam): `findings.jsonl` (journal append-only de eventos discovered/invalidated/curated — o estado vivo é o fold) + `ledger.json` (delta forward por sessão/commit + backward por anchors mudadas). Scrubber em camadas (PEM → connection string → JWT → prefixos de provider → chave=valor → prosa+entropia → `‹revisar?›` na dúvida) move o **valor-secreto** pro cofre (`~/Library/.../Cofre/<slug>.env`, iCloud; symlink gitignored em `.claude/secrets/ops.env`) e preserva nome/host/porta/contexto. **Nunca consulte segredo daqui — refira o cofre `.claude/secrets/ops.env`.**

- **Catálogo / registro do marketplace (`.claude-plugin/marketplace.json`).** Convergência de TODAS as frentes; reformatado por linter (single↔multi-line) — em commits cirúrgicos, comparar delta semântico (name+version), não diff textual.

- **Comunidades do grafo** (mapa de acoplamento, não eixo de fan-out): Bootstrap & Marketplace Sync, Hook Config (PreToolUse / SessionStart / PostToolUse), Context-Guard & Handoff Bridge, Handoff Save/Resume, Project-Doc Generator, Documentation System (CLAUDE.md), Graphify-Guard Net (+ Detect/Guard/SessionStart scripts), Marketplace Registry & Plugin Config / Manifest Metadata, Slides Deck Generation / Fidelity Checker, Fallow Audit Engine / Report Generation / Liveness & Convergence, QA & Rev6 Parallel Review (legado, absorvido pelo qa-loop), Sovai Autonomous Mode, RAIOX Channel Intelligence, Visual Auto-Mode Config / Daemon Start, PreToolUse Hooks & Visual Daemon, Grill Design Review, Improve Autoresearch.

- **Workflows (hyperedges) confirmados pelo grafo:**
  - Bootstrap Sync Cycle: pull → apply → snapshot → commit/push (conf 0.95).
  - Cross-Tool Doc Routing to CLAUDE.md (conf 0.95).
  - Context-Guard StatusLine/State-File Bridge (conf 0.95).
  - visual live-sync pipeline: skill → daemon starter → daemon → gate hook (conf 0.85).
  - slides deck generation: skill → template → layout map → theme → fidelity check (conf 0.85).
  - ship test gate: skill flow → hooks config → enforcing hook script (conf 0.85).

## Decisões de Arquitetura

- **Monorepo de plugins independentes** — 1 marketplace, 17 plugins; cada um instala/versiona sozinho.
- **Release por `version` string** — Claude Code detecta update SÓ pela `version` do `plugin.json` (sem semver range, sem content-hash). Bump obrigatório a cada mudança + espelho no `marketplace.json`; o que replica entre máquinas é a `main`.
- **Hook de plugin em `hooks/hooks.json` (subpasta), nunca na raiz** — na raiz o Claude Code ignora em silêncio (`claude plugin details` mostra `Hooks (0)`); `claude plugin validate` passa mesmo assim. `details` é o diagnóstico canônico. ("Hooks (N)" conta tipos de evento, não scripts.)
- **Hook como mecanismo de "global replicável"** — empacotar hooks soltos do `~/.claude/settings.json` como plugin (guardrails) replica via `install`, sem editar settings em cada máquina.
- **Estado mutável de hook fora do `${CLAUDE_PLUGIN_ROOT}`** — o cache do plugin é reescrito a cada bump; log/streak/mode vão em `~/.claude/<plugin>/` (por-máquina de propósito).
- **Engine compartilhada vendorada, não importada** — `_shared/` é fonte DRY; `sync-shared.sh` copia pra cada plugin porque o cache isola plugins (sem variável cross-plugin em runtime).
- **Journal append-only + scrubber como barreira pro git** — conhecimento acumula como eventos (super-git de findings); contradição → invalida na doc canônica mas mantém no journal; valor-secreto desviado pro cofre antes de qualquer escrita versionada.
- **Grafo é documentação obrigatória (project-doc FULL/--deep)** — `graphify update . --force` (AST puro, sem LLM, não-interativo) roda sempre que se documenta; o agente LÊ o código real por ordem de fan-in (capacidade nova — nenhuma versão anterior lia código de verdade).
- **Loop de review para por retornos decrescentes, não por zero** — domínio assintótico (scrubber/parser/heurística) não admite "até zero"; regression gate por conserto evita as regressões auto-infligidas (qa-loop).
- **`qa-loop` motor = um único Workflow determinístico** — Review+Plan+Exec num Workflow (Opus Revisor independente → Opus Planejador árbitro → Sonnet Executor), gates/churn/parada em JS; não sub-agentes soltos (respeita o guard `PreToolUse(Agent)`).

## Terceiros Gerenciados

Lidos de `plugins/bootstrap/config/manifest.json` — marketplaces e plugins de terceiros que o `bootstrap` auto-sincroniza (a entrada `pedro-plugins` é mantida à mão e preservada entre snapshots). `enabled` reflete o estado por máquina.

- **agent-browser** (git) — `agent-browser` ✅
- **claude-hud** (git) — `claude-hud` ✅
- **claude-plugins-official** (github `anthropics/claude-plugins-official`):
  - ✅ `code-review`, `code-simplifier`, `context7`, `explanatory-output-style`, `figma`, `frontend-design`, `playwright`, `skill-creator`, `superpowers`, `swift-lsp`
  - ❌ `claude-md-management`, `github`, `security-guidance`, `sonatype-guide`
- **i-have-adhd** (directory, source local não-replicável) — `i-have-adhd` ✅
- **obsidian-skills** (git) — `obsidian` ✅
- **openai-codex** (git) — `codex` ✅
- **voltagent-subagents** (git):
  - ✅ `voltagent-biz`, `voltagent-core-dev`, `voltagent-data-ai`, `voltagent-qa-sec`, `voltagent-research`
  - ❌ `voltagent-dev-exp`, `voltagent-domains`, `voltagent-infra`, `voltagent-lang`, `voltagent-meta`

> Nota: o `bootstrap` sincroniza **só marketplaces/plugins** via `manifest.json`. A config global (`settings.json`: env/permissions/statusLine + CLAUDE.md global) é aplicada à parte por `/bootstrap:setup` a partir de `plugins/bootstrap/config/` (`settings-defaults.json` com chaves `env/permissions/language/theme/autoCompactEnabled`, `CLAUDE-global.md`). Hooks globais hand-rolled foram empacotados como o plugin `guardrails`.
>
> **`apply-config` faz MERGE, não overwrite cego** (`apply-config.sh:10-13,51-55`): `env` → os defaults vencem em conflito; `permissions` → UNIÃO (nunca remove permissão existente); `settings.local.json` fica **intocado**. Garante idempotência sem pisar em config de máquina.
