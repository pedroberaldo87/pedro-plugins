#!/usr/bin/env python3
"""O pré-check de largada, passada 1 — a caça à decisão que trava o passo (F22.1 · R-32).

Nada caça a decisão NÃO-DECLARADA: `espera_dono` e `pendencia` travam por programa
quando alguém os escreve, e quando ninguém escreve a decisão explode no meio da
corrida como tique recusado. Esta passada varre os passos ABERTOS de um plano de
verdade e devolve o que precisa virar decisão do dono ANTES do disparo.

O que é mecânico mora aqui; o julgamento ("que decisão está embutida nesta frase?")
é passada de modelo e não cabe em programa nenhum. As sete checagens mecânicas:

    regua_pronto        o critério chegou cortado, ou fecha escrevendo à mão
    precondicao         o passo consome caminho que não está no disco
    ato_do_dono         o `pronto` pede ato do dono e ninguém declarou `espera_dono`
    tranca              o passo toca documento `status: approved` sem `protegido`
    aritmetica          `pronto` e `decidido` do MESMO passo se anulam por conta
    segredo             variável citada com zero ocorrência na árvore
    impedimento         "não alcanço X" afirmado de memória, sem comando que prove

O MÓDULO NÃO ESCREVE NO PLANO. Achado vira PERGUNTA ao dono — nunca campo gravado no
passo por palpite. Quem grava é o dono respondendo, e a resposta é selada em
`decisoes_seladas`. E ANTES de virar pergunta, todo achado passa pelo registro
selado: pergunta repetida é falha do processo, não pedido novo.

Cada achado sai classificado, porque perguntar o adiável trava tanto quanto não
perguntar o bloqueante:

    BLOQUEANTE-AGORA  sem a resposta o passo trava  → vai ao dono antes da largada
    ADIÁVEL           a resposta só faz falta no fim → fica registrada, não pergunta

Uso:
    from precheck_largada import passada1
    r = passada1(plano, raiz)      # plano = o dict do .plan.json
    r["perguntas"]                 # o que vai ao dono ANTES da largada
    r["registrados"]               # o adiável e o que o registro selado já respondeu

    t = triar(raiz, achados)       # a suspeita que NÃO passa no teste da pergunta
                                   # precisa (passo + pergunta + prova) não vai ao
                                   # dono e não some: vira linha em
                                   # `.claude/neblina.md` (F22.9). `pode_fechar(raiz)`
                                   # só libera o fecho com neblina vazia ou toda
                                   # declarada fora de escopo.

    r = passada2(plano, raiz)      # a SEQUÊNCIA: o que só trava no encadeamento
                                   # (dependência real fora do dependsOn, dois
                                   #  paralelos no mesmo arquivo quente, ordem que
                                   #  contradiz a dependência ou o critério, e a
                                   #  ordem de aplicação entre artefatos numerados)

    r = passada3(raiz, suite_cmd=..., gate_cmd=...)
                                   # A CASA, medida por EXECUÇÃO: esteira verde na
                                   # árvore da largada com a prova gravada, gate de
                                   # commit dentro do teto, suiteCmd medindo mais que
                                   # zero, alvo resolvível e veredito estável. A
                                   # referência é a FOTO da largada, nunca verde
                                   # absoluto — e porta fechada aqui não larga.

    r = passada4(plano, raiz)      # A VIZINHANÇA: motor vivo na mesma árvore
                                   # (sinal + reserva de arquivo), guarda de
                                   # PreToolUse que NEGA o comando do passo, recurso
                                   # externo sem espera declarada, porta fixa
                                   # disputada e a regra de exclusividade do
                                   # CLAUDE.md virada checagem de `ps`.

    r = rodada_seguinte(raiz, respostas)
                                   # A RODADA N+1: parte das RESPOSTAS da rodada N,
                                   # não do plano. Lê o que cada resposta confirmou,
                                   # desconfirmou ou revelou de novo; rodada sem
                                   # decorrência devolve `fechou: True`.

    python3 precheck_largada.py <plano.json> [--raiz .] [--passada 1|2|3|4]
                                   # exit 1 = há pergunta

stdlib only (requisito do repo).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import andamento  # noqa: E402
from auditoria_plano import ATO_DO_DONO  # noqa: E402
from decisoes_seladas import consultar  # noqa: E402
from plan_state import pick_plan  # noqa: E402
from regua_pronto import criterio_cortado, erros_de_pronto  # noqa: E402

BLOQUEANTE = "BLOQUEANTE-AGORA"
ADIAVEL = "ADIÁVEL"

# Caminho de arquivo dentro do texto do passo: tem barra e extensão curta.
_CAMINHO = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.[A-Za-z0-9]{1,5}")

# O passo CONSOME o caminho (ele tem que existir antes) em vez de produzi-lo.
_CONSOME = re.compile(
    r"\b(a partir d[aeo]|reusa|reutiliza|l[êe] |lendo|conferid[oa] em|j[áa] existe"
    r"|existente|copiad[oa] d[aeo]|derivad[oa] d[aeo])\b", re.I)

# A afirmação de impedimento — as duas mais caras da colheita eram FALSAS, e um
# comando de 2s desmentia cada uma.
_IMPEDIMENTO = re.compile(
    r"\b(n[ãa]o alcan[çc]|sem acesso|n[ãa]o tenho acesso|s[óo] o dono"
    r"|somente o dono|inating[íi]vel|imposs[íi]vel de fora)\w*", re.I)

# Variável de ambiente / segredo citado no texto do passo.
_VARIAVEL = re.compile(r"\$\{?([A-Z][A-Z0-9_]{3,})\}?"
                       r"|\b([A-Z][A-Z0-9]*_(?:TOKEN|KEY|SECRET|SENHA|PASSWORD|URL))\b")

_UNIDADE = {"s": 1, "seg": 1, "segundo": 1, "segundos": 1,
            "m": 60, "min": 60, "minuto": 60, "minutos": 60,
            "h": 3600, "hora": 3600, "horas": 3600,
            "d": 86400, "dia": 86400, "dias": 86400}
_PERIODO = re.compile(r"(\d+)\s*(segundos?|seg|minutos?|min|horas?|dias?|[smhd])\b", re.I)


def _periodos(texto):
    """Os períodos citados no texto, em segundos."""
    out = []
    for n, un in _PERIODO.findall(str(texto or "")):
        s = _UNIDADE.get(un.lower())
        if s:
            out.append(int(n) * s)
    return out


def _abertos(plano):
    """Os passos ainda ABERTOS — o pré-check é sobre o que vai rodar, não sobre o feito."""
    for fase in plano.get("phases") or []:
        for item in fase.get("items") or []:
            if str(item.get("status") or "todo").lower() != "done":
                yield item


def _texto(passo):
    return "%s %s" % (passo.get("desc") or "", passo.get("pronto") or "")


def _sob_tranca(raiz, caminho):
    """O arquivo traz `status: approved` no frontmatter? Régua de DISCO, não de julgamento."""
    arq = caminho if os.path.isabs(caminho) else os.path.join(raiz, caminho)
    try:
        with open(arq, encoding="utf-8", errors="replace") as f:
            cabeca = "".join([next(f, "") for _ in range(20)])
    except OSError:
        return False
    return bool(re.search(r"^status:\s*approved\s*$", cabeca, re.M))


def _grep(raiz, agulha):
    """Quantos arquivos rastreados citam a agulha. `None` = não deu para medir."""
    try:
        r = subprocess.run(["git", "grep", "-lF", "--", agulha], cwd=raiz,
                           capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode > 1:
        return None
    return len([ln for ln in r.stdout.splitlines() if ln.strip()])


def _achado(passo, check, classe, pergunta, prova):
    return {"passo": str(passo.get("id") or "?"), "check": check, "classe": classe,
            "pergunta": pergunta, "prova": prova}


def _checagens(passo, raiz, produzidos):
    """As sete checagens mecânicas sobre UM passo aberto."""
    pid = str(passo.get("id") or "?")
    pronto = str(passo.get("pronto") or "")
    texto = _texto(passo)
    out = []

    for erro in criterio_cortado(pronto, pid) + erros_de_pronto(pronto, pid):
        out.append(_achado(passo, "regua_pronto", BLOQUEANTE,
                           "o critério deste passo não é executável como está escrito "
                           "— reescreve o critério ou o passo sai da largada?", erro))

    if not str(passo.get("espera_dono") or "").strip() and ATO_DO_DONO.search(pronto):
        out.append(_achado(passo, "ato_do_dono", BLOQUEANTE,
                           "o critério pede um ato que só você faz e o passo não "
                           "declara espera — você faz o ato, ou o passo declara a "
                           "espera?", pronto))

    for caminho in sorted(set(_CAMINHO.findall(texto))):
        if _sob_tranca(raiz, caminho) and not str(passo.get("protegido") or "").strip():
            out.append(_achado(passo, "tranca", BLOQUEANTE,
                               "o passo toca %s, que está aprovado e trancado, e não "
                               "nasceu como proposta — entrega proposta ou você "
                               "destranca o arquivo?" % caminho,
                               "%s: status: approved no frontmatter" % caminho))
            continue
        alvo = caminho if os.path.isabs(caminho) else os.path.join(raiz, caminho)
        if os.path.exists(alvo) or not _CONSOME.search(texto):
            continue
        # Adiável quando OUTRO passo aberto produz o caminho; sem isso o passo larga
        # em cima do que não existe.
        outro_produz = produzidos.get(caminho, set()) - {pid}
        classe = ADIAVEL if outro_produz else BLOQUEANTE
        out.append(_achado(passo, "precondicao", classe,
                           "o passo parte de %s, que não está no disco — quem produz "
                           "esse arquivo antes da largada?" % caminho,
                           "%s: não existe em %s" % (caminho, raiz)))

    decidido = passo.get("decidido") or {}
    escolha = " ".join(str(decidido.get(k) or "") for k in ("escolha", "porque"))
    pp, pd = _periodos(pronto), _periodos(escolha)
    if pp and pd and min(pp) < min(pd):
        out.append(_achado(passo, "aritmetica", BLOQUEANTE,
                           "o critério pede %ds e a decisão já tomada escolhe um grão "
                           "de %ds — por aritmética não fecha; muda o critério ou a "
                           "decisão?" % (min(pp), min(pd)),
                           "pronto: %s | decidido: %s" % (pronto, escolha)))

    for a, b in _VARIAVEL.findall(texto):
        nome = a or b
        n = _grep(raiz, nome)
        if n == 0:
            out.append(_achado(passo, "segredo", BLOQUEANTE,
                               "o passo cita a variável %s e ela não aparece em lugar "
                               "nenhum da árvore — quem a define antes da largada?"
                               % nome, "git grep -lF %s: 0 arquivos" % nome))

    m = _IMPEDIMENTO.search(texto)
    if m:
        out.append(_achado(passo, "impedimento", BLOQUEANTE,
                           "o passo AFIRMA um impedimento (\"%s\") de memória — qual "
                           "é o comando que o prova? As duas afirmações mais caras da "
                           "colheita eram falsas." % m.group(0), texto.strip()[:200]))
    return out


def passada1(plano, raiz, hoje=None):
    """A passada item a item sobre os passos abertos. Não escreve nada em lugar nenhum.

    Devolve `perguntas` (o bloqueante que ainda não tem resposta selada) e
    `registrados` (o adiável e o que o registro selado já respondeu). O registro é
    consultado ANTES de qualquer pergunta: pergunta repetida é falha do processo.
    """
    passos = list(_abertos(plano))
    produzidos = {}
    for p in passos:
        for c in _CAMINHO.findall(_texto(p)):
            produzidos.setdefault(c, set()).add(str(p.get("id") or "?"))

    achados = []
    for p in passos:
        achados.extend(_checagens(p, raiz, produzidos))

    perguntas, registrados = [], []
    for a in achados:
        seladas = consultar(raiz, a["pergunta"])
        if seladas:
            a["respondida_por"] = seladas[0]
            registrados.append(a)
        elif a["classe"] == BLOQUEANTE:
            perguntas.append(a)
        else:
            registrados.append(a)
    return {"passos_abertos": [str(p.get("id")) for p in passos],
            "achados": achados, "perguntas": perguntas, "registrados": registrados}



# ── PASSADA 2 · A SEQUÊNCIA (F22.2) ─────────────────────────────────────────
# Artefato numerado (migration 124_ antes de 125_): a ordem de aplicação é o
# NÚMERO, não a ordem em que o plano cita os passos.
_NUMERADO = re.compile(r"(?:^|/)(\d{3,})[_-]")


def _arquivos(passo):
    """Os arquivos do passo: os declarados em `files` mais os citados no texto."""
    fora = set(str(c) for c in (passo.get("files") or []))
    return fora | set(_CAMINHO.findall(_texto(passo)))


def _depende_de(passo):
    return set(str(d) for d in (passo.get("dependsOn") or []))


def _mapa_de_producao(passos):
    """Quem PRODUZ cada caminho e quem o CONSOME, na ordem declarada.

    Produz quem o declara em `files` ou o cita sem marcador de consumo; consome
    quem o cita com marcador (`a partir de`, `lê`, `reusa`…) e não o declara seu.
    """
    produz, consome = {}, {}
    for p in passos:
        pid = str(p.get("id") or "?")
        meus = set(str(c) for c in (p.get("files") or []))
        citados = set(_CAMINHO.findall(_texto(p)))
        puxa = bool(_CONSOME.search(_texto(p)))
        for c in meus | citados:
            if c in meus or not puxa:
                produz.setdefault(c, []).append(pid)
            if puxa and c not in meus:
                consome.setdefault(c, []).append(pid)
    return produz, consome


def _arquivo_quente(passos):
    """O detector de arquivo quente: dois passos PARALELOS no mesmo arquivo.

    Paralelo é o que o plano declarou paralelo (`parallelizable`), e só conta
    quando nenhum dos dois depende do outro — com dependência declarada eles não
    rodam juntos.
    """
    paralelos = [p for p in passos if p.get("parallelizable")]
    out = []
    for i, a in enumerate(paralelos):
        for b in paralelos[i + 1:]:
            ia, ib = str(a.get("id") or "?"), str(b.get("id") or "?")
            if ia in _depende_de(b) or ib in _depende_de(a):
                continue
            comuns = sorted(_arquivos(a) & _arquivos(b))
            if comuns:
                out.append((a, ib, comuns))
    return out


def passada2(plano, raiz):
    """A passada sobre a SEQUÊNCIA — o que só trava no encadeamento.

    Mesma saída da passada 1: `perguntas` (o que vai ao dono antes da largada) e
    `registrados`. Não escreve nada em passo nenhum.
    """
    passos = list(_abertos(plano))
    ordem = {str(p.get("id") or "?"): i for i, p in enumerate(passos)}
    fase = {}
    for f in plano.get("phases") or []:
        for it in f.get("items") or []:
            fase[str(it.get("id") or "?")] = str(f.get("id") or f.get("title") or "?")
    produz, consome = _mapa_de_producao(passos)
    por_id = {str(p.get("id") or "?"): p for p in passos}
    achados = []

    # 1 · dependência REAL fora do dependsOn — e a que a ordem declarada nega.
    for caminho, quem_puxa in sorted(consome.items()):
        for pid in quem_puxa:
            for bid in produz.get(caminho, []):
                if bid == pid:
                    continue
                p = por_id[pid]
                if bid not in _depende_de(p):
                    achados.append(_achado(
                        p, "dependencia_nao_declarada", BLOQUEANTE,
                        "o passo %s parte de %s, que o passo %s produz, e não declara "
                        "essa dependência — %s entra no dependsOn de %s, ou a ordem "
                        "muda?" % (pid, caminho, bid, bid, pid),
                        "%s consome %s · %s produz %s · dependsOn(%s)=%s"
                        % (pid, caminho, bid, caminho, pid,
                           sorted(_depende_de(p)) or "[]")))
                elif ordem.get(bid, -1) > ordem[pid]:
                    achados.append(_achado(
                        p, "ordem_contraditoria", BLOQUEANTE,
                        "o passo %s depende de %s, que a ordem declarada manda fazer "
                        "DEPOIS — inverte a ordem ou solta a dependência?" % (pid, bid),
                        "ordem: %s (fase %s) antes de %s (fase %s)"
                        % (pid, fase.get(pid, "?"), bid, fase.get(bid, "?"))))

    # 2 · dependência declarada apontando para passo que vem depois (fase aberta
    #     incluída) mesmo sem artefato em comum.
    for p in passos:
        pid = str(p.get("id") or "?")
        for bid in sorted(_depende_de(p)):
            if bid in ordem and ordem[bid] > ordem[pid]:
                if any(a["check"] == "ordem_contraditoria" and a["passo"] == pid
                       and bid in a["pergunta"] for a in achados):
                    continue
                achados.append(_achado(
                    p, "ordem_contraditoria", BLOQUEANTE,
                    "o passo %s depende de %s, que a ordem declarada manda fazer "
                    "DEPOIS — inverte a ordem ou solta a dependência?" % (pid, bid),
                    "ordem: %s (fase %s) antes de %s (fase %s)"
                    % (pid, fase.get(pid, "?"), bid, fase.get(bid, "?"))))

    # 3 · dependência de CRITÉRIO: o `pronto` de um passo cita passo posterior.
    for p in passos:
        pid = str(p.get("id") or "?")
        pronto = str(p.get("pronto") or "")
        for bid in ordem:
            if bid == pid or ordem[bid] <= ordem[pid]:
                continue
            if re.search(r"(?<![\w.])%s(?![\w.])" % re.escape(bid), pronto):
                achados.append(_achado(
                    p, "dependencia_de_criterio", BLOQUEANTE,
                    "o critério de %s só é satisfazível depois de %s, e a ordem manda "
                    "%s por último — inverte a ordem ou reescreve o critério?"
                    % (pid, bid, bid),
                    "pronto de %s cita %s · ordem: %s antes de %s"
                    % (pid, bid, pid, bid)))

    # 4 · dois paralelos no mesmo arquivo quente.
    for a, bid, comuns in _arquivo_quente(passos):
        achados.append(_achado(
            a, "arquivo_quente", BLOQUEANTE,
            "os passos %s e %s são paralelos e tocam o mesmo arquivo %s — serializa "
            "os dois ou divide o arquivo?"
            % (str(a.get("id") or "?"), bid, comuns[0]),
            "arquivo(s) em comum: %s" % ", ".join(comuns)))

    # 5 · ordem de aplicação entre artefatos numerados (125 antes de 124 estoura).
    numerados = []
    for p in passos:
        pid = str(p.get("id") or "?")
        for c in sorted(_arquivos(p)):
            m = _NUMERADO.search(c)
            if m:
                numerados.append((ordem[pid], int(m.group(1)), pid, c, p))
    for i, (oi, ni, pid, ci, p) in enumerate(numerados):
        for oj, nj, bid, cj, _ in numerados[i + 1:]:
            if oi < oj and ni > nj:
                achados.append(_achado(
                    p, "ordem_de_artefatos", BLOQUEANTE,
                    "o passo %s aplica %s antes de %s (passo %s), e a ordem de "
                    "aplicação é o número — inverte os dois?" % (pid, ci, cj, bid),
                    "%s (%d) vem antes de %s (%d) na ordem declarada"
                    % (ci, ni, cj, nj)))

    perguntas, registrados = [], []
    for a in achados:
        seladas = consultar(raiz, a["pergunta"])
        if seladas:
            a["respondida_por"] = seladas[0]
            registrados.append(a)
        elif a["classe"] == BLOQUEANTE:
            perguntas.append(a)
        else:
            registrados.append(a)
    return {"passos_abertos": [str(p.get("id")) for p in passos],
            "achados": achados, "perguntas": perguntas, "registrados": registrados}


# ── PASSADA 3 · A CASA, MEDIDA POR EXECUÇÃO (F22.3) ─────────────────────────
# As duas passadas anteriores leem o PLANO. Esta roda COMANDO: o que ela afirma
# sobre a casa foi medido nesta largada, não lembrado de uma rodada antiga. A
# referência é a FOTO da largada — a árvore como ela está agora, hash e tudo —, e
# nunca "verde absoluto": esteira verde ontem, ou verde num outro estado do disco,
# não diz nada sobre o código que vai rodar daqui a pouco.

GREEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "green-cache.sh")

# "155 suíte(s) · 0 problema(s)" — quantas suítes a esteira REALMENTE mediu.
_MEDIDAS = re.compile(r"(\d+)\s*su[íi]te", re.I)


def _roda(cmd, raiz, teto):
    """Roda o comando na raiz. Devolve (rc, saída) — rc `None` = estourou o teto."""
    try:
        r = subprocess.run(cmd, cwd=raiz, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=teto,
                           stdin=subprocess.DEVNULL, start_new_session=True)
    except subprocess.TimeoutExpired:
        return None, ""
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _green(raiz, *args):
    """Chama uma função do green-cache vendorado. Devolve (rc, saída limpa)."""
    cmd = ". %s; %s" % (_aspas(GREEN), " ".join(_aspas(a) for a in args))
    rc, out = _roda(cmd, raiz, 60)
    return (1 if rc is None else rc), out.strip()


def _aspas(s):
    return "'%s'" % str(s).replace("'", "'\\''")


def _tail(texto, n=400):
    t = (texto or "").strip()
    return t[-n:] if t else "(sem saída)"


def passada3(raiz, suite_cmd=None, gate_cmd=None, planos=None, alvo=None,
             teto_suite=3600, teto_gate=90, rodadas=1):
    """O pré-flight da CASA, medido por execução. Não escreve nada no plano.

    `suite_cmd` é a esteira inteira (neste repositório, `bash scripts/suite.sh`);
    `gate_cmd`, o portão que responde no commit. Mesma saída das outras passadas:
    `perguntas` (porta fechada — não larga) e `registrados`.
    """
    achados = []
    passo = {"id": "largada"}
    arvore_antes = _green(raiz, "green_tree_hash", raiz)[1]

    if not str(suite_cmd or "").strip():
        achados.append(_achado(passo, "esteira", BLOQUEANTE,
                               "a largada não declara o comando da esteira — qual é o "
                               "comando que roda a suíte inteira deste projeto?",
                               "suiteCmd vazio"))
    else:
        vereditos, saida = [], ""
        for _ in range(max(1, int(rodadas))):
            rc, saida = _roda(suite_cmd, raiz, teto_suite)
            vereditos.append(rc)
        rc = vereditos[-1]
        if rc is None:
            achados.append(_achado(passo, "esteira", BLOQUEANTE,
                                   "a esteira não terminou em %ds — o teto sobe ou a "
                                   "esteira encolhe?" % teto_suite,
                                   "%s: estourou o teto" % suite_cmd))
        elif rc != 0:
            achados.append(_achado(passo, "esteira", BLOQUEANTE,
                                   "a esteira está VERMELHA na árvore da largada — "
                                   "conserta antes de largar, ou a largada segue com a "
                                   "suíte quebrada?",
                                   "%s: rc=%d\n%s" % (suite_cmd, rc, _tail(saida))))
        m = _MEDIDAS.search(saida or "")
        if m is None:
            achados.append(_achado(passo, "suite_mede", ADIAVEL,
                                   "a esteira não disse quantas suítes mediu — dá para "
                                   "confiar no veredito dela?",
                                   "saída sem contagem: %s" % _tail(saida, 200)))
        elif int(m.group(1)) == 0:
            achados.append(_achado(passo, "suite_mede", BLOQUEANTE,
                                   "o comando da esteira mediu ZERO suítes e saiu verde "
                                   "— o comando está errado (glob vazio) ou o projeto "
                                   "não tem suíte?",
                                   "%s: %s" % (suite_cmd, _tail(saida, 200))))
        if len(vereditos) > 1 and len(set(vereditos)) > 1:
            achados.append(_achado(passo, "veredito_estavel", BLOQUEANTE,
                                   "a mesma esteira deu vereditos DIFERENTES em %d "
                                   "rodadas seguidas — larga com suíte instável ou "
                                   "estabiliza antes?" % len(vereditos),
                                   "vereditos: %s" % vereditos))
        elif len(vereditos) == 1:
            achados.append(_achado(passo, "veredito_estavel", ADIAVEL,
                                   "a estabilidade do veredito não foi medida (uma "
                                   "rodada só) — vale rodar `--flake` antes da largada?",
                                   "rodadas=1"))

    # A PROVA VIAJA COM A ÁRVORE: a esteira só grava quando a árvore ficou parada, e
    # a chave da prova é o hash de AGORA. Sem prova para esta foto, o verde que
    # existir é de outro estado do disco — emprestado.
    arvore = _green(raiz, "green_tree_hash", raiz)[1]
    if _green(raiz, "green_cache_check", raiz, "full")[0] != 0:
        achados.append(_achado(passo, "prova_da_arvore", BLOQUEANTE,
                               "não existe prova de esteira verde para a árvore desta "
                               "largada — roda a esteira inteira com a árvore parada, "
                               "ou larga sem prova?",
                               "árvore %s: sem registro no green-cache"
                               % (arvore or "(hash ilegível)")))
    elif arvore_antes and arvore and arvore_antes != arvore:
        achados.append(_achado(passo, "prova_da_arvore", BLOQUEANTE,
                               "a árvore MUDOU durante a medição — o que foi medido não "
                               "é o que vai rodar; mede de novo com a árvore parada?",
                               "antes %s · depois %s" % (arvore_antes[:7], arvore[:7])))

    if str(gate_cmd or "").strip():
        rc, out = _roda(gate_cmd, raiz, teto_gate)
        if rc is None:
            achados.append(_achado(passo, "gate_de_commit", BLOQUEANTE,
                                   "o gate de commit não respondeu em %ds — cada commit "
                                   "da largada vai pendurar; sobe o teto ou conserta o "
                                   "gate?" % teto_gate,
                                   "%s: estourou o teto" % gate_cmd))
        elif rc != 0:
            achados.append(_achado(passo, "gate_de_commit", BLOQUEANTE,
                                   "o gate de commit REPROVA a árvore como ela está — "
                                   "nenhum commit da largada vai passar; conserta antes?",
                                   "%s: rc=%d\n%s" % (gate_cmd, rc, _tail(out))))

    if planos:
        try:
            pick_plan(planos, alvo)
        except Exception as exc:  # PlanError e afins: o texto é a prova
            achados.append(_achado(passo, "alvo_da_largada", BLOQUEANTE,
                                   "a largada não tem um alvo resolvível — diz qual "
                                   "plano ela executa?", str(exc)))

    perguntas, registrados = [], []
    for a in achados:
        seladas = consultar(raiz, a["pergunta"])
        if seladas:
            a["respondida_por"] = seladas[0]
            registrados.append(a)
        elif a["classe"] == BLOQUEANTE:
            perguntas.append(a)
        else:
            registrados.append(a)
    return {"arvore": arvore, "achados": achados, "perguntas": perguntas,
            "registrados": registrados}


# ── PASSADA 4 · A VIZINHANÇA (F22.4) ────────────────────────────────────────
# As três passadas anteriores olham o plano e a casa como se a máquina fosse só
# dela. Não é: outro motor pode estar de pé na MESMA árvore, uma guarda de
# PreToolUse pode negar por texto o comando que o passo vai rodar, um passo pode
# depender de coisa que não está nesta máquina (CI, credencial, aprovação), e dois
# passos podem disputar a mesma porta. Nada disso aparece lendo o passo sozinho.
#
# A guarda NÃO é adivinhada por leitura do script: ela é MEDIDA — o payload do
# passo entra por stdin no hook de verdade e o veredito é o que ele responde. Só
# matcher de Bash/edição roda aqui; `Agent` fica de fora de propósito, porque o
# gate do motor ARMA sinal quando consultado e o pré-check não escreve estado.

_COMANDO = re.compile(r"`([^`\n]{3,120})`")
_RECURSO = re.compile(
    r"\b(CI\b|GitHub Actions|pipeline|credencial|token de acesso|chave de API"
    r"|/plugin\b|App Store|VPN|conta paga|aprova[çc][ãa]o d[oa])", re.I)
_PORTA = re.compile(r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d{2,5})"
                    r"|(?<![\w.]):(\d{4,5})(?![\w.])")
_EXCLUSIVO = re.compile(r"nunca duas [^.\n]*ao mesmo tempo"
                        r"|uma [^.\n]{1,40} por vez"
                        r"|nunca [^.\n]{1,40} em paralelo", re.I)
_DENY = re.compile(r'"permissionDecision"\s*:\s*"deny"')
_TOOL_CMD = ("Bash",)
_TOOL_ARQ = ("Edit", "Write", "MultiEdit")


def _comandos(passo):
    """Os comandos citados entre crases no texto do passo."""
    out = []
    for c in _COMANDO.findall(_texto(passo)):
        c = c.strip()
        if re.match(r"^[a-z][a-z0-9_.-]*(\s|$)", c) and (" " in c or "/" in c):
            out.append(c)
    return out


def _guardas(raiz):
    """As guardas de PreToolUse dos plugins da árvore: (raiz_do_plugin, cmd, tool)."""
    fora = []
    import glob as _glob
    for arq in sorted(_glob.glob(os.path.join(raiz, "plugins", "*", "hooks", "hooks.json"))):
        try:
            with open(arq, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        proot = os.path.dirname(os.path.dirname(arq))
        for m in (d.get("hooks") or {}).get("PreToolUse") or []:
            tools = set(str(m.get("matcher") or "").split("|"))
            for h in m.get("hooks") or []:
                cmd = str(h.get("command") or "").strip()
                if not cmd:
                    continue
                for t in _TOOL_CMD + _TOOL_ARQ:
                    if t in tools:
                        fora.append((proot, cmd, t))
    return fora


def _pergunta_a_guarda(proot, cmd, tool, entrada, raiz, teto):
    """Roda a guarda de verdade com o payload do passo. Devolve a saída, ou None."""
    payload = json.dumps({"tool_name": tool, "cwd": raiz,
                          "session_id": "precheck-largada", "tool_input": entrada})
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=proot, CLAUDE_PROJECT_DIR=raiz)
    try:
        r = subprocess.run(cmd, cwd=raiz, shell=True, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=teto,
                           input=payload, env=env, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return (r.stdout or "") + (r.stderr or "")


def _reservas_na_arvore(raiz, base_estado, agora):
    """Reserva de arquivo VIVA apontando para dentro desta árvore: (sid, motor, arqs).

    Reusa o estado que `reserva-de-arquivos.sh` já escreve (`reservas/<sid>__<motor>.files`)
    e o mesmo teto de idade do sinal (`andamento.TTL_SINAL_MIN`): reserva expirada é
    motor morto, e motor morto não disputa nada.
    """
    import glob as _glob
    fora = []
    for arq in sorted(_glob.glob(os.path.join(base_estado, "reservas", "*.files"))):
        try:
            if agora - os.path.getmtime(arq) > andamento.TTL_SINAL_MIN * 60:
                continue
            with open(arq, encoding="utf-8") as fh:
                linhas = [ln.strip() for ln in fh if ln.strip()]
        except OSError:
            continue
        sid, _, motor = os.path.basename(arq)[:-len(".files")].partition("__")
        meus = []
        for ln in linhas:
            # Caminho RELATIVO na reserva pode ser de outro projeto: só conta o que
            # existe AQUI. Absoluto já diz de qual árvore fala.
            if not os.path.isabs(ln) and not os.path.exists(os.path.join(raiz, ln)):
                continue
            alvo = ln if os.path.isabs(ln) else os.path.join(raiz, ln)
            if os.path.realpath(alvo).startswith(os.path.realpath(raiz) + os.sep):
                meus.append(os.path.relpath(os.path.realpath(alvo),
                                            os.path.realpath(raiz)))
        if meus:
            fora.append((sid, motor, sorted(set(meus)), arq))
    return fora


def _pid(linha):
    """O pid que abre uma linha de `ps -eo pid=,args=`, ou -1."""
    try:
        return int(linha.split()[0])
    except (IndexError, ValueError):
        return -1


def _ancestrais():
    """Os pids deste processo e dos que o lançaram — eles não são a vizinhança."""
    pids, pid = set(), os.getpid()
    for _ in range(20):
        pids.add(pid)
        _, out = _roda("ps -o ppid= -p %d" % pid, ".", 10)
        try:
            pid = int((out or "").strip())
        except ValueError:
            break
        if pid <= 1:
            break
    return pids


def passada4(plano, raiz, base_estado=None, teto_guarda=15, agora=None):
    """A passada sobre a VIZINHANÇA — quem mais está de pé em volta desta largada.

    Mesma saída das outras: `perguntas` e `registrados`. Não escreve nada.
    """
    agora = time.time() if agora is None else agora
    base_estado = base_estado or andamento.ESTADO
    passos = list(_abertos(plano))
    achados = []

    # 1 · motor/sessão viva na MESMA árvore (sinal de andamento + reserva de arquivo).
    meus_arquivos = set()
    for p in passos:
        meus_arquivos |= _arquivos(p)
    for sid, motor, arqs, arq in _reservas_na_arvore(raiz, base_estado, agora):
        vivo = os.path.exists(os.path.join(base_estado, "ativo-%s" % sid))
        cruza = sorted(meus_arquivos.intersection(arqs))
        classe = BLOQUEANTE if (vivo and cruza) else ADIAVEL
        achados.append(_achado(
            {"id": "largada"}, "motor_vivo", classe,
            "o motor %s já está de pé nesta mesma árvore e reservou %s%s — espera ele "
            "terminar, ou as duas largadas dividem os arquivos?"
            % (motor or "?", arqs[0], " (que este plano também toca)" if cruza else ""),
            "%s: %s%s" % (arq, ", ".join(arqs[:5]),
                          " · ativo-%s aceso" % sid if vivo else " · sem aviso aceso")))

    # 2 · guarda de PreToolUse que NEGA, medida com o payload dos passos abertos.
    guardas = _guardas(raiz)
    vistos = set()
    for p in passos:
        pid = str(p.get("id") or "?")
        alvos = [("command", c) for c in _comandos(p)]
        alvos += [("file_path", c) for c in sorted(_arquivos(p))]
        for campo, valor in alvos:
            for proot, cmd, tool in guardas:
                if (campo == "command") != (tool in _TOOL_CMD):
                    continue
                chave = (proot, cmd, tool, valor)
                if chave in vistos:
                    continue
                vistos.add(chave)
                entrada = {campo: valor}
                if campo == "file_path":
                    entrada["path"] = valor
                saida = _pergunta_a_guarda(proot, cmd, tool, entrada, raiz, teto_guarda)
                if saida and _DENY.search(saida):
                    achados.append(_achado(
                        p, "guarda_nega", BLOQUEANTE,
                        "a guarda de %s nega %s antes de o passo %s começar — o passo "
                        "muda de caminho, ou a guarda sai do caminho dele?"
                        % (os.path.basename(proot), valor, pid),
                        "%s (%s): %s" % (cmd.split(";")[-1].strip(), tool,
                                         _tail(saida, 240))))

    # 3 · recurso externo exigido pelo passo sem espera declarada.
    for p in passos:
        if str(p.get("espera_dono") or "").strip():
            continue
        m = _RECURSO.search(_texto(p))
        if m:
            achados.append(_achado(
                p, "recurso_externo", BLOQUEANTE,
                "o passo depende de %s, que não está nesta máquina, e não declara "
                "espera — você libera o recurso antes, ou o passo declara a espera?"
                % m.group(0), _texto(p).strip()[:200]))

    # 4 · porta fixa compartilhada por dois passos abertos.
    portas = {}
    for p in passos:
        for a, b in _PORTA.findall(_texto(p)):
            portas.setdefault(a or b, set()).add(str(p.get("id") or "?"))
    for porta, quem in sorted(portas.items()):
        if len(quem) > 1:
            achados.append(_achado(
                {"id": sorted(quem)[0]}, "porta_compartilhada", BLOQUEANTE,
                "os passos %s citam a MESMA porta %s — o segundo a subir morre com "
                "porta ocupada; serializa os dois ou dá porta própria a cada um?"
                % (", ".join(sorted(quem)), porta),
                "porta %s citada em: %s" % (porta, ", ".join(sorted(quem)))))

    # 5 · a regra escrita no CLAUDE.md ("nunca duas suítes ao mesmo tempo") vira
    #     checagem de `ps`: se a regra existe e o processo JÁ está de pé, não larga.
    import glob as _glob
    regra = None
    for arq in [os.path.join(raiz, "CLAUDE.md")] + sorted(
            _glob.glob(os.path.join(raiz, "*", "CLAUDE.md"))):
        try:
            with open(arq, encoding="utf-8", errors="replace") as fh:
                m = _EXCLUSIVO.search(fh.read())
        except OSError:
            continue
        if m:
            regra = (arq, m.group(0))
            break
    if regra:
        rc, ps = _roda("ps -eo pid=,args=", raiz, 15)
        # O PRÓPRIO PROCESSO NÃO É O VIZINHO. Quem chama o pré-check costuma ser um
        # shell cuja linha de comando CITA a esteira — sem tirar a nossa árvore da
        # frente, a checagem acusaria a si mesma toda vez.
        meus = _ancestrais()
        linhas = [ln for ln in (ps or "").splitlines()
                  if "ps -eo" not in ln and _pid(ln) not in meus]
        for p in passos:
            for c in _comandos(p):
                alvo = os.path.basename(c.split()[-1]) if "/" in c else c.split()[0]
                linha = next((ln for ln in linhas if alvo and alvo in ln), None)
                if linha:
                    achados.append(_achado(
                        p, "exclusividade", BLOQUEANTE,
                        "a regra de %s diz \"%s\" e JÁ existe um `%s` de pé nesta "
                        "máquina — espera o que está rodando, ou larga por cima?"
                        % (os.path.relpath(regra[0], raiz), regra[1], alvo),
                        linha.strip()[:200]))

    perguntas, registrados = [], []
    for a in achados:
        seladas = consultar(raiz, a["pergunta"])
        if seladas:
            a["respondida_por"] = seladas[0]
            registrados.append(a)
        elif a["classe"] == BLOQUEANTE:
            perguntas.append(a)
        else:
            registrados.append(a)
    return {"passos_abertos": [str(p.get("id")) for p in passos],
            "achados": achados, "perguntas": perguntas, "registrados": registrados}


# ── NEBLINA · a suspeita que não vira pergunta (F22.9) ──────────────────────
# Nem toda suspeita tem forma de pergunta. A que não tem só tinha dois destinos:
# ir ao dono como neblina ("acho que tem algo aqui") — e ele não tem o que
# responder —, ou sumir da rodada e voltar como surpresa no meio da corrida.
# O terceiro destino é este: REGISTRO. Fora do plugin (`${CLAUDE_PLUGIN_ROOT}` é
# cache reescrito a cada bump), na casa do projeto, no mesmo molde de
# `decisoes-seladas.md`: uma linha por suspeita, grep-ável, inteira numa linha só.
#
# O teste da pergunta precisa, as três exigências: aponta UM passo, termina em
# pergunta de verdade, e carrega a prova visível. Falhou qualquer uma ⇒ neblina.

NEBLINA = os.path.join(".claude", "neblina.md")

CABECALHO_NEBLINA = """\
# Neblina

