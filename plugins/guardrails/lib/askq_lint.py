#!/usr/bin/env python3
"""askq_lint.py — mede o que é MEDÍVEL numa pergunta com opções.

Lê no stdin o JSON que o Claude Code entrega ao hook de PreToolUse e imprime as
violações, uma por linha. Exit 1 quando há violação (veredito, não crash — quem
consome do shell precisa saber disso).

Stdlib-puro (regra do repo: o plugin é copiado pro cache sem passo de instalação,
não existe onde rodar pip install).

FAIL-OPEN é lei, e aqui isso significa: forma inesperada da entrada NÃO acusa
ninguém. Sem `questions`, com `questions` que não é lista, com item que não é
objeto — devolve zero violações. "Não sei" nunca vira "está errado".

O que este lint NÃO faz: julgar se a premissa está clara. Isso é julgamento, não
régua. Ele pega os três defeitos que dão pra medir e devolve a pergunta pro
modelo — o resto continua sendo trabalho de quem escreve.

Uso:
    python3 askq_lint.py < input.json
    python3 askq_lint.py --explica          # imprime as regras e sai
"""

import json
import re
import sys

# ── Calibragem ───────────────────────────────────────────────────────────────
# Números escolhidos pra forçar frase de verdade, não pra punir concisão.
# Se der falso-positivo demais na prática, é AQUI que se afrouxa — um lugar só.
MIN_DESC = 30   # chars na consequência de cada opção
MIN_Q = 80      # chars na pergunta, quando não há nenhum preview pra olhar

# Identificador de código na superfície que o humano lê. Cada padrão tem nome
# porque a mensagem de volta cita qual casou — acusação sem o trecho ensina a
# ignorar o gate.
CODE_TELLS = (
    ("nome_com_underscore", re.compile(r"[A-Za-z]+_[A-Za-z]")),
    ("chamada_de_funcao",   re.compile(r"\w+\(\s*\)")),
    ("nome_de_arquivo",     re.compile(
        r"\w+\.(?:py|sh|js|ts|tsx|jsx|json|md|html|css|yml|yaml|toml|mjs)\b")),
    # O lookahead exige LETRA no primeiro segmento. Sem ele, "30/07/2026" casa
    # como caminho e o gate barra toda pergunta que cita uma data — falso-positivo
    # que treinaria o usuário a desligar o gate no primeiro dia.
    ("caminho",             re.compile(r"/(?=[\w.-]*[A-Za-z])[\w.-]+/[\w.-]+")),
    ("backtick",            re.compile(r"`[^`]+`")),
)


# Maiúscula NO MEIO da palavra é o tell mais forte de identificador — e também a
# grafia normal de um monte de nome próprio que aparece em pergunta humana. Sem
# esta lista, "o commit já está no GitHub" é barrado (foi o que aconteceu na
# PRIMEIRA pergunta real, 2026-07-30). Comparação em minúsculas.
NOMES_PROPRIOS = frozenset("""
github gitlab bitbucket javascript typescript coffeescript postgresql mysql sqlite
mongodb graphql oauth openai chatgpt deepseek anthropic claudecode nodejs npmjs
macos ios ipados iphone ipad ipod appstore youtube linkedin whatsapp powerpoint
onedrive dropbox icloud airdrop facetime vscode jetbrains pycharm webstorm intellij
datagrip xcode testflight cloudflare digitalocean namecheap godaddy
wordpress woocommerce shopify hubspot mailchimp
""".split())

# Palavra com maiúscula interna: "askqLint", "AskQ", "GitHub", "postState".
_MEIO_MAIUSCULO = re.compile(r"\b[A-Za-z]*[a-z][A-Z][A-Za-z]*\b")


def _txt(v):
    """Devolve string limpa pra qualquer coisa que devia ser texto."""
    return v.strip() if isinstance(v, str) else ""


def camel_suspeitas(s):
    """Palavras com maiúscula interna que NÃO são nome próprio conhecido."""
    return [w for w in _MEIO_MAIUSCULO.findall(s)
            if w.lower() not in NOMES_PROPRIOS]


