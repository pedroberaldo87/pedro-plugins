---
name: project-doc
description: "Use when entering a project without CLAUDE.md, after major structural changes, or when the user says \"project-doc\", \"documenta\", \"documentar\", \"documenta o projeto\", \"gera o claude.md\", \"atualiza o claude.md\", \"limpa os artefatos\", \"limpa os prints\", \"limpa o projeto\", \"arquiva protótipos\", or runs \"/project-doc clean\". Generates a modular documentation system (lightweight CLAUDE.md routing table + .claude/docs/*.md per concern + thin pointers for other AI tools) and detects/cleans up stale test artifacts (screenshots, runner output, temp files)."
---

# Project Doc v3 — Documentation System Generator

## Overview

Generates a **documentation system** for a project, not a single file.

**v3 em uma frase:** a doc deixa de ser file-scanner cego e passa a derivar de **toda evidência que o projeto tem** — arquivos, handoffs, memória, grafo, git log e os **transcripts das sessões** — guardando tudo num journal append-only versionado, projetando só o que está vivo e verdadeiro, sem nunca vazar um secret pro git. **A estrutura de saída é idêntica à v2** (markers `project-doc:v2` preservados): mudam a FONTE (cascata de tiers — Tier 0 discurso da invocação → Tier 1 arquivos → … → Tier 5 humano; ver **Sources**) e o MOTOR (journal + projeção — ver **Collect & Project**). Quem conhece a doc v2 não vê diferença estrutural, só uma doc mais completa e auto-mantida.

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
- `/project-doc --solo` — escape: força FULL/`--deep` a rodar **single-agent** (sem Workflow). **NÃO pula mais o grafo** — o grafo é obrigatório em todo modo (Passo 0); `--solo` só desliga o Workflow. Debug / projeto pequeno.
- `/project-doc --nested` — **NESTED (EXPERIMENTAL)**: monorepo only. Generates `apps/{app}/CLAUDE.md` as a **derived pointer** for each app that has a canonical doc in `.claude/docs/apps/{app}.md`. Serialized after t1d (runs only after a full FULL/`--deep` that already wrote the canonical docs). See **Nested Pointers** section.

**Grafo é premissa de TODO modo (v3.7):** rodou o project-doc = o grafo tem que existir e estar fresco. **Qualquer** invocação — FULL, `--deep`, incremental, `index`, `pointers`, `--rebuild`, `migrate`, `verify`, `clean`, **inclusive `--solo`** — executa o **Passo 0** (`graphify update --force`: cria se ausente, atualiza se stale, no-op se fresco) antes de ramificar por modo. `graphify` **não instalado ⇒ erro que bloqueia** (não degrada, não pula). `--solo` só desliga o Workflow (single-agent); **não pula mais o grafo**. A **destilação do mapa** (`graph_map.py`) + o **fan-out** continuam exclusivos do FULL/`--deep` — são quem *consome* o mapa; ver **Workflow Engine**. Garantir o grafo (universal) ≠ consumir o mapa no fan-out (FULL/`--deep`).

**FULL e `--deep` mineram via Workflow (fan-out por concern) por padrão** — ver **Workflow Engine**. Os demais modos rodam single-agent. `--solo` desliga o Workflow.

Doc names map directly to `.claude/docs/{arg}.md`.

**Separe o flag de modo da prosa (v3.8):** o argumento que casa um modo/doc-name conhecido (`migrate`, `verify`, `index`, `pointers`, `clean`, `--deep`, `--rebuild`, `--solo`, `--nested`, ou um doc-name válido) controla o **modo**; **todo o resto da invocação é prosa — o discurso direcionado (Tier 0), NÃO um doc-name desconhecido.** Não trate prosa livre como "doc-name que não casou → warn"; capture-a como o **brief do run** (ver **Tier 0** em Sources e o passo de captura na casca). Só avise "doc-name desconhecido" quando o argumento for claramente um token único parecido com doc-name e que não casa nenhum doc — não quando é uma frase. Sem flag reconhecido + prosa presente → FULL mode **com brief**.

## Nested Pointers (`--nested`, EXPERIMENTAL)

**What it is:** In a monorepo, Claude Code natively lazy-loads `apps/{app}/CLAUDE.md` when the agent edits files under that app. Without `--nested`, an agent editing `apps/payments/src/routes.ts` directly — without first exploring the project — might miss the canonical doc in `.claude/docs/apps/payments.md`. The `--nested` flag generates a **derived pointer** at `apps/{app}/CLAUDE.md` that covers this "edit-without-exploring" path by surfacing the name, port, and the canonical doc location.

**Why EXPERIMENTAL:** The gain is marginal (Claude Code users familiar with the project follow the Documentation Index; the lazy-load path is an edge case). Inline content would stale immediately (the canonical doc is the source of truth — duplicating gotchas causes drift). The pointer is intentionally thin.

**When it runs:** `--nested` is **not default**. It is opt-in and runs **serialized after t1d** — only once the FULL/`--deep` Workflow has already written all canonical docs in `.claude/docs/apps/{app}.md`. Never runs as a standalone mode before the canonical docs exist.

**What each generated file contains (the derived pointer format):**

```markdown
<!-- nested-pointer gen=3.6 derived-from=.claude/docs/apps/{app}.md sig=<sig> — nao editar a mao -->
# {app-name}

**Porta:** {port} · {1-line description of what this app does}

→ doc canônico: `.claude/docs/apps/{app}.md` (leia antes de mexer)
```

- **Header only:** name + port + 1-line description. No gotchas, no stack details, no commands — avoids stale content. These live in the canonical doc.
- **Provenance stamp:** HTML comment at the top: `<!-- nested-pointer gen=3.6 derived-from=.claude/docs/apps/{app}.md sig=<sig> — nao editar a mao -->`. The `sig` is the sha256 (first 8 hex) of the canonical doc body at generation time. Deterministic and content-addressed: the sig changes when the canonical doc changes, making staleness detectable.
- **Pointer line:** `→ doc canônico: .claude/docs/apps/{app}.md (leia antes de mexer)` — the only factual guidance; always current by reference.

**Scope:** one `apps/{app}/CLAUDE.md` per app that has a canonical doc. Apps without a `.claude/docs/apps/{app}.md` (because they follow the common pattern exactly) get **no nested pointer** — no empty file.

**Sig generation (deterministic):**
```python
import hashlib, pathlib
body = pathlib.Path(".claude/docs/apps/{app}.md").read_text()
# strip frontmatter block (everything between leading --- delimiters)
if body.startswith("---"):
    end = body.index("---", 3) + 3
    body = body[end:].lstrip("\n")
sig = hashlib.sha256(body.encode()).hexdigest()[:8]
```

**Staleness detection:** compare the `sig` in the HTML comment against `sha256(canonical_doc_body)[:8]`. If they differ, the nested pointer is stale and should be regenerated (run `/project-doc --nested` again after the canonical doc was updated).

**Do not hand-edit** the generated files — the comment warns explicitly. They are derived; the canonical doc is the source of truth.

## Output Protocol

Report each step to the user as you execute. Don't skip steps or batch them silently.

**Passo 0 — Grafo garantido (precede TODO modo, não renumerado nos protocolos abaixo):** antes de qualquer ramificação por modo, garanta o grafo fresco — `graphify update --force` (cria se ausente, atualiza se stale). `graphify` ausente ⇒ **erro que bloqueia** (instale; não há opt-out). Reporte `Grafo → criado | atualizado | já fresco`. No FULL/`--deep` o Passo 0 também destila o mapa (`graph_map.py`) pro fan-out (ver Workflow Engine); nos demais modos só garante o grafo.

### Full Mode

