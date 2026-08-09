#!/usr/bin/env python3
"""O andamento de uma ferramenta longa, em uma linha — relogio, estimativa, avanco.

POR QUE EXISTE. Dentro de um Workflow o dono fica cego: o agente entra em idle e a
tela nao diz se ele esta rodando uma suite de 11 minutos ou travado. "Idle" nao
carrega hora nem progresso, entao parada legitima e travamento se parecem.

O QUE FOI MEDIDO ANTES DE ESCREVER (299 transcripts de agente de workflow deste
projeto, 2026-08-06):

  FERRAMENTA              n  mediana      p90      max
  Bash                 6047     0.7s    19.1s   660.4s
  suite/test (bash)    2043     1.4s    66.7s   660.4s

Duas conclusoes vieram dai, e as duas sao regra deste modulo:

1. ESTIMATIVA SO POR MEMORIA DO PROPRIO COMANDO, NESTE PROJETO. A dispersao e de
   quase mil vezes entre a mediana e o maximo, entao media global — ou pior,
   palpite por "complexidade do codigo" — produziria numero com cara de dado e
   sem lastro. Comando sem historico aqui sai SEM estimativa: o relogio sozinho e
   honesto, o numero inventado nao. Suite costuma rodar varias vezes no mesmo
   projeto, e e disso que a estimativa vive.

2. REPETICAO DE COMANDO NAO E SINTOMA DE CIRCULO. Medido: 0 de 282 agentes
   repetiram o mesmo comando 4x ou mais. Um detector baseado nisso nao pegaria
   nada. O sinal que EXISTE e o placar que a propria suite imprime — 540
   ocorrencias na amostra, em tres formatos — e e nele que `avanco()` se apoia:
   placar igual duas vezes seguidas e que significa "nao andou".

O modulo nao decide nada e nao bloqueia nada: devolve texto para o vigia narrar.
"""

import json
import os
import re
import time

_CONFIG = os.environ.get("CLAUDE_CONFIG_DIR",
                         os.path.join(os.path.expanduser("~"), ".claude"))

# A CASA DO ESTADO E NEUTRA. Quatro plugins ja chamam este modulo; a pasta batizada
# com o nome de um deles fazia o estado dos outros parecer emprestado. O que NASCE
# vai pra ca.
ESTADO = os.path.join(_CONFIG, "andamento")

# A casa antiga continua sendo LIDA — missao que ja estava de pe quando a pasta
# mudou nao pode perder a memoria dela. So leitura: nada novo e escrito aqui.
ESTADO_LEGADO = os.path.join(_CONFIG, "sovai")


def _ler(base, nome):
    """O caminho de onde LER: a casa nova primeiro, a antiga quando ela nao tem.

    Vale so pra casa padrao — quem passa `dir_estado` (bancada, ou motor com casa
    propria) esta dizendo exatamente onde olhar, e ai nao ha legado que valha.
    """
    novo = os.path.join(base, nome)
    if base != ESTADO or os.path.exists(novo):
        return novo
    antigo = os.path.join(ESTADO_LEGADO, nome)
    return antigo if os.path.exists(antigo) else novo


# Os TRES formatos que a amostra mostrou, em ordem de frequencia medida.
# Cada um devolve (passou, falhou) — `falhou` e None quando o formato nao informa.
PLACARES = (
    re.compile(r"(\d+)\s+passou\s*·\s*(\d+)\s+falhou"),      # 139 passou · 0 falhou
    re.compile(r"(\d+)\s+ok\s*/\s*(\d+)\s+falhas?"),          # 17 ok / 0 falhas
    re.compile(r"OK\s*\((\d+)\s+checks?\)"),                  # OK (56 checks)
    re.compile(r"(\d+)\s+passed(?:,\s*(\d+)\s+failed)?"),     # pytest/jest
)


