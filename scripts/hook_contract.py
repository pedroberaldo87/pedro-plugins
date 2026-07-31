#!/usr/bin/env python3
"""hook_contract.py — mede o CONTRATO DE CONVIVÊNCIA dos hooks deste marketplace.

Por que existe
--------------
Três gates disputam o `ExitPlanMode` e cada um resolveu por conta própria como
não travar o usuário, como ser desligado e como falar. A divergência não foi
descuido de um autor: **não havia onde estivesse escrito o contrato**, então
cada hook nasceu com o seu. Este script transforma o contrato em medida.

Ele mede as 5 propriedades que separam um gate saudável de um gate que trava
ou que se desliga sozinho:

  1. canal de saída  — como o hook fala (bloqueia? informa? só loga?)
  2. cap anti-loop   — quem bloqueia tem teto de devoluções, escopado por sessão?
  3. kill-switch     — dá pra desligar sem editar o arquivo?
  4. binário fixo    — usa caminho absoluto de ferramenta (some fora do Homebrew)?
  5. fail-open       — guarda a ausência das ferramentas que usa?

⚠️ **Isto é grep sofisticado, não verdade.** O script diz ONDE OLHAR. Um achado
só vira defeito depois de conferido no arquivo real — é a mesma disciplina do
knowledge graph ("mapa, não verdade"). Por isso a saída traz sempre a linha e o
trecho que dispararam o achado: pra conferir custar segundos, não minutos.

Uso
---
  python3 scripts/hook_contract.py                 # relatório humano
  python3 scripts/hook_contract.py --json          # a medida crua
  python3 scripts/hook_contract.py --fail-on high  # exit 1 se houver HIGH (gate)
  python3 scripts/hook_contract.py --baseline f.json   # só o que PIOROU vs o retrato

Só stdlib.
"""

import argparse
import json
import os
import re
import sys

# ── o que conta como cada coisa (padrões vistos no código real deste repo) ────

# Canais que BLOQUEIAM o agente. Os três coexistem hoje: exit 2 (intent-guard,
# visual), permissionDecision:deny (project-doc, guardrails) e decision:block
# (handoff). Não normalizo: só meço.
BLOCK_PATTERNS = [
    ("exit2", re.compile(r"^\s*exit\s+2\b", re.M)),
    ("permissionDecision", re.compile(r'permissionDecision"?\s*:\s*"?deny')),
    ("decisionBlock", re.compile(r'"decision"\s*:\s*"block"')),
]
# Canais que só INFORMAM — não travam nada, logo não precisam de cap.
INFORM_PATTERNS = [
    ("additionalContext", re.compile(r"additionalContext")),
    ("systemMessage", re.compile(r"systemMessage")),
]

# Cap = um teto de repetições. Duas formas legítimas, ambas vistas no repo:
#   contador  -> [ "$COUNT" -ge 2 ] ... exit 0        (intent-guard, literal)
#               [ "$COUNT" -ge "$MAX_NUDGES" ] && exit 0  (project-doc, variável)
#   sentinela -> [ -f "$SENTINEL" ] && exit 0         (stop-doc-touch, stop-plan-nudge)
#
# DIREÇÃO DO ERRO IMPORTA. Detectar um cap que não existe é o erro CARO: o
# script deixaria de acusar um gate que trava de verdade. Detectar de menos só
# gera um falso alarme que a conferência derruba. Por isso as duas regras exigem
# o `exit 0` por perto — um `-ge` solto (comparação numérica qualquer) não conta.
CAP_COUNTER = re.compile(r"-ge\s+\"?\$?\{?[\w]+\}?\"?\s*\]", re.I)
# A sentinela aparece de duas formas no repo, e a regra tem que pegar as duas
# SEM pegar um `[ -f "$1" ]` qualquer dentro de função auxiliar (foi o que
# aconteceu quando afrouxei: o ship ganhou um "cap" que não existe — o erro CARO).
#   nomeada  -> [ -f "$SENTINEL" ] / "$DENYF" / "$COUNT_FILE"
#   inline   -> [ -f "$STATE_DIR/${ID}.denied" ]   (organism-gate: dir + arquivo)
CAP_SENTINEL = re.compile(
    r"\[\s*-f\s+\"?\$\{?\w*(SENTINEL|FLAG|OKFLAG|DENYF|COUNT|MARK)\w*\}?\"?\s*\]"
    r"|\[\s*-f\s+\"?\$\{?\w+\}?/", re.I)
