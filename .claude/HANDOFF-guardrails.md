# Session Handoff — PRD
Date: 2026-06-20 03:40
Project: /Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins
Frente: guardrails (migração de hooks globais → plugin do marketplace)
Session: e48ab410-03e2-467e-8491-b62a35ecb28a
LOG (ata verbatim): /Users/pedroberaldo/PROGRAMACAO/PEDRO/pedro-plugins/.claude/ata/LOG-e48ab410-03e2-467e-8491-b62a35ecb28a.md

> Nota: este repo tem DUAS frentes paralelas. Este handoff é da frente **guardrails** (concluída).
> O `HANDOFF.md` (sem sufixo) é de outra frente — **project-doc v3** (sessão 6efd861d), com pendência própria. Não confundir.

## Resumo
Sessão **concluída**: migrou 3 dos 4 hooks "globais" do Pedro (que viviam soltos em `~/.claude/settings.json`) para um plugin novo `guardrails` no marketplace pedro-plugins, pra que repliquem entre máquinas. Plugin criado, instalado, verificado, commitado (`94514ee`) e **já na `main`** (`origin/main`). `settings.json` desta máquina limpo dos hooks antigos (backup feito). **Nada pendente** na frente guardrails — só follow-ups triviais opcionais.

## Contexto e Propósito
O Pedro pediu mover os hooks globais pra dentro do pedro-plugins e vinculá-los ao marketplace, pra conseguir replicá-los ao trocar de máquina [d1]. Hoje eles viviam em `~/.claude/settings.json` apontando pra scripts em `~/.claude/hooks/` — não viajam entre máquinas. A solução: empacotar como plugin; plugin instalado dispara hooks em qualquer projeto (mecânica já provada por `graphify-guard`/`context-guard`). Numa máquina nova, `claude plugin install guardrails@pedro-plugins && /guardrails:setup` traz tudo de volta.

Escopo definido: migrar **3 dos 4** hooks ativos. O 4º (auto-ativador do i-have-adhd) ficou de fora.

## Discussões e Decisões
Três decisões de design, todas fechadas via AskUserQuestion no início:
- **Um plugin só [a1].** Em vez de splitar por preocupação, os 3 hooks num plugin único (`guardrails`). Justificativa: 1 install replica tudo, 1 version bump por mudança, mais simples e alinhado ao objetivo de replicação.
- **adhd fica de fora [a2].** O hook que auto-ativa o i-have-adhd toda sessão lê de um path local (`/Users/pedroberaldo/PROGRAMACAO/VIU/i-have-adhd/...`) e já é plugin próprio (`i-have-adhd@i-have-adhd`). Replicá-lo é assunto à parte — continua intacto no settings.json.
- **Skill de setup [a3].** Plugin não carrega env var nem edita config global. Então uma skill `/guardrails:setup` (a) liga `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` e (b) remove os hooks antigos do settings.json pra evitar **disparo duplo** (senão lint roda 2×, scope-cop = 2 chamadas Haiku por edição).
- **Depois da implementação, autorizou rodar o setup na máquina real [a4]** (com backup), **commit + push [d2]**, e **merge na `main`** (escolheu a opção 1 — merge direto, sem PR [d5]).
- No meio, o Pedro não entendeu a estrutura de pastas do plugin [d3] nem qual decisão estava pendente [d4] — respondidos com explicação do anatomia plugin (hooks/ = automático, skills/ = manual; `plugin.json` em `.claude-plugin/`, `hooks.json` em `hooks/`) e do passo de merge.

## O Que Foi Feito
A migração inteira foi executada nesta sessão (o plano aprovado virou código + commit — `last_plan.likely_executed: true`). NÃO há nada pra reimplementar.