def _arquivo(projeto):
    """Um registro por projeto. A memoria de um projeto nunca estima a de outro."""
    seguro = re.sub(r"[^A-Za-z0-9_.-]", "-", projeto.strip("/"))[-120:] or "sem-projeto"
    return os.path.join(ESTADO, "duracoes-%s.json" % seguro)


def _arquivo_lido(projeto):
    """O mesmo registro, mas de onde ele PODE estar: casa nova ou a antiga."""
    return _ler(ESTADO, os.path.basename(_arquivo(projeto)))


def _chave(comando):
    """O comando sem o que varia entre execucoes iguais.

    Caminho temporario e numero solto entram como curinga, senao a mesma suite
    rodada duas vezes viraria duas entradas e a memoria nunca acumularia.
    """
    c = " ".join(str(comando).split())
    c = re.sub(r"/(?:tmp|var/folders)/\S+", "<tmp>", c)
    c = re.sub(r"\b\d{4}-\d{2}-\d{2}\S*", "<data>", c)
    return c[:200]


def registrar(projeto, comando, segundos):
    """Guarda quanto ESTE comando demorou AQUI. Guarda as 5 ultimas."""
    caminho = _arquivo(projeto)
    try:
        os.makedirs(ESTADO, exist_ok=True)
        try:
            # LE de onde estiver (casa antiga inclusive) e ESCREVE na casa nova:
            # e assim que a memoria de uma missao viva atravessa a troca de pasta.
            with open(_arquivo_lido(projeto), encoding="utf-8") as fh:
                dados = json.load(fh)
        except (OSError, ValueError):
            dados = {}
        k = _chave(comando)
        v = dados.get(k, [])
        v.append(round(float(segundos), 1))
        dados[k] = v[-5:]
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(dados, fh, ensure_ascii=False)
        os.replace(tmp, caminho)
        return dados[k]
    except OSError:
        # Falhar aqui nao pode derrubar a missao: sem memoria a linha sai sem
        # estimativa, que e exatamente o caso do comando novo.
        return []


