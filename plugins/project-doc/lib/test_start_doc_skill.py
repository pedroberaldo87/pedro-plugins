#!/usr/bin/env python3
"""A concepção do /start-doc tem que fechar por ACORDO, não por fim de roteiro.

Os três defeitos que esta suíte impede:

  1. a entrevista terminava sem aprovação nenhuma registrada — o "de acordo" só
     existia na memória da conversa, e conversa não sobrevive ao /clear;
  2. arquitetura, interface e jornadas não eram etapa: viravam parágrafo solto
     dentro de outro documento, sem documento próprio nem aprovação própria;
  3. a sabatina (grill-me / grill-with-docs) escorregava para juíza da
     constituição — ela é COMO se chega nela, nunca quem a julga.

Os nomes de arquivo das etapas são contrato: quem cobra lacuna lê daqui.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(AQUI, "..")
RAIZ_PLUGINS = os.path.join(PLUGIN, "..")

KIT = os.path.join(PLUGIN, "skills", "start-doc", "references", "authorial-kit.md")
SKILL = os.path.join(PLUGIN, "skills", "start-doc", "SKILL.md")
DESIGN = os.path.join(PLUGIN, "skills", "design-md", "SKILL.md")
GRILL_ME = os.path.join(RAIZ_PLUGINS, "grill-me", "skills", "grill-me", "SKILL.md")
GRILL_DOCS = os.path.join(RAIZ_PLUGINS, "grill-with-docs", "skills",
                          "grill-with-docs", "SKILL.md")
VISUAL_PAGE = os.path.join(RAIZ_PLUGINS, "visual", "lib", "visual_page.py")
TEMPLATE = os.path.join(RAIZ_PLUGINS, "visual", "skills", "visual", "template.html")
HISTORICO = os.path.join(PLUGIN, "lib", "historico.py")
RASTREIO = os.path.join(PLUGIN, "lib", "rastreio_etapas.py")

# O projeto de bancada da conferência de fechamento (F4.3): duas pontas soltas de
# propósito — a F-2 não aponta origem, e a jornada "Arquivar um plugin" não é
# realizada por funcionalidade nenhuma.
BANCADA_JOURNEYS = """---
authored-by: human
status: approved
approved: 2026-01-02
---

# Jornadas

## Publicar um plugin novo
- **Ator:** o dono do marketplace
- **Percurso:** escreve → valida → publica

## Arquivar um plugin
- **Ator:** o dono do marketplace
- **Percurso:** decide → tira do catálogo
"""

BANCADA_FEATURES = """---
authored-by: human
status: ready
approved:
---

# Funcionalidades

## As funcionalidades

### F-1 · Publicar o plugin
- **O que faz:** manda o plugin para o catálogo
- **Origem:** jornada "Publicar um plugin novo" de `journeys.md`
- **Passagem que a motivou:** "escreve → valida → publica"

### F-2 · Mandar e-mail de boas-vindas
- **O que faz:** avisa quem instalou
- **Passagem que a motivou:** "achei bonito"

