---
name: visual
description: Use when Pedro invokes `/visual` (with or without flags like `-auto-off`, `-auto-on`, `-status`), asks to "ver isso no HTML", wants a visual presentation of a plan/diagnostic/question, or when the PreToolUse hook `pre-exitplan-visualize.sh` on ExitPlanMode blocks. ALSO invoke PROACTIVELY when auto mode is on (default ON, check `${CLAUDE_PLUGIN_ROOT}/skills/visual/config.json`) and you're about to emit a plan with 3+ items, a decision with 2+ options, a diagnostic with 3+ problems, or a long explanation (40+ lines / 3+ sections). Generates a self-contained dark-theme HTML in ~/Desktop/claude-visual/, spawns a local daemon for live-sync back to Claude (Pedro types "ok" and Claude reads state from disk — no copy/paste), and opens it in the browser. Replaces 20-page CLI dumps with scannable visual surfaces — decisions on top, technical details collapsed below.
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

```
~/Desktop/claude-visual/YYYY-MM-DD-sess-<session8>-<slug>.html
```

**Session-scoped naming is mandatory when invoked by the pre-ExitPlanMode hook.** The `<session8>` is the first 8 characters of the Claude Code `session_id` that the hook passes to you via stderr. The hook finds the current session's visual by matching `*sess-<session8>*.html` — if the filename doesn't contain that token, the hook won't recognize it and will block again.

For manual invocation (Pedro types `/visual` outside plan mode), session scoping is optional; a simpler `YYYY-MM-DD-<slug>.html` is fine.

Slug = kebab-case of main topic (e.g., `plan`, `diagnostico-cron`, `decisao-arquitetura`).

After writing, always run `open <path>` to show it.

## Hierarchy rules (non-negotiable)

1. **Top**: the decision Pedro must make. Max 1 main decision per HTML. Large, visually dominant.
2. **Middle**: context + justification. 3-5 bullets max. Link to concrete data (friction counts, real metrics, file paths) when available.
3. **Bottom**: technical detail in `<details>` collapsed by default. User expands only if they want depth.
4. **Before feedback**: executive summary with 🔧/💡/📁 labels per item.
5. **After `.exec` (when `.decision-card` is present)**: the **Decisions box** — live summary + comments + copy button. Mandatory whenever decision cards exist. See "Decisions channel" below.
6. **After `.exec` (for plans)**: the **Feedback box** — per-item keep/change/remove + copy. See "Feedback channel" below.
7. **When both exist**: decisions-box comes first (right after `.exec`), feedback-box is last. The CSS `:has()` rule automatically demotes the decisions-box sticky-actions to inline so the two sticky bars don't collide.

If there's no decision pending, skip the decision block — don't fake one.

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

## Feedback channel (for plans — the most important part)

**Context:** historically Pedro's CLAUDE.md required a `## Sumário Executivo` as the plan's last section, enforced by a `plan-verification-gate.sh` hook. That gate was removed because it was causing endless plan-rewrite loops. The visual skill now owns the "help Pedro review" job — the feedback box is the canonical way Pedro sends feedback back to Claude.

**When to include the feedback-box:** always, when rendering a plan. Skip it for diagnostics, questions with options, or generic content where there's nothing to approve/reject item-by-item.

**How to build it:**

- **One `.feedback-item` per task in the plan.** Extract each task's number and title from the plan file. Example: if the plan has `### Task 1: Migrate DB` and `### Task 2: Update API`, generate two `.feedback-item` divs, one with `data-num="1" data-title="Migrate DB"` and one with `data-num="2" data-title="Update API"`.
- Each item gets three radio buttons: Manter (default), Mudar, Remover.
- Radio name must be unique (`fb-1`, `fb-2`, …) — the radios share a name to be mutually exclusive per item.
- When Pedro clicks "Mudar", the textarea appears (pure CSS via `.feedback-item.state-change .feedback-textarea { display: block }`).
- The general observation textarea at the end catches plan-wide comments.
- Two action buttons: **"Aprovar tudo"** (copies a simple "aprovado" line) and **"Copiar feedback estruturado"** (copies a markdown bullet list with the per-item state).

