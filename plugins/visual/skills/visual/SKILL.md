---
name: visual
description: Use when Pedro invokes `/visual` (with or without flags like `-auto-off`, `-auto-on`, `-status`), asks to "ver isso no HTML", wants a visual presentation of a plan/diagnostic/question, or when the PreToolUse hook `pre-exitplan-visualize.sh` on ExitPlanMode blocks. ALSO invoke PROACTIVELY when auto mode is on (default ON, check `${CLAUDE_PLUGIN_ROOT}/skills/visual/config.json`) and you're about to emit a plan with 3+ items, a decision with 2+ options, a diagnostic with 3+ problems, or a long explanation (40+ lines / 3+ sections). Generates a self-contained dark-theme HTML inside the project's `.claude/visual/` (falls back to `~/Desktop/claude-visual/` outside a project), spawns a local daemon for live-sync back to Claude (Pedro types "ok" and Claude reads state from disk — no copy/paste), and opens it in the browser. Replaces 20-page CLI dumps with scannable visual surfaces — decisions on top, technical details collapsed below.
---

# Skill: /visual

Turn walls of CLI text into a scannable HTML surface. Dark theme, self-contained, opens in browser.

## When to invoke

- **Explicit**: Pedro types `/visual`, says "faz visual disso", "preciso ver no HTML", "joga pro browser".
- **Toggle commands** (handled inside this skill, NOT regenerating):
  - `/visual -auto-off` — disables auto mode. Writes `auto_mode: false` to config.json.
  - `/visual -auto-on` — re-enables auto mode. Writes `auto_mode: true`.
  - `/visual -status` — prints current config and returns.
  When Pedro passes any of these flags, DO NOT generate a visual — just update config and confirm in CLI.
