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

### Process

1. **Review the entire conversation** — analyze the full session history, identifying:
   - Purpose and objective of the session
   - Discussions and their conclusions
   - Decisions made and their complete reasoning (why yes, why not the alternatives)
   - Technical details that matter
   - Problems encountered and how they were resolved
   - Pedro's learning moments and insights
   - Preferences Pedro expressed, constraints mentioned

2. **Complement with code state** — run `git log` and `git diff --stat` to capture concrete changes that may have scrolled out of context

3. **Compose and save the HANDOFF.md** — follow the format below, prioritizing **completeness over brevity**. The next Claude needs to reconstruct the full mental model from this document alone. Write directly to `{project_root}/.claude/HANDOFF.md`.

4. **Show summary to Pedro** — present a brief summary of what was captured. Pedro can request changes after reviewing — the file is already saved and editable.

### HANDOFF.md Format

```markdown
# Session Handoff
Date: {YYYY-MM-DD HH:MM}
Project: {absolute path}

## Resumo
{1-3 sentences: what this session was about and where it ended}

## Contexto e Propósito
{Why this session happened. The macro objective. What Pedro is trying to do/learn/solve. Enough context for the next Claude to understand the motivation without asking.}

## Discussões e Decisões
{What was discussed. Decisions made with complete reasoning — not just "decided X", but "decided X because Y, discarding Z because of W". Alternatives considered and why they were rejected. Each decision must make sense to a reader with zero context.}

## O Que Foi Feito
{Concrete actions: files created/modified, commits, configurations changed. With enough context to understand why each change was made.}

## Em Andamento
{What was left incomplete. Exactly where it stopped. Current state — what works, what doesn't yet.}

## Próximos Passos
1. {Step with enough context to execute without asking "why are we doing this?"}
2. ...

## Problemas Conhecidos
{Bugs, gotchas, warnings, limitations discovered during the session.}

## Detalhes Técnicos
{Architecture, patterns used, important configs, relevant file paths, dependencies, integrations. Everything the next Claude needs to work on the code.}

## Contexto Extra
{Anything that doesn't fit above but would be lost without recording. Preferences Pedro expressed, constraints mentioned, domain insights.}
```

### SAVE Rules
- **Completeness > brevity** — better long and complete than short with gaps. The reader has no context.
- **Preserve reasoning chains** — every decision with its "why". Every technical detail with its motivation.
- **Written for someone who knows nothing** — assume zero context in the reader.
- **Save first, ask later** — write the file immediately, then show a summary. Pedro edits after if needed.
- **Overwrites previous** — HANDOFF.md is always the snapshot of the most recent session. But if the existing file is < 5 min old, confirm first (see Mode Detection guardrail).
- **The RESUME side expects** sections like Resumo, Em Andamento, Próximos Passos, Problemas Conhecidos — this format is a superset of that.
- **Omit empty sections** — if there were no known issues, don't include the empty section.
- **No secrets** — never include API keys, passwords, tokens, or secret values. File paths and variable names are ok.
- **Absolute paths for external files** — when referencing files outside the project (plans, memories, global configs in `~/.claude/`), ALWAYS use the full absolute path (e.g., `/Users/pedroberaldo/.claude/plans/foo.md`). Never use `~/.claude/...` or `.claude/...` — these are ambiguous to the next Claude, who may confuse global paths with project-local ones. For files inside the project, use paths relative to the project root.

---

## Mode: RESUME — Pick up from the last handoff

Reads the handoff document from a previous session and presents it to Pedro for confirmation before taking any action.

### Process

1. **Find the handoff file:**
   - Check `{project_root}/.claude/HANDOFF.md`
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
