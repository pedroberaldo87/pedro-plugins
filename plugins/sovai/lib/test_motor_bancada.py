#!/usr/bin/env python3
"""Bancada do motor — ele RODA contra um plano de mentira, e se afere o que ficou.

Cinco coisas se medem aqui: o plano sai marcado (F9.10), o teto de gasto desliga o motor
(F9.12), o vigia derruba a execucao com o registro mudo alem do limite e sem trabalho
vivo (F9.13 + F9.24), a onda verde fica no historico quando o motor e interrompido no
meio (F9.14), e a onda VERMELHA nao vira ponto de salvamento — nada e commitado e o
motor relata pelo nome qual suite quebrou (F9.15).

`test_travas_motor.py` cobra que a logica esta ESCRITA no esqueleto. Isso nao prova
que ela funciona: o bloco pode citar `tickPlanPrompt` e nada acontecer no arquivo do
plano. Aqui o esqueleto do SKILL.md e EXECUTADO em Node com os agentes de mentira, e o
papel que marca roda o comando REAL (o mesmo que a skill escreve, extraido dela) contra
um plano de verdade criado num diretorio temporario. O que se afere e o ARQUIVO depois:
quais passos ficaram `done`, e com que prova.

Sem Node ou sem Python o teste NAO inventa aprovacao — falha dizendo o que faltou.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL_MD = os.path.join(AQUI, "..", "skills", "sovai", "SKILL.md")
PLAN_STATE = os.path.join(AQUI, "..", "..", "visual", "lib", "plan_state.py")

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def esqueleto(texto):
    """O MAIOR bloco ```javascript — o motor. Mesma regra do test_travas_motor."""
    blocos = re.findall(r"```javascript\n(.*?)\n```", texto, re.S)
    return max(blocos, key=len) if blocos else ""


def comando_de_tique(texto):
    """A linha de comando que a skill manda o papel de marcacao rodar.

    Extraida do SKILL.md para o teste rodar O QUE ESTA ESCRITO la — comando copiado
    para dentro do teste envelhece calado e passa a aprovar o que ninguem executa.
    """
    for bloco in re.findall(r"```bash\n(.*?)\n```", texto, re.S):
        for linha in bloco.splitlines():
            if "plan_state.py" in linha and " tick " in linha:
                return linha.strip()
    return ""


def comando_de_checkpoint(texto):
    """A linha de comando com que a skill salva a onda verde no historico.

    Mesma regra do tique: extraida do SKILL.md, para a bancada rodar O QUE ESTA
    ESCRITO la — comando copiado para dentro do teste passaria a aprovar um salvamento
    que a skill nao manda mais fazer.
    """
    for bloco in re.findall(r"```bash\n(.*?)\n```", texto, re.S):
        for linha in bloco.splitlines():
            if "git -C" in linha and "commit" in linha:
                return linha.strip()
    return ""


# ── o plano de bancada ───────────────────────────────────────────────────────
PLANO = {
    "id": "2026-08-07-bancada-sovai",
    "title": "Plano de bancada do motor",
    "requisitos": [{"id": "S-18", "titulo": "O plano registra o que o motor fez",
                    "ca": "os passos saem marcados sem ninguem marcar a mao",
                    "epico": "E0 — Bancada"}],
    "phases": [{"id": "F1", "title": "Fase de bancada", "items": [
        {"id": "F1.1", "title": "Passo entregue", "desc": "o executor devolve done",
         "requisito": "S-18", "pronto": "o passo sai marcado com a prova"},
        {"id": "F1.2", "title": "Passo tambem entregue", "desc": "outro executor devolve done",
         "requisito": "S-18", "pronto": "o passo sai marcado com a prova"},
        {"id": "F1.3", "title": "Passo nao entregue", "desc": "o executor devolve done falso",
         "requisito": "S-18", "pronto": "o passo continua aberto"},
        {"id": "F1.4", "title": "Passo que estourou o teto", "desc": "o executor pede espera",
         "requisito": "S-18", "pronto": "o passo continua aberto"},
    ]}],
}

# Os agentes de mentira. O executor de F1.3 devolve `done: false` e o de F1.4 devolve
# `espera: true` — os dois casos que NAO podem sair marcados.
RESULTADOS = {
    "F1.1": {"task_id": "F1.1", "done": True, "summary": "escrevi o arquivo",
             "files_touched": ["a.py"], "anchor": "fim"},
    "F1.2": {"task_id": "F1.2", "done": True, "summary": "ajustei o hook",
             "files_touched": ["b.sh", "c.sh"], "anchor": "fim"},
    "F1.3": {"task_id": "F1.3", "done": False, "summary": "nao consegui",
             "files_touched": [], "anchor": "fim"},
    "F1.4": {"task_id": "F1.4", "done": True, "espera": True, "summary": "estourei o teto",
             "files_touched": ["d.py"], "anchor": "fim"},
}

HARNESS = r"""
const { execSync } = require('child_process')
const fs = require('fs')
const CFG = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const CORPO = fs.readFileSync(process.argv[3], 'utf8')

const PRELUDE = `
const DECOMP={}, TASK_RESULT={}, BUILD_REVIEW={}, RESERVA={}, SUITE_RESULT={};
const mk = n => (p => Object.assign({ __p: n }, p));
const decomposePrompt=mk('decompose'), execPrompt=mk('exec'), reviewBuildPrompt=mk('review'),
      runSuitePrompt=mk('suite'), checkpointPrompt=mk('checkpoint'), tickPlanPrompt=mk('tick'),
      diagnoseStuckTaskPrompt=mk('diag'), reservaPrompt=mk('reserva'), confirmBuildPrompt=mk('confirm');
