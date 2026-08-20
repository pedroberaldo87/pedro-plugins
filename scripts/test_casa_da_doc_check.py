#!/usr/bin/env python3
"""O cobrador do caminho de doc cravado morde de verdade — provado por mutação."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anti_slop_inventario as asi  # noqa: E402
import casa_da_doc_check as chk  # noqa: E402

# O caminho da mutação nasce em dois pedaços de propósito: escrito inteiro nesta linha
# ele seria o próprio defeito que este arquivo cobra, e a suíte reprovaria a si mesma.
CRAVADO = ".claude" + "/docs/architecture.md"


def test_o_repositorio_de_hoje_esta_verde():
    assert chk.main() == 0, "a dívida de hoje passou do teto — mediu-se onde?"


def test_arquivo_novo_com_caminho_cravado_fica_vermelho():
    """A mutação: um ponto a mais que a dívida medida, e o check sai 1."""
    alvos = asi.universo()
    assert chk.conta(alvos) <= asi.TETO["A"]
    mutante = alvos + [("plugins/inventado/lib/x.py", f'abrir("{CRAVADO}")')]
    assert chk.conta(mutante) == chk.conta(alvos) + 1
    assert chk.main(mutante) == 1


def test_a_linha_com_motivo_escrito_e_isenta():
    """`casa-ok:` só isenta com o motivo escrito — carimbo pelado continua contando."""
    marca = asi.ISENCAO_CASA
    com = [("plugins/inventado/lib/x.py", f'abrir("{CRAVADO}")  # {marca} exemplo em prosa')]
    pelado = [("plugins/inventado/lib/x.py", f'abrir("{CRAVADO}")  # {marca}')]
    assert chk.conta(com) == 0
    assert chk.conta(pelado) == 1


def test_o_script_roda_pela_linha_de_comando():
    r = subprocess.run([sys.executable,
                        os.path.join(asi.RAIZ, "scripts", "casa_da_doc_check.py")],
                       cwd=asi.RAIZ, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    assert r.returncode == 0, r.stdout + r.stderr


if __name__ == "__main__":
    for _nome, _fn in sorted(globals().items()):
        if _nome.startswith("test_") and callable(_fn):
            _fn()
            print("  ok", _nome)
    print("ok")
