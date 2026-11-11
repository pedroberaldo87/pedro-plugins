#!/usr/bin/env python3
"""Suite do report.py — stdlib, sem framework (padrão do repo).

    python3 plugins/fallow/lib/test_report.py

O que ela existe pra provar: o relatório do /fallow é RECUSADO quando o nível 0
de um achado é texto corrido. Antes disso o gerador só avisava no stderr e a
página nascia torta do mesmo jeito — e o `release-gate` nem rodava nada aqui,
porque não havia `test_*.py` neste plugin.

O fallow real não é chamado: `run_fallow` sai por `npx`, que depende de rede.
O que entra no lugar é a saída dele em JSON, sintética, cobrindo cada veredito
que a auditoria sabe emitir — é a redação DESTE arquivo que está sob medição,
não a do analisador.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report as R  # noqa: E402
from regua_texto import BULLET_MAX  # noqa: E402

FAILS = []


def check(label, cond, extra=""):
    print(("  ok   " if cond else "  FAIL ") + label + (" %s" % (extra,) if not cond else ""))
    if not cond:
        FAILS.append(label)


# ── a saída do fallow, sintética, acionando cada veredito ──────────────────

DEAD = {
    "unused_files": [{"path": "src/a.ts"}, {"path": "scripts/b.ts"},
                     {"path": "src/c.ts"}, {"path": "src/d.ts"}],
    "unused_exports": [{"path": "src/e.ts", "export_name": "foo", "line": 3},
                       {"path": "src/e.ts", "export_name": "bar", "line": 4},
                       {"path": "src/e.ts", "export_name": "baz", "line": 5},
                       {"path": "src/e.ts", "export_name": "qux", "line": 6}],
    "unused_types": [{"path": "src/t.ts", "export_name": "T", "line": 9}],
    "unused_dependencies": [{"name": "lodash"}],
    "circular_dependencies": [{"files": ["src/x/a.ts", "src/y/b.ts"]}],
    "re_export_cycles": [],
}
DUPES = {"clone_families": [{"files": ["src/a.spec.ts", "src/b.spec.ts"],
                             "total_duplicated_lines": 40,
                             "suggestions": [{"description": "extrair helper"}]}]}
HEALTH = {"health_score": {"grade": "B", "score": 70},
          "targets": [{"path": "src/big.ts", "effort": "alto",
                       "recommendation": "Quebrar em módulos",
                       "confidence": "alta", "priority": 9,
                       "factors": [{"detail": "cognitiva 40"}],
                       "evidence": {"complex_functions": [
                           {"name": "f", "line": 2, "cognitive": 40}]}}]}
AUDIT = {"groups": {"g": [
             {"path": "src/a.ts", "verdict": "falso_positivo",
              "reason": "rota HTTP", "proof": "app.get"},
             {"path": "scripts/b.ts", "verdict": "manual_cli",
              "reason": "script solto", "proof": ""},
             {"path": "src/c.ts", "verdict": "dead_confirmado",
              "reason": "", "proof": ""}]},
         "export_verdicts": [
             {"path": "src/e.ts", "name": "foo", "verdict": "falso_positivo",
              "reason": "usado no .svelte", "proof": "x"},
             {"path": "src/e.ts", "name": "bar", "verdict": "usado_interno",
              "reason": "uso local", "proof": ""},
             {"path": "src/e.ts", "name": "baz", "verdict": "dead_confirmado",
              "reason": "", "proof": ""}]}


def bucket(prob_h, sol_h="Deletar o arquivo."):
    return [{"key": "morto", "emoji": "🧟", "title": "Código morto",
             "items": [{"path": "src/a.ts", "badge": None, "conf": "confirmado",
                        "prob_h": prob_h, "prob_t": "prova crua",
                        "sol_h": sol_h, "sol_t": "prova crua"}]}]


def render(buckets):
    return R.render_html("proj", buckets, HEALTH, "sessao", "2026-01-01", AUDIT)


def main():
    print("perfil e régua")
    check("o perfil declarado é o de página", R.PERFIL == "pagina")

    print("o live-sync manda o segredo do daemon do /visual")
    tok = "cd" * 32
    pg = R.render_html("proj", bucket("Texto curto."), HEALTH, "sessao", "2026-01-01", AUDIT, token=tok)
    check("a página embute o token recebido", 'window.VISUAL_TOKEN="%s"' % tok in pg)
    check("o fetch manda X-Visual-Token", "'X-Visual-Token':window.VISUAL_TOKEN" in pg)
    pg0 = R.render_html("proj", bucket("Texto curto."), HEALTH, "sessao", "2026-01-01", AUDIT, token="")
    check("sem token a página sai com VISUAL_TOKEN vazio (copy/paste)", 'window.VISUAL_TOKEN=""' in pg0)
    tmpd = tempfile.mkdtemp(prefix="fallow-tok-")
    try:
        tf = os.path.join(tmpd, ".token")
        with open(tf, "w") as fh:
            fh.write(tok + "\n")
        check("visual_sync_token lê o arquivo de 64 hex", R.visual_sync_token(tf) == tok)
        with open(tf, "w") as fh:
            fh.write('x"</script>')
        check("conteúdo que não é hex de 64 é descartado", R.visual_sync_token(tf) == "")
        check("arquivo ausente dá vazio", R.visual_sync_token(os.path.join(tmpd, "nope")) == "")
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)

    print("os textos que o programa REALMENTE escreve passam na régua")
    buckets = R.build_buckets(DEAD, DUPES, HEALTH, AUDIT)
    check("os 5 baldes saem preenchidos",
          len([b for b in buckets if b["items"]]) == 5,
          [(b["key"], len(b["items"])) for b in buckets])
    errs = []
    for b in buckets:
        for it in b["items"]:
            for campo in ("prob_h", "sol_h"):
                errs += R.erros_de_estilo(it.get(campo), "%s: %s" % (b["key"], campo))
    check("nenhum nível 0 viola a régua", errs == [], errs[:3])
    check("e o relatório inteiro é gerado", "<!DOCTYPE html>" in render(buckets))

    print("texto corrido é RECUSADO — nada de HTML sai")
    try:
        render(bucket("O arquivo está órfão. Ninguém importa ele."))
        check("duas frases no nível 0 são recusadas", False)
    except R.ReportError as exc:
        check("duas frases no nível 0 são recusadas", True)
        check("e a recusa vem com o motivo medido", "duas frases" in str(exc), str(exc))
        check("e diz em qual achado", "morto · src/a.ts: prob_h" in str(exc), str(exc))

    longo = "Ninguém importa este arquivo em lugar nenhum do projeto, nem por import " \
            "estático, nem por import dinâmico, nem por rota HTTP registrada no servidor"
    check("o exemplo passa do teto de %d caracteres" % BULLET_MAX,
          len(longo) > BULLET_MAX, len(longo))
    try:
        render(bucket(longo))
        check("nível 0 acima de 140 caracteres é recusado", False)
    except R.ReportError as exc:
        check("nível 0 acima de 140 caracteres é recusado", "caracteres" in str(exc), str(exc))

    try:
        render(bucket("Órfão confirmado.", "E dá pra deletar o arquivo."))
        check("conectivo de continuação no nível 0 é recusado", False)
    except R.ReportError as exc:
        check("conectivo de continuação no nível 0 é recusado",
              "conectivo" in str(exc), str(exc))

    check("a marcação não conta no teto — o teto conta o que o olho lê",
          R.erros_de_estilo("<b>Órfão confirmado</b> — 0 referências.", "x") == [])

    print("o `main` recusa: sai 2 e não deixa arquivo pra trás")
    raiz = tempfile.mkdtemp(prefix="fallow-report-test-")
    fallow_real, audit_real, buckets_real = R.run_fallow, R.run_audit_engine, R.build_buckets
    # O `main` agora cria o token do live-sync em ~/.claude: nunca no HOME de verdade.
    lar = tempfile.mkdtemp(prefix="fallow-report-home-")
    env_real = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE")}
    os.environ["HOME"] = os.environ["USERPROFILE"] = lar
    try:
        os.makedirs(os.path.join(raiz, ".git"))
        R.run_fallow = lambda cmd, root: {}
        R.run_audit_engine = lambda root: {}
        saida = os.path.join(raiz, ".claude", "visual")

        R.build_buckets = lambda d, u, h, a=None: bucket("O arquivo está órfão. Ninguém importa ele.")
        sys.argv = ["report.py", raiz]
        try:
            R.main()
            check("o `main` sai 2 na recusa", False)
        except SystemExit as e:
            check("o `main` sai 2 na recusa", e.code == 2, e.code)
        check("e nenhum HTML sai",
              [] == [f for f in os.listdir(saida) if f.endswith(".html")]
              if os.path.isdir(saida) else True,
              os.path.isdir(saida) and os.listdir(saida))

        R.build_buckets = lambda d, u, h, a=None: bucket("Órfão confirmado — 0 referências.")
        R.main()
        paginas = [f for f in os.listdir(saida) if f.endswith(".html")]
        check("e o HTML sai quando a régua passa", paginas != [])
        tp = os.path.join(lar, ".claude", "visual-state", ".token")
        check("primeiro relatório da máquina: o `main` cria o token (64 hex)",
              R.visual_sync_token(tp) != "")
        if paginas:
            conteudo = open(os.path.join(saida, paginas[0]), encoding="utf-8").read()
            check("  …e a página já sai com ele embutido",
                  'window.VISUAL_TOKEN="%s"' % R.visual_sync_token(tp) in conteudo)
            if os.name == "posix":
                check("a página sai 0600 (leva o token e pode cair numa Desktop sincronizada)",
                      (os.stat(os.path.join(saida, paginas[0])).st_mode & 0o777) == 0o600,
                      oct(os.stat(os.path.join(saida, paginas[0])).st_mode))
                check("  …o token criado é 0600", (os.stat(tp).st_mode & 0o777) == 0o600)
                # rodar de novo sobre uma página 0644 de antes: volta a 0600 e o token não gira
                os.chmod(os.path.join(saida, paginas[0]), 0o644)
                tok1 = R.visual_sync_token(tp)
                R.main()
                check("  …página antiga 0644 reescrita volta a 0600",
                      (os.stat(os.path.join(saida, paginas[0])).st_mode & 0o777) == 0o600)
                check("  …e o token não é girado pelo `main`", R.visual_sync_token(tp) == tok1)
        # token solto e token corrompido
        if os.name == "posix":
            os.chmod(tp, 0o644)
            R.ensure_sync_token(tp)
            check("token solto (0644) volta a 0600", (os.stat(tp).st_mode & 0o777) == 0o600)
        with open(tp, "w") as fh:
            fh.write("lixo\n")
        novo = R.ensure_sync_token(tp)
        check("token corrompido é refeito (64 hex) e gravado",
              len(novo) == 64 and R.visual_sync_token(tp) == novo)
    finally:
        R.run_fallow, R.run_audit_engine, R.build_buckets = fallow_real, audit_real, buckets_real
        for k, v in env_real.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(raiz, ignore_errors=True)
        shutil.rmtree(lar, ignore_errors=True)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
