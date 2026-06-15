---
generated: 2026-06-15
project: pedro-plugins
scope: .claude-plugin/marketplace.json, plugins/*/plugin.json, plugins/*/hooks/hooks.json
---

# Patterns & Conventions

## Hooks de Plugin — Localização (ARMADILHA #1)
- **A declaração de hooks vai em `plugins/<nome>/hooks/hooks.json` (dentro da subpasta `hooks/`).** Um `hooks.json` na RAIZ do plugin é silenciosamente ignorado pelo Claude Code — não há erro, `claude plugin validate` passa, o plugin instala, mas os hooks nunca disparam.
- **Diagnóstico canônico:** `claude plugin details <plugin>@pedro-plugins`. Se um plugin que tem hooks mostra `Hooks (0)`, a declaração está no lugar errado (ou ausente). Plugin saudável mostra `Hooks (N) <eventos>`.
- **Os scripts** ficam em `hooks/<script>.sh` e são referenciados no hooks.json como `${CLAUDE_PLUGIN_ROOT}/hooks/<script>.sh` (a var resolve pra raiz do plugin, independe de onde o hooks.json está). Tornar executável: `chmod +x`.
- **Incidente (jun/2026):** os 5 plugins com hook (graphify-guard, visual, ship, context-guard, bootstrap-third-party) estavam TODOS com `hooks.json` na raiz → `Hooks (0)`, hooks mortos. Corrigido movendo pra `hooks/hooks.json` + bump (commits dd75977, c5c2e89). Antes do fix, `context-guard` só funcionava porque a skill setup registrava parte no `settings.json`.
- Formato do hooks.json: `{ "hooks": { "<Evento>": [ { "matcher": "...", "hooks": [ {"type":"command","command":"${CLAUDE_PLUGIN_ROOT}/hooks/x.sh","timeout":N} ] } ] } }`. Eventos sem matcher (ex: SessionStart) omitem o campo `matcher`.

## Marketplace Registry — Regras de Release
- **Arquivo índice:** `.claude-plugin/marketplace.json`
- **`version` em `plugin.json`:** bumpar a cada mudança em qualquer arquivo do plugin — sem bump, clientes nunca recebem a atualização
- **Sincronização:** versão em `plugin.json` deve ser idêntica à entrada em `marketplace.json`
- **Cache local não auto-refresca:** mesmo nesta máquina, editar o source não basta — o Claude lê de `~/.claude/plugins/cache/pedro-plugins/<nome>/<versão>/`. Sincronize por cima do cache (ou reinstale) e rode `/reload-plugins`. O número da versão no path do cache é só o nome do diretório.
- **Instalar ≠ atualizar índice:** `/plugin marketplace update` só atualiza o catálogo; `/plugin install <nome>@pedro-plugins` é o que instala. `/reload-plugins` recarrega hooks na sessão sem precisar de restart.
- **Categorias:** `productivity` (8 plugins), `dev-tools` (10 plugins)

## Dependências entre Plugins
- **context-guard → handoff**: quando o guard dispara, sugere `/handoff` — instalar ambos juntos
- **bootstrap-third-party → manifest.json**: hook SessionStart lê manifest para decidir o que instalar/sincronizar
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
- Editar skill/hook sem bumpar `plugin.json` = clientes nunca recebem atualização; e o cache local não refresca sozinho
- sovai não faz workarounds silenciosos — pula itens bloqueados e anota; a descrição no marketplace já reflete isso
- context-guard é agnóstico de statusLine — encaminha via `CLAUDE_STATUSLINE_FORWARD` (env var); sem dependência direta do claude-hud
- context-guard: os hooks (reset + check de 80%) vêm de `hooks/hooks.json`; a skill `/context-guard:setup` deve cuidar SÓ do statusLine wrapper — não registrar os hooks no settings.json também, senão duplica
- `iterate` e `improve` são plugins válidos no marketplace mas raramente usados diretamente — não confundir com fluxos internos de outros plugins
