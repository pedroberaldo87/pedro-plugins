---
name: handoff-continue
description: Use ONLY when the user explicitly says "continue", "continua", or "/continue" to resume from a handoff file. Do NOT use when the user resumes a conversation (Claude resume feature) — resumed conversations already have their context, no handoff loading needed
---

# Continue — Resume From Handoff

## Overview
Reads the handoff document from a previous session and presents it to the user for confirmation before taking any action.

## Process

1. **Find the handoff file:**
   - Check `{project_root}/.claude/HANDOFF.md`
   - If not found, check recent git log and git status for clues about last session
   - If nothing found, tell the user and ask for context

2. **Present the summary:**
   - Show what was completed
   - Show what's in progress and where it stopped
   - Show next steps
   - Show known issues

3. **Ask for confirmation:**
   - "Esse é o estado da última sessão. Quer que eu continue de onde parou, ou tem alguma mudança de prioridade?"
   - Wait for explicit confirmation before doing anything

4. **Only then start working** — pick up from "In Progress" or "Next Steps"

## Rules
- NEVER start working before the user confirms
- NEVER reinterpret the handoff — follow what's written
- If the handoff seems outdated (files changed since then), flag it to the user
- If the user provides additional context that conflicts with the handoff, ask which takes priority
- Read the handoff file completely — do not skim or skip sections
