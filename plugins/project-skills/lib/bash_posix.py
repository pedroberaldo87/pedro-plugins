#!/usr/bin/env python3
"""bash_posix — o caminho de um bash que RODA, não o primeiro que o PATH oferecer.

Por que existe
--------------
Toda suíte que executa um comando de shell precisava da mesma resposta, e a
resposta óbvia (`shutil.which("bash")`) está errada no Windows: o `bash` do PATH
é o do WSL (`System32\\bash.exe`), e em máquina sem distro instalada ele responde
`Windows Subsystem for Linux has no installed distributions.` **em UTF-16** — o
que chega ao Python como stdout vazio ou como texto salpicado de `\\x00`.

O efeito medido na esteira de 2026-08-10: suítes reprovando a SKILL ou o HOOK
por causa do interpretador. "O comando não imprimiu nada" e "o comando não
existe" ficam indistinguíveis, e a conclusão sai errada sobre código certo.

A régua, então, não é estar no PATH: é **responder**. E sem nenhum bash que
responda, quem chama PULA o caso declarando — comando de shell sem shell não é
falha de quem escreveu o comando.

Estava duplicado em `bootstrap/lib/test_conformance.py` e em
`handoff/lib/test_handoff_skill.py`, com o mesmo comentário reescrito nos dois.
Terceira cópia seria a hora de errar: prosa copiada diverge no primeiro conserto,
e a divergência é silenciosa (`patterns.md` §1.6a).

Uso
---
    from bash_posix import bash_posix

    BASH = bash_posix()
    if BASH is None:
        print("  skip <o caso> (nenhum bash funcional nesta máquina)")
    else:
        subprocess.run([BASH, "-c", comando], ...)
"""

import os
import subprocess

_BASH = None


def _igual(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def _bash_do_path():
    """Os `bash` das pastas ABSOLUTAS do PATH, na ordem — NUNCA o da pasta corrente.

    `shutil.which` não serve aqui (scan 8e9a3ff2, achado 39): no Windows ele consulta a
    pasta corrente ANTES do PATH, e no POSIX uma entrada vazia ou relativa (`:`, `.`,
    `bin`) vale como cwd. A pasta corrente é a do repositório que o usuário abriu — um
    `bash.exe`/`bash.bat` ali seria executado, e o único crivo do chamador, imprimir
    `VIVO`, um programa plantado imprime. Por isso o PATH é percorrido à mão: entrada
    vazia, relativa ou que resolve para o cwd é descartada, e `which` não é chamado.
    """
    cwd = os.getcwd()
    exts = [""]
    if os.name == "nt":
        exts = [e.lower() for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e]
    achados = []
    for pasta in os.environ.get("PATH", "").split(os.pathsep):
        pasta = pasta.strip('"')
        if not pasta or not os.path.isabs(pasta) or _igual(pasta, cwd):
            continue
        for ext in exts:
            c = os.path.join(pasta, "bash" + ext)
            if os.path.isfile(c) and os.access(c, os.X_OK):
                achados.append(c)
                break
    return achados


def bash_posix():
    """Devolve o caminho de um bash que responde, ou None se não houver nenhum."""
    global _BASH
    if _BASH is not None:
        return _BASH or None
    candidatos = _bash_do_path()
    if os.name == "nt":
        # Barra NORMAL de propósito: o Windows aceita as duas, e a invertida em
        # literal Python é campo minado (`\b` de `\bin` vira backspace).
        candidatos += ["C:/Program Files/Git/bin/bash.exe",
                       "C:/Program Files/Git/usr/bin/bash.exe",
                       "C:/Program Files (x86)/Git/bin/bash.exe"]
    for c in candidatos:
        if not os.path.exists(c):
            continue
        try:
            r = subprocess.run([c, "-c", "echo VIVO"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=20,
                               stdin=subprocess.DEVNULL, start_new_session=True)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.stdout.strip() == "VIVO":
            _BASH = c
            return c
    _BASH = ""
    return None


if __name__ == "__main__":
    achado = bash_posix()
    print(achado or "(nenhum bash funcional nesta máquina)")
