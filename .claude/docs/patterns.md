---
generated: 2026-06-22
project: pedro-plugins
scope: plugins/project-doc/lib/journal.py, _shared/collect_engine.py, scripts/sync-shared.sh, plugins/guardrails/hooks/{scope-cop,lint-and-typecheck}.sh, plugins/context-guard/hooks/context-guard.sh, plugins/ship/hooks/pre-deploy-test-check.sh, plugins/bootstrap/hooks/{session-sync.sh,lib/apply.sh,lib/git-sync.sh}, plugins/graphify-guard/hooks/graphify-detect.sh, plugins/project-doc/lib/test_journal.py, .claude-plugin/marketplace.json, plugins/*/.claude-plugin/plugin.json, .gitignore
doc-sig: pedro-plugins/journal.py@gen=3.6#da241ca7
---

# patterns.md — convenções, release, dependências, gotchas

Doc derivada do código real (não da doc antiga). Tudo abaixo foi CONFIRMADO lendo o arquivo, exceto onde marcado `[relatado]`.

## Convenções Shell — fail-open, estado em ~/.claude, padrões dos hooks

Regra-mãe: **um hook NUNCA pode quebrar/bloquear o que não devia.** Toda dependência ausente → `exit 0` (fail-open).

- **Shebang `#!/bin/bash` ou `#!/usr/bin/env bash`** + `chmod +x`. Hooks com lógica de sync usam `set -uo pipefail` (`apply.sh:30`, `session-sync.sh:15`, `git-sync.sh:15`); hooks-trava NÃO usam `set -e` (não podem abortar no meio).
- **Fail-open por dependência ausente** — resolve binário via `command -v`, nunca path hardcoded de Homebrew:
  - `jq` ausente → `exit 0`: `lint-and-typecheck.sh:16-17`, `pre-deploy-test-check.sh:16`, `scope-cop.sh:16-19`.
  - `claude` (o juiz LLM) ausente → libera a edição: `scope-cop.sh:262-266`.
  - juiz com erro/timeout/saída ilegível → libera + loga: `scope-cop.sh:296-299, 317-320`.
- **Estado mutável vive em `~/.claude/…`, NUNCA dentro do plugin** (o cache `${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump de versão). Exemplos:
  - `~/.claude/guardrails/scope-cop.{mode,log,blockstreak,bypass}` (`scope-cop.sh:8-25`)
  - `~/.claude/plugins/.pedro-plugins-{last-sync,sync.lock}` (`session-sync.sh:28-29`)
  - `~/.claude/visual-state/latest.json` (live-sync do /visual, lido pelo scope-cop:212)
- **Exceção `/tmp`** para estado efêmero por-sessão: `/tmp/claude-context-pct` (escrito pela statusLine, lido pelo guard — `context-guard.sh:6`), sentinelas `/tmp/claude-context-warned-${SESSION_ID}` (`context-guard.sh:10`), `/tmp/claude-ata-session-<hash>` (sentinel legado de discovery — `collect_engine.py:319`).
- **Protocolo de saída do hook:**
  - PostToolUse bloqueante → `exit 2` + mensagem no stderr (`lint-and-typecheck.sh:128-131`).
  - PreToolUse bloqueante → JSON `{"continue":false,"stopReason":…}` (context-guard) OU `{"hookSpecificOutput":{permissionDecision:"deny",…}}` (scope-cop:328-334).
- **Sentinela por-sessão** pra disparar "uma vez por sessão": `session_id` vem de `jq -r '.session_id'` no stdin (`context-guard.sh:9`).
- **stat portátil mac↔linux:** `stat -f %m … || stat -c %Y …` (`session-sync.sh:54,106`; `graphify-detect.sh:26-27`).
- **Re-entrancy + lock atômico no sync:** guard via env `PEDRO_PLUGINS_HOOK_RUNNING` (`session-sync.sh:20-23`); lock por `mkdir` (POSIX, sem flock) com quebra de lock stale >5min (`session-sync.sh:53-64`).
- **scope-cop é juiz-LLM, não régua de caracteres:** chama `claude -p --model haiku` com system-prompt classificador; só policia arquivos de UI (`*.html|*.tsx|*.css|…` — `scope-cop.sh:58-61`), isenta docs/`.claude/`/PRD/HANDOFF (`:67-69`); circuit-breaker libera 1 edição após 3 BLOCKs seguidos (`:251-260`). NÃO corta por tamanho.

## Convenções Python — stdlib only, sem framework, onde mora o estado

- **stdlib pura.** `journal.py` importa só `argparse, hashlib, json, math, os, re, subprocess, sys, time`. `collect_engine.py` idem (+`glob`). Zero dependências de terceiros, zero framework de teste.
- **Degradação graciosa de import:** `journal.py:43-58` tenta importar `collect_engine`; se faltar, define fallbacks `anchor_of`/`finding_id` IDÊNTICOS (mesmo hash) e pula o tier de transcript — `HAVE_ENGINE` chaveia o resto.
- **`finding_id` = sha1 do TEXTO COMPLETO normalizado + raw_kind, truncado em 16 hex** (`collect_engine.py:532-534`, espelhado em `journal.py:56-58`). Hashear o texto inteiro (não a âncora de 64 chars) evita colisão entre falas com prefixo comum — qualquer divergência entre as duas cópias re-chavearia o journal.
- **Estado do project-doc: `.claude/.project-doc/`** (`journal.py:64-73`). É **VERSIONADO** — `findings.jsonl` (journal append-only) e `ledger.json` estão git-tracked (confirmado: `git ls-files`). É o veículo do conhecimento entre máquinas; só `.claude/.project-doc/backups/` fica gitignored (`.gitignore:37`).
- **Journal append-only:** `append_events` só faz `open(...,"a")` (`journal.py:122-129`); o estado vivo = `fold()` dos eventos por id em ordem cronológica (`:132-159`). `discovered` cria, `invalidated` mata (sem apagar), `curated` sobrepõe texto. Morte é definitiva até curadoria/re-discovery explícita.
- **Scrubber de secret = barreira entre conversa-verbatim e git** (`journal.py:330-458`). Scorer em 4 camadas: (1) estruturado PEM→connstring→JWT→provider; (1.5) pares JSON aninhados; (2) chave=valor de 1 linha; (3) prosa por palavra-sinal + entropia de Shannon (`_looks_random` ≥16 chars, entropia ≥3.5); (4) na dúvida marca `‹revisar?›`. Política: nomes/host/IP/porta/path/sha/uuid PRESERVADOS, só o VALOR vai pro cofre.
- **Cofre fora do repo:** `cofre_paths` (`journal.py:461-474`) — override `PROJECT_DOC_COFRE_DIR` (testes) > iCloud (`~/Library/Mobile Documents/com~apple~CloudDocs/Cofre`) > fallback local gitignored `.claude/secrets/_local_cofre`. `ensure_gitignore` planta `.claude/secrets/` ANTES de escrever (`:477-492, 500`).
- **Resolução de project-root mecânica** (`collect_engine.py:92-113`): sobe até o 1º ancestral com `.git` OU monorepo formal. Distingue projeto de agrupador (PEDRO/ e VIU/ sem `.git` são atravessados).

## Engine compartilhada — vendoring, não import em runtime

- **Fonte-da-verdade = `_shared/collect_engine.py`**; cópias derivadas em `plugins/handoff/lib/` e `plugins/project-doc/lib/`. As 3 são byte-idênticas (md5 confirmado).
- **Por que copiar e não importar:** o Claude Code isola plugins na instalação — só `plugins/<nome>/` vai pro cache, sem variável cross-plugin (`_shared/collect_engine.py:13-16`).
- **Build deste monorepo = `scripts/sync-shared.sh`** (o único "build"):
  - `scripts/sync-shared.sh` → vendora (copia para os 2 consumidores).
  - `scripts/sync-shared.sh --check` → NÃO copia, sai 1 se houver drift (gate de CI/pré-commit).
- ⚠️ **Editar `_shared/` sem rodar o sync deixa as cópias defasadas** — rode `sync-shared.sh` antes de commitar; `--check` para verificar.

## Regras de Release — bump plugin.json + espelhar marketplace.json

- **A `version` em `plugins/<nome>/.claude-plugin/plugin.json` é a chave de propagação.** Toda mudança = bump. No install, `plugin.json` vence o `marketplace.json` (commit aa274781), mas a entrada do marketplace deve ESPELHAR pra não enganar. Hoje todas as 17 batem:
  ```
  bootstrap 1.0.1 · context-guard 1.1.1 · fallow 1.0.3 · graphify-guard 1.0.1
  grill-me 1.0.0 · grill-with-docs 1.0.0 · guardrails 1.1.1 · handoff 1.7.1
  improve 1.0.0 · principles 1.0.0 · project-doc 3.6.0 · qa-loop 1.3.0
  raiox 0.2.0 · ship 1.1.0 · slides 1.2.0 · sovai 1.4.0 · visual 1.2.1
  ```
- **`marketplace.json` é o ponto de convergência de TODAS as frentes** + é reformatado por um linter (single-line ↔ multi-line). Em commits cirúrgicos isole-o: `git stash push -- .claude-plugin/marketplace.json`, commita o resto, despausa. [relatado, dos handoffs]
- **Cache não auto-refresca** (nesta máquina): `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/`. Sincronize por cima ou reinstale; depois `/reload-plugins`. [relatado]
- **`author` DEVE ser objeto `{name, …}`, nunca string** — string bloqueia o install em silêncio (commit b4770351 corrigiu grill-me/grill-with-docs; hoje ambos são dict, os outros 15 omitem o campo, o que é válido).
- **Gate de release = `claude plugin validate`** (pega frontmatter quebrado, author-string). **Diagnóstico de hook = `claude plugin details <nome>`** (mostra `Hooks (N)`; `validate` NÃO pega hooks.json mal-posicionado).
- **Passo-a-passo de plugin novo** [relatado, doc_nuance]: anatomia → `.claude-plugin/plugin.json` → `skills/<nome>/SKILL.md` → `hooks/hooks.json`+scripts `chmod +x` → entrada no `marketplace.json` com mesma version → `validate`+`details` → bump.

## Dependências entre Plugins

- **context-guard → handoff:** o guard, ao cruzar o threshold, manda rodar `/handoff` (`context-guard.sh:21`). Andam juntos.
- **project-doc + handoff → engine compartilhada:** ambos consomem `collect_engine.py` (vendorado de `_shared/`). project-doc é o único com scrubber/journal/cofre (`journal.py`) e grafo (`graph_map.py`).
- **project-doc + graphify(-guard):** project-doc detecta `graphify-out/graph.json`, checa staleness e fia o grafo no CLAUDE.md (`graph_map.py`); graphify-guard usa `graphify-detect.sh` (helper compartilhado, fan-in 8) pra heads-up de freshness.
- **bootstrap (ex bootstrap-third-party):** orquestra sync de marketplaces/plugins via `apply.sh` (lê `config/manifest.json`) + config global. `session-sync.sh` roda no SessionStart: fetch → throttle 24h → pull → apply → snapshot → commit+push do manifest (`git-sync.sh`).
- **guardrails:** 3 hooks que viviam soltos em `~/.claude/settings.json`, empacotados pra replicar entre máquinas (lint-and-typecheck, scope-cop, agent-teams classifier). scope-cop lê o estado do /visual.
- **ship → testes:** `pre-deploy-test-check.sh` bloqueia deploy se os testes do app falham (prefere `scripts/run_app_tests.sh` por-app; fallback whole-suite).
- **qa-loop:** consolidou e substituiu `/qa`, `/rev6`, `/iterate`.

## Testing — `python3 .../test_*.py`, stdlib, sem framework

- **3 suites, todas em `plugins/project-doc/lib/`:**
  ```bash
  python3 plugins/project-doc/lib/test_journal.py        # 117 checks (CONFIRMADO passando)
  python3 plugins/project-doc/lib/test_graph_map.py      #  23 checks (CONFIRMADO passando)
  python3 plugins/project-doc/lib/test_pattern_check.py  #  21 checks (CONFIRMADO passando)
  ```
- **Padrão:** `assert` numa função `check(label, cond)` que conta PASS e imprime; sem pytest/unittest. Self-contained — `test_journal.py` cria repo git temporário + cofre em `/tmp` via `PROJECT_DOC_COFRE_DIR` (`:18-22`).
- **O que `test_journal.py` cobre:** os 5 vazamentos de secret do code-review (PEM-newline, numérico, prosa, provider, PUBLIC word-boundary), integridade do cofre, delta forward, backward-delta (self-stale + working-tree), colisão de id de 64 chars, `self_path_match`, validação de invalidate/curate.
- **Shell:** sem testes unitários; o "teste" é `claude plugin validate` + `claude plugin details`. `sync-shared.sh --check` é o gate de drift da engine.
- ⚠️ **Os demais plugins não têm teste automatizado** — verificação é manual (validate/details, smoke E2E).

## Gotchas — lista completa

- ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), NUNCA na raiz.** Na raiz o Claude Code ignora em silêncio (`details` → `Hooks(0)`); `validate` passa mesmo assim. Hoje os 8 plugins com hook estão corretos (bootstrap, context-guard, graphify-guard, guardrails, handoff, project-doc, ship, visual). (commits 9389c512, 379b6b08)
- ⚠️ **Bump `plugin.json` em TODA mudança** — a `version` é a chave de propagação; espelhe em `marketplace.json`.
- ⚠️ **`author` como string bloqueia install em silêncio** — use objeto `{name,…}` ou omita. (commit b4770351)
- ⚠️ **`SKILL.md` com `---` duplo (linha 1 E 2), ou `: `/`<>` em valores de frontmatter, bloqueiam install em silêncio.** Rode `claude plugin validate`. (memory 924b2b88, [relatado])
- ⚠️ **Cache `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/` não auto-refresca** nesta máquina — sincronize por cima/reinstale, depois `/reload-plugins`. [relatado]
- ⚠️ **`validate` NÃO diagnostica hook mal-posicionado** — só `claude plugin details <nome>` (`Hooks N`) faz isso.
- ⚠️ **Instalar ≠ atualizar índice:** `marketplace update`/`reload-plugins` só atualizam catálogo/hooks; instala/desinstala de fato é `claude plugin install`/`uninstall`. [relatado]
- ⚠️ **Editar `_shared/collect_engine.py` sem rodar `scripts/sync-shared.sh`** deixa as cópias vendoradas defasadas (handoff + project-doc) — `--check` falha em drift.
- ⚠️ **As 2 cópias de `finding_id` (`collect_engine.py:532` e `journal.py:56`) DEVEM ser idênticas** — divergência re-chaveia o journal inteiro.
- ⚠️ **Estado mutável NUNCA dentro do plugin** (`${CLAUDE_PLUGIN_ROOT}` é reescrito a cada bump) — vai em `~/.claude/…` (`scope-cop.sh:13-14`).
- ⚠️ **Plugins NÃO carregam env vars** — qualquer var necessária (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, `CLAUDE_CONTEXT_THRESHOLD`) entra via a skill `setup` do plugin (bootstrap/context-guard/guardrails). É a razão de existir das skills `:setup`. (context-guard.sh:5, guardrails/skills/setup/SKILL.md:12)
- ⚠️ **`marketplace.json` é reformatado por linter + converge todas as frentes** — em commit cirúrgico, isole com `git stash push -- .claude-plugin/marketplace.json`. [relatado]
- ⚠️ **`rm -rf` é bloqueado por permissão** (`Bash(rm -rf*)` no `deny` do `~/.claude/settings.json:161`), valendo tanto em `~/.claude/` quanto no repo — use remoção alvo (`rm <arquivo>`), nunca recursiva-forçada.
- ⚠️ **last_commit órfão no ledger** (rebase/amend/reset) → `journal.py:727` trata como cold-start, senão `git log orfão..HEAD` sai 128 e perde TODOS os commits do range (`_commit_reachable:563-566`).
- ⚠️ **`self_path_match`: basename puro (sem `/`) só marca stale se EXATAMENTE 1 arquivo mudado tem aquele nome** (`journal.py:787-804`) — evita `config.json`/`index.ts` marcarem homônimos no monorepo.
- ⚠️ **apply falhou → snapshot/push PULADO** (`session-sync.sh:178-187`): senão um install que falhou numa máquina vira "nova verdade" e desinstala o plugin de TODAS. Nunca propague estado degradado.
- ⚠️ **context-guard 80% assume modelo ~200k** (ex. Opus): feito pra modelos de contexto baixo. Threshold via `CLAUDE_CONTEXT_THRESHOLD` (`context-guard.sh:5`).
- ⚠️ **scope-cop precisa de `claude` no PATH** (é o juiz) — sem ele, fail-open silencioso (trava destravada). Pra desligar: `~/.claude/guardrails/scope-cop.mode` = `off`.
- ⚠️ **ship: `jq` resolvido via PATH** (commit e36fff61) — path Homebrew fixo deixava o gate fail-open silencioso fora deste mac.
