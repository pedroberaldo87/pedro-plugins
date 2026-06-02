# pedro-plugins

Marketplace privado de plugins Claude Code do Pedro. Monorepo — cada subdiretório em `plugins/` é um plugin independente distribuído via este marketplace.

## Plugins disponíveis

3 plugins rodam automaticamente via hooks (marcados com ⚙️). Os demais são invocados sob demanda via slash command.

### Produtividade & Sessão

| Plugin | Trigger | O que faz |
|---|---|---|
| ⚙️ `bootstrap-third-party` | `/bootstrap-third-party` ou automático no SessionStart | Sincroniza marketplaces e plugins de terceiros entre máquinas via git. Declarativo (manifest.json). |
| ⚙️ `visual` | `/visual` ou automático em planos/diagnósticos | Transforma textão do CLI em HTML dark-theme interativo. Abre no browser com live sync via daemon local. Modo auto renderiza planos (3+ itens), decisões (2+ opções) e diagnósticos (3+ problemas) sem precisar invocar. |
| ⚙️ `context-guard` | Automático (PostToolUse) — setup via `/context-guard:setup` | Auto-interrompe o workflow quando o context window ultrapassa threshold configurável (default: 80%). Agnóstico de statusLine — encaminha para qualquer comando existente via `CLAUDE_STATUSLINE_FORWARD`. Quando dispara, sugere `/handoff`. **Requer `handoff` instalado.** |
| `handoff` | `/handoff` (detecta: salva ou retoma) · override `/handoff salvar\|retomar` | Comando único de continuidade: detecta o estado da sessão — contexto cheio → salva `.claude/HANDOFF.md`; sessão recém-limpa → retoma de onde parou. |
| `sovai` | `/sovai` | Modo autônomo — executa plano até o fim sem pausas, checkpoints ou confirmações. Toma decisões e anota cada uma. Bloqueios são pulados e registrados, não resolvidos com workarounds silenciosos. Entrega relatório estruturado. |
| `project-doc` | `/project-doc` | Gera um bloco de referência estruturado em `.claude/CLAUDE.md` (stack, portas, env, deploy, DB, gotchas). Detecta monorepo vs standard e roda verificação pós-geração. |

### Qualidade & Review

| Plugin | Trigger | O que faz |
|---|---|---|
| `rev6` | `/rev6` | Dispara 6 agentes voltagent em paralelo (architect, backend, frontend, fullstack, code-reviewer, UX) pra review multi-ângulo. |
| `qa` | `/qa <path-do-plano>` | Audita implementação contra um plano com 4 agentes especialistas em paralelo. Repete até zero findings P0/P1. |
| `grill-me` | `/grill-me` | Entrevista implacável uma pergunta por vez sobre um plano/design até esgotar a árvore de decisões. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `grill-with-docs` | `/grill-with-docs` | Igual ao grill-me, mas confronta contra o domain model existente (CONTEXT.md, ADRs). Atualiza docs inline conforme decisões cristalizam. *Por [Matt Pocock](https://github.com/mattpocock/skills).* |
| `principles` | `/principles` | Carrega princípios de sistema do projeto (PRINCIPIOS-SISTEMAS.md), mapeia categorias relevantes ao contexto, gera guia com WHY + HOW. Dois modos: planning e review. |

### Dev & Deploy

| Plugin | Trigger | O que faz |
|---|---|---|
| `ship` | `/ship` | Lint → type-check → commit → push → deploy em fluxo disciplinado. |
| `iterate` | `/iterate` | Loop de convergência autônoma — faz mudança atômica + verificação até o comando de verificação passar. Contrato duro: exige resultado verificável + meio de verificar. |
| `improve` | `/improve` | Implementa rodada de melhoria iterativa lendo `IMPROVEMENT_PROGRAM.md` + issues GitHub com label `autoresearch`. Genérico — funciona com qualquer app que siga a metodologia. |

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

```bash
# 1. Adicionar o marketplace + instalar bootstrap
claude plugin marketplace add git@github.com:pedroberaldo87/pedro-plugins.git
claude plugin install bootstrap-third-party@pedro-plugins

# 2. Bootstrap lê manifest.json e instala terceiros + pessoais
# (roda automaticamente no SessionStart, ou manualmente via skill)
```

## Desenvolvendo o marketplace localmente

Clone o repo:

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

### Anatomia de um plugin

```
plugins/<nome>/
├── .claude-plugin/plugin.json   # Identidade: nome, versão, descrição, autor
├── hooks.json                   # (opcional) Hooks automáticos (SessionStart, PostToolUse, PreToolUse)
├── hooks/                       # (opcional) Scripts dos hooks
└── skills/<nome>/
    └── SKILL.md                 # Instrução completa da skill
```

Plugins com hooks: **bootstrap-third-party** (SessionStart + PostToolUse), **visual** (PreToolUse em ExitPlanMode), **context-guard** (SessionStart + PostToolUse).

## Licença

Uso pessoal do Pedro. Sem licença pública.
