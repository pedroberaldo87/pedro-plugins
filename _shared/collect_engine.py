#!/usr/bin/env python3
"""
collect_engine.py — camada de coleta compartilhada (FONTE-DA-VERDADE em _shared/).

Extraída de plugins/handoff/lib/extract_ata.py (que tinha o schema do .jsonl
verificado em dados reais, jun/2026 — o ativo caro). Concentra TUDO que é
mecânica de transcript + resolução de escopo, sem nenhum julgamento de LLM:
  • leitura/descoberta de transcript (single + multi-slug por projeto)
  • resolução de project-root / módulos (avulso, monorepo, guarda-chuva)
  • collect() — itens crus por record (directive, rejection, ask, plan, task, ...)
  • anchor_of() — chave estável p/ dedup/id

Consumidores (handoff, project-doc) NÃO importam isto em runtime: o Claude Code
isola plugins na instalação (só plugins/<nome>/ vai pro cache, sem variável
cross-plugin). Por isso scripts/sync-shared.sh VENDORA este arquivo como cópia
sibling dentro do lib/ de cada plugin. Source DRY; runtime autônomo.

CLI (modo engine, usado pelo project-doc — tier 4 da cascata de fontes):
  collect_engine.py --emit-findings [--project-root D | --cwd D]
                    [--scope all|session] [--session ID] [--all-kinds]
  collect_engine.py --discover-all  [--project-root D | --cwd D]
"""
import argparse, glob, hashlib, json, os, re, sys

HOME = os.path.expanduser("~")
PROJECTS_DIR = os.path.join(HOME, ".claude", "projects")
TEAMS_DIR = os.path.join(HOME, ".claude", "teams")

# Tags que marcam injeção de sistema / slash command — NÃO são fala do humano.
SYSTEM_TAG_PREFIXES = (
    "<local-command", "<command-name", "<command-message", "<command-args",
    "<command-stdout", "<task-notification", "<system-reminder", "<bash-input",
    "<bash-stdout", "<bash-stderr",
)
# Caracteres de box-drawing / fence que sinalizam diagrama/ASCII no texto do assistant.
DIAGRAM_RE = re.compile(r"[┌┐└┘├┤┬┴┼─│╮╭╯╰▶◀▲▼]|```|^\s*[│|]\s", re.M)


def cwd_to_projects_subdir(cwd):
    """~/.claude/projects usa o cwd com '/' e '.' trocados por '-' (e leading dash)."""
    enc = re.sub(r"[^A-Za-z0-9]", "-", cwd)
    return os.path.join(PROJECTS_DIR, enc)


# ---------------------------------------------------------------------------
# Detecção de workspace — mecânica, sem julgamento de LLM.
# Princípio: o handoff PERTENCE ao projeto. Resolve-se a fronteira de projeto
# (.git) dos arquivos que a sessão editou e decide-se se esse projeto é
# multi-módulo. Cobre os 3 cenários: projeto avulso, monorepo (apps/*) e pasta
# guarda-chuva (cwd não é projeto; os projetos estão aninhados).
# ---------------------------------------------------------------------------
PROJECT_MARKERS = ("package.json", "pyproject.toml", "setup.py", "Cargo.toml",
                   "go.mod", "pom.xml", "build.gradle", "composer.json", "Gemfile",
                   "requirements.txt")
WORKSPACE_FILES = ("pnpm-workspace.yaml", "turbo.json", "nx.json", "lerna.json", "go.work")
MODULE_CONTAINERS = ("apps", "packages", "services", "libs", "modules")
IGNORE_DIRS = {"node_modules", ".git", ".claude", ".venv", "venv", "__pycache__",
               "dist", "build", ".next", ".turbo", "target", "vendor", "coverage",
               ".cache", ".pytest_cache", ".ruff_cache", ".mypy_cache", "_archive",
               "_template", "worktrees", ".worktrees", ".playwright-mcp", ".idea",
               ".vscode"}


