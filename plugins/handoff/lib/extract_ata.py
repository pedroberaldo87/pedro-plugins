#!/usr/bin/env python3
"""
extract_ata.py — extrator read-only do transcript da sessão para o rito ATA/PRD.

Lê o(s) transcript(s) .jsonl de uma sessão Claude Code e GERA, mecanicamente
(sem julgamento de LLM):
  • LOG-<sessão>.md  — ata verbatim, cronológica, cada item com um ID estável
  • MANIFEST (json)  — lista de todos os itens {id, type, timestamp, gate, anchor}

O LOG é a "prova" verbatim; o MANIFEST é o que o gate de completude usa para
verificar que o PRD (HANDOFF.md, escrito pelo Claude) referencia cada item forte.

Trabalha sobre o schema REAL do .jsonl (verificado por parse, jun/2026):
  - prompt do humano: record type=user, message.content STRING, sem isMeta,
    sem tags de sistema (<command-*>, <local-command-*>, <task-notification>, <system-reminder>)
  - feedback de rejeição de tool (fala do humano): record type=user com
    toolUseResult STRING contendo "the user said:"
  - resposta de AskUserQuestion: record type=user com toolUseResult dict que tem "answers"
  - plano: record type=assistant, bloco tool_use name=ExitPlanMode, input.plan
  - tarefas: tool_use TaskCreate / TaskUpdate (NÃO TodoWrite — não existe nesta build)
  - diagramas/ASCII e discussão: bloco text do assistant (vive só no texto, nenhum hook de tool vê)

Tolerante a schema: campo ausente nunca quebra; o que não for reconhecido é ignorado
(e contabilizado em stats), não inventado.

Uso:
  extract_ata.py --transcript <path.jsonl> [--transcript <outro.jsonl> ...] \\
                 --session <id> --out-log <LOG.md> --out-manifest <MANIFEST.json> \\
                 [--cwd <dir>] [--quiet]
  extract_ata.py --auto --cwd <dir> --out-log ... --out-manifest ...
      (auto: descobre o transcript via sentinel /tmp do hook de discovery; fallback = .jsonl mais
       recente da pasta projects do cwd; agrega transcripts de teammates se houver clã)
"""
import argparse, glob, hashlib, json, os, re, sys, time

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


def read_jsonl(path):
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
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


def discover_transcript(cwd):
    """Sentinel do hook de discovery primeiro; fallback = .jsonl mais recente do cwd."""
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
        sub = cwd_to_projects_subdir(cwd)
        cands = sorted(glob.glob(os.path.join(sub, "*.jsonl")), key=os.path.getmtime, reverse=True)
        if cands:
            sid = os.path.splitext(os.path.basename(cands[0]))[0]
            return cands[0], sid
    return None, None


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


KIND_PREFIX = {"user_directive": "d", "tool_rejection": "r", "ask_answer": "a",
               "plan": "p", "task": "t", "diagram": "g", "assistant_text": "x"}
KIND_LABEL = {"user_directive": "Direcionamento do Pedro", "tool_rejection": "Direcionamento (rejeição/feedback)",
              "ask_answer": "Decisão (AskUserQuestion)", "plan": "Plano (ExitPlanMode)",
              "task": "Tarefa", "diagram": "Diagrama / ASCII", "assistant_text": "Discussão (assistant)"}