def estimativa(projeto, comando):
    """Segundos esperados, ou None quando este comando nunca rodou aqui.

    None NAO e falha: e a resposta honesta pra comando sem historico. Quem chama
    tem que saber imprimir a linha sem numero.
    """
    try:
        with open(_arquivo_lido(projeto), encoding="utf-8") as fh:
            v = json.load(fh).get(_chave(comando)) or []
    except (OSError, ValueError):
        return None
    if not v:
        return None
    ordenado = sorted(v)
    return ordenado[len(ordenado) // 2]      # mediana das ultimas


def placar(saida):
    """O placar que a propria ferramenta imprimiu, ou None.

    Le a saida CRUA — nao pergunta ao modelo o que aconteceu. Varre de tras pra
    frente porque a suite imprime o total no fim.
    """
    texto = str(saida or "")
    for linha in reversed(texto.splitlines()[-40:]):
        # Linha com marcacao de markdown NAO e saida de suite: e prosa FALANDO sobre
        # placar. Medido em 2026-08-06 num motor real — o texto que documenta o formato
        # ("a linha crua que a suite imprimiu (`139 passou · 0 falhou`)") foi lido como
        # se fosse o placar daquele agente. Saida crua de suite nao tem crase nem
        # asterisco duplo; prosa sobre ela quase sempre tem.
        if "`" in linha or "**" in linha:
            continue
        for rx in PLACARES:
            m = rx.search(linha)
            if m:
                g = m.groups()
                passou = int(g[0])
                falhou = int(g[1]) if len(g) > 1 and g[1] is not None else None
                return {"passou": passou, "falhou": falhou, "linha": linha.strip()[:120]}
    return None


def _como_placar(x):
    """Aceita o placar ja estruturado OU a saida crua de onde ele sai.

    O chamador real guarda o placar da rodada anterior em disco e o relê; nem
    sempre volta dicionario — volta o texto que a suite imprimiu. Assumir a
    estrutura fazia `avanco()` estourar em cima do narrador, que e justamente o
    componente que existe pra nao deixar o dono no escuro.
    """
    if isinstance(x, dict):
        return x if "passou" in x else None
    if isinstance(x, str):
        return placar(x)
    return None


def avanco(anterior, atual):
    """Andou, nao andou, ou piorou — comparando dois placares.

    'nao andou' e o sinal que interessa: duas rodadas com o MESMO placar querem
    dizer que a suite parou de mudar, e e ai que vale olhar.

    Os dois lados aceitam texto cru: ver `_como_placar`.
    """
    anterior = _como_placar(anterior)
    atual = _como_placar(atual)
    if atual is None:
        return "sem placar"
    if anterior is None:
        return "primeiro placar"
    if atual["passou"] > anterior["passou"]:
        return "avançou"
    if atual["passou"] < anterior["passou"]:
        return "regrediu"
    if (atual["falhou"] or 0) < (anterior["falhou"] or 0):
        return "avançou"
    return "sem avanço"


def onda(sessao, saida, dir_estado=None):
    """O placar da suite de UMA ONDA, comparado com o da onda anterior.

    O motor ja pedia o campo `placar` ao papel da suite e o DESCARTAVA: a
    comparacao entre ondas — o unico sinal medido de "esta em circulos" — nao
    chegava a tela nenhuma. Aqui o placar da onda fica no disco, por sessao (o
    mesmo lugar do resto do estado da missao), e sai comparado.

    Devolve None quando a saida nao tem placar: onda sem placar nao e onda nova,
    e sobrescrever o registro com nada apagaria o termo de comparacao.
    """
    p = _como_placar(saida)
    if p is None:
        return None
    base = dir_estado or ESTADO
    caminho = os.path.join(base, "placar-%s" % sessao)
    estado = avanco(ultimo_placar(sessao, base), p)
    linha = "suíte: %s — %s" % (p["linha"], estado)
    try:
        os.makedirs(base, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as fh:
            json.dump({"placar": p, "linha": linha}, fh, ensure_ascii=False)
    except OSError:
        # Fail-open como o resto do modulo: sem registro a proxima onda volta a
        # ser "primeiro placar", que e honesto.
        pass
    return linha


def doc_da_onda(sessao, rodada, docs, dir_estado=None):
    """Os caminhos de doc que a onda re-projetou, no disco (S-111).

    A lista confirmada pelo papel de doc so vivia na memoria do motor
    (`rounds[].doc`): terminada a missao, nao sobrava como provar que a doc do
    commit seguinte saiu da onda e nao de uma passada manual. Mesmo diretorio,
    mesma chave por sessao e mesma regra de fail-open do `placar-<sid>`.

    Devolve a lista gravada (vazia quando nao havia nada a gravar).
    """
    docs = [c for c in (docs or []) if c]
    if not docs:
        return []
    base = dir_estado or ESTADO
    try:
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "doc-%s" % sessao), "w",
                  encoding="utf-8") as fh:
            json.dump({"round": rodada, "docs": docs, "quando": time.time()},
                      fh, ensure_ascii=False)
    except OSError:
        # Fail-open: perder o registro nao pode derrubar a onda — o commit da
        # rodada ja esta feito quando este papel roda.
        pass
    return docs


def marca_onda(sessao, rodada, plano=None, dir_estado=None):
    """A rodada em curso e o progresso do plano, no disco (a barra so LE).

    A barra dizia ha quanto tempo a missao estava de pe e como foi a ultima
    suite, mas nao dizia EM QUE PONTO a missao esta: quem volta ao terminal via
    `missao ha 2h14` sem saber se isso e a primeira volta ou a decima. A rodada
    so existe na memoria do motor, e o progresso so existe no arquivo do plano —
    nenhum dos dois chega a um processo que desenha barra.

    O total sai do plano LIDO AQUI, uma vez por bloco, e nao do que o motor
    contou: quem marca os passos e o marcador, e pedir a conta a quem nao marcou
    e como o placar de suite que o motor descartava.
    """
    base = dir_estado or ESTADO
    registro = {"rodada": rodada}
    if plano:
        try:
            with open(plano, encoding="utf-8") as fh:
                itens = [it for ph in json.load(fh).get("phases", [])
                         for it in ph.get("items", [])]
            registro["feitos"] = sum(1 for it in itens if it.get("status") == "done")
            registro["total"] = len(itens)
        except (OSError, ValueError, AttributeError, TypeError):
            # Plano ilegivel = barra sem o placar do plano, nunca barra sem rodada.
            pass
    try:
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "onda-%s" % sessao), "w",
                  encoding="utf-8") as fh:
            json.dump(registro, fh, ensure_ascii=False)
    except OSError:
        pass   # fail-open, como o resto do modulo
    return registro


