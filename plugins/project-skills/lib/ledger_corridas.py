#!/usr/bin/env python3
"""ledger_corridas.py — uma linha por corrida, no projeto (F24.1 · R-34).

O que hoje só existe na memória da sessão passa a existir em disco: cada run do
motor deixa UMA entrada, append-only, num arquivo por projeto. Append-only porque
a pergunta que o ledger existe para responder é de SÉRIE ("a missão avança ou gira
em falso?") — reescrever a entrada anterior apaga justamente a comparação.

Casa: <projeto>/.claude/.sprint/corridas.jsonl  (registro de trabalho, fora do git —
F24.6 declara a casa no contrato de pastas).

CLI:
  ledger_corridas.py registra --project-root D --json -   # entrada por stdin
  ledger_corridas.py le       --project-root D            # imprime as entradas

  # F24.2 — quem escreve é o programa, com o resultado REAL do run:
  ledger_corridas.py registra-run --project-root D --run-id X --missao Y \\
                     --total N --inicio EPOCH --json -   # o retorno do motor por stdin

  # F24.3 — a largada fica em disco ANTES da chamada; corrida que não volta
  # (limite de sessão, processo morto, canal caído) vira linha na próxima leitura:
  ledger_corridas.py abre  --project-root D --run-id X --missao Y --total N --inicio EPOCH
  ledger_corridas.py colhe --project-root D

  # F24.4 — a série lida: progresso por corrida e custo por passo fechado.
  ledger_corridas.py serie --project-root D [--missao Y]

  # F24.5 — antes de relançar: causa que já parou duas vezes sai 3 (pendência do dono).
  ledger_corridas.py relance --project-root D --missao Y
"""
import argparse
import json
import os
import sys
import time

for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

# Os cinco eixos que a série precisa para comparar duas corridas.
CAMPOS = (
    "run_id",       # identidade — quem foi esta corrida
    "missao",       # identidade — o plano/objetivo que ela servia
    "progresso",    # {"fechadas": n, "total": n}
    "custo",        # {"tokens": n}
    "tempo",        # {"inicio": epoch, "fim": epoch}
    "desfecho",     # como terminou: "completo", "teto", "morta-por-fora", ...
)


# Corrida sem sinal de vida por mais que isto está morta, não lenta — é o mesmo teto
# da reserva de arquivos do sprint.
# ponytail: teto de relógio, não handshake; se um dia houver sprint de >12h, o critério
# vira "o motor ainda está no registro do andamento".
TETO_SEM_SINAL = 12 * 3600
NAO_MEDIDO = "nao-medido"

# Desfecho que diz "a corrida terminou o que foi fazer". Todo o resto é uma PARADA —
# a corrida esbarrou em alguma coisa, e é essa coisa que o relance conta.
# ponytail: lista curta de fim limpo em vez de catálogo de causas; se o motor passar a
# devolver outro nome para "acabou", ele entra aqui.
FIM_LIMPO = ("completo", "build-complete")


def caminho(project_root):
    return os.path.join(project_root, ".claude", ".sprint", "corridas.jsonl")


def dir_largadas(project_root):
    return os.path.join(project_root, ".claude", ".sprint", "em-curso")