CAP_ESCAPE_WINDOW = 8  # linhas depois do teste em que o `exit 0` ainda conta
                       # (8 e não 3: o circuit breaker do scope-cop loga e grava
                       #  rastro antes de liberar — o exit 0 dele cai 7 linhas abaixo)
# O cap tem que ser POR SESSÃO — regra dura do repo (estado global vazou entre
# sessões e causou falso-positivo em massa no context-guard).
SESSION_SCOPED = re.compile(r"(SESSION|session_id|SID)\w*\}?[-_\"]", re.I)

# Kill-switch: env var com default, arquivo de modo, ou marcador de desligado.
KILL_PATTERNS = [
    re.compile(r'\$\{(\w+):-1\}"?\s*=\s*"?0'),          # [ "${PLAN_NUDGE:-1}" = "0" ]
    re.compile(r'\$\{(\w+):-\w+\}"?\s*=\s*"?(off|0)'),   # ${X:-on} = off
    re.compile(r"MODE_FILE|_MODE\b"),
    re.compile(r'\[\s*-f\s+"\$\w+/off"'),
]

# Caminho absoluto de ferramenta: o defeito que DESLIGA o hook em silêncio fora
# da máquina onde foi escrito. Ignora shebang e caminhos de sistema estáveis.
HARDCODED_TOOL = re.compile(r"(?<!#!)(/opt/homebrew/bin/|/usr/local/bin/|/opt/local/bin/)(\w[\w.-]*)")

# Ferramentas externas que, faltando, mudam o comportamento do hook.
EXTERNAL_TOOLS = ("jq", "python3", "node", "graphify")
FAILOPEN_GUARD = re.compile(
    r"command\s+-v\s+(\w+)[^\n]*(\|\|\s*exit\s+0|>\s*/dev/null[^\n]*\|\|\s*exit\s+0)")
FAILOPEN_VAR = re.compile(r'(\w+)\s*=\s*"?\$\(\s*command\s+-v\s+(\w+)')
# `graphify` aparecia como "usado sem guarda" em hook que só o cita em
# comentário e dentro de string de contexto. Ferramenta só conta quando está em
# POSIÇÃO DE COMANDO: início de linha, depois de pipe, `$(`, `;`, `&&`, `||`.
CMD_POS = r"(?:^|[|;&]|\$\(|\btype\s+|\bcommand\s+-v\s+)\s*\"?"
# `graphify` nunca é invocado no graphify-guard: o que existe lá é
# `graphify-detect.sh` (script bash) e o nome dentro de comentário/string.
# Nome de ferramenta seguido de -, / ou . é OUTRO programa.
NOT_SUFFIXED = r"(?![\w./-])"
COMMENT = re.compile(r"(?<!\\)#.*$")

SEV_ORDER = {"high": 3, "med": 2, "low": 1}


# ── coleta ───────────────────────────────────────────────────────────────────

def discover(root):
    """Todo hook registrado, com o caminho real do script resolvido."""
    out = []
    plugdir = os.path.join(root, "plugins")
    for plug in sorted(os.listdir(plugdir)) if os.path.isdir(plugdir) else []:
        hj = os.path.join(plugdir, plug, "hooks", "hooks.json")
        if not os.path.exists(hj):
            continue
        try:
            with open(hj, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, ValueError) as exc:
            out.append({"plugin": plug, "event": "?", "matcher": "?", "script": None,
                        "error": "hooks.json ilegível: %s" % exc})
            continue
        for event, groups in (cfg.get("hooks") or {}).items():
            for grp in groups:
                for h in grp.get("hooks") or []:
                    cmd = h.get("command", "")
                    entry = {
                        "plugin": plug, "event": event,
                        "matcher": grp.get("matcher", "*"),
                        "type": h.get("type", "command"),
                        "timeout": h.get("timeout"),
                        "command": cmd,
                        "script": resolve_script(root, plug, cmd),
                    }
                    out.append(entry)
    return out


