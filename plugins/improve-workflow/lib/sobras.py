#!/usr/bin/env python3
"""sobras.py — o que ESTE run deixou no disco e não entra em relatório nenhum.

O relatório do motor conta as tarefas. O que sobrevive ao fim da missão não
aparece em lugar nenhum — some entre uma missão e a próxima, e só reaparece como
defeito:

  reserva   — trava de arquivos de um motor que morreu sem liberar. Ela só expira
              quando OUTRO motor esbarra nela; até lá, ninguém a vê.

Uma natureza só, e é de propósito. Processo de pé, árvore de trabalho parada e
higiene de máquina JÁ TÊM DONO neste marketplace (`/faxina`, `/branches`,
`/fallow`): varrer isso aqui seria o quarto plugin brigando pelo mesmo achado —
a doença que o conferidor de skills existe para diagnosticar. E o corte é duplo:
a varredura é escopada pelo IDENTIFICADOR DO RUN, então sobra de outro run é
assunto de quem cuida daquele run, não desta autópsia.

    python3 sobras.py [--run <run>] [--json]
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import medidor  # noqa: E402


def sessao_do_run(dir_run):
    """A sessão dona do run: `<projeto>/<sessão>/subagents/workflows/<runId>`.

    A reserva é gravada por SESSÃO (`<sessão>__<motor>.files`, ver
    `reserva-de-arquivos.sh`), então é a sessão que liga uma reserva ao run.
    Caminho fora desse formato devolve "" — sem sessão não há escopo, e sem
    escopo é melhor não acusar nada."""
    p = os.path.normpath(dir_run).rstrip(os.sep)
    partes = p.split(os.sep)
    if len(partes) < 4 or partes[-3:-1] != ["subagents", "workflows"]:
        return ""
    return partes[-4]


def _limpa(nome):
    """A mesma sanitização do hook que grava a reserva — sem ela, sessão com
    caractere fora do conjunto nunca casaria com o nome do arquivo."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", nome)


def reservas(sessao, dir_reservas=None, agora=None, ttl_min=None):
    """Reserva DESTA sessão mais velha que o TTL — o motor dela morreu sem liberar.

    Mesmo TTL do `reserva-de-arquivos.sh` (720 min), pela mesma razão: a missão
    que ele protege é longa por definição."""
    if not sessao:
        return []
    if dir_reservas is None:
        base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        dir_reservas = os.path.join(base, "sovai", "reservas")
    ttl_min = int(os.environ.get("SOVAI_RESERVA_TTL_MIN", 720)) if ttl_min is None else ttl_min
    agora = time.time() if agora is None else agora
    if not os.path.isdir(dir_reservas):
        return []
    prefixo = _limpa(sessao) + "__"
    fora = []
    for nome in sorted(os.listdir(dir_reservas)):
        if not nome.endswith(".files") or not nome.startswith(prefixo):
            continue
        p = os.path.join(dir_reservas, nome)
        try:
            idade_min = (agora - os.stat(p).st_mtime) / 60.0
            linhas = [ln for ln in open(p, encoding="utf-8").read().splitlines() if ln.strip()]
        except OSError:
            continue
        if idade_min <= ttl_min:
            continue
        fora.append({
            "natureza": "reserva",
            "o_que": nome[:-len(".files")],
            "tamanho": len(linhas),
            "unidade": "arquivos travados",
            "detalhe": "parada há %d h — recusa todo motor que encostar nesses arquivos"
                       % (idade_min / 60),
        })
    return fora


def varre(run=None, base=None):
    """(sobras, erro). Toda sobra sai carimbada com o run de onde veio: sem o
    carimbo, o leitor não distingue o que ESTA missão deixou do que já estava lá."""
    dir_run, erro = medidor.resolver_run(run, base)
    if erro:
        return [], erro
    nome_run = os.path.basename(os.path.normpath(dir_run))
    fora = reservas(sessao_do_run(dir_run))
    for x in fora:
        x["run"] = nome_run
    return fora, None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--run", default=None)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    r, erro = varre(a.run)
    if erro:
        return medidor.degrada("sobras: %s" % erro, a.run)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 1 if r else 0
    if not r:
        print("sobras: nenhuma — este run não deixou reserva presa para trás")
        return 0
    print("SOBRAS DO RUN %s — %d, e nenhuma delas entra em relatório nenhum:\n"
          % (r[0]["run"], len(r)))
    for x in r:
        print("  [%s] %s" % (x["natureza"], x["o_que"]))
        print("      %s %s · %s" % (x["tamanho"], x["unidade"], x["detalhe"]))
    print("\nNada foi removido: o que fazer com cada uma é leitura de quem está aqui.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
