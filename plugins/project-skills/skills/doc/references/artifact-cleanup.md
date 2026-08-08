# Artifact Cleanup

Referência do modo `clean` do project-doc (e da detecção que roda em todo FULL). Carregue este arquivo quando rodar `/project-doc clean` ou ao reportar artefatos detectados no FULL.

Directory hygiene for stale test/scratch artifacts. **Detection runs on every full `/project-doc`** and is reported with the other results — but it NEVER deletes or moves anything on its own. Removal/archival only happens in `/project-doc clean`, and only after the user approves a clustered list. Same philosophy as Auto-Fix and the graphify suggestion: surface, then act on confirmation.

## Detection

Scan the project root recursively, honoring the hard exclusions below. Group findings into categories:

- **Loose screenshots/prints** — image files (`*.png *.jpg *.jpeg *.webp *.gif`) **not inside asset folders**, typically dumped in the repo root or in `.playwright-mcp/`. Name patterns that confirm test origin: `e2e-*`, `screenshot*`, `print*`, `test-*`, `*-debug*`, `Screen Shot*`, timestamped names.
- **Test runner / tool output** — `.playwright-mcp/` (its `*.yml` snapshots + `console-*.log`), `test-results/`, `playwright-report/`, `coverage/`, `.nyc_output/`, `.pytest_cache/`.
- **Temp / scratch / OS cruft** — `*.tmp *.temp *.bak`, loose `*.log`, `tmp-* scratch-* debug-*`, `.DS_Store` (recursive), `*.dump`, core dumps.
- **Prototypes** (→ archive, don't delete) — loose `*.html` outside the build output, `proto*/ mockup*/` folders.

**Hard exclusions — NEVER scan or touch:** `.git/ node_modules/ .venv/ dist/ build/ vendor/`, `graphify-out/` (useful), `.claude/docs/` (the docs themselves), and any asset folder (`public/ assets/ static/ src/ docs/`) or referenced asset.

## Classification (suggested action per finding)

Every finding gets one of four proposed actions:

- 🗑️ **Delete** — unambiguous junk: `.DS_Store`, old `console-*.log`, `test-results/`, `coverage/`.
- 📦 **Archive** — has potential value: prototype HTML, prints that document a state. Moved to `_archive/`, never trashed.
- 🚩 **Review (sensitive)** — listed individually, never acted on automatically (see Sensitivity).
- ✋ **Keep** — recent/likely in use, or referenced somewhere.

## Sensitivity assessment

A finding goes to 🚩 (and is listed individually, never bulk-actioned) if ANY of:

- **Git-tracked** — `git ls-files` includes it (deleting mutates the repo). *Conditional: only when the project is a git repo; if not, fall back to name/location/reference/mtime signals.*
- **Referenced** — its basename appears via grep in code, `README*`, or `.claude/docs/` → it's an asset, not junk.
- **Recent** — `mtime` < 24h → may be in use in the current session.
- **Unclassifiable** — fits no clear pattern, or is a single large unique file.

## Archive destination

Reuse an existing archive dir if present (detect `_archive/ archive/ .archive/`), else create `_archive/`. Two modes:

- **Reopenable items** (prototypes) → move the **raw file** into `_archive/<category>/`.
- **Safety net before a bulk delete** → first pack the originals into `_archive/<project>-housekeeping-<YYYY-MM-DD>.tar.gz` (the convention already in use), THEN remove them. Guarantees reversibility ("look before you delete").
- Check whether `_archive/` is gitignored; if not, mention it to the user.

## Clustered report format

Group by action, list sensitive items individually, end with an approval prompt:

```
## Artefatos detectados — 152 itens

🗑️  Deletar (descarte seguro) — 95
  • .DS_Store ×129 (lixo macOS, recursivo)
  • .playwright-mcp/console-*.log ×22 (logs de console antigos)

📦  Arquivar → _archive/ — 45
  • Prints E2E soltos na raiz ×45 (e2e-*.jpeg, bulk-*.jpeg, c3-*.jpeg…)
    → tarball _archive/viu-housekeeping-2026-06-13.tar.gz

🚩  Revisar (sensível) — 2
  • logo.png — referenciado em README.md (asset, provável manter)
  • screenshot-novo.png — criado há 2h (pode estar em uso)

Aprovar? [tudo | só deletar | só arquivar | escolher itens | cancelar]
```

## Confirmation protocol

- **Never remove or move without explicit approval.** Show the clustered list first.
- User approves per cluster or per item; sensitive (🚩) items require individual confirmation.
- After acting, report a summary: how many deleted, how many archived (and where), how many skipped.

## Scope & safety

- Operate only inside the project root — never touch `~/Desktop/claude-visual/` or anything outside it.
- Respect the hard exclusions above.
- Default to reversible: pack into the dated tarball before any bulk delete.
