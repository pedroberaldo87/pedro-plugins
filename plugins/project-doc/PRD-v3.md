# PRD — project-doc v3

**Status:** rascunho para validação · **Autor:** Claude + Pedro · **Data:** 2026-06-19
**Versão alvo:** project-doc 3.0.0 · handoff 1.7.0 · `_shared/` (novo)

---

## 1. Contexto

### 1.1 O que o project-doc é hoje (v2.2.1)
Skill de 1056 linhas, 100% prosa, zero código. Gera um sistema de documentação em 3 camadas: `CLAUDE.md` (índice ~60-100 linhas, sempre carregado), `.claude/docs/*.md` (detalhe por concern, on-demand) e thin pointers (`AGENTS.md`, `GEMINI.md`, `.cursorrules`). A coleta inteira vive na **Detection Matrix** (SKILL.md linhas 137-242): uma lista de arquivos a escanear por doc-alvo.

### 1.2 A lacuna — a fonte
A Detection Matrix lê **exclusivamente arquivos do disco**. Consequências mensuráveis:
- **Decisões de arquitetura** (linha 190) só entram se já estiverem escritas em `docs/ARCHITECTURE.md`, `docs/ADR*`, `docs/decisions/` ou no README. Decisão tomada em conversa e nunca escrita → invisível.
- **Gotchas** (linha 216) são *inferidos* de config não-padrão (`network_mode:host`, etc.). Conhecimento tácito de debugging → invisível.
- **git log** é usado só para *data* de staleness, nunca para extrair o "porquê" das mudanças.
- **Não toca**: contexto da sessão atual, transcripts (`~/.claude/projects/<slug>/*.jsonl`), `.claude/HANDOFF*.md`, `memory/*.md`, mensagens de commit.

**Caso canônico:** o gotcha *"hook de plugin vai em `hooks/hooks.json`, NUNCA na raiz"* nasceu de uma sessão de debugging em jun/2026. O project-doc só o documenta porque foi escrito à mão no CLAUDE.md — ele não o descobriria sozinho.

### 1.3 Escala real (VIUSTUDIO-TOOLS, caso de referência)
**303 sessões de transcript, ~270 MB**, espalhadas em **11 slugs** de `~/.claude/projects/` (um por CWD de trabalho). Já versiona 52 arquivos em `.claude/` (5 HANDOFFs, atas `LOG-*.md` + `manifest-*.json`, `SESSION_DECISIONS.md`). Zero secret-valor vaza nos docs gerados hoje (guard de secret v2 funciona).

---

## 2. Objetivo, usuários e métricas

### 2.1 Objetivo
Que o project-doc documente a partir de **toda evidência que o projeto tem** — não só arquivos — guardando tudo sem perda, mantendo a doc canônica enxuta e verdadeira, e sem nunca vazar um secret para o git.

### 2.2 Usuários
- **Primário: agentes** (Claude, GPT-5.x, etc.) que consomem a doc para trabalhar. → a doc é **agent-facing**: o critério de utilidade é "isto me ajuda a programar/operar", não "um humano leria isto".
- **Secundário: Pedro**, que raramente lê a doc direto, mas precisa que o agente opere (deploy, SSH) sem ele relembrar credenciais.

### 2.3 Métricas de sucesso
- A doc gerada cita ≥1 gotcha/decisão que **só** existe em conversa/handoff, não em arquivo (cobertura de fonte).
- Zero secret-valor no git em qualquer rodada (segurança).
- Uma rodada de atualização incremental não re-minera sessão já consumida (eficiência do delta).
- Clonar o repo noutra máquina preserva o conhecimento (portabilidade).

---

## 3. Requisitos funcionais

### RF1 — Coleta multi-fonte em cascata de 5 tiers
A fase de detecção passa de "ler arquivo" para uma cascata ordenada por densidade/custo. Cada tier alimenta os mesmos campos-alvo dos templates atuais (`## Decisões de Arquitetura`, `## Gotchas`, etc.).

