#!/usr/bin/env python3
"""A concepção do /start tem que fechar por ACORDO, não por fim de roteiro.

Os três defeitos que esta suíte impede:

  1. a entrevista terminava sem aprovação nenhuma registrada — o "de acordo" só
     existia na memória da conversa, e conversa não sobrevive ao /clear;
  2. arquitetura, interface e jornadas não eram etapa: viravam parágrafo solto
     dentro de outro documento, sem documento próprio nem aprovação própria;
  3. a sabatina (grill-me, com ou sem o argumento com-docs) escorregava para juíza da
     constituição — ela é COMO se chega nela, nunca quem a julga.

Os nomes de arquivo das etapas são contrato: quem cobra lacuna lê daqui.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

# O bash que RESPONDE, não o do PATH: no Windows o do PATH é o do WSL, que sem
# distro fala UTF-16 e chega como stdout vazio — a suíte reprovaria o comando
# certo por causa do interpretador. Módulo compartilhado (_shared/bash_posix.py).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bash_posix import bash_posix  # noqa: E402

BASH = bash_posix() or "bash"


AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(AQUI, "..")
SKILLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                      "project-skills", "skills")
RAIZ_PLUGINS = os.path.join(PLUGIN, "..")

KIT = os.path.join(SKILLS, "start", "references", "authorial-kit.md")
SKILL = os.path.join(SKILLS, "start", "SKILL.md")
SKILL_DOC = os.path.join(SKILLS, "doc", "SKILL.md")
DESIGN = os.path.join(PLUGIN, "skills", "design-md", "SKILL.md")
GRILL_ME = os.path.join(RAIZ_PLUGINS, "grill-me", "skills", "grill-me", "SKILL.md")
VISUAL_PAGE = os.path.join(RAIZ_PLUGINS, "visual", "lib", "visual_page.py")
TEMPLATE = os.path.join(RAIZ_PLUGINS, "visual", "skills", "visual", "template.html")
DIAGRAMA = os.path.join(SKILLS, "start", "diagrama-blueprint.sh")
ENTRADA_EXEMPLO = os.path.join(RAIZ_PLUGINS, "archify", "skills", "archify",
                               "examples", "incident-response.workflow.json")
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

# O desenho da bancada (F12.5): o primeiro passo é citado verbatim pela F-1, o
# segundo é órfão — nenhuma funcionalidade o atende.
BANCADA_BLUEPRINT = """---
authored-by: human
status: approved
approved: 2026-01-03
---

# Como o sistema funciona

## O ciclo, do começo ao fim
1. escreve → valida → publica  ← journeys.md:12
2. o catálogo devolve o plugin ao autor quando a validação falha  ← journeys.md:20

## O que este desenho NÃO mostra, de propósito
- a cobrança — não é deste sistema
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


def _tem_node():
    """O render do archify é Node — sem ele o caminho feliz não é checável."""
    return subprocess.run([BASH, "-c", "command -v node"],
                          capture_output=True, stdin=subprocess.DEVNULL, start_new_session=True).returncode == 0


