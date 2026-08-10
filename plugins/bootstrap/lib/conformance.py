#!/usr/bin/env python3
"""conformance.py — compara o estado VIVO da maquina contra o contrato versionado.

Modo relatorio: imprime cada desvio e o comando que corrige. Nunca escreve nada.
Decisao de projeto (2026-07-30): a ferramenta mostra o desvio, quem le decide.

Uso:
    python3 lib/conformance.py            # relatorio legivel
    python3 lib/conformance.py --quiet    # so o resumo (pra hook)
    python3 lib/conformance.py --json     # saida estruturada

Saida: 0 quando esta tudo conforme, 1 quando ha desvio. Nunca bloqueia nada
(quem chama decide o que fazer com o codigo de saida).

Python 3 stdlib apenas — convencao do repo (patterns.md).
"""
import argparse
import difflib
import json
import os
import re
import shutil
import shlex
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude"))


def repo_config_dir():
    """Acha o config/ versionado: CLAUDE_PLUGIN_ROOT, env do repo, ou o proprio arquivo."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root and (Path(root) / "config").is_dir():
        return Path(root) / "config"
    repo = os.environ.get("PEDRO_PLUGINS_REPO")
    if repo:
        p = Path(repo) / "plugins" / "bootstrap" / "config"
        if p.is_dir():
            return p
    # rodando de dentro do repo: lib/ -> bootstrap/ -> config/
    p = Path(__file__).resolve().parent.parent / "config"
    return p if p.is_dir() else None


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


class Report:
    def __init__(self):
        self.desvios = []
        self.ok = []

    def desvio(self, area, o_que, evidencia, conserto):
        self.desvios.append({"area": area, "o_que": o_que,
                             "evidencia": evidencia, "conserto": conserto})

    def conforme(self, area, o_que):
        self.ok.append({"area": area, "o_que": o_que})


# ---------------------------------------------------------------- checagens


def _refs_instaladas():
    """O que esta INSTALADO segundo CLAUDE_DIR/plugins/installed_plugins.json.

    Formato conferido na maquina (v2): {"plugins": {"<nome>@<mkt>": [ {..instalacao..} ]}}
    — a chave existir com lista nao-vazia e o que significa instalado.
    Devolve None quando a fonte nao existe/nao parseia: sem ela o check volta a
    olhar so o enabledPlugins (fail-open, a ferramenta e so relatorio).
    """
    d = load_json(CLAUDE_DIR / "plugins" / "installed_plugins.json")
    plugins = d.get("plugins") if isinstance(d, dict) else None
    if not isinstance(plugins, dict) or not plugins:
        return None
    return {ref for ref, inst in plugins.items() if isinstance(inst, list) and inst}


def check_plugins(rep, cfg):
    """settings.json vivo x manifest versionado."""
    manifest = load_json(cfg / "manifest.json")
    if not manifest:
        rep.desvio("plugins", "manifest.json versionado nao foi encontrado",
                   str(cfg / "manifest.json"), "conferir o checkout do pedro-plugins")
        return
    settings = load_json(CLAUDE_DIR / "settings.json")
    vivo = settings.get("enabledPlugins", {}) or {}

    querido = {}
    for m in manifest.get("marketplaces", []):
        for pl in m.get("plugins", []):
            querido[f"{pl['name']}@{m['name']}"] = bool(pl.get("enabled", True))

    # AUSENTE e DESLIGADO nao sao a mesma coisa: `claude plugin enable` num plugin
    # que nem foi instalado falha. Sem a fonte do instalado (None) fica o comportamento
    # antigo, que so enxerga o enabledPlugins.
    instaladas = _refs_instaladas()

    for ref, quer in sorted(querido.items()):
        tem = bool(vivo.get(ref, False))
        if instaladas is not None and ref not in instaladas:
            if quer:
                rep.desvio("plugins", f"{ref} nao instalado nesta maquina",
                           f'{CLAUDE_DIR / "plugins" / "installed_plugins.json"} '
                           f'nao tem a chave "{ref}"',
                           f"claude plugin install {ref}")
            continue   # ausente e o manifest quer desligado: nada a fazer
        if tem == quer:
            continue
        nome = ref.split("@")[0]
        if quer:
            rep.desvio("plugins", f"{ref} devia estar LIGADO e esta desligado",
                       f'settings.json enabledPlugins["{ref}"] = {tem}',
                       f"claude plugin enable {ref}")
        else:
            rep.desvio("plugins", f"{ref} devia estar DESLIGADO e esta ligado",
                       f'settings.json enabledPlugins["{ref}"] = {tem}',
                       f"claude plugin disable {ref}   (ou rode o sync do bootstrap)")
        del nome
    if not any(d["area"] == "plugins" for d in rep.desvios):
        rep.conforme("plugins", f"{len(querido)} plugins do manifest batem com a maquina")


def check_claude_md(rep, cfg):
    """O CLAUDE.md vivo divergiu do versionado? O sync e de mao unica e sobrescreve."""
    src = cfg / "CLAUDE-global.md"
    dst = CLAUDE_DIR / "CLAUDE.md"
    if not src.is_file() or not dst.is_file():
        return
    a = src.read_text(encoding="utf-8").splitlines()
    b = dst.read_text(encoding="utf-8").splitlines()
    if a == b:
        rep.conforme("claude.md", "o CLAUDE.md da maquina e igual ao versionado")
        return
    diff = list(difflib.unified_diff(a, b, "versionado", "maquina", lineterm="", n=0))
    so_na_maquina = [ln[1:].strip() for ln in diff
                     if ln.startswith("+") and not ln.startswith("+++") and ln[1:].strip()]
    so_no_repo = [ln[1:].strip() for ln in diff
                  if ln.startswith("-") and not ln.startswith("---") and ln[1:].strip()]
    ev = [f"diff {src} {dst}"]
    for rotulo, linhas in (("so na MAQUINA", so_na_maquina), ("so no REPO", so_no_repo)):
        if linhas:
            ev.append(f"  {rotulo} ({len(linhas)} linha(s)):")
            ev += [f"    {ln[:100]}" for ln in linhas[:3]]
            if len(linhas) > 3:
                ev.append(f"    … mais {len(linhas) - 3}")
    # a direcao NAO e prescrita: quem edita o repo de proposito quer o contrario
    # de quem escreveu uma regra nova na maquina. O sync so anda repo -> maquina.
    rep.desvio(
        "claude.md",
        "o CLAUDE.md da maquina e o versionado divergiram",
        "\n".join(ev),
        "o sync so anda repo -> maquina, entao o que so existe na MAQUINA some no proximo\n"
        "     /bootstrap:setup. Decida a direcao e rode UM dos dois:\n"
        f"       cp {dst} {src}    # a maquina vira a verdade\n"
        f"       cp {src} {dst}    # o repo vira a verdade (aplica o que voce editou la)")


def check_teto_unico(rep, cfg):
    """Um numero de linhas so. Regra numerica duplicada foi a causa-raiz da verbosidade."""
    dst = CLAUDE_DIR / "CLAUDE.md"
    if not dst.is_file():
        return
    achados = []
    for i, ln in enumerate(dst.read_text(encoding="utf-8").splitlines(), 1):
        if re.search(r"\b\d+\s*(?:-\s*\d+)?\s*linhas?\b", ln, re.I):
            achados.append((i, ln.strip()[:110]))
    if len(achados) > 1:
        ev = "\n".join(f"  {n}: {t}" for n, t in achados)
        rep.desvio("teto", f"{len(achados)} regras de tamanho no CLAUDE.md (o contrato pede UMA)",
                   f"{dst}\n{ev}",
                   "deixar so uma; o teto canonico vive em output-styles/clean-style.md")
    else:
        rep.conforme("teto", "existe no maximo uma regra numerica de tamanho no CLAUDE.md")


def check_output_style(rep, cfg):
    """O output style Clean Style esta no lugar e o plugin que o carrega esta ligado."""
    estilo = cfg.parent / "output-styles" / "clean-style.md"
    if not estilo.is_file():
        rep.desvio("output style", "output-styles/clean-style.md nao existe no plugin",
                   str(estilo), "restaurar o arquivo no pedro-plugins")
        return
    txt = estilo.read_text(encoding="utf-8")
    faltando = [c for c in ("force-for-plugin: true", "keep-coding-instructions: true")
                if c not in txt]
    if faltando:
        rep.desvio("output style", "frontmatter incompleto: " + ", ".join(faltando),
                   str(estilo),
                   "sem force-for-plugin o estilo so vale se selecionado no /config;\n"
                   "    sem keep-coding-instructions o Claude perde as instrucoes de engenharia")
    else:
        rep.conforme("output style", "clean-style.md presente, com force-for-plugin e keep-coding-instructions")

    settings = load_json(CLAUDE_DIR / "settings.json")
    if settings.get("outputStyle") != "Clean Style":
        rep.desvio("output style",
                   f'outputStyle esta {settings.get("outputStyle")!r}, devia ser "Clean Style"',
                   'settings.json -> "outputStyle"',
                   'sem isso o estilo nao entra no prompt de sistema e so o Stop hook barra,\n'
                   '     depois do fato. Conserto: "outputStyle": "Clean Style" no settings.json')
    if not settings.get("enabledPlugins", {}).get("bootstrap@pedro-plugins", False):
        rep.desvio("output style", "o plugin bootstrap esta desligado, entao o estilo nao carrega",
                   'settings.json enabledPlugins["bootstrap@pedro-plugins"]',
                   "claude plugin enable bootstrap@pedro-plugins")


def check_skills(rep, cfg):
    """Skill instalada em ~/.claude/skills que o manifest nao declara."""
    manifest = load_json(cfg / "manifest.json")
    declaradas = set(manifest.get("skills", {}).get("permitidas", []))
    skills_dir = CLAUDE_DIR / "skills"
    if not skills_dir.is_dir():
        return
    instaladas = sorted(p.name for p in skills_dir.iterdir() if not p.name.startswith("."))
    if not declaradas:
        rep.desvio("skills",
                   f"{len(instaladas)} skills instaladas e o manifest nao declara nenhuma",
                   f"{skills_dir}\n  " + ", ".join(instaladas[:12])
                   + ("…" if len(instaladas) > 12 else ""),
                   'adicionar "skills": {"permitidas": [...]} no manifest.json')
        return
    intrusas = [s for s in instaladas if s not in declaradas]
    sumidas = [s for s in sorted(declaradas) if s not in instaladas]
    if intrusas:
        rep.desvio("skills", f"{len(intrusas)} skill(s) instalada(s) fora da lista do manifest",
                   f"{skills_dir}\n  " + ", ".join(intrusas),
                   "ou declarar no manifest, ou remover de ~/.claude/skills")
    # "declarada e nao instalada" NAO e desvio: a lista e retrato do dono do manifest,
    # nao requisito. Em maquina de outra pessoa isso viraria uma acusacao por skill que
    # ela nunca pediu — e desvio permanente em quem nao usa ensina a ignorar o relatorio
    # inteiro. Fica so como nota, e so quando ha alguma.
    if sumidas:
        rep.conforme("skills", "%d skill(s) da lista nao estao nesta maquina (nota, nao desvio: "
                               "a lista e retrato do dono do manifest)" % len(sumidas))
    if not intrusas:
        rep.conforme("skills", f"nenhuma das {len(instaladas)} skills instaladas esta fora da lista")


def _versao(s):
    """'3.18.0' -> (3, 18, 0) pra ordenar; o cache guarda toda versao ja instalada."""
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[._-]", s)[:4])


def check_hooks_duplicados(rep, cfg):
    """Dois plugins bloqueando a MESMA ferramenta = dois denies antes do trabalho comecar.

    O matcher e uma alternancia ('Grep|Glob|Bash'), entao comparar a string inteira
    nao acha colisao parcial. A comparacao e por ferramenta.
    Do cache so vale a versao mais alta de cada plugin — as antigas nao rodam.
    """
    cache = CLAUDE_DIR / "plugins" / "cache"
    if not cache.is_dir():
        return
    settings = load_json(CLAUDE_DIR / "settings.json")
    vivo = settings.get("enabledPlugins", {}) or {}

    # so a versao mais alta de cada plugin
    mais_nova = {}
    for hj in cache.glob("*/*/*/hooks/hooks.json"):
        mkt, plug, ver = hj.parts[-5], hj.parts[-4], hj.parts[-3]
        if not vivo.get(f"{plug}@{mkt}", False):
            continue
        atual = mais_nova.get(plug)
        if atual is None or _versao(ver) > _versao(atual[0]):
            mais_nova[plug] = (ver, hj)

    # So conta quem BLOQUEIA. Registrar PreToolUse pra avisar nao custa round-trip;
    # dois denies na mesma ferramenta custam dois. Depois que o graphify-guard virou
    # aviso (2026-07-30) a contagem por registro passou a acusar colisao que nao existe.
    def bloqueia(script):
        try:
            txt = Path(script).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return True   # nao consegui ler: assume o pior
        if "conformance: default-warn" in txt:
            return False   # o script declara que so avisa por padrao
        return ('permissionDecision' in txt and '"deny"' in txt) or "exit 2" in txt

    # So vira alvo o token que carrega ${CLAUDE_PLUGIN_ROOT}/ (ou sem chaves) E resolve
    # pra um script QUE EXISTE sob a raiz do plugin — as duas unicas formas que o Claude
    # Code expande. Sem isso, '<script>.sh 2>/dev/null' virava dois alvos e o fantasma
    # '2>/dev/null' caia no except acima (assume o pior), anulando o default-warn;
    # e token absoluto escapava da raiz porque 'raiz / "/abs"' devolve "/abs".
    def alvo(raiz, tok):
        for marca in ("${CLAUDE_PLUGIN_ROOT}/", "$CLAUDE_PLUGIN_ROOT/"):
            if marca in tok:
                tok = tok.split(marca, 1)[-1]
                break
        else:
            return None   # sem a marca nao da pra afirmar que o token e um script do plugin
        # nao exigir barra no resto: com a marca arrancada, um hook na RAIZ do plugin
        # ('${CLAUDE_PLUGIN_ROOT}/guard.sh' -> 'guard.sh') e caminho legitimo. Quem
        # julga e o par is_file()+ancestralidade abaixo; a marca sozinha vira tok=''
        # e cai fora ali (a raiz nao e arquivo).
        if tok.startswith("-"):
            return None
        try:
            p = (raiz / tok).resolve()
            return p if p.is_file() and raiz.resolve() in p.parents else None
        except OSError:
            return None

    por_tool = {}
    for plug, (_ver, hj) in mais_nova.items():
        d = load_json(hj)
        raiz = hj.parent.parent
        for entrada in (d.get("hooks", {}) or {}).get("PreToolUse", []) or []:
            cmds = [h.get("command", "") for h in entrada.get("hooks", []) or []]
            alvos = []
            for c in cmds:
                try:
                    toks = shlex.split(c)   # aspa simples tambem, igual ao shell
                except ValueError:
                    toks = c.replace('"', " ").split()   # aspa sem fechar nao derruba
                for tok in toks:
                    a = alvo(raiz, tok)
                    if a is not None:
                        alvos.append(a)
            # nenhum token resolveu -> nao da pra afirmar que so avisa: conta como disputante
            if alvos and not any(bloqueia(a) for a in alvos):
                continue      # so avisa -> nao disputa a ferramenta
            for tool in str(entrada.get("matcher", "")).split("|"):
                tool = tool.strip()
                if tool:
                    por_tool.setdefault(tool, set()).add(plug)

    dups = {t: sorted(ps) for t, ps in por_tool.items() if len(ps) > 1}
    if dups:
        ev = "\n".join(f"  {t}: " + ", ".join(ps) for t, ps in sorted(dups.items()))
        rep.desvio("hooks",
                   f"{len(dups)} ferramenta(s) BLOQUEADA por mais de um plugin habilitado",
                   ev,
                   "colisao so e DEFEITO quando os gates tem o MESMO proposito — ai um vira\n"
                   "     aviso (marque o script com '# conformance: default-warn'). Gates com\n"
                   "     propositos distintos no mesmo evento sao camadas, nao duplicatas:\n"
                   "     conferido em 2026-07-30 que Agent/Bash/Edit/Write/ExitPlanMode aqui sao\n"
                   "     escopo x doc x teste-de-deploy x auditoria x render — cada um pega\n"
                   "     um caso que os outros nao pegam. Este item e para VOCE julgar, nao\n"
                   "     para cortar no automatico.")
    else:
        rep.conforme("hooks", "nenhuma ferramenta bloqueada por dois plugins")


def check_gates_enganosos(rep, cfg):
    """Gate marcado 'off' no disco enquanto o plugin dele segue habilitado — e
    gate HOMONIMO em duas pastas, que engana independente do valor."""
    settings = load_json(CLAUDE_DIR / "settings.json")
    vivo = settings.get("enabledPlugins", {}) or {}
    modos = list(CLAUDE_DIR.glob("**/*.mode"))[:200]
    achados = []
    for modo in modos:
        try:
            valor = modo.read_text(encoding="utf-8").strip()
        except Exception:
            continue
        if valor.lower() not in ("off", "0", "disabled"):
            continue
        nome = modo.stem
        ligado = [ref for ref in vivo
                  if vivo[ref] and (nome in ref or nome.split("-")[0] in ref)]
        achados.append((modo, valor, ligado))
    for modo, valor, ligado in achados:
        rep.desvio("gate", f"{modo.stem} esta '{valor}' no disco"
                   + (f" mas {ligado[0]} segue habilitado" if ligado else ""),
                   f"{modo} = {valor}",
                   "ou religar em modo aviso, ou desinstalar o plugin — "
                   "estado meio-ligado faz parecer que existe trava e nao existe")

    # Homonimo em duas pastas: o hook le so o de CLAUDE_DIR/guardrails/, o resto
    # e inerte. O defeito e a EXISTENCIA do duplicado, nao o valor dele — editar
    # o inerte nao muda comportamento nenhum e nao avisa.
    por_nome = {}
    for modo in modos:
        por_nome.setdefault(modo.stem, []).append(modo)
    duplicados = [(nome, sorted(caminhos)) for nome, caminhos in sorted(por_nome.items())
                  if len({c.parent for c in caminhos}) > 1]
    for nome, caminhos in duplicados:
        lido = CLAUDE_DIR / "guardrails" / f"{nome}.mode"
        if lido in caminhos:
            # dono conhecido (o caso do guardrails): da pra nomear vivo x inerte
            ev = "\n".join(f"{c}" + (" ← o hook LE este" if c == lido else " (inerte)")
                           for c in caminhos)
            o_que = f"{nome}.mode existe em {len(caminhos)} pastas — so uma vale"
            conserto = (f"o hook le so o de {CLAUDE_DIR / 'guardrails'}/ — editar um inerte\n"
                        "     nao muda comportamento nenhum e nao avisa. Aposente os inertes\n"
                        "     renomeando pra *.obsoleto (a skill guardrails:setup faz isso)")
        else:
            # nenhuma copia mora em guardrails/: o defeito (duplicidade) e real, mas
            # quem le qual e desconhecido — eleger vencedor ou mandar aposentar aqui
            # seria chutar, e o conserto apontaria pra uma pasta que nem existe.
            ev = "\n".join(str(c) for c in caminhos)
            o_que = f"{nome}.mode existe em {len(caminhos)} pastas"
            conserto = ("dono nao identificado: nenhuma dessas copias esta na pasta que\n"
                        "     o conformance sabe ler. Descubra qual delas o gate le de\n"
                        "     verdade antes de mexer — editar a copia errada nao muda\n"
                        "     comportamento nenhum e nao avisa")
        rep.desvio("gate", o_que, ev, conserto)

    if not achados and not duplicados:
        rep.conforme("gate", "nenhum gate em estado meio-ligado nem .mode duplicado")


def check_ferramentas_externas(rep, cfg):
    """Plugin habilitado cuja dependencia EXTERNA nao esta na maquina.

    Mesmo padrao do gate meio-ligado: o plugin instalado da a impressao de que a
    funcao existe, e ela nao existe. O graphify-guard procura graphify-out/graph.json
    e redireciona busca cega pro grafo — sem o binario `graphify` ninguem cria esse
    diretorio e o guarda vira decorativo, calado, pra sempre.
    So cobra quando o plugin que precisa esta LIGADO: quem nao usa nao e incomodado.
    """
    manifest = load_json(cfg / "manifest.json")
    itens = (manifest.get("ferramentas_externas") or {}).get("itens") or []
    if not itens:
        return
    settings = load_json(CLAUDE_DIR / "settings.json")
    vivo = settings.get("enabledPlugins", {}) or {}
    ligados = {ref.split("@")[0] for ref, on in vivo.items() if on}

    faltando = []
    for it in itens:
        precisam = [p for p in it.get("requerido_por", []) if p in ligados]
        if not precisam:
            continue
        if shutil.which(it["comando"]):
            continue
        faltando.append((it, precisam))

    for it, precisam in faltando:
        rep.desvio(
            "dependencia",
            "%s esta habilitado mas o comando `%s` nao existe nesta maquina"
            % (", ".join(precisam), it["comando"]),
            "which %s -> nada\n     %s" % (it["comando"], it.get("porque", "")),
            "%s\n     (alternativa: %s)" % (it.get("instalar", "?"), it.get("alternativa", "-")))
    if not faltando:
        rep.conforme("dependencia", "toda dependencia externa de plugin ligado esta na maquina")


def _catalogo_publicado(cfg):
    """Onde mora o marketplace.json do pedro-plugins NESTA maquina.

    Ordem: (1) o registro vivo, CLAUDE_DIR/plugins/known_marketplaces.json —
    formato conferido na maquina: {"pedro-plugins": {"source": {"source":
    "directory", "path": "/Users/..."}}} (o "source" e um objeto aninhado; a
    forma plana tambem e aceita). Marketplace de diretorio le o catalogo no
    proprio diretorio; git/github le o clone em plugins/marketplaces/.
    (2) fallback repo-relativo, pra quem roda de dentro do checkout sem ter o
    marketplace adicionado. Nenhum resolveu -> None (fail-open).
    """
    mkts = load_json(CLAUDE_DIR / "plugins" / "known_marketplaces.json")
    ent = mkts.get("pedro-plugins") if isinstance(mkts, dict) else None
    if isinstance(ent, dict):
        src = ent.get("source")
        if isinstance(src, dict):
            tipo, caminho = src.get("source"), src.get("path")
        else:
            tipo, caminho = src, ent.get("path")
        p = None
        if tipo == "directory" and caminho:
            p = Path(caminho) / ".claude-plugin" / "marketplace.json"
        elif tipo in ("git", "github"):
            p = (CLAUDE_DIR / "plugins" / "marketplaces" / "pedro-plugins"
                 / ".claude-plugin" / "marketplace.json")
        if p is not None and p.is_file():
            return p
    if cfg is not None:
        # cfg = <repo>/plugins/bootstrap/config
        p = cfg.parent.parent.parent / ".claude-plugin" / "marketplace.json"
        if p.is_file():
            return p
    return None


def check_catalogo(rep, cfg):
    """Plugin PUBLICADO no marketplace.json que o manifest nao declara.

    O manifest e a receita do que a maquina instala; o marketplace.json e o
    catalogo do que existe pra instalar. Plugin que entra no catalogo e nao
    entra na receita nunca chega em maquina nenhuma — e ninguem descobre,
    porque nada mais compara os dois lados.
    Maquina sem o marketplace instalado nao e desvio: sai calado.
    """
    cat = _catalogo_publicado(cfg)
    if cat is None:
        return
    publicados = [p.get("name") for p in (load_json(cat).get("plugins") or [])
                  if isinstance(p, dict) and p.get("name")]
    if not publicados:
        return
    manifest = load_json(cfg / "manifest.json")
    declarados = set()
    for m in manifest.get("marketplaces", []):
        if m.get("name") == "pedro-plugins":
            declarados |= {pl.get("name") for pl in m.get("plugins", []) or []}

    esquecidos = [n for n in publicados if n not in declarados]
    for nome in esquecidos:
        rep.desvio("catalogo",
                   f"{nome} esta publicado no catalogo e nao esta na receita",
                   f'{cat} tem "{nome}", '
                   f'{cfg / "manifest.json"} (marketplaces -> pedro-plugins) nao',
                   "declare em config/manifest.json")
    if not esquecidos:
        rep.conforme("catalogo",
                     f"os {len(publicados)} plugins do catalogo estao na receita")


# A cadeia da statusLine tem elos com papeis diferentes, e cada um sai de um jeito.
# Ordem importa: o ESCRITOR intercepta e encaminha; o RENDERIZADOR desenha. Escritor fora
# da cadeia nao quebra a tela — some so o dado que ele produz, em silencio.
ELOS_STATUSLINE = (
    {"plugin": "context-guard", "papel": "escritor",
     "marca": "context-guard-writer",
     "produz": "o percentual de contexto por sessao no temporario do sistema, "
               "em claude-context-pct-<session_id>",
     "quem_consome": "o guarda do context-guard, que so dispara com esse arquivo na mao",
     "conserto": "rode `/context-guard:setup` — ele registra o wrapper e move o comando "
                 "atual pra CLAUDE_STATUSLINE_FORWARD, preservando o que ja renderizava"},
    {"plugin": "project-skills", "papel": "narrador",
     "marca": "statusline-motor",
     "produz": "a linha do motor ACIMA da barra — ha quanto tempo a missao roda e "
               "quando ela falou pela ultima vez, lidos do estado em disco",
     "quem_consome": "voce, na tela, quando volta ao terminal e o systemMessage "
                     "da narracao ja rolou pra fora",
     "conserto": "ponha CLAUDE_STATUSLINE_FORWARD apontando pro "
                 "`hooks/statusline-motor.sh` do project-skills, com o comando que desenha a "
                 "barra como ARGUMENTO dele (a receita em "
                 "`config/settings-defaults.json` ja vem assim)"},
    {"plugin": "claude-hud", "papel": "renderizador",
     "marca": "claude-hud",
     "produz": "a propria barra de status",
     "quem_consome": "voce, na tela",
     "conserto": "rode `/claude-hud:setup`, ou aponte CLAUDE_STATUSLINE_FORWARD pro "
                 "`dist/index.js` dele se houver um escritor na frente"},
)


def check_statusline_meio_ligada(rep, cfg):
    """Plugin de statusLine habilitado que NAO esta na cadeia do comando.

    Mesma familia do check_gates_enganosos: o plugin aparece ligado em toda listagem,
    o dono acha que tem a funcao, e nada dispara. A diferenca e que aqui o sintoma e
    ainda mais mudo — statusLine que perdeu o ESCRITOR continua desenhando bonito,
    porque quem sumiu foi o elo que grava dado pra outro consumir.

    Medido em 2026-08-02 nesta maquina: `context-guard` habilitado, writer fora do
    comando, e o unico claude-context-pct-* no temporario era um fixture de teste de
    tres dias antes. Nenhuma sessao real gravou, e nenhum check acusava.
    """
    settings = load_json(CLAUDE_DIR / "settings.json")
    if not settings:
        return
    vivo = settings.get("enabledPlugins", {}) or {}
    sl = (settings.get("statusLine") or {}).get("command") or ""
    fwd = ((settings.get("env") or {}).get("CLAUDE_STATUSLINE_FORWARD") or "")
    # A cadeia inteira e o comando MAIS o forward: um elo pode morar em qualquer um dos
    # dois. Procurar so no comando acusaria o renderizador toda vez que ele for o forward.
    cadeia = sl + "\n" + fwd

    if not sl:
        # Sem statusLine nenhuma e escolha legitima; so vira desvio se algum elo esta ligado.
        ligados = [e for e in ELOS_STATUSLINE
                   if any(k.split("@")[0] == e["plugin"] and v for k, v in vivo.items())]
        if ligados:
            rep.desvio("statusline", "plugin de statusLine habilitado sem statusLine configurada",
                       "settings.json nao tem statusLine.command · ligados: "
                       + ", ".join(e["plugin"] for e in ligados),
                       ligados[0]["conserto"])
        return

    for elo in ELOS_STATUSLINE:
        habilitado = any(k.split("@")[0] == elo["plugin"] and v for k, v in vivo.items())
        if not habilitado or elo["marca"] in cadeia:
            continue
        rep.desvio(
            "statusline",
            "%s (%s) esta habilitado e FORA da cadeia da statusLine" % (elo["plugin"], elo["papel"]),
            "nem statusLine.command nem CLAUDE_STATUSLINE_FORWARD citam %r — "
            "entao %s nunca acontece, e quem esperava isso (%s) fica sem dado"
            % (elo["marca"], elo["produz"], elo["quem_consome"]),
            elo["conserto"])

    presentes = [e["plugin"] for e in ELOS_STATUSLINE if e["marca"] in cadeia]
    if presentes:
        rep.conforme("statusline", "na cadeia: " + " → ".join(presentes))


CHECAGENS = [check_plugins, check_claude_md, check_teto_unico,
             check_output_style, check_skills, check_hooks_duplicados,
             check_gates_enganosos,
             check_ferramentas_externas, check_catalogo, check_statusline_meio_ligada]


def main():
    # O console do Windows codifica a saida em cp1252, e a seta `→` do conserto
    # nao existe nessa tabela: o programa morria de UnicodeEncodeError ANTES de
    # escrever o JSON, e quem chamava recebia stdout vazio. Sai sempre em UTF-8.
    for canal in (sys.stdout, sys.stderr):
        try:
            canal.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass  # canal exotico (pipe ja embrulhado, py antigo) — segue como esta

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="saida estruturada")
    ap.add_argument("--quiet", action="store_true", help="so o resumo")
    args = ap.parse_args()

    cfg = repo_config_dir()
    if cfg is None:
        print("conformance: nao achei o config/ versionado do bootstrap.", file=sys.stderr)
        return 1

    rep = Report()
    for fn in CHECAGENS:
        try:
            fn(rep, cfg)
        except Exception as e:  # uma checagem quebrada nunca derruba o relatorio
            rep.desvio("interno", f"a checagem {fn.__name__} falhou", repr(e),
                       "abrir issue / conferir lib/conformance.py")

    if args.json:
        print(json.dumps({"desvios": rep.desvios, "conforme": rep.ok},
                         ensure_ascii=False, indent=1))
        return 1 if rep.desvios else 0

    if not rep.desvios:
        print(f"✓ conforme — {len(rep.ok)} checagens passaram, nenhum desvio.")
        return 0

    if args.quiet:
        print(f"⚠ {len(rep.desvios)} desvio(s) de conformidade. "
              f"Rode: python3 {Path(__file__).name}")
        return 1

    print(f"⚠ {len(rep.desvios)} desvio(s) — nada foi alterado.\n")
    for i, d in enumerate(rep.desvios, 1):
        print(f"{i}. [{d['area']}] {d['o_que']}")
        for ln in d["evidencia"].splitlines():
            print(f"     {ln}")
        print(f"   → {d['conserto']}\n")
    if rep.ok:
        print("conforme: " + " · ".join(o["area"] for o in rep.ok))
    return 1


if __name__ == "__main__":
    sys.exit(main())