```
**Step 1/14:** Root → `/path/to/project`
**Step 2/14:** Layout → Standard | Monorepo (N apps)
**Step 3/14:** Type → app | lib | cli
**Step 4/14:** Package manager → pnpm | yarn | bun | npm
**Step 5/14:** Mode → FULL | MIGRATE (v1→v2 detected) | CREATE (no CLAUDE.md)
**Step 6/14:** CLAUDE.md → v1 markers (will migrate) | v2 index (will update) | none (will create)
**Step 7/14:** Graph (**Passo 0 — obrigatório em todo modo**) → `graphify update --force` {criado | atualizado | já fresco} + graph_map (FULL/`--deep`) → {N god nodes, M comunidades, K hyperedges} | **graphify ausente → ERRO que bloqueia (instale)**
**Step 8/14:** Collecting → **tier 0 discurso** (se houve: {N fato(s) persistido(s) no journal · M direção(ões) guiando este run}) + tier 1 scan (arquivos por concern, **ranqueados por fan-in do grafo**) + `journal.py` tiers 2-4 → {new_events, live_count, stale}
**Step 9/14:** Generating docs → {list of .claude/docs/*.md to create/update, with line counts}
**Step 10/14:** Writing CLAUDE.md index → {N lines}
**Step 11/14:** Pointer files → {list created/updated/skipped}
**Step 12/14:** Verification → {results summary, inclui auditoria grafo×doc}
**Step 13/14:** Commit + push → {commitado `<hash>` + pushado | commitado, push pulado: `<motivo>` | nada a commitar}
**Step 14/14:** Token impact → Before: {N} lines always-loaded | After: {M} lines always-loaded + {K} docs on-demand | Savings: {X}%
```

### Incremental Mode

```
**Step 1/4:** Root → `/path/to/project`, scope → {doc-name}
**Step 2/4:** Scanning {doc-name} sources... (list files read) + **tier 0 discurso** (se houve prosa: {N fato(s) persistido(s) · M direção(ões)})
**Step 3/4:** Written → `.claude/docs/{doc-name}.md` ({N} lines), CLAUDE.md index updated
**Step 4/4:** Commit + push → {commitado `<hash>` + pushado | commitado, push pulado: `<motivo>` | nada a commitar}
```

### Migrate Mode

