#!/usr/bin/env python3
"""medidor.py — o que cada PAPEL do run custou, lido do transcript e não do relatório.

O relatório do motor conta o que ele sabe que fez. O gasto mora noutro lugar: um
`agent-<id>.jsonl` por agente, uma linha por evento, e o `message.usage` de cada
resposta. Duas armadilhas, e as duas fazem o número mentir:

  papel     — o transcript não diz o papel do agente em campo nenhum. Ele está na
              PRIMEIRA linha (o prompt que o motor montou), DECLARADO como
              `PAPEL: <NOME>`; run antigo, que não declara, ainda cai no palpite
              pela frase. É por papel que a comparação faz sentido: um agente caro
              entre 50 não diz nada.
  streaming — a mesma resposta aparece em VÁRIAS linhas, todas com o mesmo
              `requestId` e o mesmo `usage`. Somar linha a linha infla o gasto em
              3-5×. Um turno é um `requestId`, e vale a ÚLTIMA linha dele (só ela
              tem o `output_tokens` final).

A métrica que importa não é token por agente, é TURNO por agente: o cache_read
relê tudo a cada turno, então turno é a causa e token é a consequência.

    python3 medidor.py [<run>] [--json]

O <run> é o caminho do diretório OU o ID dele (`wf_…`); sem nenhum, mede o run
mais recente DESTE projeto. Run que mora na pasta de outro projeto é RECUSADO
pelo id: foi o defeito de 2026-08-15 — o mais recente do disco era de outra
missão, e a leitura apontou arquivos que não existem aqui. Sem run nenhum no
disco, o comando diz isso e para — medir o run errado é pior do que não medir.
"""

import argparse
import glob
import json
import os
import re
import sys
import unicodedata

CAMPOS = ("input_tokens", "output_tokens",
          "cache_creation_input_tokens", "cache_read_input_tokens")

# O papel DECLARADO pelo motor (S-123): o prompt abre com `PAPEL: <NOME>` e é ele
# que manda. Adivinhar o papel pela frase ("Você é o X") funcionava só enquanto
# ninguém reescrevesse o texto do motor — e reescrever texto é o que mais acontece
# aqui. Os marcadores abaixo continuam como resgate do run antigo, que não declara.
_DECLARADO = re.compile(r"PAPEL:\s*([A-Z][A-Z0-9_]{2,})")

# Papel que não se anuncia com "Você é o X" — marcadores do motor deste repo,
# conforme .claude/specs/metodo-autopsia-de-workflow.md.
MARCADORES = (
    ("PAPEL MECANICO", "MECANICO"),
    ("GRAVE NO PLANO", "MARCAR"),
    ("RODE A SUITE", "SUITE"),
)

# Papel mecânico roda UM comando: acima deste teto ele está tentando de novo,
# procurando alguma coisa ou falhando — foi o defeito de 2026-08-08 (8 turnos × 38).
PAPEIS_MECANICOS = frozenset(papel for _, papel in MARCADORES)
TETO_TURNOS_MECANICO = 2

# Mesmo comando em 3 agentes distintos não é coincidência: é cada um redescobrindo
# sozinho o que o anterior já descobriu (a arqueologia repetida 38× de 2026-08-08).
TETO_AGENTES_REPETINDO = 3

# A raiz de onde um comando invocou um plugin. Duas raízes no mesmo run = tem cópia
# do projeto sendo executada no lugar da árvore. O olhar-para-trás é o que separa o
# caminho de verdade do PEDAÇO de caminho: sem ele, `~/.claude/plugins/*` de um grep
# vira a "raiz" `/.claude` e o sinal acusa quem não fez nada.
_RAIZ_PLUGINS = re.compile(r"(?<![\w/.~-])(/[^\s'\";|*]*?)/plugins/[A-Za-z0-9_.-]+/")

TITULOS = {
    "voltas_demais": "papel mecânico acima do teto de turnos — está procurando, não gravando",
    "comando_repetido": "o mesmo comando redescoberto por vários agentes",
    "caminho_fantasma": "comando executou plugin de fora da árvore do projeto",
    "trabalho_fantasma": "trabalho sobre passo que já tinha saído da fila esperando o dono",
    "resultado_vazio": "agente que voltou sem valor de retorno — pago e sem entrega",
    "agente_morto": "agente que começou e nunca registrou resultado",
}

