#!/usr/bin/env python3
"""Aspas de shell no motor do /sprint (P5 · scan hsf_bdf8f754, hsf_bfa6322d, hsf_3849dde4).

O motor escreve COMANDOS DE SHELL dentro dos prompts dos papéis mecânicos, e dois dos
textos que entram neles não são do motor: o nome de arquivo que a decomposição devolve e
o nome do arquivo do plano (que pode vir de um repositório clonado), mais a prova que o
executor cola no `summary`. Aqui os comandos que o motor ESCREVE são EXECUTADOS de
verdade, com programas de mentira que só gravam o argv que receberam, e se aferem duas
coisas: o argv chega inteiro (um argumento por texto, sem fatiar) e nenhum comando
embutido no texto rodou (o marcador `PWNED*` não nasceu).

    python3 plugins/project-skills/lib/test_motor_aspas.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from bash_posix import bash_posix  # noqa: E402  — o vendorado ao lado, nunca o PATH pelado

PLUGIN = os.path.dirname(AQUI)
MOTOR = os.path.join(PLUGIN, "skills", "sprint", "references", "motor.js")

FAILS = []


def check(nome, cond, detalhe=""):
    if cond:
        print("  ok   %s" % nome)
    else:
        print("  FAIL %s  %s" % (nome, detalhe))
        FAILS.append(nome)


# ── a bancada: o corpo do motor, cortado ANTES do laço, devolvendo as funções ──────
HARNESS = r"""
const fs = require('fs')
const CFG = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
let src = fs.readFileSync(process.argv[3], 'utf8').replace('export const meta', 'const meta')
const corte = src.indexOf('// ───────────────────────── MOTOR ─────────────────────────')
if (corte < 0) { console.error('marca do corte ausente'); process.exit(3) }
src = src.slice(0, corte) + `
return { saudePrompt, orfaosPrompt, reservaPrompt, runSuitePrompt, tickPlanPrompt,
         pendenciaPrompt, checkpointPrompt,
         nomeDeArquivoSujo: typeof nomeDeArquivoSujo === 'undefined' ? null : nomeDeArquivoSujo }`
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
new AsyncFunction('args', 'agent', 'phase', 'log', 'budget', src)(CFG.args, null, () => {}, () => {}, null)
  .then(f => {
    const out = {}
    for (const [nome, chamada] of CFG.chamadas) {
      out[nome] = nome === 'nomeDeArquivoSujo'
        ? CFG.args.nomes.map(n => f.nomeDeArquivoSujo ? f.nomeDeArquivoSujo(n) : null)
        : f[nome](chamada)
    }
    process.stdout.write(JSON.stringify(out))
  })
  .catch(e => { console.error(String(e && e.stack || e)); process.exit(2) })
