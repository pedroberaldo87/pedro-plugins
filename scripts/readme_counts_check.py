#!/usr/bin/env python3
"""readme_counts_check.py — reprova número de contagem defasado no README.

O README é a vitrine do marketplace e afirma quantidade: quantos plugins o catálogo
tem, quantos o `bootstrap` liga de fábrica, quantos hooks precisam de `jq`, quantos
plugins registram hook e quantos registros isso dá. Todo esse número é DERIVÁVEL do
repositório — e nenhum deles era conferido, então o README envelhecia calado enquanto
plugin novo entrava. Este script é o cobrador: extrai cada número afirmado, recalcula
do repositório e reprova quando divergem.

Uso:
    python3 scripts/readme_counts_check.py            # confere, exit 1 se divergir
    python3 scripts/readme_counts_check.py --json

Afirmação que o padrão não acha também reprova: gate que não consegue medir tem que
dizer que não mediu (Artigo 4 da constituição), nunca ficar verde por omissão.

Fail-open só para falha de infraestrutura (README ausente, `hook_contract.py` que não
roda): a afirmação vira "não medida" no relatório e não derruba o commit.
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")


# ── os números reais, cada um derivado da sua fonte ───────────────────────────

def _catalogo():
    """Quantos plugins o marketplace distribui (a fonte da verdade é o catálogo)."""
    with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"), encoding="utf-8") as f:
        return len(json.load(f)["plugins"])


def _manifest_liga_desliga():
    """(ligados, desligados) na receita do bootstrap para o próprio marketplace."""
    caminho = os.path.join(ROOT, "plugins", "bootstrap", "config", "manifest.json")
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    for mk in dados.get("marketplaces", []):
        if mk.get("name") == "pedro-plugins":
            ps = mk.get("plugins", [])
            ligados = sum(1 for p in ps if p.get("enabled"))
            return ligados, len(ps) - ligados
    raise LookupError("manifest.json não declara o marketplace pedro-plugins")


def _manifest_desligados_nomes():
    """Os NOMES desligados na receita do bootstrap — a contagem certa com nome errado
    manda o instalador ligar o plugin errado, e o número sozinho não pega isso."""
    caminho = os.path.join(ROOT, "plugins", "bootstrap", "config", "manifest.json")
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    for mk in dados.get("marketplaces", []):
        if mk.get("name") == "pedro-plugins":
            return sorted(p["name"] for p in mk.get("plugins", []) if not p.get("enabled"))
    raise LookupError("manifest.json não declara o marketplace pedro-plugins")


def _hooks_com_jq():
    """Mesma conta do comando publicado no README: hooks .sh que citam jq.

    Fora da conta, como em `scripts/test_sem_jq.sh`: `test_*` (suíte, não hook) e
    TODA biblioteca de `_shared/` — a cópia em `plugins/*/hooks/` é vendoring do
    mesmo arquivo, não um hook a mais. A lista de nomes é derivada de `_shared/`
    para que vendorar uma biblioteca nova não mude o número.
    """
    jq = re.compile(r"\bjq\b")
    vendorados = {a for a in os.listdir(os.path.join(ROOT, "_shared"))
                  if a.endswith(".sh")}
    n = 0
    base = os.path.join(ROOT, "plugins")
    for plugin in sorted(os.listdir(base)):
        pasta = os.path.join(base, plugin, "hooks")
        if not os.path.isdir(pasta):
            continue
        for arq in sorted(os.listdir(pasta)):
            if not arq.endswith(".sh"):
                continue
            if arq.startswith("test_") or arq in vendorados:
                continue
            with open(os.path.join(pasta, arq), encoding="utf-8", errors="replace") as f:
                if jq.search(f.read()):
                    n += 1
    return n


def _hooks_que_decidem():
    """Hooks da classe B — os que leem pelo payload o campo que DECIDE.

    Mesma regra de `scripts/test_sem_jq.sh` (LISTA_B): linha fora de comentário
    que cita o leitor (`jq`, `hj_campo`, `hj_eh_falso`) e, na mesma linha, um dos
    três campos de decisão. Fora da conta, como lá: `test_*` e as bibliotecas
    vendoradas de `_shared/`.
    """
    decide = re.compile(r"(jq|JQ|hj_campo|hj_campo_ou|hj_eh_falso)"
                        r"[^#]*(tool_input\.command|session_id|stop_hook_active)")
    vendorados = {a for a in os.listdir(os.path.join(ROOT, "_shared"))
                  if a.endswith(".sh")}
    n = 0
    base = os.path.join(ROOT, "plugins")
    for plugin in sorted(os.listdir(base)):
        pasta = os.path.join(base, plugin, "hooks")
        if not os.path.isdir(pasta):
            continue
        for arq in sorted(os.listdir(pasta)):
            if not arq.endswith(".sh"):
                continue
            if arq.startswith("test_") or arq in vendorados:
                continue
            with open(os.path.join(pasta, arq), encoding="utf-8", errors="replace") as f:
                if any(decide.search(ln) for ln in f if not ln.lstrip().startswith("#")):
                    n += 1
    return n


def _plugins_com_hooks():
    """Plugins que registram hook = os que têm hooks/hooks.json (nunca na raiz)."""
    base = os.path.join(ROOT, "plugins")
    return sum(1 for p in os.listdir(base)
               if os.path.isfile(os.path.join(base, p, "hooks", "hooks.json")))


def _registros_de_hook():
    """Total de registros, medido pelo mesmo script que o README cita."""
    hc = os.path.join(ROOT, "scripts", "hook_contract.py")
    saida = subprocess.run([sys.executable, hc, "--json"], cwd=ROOT,
                           capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL, start_new_session=True).stdout
    return json.loads(saida)["entries"]


# ── as afirmações do README, cada uma ancorada no seu padrão ──────────────────
#
# A âncora é o TEXTO ao redor, nunca o número da linha: linha se desloca a cada
# parágrafo novo e o gate passaria a medir outra frase.

AFIRMACOES = [
    {
        "id": "catalogo",
        "onde": "subtítulo do topo",
        "padrao": r"\*\*(\d+) plugins · Markdown",
        "real": lambda: (_catalogo(),),
        "conserto": "conte com: python3 -c \"import json;print(len(json.load(open('.claude-plugin/marketplace.json'))['plugins']))\"",
    },
    {
        "id": "liga-desliga",
        "onde": "resultado do /bootstrap:setup",
        "padrao": r"\*\*(\d+) plugins ligados \+ (\d+) desligados? de fábrica\*\*",
        "real": _manifest_liga_desliga,
        "conserto": "a receita é plugins/bootstrap/config/manifest.json (campo enabled)",
    },
    {
        "id": "hooks-jq",
        "onde": "tabela de dependência externa",
        "padrao": r"\|\s*(\d+) hooks — `grep -rl",
        "real": lambda: (_hooks_com_jq(),),
        "conserto": "conte com: grep -rl '\\bjq\\b' plugins/*/hooks/*.sh"
                    " | grep -v -e /test_ $(ls _shared/*.sh | sed -E 's#.*/#-e /#')"
                    " | wc -l",
    },
    {
        "id": "hooks-decisao",
        "onde": "tabela de dependência externa (a célula do jq)",
        "padrao": r"os (\d+) hooks que decidem",
        "real": lambda: (_hooks_que_decidem(),),
        "conserto": "conte com: bash scripts/test_sem_jq.sh (linha 'classe B')",
    },
    {
        "id": "hooks-plugins",
        "onde": "abertura de 'Hooks automáticos'",
        "padrao": r"(\d+) plugins registram hooks que disparam sem slash command",
        "real": lambda: (_plugins_com_hooks(),),
        "conserto": "conte com: ls -d plugins/*/hooks/hooks.json | wc -l",
    },
    {
        "id": "hooks-registros",
        "onde": "abertura de 'Hooks automáticos'",
        "padrao": r"(\d+) registros no total",
        "real": lambda: (_registros_de_hook(),),
        "conserto": "conte com: python3 scripts/hook_contract.py",
    },
]


# As duas passagens que LISTAM os desligados pelo nome. O grupo 1 é o trecho onde
# os nomes aparecem; dele saem os identificadores entre crases que existem no catálogo.
NOMES_DESLIGADOS = [
    {
        "id": "desligados-nomes-setup",
        "onde": "resultado do /bootstrap:setup",
        "padrao": r"desligados? de fábrica\*\*\s*\n\(([^)]*)\)",
    },
    {
        "id": "desligados-nomes-plugins",
        "onde": "abertura de 'Plugins'",
        "padrao": r"desligados? de fábrica\*\* na receita do `bootstrap`[^:]*:(.*?)Ligar:",
    },
]


def _confere_nomes(texto, achados, nao_medidas):
    try:
        reais = _manifest_desligados_nomes()
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json"),
                  encoding="utf-8") as f:
            catalogo = {p["name"] for p in json.load(f)["plugins"]}
    except Exception as e:                          # infra quebrada não derruba commit
        nao_medidas.append("desligados-nomes — não medido (%s)" % e)
        return

    for af in NOMES_DESLIGADOS:
        m = re.search(af["padrao"], texto, re.DOTALL)
        if not m:
            achados.append({
                "id": af["id"], "onde": af["onde"], "linha": 0,
                "afirmado": None, "real": reais,
                "msg": "a passagem que lista os plugins desligados sumiu do README (ou "
                       "foi reescrita): o padrão não casa mais.",
                "conserto": "os nomes reais são: %s" % ", ".join(reais),
            })
            continue
        afirmados = sorted(n for n in re.findall(r"`([a-z0-9-]+)`", m.group(1))
                           if n in catalogo)
        if afirmados != reais:
            linha = texto[:m.start()].count("\n") + 1
            achados.append({
                "id": af["id"], "onde": af["onde"], "linha": linha,
                "afirmado": afirmados, "real": reais,
                "msg": "README lista %s como desligados, o manifest desliga %s"
                       % (", ".join(afirmados) or "(nenhum)", ", ".join(reais)),
                "conserto": "a receita é plugins/bootstrap/config/manifest.json"
                            " (campo enabled)",
            })


def confere():
    """Devolve (achados, nao_medidas). Achado = afirmação divergente ou sumida."""
    achados, nao_medidas = [], []
    try:
        with open(README, encoding="utf-8") as f:
            texto = f.read()
    except OSError as e:
        return achados, ["README.md ilegível (%s)" % e]

    linhas = texto.splitlines()

    for af in AFIRMACOES:
        try:
            reais = af["real"]()
        except Exception as e:                      # infra quebrada não derruba commit
            nao_medidas.append("%s — não medido (%s)" % (af["id"], e))
            continue

        m = re.search(af["padrao"], texto)
        if not m:
            achados.append({
                "id": af["id"], "onde": af["onde"], "linha": 0,
                "afirmado": None, "real": list(reais),
                "msg": "afirmação sumiu do README (ou foi reescrita): o padrão não casa "
                       "mais. Reescreva o padrão em scripts/readme_counts_check.py ou "
                       "devolva o número ao texto.",
                "conserto": af["conserto"],
            })
            continue

        afirmados = tuple(int(g) for g in m.groups())
        if afirmados != tuple(reais):
            linha = texto[:m.start()].count("\n") + 1
            achados.append({
                "id": af["id"], "onde": af["onde"], "linha": linha,
                "afirmado": list(afirmados), "real": list(reais),
                "msg": "README afirma %s, o repositório tem %s"
                       % (" + ".join(map(str, afirmados)), " + ".join(map(str, reais))),
                "conserto": af["conserto"],
                "trecho": linhas[linha - 1].strip()[:100],
            })

    _confere_nomes(texto, achados, nao_medidas)

    return achados, nao_medidas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    achados, nao_medidas = confere()

    if args.json:
        print(json.dumps({"achados": achados, "nao_medidas": nao_medidas},
                         ensure_ascii=False, indent=2))
        return 1 if achados else 0

    for nm in nao_medidas:
        print("⚪ %s" % nm)

    if not achados:
        print("README em dia — %d afirmação(ões) de contagem conferida(s)."
              % (len(AFIRMACOES) + len(NOMES_DESLIGADOS) - len(nao_medidas)))
        return 0

    print("README DEFASADO — %d afirmação(ões) de contagem divergem do repositório:"
          % len(achados))
    for a in achados:
        alvo = "README.md:%d" % a["linha"] if a["linha"] else "README.md"
        print("\n  %s (%s)\n    %s" % (alvo, a["onde"], a["msg"]))
        if a.get("trecho"):
            print("    │ %s" % a["trecho"])
        print("    → %s" % a["conserto"])
    return 1


if __name__ == "__main__":
    sys.exit(main())