def build(items, session_id):
    """Ordena por timestamp, atribui IDs estáveis e devolve (log_md, manifest)."""
    items.sort(key=lambda it: (it.get("ts") or "", KIND_PREFIX.get(it["kind"], "z")))
    counters = {}
    manifest = []
    log_lines = [f"# LOG — ata verbatim da sessão `{session_id}`", "",
                 "> Gerado mecanicamente por extract_ata.py. NÃO editar à mão. Verbatim, cronológico.",
                 "> Cada item tem um ID estável; o PRD (HANDOFF.md) referencia os IDs fortes.", ""]
    for it in items:
        pfx = KIND_PREFIX.get(it["kind"], "z")
        counters[pfx] = counters.get(pfx, 0) + 1
        iid = f"{pfx}{counters[pfx]}"
        if it["kind"] == "ask_answer":
            body = f"**P:** {it['question']}\n\n**R:** {it['answer']}"
            anchor = anchor_of(it["question"])
        elif it["kind"] == "task":
            body = "```json\n" + json.dumps(it["input"], ensure_ascii=False, indent=2) + "\n```"
            anchor = anchor_of(f"{it.get('op')} {json.dumps(it['input'], ensure_ascii=False)}")
        else:
            body = it.get("text", "")
            anchor = anchor_of(body)
        label = KIND_LABEL.get(it["kind"], it["kind"])
        src = "" if it.get("source") in (None, "self") else f" · _{it['source']}_"
        log_lines.append(f"### [{iid}] {it.get('ts','')} · {label}{src}")
        log_lines.append("")
        log_lines.append(body)
        log_lines.append("")
        manifest.append({"id": iid, "type": it["kind"], "ts": it.get("ts", ""),
                         "gate": bool(it["gate"]), "anchor": anchor,
                         "source": it.get("source", "self")})
    return "\n".join(log_lines), manifest