def registra(project_root, entrada):
    """Acrescenta UMA entrada ao ledger. Devolve a entrada gravada."""
    faltando = [c for c in CAMPOS if not entrada.get(c)]
    # Vazio de DENTRO também reprova: `progresso` cheio de None é dict verdadeiro e
    # passaria calado — e é justamente o que o run devolve quando não mediu (F24.2).
    # `is None` e não falsidade: zero passo fechado é medição legítima, não ausência.
    for c in CAMPOS:
        v = entrada.get(c)
        if isinstance(v, dict):
            faltando += ["%s.%s" % (c, k) for k, sub in sorted(v.items()) if sub is None]
    if faltando:
        raise ValueError("campo obrigatorio vazio: " + ", ".join(faltando))
    linha = dict(entrada)
    linha["gravado_em"] = time.time()
    alvo = caminho(project_root)
    os.makedirs(os.path.dirname(alvo), exist_ok=True)
    with open(alvo, "a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return linha


def do_run(resultado, run_id, missao, total, inicio, fim=None):
    """Monta a entrada a partir do RETORNO do motor — nunca de memória.

    Cada campo aponta para um campo do resultado do run (F24.2): número redigido à
    mão é exatamente o defeito que o ledger existe para matar. O que o motor não
    devolve (identidade, tamanho da fila, largada) vem da casca, que o sabe.
    Campo que chegar vazio reprova no `registra` — inclusive `stopReason` ausente.
    """
    resultado = resultado or {}
    progresso = resultado.get("progresso") or {}
    return {
        "run_id": run_id,
        "missao": missao,
        "progresso": {"fechadas": progresso.get("feitos"), "total": total},
        "custo": {"tokens": resultado.get("gasto")},
        "tempo": {"inicio": inicio, "fim": fim if fim is not None else time.time()},
        "desfecho": resultado.get("stopReason"),
    }


def abre(project_root, run_id, missao, total, inicio):
    """Grava a LARGADA antes da chamada (F24.3 · R-34).

    A linha do ledger é escrita no retorno — e corrida que morre por fora (limite de
    sessão, processo morto, canal caído) não tem retorno: sem esta marca ela some do
    ledger inteira, e a série passa a mentir por omissão justamente na corrida que
    fracassou. A marca é solta pelo `registra-run`; o que sobrar vira linha no `colhe`.
    """
    alvo = os.path.join(dir_largadas(project_root), "%s.json" % run_id.replace("/", "_"))
    os.makedirs(os.path.dirname(alvo), exist_ok=True)
    with open(alvo, "w", encoding="utf-8") as f:
        json.dump({"run_id": run_id, "missao": missao, "total": total,
                   "inicio": inicio}, f, ensure_ascii=False)
    return alvo


def _solta_largada(project_root, run_id):
    if not run_id:
        return
    alvo = os.path.join(dir_largadas(project_root), "%s.json" % run_id.replace("/", "_"))
    if os.path.exists(alvo):
        os.remove(alvo)


def colhe_orfas(project_root, agora=None, teto=TETO_SEM_SINAL):
    """Fecha as largadas sem retorno: uma linha por corrida morta por fora.

    O desfecho é o que houve — `morta-por-fora` —, e o que ninguém mediu vai marcado
    `nao-medido` em vez de 0: zero é medição, e inventá-la aqui é o defeito que o
    ledger existe para matar. O fim é o último sinal de vida do arquivo de largada.
    Devolve as entradas gravadas.
    """
    agora = time.time() if agora is None else agora
    pasta = dir_largadas(project_root)
    if not os.path.isdir(pasta):
        return []
    gravadas = []
    for nome in sorted(os.listdir(pasta)):
        if not nome.endswith(".json"):
            continue
        arq = os.path.join(pasta, nome)
        ultimo_sinal = os.path.getmtime(arq)
        if agora - ultimo_sinal < teto:
            continue  # ainda pode estar viva
        # Marca ilegível (processo morto no meio da escrita, disco cheio) é da MESMA
        # família de falhas que a colheita existe para cobrir — deixá-la estourar
        # derrubaria a leitura inteira do ledger, e "nunca ausente" viraria "todas
        # ausentes". Sem identidade legível, a corrida entra pelo que o nome do
        # arquivo diz e o resto vai marcado como não medido.
        try:
            with open(arq, encoding="utf-8") as f:
                largada = json.load(f)
        except (OSError, ValueError):
            largada = {}
        gravadas.append(registra(project_root, {
            "run_id": largada.get("run_id") or nome[:-5],
            "missao": largada.get("missao") or NAO_MEDIDO,
            "progresso": {"fechadas": NAO_MEDIDO,
                          "total": largada.get("total") or NAO_MEDIDO},
            "custo": {"tokens": NAO_MEDIDO},
            "tempo": {"inicio": largada.get("inicio") or NAO_MEDIDO,
                      "fim": ultimo_sinal},
            "desfecho": "morta-por-fora",
        }))
        os.remove(arq)
    return gravadas


def le(project_root):
    """Todas as entradas, na ordem em que foram gravadas. Sem ledger = []."""
    colhe_orfas(project_root)  # ler é a hora em que a corrida sem retorno vira linha
    alvo = caminho(project_root)
    if not os.path.exists(alvo):
        return []
    entradas = []
    with open(alvo, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                entradas.append(json.loads(linha))
            except ValueError:
                continue  # linha truncada não leva as boas junto
    return entradas


def _num(v):
    """O valor se for número; None se for `nao-medido` ou qualquer outra coisa."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def serie(project_root, missao=None):
    """A série lida: progresso por corrida e custo por passo fechado (F24.4 · R-34).

    Responde "a missão avança ou gira?". `fechadas` é o que AQUELA corrida fechou —
    o motor devolve `progresso.feitos` das rodadas DELE, e a lista nasce vazia a cada
    chamada, então o número nunca é acumulado. Daí os dois derivados: `acumulado`
    soma as corridas da mesma missão até aqui (é ele que mostra a missão andando), e
    `girou` é a corrida que queimou token e não fechou passo nenhum.

    Comparar corrida com corrida como se o número fosse acumulado inverte a resposta
    justamente no caso que isto existe para pegar: a corrida que fecha zero sairia
    com ganho negativo e `girou: False`.

    O que ninguém mediu fica `nao-medido` — dividir por palpite é a mentira que o
    ledger existe para matar, e passo fechado zero não tem custo por passo, tem custo
    sem passo.
    """
    fora = []
    acumulado = {}
    # Corrida que passou do teto e VOLTOU tem duas linhas: a `morta-por-fora` que a
    # colheita gravou e a real do retorno. A série fica com a real — contar as duas
    # é contar a mesma corrida duas vezes.
    entradas = le(project_root)
    reais = {e.get("run_id") for e in entradas if e.get("desfecho") != "morta-por-fora"}
    for e in entradas:
        if missao is not None and e.get("missao") != missao:
            continue
        if e.get("desfecho") == "morta-por-fora" and e.get("run_id") in reais:
            continue
        prog = e.get("progresso") or {}
        fechadas, total = _num(prog.get("fechadas")), _num(prog.get("total"))
        tokens = _num((e.get("custo") or {}).get("tokens"))
        soma = acumulado.get(e.get("missao"))
        if fechadas is not None:
            soma = (soma or 0) + fechadas
            acumulado[e.get("missao")] = soma
        fora.append({
            "run_id": e.get("run_id"),
            "missao": e.get("missao"),
            "desfecho": e.get("desfecho"),
            "fechadas": fechadas if fechadas is not None else NAO_MEDIDO,
            "total": total if total is not None else NAO_MEDIDO,
            "acumulado": soma if soma is not None else NAO_MEDIDO,
            "tokens": tokens if tokens is not None else NAO_MEDIDO,
            "custo_por_passo": (round(tokens / fechadas, 2)
                                if tokens is not None and fechadas else NAO_MEDIDO),
            "girou": (tokens > 0 and fechadas == 0)
                     if (fechadas is not None and tokens is not None) else NAO_MEDIDO,
        })
    return fora


def relance(project_root, missao, limite=2):
    """Antes de relançar: causa que já parou duas vezes é pendência do dono (F24.5 · R-34).

    Relançar é apostar que a próxima corrida passa onde a anterior parou. Na terceira
    vez a aposta já perdeu duas: o que falta não é tentativa, é decisão de quem manda.
    A causa é o `desfecho` da corrida — a série já descarta a corrida contada duas
    vezes (a `morta-por-fora` que depois voltou), então quem conta aqui é ela.

    **Só as ÚLTIMAS corridas contam, e a sequência quebra na primeira que sai
    diferente.** O que segura o relance é a mesma pedra com o estado inalterado — uma
    corrida que parou noutro ponto, ou que fechou passo, é prova de que o estado mudou,
    e causa velha de antes disso não pode barrar a tentativa de agora. Contar o
    histórico inteiro travava a missão pelo que já tinha sido consertado: medido em
    2026-08-15, duas corridas mortas pela mesma porta foram consertadas na raiz, a
    seguinte fechou três passos, e o relance ainda apontava a pedra antiga.
    """
    causas = {}
    ultimo = None
    for c in reversed(serie(project_root, missao)):
        if c["desfecho"] in FIM_LIMPO:
            break  # terminou o que foi fazer: daqui para trás é outra história
        if ultimo is not None and c["desfecho"] != ultimo:
            break  # a sequência quebrou: a pedra de agora não é a de antes
        ultimo = c["desfecho"]
        causas.setdefault(c["desfecho"], []).insert(0, c["run_id"])
    repetidas = sorted((k for k in causas if len(causas[k]) >= limite),
                       key=lambda k: (-len(causas[k]), k))
    return {
        "relanca": not repetidas,
        "pendencias": [{"causa": k, "vezes": len(causas[k]), "corridas": causas[k]}
                       for k in repetidas],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comando",
                    choices=("registra", "registra-run", "le", "abre", "colhe", "serie",
                             "relance"))
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--json", help="entrada em JSON, ou '-' para ler do stdin")
    ap.add_argument("--run-id")
    ap.add_argument("--missao")
    ap.add_argument("--total", type=int)
    ap.add_argument("--inicio", type=float)
    a = ap.parse_args()
    if a.comando == "relance":
        v = relance(a.project_root, a.missao)
        print(json.dumps(v, ensure_ascii=False, indent=2))
        if not v["relanca"]:
            p = v["pendencias"][0]
            print("PENDENCIA DO DONO: '%s' ja parou %d corridas — relancar seria a %da "
                  "tentativa na mesma pedra." % (p["causa"], p["vezes"], p["vezes"] + 1),
                  file=sys.stderr)
            return 3
        return 0
    if a.comando == "serie":
        print(json.dumps(serie(a.project_root, a.missao), ensure_ascii=False, indent=2))
        return 0
    if a.comando == "le":
        print(json.dumps(le(a.project_root), ensure_ascii=False, indent=2))
        return 0
    if a.comando == "abre":
        print(abre(a.project_root, a.run_id, a.missao, a.total, a.inicio))
        return 0
    if a.comando == "colhe":
        print(json.dumps(colhe_orfas(a.project_root), ensure_ascii=False, indent=2))
        return 0
    bruto = sys.stdin.read() if a.json == "-" else (a.json or "")
    try:
        entrada = json.loads(bruto) if bruto.strip() else {}
        if a.comando == "registra-run":
            entrada = do_run(entrada, a.run_id, a.missao, a.total, a.inicio)
        gravada = registra(a.project_root, entrada)
        if a.comando == "registra-run":
            _solta_largada(a.project_root, a.run_id)  # voltou: não é órfã
    except ValueError as e:
        print("REPROVADO: %s" % e, file=sys.stderr)
        return 2
    print(json.dumps(gravada, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