**Plugin criado** em `plugins/guardrails/`:
- `.claude-plugin/plugin.json` — name `guardrails`, version `1.0.0`.
- `hooks/hooks.json` — 3 hooks: `PostToolUse (Edit|Write)` → lint; `PreToolUse (Edit|Write)` → scope-cop; `PreToolUse (Agent)` → prompt inline do guarda de Agent Teams (copiado literal do settings.json).
- `hooks/lint-and-typecheck.sh` — cópia do global + fix de portabilidade (jq via `command -v`).
- `hooks/scope-cop.sh` — cópia do global + 3 fixes de portabilidade (jq/python3 via `command -v`; estado em `~/.claude/guardrails/` com `mkdir -p`; leitura guardada dos arquivos de estado).
- `skills/setup/SKILL.md` — a skill `/guardrails:setup`.

**Registro e docs:**
- `.claude-plugin/marketplace.json` — entrada `guardrails` (v1.0.0, dev-tools) + contagem 18 → 19.
- `.claude/docs/architecture.md` — guardrails no catálogo, na árvore e na lista de "Plugins com Hooks Automáticos"; contagens atualizadas.
- `.claude/CLAUDE.md` — "18 plugins" → "19".

**Verificação (E2E, não-destrutiva antes de mexer ao vivo):**
- `claude plugin validate .` passa (2 warnings PRÉ-EXISTENTES, não meus — ver Próximos Passos).
- Smoke-tests dos scripts: lint e scope-cop rodam sem crash, sem vazar stderr; estado criado em `~/.claude/guardrails/`.
- Dry-run do jq do setup numa cópia de settings.json: env ligada, 3 hooks antigos removidos, adhd preservado, JSON válido, **idempotente**.
- `claude plugin install guardrails@pedro-plugins` + `claude plugin details` → carrega "Hooks (2)" listando PostToolUse + PreToolUse (= 3 hooks, ver gotcha); cache idêntico ao source.

**Aplicado ao vivo:**
- `/guardrails:setup` rodado no `~/.claude/settings.json` real: backup em `settings.json.bak.20260620002535`, 3 hooks antigos removidos, env=1, adhd SessionStart intacto.
- Commit `94514ee` (8 arquivos, 555 inserções) — só os arquivos do guardrails; os bumps de handoff/project-doc no marketplace.json ficaram FORA do commit (são da outra frente).
- Push da branch `feat/guardrails-plugin` → depois fast-forward de `origin/main` (7fa0597 → 94514ee). Só o commit do guardrails entrou na main.
- `/reload-plugins` — 21 hooks ativos na sessão.

## Em Andamento
Nada pendente na frente guardrails. Trabalho concluído e na `main`.

## Próximos Passos
<!-- Todos triviais/opcionais. A frente guardrails está fechada. -->

### 1. Apagar a branch feat/guardrails-plugin (trivial)
Já está idêntica à `main`. Quando voltar pra `main` (depois de commitar a frente project-doc), `git branch -d feat/guardrails-plugin` e `git push origin --delete feat/guardrails-plugin`. Hoje a sessão terminou COM a branch `feat/guardrails-plugin` ainda como branch atual.

### 2. Alinhar 2 versões dessincronizadas no marketplace.json (trivial)
`claude plugin validate .` aponta: visual entry diz 1.1.2 mas plugin.json diz 1.2.0; raiox entry diz 0.1.0 mas plugin.json diz 0.2.0. São PRÉ-EXISTENTES (não do guardrails). plugin.json vence no install, então é cosmético — mas o validate fica reclamando. Editar as 2 linhas no marketplace.json quando for mexer nele.

### 3. Apagar os scripts antigos soltos em ~/.claude/hooks/ (trivial)
O setup desligou-os do settings.json mas deixou os arquivos no disco (`/Users/pedroberaldo/.claude/hooks/lint-and-typecheck.sh`, `pretooluse-scope-cop.sh`, e os `.disabled`). Já não disparam. Apagar quando quiser limpar — o `sessionstart-adhd-mode.sh` DEVE FICAR (ainda em uso).

