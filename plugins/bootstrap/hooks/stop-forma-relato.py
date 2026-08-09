#!/usr/bin/env python3
"""Stop hook: um juiz barato avalia a FORMA do relato — o que regex nao alcanca.

Divisao de trabalho com o stop-prose-ceiling.py, que e vizinho e deliberadamente
diferente: aquele e mecanico, roda em todo turno e custa zero token; este chama um
modelo, entao SO roda quando a resposta e um RELATO. Nenhum padrao distingue
"6 linhas densas" de "6 linhas vazias" — para isso precisa de um leitor.

Julga quatro coisas, e so a FORMA:
  limpeza         · sobra frase que nao carrega fato?
  clareza         · da pra agir depois de ler uma vez?
  didatica        · explica em linguagem humana ou despeja jargao?
  escaneabilidade · o olho acha o resultado sem ler tudo?

QUANDO RODA (o gatilho, em duas partes):
  1. o turno passou pelo /visual — chamou a skill, o comando, ou escreveu a pagina.
     Sem isso nao julga nada: o juiz e do /visual, e nao de todo fim de turno.
     Medido em 9 dias com o gatilho antigo (todo relato): 463 julgamentos, ~25s cada,
     US$ 19,26 — cada `claude -p` recarrega o CLAUDE.md global so pra devolver 1 palavra.
  2. e a resposta e um RELATO: >= 2 linhas de prosa E um bloco de codigo (a prova colada).
Medido: um relato bom e CURTO — o exemplo canonico tem 2 linhas de prosa e 4 de
prova. Exigir 4 de prosa deixava passar exatamente os relatos que dao certo.
Resposta curta e conversa nao passam pelo juiz — sao a maioria dos turnos, e
mandar cada uma para um modelo custaria ~4,5s em cada uma delas.

FAIL-OPEN em tudo que nao for reprovacao explicita: sem `claude` no PATH, timeout,
saida ilegivel ou erro de rede => passa. Guarda que trava a sessao por infra e pior
que guarda nenhum.

TETO CONHECIDO, medido: com um CLAUDE_CONFIG_DIR que nao tem credencial, o `claude -p`
sai com rc=1 e "Not logged in", e o juiz cai no fail-open sem barrar nada. O motivo
fica na batida ("juiz sem resposta"), e o conformance le esse log — e assim que se
descobre que o juiz esta mudo em vez de aprovando.

Kill-switch: FORMA_RELATO=0.   Modelo: FORMA_RELATO_MODEL (default haiku).
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

MIN_PROSA = 2
MAX_BLOQUEIOS = 2
# o turno passou pelo /visual: chamou a skill, digitou o comando, ou escreveu a pagina
MARCA_VISUAL = re.compile(r'"skill"\s*:\s*"(?:[\w-]+:)?visual"'
                          r'|<command-name>/?visual\b'
                          r'|[\w./-]*\.claude/visual/')
# MEDIDO em 2026-08-05: `claude -p --model haiku` respondendo so "PASSA" levou 30s,
# 33s e 48s — o custo e a partida do CLI, nao o texto. Teto de 25s ficava ABAIXO do
# piso da ferramenta: o juiz estourava sempre e caia no fail-open, aprovando tudo.
TIMEOUT_S = 90
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
# estado com var propria: isolar o teste via CLAUDE_CONFIG_DIR tirava a credencial
# do `claude -p` junto, e o juiz passava a aprovar tudo por fail-open.
ESTADO = Path(os.environ.get("FORMA_RELATO_STATE",
                             CLAUDE_DIR / "state" / "forma-relato"))

PROMPT = """Voce julga a FORMA de um relato tecnico, nunca o conteudo. Seja severo:
na duvida entre PASSA e REPROVA, escolha REPROVA.

Quatro criterios:
1. LIMPEZA — toda linha carrega um fato novo? Frase que so prepara, justifica,
   contextualiza ou amortece REPROVA. Exemplos que reprovam: "deixa eu explicar",
   "vale notar", "em outras palavras", "dito isso", "espero que isso esclareca",
   "o processo foi complexo", "acredito que podemos seguir".
2. CLAREZA — da pra agir depois de ler UMA vez? Se o resultado so aparece no fim,
   ou nao aparece, REPROVA.
3. DIDATICA — explica em linguagem humana? Nome de funcao, nome de variavel e
   jargao no lugar da explicacao REPROVAM.
4. ESCANEABILIDADE — o olho acha o resultado sem ler tudo? Paragrafo unico e
   denso REPROVA; primeira linha que ja entrega o veredito passa.

Bloco de codigo e PROVA: nao conta como excesso, e a ausencia dele nao reprova.
Relato curto e bom sinal, nao defeito.

Responda UMA linha, exatamente num destes dois formatos:
PASSA
REPROVA: <o defeito em ate 12 palavras, no imperativo>

