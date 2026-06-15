# Graph Report - .  (2026-06-15)

## Corpus Check
- 79 files · ~73,392 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 417 nodes · 463 edges · 50 communities (41 shown, 9 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.84)
- Token cost: 362,912 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Bootstrap & Marketplace Sync|Bootstrap & Marketplace Sync]]
- [[_COMMUNITY_Fallow Audit Engine|Fallow Audit Engine]]
- [[_COMMUNITY_PreToolUse Hooks & Visual Daemon|PreToolUse Hooks & Visual Daemon]]
- [[_COMMUNITY_Iterate Convergence Loop|Iterate Convergence Loop]]
- [[_COMMUNITY_Fallow Report Generation|Fallow Report Generation]]
- [[_COMMUNITY_Slides Fidelity Checker|Slides Fidelity Checker]]
- [[_COMMUNITY_Marketplace Registry & Plugin Config|Marketplace Registry & Plugin Config]]
- [[_COMMUNITY_Graphify-Guard Net|Graphify-Guard Net]]
- [[_COMMUNITY_RAIOX Channel Intelligence|RAIOX Channel Intelligence]]
- [[_COMMUNITY_Context-Guard & Handoff Bridge|Context-Guard & Handoff Bridge]]
- [[_COMMUNITY_Fallow Liveness & Convergence|Fallow Liveness & Convergence]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Documentation System (CLAUDE.md)|Documentation System (CLAUDE.md)]]
- [[_COMMUNITY_Marketplace Manifest Metadata|Marketplace Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Project-Doc Generator|Project-Doc Generator]]
- [[_COMMUNITY_QA & Rev6 Parallel Review|QA & Rev6 Parallel Review]]
- [[_COMMUNITY_Grill Design Review|Grill Design Review]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Plugin Manifest Metadata|Plugin Manifest Metadata]]
- [[_COMMUNITY_Slides Deck Generation|Slides Deck Generation]]
- [[_COMMUNITY_Visual Auto-Mode Config|Visual Auto-Mode Config]]
- [[_COMMUNITY_Handoff SaveResume|Handoff Save/Resume]]
- [[_COMMUNITY_Improve Autoresearch|Improve Autoresearch]]
- [[_COMMUNITY_Hook Config (SessionStartPostToolUse)|Hook Config (SessionStart/PostToolUse)]]
- [[_COMMUNITY_Hook Config (SessionStartPostToolUse)|Hook Config (SessionStart/PostToolUse)]]
- [[_COMMUNITY_Hook Config (SessionStartPreToolUse)|Hook Config (SessionStart/PreToolUse)]]
- [[_COMMUNITY_Graphify Detect Script|Graphify Detect Script]]
- [[_COMMUNITY_Graphify Guard Script|Graphify Guard Script]]
- [[_COMMUNITY_Hook Config (PreToolUse)|Hook Config (PreToolUse)]]
- [[_COMMUNITY_Hook Config (PreToolUse)|Hook Config (PreToolUse)]]
- [[_COMMUNITY_Visual Daemon Start|Visual Daemon Start]]
- [[_COMMUNITY_Context-Guard Check Script|Context-Guard Check Script]]
- [[_COMMUNITY_Graphify SessionStart Script|Graphify SessionStart Script]]
- [[_COMMUNITY_Sovai Autonomous Mode|Sovai Autonomous Mode]]
- [[_COMMUNITY_Graphify-Guard Manifest|Graphify-Guard Manifest]]

## God Nodes (most connected - your core abstractions)
1. `build_buckets()` - 9 edges
2. `SlideText` - 9 edges
3. `PRINCIPIOS-SISTEMAS.md (canonical reference, 19 categories)` - 8 edges
4. `visual skill (SKILL.md)` - 8 edges
5. `iterate skill (autonomous convergence loop)` - 7 edges
6. `grep_n()` - 6 edges
7. `direct_evidence()` - 6 edges
8. `audit_round()` - 6 edges
9. `fallow audit.py engine` - 6 edges
10. `graphify-detect.sh (shared helper)` - 6 edges

## Surprising Connections (you probably didn't know these)
- `README (pedro-plugins)` --references--> `Marketplace Registry (marketplace.json)`  [INFERRED]
  README.md → .claude-plugin/marketplace.json
