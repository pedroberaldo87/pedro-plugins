# Security policy

## What is in scope

This repository is a marketplace of Claude Code plugins. Installing a plugin lets its skills and hooks run on your machine, so the interesting reports are about the code in `plugins/`, `_shared/` and `scripts/`:

- a hook or script that runs something you did not ask for, or runs it with more access than it needs;
- a way for untrusted input (a file in a project, a tool result, a branch name) to reach a shell command or to be written outside the intended folder;
- a secret, token, personal path or private hostname committed to the repository;
- a bug in the supply-chain checker (`sec`) that makes a poisoned or vulnerable package look clean.

## Reporting a vulnerability

Please do not open a public issue with the details.

1. Go to the **Security** tab of this repository and choose **Report a vulnerability** (GitHub private vulnerability reporting).
2. If that button is not shown, open a public issue that says only that you have a security report and asks for a private channel. Leave out the details; they will be asked for there.

Include the plugin name and version (`claude plugin list`), what you did, and what happened. A short reproduction helps most.

This is a personal project maintained by one person. There is no fixed response time, but reports are read and a fix ships as a version bump of the affected plugin (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Supported versions

Only the latest version of each plugin on `main` is maintained. Update with `/plugin marketplace update` and reinstall the plugin to pick up a fix.
