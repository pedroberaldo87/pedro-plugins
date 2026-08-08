#!/usr/bin/env python3
"""Bancada do motor — ele RODA contra um plano de mentira, e se afere o que ficou.

Cinco coisas se medem aqui: o plano sai marcado (F9.10), o teto de gasto desliga o motor
(F9.12), o vigia derruba a execucao com o registro mudo alem do limite e sem trabalho
vivo (F9.13 + F9.24), a onda verde fica no historico quando o motor e interrompido no
meio (F9.14), a onda VERMELHA nao vira ponto de salvamento — nada e commitado e o
motor relata pelo nome qual suite quebrou (F9.15) —, e a concepcao errada vira aviso
"precisa de voce" SEM segurar a obra (S-9).

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
SKILL_MD = os.path.join(AQUI, "..", "..", "project-skills", "skills", "sprint", "SKILL.md")
PLAN_STATE = os.path.join(AQUI, "..", "..", "project-skills", "lib", "plan_state.py")

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

# ── a alegacao de impossivel (F9.18) ────────────────────────────────────────
# O que o executor diz quando desiste, e o que ele TINHA na mao quando disse. O caso real
# e este: o diagnostico dizia "exige navegador", e o agente tinha navegador.
ALEGACAO = "nao da: exige navegador contra producao"
FERRAMENTAS_A_MAO = ["navegador", "terminal", "leitura de arquivo"]

# ── o replay de cache (F9.35) ────────────────────────────────────────────────
# Retomar a missao REGRAVA veredito: o runtime devolve do cache o que ja tinha sido
# entregue. Duas coisas voltam — a mesma tarefa outra vez, com o mesmo `task_id`, e a
# devolucao do DECOMPOSITOR, que nao e passo nenhum e vem SEM `task_id`. As duas viram
# linha em `results`, e quem contava linha via cinco onde havia tres.
REPLAY_DECOMP_ID = "REPLAY-DECOMP"
REPLAY_DECOMP_RESULT = {"done": True, "summary": "replay da decomposicao vinda do cache",
                        "files_touched": [], "anchor": "fim",
                        "tasks": [{"id": "F1.1"}, {"id": "F1.2"}]}

# ── a concepcao errada (S-9) ─────────────────────────────────────────────────
# O gap que diz "a entrevista errou, o codigo esta certo". Ele tem DUAS promessas no
# motor, e o par abaixo so serve se a UNICA diferenca entre os dois for o `kind` — e o
# controle de `spec` existe pra provar que quem soltou a obra foi o kind, e nao o cenario.
GAP_CONCEPCAO = {"task_id": "F1.1", "kind": "concepcao", "severity": "P0",
                 "problem": "o documento aprovado promete cache local, e o que se descobriu "
                            "e que a origem nao versiona nada"}
GAP_SPEC = dict(GAP_CONCEPCAO, kind="spec")

# ── a obra contradiz o desenho aprovado (S-104) ──────────────────────────────
# A contradicao injetada: o esquema aprovado desenha uma coisa e a obra fez outra. Pelo
# eixo de constituicao ela nasce como gap de `constituicao` e SEGURA a obra; se o errado
# for o desenho, o mesmo texto entra como `concepcao` e vira aviso sem segurar nada.
GAP_DESENHO = {"task_id": "F1.1", "kind": "constituicao", "severity": "P0",
               "problem": "`.claude/docs/blueprint.md` (aprovado) desenha a leitura saindo "
                          "do cache local, e a obra le a origem a cada chamada"}
GAP_DESENHO_CONCEPCAO = dict(GAP_DESENHO, kind="concepcao")

HARNESS = r"""
const { execSync } = require('child_process')
const fs = require('fs')
const CFG = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))
const CORPO = fs.readFileSync(process.argv[3], 'utf8')

