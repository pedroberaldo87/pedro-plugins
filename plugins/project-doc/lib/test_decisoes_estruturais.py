#!/usr/bin/env python3
"""As decisões estruturais caras só viram pergunta quando o projeto dá o sinal.

O defeito que esta suíte impede: a entrevista despejar o catálogo inteiro em
todo projeto. Perguntar sobre isolamento de cliente num projeto de um cliente
só, ou sobre resposta de modelo num projeto sem modelo nenhum, queima a sessão e
ensina o dono a responder no automático — que é o oposto de acordo.

O critério é literal: projeto sem banco, sem inteligência artificial e sem
multi-cliente recebe TRÊS perguntas, não as dez do catálogo.
"""

import os
import shutil
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import decisoes_estruturais as de  # noqa: E402

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def projeto(arquivos):
    """Cria um projeto de mentira e devolve a raiz. Chave = caminho relativo."""
    raiz = tempfile.mkdtemp(prefix="decisoes-")
    for rel, conteudo in arquivos.items():
        alvo = os.path.join(raiz, rel)
        d = os.path.dirname(alvo)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with open(alvo, "w", encoding="utf-8") as fh:
            fh.write(conteudo)
    return raiz


SECO = {
    "README.md": "# calculadora de frete\n\nRoda na máquina de quem usa.\n",
    "package.json": '{"name": "frete", "dependencies": {"chalk": "^5.0.0"}}\n',
    "src/frete.js": "export function frete(km) { return km * 2.5; }\n",
}

COM_BANCO = dict(SECO)
COM_BANCO["db/migrations/001_init.sql"] = "CREATE TABLE pedido (id serial);\n"

COM_TUDO = dict(COM_BANCO)
COM_TUDO["src/tenant.js"] = "const tenantId = req.headers['x-tenant-id'];\n"
COM_TUDO["src/resumo.py"] = "from anthropic import Anthropic\n"
COM_TUDO["worker/fila.py"] = "from celery import Celery\napp = Celery()\n"
COM_TUDO["src/pagar.js"] = "import Stripe from 'stripe';\n"


def main():
    print("o catalogo e fechado, e a maior parte dele e condicional")
    ids = [d.id for d in de.CATALOGO]
    check("o catalogo tem 10 decisoes", len(de.CATALOGO) == 10)
    check("nenhum id repetido", len(set(ids)) == len(ids))
    check("tres sao incondicionais",
          len([d for d in de.CATALOGO if d.gatilho is None]) == 3)
    check("todo gatilho de condicional existe em SINAIS",
          all(d.gatilho in de.SINAIS for d in de.CATALOGO if d.gatilho))
    check("toda decisao traz a pergunta em linguagem de gente",
          all(d.pergunta.strip().endswith("?") for d in de.CATALOGO))

    print("projeto sem banco, sem IA e sem multi-cliente recebe TRES perguntas")
    raiz = projeto(SECO)
    try:
        sinais = de.detectar(raiz)
        perguntas = de.perguntas(sinais)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    print("     sinais: %r" % (sorted(sinais),))
    print("     perguntas: %r" % ([p.id for p in perguntas],))
    check("nenhum sinal detectado", sinais == {})
    check("sao 3 perguntas, e nao as 10 do catalogo", len(perguntas) == 3)
    check("as 3 sao as incondicionais",
          all(p.gatilho is None for p in perguntas))

    print("o sinal do banco acende as duas perguntas de dado, com a pista")
    raiz = projeto(COM_BANCO)
    try:
        sinais = de.detectar(raiz)
        perguntas = de.perguntas(sinais)
        pista = sinais.get("persistencia", {}).get("arquivo", "")
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    print("     sinais: %r" % (sorted(sinais),))
    print("     perguntas: %r" % ([p.id for p in perguntas],))
    check("so o sinal de persistencia acendeu", sorted(sinais) == ["persistencia"])
    check("sao 5 perguntas (3 + as 2 de dado)", len(perguntas) == 5)
    check("a pista cita o arquivo que a levantou",
          pista.endswith("001_init.sql"))
    check("a pergunta de isolamento por cliente NAO entrou",
          "isolamento-por-cliente" not in [p.id for p in perguntas])

    print("projeto com todos os sinais recebe o catalogo inteiro")
    raiz = projeto(COM_TUDO)
    try:
        sinais = de.detectar(raiz)
        perguntas = de.perguntas(sinais)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    print("     sinais: %r" % (sorted(sinais),))
    check("os cinco sinais acenderam", len(sinais) == len(de.SINAIS))
    check("sao as 10 do catalogo", len(perguntas) == 10)

    print("lixo de dependencia nao inventa sinal")
    ruido = dict(SECO)
    ruido["node_modules/pg/index.js"] = "module.exports = require('postgres');\n"
    ruido["node_modules/openai/index.js"] = "// openai client\n"
    raiz = projeto(ruido)
    try:
        sinais = de.detectar(raiz)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    print("     sinais: %r" % (sorted(sinais),))
    check("node_modules nao acende sinal nenhum", sinais == {})

    print("a entrada da entrevista aponta o motor")
    kit = open(os.path.join(AQUI, "..", "skills", "start-doc", "references",
                            "authorial-kit.md"), encoding="utf-8").read()
    corpo = kit.split("## Como conduzir a entrevista", 1)
    check("o kit tem a secao Como conduzir a entrevista", len(corpo) == 2)
    trecho = corpo[1].split("\n---", 1)[0] if len(corpo) == 2 else ""
    check("a secao da entrevista chama o motor pelo nome",
          "decisoes_estruturais.py" in trecho)
    check("a secao diz que pergunta sem sinal nao e feita",
          "sem sinal" in trecho)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
