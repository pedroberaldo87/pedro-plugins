---
generated: 2026-06-20
project: pedro-plugins
scope: .claude-plugin/marketplace.json, plugins/*/plugin.json, plugins/*/hooks/hooks.json
---

# Patterns & Conventions

## Hooks de Plugin — Localização (ARMADILHA #1)
- **A declaração de hooks vai em `plugins/<nome>/hooks/hooks.json` (dentro da subpasta `hooks/`).** Um `hooks.json` na RAIZ do plugin é silenciosamente ignorado pelo Claude Code — não há erro, `claude plugin validate` passa, o plugin instala, mas os hooks nunca disparam.
- **Diagnóstico canônico:** `claude plugin details <plugin>@pedro-plugins`. Se um plugin que tem hooks mostra `Hooks (0)`, a declaração está no lugar errado (ou ausente). Plugin saudável mostra `Hooks (N) <eventos>`.
- **"Hooks (N)" conta EVENTOS, não hooks individuais** — um plugin com 3 hooks em 2 eventos (PostToolUse, PreToolUse) aparece como `Hooks (2)`. Não confunda contagem baixa com hook faltando.
- **Os scripts** ficam em `hooks/<script>.sh` e são referenciados no hooks.json como `${CLAUDE_PLUGIN_ROOT}/hooks/<script>.sh` (a var resolve pra raiz do plugin instalado, independe de onde o hooks.json está). Tornar executável: `chmod +x`.
- **Incidente (jun/2026):** os 5 plugins com hook (graphify-guard, visual, ship, context-guard, e o então `bootstrap-third-party` — hoje `bootstrap`) estavam TODOS com `hooks.json` na raiz → `Hooks (0)`, hooks mortos. Corrigido movendo pra `hooks/hooks.json` + bump. Antes do fix, `context-guard` só funcionava porque a skill setup registrava parte no `settings.json`.
- Formato do hooks.json: `{ "hooks": { "<Evento>": [ { "matcher": "...", "hooks": [ {"type":"command","command":"${CLAUDE_PLUGIN_ROOT}/hooks/x.sh","timeout":N} ] } ] } }`. Eventos sem matcher (ex: SessionStart) omitem o campo `matcher`.

## Estado Mutável de Hook (ARMADILHA #2)
- **Estado mutável de hook NÃO pode morar em `${CLAUDE_PLUGIN_ROOT}`.** O cache do plugin é reescrito a cada version bump → qualquer log/mode/streak gravado lá some na próxima atualização. Use um path estável fora do cache: o guardrails grava em `~/.claude/guardrails/`.
- `2>/dev/null` num redirect de **entrada** (`tr ... < "$FILE"`) NÃO suprime falha de abertura do `<` — em máquina nova, com o arquivo de estado ainda inexistente, o shell quebra antes do `tr` rodar. Crie o arquivo (ou teste `[ -f ]`) antes de lê-lo.

## Marketplace Registry — Regras de Release
- **Arquivo índice:** `.claude-plugin/marketplace.json`
- **`version` em `plugin.json`:** bumpar a cada mudança em qualquer arquivo do plugin — sem bump, clientes nunca recebem a atualização
- **Sincronização:** a versão em `plugin.json` deve ser idêntica à entrada em `marketplace.json`. ⚠️ jun/2026: `guardrails` ficou em `1.1.0` no plugin.json e `1.0.0` no marketplace — re-sincronizar antes de publicar
- **`claude plugin validate .`** é o gate real que decide se um plugin instala a partir do marketplace — rodar antes de publicar (pega frontmatter quebrado e erro de schema; NÃO pega hooks.json no lugar errado)
- **Cache local não auto-refresca:** mesmo nesta máquina, editar o source não basta — o Claude lê de `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/`. Sincronize por cima do cache (ou reinstale) e rode `/reload-plugins`. O número da versão no path do cache é só o nome do diretório.
- **`autoUpdate` (marketplace `source: directory`) atualiza um plugin JÁ instalado quando a versão sobe** (ex: 1.1.0→1.2.0 pegou no reload), mas **NÃO instala um plugin novo nem desinstala um removido** — pra isso só `claude plugin install`/`uninstall`.
- **Instalar ≠ atualizar índice:** `/plugin marketplace update` e `/reload-plugins` só atualizam o catálogo / recarregam hooks; **não** instalam nem desinstalam. Quem mexe no que está instalado é `claude plugin install`/`uninstall`.
- **O uninstall NÃO limpa a pasta do cache** — a skill some de `installed_plugins.json` mas o dir do cache sobra ("slash fantasma"), podendo confundir. Limpar o dir manualmente se necessário.
- **Categorias:** `productivity` (8 plugins), `dev-tools` (9 plugins)

