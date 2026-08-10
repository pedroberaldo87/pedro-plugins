#!/usr/bin/env python3
"""Bancada do registro.py: duas rodadas seguidas, e a segunda lê a primeira.

O que se prova aqui, e cada item já custou trabalho perdido:
  - o arquivo nasce FORA da árvore do projeto (a proibição de escrever no projeto);
  - a rodada 2 encontra a rodada 1 no disco e compara papel a papel;
  - o par turno×falha invertido sobrevive à ida e volta pelo disco.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import medidor  # noqa: E402
import registro  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.dirname(AQUI)))
FIXTURES = os.path.join(os.path.dirname(AQUI), "fixtures")
RUN_ANTES = os.path.join(FIXTURES, "run-par-antes")
RUN_DEPOIS = os.path.join(FIXTURES, "run-par-depois")

FALHAS = []


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def caso_fora_do_projeto():
    print("\nO registro mora fora do projeto")
    casa = tempfile.mkdtemp()
    try:
        alvo = registro.caminho(casa)
        check("o arquivo fica sob a raiz de config, não no projeto",
              alvo.startswith(casa) and not alvo.startswith(RAIZ_PROJETO + os.sep))
        registro.gravar(medidor.medir_run(RUN_ANTES), base=casa)
        check("o arquivo foi criado no disco", os.path.isfile(alvo))
        check("nenhum arquivo do registro apareceu na árvore do projeto",
              not os.path.exists(os.path.join(RAIZ_PROJETO, "improve-workflow")))
        with open(alvo, encoding="utf-8") as f:
            linha = json.loads(f.readline())
        check("a linha guarda número, e não conteúdo de transcript",
              set(linha) == {"run", "quando", "total", "papeis", "sinais", "consertos"})
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def caso_duas_rodadas():
    print("\nDuas rodadas: a segunda lê a primeira e compara")
    casa = tempfile.mkdtemp()
    try:
        r1 = registro.gravar(medidor.medir_run(RUN_ANTES), base=casa)
        # rodada 2: só o que está no DISCO vale como lado de antes
        antes = registro.anterior("run-par-depois", base=casa)
        check("a rodada seguinte acha a anterior no disco",
              antes is not None and antes["run"] == r1["run"])
        r2 = registro.gravar(medidor.medir_run(RUN_DEPOIS), base=casa)
        check("o histórico acumula as duas", len(registro.ler(base=casa)) == 2)
        check("a rodada não se acha como sua própria anterior",
              registro.anterior(r1["run"], base=casa)["run"] == r2["run"])

        c = registro.comparar(antes, r2)
        check("a comparação nomeia os dois runs",
              c["antes"] == "run-par-antes" and c["depois"] == "run-par-depois")
        papel = c["papeis"][0]
        check("o turno por agente caiu de 3.0 para 1.0",
              papel["papel"] == "EXECUTOR" and papel["turnos_por_agente"] == [3.0, 1.0])
        check("o par invertido sobrevive à ida e volta pelo disco",
              [x["papel"] for x in c["par_invertido"]] == ["EXECUTOR"])
        check("o gasto dos dois lados aparece", c["tokens"] == [6780, 2260])
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def caso_conserto_funcionou():
    print("\nO conserto aplicado entre as duas rodadas: funcionou ou não")
    casa = tempfile.mkdtemp()
    try:
        r1 = registro.gravar(medidor.medir_run(RUN_ANTES), base=casa)
        r2 = registro.gravar(
            medidor.medir_run(RUN_DEPOIS), base=casa,
            consertos=[
                {"papel": "EXECUTOR", "metrica": "turnos_por_agente",
                 "o_que": "teto de 1 turno por executor"},
                {"papel": "EXECUTOR", "metrica": "taxa_falha",
                 "o_que": "reentrega automática em falha"},
                {"papel": "REVISOR", "metrica": "turnos",
                 "o_que": "papel que não apareceu nas duas rodadas"},
            ])
        v = registro.comparar(r1, r2)["consertos"]
        check("cada conserto aplicado é nomeado na rodada",
              [c["o_que"] for c in v] == ["teto de 1 turno por executor",
                                          "reentrega automática em falha",
                                          "papel que não apareceu nas duas rodadas"])
        check("o conserto que mirou turno por agente melhorou, com os dois números",
              v[0]["veredito"] == "melhorou" and v[0]["numero"] == [3.0, 1.0])
        check("o conserto que mirou a taxa de falha piorou",
              v[1]["veredito"] == "piorou" and v[1]["numero"][1] > v[1]["numero"][0])
        check("conserto sobre papel ausente de um dos lados fica sem medida",
              v[2]["veredito"] == "sem_medida")
        check("rodada sem conserto anotado não inventa veredito",
              registro.comparar(r2, r1)["consertos"] == [])
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def caso_conserto_sem_numero_dos_dois_lados():
    print("\nO conserto mirou uma métrica que nenhum dos dois lados mediu")
    casa = tempfile.mkdtemp()
    try:
        r1 = registro.gravar(medidor.medir_run(os.path.join(FIXTURES, "run-sao")),
                             base=casa)
        r2 = registro.gravar(
            medidor.medir_run(os.path.join(FIXTURES, "run-fantasma")), base=casa,
            consertos=[{"papel": "EXECUTOR", "metrica": "taxa_falha",
                        "o_que": "teto de reentrega"}])
        v = registro.comparar(r1, r2)["consertos"]
        check("métrica sem número dos dois lados fica sem medida, não estoura",
              [c["veredito"] for c in v] == ["sem_medida"]
              and v[0]["numero"] == [None, None])
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def caso_conserto_mal_formado():
    print("\nConserto escrito errado é recusado, não gravado torto")
    for texto in ("EXECUTOR:turnos_por_agente", "EXECUTOR:inventada:x", "::x"):
        c, erro = registro.conserto_de_texto(texto)
        check("recusa %r com motivo" % texto, c is None and bool(erro))
    c, erro = registro.conserto_de_texto(" executor : taxa_falha : dois pontos: no meio ")
    check("aceita o formato certo e normaliza o papel",
          erro is None and c == {"papel": "EXECUTOR", "metrica": "taxa_falha",
                                 "o_que": "dois pontos: no meio"})


def caso_sem_historico():
    print("\nPrimeira rodada da vida")
    casa = tempfile.mkdtemp()
    try:
        check("histórico inexistente lê como lista vazia", registro.ler(base=casa) == [])
        check("sem anterior, a comparação não existe",
              registro.anterior("run-par-antes", base=casa) is None)
        os.makedirs(os.path.dirname(registro.caminho(casa)))
        check("diretório sem o arquivo também lê vazio", registro.ler(base=casa) == [])
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def caso_linha_corrompida():
    print("\nEscrita interrompida no meio")
    casa = tempfile.mkdtemp()
    try:
        registro.gravar(medidor.medir_run(RUN_ANTES), base=casa)
        with open(registro.caminho(casa), "a", encoding="utf-8") as f:
            f.write('{"run": "run-cor')
        check("a linha cortada é pulada e o resto fica de pé",
              [r["run"] for r in registro.ler(base=casa)] == ["run-par-antes"])
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def caso_retencao():
    print("\nA retenção: o que sai e o que fica")
    casa = tempfile.mkdtemp()
    try:
        alvo = registro.caminho(casa)
        os.makedirs(os.path.dirname(alvo))
        with open(alvo, "w", encoding="utf-8") as f:
            for i in range(registro.RETENCAO + 3):
                f.write(json.dumps({"run": "velho-%d" % i}) + "\n")
        nova = registro.gravar(medidor.medir_run(RUN_ANTES), base=casa)
        runs = [r["run"] for r in registro.ler(base=casa)]
        check("o arquivo para de crescer no teto", len(runs) == registro.RETENCAO)
        check("a rodada recém-gravada fica", runs[-1] == nova["run"])
        check("as mais velhas saem, as mais novas ficam",
              runs[0] == "velho-4" and "velho-3" not in runs)
        check("abaixo do teto nada é podado", registro.podar(alvo) == 0)
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def caso_cli():
    print("\nPela linha de comando, duas vezes")
    casa = tempfile.mkdtemp()
    env = dict(os.environ, CLAUDE_CONFIG_DIR=casa)
    try:
        um = subprocess.run([sys.executable, os.path.join(AQUI, "registro.py"),
                             "gravar", RUN_ANTES],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                            stdin=subprocess.DEVNULL, start_new_session=True)
        dois = subprocess.run([sys.executable, os.path.join(AQUI, "registro.py"),
                               "gravar", RUN_DEPOIS,
                               "--conserto", "EXECUTOR:turnos_por_agente:teto de 1 turno"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                              stdin=subprocess.DEVNULL, start_new_session=True)
        check("as duas rodadas saem com sucesso",
              um.returncode == 0 and dois.returncode == 0)
        s = json.loads(dois.stdout)
        check("a segunda rodada compara contra a primeira",
              s.get("contra_a_anterior", {}).get("antes") == "run-par-antes")
        check("a segunda rodada diz que o conserto anotado funcionou",
              [(c["o_que"], c["veredito"]) for c in s["contra_a_anterior"]["consertos"]]
              == [("teto de 1 turno", "melhorou")])
        check("a segunda rodada acusa o par invertido",
              [x["papel"] for x in s["contra_a_anterior"]["par_invertido"]] == ["EXECUTOR"])
        lido = subprocess.run([sys.executable, os.path.join(AQUI, "registro.py"), "ler"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                              stdin=subprocess.DEVNULL, start_new_session=True)
        check("`ler` devolve as duas rodadas gravadas",
              [r["run"] for r in json.loads(lido.stdout)] == ["run-par-antes", "run-par-depois"])
    finally:
        shutil.rmtree(casa, ignore_errors=True)


def main():
    caso_fora_do_projeto()
    caso_duas_rodadas()
    caso_conserto_funcionou()
    caso_conserto_sem_numero_dos_dois_lados()
    caso_conserto_mal_formado()
    caso_sem_historico()
    caso_linha_corrompida()
    caso_retencao()
    caso_cli()
    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
