---
name: fallow
description: Roda o Fallow (analisador estático JS/TS — código morto, duplicação, complexidade) num projeto, classifica os achados por tipo e nível de confiança, e entrega um relatório interativo (HTML com checkboxes) onde Pedro escolhe o que limpar. Depois limpa só o marcado com rede de segurança (preview → aplica → build/test). Trigger em "/fallow", "roda o fallow", "varre código morto", "analisa o projeto com fallow", "o que dá pra limpar aqui".
---

# /fallow — varredura e limpeza guiada

Roda o Fallow, transforma a saída crua num **relatório que Pedro escaneia e seleciona**, e limpa só o que ele marcar — nunca às cegas.

## Input

`/fallow [projeto]`

- `[projeto]` = path absoluto, nome de pasta, ou vazio (usa o cwd).
- Se Pedro disser só "FINANCE" / "TOOLS" / "tools", resolver para o path real (ex: `/Users/pedroberaldo/PROGRAMACAO/VIU/VIUSTUDIO-FINANCE`).

## O que você precisa saber sobre o Fallow (não pule — evita cagada)

- É **análise estática sintática** (parser Oxc, **sem type-check**). Constrói um grafo de imports/exports e marca como "morto" o que não é alcançável a partir dos **entry points**.
- **`dead-code` depende 100% dos entry points.** Entry não detectado → tudo abaixo vira falso "morto". **`dupes` e `health` NÃO dependem de entry → sempre confiáveis.**
- **`fallow fix` é conservador**: só remove a keyword `export`, deps do `package.json` e membros de enum. **NUNCA deleta arquivo.** Deleção de arquivo órfão é a skill que faz, sempre com build/test depois.
- Falsos-positivos sistemáticos conhecidos (já mapeados — devem estar silenciados no `.fallowrc.json`, mas confira):
  - **Client Vite** (`apps/*/client`): o `index.html` não vira entry → resolver com `entry: ["apps/*/client/src/main.{jsx,tsx,js,ts}"]`.
  - **shadcn/ui** (`components/ui/*`): re-exportam a API Radix completa de propósito → `ignoreExports: [{file, exports:["*"]}]`.
  - **Service workers / assets** (`public/sw.js`, `static/*.css`): registrados em runtime, nunca importados. **Não** silenciar via `ignorePatterns public/**` — isso cria órfãos colaterais; deixar aparecer e marcar como asset no relatório.
  - **DI/decorators, `import()` dinâmico, `next/dynamic`**: podem mascarar uso → item vira "verificar", não "deletar".

## Fluxo

### 1. Pré-check da config (BLOQUEANTE para dead-code)

- Checar se existe `<projeto>/.fallowrc.json` (ou `.fallowrc.jsonc`/`fallow.toml`). Rodar `npx -y fallow config -r <projeto>` e ver se carrega.
- **Se NÃO houver config**: avisar Pedro que o relatório de **código morto** virá com falsos-positivos (entry points / bibliotecas), e oferecer calibrar primeiro (ver "Calibrar config" abaixo). Duplicação e complexidade seguem confiáveis mesmo sem config.
- **Se houver**: seguir.

### 2. Rodar e parsear JSON REAL

Rodar e capturar JSON (nunca parsear texto, nunca assumir formato):

```bash
npx -y fallow dead-code -r <projeto> --format json
npx -y fallow dupes     -r <projeto> --format json
npx -y fallow health    -r <projeto> --format json
```

Chaves reais dos JSON (confirmadas rodando — **não chutar**):
- **`dead-code`**: `unused_files`, `unused_exports`, `unused_types`, `unused_dependencies`, `unused_dev_dependencies`, `unused_enum_members`, `unused_class_members`, `circular_dependencies`, `re_export_cycles`, `unlisted_dependencies`, `boundary_violations`. Cada item tem `path`/`file` e, em exports, `exports`/`name`.
- **`health`**: a lista é `targets` (não "refactoring_targets"), item = `{path, priority, efficiency, recommendation, category, effort, confidence, factors, evidence, actions}`. Também: `health_score`, `vital_signs`, `hotspots`, `large_functions`, `file_scores`.
- **`dupes`**: `clone_groups` (item = `{instances, token_count, line_count, fingerprint, suggested_name, actions}`) e `clone_families` (item = `{files, groups, total_duplicated_lines, total_duplicated_tokens, suggestions, actions}`) + `stats`.

