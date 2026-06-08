#!/usr/bin/env python3
"""
Auditoria do relatório do Fallow.

O Fallow é estático: ele AFIRMA "órfão/morto", mas não enxerga cron externo
(systemd/crontab), import dinâmico, uso via package.json script ou rota HTTP.
Este motor CONFIRMA cada afirmação com evidência real e classifica:

  • dead_confirmado  — 0 referências em qualquer lugar; seguro eliminar.
  • falso_positivo   — há uso que o Fallow não viu (com a razão e a prova).
  • manual_cli       — script sem refs, mas é ferramenta CLI manual: arquivar, não deletar.

Propagação de vivacidade: um falso-positivo "raiz" (ex: script de cron rodado por
systemd) é tratado como entry point vivo; tudo que ele importa e que o Fallow havia
marcado como morto também é vivo (foi assim que `gera-recorrencias.ts` foi pego —
o `cron-recorrencias.ts` o importa e roda em produção).

Goal de convergência: roda a auditoria repetidamente; cada rodada que descobre um
buraco novo (FP que rodadas anteriores não pegaram) reinicia a contagem. Converge
quando 3 rodadas consecutivas dão exatamente o mesmo resultado.

Uso:  python3 audit.py <project_root> [--json]
Sem --json: imprime relatório humano. Com --json: dump estruturado (pro report.py).
"""
import json
import os
import re
import subprocess
import sys
import hashlib

ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else "."
# .svelte/.vue/.astro incluídos: o Fallow (parser JS/TS puro) não enxerga import
# dentro de componente, então a auditoria PRECISA grepar neles pra pegar o uso real.
GREP_EXT = ["--include=*.ts", "--include=*.tsx", "--include=*.js", "--include=*.mjs",
            "--include=*.mts", "--include=*.cts", "--include=*.jsx",
            "--include=*.svelte", "--include=*.vue", "--include=*.astro"]
# diretórios onde procurar uso de um símbolo exportado (filtrados por existência)
SYMBOL_SEARCH = ["src", "app", "lib", "routes", "pages", "components",
                 "tests", "test", "e2e", "scripts"]
# infra de EXECUÇÃO (agendador/runtime), não prosa: aqui um script citado é de fato rodado.
# docs/*.md ficam de fora — citar um script num plano é planejamento, não uso ativo.
EXTERNAL_PATHS = ["deploy", "infra", ".github"]
EXTERNAL_GLOBS = ["docker-compose.yml", "docker-compose.prod.yml", "docker-compose.dev.yml",
                  "Procfile", "crontab", "Makefile"]


def run(cmd):
    try:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=180).stdout
    except Exception:
        return ""


def read(rel):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def exists(rel):
    return os.path.exists(os.path.join(ROOT, rel))


def fallow_unused_files():
    out = run(["npx", "-y", "fallow", "dead-code", "-r", ".", "--unused-files", "--format", "json"])
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return []
    return [f.get("path", "") for f in d.get("unused_files", []) if f.get("path")]


def basename_noext(p):
    return re.sub(r"\.(ts|tsx|js|mjs)$", "", os.path.basename(p))


def grep_n(pattern, *paths):
    """grep -nIE em paths existentes; devolve linhas 'file:line:texto'."""
    real = [p for p in paths if exists(p)]
    if not real:
        return []
    cmd = ["grep", "-rnIE"] + GREP_EXT + [pattern] + real
    return [l for l in run(cmd).splitlines() if l]


def grep_plain(pattern, *files):
    """grep -nE em arquivos específicos (não recursivo por extensão), ex package.json/README."""
    real = [f for f in files if exists(f)]
    if not real:
        return []
    return [l for l in run(["grep", "-rnE", pattern] + real).splitlines() if l]


ROUTE_RE = re.compile(r"/(api|app)/.*\broute(\.\w+)?\.(ts|tsx|js)$")
PAGE_RE = re.compile(r"/(page|layout|loading|error|not-found|middleware|instrumentation)(\.\w+)?\.(ts|tsx|js)$")


