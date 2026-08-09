#!/usr/bin/env python3
"""Bancada do sobras.py — o escopo do run, e o que fica de fora dele.

O caso que manda é o do vizinho: uma reserva presa de OUTRO run, no mesmo
diretório de estado, não pode entrar na autópsia deste. Sem esse teste a
varredura volta a acusar a máquina inteira, que é o que três outros plugins já
fazem.
"""

import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sobras  # noqa: E402

FALHAS = []
VELHO = 800 * 60          # mais velho que o TTL de 720 min


def check(nome, cond):
    print("  %s  %s" % ("ok  " if cond else "FAIL", nome))
    if not cond:
        FALHAS.append(nome)


def monta_run(base, projeto, sessao, run):
    d = os.path.join(base, projeto, sessao, "subagents", "workflows", run)
    os.makedirs(d)
    return d


def reserva(dir_reservas, nome, idade_seg):
    p = os.path.join(dir_reservas, nome + ".files")
    open(p, "w").write("a.py\nb.py\n")
    quando = time.time() - idade_seg
    os.utime(p, (quando, quando))
    return p


def caso_sessao():
    d = "/base/projects/proj/sessao-abc/subagents/workflows/wf_1"
    check("a sessão sai do caminho do run", sobras.sessao_do_run(d) == "sessao-abc")
    check("caminho fora do formato não inventa sessão",
          sobras.sessao_do_run("/qualquer/pasta") == "")


def caso_escopo():
    d = tempfile.mkdtemp(prefix="sobras-esc-")
    try:
        reserva(d, "sessao-abc__motor-1", VELHO)
        reserva(d, "sessao-xyz__motor-9", VELHO)      # o vizinho: outro run
        reserva(d, "sessao-abc__motor-2", 60)         # recente: ainda viva

        r = sobras.reservas("sessao-abc", d)
        check("acha a reserva presa desta sessão",
              len(r) == 1 and r[0]["o_que"] == "sessao-abc__motor-1")
        check("sobra de outro run não entra",
              all("sessao-xyz" not in x["o_que"] for x in r))
        check("reserva recente não é sobra",
              all("motor-2" not in x["o_que"] for x in r))
        check("diz o tamanho dela em arquivos travados",
              r[0]["tamanho"] == 2 and r[0]["unidade"] == "arquivos travados")
        check("sem sessão não acusa nada", sobras.reservas("", d) == [])
        check("diretório de reservas inexistente não quebra",
              sobras.reservas("sessao-abc", os.path.join(d, "nao-existe")) == [])
    finally:
        shutil.rmtree(d, ignore_errors=True)


def caso_varredura():
    d = tempfile.mkdtemp(prefix="sobras-var-")
    try:
        os.environ["CLAUDE_CONFIG_DIR"] = d
        base = os.path.join(d, "projects")
        meu = monta_run(base, "proj", "sessao-abc", "wf_meu")
        monta_run(base, "proj", "sessao-xyz", "wf_outro")
        res = os.path.join(d, "sovai", "reservas")
        os.makedirs(res)
        reserva(res, "sessao-abc__motor-1", VELHO)
        reserva(res, "sessao-xyz__motor-9", VELHO)

        r, erro = sobras.varre("wf_meu", base)
        check("a varredura do run nomeado não estoura", erro is None)
        check("ela devolve só a sobra do run pedido",
              len(r) == 1 and r[0]["o_que"] == "sessao-abc__motor-1")
        check("o que ela acusa carrega o identificador do run",
              r[0]["run"] == "wf_meu")

        r, erro = sobras.varre("wf_outro", base)
        check("o run vizinho enxerga a sobra dele, e só a dele",
              erro is None and len(r) == 1 and r[0]["run"] == "wf_outro"
              and r[0]["o_que"] == "sessao-xyz__motor-9")

        r, erro = sobras.varre("wf_inexistente", base)
        check("run que não existe vira recusa, não varredura vazia",
              r == [] and erro and "wf_inexistente" in erro)

        vazio = tempfile.mkdtemp(prefix="sobras-vazio-")
        try:
            r, erro = sobras.varre(None, vazio)
            check("sem run no disco a varredura diz isso e para",
                  r == [] and erro and "nenhum run" in erro)
        finally:
            shutil.rmtree(vazio, ignore_errors=True)

        check("o caminho do run vale como run", sobras.varre(meu, base)[0][0]["run"] == "wf_meu")
    finally:
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
        shutil.rmtree(d, ignore_errors=True)


def caso_relatorio():
    d = tempfile.mkdtemp(prefix="sobras-rel-")
    try:
        os.environ["CLAUDE_CONFIG_DIR"] = d
        base = os.path.join(d, "projects")
        limpo = monta_run(base, "proj", "sessao-abc", "wf_limpo")
        check("run sem sobra sai com 0", sobras.main(["--run", limpo]) == 0)

        res = os.path.join(d, "sovai", "reservas")
        os.makedirs(res)
        reserva(res, "sessao-abc__motor-1", VELHO)
        check("achou sobra ⇒ sai com 1", sobras.main(["--run", limpo, "--json"]) == 1)

        check("sem run nenhum ⇒ sai com 2",
              sobras.main(["--run", os.path.join(d, "nao-existe-nenhum")]) == 2)
    finally:
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("sobras")
    caso_sessao()
    caso_escopo()
    caso_varredura()
    caso_relatorio()
    print()
    if FALHAS:
        print("FALHOU · %d" % len(FALHAS))
        return 1
    print("tudo verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
