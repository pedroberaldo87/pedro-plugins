#!/usr/bin/env python3
"""plan_state.py — o plano de implementação como ARQUIVO, não como conversa.

Por que existe
--------------
Antes disto o plano só vivia no transcript. Todo consumidor (o /handoff, o
/visual, a próxima sessão) o RE-DERIVAVA por LLM — e re-derivação por LLM é
lossy: encurta, renomeia fase, e chuta se já foi executado. O caso concreto que
motivou o módulo está em plugins/handoff/lib/extract_ata.py:168,186 —
`excerpt: txt[:1200]` e `likely_executed = commits_after > 0 or edits_after >= 3`.
Um plano de 10 fases + 1 commit vira "concluído".

A correção é estrutural, não de disciplina: o Claude AUTORA o plano uma única
vez (`init`); daí em diante ele só MARCA (`tick`). Quem desenha a árvore é este
programa, lendo o arquivo. Como o modelo nunca redigita um título, não há de
onde a mudança de nome vir.

Mesma forma arquitetural de journal.py e ledger.py: o estado vem do arquivo,
nunca do julgamento do modelo.

Onde mora
---------
<raiz-do-projeto>/.claude/plans/<id>.plan.json — VERSIONADO no git de propósito:
a dor é perda, e /tmp ou ${CLAUDE_PLUGIN_ROOT} morrem no /clear e no bump.
A raiz sai de skills/visual/resolve-dir.sh (a mesma cascata do /visual).

Verbos
------
  init   [--dir D] [--file f|-]  grava/funde o plano; RECUSA renomear id existente
  tick   [--dir D] [plano] <id> --evidencia "..."   marca feito; RECUSA sem prova
  state  [--dir D] [plano] <id> <todo|doing|blocked>
  render [--dir D] [plano] [--mode track|approve] [--format html|text]
  open   [--dir D] [--json]      lista os planos abertos + progresso
  close  [--dir D] [plano]       encerra o plano (para de aparecer no `open`)

Só stdlib (requisito do repo, não preferência).
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
import time

PHASE_RE = re.compile(r"^F\d+$")
ITEM_RE = re.compile(r"^F\d+\.\d+$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")

# A linha didática é o produto do arquivo: é ela que aparece na árvore. Um
# parágrafo ali destrói a leitura de mapa, então o limite é do schema.
DESC_MAX = 140
EVIDENCE_MIN = 8

STATUSES = ("todo", "doing", "blocked", "done")


class PlanError(Exception):
    pass


# ── localização ────────────────────────────────────────────────────────────

def resolve_dir(cwd=None):
    """Diretório dos planos, pela MESMA cascata do /visual (git root → marcador
    de projeto → ~/Desktop). Delega ao shell script pra não haver duas
    implementações da cascata que possam divergir."""
    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "skills", "visual", "resolve-dir.sh")
    script = os.path.normpath(script)
    if not os.path.exists(script):
        raise PlanError("resolve-dir.sh não encontrado em %s — passe --dir" % script)
    out = subprocess.run(["bash", script, cwd or os.getcwd(), "plans"],
                         capture_output=True, text=True)
    target = (out.stdout or "").strip()
    if not target:
        raise PlanError("resolve-dir.sh não devolveu caminho — passe --dir")
    return target


def plan_path(directory, plan_id):
    return os.path.join(directory, "%s.plan.json" % plan_id)


def list_plans(directory):
    if not os.path.isdir(directory):
        return []
    out = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".plan.json"):
            continue
        try:
            with open(os.path.join(directory, name), encoding="utf-8") as fh:
                out.append(json.load(fh))
        except (OSError, ValueError):
            continue  # arquivo corrompido não derruba a listagem
    return out


def pick_plan(directory, plan_id=None):
    """Resolve QUAL plano. Com id, é o id. Sem id, o único ativo — e é erro
    quando há 0 ou 2+, porque adivinhar aqui é como o plano se perde."""
    if plan_id:
        path = plan_path(directory, plan_id)
        if not os.path.exists(path):
            raise PlanError("plano '%s' não existe em %s" % (plan_id, directory))
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    active = [p for p in list_plans(directory) if p.get("status") == "active"]
    if not active:
        raise PlanError("nenhum plano ativo em %s" % directory)
    if len(active) > 1:
        raise PlanError("há %d planos ativos (%s) — diga qual"
                        % (len(active), ", ".join(p["id"] for p in active)))
    return active[0]


def save(directory, plan):
    os.makedirs(directory, exist_ok=True)
    path = plan_path(directory, plan["id"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    return path


# ── schema ─────────────────────────────────────────────────────────────────

def erros_do_plano(plan, exigir=None):
    """Erros de forma, todos de uma vez — devolver um por vez faz o autor
    gastar N rodadas pra escrever um arquivo.

    Devolve a lista em vez de levantar porque quem marca uma tarefa precisa
    separar defeito DA tarefa de defeito alheio; a exceção derruba tudo junto.
    """
    errs = []
    if not isinstance(plan, dict):
        return ["o plano tem que ser um objeto JSON"]
    if not SLUG_RE.match(str(plan.get("id", ""))):
        errs.append("id: precisa ser slug minúsculo (ex: 2026-07-27-arvore-do-plano)")
    if not str(plan.get("title", "")).strip():
        errs.append("title: obrigatório")
    phases = plan.get("phases")
    if not isinstance(phases, list) or not phases:
        errs.append("phases: precisa ser uma lista com ao menos 1 fase")
        return errs

    seen = set()
    for pi, ph in enumerate(phases):
        tag = "fase[%d]" % pi
        pid = str(ph.get("id", ""))
        if not PHASE_RE.match(pid):
            errs.append("%s id '%s': precisa casar F<n> (ex: F1)" % (tag, pid))
        if pid in seen:
            errs.append("%s id '%s': repetido" % (tag, pid))
        seen.add(pid)
        if not str(ph.get("title", "")).strip():
            errs.append("%s title: obrigatório" % tag)
        # detail é opcional e só aparece na página de APROVAÇÃO, dentro do
        # <details> da fase — é onde mora o 🔧 Como / 💡 Por quê / 📁 Toca em.
        det = ph.get("detail")
        if det is not None:
            if not isinstance(det, list) or not all(
                    isinstance(x, str) and x.strip() for x in det):
                errs.append("%s detail: lista de linhas não-vazias, ou ausente" % tag)
        items = ph.get("items")
        if not isinstance(items, list) or not items:
            errs.append("%s items: precisa ter ao menos 1 passo" % tag)
            continue
        for ii, it in enumerate(items):
            itag = "%s passo[%d]" % (tag, ii)
            iid = str(it.get("id", ""))
            if not ITEM_RE.match(iid):
                errs.append("%s id '%s': precisa casar F<n>.<m> (ex: F1.2)" % (itag, iid))
            elif iid.split(".")[0] != pid:
                errs.append("%s id '%s': prefixo não bate com a fase '%s'" % (itag, iid, pid))
            if iid in seen:
                errs.append("%s id '%s': repetido" % (itag, iid))
            seen.add(iid)
            if not str(it.get("title", "")).strip():
                errs.append("%s title: obrigatório" % itag)
            desc = str(it.get("desc", "")).strip()
            if not desc:
                errs.append("%s desc: obrigatório — é a linha didática que aparece na árvore" % itag)
            elif len(desc) > DESC_MAX:
                errs.append("%s desc: %d chars, máximo %d — é UMA linha, não um parágrafo"
                            % (itag, len(desc), DESC_MAX))
            for campo, teto in (("pronto", DESC_MAX), ("pendencia", DESC_MAX),
                                ("grupo", 40), ("requisito", 40)):
                v = str(it.get(campo, "")).strip()
                if v and len(v) > teto:
                    errs.append("%s %s: %d chars, máximo %d" % (itag, campo, len(v), teto))
            if exigir and iid in exigir:
                if not str(it.get("pronto", "")).strip():
                    errs.append(
                        "%s pronto: obrigatório — COMO se prova que esta tarefa terminou.\n"
                        "     Um comando que roda, um arquivo:linha que passa a existir,\n"
                        "     uma tela que muda. Sem isso 'feito' vira palpite." % itag)
                if not str(it.get("requisito", "")).strip():
                    errs.append(
                        "%s requisito: obrigatório — o id do requisito que esta tarefa\n"
                        "     atende, exatamente um. Tarefa que atende dois requisitos são\n"
                        "     duas tarefas: é essa regra que torna a tarefa atômica." % itag)
            st = it.get("status", "todo")
            if st not in STATUSES:
                errs.append("%s status '%s': use %s" % (itag, st, "|".join(STATUSES)))
    return errs


def validate(plan, exigir=None):
    errs = erros_do_plano(plan, exigir)
    if errs:
        raise PlanError("plano inválido:\n  - " + "\n  - ".join(errs))
    return plan


# ── travessia ──────────────────────────────────────────────────────────────

def iter_items(plan):
    for ph in plan["phases"]:
        for it in ph["items"]:
            yield ph, it


def find_item(plan, node_id):
    for ph, it in iter_items(plan):
        if it["id"] == node_id:
            return ph, it
    return None, None


def phase_progress(ph):
    items = ph["items"]
    done = sum(1 for it in items if it.get("status") == "done")
    return done, len(items)


def phase_status(ph):
    """Derivada dos passos — fase NÃO tem estado próprio. Estado duplicado é
    estado que diverge."""
    done, total = phase_progress(ph)
    if done == total:
        return "done"
    if done or any(it.get("status") in ("doing", "blocked") for it in ph["items"]):
        return "doing"
    return "todo"


def plan_progress(plan):
    items = [it for _, it in iter_items(plan)]
    return sum(1 for it in items if it.get("status") == "done"), len(items)


# ── verbos ─────────────────────────────────────────────────────────────────

def cmd_init(args):
    directory = args.dir or resolve_dir()
    raw = sys.stdin.read() if args.file in (None, "-") else open(args.file, encoding="utf-8").read()
    try:
        incoming = json.loads(raw)
    except ValueError as exc:
        raise PlanError("JSON inválido: %s" % exc)
    if not isinstance(incoming, dict) or not isinstance(incoming.get("id"), str):
        validate(incoming)   # sem id não há arquivo pra achar; o validador explica

    path = plan_path(directory, incoming["id"])
    # Cobra os campos novos só do item ACRESCENTADO a um plano que já está no
    # disco: o arquivo que já existe é anterior à regra, e reescrever os itens
    # dele não pode ser o preço de adotá-la.
    novos = set()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                antigos = {n["id"] for ph in json.load(fh).get("phases", [])
                           for n in [ph] + ph.get("items", [])}
        except (OSError, ValueError, KeyError, TypeError):
            antigos = None   # arquivo corrompido: trata como plano novo
        if antigos is not None:
            novos = {it.get("id") for ph in incoming.get("phases", []) or []
                     if isinstance(ph, dict)
                     for it in ph.get("items", []) or []
                     if isinstance(it, dict) and it.get("id") not in antigos}
    validate(incoming, exigir=novos)

    notes = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            stored = json.load(fh)
        incoming, notes = merge(stored, incoming, renames=dict(args.rename or []))
    else:
        incoming.setdefault("created", time.strftime("%Y-%m-%d"))
        incoming.setdefault("status", "active")
        for _, it in iter_items(incoming):
            it.setdefault("status", "todo")
            it.setdefault("evidence", None)
            it.setdefault("done_at", None)

    saved = save(directory, incoming)
    done, total = plan_progress(incoming)
    print("✅ plano '%s' gravado em %s" % (incoming["id"], saved))
    print("   %d fases · %d passos · %d/%d feitos" % (len(incoming["phases"]), total, done, total))
    for n in notes:
        print("   ⚠️  %s" % n)
    return 0


def merge(stored, incoming, renames=None):
    """Funde mantendo o que é ESTADO (status, prova, data) e travando o que é
    IDENTIDADE (título). Renomear exige --rename explícito: é assim que o plano
    para de mudar de nome sozinho entre renders."""
    renames = renames or {}
    notes = []
    old_nodes = {}
    for ph in stored.get("phases", []):
        old_nodes[ph["id"]] = ph
        for it in ph.get("items", []):
            old_nodes[it["id"]] = it

    conflicts = []
    for ph in incoming["phases"]:
        for node in [ph] + ph["items"]:
            nid = node["id"]
            old = old_nodes.get(nid)
            if old is None:
                notes.append("%s: nó novo, acrescentado" % nid)
                if "items" not in node:   # passo (fase não tem estado próprio)
                    node.setdefault("status", "todo")
                    node.setdefault("evidence", None)
                    node.setdefault("done_at", None)
                continue
            if old.get("title") != node.get("title"):
                if renames.get(nid) == node.get("title"):
                    notes.append("%s: renomeado explicitamente" % nid)
                else:
                    conflicts.append((nid, old.get("title"), node.get("title")))
            # estado nunca vem do texto novo — vem do arquivo
            if "items" not in node:
                node["status"] = old.get("status", "todo")
                node["evidence"] = old.get("evidence")
                node["done_at"] = old.get("done_at")
                # registro histórico: um init que omite não pode apagar, pelo mesmo
                # motivo que não apaga a prova. `pendencia` entra com a diferença de
                # que declará-la vazia É resolvê-la de propósito.
                for campo in ("requisito", "grupo", "pronto", "pendencia", "decidido"):
                    if campo not in node and old.get(campo) is not None:
                        node[campo] = old.get(campo)

    if conflicts:
        lines = ["⛔ init recusado: %d nó(s) já existem com outro título." % len(conflicts),
                 "   O id é a identidade — trocar o título aqui é como um plano vira outro",
                 "   entre uma sessão e a seguinte. Pra renomear de propósito, use:",
                 "       --rename <id> \"<novo título>\"", ""]
        for nid, old_t, new_t in conflicts:
            lines.append("   %s" % nid)
            lines.append("     no arquivo: %s" % old_t)
            lines.append("     no init   : %s" % new_t)
        raise PlanError("\n".join(lines))

    new_ids = {n["id"] for ph in incoming["phases"] for n in [ph] + ph["items"]}
    dropped = [i for i in old_nodes if i not in new_ids]
    if dropped:
        notes.append("%d nó(s) do arquivo não vieram neste init e foram MANTIDOS: %s"
                     % (len(dropped), ", ".join(sorted(dropped))))
        for ph in stored["phases"]:
            if ph["id"] in dropped:
                incoming["phases"].append(ph)
            else:
                tgt = next((p for p in incoming["phases"] if p["id"] == ph["id"]), None)
                if tgt is not None:
                    for it in ph.get("items", []):
                        if it["id"] in dropped:
                            tgt["items"].append(it)
        incoming["phases"].sort(key=lambda p: int(p["id"][1:]))
        for p in incoming["phases"]:
            p["items"].sort(key=lambda i: int(i["id"].split(".")[1]))

    for key in ("created", "status"):
        incoming[key] = stored.get(key, incoming.get(key))
    incoming.setdefault("created", time.strftime("%Y-%m-%d"))
    incoming.setdefault("status", "active")
    return incoming, notes


def cmd_tick(args):
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    node_id = args.node

    if PHASE_RE.match(node_id):
        raise PlanError("⛔ '%s' é uma fase. Tique os passos (%s.1, %s.2…) — a fase\n"
                        "   fecha sozinha quando todos os passos dela fecharem."
                        % (node_id, node_id, node_id))
    ph, it = find_item(plan, node_id)
    if it is None:
        raise PlanError("passo '%s' não existe no plano '%s'" % (node_id, plan["id"]))

    ev = (args.evidencia or "").strip()
    if len(ev) < EVIDENCE_MIN:
        raise PlanError(
            "⛔ tick recusado: %s precisa de --evidencia.\n"
            "   Prova concreta: o comando que rodou e a saída, arquivo:linha, ou o sha\n"
            "   do commit. Sem isso, 'concluído' é palpite — foi assim que planos foram\n"
            "   dados como prontos sem estar." % node_id)

    it["status"] = "done"
    it["evidence"] = ev
    it["done_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save(directory, plan)

    pd, pt = phase_progress(ph)
    d, t = plan_progress(plan)
    print("✅ %s concluído  ·  %s agora %d/%d  ·  plano %d/%d" % (node_id, ph["id"], pd, pt, d, t))
    if d == t:
        print("   🏁 todos os passos fechados — encerre com: plan_state.py close %s" % plan["id"])
    return 0


def cmd_state(args):
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    if args.value == "done":
        raise PlanError("'done' só via tick (que exige prova). Use tick.")
    ph, it = find_item(plan, args.node)
    if it is None:
        raise PlanError("passo '%s' não existe no plano '%s'" % (args.node, plan["id"]))
    it["status"] = args.value
    if args.value != "done":
        it["evidence"] = None
        it["done_at"] = None
    save(directory, plan)
    print("· %s → %s" % (args.node, args.value))
    return 0


def cmd_close(args):
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    d, t = plan_progress(plan)
    plan["status"] = "done" if d == t else "abandoned"
    plan["closed_at"] = time.strftime("%Y-%m-%d")
    save(directory, plan)
    print("🏁 plano '%s' encerrado como '%s' (%d/%d passos)" % (plan["id"], plan["status"], d, t))
    if d != t:
        print("   %d passo(s) ficaram sem marcar — continuam registrados no arquivo." % (t - d))
    return 0


def cmd_reopen(args):
    """Volta um plano encerrado pra ativo. Existe porque o caso real é comum:
    fecha o plano, aparece um follow-up, e sem isto o arquivo estaria morto —
    o que empurraria de volta pro modo de falha de criar um plano NOVO com as
    fases renomeadas."""
    directory = args.dir or resolve_dir()
    if not args.plan:
        closed = [p for p in list_plans(directory) if p.get("status") != "active"]
        if not closed:
            raise PlanError("não há plano encerrado em %s" % directory)
        if len(closed) > 1:
            raise PlanError("há %d planos encerrados (%s) — diga qual reabrir"
                            % (len(closed), ", ".join(p["id"] for p in closed)))
        plan = closed[0]
    else:
        plan = pick_plan(directory, args.plan)
    if plan.get("status") == "active":
        raise PlanError("plano '%s' já está ativo" % plan["id"])
    plan["status"] = "active"
    plan.pop("closed_at", None)
    save(directory, plan)
    d, t = plan_progress(plan)
    print("↩️  plano '%s' reaberto (%d/%d passos)" % (plan["id"], d, t))
    return 0


def cmd_open(args):
    directory = args.dir or resolve_dir()
    active = [p for p in list_plans(directory) if p.get("status") == "active"]
    if args.json:
        print(json.dumps([summary(p) for p in active], ensure_ascii=False))
        return 0
    if not active:
        return 0
    for p in active:
        s = summary(p)
        print("📋 %s — %d/%d passos" % (s["title"], s["done"], s["total"]))
        if s["next"]:
            print("   agora: %s · %s" % (s["next"]["id"], s["next"]["title"]))
    return 0


def summary(plan):
    done, total = plan_progress(plan)
    phases = plan["phases"]
    phases_done = [ph["id"] for ph in phases if phase_status(ph) == "done"]
    nxt = None
    for ph in phases:
        if phase_status(ph) != "done":
            pd, pt = phase_progress(ph)
            nxt = {"id": ph["id"], "title": ph["title"], "done": pd, "total": pt}
            break
    return {"id": plan["id"], "title": plan.get("title", plan["id"]),
            "status": plan.get("status", "active"),
            "done": done, "total": total,
            "phases_done": phases_done, "phases_total": len(phases),
            "pending_phases": [ph["id"] for ph in phases if phase_status(ph) != "done"],
            "next": nxt, "path": plan["id"] + ".plan.json"}


# ── brief: "onde nós estamos", em 1-3 bullets ──────────────────────────────
#
# Mora AQUI, e não num heredoc do hook, por dois motivos: texto em shell não é
# testável, e o mesmo texto precisa servir pro hook de fim de turno e pra quem
# chamar na mão. Três estados, e a diferença entre eles é o ponto do pedido que
# originou isto — se tiver concluído, dar uma mensagem confirmada e INEQUÍVOCA:
#
#   em andamento  → feito · agora · falta       (3 bullets)
#   concluído     → ✅ CONCLUÍDO + o que prova   (o plano fechou, falta encerrar)
#   recém-fechado → 🏁 ENCERRADO                (uma vez só — ver --mark-seen)

def _plural(n, s, p=None):
    return "%d %s" % (n, s if n == 1 else (p or s + "s"))


def brief_lines(plan, nudge=None):
    """As linhas de um plano. Lista vazia = não há o que dizer.

    TETO DE 3 BULLETS, e ele é do pedido: "3 bullets curtos" e "dentro dos
    mesmos 1 a 3 bullets". Quando a cobrança do tique entra, ela NÃO vira um
    4º — ela toma o lugar do "Falta", que é o mais dedutível dos três (falta =
    total − feito) e o menos urgente naquele momento. A conta vive aqui, num
    lugar testável, e não montada em pedaços pelo shell.
    """
    s = summary(plan)
    done, total = s["done"], s["total"]
    pd, pt = len(s["phases_done"]), s["phases_total"]

    if s["status"] != "active":
        if done == total and total:
            return ["🏁 **PLANO ENCERRADO — %s**" % s["title"],
                    "• Os %s das %s foram concluídos, cada um com prova anexada."
                    % (_plural(total, "passo"), _plural(pt, "fase")),
                    "• O arquivo fica em `.claude/plans/%s` como registro do que foi feito." % s["path"]]
        return ["🏁 **PLANO ENCERRADO (incompleto) — %s**" % s["title"],
                "• %d de %d passos marcados; %s ficaram sem marcar."
                % (done, total, _plural(total - done, "passo")),
                "• O que ficou aberto continua registrado em `.claude/plans/%s`." % s["path"]]

    if total and done == total:
        return ["✅ **CONCLUÍDO — %s**" % s["title"],
                "• Os %s das %s estão marcados, cada um com prova anexada."
                % (_plural(total, "passo"), _plural(pt, "fase")),
                "• Nada ficou em aberto neste plano. Encerre com `plan_state.py close` "
                "pra ele parar de aparecer aqui."]

    lines = ["📍 **Onde estamos — %s**" % s["title"]]
    if pd:
        lines.append("• **Feito:** %d de %d passos · %s %s fechada%s, com prova em cada passo."
                     % (done, total, _plural(pd, "fase"),
                        "(%s)" % ", ".join(s["phases_done"]), "" if pd == 1 else "s"))
    else:
        lines.append("• **Feito:** %d de %d passos — nenhuma fase fechou ainda." % (done, total))
    nx = s["next"]
    if nx:
        lines.append("• **Agora:** %s · %s — %d de %d passos."
                     % (nx["id"], nx["title"], nx["done"], nx["total"]))
    falta = total - done
    resto = [p for p in s["pending_phases"] if not nx or p != nx["id"]]
    lines.append("• **Falta:** %s%s."
                 % (_plural(falta, "passo"),
                    (" · %s %s" % ("fase" if len(resto) == 1 else "fases", ", ".join(resto)))
                    if resto else ""))
    if nudge:
        lines[-1] = "• " + nudge.strip().lstrip("• ").strip()
    return lines


def _seen_ids(path):
    if not path or not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as fh:
            return {ln.strip() for ln in fh if ln.strip()}
    except OSError:
        return set()


def cmd_brief(args):
    directory = args.dir or resolve_dir()
    seen_path = getattr(args, "mark_seen", None)
    seen = _seen_ids(seen_path)
    blocks, novos = [], []
    for plan in list_plans(directory):
        if plan.get("status") == "active":
            blocks.append(brief_lines(plan, getattr(args, "nudge", None)))
        elif args.closed_since is not None:   # 0 é epoch válido, e é falsy
            # Encerrado DEPOIS do marco → confirma. `--mark-seen` guarda quais
            # já foram confirmados: sem isso o 🏁 repetia a CADA turno até a
            # sessão acabar. Aviso que repete vira ruído, e ruído a gente
            # aprende a ignorar — que é o oposto de "inequívoco".
            if plan["id"] in seen:
                continue
            try:
                if os.path.getmtime(plan_path(directory, plan["id"])) > float(args.closed_since):
                    blocks.append(brief_lines(plan))
                    novos.append(plan["id"])
            except (OSError, ValueError):
                pass
    if not blocks:
        return 0
    if seen_path and novos:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(seen_path)), exist_ok=True)
            with open(seen_path, "a", encoding="utf-8") as fh:
                fh.write("".join(i + "\n" for i in novos))
        except OSError:
            pass  # não conseguiu lembrar → repete; melhor que sumir
    print("\n\n".join("\n".join(b) for b in blocks))
    return 0


# ── render ─────────────────────────────────────────────────────────────────

MARK = {"done": "✅", "doing": "🔄", "blocked": "⛔", "todo": "⬜"}
DOT = {"done": "●", "doing": "◐", "blocked": "✕", "todo": "○"}


def render_text(plan):
    done, total = plan_progress(plan)
    out = ["📋 %s — %d/%d passos" % (plan.get("title", plan["id"]), done, total), ""]
    for ph in plan["phases"]:
        pd, pt = phase_progress(ph)
        out.append("%s %s · %s   (%d/%d)" % (MARK[phase_status(ph)], ph["id"], ph["title"], pd, pt))
        for it in ph["items"]:
            st = it.get("status", "todo")
            out.append("     %s %s  %s" % (DOT[st], it["id"], it["title"]))
            detail = it.get("evidence") if st == "done" else it.get("desc")
            prefix = "prova: " if st == "done" and it.get("evidence") else ""
            out.append("            %s%s" % (prefix, detail or it.get("desc", "")))
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _e(s):
    return html.escape(str(s or ""), quote=True)


def render_html(plan, mode="track"):
    """Emite o HTML do componente .plan-tree do template.html.

    É ESTE programa que escreve a árvore, nunca o modelo — por isso os títulos
    não derivam entre um render e o seguinte.
    """
    done, total = plan_progress(plan)
    pct = int(round(100.0 * done / total)) if total else 0
    parts = ['<div class="plan-tree">',
             '  <div class="pt-head">',
             '    <span class="pt-title">📋 %s</span>' % _e(plan.get("title", plan["id"])),
             '    <span class="pt-count">%d/%d passos</span>' % (done, total),
             '  </div>',
             '  <div class="pt-bar"><div class="pt-fill" style="width:%d%%"></div></div>' % pct]

    for n, ph in enumerate(plan["phases"], 1):
        st = phase_status(ph)
        pd, pt = phase_progress(ph)
        if mode == "approve":
            parts.append('  <div class="feedback-item pt-phase" data-num="%d" data-title="%s">'
                         % (n, _e("%s — %s" % (ph["id"], ph["title"]))))
            parts.append('    <div class="feedback-head">')
            parts.append('      <span class="feedback-num">%d</span>' % n)
            parts.append('      <span class="feedback-title">%s · %s</span>' % (_e(ph["id"]), _e(ph["title"])))
            parts.append('      <div class="feedback-radios">')
            for val, lbl in (("keep", "✓ Manter"), ("change", "✏️ Mudar"), ("remove", "✗ Remover")):
                parts.append('        <label><input type="radio" name="fb-%d" value="%s" '
                             'onchange="onFbChange(this)"> %s</label>' % (n, val, lbl))
            parts.append('      </div>')
            parts.append('    </div>')
        else:
            parts.append('  <div class="pt-phase pt-%s">' % st)
            parts.append('    <div class="pt-phase-head">')
            parts.append('      <span class="pt-mark">%s</span>' % MARK[st])
            parts.append('      <span class="pt-phase-title">%s · %s</span>' % (_e(ph["id"]), _e(ph["title"])))
            parts.append('      <span class="pt-phase-count">%d/%d</span>' % (pd, pt))
            parts.append('    </div>')

        parts.append('    <ul class="pt-items">')
        for it in ph["items"]:
            ist = it.get("status", "todo")
            parts.append('      <li class="pt-item pt-%s">' % ist)
            parts.append('        <span class="pt-dot">%s</span>' % DOT[ist])
            parts.append('        <span class="pt-item-title"><span class="pt-id">%s</span>%s</span>'
                         % (_e(it["id"]), _e(it["title"])))
            if ist == "done" and it.get("evidence"):
                parts.append('        <span class="pt-evidence">prova: %s</span>' % _e(it["evidence"]))
            else:
                parts.append('        <span class="pt-desc">%s</span>' % _e(it.get("desc", "")))
            parts.append('      </li>')
        parts.append('    </ul>')
        if mode == "approve":
            if ph.get("detail"):
                parts.append('    <details class="item-detail">')
                parts.append('      <summary><span class="read-dot"></span> detalhes '
                             '<span class="dchev">›</span></summary>')
                parts.append('      <div class="detail-body">')
                for line in ph["detail"]:
                    parts.append('        <p>%s</p>' % _e(line))
                parts.append('      </div>')
                parts.append('    </details>')
            parts.append('    <textarea class="feedback-textarea" placeholder="O que mudar..."></textarea>')
        parts.append('  </div>')

    parts.append('</div>')
    return "\n".join(parts) + "\n"


def cmd_render(args):
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    sys.stdout.write(render_text(plan) if args.format == "text"
                     else render_html(plan, args.mode))
    return 0


# A moldura da página é FIXA. Se o modelo remontasse o cabeçalho a cada rodada,
# o plano mudaria de aparência entre um render e o seguinte — que é metade da
# queixa original ("mudando o jeito que ele está sendo apresentado").
PAGE_COPY = {
    "track": ("em execução", "Acompanhamento · atualizado a cada passo",
              "Onde a execução está",
              "Sem rádio nenhum: esta página não pede nada, só mostra o estado do arquivo do plano."),
    "approve": ("aguardando aprovação", "Aprovação · o plano completo",
                "O plano, pra você aprovar",
                "A árvore É a lista: o veredito mora na fase, e não há segunda tabela no fim."),
}

CLOSING_BOX = """
  <div class="feedback-box">
    <h2>🏁 Fechamento</h2>
    <p class="feedback-intro">Os vereditos já estão nas fases acima — aqui não tem segunda tabela.
       Só o progresso, uma observação geral se quiser, e o envio.</p>
    <div class="fb-progress">
      <strong id="fb-done">0</strong>/<span id="fb-total">0</span> itens revisados
      <div class="fb-progress-bar"><div class="fb-progress-fill" id="fb-bar"></div></div>
    </div>
    <div class="feedback-general">
      <label for="fb-general">Observação geral (opcional)</label>
      <textarea id="fb-general" placeholder="Algo sobre o plano como um todo..."></textarea>
    </div>
    <div class="sticky-actions">
      <button class="btn" onclick="approveAll(this)">✓ Aprovar tudo</button>
      <button class="btn btn-primary" onclick="copyFeedback(this)">📋 Copiar feedback</button>
    </div>
  </div>
