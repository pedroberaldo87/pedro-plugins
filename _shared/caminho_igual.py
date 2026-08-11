#!/usr/bin/env python3
"""caminho_igual — comparar CAMINHO, e não o texto que por acaso o descreve.

Por que existe
--------------
Seis suítes deste repositório reprovaram no Windows em 2026-08-11 pela mesma razão,
e nenhuma delas media coisa errada: elas mediam a coisa certa comparando string.

    ['.claude\\docs\\blueprint.md'] == ['.claude/docs/blueprint.md']   → False

É o mesmo diretório, escrito de dois jeitos. `os.path.join` devolve a barra do
sistema, `os.path.expanduser` às vezes devolve a outra, e o teste que escreveu o
esperado à mão fica com a do autor. O `startswith`/`endswith`/`in` cru mente nos
três casos — e mente na direção pior: reprova código CERTO, o que manda a próxima
pessoa consertar o que não está quebrado.

A regra é uma só: **normalize os dois lados antes de comparar, sempre**. Sem isso a
comparação depende de quem rodou o teste, e "passa na minha máquina" volta a ser um
resultado aceitável.

Não é só para suíte. Programa que decide alguma coisa comparando caminho tem o mesmo
defeito, com consequência maior: lá ele não reprova, ele age errado calado.

Uso
---
    from caminho_igual import igual, contem, termina_em

    igual(achado, esperado)          # o mesmo caminho?
    contem(achado, ".claude/plans")  # esse pedaço está no caminho?
    termina_em(achado, "lib/x.py")   # o caminho acaba assim?

Os três aceitam o esperado escrito com barra normal, sempre — quem escreve o teste
não precisa saber em que sistema ele vai rodar. É o ponto: o esperado é um caminho,
não um texto, e cabe a esta receita traduzir.
"""

import os


def _n(p):
    """O caminho em forma canônica: barra do sistema, sem `.`/`..`, sem barra final.

    `normpath` faz a barra e os segmentos redundantes; o `rstrip` fecha o caso de
    "a/b" contra "a/b/", que `normpath` sozinho não iguala em todo sistema.
    """
    if p is None:
        return ""
    return os.path.normpath(str(p)).rstrip(os.sep) or os.sep


def igual(a, b):
    """Os dois descrevem o MESMO caminho, escritos como estiverem."""
    return _n(a) == _n(b)


def contem(caminho, pedaco):
    """`pedaco` aparece dentro de `caminho`, com as duas barras normalizadas.

    Comparação de SEGMENTO, não de substring: procurar "lib" não pode casar dentro
    de "biblioteca". O pedaço é cercado pelo separador antes de procurar.
    """
    c, p = _n(caminho), _n(pedaco)
    if not p:
        return False
    return c == p or (os.sep + p + os.sep) in (os.sep + c + os.sep)


def termina_em(caminho, sufixo):
    """O caminho acaba com esse sufixo, contado em SEGMENTOS, não em letras.

    Contar em letras deixaria "meu-lixeiro.py" casar com "lixeiro.py", que é o
    mesmo defeito do `endswith` cru só que mais difícil de ver.
    """
    c, s = _n(caminho).split(os.sep), _n(sufixo).split(os.sep)
    return len(s) <= len(c) and c[len(c) - len(s):] == s


def demo():
    """A prova que roda: `python3 _shared/caminho_igual.py`."""
    sep = os.sep
    a = sep.join([".claude", "docs", "blueprint.md"])

    assert igual(a, ".claude/docs/blueprint.md")
    assert igual("a/b/", "a/b")
    assert igual("a/./b", "a/b")
    assert not igual("a/b", "a/c")
    assert not igual(None, "a")

    assert contem(a, ".claude/docs")
    assert contem(a, "docs")
    assert contem(sep.join(["x", "lib", "y"]), "lib")
    # o que o `in` cru erraria: "lib" NÃO está em "biblioteca"
    assert not contem(sep.join(["x", "biblioteca", "y"]), "lib")
    assert not contem(a, "")

    assert termina_em(a, "docs/blueprint.md")
    assert termina_em(a, "blueprint.md")
    # o que o `endswith` cru erraria: "meu-x.py" não termina em "x.py"
    assert not termina_em(sep.join(["p", "meu-x.py"]), "x.py")
    assert not termina_em("a.py", "b/a.py")

    print("caminho_igual: ok (as duas barras descrevem o mesmo caminho)")


if __name__ == "__main__":
    demo()