- `AGENTS.md Pointer` --semantically_similar_to--> `GEMINI.md Pointer`  [INFERRED] [semantically similar]
  AGENTS.md → GEMINI.md
- `bootstrap-third-party hooks.json` --conceptually_related_to--> `Hooks-in-Subfolder Convention`  [INFERRED]
  plugins/bootstrap-third-party/hooks/hooks.json → .claude/docs/patterns.md
- `slides skill (SKILL.md)` --conceptually_related_to--> `slides plugin.json`  [INFERRED]
  plugins/slides/skills/slides/SKILL.md → plugins/slides/.claude-plugin/plugin.json
- `visual skill (SKILL.md)` --conceptually_related_to--> `visual plugin.json`  [INFERRED]
  plugins/visual/skills/visual/SKILL.md → plugins/visual/.claude-plugin/plugin.json

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Bootstrap Sync Cycle (pull → apply → snapshot → commit/push)** — hooks_session_sync, lib_apply, lib_snapshot, lib_git_sync, bootstrap_third_party_manifest [EXTRACTED 0.95]
- **Cross-Tool Doc Routing to CLAUDE.md** — _github_copilot_instructions, _agents, _gemini, _claude_claude_md [EXTRACTED 0.95]
- **Context-Guard StatusLine/State-File Bridge** — hooks_context_guard_writer, hooks_context_guard_reset, concept_context_pct_state_file [EXTRACTED 0.95]
- **context-guard: writer + guard + reset coordinate via state file** — hooks_context_guard_writer_sh, hooks_context_guard_sh, hooks_context_guard_reset_sh [EXTRACTED 0.75]
- **graphify-guard defense in depth (detect helper + sessionstart + pretooluse)** — hooks_graphify_detect_sh, hooks_sessionstart_graphify_sh, hooks_pretooluse_graphify_guard_sh [EXTRACTED 0.75]
- **fallow pipeline: skill -> report.py -> audit.py over Fallow tool** — skills_fallow_skill, lib_report_py, lib_audit_py [EXTRACTED 0.75]
- **Parallel voltagent specialist review workflows** — rev6_parallel_dispatch, qa_voltagent_auditors, rev6_consolidation [INFERRED 0.75]
- **Principles reference + index + skill routing** — principles_skill, principles_doc, principles_index [EXTRACTED 0.75]
- **RAIOX honesty pipeline: YAML config, code numbers, validate gate** — raiox_channel_yaml, raiox_honesty_rule, raiox_validate [EXTRACTED 0.75]
- **visual live-sync pipeline: skill, daemon starter, daemon, gate hook** — visual_skill_visual, server_visual_start, server_visual_server, hooks_pre_exitplan_visualize [EXTRACTED 0.85]
- **slides deck generation: skill, template, layout map, theme, fidelity check** — slides_skill_slides, slides_assets_template, slides_references_layout_patterns, slides_references_themes_viu, slides_scripts_check_fidelity [EXTRACTED 0.85]
- **ship test gate: skill flow, hooks config, enforcing hook script** — ship_skill_ship, hooks_ship_hooks_config, hooks_pre_deploy_test_check [EXTRACTED 0.85]

## Communities (50 total, 9 thin omitted)

### Community 0 - "Bootstrap & Marketplace Sync"
Cohesion: 0.11
Nodes (24): description, marketplaces, version, bootstrap-third-party SKILL.md, Hook Re-entrancy Guard (PEDRO_PLUGINS_HOOK_RUNNING), bootstrap-third-party hooks.json, Hooks-in-Subfolder Convention, log() (+16 more)

### Community 1 - "Fallow Audit Engine"
Cohesion: 0.15
Nodes (25): audit_exports(), audit_round(), basename_noext(), converge(), direct_evidence(), exists(), fallow_unused_exports(), fallow_unused_files() (+17 more)

### Community 2 - "PreToolUse Hooks & Visual Daemon"
Cohesion: 0.11
Nodes (17): ship PreToolUse hooks.json, visual PreToolUse hooks.json, lastActivity, PORT, server, STATE_DIR, start.sh (idempotent daemon starter), hard test gate (cannot be bypassed) (+9 more)

