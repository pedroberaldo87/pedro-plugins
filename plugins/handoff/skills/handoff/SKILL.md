---
name: handoff
description: Use when preserving the session for later (before /clear, long conversation, Pedro signals a pause, after a milestone) OR when resuming work at the start of a fresh/cleared session where a .claude/HANDOFF.md exists. One command, two modes — it detects the context state (full session → save, freshly cleared → resume) and routes accordingly. Also use when Pedro says "handoff", "salva a sessão", "retoma de onde paramos", or runs /handoff with an optional [salvar|retomar] argument.
---

# Handoff — Save or Resume a Session (auto-detecting)

## Overview
A single command that preserves or restores session continuity. On invocation it detects whether you are in a **full session** (lots of accumulated work → **SAVE** a handoff) or a **fresh / freshly-cleared session** (→ **RESUME** from the last handoff). The goal is to allow `/clear` without loss of meaning — not just state, but reasoning, decisions, context, and intent.

**This is NOT a todo list — but it IS executable.** It's a briefing for the next Claude, written as if the reader has zero context (because they won't). Both halves carry the same rigor: the **retrospective** (what happened and why) AND the **prospective** (what's left — each step carries the requirement that makes it executable, not a label that points elsewhere). Briefing and executable plan are not rivals; a good handoff is both.

**This is NOT /wrapup.** Wrapup is a retrospective for Pedro (what went well, friction, lessons — human reflection). Handoff is an operational briefing for the next Claude (continuity of work and understanding).

## Mode Detection — run this FIRST, every time

Decide **SAVE** vs **RESUME** using these signals, in order of confidence:

1. **Current conversation history (primary — always available, guarantees a 100% fallback).** Is there substantial accumulated work in *this* session?
   - Yes (decisions, edits, a long thread) → lean **SAVE**.
   - Nearly empty (this `/handoff` is the first/early action after a `/clear` or in a brand-new session) → lean **RESUME**.

2. **`/tmp/claude-context-pct` (objective reinforcement, when present).** Read it: `cat /tmp/claude-context-pct 2>/dev/null`.
   - Missing or low (roughly below half of `$CLAUDE_CONTEXT_THRESHOLD`, default 80) → freshly cleared → **RESUME**.
   - High → full session → **SAVE**.
   - Note: context-guard's reset hook deletes this file on `/clear`/SessionStart, so a *missing* file is itself a "fresh session" signal.

3. **`.claude/HANDOFF.md` existence + mtime (guardrail).** Check it: `stat -f '%m' {project_root}/.claude/HANDOFF.md 2>/dev/null`.
   - Leaning RESUME but **no** HANDOFF.md exists → nothing to resume → switch to SAVE (or ask).
   - Leaning SAVE but HANDOFF.md was written **< 5 min ago** → suspicious (Pedro never saves two in a row) → confirm before overwriting.

**Explicit override (skips detection):**
- `/handoff salvar` (or "salva") → force **SAVE**.
- `/handoff retomar` (or "retoma") → force **RESUME**.

**Always announce the detected mode before acting**, e.g. *"Contexto em 76% / sessão cheia → vou **salvar**"* or *"Sessão limpa + HANDOFF.md de 8min atrás → vou **retomar**"*. If genuinely ambiguous, show the detected state and ask which mode Pedro wants.

---

## Mode: SAVE — Preserve the session

### When to suggest proactively
- Conversation is getting long (risk of compaction losing nuance)
- Pedro signals a pause ("vamos parar", "por hoje é isso", "depois a gente continua")
- Before `/clear`
- After a major milestone (natural breakpoint)

Prompt: "Quer que eu rode o /handoff antes?"

### Why this matters
Compaction silently removes nuance. It preserves facts but loses reasoning chains. "Decided to use Redis" survives compaction. "Decided to use Redis because we evaluated Memcached but Pedro prefers data persistence, latency is acceptable for our use case, and we have prior experience from project X" — that dies.

For Pedro specifically — someone who learns by collision — the session isn't just work output. It's a learning journey. The discussions, wrong turns, "aha" moments, and explanations of "why" ARE the value. The handoff preserves these explicitly.

### The rito: LOG (verbatim, gerado por máquina) + PRD (você escreve)

O handoff tem **dois produtos**, e a divisão de trabalho é a regra de ouro:

- **LOG** (`{project_root}/.claude/ata/LOG-<sessão>.md`) — a **ata verbatim, cronológica**. É gerada **mecanicamente pelo extrator**, NÃO por você. Cada item (fala do Pedro, decisão de AskUserQuestion, rejeição com instrução, plano, tarefa, diagrama) recebe um **ID estável** (`[d3]`, `[a1]`, `[r1]`...). É a prova: nada de julgamento, nada de resumo, nada filtrado.
- **PRD** (`{project_root}/.claude/HANDOFF.md`) — a **vista normativa, por tema**, que VOCÊ escreve a partir do LOG. É o que o RESUME lê.

Por que o extrator gera o LOG e não você: o Pedro foi explícito — *"E o seu julgamento não serve. Vai no meu julgamento. Vai anotar tudo, vai carregar tudo."* Se você escrevesse o LOG, você filtraria. Tirando você do caminho do LOG, o "anotar tudo sem julgamento" é garantido por construção.

### Process

1. **Rode o extrator** (ele gera o LOG verbatim + um manifest dos itens — mecânico):
   ```bash
   python3 "<skill_dir>/../../lib/extract_ata.py" --auto --cwd "$(pwd)" --out-dir "{project_root}/.claude/ata"
   ```
   `<skill_dir>` é a "Base directory for this skill" injetada ao carregar a skill; o extrator vive em `lib/extract_ata.py` na raiz do plugin (dois níveis acima). O `--auto` descobre o transcript da sessão (sentinel `/tmp/claude-ata-session-*` do hook de discovery, ou o `.jsonl` mais recente do cwd) e **agrega os transcripts de teammates** se houver clã. A saída JSON traz `gate_items` (os IDs que o PRD DEVE referenciar), **`prospective`** (`open_tasks` = tarefas abertas no fim, com id/subject/status reais + `last_plan` = o último ExitPlanMode), `log_path` e `manifest_path`.

2. **Complemente com estado de código** — `git log` e `git diff --stat` para mudanças concretas que saíram do contexto.

3. **Escreva SÓ o PRD** (`{project_root}/.claude/HANDOFF.md`) — você **não toca no LOG**. O PRD agrupa por tema o que está no LOG. Para CADA id em `gate_items`, o PRD referencia `[id]` no ponto onde aquela fala/decisão é tratada (assim o gate confirma que nada se perdeu). Findings e gotchas entram **verbatim** — não parafraseie.
   - **Pré-preencha o prospecto a partir de `prospective`** (não escreva do zero quando há material): cada `open_tasks[i]` vira um passo de `## Próximos Passos` com os 5 campos. O `last_plan` depende do flag `likely_executed`:
     - `likely_executed: true` (houve commits/edits depois do plano) → **o plano JÁ foi executado nesta sessão.** Ele vira REGISTRO em `## O Que Foi Feito`, **NÃO** entra em `## Próximos Passos`. (Senão o próximo Claude acha que tem de reimplementar tudo.)
     - `likely_executed: false` → é candidato a próximos passos; refine-o como tal.
     - Refine o que o extrator deu; não o ignore.

4. **Atualize o índice** `{project_root}/.claude/ata/INDEX.md` — uma linha por sessão: data, `<sid>`, link pro `LOG-<sid>.md`, e uma frase do que foi a sessão.

5. **Mostre o resumo ao Pedro.** O gate de completude verifica o PRD contra o manifest; se faltar algum `gate_items`, ele te diz e você completa antes de declarar pronto.

### HANDOFF.md (PRD) Format

```markdown
# Session Handoff — PRD
Date: {{AAAA-MM-DD HH:MM}}
Project: {{caminho absoluto do projeto}}
LOG (ata verbatim): {{project_root}}/.claude/ata/LOG-{{sessão}}.md

## Resumo
{{1-3 frases: do que foi a sessão e onde ela parou}}

## Contexto e Propósito
{{por que a sessão aconteceu, o objetivo macro; cada afirmação que veio do Pedro cita o id do LOG, ex: "...montar o rito [d1]"}}

## Discussões e Decisões
{{por tema; cada decisão com o "porquê", citando o id do LOG: "decidiu-se X [a1] porque Y, descartando Z [d6]". TODO id em gate_items aparece referenciado em alguma seção}}

## O Que Foi Feito
{{ações concretas: arquivos criados/modificados, commits, configs — com o contexto do porquê}}

## Em Andamento
{{o que ficou pela metade e exatamente onde parou; estado atual — ou "nada pendente" se a sessão fechou tudo}}

## Próximos Passos
<!-- Um passo = um bloco "### N." com os 5 campos abaixo. O extrator pré-preenche aqui as
     tarefas abertas + o último plano (campo `prospective` do JSON). Passo trivial (deploy quando
     o Pedro mandar, etc.): marque "(trivial)" no fim do título e use UMA linha, sem os 5 campos. -->

### 1. {{título curto do passo}}
- **Ação:** {{o que fazer concretamente}}
- **Critério de pronto:** {{como sei que terminou}}
- **Problema:** {{1 linha humana — o que falta ou está errado}}
- **Arquivos prováveis:** {{paths}}
- **Decisão em aberto:** {{as opções — ou "nenhuma"}}

### 2. {{título do passo trivial}} (trivial)
{{uma linha — passos triviais dispensam os 5 campos}}

## Findings & Gotchas
{{VERBATIM — descobertas técnicas e armadilhas, transcritas literais (não parafraseadas). Cite o id quando vier de uma fala/decisão}}

## Detalhes Técnicos
{{arquitetura, padrões, configs, paths, dependências, integrações}}

## Contexto Extra
{{preferências, constraints, domain insights que se perderiam sem registro}}
```

### Exemplo de "Próximos Passos" preenchido (o alvo — sem `{{}}`)

```markdown
### 1. Migrar o endpoint /sync para cursor-based pagination
- **Ação:** trocar offset/limit por cursor em `api/sync.ts:120`; cursor = `updated_at` do último item.
- **Critério de pronto:** `npm test -- sync.spec` passa e 3 páginas devolvem 0 duplicatas.
- **Problema:** offset pula itens em insert concorrente — bug reportado em produção.
- **Arquivos prováveis:** `api/sync.ts`, `api/sync.spec.ts`, migration nova.
- **Decisão em aberto:** manter offset como fallback por 1 release, ou cortar direto?

### 2. Subir a doc atualizada pro Notion (trivial)
Rodar `npm run docs:push` quando o PR mergear.
```

### SAVE Rules
- **O LOG é da máquina; o PRD é seu.** Nunca edite o LOG à mão. No PRD, nunca corte um direcionamento, nunca reescreva uma decisão a ponto de mudar o sentido, nunca omita um finding/gotcha.
- **Todo `gate_items` referenciado.** Cada id forte (`d`/`a`/`r`) do manifest aparece citado `[id]` no PRD. O gate bloqueia se faltar.
- **Findings & gotchas verbatim** — transcrição literal, não paráfrase (direcionamento explícito do Pedro).
- **Próximos Passos executável, não ponteiro.** Se um passo referencia outro documento, transcreva o essencial inline. Se o documento referenciado **também** não especifica a ação (só lista/menciona), o passo honesto é **"destilar a spec primeiro"** — não "ver doc X". Cada passo não-trivial carrega os 5 campos do molde; passo trivial usa o escape `(trivial)`. O teste: um terceiro executa o passo sem abrir outro doc nem fazer arqueologia.
- **Handoff de implementação CONCLUÍDA é registro, não ordem de refazer.** Se a sessão terminou de implementar algo (sinal: `last_plan.likely_executed: true`, ou você sabe que o plano virou código/commits): o grosso vai pra `## O Que Foi Feito`; `## Em Andamento` = "nada pendente"; `## Próximos Passos` só os follow-ups REAIS que sobraram (deploy, testes, decisões abertas) — **nunca** o plano que você acabou de executar. O PRD + o LOG juntos são o REGISTRO do que foi feito; quem retomar não deve reimplementar.
- **Completeness > brevity** — o PRD é granular; melhor longo e completo que curto com lacunas.
- **PRD é snapshot, sobrescrito; o LOG é histórico, append-only por sessão.** O git guarda o histórico do PRD; os `LOG-<sid>.md` guardam cada sessão.
- **Save first, ask later** — escreva, depois mostre o resumo. Pedro edita o PRD se quiser (o LOG, não).
- **No secrets** — nunca inclua API keys, senhas, tokens. Paths e nomes de variável ok.
- **Absolute paths for external files** — ao referenciar arquivos fora do projeto (`~/.claude/...`), use o caminho absoluto completo (`/Users/pedroberaldo/.claude/...`), nunca `~/.claude/...` ou `.claude/...`.

---

## Mode: RESUME — Pick up from the last handoff

Reads the handoff document from a previous session and presents it to Pedro for confirmation before taking any action.

### Process

1. **Find the handoff file:**
   - Check `{project_root}/.claude/HANDOFF.md` (the PRD — read this first)
   - The verbatim ata lives in `{project_root}/.claude/ata/LOG-<sessão>.md` (index in `INDEX.md`). The PRD references LOG ids like `[d3]`; open the LOG when you need the exact wording behind a reference.
   - If not found, check recent git log and git status for clues about the last session
   - If nothing found, tell Pedro and ask for context

2. **Present the summary (with its age):**
   - Show how long ago the handoff was written (from its mtime)
   - Show what was completed
   - Show what's in progress and where it stopped
   - Show next steps
   - Show known issues
   - If the handoff is old (files changed since then, or many days passed), flag it

3. **Valide o prospecto e recupere o que falta — ANTES de pedir confirmação (ativo, não passivo).**
   - Para cada item de "Próximos Passos": tem os 5 campos preenchidos (ou é `(trivial)`)? Um terceiro executaria sem abrir outro doc?
   - Se algum passo está **magro** (aponta pra outro doc sem a spec inline, ou falta Ação/Critério de pronto): **NÃO execute a partir da menção.** Faça a arqueologia primeiro — abra o LOG pelos `[id]`, o `last_plan`, o doc referenciado, rode `git diff` — e **monte um plano de recuperação concreto** (o que abrir, o que inspecionar, qual a ação real). Converta o passo magro num passo executável você mesmo.
   - Isso é a régua do Pedro: recuperar decisões/contexto ANTES de decidir ou executar trabalho continuado. O custo do prospecto fraco recai no RESUME — pague-o aqui, não no meio da execução.

4. **Ask for confirmation:**
   - "Esse é o estado da última sessão. Quer que eu continue de onde parou, ou tem alguma mudança de prioridade?"
   - Wait for explicit confirmation before doing anything

5. **Reconcilie com o código real ANTES de executar — depois trabalhe.** Antes de tocar em qualquer "Próximo Passo", rode `git log --oneline -10` + `git status` e leia os arquivos que o passo cita. Se o que o passo descreve **já está no código / já foi commitado** (caso típico: o handoff foi tirado logo após uma implementação concluída), **NÃO reimplemente** — reconheça como feito e siga só pro que de fato falta. O handoff é um REGISTRO do que aconteceu, não uma ordem de refazer. Só então pegue de "Em Andamento" / "Próximos Passos".

### RESUME Rules
- NEVER start working before Pedro confirms
- NEVER reinterpret the handoff — follow what's written
- If the handoff seems outdated (files changed since then), flag it to Pedro
- If Pedro provides additional context that conflicts with the handoff, ask which takes priority
- Read the handoff file completely — do not skim or skip sections
- **Prospecto magro → arqueologia ativa, não pergunta passiva.** Se um próximo passo aponta pra fora ou falta campo, recupere o contexto (LOG, `last_plan`, doc referenciado, `git diff`) e monte o plano de recuperação ANTES de apresentar — não devolva a lacuna pro Pedro como pergunta.
- **NUNCA reimplemente o que já está feito.** Handoff de implementação concluída é registro. Sempre confira `git log`/`git status` e o código antes de executar um passo; se já existe, marque feito e siga. Na dúvida entre "refazer" e "já está pronto", leia o código — não refaça.
