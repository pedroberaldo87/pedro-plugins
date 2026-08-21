#!/usr/bin/env python3
"""Suite da skill de reentrada (F23.10 · R-33): o caso da manha.

O que prova, executando o COMANDO da propria SKILL.md (nunca uma reescrita dele):

1. O bloco da skill le o desfecho do ULTIMO run do ledger e o classifica por
   lib/retomada.py — os quatro campos (desfecho/acao/causa/evidencia) saem do
   disco, nunca de memoria.
2. Largada pendurada em em-curso/ (a corrida que morreu por fora, antes do teto
   da colheita) sai classificada como morta-por-fora → conserta-e-relanca.
3. O gate do relance declara --caso causa-repetida quando a mesma causa parou
   duas corridas — e a acao vira espera-dono.
4. A skill APONTA os blocos da SKILL.md do sprint (largada, retorno, parada no
   ledger) por titulo LITERAL — o teste reprova se o sprint renomear o bloco e o
   ponteiro apodrecer — e NAO copia os comandos deles.

Roda com: python3 lib/test_reentrada_skill.py
Sem framework: __main__ com asserts, sai !=0 se falhar.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(AQUI)
SKILL = os.path.join(PLUGIN, "skills", "reentrada", "SKILL.md")
SPRINT = os.path.join(PLUGIN, "skills", "sprint", "SKILL.md")

sys.path.insert(0, AQUI)
from retomada import SEGUE, CONSERTA, DONO  # noqa: E402


def bloco_da_skill():
    """O bloco bash da SKILL.md que faz a leitura da manha — extraido, nao reescrito."""
    md = open(SKILL, encoding="utf-8").read()
    blocos = re.findall(r"```bash\n(.*?)```", md, re.S)
    alvo = [b for b in blocos if "RETOMADA" in b and "$LEDGER" in b]
    assert len(alvo) == 1, "esperava UM bloco bash com o pipeline ledger→retomada, achei %d" % len(alvo)
    return alvo[0]


def roda_bloco(repo_root, plan_path):
    """Executa o bloco com os placeholders preenchidos, como quem segue a skill."""
    bloco = bloco_da_skill()
    assert "<a raiz do projeto>" in bloco and "<o plano da missão>" in bloco, \
        "os placeholders do bloco mudaram — a prosa da skill tem que defini-los"
    bloco = bloco.replace("<a raiz do projeto>", repo_root).replace("<o plano da missão>", plan_path)
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN)
    return subprocess.run(["bash", "-c", bloco], capture_output=True, text=True, env=env,
                          stdin=subprocess.DEVNULL, start_new_session=True)


def objetos(stdout):
    """Todos os objetos JSON de topo do stdout (relance e depois o veredito)."""
    dec = json.JSONDecoder()
    i, fora = 0, []
    while True:
        j = stdout.find("{", i)
        if j < 0:
            return fora
        try:
            obj, fim = dec.raw_decode(stdout, j)
            fora.append(obj)
            i = fim
        except ValueError:
            i = j + 1


def grava_corrida(repo_root, run_id, desfecho, causa, missao):
    pasta = os.path.join(repo_root, ".claude", ".sprint")
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, "corridas.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "run_id": run_id, "missao": missao,
            "progresso": {"fechadas": 2, "total": 8},
            "custo": {"tokens": 1000},
            "tempo": {"inicio": 1, "fim": 2},
            "desfecho": desfecho, "causa": causa,
        }, ensure_ascii=False) + "\n")


def caso_ultimo_run_classificado():
    """O desfecho do ULTIMO run sai classificado por retomada.py."""
    tmp = tempfile.mkdtemp(prefix="reentrada-")
    try:
        grava_corrida(tmp, "motor-1", "max-rounds", None, "plano.json")
        grava_corrida(tmp, "motor-2", "porta-fechada", "suite do repo reprovou no lint", "plano.json")
        r = roda_bloco(tmp, "plano.json")
        assert r.returncode == 0, "bloco da skill falhou: %s" % r.stderr
        # o stdout traz o JSON do relance e depois o do classificador; o ultimo objeto e o veredito
        veredito = objetos(r.stdout)[-1]
        assert veredito["desfecho"] == "porta-fechada", veredito
        assert veredito["acao"] == CONSERTA, veredito
        assert veredito["causa"] == "suite do repo reprovou no lint", veredito
        assert veredito["evidencia"], veredito
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def caso_morta_por_fora():
    """Largada pendurada em em-curso/ = corrida morta por fora → conserta-e-relanca."""
    tmp = tempfile.mkdtemp(prefix="reentrada-")
    try:
        grava_corrida(tmp, "motor-1", "max-rounds", None, "plano.json")
        pend = os.path.join(tmp, ".claude", ".sprint", "em-curso")
        os.makedirs(pend, exist_ok=True)
        with open(os.path.join(pend, "motor-2.json"), "w", encoding="utf-8") as f:
            json.dump({"run_id": "motor-2", "missao": "plano.json", "total": 8, "inicio": 1}, f)
        r = roda_bloco(tmp, "plano.json")
        assert r.returncode == 0, "bloco da skill falhou: %s" % r.stderr
        veredito = objetos(r.stdout)[-1]
        assert veredito["desfecho"] == "morta-por-fora", veredito
        assert veredito["acao"] == CONSERTA, veredito
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def caso_causa_repetida_chama_o_dono():
    """A mesma causa em duas corridas seguidas: o relance sai 3 e a acao e do dono."""
    tmp = tempfile.mkdtemp(prefix="reentrada-")
    try:
        grava_corrida(tmp, "motor-1", "porta-fechada", "mesma pedra", "plano.json")
        grava_corrida(tmp, "motor-2", "porta-fechada", "mesma pedra", "plano.json")
        r = roda_bloco(tmp, "plano.json")
        assert r.returncode == 0, "bloco da skill falhou: %s" % r.stderr
        veredito = objetos(r.stdout)[-1]
        assert veredito["acao"] == DONO, veredito
        assert "PENDENCIA DO DONO" in r.stderr, r.stderr
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def caso_aponta_sem_copiar():
    """Os blocos do sprint sao apontados por titulo literal, nunca copiados."""
    md = open(SKILL, encoding="utf-8").read()
    sprint = open(SPRINT, encoding="utf-8").read()
    ponteiros = (
        "### O sinal que arma o gate (obrigatório, e é a PRIMEIRA coisa)",
        "A LARGADA vai para o disco",
        "2) NO RETORNO da chamada",
        "A PARADA vai para o disco",
    )
    for p in ponteiros:
        assert p in md, "a skill de reentrada nao aponta o bloco: %s" % p
        assert p in sprint, "ponteiro podre — o sprint nao tem mais o bloco: %s" % p
    # copiar o comando do sprint e o defeito que o ponteiro evita
    for marca in ("SPRINT_MOTOR_ID=", "registra-run", "andamento.py"):
        assert marca not in md, "a skill COPIOU um comando do sprint (%s) em vez de apontar" % marca
    # as tres acoes da lista fechada aparecem nomeadas
    for acao in (SEGUE, CONSERTA, DONO):
        assert acao in md, "a skill nao trata a acao %s" % acao


if __name__ == "__main__":
    casos = [caso_ultimo_run_classificado, caso_morta_por_fora,
             caso_causa_repetida_chama_o_dono, caso_aponta_sem_copiar]
    for caso in casos:
        caso()
        print("ok - %s" % caso.__name__)
    print("test_reentrada_skill: %d casos, tudo verde" % len(casos))
