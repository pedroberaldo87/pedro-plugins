---
generated: 2026-06-20
project: pedro-plugins
scope: .claude-plugin/marketplace.json, plugins/*/plugin.json, plugins/*/hooks/hooks.json, plugins/bootstrap/config/manifest.json
---

# Architecture

## Visão Geral
Marketplace privado de plugins Claude Code do Pedro. 17 plugins independentes (skills, hooks, automações) distribuídos via `.claude-plugin/marketplace.json`. Qualquer máquina instala com `claude plugin install`.

## Stack
- **Linguagem:** Shell (hooks), Markdown (skills), Python (libs de skill — ex: project-doc)
- **Runtime:** Claude Code plugin system
- **Hosting:** GitHub (`pedroberaldo87/pedro-plugins`)
- **Package manager:** nenhum — sem build, sem lockfiles

## Estrutura de Diretórios
```
pedro-plugins/
├── .claude-plugin/marketplace.json   # índice do marketplace (17 plugins)
├── plugins/                          # cada subdir = 1 plugin independente
│   ├── bootstrap/                    # ⚙️ hooks: SessionStart, PostToolUse — sync de terceiros + config global
│   ├── context-guard/                # ⚙️ hooks: SessionStart, PostToolUse
│   ├── fallow/
│   ├── graphify-guard/               # ⚙️ hooks: SessionStart, PreToolUse
│   ├── grill-me/                     # por Matt Pocock
│   ├── grill-with-docs/              # por Matt Pocock
│   ├── guardrails/                   # ⚙️ hooks: PostToolUse, PreToolUse (Edit|Write, Agent)
│   ├── handoff/
│   ├── improve/
│   ├── principles/
│   ├── project-doc/                  # tem lib/ (journal.py, collect_engine.py) — motor v3
│   ├── qa-loop/                      # review→conserto em loop (substitui qa, rev6, iterate)
│   ├── raiox/                        # pipeline YouTube (VIU Studio)
│   ├── ship/                         # ⚙️ hook: PreToolUse (Bash)
│   ├── slides/
│   ├── sovai/
│   └── visual/                       # ⚙️ hook: PreToolUse (ExitPlanMode)
└── README.md
```

## Anatomia de um Plugin
```
plugins/<nome>/
├── .claude-plugin/plugin.json    # identidade: nome, versão, descrição, autor
├── hooks/                        # (opcional)
│   ├── hooks.json                # declaração dos hooks — AQUI, NUNCA na raiz do plugin
│   └── <script>.sh               # scripts (referenciados como ${CLAUDE_PLUGIN_ROOT}/hooks/<script>.sh)
└── skills/<nome>/
    └── SKILL.md                  # instrução completa da skill
```
⚠️ O Claude Code só carrega hooks de `hooks/hooks.json`. Um `hooks.json` na raiz do plugin é silenciosamente ignorado (`claude plugin details` → `Hooks (0)`). Ver patterns.md → "Hooks de Plugin".

## Plugins com Hooks Automáticos
- **bootstrap** — `SessionStart`: sincroniza marketplaces/plugins de terceiros via `config/manifest.json` (pull → apply → snapshot → push) · `PostToolUse`: snapshot após comandos `claude plugin`. Substitui o antigo `bootstrap-third-party`; ganhou uma 2ª camada de **config global** (env vars, permissions, behavior flags, CLAUDE.md global, statusLine) aplicada via `/bootstrap:setup`
- **context-guard** — `SessionStart`: reseta sentinel · `PostToolUse`: lê `/tmp/claude-context-pct`, bloqueia se > threshold (80%)
- **graphify-guard** — `SessionStart`: avisa se o projeto tem knowledge graph · `PreToolUse (Grep/Glob/Bash)`: intercepta busca cega e redireciona pra `graphify query` (1x/sessão; cobre cwd container descendo)
- **guardrails** — `PostToolUse (Edit|Write)`: lint + type-check pós-edição (JS/TS/Python) · `PreToolUse (Edit|Write)`: scope-cop (juiz Haiku) bloqueia edição de UI que foge do plano · `PreToolUse (Agent)`: guarda contra mau uso de Agent Teams. Estado mutável em `~/.claude/guardrails/` (NÃO no cache do plugin). Migrado dos hooks soltos do `settings.json`; `/guardrails:setup` liga a env e remove os hooks antigos
- **ship** — `PreToolUse (Bash)`: bloqueia deploy se testes falham (só age em comandos de deploy)
- **visual** — `PreToolUse (ExitPlanMode)`: força renderização HTML do plano antes de apresentar ao usuário

