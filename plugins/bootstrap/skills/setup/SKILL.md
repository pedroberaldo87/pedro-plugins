---
name: bootstrap:setup
description: One-shot setup for a new machine — installs Pedro's marketplaces and plugins from the manifest, then applies the versioned global config (env vars, permissions, behavior flags, global CLAUDE.md, machine-resolved statusLine). Run once per machine after installing the bootstrap plugin. Does not manage secrets.
---

# Bootstrap Setup

You are bringing a machine up to Pedro's Claude Code baseline. This plugin has **two layers**:

1. **Plugin sync** (automatic, via hooks) — `config/manifest.json` is the source of truth for third-party marketplaces + plugins; the SessionStart/PostToolUse hooks converge local state to it (pull → apply → snapshot → push). You don't trigger this manually; it runs on its own.
2. **Config layer** (on demand — this skill) — applies the versioned global config that a plugin can't carry by itself: env vars, permissions, behavior flags, the global `CLAUDE.md`, and a `statusLine` resolved to THIS machine's paths.

This setup runs the config layer (and kicks the plugin sync once so the machine is fully provisioned). It is **idempotent** and **never touches `settings.local.json`** (which may hold secrets).

## Prerequisites

```bash
command -v jq >/dev/null || { echo "jq required — install it (brew install jq) and re-run"; exit 1; }
command -v claude >/dev/null || { echo "claude CLI required"; exit 1; }
```

`${CLAUDE_PLUGIN_ROOT}` is the installed `bootstrap` plugin dir. Resolve it from the skill context.

## Steps

### 1. Install marketplaces + plugins from the manifest

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply.sh"
```

This adds every marketplace in `config/manifest.json` and installs/enables the plugins it lists. It's safe to re-run (converges, never touches unmanaged plugins). **Check the exit code** — non-zero means some operations failed; investigate before trusting the state.

### 2. Apply the global config layer

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply-config.sh"
```

This merges `config/settings-defaults.json` into `~/.claude/settings.json`:
- **env** — sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CONTEXT_THRESHOLD`, `CLAUDE_STATUSLINE_FORWARD` (defaults win).
- **permissions** — UNION of the machine's existing allow/deny with the versioned defaults (machine keeps its own, gains the shared ones).
- **flags** — `language`, `theme`, `autoCompactEnabled`.
- **statusLine** — resolved to the `context-guard` writer installed on THIS machine (runtime glob, survives version bumps). Requires `context-guard` installed (step 1 installs it).
- **CLAUDE.md** — copies `config/CLAUDE-global.md` to `~/.claude/CLAUDE.md` (with a backup).

It backs up `settings.json` first and **does not touch `settings.local.json`**.

### 3. Reload

```bash
# Tell the user to run /reload-plugins (or restart Claude Code) so the new
# plugins' hooks load and the merged settings take effect.
```

### 4. Report — and flag what setup does NOT do

Tell the user, in plain language:
- Which marketplaces/plugins were installed and whether anything failed.
- That settings.json was merged (env, permissions, flags, statusLine, CLAUDE.md) with a backup made.
- **Secrets are NOT managed.** Anything machine-specific or secret (SSH passphrases, API keys, machine-local paths) lives in `settings.local.json` and must be set up by hand on each machine — e.g. load the SSH key into `ssh-agent`/Keychain (`ssh-add --apple-use-keychain ~/.ssh/<key>`) instead of putting a passphrase in config.

## Updating the versioned config (from the source machine)

When Pedro changes his permissions / env / global CLAUDE.md and wants it to propagate, re-snapshot the defaults into the repo:

```bash
# Regenerate settings-defaults.json from the current settings (drops any secret).
jq '{
  env: .env,
  permissions: {
    allow: [.permissions.allow[] | select(test("SSH_PASSPHRASE|PASSPHRASE";"i") | not)],
    deny: .permissions.deny,
    defaultMode: .permissions.defaultMode
  },
  language: .language, theme: .theme, autoCompactEnabled: .autoCompactEnabled
}' "$HOME/.claude/settings.json" > "$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/settings-defaults.json"

cp "$HOME/.claude/CLAUDE.md" "$PEDRO_PLUGINS_REPO/plugins/bootstrap/config/CLAUDE-global.md"
```

Then bump `plugin.json`, commit, and push — other machines pick it up on their next `/bootstrap:setup`.