def linha_onda(sessao, dir_estado=None):
    """`onda 5 · 216/223` — ou None quando nenhuma onda se registrou ainda."""
    try:
        with open(_ler(dir_estado or ESTADO, "onda-%s" % sessao),
                  encoding="utf-8") as fh:
            reg = json.load(fh)
    except (OSError, ValueError):
        return None
    rodada = reg.get("rodada")
    if rodada in (None, ""):
        return None
    partes = ["onda %s" % rodada]
    if reg.get("total"):
        partes.append("%s/%s" % (reg.get("feitos", 0), reg["total"]))
    return " · ".join(partes)


def ultima_doc(sessao, dir_estado=None):
    """O registro de doc da ultima onda desta sessao, ou {} quando nao houve."""
    try:
        with open(_ler(dir_estado or ESTADO, "doc-%s" % sessao),
                  encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _registro_onda(sessao, dir_estado=None):
    try:
        with open(_ler(dir_estado or ESTADO, "placar-%s" % sessao),
                  encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def ultimo_placar(sessao, dir_estado=None):
    """O placar da onda anterior desta sessao, ou None na primeira."""
    return _registro_onda(sessao, dir_estado).get("placar")


def linha_placar(sessao, dir_estado=None):
    """A linha da ultima onda, lida do disco — ou None quando nao houve onda.

    E o que a BARRA le: ela e desenhada por um processo que nao viu a suite rodar.
    """
    return _registro_onda(sessao, dir_estado).get("linha") or None


def _dur(segundos):
    s = int(round(segundos))
    if s < 90:
        return "%ds" % s
    # Missao longa e o caso comum desta barra, e `194min12s` obriga quem le a
    # dividir de cabeca pra saber que sao tres horas.
    if s < 3600:
        return "%dmin%02ds" % (s // 60, s % 60)
    return "%dh%02d" % (s // 3600, (s % 3600) // 60)


# O mesmo teto do vigia do motor (`silenceLimitMin`, 12 min): abaixo dele silencio
# nao e nem demora nem travamento — e so uma ferramenta rodando.
LIMITE_SILENCIO = 12 * 60


def linha_silencio(mudo, trabalho_vivo, limite=LIMITE_SILENCIO):
    """O silencio longo, dito na tela — e dito COM O NOME CERTO.

    O vigia do motor ja separa demora de travamento (`mudo > silenceLimitMs &&
    !trabalhoVivo`), mas so a metade travamento fala: ela vira Bloqueio no
    relatorio. A demora legitima nao produz nada, entao a tela do dono ausente
    fica igual nos dois casos — que e o defeito que esta funcao fecha.

    - COM sinal de vida (ferramenta rodando ha tanto tempo quanto o silencio):
      sai `rodando ha N minutos`, e nada e derrubado.
    - SEM sinal de vida: sai a palavra travamento, porque ninguem estava
      trabalhando durante aquele silencio.

    Devolve None quando o silencio ainda nao passou do limite: narrar aqui seria
    ruido, e ruido acaba ensinando o dono a ignorar a linha.
    """
    if mudo is None or mudo <= limite:
        return None
    minutos = int(round(mudo / 60.0))
    if trabalho_vivo:
        return "rodando há %d min — trabalho vivo, não é travamento" % minutos
    return "travamento: nada mudou há %d min e não há trabalho vivo" % minutos


def linha_disparo(comando, projeto, agora=None):
    """A linha que o vigia narra AO DISPARAR: relogio sempre, estimativa se houver."""
    t = time.localtime(agora) if agora else time.localtime()
    rotulo = _chave(comando)
    rotulo = rotulo if len(rotulo) <= 60 else rotulo[:57] + "..."
    est = estimativa(projeto, comando)
    if est is None:
        return "%s · %s · primeira vez aqui, sem estimativa" % (
            time.strftime("%H:%M:%S", t), rotulo)
    return "%s · %s · ~%s (das %d vezes anteriores aqui)" % (
        time.strftime("%H:%M:%S", t), rotulo, _dur(est),
        len(_historico(projeto, comando)))


def _historico(projeto, comando):
    try:
        with open(_arquivo_lido(projeto), encoding="utf-8") as fh:
            return json.load(fh).get(_chave(comando)) or []
    except (OSError, ValueError):
        return []


def linha_andamento(comando, projeto, decorrido, saida_ate_agora="", anterior=None):
    """A linha que o vigia narra ENQUANTO roda. Calada quando nada mudou.

    Devolve None quando nao ha o que dizer — silencio significa 'nada mudou', e e
    o unico jeito de a narracao nao virar ruido.
    """
    p = placar(saida_ate_agora)
    est = estimativa(projeto, comando)
    partes = ["rodando há %s" % _dur(decorrido)]
    if est is not None:
        if decorrido > est * 2:
            partes.append("passou do dobro do usual (~%s)" % _dur(est))
        else:
            partes.append("usual ~%s" % _dur(est))
    if p:
        estado = avanco(anterior, p)
        partes.append("%s — %s" % (p["linha"], estado))
    elif est is None and decorrido < 60:
        return None
    return " · ".join(partes)


def _trabalho(base, sessao):
    """O disparo que QUEM EXECUTA gravou: (instante, comando, projeto), ou None.

    `trabalho-<sid>` e escrito quando um comando dispara e apagado quando ele
    volta: existir ja quer dizer "tem comando rodando agora". Alem do instante,
    quem grava passa o COMANDO e o PROJETO — sem esses dois a barra teria
    relogio e nao teria estimativa, porque `estimativa()` so responde por comando
    E projeto. Registro no formato antigo (so o carimbo) devolve comando vazio, e
    ai a barra fica exatamente a que sempre foi.
    """
    try:
        with open(_ler(base, "trabalho-%s" % sessao), encoding="utf-8") as fh:
            linhas = fh.read().splitlines()
        inicio = float(linhas[0].strip())
    except (OSError, ValueError, IndexError):
        return None
    return (inicio,
            linhas[1].strip() if len(linhas) > 1 else "",
            linhas[2].strip() if len(linhas) > 2 else "")


def _trabalho_vivo(base, sessao, agora, limite=LIMITE_SILENCIO):
    """Havia ferramenta DE PE durante o silencio? — lido do disco, nada perguntado.

    O instante do disparo e de onde sai a segunda metade da resposta — um comando
    de pe ha 3 segundos NAO explica um silencio de 20 minutos; so o que ja passou
    do mesmo teto ocupou o silencio inteiro. E a mesma regra que o gancho de
    andamento aplica no cartao (`decorrido >= LIMITE_SILENCIO`).
    """
    t = _trabalho(base, sessao)
    if t is None:
        return False
    return (agora - t[0]) >= limite


# QUEM ACENDEU O SINAL DIZ O NOME NO PROPRIO SINAL. Era a unica coisa do modulo
# presa a um plugin: a linha escrevia `sovai` fixo, e um workflow de outro motor
# aparecia na barra com o nome de quem nao o disparou.
MOTOR_PADRAO = "motor"

# Nome de motor e uma palavra so, comecando por letra. O sinal antigo e VAZIO, e
# houve quem gravasse um carimbo dentro dele — nenhum dos dois e nome, e nos dois
# casos a linha volta a ser a de sempre em vez de inventar um motor.
_NOME_MOTOR = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,30}$")


def _motor(caminho_ativo):
    """O nome do motor gravado no sinal, ou a execucao continua quando nao ha."""
    try:
        with open(caminho_ativo, encoding="utf-8") as fh:
            nome = fh.readline().strip()
    except OSError:
        return MOTOR_PADRAO
    return nome if _NOME_MOTOR.match(nome) else MOTOR_PADRAO


def linha_motor(sessao, dir_estado=None, agora=None):
    """A linha do motor para a barra de status, ou None quando nao ha motor vivo.

    POR QUE EXISTE. As linhas acima saem por `systemMessage`, que rola junto com a
    conversa: quem chega na tela depois de uma hora nao ve nenhuma delas. A barra
    de status e a unica superficie que fica, e ate aqui ela nao dizia se havia
    missao rodando.

    LE SO O QUE O MOTOR JA ESCREVE NO DISCO — nada de perguntar a ninguem:

      ativo-<sid>  aceso quando a missao arma, apagado quando ela entrega. A idade
                   dele e ha quanto tempo a missao esta de pe, e o que estiver
                   escrito dentro dele e o NOME do motor que a acendeu.
      sinal-<sid>  o instante em que o narrador falou pela ultima vez (o gancho de
                   andamento grava). A idade dele e o silencio.
      bloqueios-<sid>  o contador de negacoes do gate, quando ele existe.

    SEM `ativo-<sid>` DEVOLVE None, e e isso que faz a linha sumir quando nao ha
    motor: quem chama nao imprime nada e a barra volta a ser exatamente o que o
    renderizador desenha.
    """
    if not sessao:
        return None
    base = dir_estado or ESTADO
    agora = time.time() if agora is None else agora
    ativo = _ler(base, "ativo-%s" % sessao)
    try:
        idade = agora - os.path.getmtime(ativo)
    except OSError:
        return None

    # O ICONE ABRE CADA PEDACO porque a barra e lida de relance, no meio de outra
    # coisa: sem ele, achar o silencio no meio de seis frases separadas por ponto
    # exige LER a linha inteira. O separador vertical corta o que o ponto medio
    # nao cortava — ele tambem separa palavra dentro de cada pedaco.
    partes = ["🚀 %s · missão há %s" % (_motor(ativo), _dur(max(idade, 0)))]

    onda_atual = linha_onda(sessao, base)
    if onda_atual:
        partes.append("🌊 %s" % onda_atual)

    # O RELOGIO E A ESTIMATIVA DA FERRAMENTA QUE ESTA DE PE. Os dois ja nasciam em
    # `linha_disparo`, que sai por `systemMessage` e rola com a conversa: quem volta
    # ao terminal depois de uma hora nao ve nenhuma. Aqui eles chegam a superficie
    # que FICA. Nada e adivinhado — comando e projeto sao os que quem executa gravou
    # no disparo; sem eles nao ha o que dizer e a barra segue igual.
    t = _trabalho(base, sessao)
    if t and t[1]:
        decorrido = agora - t[0]
        if decorrido >= 0:
            corrido = "🔧 ferramenta há %s" % _dur(decorrido)
            est = estimativa(t[2], t[1])
            # Comando sem historico AQUI sai sem numero: a mesma regra do modulo
            # inteiro — relogio sozinho e honesto, numero inventado nao.
            if est is not None:
                corrido += " · usual ~%s" % _dur(est)
            partes.append(corrido)

    sinal = _ler(base, "sinal-%s" % sessao)
    mudo = None
    try:
        with open(sinal, encoding="utf-8") as fh:
            mudo = agora - float(fh.read().strip())
    except (OSError, ValueError):
        mudo = None
    if mudo is not None and mudo >= 0:
        # A mesma palavra do gancho de andamento: acima do teto do vigia o silencio
        # deixa de ser so um numero e passa a ter nome. E o nome depende de haver
        # trabalho vivo — sem essa distincao a barra chamava de SEM SINAL a suite
        # de 20 minutos que estava rodando normalmente.
        if mudo > LIMITE_SILENCIO:
            if _trabalho_vivo(base, sessao, agora):
                partes.append("⏳ rodando há %d min" % int(round(mudo / 60.0)))
            else:
                partes.append("🔇 SEM SINAL há %s" % _dur(mudo))
        else:
            partes.append("💬 último sinal há %s" % _dur(mudo))

    try:
        with open(_ler(base, "bloqueios-%s" % sessao), encoding="utf-8") as fh:
            n = int((fh.read().strip() or "0").split()[0])
    except (OSError, ValueError, IndexError):
        n = 0
    if n > 0:
        partes.append("⛔ %d bloqueio%s" % (n, "s" if n > 1 else ""))

    # O PLACAR DA ULTIMA ONDA, comparado com o da anterior (F9.27). Chega aqui pela
    # mesma regra do resto: lido do disco, nunca perguntado a ninguem.
    onda_linha = linha_placar(sessao, base)
    if onda_linha:
        partes.append("🧪 %s" % onda_linha)

    return "  │  ".join(partes)


def painel(dir_estado=None, agora=None):
    """O andamento AGORA de toda missao de pe, lido do disco — uma linha por sessao.

    A barra de status so fala da sessao em que ela esta desenhada, e `systemMessage`
    rola com a conversa: quem quer perguntar "e ai, como vai?" nao tinha onde olhar.
    Aqui a pergunta vira comando, e a resposta sai do MESMO estado que a barra le —
    `ativo-<sid>` e o que existe: sem ele nao ha missao, e nao ha o que imprimir.
    """
    bases = [dir_estado] if dir_estado else [ESTADO, ESTADO_LEGADO]
    sessoes = []
    for base in bases:
        try:
            nomes = sorted(os.listdir(base))
        except OSError:
            continue
        for nome in nomes:
            if nome.startswith("ativo-") and nome[6:] not in sessoes:
                sessoes.append(nome[6:])

    linhas = []
    for sessao in sessoes:
        linha = linha_motor(sessao, dir_estado, agora)
        if not linha:
            continue
        # A DOC DA ONDA SO CABE AQUI. Ela e o registro de S-111 — a prova de que a
        # doc do commit saiu da onda —, e ate agora nada a LIA: o registro existia
        # e nenhuma tela o mostrava, que e o mesmo defeito do placar de suite que o
        # motor descartava. Na barra nao cabe (ela ja tem seis pedacos); aqui, na
        # pergunta "como vai?", e exatamente o que se quer saber.
        docs = (ultima_doc(sessao, dir_estado) or {}).get("docs") or []
        if docs:
            linha += "  │  📄 doc da onda: %d" % len(docs)
        linhas.append("%s · %s" % (sessao, linha))
    return linhas


if __name__ == "__main__":
    import sys

    # `doc <sid> <rodada> <caminho...>` — o papel de doc registra o que confirmou.
    # `onda <sid> <rodada> [plano.json]` — quem executa diz em que volta esta.
    if len(sys.argv) > 3 and sys.argv[1] == "onda":
        reg = marca_onda(sys.argv[2], sys.argv[3],
                         sys.argv[4] if len(sys.argv) > 4 else None)
        print("onda registrada: %s" % json.dumps(reg, ensure_ascii=False))
        sys.exit(0)

    if len(sys.argv) > 3 and sys.argv[1] == "doc":
        gravados = doc_da_onda(sys.argv[2], sys.argv[3], sys.argv[4:])
        print("doc da onda registrada: %d caminho(s)" % len(gravados))
        sys.exit(0)

    saida = painel()
    print("\n".join(saida) if saida else "nenhuma missão de pé")
    sys.exit(0)
