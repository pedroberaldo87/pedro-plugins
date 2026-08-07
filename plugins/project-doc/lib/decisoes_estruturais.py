#!/usr/bin/env python3
"""As decisões estruturais caras — e o sinal que decide se cada uma é perguntada.

São caras porque decidir tarde custa reescrita: quem é dono do dado, como o
esquema evolui, o que acontece quando o modelo devolve lixo. O erro fácil é
transformar isso num questionário fixo e despejar as dez em todo projeto — o
dono responde as sete que não são dele no automático, e as três que eram dele
vêm no mesmo automático.

Por isso o catálogo é quase todo CONDICIONAL, e o gatilho é o próprio projeto
minerado: a pergunta sobre dado só aparece quando existe dado guardado, a de
isolamento só quando existe mais de um cliente, a de modelo só quando existe
modelo. Projeto sem pista nenhuma recebe as três incondicionais e mais nada.

O sinal vem com a PISTA — arquivo e trecho —, porque a regra da entrevista
(`authorial-kit.md`, "Como conduzir a entrevista") é perguntar sempre com o
insumo à vista. Pista alimenta a pergunta; nunca vira a resposta.

As quatro perguntas de SEGURANÇA seguem a regra oposta, e de propósito: elas são
sempre feitas — quem acessa o quê, que dado de pessoa fica guardado, quanto pode
cair, o que fica exposto. Segurança adiada não é economia de pergunta, é dívida.
O que o projeto minerado decide não é SE elas entram, é com que DADO elas entram:
achar a biblioteca de papel/permissão confirma a resposta "só o dono edita"; não
achar nada disso a contradiz. Ausência de dado também é dado, e é o que muda a
conversa de opinião para constatação.

Uso:
    from decisoes_estruturais import detectar, perguntas, pilares_seguranca
    sinais = detectar(raiz)          # {"persistencia": {"arquivo":…, "trecho":…}}
    for p in perguntas(sinais):      # só as que o projeto acendeu
        ...
    for p in pilares_seguranca(raiz):  # sempre as quatro, cada uma com o dado
        ...

    python3 decisoes_estruturais.py [raiz] [--json]

stdlib only (requisito do repo).
"""

import collections
import json
import os
import re
import sys

# Poda de varredura: a mesma do `collect_engine.IGNORE_DIRS`. Dependência
# baixada não é decisão do dono — `node_modules/pg` acenderia o sinal de banco
# num projeto que não guarda nada.
IGNORE_DIRS = {"node_modules", ".git", ".claude", ".venv", "venv", "__pycache__",
               "dist", "build", ".next", ".turbo", "target", "vendor", "coverage",
               ".cache", ".pytest_cache", ".ruff_cache", ".mypy_cache", "_archive",
               "_template", "worktrees", ".worktrees", ".playwright-mcp", ".idea",
               ".vscode"}

# Só arquivo que uma pessoa escreveu. Binário e minificado não viram pista.
EXTENSOES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".sql", ".json",
             ".yaml", ".yml", ".toml", ".md", ".txt", ".sh", ".rb", ".go", ".java",
             ".kt", ".php", ".rs", ".prisma", ".env", ".ini", ".cfg", ".tf"}
NOMES = {"Dockerfile", "Makefile", "Gemfile", "Procfile", "requirements.txt"}

MAX_ARQUIVOS = 4000      # teto de varredura: pista é amostra, não inventário
MAX_BYTES = 200000       # arquivo maior que isto é dado gerado, não código autoral

# ── os cinco sinais ────────────────────────────────────────────────────────
# Cada um é um termo que só aparece quando a coisa existe de verdade no projeto.
SINAIS = {
    "persistencia": re.compile(
        r"(?i)\b(create\s+table|migrations?|postgres\w*|mysql|mariadb|mongodb|"
        r"mongoose|sqlite\w*|sqlalchemy|prisma|alembic|liquibase|supabase|"
        r"dynamodb|firestore|typeorm|knex)\b"),
    "inteligencia": re.compile(
        # `generative-?ai` e não `gemini`: o pointer `GEMINI.md` que este mesmo
        # repo escreve não é uso de modelo — é arquivo de roteamento de doc.
        r"(?i)\b(anthropic|openai|langchain|llama[_-]?index|huggingface|ollama|"
        r"bedrock|vertexai|generative-?ai|transformers|embeddings?)\b"),
    "multi_cliente": re.compile(
        r"(?i)\b(multi-?tenan\w*|tenant[_-]?id|tenantid|x-tenant-id|"
        r"organization_id|account_id|workspace_id)\b"),
    "trabalho_assincrono": re.compile(
        r"(?i)\b(celery|sidekiq|bullmq|resque|rabbitmq|amqp|kafka|"
        r"pubsub|sqs|temporal|worker[_-]?queue|job[_-]?queue)\b"),
    "dinheiro": re.compile(
        r"(?i)\b(stripe|paypal|pagarme|pagar\.me|mercadopago|braintree|adyen|"
        r"iugu|checkout[_-]?session|subscription[_-]?id)\b"),
}

