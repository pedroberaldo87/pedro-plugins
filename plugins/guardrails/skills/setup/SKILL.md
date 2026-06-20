---
name: guardrails:setup
description: One-shot setup for the guardrails plugin — sets the env var the plugin can't carry and removes the old hand-rolled global hooks from settings.json so they don't double-fire alongside the plugin's. Run once per machine after installing.
---

# Guardrails Setup

You are configuring the **guardrails** plugin. The plugin's three hooks (post-edit lint & type-check, scope-cop, Agent Teams guard) come from its own `hooks/hooks.json` and fire automatically once the plugin is installed — you do **NOT** register them here.

This setup does only the two things a plugin **cannot** do on its own:

1. **Set the env var** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `~/.claude/settings.json` (plugins can't carry env vars; the Agent Teams guard is about a feature this flag enables).
2. **Remove the old hand-rolled global hooks** from `~/.claude/settings.json` so they don't fire **in addition to** the plugin's identical hooks. Without this, every edit runs lint twice and pays for two Haiku judge calls.

It is **idempotent**: running it again sets an already-set env var and finds the old hooks already gone — no harm.

## What "the old hooks" are

Three entries in `~/.claude/settings.json` → `.hooks`, all pointing at scripts under `~/.claude/hooks/` (or inline):

| Event | Matcher | How to identify it |
|---|---|---|
| `PostToolUse` | `Edit\|Write` | a hook whose `command` contains `.claude/hooks/lint-and-typecheck` |
| `PreToolUse` | `Edit\|Write` | a hook whose `command` contains `.claude/hooks/pretooluse-scope-cop` |
| `PreToolUse` | `Agent` | a `type: "prompt"` hook whose `prompt` contains `substitute for Agent Teams` |

**Must be preserved:** the `SessionStart` hook pointing at `sessionstart-adhd-mode.sh` (the i-have-adhd auto-activator — deliberately out of scope), and any other unrelated hook the user has.

## Steps

### 1. Sanity-check the file exists and is valid JSON

```bash
SETTINGS="$HOME/.claude/settings.json"
jq . "$SETTINGS" > /dev/null || { echo "settings.json is not valid JSON — aborting"; exit 1; }
```

### 2. Back it up

```bash
cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
```

### 3. Apply the transform with jq

Run this jq program against `~/.claude/settings.json`. It (a) sets the env var, (b) drops the three old hook entries by matching their command path / prompt text, and (c) deletes the `PostToolUse` / `PreToolUse` arrays only if they end up empty (so unrelated hooks survive).

```bash
jq '
  def strip(pred): map(select(pred | not));

  .env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1"

  | if .hooks.PostToolUse then
      .hooks.PostToolUse |= strip(
        ((.hooks // []) | any(.[]; (.command // "") | test("\\.claude/hooks/lint-and-typecheck")))
      )
    else . end

  | if .hooks.PreToolUse then
      .hooks.PreToolUse |= strip(
        ((.hooks // []) | any(.[];
          ((.command // "") | test("\\.claude/hooks/pretooluse-scope-cop"))
          or ((.prompt // "") | test("substitute for Agent Teams"))
        ))
      )
    else . end

  | if (.hooks.PostToolUse // []) == [] then del(.hooks.PostToolUse) else . end
  | if (.hooks.PreToolUse  // []) == [] then del(.hooks.PreToolUse)  else . end
' "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"
```

> Note on `any/2`: `any(generator; condition)` runs `condition` against each output of `generator`. Here the input is the entry's `.hooks` array, the generator `.[]` yields each individual hook object, and the condition inspects that hook's `.command` / `.prompt`. So an entry is dropped when **any** of its `hooks[]` looks like one of the old migrated hooks. (Using `.command` directly as the generator would try to index the array itself — wrong.)

### 4. Verify

```bash
# Valid JSON?
jq . "$SETTINGS" > /dev/null && echo "settings.json OK"

# Env var set?
jq -r '.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' "$SETTINGS"   # → 1

# Old hooks gone? (all three greps should print nothing)
jq -r '.hooks' "$SETTINGS" | grep -E 'lint-and-typecheck|pretooluse-scope-cop|substitute for Agent Teams' || echo "old hooks removed"

# adhd SessionStart preserved?
jq -r '.hooks.SessionStart' "$SETTINGS" | grep -q 'sessionstart-adhd-mode' && echo "adhd hook preserved"
```

### 5. Reload and report

Tell the user, in plain language:

- The three guardrails (lint/type-check, scope-cop, Agent Teams guard) now come from the **plugin**, not from loose scripts in `~/.claude/hooks/`. Those loose scripts still exist on this machine but are no longer wired up — safe to delete later if they want.
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set.
- A timestamped backup of `settings.json` was made.
- Run `/reload-plugins` (or restart Claude Code) so the plugin's hooks load and the removed settings-hooks stop firing.
- Quick check that they're live: `claude plugin details guardrails@pedro-plugins` should show **Hooks (3)**.

**Do not** delete the old scripts in `~/.claude/hooks/` automatically — leave that to the user.
