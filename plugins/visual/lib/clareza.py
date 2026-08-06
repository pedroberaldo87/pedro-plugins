#!/usr/bin/env python3
"""O banco de lições de clareza — o que o juiz de clareza já reprovou, virando gate.

POR QUE ISTO EXISTE
-------------------
O autor da página não é juiz confiável da clareza da própria página. Medido em
2026-08-06, duas vezes seguidas na mesma sessão: a primeira versão pediu decisão
sobre quatro peças sem mostrar nenhuma delas ("você só me pediu pra decidir coisa
com base em bola de cristal"); a segunda, feita para consertar a primeira, empilhou
referência sobre referência ("uma coisa recursiva a outra, recursiva a outra").
Nas duas o autor tinha lido a página e concluído que estava clara.

O conserto tem duas metades, e **só as duas juntas funcionam**:

  1. um juiz externo (um agente barato que lê como uma criança de 5 anos e diz o
     que é para decidir) — mas juiz sozinho só reprova depois de escrito; e
  2. ESTE banco, que guarda a ESSÊNCIA de cada reprovação e a devolve ANTES da
     escrita seguinte, como regra e — quando dá — como termo que o build recusa.

Sem (2), todo veredito do juiz morre no chat e o mesmo erro volta na página
seguinte. Com (2), o erro vira lei da casa, no padrão que este repositório já
usa: regra em prosa não pega, regra em programa pega.

O banco mora em `~/.claude/visual-state/` e NÃO dentro do plugin — o diretório do
plugin é cache reescrito a cada bump de versão, e lição perdida no bump é o
mesmo que lição nenhuma.

USO
---
    clareza.py licoes                    # ANTES de escrever o spec — obrigatório
    clareza.py check --spec pagina.json  # o que o build chama sozinho
    clareza.py registrar --json v.json   # grava o veredito novo do juiz
"""
import argparse
import json
import os
import re
import sys

STATE_DIR = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR",
                                        os.path.expanduser("~/.claude")),
                         "visual-state")
BANCO = os.path.join(STATE_DIR, "licoes-clareza.json")

# Campos do spec que a régua de clareza NÃO alcança, e por quê:
#   evidencia.output → saída crua é literal por obrigação; "humanizar" prova é o
#                      defeito original com outra roupa
#   raw_html         → a válvula; quem a usa assume a responsabilidade
ISENTOS = {("evidencia", "output"), ("raw_html", "html")}

# As lições de fábrica saem das duas reprovações de 2026-08-06. Elas são a semente:
# `registrar` acrescenta as próximas sem tocar nestas.
SEMENTE = {
    "versao": 1,
    "licoes": [
        {
            "id": "referente-pendurado",
            "nome": "Peço decisão sobre coisa que a página não mostra",
            "erro": "Cito uma peça pelo nome como se o leitor já a conhecesse, porque EU a conheço.",
            "regra": "Toda peça citada aparece na própria página — o que ela é, em uma frase — ANTES da pergunta.",
            "teste": "Tape o resto da página. A escolha ainda se entende sozinha?",
            "banido": [],
            "de": "2026-08-06 · retorno do dono: 'você só me pediu pra decidir coisa com base em bola de cristal'"
        },
        {
            "id": "referencia-recursiva",
            "nome": "Explico uma coisa usando outra que também não expliquei",
            "erro": "A explicação de A depende de B, que depende de C, e nenhuma das três está na página.",
            "regra": "Cada explicação fecha em si mesma; nunca use um segundo conceito novo para explicar o primeiro.",
            "teste": "Conte quantos conceitos novos a frase exige. Mais de um, quebre.",
            "banido": [],
            "de": "2026-08-06 · retorno do dono: 'uma coisa recursiva a outra, recursiva a outra'"
        },
        {
            "id": "termo-vago-meu",
            "nome": "Uso um nome que eu inventei e nunca defini",
            "erro": "Batizo uma coisa com nome bonito e uso o nome como se ele explicasse a coisa.",
            "regra": "Nome que eu inventei se troca pelo que a coisa FAZ, em palavras comuns.",
            "teste": "O nome aparece em algum lugar fora desta conversa? Se não, descreva em vez de nomear.",
            "banido": ["impressão digital", "banco de perguntas", "mapa condensado",
                       "grafo condensado", "sistema pai", "espólio", "superfície-mãe",
                       "cobrador universal", "referente pendurado"],
            "de": "2026-08-06 · juiz de clareza: 'uma criança pensa em banco de dinheiro ou banco de sentar'"
        },
        {
            "id": "jargao-sem-glosa",
            "nome": "Solto um termo técnico sem dizer o que é ali mesmo",
            "erro": "Uso a palavra da área achando que ela é comum porque é comum PARA MIM.",
            "regra": "Termo técnico ganha meia linha de explicação na primeira vez, na mesma frase.",
            "teste": "A palavra se explica sem sair da página? Se não, glose ou troque.",
            "banido": ["herda", "herança", "instanciar", "vendorado", "idempotente",
                       "fail-open", "gate", "hook", "spec", "schema", "frontmatter"],
            "de": "2026-08-06 · juiz de clareza: 'a palavra herda é de programação e aparece sem explicação'"
        },
        {
            "id": "escolha-sem-diferenca",
            "nome": "As duas opções não dizem o que muda entre elas",
            "erro": "Descrevo cada opção por dentro, sem dizer o que o leitor ganha e perde escolhendo.",
            "regra": "Cada opção diz a consequência concreta de escolhê-la, em palavras de gente.",
            "teste": "Dá para dizer a diferença entre as duas numa frase? Se não, reescreva as duas.",
            "banido": [],
            "de": "2026-08-06 · retorno do dono: 'não consigo entender se é pra deixar o enxame grande ou pequeno'"
        }
    ]
}