# ── o catálogo ─────────────────────────────────────────────────────────────
# `gatilho = None` é incondicional: todo projeto que sobe pra algum lugar
# encara as três, tenha o tamanho que tiver.
Decisao = collections.namedtuple("Decisao", "id gatilho pergunta porque")

CATALOGO = [
    Decisao(
        "fronteira-de-subida", None,
        "Isso sobe como uma peça só, ou em pedaços que sobem separados?",
        "É a decisão que mais custa desfazer: separar depois obriga a inventar "
        "contrato entre as partes que hoje se chamam direto."),
    Decisao(
        "volta-atras", None,
        "Quando uma versão sai ruim, como você volta para a anterior?",
        "Sem resposta, a primeira versão ruim vira madrugada de conserto ao vivo."),
    Decisao(
        "sinal-de-quebra", None,
        "Como você descobre que quebrou, antes de alguém te contar?",
        "Se a resposta é 'o usuário avisa', toda meta de disponibilidade é torcida."),
    Decisao(
        "dono-do-dado", "persistencia",
        "Quem pode escrever em cada pedaço do dado — e quem só lê?",
        "Dois donos escrevendo a mesma coisa é o defeito que só aparece em produção, "
        "e sempre como dado errado."),
    Decisao(
        "evolucao-do-esquema", "persistencia",
        "Como o formato do dado muda depois que já tem gente usando?",
        "Mudar formato com dado dentro é a manobra mais cara que existe; decidida "
        "no começo, ela é rotina."),
    Decisao(
        "isolamento-por-cliente", "multi_cliente",
        "O que garante que o dado de um cliente nunca apareça para outro?",
        "Vazamento entre clientes não tem conserto depois — a confiança já foi."),
    Decisao(
        "resposta-nao-confiavel", "inteligencia",
        "O que acontece quando o modelo devolve uma resposta errada ou vazia?",
        "Resposta de modelo não é retorno de função: ela pode estar bem formada e "
        "errada ao mesmo tempo."),
    Decisao(
        "teto-de-custo", "inteligencia",
        "Qual é o teto de gasto por uso, e o que acontece quando ele estoura?",
        "Custo por chamada sem teto é a conta que chega depois do sucesso."),
    Decisao(
        "entrega-do-trabalho-longo", "trabalho_assincrono",
        "Quando um trabalho demorado falha no meio, ele repete ou se perde?",
        "Repetir sem cuidado cobra duas vezes; perder em silêncio some com o pedido."),
    Decisao(
        "dinheiro-em-transito", "dinheiro",
        "O que garante que uma cobrança não aconteça duas vezes?",
        "Cobrança repetida é o erro que o usuário percebe primeiro e perdoa por último."),
]