def code_tells(s):
    """Nomes dos padrões de código que casam em s (lista, possivelmente vazia)."""
    achados = [nome for nome, rx in CODE_TELLS if rx.search(s)]
    if camel_suspeitas(s):
        achados.append("maiuscula_no_meio")
    return achados


def lint(payload):
    """Devolve a lista de violações. Entrada estranha ⇒ lista vazia (fail-open)."""
    if not isinstance(payload, dict):
        return []
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return []
    questions = ti.get("questions")
    if not isinstance(questions, list):
        return []

    viol = []
    for qi, q in enumerate(questions, 1):
        if not isinstance(q, dict):
            continue
        onde = "pergunta %d" % qi
        pergunta = _txt(q.get("question"))
        header = _txt(q.get("header"))
        opts = q.get("options")
        # Sem lista de opções a forma não é a que este lint conhece — o schema da
        # ferramenta exige 2 a 4. Forma estranha ⇒ não acusa nada nesta pergunta.
        if not isinstance(opts, list) or not opts:
            continue

        # ── 1 · nome que só o modelo conhece, na superfície visível ──────────
        for campo, valor in (("question", pergunta), ("header", header)):
            tells = code_tells(valor)
            if tells:
                viol.append(
                    "%s · o %s traz nome de código (%s): %r\n"
                    "    → o usuário não estava no seu raciocínio quando você batizou isso. "
                    "Diga a COISA, não o identificador."
                    % (onde, campo, ", ".join(tells), valor[:120]))

        # ── 2 · opção sem a consequência de escolher ─────────────────────────
        for oi, o in enumerate(opts, 1):
            if not isinstance(o, dict):
                continue
            desc = _txt(o.get("description"))
            label = _txt(o.get("label")) or "opção %d" % oi
            if len(desc) < MIN_DESC:
                viol.append(
                    "%s · opção %r não diz o que ACONTECE se ele escolher "
                    "(description tem %d chars, mínimo %d)\n"
                    "    → rótulo não é consequência. Escreva o que essa escolha causa."
                    % (onde, label[:60], len(desc), MIN_DESC))

        # ── 3 · pergunta seca e nada pra olhar ──────────────────────────────
        # Pergunta curta é legítima QUANDO há artefato na tela (preview). As duas
        # faltando juntas é o caso que o usuário relatou: decidir no vácuo.
        tem_preview = any(
            isinstance(o, dict) and _txt(o.get("preview")) for o in opts)
        if len(pergunta) < MIN_Q and not tem_preview:
            viol.append(
                "%s · pergunta sem premissa e sem nada pra olhar "
                "(%d chars, mínimo %d, e nenhuma opção tem preview)\n"
                "    → falta o que provocou a pergunta e o que está em jogo. "
                "Ou escreva a premissa, ou anexe o conteúdo concreto em preview."
                % (onde, len(pergunta), MIN_Q))

    return viol


REGRAS = """askq_lint — as três réguas (o resto é julgamento, não régua):

  1. Nome de código em `question` ou `header`     → o humano não batizou isso junto
     (maiúscula no meio da palavra conta, MENOS os nomes próprios de NOMES_PROPRIOS —
      "GitHub", "JavaScript", "macOS" são grafia normal, não identificador)
  2. `description` de opção com menos de %d chars → rótulo não é consequência
  3. `question` com menos de %d chars E zero preview → decidir no vácuo

Fail-open: forma inesperada da entrada devolve ZERO violações.
""" % (MIN_DESC, MIN_Q)


def main(argv):
    if "--explica" in argv:
        sys.stdout.write(REGRAS)
        return 0
    try:
        payload = json.loads(sys.stdin.read())
    except ValueError:
        return 0          # JSON quebrado não é pergunta ruim — fail-open
    viol = lint(payload)
    for v in viol:
        sys.stdout.write(v + "\n")
    return 1 if viol else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
