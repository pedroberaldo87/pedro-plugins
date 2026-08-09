#!/usr/bin/env python3
"""Suíte do cadeia_check — cada caso reproduz um jeito real de a entrega quebrar.

O primeiro deles é o que motivou o programa: em 2026-08-09 a máquina rodou o
`gauntlet` 0.3.2 durante uma sessão inteira de revisão da 0.4.0, e nada acusou.

    python3 scripts/test_cadeia_check.py
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cadeia_check as cc  # noqa: E402

FALHAS = []


def check(rotulo, cond):
    print(("  ok   " if cond else "  FAIL ") + rotulo)
    if not cond:
        FALHAS.append(rotulo)


def escreve(caminho, dado):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(dado, fh, ensure_ascii=False, indent=1)


def monta_repo(raiz, plugins=(("alfa", "1.0.0"), ("beta", "2.1.0"))):
    """Um repositório saudável: o disco, o catálogo e a receita concordando."""
    for nome, versao in plugins:
        escreve(os.path.join(raiz, "plugins", nome, ".claude-plugin", "plugin.json"),
                {"name": nome, "version": versao})
        cam = os.path.join(raiz, "plugins", nome, "skills", nome, "SKILL.md")
        os.makedirs(os.path.dirname(cam), exist_ok=True)
        open(cam, "w", encoding="utf-8").write("---\nname: %s\n---\n" % nome)
    escreve(os.path.join(raiz, cc.CATALOGO),
            {"plugins": [{"name": n, "version": v} for n, v in plugins]})
    escreve(os.path.join(raiz, cc.RECEITA),
            {"marketplaces": [{"name": cc.NOME_DO_MERCADO,
                               "plugins": [{"name": n, "enabled": True}
                                           for n, _ in plugins]}]})
    return raiz


def monta_maquina(casa, instalados):
    """A instalação do cliente: o caminho do cache é quem diz a versão viva."""
    escreve(os.path.join(casa, "plugins", "installed_plugins.json"),
            {"repos": {"%s@%s" % (n, cc.NOME_DO_MERCADO): [
                {"installPath": "/qualquer/cache/%s/%s" % (n, v)}]
                for n, v in instalados.items()}})
    os.environ["CLAUDE_CONFIG_DIR"] = casa


def tmp():
    return tempfile.mkdtemp(prefix="cadeia-")


print("O CHÃO — a cadeia saudável não acusa nada")
d = tmp()
monta_repo(d)
monta_maquina(os.path.join(d, "casa"), {"alfa": "1.0.0", "beta": "2.1.0"})
check("repo alinhado não tem desvio", cc.desvios_do_repo(d) == [])
check("máquina em dia não tem desvio", cc.desvios_da_maquina(d) == [])
shutil.rmtree(d)

print()
print("O DEFEITO DE ORIGEM — a máquina roda código velho e nada avisa")
d = tmp()
monta_repo(d)
monta_maquina(os.path.join(d, "casa"), {"alfa": "0.9.0", "beta": "2.1.0"})
achados = cc.desvios_da_maquina(d)
check("a versão velha é acusada", any(t == "código velho rodando" for t, _, _ in achados))
check("e o recado nomeia as DUAS versões, a viva e a do repositório",
      any("0.9.0" in o and "1.0.0" in o for _, o, _ in achados))
check("e ensina que só o update não basta — tem que reiniciar",
      any("reinicie" in c for _, _, c in achados))
check("o plugin em dia não entra na lista", len(achados) == 1)
shutil.rmtree(d)

print()
print("ESCRITO E NUNCA PUBLICADO — o plugin que ninguém consegue instalar")
d = tmp()
monta_repo(d)
escreve(os.path.join(d, "plugins", "gama", ".claude-plugin", "plugin.json"),
        {"name": "gama", "version": "0.1.0"})
cam = os.path.join(d, "plugins", "gama", "skills", "gama", "SKILL.md")
os.makedirs(os.path.dirname(cam), exist_ok=True)
open(cam, "w", encoding="utf-8").write("---\nname: gama\n---\n")
achados = cc.desvios_do_repo(d)
check("o plugin fora do catálogo é acusado",
      any(t == "escrito e fora do catálogo" for t, _, _ in achados))
# É a skill que o dono sente falta: "desenvolvi e não aparece em lugar nenhum".
check("e o recado diz QUANTAS skills ficam de fora, com o nome delas",
      any("1 skill(s): gama" in o for _, o, _ in achados))
shutil.rmtree(d)

print()
print("PUBLICADO E FORA DA RECEITA — entra no catálogo e não chega em máquina nenhuma")
d = tmp()
monta_repo(d)
receita = os.path.join(d, cc.RECEITA)
dado = json.load(open(receita, encoding="utf-8"))
dado["marketplaces"][0]["plugins"] = [p for p in dado["marketplaces"][0]["plugins"]
                                      if p["name"] != "beta"]
escreve(receita, dado)
check("o publicado que a receita não declara é acusado",
      any(t == "publicado e fora da receita" for t, _, _ in cc.desvios_do_repo(d)))
shutil.rmtree(d)

print()
print("O CATÁLOGO DESALINHADO — anuncia uma versão e o código está noutra")
d = tmp()
monta_repo(d)
cat = os.path.join(d, cc.CATALOGO)
dado = json.load(open(cat, encoding="utf-8"))
dado["plugins"][0]["version"] = "0.0.1"
escreve(cat, dado)
check("o espelho quebrado entre plugin.json e catálogo é acusado",
      any(t == "catálogo desalinhado" for t, _, _ in cc.desvios_do_repo(d)))
shutil.rmtree(d)

print()
print("PUBLICADO E SEM CÓDIGO — o catálogo apontando para pasta que não existe")
d = tmp()
monta_repo(d)
shutil.rmtree(os.path.join(d, "plugins", "beta"))
check("a entrada órfã do catálogo é acusada",
      any(t == "publicado e sem código" for t, _, _ in cc.desvios_do_repo(d)))
shutil.rmtree(d)

print()
print("FAIL-OPEN — sem material para julgar, ele não acusa ninguém")
d = tmp()
check("repositório vazio não gera desvio", cc.desvios_do_repo(d) == [])
monta_repo(d)
os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(d, "casa-que-nao-existe")
check("sem instalação no disco, a máquina não é julgada", cc.desvios_da_maquina(d) == [])
shutil.rmtree(d)

print()
if FALHAS:
    print("cadeia_check: %d falha(s)" % len(FALHAS))
    for f in FALHAS:
        print("  - %s" % f)
    sys.exit(1)
print("cadeia_check: tudo verde")
