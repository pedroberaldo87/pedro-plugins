# Verification — project-doc

> Checklist de verificação pós-geração do `/project-doc` (19 checks + output format + auto-fix + quando rodar). Consultado on-demand pela skill no passo 13 e no modo `verify`. Fonte canônica; o `SKILL.md` referencia este arquivo.

## Verification (Post-Generation Quality Check)

After writing all files, run this verification checklist. Report results to the user with pass/fail per check.

### Index-Level Checks

**1. Structural Integrity**
- v2 markers present: both `<!-- project-doc:v2 -->` and `<!-- project-doc:v2:end -->` exist
- Content between markers is not empty
- No duplicate markers (only one v2 start/end pair)
- Manual content outside markers (if any) is preserved intact
- No v1 markers remaining (if migration was performed)

**2. Link Validity**
- For every doc referenced in the Documentation Index, verify the file exists in `.claude/docs/`
- Report any broken link as **FAIL — doc referenced but not found**

**3. No Orphan Docs**
- List all files in `.claude/docs/` (and subdirectories for monorepo)
- Compare against docs referenced in the CLAUDE.md index
- Report any doc file not in the index as **WARN — orphan doc**

**4. Coverage Gaps**
- Scan source files for content that should be documented but isn't covered by any doc
- Example: docker-compose.yml exists but no infrastructure.md → **WARN — undocumented area**

**5. Token Budget**
- Count total lines in CLAUDE.md between v2 markers
- PASS if ≤100, WARN if 101-150, FAIL if >150

### Per-Doc Checks

**6. File Path Accuracy**
- For every file path mentioned in any doc (e.g., `dashboard/src/middleware.ts`, `scripts/deploy.sh`), verify the file actually exists using Glob
- Report any referenced paths that don't exist as **FAIL — phantom path**

**7. Port Consistency**
- Cross-reference ports listed in infrastructure.md against docker-compose.yml (ports, EXPOSE), proxy configs (listen, proxy_pass)
- Report any port in the doc not found in source files, or any port in source files missing from the doc

**8. Env Var Coverage**
- Compare env vars listed in env-vars.md against all vars in .env.example
- Report any var in .env.example missing from the doc
- Report any var in the doc not in .env.example (may be valid if from docker-compose environment)

**9. Service Completeness**
- Compare services listed in infrastructure.md against all services in docker-compose.yml
- Report any service missing from the doc

**10. Security — Scrubber + No Leaked Secrets**
- O **scrubber** (lib) é a 1ª barreira na escrita do journal; este check é a 2ª, na doc final (defense-in-depth — repo privado NÃO é controle de secret).
- Scan ALL generated files for secret-looking values, **em paridade com o gate 5 do Stitch e o `PROVIDER_RE` do `journal.py`** (fonte única): atribuição `(?i)(password|senha|passwd|pwd|secret|token|api[_-]?key|credential)\s*[:=]\s*<valor>` cujo `<valor>` seja **credencial-shaped** (≥16 chars de classe mista **ou** Shannon ≥3.5, como a Camada 4 do `journal.py` — **NÃO bare `\S+`**, pra não marcar prosa tipo `secret = barreira`), base64 longo, JWT (`eyJ…`), AWS `AKIA…`/`ASIA…`, **Google `AIza…` e `ya29.…`**, GitHub `gh[posu]_…`/`github_pat_…`, `sk-…`/`sk_live_`/`sk_test_`, Slack `xox…`, GitLab `glpat-…`, blocos PEM, connection strings com senha embutida.
- Garanta que valores de .env NUNCA entram — só nomes. Onde havia um secret, a doc deve **referenciar o cofre** (`.claude/secrets/ops.env`), não o valor.
- Confirme que `.claude/secrets/` está no `.gitignore` (o lib adiciona; verifique).
- Qualquer vazamento potencial = **CRITICAL FAIL** — corrija antes de declarar pronto.

**11. Deploy Flow Accuracy**
- If deploy.md exists, verify the documented steps match the actual deploy script content
- Check that flags documented (--dry-run, --sync-only, etc.) actually exist in the script

**12. Section Relevance**
- For each doc present, verify it has actual content (not just frontmatter + empty template)
- For each doc absent, verify no detection source exists (e.g., if database.md is missing, confirm no DB images in docker-compose, no DB_* vars in .env)
- Report false negatives (doc should exist but doesn't) and false positives (doc exists but shouldn't)

