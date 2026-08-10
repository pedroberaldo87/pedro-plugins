#!/usr/bin/env python3
"""O cobrador do gauntlet — stdlib, sem framework.

Existe por uma falha medida: uma sessão real lançou SETE construtores prometendo um
juiz em cada briefing, lançou ZERO juízes, e ninguém percebeu. O estado normal de um
sistema sem gatilho é "nenhum juiz existe", e isso é indistinguível de "tudo aprovado"
em qualquer foto que se tire.

Este programa inverte o default: sem julgamento válido no disco, o fecho é RECUSADO, e
a ausência passa a gritar em vez de parecer normal.

Três subcomandos:

    rito   <missao>   o rito está completo? sem alvo, sonda e eixos não se começa
    fecho  <missao>   o fecho pode acontecer? é o ÚNICO que apaga o sinal da missão
    mapa   <missao>   o estado legível — SAÍDA de programa, nunca redigida por agente

O `mapa` existe porque a outra metade da falha foi de memória: os vereditos REPROVADO
viviam na conversa, e a conversa foi atropelada por ~35 direcionamentos em duas horas.
O que está em disco sobrevive ao /clear; o que está na conversa, não.

    python3 fecho_check.py fecho .claude/gauntlet/2026-08-07-site
"""

import argparse
import hashlib
import json
import os
import re
import sys

# O rito da abertura, ENXUTO por decisão do dono (2026-08-09): a versão de 9 campos
# nasceu do ritual de uma sessão que falhou, e ele mandou reduzir ao essencial. O que
# saiu (`tipo`, `congelado`, `liberado`, `material`) continua ACEITO como campo
# opcional — só deixou de ser porta de entrada. A lei do projeto, quando existe, entra
# no campo opcional `lei`: orienta quem constrói, e o juiz reprova a violação.
CAMPOS_DO_RITO = (
    "objetivo",
    "alvos",
    "sonda",
    "eixos",
    "orcamento",
)
# A tríade de entrada: os três sem os quais o juiz não tem régua nem procedimento.
TRIADE = ("alvos", "sonda", "eixos")
# O que uma sonda precisa trazer para ser executável. `interagir` é opcional: peça
# parada (um relatório) não tem gesto, e exigir um faria o dono inventar.
# `registrar` e `alvo` são o que produz os dois lados da comparação: sem eles não há
# par, e sem par não há veredito. `preparar` tem que ser DECLARADO, mas pode ser vazio
# — peça que já é observável (um documento, um arquivo) não tem o que preparar, e
# exigir um comando aí faria o dono inventar um.
CAMPOS_DA_SONDA = ("registrar", "alvo")
CAMPOS_DECLARADOS_DA_SONDA = ("preparar", "registrar", "alvo")
# Os três desfechos. `marginal` é RELATO de ganho pequeno, nunca porta de saída: ele
# só fecha peça com o orçamento esgotado. Medido em 2026-08-09: duas peças fecharam na
# rodada 1 de 4 por "retorno decrescente" e a obra ficou feia com 45% do orçamento
# intacto — a fonte da skill manda o contrário ("if it doesn't look AAA, keep going").
STATUS = ("aprovado", "reprovado", "marginal")
# O cheiro de receita num NOME de eixo: medida concreta onde devia haver qualidade.
# Nasceu de uma missão real (2026-08-09): o eixo "moldura de 32px" virou moldura de
# 32px na obra. O número do alvo tem casa própria — o campo `numero`, como prova do
# nível — e nome com medida é o vetor da cópia, então o rito o recusa.
MEDIDA_NO_NOME = re.compile(r"\d+([.,]\d+)?\s*(%|(px|ms|fps|em|rem|vh|vw|s)\b)")


def _le(caminho):
    """Lê JSON e devolve (dado, erro). Arquivo ausente NÃO é exceção: é achado."""
    if not os.path.isfile(caminho):
        return None, "não existe: %s" % caminho
    try:
        with open(caminho, encoding="utf-8") as fh:
            return json.load(fh), None
    except (ValueError, OSError) as e:
        return None, "ilegível: %s (%s)" % (caminho, e)