def _has_workspace_marker(d):
    """True se o dir é raiz de um monorepo FORMAL (pnpm/turbo/nx/.../workspaces)."""
    for wf in WORKSPACE_FILES:
        if os.path.exists(os.path.join(d, wf)):
            return True
    pj = os.path.join(d, "package.json")
    if os.path.exists(pj):
        try:
            if "workspaces" in (json.load(open(pj, encoding="utf-8")) or {}):
                return True
        except Exception:
            pass
    cg = os.path.join(d, "Cargo.toml")
    if os.path.exists(cg):
        try:
            if re.search(r"(?m)^\s*\[workspace\]", open(cg, encoding="utf-8").read()):
                return True
        except Exception:
            pass
    return False


def _is_project_root(d):
    """Fronteira de projeto = tem .git (dir/file/worktree) OU é monorepo formal."""
    return os.path.exists(os.path.join(d, ".git")) or _has_workspace_marker(d)


def resolve_project_root(path, stop_at=None):
    """Sobe de `path` até o 1º ancestral que é fronteira de projeto. None se nada.

    É o que distingue projeto de agrupador: PEDRO/ e VIU/ não têm .git (sobe-se
    através deles), mas PEDRO/mytube e VIU/VIUSTUDIO-TOOLS têm.
    """
    stop_at = os.path.abspath(stop_at or HOME)
    p = os.path.abspath(path)
    if not os.path.isdir(p):
        p = os.path.dirname(p)
    while p and p != os.path.dirname(p):
        if _is_project_root(p):
            return p
        if p == stop_at:
            break
        p = os.path.dirname(p)
    return None


def _has_project_marker(d):
    return any(os.path.exists(os.path.join(d, m)) for m in PROJECT_MARKERS)


def _child_has_marker(d):
    """Algum filho direto de `d` é um projeto? (caso fullstack: X/client, X/server)."""
    try:
        for name in os.listdir(d):
            if name in IGNORE_DIRS or name.startswith("."):
                continue
            sub = os.path.join(d, name)
            if os.path.isdir(sub) and _has_project_marker(sub):
                return True
    except OSError:
        pass
    return False


