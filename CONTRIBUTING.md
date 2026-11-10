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
python3 scripts/public_repo_check.py     # no personal data in tracked files
bash scripts/sync-shared.sh --check      # vendored copies match _shared/
claude plugin validate .                 # catalog and manifests
```

Do not run `scripts/run_suites.py` without arguments: with no globs it runs zero suites and exits green. Use `scripts/suite.sh`.

## Rules that the checks enforce

- **Bump the version of every plugin you change.** `python3 scripts/bump.py <name>` updates `plugin.json`, `marketplace.json` and the version table in `docs/architecture.md` together. Without a bump, clients never receive the change.
- **Keep the READMEs true.** `README.md` (English) and `README.pt-BR.md` (Portuguese) state plugin, skill, hook and registration counts; `scripts/readme_counts_check.py` compares them with the repository. If you add or remove a plugin, update both files.
- **Nothing personal in tracked files:** no absolute machine paths, personal e-mail addresses, client names or credentials. Use `~/` or placeholders in examples.
- **Prose that a skill shows the user is checked** by a style ruler (`_shared/regua_texto.py`); the tests tell you which sentence failed.

## Commits and pull requests

Describe what changed and why, and say how you tested it. One topic per pull request. If a test fails on your machine and also on `main`, say so in the description instead of working around it.
