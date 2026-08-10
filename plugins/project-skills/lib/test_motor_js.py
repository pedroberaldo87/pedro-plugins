#!/usr/bin/env python3
"""O cobrador do motor.js — o arquivo que o disparo do /sprint passa como scriptPath.

Por que existe (2026-08-09): os prompts e schemas do motor só existiam em prosa no
SKILL.md, a casca os traduzia em código a cada disparo, e uma dessas traduções foi
guardada em rascunho e rodou DEPOIS do rename sovai->sprint com o nome velho — sem
nada acusar. Agora o código mora em references/motor.js, e este teste cobra que ele
não divirja das três fontes que o definem:

  A · o esqueleto do SKILL.md (as peças com nome — blocoMax, ledgerCorrida, ...);
  B · a tabela prompt -> PAPEL do SKILL.md (o medidor da autópsia classifica por ela);
  C · os tiers de _shared/r8-tiers.json (a constante T é escrita no arquivo, não lida
      de args — e escrita à mão diverge no primeiro reajuste).

    python3 plugins/project-skills/lib/test_motor_js.py
"""
import json
import os
import re
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
MOTOR = os.path.join(PLUGIN, "skills", "sprint", "references", "motor.js")
SKILL = os.path.join(PLUGIN, "skills", "sprint", "SKILL.md")
TIERS = os.path.join(PLUGIN, "skills", "sprint", "references", "r8-tiers.json")

ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


motor = open(MOTOR, encoding="utf-8").read()
skill = open(SKILL, encoding="utf-8").read()

# A · as peças do esqueleto — a MESMA lista da conferência escrita no SKILL.md.
PECAS = ["blocoMax", "naoDespachadas", "idsDoPlano", "congeladas", "esperaChain",
         "saudePrompt", "ledgerCorrida", "impressaoTarefa", "emCirculo",
         "paraPorCausaGlobal"]
for peca in PECAS:
    check("peça '%s' está no motor.js" % peca, peca in motor)
    check("peça '%s' segue no esqueleto do SKILL.md" % peca, peca in skill)

# B · a tabela prompt -> PAPEL do SKILL.md, cobrada no arquivo executável.
PAPEIS = {
    "orquestradorPrompt": "ORQUESTRADOR", "execPrompt": "EXECUTOR",
    "reviewBuildPrompt": "REVISOR", "confirmBuildPrompt": "CONFIRMADOR",
    "auditorPrompt": "AUDITOR", "diagnoseStuckTaskPrompt": "DIAGNOSTICO",
    "desafioCausaPrompt": "DESAFIADOR", "reguaPrompt": "MECANICO",
    "saudePrompt": "MECANICO", "reservaPrompt": "MECANICO",
    "checkpointPrompt": "MECANICO", "docTouchPrompt": "MECANICO",
    "colheitaPrompt": "MECANICO", "tickPlanPrompt": "MARCAR",
    "runSuitePrompt": "SUITE",
}
for nome, papel in PAPEIS.items():
    m = re.search(r"const %s = [^`]*`PAPEL: (\w+)" % nome, motor)
    check("%s abre com PAPEL: %s" % (nome, papel),
          m is not None and m.group(1) == papel,
          "achado: %s" % (m.group(1) if m else "prompt sem a declaração"))

# os revisores de tarefa e de bloco também são REVISOR (não estão na tabela por nome)
for nome in ("revisorTarefaPrompt", "revisorBlocoPrompt"):
    m = re.search(r"const %s = [^`]*`PAPEL: (\w+)" % nome, motor)
    check("%s abre com PAPEL: REVISOR" % nome, m is not None and m.group(1) == "REVISOR")

# C · a constante T contra os tiers vendorados — escrita à mão diverge calada.
tiers = json.load(open(TIERS, encoding="utf-8"))["tiers"]
m = re.search(r"const T = \{(.*?)\}\s*\n", motor, re.S)
check("a constante T existe no motor.js", m is not None)
if m:
    for knob in ("decompose", "coordinate", "executor", "mechanical", "diagnose", "finalize"):
        esperado = tiers[knob]["effort"]
        got = re.search(r"%s: \{effort:'(\w+)'\}" % knob, m.group(0))
        check("T.%s = %s (igual ao r8-tiers.json)" % (knob, esperado),
              got is not None and got.group(1) == esperado,
              "no arquivo: %s" % (got.group(1) if got else "ausente"))

# o nome do motor e a ausência do nome morto — o defeito que pariu este arquivo.
check("meta.name é sprint-build-engine", "name: 'sprint-build-engine'" in motor)
check("nenhum 'sovai' sobrevive no motor.js", "sovai" not in motor.lower())

# o commit da onda sai com o prefixo novo (o suite_congela compara literal).
check("o checkpoint commita como 'sprint: onda'", "sprint: onda" in motor)

# nada de caminho cravado de máquina — o repo do dono não é este marketplace.
check("sem caminho absoluto de máquina", "/Users/" not in motor)

# sintaxe: o arquivo tem que ser JavaScript válido (quando node existe na máquina).
if shutil.which("node"):
    r = subprocess.run(["node", "--check", MOTOR], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    check("node --check passa", r.returncode == 0, r.stderr.strip()[:120])
else:
    print("  skip node --check (node ausente)")

print()
if falhas:
    print("FALHOU: %d" % falhas)
    sys.exit(1)
print("test_motor_js: %d checagens verdes" % ok)
