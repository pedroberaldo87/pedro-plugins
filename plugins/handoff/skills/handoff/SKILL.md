---
name: handoff
description: Use when the session needs to be preserved for later continuation — before /clear, when conversation is getting long, when Pedro signals a pause, or after completing a major milestone. Creates a complete knowledge transfer document at {project_root}/.claude/HANDOFF.md
---

# Handoff — Preserve Session for Continuation

## Overview
Creates a complete knowledge transfer document that captures everything meaningful from the current session. The goal is to allow `/clear` + `/continue` without loss of meaning — not just state, but reasoning, decisions, context, and intent.

**This is NOT a todo list.** It's a briefing for the next Claude, written as if the reader has zero context — because they won't.

**This is NOT /wrapup.** Wrapup is a retrospective for Pedro (what went well, friction, lessons — human reflection). Handoff is an operational briefing for the next Claude (continuity of work and understanding).

## When to Suggest Proactively
- Conversation is getting long (risk of compaction losing nuance)
- Pedro signals a pause ("vamos parar", "por hoje é isso", "depois a gente continua")
- Before `/clear`
- After a major milestone (natural breakpoint)

Prompt: "Quer que eu rode o /handoff antes?"

## Why This Matters
Compaction silently removes nuance. It preserves facts but loses reasoning chains. "Decided to use Redis" survives compaction. "Decided to use Redis because we evaluated Memcached but Pedro prefers data persistence, latency is acceptable for our use case, and we have prior experience from project X" — that dies.

For Pedro specifically — someone who learns by collision — the session isn't just work output. It's a learning journey. The discussions, wrong turns, "aha" moments, and explanations of "why" ARE the value. The handoff preserves these explicitly.

## Process

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

## HANDOFF.md Format

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

## Rules
- **Completeness > brevity** — better long and complete than short with gaps. The reader has no context.
- **Preserve reasoning chains** — every decision with its "why". Every technical detail with its motivation.
- **Written for someone who knows nothing** — assume zero context in the reader.
- **Save first, ask later** — write the file immediately, then show a summary. Pedro edits after if needed.
- **Overwrites previous** — HANDOFF.md is always the snapshot of the most recent session.
- **Compatible with /continue** — the `carregar-handoff` skill expects sections like Completed, In Progress, Next Steps, Known Issues. This format is a superset of that.
- **Omit empty sections** — if there were no known issues, don't include the empty section.
- **No secrets** — never include API keys, passwords, tokens, or secret values. File paths and variable names are ok.
- **Absolute paths for external files** — when referencing files outside the project (plans, memories, global configs in `~/.claude/`), ALWAYS use the full absolute path (e.g., `/Users/pedroberaldo/.claude/plans/foo.md`). Never use `~/.claude/...` or `.claude/...` — these are ambiguous to the next Claude, who may confuse global paths with project-local ones. For files inside the project, use paths relative to the project root.
