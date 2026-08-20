#!/usr/bin/env python3
"""Quem escreve documento nasce sabendo do desacoplamento (S-58).

A doc que este marketplace gera envelhecia em silêncio por duas frases:
a contagem cravada ("os N plugins") e a lista de nomes em prosa. As duas
são as formas 2 e 3 do Artigo 9 da constituição, e nenhuma delas estava
escrita onde o documento é ESCRITO — só onde ele é cobrado, depois.

Esta suíte confere o texto no arquivo: a regra existe uma vez, no
`/doc`, mandando as duas trocas concretas (comando no lugar do
número, índice no lugar da lista), citando o cobrador pelo comando e a
isenção pelo molde; e o `/doc-touch`, que re-projeta os mesmos docs,
aponta para ela em vez de repetir uma cópia que defasa.
"""

import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(AQUI, "..")
SKILLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                      "project-skills", "skills")
RAIZ = os.path.join(PLUGIN, "..", "..")
COBRADOR = os.path.join(RAIZ, "scripts", "desacoplamento_check.py")

FULL = os.path.join(SKILLS, "doc", "SKILL.md")
TOUCH = os.path.join(SKILLS, "doc-touch", "SKILL.md")

# O título da seção é contrato: é por ele que o /doc-touch aponta.
SECAO = "Desacoplamento — duas trocas obrigatórias em TODO doc escrito"

# Os índices que substituem a lista de nomes em prosa — os mesmos que o
# cobrador isenta em `desacoplamento_check.py:INDICES`.
INDICES = (".claude-plugin/marketplace.json",
           "plugins/bootstrap/config/manifest.json")  # acopla-ok: índice citado, não dependência executável — o mesmo que `desacoplamento_check.py:INDICES` isenta

# As formas de comando que o cobrador aceita como procedência
# (`desacoplamento_check.py:COM_COMANDO`).
COMANDOS = ("grep -c", "wc -l", "python3")

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def ler(caminho):
    """Lê o contrato com o espaço em branco normalizado.

    A quebra de linha do Markdown é diagramação, não conteúdo.
    """
    return " ".join(open(caminho, encoding="utf-8").read().split())


def main():
    full = ler(FULL)
    touch = ler(TOUCH)

    print("a regra existe, uma vez, na skill que escreve documento")
    check("a secao de desacoplamento existe no /doc", SECAO in full)
    check("a secao vale para todo doc escrito, nao so para o CLAUDE.md",
          "`CLAUDE.md`" in full and ".claude/docs/*.md" in full)  # casa-ok: fixture de teste, o literal e o dado do caso

    print("troca 1 — o COMANDO entra no lugar do numero")
    check("a skill manda a contagem cravada sair",
          "Contagem cravada sai" in full)
    check("a skill nomeia o comando como o que entra",
          "entra o COMANDO que a produz" in full)
    for cmd in COMANDOS:
        check("a skill mostra a forma de comando `%s`" % cmd, cmd in full)
    check("o numero so entra colado ao comando, nunca solto",
          "colado ao comando" in full and "nunca solto" in full)

    print("troca 2 — o INDICE entra no lugar da lista de nomes")
    check("a skill manda a lista de nomes de plugin sair",
          "Lista de nomes de plugin sai" in full)
    check("a skill nomeia o indice como o que entra",
          "entra o ÍNDICE que os enumera" in full)
    for idx in INDICES:
        check("a skill aponta o indice `%s`" % idx, idx in full)

    print("a skill diz quem cobra e como se isenta")
    check("o cobrador e citado pelo comando que se roda",
          "python3 scripts/desacoplamento_check.py" in full)
    check("a isencao e citada no molde que o cobrador aceita",
          "`acopla-ok: <motivo>`" in full)
    check("a lei de origem e apontada, nao recontada",
          "constituicao.md" in full and "Artigo 9" in full)

    print("o cobrador citado pela skill morde DENTRO da pasta de documentacao")
    d = tempfile.mkdtemp(prefix="docdesac-")
    try:
        os.makedirs(os.path.join(d, ".claude", "docs"))
        os.makedirs(os.path.join(d, "plugins", "alfa"))
        with open(os.path.join(d, ".claude", "docs", "architecture.md"),
                  "w", encoding="utf-8") as fh:
            fh.write("O repo tem 21 plugins hoje.\n")
        for a in (["init", "-q"], ["config", "user.email", "t@t"],
                  ["config", "user.name", "t"], ["add", "-A"], ["commit", "-qm", "x"]):
            subprocess.run(["git", "-C", d] + a, capture_output=True, timeout=30, stdin=subprocess.DEVNULL, start_new_session=True)
        saida = subprocess.run([sys.executable, COBRADOR, "--root", d, "--todos"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, stdin=subprocess.DEVNULL, start_new_session=True)
        check("numero cravado num doc de `.claude/docs/` e acusado",  # casa-ok: fixture de teste, o literal e o dado do caso
              saida.returncode == 1 and "contagem-cravada" in saida.stdout
              and "architecture.md" in saida.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("o /doc-touch aponta para a regra em vez de guardar uma copia")
    check("o touch traz o desacoplamento entre as invariantes",
          "Desacoplamento" in touch)
    check("o touch manda as MESMAS duas trocas",
          "comando" in touch and "índice" in touch
          and all(i in touch for i in INDICES))
    check("o touch aponta a secao canonica do /doc pelo titulo",
          SECAO in touch)
    check("o touch cita o mesmo cobrador e a mesma isencao",
          "python3 scripts/desacoplamento_check.py" in touch
          and "acopla-ok: <motivo>" in touch)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
