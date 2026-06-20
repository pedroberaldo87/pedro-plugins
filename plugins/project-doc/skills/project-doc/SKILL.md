---
name: project-doc
description: "Use when entering a project without CLAUDE.md, after major structural changes, or when the user says \"project-doc\", \"documenta\", \"documentar\", \"documenta o projeto\", \"gera o claude.md\", \"atualiza o claude.md\", \"limpa os artefatos\", \"limpa os prints\", \"limpa o projeto\", \"arquiva protótipos\", or runs \"/project-doc clean\". Generates a modular documentation system (lightweight CLAUDE.md routing table + .claude/docs/*.md per concern + thin pointers for other AI tools) and detects/cleans up stale test artifacts (screenshots, runner output, temp files)."
---

# Project Doc v3 — Documentation System Generator

## Overview

Generates a **documentation system** for a project, not a single file.

**v3 em uma frase:** a doc deixa de ser file-scanner cego e passa a derivar de **toda evidência que o projeto tem** — arquivos, handoffs, memória, grafo, git log e os **transcripts das sessões** — guardando tudo num journal append-only versionado, projetando só o que está vivo e verdadeiro, sem nunca vazar um secret pro git. **A estrutura de saída é idêntica à v2** (markers `project-doc:v2` preservados): mudam a FONTE (cascata de 5 tiers — ver **Sources**) e o MOTOR (journal + projeção — ver **Collect & Project**). Quem conhece a doc v2 não vê diferença estrutural, só uma doc mais completa e auto-mantida.

The system has three layers:

1. **CLAUDE.md** — lightweight routing table (~60-100 lines). Always loaded in context. Contains: project identity, stack one-liner, quick commands, top gotchas, and a documentation index with "→ read when" hints
2. **`.claude/docs/*.md`** — detailed docs per concern (architecture, database, API, deploy, etc.). Loaded on-demand when Claude needs them for the current task
3. **Thin pointer files** — pure redirects (AGENTS.md, GEMINI.md, .cursorrules, etc.) that tell other AI tools to read CLAUDE.md

Sections are conditional — only generated if relevant content is detected. Small sections (≤5 lines) stay inline in CLAUDE.md instead of becoming separate doc files.

## When to Suggest Proactively

- Project has no `.claude/CLAUDE.md` → "Esse projeto não tem CLAUDE.md. Quer que eu rode o /project-doc pra gerar?"
- CLAUDE.md exists but major structural changes detected (new services, new deploy scripts, new database) → "O CLAUDE.md pode estar desatualizado. Quer que eu rode o /project-doc pra atualizar?"
- CLAUDE.md has v1 format (monolithic block with `project-doc:start/end` markers) → "O CLAUDE.md está no formato v1 (monolítico). Quer migrar pro v2 (indexado)? Roda `/project-doc migrate`"
- `.claude/docs/` exists but CLAUDE.md index is missing or doesn't reference it → "Tem docs em .claude/docs/ mas o CLAUDE.md não aponta pra eles. Quer que eu rode o /project-doc index?"
- `graphify-out/graph.json` exists but is stale (source files changed after its mtime) → "O knowledge graph (graphify-out/) pode estar desatualizado. Quer que eu rode `/graphify <path> --update`?"
- `graphify-out/graph.json` does NOT exist → **ALWAYS suggest creating one. Unconditional — no exceptions.** Do not assess triviality, coupling, file count, or whether it "would compensate"; that judgment is unreliable and is not the model's to make. Just offer; whether to run it is the user's call. → "Esse projeto se beneficiaria de um knowledge graph: mapeia relações e ajuda a localizar/debugar. Quer gerar um com `/graphify`?"
- Volume of stale test artifacts detected (loose images in root, `.playwright-mcp/`, `test-results/`, many `.DS_Store`) → "Achei {N} artefatos de teste/temporários largados ({breakdown curto, ex: 45 prints soltos, .playwright-mcp/ com 78 arquivos, 129 .DS_Store}). Quer revisar e limpar com `/project-doc clean`?"

## Invocation Modes

The skill accepts an optional argument to control scope:

- `/project-doc` — **FULL**: scan everything, generate/update all docs + index + pointers
- `/project-doc <doc-name>` — **INCREMENTAL**: regenerate only that doc. Valid names: `architecture`, `database`, `api`, `deploy`, `infrastructure`, `env-vars`, `auth`, `patterns`. For monorepos also: `{app-name}/api`, `{app-name}/database`, etc.
- `/project-doc index` — regenerate only the CLAUDE.md routing table (re-scan for new/removed docs)
- `/project-doc pointers` — regenerate only the thin pointer files
- `/project-doc migrate` — migrate v1 monolithic CLAUDE.md → v2 indexed format (see Migration section)
- `/project-doc verify` — run verification only, no generation
- `/project-doc clean` — detect, **cluster**, and offer cleanup/archival of stale test artifacts (see Artifact Cleanup). Nothing is removed without confirmation. Runs standalone (no doc regeneration).
- `/project-doc --deep` — **DEEP**: como o FULL, mas o tier 4 minera **TODAS** as sessões de transcript do projeto (cold-start / backfill do histórico de conversas), não só o delta. Pesado — rode pro primeiro mergulho completo.
- `/project-doc --rebuild` — **REBUILD**: descarta a doc gerada e re-projeta do **journal inteiro** (`findings.jsonl`). Idempotente; não minera nada novo — só re-deriva a doc dos findings vivos.
- `/project-doc --solo` — escape: força FULL/`--deep` a rodar **single-agent** (sem Workflow) e **pula o grafo** (passo 0.0). Debug / projeto pequeno.

**Escape do grafo (v3.2):** o FULL/`--deep` garante o grafo por padrão (passo 0.0). Pra desligar sem desligar o Workflow, ponha `project_doc.skip_graph: true` em `.claude/settings.json`. O `--solo` também pula o grafo.

**FULL e `--deep` mineram via Workflow (fan-out por concern) por padrão** — ver **Workflow Engine**. Os demais modos rodam single-agent. `--solo` desliga o Workflow.

Doc names map directly to `.claude/docs/{arg}.md`. If the argument doesn't match a known doc name, treat it as a full run and warn the user.

## Output Protocol

Report each step to the user as you execute. Don't skip steps or batch them silently.

### Full Mode

```
**Step 1/13:** Root → `/path/to/project`
**Step 2/13:** Layout → Standard | Monorepo (N apps)
**Step 3/13:** Type → app | lib | cli
**Step 4/13:** Package manager → pnpm | yarn | bun | npm
**Step 5/13:** Mode → FULL | MIGRATE (v1→v2 detected) | CREATE (no CLAUDE.md)
**Step 6/13:** CLAUDE.md → v1 markers (will migrate) | v2 index (will update) | none (will create)
**Step 7/13:** Graph (FULL/`--deep`) → `graphify update --force` {criado | atualizado | já fresco | graphify ausente} + graph_map → {N god nodes, M comunidades, K hyperedges} | skipped (`--solo` / `skip_graph`)
**Step 8/13:** Collecting → tier 1 scan (arquivos por concern, **ranqueados por fan-in do grafo**) + `journal.py` tiers 2-4 → {new_events, live_count, stale}
**Step 9/13:** Generating docs → {list of .claude/docs/*.md to create/update, with line counts}
**Step 10/13:** Writing CLAUDE.md index → {N lines}
**Step 11/13:** Pointer files → {list created/updated/skipped}
**Step 12/13:** Verification → {results summary, inclui auditoria grafo×doc}
**Step 13/13:** Token impact → Before: {N} lines always-loaded | After: {M} lines always-loaded + {K} docs on-demand | Savings: {X}%
```

### Incremental Mode

```
**Step 1/3:** Root → `/path/to/project`, scope → {doc-name}
**Step 2/3:** Scanning {doc-name} sources... (list files read)
**Step 3/3:** Written → `.claude/docs/{doc-name}.md` ({N} lines), CLAUDE.md index updated
```

### Migrate Mode

```
**Step 1/5:** Root → `/path/to/project`
**Step 2/5:** Parsing v1 block... ({N} sections found)
**Step 3/5:** Extracting to .claude/docs/... ({list of docs created})
**Step 4/5:** Rewriting CLAUDE.md as v2 index... ({N} lines)
**Step 5/5:** Token impact → Before: {N} lines monolithic | After: {M} lines index + {K} docs on-demand | Savings: {X}%
```

### Clean Mode

```
**Step 1/5:** Root → `/path`, escopo → cleanup
**Step 2/5:** Varrendo artefatos... (imagens soltas, .playwright-mcp/, test-results/, temporários, .DS_Store, protótipos)
**Step 3/5:** Classificação → 🗑️ deletar ({N}) · 📦 arquivar ({M}) · 🚩 revisar/sensível ({K}) · ✋ manter ({X})
**Step 4/5:** Lista clusterizada para julgamento (ver Artifact Cleanup) — aguarda aprovação
**Step 5/5:** Aplicado → {deletados} removidos, {arquivados} → _archive/, {pulados}. Rede de segurança: _archive/{nome}-housekeeping-{data}.tar.gz
```

## Process

1. **Identify project root** — find nearest git repo root or use cwd
2. **Detect project layout** — check for monorepo indicators:
   - `apps/` or `packages/` directory with 2+ subdirs containing Dockerfile, package.json, or main entry files
   - Root docker-compose.yml with services mapping to subdirs (e.g., `dockerfile: apps/X/Dockerfile`)
   - Workspace config (pnpm-workspace.yaml, package.json workspaces, lerna.json)
   - If monorepo detected: use Monorepo layout. If not: use Standard layout.