## Catálogo dos 17 Plugins

Produtividade (8):
- **bootstrap** v1.0.0 — provisiona máquina nova em 2 camadas: (1) auto-sync de marketplaces/plugins de terceiros via `config/manifest.json` (hooks, convergência declarativa) e (2) config global versionada (env, permissions, behavior flags, CLAUDE.md global, statusLine resolvida pra máquina). Substitui `bootstrap-third-party`. `/bootstrap:setup` roda 1x por máquina
- **context-guard** v1.1.1 — interrompe workflow ao ultrapassar threshold de contexto (default 80%)
- **graphify-guard** v1.0.1 — garante consulta ao knowledge graph (graphify): heads-up no SessionStart + rede PreToolUse que redireciona grep/glob/find cego pra `graphify query`. Fail-open, monorepo-aware
- **handoff** v1.7.0 — continuidade de sessão: salva ou retoma `.claude/HANDOFF*.md` num único comando; workspace-aware (resolve o boundary `.git` dos arquivos tocados)
- **project-doc** v3.0.0 — gera sistema de documentação CLAUDE.md + `.claude/docs/` modular a partir de TODA evidência do projeto (cascata de 5 tiers: arquivos, destilados, git log, transcripts, humano). Motor = journal append-only versionado + projeção; scrubber de secrets. Lib em `plugins/project-doc/lib/`
- **slides** v1.1.0 — outline Markdown → deck HTML keynote-grade single-file
- **sovai** v1.1.0 — modo autônomo sem interrupções; pula itens bloqueados e anota
- **visual** v1.2.0 — CLI textão → HTML dark-theme com live sync via daemon local

Dev Tools (9):
- **fallow** v1.0.2 — análise estática JS/TS (dead code, duplicação, complexidade) com report interativo
- **grill-me** v1.0.0 — design review implacável uma pergunta por vez (Matt Pocock)
- **grill-with-docs** v1.0.0 — design review contra domain model existente, atualiza CONTEXT.md/ADRs inline (Matt Pocock)
- **guardrails** v1.1.0 — guardrails globais de edição como hooks: lint+type-check pós-edição, scope-cop (juiz Haiku) e guarda de Agent Teams. Migrado dos hooks soltos do `~/.claude/settings.json`; `/guardrails:setup` liga a env e limpa os antigos
- **improve** v1.0.0 — implementa melhorias via GitHub Issues com label `autoresearch`
- **principles** v1.0.0 — princípios de sistema mapeados ao contexto atual, guia WHY + HOW
- **qa-loop** v1.2.1 — loop de review→conserto que para por retornos decrescentes (não por zero). Motor roda como **Workflow determinístico** (Opus revisa → Opus planeja/adjudica → Sonnet conserta; gate/churn/parada em código). Ancora no plano (3 buckets: implementação/plan-drift/plano-falho), regression gate por conserto, accepted-limits, journal AGÊNTICO, e **relatório HUMANO interativo** (via /visual: 4 categorias de actionable + seleção live → próximo plano + gráfico de severidade por rodada). Substitui qa, rev6 e iterate
- **raiox** v0.2.0 — pipeline de inteligência de canal YouTube para VIU Studio (fetch → DuckDB → módulos de diagnóstico → validate)
- **ship** v1.0.1 — lint → typecheck → commit → push → deploy em sequência disciplinada

## Terceiros Gerenciados (via bootstrap)
Manifest em `plugins/bootstrap/config/manifest.json` (fonte de verdade dos marketplaces + plugins de terceiros; os hooks do bootstrap convergem o estado local pra ele):
- **claude-hud** — statusLine no terminal
- **claude-plugins-official** (Anthropic) — code-review, context7, figma, playwright, superpowers, etc.
- **obsidian-skills** — integração Obsidian
- **openai-codex** — bridge pro Codex
- **voltagent-subagents** — 57 subagentes especialistas (biz, core-dev, data-ai, qa-sec, research)
