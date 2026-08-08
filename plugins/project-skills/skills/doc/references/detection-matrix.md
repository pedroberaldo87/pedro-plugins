# Tier 1 — Detection Matrix (scan de arquivos)

Referência do scan Tier 1 do project-doc. Carregue este arquivo ao executar o passo 6 (coleta Tier 1), ao particionar o fan-out por concern (casca passo 5) e ao escanear apps de monorepo.


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
- **Nos modos pesados o grafo é GARANTIDO, não só detectado** (regra pesado/leve: **Workflow Engine → Passo 0**). No FULL/`--deep` o Passo 0.0 destila o mapa via `graph_map.py`, que **prioriza os arquivos de cada concern por fan-in** pra leitura profunda.
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

**→ data-stores.md** (gen 3.8 — o inventário de onde o dado mora)

Escaneie **depósitos**, não máquinas. Um servidor de banco hospeda vários bancos; enumerar o
servidor em vez dos bancos foi a causa-raiz do caso que motivou este concern.

- **Bancos** — `docker-compose*.yml` (serviços com imagem postgres/mysql/mongo/mariadb/mssql);
  `CREATE DATABASE` em `migrations/`, `*.sql`, scripts de init e docs; `datasource` do
  `schema.prisma`, `drizzle.config.*`, `alembic.ini`; `DATABASE_URL`/`DB_NAME`/`POSTGRES_DB` em
  `.env*` e na seção `environment:` do compose
- **Volumes** — seção `volumes:` de topo do compose **cruzada com** os `volumes:` de cada serviço
  (quem monta o quê, em que path); `VOLUME` no Dockerfile; bind mounts
- **Buckets** — env vars casando `*_BUCKET`, `S3_*`, `GCS_*`, `R2_*`, `MINIO_*`, `SPACES_*`;
  imports/chamadas de SDK (`boto3`, `@aws-sdk/client-s3`, `minio`, `@google-cloud/storage`,
  `supabase.storage`); IaC (`*.tf`, `serverless.yml`) declarando bucket
- **Filas e caches** — serviços redis/rabbitmq/kafka/nats no compose; clientes no código
  (`ioredis`, `bullmq`, `celery`, `pika`, `kafkajs`)
- **Natureza de cada depósito** (insubstituível / reconstruível / descartável) é **julgamento seu**
  a partir de quem escreve nele — cache e thumbnail são descartáveis; fila com job não-idempotente
  **não é**. Na dúvida, classifique como insubstituível e diga que é hipótese.

**→ durability.md** (gen 3.8 — como cada depósito sobrevive)

Depende do `data-stores.md`: **todo ativo listado lá precisa de um bloco aqui**, inclusive os sem
cobertura. Se este concern rodar em paralelo com o `data-stores`, reconcilie no Stitch (gate 10; o check #24 da verification é a rede depois).

- **Agendadores** — `crontab`/`/etc/cron.d/` referenciados no repo; units `*.timer` e `*.service`
  do systemd; `schedule:` em CI (`.github/workflows/*.yml` com `on: schedule`); `deploy/` e `ops/`
- **Scripts de cópia** — arquivos cujo nome ou conteúdo casa `backup`, `dump`, `pg_dump`,
  `mysqldump`, `mongodump`, `restic`, `borg`, `rclone`, `rsync`, `tar -c`
- **Cobertura gerenciada** — backup declarado em IaC (RDS `backup_retention_period`, snapshots),
  `lifecycle`/`versioning` de bucket, config de Supabase/PlanetScale
- **RPO, RTO e "restauração testada em" são AUTORAIS** — derivam das metas de qualidade. **Não
  invente.** Pergunte (Tier 5) ou marque `[TODO]`. Um RPO inventado é pior que um ausente.

**→ runtime.md** (gen 3.8 — os fluxos que importam)

- **Candidatos mecânicos** — rotas/handlers; consumidores de fila; jobs de cron; `depends_on` +
  `healthcheck` do compose (dá o cenário de **arranque**); handlers de erro e dead-letter (dão o
  cenário de **falha**)
- **A fonte mais produtiva é o grafo** — as `hyperedges` e as `communities` nomeadas do `GRAPH_MAP`
  já são literalmente fluxos que cruzam arquivos, e a Detection Matrix não os enxerga
- **A ESCOLHA dos 3-7 cenários é autoral.** Minere os candidatos, apresente a lista, deixe o humano
  escolher. Sete mal escolhidos valem menos que três certos.

**→ verified-by** (frontmatter de qualquer doc, gen 3.8)

Só entra o verificador que **falha se o doc mentir**:
- scripts sob `tools/`, `scripts/audit*`, `verify*/`, `check*`, `ops/verify*`
- steps de CI que rodam **checagem** (lint de infra, validação de schema, auditoria) — não build/deploy
- testes que assertam **estrutura** (existe a rota? a coluna? o serviço?), não comportamento de feature

Ausência é legítima (`verified-by` omitido). Apontar um script que não checa aquilo é **pior que
omitir** — dá falsa segurança.

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

