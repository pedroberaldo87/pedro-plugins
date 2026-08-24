#!/usr/bin/env python3
"""A "rodada limpa" se define por SEVERIDADE, não por taxa de descoberta.

O bloco "As fases não são sequenciais no tempo" da /qa-loop é o último lugar VIVO
(não-revogado) do SKILL.md que explicava o evento interno da Fase Assintótica como
"retornos decrescentes" — a leitura que o Artigo 14 revogou. Ele escapava do cobrador
`test_revisao_fecha_por_problema.py` porque a frase proibida estava QUEBRADA por uma
mudança de linha do markdown, e aquele cobrador lê linha a linha.

Este teste lê o bloco com o espaço em branco NORMALIZADO — quebra de linha não esconde
frase — e exige que o evento interno esteja escrito no eixo de severidade.

    python3 scripts/test_rodada_limpa_por_severidade.py
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(RAIZ, "plugins/project-skills/skills/qa-loop/SKILL.md")

FRASES_DE_TAXA = ["retornos decrescentes", "retorno decrescente", "rendendo menos",
                  "achando cada vez menos", "convergiu o suficiente"]

texto = open(SKILL, encoding="utf-8").read()
bloco = texto.split("As fases **não são sequenciais no tempo**", 1)
assert len(bloco) == 2, "o bloco das duas fases sumiu do SKILL.md — atualize este teste"
bloco = bloco[1].split("\n\n", 1)[0]
plano = re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>\s?", "", bloco)).lower()

for frase in FRASES_DE_TAXA:
    assert frase not in plano, (
        "o bloco das duas fases define a rodada limpa como TAXA DE DESCOBERTA (%r) — "
        "o Artigo 14 fecha por severidade" % frase)

assert "acima do piso" in plano, (
    "o bloco não nomeia o piso de severidade ao descrever o evento interno da rodada limpa")

print("ok · a rodada limpa é definida por severidade, e a quebra de linha não esconde a frase")