**How Pedro uses it:**

1. Plan mode prompt appears in the CLI with the plan.
2. Pedro reads it in the HTML (already open in browser).
3. Pedro fills out feedback in the HTML: marks each item, writes general note if any.
4. Pedro clicks "Copiar feedback estruturado" → clipboard gets a markdown-formatted feedback block.
5. Pedro goes to the CLI:
   - If approving: accepts in plan mode (no need to paste anything — the "aprovar tudo" text is just confirmation).
   - If rejecting with feedback: rejects the plan in plan mode, then pastes the feedback as the next message. Claude reads the markdown bullets and adjusts the plan.

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
- **`.opt`** — option card (emoji + title + tradeoff). 3 per decision. 3rd is always `.opt-custom` with embedded `.opt-custom-input` textarea
- **`.plan-item`** (`<details>`) — collapsible plan step with `.read-dot` + `.plan-num` + `.plan-title`
- **`.card-tile`** — friction/metric grid cell
- **`.callout`** — side-ruled note (info/warn/danger/ok variants)
- **`.exec`** — exec summary card
- **`.feedback-box`** — radios per item + progress + sticky actions (for plans)
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

**Feedback-box mapping:** when the plan has N sub-decisions, the feedback-box gets N items (one per decision), and each is radio-driven (keep/change/remove). The copy-feedback output includes which option Pedro picked for each.


## Bugs to avoid (historical)

### Unclickable recommended card
The first version had decision cards that were `.recommended` (bordered accent) but not clickable — only Option A looked interactive, Option B felt dead. **Fix applied**: both cards are `role="radio"` with `tabindex="0"`, `onclick` handler, and a `.selected` state that shows a ✓ badge and stronger shadow. Always use this interactive pattern when rendering multiple options.

### Selected and recommended looked identical (2026-04-20)
`.opt.recommended` and `.opt.selected` had nearly-identical styles (both with accent border + peach gradient at 0.10 vs 0.14 opacity — imperceptible). When Pedro selected a non-recommended option, BOTH cards looked "winning" — ambiguous state.

**Fix applied** (CSS-only, uses `:has()`):
- `.opt.selected` now has `box-shadow: 0 10px 28px rgba(255,168,140,0.22)` and stronger gradient (0.22 opacity) for unambiguous highlight.
- When `.options:has(.opt.selected)` is true, any `.opt.recommended:not(.selected)` reverts to neutral card state (transparent border, no gradient, no shadow) — only the "★ RECOMENDADO" badge remains (at reduced opacity 0.55).

Architectural principle: `.recommended` is a **suggestion**, not a permanent highlight. Once the user picks something, the suggestion steps aside so the real choice is unambiguous.

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
3. `pre-exitplan-visualize.sh` runs → looks for a recent HTML matching the plan slug in `~/Desktop/claude-visual/`.
4. No recent HTML → exits 2 with stderr instructions. The tool call is BLOCKED. The plan is NOT shown to Pedro.
5. You receive the stderr message and MUST:
   - Invoke this skill (Skill tool with `name: visual`)
   - Read the plan file named in the stderr
   - Render it as HTML using the template above
   - Save to the path suggested in stderr (`~/Desktop/claude-visual/YYYY-MM-DD-<slug>.html`)
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
3. Pick slug from main topic → `YYYY-MM-DD-slug.html`
4. Write file to `~/Desktop/claude-visual/` using template
5. Run `open ~/Desktop/claude-visual/<file>`
6. Tell Pedro in 1-2 lines: "Abri no browser: `<path>`"

Never render and then text-dump the same content in the CLI response. The whole point is: HTML replaces the textão, doesn't duplicate it.
