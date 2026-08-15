#!/usr/bin/env python3
"""Suite do ledger_corridas.py (F24.1 · R-34).

O que prova: duas corridas de mentira viram DUAS entradas, cada uma com os campos
exigidos, e a segunda nao apaga a primeira.

Roda com: python3 lib/test_ledger_corridas.py
Sem framework: __main__ com asserts, sai !=0 se falhar.
"""
import os
import tempfile
import time

import ledger_corridas

CORRIDA_1 = {
    "run_id": "run-001",
    "missao": "plano-da-noite",
    "progresso": {"fechadas": 3, "total": 40},
    "custo": {"tokens": 120000},
    "tempo": {"inicio": 1000, "fim": 2800},
    "desfecho": "teto-de-rodadas",
}
CORRIDA_2 = {
    "run_id": "run-002",
    "missao": "plano-da-noite",
    "progresso": {"fechadas": 11, "total": 40},
    "custo": {"tokens": 340000},
    "tempo": {"inicio": 3000, "fim": 9000},
    "desfecho": "completo",
}


# O retorno REAL do motor, no formato que a casca recebe do Workflow.
RETORNO_DO_MOTOR = {
    "built": True,
    "progresso": {"feitos": 7, "passos": ["F1", "F2"]},
    "gasto": 412000,
    "stopReason": "build-complete",
    "blockers": [],
}


def prova_do_run(raiz):
    """F24.2 — a entrada SAI do resultado do run, e vazio reprova."""
    falhas = []
    entrada = ledger_corridas.do_run(RETORNO_DO_MOTOR, run_id="wf_abc",
                                     missao="plano-da-noite", total=40,
                                     inicio=5000, fim=9000)
    esperado = {
        "progresso": ({"fechadas": 7, "total": 40}, "progresso.feitos do motor"),
        "custo": ({"tokens": 412000}, "gasto do motor"),
        "tempo": ({"inicio": 5000, "fim": 9000}, "relogio da casca"),
        "desfecho": ("build-complete", "stopReason do motor"),
    }
    for campo, (valor, origem) in esperado.items():
        if entrada.get(campo) != valor:
            falhas.append("%s nao saiu do run (%s): %r" % (campo, origem, entrada.get(campo)))

    gravada = ledger_corridas.registra(raiz, entrada)
    if gravada["desfecho"] != "build-complete":
        falhas.append("a entrada gravada nao carrega o desfecho do run")

    # Campo obrigatorio vazio: o motor que nao mediu (sem `gasto`, sem `stopReason`)
    # e a casca que nao soube o tamanho da fila (`total` None) reprovam, nunca gravam.
    for rotulo, kwargs, resultado in (
        ("stopReason ausente", {}, dict(RETORNO_DO_MOTOR, stopReason=None)),
        ("gasto ausente", {}, dict(RETORNO_DO_MOTOR, gasto=None)),
        ("progresso ausente", {}, dict(RETORNO_DO_MOTOR, progresso={})),
        ("total desconhecido", {"total": None}, RETORNO_DO_MOTOR),
        ("run_id vazio", {"run_id": ""}, RETORNO_DO_MOTOR),
    ):
        base = dict(run_id="wf_abc", missao="plano-da-noite", total=40, inicio=5000)
        base.update(kwargs)
        try:
            ledger_corridas.registra(raiz, ledger_corridas.do_run(resultado, **base))
            falhas.append("%s deveria reprovar, gravou" % rotulo)
        except ValueError:
            pass

    # Zero passo fechado é medição legítima — não pode ser confundido com ausência.
    magra = ledger_corridas.do_run(dict(RETORNO_DO_MOTOR, progresso={"feitos": 0}),
                                   run_id="wf_zero", missao="m", total=40, inicio=1)
    try:
        ledger_corridas.registra(raiz, magra)
    except ValueError as e:
        falhas.append("corrida com 0 passos fechados foi tratada como vazia: %s" % e)
    return falhas


