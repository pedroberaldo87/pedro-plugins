#!/usr/bin/env python3
"""Suite do hook_contract.py — hooks de mentira, medidos em isolamento.

O valor desta suite não é provar que o checker ACUSA. É provar que ele
ABSOLVE. Na primeira rodada contra o repo real ele produziu 4 falsos-positivos,
todos derrubados na mão lendo o código:

  1. intent-guard/plan-gate.sh   — cap existe, mas é `-ge 2` literal (não `-ge $MAX`)
  2. intent-guard/plan-gate.sh   — jq guardado por `{ [ -z "$JQ" ] || … ; } && exit 0`
  3. guardrails/scope-cop.sh     — cap existe, mas o `exit 0` cai 7 linhas abaixo
  4. graphify-guard/*.sh         — "graphify" só aparece em comentário, string e
                                   no nome de OUTRO programa (graphify-detect.sh)

Cada um virou um caso aqui. Falso-positivo em ferramenta de auditoria custa caro
de um jeito específico: ele treina quem lê a ignorar a saída inteira.

E o caso 1/3 tem direção: **deixar de ver um cap que existe é barato** (alarme
falso que a conferência derruba); **ver um cap que não existe é caro** (um gate
que trava de verdade passa despercebido). Os testes fixam os dois lados.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hook_contract as hc  # noqa: E402

FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


class Repo(object):
    """Um repo de mentira com um plugin e os hooks que eu mandar."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="hook-contract-test-")

    def hook(self, name, body, event="PreToolUse", matcher="Bash", plugin="fake"):
        hd = os.path.join(self.root, "plugins", plugin, "hooks")
        os.makedirs(hd, exist_ok=True)
        with open(os.path.join(hd, name), "w", encoding="utf-8") as fh:
            fh.write(body)
        import json
        cfgp = os.path.join(hd, "hooks.json")
        cfg = {"hooks": {}}
        if os.path.exists(cfgp):
            with open(cfgp, encoding="utf-8") as fh:
                cfg = json.load(fh)
        cfg["hooks"].setdefault(event, []).append(
            {"matcher": matcher, "hooks": [
                {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/" + name}]})
        with open(cfgp, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh)
        return self

    def rules(self, script=None):
        res = hc.run(self.root)
        fs = res["findings"]
        if script:
            # `who` aponta pra ONDE A PROVA ESTÁ, e desde 2026-08-09 a prova de um
            # veredito sobre o NOME é a linha do REGISTRO no hooks.json — quem diz
            # em que evento o script roda é ele, não o corpo do script. Por isso o
            # nome do script é procurado também no `msg`, que passou a trazê-lo.
            fs = [f for f in fs if f["who"].endswith(script) or script in f["msg"]]
        return {f["rule"] for f in fs}

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


HDR = "#!/bin/bash\n"


def main():
    print("bloqueio sem cap — o achado que importa")
    r = Repo()
    r.hook("nocap.sh", HDR + 'INPUT=$(cat)\nif [ -n "$INPUT" ]; then\n  echo ruim >&2\n  exit 2\nfi\n')
    got = r.rules("nocap.sh")
    check("bloqueia sem cap -> R1", "R1-cap-ausente" in got)
    check("bloqueia sem kill-switch -> R3", "R3-sem-killswitch" in got)
    r.close()

    print("cap com variável (forma do project-doc)")
    r = Repo()
    r.hook("capvar.sh", HDR + '''SESSION=$1
MAX_NUDGES=3
COUNT_FILE="/tmp/x-${SESSION}-1"
COUNT=0
[ -f "$COUNT_FILE" ] && COUNT="$(cat "$COUNT_FILE")"
[ "$COUNT" -ge "$MAX_NUDGES" ] && exit 0
echo $((COUNT + 1)) > "$COUNT_FILE"
exit 2
''')
    check("cap por variável é reconhecido", "R1-cap-ausente" not in r.rules("capvar.sh"))
    r.close()

    print("cap com literal (forma do intent-guard) — falso-positivo nº 1")
    r = Repo()
    r.hook("caplit.sh", HDR + '''SID=$1
DENYF="/tmp/plandeny-${SID}"
N=0; [ -f "$DENYF" ] && N="$(cat "$DENYF")"
if [ "$N" -ge 2 ]; then
  exit 0
fi
echo $((N + 1)) > "$DENYF"
exit 2
''')
    check("cap com número literal é reconhecido", "R1-cap-ausente" not in r.rules("caplit.sh"))
    r.close()

    print("cap com o exit 0 longe (forma do scope-cop) — falso-positivo nº 3")
    r = Repo()
    r.hook("capfar.sh", HDR + '''SESSION=$1
MAX_STREAK=3
STREAK_FILE="/tmp/streak-${SESSION}"
STREAK=0
[ -f "$STREAK_FILE" ] && STREAK="$(cat "$STREAK_FILE")"
if [ "$STREAK" -ge "$MAX_STREAK" ]; then
  echo 0 > "$STREAK_FILE"
  printf 'rastro\\n' > /tmp/bypass
  echo "liberado por circuit breaker"
  echo "log"
  exit 0
fi
exit 2
''')
    check("cap com exit 0 a 6 linhas ainda é cap", "R1-cap-ausente" not in r.rules("capfar.sh"))
    r.close()

    print("comparação numérica solta NÃO é cap (a direção cara do erro)")
    r = Repo()
    r.hook("fakecap.sh", HDR + '''SESSION=$1
N=$(wc -l < /etc/hosts)
if [ "$N" -ge 5 ]; then
  echo "arquivo grande" >&2
fi
exit 2
''')
    check("-ge sem exit 0 por perto NÃO conta como cap",
          "R1-cap-ausente" in r.rules("fakecap.sh"))
    r.close()

    print("cap global (sem session_id na chave)")
    r = Repo()
    r.hook("capglobal.sh", HDR + '''MAX=3
F="$HOME/.claude/contador"
N=0; [ -f "$F" ] && N="$(cat "$F")"
[ "$N" -ge "$MAX" ] && exit 0
echo $((N+1)) > "$F"
exit 2
''')
    check("cap sem escopo de sessão -> R2", "R2-cap-global" in r.rules("capglobal.sh"))
    r.close()

    print("kill-switch nas formas reais do repo")
    for name, body in [
        ("killenv.sh", HDR + '[ "${MEU_NUDGE:-1}" = "0" ] && exit 0\nSESSION=$1\nS="/tmp/s-${SESSION}"\n[ -f "$S" ] && exit 0\ntouch "$S"\nexit 2\n'),
        ("killmode.sh", HDR + 'MODE_FILE="$HOME/.claude/x/mode"\n[ -f "$MODE_FILE" ] && exit 0\nSESSION=$1\nS="/tmp/s-${SESSION}"\n[ -f "$S" ] && exit 0\ntouch "$S"\nexit 2\n'),
    ]:
        r = Repo()
        r.hook(name, body)
        check("%s reconhecido como kill-switch" % name, "R3-sem-killswitch" not in r.rules(name))
        r.close()

    print("binário com caminho absoluto")
    r = Repo()
    r.hook("hardjq.sh", HDR + 'S=$(echo "$1" | /opt/homebrew/bin/jq -r .session_id)\nexit 0\n')
    check("caminho fixo do Homebrew -> R4", "R4-binario-fixo" in r.rules("hardjq.sh"))
    r.close()
    r = Repo()
    r.hook("shebang.sh", "#!/usr/local/bin/bash\nexit 0\n")
    check("shebang NÃO é binário fixo", "R4-binario-fixo" not in r.rules("shebang.sh"))
    r.close()

    print("fail-open nas duas formas — falso-positivo nº 2")
    r = Repo()
    r.hook("guard1.sh", HDR + 'command -v jq >/dev/null 2>&1 || exit 0\necho "$1" | jq .\n')
    check("command -v jq || exit 0 é guarda", "R5-sem-failopen" not in r.rules("guard1.sh"))
    r.close()
    r = Repo()
    r.hook("guard2.sh", HDR + 'PY="$(command -v python3)"; JQ="$(command -v jq)"\n'
                              '{ [ -z "$PY" ] || [ -z "$JQ" ]; } && exit 0\n'
                              'echo "$1" | "$JQ" -r .x | "$PY" -c "pass"\n')
    check("guarda composta { -z || -z ; } && exit 0 é guarda",
          "R5-sem-failopen" not in r.rules("guard2.sh"))
    r.close()
    r = Repo()
    r.hook("noguard.sh", HDR + 'echo "$1" | jq -r .session_id\n')
    check("jq sem guarda nenhuma -> R5", "R5-sem-failopen" in r.rules("noguard.sh"))
    r.close()

    print("nome de ferramenta que não é invocação — falso-positivo nº 4")
    r = Repo()
    r.hook("mention.sh", HDR + '''# roda o graphify query antes de grep
SCRIPT_DIR=$(dirname "$0")
LINES=$(bash "$SCRIPT_DIR/graphify-detect.sh" "$1")
CTX="tem grafo: rode && graphify query 'x' pra consultar"
echo "$CTX"
''')
    check("graphify em comentário/string/outro-programa NÃO é uso",
          "R5-sem-failopen" not in r.rules("mention.sh"))
    r.close()

    print("hook que só informa não precisa de cap")
    r = Repo()
    r.hook("info.sh", HDR + 'jq -n --arg m "oi" \'{systemMessage:$m}\'\nexit 0\n',
           event="Stop", matcher="*")
    got = r.rules("info.sh")
    check("só systemMessage -> sem R1", "R1-cap-ausente" not in got)
    check("só systemMessage -> sem R3", "R3-sem-killswitch" not in got)
    r.close()

    print("erros de configuração")
    r = Repo()
    r.hook("existe.sh", HDR + "exit 0\n")
    os.remove(os.path.join(r.root, "plugins", "fake", "hooks", "existe.sh"))
    check("hooks.json apontando pra script ausente -> R0",
          "R0-script-ausente" in r.rules())
    r.close()

    print("cegueiras derrubadas na varredura dos hooks reais")
    r = Repo()
    r.hook("inlinesent.sh", HDR + """SESSION=$1
ID=costura-x
STATE_DIR="/tmp/gate-${SESSION}"
mkdir -p "$STATE_DIR"
if [ -f "$STATE_DIR/${ID}.denied" ]; then
  exit 0
fi
touch "$STATE_DIR/${ID}.denied"
exit 2
""")
    check("sentinela montada inline (sem var 'SENTINEL') é cap",
          "R1-cap-ausente" not in r.rules("inlinesent.sh"))
    r.close()

    r = Repo()
    r.hook("stopgate.sh", HDR + '''python3 -c "print('{\\"decision\\": \\"block\\"}')"\n''',
           event="Stop", matcher="*")
    check("hook de Stop não é cobrado por cap (o harness tem o nativo)",
          "R1-cap-ausente" not in r.rules("stopgate.sh"))
    r.close()

    r = Repo()
    r.hook("loopsent.sh", HDR + """SESSION=$1
STATE_DIR="/tmp/gate-${SESSION}"
mkdir -p "$STATE_DIR"
for ID in a b c; do
  if [ -f "$STATE_DIR/${ID}.denied" ]; then
    continue
  fi
  touch "$STATE_DIR/${ID}.denied"
  REASON="$ID"
done
[ -n "$REASON" ] && exit 2
exit 0
""")
    check("sentinela dentro de laço com `continue` é cap",
          "R1-cap-ausente" not in r.rules("loopsent.sh"))
    r.close()

    r = Repo()
    r.hook("helper.sh", HDR + """tem_arquivo() {
  [ -f "$1" ] || return 1
  local t
  t=$(cat "$1")
  [ -n "$t" ]
}
outra() {
  [ -d "/tmp/x" ] && return 0
  return 1
}
tem_arquivo /etc/hosts || exit 2
exit 2
""")
    check("[ -f \"$1\" ] em função auxiliar NÃO é cap (o erro caro)",
          "R1-cap-ausente" in r.rules("helper.sh"))
    r.close()

    r = Repo()
    r.hook("capfn.sh", HDR + """SESSION=$1
MAX=3
F="/tmp/c-${SESSION}"
N=0; [ -f "$F" ] && N="$(cat "$F")"
capped() { [ "$N" -ge "$MAX" ]; }
bump()   { echo $((N + 1)) > "$F"; }
capped && exit 0
bump
exit 2
""")
    check("cap fatorado em função (`capped && exit 0`) é cap",
          "R1-cap-ausente" not in r.rules("capfn.sh"))
    r.close()

    r = Repo()
    r.hook("condguard.sh", HDR + """if command -v python3 >/dev/null 2>&1; then
  python3 -c "print(1)"
fi
exit 0
""")
    check("`if command -v X` guardando bloco conta como guarda",
          "R5-sem-failopen" not in r.rules("condguard.sh"))
    r.close()

    print("saída e gate")
    r = Repo()
    r.hook("nocap.sh", HDR + "exit 2\n")
    res = hc.run(r.root)
    check("o achado carrega a linha", all(isinstance(f["line"], int) for f in res["findings"]))
    check("--fail-on high sai 1 quando há ALTA",
          hc.main(["--root", r.root, "--json", "--fail-on", "high"]) == 1)
    r.close()
    r = Repo()
    r.hook("sessionstart-avisa-limpo.sh",
           HDR + 'command -v jq >/dev/null 2>&1 || exit 0\njq -n "{}"\nexit 0\n',
           event="SessionStart", matcher="*")
    check("hook limpo não gera achado nenhum", hc.run(r.root)["findings"] == [])
    check("--fail-on high sai 0 sem ALTA",
          hc.main(["--root", r.root, "--json", "--fail-on", "high"]) == 0)
    r.close()

    print()
    print("R6 — o nome tem que dizer QUANDO roda e SE barra")
    r = Repo()
    r.hook("scope-cop.sh", HDR + "exit 0\n", event="PreToolUse")
    check("nome sem evento nem verbo reprova",
          "R6-nome-fora-do-molde" in r.rules("scope-cop.sh"))
    r.close()

    r = Repo()
    r.hook("stop-avisa-doc.sh", HDR + "exit 0\n", event="PreToolUse")
    check("prefixo de evento que não é o registrado reprova",
          "R6-nome-evento-errado" in r.rules("stop-avisa-doc.sh"))
    r.close()

    r = Repo()
    r.hook("pretooluse-avisa-plano.sh",
           HDR + 'SESSION=$1\nF="/tmp/x-${SESSION}"\n[ -f "$F" ] && exit 0\n'
                 '[ "${X:-1}" = "0" ] && exit 0\ntouch "$F"\nexit 2\n',
           event="PreToolUse")
    check("verbo de aviso em script que bloqueia reprova",
          "R6-nome-verbo-errado" in r.rules("pretooluse-avisa-plano.sh"))
    r.close()

    r = Repo()
    r.hook("posttooluse-barra-nada.sh", HDR + "exit 0\n", event="PostToolUse")
    check("verbo de bloqueio em script que só avisa reprova",
          "R6-nome-verbo-errado" in r.rules("posttooluse-barra-nada.sh"))
    r.close()

    r = Repo()
    r.hook("posttooluse-anota-uso.sh", HDR + "exit 0\n", event="PostToolUse")
    check("nome no molde passa", "R6" not in "".join(r.rules("posttooluse-anota-uso.sh")))
    r.close()

    check("script em dois eventos casa com um deles",
          hc.judge_nome("posttooluse-anota-uso.sh",
                        {"PreToolUse", "PostToolUse"}, False) is None)

    print()
    print("o medidor do fim de turno conta o TEXTO, não o embrulho de dados")
    envelope = '{\n  "systemMessage": "a\\nb\\nc\\nd\\ne"\n}'
    check("cinco linhas de mensagem contam cinco, não as três do JSON",
          hc._linhas_visiveis(envelope) == 5)
    check("o campo de bloqueio também é desembrulhado",
          hc._linhas_visiveis('{"reason": "um\\ndois"}') == 2)
    check("texto puro em stderr segue contado como sempre",
          hc._linhas_visiveis("uma\ndupla") == 2)
    check("saída vazia custa zero", hc._linhas_visiveis("") == 0)
    check("linha em branco no meio não conta",
          hc._linhas_visiveis('{"systemMessage": "a\\n\\n\\nb"}') == 2)
    check("JSON sem campo de texto cai na contagem crua",
          hc._linhas_visiveis('{"outro": 1}') == 1)
    check("saída que não é JSON não quebra o medidor",
          hc._linhas_visiveis("{ isto nao fecha") == 1)

    print()
    print("o orçamento do fim de turno barra a DERIVA, não o número de hoje")
    import json as _json
    import tempfile as _tf
    atual = {"emissores": [{"plugin": "visual", "script": "a.sh", "linhas": 5, "timeout": 15},
                           {"plugin": "novo", "script": "b.py", "linhas": 0, "timeout": 20}],
             "total_linhas": 5, "teto": 6}

    def retrato(total, emissores):
        p = _tf.mktemp(suffix=".json")
        with open(p, "w", encoding="utf-8") as fh:
            _json.dump({"total_linhas": total, "emissores": emissores, "teto": 6}, fh)
        return p

    igual = retrato(5, [{"plugin": "visual", "script": "a.sh", "linhas": 5}])
    check("total igual ao retrato passa", hc._piorou(atual, igual) == 0)
    folgado = retrato(9, [{"plugin": "visual", "script": "a.sh", "linhas": 9}])
    check("total menor que o retrato passa", hc._piorou(atual, folgado) == 0)
    magro = retrato(3, [{"plugin": "visual", "script": "a.sh", "linhas": 3}])
    check("total maior que o retrato barra", hc._piorou(atual, magro) == 1)
    check("retrato ilegível NÃO barra — gate não trava por infra",
          hc._piorou(atual, "/caminho/que/nao/existe.json") == 0)
    with open(magro, "w", encoding="utf-8") as fh:
        fh.write("{ isto nao fecha")
    check("retrato corrompido NÃO barra", hc._piorou(atual, magro) == 0)
    # o estado de hoje é 6 de um teto de 6: um gate por número absoluto barraria o
    # próximo commit que tocasse hook sem nada ter piorado. Este não barra.
    no_limite = retrato(6, [{"plugin": "visual", "script": "a.sh", "linhas": 6}])
    check("estar NO teto não barra — só subir barra",
          hc._piorou({"emissores": [], "total_linhas": 6}, no_limite) == 0)

    print()
    print("o medidor enxerga hook de plugin de TERCEIRO, e só a versão viva")
    lar = _tf.mkdtemp(prefix="cc-terceiros-")
    try:
        def instala(mercado, plug, versao, cmd, registrado=True):
            d = os.path.join(lar, "plugins", "cache", mercado, plug, versao, "hooks")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "hooks.json"), "w", encoding="utf-8") as fh:
                _json.dump({"hooks": {"Stop": [{"matcher": "*", "hooks": [
                    {"type": "command", "command": cmd, "timeout": 9}]}]}}, fh)
            return "%s@%s" % (plug, mercado), versao if registrado else None

        idx = {}
        for mercado, plug, versao, reg in [("outro", "novo", "2.0.0", True),
                                           ("outro", "novo", "1.0.0", False),
                                           ("pedro-plugins", "meu", "1.0.0", True)]:
            k, v = instala(mercado, plug, versao, "echo oi", reg)
            if v:
                idx.setdefault(k, []).append({"version": v})
        os.makedirs(os.path.join(lar, "plugins"), exist_ok=True)
        with open(os.path.join(lar, "plugins", "installed_plugins.json"), "w",
                  encoding="utf-8") as fh:
            _json.dump({"version": 2, "plugins": idx}, fh)

        antigo = os.environ.get("CLAUDE_CONFIG_DIR")
        os.environ["CLAUDE_CONFIG_DIR"] = lar
        try:
            achados = hc._emissores_de_terceiros()
        finally:
            if antigo is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = antigo

        chaves = {(a["marketplace"], a["plugin"], a["versao"]) for a in achados}
        check("acha o hook de Stop de um marketplace de fora",
              ("outro", "novo", "2.0.0") in chaves)
        check("versão antiga no cache NÃO é medida — é código morto",
              ("outro", "novo", "1.0.0") not in chaves)
        check("o próprio marketplace fica de fora — já entra pelo repositório",
              not any(m == "pedro-plugins" for m, _, _ in chaves))
        check("guarda a raiz do plugin, que é o que o comando dele interpola",
              all(a["raiz"].endswith(os.path.join("novo", "2.0.0")) for a in achados))
        # índice ausente não pode ESCONDER emissor: sem saber quem é vivo, mede todos
        os.remove(os.path.join(lar, "plugins", "installed_plugins.json"))
        os.environ["CLAUDE_CONFIG_DIR"] = lar
        try:
            sem_indice = hc._emissores_de_terceiros()
        finally:
            if antigo is None:
                os.environ.pop("CLAUDE_CONFIG_DIR", None)
            else:
                os.environ["CLAUDE_CONFIG_DIR"] = antigo
        check("sem o índice, mede a mais em vez de a menos", len(sem_indice) == 2)
    finally:
        shutil.rmtree(lar, ignore_errors=True)

    print()
    print("kill-switch de hook Python é reconhecido")
    r = Repo()
    r.hook("guarda.py",
           '#!/usr/bin/env python3\nimport os, json, sys\n'
           'if os.environ.get("MEU_GUARDA") == "0":\n    sys.exit(0)\n'
           'print(json.dumps({"decision": "block", "reason": "x"}))\n',
           event="Stop", matcher="*")
    achados = [f for f in hc.run(r.root)["findings"] if f["rule"] == "R3-sem-killswitch"]
    check("guarda Python com interruptor não é acusado de não ter", achados == [])
    r.close()

    r = Repo()
    r.hook("sem-guarda.py",
           '#!/usr/bin/env python3\nimport json\n'
           'print(json.dumps({"decision": "block", "reason": "x"}))\n',
           event="Stop", matcher="*")
    achados = [f for f in hc.run(r.root)["findings"] if f["rule"] == "R3-sem-killswitch"]
    check("guarda Python SEM interruptor continua sendo acusado", len(achados) == 1)
    r.close()

    print()
    print("o retrato viaja no git: nada de caminho de máquina dentro")
    r = Repo()
    r.hook("calado.sh", "#!/bin/sh\nexit 0\n")
    # A forma que os hooks.json usam hoje: normalização de barra por `tr`, e o
    # script no rabo do comando. Sem reconhecê-la, TODO hook vira R0-script-ausente.
    novo = ("CLAUDE_PLUGIN_ROOT=$(printf '%s' \"$CLAUDE_PLUGIN_ROOT\" | tr '\\\\' /); "
            "export CLAUDE_PLUGIN_ROOT; \"$CLAUDE_PLUGIN_ROOT\"/hooks/calado.sh")
    check("a forma de comando em uso hoje resolve pro script real",
          hc.resolve_script(r.root, "fake", novo)
          == os.path.join(r.root, "plugins", "fake", "hooks", "calado.sh"))
    res = hc.run(r.root)
    import json as _json
    bruto = _json.dumps(res, ensure_ascii=False)
    check("a saída não carrega a raiz de quem mediu", "root" not in res)
    check("caminho de script sai relativo à raiz", r.root not in bruto)

    # ── TODO ACHADO SAI COM O PAR DE CITAÇÕES (decisão do dono, 2026-08-09) ──
    # A vistoria recusa na porta achado sem par (arquivo:linha + trecho literal),
    # e o tradutor dela repetia o `msg` como "prova" para tapar o buraco. Medido
    # antes do conserto no repo real: 41 dos 42 achados saíam com `quote` vazio e
    # `line` 0, e os 42 `who` não resolviam como caminho. O conserto foi na FONTE,
    # e é aqui que ele para de regredir.
    r.close()
    r = Repo()
    r.hook("scope-cop.sh", HDR + "exit 0\n", event="PreToolUse")          # R6
    r.hook("sessionstart-avisa-jq.sh", HDR + 'jq -n "{}"\nexit 0\n',
           event="SessionStart", matcher="*")                            # R5
    fs = hc.run(r.root)["findings"]
    check("o repro gera achado de R5 e de R6",
          {f["rule"][:2] for f in fs} >= {"R5", "R6"})
    check("nenhum achado sai sem trecho literal", all(f["quote"] for f in fs))
    check("nenhum achado sai com linha 0", all(f["line"] for f in fs))
    check("todo `who` resolve como arquivo de verdade",
          all(os.path.exists(os.path.join(r.root, f["who"])) for f in fs))
    check("o trecho é prova, não eco da mensagem",
          all(f["quote"] != f["msg"] for f in fs))
    r.close()

    # A linha citada tem que CASAR a regra que gerou o achado: o R5 nasce de uso
    # em posição de comando, então citar a linha que só MENCIONA a ferramenta
    # (echo, prosa) manda o dono para o lugar errado.
    print("o trecho do R5 é a linha que INVOCA a ferramenta, não a que a menciona")
    r = Repo()
    r.hook("avisa-jq.sh", HDR + 'echo "este hook precisa de jq instalado"\njq -n "{}"\nexit 0\n',
           event="SessionStart", matcher="*")
    fs = [f for f in hc.run(r.root)["findings"] if f["rule"] == "R5-sem-failopen"]
    check("o repro gera o R5", len(fs) == 1)
    check("a linha citada é a da invocação", fs and fs[0]["line"] == 3)
    check("o trecho citado é o comando, não o aviso",
          fs and fs[0]["quote"].startswith("jq -n"))
    r.close()

    # O mesmo par de citações vale pro hooks.json que nem abre: era o único
    # achado que saía com `who` sendo o NOME NU do plugin (não resolve como
    # caminho), linha 0 e o texto do parser repetido como "prova".
    r = Repo()
    r.hook("ok.sh", HDR + "exit 0\n", plugin="bom")
    hd = os.path.join(r.root, "plugins", "quebrado", "hooks")
    os.makedirs(hd)
    with open(os.path.join(hd, "hooks.json"), "w", encoding="utf-8") as fh:
        fh.write('{\n  "hooks": {\n    "PreToolUse": [,]\n  }\n}\n')
    fs = [f for f in hc.run(r.root)["findings"] if f["rule"] == "R0-config"]
    check("hooks.json ilegível vira um achado", len(fs) == 1)
    check("o `who` do hooks.json ilegível resolve como arquivo de verdade",
          all(os.path.exists(os.path.join(r.root, f["who"])) for f in fs))
    check("o hooks.json ilegível aponta a linha real do estrago",
          all(f["line"] == 3 for f in fs))
    check("o trecho do hooks.json ilegível é a linha do arquivo, não o eco do msg",
          all(f["quote"] == '"PreToolUse": [,]' for f in fs))
    r.close()

    print()
    print("retrato sem a raiz continua comparável")
    r = Repo()
    r.hook("bloqueia.sh", "#!/bin/sh\nexit 2\n")
    retrato = os.path.join(r.root, "retrato.json")
    with open(retrato, "w", encoding="utf-8") as fh:
        _json.dump({k: v for k, v in hc.run(r.root).items() if k != "root"}, fh)
    check("--baseline sem campo de raiz não reporta nada de novo",
          hc.main(["--root", r.root, "--baseline", retrato, "--fail-on", "high"]) == 0)
    r.close()

    print()
    print("quem responde ao ExitPlanMode — antes e depois da fusão dos gates")
    # ANTES: três plugins disputam o mesmo evento (o estado de hoje).
    r = Repo()
    r.hook("a.sh", HDR + "exit 0", matcher="ExitPlanMode", plugin="p1")
    r.hook("b.sh", HDR + "exit 0", matcher="EnterPlanMode|ExitPlanMode", plugin="p2")
    r.hook("c.sh", HDR + "exit 0", matcher="ExitPlanMode", plugin="p3")
    r.hook("d.sh", HDR + "exit 0", matcher="Bash", plugin="p4")   # não é do evento
    antes = hc.respondentes(r.root, "ExitPlanMode")
    check("antes da fusão: os três respondem", len(antes) == 3)
    check("a alternância EnterPlanMode|ExitPlanMode conta",
          {e["plugin"] for e in antes} == {"p1", "p2", "p3"})
    check("hook de outra ferramenta não entra na conta",
          "p4" not in {e["plugin"] for e in antes})
    r.close()

    # DEPOIS: a fusão deixa um só registrado — os outros dois saem do evento.
    r = Repo()
    r.hook("fundido.sh", HDR + "exit 0", matcher="ExitPlanMode", plugin="p1")
    r.hook("outro.sh", HDR + "exit 0", matcher="Edit|Write", plugin="p2")
    r.hook("mais.sh", HDR + "exit 0", event="Stop", matcher="*", plugin="p3")
    depois = hc.respondentes(r.root, "ExitPlanMode")
    check("depois da fusão: só um responde", len(depois) == 1)
    check("e é o gate fundido", depois and depois[0]["plugin"] == "p1")
    r.close()

    # O repo real, medido: a fusão do F14.5 aconteceu em 2026-08-09 — o portão
    # único da família responde sozinho, e chama intent-guard e visual por nome
    # (fail-open). Este número voltar a subir é regressão da fusão.
    REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reais = hc.respondentes(REPO, "ExitPlanMode")
    ESPERADO_HOJE = 1
    check("o repo real tem %d respondente(s) ao ExitPlanMode (tem %d)"
          % (ESPERADO_HOJE, len(reais)), len(reais) == ESPERADO_HOJE)
    # Vivo = tem suíte que o exercita com o evento. Fundir com um mudo esconderia
    # justamente o caso que a fusão precisa cobrir.
    SUITES = {
        "intent-guard": "plugins/intent-guard/hooks/test_plan_gate.sh",
        "project-skills": "plugins/project-skills/hooks/test_plan_gate.sh",
        "visual": "plugins/visual/hooks/test_exitplan_gate.sh",
    }
    for e in reais:
        s = SUITES.get(e["plugin"])
        vivo = False
        if s and os.path.exists(os.path.join(REPO, s)):
            with open(os.path.join(REPO, s), encoding="utf-8", errors="replace") as fh:
                vivo = "ExitPlanMode" in fh.read()
        check("%s tem suíte que o exercita com o evento" % e["plugin"], vivo)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