| Tier | Fonte | O que extrai | Custo |
|---|---|---|---|
| 1 | Arquivos (Detection Matrix atual) | stack, deps, rotas, schema, config | baixo |
| 2 | `.claude/HANDOFF*.md`, `memory/*.md`, `graphify-out/`, `.claude/ata/manifest-*.json`+`LOG-*.md` | decisões/gotchas já destilados; god nodes→arquitetura, comunidades→módulos | baixo |
| 3 | `git log` (mensagens) | o "porquê" das mudanças | baixo |
| 4 | Transcripts `.jsonl` minerados, todos os slugs sob o project_root | direcionamentos, rejeições, decisões que nunca viraram arquivo | alto |
| 5 | O humano | lacuna crítica sem fonte (ex: host SSH inexistente em arquivo) → **pergunta**, em vez de marcar `[TODO]` | — |

**Critério de aceite:** rodar no `pedro-plugins` e a doc captura ≥1 gotcha/decisão presente só em sessão/handoff.

### RF2 — Journal de evidência (store append-only)
Arquivo **`.claude/.project-doc/findings.jsonl`**, versionado no git, append-only ("super git" do conhecimento). Cada linha é **um evento**:

- `discovered` — `{id, raw_kind, text, anchors:[paths], source:{type,ref,ts}, scrubbed:bool}`
  - `raw_kind ∈ {user_directive, tool_rejection, ask_answer, commit, handoff, memory}`
  - `id` estável = `hash(anchor_of(text) + raw_kind)` (reusa `anchor_of`, 64 chars normalizados)
- `invalidated` — `{target:id, reason, ts}` — **não apaga** o `discovered`
- `curated` — `{target:id, text, ts}` — edição humana; a projeção a respeita

O estado de um finding = *fold* dos eventos sobre seu `id` (vivo se o último evento não é `invalidated`/`superseded`).

**Critério de aceite:** rodar 2×; o journal só cresce; um finding invalidado mantém seu `discovered` original recuperável.

### RF3 — Projeção (doc canônica derivada)
A doc canônica (`CLAUDE.md` + `.claude/docs/`) é **derivada** do fold do journal (findings vivos) + scan tier 1. Não é fonte de verdade — é descartável e re-derivável.

**Estrutura de saída idêntica à v2:** índice `CLAUDE.md` (~60-100 linhas) + `.claude/docs/*.md` por concern + thin pointers (`AGENTS.md`, `GEMINI.md`, `.cursorrules`), com layout monorepo quando aplicável. A v3 troca a **fonte** (journal multi-fonte) e o **motor** (projeção), **não o formato** — quem conhece a doc v2 não vê diferença estrutural, só uma doc mais completa e auto-mantida.

- **Mapeamento kind→seção:** gotcha → `patterns.md`/Gotchas (+ top 3-5 no CLAUDE.md); decisão → `architecture.md`/Decisões; feature → Visão Geral; convenção → `patterns.md`.
- **Relevância:** filtra candidatos doc-worthy (os `gate=True` da engine são primários); o `kind` semântico é atribuído **na projeção** (julgamento do agente), não no journal.
- **Reconciliação:** todo finding histórico é confirmado contra o **código atual** antes de entrar. Vale → entra; não dá pra confirmar → marca `[relatado]`; código contradiz → não entra (gera `invalidated`).
- **Preserva** `## Custom Rules` e todo conteúdo fora dos markers `<!-- project-doc:v2 -->`.

**Critério de aceite:** a doc não contém nenhum gotcha que o código atual contradiz.

### RF4 — Atualização incremental (delta de 2 direções)
Ledger **`.claude/.project-doc/ledger.json`** versionado: `{mined_sessions:[uuid], last_commit:sha, distilled_hashes:{file:hash}}`.

- **Forward:** sessões novas (`glob *.jsonl` − `mined_sessions`) + commits novos (`last_commit..HEAD`) → minerados → eventos `discovered`. A **sessão ativa** é sempre re-minerada (cresce).
- **Backward:** `git diff last_commit..HEAD --name-only` → findings cujas `anchors` batem nesses paths → re-validados; mortos viram `invalidated`. Cirúrgico — não re-valida o journal inteiro.

**Critério de aceite:** 2ª rodada sem mudança = delta vazio (nada re-minerado); commit que altera a regra X → o gotcha de X é invalidado e some da doc.

