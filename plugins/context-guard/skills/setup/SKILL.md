---
name: context-guard:setup
description: Configure context-guard plugin — registers hooks and statusLine wrapper in settings.json. Run once after installing the plugin.
---

# Context Guard Setup

You are configuring the context-guard plugin. This plugin interrupts the workflow when context window usage exceeds a threshold, prompting the user to preserve session state.

## Architecture

Three components that need to be registered in `~/.claude/settings.json`:

1. **StatusLine wrapper** (`hooks/context-guard-writer.sh`) — intercepts stdin JSON from Claude Code, extracts `context_window.used_percentage`, writes to `/tmp/claude-context-pct`, then optionally forwards to whatever statusLine was previously configured via `CLAUDE_STATUSLINE_FORWARD`.
2. **PostToolUse hook** (`hooks/context-guard.sh`) — reads that file after every tool call and blocks with `continue:false` if threshold is exceeded.
3. **SessionStart hook** (`hooks/context-guard-reset.sh`) — clears sentinel and state files so the guard can fire again in new sessions.

**Why settings.json instead of hooks.json?** The plugin's `hooks.json` uses `${CLAUDE_PLUGIN_ROOT}` which depends on the plugin being cached. For directory-source marketplaces, the cache may not exist. Registering hooks directly in `settings.json` with absolute paths is reliable regardless of cache state.

## Steps

### 1. Resolve the plugin path

Find the context-guard plugin root dynamically:

```bash
# Option A: plugin cache (installed from git marketplace)
PLUGIN_PATH=$(ls -d ~/.claude/plugins/cache/*/context-guard/*/ 2>/dev/null | tail -1)

# Option B: local directory marketplace
# Parse extraKnownMarketplaces from settings.json to find the marketplace root,
# then append plugins/context-guard/
```

Validate that the path exists and contains `hooks/context-guard.sh`. Store the resolved path as `PLUGIN_PATH`.

### 2. Read current settings

Read `~/.claude/settings.json`. Check what already exists:
- Current `statusLine` entry? (save the original command — we'll preserve it)
- `CLAUDE_CONTEXT_THRESHOLD` in `env`?
- `CLAUDE_STATUSLINE_FORWARD` in `env`?
- Existing `PostToolUse` and `SessionStart` hooks? (don't overwrite — merge)

### 3. Configure statusLine

If there's an existing `statusLine.command`, save it as `CLAUDE_STATUSLINE_FORWARD` in the `env` section so the wrapper can forward to it.

Then set `statusLine.command` to:
```json
"statusLine": {
  "type": "command",
  "command": "bash <PLUGIN_PATH>/hooks/context-guard-writer.sh"
}
```

The wrapper extracts context% AND forwards stdin to the original command, so any existing statusLine (claude-hud or other) continues working.

### 4. Register hooks

Add to the `hooks` section in settings.json. **Merge** with existing hooks — don't replace.

Add a **SessionStart** hook:
```json
"SessionStart": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "<PLUGIN_PATH>/hooks/context-guard-reset.sh",
        "timeout": 5
      }
    ]
  }
]
```

Add a **PostToolUse** entry (append to existing PostToolUse array, don't replace other entries):
```json
{
  "hooks": [
    {
      "type": "command",
      "command": "<PLUGIN_PATH>/hooks/context-guard.sh",
      "timeout": 5
    }
  ]
}
```

No `matcher` on PostToolUse — it must fire on ALL tool calls.

### 5. Add env vars

Add to `env` in settings.json (if not already present):
```json
"CLAUDE_CONTEXT_THRESHOLD": "80"
```

If there was an original statusLine command (from step 3), also add:
```json
"CLAUDE_STATUSLINE_FORWARD": "<original statusLine command>"
```

### 6. Verify

Test the full chain:

```bash
# Test writer extracts context%
rm -f /tmp/claude-context-pct /tmp/claude-context-warned-*
echo '{"model":{"display_name":"Opus"},"context_window":{"used_percentage":45,"context_window_size":200000}}' | bash <PLUGIN_PATH>/hooks/context-guard-writer.sh > /dev/null 2>&1
cat /tmp/claude-context-pct  # Should output: 45

# Test guard does NOT fire below threshold
echo '{}' | CLAUDE_CONTEXT_THRESHOLD=80 bash <PLUGIN_PATH>/hooks/context-guard.sh
# Should produce no output

# Test guard DOES fire above threshold
printf '85' > /tmp/claude-context-pct
echo '{}' | CLAUDE_CONTEXT_THRESHOLD=80 bash <PLUGIN_PATH>/hooks/context-guard.sh
# Should output: {"continue":false,"stopReason":"..."}

# Clean up test state
rm -f /tmp/claude-context-pct /tmp/claude-context-warned-*
```

Validate settings.json syntax:
```bash
jq . ~/.claude/settings.json > /dev/null
```

### 7. Report

Tell the user:
- Context guard is active with threshold at X%
- To change threshold: edit `CLAUDE_CONTEXT_THRESHOLD` in `~/.claude/settings.json` env section
- The guard fires ONCE per session, then lets you continue (so you can run /handoff)
- If a previous statusLine was configured, it's been preserved via `CLAUDE_STATUSLINE_FORWARD`
- New sessions auto-reset via SessionStart hook
- Run `/hooks` or restart Claude Code to reload config
