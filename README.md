# pedro-plugins

Marketplace privado de plugins Claude Code do Pedro. Monorepo — cada subdiretório em `plugins/` é um plugin independente distribuído via este marketplace.

## Plugins disponíveis

### Produtividade & Workflow

| Plugin | O que faz | Ideal pra |
|---|---|---|
| `bootstrap-third-party` | Sincroniza marketplaces e plugins de terceiros entre máquinas via git. Declarativo (manifest.json). | Restaurar todo seu ambiente Claude Code numa máquina nova com 1 comando |
| `visual` | Transforma textão do CLI em HTML dark-theme interativo. Abre no browser com live sync via daemon local. | Planos, diagnósticos e decisões que você escaneia em 30s em vez de rolar 20 páginas no terminal |
| `handoff` | Ciclo completo de continuidade: cria `.claude/HANDOFF.md` no fim da sessão e carrega de volta na próxima (via "continue" / `/continue`) pra retomar exatamente de onde parou. | Fim de sessão longa, antes de `/clear`, e início da sessão seguinte pra recuperar contexto |
| `sovai` | Modo autônomo — executa plano até o fim sem pausas, checkpoints ou confirmações. Toma decisões, loga tudo, entrega relatório estruturado. | Tarefas multi-etapa quando Pedro não está disponível pra responder |
| `context-guard` | Auto-interrompe o workflow quando o context window ultrapassa threshold configurável. Ponte entre statusLine e PostToolUse hooks via temp file. | Evitar que sessões longas percam contexto sem aviso |

### Qualidade & Review