# ── os quatro pilares de segurança ─────────────────────────────────────────
# Estes não têm gatilho: são sempre perguntados. O que o projeto decide é o
# DADO que vai junto — o termo encontrado (confirma) ou a falta dele (contradiz).
SINAIS_SEGURANCA = {
    "controle-de-acesso": re.compile(
        r"(?i)(\b(passport|next-?auth|auth0|clerk|keycloak|devise|pundit|"
        r"cancancan|casbin|oauth2?|openid|jsonwebtoken|\bjwt\b|rbac|"
        r"authoriz(e|ed|ation)|autoriza(cao|ção)|role[_-]?based|"
        r"is[_-]?admin|current[_-]?user|require[sd]?[_-]?auth|login[_-]?required|"
        r"row[_-]?level[_-]?security)\b)"),
    "dado-de-pessoa": re.compile(
        r"(?i)(\b(cpf|cnpj|\bssn\b|\bpii\b|lgpd|gdpr|dados?[_-]?pessoa\w*|"
        r"personal[_-]?data|password[_-]?hash|senha|"
        r"phone[_-]?number|telefone|date[_-]?of[_-]?birth|data[_-]?de[_-]?nascimento|"
        r"endereco|endereço|address[_-]?line|card[_-]?number|credit[_-]?card|"
        r"user[_-]?email|customer[_-]?email)\b)"),
    "quanto-pode-cair": re.compile(
        r"(?i)(\b(backup\w*|pg_?dump|mysqldump|health[_-]?check|healthcheck|"
        r"uptime|\bsla\b|\brpo\b|\brto\b|point-?in-?time|"
        r"disaster[_-]?recovery|failover|replicas?)\b|restart:)"),
    "o-que-fica-exposto": re.compile(
        r"(?i)(\bports?:|\bexpose\b|0\.0\.0\.0|\bcors\b|allow[_-]?origin|"
        r"\bingress\b|api[_-]?gateway|app\.listen|public[_-]?read|"
        r"publicly[_-]?accessible|\bpublic[_-]?bucket\b)"),
}

# O que dizer quando NÃO se acha nada — a ausência precisa ser nomeável em
# linguagem de gente, senão ela não vira contradição na frente do dono.
PROCURADO = {
    "controle-de-acesso":
        "nenhuma biblioteca de login nem noção de papel/permissão no código",
    "dado-de-pessoa":
        "nenhum campo com cara de dado de pessoa (documento, telefone, "
        "endereço, senha) e nenhuma menção a lei de privacidade",
    "quanto-pode-cair":
        "nenhum backup, nenhuma checagem de saúde e nenhuma réplica",
    "o-que-fica-exposto":
        "nenhuma porta publicada, nenhum servidor escutando e nenhuma regra "
        "de origem permitida",
}

Pilar = collections.namedtuple("Pilar", "id procura pergunta porque")

PILARES = [
    Pilar(
        "quem-acessa-o-que", "controle-de-acesso",
        "Quem pode fazer o quê aqui dentro — e o que impede alguém de fazer o "
        "que não é dele?",
        "Sem essa linha desenhada no começo, ela vira `if` espalhado por vinte "
        "arquivos, e nenhum deles é a resposta."),
    Pilar(
        "dado-de-pessoa", "dado-de-pessoa",
        "Que dado de pessoa este sistema guarda, e por quanto tempo ele fica?",
        "Dado de pessoa que ninguém decidiu guardar é o que aparece no "
        "vazamento — e apagar depois exige saber onde ele foi parar."),
    Pilar(
        "quanto-pode-cair", "quanto-pode-cair",
        "Quanto tempo isso pode ficar fora do ar sem virar problema, e quanto "
        "do que já foi salvo dá para perder?",
        "As duas respostas decidem backup e réplica. Sem elas, a escolha é "
        "feita por acidente, no dia em que o disco morre."),
    Pilar(
        "o-que-fica-exposto", "o-que-fica-exposto",
        "O que deste sistema está aberto para qualquer um na internet — e o "
        "que só deveria abrir de dentro?",
        "Toda porta aberta é uma que alguém vai bater. A que ninguém sabe que "
        "está aberta é a que ninguém está olhando."),
]


# ── a varredura ────────────────────────────────────────────────────────────

def _arquivos(raiz):
    """Os arquivos autorais de `raiz`, já podados e com teto."""
    n = 0
    for dirpath, dirnames, filenames in os.walk(raiz):
        # poda in-place (os.walk respeita a mutação de dirnames)
        dirnames[:] = [d for d in dirnames
                       if d not in IGNORE_DIRS and not d.startswith(".")]
        for nome in sorted(filenames):
            ext = os.path.splitext(nome)[1].lower()
            if ext not in EXTENSOES and nome not in NOMES:
                continue
            caminho = os.path.join(dirpath, nome)
            try:
                if os.path.getsize(caminho) > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield caminho
            n += 1
            if n >= MAX_ARQUIVOS:
                return


