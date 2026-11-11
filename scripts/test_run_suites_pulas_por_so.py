#!/usr/bin/env python3
"""Suíte das PULAS POR SISTEMA do run_suites.py — pular suíte só com motivo e em voz alta.

Por que existe: no Windows do CI uma suíte (`test_lixeiro_hooks.sh`) derrubava a esteira
inteira, e o job saía verde sem placar. A saída honesta é o rodador PULAR essa suíte
no Windows — mas pular é a porta por onde o "verde mentiroso" volta, então a pula tem
regras e este arquivo as cobra:

  * só o Windows pula; POSIX nunca pula nada;
  * toda entrada da tabela tem o arquivo no disco (pula de suíte que já morreu é lixo);
  * toda entrada tem motivo escrito, com tamanho de motivo e não de rótulo;
  * a suíte pulada aparece no log (`↷ PULADA`), na anotação (`::warning::`) e no placar —
    e NÃO conta como problema nem como suíte rodada;
  * a mesma suíte, no sistema que não pula, RODA e reprova se for o caso.

    python3 scripts/test_run_suites_pulas_por_so.py
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import shutil

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RODADOR = os.path.join(RAIZ, "scripts", "run_suites.py")
ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ✓ %s" % nome)
    else:
        falhas += 1
        print("  ✗ %s%s" % (nome, ("\n      %s" % detalhe) if detalhe else ""))


spec = importlib.util.spec_from_file_location("run_suites_sob_teste", RODADOR)
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

ALVO = "plugins/lixeiro/hooks/test_lixeiro_hooks.sh"

print("a tabela")
check("o Windows pula o test_lixeiro_hooks.sh", ALVO in rs.pulas_do_so("nt"))
check("POSIX não pula NADA", rs.pulas_do_so("posix") == {})
for alvo, motivo in rs.PULA_NO_SO["nt"].items():
    check("o arquivo pulado existe no disco: %s" % alvo,
          os.path.isfile(os.path.join(RAIZ, *alvo.split("/"))))
    check("o motivo é uma frase, não um rótulo (%d caracteres)" % len(motivo), len(motivo) >= 80)
    check("o motivo aponta onde está rastreado", "PR #10" in motivo)

print("separa_puladas")
rodam, puladas = rs.separa_puladas(["plugins\\lixeiro\\hooks\\test_lixeiro_hooks.sh", "scripts/outra.py"], "nt")
check("aceita o caminho do Windows (barra invertida)", [a for a, _ in puladas] == ["plugins\\lixeiro\\hooks\\test_lixeiro_hooks.sh"])
check("o resto continua na lista que roda", rodam == ["scripts/outra.py"])
rodam, puladas = rs.separa_puladas([ALVO, "scripts/outra.py"], "posix")
check("no POSIX nada sai da lista", puladas == [] and rodam == [ALVO, "scripts/outra.py"])
os.environ["RUN_SUITES_NAO_PULA"] = "1"
try:
    check("RUN_SUITES_NAO_PULA=1 desliga a pula (para medir o conserto do produto)",
          rs.pulas_do_so("nt") == {})
finally:
    del os.environ["RUN_SUITES_NAO_PULA"]

print("o rodador, de ponta a ponta, numa árvore de mentira")
d = tempfile.mkdtemp(prefix="pula-so-")
try:
    caminho = os.path.join(d, *ALVO.split("/"))
    os.makedirs(os.path.dirname(caminho))
    # O rodador dispara o que o `--py` aponta com o Python, qualquer que seja a
    # extensão: assim a prova não depende de haver um bash na máquina.
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write("import sys\nprint('esta suite sempre reprova')\nsys.exit(1)\n")
    with open(os.path.join(d, "test_verde.py"), "w", encoding="utf-8") as fh:
        fh.write("print('ok')\n")

    def roda(so, *extra):
        env = dict(os.environ, RUN_SUITES_SO=so)
        env.pop("RUN_SUITES_NAO_PULA", None)
        r = subprocess.run([sys.executable, RODADOR, "--py", ALVO, "test_verde.py", *extra],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, start_new_session=True, cwd=d, env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    rc, saida = roda("nt")
    check("no Windows encenado: sai 0 (a única reprovada foi pulada)", rc == 0, saida)
    check("a linha '↷ PULADA' diz qual suíte", "↷ PULADA" in saida and ALVO in saida, saida)
    check("a linha traz o motivo", "motivo:" in saida and "PR #10" in saida, saida)
    check("a anotação ::warning:: sai para o painel do CI", "::warning::suíte pulada" in saida, saida)
    check("o placar conta 1 suíte rodada e 0 problemas", "1 suíte(s) · 0 problema(s)" in saida, saida)
    check("o placar nomeia a pulada", "1 suíte(s) PULADA(S)" in saida and ALVO in saida.split("PULADA(S)")[-1], saida)
    check("a última linha é o veredito do próprio rodador", saida.rstrip().endswith("run_suites: veredito rc=0"), saida)

    rc, saida = roda("posix")
    check("no POSIX encenado a MESMA suíte roda e reprova: sai 1", rc == 1, saida)
    check("e não há pula nenhuma", "PULADA" not in saida, saida)
    check("o placar conta as duas suítes e 1 problema", "2 suíte(s) · 1 problema(s)" in saida, saida)
    check("a última linha é o veredito: rc=1", saida.rstrip().endswith("run_suites: veredito rc=1"), saida)
finally:
    shutil.rmtree(d, ignore_errors=True)

print("\n%d ok · %d falha(s)" % (ok, falhas))
sys.exit(1 if falhas else 0)