| Plugin | O que faz | Ideal pra |
|---|---|---|
| `rev6` | Dispara 6 agentes voltagent em paralelo (architect, backend, frontend, fullstack, code-reviewer, UX) pra review multi-ângulo. | Feedback multi-lente em feature nova antes de ship |
| `qa` | Audita implementação contra um plano com 4 agentes especialistas em paralelo. Repete via /goal até 100% aderente. | Garantir que a implementação está 100% fiel ao plano |
| `grill-me` | Entrevista implacável uma pergunta por vez sobre um plano/design até esgotar a árvore de decisões. *Por [Matt Pocock](https://github.com/mattpocock/skills).* | Stress-test de planos e decisões antes de implementar |
| `grill-with-docs` | Igual ao grill-me, mas confronta contra o domain model existente (CONTEXT.md, ADRs). Atualiza docs inline conforme decisões cristalizam. *Por [Matt Pocock](https://github.com/mattpocock/skills).* | Validar plano contra a linguagem e decisões documentadas do projeto |
| `principles` | Carrega princípios de sistema do projeto (PRINCIPIOS-SISTEMAS.md), mapeia categorias relevantes ao contexto, gera guia com WHY + HOW. Dois modos: planning e review. | Planejar ou revisar com princípios de arquitetura do projeto |

### Dev & Deploy

| Plugin | O que faz | Ideal pra |
|---|---|---|
| `ship` | Lint → type-check → commit → push → deploy em fluxo disciplinado. | Quando uma feature está pronta pra produção |
| `improve` | Implementa rodada de melhoria iterativa lendo `IMPROVEMENT_PROGRAM.md` + issues GitHub com label `autoresearch`. | Loops de auto-pesquisa/improvement em apps ML |
| `iterate` | Loop de convergência autônoma — faz mudança atômica + verificação até o comando de verificação passar. Capped, logado, respeita princípios. | Convergir em um comportamento alvo com ciclo tight de change→verify |
| `project-doc` | Gera um bloco de referência estruturado em `.claude/CLAUDE.md` (stack, portas, env, deploy, DB, gotchas). Detecta monorepo vs standard e roda verificação pós-geração. | Entrar num projeto sem `CLAUDE.md` ou atualizar depois de mudanças estruturais |

## Instalação (em qualquer máquina)

### Fluxo rápido (pegar só o que quiser)

```bash
# 1. Adicionar o marketplace
claude plugin marketplace add git@github.com:pedroberaldo87/pedro-plugins.git

# 2. Instalar os plugins que você quiser
claude plugin install visual@pedro-plugins
claude plugin install rev6@pedro-plugins
# etc.
```

### Fluxo completo (restaurar todo o setup de uma vez)

Se você for o Pedro (ou qualquer pessoa que queira o setup inteiro: plugins de terceiros + skills pessoais):

```bash
# 1. Adicionar o marketplace + instalar bootstrap
claude plugin marketplace add git@github.com:pedroberaldo87/pedro-plugins.git
claude plugin install bootstrap-third-party@pedro-plugins

# 2. Bootstrap lê manifest.json e instala terceiros + pessoais
# (roda automaticamente no SessionStart, ou manualmente via skill)
```

## Desenvolvendo o marketplace localmente

Se for contribuir com plugins novos ou editar os existentes, clone o repo:

```bash
git clone git@github.com:pedroberaldo87/pedro-plugins.git ~/PROGRAMACAO/PEDRO/pedro-plugins
```

O `bootstrap-third-party` detecta automaticamente se o repo está clonado localmente e adapta o comportamento:
- **Com repo**: pode fazer `snapshot` (máquina → manifest, commit, push).
- **Sem repo**: só `apply` (manifest → máquina).

Pra usar outro caminho além de `~/PROGRAMACAO/PEDRO/pedro-plugins`:

```bash
export PEDRO_PLUGINS_REPO="/caminho/alternativo/pedro-plugins"
```

## Estrutura

```
pedro-plugins/
├── .claude-plugin/
│   └── marketplace.json              # Index do marketplace (lista todos os plugins)
├── plugins/
│   ├── bootstrap-third-party/        # Sync declarativo de plugins de terceiros
│   │   ├── .claude-plugin/plugin.json
│   │   ├── hooks.json
│   │   ├── hooks/
│   │   └── skills/bootstrap-third-party/
│   │       ├── SKILL.md
│   │       └── manifest.json         # Fonte de verdade: quais terceiros + pessoais
│   ├── context-guard/                # Auto-interrupt por limite de contexto
│   │   ├── .claude-plugin/plugin.json
│   │   ├── hooks.json
│   │   ├── hooks/
│   │   └── skills/setup/
│   ├── grill-me/                     # Stress-test de planos via entrevista
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/grill-me/
│   ├── grill-with-docs/              # Stress-test + confronto com docs do projeto
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/grill-with-docs/
│   │       ├── SKILL.md
│   │       ├── ADR-FORMAT.md
│   │       └── CONTEXT-FORMAT.md
│   ├── handoff/                      # Session continuity cycle (create + load)
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/
│   │       ├── handoff/              # Cria HANDOFF.md
│   │       └── carregar-handoff/     # Carrega HANDOFF.md na sessão seguinte
│   ├── improve/                      # Autoresearch improvement loop
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/improve/
│   ├── iterate/                      # Convergência autônoma change→verify
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/iterate/
│   ├── principles/                   # Princípios de sistema contextuais
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/principles/
│   │       ├── SKILL.md
│   │       ├── index.md
│   │       └── PRINCIPIOS-SISTEMAS.md
│   ├── project-doc/                  # Auto-generate project CLAUDE.md
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/project-doc/
│   ├── qa/                           # Auditoria multi-agente contra plano
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/qa/
│   ├── rev6/                         # Multi-angle code review (6 agentes)
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/rev6/
│   ├── ship/                         # Production deploy flow
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/ship/
│   ├── sovai/                        # Execução autônoma sem interrupção
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/sovai/
│   └── visual/                       # HTML visual views com live sync
│       ├── .claude-plugin/plugin.json
│       ├── hooks.json
│       ├── hooks/
│       ├── server/                   # Daemon Node pra live sync (zero deps)
│       └── skills/visual/
│           ├── SKILL.md
│           ├── config.default.json
│           └── template.html
└── README.md
```

## Licença

Uso pessoal do Pedro. Sem licença pública.