def carrega():
    if os.path.exists(BANCO):
        try:
            with open(BANCO, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError):
            pass  # banco corrompido não pode derrubar o build — cai na semente
    return SEMENTE


def grava(banco):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(BANCO, "w", encoding="utf-8") as f:
        json.dump(banco, f, ensure_ascii=False, indent=2)


def textos_do_spec(spec):
    """Todo texto do spec que o leitor lê, com o caminho de onde ele veio.

    Anda no spec inteiro sem saber o formato de cada bloco de propósito: bloco novo
    passa a ser checado sozinho, sem ninguém lembrar de vir aqui acrescentá-lo.
    """
    achados = []

    def anda(no, caminho, kind=None):
        if isinstance(no, dict):
            k = no.get("kind", kind)
            for chave, val in no.items():
                if (k, chave) in ISENTOS:
                    continue
                anda(val, "%s.%s" % (caminho, chave) if caminho else chave, k)
        elif isinstance(no, list):
            for i, val in enumerate(no):
                anda(val, "%s[%d]" % (caminho, i), kind)
        elif isinstance(no, str) and no.strip():
            achados.append((caminho, no))

    anda(spec, "")
    return achados


def erros_de_clareza(spec, banco=None):
    """Os termos banidos que aparecem no spec, com a lição que os baniu."""
    banco = banco or carrega()
    errs = []
    for caminho, texto in textos_do_spec(spec):
        baixo = texto.lower()
        for licao in banco.get("licoes", []):
            for termo in licao.get("banido", []):
                if re.search(r"(?<!\w)%s(?!\w)" % re.escape(termo.lower()), baixo):
                    errs.append('%s: a palavra "%s" já reprovou antes — %s'
                                % (caminho, termo, licao["regra"]))
    return errs


def cmd_licoes(args):
    banco = carrega()
    licoes = banco.get("licoes", [])
    print("LIÇÕES DE CLAREZA — leia ANTES de escrever o spec (%d)" % len(licoes))
    print("=" * 72)
    for licao in licoes:
        print("\n▸ %s" % licao["nome"])
        print("  o erro:  %s" % licao["erro"])
        print("  a regra: %s" % licao["regra"])
        if licao.get("teste"):
            print("  o teste: %s" % licao["teste"])
        if licao.get("banido"):
            print("  o build RECUSA: %s" % " · ".join(licao["banido"]))
        print("  origem:  %s" % licao.get("de", "—"))
    print("\n" + "=" * 72)
    print("Termo banido no spec = build recusa. Os outros são julgamento seu.")
    return 0


def cmd_check(args):
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    errs = erros_de_clareza(spec)
    if not errs:
        print("✅ nenhum termo já reprovado no spec")
        return 0
    print("⛔ termos que já reprovaram antes:")
    for e in errs:
        print("  - %s" % e)
    return 2


def cmd_registrar(args):
    """Acrescenta lições novas. Lição com id repetido é ATUALIZADA, não duplicada."""
    with open(args.json, encoding="utf-8") as f:
        novas = json.load(f)
    if isinstance(novas, dict):
        novas = novas.get("licoes", [])
    banco = carrega()
    por_id = {x["id"]: x for x in banco.get("licoes", [])}
    for licao in novas:
        if not licao.get("id") or not licao.get("regra"):
            print("⛔ lição sem id ou sem regra, pulada: %r" % licao)
            continue
        antiga = por_id.get(licao["id"])
        if antiga:
            # termo banido só ENTRA, nunca sai — desbanir é decisão humana, à mão
            licao["banido"] = sorted(set(antiga.get("banido", [])) |
                                     set(licao.get("banido", [])))
        por_id[licao["id"]] = licao
    banco["licoes"] = list(por_id.values())
    grava(banco)
    print("✅ %d lições no banco · %s" % (len(banco["licoes"]), BANCO))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("licoes", help="imprime as lições — rode ANTES de escrever o spec")
    c = sub.add_parser("check", help="acusa termo já reprovado dentro de um spec")
    c.add_argument("--spec", required=True)
    r = sub.add_parser("registrar", help="grava lições novas vindas do juiz de clareza")
    r.add_argument("--json", required=True)
    args = p.parse_args(argv)
    if args.cmd == "licoes":
        return cmd_licoes(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "registrar":
        return cmd_registrar(args)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
