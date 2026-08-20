#!/usr/bin/env python3
"""branch_state.py — quais branches dá pra apagar, e quais NÃO dá.

Por que existe
--------------
O problema nunca foi apagar branch: é saber **quais**. E a ferramenta que todo
mundo usa pra isso, `git branch --merged`, **mente por omissão** — ela só
enxerga merge por ancestralidade. Squash-merge (o botão padrão do GitHub) e
rebase produzem commits com sha novo, então a branch original aparece como
"não mergeada" mesmo com o conteúdo inteiro já na main.

Medido no pedro-plugins em 2026-07-28:

    doc/readme      git --merged: NÃO     conteúdo na main: SIM (squash)

É isso que faz a pilha crescer: você não confia na lista, então não apaga
nenhuma, e em seis meses são quinze.

As três categorias
------------------
    merged        o git já reconhece — apagar é seguro e trivial
    equivalent    conteúdo já está na base por patch (squash/rebase/cherry-pick)
                  → seguro TAMBÉM, e é exatamente o que o --merged perde
    unique        tem commit que só existe ali → NÃO é lixo, é trabalho

A terceira é a razão de este módulo não apagar nada sozinho. Uma limpeza em
bloco mataria justamente o que você esqueceu de mergear — que é o caso que
dói. Aqui a gente MEDE; quem decide é o humano, olhando o que perderia.

Só stdlib. O único verbo que ESCREVE é o `prune` — e ele exige nomes explícitos,
cria tag de resgate antes de cada remoção e recusa branch com trabalho exclusivo.
"""

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regua_texto import erros_de_estilo as _erros_de_estilo  # noqa: E402

# A régua de estilo (quality-goals.md, regime "informação rápida"): esta página é
# relatório, lido com pressa, então vale a mesma régua do gerador de página. As
# quatro checagens moram em `_shared/regua_texto.py`; aqui só se DECLARA o perfil.
PERFIL = "pagina"

# Bases prováveis, na ordem em que se procura quando o remoto não diz qual é.
BASE_FALLBACKS = ("main", "master", "trunk", "develop")
PARADA_DIAS = 30   # a partir daqui uma branch conta como "parada"


class BranchError(Exception):
    pass


def git(repo, *args, **kw):
    """git, com saída limpa. `ok_fail` devolve None em vez de levantar."""
    # `encoding` EXPLÍCITO: com `text=True` sozinho o Python decodifica pela
    # codificação do sistema, que no Windows é cp1252 — e a saída do git é UTF-8.
    # Todo acento virava lixo: a esteira acusou por um assunto de commit com "só",
    # que o relatório do /branches mostraria mojibake para quem decide o que apagar.
    # `replace` porque assunto de commit alheio não é dado confiável: melhor um
    # caractere trocado do que a leitura inteira estourando.
    out = subprocess.run(("git", "-C", repo) + args, capture_output=True, text=True,
                         encoding="utf-8", errors="replace",
                         stdin=subprocess.DEVNULL, start_new_session=True)
    if out.returncode != 0:
        if kw.get("ok_fail"):
            return None
        raise BranchError("git %s falhou em %s: %s"
                          % (" ".join(args), repo, (out.stderr or "").strip()[:200]))
    return out.stdout.rstrip("\n")


def is_repo(path):
    return git(path, "rev-parse", "--git-dir", ok_fail=True) is not None


def resolve_base(repo, explicit=None):
    """Qual é o tronco. Pergunta ao remoto primeiro — adivinhar 'main' quebra
    em repo antigo que usa 'master', e quebrar aqui classifica TUDO errado."""
    if explicit:
        if git(repo, "rev-parse", "--verify", explicit, ok_fail=True) is None:
            raise BranchError("base '%s' não existe em %s" % (explicit, repo))
        return explicit
    head = git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", ok_fail=True)
    if head:
        return head.rsplit("/", 1)[-1]
    for cand in BASE_FALLBACKS:
        if git(repo, "rev-parse", "--verify", cand, ok_fail=True) is not None:
            return cand
    raise BranchError("não achei o tronco em %s (tentei %s) — passe --base"
                      % (repo, ", ".join(BASE_FALLBACKS)))


def _int(v, default=0):
    try:
        return int((v or "").strip())
    except (TypeError, ValueError):
        return default