def _linhas(caminho):
    """Lê um arquivo de uma-linha-por-registro. Ausente = vazio, não erro."""
    if not os.path.isfile(caminho):
        return []
    fora = []
    with open(caminho, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            try:
                fora.append(json.loads(linha))
            except ValueError:
                continue
    return fora


def _dentro_da_missao(missao, relativo):
    """O caminho relativo resolve para dentro do diretório da missão?"""
    base = os.path.normpath(missao)
    alvo = os.path.normpath(os.path.join(base, relativo))
    return alvo == base or alvo.startswith(base + os.sep)


def marca(caminho):
    """A marca de um arquivo: o conteúdo, não a data.

    A data de modificação é o mecanismo óbvio e o errado — ela não sobrevive a um
    clone, a uma cópia, nem a um `git checkout`, e um veredito legítimo passaria a
    ser recusado por causa de uma operação de git que ninguém associaria ao gauntlet.
    O conteúdo sobrevive a tudo isso e continua provando o que interessa: que a obra
    julgada é a obra que está no disco.
    """
    if not os.path.isfile(caminho):
        return None
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for pedaco in iter(lambda: fh.read(65536), b""):
            h.update(pedaco)
    return h.hexdigest()[:16]


def _leis_em_arquivo(rito, missao):
    """As entradas de `lei` que são ARQUIVO no disco: (entrada, caminho resolvido).

    A lei aceita dois formatos — o texto verbatim, que mora dentro do rito.json e a
    âncora da régua já congela, e o caminho de um documento de fora. O documento é o
    que a âncora do rito NÃO cobre, e é dele que esta lista cuida.
    """
    lei = rito.get("lei") or []
    if isinstance(lei, str):
        lei = [lei]
    raiz = rito.get("raiz") or missao
    if not os.path.isabs(raiz):
        raiz = os.path.join(missao, raiz)
    fora = []
    for entrada in lei:
        if not isinstance(entrada, str) or not entrada:
            continue
        cam = entrada if os.path.isabs(entrada) else os.path.join(raiz, entrada)
        if os.path.isfile(cam):
            fora.append((entrada, cam))
    return fora


def ancora_leis(missao):
    """Congela o conteúdo dos documentos de lei no momento da abertura.

    "Reconfira a lei no fecho" era instrução de prosa — a classe de furo que criou a
    skill. Com a âncora gravada aqui, quem reconfere é `erros_do_fecho`, nunca a
    memória de quem orquestra.
    """
    rito, erro = _le(os.path.join(missao, "rito.json"))
    if erro:
        return
    marcas = {entrada: marca(cam) for entrada, cam in _leis_em_arquivo(rito, missao)}
    with open(os.path.join(missao, "lei-aprovada.marca"), "w", encoding="utf-8") as fh:
        json.dump(marcas, fh, ensure_ascii=False, indent=1)


def _rodadas(dir_peca):
    """As rodadas de uma peça, em ordem. Nome `r<N>`; o resto é ignorado."""
    if not os.path.isdir(dir_peca):
        return []
    fora = []
    for nome in os.listdir(dir_peca):
        if not nome.startswith("r") or not nome[1:].isdigit():
            continue
        fora.append((int(nome[1:]), os.path.join(dir_peca, nome)))
    return [c for _, c in sorted(fora)]


def _ultima_rodada(dir_peca):
    r = _rodadas(dir_peca)
    return r[-1] if r else None


# ─────────────────────────────────────────────────────────────────────────────
# rito — o rito está completo?
# ─────────────────────────────────────────────────────────────────────────────


# ── APAGAR O SINAL É UMA RECEITA SÓ, E ELA LEVA O ESTADO INTEIRO ──────────────
# Duas coisas que faltavam, medidas em 2026-08-10 com a barra do dono na tela.
#
# (1) O apagamento levava só `ativo-` e `bloqueios-`; `onda-`, `placar-`, `sinal-`,
#     `trabalho-`, `doc-` e `motorid-` ficavam para trás, e a onda velha de uma
#     missão morta reaparecia na barra de quem reusasse o mesmo id de sessão. É a
#     mesma lista que `project-skills/lib/andamento.py:encerra` usa — as duas casas
#     escrevem o mesmo estado, então apagam o mesmo conjunto.
#
# (2) Só o fecho VERDE apagava. Disputa parada pelo dono, abandonada, ou cujo fecho
#     foi recusado por furo ficava com o sinal aceso até a expiração — e a barra
#     anunciando "Missão há 10h25" de uma disputa que ninguém ia retomar. Por isso
#     nasce o subcomando `encerra`: ele NÃO julga nada, só apaga. Encerrar não é
#     aprovar, e confundir os dois foi o que deixou o sinal preso ao caminho feliz.
_PREFIXOS_DO_ESTADO = ("ativo-", "bloqueios-", "onda-", "placar-", "doc-",
                       "sinal-", "trabalho-", "motorid-")


def apaga_sinal(sinal):
    """Apaga o sinal e todo o estado da mesma sessão. Devolve o que sumiu."""
    pasta, nome = os.path.dirname(sinal), os.path.basename(sinal)
    sessao = nome[len("ativo-"):] if nome.startswith("ativo-") else nome
    sumiram = []
    for prefixo in _PREFIXOS_DO_ESTADO:
        try:
            os.remove(os.path.join(pasta, prefixo + sessao))
            sumiram.append(prefixo.rstrip("-"))
        except OSError:
            pass
    print("sinal apagado: %s (%s)" % (sinal, ", ".join(sumiram) or "nada aceso"))
    return sumiram


def erros_do_rito(missao, sinal=None):
    """Devolve a lista de furos do rito. Lista vazia = a missão pode começar.

    `sinal` é o caminho do arquivo que marca uma missão de pé. A versão enxuta cortou
    a reserva de arquivos entre motores apoiada em "duas missões não convivem" — e
    essa recusa não existia em lugar nenhum até esta linha.
    """
    erros = []
    if sinal and os.path.exists(sinal):
        erros.append(
            "já há uma missão de pé nesta sessão — termine ou encerre antes de abrir outra"
        )
    rito, erro = _le(os.path.join(missao, "rito.json"))
    if erro:
        return ["o rito não está no disco — %s" % erro]

    for campo in CAMPOS_DO_RITO:
        valor = rito.get(campo)
        if valor is None or valor == "" or valor == [] or valor == {}:
            erros.append("o rito não declara `%s`" % campo)

    # A tríade tem cobrança própria: sem ela o juiz não tem contra o que medir nem
    # como observar, e o laço inteiro vira revisão de conformidade.
    for campo in TRIADE:
        if not rito.get(campo):
            erros.append(
                "sem `%s` não há gauntlet: o juiz fica sem régua ou sem procedimento" % campo
            )

    sonda = rito.get("sonda") or {}
    if isinstance(sonda, dict):
        for campo in CAMPOS_DECLARADOS_DA_SONDA:
            if campo not in sonda:
                erros.append("a sonda não declara `%s`" % campo)
        for campo in CAMPOS_DA_SONDA:
            if campo in sonda and not sonda.get(campo):
                erros.append("a sonda declara `%s` vazio, e sem ele não há par" % campo)
        # A sonda tem que ter RODADO uma vez, e o que prova isso é o registro que ela
        # deixou. Sem este campo, "a abertura testa cada sonda" seria frase que nada
        # cobra — e é assim que mecanismo descrito e nunca executado nasce.
        prova = sonda.get("teste_registro")
        if not prova:
            erros.append("a sonda não foi testada: falta `teste_registro`")
        else:
            cam = prova if os.path.isabs(prova) else os.path.join(missao, prova)
            if not os.path.isfile(cam):
                erros.append("o registro de teste da sonda não está no disco: %s" % prova)
            elif os.path.getsize(cam) == 0:
                erros.append("a sonda rodou e não produziu registro: %s está vazio" % prova)
    else:
        erros.append("a sonda tem que ser um bloco com preparar, registrar e alvo")

    eixos = rito.get("eixos") or []
    if isinstance(eixos, list):
        for i, eixo in enumerate(eixos):
            if not isinstance(eixo, dict):
                erros.append("o eixo %d não é um bloco" % i)
                continue
            for campo in ("nome", "gesto", "registro"):
                if not eixo.get(campo):
                    erros.append(
                        "o eixo `%s` não declara `%s`" % (eixo.get("nome", i), campo)
                    )
            # RÉGUA, NUNCA RECEITA: nome de eixo com medida é o vetor da cópia — o
            # briefing interpola o nome, e "moldura de 32px" vira moldura de 32px.
            nome_eixo = eixo.get("nome") or ""
            if MEDIDA_NO_NOME.search(nome_eixo):
                erros.append(
                    "o eixo `%s` traz MEDIDA no nome — nome nomeia qualidade; o "
                    "número do alvo vai em `numero`, como prova de nível, nunca "
                    "como receita" % nome_eixo
                )
            # O registro do eixo é caminho DE DENTRO da missão. Absoluto já levou o nome
            # da conta da máquina para um arquivo do projeto, e sair da missão por `..`
            # tem o mesmo efeito — por isso os dois são recusados antes de procurar.
            reg = eixo.get("registro")
            if reg and os.path.isabs(reg):
                erros.append(
                    "o registro do eixo `%s` é caminho absoluto: %s — grave-o relativo "
                    "à missão (recon/registros/…), senão ele leva o nome da conta junto"
                    % (eixo.get("nome"), reg)
                )
            elif reg and not _dentro_da_missao(missao, reg):
                erros.append(
                    "o registro do eixo `%s` aponta para fora da missão: %s"
                    % (eixo.get("nome"), reg)
                )
            elif reg and not os.path.isfile(os.path.join(missao, reg)):
                erros.append(
                    "o registro do eixo `%s` não está no disco: %s" % (eixo.get("nome"), reg)
                )
    else:
        erros.append("`eixos` tem que ser uma lista")
    return erros


# ─────────────────────────────────────────────────────────────────────────────
# fecho — o fecho pode acontecer?
# ─────────────────────────────────────────────────────────────────────────────

def _erros_do_veredito(missao, peca, dir_rodada, nomes_de_eixo, raiz=None,
                       arsenal=False):
    """As checagens de UM veredito. Cada uma nasceu de uma falha documentada."""
    erros = []
    cam_v = os.path.join(dir_rodada, "veredito.json")
    rodada = os.path.basename(dir_rodada)

    raiz = raiz or missao
    ver, erro = _le(cam_v)
    if erro:
        # A falha central: houve entrega e não houve julgamento nenhum.
        return ["%s %s: não há veredito — %s" % (peca, rodada, erro)]
    if not isinstance(ver, dict):
        return ["%s %s: o veredito não é um bloco de campos — grave um objeto JSON"
                % (peca, rodada)]

    # Dado malformado recusa com MENSAGEM, nunca com estouro. Medido em 2026-08-10:
    # três vereditos reais gravaram lista ou bloco onde o programa esperava texto, e a
    # resposta foi exceção sem uma linha útil — o juiz não tinha como saber o que
    # corrigir. O campo malformado é anulado para o resto das checagens seguir.
    malformados = []
    for campo in ("peca", "status", "eixo", "gap", "entrega"):
        valor = ver.get(campo)
        if valor is not None and not isinstance(valor, str):
            malformados.append(campo)
            ver[campo] = None
    regs_cru = ver.get("registros")
    if regs_cru is not None and not isinstance(regs_cru, dict):
        malformados.append("registros")
        ver["registros"] = {}
    elif isinstance(regs_cru, dict):
        for lado in ("nosso", "alvo"):
            valor = regs_cru.get(lado)
            if valor is not None and not isinstance(valor, str):
                malformados.append("registros.%s" % lado)
                regs_cru[lado] = None
    for campo in malformados:
        erros.append(
            "%s %s: o campo `%s` do veredito não é texto — grave texto simples, "
            "não lista nem bloco" % (peca, rodada, campo)
        )

    # A pergunta que fecha peça é de GENTE: o juiz declara se ficou boquiaberto.
    # Sem este campo, "melhor que o alvo" volta a ser comparação de grandezas — onze
    # vereditos honestos aprovaram uma obra vergonhosa numa noite real.
    if "impressionado" not in ver:
        erros.append(
            "%s %s: o veredito não declara `impressionado` — o juiz diz se ficou "
            "boquiaberto (true/false); sem isso não há julgamento de gosto"
            % (peca, rodada)
        )
    elif not isinstance(ver.get("impressionado"), bool):
        erros.append(
            "%s %s: `impressionado` é true ou false, nada mais" % (peca, rodada)
        )
    if ver.get("status") == "aprovado":
        if ver.get("impressionado") is not True:
            erros.append(
                "%s %s: aprovou sem estar boquiaberto — aprovar É a declaração de "
                "impressão; ganho pequeno é `marginal`, e a peça segue" % (peca, rodada)
            )
        frase = ver.get("frase")
        if not frase or not isinstance(frase, str):
            erros.append(
                "%s %s: falta a `frase` — em palavras de gente, o que na obra te "
                "impressionou diante do alvo inteiro" % (peca, rodada)
            )

    # A rodada tem que ser a dela. Copiar r1/ inteiro de uma peça aprovada para outra
    # traz a âncora junto e daria fecho verde com a peça jamais julgada.
    esperada = int(rodada[1:]) if rodada[1:].isdigit() else None
    if ver.get("peca") != peca:
        erros.append(
            "%s %s: este veredito é da peça `%s` — foi transplantado"
            % (peca, rodada, ver.get("peca"))
        )
    if esperada is not None and ver.get("rodada") != esperada:
        erros.append(
            "%s %s: este veredito diz ser da rodada %s" % (peca, rodada, ver.get("rodada"))
        )
    if ver.get("status") not in STATUS:
        erros.append(
            "%s %s: o veredito não diz %s" % (peca, rodada, " nem ".join(STATUS))
        )

    # Os dois registros, ou o veredito é nulo. Medido: o orquestrador aceitou sete
    # entregas olhando os prints que os PRÓPRIOS construtores produziram.
    regs = ver.get("registros") or {}
    nosso, alvo = regs.get("nosso"), regs.get("alvo")
    if not nosso or not alvo:
        erros.append("%s %s: veredito sem o par de registros é nulo" % (peca, rodada))
    else:
        cnosso = os.path.join(missao, nosso) if not os.path.isabs(nosso) else nosso
        calvo = os.path.join(missao, alvo) if not os.path.isabs(alvo) else alvo
        for rotulo, cam in (("nosso", cnosso), ("do alvo", calvo)):
            if not os.path.isfile(cam):
                erros.append("%s %s: o registro %s não está no disco" % (peca, rodada, rotulo))
            elif os.path.getsize(cam) == 0:
                erros.append("%s %s: o registro %s está vazio" % (peca, rodada, rotulo))
        if nosso == alvo:
            erros.append(
                "%s %s: o mesmo arquivo nos dois lados — não houve comparação" % (peca, rodada)
            )
        elif (os.path.isfile(cnosso) and os.path.isfile(calvo)
                and marca(cnosso) == marca(calvo)):
            erros.append(
                "%s %s: os dois registros têm o mesmo conteúdo" % (peca, rodada)
            )

    # O veredito ancora na ENTREGA que ele julgou, e a entrega ancora nos artefatos.
    # A entrega é ALEGAÇÃO do construtor, nunca carimbo: o programa recomputa tudo
    # contra o disco. Construtor que mente no manifesto é pego aqui.
    cam_e = os.path.join(dir_rodada, "entrega.json")
    ent, erro_e = _le(cam_e)
    if erro_e:
        erros.append("%s %s: não há manifesto de entrega — %s" % (peca, rodada, erro_e))
    else:
        if ver.get("entrega") != marca(cam_e):
            erros.append(
                "%s %s: o veredito julgou OUTRA entrega — é veredito requentado"
                % (peca, rodada)
            )
        if ent.get("peca") != peca:
            erros.append(
                "%s %s: este manifesto é da peça `%s`" % (peca, rodada, ent.get("peca"))
            )
        # O arsenal é oferta do dono; a ENTREGA diz o que dele foi usado, e é essa
        # declaração que dá ao dono a chance de vetar a dependência. Lista vazia é
        # resposta ("não usei nada"); campo ausente é silêncio, e silêncio não vale.
        if arsenal and "arsenal_usado" not in ent:
            erros.append(
                "%s %s: a missão tem arsenal e a entrega não declara `arsenal_usado`"
                % (peca, rodada)
            )
        artefatos = ent.get("artefatos") or []
        if not artefatos:
            erros.append("%s %s: o manifesto não lista artefato nenhum" % (peca, rodada))
        for art in artefatos:
            arquivo, esperado = art.get("caminho"), art.get("marca")
            if not arquivo or not esperado:
                erros.append("%s %s: artefato sem caminho ou sem marca" % (peca, rodada))
                continue
            cam = arquivo if os.path.isabs(arquivo) else os.path.join(raiz, arquivo)
            atual = marca(cam)
            if atual is None:
                erros.append("%s %s: o artefato %s sumiu" % (peca, rodada, arquivo))
            elif atual != esperado:
                erros.append(
                    "%s %s: %s mudou depois de julgado" % (peca, rodada, arquivo)
                )

    # O gap nomeia um eixo que existe. Eixo novo é permitido — o juiz pode ver o que o
    # reconhecimento não viu —, mas paga o mesmo preço de prova.
    if ver.get("status") in ("reprovado", "marginal"):
        if not ver.get("gap"):
            erros.append("%s %s: reprovou sem dizer o gap" % (peca, rodada))
        eixo = ver.get("eixo")
        if not eixo:
            erros.append("%s %s: o gap não nomeia eixo nenhum" % (peca, rodada))
        elif eixo not in nomes_de_eixo and not ver.get("eixo_novo"):
            erros.append(
                "%s %s: o eixo `%s` não existe e não foi declarado novo" % (peca, rodada, eixo)
            )
    return erros


def erros_do_fecho(missao):
    """Devolve a lista de furos do fecho. Lista vazia = a missão pode fechar."""
    erros = []
    rito, erro_rito = _le(os.path.join(missao, "rito.json"))
    if erro_rito:
        return ["o rito não está no disco — %s" % erro_rito]
    nomes_de_eixo = {
        e.get("nome") for e in (rito.get("eixos") or []) if isinstance(e, dict)
    }
    # Onde o artefato mora. O registro é da missão; a OBRA é do projeto, e adivinhar
    # a base fazia todo artefato relativo virar "sumiu" numa missão de verdade.
    raiz = rito.get("raiz") or missao
    if not os.path.isabs(raiz):
        raiz = os.path.join(missao, raiz)

    # A régua não pode mudar no meio: tirar um eixo do rito depois de julgamentos
    # feitos rebaixa a barra, e o fecho aprovaria sem nada acusar.
    cam_ancora = os.path.join(missao, "rito-aprovado.marca")
    if os.path.isfile(cam_ancora):
        with open(cam_ancora, encoding="utf-8") as fh:
            ancorada = fh.read().strip()
        if ancorada and ancorada != marca(os.path.join(missao, "rito.json")):
            erros.append(
                "a régua mudou depois da abertura — o rito não é mais o que foi aprovado"
            )
    else:
        erros.append("a missão nunca passou pela abertura: falta a âncora da régua")

    # A lei em documento mora FORA do rito, e a âncora da régua não a cobre. Sem esta
    # conta, "reconfira a lei no fecho" dependia da memória de quem orquestra — e o
    # dono aprovaria obra julgada contra regra que já não vale.
    leis = _leis_em_arquivo(rito, missao)
    gravadas, erro_lei = _le(os.path.join(missao, "lei-aprovada.marca"))
    if leis and erro_lei:
        erros.append(
            "a lei em documento nunca foi ancorada — rode o `rito` de novo para ancorar"
        )
    elif not erro_lei:
        atuais = dict(leis)
        for entrada, cam in leis:
            if entrada not in gravadas:
                erros.append(
                    "a lei `%s` entrou depois da abertura — reancore com o dono" % entrada
                )
            elif marca(cam) != gravadas[entrada]:
                erros.append(
                    "a lei `%s` mudou durante a missão — mostre ao dono antes de fechar"
                    % entrada
                )
        for entrada in gravadas:
            if entrada not in atuais:
                erros.append("a lei `%s` sumiu do disco depois da abertura" % entrada)

    decomp, erro = _le(os.path.join(missao, "decomposicao.json"))
    if erro:
        return erros + ["a decomposição não está no disco — %s" % erro]
    pecas = decomp.get("pecas") or []
    if not pecas:
        return ["a decomposição não tem peça nenhuma"]

    aprovadas = {}
    for peca in pecas:
        nome = peca.get("id") or peca.get("nome")
        dir_peca = os.path.join(missao, "pecas", nome)
        ultima = _ultima_rodada(dir_peca)
        if ultima is None:
            # É esta linha que pega "sete construtores, zero juízes".
            erros.append("%s: nenhuma rodada no disco" % nome)
            continue
        erros.extend(_erros_do_veredito(missao, nome, ultima, nomes_de_eixo, raiz,
                                        arsenal=bool(rito.get("arsenal"))))
        # TODA rodada entregue tem juiz, não só a última. Medido em 2026-08-09: com
        # r1 entregue e sem veredito e r2 entregue e julgada, o fecho dizia "todo
        # pedaço julgado" — a falha de origem escapando pela porta da rodada
        # intermediária. No laço normal isto nunca acusa nada: rodada que existe é
        # rodada que o juiz reprovou, e reprovar é gravar veredito.
        for anterior in _rodadas(dir_peca):
            if anterior == ultima:
                continue
            if not os.path.isfile(os.path.join(anterior, "entrega.json")):
                continue
            ver_ant, erro_ant = _le(os.path.join(anterior, "veredito.json"))
            if erro_ant or not isinstance(ver_ant, dict) or ver_ant.get("status") not in STATUS:
                erros.append(
                    "%s %s: houve entrega nesta rodada e nenhum juiz a julgou"
                    % (nome, os.path.basename(anterior))
                )
        ver, _ = _le(os.path.join(ultima, "veredito.json"))
        status = ver.get("status") if isinstance(ver, dict) else None
        if status == "aprovado":
            aprovadas[nome] = marca(os.path.join(ultima, "entrega.json"))
        elif status == "marginal":
            # `marginal` é relato, não saída. Fechar peça por retorno decrescente com
            # orçamento sobrando é a rendição medida em 2026-08-09: o que fecha peça é
            # juiz boquiaberto, orçamento esgotado, ou o dono mandando parar (e parar
            # é `encerra`, não fecho verde). Ganho pequeno manda propor caminho NOVO.
            orc = rito.get("orcamento") if isinstance(rito.get("orcamento"), dict) else {}
            rpp = orc.get("rodadas_por_peca")
            usadas = len(_rodadas(dir_peca))
            if isinstance(rpp, int) and usadas < rpp:
                erros.append(
                    "%s: parou por ganho pequeno com %d rodada(s) sobrando — "
                    "`marginal` não fecha peça: o construtor seguinte propõe um "
                    "caminho NOVO, até o juiz ficar boquiaberto ou o orçamento acabar"
                    % (nome, rpp - usadas)
                )
            else:
                aprovadas[nome] = marca(os.path.join(ultima, "entrega.json"))
        else:
            erros.append("%s: a última rodada não fechou" % nome)

    # Peça que sai da decomposição levaria o REPROVADO dela junto, em silêncio — é a
    # falha da conversa atropelada reintroduzida por outra porta.
    dir_pecas = os.path.join(missao, "pecas")
    if os.path.isdir(dir_pecas):
        conhecidas = {p.get("id") or p.get("nome") for p in pecas}
        for nome in sorted(os.listdir(dir_pecas)):
            if nome.startswith(".") or nome in conhecidas:
                continue
            if os.path.isdir(os.path.join(dir_pecas, nome)):
                erros.append(
                    "há trabalho de `%s` no disco, e a decomposição não a conhece mais"
                    % nome
                )

    # Todo eixo tem dono: o que não coube em peça é do diretor. Sem esta conta, o
    # defeito ENTRE peças é invisível a todos os juízes — medido: um aprovou letra a
    # 74% de largura, outro a 62%, e a incoerência não morava em nenhuma das duas.
    donos = set()
    for peca in pecas:
        donos.update(peca.get("eixos") or [])
    orfaos = sorted(nomes_de_eixo - donos - set(decomp.get("eixos_do_diretor") or []))
    if orfaos:
        erros.append("eixo sem dono: %s" % " · ".join(orfaos))

    # O diretor passou, e passou DEPOIS da última aprovação de peça.
    diretor, erro = _le(os.path.join(missao, "diretor.json"))
    if erro:
        erros.append("o diretor não passou pelo conjunto — %s" % erro)
    else:
        if diretor.get("status") != "aprovado":
            erros.append("o diretor não aprovou o conjunto")
        # Sem relógio: o diretor diz QUAL entrega de cada peça ele viu, e o programa
        # compara com a vigente. Data seria frágil — não sobrevive a clone nem a cópia.
        viu = diretor.get("viu") or {}
        for peca_nome, vigente in sorted(aprovadas.items()):
            if viu.get(peca_nome) != vigente:
                erros.append(
                    "o diretor olhou uma versão superada de `%s`" % peca_nome
                )

    # Veto do dono depois de uma aprovação que ele toca: ou tem julgamento novo, ou a
    # peça consta reaberta. É o que impede o aprovado de evaporar em silêncio.
    for veto in _linhas(os.path.join(missao, "vetos.jsonl")):
        if veto.get("mantido"):
            continue
        for alvo, sha_no_veto in (veto.get("toca") or {}).items():
            vigente = aprovadas.get(alvo)
            if vigente and vigente == sha_no_veto:
                erros.append(
                    "o veto `%s` toca `%s`, que não foi retrabalhado desde então"
                    % (veto.get("o_que", "?"), alvo)
                )
    return erros


# ─────────────────────────────────────────────────────────────────────────────
# mapa — o estado legível, derivado
# ─────────────────────────────────────────────────────────────────────────────

def desenha_mapa(missao):
    """O estado da missão, lido do disco. Nenhum agente escreve isto."""
    linhas = ["# Onde a missão está", ""]
    rito, erro = _le(os.path.join(missao, "rito.json"))
    if erro:
        return "\n".join(linhas + ["A missão não tem rito no disco.", ""])

    linhas.append("**Objetivo:** %s" % rito.get("objetivo", "—"))
    linhas.append("**Alvos:** %s" % " · ".join(rito.get("alvos") or ["—"]))
    linhas.append("")

    decomp, erro = _le(os.path.join(missao, "decomposicao.json"))
    if erro:
        linhas += ["A decomposição ainda não existe.", ""]
    else:
        pecas = decomp.get("pecas") or []
        linhas.append("| peça | rodadas | estado | o maior gap aberto |")
        linhas.append("|---|---|---|---|")
        for peca in pecas:
            nome = peca.get("id") or peca.get("nome")
            rodadas = _rodadas(os.path.join(missao, "pecas", nome))
            if not rodadas:
                linhas.append("| %s | 0 | **nunca julgada** | — |" % nome)
                continue
            ver, _ = _le(os.path.join(rodadas[-1], "veredito.json"))
            if ver is None:
                estado, gap = "**entregue, SEM JUÍZO**", "—"
            elif ver.get("status") == "aprovado":
                estado, gap = "aprovada", "—"
            elif ver.get("status") == "marginal":
                estado = "ganho pequeno declarado — segue aberta até impressionar"
                gap = ver.get("gap", "—")
            else:
                estado = "reprovada"
                gap = "%s — %s" % (ver.get("eixo", "?"), ver.get("gap", "?"))
            linhas.append("| %s | %d | %s | %s |" % (nome, len(rodadas), estado, gap))
        linhas.append("")

    vetos = _linhas(os.path.join(missao, "vetos.jsonl"))
    if vetos:
        linhas.append("## Os seus vetos")
        for v in vetos:
            linhas.append("- **%s** — %s" % (v.get("quando", "?"), v.get("o_que", "?")))
        linhas.append("")

    furos = erros_do_fecho(missao)
    linhas.append("## O que falta para fechar")
    if furos:
        linhas += ["- %s" % f for f in furos]
    else:
        linhas.append("Nada: o fecho está liberado.")
    linhas.append("")
    return "\n".join(linhas)


# ─────────────────────────────────────────────────────────────────────────────
# pendentes — a pergunta da trava dupla: qual peça está entregue e sem juiz?
# ─────────────────────────────────────────────────────────────────────────────

def pecas_pendentes(missao):
    """As peças com ALGUMA rodada entregue e sem veredito legível.

    É a foto exata da falha central ("sete construtores, zero juízes") tirada EM VOO,
    não no fecho: o guarda de PreToolUse consulta esta lista antes de deixar um novo
    agente partir, e enquanto ela não estiver vazia só o juiz da peça pendente passa.
    Peça sem rodada nenhuma não entra: ainda não houve entrega para julgar.

    Olha TODA rodada, não só a última: uma rodada seguinte gravada por cima apagava
    a pendência da anterior, e a entrega sem juiz seguia viva sem ninguém acusar.
    """
    fora = []
    decomp, erro = _le(os.path.join(missao, "decomposicao.json"))
    if erro:
        return fora
    for peca in decomp.get("pecas") or []:
        nome = peca.get("id") or peca.get("nome")
        for rodada in _rodadas(os.path.join(missao, "pecas", nome)):
            if not os.path.isfile(os.path.join(rodada, "entrega.json")):
                continue
            ver, erro_v = _le(os.path.join(rodada, "veredito.json"))
            if erro_v or not isinstance(ver, dict) or ver.get("status") not in STATUS:
                fora.append(nome)
                break
    return fora


# ─────────────────────────────────────────────────────────────────────────────
# veto — quem grava a linha do dono, e quem detecta o toque
# ─────────────────────────────────────────────────────────────────────────────

def grava_veto(missao, o_que, pecas):
    """Grava o veto e devolve as peças tocadas que já estavam fechadas.

    Quem grava é este programa, não quem orquestra: o veto carrega a marca da entrega
    vigente de cada peça no momento em que foi dado, e é essa marca que depois prova
    se houve retrabalho. Se quem conduz redigisse a linha, o registro do veto seria
    mais um arquivo que o interessado carimba.
    """
    decomp, erro = _le(os.path.join(missao, "decomposicao.json"))
    conhecidas = set()
    if not erro:
        conhecidas = {(p.get("id") or p.get("nome")) for p in (decomp.get("pecas") or [])}

    toca, fechadas, desconhecidas = {}, [], []
    for peca in pecas:
        if conhecidas and peca not in conhecidas:
            desconhecidas.append(peca)
            continue
        ultima = _ultima_rodada(os.path.join(missao, "pecas", peca))
        sha = marca(os.path.join(ultima, "entrega.json")) if ultima else None
        toca[peca] = sha
        if ultima:
            ver, _ = _le(os.path.join(ultima, "veredito.json"))
            if ver and ver.get("status") in ("aprovado", "marginal"):
                fechadas.append(peca)

    # Veto sem peça não segura fecho nenhum. Veto global é legítimo, então isto avisa
    # em vez de recusar — mas calar seria deixar o dono achar que trancou algo.
    if not toca:
        desconhecidas = desconhecidas or []
    with open(os.path.join(missao, "vetos.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"o_que": o_que, "toca": toca}, ensure_ascii=False) + "\n")
    return fechadas, desconhecidas


# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("comando", choices=("rito", "fecho", "mapa", "veto", "pendentes", "encerra"))
    p.add_argument("missao", help="o diretório da missão em .claude/gauntlet/")
    p.add_argument("--o-que", help="o texto do veto, para o comando `veto`")
    p.add_argument("--pecas", help="as peças que o veto toca, separadas por vírgula")
    p.add_argument("--sinal", help="o arquivo que marca uma missão de pé, para o `rito`")
    args = p.parse_args(argv)

    # ENCERRAR NÃO É APROVAR. Vem ANTES de tudo e não julga nada: a disputa parada
    # pelo dono, abandonada, ou cujo fecho foi recusado por furo, tem que poder
    # apagar o sinal — senão a barra anuncia "missão de pé" de algo que ninguém vai
    # retomar. Foi o que aconteceu: o apagamento vivia só no caminho do fecho VERDE.
    if args.comando == "encerra":
        if not args.sinal:
            print("⛔ encerra sem --sinal — diga qual arquivo apagar")
            return 2
        apaga_sinal(args.sinal)
        print("missão encerrada na barra. O veredito do fecho NÃO foi dado — "
              "encerrar não é aprovar.")
        return 0

    if args.comando == "veto":
        if not args.o_que:
            print("⛔ veto sem texto — diga o que foi vetado, com --o-que")
            return 2
        pecas = [x.strip() for x in (args.pecas or "").split(",") if x.strip()]
        fechadas, desconhecidas = grava_veto(args.missao, args.o_que, pecas)
        print("veto registrado: %s" % args.o_que)
        if not pecas:
            print("   ⚠️  sem peça nomeada — ele NÃO vai segurar o fecho de nada")
        if desconhecidas:
            print("   ⚠️  peça(s) que a decomposição não conhece: %s"
                  % " · ".join(desconhecidas))
        if fechadas:
            # É esta linha que dispara a pergunta ao dono. Sem ela, o veto derrubaria
            # em silêncio um trabalho que já tinha passado por juiz.
            print("   ⚠️  ELE TOCA COISA JÁ FECHADA: %s" % " · ".join(fechadas))
            print("   PERGUNTE ao dono antes de reabrir. Se ele mandar manter como está,")
            print("   acrescente `\"mantido\": true` na linha do veto.")
            return 3
        return 0

    if args.comando == "pendentes":
        # Uma peça por linha, nada mais: é interface de programa (o guarda de
        # PreToolUse), não de gente. Lista vazia = nenhum juiz devido agora.
        for nome in pecas_pendentes(args.missao):
            print(nome)
        return 0

    if args.comando == "mapa":
        texto = desenha_mapa(args.missao)
        destino = os.path.join(args.missao, "MAPA.md")
        try:
            with open(destino, "w", encoding="utf-8") as fh:
                fh.write(texto)
        except OSError:
            pass
        sys.stdout.write(texto)
        return 0

    if args.comando == "rito":
        furos = erros_do_rito(args.missao, args.sinal)
    else:
        furos = erros_do_fecho(args.missao)
    if not furos:
        if args.comando == "rito":
            # A régua fica ancorada aqui, e quem a ancora é o programa. Sem isto,
            # editar o rito no meio da missão rebaixa a barra e o fecho aprova.
            with open(os.path.join(args.missao, "rito-aprovado.marca"), "w",
                      encoding="utf-8") as fh:
                fh.write(marca(os.path.join(args.missao, "rito.json")) or "")
            # A lei em documento ganha âncora própria: a do rito só congela o que
            # está DENTRO do rito.json, e a lei mora fora.
            ancora_leis(args.missao)
            print("rito completo — a missão pode começar.")
            return 0
        print("fecho liberado — todo pedaço julgado, com o par de registros.")
        # Quem apaga o sinal é ESTE caminho, e só ele. Estava escrito em três lugares
        # da skill e em nenhuma linha de código — que é o defeito que ela combate.
        if args.sinal:
            apaga_sinal(args.sinal)
        return 0

    print("⛔ %s recusado — %d furo(s):" % (args.comando, len(furos)))
    for f in furos:
        print("   %s" % f)
    print("\nmapa do que falta: python3 %s mapa %s" % (sys.argv[0], args.missao))
    return 1


if __name__ == "__main__":
    sys.exit(main())
