# pedro-plugins

A public marketplace of plugins for [Claude Code](https://code.claude.com/docs/en/overview): skills, hooks and automations written in Markdown, Bash and Python, for people who use Claude Code every day and want to install only what they need.

**English** · [Português](README.pt-BR.md)

[![portability](https://github.com/pedroberaldo87/pedro-plugins/actions/workflows/portability.yml/badge.svg)](https://github.com/pedroberaldo87/pedro-plugins/actions/workflows/portability.yml)
![Platforms: macOS, Linux and Windows](https://img.shields.io/badge/platforms-macOS%20%C2%B7%20Linux%20%C2%B7%20Windows-informational)
![Runs on Claude Code](https://img.shields.io/badge/runs%20on-Claude%20Code-blueviolet)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A monorepo: each subdirectory of `plugins/` is an independent plugin, distributed through the `.claude-plugin/marketplace.json` catalog.

**24 plugins · Markdown + Shell + Python · no build step, no package manager.**

The 24 plugins add up to **37 skills** — 19 ship exactly one, `visual` ships two, `2op` ships three, `project-skills` ships thirteen, and `graphify-guard` and `vision` ship none.

This is a command-line toolkit with no graphical interface, so there is no screenshot. Installing is two commands in a terminal:

```console
$ claude plugin marketplace add pedroberaldo87/pedro-plugins
$ claude plugin install handoff@pedro-plugins
```

---

## Contents

- [Features](#features)
- [Installation](#installation)
  - [Install only what you want](#install-only-what-you-want)
  - [Restore the whole setup (new machine)](#restore-the-whole-setup-new-machine)
  - [External dependencies](#external-dependencies)
  - [Check the state](#check-the-state)
- [Configuration](#configuration)
- [Usage: the plugins](#usage-the-plugins)
  - [project-skills — a project's whole lifecycle](#project-skills--a-projects-whole-lifecycle)
  - [Session and continuity](#session-and-continuity)
  - [Planning and review](#planning-and-review)
  - [Documentation and knowledge](#documentation-and-knowledge)
  - [Dev, deploy and cleanup](#dev-deploy-and-cleanup)
  - [Visual presentation](#visual-presentation)
  - [Machine setup](#machine-setup)
- [How it works](#how-it-works)
  - [Automatic hooks](#automatic-hooks)
  - [Anatomy of a plugin](#anatomy-of-a-plugin)
  - [Code shared between plugins](#code-shared-between-plugins)
- [Development](#development)
  - [Tests and checks](#tests-and-checks)
  - [Publishing a change](#publishing-a-change)
- [Project documentation](#project-documentation)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Pick and choose:** 24 independent plugins; install only the ones you want.
- **Project lifecycle (`project-skills`):** concept, plan, autonomous execution, severity-based review and documentation.
- **Session continuity:** `handoff`, `context-guard` and `intent-guard` keep what matters across sessions.
- **Review and second opinions:** `grill-me`, `2op`, `gauntlet`, `improve-workflow`, `vistoria`.
- **Development hygiene:** `ship`, `branches`, `lixeiro`, `fallow`, `guardrails` and `sec` (supply chain).
- **Visual output:** `visual`, `archify` and `slides` produce interactive HTML, diagrams and slide decks.
- **New machine in one command:** `bootstrap` installs marketplaces and plugins and applies the versioned global configuration.
- **No build step:** Markdown, Bash and standard-library Python (the `visual` daemon uses Node).

---

## Installation

You need [Claude Code](https://code.claude.com/docs/en/overview) and Python 3 on your PATH. The commands below use the `claude` CLI; inside a session the equivalents are `/plugin marketplace add …` and `/plugin install …`.

### Install only what you want

```bash
# 1. Add the marketplace (once per machine)
claude plugin marketplace add pedroberaldo87/pedro-plugins

# 2. Install the plugins you want
claude plugin install visual@pedro-plugins
claude plugin install project-skills@pedro-plugins
claude plugin install handoff@pedro-plugins
# ...
```

> ⚠️ **`qa-loop`, `project-doc` and `sovai` are no longer plugins** — they became skills of
> `project-skills` in the 2026-08-09 merge. Installing them by those names fails; what you
> want is `project-skills@pedro-plugins`, and the commands (`/qa-loop`, `/doc`, `/sprint`)
> are unchanged once it is installed.

### Restore the whole setup (new machine)

```bash
# 1. Marketplace + bootstrap
claude plugin marketplace add pedroberaldo87/pedro-plugins
claude plugin install bootstrap@pedro-plugins
```

```text
# 2. Inside a Claude Code session: installs the marketplaces + plugins from the manifest
#    AND applies the global config (env vars, permissions, flags, global CLAUDE.md,
#    output style, statusLine)
/bootstrap:setup
```

Expected result on a blank machine: **23 plugins enabled + 1 disabled by default**
(`graphify-guard`), plus the third-party marketplaces listed in the manifest.

> ⚠️ **If you see `sync incompleto: N operações falharam` ("incomplete sync: N operations failed"), run `/bootstrap:setup` again.**
> Measured on a clean install: the first run left one third-party marketplace behind and the
> second one installed it. The script is convergent on purpose (re-running is safe and never
> touches a marketplace the manifest does not declare). The session-start sync no longer
> finishes the job: it only lists what is still missing, and `/bootstrap:setup` installs it
> after you confirm the list.
> (The script's messages are in Portuguese.)

> `bootstrap` replaces the old `bootstrap-third-party`.

**Know what it overwrites before you run it.** Step 2 copies the versioned global
`CLAUDE.md` over `~/.claude/CLAUDE.md` (with a dated backup next to it) and sets
`outputStyle` to `Clean Style`. If you already have global instructions of your own, run
the checker first — it shows what exists on only one side, without prescribing a direction:

```bash
python3 "$(ls -d ~/.claude/plugins/cache/pedro-plugins/bootstrap/*/ | tail -1)lib/conformance.py"
```

The copy goes **one way, repo → machine**: a rule you write directly in your
`~/.claude/CLAUDE.md` disappears on the next `/bootstrap:setup`. For it to survive, it has to
go into `plugins/bootstrap/config/CLAUDE-global.md`.

### External dependencies

One plugin depends on a binary that the marketplace does **not** install:

| Plugin | Needs | Install |
|---|---|---|
| `graphify-guard` | `graphify` | `uv tool install graphifyy` (or `pipx install graphifyy`) |
| 35 hooks — `grep -rl '\bjq\b' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` | `jq` (**optional**) | Nothing to do: the 33 hooks that make a decision — `grep -rlE '(jq\|hj_campo\|hj_eh_falso)[^#]*(tool_input\.command\|session_id\|stop_hook_active)' plugins/*/hooks/*.sh \| grep -v -e /test_ $(ls _shared/*.sh \| sed -E 's#.*/#-e /#') \| wc -l` — read the payload with `python3` when `jq` is missing, and without both they warn instead of exiting silently. For formatted output: `brew install jq` (macOS) · `choco install jq` (Windows) |
| guards | Python 3 | Ships with macOS · Windows: install the real one (the Microsoft Store stub does not run) |

**Installing does not need `jq`.** `/bootstrap:setup` runs entirely on Python — the reads and
the config merge live in `plugins/bootstrap/lib/cfgjson.py`, and the test next to it compares
each output with the real `jq` so the two cannot drift apart. The only place that still uses
`jq` is `snapshot.sh`, and it only runs on a machine that **cloned** the repository (it writes
the machine's state back into the manifest); installing through the marketplace never touches it.

**Windows:** install Python from the official site, not from the Microsoft Store. The system
ships a fake `python3` that prints an ad instead of running, which is why the marketplace
tests whether Python **executes**, rather than only whether it exists on the path.

Without `graphify`, the guard looks for a `graphify-out/graph.json` that nothing creates — it
stays installed, silent and protecting nothing. The checker reports this in the `dependencia`
area, and only when the plugin that needs it is enabled. If you do not use a graph, the way out
is to disable `graphify-guard` in the manifest, not to install the binary.

### Check the state

```bash
claude plugin list                            # installed plugins
claude plugin marketplace list                # known marketplaces
claude plugin details <name>@pedro-plugins    # canonical diagnostic (shows Hooks (N))
```

---

## Configuration

Everything is optional; the defaults work. These are the variables and files the code actually reads:

| Variable / file | Used by | Default | What it does |
|---|---|---|---|
| `PEDRO_PLUGINS_REPO` | `bootstrap` | `$HOME/pedro-plugins` | Where the local clone of the repository lives. With a clone, `bootstrap` can also run `snapshot` (machine → manifest); without one, only `apply` (manifest → machine). |
| `CLAUDE_STATUSLINE_FORWARD` | `context-guard`, `bootstrap` | set by `bootstrap` | The statusLine command `context-guard` forwards the JSON it receives to. Works with any statusLine you already have. |
| `CLAUDE_CONTEXT_THRESHOLD` | `context-guard` | `85` (also written by `bootstrap`) | Percentage of the context window at which the guard interrupts and suggests `/handoff`. |
| `CLAUDE_CONTEXT_TOKENS` | `context-guard` | `850000` | The same cut-off, in tokens. Whichever is hit first triggers. |
| `QWEN_BASE`, `QWEN_MODEL` | `vision` | none | Address and model of the vision server (OpenAI-compatible API). |
| `QWEN_TIMEOUT` | `vision` | `180` | Maximum wait in seconds (a cold model is slow to answer). |
| `~/.claude/vision.json` | `vision` | absent | Alternative to the variables: `{"base": "...", "model": "..."}`. |

---

## Usage: the plugins

Plugins marked **⚙️** register hooks that run **on their own** (no slash command) — see [Automatic hooks](#automatic-hooks). The rest are invoked on demand through a slash command / skill.

One ships **disabled by default** in the `bootstrap` recipe and you enable it if you want:
`graphify-guard` (it needs an external binary, see above).
Enable: `claude plugin enable <name>@pedro-plugins`.

Nineteen plugins ship **one** skill each (in `lixeiro` it is called `/faxina`). Two ship none —
`graphify-guard` only has hooks and `vision` only has the `see_image` tool. `visual` ships two
and `2op` ships three. And `project-skills` ships thirteen, so it gets its own section right below.

Command names, trigger phrases and skill text are in Portuguese (the author's language); the descriptions here are translated.

### project-skills — a project's whole lifecycle

A single plugin with **thirteen skills**, covering a project's life from the first agreement
to the review of what was written. They talk to each other by plugin name, never by a path to
the neighbour's folder, and they all judge against the project's law and agreements — read
from `.claude/docs/` on the spot, never copied into the skill.

It absorbed `project-doc`, `qa-loop` and `sovai` in the 2026-08-09 merge; the commands did
not change.

**Conceive**

| Command | What it does |
|---|---|
| `/start` | Runs the concept phase in six agreement stages — quality goals, architecture, interface, journeys, how the system works, and the feature list —, each in its own document, re-presented until you approve it, with the approval recorded. It is an **interview, not mining**: it asks and records your answer, never invents content. Also triggers on "vamos conceber" ("let's conceive"). |
| `/pesquisa-referencias` | Builds up reference material when a `/start` stage stalls for lack of it — many agents reading open projects and paid products in parallel. The **cost is declared before** any reading (how many agents, how long, how many sources) and nothing starts without your OK. It stops at a cap on agents, sources or time, or when new sources stop adding anything new. |
| `/design-md` | Authors `DESIGN.md` — Google's open format for describing a design system (values in YAML + sections in markdown). It validates for real with the official tool via `npx`, and falls back to a manual check against the specification when `npx` is not available. Exports the values to Tailwind/DTCG. |

**Plan and execute**

| Command | What it does |
|---|---|
| `/plan` | Turns the approved spec into a checkable plan. **Before creating any new plan, it prints the ones still open** in the project. The word "plano" ("plan") on its own, with no other context, already counts as the invocation — precisely so that list shows up before you start yet another one. |
| `/sprint` | Executes a plan from start to finish **with no pauses, checkpoints or questions**, deciding what it has to and noting each decision for the final report. The engine is deterministic (decompose → execute → review) and a hook enforces that: while the mission is armed, a loose sub-agent launch is denied and sent back. The gate **gives up after 3 denials** and records that it did, because a long mission with the owner away cannot die standing still. Also triggers on "sova", "não me consulte" ("don't ask me"). |
| `/reentrada` | For when `/sprint` died overnight and you are back in the morning: it reads the outcome of the last run from the ledger, classifies it (carry on in the engine, fix and relaunch, or wait for the owner) and **re-arms the loop from where it stopped**, instead of starting from zero. Also triggers on "retoma o sprint" ("resume the sprint"). |
| `/monitorar` | Prints the progress **right now** of every mission that is up — clock, what is running, how long it has been silent, scoreboard of the last round. It reads everything from disk and asks nobody anything. For when you come back to the terminal and the status bar is not telling the story. Also triggers on "tem coisa rodando aí?" ("is anything running?"). |
| `/qa-loop` | Reviews code in a loop that **closes on SEVERITY, not on spend**: it ends when a full round finds nothing above the severity floor, confirmed by an independent re-sweep — never by round count, tokens or time. It anchors on the plan: each finding is classified as an implementation error, a deviation from the plan, or a flaw in the plan itself — and only the first becomes a fix. Each fix goes through the whole test suite before the next one, and at the end an absolute gate requires lint, types, unit and integration all green across the repository. Also triggers on "revisa isso" ("review this"), "tá 100%?" ("is it 100%?"). |
| `/completude` | Measures whether the work **closes**, and returns what is missing **named item by item** — never a percentage. Two sides in the same measurement: the whole chain (feature → requirement → task → proof of the tick) and the articles of the project's law that no task represents. A program counts, not the eye, and a document the measurement did not find does not turn green. Also triggers on "o que falta pra fechar" ("what's left to close"). |

**Document**

| Command | What it does |
|---|---|
| `/doc` | The full round: mines **all** the project's evidence (files, handoffs, memory, knowledge graph, git history, transcripts) into a versioned journal that only grows, and projects it into a `CLAUDE.md` index + one `.claude/docs/*.md` per subject. A cleaner moves secrets to a vault, never to git. Also triggers on "documenta o projeto" ("document the project"). |
| `/doc-touch` | The frequent companion of `/doc`: looks at what your diff touched, works out which documents that affects and **re-projects only those**, without mining everything again. Also triggers on "atualiza a doc do que eu mexi" ("update the docs for what I changed"). |
| `/doc-load` | Says what counts as the **ruler** today and why: the law (constitution, quality goals, constraints), what was agreed with you (blueprint, features, journeys, design) and the mined map — each with the text's stamp and the reason it counts or not. It runs at the start of every stage that specifies, plans, implements, tests or reviews. Also triggers on "qual é a régua deste projeto" ("what's this project's ruler"). |
| `/project-skills` | The index of the family itself: reads the skills from disk and points to the right one for what you want to do. Also triggers on "que skill de projeto eu uso aqui" ("which project skill do I use here"). |

### Session and continuity

| Plugin | Trigger | What it does |
|---|---|---|
| `handoff` ⚙️ | `/handoff` · override `/handoff salvar\|retomar` | Session continuity in one command: it detects the state and routes — full context → saves a transfer document; freshly cleared session → resumes where it left off. Workspace-aware: the handoff belongs to the project the session touched (it resolves the `.git` boundary) and works in a single project, a monorepo (`HANDOFF-<module>.md`) or an umbrella folder. |
| `context-guard` ⚙️ | automatic (PostToolUse) · setup `/context-guard:setup` | Automatically interrupts the workflow when the context window passes a configurable threshold (default 85%) and suggests `/handoff`. statusLine-agnostic — forwards to any existing command through `CLAUDE_STATUSLINE_FORWARD`. **Use together with `handoff`.** |
| `intent-guard` ⚙️ | automatic (UserPromptSubmit + Stop + PreToolUse) | An append-only notebook of the user's requests, **verbatim**. Classifies each message (request / correction / constraint / chat) and keeps the list of live requests. At the end of the turn it blocks declaring delivery without an independent audit: it dispatches an auditor that judges each request and records a verdict with proof. The gate stamps a `.escopo` sidecar with **which** requests it asked about — without that, a new message arriving mid-way made the verdict impossible to approve. |

### Planning and review

| Plugin | Trigger | What it does |
|---|---|---|
| `grill-me` | `/grill-me [com-docs]` | A relentless interview about a plan/design until the decision tree is exhausted. With no argument it grills the plan on its own; with `com-docs` it confronts it with the existing domain model (CONTEXT.md, ADRs) and updates the docs inline as decisions crystallize. *By [Matt Pocock](https://github.com/mattpocock/skills).* |
| `principles` | `/principles [review]` | Loads generic system principles (`PRINCIPIOS-SISTEMAS.md`), maps the categories relevant to the context and produces a guide with the why and the how. Two modes: before implementing, and auditing what is already written. It never decides what THIS system has to be — that belongs to the project's constitution. |
| `gauntlet` ⚙️ | `/gauntlet` | Agents compete against a real product you name, and **nothing that gets built judges itself**: each piece gets a builder and a separate blind judge. **The bar is to leave jaws on the floor** — the judge puts the whole work next to the whole target, decides which half is stronger before checking the labels, and its answer starts out as "no". A small gain closes nothing: it sends the next builder to propose a NEW path. A piece closes only when the judge is impressed, on your order, or when the budget runs out — and the director holds the whole to the same bar. It runs as a **visible team** in the conversation: you see each agent, steer mid-flight, veto and stop. Each verdict is a file on disk with the pair of observations that proves it; a PreToolUse lock prevents new dispatches while any delivery lacks a judge, and a program refuses the close when one is missing. It was born from a real failure — seven builders launched with a judge promised in every briefing, zero judges launched, nobody noticed. |
| `improve-workflow` | `/improve-workflow` | **Autopsy of a multi-agent run that has already finished.** Reads the whole transcript, measures what each ROLE cost (agents, turns, tokens, failure rate), raises defect signals by counting instead of judging, and delivers an opinion for you to approve item by item. It **investigates and proposes, and by design it is forbidden to fix what it found**. |
| `improve` | `/improve` | Iterative improvement rounds that read the app's `IMPROVEMENT_PROGRAM.md` + GitHub issues labelled `autoresearch`. Generic — works with any app that follows the methodology. |
| `2op` | `/2op` · `/2op-opus` · `/2op-sonnet` | A second opinion from **another model inside the same session** — no subagent, no re-briefing, no orchestration. The `model` field in the frontmatter switches the model for the whole turn, with the context already loaded; the session's model comes back on its own at the next prompt. The reviewer opens with CONCORDO / CONCORDO COM RESSALVA / DISCORDO (agree / agree with reservations / disagree), labels each claim CONFIRMADO or INFERIDO (confirmed / inferred), and is forbidden to edit files. One command per model because the frontmatter does not interpolate arguments (`model: $0` fails the invocation). |

### Documentation and knowledge

| Plugin | Trigger | What it does |
|---|---|---|
| `vistoria` | `/vistoria` | Reviews the **marketplace's own instruction files** — skills, hooks and checkers — and returns a page of findings with the proof pasted in, where you tick what becomes a checkable plan. It runs the checkers that already exist in one command and adds the measured lenses (a test assertion that froze a dead phrase, a hook script nobody registers). **A finding without proof is refused at the door.** |
| `check-skills` | `/check-skills` | Checks the health of what is installed on the machine through six lenses: a repeated skill name, hooks from different origins on the same event, descriptions competing for the same subject, versions stuck in the cache, a process a skill opens and does not close, and a mention of a sibling plugin that is not installed here. The sweep is done by a program; judging contradictions between instructions requires reading the descriptions side by side. |
| `graphify-guard` ⚙️ | automatic (SessionStart + PreToolUse) | Makes sure `graphify` knowledge graphs get consulted when relevant. A SessionStart heads-up when a graph exists; a PreToolUse net redirects blind search to `graphify query` once per session. Detects a stale graph and offers to update it. Defense in depth, fail-open, monorepo-aware. |
| `vision` | tool `see_image` | Gives Claude eyes by delegating to a vision server (OpenAI-compatible API). When it needs to understand an image it cannot read, it calls `see_image(path, question)` and the server returns a text description. The endpoint is set by `QWEN_BASE`/`QWEN_MODEL` or `~/.claude/vision.json` — whoever installs it points it at their own backend. |

### Dev, deploy and cleanup

| Plugin | Trigger | What it does |
|---|---|---|
| `sec` | `/sec` | Checks the supply chain of the open project and of the machine against public databases (OSV and the Aikido Intel malware list), **without reviewing your code**. Project: npm, pnpm, yarn, uv, poetry and pip lockfiles, GitHub Actions and `.mcp.json`. Machine: Claude Code, plugins, MCP, `npm -g`, pipx, Node and Homebrew. Separates poisoned package, known flaw, open door and outdated; delivers a report with checkboxes and fixes only what you tick. A source that did not answer comes out as NOT VERIFIED, never as green. |
| `ship` ⚙️ | `/ship` · PreToolUse | Production deploy flow: lint → type-check → commit → push → deploy in a disciplined sequence. |
| `guardrails` ⚙️ | automatic (PostToolUse + PreToolUse) · setup `/guardrails:setup` | Global editing guardrails as hooks: post-edit lint & type-check (JS/TS/Python), an LLM scope-cop that blocks UI edits outside the approved plan, and a guard against misuse of Agent Teams. Portable across machines — replaces hand-rolled hooks in `~/.claude/settings.json`. Run `/guardrails:setup` once per machine. |
| `fallow` | `/fallow` | Runs Fallow (a JS/TS static analyzer — dead code, duplication, complexity), classifies findings by type and confidence, audits the report to catch false positives (cron, HTTP routes, dynamic imports) and delivers an interactive report where you choose what to clean up. Cleanup with a safety net (preview + build/test). |
| `branches` ⚙️ | `/branches` · SessionStart | A report of stale branches with proof: how many, which are already contained in the base, and what can be deleted. Before deleting, it creates an `archive/<branch>-<date>` tag as a rescue net. A silent SessionStart notice when there is no stale branch. |
| `lixeiro` ⚙️ | `/faxina` · automatic (SessionEnd + Stop) | Ends the processes the session opened and left running — dev server, test suite in watch mode, tunnel. The automatic part reaps **only what the session noted it had opened**; the `/faxina` command is the manual sibling, which shows **everything** that is up, with or without provenance, and ends only what you tick. |

### Visual presentation

| Plugin | Trigger | What it does |
|---|---|---|
| `visual` ⚙️ | `/visual` · `/andamento` · automatic on plans/diagnoses (PreToolUse on ExitPlanMode) | Turns walls of CLI text into interactive dark-theme HTML views, opened in the browser with **live sync** back to Claude through a local daemon. Auto mode renders plans (3+ items), decisions (2+ options) and diagnoses (3+ problems) without being invoked. **Prose is refused by the program**: every text field goes through four checks (≤140 characters per bullet, one sentence per bullet, no continuation connective at the start, at most 6 bullets per block) and exceeding them aborts without writing the page. The body of each problem **starts folded** — the title stays visible, the consequence and the proposal open with a click whose label is derived from the content, never a fixed tag. The second skill, `/andamento`, shows in the CLI, as a tree, where the current plan's implementation stands. |
| `archify` | `/archify` | Architecture, flow, sequence and lifecycle diagrams as explorable HTML with SVG: progressive reading depth, semantic lens, route preview between two points, chapter navigation and export to PNG/SVG/WebM. Accepts a plain-language description or pasted Mermaid. |
| `slides` | `/slides <file.md> [theme]` | A markdown outline → a keynote-grade single-file HTML deck. Theme system (Slate default), a presentation language with large type, strict fidelity to the text (never invents a sentence) and output next to the source `.md`. |

### Machine setup

| Plugin | Trigger | What it does |
|---|---|---|
| `bootstrap` ⚙️ | `/bootstrap:setup` · automatic on SessionStart + PostToolUse | Prepares a new machine: keeps installed marketplaces and plugins in sync through hooks (it installs nothing new without your confirmation in `/bootstrap:setup`) **and** applies the versioned global config (env, permissions, flags, global `CLAUDE.md`, output style, a statusLine resolved per machine). It also ships **Clean Style** (result on the first line, a ceiling on prose, pasted evidence uncapped) and a **conformance checker** that compares the live machine against the versioned contract without writing anything. Run `/bootstrap:setup` once per machine. The permission defaults auto-approve a plugin script only when it is called by its literal cache path and the script runs no command it receives; calls built with `$VAR` or `$(…)` ask for approval (re-run `apply-config.sh` after a plugin update). |

---

## How it works

Each plugin is a self-contained folder: Claude Code reads the catalog, copies the plugin's folder into the machine's cache and loads the skills and hooks it declares. There is no server and no compile step; what runs is Bash and Python (standard library) scripts that the folder itself carries.

### Automatic hooks

12 plugins register hooks that fire without a slash command — 54 registrations in total
(derived in this run: `python3 scripts/hook_contract.py`; checked at commit time by
`python3 scripts/readme_counts_check.py`):

| Plugin | Events | Role |
|---|---|---|
| `bootstrap` | SessionStart×2 · PostToolUse | Sync of what is already installed, a notice about what the manifest adds, and the notice after a plugin command |
| `branches` | SessionStart×2 · PostToolUse | Stale-branch notice, silent when there is none |
| `context-guard` | SessionStart×2 · PostToolUse | Watches how much of the conversation is used and suggests the handoff |
| `gauntlet` | SessionStart×2 · PreToolUse | Denies new dispatches while a delivery has no judge, and finds the contest again on startup |
| `graphify-guard` | SessionStart×2 · PreToolUse | Redirects blind search to the knowledge graph |
| `guardrails` | SessionStart · PreToolUse×4 · PostToolUse | Post-edit lint and type-check, UI scope-cop, and the unsupported-question gate |
| `handoff` | SessionStart×2 · PreToolUse · Stop | Detects a resume and saves the session's continuity |
| `intent-guard` | SessionStart · UserPromptSubmit · PostToolUse×2 · Stop | Verbatim request notebook and delivery gate |
| `lixeiro` | SessionStart×2 · PostToolUse · Stop · SessionEnd | Notes who opened a process and ends what the session left running |
| `project-skills` | SessionStart×4 · UserPromptSubmit · PreToolUse×6 · PostToolUse×2 · Stop×2 | Doc-first guard, stale-doc notice, plan gate, and the autonomous engine in the status bar |
| `ship` | SessionStart · PreToolUse | Guards the deploy flow |
| `visual` | SessionStart · Stop | Intercepts plan-mode output and revives the open plan |

> ⚠️ **A plugin's hook goes in `hooks/hooks.json` (a subfolder), never `hooks.json` at the root.** At the root Claude Code silently ignores it — `claude plugin details` shows `Hooks (0)` and nothing fires. `claude plugin validate` passes anyway. The canonical diagnostic is `claude plugin details <plugin>@pedro-plugins`.

### Anatomy of a plugin

```
plugins/<name>/
├── .claude-plugin/
│   └── plugin.json          # Identity: name, version, description, author
├── hooks/                   # (optional) automations
│   ├── hooks.json           #   ⚠️ HERE, not at the plugin root
│   └── *.sh / *.py          #   hook scripts
├── skills/<name>/
│   └── SKILL.md             # The skill's full instructions
└── lib/                     # (optional) the plugin's helper code (Python stdlib)
```

Some plugins have extra folders: `bootstrap` has `config/` and `output-styles/`, `visual` has `server/`, and `vision` is an MCP server (`.mcp.json` + `vision_mcp.py`).

The catalog lives in `.claude-plugin/marketplace.json` at the root — each plugin has an entry with `name`, `source`, `description`, `category`, `version` and `tags`.

### Code shared between plugins

Code that is truly common lives in `_shared/` at the root and is **vendored** into each consumer by `scripts/sync-shared.sh` — copied, **not imported at runtime**, because Claude Code isolates each plugin in the cache. There are 31 source files in `_shared/`, spread over 116 copies in 46 destination folders: `resolve-plugin.sh` (finds a sibling plugin's folder) lives in 18 plugins; `hook-json.sh` (reads the hook payload without depending on `jq`) and `regua_texto.py` (the ruler that refuses prose) in 12 each; `collect_engine.py` (transcript reading, project-root resolution) in `handoff` and `project-skills`. `_shared/` is the source of truth: edit there and run `scripts/sync-shared.sh` (`--check` catches drift between the source and the copies).

---

## Development

You need `git`, `bash` and Python 3 (CI uses 3.12). `jq` and Node are only needed for specific parts (see [External dependencies](#external-dependencies)).

```bash
git clone https://github.com/pedroberaldo87/pedro-plugins.git ~/pedro-plugins
cd ~/pedro-plugins
```

`bootstrap` detects whether the repo is cloned locally and adapts:
- **With the repo:** it can run `snapshot` (machine state → manifest, commit, push).
- **Without the repo:** only `apply` (manifest → machine).

To use another path: `export PEDRO_PLUGINS_REPO="/alternative/path/pedro-plugins"`.

To try the local catalog in Claude Code: `claude plugin marketplace add ./`, from the root of the clone.

### Tests and checks

```bash
bash scripts/suite.sh                          # the whole pipeline, the same one CI runs
python3 scripts/readme_counts_check.py         # numbers and names in both READMEs against the repository
python3 scripts/public_repo_check.py           # no personal data in tracked files
bash scripts/sync-shared.sh --check            # drift between _shared/ and the vendored copies
claude plugin validate .                       # validates the catalog and the manifests
```

Individual suites sit next to the code: `python3 plugins/<name>/lib/test_*.py` and `bash plugins/<name>/hooks/test_*.sh`. Always run `scripts/suite.sh`, never `scripts/run_suites.py` with no arguments: without globs it runs zero suites and exits green.

CI (`.github/workflows/portability.yml`) runs the pipeline on Ubuntu, macOS and Windows on every push to `main` and on every pull request. The repository also has a commit gate for people working inside Claude Code (`.claude/hooks/release-gate.sh`, wired up by `.claude/settings.json`).

### Publishing a change

> ⚠️ **Editing a skill/hook without bumping `version` in `plugin.json` = clients never get the update.**

1. Edit the plugin in `plugins/<name>/`.
2. **Bump `version`** with `python3 scripts/bump.py <name>` (`--minor`, `--major` or `--para X.Y.Z`): it updates `plugin.json`, mirrors it in `marketplace.json` and updates the version table in `docs/architecture.md`.
3. `claude plugin validate .` — catches invalid frontmatter (`author` as a string, `: `/`<>` in values) that silently blocks the install.
4. Commit + push.
5. On the clients: `/plugin marketplace update` + `claude plugin install <name>@pedro-plugins` (installing ≠ refreshing the index).

---

## Project documentation

The [`docs/`](docs/) folder describes how the repository works inside. It is in **Portuguese** and has no English version. Where to start:

- [`architecture.md`](docs/architecture.md): the architecture, with the plugin and version table.
- [`constituicao.md`](docs/constituicao.md): the rules the repository's checkers enforce.
- [`blueprint.md`](docs/blueprint.md), [`solution-strategy.md`](docs/solution-strategy.md) and [`architecture-intent.md`](docs/architecture-intent.md): how the system works and the solution strategy.
- [`context.md`](docs/context.md), [`features.md`](docs/features.md), [`journeys.md`](docs/journeys.md), [`glossary.md`](docs/glossary.md) and [`constraints.md`](docs/constraints.md): context and scope, features, journeys, glossary and constraints.
- [`jq-pontos-de-decisao.md`](docs/jq-pontos-de-decisao.md): where a missing `jq` used to silence a gate.

The folder also has the end-to-end flows, the map of where each piece of data lives, durability, quality goals and known pitfalls. [`docs/fluxos/`](docs/fluxos/) has HTML diagrams. Each plugin documents its own behavior in the `SKILL.md` of its skills (in Portuguese); only `graphify-guard` has a `README.md` of its own.

---

## Security

To report a vulnerability, see [SECURITY.md](SECURITY.md). In short: do not open a public issue with the details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: open an issue before a large change, and run the pipeline and `claude plugin validate .` before the pull request.

---

## License

[MIT](LICENSE) © 2026 Pedro Beraldo.

Third-party plugins keep their own licenses:
- `archify` — MIT, see [`plugins/archify/skills/archify/LICENSE`](plugins/archify/skills/archify/LICENSE).
- `grill-me` — MIT © Matt Pocock, from [mattpocock/skills](https://github.com/mattpocock/skills); see [`plugins/grill-me/LICENSE`](plugins/grill-me/LICENSE).
