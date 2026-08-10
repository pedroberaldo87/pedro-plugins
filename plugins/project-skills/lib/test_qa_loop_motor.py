#!/usr/bin/env python3
"""O cobrador do motor.js do /qa-loop — irmão do test_motor_js.py (que cobra o do /sprint).

POR QUE EXISTE (2026-08-10). O motor do `/sprint` virou arquivo do plugin em
2026-08-09; o deste continuou sendo MONTADO PELA CASCA a cada disparo. A
assimetria cobrou na mesma sessão em que foi notada: o passo que apaga o sinal da
barra virou CÓDIGO no sprint (`encerra:barra`) e ficou em PROSA aqui — "ao
entregar o relatório, encerre". Prosa não pega. O sinal do qa-loop ficou aceso
**9h26 depois do fim**, com a barra anunciando missão de pé, e quem viu foi o
dono, não um cobrador.

O que este arquivo cobra:

  A · o motor é ARQUIVO e é JavaScript válido (a casca não o redigita);
  B · a barra ANDA — cada etapa da rodada se registra;
  C · a barra APAGA — o encerramento é o último ato, antes do `return`, e por
      isso alcança todo caminho de saída (rodada limpa, teto, churn, agente mudo);
  D · toda chamada de agente leva `label` próprio (a mesma régua do irmão);
  E · nada de caminho absoluto de máquina.

    python3 plugins/project-skills/lib/test_qa_loop_motor.py
"""
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
MOTOR = os.path.join(PLUGIN, "skills", "qa-loop", "references", "motor.js")
SKILL = os.path.join(PLUGIN, "skills", "qa-loop", "SKILL.md")

ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


# A · o motor existe como arquivo do plugin
check("o motor do qa-loop é ARQUIVO do plugin", os.path.isfile(MOTOR),
      "esperado em %s" % MOTOR)
if not os.path.isfile(MOTOR):
    print("\nFALHOU: %d" % falhas)
    sys.exit(1)

motor = open(MOTOR, encoding="utf-8").read()
skill = open(SKILL, encoding="utf-8").read()

check("meta.name é qa-loop-engine", "name: 'qa-loop-engine'" in motor)

# B · a barra anda: cada etapa da rodada se registra, e o comando é o do módulo
# de andamento (não um `rm` à mão, que deixaria o resto do estado para trás).
check("existe o papel que faz a barra ANDAR", "andaPrompt" in motor and "const anda =" in motor)
etapas = set(re.findall(r"await anda\(r, [`']([a-zç ]+)", motor))
check("as quatro etapas da rodada se registram",
      {"revisando", "planejando", "confirmando"} <= etapas and
      any(e.startswith("consertando") for e in re.findall(r"await anda\(r, [`']([^`'$]+)", motor)),
      "achadas: %s" % sorted(etapas))
check("o registro usa o módulo de andamento, não um comando à mão",
      "lib/andamento.py" in motor and '" onda ' in motor)

# C · a barra apaga, e o encerramento é o ÚLTIMO ato — antes do `return`.
check("existe o papel que APAGA o sinal", "encerraPrompt" in motor and "encerra:barra" in motor)
check("o encerramento chama `andamento.py encerra`", '" encerra ' in motor)
pos_encerra = motor.find("label: 'encerra:barra'")
pos_return = motor.find("\nreturn {")
check("o encerramento vem ANTES do return (alcança todo caminho de saída)",
      0 < pos_encerra < pos_return,
      "encerra=%d return=%d" % (pos_encerra, pos_return))
# O teste que morde: o encerramento não pode estar dentro do `if` da rodada limpa,
# senão teto e churn saem sem apagar — que é exatamente o defeito que o originou.
trecho = motor[max(0, pos_encerra - 900):pos_encerra]
check("o encerramento NÃO está preso ao caminho da rodada limpa",
      "cleanRound ?" in trecho or "cleanRound?" in trecho,
      "o motivo tem que ser derivado, não o passo condicionado")

# D · todo agente sai com rótulo próprio (sem ele a tela nomeia pelo prompt).
linhas = motor.splitlines()
sem_rotulo = [
    "%d: %s" % (i + 1, linha.strip()[:70])
    for i, linha in enumerate(linhas)
    if "phase: '" in linha
    and "label:" not in linha
    and "label:" not in (linhas[i + 1] if i + 1 < len(linhas) else "")
]
check("toda chamada de agente tem label próprio", not sem_rotulo,
      "sem rótulo → %s" % " | ".join(sem_rotulo))

# E · nada de caminho de máquina, e o resolvedor entra por args.
check("sem caminho absoluto de máquina", "/Users/" not in motor)
check("o resolvedor de plugin chega por args (roda fora deste repo)",
      "ARGS.resolvePlugin" in motor)

# F · a SKILL manda usar o ARQUIVO, não redigitar o script.
check("a skill aponta o motor por scriptPath",
      "references/motor.js" in skill and "scriptPath" in skill)

# sintaxe: tem que ser JavaScript válido (quando node existe na máquina).
if shutil.which("node"):
    r = subprocess.run(["node", "--check", MOTOR], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    check("node --check passa", r.returncode == 0, r.stderr.strip()[:160])
else:
    print("  skip node --check (node ausente)")

print()
if falhas:
    print("FALHOU: %d" % falhas)
    sys.exit(1)
print("test_qa_loop_motor: %d checagens verdes" % ok)
