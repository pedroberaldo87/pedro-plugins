---
name: project-doc
description: Use when entering a project without CLAUDE.md, after major structural changes, or when the user says "project-doc", "documenta", "documentar", "documenta o projeto", "gera o claude.md", "atualiza o claude.md"
---

# Project Doc — Auto-Generate Project CLAUDE.md

## Overview

Scans a project's files and generates a structured reference block in the project's CLAUDE.md with everything Claude needs to work effectively: stack, ports, env vars, deploy flow, SSH, database, gotchas. Sections are conditional — only included if relevant content is detected.

## When to Suggest Proactively

- Project has no `.claude/CLAUDE.md` → "Esse projeto não tem CLAUDE.md. Quer que eu rode o /project-doc pra gerar?"
- CLAUDE.md exists but major structural changes detected (new services, new deploy scripts, new database) → "O CLAUDE.md pode estar desatualizado. Quer que eu rode o /project-doc pra atualizar?"

## Output Protocol

Report each step to the user as you execute. Format:

```
**Step 1/10:** Root → `/path/to/project`
**Step 2/10:** Layout → Standard | Monorepo (N apps)
**Step 3/10:** Type → app | lib | cli
**Step 4/10:** Package manager → pnpm | yarn | bun | npm
**Step 5/10:** CLAUDE.md → CREATE | APPEND | REPLACE (markers found)
**Step 6/10:** Scanning... (list key files read)
**Step 7/10:** Generating... (N sections)
**Step 8/10:** Aux docs → {N docs created in docs/} | none needed
**Step 9/10:** Written → `.claude/CLAUDE.md` (N lines)
**Step 10/10:** Report — diff summary (if REPLACE), sections, TODOs, verification
```

This gives the user visibility into what's happening. Don't skip steps or batch them silently.

## Process

1. **Identify project root** — find nearest git repo root or use cwd
2. **Detect project layout** — check for monorepo indicators:
   - `apps/` or `packages/` directory with 2+ subdirs containing Dockerfile, package.json, or main entry files
   - Root docker-compose.yml with services mapping to subdirs (e.g., `dockerfile: apps/X/Dockerfile`)
   - Workspace config (pnpm-workspace.yaml, package.json workspaces, lerna.json)
   - If monorepo detected: use **Monorepo Output Format**. If not: use **Standard Output Format**.
3. **Detect project type** — classify as app, lib, or cli using the Detection Matrix rules. This determines which sections to include/omit.
4. **Detect package manager** — check lockfiles (pnpm-lock.yaml → yarn.lock → bun.lockb → package-lock.json). First match wins.
5. **Check for existing CLAUDE.md** at `{project_root}/.claude/CLAUDE.md` (standard) or `{project_root}/CLAUDE.md` (if already exists there)
   - If exists: read it, check for `<!-- project-doc:start -->` / `<!-- project-doc:end -->` markers
   - If markers found: will REPLACE content between markers (preserve everything outside). **Save old block for diff.**
   - If no markers: will APPEND the block at the end
   - If no CLAUDE.md: will CREATE `.claude/CLAUDE.md` with just the block
6. **Scan project files** using the Detection Matrix below. For monorepos, also scan each app directory.
   - **REPLACE mode — monorepo CRITICAL RULE:** NEVER carry forward app entries from the existing block. Every app entry must be regenerated from disk. For each app directory found in `apps/`:
     - Read `apps/{name}/requirements.txt` or `package.json` (full content)
     - Read `apps/{name}/main.py` or main entry file (full content, or at minimum the imports + route definitions)
     - Read `apps/{name}/.env.example` if it exists
     - Compare what you find against the existing CLAUDE.md entry
     - Flag any discrepancy (new dep, removed dep, new feature, changed description) as a `~` diff item
   - Skipping any app file read in REPLACE mode is a process violation. There are no shortcuts.
