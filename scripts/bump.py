#!/usr/bin/env python3
"""bump.py — subir a versão de um plugin é UM gesto, não três arquivos.

Por que existe (2026-08-15). Quatro corridas do /sprint morreram na mesma porta: o
autor sobe a versão em `plugins/<nome>/.claude-plugin/plugin.json`, espelha em
`.claude-plugin/marketplace.json`, esquece a tabela que `architecture.md` (na casa da doc)
publica — e a esteira fica vermelha para todo mundo. Nenhuma delas foi desatenção
isolada: o terceiro arquivo não parece parte do bump, e lembrar dele é justamente o
que falha sob carga.

    python3 scripts/bump.py project-skills           # patch  (0.22.76 → 0.22.77)
    python3 scripts/bump.py project-skills --minor   # minor  (0.22.76 → 0.23.0)
    python3 scripts/bump.py project-skills --major
    python3 scripts/bump.py project-skills --para 1.0.0

Quem confere continua sendo a esteira: `scripts/test_doc_catalogo_plugins.py` compara
a tabela com o disco, e o portão de commit barra bump sem espelho.
"""
import argparse
import json
import os
import re
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))


def _le(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def proxima(versao, parte):
    n = [int(x) for x in versao.split(".")]
    while len(n) < 3:
        n.append(0)
    if parte == "major":
        return "%d.0.0" % (n[0] + 1)
    if parte == "minor":
        return "%d.%d.0" % (n[0], n[1] + 1)
    return "%d.%d.%d" % (n[0], n[1], n[2] + 1)


def _tranca(segundos=60):
    """Serializa o bump: dois plugins diferentes na MESMA onda reescrevem os mesmos
    dois arquivos compartilhados (o catálogo e a tabela da doc). Sem tranca, quem
    escreve por último lê o arquivo de antes do vizinho e apaga o bump dele — o gate
    de commit barra a onda inteira, e o motivo aparece como 'esqueceram o bump'.
    """
    alvo = os.path.join(RAIZ, ".claude-plugin", ".bump.lock")
    espera = 0.0
    while True:
        try:
            fd = os.open(alvo, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return alvo
        except FileExistsError:
            # tranca órfã (processo morto no meio) não trava ninguém para sempre
            try:
                if time.time() - os.path.getmtime(alvo) > segundos:
                    os.remove(alvo)
                    continue
            except OSError:
                continue
            if espera > segundos:
                print("a tranca do bump não liberou em %ds — seguindo sem ela" % segundos)
                return None
            time.sleep(0.2)
            espera += 0.2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plugin")
    ap.add_argument("--major", action="store_true")
    ap.add_argument("--minor", action="store_true")
    ap.add_argument("--para", help="versão literal, em vez de incrementar")
    a = ap.parse_args()

    manifesto = os.path.join(RAIZ, "plugins", a.plugin, ".claude-plugin", "plugin.json")
    if not os.path.exists(manifesto):
        print("plugin desconhecido: %s (não achei %s)" % (a.plugin, manifesto))
        return 1
    lock = _tranca()
    try:
        return _bump(manifesto, a)
    finally:
        if lock:
            try:
                os.remove(lock)
            except OSError:
                pass


def _bump(manifesto, a):
    atual = json.loads(_le(manifesto))["version"]
    nova = a.para or proxima(atual, "major" if a.major else
                             "minor" if a.minor else "patch")

    # 1 · o manifesto do plugin. Substituição pontual da linha da version: reescrever
    # o JSON inteiro reordenaria chaves e encheria o diff de ruído.
    texto = _le(manifesto)
    novo = re.sub(r'("version"\s*:\s*")%s(")' % re.escape(atual),
                  r"\g<1>%s\g<2>" % nova, texto, count=1)
    if novo == texto:
        print("não achei a version %s em %s" % (atual, manifesto))
        return 1
    with open(manifesto, "w", encoding="utf-8") as fh:
        fh.write(novo)

    # 2 · o espelho no catálogo — a entrada é achada pelo `source`, nunca pela ordem
    catalogo = os.path.join(RAIZ, ".claude-plugin", "marketplace.json")
    dados = json.loads(_le(catalogo))
    alvo = next((p for p in dados.get("plugins", [])
                 if p.get("source", "").rstrip("/").endswith("/" + a.plugin)), None)
    if alvo is None:
        print("o catálogo não tem entrada com source ./plugins/%s" % a.plugin)
        return 1
    texto = _le(catalogo)
    marca = '"source": "%s"' % alvo["source"]
    i = texto.find(marca)
    j = texto.find('"version"', i)
    k = texto.find('"', texto.find(":", j) + 1)
    fim = texto.find('"', k + 1)
    if i < 0 or j < 0 or fim < 0:
        print("não achei a version de %s no catálogo" % a.plugin)
        return 1
    with open(catalogo, "w", encoding="utf-8") as fh:
        fh.write(texto[:k + 1] + nova + texto[fim:])

    # 3 · a tabela que a doc publica — quem sabe montá-la é o cobrador dela
    import test_doc_catalogo_plugins as catalogo_doc
    catalogo_doc.conserta(catalogo_doc.do_disco())

    print("%s: %s → %s (manifesto · catálogo · tabela da doc)" % (a.plugin, atual, nova))
    return 0


if __name__ == "__main__":
    sys.exit(main())