def prova_morta_por_fora(raiz):
    """F24.3 — corrida SEM retorno (sessao estourada, processo morto) deixa linha."""
    falhas = []
    ledger_corridas.abre(raiz, run_id="wf_morta", missao="plano-da-noite",
                         total=40, inicio=1000)

    # Ainda dentro do teto: pode estar viva, ninguem declara morte.
    if ledger_corridas.colhe_orfas(raiz):
        falhas.append("corrida recem-largada foi dada como morta")

    # A chamada nunca voltou: nenhum bloco de retorno rodou, so o tempo passou.
    largada = os.path.join(ledger_corridas.dir_largadas(raiz), "wf_morta.json")
    velho = time.time() - ledger_corridas.TETO_SEM_SINAL - 60
    os.utime(largada, (velho, velho))

    entradas = [e for e in ledger_corridas.le(raiz) if e["run_id"] == "wf_morta"]
    if len(entradas) != 1:
        falhas.append("corrida morta por fora nao deixou linha (%d entradas)" % len(entradas))
    else:
        e = entradas[0]
        if e["desfecho"] != "morta-por-fora":
            falhas.append("linha sem o desfecho que houve: %r" % e["desfecho"])
        if e["missao"] != "plano-da-noite" or e["progresso"]["total"] != 40:
            falhas.append("a linha perdeu a identidade da largada: %r" % e)
        if e["progresso"]["fechadas"] != ledger_corridas.NAO_MEDIDO:
            falhas.append("o que ninguem mediu virou numero inventado: %r" % e["progresso"])
        if e["tempo"]["fim"] < e["tempo"]["inicio"]:
            falhas.append("fim anterior ao inicio: %r" % e["tempo"])

    # Colhida uma vez, colhida para sempre: nao duplica a cada leitura.
    if len([x for x in ledger_corridas.le(raiz) if x["run_id"] == "wf_morta"]) != 1:
        falhas.append("a corrida morta virou duas linhas na leitura seguinte")

    # Marca de largada ilegivel (processo morto no meio da escrita, disco cheio) e da
    # MESMA familia de falhas que esta colheita cobre: se ela estourasse, a leitura
    # inteira do ledger cairia junto e "nunca ausente" viraria "todas ausentes".
    lixo = os.path.join(ledger_corridas.dir_largadas(raiz), "wf_truncada.json")
    with open(lixo, "w", encoding="utf-8") as f:
        f.write('{"run_id": "wf_trunc')
    velho2 = time.time() - ledger_corridas.TETO_SEM_SINAL - 60
    os.utime(lixo, (velho2, velho2))
    try:
        depois = ledger_corridas.le(raiz)
    except Exception as e:
        falhas.append("marca ilegivel derrubou a leitura inteira: %r" % e)
        depois = []
    if not any(x["run_id"] == "wf_morta" for x in depois):
        falhas.append("as linhas boas sumiram junto com a marca ilegivel")
    if not any(x["desfecho"] == "morta-por-fora" and x["run_id"] == "wf_truncada"
               for x in depois):
        falhas.append("a marca ilegivel nao virou linha pelo nome do arquivo")

    # Quem VOLTOU nao vira orfa: o registra-run solta a largada.
    ledger_corridas.abre(raiz, run_id="wf_viva", missao="m", total=40, inicio=1)
    ledger_corridas.registra(raiz, ledger_corridas.do_run(
        RETORNO_DO_MOTOR, run_id="wf_viva", missao="m", total=40, inicio=1))
    ledger_corridas._solta_largada(raiz, "wf_viva")
    if ledger_corridas.colhe_orfas(raiz, agora=time.time() + 10 * ledger_corridas.TETO_SEM_SINAL):
        falhas.append("corrida que voltou foi colhida como morta — linha em dobro")
    return falhas


