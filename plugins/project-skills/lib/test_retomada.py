#!/usr/bin/env python3
"""Suite da retomada: inventario (F23.1), classificador (F23.2), lista fechada do dono (F23.5),
rito manual sem o /goal (F23.8) · R-33.

O que prova: a lista DESFECHOS — o que o programa da retomada sabe fazer quando um
run para — cobre TODO stopReason que o motor.js do /sprint pode emitir. A lista de
verdade nao e uma copia em prosa: sai do proprio motor.js, lido aqui, e e o conjunto
dos valores que `desligadoPor` recebe mais os literais da linha do `stopReason`.

Reprova nos dois lados: desfecho novo no motor sem entrada aqui (quem retoma nao
saberia o que fazer) e entrada aqui que o motor nao emite mais (lista podre).

Roda com: python3 lib/test_retomada.py
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
MOTOR = os.path.join(os.path.dirname(AQUI), "skills", "sprint", "references", "motor.js")
SKILL = os.path.join(os.path.dirname(AQUI), "skills", "sprint", "SKILL.md")

sys.path.insert(0, AQUI)
from retomada import DESFECHOS, SEGUE, CONSERTA, DONO, classifica  # noqa: E402

RETOMADA = os.path.join(AQUI, "retomada.py")


def do_motor():
    """O conjunto REAL de stopReason que o motor.js emite."""
    js = open(MOTOR, encoding="utf-8").read()
    # Os valores atribuidos a desligadoPor (o `===` das comparacoes nao casa com `=\s*'`).
    causas = set(re.findall(r"desligadoPor\s*=\s*'([^']+)'", js))
    # Os literais do fallback, na linha que monta o campo.
    linha = [ln for ln in js.splitlines() if "stopReason:" in ln]
    if len(linha) != 1:
        raise AssertionError("esperava UMA linha com stopReason: no motor.js, achei %d" % len(linha))
    literais = set(re.findall(r"'([^']+)'", linha[0]))
    if not causas or not literais:
        raise AssertionError("leitura do motor.js voltou vazia — o formato mudou")
    return causas | literais


# Tres saidas de run no formato que o motor.js devolve (o objeto do `return` do fim da
# corrida), pares (acao esperada, run). Os textos de `blockers` sao os literais que o
# motor empurra nas linhas de `porta-fechada`, `reserva` e no fecho por teto de rodadas.
# Nenhum stopReason espera DONO: desde F23.5 o dono so se chama por caso declarado.
FIXTURES = [
    (SEGUE, {
        "rounds": [{"r": 1}, {"r": 2}],
        "built": False,
        "blockers": [],
        "progresso": {"feitos": 3, "passos": ["F1.1", "F1.2", "F1.3"]},
        "impedidos": [], "naoDeuTempo": ["F1.4"], "esperandoVoce": [],
        "gasto": 812345,
        "stopReason": "max-rounds",
    }),
    (CONSERTA, {
        "rounds": [{"r": 1}],
        "built": False,
        "blockers": [{"what": "a porta do repositorio esta fechada: suite vermelha",
                      "whyNeedsYou": "nenhuma onda sai com a porta fechada — todo trabalho novo morreria nela. "
                                     "Prova:\nFAILED lib/test_journal.py::test_ledger — 1 failed, 373 passed"}],
        "progresso": {"feitos": 0, "passos": []},
        "impedidos": [], "naoDeuTempo": [], "esperandoVoce": [],
        "gasto": 41000,
        "stopReason": "porta-fechada",
    }),
    (SEGUE, {
        "rounds": [],
        "built": False,
        "blockers": [{"what": "outro motor desta sessao ja reservou: <raiz>/lib/plan_state.py",
                      "whyNeedsYou": "dois motores no mesmo arquivo e um apagando o trabalho do outro — "
                                     "espere o outro terminar (ele libera ao sair) ou recorte a missao"}],
        "progresso": {"feitos": 0, "passos": []},
        "impedidos": [], "naoDeuTempo": [], "esperandoVoce": [],
        "gasto": 9000,
        "stopReason": "reserva",
    }),
]


def tres_caminhos():
    """Roda `retomada.py --run <saida>` numa fixture de cada caminho."""
    falhas = []
    tmp = tempfile.mkdtemp(prefix="retomada-")
    for esperada, run in FIXTURES:
        alvo = os.path.join(tmp, "%s.json" % run["stopReason"])
        with open(alvo, "w", encoding="utf-8") as fh:
            json.dump(run, fh, ensure_ascii=False)
        # `text=True` sem `encoding` decodifica com o encoding do LOCAL — cp1252 no
        # Windows —, e a evidencia do blocker (que tem travessao) voltava mordida:
        # a suite reprovava o programa por causa da leitura dela. Medido no run
        # 32326701424 (windows-latest): "porta-fechada nao trouxe a evidencia".
        p = subprocess.run([sys.executable, RETOMADA, "--run", alvo],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, start_new_session=True)
        if p.returncode != 0:
            falhas.append("--run %s saiu %d: %s" % (alvo, p.returncode, p.stderr.strip()))
            continue
        try:
            saida = json.loads(p.stdout)
        except ValueError:
            falhas.append("--run %s nao devolveu JSON: %r" % (alvo, p.stdout[:120]))
            continue
        if sorted(saida) != ["acao", "causa", "desfecho", "evidencia"]:
            falhas.append("campos errados para %s: %s" % (run["stopReason"], sorted(saida)))
            continue
        if saida["acao"] != esperada:
            falhas.append("%s deu acao %r, esperava %r" % (run["stopReason"], saida["acao"], esperada))
        if saida["desfecho"] != run["stopReason"]:
            falhas.append("%s devolveu desfecho %r" % (run["stopReason"], saida["desfecho"]))
        blk = run["blockers"]
        if blk:
            if saida["causa"] != blk[-1]["what"]:
                falhas.append("%s nao trouxe a causa do blocker: %r" % (run["stopReason"], saida["causa"]))
            if saida["evidencia"] != blk[-1]["whyNeedsYou"]:
                falhas.append("%s nao trouxe a evidencia do blocker" % run["stopReason"])
        elif not saida["causa"].strip() or not saida["evidencia"].strip():
            falhas.append("%s sem blocker deixou causa/evidencia vazia" % run["stopReason"])
    # O pronto do F23.5 e literal: espera-dono SO para os quatro casos, e o de fora
    # o LACO decide — desconhecido cai em conserta (investigar a causa), nunca no dono.
    saida = classifica({"stopReason": "desfecho-que-ninguem-viu"})
    if saida["acao"] == DONO:
        falhas.append("stopReason desconhecido chamou o dono — a lista fechada vazou")
    if saida["acao"] != CONSERTA:
        falhas.append("stopReason desconhecido nao caiu em conserta (investigar antes de relancar)")
    shutil.rmtree(tmp, ignore_errors=True)
    return falhas


def sem_goal(md=None):
    """F23.8: sem o /goal nativo na maquina, a SKILL.md do sprint nao pode fingir que
    vigia — ou entrega o rito manual, declarando a ausencia em voz alta (na largada e
    no relatorio), ou reprova aqui. Le a SKILL.md real, nunca uma copia."""
    falhas = []
    if md is None:
        md = open(SKILL, encoding="utf-8").read()
    pos = md.find("GOAL AUSENTE")
    if pos < 0:
        return ["a SKILL.md do sprint nao trata o caso do /goal ausente na maquina — "
                "a vigilia finge que roda"]
    trecho = md[pos:pos + 1500]
    # A declaracao em voz alta, nos dois momentos.
    for token, falta in [
        ("DECLARE", "a ausencia do goal nao e declarada em voz alta"),
        ("largada", "a ausencia nao e declarada na largada"),
        ("relatório", "a ausencia nao e declarada no relatorio"),
        ("Silenciar", "o trecho nao proibe silenciar a ausencia"),
    ]:
        if token not in trecho:
            falhas.append("%s (falta %r no trecho do goal ausente)" % (falta, token))
    # O rito manual, com os seis passos NA ORDEM do laco.
    rito = ["investigar", "prova de comando", "desafiador", "conserto",
            "ledger", "relançar"]
    anterior = -1
    for passo in rito:
        i = trecho.find(passo)
        if i < 0:
            falhas.append("o rito manual nao entrega o passo %r" % passo)
        elif i < anterior:
            falhas.append("o passo %r do rito manual esta fora de ordem" % passo)
        else:
            anterior = i
    return falhas


def main():
    emitidos = do_motor()
    falhas = []

    faltando = sorted(emitidos - set(DESFECHOS))
    if faltando:
        falhas.append("o motor emite e a lista nao cobre: %s" % ", ".join(faltando))

    sobrando = sorted(set(DESFECHOS) - emitidos)
    if sobrando:
        falhas.append("a lista tem desfecho que o motor nao emite mais: %s" % ", ".join(sobrando))

    vazios = sorted(k for k, v in DESFECHOS.items() if not str(v[1]).strip())
    if vazios:
        falhas.append("desfecho sem o que fazer na retomada: %s" % ", ".join(vazios))

    acoes = {a for a, _ in DESFECHOS.values()}
    if acoes - {SEGUE, CONSERTA, DONO}:
        falhas.append("acao fora das tres: %s" % ", ".join(sorted(acoes - {SEGUE, CONSERTA, DONO})))

    falhas += tres_caminhos()
    falhas += sem_goal()

    for f in falhas:
        print("FALHA: %s" % f)
    if falhas:
        print("FALHOU: %d" % len(falhas))
        return 1
    print("OK: retomada (%d desfechos do motor.js cobertos: %s)"
          % (len(emitidos), ", ".join(sorted(emitidos))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
