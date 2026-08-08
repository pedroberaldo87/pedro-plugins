#!/usr/bin/env python3
"""Suíte do cobrador do Artigo 9.

O que mais importa aqui não é ele ACHAR — é ele NÃO acusar o legítimo. A primeira versão
desta régua devolveu 846 achados, quase todos menção de plugin em prosa de documentação;
gate que grita assim é desligado na primeira hora, e o repositório já tem esse precedente
(o `scope-cop` ficou em `off`). Por isso metade dos checks abaixo é negativa.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desacoplamento_check as dc  # noqa: E402

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    print("  %s   %s" % ("ok " if cond else "FAIL", label))
    if not cond:
        FAILS.append(label)


def git(d, *a):
    subprocess.run(["git", "-C", d] + list(a), capture_output=True, text=True, timeout=30)


def monta(d, arquivos):
    git(d, "init", "-q")
    git(d, "config", "user.email", "t@t")
    git(d, "config", "user.name", "t")
    os.makedirs(os.path.join(d, "plugins", "alfa"), exist_ok=True)
    os.makedirs(os.path.join(d, "plugins", "beta"), exist_ok=True)
    for rel, txt in arquivos.items():
        cam = os.path.join(d, rel)
        os.makedirs(os.path.dirname(cam), exist_ok=True)
        with open(cam, "w", encoding="utf-8") as fh:
            fh.write(txt)
    git(d, "add", "-A")
    git(d, "commit", "-qm", "x")


def formas(achados):
    return sorted(a["forma"] for a in achados)


def main():
    print("ACUSA o que quebra de verdade")
    d = tempfile.mkdtemp(prefix="desac-sim-")
    try:
        monta(d, {
            "plugins/alfa/skills/alfa/SKILL.md":
                'Rode `"${CLAUDE_PLUGIN_ROOT}/../beta/lib/coisa.py"` para ver.\n',
            "plugins/beta/lib/coisa.py": "# nada\n",
        })
        a = dc.varre(d)
        check("irmão por posição é acusado", "irmao-por-posicao" in formas(a))
        check("e nomeia o irmão certo",
              any(x["alvo"] == "beta" for x in a if x["forma"] == "irmao-por-posicao"))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-cam-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md":
                  "Abra plugins/beta/lib/motor.py antes de continuar.\n"})
        check("caminho dentro do repo para irmão é acusado",
              "dependencia-de-irmao" in formas(dc.varre(d)))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-cont-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md": "Este marketplace tem 21 plugins.\n"})
        check("contagem cravada é acusada", "contagem-cravada" in formas(dc.varre(d)))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("NÃO acusa o legítimo — a metade que impede o gate de ser desligado")
    d = tempfile.mkdtemp(prefix="desac-prosa-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md":
                  "Esta skill conversa com o beta quando ele estiver instalado.\n"})
        check("citar o nome do irmão em PROSA não é acoplamento", dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-doc-")
    try:
        monta(d, {".claude/docs/architecture.md":
                  "O beta vive em plugins/beta/ e faz o seu trabalho.\n"})
        check("documentação que descreve o repo não é acusada por CITAR o nome",
              dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # A isenção da doc é de NOME, não de NÚMERO: é lá que a contagem envelhece calada.
    d = tempfile.mkdtemp(prefix="desac-docnum-")
    try:
        monta(d, {".claude/docs/architecture.md": "O repo tem 21 plugins hoje.\n"})
        a = dc.varre(d)
        check("contagem cravada NA DOC é acusada", formas(a) == ["contagem-cravada"])
        check("e nomeia a contagem que envelheceu",
              any(x["alvo"] == "21 plugins" for x in a))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-docmd-")
    try:
        monta(d, {".claude/docs/architecture.md":
                  "São 21 plugins — `$ ls plugins | wc -l` diz quantos.\n"})
        check("na doc, o número COM o comando que o produz segue legítimo",
              dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-outros-")
    try:
        monta(d, {"README.md": "O repo tem 21 plugins.\n",
                  ".claude/plans/x.md": "O repo tem 21 plugins.\n"})
        check("fora da pasta de doc, `.claude/` e o README seguem isentos da contagem",
              dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-cmd-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md":
                  "São 21 plugins hoje — `$ ls plugins | wc -l` diz quantos.\n"})
        check("número COM o comando que o produz não é cravado", dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-narr-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md":
                  "Até 2026-08-07 este artigo dizia 54 suítes, e estava errado.\n"})
        check("narrativa de defeito passado não é contagem cravada", dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-isen-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md":
                  "Abra plugins/beta/lib/x.py  <!-- acopla-ok: o catálogo aponta a dependência -->\n"})
        check("isenção declarada na linha silencia o achado", dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    d = tempfile.mkdtemp(prefix="desac-self-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md": "Rode plugins/alfa/lib/meu.py.\n"})
        check("citar a SI MESMO nunca é acoplamento", dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("o retrato: reprova o que PIORA, não a dívida que já existe")
    d = tempfile.mkdtemp(prefix="desac-base-")
    try:
        monta(d, {"plugins/alfa/skills/alfa/SKILL.md": "Abra plugins/beta/lib/velho.py\n"})
        antigos = dc.varre(d)
        os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
        with open(os.path.join(d, dc.RETRATO), "w", encoding="utf-8") as fh:
            json.dump(sorted(dc.chave(x) for x in antigos), fh)
        conhecidos = set(json.load(open(os.path.join(d, dc.RETRATO), encoding="utf-8")))
        check("a dívida do retrato não conta como nova",
              [x for x in dc.varre(d) if dc.chave(x) not in conhecidos] == [])

        with open(os.path.join(d, "plugins/alfa/skills/alfa/SKILL.md"), "a",
                  encoding="utf-8") as fh:
            fh.write("\nE tambem plugins/beta/hooks/novo.sh\n")
        git(d, "add", "-A")
        git(d, "commit", "-qm", "y")
        novos = [x for x in dc.varre(d) if dc.chave(x) not in conhecidos]
        check("acoplamento NOVO fura o retrato e é acusado", len(novos) >= 1)

        with open(os.path.join(d, "plugins/alfa/skills/alfa/SKILL.md"), encoding="utf-8") as fh:
            corpo = fh.read()
        with open(os.path.join(d, "plugins/alfa/skills/alfa/SKILL.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("linha nova no topo\n" + corpo)
        git(d, "add", "-A")
        git(d, "commit", "-qm", "z")
        depois = [x for x in dc.varre(d) if dc.chave(x) not in conhecidos]
        check("empurrar as linhas NÃO cria achado falso (a chave ignora o número da linha)",
              len(depois) == len(novos))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("sem git, não julga — e não acusa ninguém")
    d = tempfile.mkdtemp(prefix="desac-nogit-")
    try:
        check("pasta sem repositório devolve vazio", dc.varre(d) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK (%d checks)" % TOTAL[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