### Os dois motores (lib/) — não reimplementar à mão

A skill tem motores prontos e testados. O caminho normal é **rodá-los**, não recriar a lógica:

- **`lib/report.py <projeto> [session]`** — roda os 3 fallow + a auditoria, classifica, e gera o HTML interativo em `~/Desktop/claude-visual/`. Imprime o path + um resumo JSON dos baldes.
- **`lib/audit.py <projeto> [--json]`** — auditoria isolada (o `report.py` já a chama internamente). Útil pra rodar/inspecionar só a auditoria.

Antes de abrir o HTML: rodar `plugins/visual/server/start.sh` (live-sync). Depois `open` o arquivo.

### 3. Auditoria — o goal (confirmar cada afirmação do Fallow)

O Fallow é estático: **afirma** "órfão" mas não enxerga cron/systemd, rota HTTP, `import()` dinâmico nem uso via `package.json`. `audit.py` re-verifica cada `unused_file` com **evidência real** e classifica:

- **`falso_positivo`** (🛑 não deletar) — achou uso real. Razão + prova (ex: `deploy/README.md` rodando o script via systemd). Inclui **propagação de vivacidade**: um FP-raiz (ex: script de cron) é entry vivo → o que ele importa e o Fallow marcou como morto também é vivo.

  **Enquadramento (comunicar ao usuário em humano):** um falso-positivo **não é bug do código nem código morto** — é uma **limitação intrínseca da análise estática**. O Fallow lê só o grafo de imports (quem chama quem no código) e não enxerga gatilhos de fora: agendador do SO (cron/systemd), requisição HTTP (rota), import dinâmico. O código está correto; não há o que corrigir nele. Por padrão a skill **mantém os FPs visíveis** no relatório (não suprime via `entry`) — é escolha consciente, dá transparência. Suprimir é opção cosmética do usuário, não correção.
- **`dead_confirmado`** (✓ seguro) — 0 referências em import estático, dinâmico, símbolo, cron/rota.
- **`manual_cli`** (⚠ arquivar) — script sem refs e não agendado, mas é ferramenta CLI manual.

**Goal de convergência (não-negociável):** a auditoria roda repetidamente; cada rodada que descobre um buraco novo (FP que rodadas anteriores não pegaram) reinicia a contagem. **Converge só quando 3 rodadas consecutivas dão fingerprint idêntico.** Convergência prova determinismo — **não prova correção**: matches frouxos (substring de path, basename solto, símbolo genérico como `POST`/`GET`) geram falso-positivo de auditoria. Por isso os matches são **ancorados** (path com boundary, nome+extensão, infra de execução ≠ menção em doc de planejamento). Ao evoluir o `audit.py`, sempre re-validar contra uma auditoria manual de referência.

### 3b. Classificar os demais baldes

- 🧟 **Código morto** — arquivos usam o veredito da auditoria acima; `unused_exports`/`unused_types` usam heurística (`export_name`, `is_type_only`, `line`).
- 📦 **Dependências não usadas** — `unused_dependencies`. Quick-win seguro (auto-fixable). Excluir as típicas-FP se aparecerem (`@types/*`, `eslint`, `typescript`, `tsx`, test runners, `autoprefixer`/`@tailwindcss/postcss`).
- 🔁 **Ciclos** — `circular_dependencies` + `re_export_cycles`. Não deletável; é refactor.
- 👯 **Duplicação** — `clone_families` ordenadas por `total_duplicated_lines` (maiores primeiro). Refactor manual (extrair módulo via `suggestions`), nunca auto-fix.
- 🧠 **Complexidade** — `targets` ordenados por `priority` (e `efficiency` = ROI); destacar `effort: "low"` como quick wins. Usar `recommendation` (texto humano) e `evidence` (dados acionáveis).

### 4. Apresentar (relatório interativo)

Gerar um HTML **dark-theme self-contained** em `~/Desktop/claude-visual/YYYY-MM-DD-fallow-<projeto>.html` (reaproveitar o CSS e o daemon de live-sync da skill `visual` — `plugins/visual/server/start.sh` + `window.VISUAL_SESSION`). Estrutura:

