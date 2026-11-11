#!/usr/bin/env python3
"""cfgjson.py — as leituras e escritas de JSON que o /bootstrap:setup precisa.

POR QUE ISTO EXISTE. O caminho de instalacao (apply.sh, apply-config.sh,
session-sync.sh) fazia tudo por `jq`, e o `jq` nao acompanha o Windows nem o
macOS de fabrica. Resultado medido em maquina limpa: `apply.sh` saia 255 e
`apply-config.sh` saia 1 — o primeiro comando que a pessoa roda depois de
instalar o marketplace morria, e a maquina ficava sem config nenhuma.

O Python ja e dependencia dura de todo o resto do marketplace e le JSON na
biblioteca padrao. Entao a saida foi tirar a dependencia, nao documenta-la: um
caminho SO, aqui, em vez de dois caminhos paralelos que divergem com o tempo.

Cada subcomando abaixo substitui um programa `jq` que existia nos tres scripts,
com a MESMA semantica — inclusive as pegadinhas do jq que importam aqui:

  *   (merge de objeto)  → recursivo, e o lado direito vence
  //  (alternativa)      → cai para o outro lado quando null OU false
  unique                 → ordena E remove duplicata
  del(.x) quando null    → a chave some do arquivo, nao vira null

`test_cfgjson.py` compara a saida de cada subcomando com a do `jq` de verdade
quando ha `jq` na maquina; sem ele, confere o valor esperado direto.
"""
import hashlib
import json
import os
import re
import sys