**13. Staleness Detection**
- For each doc, read the `generated` date from frontmatter
- Compare against `git log --format=%aI -1 -- {source files}` for each doc's scope
- Report per-doc staleness: **WARN — {doc}.md may be stale (generated {date}, sources changed {date})**

### Monorepo-Specific Checks

**14. App Completeness**
- List all app directories in `apps/` or `packages/` that have a Dockerfile or package.json
- Compare against apps documented in the CLAUDE.md index Apps section
- Report any app present in filesystem but missing from the index
- Report any app in the index that no longer exists in filesystem

**15. App Content Accuracy (REQUIRED)**
- For each app with docs in `.claude/docs/{app-name}/`, read the app's source files
- Cross-reference deps listed in docs against actual requirements.txt/package.json
- Flag any dep in the file but missing from the doc as **FAIL — undocumented dep**
- Flag any dep documented but no longer in the source as **FAIL — phantom dep**
- This check cannot be skipped or approximated. Read the files.

### Git-Tracking Checks

**16. Versioned Artifacts Are Tracked (CRITICAL — o conhecimento precisa viajar)**
- Os artefatos cujo PROPÓSITO é viajar no git **não podem estar gitignored nem untracked**. Caso real: no `tools` o **journal caiu no `.gitignore`** — a doc gerava, mas o conhecimento não viajava entre máquinas/clones (quebra o RF Portabilidade **em silêncio**).
- Para cada path abaixo, rode `git -C "<root>" check-ignore -q <path>` (ignorado se exit 0) **e** `git -C "<root>" ls-files --error-unmatch <path>` (tracked se exit 0):
  - `.claude/CLAUDE.md` e todo `.claude/docs/*.md`
  - **`.claude/.project-doc/findings.jsonl`** e **`.claude/.project-doc/ledger.json`** — o journal + ledger, o ÚNICO veículo do conhecimento entre máquinas
  - **`graphify-out/graph.json`** (se o projeto tem grafo) — o grafo é documentação obrigatória (premissa do FULL/`--deep`); o passo 0.0 o gera/atualiza, mas só viaja entre máquinas se entrar no git. Caso real do furo: a skill regenerava o grafo e **não o stageava** — cada clone ficava sem mapa, em silêncio (mesma classe do journal no `tools`).
  - os thin pointers gerados (`AGENTS.md`, `GEMINI.md`, `.cursorrules`)
- **Ignorado** (`check-ignore` exit 0) → **CRITICAL FAIL — "{path} está no .gitignore; o conhecimento não vai viajar"**. Mostre a regra que casa (`git check-ignore -v <path>`) pro Pedro removê-la.
- **Não-ignorado mas untracked** (nunca commitado) → **WARN — "{path} existe mas não está no git ainda (git add)"**.
- **Distinção que NÃO pode confundir:** `.claude/.project-doc/backups/`, `.claude/secrets/` e **`graphify-out/cache/` + `graphify-out/.graphify_*`** (máquina-específico / regenerável) **DEVEM** estar gitignored (efêmero / cofre / cache). O check é sobre os arquivos versionados-por-design (journal, ledger, docs, **`graph.json`**), **não** a pasta inteira — `graphify-out/graph.json` precisa viajar, mas `graphify-out/cache/` não.

### Graph Coverage Check (v3.2)

**17. Auditoria grafo × doc** (o grafo é premissa de todo modo → sempre presente; roda em qualquer modo que **gera/atualiza doc** — FULL/`--deep`/incremental/`--rebuild`/`--solo`; modos que NÃO tocam doc — `verify` standalone, `clean` — → N/A, nada novo pra auditar)
- O grafo é o **completeness-critic** do fim: cruza o que o grafo diz ser importante contra o que a doc cobriu (espelha o gate 7 do Stitch; aqui é o check final da Verification).
- Rode `graph_map.py` (ou reuse a saída do passo 0.0) e, para cada item, procure cobertura no texto gerado (qualquer `.claude/docs/*.md` + índice), por `label` ou `source_file`:
  - **god node** (fan-in alto) sem nenhuma menção → **WARN — função central não documentada: `{label}` ({source_file})**
  - **comunidade nomeada** (não-generic) sem seção que a cubra → **WARN — módulo não documentado: `{label}`**
  - **hyperedge ≥0.85** sem menção → **WARN — workflow não documentado: `{label}`** (candidato a nota de arquitetura)
