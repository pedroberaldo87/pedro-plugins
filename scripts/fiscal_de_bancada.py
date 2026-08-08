#!/usr/bin/env python3
"""fiscal_de_bancada.py — acusa sonda de depuração esquecida na bancada.

Um arquivo com nome que a suíte coleta (test_*.py, *_test.py, *.spec.ts) e que
ninguém rastreou no git é quase sempre uma sonda que alguém plantou pra investigar
uma coisa e esqueceu de recolher. Ela não aparece em diff nenhum, não sai em code
review, e derruba a suíte de todo mundo que rodar o coletor na árvore.

O fiscal varre e acusa quatro coisas:

  sonda        arquivo NÃO rastreado cujo nome a suíte coleta, em qualquer lugar
               da árvore;
  nao-declarado arquivo NÃO rastreado dentro de plugins/ — o que sobe pro
               marketplace é o que está rastreado, e o que não está nem rastreado
               nem ignorado é trabalho pela metade sem dono declarado.
  sem-chamador função nova (arquivo novo ou alterado desde o último commit) que
               nenhum caminho EXECUTÁVEL da árvore chama — nem o próprio arquivo
               dela. Citação em prosa (.md, .txt) não conta como chamada, e o
               teste da própria peça também não. Código bom que caminho nenhum
               invoca não cumpre critério nenhum: ele não roda, então não prova nada.
  aviso-no-vazio arquivo mexido que avisa pelo canal de erro (`>&2`, `sys.stderr`)
               e cujos consumidores, TODOS eles, jogam esse canal fora com
               `2>/dev/null`. Aviso escrito onde ninguém lê é aviso que não existe.

O que está RASTREADO nunca é acusado: os test_*.py rastreados são a suíte de verdade
do repositório. Um fiscal que multa trabalho legítimo é desligado no primeiro dia.
Ignorado pelo .gitignore também não é acusado — ali a ausência já foi declarada.

Uso:
    python3 scripts/fiscal_de_bancada.py            # varre o repo deste script
    python3 scripts/fiscal_de_bancada.py <caminho>  # varre outro repositório
    python3 scripts/fiscal_de_bancada.py --motivo sem-chamador [<caminho>]

O `--motivo` recorta a varredura a UM dos quatro motivos. É por ele que o gate de
commit cobra o eixo sem-chamador sozinho, sem que sonda de trabalho em andamento
(que ainda nem foi `git add`) trave o commit de outra pessoa.

Sai 0 quando a bancada está limpa, 1 quando acha, imprimindo o caminho de cada achado.
"""
import ast
import fnmatch
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# nomes que um coletor de teste pega sozinho, sem ninguém listar o arquivo
PADROES_DE_SUITE = ("test_*.py", "*_test.py", "*.spec.ts")

# arquivos onde uma chamada pode estar escrita (código, config, instrução)
EXTENSOES_DE_TEXTO = (".py", ".sh", ".bash", ".md", ".json", ".txt", ".ts",
                      ".js", ".mjs", ".html", ".yml", ".yaml", ".toml")

# nome que o próprio interpretador ou o coletor chama, sem ninguém escrever a chamada
NOMES_CHAMADOS_DE_FORA = ("main",)

# escrita no canal de aviso: `>&2` no shell, sys.stderr no Python
MARCAS_DE_AVISO = (re.compile(r">&\s*2"),
                   re.compile(r"sys\.stderr"))

# quem INVOCA um arquivo — doc que só cita o nome não é consumidor
EXTENSOES_DE_CHAMADA = (".py", ".sh", ".bash", ".json", ".yml", ".yaml")

# a chamada que joga o canal de aviso fora
DESCARTA_AVISO = re.compile(r"2>\s*(?:/dev/null|&\s*-)")


def _git(repo, *args):
    saida = subprocess.run(["git", "-C", repo] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, start_new_session=True)
    if saida.returncode != 0:
        return []
    return [linha for linha in saida.stdout.decode("utf-8", "replace").splitlines()
            if linha]


def nome_de_suite(caminho):
    base = os.path.basename(caminho)
    return any(fnmatch.fnmatch(base, p) for p in PADROES_DE_SUITE)