# ---- evidência direta de uso por arquivo ----
def direct_evidence(path):
    """Retorna lista de (tipo, prova) se houver QUALQUER uso. Vazia = sem evidência direta.
    Matches ancorados pra evitar falso-positivo (substring de path, basename solto, símbolo genérico)."""
    base = re.escape(basename_noext(path))
    found = []

    # 1. import/require/dynamic do módulo pelo caminho (basename como último segmento do specifier)
    refs = [l for l in grep_n(rf"(import|from|require|dynamic|lazy).*[/'\"]{base}['\"]",
                              "src", "tests", "e2e", "prisma", "scripts")
            if not l.startswith(path + ":")]
    if refs:
        found.append(("import-do-modulo", refs[0]))

    # 2. rota HTTP ou arquivo de convenção de framework (acionado por request/runtime, não por import)
    if ROUTE_RE.search(path):
        found.append(("rota-http", "route handler em /api ou /app — acionado por request, não importado"))
    elif PAGE_RE.search(path):
        found.append(("convenção-framework", "page/layout/middleware — entry do framework"))

    # 3. package.json aponta pro caminho EXATO (precedido por aspas/espaço → não casa sufixo de path aninhado)
    pj = grep_plain(rf"[\"' ]{re.escape(path)}", "package.json")
    if pj:
        found.append(("package.json-script", pj[0]))

    # 4. infra de execução (cron/systemd/docker/CI) roda o arquivo. Boundary à esquerda + nome+extensão:
    #    "switch.tsx" não casa "switcher"; "data-table.tsx" não casa "advanced-data-table.tsx".
    fname = re.escape(os.path.basename(path))
    ext = grep_plain(rf"(^|[^A-Za-z0-9_-]){fname}", *EXTERNAL_PATHS, *EXTERNAL_GLOBS)
    if ext:
        found.append(("infra-execução", ext[0]))

    return found


# ---- resolução de imports pra propagação ----
def imports_of(path):
    txt = read(path)
    specs = re.findall(r"(?:from|import)\s+['\"]([^'\"]+)['\"]", txt)
    specs += re.findall(r"import\(\s*['\"]([^'\"]+)['\"]\s*\)", txt)
    out = []
    d = os.path.dirname(path)
    for s in specs:
        if s.startswith("@/"):
            cand = os.path.join("src", s[2:])
        elif s.startswith("."):
            cand = os.path.normpath(os.path.join(d, s))
        else:
            continue  # pacote externo do node_modules
        out.append(cand)
    return out


def resolve(cand):
    for ext in (".ts", ".tsx", ".js", ".mjs", "/index.ts", "/index.tsx", "/index.js"):
        if exists(cand + ext):
            return cand + ext
    return cand if exists(cand) else None


def is_script(path):
    return "scripts" in path.lower().split("/")[:-1]


# ---- uma rodada de auditoria (com propagação interna até estável) ----
def audit_round(dead):
    dead_set = set(dead)
    verdict = {}   # path -> {"verdict","reason","proof"}
    live_roots = []

    for p in dead:
        ev = direct_evidence(p)
        if ev:
            kinds = ", ".join(k for k, _ in ev)
            verdict[p] = {"verdict": "falso_positivo", "reason": f"uso real via {kinds}",
                          "proof": ev[0][1], "origin": "evidência direta"}
            live_roots.append(p)
        elif is_script(p):
            verdict[p] = {"verdict": "manual_cli",
                          "reason": "sem refs e não agendado, mas é script CLI — arquivar, não deletar",
                          "proof": "", "origin": "heurística"}
        else:
            verdict[p] = {"verdict": "dead_confirmado", "reason": "0 referências em todo o projeto",
                          "proof": "", "origin": "evidência direta"}

    # propagação: FP-raiz vira entry vivo; mortos que ele alcança também vivem
    holes = 0
    live = set(live_roots)
    frontier = list(live_roots)
    while frontier:
        cur = frontier.pop()
        for imp in imports_of(cur):
            r = resolve(imp)
            if r and r in dead_set and r not in live:
                live.add(r)
                frontier.append(r)
                holes += 1
                verdict[r] = {"verdict": "falso_positivo",
                              "reason": f"vivo por propagação — importado por {os.path.basename(cur)} "
                                        f"(que roda em produção)",
                              "proof": f"{cur} importa {r}", "origin": "propagação"}
    return verdict, holes