### Community 3 - "Iterate Convergence Loop"
Cohesion: 0.11
Nodes (20): One atomic change per iteration, Lint/typecheck baseline regression detection, ENV PROBLEM output classification (stop, don't spend iteration), Hard contract: verifiable result + binary verification, .claude/iterate/<timestamp>.md persistent log, iterate plugin manifest, Reject LLM-as-judge/human inspection: subjective breaks autonomy, iterate skill (autonomous convergence loop) (+12 more)

### Community 4 - "Fallow Report Generation"
Cohesion: 0.18
Nodes (18): audit_map(), build_buckets(), confidence(), esc(), export_audit_map(), export_item(), item_path(), main() (+10 more)

### Community 5 - "Slides Fidelity Checker"
Cohesion: 0.23
Nodes (5): HTMLParser, main(), norm(), SlideText, strip_enum()

### Community 6 - "Marketplace Registry & Plugin Config"
Cohesion: 0.22
Nodes (8): bootstrap-third-party plugin.json, Marketplace Registry (marketplace.json), context-guard plugin.json, README (pedro-plugins), Context-Pct Temp State File (/tmp/claude-context-pct), Throttled Locked Git Sync, context-guard-reset.sh script, context-guard-writer.sh script

### Community 7 - "Graphify-Guard Net"
Cohesion: 0.31
Nodes (10): graph freshness (fresh|stale by mtime), graphify-out/graph.json knowledge graph, fail-open hooks / defense in depth, graphify-guard hooks.json, graphify-guard README, once-per-session sentinel (session_id), graphify skill / graphify query CLI, graphify-detect.sh (shared helper) (+2 more)

### Community 8 - "RAIOX Channel Intelligence"
Cohesion: 0.24
Nodes (10): Benchmark G13 (peer basket, DRAFT until validated), channel-onboarding.md (YAML + checklist reference), channels/<key>.yaml per-channel config, Honesty Rule: numbers code-born, LLM only labels, metrics-spec.md (legacy modules + citation rules), raiox plugin manifest, Replicate the QUESTION never the answer (Massini grade not a template), raiox skill (replicable YouTube channel analysis) (+2 more)

### Community 9 - "Context-Guard & Handoff Bridge"
Cohesion: 0.31
Nodes (9): context-guard hooks.json, /tmp/claude-context-pct state file, HANDOFF.md knowledge-transfer document, context-guard-reset.sh (SessionStart reset), context-guard.sh (PostToolUse guard), context-guard-writer.sh (statusLine wrapper), handoff plugin.json, context-guard:setup SKILL (+1 more)

### Community 10 - "Fallow Liveness & Convergence"
Cohesion: 0.31
Nodes (9): convergence goal (3 identical rounds), Fallow static analyzer (npx fallow), liveness propagation from FP-root entry points, static analysis cannot see cron/route/dynamic/.svelte imports, fallow audit.py engine, fallow report.py engine, fallow plugin.json, fallow SKILL (+1 more)

### Community 11 - "Plugin Manifest Metadata"
Cohesion: 0.22
Nodes (8): author, email, name, description, homepage, license, name, version

### Community 12 - "Plugin Manifest Metadata"
Cohesion: 0.22
Nodes (8): author, email, name, description, homepage, license, name, version

### Community 13 - "Documentation System (CLAUDE.md)"
Cohesion: 0.32
Nodes (8): AGENTS.md Pointer, Project Reference Index (CLAUDE.md), GEMINI.md Pointer, Copilot Instructions Pointer, Architecture Doc, Patterns & Conventions Doc, Local Cache Does Not Auto-Refresh, Version Bump Release Rule

### Community 14 - "Marketplace Manifest Metadata"
Cohesion: 0.25
Nodes (7): metadata, description, name, owner, email, name, plugins

### Community 15 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 16 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 17 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 18 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 19 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 20 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 21 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 22 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 23 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 24 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 25 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 26 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 27 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 28 - "Plugin Manifest Metadata"
Cohesion: 0.25
Nodes (7): author, email, name, description, homepage, name, version

### Community 29 - "Project-Doc Generator"
Cohesion: 0.29
Nodes (8): Artifact cleanup (clean mode, clustered approval), CLAUDE.md lightweight routing index, .claude/docs/*.md per-concern on-demand docs, graphify knowledge-graph integration + unconditional suggestion, project-doc plugin manifest, Thin pointer files (AGENTS.md/GEMINI.md/.cursorrules), project-doc skill (modular doc system generator), Index always-loaded, docs on-demand = context token savings

### Community 30 - "QA & Rev6 Parallel Review"
Cohesion: 0.29
Nodes (8): /goal loop until zero P0/P1 findings, qa plugin manifest, qa skill (4 parallel auditors vs plan), 4 voltagent specialist auditors by domain, Consolidate + dedup findings by severity, Single-message parallel dispatch of 6 agents, rev6 plugin manifest, rev6 skill (6 parallel specialist reviewers)

### Community 31 - "Grill Design Review"
Cohesion: 0.29
Nodes (7): ADR only when hard-to-reverse + surprising + real trade-off, grill-me plugin.json, grill-with-docs plugin.json, grill-me SKILL, ADR-FORMAT (ADR conventions), CONTEXT-FORMAT (CONTEXT.md conventions), grill-with-docs SKILL

### Community 32 - "Plugin Manifest Metadata"
Cohesion: 0.29
Nodes (6): author, homepage, name, description, name, version

### Community 33 - "Plugin Manifest Metadata"
Cohesion: 0.29
Nodes (6): author, homepage, name, description, name, version

### Community 34 - "Slides Deck Generation"
Cohesion: 0.43
Nodes (7): slides deck template.html, golden rule: text is the author's, never invented, slides plugin.json, layout-patterns.md (content-type to component map), VIU theme (canonical, default), check_fidelity.py (anti-invention verifier), slides skill (SKILL.md)

### Community 35 - "Visual Auto-Mode Config"
Cohesion: 0.33
Nodes (5): auto_mode, auto_triggers, min_decisions, min_output_lines, min_plan_items

### Community 36 - "Handoff Save/Resume"
Cohesion: 0.40
Nodes (5): /tmp/claude-context-pct fresh-session signal, .claude/HANDOFF.md briefing document, Handoff mode detection (SAVE vs RESUME), Compaction loses reasoning chains; handoff preserves the why, handoff skill (save/resume session)

### Community 37 - "Improve Autoresearch"
Cohesion: 0.40
Nodes (5): Skill is generic; all app knowledge lives in the program file, GitHub Issues (label 'autoresearch') as proposals, improve plugin manifest, IMPROVEMENT_PROGRAM.md (app-specific context), improve skill (autoresearch implementer)

### Community 38 - "Hook Config (SessionStart/PostToolUse)"
Cohesion: 0.50
Nodes (3): hooks, PostToolUse, SessionStart

### Community 39 - "Hook Config (SessionStart/PostToolUse)"
Cohesion: 0.50
Nodes (3): hooks, PostToolUse, SessionStart

### Community 40 - "Hook Config (SessionStart/PreToolUse)"
Cohesion: 0.50
Nodes (3): hooks, PreToolUse, SessionStart

## Knowledge Gaps
- **186 isolated node(s):** `name`, `description`, `name`, `email`, `plugins` (+181 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Architecture Doc` connect `Documentation System (CLAUDE.md)` to `Bootstrap & Marketplace Sync`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Why does `Throttled Locked Git Sync` connect `Marketplace Registry & Plugin Config` to `Bootstrap & Marketplace Sync`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **What connects `name`, `description`, `name` to the rest of the system?**
  _211 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Bootstrap & Marketplace Sync` be split into smaller, more focused modules?**
  _Cohesion score 0.11494252873563218 - nodes in this community are weakly interconnected._
- **Should `PreToolUse Hooks & Visual Daemon` be split into smaller, more focused modules?**
  _Cohesion score 0.10822510822510822 - nodes in this community are weakly interconnected._
- **Should `Iterate Convergence Loop` be split into smaller, more focused modules?**
  _Cohesion score 0.11052631578947368 - nodes in this community are weakly interconnected._