### RF5 — Scrubber + Cofre Operacional
**Scrubber** roda na escrita do journal (barreira crítica, já que o journal vai pro git):
- **Detecta:** `KEY=valor` não-placeholder, base64 longo, JWT (`eyJ…`), `AKIA…`, `-----BEGIN…`, connection strings com senha embutida.
- **Política "nomes e contexto sim, valores não":** preserva nome de var, host, porta, path; redige só o valor-secreto. Hosts/IPs internos: **preserva** (contexto de infra). Na dúvida: **preserva e marca** `‹revisar?›`.

**Cofre:** o valor-secreto não é descartado — é **desviado**. Vai para `iCloud Drive/Cofre/<projeto>.env`; o repo tem `.claude/secrets/ops.env` (symlink gitignored) → cofre; a doc referencia (`SSH_HOST → ver cofre`).

**Critério de aceite:** input mock com `SSH_HOST=1.2.3.4` e `DB_PASSWORD=x` → zero valor no git; valores no cofre; doc referencia. Reaproveita o guard de secret existente (verification check #10) na doc final.

### RF6 — Engine de extração compartilhada (vendoring)
**`_shared/`** (source-only, **não** é plugin instalável) nasce de `plugins/handoff/lib/extract_ata.py` — que já tem o **schema do `.jsonl` verificado em dados reais** (o ativo caro, não-duplicável).

- **Reusa:** `collect()`, `read_jsonl`, `discover_transcript`, `resolve_project_root`, `detect_modules`, `infer_scope`, `collect_edited_paths`, `anchor_of`. Descarta `build()` (formatação de ata, fica no handoff).
- **Adiciona:** (a) varredura **multi-slug** por project_root (a engine atual é mono-sessão); (b) modo **`--emit-findings`** (candidatos crus em JSON).
- **`scripts/sync-shared.sh`** vendora `_shared/` para dentro de cada plugin consumidor antes do commit (o "build" do monorepo). Source DRY, plugins autônomos no runtime.
- **Degradação graciosa:** sem o handoff instalado, o project-doc pula o tier 4 (mineração crua) e usa tiers 1-3.

**Justificativa técnica (confirmada na doc oficial):** o Claude Code isola plugins na instalação — só `plugins/<nome>/` vai pro cache, sem variável cross-plugin. Compartilhar código em runtime é inviável; vendoring é o caminho.

**Critério de aceite:** `sync-shared.sh` deixa as cópias idênticas; `claude plugin validate` passa; o handoff SAVE continua funcionando; o project-doc emite findings reais no `pedro-plugins`.

### RF7 — Modos de invocação
- `/project-doc` — **delta** (forward+backward) + projeta. Padrão.
- `/project-doc --deep` — minera **todas** as sessões cruas (cold-start / backfill do tier 4).
- `/project-doc --rebuild` — descarta a doc e re-projeta do **journal inteiro** (idempotente).
- `incremental` / `index` / `migrate` / `verify` / `clean` — **inalterados**.

### RF8 — Doc-first guard (hook que força a doc antes da exploração)
Documentação só rende se for **consultada**. Um hook do project-doc garante que a doc canônica seja levada em conta antes de exploração cega — fecha o ciclo "gerar → usar". Modelo direto e já testado do `graphify-guard`, em 2 camadas:

- **SessionStart** (`sessionstart-doc.sh`): se o projeto tem `.claude/CLAUDE.md`, injeta um heads-up no contexto, listando os docs disponíveis (`.claude/docs/*.md`) e instruindo a consultar o relevante **antes** de grep/Explore.
- **PreToolUse** (`pretooluse-doc-guard.sh`, matcher `Grep|Glob|Bash`): quando uma busca cega vai rodar num projeto com `.claude/docs/`, **nega uma vez por sessão** e redireciona para o doc relevante. Fail-open (qualquer erro → deixa passar); o "once-per-session" evita virar nag; cobre o caso monorepo-container (inspeciona os paths da busca, como o graphify-guard já faz).
- **Convive com o `graphify-guard`** — grafo e doc são fontes complementares; cada guard intercepta e redireciona para a sua, no máximo um bloqueio por fonte por sessão.
- **Localização:** `plugins/project-doc/hooks/hooks.json` (subpasta `hooks/` — gotcha conhecido do projeto: na raiz o Claude ignora silenciosamente).

**Critério de aceite:** num projeto com doc, o 1º grep cego da sessão é bloqueado com redirect para `.claude/docs/`; buscas seguintes passam. Num projeto sem doc, o guard nunca dispara.

---

## 4. Requisitos não-funcionais

- **Performance:** a rodada padrão processa só o delta; o custo de minerar 270 MB fica isolado em `--deep`. A extração é Python/regex (rápida); o caro é a síntese, que opera sobre findings já reconciliados.
- **Segurança:** o scrubber é a barreira entre conversa-verbatim e git; defense-in-depth com o check #10 na doc final. Repo privado **não** é controle de secret — não-capturar (scrubber) + não-emitir (check #10).
- **Portabilidade:** transcripts são locais por máquina e não viajam; o `findings.jsonl` versionado é o **único veículo** do conhecimento entre máquinas/clones. O ledger versionado permite que cada máquina minere só suas sessões locais e some no git.
- **Compatibilidade:** v2 intacto — templates de doc, layout monorepo, migração v1→v2, artifact cleanup, os 15 checks de verification, `## Custom Rules`. O handoff inteiro (SAVE/RESUME/gate) preservado; só a camada de extração migra para `_shared/`.

---

## 5. Fora de escopo (desta entrega)

- **Cold-start das 303 sessões do tools** — a estratégia de atacar o primeiro mergulho dos 270 MB fica para quando Pedro rodar.
- **Trigger automático** — o project-doc continua rodando sob comando; integração com o fim de sessão / `/handoff` fica para depois.
- **Deploy** — a implementação para antes de subir; `sync-shared.sh`, commit, `plugin tag` e atualização dos plugins ficam com Pedro.

---

## 6. Critérios de aceite end-to-end

1. **Cobertura de fonte:** rodar no `pedro-plugins` → a doc cita um gotcha que só existe em sessão/handoff.
2. **Multi-slug:** apontar para o project_root do tools → a engine varre os 11 slugs (303 sessões).
3. **Segurança:** secret mock → zero valor no git; valor no cofre; referência na doc.
4. **Reconciliação:** a doc não tem gotcha que o código atual contradiz.
5. **Delta idempotente:** 2ª rodada sem mudança → nada re-minerado.
6. **Backward:** commit que contradiz um gotcha → `invalidated` no journal, some da doc, `discovered` original preservado.
7. **Vendoring:** cópias idênticas pós-sync; `plugin validate` passa; handoff funciona.
8. **Doc-first guard:** num projeto com doc, o 1º grep cego da sessão é bloqueado e redirecionado para `.claude/docs/`; buscas seguintes passam; projeto sem doc nunca dispara.

---

## 7. Riscos e questões abertas

- **Cold-start (270 MB):** minerar 303 sessões na 1ª rodada é pesado. Estratégia (paralelizar? funil de relevância? backfill em background?) — **a decidir**.
- **Ruído da mineração:** transcripts verbatim trazem candidatos irrelevantes. Mitigação = reconciliação + filtro de relevância na projeção; mas o limiar exato ("o que vira finding") é uma questão aberta.
- **Custo da síntese no `--rebuild`** de um journal grande (muitos findings vivos) — pode precisar de cache/snapshot futuro.
- **Curadoria humana vs re-projeção:** edição manual na parte gerada precisa virar evento `curated` para sobreviver; o mecanismo exato de captura está esboçado, não fechado.

---

## 8. Plano de versionamento

| Artefato | De → Para | Natureza |
|---|---|---|
| `plugins/project-doc` | 2.2.1 → **3.0.0** | mudança maior (nova arquitetura) |
| `plugins/handoff` | 1.6.0 → **1.7.0** | passa a vendorar de `_shared/` |
| `_shared/` | — → novo | source-only, fora do `marketplace.json` |
| `scripts/sync-shared.sh` | — → novo | build do monorepo |