_PREFIXO = re.compile(r"voc[eê]\s+[eé]\s+[oa]\s+", re.IGNORECASE)
_NOME = re.compile(r"[A-Z]{3,}")


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def papel_do_prompt(texto):
    """O papel DECLARADO ganha de tudo: `PAPEL: EXECUTOR` na abertura do prompt.

    Sem declaração (run gravado antes de o motor declarar), cai no palpite pela
    frase: "Você é o EXECUTOR (Sonnet)…" → EXECUTOR, sendo o nome do papel a
    primeira palavra TODA MAIÚSCULA depois do "você é o"; depois, os marcadores.
    Nada disso casando, o papel sai como DESCONHECIDO — nunca inventado.
    """
    sem_acento = _sem_acento(texto)
    declarado = _DECLARADO.search(sem_acento)
    if declarado:
        return declarado.group(1)
    m = _PREFIXO.search(texto)
    if m:
        nome = _NOME.match(_sem_acento(texto[m.end():]))
        if nome:
            return nome.group(0)
    alto = _sem_acento(texto).upper()
    for marcador, papel in MARCADORES:
        if marcador in alto:
            return papel
    return "DESCONHECIDO"


def ler_jsonl(caminho):
    """(eventos, nº da última linha que não fechou). Run interrompido é o caso
    comum: o arquivo para no meio de uma linha, e ela não vira evento. O que não
    pode acontecer é o número sair como se estivesse inteiro — por isso a linha
    cortada volta junto, para ser NOMEADA em vez de sumir."""
    eventos, cortada = [], None
    with open(caminho, encoding="utf-8", errors="replace") as fh:
        for n_linha, linha in enumerate(fh, 1):
            linha = linha.strip()
            if not linha:
                continue
            try:
                eventos.append((n_linha, json.loads(linha)))
            except ValueError:
                cortada = n_linha
    return eventos, cortada


def medir_agente(caminho):
    """Um agente: papel, turnos e tokens. Turno = requestId distinto, contado
    pela ÚLTIMA linha dele — as anteriores são o mesmo turno em streaming."""
    prompt = ""
    ultima = {}   # requestId → usage da linha mais recente
    ordem = []
    inicio = {}   # requestId → nº da linha onde o turno começa (1-indexado)
    comandos = []  # (comando, nº da linha) de cada Bash que o agente disparou
    eventos, cortada = ler_jsonl(caminho)
    for n_linha, ev in eventos:
        msg = ev.get("message") or {}
        if not prompt and ev.get("type") == "user":
            conteudo = msg.get("content")
            prompt = conteudo if isinstance(conteudo, str) else json.dumps(conteudo)
        blocos = msg.get("content")
        for bloco in blocos if isinstance(blocos, list) else ():
            if (isinstance(bloco, dict) and bloco.get("type") == "tool_use"
                    and bloco.get("name") == "Bash"):
                cmd = (bloco.get("input") or {}).get("command")
                if cmd:
                    comandos.append((cmd, n_linha))
        uso = msg.get("usage")
        if ev.get("type") == "assistant" and isinstance(uso, dict):
            chave = ev.get("requestId") or msg.get("id") or ev.get("uuid")
            if chave not in ultima:
                ordem.append(chave)
                inicio[chave] = n_linha
            ultima[chave] = uso

    tokens = {c: 0 for c in CAMPOS}
    for chave in ordem:
        for c in CAMPOS:
            tokens[c] += ultima[chave].get(c, 0) or 0
    tokens["total"] = sum(tokens[c] for c in CAMPOS)
    return {
        "agente": os.path.basename(caminho)[len("agent-"):-len(".jsonl")],
        "papel": papel_do_prompt(prompt),
        "turnos": len(ordem),
        "tokens": tokens,
        # o endereço, não o conteúdo: quem lê abre o arquivo nessa linha.
        "arquivo": os.path.abspath(caminho),
        "linhas_dos_turnos": [inicio[c] for c in ordem],
        "comandos": comandos,
        # nº da linha em que o arquivo parou no meio, ou None se fechou inteiro
        "cortado": cortada,
    }


def eventos_do_journal(dir_run):
    """(eventos, nº da linha cortada). Journal ausente é ([], None): run que nunca
    teve journal não é run cortado."""
    caminho = os.path.join(dir_run, "journal.jsonl")
    if not os.path.isfile(caminho):
        return [], None
    eventos, cortada = ler_jsonl(caminho)
    return [ev for _, ev in eventos], cortada


