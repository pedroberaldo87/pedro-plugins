#!/usr/bin/env python3
"""
Motor do relatório /fallow.
Roda o Fallow (dead-code + dupes + health) num projeto, classifica os achados
por tipo e nível de confiança, e gera um relatório HTML interativo (checkboxes)
em ~/Desktop/claude-visual/. Pedro marca o que limpar; a seleção volta pro Claude
via clipboard (marcador <!-- fallow-selection v1 -->) ou live-sync do daemon visual.

Uso:  python3 report.py <project_root> [session_token]
Imprime no stdout o path do HTML gerado + um resumo JSON dos baldes.

Não escreve nada no projeto-alvo (só lê via fallow) e nada destrutivo.
"""
import json
import os
import subprocess
import sys
import html as _html
from datetime import datetime, timezone


def run_fallow(cmd, root):
    """Roda um subcomando fallow --format json e devolve o dict, ou {} se falhar."""
    try:
        p = subprocess.run(
            ["npx", "-y", "fallow", cmd, "-r", root, "--format", "json"],
            capture_output=True, text=True, timeout=300,
        )
        # fallow sai 1 quando acha findings; a saída JSON ainda é válida.
        return json.loads(p.stdout) if p.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[fallow {cmd}] falhou: {e}", file=sys.stderr)
        return {}


def run_audit_engine(root):
    """Roda audit.py (auditoria + goal de convergência) e devolve o dict de vereditos."""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        p = subprocess.run(["python3", os.path.join(here, "audit.py"), root, "--json"],
                           capture_output=True, text=True, timeout=600)
        return json.loads(p.stdout) if p.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"[audit] falhou: {e}", file=sys.stderr)
        return {}


def audit_map(audit):
    """path -> {verdict, reason, proof} a partir do JSON do audit."""
    m = {}
    for items in (audit.get("groups") or {}).values():
        for it in items:
            m[it["path"]] = it
    return m


def export_audit_map(audit):
    """(path, name) -> verdict de export/tipo a partir do JSON do audit."""
    m = {}
    for ev in (audit.get("export_verdicts") or []):
        m[(ev["path"], ev["name"])] = ev
    return m


def export_item(p, name, line, kind, rexp, ev):
    """Monta o item de export/tipo no bucket de código morto, usando o VEREDITO da auditoria
    (falso_positivo / usado_interno / dead_confirmado) — não a heurística cega do Fallow."""
    label = "tipo" if kind == "type" else "export"
    v = (ev or {}).get("verdict")
    reason = esc((ev or {}).get("reason", ""))
    proof = esc(str((ev or {}).get("proof", ""))[:200])
    pf = f" Prova: <code>{proof}</code>" if proof else ""
    if v == "falso_positivo":
        return {"path": p, "badge": name, "conf": "fp",
                "prob_h": f"O {label} <b>{esc(name)}</b> aparece como não-usado, mas <b>está em uso</b> — não é morto.",
                "prob_t": f"Limitação do Fallow: ele não enxerga import dentro de <code>.svelte</code>/<code>.vue</code>. "
                          f"A auditoria achou uso real: {reason}.{pf}",
                "sol_h": "<b>Não remover.</b> O código está certo.",
                "sol_t": "Mantido na lista de propósito (transparência). Pra sumir daqui, suprimir com "
                         "<code>// fallow-ignore-next-line unused-export</code> — cosmético."}
    if v == "usado_interno":
        return {"path": p, "badge": name, "conf": "interno",
                "prob_h": f"O {label} <b>{esc(name)}</b> é usado só dentro do próprio arquivo — o <code>export</code> é redundante.",
                "prob_t": f"A auditoria achou uso interno: {reason}.{pf} Apagar a função/tipo inteiro quebraria o "
                          "arquivo; só a palavra <code>export</code> sobra à toa.",
                "sol_h": "Tirar só o <code>export</code> (o símbolo continua). Opcional, baixo valor.",
                "sol_t": "Se for parte intencional da API pública (ex.: ponte de comandos do app), deixar como está."}
    if v == "dead_confirmado":
        return {"path": p, "badge": name, "conf": "confirmado",
                "prob_h": f"O {label} <b>{esc(name)}</b> é morto — <b>confirmado pela auditoria</b> (0 uso interno e externo).",
                "prob_t": f"Declarado em <code>{esc(p)}:{line}</code>{rexp}. O grep não achou nenhum consumidor em "
                          "arquivo nenhum, incluindo <code>.svelte</code>.",
                "sol_h": "Apagar o símbolo inteiro (não só o <code>export</code>).",
                "sol_t": "Auditado: 0 referências. Ainda assim confirmo com build/test antes de remover."}
    # auditoria indisponível → fallback honesto (NÃO afirmar que é morto)
    return {"path": p, "badge": name, "conf": "verificar",
            "prob_h": f"O {label} <b>{esc(name)}</b> aparece como não-usado pelo Fallow.",
            "prob_t": f"Declarado em <code>{esc(p)}:{line}</code>{rexp}. <b>Auditoria de exports indisponível</b> — "
                      "o Fallow não enxerga import dentro de .svelte, então pode ser falso-positivo.",
            "sol_h": "Verificar com grep antes de tocar.",
            "sol_t": "Confirmar 0 uso real (incl. <code>.svelte</code>) antes de remover o <code>export</code>."}