def tabela_etapas(caminho):
    """Mapa `nº da etapa` → documentos dela, lido da tabela de etapas do arquivo.

    A tabela existe em dois lugares — o SKILL.md e o authorial-kit.md — e o que
    tem que bater entre as duas não é a prosa da coluna do nome, é o CONTRATO:
    que etapa existe, com que número, e qual documento é dela.
    """
    linhas = open(caminho, encoding="utf-8").read().splitlines()
    dentro = False
    mapa = {}
    for linha in linhas:
        crua = linha.strip()
        if not dentro:
            if crua.startswith("|") and "| Etapa |" in crua:
                dentro = True
            continue
        if not crua.startswith("|"):
            break
        celulas = [c.strip() for c in crua.strip("|").split("|")]
        chave = celulas[0].strip("* ")
        if not chave or set(chave) <= set("- :"):
            continue
        mapa[chave] = sorted(set(re.findall(r"[A-Za-z0-9_.-]+\.md", " ".join(celulas[1:]))))
    return mapa


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

    print("o achado da varredura entra como RASCUNHO, com fonte e tres saidas (F2.2)")
    # O texto de antes dispensava a pergunta ("não vira pergunta, vira pista
    # confirmada com o dono") — isto é absorver texto de terceiro no documento
    # canônico sem o de acordo do dono. Escopo: o bloco do passo 2 só.
    bloco = skill.split("### 2 · Minerar as pistas")[1].split("### 3 ·")[0]
    corrido = " ".join(bloco.split())
    check("o passo 2 nao dispensa a pergunta sobre o que ja esta escrito",
          "não vira pergunta" not in corrido
          and "vira pista confirmada com o dono" not in corrido)
    check("o achado entra como rascunho, nao como conteudo aceito",
          "rascunho" in corrido)
    for saida in ("confirma", "corrige", "não vale mais"):
        check("o passo 2 nomeia a saida '%s'" % saida, saida in corrido)
    check("o passo 2 exige a fonte do achado (arquivo:linha)",
          "`arquivo:linha`" in corrido)
    check("o passo 2 veta absorver texto de terceiro sem o de acordo do dono",
          "sem o de acordo do dono" in corrido)

    print("a tabela de etapas e a MESMA nos dois arquivos que a escrevem")
    etapas_skill = tabela_etapas(SKILL)
    etapas_kit = tabela_etapas(KIT)
    check("as duas tabelas foram encontradas e nao estao vazias",
          len(etapas_skill) >= 6 and len(etapas_kit) >= 6)
    # Contrato: etapa que existe num arquivo e não no outro, ou documento que
    # troca de etapa só de um lado, é divergência — e divergência aqui é a
    # skill conduzindo uma sequência e o material de referência descrevendo
    # outra.
    check("nenhuma etapa existe so de um lado (%s vs %s)"
          % (sorted(etapas_skill), sorted(etapas_kit)),
          set(etapas_skill) == set(etapas_kit))
    for num in sorted(set(etapas_skill) & set(etapas_kit)):
        check("a etapa %s aponta os mesmos documentos nos dois (%s vs %s)"
              % (num, etapas_skill[num], etapas_kit[num]),
              etapas_skill[num] == etapas_kit[num])
    check("a etapa 5 e o esquema, com documento proprio",
          etapas_kit.get("5") == ["blueprint.md"])
    check("a etapa 6 e a lista derivada, depois do esquema",
          etapas_kit.get("6") == ["features.md"])
    check("a revisao 5b reapresenta o MESMO documento da 5",
          etapas_kit.get("5b") == ["blueprint.md"])
    print("a lei que os motores leem nasce na etapa autoral (F16.2)")
    # Quatro leitores cobram `.claude/docs/constituicao.md` e nenhuma etapa a
    # produzia: a lei era exigida de um arquivo que o rito nunca escrevia.
    check("constituicao.md e documento da etapa 1 nas duas tabelas",
          "constituicao.md" in etapas_skill.get("1", [])
          and "constituicao.md" in etapas_kit.get("1", []))
    check("o kit traz o molde da lei, com roteiro proprio",
          "`constituicao.md` — A lei do projeto" in kit
          and "# A lei deste projeto" in kit
          and "## Artigo 1 ·" in kit)
    check("o molde fixa o caminho de saida da lei nos dois arquivos",
          ".claude/docs/constituicao.md" in kit
          and ".claude/docs/constituicao.md" in skill)
    check("a skill aceita `constituicao` como documento avulso",
          "`constituicao`" in skill)

    check("o kit traz o molde do decimo documento, com roteiro proprio",
          "`blueprint.md` — Esquema de funcionamento" in kit
          and "# Como o sistema funciona" in kit
          and "O que este desenho NÃO mostra" in kit)
    check("o esquema nao abre a etapa seguinte sem o de acordo gravado",
          "Etapa 5 sem `approved:` trava a etapa 6" in kit)
    check("archify ausente degrada em voz alta, sem travar a etapa",
          "`archify` ausente na máquina não bloqueia a etapa" in kit)

    print("a skill CONDUZ a etapa do esquema — nao so a lista na tabela (F12.2)")
    check("a skill se declara em seis etapas, e nao mais em cinco",
          "seis etapas de acordo" in skill and "## As seis etapas de acordo" in skill
          and "**seis acordos, nesta ordem**" in skill)
    check("blueprint.md entra na chamada da skill, com o desenho e o diagrama",
          "blueprint.md" in skill and "esquema de funcionamento" in skill)
    check("existe o modo `/start blueprint`",
          "`/start blueprint` — **só a etapa 5**" in skill)
    check("`blueprint` entra nos nomes de doc avulso aceitos",
          re.search(r"`journeys`, `blueprint`, `features`", skill) is not None)
    check("a trava da etapa 6 esta escrita, e diz o que conferir no disco",
          skill.count("A etapa 6 não abre sem `blueprint.md` aprovado") >= 2
          and "`.claude/docs/blueprint.md` existe e traz `status: approved`" in skill)
    check("a trava manda PARAR e conduzir a etapa 5, nao seguir",
          "pare e conduza a etapa 5" in skill)
    check("o passo 3 abre a etapa do esquema com o ciclo montado",
          "**A etapa 5 (esquema) você abre com o ciclo montado" in skill)
    check("a lista derivada passou a ser a etapa 6 no roteiro e na curadoria",
          "**A etapa 6 (funcionalidades) é a única em que você fala primeiro.**" in skill
          and "A curadoria da etapa 6" in skill
          and "A etapa 5 (funcionalidades)" not in skill)
    check("a revisao 5b esta declarada como reapresentacao, nao como setima etapa",
          "A 5b é a 5 reapresentada, não uma sétima etapa" in skill)
    print("a revisao 5b e CONDUZIDA, e a troca passa pelo historico (F12.3)")
    check("a 5b tem roteiro proprio, logo depois da lista gravada",
          "#### A revisão 5b — o esquema volta pra mesa assim que a lista fecha" in skill)
    check("a 5b roda sempre, e nao 'quando parece necessario'",
          "**Ela roda SEMPRE**" in skill
          and 'Rodar só "quando parece' in skill)
    check("nada mudou fecha a etapa sem tocar o arquivo",
          "a etapa fecha sem tocar o arquivo" in skill)
    check("mudou, a troca do texto aprovado passa pelo historico e nao por edicao direta",
          "a troca passa pelo histórico, nunca por edição direta no corpo" in skill
          and 'lib/historico.py)" reescrever .claude/docs/blueprint.md' in skill
          and "blueprint.historico.md" in skill)
    check("a skill sabe que o historico reabre a etapa e manda reaprovar",
          "reabriu_aprovacao" in skill
          and "doc-aprovar.sh" in skill.split("#### A revisão 5b")[1])
    check("o programa REALMENTE reabre a etapa quando o corpo aprovado muda",
          "def _reabrir_aprovacao(" in ler(HISTORICO)
          and '"reabriu_aprovacao": reabriu' in ler(HISTORICO))

    check("o protocolo de saida imprime a etapa nova, com o estado do diagrama",
          "Esquema → `blueprint.md`" in skill
          and "`archify` ausente, DEGRADADO" in skill
          and "revisão 5b" in skill)

    print("o diagrama da etapa 5 EXECUTA, e a ausencia degrada em voz alta (F12.4)")
    check("o mecanismo existe no disco, ao lado da skill",
          os.path.exists(DIAGRAMA))
    check("o kit manda rodar o mecanismo, e nao so descreve o diagrama",
          "diagrama-blueprint.sh" in kit and "DEGRADADO:" in kit)
    check("o archify e achado pelo NOME, nunca por caminho relativo",
          'resolve-plugin.sh" archify skills/archify/' in ler(DIAGRAMA))
    # Caminho 1 — archify presente: o HTML nasce em .claude/archify/ pela régua
    # de nome dele. Caminho 2 — archify ausente: sai a linha DEGRADADO e o
    # código 3, e a etapa segue.
    # O interpretador é o BASH que RESPONDE, nunca o `bash` do PATH: no Windows
    # o do PATH é o do WSL, e as quatro checagens abaixo reprovavam por causa
    # dele, não por causa do mecanismo.
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "proj")
        os.makedirs(proj)
        open(os.path.join(proj, "CLAUDE.md"), "w", encoding="utf-8").write("# marcador de projeto\n")
        vazio = os.path.join(tmp, "sem-plugins")
        os.makedirs(vazio)
        ausente = subprocess.run(
            [BASH, DIAGRAMA, proj, "workflow", ENTRADA_EXEMPLO, "organismo.html"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, CLAUDE_PLUGIN_ROOT=vazio, CLAUDE_CONFIG_DIR=vazio), stdin=subprocess.DEVNULL, start_new_session=True)
        check("sem archify: codigo 3 e a linha DEGRADADO, sem travar",
              ausente.returncode == 3 and "DEGRADADO:" in ausente.stdout)
        check("sem archify: nada foi escrito em .claude/archify/",
              not os.path.exists(os.path.join(proj, ".claude", "archify")))
        fora_da_regua = subprocess.run(
            [BASH, DIAGRAMA, proj, "workflow", ENTRADA_EXEMPLO, "blueprint.html"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN), stdin=subprocess.DEVNULL, start_new_session=True)
        check("nome fora da regua do archify e recusado",
              fora_da_regua.returncode == 2)
        if not (os.path.exists(ENTRADA_EXEMPLO) and _tem_node()):
            # O archify é plugin IRMÃO: só o repositório tem os dois lado a
            # lado, e o render dele é Node. Faltando um dos dois, o caminho
            # feliz não é checável aqui.
            print("  --   archify irmao ou node ausentes — 2 checagens puladas")
        else:
            presente = subprocess.run(
                [BASH, DIAGRAMA, proj, "workflow", ENTRADA_EXEMPLO, "organismo.html"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env=dict(os.environ, CLAUDE_PLUGIN_ROOT=PLUGIN), stdin=subprocess.DEVNULL, start_new_session=True)
            esperado = os.path.join(proj, ".claude", "archify", "organismo.html")
            check("com archify: o html nasce em .claude/archify/ pela regua de nome dele",
                  presente.returncode == 0 and os.path.exists(esperado))
            check("com archify: o caminho do html sai no stdout, pro relatorio citar",
                  presente.stdout.strip() == esperado)

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
    check("o kit aponta a sabatina, nas duas jornadas, como o caminho",
          "/grill-me" in kit and "/grill-me com-docs" in kit)
    check("a skill aponta a sabatina, nas duas jornadas, como o caminho",
          "/grill-me" in skill and "/grill-me com-docs" in skill)
    check("o kit nega o papel de juiz a sabatina",
          "A sabatina não é juíza" in kit)
    check("a skill nega o papel de juiz a sabatina",
          "A sabatina não julga o documento" in skill
          and "A sabatina não é juíza" in skill)
    check("a etapa seguinte nao comeca com a anterior aberta",
          "a etapa continua aberta e a próxima não começa" in skill)

    print("a etapa de interface reaproveita a skill design-md, sem duplicar")
    check("o design-md se declara a etapa de interface do /start",
          "etapa de interface do `/start`" in design)
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
            capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
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
            input=json.dumps(spec_vazio), capture_output=True, text=True, encoding="utf-8", errors="replace", start_new_session=True)
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
    with open(os.path.join(docs, "blueprint.md"), "w", encoding="utf-8") as fh:
        fh.write(BANCADA_BLUEPRINT)
    antes = _impressao(banca)
    proc = subprocess.run([sys.executable, RASTREIO, banca],
                          capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    check("a conferencia roda no projeto de bancada e devolve JSON",
          proc.returncode == 0 and proc.stdout.strip().startswith("{"))
    saida = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
    check("funcionalidade sem origem aparece na contagem",
          saida.get("funcionalidades_sem_origem") == ["F-2 · Mandar e-mail de boas-vindas"])
    check("jornada sem funcionalidade aparece na contagem",
          saida.get("jornadas_sem_funcionalidade") == ["Arquivar um plugin"])
    check("passo do desenho que ninguem atende sai nomeado na terceira lista",
          saida.get("passos_sem_funcionalidade")
          == ["o catálogo devolve o plugin ao autor quando a validação falha"])
    check("a funcionalidade com origem, a jornada realizada e o passo atendido NAO sao acusados",
          saida.get("contagem", {}).get("funcionalidades") == 2
          and saida.get("contagem", {}).get("jornadas") == 2
          and saida.get("contagem", {}).get("passos") == 2
          and saida.get("sem_dono") == 3)
    check("a conferencia nao alterou nada no projeto de bancada",
          _impressao(banca) == antes)

    print("o projeto sai da concepcao ligado: indice minimo e ponteiros na raiz")
    kit = ler(KIT)
    check("o molde do indice minimo e dos ponteiros mora no kit",
          "start-doc:index" in kit and "start-doc:index:end" in kit
          and "AGENTS.md" in kit and ".github/copilot-instructions.md" in kit)
    check("o molde so admite documento aprovado no indice",
          "Só entra documento com `status: approved`" in kit)
    check("o fecho manda escrever o indice minimo em vez de deixar o projeto sem indice",
          "índice mínimo" in skill and "ponteiros finos" in skill
          and "não crie o índice" not in skill)
    check("o fecho proibe o marker da doc minerada no indice provisorio",
          "start-doc:index" in skill and "project-doc:v2" in skill
          and "fora do padrão" in skill)
    if not os.path.exists(SKILL_DOC):
        print("  --   skill irma ausente (fora do repo) — 1 checagem pulada")
    else:
        check("o FULL substitui o bloco provisorio inteiro pelo indice dele",
              "start-doc:index:end" in ler(SKILL_DOC))

    # A prova mecânica: o índice derivado dos documentos APROVADOS da fixture não
    # deixa o projeto "fora do padrão", e o índice do FULL o substitui.
    sys.path.insert(0, AQUI)
    import pattern_check
    aprovados, rascunhos = [], []
    for nome in sorted(os.listdir(docs)):
        fm, _ = pattern_check._extract_frontmatter_and_body(
            open(os.path.join(docs, nome), encoding="utf-8").read())
        (aprovados if pattern_check._fm_field(fm, "status") == "approved"
         else rascunhos).append(nome)
    with open(os.path.join(docs, "design.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nauthored-by: human\nstatus: draft\n---\n\n# Design\n")
    rascunhos.append("design.md")
    linhas = ["- **[%s](.claude/docs/%s)** — %s → leia quando decidir sobre isso"
              % (n, n, n[:-3]) for n in aprovados]
    indice = ("# bancada\n\n<!-- start-doc:index -->\n"
              "## Documentation Index\n" + "\n".join(linhas) +
              "\n<!-- start-doc:index:end -->\n")
    with open(os.path.join(banca, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write(indice)
    for ponteiro in ("AGENTS.md", "GEMINI.md", ".cursorrules"):
        with open(os.path.join(banca, ponteiro), "w", encoding="utf-8") as fh:
            fh.write("Read `CLAUDE.md` at the project root for the project index.\n")
    check("o indice minimo lista todo documento aprovado da fixture",
          aprovados and all(("(.claude/docs/%s)" % n) in indice for n in aprovados))
    check("documento nao aprovado da fixture fica de fora do indice",
          rascunhos and not any(("(.claude/docs/%s)" % n) in indice for n in rascunhos))
    check("os ponteiros de agente apontam o indice da raiz",
          all("Read `CLAUDE.md`" in ler(os.path.join(banca, p))
              for p in ("AGENTS.md", "GEMINI.md", ".cursorrules")))
    antes_full = pattern_check.check_pattern(banca)
    check("o indice provisorio NAO e acusado de fora do padrao (gen)",
          not any(v.startswith("(e) gen desatualizado") for v in antes_full["violations"])
          and antes_full["gen_found"] is None)

    # O FULL roda: substitui o bloco provisório inteiro, carimba doc-sig e journal.
    os.makedirs(os.path.join(banca, ".claude", ".project-doc"))
    open(os.path.join(banca, ".claude", ".project-doc", "findings.jsonl"), "w", encoding="utf-8").close()
    for nome in sorted(os.listdir(docs)):
        alvo = os.path.join(docs, nome)
        corpo = open(alvo, encoding="utf-8").read()
        with open(alvo, "w", encoding="utf-8") as fh:
            fh.write(corpo.replace("---\n", "---\ndoc-sig: x\n", 1))
    with open(os.path.join(banca, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("# bancada\n\n<!-- project-doc:v2 gen=%s -->\n## Documentation Index\n"
                 "<!-- project-doc:v2:end -->\n" % pattern_check.CURRENT_GEN)
    depois = pattern_check.check_pattern(banca)
    check("o indice do FULL substitui o provisorio, sem sobra do bloco antigo",
          "start-doc:index" not in ler(os.path.join(banca, "CLAUDE.md")))
    check("depois do FULL o projeto esta no padrao",
          depois["in_pattern"] and depois["gen_found"] == pattern_check.CURRENT_GEN)

    print("a sabatina, uma so e nas duas jornadas, sabe que nao e juiza")
    if not os.path.exists(GRILL_ME):
        # Só o repositório tem os plugins irmãos lado a lado; o cache de um
        # plugin instalado tem apenas o project-doc. Contrato de irmão só é
        # checável onde os dois moram.
        print("  --   plugin irmao ausente (fora do repo) — 3 checagens puladas")
    else:
        texto = ler(GRILL_ME)
        check("grill-me: sabe que e chamada pelas cinco etapas do /start",
              "cinco etapas de acordo" in texto and "/start" in texto)
        check("grill-me: nega o papel de juiz e devolve a aprovacao ao dono",
              "Você não é juiz" in texto and "Quem aprova é o dono" in texto)
        check("grill-me: a jornada com documento entra por argumento",
              "`/grill-me com-docs`" in texto)

    print("o modo ex-post: inferir do construido, referendar pelo dono (F0-F2)")
    skill = ler(SKILL)
    kit = ler(KIT)
    # O modo existe, com gatilho e fronteira — sem isto a lacuna de projeto maduro
    # continua mandando o dono para uma entrevista do zero.
    check("o modo ex-post esta na lista de invocacoes",
          "`/start ex-post`" in skill)
    check("a secao do modo declara a fronteira com projeto nascendo",
          "O modo ex-post" in skill and "projeto nascendo" in skill)
    bloco_expost = skill.split("## O modo ex-post")[1].split("\n## ")[0]
    check("as seis etapas continuam cobertas no modo",
          "as seis etapas" in bloco_expost)
    # As tres camadas de evidencia, com rotulo e regua propria.
    check("as tres camadas tem rotulo escrito",
          all(r in bloco_expost for r in
              ("DITO POR VOC", "ESCRITO", "INFERIDO DO C")))
    check("artigo sem prova vira pergunta, nunca proposta",
          "Artigo sem prova" in bloco_expost)
    # A camada 1 sai por comando, nao por julgamento (R-4).
    check("o comando da fala do dono esta no roteiro",
          "Direcionamento do usu" in bloco_expost and "findings.jsonl" in bloco_expost)
    # A camada 3 parte da doc minerada (R-5).
    check("varrer a arvore inteira de codigo e proibido",
          "varrer a" in bloco_expost.lower() and "proibido" in bloco_expost.lower())
    check("o organismo entra pelo mecanismo de heranca existente",
          "organism.py inherited" in bloco_expost)
    # O referendo: tres saidas e a proibicao do autoral no rascunho (F2).
    check("as tres saidas do referendo estao escritas",
          "confirma" in bloco_expost and "corrige" in bloco_expost
          and "vale mais" in bloco_expost)
    check("o rascunho nunca nasce autoral nem aprovado",
          "NUNCA nasce com" in bloco_expost
          and "authored-by: human" in bloco_expost)
    check("a REGRA DURA reconcilia o modo como pergunta noutra forma",
          "o modo ex-post" in skill.split("A REGRA DURA")[1][:900])
    # O kit dedica a subsecao de inferencia a cada molde autoral (F1.3).
    check("o kit tem a subsecao ex-post nos 11 moldes",
          kit.count("### Ex-post") == 11)
    # Consertos da revisao assintotica de 2026-08-13 — cada um reprovava antes:
    check("a description do frontmatter carrega o gatilho do modo",
          "ex-post" in skill.split("---", 2)[1])
    check("a ordem inverte em projeto maduro: minera primeiro, ex-post depois",
          "a ordem INVERTE" in skill)
    check("o comando das atas nao usa glob (zsh aborta com glob sem match)",
          ".claude/ata/*.md" not in bloco_expost
          and ".claude/ata/" in bloco_expost)
    check("o Tier 5 do /doc oferece o ex-post para quem acabou de minerar",
          "`/start ex-post`" in ler(SKILL_DOC))

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