7. **Generate the block** using the appropriate Output Format template. Only include sections where detection found content. Mark gaps with `[TODO: ...]`. Use today's date in the timestamp comment.
8. **Check for auxiliary docs need** — if any section exceeds 30 lines or total block exceeds 350 lines:
   - Extract detailed content into `docs/{topic}.md` (e.g., docs/deploy-flow.md, docs/monorepo-apps.md, docs/api-routes.md)
   - Replace the detailed content in CLAUDE.md with a 2-3 line summary + reference: "Detalhes em **docs/{topic}.md**"
   - Create the docs/ directory if needed
9. **Write the block** to CLAUDE.md using the Update Mechanism.
10. **Report to user:**
    - **If REPLACE mode:** show diff summary — sections added (+), removed (-), and modified (~). Format: "Atualizado: +Seção API, ~Stack (pnpm detectado), -Seção Infra (arquivos removidos)". If no changes: "Sem mudanças detectadas."
    - Show which sections were populated
    - For monorepos: list which apps were documented
    - List any `[TODO: ...]` gaps found
    - List any auxiliary docs created
    - Ask: "Quer preencher os TODOs agora?"

## Detection Matrix

For each section, scan these files (read only those that exist):

**Project Type Detection (run first):**
- **app** — has server entry (main.py, index.ts, server.js), Dockerfile, docker-compose.yml, port bindings, deploy scripts
- **lib** — has exports field in package.json, publishConfig, peer dependencies, or main/module/types fields pointing to dist/
- **cli** — has bin field in package.json, or depends on commander/yargs/meow/oclif/click/argparse with entry script
- Default to **app** if unclear. Libs and CLIs omit: Serviços/Containers, Portas, Deploy, Infraestrutura, Acesso Remoto

**Package Manager Detection (run first):**
- pnpm-lock.yaml → pnpm
- yarn.lock → yarn
- bun.lockb → bun
- package-lock.json → npm
- (check in this order — first match wins)

**Test Framework Detection:**
- jest.config.{js,ts,cjs,mjs}, jest field in package.json → Jest
- vitest.config.{js,ts,mjs}, vite.config with test → Vitest
- pytest.ini, conftest.py, pyproject.toml [tool.pytest] → pytest
- .rspec, spec/ dir → RSpec
- go test files (*_test.go) → go test
- Cargo.toml with [dev-dependencies] + #[test] in src → cargo test

**Per-Section Detection:**

