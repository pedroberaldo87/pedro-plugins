# Nested Pointers (`--nested`, EXPERIMENTAL)

Referência do modo `--nested` do project-doc. Carregue este arquivo SÓ quando a invocação usa `--nested` (ou ao validar o CONDITIONAL invariant do Pattern Manifest).

**What it is:** In a monorepo, Claude Code natively lazy-loads `apps/{app}/CLAUDE.md` when the agent edits files under that app. Without `--nested`, an agent editing `apps/payments/src/routes.ts` directly — without first exploring the project — might miss the canonical doc in `.claude/docs/apps/payments.md`. The `--nested` flag generates a **derived pointer** at `apps/{app}/CLAUDE.md` that covers this "edit-without-exploring" path by surfacing the name, port, and the canonical doc location.

**Why EXPERIMENTAL:** The gain is marginal (Claude Code users familiar with the project follow the Documentation Index; the lazy-load path is an edge case). Inline content would stale immediately (the canonical doc is the source of truth — duplicating gotchas causes drift). The pointer is intentionally thin.

**When it runs:** `--nested` is **not default**. It is opt-in and runs **serialized after t1d** — only once the FULL/`--deep` Workflow has already written all canonical docs in `.claude/docs/apps/{app}.md`. Never runs as a standalone mode before the canonical docs exist.

**What each generated file contains (the derived pointer format):**

```markdown
<!-- nested-pointer gen=3.6 derived-from=.claude/docs/apps/{app}.md sig=<sig> — nao editar a mao -->
# {app-name}

**Porta:** {port} · {1-line description of what this app does}

→ doc canônico: `.claude/docs/apps/{app}.md` (leia antes de mexer)
```

- **Header only:** name + port + 1-line description. No gotchas, no stack details, no commands — avoids stale content. These live in the canonical doc.
- **Provenance stamp:** HTML comment at the top: `<!-- nested-pointer gen=3.6 derived-from=.claude/docs/apps/{app}.md sig=<sig> — nao editar a mao -->`. The `sig` is the sha256 (first 8 hex) of the canonical doc body at generation time. Deterministic and content-addressed: the sig changes when the canonical doc changes, making staleness detectable.
- **Pointer line:** `→ doc canônico: .claude/docs/apps/{app}.md (leia antes de mexer)` — the only factual guidance; always current by reference.

**Scope:** one `apps/{app}/CLAUDE.md` per app that has a canonical doc. Apps without a `.claude/docs/apps/{app}.md` (because they follow the common pattern exactly) get **no nested pointer** — no empty file.

**Sig generation (deterministic):**
```python
import hashlib, pathlib
body = pathlib.Path(".claude/docs/apps/{app}.md").read_text()
# strip frontmatter block (everything between leading --- delimiters)
if body.startswith("---"):
    end = body.index("---", 3) + 3
    body = body[end:].lstrip("\n")
sig = hashlib.sha256(body.encode()).hexdigest()[:8]
```

**Staleness detection:** compare the `sig` in the HTML comment against `sha256(canonical_doc_body)[:8]`. If they differ, the nested pointer is stale and should be regenerated (run `/project-doc --nested` again after the canonical doc was updated).

**Do not hand-edit** the generated files — the comment warns explicitly. They are derived; the canonical doc is the source of truth.