def sinais_do_journal(evs):
    """Os três sinais que só o journal conta:

    vazio      — agente que voltou sem valor de retorno; pago e sem entrega.
    morto      — agente que começou e nunca registrou resultado nenhum.
    fantasma   — passo que saiu da fila esperando o dono e MESMO ASSIM recebeu
                 trabalho depois. O motor não distingue quem falhou de quem nunca
                 foi tentado, e o passo parado volta como faltante.
    """
    vazios, mortos, fantasma = [], [], []
    iniciados, concluidos, esperando = [], set(), set()
    for ev in evs:
        aid = ev.get("agentId")
        if ev.get("type") == "started":
            iniciados.append(aid)
        elif ev.get("type") == "result":
            concluidos.add(aid)
            r = ev.get("result")
            if not r:
                vazios.append(aid)
                continue
            tid = r.get("task_id") if isinstance(r, dict) else None
            if not tid:
                continue
            if r.get("espera"):
                esperando.add(tid)
            elif tid in esperando:
                fantasma.append({"task_id": tid, "agente": aid})
    mortos = [a for a in iniciados if a not in concluidos]
    return vazios, mortos, fantasma


def falhas_do_journal(evs):
    """agentId de todo agente que o registro do run diz que NÃO entregou: começou
    e nunca voltou, voltou sem valor, ou voltou dizendo que não fechou. É a outra
    metade do par — turno publicado sozinho faz o motor otimizar turno, e cortar
    turno às custas de entrega passaria como melhora."""
    falhos = set()
    for ev in evs:
        aid = ev.get("agentId")
        if ev.get("type") != "result":
            continue
        r = ev.get("result")
        # parar no teto e devolver `espera` é combinado, não falha.
        if not r or (isinstance(r, dict) and r.get("done") is False
                     and not r.get("espera")):
            falhos.add(aid)
    vazios, mortos, _ = sinais_do_journal(evs)
    return falhos | set(vazios) | set(mortos)


def resultados_vazios(dir_run):
    """journal.jsonl: agente que voltou sem valor de retorno."""
    return sinais_do_journal(eventos_do_journal(dir_run)[0])[0]


def sinal_comando_repetido(agentes):
    """O mesmo comando disparado por agentes DIFERENTES: cada um redescobrindo o
    que o anterior já descobriu. Sinal de conhecimento que não circula."""
    por_comando = {}
    for a in agentes:
        for cmd, linha in a["comandos"]:
            por_comando.setdefault(cmd, []).append((a, linha))
    casos = []
    for cmd, ocorrencias in por_comando.items():
        distintos = {a["agente"] for a, _ in ocorrencias}
        if len(distintos) >= TETO_AGENTES_REPETINDO:
            a, linha = ocorrencias[0]
            casos.append({"comando": cmd.splitlines()[0][:120], "agentes": len(distintos),
                          "vezes": len(ocorrencias), "arquivo": a["arquivo"], "linha": linha})
    return sorted(casos, key=lambda c: (-c["agentes"], -c["vezes"]))


def sinal_caminho_fantasma(agentes):
    """De qual raiz cada comando invocou um plugin. A raiz mais usada é a árvore;
    qualquer outra é cópia velha do projeto virando caminho de execução."""
    por_raiz = {}
    for a in agentes:
        for cmd, linha in a["comandos"]:
            for m in _RAIZ_PLUGINS.finditer(cmd):
                por_raiz.setdefault(m.group(1), []).append((a, linha))
    if len(por_raiz) < 2:
        return []
    arvore = max(por_raiz, key=lambda r: len(por_raiz[r]))
    casos = []
    for raiz, ocorrencias in por_raiz.items():
        if raiz == arvore:
            continue
        a, linha = ocorrencias[0]
        casos.append({"raiz": raiz, "raiz_da_arvore": arvore, "vezes": len(ocorrencias),
                      "agentes": len({x["agente"] for x, _ in ocorrencias}),
                      "arquivo": a["arquivo"], "linha": linha})
    return sorted(casos, key=lambda c: -c["vezes"])


