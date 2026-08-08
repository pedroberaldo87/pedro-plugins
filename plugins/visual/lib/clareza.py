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
    clareza.py licoes                     # ANTES de escrever o spec — obrigatório
    clareza.py check --spec pagina.json   # o que o build chama sozinho
    clareza.py revisar --spec pagina.json # ANTES do build — as 5 conferências mecânicas
    clareza.py registrar --json v.json    # grava o veredito novo do juiz

POR QUE O `revisar` EXISTE, SE JÁ HÁ AS LIÇÕES E O JUIZ
-------------------------------------------------------
Medido em 2026-08-08: uma página reprovou nas três decisões, e **duas das quatro
lições que a reprovaram já estavam no banco**. O autor tinha lido as 60 lições no
começo e errou assim mesmo. Ler 60 lições no início não é conferir 60 lições no
fim — entre escrever o spec e chamar o build não havia nenhuma conferência, só o
"releia como se nunca tivesse visto", que é o julgamento já sabidamente falho.

O `check` pega termo BANIDO (lista de palavras). O `revisar` pega o que não cabe
numa lista de palavras: a palavra da casa usada sem abrir, dois nomes para a
mesma coisa, apoio em escolha que não está na página, custo sem unidade, e prova
colada sem dizer o que ela estraga. Nada disso julga clareza — isso é do juiz.
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


# ── as 5 conferências mecânicas do `revisar` ────────────────────────────────
#
# FAMILIAS: cada grupo é um conjunto de palavras que a casa usa para a MESMA
# coisa. Duas do mesmo grupo na mesma página fazem o leitor procurar a diferença
# que não existe — foi o erro medido em 2026-08-08, onde "pacote", "skill" e
# "ferramenta" conviviam com sentidos que se cruzavam.
FAMILIAS = [
    ["plugin", "pacote", "caixinha"],
    ["skill", "ferramenta", "receita"],
    ["hook", "gancho", "guarda"],
    ["agente", "subagente"],
    ["motor", "workflow", "missão", "execução automática"],
    ["passo", "tarefa", "item do plano"],
]

# Apoio em coisa que o leitor não tem: a página se sustenta numa escolha ou numa
# leitura que aconteceu FORA dela. Vale para conversa anterior E para esta mesma
# conversa — o erro de 2026-08-08 citava escolha feita dez minutos antes.
APOIO_FORA = ["você já escolheu", "voce ja escolheu", "como vimos", "como combinamos",
              "como você sabe", "como voce sabe", "conforme decidido",
              "você já decidiu", "voce ja decidiu", "como falamos"]

# Custo sem unidade: dizer que algo é caro sem dizer caro em quê deixa o leitor
# inventar a resposta (dinheiro? tempo? espera?).
CUSTO = r"(?<!\w)(car[oa]s?|custa|custo|custam|barat[oa]s?|gast[ao]|gasta|gastam)(?!\w)"
UNIDADE = r"(?<!\w)(dinheiro|reais|R\$|minutos?|horas?|segundos?|dias?|tokens?|" \
          r"palavras?|milhõ|milha|%|por cento|espera|vezes)"


def _blocos(spec):
    """(indice_secao, indice_bloco, bloco) de todo bloco de toda seção."""
    for si, sec in enumerate(spec.get("sections") or []):
        for bi, bl in enumerate(sec.get("blocks") or []):
            if isinstance(bl, dict):
                yield si, bi, bl


def _texto_visivel(spec):
    """Só o texto que o leitor lê, sem a prova crua — a prova é literal por lei."""
    return [(c, t) for c, t in textos_do_spec(spec)]


def _abertura_frases(spec):
    """As frases dos blocos que vêm ANTES do primeiro bloco de decisão.

    É onde a definição das palavras tem que morar: definir depois da pergunta é
    definir para quem já se perdeu.
    """
    saida = []
    for _si, _bi, bl in _blocos(spec):
        if bl.get("kind") == "decision":
            break
        if bl.get("kind") in ("bullets", "text"):
            saida.extend(bl.get("items") or [])
            if bl.get("text"):
                saida.append(bl["text"])
    return saida


def _antes_da_primeira_pergunta(spec):
    return " ".join(_abertura_frases(spec)).lower()


def _cita(texto, palavra):
    return re.search(r"(?<!\w)%s(?!\w)" % re.escape(palavra), texto, re.I)