3. **Detect project type** — classify as app, lib, or cli using the Detection Matrix rules. This determines which sections to include/omit.
4. **Detect package manager** — check lockfiles (pnpm-lock.yaml → yarn.lock → bun.lockb → package-lock.json). First match wins.
5. **Determine mode:**
   - If argument is `migrate` → MIGRATE mode
   - If argument is `verify` → VERIFY mode (skip to verification)
   - If argument is `index` → INDEX mode (skip to step 9)
   - If argument is `pointers` → POINTERS mode (skip to step 10)
   - If argument is a doc name → INCREMENTAL mode (skip to step 6, scan only that doc's sources)
   - If no argument and v1 markers found (`<!-- project-doc:start -->`) → auto-trigger MIGRATE, then FULL
   - If no argument → FULL mode
6. **Collect from the 5-tier source cascade** (see **Sources** + **Collect & Project**). Tier 1 = scan files via the Detection Matrix below; tiers 2-4 = run the lib (`journal.py`); tier 5 = ask the human for critical gaps.
   - **FULL / DEEP:** rode a **checagem ativa (passo 0.1)** e minere via **Workflow** (fan-out por concern) — ver **Workflow Engine**. A checagem classifica a doc existente, decide `update` vs `deep`, e dispara backup+garimpo se a doc estiver fora do padrão. `--solo` força single-agent.
   - **FULL mode:** scan everything (tier 1) + `journal.py update` (tiers 2-4, delta)
   - **DEEP mode:** tier 1 + `journal.py deep` (minera TODAS as sessões — cold-start)
   - **REBUILD mode:** pula a mineração; `journal.py rebuild` re-projeta do journal existente
   - **INCREMENTAL mode:** scan only the source files mapped to the target doc (tier 1); o journal já carrega os findings das outras fontes
   - For monorepos, also scan each app directory (see Monorepo-Specific Detection)
   - **Monorepo CRITICAL RULE:** NEVER carry forward app entries from existing docs. Every app must be regenerated from disk. For each app directory found in `apps/`:
     - Read `apps/{name}/requirements.txt` or `package.json` (full content)
     - Read `apps/{name}/main.py` or main entry file (full content, or at minimum the imports + route definitions)
     - Read `apps/{name}/.env.example` if it exists
   - Skipping any app file read is a process violation. There are no shortcuts.
7. **Project the live findings + tier-1 scan into doc sections** (see **Collect & Project** — relevância, kind→seção, reconciliação contra o código atual), then **determine which docs to generate** based on the projected results. A doc file is generated only if its detection/projection found substantive content.
   - **Inline threshold:** if a section would produce ≤5 lines of content, keep it inline in the CLAUDE.md index instead of creating a separate doc file. This prevents tiny projects from getting 8 doc files with 3 lines each.
   - Map detection results → doc files (see Detection Matrix)
8. **Generate `.claude/docs/*.md`** — each doc with YAML frontmatter and content from its template (see Doc File Templates). Create `.claude/docs/` directory if needed.
9. **Generate CLAUDE.md index** — lightweight routing table (see Index Template). Preserve any Custom Rules section and any content outside the v2 markers.
10. **Generate thin pointer files** — pure redirects for other AI tools (see Pointer Templates). Only create if file doesn't already exist with custom content.
11. **Preserve human content** — any content outside `<!-- project-doc:v2 -->` / `<!-- project-doc:v2:end -->` markers is preserved untouched. The `## Custom Rules` section inside the markers is also preserved across regenerations.
12. **Write all files**
13. **Run verification** (see Verification section)
14. **Report to user:**
    - Token impact (before/after comparison)
    - List of docs generated with line counts
    - List of pointer files created/updated/skipped
    - Any `[TODO: ...]` gaps found
    - Verification results
    - Knowledge graph status + suggestion (see Knowledge Graph Integration section)
    - Stale test artifacts detected: {N} ({breakdown}). Offer `/project-doc clean` (see Artifact Cleanup) — detect & report only, never delete here
    - Ask: "Quer preencher os TODOs agora?"

## Sources — cascata de 5 tiers (v3)

v2 documentava só a partir de **arquivos**. v3 colhe de TODA a evidência do projeto, em cascata ordenada por densidade/custo. Cada tier alimenta os MESMOS campos dos templates v2 (`## Decisões de Arquitetura`, `## Gotchas`, etc.) — a estrutura de saída é idêntica; muda a fonte e o motor.

- **Tier 1 — Arquivos** (a Detection Matrix abaixo): stack, deps, rotas, schema, config. Custo baixo. É o scan que a v2 já fazia. Vive **nesta skill** (julgamento de leitura).
- **Tier 2 — Destilado pronto:** `.claude/HANDOFF*.md`, `memory/*.md`, `graphify-out/`, `.claude/ata/`. Decisões/gotchas já mastigados. Colhido pelo lib (`journal.py`).
- **Tier 3 — git log:** o "porquê" das mudanças (mensagens de commit + arquivos tocados, que viram âncoras). Colhido pelo lib.
- **Tier 4 — Transcripts:** as sessões `.jsonl` de **todos os slugs sob o projeto** — direcionamentos, rejeições, decisões que nunca viraram arquivo. Custo alto. Colhido pelo lib via a engine compartilhada (`collect_engine.py`).
- **Tier 5 — O humano:** lacuna crítica sem fonte (ex: host SSH que não está em arquivo nenhum) → **pergunte ao Pedro**, em vez de marcar `[TODO]` e seguir. Vive **nesta skill**.

Tiers 2-4 são **mecânicos** e vivem em `plugins/project-doc/lib/journal.py` (degrada gracioso: sem a engine vendorada, pula o tier 4 e usa tiers 1-3). Tier 1 e tier 5 são desta skill. O fluxo completo (coleta → projeção) está em **Collect & Project**.

## Tier 1 — Detection Matrix (scan de arquivos)

For each section, scan these files (read only those that exist). Detection results are grouped by their target doc file.

### Pre-Detection (run first, feeds multiple docs)

**Project Type Detection:**
- **app** — has server entry (main.py, index.ts, server.js), Dockerfile, docker-compose.yml, port bindings, deploy scripts
- **lib** — has exports field in package.json, publishConfig, peer dependencies, or main/module/types fields pointing to dist/
- **cli** — has bin field in package.json, or depends on commander/yargs/meow/oclif/click/argparse with entry script
- Default to **app** if unclear. Libs and CLIs omit: infrastructure, deploy, services docs

**Package Manager Detection:**
- pnpm-lock.yaml → pnpm
- yarn.lock → yarn
- bun.lockb → bun
- package-lock.json → npm
- (check in this order — first match wins)

**Knowledge Graph Detection (graphify):**
- Check for `graphify-out/graph.json`. If present, the project has a graphify knowledge graph.
- **Staleness:** compare `graphify-out/graph.json` mtime (or the `date` in `graphify-out/cost.json` last run) against the most recent source-file change (`git log --format=%aI -1`). If sources are newer → graph is stale.
- **No FULL/`--deep` (v3.2), o grafo é GARANTIDO, não só detectado** — o passo 0.0 do Workflow roda `graphify update --force` (cria/atualiza) e destila o mapa via `graph_map.py`, que **prioriza os arquivos de cada concern por fan-in** pra leitura profunda. Nos modos leves, staleness/ausência só viram **sugestão** (ver **Knowledge Graph Integration**).
- This feeds the "## Knowledge Graph" index section (generated only when the graph exists), the **graph-ranked file reading** in the Workflow (Fase A), and the proactive suggestions.

**Complexity Assessment (when to suggest CREATING a graph):**

**Rule: if `graphify-out/` does not exist, ALWAYS suggest creating a graph. Unconditional.** No triviality test, no coupling assessment, no "this one won't compensate", no gating on size / file count / language / architecture. There is no project that is exempt from the suggestion. This judgment was removed on purpose: the model has repeatedly skipped graphs on projects that clearly warranted one, so it does not decide whether a graph is worth it. The model's only job is to **offer**; whether to actually run `/graphify` (which costs tokens/time) is the user's call, like deploy.

The signals below are NOT a gate — they only tell you to suggest with *extra conviction* and to name the signal you saw. Their absence NEVER cancels the suggestion:
- monorepo (`apps/` or `packages/`)
- code spread across ≥3 directories, or multiple distinct modules
- multiple languages in one repo (e.g. Rust backend + Svelte/TS frontend)
- event-driven / daemon / WebSocket / DI-container / plugin architecture — wiring that isn't obvious from imports
- presence of `docs/ARCHITECTURE*`, ADRs, or a CONTEXT.md — the team already flagged it as complex
- many cross-module references / high fan-in on shared state or service clients

Frame the suggestion by **value**: "o grafo mapeia relações e ajuda a localizar/debugar". Generating a graph has minimal downside (some processing time/tokens; `graphify-out/` can be gitignored), so always offer.

**Test Framework Detection:**
- jest.config.{js,ts,cjs,mjs}, jest field in package.json → Jest
- vitest.config.{js,ts,mjs}, vite.config with test → Vitest
- pytest.ini, conftest.py, pyproject.toml [tool.pytest] → pytest
- .rspec, spec/ dir → RSpec
- go test files (*_test.go) → go test
- Cargo.toml with [dev-dependencies] + #[test] in src → cargo test

### Detection → Doc Mapping

**→ architecture.md**
- **Visão geral** — README.md, package.json (description), pyproject.toml, go.mod, pom.xml, build.gradle, Gemfile, composer.json, .csproj/.sln, mix.exs
- **Stack** — package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml, docker-compose.yml, Dockerfile*, .tool-versions, .node-version, .python-version, pom.xml, build.gradle, Gemfile, composer.json, .csproj/.sln, mix.exs
- **Estrutura de diretórios** — ls top-level + ls of src/, app/, lib/, pages/, components/ if they exist
- **Dependências críticas** — package.json (non-obvious deps), requirements.txt (specialized libs), go.mod, pom.xml, build.gradle, Gemfile, composer.json
- **Decisões de arquitetura** — docs/ARCHITECTURE.md, docs/ADR*, docs/decisions/, README.md architecture sections
- **Documentação disponível** — docs/*.md, README.md, CONTRIBUTING.md, API docs

**→ database.md**
- docker-compose.yml (postgres/mysql/mongo/redis images), .env (DB_*/DATABASE_* vars), prisma/schema.prisma, drizzle.config.*, knexfile.*, sqlalchemy configs, migrations/ dir

**→ api.md**
- app/api/ dir, routes/ dir, controllers/ dir, openapi.yaml, openapi.json, swagger.json, swagger.yaml, graphql schema files. Skip if no route patterns found

