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
                       stdin=None if entrada is not None else subprocess.DEVNULL)
    return r.stdout, r.returncode


def roda_jq(programa, *args, arquivo=None, cru=False):
    cmd = [JQ] + (["-r"] if cru else []) + list(args) + [programa]
    if arquivo:
        cmd.append(arquivo)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       stdin=subprocess.DEVNULL)
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
    with open(ruim, "w") as f:
        f.write('{"a": ')
    check("JSON valido → 0", roda("valida", bom)[1] == 0)
    check("JSON quebrado → 1", roda("valida", ruim)[1] == 1)
    check("arquivo inexistente → 1", roda("valida", os.path.join(t, "nao-existe"))[1] == 1)

print("\n%d ok · %d FAIL%s" % (casos - falhas, falhas,
                               "" if JQ else "   (sem jq: comparacao direta com o jq foi pulada)"))
sys.exit(1 if falhas else 0)