def _le(caminho):
    try:
        with open(caminho, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _arvore_de_texto(repo, nao_rastreados):
    """Todo arquivo da árvore onde uma chamada poderia estar escrita."""
    rastreados = _git(repo, "ls-files")
    vistos = []
    for rel in list(rastreados) + list(nao_rastreados):
        if rel.endswith(EXTENSOES_DE_TEXTO) and rel not in vistos:
            vistos.append(rel)
    return vistos


def _mexidos(repo, nao_rastreados, extensoes=(".py",)):
    """Arquivos novos ou alterados desde o último commit, nas extensões pedidas."""
    alterados = _git(repo, "diff", "--name-only", "HEAD")
    novos = []
    for rel in list(alterados) + list(nao_rastreados):
        if rel.endswith(extensoes) and not nome_de_suite(rel) and rel not in novos:
            novos.append(rel)
    return novos


def funcoes_novas(repo, nao_rastreados):
    """Devolve [(arquivo, nome, linha)] das funções de topo em arquivo mexido."""
    achadas = []
    for rel in _mexidos(repo, nao_rastreados):
        fonte = _le(os.path.join(repo, rel))
        try:
            arvore = ast.parse(fonte)
        except SyntaxError:
            continue
        for no in arvore.body:
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if no.name.startswith("_") or no.name in NOMES_CHAMADOS_DE_FORA:
                continue
            achadas.append((rel, no.name, no.lineno))
    return achadas


def _teste_da_peca(onde, rel):
    """True se `onde` é o arquivo de teste da própria peça `rel`."""
    if not nome_de_suite(onde):
        return False
    caule = os.path.splitext(os.path.basename(rel))[0]
    base = os.path.basename(onde)
    return base in ("test_%s.py" % caule, "%s_test.py" % caule,
                    "%s.spec.ts" % caule)


def sem_chamador(repo, nao_rastreados):
    """Função nova que nenhum caminho EXECUTÁVEL da árvore chama.

    Menção em prosa (.md, .txt) não é chamada, e o teste da própria peça não
    conta como consumidor: um teste sozinho não liga a peça a caminho nenhum
    que rode em produção.
    """
    novas = funcoes_novas(repo, nao_rastreados)
    if not novas:
        return []
    texto = {rel: _le(os.path.join(repo, rel))
             for rel in _arvore_de_texto(repo, nao_rastreados)
             if rel.endswith(EXTENSOES_DE_CHAMADA)}
    orfas = []
    for rel, nome, linha in novas:
        padrao = re.compile(r"\b%s\b" % re.escape(nome))
        chamada = False
        for onde, conteudo in texto.items():
            if _teste_da_peca(onde, rel):
                continue
            for n, fileira in enumerate(conteudo.splitlines(), 1):
                if onde == rel and n == linha:
                    continue  # a própria linha do def não é chamada
                if padrao.search(fileira):
                    chamada = True
                    break
            if chamada:
                break
        if not chamada:
            orfas.append("%s:%d %s()" % (rel, linha, nome))
    return orfas


def aviso_no_vazio(repo, nao_rastreados):
    """Arquivo mexido que avisa por stderr e cujos consumidores descartam stderr."""
    mexidos = _mexidos(repo, nao_rastreados, (".py", ".sh", ".bash"))
    if not mexidos:
        return []
    texto = {rel: _le(os.path.join(repo, rel))
             for rel in _arvore_de_texto(repo, nao_rastreados)
             if rel.endswith(EXTENSOES_DE_CHAMADA)}
    mudos = []
    for rel in mexidos:
        fonte = _le(os.path.join(repo, rel))
        if not any(marca.search(fonte) for marca in MARCAS_DE_AVISO):
            continue
        base = os.path.basename(rel)
        consumidores = 0
        descartam = 0
        for onde, conteudo in texto.items():
            if onde == rel:
                continue
            for fileira in conteudo.splitlines():
                if base not in fileira:
                    continue
                consumidores += 1
                if DESCARTA_AVISO.search(fileira):
                    descartam += 1
        if consumidores and consumidores == descartam:
            mudos.append("%s (avisa por stderr; %d consumidor(es), todos com 2>/dev/null)"
                         % (rel, consumidores))
    return mudos


def varre(repo):
    """Devolve [(motivo, caminho)] ordenado por caminho."""
    nao_rastreados = _git(repo, "ls-files", "--others", "--exclude-standard")
    achados = []
    for caminho in nao_rastreados:
        if nome_de_suite(caminho):
            achados.append(("sonda", caminho))
        elif caminho.startswith("plugins/"):
            achados.append(("nao-declarado", caminho))
    for orfa in sem_chamador(repo, nao_rastreados):
        achados.append(("sem-chamador", orfa))
    for mudo in aviso_no_vazio(repo, nao_rastreados):
        achados.append(("aviso-no-vazio", mudo))
    return sorted(achados, key=lambda a: a[1])


def main(argv):
    motivo_pedido = ""
    resto = []
    args = list(argv[1:])
    while args:
        arg = args.pop(0)
        if arg == "--motivo":
            motivo_pedido = args.pop(0) if args else ""
        else:
            resto.append(arg)
    repo = os.path.abspath(resto[0]) if resto else ROOT
    achados = varre(repo)
    if motivo_pedido:
        achados = [a for a in achados if a[0] == motivo_pedido]
    if not achados:
        print("fiscal-de-bancada: bancada limpa")
        return 0
    for motivo, caminho in achados:
        print("%-14s %s" % (motivo, caminho))
    print("")
    print("fiscal-de-bancada: %d achado(s). Rastreie no git, apague, ou declare no .gitignore."
          % len(achados))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