def resolve_script(root, plug, cmd):
    """`${CLAUDE_PLUGIN_ROOT}/hooks/x.sh` → `<root>/plugins/<plug>/hooks/x.sh`."""
    if not cmd:
        return None
    m = re.search(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/(.+)$", cmd.strip())
    if not m:
        return None
    return os.path.join(root, "plugins", plug, m.group(1).strip().strip('"'))


def measure(path):
    """As 5 propriedades de um script, com a linha que sustenta cada uma."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    lines = src.splitlines()

    def hits(rx):
        return [(i + 1, ln.strip()[:110]) for i, ln in enumerate(lines) if rx.search(ln)]

    blocks = {name: hits(rx) for name, rx in BLOCK_PATTERNS if rx.search(src)}
    informs = {name: hits(rx) for name, rx in INFORM_PATTERNS if rx.search(src)}

    def cap_hits(rx):
        """Só conta como cap se houver `exit 0` na mesma linha ou logo abaixo —
        senão qualquer comparação numérica viraria 'tem teto'."""
        out = []
        for i, ln in enumerate(lines):
            if not rx.search(ln):
                continue
            window = "\n".join(lines[i:i + 1 + CAP_ESCAPE_WINDOW])
            # `continue` conta: no organism-gate a sentinela vive dentro do laço
            # de costuras e o escape é pular AQUELA costura, não sair do script.
            if re.search(r"^\s*exit\s+0|&&\s*exit\s+0|\breturn\s+0\b"
                         r"|\bcontinue\b|&&\s*\{[^}]*continue", window, re.M):
                out.append((i + 1, ln.strip()[:110]))
        return out

    cap_counter, cap_sentinel = cap_hits(CAP_COUNTER), cap_hits(CAP_SENTINEL)
    # Cap fatorado em função — `capped() { [ "$N" -ge "$MAX" ]; }` chamado depois
    # como `capped && exit 0`. O teste e o escape ficam longe um do outro, então
    # a janela de linhas não alcança. Casa os dois pelo NOME da função.
    for fn, body in re.findall(r"^\s*(\w+)\s*\(\)\s*\{([^}]*)\}", src, re.M):
        if not re.search(r"-ge|-gt|-f\s", body):
            continue
        if re.search(r"^\s*%s\s*&&\s*(exit|return)\s+0" % re.escape(fn), src, re.M):
            ln = next((i + 1 for i, l in enumerate(lines) if re.match(r"\s*%s\s*\(\)" % re.escape(fn), l)), 0)
            cap_counter.append((ln, ("%s() — cap em função, escape em `%s && exit 0`" % (fn, fn))[:110]))
    cap_lines = cap_counter + cap_sentinel
    # o cap só vale se a chave dele for por sessão — estado global vaza entre
    # sessões concorrentes (bug real do context-guard, v1.2.0)
    cap_session = bool(cap_lines) and bool(SESSION_SCOPED.search(src))

    kill = []
    for rx in KILL_PATTERNS:
        kill += hits(rx)

    hard = []
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("#!"):
            continue
        for m in HARDCODED_TOOL.finditer(ln):
            hard.append((i + 1, m.group(0), ln.strip()[:110]))

    guarded = set(FAILOPEN_GUARD.findall(src))
    guarded = {g[0] if isinstance(g, tuple) else g for g in guarded}
    # Teto assumido: um `command -v X` em qualquer lugar conta como guarda, mesmo
    # sem `|| exit 0` — o autor checou, e as formas de usar o resultado são muitas
    # (if/then, variável, &&). Cobrar a forma exata gerava alarme falso, e alarme
    # falso em auditoria treina a ignorar a saída inteira.
    guarded |= set(re.findall(r"command\s+-v\s+(\w+)", src))
    for var, tool in FAILOPEN_VAR.findall(src):
        # Duas formas reais no repo:
        #   PY3=$(command -v python3);  [ -z "$PY3" ] && exit 0
        #   PY="$(command -v python3)"; { [ -z "$PY" ] || [ -z "$JQ" ]; } && exit 0
        if re.search(r'\[\s*-z\s+"\$\{?%s\}?"\s*\]' % re.escape(var), src):
            guarded.add(tool)

    # código sem comentário — `graphify` citado em comentário não é uso
    code = "\n".join(COMMENT.sub("", ln) for ln in lines)
    used = set()
    for t in EXTERNAL_TOOLS:
        for m in re.finditer(CMD_POS + re.escape(t) + NOT_SUFFIXED, code, re.M):
            line = code[code.rfind("\n", 0, m.start()) + 1:]
            line = line[:line.find("\n") if "\n" in line else len(line)]
            col = m.start() - (code.rfind("\n", 0, m.start()) + 1)
            # dentro de string (nº ímpar de aspas antes) não é invocação
            if line[:col].count('"') % 2 or line[:col].count("'") % 2:
                continue
            used.add(t)
            break
        # invocação via variável resolvida por command -v conta como uso guardado
        if t in guarded:
            used.add(t)

    return {
        "lines": len(lines),
        "blocking": blocks,
        "informing": informs,
        "cap": {"counter": cap_counter, "sentinel": cap_sentinel, "session_scoped": cap_session},
        "killswitch": kill,
        "hardcoded_tools": hard,
        "tools_used": sorted(used),
        "tools_guarded": sorted(guarded),
        "tools_unguarded": sorted(used - guarded),
    }


# ── as regras ────────────────────────────────────────────────────────────────

def judge(entry, m):
    """Achados. Cada um carrega a linha que o disparou — pra conferir rápido."""
    f = []
    who = "%s/%s" % (entry["plugin"], os.path.basename(entry["script"]))
    blocks = m["blocking"]

    if blocks:
        chans = ", ".join(sorted(blocks))
        # Hook de Stop tem cap NATIVO do harness (CLAUDE_CODE_STOP_HOOK_BLOCK_CAP):
        # ele não pode prender pra sempre mesmo sem cap próprio. Cobrar cap dele
        # seria alarme falso — e alarme falso treina a ignorar o relatório.
        native_cap = entry["event"] == "Stop"
        if native_cap:
            pass
        elif not (m["cap"]["counter"] or m["cap"]["sentinel"]):
            ln = sorted(v[0] for vs in blocks.values() for v in vs)[0]
            f.append(dict(rule="R1-cap-ausente", sev="high", who=who, line=ln,
                          msg="bloqueia (%s) e não tem teto de devoluções" % chans,
                          quote=sorted(blocks.values())[0][0][1]))
        elif not m["cap"]["session_scoped"]:
            ln = (m["cap"]["counter"] or m["cap"]["sentinel"])[0][0]
            f.append(dict(rule="R2-cap-global", sev="high", who=who, line=ln,
                          msg="tem cap, mas a chave dele não parece escopada por sessão",
                          quote=(m["cap"]["counter"] or m["cap"]["sentinel"])[0][1]))
        if not m["killswitch"]:
            ln = sorted(v[0] for vs in blocks.values() for v in vs)[0]
            f.append(dict(rule="R3-sem-killswitch", sev="med", who=who, line=ln,
                          msg="bloqueia (%s) e não tem como ser desligado sem editar o arquivo" % chans,
                          quote=sorted(blocks.values())[0][0][1]))

    for ln, tool, quote in m["hardcoded_tools"]:
        f.append(dict(rule="R4-binario-fixo", sev="high", who=who, line=ln,
                      msg="caminho absoluto de ferramenta (%s) — some fora dessa máquina "
                          "e o hook cai no fail-open sem avisar" % tool,
                      quote=quote))

    for tool in m["tools_unguarded"]:
        f.append(dict(rule="R5-sem-failopen", sev="med", who=who, line=0,
                      msg="usa %s sem guarda de ausência (command -v … || exit 0)" % tool,
                      quote=""))
    return f


def run(root):
    entries = discover(root)
    findings, measured = [], []
    for e in entries:
        if e.get("error"):
            findings.append(dict(rule="R0-config", sev="high", who=e["plugin"],
                                 line=0, msg=e["error"], quote=""))
            continue
        if e["type"] != "command":
            measured.append(dict(e, measure=None, note="hook do tipo '%s' — sem script pra medir" % e["type"]))
            continue
        if not e["script"] or not os.path.exists(e["script"]):
            findings.append(dict(rule="R0-script-ausente", sev="high",
                                 who="%s/%s" % (e["plugin"], os.path.basename(e["command"] or "?")),
                                 line=0, msg="hooks.json aponta pra script que não existe: %s" % e["command"],
                                 quote=""))
            continue
        m = measure(e["script"])
        measured.append(dict(e, measure=m))
        findings.extend(judge(e, m))

    # dedup: o mesmo script pode estar registrado em mais de um evento
    seen, uniq = set(), []
    for f in sorted(findings, key=lambda x: (-SEV_ORDER[x["sev"]], x["who"], x["rule"])):
        k = (f["who"], f["rule"], f["msg"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    return {"root": root, "entries": len(entries), "scripts": len(
        {e["script"] for e in measured if e.get("script")}), "findings": uniq,
        "measured": measured}


# ── saída ────────────────────────────────────────────────────────────────────

BADGE = {"high": "🔴 ALTA", "med": "🟡 MÉDIA", "low": "⚪ BAIXA"}


def report(res):
    out = ["Contrato dos hooks — %d registros, %d scripts distintos" % (res["entries"], res["scripts"]), ""]
    if not res["findings"]:
        out.append("Nenhum achado. Todos os hooks batem com o contrato.")
        return "\n".join(out) + "\n"
    by = {}
    for f in res["findings"]:
        by.setdefault(f["who"], []).append(f)
    for who in sorted(by, key=lambda w: -max(SEV_ORDER[x["sev"]] for x in by[w])):
        out.append(who)
        for f in by[who]:
            loc = ":%d" % f["line"] if f["line"] else ""
            out.append("  %s  %-18s %s%s" % (BADGE[f["sev"]], f["rule"], f["msg"], loc))
            if f["quote"]:
                out.append("        │ %s" % f["quote"])
        out.append("")
    n = {s: sum(1 for f in res["findings"] if f["sev"] == s) for s in ("high", "med", "low")}
    out.append("Total: %d achado(s) — %d alta · %d média · %d baixa"
               % (len(res["findings"]), n["high"], n["med"], n["low"]))
    out.append("Cada achado é ONDE OLHAR, não veredito. Confira no arquivo antes de consertar.")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hook_contract.py", description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("high", "med", "low"), help="exit 1 se houver achado nesse nível ou pior")
    ap.add_argument("--baseline", help="JSON de um retrato anterior: reporta só o que PIOROU")
    args = ap.parse_args(argv)

    res = run(os.path.abspath(args.root))

    if args.baseline:
        try:
            with open(args.baseline, encoding="utf-8") as fh:
                old = {(f["who"], f["rule"], f["msg"]) for f in json.load(fh)["findings"]}
        except (OSError, ValueError, KeyError) as exc:
            sys.stderr.write("baseline ilegível (%s) — reportando tudo\n" % exc)
            old = set()
        res["findings"] = [f for f in res["findings"]
                           if (f["who"], f["rule"], f["msg"]) not in old]

    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(report(res))

    if args.fail_on:
        floor = SEV_ORDER[args.fail_on]
        if any(SEV_ORDER[f["sev"]] >= floor for f in res["findings"]):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