## Dependências entre Plugins
- **context-guard → handoff**: quando o guard dispara, sugere `/handoff` — instalar ambos juntos
- **bootstrap → config/manifest.json**: hooks SessionStart/PostToolUse leem o manifest pra decidir o que instalar/sincronizar (marketplaces + plugins de terceiros)
- **bootstrap → settings.json**: a camada de config global (`/bootstrap:setup` → `apply-config.sh`) faz merge de `config/settings-defaults.json` em `~/.claude/settings.json` (env, permissions, behavior flags) e instala o CLAUDE.md global + statusLine. Nunca toca `settings.local.json` (secrets)
- **guardrails → settings.json**: `/guardrails:setup` liga `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` e **remove os hooks globais antigos** (lint, scope-cop, Agent guard) de `~/.claude/settings.json` pra não disparar em dobro com os do plugin. Preserva o `SessionStart` do `sessionstart-adhd-mode.sh`
- **graphify-guard → graphify (skill global)**: o guard só redireciona; quem cria/consulta o grafo é a skill `graphify` / o binário `graphify`

## Desenvolvimento de Plugin Novo
1. Criar `plugins/<nome>/` com a anatomia padrão (ver architecture.md)
2. Escrever `.claude-plugin/plugin.json` com `name`, `version`, `description`, `author`, `homepage`
3. Se skill: escrever `skills/<nome>/SKILL.md`
4. Se hooks: criar `hooks/hooks.json` (SUBPASTA, **nunca** `hooks.json` na raiz) + scripts em `hooks/*.sh` com `chmod +x`, usando `${CLAUDE_PLUGIN_ROOT}/hooks/...` nos paths
5. Adicionar entrada em `.claude-plugin/marketplace.json` (com `version` idêntica ao plugin.json)
6. `claude plugin validate ./plugins/<nome>` (schema) **e** `claude plugin details <nome>@pedro-plugins` (confirmar `Hooks (N)` se tem hook)
7. Bumpar `version` a cada mudança subsequente; sincronizar cache local; commit + push

## Validação Antes de Publicar
- `claude plugin validate ./plugins/<nome>` — detecta silently-broken frontmatter e erro de schema (mas NÃO pega hooks.json no lugar errado)
- `claude plugin details <nome>@pedro-plugins` — confirma o inventário real (Skills/Hooks/Agents reconhecidos). É o único jeito de pegar hook que não carrega
- **author como objeto JSON** no frontmatter do `SKILL.md` bloqueia install silenciosamente
- **Caracteres `: ` ou `<>`** em valores de frontmatter YAML também bloqueiam silenciosamente

## Gotchas
- Hook em `hooks.json` na raiz = morto (ver "Hooks de Plugin" acima) — a causa de bug mais traiçoeira deste repo
- Estado mutável de hook em `${CLAUDE_PLUGIN_ROOT}` = perdido no próximo bump (ver "Estado Mutável de Hook")
- Editar skill/hook sem bumpar `plugin.json` = clientes nunca recebem atualização; e o cache local não refresca sozinho
- **Plugin instalado = hook global automático**: uma vez instalado, o `hooks.json` do plugin dispara em QUALQUER projeto, não só neste repo — é o mecanismo pra guardrails/context-guard valerem em todo lugar, mas cuidado ao testar
- `bootstrap-third-party` foi **renomeado pra `bootstrap`** (jun/2026) e ganhou a camada de config global — referências antigas ao nome velho estão mortas
- `marketplace.json` é o arquivo de convergência de TODAS as frentes (e é reformatado por linter) — cuidado ao isolar commits cirúrgicos pra não arrastar mudança de outra frente
- Nesta máquina o marketplace `pedro-plugins` é `source: directory` apontando pro próprio working tree local (com `autoUpdate`) — por isso o cache reage a bump sem reinstall
- `rm -rf` é bloqueado pela permissão tanto em `~/.claude/` quanto no repo — usar remoção alvo, não recursiva-forçada
- sovai não faz workarounds silenciosos — pula itens bloqueados e anota; a descrição no marketplace já reflete isso
- context-guard é agnóstico de statusLine — encaminha via `CLAUDE_STATUSLINE_FORWARD` (env var); sem dependência direta do claude-hud
- context-guard: os hooks (reset + check de 80%) vêm de `hooks/hooks.json`; a skill `/context-guard:setup` cuida SÓ do statusLine wrapper — não registrar os hooks no settings.json também, senão duplica
- `improve` é plugin válido no marketplace mas raramente usado diretamente — não confundir com fluxos internos de outros plugins
- `qa-loop` substituiu `qa`, `rev6` e `iterate` (jun/2026): o convergente do iterate virou um modo embutido no qa-loop (a detecção lint/typecheck/test foi copiada, não referenciada)
