#!/usr/bin/env python3
"""A cadeia que leva o código escrito aqui até a máquina de quem usa — conferida.

POR QUE EXISTE. Em 2026-08-09 o dono passou uma sessão inteira revisando, testando e
aprovando a versão 0.4.0 do `gauntlet` no repositório. O que rodava na máquina dele
era a 0.3.2, instalada dias antes: a trava que ele acreditava estar de pé não tinha
nenhum dos consertos, e **nada no repositório dizia isso**. A descoberta foi por
acaso, cavando o cache do cliente à mão.

O código atravessa quatro estações até virar comportamento, e cada fronteira entre
elas some em silêncio quando alguém esquece um passo:

    plugins/<nome>/          o que foi escrito
      → marketplace.json     o que é PUBLICADO (quem não entra, ninguém instala)
      → bootstrap/config/manifest.json   o que a receita MANDA instalar
      → ~/.claude/plugins/   o que a máquina RODA de verdade

Este programa compara as quatro. Ele não instala nada e não escreve em lugar nenhum:
o estrago de um instalador automático errado é maior que o do aviso que ele evita.

Dois modos, porque as perguntas têm públicos diferentes:

    --repo      só o que se decide com o repositório na mão. É o que roda no commit.
    --maquina   compara com o que está instalado AQUI. É o que roda no arranque da
                sessão, e é o único que responde "estou rodando código velho?".

Sem argumento roda os dois. Sai 1 quando há desvio; 0 quando está tudo alinhado, e
0 também quando falta material para julgar (sem git, sem instalação) — guarda que
acusa por causa da própria infra é pior que guarda nenhum.

    python3 scripts/cadeia_check.py
    python3 scripts/cadeia_check.py --maquina --json
"""

import argparse
import json
import os
import sys

CATALOGO = ".claude-plugin/marketplace.json"
RECEITA = "plugins/bootstrap/config/manifest.json"
NOME_DO_MERCADO = "pedro-plugins"


def _le(caminho):
    """O JSON, ou None. Arquivo ausente não é exceção: é 'não dá para julgar'."""
    try:
        with open(caminho, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _casa_do_cliente():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(
        os.path.expanduser("~"), ".claude")


def plugins_no_disco(raiz):
    """As pastas de plugin que existem no repositório, com a versão de cada uma."""
    base = os.path.join(raiz, "plugins")
    if not os.path.isdir(base):
        return {}
    fora = {}
    for nome in sorted(os.listdir(base)):
        manifesto = os.path.join(base, nome, ".claude-plugin", "plugin.json")
        if not os.path.isfile(manifesto):
            continue
        dado = _le(manifesto) or {}
        fora[nome] = dado.get("version")
    return fora


def publicados(raiz):
    """O que o catálogo distribui: nome → versão anunciada."""
    dado = _le(os.path.join(raiz, CATALOGO))
    if dado is None:
        return None
    return {p.get("name"): p.get("version")
            for p in (dado.get("plugins") or []) if isinstance(p, dict) and p.get("name")}


def na_receita(raiz):
    """O que o bootstrap manda instalar: nome → ligado de fábrica."""
    dado = _le(os.path.join(raiz, RECEITA))
    if dado is None:
        return None
    fora = {}
    for mercado in dado.get("marketplaces") or []:
        if mercado.get("name") != NOME_DO_MERCADO:
            continue
        for p in mercado.get("plugins") or []:
            if isinstance(p, dict) and p.get("name"):
                fora[p["name"]] = bool(p.get("enabled"))
    return fora


def instalados():
    """O que a máquina roda: nome → versão, lida do caminho do cache.

    A versão vem do `installPath` porque é ele que aponta para os arquivos que o
    harness realmente carrega. O número escrito noutro lugar diria o que deveria
    estar instalado; este diz o que está.
    """
    dado = _le(os.path.join(_casa_do_cliente(), "plugins", "installed_plugins.json"))
    if dado is None:
        return None
    fora = {}

    def desce(o):
        if isinstance(o, dict):
            for chave, valor in o.items():
                if chave.endswith("@" + NOME_DO_MERCADO) and isinstance(valor, list):
                    for item in valor:
                        caminho = (item or {}).get("installPath") if isinstance(item, dict) else None
                        if caminho:
                            fora[chave.split("@")[0]] = os.path.basename(caminho.rstrip("/"))
                else:
                    desce(valor)
        elif isinstance(o, list):
            for item in o:
                desce(item)

    desce(dado)
    return fora


def skills_de(raiz, nome):
    """As skills que um plugin carrega."""
    base = os.path.join(raiz, "plugins", nome, "skills")
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base)
                  if os.path.isfile(os.path.join(base, d, "SKILL.md")))


