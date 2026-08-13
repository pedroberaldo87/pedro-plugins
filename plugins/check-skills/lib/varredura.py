#!/usr/bin/env python3
"""O varredor da saúde do que está INSTALADO na máquina — stdlib, sem framework.

Existe porque a pergunta "meus plugins brigam com os dos outros?" não tem resposta em
lugar nenhum: `claude plugin list` diz o que existe, e nada diz o que se ATROPELA. As
seis lentes deste programa, e cada uma é de uma natureza diferente:

    nome        duas skills com o MESMO nome — quem digita não sabe qual responde
    evento      hooks de marketplaces diferentes no mesmo evento, e quem pode BARRAR
    gatilho     descrições que disputam o mesmo assunto — o modelo hesita na escolha
    versao      mais de uma versão da mesma coisa no cache (só a mais alta roda)
    vazamento   processo que a skill abre e NÃO fecha — o código e o que está de pé
    irmao       citação de plugin irmão que NÃO está instalado — e o que fica mudo
    morto       gatilho `/nome` prometido na descrição sem skill instalada que atenda
    fabrica     skill que se chama como um comando do próprio Claude Code — quem digita
                o nome recebe o harness, e a lista de fábrica mora em arquivo declarado

A quinta nasceu de um caso medido em 2026-08-08: uma máquina acumulou **2125 processos
`python3` órfãos**, e nenhuma ferramenta ligava aquilo a quem tinha aberto. Ela olha
para os dois lados, porque um só perderia metade do caso — o código acusa o defeito
antes de rodar, e a máquina mostra o que já vazou e de quem é.

⚠️ O QUE ELE NÃO FAZ, de propósito: julgar. Contradição de INSTRUÇÃO — uma skill que
manda fazer o oposto da outra — não é detectável por varredura de texto, e chutar aqui
produziria alarme que ninguém confere. Quem lê as descrições e julga é a skill que chama
este programa; o programa entrega o material.

    python3 varredura.py            # relatório humano
    python3 varredura.py --json     # o mesmo, para outro programa consumir
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

# O cache é <raiz>/plugins/cache/<marketplace>/<plugin>/<versao>/
CACHE = os.path.join(
    os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"),
    "plugins", "cache",
)

# Assunto → as palavras que o denunciam numa descrição. A busca é por PALAVRA INTEIRA:
# sem isso "ui" casa dentro de "constrUI" e "test" dentro de "conTESTe", e o relatório
# vira ruído — foi o primeiro resultado desta varredura, com 37 falsos positivos em "ui".
ASSUNTOS = {
    "revisar código": ["review", "revisar", "revisão", "audit", "auditoria", "lint"],
    "executar plano": ["executar", "execution", "autônomo", "autonomous", "orquestra"],
    "escrever plano": ["plano", "plan", "roadmap", "prd"],
    "sabatinar antes": ["brainstorm", "sabatina", "grill", "entrevista", "interview"],
    "desenhar diagrama": ["diagrama", "diagram", "arquitetura", "architecture"],
    "design de tela": ["design", "frontend", "interface", "layout", "css"],
    "documentar": ["documentação", "documentation", "documenta", "claude.md", "readme"],
    "publicar": ["deploy", "publish", "publicar", "commit", "push", "release"],
    "navegador": ["browser", "navegador", "playwright", "screenshot"],
    "limpar código": ["dead code", "código morto", "simplif", "refactor", "over-engineer"],
}


def _versao(txt):
    """(1, 16, 2) a partir de '1.16.2'. Parte não numérica vira 0."""
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", txt)[:4])


def instalados(cache=CACHE):
    """{(marketplace, plugin): {"dir", "versao", "outras"}} — só a versão que RODA.

    O cache guarda toda versão já instalada, e uma varredura ingênua conta a mesma
    colisão dezoito vezes. Quem roda é a mais alta; as outras entram em `outras`
    porque cache inchado é achado por si só.
    """
    achados = defaultdict(list)
    if not os.path.isdir(cache):
        return {}
    for market in sorted(os.listdir(cache)):
        dm = os.path.join(cache, market)
        if not os.path.isdir(dm):
            continue
        for plug in sorted(os.listdir(dm)):
            dp = os.path.join(dm, plug)
            if not os.path.isdir(dp):
                continue
            for ver in sorted(os.listdir(dp)):
                dv = os.path.join(dp, ver)
                if os.path.isdir(dv):
                    achados[(market, plug)].append((_versao(ver), ver, dv))
    fora = {}
    for k, v in achados.items():
        v.sort()
        _, ver, dv = v[-1]
        fora[k] = {"dir": dv, "versao": ver, "outras": [x[1] for x in v[:-1]]}
    return fora


def _descricao(caminho):
    """A `description:` do frontmatter, numa linha só. Ausente devolve ''."""
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            txt = fh.read(8000)
    except OSError:
        return ""
    m = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*(?=\n[a-z-]+:|\n---)",
                  txt, re.S | re.M)
    return " ".join((m.group(1) if m else "").split())


def _so_do_usuario(caminho):
    """`disable-model-invocation: true` no frontmatter — só o usuário pode invocar.

    Quem tem esta marca nunca é escolhida pelo modelo: a description dela não entra
    na decisão de invocar, entra na ajuda de quem digita a barra. Cobrar dela a frase
    de situação (`use quando…`, escrita PARA o modelo) é cobrar uma frase que não
    alcança ninguém — e foi assim que as três skills do 2op reprovaram na lente 8
    tendo o único leitor possível já nomeado na própria description.
    """
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            txt = fh.read(8000)
    except OSError:
        return False
    if not txt.startswith("---"):
        return False
    fim = txt.find("\n---", 3)
    if fim < 0:
        # frontmatter sem linha de fecho não é frontmatter: a marca não vale, e a
        # lente continua cobrando. Ler o arquivo inteiro aqui isentaria qualquer
        # skill que apenas MENCIONE o campo no corpo.
        return False
    return re.search(r"^disable-model-invocation:\s*true\s*$", txt[:fim], re.M) is not None


def skills(inst):
    """[(marketplace, plugin, nome, descricao, so_do_usuario)] do que está instalado."""
    fora = []
    for (market, plug), meta in sorted(inst.items()):
        base = os.path.join(meta["dir"], "skills")
        if not os.path.isdir(base):
            continue
        for nome in sorted(os.listdir(base)):
            sk = os.path.join(base, nome, "SKILL.md")
            if os.path.isfile(sk):
                fora.append((market, plug, nome, _descricao(sk), _so_do_usuario(sk)))
    return fora


def _barra(caminho):
    """O script pode NEGAR? Lê o arquivo e procura os canais de recusa.

    É leitura de texto, não execução: um script que só menciona `deny` num comentário
    entra como candidato. Falso positivo aqui custa uma conferência; falso negativo
    esconderia justamente o conflito que interessa.
    """
    if not caminho or not os.path.isfile(caminho):
        return False
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            t = fh.read()
    except OSError:
        return False
    return ('permissionDecision' in t and 'deny' in t) or "hj_deny" in t \
        or "exit 2" in t or ('"decision"' in t and "block" in t) \
        or ("decision:" in t and "block" in t)


def hooks(inst):
    """[(evento, matcher, marketplace, plugin, script, barra)] de tudo que está instalado."""
    fora = []
    for (market, plug), meta in sorted(inst.items()):
        f = os.path.join(meta["dir"], "hooks", "hooks.json")
        if not os.path.isfile(f):
            continue
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except (ValueError, OSError):
            continue
        for ev, grupos in (d.get("hooks") or {}).items():
            for g in grupos or []:
                for h in g.get("hooks") or []:
                    cmd = h.get("command") or ""
                    # o caminho do script dentro do comando, que pode vir composto
                    cand = [t for t in cmd.replace('"', " ").split()
                            if "/hooks/" in t or t.endswith((".mjs", ".py", ".sh"))]
                    caminho = cand[-1] if cand else ""
                    for pref in ("${CLAUDE_PLUGIN_ROOT}", "$CLAUDE_PLUGIN_ROOT"):
                        caminho = caminho.replace(pref, meta["dir"])
                    nome = os.path.basename(caminho) if caminho else "(prompt LLM inline)"
                    fora.append((ev, g.get("matcher", "*"), market, plug,
                                 nome, _barra(caminho)))
    return fora


def _cita(desc, palavra):
    """A palavra aparece na descrição como PALAVRA, não como pedaço de outra."""
    return re.search(r"(?<![a-zà-ú])%s" % re.escape(palavra), desc, re.I) is not None


def varre(inst=None):
    """Os quatro conflitos, cada um numa lista própria."""
    inst = instalados() if inst is None else inst
    sk = skills(inst)
    hk = hooks(inst)

    # 1 · NOME REPETIDO — duas skills com o mesmo nome
    por_nome = defaultdict(list)
    for market, plug, nome, _, _uso in sk:
        por_nome[nome].append({"marketplace": market, "plugin": plug})
    nomes = [{"nome": n, "onde": v} for n, v in sorted(por_nome.items()) if len(v) > 1]

    # 2 · EVENTO DISPUTADO — só quando os hooks vêm de marketplaces diferentes
    por_ev = defaultdict(list)
    for ev, m, market, plug, script, barra in hk:
        por_ev[ev].append({"matcher": m, "marketplace": market, "plugin": plug,
                           "script": script, "barra": barra})
    eventos = []
    for ev, v in sorted(por_ev.items()):
        markets = {x["marketplace"] for x in v}
        if len(markets) > 1:
            eventos.append({"evento": ev, "marketplaces": sorted(markets),
                            "hooks": v,
                            "barram": [x for x in v if x["barra"]]})

    # 3 · GATILHO DISPUTADO — descrições que citam o mesmo assunto, de origens diferentes
    gatilhos = []
    for assunto, palavras in sorted(ASSUNTOS.items()):
        hits = [{"marketplace": m, "plugin": p, "skill": n}
                for m, p, n, d, _uso in sk if any(_cita(d, w) for w in palavras)]
        markets = {x["marketplace"] for x in hits}
        if len(markets) > 1 and len(hits) > 2:
            gatilhos.append({"assunto": assunto, "marketplaces": sorted(markets),
                             "skills": hits})

    # 4 · CACHE INCHADO — versões antigas que ficaram no disco
    versoes = [{"marketplace": m, "plugin": p, "roda": meta["versao"],
                "paradas": meta["outras"]}
               for (m, p), meta in sorted(inst.items()) if meta["outras"]]

    return {"instalados": len(inst), "skills": len(sk), "hooks": len(hk),
            "nome_repetido": nomes, "evento_disputado": eventos,
            "gatilho_disputado": gatilhos, "cache_inchado": versoes,
            "vazamento_codigo": vazamento_codigo(inst),
            "vazamento_vivo": vazamento_vivo(inst),
            "irmao_ausente": irmao_ausente(inst),
            "gatilho_morto": gatilho_morto(inst, sk),
            "sem_situacao": sem_situacao(sk),
            "nome_de_fabrica": nome_de_fabrica(sk)}


# ── 5 · VAZAMENTO — processo que a skill abre e não fecha ──────────────────────
# Duas metades, e nenhuma substitui a outra. O CÓDIGO acusa o defeito antes de ele
# rodar; a MÁQUINA mostra o que já vazou e de quem é. Em 2026-08-08 um caso real
# precisou das duas: 155 pontos de código defeituoso produziram 2125 órfãos, e nem o
# código dizia quantos já estavam de pé, nem os processos diziam de onde vieram.

# Python: disparo sem fechar a entrada, ou sem grupo próprio (o timeout mata o filho
# e o NETO sobrevive). Node: `stdio: 'inherit'` entrega o terminal ao filho.
# Shell: `&` sem `wait`, `nohup` e `disown` largam o processo de propósito.
# Os padrões vêm da CÓPIA LOCAL de `_shared/padroes_vazamento.py`, vendorada por
# `scripts/sync-shared.sh`. Três programas cobram este mesmo defeito, e no dia em que
# nasceram já divergiam — um tinha `disown` na lista, outro não.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from padroes_vazamento import ISENTO, NODE_OK, RISCO  # noqa: E402


def vazamento_codigo(inst=None):
    """[{marketplace, plugin, arquivo, linha, risco}] — o defeito ANTES de rodar."""
    inst = instalados() if inst is None else inst
    fora = []
    for (market, plug), meta in sorted(inst.items()):
        for base, _, nomes in os.walk(meta["dir"]):
            if "node_modules" in base or "__pycache__" in base:
                continue
            for nome in sorted(nomes):
                if not nome.endswith((".py", ".mjs", ".js", ".sh")):
                    continue
                cam = os.path.join(base, nome)
                try:
                    with open(cam, encoding="utf-8", errors="replace") as fh:
                        txt = fh.read()
                except OSError:
                    continue
                linhas = txt.splitlines()
                # o rótulo CURTO é o desta lista; o humano é do relatório de causa
                for padrao, risco, _humano in RISCO:
                    for m in padrao.finditer(txt):
                        ln = txt.count("\n", 0, m.start()) + 1
                        volta = "\n".join(linhas[max(0, ln - 2):ln])
                        if ISENTO.search(volta):
                            continue
                        # `stdio: ['ignore', 'inherit', 'inherit']` É o conserto — stdin
                        # fechado, saída visível —, e a palavra `inherit` dentro do
                        # arranjo casa o padrão do mesmo jeito. Sem esta linha a lente
                        # acusaria justamente o código já corrigido, e lista que nunca
                        # chega a zero é lista que ninguém mais abre.
                        if NODE_OK.search(m.group(0)):
                            continue
                        fora.append({"marketplace": market, "plugin": plug,
                                     "arquivo": os.path.relpath(cam, meta["dir"]),
                                     "linha": ln, "risco": risco})
    return fora


def _ps():
    """[(pid, ppid, minutos_de_cpu, comando)] — vazio quando não dá para ler."""
    try:
        r = subprocess.run(["ps", "-eo", "pid=,ppid=,time=,args="],
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=15, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return []
    fora = []
    for linha in (r.stdout or "").splitlines():
        campos = linha.split(None, 3)
        if len(campos) < 4:
            continue
        try:
            fora.append((int(campos[0]), int(campos[1]), campos[2], campos[3]))
        except ValueError:
            continue
    return fora


def vazamento_vivo(inst=None):
    """[{plugin, pid, comando, motivo}] — o que está de pé AGORA por culpa de alguém.

    A ligação processo→skill é por CAMINHO: o cache instala cada plugin em pasta
    própria, e o comando do órfão carrega esse caminho. Sem isso o achado seria "há
    processos estranhos na máquina", que não diz a ninguém o que fazer.

    Só entra quem é ÓRFÃO (pai `1`): processo com pai vivo tem dono, e encerrá-lo
    seria matar trabalho em curso. É a mesma trava do lixeiro — quem abriu, colhe.
    """
    inst = instalados() if inst is None else inst
    porcaminho = {meta["dir"]: (m, p) for (m, p), meta in inst.items()}
    fora = []
    for pid, ppid, cpu, cmd in _ps():
        if ppid != 1 or pid <= 1:
            continue
        dono = next(((m, p) for d, (m, p) in porcaminho.items() if d in cmd), None)
        if dono is None:
            continue
        fora.append({"marketplace": dono[0], "plugin": dono[1], "pid": pid,
                     "cpu": cpu, "comando": cmd[:160],
                     "motivo": "o pai morreu e ele continuou"})
    return fora


# ── 6 · IRMÃO AUSENTE — a travessia que não resolve NESTA máquina ─────────────
# O cobrador do repositório vê o TEXTO da citação e sabe que ela é acoplamento; só a
# máquina de quem instalou sabe se o irmão citado está aqui. Quando não está, nada
# estoura: `resolve-plugin.sh` devolve vazio e o hook sai calado — o usuário descobre
# a dependência pelo que deixou de acontecer. Daí a lente nomear as duas coisas: QUEM
# depende do ausente, e QUE arquivo do outro plugin ficou mudo.
CITA_IRMAO = (
    re.compile(r"resolve-plugin\.sh\s+([\w-]+)\s+(\S+)"),
    re.compile(r"CLAUDE_PLUGIN_ROOT\}?/\.\./([\w-]+)/?(\S*)"),
    re.compile(r"(?<![\w./-])plugins/([\w-]+)/((?:lib|hooks|skills)/\S*)"),
)


def irmao_ausente(inst=None):
    """[{marketplace, plugin, arquivo, linha, ausente, mudo}] — citação que não resolve."""
    inst = instalados() if inst is None else inst
    presentes = {p for _, p in inst}
    fora = []
    for (market, plug), meta in sorted(inst.items()):
        for base, _, nomes in os.walk(meta["dir"]):
            # bancada e fixture citam plugin de MENTIRA de propósito — numa máquina real
            # foram os 4 únicos achados desta lente, e lista que nunca chega a zero é
            # lista que ninguém mais abre
            if "node_modules" in base or "__pycache__" in base or "/fixtures" in base:
                continue
            for nome in sorted(nomes):
                # o próprio resolvedor cita irmão nos exemplos de uso, e exemplo não é
                # dependência — acusá-lo seria acusar a régua de encostar na peça
                if nome == "resolve-plugin.sh" or nome.startswith("test_"):
                    continue
                if not nome.endswith((".md", ".sh", ".py", ".mjs", ".js", ".json")):
                    continue
                cam = os.path.join(base, nome)
                try:
                    with open(cam, encoding="utf-8", errors="replace") as fh:
                        linhas = fh.read().splitlines()
                except OSError:
                    continue
                for n, linha in enumerate(linhas, 1):
                    vistos = set()
                    for rx in CITA_IRMAO:
                        for m in rx.finditer(linha):
                            alvo = m.group(1)
                            if alvo == plug or alvo in presentes or alvo in vistos:
                                continue
                            vistos.add(alvo)
                            fora.append({
                                "marketplace": market, "plugin": plug,
                                "arquivo": os.path.relpath(cam, meta["dir"]),
                                "linha": n, "ausente": alvo,
                                "mudo": m.group(2).strip("\"'`,);") or "(o plugin inteiro)",
                                "trecho": linha.strip()[:120]})
    return fora


# ── 7 · GATILHO MORTO — a barra que a descrição promete e ninguém atende ──────
# Uma descrição que diz `Use quando o usuário diz "/project-doc"` ensina ao modelo um
# comando que o rename apagou: quem digita o nome velho é atendido por uma skill que
# não se chama mais assim, e quem digita o novo não acha gatilho nenhum. Entra QUALQUER
# barra-nome, com aspas ou solta em prosa — `NÃO substitui o /project-doc FULL` ensina o
# comando morto exatamente igual à forma citada, e enquanto a lente só olhava aspas essa
# frase saía limpa. Fora ficam nome sem barra ("vira plano" é linguagem, não promessa de
# comando) e caminho de arquivo, que a barra colada em letra ou em outra barra denuncia.
CITA_COMANDO = re.compile(r"(?<![\w/.~-])(/[a-zA-Z][\w-]*)(?![\w/-])")


def gatilho_morto(inst=None, sk=None):
    """[{marketplace, plugin, skill, gatilho}] — barra prometida sem skill que atenda."""
    inst = instalados() if inst is None else inst
    sk = skills(inst) if sk is None else sk
    # Barra-nome do próprio harness (`/clear`) É atendida — quem digita recebe o comando
    # de fábrica. Sai da lente pela MESMA lista declarada que a lente 9 usa.
    fab, _isentos = fabrica()
    nomes = {n for _, _, n, _, _uso in sk} | fab
    fora, vistos = [], set()
    for market, plug, nome, desc, _uso in sk:
        for m in CITA_COMANDO.finditer(desc):
            gat = m.group(1)
            alvo = gat.lstrip("/").split("/")[0]
            if not alvo or alvo in nomes or (plug, nome, gat) in vistos:
                continue
            vistos.add((plug, nome, gat))
            fora.append({"marketplace": market, "plugin": plug, "skill": nome,
                         "gatilho": gat})
    return fora


# ── 8 · SEM SITUAÇÃO — a descrição que só serve a quem já sabe que a skill existe ──
# Apelido (`"/faxina"`, `"sprint"`) serve a quem lembra do nome. Quem NÃO lembra que a
# skill existe só é atendido se a descrição disser em que SITUAÇÃO DE TRABALHO ela entra
# — o molde é a de `sprint`: `Use quando o usuário disser …`. A frase tem duas peças, e
# nenhuma sozinha basta: um verbo de invocação (use, rode, dispare…) e o elo que amarra
# a situação (quando, depois de, sempre que…). Lista de apelido sem elo — `Trigger em
# /principles` — passa direto por este teste de propósito: é nome, não situação.
SITUACAO = re.compile(
    r"\b(?:use|usar|rode|rodar|dispar\w+|acion\w+|chame|chamar|invoque|trigger)\b"
    r"[^.;]{0,60}?"
    r"\b(?:quando|when|sempre que|assim que|ao |após|apos|depois de|depois que|antes de|"
    r"no (?:fim|começo|comeco|início|inicio) de|se o|se a|se você|se voce)",
    re.I)


def sem_situacao(sk):
    """[{marketplace, plugin, skill}] — description sem uma situação de trabalho em frase.

    Skill marcada `disable-model-invocation: true` fica de FORA: a frase que esta
    lente cobra é escrita para o modelo decidir se invoca, e nessas o modelo nunca
    invoca. Isenção por mecanismo declarado no próprio arquivo, não por lista à mão.
    """
    return [{"marketplace": m, "plugin": p, "skill": n}
            for m, p, n, d, so_usuario in sk
            if not so_usuario and not SITUACAO.search(d)]


# ── 9 · NOME DE FÁBRICA — a skill que disputa o nome com o próprio Claude Code ──
# Skill que se chama como comando do harness não avisa: quem digita o nome recebe o
# comando de fábrica, e a skill nunca é chamada. A lista de fábrica NÃO mora aqui —
# mora em `comandos-de-fabrica.txt`, com a fonte e a data escritas; lista dentro do
# cobrador envelhece sem ninguém ver. Disputa decidida ganha `isento <nome>: <motivo>`
# no mesmo arquivo, e isenção sem motivo escrito não conta — descuido com crachá.
FABRICA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "comandos-de-fabrica.txt")


def fabrica(caminho=FABRICA):
    """(set de nomes de fábrica, {nome isento: motivo}) lidos do arquivo declarado."""
    nomes, isentos = set(), {}
    try:
        with open(caminho, encoding="utf-8") as fh:
            linhas = fh.read().splitlines()
    except OSError:
        return nomes, isentos
    for linha in linhas:
        linha = linha.split("#", 1)[0].strip()
        if not linha:
            continue
        m = re.match(r"isento\s+([\w-]+)\s*:\s*(\S.*)$", linha)
        if m:
            isentos[m.group(1)] = m.group(2).strip()
        elif re.fullmatch(r"[\w-]+", linha):
            nomes.add(linha)
    return nomes, isentos


def nome_de_fabrica(sk, fab=None):
    """[{marketplace, plugin, skill, motivo}] — disputa com comando de fábrica.

    `motivo` vem preenchido quando a disputa foi decidida e declarada; vazio é descuido.
    """
    nomes, isentos = fab if fab is not None else fabrica()
    return [{"marketplace": m, "plugin": p, "skill": n,
             "motivo": isentos.get(n, "")}
            for m, p, n, _, _uso in sk if n in nomes]


def skills_do_repo(raiz):
    """[(marketplace, plugin, nome, descricao, so_do_usuario)] lidas do REPOSITÓRIO.

    O cache pode estar numa versão anterior à do disco, e é o disco que o commit
    publica — o cobrador do gate tem que olhar o que está sendo commitado.
    """
    fora = []
    base_plugins = os.path.join(raiz, "plugins")
    for plug in sorted(os.listdir(base_plugins)):
        base = os.path.join(base_plugins, plug, "skills")
        if not os.path.isdir(base):
            continue
        for nome in sorted(os.listdir(base)):
            sk = os.path.join(base, nome, "SKILL.md")
            if os.path.isfile(sk):
                fora.append(("(repositório)", plug, nome, _descricao(sk),
                             _so_do_usuario(sk)))
    return fora


def desenha(r):
    """O relatório humano. Saída de programa, não redigida por ninguém."""
    L = ["CONFLITOS ENTRE O QUE ESTÁ INSTALADO", ""]
    L.append("%d plugins · %d skills · %d registros de hook" %
             (r["instalados"], r["skills"], r["hooks"]))
    L.append("")

    L.append("1 · NOME REPETIDO — quem digita não sabe qual responde")
    if not r["nome_repetido"]:
        L.append("   nenhum")
    for n in r["nome_repetido"]:
        L.append("   /%s  ×%d" % (n["nome"], len(n["onde"])))
        for o in n["onde"]:
            L.append("      %s / %s" % (o["marketplace"], o["plugin"]))
    L.append("")

    L.append("2 · EVENTO DISPUTADO — hooks de origens diferentes no mesmo gatilho")
    if not r["evento_disputado"]:
        L.append("   nenhum")
    for e in r["evento_disputado"]:
        L.append("   %s — %d marketplaces, %d hooks, %d podem BARRAR"
                 % (e["evento"], len(e["marketplaces"]), len(e["hooks"]),
                    len(e["barram"])))
        for h in e["barram"]:
            L.append("      BARRA  %-24s %-22s %s"
                     % (h["marketplace"], h["plugin"], h["script"]))
    L.append("")

    L.append("3 · GATILHO DISPUTADO — o modelo hesita entre elas")
    if not r["gatilho_disputado"]:
        L.append("   nenhum")
    for g in r["gatilho_disputado"]:
        L.append("   %s — %d skills, %d marketplaces"
                 % (g["assunto"], len(g["skills"]), len(g["marketplaces"])))
        for s in g["skills"]:
            L.append("      %-24s /%s" % (s["marketplace"], s["skill"]))
    L.append("")

    L.append("4 · CACHE INCHADO — versões paradas no disco")
    if not r["cache_inchado"]:
        L.append("   nenhum")
    for v in r["cache_inchado"]:
        L.append("   %s/%s roda %s · %d parada(s): %s"
                 % (v["marketplace"], v["plugin"], v["roda"],
                    len(v["paradas"]), ", ".join(v["paradas"][:6])))
    L.append("")

    L.append("5 · VAZAMENTO — processo que a skill abre e não fecha")
    vivo, cod = r.get("vazamento_vivo") or [], r.get("vazamento_codigo") or []
    if not vivo:
        L.append("   de pé agora: nenhum")
    else:
        L.append("   DE PÉ AGORA — %d processo(s) órfão(s):" % len(vivo))
        porplug = defaultdict(list)
        for x in vivo:
            porplug[(x["marketplace"], x["plugin"])].append(x)
        for (m, p), xs in sorted(porplug.items()):
            L.append("      %s/%s — %d, ex. pid %s: %s"
                     % (m, p, len(xs), xs[0]["pid"], xs[0]["comando"][:70]))
    if not cod:
        L.append("   no código: nenhum")
    else:
        L.append("   NO CÓDIGO — %d ponto(s) que podem vazar:" % len(cod))
        porplug = defaultdict(list)
        for x in cod:
            porplug[(x["marketplace"], x["plugin"])].append(x)
        for (m, p), xs in sorted(porplug.items(), key=lambda kv: -len(kv[1]))[:8]:
            L.append("      %-34s %3d — ex. %s:%s (%s)"
                     % ("%s/%s" % (m, p), len(xs), xs[0]["arquivo"], xs[0]["linha"],
                        xs[0]["risco"]))
    L.append("")

    L.append("6 · IRMÃO AUSENTE — a citação que não resolve nesta máquina")
    irm = r.get("irmao_ausente") or []
    if not irm:
        L.append("   nenhum")
    else:
        porausente = defaultdict(list)
        for x in irm:
            porausente[x["ausente"]].append(x)
        for alvo, xs in sorted(porausente.items()):
            L.append("   %s não está instalado — %d citação(ões):" % (alvo, len(xs)))
            for x in xs[:6]:
                L.append("      %s/%s %s:%s fica mudo: %s"
                         % (x["marketplace"], x["plugin"], x["arquivo"], x["linha"],
                            x["mudo"]))
    L.append("")

    L.append("7 · GATILHO MORTO — a barra que a descrição promete e ninguém atende")
    mortos = r.get("gatilho_morto") or []
    if not mortos:
        L.append("   nenhum")
    for x in mortos:
        L.append("   %s aparece em %s/%s /%s e não tem skill instalada"
                 % (x["gatilho"], x["marketplace"], x["plugin"], x["skill"]))
    L.append("")

    L.append("8 · SEM SITUAÇÃO — a descrição não diz em que momento de trabalho entra")
    sems = r.get("sem_situacao") or []
    if not sems:
        L.append("   nenhuma")
    for x in sems:
        L.append("   %s/%s /%s — só apelido, nenhuma frase de situação"
                 % (x["marketplace"], x["plugin"], x["skill"]))
    L.append("")

    L.append("9 · NOME DE FÁBRICA — a skill disputa o nome com um comando do harness")
    fab = r.get("nome_de_fabrica") or []
    if not fab:
        L.append("   nenhuma")
    for x in fab:
        if x["motivo"]:
            L.append("   /%s — %s/%s: isenção declarada — %s"
                     % (x["skill"], x["marketplace"], x["plugin"], x["motivo"][:90]))
        else:
            L.append("   /%s — %s/%s disputa com o comando de fábrica e NÃO tem isenção"
                     % (x["skill"], x["marketplace"], x["plugin"]))
    L.append("")

    L.append("O que este programa NÃO mede: contradição de INSTRUÇÃO — uma skill que")
    L.append("manda o oposto da outra. Isso se lê nas descrições, e quem julga é humano.")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true", help="devolve o achado em JSON")
    p.add_argument("--situacao-repo", metavar="RAIZ",
                   help="cobra as skills do REPOSITÓRIO: sai 1 se alguma description "
                        "não declara situação de trabalho em frase")
    args = p.parse_args(argv)
    if args.situacao_repo:
        fora = sem_situacao(skills_do_repo(args.situacao_repo))
        for x in fora:
            print("plugins/%s/skills/%s/SKILL.md — a description não diz em que "
                  "situação de trabalho a skill entra" % (x["plugin"], x["skill"]))
        return 1 if fora else 0
    r = varre()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(desenha(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
