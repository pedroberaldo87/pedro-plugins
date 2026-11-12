#!/usr/bin/env python3
"""O cobrador public-repo do medidor contra o contrato de saída de verdade.

O gate `scripts/public_repo_check.py` não devolve mais o trecho (`excerpt`) e diz,
pelo código de saída, quando NÃO mediu: 1 = achou dado pessoal, 2 = não mediu (git
falhou, lista vazia, arquivo ilegível), 3 = termos não rodaram sob CI. O consumidor
tinha que (a) não ler campo removido e (b) nunca transformar "não mediu" em "limpo".

Roda o gate real numa cópia descartável do repositório (`medidor.ROOT` aponta para
ela), então vale com o repositório de verdade limpo — que escondia o defeito.

    python3 plugins/vistoria/lib/test_medidor_public_repo.py

stdlib only. Todo conteúdo que casa uma regra é montado por concatenação.
"""
import os
import shutil
import stat
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import medidor  # noqa: E402
from achado import erros_de_achado  # noqa: E402

ROOT_REAL = medidor.ROOT
GATE = os.path.join(ROOT_REAL, "scripts", "public_repo_check.py")

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def _rm(func, path, _exc):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def env_limpo(**extra):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    env.pop("CI", None)
    env.pop("GIT_CEILING_DIRECTORIES", None)
    env.update(extra)
    return env


def repo_de_mentira(conteudo, termos=True, com_git=True):
    raiz = tempfile.mkdtemp(prefix="vistoria-prc-")
    os.makedirs(os.path.join(raiz, "scripts"))
    shutil.copy(GATE, os.path.join(raiz, "scripts", "public_repo_check.py"))
    if termos:
        with open(os.path.join(raiz, "scripts", "public_repo_terms"), "w",
                  encoding="utf-8") as fh:
            fh.write("# nome-proprio\nzzfulanozz\n")
    with open(os.path.join(raiz, "nota.md"), "w", encoding="utf-8") as fh:
        fh.write(conteudo)
    if com_git:
        for args in (["init", "-q"], ["add", "nota.md"]):
            subprocess.run(["git", "-C", raiz] + args, check=True, capture_output=True,
                           env=env_limpo(), stdin=subprocess.DEVNULL)
    return raiz


def mede_em(raiz, **env):
    """Roda o cobrador public-repo do medidor sobre `raiz`; devolve (achados, falhas)."""
    antes_root, antes_env = medidor.ROOT, dict(os.environ)
    medidor.ROOT = raiz
    # Montar o ambiente ANTES de limpar: env_limpo() parte de os.environ, e com ele já
    # vazio o filho ficava sem PATH/SystemRoot — no Windows o `git` some (WinError 2).
    limpo = env_limpo(**env)
    os.environ.clear()
    os.environ.update(limpo)
    try:
        return medidor.mede(["public-repo"])
    finally:
        medidor.ROOT = antes_root
        os.environ.clear()
        os.environ.update(antes_env)


CAMINHO_RUIM = "cd %sfulano/app\n" % "/Users/"   # casa "caminho-de-maquina"
LIMPO = "nada aqui\n"


def main():
    print("test_medidor_public_repo")

    # (1) achado de verdade (exit 1): antes, KeyError('excerpt') e o cobrador sumia.
    raiz = repo_de_mentira(CAMINHO_RUIM)
    try:
        achados, nao = mede_em(raiz)
    finally:
        shutil.rmtree(raiz, onerror=_rm)
    checa("achado: o cobrador não quebra", "public-repo" not in nao, repr(nao))
    checa("achado: vira 1 achado", len(achados) == 1, repr(achados))
    if achados:
        a = achados[0]
        checa("achado: onde é arquivo:linha", a["onde"] == "nota.md:1", a["onde"])
        checa("achado: a regra vai junto", a["regra"] == "caminho-de-maquina", a["regra"])
        checa("achado: a prova é o lugar (arquivo:linha:coluna), sem trecho",
              a["prova"].startswith("nota.md:1:") and "fulano" not in str(a),
              repr(a["prova"]))
        checa("achado: passa no validador", erros_de_achado(a) == [], repr(erros_de_achado(a)))

    # (2) exit 2: git falhou. Antes, ok:false + findings:[] lia como "0 achados".
    raiz = repo_de_mentira(LIMPO, com_git=False)
    try:
        achados, nao = mede_em(raiz, GIT_CEILING_DIRECTORIES=os.path.dirname(raiz))
    finally:
        shutil.rmtree(raiz, onerror=_rm)
    checa("exit 2: nenhum achado inventado", achados == [], repr(achados))
    checa("exit 2: NÃO MEDIDO, não limpo", "public-repo" in nao, repr(nao))

    # (3) exit 3: termos ausentes sob CI.
    raiz = repo_de_mentira(LIMPO, termos=False)
    try:
        achados, nao = mede_em(raiz, CI="true")
    finally:
        shutil.rmtree(raiz, onerror=_rm)
    checa("exit 3: NÃO MEDIDO, não limpo", achados == [] and "public-repo" in nao, repr(nao))

    # (4) exit 0 mas terms_checked:false (local, sem lista): estrutural só — não é limpo.
    raiz = repo_de_mentira(LIMPO, termos=False)
    try:
        achados, nao = mede_em(raiz)
    finally:
        shutil.rmtree(raiz, onerror=_rm)
    checa("terms_checked=false: NÃO MEDIDO por inteiro", "public-repo" in nao, repr(nao))

    # (5) arquivo rastreado ilegível (exit 2 com `unreadable`).
    if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0:
        raiz = repo_de_mentira(LIMPO)
        fechado = os.path.join(raiz, "nota.md")
        os.chmod(fechado, 0)
        try:
            achados, nao = mede_em(raiz)
        finally:
            os.chmod(fechado, stat.S_IRUSR | stat.S_IWUSR)
            shutil.rmtree(raiz, onerror=_rm)
        checa("arquivo ilegível: NÃO MEDIDO", achados == [] and "public-repo" in nao, repr(nao))

    # (6) o caso limpo de verdade continua limpo (e medido).
    raiz = repo_de_mentira(LIMPO)
    try:
        achados, nao = mede_em(raiz)
    finally:
        shutil.rmtree(raiz, onerror=_rm)
    checa("limpo e medido: 0 achados e nada não-medido", achados == [] and not nao,
          repr((achados, nao)))

    # (7) o envelope --json carrega o não-medido: quem lê só `achados` não pode ver "limpo".
    raiz = repo_de_mentira(LIMPO, termos=False)
    antes = medidor.ROOT
    medidor.ROOT = raiz
    try:
        import io
        import json
        buf, velho = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            medidor.main(["public-repo", "--json"])
        finally:
            sys.stdout = velho
        env = json.loads(buf.getvalue())
    finally:
        medidor.ROOT = antes
        shutil.rmtree(raiz, onerror=_rm)
    checa("--json: _nao_medidos lista o cobrador",
          "public-repo" in (env.get("_nao_medidos") or {}), repr(env)[:200])

    print("\n%s" % ("FALHOU: " + ", ".join(falhas) if falhas else "tudo verde"))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