def orphan_commits(repo, base, branch, cap=8):
    """Os commits que só existem na branch, por CONTEÚDO (patch-id).

    `git cherry` marca com '-' o commit cujo patch equivalente já está na base
    (squash/rebase/cherry-pick) e com '+' o que é de fato exclusivo. É essa
    distinção que o `--merged` não faz.
    """
    raw = git(repo, "cherry", base, branch, ok_fail=True)
    if raw is None:
        return None, None
    total = uniques = 0
    shas = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        total += 1
        if line.startswith("+"):
            uniques += 1
            shas.append(line.split()[-1])
    detail = []
    for sha in shas[:cap]:
        subj = git(repo, "log", "-1", "--format=%s", sha, ok_fail=True) or ""
        files = git(repo, "show", "--name-only", "--format=", sha, ok_fail=True) or ""
        files = [f for f in files.splitlines() if f.strip()]
        detail.append({"sha": sha[:9], "subject": subj[:120],
                       "files": files[:6], "n_files": len(files)})
    return {"total": total, "unique": uniques, "commits": detail}, shas


def classify(repo, base=None, include_remote=False):
    """Uma linha por branch. NÃO escreve nada."""
    base = resolve_base(repo, base)
    merged = set()
    raw = git(repo, "branch", "--merged", base, "--format=%(refname:short)", ok_fail=True)
    if raw:
        merged = {b.strip() for b in raw.splitlines() if b.strip()}

    fmt = "%(refname:short)%09%(committerdate:unix)%09%(upstream:short)"
    raw = git(repo, "branch", "--format=" + fmt, ok_fail=True) or ""
    # relógio de verdade, não o último commit da base: com a base parada, uma
    # branch MAIS NOVA que ela dava idade 0 e sumia do radar de "parada".
    now = int(time.time())
    head = git(repo, "rev-parse", "--abbrev-ref", "HEAD", ok_fail=True)

    out = []
    for line in raw.splitlines():
        parts = line.split("\t")
        name = parts[0].strip()
        if not name or name == base:
            continue
        ts = _int(parts[1] if len(parts) > 1 else "", 0)
        upstream = (parts[2].strip() if len(parts) > 2 else "")
        ahead = _int(git(repo, "rev-list", "--count", "%s..%s" % (base, name), ok_fail=True))
        behind = _int(git(repo, "rev-list", "--count", "%s..%s" % (name, base), ok_fail=True))
        orph, _shas = orphan_commits(repo, base, name)

        if name in merged:
            cat, why = "merged", "o git já reconhece o merge"
        elif ahead == 0:
            cat, why = "merged", "não tem nada à frente da base"
        elif orph and orph["unique"] == 0:
            n = orph["total"]
            cat, why = "equivalent", ("%s já %s na base por conteúdo (squash/rebase) — "
                                      "o --merged NÃO vê isto"
                                      % ("o commit" if n == 1 else "os %d commits" % n,
                                         "está" if n == 1 else "estão"))
        elif orph is None:
            cat, why = "unknown", "não consegui comparar os commits com a base"
        else:
            u, t = orph["unique"], orph["total"]
            cat, why = "unique", ("%d de %d commit%s só existe%s aqui"
                                  % (u, t, "" if t == 1 else "s", "" if u == 1 else "m"))

        out.append({
            "name": name, "category": cat, "why": why,
            "ahead": ahead, "behind": behind,
            "dias": max(0, (now - ts) // 86400) if (now and ts) else None,
            "upstream": upstream or None,
            "is_head": name == head,
            "orphans": orph,
        })
    out.sort(key=lambda b: ({"unique": 0, "unknown": 1, "equivalent": 2, "merged": 3}[b["category"]],
                            -(b["dias"] or 0)))
    return {"repo": os.path.abspath(repo), "base": base, "head": head, "branches": out}


def scan(root, base=None, depth=3):
    """Vários repositórios de uma vez — o problema é da pasta de projetos, não
    de um repo só. Não desce em node_modules e afins."""
    PRUNE = {"node_modules", ".git", "vendor", "dist", "build", "__pycache__",
             ".venv", "venv", "target", ".next"}
    found, root = [], os.path.abspath(root)
    base_depth = root.rstrip(os.sep).count(os.sep)
    for cur, dirs, _files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PRUNE and not d.startswith(".")]
        if cur.rstrip(os.sep).count(os.sep) - base_depth >= depth:
            dirs[:] = []
        if os.path.isdir(os.path.join(cur, ".git")):
            dirs[:] = []          # não desce em submódulo/worktree aninhado
            try:
                found.append(classify(cur, base))
            except BranchError as exc:
                found.append({"repo": cur, "error": str(exc), "branches": []})
    return found


