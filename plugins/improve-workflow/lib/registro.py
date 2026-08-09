#!/usr/bin/env python3
"""registro.py — o histórico das rodadas, fora do projeto, para a rodada seguinte ler.

Sem histórico, todo número da autópsia é palpite de uma amostra: 3 turnos por
agente é muito ou pouco? Só o run anterior responde. E a pergunta que interessa
depois de um conserto — "melhorou no ponto que eu toquei?" — não existe sem os
dois lados.

Ele mora em `~/.claude/improve-workflow/registro.jsonl` (ou `$CLAUDE_CONFIG_DIR`),
NUNCA dentro do projeto: escrever no projeto quebraria a proibição que impede
esta skill de mexer na árvore que ela audita.

Uma linha por run, só os números — nunca conteúdo de transcript. Ficam as 50
rodadas mais novas: a gravação apaga o que passar disso.

    python3 registro.py gravar [<run>] [--conserto PAPEL:metrica:o que foi feito]
    python3 registro.py ler              # o histórico inteiro, em JSON

O `--conserto` é o que a rodada anterior propôs e alguém aplicou antes desta: ele
fica na linha com o número que mirava, e a rodada seguinte responde se aquele
número melhorou. Sem isso, "o conserto funcionou?" fica no palpite.
"""

import json
import os
import sys
import time

import medidor

RESUMO_PAPEL = ("papel", "agentes", "turnos", "turnos_por_agente", "taxa_falha", "suspeito")

# as métricas que um conserto pode mirar — em todas, menor é melhor
METRICAS = ("turnos_por_agente", "taxa_falha", "turnos", "agentes")

# quantas rodadas ficam no arquivo. A comparação usa a anterior, e a leitura humana
# olha as últimas; rodada de meio de ano não responde nenhuma pergunta e o arquivo
# cresce para sempre. As RETENCAO mais novas ficam, as mais velhas saem na gravação.
RETENCAO = 50


def caminho(base=None):
    """O arquivo do histórico. Fora do projeto, onde o estado da máquina mora."""
    raiz = base or (os.environ.get("CLAUDE_CONFIG_DIR")
                    or os.path.join(os.path.expanduser("~"), ".claude"))
    return os.path.join(raiz, "improve-workflow", "registro.jsonl")


def conserto_de_texto(texto):
    """`PAPEL:metrica:o que foi feito` → o conserto, ou (None, o motivo da recusa)."""
    partes = [p.strip() for p in texto.split(":", 2)]
    if len(partes) != 3 or not all(partes):
        return None, ("conserto mal formado: %r — use PAPEL:metrica:o que foi feito"
                      % texto)
    papel, metrica, o_que = partes
    if metrica not in METRICAS:
        return None, ("métrica desconhecida: %r — use uma de %s"
                      % (metrica, ", ".join(METRICAS)))
    return {"papel": papel.upper(), "metrica": metrica, "o_que": o_que}, None


def resumir(medida, consertos=None):
    """O que fica: os números por papel, a contagem de casos por sinal, e os
    consertos aplicados antes deste run — o lado 'o que eu mexi' da comparação."""
    return {
        "run": medida["run"],
        "quando": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total": medida["total"],
        "papeis": [{c: p[c] for c in RESUMO_PAPEL} for p in medida["papeis"]],
        "sinais": {s["sinal"]: len(s["casos"]) for s in medida["sinais"]},
        "consertos": list(consertos or []),
    }