# CANAIS DE TEXTO EM UTF-8, SEMPRE. No Windows eles nascem na codificação do sistema
# (cp1252) e o JSON que entra por stdin é UTF-8 — o `main()` já reconfigurava a SAÍDA
# por este motivo; a ENTRADA ficou de fora, e é por ela que o settings do usuário passa.
for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _carrega(caminho):
    if caminho == "-":
        return json.load(sys.stdin)
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _escreve(dados):
    # indent=2 como o `jq` sem -c: o settings.json continua legivel a olho nu.
    json.dump(dados, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _merge_fundo(base, novo):
    """O `*` do jq: junta objeto com objeto, descendo; o lado direito vence."""
    saida = dict(base)
    for k, v in novo.items():
        if isinstance(v, dict) and isinstance(saida.get(k), dict):
            saida[k] = _merge_fundo(saida[k], v)
        else:
            saida[k] = v
    return saida


def _alternativa(a, b):
    """O `//` do jq: fica com `a`, salvo quando `a` e null ou false."""
    return b if a is None or a is False else a


def cmd_valida(args):
    """`jq empty <arquivo>` — 0 se o JSON e valido, 1 se nao."""
    try:
        _carrega(args[0])
    except (OSError, ValueError):
        return 1
    return 0


# O QUE DEIXOU DE SER PADRAO. Estas entradas ja viveram no allow dos defaults e
# aprovavam, sem pedir nada, programas que rodam qualquer coisa ou saem para a
# rede (um interprete roda o proprio cliente HTTP; `env`/`xargs`/`timeout` rodam o
# argumento como comando). Sair dos defaults NAO tira a entrada de quem ja recebeu:
# o merge e uniao. Por isso a lista mora aqui — o apply-config avisa da que ainda
# esta na maquina e so remove quando a pessoa pede. A comparacao e pela FORMA
# CANONICA (`_canon`): `Bash(python3:*)`, `Bash(python3 *)` e `Bash(python3*)` sao
# a mesma regra para o Claude Code, e quem escreveu uma delas tem o mesmo risco.
# Entrada com outro escopo (`Bash(python3 -m pytest*)`) nunca e tocada.
RETIRADAS = (
    "Bash(python3*)", "Bash(python*)", "Bash(node*)", "Bash(perl*)", "Bash(bun*)",
    "Bash(env*)", "Bash(printenv*)", "Bash(xargs*)", "Bash(timeout*)",
    "Bash(find*)", "Bash(sed*)", "Bash(awk*)",
    "WebFetch",
    "mcp__plugin_playwright_playwright__browser_evaluate",
    "mcp__plugin_playwright_playwright__browser_run_code",
    "mcp__plugin_playwright_playwright__browser_file_upload",
)

# A regra de PASTA INTEIRA que a primeira versao desta correcao distribuiu:
# `python3 <config>/plugins/cache/pedro-plugins/*` libera todo script de todo plugin
# (inclusive os que executam o comando que recebem). Tem o caminho da maquina, entao
# nao cabe numa lista fixa: casa por forma.
RE_PASTA_INTEIRA = re.compile(r'^Bash\((?:python3?|node) "?[^*"]*/plugins/cache/pedro-plugins/\*\)$')

# Onde o caminho desta maquina entra nas regras dos defaults.
MARCA_DIR = "{{CLAUDE_DIR}}"
MARCA_VERSAO = "{{VERSION}}"
LISTAS = ("allow", "ask", "deny")
LISTA_SCRIPTS = "plugin-scripts.baseline.json"
MKT_CACHE = "pedro-plugins"


def _canon(x):
    """A forma canonica de uma regra, para comparar grafias que valem o mesmo.

    `Bash(python3:*)` (sintaxe antiga), `Bash(python3 *)` e `Bash(python3*)` viram
    `Bash(python3*)`; `WebFetch(*)` vira `WebFetch`. O resto passa como veio.
    """
    if not isinstance(x, str):
        return x
    t = x.strip()
    m = re.fullmatch(r"(\w+)\((.*)\)", t, re.S)
    if not m:
        return t
    ferramenta, interno = m.group(1), m.group(2).strip()
    if ferramenta == "Bash":
        return "Bash(%s)" % re.sub(r"\s*(?::\*|\*)$", "*", interno)
    if interno in ("", "*"):
        return ferramenta
    return t


RETIRADAS_CANON = frozenset(_canon(r) for r in RETIRADAS)


def _e_retirada(x):
    return _canon(x) in RETIRADAS_CANON or bool(isinstance(x, str) and RE_PASTA_INTEIRA.match(x.strip()))


def _lista_de_scripts(caminho_defaults):
    """`plugin-scripts.baseline.json` ao lado dos defaults: {"scripts": [...], "pedem_aprovacao": [...]}."""
    try:
        d = _carrega(os.path.join(os.path.dirname(os.path.abspath(caminho_defaults)), LISTA_SCRIPTS))
    except (OSError, ValueError):
        return {"scripts": [], "pedem_aprovacao": []}
    return {"scripts": [e for e in d.get("scripts") or [] if isinstance(e, dict)],
            "pedem_aprovacao": [e for e in d.get("pedem_aprovacao") or [] if isinstance(e, dict)]}


def _audit():
    # o analisador mora ao lado; o caminho entra explicito porque `python3 -I` nao poe a
    # pasta do script no sys.path. Import preguicoso: so quem gera regra de script paga.
    aqui = os.path.dirname(os.path.abspath(__file__))
    if aqui not in sys.path:
        sys.path.append(aqui)
    import script_audit
    return script_audit


def _chave_versao(nome):
    return tuple(int(n) for n in re.findall(r"\d+", nome)) + (nome,)


def _versao_mais_alta(dir_plugin):
    """A pasta de versao mais alta de um plugin no cache (ignora `.in_use` e arquivos)."""
    try:
        nomes = [n for n in os.listdir(dir_plugin)
                 if not n.startswith(".") and os.path.isdir(os.path.join(dir_plugin, n))]
    except OSError:
        return None
    return max(nomes, key=_chave_versao) if nomes else None


def _regras_de_scripts(claude_dir, lista):
    """As regras de allow POR SCRIPT, para o que esta de fato no cache desta maquina.

    Uma por script e interprete (com o caminho puro e com ele entre aspas), com a
    versao MAIS ALTA instalada no caminho e o curinga so no fim, nos argumentos:
    medido num Claude Code real, um `*` no meio do caminho engole texto, inclusive
    outro script (`python3 <cache>/*/lib/x.py *` aprovou `evil.py ... x.py`). Por
    isso a versao e resolvida aqui, na hora do merge, e nao deixada a um curinga.
    So ganha regra o script que a analise reconfirma como puro na copia instalada.
    """
    audit = _audit()
    cache_fs = os.path.join(claude_dir, "plugins", "cache", MKT_CACHE)
    cache_regra = claude_dir + "/plugins/cache/" + MKT_CACHE
    regras = set()
    for e in lista:
        plugin, script, interp = e.get("plugin"), e.get("script"), e.get("interprete")
        if not (isinstance(plugin, str) and isinstance(script, str) and interp in ("python3", "node")):
            continue
        base = os.path.join(cache_fs, plugin)
        versao = _versao_mais_alta(base)
        if versao is None:
            continue
        arquivo = os.path.join(base, versao, *script.split("/"))
        if not os.path.isfile(arquivo):
            continue
        if audit.classifica_arquivo(arquivo, os.path.join(base, versao))["classe"] != "puro":
            continue
        caminho = "%s/%s/%s/%s" % (cache_regra, plugin, versao, script)
        if any(c in caminho for c in '*"\n\r?'):
            continue
        regras.add("Bash(%s %s *)" % (interp, caminho))
        regras.add('Bash(%s "%s" *)' % (interp, caminho))
    return sorted(regras)


def _regras_de_ask(pedem):
    """Ask para os scripts citados que executam comando: vence um allow largo antigo."""
    return sorted("Bash(*%s/plugins/cache/%s/%s/*/%s*)" % (MARCA_DIR, MKT_CACHE, e["plugin"], e["script"])
                  for e in pedem if isinstance(e.get("plugin"), str) and isinstance(e.get("script"), str))


def _resolve(defaults, claude_dir, caminho_defaults=None):
    """Troca {{CLAUDE_DIR}} nas regras e acrescenta as regras POR SCRIPT desta maquina."""
    perms = defaults.get("permissions")
    if not isinstance(perms, dict):
        return defaults
    saida = dict(defaults)
    saida["permissions"] = dict(perms)
    lista = _lista_de_scripts(caminho_defaults) if caminho_defaults else {"scripts": [], "pedem_aprovacao": []}
    extra = {"allow": _regras_de_scripts(claude_dir, lista["scripts"]),
             "ask": _regras_de_ask(lista["pedem_aprovacao"])}
    for nome in LISTAS:
        if isinstance(perms.get(nome), list) or extra.get(nome):
            base = perms.get(nome) if isinstance(perms.get(nome), list) else []
            resolvido = [x.replace(MARCA_DIR, claude_dir) if isinstance(x, str) else x for x in base]
            resolvido += [x.replace(MARCA_DIR, claude_dir) for x in extra.get(nome, ())]
            saida["permissions"][nome] = list(dict.fromkeys(resolvido))
    return saida


# O CONSENTIMENTO. A marca que o /bootstrap grava depois do "sim" nao e um arquivo
# vazio: guarda o hash (e as linhas) da lista que o usuario viu. A lista e o MOLDE
# das regras — as dos defaults como escritas, e uma regra por script da lista de
# scripts com `{{CLAUDE_DIR}}` e `{{VERSION}}` no lugar do que muda por maquina e por
# atualizacao. Assim a marca vale em qualquer maquina e sobrevive a um plugin que
# subiu de versao, mas NAO sobrevive a um release que acrescenta regra.
def _linhas_do_molde(defaults, lista):
    linhas = set()
    for nome in LISTAS:
        for x in (defaults.get("permissions") or {}).get(nome) or []:
            linhas.add("%s + %s" % (nome, x))
    for e in lista["scripts"]:
        caminho = "%s/plugins/cache/%s/%s/%s/%s" % (MARCA_DIR, MKT_CACHE, e.get("plugin"), MARCA_VERSAO, e.get("script"))
        linhas.add("allow + Bash(%s %s *)" % (e.get("interprete"), caminho))
        linhas.add('allow + Bash(%s "%s" *)' % (e.get("interprete"), caminho))
    for x in _regras_de_ask(lista["pedem_aprovacao"]):
        linhas.add("ask + " + x)
    return sorted(linhas)


def _hash_das_linhas(linhas):
    return hashlib.sha256(("\n".join(linhas) + "\n").encode("utf-8")).hexdigest()


def cmd_consentimento(args):
    """`consentimento <defaults>`: o texto da marca (hash + linhas) para o usuario que disse sim."""
    linhas = _linhas_do_molde(_carrega(args[0]), _lista_de_scripts(args[0]))
    sys.stdout.write("sha256:%s\n" % _hash_das_linhas(linhas))
    for l in linhas:
        sys.stdout.write(l + "\n")
    return 0


def cmd_consent_estado(args):
    """`consent-estado <marca> <defaults>`: ok | ausente | antiga | mudou (+ o que mudou).

    Primeira linha = o estado. Em `mudou`, vem uma linha `+ <regra>` por regra nova
    e `- <regra>` por regra que saiu da lista desde o sim do usuario.
    """
    atuais = _linhas_do_molde(_carrega(args[1]), _lista_de_scripts(args[1]))
    try:
        with open(args[0], encoding="utf-8") as f:
            texto = f.read()
    except OSError:
        print("ausente")
        return 0
    linhas = texto.splitlines()
    cab = linhas[0].strip() if linhas else ""
    guardadas = [l for l in linhas[1:] if l.strip()]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", cab) or cab != "sha256:" + _hash_das_linhas(guardadas):
        # arquivo vazio (a marca das versoes antigas) ou adulterado: nao diz o que foi aprovado
        print("antiga")
        return 0
    if cab == "sha256:" + _hash_das_linhas(atuais):
        print("ok")
        return 0
    print("mudou")
    for l in sorted(set(atuais) - set(guardadas)):
        print("+ " + l)
    for l in sorted(set(guardadas) - set(atuais)):
        print("- " + l)
    return 0


def cmd_prepara_defaults(args):
    """`prepara-defaults <defaults> <claude_dir> <com|sem>`: os defaults prontos para o merge.

    `com` resolve o caminho nas regras; `sem` corta o bloco `permissions` inteiro
    (o consentimento ainda nao foi dado) e deixa o resto valer.
    """
    defaults = _carrega(args[0])
    claude_dir = args[1].rstrip("/\\")
    if args[2] == "sem":
        defaults = dict(defaults)
        defaults.pop("permissions", None)
    else:
        defaults = _resolve(defaults, claude_dir, args[0])
    _escreve(defaults)
    return 0


def cmd_lista_novas(args):
    """`lista-novas <settings> <defaults> <claude_dir>`: o que o merge acrescentaria.

    Uma entrada por linha, `<lista> + <regra>`, ja com o caminho resolvido, e a
    contagem na ultima. Arquivo de settings ausente conta como vazio.
    """
    try:
        atual = _carrega(args[0])
    except OSError:
        atual = {}
    defaults = _resolve(_carrega(args[1]), args[2].rstrip("/\\"), args[1])
    ja = atual.get("permissions") or {}
    novas = {}
    for lista in LISTAS:
        tem = set(ja.get(lista) or [])
        novas[lista] = [x for x in (defaults.get("permissions") or {}).get(lista) or [] if x not in tem]
        for x in novas[lista]:
            print("%s + %s" % (lista, x))
    total = sum(len(v) for v in novas.values())
    print("%d entradas novas (allow %d · ask %d · deny %d)"
          % (total, len(novas["allow"]), len(novas["ask"]), len(novas["deny"])))
    return 0


def cmd_retiradas(args):
    """`retiradas <settings>`: as entradas largas de antes que ainda estao no allow."""
    try:
        atual = _carrega(args[0])
    except OSError:
        return 0
    for x in (atual.get("permissions") or {}).get("allow") or []:
        if _e_retirada(x):
            print(x)
    return 0


def cmd_remove_retiradas(args):
    """`remove-retiradas <settings>`: o settings sem as entradas largas de antes."""
    atual = _carrega(args[0])
    perms = atual.get("permissions")
    if isinstance(perms, dict) and isinstance(perms.get("allow"), list):
        perms["allow"] = [x for x in perms["allow"] if not _e_retirada(x)]
    _escreve(atual)
    return 0


def cmd_merge_settings(args):
    """O merge de settings do apply-config.sh.

    A politica esta escrita no cabecalho daquele script e e repetida aqui de
    proposito, porque quem le este arquivo precisa dela junto:
      env                                   → defaults vencem (merge)
      permissions.allow/ask/deny            → UNIAO (a maquina mantem as dela)
      permissions.defaultMode               → o local, senao o default
      language/theme/autoCompact/outputStyle→ defaults vencem
    """
    atual, defaults = _carrega(args[0]), _carrega(args[1])
    saida = dict(atual)

    saida["env"] = _merge_fundo(atual.get("env") or {}, defaults.get("env") or {})

    perms = dict(atual.get("permissions") or {})
    pd = defaults.get("permissions") or {}
    perms["allow"] = sorted(set((atual.get("permissions") or {}).get("allow") or [])
                            | set(pd.get("allow") or []))
    perms["deny"] = sorted(set((atual.get("permissions") or {}).get("deny") or [])
                           | set(pd.get("deny") or []))
    # `ask` tambem e UNIAO, e a chave so nasce quando alguem a tem (uma maquina
    # sem nenhuma regra de ask nao ganha `"ask": []` de brinde).
    ask = sorted(set((atual.get("permissions") or {}).get("ask") or [])
                 | set(pd.get("ask") or []))
    if ask:
        perms["ask"] = ask
    modo = _alternativa((atual.get("permissions") or {}).get("defaultMode"),
                        pd.get("defaultMode"))
    if modo is None:
        perms.pop("defaultMode", None)
    else:
        perms["defaultMode"] = modo
    saida["permissions"] = perms

    for campo in ("language", "theme", "outputStyle"):
        v = _alternativa(defaults.get(campo), atual.get(campo))
        if v is None:
            saida.pop(campo, None)
        else:
            saida[campo] = v

    # autoCompactEnabled e booleano: `//` trataria `false` como ausente e o
    # default nunca conseguiria desligar. Por isso o teste e contra null.
    ac = defaults.get("autoCompactEnabled")
    ac = atual.get("autoCompactEnabled") if ac is None else ac
    if ac is None:
        saida.pop("autoCompactEnabled", None)
    else:
        saida["autoCompactEnabled"] = ac

    _escreve(saida)
    return 0


def cmd_statusline(args):
    """`.statusLine = {type,command,refreshInterval}` do apply-config.sh."""
    d = _carrega(args[0])
    d["statusLine"] = {"type": "command", "command": args[1], "refreshInterval": 10}
    _escreve(d)
    return 0


def cmd_mkts(args):
    """`.marketplaces[] | .name + "|" + .source` do apply.sh."""
    for mk in _carrega(args[0]).get("marketplaces") or []:
        print("%s|%s" % (mk.get("name", ""), mk.get("source", "")))
    return 0


def cmd_mkt_names(args):
    """`.marketplaces[].name` do apply.sh."""
    for mk in _carrega(args[0]).get("marketplaces") or []:
        print(mk.get("name", ""))
    return 0


def cmd_plugins(args):
    """`.name + "@" + $mkt + "\\t" + (.enabled|tostring)` do apply.sh."""
    for mk in _carrega(args[0]).get("marketplaces") or []:
        for p in mk.get("plugins") or []:
            print("%s@%s\t%s" % (p.get("name", ""), mk.get("name", ""),
                                 "true" if p.get("enabled") else "false"))
    return 0


def cmd_chaves(args):
    """`keys[]` — ORDENADO, que e o que o jq faz, nao a ordem do arquivo."""
    try:
        d = _carrega(args[0])
    except (OSError, ValueError):
        return 1
    for k in sorted(d):
        print(k)
    return 0


def cmd_tem_chave(args):
    """`jq -e '.<chave>'` — 0 quando a chave existe e nao e null/false."""
    try:
        d = _carrega(args[0])
    except (OSError, ValueError):
        return 1
    v = d.get(args[1])
    return 1 if v is None or v is False else 0


COMANDOS = {
    "valida": cmd_valida,
    "merge-settings": cmd_merge_settings,
    "prepara-defaults": cmd_prepara_defaults,
    "lista-novas": cmd_lista_novas,
    "consentimento": cmd_consentimento,
    "consent-estado": cmd_consent_estado,
    "retiradas": cmd_retiradas,
    "remove-retiradas": cmd_remove_retiradas,
    "statusline": cmd_statusline,
    "mkts": cmd_mkts,
    "mkt-names": cmd_mkt_names,
    "plugins": cmd_plugins,
    "chaves": cmd_chaves,
    "tem-chave": cmd_tem_chave,
}


def main(argv):
    if len(argv) < 2 or argv[1] not in COMANDOS:
        print("uso: cfgjson.py <%s> [args]" % "|".join(COMANDOS), file=sys.stderr)
        return 2
    try:
        return COMANDOS[argv[1]](argv[2:])
    except (OSError, ValueError, IndexError, KeyError) as e:
        print("cfgjson: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    sys.exit(main(sys.argv))
