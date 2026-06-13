---
name: project-doc
description: "Use when entering a project without CLAUDE.md, after major structural changes, or when the user says \"project-doc\", \"documenta\", \"documentar\", \"documenta o projeto\", \"gera o claude.md\", \"atualiza o claude.md\", \"limpa os artefatos\", \"limpa os prints\", \"limpa o projeto\", \"arquiva protótipos\", or runs \"/project-doc clean\". Generates a modular documentation system (lightweight CLAUDE.md routing table + .claude/docs/*.md per concern + thin pointers for other AI tools) and detects/cleans up stale test artifacts (screenshots, runner output, temp files)."
---

# Project Doc v2 — Documentation System Generator

## Overview

Generates a **documentation system** for a project, not a single file. The system has three layers:

1. **CLAUDE.md** — lightweight routing table (~60-100 lines). Always loaded in context. Contains: project identity, stack one-liner, quick commands, top gotchas, and a documentation index with "→ read when" hints
2. **`.claude/docs/*.md`** — detailed docs per concern (architecture, database, API, deploy, etc.). Loaded on-demand when Claude needs them for the current task
3. **Thin pointer files** — pure redirects (AGENTS.md, GEMINI.md, .cursorrules, etc.) that tell other AI tools to read CLAUDE.md

Sections are conditional — only generated if relevant content is detected. Small sections (≤5 lines) stay inline in CLAUDE.md instead of becoming separate doc files.

## When to Suggest Proactively

