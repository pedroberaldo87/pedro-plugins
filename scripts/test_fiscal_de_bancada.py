#!/usr/bin/env python3
"""Checagem do fiscal_de_bancada.py.

Monta um repositório git de mentira num diretório temporário, com uma suíte
LEGÍTIMA rastreada dentro dele, e verifica os dois lados: bancada limpa sai 0, e
sonda plantada de propósito sai 1 com o caminho impresso.

Os nomes de arquivo de teste plantados aqui são montados por concatenação
("test" + "_") pra que nenhum coletor rodando na árvore de verdade tente executá-los.
"""
import os
import shutil
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
FISCAL = os.path.join(AQUI, "fiscal_de_bancada.py")

ok = 0


def check(nome, cond):
    global ok
    assert cond, "FALHOU: %s" % nome
    ok += 1


def git(repo, *args):
    subprocess.run(["git", "-C", repo] + list(args), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)


def escreve(repo, rel, conteudo="# nada\n"):
    caminho = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(conteudo)
    return rel


def rotulo(saida, alvo):
    """Motivo da primeira linha de achado que cita alvo."""
    for fileira in saida.splitlines():
        if alvo in fileira:
            return fileira.split()[0]
    return ""


def como_o_git(rel):
    """O caminho na forma que o fiscal IMPRIME — barra normal, sempre.

    Ele lista pelo `git ls-files`, e o git emite `/` em qualquer sistema. O teste
    monta o esperado com `os.path.join`, que no Windows devolve `\\`: o mesmo
    arquivo, dois textos, e o `in saida` dizia que a sonda plantada não aparecia.
    """
    return rel.replace(os.sep, "/")


