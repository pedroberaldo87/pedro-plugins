#!/usr/bin/env python3
"""O varredor de conflitos entre o que está INSTALADO na máquina — stdlib, sem framework.

Existe porque a pergunta "meus plugins brigam com os dos outros?" não tem resposta em
lugar nenhum: `claude plugin list` diz o que existe, e nada diz o que se ATROPELA. Os
quatro atropelos que este programa mede, e cada um é de uma natureza diferente:

    nome        duas skills com o MESMO nome — quem digita não sabe qual responde
    evento      hooks de marketplaces diferentes no mesmo evento, e quem pode BARRAR
    gatilho     descrições que disputam o mesmo assunto — o modelo hesita na escolha
    versao      mais de uma versão da mesma coisa no cache (só a mais alta roda)

⚠️ O QUE ELE NÃO FAZ, de propósito: julgar. Contradição de INSTRUÇÃO — uma skill que
manda fazer o oposto da outra — não é detectável por varredura de texto, e chutar aqui
produziria alarme que ninguém confere. Quem lê as descrições e julga é a skill que chama
este programa; o programa entrega o material.

    python3 conflitos.py            # relatório humano
    python3 conflitos.py --json     # o mesmo, para outro programa consumir
"""

import argparse
import json
import os
import re
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
            "gatilho_disputado": gatilhos, "cache_inchado": versoes}


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
