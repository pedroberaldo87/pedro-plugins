#!/usr/bin/env python3
"""Testes do ledger do intent-guard — python3 plugins/intent-guard/lib/test_ledger.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ledger  # noqa: E402


def make_repo():
    d = tempfile.mkdtemp(prefix="ig-test-")
    subprocess.run(["git", "init", "-q", d], check=True)
    open(os.path.join(d, "app.py"), "w").write("print(1)\n")
    subprocess.run(["git", "-C", d, "add", "-A"], check=True)
    subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    return d


def run(args, stdin=""):
    return subprocess.run([sys.executable, os.path.join(HERE, "ledger.py")] + args,
                          input=stdin, capture_output=True, text=True)


def test_concurrent_record_raw():
    """I-2: 8 record-raw concorrentes não podem produzir ids r-N duplicados."""
    repo = make_repo()
    files = []
    try:
        procs = []
        for i in range(8):
            fh = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
            fh.write("pedido concorrente %d" % i)
            fh.close()
            files.append(fh.name)
        opened = [open(fn) for fn in files]
        try:
            for f in opened:
                p = subprocess.Popen([sys.executable, os.path.join(HERE, "ledger.py"),
                                      "record-raw", "--cwd", repo, "--session", "race",
                                      "--text-stdin"], stdin=f, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                procs.append(p)
            for p in procs:
                assert p.wait() == 0
        finally:
            for f in opened:
                f.close()
        evs = ledger.load(os.path.join(repo, ".claude", "intent"))
        raw_ids = [e["id"] for e in evs if e.get("ev") == "raw" and e.get("session") == "race"]
        assert len(raw_ids) == 8, raw_ids
        assert len(set(raw_ids)) == 8, "ids r-N duplicados: %r" % raw_ids
    finally:
        for fn in files:
            os.unlink(fn)
        shutil.rmtree(repo, ignore_errors=True)


def main():
    test_concurrent_record_raw()
    repo = make_repo()
    try:
        # resolve-dir: dentro de git repo → <root>/.claude/intent
        r = run(["resolve-dir", "--cwd", repo])
        assert r.stdout.strip() == os.path.join(repo, ".claude", "intent"), r.stdout

        # record-raw: grava verbatim (com acento, aspas, multiline) + exclude
        texto = 'adiciona export CSV\ncom separador ";" — não mexe no layout'
        r = run(["record-raw", "--cwd", repo, "--session", "sess1", "--text-stdin"], stdin=texto)
        assert r.returncode == 0, r.stderr
        evs = ledger.load(os.path.join(repo, ".claude", "intent"))
        assert len(evs) == 1 and evs[0]["ev"] == "raw" and evs[0]["text"] == texto
        assert evs[0]["id"] == "r-1" and evs[0]["session"] == "sess1"
        excl = open(os.path.join(repo, ".git", "info", "exclude")).read()
        assert ".claude/intent/" in excl
        # git não enxerga o ledger
        st = subprocess.run(["git", "-C", repo, "status", "--porcelain"],
                            capture_output=True, text=True).stdout
        assert ".claude/intent" not in st, st

        # texto vazio não grava
        run(["record-raw", "--cwd", repo, "--session", "sess1", "--text-stdin"], stdin="   ")
        assert len(ledger.load(os.path.join(repo, ".claude", "intent"))) == 1

        # state: 1 pending, 0 live
        st = json.loads(run(["state", "--cwd", repo]).stdout)
        assert len(st["pending"]) == 1 and st["live"] == []

        # apply (classify do juiz): pedido vira p-1 vivo; conversa some
        run(["record-raw", "--cwd", repo, "--session", "sess1", "--text-stdin"], stdin="kkk boa")
        clas = ('{"ev":"classify","raw":"r-1","class":"pedido","resumo":"export CSV ;","substitui":null}\n'
                '{"ev":"classify","raw":"r-2","class":"conversa","resumo":"","substitui":null}\n')
        r = run(["apply", "--cwd", repo], stdin=clas)
        assert r.returncode == 0, r.stderr
        st = json.loads(run(["state", "--cwd", repo]).stdout)
        assert st["pending"] == [] and len(st["live"]) == 1
        assert st["live"][0]["id"] == "p-1" and st["live"][0]["class"] == "pedido"
        assert st["live"][0]["text"] == texto  # verbatim preservado no fold

        # correção substitui pedido
        run(["record-raw", "--cwd", repo, "--session", "sess1", "--text-stdin"], stdin="na real, separador tab")
        clas2 = '{"ev":"classify","raw":"r-3","class":"correcao","resumo":"separador tab","substitui":"p-1"}\n'
        run(["apply", "--cwd", repo], stdin=clas2)
        st = json.loads(run(["state", "--cwd", repo]).stdout)
        assert len(st["live"]) == 1 and st["live"][0]["id"] == "p-2"
        assert st["entries"]["p-1"]["status"] == "substituido"

        # tree-hash: determinístico e sensível a untracked
        h1 = run(["tree-hash", "--cwd", repo]).stdout.strip()
        assert len(h1) == 40
        assert run(["tree-hash", "--cwd", repo]).stdout.strip() == h1
        open(os.path.join(repo, "novo.txt"), "w").write("x")
        h2 = run(["tree-hash", "--cwd", repo]).stdout.strip()
        assert h2 != h1, "untracked tem que mudar o hash"

        # audit-check + apply-audit
        audit = {"tree_hash": h2, "generated_ts": 1, "verdicts": [
            {"entry": "p-2", "verdict": "feito", "mode": "confirmado", "evidence": "rodei o export, saiu com tab"}]}
        ap = os.path.join(repo, ".claude", "intent", "audit-1.json")
        json.dump(audit, open(ap, "w"))
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", ap]).stdout)
        assert chk["ok"] is True, chk
        # tree mudou → audit vence
        open(os.path.join(repo, "outro.txt"), "w").write("y")
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", ap]).stdout)
        assert chk["ok"] is False and any("tree" in w for w in chk["why"])
        os.unlink(os.path.join(repo, "outro.txt"))
        # evidência vazia → falha
        bad = dict(audit)
        bad["verdicts"] = [dict(audit["verdicts"][0], evidence="")]
        bp = os.path.join(repo, ".claude", "intent", "audit-2.json")
        json.dump(bad, open(bp, "w"))
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", bp]).stdout)
        assert chk["ok"] is False
        # não cobre todos os vivos → falha
        empty = {"tree_hash": h2, "generated_ts": 1, "verdicts": []}
        ep = os.path.join(repo, ".claude", "intent", "audit-3.json")
        json.dump(empty, open(ep, "w"))
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", ep]).stdout)
        assert chk["ok"] is False

        # ---- a CATRACA: pedido novo entre auditar e consumir ----
        # O bloqueio pergunta pelos vivos DAQUELE instante, mas o consumo so acontece
        # no Stop seguinte. Sem o sidecar de escopo, todo pedido que chegou no meio
        # entrava na conta e o veredito nascia impossivel de aprovar — medido em
        # 30/07 com 33 pedidos cobrados de uma auditoria que perguntou por 1.
        h3 = run(["tree-hash", "--cwd", repo]).stdout.strip()
        cat = {"tree_hash": h3, "generated_ts": 1, "verdicts": [
            {"entry": "p-2", "verdict": "feito", "mode": "confirmado",
             "evidence": "rodei o export, saiu com tab"}]}
        cp = os.path.join(repo, ".claude", "intent", "audit-cat.json")
        json.dump(cat, open(cp, "w"))
        json.dump(["p-2"], open(cp + ".escopo", "w"))   # o gate perguntou so por p-2
        assert json.loads(run(["audit-check", "--cwd", repo, "--file", cp]).stdout)["ok"] is True

        # chega pedido novo DEPOIS da auditoria
        run(["record-raw", "--cwd", repo, "--session", "s1", "--text-stdin"],
            stdin="agora faz outra coisa")
        evs4 = ledger.load(os.path.join(repo, ".claude", "intent"))
        novo_raw = [e for e in evs4 if e.get("ev") == "raw"][-1]["id"]
        run(["apply", "--cwd", repo], stdin=json.dumps(
            {"ev": "classify", "raw": novo_raw, "class": "pedido",
             "resumo": "pedido que chegou depois", "substitui": None}) + "\n")
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", cp]).stdout)
        assert chk["ok"] is True, ("pedido que chegou DEPOIS nao e responsabilidade "
                                   "deste veredito: %s" % chk)

        # sem sidecar, o mesmo arquivo reprova — compatibilidade com auditoria antiga
        os.unlink(cp + ".escopo")
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", cp]).stdout)
        assert chk["ok"] is False and any("sem veredito" in w for w in chk["why"]), chk

        # ---- o veredito nao vence com o conserto que ele mesmo pediu ----
        # O auditor aponta um problema, o agente conserta, e o conserto invalidava o
        # veredito recem-chegado. So reprova se mexeu no que o veredito CITOU.
        run(["record-raw", "--cwd", repo, "--session", "s9", "--text-stdin"],
            stdin="arruma o alvo")
        alvo_f = os.path.join(repo, "alvo.py")
        open(alvo_f, "w").write("# antes\n")
        h5 = run(["tree-hash", "--cwd", repo]).stdout.strip()
        aud5 = {"tree_hash": h5, "generated_ts": 1, "verdicts": [
            {"entry": "p-2", "verdict": "feito", "mode": "confirmado",
             "evidence": "conferi alvo.py e o comportamento bate"}]}
        p5 = os.path.join(repo, ".claude", "intent", "audit-5.json")
        json.dump(aud5, open(p5, "w"))
        json.dump(["p-2"], open(p5 + ".escopo", "w"))
        assert json.loads(run(["audit-check", "--cwd", repo, "--file", p5]).stdout)["ok"] is True

        # mexe em arquivo que o veredito NAO cita -> continua valendo
        open(os.path.join(repo, "nao-citado.txt"), "w").write("z")
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", p5]).stdout)
        assert chk["ok"] is True, ("mudanca fora do que o veredito auditou nao pode "
                                   "vencer o veredito: %s" % chk)

        # mexe no arquivo CITADO -> vence, como tem que ser
        open(alvo_f, "w").write("# depois\n")
        chk = json.loads(run(["audit-check", "--cwd", repo, "--file", p5]).stdout)
        assert chk["ok"] is False and any("tree" in w for w in chk["why"]), chk
        os.unlink(os.path.join(repo, "nao-citado.txt"))
        os.unlink(alvo_f)

        # limpeza: os pedidos que ESTE bloco criou nao podem vazar pros testes
        # seguintes, que afirmam sobre a lista de vivos.
        st_tmp = json.loads(run(["state", "--cwd", repo]).stdout)
        for e in st_tmp["live"]:
            if e["id"] != "p-2":
                run(["baixa", "--cwd", repo, "--id", e["id"], "--by", "usuario",
                     "--reason", "limpeza do teste"])

        # apply-audit: feito+confirmado → baixa automática (EXPERIMENTAL); idempotente
        run(["apply-audit", "--cwd", repo, "--file", ap])
        st = json.loads(run(["state", "--cwd", repo]).stdout)
        assert st["live"] == [] and st["entries"]["p-2"]["status"] == "baixado:auditor"
        n = len(ledger.load(os.path.join(repo, ".claude", "intent")))
        run(["apply-audit", "--cwd", repo, "--file", ap])  # 2ª vez: no-op
        assert len(ledger.load(os.path.join(repo, ".claude", "intent"))) == n

        # baixa manual
        run(["record-raw", "--cwd", repo, "--session", "s2", "--text-stdin"], stdin="faz X")
        run(["apply", "--cwd", repo],
            stdin='{"ev":"classify","raw":"r-4","class":"pedido","resumo":"X","substitui":null}\n')
        run(["baixa", "--cwd", repo, "--id", "p-3", "--by", "usuario", "--reason", "esquece"])
        st = json.loads(run(["state", "--cwd", repo]).stdout)
        assert st["live"] == []

        # worktree: .git é um FILE, não diretório — exclude e tree-hash têm que
        # funcionar do mesmo jeito que num repo normal (I-1)
        wt_parent = tempfile.mkdtemp(prefix="ig-wt-parent-")
        wt_dir = os.path.join(wt_parent, "wt")
        subprocess.run(["git", "-C", repo, "worktree", "add", wt_dir, "-b", "wtbranch"],
                       check=True, capture_output=True)
        try:
            r = run(["record-raw", "--cwd", wt_dir, "--session", "wtsess", "--text-stdin"],
                    stdin="pedido gravado dentro do worktree")
            assert r.returncode == 0, r.stderr
            st_wt = subprocess.run(["git", "-C", wt_dir, "status", "--porcelain"],
                                   capture_output=True, text=True).stdout
            assert ".claude/intent" not in st_wt, st_wt
            h_wt = run(["tree-hash", "--cwd", wt_dir]).stdout.strip()
            assert len(h_wt) == 40 and all(c in "0123456789abcdef" for c in h_wt), h_wt
        finally:
            subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", wt_dir],
                           capture_output=True)
            shutil.rmtree(wt_parent, ignore_errors=True)

        # status roda e menciona o descartado
        out = run(["status", "--cwd", repo]).stdout
        assert "conversa" in out or "descartado" in out.lower()

        # fora de git/projeto → fallback em ~/.claude/intent/<slug>
        loose = tempfile.mkdtemp(prefix="ig-loose-")
        d = run(["resolve-dir", "--cwd", loose]).stdout.strip()
        assert d.startswith(os.path.expanduser("~/.claude/intent/")), d
        shutil.rmtree(loose)

        # Fail-open: intent dir read-only (I/O error) degradação silenciosa.
        # Skip if running as root (ignores modos de arquivo).
        if os.getuid() != 0:
            intent = os.path.join(repo, ".claude", "intent")
            orig_mode = os.stat(intent).st_mode
            os.chmod(intent, 0o555)  # read-only
            r = run(["record-raw", "--cwd", repo, "--session", "s3", "--text-stdin"],
                    stdin="teste de fail-open")
            assert r.returncode == 0, f"Exit code deve ser 0, foi {r.returncode}"
            assert "Traceback" not in r.stderr, f"Sem traceback: {r.stderr}"
            # Verificar fallback JSON para leitura
            r_state = run(["state", "--cwd", repo])
            assert r_state.returncode == 0
            st = json.loads(r_state.stdout)
            assert "pending" in st and "live" in st, f"Fallback JSON: {st}"
            os.chmod(intent, orig_mode)  # restaurar para cleanup funcionar

        # REGRESSÃO (smoke E2E 2026-07-24): auditar EXECUTA código, e executar
        # cria artefato (__pycache__, node_modules...). Se isso mudasse o
        # tree-hash, todo veredito nasceria vencido, o gate nunca fecharia e
        # liberaria SEM auditoria — o oposto do propósito do plugin.
        h_before = run(["tree-hash", "--cwd", repo]).stdout.strip()
        os.makedirs(os.path.join(repo, "__pycache__"), exist_ok=True)
        open(os.path.join(repo, "__pycache__", "m.cpython-314.pyc"), "w").write("x")
        os.makedirs(os.path.join(repo, "node_modules", "leftpad"), exist_ok=True)
        open(os.path.join(repo, "node_modules", "leftpad", "index.js"), "w").write("x")
        open(os.path.join(repo, "run.log"), "w").write("saida do teste")
        h_after = run(["tree-hash", "--cwd", repo]).stdout.strip()
        assert h_after == h_before, "artefato de execução NÃO pode mudar o tree-hash"
        # mas código de verdade continua mudando o hash
        open(os.path.join(repo, "codigo_novo.py"), "w").write("print(1)\n")
        assert run(["tree-hash", "--cwd", repo]).stdout.strip() != h_before, \
            "código novo TEM que mudar o tree-hash"

        # REGRESSÃO (relato do usuário, 2026-07-24, num monorepo): duas sessões
        # PARALELAS no mesmo projeto (Prisma numa, Workplace noutra) dividiam a
        # lista de vivos — o gate de uma cobrava os pedidos da outra. Uma única
        # auditoria real chegou a cobrar 3 frentes de 3 sessões.
        iso = make_repo()
        try:
            run(["record-raw", "--cwd", iso, "--session", "sessA", "--text-stdin"],
                stdin="aqui é só prisma")
            run(["record-raw", "--cwd", iso, "--session", "sessB", "--text-stdin"],
                stdin="analisa o feedback do workplace")
            # cada sessão só enxerga o SEU cru pendente
            sa = json.loads(run(["state", "--cwd", iso, "--session", "sessA"]).stdout)
            sb = json.loads(run(["state", "--cwd", iso, "--session", "sessB"]).stdout)
            assert [r["text"] for r in sa["pending"]] == ["aqui é só prisma"], sa["pending"]
            assert [r["text"] for r in sb["pending"]] == ["analisa o feedback do workplace"]
            # sem --session, o caderno inteiro continua visível (o /intent-guard status)
            todos = json.loads(run(["state", "--cwd", iso]).stdout)
            assert len(todos["pending"]) == 2

            run(["apply", "--cwd", iso],
                stdin='{"ev":"classify","raw":"r-1","class":"pedido","resumo":"prisma","substitui":null}\n'
                      '{"ev":"classify","raw":"r-2","class":"pedido","resumo":"workplace","substitui":null}\n')
            la = json.loads(run(["state", "--cwd", iso, "--session", "sessA"]).stdout)["live"]
            lb = json.loads(run(["state", "--cwd", iso, "--session", "sessB"]).stdout)["live"]
            assert len(la) == 1 and la[0]["resumo"] == "prisma", la
            assert len(lb) == 1 and lb[0]["resumo"] == "workplace", lb
            assert la[0]["session"] == "sessA" and lb[0]["session"] == "sessB"

            # a auditoria da sessão A cobre só o pedido de A — e o gate ACEITA
            hh = run(["tree-hash", "--cwd", iso]).stdout.strip()
            ap = os.path.join(iso, ".claude", "intent", "audit-iso.json")
            json.dump({"tree_hash": hh, "generated_ts": 1, "verdicts": [
                {"entry": la[0]["id"], "verdict": "feito", "mode": "confirmado",
                 "evidence": "rodei o prisma e conferi o schema"}]}, open(ap, "w"))
            chk = json.loads(run(["audit-check", "--cwd", iso, "--session", "sessA",
                                  "--file", ap]).stdout)
            assert chk["ok"] is True, chk  # antes: exigia veredito do pedido de sessB
            # e sem escopo, a MESMA auditoria é (corretamente) insuficiente pro caderno todo
            chk_all = json.loads(run(["audit-check", "--cwd", iso, "--file", ap]).stdout)
            assert chk_all["ok"] is False
        finally:
            shutil.rmtree(iso, ignore_errors=True)

        # ESCADA DE CUSTO (decisão de projeto, 2026-07-24): pedido com receita
        # mecânica é resolvido por CÓDIGO, sem gastar agente. Numa sessão real,
        # 4 de 7 pedidos eram "commit push" — ~50k tokens cada pra conferir hash.
        esc = make_repo()
        try:
            # espelho local faz as vezes de "origin" (sem rede no teste)
            bare = tempfile.mkdtemp(prefix="ig-bare-")
            subprocess.run(["git", "init", "-q", "--bare", bare], check=True)
            subprocess.run(["git", "-C", esc, "remote", "add", "origin", bare], check=True)
            subprocess.run(["git", "-C", esc, "push", "-q", "-u", "origin", "HEAD"], check=True)

            run(["record-raw", "--cwd", esc, "--session", "s1", "--text-stdin"], stdin="commit push")
            run(["apply", "--cwd", esc],
                stdin='{"ev":"classify","raw":"r-1","class":"pedido","resumo":"commit push",'
                      '"substitui":null,"verify":"git_synced"}\n')
            # tudo sincronizado → receita resolve sozinha, sem LLM
            v = json.loads(run(["verify", "--cwd", esc, "--session", "s1"]).stdout)
            assert len(v["resolved"]) == 1 and v["remaining"] == 0, v
            assert "git_synced" in v["resolved"][0]["recipe"]
            ent = json.loads(run(["state", "--cwd", esc]).stdout)["entries"]["p-1"]
            assert ent["status"] == "baixado:receita", ent["status"]
            assert ent["verdicts"][0]["mode"] == "confirmado"

            # commit local não publicado → a receita REPROVA (não é carimbo automático)
            open(os.path.join(esc, "novo.py"), "w").write("x=1\n")
            subprocess.run(["git", "-C", esc, "add", "-A"], check=True)
            subprocess.run(["git", "-C", esc, "-c", "user.email=t@t", "-c", "user.name=t",
                            "commit", "-qm", "local"], check=True)
            run(["record-raw", "--cwd", esc, "--session", "s1", "--text-stdin"], stdin="sobe pro git")
            run(["apply", "--cwd", esc],
                stdin='{"ev":"classify","raw":"r-2","class":"pedido","resumo":"sobe",'
                      '"substitui":null,"verify":"git_synced"}\n')
            v = json.loads(run(["verify", "--cwd", esc, "--session", "s1"]).stdout)
            assert len(v["failed"]) == 1 and v["remaining"] == 1, v
            assert "não publicado" in v["failed"][0]["evidence"] or "!=" in v["failed"][0]["evidence"]

            # SEGURANÇA: juiz tentando injetar comando não vira receita
            run(["record-raw", "--cwd", esc, "--session", "s1", "--text-stdin"], stdin="qualquer coisa")
            run(["apply", "--cwd", esc],
                stdin='{"ev":"classify","raw":"r-3","class":"pedido","resumo":"x",'
                      '"substitui":null,"verify":"rm -rf / ; echo pwned"}\n')
            evs2 = ledger.load(os.path.join(esc, ".claude", "intent"))
            inj = [e for e in evs2 if e.get("ev") == "classify" and e.get("raw") == "r-3"][0]
            assert inj["verify"] is None, "comando arbitrário NÃO pode virar receita"
        finally:
            shutil.rmtree(esc, ignore_errors=True)
            shutil.rmtree(bare, ignore_errors=True)

        # RESTRIÇÃO NÃO CONCLUI — sai da lista que cobra veredito e vira contagem.
        # Enquanto ficava junto, o gate exigia veredito de algo que um auditor
        # escreveu ser inauditável por desenho, e a lista nunca esvaziava.
        evs = [
            {"ev": "raw", "id": "r-1", "session": "s1", "text": "faz X"},
            {"ev": "raw", "id": "r-2", "session": "s1", "text": "fala portugues comigo"},
            {"ev": "classify", "raw": "r-1", "id": "p-1", "class": "pedido", "resumo": "faz X"},
            {"ev": "classify", "raw": "r-2", "id": "p-2", "class": "restricao", "resumo": "portugues"},
        ]
        st = ledger.fold(evs)
        assert [e["id"] for e in st["live"]] == ["p-1"], st["live"]
        assert [e["id"] for e in st["standing"]] == ["p-2"], st["standing"]
        assert st["entries"]["p-2"]["status"] == "vivo", "permanente continua viva, só não é cobrada"

        # CONTAGEM DE FUROS: os dois números saem do mesmo log append-only, e log
        # AUSENTE não é zero furo — é ausência de registro (foi assim que o bypass.log
        # ausente virou o elogio "nenhuma resposta furou o teto" com o teto furado).
        cont = tempfile.mkdtemp()
        try:
            velho, novo = 1000, 9000
            os.environ["CLAUDE_CONFIG_DIR"] = cont
            t, n, fontes, marca = ledger.furos_da_regua()
            assert (t, n, fontes) == (0, 0, 0), "sem fonte nenhuma, fontes tem que ser 0"

            bp = os.path.join(cont, "state", "prose-ceiling")
            os.makedirs(bp, exist_ok=True)
            with open(os.path.join(bp, "bypass.log"), "w") as f:
                f.write(json.dumps({"ts": velho, "linhas_prosa": 9}) + "\n")
                f.write(json.dumps({"ts": novo, "linhas_prosa": 12}) + "\n")
            fr = os.path.join(cont, "state", "forma-relato")
            os.makedirs(fr, exist_ok=True)
            with open(os.path.join(fr, "batidas.log"), "w") as f:
                f.write(json.dumps({"ts": novo, "motivo": "julgou", "veredito": "passa"}) + "\n")
                f.write(json.dumps({"ts": novo, "motivo": "julgou", "veredito": "corte a prosa"}) + "\n")
                f.write(json.dumps({"ts": novo, "motivo": "nao e relato", "veredito": None}) + "\n")
            t, n, fontes, marca = ledger.furos_da_regua()
            assert fontes == 2, fontes
            assert t == 3, ("2 furos do teto + 1 reprovação do juiz; 'passa' e "
                            "'nao e relato' não contam — deu %s" % t)
            assert n == 3, n
            os.makedirs(os.path.dirname(marca), exist_ok=True)
            with open(marca, "w") as f:
                f.write(str(velho + 1))
            t, n, fontes, marca = ledger.furos_da_regua()
            assert (t, n) == (3, 2), ("o total não muda com a marca; só o 'desde a "
                                      "última olhada' — deu %s/%s" % (t, n))
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
            shutil.rmtree(cont, ignore_errors=True)

        print("test_ledger: OK")
    finally:
        shutil.rmtree(repo, ignore_errors=True)


if __name__ == "__main__":
    main()