```
**Step 1/6:** Root → `/path/to/project`
**Step 2/6:** Parsing v1 block... ({N} sections found)
**Step 3/6:** Extracting to .claude/docs/... ({list of docs created})
**Step 4/6:** Rewriting CLAUDE.md as v2 index... ({N} lines)
**Step 5/6:** Commit + push → {commitado `<hash>` + pushado | commitado, push pulado: `<motivo>` | nada a commitar}
**Step 6/6:** Token impact → Before: {N} lines monolithic | After: {M} lines index + {K} docs on-demand | Savings: {X}%
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

**Passo 0 (UNIVERSAL — roda em TODO modo, logo após identificar o root, antes de ramificar):** garanta o grafo fresco — `graphify update "<root>" --force` (cria se ausente, atualiza se stale, no-op se fresco). `graphify` **não instalado ⇒ erro que bloqueia** o run inteiro (único pré-requisito duro; nem `--solo` escapa). Ver **Knowledge Graph Integration** / **Workflow Engine → Passo 0**. A destilação do mapa (`graph_map.py`) só ocorre no FULL/`--deep` (quem consome o fan-out).

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
   - **Em QUALQUER ramo acima, a prosa livre que sobra além do flag/doc-name é o discurso direcionado (Tier 0)** — separada do flag (ver **Invocation Modes**), capturada no passo 6 (não muda o modo escolhido). Prosa sem nenhum flag reconhecido → FULL mode + brief.
6. **Collect from the source cascade** (see **Sources** + **Collect & Project**). Tier 0 = capture the invocation discourse and `adopt` the durable facts; Tier 1 = scan files via the Detection Matrix below; tiers 2-4 = run the lib (`journal.py`); tier 5 = ask the human for critical gaps.
   - **Tier 0 vale em TODO modo que aceita prosa** (FULL, `--deep`, **e os single-agent** incremental/`index`/`pointers`/`--rebuild`/`--solo`): classifique fato vs direção, `adopt` os fatos (passa pelo scrubber, idempotente), e **reporte o echo-back**. A descrição detalhada está na **casca passo 2** (Workflow Engine) — é a instanciação FULL/`--deep`; **nos modos single-agent a casca roda o MESMO passo** (capturar → classificar → `adopt` fatos → echo-back), só que **sem `RUN.brief`** (não há fan-out): a direção orienta o agente único direto. Nunca descarte prosa só porque o modo é single-agent.
   - **FULL / DEEP:** rode a **checagem ativa (passo 0.1)** e minere via **Workflow** (fan-out por concern) — ver **Workflow Engine**. A checagem **executa** `python3 plugins/project-doc/lib/pattern_check.py --project-root "<root>"` (não só lê o número do marker — roda o script): `in_pattern==false` => fora do padrão => reconstrói via Workflow `deep` + garimpo. `--solo` força single-agent.
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
8. **Generate `.claude/docs/*.md`** — each doc with YAML frontmatter and content from its template (see `references/templates.md` → Doc File Templates). Create `.claude/docs/` directory if needed.
9. **Generate CLAUDE.md index** — lightweight routing table (see `references/templates.md` → Index Template). Preserve any Custom Rules section and any content outside the v2 markers.
10. **Generate thin pointer files** — pure redirects for other AI tools (see `references/templates.md` → Thin Pointer Templates). Only create if file doesn't already exist with custom content.
11. **Preserve human content** — any content outside `<!-- project-doc:v2 -->` / `<!-- project-doc:v2:end -->` markers is preserved untouched. The `## Custom Rules` section inside the markers is also preserved across regenerations.
12. **Write all files**
13. **Run verification** (see `references/verification.md`)
14. **Auto commit + push** (FULL e qualquer modo que ESCREVE doc — `verify`/`clean` pulam) — persiste os artefatos de doc no git, **escopado**:
    - **`git add` cirúrgico — SÓ os artefatos de doc:** `.claude/CLAUDE.md`, `.claude/docs/`, `.claude/.project-doc/findings.jsonl`, `.claude/.project-doc/ledger.json`, **`graphify-out/` se existir** (o grafo é documentação obrigatória — premissa do FULL/`--deep` — e precisa viajar entre máquinas igual à doc; `git add graphify-out/` **respeita o `.gitignore` interno**, então entram `graph.json`/`cost.json`/comunidades e ficam de fora `cache/`/`.graphify_*`), e os ponteiros gerados (`AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.github/copilot-instructions.md`). **NUNCA `git add -A`** — não varrer trabalho não-relacionado do repo-alvo. `secrets/`/`backups/` ficam de fora (gitignored).
    - **Commit** na branch atual, mensagem `docs(project-doc): regenera CLAUDE.md + .claude/docs + journal`. Nada staged (doc não mudou) → pula e anota "nada a commitar".
    - **Push seguro:** `git fetch` antes; **nunca `--force`**; divergiu de `origin` → tenta `pull --rebase` e re-push, senão reporta. Sem remote/upstream → commita e **pula o push**. Não é repo git → pula commit+push.
    - **Falha de push** (conflito/permissão) → reporta o erro real e segue (commit local feito; doc no disco).
15. **Report to user:**
    - **Discurso capturado (Tier 0, echo-back):** `→ N fato(s) persistido(s) no journal · M direção(ões) guiando este run` + lista curta de cada um (fato: o texto; direção: a ordem) — é a garantia visível de que nada do que o humano falou foi descartado. Omita a linha se não houve prosa na invocação.
    - Token impact (before/after comparison)
    - List of docs generated with line counts
    - List of pointer files created/updated/skipped
    - Any `[TODO: ...]` gaps found
    - Verification results
    - **Commit + push:** `commitado {hash} + pushado` | `commitado, push pulado: {motivo}` | `nada a commitar`
    - Knowledge graph status + suggestion (see Knowledge Graph Integration section)
    - Stale test artifacts detected: {N} ({breakdown}). Offer `/project-doc clean` (see Artifact Cleanup) — detect & report only, never delete here
    - Ask: "Quer preencher os TODOs agora?"

## Sources — cascata de tiers (v3; Tier 0 desde v3.8)

v2 documentava só a partir de **arquivos**. v3 colhe de TODA a evidência do projeto, em cascata ordenada por densidade/custo. Cada tier alimenta os MESMOS campos dos templates v2 (`## Decisões de Arquitetura`, `## Gotchas`, etc.) — a estrutura de saída é idêntica; muda a fonte e o motor.

- **Tier 0 — O discurso da invocação** (v3.8): toda a prosa que o humano digita JUNTO da invocação, além do flag de modo ("documenta, e lembra que o módulo X é legado e vai morrer", "o motivo do network_mode host é Y", "foca no auth", "ignora a pasta Z"). Fonte **autoritativa** — é o humano falando AGORA, conhecimento que não está em arquivo nenhum e que uma mineração cega perde. **Captura automática** (sem marcador — a prosa já está no contexto do agente). Classificada em DUAS naturezas:
  - **fato / conhecimento durável** ("o motivo do X é Y", "o módulo Z é legado") → **persiste** no journal via `journal.py adopt` (versionado, viaja entre máquinas, sobrevive a `--rebuild`). É o "não se perde" forte.
  - **direção de processo** ("foca no auth nesta rodada", "ignora a pasta experimental") → **só guia este run** (vai pro `RUN.brief` do Workflow), NÃO grava no journal — não polui o conhecimento durável com ordem efêmera.
  Distingue do **Tier 5** (o humano **reativo** — a skill *pergunta* quando acha lacuna): o Tier 0 é o humano **proativo**, no momento da invocação. Vive **nesta skill** (captura + julgamento de classificação). Ver o passo de captura na casca (**Workflow Engine → A casca**) e a composição com a Fase B (**Sequência "melhor dos dois mundos"**).
- **Tier 1 — Arquivos** (a Detection Matrix abaixo): stack, deps, rotas, schema, config. Custo baixo. É o scan que a v2 já fazia. Vive **nesta skill** (julgamento de leitura).
- **Tier 2 — Destilado pronto:** `.claude/HANDOFF*.md`, `memory/*.md`, `graphify-out/`, `.claude/ata/`. Decisões/gotchas já mastigados. Colhido pelo lib (`journal.py`).
- **Tier 3 — git log:** o "porquê" das mudanças (mensagens de commit + arquivos tocados, que viram âncoras). Colhido pelo lib.
- **Tier 4 — Transcripts:** as sessões `.jsonl` de **todos os slugs sob o projeto** — direcionamentos, rejeições, decisões que nunca viraram arquivo. Custo alto. Colhido pelo lib via a engine compartilhada (`collect_engine.py`).
- **Tier 5 — O humano:** lacuna crítica sem fonte (ex: host SSH que não está em arquivo nenhum) → **pergunte ao Pedro**, em vez de marcar `[TODO]` e seguir. Vive **nesta skill**.

Tiers 2-4 são **mecânicos** e vivem em `plugins/project-doc/lib/journal.py` (degrada gracioso: sem a engine vendorada, pula o tier 4 e usa tiers 1-3). Tier 0, tier 1 e tier 5 são desta skill (captura/julgamento). O fluxo completo (coleta → projeção) está em **Collect & Project**.

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
- **Em TODO modo (v3.7), o grafo é GARANTIDO, não só detectado** — o **Passo 0** roda `graphify update --force` (cria/atualiza) em qualquer invocação do project-doc; `graphify` ausente ⇒ erro que bloqueia. **Adicionalmente no FULL/`--deep`** o Passo 0 destila o mapa via `graph_map.py`, que **prioriza os arquivos de cada concern por fan-in** pra leitura profunda. A sugestão (`/graphify`) sobrevive só **fora da execução** (proatividade ao navegar o projeto) ou pro labeling LLM caro — ver **Knowledge Graph Integration**.
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
  **Exceção Tier 0 (v3.8):** fato vindo do discurso da invocação (é o humano falando AGORA — opinião/intenção como "o módulo X vai morrer") é **autoritativo**: não-confirmável pelo código → `[relatado]`, **nunca** invalidado por "código não confirma". Só mata se o código o **contradiz** frontalmente (evidência alta, igual ao gate 2).
- **Curadoria:** se o Pedro editar à mão um finding gerado, registre pra sobreviver à re-projeção:
  `python3 .../journal.py curate --project-root "<root>" --id <id> --text "..."` (a projeção respeita o texto curado).

A doc canônica é **derivada e descartável** (`--rebuild` re-cria do journal). O journal é a verdade; a doc é a vista. Critério de aceite: a doc cita ≥1 gotcha/decisão que só existe em sessão/handoff, e **nenhum** gotcha que o código atual contradiz.

## Workflow Engine — FULL e --deep mineram via Workflow (v3.1) + grafo dirige a leitura profunda (v3.2) + merge nativo de nuances (v3.4)

**O problema que isso resolve:** numa janela única, sob volume de contexto, o agente "tira o pé" — corta o Tier 1 scan (não lê o código de verdade) e a Reconciliação (confere 5 de 30 `stale_ids`). A COLETA (Python) é determinística e não tira o pé; quem tira é a **projeção** quando feita numa janela só. A solução: nos modos que mineram, a projeção roda como um **Workflow** com **fan-out por concern** — cada agente recebe uma fatia (um doc-alvo), tem working-set pequeno, e não tem medo do volume. A soma cobre tudo.

### Fronteira de modos — quando é Workflow, quando é single-agent

| Modo | Motor | Por quê |
|---|---|---|
| **FULL** (`/project-doc`) e **`--deep`** | **Workflow** (fan-out) | mineram fontes novas + projetam tudo → é onde o medo de contexto bate |
| incremental (`/project-doc <doc>`), `index`, `pointers`, `--rebuild`, `migrate`, `verify`, `clean` | **single-agent** (como antes) | não mineram / 1 concern só / re-projeção pura → nada a paralelizar |

- `--rebuild` re-projeta do journal **sem minerar** → single-agent, sem backup, sem garimpo.
- Flag de escape **`--solo`**: força FULL/--deep a rodar single-agent (debug/projeto pequeno). Sem `--solo`, FULL/--deep **disparam o Workflow direto** — não anuncie custo nem peça confirmação.

### Passo 0 — Grafo garantido (TODO modo) + Passo 0.0 — mapeado pro fan-out (FULL/`--deep`)

**Premissa (v3.7):** nenhuma versão do project-doc jamais leu o código-fonte de verdade — o Tier 1 sempre foi uma allowlist (manifestos/configs/schemas/rotas) + `ls`. A única coisa que mapeia o codebase inteiro é o **grafo (graphify)**. Desde a v3.7 o grafo é **documentação obrigatória em qualquer invocação do project-doc** (não só no FULL/`--deep`): rodou a doc = o grafo tem que existir e estar fresco. **Postura: roda sempre, informa, não oferece** (a sugestão `/graphify` sobrevive só fora da execução / pro labeling caro — ver **Knowledge Graph Integration**). O grafo garantido dirige a leitura profunda do código (Fase A, FULL/`--deep`) e audita a cobertura no fim (gate 7 / check #17).

**Passo 0 (UNIVERSAL — todo modo, ANTES de ramificar):** garante o grafo fresco, sem perguntar. Detecta staleness (graph.json ausente, ou mtime < `git log --format=%aI -1`) e roda:
```bash
graphify update "<root>" --force    # `update`: re-extrai por AST, ZERO LLM, ~segundos, não-interativo, idempotente
                                     # `--force`: sobrescreve graph.json mesmo se a re-extração tiver MENOS nós (após refactor que apaga código)
```
Ausente → cria (AST); stale → atualiza; fresco → no-op. O `--force` garante o overwrite em refactors destrutivos (sem ele, uma re-extração menor poderia ser recusada). **Não anuncie custo nem peça confirmação** — informa "grafo: criado / atualizado / já fresco" no Output Protocol. O labeling LLM de comunidades (nomes bonitos) é upgrade opcional via `/graphify` completo, **fora** do caminho crítico; `update --force` preserva labels já existentes.
- **`graphify` não instalado** → **erro que bloqueia, em QUALQUER modo**: "o project-doc exige o grafo; instale o `graphify`". NÃO degrada, NÃO pula — nem com `--solo`. É o único pré-requisito duro do project-doc.
- **`--solo` NÃO pula o Passo 0** — ele só desliga o Workflow (cai pro single-agent). O grafo roda igual.

**Passo 0.0 (SÓ FULL/`--deep` — destila o mapa pro fan-out):** o grafo bruto tem milhares de nós — não engula inline. Só os modos com Workflow consomem o mapa, então só eles destilam:
```bash
python3 plugins/project-doc/lib/graph_map.py --project-root "<root>"
```
Devolve JSON: `{available, stats, files[], god_nodes[], communities[], generic_communities[], hyperedges[]}` (ver **Schemas / GRAPH_MAP**). Como o Passo 0 já garantiu o grafo, `available:false` aqui é anomalia (graphify falhou após o `update`) ⇒ **ERRO** — não há fan-out sem mapa. O mapa alimenta o particionamento (passo 5) e a leitura profunda (Fase A).



Antes de minerar, **execute** `python3 plugins/project-doc/lib/pattern_check.py --project-root "<root>"` e **classifique a doc existente** com base no resultado (esta é a checagem ativa — roda no passo 0 da casca, **não é leitura manual do marker**):

- **Ausente** (sem `.claude/CLAUDE.md`) → CREATE: Workflow + `deep` (cold-start). Sem backup/garimpo (não há doc antiga).
- **`in_pattern==false`** (script retorna fora do padrão) → **sequência full forçada**: backup + Workflow + **`deep`** + garimpo. O script detecta QUALQUER das condições abaixo como violação:
  - (a) markers v1 (`project-doc:start/end`), **ou sem markers**, ou doc escrita à mão;
  - (c) markers v2 **mas sem journal** (`.claude/.project-doc/findings.jsonl` ausente) → doc gerada por motor pré-v3, **nunca minerada** — o caso que mais engana (parece boa, o agente a "seguia");
  - (b) algum `.claude/docs/*.md` sem frontmatter YAML;
  - (d) algum doc sem linha `doc-sig:` no frontmatter;
  - (e) `gen_found` **ausente ou diferente** de `CURRENT_GEN` → o motor mudou de padrão desde a última geração.
- **`in_pattern==true`** → FULL normal: Workflow + `update` (delta) + backup/garimpo (sempre que há doc, pra preservar nuance).

A regra-mãe: **doc fora do padrão não é base confiável** — não faça update delta leve em cima dela; reconstrua por mineração (`deep`) e use a antiga só como fonte de nuances (garimpo). O marker passa a gravar a versão do gerador — ver **Update Mechanism**.

### A casca (esta skill) vs o Workflow (o motor)

Espelha o qa-loop: o Workflow roda em background e **não pergunta nada no meio**; tudo entra **embutido no script como `const`** (NÃO via `args` — ver gotcha no molde), os gates são lógica do script (JS), não "o agente lembrar a regra".

**CASCA — passo 0 (antes de disparar):**
1. Identify root/layout/type/PM + **grafo garantido + mapa (0.0)** + **checagem ativa (0.1)** → decide `update` vs `deep` e se força a sequência. **Separa o flag de modo da prosa** da invocação (ver **Invocation Modes**): o que sobra de prosa é o **discurso direcionado (Tier 0)**.
2. **Captura do discurso (Tier 0, v3.8 — antes da coleta Python):** se houve prosa na invocação, **classifique** cada pedaço em **fato durável** vs **direção de processo** (mesmo julgamento da projeção). Para cada **fato**, **persista** com a porta que já existe:
   `python3 plugins/project-doc/lib/journal.py adopt --project-root "<root>" --text "<fato>" --raw-kind user_directive`
   (`adopt` → `discovered` de 1ª classe; passa pelo MESMO scrubber de secret; idempotente por `finding_id` — re-rodar não duplica; ver `run_adopt`). `user_directive` é tratado como primário (`gate=True`) na projeção. **A direção de processo NÃO é persistida** — vai só pro `RUN.brief` (montado no passo 5). Persistir ANTES da coleta (passo 4) garante que os fatos entrem no `live[]` desta rodada. Guarde os contadores `{fatos_persistidos, direcoes}` pro echo-back.
3. **Backup** (se há doc): garanta `.claude/.project-doc/backups/` no `.gitignore` (é **efêmero, não versiona** — ao contrário do journal/ledger, que SÃO versionados); então `cp` de `CLAUDE.md` + `.claude/docs/` → `.claude/.project-doc/backups/<UTC-ts>/` + `MANIFEST.json` (git_head, mode). Sem agente.
4. Roda a **coleta Python 1×** (`journal.py update|deep`) → `{live[], stale_ids, ...}` (já inclui os fatos do Tier 0 adotados no passo 2). A mineração **nunca** entra no fan-out (é determinística e barata).
5. **Dimensiona** o fan-out e **particiona** por concern, carregando DUAS coisas por concern: (a) os findings (`live[]`/`stale_ids`, roteamento grosso por `raw_kind`+anchor: gotcha→patterns, decisão→architecture, anchor `schema.prisma`→database, etc.) **e** (b) a **lista de arquivos-fonte priorizada pelo grafo** — cruze a Detection Matrix invertida (padrões de path: `schema.prisma`→database, `routes/`→api, etc.) com `GRAPH_MAP.files[]` (ranqueado por fan-in) pra dar a cada agente seus arquivos do concern **em ordem de relevância**, mais os `god_nodes` que caem na fatia. As `communities`/`hyperedges` nomeadas do grafo (módulos/workflows que a Detection Matrix não vê) vão pro concern **architecture** (conteúdo de `architecture.md`/Decisões), não viram eixo de fan-out. No monorepo, um sub-agente por `app×concern` que diverge do comum. **Monta o `RUN.brief`** (v3.8): o discurso direcionado verbatim (fato + direção) num campo do `const RUN` — dado pequeno, vai inteiro pro prompt de **todo** agente da **Fase A** (é onde a projeção/leitura acontece), pra orientação sem anchor (ex.: "foca no auth") não depender do roteamento por concern. Garimpo/Merge não consomem o brief (tarefa negativa / inserção de nuance já aprovada).

**WORKFLOW — fases:**
- **Fase A — Scan+Reconcile + leitura profunda (PARALELO):** 1 agente por concern. Cada um executa o protocolo **Project (seu julgamento)** acima, restrito à sua fatia, e agora faz **leitura profunda guiada pelo grafo** (capacidade nova do v3.2 — caminho 1):
  - **Lê o código-fonte real** dos arquivos da fatia, na **ordem de fan-in** que o `GRAPH_MAP` deu (maior fan-in primeiro) — não só os manifestos, mas o **corpo das funções** dos `god_nodes` e dos arquivos quentes. Daí extrai gotchas/convenções/decisões que **só o código revela** (o que o AST não vê: invariantes, efeitos colaterais, "por que assim").
  - **Trava de contexto:** lê integralmente os **top-N por fan-in** do concern (teto por agente); o resto entra como "coberto por menção", não leitura integral. O agente **reporta no `DOC_SECTION` o que leu de fato vs o que só listou** (`files_read[]` / `files_listed[]`).
  - Reconcilia cada finding da fatia contra o código que leu (confirma / `[relatado]` / propõe invalidação), escreve a seção. Devolve `DOC_SECTION`. **A doc nova é a BASE canônica — projetada SEM ver a doc antiga.**
  - **Frontmatter obrigatório (v3.4):** todo `body_md` começa com o bloco YAML (`generated`/`project`/`scope`) — vale **inclusive pros shared docs do monorepo** (foi onde a v3.2 esquecia). O agente marca `has_frontmatter:true`; o gate de frontmatter (Stitch) injeta se vier `false`. Não é "lembrar a regra" — é trava.
- **Fase B — Garimpeiro de nuances (1 agente, só se há doc antiga):** recebe a doc antiga (backup) + a nova + leitura do código/journal + o **JSON de `live_findings`** (`id`/`text`/`raw_kind`). Tarefa **negativa**: achar info verdadeira presente só na antiga e **ausente** na nova; validar cada candidata contra o código. Devolve `NUANCE_CANDIDATES`. Não reescreve nada — só propõe adições. **Anti-falso-positivo + finding_id (v3.4):** por candidata, (i) auto-check determinístico — se o **token-chave** da nuance já aparece na prosa nova, marca `proposed_action: drop` (a v3.2 trouxe 182 candidatas e só ~52 eram reais; ~70% era já-coberto reformulado); (ii) casa contra os findings vivos e preenche `match_to_journal{finding_id, relation}` — `curate_existing` quando achou par, `new_discovered` só quando é genuinamente nova (sem isso o `adopt` cego duplica, porque o journal só dedup por texto exato).
- **Fase C — Stitch (JS puro, sem LLM):** aplica os gates (abaixo), dedup, frontmatter, secret, monta o índice. Devolve `STITCH_RESULT` — incluindo `docs_with_nuances[]` (cada doc + suas `approved_nuances[]`) pra Fase D.
- **Fase D — Merge de nuances na prosa (PARALELO, só se há `docs_with_nuances`, v3.4):** 1 agente por doc que ganhou nuance aprovada. Recebe o `body_md` da Fase A + as `approved_nuances` daquele doc e **enxerta cada uma na prosa, sem inflar nem duplicar**. Travas: não reescreve o que já está lá, não copia a doc antiga, só costura as nuances confirmadas no ponto certo da seção. Devolve `MERGED_DOC` (`body_md` final + `merged_count` + `skipped[]`). **A Fase D é LLM — então NÃO é a autoridade final:** o `gateMergedDocs` (JS, gate 9) valida a saída e rejeita qualquer merge que tenha regredido fatos-chave vs a Fase A (a base canônica), caindo pro body da Fase A. As "travas" acima são só instrução de prompt; a garantia é o gate. **Por que existe:** o `journal.py rebuild` é mecânico (re-fold de findings, NÃO re-projeta prosa) — sem esta fase, `adopt`+`rebuild` registra a nuance mas ela nunca entra no `.md`. Era o passo que a v3.2 fazia à mão.

**CASCA — passo final (depois do Workflow):**
6. **Só a casca escreve no journal** (serializa o append-only): aplica as invalidações aprovadas + reintegra **com guarda de finding_id** (v3.4) — `curate` quando `relation==="curate_existing"` (finding existe, perdeu o tom), `adopt` **só** quando `relation==="new_discovered"` **e** o `finding_id` não está no `live[]` (nunca adopt cego — era o risco das duplicatas), `invalidate` quando a antiga contradiz o código.
7. **Escreve os arquivos** usando o `body_md` **mergeado da Fase D que passou no gate anti-regressão** (gate 9) pros docs que ganharam nuance; merge **rejeitado** ⇒ escreve o `body_md` da **Fase A** daquele doc (preserva a correção, perde só a costura); os demais saem da Fase A. A prosa já está materializada aqui — o journal (passo 6) é registro fiel, não a fonte da escrita.
8. **Re-projeta** (`journal.py rebuild`) pra reconciliar o estado vivo do journal — o `--rebuild` futuro parte daí. + **Verification** (inclui secret + frontmatter + anti-regressão, check #18) + relatório com telemetria (nº de agentes por fase, invalidações aplicadas vs propostas, nuances mergeadas vs dropadas, **merges rejeitados pelo gate 9**). **Nunca declarar PASS com `merge_rejected` não reportado.**

### O script do Workflow (molde — estilo qa-loop)

```javascript
export const meta = {
  name: 'project-doc-mine',
  description: 'Minera a doc via fan-out por concern; cada agente lê o código da sua fatia e reconcilia',
  phases: [{ title: 'Scan+Reconcile' }, { title: 'Garimpo' }, { title: 'Stitch' }, { title: 'Merge' }],
}
// ⚠️ NÃO use `args` — embuta os dados do run como CONST no topo do script (ver gotcha abaixo).
// A casca PREENCHE este RUN ao gerar o script (substitui os placeholders pelos valores reais do run):
const RUN = {
  root: '<ABS_ROOT>', deep: false, hasOldDoc: true, backupPath: '<ABS_BACKUP>',
  brief: '<DISCURSO_DIRECIONADO_VERBATIM>',  // Tier 0 (v3.8): prosa da invocação (fato já adotado no journal + direção de processo). '' se não houve. Vai pro prompt de TODO agente.
  graphMap: { /* saída do graph_map.py — sempre populado (o passo 0.0 garante; available:false já abortou antes) */ },
  // files[] já vem ranqueado por fan-in; findings/staleIds podem ser referenciados por id (os agentes leem do disco)
  concerns: [ /* {key, app, files:[], findings:[], staleIds:[], godNodes:[], template} */ ],
}

