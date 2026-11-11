#!/usr/bin/env python3
"""Suite do sec.py — sem internet, contra respostas REAIS gravadas do OSV e da Aikido.

O erro que importa aqui tem duas direções e as duas são caras:
    verde falso    pacote envenenado passa calado, ou fonte fora do ar vira "tudo certo"
    alarme falso   pacote comum sai como malicioso (o vite 6.4.3 saía, porque o texto
                   da falha dele fala em "site malicioso" — é o atacante, não o pacote)

Os arquivos de pacotes em fixtures/projeto/ foram recortados de lockfiles reais (npm,
pnpm 9, yarn v1, yarn berry, uv, poetry) e as respostas em fixtures/respostas/ foram
gravadas da API do OSV em 2026-10-24. Um servidor local devolve essas respostas, então
o caminho de rede do motor roda inteiro.
"""

import http.server
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import sec  # noqa: E402

FIX = os.path.join(AQUI, "fixtures")
RESP = os.path.join(FIX, "respostas")
FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


class Falso(http.server.BaseHTTPRequestHandler):
    """OSV + dump de Actions + Aikido, servidos das respostas gravadas."""

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        corpo = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.end_headers()
        self.wfile.write(corpo)

    def do_POST(self):
        q = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/v1/querybatch":
            with open(os.path.join(RESP, "querybatch.json")) as fh:
                mapa = json.load(fh)
            res = []
            for c in q["queries"]:
                ids = mapa.get("%s|%s|%s" % (c["package"]["ecosystem"], c["package"]["name"], c["version"]))
                if c["package"]["name"] == "pacote-sumido":  # registro que a base apagou → 404
                    ids = ["GHSA-0000-0000-sumi", "GHSA-35jh-r3h4-6jhm"]
                res.append({"vulns": [{"id": i} for i in ids]} if ids else {})
            return self._json({"results": res})
        return self._json({})

    def do_GET(self):
        if self.path.startswith("/v1/vulns/"):
            f = os.path.join(RESP, "vulns", self.path.rsplit("/", 1)[1] + ".json")
            if os.path.exists(f):
                with open(f, "rb") as fh:
                    return self._json(fh.read())
            return self._json({}, 404)
        if self.path == "/GitHub%20Actions/all.zip":
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.write(os.path.join(RESP, "GHSA-mrrh-fwg8-r2c3.json"), "GHSA-mrrh-fwg8-r2c3.json")
            return self._json(buf.getvalue())
        if self.path == "/malware_predictions.json":  # entrada real da lista da Aikido
            return self._json([{"package_name": "jshelperdependenceny", "version": "99.0.0", "reason": "MALWARE"},
                               {"package_name": "@babel/core", "version": "0.0.1", "reason": "MALWARE"}])
        if self.path == "/malware_pypi.json":
            return self._json([{"package_name": "rich", "version": "*", "reason": "TELEMETRY"}])
        return self._json({}, 404)


def apontar(base, cache):
    sec.OSV_API = sec.OSV_DUMP = sec.AIKIDO = base
    sec.CACHE_DIR = cache


def por_alvo(res):
    return {i["alvo"]: i for i in res["itens"]}