# ── saída ──────────────────────────────────────────────────────────────────

BADGE = {"merged": "✅", "equivalent": "✅", "unique": "⚠️ ", "unknown": "❔"}
GRUPO = [("merged", "SEGURAS — o git já reconhece o merge"),
         ("equivalent", "SEGURAS — conteúdo já está na base (o --merged NEGA estas)"),
         ("unknown", "NÃO CONSEGUI DIZER"),
         ("unique", "OLHE ANTES — têm commit que só existe ali")]


def report(res):
    L = ["%s   (tronco: %s)" % (res["repo"], res["base"])]
    if not res["branches"]:
        L.append("  nenhuma branch além do tronco.")
        return "\n".join(L) + "\n"
    for cat, titulo in GRUPO:
        grupo = [b for b in res["branches"] if b["category"] == cat]
        if not grupo:
            continue
        L.append("")
        L.append("%s %s (%d)" % (BADGE[cat], titulo, len(grupo)))
        for b in grupo:
            idade = ("%dd" % b["dias"]) if b["dias"] is not None else "?"
            flags = "".join([" [HEAD]" if b["is_head"] else "",
                             "" if b["upstream"] else " [só local]"])
            L.append("   %-44s %5s  %s%s" % (b["name"], idade, b["why"], flags))
            if cat == "unique" and b["orphans"]:
                for c in b["orphans"]["commits"]:
                    L.append("        %s %s" % (c["sha"], c["subject"]))
                    if c["files"]:
                        L.append("           %s%s" % (", ".join(c["files"][:4]),
                                                      " …" if c["n_files"] > 4 else ""))
    L.append("")
    L.append("Nada foi apagado. Este comando só mede — quem decide é você.")
    return "\n".join(L) + "\n"


def cmd_list(args):
    if args.scan:
        todos = scan(args.scan, args.base, args.depth)
        if args.json:
            print(json.dumps(todos, ensure_ascii=False, indent=2))
            return 0
        vistos = 0
        for res in todos:
            if res.get("error"):
                sys.stderr.write("⚠️  %s: %s\n" % (res["repo"], res["error"]))
                continue
            if not res["branches"]:
                continue
            vistos += 1
            sys.stdout.write(report(res) + "\n")
        if not vistos:
            print("Nenhum repositório com branch além do tronco em %s." % args.scan)
        return 0
    repo = args.repo or os.getcwd()
    if not is_repo(repo):
        raise BranchError("%s não é um repositório git" % repo)
    res = classify(repo, args.base)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(report(res))
    return 0


def cmd_stale(args):
    """Só a contagem, pro hook de começo de sessão. Barato de propósito."""
    repo = args.repo or os.getcwd()
    if not is_repo(repo):
        return 0
    try:
        res = classify(repo, args.base)
    except BranchError:
        return 0
    dias = args.dias
    paradas = [b for b in res["branches"]
               if b["dias"] is not None and b["dias"] >= dias and not b["is_head"]]
    seguras = [b for b in paradas if b["category"] in ("merged", "equivalent")]
    if not paradas:
        return 0
    print(json.dumps({"repo": res["repo"], "base": res["base"], "dias": dias,
                      "paradas": len(paradas), "seguras": len(seguras),
                      "nomes": [b["name"] for b in paradas[:5]]}, ensure_ascii=False))
    return 0


# ── relatório HTML e a limpeza com rede ────────────────────────────────────
#
# HTML autocontido (mesmo padrão do fallow/lib/report.py): plugin não consegue
# ler o template de outro plugin — o Claude Code isola cada um na instalação.

def resolve_visual_dir(repo):
    """Onde o relatório é escrito: <raiz-git>/.claude/visual, senão ~/Desktop."""
    root = git(repo, "rev-parse", "--show-toplevel", ok_fail=True)
    if root:
        return os.path.join(root, ".claude", "visual")
    return os.path.join(os.path.expanduser("~"), "Desktop", "claude-visual")