- **Visão geral** — README.md, package.json (description), pyproject.toml, go.mod, pom.xml, build.gradle, Gemfile, composer.json, .csproj/.sln, mix.exs
- **Stack** — package.json, requirements.txt, pyproject.toml, go.mod, Cargo.toml, docker-compose.yml, Dockerfile*, .tool-versions, .node-version, .python-version, pom.xml, build.gradle, Gemfile, composer.json, .csproj/.sln, mix.exs
- **Estrutura de diretórios** — ls top-level + ls of src/, app/, lib/, pages/, components/ if they exist
- **Serviços/Containers** — docker-compose.yml, docker-compose.*.yml (skip for lib/cli)
- **Portas e URLs** — docker-compose.yml (ports), .env/.env.example (PORT/URL vars), nginx/*.conf, Dockerfile (EXPOSE), server config files (skip for lib/cli)
- **Banco de dados** — docker-compose.yml (postgres/mysql/mongo/redis images), .env (DB_*/DATABASE_* vars), prisma/schema.prisma, drizzle.config.*, knexfile.*, sqlalchemy configs, migrations/ dir
- **Variáveis de ambiente** — .env.example, .env.local.example, .env (names only, NEVER values), docker-compose.yml (environment section), .env.development, .env.staging, .env.production, .env.local, .env.test
- **API / Endpoints** — app/api/ dir, routes/ dir, controllers/ dir, openapi.yaml, openapi.json, swagger.json, swagger.yaml, graphql schema files. Skip if no route patterns found
- **Autenticação** — middleware.ts, middleware.js, src/middleware.*, auth/, src/auth/, lib/auth*, next-auth config, passport config, JWT patterns in code
- **Padrões do projeto** — tsconfig.json (paths), .eslintrc*, .prettierrc*, src/ structure conventions, existing code patterns
- **Dependências críticas** — package.json (non-obvious deps), requirements.txt (specialized libs), go.mod, pom.xml, build.gradle, Gemfile, composer.json
- **Infraestrutura** — nginx/, nginx.conf, nginx/conf.d/*.conf, Caddyfile, traefik configs, certbot/SSL references (skip for lib/cli)
- **Acesso remoto** — scripts/deploy*, .env (SERVER/VPS/SSH vars), Makefile (deploy targets), CI/CD configs (.github/workflows/*.yml, .gitlab-ci.yml) (skip for lib/cli)
- **Deploy** — scripts/deploy*, deploy.sh, Makefile, CI/CD configs — READ the full deploy script to document the complete flow (skip for lib/cli)
- **Testes** — detect framework (see above), add test command to Comandos Úteis with framework name
- **Gotchas** — Known from scanning (e.g., network_mode:host, special env handling, non-standard configs)
- **Decisões de arquitetura** — docs/ARCHITECTURE.md, docs/ADR*, docs/decisions/, README.md architecture sections
- **Documentação disponível** — docs/*.md, README.md, CONTRIBUTING.md, API docs
- **Comandos úteis** — package.json (scripts), Makefile (targets), scripts/*.sh, pyproject.toml (scripts)

### Monorepo-Specific Detection

When monorepo is detected, additionally scan per app. **This scan is mandatory for every app, every run — no exceptions, no shortcuts, no copying from the existing block.**

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

## Output Format

Two templates exist: **Standard** (single project) and **Monorepo** (multiple apps). Use the one matching the detected project type. **Only include sections where content was detected.** Each section should be terse — bullet points, no prose.

### Standard Output Format

```markdown
<!-- project-doc:start -->
<!-- Generated by /project-doc on {YYYY-MM-DD} — run /project-doc to update -->

# Project Reference

## Visão Geral
{1-2 sentence description of what this project is}
**Tipo:** {app | lib | cli} — detected automatically

## Stack
- **Package manager:** {pnpm | yarn | bun | npm} (detected from lockfile)
- {Language}: {version if detected}
- {Framework}: {version}
- {Runtime}: {version}
- {Key tool}: {version}

## Estrutura de Diretórios
```
{tree, max 2 levels deep, only meaningful dirs}
```

## Serviços / Containers
- **{name}** — {image} — ports {host:container} — {network_mode, volumes, depends_on}

## Portas
- **{port}** {TCP/UDP} — {serviço} — {internal/external, proxy target}

## Banco de Dados
- **Tipo:** {PostgreSQL/MySQL/MongoDB/Redis/SQLite}
- **Host/Porta:** {host:port or socket}
- **Env vars:** `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- **ORM/Driver:** {Prisma/Drizzle/Knex/SQLAlchemy/raw driver}
- **Schema:** {path to schema file}
- **Migrations:** {path to migrations dir, how to run}
- **Admin tool:** {pgAdmin/Adminer/RedisInsight if configured}
- **Acesso direto:** `{command to connect, e.g., docker exec -it db psql -U user dbname}`

## Variáveis de Ambiente
- **Arquivo base:** `.env` (from `.env.example`)
- **Ambientes detectados:** {list .env.development, .env.staging, .env.production, .env.local, .env.test — only those that exist}
- `VAR_NAME` — {what it does}
- `VAR_NAME` — {what it does}

## API / Endpoints (conditional — only for API-centric projects)
- **Tipo:** {REST | GraphQL | gRPC | mixed}
- **Padrão de rotas:** {e.g., src/app/api/[resource]/route.ts, routes/*.py, controllers/*.rb}
- **Spec:** {path to openapi.yaml/swagger.json if exists}
- **Base URL:** {/api/v1, /graphql, etc.}

## Autenticação
- **Tipo:** {JWT/Session/OAuth/API Key}
- **Implementação:** {file paths}
- **Fluxo:** {login → token → middleware validates}

## Padrões do Projeto
- **Imports:** {absolute via tsconfig paths / relative}
- **Naming:** {camelCase/snake_case, file naming convention}
- **Componentes:** {where they live, how to create new ones}
- **Rotas API:** {pattern, e.g., src/app/api/[resource]/route.ts}

## Dependências Críticas
- `{package}` — {why it's important, what it does that's non-obvious}

## Infraestrutura
- **Proxy:** {Nginx/Caddy/Traefik} → {what it proxies}
- **SSL:** {Let's Encrypt/self-signed/managed}
- **Config:** {path to proxy config}

## Acesso Remoto
- **Host:** `{user@host}` or `{env var that holds it}`
- **Key:** `{key path}`
- **Project path (server):** `{path on server}`

## Deploy
- **Script:** `{path to deploy script}`
- **Fluxo:** {step-by-step of what the deploy script does: build → prune → push/rsync → restart → healthcheck}
- **Flags:** `{--dry-run, --force, etc.}`
- **CI/CD:** {GitHub Actions/GitLab CI — workflow file path}

## Gotchas
- {Thing that looks right but breaks — 1 line each}

## Decisões de Arquitetura
- {Decision — 1 line each, e.g., "SRS uses network_mode:host because UDP+Docker NAT breaks SRT"}

## Documentação
- **{doc name}** — {path} — {what it covers}

## Comandos Úteis
```bash
# Build
{command}

# Test ({framework}: jest | vitest | pytest | rspec | go test | cargo test)
{command}

# Dev
{command}

# Deploy
{command}

# Lint
{command}
```

<!-- project-doc:end -->
```

### Monorepo Output Format

For monorepos, the structure changes: global sections first, then a compact **Apps** section with per-app entries. Each app gets ~5-10 lines max — only what's unique to that app. Shared patterns go in the global sections.

```markdown
<!-- project-doc:start -->
<!-- Generated by /project-doc on {YYYY-MM-DD} — run /project-doc to update -->

# Project Reference

## Visão Geral
{1-2 sentence description. Mention it's a monorepo with N apps.}
**Tipo:** monorepo — detected automatically

## Stack Comum
- **Package manager:** {pnpm | yarn | bun | npm} (detected from lockfile)
- {Language}: {version}
- {Framework}: {version} (used by most/all apps)
- {Runtime}: {version}
- {Key tool}: {version}

## Estrutura de Diretórios
```
{tree showing apps/, shared/, key root files — max 2 levels}
```

## Serviços / Containers
- **{name}** — port {port} — apps/{name}/Dockerfile — healthcheck: {method}

## Infra Compartilhada
- **Shared libs:** {shared/, shared_lib/ — what they provide}
- **Shared env:** `.env.shared` — {key vars: DB connection, API keys used by all apps}
- **Networking:** {Docker network name, bridge/host}
- **Proxy:** {Nginx/Caddy} → {routing pattern, e.g., /app-name → port}
- **SSL:** {Let's Encrypt/managed}

## Variáveis de Ambiente
- **Shared (`.env.shared`):**
  - `VAR_NAME` — {what it does}
- **Per-app (`apps/X/.env`):**
  - Each app has its own .env with app-specific vars (API keys, ports, feature flags)

## Padrão Comum das Apps
{Describe the repeating pattern so individual app sections only note exceptions}
- **Entry point:** {main.py, index.ts}
- **Structure:** {database.py, templates/, static/}
- **New app:** {steps to create, e.g., "copy apps/_template/, adjust Dockerfile and port, add to docker-compose and deploy.sh"}

## Deploy
- **Script:** `{path}`
- **Seletivo:** `./deploy.sh {app1} {app2}` — rebuilds only specified services
- **Full:** `./deploy.sh` — rebuilds everything
- **Fluxo:** {step-by-step}
- **Valid services:** {list}

## Acesso Remoto
- **Host:** `{user@host}` or `{env var}`
- **Project path (server):** `{path}`

## Apps

### {app-name} (porta {port})
- **O que faz:** {1 sentence}
- **Stack diferente:** {only if differs from common, e.g., "Next.js (not FastAPI)"}
- **Deps críticas:** `{lib}` — {why}
- **Env específico:** `{VAR}` — {what}
- **Gotcha:** {if any}

### {app-name} (porta {port})
- **O que faz:** {1 sentence}
- **Deps críticas:** `{lib}` — {why}

{repeat for each app — omit bullets with nothing unique}

## Gotchas Globais
- {Things that affect the whole monorepo}

## Documentação
- **{doc name}** — {path} — {what it covers}

## Comandos Úteis
```bash
# Dev (any app)
cd apps/{name} && uvicorn main:app --port {port} --reload

# Deploy selective
./deploy.sh {app1} {app2}

# Deploy all
./deploy.sh

# Lint
{command}

# Tests
{command}
```

<!-- project-doc:end -->
```

## Update Mechanism

Three scenarios for writing the block:

1. **No CLAUDE.md exists:** Create `.claude/CLAUDE.md` with just the block
2. **CLAUDE.md exists, no markers:** Append the block at the end of the file
3. **CLAUDE.md exists, markers found:** Replace everything between `<!-- project-doc:start -->` and `<!-- project-doc:end -->` (inclusive). Preserve all content before and after the markers.

**CRITICAL:** When replacing, include the markers themselves in the new content. The markers are part of the block.

## Token Limits

**Standard projects:**
- **Target:** ~200 lines total
- **Hard max:** 400 lines

**Monorepos:**
- **Target:** ~250 lines (global sections ~150 + apps ~100)
- **Hard max:** 400 lines
- **Per app:** max 5-10 lines — only what's unique. If an app follows the common pattern exactly, 2 lines suffice (name, port, what it does).
- If total exceeds 400 lines, compress app entries further (1-2 lines per app) or extract to docs/monorepo-apps.md

**Both:**
- **Per section:** max 30 lines (if exceeds, extract to docs/ — see step 8)
- **No prose** — bullets, code blocks only. **NEVER use markdown tables** (render poorly in Pedro's terminal)
- **Omit empty sections entirely** — do not include section headers with no content

## Rules

- **NEVER include secret values** — only variable names from .env. Write `DB_PASSWORD` not `DB_PASSWORD=hunter2`
- **NEVER include API keys, tokens, or passwords** — even if found in config files
- **SSH key paths are OK** — key file contents are NEVER OK
- **Seções condicionais** — if detection found nothing for a section, omit it entirely
- **[TODO: ...]** — when information can't be auto-detected (e.g., SSH host that's not in any file), mark it with `[TODO: describe what's needed]` and list all TODOs to the user after generation
- **Read deploy scripts fully** — don't just note "deploy.sh exists". Read it and document what it does step by step
- **Read docker-compose fully** — extract all services, ports, volumes, network modes, environment variables
- **Be specific** — file paths, port numbers, exact commands. No vague descriptions
- **One line per item** — gotchas, decisions, deps are all one-liners

## Verification (Post-Generation Quality Check)

After writing the CLAUDE.md block, run this verification checklist. Report results to the user with pass/fail per check.

### Checks to Run

**1. Structural Integrity**
- Markers present: both `<!-- project-doc:start -->` and `<!-- project-doc:end -->` exist
- Content between markers is not empty
- No duplicate markers (only one start/end pair)
- Manual content outside markers (if any) is preserved intact

**2. File Path Accuracy**
- For every file path mentioned in the doc (e.g., `dashboard/src/middleware.ts`, `scripts/deploy.sh`), verify the file actually exists using Glob
- Report any referenced paths that don't exist as **FAIL — phantom path**

**3. Port Consistency**
- Cross-reference ports listed in "Portas" section against docker-compose.yml (ports, EXPOSE), srs.conf (listen), nginx configs (listen, proxy_pass)
- Report any port in the doc not found in source files, or any port in source files missing from the doc

**4. Env Var Coverage**
- Compare env vars listed in "Variáveis de Ambiente" against all vars in .env.example
- Report any var in .env.example missing from the doc
- Report any var in the doc not in .env.example (may be valid if from docker-compose environment)

**5. Service Completeness**
- Compare services listed in "Serviços / Containers" against all services in docker-compose.yml
- Report any service missing from the doc

**6. Security — No Leaked Secrets**
- Scan the generated block for patterns that look like secret values: strings after `=` that aren't placeholder/template values, base64-encoded strings, API keys, tokens
- Check that .env values are NEVER included — only variable names
- Report any potential leak as **CRITICAL FAIL**

**7. Token Budget**
- Count total lines between markers
- PASS if ≤200, WARN if 201-400, FAIL if >400

**8. Section Relevance**
- For each section present, verify it has actual content (not just the header)
- For each section absent, verify no detection source exists (e.g., if "Banco de Dados" is missing, confirm no DB images in docker-compose, no DB_* vars in .env)
- Report false negatives (section should exist but doesn't) and false positives (section exists but shouldn't)

**9. Deploy Flow Accuracy**
- If "Deploy" section exists, verify the documented steps match the actual deploy script content
- Check that flags documented (--dry-run, --sync-only, etc.) actually exist in the script

**10. App Completeness (monorepo only)**
- List all app directories in `apps/` or `packages/` that have a Dockerfile or package.json
- Compare against apps documented in the "Apps" section
- Report any app present in filesystem but missing from the doc
- Report any app in the doc that no longer exists in filesystem

**10b. App Content Accuracy (monorepo only — REQUIRED)**
- For each app in the "Apps" section, read `apps/{name}/requirements.txt` (or `package.json`) and the main entry file
- Cross-reference non-obvious deps listed in requirements.txt against the app's "Deps críticas" bullet
- Flag any dep that is in the file but missing from the doc as **FAIL — undocumented dep**
- Flag any dep documented but no longer in requirements.txt as **FAIL — phantom dep**
- Cross-reference the "O que faz" description against what the main file actually does — flag if description appears stale
- This check cannot be skipped or approximated. "Looks right" is not evidence. Read the files.

**11. Staleness Detection**
- Compare file modification times of key source files (docker-compose.yml, package.json, .env.example, deploy scripts) against the CLAUDE.md modification time
- If any source file is newer than CLAUDE.md, flag as **WARN — potentially stale**

### Verification Output Format

```
## /project-doc Verification Results

✅ Structural integrity — markers present, content valid
✅ File paths — 23/23 paths exist
❌ Port consistency — port 8080 in srs.conf not documented
✅ Env var coverage — 11/11 vars documented
✅ Service completeness — 3/3 services documented
✅ Security — no leaked secrets
✅ Token budget — 188 lines (target: 200)
✅ Section relevance — 16 sections, 0 false negatives
✅ Deploy flow — 3/3 flags documented, steps match script
⚠️  Staleness — docker-compose.yml modified after CLAUDE.md

Summary: 8 passed, 1 warning, 1 failed
```

### Auto-Fix

After verification, if simple auto-correctable issues are found:
- Port in docker-compose/nginx but missing from Portas section
- Env var in .env.example but missing from Variáveis de Ambiente section
- Service in docker-compose but missing from Serviços section
- File path referenced that moved (old path doesn't exist, similar file found nearby)

**Action:** report to user with: "Encontrei N issues corrigíveis automaticamente. Quer que eu corrija?" If user confirms, apply fixes directly to the CLAUDE.md block and re-run verification.

Do NOT auto-fix without asking. Do NOT fix complex issues (wrong descriptions, outdated deploy flow, architectural changes) — those require re-running `/project-doc`.

### When to Run Verification

- **Automatically** after every `/project-doc` generation or update
- **On demand** when user says "verifica o claude.md", "check project-doc", "valida a doc"
- Verification can run standalone (without regenerating) — just read the existing CLAUDE.md and run checks against source files
