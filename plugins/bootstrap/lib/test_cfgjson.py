#!/usr/bin/env python3
"""test_cfgjson.py — o cfgjson.py faz o MESMO que o jq que ele substituiu.

A prova forte nao e "o resultado parece certo": e o resultado ser IGUAL ao do
`jq` rodando o programa original. Onde ha `jq` na maquina (macOS e Linux de
quem desenvolve, e os tres runners da esteira), cada caso roda dos dois lados e
compara. Onde nao ha — Windows de fabrica, que e justamente a maquina que este
codigo existe para atender — os mesmos casos conferem contra o valor esperado
escrito a mao, entao a suite nunca fica verde por ausencia de ferramenta.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(AQUI, "cfgjson.py")
JQ = shutil.which("jq")

falhas = 0
casos = 0


def check(nome, ok, detalhe=""):
    global falhas, casos
    casos += 1
    if ok:
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


def roda(*args, entrada=None):
    r = subprocess.run([sys.executable, CFG] + list(args), capture_output=True,
                       text=True, encoding="utf-8", input=entrada,
                       stdin=None if entrada is not None else subprocess.DEVNULL,
                       start_new_session=True)
    return r.stdout, r.returncode


def roda_jq(programa, *args, arquivo=None, cru=False):
    cmd = [JQ] + (["-r"] if cru else []) + list(args) + [programa]
    if arquivo:
        cmd.append(arquivo)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       stdin=subprocess.DEVNULL, start_new_session=True)
    return r.stdout, r.returncode


PROGRAMA_MERGE = '''
  . as $cur
  | ($d[0]) as $def
  | .env = (($cur.env // {}) * ($def.env // {}))
  | .permissions = ($cur.permissions // {})
  | .permissions.allow = (((($cur.permissions.allow) // []) + (($def.permissions.allow) // [])) | unique)
  | .permissions.deny  = (((($cur.permissions.deny)  // []) + (($def.permissions.deny)  // [])) | unique)
  | .permissions.defaultMode = ($cur.permissions.defaultMode // $def.permissions.defaultMode)
  | .language = ($def.language // $cur.language)
  | .theme = ($def.theme // $cur.theme)
  | .autoCompactEnabled = (if ($def.autoCompactEnabled != null) then $def.autoCompactEnabled else $cur.autoCompactEnabled end)
  | .outputStyle = ($def.outputStyle // $cur.outputStyle)
  | .permissions |= (if .defaultMode == null then del(.defaultMode) else . end)
  | (if .language == null then del(.language) else . end)
  | (if .theme == null then del(.theme) else . end)
  | (if .autoCompactEnabled == null then del(.autoCompactEnabled) else . end)
  | (if .outputStyle == null then del(.outputStyle) else . end)
'''


def escreve(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False)
    return caminho


print("── merge de settings: o caso real de uma maquina ja usada ──")
with tempfile.TemporaryDirectory() as t:
    atual = escreve(os.path.join(t, "atual.json"), {
        "env": {"MEU_ENV": "1", "CLAUDE_CONTEXT_THRESHOLD": "50"},
        "permissions": {"allow": ["Bash(git status)", "Bash(ls)"], "deny": ["Bash(rm -rf /)"]},
        "autoCompactEnabled": True,
        "enabledPlugins": {"visual@pedro-plugins": True},
    })
    defaults = escreve(os.path.join(t, "def.json"), {
        "env": {"CLAUDE_CONTEXT_THRESHOLD": "80", "AGENT_TEAMS": "1"},
        "permissions": {"allow": ["Bash(ls)", "Bash(cat)"], "deny": []},
        "language": "Brazilian Portuguese",
        "theme": "auto",
        "autoCompactEnabled": False,
        "outputStyle": "Clean Style",
    })
    saida, rc = roda("merge-settings", atual, defaults)
    got = json.loads(saida)

    check("o default vence no env (threshold 50 → 80)", got["env"]["CLAUDE_CONTEXT_THRESHOLD"] == "80", got["env"])
    check("o env proprio da maquina sobrevive", got["env"].get("MEU_ENV") == "1", got["env"])
    check("permissoes sao UNIAO, nao substituicao",
          got["permissions"]["allow"] == ["Bash(cat)", "Bash(git status)", "Bash(ls)"],
          got["permissions"]["allow"])
    check("o default consegue DESLIGAR o autoCompact (false nao e 'ausente')",
          got["autoCompactEnabled"] is False, got.get("autoCompactEnabled"))
    check("chave que o bootstrap nao gerencia fica intacta",
          got.get("enabledPlugins") == {"visual@pedro-plugins": True}, got.get("enabledPlugins"))

    if JQ:
        esperado_txt, _ = roda_jq(PROGRAMA_MERGE, "--slurpfile", "d", defaults, arquivo=atual)
        check("IGUAL ao jq rodando o programa original", got == json.loads(esperado_txt),
              "python=%s\njq=%s" % (saida[:200], esperado_txt[:200]))
    else:
        print("  skip comparacao com jq (nao ha jq nesta maquina — o esperado acima ja cobre)")

print("── campo que nao existe dos dois lados nao vira null no arquivo ──")
with tempfile.TemporaryDirectory() as t:
    atual = escreve(os.path.join(t, "a.json"), {})
    defaults = escreve(os.path.join(t, "d.json"), {"env": {}})
    got = json.loads(roda("merge-settings", atual, defaults)[0])
    check("language ausente nos dois → a chave nem aparece", "language" not in got, got)
    check("defaultMode ausente nos dois → a chave nem aparece",
          "defaultMode" not in got.get("permissions", {}), got.get("permissions"))

print("── as leituras do apply.sh ──")
with tempfile.TemporaryDirectory() as t:
    man = escreve(os.path.join(t, "manifest.json"), {"marketplaces": [
        {"name": "pedro-plugins", "source": "git@github.com:x/y.git",
         "plugins": [{"name": "visual", "enabled": True},
                     {"name": "graphify-guard", "enabled": False}]},
        {"name": "outro", "source": "https://z", "plugins": []},
    ]})
    known = escreve(os.path.join(t, "known.json"), {"outro": {}, "pedro-plugins": {}})

    saida, _ = roda("mkts", man)
    check("mkts devolve nome|source", saida.split("\n")[0] == "pedro-plugins|git@github.com:x/y.git", saida)
    saida, _ = roda("plugins", man)
    check("plugins devolve ref e o enabled como texto",
          saida.split("\n")[1] == "graphify-guard@pedro-plugins\tfalse", repr(saida))
    saida, _ = roda("mkt-names", man)
    check("mkt-names devolve um nome por linha", saida.split() == ["pedro-plugins", "outro"], saida)
    saida, _ = roda("chaves", known)
    check("chaves sai ORDENADO, como o keys[] do jq", saida.split() == ["outro", "pedro-plugins"], saida)

    if JQ:
        for nome, prog, sub in (("mkts", '.marketplaces[] | .name + "|" + .source', "mkts"),
                                ("mkt-names", '.marketplaces[].name', "mkt-names"),
                                ("plugins", '.marketplaces[] | .name as $mkt | .plugins[] | .name + "@" + $mkt + "\\t" + (.enabled | tostring)', "plugins")):
            esperado, _ = roda_jq(prog, arquivo=man, cru=True)
            got, _ = roda(sub, man)
            check("%s: identico ao jq" % nome, got == esperado, "py=%r jq=%r" % (got, esperado))
        esperado, _ = roda_jq('keys[]', arquivo=known, cru=True)
        got, _ = roda("chaves", known)
        check("chaves: identico ao jq", got == esperado, "py=%r jq=%r" % (got, esperado))

print("── tem-chave: o teste do session-sync.sh ──")
with tempfile.TemporaryDirectory() as t:
    k = escreve(os.path.join(t, "k.json"), {"pedro-plugins": {"a": 1}, "vazio": None, "falso": False})
    check("chave presente → 0", roda("tem-chave", k, "pedro-plugins")[1] == 0)
    check("chave ausente → 1", roda("tem-chave", k, "nao-existe")[1] == 1)
    check("chave null → 1 (como o -e do jq)", roda("tem-chave", k, "vazio")[1] == 1)
    check("chave false → 1 (a pegadinha do -e)", roda("tem-chave", k, "falso")[1] == 1)
    if JQ:
        for chave in ("pedro-plugins", "nao-existe", "vazio", "falso"):
            _, rc_jq = roda_jq('."%s"' % chave, "-e", arquivo=k)
            _, rc_py = roda("tem-chave", k, chave)
            check("tem-chave %s: mesmo veredito do jq -e" % chave,
                  (rc_py == 0) == (rc_jq == 0), "py=%s jq=%s" % (rc_py, rc_jq))

print("── valida: JSON quebrado nao passa ──")
with tempfile.TemporaryDirectory() as t:
    bom = escreve(os.path.join(t, "bom.json"), {"a": 1})
    ruim = os.path.join(t, "ruim.json")
    with open(ruim, "w", encoding="utf-8") as f:
        f.write('{"a": ')
    check("JSON valido → 0", roda("valida", bom)[1] == 0)
    check("JSON quebrado → 1", roda("valida", ruim)[1] == 1)
    check("arquivo inexistente → 1", roda("valida", os.path.join(t, "nao-existe"))[1] == 1)

print("── permissoes com caminho resolvido, lista do que entra e retiradas ──")
with tempfile.TemporaryDirectory() as t:
    defaults = escreve(os.path.join(t, "d.json"), {
        "permissions": {
            "allow": ["Bash(ls*)", "Bash(python3 {{CLAUDE_DIR}}/plugins/cache/pedro-plugins/*)"],
            "ask": ["Edit(/{{CLAUDE_DIR}}/plugins/cache/**)"],
            "deny": ["Bash(dd*)"]},
        "language": "Brazilian Portuguese"})
    cd = os.path.join(t, "casa", ".claude")

    saida, rc = roda("prepara-defaults", defaults, cd, "com")
    got = json.loads(saida)
    check("prepara-defaults troca {{CLAUDE_DIR}} pelo caminho da maquina",
          got["permissions"]["allow"][1] == "Bash(python3 %s/plugins/cache/pedro-plugins/*)" % cd,
          got["permissions"]["allow"])
    check("prepara-defaults resolve o caminho do Edit com a barra dupla",
          got["permissions"]["ask"] == ["Edit(/%s/plugins/cache/**)" % cd], got["permissions"]["ask"])
    check("prepara-defaults nao deixa placeholder em lugar nenhum", "{{" not in saida, saida)
    saida, rc = roda("prepara-defaults", defaults, cd, "sem")
    got = json.loads(saida)
    check("prepara-defaults 'sem' corta o bloco permissions e guarda o resto",
          "permissions" not in got and got["language"] == "Brazilian Portuguese", got)

    atual = escreve(os.path.join(t, "a.json"), {
        "permissions": {"allow": ["Bash(ls*)"], "ask": ["Bash(rm *)"]}})
    saida, rc = roda("lista-novas", atual, defaults, cd)
    linhas = saida.strip().split("\n")
    check("lista-novas nao repete o que a maquina ja tem",
          not any(l == "allow + Bash(ls*)" for l in linhas), linhas)
    check("lista-novas mostra o interprete com o caminho resolvido",
          "allow + Bash(python3 %s/plugins/cache/pedro-plugins/*)" % cd in linhas, linhas)
    check("lista-novas mostra o ask e o deny novos",
          "ask + Edit(/%s/plugins/cache/**)" % cd in linhas and "deny + Bash(dd*)" in linhas, linhas)
    check("lista-novas fecha com a contagem", linhas[-1].startswith("3 entradas novas (allow 1 · ask 1 · deny 1)"), linhas[-1])
    saida, rc = roda("lista-novas", os.path.join(t, "nao-existe.json"), defaults, cd)
    check("lista-novas sem settings trata como vazio", "allow + Bash(ls*)" in saida.split("\n"), saida)

    amplo = escreve(os.path.join(t, "amplo.json"), {"permissions": {"allow": [
        "Bash(python3*)", "Bash(node*)", "WebFetch", "Bash(ls*)", "Bash(meu-script*)",
        "mcp__plugin_playwright_playwright__browser_run_code"]}})
    saida, rc = roda("retiradas", amplo)
    check("retiradas lista as largas e ignora as do usuario",
          saida.split() == ["Bash(python3*)", "Bash(node*)", "WebFetch",
                            "mcp__plugin_playwright_playwright__browser_run_code"], saida)
    saida, rc = roda("remove-retiradas", amplo)
    got = json.loads(saida)
    check("remove-retiradas deixa so o que o usuario escreveu",
          got["permissions"]["allow"] == ["Bash(ls*)", "Bash(meu-script*)"], got)

    # o ask tambem e UNIAO no merge, e a chave so nasce quando alguem a tem
    saida, rc = roda("merge-settings", atual, defaults)
    got = json.loads(saida)
    check("merge-settings une o ask", got["permissions"]["ask"] == ["Bash(rm *)", "Edit(/{{CLAUDE_DIR}}/plugins/cache/**)"], got["permissions"])
    vazio = escreve(os.path.join(t, "v.json"), {})
    sem_ask = escreve(os.path.join(t, "sa.json"), {"permissions": {"allow": ["x"]}})
    saida, rc = roda("merge-settings", vazio, sem_ask)
    check("sem ask dos dois lados a chave nem aparece", "ask" not in json.loads(saida)["permissions"], saida)

print("── retiradas: as grafias que o Claude Code trata como a mesma regra ──")
with tempfile.TemporaryDirectory() as t:
    grafias = escreve(os.path.join(t, "g.json"), {"permissions": {"allow": [
        "Bash(python3:*)", "Bash(python3 *)", "Bash(node *)", "Bash(env:*)", "Bash(find *)",
        "WebFetch(*)", "Bash(python3 -m pytest*)", "Bash(python3 meu.py)", "Bash(ls*)",
        "Bash(python3.12 *)"]}})
    saida, rc = roda("retiradas", grafias)
    check("python3:* · python3 * · node * · env:* · find * · WebFetch(*) sao retiradas",
          saida.split("\n")[:-1] == ["Bash(python3:*)", "Bash(python3 *)", "Bash(node *)", "Bash(env:*)",
                                      "Bash(find *)", "WebFetch(*)"], saida)
    saida, rc = roda("remove-retiradas", grafias)
    check("remove-retiradas deixa as entradas de escopo menor",
          json.loads(saida)["permissions"]["allow"] == [
              "Bash(python3 -m pytest*)", "Bash(python3 meu.py)", "Bash(ls*)", "Bash(python3.12 *)"], saida)
    pasta = escreve(os.path.join(t, "p.json"), {"permissions": {"allow": [
        "Bash(python3 /h/.claude/plugins/cache/pedro-plugins/*)",
        "Bash(node \"/h/.claude/plugins/cache/pedro-plugins/*)",
        "Bash(python3 /h/.claude/plugins/cache/pedro-plugins/p/1.0/lib/x.py *)"]}})
    saida, rc = roda("retiradas", pasta)
    check("a regra de pasta inteira da primeira versao e retirada; a de UM script nao",
          saida.split("\n")[:-1] == ["Bash(python3 /h/.claude/plugins/cache/pedro-plugins/*)",
                                      "Bash(node \"/h/.claude/plugins/cache/pedro-plugins/*)"], saida)

print("── regras por script: so o puro, so a versao mais alta, curinga so no fim ──")
with tempfile.TemporaryDirectory() as t:
    cd = os.path.join(t, "casa", ".claude")
    cache = os.path.join(cd, "plugins", "cache", "pedro-plugins")

    def pluginfile(plugin, versao, rel, texto):
        cam = os.path.join(cache, plugin, versao, *rel.split("/"))
        os.makedirs(os.path.dirname(cam), exist_ok=True)
        with open(cam, "w", encoding="utf-8") as f:
            f.write(texto)

    pluginfile("p", "1.9.0", "lib/puro.py", "print(1)\n")
    pluginfile("p", "1.10.0", "lib/puro.py", "print(1)\n")
    pluginfile("p", "1.10.0", "lib/roda.py", "import subprocess\nsubprocess.run(['bash','-c','x'])\n")
    pluginfile("p", "1.10.0", "lib/virou.py", "import os\nos.system('ls')\n")   # a lista diz puro, o cache diz outra coisa
    pluginfile("p", "1.10.0", "lib/novo.py", "print(2)\n")                      # nao esta na lista
    pluginfile("q", "2.0.0", "app/run.mjs", "console.log(1)\n")
    os.makedirs(os.path.join(cache, "p", ".in_use"), exist_ok=True)
    escreve(os.path.join(t, "plugin-scripts.baseline.json"), {
        "scripts": [
            {"plugin": "p", "script": "lib/puro.py", "interprete": "python3"},
            {"plugin": "p", "script": "lib/virou.py", "interprete": "python3"},
            {"plugin": "p", "script": "lib/nao-existe.py", "interprete": "python3"},
            {"plugin": "q", "script": "app/run.mjs", "interprete": "node"},
            {"plugin": "ausente", "script": "lib/x.py", "interprete": "python3"}],
        "pedem_aprovacao": [{"plugin": "p", "script": "lib/roda.py"}]})
    defaults = escreve(os.path.join(t, "d.json"), {"permissions": {"allow": ["Bash(ls*)"], "ask": [], "deny": []}})
    saida, rc = roda("prepara-defaults", defaults, cd, "com")
    got = json.loads(saida)["permissions"]
    esperado = sorted([
        "Bash(ls*)",
        "Bash(python3 %s/plugins/cache/pedro-plugins/p/1.10.0/lib/puro.py *)" % cd,
        "Bash(python3 \"%s/plugins/cache/pedro-plugins/p/1.10.0/lib/puro.py\" *)" % cd,
        "Bash(node %s/plugins/cache/pedro-plugins/q/2.0.0/app/run.mjs *)" % cd,
        "Bash(node \"%s/plugins/cache/pedro-plugins/q/2.0.0/app/run.mjs\" *)" % cd])
    check("uma regra por script (pura e entre aspas), na versao mais alta (1.10 > 1.9)",
          sorted(got["allow"]) == esperado, got["allow"])
    check("script que a lista diz puro mas o cache mostra executando (virou.py) nao ganha regra",
          not any("virou.py" in x for x in got["allow"]))
    check("o executor da lista de pedem_aprovacao ganha ask, nao allow",
          got["ask"] == ["Bash(*%s/plugins/cache/pedro-plugins/p/*/lib/roda.py*)" % cd]
          and not any("roda.py" in x for x in got["allow"]), got)
    check("nenhum curinga no meio do caminho de um allow de script",
          all(x.count("*") == 1 and x.endswith(" *)") for x in got["allow"] if "plugins/cache" in x), got["allow"])
    saida, rc = roda("lista-novas", os.path.join(t, "nao-existe.json"), defaults, cd)
    check("lista-novas mostra as mesmas regras por script",
          "allow + Bash(python3 %s/plugins/cache/pedro-plugins/p/1.10.0/lib/puro.py *)" % cd in saida.split("\n"), saida)
    saida, rc = roda("prepara-defaults", defaults, cd, "sem")
    check("sem consentimento o bloco de permissoes inteiro some, regras por script inclusas",
          "permissions" not in json.loads(saida), saida)

print("── consentimento: a marca guarda o hash da lista que o usuario viu ──")
with tempfile.TemporaryDirectory() as t:
    escreve(os.path.join(t, "plugin-scripts.baseline.json"), {
        "scripts": [{"plugin": "p", "script": "lib/a.py", "interprete": "python3"}],
        "pedem_aprovacao": [{"plugin": "p", "script": "lib/b.py"}]})
    defaults = escreve(os.path.join(t, "d.json"), {"permissions": {"allow": ["Bash(ls*)"], "ask": [], "deny": ["Bash(dd*)"]}})
    marca = os.path.join(t, "ok")
    saida, rc = roda("consentimento", defaults)
    linhas = saida.strip().split("\n")
    check("a marca tem o hash na 1a linha e o molde (com {{CLAUDE_DIR}} e {{VERSION}}) nas demais",
          linhas[0].startswith("sha256:") and len(linhas[0]) == 71
          and "allow + Bash(python3 {{CLAUDE_DIR}}/plugins/cache/pedro-plugins/p/{{VERSION}}/lib/a.py *)" in linhas
          and "ask + Bash(*{{CLAUDE_DIR}}/plugins/cache/pedro-plugins/p/*/lib/b.py*)" in linhas, linhas)
    check("o molde e igual em duas rodadas", roda("consentimento", defaults)[0] == saida)
    with open(marca, "w", encoding="utf-8") as f:
        f.write(saida)
    check("marca gravada: ok", roda("consent-estado", marca, defaults)[0].strip() == "ok")
    check("sem arquivo: ausente", roda("consent-estado", os.path.join(t, "nao"), defaults)[0].strip() == "ausente")
    with open(os.path.join(t, "vazia"), "w", encoding="utf-8"):
        pass
    check("arquivo vazio (a marca das versoes antigas): antiga", roda("consent-estado", os.path.join(t, "vazia"), defaults)[0].strip() == "antiga")
    with open(marca, "a", encoding="utf-8") as f:
        f.write("allow + Bash(curl*)\n")
    check("linhas adulteradas (hash nao bate): antiga", roda("consent-estado", marca, defaults)[0].strip() == "antiga")
    with open(marca, "w", encoding="utf-8") as f:
        f.write(saida)
    # o release acrescenta uma regra e tira outra
    defaults2 = escreve(os.path.join(t, "d2.json"), {"permissions": {"allow": ["Bash(ls*)", "Bash(novo*)"], "ask": [], "deny": []}})
    os.replace(os.path.join(t, "plugin-scripts.baseline.json"), os.path.join(t, "plugin-scripts.baseline.json.bak"))
    escreve(os.path.join(t, "plugin-scripts.baseline.json"), {
        "scripts": [{"plugin": "p", "script": "lib/a.py", "interprete": "python3"}],
        "pedem_aprovacao": [{"plugin": "p", "script": "lib/b.py"}]})
    saida, rc = roda("consent-estado", marca, defaults2)
    linhas = saida.strip().split("\n")
    check("defaults que mudaram: mudou, com o que entrou (+) e o que saiu (-)",
          linhas[0] == "mudou" and "+ allow + Bash(novo*)" in linhas and "- deny + Bash(dd*)" in linhas, linhas)
    # script novo na lista de liberados tambem invalida o sim
    escreve(os.path.join(t, "plugin-scripts.baseline.json"), {
        "scripts": [{"plugin": "p", "script": "lib/a.py", "interprete": "python3"},
                    {"plugin": "p", "script": "lib/c.py", "interprete": "python3"}],
        "pedem_aprovacao": [{"plugin": "p", "script": "lib/b.py"}]})
    saida, rc = roda("consent-estado", marca, defaults)
    check("script novo na lista de liberados invalida o sim anterior",
          saida.split("\n")[0] == "mudou" and any("lib/c.py" in l for l in saida.split("\n")), saida)

print("\n%d ok · %d FAIL%s" % (casos - falhas, falhas,
                               "" if JQ else "   (sem jq: comparacao direta com o jq foi pulada)"))
sys.exit(1 if falhas else 0)