def main():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Falso)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    tmp = tempfile.mkdtemp(prefix="sec-test-")
    projeto = os.path.join(FIX, "projeto")
    try:
        print("leitores (recortes de lockfiles reais)")
        check("package-lock: pula link e workspace, pega aninhado",
              sorted(n for _, n, _ in sec.ler_package_lock(os.path.join(projeto, "package-lock.json"))) ==
              ["@babel/code-frame", "@babel/compat-data", "@babel/core", "event-stream", "jshelperdependenceny", "lodash"])
        check("pnpm 9: linha em branco não fecha a seção packages",
              sec.ler_pnpm_lock(os.path.join(projeto, "pnpm", "pnpm-lock.yaml")) ==
              [("npm", "@adobe/css-tools", "4.4.4"), ("npm", "@alloc/quick-lru", "5.2.0"),
               ("npm", "@asamuzakjp/css-color", "5.1.11"), ("npm", "lodash", "4.17.15")])
        check("yarn v1: nome tirado do cabeçalho, versão do corpo",
              sec.ler_yarn_lock(os.path.join(projeto, "yarn1", "yarn.lock")) ==
              [("npm", "@develar/schema-utils", "2.6.5"), ("npm", "@electron/asar", "3.2.4")])
        check("yarn berry: só @npm:, workspace fica de fora",
              sec.ler_yarn_lock(os.path.join(projeto, "berry", "yarn.lock")) ==
              [("npm", "@aashutoshrathi/word-wrap", "1.2.6"), ("npm", "@actions/core", "1.2.6")])
        check("uv: projeto virtual fica de fora",
              sec.ler_toml_lock(os.path.join(projeto, "py", "uv.lock")) ==
              [("PyPI", "annotated-doc", "0.0.4"), ("PyPI", "PyYAML", "5.3")])
        check("poetry: [[package]] lido",
              sec.ler_toml_lock(os.path.join(projeto, "poetry", "poetry.lock")) == [("PyPI", "anyio", "4.15.1")])
        fixos, soltos = sec.ler_requirements(os.path.join(projeto, "py", "requirements.txt"))
        check("requirements: == com extra e marcador entra; >= e solto viram aviso",
              fixos == [("PyPI", "requests", "2.19.0"), ("PyPI", "rich", "13.0.0")] and soltos == ["flask", "numpy"])
        check("workflow: ação local e docker:// ficam de fora",
              sec.ler_workflow(os.path.join(projeto, ".github", "workflows", "ci.yml")) ==
              [("actions/checkout", "11bd71901bbe5b1630ceea73d27597364c9af683"), ("tj-actions/changed-files", "v45")])
        try:
            sec.ler_pnpm_lock(os.path.join(FIX, "..", "test_sec.py"))
            check("pnpm de versão desconhecida é recusado", False)
        except sec.SecError:
            check("pnpm de versão desconhecida é recusado", True)

        print("versões")
        check("1.0rc1 < 1.0", sec.cmp_ver("1.0rc1", "1.0") < 0)
        check("4.17.15 < 4.17.21", sec.cmp_ver("4.17.15", "4.17.21") < 0)
        faixa = {"ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "46.0.1"}]}]}
        check("v45 (a última 45.x) cai antes de 46.0.1", sec.afeta(faixa, "45", pad=10 ** 9))
        faixa4 = {"ranges": [{"type": "SEMVER", "events": [{"introduced": "0"}, {"fixed": "4.2.1"}]}]}
        check("v4 (a última 4.x) NÃO cai antes de 4.2.1", not sec.afeta(faixa4, "4", pad=10 ** 9))
        ult = {"ranges": [{"type": "SEMVER", "events": [{"introduced": "1.0.0"}, {"last_affected": "1.2.0"}]}]}
        check("last_affected inclui a própria versão", sec.afeta(ult, "1.2.0") and not sec.afeta(ult, "1.2.1"))

        print("malicioso por sinal estrutural, nunca pela palavra")
        with open(os.path.join(RESP, "vulns", "GHSA-mh6f-8j2x-4483.json")) as fh:
            check("event-stream 3.3.6 (CWE-506) é malicioso", sec._malicioso(json.load(fh)))
        with open(os.path.join(RESP, "vulns", "GHSA-9jrq-w75r-8gcw.json")) as fh:
            check("falha do vite que fala em 'site malicioso' NÃO é", not sec._malicioso(json.load(fh)))

        print("varredura do projeto de exemplo")
        apontar(base, os.path.join(tmp, "cache"))
        res = sec.varrer(projeto, maquina=False)
        it = por_alvo(res)
        check("nenhuma fonte falhou", res["falhas"] == {})
        check("event-stream 3.3.6 → malicioso", it.get("npm event-stream 3.3.6", {}).get("nivel") == "malicioso")
        check("Aikido: jshelperdependenceny → malicioso",
              it.get("npm jshelperdependenceny 99.0.0", {}).get("nivel") == "malicioso")
        check("Aikido por versão: @babel/core 7.29.7 não casa com a entrada 0.0.1",
              "npm @babel/core 7.29.7" not in it)
        check("Aikido '*' = toda versão: rich → cadeia (telemetria)",
              it.get("PyPI rich 13.0.0", {}).get("nivel") == "cadeia")
        lo = it.get("npm lodash 4.17.15", {})
        check("lodash → falha, subir para 4.18.0 (a maior das correções)",
              lo.get("nivel") == "falha" and lo.get("conserto") == "subir para 4.18.0")
        check("lodash aparece uma vez só, com os dois lockfiles em 'onde'",
              lo.get("onde") == "package-lock.json, pnpm/pnpm-lock.yaml")
        check("PyYAML 5.3 (uv.lock) → falha", it.get("PyPI PyYAML 5.3", {}).get("nivel") == "falha")
        check("MCP com versão fixa → conferido: inspector 0.14.0 subir para 0.16.6",
              it.get("npm @modelcontextprotocol/inspector 0.14.0", {}).get("conserto") == "subir para 0.16.6")
        check("MCP sem versão → cadeia", it.get("MCP solto (@exemplo/mcp-server)", {}).get("nivel") == "cadeia")
        # GHSA-mrrh é o comprometimento de março/2025 (CVE-2025-30066, CWE-506): malicioso, não só falha
        check("tj-actions@v45 → malicioso pelo dump do OSV (a tag móvel apontava para o commit envenenado)", any(
            i["alvo"] == "ação tj-actions/changed-files@v45" and i["nivel"] == "malicioso" for i in res["itens"]))
        check("tj-actions@v45 → também cadeia (tag móvel)", any(
            i["alvo"] == "ação tj-actions/changed-files@v45" and i["nivel"] == "cadeia" for i in res["itens"]))
        check("checkout fixado por SHA → nada", not any("actions/checkout" in i["alvo"] for i in res["itens"]))
        check("requirements com pacote solto → cadeia", it.get("py/requirements.txt", {}).get("nivel") == "cadeia")
        check("tem lockfile → sem aviso de lockfile ausente", "package.json" not in it)
        check("ordem: malicioso antes de falha antes de cadeia",
              [i["nivel"] for i in res["itens"]] == sorted((i["nivel"] for i in res["itens"]), key=sec.NIVEIS.index))

        print("caminhos do relatório saem sempre com '/'")
        # No Windows `normpath` devolve `pnpm\pnpm-lock.yaml` e o relatório (e a chave dos
        # itens) saía com barra invertida; a suíte falhava só lá. Aqui o sistema é
        # ENCENADO — `normpath` do ntpath e `os.sep` de lá — para o defeito aparecer
        # também no macOS e no Linux, onde a esteira roda primeiro.
        import ntpath

        class _CaminhoNt:   # o `os.path` daqui, com o `normpath` do Windows
            normpath = staticmethod(ntpath.normpath)

            def __getattr__(self, nome):
                return getattr(os.path, nome)

        class _OsNt:        # o `os` do sec, com o separador do Windows
            sep = "\\"
            path = _CaminhoNt()

            def __getattr__(self, nome):
                return getattr(os, nome)

        os_real = sec.os
        sec.os = _OsNt()
        try:
            pacs, acoes, avisos, _mcp = sec.inventario_projeto(projeto)
        finally:
            sec.os = os_real
        ondes = [p[3] for p in pacs] + [a[2] for a in acoes] + [v["onde"] for v in avisos]
        check("há caminhos a conferir (a encenação mediu alguma coisa)", len(ondes) > 3)
        check("nenhum 'onde' leva barra invertida", not any("\\" in o for o in ondes))
        check("o lockfile de subpasta sai como pnpm/pnpm-lock.yaml", "pnpm/pnpm-lock.yaml" in ondes)

        print("relatório")
        html = sec.render_html(res, "2026-10-24 12:00")
        check("marcador de cópia presente", "<!-- sec-corrigir v1 -->" in html)
        check("um checkbox por item", html.count("type='checkbox'") == len(res["itens"]))
        check("malicioso e falha nascem marcados, cadeia não",
              html.count(" checked>") == sum(1 for i in res["itens"] if i["nivel"] in ("malicioso", "falha")))
        check("sem aviso de NÃO VERIFICADO quando tudo respondeu", "NÃO VERIFICADO" not in html)

        print("fonte fora do ar nunca vira verde")
        apontar("http://127.0.0.1:9", os.path.join(tmp, "cache-vazio"))
        caido = sec.varrer(projeto, maquina=False)
        check("OSV e Aikido acusados", "OSV" in caido["falhas"] and "Aikido Intel (npm)" in caido["falhas"])
        check("NÃO VERIFICADO no relatório", "NÃO VERIFICADO" in sec.render_html(caido, "x"))
        out = os.path.join(tmp, "r.html")
        check("código de saída 2", sec.main(["report", "--projeto", projeto, "--sem-maquina", "--out", out]) == 2
              and os.path.exists(out))
        apontar(base, os.path.join(tmp, "cache"))

        print("projeto sem lockfile")
        sem = os.path.join(tmp, "sem-lock")
        os.makedirs(sem)
        with open(os.path.join(sem, "package.json"), "w") as fh:
            fh.write("{}")
        check("package.json sozinho → cadeia",
              por_alvo(sec.varrer(sem, maquina=False)).get("package.json", {}).get("nivel") == "cadeia")

        print("exemplo de teste não é instalado")
        com_fix = os.path.join(tmp, "com-fixtures")
        shutil.copytree(projeto, os.path.join(com_fix, "tests", "fixtures", "p"))
        shutil.copytree(projeto, os.path.join(com_fix, "testdata", "p"))
        check("pasta fixtures/ e testdata/ ficam fora da varredura",
              sec.varrer(com_fix, maquina=False)["itens"] == [])

        print("registro sumido (404) vale só para o pacote dele")
        sumido = os.path.join(tmp, "sumido")
        os.makedirs(sumido)
        with open(os.path.join(sumido, "package-lock.json"), "w") as fh:
            json.dump({"lockfileVersion": 3, "packages": {"": {}, "node_modules/pacote-sumido": {"version": "1.0.0"}}}, fh)
        r404 = sec.varrer(sumido, maquina=False)
        ps = por_alvo(r404).get("npm pacote-sumido 1.0.0", {})
        check("OSV segue verificado", "OSV" not in r404["falhas"])
        check("o pacote sai como falha, contando os 2 registros",
              ps.get("nivel") == "falha" and ps.get("motivo", "").startswith("2 falha"))
        check("e pede conferência à mão com o id que sumiu", "GHSA-0000-0000-sumi" in ps.get("conserto", ""))

        print("comando que estoura o tempo não derruba a varredura")
        real_run = sec.subprocess.run

        def lento(*a, **k):
            raise sec.subprocess.TimeoutExpired(a[0], k.get("timeout"))
        sec.subprocess.run = lento
        try:
            f = sec.Fontes()
            out_node = sec.checar_node(f)
            check("node que não responde → nada acusado e NÃO VERIFICADO",
                  out_node == [] and "node --version" in f.falhas())
        finally:
            sec.subprocess.run = real_run

        print("quarentena de versão nova")
        real_rodar = sec._rodar

        def fingir(respostas):
            def _r(fontes, cmd, timeout=60, cwd=None):
                return respostas.get(" ".join(cmd))
            return _r
        casos = [
            ({"pnpm --version": "10.33.2\n", "pnpm config get minimumReleaseAge": "undefined\n"}, True,
             "pnpm 10 sem valor → acusa"),
            ({"pnpm --version": "10.33.2\n", "pnpm config get minimumReleaseAge": "1440\n"}, False,
             "pnpm 10 com 1440 → nada"),
            ({"pnpm --version": "11.1.0\n", "pnpm config get minimumReleaseAge": "undefined\n"}, False,
             "pnpm 11 sem valor → padrão de 1 dia, nada"),
            ({"pnpm --version": "11.1.0\n", "pnpm config get minimumReleaseAge": "0\n"}, True,
             "pnpm 11 desligado à mão → acusa"),
        ]
        try:
            for resp, acusa, rotulo in casos:
                sec._rodar = fingir(resp)
                check(rotulo, bool(sec.checar_quarentena_pnpm(sec.Fontes(), "maquina", tmp)) == acusa)
            sec._rodar = fingir({"pnpm --version": "10.33.2\n", "pnpm config get minimumReleaseAge": "undefined\n"})
            pr = sec.checar_quarentena_pnpm(sec.Fontes(), "projeto", tmp)
            check("no projeto, o conserto aponta o pnpm-workspace.yaml",
                  pr and "pnpm-workspace.yaml" in pr[0]["conserto"])
            mq = sec.checar_quarentena_pnpm(sec.Fontes(), "maquina", tmp)
            check("na máquina (pnpm 10), o conserto é o --global testado",
                  mq and mq[0]["conserto"] == "pnpm config set minimumReleaseAge 1440 --global")
            sec._rodar = fingir({"npm --version": "10.9.8\n"})
            n10 = sec.checar_quarentena_npm(sec.Fontes())
            check("npm 10.9.8 → acusa e manda atualizar", n10 and "npm@latest" in n10[0]["conserto"])
            casa = os.path.join(tmp, "casa-npm")
            os.makedirs(casa)
            antigo_npm = os.environ.get("HOME"), os.environ.get("USERPROFILE")
            os.environ["HOME"] = os.environ["USERPROFILE"] = casa
            try:
                sec._rodar = fingir({"npm --version": "11.10.0\n"})
                check("npm 11.10 sem ~/.npmrc → acusa", bool(sec.checar_quarentena_npm(sec.Fontes())))
                with open(os.path.join(casa, ".npmrc"), "w") as fh:
                    fh.write("registry=https://registry.npmjs.org/\nmin-release-age=1\n")
                check("npm 11.10 com min-release-age=1 → nada", sec.checar_quarentena_npm(sec.Fontes()) == [])
            finally:
                for k, v in zip(("HOME", "USERPROFILE"), antigo_npm):
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        finally:
            sec._rodar = real_rodar

        print("plugins da máquina (HOME de mentira)")
        home = os.path.join(tmp, "home")
        pl = os.path.join(home, ".claude", "plugins")
        inline = os.path.join(pl, "cache", "terceiro", "inline", "1.0")
        oficial = os.path.join(pl, "cache", "oficial", "of", "1.0")
        so_skill = os.path.join(pl, "cache", "terceiro", "skill", "1.0")
        for d, manif in ((inline, {"name": "inline", "hooks": {"SessionStart": []}}),
                         (oficial, {"name": "of"}), (so_skill, {"name": "skill"})):
            os.makedirs(os.path.join(d, ".claude-plugin"))
            with open(os.path.join(d, ".claude-plugin", "plugin.json"), "w") as fh:
                json.dump(manif, fh)
        os.makedirs(os.path.join(oficial, "hooks"))
        open(os.path.join(oficial, "hooks", "hooks.json"), "w").close()
        with open(os.path.join(pl, "installed_plugins.json"), "w") as fh:
            json.dump({"version": 2, "plugins": {
                "inline@terceiro": [{"installPath": inline}], "of@oficial": [{"installPath": oficial}],
                "skill@terceiro": [{"installPath": so_skill}]}}, fh)
        with open(os.path.join(pl, "known_marketplaces.json"), "w") as fh:
            json.dump({"terceiro": {"source": {"source": "git", "url": "https://example.com/t.git"}},
                       "oficial": {"source": {"source": "github", "repo": sec.MARKETPLACE_OFICIAL}}}, fh)
        with open(os.path.join(pl, "blocklist.json"), "w") as fh:
            json.dump({"plugins": [{"plugin": "skill@terceiro", "reason": "security", "text": "teste"}]}, fh)
        antigo = os.environ.get("HOME"), os.environ.get("USERPROFILE")
        os.environ["HOME"] = os.environ["USERPROFILE"] = home
        try:
            pi = por_alvo({"itens": sec.checar_plugins()})
        finally:
            for k, v in zip(("HOME", "USERPROFILE"), antigo):
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        check("terceiro com hook declarado no plugin.json → cadeia",
              pi.get("plugin inline@terceiro", {}).get("nivel") == "cadeia")
        check("oficial com hook → nada", "plugin of@oficial" not in pi)
        check("na lista de bloqueio de segurança → malicioso",
              pi.get("plugin skill@terceiro", {}).get("nivel") == "malicioso")
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d falha(s)" % len(FAILS) if FAILS else "\ntudo verde")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