def ponteiro(agentes_do_papel, suspeito):
    """O endereço do trecho a abrir: o agente mais falador do papel, e a linha do
    turno que interessa — o 1º quando o papel está são, o primeiro turno ACIMA do
    teto quando é suspeito (é lá que a volta começa). Só endereço, sem conteúdo."""
    pior = max(agentes_do_papel, key=lambda a: (a["turnos"], a["tokens"]["total"]))
    linhas = pior["linhas_dos_turnos"]
    if not linhas:
        return None
    i = TETO_TURNOS_MECANICO if suspeito and len(linhas) > TETO_TURNOS_MECANICO else 0
    return {"agente": pior["agente"], "arquivo": pior["arquivo"],
            "linha": linhas[i], "turno": i + 1}


def medir_run(dir_run):
    agentes = [medir_agente(f) for f in sorted(glob.glob(os.path.join(dir_run, "agent-*.jsonl")))]
    evs_journal, journal_cortado = eventos_do_journal(dir_run)
    falhos = falhas_do_journal(evs_journal)
    papeis = {}
    do_papel = {}
    for a in agentes:
        p = papeis.setdefault(a["papel"], {"papel": a["papel"], "agentes": 0, "turnos": 0,
                                           "tokens": {c: 0 for c in CAMPOS + ("total",)}})
        do_papel.setdefault(a["papel"], []).append(a)
        p["agentes"] += 1
        p["turnos"] += a["turnos"]
        for c in p["tokens"]:
            p["tokens"][c] += a["tokens"][c]
    for p in papeis.values():
        p["turnos_por_agente"] = round(p["turnos"] / p["agentes"], 1)
        # o par: turno nunca sai sozinho. Sem journal não há registro de entrega,
        # e aí a taxa é None — inventar 0 diria "ninguém falhou" sem saber.
        p["falhas"] = sum(1 for a in do_papel[p["papel"]] if a["agente"] in falhos)
        p["taxa_falha"] = (round(p["falhas"] / p["agentes"], 2)
                           if evs_journal else None)
        p["suspeito"] = (p["papel"] in PAPEIS_MECANICOS
                         and p["turnos_por_agente"] > TETO_TURNOS_MECANICO)
        p["ponteiro"] = ponteiro(do_papel[p["papel"]], p["suspeito"])
    tabela = sorted(papeis.values(), key=lambda p: -p["tokens"]["total"])
    vazios, mortos, fantasma = sinais_do_journal(evs_journal)
    # O passo parado vem nomeado do journal; o que ele CUSTOU vem do transcript de
    # quem trabalhou nele. Nomear sem somar deixa o defeito com cara de detalhe —
    # e o motor reporta esse trabalho como legítimo.
    custo = {a["agente"]: a["tokens"]["total"] for a in agentes}
    for c in fantasma:
        c["tokens"] = custo.get(c["agente"], 0)
    sinais = [
        {"sinal": "voltas_demais",
         "casos": [{"papel": p["papel"], "turnos_por_agente": p["turnos_por_agente"],
                    **(p["ponteiro"] or {})} for p in tabela if p["suspeito"]]},
        {"sinal": "comando_repetido", "casos": sinal_comando_repetido(agentes)},
        {"sinal": "caminho_fantasma", "casos": sinal_caminho_fantasma(agentes)},
        {"sinal": "trabalho_fantasma", "casos": fantasma,
         "tokens": sum(c["tokens"] for c in fantasma)},
        {"sinal": "resultado_vazio", "casos": [{"agente": a} for a in vazios]},
        {"sinal": "agente_morto", "casos": [{"agente": a} for a in mortos]},
    ]
    for s in sinais:
        s["titulo"] = TITULOS[s["sinal"]]
    # Run interrompido no meio da escrita: o que deu para medir sai medido, e o
    # pedaço que faltou sai NOMEADO por arquivo e linha — número de run cortado
    # que se apresenta como inteiro é pior do que número nenhum.
    incompleto = [{"arquivo": a["arquivo"], "linha": a["cortado"]}
                  for a in agentes if a["cortado"]]
    if journal_cortado:
        incompleto.append({"arquivo": os.path.abspath(os.path.join(dir_run, "journal.jsonl")),
                           "linha": journal_cortado})
    for a in agentes:
        del a["comandos"]   # endereço sim, conteúdo de transcript não
    return {
        "run": os.path.basename(os.path.normpath(dir_run)),
        "papeis": tabela,
        "agentes": agentes,
        "sinais": sinais,
        "incompleto": incompleto,
        "resultados_vazios": vazios,
        "total": {
            "agentes": len(agentes),
            "turnos": sum(a["turnos"] for a in agentes),
            "tokens": sum(a["tokens"]["total"] for a in agentes),
        },
    }


