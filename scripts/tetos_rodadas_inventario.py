#!/usr/bin/env python3
"""tetos_rodadas_inventario.py — inventário dos tetos por contagem de rodadas (F16.3 · R-26).

A decisão do dono (2026-08-13, gravada em `sprint/references/motor.js`) é que quem para
uma corrida é COMPORTAMENTO — obra pronta, vigia, juiz de produtividade (F16.1/F16.2) —
nunca uma conta de rodadas. Este script varre a casa inteira atrás de todo teto que ainda
conta rodadas (`max_rounds`, `maxRounds` e afins) e cobra que cada um tenha VEREDITO:

  MIGRADO — o teto deixou de decidir; quem para é o juiz de produtividade do motor.
  FICA    — o teto permanece, com a justificativa por escrito aqui embaixo.

O universo varrido sai de `git ls-files` (glob, nunca lista à mão): todo `.py`, `.js` e
`.sh` rastreado, menos testes (fixture de teto é exercício, não política) e este arquivo.
Um teto NOVO que apareça sem veredito reprova o `--check`; um veredito cujo teto sumiu do
código também reprova (veredito órfão é doc mentindo).

    python3 scripts/tetos_rodadas_inventario.py          # inventário legível
    python3 scripts/tetos_rodadas_inventario.py --json   # o mesmo, para máquina
    python3 scripts/tetos_rodadas_inventario.py --check  # sai 1 se há teto sem veredito
"""
import argparse
import json
import os
import re
import subprocess
import sys

