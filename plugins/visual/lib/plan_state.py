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


def le_plano(path):
    """Lê UM arquivo de plano nomeando-o quando ele não abre.

    `json.load` cru mata o programa com traceback e rc=1, sem dizer sequer qual
    arquivo está torto — e o plano é justamente o registro que este módulo existe
    pra não perder. Quem lista (`list_plans`) segue engolindo: um arquivo torto não
    pode derrubar a listagem dos outros.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        raise PlanError("plano ilegível em %s: %s" % (path, exc))
    except ValueError as exc:
        raise PlanError("plano ilegível em %s: %s\n"
                        "   O arquivo existe e não é JSON válido. Conserte-o à mão —\n"
                        "   é o registro do que já foi feito, e nada aqui o reescreve." % (path, exc))


def pick_plan(directory, plan_id=None):
    """Resolve QUAL plano. Com id, é o id. Sem id, o único ativo — e é erro
    quando há 0 ou 2+, porque adivinhar aqui é como o plano se perde."""
    if plan_id:
        path = plan_path(directory, plan_id)
        if not os.path.exists(path):
            raise PlanError("plano '%s' não existe em %s" % (plan_id, directory))
        return le_plano(path)
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
            # Quem escreve o JSON do init é o modelo, e sem isto `status: "done"`
            # entrava à mão com `evidence: null` — o mesmo "concluído sem estar" que o
            # tick recusa. O teto da prova é o mesmo dos dois lados, senão há dois.
            elif st == "done" and len(str(it.get("evidence") or "").strip()) < EVIDENCE_MIN:
                errs.append(
                    "%s status 'done' sem prova: marcar feito é `tick <id> --evidencia`,\n"
                    "     que grava a prova junto. Escrito à mão, 'concluído' é palpite." % itag)
    return errs


def validate(plan, exigir=None, reqs=None):
    errs = erros_do_plano(plan, exigir)
    # Citação que aponta pro nada é o quarto estado do fio, e ele NÃO é aviso: é erro
    # que recusa gravar. Sem isto a citação apodrece em silêncio — foi assim que 7 de
    # 154 itens de um plano real citaram artigo de lei sem ninguém nunca conferir se o
    # artigo existia. `reqs` vazio desliga a checagem: projeto sem documento de
    # requisitos não é erro, é o caso comum.
    if reqs:
        for _, it in iter_items(plan):
            rid = str(it.get("requisito", "")).strip()
            if rid and rid not in reqs:
                errs.append("%s requisito '%s': não existe no documento de requisitos.\n"
                            "     Ids conhecidos: %s" % (it.get("id", "?"), rid,
                                                         ", ".join(sorted(reqs)[:8]) or "(nenhum)"))
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
    stored = le_plano(path) if os.path.exists(path) else None
    # O que é COBRADO é a tarefa que nasce agora: todas, num plano novo; só as
    # acrescentadas, num plano que já está no disco. O arquivo que já existe é
    # anterior à regra, e reescrever os itens dele não pode ser o preço de adotá-la
    # ("zero migração") — mas plano novo não tem essa desculpa, e deixá-lo passar
    # faria o portão morder só a partir da SEGUNDA gravação, que é o caso raro.
    antigos = set()
    if stored is not None:
        try:
            antigos = {n["id"] for ph in stored.get("phases", [])
                       for n in [ph] + ph.get("items", [])}
        except (AttributeError, KeyError, TypeError):
            # estrutura torta: não dá pra saber o que é velho, e cobrar tudo
            # apagaria um plano em curso por causa de um nó sem id. Não cobra.
            antigos = None
    novos = set() if antigos is None else {
        it.get("id") for ph in incoming.get("phases", []) or []
        if isinstance(ph, dict)
        for it in ph.get("items", []) or []
        if isinstance(it, dict) and it.get("id") not in antigos}
    # O bloco de requisitos que vai FICAR gravado é o do init quando ele traz um, e o
    # do arquivo quando não traz (o merge o preserva). Validar a citação contra outro
    # conjunto é validar contra o que não vai ficar — foi assim que o init que apagava
    # a fonte era o mesmo que deixava de conferir as citações.
    fonte = incoming if stored is None or _requisitos_do_plano(incoming) else stored
    validate(incoming, exigir=novos,
             reqs=_requisitos_do_projeto(directory, fonte))

    notes = []
    if stored is not None:
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
            # motivo que não apaga a prova. Vale pra FASE também — é nela que mora o
            # `detail`, o único lugar do 🔧 Como / 💡 Por quê / 📁 Toca em.
            for campo in ("requisito", "grupo", "pronto", "pendencia", "decidido", "detail"):
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
    # O topo do plano segue a MESMA regra dos nós: o que o init não trouxe vem do
    # arquivo. Uma lista fixa de chaves apagava tudo o que não estivesse nela — e o
    # que morava ali era o bloco `requisitos` (a fonte que as tarefas citam) e o
    # `closed_at`. Pra apagar de propósito, declare a chave vazia, como na `pendencia`.
    for key, valor in stored.items():
        if key not in incoming:
            incoming[key] = valor
    incoming.setdefault("created", time.strftime("%Y-%m-%d"))
    incoming.setdefault("status", "active")
    return incoming, notes


def _erro_e_do_no(msg, plan, node_id):
    """A mensagem cita a tarefa `node_id`?

    `erros_do_plano` prefixa com 'fase[i] passo[j]', que são POSIÇÕES e não ids.
    Traduz a posição do nó procurado e casa pelo prefixo.
    """
    for pi, ph in enumerate(plan.get("phases", [])):
        for ii, it in enumerate(ph.get("items", [])):
            if it.get("id") == node_id:
                return msg.startswith("fase[%d] passo[%d]" % (pi, ii))
    return False


def _requisitos_do_plano(plan):
    """Os requisitos declarados DENTRO do próprio arquivo do plano.

    O requisito é obrigatório; o LUGAR dele é opcional. Projeto com documento de
    requisitos aponta pra lá; projeto sem documento — o caso deste repositório, que
    não tem PRD — declara aqui. Sem esta porta, todo projeto sem PRD voltaria a ter
    tarefa que não rastreia pra nada, que é o defeito que o fio existe pra fechar.

    Formato, no topo do plano, ao lado de `phases`:
        "requisitos": [{"id": "S-1.1", "titulo": "...", "ca": "...",
                        "ancora": "Art. 6", "epico": "E1 — Base"}]
    """
    out = {}
    for r in plan.get("requisitos") or []:
        if isinstance(r, dict) and str(r.get("id", "")).strip():
            out[r["id"].strip()] = {"titulo": r.get("titulo", ""), "ca": r.get("ca"),
                                    "ancora": r.get("ancora"), "epico": r.get("epico")}
    return out


def _requisitos_do_projeto(directory, plan=None):
    """Acha os requisitos. {} se não houver — e isso não é erro.

    Cascata: bloco no próprio plano → $PLAN_REQS → <raiz>/docs/PRD.md →
    <raiz>/docs/REQUISITOS.md → {}. O bloco vem primeiro porque é o mais específico:
    quem o declarou no plano quis aquele conjunto, não o do projeto inteiro.
    """
    import cobertura
    if plan is not None:
        do_plano = _requisitos_do_plano(plan)
        if do_plano:
            return do_plano
    env = os.environ.get("PLAN_REQS")
    if env and os.path.exists(env):
        return cobertura.le_requisitos(env)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(directory)))
    for cand in ("docs/PRD.md", "docs/REQUISITOS.md"):
        p = os.path.join(raiz, cand)
        if os.path.exists(p):
            return cobertura.le_requisitos(p)
    return {}


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

    # O validador passa a morder aqui: até 2026-08-01 ele só rodava no init, e por isso
    # um desc de 356 chars sobreviveu num plano cujo teto é 140. Só BLOQUEIA por defeito
    # DA TAREFA TICADA — defeito alheio vira aviso, senão uma tarefa torta congelaria o
    # plano inteiro (fail-open: bloquear precisa de evidência sobre o alvo).
    erros = erros_do_plano(plan)
    do_alvo = [e for e in erros if _erro_e_do_no(e, plan, node_id)]
    if do_alvo:
        raise PlanError("⛔ tick recusado: %s está fora do schema.\n  - %s"
                        % (node_id, "\n  - ".join(do_alvo)))
    if erros:
        print("⚠️  %d defeito(s) em outras tarefas (não bloqueiam este tique):" % len(erros),
              file=sys.stderr)
        for e in erros[:3]:
            print("     %s" % e, file=sys.stderr)

    # Quem resolve a pendência é a DECISÃO registrada, não a ausência do campo: o init
    # que omite a `pendencia` não a apaga (o merge preserva o que o init não trouxe), e
    # o autor do plano não tem que saber que existe um merge pra conseguir destravar.
    # A pergunta continua no arquivo — é dela que o `reabrir` vive.
    dec = it.get("decidido")
    pend = "" if isinstance(dec, dict) and str(dec.get("escolha", "")).strip() \
        else str(it.get("pendencia", "")).strip()
    if pend:
        raise PlanError(
            "⛔ tick recusado: %s tem decisão em aberto.\n   %s\n\n"
            "   Feche a decisão antes de marcar feito. Quem destrava é o registro: o\n"
            "   motor de decisão escreve a escolha em `decidido` e o tique volta a\n"
            "   passar — ver plugins/visual/skills/visual/SKILL.md, 'Motor de decisão'."
            % (node_id, pend))

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

    # Relatório, não estado: o requisito NÃO ganha `status`. Estado duplicado é estado
    # que diverge — o mesmo motivo pelo qual a fase também não tem estado próprio.
    rid = str(it.get("requisito", "")).strip()
    if rid:
        reqs = _requisitos_do_projeto(directory, plan)
        irmas = [x for _, x in iter_items(plan) if x.get("requisito") == rid]
        faltam = [x["id"] for x in irmas if x.get("status") != "done"]
        if not faltam and rid in reqs and reqs[rid].get("ca"):
            print()
            print("🎯 %s fechou (%d/%d tarefas). O critério de aceite era:"
                  % (rid, len(irmas), len(irmas)))
            print("   %s" % reqs[rid]["ca"])
            print("   → confira antes de seguir. O motor não verifica critério de aceite;")
            print("     ele lembra, e quem confere é você.")
    return 0


def cmd_cobertura(args):
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    import cobertura
    reqs = (cobertura.le_requisitos(args.reqs) if args.reqs
            else _requisitos_do_projeto(directory, plan))
    m = cobertura.mapa(plan, reqs)
    if args.json:
        print(json.dumps(m, ensure_ascii=False))
        return 0
    print(cobertura.resumo(m))
    if not reqs:
        print("   (nenhum documento de requisitos encontrado — veja PLAN_REQS)")
    for chave, rotulo in (("sem_requisito", "⚠️ tarefas sem requisito"),
                          ("orfaos", "🔴 requisitos sem tarefa"),
                          ("inexistentes", "⛔ citando requisito inexistente")):
        if m[chave]:
            print()
            print("%s (%d):" % (rotulo, len(m[chave])))
            for x in m[chave]:
                print("   %s" % (x if isinstance(x, str) else "%s → %s" % x))
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


def cmd_reabrir(args):
    """Derruba uma decisão que o agente tomou no lugar do dono.

    A decisão volta a ser pergunta e a tarefa volta a `todo`. Sem isto, `decidido`
    seria fato consumado — e o combinado é que toda decisão tomada na ausência do
    dono seja reversível por construção.
    """
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    ph, it = find_item(plan, args.node)
    if it is None:
        raise PlanError("tarefa '%s' não existe no plano '%s'" % (args.node, plan["id"]))
    dec = it.get("decidido")
    if not isinstance(dec, dict) or not dec.get("escolha"):
        raise PlanError("⛔ %s não tem decisão registrada pra reabrir." % args.node)
    it["pendencia"] = dec.get("pergunta") or dec.get("porque") or "decisão reaberta pelo dono"
    it.pop("decidido", None)
    it["status"] = "todo"
    it["evidence"] = None
    it["done_at"] = None
    save(directory, plan)
    print("↩️  %s reaberto  ·  a escolha era: %s" % (args.node, dec.get("escolha")))
    print("   falta decidir de novo: %s" % it["pendencia"])
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


def _com_prova(plan):
    """Todo passo marcado tem prova anexada?

    O brief é o texto que o hook de fim de turno mostra ao usuário; afirmar prova
    sem olhar a `evidence` é a mesma mentira que o módulo existe pra impedir.
    """
    return all(str(it.get("evidence") or "").strip()
               for _, it in iter_items(plan) if it.get("status") == "done")


def brief_lines(plan, nudge=None, reqs=None):
    """As linhas de um plano. Lista vazia = não há o que dizer.

    TETO DE 3 BULLETS, e ele é do pedido: "3 bullets curtos" e "dentro dos
    mesmos 1 a 3 bullets". Quando a cobrança do tique entra, ela NÃO vira um
    4º — ela toma o lugar do "Falta", que é o mais dedutível dos três (falta =
    total − feito) e o menos urgente naquele momento. A conta vive aqui, num
    lugar testável, e não montada em pedaços pelo shell.

    `reqs` faz a cobertura aparecer SEM ser pedida: transparente é o número
    estar onde o plano já está, não num comando que alguém precisa lembrar de
    rodar. Disputa o mesmo slot do "Falta"; com cobrança, a cobrança ganha,
    porque ela fala do que acabou de acontecer nesta sessão.
    """
    s = summary(plan)
    done, total = s["done"], s["total"]
    pd, pt = len(s["phases_done"]), s["phases_total"]
    provado = _com_prova(plan)
    prova = ", cada um com prova anexada" if provado else ""

    if s["status"] != "active":
        if done == total and total:
            return ["🏁 **PLANO ENCERRADO — %s**" % s["title"],
                    "• Os %s das %s foram concluídos%s."
                    % (_plural(total, "passo"), _plural(pt, "fase"), prova),
                    "• O arquivo fica em `.claude/plans/%s` como registro do que foi feito." % s["path"]]
        return ["🏁 **PLANO ENCERRADO (incompleto) — %s**" % s["title"],
                "• %d de %d passos marcados; %s ficaram sem marcar."
                % (done, total, _plural(total - done, "passo")),
                "• O que ficou aberto continua registrado em `.claude/plans/%s`." % s["path"]]

    if total and done == total:
        return ["✅ **CONCLUÍDO — %s**" % s["title"],
                "• Os %s das %s estão marcados%s."
                % (_plural(total, "passo"), _plural(pt, "fase"), prova),
                "• Nada ficou em aberto neste plano. Encerre com `plan_state.py close` "
                "pra ele parar de aparecer aqui."]

    lines = ["📍 **Onde estamos — %s**" % s["title"]]
    if pd:
        lines.append("• **Feito:** %d de %d passos · %s %s fechada%s%s."
                     % (done, total, _plural(pd, "fase"),
                        "(%s)" % ", ".join(s["phases_done"]), "" if pd == 1 else "s",
                        ", com prova em cada passo" if provado else ""))
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
    if reqs:
        import cobertura
        m = cobertura.mapa(plan, reqs)
        if m["sem_requisito"] or m["inexistentes"]:
            lines[-1] = ("• **Cobertura:** %s. Quem está sem requisito e qual requisito "
                         "ficou sem tarefa: `plan_state.py cobertura`." % cobertura.resumo(m))
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
            # por plano, não uma vez só: cada um pode declarar os próprios requisitos
            blocks.append(brief_lines(plan, getattr(args, "nudge", None),
                                      _requisitos_do_projeto(directory, plan)))
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


def _detalhe(it):
    """A linha de baixo do item, e a classe com que ela vai pro HTML.

    Uma regra só, lida pelas duas vistas: a PROVA quando o passo está feito, a decisão
    em aberto quando ela trava o tique, a linha didática no resto. Enquanto eram duas
    cópias, a `pendencia` era invisível justo na vista em que o dono aprova o plano —
    o motor recusava o tique por um bloqueio que a página nunca tinha mostrado.
    """
    st = it.get("status", "todo")
    ev = str(it.get("evidence") or "").strip()
    if st == "done" and ev:
        return "prova: " + ev, "pt-evidence"
    pend = str(it.get("pendencia", "")).strip()
    if pend:
        return "⛔ falta decidir: " + pend, "pt-desc"
    return it.get("desc", "") or "", "pt-desc"


def render_text(plan, reqs=None, vista="execucao"):
    if vista == "valor":
        return _render_valor(plan, reqs or {})
    done, total = plan_progress(plan)
    out = ["📋 %s — %d/%d passos" % (plan.get("title", plan["id"]), done, total), ""]
    for ph in plan["phases"]:
        pd, pt = phase_progress(ph)
        out.append("%s %s · %s   (%d/%d)" % (MARK[phase_status(ph)], ph["id"], ph["title"], pd, pt))
        for it in ph["items"]:
            st = it.get("status", "todo")
            out.append("     %s %s  %s" % (DOT[st], it["id"], it["title"]))
            out.append("            %s" % _detalhe(it)[0])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _render_valor(plan, reqs):
    """Épico › requisito › grupo › tarefa — DERIVADO, não armazenado.

    O arquivo guarda fase→tarefa; esta vista junta com o documento de requisitos.
    Duas árvores sobre os mesmos itens é o que WBS manda: a decomposição do trabalho
    não é a estrutura dos requisitos.
    """
    import cobertura
    m = cobertura.mapa(plan, reqs)
    idx = {it["id"]: it for _, it in iter_items(plan)}
    done, total = plan_progress(plan)
    out = ["📋 %s — %d/%d tarefas" % (plan.get("title", plan["id"]), done, total),
           "   %s" % cobertura.resumo(m), ""]

    sem_eixo = _sem_eixo(m, idx)
    if sem_eixo:
        todas = [it for _, it in iter_items(plan)]
        out.append("⚠️ %s" % SEM_REQ_AVISO)
        out.append("")
        out.append("▸ sem requisito   %s  %d/%d%s"
                   % (_plural(len(todas), "tarefa"),
                      sum(1 for t in todas if t.get("status") == "done"),
                      len(todas), _marcas(todas)))
        for g, gt in sorted(_por_grupo(todas).items()):
            out.append("    ▸ %s   %s  %d/%d%s"
                       % (g, _plural(len(gt), "tarefa"),
                          sum(1 for t in gt if t.get("status") == "done"),
                          len(gt), _marcas(gt)))
            for t in gt:
                out.extend(_tarefa_txt(t, "        "))
        out.append("")

    por_epico = {}
    for rid in sorted(m["por_req"]):
        por_epico.setdefault(reqs.get(rid, {}).get("epico") or "(sem épico)", []).append(rid)

    for ep in sorted(por_epico):
        rids = por_epico[ep]
        tarefas = [t for rid in rids for t in m["por_req"][rid]]
        feitas = sum(1 for t in tarefas if idx[t].get("status") == "done")
        marcas = _marcas([idx[t] for t in tarefas])
        out.append("▸ %s   %d req · %d tarefas  %d/%d%s"
                   % (ep, len(rids), len(tarefas), feitas, len(tarefas), marcas))
        for rid in rids:
            ts = [idx[t] for t in m["por_req"][rid]]
            r = reqs.get(rid, {})
            cab = "%s  %s" % (rid, r.get("titulo", "?"))
            if r.get("ancora"):
                cab += " · %s" % r["ancora"]
            out.append("    ▸ %s   %d tarefas  %d/%d%s"
                       % (cab, len(ts), sum(1 for t in ts if t.get("status") == "done"),
                          len(ts), _marcas(ts)))
            grupos = {}
            for t in ts:
                grupos.setdefault(t.get("grupo") or "(sem grupo)", []).append(t)
            for g in sorted(grupos):
                gt = grupos[g]
                out.append("        ▸ %s   %d tarefas  %d/%d%s"
                           % (g, len(gt), sum(1 for t in gt if t.get("status") == "done"),
                              len(gt), _marcas(gt)))
                for t in gt:
                    out.extend(_tarefa_txt(t, "            "))
        out.append("")

    # a lista de ids não se repete: sem eixo, a árvore acima JÁ é ela inteira
    if m["sem_requisito"] and not sem_eixo:
        out.append("⚠️ %s sem requisito — trabalho que ninguém pediu:"
                   % _plural(len(m["sem_requisito"]), "tarefa"))
        out.append("   %s" % ", ".join(m["sem_requisito"]))
        out.append("")
    if m["orfaos"]:
        out.append("🔴 %s sem nenhuma tarefa — pedido que ninguém planejou:"
                   % _plural(len(m["orfaos"]), "requisito"))
        for rid in m["orfaos"]:
            out.append("   %s  %s" % (rid, reqs.get(rid, {}).get("titulo", "")))
        out.append("")
    if m["inexistentes"]:
        out.append("⛔ %s citando requisito que não existe:"
                   % _plural(len(m["inexistentes"]), "tarefa"))
        for tid, rid in m["inexistentes"]:
            out.append("   %s → %s" % (tid, rid))
    return "\n".join(out).rstrip() + "\n"


SEM_REQ_AVISO = (
    "Nenhuma tarefa declara requisito ainda — sem esse fio não há eixo de valor pra "
    "desenhar. Abaixo estão as tarefas do plano, agrupadas em «sem requisito»; declare "
    "`requisito` nelas pra esta vista virar o que promete.")


def _sem_eixo(m, idx):
    """A vista de valor tem plano pra mostrar, mas não tem requisito nenhum?

    Medido em 14 planos reais: 0 tarefas com `requisito` em 14 deles. Sair em branco
    num plano de 157 tarefas afirma, por omissão, que não há trabalho — o oposto do
    arquivo. Então quando o eixo não existe, a vista diz isso e desenha o que existe.
    """
    return bool(idx) and not m["por_req"]


def _por_grupo(itens):
    grupos = {}
    for t in itens:
        grupos.setdefault(t.get("grupo") or "(sem grupo)", []).append(t)
    return grupos


def _tarefa_txt(t, ind):
    """A tarefa no texto da vista de valor. A prova entra porque 'feito' sem prova
    anexada é exatamente o que este módulo existe pra impedir — e era no eixo de
    valor, onde se decide se um requisito fechou, que ela não aparecia."""
    linhas = ["%s%s %s  %s%s" % (ind, DOT[t.get("status", "todo")], t["id"],
                                 t["title"], _marcas([t]))]
    ev = str(t.get("evidence") or "").strip()
    if t.get("status") == "done" and ev:
        linhas.append("%s    prova: %s" % (ind, ev))
    return linhas


def _marcas(itens):
    """As marcas de atenção somam pra cima. Sem isto a dobra esconde o problema
    junto com o resto — a mesma armadilha que a spec §2 documenta."""
    pend = sum(1 for t in itens if str(t.get("pendencia", "")).strip())
    blq = sum(1 for t in itens if t.get("status") == "blocked")
    partes = []
    if pend:
        partes.append("⛔%d" % pend)
    if blq:
        partes.append("⚠️%d" % blq)
    return ("  " + " ".join(partes)) if partes else ""


def _e(s):
    return html.escape(str(s or ""), quote=True)


def render_html(plan, mode="track", reqs=None, vista="execucao"):
    """Emite o HTML do componente .plan-tree do template.html.

    É ESTE programa que escreve a árvore, nunca o modelo — por isso os títulos
    não derivam entre um render e o seguinte.
    """
    if vista == "valor":
        return _html_valor(plan, reqs or {})
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
            texto, classe = _detalhe(it)
            parts.append('        <span class="%s">%s</span>' % (classe, _e(texto)))
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


def _html_valor(plan, reqs):
    """Árvore dobrável. TUDO nasce fechado: o usuário abre um ramo por vez.

    Reverte, SÓ nesta vista, a escolha declarada em PAGE_COPY ('a árvore É a lista').
    Motivo, do dono: 'idealmente é esse negócio no visual poder ser colapsável, para eu
    poder esconder o que não me interessa olhar, durante a análise do doc'.
    """
    import cobertura
    m = cobertura.mapa(plan, reqs)
    idx = {it["id"]: it for _, it in iter_items(plan)}
    p = ['<div class="plan-tree pt-valor">',
         '  <div class="pt-cobertura">%s</div>' % _e(cobertura.resumo(m))]

    def nivel(classe, rotulo, itens, corpo):
        feitas = sum(1 for t in itens if t.get("status") == "done")
        p.append('  <details class="pt-n %s">' % classe)
        p.append('    <summary><span class="pt-chev">▸</span>'
                 '<span class="pt-rot">%s</span>'
                 '<span class="pt-cnt">%d/%d</span>'
                 '<span class="pt-marcas">%s</span></summary>'
                 % (_e(rotulo), feitas, len(itens), _e(_marcas(itens).strip())))
        corpo()
        p.append('  </details>')

    def itens(gt):
        p.append('      <ul class="pt-items">')
        for t in gt:
            st = t.get("status", "todo")
            texto, classe = _detalhe(t)
            p.append('        <li class="pt-item pt-%s">'
                     '<span class="pt-dot">%s</span>'
                     '<span class="pt-item-title">'
                     '<span class="pt-id">%s</span>%s</span>'
                     '<span class="%s">%s</span></li>'
                     % (st, DOT[st], _e(t["id"]), _e(t["title"]), classe, _e(texto)))
        p.append('      </ul>')

    sem_eixo = _sem_eixo(m, idx)
    if sem_eixo:
        todas = [it for _, it in iter_items(plan)]
        p.append('  <div class="pt-ausencias pt-aviso">%s</div>' % _e(SEM_REQ_AVISO))

        def corpo_sem(todas=todas):
            for g, gt in sorted(_por_grupo(todas).items()):
                nivel("pt-grupo", g, gt, lambda gt=gt: itens(gt))
        nivel("pt-epico", "sem requisito", todas, corpo_sem)

    por_epico = {}
    for rid in sorted(m["por_req"]):
        por_epico.setdefault(reqs.get(rid, {}).get("epico") or "(sem épico)", []).append(rid)

    for ep in sorted(por_epico):
        rids = por_epico[ep]
        t_ep = [idx[t] for rid in rids for t in m["por_req"][rid]]
        def corpo_ep(rids=rids):
            for rid in rids:
                ts = [idx[t] for t in m["por_req"][rid]]
                r = reqs.get(rid, {})
                rot = "%s  %s%s" % (rid, r.get("titulo", "?"),
                                    (" · " + r["ancora"]) if r.get("ancora") else "")
                def corpo_req(ts=ts):
                    if r.get("ca"):
                        p.append('    <div class="pt-ca">critério de aceite: %s</div>' % _e(r["ca"]))
                    grupos = _por_grupo(ts)
                    for g in sorted(grupos):
                        nivel("pt-grupo", g, grupos[g], lambda gt=grupos[g]: itens(gt))
                nivel("pt-req", rot, ts, corpo_req)
        nivel("pt-epico", ep, t_ep, corpo_ep)

    for chave, titulo, classe in (("sem_requisito", "tarefas sem requisito", "pt-aviso"),
                                  ("orfaos", "requisitos sem nenhuma tarefa", "pt-alerta"),
                                  ("inexistentes", "tarefas citando requisito inexistente", "pt-erro")):
        # a lista de ids não se repete: sem eixo, a árvore acima JÁ é ela inteira
        if m[chave] and not (sem_eixo and chave == "sem_requisito"):
            p.append('  <div class="pt-ausencias %s">' % classe)
            p.append('    <b>%d %s</b>' % (len(m[chave]), _e(titulo)))
            p.append('    <p>%s</p>' % _e(", ".join(
                x if isinstance(x, str) else "%s → %s" % x for x in m[chave])))
            p.append('  </div>')
    p.append('</div>')
    return "\n".join(p) + "\n"


def cmd_render(args):
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    if args.format == "text":
        sys.stdout.write(render_text(plan, reqs=_requisitos_do_projeto(directory, plan),
                                     vista=getattr(args, "vista", "execucao")))
    else:
        sys.stdout.write(render_html(plan, args.mode,
                                     reqs=_requisitos_do_projeto(directory, plan),
                                     vista=getattr(args, "vista", "execucao")))
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

    vista = getattr(args, "vista", "execucao")
    # O veredito (Manter/Mudar/Remover) mora na FASE, e a vista de valor não desenha
    # fase nenhuma — a página saía com a caixa de fechamento, os dois botões e ZERO
    # item revisável, e o "Aprovar tudo" devolvia uma aprovação que ninguém deu.
    if args.mode == "approve" and vista != "execucao":
        raise PlanError(
            "⛔ aprovação não existe na vista '%s'.\n"
            "   O veredito mora na FASE, e essa vista desenha épico › requisito › grupo:\n"
            "   a página sairia com os botões e nenhum item pra você marcar, e o botão\n"
            "   devolveria uma aprovação que você não deu.\n"
            "   Aprove com `--vista execucao`; pra ler o eixo de valor, `--mode track`."
            % vista)

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
        render_html(plan, args.mode, reqs=_requisitos_do_projeto(directory, plan),
                    vista=vista),
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
        # a vista entra no nome: sem ela, as duas árvores do mesmo plano gravam no
        # mesmo arquivo e a última apaga a outra em silêncio
        sufixo = args.mode if vista == "execucao" else "%s-%s" % (args.mode, vista)
        out = os.path.join(vdir, "plano-%s-%s.html" % (plan["id"], sufixo))
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
    q.add_argument("--vista", choices=("execucao", "valor"), default="execucao")
    q.set_defaults(func=cmd_render)

    q = sub.add_parser("page", help="monta a PÁGINA inteira (template + árvore) e imprime o caminho")
    q.add_argument("plan", nargs="?")
    q.add_argument("--mode", choices=("track", "approve"), default="track")
    q.add_argument("--out", help="caminho do HTML (default: <dir do /visual>/plano-<id>-<modo>.html)")
    q.add_argument("--vista", choices=("execucao", "valor"), default="execucao")
    q.set_defaults(func=cmd_page)

    q = sub.add_parser("brief", help="1-3 bullets de 'onde nós estamos' (usado pelo hook de fim de turno)")
    q.add_argument("--closed-since", dest="closed_since",
                   help="epoch: também confirma plano encerrado depois desse instante")
    q.add_argument("--mark-seen", dest="mark_seen",
                   help="arquivo onde anotar os encerramentos já confirmados (não repete)")
    q.add_argument("--nudge", help="cobrança a incluir: ENTRA NO LUGAR do bullet 'Falta', "
                                   "nunca como 4º (o teto de 3 é do pedido)")
    q.set_defaults(func=cmd_brief)

    q = sub.add_parser("cobertura", help="o mapa entre requisito e tarefa, os dois lados")
    q.add_argument("plan", nargs="?")
    q.add_argument("--reqs", help="caminho do documento de requisitos (default: cascata)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_cobertura)

    q = sub.add_parser("reabrir", help="derruba uma decisão tomada no seu lugar")
    q.add_argument("plan", nargs="?")
    q.add_argument("node")
    q.set_defaults(func=cmd_reabrir)

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
