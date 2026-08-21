#!/usr/bin/env python3
"""orfaos.py — o trabalho que está no disco e não tem passo marcado.

Nasceu da corrida de 2026-08-13: 87 minutos, 4 tarefas entregues, 3 commits — e
ZERO passos marcados, porque o bloco não fechou antes da parada. A retomada
seguinte não sabia disso e mandaria refazer tudo.

O que este detector faz, e SÓ isto: cruza o que a árvore carrega (`git status
--porcelain`) e o que os commits desde o último tique tocaram com os passos
ABERTOS do plano, e devolve os ids cujo entregável já aparece mexido. É
SUSPEITA, nunca veredito — quem julga o órfão é o revisor por tarefa (F18.2), e
quem marca é o tique com prova (F18.3).

O caminho do entregável sai do campo `files` do passo quando ele existe, e só cai no
texto (title/desc/pronto) quando não existe — aí pelo MESMO recorte de
`scripts/plano_vs_codigo.py` (RE_CAMINHO, forma "caminho"). A prosa sozinha é peneira
furada: no plano de 2026-08-12, 3 dos 39 passos abertos nomeavam caminho no texto. A
leitura
do `pronto` não se reescreve aqui: aquele script julga se o critério se cumpre —
este só pergunta se o arquivo que o critério nomeia foi mexido.

Uso:
    python3 orfaos.py <plano.plan.json> [--root <raiz>]   # JSON na saída

stdlib only (requisito do repo).
"""
import argparse
import json
import os
import re
import subprocess
import sys

# O recorte de caminho de scripts/plano_vs_codigo.py:RE_CAMINHO, sem as âncoras —
# aqui ele varre o texto inteiro do passo, não só o critério isolado.
RE_CAMINHO = re.compile(r"[\w.@-]+(?:/[\w.@-]+)+\.\w+")


def _itens(no):
    """Todo passo do plano, em qualquer nível de aninhamento."""
    if isinstance(no, dict):
        if "id" in no and ("pronto" in no or "status" in no):
            yield no
        for v in no.values():
            for it in _itens(v):
                yield it
    elif isinstance(no, list):
        for v in no:
            for it in _itens(v):
                yield it


def _git(root, *args):
    try:
        r = subprocess.run(("git",) + args, cwd=root, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=30, start_new_session=True)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def ultimo_tique(plano):
    """A hora do passo marcado mais recente — a borda dos commits que interessam."""
    marcas = [i.get("done_at") for i in _itens(plano) if i.get("done_at")]
    return max(marcas) if marcas else None


def mexidos(root, desde=None):
    """Caminhos que a árvore suja carrega + os que os commits desde `desde` tocaram."""
    fora = set()
    # `-uall`: sem ele o git COLAPSA a pasta nova numa linha só ("?? plugins/") e o
    # entregável recém-criado — o caso mais comum de órfão — não bate com nada.
    for ln in _git(root, "status", "--porcelain", "-uall"):
        caminho = ln[3:].strip()
        if " -> " in caminho:          # rename: o que vale é o destino
            caminho = caminho.split(" -> ", 1)[1]
        fora.add(caminho.strip('"'))
    if desde:
        fora.update(_git(root, "log", "--since=%s" % desde, "--name-only",
                         "--pretty=format:"))
    return {c for c in fora if c}


def alvos_do_passo(item):
    """Os caminhos que o passo nomeia — o campo `files` primeiro, a prosa depois.

    Quando o passo declara `files`, essa lista É a resposta: ela nomeia o entregável
    inteiro, enquanto a prosa nomeia só o que coube na frase. Medido no plano de
    2026-08-12: dos 39 passos abertos, 3 tinham caminho no texto. Sem o campo, o
    recorte de prosa continua sendo tudo o que existe — por isso ele fica como queda,
    não como concorrente.
    """
    arquivos = item.get("files")
    if isinstance(arquivos, list):
        alvos = {str(f).strip() for f in arquivos if str(f).strip()}
        if alvos:
            return alvos
    texto = " ".join(str(item.get(k) or "") for k in ("title", "desc", "pronto"))
    return set(RE_CAMINHO.findall(texto))


def assuntos(root, desde=None):
    """Os assuntos dos commits desde o último tique — o id do passo costuma estar lá."""
    if not desde:
        return []
    return _git(root, "log", "--since=%s" % desde, "--pretty=format:%s")


def orfaos(plano, root):
    desde = ultimo_tique(plano)
    mudou = mexidos(root, desde)
    subjs = assuntos(root, desde)
    achados = []
    for item in _itens(plano):
        if item.get("status") == "done":
            continue
        ident = item.get("id") or ""
        alvos = alvos_do_passo(item)
        batidos = sorted(a for a in alvos
                         if any(m == a or m.endswith("/" + a) or a.endswith("/" + m)
                                for m in mudou))
        # O commit que nomeia o passo denuncia sozinho: entregou e não marcou.
        citado = [t for t in subjs if ident and re.search(r"\b%s\b" % re.escape(ident), t)]
        if batidos or citado:
            achados.append({"id": ident, "title": item.get("title"),
                            "status": item.get("status"), "paths": batidos,
                            "commits": citado})
    return achados


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("plano")
    ap.add_argument("--root", default=".", help="raiz do repositório conferido")
    args = ap.parse_args(argv)

    with open(args.plano, "r", encoding="utf-8") as fh:
        plano = json.load(fh)
    print(json.dumps({"orfaos": orfaos(plano, os.path.abspath(args.root))},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