- WARN não bloqueia (o grafo pode ter ruído/defasagem) — alimenta o relatório e, opcionalmente, uma 2ª leva de agente pro gap. Em modo que não gera doc → check **N/A** (não falha). "Sem grafo" não é mais um estado possível: o Passo 0 garante o grafo em todo modo.

### Anti-Regression Check (v3.5.1)

**18. Anti-regressão da projeção — não declare PASS sem isto.** Fecha o buraco onde o check #15 (só deps de app em monorepo) **não** cobre o catálogo de versões, e onde a Fase D (LLM) pode regredir fatos. Confirme, ANTES de cravar sucesso:
- **Gate 9 reportado:** se houve `merge_rejected`, está no relatório (nenhum PASS silencioso com merge rejeitado).
- **Versões batem com o manifesto real:** todo número de versão citado num doc (catálogo / `architecture.md` / índice) **== o `plugin.json`/`package.json` real** — NÃO a versão do backup. Divergência = **FAIL**.
- **`generated` não regrediu:** a data do frontmatter de cada doc escrito é ≥ a data do backup (nunca uma doc "nova" datada mais velha que a anterior).
- **Números de mapa não regrediram:** contagens citadas (ex: nós/comunidades do grafo) ≥ as do snapshot anterior, salvo refactor que de fato apagou código (justifique).
- Qualquer regressão = **FAIL — corrija antes de declarar pronto** (foi o que vazou pro commit quando se cravou "12/12 PASS" sem conferir os fatos do catálogo).

### Pattern Conformance Check (v3.6)

**19. Conformidade com o Pattern Manifest — execute o script, não leia o marker.**
```bash
python3 plugins/project-doc/lib/pattern_check.py --project-root "<root>"
```
- `in_pattern==true` → **PASS**
- `in_pattern==false` → **FAIL — <lista de violations>**. As violations mapeiam diretamente para: (a) marker v2 ausente, (b) frontmatter ausente em algum doc, (c) findings.jsonl ausente, (d) `doc-sig:` ausente no frontmatter de algum doc, (e) gen desatualizado. Corrija cada uma antes de declarar pronto — nunca declarar PASS com `in_pattern==false`.

### Verification Output Format

```
## /project-doc Verification Results

✅ Structural integrity — v2 markers present, content valid
✅ Link validity — 5/5 docs exist
✅ No orphan docs — 0 orphans
✅ Coverage — all detected areas documented
✅ Token budget — 82 lines (target: 60-100)
✅ File paths — 23/23 paths exist across all docs
❌ Port consistency — port 8080 in docker-compose not in infrastructure.md
✅ Env var coverage — 11/11 vars documented
✅ Service completeness — 3/3 services documented
✅ Security — no leaked secrets
✅ Versioned artifacts tracked — journal + ledger + 5 docs + graphify-out/graph.json no git (backups/, secrets/, graphify-out/cache/ ignorados, como esperado)
⚠️  Graph coverage — 18/20 god nodes documentados; "Bootstrap Sync Cycle" (hyperedge) sem nota de arquitetura
✅ Deploy flow — 3/3 flags documented, steps match script
✅ Section relevance — 5 docs, 0 false negatives
⚠️  Staleness — database.md generated 2026-05-01, schema.prisma changed 2026-05-25

Summary: 12 passed, 1 warning, 1 failed
Token impact: 305 lines (v1) → 82 lines index + 5 docs on-demand (73% context reduction)
```

### Auto-Fix

After verification, if simple auto-correctable issues are found:
- Port in docker-compose but missing from infrastructure.md
- Env var in .env.example but missing from env-vars.md
- Service in docker-compose but missing from infrastructure.md
- Orphan doc not referenced in index → add entry
- Doc referenced in index but file missing → remove entry from index
- File path referenced that moved (old path doesn't exist, similar file found nearby)

**Action:** report to user with: "Encontrei N issues corrigíveis automaticamente. Quer que eu corrija?" If user confirms, apply fixes and re-run verification.

Do NOT auto-fix without asking. Do NOT fix complex issues (wrong descriptions, outdated deploy flow, architectural changes) — those require re-running `/project-doc` or `/project-doc {doc-name}`.

### When to Run Verification

- **Automatically** after every `/project-doc` generation, update, or migration
- **On demand** when user says "verifica o claude.md", "check project-doc", "valida a doc", or runs `/project-doc verify`
- Verification can run standalone (without regenerating) — just read existing files and run checks against source files
