#!/usr/bin/env python3
"""Do checkbox ao plano ticável — o que o dono marcou vira arquivo de plano.

Entra a lista dos achados MARCADOS na página (o mesmo formato de `achado.py`,
pelo `stdin`), sai `.claude/plans/vistoria-<data>.plan.json` no molde do
`plan_state`: um passo por achado, id fixo, e o critério verificável escrito no
`pronto`. Daí em diante o plano só é MARCADO (`tick`) — nunca reescrito.

O id do passo é posicional e estável (`F1.1`, `F1.2`, …): quem marcou primeiro
fica sendo o primeiro para sempre, que é o que deixa o `tick` de uma sessão
valer na seguinte.

O destino NÃO é adivinhado: `--dir` é obrigatório. Um padrão calculado a partir da
posição deste arquivo aponta para dentro do cache do plugin quando instalado — o
plano do dono nasceria na pasta do autor da skill. Sem `--dir`, o programa recusa.

DEGRADAÇÃO DECLARADA. A conferência do arquivo contra o schema é feita pelo
`plan_state.py`, que vive no plugin `project-skills` e é achado pelo NOME
(`resolve-plugin.sh`), nunca pela posição no disco — e ele pode não estar na
máquina. Nesse caso o JSON sai do mesmo jeito (ele é gravado por este módulo,
não por lá) e o aviso da conferência que não aconteceu vai para o `stderr`. Um
plano gravado sem conferência é pior do que plano nenhum só se ninguém souber.

Uso:
    python3 plugins/vistoria/lib/plano_saida.py --dir .claude/plans < marcados.json

stdlib only (requisito do repo).
"""

import argparse
import datetime
import importlib.util
import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from achado import valida  # noqa: E402
from regua_texto import erros_de_estilo  # noqa: E402

PLUGIN = os.path.dirname(AQUI)
RESOLVEDOR = os.path.join(AQUI, "resolve-plugin.sh")

FASE = "F1"

AVISO_DEGRADACAO = (
    "aviso: o plugin visual não está nesta máquina (%s) — o plano foi gravado "
    "sem a conferência do plan_state; confira-o à mão antes de executar")


def data_de_hoje():
    return datetime.date.today().isoformat()


def id_do_plano(data):
    return "vistoria-%s" % data


def id_do_passo(n):
    """O id fixo do n-ésimo achado marcado — posicional, e por isso estável."""
    return "%s.%d" % (FASE, n)


def desc_de(a):
    """A linha didática que aparece na árvore: quem acusou, onde, por qual regra."""
    return "o cobrador %s marcou %s pela regra %s" % (a["cobrador"], a["onde"], a["regra"])


def pronto_de(a):
    """O critério verificável: o mesmo cobrador, rodado de novo, não acusa mais ali."""
    return "o cobrador %s deixa de acusar a regra %s em %s" % (
        a["cobrador"], a["regra"], a["onde"])


def passo_de(n, a):
    return {
        "id": id_do_passo(n),
        "title": a["o_que"],
        "desc": desc_de(a),
        "pronto": pronto_de(a),
        "status": "todo",
        "evidence": None,
        "done_at": None,
    }


def plano_de(achados, data=None):
    """O plano inteiro, em memória. Achado sem prova nem chega aqui: `valida` recusa."""
    data = data or data_de_hoje()
    itens = [passo_de(n, valida(a)) for n, a in enumerate(achados, 1)]
    return {
        "id": id_do_plano(data),
        "title": "Vistoria de %s — %d achado(s) marcado(s)" % (data, len(itens)),
        "created": data,
        "status": "active",
        "phases": [{
            "id": FASE,
            "title": "Achados marcados na vistoria de %s" % data,
            "items": itens,
        }],
    }


def erros_do_texto(plano):
    """A régua compartilhada sobre o que ESTE gerador redige, no perfil do plano."""
    errs = []
    for ph in plano["phases"]:
        for it in ph["items"]:
            for campo in ("desc", "pronto"):
                errs += erros_de_estilo(it[campo], "%s %s" % (it["id"], campo), "plano")
    return errs


def acha_plan_state():
    """O `plan_state.py` do irmão pelo NOME — vazio quando não está na máquina."""
    env = dict(os.environ)
    env.setdefault("CLAUDE_PLUGIN_ROOT", PLUGIN)
    try:
        r = subprocess.run(["bash", RESOLVEDOR, "project-skills", "lib/plan_state.py"],
                           capture_output=True, text=True, env=env,
                           stdin=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def confere_com_plan_state(plano, caminho=None):
    """Confere o plano contra o schema do `plan_state`, quando ele está na máquina.

    Devolve `(erros, aviso)`. `aviso` preenchido = a conferência NÃO aconteceu, e
    quem chamou tem que dizer isso em voz alta.
    """
    caminho = acha_plan_state() if caminho is None else caminho
    if not caminho or not os.path.isfile(caminho):
        return [], AVISO_DEGRADACAO % (caminho or "não achado pelo nome")
    spec = importlib.util.spec_from_file_location("plan_state_da_vistoria", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.erros_do_plano(plano), ""


def escreve(achados, saida, data=None):
    """Grava o plano e devolve `(caminho, aviso)`. Aviso vazio = houve conferência."""
    plano = plano_de(achados, data)
    errs = erros_do_texto(plano)
    if errs:
        raise ValueError("o texto do plano não passa na régua: " + "; ".join(errs))
    do_schema, aviso = confere_com_plan_state(plano)
    if do_schema:
        raise ValueError("o plano não passa no schema: " + "; ".join(do_schema))
    os.makedirs(saida, exist_ok=True)
    caminho = os.path.join(saida, "%s.plan.json" % plano["id"])
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(plano, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return caminho, aviso


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True,
                    help="onde gravar (obrigatório: destino adivinhado cai no cache "
                         "do plugin quando instalado)")
    ap.add_argument("--data", default=None, help="a data do plano (padrão: hoje)")
    args = ap.parse_args(argv)
    dados = json.load(sys.stdin)
    achados = dados.get("achados", dados) if isinstance(dados, dict) else dados
    caminho, aviso = escreve(achados, args.dir, args.data)
    if aviso:
        sys.stderr.write(aviso + "\n")
    print(caminho)
    return 0


if __name__ == "__main__":
    sys.exit(main())