const PRELUDE = `
const DECOMP={}, TASK_RESULT={}, BUILD_REVIEW={}, RESERVA={}, REGUA={}, SUITE_RESULT={}, AUDITOR={}, DOC_TOUCH={};
const mk = n => (p => Object.assign({ __p: n }, p));
const decomposePrompt=mk('decompose'), execPrompt=mk('exec'), reviewBuildPrompt=mk('review'),
      runSuitePrompt=mk('suite'), checkpointPrompt=mk('checkpoint'), tickPlanPrompt=mk('tick'),
      docTouchPrompt=mk('docTouch'), colheitaPrompt=mk('colheita'),
      diagnoseStuckTaskPrompt=mk('diag'), reservaPrompt=mk('reserva'), confirmBuildPrompt=mk('confirm'),
      reguaPrompt=mk('regua'), auditorPrompt=mk('auditor');
`

const chamadas = []
const checkpoints = []
// O juiz que nao prova que leu (F9.16). `vereditos` registra, na ordem, se a chamada veio
// com o aviso de recusa — e com isso a bancada consegue perguntar se o papel foi RE-RODADO
// e se ele soube por que voltou. `CFG.reviewSemAncora` escolhe o cenario: 'primeira' (a
// primeira volta sem ancora, a segunda com) ou 'sempre' (juiz que nunca prova).
const vereditos = []
const auditorias = []
const docs = []
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
  for (const [k, v] of Object.entries({ '<plugin project-skills>': CFG.pluginSkills, '<raiz>': CFG.raiz,
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

// O papel que INVOCA SKILL, com efeito de verdade tambem — igual ao que roda comando.
// No caso honesto a re-projecao acontece: o arquivo da doc daquela onda e ESCRITO, e o
// papel devolve o caminho. Com CFG.docFalso o papel MENTE ter feito: devolve um caminho
// que ninguem escreveu. Os dois passam pela mesma peneira, que e o disco — e e por isso
// que a mentira volta como lista vazia, sem o motor precisar acreditar em ninguem.
function documenta(p) {
  const alegado = CFG.docFalso || ('.claude/docs/onda-' + p.round + '.md')
  if (!CFG.docFalso) {
    fs.mkdirSync(CFG.raiz + '/.claude/docs', { recursive: true })
    fs.writeFileSync(CFG.raiz + '/' + alegado, 'doc re-projetada na onda ' + p.round + '\n')
  }
  const confirmados = [alegado].filter(f => fs.existsSync(CFG.raiz + '/' + f))
  docs.push({ round: p.round, files: p.files, alegados: [alegado], docs: confirmados })
  return { docs: confirmados }
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
    // Os gaps vem do cenario. Com eles fixos em vazio (como era aqui), nenhuma regra do
    // motor que julga gap era exercitada — nem a que vira aviso, nem a que segura a obra.
    case 'review': {
      vereditos.push(!!p.recusado)
      const semAncora = CFG.reviewSemAncora === 'sempre' ||
                        (CFG.reviewSemAncora === 'primeira' && !p.recusado)
      const v = { complete: CFG.reviewComplete !== false, cohesive: true,
                  gaps: CFG.gaps || [],
                  missingTasks: CFG.reviewComplete === false ? ['F1.3'] : [],
                  lawMark: null }
      if (!semAncora) v.anchor = 'ultima linha do que julguei'
      return v
    }
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
    // O auditor da alegacao de impossivel (F9.18). O cenario escolhe o desfecho, e o que
    // ele RECEBEU fica registrado: sem isso a bancada nao consegue perguntar se a lente
    // invertida chegou com a lista do que havia a mao.
    case 'auditor':
      auditorias.push({ taskId: p.task && p.task.id, alegacao: p.alegacao,
                        ferramentas: p.ferramentas, tentativas: p.tentativas })
      return { derruba: CFG.auditorDerruba === true, motivo: CFG.auditorMotivo || '',
               naoTentou: CFG.auditorNaoTentou || [], anchor: 'ultima linha do que auditei' }
    case 'docTouch':  return documenta(p)
    case 'tick':      return tica(p)
    default:          return {}
  }
}

const corpo = CORPO.replace(/^export const meta = \{[\s\S]*?\n\}\n/m, '')
const motor = new Function('args', 'agent', 'phase', 'budget', 'parallel',
                           'return (async () => {' + PRELUDE + corpo + '})()')
motor(CFG.args, agent, phase, budget, parallel).then(saida => {
  fs.writeFileSync(CFG.out, JSON.stringify({ saida, chamadas, checkpoints, docs, agentes, vereditos, auditorias }, null, 2))
}).catch(e => { console.error('MOTOR ESTOUROU: ' + (e && e.stack || e)); process.exit(3) })
"""


def roda_motor(tmp, texto, plan_dir, tick_cmd, plan_path, token_budget=None,
               gasto_por_chamada=0, max_rounds=2, review_complete=True,
               agora=1, heartbeat=None, trabalho_vivo=False,
               checkpoint_cmd="", escreve_no_disco=False,
               suite_verde=True, suite_falhando=None, replay_cache=False, gaps=None,
               review_sem_ancora=None, alegacao_impossivel=None, auditor_derruba=False,
               auditor_motivo="", auditor_nao_tentou=None, doc_falso=None):
    """Executa o esqueleto do SKILL.md com os agentes de mentira. Devolve
    {saida, chamadas, agentes} ou levanta AssertionError com o motivo."""
    corpo = os.path.join(tmp, "motor.js")
    with open(corpo, "w", encoding="utf-8") as fh:
        fh.write(esqueleto(texto))
    harness = os.path.join(tmp, "harness.js")
    with open(harness, "w", encoding="utf-8") as fh:
        fh.write(HARNESS)
    out = os.path.join(tmp, "saida.json")
    tarefas = [{"id": i["id"], "desc": i["desc"], "requisito": i["requisito"],
                "pronto": i["pronto"], "files": ["%s.txt" % i["id"]],
                "parallelizable": True, "dependsOn": [], "done": False}
               for i in PLANO["phases"][0]["items"]]
    resultados = dict(RESULTADOS)
    if alegacao_impossivel:
        # F1.3 (o passo que nao sai) passa a voltar ALEGANDO impossivel, com a lista do
        # que havia a mao — que e o insumo da lente invertida do auditor.
        resultados["F1.3"] = dict(RESULTADOS["F1.3"], impossivel=alegacao_impossivel,
                                  ferramentas=FERRAMENTAS_A_MAO)
    if replay_cache:
        # O plantio: F1.1 e F1.2 voltam do cache uma segunda vez (mesmo `task_id`, mesmo
        # veredito), e a devolucao do decompositor entra na fila como uma linha a mais,
        # sem `task_id`. Nada disso e passo novo — e nenhuma das duas pode contar.
        tarefas = tarefas + [dict(t) for t in tarefas if t["id"] in ("F1.1", "F1.2")] + [
            {"id": REPLAY_DECOMP_ID, "desc": "linha da decomposicao repetida do cache",
             "requisito": "S-43", "pronto": "nao e passo", "files": [],
             "parallelizable": True, "dependsOn": [], "done": False}]
        resultados[REPLAY_DECOMP_ID] = REPLAY_DECOMP_RESULT
    cfg = {
        "tickCmd": tick_cmd,
        "checkpointCmd": checkpoint_cmd,
        "escreveNoDisco": escreve_no_disco,
        "docFalso": doc_falso,
        "suiteVerde": suite_verde,
        "suiteFalhando": suite_falhando or [],
        "pluginSkills": os.path.abspath(os.path.join(AQUI, "..", "..", "project-skills")),
        "raiz": tmp,
        "planoId": PLANO["id"],
        "out": out,
        "now": agora,
        "heartbeat": heartbeat,
        "trabalhoVivo": trabalho_vivo,
        "gastoPorChamada": gasto_por_chamada,
        "reviewComplete": review_complete,
        "gaps": gaps or [],
        "reviewSemAncora": review_sem_ancora,
        "auditorDerruba": auditor_derruba,
        "auditorMotivo": auditor_motivo,
        "auditorNaoTentou": auditor_nao_tentou or [],
        "results": resultados,
        "tasks": tarefas,
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
                          capture_output=True, text=True, cwd=tmp, stdin=subprocess.DEVNULL, start_new_session=True)
    if proc.returncode != 0:
        raise AssertionError("o motor nao rodou: %s" % (proc.stderr.strip() or proc.stdout.strip()))
    with open(out, encoding="utf-8") as fh:
        return json.load(fh)


def cria_plano(plan_dir):
    entrada = os.path.join(plan_dir, "_in.json")
    with open(entrada, "w", encoding="utf-8") as fh:
        json.dump(PLANO, fh)
    proc = subprocess.run([sys.executable, PLAN_STATE, "--dir", plan_dir, "init", "--file", entrada],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
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
                                  capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
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

    # ── F9.32 ────────────────────────────────────────────────────────────────────
    # O checkpoint gravava so CODIGO. Quem executasse a onda seguinte leria a doc do
    # repo de ANTES. Nos MESMOS dois cenarios acima (mesma missao, mesma interrupcao,
    # so a cor da suite muda) se afere agora o par commit+doc: a onda verde produz os
    # dois, nessa ordem; a vermelha nao produz nenhum.
    print("F9.32 — onda verde fecha com commit E doc; onda vermelha, com nenhum dos dois")
    check("a skill nomeia a skill que re-projeta a doc da onda",
          "docTouchPrompt" in texto and "project-doc:doc-touch" in texto)

    check("a onda verde re-projetou a doc, uma vez so",
          [d["round"] for d in interrompido["docs"]] == [1])
    # A doc pedida e a dos arquivos que ESTA onda tocou — doc do repo inteiro seria o
    # FULL, e doc de arquivo que ninguem tocou e gasto puro.
    tocados = sorted(interrompido["docs"][0]["files"]) if interrompido["docs"] else []
    check("a doc pedida e a dos arquivos que a onda tocou",
          tocados == ["a.py", "b.sh", "c.sh"])
    check("arquivo de quem estourou o teto nao entra (nao e obra fechada)",
          "d.py" not in tocados)
    # A ORDEM e o ponto: commit primeiro, doc depois. Doc antes do commit deixaria o
    # trabalho fora do historico se o touch estourasse.
    ag = interrompido["agentes"]
    check("o commit veio ANTES da doc, nao depois",
          "checkpoint" in ag and "docTouch" in ag
          and ag.index("checkpoint") < ag.index("docTouch"))

    check("a onda vermelha nao re-projetou doc nenhuma", vermelha["docs"] == [])
    check("na onda vermelha nao houve nem commit nem doc",
          vermelha["checkpoints"] == [] and "docTouch" not in vermelha["agentes"])

    # ── S-112 ────────────────────────────────────────────────────────────────────
    # O papel que INVOCA SKILL nao devolvia nada: papel mudo, papel que invocou skill
    # quebrada e papel que MENTE ter feito chegavam iguais ao motor. Agora ele devolve os
    # caminhos que tocou, conferidos no disco — e a onda registra o que ele CONFIRMOU.
    print("S-112 — o papel que invoca skill devolve os caminhos que tocou")
    check("a doc devolvida pelo papel e a que o disco confirma",
          bool(interrompido["docs"]) and interrompido["docs"][0]["docs"] ==
          [".claude/docs/onda-1.md"])
    check("a onda registra o que o papel confirmou, nao a lista que ele recebeu",
          saida5["rounds"][0].get("doc") == [".claude/docs/onda-1.md"])
    check("papel que confirmou a doc nao vira Bloqueio",
          not [b for b in saida5["blockers"] if "doc da rodada" in (b.get("what") or "")])

    # O papel que MENTE ter feito: mesma missao, mesma onda verde — a UNICA coisa que muda
    # e o papel devolver um caminho que ninguem escreveu. O disco nao confirma, a lista
    # volta vazia, e lista vazia e Bloqueio.
    print("S-112 — papel que devolve caminho que o disco nao confirma vira Bloqueio")
    mentiu = bancada_git(texto, tick_cmd, ck_cmd, max_rounds=1,
                         doc_falso=".claude/docs/nunca-escrita.md")
    if mentiu is None:
        return 1
    saida_m = mentiu["saida"]
    check("o papel foi chamado e alegou ter re-projetado uma doc",
          bool(mentiu["docs"]) and mentiu["docs"][0]["alegados"] ==
          [".claude/docs/nunca-escrita.md"])
    check("o caminho que o disco nao confirma nao entra na lista",
          mentiu["docs"][0]["docs"] == [])
    doc_bloq = [b for b in saida_m["blockers"] if "doc da rodada" in (b.get("what") or "")]
    check("lista vazia vira Bloqueio, e nao silencio", len(doc_bloq) == 1)
    check("o Bloqueio diz em que rodada a doc nao saiu",
          bool(doc_bloq) and "rodada 1" in doc_bloq[0]["what"])
    check("o Bloqueio diz por que isso custa caro na onda seguinte",
          bool(doc_bloq) and "mapa vencido" in (doc_bloq[0].get("whyNeedsYou") or ""))
    # A mentira NAO derruba a onda: o commit ja esta feito, mesma regra do tique.
    check("a mentira do papel nao desfaz o ponto de salvamento da onda",
          saida_m["rounds"][0].get("checkpoint") is True and mentiu["checkpoints"] != [])

    # ── F9.35 ────────────────────────────────────────────────────────────────────
    # A MESMA missao da primeira rodada, com UMA coisa plantada: o replay do cache.
    # F1.1 e F1.2 voltam uma segunda vez com o mesmo veredito, e a devolucao do
    # decompositor entra como mais uma linha de resultado, sem `task_id`. A contagem
    # tem que enxergar TAREFA, nao linha.
    print("F9.35 — com replay de cache plantado, a contagem devolve tarefas distintas")
    replay = bancada(texto, tick_cmd, max_rounds=1, replay_cache=True)
    if replay is None:
        return 1
    saida7 = replay["saida"]
    linhas = saida7["rounds"][0]["results"] if saida7.get("rounds") else []
    feitas_em_linha = [x for x in linhas if x.get("done")]
    # O plantio so vale se o replay realmente aconteceu: sem esta afericao, a contagem
    # certa poderia ser a de um cenario que nunca teve duplicata nenhuma.
    check("o replay foi mesmo plantado: 5 linhas de resultado fechado para 2 tarefas",
          len(feitas_em_linha) == 5)
    check("a linha da decomposicao chegou mesmo em results, sem task_id",
          any(not x.get("task_id") for x in feitas_em_linha))

    prog = saida7.get("progresso") or {}
    check("a contagem devolve o numero de tarefas distintas, nao de linhas",
          prog.get("feitos") == 2)
    check("a contagem nomeia quais passos fecharam, cada um uma vez",
          sorted(prog.get("passos") or []) == ["F1.1", "F1.2"])
    check("a linha da decomposicao nao entrou na contagem",
          REPLAY_DECOMP_ID not in (prog.get("passos") or []))
    # A telemetria conta a mesma coisa pela mesma regra: 3 tarefas distintas com
    # resultado (F1.1, F1.2, F1.3), e nao as 6 linhas que o replay produziu.
    check("a telemetria da onda conta tarefa distinta, nao linha",
          saida7["telemetry"][0]["tasks"] == 3)
    # E o efeito no disco: o passo repetido nao e marcado duas vezes.
    check("nenhum passo foi marcado duas vezes",
          sorted(c["taskId"] for c in replay["chamadas"]) == ["F1.1", "F1.2"])

    # ── S-9 ──────────────────────────────────────────────────────────────────────
    # A concepcao errada: a execucao descobriu algo que contradiz documento ja aprovado.
    # O motor promete duas coisas, e nenhuma era exercitada — o gap vira aviso "precisa
    # de voce" no relatorio, e NAO segura a obra (segurar empurraria o executor a
    # "consertar" codigo que esta certo).
    print("S-9 — gap de spec com o mesmo texto SEGURA a obra (o controle)")
    trava = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_SPEC])
    if trava is None:
        return 1
    check("com gap de spec, o motor nao declara a obra construida",
          trava["saida"]["built"] is False)
    check("com gap de spec, o executor recebe tarefa numa segunda volta",
          trava["agentes"].count("decompose") == 2)

    print("S-9 — o gap de concepcao vira aviso e NAO segura a obra")
    # Mesmo gap, mesmo texto, mesmo cenario: so o `kind` muda.
    conc = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_CONCEPCAO])
    if conc is None:
        return 1
    saida8 = conc["saida"]
    aviso = [b for b in saida8["blockers"] if "a concepção está errada" in (b.get("what") or "")]
    check("o gap de concepcao vira Bloqueio no relatorio", len(aviso) == 1)
    check("o Bloqueio repete o que a execucao contradisse, com as palavras do revisor",
          bool(aviso) and GAP_CONCEPCAO["problem"] in aviso[0]["what"])
    check("o Bloqueio sai como 'precisa de voce' e propoe reabrir a etapa",
          bool(aviso) and "correcao-pendente" in (aviso[0].get("whyNeedsYou") or "")
          and "reabra a etapa" in (aviso[0].get("whyNeedsYou") or ""))
    check("ele entra na lista de impedidos, que e a que pede acao do dono",
          any("a concepção está errada" in (b.get("what") or "")
              for b in saida8.get("impedidos") or []))
    check("o motor declara a obra construida mesmo assim", saida8["built"] is True)
    check("a onda nao foi segurada: uma volta so", len(saida8["rounds"]) == 1)
    check("nenhum executor recebeu tarefa nova por causa dele",
          conc["agentes"].count("decompose") == 1
          and conc["agentes"].count("exec") == trava["agentes"].count("exec") / 2)

    # ── S-104 ────────────────────────────────────────────────────────────────────
    # A obra contradiz o desenho aprovado. Injetada a contradicao, o gap tem que NASCER:
    # pelo eixo de constituicao ele segura a obra e devolve tarefa; e quando quem errou
    # foi o desenho, o mesmo texto vira aviso que nomeia o documento contradito.
    print("S-104 — a obra que contradiz o desenho aprovado segura a obra")
    desenho = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_DESENHO])
    if desenho is None:
        return 1
    check("com a obra contradizendo o desenho, o motor nao declara construida",
          desenho["saida"]["built"] is False)
    check("o executor recebe tarefa numa segunda volta",
          desenho["agentes"].count("decompose") == 2)

    print("S-104 — quando quem errou foi o desenho, o aviso nomeia o documento")
    desenho_erra = bancada(texto, tick_cmd, max_rounds=2, gaps=[GAP_DESENHO_CONCEPCAO])
    if desenho_erra is None:
        return 1
    aviso_des = [b for b in desenho_erra["saida"]["blockers"]
                 if "a concepção está errada" in (b.get("what") or "")]
    check("o aviso nomeia o documento contradito",
          bool(aviso_des) and ".claude/docs/blueprint.md" in aviso_des[0]["what"])
    check("e ele nao segura a obra", desenho_erra["saida"]["built"] is True)

    # ── F9.16 · S-24 ─────────────────────────────────────────────────────────────
    # O juiz prova que leu a coisa inteira: veredito sem a ancora do fim e RECUSADO e o
    # papel roda de novo. Dois cenarios, com o mesmo controle: com ancora (o caminho
    # normal, uma chamada so) e sem ancora (recusa + re-rodada).
    print("F9.16 — veredito COM a ancora passa de primeira (o controle)")
    com_ancora = bancada(texto, tick_cmd, max_rounds=1)
    if com_ancora is None:
        return 1
    check("com a ancora, o revisor e chamado uma vez so",
          com_ancora["agentes"].count("review") == 1)
    check("com a ancora, nenhuma chamada veio marcada como recusa",
          com_ancora["vereditos"] == [False])
    check("com a ancora, o motor fecha a obra", com_ancora["saida"]["built"] is True)

    print("F9.16 — veredito SEM a ancora e recusado e o papel roda de novo")
    sem_ancora = bancada(texto, tick_cmd, max_rounds=1, review_sem_ancora="primeira")
    if sem_ancora is None:
        return 1
    check("sem a ancora, o revisor da MESMA rodada e chamado duas vezes",
          sem_ancora["agentes"].count("review") == 2)
    check("a segunda chamada diz ao juiz por que a primeira foi recusada",
          sem_ancora["vereditos"] == [False, True])
    check("o veredito que voltou com a ancora e o que vale",
          sem_ancora["saida"]["built"] is True)

    print("F9.16 — juiz que nunca prova que leu nao aprova nada")
    nunca = bancada(texto, tick_cmd, max_rounds=1, review_sem_ancora="sempre")
    if nunca is None:
        return 1
    check("o papel foi re-rodado uma vez e parou por ai (nao loopa)",
          nunca["agentes"].count("review") == 2)
    check("duas recusas seguidas nao viram aprovacao",
          nunca["saida"]["built"] is False)
    recusa = [b for b in nunca["saida"]["blockers"]
              if "ncora do fim" in (b.get("what") or "")]
    check("o relatorio diz que o veredito voltou sem a ancora", len(recusa) == 1)
    check("a obra da rodada e tratada como NAO verificada",
          bool(recusa) and "sem revisão" in (recusa[0].get("whyNeedsYou") or "").lower())

    # ── F9.18 · S-26 ─────────────────────────────────────────────────────────────
    # Executor que declara impossivel nao encerra nada sozinho. A alegacao repetida na
    # mesma tarefa convoca o auditor, e os DOIS desfechos sao do script: derruba devolve
    # a tarefa ao loop; confirma encerra como impedimento real, com o motivo escrito.
    # O controle vem primeiro: alegacao de UMA rodada so nao convoca ninguem.
    print("F9.18 — alegacao que nao se repetiu nao convoca auditor (o controle)")
    uma_vez = bancada(texto, tick_cmd, max_rounds=1, alegacao_impossivel=ALEGACAO)
    if uma_vez is None:
        return 1
    check("com uma rodada so, nenhum auditor foi convocado",
          "auditor" not in uma_vez["agentes"])
    check("e ninguem encerrou a tarefa como impedimento",
          not [b for b in uma_vez["saida"]["blockers"] if b.get("kind") == "impedimento"])

    print("F9.18 — auditor que DERRUBA a alegacao devolve a tarefa ao loop")
    derruba = bancada(texto, tick_cmd, max_rounds=2, review_complete=False,
                      alegacao_impossivel=ALEGACAO, auditor_derruba=True,
                      auditor_motivo="a ferramenta estava na mao; a causa e outra",
                      auditor_nao_tentou=["navegador"])
    if derruba is None:
        return 1
    saida9 = derruba["saida"]
    check("a alegacao repetida convocou o auditor, uma vez",
          derruba["agentes"].count("auditor") == 1)
    auditoria = derruba["auditorias"][0] if derruba["auditorias"] else {}
    check("o auditor recebeu a alegacao do executor", auditoria.get("alegacao") == ALEGACAO)
    check("o auditor recebeu a lista do que havia a mao",
          auditoria.get("ferramentas") == FERRAMENTAS_A_MAO)
    devolvidas = saida9["rounds"][-1].get("devolvidas") or []
    check("a tarefa derrubada volta pro loop, com o que o auditor apontou",
          [d["taskId"] for d in devolvidas] == ["F1.3"]
          and "a causa e outra" in devolvidas[0]["motivo"])
    check("o auditor que derruba nao encerra nada como impedimento",
          not [b for b in saida9["blockers"] if b.get("kind") == "impedimento"])
    check("e o dono nao e chamado por causa dela",
          not [b for b in (saida9.get("impedidos") or []) if b.get("taskId") == "F1.3"])

    print("F9.18 — auditor que CONFIRMA encerra como impedimento real, com o motivo")
    confirma = bancada(texto, tick_cmd, max_rounds=2, review_complete=False,
                       alegacao_impossivel=ALEGACAO, auditor_derruba=False,
                       auditor_motivo="publicar depende do aval do dono, e a tela so existe publicada")
    if confirma is None:
        return 1
    saida10 = confirma["saida"]
    check("o mesmo cenario convocou o auditor, uma vez",
          confirma["agentes"].count("auditor") == 1)
    impedimento = [b for b in saida10["blockers"] if b.get("kind") == "impedimento"]
    check("a tarefa e encerrada como impedimento real", len(impedimento) == 1)
    check("o impedimento nomeia a tarefa e traz o motivo ESCRITO pelo auditor",
          bool(impedimento) and impedimento[0]["taskId"] == "F1.3"
          and "publicar depende do aval do dono" in impedimento[0]["what"])
    check("o impedimento sai como 'precisa de voce', e nao como falta de tempo",
          any(b.get("taskId") == "F1.3" for b in saida10.get("impedidos") or []))
    check("a tarefa confirmada NAO volta pro loop",
          not (saida10["rounds"][-1].get("devolvidas") or []))
    check("e ela nao sai marcada no plano",
          "F1.3" not in [c["taskId"] for c in confirma["chamadas"]])

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
