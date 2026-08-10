#!/usr/bin/env python3
"""A régua do lote — achado LIDO sem par de citações não passa no `--validar`."""

import json
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from achado import erros_de_lote  # noqa: E402

MEDIDO = {"cobrador": "hook-contract", "regra": "R1", "gravidade": "alta",
          "onde": "x.sh:1", "o_que": "bloqueia sem teto", "prova": "exit 2"}
LIDO_OK = dict(MEDIDO, cobrador="leitor",
               prova="a/SKILL.md:11: espere a suíte\nb/guard.sh:10: recusado")
LIDO_SEM_PAR = dict(LIDO_OK, prova="a/SKILL.md:11: espere a suíte")


def roda(lote):
    p = subprocess.run([sys.executable, os.path.join(AQUI, "achado.py"), "--validar"],
                       input=json.dumps(lote), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       start_new_session=True)
    return p.returncode, p.stderr


def main():
    assert erros_de_lote([MEDIDO]) == [], "achado medido bem formado tem que passar"
    assert erros_de_lote([LIDO_OK]) == [], "achado lido com as duas citações passa"
    errs = erros_de_lote([LIDO_SEM_PAR])
    assert errs and "par de citações" in errs[0], errs
    # a prova crua do cobrador medido não tem citação nenhuma e continua válida
    assert erros_de_lote([dict(MEDIDO, prova="saída crua")]) == []

    rc, _ = roda([MEDIDO, LIDO_OK])
    assert rc == 0, "lote válido tem que sair 0, saiu %d" % rc
    rc, err = roda([LIDO_SEM_PAR])
    assert rc == 1 and "par de citações" in err, (rc, err)

    print("test_achado: 6 checagens verdes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