def _procurar(raiz, padroes):
    """A primeira ocorrência de cada padrão, com arquivo e trecho."""
    achados = {}
    for caminho in _arquivos(raiz):
        rel = os.path.relpath(caminho, raiz)
        try:
            with open(caminho, encoding="utf-8", errors="replace") as fh:
                conteudo = fh.read(MAX_BYTES)
        except OSError:
            continue
        # O caminho entra na busca: `db/migrations/` é pista tanto quanto o
        # `CREATE TABLE` que mora lá dentro.
        alvo = rel + "\n" + conteudo
        for nome, padrao in padroes.items():
            if nome in achados:
                continue
            m = padrao.search(alvo)
            if m:
                achados[nome] = {"arquivo": rel, "trecho": m.group(0)}
        if len(achados) == len(padroes):
            break
    return achados


def detectar(raiz):
    """Os sinais que o projeto acende, cada um com a PISTA que o levantou.

    Devolve `{nome_do_sinal: {"arquivo": rel, "trecho": termo}}`. Sinal que não
    acendeu simplesmente não está no dicionário — ausência aqui é ausência de
    pergunta, e é assim que o projeto seco recebe só as três incondicionais.
    """
    return _procurar(raiz, SINAIS)


def pilares_seguranca(raiz):
    """As quatro perguntas de segurança, cada uma com o dado que a confere.

    Sempre as quatro — o que o projeto decide é o DADO que vai junto, não se a
    pergunta é feita. Cada uma volta com `dado`, e `dado["sentido"]` é:

    - `"confirma"` — achou no projeto (`arquivo` + `trecho`) o que a resposta
      esperada afirmaria;
    - `"contradiz"` — não achou nada disso, e `dado["procurado"]` diz em
      linguagem de gente o que foi procurado e não existe.

    Ausência é o dado mais útil dos dois: é ela que transforma "claro que tem
    controle de acesso" em uma divergência visível na hora da entrevista.
    """
    achados = _procurar(raiz, SINAIS_SEGURANCA)
    saida = []
    for p in PILARES:
        achado = achados.get(p.procura)
        if achado:
            dado = {"sentido": "confirma", "arquivo": achado["arquivo"],
                    "trecho": achado["trecho"]}
        else:
            dado = {"sentido": "contradiz", "procurado": PROCURADO[p.procura]}
        saida.append({"id": p.id, "pergunta": p.pergunta, "porque": p.porque,
                      "dado": dado})
    return saida


def perguntas(sinais):
    """As decisões a perguntar: as incondicionais + as que o projeto acendeu."""
    acesos = set(sinais or ())
    return [d for d in CATALOGO if d.gatilho is None or d.gatilho in acesos]


# ── linha de comando ───────────────────────────────────────────────────────

_USO = "uso: decisoes_estruturais.py [RAIZ] [--json]\n"


def _main(argv):
    raiz, como_json = ".", False
    for a in argv:
        if a == "--json":
            como_json = True
        elif a.startswith("-"):
            sys.stderr.write(_USO)
            return 2
        else:
            raiz = a
    if not os.path.isdir(raiz):
        sys.stderr.write("raiz inexistente: %s\n" % raiz)
        return 2
    sinais = detectar(raiz)
    lista = perguntas(sinais)
    seguranca = pilares_seguranca(raiz)
    if como_json:
        print(json.dumps({
            "sinais": sinais,
            "perguntas": [{"id": d.id, "gatilho": d.gatilho,
                           "pergunta": d.pergunta, "porque": d.porque,
                           "pista": sinais.get(d.gatilho) if d.gatilho else None}
                          for d in lista],
            "seguranca": seguranca,
        }, ensure_ascii=False, indent=2))
        return 0
    print("sinais: %s" % (", ".join(sorted(sinais)) or "nenhum"))
    print("perguntas: %d de %d" % (len(lista), len(CATALOGO)))
    for d in lista:
        pista = sinais.get(d.gatilho) if d.gatilho else None
        print("- %s" % d.pergunta)
        if pista:
            print("  pista: %s (%s)" % (pista["arquivo"], pista["trecho"]))
    print()
    print("seguranca: as %d, sempre — cada uma com o dado que a confere"
          % len(seguranca))
    for p in seguranca:
        dado = p["dado"]
        print("- %s" % p["pergunta"])
        if dado["sentido"] == "confirma":
            print("  o projeto confirma: %s (%s)"
                  % (dado["arquivo"], dado["trecho"]))
        else:
            print("  o projeto contradiz: %s" % dado["procurado"])
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