def _e(t):
    return (str(t or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


HTML_CSS = """
:root{--bg:#1A1625;--card:#2A2438;--deep:#221D2E;--tx:#F0EDF5;--dim:#A599B5;
--mut:#7A7089;--ac:#FFA88C;--ok:#7FD1AE;--warn:#FFD166;--dg:#FF6B8A;
--bd:rgba(255,255,255,.08)}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--tx);font:16px/1.6 -apple-system,BlinkMacSystemFont,'SF Pro Display',sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:960px;margin:0 auto;padding:56px 28px 160px}
h1{font-size:34px;font-weight:800;letter-spacing:-.02em;margin-bottom:6px}
.sub{color:var(--dim);font-size:15px;margin-bottom:22px}
.ident{background:var(--deep);border:1px solid var(--bd);border-left:3px solid var(--ac);
border-radius:12px;padding:12px 16px;margin-bottom:22px;font-size:13px;color:var(--dim)}
.ident b{color:var(--tx)}
.grp{background:var(--card);border:1px solid var(--bd);border-radius:18px;padding:18px 20px;margin-bottom:16px}
.grp h2{font-size:16px;margin-bottom:4px}
.grp .hint{color:var(--dim);font-size:13px;margin-bottom:14px}
.grp.safe{border-left:3px solid var(--ok)}
.grp.risk{border-left:3px solid var(--warn)}
.br{display:flex;gap:11px;align-items:flex-start;padding:10px 0;border-top:1px solid var(--bd)}
.br:first-of-type{border-top:none}
.br input{margin-top:4px;width:16px;height:16px;accent-color:var(--ac);cursor:pointer;flex:none}
.br .nm{font-weight:650;font-size:14.5px;font-family:ui-monospace,Menlo,monospace}
.br .wy{color:var(--dim);font-size:12.5px;line-height:1.5}
.br .tag{font-size:11px;color:var(--mut);margin-left:6px}
.cm{margin:6px 0 0 0;padding-left:12px;border-left:1px solid var(--bd)}
.cm div{font-size:12px;color:var(--dim);font-family:ui-monospace,Menlo,monospace;padding:2px 0}
.cm .fl{color:var(--mut);font-size:11.5px}
.foot{position:sticky;bottom:0;background:linear-gradient(transparent,var(--bg) 26%);
padding:22px 0 8px;margin-top:24px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
button{background:var(--ac);color:#1A1625;border:0;border-radius:11px;padding:11px 20px;
font-size:14px;font-weight:700;cursor:pointer;font-family:inherit}
button.gh{background:transparent;color:var(--tx);border:1px solid var(--bd)}
#cnt{color:var(--dim);font-size:13px}
pre{background:#12101a;border:1px solid var(--bd);border-radius:11px;padding:13px 15px;
overflow:auto;font:12.5px/1.6 ui-monospace,Menlo,monospace;color:#D9D3E4;margin-top:14px}
mark{background:rgba(255,168,140,.22);color:var(--ac);padding:0 3px;border-radius:3px}
"""

HTML_JS = """
function marcadas(){return [...document.querySelectorAll('.br input:checked')].map(i=>i.dataset.br)}
function upd(){const n=marcadas().length;
 document.getElementById('cnt').textContent = n===0 ? 'nenhuma marcada'
   : (n===1 ? '1 branch marcada' : n+' branches marcadas');}
function copiar(btn){const b=marcadas();
 if(!b.length){alert('Nenhuma branch marcada.');return;}
 const t='<!-- branches-apagar v1 -->\n🌿 **Apagar estas branches:**\n'
   + b.map(x=>'- '+x).join('\n') + '\n<!-- /branches-apagar -->';
 navigator.clipboard.writeText(t).then(()=>{const o=btn.textContent;
   btn.textContent='✓ copiado';setTimeout(()=>btn.textContent=o,1600);});}
function todas(v){document.querySelectorAll('.grp.safe .br input').forEach(i=>i.checked=v);upd();}
document.addEventListener('change',e=>{if(e.target.matches('.br input'))upd();});
document.addEventListener('DOMContentLoaded',upd);
"""


def erros_de_estilo(v, onde):
    """A régua no perfil DESTE gerador — a definição mora em `regua_texto.py`.

    Fora do alcance de propósito: assunto de commit e nome de arquivo, que são
    citação do git e não redação desta página.
    """
    return _erros_de_estilo(v, onde, PERFIL)


def render_html(res, stamp):
    # O `why` de cada branch é o único texto autoral que entra nesta página — o
    # resto é nome de branch, assunto de commit e rótulo fixo. Quem o escreve é
    # `classify`, então violação aqui é defeito DESTE arquivo: a página é RECUSADA
    # com os motivos. Aviso no stderr deixava o relatório torto nascer assim mesmo,
    # e ninguém lê stderr de um comando que terminou imprimindo um caminho.
    errs = []
    for b in res["branches"]:
        errs.extend(erros_de_estilo(b["why"], "branch %s: why" % b["name"]))
    if errs:
        raise BranchError("relatório recusado pela régua de estilo:\n  - "
                          + "\n  - ".join(errs))

    seguras = [b for b in res["branches"] if b["category"] in ("merged", "equivalent")]
    risco = [b for b in res["branches"] if b["category"] not in ("merged", "equivalent")]
    proj = os.path.basename(res["repo"])

    def linha(b, marcada):
        tags = []
        if b["is_head"]:
            tags.append("você está nela")
        if not b["upstream"]:
            tags.append("só local")
        if b["dias"] is not None:
            tags.append("parada há %dd" % b["dias"])
        det = ""
        if b["orphans"] and b["orphans"]["commits"]:
            itens = []
            for c in b["orphans"]["commits"]:
                fl = ", ".join(c["files"][:4]) + (" …" if c["n_files"] > 4 else "")
                itens.append("<div>%s %s<div class='fl'>%s</div></div>"
                             % (_e(c["sha"]), _e(c["subject"]), _e(fl)))
            det = "<div class='cm'>%s</div>" % "".join(itens)
        dis = " disabled" if b["is_head"] else ""
        return ("<div class='br'><input type='checkbox' data-br='%s'%s%s>"
                "<div><div class='nm'>%s<span class='tag'>%s</span></div>"
                "<div class='wy'>%s</div>%s</div></div>"
                % (_e(b["name"]), " checked" if marcada and not b["is_head"] else "", dis,
                   _e(b["name"]), _e(" · ".join(tags)), _e(b["why"]), det))

    partes = []
    if seguras:
        partes.append(
            "<div class='grp safe'><h2>✅ Seguras — o conteúdo já está no tronco (%d)</h2>"
            "<p class='hint'>Já vêm marcadas. As de baixo o <code>git branch --merged</code> "
            "NÃO reconhece: o conteúdo entrou por squash ou rebase, com sha novo.</p>%s</div>"
            % (len(seguras), "".join(linha(b, True) for b in seguras)))
    if risco:
        partes.append(
            "<div class='grp risk'><h2>⚠️ Olhe antes — têm commit que só existe ali (%d)</h2>"
            "<p class='hint'>Nascem DESMARCADAS de propósito. Abaixo de cada uma está o que "
            "você perderia: assunto e arquivos dos commits que não estão no tronco.</p>%s</div>"
            % (len(risco), "".join(linha(b, False) for b in risco)))
    if not partes:
        partes.append("<div class='grp safe'><h2>Nada a limpar</h2>"
                      "<p class='hint'>Só existe o tronco neste repositório.</p></div>")

    return ("<!DOCTYPE html><html lang='pt-BR'><head><meta charset='UTF-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Branches · %s</title><style>%s</style></head><body><div class='wrap'>"
            "<div class='ident'><b>Projeto</b> %s &nbsp;·&nbsp; <b>Tronco</b> %s "
            "&nbsp;·&nbsp; <b>Medido em</b> %s &nbsp;·&nbsp; <b>Comando</b> "
            "branch_state.py report</div>"
            "<h1>O que dá pra apagar, e o que <em>não</em> dá.</h1>"
            "<p class='sub'>Marque o que quer apagar e copie. Nada é apagado por esta página — "
            "ela só mede e você escolhe.</p>%s"
            "<div class='foot'><button onclick='copiar(this)'>📋 Copiar as marcadas</button>"
            "<button class='gh' onclick='todas(true)'>marcar todas as seguras</button>"
            "<button class='gh' onclick='todas(false)'>desmarcar</button>"
            "<span id='cnt'></span></div>"
            "<pre>Antes de apagar, cada branch vira uma tag de resgate:\n"
            "  <mark>archive/&lt;branch&gt;-&lt;data&gt;</mark>\n"
            "Voltar atrás é <mark>git branch &lt;nome&gt; archive/&lt;branch&gt;-&lt;data&gt;</mark> — "
            "um comando, não arqueologia no reflog.</pre>"
            "</div><script>%s</script></body></html>"
            % (_e(proj), HTML_CSS, _e(proj), _e(res["base"]), _e(stamp),
               "".join(partes), HTML_JS))


def cmd_report(args):
    repo = args.repo or os.getcwd()
    if not is_repo(repo):
        raise BranchError("%s não é um repositório git" % repo)
    res = classify(repo, args.base)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    out = args.out or os.path.join(resolve_visual_dir(repo),
                                   "%s-branches-%s.html" % (time.strftime("%Y-%m-%d"),
                                                            os.path.basename(res["repo"])))
    # Renderiza ANTES de abrir o arquivo: `open(…, "w")` trunca na hora, então
    # recusa da régua com o arquivo já aberto deixaria um HTML vazio no lugar.
    page = render_html(res, stamp)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(out)
    return 0


def cmd_prune(args):
    """Apaga branch — o ÚNICO verbo que escreve. Três travas:
    nomes explícitos (nunca 'todas as seguras'), tag de resgate antes de cada
    remoção, e recusa de branch com trabalho exclusivo sem --force."""
    repo = args.repo or os.getcwd()
    if not is_repo(repo):
        raise BranchError("%s não é um repositório git" % repo)
    res = classify(repo, args.base)
    porname = {b["name"]: b for b in res["branches"]}

    alvos, recusadas = [], []
    for nome in args.branches:
        b = porname.get(nome)
        if b is None:
            raise BranchError("branch '%s' não existe (ou é o tronco '%s')" % (nome, res["base"]))
        if b["is_head"]:
            raise BranchError("'%s' é a branch em que você está — troque antes" % nome)
        if b["category"] in ("unique", "unknown") and not args.force:
            recusadas.append(b)
        else:
            alvos.append(b)

    if recusadas:
        linhas = ["⛔ %d branch(es) têm trabalho que só existe nelas:" % len(recusadas)]
        for b in recusadas:
            linhas.append("   %-40s %s" % (b["name"], b["why"]))
            for c in (b["orphans"] or {}).get("commits", [])[:3]:
                linhas.append("       %s %s" % (c["sha"], c["subject"]))
        linhas.append("")
        linhas.append("Mergeie, ou passe --force se souber que pode perder.")
        raise BranchError("\n".join(linhas))

    if args.dry_run:
        for b in alvos:
            print("apagaria %-40s (tag archive/%s-%s)" % (b["name"], b["name"], time.strftime("%Y%m%d")))
        return 0

    dia = time.strftime("%Y%m%d")
    feitas = []
    for b in alvos:
        tag = "archive/%s-%s" % (b["name"], dia)
        sha = git(repo, "rev-parse", b["name"], ok_fail=True)
        if git(repo, "tag", "-f", tag, b["name"], ok_fail=True) is None:
            raise BranchError("não consegui criar a tag de resgate de '%s' — nada foi apagado" % b["name"])
        if git(repo, "branch", "-D", b["name"], ok_fail=True) is None:
            raise BranchError("não consegui apagar '%s' (a tag %s ficou)" % (b["name"], tag))
        feitas.append((b["name"], tag, (sha or "")[:9]))

    for nome, tag, sha in feitas:
        print("🗑  %-40s apagada · resgate: %s (%s)" % (nome, tag, sha))
    if feitas:
        print("")
        print("Voltar atrás: git branch <nome> <tag-de-resgate>")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="branch_state.py", description=__doc__.split("\n")[0])
    p.add_argument("--repo", help="repositório (default: cwd)")
    p.add_argument("--base", help="tronco (default: o que o remoto disser, senão main/master)")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("list", help="classifica as branches (não apaga nada)")
    q.add_argument("--json", action="store_true")
    q.add_argument("--scan", help="varre todos os repositórios abaixo deste diretório")
    q.add_argument("--depth", type=int, default=3, help="profundidade da varredura (default 3)")
    q.set_defaults(func=cmd_list)

    q = sub.add_parser("stale", help="só a contagem de branches paradas (pro hook)")
    q.add_argument("--dias", type=int, default=PARADA_DIAS)
    q.set_defaults(func=cmd_stale)

    q = sub.add_parser("report", help="relatório HTML com checkbox por branch")
    q.add_argument("--out", help="caminho do HTML (default: <raiz>/.claude/visual/)")
    q.set_defaults(func=cmd_report)

    q = sub.add_parser("prune", help="apaga as branches NOMEADAS (cria tag de resgate antes)")
    q.add_argument("branches", nargs="+")
    q.add_argument("--force", action="store_true",
                   help="apaga mesmo tendo trabalho exclusivo (a tag de resgate continua)")
    q.add_argument("--dry-run", action="store_true", dest="dry_run")
    q.set_defaults(func=cmd_prune)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BranchError as exc:
        sys.stderr.write("%s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