RELATO A JULGAR:
---
%s
---"""


def batida(motivo, veredito=None, sid=""):
    try:
        ESTADO.mkdir(parents=True, exist_ok=True)
        with (ESTADO / "batidas.log").open("a") as f:
            f.write(json.dumps({"ts": int(time.time()), "sessao": str(sid)[:8],
                                "motivo": motivo, "veredito": veredito}) + "\n")
    except OSError:
        pass


def sair(msg=None, codigo=0):
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(codigo)


def ultima_msg_assistente(transcript):
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
        c = msg.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            t = "\n".join(b.get("text", "") for b in c
                          if isinstance(b, dict) and b.get("type") == "text").strip()
            if t:
                return t
    return None


def usou_visual(transcript):
    """O juiz e do /visual: so julga o turno que rodou a skill ou escreveu a pagina."""
    try:
        linhas = Path(transcript).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return False
    for ln in reversed(linhas):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        if MARCA_VISUAL.search(ln):
            return True
        msg = d.get("message") or {}
        if msg.get("role") == "user" and isinstance(msg.get("content"), str):
            return False   # chegou no pedido humano sem passar pelo /visual
    return False


def e_relato(texto):
    """Prosa suficiente E prova colada. Os dois, senao nao e relato."""
    if "```" not in texto:
        return False
    sem_codigo = re.sub(r"```.*?```", "", texto, flags=re.S)
    prosa = [ln for ln in (x.strip() for x in sem_codigo.splitlines()) if ln]
    return len(prosa) >= MIN_PROSA


def julga(texto):
    """Devolve (passou, motivo). Qualquer problema de infra devolve (True, ...)."""
    exe = shutil.which("claude")
    if not exe:
        return True, "claude ausente no PATH"
    modelo = os.environ.get("FORMA_RELATO_MODEL", "haiku")
    # o filho herda os hooks deste marketplace e chamaria o juiz de novo; desliga
    # sem sujar o log — "interno" e desligamento silencioso, "0" e o kill-switch do dono
    ambiente = dict(os.environ, FORMA_RELATO="interno")
    try:
        r = subprocess.run([exe, "-p", "--model", modelo],
                           input=PROMPT % texto[:6000], env=ambiente,
                           capture_output=True, text=True, timeout=TIMEOUT_S, start_new_session=True)
    except (subprocess.TimeoutExpired, OSError) as e:
        return True, "juiz indisponivel: %s" % type(e).__name__
    saida = (r.stdout or "").strip()
    if r.returncode != 0 or not saida:
        return True, "juiz sem resposta (rc=%s)" % r.returncode
    primeira = saida.splitlines()[0].strip()
    if primeira.upper().startswith("REPROVA"):
        return False, primeira.split(":", 1)[-1].strip() or "forma reprovada"
    if primeira.upper().startswith("PASSA"):
        return True, "passa"
    return True, "veredito ilegivel: %s" % primeira[:60]   # fail-open


def main():
    modo = os.environ.get("FORMA_RELATO")
    if modo == "interno":      # subprocesso do proprio juiz: nem batida
        sair()
    if modo == "0":
        batida("kill-switch")
        sair()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        batida("payload ilegivel")
        sair()

    sid = payload.get("session_id", "")
    if payload.get("stop_hook_active"):
        batida("stop_hook_active", sid=sid)
        sair()

    transcript = payload.get("transcript_path", "")
    if not usou_visual(transcript):
        batida("sem /visual no turno", sid=sid)
        sair()

    texto = ultima_msg_assistente(transcript)
    if not texto:
        batida("sem texto", sid=sid)
        sair()
    if not e_relato(texto):
        batida("nao e relato", sid=sid)
        sair()

    # anti-loop antes de gastar o modelo: 2 tentativas por resposta e acabou
    ESTADO.mkdir(parents=True, exist_ok=True)
    chave = hashlib.sha1((str(sid) + texto).encode()).hexdigest()[:16]
    contador = ESTADO / chave
    n = int(contador.read_text()) if contador.exists() else 0
    if n >= MAX_BLOQUEIOS:
        batida("desistiu", sid=sid)
        sair()

    passou, motivo = julga(texto)
    # so e "julgou" quando o modelo respondeu: aprovacao por timeout, erro ou
    # veredito ilegivel entra como "fail-open" — gate que nao mediu diz que nao mediu
    julgou = (not passou) or motivo == "passa"
    batida("julgou" if julgou else "fail-open", veredito=motivo, sid=sid)
    if passou:
        sair()

    contador.write_text(str(n + 1))
    sair("FORMA DO RELATO REPROVADA: %s\n\n"
         "Reescreva o relato inteiro. Nao acrescente um resumo no fim.\n"
         "Abra pelo resultado; cada linha carrega um fato; a prova vai em bloco de codigo.\n"
         "O que nao couber vira /visual em HTML." % motivo, 2)


if __name__ == "__main__":
    main()