- Project has no `.claude/CLAUDE.md` → "Esse projeto não tem CLAUDE.md. Quer que eu rode o /project-doc pra gerar?"
- CLAUDE.md exists but major structural changes detected (new services, new deploy scripts, new database) → "O CLAUDE.md pode estar desatualizado. Quer que eu rode o /project-doc pra atualizar?"
- CLAUDE.md has v1 format (monolithic block with `project-doc:start/end` markers) → "O CLAUDE.md está no formato v1 (monolítico). Quer migrar pro v2 (indexado)? Roda `/project-doc migrate`"
- `.claude/docs/` exists but CLAUDE.md index is missing or doesn't reference it → "Tem docs em .claude/docs/ mas o CLAUDE.md não aponta pra eles. Quer que eu rode o /project-doc index?"
- `graphify-out/graph.json` exists but is stale (source files changed after its mtime) → "O knowledge graph (graphify-out/) pode estar desatualizado. Quer que eu rode `graphify --update`?"
- `graphify-out/graph.json` does NOT exist and the project is non-trivial (see Knowledge Graph Detection → Complexity Assessment — **default to suggesting** unless it's a trivial linear script) → "Esse projeto se beneficiaria de um knowledge graph: mapeia o acoplamento real e ajuda a localizar/debugar numa arquitetura intrincada. Quer gerar um com `/graphify`?"
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

Doc names map directly to `.claude/docs/{arg}.md`. If the argument doesn't match a known doc name, treat it as a full run and warn the user.

## Output Protocol

Report each step to the user as you execute. Don't skip steps or batch them silently.

### Full Mode

```
**Step 1/12:** Root → `/path/to/project`
**Step 2/12:** Layout → Standard | Monorepo (N apps)
**Step 3/12:** Type → app | lib | cli
**Step 4/12:** Package manager → pnpm | yarn | bun | npm
**Step 5/12:** Mode → FULL | MIGRATE (v1→v2 detected) | CREATE (no CLAUDE.md)
**Step 6/12:** CLAUDE.md → v1 markers (will migrate) | v2 index (will update) | none (will create)
**Step 7/12:** Scanning... (list key files read per doc target)
**Step 8/12:** Generating docs → {list of .claude/docs/*.md to create/update, with line counts}
**Step 9/12:** Writing CLAUDE.md index → {N lines}
**Step 10/12:** Pointer files → {list created/updated/skipped}
**Step 11/12:** Verification → {results summary}
**Step 12/12:** Token impact → Before: {N} lines always-loaded | After: {M} lines always-loaded + {K} docs on-demand | Savings: {X}%
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
6. **Scan project files** using the Detection Matrix below.
   - **FULL mode:** scan everything
   - **INCREMENTAL mode:** scan only the source files mapped to the target doc
   - For monorepos, also scan each app directory (see Monorepo-Specific Detection)
   - **Monorepo CRITICAL RULE:** NEVER carry forward app entries from existing docs. Every app must be regenerated from disk. For each app directory found in `apps/`:
     - Read `apps/{name}/requirements.txt` or `package.json` (full content)
     - Read `apps/{name}/main.py` or main entry file (full content, or at minimum the imports + route definitions)
     - Read `apps/{name}/.env.example` if it exists
   - Skipping any app file read is a process violation. There are no shortcuts.
7. **Determine which docs to generate** based on detection results. A doc file is generated only if its detection found substantive content.
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

## Detection Matrix

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
- **Staleness:** compare `graphify-out/graph.json` mtime (or the `date` in `graphify-out/cost.json` last run) against the most recent source-file change (`git log --format=%aI -1`). If sources are newer → graph is stale → suggest `graphify --update`.
- This feeds the "## Knowledge Graph" index section (generated only when the graph exists) and the proactive suggestions above.

**Complexity Assessment (when to suggest CREATING a graph):**

The value of a knowledge graph comes from **architectural complexity / coupling, NOT file count.** A 66-file audio daemon produced 56 communities and was the hardest repo to navigate; a 300-file CRUD app may be trivially flat. So do not gate on size — gate on complexity, and **default to suggesting.**

**Suggest creating a graph UNLESS the project is trivial.** Trivial = ALL of: single module, ≤15 code files, flat (no meaningful subdirectory nesting), one language, no architecture docs. A linear script or a tiny flat lib. Only these skip the suggestion.

For everything else, suggest — and suggest with extra conviction when ANY complexity signal is present (these warrant a graph regardless of how few files there are):
- monorepo (`apps/` or `packages/`)
- code spread across ≥3 directories, or multiple distinct modules
- multiple languages in one repo (e.g. Rust backend + Svelte/TS frontend)
- event-driven / daemon / WebSocket / DI-container / plugin architecture — wiring that isn't obvious from imports
- presence of `docs/ARCHITECTURE*`, ADRs, or a CONTEXT.md — the team already flagged it as complex
- many cross-module references / high fan-in on shared state or service clients

Frame the suggestion by **value, not size**: "arquitetura intrincada é difícil de localizar/debugar — o grafo mapeia o acoplamento contraintuitivo". Generating a graph has minimal downside (some processing time/tokens for doc semantics; AST is free; `graphify-out/` can be gitignored), so when in doubt, suggest.

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

## CLAUDE.md Index Template

The CLAUDE.md index is the always-loaded routing table. Two variants exist: Standard and Monorepo.

### Standard Index Template

```markdown
<!-- project-doc:v2 -->
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
Grafo do projeto em `graphify-out/`. **Antes de analisar arquitetura ou mexer em código compartilhado, consultar o grafo** em vez de grep cego: `graphify query "<pergunta>"` (relações, blast radius), `graphify explain "<símbolo>"`, `graphify path "A" "B"`. É mapa, não verdade — confirmar causa-raiz no código real; edges INFERRED são hipóteses. Snapshot: após um ciclo de mudanças, `graphify --update`.

## Custom Rules

{Preserved from previous generation — human-written content. If no custom rules exist, include this section empty so users know where to add them.}

<!-- project-doc:v2:end -->
```

### Monorepo Index Template

```markdown
<!-- project-doc:v2 -->
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
Grafo do monorepo em `graphify-out/`. **Antes de analisar arquitetura ou mexer em código compartilhado, consultar o grafo** em vez de grep cego: `graphify query "<pergunta>"` (relações, blast radius cross-app), `graphify explain "<símbolo>"`, `graphify path "A" "B"`. É mapa, não verdade — confirmar causa-raiz no código real; edges INFERRED são hipóteses. Snapshot: após um ciclo de mudanças, `graphify --update`.

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

When the project has a graphify knowledge graph (`graphify-out/graph.json`), `/project-doc` integrates with it in three ways:

1. **Index section** — generate the `## Knowledge Graph (graphify)` section inside the v2 markers (see Index Templates). Generated ONLY when `graphify-out/graph.json` exists. Omit entirely otherwise. This makes "consult the graph before touching code" a durable instruction loaded every session.

2. **Anti-duplication** — if a `## Knowledge Graph` (or `## Knowledge Graph (graphify)`) section already exists OUTSIDE the v2 markers (a manual addition by a previous session), remove that manual copy and let the canonical one be generated inside the markers. Never leave two. Detect by header match; the manual one is the copy not enclosed by `<!-- project-doc:v2 -->` / `<!-- project-doc:v2:end -->`.

3. **Proactive suggestion** — after writing all files (step 14 report), evaluate graph state and tell the user:
   - Graph exists but stale (sources changed after graph mtime) → "O knowledge graph está desatualizado (gerado {date}, sources mudaram {date}). Quer que eu rode `graphify --update`?"
   - Graph absent and project is non-trivial (see Complexity Assessment — default to suggesting unless it's a trivial linear script) → "Esse projeto se beneficiaria de um knowledge graph (mapeia o acoplamento, ajuda a debugar arquitetura intrincada). Quer gerar um com `/graphify`?" — cite the complexity signal you saw (módulos, linguagens mistas, arquitetura event-driven, etc.).
   - Graph exists and fresh → no prompt, just note "Knowledge graph: presente e atualizado" in the report.

Do NOT run `graphify` or `graphify --update` automatically — only suggest. Graph generation can spawn many subagents and cost tokens; it is the user's call (same posture as deploy).

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

- **NEVER include secret values** — only variable names from .env. Write `DB_PASSWORD` not `DB_PASSWORD=hunter2`
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

**10. Security — No Leaked Secrets**
- Scan ALL generated files for patterns that look like secret values: strings after `=` that aren't placeholder/template values, base64-encoded strings, API keys, tokens
- Check that .env values are NEVER included — only variable names
- Report any potential leak as **CRITICAL FAIL**

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
✅ Deploy flow — 3/3 flags documented, steps match script
✅ Section relevance — 5 docs, 0 false negatives
⚠️  Staleness — database.md generated 2026-05-01, schema.prisma changed 2026-05-25

Summary: 11 passed, 1 warning, 1 failed
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