- **Topo**: saúde (health score) + contadores por balde + **card da auditoria** (goal): "convergiu em N rodadas idênticas" e os 3 números (🛑 falsos-positivos · ✓ órfãos reais · ⚠ scripts manuais).
- **Seções colapsáveis por balde.** Cada item = checkbox + path + tag de confiança (`✓ confirmado` verde / `🛑 não deletar` vermelho / `⚠ verificar` amarelo) + **mini-resumo humano sempre visível**. Ao expandir: bloco **⛔ Problema** (humano + técnico) e bloco **✅ Solução** (humano + técnico, com a ação e a prova da auditoria).
- Botões: **"Marcar só os seguros"** (só `confirmado` + deps — nunca `fp`/`verificar`), **"Limpar"**, **"Copiar seleção"** (+ live sync).
- Abrir com `open`. Pedro marca o que quer eliminar e diz "ok"/"pronto" (live sync) ou cola a seleção.

Se o volume for pequeno (≤ ~8 itens acionáveis), pode usar a skill `visual` direto. Para listas grandes (dezenas de itens), gerar o relatório de lista com checkboxes.

### 5. Limpar só o marcado (ordem de risco crescente)

**Antes de qualquer escrita:** garantir git limpo ou `git stash`/commit do estado atual (a skill avisa e faz). Trabalhar num branch se o projeto estiver no default.

1. **Deps não usadas** → `npx fallow fix -r <projeto> --dry-run` (preview) → mostrar o diff → `npx fallow fix -r <projeto> --yes` (escopo deps).
2. **Exports 100% dead** → para cada um, `npx fallow dead-code -r <projeto> --trace <file>:<export>` confirma 0 referências → `fallow fix`.
3. **Arquivos órfãos** → confirmar via `--trace`/grep + olhar `git log` do arquivo; deletar; rodar build/test **do app afetado**.
4. **Duplicação / complexidade** → refactor manual dos maiores; nunca auto.

**Após cada lote**: rodar build + test do projeto (ou do app no monorepo). Comandos:
- FINANCE (pnpm): `pnpm build` / `pnpm test` / `pnpm lint`.
- TOOLS (monorepo, por app): `cd apps/<app> && npm run lint && npx tsc --noEmit` (ver `.claude/docs/patterns.md`).
- Se o build/test quebrar: **reverter o lote** (`git checkout`/`git stash pop`) e reportar o que quebrou. Parar.

### 6. Relatório final

Resumir em linguagem humana (1-2 linhas por balde): o que foi removido, o que passou no build/test, o que ficou pendente (itens `verificar` não tocados), e quanto caiu cada métrica. Oferecer commit.

## Calibrar config (quando o projeto não tem `.fallowrc.json`)

Criar `<projeto>/.fallowrc.json` (schema real — campos válidos: `entry`, `ignorePatterns`, `workspaces.patterns`, `ignoreExports`, `ignoreDependencies`, `dynamicallyLoaded`, `ignoreDecorators`, `usedClassMembers`, `duplicates`). Padrões que valem:
- Apps Vite com client aninhado → `entry: ["apps/*/client/src/main.jsx", ...]` (o `index.html` **não** é target válido de `entry`; `workspaces.patterns: ["apps/*/client"]` **não** funciona quando o pai já é workspace).
- Express server aninhado não detectado → `entry: ["apps/*/server/index.js"]`.
- shadcn/ui → `ignoreExports: [{"file": "src/components/ui/*.tsx", "exports": ["*"]}]`.
- Código gerado → `ignorePatterns: ["prisma/migrations/**", "apps/**/.next/**", "apps/**/dist/**", "**/*.d.ts"]`.
- **NÃO** ignorar `public/**` nem `static/**` em massa — cria órfãos colaterais (testado). Deixar assets aparecerem e marcar no relatório.

**Loop de calibração (obrigatório):** depois de escrever a config, rodar `fallow dead-code --format json` e medir o delta por categoria (script de bucket: agrupar `unused_files` por `/client/`, `/components/`, `/lib/`, etc.). Confirmar que o ruído sistemático sumiu (ex: bucket Vite → 0) **sem** o total subir por efeito colateral. Iterar até todo finding ser acionável.

## Regras de ouro (não-negociáveis)

- Nunca declarar um finding "código morto" sem o entry point estar resolvido — verifique a config primeiro.
- Nunca deletar item `verificar` sem `--trace` + grep confirmando 0 referências.
- `fallow fix` toca só export/deps/enum; deleção de arquivo é a skill, sempre com build/test depois.
- Sempre commit/stash antes; sempre build/test depois de cada lote; reverter se quebrar.
- Apresentar problemas em linguagem humana (1-2 linhas), técnico no colapsável.
