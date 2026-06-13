---
generated: 2026-06-13
project: pedro-plugins
scope: .claude-plugin/marketplace.json, plugins/*/plugin.json
---

# Patterns & Conventions

## Marketplace Registry — Regras de Release
- **Arquivo índice:** `.claude-plugin/marketplace.json`
- **`version` em `plugin.json`:** bumpar a cada mudança em qualquer arquivo do plugin — sem bump, clientes nunca recebem a atualização
- **Sincronização:** versão em `plugin.json` deve ser idêntica à entrada em `marketplace.json`
- **Categorias:** `productivity` (7 plugins), `dev-tools` (10 plugins)

## Dependências entre Plugins
- **context-guard → handoff**: quando o guard dispara, sugere `/handoff` — instalar ambos juntos
- **bootstrap-third-party → manifest.json**: hook SessionStart lê manifest para decidir o que instalar/sincronizar

## Desenvolvimento de Plugin Novo
1. Criar `plugins/<nome>/` com a anatomia padrão (ver architecture.md)
2. Escrever `plugin.json` com `name`, `version`, `description`, `author`, `homepage`
3. Se skill: escrever `skills/<nome>/SKILL.md`
4. Se hooks: declarar em `hooks.json` usando `${CLAUDE_PLUGIN_ROOT}` nos paths dos scripts
5. Adicionar entrada em `.claude-plugin/marketplace.json`
6. Bumpar `version` a cada mudança subsequente

## Validação Antes de Publicar
- Rodar `claude plugin validate` — detecta silently-broken frontmatter
- **author como objeto JSON** no frontmatter do `SKILL.md` bloqueia install silenciosamente
- **Caracteres `: ` ou `<>`** em valores de frontmatter YAML também bloqueiam silenciosamente

## Gotchas
- Editar skill/hook sem bumpar `plugin.json` = clientes nunca recebem atualização
- sovai não faz workarounds silenciosos — pula itens bloqueados e anota; a descrição no marketplace já reflete isso
- context-guard é agnóstico de statusLine — encaminha via `CLAUDE_STATUSLINE_FORWARD` (env var); sem dependência direta do claude-hud
- context-guard requer setup skill (`/context-guard:setup`) para registrar o statusLine wrapper em `settings.json`; os hooks vêm do `hooks.json` via `${CLAUDE_PLUGIN_ROOT}`
- `iterate` e `improve` são plugins válidos no marketplace mas raramente usados diretamente — não confundir com fluxos internos de outros plugins
