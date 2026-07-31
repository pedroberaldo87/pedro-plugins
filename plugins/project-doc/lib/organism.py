#!/usr/bin/env python3
"""organism.py — parser + query engine do organism.yaml (registro de costuras).

Consumido pelos hooks (bash chama via `python3 organism.py <cmd> ...` e lê o JSON)
e, futuramente, pela skill project-doc (cobertura + 2ª projeção).

O organism.yaml é DADO CURADO — este módulo só o lê e responde perguntas:
  match <abs_path>           → costuras que o path toca + blast-radius (os módulos das outras pontas)
  marker <start_path>        → { organism: bool, root, name } (está dentro de um organismo?)
  verify-cite <root> <id> <arquivo:linha>  → { valid: bool, reason } (a refutação cita algo real?)

Princípios (do design com o Fable):
- SISTEMA afirma, agente refuta. Este módulo só produz a afirmação (o que o path toca).
- Globs CIRÚRGICOS (arquivos, não módulos) — a curadoria no yaml garante isso.
- Fail-open na borda: sem organism.yaml, `match` devolve [] (o hook deixa passar).
- Stdlib + PyYAML apenas. Sem estado, sem rede.
"""
import json
import os
import re
import sys

ORGANISM_FILE = os.path.join(".claude", "organism.yaml")


