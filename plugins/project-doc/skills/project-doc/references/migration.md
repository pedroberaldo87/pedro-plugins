# Migration v1 → v2

Referência do modo `migrate` do project-doc. Carregue este arquivo SÓ quando markers v1 forem detectados ou o usuário rodar `/project-doc migrate`.

## Steps

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

## Monorepo v1 → v2 Migration

For monorepo v1 blocks, additionally:
- Parse per-app sections (### {app-name}) from the `## Apps` section
- Create per-app subdirectories in `.claude/docs/{app-name}/`
- Map each app's content to the appropriate doc (deps → note in architecture, gotcha → patterns, etc.)
- Shared sections (Infra Compartilhada, Stack Comum, Deploy) go to shared root docs
