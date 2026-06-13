---
generated: 2026-06-13
project: pedro-plugins
scope: .claude-plugin/marketplace.json, plugins/*/plugin.json, plugins/*/hooks.json
---

# Architecture

## Visão Geral
Marketplace privado de plugins Claude Code do Pedro. 17 plugins independentes (skills, hooks, automações) distribuídos via `.claude-plugin/marketplace.json`. Qualquer máquina instala com `claude plugin install`.

## Stack
- **Linguagem:** Shell (hooks), Markdown (skills)
- **Runtime:** Claude Code plugin system
- **Hosting:** GitHub (`pedroberaldo87/pedro-plugins`)
- **Package manager:** nenhum — sem build, sem lockfiles

## Estrutura de Diretórios
```
pedro-plugins/
├── .claude-plugin/marketplace.json   # índice do marketplace (17 plugins)
├── plugins/                          # cada subdir = 1 plugin independente
│   ├── bootstrap-third-party/        # ⚙️ hooks: SessionStart, PostToolUse
│   ├── context-guard/                # ⚙️ hooks: SessionStart, PostToolUse
│   ├── fallow/
│   ├── grill-me/                     # por Matt Pocock
│   ├── grill-with-docs/              # por Matt Pocock
│   ├── handoff/
│   ├── improve/
│   ├── iterate/
│   ├── principles/
│   ├── project-doc/
│   ├── qa/
│   ├── raiox/                        # pipeline YouTube (VIU Studio)
│   ├── rev6/
│   ├── ship/                         # ⚙️ hook: PreToolUse (Bash)
│   ├── slides/
│   ├── sovai/
│   └── visual/                       # ⚙️ hook: PreToolUse (ExitPlanMode)
└── README.md
```

## Anatomia de um Plugin
```
plugins/<nome>/
├── .claude-plugin/plugin.json    # identidade: nome, versão, descrição, autor
├── hooks.json                    # (opcional) hooks automáticos
├── hooks/                        # (opcional) scripts dos hooks
└── skills/<nome>/
    └── SKILL.md                  # instrução completa da skill
```

## Plugins com Hooks Automáticos
- **bootstrap-third-party** — `SessionStart`: sincroniza plugins via manifest.json · `PostToolUse`: detecta comandos `claude plugin`
- **context-guard** — `SessionStart`: reseta sentinel · `PostToolUse`: lê `/tmp/claude-context-pct`, bloqueia se > threshold
- **ship** — `PreToolUse (Bash)`: bloqueia deploy se testes falham
- **visual** — `PreToolUse (ExitPlanMode)`: força renderização HTML do plano antes de apresentar ao usuário

## Catálogo dos 17 Plugins

Produtividade:
- **bootstrap-third-party** v0.1.2 — auto-sync marketplaces e plugins entre máquinas via manifest.json declarativo
- **context-guard** v1.1.0 — interrompe workflow ao ultrapassar threshold de contexto (default 80%)
- **handoff** v1.3.0 — continuidade de sessão: salva ou retoma `.claude/HANDOFF.md` num único comando
- **project-doc** v2.2.0 — gera sistema de documentação CLAUDE.md + `.claude/docs/` modular
- **slides** v1.0.0 — outline Markdown → deck HTML keynote-grade single-file
- **sovai** v1.0.0 — modo autônomo sem interrupções; pula itens bloqueados e anota
- **visual** v1.0.0 — CLI textão → HTML dark-theme com live sync via daemon local

Dev Tools:
- **fallow** v1.0.2 — análise estática JS/TS (dead code, duplicação, complexidade) com report interativo
- **grill-me** v1.0.0 — design review implacável uma pergunta por vez (Matt Pocock)
- **grill-with-docs** v1.0.0 — design review contra domain model existente, atualiza CONTEXT.md/ADRs inline (Matt Pocock)
- **improve** v1.0.0 — implementa melhorias via GitHub Issues com label `autoresearch`
- **iterate** v1.0.0 — loop autônomo até verificação passar (contrato: resultado verificável + comando de verif.)
- **principles** v1.0.0 — princípios de sistema mapeados ao contexto atual, guia WHY + HOW
- **qa** v1.0.0 — auditoria implementação vs plano via 4 agentes especialistas paralelos
- **raiox** v0.2.0 — pipeline de inteligência de canal YouTube para VIU Studio (fetch → DuckDB → 7 módulos → validate)
- **rev6** v1.0.0 — code review multi-ângulo via 6 agentes voltagent em paralelo
- **ship** v1.0.0 — lint → typecheck → commit → push → deploy em sequência disciplinada

## Terceiros Gerenciados (via bootstrap-third-party)
Manifest em `plugins/bootstrap-third-party/skills/bootstrap-third-party/manifest.json`:
- **claude-hud** — statusLine no terminal
- **claude-plugins-official** (Anthropic) — code-review, context7, figma, playwright, superpowers, etc.
- **obsidian-skills** — integração Obsidian
- **openai-codex** — bridge pro Codex
- **voltagent-subagents** — 57 subagentes especialistas (biz, core-dev, data-ai, qa-sec, research)