def par_invertido(antes, depois):
    """Os papéis em que o turno CAIU e a falha SUBIU de um run para o outro: o
    motor deu menos voltas entregando menos. É a troca que a métrica vigiada faz
    sozinha, e ela só aparece no PAR — cada número, isolado, parece uma melhora."""
    velho = {p["papel"]: p for p in antes["papeis"]}
    casos = []
    for p in depois["papeis"]:
        v = velho.get(p["papel"])
        if not v or v["taxa_falha"] is None or p["taxa_falha"] is None:
            continue
        if (p["turnos_por_agente"] < v["turnos_por_agente"]
                and p["taxa_falha"] > v["taxa_falha"]):
            casos.append({"papel": p["papel"],
                          "turnos_por_agente": [v["turnos_por_agente"], p["turnos_por_agente"]],
                          "taxa_falha": [v["taxa_falha"], p["taxa_falha"]]})
    return casos


def _lar():
    return (os.environ.get("CLAUDE_CONFIG_DIR")
            or os.path.join(os.path.expanduser("~"), ".claude"))


def _base_runs():
    return os.path.join(_lar(), "projects")


def desligado(base=None):
    """A chave de desligar, como todo automatismo da casa: `off` escrito em
    `~/.claude/improve-workflow/mode` cala o medidor. A chave mora FORA do
    plugin porque o plugin é cache reescrito a cada bump — chave lá dentro
    voltaria a ligar sozinha na próxima atualização."""
    arq = os.path.join(base or _lar(), "improve-workflow", "mode")
    try:
        with open(arq, encoding="utf-8") as f:
            return f.read().strip() == "off"
    except OSError:
        return False