- **Auto mode** (default ON per Pedro's preference, 2026-04-20): if `${CLAUDE_PLUGIN_ROOT}/skills/visual/config.json` has `auto_mode: true`, automatically invoke this skill whenever you're about to emit:
  - A plan (numbered items, 3+ steps)
  - A decision with ≥2 options
  - A diagnostic with 3+ problems
  - A long explanation (≥40 lines of prose or ≥3 sections)
  Threshold numbers come from `auto_triggers` in config.json. Pedro can tune them by editing the file directly or by saying "aumenta o threshold pra X".
- **Auto-triggered (gate-blocked)**: the PreToolUse hook `pre-exitplan-visualize.sh` on `ExitPlanMode` blocks with exit code 2 and tells you to render the plan as HTML before the plan is shown to Pedro. Pedro wants to READ in the browser, not the CLI. This hook fires regardless of auto mode (plan mode is always visualized).
- **Explicit override when auto is off**: if `auto_mode: false`, wait for Pedro to type `/visual` or ask explicitly. Do NOT proactively generate.

**Decision tree at start of skill invocation:**

```
1. Read ${CLAUDE_PLUGIN_ROOT}/skills/visual/config.json
2. Parse args from the /visual command:
   - If "-auto-off" → update config, write, confirm, STOP.
   - If "-auto-on"  → update config, write, confirm, STOP.
   - If "-status"   → print config, STOP.
3. Otherwise → generate visual as normal.
```

## What to render

Detect the content type from the last substantial message or plan file:

| Content type | Shape |
|---|---|
| Plan (numbered items, exec summary) | Decision card + plan items as `<details>` + exec summary at bottom |
| Diagnostic (problems + what's working) | Problems grid on top (severity colors), "funcionando" section below |
| Question with options | Decision card with selectable cards (A/B/C), recommendation highlighted |
| Mixed / generic | Hero + sections + exec summary, following same hierarchy |

## Output location

The visual is saved **inside the project**, not on the Desktop. The target directory is decided by a 3-level cascade (stops at the first that matches):

1. **Git root** — if the cwd is inside a git repo → `<repo-root>/.claude/visual/`
2. **Project marker** — else, walking up from the cwd (stopping before `$HOME`), the first dir holding `package.json` / `CLAUDE.md` / `pyproject.toml` / `Cargo.toml` / `go.mod` / `graphify-out/` / `.git` → `<dir>/.claude/visual/`
3. **Desktop fallback** — nothing found (e.g. running loose in a non-project dir or `$HOME`) → `~/Desktop/claude-visual/`

**Do not hardcode the directory.** Run the resolver and use its stdout:

```
bash ${CLAUDE_PLUGIN_ROOT}/skills/visual/resolve-dir.sh "$PWD"
```

It prints the absolute target dir and creates it (`mkdir -p`). The filename pattern is:

```
<resolved-dir>/YYYY-MM-DD-sess-<session8>-<slug>.html
```

**Session-scoped naming is mandatory when invoked by the pre-ExitPlanMode hook.** The `<session8>` is the first 8 characters of the Claude Code `session_id` that the hook passes to you via stderr. The hook finds the current session's visual by matching `*sess-<session8>*.html` **in the same resolved dir** — if the filename doesn't contain that token, the hook won't recognize it and will block again. When the hook blocks, it already prints the full resolved path in stderr — save exactly there.

For manual invocation (Pedro types `/visual` outside plan mode), session scoping is optional; a simpler `YYYY-MM-DD-<slug>.html` inside the resolved dir is fine.

Slug = kebab-case of main topic (e.g., `plan`, `diagnostico-cron`, `decisao-arquitetura`).

After writing, always run `open <path>` to show it.

## Hierarchy rules (non-negotiable)

1. **Top**: the decision Pedro must make. Max 1 main decision per HTML. Large, visually dominant. Every decision carries its own plain-language context line (`.decision-context`) — see "O pedido de aprovação tem que se explicar sozinho" below.
2. **Middle**: context + justification. 3-5 bullets max. Link to concrete data (friction counts, real metrics, file paths) when available. This is section-level background — it does NOT replace the per-decision context line. Both exist: the `.decision-context` says what's at stake for THAT decision; the middle bullets give the broader why.
3. **Bottom**: technical detail in `<details>` collapsed by default. User expands only if they want depth.
4. **Reviewable items carry their verdict INLINE**: every item Pedro decides on (plan step, benchmark finding, proposed feature) is a `.feedback-item` with its keep/change/remove radios in the item's own header — NOT re-listed in a separate box at the bottom. See "Feedback channel" below. This is non-negotiable: the old "second table of approval" is a forbidden anti-pattern.
5. **Before feedback**: executive summary with 🔧/💡/📁 labels per item.
6. **After `.exec` (when `.decision-card` is present)**: the **Decisions box** — live summary + comments + copy button. Mandatory whenever decision cards exist. See "Decisions channel" below.
7. **After `.exec` (when reviewable items exist)**: the **Feedback box is a CLOSING box only** — progress bar + general observation + the two action buttons. It NEVER re-lists the items. See "Feedback channel" below.
8. **When both exist**: decisions-box comes first (right after `.exec`), feedback-box is last. The CSS `:has()` rule automatically demotes the decisions-box sticky-actions to inline so the two sticky bars don't collide.

If there's no decision pending, skip the decision block — don't fake one.

## O pedido de aprovação tem que se explicar sozinho (non-negotiable)

This skill governs the *container* well (where boxes go, copy semantics, sync). This section governs the thing that was missing: **the language and self-sufficiency of what you're asking Pedro to approve.** The mechanics being perfect is worthless if Pedro reads the card and still can't tell what he's signing off on.

This is the most-violated rule. Read it before writing any decision, approval item, plan title, finding, or exec line.

### The reader test (altitude)

Pedro reads **only the HTML**. Never assume he read the CLI, the plan file, or the code — those don't exist for him at the moment of deciding. After reading a card, if he can't say **in his own words** (a) what he's approving, (b) why he's being asked, and (c) what changes with each choice — the card failed. Rewrite it.

### Every decision / approval item carries three things, in its own body

1. **O quê** — what's being approved or decided. One plain line. This is the title or the `.decision-q`.
2. **Por quê / a premissa** — what prompted it, what's at stake. 1-2 sentences. For a decision card this is the `.decision-context` line (see below). For a plan item it's the first line of the body.
3. **A consequência de cada opção** — what each choice actually causes. One plain line per option (the option's `<p>` or `.tradeoff`). "✔ Robusto · ✘ Polui Desktop" is a consequence; "Opção A" is not.

This mirrors Pedro's `perguntas-autocontidas` memory: every decision carries its premises and consequences **in its own body**. A bare label is rejected.

### Human language — banned vocabulary

The text Pedro reads is for a human, not a log. Forbidden as the visible headline/title/option of what he approves:

- **Code identifiers** as the thing on display: `data-num`, `latest.json`, `postState()`, `state-change`, class names, function names.
- **Internal jargon / category codes**: `wrong_approach`, `buggy_code`, `over-planning`, error codes, enum values, ticket slugs. If a system emitted it, it's not human language.
- **Agentic / process talk**: "injeta o script após o body", "o parser detecta o marker", "o hook dispara exit 2", "fetch POST pro daemon". Pedro doesn't approve your process — he approves an outcome.

Allowed: a path or command as **secondary** detail inside `code.inline` (e.g. "salvo em `~/Desktop/...`") — never as the title of what's being approved. If a technical term is genuinely unavoidable, gloss it in one plain phrase right after: "o daemon (o programinha que sincroniza em segundo plano)".

This mirrors Pedro's `sem-jargao-proprio` memory and the CLAUDE.md rule: *"Problemas devem ser explicados em 1-2 linhas, em linguagem humana e intuitiva"* — never "somente da forma técnica".

### The two failure modes — and the ruler between them

There's a chasm between two bad extremes, and the skill keeps falling into one or the other:

- **❌ The wall** — a giant paragraph re-explaining everything from zero, every caveat, the whole history. Pedro can't find the decision inside it.
- **❌ The bare label** — so terse he can't act: "Aprovar refactor?", "Opção A / B / C", a title that's just a code name.

The ruler: **enough to decide, nothing more.** Concretely — question in one plain line, premise in 1-2 sentences, one consequence line per option. If you wrote three paragraphs, cut to the premise. If you wrote four words, you owe the premise and the consequences.

### Self-check before opening the browser

Reread each decision/approval block as if you'd never seen the conversation. Can you state what it approves, why, and what each path costs — from the card alone, with zero jargon? If not, it's not ready to show.

## Decisions channel (for questions/decisions — non-negotiable when decision cards are present)

**Context:** when the HTML contains `.decision-card` blocks (main decision or sub-decisions), Pedro clicks to pick options but that state stays inside the browser. Without a feedback channel, Claude has no way to know what he chose — Pedro would have to retype each answer in the CLI. This component bridges that gap.

**When to include `.decisions-box`:** always, when the HTML has at least one `.decision-card`. Mandatory. This applies to "question with options" content, plans with sub-decisions, any rendering that includes option cards.

**Three components inside `.decisions-box`:**

1. **Live summary panel** (`.dsum-list` with `id="dsum-list"`) — updates in real time as Pedro clicks option cards. Shows each decision's question + the chosen option title (with custom note if any). This is the "tail" — Pedro sees his current state reflected back immediately without leaving the page.
2. **Free-form comments textarea** (`#dec-comments`) — for Pedro to jot open-ended thoughts, next-steps, things to discuss after. Not tied to any specific decision.
3. **Copy button** (`btn.btn-primary` with `onclick="copyDecisions(this)"`) — collects every selection + comments into a markdown-formatted block on the clipboard. Pedro pastes in the CLI so Claude knows what he chose.

**Required HTML pattern (copy verbatim, change only surrounding text):**

```html
<div class="decisions-box">
  <h2>📋 Suas escolhas</h2>
  <p class="decisions-intro">Clica nos cards das decisões acima — este painel atualiza em tempo real. Depois é só copiar e colar no CLI.</p>
  <div class="dec-progress" id="dec-progress">
    <strong id="dec-done">0</strong>/<span id="dec-total">0</span> decisões escolhidas
    <div class="dec-progress-bar"><div class="dec-progress-fill" id="dec-bar"></div></div>
  </div>
  <div class="dsum-list" id="dsum-list" aria-live="polite" aria-atomic="false"></div>
  <div class="decisions-note">
    <label for="dec-comments">Algo mais pra me falar? (opcional)</label>
    <textarea id="dec-comments" placeholder="Ex: queria adicionar X antes, ou discutir Y depois..."></textarea>
  </div>
  <div class="sticky-actions">
    <button class="btn btn-primary" onclick="copyDecisions(this)">📋 Copiar escolhas</button>
  </div>
</div>
```

**Required elements breakdown:**
- `.dec-progress` — shows "X/N decisões escolhidas" with bar. Goes orange (incomplete) vs peach (complete). Updates on every click.
- `.dsum-list` with `aria-live="polite"` — live summary, announced by screen readers.
- `.decisions-note` — comments textarea, label uses humanized phrasing ("Algo mais pra me falar?").
- `.sticky-actions` with single button.

**Where to place it:** AFTER the `.exec` summary. If the HTML also has `.feedback-box`, decisions-box goes BEFORE feedback-box (feedback-box stays last because plan-review takes priority; decisions-box's sticky automatically becomes inline via CSS `:has()` rule when feedback-box is present).

**Copy output format (versioned, v1):**

The `copyDecisions` function emits a markdown block wrapped in versioned HTML comments:

```
<!-- visual-decisions v1 -->
📋 **Minhas escolhas:**

- **Decisão 1**: GitHub público · Como hospedar o marketplace?
- **Decisão 2**: Personalizada · Agrupamento
  - _Nota_: 2 plugins (handoff+wrapup juntos, carregar-handoff separado)

**Comentários / próximos passos:**
Quero pensar melhor na decisão 3.

<!-- /visual-decisions -->
```

Claude SHOULD detect the `<!-- visual-decisions v1 -->` marker when parsing pasted content — this is the signal that the user pasted a decisions block. Future format evolutions bump the version (`v2`, etc.) without breaking old-version detection.

**Incomplete selection warning:**

When Pedro clicks "Copiar escolhas" with fewer decisions selected than total, JS fires a `confirm()` dialog: "Você respondeu X de N decisões. Copiar assim mesmo?". He can cancel and finish selecting, or confirm and send partial. This prevents the "I forgot two" failure mode the review team flagged.

**Persistence via localStorage:**

All state (decisions, comments, feedback, general notes) is auto-saved to `localStorage` on every change using key `claude-visual:<pathname>`. On page load, `restoreState()` repopulates the DOM. Refresh, crash, or accidental close no longer destroys progress. The state is per-file — opening a different HTML restores that file's state, not a global one.

**How Pedro uses it:**

1. Pedro clicks option cards in each `.decision-card`. Live summary panel updates as he clicks.
2. Pedro types a note in the Comments textarea if relevant.
3. Pedro clicks "Copiar escolhas" → clipboard gets a markdown block like:
   ```
   📋 **Minhas escolhas:**

   - **Decisão 1**: GitHub público · Como hospedar o marketplace?
   - **Decisão 2**: 1 plugin · session-management · Handoff, carregar-handoff e wrapup — juntos ou separados?
     - _Nota_: (se for opção custom com texto)

   **Comentários / próximos passos:**
   Quero pensar melhor na decisão 3.
   ```
4. Pedro volta ao CLI e cola. Claude lê os bullets e age (escreve plano, ajusta, esclarece).

**Why this pattern over "tail to a file":**

Static HTML cannot write to the filesystem — the browser sandboxes prevent it. A true tail would require a local HTTP server running alongside the browser to accept POST requests. That adds infra. The live summary + copy button delivers the same UX (Pedro sees state, Claude gets structured data) with zero infra.

## Live sync via `claude-visual-server` (implemented 2026-04-20)

The copy/paste flow works but requires a round-trip. A local Node daemon now provides real "tail" mode: Pedro interacts in the browser, the daemon writes state to disk, Claude reads it when Pedro says "ok" / "pronto" / "lido".

**Files:**
- `${CLAUDE_PLUGIN_ROOT}/server/visual_server.mjs` — the daemon (Node stdlib only, zero deps). Binds `127.0.0.1:7755`.
- `${CLAUDE_PLUGIN_ROOT}/server/start.sh` — idempotent starter. Pings the port; if nothing responds, spawns `node visual_server.mjs` detached. Soft-fails if Node is missing.
- `~/.claude/visual-state/<session>.json` — per-session state file (rewritten on every POST from browser).
- `~/.claude/visual-state/latest.json` — always points to the most recently updated session. **Claude reads THIS file** to fetch the user's current state without needing to know the token.

**Endpoints:**
- `GET  /ping` — liveness probe (returns `{status,pid,port}`).
- `POST /state` — body `{session, docTitle?, state}`. Writes `<session>.json` + updates `latest.json`.
- `GET  /state?session=<id>` — reads a specific session (debugging).

**Skill workflow when generating an HTML (mandatory):**

1. Generate a unique session token. Format: short, matching `^[a-zA-Z0-9_-]{4,64}$`. Recommended: `<YYYYMMDDHHMM>-<rand6>` e.g. `202604201230-a3f2k9`.
2. Right after `<body>`, inject:
   ```html
   <script>window.VISUAL_SESSION = "<token>";</script>
   ```
3. Before `open "<path>"`, run `${CLAUDE_PLUGIN_ROOT}/server/start.sh`. Idempotent — if daemon already running, no-op.
4. Open the HTML.

**Behavior in the browser:**
- Every `saveState()` call (triggered on every click, key press, option-card change) also calls `postState()`, debounced at 400ms.
- `postState()` does `fetch POST http://127.0.0.1:7755/state` with `{session, docTitle, state}`.
- On success, the `.live-indicator` pill in the decisions-box turns green (`live sync`). On failure (daemon off), it turns amber (`copy manual`) — copy/paste button still works.

**How Claude reads state (the "tail" part):**

When Pedro signals completion via short triggers like **"ok"**, **"pronto"**, **"lido"**, **"tá bom"**, **"finalizei"**, Claude MUST:
1. Check `~/.claude/visual-state/latest.json` exists.
2. Read it, parse `state` field.
3. Act on the state the same way it would parse a pasted markdown block — decisions, comments, feedback items, general notes.
4. Respond.

If `latest.json` doesn't exist or is stale (>30min old), Claude falls back to asking Pedro to paste the copy/paste block.

**Security surface (deliberate):**
- Daemon binds **only** `127.0.0.1` (never `0.0.0.0`) — unreachable from the network.
- Session token is validated against `^[a-zA-Z0-9_-]{4,64}$` — no path traversal possible.
- Max body size 256KB — no DoS via huge uploads.
- 30-minute idle shutdown — daemon doesn't linger as zombie.
- CORS is `*` (needed for `file://` contexts which send origin `null`). Acceptable since daemon only binds local.

**Auto-shutdown:** daemon kills itself after 30 min of no requests. Next `/visual` invocation respawns.

**Graceful degradation:** HTMLs generated without `window.VISUAL_SESSION` (old files, or Pedro opens template.html directly) never try to sync — `postState()` is a no-op when the session is absent. Backward compatible.

## Feedback channel (verdict INLINE per item — the most important part)

**Context:** historically Pedro's CLAUDE.md required a `## Sumário Executivo` as the plan's last section, enforced by a `plan-verification-gate.sh` hook. That gate was removed because it was causing endless plan-rewrite loops. The visual skill now owns the "help Pedro review" job — the per-item verdict controls are the canonical way Pedro sends feedback back to Claude.

### The verdict lives ON the item — never in a second table (non-negotiable)

**Historical bug (2026-06-10, flagged by Pedro):** the skill rendered every reviewable list TWICE — first the content (plan-items / findings), then a *separate* `.feedback-box` at the bottom that re-listed each item with its keep/change/remove radios. On a big report (a benchmark with dozens of findings), Pedro read all the content, hit the approval menu at the end, and had to scroll back up — or hold the item in memory — to remember what finding #1 even was when deciding on finding #50. His words: he wanted to decide *as he reads*, not re-derive every item at a menu afterward.

**Rule:** each reviewable item is a single `.feedback-item` that **contains** its own content. The keep/change/remove radios sit in the item's `.feedback-head` (right next to the title), and the depth goes in a `<details class="item-detail">` inside the same item. Pedro marks his verdict while reading the item. **Re-listing items with controls in a separate block at the bottom is a forbidden anti-pattern** — that is the "two tables" bug. There is exactly ONE list.

**When to render inline verdicts:** any list where Pedro decides item-by-item — plan tasks, benchmark/report findings, proposed features, schema choices. A purely informational diagnostic (nothing to approve/reject) gets no verdict controls.

**How to build each item:**

- **One `.feedback-item` per reviewable item**, wrapping its content. `data-num` + `data-title` carry the identity (e.g. `data-num="1" data-title="Onboarding guiado"`).
- The `.feedback-head` holds: `.feedback-num` + `.feedback-title` + the three radios. Radios go in the head, **outside** the `<details>` — this avoids the click-on-radio-toggles-the-details conflict without any `preventDefault` hack.
- **Machine values are fixed: `keep` / `change` / `remove`** (the clipboard parser and live-sync depend on them). The visible label text adapts to the content: a plan → "✓ Manter / ✏️ Mudar / ✗ Remover"; findings or features → "✓ Aprovar / ✏️ Ajustar / ✗ Negar". Same values, humanized wording.
- Radio `name` must be unique per item (`fb-1`, `fb-2`, …).
- **NO pre-selected verdict (non-negotiable, Pedro 2026-06-20).** Never ship a radio with `checked` and never seed the item with `state-keep`. The item must render with NOTHING marked, so Pedro has to actively decide — *especially on implementation items*. A pre-checked `<input checked>` ALSO never fires `onchange` on load, so the progress counter would read 0 while the radio looks selected — the exact "parece marcado mas não conta, tenho que mudar e voltar" bug. Untouched items copy as "⚠️ sem veredito" (only **Aprovar tudo** treats untouched as ok).
- Depth goes in `<details class="item-detail">` with `.read-dot` + summary + `.dchev` + `.detail-body`. Optional `.sev` severity tag (`sev-high`/`sev-med`/`sev-low`) next to the title for findings.
- When Pedro picks "Mudar/Ajustar", the textarea appears (pure CSS via `.feedback-item.state-change .feedback-textarea { display: block }`). The radios also recolor per state (change → warn, remove → danger).

**The closing `.feedback-box` is NOT a second list.** It holds only: the progress bar (`X/N itens revisados`), the general-observation textarea (`#fb-general`), and the two action buttons. It must NEVER re-render the items. Title it "🏁 Fechamento", not "Seu feedback".

**Action buttons:** **"Aprovar tudo"** and **"Copiar feedback"**. Both — together with **"Copiar escolhas"** in the decisions-box — emit the **full user-input state** (decisions + dec-comments + feedback items + fb-general). They differ only in the leading verdict and trailing action cue, never in what they capture.

### Non-siloed copy semantics (mandatory)

Historical bug (2026-04-21, flagged by Pedro): each copy button captured only the inputs inside its own box. `approveAll` emitted a bare `"✅ Plano aprovado"` and threw away every observation Pedro had written. `copyDecisions` ignored the feedback items. `copyFeedback` ignored the decisions and `#dec-comments`. Any comment Pedro typed anywhere could vanish depending on which button he pressed. Pedro's words: *"o botao final tem que resumir tudo qeu rolou ao longo do caminho"*.

**Rule:** every copy button calls `collectAllInput()` which concatenates decisions + `#dec-comments` + feedback items (with per-item `change` notes) + `#fb-general`. The buttons then wrap this body with a button-specific envelope:

| Button | Leading envelope | Trailing cue | Extra |
|---|---|---|---|
| `copyDecisions` ("Copiar escolhas") | `<!-- visual-decisions v1 -->` + `📋 Snapshot — escolhas e comentários` | `<!-- /visual-decisions -->` | confirm dialog if selections incomplete |
| `approveAll` ("Aprovar tudo") | `<!-- visual-approve v1 -->` + `✅ APROVADO — <title>` | `Pode prosseguir.` + `<!-- /visual-approve -->` | confirm dialog if any feedback item is `change`/`remove` (prevents accidental approval while asking for changes) |
| `copyFeedback` ("Copiar feedback") | `<!-- visual-feedback v1 -->` + `📝 Feedback no plano` | `Ajuste o plano e mostre de novo.` OR `Tudo certo — pode implementar.` + `<!-- /visual-feedback -->` | — |

**Parser implications for Claude:** the three markers (`visual-decisions`, `visual-approve`, `visual-feedback`) signal intent (snapshot vs approval vs rework), but the **body structure is identical**. When parsing pasted content, Claude should extract decisions + feedback together regardless of which marker wrapped them. The marker tells Claude what Pedro wants done with the information, not what fields to look for.

**How Pedro uses it:**

1. Plan mode prompt appears in the CLI with the plan.
2. Pedro reads it in the HTML (already open in browser).
3. Pedro fills out decisions + feedback + any comments in the HTML.
4. Pedro clicks whichever button matches his verdict: "Aprovar tudo" (approves, includes his observations), "Copiar feedback" (asks for changes, includes full state), or "Copiar escolhas" (snapshot at any point, full state).
5. Pedro goes to the CLI, pastes. Claude reads the marker + body and acts.

**Never** dump the plan text into the CLI response. The HTML IS the plan view. The CLI just handles the accept/reject mechanical step.

## Template

Use this as the base. Customize content, not the CSS or structure.

The canonical template lives at **`${CLAUDE_PLUGIN_ROOT}/skills/visual/template.html`**.

Read that file. It is a fully-working **Variant B** (indigo background + peach accent + rounded cards) self-contained HTML. Components included:

- **`.pill`** — label tags (kicker, decision-label, etc.)
- **`.tldr`** — one-sentence summary card with emoji
- **`h1`** + **`.subtitle`** — hero
- **`.meta-chips`** — reading-cost chips (time, items, decisions, date)
- **`.decision-card`** — wraps 3 option cards
- **`.decision-context`** — mandatory plain-language line right below `.decision-q`. One or two sentences saying what's at stake / what prompted the question, in human language (no code, no jargon). See "O pedido de aprovação tem que se explicar sozinho". Required on every decision card.
- **`.opt`** — option card (emoji + title + tradeoff). 3 per decision. 3rd is always `.opt-custom` with embedded `.opt-custom-input` textarea. Each option's `<p>`/`.tradeoff` states the consequence of picking it, in plain words.
- **`.feedback-item`** — the unified reviewable item: `.feedback-head` (num + title + keep/change/remove radios) + `.item-detail` (`<details>` with `.read-dot`/`.dchev`/`.detail-body` for depth) + inline `.feedback-textarea`. This is what carries the INLINE verdict. Use it for every plan step / finding / feature Pedro decides on. Demo: section 2 of the template.
- **`.sev`** — optional severity tag (`sev-high`/`sev-med`/`sev-low`) shown next to a finding's title
- **`.plan-item`** (`<details>`) — legacy collapsible block with `.read-dot` + `.plan-num` + `.plan-title`, for NON-reviewable read-only content only. For anything Pedro decides on, use `.feedback-item` instead.
- **`.card-tile`** — friction/metric grid cell
- **`.callout`** — side-ruled note (info/warn/danger/ok variants)
- **`.exec`** — exec summary card
- **`.feedback-box`** — CLOSING box only: progress + general observation + sticky action buttons. NEVER re-lists items (the verdicts live inline on each `.feedback-item`).
- **`.decisions-box`** — live summary of selected options + comments + copy button (mandatory when `.decision-card` is present)
- **`.sticky-actions`** — copy-feedback bar glued to bottom
- **`prefers-reduced-motion`** respected

To render a new visual: copy `template.html` to the target path, keep ALL CSS and JS untouched, replace the content inside `<body>` with the current plan/diagnostic/question. Do not invent new class names.


## Illustrate concepts whenever possible — non-negotiable

Pedro consumes visuals much faster than text. If the content has ANY visualizable concept, you MUST illustrate it inline. Do not leave dense ideas as text-only.

**When to illustrate (not optional):**

- Architecture / system diagrams (components + arrows)
- Flowcharts / timelines / state machines
- Before / after comparisons
- Hierarchy or tree structures
- Relationships (who depends on what, who calls what)
- Data flow (request → server → DB → response)
- Any concept that has ≥3 entities with connections between them

**How to illustrate (in order of preference):**

1. **Inline SVG** — default choice. Wrap in `.diagram` container. Use `viewBox`, `stroke="currentColor"`, simple geometric shapes, `<marker>` for arrowheads. Stroke width 1.5–2px. Use `var(--accent)` or `currentColor` so it respects the palette.
2. **ASCII art** inside a `<pre>` block — fallback for flows and trees when SVG would be overkill. Monospace, aligned.
3. **Emoji sequences** — micro-illustrations inline within text (e.g., `📥 input → 🔍 parse → 📤 output`).

**Web images — keep it self-contained:**

Never use `<img src="https://...">` with external URLs. The template is self-contained by design — it must work offline forever.

When a real image is required (screenshot, reference photo, diagram from docs):

1. Fetch the image (WebFetch, curl, or ask Pedro to drop it in Desktop).
2. Convert to base64: `base64 < image.png | pbcopy` (or `openssl base64 < image.png`).
3. Embed inline: `<img src="data:image/png;base64,...">`.

This keeps the HTML self-contained and archivable indefinitely. Large images bloat the file — prefer SVG recreation when feasible.

**The rule is:** if you're rendering dense text and you thought for even a second "this could be a diagram", it SHOULD be a diagram.


## Multiple sub-decisions — each one gets its own option cards

**Problem seen in the wild (2026-04-19, `decisao-exames-imagem.html`):** a plan had 8 open questions, and the skill rendered each as a `.plan-item` with a "💡 Minha inclinação" label. Pedro had no way to choose per-question — only the top-level decision (A/B/C) was interactive. The 8 questions became read-only text.

**Rule:** if the content describes multiple sub-decisions Pedro has to make (e.g., "8 questions the plan needs to answer", "schema choices", "per-module configuration"), EACH sub-decision gets its own mini decision block with 3 option cards (including the mandatory `.opt.opt-custom` third card). Never reduce a decision to "my inclination" as read-only text.

**Detection heuristic:** if a plan section contains N items and each has a question mark, branching language ("ou", "entre X e Y"), or phrases like "decidir se", "escolher entre", "tag única vs múltipla" — that's N decisions, not N plan items.

**Rendering pattern for N sub-decisions:**

```html
<section>
  <div class="section-head">
    <span class="section-num">2</span>
    <h2>Sub-decisões</h2>
  </div>

  <!-- Repeat this block per sub-decision -->
  <div class="decision-card">
    <div class="pill">⚡ Sub-decisão · Pergunta 1 de 8</div>
    <h3 class="decision-q">Modalidades — enum fixo ou livre?</h3>
    <div class="options" role="radiogroup">
      <div class="opt">...A...</div>
      <div class="opt recommended">...B (com minha inclinação marcada)...</div>
      <div class="opt opt-custom">...C com textarea...</div>
    </div>
  </div>
  <!-- ...next sub-decision... -->
</section>
```

My inclination still shows — but as the `.recommended` card, not as the only answer. Pedro picks card or writes in "Outra".

**Inline-verdict mapping:** the N sub-decisions are option-card blocks (Pedro picks A/B/C inline, tracked by the decisions-box). If on top of that the plan also has reviewable tasks, those tasks are `.feedback-item`s with inline keep/change/remove — never re-listed in the closing box. The copy output includes both the picked options and the per-task verdict.


## Bugs to avoid (historical)

### Unclickable recommended card
The first version had decision cards that were `.recommended` (bordered accent) but not clickable — only Option A looked interactive, Option B felt dead. **Fix applied**: both cards are `role="radio"` with `tabindex="0"`, `onclick` handler, and a `.selected` state that shows a ✓ badge and stronger shadow. Always use this interactive pattern when rendering multiple options.

### Selected and recommended looked identical (2026-04-20)
`.opt.recommended` and `.opt.selected` had nearly-identical styles (both with accent border + peach gradient at 0.10 vs 0.14 opacity — imperceptible). When Pedro selected a non-recommended option, BOTH cards looked "winning" — ambiguous state.

**Fix applied** (CSS-only, uses `:has()`):
- `.opt.selected` now has `box-shadow: 0 10px 28px rgba(255,168,140,0.22)` and stronger gradient (0.22 opacity) for unambiguous highlight.
- When `.options:has(.opt.selected)` is true, any `.opt.recommended:not(.selected)` reverts to neutral card state (transparent border, no gradient, no shadow) — only the "★ RECOMENDADO" badge remains (at reduced opacity 0.55).

Architectural principle: `.recommended` is a **suggestion**, not a permanent highlight. Once the user picks something, the suggestion steps aside so the real choice is unambiguous.

### Nothing nasce pré-selecionado (2026-06-20, flagged by Pedro)
Two surfaces shipped looking already-chosen while the counter said nothing was chosen:
1. **Plan items** rendered with `state-keep` + `<input value="keep" checked>`. A pre-checked radio looks selected (the `:has(input:checked)` highlight) but **never fires `onchange` on load**, so `touched` stayed false and the "X/N itens revisados" counter read 0. To register even a simple "concordo", Pedro had to click "Mudar" and back. His words: the fields show up already filled but it "não tá contabilizando lá embaixo".
2. **Recommended option card** had an accent border + peach gradient that made it impersonate the `.selected` state before any click — so a fresh decision looked already-decided.

**Fix applied:**
- `.feedback-item` ships with **no `state-keep` and no `checked`** — nothing marked. First click registers in the counter immediately.
- `.opt.recommended` lost its border/gradient; the recommendation is now the **★ badge ALONE**. An unselected recommended card looks identical to its siblings, so nothing reads as pre-chosen.
- JS made consistent so the fix survives copy and reload: `collectAllInput(untouchedAsKeep)` reports untouched items as "⚠️ sem veredito" (only `approveAll` passes `true`), and `restoreState` only re-marks items Pedro actually touched.

Principle: **the human must take the decision** — render zero pre-selection, especially on implementation choices. A suggestion is a badge, never a pre-filled answer.

## Option cards (decision block) — always 3 with illustrations

When you render a decision block with option cards, there are **two non-negotiable rules**:

### 1. Always include a third "Outra — eu especifico" card

Every options grid has exactly 3 cards: two concrete proposals (Opção A, Opção B) plus a third `.opt.opt-custom` card labeled **"Outra — Eu especifico"**. Pedro uses the embedded `<textarea class="opt-custom-input">` to write his own alternative when none of the pre-baked options fit. The textarea only reveals when the custom card is selected (handled by CSS: `.opt.opt-custom.selected .opt-custom-input { display: block }`), and uses `event.stopPropagation()` on click/keydown/input so typing in the textarea doesn't bubble up and mess with the card's selection state.

Never ship a decision card with only 2 options. Pedro must always have the escape hatch.

### 2. Illustrate options with inline SVG when possible

Each `.opt` card should start with an `<span class="opt-illustration">` containing a small inline SVG that visually conveys the concept of that option. Target: viewBox `0 0 100 60`, 64px tall, `stroke="currentColor"` (the CSS sets color to `var(--accent)`). Use simple geometric shapes — don't try to be realistic.

Good illustrations make options scannable at a glance. Examples:

- **Manual trigger** → a hand/finger pointing at a button
- **Automatic** → a lightning bolt or gear with motion lines
- **Before/after** → an arrow connecting two states
- **Ordered list** → numbered dots connected
- **Branching** → a tree/fork diagram
- **Custom/freeform** → scattered dots with an arrow pointing to blank space (see the default `.opt-custom` SVG in the template)

If the concept is truly abstract and you can't think of a clean visual, skip the illustration for THAT card — but still include it for the others when possible. Partial illustration is fine; generic stock icons are not.

Illustration is visual priority for Pedro, not decoration. He scans fast. A clean SVG beats three paragraphs of description.

## Content rules

- **Titles in bold, NOT backticks** (per CLAUDE.md). Backticks render azul claro — ruim no fundo claro no CLI, mas aqui a gente tá em HTML dark, ok usar `code.inline` para paths/commands.
- **No blockquotes (`>`)** in content rendering — in HTML they're fine but mimic the CLAUDE.md rule of keeping text readable.
- **No markdown tables inside `<details>`** — use the labels pattern (label-row with 🔧💡📁).
- **Svg inline** for diagrams — no external JS libs, no CDN. Everything works offline.
- **Max ~5 top-level `<section>`s** — if you need more, it's too dense for one visual; split into multiple files.

## Hook integration

The hook `~/.claude/hooks/pre-exitplan-visualize.sh` fires on `PreToolUse` of `ExitPlanMode`, AFTER the existing `plan-verification-gate.sh` passes. Its job: **block plan presentation in the CLI until the HTML visual exists**, so Pedro reads the plan in the browser before approving.

Flow when the hook blocks (exit 2):

1. You (Claude) just called `ExitPlanMode` with a plan file.
2. `plan-verification-gate.sh` validates format → passes.
3. `pre-exitplan-visualize.sh` runs → resolves the project's visual dir (cascade) and looks for a recent HTML matching this session in it.
4. No recent HTML → exits 2 with stderr instructions. The tool call is BLOCKED. The plan is NOT shown to Pedro.
5. You receive the stderr message and MUST:
   - Invoke this skill (Skill tool with `name: visual`)
   - Read the plan file named in the stderr
   - Render it as HTML using the template above
   - Save to the **exact path suggested in stderr** (the hook already resolved the project dir for you — do not change it)
   - Open with `open "<path>"`
6. Retry `ExitPlanMode`. The hook now finds the fresh HTML (< 5 min old) → exit 0, plan proceeds to Pedro in the CLI.
7. Pedro reads the HTML in the browser, approves or rejects in the CLI.

Critical behavior when the hook blocks:

- Do NOT try to present the plan as text in your response.
- Do NOT skip the skill — use the template, do not invent your own HTML.
- Do NOT summarize the plan to Pedro — the HTML IS the summary.
- Do the minimum: render, open, retry `ExitPlanMode`. One tight loop.

## Workflow when invoked

1. Identify source content (last message, plan file, explicit content)
2. Detect type (plan / diagnostic / question with options / generic)
3. Resolve the target dir: `DIR=$(bash ${CLAUDE_PLUGIN_ROOT}/skills/visual/resolve-dir.sh "$PWD")`
4. Pick slug from main topic → filename `YYYY-MM-DD-<slug>.html`
5. Write file to `$DIR/<filename>` using template
6. Run `open "$DIR/<filename>"`
7. Tell Pedro in 1-2 lines: "Abri no browser: `<path>`"

Never render and then text-dump the same content in the CLI response. The whole point is: HTML replaces the textão, doesn't duplicate it.