"""


def cmd_page(args):
    """Monta a PÁGINA inteira (template + árvore) e devolve o caminho.

    Nome de arquivo estável por plano: a página de acompanhamento é reescrita
    no MESMO caminho a cada tick, então o usuário dá refresh na aba que já está
    aberta em vez de acumular 51 arquivos como antes.
    """
    import random
    import string

    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    here = os.path.dirname(os.path.abspath(__file__))
    tpl_path = os.path.join(here, "..", "skills", "visual", "template.html")
    tpl_path = os.path.normpath(tpl_path)
    if not os.path.exists(tpl_path):
        raise PlanError("template.html não encontrado em %s" % tpl_path)
    with open(tpl_path, encoding="utf-8") as fh:
        tpl = fh.read()

    estado, kicker, h1, sub = PAGE_COPY[args.mode]
    done, total = plan_progress(plan)
    body = [
        '<div class="wrap">',
        '  <div class="ident-strip">',
        # directory é <raiz>/.claude/plans — dois níveis acima é o nome do projeto
        '    <span><span class="ik">Projeto</span><span class="iv">%s</span></span>'
        % _e(os.path.basename(os.path.abspath(os.path.join(directory, "..", "..")))),
        '    <span><span class="ik">Plano</span><span class="iv">%s</span></span>'
        % _e(plan.get("title", plan["id"])),
        '    <span><span class="ik">Gerado de</span><code class="inline">'
        'plan_state.py page --mode %s</code></span>' % args.mode,
        '    <span class="estado estado-gerado">%s</span>' % _e(estado),
        '  </div>',
        '  <div class="pill">%s</div>' % _e(kicker),
        '  <h1>%s</h1>' % _e(h1),
        '  <p class="subtitle">%s</p>' % _e(sub),
        '  <div class="meta-chips">',
        '    <span class="chip">📋 %d fases · %d passos</span>' % (len(plan["phases"]), total),
        '    <span class="chip primary">%d/%d feitos</span>' % (done, total),
        '    <span class="chip">📅 %s</span>' % time.strftime("%Y-%m-%d"),
        '  </div>',
        render_html(plan, args.mode),
    ]
    if args.mode == "approve":
        body.append(CLOSING_BOX)
    body.append('</div>')

    token = "%s-%s" % (time.strftime("%Y%m%d%H%M"),
                       "".join(random.choice(string.ascii_lowercase + string.digits)
                               for _ in range(6)))
    i = tpl.index("<body>")
    j = tpl.index("<script>", i)
    page = (tpl[:i] + '<body>\n<script>window.VISUAL_SESSION = "%s";</script>\n' % token
            + "\n".join(body) + "\n" + tpl[j:])
    page = re.sub(r"<title>.*?</title>",
                  "<title>%s — %s</title>" % (_e(h1), _e(plan.get("title", plan["id"]))),
                  page, count=1, flags=re.S)

    out = args.out
    if not out:
        vis = subprocess.run(["bash", os.path.join(here, "..", "skills", "visual", "resolve-dir.sh"),
                              os.getcwd(), "visual"], capture_output=True, text=True)
        vdir = (vis.stdout or "").strip()
        if not vdir:
            raise PlanError("não consegui resolver o diretório do /visual — passe --out")
        out = os.path.join(vdir, "plano-%s-%s.html" % (plan["id"], args.mode))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(out)
    return 0


# ── cli ────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(prog="plan_state.py", description=__doc__.split("\n")[0])
    p.add_argument("--dir", help="diretório dos planos (default: cascata do /visual)")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("init", help="grava/funde o plano (recusa renomear id existente)")
    q.add_argument("--file", default="-", help="arquivo JSON, ou - pra stdin")
    q.add_argument("--rename", nargs=2, action="append", metavar=("ID", "TITULO"),
                   help="autoriza renomear um id existente")
    q.set_defaults(func=cmd_init)

    q = sub.add_parser("tick", help="marca um passo como feito (exige prova)")
    q.add_argument("plan", nargs="?")
    q.add_argument("node")
    q.add_argument("--evidencia", "--evidence", dest="evidencia", default="")
    q.set_defaults(func=cmd_tick)

    q = sub.add_parser("state", help="muda o estado de um passo (todo/doing/blocked)")
    q.add_argument("plan", nargs="?")
    q.add_argument("node")
    q.add_argument("value", choices=STATUSES)
    q.set_defaults(func=cmd_state)

    q = sub.add_parser("render", help="desenha a árvore do plano")
    q.add_argument("plan", nargs="?")
    q.add_argument("--mode", choices=("track", "approve"), default="track")
    q.add_argument("--format", choices=("html", "text"), default="html")
    q.set_defaults(func=cmd_render)

    q = sub.add_parser("page", help="monta a PÁGINA inteira (template + árvore) e imprime o caminho")
    q.add_argument("plan", nargs="?")
    q.add_argument("--mode", choices=("track", "approve"), default="track")
    q.add_argument("--out", help="caminho do HTML (default: <dir do /visual>/plano-<id>-<modo>.html)")
    q.set_defaults(func=cmd_page)

    q = sub.add_parser("brief", help="1-3 bullets de 'onde nós estamos' (usado pelo hook de fim de turno)")
    q.add_argument("--closed-since", dest="closed_since",
                   help="epoch: também confirma plano encerrado depois desse instante")
    q.add_argument("--mark-seen", dest="mark_seen",
                   help="arquivo onde anotar os encerramentos já confirmados (não repete)")
    q.add_argument("--nudge", help="cobrança a incluir: ENTRA NO LUGAR do bullet 'Falta', "
                                   "nunca como 4º (o teto de 3 é do pedido)")
    q.set_defaults(func=cmd_brief)

    q = sub.add_parser("open", help="lista os planos abertos")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_open)

    q = sub.add_parser("close", help="encerra o plano")
    q.add_argument("plan", nargs="?")
    q.set_defaults(func=cmd_close)

    q = sub.add_parser("reopen", help="volta um plano encerrado pra ativo")
    q.add_argument("plan", nargs="?")
    q.set_defaults(func=cmd_reopen)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    # `tick F1.2` (sem nome de plano) e `tick meu-plano F1.2` resolvem sozinhos:
    # com `plan` opcional antes de `node` obrigatório, argparse dá o único
    # argumento ao obrigatório. Verificado nesta sessão, não presumido.
    try:
        return args.func(args)
    except PlanError as exc:
        sys.stderr.write("%s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