"""


def prompts(tmp, args, chamadas):
    cfg = os.path.join(tmp, "cfg.json")
    harness = os.path.join(tmp, "harness.js")
    with open(cfg, "w", encoding="utf-8") as fh:
        json.dump({"args": args, "chamadas": chamadas}, fh)
    with open(harness, "w", encoding="utf-8") as fh:
        fh.write(HARNESS)
    r = subprocess.run(["node", harness, cfg, MOTOR], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError("bancada do motor falhou (%d): %s" % (r.returncode, r.stderr[:400]))
    return json.loads(r.stdout)


# ── os programas de mentira: gravam o argv que receberam, um arquivo por programa ───
STUB_RESOLVE = """#!/bin/bash
# resolve-plugin.sh de mentira: <plugin> <caminho relativo> -> o stub de mesmo nome
printf '%s\\n' "$STUBS/$(basename "$2")"
"""
STUB_SH = """#!/bin/bash
python3 - "$@" <<'PY'
import json, os, sys
with open(os.path.join(os.environ["SAIDA"], "argv-" + os.environ["QUEM"] + ".jsonl"), "a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
PY
"""
STUB_PY = """import json, os, sys
with open(os.path.join(os.environ["SAIDA"], "argv-" + os.environ["QUEM"] + ".jsonl"), "a") as fh:
    fh.write(json.dumps(sys.argv[1:]) + "\\n")
"""


def monta_stubs(tmp):
    stubs = os.path.join(tmp, "stubs")
    saida = os.path.join(tmp, "saida")
    os.makedirs(stubs)
    os.makedirs(saida)
    with open(os.path.join(stubs, "resolve-plugin.sh"), "w") as fh:
        fh.write(STUB_RESOLVE)
    for nome in ("reserva-de-arquivos.sh",):
        with open(os.path.join(stubs, nome), "w") as fh:
            fh.write(STUB_SH.replace('os.environ["QUEM"]', '"reserva"'))
    for nome, quem in (("plan_state.py", "plan_state"), ("orfaos.py", "orfaos"),
                       ("andamento.py", "andamento")):
        with open(os.path.join(stubs, nome), "w") as fh:
            fh.write(STUB_PY.replace('os.environ["QUEM"]', repr(quem)))
    return stubs, saida


def comandos_indentados(prompt):
    """Os comandos indentados (`  bash ...` / `  python3 ...`) do prompt, cada um até a linha
    em branco — um nome de arquivo com quebra de linha faz o comando ocupar mais de uma."""
    return [m.strip() for m in re.findall(r"(?:^|\n)(  (?:bash|python3) .*?)(?=\n\n|\Z)", prompt, re.S)]


def blocos_bash(prompt):
    return re.findall(r"```bash\n(.*?)\n```", prompt, re.S)


def roda(script, cwd, stubs, saida):
    env = dict(os.environ, STUBS=stubs, SAIDA=saida)
    return subprocess.run([bash_posix(), "-c", script], cwd=cwd, env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)


def argvs(saida, quem):
    caminho = os.path.join(saida, "argv-%s.jsonl" % quem)
    if not os.path.exists(caminho):
        return []
    with open(caminho, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def barras(lista):
    """No Windows o motor monta a pasta com `/` (ele divide o caminho do plano em `/`):
    o que importa aqui é a palavra de shell, não a barra — compara sem ela."""
    return [[a.replace("\\", "/") for a in linha] for linha in lista]


def marcadores(*pastas):
    return sorted(n for p in pastas for n in os.listdir(p) if n.startswith("PWNED"))


if not shutil.which("node"):
    print("  FAIL node ausente — o motor é JavaScript e este teste o executa")
    sys.exit(1)

tmp = tempfile.mkdtemp(prefix="motor-aspas-")
try:
    stubs, saida = monta_stubs(tmp)
    # A raiz do repositório tem espaço E apóstrofo — o caso que quebra aspas ingênuas.
    raiz = os.path.join(tmp, "r o'ot")
    # O motor divide o caminho do plano em `/` (planIdDe/dirDe): é a forma em que o caminho chega a
    # ele em qualquer sistema, então o plano daqui também usa `/` (no Windows o os.path.join daria `\\`).
    plans = os.path.join(raiz, ".claude", "plans").replace(os.sep, "/")
    os.makedirs(plans)
    plano = plans + "/x;touch PWNED-plano $(touch PWNED-sub).plan.json"
    args = {"repoRoot": raiz, "planPath": plano, "sessionId": "sess1", "motorId": "mot1",
            "resolvePlugin": os.path.join(stubs, "resolve-plugin.sh"),
            "resolveSkill": os.path.join(stubs, "resolve-plugin.sh"),
            "resolveSprintPlugin": os.path.join(stubs, "resolve-plugin.sh"),
            "nomes": []}

    NOMES = ["a b.ts", "it's;touch PWNED-aspa.ts", "$(touch PWNED-sub2).ts", "`touch PWNED-crase`.ts",
             "quebra\nde linha.ts", 'dupla"aspa.ts']
    EVID = ("feito · $(touch PWNED-evid) · `touch PWNED-crase2` · \"aspas\" · it's · $HOME\n"
            "segunda linha ; touch PWNED-ev3 · files: a b.ts")
    PEND = 'Pergunta do dono: manter "x" ou $(touch PWNED-pend)? é o `y` do it\'s'
    ret = prompts(tmp, args, [
        ["reservaPrompt", {"verbo": "reservar", "sessionId": "sess1", "motorId": "mot1", "files": NOMES}],
        ["orfaosPrompt", {"repoRoot": raiz, "planPath": plano}],
        ["saudePrompt", {"repoRoot": raiz, "round": 1, "suiteCmd": None, "tetoMin": 10}],
        ["runSuitePrompt", {"repoRoot": raiz, "round": 1, "bloco": 1, "suiteCmd": None, "tetoMin": 10}],
        ["tickPlanPrompt", {"planPath": plano, "passos": [
            {"taskId": "F1.1", "retomada": False, "evidencia": EVID},
            {"taskId": "F1.2", "retomada": True, "evidencia": "outra"}]}],
        ["pendenciaPrompt", {"planPath": plano, "passos": [{"taskId": "F1.1", "pendencia": PEND}]}],
        ["checkpointPrompt", {"repoRoot": raiz, "round": 2, "bloco": 1, "planPath": plano, "results": [
            {"files_touched": ["a b.ts", "it's.ts", "$(touch PWNED-ck).ts"]}]}],
    ])

    # ── 46 · nomes de arquivo na reserva ────────────────────────────────────────
    print("hsf_bdf8f754 — nome de arquivo na reserva")
    cmds = comandos_indentados(ret["reservaPrompt"])
    check("a reserva escreve um comando", len(cmds) == 1, repr(cmds))
    if cmds:
        r = roda(cmds[0], raiz, stubs, saida)
        esperado = ["reservar", "sess1", "mot1"] + NOMES
        check("o hook de reserva recebe cada nome como UM argumento, byte a byte",
              argvs(saida, "reserva") == [esperado], "%r | %s" % (argvs(saida, "reserva"), r.stderr[:200]))
        check("nenhum comando embutido no nome rodou (reserva)", marcadores(raiz, tmp, saida) == [],
              repr(marcadores(raiz, tmp, saida)))

    # ── 46 · nomes no checkpoint (laço de import + commit) ─────────────────────
    print("hsf_bdf8f754 — nome de arquivo no checkpoint")
    ck = blocos_bash(ret["checkpointPrompt"])
    check("o checkpoint traz o script num bloco ```bash", len(ck) == 1, "blocos=%d" % len(ck))
    if len(ck) == 1:
        repo = os.path.join(tmp, "repo ck'")
        os.makedirs(os.path.join(repo, ".claude", "plans"))
        env_git = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                       GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        subprocess.run(["git", "init", "-q", repo], check=True, env=env_git)
        for n in ("a b.ts", "it's.ts", "$(touch PWNED-ck).ts", "fora.ts"):
            with open(os.path.join(repo, n), "w") as fh:
                fh.write("x\n")
        # o prompt da bancada anterior apontava para `raiz`; refaz com o repositório real
        ret2 = prompts(tmp, dict(args, repoRoot=repo), [["checkpointPrompt", {
            "repoRoot": repo, "round": 2, "bloco": 1, "planPath": None,
            "results": [{"files_touched": ["a b.ts", "it's.ts", "$(touch PWNED-ck).ts"]}]}]])
        blocos = blocos_bash(ret2["checkpointPrompt"])
        for b in blocos:
            subprocess.run([bash_posix(), "-c", b], cwd=repo, env=env_git, capture_output=True,
                           text=True, stdin=subprocess.DEVNULL)
        lista = subprocess.run(["git", "-C", repo, "show", "--name-only", "--format=", "-z", "HEAD"],
                               capture_output=True, text=True, env=env_git)
        no_commit = sorted(x for x in lista.stdout.split("\0") if x)
        check("o commit leva os três nomes, inteiros, e deixa `fora.ts` de fora",
              no_commit == sorted(["a b.ts", "it's.ts", "$(touch PWNED-ck).ts"]), repr(no_commit))
        check("nenhum comando embutido no nome rodou (checkpoint)", marcadores(repo, tmp) == [],
              repr(marcadores(repo, tmp)))

    # ── 44 · plano com metacaractere no nome: orfaos, andamento, tick, pendência ─
    print("hsf_3849dde4 — caminho e id do plano")
    cmds = comandos_indentados(ret["orfaosPrompt"])
    check("o detector de órfãos escreve um comando", len(cmds) == 1, repr(cmds))
    if cmds:
        roda('ORFAOS="$STUBS/orfaos.py"\n' + cmds[0], raiz, stubs, saida)
        check("orfaos.py recebe o plano e a raiz como UM argumento cada",
              argvs(saida, "orfaos") == [[plano, "--root", raiz]], repr(argvs(saida, "orfaos")))
    for qual, onde in (("saudePrompt", "andamento da saúde"), ("runSuitePrompt", "andamento da suíte")):
        cmds = [c for c in comandos_indentados(ret[qual]) if "ANDAMENTO" in c]
        if cmds:
            antes = len(argvs(saida, "andamento"))
            roda('ANDAMENTO="$STUBS/andamento.py"\n' + cmds[0], raiz, stubs, saida)
            novos = argvs(saida, "andamento")[antes:]
            check("%s: o caminho do plano chega como UM argumento" % onde,
                  bool(novos) and plano in novos[0], repr(novos))
        else:
            check("%s: achou o comando do andamento" % onde, False)

    print("hsf_3849dde4 / hsf_bfa6322d — tick com prova hostil")
    tick = blocos_bash(ret["tickPlanPrompt"])
    check("o tick escreve os comandos num bloco ```bash", len(tick) == 1, "blocos=%d" % len(tick))
    if tick:
        antes = len(argvs(saida, "plan_state"))
        r = roda(tick[0], raiz, stubs, saida)
        novos = argvs(saida, "plan_state")[antes:]
        stem = os.path.basename(plano)[:-len(".plan.json")]
        esperado = [["--dir", plans, "tick", stem, "F1.1", "--evidencia", EVID],
                    ["--dir", plans, "tick", stem, "F1.2", "--evidencia", "outra", "--retomada"]]
        check("cada tique chega com dir, id, tarefa e prova como argumentos inteiros",
              barras(novos) == barras(esperado), "%r | %s" % (novos, r.stderr[:200]))
        check("nenhum comando embutido no plano ou na prova rodou (tick)",
              marcadores(raiz, plans, tmp, saida) == [], repr(marcadores(raiz, plans, tmp, saida)))

    print("hsf_3849dde4 / hsf_bfa6322d — pendência com texto hostil")
    pend = blocos_bash(ret["pendenciaPrompt"])
    check("a pendência escreve o comando num bloco ```bash", len(pend) == 1, "blocos=%d" % len(pend))
    if pend:
        antes = len(argvs(saida, "plan_state"))
        r = roda(pend[0], raiz, stubs, saida)
        novos = argvs(saida, "plan_state")[antes:]
        stem = os.path.basename(plano)[:-len(".plan.json")]
        check("a pendência chega como UM argumento",
              barras(novos) == barras([["--dir", plans, "pendencia", stem, "F1.1", PEND]]), "%r | %s" % (novos, r.stderr[:200]))
        check("nenhum comando embutido na pendência rodou",
              marcadores(raiz, plans, tmp, saida) == [], repr(marcadores(raiz, plans, tmp, saida)))

    # ── 46 · nome com caractere de controle é recusado antes do despacho ────────
    print("hsf_bdf8f754 — nome com quebra de linha é recusado na decomposição")
    args_n = dict(args, nomes=["ok.ts", "a b.ts", "it's.ts", "quebra\nlinha.ts", "tab\t.ts", "nul\u0000.ts"])
    r = prompts(tmp, args_n, [["nomeDeArquivoSujo", None]])
    check("existe `nomeDeArquivoSujo` e ele recusa só nomes com caractere de controle",
          r["nomeDeArquivoSujo"] == [False, False, False, True, True, True], repr(r["nomeDeArquivoSujo"]))
    motor = open(MOTOR, encoding="utf-8").read()
    i_filtro = motor.find("nomeDeArquivoSujo(", motor.find("// ───────────────────────── MOTOR"))
    i_reserva = motor.find("await agent(reservaPrompt(")
    check("o laço aplica o filtro ANTES de despachar a reserva",
          0 < i_filtro < i_reserva, "filtro@%d reserva@%d" % (i_filtro, i_reserva))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print()
if FAILS:
    print("FALHOU: %d" % len(FAILS))
    for f in FAILS:
        print("  - " + f)
    sys.exit(1)
print("OK")
