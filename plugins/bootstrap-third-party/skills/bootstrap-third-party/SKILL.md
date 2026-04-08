---
name: bootstrap-third-party
description: Use when the user wants to bootstrap, apply, sync or snapshot third-party Claude Code plugins across machines. Triggers include "bootstrap plugins", "aplica plugins", "sync plugins", "snapshot plugins", "atualiza manifest", "sincroniza plugins de terceiros", "força sync dos plugins". Manages marketplaces and plugins declared in manifest.json via git auto-sync.
---

# Bootstrap Third-Party Plugins

This skill manages Pedro's third-party Claude Code marketplaces and plugins via a versioned `manifest.json`. Most of the time this runs automatically via hooks (`SessionStart` and `PostToolUse`) — this skill is for **manual invocation** when the user wants to force a sync, debug, or trigger an action explicitly.

## Two modes

**`apply`** — "the manifest is truth, make the machine match"
- Triggered by: "bootstrap plugins", "aplica plugins", "sync plugins", "instala os plugins que faltam", "força sync"
- Reads `manifest.json`, compares with local state, adds missing marketplaces, installs missing plugins, uninstalls extras, applies enable/disable state

**`snapshot`** — "the machine is truth, update the manifest"
- Triggered by: "snapshot plugins", "atualiza manifest", "registra estado atual", "commita os plugins"
- Reads local state, regenerates `manifest.json` in the source repo, commits and pushes if changed

## How it works (for Claude running this skill)

The real logic lives in bash scripts at `${CLAUDE_PLUGIN_ROOT}/hooks/lib/`:
- `snapshot.sh` — regenerates `manifest.json` from `~/.claude/plugins/*.json`
- `apply.sh` — applies manifest deltas via `claude plugin *` commands
- `git-sync.sh` — commit and push helpers with retry-on-reject

These scripts are the source of truth. Don't reimplement the logic — **invoke them directly via Bash**.

### Path convention

Source repo is expected at `$PEDRO_PLUGINS_REPO` (default `$HOME/PROGRAMACAO/PEDRO/pedro-plugins`). The scripts auto-detect presence of `.git` directory and adapt behavior.

### Running apply mode

```bash
# Force apply (bypass throttle, run full sync)
PEDRO_PLUGINS_FORCE_SYNC=1 bash "${CLAUDE_PLUGIN_ROOT}/hooks/session-sync.sh" --manual
```

Or invoke the apply lib directly:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/apply.sh"
```

After running, report to the user a clear summary:
- Marketplaces added / removed
- Plugins installed / uninstalled
- Plugins enabled / disabled
- Any failures (these are critical — never hide them)

### Running snapshot mode

Only meaningful on a machine where the source repo is cloned (`~/PROGRAMACAO/PEDRO/pedro-plugins/.git` exists).

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/snapshot.sh" && \
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/git-sync.sh" "manual: snapshot"
```

After running, report:
- Whether manifest changed
- Diff summary (+N plugins, -N plugins, enabled/disabled changes)
- Whether commit+push succeeded
- If push failed, show the error clearly so Pedro can intervene

## Important rules

1. **Never hide failures.** If any `claude plugin` command fails, if `git push` is rejected, or if a conflict appears — surface it prominently in your response. Do not bury it in a long report.

2. **Respect `PEDRO_PLUGINS_VERBOSE=1`** — if set, print detailed output. Otherwise, keep it concise.

3. **Don't run commands that the hook already ran.** If the user asks for "sync" and the SessionStart hook already ran successfully seconds ago, just report the state instead of re-running.

4. **Idempotency check first.** Before doing anything, run `claude plugin marketplace list` and `claude plugin list` to see the current state. If it already matches the manifest, just say so and exit.

## When the hooks fail

If Pedro complains that auto-sync isn't working, check in order:
1. `ls -la ~/PROGRAMACAO/PEDRO/pedro-plugins/.git` — repo present?
2. `cat ~/.claude/plugins/.pedro-plugins-last-sync` — when was last successful sync?
3. `git -C ~/PROGRAMACAO/PEDRO/pedro-plugins status` — dirty state? uncommitted changes?
4. `git -C ~/PROGRAMACAO/PEDRO/pedro-plugins log --oneline -5` — recent commits?
5. Test `git -C ~/PROGRAMACAO/PEDRO/pedro-plugins fetch` — SSH/network issues?

Report findings to Pedro and suggest fixes. Don't auto-fix git state without asking.