def revisao_do_spec(spec):
    """As 5 conferências. Devolve lista de (id_da_conferencia, mensagem)."""
    achados = []
    visivel = _texto_visivel(spec)
    tudo = " ".join(t for _c, t in visivel).lower()
    abertura = _antes_da_primeira_pergunta(spec)

    # 1 · palavra da casa usada sem ser aberta antes da primeira pergunta
    # 2 · duas palavras da MESMA família na mesma página
    #
    # A abertura é ISENTA da conferência 2: é exatamente ali que se diz "pacote é a
    # caixinha que se instala", e acusar o glossário de confundir mataria a única
    # forma certa de apresentar a palavra. O que se acusa é usar as duas DEPOIS.
    depois = " ".join(t for _c, t in visivel).lower()
    for frag in _abertura_frases(spec):
        depois = depois.replace(frag.lower(), " ")
    for fam in FAMILIAS:
        usadas = [p for p in fam if _cita(tudo, p)]
        if not usadas:
            continue
        fora = [p for p in fam if _cita(depois, p)]
        if len(fora) > 1:
            achados.append((
                "dois-nomes",
                'depois da abertura a página chama a mesma coisa de %s — escolha '
                'uma e varra as outras' % " e ".join('"%s"' % u for u in fora)))
        for p in usadas:
            if not _cita(abertura, p):
                achados.append((
                    "palavra-sem-abrir",
                    'a palavra "%s" é da casa e não aparece definida antes da '
                    'primeira pergunta' % p))

    # 3 · apoio em escolha que não está escrita na página
    for caminho, texto in visivel:
        baixo = texto.lower()
        for frase in APOIO_FORA:
            if frase in baixo:
                achados.append((
                    "apoio-fora",
                    '%s: "%s" apoia a página em algo que o leitor não tem — '
                    'escreva o valor da escolha na própria página' % (caminho, frase)))

    # 4 · a página fala de custo e em lugar NENHUM diz custa o quê
    #
    # A régua é por PÁGINA, não por frase: depois de dizer uma vez que o custo é
    # dinheiro, repetir "a leitura cara" é economia de palavra, não omissão. Por
    # frase isto virava sete avisos numa página que já explicava o custo na
    # abertura — e falso-positivo ensina a ignorar o cobrador.
    if re.search(CUSTO, tudo, re.I) and not re.search(UNIDADE, tudo, re.I):
        primeira = next((("%s: \"%s\"" % (c, t.strip()[:70]))
                         for c, t in visivel if re.search(CUSTO, t, re.I)), "")
        achados.append((
            "custo-sem-unidade",
            'a página fala de custo e nunca diz custa O QUE — dinheiro, tempo ou '
            'espera. Primeira menção: %s' % primeira))

    # 5 · prova colada sem dizer o que ela estraga
    #
    # O estrago pode abrir a seção SEGUINTE — prova no fim de um capítulo e a
    # conclusão no começo do próximo é escrita normal, não omissão. Por isso a
    # busca atravessa a fronteira de seção em vez de parar nela.
    todos = [b for _si, _bi, b in _blocos(spec)]
    for pos, bl in enumerate(todos):
        if bl.get("kind") != "evidencia":
            continue
        proximo = next((b for b in todos[pos + 1:]
                        if b.get("kind") in ("bullets", "text", "tri", "callout")), None)
        # Duas provas seguidas não se explicam entre si: o que vale é o primeiro
        # bloco de texto DEPOIS delas, e ele é o mesmo para as duas.
        if proximo is None:
            si = next(i for i, sec in enumerate(spec.get("sections") or [])
                      if bl in (sec.get("blocks") or []))
            bi = (spec["sections"][si]["blocks"]).index(bl)
            achados.append((
                "prova-sem-estrago",
                'seção %d bloco %d: a prova é colada e nada depois dela diz o que '
                'ela estraga' % (si + 1, bi + 1)))
    return achados


def cmd_revisar(args):
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    achados = revisao_do_spec(spec)
    if args.json:
        print(json.dumps([{"check": c, "msg": m} for c, m in achados],
                         ensure_ascii=False, indent=2))
        return 0
    if not achados:
        print("✅ as 5 conferências passaram — o spec pode ir para o build")
        return 0
    print("⚠️  %d ponto(s) a conferir ANTES do build:" % len(achados))
    for check, msg in achados:
        print("  [%s] %s" % (check, msg))
    print("\nNenhum destes é julgamento de clareza — são os cinco defeitos que já")
    print("reprovaram páginas antes. Conserte o spec, não a página.")
    return 1


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
    v = sub.add_parser("revisar", help="as 5 conferências mecânicas, ANTES do build")
    v.add_argument("--spec", required=True)
    v.add_argument("--json", action="store_true")
    r = sub.add_parser("registrar", help="grava lições novas vindas do juiz de clareza")
    r.add_argument("--json", required=True)
    args = p.parse_args(argv)
    if args.cmd == "licoes":
        return cmd_licoes(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "revisar":
        return cmd_revisar(args)
    if args.cmd == "registrar":
        return cmd_registrar(args)
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
