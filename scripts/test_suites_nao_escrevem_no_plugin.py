#!/usr/bin/env python3
"""Suite de hook não escreve arquivo dentro da própria pasta rastreada.

Duas suítes rodando ao mesmo tempo escrevem o mesmo `mock_*.sh` na pasta do
plugin e o trap de uma apaga o mock da outra: a esteira fica vermelha por
sorteio, e é debaixo desse ruído que defeito de verdade passa despercebido.
Além disso o processo morto deixa mock órfão no working tree de um repo
público.

Régua: arquivo temporário de suíte nasce em diretório temporário POR EXECUÇÃO.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# `cat > "$HERE/x"`, `> "$HERE"/x`, `tee "$HERE/x"` — escrita dentro da pasta da suíte
ESCRITA = re.compile(r'(?:>\s*|tee\s+(?:-\w+\s+)*)"\$HERE"?[/"]')


def suites():
    for base, dirs, arquivos in os.walk(os.path.join(RAIZ, "plugins")):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        for a in arquivos:
            if a.startswith("test_") and a.endswith(".sh"):
                yield os.path.join(base, a)


def test_nenhuma_suite_escreve_na_pasta_do_plugin():
    faltas = []
    for caminho in suites():
        with open(caminho, encoding="utf-8") as fh:
            for n, linha in enumerate(fh, 1):
                if linha.lstrip().startswith("#"):
                    continue
                if ESCRITA.search(linha):
                    faltas.append(
                        "%s:%d: %s" % (os.path.relpath(caminho, RAIZ), n, linha.strip())
                    )
    assert not faltas, (
        "suíte escrevendo dentro da pasta rastreada do plugin "
        "(use um temporário por execução):\n" + "\n".join(faltas)
    )


def test_working_tree_sem_mock_orfao():
    sobras = []
    for base, dirs, arquivos in os.walk(os.path.join(RAIZ, "plugins")):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        sobras += [
            os.path.relpath(os.path.join(base, a), RAIZ)
            for a in arquivos
            if a.startswith("mock_") and a.endswith(".sh")
        ]
    assert not sobras, "mock órfão de suíte no working tree: %s" % sobras


if __name__ == "__main__":
    falhou = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_"):
            try:
                fn()
                print("ok   %s" % nome)
            except AssertionError as e:
                falhou = 1
                print("FALHOU %s\n%s" % (nome, e))
    sys.exit(falhou)
