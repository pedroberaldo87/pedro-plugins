# Contributing

Thanks for looking. This is a personal marketplace, so changes are reviewed against one person's conventions; opening an issue before a large change saves both sides time.

## Layout

- `plugins/<name>/` — one independent plugin (skills, hooks, helper code). Hooks live in `hooks/hooks.json`, never in a `hooks.json` at the plugin root.
- `_shared/` — code used by several plugins. It is **copied** into each consumer by `scripts/sync-shared.sh`; edit it in `_shared/`, never in a copy.
- `.claude-plugin/marketplace.json` — the catalog.
- `scripts/` — the checkers and the test pipeline.
- `docs/` — design documentation (in Portuguese).

See the [README](README.md) for how the pieces fit together.

## Setting up

You need `git`, `bash` and Python 3 (CI uses 3.12). `jq` and Node are only needed by a few hooks and by the `visual` daemon.

```bash
git clone https://github.com/pedroberaldo87/pedro-plugins.git
cd pedro-plugins
```

## Before you open a pull request

```bash
bash scripts/suite.sh                    # the whole pipeline (CI runs the same file)
python3 scripts/readme_counts_check.py   # counts and names in both READMEs
python3 scripts/public_repo_check.py     # no personal data in tracked files (reports file:line:col + rule, never the matched text)
bash scripts/sync-shared.sh --check      # vendored copies match _shared/
claude plugin validate .                 # catalog and manifests
```

`public_repo_check.py` exit codes: `0` measured and clean; `1` personal data found; `2` NOT MEASURED (git failed, a tracked file could not be read, or the terms file is unreadable); `3` the name/client/machine rules did not run and `CI` is set. Those rules read `scripts/public_repo_terms`, a private, gitignored list that only the owner has, so a plain checkout runs the structural rules only and says so (exit `0`, "not a complete OK"). Pass `--so-estruturais` to ask for that explicitly, as the public CI does; without it, `CI=1` and no terms file exit `3`. `--staged` checks the index (what the commit will contain), `--json` carries `terms_checked`, `unreadable` and the non-UTF-8 counters, and a finding is always reported as `file:line:col` plus a rule, never the matched text.

Do not run `scripts/run_suites.py` without arguments: with no globs it runs zero suites and exits green. Use `scripts/suite.sh`.

## Rules that the checks enforce

- **Bump the version of every plugin you change.** `python3 scripts/bump.py <name>` updates `plugin.json`, `marketplace.json` and the version table in `docs/architecture.md` together. Without a bump, clients never receive the change.
- **Keep the READMEs true.** `README.md` (English) and `README.pt-BR.md` (Portuguese) state plugin, skill, hook and registration counts; `scripts/readme_counts_check.py` compares them with the repository. If you add or remove a plugin, update both files.
- **Nothing personal in tracked files:** no absolute machine paths, personal e-mail addresses, client names or credentials. Use `~/` or placeholders in examples.
- **Prose that a skill shows the user is checked** by a style ruler (`_shared/regua_texto.py`); the tests tell you which sentence failed.

## Commits and pull requests

Describe what changed and why, and say how you tested it. One topic per pull request. If a test fails on your machine and also on `main`, say so in the description instead of working around it.
