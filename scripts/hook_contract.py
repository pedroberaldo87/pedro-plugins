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
import glob
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
    # Hook Python desliga por env var lida no código, e os quatro padrões acima só
    # falam shell — todo guarda Python era acusado de não ter interruptor que tem.
    re.compile(r'environ\.get\(\s*["\'](\w+)["\'][^)]*\)\s*==\s*["\'](0|off)["\']'),
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
                        "hooks_json": hj,
                    }
                    out.append(entry)
    return out


def cita_registro(root, hooks_json, alvo):
    """O par arquivo:linha + linha literal do REGISTRO do hook no hooks.json.

    Existe porque 41 dos 42 achados saíam com quote vazio e line 0 (decisão do
    dono, 2026-08-09): a vistoria exige citação real — achado sem par de
    citações é recusado na porta —, e o tradutor dela repetia o msg como
    "prova". A prova de um veredito sobre NOME/registro é a linha do registro.
    """
    rel = os.path.relpath(hooks_json, root) if hooks_json else "?"
    # o alvo pode chegar como a linha de comando inteira do hooks.json — o basename
    # dela arrasta aspas e barras de escape, e aí a busca nunca casa com o texto cru.
    nome = os.path.basename(alvo or "").strip("\\\"'")
    if hooks_json and nome and os.path.exists(hooks_json):
        try:
            with open(hooks_json, encoding="utf-8") as fh:
                for i, ln in enumerate(fh, 1):
                    if nome in ln:
                        return rel, i, ln.strip()
        except OSError:
            pass
    return rel, 0, ""


def respondentes(root, ferramenta, evento="PreToolUse"):
    """Quem responde a UMA ferramenta num evento — a medida da fusão de gates.

    Três plugins disputam o `ExitPlanMode` hoje; depois da fusão tem que sobrar
    um. Contar na mão é o que deixou a divergência passar, então a contagem
    vira comando: `--responde ExitPlanMode`.

    Matcher é a expressão do próprio hooks.json: `*` (ou vazio) pega tudo,
    `EnterPlanMode|ExitPlanMode` pega as duas — a alternância é do formato, não
    invento aqui.
    """
    achados = []
    for e in discover(root):
        if e.get("event") != evento:
            continue
        mt = (e.get("matcher") or "*").strip()
        if mt in ("", "*"):
            achados.append(e)
            continue
        try:
            if re.fullmatch(mt, ferramenta):
                achados.append(e)
        except re.error:
            continue
    return achados


def resolve_script(root, plug, cmd):
    """`${CLAUDE_PLUGIN_ROOT}/hooks/x.sh` → `<root>/plugins/<plug>/hooks/x.sh`."""
    if not cmd:
        return None
    # Hook que mora em OUTRO plugin: `resolve-plugin.sh <nome> <caminho/dentro/dele>`.
    # Sem esta forma, o inventário mediria o RESOLVEDOR — e o script de verdade
    # apareceria uma vez por plugin que o chama, que é exatamente o que a cópia
    # única veio matar. O aviso de dependência é o caso: treze registros, um script.
    m = re.search(r"resolve-plugin\.sh\s+([\w.-]+)\s+([\w./-]+\.(?:sh|py))", cmd)
    if m:
        return os.path.join(root, "plugins", m.group(1), m.group(2))
    # Forma nova: `CLAUDE_PLUGIN_ROOT=$(printf '%s' "$CLAUDE_PLUGIN_ROOT" | tr '\\' /)`
    # normaliza backslash → barra sem `${x//y/z}` (que é bashismo e morre no shell
    # POSIX do Linux). O script fica no rabo, após o ';', em três formas:
    # "$CLAUDE_PLUGIN_ROOT"/hooks/x.sh · python3 "$…/hooks/x.py" · bash "$…/hooks/x.sh".
    if re.search(r"tr\s+'\\\\'\s+/", cmd):
        # O que é SOURCEADO não é o hook — é biblioteca. Sem tirar o `source` da
        # frente, o primeiro `/hooks/*.sh` do comando é sempre `hook-json.sh`, e o
        # scanner passava a medir a BIBLIOTECA: cobrava cap e kill-switch dela por
        # causa do `hj_deny` que ela oferece, quando quem decide bloquear é o hook
        # que a chama — e esse tem o kill-switch dele. Falso-positivo confirmado em
        # 2026-08-07, em 3 plugins de uma vez.
        limpo = re.sub(r"(^|[;&|]|\s)(\.|source)\s+\"?[^\s;&|\"]+\"?", r"\1", cmd)
        m = re.search(r'/hooks/([\w.-]+\.(?:sh|py))', limpo)
        if m:
            return os.path.join(root, "plugins", plug, "hooks", m.group(1))
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
            ln = next((i + 1 for i, linha in enumerate(lines) if re.match(r"\s*%s\s*\(\)" % re.escape(fn), linha)), 0)
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

