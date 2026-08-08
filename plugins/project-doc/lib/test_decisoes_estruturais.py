#!/usr/bin/env python3
"""As decisões estruturais caras só viram pergunta quando o projeto dá o sinal.

O defeito que esta suíte impede: a entrevista despejar o catálogo inteiro em
todo projeto. Perguntar sobre isolamento de cliente num projeto de um cliente
só, ou sobre resposta de modelo num projeto sem modelo nenhum, queima a sessão e
ensina o dono a responder no automático — que é o oposto de acordo.

O critério é literal: projeto sem banco, sem inteligência artificial e sem
multi-cliente recebe TRÊS perguntas, não as dez do catálogo.
"""

import json
import os
import shutil
import subprocess
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

# Um projeto que responde "sim" às quatro de segurança — cada resposta tem, no
# código, o dado que a confirma.
COM_SEGURANCA = dict(SECO)
COM_SEGURANCA["src/auth.js"] = "import jwt from 'jsonwebtoken';\n"
COM_SEGURANCA["db/cliente.sql"] = "CREATE TABLE cliente (cpf text, telefone text);\n"
COM_SEGURANCA["ops/backup.sh"] = "pg_dump frete > /var/dump.sql\n"
COM_SEGURANCA["docker-compose.yml"] = "services:\n  web:\n    ports:\n      - 80:80\n"


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

    print("as quatro de seguranca sao sempre as quatro, e sao perguntas de gente")
    ids_seg = [p.id for p in de.PILARES]
    check("sao quatro pilares", len(de.PILARES) == 4)
    check("nenhum id repetido", len(set(ids_seg)) == len(ids_seg))
    check("todo pilar procura um sinal que existe",
          all(p.procura in de.SINAIS_SEGURANCA for p in de.PILARES))
    check("todo pilar sabe nomear a ausencia do que procura",
          all(p.procura in de.PROCURADO for p in de.PILARES))
    check("toda pergunta e uma pergunta",
          all(p.pergunta.strip().endswith("?") for p in de.PILARES))
    check("nenhum pilar colide com o catalogo condicional",
          not (set(ids_seg) & {d.id for d in de.CATALOGO}))

    print("no projeto seco, as quatro vem com o dado que CONTRADIZ a resposta facil")
    raiz = projeto(SECO)
    try:
        seg = de.pilares_seguranca(raiz)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    for p in seg:
        print("     %s -> %r" % (p["id"], p["dado"]))
    check("as quatro sao perguntadas mesmo sem sinal nenhum", len(seg) == 4)
    check("cada uma das quatro tem dado", all(p.get("dado") for p in seg))
    check("as quatro contradizem",
          all(p["dado"]["sentido"] == "contradiz" for p in seg))
    check("a ausencia e nomeada em linguagem de gente",
          all(len(p["dado"].get("procurado", "")) > 20 for p in seg))

    print("no projeto que tem as quatro coisas, o dado CONFIRMA, com arquivo e trecho")
    raiz = projeto(COM_SEGURANCA)
    try:
        seg = de.pilares_seguranca(raiz)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    for p in seg:
        print("     %s -> %r" % (p["id"], p["dado"]))
    check("as quatro confirmam",
          all(p["dado"]["sentido"] == "confirma" for p in seg))
    check("cada confirmacao cita o arquivo do projeto",
          all(p["dado"].get("arquivo") for p in seg))
    check("cada confirmacao cita o trecho que a levantou",
          all(p["dado"].get("trecho") for p in seg))
    por_id = {p["id"]: p["dado"] for p in seg}
    check("o dado de pessoa veio da tabela de cliente",
          por_id["dado-de-pessoa"]["arquivo"].endswith("cliente.sql"))
    check("o quanto pode cair veio do backup",
          por_id["quanto-pode-cair"]["arquivo"].endswith("backup.sh"))

    print("lixo de dependencia nao vira dado de seguranca")
    ruido = dict(SECO)
    ruido["node_modules/jsonwebtoken/index.js"] = "// jwt\n"
    ruido["node_modules/cors/index.js"] = "// cors allow-origin\n"
    raiz = projeto(ruido)
    try:
        seg = de.pilares_seguranca(raiz)
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    check("node_modules nao confirma nada",
          all(p["dado"]["sentido"] == "contradiz" for p in seg))

    print("o comando que a skill roda IMPRIME as quatro, com o dado ao lado")
    raiz = projeto(COM_SEGURANCA)
    motor = os.path.join(AQUI, "decisoes_estruturais.py")
    try:
        texto = subprocess.run([sys.executable, motor, raiz],
                               capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL, start_new_session=True).stdout
        bruto = subprocess.run([sys.executable, motor, raiz, "--json"],
                               capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL, start_new_session=True).stdout
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    print("     ...%s" % texto[texto.find("seguranca:"):][:120].replace("\n", " | "))
    check("a saida de texto tem as quatro perguntas",
          all(p.pergunta in texto for p in de.PILARES))
    check("a saida de texto cola o dado em cada uma",
          texto.count("o projeto confirma:") + texto.count("o projeto contradiz:") == 4)
    dados = json.loads(bruto)
    check("o --json entrega os quatro pilares", len(dados.get("seguranca", [])) == 4)
    check("cada pilar do --json vem com o dado",
          all(p["dado"].get("sentido") for p in dados["seguranca"]))

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
    check("o kit tem a secao das quatro de seguranca",
          "As quatro de seguranca" in kit or "As quatro de segurança" in kit)
    seg_doc = kit.split("As quatro de seguran", 1)[-1].split("\n---", 1)[0]
    check("a secao de seguranca diz que a ausencia tambem e dado",
          "contradiz" in seg_doc)
    check("a secao de seguranca diz que essas nao tem gatilho",
          "sem sinal" in seg_doc and "não vale" in seg_doc)

    print("o passo de mineracao da skill roda o motor")
    skill = open(os.path.join(AQUI, "..", "skills", "start-doc", "SKILL.md"),
                 encoding="utf-8").read()
    minerar = skill.split("### 2 · Minerar", 1)[-1].split("\n### 3", 1)[0]
    check("o passo 2 invoca o motor",
          "decisoes_estruturais.py" in minerar)
    check("o passo 2 nomeia as quatro de seguranca",
          "seguran" in minerar and "sempre as quatro" in minerar)

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
