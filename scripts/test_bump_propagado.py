#!/usr/bin/env python3
"""O último commit que mexeu num plugin é o mesmo que subiu a version dele.

Nasceu de um caso real: o commit d7d48c2 acrescentou a receita do `2op` em
`plugins/bootstrap/config/manifest.json` e deixou a version do bootstrap parada
em 1.17.10 — quem já tinha o plugin instalado nunca receberia a receita nova,
porque a version é a única chave de propagação.

    python3 scripts/test_bump_propagado.py
"""

import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS = []


def git(*args):
    out = subprocess.run(["git"] + list(args), cwd=RAIZ, capture_output=True,
                         text=True, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    return out.stdout


def _e_sha(txt):
    """A saída é mesmo um identificador de commit, e não o eco de um erro do git."""
    return len(txt) == 40 and all(c in "0123456789abcdef" for c in txt)


def _versao_no_commit(sha, manifesto):
    """A `version` do manifesto COMO ELA ESTAVA naquele commit. Ausente devolve None."""
    try:
        return json.loads(git("show", sha + ":" + manifesto)).get("version")
    except ValueError:
        return None


def main():
    plugins = sorted(os.listdir(os.path.join(RAIZ, "plugins")))
    for nome in plugins:
        pasta = "plugins/%s" % nome
        manifesto = "%s/.claude-plugin/plugin.json" % pasta
        if not os.path.exists(os.path.join(RAIZ, manifesto)):
            continue
        # C = último commit que mexeu em QUALQUER arquivo do plugin.
        c_conteudo = git("log", "-1", "--format=%H", "--", pasta).strip()
        if not c_conteudo:
            continue
        # A version DEPOIS do último commit de conteúdo. Comparar com a de hoje é o
        # que diz se alguém subiu o número desde então.
        #
        # A primeira versão deste teste perguntava outra coisa: se o `plugin.json`
        # aparecia entre os arquivos daquele commit. Isso é proxy, e proxy grosseiro —
        # um commit que mexe só na `description` toca o arquivo sem subir número
        # nenhum, e passava. Agora a pergunta é o número, não o arquivo.
        ver_em_c = _versao_no_commit(c_conteudo, manifesto)
        if ver_em_c is None:
            continue
        # Commit que já subiu o número: o de antes dele é diferente do dele.
        #
        # `git rev-parse <raiz>^` não devolve vazio: sai 128 e ECOA o argumento de
        # volta no stdout. Sem conferir a forma, o commit raiz virava um pai falso,
        # a leitura da version falhava, e o plugin era pulado em silêncio — que é o
        # mesmo defeito de proxy que este teste acabou de perder.
        pai = git("rev-parse", c_conteudo + "^").strip()
        if _e_sha(pai) and _versao_no_commit(pai, manifesto) != ver_em_c:
            continue
        with open(os.path.join(RAIZ, manifesto), encoding="utf-8") as fh:
            ver_hoje = json.load(fh).get("version")
        ok = ver_em_c != ver_hoje
        print(("  ok   " if ok else "  FAIL ") +
              "%s: bump acompanha a última mudança de conteúdo" % nome)
        if not ok:
            FALHAS.append("%s (conteúdo em %s, version parada em %s)"
                          % (nome, c_conteudo[:7], ver_hoje))

    if FALHAS:
        print("\nBUMP ESQUECIDO em: " + ", ".join(FALHAS))
        return 1
    print("\ntodos os plugins com bump propagado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