def gravar(medida, base=None, consertos=None):
    caminho_arq = caminho(base)
    os.makedirs(os.path.dirname(caminho_arq), exist_ok=True)
    linha = resumir(medida, consertos)
    with open(caminho_arq, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    podar(caminho_arq)
    return linha


def podar(caminho_arq):
    """Deixa no arquivo só as RETENCAO rodadas mais novas. Reescreve por cima só
    quando sobrou linha a tirar — arquivo pequeno não é tocado."""
    with open(caminho_arq, encoding="utf-8") as f:
        linhas = f.readlines()
    if len(linhas) <= RETENCAO:
        return 0
    fora = len(linhas) - RETENCAO
    with open(caminho_arq, "w", encoding="utf-8") as f:
        f.writelines(linhas[fora:])
    return fora


def ler(base=None):
    """As rodadas gravadas, da mais antiga para a mais nova. Linha corrompida por
    escrita interrompida é pulada — histórico truncado vale mais que nenhum."""
    try:
        with open(caminho(base), encoding="utf-8") as f:
            linhas = f.readlines()
    except OSError:
        return []
    fora = []
    for linha in linhas:
        try:
            fora.append(json.loads(linha))
        except ValueError:
            continue
    return fora


def anterior(run, base=None):
    """A última rodada gravada que NÃO é esta — o lado de antes da comparação."""
    for r in reversed(ler(base)):
        if r["run"] != run:
            return r
    return None


def veredito(antes, depois):
    """Conserto a conserto, o número que ele mirava nos dois lados. Menor é melhor
    em toda métrica do registro, então a régua é uma só: caiu, melhorou."""
    velho = {p["papel"]: p for p in antes["papeis"]}
    novo = {p["papel"]: p for p in depois["papeis"]}
    fora = []
    for c in depois.get("consertos") or []:
        v, n = velho.get(c["papel"]), novo.get(c["papel"])
        if v is None or n is None:
            fora.append(dict(c, numero=[None, None], veredito="sem_medida"))
            continue
        a, d = v[c["metrica"]], n[c["metrica"]]
        if a is None or d is None:
            # lado sem medida (run sem journal não tem taxa_falha) não vira comparação
            fora.append(dict(c, numero=[a, d], veredito="sem_medida"))
            continue
        fora.append(dict(c, numero=[a, d],
                         veredito="melhorou" if d < a else
                                  "piorou" if d > a else "igual"))
    return fora


def comparar(antes, depois):
    """Papel a papel, o que mudou de uma rodada para a outra. `par_invertido` é o
    caso que só aparece no par: turno caiu e falha subiu — o motor deu menos
    voltas entregando menos."""
    velho = {p["papel"]: p for p in antes["papeis"]}
    papeis = []
    for p in depois["papeis"]:
        v = velho.get(p["papel"])
        if not v:
            continue
        papeis.append({
            "papel": p["papel"],
            "turnos_por_agente": [v["turnos_por_agente"], p["turnos_por_agente"]],
            "taxa_falha": [v["taxa_falha"], p["taxa_falha"]],
            "melhorou": p["turnos_por_agente"] < v["turnos_por_agente"],
        })
    return {
        "antes": antes["run"], "depois": depois["run"],
        "papeis": papeis,
        "consertos": veredito(antes, depois),
        "par_invertido": medidor.par_invertido(antes, depois),
        "tokens": [antes["total"]["tokens"], depois["total"]["tokens"]],
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv else "ler"
    if cmd == "ler":
        print(json.dumps(ler(), ensure_ascii=False, indent=2))
        return 0
    if cmd != "gravar":
        print("uso: registro.py [gravar <run> [--conserto PAPEL:metrica:o que foi feito] | ler]",
              file=sys.stderr)
        return 2
    consertos, resto = [], []
    while argv:
        a = argv.pop(0)
        if a == "--conserto":
            if not argv:
                print("--conserto sem valor", file=sys.stderr)
                return 2
            c, erro = conserto_de_texto(argv.pop(0))
            if erro:
                print(erro, file=sys.stderr)
                return 2
            consertos.append(c)
        else:
            resto.append(a)
    dir_run, erro = medidor.resolver_run(resto[0] if resto else None)
    if erro:
        print(erro, file=sys.stderr)
        return 2
    medida = medidor.medir_run(dir_run)
    antes = anterior(medida["run"])
    linha = gravar(medida, consertos=consertos)
    saida = {"gravado": linha, "em": caminho()}
    if antes:
        saida["contra_a_anterior"] = comparar(antes, linha)
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