for _canal in (sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Identificadores que significam "teto por contagem": a DEFINIÇÃO deles (atribuição ou
# default de parâmetro) é o que entra no inventário; uso (`>= teto`) não conta duas vezes.
IDENT = r"(max_?rounds|rodadas_?mudas_?max|max_?iter\w*|max_?attempts|max_?loops|max_?tentativas|churn_?threshold)"
DEFINICAO = re.compile(rf"\b{IDENT}\s*=(?!=)", re.IGNORECASE)

# O VEREDITO DE CADA TETO (F16.3). Chave: (arquivo, identificador normalizado).
# Migração feita se resolve em código (e o código é a prova); permanência se defende aqui,
# por escrito — teto sem linha neste dicionário é exatamente o defeito que o --check caça.
VEREDITOS = {
    ("plugins/project-skills/skills/sprint/references/motor.js", "maxrounds"): (
        "MIGRADO",
        "F16.1/F16.2: default é Infinity (sem teto — decisão do dono, 2026-08-13); quem "
        "para a corrida em falso é o juiz de produtividade (`produtividadePrompt` + "
        "veredito 'em falso' sobre a medição crua das últimas rodadas), não a conta. O "
        "número só age se a casca o passar de propósito."),
    ("plugins/project-skills/skills/sprint/references/motor.js", "rodadasmudasmax"): (
        "FICA",
        "Vigia por avanço, não aposta de contagem: conta rodadas que fecharam SEM nenhum "
        "bloco verde e sem passo marcado. Rodada muda não gera medição de produção — o "
        "juiz de produtividade julga medições e aqui não há nenhuma; sem o vigia, "
        "travamento vira silêncio infinito (autópsia de 2026-08-10 em runtime.md)."),
    ("plugins/project-skills/skills/sprint/references/motor.js", "churnthreshold"): (
        "FICA",
        "Escalador, não parador: ao bater, a tarefa vai para DIAGNOSE (investigação de "
        "causa raiz dedicada) em vez de repetir o conserto — a corrida continua. Migrar "
        "para o juiz trocaria escalada determinística por julgamento, sem ganho."),
    ("plugins/project-skills/skills/qa-loop/references/motor.js", "maxrounds"): (
        "FICA",
        "Trava de incêndio, não meta (SKILL.md:133): no domínio assintótico quem decide "
        "a parada é o gate de severidade — 'rodada limpa' JÁ É o critério de retorno "
        "decrescente, a versão determinística do juiz de produtividade. O clamp por "
        "camada de rede (Camada 4→2, 5→1) é decisão deliberada: rede fraca não ganha "
        "volta de aposta cega."),
    ("plugins/project-skills/skills/qa-loop/references/motor.js", "churnthreshold"): (
        "FICA",
        "Mesmo papel do irmão no sprint: escala a mesma correção repetida para revert + "
        "replan, não encerra o loop. Determinístico e barato; juiz não se aplica."),
    ("plugins/fallow/lib/audit.py", "max_rounds"): (
        "FICA",
        "Laço determinístico de ponto fixo em análise estática (convergência de código "
        "morto) — não há corrida de agentes nem rodada de LLM para um juiz medir; o teto "
        "só guarda contra oscilação sem fim do algoritmo."),
}

FORA_NOME = ("test_", "_test.")


def universo():
    """Todo código que o git rastreia, menos teste e o próprio medidor — via glob, nunca à mão."""
    saida = subprocess.run(["git", "-C", RAIZ, "ls-files", "*.py", "*.js", "*.sh"],
                           capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, start_new_session=True).stdout
    alvos = []
    for rel in saida.splitlines():
        nome = os.path.basename(rel)
        if any(m in nome for m in FORA_NOME) or nome == "tetos_rodadas_inventario.py":
            continue
        alvos.append(rel)
    return alvos


def varre(arquivos):
    """Cada DEFINIÇÃO de teto encontrada: (arquivo, ident_normalizado, linha, texto)."""
    achados = []
    for rel in arquivos:
        try:
            with open(os.path.join(RAIZ, rel), encoding="utf-8", errors="replace") as f:
                for n, linha in enumerate(f, 1):
                    m = DEFINICAO.search(linha)
                    if m:
                        ident = re.sub(r"[^a-z0-9_]", "", m.group(1).lower())
                        achados.append({"arquivo": rel, "ident": ident,
                                        "linha": n, "texto": linha.strip()})
        except OSError:
            continue
    return achados


def julga(achados):
    """Casa cada achado com o veredito; devolve (itens, sem_veredito, vereditos_orfaos)."""
    itens, sem_veredito = [], []
    vistos = set()
    for a in achados:
        chave = (a["arquivo"], a["ident"])
        vistos.add(chave)
        if chave in VEREDITOS:
            situacao, justificativa = VEREDITOS[chave]
            itens.append({**a, "situacao": situacao, "justificativa": justificativa})
        else:
            sem_veredito.append(a)
    orfaos = [{"arquivo": arq, "ident": ident}
              for (arq, ident) in VEREDITOS if (arq, ident) not in vistos]
    return itens, sem_veredito, orfaos


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    itens, sem_veredito, orfaos = julga(varre(universo()))

    if args.json:
        print(json.dumps({"tetos": itens, "sem_veredito": sem_veredito,
                          "vereditos_orfaos": orfaos}, ensure_ascii=False, indent=2))
    else:
        print(f"TETOS POR CONTAGEM DE RODADAS — {len(itens)} com veredito, "
              f"{len(sem_veredito)} sem, {len(orfaos) } veredito(s) órfão(s)\n")
        for i in itens:
            print(f"[{i['situacao']}] {i['arquivo']}:{i['linha']}  {i['texto']}")
            print(f"          {i['justificativa']}\n")
        for a in sem_veredito:
            print(f"[SEM VEREDITO] {a['arquivo']}:{a['linha']}  {a['texto']}")
        for o in orfaos:
            print(f"[ÓRFÃO] veredito para {o['arquivo']} · {o['ident']} sem teto no código")

    if args.check and (sem_veredito or orfaos):
        for a in sem_veredito:
            print(f"REPROVADO: teto novo sem veredito — {a['arquivo']}:{a['linha']} "
                  f"({a['texto']}); migre para o juiz de produtividade ou justifique em "
                  f"VEREDITOS de scripts/tetos_rodadas_inventario.py", file=sys.stderr)
        for o in orfaos:
            print(f"REPROVADO: veredito órfão — {o['arquivo']} · {o['ident']} não existe "
                  f"mais no código; apague a entrada", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
