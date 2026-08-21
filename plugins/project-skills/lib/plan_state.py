#!/usr/bin/env python3
"""plan_state.py — o plano de implementação como ARQUIVO, não como conversa.

Por que existe
--------------
Antes disto o plano só vivia no transcript. Todo consumidor (o /handoff, o
/visual, a próxima sessão) o RE-DERIVAVA por LLM — e re-derivação por LLM é
lossy: encurta, renomeia fase, e chuta se já foi executado. O caso concreto que
motivou o módulo está em plugins/handoff/lib/extract_ata.py:168,186 —  # acopla-ok: narrativa histórica do defeito que originou o módulo; nada aqui executa o arquivo citado
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
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time

# CANAIS DE TEXTO EM UTF-8, SEMPRE. No Windows eles nascem na codificação do sistema
# (cp1252) e o payload do evento — que chega por stdin — é UTF-8: sem isto, todo
# acento do pedido do usuário chega corrompido ao gate, e emoji derruba a escrita.
for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bash_posix import bash_posix  # noqa: E402
from regua_pronto import criterio_cortado, erros_de_pronto  # noqa: E402
from regua_texto import BULLET_MAX  # noqa: E402
from regua_texto import erros_de_estilo as _erros_de_estilo  # noqa: E402

PHASE_RE = re.compile(r"^F\d+$")
ITEM_RE = re.compile(r"^F\d+\.\d+$")
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")

# A régua de estilo (quality-goals.md, regime "informação rápida"): o plano é lido
# com a mesma pressa que a página, e até 2026-08-03 só o TAMANHO era cobrado aqui —
# um passo com duas frases entrava. As quatro checagens moram em
# `_shared/regua_texto.py`; o que este gerador faz é DECLARAR qual perfil usa. O
# perfil "plano" deixa fora da régua a árvore que o próprio programa desenha.
PERFIL = "plano"

# O fim de turno é o SÉTIMO emissor do canal de texto, e ele não sai numa página:
# sai no terminal, pelo `stop-plan-status.sh`. Sob o perfil do plano ele passava
# livre — a régua da página não cobra markdown nem cabeçalho, e foi assim que `**`
# chegou literal na tela em 2026-08-03. O canal manda na forma, então o perfil é
# outro: sem markdown, e todo cabeçalho abre com emoji.
PERFIL_BRIEF = "hook"

# A linha didática é o produto do arquivo: é ela que aparece na árvore. Um
# parágrafo ali destrói a leitura de mapa, então o limite é do schema. É o MESMO
# número da régua — dois números para o mesmo teto divergem no primeiro ajuste.
DESC_MAX = BULLET_MAX
EVIDENCE_MIN = 8

# Tique de RETOMADA (F18.3 · R-28): o passo que a largada achou feito no disco e
# ninguém marcou só fecha com as DUAS provas do rito que a mão fez em F16.1, F15.1,
# F23.5 e F17.10 — o veredito de quem revisou ("revisor … APROVOU") e o sha do
# commit. Sem elas, "já estava pronto" é palpite sobre trabalho de outra sessão, que
# é exatamente o que a retomada não pode carimbar.
REVISOR_RE = re.compile(r"revis", re.I)
VEREDITO_RE = re.compile(r"aprov", re.I)
SHA_RE = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])")

STATUSES = ("todo", "doing", "blocked", "done")
# O status do TOPO tem vocabulário PRÓPRIO, e é o que `close`/`reopen` gravam. Sem
# esta lista o init aceitava qualquer palavra ('open', por exemplo) e o plano sumia
# de `cmd_open`, que filtra por 'active' — invisível para a skill e para o hook.
PLAN_STATUSES = ("active", "done", "abandoned")


class PlanError(Exception):
    pass


def erros_de_estilo(v, onde):
    """A régua no perfil DESTE gerador — a definição mora em `regua_texto.py`.

    Fora do alcance de propósito: `evidence` (é prova, literal por obrigação) e
    `grupo`/`requisito`, que são rótulo e não redação.
    """
    return _erros_de_estilo(v, onde, PERFIL)


def erros_do_brief(linhas, onde):
    """A régua do CANAL do fim de turno — terminal, não HTML.

    Separada de `erros_de_estilo` porque o artefato é outro, não porque é mais
    frouxa: o mesmo texto que passa na página reprova aqui se traz markdown ou se
    o cabeçalho não abre com emoji.
    """
    return _erros_de_estilo(linhas, onde, PERFIL_BRIEF)


# ── localização ────────────────────────────────────────────────────────────

def resolve_dir(cwd=None):
    """Diretório dos planos, pela MESMA cascata do /visual (git root → marcador
    de projeto → ~/Desktop). Delega ao shell script pra não haver duas
    implementações da cascata que possam divergir."""
    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "resolve-dir.sh")
    if not os.path.exists(script):
        raise PlanError("resolve-dir.sh não encontrado em %s — passe --dir" % script)
    target = _roda_resolvedor(script, cwd or os.getcwd(), "plans")
    if not target:
        raise PlanError("resolve-dir.sh não devolveu caminho — passe --dir")
    return target



def _roda_resolvedor(script, *args):
    """Roda um resolvedor de shell e devolve o caminho — ou "" se não der.

    Duas defesas, e as duas nasceram do mesmo dia no Windows:

    - o bash vem de `bash_posix()`, nunca do PATH. O `bash` do PATH no Windows é o
      do WSL, e sem distro instalada ele responde uma reclamação em UTF-16 no
      stdout — com código 0. Sem esta defesa a reclamação virava "o caminho".
    - o que volta só é aceito se EXISTIR no disco. É a defesa que vale mesmo com o
      interpretador certo: resolvedor é para devolver caminho, e o que não aponta
      para nada não é caminho, é ruído com formato de resposta.
    """
    bash = bash_posix()
    if not bash:
        return ""
    try:
        out = subprocess.run([bash, script] + list(args),
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", stdin=subprocess.DEVNULL,
                             start_new_session=True)
    except OSError:
        return ""
    achado = (out.stdout or "").strip()
    return achado if achado and os.path.exists(achado) else ""


def visual_page_path():
    """Quem MONTA a página é o plugin `visual`; aqui só sai a árvore desenhada.

    O molde de HTML não é aberto daqui: este programa devolve o HTML da árvore e
    o `visual_page.py` a embute pelo bloco `raw_html`, que já existe no spec dele.
    O programa vizinho é achado pelo NOME — nunca por caminho relativo, que o cache
    do harness quebra. Ausente na máquina: devolve "" e quem chama recusa só o
    comando de página."""
    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "resolve-plugin.sh")
    achado = _roda_resolvedor(script, "visual", "lib/visual_page.py")
    if achado:
        return achado
    # Rodando do repositório, sem o harness: o plugin é pasta irmã.
    irmao = os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "visual", "lib", "visual_page.py"))
    return irmao if os.path.exists(irmao) else ""


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
    # Tarefa sem `status` some das contagens: não é feita, não é pendente, e a soma
    # por fora erra (medido em 2026-08-09 — duas tarefas gravadas sem o campo fizeram
    # 218 virar 217). Toda escrita passa por aqui, então a normalização mora aqui: o
    # campo ausente vira "todo" ANTES de ir ao disco, não importa quem esqueceu.
    for ph in plan.get("phases", []) or []:
        if isinstance(ph, dict):
            for it in ph.get("items", []) or []:
                if isinstance(it, dict):
                    it.setdefault("status", "todo")
    path = plan_path(directory, plan["id"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    # Toda escrita de plano é uma sessão dizendo "estou NESTE". A marca fica aqui, e
    # não em cada comando, porque `tick`, `state`, `init` e `close` passam todos por
    # este ponto — pendurar em cada um deixaria o próximo comando novo de fora.
    _marca_sessao(directory, plan["id"])
    return path


# ── schema ─────────────────────────────────────────────────────────────────

def _erros_dos_limites(plan):
    """A seção `limites` — o que a rodada ACEITOU deixar de fora, e por quê (S-77).

    Limite aceito que só vive na conversa some no /clear, e a sessão seguinte
    re-reporta o que já tinha sido decidido. Por isso ele é linha de arquivo. E o
    motivo é obrigatório: limite sem motivo é indistinguível de esquecimento —
    quem lê depois não sabe se pode reabrir.

    Formato, no topo do plano, ao lado de `phases`:
        "limites": [{"limite": "o que fica de fora", "motivo": "por que fica"}]
    """
    lim = plan.get("limites")
    if lim is None:
        return []
    if not isinstance(lim, list):
        return ["limites: precisa ser uma lista de {limite, motivo}, ou ausente"]
    errs = []
    for i, item in enumerate(lim):
        tag = "limites[%d]" % i
        if not isinstance(item, dict):
            errs.append("%s: precisa ser um objeto {limite, motivo}" % tag)
            continue
        for campo in ("limite", "motivo"):
            v = str(item.get(campo, "")).strip()
            if not v:
                errs.append("%s %s: obrigatório — limite aceito sem motivo escrito\n"
                            "     é indistinguível de esquecimento." % (tag, campo))
            else:
                errs.extend(erros_de_estilo(v, "%s %s" % (tag, campo)))
    return errs


# A mesma frase no aviso do close e no cartão da página: a decisão é uma só, e
# duas redações dela envelheceriam separadas.
FRENTE_DECIDA = "decida mesclar, manter ou descartar — fechar o plano não fecha a branch."


def _erros_da_frente(plan):
    """A seção `frente` — a branch e a worktree em que este plano é trabalhado (R-20).

    É ANINHADA e os dois campos são obrigatórios juntos: a decisão do dono é que
    haja uma checagem só no fechamento, e meio-gravar (branch sem worktree, ou o
    contrário) daria uma frente que o fechamento não sabe encerrar. Projeto que
    trabalha na própria árvore grava a raiz do repositório como worktree.

    Formato, no topo do plano, ao lado de `phases`:
        "frente": {"branch": "feature/<slug>", "worktree": "<caminho>"}
    """
    fr = plan.get("frente")
    if fr is None:
        return []
    if not isinstance(fr, dict):
        return ["frente: precisa ser um objeto {branch, worktree}, ou ausente"]
    errs = []
    for campo in ("branch", "worktree"):
        if not str(fr.get(campo, "")).strip():
            errs.append("frente %s: obrigatório — a frente se grava inteira ou não se\n"
                        "     grava: só com a branch E a worktree o fechamento tem o que\n"
                        "     encerrar." % campo)
    return errs


def _funde_limites(stored, incoming):
    """União da seção `limites` por texto do limite. Devolve (lista, mantidos).

    Mesma regra dos requisitos: o init que traz um pedaço não pode apagar o resto —
    o limite aceito na rodada 1 continua aceito na rodada 3. Declarar a lista VAZIA
    apaga de propósito.
    """
    novos = [x for x in (incoming.get("limites") or []) if isinstance(x, dict)]
    if not novos:
        return None, []
    vindos = {str(x.get("limite", "")).strip() for x in novos}
    mantidos = [x for x in (stored.get("limites") or [])
                if isinstance(x, dict) and str(x.get("limite", "")).strip() not in vindos]
    return novos + mantidos, [str(x.get("limite", "")).strip() for x in mantidos]


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
    pst = plan.get("status")
    if pst is not None and pst not in PLAN_STATUSES:
        errs.append("status '%s': use %s (o do PLANO, não o do passo)"
                    % (pst, "|".join(PLAN_STATUSES)))
    errs.extend(_erros_dos_limites(plan))
    errs.extend(_erros_da_frente(plan))
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
            # As QUATRO checagens, não só o tamanho: `desc`, `pronto` e `pendencia`
            # são redação lida com pressa, e o teto sozinho deixava passar o parágrafo
            # de duas frases que cabe em 140 caracteres.
            for campo in ("desc", "pronto", "pendencia", "espera_dono"):
                v = str(it.get(campo, "")).strip()
                if v:
                    errs.extend(erros_de_estilo(v, "%s %s" % (itag, campo)))
            # S-14: o critério de aceite não pode fechar com o valor DENTRO do
            # entregável sem dizer de onde ele vem — assim escrever à mão cumpre.
            # A régua mora em `regua_pronto.py`; aqui ela RECUSA A GRAVAÇÃO, em
            # vez de só acusar num plano que já está no disco.
            errs.extend(erros_de_pronto(it.get("pronto"), "%s pronto" % itag))
            # S-94: o critério que chegou CORTADO no meio. Fica fora do desconto
            # de `_erros_herdados` de propósito — pela metade ele não diz o que
            # provar, e o que já está no disco tem que ser recusado de novo.
            errs.extend(criterio_cortado(it.get("pronto"), "%s pronto" % itag))
            # ESPERA DO DONO (S-23). O campo não é bandeira: é a frase do ATO que
            # só o dono pode fazer (aprovar, publicar, liberar acesso). `true`
            # solto diria que espera sem dizer o quê, e aí quem lê o relatório não
            # sabe o que fazer para destravar.
            esp = it.get("espera_dono")
            if esp is not None and not (isinstance(esp, str) and esp.strip()):
                errs.append(
                    "%s espera_dono: escreva O ATO que só você pode fazer\n"
                    "     (ex: \"publicar o site\"), ou tire o campo. Bandeira sem\n"
                    "     o ato diz que espera sem dizer o quê." % itag)
            for campo, teto in (("grupo", 40), ("requisito", 40)):
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
    # R-11: plano 'done' some da listagem de planos abertos. Gravado com passo que
    # ninguém provou, ele leva o passo junto para fora da vista — e some sem que
    # nada tenha sido feito. Quem encerra é `close`, que só escreve 'done' quando
    # todos os passos estão marcados; à mão, é recusado com os ids na cara.
    if pst == "done":
        pendentes = [str(it.get("id", "?"))
                     for ph in phases if isinstance(ph, dict)
                     for it in ph.get("items") or []
                     if isinstance(it, dict) and it.get("status") != "done"]
        if pendentes:
            errs.append(
                "status 'done' com %d passo(s) sem prova: %s.\n"
                "     Encerrar é `close`, e ele só escreve 'done' quando todo passo\n"
                "     está marcado com `tick <id> --evidencia`. Plano 'done' sai da\n"
                "     listagem — do jeito que está, ele levaria esses passos junto."
                % (len(pendentes), ", ".join(pendentes[:8])))
    return errs


def validate(plan, exigir=None, reqs=None, isentos=None):
    errs = erros_do_plano(plan, exigir)
    # `isentos` são as mensagens de REDAÇÃO de texto que esta gravação não muda —
    # ver `_erros_herdados`. Sai da lista o defeito que já estava no disco; o que a
    # gravação escreve de novo continua recusando.
    if isentos:
        herdados = set(isentos)
        errs = [e for e in errs if e not in herdados]
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
    if stored is not None and _requisitos_do_plano(incoming):
        # o merge funde por id, então o que vai FICAR gravado é a união — validar
        # contra o pedaço reprovaria a tarefa que cita requisito só do arquivo.
        fonte = dict(incoming, requisitos=_funde_requisitos(stored, incoming)[0])
    validate(incoming, exigir=novos,
             reqs=_requisitos_do_projeto(directory, fonte),
             isentos=_erros_herdados(stored, incoming))

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
            for campo in ("requisito", "grupo", "pronto", "pendencia", "espera_dono",
                          "decidido", "detail"):
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

    fundidos, mantidos = _funde_requisitos(stored, incoming)
    if fundidos is not None:
        if mantidos:
            notes.append("%d requisito(s) do arquivo não vieram neste init e foram "
                         "MANTIDOS: %s" % (len(mantidos), ", ".join(mantidos)))
        incoming["requisitos"] = fundidos

    limites, mantidos_lim = _funde_limites(stored, incoming)
    if limites is not None:
        if mantidos_lim:
            notes.append("%d limite(s) aceito(s) do arquivo não vieram neste init e "
                         "foram MANTIDOS: %s" % (len(mantidos_lim), ", ".join(mantidos_lim)))
        incoming["limites"] = limites

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


def _erros_de_redacao_do_no(plan, node_id):
    """Só os erros de REDAÇÃO da tarefa — o teto de 140, a frase dupla, o conectivo.

    Recalculados com o mesmo prefixo de posição de `erros_do_plano`, pra o `cmd_tick`
    poder separá-los do resto por igualdade de string.
    """
    for pi, ph in enumerate(plan.get("phases", [])):
        for ii, it in enumerate(ph.get("items", [])):
            if it.get("id") != node_id:
                continue
            itag = "fase[%d] passo[%d]" % (pi, ii)
            out = []
            for campo in ("desc", "pronto", "pendencia", "espera_dono"):
                v = str(it.get(campo, "")).strip()
                if v:
                    out.extend(erros_de_estilo(v, "%s %s" % (itag, campo)))
            # O `pronto` de bancada é defeito de REDAÇÃO do critério: recusa gravar,
            # mas não pode congelar o tique de uma tarefa antiga já executada.
            out.extend(erros_de_pronto(it.get("pronto"), "%s pronto" % itag))
            out.extend(criterio_cortado(it.get("pronto"), "%s pronto" % itag))
            return out
    return []


def _erros_herdados(stored, incoming):
    """Os erros de REDAÇÃO do texto que esta gravação NÃO altera.

    O plano no disco é anterior à régua, e recusar o arquivo inteiro por causa de
    texto que já estava lá obriga a mandar o plano em pedaços — foi assim que o
    `pronto` de duas tarefas chegou cortado em 400 caracteres ao disco. Campo cujo
    texto vem IGUAL ao gravado não é reavaliado; campo que a gravação reescreve (ou
    que nasce agora) continua sendo cobrado pela régua inteira.

    As mensagens saem com o MESMO prefixo de posição de `erros_do_plano`, pra
    `validate` poder descontá-las por igualdade de string.
    """
    if not isinstance(stored, dict):
        return []
    velhos = {}
    for ph in stored.get("phases", []) or []:
        if isinstance(ph, dict):
            for it in ph.get("items", []) or []:
                if isinstance(it, dict):
                    velhos[it.get("id")] = it
    out = []
    for pi, ph in enumerate(incoming.get("phases", []) or []):
        if not isinstance(ph, dict):
            continue
        for ii, it in enumerate(ph.get("items", []) or []):
            if not isinstance(it, dict):
                continue
            old = velhos.get(it.get("id"))
            if old is None:
                continue
            itag = "fase[%d] passo[%d]" % (pi, ii)
            for campo in ("desc", "pronto", "pendencia", "espera_dono"):
                v = str(it.get(campo, "") or "").strip()
                if not v or v != str(old.get(campo, "") or "").strip():
                    continue
                out.extend(erros_de_estilo(v, "%s %s" % (itag, campo)))
                if campo == "pronto":
                    out.extend(erros_de_pronto(v, "%s pronto" % itag))
    return out


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


def _funde_requisitos(stored, incoming):
    """União por id do bloco `requisitos`. Devolve (lista, ids mantidos) ou (None, []).

    A preservação de chave AUSENTE só alcança o init que OMITE o bloco inteiro; o init
    que traz um pedaço dele (a fase da vez com os 4 requisitos que ela cita) trocava a
    lista inteira do arquivo pelo pedaço, e os outros 55 sumiam em silêncio. Aqui vale
    a mesma regra dos nós: o que veio no init vence, o que só existe no arquivo FICA.
    Declarar a lista VAZIA continua apagando de propósito, como na `pendencia`.
    """
    novos = [r for r in (incoming.get("requisitos") or []) if isinstance(r, dict)]
    if not novos:
        return None, []
    vindos = {str(r.get("id", "")).strip() for r in novos}
    mantidos = [r for r in (stored.get("requisitos") or [])
                if isinstance(r, dict) and str(r.get("id", "")).strip() not in vindos]
    return novos + mantidos, [str(r.get("id", "")).strip() for r in mantidos]


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
                                    "ancora": r.get("ancora"), "jornada": r.get("jornada"),
                                    "peca": r.get("peca"), "passo": r.get("passo"),
                                    "epico": r.get("epico"), "decisao": r.get("decisao")}
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
    from casa_da_doc import NOVA
    for nome in ("PRD.md", "REQUISITOS.md"):
        p = os.path.join(raiz, *NOVA, nome)
        if os.path.exists(p):
            return cobertura.le_requisitos(p)
    return {}


def _doc_cands(raiz, nome):
    """Os candidatos de um documento nas duas casas da doc, casa antiga primeiro
    (a ordem que a cascata sempre teve). As casas saem do resolvedor único
    (`casa_da_doc`, contrato em _shared/casa-da-doc.md), nunca cravadas aqui."""
    from casa_da_doc import NOVA, VELHA
    return [os.path.join(raiz, *c, nome) for c in (VELHA, NOVA)]


def _jornadas_do_projeto(directory):
    """Acha as jornadas do projeto. [] se não houver — e isso não é erro.

    Cascata: $PLAN_JORNADAS → journeys.md nas duas casas da doc (casa antiga primeiro)
    → []. É o documento que a etapa 4 do /start escreve; sem ele não há caminho de
    pessoa com o que cruzar, e o cruzamento fica quieto em vez de acusar todo mundo.
    """
    import cobertura
    env = os.environ.get("PLAN_JORNADAS")
    if env and os.path.exists(env):
        return cobertura.le_jornadas(env)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(directory)))
    for p in _doc_cands(raiz, "journeys.md"):
        if os.path.exists(p):
            return cobertura.le_jornadas(p)
    return []


def _caminho_da_lei(directory):
    """O arquivo da lei do projeto, ou "" se não houver — e isso não é erro.

    Cascata: $PLAN_LEI → constituicao.md nas duas casas da doc (casa antiga primeiro)
    → "". Mesma forma da cascata das jornadas, pelo mesmo motivo: sem lei escrita não há
    com o que conferir a citação, e o cruzamento fica quieto em vez de acusar todo mundo.

    O caminho sai daqui em vez de ficar dentro de quem lê os artigos porque a lei
    responde DUAS perguntas — quais artigos ela tem e quais ela declara sem cobrador —
    e resolver o arquivo duas vezes é como o mesmo fato ganhou dois vereditos.
    """
    env = os.environ.get("PLAN_LEI")
    if env and os.path.exists(env):
        return env
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(directory)))
    for p in _doc_cands(raiz, "constituicao.md"):
        if os.path.exists(p):
            return p
    return ""


def _artigos_do_projeto(directory):
    """Acha os artigos da lei do projeto. [] se não houver — e isso não é erro."""
    import cobertura
    lei = _caminho_da_lei(directory)
    return cobertura.le_artigos(lei) if lei else []


def _pecas_do_projeto(directory):
    """Acha as peças da arquitetura pretendida. [] se não houver — e isso não é erro.

    Cascata: $PLAN_ARQUITETURA → architecture-intent.md nas duas casas da doc
    (casa antiga primeiro) → []. É o documento que a etapa 2 do /start
    escreve (o que a arquitetura DEVE ser, não o que o código é); sem ele não há
    desenho com o que cruzar, e o cruzamento fica quieto em vez de acusar todo mundo.
    """
    import cobertura
    env = os.environ.get("PLAN_ARQUITETURA")
    if env and os.path.exists(env):
        return cobertura.le_pecas(env)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(directory)))
    for p in _doc_cands(raiz, "architecture-intent.md"):
        if os.path.exists(p):
            return cobertura.le_pecas(p)
    return []


def _passos_do_projeto(directory):
    """Acha os passos do ciclo do desenho de funcionamento. [] se não houver.

    Cascata: $PLAN_BLUEPRINT → blueprint.md nas duas casas da doc (casa antiga primeiro)
    → []. É o documento que a etapa 5 do /start escreve (como o sistema funciona, do
    começo ao fim); sem ele não há ciclo com o que cruzar, e o cruzamento fica quieto em
    vez de acusar todo mundo.
    """
    import cobertura
    env = os.environ.get("PLAN_BLUEPRINT")
    if env and os.path.exists(env):
        return cobertura.le_passos(env)
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(directory)))
    for p in _doc_cands(raiz, "blueprint.md"):
        if os.path.exists(p):
            return cobertura.le_passos(p)
    return []


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
    # …e desde 2026-08-06 a REDAÇÃO da própria tarefa saiu do bloqueio. Mudar o estado
    # não é reescrever o texto: obrigar a cortar um `desc` de 356 chars pra ticar fez um
    # executor mutilar descrição antiga só pra registrar trabalho que já estava feito.
    # O aviso continua — o que caiu é a recusa. Defeito que impede a marcação em si (id
    # torto, status fora do vocabulário, 'done' sem prova) segue recusando.
    redacao = set(_erros_de_redacao_do_no(plan, node_id))
    avisos_redacao = [e for e in do_alvo if e in redacao]
    do_alvo = [e for e in do_alvo if e not in redacao]
    for e in avisos_redacao:
        print("⚠️  redação de %s fora da régua (não bloqueia o tique): %s"
              % (node_id, e), file=sys.stderr)
    if do_alvo:
        raise PlanError("⛔ tick recusado: %s está fora do schema.\n  - %s"
                        % (node_id, "\n  - ".join(do_alvo)))
    if erros:
        print("⚠️  %d defeito(s) em outras tarefas (não bloqueiam este tique):" % len(erros),
              file=sys.stderr)
        for e in erros[:3]:
            print("     %s" % e, file=sys.stderr)

    pend = pendencia_viva(it)
    if pend:
        raise PlanError(
            "⛔ tick recusado: %s tem decisão em aberto.\n   %s\n\n"
            "   Feche a decisão antes de marcar feito. Quem destrava é o registro: o\n"
            "   motor de decisão escreve a escolha em `decidido` e o tique volta a\n"
            "   passar — ver plugins/visual/skills/visual/SKILL.md, 'Motor de decisão'."  # acopla-ok: ponteiro de leitura numa mensagem de erro; o tique funciona igual se o plugin visual não existir
            % (node_id, pend))

    ev = (args.evidencia or "").strip()
    if len(ev) < EVIDENCE_MIN:
        raise PlanError(
            "⛔ tick recusado: %s precisa de --evidencia.\n"
            "   Prova concreta: o comando que rodou e a saída, arquivo:linha, ou o sha\n"
            "   do commit. Sem isso, 'concluído' é palpite — foi assim que planos foram\n"
            "   dados como prontos sem estar." % node_id)

    if len(ev) > BULLET_MAX and len(prova_bullets(ev)) < 2:
        raise PlanError(
            "⛔ tick recusado: a prova de %s tem %d caracteres num bloco só.\n"
            "   A prova aparece colada ao título do passo, onde a constituição manda\n"
            "   bullet — um plano de trinta itens vira trinta parágrafos.\n"
            "   Separe com ` · `, `; `, ` + ` ou quebra de linha. Exemplo:\n"
            "     --evidencia \"$ pytest -q → 62 ok · sync-shared --check OK · a1b2c3d\"\n"
            "   Saída crua de um comando só passa inteira — o teto só vale pro texto\n"
            "   que VOCÊ redigiu." % (node_id, len(ev)))

    # F18.3 · R-28 — o tique de RETOMADA cobra mais que os outros. Trabalho achado no
    # disco não foi visto sair: quem marca não estava lá quando saiu. Então a prova tem
    # que trazer os dois que o rito à mão trouxe (F16.1, F15.1, F23.5, F17.10): o
    # veredito do revisor e o sha. Faltando um, é marcação no escuro — e a recusa diz
    # qual falta, senão o executor adivinha.
    if getattr(args, "retomada", False):
        falta = []
        if not (REVISOR_RE.search(ev) and VEREDITO_RE.search(ev)):
            falta.append("o veredito de quem revisou (ex.: 'revisor de órfão APROVOU')")
        if not SHA_RE.search(ev):
            falta.append("o sha do commit (7+ hex, ex.: 'commit b738348')")
        if falta:
            raise PlanError(
                "⛔ tick de retomada recusado: falta na prova de %s\n  - %s\n\n"
                "   Passo marcado por retomada é trabalho que ninguém viu sair: sem\n"
                "   revisão e sem sha, 'já estava feito' é palpite sobre sessão alheia.\n"
                "   Modelo: --evidencia \"revisor de órfão APROVOU · <o que ele conferiu>"
                " · commit <sha>\"" % (node_id, "\n  - ".join(falta)))

    it["status"] = "done"
    it["evidence"] = ev
    # S-148: a espera do dono entra pelo gravador e agora SAI por ele, junto da prova
    # de entrega. A saída é DECLARADA (`--sem-espera`) porque tique nem sempre é o ato
    # do dono. E a remoção APAGA a chave em vez de esvaziá-la: `espera_dono: ""` seria
    # mordido pela regra que recusa bandeira sem ato — a mesma que empurrou a remoção
    # anterior pra edição do arquivo à mão.
    if getattr(args, "sem_espera", False):
        it.pop("espera_dono", None)
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
    lei = _caminho_da_lei(directory)
    m = cobertura.mapa(plan, reqs, _jornadas_do_projeto(directory),
                       _artigos_do_projeto(directory), _pecas_do_projeto(directory),
                       _passos_do_projeto(directory),
                       sem_cobrador=cobertura.le_sem_cobrador(lei) if lei else None)
    if args.json:
        print(json.dumps(m, ensure_ascii=False))
        return 0
    print(cobertura.resumo(m))
    if not reqs:
        print("   (nenhum documento de requisitos encontrado — veja PLAN_REQS)")
    for chave, rotulo in (("sem_requisito", "⚠️ tarefas sem requisito"),
                          ("orfaos", "🔴 requisitos sem tarefa"),
                          ("sem_jornada", "🔴 funcionalidades sem jornada de origem"),
                          ("epicos_sem_jornada", "🔴 épicos sem jornada de origem"),
                          ("sem_artigo",
                           "🔴 funcionalidades sem artigo da lei que as motive"),
                          ("decididas",
                           "⚪ funcionalidades sem artigo, declaradas como decisão sua"),
                          ("artigos_sem_tarefa",
                           "🔴 artigos da lei que nenhuma tarefa representa"),
                          ("sem_peca",
                           "🔴 funcionalidades sem peça da arquitetura pretendida"),
                          ("sem_passo",
                           "🔴 funcionalidades sem passo do ciclo do desenho"),
                          ("sem_ca", "🔴 requisitos sem critério de aceite"),
                          ("jornadas_sem_funcionalidade",
                           "🔵 jornadas que nenhuma funcionalidade atende"),
                          ("passos_sem_funcionalidade",
                           "🔵 passos do ciclo que nenhuma funcionalidade atende"),
                          ("artigos_inexistentes",
                           "⛔ requisitos citando artigo que a lei não tem"),
                          ("pecas_inexistentes",
                           "⛔ requisitos citando peça que a arquitetura não tem"),
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


def cmd_pendencia(args):
    """Grava no passo a decisão que o trava — o blocker do motor virando pergunta.

    Sem isto o blocker do /sprint morria no relatório do fim da corrida: o passo
    continuava `todo` no arquivo, a rodada seguinte soltava executor nele de novo, e a
    decisão que só o dono pode tomar aparecia horas depois de nascer. Escrever a
    pergunta AQUI é o que a faz valer: `pendencia_viva` recusa o tique e a árvore
    desenha o ⛔ na linha do passo.

    A `decidido` sai junto porque escolha registrada apaga a pendência
    (`pendencia_viva`) — mantê-la faria a pergunta nova nascer invisível.
    """
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    ph, it = find_item(plan, args.node)
    if it is None:
        raise PlanError("passo '%s' não existe no plano '%s'" % (args.node, plan["id"]))
    texto = (args.texto or "").strip()
    if not texto:
        raise PlanError("⛔ pendência vazia: diga o que falta decidir.")
    erros = erros_de_estilo(texto, "pendencia")
    if erros:
        raise PlanError("⛔ pendência recusada — a régua vale para o texto que o dono lê:"
                        "\n  - %s" % "\n  - ".join(erros))
    it["pendencia"] = texto
    it.pop("decidido", None)
    save(directory, plan)
    print("⛔ %s  ·  falta decidir: %s" % (args.node, texto))
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


def cmd_frente(args):
    """Grava a frente da missão (branch + worktree) no plano — R-42.

    Quem abre branch e worktree é a casca do /sprint, antes do primeiro executor;
    este comando é só o cartório: registra o par no topo do plano para que a árvore
    mostre a frente aberta e o fechamento (`pt-frente-fechar`) saiba o que encerrar.
    É idempotente — regravar a mesma frente não é erro, e é o que torna a largada
    reexecutável. Meia frente é recusada aqui pelo mesmo motivo que
    `_erros_da_frente` recusa no init: branch sem worktree o fechamento não sabe
    encerrar.
    """
    directory = args.dir or resolve_dir()
    plan = pick_plan(directory, args.plan)
    if getattr(args, "encerrar", False):
        # Passo (7) do rito de fechamento (R-42): a frente já foi mesclada na main
        # e a branch/worktree removidas — o registro sai do plano pra que a árvore
        # e o cartão `pt-frente-fechar` parem de anunciar uma frente que não existe.
        fr = plan.pop("frente", None)
        save(directory, plan)
        print("🌿 frente encerrada: %s" % ((fr or {}).get("branch") or "(não havia)"))
        return 0
    branch = (args.branch or "").strip()
    worktree = (args.worktree or "").strip()
    if not branch or not worktree:
        raise PlanError("⛔ frente incompleta: preciso da branch E da worktree — "
                        "a frente se grava inteira ou não se grava.")
    plan["frente"] = {"branch": branch, "worktree": worktree}
    save(directory, plan)
    print("🌿 frente gravada: %s · %s" % (branch, worktree))
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
    # R-20: fechar o plano não fecha a frente. A branch continua viva na máquina e é
    # exatamente isso que fica esquecido — o aviso NOMEIA a branch pra que o dono
    # decida mesclar, manter ou descartar.
    fr = plan.get("frente") or {}
    if fr.get("branch"):
        print("   🌿 frente ainda aberta: %s (%s) — %s"
              % (fr["branch"], fr.get("worktree", ""), FRENTE_DECIDA))
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


def brief_lines(plan, nudge=None, reqs=None, desta_sessao=True):
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
            return ["🏁 PLANO ENCERRADO — %s" % s["title"],
                    "• Os %s das %s foram concluídos%s."
                    % (_plural(total, "passo"), _plural(pt, "fase"), prova),
                    "• O arquivo fica em .claude/plans/%s como registro do que foi feito." % s["path"]]
        return ["🏁 PLANO ENCERRADO (incompleto) — %s" % s["title"],
                "• %d de %d passos marcados; %s ficaram sem marcar."
                % (done, total, _plural(total - done, "passo")),
                "• O que ficou aberto continua registrado em .claude/plans/%s." % s["path"]]

    if total and done == total:
        return ["✅ CONCLUÍDO — %s" % s["title"],
                "• Os %s das %s estão marcados%s."
                % (_plural(total, "passo"), _plural(pt, "fase"), prova),
                "• Nada ficou em aberto — encerre com plan_state.py close pra ele "
                "parar de aparecer aqui."]

    # "Onde estamos" é uma AFIRMAÇÃO sobre a sessão, e ela só vale se a sessão estiver
    # mesmo nesse plano. Medido em produção (2026-08-02): a sessão mexia numa frente
    # SEM plano próprio e o fim de turno afirmava "Onde estamos" sobre a frente de
    # outro plano, com progresso e fase em curso — o material que faz o agente misturar
    # frentes. Sem sinal de que a sessão encostou no plano, o cabeçalho relata a
    # existência dele em vez de situar quem lê dentro dele.
    lines = [("📍 Onde estamos — %s" if desta_sessao
              else "📋 Plano aberto no projeto — %s") % s["title"], ""]
    if pd:
        # Quem cede quando a linha estoura o teto é a ENUMERAÇÃO das fases, nunca o
        # número — mesmo padrão do ponteiro da cobertura abaixo. Medido em 2026-08-09:
        # com 14 fases fechadas a lista entre parênteses levou o bullet a 141+ chars e
        # a régua do canal recusou o resumo INTEIRO — o dono ficou sem fim de turno.
        cheia = ("• ✅ Feito: %d de %d passos · %s %s fechada%s%s."
                 % (done, total, _plural(pd, "fase"),
                    "(%s)" % ", ".join(s["phases_done"]), "" if pd == 1 else "s",
                    ", com prova em cada passo" if provado else ""))
        curta = ("• ✅ Feito: %d de %d passos · %s fechada%s%s."
                 % (done, total, _plural(pd, "fase"), "" if pd == 1 else "s",
                    ", com prova em cada passo" if provado else ""))
        lines.append(cheia if len(cheia) <= BULLET_MAX else curta)
    else:
        lines.append("• ✅ Feito: %d de %d passos — nenhuma fase fechou ainda." % (done, total))
    nx = s["next"]
    if nx:
        lines.append("• 🔄 Agora: %s · %s — %d de %d passos."
                     % (nx["id"], nx["title"], nx["done"], nx["total"]))
    falta = total - done
    resto = [p for p in s["pending_phases"] if not nx or p != nx["id"]]
    lines.append("• ⬜ Falta: %s%s."
                 % (_plural(falta, "passo"),
                    (" · %s %s" % ("fase" if len(resto) == 1 else "fases", ", ".join(resto)))
                    if resto else ""))
    if reqs:
        import cobertura
        m = cobertura.mapa(plan, reqs)
        if m["sem_requisito"] or m["inexistentes"]:
            base = "• 🎯 Cobertura: %s" % cobertura.resumo(m)
            ponteiro = " — veja com plan_state.py cobertura."
            # Quem cede quando a linha estoura o teto é o PONTEIRO, nunca o número:
            # ele é navegação, e o rótulo 🎯 Cobertura já nomeia o comando. Com
            # tarefa citando requisito inexistente o resumo sozinho passa de 95
            # caracteres, e teto que só vale com dado pequeno não é teto.
            cheia = base + ponteiro
            lines[-1] = cheia if len(cheia) <= BULLET_MAX else base + "."
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


# O teto do fim de turno é do CONJUNTO, não de cada plano. `brief_lines` já corta
# em 3 bullets por plano — e era só isso que existia, então N planos abertos davam
# 3×N. Medido em 2026-08-02 num projeto real: 4 planos ativos renderam 12 bullets
# mais 4 cabeçalhos, num Stop que já soma 6 hooks.
BRIEF_MAX_BLOCOS = 1

# O 🏁 tem teto PRÓPRIO, e maior: ele acontece uma vez e some, então cortá-lo custa
# mais que cortar um plano aberto, que continua lá amanhã. Mas tem teto — fechar
# planos em lote despejava 3 linhas por plano no mesmo Stop, e aí o "acabou" vira
# lista. Quem for cortado entra na contagem, como no grupo ativo.
BRIEF_MAX_ENCERRADOS = 2


def _sentinel_sessao(directory, sid):
    """Onde fica a marca 'esta sessão está NESTE plano'.

    Uma função só, usada por quem escreve (`tick`/`state`/`init`) e por quem lê
    (`brief`) — chave calculada em dois lugares diverge, e sentinel que nunca casa é
    pior que sentinel nenhum (a mesma armadilha do `cksum` sobre path canonicalizado
    que já mordeu este repo).
    """
    if not sid:
        return None
    # `tempfile.gettempdir()`, não `TMPDIR or "/tmp"`: no Windows nenhuma das
    # variáveis POSIX está definida e o `/tmp` cravado vira `C:\tmp`, que não
    # existe — a marca nunca era gravada (o `except OSError` a engole), e o fim
    # de turno deixava de afirmar "Onde estamos" para quem tinha marcado o passo.
    # A stdlib já faz a cascata TMPDIR→TMP→TEMP→temp do sistema.
    tmp = tempfile.gettempdir()
    chave = hashlib.sha1(os.path.abspath(directory).encode("utf-8")).hexdigest()[:12]
    try:
        uid = os.getuid()
    except AttributeError:
        uid = 0
    return os.path.join(tmp, "claude-plan-sessao-%d-%s-%s" % (uid, str(sid)[:36], chave))


def _marca_sessao(directory, plan_id, sid=None):
    """Registra que ESTA sessão mexeu neste plano. Falha em silêncio, de propósito.

    O sinal nasce em quem MARCA porque só ele sabe de quem é a marcação: `mtime` do
    arquivo diz que alguém mexeu, nunca quem. Num projeto com frentes paralelas — 6
    sessões abertas no mesmo repositório em 2026-08-03 — a vizinha marcando um passo
    empurrava o plano dela para o topo do fim de turno de todo mundo.
    """
    caminho = _sentinel_sessao(directory, sid or os.environ.get("CLAUDE_CODE_SESSION_ID"))
    if not caminho:
        return
    try:
        with open(caminho, "w", encoding="utf-8") as fh:
            fh.write(plan_id + "\n")
    except OSError:
        pass          # marca é otimização de precisão; perdê-la degrada, não quebra


def _plano_da_sessao(directory, sid):
    """O plano que esta sessão marcou, ou None. Ilegível conta como None."""
    caminho = _sentinel_sessao(directory, sid)
    if not caminho:
        return None
    try:
        with open(caminho, encoding="utf-8") as fh:
            return fh.read().strip() or None
    except OSError:
        return None


def _tocado_em(directory, plan_id):
    """Quando o arquivo do plano foi escrito pela última vez.

    É o desempate de QUAL plano cabe no teto. Marcar um passo reescreve o arquivo,
    então o plano da frente em curso é, por construção, o mais recente. Ilegível
    conta como epoch: vai para o fim da fila, não derruba a listagem.
    """
    try:
        return os.path.getmtime(plan_path(directory, plan_id))
    except (OSError, ValueError):
        return 0.0


SOBRA_ABERTOS = "plano(s) aberto(s) neste projeto — veja com plan_state.py open"
SOBRA_ENCERRADOS = "plano(s) encerrado(s) — o registro de cada um fica em .claude/plans/"


def _cabe_no_teto(blocks, teto=BRIEF_MAX_BLOCOS, sobra_msg=SOBRA_ABERTOS):
    """Corta o excedente e DIZ quantos ficaram de fora.

    Sumir com plano em silêncio seria trocar um defeito por outro pior: o dono
    deixaria de saber que existem. A contagem é a linha que impede isso — e é por
    ela que o grupo dos encerrados também pode ser cortado sem engolir o 🏁.
    """
    if len(blocks) <= teto:
        return blocks
    sobra = len(blocks) - teto
    # Bullet, e não linha indentada: o resumo sai no canal de texto, onde o perfil
    # `hook` só admite duas formas — bullet, ou cabeçalho abrindo com emoji. O "⋯"
    # não é emoji, então a linha indentada de antes reprovava.
    return blocks[:teto] + [["• ⋯ e mais %d %s" % (sobra, sobra_msg)]]


def cmd_brief(args):
    directory = args.dir or resolve_dir()
    seen_path = getattr(args, "mark_seen", None)
    seen = _seen_ids(seen_path)
    # Dois grupos, cada um com o SEU teto. O do encerrado é maior porque a
    # confirmação acontece uma vez e some — mas "sem teto" não era a forma de
    # protegê-la: com muito plano fechado desde o marco, o 🏁 inequívoco virava um
    # despejo de blocos. Cortado, ele sai contado, nunca em silêncio.
    ativos, blocks, novos = [], [], []
    for plan in list_plans(directory):
        if plan.get("status") == "active":
            ativos.append((_tocado_em(directory, plan["id"]), plan))
            continue
        if args.closed_since is not None:   # 0 é epoch válido, e é falsy
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
    if not ativos and not blocks:
        return 0
    if seen_path and novos:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(seen_path)), exist_ok=True)
            with open(seen_path, "a", encoding="utf-8") as fh:
                fh.write("".join(i + "\n" for i in novos))
        except OSError:
            pass  # não conseguiu lembrar → repete; melhor que sumir
    # Quem cabe no teto é o plano DESTA sessão. `list_plans` entrega em ordem
    # alfabética e o nome começa com a data de criação, então o primeiro era o mais
    # ANTIGO do diretório: num projeto com frentes paralelas o fim de turno afirmava
    # "onde estamos" sobre a frente errada, e escondia a da sessão atrás do "e mais N".
    # Medido em 2026-08-02: sessão de Propostas recebia o brief de PRISMA.
    #
    # QUEM é o plano desta sessão, em duas fontes e nesta ordem:
    #
    #   1. a MARCA que a própria sessão deixou ao escrever um plano (`--sessao`).
    #      É a única fonte que sabe DE QUEM foi a mexida. `mtime` diz que alguém
    #      mexeu, nunca quem — e num projeto com frentes paralelas (6 sessões abertas
    #      no mesmo repositório em 2026-08-03) a vizinha marcando um passo empurrava o
    #      plano dela para o topo do fim de turno de todo mundo. Foi medido duas vezes
    #      em produção antes de virar código.
    #   2. sem marca, NENHUM plano é da sessão — mostrar o mais mexido é mostrar a
    #      frente da vizinha, que é o defeito que este bloco existe pra impedir.
    sid = getattr(args, "sessao", None)
    meu = _plano_da_sessao(directory, sid)
    ids = {p["id"] for _, p in ativos}
    if meu not in ids:
        meu = None                 # plano da marca já foi encerrado ou apagado
    if meu:
        # a marca é prova de autoria: afirma, e põe o plano certo no topo
        ativos.sort(key=lambda par: (par[1]["id"] != meu, -par[0]))
        ordenados = [brief_lines(plan, getattr(args, "nudge", None),
                                 _requisitos_do_projeto(directory, plan), True)
                     for _, plan in ativos]
    else:
        # Sessão sem marca: nada liga a sessão aos planos. Com UMA frente ativa,
        # mostrá-la de forma neutra orienta sem arriscar ser a vizinha — não há
        # alternativa. Com VÁRIAS, escolher uma seria a frente de outra sessão (o
        # vazamento medido em 2026-08-03: sessão que só leu o projeto recebia o
        # "43 de 56 passos" do Propostas que OUTRA sessão estava marcando), então
        # só a contagem. A cobrança do tique sobrevive nos dois casos.
        nudge = getattr(args, "nudge", None)
        if len(ativos) == 1:
            _, unico = ativos[0]
            ordenados = [brief_lines(unico, nudge,
                                     _requisitos_do_projeto(directory, unico), False)]
        else:
            n = len(ativos)
            if nudge:
                cobranca = nudge.strip().lstrip("• ").strip()
                ordenados = [["📋 %d plano(s) aberto(s) neste projeto." % n,
                              "• " + cobranca]]
            else:
                # Plural fixo, não "plano(s)": este ramo só roda com n >= 2 (o caso de
                # UM plano sai pelo `if` acima), então a forma singular era garantidamente
                # errada — "8 plano aberto" foi o que apareceu na tela. Relatado com print
                # de produção em 2026-08-06.
                ordenados = [[("📋 %d planos abertos neste projeto — veja com "
                               "plan_state.py open") % n]]
    encerrados = _cabe_no_teto(blocks, BRIEF_MAX_ENCERRADOS, SOBRA_ENCERRADOS)
    # Régua no ponto de uso: o canal aqui é o terminal, não a página. Bloco que
    # quebra o perfil do canal não vai para a tela — vai a recusa, dizendo o que
    # quebrou, para o defeito aparecer em vez de sair renderizado errado.
    saida = []
    for bloco in _cabe_no_teto(ordenados) + encerrados:
        errs = erros_do_brief(bloco, "resumo de fim de turno")
        saida.append(bloco if not errs
                     else ["⚠️ Resumo recusado pela régua do canal: %s" % "; ".join(errs)])
    print("\n\n".join("\n".join(b) for b in saida))
    return 0


# ── render ─────────────────────────────────────────────────────────────────

MARK = {"done": "✅", "doing": "🔄", "blocked": "⛔", "todo": "⬜"}
DOT = {"done": "●", "doing": "◐", "blocked": "✕", "todo": "○"}


def pendencia_viva(it):
    """A pergunta que AINDA trava a tarefa — "" quando já foi respondida.

    Quem resolve a pendência é a DECISÃO registrada, não a ausência do campo: o `init`
    que omite a `pendencia` não a apaga (o `merge` preserva o que o init não trouxe), e
    o autor do plano não tem que saber que existe um merge pra conseguir destravar. A
    pergunta continua no arquivo de propósito — é dela que o `reabrir` vive.

    É UMA função porque a regra vale nos dois lados e eles precisam concordar: quem
    RECUSA o tique (`cmd_tick`) e quem DESENHA a linha de baixo do item (`_detalhe`).
    Enquanto eram duas, a árvore anunciava "⛔ falta decidir" sobre passo já destravado
    — e é essa árvore que o motor lê como fila, então ele gastava o tier caro
    diagnosticando por que passos com `decidido` gravado "não saíam do lugar". Mesma
    armadilha da chave de sentinel computada em dois lugares (`patterns.md` §1.6).
    """
    dec = it.get("decidido")
    # `escolha` NULA não destrava, e a distinção não é preciosismo: `str(None)` devolve
    # a palavra "None", que é texto não-vazio — então gravar "não escolhi" liberava o
    # tique. O `or ""` é o que separa ausência de escolha de escolha vazia.
    if isinstance(dec, dict) and str(dec.get("escolha") or "").strip():
        return ""
    return str(it.get("pendencia") or "").strip()


def prova_bullets(ev):
    """A prova, quebrada nos separadores que quem a escreveu já usou.

    Um plano de trinta passos com um parágrafo em cada não se lê — foi essa a
    queixa que abriu o assunto. A prova vive no nível do corpo, onde a
    constituição manda bullet (`quality-goals.md:47`); a isenção de lá cobre a
    saída crua DENTRO do bloco de prova, não a linha colada ao título.

    Não inventa corte: quebra só onde já existe `\\n`, ` · `, `; ` ou ` + `.
    Prova de um segmento só continua um bullet — quem barra a linha corrida
    longa é o `tick`, no momento de gravar, não o renderizador.
    """
    ev = str(ev or "").strip()
    if not ev:
        return []
    partes = [ev]
    for sep in ("\n", " · ", "; ", " + "):
        partes = [p for bloco in partes for p in bloco.split(sep)]
    return [p.strip(" ·;") for p in partes if p.strip(" ·;")]


def _detalhe_html(texto, classe):
    """A prova vira um bloco dobrável fechado; o resto continua um span.

    O `_detalhe` devolve `prova:` + bullets separados por `\n` — jogar isso num
    span colapsaria tudo numa linha, que é o defeito que F6.1 conserta.

    O rótulo do que fica fechado é DERIVADO do conteúdo (`quality-goals.md:102`):
    promove o primeiro pedaço da prova e conta o que sobrou (`… · +2`). A etiqueta
    fixa `prova:` já foi tentada e rejeitada — num plano de 72 passos feitos ela
    dava 72 linhas idênticas, que não ajudam a decidir se vale abrir.
    """
    if classe != "pt-evidence":
        return '<span class="%s">%s</span>' % (classe, _e(texto))
    # F25.1: a prova nasce FECHADA — <details> nativo, sem JS, como a árvore de valor.
    linhas = texto.split("\n")
    if len(linhas) > 1:
        bullets = [b.lstrip("· ").strip() for b in linhas[1:] if b.strip()]
    else:
        bullets = [linhas[0].partition(":")[2].strip() or linhas[0]]
    rot = bullets[0] if len(bullets[0]) <= 88 else bullets[0][:87].rstrip() + "…"
    if len(bullets) > 1:
        rot += " · +%d" % (len(bullets) - 1)
        corpo = ('<ul class="pt-prova">'
                 + "".join("<li>%s</li>" % _e(b) for b in bullets)
                 + "</ul>")
    else:
        corpo = '<span class="pt-evidence">%s</span>' % _e(bullets[0])
    return ('<details class="pt-evidence-d"><summary><span class="pt-chev">▸</span>'
            '<span class="pt-prova-rot">%s</span></summary>%s</details>' % (_e(rot), corpo))


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
        bs = prova_bullets(ev)
        if len(bs) > 1:
            return "prova:\n" + "\n".join("· " + b for b in bs), "pt-evidence"
        return "prova: " + ev, "pt-evidence"
    esp = str(it.get("espera_dono", "")).strip()
    if esp:
        return "⏸️ espera você: " + esp, "pt-desc"
    pend = pendencia_viva(it)
    if pend:
        return "⛔ falta decidir: " + pend, "pt-desc"
    d = it.get("desc", "") or ""
    # `desc` em lista sobrevive ao init (o validador o stringifica ao medir) — o
    # renderizador não pode ser o primeiro a quebrar: vira bullets, um por linha.
    if isinstance(d, (list, tuple)):
        d = "\n".join("· " + str(b) for b in d)
    return d, "pt-desc"


def render_text(plan, reqs=None, vista="execucao", compacto=False):
    """A árvore de execução em texto.

    `compacto` existe para a pergunta "onde a gente está?", que se faz muitas vezes por
    sessão: uma linha por passo, sem a prova nem a linha didática. A árvore inteira de um
    plano de 37 passos passa de ~130 linhas para ~50, e cabe numa tela. A vista completa
    continua sendo o padrão — quem quer a prova de um passo feito lê ela.
    """
    if vista == "valor":
        return _render_valor(plan, reqs or {})
    done, total = plan_progress(plan)
    out = ["📋 %s — %d/%d passos" % (plan.get("title", plan["id"]), done, total)]
    # A frente aparece na árvore porque ela é o que fica esquecido: quem lê "onde a
    # gente está" tem que ver em qual branch/worktree este plano vive.
    fr = plan.get("frente") or {}
    if fr.get("branch"):
        out.append("🌿 frente: %s · %s" % (fr["branch"], fr.get("worktree", "")))
    out.append("")
    for ph in plan["phases"]:
        pd, pt = phase_progress(ph)
        out.append("%s %s · %s   (%d/%d)" % (MARK[phase_status(ph)], ph["id"], ph["title"], pd, pt))
        for it in ph["items"]:
            st = it.get("status", "todo")
            # Passo que espera um ato do dono não é "a fazer": ninguém vai pegá-lo
            # enquanto o ato não acontecer. O bolinha diz isso na própria árvore.
            ponto = "⏸" if (st != "done" and str(it.get("espera_dono", "")).strip()) else DOT[st]
            out.append("     %s %s  %s" % (ponto, it["id"], it["title"]))
            if compacto:
                if str(it.get("espera_dono", "")).strip() and st != "done":
                    out.append("            ⏸️ espera você: %s" % it["espera_dono"])
                # a pendência sobrevive ao corte junto com a espera acima: ela é o "deu
                # problema", e esconder problema no modo curto seria o anti-padrão que
                # o resto deste arquivo existe pra impedir. Quem decide se ela ainda
                # trava é `pendencia_viva` — a pendência crua aqui era a segunda cópia
                # da regra, e anunciava preso o passo que o `decidido` já destravou.
                pend_viva = pendencia_viva(it)
                if pend_viva:
                    out.append("            ⛔ %s" % pend_viva)
                continue
            det = _detalhe(it)[0]
            # `prova:` multilinha chega com \n — cada bullet ganha a mesma sangria
            out += ["            %s" % ln for ln in det.split("\n")]
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
        bs = prova_bullets(ev)
        if len(bs) > 1:
            linhas.append("%s    prova:" % ind)
            linhas += ["%s      · %s" % (ind, b) for b in bs]
        else:
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
    # A mesma frente que a árvore de texto mostra: a página HTML é a superfície que o
    # dono abre, e é nela que a branch esquecida tem que aparecer. Aqui ela vem como
    # CARTÃO DE FECHAMENTO (R-20) — nomear a branch só avisa; o que fecha a frente é a
    # decisão com os comandos dela à mão, na página do relatório do sprint.
    fr = plan.get("frente") or {}
    if fr.get("branch"):
        b, w = _e(fr["branch"]), _e(fr.get("worktree", ""))
        parts.append('  <div class="pt-frente pt-frente-fechar">')
        parts.append('    <b>🌿 frente aberta: %s</b>' % b)
        parts.append('    <p>worktree: %s</p>' % w)
        parts.append('    <p>%s</p>' % FRENTE_DECIDA)
        parts.append('    <p><code>git worktree remove %s</code> · '
                     '<code>git branch -d %s</code></p>' % (w, b))
        parts.append('  </div>')

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
            parts.append('        ' + _detalhe_html(texto, classe))
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
            p.append(('    <div class="pt-t pt-%s"><span class="pt-mark">%s</span>'
                      '<span class="pt-id">%s</span> %s'
                      % (st, DOT[st], _e(t["id"]), _e(t["title"])))
                     + _detalhe_html(texto, classe) + '</div>')
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
                                     vista=getattr(args, "vista", "execucao"),
                                     compacto=getattr(args, "compacto", False)))
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
    <p class="feedback-intro">Os vereditos já estão nas fases acima — aqui não tem segunda tabela,
       só o progresso, uma observação geral e o envio.</p>
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
    """Devolve a árvore desenhada ao `visual`, que monta a página, e imprime o caminho.

    A moldura não é aberta daqui: a árvore vai num bloco `raw_html` do spec e quem
    embute é o `visual_page.py`. O contrato entre os dois plugins é o SPEC.

    Nome de arquivo estável por plano: a página de acompanhamento é reescrita
    no MESMO caminho a cada tick, então o usuário dá refresh na aba que já está
    aberta em vez de acumular 51 arquivos como antes.
    """
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
    montador = visual_page_path()
    if not montador:
        raise PlanError(
            "quem monta a página é o plugin `visual`, que não está nesta máquina — "
            "instale-o, ou use `render --format text`")

    estado, kicker, h1, sub = PAGE_COPY[args.mode]
    done, total = plan_progress(plan)
    titulo = plan.get("title", plan["id"])
    blocos = [{"kind": "raw_html",
               "html": render_html(plan, args.mode,
                                   reqs=_requisitos_do_projeto(directory, plan),
                                   vista=vista)}]
    if args.mode == "approve":
        blocos.append({"kind": "raw_html", "html": CLOSING_BOX})
    spec = {
        "title": h1,
        "doc_title": "%s — %s" % (h1, titulo),
        "subtitle": sub,
        "kicker": kicker,
        # o 1º chip é o destacado; o estado do plano vira chip porque a faixa de
        # identidade do `visual` só aceita os estados DELA (rascunho|gerado|noar|apresentado)
        "chips": ["%d/%d feitos" % (done, total),
                  "📋 %d fases · %d passos" % (len(plan["phases"]), total),
                  estado,
                  "📅 %s" % time.strftime("%Y-%m-%d")],
        "chip_primary": True,
        "ident": {
            # directory é <raiz>/.claude/plans — dois níveis acima é o nome do projeto.
            # ⚠️ E ele pode sair VAZIO: quando o diretório está a menos de dois níveis
            # da raiz do sistema, `basename('/')` é `''`, o `visual` recusa o spec
            # ("ident.projeto e ident.artefato são obrigatórios") e a página do plano
            # não nasce. Medido em 2026-08-10: no Linux um plano em `/tmp/<algo>`
            # quebrava, e no macOS o MESMO caminho passava — lá `/tmp` é atalho para
            # `/private/tmp`, então sobrava um nível e o nome não vinha vazio. O
            # fallback nomeia o que existe, em vez de deixar a página morrer.
            "projeto": (os.path.basename(os.path.abspath(os.path.join(directory, "..", "..")))
                        or os.path.basename(os.path.abspath(directory))
                        or "projeto sem nome"),
            "artefato": titulo,
            "gerado_de": "plan_state.py page --mode %s" % args.mode,
            "estado": "gerado",
        },
        "sections": [{"blocks": blocos}],
    }

    out = args.out
    if not out:
        vdir = _roda_resolvedor(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "resolve-dir.sh"),
            os.getcwd(), "visual")
        if not vdir:
            raise PlanError("não consegui resolver o diretório do /visual — passe --out")
        # a vista entra no nome: sem ela, as duas árvores do mesmo plano gravam no
        # mesmo arquivo e a última apaga a outra em silêncio
        sufixo = args.mode if vista == "execucao" else "%s-%s" % (args.mode, vista)
        out = os.path.join(vdir, "plano-%s-%s.html" % (plan["id"], sufixo))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    r = subprocess.run([sys.executable, montador, "build", "--spec", "-", "--out", out],
                       input=json.dumps(spec, ensure_ascii=False), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", start_new_session=True)
    if r.returncode != 0:
        raise PlanError("o `visual` recusou a página:\n%s" % (r.stderr or "").strip())
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
    q.add_argument("--sem-espera", dest="sem_espera", action="store_true",
                   help="tira a espera do dono deste passo (o ato já aconteceu)")
    q.add_argument("--retomada", action="store_true",
                   help="o passo veio de trabalho órfão: a prova exige veredito do "
                        "revisor E sha do commit")
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
    q.add_argument("--compacto", action="store_true",
                   help="uma linha por passo, sem a prova — a vista de 'onde a gente está'")
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
    q.add_argument("--sessao", help="id da sessão: mostra o plano que ELA marcou, não o "
                                    "que a sessão vizinha mexeu por último")
    q.set_defaults(func=cmd_brief)

    q = sub.add_parser("cobertura", help="o mapa entre requisito e tarefa, os dois lados")
    q.add_argument("plan", nargs="?")
    q.add_argument("--reqs", help="caminho do documento de requisitos (default: cascata)")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_cobertura)

    q = sub.add_parser("pendencia", help="grava no passo a decisão que o trava")
    q.add_argument("plan", nargs="?")
    q.add_argument("node")
    q.add_argument("texto")
    q.set_defaults(func=cmd_pendencia)

    q = sub.add_parser("reabrir", help="derruba uma decisão tomada no seu lugar")
    q.add_argument("plan", nargs="?")
    q.add_argument("node")
    q.set_defaults(func=cmd_reabrir)

    q = sub.add_parser("frente", help="grava a frente da missão (branch + worktree) no plano")
    q.add_argument("plan", nargs="?")
    q.add_argument("branch", nargs="?")
    q.add_argument("worktree", nargs="?")
    q.add_argument("--encerrar", action="store_true",
                   help="tira a frente do plano — passo (7) do rito de fechamento")
    q.set_defaults(func=cmd_frente)

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