# diretórios e nomes FP-prone: pedem verificação manual antes de deletar
# (rotas/scripts/cron/assets que análise estática não enxerga como entry)
VERIFY_DIRS = {"scripts", "cron", "public", "static", "api", "migrations", "e2e", "tests"}
VERIFY_NAME_HINTS = ("route.", "page.", "layout.", "middleware", "main.",
                     "instrumentation", ".dev.")


def confidence(path):
    p = path.lower()
    segs = p.split("/")
    name = segs[-1]
    # qualquer segmento de diretório FP-prone (pega "scripts/" na raiz E aninhado)
    if VERIFY_DIRS.intersection(segs[:-1]):
        return "verificar"
    if name.endswith(".css") or any(h in name for h in VERIFY_NAME_HINTS):
        return "verificar"
    return "confirmado"


def item_path(x):
    if isinstance(x, dict):
        return x.get("path") or x.get("file") or ""
    return str(x)


def short(p):
    """Caminho compacto pro summary: 2 últimos segmentos."""
    parts = p.split("/")
    return "/".join(parts[-2:]) if len(parts) > 2 else p


def build_buckets(dead, dupes, health, audit=None):
    buckets = []
    averd = audit_map(audit or {})
    eaverd = export_audit_map(audit or {})

    # 🧟 código morto: arquivos órfãos (com VEREDITO da auditoria) + exports + types
    dead_items = []
    for f in dead.get("unused_files", []):
        p = item_path(f)
        av = averd.get(p, {})
        v = av.get("verdict", "")
        reason = av.get("reason", "")
        proof = esc(str(av.get("proof", ""))[:200])
        if v == "falso_positivo":
            dead_items.append({
                "path": p, "badge": "🛑 não deletar", "conf": "fp",
                "prob_h": "<b>Não é código morto nem bug do teu código.</b> É uma limitação do Fallow: "
                          "este arquivo está em uso, mas acionado de fora do código.",
                "prob_t": "Limitação da análise estática — o Fallow lê só o grafo de imports (quem chama quem "
                          "no código) e <b>não enxerga</b> gatilhos externos: agendador do servidor (cron/systemd), "
                          "requisição HTTP (rota) ou import dinâmico. "
                          f"A auditoria confirmou o uso: {esc(reason)}." + (f" Prova: <code>{proof}</code>" if proof else ""),
                "sol_h": "<b>Nada a fazer no código</b> — está correto. Só não deletar.",
                "sol_t": "Mantido na lista de propósito, pra dar transparência. Se quiser que suma daqui, dá pra "
                         "declarar o arquivo como ponto de entrada no <code>.fallowrc.json</code> — mas é cosmético, "
                         "não muda nada no app."})
        elif v == "dead_confirmado":
            dead_items.append({
                "path": p, "badge": None, "conf": "confirmado",
                "prob_h": "Órfão <b>confirmado pela auditoria</b> — 0 referências em todo o projeto.",
                "prob_t": "Sem import estático, sem import dinâmico, sem uso por símbolo, sem cron/rota. "
                          "Auditado e estável (convergiu).",
                "sol_h": "Deletar o arquivo.",
                "sol_t": "Ação <code>delete-file</code>. Auditoria confirma 0 uso; ainda assim rodo "
                         "<code>--trace</code> + build/test antes de apagar."})
        elif v == "manual_cli":
            dead_items.append({
                "path": p, "badge": "arquivar", "conf": "verificar",
                "prob_h": "Script sem refs e não agendado — provável ferramenta CLI manual.",
                "prob_t": f"Auditoria: {esc(reason)}. Não é importado nem está em cron/infra, mas pode ser "
                          "rodado à mão pontualmente.",
                "sol_h": "Arquivar (mover pra fora), não deletar.",
                "sol_t": "Vários têm cara de tarefa única já executada. O seguro é arquivar — você confirma "
                         "quais já cumpriram a função."})
        else:  # sem veredito da auditoria → fallback heurístico
            is_script = "scripts" in p.lower().split("/")[:-1]
            dead_items.append({
                "path": p, "badge": None, "conf": confidence(p),
                "prob_h": "Ninguém importa este arquivo — está órfão no projeto.",
                "prob_t": "Não alcançado por nenhum entry point no grafo do Fallow (auditoria indisponível).",
                "sol_h": ("Arquivar ou deletar." if is_script else "Deletar o arquivo."),
                "sol_t": "Ação <code>delete-file</code> — confirmo com <code>--trace</code> + build/test antes."})
    for e in dead.get("unused_exports", []):
        p = item_path(e)
        name = e.get("export_name", "?")
        line = e.get("line", "?")
        kind = "type" if e.get("is_type_only") else "export"
        rexp = " · é um re-export" if e.get("is_re_export") else ""
        dead_items.append(export_item(p, name, line, kind, rexp, eaverd.get((p, name))))
    for t in dead.get("unused_types", []):
        p = item_path(t)
        name = t.get("export_name", "?")
        dead_items.append(export_item(p, name, t.get("line", "?"), "type", "", eaverd.get((p, name))))
    buckets.append({"key": "morto", "emoji": "🧟", "title": "Código morto", "items": dead_items})

    # 📦 dependências
    dep_items = []
    for d in dead.get("unused_dependencies", []):
        name = d.get("name") if isinstance(d, dict) else d
        dep_items.append({
            "path": str(name), "badge": "dep", "conf": "confirmado",
            "prob_h": f"A dependência <b>{esc(name)}</b> está instalada mas nunca é importada.",
            "prob_t": "Declarada no <code>package.json</code>, zero imports no código — peso morto no "
                      "<code>node_modules</code> e no lockfile.",
            "sol_h": "Remover do package.json.",
            "sol_t": "<b>Auto-fixável</b> via <code>fallow fix</code>. Antes: confirmar que não é peer dep / "
                     "plugin de build / usada só em config — esses são falso-positivo clássico."})
    buckets.append({"key": "deps", "emoji": "📦", "title": "Dependências não usadas", "items": dep_items})

    # 🔁 ciclos
    cyc_items = []
    for c in dead.get("circular_dependencies", []) + dead.get("re_export_cycles", []):
        files = c.get("files") or c.get("cycle_path") or c if isinstance(c, dict) else c
        flist = files if isinstance(files, list) else [str(files)]
        cyc_items.append({
            "path": " → ".join(short(x) for x in flist), "badge": f"{len(flist)} arq", "conf": "verificar",
            "prob_h": "Arquivos que se importam em círculo.",
            "prob_t": "Ciclo: " + " → ".join(f"<code>{esc(x)}</code>" for x in flist) +
                      ". Risco de ordem de inicialização (export <code>undefined</code> no meio do ciclo) e "
                      "impede tree-shaking.",
            "sol_h": "Quebrar a dependência mútua.",
            "sol_t": "Não é deletável — é refactor. Extrair o que os dois arquivos compartilham pra um terceiro "
                     "módulo, ou inverter uma das direções de import."})
    buckets.append({"key": "ciclos", "emoji": "🔁", "title": "Dependências circulares", "items": cyc_items})

    # 👯 duplicação (famílias maiores)
    def sugg_text(s):
        if isinstance(s, dict):
            return s.get("description") or s.get("message") or s.get("text") or s.get("suggested_name") or ""
        return str(s)
    dup_items = []
    fams = sorted(dupes.get("clone_families", []),
                  key=lambda f: f.get("total_duplicated_lines", 0), reverse=True)
    for fam in fams[:30]:
        files = fam.get("files", [])
        lines = fam.get("total_duplicated_lines", 0)
        sugg = [t for t in (sugg_text(s) for s in (fam.get("suggestions") or [])) if t]
        is_test = all(".spec." in f or ".test." in f for f in files)
        dup_items.append({
            "path": ", ".join(os.path.basename(x) for x in files[:2]) + (f" +{len(files)-2}" if len(files) > 2 else ""),
            "badge": f"{lines} ln", "conf": "verificar",
            "prob_h": f"Mesmo bloco repetido em {len(files)} arquivos ({lines} linhas).",
            "prob_t": "Arquivos: " + ", ".join(f"<code>{esc(x)}</code>" for x in files) +
                      (". São testes — duplicação aqui costuma ser aceitável." if is_test else
                       ". Corrigir um bug exige lembrar de corrigir em todas as cópias."),
            "sol_h": "Extrair o trecho pra uma função/helper compartilhado.",
            "sol_t": ("Sugestão do Fallow: " + esc("; ".join(sugg)) + ". " if sugg else "") +
                     "Refactor manual (não auto-fix)."})
    buckets.append({"key": "dup", "emoji": "👯", "title": "Duplicação", "items": dup_items})

    # 🧠 complexidade (targets por prioridade, quick wins primeiro)
    cx_items = []
    targets = sorted(health.get("targets", []), key=lambda t: t.get("priority", 0), reverse=True)
    for t in targets[:40]:
        p = item_path(t)
        eff = t.get("effort", "?")
        rec = t.get("recommendation", t.get("category", ""))
        factors = t.get("factors", [])
        fac_txt = "; ".join(f.get("detail", "") for f in factors if f.get("detail"))
        ev = t.get("evidence", {}).get("complex_functions", [])
        ev_txt = ", ".join(f"<code>{esc(fn.get('name'))}</code> (linha {fn.get('line')}, cognitiva {fn.get('cognitive')})"
                           for fn in ev) if ev else ""
        cx_items.append({
            "path": short(p), "badge": eff, "conf": "verificar",
            "prob_h": "Função(ões) complexas demais — difícil de entender, testar e mexer sem introduzir bug.",
            "prob_t": (f"Arquivo <code>{esc(p)}</code>. " + (f"Sinais: {esc(fac_txt)}. " if fac_txt else "")
                       + (f"Funções críticas: {ev_txt}." if ev_txt else "")),
            "sol_h": esc(rec),
            "sol_t": f"Esforço <b>{eff}</b> · confiança {t.get('confidence','?')} · prioridade {t.get('priority','?')}. "
                     "Refactor manual (não auto-fix) — quebrar a função grande em partes menores e testáveis."})
    buckets.append({"key": "cx", "emoji": "🧠", "title": "Complexidade / refactor", "items": cx_items})

    return buckets