def fingerprint(verdict):
    items = sorted((p, v["verdict"]) for p, v in verdict.items())
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()[:16]


def converge(dead, max_rounds=12):
    """Goal: repetir até 3 rodadas consecutivas idênticas. Cada rodada que muda
    o resultado (acha buraco novo) reinicia a contagem de estabilidade."""
    rounds = []
    last_fp = None
    stable = 0
    final = None
    while stable < 3 and len(rounds) < max_rounds:
        verdict, holes = audit_round(dead)
        fp = fingerprint(verdict)
        if fp == last_fp:
            stable += 1
        else:
            stable = 1  # resultado novo: reinicia rumo às 3 iguais
        last_fp = fp
        final = verdict
        rounds.append({"round": len(rounds) + 1, "fingerprint": fp, "holes_propagated": holes})
    return final, rounds, stable >= 3


# ---- auditoria de EXPORTS e TIPOS (o Fallow erra muito aqui em projeto Svelte/Vue) ----
def fallow_unused_exports():
    out = run(["npx", "-y", "fallow", "dead-code", "-r", ".", "--format", "json"])
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return []
    items = []
    for e in d.get("unused_exports", []):
        if e.get("path") and e.get("export_name"):
            items.append({"path": e["path"], "name": e["export_name"], "line": e.get("line"),
                          "kind": "type" if e.get("is_type_only") else "export"})
    for t in d.get("unused_types", []):
        if t.get("path") and t.get("export_name"):
            items.append({"path": t["path"], "name": t["export_name"], "line": t.get("line"),
                          "kind": "type"})
    return items


def _is_comment_ref(line, name):
    """True se a ocorrência do símbolo está num comentário/prosa (// /* * <!-- #),
    não em código. Evita FP de auditoria com nome genérico (ex.: 'send' em '// throttled send')."""
    parts = line.split(":", 2)
    text = parts[2] if len(parts) >= 3 else line
    if text.lstrip().startswith(("//", "*", "/*", "<!--", "{/*", "#")):
        return True
    cpos = text.find("//")
    npos = text.find(name)
    return cpos != -1 and npos != -1 and cpos < npos


def symbol_evidence(decl_path, name, decl_line=None):
    """('externo', prova) se o símbolo é usado em OUTRO arquivo (FP do Fallow, ex.: import em .svelte);
    ('interno', prova) se só é usado dentro do próprio arquivo (export redundante, símbolo vivo);
    None se não há uso em lugar nenhum (morto de verdade).
    Comentários/prosa são descartados — só uso em código conta."""
    pat = rf"\b{re.escape(name)}\b"
    ext = [l for l in grep_n(pat, *SYMBOL_SEARCH)
           if not l.startswith(decl_path + ":") and not _is_comment_ref(l, name)]
    if ext:
        return ("externo", ext[0])
    inner = []
    for l in grep_n(pat, decl_path):
        parts = l.split(":", 2)
        if decl_line is not None and len(parts) >= 2 and parts[1] == str(decl_line):
            continue  # a própria linha da declaração não conta como uso
        if _is_comment_ref(l, name):
            continue
        inner.append(l)
    if inner:
        return ("interno", inner[0])
    return None


