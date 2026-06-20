#!/usr/bin/env python3
"""
extract_ata.py — extrator read-only do transcript da sessão para o rito ATA/PRD.

Lê o(s) transcript(s) .jsonl de uma sessão Claude Code e GERA, mecanicamente
(sem julgamento de LLM):
  • LOG-<sessão>.md  — ata verbatim, cronológica, cada item com um ID estável
  • MANIFEST (json)  — lista de todos os itens {id, type, timestamp, gate, anchor}

O LOG é a "prova" verbatim; o MANIFEST é o que o gate de completude usa para
verificar que o PRD (HANDOFF.md, escrito pelo Claude) referencia cada item forte.

A CAMADA DE COLETA (schema do .jsonl, descoberta de transcript, resolução de
escopo, collect()/anchor_of) vive em collect_engine.py — a fonte-da-verdade está
em _shared/ e é vendorada como sibling por scripts/sync-shared.sh. Este módulo
fica só com o que é específico do rito do handoff: o formato do LOG (build),
o prospecto (build_prospective), o sentinel do gate e a CLI.

Uso:
  extract_ata.py --transcript <path.jsonl> [--transcript <outro.jsonl> ...] \\
                 --session <id> --out-log <LOG.md> --out-manifest <MANIFEST.json> \\
                 [--cwd <dir>] [--quiet]
  extract_ata.py --auto --cwd <dir> --out-log ... --out-manifest ...
      (auto: descobre o transcript via sentinel /tmp do hook de discovery; fallback = .jsonl mais
       recente da pasta projects do cwd; agrega transcripts de teammates se houver clã)
"""
import argparse, json, os, sys, time

# A camada de coleta é vendorada como sibling (collect_engine.py). Inserir o dir
# do script no path torna o import robusto a como o python foi invocado.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from collect_engine import (  # noqa: E402
        anchor_of, collect, collect_edited_paths, detect_modules, discover_transcript,
        find_team_transcripts, infer_scope, read_jsonl, resolve_project_root,
        _is_project_root,
    )
except ImportError as e:
    # collect_engine.py é vendorado por scripts/sync-shared.sh; se sumiu (sync esquecido,
    # ou o arquivo não foi commitado/empacotado), falha ALTO e acionável em vez de traceback cru.
    sys.stderr.write(
        "ERRO: extract_ata.py não achou collect_engine.py ao lado dele (%s).\n"
        "A engine compartilhada é vendorada — rode: bash scripts/sync-shared.sh\n"
        "Detalhe: %s\n" % (os.path.dirname(os.path.abspath(__file__)), e))
    sys.exit(4)


def write_gate_sentinel(session_id, scope, manifest_path=None):
    """Bilhete por-sessão pro gate achar o handoff + manifest REAIS (não derivados).

    Gravar o manifest_path explícito (em vez de o gate adivinhar
    {project_root}/.claude/ata/manifest-<sid>.json) deixa o vínculo robusto a
    --out-dir custom e a qualquer divergência de localização.
    """
    if not session_id:
        return
    try:
        with open("/tmp/claude-handoff-target-%s" % session_id, "w") as fh:
            json.dump({"project_root": scope.get("project_root"),
                       "handoff_path": scope.get("handoff_path"),
                       "manifest_path": manifest_path,
                       "module": scope.get("module")}, fh)
    except OSError:
        pass


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
    ap.add_argument("--detect-workspace", action="store_true",
                    help="só detecta o workspace do --cwd e imprime o JSON (debug)")
    ap.add_argument("--out-log", default=None)
    ap.add_argument("--out-manifest", default=None)
    ap.add_argument("--out-dir", default=None,
                    help="diretório do LOG/manifest. Se ausente, deriva do projeto-raiz resolvido pelos edits.")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    # Modo debug: detecta o workspace do cwd e sai (não toca em transcript).
    if args.detect_workspace:
        cwd = os.path.abspath(args.cwd)
        if _is_project_root(cwd):
            out = {"cwd": cwd, "project_root": cwd, **detect_modules(cwd)}
        else:
            out = {"cwd": cwd, "project_root": None,
                   "note": "cwd não é fronteira de projeto (guarda-chuva); o escopo real "
                           "sai de infer_scope pelos arquivos editados",
                   **detect_modules(cwd)}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    transcripts = list(args.transcript)
    session_id = args.session
    if args.auto and not transcripts:
        tp, sid = discover_transcript(args.cwd, session_id)
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

    all_items = []
    all_records = []
    stats = {"transcripts": len(transcripts), "records": 0}
    for idx, tp in enumerate(transcripts):
        recs = read_jsonl(tp)
        stats["records"] += len(recs)
        all_records.extend(recs)
        tag = "self" if idx == 0 else f"teammate:{os.path.splitext(os.path.basename(tp))[0][:8]}"
        all_items.extend(collect(recs, tag))

    # Escopo: projeto-raiz dominante dos arquivos editados + módulo (se monorepo).
    scope = infer_scope(collect_edited_paths(all_records), args.cwd)

    # Resolve paths de saída. --out-dir explícito vence; senão deriva do projeto-raiz
    # (LOG/manifest ficam junto do handoff, em {project_root}/.claude/ata).
    out_dir = args.out_dir or os.path.join(scope["project_root"], ".claude", "ata")
    out_log = args.out_log or os.path.join(out_dir, f"LOG-{session_id}.md")
    out_manifest = args.out_manifest or os.path.join(out_dir, f"manifest-{session_id}.json")

    # Bilhete por-sessão pro gate, com o manifest REAL (não derivado).
    write_gate_sentinel(session_id, scope, out_manifest)

    log_md, manifest = build(all_items, session_id)
    prospective = build_prospective(all_records, all_items)

    os.makedirs(os.path.dirname(os.path.abspath(out_log)), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(out_manifest)), exist_ok=True)
    with open(out_log, "w", encoding="utf-8") as fh:
        fh.write(log_md + "\n")
    manifest_doc = {"session": session_id, "transcripts": transcripts,
                    "generated_unix": int(time.time()), "log_path": out_log,
                    "scope": scope, "prospective": prospective, "items": manifest}
    with open(out_manifest, "w", encoding="utf-8") as fh:
        json.dump(manifest_doc, fh, ensure_ascii=False, indent=2)

    by_kind = {}
    for it in manifest:
        by_kind[it["type"]] = by_kind.get(it["type"], 0) + 1
    gate_items = [it["id"] for it in manifest if it["gate"]]
    if not args.quiet:
        print(json.dumps({"session": session_id, **stats, "items_total": len(manifest),
                          "by_kind": by_kind, "gate_items": gate_items,
                          "scope": scope, "prospective": prospective,
                          "log_path": out_log, "manifest_path": out_manifest},
                         ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