def esc(s):
    return _html.escape(str(s))


def render_html(project_name, buckets, health, session, stamp, audit=None):
    hscore = health.get("health_score", {})
    grade = hscore.get("grade", "?") if isinstance(hscore, dict) else "?"
    score = hscore.get("score", "?") if isinstance(hscore, dict) else hscore
    counts = {b["key"]: len(b["items"]) for b in buckets}
    chips = " · ".join(f"{b['emoji']} {len(b['items'])}" for b in buckets if b["items"])

    # card da auditoria (goal de convergência)
    audit = audit or {}
    a_counts = audit.get("counts", {})
    a_rounds = audit.get("rounds", [])
    n_fp = a_counts.get("falso_positivo", 0)
    n_real = a_counts.get("dead_confirmado", 0)
    n_man = a_counts.get("manual_cli", 0)
    n_int = a_counts.get("usado_interno", 0)
    conv = audit.get("converged")
    ident = audit.get("identical_fingerprints")
    audit_card = ""
    if audit.get("total_audited") is not None:
        status = (f"✓ convergiu em {len(a_rounds)} rodadas idênticas"
                  if (conv and ident) else f"⚠ {len(a_rounds)} rodadas, não estabilizou")
        audit_card = (
            f'<div class="auditcard"><div class="ahead"><span class="apill">🔍 Auditoria do relatório · goal</span>'
            f'<span class="aconv {"ok" if (conv and ident) else "warn"}">{status}</span></div>'
            f'<p class="asub">Cada achado do Fallow (arquivo órfão, export e tipo) foi re-verificado com evidência '
            f'real — import estático+dinâmico, uso de símbolo em <b>.svelte/.vue</b>, package.json, cron/systemd, rota '
            f'HTTP. O goal repete a auditoria até dar igual 3× seguidas.</p>'
            f'<div class="astats">'
            f'<span class="astat fp"><b>{n_fp}</b> falso-positivo do Fallow<br><small>NÃO mexer — em uso, não é bug</small></span>'
            f'<span class="astat ok"><b>{n_real}</b> mortos reais<br><small>auditados, seguros</small></span>'
            f'<span class="astat int"><b>{n_int}</b> só uso interno<br><small>export redundante, símbolo vivo</small></span>'
            f'<span class="astat warn"><b>{n_man}</b> scripts manuais<br><small>arquivar</small></span>'
            f'</div></div>')

    # selo do goal no rodapé (prova da convergência)
    audit_footer = ""
    if a_rounds:
        fps = " · ".join(r.get("fingerprint", "") for r in a_rounds)
        ok = conv and ident
        audit_footer = (
            f'<div class="goalseal {"ok" if ok else "warn"}">'
            f'<div class="gtitle">🎯 Goal — auditar o relatório do Fallow</div>'
            f'<div class="gbody">Critério: repetir a auditoria até <b>3 rodadas consecutivas idênticas</b>; '
            f'cada buraco novo (falso-positivo não pego antes) reinicia a contagem.<br>'
            f'Resultado: <b>{"✓ CONVERGIU" if ok else "⚠ não estabilizou"}</b> em {len(a_rounds)} rodadas. '
            f'Fingerprints: <code>{esc(fps)}</code> {"(idênticos)" if ident else "(divergem)"}.</div></div>')

    sections = []
    for b in buckets:
        if not b["items"]:
            continue
        rows = []
        for it in b["items"]:
            cmap = {"confirmado": ("ok", "✓ confirmado"), "fp": ("fp", "🛑 não deletar"),
                    "verificar": ("warn", "⚠ verificar"), "interno": ("warn", "↩ só interno")}
            tag_cls, tag_txt = cmap.get(it["conf"], ("warn", "⚠ verificar"))
            badge = f'<span class="badge">{esc(it["badge"])}</span>' if it.get("badge") else ""
            sel = esc(it["path"] + ((" · " + it["badge"]) if it.get("badge") and it["badge"] not in ("dep",) else ""))
            rows.append(
                f'<div class="row" data-conf="{it["conf"]}" data-bucket="{b["key"]}">'
                f'<input type="checkbox" data-label="{sel}" data-bucket="{esc(b["title"])}">'
                f'<details class="ritem"><summary>'
                f'<span class="rtop"><code>{esc(it["path"])}</code>{badge}'
                f'<span class="tag {tag_cls}">{tag_txt}</span><span class="chev">›</span></span>'
                f'<span class="rhuman">{it["prob_h"]}</span></summary>'
                f'<div class="rdetail">'
                f'<div class="block prob"><span class="blabel">⛔ Problema</span>'
                f'<div class="bh">{it["prob_h"]}</div><div class="bt">{it["prob_t"]}</div></div>'
                f'<div class="block sol"><span class="blabel">✅ Solução</span>'
                f'<div class="bh">{it["sol_h"]}</div><div class="bt">{it["sol_t"]}</div></div>'
                f'</div></details></div>'
            )
        sections.append(
            f'<details class="bucket" open><summary>{b["emoji"]} {esc(b["title"])} '
            f'<span class="bcount">{len(b["items"])}</span></summary>'
            f'<div class="rows">{"".join(rows)}</div></details>'
        )

    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fallow · {esc(project_name)}</title><style>