def prova_serie():
    """F24.4 — serie de TRES corridas: progresso por run e custo por passo fechado.

    A serie e alimentada por `do_run`, o UNICO ponto onde o formato do motor entra:
    montar as entradas a mao aqui codificaria a semantica que a implementacao supoe,
    e a suite passaria a confirmar a suposicao em vez de medi-la. `progresso.feitos`
    do motor e o que AQUELA corrida fechou (a lista de rodadas nasce vazia a cada
    chamada), e e por isso que a corrida de ZERO passos e a que acende `girou`.
    """
    falhas = []
    with tempfile.TemporaryDirectory() as raiz:
        for run_id, feitos, gasto, desfecho in (
            ("s1", 3, 120000, "teto"),          # fechou 3, 40k por passo
            ("s2", 0, 300000, "teto"),          # queimou 300k e nao fechou nada: girou
            ("s3", 3, 150000, "build-complete"),  # voltou a andar: acumulado sobe
        ):
            ledger_corridas.registra(raiz, ledger_corridas.do_run(
                {"progresso": {"feitos": feitos}, "gasto": gasto,
                 "stopReason": desfecho},
                run_id=run_id, missao="m", total=40, inicio=1, fim=2))
        # morta por fora: nada medido, e nada inventado
        ledger_corridas.registra(raiz, {
            "run_id": "s4", "missao": "m",
            "progresso": {"fechadas": ledger_corridas.NAO_MEDIDO, "total": 40},
            "custo": {"tokens": ledger_corridas.NAO_MEDIDO},
            "tempo": {"inicio": 5, "fim": 6}, "desfecho": "morta-por-fora"})

        s = ledger_corridas.serie(raiz)
        if len(s) != 4:
            return ["a serie perdeu corrida: %d de 4" % len(s)]
        N = ledger_corridas.NAO_MEDIDO
        esperado = [
            ("s1", {"fechadas": 3, "total": 40, "acumulado": 3,
                    "custo_por_passo": 40000.0, "girou": False}),
            # o caso que a serie existe para pegar: gastou e nao moveu
            ("s2", {"fechadas": 0, "total": 40, "acumulado": 3,
                    "custo_por_passo": N, "girou": True}),
            ("s3", {"fechadas": 3, "total": 40, "acumulado": 6,
                    "custo_por_passo": 50000.0, "girou": False}),
            ("s4", {"fechadas": N, "total": 40, "acumulado": 6,
                    "custo_por_passo": N, "girou": N}),
        ]
        for (run_id, campos), linha in zip(esperado, s):
            if linha["run_id"] != run_id:
                falhas.append("ordem da serie trocada: %r" % linha["run_id"])
            for k, v in campos.items():
                if linha.get(k) != v:
                    falhas.append("%s.%s: esperava %r, veio %r" % (run_id, k, v, linha.get(k)))

        # A corrida que passa do teto e VOLTA tem duas linhas no arquivo: a
        # `morta-por-fora` que a colheita gravou enquanto ela ainda rodava, e a real
        # do retorno. A serie fica com a real — contar as duas e contar a mesma
        # corrida duas vezes, e o acumulado da missao passa a mentir.
        ledger_corridas.registra(raiz, {
            "run_id": "s5", "missao": "m",
            "progresso": {"fechadas": ledger_corridas.NAO_MEDIDO, "total": 40},
            "custo": {"tokens": ledger_corridas.NAO_MEDIDO},
            "tempo": {"inicio": 9, "fim": 10}, "desfecho": "morta-por-fora"})
        ledger_corridas.registra(raiz, ledger_corridas.do_run(
            {"progresso": {"feitos": 2}, "gasto": 90000, "stopReason": "teto"},
            run_id="s5", missao="m", total=40, inicio=9, fim=11))
        linhas_s5 = [x for x in ledger_corridas.serie(raiz, missao="m")
                     if x["run_id"] == "s5"]
        if len(linhas_s5) != 1:
            falhas.append("a corrida que voltou depois do teto virou %d linhas na serie"
                          % len(linhas_s5))
        elif linhas_s5[0]["desfecho"] == "morta-por-fora":
            falhas.append("a serie ficou com a linha da morte, nao com a real")
        elif linhas_s5[0]["acumulado"] != 8:
            falhas.append("o acumulado nao contou a corrida que voltou: %r"
                          % linhas_s5[0]["acumulado"])

        # filtro por missao: outra missao nao entra na comparacao
        ledger_corridas.registra(raiz, {
            "run_id": "outro", "missao": "z", "progresso": {"fechadas": 9, "total": 9},
            "custo": {"tokens": 10}, "tempo": {"inicio": 7, "fim": 8}, "desfecho": "completo"})
        if [x["run_id"] for x in ledger_corridas.serie(raiz, missao="m")] \
                != ["s1", "s2", "s3", "s4", "s5"]:
            falhas.append("o filtro por missao deixou corrida de outra missao entrar")
    return falhas


def main():
    falhas = []
    with tempfile.TemporaryDirectory() as raiz:
        assert ledger_corridas.le(raiz) == [], "ledger inexistente deveria ler vazio"

        ledger_corridas.registra(raiz, CORRIDA_1)
        ledger_corridas.registra(raiz, CORRIDA_2)
        entradas = ledger_corridas.le(raiz)

        if len(entradas) != 2:
            falhas.append("esperava 2 entradas, veio %d — a segunda sobrescreveu?"
                          % len(entradas))
        elif [e["run_id"] for e in entradas] != ["run-001", "run-002"]:
            falhas.append("ordem/identidade erradas: %s"
                          % [e["run_id"] for e in entradas])

        for e in entradas:
            vazios = [c for c in ledger_corridas.CAMPOS if not e.get(c)]
            if vazios:
                falhas.append("entrada %s sem campos %s" % (e.get("run_id"), vazios))
            if not e.get("gravado_em"):
                falhas.append("entrada %s sem carimbo de gravacao" % e.get("run_id"))

        if entradas and entradas[0]["progresso"]["fechadas"] != 3:
            falhas.append("a primeira entrada foi adulterada pela segunda")

        try:
            ledger_corridas.registra(raiz, dict(CORRIDA_1, desfecho=""))
            falhas.append("desfecho vazio deveria reprovar, passou")
        except ValueError:
            pass

        falhas += prova_do_run(raiz)
        falhas += prova_morta_por_fora(raiz)

    falhas += prova_serie()

    for f in falhas:
        print("FALHA: %s" % f)
    print("FALHOU: %d" % len(falhas) if falhas else "OK: ledger_corridas (2 corridas, 2 entradas)")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
