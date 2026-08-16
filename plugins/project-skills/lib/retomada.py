#!/usr/bin/env python3
"""Le a saida de um run do /sprint e diz o que fazer com a parada (F23.2 · R-33).

Uso: python3 lib/retomada.py --run <arquivo.json>   (ou `-` para ler do stdin)

O arquivo e a saida crua que o motor.js devolve no fim da corrida — o objeto com
`stopReason` e `blockers`. Sai um JSON de quatro campos:

  {"desfecho": <stopReason>, "acao": <uma das tres>, "causa": ..., "evidencia": ...}

As tres acoes, e so tres:

  segue-no-motor    a casca nao conserta nada — relanca igual (ou nem isso) e o
                    motor continua de onde parou; a parada nunca vira trabalho de fora.
  conserta-e-relanca  alguem tem que consertar a causa ANTES de relancar; relancar
                    igual repete a mesma parada pelo mesmo preco.
  espera-dono       decisao que nao e do laco: chama o dono.

⚠️ A lista de espera-dono aqui e PROVISORIA. A lista FECHADA (credencial ausente ·
ato externo irreversivel nao autorizado · escrever na lei ou em doc aprovada · mesma
causa repetida) e da tarefa F23.5 e ainda nao existe. Ate ela chegar, o que classifica
e so o inventario de desfechos medido no motor.js (F23.1), e desfecho DESCONHECIDO cai
em espera-dono por seguranca — quem retoma nao inventa o que fazer com o que nao sabe.
"""
import argparse
import json
import sys

SEGUE = "segue-no-motor"
CONSERTA = "conserta-e-relanca"
DONO = "espera-dono"

# Cada desfecho que o motor.js emite (a suite cobra que a lista cobre TODOS), com a
# acao de quem retoma e o que ela exige. A chave e o `stopReason`.
DESFECHOS = {
    "build-complete": (SEGUE, "nada: o plano fechou — so o relatorio"),
    "max-rounds": (SEGUE, "relancar com o mesmo plano; o que faltou esta nas tarefas abertas"),
    "causa-global": (CONSERTA, "consertar a causa de escopo de repositorio antes de relancar"),
    "porta-fechada": (CONSERTA, "consertar a porta (lint/type/teste do repo) e re-medir antes de relancar"),
    "onda-esteril": (CONSERTA, "destravar o que os impedidos/esperando apontam — relancar igual repete"),
    "corrida-em-circulo": (CONSERTA, "destravar o que os achados apontam; rodada nova repetiria o estado"),
    "vigia": (CONSERTA, "investigar travamento; o ultimo estado salvo e o checkpoint da rodada anterior"),
    # PROVISORIO ate F23.5: os dois abaixo gastam dinheiro ou mexem com outro motor da
    # sessao — decisao de dono, nao do laco.
    "reserva": (DONO, "esperar o outro motor da sessao sair, ou recortar a missao para outros arquivos"),
    "orcamento": (DONO, "decidir se vale relancar com teto maior de tokens"),
}


def classifica(run):
    """run: o dict que o motor.js devolveu. Devolve os quatro campos."""
    desfecho = str(run.get("stopReason") or "").strip() or "(sem stopReason)"
    acao, exige = DESFECHOS.get(desfecho, (DONO, "desfecho que o inventario nao conhece — nao ha o que retomar em automatico"))

    blockers = [b for b in (run.get("blockers") or []) if isinstance(b, dict)]
    ultimo = blockers[-1] if blockers else {}
    causa = str(ultimo.get("what") or "").strip() or exige
    evidencia = str(ultimo.get("whyNeedsYou") or "").strip()
    if not evidencia:
        p = run.get("progresso") or {}
        evidencia = "sem blocker na saida — %s passo(s) marcado(s) em %s rodada(s)" % (
            p.get("feitos", "?"), len(run.get("rounds") or []))
    return {"desfecho": desfecho, "acao": acao, "causa": causa, "evidencia": evidencia}


def main(argv=None):
    ap = argparse.ArgumentParser(description="classifica a parada de um run do /sprint")
    ap.add_argument("--run", required=True, help="arquivo com a saida JSON do motor (ou - para stdin)")
    a = ap.parse_args(argv)
    bruto = sys.stdin.read() if a.run == "-" else open(a.run, encoding="utf-8").read()
    try:
        run = json.loads(bruto)
    except ValueError as e:
        print("saida de run ilegivel: %s" % e, file=sys.stderr)
        return 2
    print(json.dumps(classifica(run), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
