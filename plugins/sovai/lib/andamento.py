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

ESTADO = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR",
                                     os.path.join(os.path.expanduser("~"), ".claude")),
                      "sovai")

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
            with open(caminho, encoding="utf-8") as fh:
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
        with open(_arquivo(projeto), encoding="utf-8") as fh:
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


def avanco(anterior, atual):
    """Andou, nao andou, ou piorou — comparando dois placares.

    'nao andou' e o sinal que interessa: duas rodadas com o MESMO placar querem
    dizer que a suite parou de mudar, e e ai que vale olhar.
    """
    if atual is None:
        return "sem placar"
    if anterior is None:
        return "primeiro placar"
    if atual["passou"] > anterior["passou"]:
        return "avancou"
    if atual["passou"] < anterior["passou"]:
        return "regrediu"
    if (atual["falhou"] or 0) < (anterior["falhou"] or 0):
        return "avancou"
    return "sem avanco"


def _dur(segundos):
    s = int(round(segundos))
    return "%ds" % s if s < 90 else "%dmin%02ds" % (s // 60, s % 60)


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
        return "rodando ha %d min — trabalho vivo, nao e travamento" % minutos
    return "travamento: nada mudou ha %d min e nao ha trabalho vivo" % minutos


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
        with open(_arquivo(projeto), encoding="utf-8") as fh:
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
    partes = ["rodando ha %s" % _dur(decorrido)]
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