`

const chamadas = []
const checkpoints = []
const agentes = []
const phase = () => {}
// O medidor de gasto da bancada: cada agente disparado queima `gastoPorChamada`. E o
// unico jeito de o disjuntor ser exercitado de verdade — com `spent()` fixo em zero
// (como era aqui), o teto nunca e alcancado e a trava passa sem nunca ter armado.
let gastoAcumulado = 0
const budget = { spent: () => gastoAcumulado }
const parallel = fns => Promise.all(fns.map(f => f()))

// O papel de marcacao roda o comando REAL da skill. E o unico agente com efeito de
// verdade: os outros so devolvem o dado canonico da rodada.
function tica(p) {
  let cmd = CFG.tickCmd
  for (const [k, v] of Object.entries({ '<plugin visual>': CFG.pluginVisual, '<raiz>': CFG.raiz,
                                        '<plano>': CFG.planoId, '<taskId>': p.taskId,
                                        '<evidencia>': p.evidencia })) {
    cmd = cmd.split(k).join(v)
  }
  chamadas.push({ taskId: p.taskId, evidencia: p.evidencia, cmd })
  execSync(cmd, { stdio: 'pipe' })
  return {}
}

// O papel que salva a onda, com efeito de verdade tambem: roda o comando REAL da skill
// (extraido dela) no repositorio de bancada. Sem efeito, "salvou" seria so uma string na
// lista de agentes — e o que se quer medir aqui e o que sobrou no HISTORICO depois de o
// motor ser interrompido.
function salva(p) {
  if (!CFG.checkpointCmd) return {}
  let cmd = CFG.checkpointCmd
  for (const [k, v] of Object.entries({ '<raiz>': CFG.raiz, '<r>': String(p.round) })) {
    cmd = cmd.split(k).join(v)
  }
  checkpoints.push({ round: p.round, cmd })
  execSync(cmd, { stdio: 'pipe', shell: '/bin/sh' })
  return {}
}

async function agent(p, opts) {
  agentes.push(p.__p)
  gastoAcumulado += (CFG.gastoPorChamada || 0)
  switch (p.__p) {
    case 'decompose': return { tasks: CFG.tasks, blockers: [] }
    case 'reserva':   return { recusado: false, arquivos: [] }
    case 'exec':
      // Executor que nao deixa nada no disco nao permite perguntar onde o trabalho foi
      // parar. Com CFG.escreveNoDisco ele escreve o arquivo da tarefa na raiz do repo.
      if (CFG.escreveNoDisco && CFG.results[p.task.id]?.done) {
        fs.writeFileSync(CFG.raiz + '/' + p.task.id + '.txt', 'obra de ' + p.task.id + '\n')
      }
      return CFG.results[p.task.id]
    case 'review':    return { complete: CFG.reviewComplete !== false, cohesive: true,
                               gaps: [], missingTasks: CFG.reviewComplete === false ? ['F1.3'] : [],
                               lawMark: null }
    // O sinal de vida e o trabalho vivo vem do cenario: com `heartbeat` fixo em CFG.now
    // (como era aqui) o registro nunca fica mudo e o vigia nunca arma — a trava passaria
    // sem nunca ter sido exercitada, do mesmo jeito que o disjuntor com spent() zerado.
    // A COR da suite vem do cenario. Com ela fixa em verde (como era aqui) a onda
    // vermelha nunca acontece, e a metade do F9.15 que RECUSA o salvamento passaria sem
    // nunca ter sido exercitada — mesmo vicio do spent() zerado e do heartbeat fresco.
    case 'suite':     return { green: CFG.suiteVerde !== false, failing: CFG.suiteFalhando || [],
                               placar: '4 ok',
                               heartbeat: CFG.heartbeat === null ? CFG.now : CFG.heartbeat,
                               trabalhoVivo: CFG.trabalhoVivo === true }
    case 'checkpoint': return salva(p)
    case 'tick':      return tica(p)
    default:          return {}
  }
}

const corpo = CORPO.replace(/^export const meta = \{[\s\S]*?\n\}\n/m, '')
const motor = new Function('args', 'agent', 'phase', 'budget', 'parallel',
                           'return (async () => {' + PRELUDE + corpo + '})()')
motor(CFG.args, agent, phase, budget, parallel).then(saida => {
  fs.writeFileSync(CFG.out, JSON.stringify({ saida, chamadas, checkpoints, agentes }, null, 2))
}).catch(e => { console.error('MOTOR ESTOUROU: ' + (e && e.stack || e)); process.exit(3) })
"""


def roda_motor(tmp, texto, plan_dir, tick_cmd, plan_path, token_budget=None,
               gasto_por_chamada=0, max_rounds=2, review_complete=True,
               agora=1, heartbeat=None, trabalho_vivo=False,
               checkpoint_cmd="", escreve_no_disco=False,
               suite_verde=True, suite_falhando=None):
    """Executa o esqueleto do SKILL.md com os agentes de mentira. Devolve
    {saida, chamadas, agentes} ou levanta AssertionError com o motivo."""
    corpo = os.path.join(tmp, "motor.js")
    with open(corpo, "w", encoding="utf-8") as fh:
        fh.write(esqueleto(texto))
    harness = os.path.join(tmp, "harness.js")
    with open(harness, "w", encoding="utf-8") as fh:
        fh.write(HARNESS)
    out = os.path.join(tmp, "saida.json")
    cfg = {
        "tickCmd": tick_cmd,
        "checkpointCmd": checkpoint_cmd,
        "escreveNoDisco": escreve_no_disco,
        "suiteVerde": suite_verde,
        "suiteFalhando": suite_falhando or [],
        "pluginVisual": os.path.abspath(os.path.join(AQUI, "..", "..", "visual")),
        "raiz": tmp,
        "planoId": PLANO["id"],
        "out": out,
        "now": agora,
        "heartbeat": heartbeat,
        "trabalhoVivo": trabalho_vivo,
        "gastoPorChamada": gasto_por_chamada,
        "reviewComplete": review_complete,
        "results": RESULTADOS,
        "tasks": [{"id": i["id"], "desc": i["desc"], "requisito": i["requisito"],
                   "pronto": i["pronto"], "files": ["%s.txt" % i["id"]],
                   "parallelizable": True, "dependsOn": [], "done": False}
                  for i in PLANO["phases"][0]["items"]],
        "args": {"planPath": plan_path, "planText": "plano de bancada", "maxRounds": max_rounds,
                 "tokenBudget": token_budget,
                 "severityFloor": "P1", "repoRoot": tmp, "churnThreshold": 2,
                 "hasQaLoop": True, "sessionId": "sessao-bancada", "motorId": "motor-bancada",
                 "now": agora, "model": "opus",
                 "tiers": {k: {"effort": "medium"} for k in
                           ("decompose", "coordinate", "executor", "mechanical",
                            "diagnose", "finalize")}},
    }
    cfg_path = os.path.join(tmp, "cfg.json")
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)
    proc = subprocess.run(["node", harness, cfg_path, corpo],
                          capture_output=True, text=True, cwd=tmp)
    if proc.returncode != 0:
        raise AssertionError("o motor nao rodou: %s" % (proc.stderr.strip() or proc.stdout.strip()))
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


def cria_plano(plan_dir):
    entrada = os.path.join(plan_dir, "_in.json")
    with open(entrada, "w", encoding="utf-8") as fh:
        json.dump(PLANO, fh)
    proc = subprocess.run([sys.executable, PLAN_STATE, "--dir", plan_dir, "init", "--file", entrada],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError("o plano de bancada nao foi criado: %s" % proc.stderr.strip())
    return os.path.join(plan_dir, "%s.plan.json" % PLANO["id"])


def bancada(texto, tick_cmd, **kw):
    """Uma rodada de bancada em diretorio proprio, com plano proprio. Cada cenario tem
    o seu — dois cenarios no mesmo plano marcariam passo ja marcado e o `tick` recusaria,
    misturando falha de registro com o que o cenario quer medir. Devolve None se o motor
    nao rodou (e o motivo ja saiu como check reprovado)."""
    tmp = tempfile.mkdtemp(prefix="sovai-bancada-")
    try:
        plan_dir = os.path.join(tmp, ".claude", "plans")
        os.makedirs(plan_dir)
        plan_path = cria_plano(plan_dir)
        try:
            return roda_motor(tmp, texto, plan_dir, tick_cmd, plan_path, **kw)
        except AssertionError as exc:
            check("o motor rodou de ponta a ponta (%s)" % exc, False)
            return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def bancada_git(texto, tick_cmd, ck_cmd, **kw):
    """Uma rodada de bancada dentro de um repositorio git de verdade, com o papel de
    salvamento rodando o comando REAL da skill. Devolve o que rodou MAIS o que sobrou no
    repositorio depois (historico, arvore versionada, o que ficou solto) — que e o unico
    jeito de perguntar se a onda virou ponto de salvamento ou nao. None se o motor nao
    rodou (e o motivo ja saiu como check reprovado)."""
    repo = tempfile.mkdtemp(prefix="sovai-bancada-git-")
    try:
        def git(*args):
            return subprocess.run(["git", "-C", repo] + list(args),
                                  capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "bancada@exemplo.invalido")
        git("config", "user.name", "bancada")
        git("commit", "-q", "--allow-empty", "-m", "base")
        plan_dir_g = os.path.join(repo, ".claude", "plans")
        os.makedirs(plan_dir_g)
        plan_path_g = cria_plano(plan_dir_g)
        try:
            rodada = roda_motor(repo, texto, plan_dir_g, tick_cmd, plan_path_g,
                                checkpoint_cmd=ck_cmd, escreve_no_disco=True, **kw)
        except AssertionError as exc:
            check("o motor rodou de ponta a ponta (%s)" % exc, False)
            return None
        rodada["log"] = git("log", "--oneline").stdout
        rodada["versionados"] = git("ls-tree", "-r", "--name-only", "HEAD").stdout.split()
        rodada["solto"] = git("status", "--porcelain").stdout
        return rodada
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def estado(plan_path):
    with open(plan_path, encoding="utf-8") as fh:
        plano = json.load(fh)
    return {i["id"]: i for ph in plano["phases"] for i in ph["items"]}


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()

    print("F9.10 — a skill nomeia o comando que marca o plano")
    tick_cmd = comando_de_tique(texto)
    check("o comando de tique esta escrito na skill", bool(tick_cmd))
    check("a prova que ele grava e a do EXECUTOR",
          "`summary` + `files_touched`" in texto and "nunca redigida por quem marca" in texto)

    if not shutil.which("node"):
        check("Node esta na maquina (sem ele a bancada nao roda)", False)
        return 1
    if not tick_cmd:
        return 1

    tmp = tempfile.mkdtemp(prefix="sovai-bancada-")
    try:
        plan_dir = os.path.join(tmp, ".claude", "plans")
        os.makedirs(plan_dir)
        plan_path = cria_plano(plan_dir)

        print("F9.10 — o motor roda em plano de bancada e o plano sai marcado")
        try:
            rodada = roda_motor(tmp, texto, plan_dir, tick_cmd, plan_path)
        except AssertionError as exc:
            check("o motor rodou de ponta a ponta (%s)" % exc, False)
            return 1
        saida, chamadas = rodada["saida"], rodada["chamadas"]
        check("o motor fechou a rodada", saida.get("built") is True)

        itens = estado(plan_path)
        check("F1.1 saiu marcado sem ninguem marcar a mao", itens["F1.1"]["status"] == "done")
        check("F1.2 saiu marcado sem ninguem marcar a mao", itens["F1.2"]["status"] == "done")
        check("a prova gravada e a do executor (o resumo dele)",
              "escrevi o arquivo" in (itens["F1.1"].get("evidence") or ""))
        check("a prova gravada traz os arquivos que o executor tocou",
              "b.sh" in (itens["F1.2"].get("evidence") or "")
              and "c.sh" in (itens["F1.2"].get("evidence") or ""))
        check("quem NAO devolveu done continua aberto",
              itens["F1.3"].get("status") != "done" and not itens["F1.3"].get("evidence"))
        check("quem estourou o teto (espera) continua aberto",
              itens["F1.4"].get("status") != "done" and not itens["F1.4"].get("evidence"))
        check("nenhuma marcacao a mais foi disparada",
              sorted(c["taskId"] for c in chamadas) == ["F1.1", "F1.2"])

        print("F9.10 — plano que nao e arquivo nao e marcado por ninguem")
        # Mesma rodada, com planPath de plano solto: o guarda do script tem que calar o
        # papel de marcacao inteiro (senao ele rodaria o tick contra um plano inexistente).
        tmp2 = tempfile.mkdtemp(prefix="sovai-bancada-solto-")
        try:
            os.makedirs(os.path.join(tmp2, ".claude", "plans"))
            rodada2 = roda_motor(tmp2, texto, plan_dir, tick_cmd,
                                 os.path.join(tmp2, "plano.md"))
            check("com plano fora do arquivo, nada e marcado", rodada2["chamadas"] == [])
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("F9.12 — sem teto, o motor roda ate a trava de voltas (o controle)")
    # O controle existe pra provar que quem desligou o motor na rodada seguinte foi o
    # TETO, e nao a obra ter ficado pronta ou a trava de voltas ter chegado antes.
    solto = bancada(texto, tick_cmd, token_budget=None, gasto_por_chamada=400,
                    max_rounds=3, review_complete=False)
    if solto is None:
        return 1
    check("sem teto, o motor gasta as 3 voltas inteiras", len(solto["saida"]["rounds"]) == 3)
    check("sem teto, quem parou foi a trava de voltas",
          solto["saida"]["stopReason"] == "max-rounds")
    check("sem teto, o gasto e alto e ninguem reclama",
          solto["saida"]["gasto"] > 400 and not any(
              "disjuntor" in (b.get("what") or "") for b in solto["saida"]["blockers"]))

    print("F9.12 — o motor estoura o teto, se desliga sozinho e diz quanto gastou")
    # Mesma missao, mesmo numero de voltas permitido, mesma queima por agente. A UNICA
    # diferenca e o teto — entao toda diferenca de desfecho abaixo e obra do disjuntor.
    est = bancada(texto, tick_cmd, token_budget=1000, gasto_por_chamada=400,
                  max_rounds=3, review_complete=False)
    if est is None:
        return 1
    saida3 = est["saida"]
    check("o motor se desligou antes de gastar as voltas", len(saida3["rounds"]) < 3)
    check("o motivo da parada e o orcamento", saida3["stopReason"] == "orcamento")
    check("ele relata o quanto gastou, em numero", saida3["gasto"] >= 1000)
    disjuntor = [b for b in saida3["blockers"] if "disjuntor" in (b.get("what") or "")]
    check("o desligamento vira Bloqueio, nao silencio", len(disjuntor) == 1)
    check("o Bloqueio diz o gasto, o teto e a rodada",
          bool(disjuntor) and re.search(r"gastou %d de 1000 tokens.*rodada 1" % saida3["gasto"],
                                        disjuntor[0]["what"]))
    check("ele nao declara obra construida ao se desligar", saida3["built"] is False)
    # A prova de que o desligamento e EFETIVO: nenhum agente foi disparado depois dele.
    # Trava que grava o motivo e seguisse gastando seria relatorio, nao disjuntor.
    check("nenhum decompositor foi disparado numa segunda volta",
          est["agentes"].count("decompose") == 1)
    check("o disjuntor cortou agente: gastou menos que a rodada sem teto",
          len(est["agentes"]) < len(solto["agentes"]))

    # ── F9.13 + F9.24 ────────────────────────────────────────────────────────────
    # O relogio da bancada. `AGORA` e o carimbo que a casca injeta; `MUDO_HA` poe o
    # ultimo sinal de vida 20 min atras, alem do limite de 12 min do vigia. Os tres
    # cenarios abaixo mudam UMA coisa cada um em cima da mesma missao — assim a
    # diferenca de desfecho so pode ser obra da condicao que mudou.
    AGORA = 10 ** 9
    MUDO_HA = AGORA - 20 * 60 * 1000

    print("F9.13 — com o registro fresco, o vigia nao encosta no motor (o controle)")
    fresco = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                     agora=AGORA, heartbeat=AGORA, trabalho_vivo=False)
    if fresco is None:
        return 1
    check("registro fresco: o motor gasta as 3 voltas inteiras",
          len(fresco["saida"]["rounds"]) == 3)
    check("registro fresco: quem parou foi a trava de voltas",
          fresco["saida"]["stopReason"] == "max-rounds")

    print("F9.24 — mudo, mas COM trabalho vivo, o vigia nao derruba (demora nao e travamento)")
    # A metade que separa demora de travamento: mesmo silencio do cenario seguinte,
    # so que a suite diz que ha trabalho rodando. Sem esta metade, o vigia mataria
    # agente no meio de uma suite longa — que foi o motivo de a condicao ser dupla.
    vivo = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                   agora=AGORA, heartbeat=MUDO_HA, trabalho_vivo=True)
    if vivo is None:
        return 1
    check("com trabalho vivo, o motor gasta as 3 voltas inteiras",
          len(vivo["saida"]["rounds"]) == 3)
    check("com trabalho vivo, o vigia nao acende o sinal",
          vivo["saida"]["stopReason"] == "max-rounds")
    check("com trabalho vivo, nenhum Bloqueio do vigia e escrito",
          not any("vigia" in (b.get("what") or "") for b in vivo["saida"]["blockers"]))

    print("F9.13 — mudo alem do limite E sem trabalho vivo: o vigia derruba a execucao")
    travado = bancada(texto, tick_cmd, max_rounds=3, review_complete=False,
                      agora=AGORA, heartbeat=MUDO_HA, trabalho_vivo=False)
    if travado is None:
        return 1
    saida4 = travado["saida"]
    check("o motor parou antes de gastar as voltas", len(saida4["rounds"]) < 3)
    check("o motivo da parada e o vigia", saida4["stopReason"] == "vigia")
    vig = [b for b in saida4["blockers"] if "vigia" in (b.get("what") or "")]
    check("a derrubada vira Bloqueio, nao silencio", len(vig) == 1)
    check("o Bloqueio diz ha quantos minutos o registro esta mudo",
          bool(vig) and "há 20 min" in vig[0]["what"])
    check("o Bloqueio chama a coisa pelo nome: travamento, nao demora",
          bool(vig) and "travamento, não demora" in (vig[0].get("whyNeedsYou") or ""))
    check("ele nao declara obra construida ao ser derrubado", saida4["built"] is False)
    # A prova de que a derrubada e EFETIVA: nenhuma volta seguinte foi aberta. Vigia que
    # gravasse o motivo e deixasse o motor seguir seria relatorio, nao freio.
    check("nenhum decompositor foi disparado numa segunda volta",
          travado["agentes"].count("decompose") == 1)
    check("o vigia cortou agente: menos agentes que a rodada de registro fresco",
          len(travado["agentes"]) < len(fresco["agentes"]))

    # ── F9.14 ────────────────────────────────────────────────────────────────────
    # Interrupcao de verdade: a mesma missao do cenario do vigia, so que agora o
    # executor DEIXA ARQUIVO no disco e o papel de salvamento roda o comando REAL da
    # skill num repositorio git de bancada. O motor e derrubado na rodada 1 — o que se
    # afere e o que sobrou depois dele morrer: a onda fechada tem que estar no
    # HISTORICO, nao solta na arvore.
    print("F9.14 — motor interrompido no meio deixa a onda fechada no historico")
    ck_cmd = comando_de_checkpoint(texto)
    check("o comando que salva a onda esta escrito na skill", bool(ck_cmd))
    if not ck_cmd:
        return 1
    if not shutil.which("git"):
        check("git esta na maquina (sem ele o historico nao existe)", False)
        return 1

    interrompido = bancada_git(texto, tick_cmd, ck_cmd, max_rounds=3, review_complete=False,
                               agora=AGORA, heartbeat=MUDO_HA, trabalho_vivo=False)
    if interrompido is None:
        return 1

    saida5 = interrompido["saida"]
    check("o motor foi mesmo interrompido no meio",
          saida5["stopReason"] == "vigia" and len(saida5["rounds"]) < 3)
    check("a onda que fechou verde virou ponto de salvamento",
          saida5["rounds"][0].get("checkpoint") is True)
    check("o salvamento aconteceu na onda 1, uma vez so",
          [c["round"] for c in interrompido["checkpoints"]] == [1])

    check("o historico ganhou a onda, com o numero dela", "onda 1" in interrompido["log"])
    check("a obra dos executores esta NO HISTORICO",
          "F1.1.txt" in interrompido["versionados"] and "F1.2.txt" in interrompido["versionados"])
    check("o plano marcado tambem entrou no historico",
          any(v.endswith("%s.plan.json" % PLANO["id"]) for v in interrompido["versionados"]))
    check("nada da onda fechada ficou solto no disco",
          "F1.1.txt" not in interrompido["solto"] and "F1.2.txt" not in interrompido["solto"])
    # O que NAO fechou nao pode ser inventado no historico: F1.3 devolveu
    # `done: false` e o executor nem escreveu o arquivo dele.
    check("o que nao fechou nao aparece no historico",
          "F1.3.txt" not in interrompido["versionados"])

    # ── F9.15 ────────────────────────────────────────────────────────────────────
    # Mesma missao do cenario acima, no mesmo repositorio de bancada, com a MESMA
    # interrupcao. A unica coisa que muda e a COR da suite — entao toda diferenca de
    # desfecho abaixo e obra da recusa de salvar onda vermelha, e nao de outra trava.
    print("F9.15 — onda com suite vermelha nao vira ponto de salvamento")
    vermelha = bancada_git(texto, tick_cmd, ck_cmd, max_rounds=3, review_complete=False,
                           agora=AGORA, heartbeat=MUDO_HA, trabalho_vivo=False,
                           suite_verde=False,
                           suite_falhando=["test_plan_state.py", "test_andamento.py"])
    if vermelha is None:
        return 1

    saida6 = vermelha["saida"]
    check("a onda vermelha NAO foi marcada como ponto de salvamento",
          saida6["rounds"][0].get("checkpoint") is not True)
    # A prova de que a recusa e EFETIVA: o comando de salvamento nem chegou a rodar.
    # Marcar `checkpoint: false` e commitar assim mesmo seria o carimbo sem a recusa.
    check("nenhum salvamento foi disparado na onda vermelha", vermelha["checkpoints"] == [])
    check("o historico NAO ganhou a onda vermelha", "onda 1" not in vermelha["log"])
    check("a obra da onda vermelha ficou solta, fora do historico",
          "F1.1.txt" in vermelha["solto"] and "F1.1.txt" not in vermelha["versionados"])

    quebra = [b for b in saida6["blockers"] if "suíte quebrou" in (b.get("what") or "")]
    check("a onda vermelha vira Bloqueio, nao silencio", len(quebra) == 1)
    check("o Bloqueio diz QUAIS suites quebraram, pelo nome",
          bool(quebra) and "test_plan_state.py" in quebra[0]["what"]
          and "test_andamento.py" in quebra[0]["what"])
    check("o Bloqueio diz em que rodada quebrou",
          bool(quebra) and "rodada 1" in quebra[0]["what"])
    check("o Bloqueio manda consertar antes de seguir",
          bool(quebra) and "não vira ponto de salvamento" in (quebra[0].get("whyNeedsYou") or ""))

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK (%d checks)" % TOTAL[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
