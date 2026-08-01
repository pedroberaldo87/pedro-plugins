#!/usr/bin/env python3
"""O que a SKILL.md do handoff MANDA fazer com o arquivo de plano.

O handoff é o consumidor do `.claude/plans/*.plan.json`, e o defeito que ele
existe pra impedir é a sessão seguinte reescrever o que o arquivo já guarda. A
suíte cobra as duas pontas:
  - o comando prescrito na skill roda e mostra `pronto`/`pendencia` de verdade
  - a prosa manda COPIAR esses campos, não redigi-los de novo
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "skills", "handoff", "SKILL.md")

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def blocos_bash(texto):
    """O bloco como quem copia recebe: sem a indentação do bullet que o aninha."""
    return [textwrap.dedent(b) for b in re.findall(r"```bash\n(.*?)```", texto, re.S)]


def secao_do_plano(texto):
    """O trecho do Processo que fala do arquivo de plano no disco."""
    ini = texto.find("existe arquivo de plano no disco?")
    fim = texto.find("Pré-preencha o prospecto", ini)
    return texto[ini:fim] if ini >= 0 else ""


PLANO = {
    "id": "2026-08-01-sandbox",
    "title": "Plano de sandbox",
    "status": "active",
    "phases": [{"id": "F1", "title": "Base", "items": [
        {"id": "F1.1", "title": "Endpoint de login", "desc": "abre a sessão",
         "requisito": "S-1.1", "pronto": "`curl -X POST /login` devolve 200",
         "status": "done", "evidence": "commit a1b2c3d · 4 testes OK"},
        {"id": "F1.2", "title": "Endpoint de logout", "desc": "derruba a sessão",
         "requisito": "S-1.2", "pronto": "`curl -X POST /logout` devolve 204",
         "pendencia": "cookie ou header? falta decidir", "status": "todo"},
    ]}],
}


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()
    secao = secao_do_plano(texto)

    print("o comando prescrito mostra os campos que a árvore esconde")
    candidatos = [b for b in blocos_bash(secao) if "pronto" in b]
    check("a skill prescreve um comando que lê `pronto` do arquivo", len(candidatos) == 1)
    if candidatos:
        raiz = tempfile.mkdtemp(prefix="handoff-skill-")
        try:
            plans = os.path.join(raiz, ".claude", "plans")
            os.makedirs(plans)
            with open(os.path.join(plans, "2026-08-01-sandbox.plan.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(PLANO, fh, ensure_ascii=False)
            cmd = candidatos[0].replace("<project_root>", raiz)
            proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
            saida = proc.stdout
            check("o comando roda sem erro (%s)" % (proc.stderr.strip()[:80] or "ok"),
                  proc.returncode == 0)
            check("mostra o `pronto` do passo aberto",
                  "curl -X POST /logout` devolve 204" in saida)
            check("mostra a `pendencia` do passo aberto",
                  "cookie ou header? falta decidir" in saida)
            check("não repete o passo já marcado", "Endpoint de login" not in saida)
        finally:
            shutil.rmtree(raiz, ignore_errors=True)

    print("a prosa manda copiar, não redigir")
    check("o `pronto` do arquivo vira o 'Critério de pronto'",
          "Critério de pronto" in secao and "verbatim" in secao.lower())
    check("a `pendencia` vira 'Decisão em aberto' e bloqueia o passo",
          "pendencia" in secao and "bloquead" in secao.lower())

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
