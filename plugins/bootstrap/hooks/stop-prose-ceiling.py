#!/usr/bin/env python3
"""Stop hook: barra prosa acima do teto, retorica no meio e menu de opcoes.

Vale quando o modelo "esquece" a regra — e a diferenca entre regra (ponderavel)
e mecanismo. TETO CONHECIDO, medido por auditoria independente em 2026-07-30:
como todo hook de plugin, so carrega no SessionStart, entao sessao ja aberta
no momento da instalacao fica descoberta ate o proximo /clear.

Sempre ligadas: teto de prosa, retorica no meio e menu de opcoes no fim.

O TETO E PREMISSA DO REPO, nao preferencia configuravel. Ele NASCE LIGADO em
TETO_PADRAO. PROSE_CEILING_MAX so AJUSTA o numero; nao existe valor que desligue
(0 ou lixo cai no padrao).

Historico, para nao reincidir: em 2026-07-30 este teto foi transformado em opt-in
sob o argumento "e preferencia do dono, nao regra universal". A variavel nunca foi
definida, entao o guarda ficou inerte e a primeira resposta seguinte ja estourou.
Premissa que nasce desligada nao e premissa — e comentario.

Conta linhas de PROSA da ultima mensagem do assistente e nao conta:
  - bloco de codigo (``` ... ```), que e PROVA e nao tem teto
  - linha em branco
Bloqueia com exit 2. Trava anti-loop: 2 bloqueios por turno.

Kill-switch de emergencia (unico): PROSE_CEILING=0 desliga o hook inteiro.
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

# PREMISSA: nasce ligado. A env var so ajusta o numero, nunca desliga o teto —
# desligar exige PROSE_CEILING=0, que derruba o hook inteiro e e visivel.
TETO_PADRAO = 6
_TETO_ENV = os.environ.get("PROSE_CEILING_MAX", "").strip()
TETO = int(_TETO_ENV) if (_TETO_ENV.isdigit() and int(_TETO_ENV) > 0) else TETO_PADRAO
MAX_BLOQUEIOS = 2
# MESMA regra do lib/conformance.py:CLAUDE_DIR. Com Path.home() fixo aqui, quem usa
# CLAUDE_CONFIG_DIR fazia o hook escrever num lugar e o verificador ler noutro — e o
# relatorio dizia "nenhuma resposta furou o teto" com o teto furado. Falha silenciosa.
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
ESTADO = CLAUDE_DIR / "state" / "prose-ceiling"


def sair(msg=None, codigo=0):
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(codigo)


def ultima_msg_assistente(transcript):
    """Le o .jsonl do transcript de tras pra frente ate achar texto do assistente."""
    try:
        linhas = Path(transcript).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for ln in reversed(linhas):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        msg = d.get("message") or {}
        if msg.get("role") != "assistant":
            continue
        conteudo = msg.get("content")
        if isinstance(conteudo, str):
            return conteudo
        if isinstance(conteudo, list):
            partes = [b.get("text", "") for b in conteudo
                      if isinstance(b, dict) and b.get("type") == "text"]
            texto = "\n".join(partes).strip()
            if texto:
                return texto
    return None


def ultima_pergunta_usuario(transcript):
    """A ultima coisa que o usuario escreveu, ou None. Le de tras pra frente."""
    try:
        linhas = Path(transcript).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for ln in reversed(linhas):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        msg = d.get("message") or {}
        if msg.get("role") != "user":
            continue
        c = msg.get("content")
        if isinstance(c, str):
            texto = c
        elif isinstance(c, list):
            texto = "\n".join(b.get("text", "") for b in c
                              if isinstance(b, dict) and b.get("type") == "text")
        else:
            continue
        texto = texto.strip()
        # resultado de ferramenta e lembrete do sistema entram como 'user' e nao sao pergunta
        if texto and "<system-reminder>" not in texto and not texto.startswith("<"):
            return texto
    return None


# Pergunta FECHADA: espera veredito, nao dissertacao. Casada no fim do texto do usuario.
PERGUNTA_FECHADA = re.compile(
    r"(?:^|[\s,])(voce |vc |ja |ta |esta |tem |da |consegue |confirma|garante|passou|"
    r"rodou|funciona|resolveu|terminou|fechou|pode|vale|preciso saber)"
    r"[^?]{0,120}\?\s*$", re.I)

# Pronome interrogativo abre pergunta ABERTA — "como faz pra funcionar?" pede
# explicacao, nao sim/nao. Sem esta exclusao o guarda cobrava veredito de tudo.
PERGUNTA_ABERTA = re.compile(
    r"(?:^|[.?!]\s+)\W*(como|por ?que|pq|o que|que |qual|quais|quando|onde|quem|"
    r"quanto|de que|em que|explica|descreve|me diz como)\b", re.I)

# Abertura que responde: veredito nas primeiras palavras. Negacao/afirmacao direta,
# ou o rotulo de prova que o output style ja exige.
ABRE_COM_VEREDITO = re.compile(
    r"^\W*(?:\*\*)?\s*(sim|nao|não|confirmo|nenhum|nenhuma|zero|passou|falhou|"
    r"funciona|resolvido|pronto|feito|em parte|parcial|ainda nao|ainda não|"
    r"confirmado|inferido|depende)\b", re.I)


def linhas_de_prosa(texto):
    """Tira bloco de codigo (prova, sem teto) e conta o que sobra."""
    sem_codigo = re.sub(r"```.*?```", "", texto, flags=re.S)
    sem_codigo = re.sub(r"^\s*(?:\||\+?-{3,})[^\n]*$", "", sem_codigo, flags=re.M)
    return [ln for ln in (x.strip() for x in sem_codigo.splitlines()) if ln]


def batida(motivo, linhas=None, sid=""):
    """Registra TODA execucao, nao so as que barram.

    Sem isto, 'o guarda nao rodou' e 'o guarda rodou e aprovou' sao indistinguiveis
    — e foi exatamente esse cegueira que deixou passar uma resposta de 9 linhas em
    2026-07-31 09:21 sem ninguem notar: o disco so tinha registro de bloqueio, e o
    primeiro era de 09:36. Uma linha por execucao, append, barata.
    """
    try:
        ESTADO.mkdir(parents=True, exist_ok=True)
        with (ESTADO / "batidas.log").open("a") as f:
            f.write(json.dumps({
                "ts": int(time.time()), "sessao": str(sid)[:8],
                "motivo": motivo, "linhas": linhas, "teto": TETO,
            }) + "\n")
    except OSError:
        pass  # fail-open: registro nunca trava a sessao


def main():
    if os.environ.get("PROSE_CEILING") == "0":
        batida("kill-switch")
        sair()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        batida("payload ilegivel")
        sair()  # fail-open: hook quebrado nunca trava a sessao

    sid = payload.get("session_id", "")
    if payload.get("stop_hook_active"):
        batida("stop_hook_active", sid=sid)
        sair()

    texto = ultima_msg_assistente(payload.get("transcript_path", ""))
    if not texto:
        batida("sem texto do assistente", sid=sid)
        sair()

    prosa = linhas_de_prosa(texto)
    problemas = []
    if len(prosa) > TETO:
        problemas.append(f"{len(prosa)} linhas de prosa, o teto e {TETO}")

    # Padroes nomeados na calibracao. Medido: tamanho e 1a linha NAO separam aprovada de
    # rejeitada (71 x 154 amostras, diferenca ~0). A reclamacao real e destes:
    RETORICA = re.compile(
        r"(vale (?:notar|lembrar|ressaltar)|importante (?:notar|destacar)|"
        r"cabe destacar|dito isso|em outras palavras|ou seja[,]|"
        r"o que eu fiz foi|deixa eu (?:explicar|contextualizar)|"
        r"antes de (?:mais nada|continuar)|para (?:contextualizar|ficar claro)|"
        r"como (?:eu )?(?:mencionei|falei|expliquei|disse) (?:antes|acima|anteriormente))",
        re.I)
    achado = RETORICA.search(texto)
    if achado:
        problemas.append(f"retorica no meio: {achado.group(0)!r}")

    # menu de opcoes no fim = devolver a decisao em vez de decidir
    if re.search(r"^\s*(?:[-*]|\d[.)])\s*(?:op[çc][ãa]o|alternativa)\s*[ABC1-3]?\b",
                 texto, re.I | re.M):
        problemas.append("menu de opcoes — decida e diga qual escolheu")

    # pergunta fechada exige veredito na PRIMEIRA linha. Nasceu de um caso real:
    # a resposta trouxe a varredura inteira, com prova, e nao dizia sim nem nao —
    # e a devolutiva foi "voce nao me respondeu".
    pergunta = ultima_pergunta_usuario(payload.get("transcript_path", ""))
    cauda = pergunta[-200:] if pergunta else ""
    if pergunta and PERGUNTA_FECHADA.search(cauda) and not PERGUNTA_ABERTA.search(cauda):
        primeira = next((ln for ln in texto.splitlines() if ln.strip()), "")
        if not ABRE_COM_VEREDITO.match(primeira.strip()):
            problemas.append("pergunta fechada sem veredito na 1a linha")

    if not problemas:
        batida("aprovou", linhas=len(prosa), sid=sid)
        sair()

    batida("barrou", linhas=len(prosa), sid=sid)

    # anti-loop, chaveado por sessao + hash da mensagem
    ESTADO.mkdir(parents=True, exist_ok=True)
    # hash do texto INTEIRO: com texto[:200] duas respostas diferentes que comecam
    # igual dividiam o mesmo orcamento — e o output style manda a 1a linha ser
    # estavel, entao a colisao era o caso comum, nao a excecao.
    chave = hashlib.sha1(
        (str(payload.get("session_id", "")) + texto).encode()
    ).hexdigest()[:16]
    contador = ESTADO / chave
    n = int(contador.read_text()) if contador.exists() else 0
    if n >= MAX_BLOQUEIOS:
        # Teto conhecido: bloquear pra sempre trava a sessao, entao o hook desiste.
        # O que NAO pode acontecer e desistir em silencio — o conformance le este log
        # e mostra quantas vezes o teto foi furado.
        with (ESTADO / "bypass.log").open("a") as f:
            f.write(json.dumps({
                "session": str(payload.get("session_id", ""))[:8],
                "linhas_prosa": len(prosa),
                "problemas": problemas,
                "trecho": prosa[0][:120] if prosa else "",
            }, ensure_ascii=False) + "\n")
        sair()
    contador.write_text(str(n + 1))

    sair(
        "PROSA REPROVADA: " + " | ".join(problemas) + "\n\n"
        "TESTE: apague cada linha e veja se quem le perde informacao.\n"
        "Se nao perde, a linha sai. Linha que so prepara, justifica ou amortece nasce cortada.\n\n"
        "Assim uma resposta passa:\n"
        "  Gate verde pos-calibracao: typecheck limpo · unit 981 · integracao 1427/0.\n"
        "  Pronto e testado, nao commitado. Mantenho janela_dias = 30 ou troco pra 15?\n\n"
        "Bloco de codigo e PROVA e nao conta no teto — corte a prosa, nunca a prova.\n"
        "O que nao couber vira /visual em HTML.\n"
        "Reescreva a resposta inteira; nao acrescente um resumo no fim.",
        2,
    )


if __name__ == "__main__":
    main()
