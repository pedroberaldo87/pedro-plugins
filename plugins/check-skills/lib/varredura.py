#!/usr/bin/env python3
"""O varredor da saúde do que está INSTALADO na máquina — stdlib, sem framework.

Existe porque a pergunta "meus plugins brigam com os dos outros?" não tem resposta em
lugar nenhum: `claude plugin list` diz o que existe, e nada diz o que se ATROPELA. As
cinco lentes deste programa, e cada uma é de uma natureza diferente:

    nome        duas skills com o MESMO nome — quem digita não sabe qual responde
    evento      hooks de marketplaces diferentes no mesmo evento, e quem pode BARRAR
    gatilho     descrições que disputam o mesmo assunto — o modelo hesita na escolha
    versao      mais de uma versão da mesma coisa no cache (só a mais alta roda)
    vazamento   processo que a skill abre e NÃO fecha — o código e o que está de pé

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


def skills(inst):
    """[(marketplace, plugin, nome, descricao)] de tudo que está instalado."""
    fora = []
    for (market, plug), meta in sorted(inst.items()):
        base = os.path.join(meta["dir"], "skills")
        if not os.path.isdir(base):
            continue
        for nome in sorted(os.listdir(base)):
            sk = os.path.join(base, nome, "SKILL.md")
            if os.path.isfile(sk):
                fora.append((market, plug, nome, _descricao(sk)))
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
    for market, plug, nome, _ in sk:
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
                for m, p, n, d in sk if any(_cita(d, w) for w in palavras)]
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
            "vazamento_vivo": vazamento_vivo(inst)}


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
                           stdin=subprocess.DEVNULL, capture_output=True, text=True,
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
    L.append("O que este programa NÃO mede: contradição de INSTRUÇÃO — uma skill que")
    L.append("manda o oposto da outra. Isso se lê nas descrições, e quem julga é humano.")
    return "\n".join(L)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true", help="devolve o achado em JSON")
    args = p.parse_args(argv)
    r = varre()
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(desenha(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