def slugify_module(name):
    s = re.sub(r"[^a-z0-9_-]+", "-", (name or "").lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s or "modulo"


def _module_candidates(project_root):
    """Módulos internos do projeto-raiz, com poda backend/frontend.

    Um subdir vira UM módulo se tem marker próprio OU tem filhos com marker
    (apps/superlive/{client,server} → 1 módulo 'superlive', NÃO 2). Não desce
    além disso — os papéis-internos não viram módulos separados.
    """
    mods, seen = [], set()

    def add(name, path):
        key = os.path.abspath(path)
        if key not in seen:
            seen.add(key)
            mods.append({"name": name, "path": path})

    for cont in MODULE_CONTAINERS:
        cdir = os.path.join(project_root, cont)
        if not os.path.isdir(cdir):
            continue
        try:
            entries = sorted(os.listdir(cdir))
        except OSError:
            continue
        for name in entries:
            if name in IGNORE_DIRS or name.startswith("."):
                continue
            sub = os.path.join(cdir, name)
            if os.path.isdir(sub) and (_has_project_marker(sub) or _child_has_marker(sub)):
                add(name, sub)

    try:
        entries = sorted(os.listdir(project_root))
    except OSError:
        entries = []
    for name in entries:
        if name in IGNORE_DIRS or name in MODULE_CONTAINERS or name.startswith("."):
            continue
        sub = os.path.join(project_root, name)
        if os.path.isdir(sub) and _has_project_marker(sub):
            add(name, sub)
    return mods


def detect_modules(project_root):
    """{multi, modules:[{name,path}], reason} para um projeto-raiz."""
    if not project_root or not os.path.isdir(project_root):
        return {"multi": False, "modules": [], "reason": "sem projeto-raiz"}
    formal = _has_workspace_marker(project_root)
    mods = _module_candidates(project_root)
    multi = formal or len(mods) >= 2
    if formal:
        reason = "monorepo formal (workspace marker), %d módulos" % len(mods)
    elif multi:
        reason = "%d projetos-membro detectados" % len(mods)
    else:
        reason = "projeto único (%d sub-projeto)" % len(mods)
    return {"multi": multi, "modules": mods, "reason": reason}


def collect_edited_paths(records):
    """file_path de todos os Edit/Write/NotebookEdit do transcript (revela ONDE)."""
    out = []
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        for b in (rec.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            if b.get("name") in ("Edit", "Write", "NotebookEdit"):
                inp = b.get("input") or {}
                fp = inp.get("file_path") or inp.get("notebook_path")
                if fp:
                    out.append(fp)
    return out


def infer_scope(edited_paths, cwd):
    """Projeto-raiz dominante dos arquivos editados (+ módulo se monorepo).

    Devolve project_root, module, multi, modules, handoff_path, edits_by_project,
    edits_by_module, reason. Mecânico — o Claude valida e, se ambíguo, pergunta.
    """
    cwd = os.path.abspath(cwd or os.getcwd())

    def absify(p):
        return os.path.abspath(p if os.path.isabs(p) else os.path.join(cwd, p))

    # absify 1x por edit; resolve_project_root cacheado por path (o mesmo arquivo
    # editado N vezes não re-sobe a árvore).
    abs_paths = [absify(p) for p in edited_paths]
    root_cache, by_proj = {}, {}
    for ap in abs_paths:
        if ap not in root_cache:
            root_cache[ap] = resolve_project_root(ap)
        if root_cache[ap]:
            by_proj[root_cache[ap]] = by_proj.get(root_cache[ap], 0) + 1
    from_edits = bool(by_proj)
    if from_edits:
        project_root = max(by_proj, key=lambda k: by_proj[k])
    else:
        project_root = resolve_project_root(cwd) or cwd

    det = detect_modules(project_root)
    module = None
    module_ambiguous = False
    edits_by_module = {}
    if det["multi"] and det["modules"]:
        prefixes = [(m["name"], os.path.abspath(m["path"]) + os.sep) for m in det["modules"]]
        for ap in abs_paths:
            for name, prefix in prefixes:
                if ap.startswith(prefix):
                    edits_by_module[name] = edits_by_module.get(name, 0) + 1
                    break
        if edits_by_module:
            module = max(edits_by_module, key=lambda k: edits_by_module[k])
            # empate no topo (ex: 2 módulos com a mesma contagem) = ambíguo → a skill pergunta
            top = sorted(edits_by_module.values(), reverse=True)
            module_ambiguous = len(top) >= 2 and top[0] == top[1]

    claude_dir = os.path.join(project_root, ".claude")
    handoff = os.path.join(
        claude_dir, "HANDOFF-%s.md" % slugify_module(module) if module else "HANDOFF.md")
    return {
        "project_root": project_root,
        "module": module,
        "multi": det["multi"],
        "modules": [m["name"] for m in det["modules"]],
        "handoff_path": handoff,
        # from_edits=False → o projeto-raiz foi chutado pelo cwd (sessão sem edits);
        # is_boundary=False → o cwd nem é fronteira de projeto (pasta guarda-chuva).
        # A skill usa os dois pra decidir se confirma o destino com o Pedro.
        "from_edits": from_edits,
        "project_root_is_boundary": _is_project_root(project_root),
        "module_ambiguous": module_ambiguous,
        "edits_by_project": by_proj,
        "edits_by_module": edits_by_module,
        "reason": det["reason"],
    }


def read_jsonl(path):
    out = []
    try:
        # errors="replace": um .jsonl com byte não-UTF-8 (transcript corrompido) não pode
        # derrubar a rodada — a linha vira texto com � e o json.loads dela falha tolerante.
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # tolerante: linha corrompida não derruba
    except OSError:
        pass
    return out


def discover_transcript(cwd, session_id=None):
    """sid-first (determinístico) → sentinel por-cwd → .jsonl mais recente do cwd.

    Com várias sessões no mesmo cwd (monorepo), o sentinel por-cwd e o "mais
    recente" são corridas. O session_id (= nome do .jsonl, único global) resolve
    sem ambiguidade quando a skill o passa via --session "$CLAUDE_CODE_SESSION_ID".
    """
    # 1) sid explícito: o nome do .jsonl É o session_id
    if session_id:
        if cwd:
            cand = os.path.join(cwd_to_projects_subdir(cwd), "%s.jsonl" % session_id)
            if os.path.exists(cand):
                return cand, session_id
        hits = glob.glob(os.path.join(PROJECTS_DIR, "*", "%s.jsonl" % session_id))
        if hits:
            return hits[0], session_id
    # 2) legado: sentinel por-cwd do hook de discovery
    if cwd:
        h = hashlib.sha1(cwd.encode("utf-8")).hexdigest()[:12]
        sentinel = f"/tmp/claude-ata-session-{h}"
        try:
            with open(sentinel) as fh:
                data = json.load(fh)
            tp = data.get("transcript_path")
            if tp and os.path.exists(tp):
                return tp, data.get("session_id")
        except (OSError, json.JSONDecodeError):
            pass
        # 3) fallback: .jsonl mais recente do cwd. getmtime guard: um .jsonl pode ser
        # rotacionado entre o glob e o stat (Claude Code poda sessões) — não derrubar a rodada.
        sub = cwd_to_projects_subdir(cwd)

        def _mtime(p):
            try:
                return os.path.getmtime(p)
            except OSError:
                return -1.0

        cands = sorted(glob.glob(os.path.join(sub, "*.jsonl")), key=_mtime, reverse=True)
        for cand in cands:
            if os.path.exists(cand):
                sid = os.path.splitext(os.path.basename(cand))[0]
                return cand, sid
    return None, None


def _first_cwd(path, max_lines=40):
    """1º campo `cwd` das primeiras linhas de um .jsonl (None se não achar).

    O campo `cwd` está presente nos records user/attachment (verificado em dados
    reais, jun/2026). Lê só o cabeçalho do arquivo — barato mesmo com 270 MB.
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= max_lines:
                    break
                line = line.strip()
                if not line or '"cwd"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cwd = rec.get("cwd")
                if cwd:
                    return cwd
    except OSError:
        pass
    return None


def discover_all_transcripts(project_root):
    """Todos os .jsonl de TODOS os slugs cujo cwd resolve para project_root.

    A engine antiga era mono-sessão; o project-doc precisa varrer os N slugs sob
    um projeto (um por CWD de trabalho — o tools tem 11). Estratégia em 2 passos:
      1) pré-filtro por NOME-de-slug: o encoding cwd→slug é determinístico
         ([^A-Za-z0-9]→'-'), então todo subdir de project_root gera um slug que
         começa com o mesmo prefixo. Evita abrir 303 transcripts à toa.
      2) confirma lendo o `cwd` real do record e resolvendo o project_root — o
         prefixo é necessário mas não suficiente (encoding é lossy).
    """
    project_root = os.path.abspath(project_root)
    enc = re.sub(r"[^A-Za-z0-9]", "-", project_root)
    out = []
    skipped = 0
    for slug_dir in sorted(glob.glob(os.path.join(PROJECTS_DIR, "*"))):
        if not os.path.isdir(slug_dir):
            continue
        name = os.path.basename(slug_dir)
        is_exact = (name == enc)
        if not is_exact and not name.startswith(enc + "-"):
            continue
        for tp in sorted(glob.glob(os.path.join(slug_dir, "*.jsonl"))):
            cwd = _first_cwd(tp)
            if cwd is not None:
                # cwd legível: só entra se resolve PRA ESTE projeto (descarta irmão).
                if resolve_project_root(cwd) == project_root:
                    out.append(tp)
            elif is_exact:
                # slug == enc é o cwd do próprio projeto → seguro mesmo sem cwd legível.
                out.append(tp)
            else:
                # prefixo casa um SUBDIR/irmão e o cwd não confirma → não incluir às cegas
                # (evitava puxar sessões de um projeto vizinho de nome parecido).
                skipped += 1
    if skipped:
        print("collect_engine: %d transcript(s) puladas — slug casa o prefixo de %s "
              "mas o cwd não confirma o projeto." % (skipped, project_root), file=sys.stderr)
    return out


def find_team_transcripts(lead_session_id, cwd):
    """Se há um team liderado por esta sessão, devolve os .jsonl dos teammates.

    INFERIDO / não exercido com clã real nesta sessão: o mapeamento member->.jsonl
    depende dos campos do config.json (leadSessionId + members[]). Implementado de forma
    defensiva — qualquer campo ausente é ignorado e contabilizado, nunca quebra.
    """
    extra = []
    if not lead_session_id:
        return extra
    for cfg_path in glob.glob(os.path.join(TEAMS_DIR, "session-*", "config.json")):
        cfg = {}
        try:
            with open(cfg_path) as fh:
                cfg = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if cfg.get("leadSessionId") != lead_session_id:
            continue
        for m in cfg.get("members", []) or []:
            # tentamos várias chaves possíveis para o id de sessão do teammate
            sid = m.get("sessionId") or m.get("leadSessionId") or m.get("agentSessionId")
            if not sid or sid == lead_session_id:
                continue
            mcwd = m.get("cwd") or cwd
            sub = cwd_to_projects_subdir(mcwd) if mcwd else None
            cand = os.path.join(sub, f"{sid}.jsonl") if sub else None
            if cand and os.path.exists(cand):
                extra.append(cand)
    return extra


def is_human_prompt(rec):
    if rec.get("isMeta"):
        return False
    m = rec.get("message") or {}
    c = m.get("content")
    if not isinstance(c, str):
        return False
    s = c.lstrip()
    return not any(s.startswith(p) for p in SYSTEM_TAG_PREFIXES)


def extract_rejection_speech(tur_str):
    """A fala do humano numa rejeição de tool fica após 'the user said:'."""
    if "the user said:" not in tur_str:
        return None
    tail = tur_str.split("the user said:", 1)[1]
    # corta no rodapé padrão "Note: The user's next message..."
    tail = re.split(r"\n\s*Note:\s", tail, maxsplit=1)[0]
    spoken = tail.strip().strip('"').strip()
    return spoken or None


def anchor_of(text, n=64):
    norm = re.sub(r"\s+", " ", (text or "")).strip().lower()
    return norm[:n]


def collect(records, source_tag):
    """Devolve lista de itens crus (sem id global) a partir de um conjunto de records."""
    items = []
    for rec in records:
        t = rec.get("type")
        ts = rec.get("timestamp") or ""
        if t == "user":
            tur = rec.get("toolUseResult")
            m = rec.get("message") or {}
            content = m.get("content")
            if isinstance(tur, str):
                spoken = extract_rejection_speech(tur)
                if spoken:
                    items.append({"kind": "tool_rejection", "ts": ts, "gate": True,
                                  "text": spoken, "source": source_tag})
                continue
            if isinstance(tur, dict) and isinstance(tur.get("answers"), dict):
                for q, a in tur["answers"].items():
                    items.append({"kind": "ask_answer", "ts": ts, "gate": True,
                                  "question": q, "answer": a, "source": source_tag})
                continue
            if is_human_prompt(rec):
                items.append({"kind": "user_directive", "ts": ts, "gate": True,
                              "text": content, "source": source_tag})
            continue
        if t == "assistant":
            m = rec.get("message") or {}
            for b in (m.get("content") or []):
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text":
                    txt = b.get("text") or ""
                    if not txt.strip():
                        continue
                    kind = "diagram" if DIAGRAM_RE.search(txt) else "assistant_text"
                    items.append({"kind": kind, "ts": ts, "gate": False,
                                  "text": txt, "source": source_tag})
                elif b.get("type") == "tool_use":
                    name = b.get("name")
                    inp = b.get("input") or {}
                    if name == "ExitPlanMode":
                        # plano vai pro LOG (gate=False): o PRD aprovado JÁ é o plano,
                        # não faz sentido o PRD "referenciar" cada versão do plano.
                        items.append({"kind": "plan", "ts": ts, "gate": False,
                                      "text": inp.get("plan", ""), "source": source_tag})
                    elif name in ("TaskCreate", "TaskUpdate"):
                        # tarefas vão pro LOG (gate=False): o PRD descreve o trabalho em
                        # prosa; não precisa citar cada TaskUpdate de status.
                        items.append({"kind": "task", "ts": ts, "gate": False,
                                      "op": name, "input": inp, "source": source_tag})
            continue
        # demais types (mode, attachment, system, last-prompt, etc.) = ruído, ignorado
    return items


# ---------------------------------------------------------------------------
# Tier 4 da cascata de fontes (project-doc): minera transcripts → candidatos crus
# de finding. id estável = hash(TEXTO COMPLETO normalizado + raw_kind) para dedup/journal.
# Usa o texto inteiro (não a âncora truncada de 64 chars): duas falas distintas que
# compartilham os primeiros 64 chars colidiriam e a 2ª seria perdida no journal.
# ---------------------------------------------------------------------------
def finding_id(text, raw_kind):
    norm = re.sub(r"\s+", " ", (text or "")).strip().lower()
    return hashlib.sha1(("%s|%s" % (norm, raw_kind)).encode("utf-8")).hexdigest()[:16]


def emit_findings(project_root, cwd=None, scope="all", session_id=None, gate_only=True):
    """Candidatos crus de finding (tier 4: transcripts) p/ o project-doc.

    scope='all' varre todos os slugs sob project_root; 'session' só a sessão dada.
    Devolve lista de {id, raw_kind, text, anchor, source:{type,ref,ts}, gate},
    dedup por id dentro da varredura (mantém a ocorrência de menor ts).
    """
    if scope == "session":
        tp, _ = discover_transcript(cwd or project_root, session_id)
        transcripts = [tp] if tp else []
    else:
        transcripts = discover_all_transcripts(project_root)

    by_id = {}
    for tp in transcripts:
        ref = os.path.splitext(os.path.basename(tp))[0]
        for it in collect(read_jsonl(tp), source_tag="transcript"):
            if gate_only and not it.get("gate"):
                continue
            if it["kind"] == "ask_answer":
                text = "P: %s\nR: %s" % (it.get("question", ""), it.get("answer", ""))
            else:
                text = it.get("text", "") or ""
            if not text.strip():
                continue
            anchor = anchor_of(text)
            fid = finding_id(text, it["kind"])
            ts = it.get("ts", "")
            prev = by_id.get(fid)
            if prev is None or (ts and ts < prev["source"]["ts"]):
                by_id[fid] = {"id": fid, "raw_kind": it["kind"], "text": text,
                              "anchor": anchor, "gate": bool(it.get("gate")),
                              "source": {"type": "transcript", "ref": ref, "ts": ts}}
    return sorted(by_id.values(), key=lambda f: f["source"]["ts"])


def main():
    ap = argparse.ArgumentParser(description="collect_engine — camada de coleta compartilhada")
    ap.add_argument("--emit-findings", action="store_true", help="minera transcripts → findings JSON")
    ap.add_argument("--discover-all", action="store_true", help="lista os transcripts do projeto (debug)")
    ap.add_argument("--project-root", default=None)
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--scope", choices=["all", "session"], default="all")
    ap.add_argument("--session", default=None)
    ap.add_argument("--all-kinds", action="store_true",
                    help="inclui kinds fracos (assistant_text/diagram/plan/task), não só os gate")
    args = ap.parse_args()

    project_root = args.project_root or resolve_project_root(args.cwd) or os.path.abspath(args.cwd)

    if args.discover_all:
        tps = discover_all_transcripts(project_root)
        print(json.dumps({"project_root": project_root, "count": len(tps), "transcripts": tps},
                         ensure_ascii=False, indent=2))
        return 0
    if args.emit_findings:
        findings = emit_findings(project_root, cwd=args.cwd, scope=args.scope,
                                 session_id=args.session, gate_only=not args.all_kinds)
        print(json.dumps({"project_root": project_root, "scope": args.scope,
                          "count": len(findings), "findings": findings},
                         ensure_ascii=False, indent=2))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
