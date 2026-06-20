# pedro-plugins

Marketplace privado de plugins para [Claude Code](https://docs.claude.com/en/docs/claude-code). Monorepo — cada subdiretório em `plugins/` é um plugin independente (skills, hooks e automações), distribuído via `.claude-plugin/marketplace.json`.

**17 plugins · Markdown + Shell + Python · sem build, sem package manager.**

---

## Índice

- [Instalação](#instalação)
- [Plugins](#plugins)
  - [Sessão & continuidade](#sessão--continuidade)
  - [Planejamento & review](#planejamento--review)
  - [Documentação & conhecimento](#documentação--conhecimento)
  - [Dev, deploy & limpeza](#dev-deploy--limpeza)
  - [Apresentação visual](#apresentação-visual)
  - [Setup de máquina](#setup-de-máquina)
  - [Domínio VIU](#domínio-viu)
- [Hooks automáticos](#hooks-automáticos)
- [Anatomia de um plugin](#anatomia-de-um-plugin)
- [Desenvolvendo localmente](#desenvolvendo-localmente)
- [Publicando uma mudança](#publicando-uma-mudança)
- [Licença](#licença)

---

## Instalação

### Pegar só o que quiser

```bash
# 1. Adicionar o marketplace (uma vez por máquina)
claude plugin marketplace add git@github.com:pedroberaldo87/pedro-plugins.git

# 2. Instalar os plugins desejados
claude plugin install visual@pedro-plugins
claude plugin install qa-loop@pedro-plugins
claude plugin install handoff@pedro-plugins
# ...
```

### Restaurar o setup inteiro (máquina nova)

```bash
# 1. Marketplace + bootstrap
claude plugin marketplace add git@github.com:pedroberaldo87/pedro-plugins.git
claude plugin install bootstrap@pedro-plugins

# 2. Instala marketplaces + plugins do manifest E aplica a config global
#    (env vars, permissões, flags, CLAUDE.md global, statusLine)
/bootstrap:setup
```

> `bootstrap` substitui o antigo `bootstrap-third-party`.

### Verificar estado

```bash
claude plugin list                       # plugins instalados
claude plugin marketplace list           # marketplaces conhecidos
claude plugin details <nome>@pedro-plugins   # diagnóstico canônico (mostra Hooks (N))
```

---

## Plugins

Plugins marcados com **⚙️** registram hooks que rodam **sozinhos** (sem slash command) — veja [Hooks automáticos](#hooks-automáticos). Os demais são invocados sob demanda via slash command / skill.

### Sessão & continuidade

| Plugin | Trigger | O que faz |
|---|---|---|
| `handoff` ⚙️ | `/handoff` · override `/handoff salvar\|retomar` | Continuidade de sessão em um comando: detecta o estado e roteia — contexto cheio → salva um documento de transferência; sessão recém-limpa → retoma de onde parou. Workspace-aware: o handoff pertence ao projeto que a sessão tocou (resolve a fronteira `.git`), funciona em projeto único, monorepo (`HANDOFF-<módulo>.md`) ou pasta guarda-chuva. |
| `context-guard` ⚙️ | automático (PostToolUse) · setup `/context-guard:setup` | Auto-interrompe o workflow quando o context window passa de um threshold configurável (default 80%) e sugere `/handoff`. Agnóstico de statusLine — encaminha para qualquer comando existente via `CLAUDE_STATUSLINE_FORWARD`. **Use junto com `handoff`.** |
| `sovai` | `/sovai` | Modo autônomo — executa um plano até o fim sem pausas, checkpoints ou confirmações. Pula bloqueios (sem workaround silencioso), registra cada decisão, roda um passe final headless de `qa-loop` e entrega relatório estruturado. |

### Planejamento & review

| Plugin | Trigger | O que faz |
|---|---|---|
| `qa-loop` | `/qa-loop <alvo>` | Loop de review→conserto que **para por retornos decrescentes**, não por zero. Motor roda como **Workflow determinístico** (Opus revisa → Opus planeja/adjudica → Sonnet conserta; gate/churn/parada em código). Ancora no plano (3 buckets: implementação / plan-drift / plano-falho), regression gate por conserto, accepted-limits, relatório **humano** (HTML) + journal **agêntico**. Substitui `qa`, `rev6` e `iterate`. |
| `grill-me` | `/grill-me` | Entrevista implacável, uma pergunta por vez, sobre um plano/design até esgotar a árvore de decisões. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `grill-with-docs` | `/grill-with-docs` | Igual ao `grill-me`, mas confronta contra o domain model existente (CONTEXT.md, ADRs) e atualiza as docs inline conforme as decisões cristalizam. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `principles` | `/principles` | Carrega princípios de sistema do projeto (`PRINCIPIOS-SISTEMAS.md`), mapeia categorias relevantes ao contexto e gera um guia com WHY + HOW. Dois modos: planning e review. |

### Documentação & conhecimento

| Plugin | Trigger | O que faz |
|---|---|---|
| `project-doc` ⚙️ | `/project-doc` · SessionStart + PreToolUse | Gera um sistema de documentação a partir de **toda** a evidência do projeto (arquivos, handoffs, memória, grafo, git log, transcripts) num journal versionado append-only, projetado em índice `CLAUDE.md` + `.claude/docs/*.md` + ponteiros finos. Scrubber move segredos pra um vault (nunca pro git). Suporta delta/`--deep`/`--rebuild`, monorepo, guard hook doc-first e limpeza de artefatos. |
| `graphify-guard` ⚙️ | automático (SessionStart + PreToolUse) | Garante que os knowledge graphs do `graphify` sejam consultados quando relevante. Aviso no SessionStart quando há grafo; rede no PreToolUse redireciona grep/glob/find cego pra `graphify query` uma vez por sessão. Detecta grafo defasado e oferece `graphify --update`. Defense-in-depth, fail-open, monorepo-aware. |

### Dev, deploy & limpeza

| Plugin | Trigger | O que faz |
|---|---|---|
| `ship` ⚙️ | `/ship` · PreToolUse | Fluxo de deploy pra produção: lint → type-check → commit → push → deploy numa sequência disciplinada. |
| `guardrails` ⚙️ | automático (PostToolUse + PreToolUse) · setup `/guardrails:setup` | Guardrails globais de edição como hooks: lint & type-check pós-edição (JS/TS/Python), um scope-cop LLM que bloqueia edições de UI fora do plano aprovado e um guard de uso indevido de Agent Teams. Portável entre máquinas — substitui hooks hand-rolled no `~/.claude/settings.json`. Rode `/guardrails:setup` uma vez por máquina. |
| `fallow` | `/fallow` | Roda o Fallow (analisador estático JS/TS — código morto, duplicação, complexidade), classifica achados por tipo e confiança, audita o relatório pra pegar falsos-positivos (cron, rotas HTTP, imports dinâmicos) e entrega um relatório interativo onde você escolhe o que limpar. Limpeza com rede de segurança (preview + build/test). |
| `improve` | `/improve` | Implementa rodadas de melhoria iterativa lendo o `IMPROVEMENT_PROGRAM.md` do app + issues do GitHub com label `autoresearch`. Genérico — funciona com qualquer app que siga a metodologia. |

### Apresentação visual

| Plugin | Trigger | O que faz |
|---|---|---|
| `visual` ⚙️ | `/visual` · automático em planos/diagnósticos (PreToolUse em ExitPlanMode) | Transforma textão do CLI em views HTML dark-theme interativas, abertas no browser com **live sync** de volta pro Claude via daemon local. Modo auto renderiza planos (3+ itens), decisões (2+ opções) e diagnósticos (3+ problemas) sem precisar invocar. |
| `slides` | `/slides <arquivo.md> [tema]` | Outline em markdown → deck HTML single-file nível keynote. Sistema de temas (VIU default), linguagem de apresentação com tipografia grande, fidelidade estrita ao texto (nunca inventa frase) e output ao lado do `.md` de origem. |

### Setup de máquina

| Plugin | Trigger | O que faz |
|---|---|---|
| `bootstrap` ⚙️ | `/bootstrap:setup` · automático no SessionStart | Prepara uma máquina nova: auto-sincroniza marketplaces e plugins via hooks **e** aplica a config global versionada (env, permissões, flags, CLAUDE.md global, statusLine resolvido por máquina). Rode `/bootstrap:setup` uma vez por máquina. |

### Domínio VIU

| Plugin | Trigger | O que faz |
|---|---|---|
| `raiox` | `/raiox` · `roda o raiox` | RAIOX — inteligência replicável de canais do YouTube pra VIU Studio. Orquestra o pipeline viu-raiox (fetch público → fact store DuckDB → módulos de análise code-only → validação de números órfãos) por config YAML de canal. **Honesty Rule:** todo número citável nasce em JSON gerado por código; o LLM nunca origina número. |

---

## Hooks automáticos

8 plugins registram hooks que disparam sem slash command:

| Plugin | Eventos | Papel |
|---|---|---|
| `bootstrap` | SessionStart · PostToolUse | Auto-sync de marketplaces/plugins |
| `context-guard` | SessionStart · PostToolUse | Vigia o context window, sugere handoff |
| `graphify-guard` | SessionStart · PreToolUse | Redireciona busca cega pro knowledge graph |
| `guardrails` | PreToolUse · PostToolUse | Lint/type-check + scope-cop de UI |
| `handoff` | SessionStart · PreToolUse · Stop | Detecta retomada e salva continuidade |
| `project-doc` | SessionStart · PreToolUse | Guard doc-first + aviso de doc defasada |
| `ship` | PreToolUse | Guarda o fluxo de deploy |
| `visual` | PreToolUse | Intercepta ExitPlanMode pra renderizar o plano |

> ⚠️ **Hook de plugin vai em `hooks/hooks.json` (subpasta), nunca `hooks.json` na raiz.** Na raiz o Claude Code ignora silenciosamente — `claude plugin details` mostra `Hooks (0)` e nada dispara. `claude plugin validate` passa mesmo assim. Diagnóstico canônico = `claude plugin details <plugin>@pedro-plugins`.

---

## Anatomia de um plugin

```
plugins/<nome>/
├── .claude-plugin/
│   └── plugin.json          # Identidade: nome, versão, descrição, autor
├── hooks/                   # (opcional) automações
│   ├── hooks.json           #   ⚠️ AQUI, não na raiz do plugin
│   └── *.sh / *.py          #   scripts dos hooks
├── skills/<nome>/
│   └── SKILL.md             # Instrução completa da skill
└── lib/                     # (opcional) código compartilhado (ex.: project-doc, raiox)
```

O catálogo vive em `.claude-plugin/marketplace.json` na raiz — cada plugin tem uma entrada com `name`, `source`, `description`, `category`, `version` e `tags`.

---

## Desenvolvendo localmente

```bash
git clone git@github.com:pedroberaldo87/pedro-plugins.git ~/PROGRAMACAO/PEDRO/pedro-plugins
```

O `bootstrap` detecta se o repo está clonado localmente e adapta:
- **Com repo:** pode fazer `snapshot` (estado da máquina → manifest, commit, push).
- **Sem repo:** só `apply` (manifest → máquina).

Caminho alternativo:

```bash
export PEDRO_PLUGINS_REPO="/caminho/alternativo/pedro-plugins"
```

---

## Publicando uma mudança

> ⚠️ **Editar skill/hook sem bumpar `version` no `plugin.json` = clientes nunca recebem a atualização.**

1. Edite o plugin em `plugins/<nome>/`.
2. **Bumpe `version`** em `plugins/<nome>/.claude-plugin/plugin.json` (e espelhe em `marketplace.json`).
3. `claude plugin validate` — pega frontmatter inválido (`author` como string, `: `/`<>` em valores) que silenciosamente bloqueia o install.
4. Commit + push.
5. Nos clientes: `/plugin marketplace update` + `claude plugin install <nome>@pedro-plugins` (instalar ≠ atualizar índice).

---

## Licença

Uso pessoal do Pedro. Sem licença pública.
