---
generated: 2026-06-20
project: pedro-plugins
scope:
  - .claude-plugin/marketplace.json
  - plugins/*/.claude-plugin/plugin.json
  - plugins/*/hooks/hooks.json
  - plugins/*/hooks/*.sh
  - plugins/*/skills/*/SKILL.md
  - plugins/project-doc/lib/journal.py
---

# Patterns & Conventions

Convenções reais extraídas do código deste marketplace (17 plugins). Tudo aqui foi
verificado lendo o arquivo-fonte na sessão de geração desta doc.

## Code Style

### Shell (hooks `.sh`)
- **Shebang misto, sem regra única:** os scripts de `context-guard`, `guardrails`,
  `project-doc`, `ship`, `visual`, `graphify-guard` usam `#!/bin/bash`; os de
  `bootstrap` e `handoff` usam `#!/usr/bin/env bash`. Não há lint forçando um padrão.
- **Fail-open é a lei dos hooks.** Toda dependência externa é resolvida via PATH e,
  se faltar, o hook sai com `exit 0` (deixa a ação passar) — NUNCA bloqueia por
  causa de ferramenta ausente. Padrão canônico (8 scripts usam):
  ```bash
  command -v jq >/dev/null 2>&1 || exit 0
  ```
  `guardrails/hooks/scope-cop.sh:16-19` exige `jq` E `python3`; sem qualquer um → `exit 0`.
- **Binários resolvidos via PATH, nunca hardcoded.** `scope-cop.sh` resolve
  `CLAUDE_BIN="$(command -v claude)"` e, se não achar, faz fail-open — não amarra a
  máquina/app específico. Comentário explícito: "Sem path hardcoded de app específico".
- **Estado mutável vive em `~/.claude/...` (por-máquina), fora do cache do plugin.**
  `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão, então logs/flags/streak
  não podem morar lá. Ex.: `scope-cop` grava em `~/.claude/guardrails/`,
  `context-guard` em `/tmp/claude-context-pct` e `/tmp/claude-context-warned-<session>`.
- **Sentinela por sessão (× projeto).** Hooks que devem avisar só 1x usam um arquivo
  em `/tmp` chaveado por `session_id` (e por `cksum` do path do projeto em
  `pretooluse-doc-guard.sh:92-93`). Padrão: `SESSION=$(... jq -r '.session_id')`.
- **Re-entrância:** `session-sync.sh:20-23` usa env var-guard
  (`PEDRO_PLUGINS_HOOK_RUNNING`) pra evitar recursão quando um hook dispara outro.
- **Lock atômico portável:** `session-sync.sh:53-64` usa `mkdir` (não `flock`) +
  `trap ... EXIT` pra lock POSIX-portável; quebra lock obsoleto (>5min).
- **Veredito do juiz LLM lido por regex de JSON**, nunca parse ingênuo: `scope-cop.sh:302-314`
  varre `{...}` no output do `claude -p` e valida `verdict in (pass|block)`; ilegível → fail-open.
- **`2>/dev/null` num redirect de ENTRADA NÃO suprime falha de abertura.** Em `cmd < "$FILE" 2>/dev/null`
  o `2>` cobre só o stderr do comando, não a abertura do `<` pelo shell. Guarde com `[ -f "$FILE" ]`
  antes de ler (padrão defendido em `scope-cop.sh:49,74`).
- **Comentários em pt-BR explicando o "porquê"** (não o "o quê") são a norma; cada
  decisão não-óbvia tem 1-3 linhas de justificativa inline.

### Hooks LLM ("juiz") — invocação do modelo
- Hooks que precisam de julgamento chamam o modelo barato via CLI:
  ```bash
  claude -p --model haiku --system-prompt "$JUDGE_SYS" \
    --exclude-dynamic-system-prompt-sections "$JUDGE_INPUT" </dev/null
  ```
  (`scope-cop.sh:293`). O `guardrails/hooks/hooks.json` Agent-guard usa `type: "prompt"`
  (julgamento inline pelo próprio Claude Code, sem subprocesso).
- O system-prompt do juiz começa SEMPRE com "Você é um classificador automático
  (NÃO um assistente)" e restringe a saída a um JSON único — evita o modelo "conversar".

### Python (`plugins/project-doc/lib/`)
- `#!/usr/bin/env python3`; stdlib pura (argparse, hashlib, json, re, subprocess) —
  **zero dependências externas** (journal.py:32-39).
- **Degradação graciosa de import:** `journal.py:43-58` tenta importar `collect_engine`
  e, no `ImportError`, define fallbacks locais — `finding_id`/`anchor_of` DEVEM ficar
  idênticos à engine (hash do texto normalizado + kind), senão re-chaveia o journal.
- Docstring de módulo descreve o CLI inteiro (subcomandos) e as fontes coletadas.
- `sys.path.insert(0, os.path.dirname(...))` pra importar siblings vendorados.

## Anatomia de um Plugin

Layout canônico (ex.: `plugins/project-doc/`):
```
plugins/<nome>/
├── .claude-plugin/
│   └── plugin.json          # manifesto: name, version, description, author{}, homepage
├── hooks/                   # OPCIONAL — só se o plugin tiver hooks
│   ├── hooks.json           # ⚠️ SEMPRE aqui (subpasta), NUNCA na raiz do plugin
│   ├── *.sh                 # scripts referenciados via ${CLAUDE_PLUGIN_ROOT}/hooks/...
│   └── lib/                 # OPCIONAL — libs compartilhadas entre hooks (ex.: bootstrap)
├── skills/                  # OPCIONAL — uma pasta por skill
│   └── <skill>/SKILL.md     # frontmatter YAML (name, description) + corpo
└── lib/                     # OPCIONAL — código de apoio (ex.: project-doc/lib/*.py)
```
- **Manifesto:** todos os 17 `plugin.json` usam `author` como **objeto** `{name, email}`
  (verificado: 17/17 `type=object`). String em `author` bloqueia install silenciosamente.
- **Skill `setup` para o que o plugin não consegue fazer sozinho.** Plugins que dependem
  de env var ou de mexer no `settings.json` global trazem `skills/setup/SKILL.md`
  (`bootstrap`, `context-guard`, `guardrails`). Plugin **não carrega env var** — daí o
  setup. Nome da skill = `<plugin>:setup` no frontmatter.
- **Plugin hooks-only existe:** `graphify-guard` não tem pasta `skills/` (só `hooks/`).
- **Referência a script em hooks.json:** SEMPRE `${CLAUDE_PLUGIN_ROOT}/hooks/<script>.sh`
  (8/8 hooks.json usam essa variável). `timeout` é opcional (em segundos).
- **Schema do `hooks.json`:** `{ "hooks": { "<Evento>": [ { "matcher": "<tool|regex>", "hooks":
  [ { "type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/x.sh", "timeout": <s> } ] } ] } }`.
  Eventos sem alvo de tool (`SessionStart`, `Stop`) omitem `matcher`. Os `.sh` precisam de `chmod +x`.
- **Criar um plugin novo (checklist):** 1) anatomia (`.claude-plugin/`, `skills/`, `hooks/` se preciso);
  2) `plugin.json` com `author` objeto; 3) `SKILL.md` com frontmatter; 4) `hooks/hooks.json` na subpasta
  + `chmod +x`; 5) entrada no `marketplace.json`; 6) `claude plugin validate`; 7) `claude plugin details`
  pra confirmar `Hooks (N)`.

## Regras de Release

- **Bump obrigatório do `plugin.json` em TODA mudança.** Sem subir a `version`, clientes
  nunca recebem a atualização (a versão é a chave de propagação).
- **Versão tem que bater em DOIS lugares:** `plugins/<nome>/.claude-plugin/plugin.json`
  E a entrada `version` correspondente em `.claude-plugin/marketplace.json`. Hoje estão
  alinhadas (ex.: project-doc 3.3.0 nos dois; qa-loop 1.2.1 nos dois).
- **Cache local NÃO auto-refresca** nesta máquina:
  `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/` precisa ser sincronizado por
  cima ou o plugin reinstalado; depois `/reload-plugins` (hooks recarregam sem restart).
- **Validar antes de publicar:** `claude plugin validate`. Mas atenção — ele NÃO pega o
  bug de hooks.json na raiz (ver Gotchas). Diagnóstico canônico de hook = `claude plugin details <plugin>@pedro-plugins` (mostra `Hooks (N)`).
- **Instalar ≠ atualizar índice:** `/plugin marketplace update` e `/reload-plugins` só
  atualizam catálogo/hooks; quem instala/desinstala de fato é `claude plugin install`/`uninstall`.

## Dependências entre Plugins

- **context-guard + handoff** andam juntos: o context-guard, ao cruzar o threshold,
  emite `stopReason` sugerindo rodar `/handoff` (`context-guard.sh:20-22`). Instalar um
  sem o outro deixa a sugestão sem destino.
- **context-guard depende de um statusLine wrapper** que escreve `/tmp/claude-context-pct`
  (o hook só lê esse arquivo; quem o popula é o wrapper registrado pela `context-guard:setup`).
- **`context-guard:setup` registra os hooks E o statusLine wrapper diretamente no `~/.claude/settings.json`
  (paths absolutos), não via `hooks.json` do plugin** — porque o cache do marketplace `source: directory`
  pode não existir no momento do setup; o `settings.json` é o ponto de registro garantido
  (`context-guard/skills/setup/SKILL.md:18`).
- **guardrails substitui hooks globais hand-rolled.** A `guardrails:setup` remove do
  `~/.claude/settings.json` os hooks antigos (lint-and-typecheck, scope-cop, Agent-teams-guard)
  pra não dispararem em dobro com os do plugin (senão lint roda 2x e paga 2 chamadas Haiku).
  **Mas PRESERVA** o hook `SessionStart` que aponta pro `sessionstart-adhd-mode.sh` (auto-ativador do
  modo ADHD) ao limpar os antigos — não apaga junto (`guardrails/skills/setup/SKILL.md:27,92-93`).
- **bootstrap** orquestra a instalação dos demais a partir do manifest + aplica config
  global versionada (`bootstrap/skills/setup` → `/bootstrap:setup`).
- **project-doc + graphify** acoplados: o project-doc trata o grafo (`graphify-out/`) como
  parte da documentação — atualiza/exige o grafo por padrão ao documentar.
- **qa-loop + visual:** o relatório humano do qa-loop reusa a skill `/visual` pra a
  superfície de seleção live (lê estado em `~/.claude/visual-state/latest.json`).
  `scope-cop.sh:213-235` também consome esse `latest.json` como fonte de plano aprovado.

## Testing

- **Suíte Python real no project-doc** (stdlib `assert`, sem framework):
  - `plugins/project-doc/lib/test_journal.py` — scrubber, cofre, delta forward/backward,
    colisão de id, validação de invalidate/curate. Roda com
    `python3 plugins/project-doc/lib/test_journal.py`. **CONFIRMADO: 117 checks passam.**
  - `plugins/project-doc/lib/test_graph_map.py`.
  - Self-contained: cria repo git temporário + cofre em `/tmp` via env
    `PROJECT_DOC_COFRE_DIR` (não toca o ambiente real).
- **Não há CI nem runner agregado** — testes são invocados à mão por arquivo.
- Para hooks/skills, "teste" = smoke test E2E manual (rodar a skill, `claude plugin details`).

## Gotchas

- ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), NUNCA `hooks.json` na raiz.**
  Na raiz o Claude Code ignora silenciosamente (`claude plugin details` mostra `Hooks (0)`);
  `claude plugin validate` passa mesmo assim. Hoje os 8 plugins com hook estão corretos.
- ⚠️ **`author` como STRING (em vez de objeto `{name,email}`) bloqueia o install sem erro.**
  Rodar `claude plugin validate`. Hoje 17/17 estão como objeto.
- ⚠️ **`SKILL.md` começando com `---` duplo (`---` na linha 1 E na 2) zera o frontmatter**
  — `name`/`description` caem no corpo, o loader rejeita a skill e o plugin inteiro falha
  ao instalar. Causou a falha histórica do grill-me; HOJE está correto (um `---` só abrindo,
  `plugins/grill-me/skills/grill-me/SKILL.md:1-4`). Caracteres `: ` ou `<>` em valores do
  frontmatter também bloqueiam install silenciosamente.
- ⚠️ **Editar skill/hook sem bumpar `plugin.json` = cliente nunca recebe.** A versão é a chave.
- ⚠️ **Cache do plugin não auto-refresca nesta máquina:** sincronizar por cima de
  `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/` ou reinstalar; depois `/reload-plugins`.
- ⚠️ **`${CLAUDE_PLUGIN_ROOT}` muda a cada bump** — não guarde estado lá; use `~/.claude/...` ou `/tmp`.
- Hooks devem ser **fail-open** (`exit 0` quando falta `jq`/`python3`/`claude`); um linter
  ausente ou juiz indisponível nunca pode bloquear uma edição.
- **scope-cop NÃO corta por limite de caracteres** — o veredito é julgamento de coerência
  da LLM (Haiku) contra o plano/pedido. Tem isenção explícita pra artefatos
  (`*/.claude/*`, `*/docs/*`, `*HANDOFF*`, `*PRD*`, `*plan*.html`, `*_archive/*`) e só
  policia arquivos de UI; circuit breaker libera após 3 BLOCKs seguidos (anti-loop).
- **scope-cop usa `deny` (não `ask`)** — nega pra o Claude se auto-corrigir, NUNCA escala
  pro Pedro.
- Plugins **não carregam env vars** — qualquer var necessária (ex.:
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, `CLAUDE_CONTEXT_THRESHOLD`) entra via skill `setup`.
- **`rm -rf` é bloqueado por permissão** (tanto em `~/.claude/` quanto no repo, `~/.claude/settings.json:160`)
  — use remoção alvo (`rm <arquivo>`), nunca recursiva-forçada.
- **`uninstall` não limpa o diretório do cache** [relatado] — a skill some de `installed_plugins.json`
  mas o dir `~/.claude/plugins/cache/pedro-plugins/<nome>/` sobra ("slash fantasma"); limpar à mão se reaparecer.
- **bootstrap nunca propaga estado degradado:** se `apply` falhar, o `session-sync` pula o
  snapshot/commit/push — senão uma falha transitória de uma máquina desinstalaria plugins
  de todas (`session-sync.sh:167-187`).
- **Secrets nunca vão pro git.** O scrubber do project-doc (`journal.py`) move o
  VALOR-secreto pro cofre (`~/Library/Mobile Documents/...` iCloud, override por
  `PROJECT_DOC_COFRE_DIR`) e deixa só `‹cofre:LABEL:hash›` no journal versionado. Refira
  segredos pelo NOME / pelo cofre `.claude/secrets/ops.env`, nunca pelo valor.
