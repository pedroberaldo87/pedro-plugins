---
name: doc
description: Gera o sistema modular de documentação de um projeto — CLAUDE.md leve como tabela de rotas, um .claude/docs/*.md por assunto e ponteiros finos para outras ferramentas de IA — e detecta e limpa artefato de teste velho (print, saída de runner, temporário). Use ao entrar num projeto sem CLAUDE.md, depois de mudança estrutural grande, ou quando o usuário diz "/doc", "documenta o projeto", "atualiza o claude.md", "limpa os artefatos", "arquiva protótipos".
---

# Project Doc v3 — Documentation System Generator

## Antes de tudo — a régua e os princípios (o par obrigatório)

Antes de minerar e projetar a documentação, rode o par, nesta ordem — é ele que substitui a antiga instrução em
prosa "leia a constituição e o quality-goals do projeto":

1. **A régua do projeto** — a skill `doc-load` (invoque pela Skill tool; fora dela:
   `python3 "$(bash "<plugin project-skills>/lib/resolve-plugin.sh" project-skills lib/doc_load.py)" --project-root "$PWD"`).
   Ela diz o que vale como régua HOJE — a lei com `ready`/`approved`, o acordo só com
   `approved`, o minerado como mapa — e o que está ausente, sem fingir.
2. **Os princípios genéricos** — a skill `principles`, quando instalada
   na máquina. Ausente: siga sem ela, dizendo isso no relato.

Em conflito, **a régua do projeto ganha** — princípio genérico não revoga a lei da casa.

## Overview

Generates a **documentation system** for a project, not a single file.

**v3 em uma frase:** a doc deixa de ser file-scanner cego e passa a derivar de **toda evidência que o projeto tem** — arquivos, handoffs, memória, grafo, git log e os **transcripts das sessões** — guardando tudo num journal append-only versionado, projetando só o que está vivo e verdadeiro, sem nunca vazar um secret pro git. **A estrutura de saída é idêntica à v2** (markers `project-doc:v2` preservados): mudam a FONTE (cascata de tiers — Tier 0 discurso da invocação → Tier 1 arquivos → … → Tier 5 humano; ver **Sources**) e o MOTOR (journal + projeção — ver **Collect & Project**). Quem conhece a doc v2 não vê diferença estrutural, só uma doc mais completa e auto-mantida.

The system has three layers:

1. **CLAUDE.md** — lightweight routing table (~60-100 lines). Always loaded in context. Contains: project identity, stack one-liner, quick commands, top gotchas, and a documentation index with "→ read when" hints
2. **`.claude/docs/*.md`** — detailed docs per concern (architecture, database, API, deploy, etc.). Loaded on-demand when Claude needs them for the current task
3. **Thin pointer files** — pure redirects (AGENTS.md, GEMINI.md, .cursorrules, etc.) that tell other AI tools to read CLAUDE.md

**Onde cada documento mora, e quem tem direito de escrevê-lo** (pastas, as três naturezas — autoral,
minerado, derivado —, o frontmatter e a tabela de quem escreve e quem lê) está em
`contrato-familia.md`, ao lado deste arquivo (fonte: `_shared/contrato-familia.md`). É ele que diz
por que `authored-by: human` trava a regeneração.

Sections are conditional — only generated if relevant content is detected. Small sections (≤5 lines) stay inline in CLAUDE.md instead of becoming separate doc files.

## When to Suggest Proactively

- Project has no `.claude/CLAUDE.md` → "Esse projeto não tem CLAUDE.md. Quer que eu rode o /doc pra gerar?"
- CLAUDE.md exists but major structural changes detected (new services, new deploy scripts, new database) → "O CLAUDE.md pode estar desatualizado. Quer que eu rode o /doc pra atualizar?"
- CLAUDE.md has v1 format (monolithic block with `project-doc:start/end` markers) → "O CLAUDE.md está no formato v1 (monolítico). Quer migrar pro v2 (indexado)? Roda `/doc migrate`"
- `.claude/docs/` exists but CLAUDE.md index is missing or doesn't reference it → "Tem docs em .claude/docs/ mas o CLAUDE.md não aponta pra eles. Quer que eu rode o /doc index?"
- `graphify-out/graph.json` exists but is stale (source files changed after its mtime) → "O knowledge graph (graphify-out/) pode estar desatualizado. Quer que eu rode `/graphify <path> --update`?"
- `graphify-out/graph.json` does NOT exist → **ALWAYS suggest creating one. Unconditional — no exceptions.** Do not assess triviality, coupling, file count, or whether it "would compensate"; that judgment is unreliable and is not the model's to make. Just offer; whether to run it is the user's call. → "Esse projeto se beneficiaria de um knowledge graph: mapeia relações e ajuda a localizar/debugar. Quer gerar um com `/graphify`?"
- Volume of stale test artifacts detected (loose images in root, `.playwright-mcp/`, `test-results/`, many `.DS_Store`) → "Achei {N} artefatos de teste/temporários largados ({breakdown curto, ex: 45 prints soltos, .playwright-mcp/ com 78 arquivos, 129 .DS_Store}). Quer revisar e limpar com `/doc clean`?"

## Invocation Modes

The skill accepts an optional argument to control scope:

- `/doc` — **FULL**: scan everything, generate/update all docs + index + pointers
- `/doc <doc-name>` — **INCREMENTAL**: regenerate only that doc. Valid names: `architecture`, `database`, `api`, `deploy`, `infrastructure`, `env-vars`, `auth`, `patterns`, `data-stores`, `durability`, `runtime`. For monorepos also: `{app-name}/api`, `{app-name}/database`, etc. **Os 5 docs autorais (`quality-goals`, `constraints`, `context`, `solution-strategy`, `glossary`) NÃO são nomes válidos aqui** — eles pertencem ao `/start`; pedi-los ao FULL é erro de rota (responda apontando a skill certa).
- `/doc index` — regenerate only the CLAUDE.md routing table (re-scan for new/removed docs)
- `/doc pointers` — regenerate only the thin pointer files
- `/doc migrate` — migrate v1 monolithic CLAUDE.md → v2 indexed format (see `references/migration.md`)
- `/doc verify` — run verification only, no generation
- `/doc touch` — **use a skill irmã `doc-touch`** (mesmo plugin): atualização INCREMENTAL dos docs afetados pelo diff recente, sem re-mineração. O touch consome `pattern_check --touch-plan`/`doc_lint` e NUNCA redefine invariantes desta skill.
- `/doc clean` — detect, **cluster**, and offer cleanup/archival of stale test artifacts (see `references/artifact-cleanup.md`). Nothing is removed without confirmation. Runs standalone (no doc regeneration).
- `/doc --deep` — **DEEP**: como o FULL, mas o tier 4 minera **TODAS** as sessões de transcript do projeto (cold-start / backfill do histórico de conversas), não só o delta. Pesado — rode pro primeiro mergulho completo.
- `/doc --rebuild` — **REBUILD**: descarta a doc gerada e re-projeta do **journal inteiro** (`findings.jsonl`). Idempotente; não minera nada novo — só re-deriva a doc dos findings vivos.
- `/doc --solo` — escape: força FULL/`--deep` a rodar **single-agent** (sem Workflow). É modo pesado — o grafo continua obrigatório (ver **Workflow Engine → Passo 0**). Debug / projeto pequeno.
- `/doc --nested` — **NESTED (EXPERIMENTAL)**: monorepo only. Generates `apps/{app}/CLAUDE.md` as a **derived pointer** for each app that has a canonical doc in `.claude/docs/apps/{app}.md`. Serialized after t1d (runs only after a full FULL/`--deep` that already wrote the canonical docs). See `references/nested-pointers.md`.

**Grafo — regra pesado/leve (v3.9):** modos que DOCUMENTAM (FULL, `--deep`, incremental, `--solo`, `doc-touch`) garantem o grafo fresco (`graphify update --force`; ausente ⇒ erro que bloqueia); modos leves (`clean`, `verify`, `index`, `pointers`, `migrate`, `--rebuild`) só checam staleness (mtime, barato) e avisam — nunca rodam o update. Regra completa: ver **Workflow Engine → Passo 0** (seção canônica).

**FULL e `--deep` mineram via Workflow (fan-out por concern) por padrão** — ver **Workflow Engine**. Os demais modos rodam single-agent. `--solo` desliga o Workflow.

Doc names map directly to `.claude/docs/{arg}.md`.

**Separe o flag de modo da prosa (v3.8):** o argumento que casa um modo/doc-name conhecido controla o **modo**; **todo o resto da invocação é prosa — o discurso direcionado (Tier 0)**, nunca "doc-name desconhecido → warn" (warn só pra token único parecido com doc-name). Sem flag reconhecido + prosa presente → FULL mode **com brief**. Captura/classificação: ver **Tier 0** em Sources + o passo 2 da casca.

## Nested Pointers (`--nested`, EXPERIMENTAL) → `references/nested-pointers.md`

Modo opt-in de monorepo: gera `apps/{app}/CLAUDE.md` como ponteiro derivado (nome + porta + link pro doc
canônico), serializado após o t1d. Invocação usou `--nested` → **leia `references/nested-pointers.md`**
(formato do pointer, geração da sig, staleness). O CONDITIONAL invariant do Pattern Manifest (abaixo)
continua nesta skill.

## Organismo — de-silo por costuras → `references/organism.md`

Um **organismo** é um monorepo de módulos que se integram (um `.git` com `tools/`, `mcp/`, `brain/`… que
se chamam). O risco é de **atenção**: o agente trata o módulo como ilha e ignora o blast-radius nos demais,
mesmo com a doc do todo carregada. O suporte a organismo (opt-in por um `.claude/organism.yaml` na raiz)
ataca isso com **checkpoints determinísticos**, não mais texto — princípio: **o sistema afirma a aresta, o
agente refuta com citação**. Componentes (todos já vivem no plugin — hooks + `lib/organism.py`):

- **Gate invertido** (`hooks/pretooluse-organism-gate.sh`, PreToolUse `Edit|Write|MultiEdit`): no 1º toque
  de um arquivo-ponta de costura `block`, DENY afirmando a aresta + blast-radius; **anti-loop de 1 deny por
  (costura, sessão)**; refutação por `arquivo:linha` verificada por grep; log jsonl desde o dia 1.
- **Consciência** (`hooks/sessionstart-organism.sh`, SessionStart): injeta "1 organismo, N módulos, não N
  ilhas" + regra de ouro + costuras, em qualquer cwd (sobe até o `organism.yaml`). Cobre o pertencimento
  **sem materializar routers** — torna a relocação `<módulo>/CLAUDE.md` largamente redundante.
- **2ª projeção (responsabilidade DESTA skill):** ao gerar `architecture.md`, o passo de síntese que já
  mapeia "quem chama quem" **propõe** costuras candidatas ao `organism.yaml` (com o grafo canônico marcando
  cruzamentos de fronteira de módulo). O humano cura; a skill nunca escreve `block` sozinha.
- **Não vazar pros subagentes:** ao delegar (Agent/Workflow) uma tarefa que toca costura, inclua o
  blast-radius **no prompt do subagente** — ele nunca viu a doc do organismo.
- **Conformação da DOC (Caminho C, responsabilidade DESTA skill):** o gate acima trata **atenção**;
  esta trata **drift da doc**. Cada módulo herdou uma `<módulo>/.claude/docs/` da época de repo separado
  que o FULL da raiz nunca tocava → defasava eterno e os hooks a surfaceavam como fresca. O FULL num
  organismo agora **conforma**: gera o miolo de cada módulo em `<root>/.claude/docs/modules/{m}/` (cross-
  aware), deixa um **router fino** (`{m}/.claude/CLAUDE.md`, marker `project-doc:module-router`) no módulo,
  **funde os journals** (`journal.py fuse`) e **absorve→arquiva** o legado (`_archive/`, nunca deleta). O
  **census** (`pattern_check.py --census`/`--plan`) é a régua mundo-aberto (4 classes: canonical/
  legacy-archived/pending-migration/orphan). O **gen 3.7** força o re-run global (doc `gen=3.6` fica
  fora-do-padrão); o census é o gate **organismo-específico** por cima (a invariante condicional que
  distingue pending/orphan). **Regra de "pronto": rode `--plan` (dry-run read-only) no organismo
  real e inspecione a classificação ANTES de escrever** — é o smoke E2E, não opcional.
  - **Lazy (Fase 3):** `organism.py dirty <root> <data>` = módulos sujos ∪ blast-radius das costuras; só
    esses entram no fan-out (`--deep` força todos). Propagação obrigatória — senão o lazy dá drift na costura.

Ao rodar `/doc` num projeto com `organism.yaml`, **leia `references/organism.md`** (formato do
registro, regras de curadoria, **Conformação de organismo (Caminho C)**, o teto honesto de "mitigação,
não solução"). Detecção: `python3 lib/organism.py marker <root>`. Modos read-only novos:
`pattern_check.py --census <root>` (classifica) e `--plan <root>` (dry-run da conformação).

## Output Protocol

Report each step to the user as you execute. Don't skip steps or batch them silently.

**Passo 0 — Grafo (precede todo modo, não renumerado nos protocolos abaixo):** regra pesado/leve — ver **Workflow Engine → Passo 0**. Modo pesado → reporte `Grafo → criado | atualizado | já fresco`; modo leve → reporte `Grafo → fresco | ⚠️ stale (aviso, não atualiza)`.

### Full Mode

```
**Step 1/14:** Root → `/path/to/project`
**Step 2/14:** Layout → Standard | Monorepo (N apps)
**Step 3/14:** Type → app | lib | cli
**Step 4/14:** Package manager → pnpm | yarn | bun | npm
**Step 5/14:** Mode → FULL | MIGRATE (v1→v2 detected) | CREATE (no CLAUDE.md)
**Step 6/14:** CLAUDE.md → v1 markers (will migrate) | v2 index (will update) | none (will create)
**Step 7/14:** Graph (**Passo 0 — modo pesado**) → `graphify update --force` {criado | atualizado | já fresco} + graph_map (FULL/`--deep`) → {N god nodes, M comunidades, K hyperedges} | **graphify ausente → ERRO que bloqueia (instale)**
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
**Step 4/5:** Lista clusterizada para julgamento (ver `references/artifact-cleanup.md`) — aguarda aprovação
**Step 5/5:** Aplicado → {deletados} removidos, {arquivados} → _archive/, {pulados}. Rede de segurança: _archive/{nome}-housekeeping-{data}.tar.gz
```

## Process

**Passo 0 (logo após identificar o root, antes de ramificar):** aplique a regra pesado/leve do grafo — ver **Workflow Engine → Passo 0** (canônica). A destilação do mapa (`graph_map.py`) só ocorre no FULL/`--deep` (quem consome o fan-out).

1. **Identify project root** — find nearest git repo root or use cwd
1b. **Casa da doc — detectar a casa antiga e OFERECER a migração** (F15.8): pergunte ao resolvedor onde a doc mora — `lib/casa_da_doc.py` (`casa(raiz)`) ou o irmão `hooks/lib-casa-da-doc.sh` (`casa_da_doc "$RAIZ"`), nunca caminho cravado. Se ele devolver a casa VELHA (`.claude/docs/` existe e `docs/` na raiz não), **pare e pergunte com `AskUserQuestion`** — não migre calado, e não siga calado. A pergunta leva o de-para VISÍVEL no `preview` da opção (`.claude/docs/architecture.md` → `docs/architecture.md`, e assim por diante, os arquivos reais que estão lá). Duas opções: **migrar agora** (`git mv .claude/docs docs`, e a doc deste run já nasce na casa nova) e **ficar como está** (o run segue na casa velha, e a oferta volta no próximo `/doc`). Sem resposta do dono, nada se move — a casa da doc é decisão dele, não do agente.

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
   - **Tier 0 vale em TODO modo que aceita prosa** (inclusive os single-agent): capturar → classificar → `adopt` fatos → echo-back, como na **casca passo 2** (Workflow Engine); nos single-agent não há `RUN.brief` — a direção orienta o agente único direto. Nunca descarte prosa só porque o modo é single-agent.
   - **FULL / DEEP:** rode a **checagem ativa (passo 0.1)** e minere via **Workflow** (fan-out por concern) — ver **Workflow Engine**. A checagem **executa** `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)" --project-root "<root>"` (não só lê o número do marker — roda o script): `in_pattern==false` => fora do padrão => reconstrói via Workflow `deep` + garimpo. `--solo` força single-agent.
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
    - Stale test artifacts detected: {N} ({breakdown}). Offer `/doc clean` (see `references/artifact-cleanup.md`) — detect & report only, never delete here
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
- **Tier 5 — O humano (ATIVO desde a gen 3.8):** lacuna crítica sem fonte → **pergunte**, em vez de marcar `[TODO]` e seguir. Vive **nesta skill**. Duas classes de lacuna, com destinos diferentes:
  - **Operacional** (host SSH que não está em arquivo, RPO/RTO, quando a restauração foi testada) → pergunte na **casca**, direto, e escreva a resposta no doc do concern.
  - **Autoral** (metas de qualidade, restrições, fronteiras, estratégia, glossário) → **não é seu**. Rode `/start gaps` (read-only) para listar o que falta e **ofereça `/start`** — e num projeto maduro (que é o caso de quem acabou de MINERAR), **ofereça `/start ex-post`**: o rascunho sai do que a mineração já leu, e o dono só referenda. Esses cinco documentos têm `authored-by: human` e o FULL **nunca os escreve** — ver **Documentos autorais** abaixo.

  **Onde perguntar:** na **casca**, nunca dentro do Workflow (ele roda em background e não pergunta no meio). Duas janelas: **(1) antes de disparar o fan-out**, quando a lacuna já é previsível — `durability.md` vai precisar de **RPO/RTO/última restauração testada**, e `runtime.md` precisa da **escolha dos 3-7 cenários** (minere os candidatos do grafo, apresente a lista e deixe o humano escolher ANTES do fan-out; o agente da Fase A não pode perguntar, então sem isso ele escolhe sozinho e o doc sai não-curado); **(2) depois do `STITCH_RESULT`**, quando os `todos[]` dos agentes revelaram a lacuna. Agrupe as perguntas em UMA rodada por janela; não pingue o humano concern a concern.

Tiers 2-4 são **mecânicos** e vivem em `lib/journal.py` do plugin `project-doc` (degrada gracioso: sem a engine vendorada, pula o tier 4 e usa tiers 1-3). Tier 0, tier 1 e tier 5 são desta skill (captura/julgamento). O fluxo completo (coleta → projeção) está em **Collect & Project**.

## Tier 1 — Detection Matrix (scan de arquivos) → `references/detection-matrix.md`

O mapa completo do scan Tier 1 — Pre-Detection (project type, package manager, knowledge graph, test
framework, Complexity Assessment do grafo), o mapeamento detecção→doc (architecture/database/api/deploy/
infrastructure/env-vars/auth/patterns/inline) e a varredura por-app de monorepo (mandatória, sem
carry-forward) — vive em **`references/detection-matrix.md`**. **Leia esse arquivo** ao executar o scan
(passo 6), ao particionar o fan-out por concern (casca passo 5) e ao escanear apps de monorepo. Regra do
grafo (pesado/leve): ver **Workflow Engine → Passo 0**.

## Documentos autorais — território do `/start` (gen 3.8)

Cinco documentos **não são mineráveis** porque a informação não está em arquivo nenhum: as metas de
qualidade, as restrições, o contexto/fronteiras, a estratégia e o glossário. Eles pertencem à skill
irmã **`/start`** (mesmo plugin), que os produz por **entrevista**.

**A trava é o frontmatter `authored-by: human`.** Doc que a carrega:

- **NUNCA entra no fan-out por concern** — não há agente escrevendo `quality-goals.md`.
- **NUNCA é sobrescrito, regenerado nem "melhorado"** pelo FULL, pelo `--rebuild` ou pelo `doc-touch`.
- **PODE (e deve) ser lido e citado** — as metas são o critério que a projeção usa para decidir o que
  é gotcha crítico e o que é detalhe; as restrições explicam decisões que pareceriam erradas.
- **Escrita automática permitida, só esta:** atualizar `reviewed:` e promover `status: draft → ready`
  quando o último `[PENDENTE]` sai do corpo.
- **Doc `draft` fica FORA do índice** do CLAUDE.md — vira linha de cobrança no relatório final.
  Sem isso, cinco arquivos quase vazios entram no arquivo que carrega em toda sessão.

**Por que a proibição é dura:** documentação de intenção fabricada por máquina é ficção com aparência
de autoridade — pior que arquivo ausente, porque ninguém desconfia de um documento que parece
completo. Inferir uma meta de qualidade a partir do código é exatamente isso.

O banco de perguntas, os moldes e os critérios de pronto vivem em
`../start/references/authorial-kit.md` — **fonte única**, consumida pelas duas skills. Não
duplique aqui.

## Collect & Project (v3 — o motor)

A v3 separa **coleta** (mecânica, código) de **projeção** (julgamento, você). Nunca pule a projeção — o lib não decide relevância nem reconcilia; isso é seu.

### Collect (rode o lib)

Roda a parte mecânica — minera tiers 2-4, passa pelo **scrubber** (barreira de secret), dá append no journal append-only e devolve os findings **vivos**:

```bash
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/journal.py)" update  --project-root "<root>" [--session "$CLAUDE_CODE_SESSION_ID"]
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
- **Curadoria:** se o usuário editar à mão um finding gerado, registre pra sobreviver à re-projeção:
  `python3 .../journal.py curate --project-root "<root>" --id <id> --text "..."` (a projeção respeita o texto curado).

A doc canônica é **derivada e descartável** (`--rebuild` re-cria do journal). O journal é a verdade; a doc é a vista. Critério de aceite: a doc cita ≥1 gotcha/decisão que só existe em sessão/handoff, e **nenhum** gotcha que o código atual contradiz.

## Workflow Engine — FULL e --deep mineram via Workflow (v3.1) + grafo dirige a leitura profunda (v3.2) + merge nativo de nuances (v3.4)

**O problema que isso resolve:** numa janela única, sob volume de contexto, o agente "tira o pé" — corta o Tier 1 scan (não lê o código de verdade) e a Reconciliação (confere 5 de 30 `stale_ids`). A COLETA (Python) é determinística e não tira o pé; quem tira é a **projeção** quando feita numa janela só. A solução: nos modos que mineram, a projeção roda como um **Workflow** com **fan-out por concern** — cada agente recebe uma fatia (um doc-alvo), tem working-set pequeno, e não tem medo do volume. A soma cobre tudo.

### Fronteira de modos — quando é Workflow, quando é single-agent

| Modo | Motor | Por quê |
|---|---|---|
| **FULL** (`/doc`) e **`--deep`** | **Workflow** (fan-out) | mineram fontes novas + projetam tudo → é onde o medo de contexto bate |
| incremental (`/doc <doc>`), `index`, `pointers`, `--rebuild`, `migrate`, `verify`, `clean` | **single-agent** (como antes) | não mineram / 1 concern só / re-projeção pura → nada a paralelizar |

- `--rebuild` re-projeta do journal **sem minerar** → single-agent, sem backup, sem garimpo.
- Flag de escape **`--solo`**: força FULL/--deep a rodar single-agent (debug/projeto pequeno). Sem `--solo`, FULL/--deep **disparam o Workflow direto** — não anuncie custo nem peça confirmação.

### Passo 0 — Grafo (SEÇÃO CANÔNICA — regra pesado/leve, v3.9) + Passo 0.0 — mapa pro fan-out (FULL/`--deep`)

**Premissa (v3.7):** nenhuma versão do project-doc jamais leu o código-fonte de verdade — o Tier 1 sempre foi uma allowlist (manifestos/configs/schemas/rotas) + `ls`. A única coisa que mapeia o codebase inteiro é o **grafo (graphify)**. Quem DOCUMENTA precisa do grafo fresco; quem só verifica/limpa/reindexa não consome o grafo — e não deve pagar o update dele (v3.9).

**A regra pesado/leve (v3.9):**
- **Modos PESADOS** — FULL, `--deep`, incremental (`<doc-name>`), `--solo`, **`doc-touch`** (skill irmã — escreve doc, logo garante o grafo; único deles que NÃO consome o `graph_map`, e por isso avisa-e-segue se `graphify` não estiver instalado em vez de bloquear): o grafo é **obrigatório e garantido**. Detecta staleness (graph.json ausente, ou mtime < `git log --format=%aI -1`) e roda:
  ```bash
  graphify update "<root>" --force    # `update`: re-extrai por AST, ZERO LLM, ~segundos, não-interativo, idempotente
                                       # `--force`: sobrescreve graph.json mesmo se a re-extração tiver MENOS nós (após refactor que apaga código)
  ```
  Ausente → cria (AST); stale → atualiza; fresco → no-op. `graphify` **não instalado ⇒ erro que bloqueia** (não degrada, não pula — nem com `--solo`, que só desliga o Workflow). **Não anuncie custo nem peça confirmação** — informa "grafo: criado / atualizado / já fresco" no Output Protocol. O labeling LLM de comunidades é upgrade opcional via `/graphify` completo, fora do caminho crítico; `update --force` preserva labels existentes.
- **Modos LEVES** — `clean`, `verify`, `index`, `pointers`, `migrate`, `--rebuild` (nenhum consome o grafo): **só staleness-check barato** — compara o mtime de `graphify-out/graph.json` contra `git log --format=%aI -1` e **AVISA** se o grafo está stale/ausente ("grafo stale/ausente — o próximo FULL atualiza, ou rode `graphify update`"). **Nunca roda `graphify update`, nunca bloqueia** — nem por graphify ausente. A doc de verdade continua nunca saindo de grafo velho: quem escreve doc é modo pesado.

**Passo 0.0 (SÓ FULL/`--deep` — destila o mapa pro fan-out):** o grafo bruto tem milhares de nós — não engula inline. Só os modos com Workflow consomem o mapa, então só eles destilam:
```bash
python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/graph_map.py)" --project-root "<root>"
```
Devolve JSON: `{available, stats, files[], god_nodes[], communities[], generic_communities[], hyperedges[]}` (ver **Schemas / GRAPH_MAP**). Como o Passo 0 já garantiu o grafo, `available:false` aqui é anomalia (graphify falhou após o `update`) ⇒ **ERRO** — não há fan-out sem mapa. O mapa alimenta o particionamento (passo 5) e a leitura profunda (Fase A).



Antes de minerar, **execute** `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)" --project-root "<root>"` e **classifique a doc existente** com base no resultado (esta é a checagem ativa — roda no passo 0 da casca, **não é leitura manual do marker**):

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
   `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/journal.py)" adopt --project-root "<root>" --text "<fato>" --raw-kind user_directive`
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
7. **Escreve os arquivos** — e **aplica o gate 11 aqui**: antes de cada `Write`, se o arquivo de destino já existe e tem `authored-by: human` no frontmatter, **pule** e registre em `authorial_skipped[]` (o JS do Stitch não tem filesystem; este é o único ponto do fluxo que tem). Feito isso, escreve o `body_md` **mergeado da Fase D que passou no gate anti-regressão** (gate 9) pros docs que ganharam nuance; merge **rejeitado** ⇒ escreve o `body_md` da **Fase A** daquele doc (preserva a correção, perde só a costura); os demais saem da Fase A. A prosa já está materializada aqui — o journal (passo 6) é registro fiel, não a fonte da escrita.
7b. **Gate doc-lint (v3.11, determinístico — check #23):** após escrever os arquivos, `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/doc_lint.py)" --project-root "<root>" --json`. `fails>0` → a casca corrige cada FAIL com a evidência que o próprio lint dá (o token + a verdade do repo) e re-roda — **máx 2 iterações**; persistiu → reporta FAIL no relatório (nunca silencia). Falso-positivo legítimo (var construída dinamicamente, config de infra externa) → `<!-- lint:ignore TOKEN -->` no doc ou `.claude/.project-doc/lint-allow.txt`, com justificativa.
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
  writingRules: '<BLOCO_REGRAS_DE_ESCRITA_ASSERTIVA_VERBATIM>',  // v3.11: as 7 regras anti-drift (Rules → "Regras de escrita assertiva"), anexadas por scanReconcilePrompt/mergePrompt a toda Fase A/D.
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
const stitched = stitchAndGate(sections, nuances, RUN.graphMap)  // adjudica invalidação, dedup-vs-prosa, frontmatter, secret, budget + AUDITORIA grafo×doc + COBERTURA ativo×durabilidade (gate 10); devolve docsWithNuances[]
// GATE 11 (autoral intocado) NÃO cabe aqui — precisa ler o frontmatter do arquivo NO DISCO, e este
// orquestrador não tem filesystem. Ele roda na casca, no passo 7, antes de cada Write.

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

**Composição Tier 0 × Fase B (v3.8):** Tier 0 + journal = garantia PRIMÁRIA (o fato da invocação é
`adopt`-ado ANTES da coleta, entra no `live[]` desta rodada, viaja versionado). Fase B = rede SECUNDÁRIA
cross-run (preserva o que só vivia na doc antiga) — ela **não** cobre o discurso da invocação na primeira
vez (esse só existe no chat; quem o captura é o Tier 0). O Tier 0 põe o discurso DENTRO da doc/journal; a
Fase B protege o que já está documentado.

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

10. **Cobertura ativo×durabilidade (gen 3.8 — o gate que resolve o caso do backup)** — cruze o
    `body_md` de `data-stores.md` contra o de `durability.md`. **Todo depósito enumerado no
    inventário precisa de um bloco correspondente na durabilidade** — inclusive os sem cobertura, que
    aparecem com justificativa explícita. Ativo sem bloco ⇒ `audit_warnings += "ativo sem linha de
    durabilidade: <X>"` **e** o `durability.md` ganha um bloco `[TODO: sem cobertura declarada]` —
    nunca silêncio. **É gate, não instrução de prompt**, porque os dois concerns rodam em agentes
    paralelos que não se veem: o casamento só pode acontecer no Stitch. **Condição de skip (precisa):**
    os **dois** ausentes (projeto sem dado persistente) ⇒ o gate não roda, e não é violação.
    `data-stores.md` presente **sem** `durability.md` **NÃO é skip** — é exatamente o caso que motivou
    a gen 3.8: gere o `durability.md` com um bloco `[TODO: sem cobertura declarada]` por ativo e
    registre em `audit_warnings`. (`durability.md` sem `data-stores.md` é incoerência: marque WARN.)

**Gate 11 — na CASCA, não no Stitch** (o orquestrador JS não tem filesystem — ver o gotcha do molde):

11. **Doc autoral intocado (gen 3.8) — roda no passo 7 da casca, imediatamente antes de cada `Write`.**
    Se o arquivo de destino **já existe no disco** e seu frontmatter contém `authored-by: human`,
    **não escreva** — registre em `authorial_skipped[]` e siga. Vale mesmo que algum agente tenha
    devolvido um `body_md` para ele. **Por que na casca e não no Stitch:** o `stitchAndGate` é JS puro
    sem acesso a disco, então não tem como consultar o frontmatter do arquivo existente; posto lá, o
    gate simplesmente não nasceria — é a mesma classe de falha que motivou o gate 9. É a rede
    determinística contra o modelo "ajudar" preenchendo intenção. Ver **Documentos autorais**.

## Pattern Manifest (v3.8)

Contrato mínimo que define "doc no padrão". Verificado **mecanicamente** por `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)" --project-root "<root>"` — **nunca por leitura manual**. O script retorna `{in_pattern, gen_found, gen_current, violations, docs}`.

### Invariantes per-gen (a-e)

- **(a) markers v2 presentes** — `.claude/CLAUDE.md` contém `<!-- project-doc:v2 … -->` e `<!-- project-doc:v2:end -->`
- **(b) frontmatter em todos os docs** — todo `.claude/docs/*.md` abre com `---\n` (frontmatter YAML)
- **(c) journal existe** — `.claude/.project-doc/findings.jsonl` presente (doc nunca foi minerada sem journal = base não-confiável)
- **(d) doc-sig no frontmatter** — todo `.claude/docs/*.md` tem linha `doc-sig: <sig>` no frontmatter. A sig é gerada por `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)" --sig <docfile>` e deve corresponder ao conteúdo atual do arquivo
- **(e) gen atual** — `gen_found == CURRENT_GEN` (atualmente `3.8`); gen ausente ou menor = motor mudou de padrão → reconstrói

### CONDITIONAL invariant — `--nested` pointers (t1d)

This invariant is **conditional on whether `--nested` was used**. Detection: check if any `apps/*/CLAUDE.md` contains the marker `nested-pointer` in its first HTML comment.

- **IF `--nested` was used** (any `apps/*/CLAUDE.md` exists with the `<!-- nested-pointer ... -->` marker): for every app that has a canonical doc in `.claude/docs/apps/{app}.md`, there MUST be an up-to-date `apps/{app}/CLAUDE.md` nested pointer whose `sig` matches `sha256(canonical_doc_body)[:8]`. A stale or missing nested pointer for any documented app = **WARN — nested pointer stale or missing for {app}** (run `/doc --nested` to regenerate).
- **IF `--nested` was NOT used** (no `apps/*/CLAUDE.md` with the marker exists): do NOT require nested pointers. Their absence is NOT a violation. `in_pattern` must not be set to `false` due to missing nested pointers — this would silently force a deep rebuild on every project that never opted in.

The `pattern_check.py` script MUST implement this conditional: presence of the marker in any `apps/*/CLAUDE.md` is the activation signal; without it, the check is skipped entirely.

### CONDITIONAL invariant — conformação de organismo (Caminho C)

**Condicional à presença de `.claude/organism.yaml`.** Mesma lógica do nested-pointer: só vale quando o
projeto opta (tem `organism.yaml`); sem ele, **não** é violação e **não** afeta `in_pattern` (não força
deep-rebuild em projeto avulso). Verificado por `pattern_check.py --census <root>` (não pelo
`--project-root` padrão, que é escopado à raiz). Regras (ver `references/organism.md` → **Conformação de
organismo** e `references/verification.md` checks #21-22):

- **`pending-migration > 0`** (doc de módulo listado sem contraparte em `modules/{m}/`) → estado esperado
  ANTES da 1ª conformação (reporta, não falha); APÓS uma conformação → **FAIL** (o módulo não foi conformado).
- **`orphan > 0`** → **WARN** (report + oferece arquivar; hard-fail só em `--strict` ou colisão direta com o
  output do run).
- **Complementa o gen 3.7 (não substitui):** o bump 3.6→3.7 força o re-run de TODO projeto (gen mismatch);
  este census é o gate **organismo-específico** que, dentro desse re-run, distingue o que migrar (pending) do
  que arquivar (orphan). Projeto avulso: só o gen 3.7 (re-roda FULL normal, sem census).

### HARD RULE — quando bumpar o gen

**Toda mudança estrutural** (nova invariante, novo campo obrigatório no frontmatter, novo passo do Workflow que invalida docs antigas) **deve**:
1. Bumpar `CURRENT_GEN` em `lib/pattern_check.py` do plugin `project-doc`
2. Bumpar `gen=X.Y` nos dois Index Templates (Standard e Monorepo) em `references/templates.md`
3. Bumpar `gen=X.Y` no **Module Router Template** (`references/templates.md`, seção Organism) e no
   **nested-pointer** (`references/nested-pointers.md`) — são o 3º e 4º lugares com gen literal. A
   lista antiga parava no item 2 e por isso o `nested-pointers.md` ficou carimbando `gen=3.7` depois
   do bump pra 3.8 (achado da revisão de 2026-07-26). **Régua mecânica, use-a:**
   `grep -rn "gen=3\." plugins/project-skills/skills/` — nenhum literal da gen anterior pode sobrar.
4. Atualizar esta seção descrevendo o que mudou
5. **Reescrever o marker do PRÓPRIO repo** se ele tiver doc project-doc (`.claude/CLAUDE.md`) —
   senão o bump deixa este projeto `in_pattern==false` e todo hook do plugin passa a gritar "fora do
   padrão" até um FULL rodar. Mesmo achado.

Não bumpe o gen para melhorias que não tornam docs antigas não-confiáveis (ex.: Fase D mais inteligente, novos checks de verification, melhorias de prompt).

### Assinatura determinística (`doc-sig`)

Formato: `<project>/<scope_basename>@gen=<CURRENT_GEN>#<hash8>`

- `project` — campo `project` do frontmatter, ou basename do project_root
- `scope_basename` — basename do primeiro path em `scope`, ou nome do arquivo sem extensão
- `CURRENT_GEN` — o gen vigente no momento da geração (`3.8`)
- `hash8` — primeiros 8 hex do sha256 do **body** (conteúdo após o bloco `---…---` do frontmatter)

A sig é **content-addressed** (muda quando o body muda) e **estável** (mesma para o mesmo conteúdo). Permite detectar regressão de conteúdo entre gerações. Gerada via `pattern_check.py --sig <docfile>`.

## Output Templates → `references/templates.md`

Os moldes de saída — **CLAUDE.md Index Template** (Standard + Monorepo, com o marker `gen=<CURRENT_GEN>`), **Doc File Templates** (frontmatter + architecture/database/api/deploy/infrastructure/env-vars/auth/patterns), **Thin Pointer Templates** (AGENTS.md, GEMINI.md, .cursorrules, .windsurfrules, copilot-instructions.md) e o **Monorepo Doc Layout** — vivem em **`references/templates.md`**. Leia esse arquivo ao escrever o índice (passo 9), os docs (passo 8), os ponteiros (passo 10) e ao montar o layout de monorepo.

## Update Mechanism

### CLAUDE.md

1. **No CLAUDE.md exists:** Create `.claude/CLAUDE.md` with v2 index
2. **CLAUDE.md exists with v1 markers** (`project-doc:start/end`): Run migration first (see `references/migration.md`), then write v2 index
3. **CLAUDE.md exists with v2 markers** (`project-doc:v2` / `project-doc:v2:end`): Replace content between v2 markers. Preserve:
   - All content before `<!-- project-doc:v2 -->`
   - All content after `<!-- project-doc:v2:end -->`
   - The `## Custom Rules` section content (extracted before write, reinserted)
4. **CLAUDE.md exists with the `start-doc:index` markers** (índice mínimo provisório do `/start`): **substitua o bloco inteiro** — do `<!-- start-doc:index -->` ao `<!-- start-doc:index:end -->`, markers inclusive — pelo bloco `project-doc:v2`. Ele é provisório por contrato: a mineração é quem produz o índice definitivo, e deixar os dois lado a lado dá duas tabelas de roteamento no mesmo arquivo. Preserve tudo antes e depois do bloco.
5. **CLAUDE.md exists with no markers:** Append the v2 block at the end

**Marker de geração (`gen`) — desacoplado da `version` do plugin:** o marker de abertura grava o **`gen` do contrato de doc** que gerou o arquivo — `<!-- project-doc:v2 gen=3.8 -->`. O **`gen` corrente é `3.8`** — a release do **kit canônico**: três concerns minerados novos (`data-stores`, `durability`, `runtime`), a chave `verified-by` no frontmatter, os rótulos de procedência `[confirmado]`/`[inferido]`/`[relatado]` na prosa, os cinco documentos **autorais** com a trava `authored-by: human` (produzidos pela skill irmã `/start`), o log de decisões promovido à raiz do projeto, e os gates 10 (cobertura ativo×durabilidade) e 11 (autoral intocado). **Doc `gen=3.7` é base não-confiável** porque lhe faltam gavetas inteiras — não porque o que ela diz esteja errado; por isso o re-run é global. O `3.7` foi a release da **conformação de organismo — Caminho C**: a árvore canônica única na raiz com `modules/{m}/`, o router fino de módulo com marker `project-doc:module-router`, o census mundo-aberto de 4 classes, o scope-staleness ternário e a fusão de journal. Docs de organismo `gen=3.6` viram não-conformantes → reconstrução via conformação; projeto avulso re-roda o FULL normal. O `3.6` foi a release do **Pattern Manifest + assinatura determinística**: invariantes (a-e) verificadas por `pattern_check.py`, a linha obrigatória `doc-sig:` no frontmatter, e a checagem ativa via script em vez de leitura manual do marker). A **checagem ativa (passo 0.1)** **executa** `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)" --project-root "<root>"`: `in_pattern==false` é **fora do padrão** → reconstrói via Workflow `deep` + garimpo. **`gen` ≠ `version` do plugin (de propósito):** a `version` (`plugin.json`) é a chave de **propagação** e bumpa a CADA mudança; o `gen` é o gatilho de **reconstrução** e só bumpa quando a doc antiga precisa ser refeita. Ex.: a **Fase D / merge nativo (plugin `3.4.0`)** melhorou a captura de nuances mas **não** invalidou docs `gen=3.3` (que já liam o código via grafo). Só bumpe o `gen` aqui, em `CURRENT_GEN` do `pattern_check.py`, e nos dois Index Templates (em `references/templates.md`) quando a mudança tornar a doc antiga base não-confiável.

**Assinatura determinística (`doc-sig`):** cada `.claude/docs/*.md` tem no frontmatter a linha `doc-sig: <sig>`, onde a sig = `<project>/<scope_basename>@gen=<CURRENT_GEN>#<hash8>`. `hash8` = primeiros 8 hex do sha256 do body (conteúdo após o frontmatter). Gerada por `python3 "$(bash "${CLAUDE_PLUGIN_ROOT}/lib/resolve-plugin.sh" project-skills lib/pattern_check.py)" --sig <docfile>`. A sig muda quando o body muda (content-addressed), mas é estável pra o mesmo conteúdo — permite detectar regressão de conteúdo entre gerações. É invariante (d) do Pattern Manifest; sua ausência é violação.

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

**Postura (v3.9):** grafo é documentação — **garantido nos modos pesados, staleness-check + aviso nos leves** (regra canônica: **Workflow Engine → Passo 0**). Dentro da execução não se oferece: modo pesado garante, modo leve avisa. A sugestão `/graphify` sobrevive só **fora da execução** ou pro **labeling LLM caro** (nomes bonitos de comunidade).

When the project has (or will have) a graphify knowledge graph (`graphify-out/graph.json`), `/doc` integrates with it in four ways:

1. **Garantir (modos pesados) + mapear (FULL/`--deep`)** — ver **Workflow Engine → Passo 0**. No FULL/`--deep`, o Passo 0.0 destila o mapa via `graph_map.py`; o mapa dirige a leitura profunda (Fase A) e a auditoria de completude (gate 7).

2. **Index section** — generate the `## Knowledge Graph (graphify)` section inside the v2 markers (see `references/templates.md` → Index Templates). Generated ONLY when `graphify-out/graph.json` exists. Omit entirely otherwise. This makes "consult the graph before touching code" a durable instruction loaded every session.

3. **Anti-duplication** — if a `## Knowledge Graph` (or `## Knowledge Graph (graphify)`) section already exists OUTSIDE the v2 markers (a manual addition by a previous session), remove that manual copy and let the canonical one be generated inside the markers. Never leave two. Detect by header match; the manual one is the copy not enclosed by `<!-- project-doc:v2 -->` / `<!-- project-doc:v2:end -->`.

4. **Sugestão proativa (só FORA da execução, ou pro labeling caro)** — no report final só restam dois prompts:
   - **Comunidades sem nome bonito** (criação inicial AST → "Community NNN") → sugira o **labeling LLM opcional** via `/graphify` completo como upgrade — fora do caminho crítico, único pedaço do grafo que ainda é opt-in (custa tokens de LLM).
   - **Grafo fresco** → sem prompt, só nota "Knowledge graph: presente e atualizado" no report.
   - A oferta "esse projeto se beneficiaria de um grafo" vale **só fora de execução** (ver **When to Suggest Proactively**): sem grafo ⇒ **ALWAYS suggest, unconditionally** (sem juízo de trivialidade — ver Complexity Assessment).

**A distinção que importa:** `graphify update --force` (AST, barato, não-interativo) é o que os modos pesados rodam sozinhos — não custa tokens de LLM. O `/graphify` **completo** (extract LLM, labeling de comunidades) pode spawnar subagentes e custar tokens → esse continua sendo **sugestão/opt-in do usuário**. Rodar o AST automático ≠ rodar o LLM automático.

## Migration v1 → v2 → `references/migration.md`

Disparada quando markers v1 são detectados ou o usuário roda `/doc migrate`. Reorganização
estrutural, não refresh de conteúdo (não re-escaneia o projeto). Modo migrate ativo → **leia
`references/migration.md`** (passos, mapeamento seção→doc, variante monorepo).

## Artifact Cleanup → `references/artifact-cleanup.md`

Higiene de artefatos de teste/scratch. A **detecção roda em todo FULL** e só reporta; remoção/arquivamento
só em `/doc clean`, após aprovação da lista clusterizada. Modo clean ativo (ou ao reportar
artefatos no FULL) → **leia `references/artifact-cleanup.md`** (detecção, classificação 🗑️/📦/🚩/✋,
sensibilidade, arquivo, formato do report, protocolo de confirmação). As regras duras de segurança do
cleanup continuam na seção **Rules** desta skill.

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

### Regras de escrita assertiva — anti-drift (v3.11; injetadas em TODO agente escritor via `RUN.writingRules`)

Destiladas da auditoria de 2026-07-22 (34 erros / 1.509 claims): 68% do drift era destas classes. A casca copia este bloco verbatim pra `RUN.writingRules`; `scanReconcilePrompt`/`mergePrompt` o anexam ao prompt de toda Fase A/D. O `doc_lint.py` (check #23) é a rede determinística pros casos mecanizáveis.

1. **Nunca contagem derivada de lista** ("17 scopes") — escreva a lista, ou derive o número mecanicamente NO run (`grep -c`/`ls | wc -l`), ou use ordem de grandeza ("~18").
2. **Nome de env var/header/flag só por cópia literal** de arquivo em `files_read[]` — nunca de memória. Não leu o arquivo que a lê → não cita o nome.
3. **Lista nunca se declara completa** ("todos", "lista completa") salvo gerada mecanicamente no run; senão "inclui / entre eles".
4. **Ponteiro = arquivo + símbolo** (função/const/seção), nunca nº de linha solto; hash de commit só copiado do `git log` do run.
5. **Feature "ativa" exige evidência de ativação** (wiring/registro/env setada), não existência de código — senão escreva "implementado, gated/inativo".
6. **Generalização ("sempre", "todo X") só com verificação mecânica**; senão qualifique ("nos casos verificados").
7. **Costura citada existe nos DOIS lados hoje** — verifique o outro módulo; decomissionado = remover a menção (é evento cross-doc), nunca mantê-la.

### Desacoplamento — duas trocas obrigatórias em TODO doc escrito (SEÇÃO CANÔNICA)

Vale para `CLAUDE.md`, todo `.claude/docs/*.md` e todo ponteiro — no FULL, no incremental e no `/doc-touch`, que aponta para cá em vez de repetir a regra. Doc que crava o retrato de hoje envelhece em silêncio: ninguém revalida a frase ao acrescentar um arquivo.

1. **Contagem cravada sai; entra o COMANDO que a produz.** Nunca escreva o número sozinho ("os N plugins", "as N suítes"). Escreva o comando ao lado — `grep -c '^## ' .claude/docs/runtime.md`, `ls plugins | wc -l`, `python3 scripts/<script>.py` — e o número só entra **colado ao comando que o devolveu**, nunca solto. Número com procedência não envelhece: quem lê refaz a medição. Sem comando à mão, use ordem de grandeza ("~20") ou escreva a lista.
2. **Lista de nomes de plugin sai; entra o ÍNDICE que os enumera.** Nunca enumere em prosa quais plugins existem, nem com quais uma skill conversa — o retrato só quem escreveu sabe atualizar, e plugin novo o deixa errado sem avisar. Aponte o índice que já existe: `.claude-plugin/marketplace.json` para o que é distribuído, `plugins/bootstrap/config/manifest.json` <!-- acopla-ok: o manifest é citado como ÍNDICE a consultar, não como dependência executável --> para o que a máquina instala, `hooks/hooks.json` para o que escuta evento.

**Quem cobra:** `python3 scripts/desacoplamento_check.py` — ele varre os arquivos rastreados e reprova as duas formas (mais o irmão por posição). **Isenção:** quando a contagem ou a lista é o próprio assunto da frase, escreva `acopla-ok: <motivo>` na linha, com o motivo explícito — mesmo molde do `public-ok`. A lei está em `.claude/docs/constituicao.md`, Artigo 9.

### Regras gerais

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

O checklist de verificação pós-geração — os **26 checks** <!-- acopla-ok: a lista dos 26 vem enumerada na própria frase, e a fonte canônica é references/verification.md --> (integridade estrutural, links, órfãos, cobertura, token budget, paths, portas, env vars, serviços, **secret/scrubber**, deploy flow, relevância, staleness, monorepo, **artefatos versionados no git**, **grafo×doc**, **anti-regressão da Fase D**, **conformidade com o Pattern Manifest**, **discurso da invocação capturado (Tier 0)**, census de organismo, scope-staleness, doc-lint, **cobertura ativo×durabilidade**, **autorais intocados**, **procedência**), o formato de output, o Auto-Fix e quando rodar — vivem em **`references/verification.md`**. Rode esse checklist no passo 13 (e no modo `verify`). Não declare PASS sem rodar o check #18 (anti-regressão), o #19 (`pattern_check.py`), o **#24** (todo depósito de dado tem linha de durabilidade) e o **#25** (nenhum doc autoral foi sobrescrito).

## Log de decisões e declarações → `references/adr.md`

O molde do ADR, a regra de escopo (**decisão que cruza módulos mora na RAIZ — na dúvida, raiz**), a
detecção mecânica de candidatos (mudança estrutural no git sem ADR no intervalo) e a superfície
`declarations/` vivem em **`references/adr.md`**. Leia-o ao gerar `.claude/docs/decisions/`.

**Duas travas:** (1) esta skill **detecta** candidatos e **nunca escreve** a decisão — contexto e
motivo são do humano, e ADR inventado é o mesmo pecado do autoral fabricado; (2) `declarations/` só
é gerado em projeto que **tem verificador executável** — sem leitor, é documento que ninguém abre, e
o próprio kit proíbe criar documento sem leitor.