def projeto_atual(raiz=None):
    """A pasta que o Claude Code dá a ESTE projeto dentro de `projects/`: o caminho
    absoluto com tudo que não é letra nem número virando `-`."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(raiz or os.getcwd()))


def runs_conhecidos(base=None, projeto=None):
    """Todo diretório de run DESTE projeto, do mais recente para o mais antigo:
    <projeto>/<sessão>/subagents/workflows/<runId>/. `projeto="*"` abre para o
    disco inteiro — só quem precisa NOMEAR o dono de um run de fora usa isso."""
    padrao = os.path.join(base or _base_runs(), projeto or projeto_atual(),
                          "*", "subagents", "workflows", "*")
    dirs = [d for d in glob.glob(padrao) if os.path.isdir(d)]
    return sorted(dirs, key=os.path.getmtime, reverse=True)


def _projeto_do_run(dir_run):
    """<projeto>/<sessão>/subagents/workflows/<runId> → o <projeto>."""
    partes = os.path.normpath(dir_run).split(os.sep)
    return partes[-5] if len(partes) >= 5 else ""


def resolver_run(nome=None, base=None, projeto=None):
    """(diretório, erro). Caminho vale como caminho, id vale como id do run, e sem
    nada vale o mais recente DESTA missão. Id que só existe na pasta de outro
    projeto é recusado com o nome do dono: o run de outra missão fala de arquivos
    que não existem aqui, e medi-lo é pior do que não medir."""
    if nome and os.path.isdir(nome):
        return nome, None
    projeto = projeto or projeto_atual()
    conhecidos = runs_conhecidos(base, projeto)
    if nome:
        for d in conhecidos:
            if os.path.basename(d) == nome:
                return d, None
        for d in runs_conhecidos(base, "*"):
            if os.path.basename(d) == nome:
                return None, ("run de outra missão: %s mora em %s, e esta missão é %s"
                              % (nome, _projeto_do_run(d), projeto))
        return None, "run não encontrado: %s" % nome
    if not conhecidos:
        return None, ("nenhum run no disco em %s — rode uma missão antes, ou passe o "
                      "id do run" % os.path.join(base or _base_runs(), projeto))
    return conhecidos[0], None


def degrada(erro, pedido):
    """Código de saída de quem não achou run: avisa sempre, e só TRAVA se o run
    foi pedido pelo nome (2 = uso errado). Sem run nenhum no disco é o projeto de
    quem instalou o plugin — nunca teve missão, não há o que medir, e sair
    diferente de zero seria acusar defeito onde não houve nem medição."""
    print(erro, file=sys.stderr)
    return 2 if pedido else 0


def _n(v):
    return "{:,}".format(v).replace(",", ".")


def main(argv=None):
    ap = argparse.ArgumentParser(description="mede um run por papel: agentes, turnos, tokens")
    ap.add_argument("run", nargs="?",
                    help="caminho OU id do run; sem isto, o mais recente DESTA missão")
    ap.add_argument("--json", action="store_true", help="devolve os números crus")
    ap.add_argument("--contra", help="run anterior: compara o PAR turno×falha papel a papel")
    args = ap.parse_args(argv)

    if desligado():
        return 0

    dir_run, erro = resolver_run(args.run)
    if erro:
        return degrada(erro, args.run)
    r = medir_run(dir_run)
    if args.contra:
        anterior, erro = resolver_run(args.contra)
        if erro:
            return degrada(erro, args.contra)
        r["par_invertido"] = par_invertido(medir_run(anterior), r)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    if not r["agentes"]:
        print("nenhum agent-*.jsonl em %s — nada a medir aqui" % dir_run)
        return 0

    print("run %s — %d agentes · %s turnos · %s tokens\n"
          % (r["run"], r["total"]["agentes"], _n(r["total"]["turnos"]), _n(r["total"]["tokens"])))
    if r["incompleto"]:
        print("run interrompido — medido até onde deu; %d arquivo(s) param no meio:"
              % len(r["incompleto"]))
        for i in r["incompleto"]:
            print("        %s:%d" % (os.path.basename(i["arquivo"]), i["linha"]))
        print()
    cab = "%-14s %6s %8s %8s %7s %14s %10s  %-32s  %s" % ("papel", "agent", "turnos", "t/agent",
                                                          "falha", "cache_read", "output",
                                                          "trecho a abrir", "sinal")
    print(cab)
    print("-" * len(cab))
    for p in r["papeis"]:
        pt = p["ponteiro"]
        endereco = "%s:%d (turno %d)" % (os.path.basename(pt["arquivo"]), pt["linha"],
                                         pt["turno"]) if pt else "—"
        print("%-14s %6d %8d %8.1f %7s %14s %10s  %-32s  %s"
              % (p["papel"], p["agentes"], p["turnos"], p["turnos_por_agente"],
                 "s/reg" if p["taxa_falha"] is None else "%.0f%%" % (p["taxa_falha"] * 100),
                 _n(p["tokens"]["cache_read_input_tokens"]), _n(p["tokens"]["output_tokens"]),
                 endereco, "⚠️  voltas demais" if p["suspeito"] else ""))
    for c in r.get("par_invertido") or []:
        print("\n⚠️  par invertido em %s — turno caiu de %.1f para %.1f e a falha subiu de "
              "%.0f%% para %.0f%%: menos voltas entregando menos"
              % (c["papel"], c["turnos_por_agente"][0], c["turnos_por_agente"][1],
                 c["taxa_falha"][0] * 100, c["taxa_falha"][1] * 100))
    print("\nsinais — %d dos %d acesos" % (sum(1 for s in r["sinais"] if s["casos"]),
                                           len(r["sinais"])))
    for s in r["sinais"]:
        if not s["casos"]:
            print("  ok  %-18s %s" % (s["sinal"], s["titulo"]))
            continue
        gasto = " · %s tokens gastos nele" % _n(s["tokens"]) if s.get("tokens") else ""
        print("  ⚠️  %-18s %s — %d caso(s)%s"
              % (s["sinal"], s["titulo"], len(s["casos"]), gasto))
        for caso in s["casos"][:5]:
            endereco = ("%s:%d  " % (os.path.basename(caso["arquivo"]), caso["linha"])
                        if caso.get("arquivo") else "")
            resto = {k: v for k, v in caso.items() if k not in ("arquivo", "linha")}
            print("        %s%s" % (endereco, json.dumps(resto, ensure_ascii=False)))
        if len(s["casos"]) > 5:
            print("        … e mais %d" % (len(s["casos"]) - 5))
    return 0


if __name__ == "__main__":
    sys.exit(main())