def audit_exports(items):
    out = []
    for it in items:
        ev = symbol_evidence(it["path"], it["name"], it.get("line"))
        if ev and ev[0] == "externo":
            out.append({**it, "verdict": "falso_positivo",
                        "reason": "usado em outro arquivo que o Fallow não enxergou (ex.: import dentro de .svelte/.vue)",
                        "proof": ev[1]})
        elif ev and ev[0] == "interno":
            out.append({**it, "verdict": "usado_interno",
                        "reason": "usado dentro do próprio arquivo; o `export` é redundante, mas o símbolo NÃO é morto",
                        "proof": ev[1]})
        else:
            out.append({**it, "verdict": "dead_confirmado",
                        "reason": "0 referências — nem em outro arquivo, nem dentro do próprio", "proof": ""})
    return out


def main():
    as_json = "--json" in sys.argv
    dead = fallow_unused_files()
    verdict, rounds, converged = converge(dead)
    exports = audit_exports(fallow_unused_exports())

    groups = {"dead_confirmado": [], "falso_positivo": [], "manual_cli": []}
    for p, v in sorted(verdict.items()):
        groups[v["verdict"]].append({"path": p, **v})

    # contagem AGREGADA (arquivos + exports/tipos) pro card do relatório refletir tudo
    agg = {"dead_confirmado": 0, "falso_positivo": 0, "manual_cli": 0, "usado_interno": 0}
    for k, lst in groups.items():
        agg[k] = len(lst)
    for ev in exports:
        agg[ev["verdict"]] = agg.get(ev["verdict"], 0) + 1

    result = {
        "project": os.path.basename(ROOT),
        "total_audited": len(dead) + len(exports),
        "converged": converged,
        "rounds": rounds,
        "identical_fingerprints": len({r["fingerprint"] for r in rounds}) == 1 if rounds else False,
        "counts": agg,
        "groups": groups,
        "export_verdicts": exports,
    }

    if as_json:
        print(json.dumps(result, ensure_ascii=False))
        return

    icon = {"dead_confirmado": "✅", "falso_positivo": "🛑", "manual_cli": "📦"}
    label = {"dead_confirmado": "ÓRFÃOS REAIS (seguro eliminar)",
             "falso_positivo": "FALSOS-POSITIVOS (NÃO deletar — o Fallow errou)",
             "manual_cli": "SCRIPTS CLI MANUAIS (arquivar, não deletar)"}
    print(f"# Auditoria do relatório Fallow — {result['project']}")
    print(f"Goal de convergência: {len(rounds)} rodadas · "
          f"{'CONVERGIU ✓ (3 idênticas)' if converged else 'NÃO convergiu ✗'} · "
          f"fingerprints {[r['fingerprint'] for r in rounds]}")
    print(f"Auditados: {len(dead)} arquivos órfãos + {len(exports)} exports/tipos\n")
    for k in ("falso_positivo", "dead_confirmado", "manual_cli"):
        g = groups[k]
        print(f"{icon[k]} {label[k]} — {len(g)}")
        for it in g:
            print(f"   {it['path']}")
            print(f"      → {it['reason']}")
            if it["proof"]:
                print(f"      prova: {it['proof'][:120]}")
        print()

    if exports:
        eicon = {"dead_confirmado": "✅", "falso_positivo": "🛑", "usado_interno": "↩"}
        elabel = {"falso_positivo": "EXPORTS FALSO-POSITIVO (em uso via .svelte/.vue — NÃO remover)",
                  "usado_interno": "EXPORTS SÓ INTERNOS (export redundante, símbolo vivo)",
                  "dead_confirmado": "EXPORTS/TIPOS MORTOS (seguro remover o símbolo)"}
        print("## Exports & tipos")
        for k in ("falso_positivo", "usado_interno", "dead_confirmado"):
            g = [e for e in exports if e["verdict"] == k]
            if not g:
                continue
            print(f"{eicon[k]} {elabel[k]} — {len(g)}")
            for e in g:
                print(f"   {e['path']}::{e['name']}")
                print(f"      → {e['reason']}")
                if e["proof"]:
                    print(f"      prova: {e['proof'][:120]}")
            print()


if __name__ == "__main__":
    main()
