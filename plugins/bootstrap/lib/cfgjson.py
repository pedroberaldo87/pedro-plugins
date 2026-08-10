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
import json
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


def cmd_merge_settings(args):
    """O merge de settings do apply-config.sh.

    A politica esta escrita no cabecalho daquele script e e repetida aqui de
    proposito, porque quem le este arquivo precisa dela junto:
      env                                   → defaults vencem (merge)
      permissions.allow/deny                → UNIAO (a maquina mantem as dela)
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