def build_prospective(records, items):
    """Deriva o bloco prospectivo MECÂNICO (o "o que falta fazer") do transcript.

    O LOG/manifest cobrem o passado; este bloco cobre o futuro estruturado que JÁ
    existe no transcript (CONFIRMADO em dados reais, jun/2026), em vez de confiar 100%
    no Claude lembrar de cabeça:
      • open_tasks — tarefas cujo status final != completed/deleted (trabalho aberto)
      • last_plan  — o último ExitPlanMode (candidato a próximos passos; pode já ter
                     sido executado, por isso "candidato")

    Schema real dos tool_results de Task (record type=user, campo toolUseResult dict):
      - TaskCreate -> {"task": {"id": "N", "subject": "..."}}
      - TaskUpdate -> {"taskId": "N", "statusChange": {"from": "...", "to": "..."}}
    O id REAL vem daí — NUNCA de um contador sequencial (1,2,3...), senão dá
    falso-positivo (RAIOX: 7 "abertas" no join ingênuo vs 0 reais). O collect() acima
    ignora esses records; aqui a gente os lê só pra derivar o status final.
    """
    created = {}       # id(str) -> subject
    last_status = {}   # id(str) -> (ts, status)
    for rec in records:
        if rec.get("type") != "user":
            continue
        tur = rec.get("toolUseResult")
        if not isinstance(tur, dict):
            continue
        ts = rec.get("timestamp") or ""
        # TaskCreate (forma single): {"task": {"id","subject"}}
        task = tur.get("task")
        if isinstance(task, dict) and task.get("id") is not None:
            created[str(task["id"])] = task.get("subject", "") or ""
        # TaskCreate (forma batch, defensivo): {"tasks": [{"id","subject"}, ...]}
        if isinstance(tur.get("tasks"), list):
            for t in tur["tasks"]:
                if isinstance(t, dict) and t.get("id") is not None:
                    created[str(t["id"])] = t.get("subject", "") or t.get("title", "") or ""
        # TaskUpdate: {"taskId","statusChange":{"to"}} — guarda o status de maior ts
        tid = tur.get("taskId")
        sc = tur.get("statusChange")
        if tid is not None and isinstance(sc, dict) and sc.get("to"):
            cur = last_status.get(str(tid))
            if cur is None or ts >= cur[0]:
                last_status[str(tid)] = (ts, sc["to"])

    open_tasks = []
    for tid, subject in created.items():
        st = last_status.get(tid)
        status = st[1] if st else "pending"
        if status not in ("completed", "deleted"):
            open_tasks.append({"id": tid, "subject": subject, "status": status})

    # último plano (ExitPlanMode) — kind já coletado pelo collect()
    plans = [it for it in items if it.get("kind") == "plan" and (it.get("text") or "").strip()]
    last_plan = None
    if plans:
        plans.sort(key=lambda it: it.get("ts") or "")
        p = plans[-1]
        txt = p.get("text", "") or ""
        last_plan = {"ts": p.get("ts", ""), "excerpt": txt[:1200]}
        # Esse plano JÁ foi executado nesta sessão? Conta edits/commits APÓS o ts do plano.
        # Se sim, ele é REGISTRO (vai pra "O Que Foi Feito"), não trabalho a fazer — evita o
        # próximo Claude "reimplementar tudo" ao retomar um handoff de implementação concluída.
        pts = last_plan["ts"]
        edits_after = commits_after = 0
        for rec in records:
            if rec.get("type") != "assistant" or (rec.get("timestamp") or "") <= pts:
                continue
            for b in (rec.get("message") or {}).get("content") or []:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                nm = b.get("name")
                if nm in ("Edit", "Write", "NotebookEdit"):
                    edits_after += 1
                elif nm == "Bash" and "git commit" in str((b.get("input") or {}).get("command", "")):
                    commits_after += 1
        last_plan["executed_after"] = {"edits": edits_after, "commits": commits_after}
        last_plan["likely_executed"] = commits_after > 0 or edits_after >= 3

    return {"open_tasks": open_tasks, "last_plan": last_plan}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", action="append", default=[], help="caminho .jsonl (repetível)")
    ap.add_argument("--session", default=None)
    ap.add_argument("--cwd", default=os.getcwd())
    ap.add_argument("--auto", action="store_true", help="descobre transcript + agrega clã")
    ap.add_argument("--out-log", default=None)
    ap.add_argument("--out-manifest", default=None)
    ap.add_argument("--out-dir", default=None,
                    help="diretório onde gravar LOG-<sid>.md e manifest-<sid>.json (nomeados após descobrir o sid)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    transcripts = list(args.transcript)
    session_id = args.session
    if args.auto and not transcripts:
        tp, sid = discover_transcript(args.cwd)
        if not tp:
            print("ERRO: não encontrei o transcript da sessão (sentinel ausente e nenhum .jsonl no cwd).",
                  file=sys.stderr)
            return 3
        transcripts.append(tp)
        session_id = session_id or sid
        for extra in find_team_transcripts(session_id, args.cwd):
            if extra not in transcripts:
                transcripts.append(extra)

    if not transcripts:
        print("ERRO: nenhum transcript informado (use --transcript ou --auto).", file=sys.stderr)
        return 2
    session_id = session_id or os.path.splitext(os.path.basename(transcripts[0]))[0]

    # Resolve paths de saída. --out-dir nomeia os arquivos a partir do session_id descoberto.
    out_log, out_manifest = args.out_log, args.out_manifest
    if args.out_dir:
        out_log = out_log or os.path.join(args.out_dir, f"LOG-{session_id}.md")
        out_manifest = out_manifest or os.path.join(args.out_dir, f"manifest-{session_id}.json")
    if not out_log or not out_manifest:
        print("ERRO: informe --out-dir OU (--out-log e --out-manifest).", file=sys.stderr)
        return 2

    all_items = []
    all_records = []
    stats = {"transcripts": len(transcripts), "records": 0}
    for idx, tp in enumerate(transcripts):
        recs = read_jsonl(tp)
        stats["records"] += len(recs)
        all_records.extend(recs)
        tag = "self" if idx == 0 else f"teammate:{os.path.splitext(os.path.basename(tp))[0][:8]}"
        all_items.extend(collect(recs, tag))

    log_md, manifest = build(all_items, session_id)
    prospective = build_prospective(all_records, all_items)

    os.makedirs(os.path.dirname(os.path.abspath(out_log)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_manifest)), exist_ok=True)
    with open(out_log, "w", encoding="utf-8") as fh:
        fh.write(log_md + "\n")
    manifest_doc = {"session": session_id, "transcripts": transcripts,
                    "generated_unix": int(time.time()), "log_path": out_log,
                    "prospective": prospective, "items": manifest}
    with open(out_manifest, "w", encoding="utf-8") as fh:
        json.dump(manifest_doc, fh, ensure_ascii=False, indent=2)

    by_kind = {}
    for it in manifest:
        by_kind[it["type"]] = by_kind.get(it["type"], 0) + 1
    gate_items = [it["id"] for it in manifest if it["gate"]]
    if not args.quiet:
        print(json.dumps({"session": session_id, **stats, "items_total": len(manifest),
                          "by_kind": by_kind, "gate_items": gate_items,
                          "prospective": prospective,
                          "log_path": out_log, "manifest_path": out_manifest},
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