def judge(entry, m, root="."):
    """Achados. Cada um carrega a linha que o disparou — pra conferir rápido.

    `who` é o caminho REAL do script relativo à raiz (decisão do dono,
    2026-08-09): o apelido "plugin/basename" não resolvia como caminho em
    nenhum dos 42 achados, e a vistoria — que monta `onde` como who:line —
    apontava para arquivo inexistente."""
    f = []
    who = os.path.relpath(entry["script"], root)
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
        # a citação é a primeira linha que USA a ferramenta — line 0 e quote vazio
        # eram o que fazia a vistoria repetir o msg como "prova" (2026-08-09).
        ln, quote = 0, ""
        try:
            with open(entry["script"], encoding="utf-8", errors="replace") as fh:
                for i, linha in enumerate(fh, 1):
                    if re.search(r"\b%s\b" % re.escape(tool), linha) and not linha.lstrip().startswith("#"):
                        ln, quote = i, linha.strip()[:110]
                        break
        except OSError:
            pass
        f.append(dict(rule="R5-sem-failopen", sev="med", who=who, line=ln,
                      msg="usa %s sem guarda de ausência (command -v … || exit 0)" % tool,
                      quote=quote))
    return f


# ── R6 · o nome diz QUANDO roda e SE barra ───────────────────────────────────
# `scope-cop.sh`, `mark-work.sh` e `delivery-audit.sh` são o mesmo problema: pra
# saber quando cada um roda e se ele trava o agente era preciso abrir os três.
# O molde é `<evento>-<verbo>-<assunto>.<ext>`: o prefixo é o evento em que ele
# está registrado, e o verbo declara o poder — barra ou só avisa. O verbo não é
# decorativo: aqui ele é conferido contra o canal MEDIDO no script, então um
# `-avisa-` que sai com `exit 2` reprova igual a um nome fora do molde.
VERBO_BARRA = ("barra", "exige", "trava", "recusa")
VERBO_AVISA = ("avisa", "anota", "mede", "lembra", "resume", "sincroniza", "colhe", "abre")
NOME_MOLDE = re.compile(r"^([a-z]+)-([a-z]+)-([a-z0-9-]+)\.(?:sh|py)$")


def judge_nome(nome, eventos, bloqueia):
    """Reprova nome de hook que não diz quando roda nem se barra.

    `eventos` é o conjunto de eventos em que o script está registrado — um script
    pode estar em dois (o andamento do sprint está em Pre e PostToolUse), e aí
    basta o prefixo casar com UM deles.
    """
    esperados = sorted(e.lower() for e in eventos)
    m = NOME_MOLDE.match(nome)
    if not m:
        return ("R6-nome-fora-do-molde",
                "o nome não diz quando roda nem se barra — molde: "
                "<evento>-<verbo>-<assunto> (evento: %s · verbo: %s)"
                % ("|".join(esperados) or "?",
                   "|".join(VERBO_BARRA if bloqueia else VERBO_AVISA)))
    evento, verbo = m.group(1), m.group(2)
    if evento not in esperados:
        return ("R6-nome-evento-errado",
                "o nome diz que roda em '%s', mas está registrado em %s"
                % (evento, ", ".join(esperados) or "nenhum evento"))
    certos = VERBO_BARRA if bloqueia else VERBO_AVISA
    errados = VERBO_AVISA if bloqueia else VERBO_BARRA
    if verbo in errados or verbo not in certos:
        return ("R6-nome-verbo-errado",
                "o verbo '%s' não bate com o que o script faz (%s) — use um de: %s"
                % (verbo, "bloqueia" if bloqueia else "só avisa", "|".join(certos)))
    return None