## Findings & Gotchas
<!-- verbatim — descobertas técnicas desta sessão -->
- **Plugin instalado = hook global automático.** Uma vez instalado, o `hooks.json` do plugin dispara em QUALQUER projeto. É o mecanismo para "hook global que replica entre máquinas" — não precisa editar settings.json em cada máquina, só `claude plugin install`.
- **"Hooks (N)" conta EVENTOS, não hooks individuais.** `claude plugin details` mostrou "Hooks (2) PostToolUse, PreToolUse" para um plugin com 3 hooks (1 PostToolUse + 2 PreToolUse). O N é o número de tipos de evento. O teste real de "carregou" é N≠0 (o bug do hooks.json-na-raiz dá `Hooks (0)`).
- **Estado mutável de hook NÃO pode morar em `${CLAUDE_PLUGIN_ROOT}`.** O cache do plugin é reescrito a cada version bump → log/mode/streak seriam apagados. Vai em `~/.claude/<plugin>/` (por-máquina de propósito; log/streak não devem viajar). O scope-cop foi mudado de `~/.claude/hooks/` para `~/.claude/guardrails/` por isso.
- **`2>/dev/null` no `tr` NÃO suprime falha de abertura do redirect `<`.** Em máquina nova, `tr ... < "$MODE_FILE"` com arquivo inexistente vazava "No such file or directory" no stderr. Fix: `[ -f "$FILE" ] && ...` antes de ler. (bug real de portabilidade, corrigido)
- **jq `any(generator; condition)`: o generator roda contra o input.** `((.hooks // []) | any(.command // ""; test(...)))` quebra com "Cannot index array with string" porque `.command` é avaliado no ARRAY. Correto: `any(.[]; (.command // "") | test(...))` — `.[]` gera cada elemento, a condição inspeciona cada um. (bug corrigido no jq do setup)
- **bootstrap-third-party NÃO sincroniza settings.json.** Ele só gerencia marketplaces/plugins de terceiros via manifest.json. Não dá pra reaproveitar pra hooks globais — o caminho é empacotar como plugin (este trabalho). Já havia uma nota [d12] no HANDOFF de outra sessão prevendo exatamente isto.
- **PRD é snapshot sobrescrito MAS untracked não tem rede.** O `HANDOFF.md` da frente project-doc estava untracked — git não guardava histórico dele. Por isso este handoff foi salvo como `HANDOFF-guardrails.md` em vez de sobrescrever (decisão do Pedro: arquivo separado).

## Detalhes Técnicos
- **Anatomia do plugin:** `plugin.json` DENTRO de `.claude-plugin/`; `hooks.json` DENTRO de `hooks/` (na raiz do plugin é ignorado em silêncio — gotcha #1 do repo); cada skill é subpasta de `skills/<nome>/` e o nome da pasta vira o comando (`/guardrails:setup`).
- **Referência a scripts:** `${CLAUDE_PLUGIN_ROOT}/hooks/<script>.sh` — resolve pra onde o plugin estiver instalado.
- **scope-cop:** juiz LLM (Haiku via `claude -p`) que NEGA edição de UI que foge do plano/pedido (fail-open, circuit breaker de 3 BLOCKs, modo deny por default; `off` desliga via `~/.claude/guardrails/scope-cop.mode`). Só julga arquivos de UI; isenta docs/.claude/_archive.
- **Templates reusados:** os do `context-guard` (plugin.json, hooks.json, skills/setup/SKILL.md).
- **Backup do settings.json:** `/Users/pedroberaldo/.claude/settings.json.bak.20260620002535`.
- **Commit:** `94514ee` na `main` (origin atualizado por fast-forward de 7fa0597).

## Contexto Extra
- Pedro replica o marketplace numa máquina nova via git (`git@github.com:pedroberaldo87/pedro-plugins.git`), então o que importa pra replicação é o que está na `main` — por isso o merge foi necessário (não bastava a branch).
- Nesta máquina o pedro-plugins é marketplace de **source directory** (aponta pro próprio repo) com autoUpdate; ainda assim o cache do plugin não auto-refresca (gotcha do repo) — daí o `/reload-plugins` após sincronizar.
- Havia MUITO trabalho paralelo não-commitado no working tree (frentes handoff e project-doc): por isso o commit do guardrails foi isolado cirurgicamente (revert do marketplace.json pro HEAD, reaplicar só minhas 2 mudanças, commitar, restaurar a versão working com os bumps das outras frentes).
