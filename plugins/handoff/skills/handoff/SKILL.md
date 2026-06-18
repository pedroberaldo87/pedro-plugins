---
name: handoff
description: Use when preserving the session for later (before /clear, long conversation, Pedro signals a pause, after a milestone) OR when resuming work at the start of a fresh/cleared session where a .claude/HANDOFF.md exists. One command, two modes — it detects the context state (full session → save, freshly cleared → resume) and routes accordingly. Also use when Pedro says "handoff", "salva a sessão", "retoma de onde paramos", or runs /handoff with an optional [salvar|retomar] argument.
---

# Handoff — Save or Resume a Session (auto-detecting)

## Overview
A single command that preserves or restores session continuity. On invocation it detects whether you are in a **full session** (lots of accumulated work → **SAVE** a handoff) or a **fresh / freshly-cleared session** (→ **RESUME** from the last handoff). The goal is to allow `/clear` without loss of meaning — not just state, but reasoning, decisions, context, and intent.

**This is NOT a todo list.** It's a briefing for the next Claude, written as if the reader has zero context — because they won't.

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
   `<skill_dir>` é a "Base directory for this skill" injetada ao carregar a skill; o extrator vive em `lib/extract_ata.py` na raiz do plugin (dois níveis acima). O `--auto` descobre o transcript da sessão (sentinel `/tmp/claude-ata-session-*` do hook de discovery, ou o `.jsonl` mais recente do cwd) e **agrega os transcripts de teammates** se houver clã. A saída JSON traz `gate_items` (os IDs que o PRD DEVE referenciar), `log_path` e `manifest_path`.

2. **Complemente com estado de código** — `git log` e `git diff --stat` para mudanças concretas que saíram do contexto.

3. **Escreva SÓ o PRD** (`{project_root}/.claude/HANDOFF.md`) — você **não toca no LOG**. O PRD agrupa por tema o que está no LOG. Para CADA id em `gate_items`, o PRD referencia `[id]` no ponto onde aquela fala/decisão é tratada (assim o gate confirma que nada se perdeu). Findings e gotchas entram **verbatim** — não parafraseie.

4. **Atualize o índice** `{project_root}/.claude/ata/INDEX.md` — uma linha por sessão: data, `<sid>`, link pro `LOG-<sid>.md`, e uma frase do que foi a sessão.

5. **Mostre o resumo ao Pedro.** O gate de completude verifica o PRD contra o manifest; se faltar algum `gate_items`, ele te diz e você completa antes de declarar pronto.

### HANDOFF.md (PRD) Format

```markdown
# Session Handoff — PRD
Date: {YYYY-MM-DD HH:MM}
Project: {absolute path}
LOG (ata verbatim): {project_root}/.claude/ata/LOG-<sessão>.md

## Resumo
{1-3 sentences: what this session was about and where it ended}

## Contexto e Propósito
{Why this session happened. The macro objective. Each claim that came from Pedro cites its LOG id, e.g. "...montar o rito [d1]".}

## Discussões e Decisões
{Por tema. Cada decisão com seu "porquê", citando o id do LOG: "decidiu-se X [a1] porque Y, descartando Z [d6]". TODO id em gate_items aparece referenciado em alguma seção.}

## O Que Foi Feito
{Concrete actions: files created/modified, commits, configs. Com contexto do porquê.}

## Em Andamento
{What was left incomplete. Exactly where it stopped. Current state.}

## Próximos Passos
1. {Step with enough context to execute without asking "why".}

## Findings & Gotchas
{VERBATIM — descobertas técnicas e armadilhas, transcritas literais (não parafraseadas). Cite o id quando vier de uma fala/decisão.}

## Detalhes Técnicos
{Architecture, patterns, configs, file paths, dependencies, integrations.}

## Contexto Extra
{Preferences, constraints, domain insights que se perderiam sem registro.}
```

### SAVE Rules
- **O LOG é da máquina; o PRD é seu.** Nunca edite o LOG à mão. No PRD, nunca corte um direcionamento, nunca reescreva uma decisão a ponto de mudar o sentido, nunca omita um finding/gotcha.
- **Todo `gate_items` referenciado.** Cada id forte (`d`/`a`/`r`) do manifest aparece citado `[id]` no PRD. O gate bloqueia se faltar.
- **Findings & gotchas verbatim** — transcrição literal, não paráfrase (direcionamento explícito do Pedro).
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

3. **Ask for confirmation:**
   - "Esse é o estado da última sessão. Quer que eu continue de onde parou, ou tem alguma mudança de prioridade?"
   - Wait for explicit confirmation before doing anything

4. **Only then start working** — pick up from "Em Andamento" or "Próximos Passos"

### RESUME Rules
- NEVER start working before Pedro confirms
- NEVER reinterpret the handoff — follow what's written
- If the handoff seems outdated (files changed since then), flag it to Pedro
- If Pedro provides additional context that conflicts with the handoff, ask which takes priority
- Read the handoff file completely — do not skim or skip sections