:root{{--bg:#1A1625;--card:#2A2438;--card-hi:#342C44;--deep:#221D2E;--text:#F0EDF5;
--dim:#A599B5;--mute:#7A7089;--accent:#FFA88C;--ok:#7FD1AE;--warn:#FFD166;--danger:#FF6B8A;
--border:rgba(255,255,255,.08);--bstrong:rgba(255,255,255,.14)}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,sans-serif;
font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1000px;margin:0 auto;padding:56px 28px 180px}}
.pill{{display:inline-block;padding:8px 18px;background:rgba(255,168,140,.12);color:var(--accent);
font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;border-radius:999px;margin-bottom:20px}}
h1{{font-size:40px;font-weight:800;letter-spacing:-.02em;margin-bottom:10px}}
h1 em{{color:var(--accent);font-style:normal}}
.sub{{color:var(--dim);margin-bottom:24px}}
.chips{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:32px}}
.chip{{padding:8px 16px;background:var(--card);border:1px solid var(--border);border-radius:999px;
font-size:13px;color:var(--dim)}}
.chip.grade{{background:rgba(127,209,174,.12);border-color:var(--ok);color:var(--ok);font-weight:700}}
.bucket{{background:var(--card);border:1px solid var(--border);border-radius:18px;margin-bottom:14px;overflow:hidden}}
.bucket summary{{padding:18px 24px;cursor:pointer;font-size:18px;font-weight:700;list-style:none;display:flex;align-items:center;gap:12px}}
.bucket summary::-webkit-details-marker{{display:none}}
.bcount{{margin-left:auto;background:var(--deep);color:var(--dim);font-size:13px;padding:2px 12px;border-radius:999px}}
.rows{{padding:0 16px 14px}}
.row{{display:flex;align-items:flex-start;gap:12px;padding:11px 12px;border-radius:10px;border-bottom:1px dashed var(--border)}}
.row:last-child{{border-bottom:none}}
.row:hover{{background:var(--card-hi)}}
.row input{{margin-top:4px;width:17px;height:17px;accent-color:var(--accent);flex-shrink:0;cursor:pointer}}
.ritem{{flex:1;min-width:0}}
.ritem summary{{list-style:none;cursor:pointer;outline:none}}
.ritem summary::-webkit-details-marker{{display:none}}
.rtop{{display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.rtop code{{color:var(--text);font-family:'SF Mono',Menlo,monospace;font-size:13px;word-break:break-all}}
.badge{{font-size:11px;font-weight:700;color:var(--accent);background:rgba(255,168,140,.12);padding:1px 8px;border-radius:6px;white-space:nowrap}}
.rhuman{{display:block;color:var(--dim);font-size:13px;margin-top:3px;line-height:1.45}}
.rhuman b{{color:var(--text);font-weight:600}}
.chev{{margin-left:auto;color:var(--mute);font-size:18px;transition:transform .2s;flex-shrink:0}}
.ritem[open] .chev{{transform:rotate(90deg);color:var(--accent)}}
.rdetail{{margin-top:10px;display:flex;flex-direction:column;gap:8px}}
.block{{padding:11px 13px;background:var(--deep);border:1px solid var(--border);border-radius:9px;border-left:3px solid var(--border)}}
.block.prob{{border-left-color:var(--danger)}}
.block.sol{{border-left-color:var(--ok)}}
.blabel{{display:block;font-size:11px;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin-bottom:6px}}
.block.prob .blabel{{color:var(--danger)}}
.block.sol .blabel{{color:var(--ok)}}
.bh{{font-size:13px;color:var(--text);line-height:1.5}}
.bt{{font-size:12.5px;color:var(--dim);line-height:1.6;margin-top:5px}}
.block code{{background:var(--card-hi);padding:1px 6px;border-radius:5px;font-family:'SF Mono',Menlo,monospace;font-size:12px;color:var(--accent);word-break:break-all}}
.block b{{color:var(--text)}}
.tag{{flex-shrink:0;font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;align-self:center}}
.tag.ok{{background:rgba(127,209,174,.14);color:var(--ok)}}
.tag.warn{{background:rgba(255,209,102,.14);color:var(--warn)}}
.tag.fp{{background:rgba(255,107,138,.16);color:var(--danger)}}
.auditcard{{background:linear-gradient(145deg,var(--card),rgba(157,140,255,.06));border:1px solid var(--bstrong);border-radius:18px;padding:22px 24px;margin-bottom:26px}}
.ahead{{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}}
.apill{{font-size:12px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--accent-2,#9D8CFF)}}
.aconv{{font-size:12px;font-weight:700;padding:3px 12px;border-radius:999px}}
.aconv.ok{{background:rgba(127,209,174,.14);color:var(--ok)}}
.aconv.warn{{background:rgba(255,209,102,.14);color:var(--warn)}}
.asub{{font-size:13px;color:var(--dim);line-height:1.55;margin-bottom:16px;max-width:760px}}
.astats{{display:flex;gap:12px;flex-wrap:wrap}}
.astat{{flex:1;min-width:150px;background:var(--deep);border:1px solid var(--border);border-radius:12px;padding:14px 16px;font-size:12.5px;color:var(--dim);line-height:1.4;border-left:3px solid var(--border)}}
.astat b{{font-size:24px;font-weight:800;color:var(--text);display:block;margin-bottom:2px}}
.astat small{{color:var(--mute)}}
.astat.fp{{border-left-color:var(--danger)}} .astat.fp b{{color:var(--danger)}}
.astat.ok{{border-left-color:var(--ok)}} .astat.ok b{{color:var(--ok)}}
.astat.warn{{border-left-color:var(--warn)}} .astat.warn b{{color:var(--warn)}}
.astat.int{{border-left-color:var(--accent)}} .astat.int b{{color:var(--accent)}}
.goalseal{{margin-top:40px;padding:20px 24px;border-radius:16px;background:var(--deep);border:1px solid var(--border)}}
.goalseal.ok{{border-color:rgba(127,209,174,.35)}}
.goalseal.warn{{border-color:rgba(255,209,102,.35)}}
.gtitle{{font-size:14px;font-weight:800;color:var(--text);margin-bottom:8px}}
.gbody{{font-size:12.5px;color:var(--dim);line-height:1.65}}
.gbody code{{background:var(--card-hi);padding:1px 6px;border-radius:5px;font-family:'SF Mono',Menlo,monospace;font-size:11.5px;color:var(--accent)}}
.gbody b{{color:var(--text)}}
.legend{{display:flex;flex-direction:column;gap:10px;background:var(--card);border:1px solid var(--border);
border-radius:14px;padding:16px 20px;margin-bottom:26px}}
.legend .lrow{{display:flex;align-items:flex-start;gap:12px;font-size:13.5px;color:var(--dim);line-height:1.5}}
.legend .lrow .tag{{flex-shrink:0;margin-top:1px}}
.legend b{{color:var(--text)}}
.bar{{position:sticky;bottom:18px;margin-top:24px;padding:14px 18px;background:rgba(42,36,56,.94);
backdrop-filter:blur(14px);border:1px solid var(--bstrong);border-radius:16px;display:flex;gap:10px;
flex-wrap:wrap;align-items:center;box-shadow:0 18px 50px rgba(0,0,0,.4);z-index:10}}
.bar .count{{color:var(--dim);font-size:13px;margin-right:auto}}
.bar .count b{{color:var(--accent)}}
.btn{{cursor:pointer;padding:11px 18px;border-radius:12px;font-size:13px;font-weight:700;
border:1px solid var(--bstrong);background:var(--card-hi);color:var(--text);font-family:inherit}}
.btn:hover{{border-color:var(--accent)}}
.btn.primary{{background:var(--accent);border-color:var(--accent);color:var(--bg)}}
.btn.copied{{background:var(--ok)!important;border-color:var(--ok)!important;color:var(--bg)!important}}
.live{{position:fixed;top:16px;right:16px;display:none;align-items:center;gap:6px;padding:4px 10px;
background:var(--deep);border:1px solid var(--border);border-radius:999px;font-size:11px;font-weight:700;text-transform:uppercase}}
.live.ok{{display:inline-flex;color:var(--ok);border-color:var(--ok)}}
.live.err{{display:inline-flex;color:var(--warn);border-color:var(--warn)}}
</style></head><body>
<span class="live" id="live"></span>
<div class="wrap">
<div class="pill">Fallow · relatório</div>
<h1>O que dá pra limpar em <em>{esc(project_name)}</em></h1>
<p class="sub">Marque o que quer eliminar e diga "ok" (ou clique em copiar). Eu limpo só o marcado, com preview + build/test — nunca às cegas.</p>
<div class="chips"><span class="chip grade">saúde {esc(grade)} ({esc(score)})</span>
<span class="chip">{esc(chips)}</span></div>
{audit_card}
<div class="legend">
<div class="lrow"><span class="tag ok">✓ confirmado</span><span><b>Órfão real, seguro eliminar.</b> A auditoria confirmou 0 referências — nem import, nem cron, nem rota.</span></div>
<div class="lrow"><span class="tag fp">🛑 não deletar</span><span><b>Limitação do Fallow, não bug do código.</b> Está em uso, mas acionado de fora do que a análise estática enxerga: agendador/rota/import dinâmico, ou <b>import dentro de .svelte/.vue</b>. O código está certo; só não mexer.</span></div>
<div class="lrow"><span class="tag warn">↩ só interno</span><span><b>Usado só dentro do próprio arquivo.</b> O <code>export</code> é redundante, mas o símbolo NÃO é morto — apagá-lo quebraria o arquivo. Tirar só a keyword <code>export</code> é opcional/cosmético.</span></div>
<div class="lrow"><span class="tag warn">⚠ verificar</span><span><b>Script CLI manual / a decidir.</b> Sem refs e não agendado, mas pode ser ferramenta rodada à mão. Arquivar, não deletar. Vem desmarcado.</span></div>
</div>
{"".join(sections)}
<div class="bar"><span class="count"><b id="n">0</b> selecionados</span>
<button class="btn" onclick="pick('confirmado')">Só os seguros (✓)</button>
<button class="btn" onclick="pickNotFp()">Tudo menos 🛑</button>
<button class="btn" onclick="clr()">Limpar</button>
<button class="btn primary" onclick="cp(this)">📋 Copiar seleção</button></div>
{audit_footer}
</div>
<script>
window.VISUAL_SESSION={json.dumps(session)};
function boxes(){{return[...document.querySelectorAll('.row input')]}}
function upd(){{document.getElementById('n').textContent=boxes().filter(b=>b.checked).length;post()}}
function pick(c){{boxes().forEach(b=>{{b.checked=b.closest('.row').dataset.conf===c}});upd()}}
function pickNotFp(){{boxes().forEach(b=>{{b.checked=b.closest('.row').dataset.conf!=='fp'}});upd()}}
function clr(){{boxes().forEach(b=>b.checked=false);upd()}}
boxes().forEach(b=>b.addEventListener('change',upd));
function collect(){{
 const by={{}};boxes().filter(b=>b.checked).forEach(b=>{{
  (by[b.dataset.bucket]=by[b.dataset.bucket]||[]).push(b.dataset.label)}});
 let out=['<!-- fallow-selection v1 -->','🧹 **Limpar em {esc(project_name)}:**',''];
 for(const k in by){{out.push('**'+k+'** ('+by[k].length+'):');by[k].forEach(x=>out.push('- '+x));out.push('')}}
 if(!Object.keys(by).length)out.push('(nada selecionado)');
 out.push('<!-- /fallow-selection -->');return out.join('\\n')}}
function cp(btn){{const t=collect();navigator.clipboard.writeText(t).then(()=>{{
 btn.textContent='✓ Copiado';btn.classList.add('copied');setTimeout(()=>{{btn.textContent='📋 Copiar seleção';btn.classList.remove('copied')}},2000)}})}}
var pt=null;
function post(){{if(!window.VISUAL_SESSION)return;clearTimeout(pt);pt=setTimeout(()=>{{
 const by={{}};boxes().filter(b=>b.checked).forEach(b=>(by[b.dataset.bucket]=by[b.dataset.bucket]||[]).push(b.dataset.label));
 fetch('http://127.0.0.1:7755/state',{{method:'POST',headers:{{'Content-Type':'application/json'}},
  body:JSON.stringify({{session:window.VISUAL_SESSION,docTitle:document.title,state:{{selection:by}}}}),keepalive:true}})
  .then(r=>document.getElementById('live').className='live '+(r.ok?'ok':'err'))
  .catch(()=>document.getElementById('live').className='live err')}},400)}}
</script></body></html>"""


def main():
    if len(sys.argv) < 2:
        print("uso: report.py <project_root> [session]", file=sys.stderr)
        sys.exit(2)
    root = os.path.abspath(sys.argv[1])
    session = sys.argv[2] if len(sys.argv) > 2 else "fallow-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    name = os.path.basename(root.rstrip("/"))

    dead = run_fallow("dead-code", root)
    dupes = run_fallow("dupes", root)
    health = run_fallow("health", root)
    audit = run_audit_engine(root)

    buckets = build_buckets(dead, dupes, health, audit)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_dir = os.path.expanduser("~/Desktop/claude-visual")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{stamp}-fallow-{name}.html")
    with open(out_path, "w") as f:
        f.write(render_html(name, buckets, health, session, stamp, audit))

    summary = {b["title"]: len(b["items"]) for b in buckets}
    print(out_path)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