def roda(repo, *flags):
    p = subprocess.run([sys.executable, FISCAL] + list(flags) + [repo],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# ─── repositório de mentira, com suíte legítima rastreada ────────────────────
repo = tempfile.mkdtemp(prefix="fiscal-bancada-")
git(repo, "init", "-q")
git(repo, "config", "user.email", "t@example.com")
git(repo, "config", "user.name", "t")

legitimo = "test" + "_da_suite_real.py"
escreve(repo, os.path.join("plugins", "algum", "lib", legitimo))
escreve(repo, os.path.join("plugins", "algum", "lib", "motor.py"))
escreve(repo, ".gitignore", "saida-gerada/\n")
git(repo, "add", "-A")
git(repo, "commit", "-qm", "suite legitima")

# ─── caso limpo: sai 0, e a suíte RASTREADA não é acusada ────────────────────
codigo, saida = roda(repo)
check("repo limpo sai 0", codigo == 0)
check("suite rastreada nao e acusada", como_o_git(legitimo) not in saida)

# ─── arquivo ignorado pelo .gitignore não é acusado ──────────────────────────
escreve(repo, os.path.join("saida-gerada", "relatorio.html"))
codigo, saida = roda(repo)
check("arquivo ignorado nao e acusado", codigo == 0)

# ─── sonda plantada: sai 1 e imprime o caminho ───────────────────────────────
sonda = os.path.join("plugins", "algum", "lib", "test" + "_sonda_esquecida.py")
escreve(repo, sonda)
codigo, saida = roda(repo)
check("sonda plantada sai 1", codigo == 1)
check("sonda plantada aparece na saida", como_o_git(sonda) in saida)
check("sonda plantada e rotulada sonda",
      "sonda" in saida.split(como_o_git(sonda))[0].splitlines()[-1])

# ─── sonda fora de plugins/ também é acusada ─────────────────────────────────
sonda2 = os.path.join("scripts", "algo" + "_test.py")
escreve(repo, sonda2)
codigo, saida = roda(repo)
check("sonda fora de plugins e acusada", codigo == 1 and como_o_git(sonda2) in saida)

sonda3 = os.path.join("web", "pagina.spec.ts")
escreve(repo, sonda3)
codigo, saida = roda(repo)
check("sonda .spec.ts e acusada", como_o_git(sonda3) in saida)

# ─── arquivo não declarado dentro de plugins/ ────────────────────────────────
orfao = os.path.join("plugins", "algum", "rascunho.md")
escreve(repo, orfao)
codigo, saida = roda(repo)
check("arquivo nao declarado em plugins/ e acusado",
      "nao-declarado" in saida.split(como_o_git(orfao))[0].splitlines()[-1])

# ─── arquivo comum FORA de plugins/ não é acusado ────────────────────────────
escreve(repo, os.path.join("docs", "rascunho.md"))
codigo, saida = roda(repo)
check("arquivo comum fora de plugins nao e acusado",
      como_o_git(os.path.join("docs", "rascunho.md")) not in saida)

# ─── volta ao limpo depois de recolher as sondas ─────────────────────────────
for rel in (sonda, sonda2, sonda3, orfao):
    os.remove(os.path.join(repo, rel))
os.remove(os.path.join(repo, "docs", "rascunho.md"))
codigo, saida = roda(repo)
check("bancada recolhida volta a sair 0", codigo == 0)

# ─── peça nova que ninguém chama ─────────────────────────────────────────────
orfa = escreve(repo, os.path.join("plugins", "algum", "lib", "peca_orfa.py"),
               "def peca_que_ninguem_chama():\n    return 1\n")
codigo, saida = roda(repo)
check("funcao nova sem chamador sai 1", codigo == 1)
check("funcao nova sem chamador aparece na saida", "peca_que_ninguem_chama" in saida)
check("funcao sem chamador e rotulada sem-chamador",
      "sem-chamador" in saida.split("peca_que_ninguem_chama")[0].splitlines()[-1])

# ─── --motivo recorta a varredura a um eixo só (é como o gate de commit cobra) ─
sonda_junto = escreve(repo, os.path.join("plugins", "algum", "test" + "_junto.py"))
codigo, saida = roda(repo, "--motivo", "sem-chamador")
check("--motivo sem-chamador acusa a funcao orfa", codigo == 1)
check("--motivo sem-chamador ignora a sonda", como_o_git(sonda_junto) not in saida)
os.remove(os.path.join(repo, orfa))
codigo, saida = roda(repo, "--motivo", "sem-chamador")
check("--motivo sem-chamador sai 0 quando so restam outros motivos", codigo == 0)
os.remove(os.path.join(repo, sonda_junto))

# ─── peça nova chamada DENTRO do próprio arquivo não é acusada ───────────────
ligada = escreve(repo, os.path.join("plugins", "algum", "lib", "peca_ligada.py"),
                 "def peca_ligada_ao_produto():\n    return 1\n\n\n"
                 "print(peca_ligada_ao_produto())\n")
codigo, saida = roda(repo)
check("funcao chamada no proprio arquivo nao e acusada",
      "peca_ligada_ao_produto" not in saida)
os.remove(os.path.join(repo, ligada))

# ─── peça nova chamada por OUTRO arquivo não é acusada ───────────────────────
solta = escreve(repo, os.path.join("plugins", "algum", "lib", "peca_solta.py"),
                "def peca_chamada_de_fora():\n    return 1\n")
quem_chama = escreve(repo, os.path.join("plugins", "algum", "lib", "consumidor.py"),
                     "from peca_solta import peca_chamada_de_fora\n"
                     "peca_chamada_de_fora()\n")
codigo, saida = roda(repo)
check("funcao chamada por outro arquivo nao e acusada",
      "peca_chamada_de_fora" not in saida)
os.remove(os.path.join(repo, solta))
os.remove(os.path.join(repo, quem_chama))

# ─── peça só CITADA em prosa (.md) continua sendo acusada ────────────────────
citada = escreve(repo, os.path.join("plugins", "algum", "lib", "peca_citada.py"),
                 "def peca_so_citada_em_prosa():\n    return 1\n")
prosa = escreve(repo, os.path.join("plugins", "algum", "README.md"),
                "A `peca_so_citada_em_prosa()` faz tal coisa.\n")
codigo, saida = roda(repo, "--motivo", "sem-chamador")
check("peca so citada em .md e acusada",
      codigo == 1 and "peca_so_citada_em_prosa" in saida)
os.remove(os.path.join(repo, prosa))

# ─── peça referida SÓ pelo teste dela mesma continua sendo acusada ───────────
so_teste = escreve(repo, os.path.join("plugins", "algum", "lib", "peca_testada.py"),
                   "def peca_so_no_teste():\n    return 1\n")
teste_dela = escreve(repo,
                     os.path.join("plugins", "algum", "lib",
                                  "test" + "_peca_testada.py"),
                     "from peca_testada import peca_so_no_teste\n"
                     "assert peca_so_no_teste() == 1\n")
codigo, saida = roda(repo, "--motivo", "sem-chamador")
check("peca referida so pelo proprio teste e acusada",
      codigo == 1 and "peca_so_no_teste" in saida)

# ─── mas um hook de produto chamando a peça basta pra ela não ser acusada ────
hook = escreve(repo, os.path.join("plugins", "algum", "hooks", "gancho.sh"),
               "python3 -c 'from peca_testada import peca_so_no_teste;"
               " peca_so_no_teste()'\n")
codigo, saida = roda(repo, "--motivo", "sem-chamador")
check("peca chamada por hook de produto nao e acusada",
      "peca_so_no_teste" not in saida)
for rel in (citada, so_teste, teste_dela, hook):
    os.remove(os.path.join(repo, rel))

# ─── função antiga já commitada e intocada não é acusada ─────────────────────
escreve(repo, os.path.join("plugins", "algum", "lib", "antigo.py"),
        "def funcao_antiga_sem_uso():\n    return 1\n")
git(repo, "add", "-A")
git(repo, "commit", "-qm", "peca antiga")
codigo, saida = roda(repo)
check("funcao antiga intocada nao e acusada", codigo == 0)
check("funcao antiga intocada fica fora da saida", "funcao_antiga_sem_uso" not in saida)

# ─── aviso que só existe no canal que todo consumidor joga fora ──────────────
avisador = escreve(repo, os.path.join("scripts", "avisador.sh"),
                   'echo "usei o destino de reserva" >&2\n')
descarta = escreve(repo, os.path.join("scripts", "roda_tudo.sh"),
                   "bash scripts/avisador.sh 2>/dev/null\n")
codigo, saida = roda(repo)
check("aviso so no canal descartado sai 1", codigo == 1)
check("aviso so no canal descartado aparece na saida", "avisador.sh" in saida)
check("aviso mudo e rotulado aviso-no-vazio",
      rotulo(saida, "avisador.sh") == "aviso-no-vazio")

# ─── basta UM consumidor que não descarta para o aviso valer ─────────────────
escuta = escreve(repo, os.path.join("scripts", "roda_direito.sh"),
                 "bash scripts/avisador.sh\n")
codigo, saida = roda(repo)
check("aviso com um consumidor que escuta nao e acusado", "avisador.sh" not in saida)
os.remove(os.path.join(repo, escuta))

# ─── aviso em Python (sys.stderr) com consumidor que descarta ────────────────
avisador_py = escreve(repo, os.path.join("scripts", "reserva.py"),
                      "import sys\n"
                      'print("caiu na reserva", file=sys.stderr)\n')
escreve(repo, descarta,
        "bash scripts/avisador.sh 2>/dev/null\n"
        "python3 scripts/reserva.py 2> /dev/null\n")
codigo, saida = roda(repo)
check("aviso por sys.stderr descartado e acusado",
      rotulo(saida, "reserva.py") == "aviso-no-vazio")
os.remove(os.path.join(repo, avisador_py))

# ─── arquivo que avisa mas que NINGUÉM chama não é acusado por este motivo ───
os.remove(os.path.join(repo, descarta))
codigo, saida = roda(repo)
check("aviso sem consumidor nenhum nao e acusado de canal descartado",
      codigo == 0 and "avisador.sh" not in saida)
os.remove(os.path.join(repo, avisador))

shutil.rmtree(repo, ignore_errors=True)
print("fiscal_de_bancada: %d checagens OK" % ok)