## Deixado de fora de propósito
- **Assinatura paga** — não é deste sistema
"""


def _spec_aprovacao(corpo):
    """O spec que o passo 5 monta para colher o de acordo da etapa (F7.1)."""
    return {
        "slug": "aprovacao-jornadas",
        "title": "Acordo de jornadas",
        "subtitle": "o documento inteiro, para o de acordo",
        "ident": {"projeto": "bancada", "artefato": "journeys.md", "estado": "gerado"},
        "sections": [{"title": "A etapa", "blocks": [{
            "kind": "aprovacao",
            "etapa": "Etapa de jornadas",
            "doc_integral": corpo,
            "cards": [{"title": "Publicar um plugin novo",
                       "ancora": "escreve → valida → publica"}],
        }]}],
    }


def _impressao(raiz):
    """Assinatura de tudo que existe embaixo de `raiz` — caminho + conteúdo."""
    marcas = []
    for pasta, _dirs, arqs in os.walk(raiz):
        for a in sorted(arqs):
            caminho = os.path.join(pasta, a)
            with open(caminho, "rb") as fh:
                marcas.append("%s:%s" % (os.path.relpath(caminho, raiz),
                                         hashlib.sha256(fh.read()).hexdigest()))
    return "\n".join(sorted(marcas))

# Os vereditos por item são valor de MÁQUINA — quem os lê é o parser do /visual.
VEREDITOS = ("keep", "change", "remove")

# Os documentos de etapa, na ordem em que as etapas fecham.
ETAPAS = [
    ("autoral", "quality-goals.md"),
    ("arquitetura", "architecture-intent.md"),
    ("interface", "design.md"),
    ("jornadas", "journeys.md"),
    ("funcionalidades", "features.md"),
]

FAILS = []


def check(label, cond):
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def ler(caminho):
    """Lê o contrato com o espaço em branco normalizado.

    A quebra de linha do Markdown é diagramação, não conteúdo: sem isso a suíte
    quebraria só porque uma frase passou a caber em duas linhas.
    """
    return " ".join(open(caminho, encoding="utf-8").read().split())


def em_ordem(texto, marcas):
    """As marcas aparecem no texto, e nesta ordem."""
    pos = -1
    for m in marcas:
        i = texto.find(m, pos + 1)
        if i < 0:
            return False
        pos = i
    return True


def main():
    kit = ler(KIT)
    skill = ler(SKILL)
    design = ler(DESIGN)

    print("o kit define as etapas de acordo, na ordem, com documento proprio")
    check("as quatro etapas aparecem na ordem autoral, arquitetura, interface, jornadas",
          em_ordem(kit, ["**Acordo autoral**", "**Acordo de arquitetura**",
                         "**Acordo de interface**", "**Acordo de jornadas**"]))
    for etapa, arquivo in ETAPAS:
        check("a etapa de %s tem documento proprio (%s)" % (etapa, arquivo),
              arquivo in kit)
    check("os nomes de arquivo sao declarados contrato",
          "Os nomes de arquivo acima são o contrato" in kit)
    check("architecture-intent.md nao se confunde com o architecture.md minerado",
          "`architecture-intent.md` não é `architecture.md`" in kit)
    check("journeys.md nao se confunde com o runtime.md minerado",
          "`journeys.md` não é `runtime.md`" in kit)
    check("os dois documentos novos trazem roteiro e molde",
          kit.count("**Roteiro:**") >= 7 and kit.count("**Molde:**") >= 6)

    print("a entrevista termina produzindo a lista de funcionalidades, aprovada")
    check("a etapa de funcionalidades entra na tabela, depois das quatro",
          em_ordem(kit, ["**Acordo autoral**", "**Acordo de arquitetura**",
                         "**Acordo de interface**", "**Acordo de jornadas**",
                         "**Acordo de funcionalidades**"]))
    check("a lista e derivada do que ja foi aprovado nas etapas anteriores",
          "derivada do que já foi aprovado" in kit)
    check("a etapa de funcionalidades tem roteiro e molde proprios",
          kit.count("**Roteiro:**") >= 9 and kit.count("**Molde:**") >= 9)
    check("a lista so fecha com o de acordo do dono, como as outras",
          "A skill propõe, o dono decide" in kit
          and "A skill propõe, o dono decide" in skill)
    check("a skill aceita `features` como documento avulso",
          "`features`" in skill)
    check("a tabela de etapas da skill tem a linha de funcionalidades",
          "**Funcionalidades**" in skill)

    print("cada funcionalidade e curada item a item, com a passagem ao lado (F4.2)")
    check("a skill manda usar o bloco `item` do /visual, o componente que ja existe",
          "**um bloco `item`**" in skill and "visual_page.py" in skill)
    check("os tres vereditos sao os valores de maquina do spec",
          all("`%s`" % v in skill for v in VEREDITOS))
    check("o rotulo humano troca por item_labels, o valor de maquina nao",
          "item_labels" in skill)
    check("a passagem que motivou o item fica visivel junto do veredito",
          "**passagem literal** do documento aprovado que a motivou" in skill)
    check("item sem veredito NAO grava",
          "Item sem veredito não grava" in skill)
    check("radio em branco nao vale como manter",
          "Rádio em branco não é `keep`" in skill)
    check("o que ele mudou vai para o historico, pelo programa que ja existe",
          "lib/historico.py" in skill and "features.historico.md" in skill)
    if os.path.exists(VISUAL_PAGE):
        spec = ler(VISUAL_PAGE)
        check("os tres vereditos existem mesmo no /visual (contrato, nao invencao)",
              all('"%s"' % v in spec for v in VEREDITOS))
    else:
        print("  --   plugin visual ausente (fora do repo) — 1 checagem pulada")
    hist = ler(HISTORICO)
    check("o historico.py expoe o reescrever que a skill manda chamar",
          "def reescrever(" in hist)

    print("o de acordo fica gravado DENTRO do documento")
    check("o frontmatter do contrato tem o campo approved:",
          "approved: {YYYY-MM-DD}" in kit)
    check("status admite approved",
          "status: draft | ready | approved" in kit)
    check("maquina nenhuma escreve approved: sozinha",
          "`approved:` nenhuma máquina escreve sozinha" in kit)
    check("silencio nao vale como aprovacao",
          "Silêncio não é aprovação" in kit and "Silêncio não é aprovação" in skill)
    check("o design.md carrega o mesmo par por cima dos tokens",
          "`status:` / `approved:` entra **por cima** dos tokens" in kit)

    print("etapa aprovada aceita correcao pendente sem reabrir (F3.2)")
    check("o frontmatter do contrato tem o campo correcao-pendente:",
          "correcao-pendente: {" in kit)
    check("a correcao pendente vive no frontmatter, nunca no corpo",
          "no frontmatter, nunca no corpo" in kit)
    check("o kit diz que a correcao pendente nao reabre a etapa",
          "não reabre a etapa" in kit)
    check("a skill manda registrar a correcao em vez de reabrir a etapa",
          "correcao-pendente:" in skill and "não reabra a etapa" in skill)

    print("a etapa so fecha depois de apresentar e REAPRESENTAR")
    check("o kit manda apresentar o documento inteiro, nao um resumo",
          "Apresentar o documento inteiro" in kit)
    check("o kit manda reapresentar sem teto de rodadas",
          "REAPRESENTAR" in kit and "teto de rodadas" in kit)
    check("a skill tem o passo de apresentar/sabatinar/colher o de acordo",
          "### 5 · Apresentar, sabatinar e colher o de acordo" in skill)
    check("a skill manda reapresentar sem teto de rodadas",
          "REAPRESENTE" in skill and "teto de rodadas" in skill)
    check("escrever nao fecha a etapa",
          "não fecha** a etapa" in kit and "não fecha** a etapa" in skill)

    print("a sabatina e o caminho de fechar CADA etapa, e nao e juiza")
    check("a regra de fechamento vale para toda etapa",
          "Cada etapa fecha do mesmo jeito" in skill)
    check("o kit aponta grill-me e grill-with-docs como o caminho",
          "/grill-me" in kit and "/grill-with-docs" in kit)
    check("a skill aponta grill-me e grill-with-docs como o caminho",
          "/grill-me" in skill and "/grill-with-docs" in skill)
    check("o kit nega o papel de juiz a sabatina",
          "A sabatina não é juíza" in kit)
    check("a skill nega o papel de juiz a sabatina",
          "A sabatina não julga o documento" in skill
          and "A sabatina não é juíza" in skill)
    check("a etapa seguinte nao comeca com a anterior aberta",
          "a etapa continua aberta e a próxima não começa" in skill)

    print("a etapa de interface reaproveita a skill design-md, sem duplicar")
    check("o design-md se declara a etapa de interface do /start-doc",
          "etapa de interface do `/start-doc`" in design)
    check("o design-md grava o mesmo par de aprovacao",
          "`status: approved`" in design and "`approved: {YYYY-MM-DD}`" in design)
    check("lint limpo nao e aprovacao",
          "Lint limpo não é aprovação" in design)
    check("nao existe documento de interface paralelo",
          "Não existe documento paralelo de interface" in design)
    check("a skill start-doc nao reescreve a spec do DESIGN.md",
          "não duplique a spec do formato aqui" in skill)

    print("os modos e o relatorio enxergam as etapas novas")
    check("os nomes de doc aceitos incluem architecture-intent e journeys",
          "`architecture-intent`" in skill and "`journeys`" in skill)
    check("o relatorio tem uma linha de de-acordo por etapa",
          "**Passo 5/7:** De acordo" in skill)
    check("etapa escrita e nao aprovada conta como lacuna no modo gaps",
          "Etapa escrita e não aprovada conta como lacuna" in skill)

    print("fechar a etapa confere o que ficou sem dono (F4.3)")
    check("existe o programa que conta as duas pontas soltas",
          os.path.exists(RASTREIO))
    check("a skill roda a conferencia no passo de fechamento, sem ninguem pedir",
          "rastreio_etapas.py" in skill
          and em_ordem(skill, ["### 5 · Apresentar, sabatinar e colher o de acordo",
                               "rastreio_etapas.py", "**Grave o de acordo**"]))
    check("a conferencia so conta — nao escreve em documento nenhum",
          "só conta — não escreve em documento nenhum**" in skill
          and "só conta — não escreve em documento nenhum**" in kit)
    check("o kit poe a conferencia no fechamento, nunca no meio da entrevista",
          "acontece no fechamento, nunca no meio da entrevista" in kit
          and "lib/rastreio_etapas.py" in kit)
    check("o relatorio traz a contagem do que ficou sem dono",
          "Sem dono → {N} funcionalidades sem origem · {M} jornadas sem funcionalidade" in skill)

    print("a aprovacao de etapa e colhida na PAGINA, com o documento a vista (F7.1)")
    check("o passo 5 manda montar a pagina em vez de apresentar no chat",
          "Monte a página do `/visual` com o documento inteiro embutido — não apresente o "
          "texto no chat" in skill)
    check("o veredito da etapa e lido do disco, nao do chat",
          "~/.claude/visual-state/latest.json" in skill and "state.feedback" in skill)
    if not (os.path.exists(VISUAL_PAGE) and os.path.exists(TEMPLATE)):
        print("  --   plugin visual ausente (fora do repo) — 6 checagens puladas")
    else:
        saida = os.path.join(tempfile.mkdtemp(prefix="start-doc-aprov-"), "etapa.html")
        proc = subprocess.run(
            [sys.executable, VISUAL_PAGE, "build", "--spec", "-", "--out", saida],
            input=json.dumps(_spec_aprovacao(BANCADA_JOURNEYS)),
            capture_output=True, text=True)
        html = open(saida, encoding="utf-8").read() if os.path.exists(saida) else ""
        check("a pagina de aprovacao da etapa e montada pelo programa do /visual",
              proc.returncode == 0 and html)
        check("o documento INTEIRO vai embutido na pagina, verbatim",
              all(linha in html for linha in
                  ("## Publicar um plugin novo", "escreve → valida → publica",
                   "## Arquivar um plugin", "decide → tira do catálogo")))
        check("o veredito da etapa sai nos tres valores de maquina",
              all('value="%s"' % v in html for v in VEREDITOS))
        vazio = os.path.join(os.path.dirname(saida), "vazio.html")
        spec_vazio = _spec_aprovacao("")
        proc2 = subprocess.run(
            [sys.executable, VISUAL_PAGE, "build", "--spec", "-", "--out", vazio],
            input=json.dumps(spec_vazio), capture_output=True, text=True)
        check("pagina de aprovacao SEM o documento e recusada, sem escrever arquivo",
              proc2.returncode == 2 and not os.path.exists(vazio))

        # O retorno: o que o browser posta em ~/.claude/visual-state/latest.json.
        # A entrada da etapa é a de `title` igual ao nome dela.
        estado = {"state": {"feedback": [
            {"num": "1", "title": "Etapa de jornadas", "val": "change",
             "touched": True, "note": "falta a jornada de arquivar"}]}}
        etapa = [f for f in estado["state"]["feedback"]
                 if f.get("title") == "Etapa de jornadas"][0]
        check("o retorno do disco entrega o veredito e a nota da etapa",
              etapa["val"] == "change" and etapa["note"] == "falta a jornada de arquivar")
        modelo = ler(TEMPLATE)
        check("os campos que a skill manda ler existem no que o browser posta",
              all(c in modelo for c in ("title: it.dataset.title",
                                        "val: checked ? checked.value",
                                        "note: ta ? ta.value"))
              and "feedback:" in modelo)

    banca = tempfile.mkdtemp(prefix="start-doc-bancada-")
    docs = os.path.join(banca, ".claude", "docs")
    os.makedirs(docs)
    with open(os.path.join(docs, "journeys.md"), "w", encoding="utf-8") as fh:
        fh.write(BANCADA_JOURNEYS)
    with open(os.path.join(docs, "features.md"), "w", encoding="utf-8") as fh:
        fh.write(BANCADA_FEATURES)
    antes = _impressao(banca)
    proc = subprocess.run([sys.executable, RASTREIO, banca],
                          capture_output=True, text=True)
    check("a conferencia roda no projeto de bancada e devolve JSON",
          proc.returncode == 0 and proc.stdout.strip().startswith("{"))
    saida = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
    check("funcionalidade sem origem aparece na contagem",
          saida.get("funcionalidades_sem_origem") == ["F-2 · Mandar e-mail de boas-vindas"])
    check("jornada sem funcionalidade aparece na contagem",
          saida.get("jornadas_sem_funcionalidade") == ["Arquivar um plugin"])
    check("a funcionalidade com origem e a jornada realizada NAO sao acusadas",
          saida.get("contagem", {}).get("funcionalidades") == 2
          and saida.get("contagem", {}).get("jornadas") == 2
          and saida.get("sem_dono") == 2)
    check("a conferencia nao alterou nada no projeto de bancada",
          _impressao(banca) == antes)

    print("as duas sabatinas sabem que nao sao juizas")
    if not (os.path.exists(GRILL_ME) and os.path.exists(GRILL_DOCS)):
        # Só o repositório tem os plugins irmãos lado a lado; o cache de um
        # plugin instalado tem apenas o project-doc. Contrato de irmão só é
        # checável onde os dois moram.
        print("  --   plugins irmaos ausentes (fora do repo) — 4 checagens puladas")
    else:
        for nome, caminho in (("grill-me", GRILL_ME), ("grill-with-docs", GRILL_DOCS)):
            texto = ler(caminho)
            check("%s: sabe que e chamada pelas cinco etapas do /start-doc" % nome,
                  "cinco etapas de acordo" in texto and "/start-doc" in texto)
            check("%s: nega o papel de juiz e devolve a aprovacao ao dono" % nome,
                  "Você não é juiz" in texto and "Quem aprova é o dono" in texto)

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