# ---------------------------------------------------------------------------
# YAML loading — PyYAML se disponível, senão um parser embutido (stdlib-only).
# O parser cobre o SUBCONJUNTO que o organism.yaml usa (mappings aninhados por
# indentação, listas, listas de mappings, inline lists [a,b], block scalars > e |,
# comentários, bool/int/float/null). Testado por PARIDADE com PyYAML em
# test_organism.py — se encontrar construção fora do subconjunto, LEVANTA erro
# (nunca produz parse errado silencioso). O project-doc é stdlib-puro; PyYAML não
# é garantido numa máquina limpa, então o kit não pode depender dele.
# ---------------------------------------------------------------------------
def load_yaml_file(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    try:
        import yaml  # preferencial quando presente
        return yaml.safe_load(text) or {}
    except ImportError:
        return mini_yaml(text) or {}


def _strip_comment(line):
    """Remove comentário (# no início ou ' #' fora de aspas). Preserva # em aspas."""
    in_s = None
    for i, ch in enumerate(line):
        if in_s:
            if ch == in_s:
                in_s = None
        elif ch in ('"', "'"):
            in_s = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _split_top(s):
    """Split por vírgula no nível 0 (fora de aspas/colchetes) — para inline lists."""
    out, cur, depth, in_s = [], "", 0, None
    for ch in s:
        if in_s:
            cur += ch
            if ch == in_s:
                in_s = None
        elif ch in ('"', "'"):
            in_s = ch
            cur += ch
        elif ch == "[":
            depth += 1
            cur += ch
        elif ch == "]":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _scalar(v):
    v = v.strip()
    if v == "":
        return None
    if v[0] == '"' and v[-1] == '"' and len(v) >= 2:
        return v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if v[0] == "'" and v[-1] == "'" and len(v) >= 2:
        return v[1:-1].replace("''", "'")
    if v[0] == "[" and v[-1] == "]":
        inner = v[1:-1].strip()
        return [_scalar(x) for x in _split_top(inner)] if inner else []
    # bool/null — paridade com o resolver YAML 1.1 do PyYAML (case-específico).
    if v in ("true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"):
        return True
    if v in ("false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF"):
        return False
    if v in ("null", "Null", "NULL", "~"):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


_KV_RE = re.compile(r'^([A-Za-z0-9_./\-]+):(\s+.*)?$')


def mini_yaml(text):
    """Parser YAML de subconjunto, stdlib-only. Levanta ValueError no não-suportado."""
    raw = text.split("\n")
    # Linhas lógicas: (indent, content, forced_value). forced_value != None só para
    # block scalars (> / |), cujo valor (com \n) é guardado direto — nunca
    # re-serializado (um \n numa linha `key: "..."` quebraria o parser).
    lines = []
    i = 0
    while i < len(raw):
        line = _strip_comment(raw[i]).rstrip()
        if line.strip() == "":
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        m = re.match(r"^(-\s+)?([A-Za-z0-9_./\-]+):\s*([>|])([+-]?)\s*$", content)
        if m:
            style, chomp = m.group(3), m.group(4)  # style: > | ; chomp: '' - +
            j, parts = i + 1, []
            while j < len(raw):
                nxt = raw[j]
                if nxt.strip() == "":
                    parts.append("")
                    j += 1
                    continue
                nind = len(nxt) - len(nxt.lstrip(" "))
                if nind <= indent:
                    break
                parts.append(nxt.rstrip())
                j += 1
            trailing = 0  # linhas em branco finais (para o chomping keep '+')
            for p in reversed(parts):
                if p.strip() == "":
                    trailing += 1
                else:
                    break
            nonempty = [p for p in parts if p.strip()]
            base = min((len(p) - len(p.lstrip(" ")) for p in nonempty), default=0)
            dedent = [p[base:] for p in parts]
            if style == ">":  # folded: junta linhas de conteúdo com espaço
                val = " ".join(p.strip() for p in dedent if p.strip())
            else:  # literal: preserva quebras (sem os trailing blanks)
                val = "\n".join(dedent[:len(dedent) - trailing] if trailing else dedent)
            # chomping: '-' strip (sem \n) · '+' keep (todos os finais) · '' clip (um só)
            if chomp == "-":
                pass
            elif chomp == "+":
                val += "\n" * max(trailing, 1)
            else:
                val += "\n"
            lines.append((indent, (m.group(1) or "") + m.group(2) + ":", val))
            i = j
        else:
            lines.append((indent, content, None))
            i += 1

    pos = [0]

    def parse(min_indent):
        node = None  # dict ou list, decidido pelo 1º filho
        while pos[0] < len(lines):
            indent, content, forced = lines[pos[0]]
            if indent < min_indent:
                break
            if content.startswith("- "):
                if node is None:
                    node = []
                if not isinstance(node, list):
                    raise ValueError("mistura lista/mapping em: %r" % content)
                item = content[2:].strip()
                if item.startswith("- "):  # lista-de-lista: fora do subconjunto → não finge parsear
                    raise ValueError("lista-de-lista não suportada: %r" % content)
                child_indent = indent + 2
                km = _KV_RE.match(item)
                if km:  # item é um mapping (- key: value ...) — reindenta e propaga forced
                    lines[pos[0]] = (child_indent, item, forced)
                    node.append(parse(child_indent))
                else:  # item escalar
                    pos[0] += 1
                    node.append(_scalar(item))
            else:
                km = _KV_RE.match(content)
                if not km:
                    raise ValueError("linha não-suportada: %r" % content)
                if node is None:
                    node = {}
                if not isinstance(node, dict):
                    raise ValueError("mistura mapping/lista em: %r" % content)
                key = km.group(1)
                rest = (km.group(2) or "").strip()
                pos[0] += 1
                if forced is not None:  # block scalar
                    node[key] = forced
                elif rest == "":  # bloco aninhado (ou chave vazia → None, paridade PyYAML)
                    node[key] = parse(indent + 1)
                else:
                    node[key] = _scalar(rest)
        return node  # None quando não houve filho (chave vazia) — load_yaml_file faz `or {}`

    return parse(0)


def find_organism(start_path):
    """Sobe de start_path até achar .claude/organism.yaml. Retorna (root, data) ou (None, None)."""
    d = os.path.abspath(start_path)
    if os.path.isfile(d):
        d = os.path.dirname(d)
    while True:
        cand = os.path.join(d, ORGANISM_FILE)
        if os.path.isfile(cand):
            try:
                return d, load_yaml_file(cand)
            except Exception:
                return None, None
        parent = os.path.dirname(d)
        if parent == d:  # cheguei em / — parou
            return None, None
        d = parent


def _glob_to_re(glob):
    """Converte um glob (com ** e *) numa regex ancorada contra um path relativo POSIX.

    ** casa qualquer coisa incl. '/'; * casa qualquer coisa menos '/'.
    """
    out = []
    i = 0
    while i < len(glob):
        c = glob[i]
        if c == "*":
            if glob[i + 1:i + 2] == "*":
                out.append(".*")
                i += 2
                # consome uma '/' logo após ** pra 'a/**/b' casar 'a/b'
                if glob[i:i + 1] == "/":
                    i += 1
                    out.append("(?:.*/)?")
                continue
            out.append("[^/]*")
            i += 1
            continue
        out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def _matches(glob, relpath):
    return _glob_to_re(glob).match(relpath) is not None


def _excluded(relpath, excludes):
    return any(_matches(g, relpath) for g in (excludes or []))


def _relpath(root, abs_path):
    try:
        rel = os.path.relpath(os.path.abspath(abs_path), root)
    except Exception:
        return None
    return rel.replace(os.sep, "/")


def costuras_for_path(root, data, abs_path):
    """Retorna a lista de costuras que abs_path toca, cada uma com o blast-radius.

    Um hit = o path casa o glob de UMA ponta; o blast-radius = os `modulo` das
    OUTRAS pontas (o que você precisa endereçar/refutar).
    """
    rel = _relpath(root, abs_path)
    if rel is None or rel.startswith(".."):
        return []
    excludes = (data.get("defaults") or {}).get("exclude") or []
    if _excluded(rel, excludes):
        return []
    hits = []
    for costura in data.get("costuras") or []:
        pontas = costura.get("pontas") or []
        touched = None
        for ponta in pontas:
            if any(_matches(g, rel) for g in (ponta.get("globs") or [])):
                touched = ponta.get("modulo")
                break
        if touched is None:
            continue
        blast = [p.get("modulo") for p in pontas if p.get("modulo") != touched]
        hits.append({
            "id": costura.get("id"),
            "severidade": costura.get("severidade", "warn"),
            "aresta_msg": " ".join((costura.get("aresta_msg") or "").split()),
            "grep_verificavel": costura.get("grep_verificavel", True),
            "ponta_tocada": touched,
            "blast_radius": blast,
        })
    return hits


def verify_cite(root, data, costura_id, cite):
    """Valida uma refutação 'arquivo:linha' — o arquivo existe e a linha contém
    um símbolo daquela costura. Barreira contra citação-fantasma, não contra
    refutação sofisticada-errada (teto assumido do mecanismo)."""
    costura = next((c for c in (data.get("costuras") or []) if c.get("id") == costura_id), None)
    if not costura:
        return {"valid": False, "reason": "costura desconhecida: %s" % costura_id}
    m = re.match(r"^(.*?):(\d+)$", cite.strip())
    if not m:
        return {"valid": False, "reason": "formato esperado arquivo:linha, veio: %r" % cite}
    fpath, lineno = m.group(1), int(m.group(2))
    abspath = fpath if os.path.isabs(fpath) else os.path.join(root, fpath)
    if not os.path.isfile(abspath):
        return {"valid": False, "reason": "arquivo não existe: %s" % fpath}
    try:
        with open(abspath, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except Exception as e:
        return {"valid": False, "reason": "não consegui ler: %s" % e}
    if lineno < 1 or lineno > len(lines):
        return {"valid": False, "reason": "linha %d fora do arquivo (%d linhas)" % (lineno, len(lines))}
    line = lines[lineno - 1]
    all_syms = [s for p in (costura.get("pontas") or []) for s in (p.get("simbolos") or [])]
    hit = next((s for s in all_syms if s in line), None)
    if hit is None:
        return {"valid": False,
                "reason": "linha %d de %s não contém nenhum símbolo da costura %s" % (lineno, fpath, costura_id)}
    return {"valid": True, "reason": "ok: linha contém %r" % hit}


# ===========================================================================
# CENSUS — mundo-aberto: varre TODA doc project-doc do repo e classifica.
#
# Motivo: a skill era closed-world (só via a árvore da raiz). Num organismo
# (monorepo de módulos que antes eram repos separados), cada módulo herdou uma
# `<módulo>/.claude/docs/` própria que a raiz nunca tocava → drift órfão. O
# census abre o mundo: enumera tudo, classifica em 4 (design com o Fable), e a
# skill decide o que migrar/arquivar. Stateless — só localização+marker decidem
# (um manifesto de "o que o run gerou" envelhece e quebra cross-machine).
#
# As 4 classes:
#   canonical         — a árvore viva da raiz (docs de costura + modules/{m}/ de
#                       miolo) + o router fino gerado no módulo.
#   legacy-archived   — sob _archive/ ou .claude/legacy-pre-migracao/ ou com
#                       marker project-doc:legacy. Preservado, invisível aos hooks.
#   pending-migration — doc de um MÓDULO listado no organism.yaml SEM contraparte
#                       em modules/{m}/ na raiz. É o legado a MIGRAR (nunca
#                       arquivar cego — é a única doc que o módulo tem).
#   orphan            — doc project-doc fora do canônico e fora de módulo listado
#                       (ou leftover de um módulo já migrado). Candidato a arquivar.
# CLAUDE.md SEM marker project-doc = autoral → fora da jurisdição (info, nunca ação).
# ===========================================================================

# Dirs que NUNCA entram no census (worktrees/legado/build/deps duplicam a árvore
# ~10x). O filtro é load-bearing: um furo aqui faz o agente ler doc de 2025 com
# carimbo de fresco. Testado em test_organism.py.
CENSUS_PRUNE = {"node_modules", ".git", "_repos-antigos", ".next", "worktrees",
                ".venv", "dist", "build", "__pycache__", "backups", ".project-doc"}

_V2_MARKER_RE = re.compile(r"<!--\s*project-doc:v2[\s>]")
_ROUTER_MARKER_RE = re.compile(r"<!--\s*project-doc:module-router\b")
_LEGACY_MARKER_RE = re.compile(r"<!--\s*project-doc:legacy\b")
_DOCSIG_RE = re.compile(r"^doc-sig:\s*\S+", re.MULTILINE)


def _head(path, nbytes=2048):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read(nbytes)
    except OSError:
        return ""


def _is_projectdoc_claude_md(path):
    """CLAUDE.md gerado pelo project-doc? (tem marker v2 ou router). SEM marker
    = autoral (fora da jurisdição — Fable: nunca classificar/arquivar autoral).
    Lê o ARQUIVO INTEIRO — num organismo o CLAUDE.md do módulo tem um banner
    autoral grande no topo e o marker v2 vem depois (o _head de 2KB o perdia)."""
    h = _head(path, nbytes=200000)
    return bool(_V2_MARKER_RE.search(h) or _ROUTER_MARKER_RE.search(h))


def _is_projectdoc_doc(path):
    """.md sob .claude/docs/ é project-doc? Exige frontmatter com doc-sig (o que
    a skill gera). Um .md solto sem isso é autoral → info, não ação."""
    h = _head(path)
    return h.startswith("---\n") and bool(_DOCSIG_RE.search(h))


def _walk_repo_docs(root):
    """Gera (abspath, relposix) de todo CLAUDE.md e .claude/docs/*.md do repo,
    podando o ruído (CENSUS_PRUNE). Não desce em legacy-pre-migracao (só reporta
    o topo como archived, sem varrer o conteúdo)."""
    for dirpath, dirnames, filenames in os.walk(root):
        # poda in-place (os.walk respeita a mutação de dirnames)
        dirnames[:] = [d for d in dirnames if d not in CENSUS_PRUNE]
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        # não varre legacy-pre-migracao a fundo (é preservado-fora-do-vigente)
        if "legacy-pre-migracao" in dirnames:
            dirnames.remove("legacy-pre-migracao")
        is_docs_dir = ".claude/docs/" in (rel_dir + "/")
        for fn in filenames:
            if fn == "CLAUDE.md" or (fn.endswith(".md") and is_docs_dir):
                ap = os.path.join(dirpath, fn)
                rp = os.path.relpath(ap, root).replace(os.sep, "/")
                yield ap, rp


def _module_of(rel, modulos):
    """Se rel está sob um módulo listado, devolve o nome do módulo; senão None."""
    top = rel.split("/")[0]
    return top if top in (modulos or []) else None


def classify_doc(root, modulos, abspath, rel):
    """Classifica um doc. Devolve {path, kind, module, is_projectdoc, reason}."""
    guard = "/" + rel + "/"
    # archived: _archive/ ou legacy-pre-migracao/ ou marker legacy
    if "/_archive/" in guard or rel.startswith("_archive/") \
            or "/legacy-pre-migracao/" in guard or rel.startswith(".claude/legacy-pre-migracao/") \
            or _LEGACY_MARKER_RE.search(_head(abspath)):
        return {"path": rel, "kind": "legacy-archived", "module": None,
                "is_projectdoc": True, "reason": "arquivado/legado preservado"}

    is_claude = os.path.basename(rel) == "CLAUDE.md"
    is_pd = _is_projectdoc_claude_md(abspath) if is_claude else _is_projectdoc_doc(abspath)
    if not is_pd:
        return {"path": rel, "kind": "authoral", "module": None,
                "is_projectdoc": False, "reason": "sem marker project-doc — autoral"}

    module = _module_of(rel, modulos)

    # --- canônico: a árvore da raiz + router gerado no módulo ---
    if rel in ("CLAUDE.md", ".claude/CLAUDE.md"):
        return {"path": rel, "kind": "canonical", "module": None,
                "is_projectdoc": True, "reason": "índice da raiz"}
    if rel.startswith(".claude/docs/"):
        return {"path": rel, "kind": "canonical", "module": None,
                "is_projectdoc": True, "reason": "doc canônico da raiz (costura ou modules/)"}
    if is_claude and module and _ROUTER_MARKER_RE.search(_head(abspath)):
        return {"path": rel, "kind": "canonical", "module": module,
                "is_projectdoc": True, "reason": "router fino gerado do módulo"}

    # --- doc DENTRO de um módulo listado: pending vs orphan ---
    if module:
        counterpart = os.path.join(root, ".claude", "docs", "modules", module)
        migrated = os.path.isdir(counterpart)
        if migrated:
            return {"path": rel, "kind": "orphan", "module": module, "is_projectdoc": True,
                    "reason": "módulo já migrado (modules/%s existe) — leftover a arquivar" % module}
        return {"path": rel, "kind": "pending-migration", "module": module, "is_projectdoc": True,
                "reason": "doc legado do módulo %s — MIGRAR (nunca arquivar cego)" % module}

    # --- project-doc marcado, fora do canônico e fora de módulo listado ---
    return {"path": rel, "kind": "orphan", "module": None, "is_projectdoc": True,
            "reason": "doc project-doc fora do canônico e sem módulo no organism.yaml"}


def census(root):
    """Varre o repo e classifica toda doc project-doc. Fora de organismo o
    census ainda roda (modulos vazio → tudo canônico/órfão/autoral), mas a
    distinção pending-migration só existe com organism.yaml."""
    root = os.path.abspath(root)
    org_root, data = find_organism(root)
    modulos = (data or {}).get("modulos") or []
    name = (data or {}).get("name")
    docs = []
    for ap, rp in _walk_repo_docs(root):
        docs.append(classify_doc(root, modulos, ap, rp))
    summary = {}
    for d in docs:
        summary[d["kind"]] = summary.get(d["kind"], 0) + 1
    return {
        "root": root,
        "organism": bool(org_root) and org_root == root,
        "name": name,
        "modulos": modulos,
        "docs": docs,
        "summary": summary,
    }


# ===========================================================================
# LAZY / dirty-modules (Fase 3) — só regenera os módulos SUJOS, com PROPAGAÇÃO
# por dependência. Um organismo FULL regenerar as 7 árvores toda vez custa ~7×;
# mas dirty-detection só por scope LOCAL reintroduz drift nas COSTURAS (mudar o
# `name:` da rede docker no tools suja mcp+servico, cujos próprios arquivos não
# mudaram). Então: dirty = (módulo cujos arquivos mudaram) ∪ (blast-radius das
# costuras que os arquivos mudados tocam). É a régua do Fable.
# ===========================================================================
def dirty_modules_from_changes(root, data, changed_rel_paths):
    """Core PURO (testável sem git): dado a lista de paths mudados (root-relativos
    POSIX), devolve o set de módulos sujos, propagando pelas costuras."""
    modulos = (data or {}).get("modulos") or []
    dirty = set()
    for rel in changed_rel_paths:
        top = rel.split("/")[0]
        if top in modulos:
            dirty.add(top)
        # propagação: se o arquivo mudado é ponta de uma costura, as OUTRAS pontas sujam
        for hit in costuras_for_path(root, data, os.path.join(root, rel)):
            dirty.add(hit["ponta_tocada"])
            for m in hit["blast_radius"]:
                dirty.add(m)
    # só MÓDULOS REAIS regeneram: uma ponta de costura pode nomear um conceito
    # curado (ex.: "tools-consumidores") que não é um dir de módulo — descarta.
    return sorted(d for d in dirty if d in modulos)


def _git_changed_since(root, date):
    import subprocess
    try:
        out = subprocess.run(
            ["git", "-C", root, "log", "--since=%s 00:00:00" % date,
             "--name-only", "--pretty=format:"],
            capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return None
    return sorted({ln.strip() for ln in out.splitlines() if ln.strip()})


def dirty_modules(root, since_date):
    """Wrapper: computa os arquivos mudados desde `since_date` via git e devolve
    os módulos sujos (com propagação). None se git falhar (→ caller trata como
    'todos sujos', fail-safe: nunca pula um módulo por incerteza)."""
    root = os.path.abspath(root)
    _, data = find_organism(root)
    changed = _git_changed_since(root, since_date)
    if changed is None:
        return None
    return {"since": since_date, "changed_count": len(changed),
            "dirty": dirty_modules_from_changes(root, data or {}, changed)}


def main(argv):
    if len(argv) < 2:
        print(json.dumps({"error": "uso: organism.py <match|marker|brief|census|dirty|verify-cite> ..."}))
        return 2
    cmd = argv[1]

    if cmd == "census":
        start = argv[2] if len(argv) > 2 else os.getcwd()
        print(json.dumps(census(start), ensure_ascii=False))
        return 0

    if cmd == "dirty":
        if len(argv) < 4:
            print(json.dumps({"error": "uso: dirty <root> <YYYY-MM-DD>"}))
            return 2
        print(json.dumps(dirty_modules(argv[2], argv[3]), ensure_ascii=False))
        return 0

    if cmd == "marker":
        start = argv[2] if len(argv) > 2 else os.getcwd()
        root, data = find_organism(start)
        if not root:
            print(json.dumps({"organism": False}))
            return 0
        print(json.dumps({
            "organism": True, "root": root,
            "name": data.get("name"),
            "modulos": data.get("modulos") or [],
        }))
        return 0

    if cmd == "brief":
        # Resumo pro SessionStart: nome, módulos, regra de ouro, costuras (id+sev+resumo).
        start = argv[2] if len(argv) > 2 else os.getcwd()
        root, data = find_organism(start)
        if not root:
            print(json.dumps({"organism": False}))
            return 0
        costuras = [{
            "id": c.get("id"),
            "severidade": c.get("severidade", "warn"),
            "modulos": [p.get("modulo") for p in (c.get("pontas") or [])],
        } for c in (data.get("costuras") or [])]
        print(json.dumps({
            "organism": True, "root": root,
            "name": data.get("name"),
            "modulos": data.get("modulos") or [],
            "golden_rule": " ".join((data.get("golden_rule") or "").split()),
            "costuras": costuras,
        }))
        return 0

    if cmd == "match":
        if len(argv) < 3:
            print(json.dumps({"error": "match precisa de <abs_path>"}))
            return 2
        abs_path = argv[2]
        root, data = find_organism(abs_path)
        if not root:
            print(json.dumps({"organism": False, "hits": []}))
            return 0
        hits = costuras_for_path(root, data, abs_path)
        print(json.dumps({"organism": True, "root": root, "hits": hits}))
        return 0

    if cmd == "verify-cite":
        if len(argv) < 5:
            print(json.dumps({"valid": False, "reason": "uso: verify-cite <root> <costura_id> <arquivo:linha>"}))
            return 2
        root = argv[2]
        cand = os.path.join(root, ORGANISM_FILE)
        try:
            data = load_yaml_file(cand)
        except Exception as e:
            print(json.dumps({"valid": False, "reason": "sem organism.yaml em %s: %s" % (root, e)}))
            return 0
        print(json.dumps(verify_cite(root, data, argv[3], argv[4])))
        return 0

    print(json.dumps({"error": "cmd desconhecido: %s" % cmd}))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