Suspeita que não passou no teste da pergunta precisa (passo nomeado + pergunta de
verdade + prova visível). Uma linha por suspeita, a frase inteira NA MESMA LINHA.
O loop só fecha com esta lista vazia, ou com cada item declarado FORA DE ESCOPO.
"""

_FORA = " — fora de escopo: "


def pergunta_precisa(achado):
    """O que falta para a suspeita ser pergunta. `[]` = passa no teste."""
    faltas = []
    if not str(achado.get("passo") or "").strip() or str(achado.get("passo")) == "?":
        faltas.append("não aponta passo nenhum")
    pergunta = str(achado.get("pergunta") or "").strip()
    if len(pergunta) < 20 or "?" not in pergunta:
        faltas.append("não é pergunta de verdade")
    if not str(achado.get("prova") or "").strip():
        faltas.append("não traz prova visível")
    return faltas


def casa_da_neblina(raiz):
    return os.path.join(raiz, NEBLINA)


def _linhas_de_neblina(raiz):
    arq = casa_da_neblina(raiz)
    if not os.path.isfile(arq):
        return []
    with open(arq, encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f if ln.startswith("- [")]


def anotar_neblina(raiz, suspeita, motivo, passo="?", data=None):
    """Grava UMA linha de neblina. Devolve a linha (ou a já existente — sem dobro)."""
    suspeita = " ".join(str(suspeita or "").split())
    if not suspeita or not str(motivo or "").strip():
        raise ValueError("neblina sem suspeita ou sem motivo não registra nada")
    data = data or time.strftime("%Y-%m-%d")
    linha = '- [%s] "%s" — passo: %s — sem forma: %s' % (
        data, suspeita, str(passo or "?").strip(), str(motivo).strip())
    for existente in _linhas_de_neblina(raiz):
        if '"%s"' % suspeita in existente:
            return existente
    arq = casa_da_neblina(raiz)
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    novo = not os.path.isfile(arq)
    with open(arq, "a", encoding="utf-8") as f:
        if novo:
            f.write(CABECALHO_NEBLINA + "\n")
        f.write(linha + "\n")
    return linha


def neblina_aberta(raiz):
    """As linhas que ninguém declarou fora de escopo — as que ainda seguram o fecho."""
    return [ln for ln in _linhas_de_neblina(raiz) if _FORA not in ln]


def declarar_fora_de_escopo(raiz, suspeita, motivo):
    """Marca a linha da suspeita como fora de escopo. `False` = não existe tal linha."""
    suspeita = " ".join(str(suspeita or "").split())
    if not str(motivo or "").strip():
        raise ValueError("fora de escopo sem motivo não declara nada")
    arq = casa_da_neblina(raiz)
    if not os.path.isfile(arq):
        return False
    with open(arq, encoding="utf-8") as f:
        linhas = f.readlines()
    achou = False
    for i, ln in enumerate(linhas):
        if ln.startswith("- [") and '"%s"' % suspeita in ln and _FORA not in ln:
            linhas[i] = ln.rstrip("\n") + _FORA + str(motivo).strip() + "\n"
            achou = True
    if achou:
        with open(arq, "w", encoding="utf-8") as f:
            f.writelines(linhas)
    return achou


def triar(raiz, achados, data=None):
    """Separa o que vira pergunta do que vira neblina. A neblina é GRAVADA aqui.

    O achado que não passa no teste da pergunta precisa sai da fila do dono e entra
    no registro — nunca some, nunca chega a ele como "acho que tem algo aqui".
    """
    perguntas, neblina = [], []
    for a in achados:
        faltas = pergunta_precisa(a)
        if not faltas:
            perguntas.append(a)
            continue
        motivo = "; ".join(faltas)
        suspeita = str(a.get("pergunta") or a.get("prova") or a.get("check") or "").strip()
        linha = anotar_neblina(raiz, suspeita or str(a.get("check") or "suspeita"),
                               motivo, a.get("passo"), data)
        neblina.append(dict(a, sem_forma=faltas, linha=linha))
    return {"perguntas": perguntas, "neblina": neblina}


def pode_fechar(raiz):
    """O fecho do loop: `(True, [])` só com neblina vazia ou toda fora de escopo."""
    abertas = neblina_aberta(raiz)
    return (not abertas), abertas


# ── RODADA N+1 · a que parte das RESPOSTAS (F22.7) ──────────────────────────
# A rodada seguinte NÃO re-varre o plano: varrer de novo devolve as mesmas sete
# checagens sobre o mesmo texto e o loop nunca fecha. O insumo dela é o que o dono
# RESPONDEU, e a leitura de cada resposta é uma pergunta só, em três partes: o que
# ela CONFIRMOU (o achado morre ali), o que DESCONFIRMOU (a prova da rodada
# anterior caiu — o passo tem que ser reescrito) e o que REVELOU de novo (nome que
# não estava na rodada N e agora entra). Confirmação pura não gera pergunta — é
# exatamente assim que o loop chega ao fim.

_DESCONFIRMA = re.compile(
    r"\b(n[ãa]o\b|nenhum\w*|nada disso|errad\w+|na verdade|pelo contr[áa]rio"
    r"|deixou de|nunca (?:foi|existiu))", re.I)


def _revelado(resposta, conhecido):
    """Nome concreto que a resposta cita e a rodada anterior não conhecia."""
    novos = []
    for rx in (_CAMINHO, _COMANDO):
        for nome in rx.findall(resposta):
            nome = nome.strip()
            if nome and nome not in conhecido and nome not in novos:
                novos.append(nome)
    return novos


def rodada_seguinte(raiz, respostas):
    """A rodada N+1, feita das RESPOSTAS da rodada N. Não lê o plano.

    Cada item de `respostas` é o achado da rodada anterior com a resposta do dono
    colada: `{"passo", "pergunta", "prova", "resposta"}`. Devolve a `leitura` de
    cada uma (confirmou / desconfirmou / revelou), as `perguntas` decorrentes e
    `fechou` — verdadeiro quando nenhuma resposta gerou decorrência.
    """
    achados, leitura = [], []
    for r in respostas:
        passo = {"id": r.get("passo") or "?"}
        resposta = " ".join(str(r.get("resposta") or "").split())
        conhecido = "%s %s" % (r.get("pergunta") or "", r.get("prova") or "")
        desconfirmou = bool(_DESCONFIRMA.search(resposta))
        revelou = _revelado(resposta, conhecido)
        leitura.append({"passo": passo["id"], "resposta": resposta,
                        "desconfirmou": desconfirmou, "revelou": revelou,
                        "confirmou": not desconfirmou and not revelou})
        if desconfirmou:
            achados.append(_achado(
                passo, "desconfirmado", BLOQUEANTE,
                "a resposta derruba a prova que sustentava o achado anterior — o "
                "passo continua de pé como está escrito, ou é reescrito?",
                "prova da rodada anterior: %s\nresposta: %s"
                % (r.get("prova") or "(sem prova)", resposta)))
        for nome in revelou:
            achados.append(_achado(
                passo, "revelado", BLOQUEANTE,
                "a resposta trouxe %s, que não estava na rodada anterior — o passo "
                "passa a depender disso, ou isso fica fora da largada?" % nome,
                "resposta: %s" % resposta))

    perguntas, registrados = [], []
    for a in achados:
        seladas = consultar(raiz, a["pergunta"])
        if seladas:
            a["respondida_por"] = seladas[0]
            registrados.append(a)
        else:
            perguntas.append(a)
    return {"leitura": leitura, "achados": achados, "perguntas": perguntas,
            "registrados": registrados, "fechou": not perguntas}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plano", help="o .plan.json a varrer")
    ap.add_argument("--raiz", default=".", help="a raiz do projeto (disco e registro)")
    ap.add_argument("--passada", choices=("1", "2", "3", "4"), default="1",
                    help="1 = item a item (padrão); 2 = a sequência; 3 = a casa; "
                         "4 = a vizinhança")
    ap.add_argument("--suite", default="bash scripts/suite.sh",
                    help="o comando da esteira INTEIRA (passada 3)")
    ap.add_argument("--gate", default="", help="o gate de commit (passada 3)")
    args = ap.parse_args(argv)
    with open(args.plano, encoding="utf-8") as f:
        plano = json.load(f)
    if args.passada == "3":
        r = passada3(args.raiz, suite_cmd=args.suite, gate_cmd=args.gate,
                     planos=os.path.dirname(os.path.abspath(args.plano)),
                     alvo=plano.get("id"))
    elif args.passada == "4":
        r = passada4(plano, args.raiz)
    else:
        r = (passada1 if args.passada == "1" else passada2)(plano, args.raiz)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 1 if r["perguntas"] else 0


if __name__ == "__main__":
    sys.exit(main())