**→ deploy.md** (skip for lib/cli)
- scripts/deploy*, deploy.sh, Makefile, CI/CD configs — READ the full deploy script to document the complete flow
- Acesso remoto: scripts/deploy*, .env (SERVER/VPS/SSH vars), Makefile (deploy targets), CI/CD configs (.github/workflows/*.yml, .gitlab-ci.yml)

**→ infrastructure.md** (skip for lib/cli)
- **Serviços/Containers** — docker-compose.yml, docker-compose.*.yml
- **Portas e URLs** — docker-compose.yml (ports), .env/.env.example (PORT/URL vars), nginx/*.conf, Dockerfile (EXPOSE), server config files
- **Infra** — nginx/, nginx.conf, nginx/conf.d/*.conf, Caddyfile, traefik configs, certbot/SSL references

**→ env-vars.md**
- .env.example, .env.local.example, .env (names only, NEVER values), docker-compose.yml (environment section), .env.development, .env.staging, .env.production, .env.local, .env.test

**→ auth.md**
- middleware.ts, middleware.js, src/middleware.*, auth/, src/auth/, lib/auth*, next-auth config, passport config, JWT patterns in code

**→ patterns.md**
- **Padrões do projeto** — tsconfig.json (paths), .eslintrc*, .prettierrc*, src/ structure conventions, existing code patterns
- **Gotchas** — Known from scanning (e.g., network_mode:host, special env handling, non-standard configs)
- **Testes** — detect framework (see above), add test command with framework name

**→ Inline in CLAUDE.md index (not separate docs)**
- **Comandos úteis** — package.json (scripts), Makefile (targets), scripts/*.sh, pyproject.toml (scripts) — top 5 only
- **Top gotchas** — the 3-5 most dangerous gotchas (subset of what goes in patterns.md)

### Monorepo-Specific Detection

When monorepo is detected, additionally scan per app. **This scan is mandatory for every app, every run — no exceptions, no shortcuts, no copying from existing docs.**

For each directory in `apps/` (or `packages/`) that has a Dockerfile or main entry file:

- **App stack** — package.json, requirements.txt, pyproject.toml (only if different from common stack)
- **App port** — docker-compose.yml (port mapping for this service), main entry file (uvicorn/express port)
- **App deps** — requirements.txt, package.json — read the full file, list all non-obvious deps specific to this app
- **App env** — apps/X/.env, apps/X/.env.example (app-specific vars, names only)
- **App DB/migrations** — apps/X/database.py, apps/X/migrations/, docker-compose DB service for this app
- **App gotchas** — Non-standard patterns, exceptions to the common pattern (e.g., Next.js app in a FastAPI monorepo)
- **App description** — read main.py or index file to understand what the app actually does now (description may have drifted)

Also scan shared infrastructure:
- `shared/`, `shared_lib/`, `packages/shared/` — common libraries
- `.env.shared`, `.env.common` — shared env vars
- Root docker-compose `networks`, `volumes` definitions

Per-app detection results feed into app-specific subdocs under `.claude/docs/{app-name}/`.

## Collect & Project (v3 — o motor)

A v3 separa **coleta** (mecânica, código) de **projeção** (julgamento, você). Nunca pule a projeção — o lib não decide relevância nem reconcilia; isso é seu.

### Collect (rode o lib)

Roda a parte mecânica — minera tiers 2-4, passa pelo **scrubber** (barreira de secret), dá append no journal append-only e devolve os findings **vivos**:

```bash
python3 plugins/project-doc/lib/journal.py update  --project-root "<root>" [--session "$CLAUDE_CODE_SESSION_ID"]
# cold-start / backfill de TODAS as sessões:  python3 .../journal.py deep    --project-root "<root>"
# re-derivar do journal sem minerar:          python3 .../journal.py rebuild --project-root "<root>"
# só ler os findings vivos:                   python3 .../journal.py fold    --project-root "<root>"
```

Saída JSON: `{mode, new_events, live_count, stale_ids, live:[{id, raw_kind, text, anchors, source, scrubbed}]}`.

- **Journal** (`.claude/.project-doc/findings.jsonl`, **versionado**): append-only, o "super git" do conhecimento — eventos `discovered`/`invalidated`/`curated`, **nunca apaga**. O estado vivo = *fold* dos eventos. É o único veículo do conhecimento entre máquinas (transcripts são locais e não viajam).
- **Ledger** (`.claude/.project-doc/ledger.json`, **versionado**): `mined_sessions`/`last_commit`/`distilled_hashes` — é o que faz a rodada padrão ser um **delta** (não re-minera o que já foi). 2ª rodada sem mudança = `new_events: 0`.
- **`stale_ids`**: findings cujas âncoras um commit recente tocou (backward delta). **Não estão mortos** — são suspeitos que precisam de re-validação na projeção.

### Project (seu julgamento)

Pegue os findings vivos + o scan tier 1 e **projete** na doc canônica (CLAUDE.md + `.claude/docs/`). Aqui entra o que o código não faz:

- **Relevância:** filtre os candidatos doc-worthy. Os `gate=True` (direcionamentos/rejeições/decisões — `raw_kind` user_directive/tool_rejection/ask_answer) são primários; descarte ruído (status update, conversa trivial).
- **kind → seção:** gotcha → `patterns.md`/Gotchas (+ top 3-5 no CLAUDE.md); decisão → `architecture.md`/Decisões; feature → Visão Geral; convenção → `patterns.md`. O `kind` semântico é atribuído **aqui** (não no journal).
- **Reconciliação (OBRIGATÓRIA):** todo finding histórico é confirmado contra o **código atual** antes de entrar. Vale → entra. Não dá pra confirmar → entra marcado `[relatado]`. O código **contradiz** → NÃO entra e você o mata:
  `python3 .../journal.py invalidate --project-root "<root>" --id <id> --reason "..."`. Trate os `stale_ids` com prioridade — são os suspeitos do backward delta.
- **Curadoria:** se o Pedro editar à mão um finding gerado, registre pra sobreviver à re-projeção:
  `python3 .../journal.py curate --project-root "<root>" --id <id> --text "..."` (a projeção respeita o texto curado).

A doc canônica é **derivada e descartável** (`--rebuild` re-cria do journal). O journal é a verdade; a doc é a vista. Critério de aceite: a doc cita ≥1 gotcha/decisão que só existe em sessão/handoff, e **nenhum** gotcha que o código atual contradiz.

## Workflow Engine — FULL e --deep mineram via Workflow (v3.1) + grafo dirige a leitura profunda (v3.2)

**O problema que isso resolve:** numa janela única, sob volume de contexto, o agente "tira o pé" — corta o Tier 1 scan (não lê o código de verdade) e a Reconciliação (confere 5 de 30 `stale_ids`). A COLETA (Python) é determinística e não tira o pé; quem tira é a **projeção** quando feita numa janela só. A solução: nos modos que mineram, a projeção roda como um **Workflow** com **fan-out por concern** — cada agente recebe uma fatia (um doc-alvo), tem working-set pequeno, e não tem medo do volume. A soma cobre tudo.

### Fronteira de modos — quando é Workflow, quando é single-agent

| Modo | Motor | Por quê |
|---|---|---|
| **FULL** (`/project-doc`) e **`--deep`** | **Workflow** (fan-out) | mineram fontes novas + projetam tudo → é onde o medo de contexto bate |
| incremental (`/project-doc <doc>`), `index`, `pointers`, `--rebuild`, `migrate`, `verify`, `clean` | **single-agent** (como antes) | não mineram / 1 concern só / re-projeção pura → nada a paralelizar |

- `--rebuild` re-projeta do journal **sem minerar** → single-agent, sem backup, sem garimpo.
- Flag de escape **`--solo`**: força FULL/--deep a rodar single-agent (debug/projeto pequeno). Sem `--solo`, FULL/--deep **disparam o Workflow direto** — não anuncie custo nem peça confirmação.

### Passo 0.0 — Grafo é documentação: garantir + mapear (v3.2)

**Premissa do v3.2:** nenhuma versão do project-doc jamais leu o código-fonte de verdade — o Tier 1 sempre foi uma allowlist (manifestos/configs/schemas/rotas) + `ls`. A única coisa que mapeia o codebase inteiro é o **grafo (graphify)**, mas até a v3.1 o project-doc só o **sugeria**, nunca o rodava nem o consumia. No v3.2 isso vira: **o grafo é parte da documentação, obrigatório no FULL/`--deep`** — ele garante o mapa que dirige a leitura profunda do código (Fase A) e audita a cobertura no fim (gate). **Postura: roda sempre, informa, não oferece** (≠ os modos leves, que mantêm só a sugestão — ver **Knowledge Graph Integration**).

No FULL/`--deep` (não nos modos leves), ANTES da checagem ativa:

1. **Garante o grafo fresco, sem perguntar.** Detecta staleness (graph.json ausente, ou mtime < `git log --format=%aI -1`) e roda:
   ```bash
   graphify update "<root>" --force    # `update`: re-extrai por AST, ZERO LLM, ~segundos, não-interativo, idempotente
                                        # `--force`: sobrescreve graph.json mesmo se a re-extração tiver MENOS nós (após refactor que apaga código)
   ```
   Ausente → cria (AST); stale → atualiza; fresco → no-op. O `--force` garante o overwrite em refactors destrutivos (sem ele, uma re-extração menor poderia ser recusada). **Não anuncie custo nem peça confirmação** — informa "grafo: criado / atualizado / já fresco" no Output Protocol. O labeling LLM de comunidades (nomes bonitos) é upgrade opcional via `/graphify` completo, **fora** do caminho crítico; `update --force` preserva labels já existentes.
   - **Escapes:** `--solo` (single-agent, pula o grafo) e um opt-out em `.claude/settings.json` (`project_doc.skip_graph: true`) pra quem não quiser; o **default é rodar**.
   - **`graphify` não instalado** → degrada gracioso: pula o grafo, avisa "graphify ausente — fan-out sem mapa (v3.1)", segue.
2. **Destila o grafo num mapa enxuto** (o grafo bruto tem milhares de nós — não engula inline):
   ```bash
   python3 plugins/project-doc/lib/graph_map.py --project-root "<root>"
   ```
   Devolve JSON: `{available, stats, files[], god_nodes[], communities[], generic_communities[], hyperedges[]}` (ver **Schemas / GRAPH_MAP**). `available:false` ⇒ sem grafo ⇒ comportamento v3.1 (fan-out sem mapa). O mapa alimenta o particionamento (passo 4) e a leitura profunda (Fase A).



Antes de minerar, **classifique a doc existente** (esta é a checagem ativa — roda no passo 0 da casca):

- **Ausente** (sem `.claude/CLAUDE.md`) → CREATE: Workflow + `deep` (cold-start). Sem backup/garimpo (não há doc antiga).
- **Fora do padrão atual** → **sequência full forçada**: backup + Workflow + **`deep`** + garimpo. É "fora do padrão" se QUALQUER:
  - markers v1 (`project-doc:start/end`), **ou sem markers**, ou doc escrita à mão;
  - markers v2 **mas sem journal** (`.claude/.project-doc/findings.jsonl` ausente) → doc gerada por motor pré-v3, **nunca minerada** — o caso que mais engana (parece boa, o agente a "seguia");
  - o marker registra `gen=<versão>` **menor** que a versão atual do plugin → o motor mudou de padrão desde a última geração.
- **No padrão** (markers v2 + journal presente + `gen` atual) → FULL normal: Workflow + `update` (delta) + backup/garimpo (sempre que há doc, pra preservar nuance).

A regra-mãe: **doc fora do padrão não é base confiável** — não faça update delta leve em cima dela; reconstrua por mineração (`deep`) e use a antiga só como fonte de nuances (garimpo). O marker passa a gravar a versão do gerador — ver **Update Mechanism**.

### A casca (esta skill) vs o Workflow (o motor)

Espelha o qa-loop: o Workflow roda em background e **não pergunta nada no meio**; tudo entra via `args`, os gates são lógica do script (JS), não "o agente lembrar a regra".

**CASCA — passo 0 (antes de disparar):**
1. Identify root/layout/type/PM + **grafo garantido + mapa (0.0)** + **checagem ativa (0.1)** → decide `update` vs `deep` e se força a sequência.
2. **Backup** (se há doc): garanta `.claude/.project-doc/backups/` no `.gitignore` (é **efêmero, não versiona** — ao contrário do journal/ledger, que SÃO versionados); então `cp` de `CLAUDE.md` + `.claude/docs/` → `.claude/.project-doc/backups/<UTC-ts>/` + `MANIFEST.json` (git_head, mode). Sem agente.
3. Roda a **coleta Python 1×** (`journal.py update|deep`) → `{live[], stale_ids, ...}`. A mineração **nunca** entra no fan-out (é determinística e barata).
4. **Dimensiona** o fan-out e **particiona** por concern, carregando DUAS coisas por concern: (a) os findings (`live[]`/`stale_ids`, roteamento grosso por `raw_kind`+anchor: gotcha→patterns, decisão→architecture, anchor `schema.prisma`→database, etc.) **e** (b) a **lista de arquivos-fonte priorizada pelo grafo** — cruze a Detection Matrix invertida (padrões de path: `schema.prisma`→database, `routes/`→api, etc.) com `GRAPH_MAP.files[]` (ranqueado por fan-in) pra dar a cada agente seus arquivos do concern **em ordem de relevância**, mais os `god_nodes` que caem na fatia. As `communities`/`hyperedges` nomeadas do grafo (módulos/workflows que a Detection Matrix não vê) vão pro concern **architecture** (conteúdo de `architecture.md`/Decisões), não viram eixo de fan-out. No monorepo, um sub-agente por `app×concern` que diverge do comum.

**WORKFLOW — fases:**
- **Fase A — Scan+Reconcile + leitura profunda (PARALELO):** 1 agente por concern. Cada um executa o protocolo **Project (seu julgamento)** acima, restrito à sua fatia, e agora faz **leitura profunda guiada pelo grafo** (capacidade nova do v3.2 — caminho 1):
  - **Lê o código-fonte real** dos arquivos da fatia, na **ordem de fan-in** que o `GRAPH_MAP` deu (maior fan-in primeiro) — não só os manifestos, mas o **corpo das funções** dos `god_nodes` e dos arquivos quentes. Daí extrai gotchas/convenções/decisões que **só o código revela** (o que o AST não vê: invariantes, efeitos colaterais, "por que assim").
  - **Trava de contexto:** lê integralmente os **top-N por fan-in** do concern (teto por agente); o resto entra como "coberto por menção", não leitura integral. O agente **reporta no `DOC_SECTION` o que leu de fato vs o que só listou** (`files_read[]` / `files_listed[]`).
  - Sem grafo (`available:false`) → cai no v3.1: lê os arquivos da Detection Matrix sem ranking, mesma reconciliação.
  - Reconcilia cada finding da fatia contra o código que leu (confirma / `[relatado]` / propõe invalidação), escreve a seção. Devolve `DOC_SECTION`. **A doc nova é a BASE canônica — projetada SEM ver a doc antiga.**
- **Fase B — Garimpeiro de nuances (1 agente, só se há doc antiga):** recebe a doc antiga (backup) + a nova + leitura do código/journal. Tarefa **negativa**: achar info verdadeira presente só na antiga e **ausente** na nova; validar cada candidata contra o código. Devolve `NUANCE_CANDIDATES`. Não reescreve nada — só propõe adições.
- **Fase C — Stitch (JS puro, sem LLM):** aplica os gates (abaixo), dedup, monta o índice. Devolve `STITCH_RESULT`.

**CASCA — passo final (depois do Workflow):**
5. **Só a casca escreve no journal** (serializa o append-only): aplica as invalidações aprovadas + reintegra **automático** as nuances confirmadas — `curate` (finding existe, perdeu o tom), `adopt` (nuance que **nunca** foi minerada), `invalidate` (a antiga contradiz o código).
6. **Re-projeta** (`journal.py rebuild`) pra materializar as nuances pela porta canônica — sem isso, o próximo `--rebuild` apagaria a edição.
7. Escreve os arquivos + **Verification** (inclui o check de secret) + relatório com telemetria (nº de agentes, invalidações aplicadas vs propostas, nuances reintegradas).

### O script do Workflow (molde — estilo qa-loop)

```javascript
export const meta = {
  name: 'project-doc-mine',
  description: 'Minera a doc via fan-out por concern; cada agente lê o código da sua fatia e reconcilia',
  phases: [{ title: 'Scan+Reconcile' }, { title: 'Garimpo' }, { title: 'Stitch' }],
}
// args = { root, deep, hasOldDoc, backupPath, graphMap,                  // graphMap = saída do graph_map.py (ou {available:false})
//          concerns:[{key, app, files[], findings[], staleIds[], godNodes[], template}] }   // files[] já vem ranqueado por fan-in

phase('Scan+Reconcile')                                  // FAN-OUT: 1 agente por concern
const sections = (await parallel(args.concerns.map(c => () =>
  agent(scanReconcilePrompt(args.root, c), { label: `concern:${c.app ? c.app+'/' : ''}${c.key}`,
    phase: 'Scan+Reconcile', schema: DOC_SECTION })
))).filter(Boolean)

let nuances = { candidates: [] }
if (args.hasOldDoc) {                                     // só se havia doc antiga
  phase('Garimpo')
  nuances = await agent(garimpoPrompt(args.root, args.backupPath, sections),
    { label: 'garimpeiro', phase: 'Garimpo', schema: NUANCE_CANDIDATES }) || nuances
}

phase('Stitch')                                          // GATES = JS puro, sem LLM
const stitched = stitchAndGate(sections, nuances, args.graphMap)  // adjudica invalidação, dedup, inline, secret, budget + AUDITORIA grafo×doc
return { sections, nuances, stitched }
```

A casca lê o `return` e executa os efeitos colaterais (passo final). `scanReconcilePrompt`/`garimpoPrompt`/`stitchAndGate` são helpers do próprio script: os dois primeiros montam o prompt do agente a partir da fatia; o terceiro é JS determinístico.

### Sequência "melhor dos dois mundos" (quando há doc antiga)

A trava anti-"caminho fácil" é **estrutural**, não confiança: a doc nova já existe e é a base ANTES de a antiga ser lida (Fase B vem depois da A). O garimpeiro só pode **propor adições validadas contra o código** — nunca reescrever, nunca copiar a antiga. Conteúdo presente nas duas é descartado por construção. Fluxo: backup → Fase A (doc nova, isolada) → Fase B (garimpa o que faltou, valida) → merge **automático** das confirmadas via journal → `rebuild` materializa. Resultado: mineração fresca + nuances curadas que só viviam na doc antiga.

### Schemas (campos pros gates, não texto solto)

- **`GRAPH_MAP`** (saída do `graph_map.py`, lido pela casca; não é schema de agente) = `{available, stats{nodes, links, hyperedges_total, communities_named, god_nodes}, params{god_min, hyper_min}, files[{source_file, fan_in, node_count, god_nodes[]}], god_nodes[{id, label, source_file, source_location, fan_in, fan_in_total, relations_in}], communities[{label, size, community_ids[], files[]}], generic_communities[{label, count}], hyperedges[{id, label, confidence_score, nodes[], source_files[]}]}`. `available:false` ⇒ sem grafo (`{available, reason, expected_path}`). A casca pode ignorar campos extras — o contrato é um superset estável.
- **`DOC_SECTION`** = `{concern, app, complete, doc_path, inline, body_md, confirmed_ids[], relatado_ids[], invalidations[{id, reason, evidence, confidence}], nuances[], todos[], secret_suspects[], files_read[], files_listed[]}` (os dois últimos: o que o agente leu integralmente vs só listou — prova da leitura profunda v3.2).
- **`NUANCE_CANDIDATES`** = `{candidates[{type, claim, where_in_old, validation{status: confirmed|unconfirmable|contradicted, evidence}, match_to_journal{finding_id, relation: curate_existing|new_discovered}, proposed_action: curate|adopt|invalidate|drop}], summary}`
- **`STITCH_RESULT`** = `{index_md, docs_to_write[], inline_sections[], approved_invalidations[], rejected_invalidations[], dedup_log[], audit_warnings[]}` (`audit_warnings`: god nodes / comunidades / hyperedges do grafo sem cobertura na doc — ver gate 7).

### Gates determinísticos (JS no Stitch, não o agente)

1. **`complete`** — `DOC_SECTION.complete===false` ⇒ o concern não entra como pronto (re-roda ou marca `[TODO: scan incompleto]`). Nunca declarar a doc pronta com concern incompleto.
2. **Invalidação (o crítico)** — o agente **propõe**; o JS **aplica** só se `confidence==="high"` **E** `evidence` não-vazio **E** o `id` está no `live[]`. Invalidar é destrutivo no journal — low-confidence vira `[relatado]`, não morte.
3. **Reintegração de nuance** — só `validation.status==="confirmed"` reintegra automático; `unconfirmable` → `[relatado]`; `contradicted` → `invalidate` da versão antiga.
4. **Dedup** — gotcha repetido em 2 concerns (match por anchor+texto) fica em 1 (patterns vence).
5. **Secret (CRITICAL)** — regex dos padrões óbvios (JWT `eyJ…`, `AKIA…`, PEM, conn-string) sobre todo `body_md` antes de escrever; match ⇒ não escreve, devolve. É a 2ª barreira (o scrubber Python é a 1ª, roda ao persistir no journal).
6. **Token budget / cobertura** — índice >150 linhas ⇒ comprime; área detectada (ex: docker-compose) sem seção ⇒ WARN.
7. **Auditoria grafo×doc (v3.2 — o repasse de completude)** — só se `graphMap.available`. Cruza o grafo contra o texto gerado (todos os `body_md` + índice): **god node** ou **comunidade nomeada** (não-generic) cujo `label`/`source_file` **não aparece** em nenhuma seção ⇒ `audit_warnings += "área importante não documentada: <X>"`; **hyperedge** ≥0.85 sem menção ⇒ candidato a nota de arquitetura. É o grafo como completeness-critic — orienta no início (mapa), audita no fim. WARN não bloqueia; alimenta o relatório (ou uma 2ª leva de agente pro gap, se a casca optar).

## CLAUDE.md Index Template

The CLAUDE.md index is the always-loaded routing table. Two variants exist: Standard and Monorepo.

### Standard Index Template

```markdown
<!-- project-doc:v2 gen=3.3 -->
<!-- Generated by /project-doc on {YYYY-MM-DD} — run /project-doc to update -->

# Project Reference

## Visão Geral
{1-2 sentence description of what this project is}
**Tipo:** {app | lib | cli} · **Stack:** {top 2-3 technologies} · **PM:** {pnpm | yarn | bun | npm}

## Quick Commands
```bash
# Dev
{command}

# Build
{command}

# Test ({framework})
{command}

# Deploy
{command}

# Lint
{command}
```

## Gotchas Críticos
- {Top 3-5 most dangerous gotchas — things that cause bugs or data loss regardless of what you're working on}

## Documentation Index

- **[architecture.md](.claude/docs/architecture.md)** — project structure, stack details, dependencies, design decisions
  → understanding the project, adding modules, onboarding
- **[database.md](.claude/docs/database.md)** — schema, ORM, migrations, access commands
  → writing migrations, querying data, changing schema
- **[api.md](.claude/docs/api.md)** — endpoints, route patterns, specs
  → adding endpoints, changing routes, API integration
- **[deploy.md](.claude/docs/deploy.md)** — deploy scripts, CI/CD, server access, rollback
  → deploying, server config, CI/CD changes
- **[infrastructure.md](.claude/docs/infrastructure.md)** — Docker services, ports, proxy, SSL, networking
  → infra changes, port conflicts, networking debug
- **[env-vars.md](.claude/docs/env-vars.md)** — all environment variables by concern
  → adding env vars, config changes, credentials
- **[auth.md](.claude/docs/auth.md)** — authentication flow, middleware, permissions
  → auth changes, new protected routes, permissions
- **[patterns.md](.claude/docs/patterns.md)** — code conventions, naming, imports, full gotchas list
  → writing new code, following conventions, avoiding pitfalls

{Only include entries for docs that were actually generated. Omit entries where no doc was created.}

{If any section was kept inline due to ≤5 lines threshold, include it here as a subsection instead of a doc link:}

## {Inline Section Name}
{content, ≤5 lines}

{Only if graphify-out/graph.json exists — see Knowledge Graph Integration section:}

## Knowledge Graph (graphify)
Grafo do projeto em `graphify-out/`. **Antes de analisar arquitetura ou mexer em código compartilhado, consultar o grafo** em vez de grep cego: `graphify query "<pergunta>"` (relações, blast radius), `graphify explain "<símbolo>"`, `graphify path "A" "B"`. É mapa, não verdade — confirmar causa-raiz no código real; edges INFERRED são hipóteses. Snapshot: após um ciclo de mudanças, `/graphify <path> --update`.

## Custom Rules

{Preserved from previous generation — human-written content. If no custom rules exist, include this section empty so users know where to add them.}

<!-- project-doc:v2:end -->
```

### Monorepo Index Template

```markdown
<!-- project-doc:v2 gen=3.3 -->
<!-- Generated by /project-doc on {YYYY-MM-DD} — run /project-doc to update -->

# Project Reference

## Visão Geral
{1-2 sentence description. Mention it's a monorepo with N apps.}
**Tipo:** monorepo · **Stack:** {common stack, top 2-3 techs} · **PM:** {pm}

## Quick Commands
```bash
# Dev (any app)
{command pattern, e.g., cd apps/{name} && uvicorn main:app --port {port} --reload}

# Deploy selective
{command, e.g., ./deploy.sh {app1} {app2}}

# Deploy all
{command}

# Lint
{command}

# Tests
{command}
```

## Gotchas Críticos
- {Top 3-5 project-wide gotchas}

## Apps

- **{app-name}** — porta {port} — {1 sentence what it does} → [docs](.claude/docs/{app-name}/)
- **{app-name}** — porta {port} — {1 sentence} → [docs](.claude/docs/{app-name}/)
{1 line per app. Omit app doc link if app has no unique docs (follows common pattern exactly).}

## Shared Documentation

- **[architecture.md](.claude/docs/architecture.md)** — overall structure, shared libs, common patterns
  → project-wide changes, new apps, onboarding
- **[infrastructure.md](.claude/docs/infrastructure.md)** — Docker, Nginx, networking, ports
  → infra changes, proxy config, new services
- **[deploy.md](.claude/docs/deploy.md)** — deploy script, CI/CD, server access
  → deploying, server config
- **[env-vars.md](.claude/docs/env-vars.md)** — shared + per-app env vars
  → config changes, new vars
- **[patterns.md](.claude/docs/patterns.md)** — common conventions, full gotchas list
  → writing new code, following project patterns

## Per-App Documentation

- **[{app-name}/api.md](.claude/docs/{app-name}/api.md)** — {app} endpoints
- **[{app-name}/database.md](.claude/docs/{app-name}/database.md)** — {app} schema, migrations
{Only list per-app docs that were generated. Omit apps that follow common pattern exactly.}

{Only if graphify-out/graph.json exists — see Knowledge Graph Integration section:}

## Knowledge Graph (graphify)
Grafo do monorepo em `graphify-out/`. **Antes de analisar arquitetura ou mexer em código compartilhado, consultar o grafo** em vez de grep cego: `graphify query "<pergunta>"` (relações, blast radius cross-app), `graphify explain "<símbolo>"`, `graphify path "A" "B"`. É mapa, não verdade — confirmar causa-raiz no código real; edges INFERRED são hipóteses. Snapshot: após um ciclo de mudanças, `/graphify <path> --update`.

## Custom Rules

{Preserved from previous generation.}

<!-- project-doc:v2:end -->
```

## Doc File Templates

Each `.claude/docs/*.md` file follows this structure. Content level should be detailed — these files are loaded on-demand, so depth is free.

### Frontmatter (required for all docs)

```yaml
---
generated: {YYYY-MM-DD}
project: {project-name}
scope: {comma-separated list of key source files this doc was generated from}
---
```

### architecture.md

```markdown
{frontmatter}

# Architecture

## Visão Geral
{Expanded project description — what it does, who uses it, key workflows}

## Stack
- **Language:** {language} {version}
- **Framework:** {framework} {version}
- **Runtime:** {runtime} {version}
- **Package manager:** {pm} (detected from lockfile)
- **Database:** {type} {version}
- **Testing:** {framework}
- {other key technologies}

## Estrutura de Diretórios
```
{tree — can go deeper than 2 levels here, show meaningful structure}
```

## Dependências Críticas
- `{package}` — {why it's important, what it does that's non-obvious}

## Decisões de Arquitetura
- {Decision — 1 line each, e.g., "SRS uses network_mode:host because UDP+Docker NAT breaks SRT"}

## Documentação Disponível
- **{doc name}** — {path} — {what it covers}
```

### database.md

```markdown
{frontmatter}

# Database

## Overview
- **Tipo:** {PostgreSQL/MySQL/MongoDB/Redis/SQLite}
- **Host/Porta:** {host:port or socket}
- **ORM/Driver:** {Prisma/Drizzle/Knex/SQLAlchemy/raw driver}

## Schema
- **Path:** {path to schema file}
- **Models:** {count and list of key models with brief descriptions}

## Migrations
- **Path:** {path to migrations dir}
- **Run:** `{migration command}`
- **Create:** `{create migration command}`

## Env Vars
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

## Seeds
- {path and command if exists}

## Admin Tool
- {pgAdmin/Adminer/RedisInsight if configured}

## Acesso Direto
```bash
{command to connect, e.g., docker exec -it db psql -U user dbname}
```
```

### api.md

```markdown
{frontmatter}

# API

## Overview
- **Tipo:** {REST | GraphQL | gRPC | mixed}
- **Base URL:** {/api/v1, /graphql, etc.}
- **Padrão de rotas:** {e.g., src/app/api/[resource]/route.ts}
- **Spec:** {path to openapi.yaml/swagger.json if exists}

## Route Groups
{List all route groups with method counts}
- **{/api/resource}** — {N routes} — {brief description}

## Authentication
- {Which routes require auth, which are public}

## Health Check
- {endpoint and expected response}
```

### deploy.md

```markdown
{frontmatter}

# Deploy

## Script
- **Path:** `{path to deploy script}`
- **Flags:** `{--dry-run, --force, etc.}`

## Flow
{Step-by-step of what the deploy script does — read the actual script}
1. {step}
2. {step}
3. {step}

## CI/CD
- **Platform:** {GitHub Actions/GitLab CI}
- **Config:** {path to workflow file}
- **Triggers:** {push to main, manual, etc.}

## Rollback
- {how to rollback if deploy fails}

## Server Access
- **Host:** `{user@host}` or `{env var that holds it}`
- **Key:** `{key path}`
- **Project path (server):** `{path on server}`
```

### infrastructure.md

```markdown
{frontmatter}

# Infrastructure

## Serviços / Containers
- **{name}** — {image} — ports {host:container} — {network_mode, volumes, depends_on, healthcheck}

## Portas
- **{port}** {TCP/UDP} — {service} — {internal/external, proxy target}

## Proxy
- **Tipo:** {Nginx/Caddy/Traefik}
- **Config:** {path to proxy config}
- **Routing:** {what it proxies where}

## SSL
- {Let's Encrypt/self-signed/managed}

## Networking
- **Docker network:** {name, driver}
- {any special networking setup}

## Cron / Scheduled Tasks
- {if any}
```

### env-vars.md

```markdown
{frontmatter}

# Environment Variables

## Files Detected
- {list all .env* files found and their purpose}

## Variables

### App Config
- `{VAR_NAME}` — {what it does}

### Database
- `{DB_HOST}` — {what it does}

### Auth / Secrets
- `{JWT_SECRET}` — {what it does}

### External Services
- `{API_KEY_SERVICE}` — {what it does}

### Feature Flags
- `{FEATURE_X}` — {what it does}

{Group by concern. List every var from .env.example. Names only, NEVER values.}
```

### auth.md

```markdown
{frontmatter}

# Authentication

## Overview
- **Tipo:** {JWT/Session/OAuth/API Key}
- **Implementation:** {key file paths}

## Flow
{Login → token/session → middleware validates → ...}

## Middleware
- **File:** {path}
- **Behavior:** {what it checks, what it rejects}

## Roles / Permissions
- {role definitions if any}

## Public Routes
- {routes that don't require auth}

## Token Details
- {expiry, refresh mechanism, storage}
```

### patterns.md

```markdown
{frontmatter}

# Patterns & Conventions

## Code Style
- **Imports:** {absolute via tsconfig paths / relative}
- **Naming:** {camelCase/snake_case, file naming convention}
- **Components:** {where they live, how to create new ones}

## API Route Pattern
- {pattern, e.g., src/app/api/[resource]/route.ts}

## Error Handling
- {project's error handling pattern}

## Testing
- **Framework:** {name}
- **Command:** `{test command}`
- **Pattern:** {where tests live, naming convention}

## Gotchas
- {COMPLETE list of all gotchas — 1 line each}
- {Thing that looks right but breaks}
- {Non-obvious behavior}
- {Common mistake in this codebase}
```

## Thin Pointer Templates

Five pointer files redirect other AI tools to read the same documentation. All use pure redirect — no project-specific content duplicated.

### Write Rules for Pointers

- **Only create if the file does not already exist** with custom content
- If the file exists and matches the pointer template (detect by presence of "Read `CLAUDE.md`" in content), it was generated by project-doc — update it
- If the file exists with different content, **do not touch it**. Report: "Skipped {file} — has custom content"
- Create `.github/` directory if needed for copilot-instructions.md

### AGENTS.md (Codex / OpenAI)

```markdown
# Project Documentation

This project uses a structured documentation system optimized for AI coding agents.

1. Read `CLAUDE.md` for the project index — it contains the stack, critical gotchas, and a documentation routing table
2. Based on your current task, read the relevant docs from `.claude/docs/` as indicated in the Documentation Index
3. Each doc entry includes "→ read when" hints to help you pick the right docs for the current task
```

### GEMINI.md (Gemini CLI)

```markdown
# Project Documentation

This project uses a structured documentation system optimized for AI coding agents.

1. Read `CLAUDE.md` for the project index — it contains the stack, critical gotchas, and a documentation routing table
2. Based on your current task, read the relevant docs from `.claude/docs/` as indicated in the Documentation Index
3. Each doc entry includes "→ read when" hints to help you pick the right docs for the current task
```

### .github/copilot-instructions.md (GitHub Copilot)

```markdown
Read `CLAUDE.md` at the project root for the project index and documentation routing table.
Detailed docs by concern are in `.claude/docs/` — load only what's relevant to the current task.
```

### .cursorrules (Cursor)

```markdown
Read `CLAUDE.md` at the project root for the project index and documentation routing table.
Detailed docs by concern are in `.claude/docs/` — load only what's relevant to the current task.
```

### .windsurfrules (Windsurf)

```markdown
Read `CLAUDE.md` at the project root for the project index and documentation routing table.
Detailed docs by concern are in `.claude/docs/` — load only what's relevant to the current task.
```

## Monorepo Doc Layout

For monorepos, `.claude/docs/` uses subdirectories per app alongside shared docs at root level.

### Structure

```
.claude/docs/
├── architecture.md         ← shared (project-wide structure, common stack)
├── deploy.md               ← shared (single deploy script serves all)
├── infrastructure.md       ← shared (docker-compose, networking, proxy)
├── env-vars.md             ← shared, with per-app subsections
├── patterns.md             ← shared (conventions + all gotchas)
├── {app-name}/
│   ├── api.md              ← app-specific routes
│   ├── database.md         ← app-specific schema/migrations
│   └── auth.md             ← if app has its own auth
├── {app-name}/
│   └── api.md
```

### Rules

- Shared docs (deploy, infrastructure, architecture) are always at root level
- Per-app docs are only created if the app has content distinct from the common pattern
- env-vars.md is always shared but contains per-app subsections
- patterns.md is always shared (gotchas are project-wide)
- If an app follows the common pattern exactly, it gets no subdirectory — mentioned only in the CLAUDE.md index Apps section
- Per-app doc frontmatter includes the app name: `scope: apps/{name}/main.py, apps/{name}/requirements.txt`

## Update Mechanism

### CLAUDE.md

1. **No CLAUDE.md exists:** Create `.claude/CLAUDE.md` with v2 index
2. **CLAUDE.md exists with v1 markers** (`project-doc:start/end`): Run migration first (see Migration section), then write v2 index
3. **CLAUDE.md exists with v2 markers** (`project-doc:v2` / `project-doc:v2:end`): Replace content between v2 markers. Preserve:
   - All content before `<!-- project-doc:v2 -->`
   - All content after `<!-- project-doc:v2:end -->`
   - The `## Custom Rules` section content (extracted before write, reinserted)
4. **CLAUDE.md exists with no markers:** Append the v2 block at the end

**Marker de geração (`gen`):** o marker de abertura grava a versão do **motor** que gerou a doc — `<!-- project-doc:v2 gen=3.3 -->`. A **versão atual do motor é `3.3`** (a release da **leitura-via-grafo**: grafo obrigatório + leitura profunda do código; a `3.1` introduziu o Workflow). A **checagem ativa (passo 0.1)** lê esse atributo: doc com `gen` **ausente ou menor** que `3.3` é **fora do padrão** → reconstrói via Workflow `deep` + garimpo (não um update delta leve) — porque a doc anterior nunca leu o código de verdade. Ao evoluir o motor de forma que a doc antiga deva ser reconstruída, **bump esse número** aqui e nos dois Index Templates.

**CRITICAL:** When replacing, include the markers themselves in the new content. The markers are part of the block.

### .claude/docs/*.md

- Create `.claude/docs/` directory if it doesn't exist
- Write each doc file. If file exists, overwrite entirely — docs are fully generated, not hand-edited
- Remove doc files that are no longer relevant (detection found no content for that concern)

### Pointer Files

- Only create if file does not exist or was previously generated by project-doc
- If file exists with custom content, do not touch it
- Detection: file was generated by project-doc if it contains "Read `CLAUDE.md`" in the first 5 lines

## Knowledge Graph Integration (graphify)

**Postura (v3.2 — mudou):** o grafo é **documentação, obrigatório no FULL/`--deep`** — não se oferece, se garante. Nos **modos leves** (incremental/index/pointers/`--rebuild`/migrate/verify/clean) a postura antiga vale: **só sugere, não roda**. A fronteira é a mesma do Workflow.

When the project has (or will have) a graphify knowledge graph (`graphify-out/graph.json`), `/project-doc` integrates with it in four ways:

1. **Garantir + mapear (FULL/`--deep`, automático)** — o **passo 0.0 do Workflow** roda `graphify update . --force` (AST, sem LLM, ~segundos) quando ausente/stale e destila o mapa via `graph_map.py`. **Roda sempre, informa, não pergunta** (ver **Workflow Engine → Passo 0.0**). O mapa dirige a leitura profunda (Fase A) e a auditoria de completude (gate 7). Escapes: `--solo` ou `project_doc.skip_graph: true` em `.claude/settings.json`. `graphify` ausente → degrada gracioso (fan-out sem mapa).

2. **Index section** — generate the `## Knowledge Graph (graphify)` section inside the v2 markers (see Index Templates). Generated ONLY when `graphify-out/graph.json` exists. Omit entirely otherwise. This makes "consult the graph before touching code" a durable instruction loaded every session.

3. **Anti-duplication** — if a `## Knowledge Graph` (or `## Knowledge Graph (graphify)`) section already exists OUTSIDE the v2 markers (a manual addition by a previous session), remove that manual copy and let the canonical one be generated inside the markers. Never leave two. Detect by header match; the manual one is the copy not enclosed by `<!-- project-doc:v2 -->` / `<!-- project-doc:v2:end -->`.

4. **Proactive suggestion (só nos modos leves, ou pra o labeling caro)** — após escrever os arquivos (step 14 report), avalie o estado do grafo:
   - **Modo leve com grafo stale** → "O knowledge graph está desatualizado (gerado {date}, sources mudaram {date}). Quer que eu rode `/graphify <path> --update`?"
   - **Modo leve sem grafo** → **ALWAYS suggest, unconditionally** (no triviality/coupling judgment — see Complexity Assessment) → "Esse projeto se beneficiaria de um knowledge graph (mapeia relações, ajuda a localizar/debugar). Quer gerar um com `/graphify`?" — name any complexity signal you saw, but NEVER withhold the offer for lack of one.
   - **Comunidades sem nome bonito** (criação inicial AST → "Community NNN") → no FULL/`--deep` o mapa já funciona (agrupa + fan-in) sem nomes; sugira o **labeling LLM opcional** via `/graphify` completo como upgrade — fora do caminho crítico.
   - **Grafo fresco** → sem prompt, só nota "Knowledge graph: presente e atualizado" no report.

**A distinção que importa:** `graphify update --force` (AST, barato, não-interativo) é o que o FULL/`--deep` **roda sozinho** — não custa tokens de LLM. O `/graphify` **completo** (extract LLM, labeling de comunidades) pode spawnar subagentes e custar tokens → esse continua sendo **sugestão/opt-in do usuário** (mesma postura do deploy). Rodar o AST automático ≠ rodar o LLM automático.

## Migration v1 → v2

Triggered when v1 markers are detected or user runs `/project-doc migrate`.

### Steps

1. Read entire existing CLAUDE.md
2. Identify content outside markers (before `<!-- project-doc:start -->` and after `<!-- project-doc:end -->`) — this is preserved as-is
3. Parse the v1 block section by section using `## ` headers
4. Map each v1 section to its target doc:
   - `## Visão Geral` + `## Stack` + `## Estrutura de Diretórios` + `## Dependências Críticas` + `## Decisões de Arquitetura` + `## Documentação` → `architecture.md`
   - `## Banco de Dados` → `database.md`
   - `## API / Endpoints` → `api.md`
   - `## Deploy` + `## Acesso Remoto` → `deploy.md`
   - `## Serviços / Containers` + `## Portas` + `## Infraestrutura` → `infrastructure.md`
   - `## Variáveis de Ambiente` → `env-vars.md`
   - `## Autenticação` → `auth.md`
   - `## Padrões do Projeto` + `## Gotchas` → `patterns.md`
   - `## Comandos Úteis` → stays inline in index (top 5)
   - `## Gotchas` → top 3-5 stay inline, full list goes to patterns.md
5. Write each doc file to `.claude/docs/` with frontmatter
6. Rewrite CLAUDE.md with v2 index format
7. Preserve content that was outside v1 markers
8. Generate thin pointer files
9. **Do NOT re-scan the project during migration** — use the existing v1 content as-is. Migration is a structural reorganization, not a content refresh. User can run `/project-doc` (full) afterward for fresh content.
10. Report migration results with before/after token comparison

### Monorepo v1 → v2 Migration

For monorepo v1 blocks, additionally:
- Parse per-app sections (### {app-name}) from the `## Apps` section
- Create per-app subdirectories in `.claude/docs/{app-name}/`
- Map each app's content to the appropriate doc (deps → note in architecture, gotcha → patterns, etc.)
- Shared sections (Infra Compartilhada, Stack Comum, Deploy) go to shared root docs

## Artifact Cleanup

Directory hygiene for stale test/scratch artifacts. **Detection runs on every full `/project-doc`** and is reported with the other results — but it NEVER deletes or moves anything on its own. Removal/archival only happens in `/project-doc clean`, and only after the user approves a clustered list. Same philosophy as Auto-Fix and the graphify suggestion: surface, then act on confirmation.

### Detection

Scan the project root recursively, honoring the hard exclusions below. Group findings into categories:

- **Loose screenshots/prints** — image files (`*.png *.jpg *.jpeg *.webp *.gif`) **not inside asset folders**, typically dumped in the repo root or in `.playwright-mcp/`. Name patterns that confirm test origin: `e2e-*`, `screenshot*`, `print*`, `test-*`, `*-debug*`, `Screen Shot*`, timestamped names.
- **Test runner / tool output** — `.playwright-mcp/` (its `*.yml` snapshots + `console-*.log`), `test-results/`, `playwright-report/`, `coverage/`, `.nyc_output/`, `.pytest_cache/`.
- **Temp / scratch / OS cruft** — `*.tmp *.temp *.bak`, loose `*.log`, `tmp-* scratch-* debug-*`, `.DS_Store` (recursive), `*.dump`, core dumps.
- **Prototypes** (→ archive, don't delete) — loose `*.html` outside the build output, `proto*/ mockup*/` folders.

**Hard exclusions — NEVER scan or touch:** `.git/ node_modules/ .venv/ dist/ build/ vendor/`, `graphify-out/` (useful), `.claude/docs/` (the docs themselves), and any asset folder (`public/ assets/ static/ src/ docs/`) or referenced asset.

### Classification (suggested action per finding)

Every finding gets one of four proposed actions:

- 🗑️ **Delete** — unambiguous junk: `.DS_Store`, old `console-*.log`, `test-results/`, `coverage/`.
- 📦 **Archive** — has potential value: prototype HTML, prints that document a state. Moved to `_archive/`, never trashed.
- 🚩 **Review (sensitive)** — listed individually, never acted on automatically (see Sensitivity).
- ✋ **Keep** — recent/likely in use, or referenced somewhere.

### Sensitivity assessment

A finding goes to 🚩 (and is listed individually, never bulk-actioned) if ANY of:

- **Git-tracked** — `git ls-files` includes it (deleting mutates the repo). *Conditional: only when the project is a git repo; if not, fall back to name/location/reference/mtime signals.*
- **Referenced** — its basename appears via grep in code, `README*`, or `.claude/docs/` → it's an asset, not junk.
- **Recent** — `mtime` < 24h → may be in use in the current session.
- **Unclassifiable** — fits no clear pattern, or is a single large unique file.

### Archive destination

Reuse an existing archive dir if present (detect `_archive/ archive/ .archive/`), else create `_archive/`. Two modes:

- **Reopenable items** (prototypes) → move the **raw file** into `_archive/<category>/`.
- **Safety net before a bulk delete** → first pack the originals into `_archive/<project>-housekeeping-<YYYY-MM-DD>.tar.gz` (the convention already in use), THEN remove them. Guarantees reversibility ("look before you delete").
- Check whether `_archive/` is gitignored; if not, mention it to the user.

### Clustered report format

Group by action, list sensitive items individually, end with an approval prompt:

```
## Artefatos detectados — 152 itens

🗑️  Deletar (descarte seguro) — 95
  • .DS_Store ×129 (lixo macOS, recursivo)
  • .playwright-mcp/console-*.log ×22 (logs de console antigos)

📦  Arquivar → _archive/ — 45
  • Prints E2E soltos na raiz ×45 (e2e-*.jpeg, bulk-*.jpeg, c3-*.jpeg…)
    → tarball _archive/viu-housekeeping-2026-06-13.tar.gz

🚩  Revisar (sensível) — 2
  • logo.png — referenciado em README.md (asset, provável manter)
  • screenshot-novo.png — criado há 2h (pode estar em uso)

Aprovar? [tudo | só deletar | só arquivar | escolher itens | cancelar]
```

### Confirmation protocol

- **Never remove or move without explicit approval.** Show the clustered list first.
- User approves per cluster or per item; sensitive (🚩) items require individual confirmation.
- After acting, report a summary: how many deleted, how many archived (and where), how many skipped.

### Scope & safety

- Operate only inside the project root — never touch `~/Desktop/claude-visual/` or anything outside it.
- Respect the hard exclusions above.
- Default to reversible: pack into the dated tarball before any bulk delete.

## Token Limits

### CLAUDE.md Index
- **Target:** 60-100 lines
- **Hard max:** 150 lines
- If index exceeds 100 lines: compress Quick Commands (top 3 instead of 5), reduce inline gotchas (top 3 instead of 5)
- If still over: something is wrong — check for content that should be in docs instead of inline

### Individual Doc Files
- No hard max — they're loaded on-demand
- Should be focused: each doc covers one concern
- If a single doc exceeds 200 lines: consider splitting, but don't force it

### Inline Threshold
- Section ≤5 lines → stays inline in CLAUDE.md index, no separate doc
- Section >5 lines → gets its own `.claude/docs/*.md` file

### Monorepo Index
- **Target:** 80-120 lines
- **Hard max:** 150 lines
- Per-app entry in index: 1 line (name, port, description, doc link)
- If total exceeds 150: compress app entries to name + port only

### Formatting Rules
- **No prose** — bullets, code blocks only
- **NEVER use markdown tables** — render poorly in terminal
- **Omit empty sections entirely** — do not include headers with no content

## Rules

- **NEVER include secret values** — só nomes de variável. Escreva `DB_PASSWORD`, nunca `DB_PASSWORD=hunter2`. **Defense-in-depth:** o **scrubber** do lib já é a 1ª barreira (move valores-secreto pro cofre na escrita do journal — ver Collect & Project / check #10); a projeção é a 2ª barreira — não reintroduza um valor que o scrubber pegaria.
- **Cofre operacional** — valores-secreto NÃO são perdidos, são **desviados** pro cofre (iCloud `Cofre/<projeto>.env`; o repo tem o symlink **gitignored** `.claude/secrets/ops.env`). Na doc, **referencie** em vez do valor: `SSH_HOST → ver cofre (.claude/secrets/ops.env)`.
- **Nomes e contexto SIM, valores NÃO** — hosts, IPs, portas e paths são contexto de infra: **preserve**. Só o valor-secreto vai pro cofre.
- **NEVER include API keys, tokens, or passwords** — even if found in config files
- **SSH key paths are OK** — key file contents are NEVER OK
- **Seções condicionais** — if detection found nothing for a section, omit it entirely. Don't generate empty doc files.
- **[TODO: ...]** — when information can't be auto-detected (e.g., SSH host that's not in any file), mark it with `[TODO: describe what's needed]` and list all TODOs to the user after generation
- **Read deploy scripts fully** — don't just note "deploy.sh exists". Read it and document what it does step by step
- **Read docker-compose fully** — extract all services, ports, volumes, network modes, environment variables
- **Be specific** — file paths, port numbers, exact commands. No vague descriptions
- **One line per item** — gotchas, decisions, deps are all one-liners
- **NEVER duplicate content between CLAUDE.md index and .claude/docs/** — the index has identity + routing, docs have details. If information appears in both places, it should be a summary in the index and full detail in the doc.
- **Gotchas inline = top 3-5 most dangerous ONLY** — the ones that cause real bugs or data loss. The complete list goes in patterns.md.
- **"Read when" hints must be actionable** — not "→ general information" but "→ writing migrations, changing schema, querying data"
- **Doc frontmatter is mandatory** — every `.claude/docs/*.md` must have the YAML frontmatter block
- **Pointer files are pure redirects** — NEVER put project-specific content in them
- **NEVER delete or move an artifact without confirmation** — always show the clustered list first (same discipline as Auto-Fix)
- **Sensitive items are listed individually** — git-tracked, referenced in code/docs, or `mtime` < 24h NEVER enter an automatic action
- **Archive > delete for items of value** — prototypes and state-documenting prints go to `_archive/`, not the trash
- **Safety net before any bulk delete** — pack originals into `_archive/*-housekeeping-<date>.tar.gz` first, then remove
- **Cleanup scope = project root** — never touch outside it (e.g. `~/Desktop/claude-visual/`); never touch `.git/ node_modules/ graphify-out/ .claude/docs/` nor referenced assets

## Verification (Post-Generation Quality Check)

After writing all files, run this verification checklist. Report results to the user with pass/fail per check.

### Index-Level Checks

**1. Structural Integrity**
- v2 markers present: both `<!-- project-doc:v2 -->` and `<!-- project-doc:v2:end -->` exist
- Content between markers is not empty
- No duplicate markers (only one v2 start/end pair)
- Manual content outside markers (if any) is preserved intact
- No v1 markers remaining (if migration was performed)

**2. Link Validity**
- For every doc referenced in the Documentation Index, verify the file exists in `.claude/docs/`
- Report any broken link as **FAIL — doc referenced but not found**

**3. No Orphan Docs**
- List all files in `.claude/docs/` (and subdirectories for monorepo)
- Compare against docs referenced in the CLAUDE.md index
- Report any doc file not in the index as **WARN — orphan doc**

**4. Coverage Gaps**
- Scan source files for content that should be documented but isn't covered by any doc
- Example: docker-compose.yml exists but no infrastructure.md → **WARN — undocumented area**

**5. Token Budget**
- Count total lines in CLAUDE.md between v2 markers
- PASS if ≤100, WARN if 101-150, FAIL if >150

### Per-Doc Checks

**6. File Path Accuracy**
- For every file path mentioned in any doc (e.g., `dashboard/src/middleware.ts`, `scripts/deploy.sh`), verify the file actually exists using Glob
- Report any referenced paths that don't exist as **FAIL — phantom path**

**7. Port Consistency**
- Cross-reference ports listed in infrastructure.md against docker-compose.yml (ports, EXPOSE), proxy configs (listen, proxy_pass)
- Report any port in the doc not found in source files, or any port in source files missing from the doc

**8. Env Var Coverage**
- Compare env vars listed in env-vars.md against all vars in .env.example
- Report any var in .env.example missing from the doc
- Report any var in the doc not in .env.example (may be valid if from docker-compose environment)

**9. Service Completeness**
- Compare services listed in infrastructure.md against all services in docker-compose.yml
- Report any service missing from the doc

**10. Security — Scrubber + No Leaked Secrets**
- O **scrubber** (lib) é a 1ª barreira na escrita do journal; este check é a 2ª, na doc final (defense-in-depth — repo privado NÃO é controle de secret).
- Scan ALL generated files for secret-looking values: strings após `=` que não são placeholder/template, base64 longo, JWT (`eyJ…`), `AKIA…`, blocos PEM, connection strings com senha embutida.
- Garanta que valores de .env NUNCA entram — só nomes. Onde havia um secret, a doc deve **referenciar o cofre** (`.claude/secrets/ops.env`), não o valor.
- Confirme que `.claude/secrets/` está no `.gitignore` (o lib adiciona; verifique).
- Qualquer vazamento potencial = **CRITICAL FAIL** — corrija antes de declarar pronto.

**11. Deploy Flow Accuracy**
- If deploy.md exists, verify the documented steps match the actual deploy script content
- Check that flags documented (--dry-run, --sync-only, etc.) actually exist in the script

**12. Section Relevance**
- For each doc present, verify it has actual content (not just frontmatter + empty template)
- For each doc absent, verify no detection source exists (e.g., if database.md is missing, confirm no DB images in docker-compose, no DB_* vars in .env)
- Report false negatives (doc should exist but doesn't) and false positives (doc exists but shouldn't)

**13. Staleness Detection**
- For each doc, read the `generated` date from frontmatter
- Compare against `git log --format=%aI -1 -- {source files}` for each doc's scope
- Report per-doc staleness: **WARN — {doc}.md may be stale (generated {date}, sources changed {date})**

### Monorepo-Specific Checks

**14. App Completeness**
- List all app directories in `apps/` or `packages/` that have a Dockerfile or package.json
- Compare against apps documented in the CLAUDE.md index Apps section
- Report any app present in filesystem but missing from the index
- Report any app in the index that no longer exists in filesystem

**15. App Content Accuracy (REQUIRED)**
- For each app with docs in `.claude/docs/{app-name}/`, read the app's source files
- Cross-reference deps listed in docs against actual requirements.txt/package.json
- Flag any dep in the file but missing from the doc as **FAIL — undocumented dep**
- Flag any dep documented but no longer in the source as **FAIL — phantom dep**
- This check cannot be skipped or approximated. Read the files.

### Git-Tracking Checks

**16. Versioned Artifacts Are Tracked (CRITICAL — o conhecimento precisa viajar)**
- Os artefatos cujo PROPÓSITO é viajar no git **não podem estar gitignored nem untracked**. Caso real: no `tools` o **journal caiu no `.gitignore`** — a doc gerava, mas o conhecimento não viajava entre máquinas/clones (quebra o RF Portabilidade **em silêncio**).
- Para cada path abaixo, rode `git -C "<root>" check-ignore -q <path>` (ignorado se exit 0) **e** `git -C "<root>" ls-files --error-unmatch <path>` (tracked se exit 0):
  - `.claude/CLAUDE.md` e todo `.claude/docs/*.md`
  - **`.claude/.project-doc/findings.jsonl`** e **`.claude/.project-doc/ledger.json`** — o journal + ledger, o ÚNICO veículo do conhecimento entre máquinas
  - os thin pointers gerados (`AGENTS.md`, `GEMINI.md`, `.cursorrules`)
- **Ignorado** (`check-ignore` exit 0) → **CRITICAL FAIL — "{path} está no .gitignore; o conhecimento não vai viajar"**. Mostre a regra que casa (`git check-ignore -v <path>`) pro Pedro removê-la.
- **Não-ignorado mas untracked** (nunca commitado) → **WARN — "{path} existe mas não está no git ainda (git add)"**.
- **Distinção que NÃO pode confundir:** `.claude/.project-doc/backups/` e `.claude/secrets/` **DEVEM** estar gitignored (efêmero / cofre). O check é sobre os arquivos versionados-por-design (journal, ledger, docs), **não** a pasta `.project-doc/` inteira.

### Graph Coverage Check (v3.2)

**17. Auditoria grafo × doc (só se há grafo — `graphMap.available`)**
- O grafo é o **completeness-critic** do fim: cruza o que o grafo diz ser importante contra o que a doc cobriu (espelha o gate 7 do Stitch; aqui é o check final da Verification).
- Rode `graph_map.py` (ou reuse a saída do passo 0.0) e, para cada item, procure cobertura no texto gerado (qualquer `.claude/docs/*.md` + índice), por `label` ou `source_file`:
  - **god node** (fan-in alto) sem nenhuma menção → **WARN — função central não documentada: `{label}` ({source_file})**
  - **comunidade nomeada** (não-generic) sem seção que a cubra → **WARN — módulo não documentado: `{label}`**
  - **hyperedge ≥0.85** sem menção → **WARN — workflow não documentado: `{label}`** (candidato a nota de arquitetura)
- WARN não bloqueia (o grafo pode ter ruído/defasagem) — alimenta o relatório e, opcionalmente, uma 2ª leva de agente pro gap. Sem grafo → check **N/A** (não falha).

### Verification Output Format

```
## /project-doc Verification Results

✅ Structural integrity — v2 markers present, content valid
✅ Link validity — 5/5 docs exist
✅ No orphan docs — 0 orphans
✅ Coverage — all detected areas documented
✅ Token budget — 82 lines (target: 60-100)
✅ File paths — 23/23 paths exist across all docs
❌ Port consistency — port 8080 in docker-compose not in infrastructure.md
✅ Env var coverage — 11/11 vars documented
✅ Service completeness — 3/3 services documented
✅ Security — no leaked secrets
✅ Versioned artifacts tracked — journal + ledger + 5 docs no git (backups/ e secrets/ ignorados, como esperado)
⚠️  Graph coverage — 18/20 god nodes documentados; "Bootstrap Sync Cycle" (hyperedge) sem nota de arquitetura
✅ Deploy flow — 3/3 flags documented, steps match script
✅ Section relevance — 5 docs, 0 false negatives
⚠️  Staleness — database.md generated 2026-05-01, schema.prisma changed 2026-05-25

Summary: 12 passed, 1 warning, 1 failed
Token impact: 305 lines (v1) → 82 lines index + 5 docs on-demand (73% context reduction)
```

### Auto-Fix

After verification, if simple auto-correctable issues are found:
- Port in docker-compose but missing from infrastructure.md
- Env var in .env.example but missing from env-vars.md
- Service in docker-compose but missing from infrastructure.md
- Orphan doc not referenced in index → add entry
- Doc referenced in index but file missing → remove entry from index
- File path referenced that moved (old path doesn't exist, similar file found nearby)

**Action:** report to user with: "Encontrei N issues corrigíveis automaticamente. Quer que eu corrija?" If user confirms, apply fixes and re-run verification.

Do NOT auto-fix without asking. Do NOT fix complex issues (wrong descriptions, outdated deploy flow, architectural changes) — those require re-running `/project-doc` or `/project-doc {doc-name}`.

### When to Run Verification

- **Automatically** after every `/project-doc` generation, update, or migration
- **On demand** when user says "verifica o claude.md", "check project-doc", "valida a doc", or runs `/project-doc verify`
- Verification can run standalone (without regenerating) — just read existing files and run checks against source files
