#!/usr/bin/env python3
"""Le a saida de um run do /sprint e diz o que fazer com a parada (F23.2/F23.5 · R-33).

Uso: python3 lib/retomada.py --run <arquivo.json> [--caso <id>]   (`-` le do stdin)

O arquivo e a saida crua que o motor.js devolve no fim da corrida — o objeto com
`stopReason` e `blockers`. Sai um JSON de quatro campos:

  {"desfecho": <stopReason>, "acao": <uma das tres>, "causa": ..., "evidencia": ...}

As tres acoes, e so tres:

  segue-no-motor    a casca nao conserta nada — relanca igual (ou nem isso) e o
                    motor continua de onde parou; a parada nunca vira trabalho de fora.
  conserta-e-relanca  alguem tem que consertar a causa ANTES de relancar; relancar
                    igual repete a mesma parada pelo mesmo preco.
  espera-dono       decisao que nao e do laco: chama o dono.

A lista do que chama o dono e FECHADA (F23.5): sao os quatro casos de CASOS_DONO, e
nenhum stopReason chega la sozinho — o motor nao sabe dizer "isto e do dono", quem
sabe e o laco, depois de investigar a causa (F23.4) ou de ver a mesma causa voltar
(F23.6). O laco declara o caso pelo `--caso`; caso fora da lista NAO chama o dono —
todo o resto o laco decide, inclusive desfecho que o inventario nao conhece (esse
cai em conserta-e-relanca: investigar antes de relancar, nunca inventar).
"""
import argparse
import json
import sys

SEGUE = "segue-no-motor"
CONSERTA = "conserta-e-relanca"
DONO = "espera-dono"

# A lista FECHADA do que chama o dono (F23.5). So estes quatro devolvem espera-dono;
# quem os identifica e o laco (investigacao/repeticao), nunca o stopReason sozinho.
CASOS_DONO = {
    "credencial-ausente": "fornecer a credencial que so o dono tem — o laco nao cria segredo",
    "ato-irreversivel": "autorizar o ato externo irreversivel (deploy, drop, push forcado) — sem autorizacao previa ninguem executa",
    "lei-ou-doc-aprovada": "aprovar a mudanca na lei do projeto ou em doc aprovada — texto acordado so muda com o dono",
    "causa-repetida": "decidir o rumo: a mesma causa parou o laco de novo sem o estado mudar — relancar repetiria",
}

# Cada desfecho que o motor.js emite (a suite cobra que a lista cobre TODOS), com a
# acao de quem retoma e o que ela exige. A chave e o `stopReason`. Nenhuma entrada
# aponta para espera-dono: dono se chama por CASOS_DONO, nunca por desfecho.
DESFECHOS = {
    "build-complete": (SEGUE, "nada: o plano fechou — so o relatorio"),
    "max-rounds": (SEGUE, "relancar com o mesmo plano; o que faltou esta nas tarefas abertas"),
    "causa-global": (CONSERTA, "consertar a causa de escopo de repositorio antes de relancar"),
    "porta-fechada": (CONSERTA, "consertar a porta (lint/type/teste do repo) e re-medir antes de relancar"),
    "onda-esteril": (CONSERTA, "destravar o que os impedidos/esperando apontam — relancar igual repete"),
    "corrida-em-circulo": (CONSERTA, "destravar o que os achados apontam; rodada nova repetiria o estado"),
    "em-falso": (CONSERTA, "destravar o que os achados apontam; a medicao das ultimas rodadas nao mostrou obra saindo"),
    "vigia": (CONSERTA, "investigar travamento; o ultimo estado salvo e o checkpoint da rodada anterior"),
    # F23.5: reserva e orcamento sairam do dono — a lista fechada nao os tem, e o
    # laco resolve os dois relancando (esperando a vez, ou com teto novo).
    "reserva": (SEGUE, "esperar o outro motor da sessao liberar (ele solta ao sair) e relancar igual"),
    "orcamento": (SEGUE, "relancar com teto maior de tokens — o laco decide o teto, nao o dono"),
}


def classifica(run, caso=None):
    """run: o dict que o motor.js devolveu; caso: o que o laco identificou na causa
    (um id de CASOS_DONO chama o dono; qualquer outro valor nao muda nada).
    Devolve os quatro campos."""
    desfecho = str(run.get("stopReason") or "").strip() or "(sem stopReason)"
    if caso in CASOS_DONO:
        acao, exige = DONO, CASOS_DONO[caso]
    else:
        acao, exige = DESFECHOS.get(desfecho, (CONSERTA, "desfecho que o inventario nao conhece — investigar a causa antes de relancar"))

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
    # A saida e JSON com acento e travessao (`ensure_ascii=False`), e o console do
    # Windows de fabrica e cp1252: sem isto o `print` do fim morre de
    # UnicodeEncodeError, ou chega mordido a quem le. Quem escreve o texto declara o
    # encoding dele — nao se deixa a conta para a variavel de ambiente do runner.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="classifica a parada de um run do /sprint")
    ap.add_argument("--run", required=True, help="arquivo com a saida JSON do motor (ou - para stdin)")
    ap.add_argument("--caso", help="o que o laco identificou na causa; um de: %s" % ", ".join(sorted(CASOS_DONO)))
    a = ap.parse_args(argv)
    bruto = sys.stdin.read() if a.run == "-" else open(a.run, encoding="utf-8").read()
    try:
        run = json.loads(bruto)
    except ValueError as e:
        print("saida de run ilegivel: %s" % e, file=sys.stderr)
        return 2
    print(json.dumps(classifica(run, caso=a.caso), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