# ─────────────────────────────────────────────────────────────────────────────

def desvios_do_repo(raiz):
    """As fronteiras que se conferem sem sair do repositório."""
    achados = []
    disco = plugins_no_disco(raiz)
    cat = publicados(raiz)
    rec = na_receita(raiz)
    if not disco or cat is None:
        return achados

    # 1 · escrito e nunca publicado. As skills entram no recado porque são elas que
    # o dono sente falta: "desenvolvi e não aparece" é sempre isto.
    for nome in sorted(set(disco) - set(cat)):
        skills = skills_de(raiz, nome)
        detalhe = (" — leva %d skill(s): %s" % (len(skills), " · ".join(skills))
                   if skills else " — sem skill")
        achados.append((
            "escrito e fora do catálogo",
            "%s existe em plugins/ e o %s não o publica%s" % (nome, CATALOGO, detalhe),
            "acrescente a entrada de `%s` em %s" % (nome, CATALOGO)))

    # 2 · publicado e sem pasta: o catálogo aponta para o que não existe.
    for nome in sorted(set(cat) - set(disco)):
        achados.append((
            "publicado e sem código",
            "%s está no catálogo e não há plugins/%s/ no disco" % (nome, nome),
            "ou a pasta voltou, ou a entrada sai do catálogo"))

    # 3 · publicado e fora da receita: nunca chega em máquina nenhuma. O
    # `conformance.py:check_catalogo` já cobra isso, mas só quando alguém roda o
    # setup do bootstrap — e aí o commit já passou faz tempo.
    if rec is not None:
        for nome in sorted(set(cat) - set(rec)):
            achados.append((
                "publicado e fora da receita",
                "%s está no catálogo e o %s não o declara" % (nome, RECEITA),
                "declare `%s` em %s" % (nome, RECEITA)))

    # 4 · a versão anunciada tem que ser a escrita. É o espelho que o gate de commit
    # já cobra; repetir aqui é o que faz este programa valer sozinho, fora do gate.
    for nome, versao in sorted(disco.items()):
        if nome in cat and cat[nome] != versao:
            achados.append((
                "catálogo desalinhado",
                "%s: plugin.json diz %s e o catálogo anuncia %s" % (nome, versao, cat[nome]),
                "espelhe a mesma version nos dois arquivos"))
    return achados


def desvios_da_maquina(raiz):
    """A fronteira que só a máquina responde: o que está rodando de verdade."""
    achados = []
    disco = plugins_no_disco(raiz)
    viva = instalados()
    if not disco or not viva:
        return achados
    for nome, versao in sorted(disco.items()):
        if nome not in viva or not versao:
            continue
        if viva[nome] != versao:
            achados.append((
                "código velho rodando",
                "%s: a máquina roda %s e o repositório está em %s"
                % (nome, viva[nome], versao),
                "claude plugin update %s@%s — e reinicie a sessão, senão o cache "
                "velho segue valendo" % (nome, NOME_DO_MERCADO)))
    return achados


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--project-root", default=".")
    p.add_argument("--repo", action="store_true", help="só o que se confere no repositório")
    p.add_argument("--maquina", action="store_true", help="só o que está instalado aqui")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quieto", action="store_true",
                   help="não imprime nada quando está tudo alinhado (para hook)")
    args = p.parse_args(argv)

    raiz = os.path.abspath(args.project_root)
    so_um = args.repo or args.maquina
    achados = []
    if args.repo or not so_um:
        achados += desvios_do_repo(raiz)
    if args.maquina or not so_um:
        achados += desvios_da_maquina(raiz)

    if args.json:
        print(json.dumps([{"tipo": t, "o_que": o, "conserto": c}
                          for t, o, c in achados], ensure_ascii=False, indent=1))
        return 1 if achados else 0

    if not achados:
        if not args.quieto:
            print("cadeia alinhada: o que está escrito é o que se publica, "
                  "o que se publica é o que se instala, e é o que roda.")
        return 0

    print("⚠️  %d desvio(s) na cadeia de entrega:" % len(achados))
    for tipo, o_que, conserto in achados:
        print("\n  [%s] %s" % (tipo, o_que))
        print("   → %s" % conserto)
    return 1


if __name__ == "__main__":
    sys.exit(main())