def run(root):
    entries = discover(root)
    findings, measured = [], []
    for e in entries:
        if e.get("error"):
            rel = os.path.relpath(e["hooks_json"], root) if e.get("hooks_json") else e["plugin"]
            findings.append(dict(rule="R0-config", sev="high", who=rel,
                                 line=0, msg=e["error"], quote=e["error"]))
            continue
        if e["type"] != "command":
            measured.append(dict(e, measure=None, note="hook do tipo '%s' — sem script pra medir" % e["type"]))
            continue
        if not e["script"] or not os.path.exists(e["script"]):
            rel, ln, quote = cita_registro(root, e.get("hooks_json"), e.get("command"))
            findings.append(dict(rule="R0-script-ausente", sev="high", who=rel, line=ln,
                                 msg="hooks.json aponta pra script que não existe: %s" % e["command"],
                                 quote=quote))
            continue
        m = measure(e["script"])
        measured.append(dict(e, measure=m))
        findings.extend(judge(e, m, root))

    # R6 é do SCRIPT, não do registro: um script em dois eventos tem um nome só,
    # e o prefixo dele basta casar com um deles. Por isso o julgamento do nome
    # espera todos os registros terem sido varridos.
    por_script = {}
    for e in measured:
        if not e.get("script") or not e.get("measure"):
            continue
        d = por_script.setdefault(e["script"], {"plugin": e["plugin"], "eventos": set(),
                                                "bloqueia": False,
                                                "hooks_json": e.get("hooks_json"),
                                                "command": e.get("command")})
        d["eventos"].add(e["event"])
        d["bloqueia"] = d["bloqueia"] or bool(e["measure"]["blocking"])
    for caminho, d in sorted(por_script.items()):
        nome = os.path.basename(caminho)
        veredito = judge_nome(nome, d["eventos"], d["bloqueia"])
        if veredito:
            # A prova de um veredito sobre o NOME é a linha do REGISTRO: quem diz
            # em que evento o script roda é o hooks.json, não o corpo do script.
            rel, ln, quote = cita_registro(root, d["hooks_json"], nome)
            findings.append(dict(rule=veredito[0], sev="high", who=rel, line=ln,
                                 msg="%s: %s" % (nome, veredito[1]), quote=quote))

    # `hooks_json` é caminho ABSOLUTO (o `cita_registro` precisa abrir o arquivo) e
    # não pode sobreviver na saída: ela é comparada entre máquinas, e a raiz de quem
    # mediu vazando é o que o check "a saída não carrega a raiz" pega. Sai só AQUI,
    # depois do laço de R6 — apagá-lo antes deixava o veredito de nome sem registro
    # a citar, e o achado voltava a sair com `who` "?" e linha 0.
    for e in measured:
        e.pop("hooks_json", None)

    # dedup: o mesmo script pode estar registrado em mais de um evento
    seen, uniq = set(), []
    for f in sorted(findings, key=lambda x: (-SEV_ORDER[x["sev"]], x["who"], x["rule"])):
        k = (f["who"], f["rule"], f["msg"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    n_scripts = len({e["script"] for e in measured if e.get("script")})
    # O retrato viaja no git deste repositório PÚBLICO, então nada aqui pode
    # carregar o caminho da máquina que mediu: a raiz não é emitida, e o caminho
    # do script sai relativo a ela. Quem lê o retrato só usa `findings`, logo a
    # ausência da raiz não quebra comparação nenhuma.
    measured = [dict(e, script=os.path.relpath(e["script"], root))
                if e.get("script") else e for e in measured]
    return {"entries": len(entries), "scripts": n_scripts, "findings": uniq,
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


# ── orçamento do fim de turno ──────────────────────────────────────────────
# Seis hooks disputam o `Stop` neste marketplace, cada um respeitando o próprio
# teto e nenhum sabendo do total. Em 2026-08-02 o dono mediu na tela: quatro
# blocos de progresso de plano, `6/9 · 35s · 773 tokens`. Cada emissor estava
# dentro do que prometia; o CONJUNTO é que não tinha dono.
#
# Isto não é gate — é medidor. Roda cada emissor num sandbox (HOME e
# CLAUDE_CONFIG_DIR temporários, projeto vazio) com o payload que o harness
# manda, e conta as linhas que saem. Sandbox porque emissor de Stop escreve
# estado, e medir não pode sujar a máquina de quem mede.
STOP_TETO_LINHAS = 6


def _linhas_visiveis(out):
    """As linhas que o HUMANO lê, não as do envelope de dados.

    Emissor de Stop imprime `{"systemMessage": "…"}` ou `{"reason": "…"}` — três linhas
    de JSON com o texto inteiro dentro de um campo. Contar a saída crua media o
    embrulho: um resumo de 5 linhas na tela era reportado como 3, e o teto estava
    sendo comparado contra um número menor que o real. Quem escreve em stderr (os
    hooks que saem 2) já emite texto puro, e cai no caminho de baixo.
    """
    texto = (out or "").strip()
    if not texto:
        return 0
    try:
        d = json.loads(texto)
    except ValueError:
        d = None
    if isinstance(d, dict):
        campos = [d.get(k) for k in ("systemMessage", "reason", "additionalContext")]
        msg = "\n".join(c for c in campos if isinstance(c, str))
        if msg.strip():
            texto = msg
    return len([x for x in texto.split("\n") if x.strip()])


def _emissores_de_terceiros():
    """Hooks de `Stop` dos plugins INSTALADOS que não são deste repositório.

    O medidor nasceu olhando só `plugins/*/hooks/hooks.json` daqui, e isso é um ponto
    cego: quem paga o fim de turno é a máquina, não o repositório. Um plugin de outro
    marketplace com hook de `Stop` verboso entra no mesmo orçamento e não aparecia.

    Eles ficam FORA do total gateado, de propósito. O retrato viaja no git e o gate
    barra deriva; se o total incluísse o que cada máquina instalou, o mesmo commit
    passaria numa máquina e barraria noutra. Aqui é relatório, lá é contrato.

    Mede pelo COMANDO registrado, não por caminho de script: hook de terceiro pode ser
    um one-liner de shell chamando outro runtime (o `impeccable` chama `node`), e o
    regex de `.sh|.py` do laço principal não o alcança.
    """
    raiz = os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude"))
    base = os.path.join(raiz, "plugins", "cache")

    # O cache guarda TODA versão já instalada, não só a viva — sem este filtro o
    # `codex` aparecia duas vezes (1.0.3 e 1.0.6) e o relatório media código morto.
    # Quem sabe qual está valendo é `installed_plugins.json`, e o índice vivo mora em
    # `["plugins"]`, não na raiz: `{"version": 2, "plugins": {"<plug>@<mercado>": [...]}}`.
    vivos = set()
    try:
        with open(os.path.join(raiz, "plugins", "installed_plugins.json"),
                  encoding="utf-8") as fh:
            idx = (json.load(fh) or {}).get("plugins") or {}
        for chave, insts in idx.items():
            plug, _, mercado = chave.partition("@")
            for inst in insts if isinstance(insts, list) else []:
                if inst.get("version"):
                    vivos.add((mercado, plug, inst["version"]))
    except (OSError, ValueError, AttributeError):
        vivos = set()                     # sem o índice, não filtra — melhor a mais que a menos

    fora = []
    for f in sorted(glob.glob(os.path.join(base, "*", "*", "*", "hooks", "hooks.json"))):
        partes = f.split(os.sep)
        mercado, plug, versao = partes[-5], partes[-4], partes[-3]
        if mercado == "pedro-plugins":
            continue                      # esses já entram pelo repositório, medidos daqui
        if vivos and (mercado, plug, versao) not in vivos:
            continue                      # versão antiga no cache, não é o que roda
        try:
            with open(f, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, ValueError):
            continue
        for h in cfg.get("hooks", {}).get("Stop", []):
            for hh in h.get("hooks", []):
                cmd = hh.get("command", "")
                if cmd:
                    fora.append({"marketplace": mercado, "plugin": plug, "versao": versao,
                                 "cmd": cmd, "raiz": os.path.dirname(os.path.dirname(f)),
                                 "timeout": hh.get("timeout")})
    return fora


def stop_budget(root):
    """Quanto o fim de turno custa em linhas, emissor a emissor."""
    import shutil
    import subprocess
    import tempfile

    emissores = []
    for f in sorted(glob.glob(os.path.join(root, "plugins/*/hooks/hooks.json"))):
        plug = f.split(os.sep)[-3]
        try:
            with open(f, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, ValueError):
            continue
        for h in cfg.get("hooks", {}).get("Stop", []):
            for hh in h.get("hooks", []):
                cmd = hh.get("command", "")
                # QUEM EMITE É O SCRIPT, NÃO A BIBLIOTECA (2026-08-09). Aqui havia um
                # `re.search(r"([\w.-]+\.(?:sh|py))", cmd)` — o PRIMEIRO nome de arquivo
                # do comando. Em todo emissor que faz `. hooks/hook-json.sh; "$PY" …`,
                # o primeiro é a biblioteca: três emissores reais (`stop-prose-ceiling.py`,
                # `stop-forma-relato.py`, `stop-anuncio-sem-acao.py`) apareciam como
                # `hook-json.sh` com 0 linha, o orçamento saía SUBESTIMADO, e a comparação
                # com o retrato congelado batia nome contra nome errado. `resolve_script`
                # já resolvia isso 400 linhas acima — este bloco o reinventava pior.
                caminho = resolve_script(root, plug, cmd)
                if caminho and os.path.exists(caminho):
                    emissores.append((plug, os.path.basename(caminho), caminho, hh.get("timeout")))

    terceiros = _emissores_de_terceiros()
    fora = []
    sandbox = tempfile.mkdtemp(prefix="stop-budget-")
    linhas_tot = 0
    saida = []
    try:
        # Sandbox VAZIO mede o caso trivial e não serve: emissor calado num projeto
        # sem nada é o que já esperávamos. O que interessa é o PIOR caso realista —
        # o que o dono viu na tela. Então o sandbox nasce povoado: N planos abertos
        # e um transcript com edições, que é o gatilho das cobranças.
        # MARCADOR DE PROJETO, e ele não é detalhe: `resolve-dir.sh` aplica uma
        # cascata (raiz git → marcador → ~/Desktop). Sem marcador o sandbox não é
        # projeto, a cascata cai no Desktop, e o medidor passa a LER OS PLANOS
        # REAIS do dono — foi o que aconteceu na primeira versão disto.
        # O HOME de mentira fica FORA do projeto, e não é detalhe: a busca por marcador
        # em `resolve-dir.sh` PARA ao chegar no HOME. Com HOME == sandbox a cascata
        # caía no fallback do Desktop, os 4 planos abaixo nunca eram lidos, e o que
        # este medidor reportava era o aviso de plano AUSENTE — o cenário oposto ao
        # "pior caso realista" que ele declara medir.
        lar = os.path.join(sandbox, "lar")
        os.makedirs(lar, exist_ok=True)
        projeto = os.path.join(sandbox, "projeto")
        os.makedirs(projeto, exist_ok=True)
        open(os.path.join(projeto, "CLAUDE.md"), "w").close()
        planos = os.path.join(projeto, ".claude", "plans")
        os.makedirs(planos, exist_ok=True)
        for i in range(4):
            with open(os.path.join(planos, "p%d.plan.json" % i), "w", encoding="utf-8") as fh:
                json.dump({"id": "p%d" % i, "title": "Plano de medição %d" % i,
                           "status": "active",
                           "phases": [{"id": "F1", "title": "Fase", "items": [
                               {"id": "F1.%d" % j, "title": "passo %d" % j,
                                "desc": "linha didática do passo %d" % j,
                                "status": "todo"} for j in (1, 2, 3)]}]}, fh)
        trans = os.path.join(projeto, "t.jsonl")
        with open(trans, "w", encoding="utf-8") as fh:
            for i in range(5):
                fh.write(json.dumps({"type": "assistant", "message": {
                    "role": "assistant", "content": [
                        {"type": "tool_use", "name": "Edit",
                         "input": {"file_path": "/x/a%d.py" % i}}]}}) + "\n")
        payload = json.dumps({"session_id": "budget-probe", "cwd": projeto,
                              "transcript_path": trans})
        env = dict(os.environ, HOME=lar, CLAUDE_CONFIG_DIR=os.path.join(lar, ".claude"),
                   CLAUDE_PROJECT_DIR=projeto, TMPDIR=sandbox)
        for plug, nome, caminho, timeout in emissores:
            runner = ["python3", caminho] if caminho.endswith(".py") else ["bash", caminho]
            try:
                r = subprocess.run(runner, input=payload, capture_output=True,
                                   text=True, env=env, cwd=projeto, timeout=20, start_new_session=True)
                out = (r.stdout or "") + (r.stderr or "")
            except (subprocess.TimeoutExpired, OSError) as exc:
                out = ""
                nome = "%s (nao mediu: %s)" % (nome, type(exc).__name__)
            n = _linhas_visiveis(out)
            linhas_tot += n
            saida.append({"plugin": plug, "script": nome, "linhas": n, "timeout": timeout})

        # Os de fora do repositório: mesmo sandbox, mesmo payload, contagem separada.
        # `CLAUDE_PLUGIN_ROOT` é o que o comando deles interpola, então tem que apontar
        # pra raiz do plugin instalado — sem isso o hook não acha o próprio script e
        # mede zero por motivo errado.
        for t in terceiros:
            env_t = dict(env, CLAUDE_PLUGIN_ROOT=t["raiz"])
            try:
                r = subprocess.run(["bash", "-c", t["cmd"]], input=payload,
                                   capture_output=True, text=True, env=env_t,
                                   cwd=projeto, timeout=20, start_new_session=True)
                out = (r.stdout or "") + (r.stderr or "")
                nota = None
            except (subprocess.TimeoutExpired, OSError) as exc:
                out, nota = "", "nao mediu: %s" % type(exc).__name__
            fora.append({"marketplace": t["marketplace"], "plugin": t["plugin"],
                         "versao": t["versao"], "linhas": _linhas_visiveis(out),
                         "timeout": t["timeout"], "nota": nota})
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    return {"emissores": saida, "total_linhas": linhas_tot, "teto": STOP_TETO_LINHAS,
            "terceiros": fora, "total_terceiros": sum(x["linhas"] for x in fora)}


def _piorou(atual, caminho):
    """Compara o orçamento com um retrato congelado. rc=1 quando o total SOBE.

    Teto absoluto não serve aqui: o total já encostou nos 6 de referência, então exigir
    um número barraria o próximo commit que tocasse hook, sem que nada tivesse piorado.
    O que importa é a DERIVA — o oitavo emissor entrando sem ninguém ver, que é o
    defeito que originou o teto (cada autor dentro do seu, o conjunto sem dono).

    Mesmo desenho do `--baseline` do contrato, e pelo mesmo motivo: comparar com o
    retrato não trava a dívida já aceita, mas trava o acréscimo.

    Retrato ilegível NÃO barra — gate que trava por infra é pior que gate nenhum.
    """
    try:
        with open(caminho, encoding="utf-8") as fh:
            antes = json.load(fh)
        antes_tot = int(antes["total_linhas"])
        por_script = {(e["plugin"], e["script"]): e["linhas"]
                      for e in antes.get("emissores", [])}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("\n  (retrato ilegível em %s: %s — nada a comparar)"
              % (caminho, type(exc).__name__))
        return 0
    if atual["total_linhas"] <= antes_tot:
        print("  ✓ não piorou vs o retrato (%d linha(s) lá)" % antes_tot)
        return 0
    print("\n  ❌ O FIM DE TURNO ENGORDOU: %d → %d linha(s)"
          % (antes_tot, atual["total_linhas"]))
    for e in atual["emissores"]:
        velho = por_script.get((e["plugin"], e["script"]))
        if velho is None:
            print("     + %s/%s — emissor NOVO, %d linha(s)"
                  % (e["plugin"], e["script"], e["linhas"]))
        elif e["linhas"] > velho:
            print("     ↑ %s/%s — %d → %d linha(s)"
                  % (e["plugin"], e["script"], velho, e["linhas"]))
    print("     → enxugue, ou aceite conscientemente e recongele o retrato:")
    print("       python3 scripts/hook_contract.py --stop-budget --json > %s" % caminho)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="hook_contract.py", description=__doc__.split("\n")[0])
    ap.add_argument("--stop-budget", action="store_true",
                    help="mede quantas linhas os emissores de Stop produzem juntos")
    ap.add_argument("--root", default=".")
    ap.add_argument("--scripts", action="store_true",
                    help="imprime o CAMINHO de cada script de hook registrado, um por linha")
    ap.add_argument("--responde", metavar="FERRAMENTA",
                    help="lista quem responde a essa ferramenta (ex.: ExitPlanMode)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on", choices=("high", "med", "low"), help="exit 1 se houver achado nesse nível ou pior")
    ap.add_argument("--baseline", help="JSON de um retrato anterior: reporta só o que PIOROU")
    args = ap.parse_args(argv)

    if args.scripts:
        # A lista dos scripts que o harness REALMENTE carrega, por caminho.
        # Existe porque "hook" não é todo `.sh` dentro de `hooks/`: biblioteca
        # local (`lib-rodada.sh`, `lib-tmpdir.sh`) mora lá e não roda em evento
        # nenhum. Comparar por NOME de arquivo também não serve — `lib-tmpdir.sh`
        # está em sete plugins, e um registro num deles faria os outros seis
        # passarem por registrados. Quem pergunta "quantos hooks existem?" chama
        # isto, em vez de listar o diretório e adivinhar.
        raiz = os.path.abspath(args.root)
        res = run(raiz)
        vistos = []
        for e in res.get("measured", []):
            sc = e.get("script")
            if sc and sc not in vistos:
                vistos.append(sc)
        for sc in sorted(vistos):
            print(sc)
        return 0

    if args.stop_budget:
        b = stop_budget(os.path.abspath(args.root))
        if args.json:
            print(json.dumps(b, ensure_ascii=False, indent=2))
            return 0
        print("Orçamento do fim de turno — linhas que cada emissor de Stop produz\n")
        for e in b["emissores"]:
            print("  %-13s %-34s %3d linha(s)   timeout=%ss"
                  % (e["plugin"], e["script"], e["linhas"], e["timeout"]))
        print("\n  TOTAL: %d linha(s) · teto de referência: %d"
              % (b["total_linhas"], b["teto"]))
        if b["total_linhas"] > b["teto"]:
            print("  ⚠️  acima do teto — o fim de turno virou relatório, não resumo")
        if b.get("terceiros"):
            print("\n  Instalados nesta máquina, FORA do gate "
                  "(o retrato viaja no git; o que cada máquina instala, não):")
            for t in b["terceiros"]:
                print("  %-13s %-34s %3d linha(s)   timeout=%ss%s"
                      % (t["marketplace"], "%s %s" % (t["plugin"], t["versao"]),
                         t["linhas"], t["timeout"],
                         "  ⚠️ %s" % t["nota"] if t.get("nota") else ""))
            print("\n  SOMADO ao que a máquina realmente paga: %d linha(s)"
                  % (b["total_linhas"] + b["total_terceiros"]))
        if args.baseline:
            return _piorou(b, args.baseline)
        return 0

    if args.responde:
        quem = respondentes(os.path.abspath(args.root), args.responde)
        if args.json:
            print(json.dumps([{"plugin": e["plugin"], "matcher": e["matcher"],
                               "script": os.path.basename(e["script"] or "?")}
                              for e in quem], ensure_ascii=False, indent=2))
        else:
            print("Quem responde a %s (evento PreToolUse)\n" % args.responde)
            for e in quem:
                print("  %-13s %-34s matcher=%s"
                      % (e["plugin"], os.path.basename(e["script"] or "?"), e["matcher"]))
            print("\n  TOTAL: %d" % len(quem))
        return 0

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