phase('Scan+Reconcile')                                  // FAN-OUT: 1 agente por concern
const sections = (await parallel(RUN.concerns.map(c => () =>
  agent(scanReconcilePrompt(RUN.root, c, RUN.brief), { label: `concern:${c.app ? c.app+'/' : ''}${c.key}`,
    phase: 'Scan+Reconcile', schema: DOC_SECTION })
))).filter(Boolean)

let nuances = { candidates: [] }
if (RUN.hasOldDoc) {                                      // só se havia doc antiga
  phase('Garimpo')
  nuances = await agent(garimpoPrompt(RUN.root, RUN.backupPath, sections),
    { label: 'garimpeiro', phase: 'Garimpo', schema: NUANCE_CANDIDATES }) || nuances
}

phase('Stitch')                                          // GATES = JS puro, sem LLM
const stitched = stitchAndGate(sections, nuances, RUN.graphMap)  // adjudica invalidação, dedup-vs-prosa, frontmatter, secret, budget + AUDITORIA grafo×doc; devolve docsWithNuances[]

let merged = []                                          // Fase D só roda se sobrou nuance aprovada
if (stitched.docsWithNuances && stitched.docsWithNuances.length) {
  phase('Merge')                                         // FAN-OUT: 1 agente por doc-que-ganhou-nuance
  merged = (await parallel(stitched.docsWithNuances.map(d => () =>
    agent(mergePrompt(RUN.root, d.doc_path, d.body_md, d.approved_nuances),
      { label: `merge:${d.doc_path}`, phase: 'Merge', schema: MERGED_DOC })
  ))).filter(Boolean)
  merged = gateMergedDocs(merged, stitched.docsWithNuances)  // GATE JS anti-regressão (gate 9): Fase D só INSERE; fato-chave regrediu vs Fase A ⇒ rejeita, cai pro body da Fase A
}
return { sections, nuances, stitched, merged }
```

A casca lê o `return` e executa os efeitos colaterais (passo final), escrevendo o `merged[].body_md` pros docs que passaram pela Fase D e o `sections[].body_md` pros demais. `scanReconcilePrompt`/`garimpoPrompt`/`mergePrompt`/`stitchAndGate`/`gateMergedDocs` são helpers do próprio script: os três primeiros montam o prompt do agente a partir da fatia; os dois últimos são **JS determinístico** (sem LLM). `scanReconcilePrompt` recebe o `RUN.brief` (Tier 0) e o **costura no prompt como orientação do humano pra esta rodada** ("o usuário direcionou: …"); o agente segue a direção (foco/escopo) e trata os fatos como conhecimento autoritativo a projetar na sua fatia. `mergePrompt` instrui o agente a (a) usar o `body_md` **do prompt** como base e **NÃO ler o `.md` do disco** (ainda é a versão ANTIGA — a casca só escreve depois do Workflow), e (b) enxertar SÓ as `approved_nuances` na prosa, sem reescrever nem duplicar. `gateMergedDocs` é a **rede determinística** que não confia nessa instrução (ver gate 9).

> **GOTCHA — embuta os dados como `const`, NÃO via `args`.** O script do Workflow é **específico deste run** (os concerns/findings/graphMap são daquele projeto naquele momento), então a casca o gera com os dados já dentro (`const RUN = {...}`). **Não dependa do `args` global do Workflow:** ele foi observado chegar `undefined` (passado como string JSON, ou na re-invocação via `scriptPath`, que NÃO recarrega `args`), e aí o `RUN.concerns.map`/`args.concerns.map` estoura com *"undefined is not an object"*. Const é uma peça móvel a menos e funciona de primeira. **Mantenha os dados pequenos:** embuta só a LISTA de concerns (keys, app, paths de arquivos ranqueados, ids de findings) + o `graphMap` **destilado** (a saída enxuta do `graph_map.py`, nunca o `graph.json` bruto de MBs); o conteúdo pesado (corpo dos findings, código-fonte) os **agentes leem do disco** (eles têm Read/Bash — o orquestrador JS não tem filesystem).

### Sequência "melhor dos dois mundos" (quando há doc antiga)

A trava anti-"caminho fácil" é **estrutural**, não confiança: a doc nova já existe e é a base ANTES de a antiga ser lida (Fase B vem depois da A). O garimpeiro só pode **propor adições validadas contra o código** — nunca reescrever, nunca copiar a antiga. Conteúdo presente nas duas é descartado por construção (o gate de dedup-vs-prosa dropa o já-coberto). Fluxo: backup → Fase A (doc nova, isolada, com frontmatter) → Fase B (garimpa o que faltou, valida, casa finding_id) → Stitch filtra e aprova as nuances reais → **Fase D enxerta as aprovadas na prosa** → casca escreve o `body_md` mergeado + registra no journal (`curate`/`adopt` com guarda) → `rebuild` reconcilia o estado vivo. Resultado: mineração fresca + nuances curadas que só viviam na doc antiga, **de fato dentro do `.md`** (não só no journal).

**Composição Tier 0 × Fase B — duas garantias diferentes (v3.8, não confundir):**
- **Tier 0 + journal = garantia PRIMÁRIA.** O discurso da invocação (fato durável) é `adopt`-ado no journal **versionado** ANTES da coleta, então entra no `live[]` e é projetado nesta mesma rodada. É a fonte da verdade — viaja entre máquinas e sobrevive a `--rebuild`. Esse é o "não se perde" forte.
- **Fase B (garimpeiro) = rede SECUNDÁRIA cross-run.** Compara a doc **antiga renderizada** × a nova fria e preserva conteúdo opinativo que só vivia no `.md` (entra `[relatado]` quando o código não confirma). **Mas ela não cobre o discurso de invocação na primeira vez** — esse texto não está na doc antiga, está só no chat; quem o captura é o Tier 0. As duas se compõem: **o Tier 0 põe o discurso DENTRO da doc/journal; a Fase B protege o que já está documentado.** Não confiar só no diff: sem o Tier 0, o que o humano fala na invocação nunca chega à doc pra a Fase B ter o que preservar.

### Schemas (campos pros gates, não texto solto)

- **`GRAPH_MAP`** (saída do `graph_map.py`, lido pela casca; não é schema de agente) = `{available, stats{nodes, links, hyperedges_total, communities_named, god_nodes}, params{god_min, hyper_min}, files[{source_file, fan_in, node_count, god_nodes[]}], god_nodes[{id, label, source_file, source_location, fan_in, fan_in_total, relations_in}], communities[{label, size, community_ids[], files[]}], generic_communities[{label, count}], hyperedges[{id, label, confidence_score, nodes[], source_files[]}]}`. **`available` é gate do passo 0.0, não modo do Workflow:** no FULL/`--deep`, `available:false` (`{available, reason, expected_path}`) ⇒ erro/abort ANTES das fases — quando o Workflow roda, `available` é sempre `true`. A casca pode ignorar campos extras — o contrato é um superset estável.
- **`DOC_SECTION`** = `{concern, app, complete, doc_path, inline, body_md, has_frontmatter, confirmed_ids[], relatado_ids[], invalidations[{id, reason, evidence, confidence}], nuances[], todos[], secret_suspects[], files_read[], files_listed[]}` (`has_frontmatter`: bool — o agente confirma que o `body_md` abre com o bloco YAML; o gate de frontmatter injeta se `false`. `files_read`/`files_listed`: o que leu integralmente vs só listou — prova da leitura profunda v3.2).
- **`NUANCE_CANDIDATES`** = `{candidates[{type, claim, where_in_old, covered_in_new (bool — o token-chave já aparece na prosa nova?), validation{status: confirmed|unconfirmable|contradicted, evidence}, match_to_journal{finding_id, relation: curate_existing|new_discovered}, proposed_action: curate|adopt|invalidate|drop}], summary}` (`covered_in_new` + `match_to_journal.finding_id` são **obrigatórios** na v3.4 — alimentam o gate de dedup-vs-prosa e o roteamento seguro de adopt/curate; sem eles a reintegração duplica).
- **`STITCH_RESULT`** = `{index_md, docs_to_write[], inline_sections[], docs_with_nuances[{doc_path, body_md, approved_nuances[]}], approved_invalidations[], rejected_invalidations[], dropped_nuances[], frontmatter_injected[], dedup_log[], audit_warnings[]}` (`docs_with_nuances`: o que a Fase D vai mergear; `dropped_nuances`: as já-cobertas/contraditas; `frontmatter_injected`: docs que vieram sem o bloco e o gate consertou; `audit_warnings`: god nodes / comunidades / hyperedges do grafo sem cobertura — ver gate 7).
- **`MERGED_DOC`** (saída da Fase D, v3.4) = `{doc_path, body_md (a prosa final, com as nuances enxertadas), merged_count, skipped[{claim, reason}]}`. O agente NÃO reescreve o doc — só costura as `approved_nuances` no ponto certo; o que não couber sem inflar vai pra `skipped` com motivo.

### Gates determinísticos (JS no Stitch, não o agente)

1. **`complete`** — `DOC_SECTION.complete===false` ⇒ o concern não entra como pronto (re-roda ou marca `[TODO: scan incompleto]`). Nunca declarar a doc pronta com concern incompleto.
2. **Invalidação (o crítico)** — o agente **propõe**; o JS **aplica** só se `confidence==="high"` **E** `evidence` não-vazio **E** o `id` está no `live[]`. Invalidar é destrutivo no journal — low-confidence vira `[relatado]`, não morte.
3. **Reintegração de nuance (guarda de finding_id, v3.4)** — só `validation.status==="confirmed"` reintegra automático; `unconfirmable` → `[relatado]`; `contradicted` → `invalidate` da versão antiga. O **roteamento de escrita no journal** segue `match_to_journal.relation`: `curate_existing` → `curate` no `finding_id` casado; `new_discovered` → `adopt` **só** se o `finding_id` não estiver no `live[]`. **Nunca adopt cego** — o journal só dedup por texto exato (`finding_id = SHA1(texto_norm|raw_kind)`), então nuance reformulada com adopt cego viraria duplicata. As confirmadas viram `approved_nuances` por doc em `docs_with_nuances` (entrada da Fase D).
4. **Dedup (intra-doc + vs-prosa-nova, v3.4)** — (a) gotcha repetido em 2 concerns (match por anchor+texto) fica em 1 (patterns vence); (b) **nuance candidata com `covered_in_new===true`** (ou cujo token-chave já aparece em qualquer `body_md`) é **dropada** pra `dropped_nuances` — é o filtro determinístico que mata os ~70% de falso-positivo do garimpo (já-coberto reformulado) que a v3.2 filtrava à mão.
5. **Secret (CRITICAL) — paridade com o scrubber Python (v3.4)** — regex sobre todo `body_md` (e sobre o `merged[].body_md` da Fase D) antes de escrever; match ⇒ não escreve, devolve. **Espelha o `PROVIDER_RE` do `journal.py` (fonte única — se um mudar, alinhe o outro):** JWT `eyJ…`, AWS `AKIA…`/`ASIA…`, Google `AIza[0-9A-Za-z_-]{20,}` e `ya29\.[0-9A-Za-z_-]{20,}`, GitHub `gh[posu]_…`/`github_pat_…`, Stripe/OpenAI `sk-…`/`sk_live_`/`sk_test_`/`rk_live_`, Slack `xox[baprs]-…`, GitLab `glpat-…`, blocos PEM, connection string com senha, **e** atribuição genérica `(?i)(password|senha|passwd|pwd|secret|token|api[_-]?key|credential)\s*[:=]\s*<valor>` — onde `<valor>` precisa ser **credencial-shaped, NÃO bare `\S+`**: ≥16 chars de classe mista (letras+dígitos/símbolos) **ou** alta-entropia (Shannon ≥3.5), espelhando a Camada 4 do scrubber Python. Assim `secret = barreira` (prosa, palavra de dicionário, baixa entropia) **não** dispara, mas `secret = aB3x9Kf2pQ…` dispara. (`\S+` casava qualquer palavra → falso-positivo de prosa; o Python nunca teve isso.) É a 2ª barreira (o scrubber Python é a 1ª, roda ao persistir no journal) — não pode depender de o agente se autocensurar.
6. **Token budget / cobertura** — índice >150 linhas ⇒ comprime; área detectada (ex: docker-compose) sem seção ⇒ WARN.
7. **Auditoria grafo×doc (v3.2 — o repasse de completude)** — o grafo é premissa do Workflow (sempre disponível aqui). Cruza o grafo contra o texto gerado (todos os `body_md` + índice): **god node** ou **comunidade nomeada** (não-generic) cujo `label`/`source_file` **não aparece** em nenhuma seção ⇒ `audit_warnings += "área importante não documentada: <X>"`; **hyperedge** ≥0.85 sem menção ⇒ candidato a nota de arquitetura. É o grafo como completeness-critic — orienta no início (mapa), audita no fim. WARN não bloqueia; alimenta o relatório (ou uma 2ª leva de agente pro gap, se a casca optar).
8. **Frontmatter (v3.4)** — todo `body_md` de doc (não-inline) tem que abrir com o bloco YAML (`generated`/`project`/`scope`). `DOC_SECTION.has_frontmatter===false` (ou ausência detectada por regex `^---\n`) ⇒ o JS **injeta** o bloco determinístico (`generated`=data do run, `project`=nome do projeto, `scope`=`files_read[]`) e registra em `frontmatter_injected`. Fecha o buraco da v3.2 (7 shared docs sem frontmatter) por construção, não por o agente lembrar.
9. **Anti-regressão da Fase D (v3.5.1 — `gateMergedDocs`, JS não prompt)** — a Fase A é a **base canônica**; a Fase D (LLM) só pode **inserir** nuances, **nunca alterar fato existente**. Pra cada `MERGED_DOC`, o JS extrai os **fatos-chave** do `merged.body_md` E do `body_md` da Fase A que entrou no merge — frontmatter `generated` (data), versões (`\d+\.\d+\.\d+`), contagens/números (ex: nós do grafo) — e compara. Se o merged **baixou a data**, **regrediu uma versão**, **diminuiu/removeu um número** que a Fase A tinha, ou **trocou o frontmatter** ⇒ **rejeita o merge**: usa o `body_md` da Fase A e registra `merge_rejected[{doc_path, reason}]`. **Por que é gate, não prompt:** delegar isso à instrução do `mergePrompt` ("não copie a antiga") é o anti-padrão que a skill condena — e foi o que deixou um agente de merge regredir a `architecture.md` pra versão do backup (v3.3.0/data antiga) apesar de a Fase A ter entregue a versão certa. Gate é JS, não o agente lembrar.

## Pattern Manifest (v3.6)

Contrato mínimo que define "doc no padrão". Verificado **mecanicamente** por `python3 plugins/project-doc/lib/pattern_check.py --project-root "<root>"` — **nunca por leitura manual**. O script retorna `{in_pattern, gen_found, gen_current, violations, docs}`.

### Invariantes per-gen (a-e)

- **(a) markers v2 presentes** — `.claude/CLAUDE.md` contém `<!-- project-doc:v2 … -->` e `<!-- project-doc:v2:end -->`
- **(b) frontmatter em todos os docs** — todo `.claude/docs/*.md` abre com `---\n` (frontmatter YAML)
- **(c) journal existe** — `.claude/.project-doc/findings.jsonl` presente (doc nunca foi minerada sem journal = base não-confiável)
- **(d) doc-sig no frontmatter** — todo `.claude/docs/*.md` tem linha `doc-sig: <sig>` no frontmatter. A sig é gerada por `python3 plugins/project-doc/lib/pattern_check.py --sig <docfile>` e deve corresponder ao conteúdo atual do arquivo
- **(e) gen atual** — `gen_found == CURRENT_GEN` (atualmente `3.6`); gen ausente ou menor = motor mudou de padrão → reconstrói

### CONDITIONAL invariant — `--nested` pointers (t1d)

This invariant is **conditional on whether `--nested` was used**. Detection: check if any `apps/*/CLAUDE.md` contains the marker `nested-pointer` in its first HTML comment.

- **IF `--nested` was used** (any `apps/*/CLAUDE.md` exists with the `<!-- nested-pointer ... -->` marker): for every app that has a canonical doc in `.claude/docs/apps/{app}.md`, there MUST be an up-to-date `apps/{app}/CLAUDE.md` nested pointer whose `sig` matches `sha256(canonical_doc_body)[:8]`. A stale or missing nested pointer for any documented app = **WARN — nested pointer stale or missing for {app}** (run `/project-doc --nested` to regenerate).
- **IF `--nested` was NOT used** (no `apps/*/CLAUDE.md` with the marker exists): do NOT require nested pointers. Their absence is NOT a violation. `in_pattern` must not be set to `false` due to missing nested pointers — this would silently force a deep rebuild on every project that never opted in.

The `pattern_check.py` script MUST implement this conditional: presence of the marker in any `apps/*/CLAUDE.md` is the activation signal; without it, the check is skipped entirely.

### HARD RULE — quando bumpar o gen

**Toda mudança estrutural** (nova invariante, novo campo obrigatório no frontmatter, novo passo do Workflow que invalida docs antigas) **deve**:
1. Bumpar `CURRENT_GEN` em `plugins/project-doc/lib/pattern_check.py`
2. Bumpar `gen=X.Y` nos dois Index Templates (Standard e Monorepo) em `references/templates.md`
3. Atualizar esta seção descrevendo o que mudou

Não bumpe o gen para melhorias que não tornam docs antigas não-confiáveis (ex.: Fase D mais inteligente, novos checks de verification, melhorias de prompt).

### Assinatura determinística (`doc-sig`)

Formato: `<project>/<scope_basename>@gen=<CURRENT_GEN>#<hash8>`

- `project` — campo `project` do frontmatter, ou basename do project_root
- `scope_basename` — basename do primeiro path em `scope`, ou nome do arquivo sem extensão
- `CURRENT_GEN` — o gen vigente no momento da geração (`3.6`)
- `hash8` — primeiros 8 hex do sha256 do **body** (conteúdo após o bloco `---…---` do frontmatter)

A sig é **content-addressed** (muda quando o body muda) e **estável** (mesma para o mesmo conteúdo). Permite detectar regressão de conteúdo entre gerações. Gerada via `pattern_check.py --sig <docfile>`.

## Output Templates → `references/templates.md`

Os moldes de saída — **CLAUDE.md Index Template** (Standard + Monorepo, com o marker `gen=<CURRENT_GEN>`), **Doc File Templates** (frontmatter + architecture/database/api/deploy/infrastructure/env-vars/auth/patterns), **Thin Pointer Templates** (AGENTS.md, GEMINI.md, .cursorrules, .windsurfrules, copilot-instructions.md) e o **Monorepo Doc Layout** — vivem em **`references/templates.md`**. Leia esse arquivo ao escrever o índice (passo 9), os docs (passo 8), os ponteiros (passo 10) e ao montar o layout de monorepo.

## Update Mechanism

### CLAUDE.md

1. **No CLAUDE.md exists:** Create `.claude/CLAUDE.md` with v2 index
2. **CLAUDE.md exists with v1 markers** (`project-doc:start/end`): Run migration first (see Migration section), then write v2 index
3. **CLAUDE.md exists with v2 markers** (`project-doc:v2` / `project-doc:v2:end`): Replace content between v2 markers. Preserve:
   - All content before `<!-- project-doc:v2 -->`
   - All content after `<!-- project-doc:v2:end -->`
   - The `## Custom Rules` section content (extracted before write, reinserted)
4. **CLAUDE.md exists with no markers:** Append the v2 block at the end

**Marker de geração (`gen`) — desacoplado da `version` do plugin:** o marker de abertura grava o **`gen` do contrato de doc** que gerou o arquivo — `<!-- project-doc:v2 gen=3.6 -->`. O **`gen` corrente é `3.6`** (a release do **Pattern Manifest + assinatura determinística**: adiciona as invariantes (a-e) verificadas por `pattern_check.py`, a linha obrigatória `doc-sig:` no frontmatter de cada doc, e a checagem ativa via script em vez de leitura manual do marker). A **checagem ativa (passo 0.1)** **executa** `python3 plugins/project-doc/lib/pattern_check.py --project-root "<root>"`: `in_pattern==false` é **fora do padrão** → reconstrói via Workflow `deep` + garimpo. **`gen` ≠ `version` do plugin (de propósito):** a `version` (`plugin.json`) é a chave de **propagação** e bumpa a CADA mudança; o `gen` é o gatilho de **reconstrução** e só bumpa quando a doc antiga precisa ser refeita. Ex.: a **Fase D / merge nativo (plugin `3.4.0`)** melhorou a captura de nuances mas **não** invalidou docs `gen=3.3` (que já liam o código via grafo). Só bumpe o `gen` aqui, em `CURRENT_GEN` do `pattern_check.py`, e nos dois Index Templates (em `references/templates.md`) quando a mudança tornar a doc antiga base não-confiável.

**Assinatura determinística (`doc-sig`):** cada `.claude/docs/*.md` tem no frontmatter a linha `doc-sig: <sig>`, onde a sig = `<project>/<scope_basename>@gen=<CURRENT_GEN>#<hash8>`. `hash8` = primeiros 8 hex do sha256 do body (conteúdo após o frontmatter). Gerada por `python3 plugins/project-doc/lib/pattern_check.py --sig <docfile>`. A sig muda quando o body muda (content-addressed), mas é estável pra o mesmo conteúdo — permite detectar regressão de conteúdo entre gerações. É invariante (d) do Pattern Manifest; sua ausência é violação.

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

**Postura (v3.7 — mudou de novo):** o grafo é **documentação, obrigatório em QUALQUER invocação do project-doc** — FULL, `--deep`, incremental, `index`, `pointers`, `--rebuild`, `migrate`, `verify`, `clean`, `--solo`. Não se oferece dentro da execução: **se garante** (Passo 0 roda `graphify update --force`; ausente ⇒ erro que bloqueia). A sugestão `/graphify` sobrevive só **fora da execução** (proatividade ao navegar um projeto sem rodar o project-doc) ou pro **labeling LLM caro** (nomes bonitos de comunidade). O que muda entre modos NÃO é se o grafo roda (roda sempre), e sim se o mapa é **consumido no fan-out**: só FULL/`--deep` destilam `graph_map.py` e particionam por concern.

When the project has (or will have) a graphify knowledge graph (`graphify-out/graph.json`), `/project-doc` integrates with it in four ways:

1. **Garantir (TODO modo) + mapear (FULL/`--deep`)** — o **Passo 0** roda `graphify update . --force` (AST, sem LLM, ~segundos) quando ausente/stale, em **qualquer modo**. **Roda sempre, informa, não pergunta** (ver **Workflow Engine → Passo 0**). `graphify` ausente → **erro que bloqueia em todo modo** (o grafo é o único pré-requisito duro), não degradação — nem com `--solo` (que só desliga o Workflow, não pula o grafo). **Adicionalmente no FULL/`--deep`**, o Passo 0.0 destila o mapa via `graph_map.py`; o mapa dirige a leitura profunda (Fase A) e a auditoria de completude (gate 7).

2. **Index section** — generate the `## Knowledge Graph (graphify)` section inside the v2 markers (see `references/templates.md` → Index Templates). Generated ONLY when `graphify-out/graph.json` exists. Omit entirely otherwise. This makes "consult the graph before touching code" a durable instruction loaded every session.

3. **Anti-duplication** — if a `## Knowledge Graph` (or `## Knowledge Graph (graphify)`) section already exists OUTSIDE the v2 markers (a manual addition by a previous session), remove that manual copy and let the canonical one be generated inside the markers. Never leave two. Detect by header match; the manual one is the copy not enclosed by `<!-- project-doc:v2 -->` / `<!-- project-doc:v2:end -->`.

4. **Sugestão proativa (só FORA da execução, ou pro labeling caro)** — DENTRO de qualquer `/project-doc` o grafo já é garantido pelo Passo 0 (não há mais "rodou e ficou sem grafo / stale"), então no report final só restam dois prompts:
   - **Comunidades sem nome bonito** (criação inicial AST → "Community NNN") → o mapa já funciona (agrupa + fan-in) sem nomes; sugira o **labeling LLM opcional** via `/graphify` completo como upgrade — fora do caminho crítico, único pedaço do grafo que ainda é opt-in (custa tokens de LLM).
   - **Grafo fresco** → sem prompt, só nota "Knowledge graph: presente e atualizado" no report.
   - A oferta "esse projeto se beneficiaria de um grafo" agora vale **só fora de execução** — quando o agente navega um projeto e o project-doc NÃO está rodando (ver **When to Suggest Proactively**). Ali a regra antiga continua: sem grafo ⇒ **ALWAYS suggest, unconditionally** (sem juízo de trivialidade — ver Complexity Assessment).

**A distinção que importa:** `graphify update --force` (AST, barato, não-interativo) é o que **todo modo do project-doc roda sozinho** (Passo 0) — não custa tokens de LLM. O `/graphify` **completo** (extract LLM, labeling de comunidades) pode spawnar subagentes e custar tokens → esse continua sendo **sugestão/opt-in do usuário** (mesma postura do deploy). Rodar o AST automático ≠ rodar o LLM automático.

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
- **Auto commit+push é ESCOPADO — nunca `git add -A`** — o passo 14 stageia SÓ os artefatos de doc (`CLAUDE.md`, `.claude/docs/`, `findings.jsonl`, `ledger.json`, **`graphify-out/` se existir**, ponteiros). Varrer o working tree do repo-alvo (`-A`) é proibido — commitaria trabalho não-relacionado. Push nunca com `--force`; sem remote → pula push; falha → reporta e segue (commit local feito).

## Verification (Post-Generation Quality Check) → `references/verification.md`

O checklist de verificação pós-geração — os **20 checks** (integridade estrutural, links, órfãos, cobertura, token budget, paths, portas, env vars, serviços, **secret/scrubber**, deploy flow, relevância, staleness, monorepo, **artefatos versionados no git**, **grafo×doc**, **anti-regressão da Fase D**, **conformidade com o Pattern Manifest**, **discurso da invocação capturado (Tier 0)**), o formato de output, o Auto-Fix e quando rodar — vivem em **`references/verification.md`**. Rode esse checklist no passo 13 (e no modo `verify`). Não declare PASS sem rodar o check #18 (anti-regressão) e o #19 (`pattern_check.py`).
