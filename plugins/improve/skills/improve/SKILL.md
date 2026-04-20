---
name: improve
description: Generic self-improvement implementer for any app using the autoresearch ML methodology. Reads the app's IMPROVEMENT_PROGRAM.md for context, fetches proposals from GitHub Issues (label 'autoresearch'), implements changes. Use with "improve", "melhoria", "rodada de improvement".
---

# Improve — Generic Self-Improvement Implementer

## Overview

A generic skill that implements improvement proposals for ANY app following the autoresearch ML methodology. The skill knows HOW to implement — the app's `IMPROVEMENT_PROGRAM.md` knows WHAT to implement.

**This skill is app-agnostic.** All app-specific knowledge lives in the app's documentation.

## How It Works

```
┌──────────────────────────────┐     ┌──────────────────────────────┐
│  /improve (this skill)       │     │  App's IMPROVEMENT_PROGRAM.md│
│  ─────────────────────       │     │  ─────────────────────────── │
│  Generic implementer:        │────▶│  App-specific context:       │
│  • Read docs                 │     │  • Objectives per stage      │
│  • Fetch GitHub Issues       │     │  • What's tunable            │
│  • Implement changes         │     │  • What's immutable          │
│  • Lint, commit, deploy      │     │  • API endpoints             │
│  • Close issues              │     │  • How to diagnose           │
└──────────────────────────────┘     │  • How to evaluate           │
                                     │  • Safety rules              │
                                     └──────────────────────────────┘
```

## Process

### 1. Find the App's Program

Look for `IMPROVEMENT_PROGRAM.md` in the current working directory or in any `apps/*/` subdirectory. This file is REQUIRED — if it doesn't exist, tell the user they need to create one for their app.

```bash
# Look for program files
find . -name "IMPROVEMENT_PROGRAM.md" -maxdepth 3
```

If multiple are found (monorepo), ask the user which app to improve. If only one, use it.

**Read the entire IMPROVEMENT_PROGRAM.md before doing anything.** It contains:
- The app's objectives and metrics
- What files can be modified and what files are IMMUTABLE
- API endpoints for health/status
- How to diagnose issues
- How to generate proposals
- Safety rules

### 2. Fetch Status

Use the health/status endpoints documented in the program file to show current state:
- Overall score / health metric
- Per-stage or per-component scores
- Trend (improving / declining / stable)
- Active proposal status (if any)

Present a concise summary to the user.

### 3. Check GitHub Issues

```bash
gh issue list --repo {repo} --label autoresearch --state open --json number,title,body,labels
```

Where `{repo}` is determined from git remote (`git remote get-url origin`).

**If open issues exist:** List them with number + title. Ask user which to implement.

**If no open issues exist:** Offer two options:
- Generate a new proposal: call the proposal generation endpoint from the program file. The API response includes a `github_issue` field with pre-formatted `title` and `body`. Use `gh issue create` to create the issue from this data.
- Let the user describe what they want to improve manually

### 4. Implement the Change

Read the selected GitHub Issue body. Issues follow this structure:

```markdown
## Diagnosis
- **Target:** {component/stage}
- **Current score:** {score}
- **Hypothesis:** {what we think will improve}

## Change Type
config | code

## Config Changes
| Parameter | Current | Proposed |
|-----------|---------|----------|
| key | old | new |

## Code Changes
{description of what to change}

---
*App: {app_name}*
*Proposal ID: {id}*
```

**For config changes:**
1. Show the proposed changes
2. Confirm with user
3. Apply via the API endpoint documented in the program file
4. No deploy needed (config is read from DB at runtime)

**For code changes:**
1. Read the IMPROVEMENT_PROGRAM.md to understand what files are editable
2. Read the relevant source files
3. Implement the change described in the issue
4. **NEVER modify files listed as IMMUTABLE in the program**
5. Show the diff to the user
6. Confirm before committing
7. Lint using the project's lint tools (read from CLAUDE.md or pyproject.toml)
8. Commit: `improve({app}): {short description} (closes #{issue_number})`
9. Push + deploy using the project's deploy method

### 5. Close the Issue

- Code changes: commit message `closes #N` auto-closes
- Config changes: close manually with a comment describing what was applied

```bash
gh issue close {N} --comment "Applied via /improve. {summary of change}"
```

### 6. Post-Implementation

Remind the user based on what the program file says about evaluation:
- How many runs are needed before evaluation
- How to trigger runs (if documented)
- How to check results later (`/improve status`)

## Subcommands

### `/improve` (default)
Full cycle: read program → show status → pick issue → implement → deploy

### `/improve status`
Read program → show current scores + active proposal progress. No implementation.

### `/improve history`
Show past improvement rounds from the app's history endpoint.

## Creating a GitHub Issue from a Proposal

When the app generates a proposal (via API), create a GitHub Issue:

```bash
gh issue create \
  --repo {repo} \
  --title "[improve:{app}:{stage}] {short hypothesis}" \
  --label autoresearch \
  --body "$(cat <<'EOF'
## Diagnosis
- **Target:** {stage} (score: {score})
- **Combined score:** {combined}
- **Trend:** {trend}

## Change Type
{config|code}

## Proposal
**Hypothesis:** {hypothesis}

### Config Changes
| Parameter | Current | Proposed |
|-----------|---------|----------|
{param_table}

### Code Changes
{code_description}

---
*App: {app_name}*
*Proposal ID: {proposal_id}*
*Run `/improve` in Claude Code CLI to implement*
EOF
)"
```

## What This Skill Does NOT Do

- Does NOT contain app-specific logic — all context comes from the program file
- Does NOT modify files marked as IMMUTABLE in the program
- Does NOT auto-implement without user confirmation
- Does NOT skip lint or deploy verification
- Does NOT evaluate results — the app's pipeline does that automatically

## Writing an IMPROVEMENT_PROGRAM.md

For app developers who want to use this skill, your `IMPROVEMENT_PROGRAM.md` must include:

1. **Architecture** — What executes vs what evaluates (separation of concerns)
2. **Editable files** — List of files the improvement agent CAN modify
3. **Immutable files** — List of files that MUST NOT be modified (evaluator, scorecard, etc.)
4. **API endpoints** — Health, proposals, params, approve/reject URLs
5. **Objectives per stage/component** — What each part should achieve
6. **Metrics** — How success is measured (per component)
7. **Tunable parameters** — What config can be changed without code changes
8. **Deploy method** — How to deploy after code changes
9. **Evaluation** — How many runs needed, how results are assessed
10. **Safety rules** — What constraints must never be violated
