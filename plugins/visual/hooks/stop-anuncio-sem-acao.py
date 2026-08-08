#!/usr/bin/env python3
"""Stop hook: o turno que ANUNCIA o proximo passo e acaba ali e devolvido.

O DEFEITO, medido por um agente externo em 2026-08-02 e reproduzido nos transcripts
dele: escrever a frase que anuncia a proxima fase e o que CONSOME a proxima fase. O
anuncio ocupa o lugar da acao — declarada a intencao em prosa, o turno fecha como
"comunicacao completa" e a chamada de ferramenta que deveria vir nao vem.

    COM anuncio escrito da proxima etapa   n =  2   parou = 2   (100%)
    SEM anuncio                            n = 42   parou = 0   (  0%)

O CONTROLE que define o gatilho: as ~12 pausas DENTRO de uma fase ("Agora ligo a
contagem...") terminaram todas em chamada de ferramenta. Legenda seguida de acao no
mesmo turno nao para. O que mata e o anuncio SOZINHO.

POR QUE O SINAL NAO E "o turno nao chamou ferramenta": no `Stop` isso e trivialmente
verdade — o evento dispara justamente porque a ultima mensagem foi texto. No caso real
o tique ACONTECEU (`plano 5/41`) e so DEPOIS veio o "Sigo para F2". O sinal util e o
texto final prometer trabalho que o plano ainda registra como aberto.

TRES CONDICOES, todas necessarias:
  1. ha plano ativo com passo em aberto     — sem trabalho pendente nao ha o que cobrar
  2. o texto final promete continuar        — em 1a pessoa, nao "o proximo passo e X"
  3. o texto NAO espera o usuario           — pergunta e pedido de aval desarmam

CONTRATO DE GATE (.claude/docs/patterns.md → §5.3):
  canal      decision:block (devolve o turno; o harness tem cap nativo)
  cap        2 devolucoes por (sessao, projeto), depois desiste
  desligar   ANUNCIO_ACAO=0
  fail-open  sem transcript, sem python3 no plano, payload torto → sai calado

TETO CONHECIDO: a deteccao e lexical, entao promessa escrita fora dos padroes abaixo
passa batido. Preferi o falso NEGATIVO — devolver turno legitimo custa mais caro que
deixar um anuncio escapar. Toda vez que arma fica uma linha em `batidas.log`; e por ela
que se mede se a lista de padroes esta larga ou estreita demais.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

MAX_DEVOLUCOES = 2
# So o fim do texto interessa: o anuncio e a ultima coisa que o agente escreve, e
# varrer o relato inteiro faria qualquer mencao a trabalho futuro armar o gate.
CAUDA_CHARS = 500

AQUI = Path(__file__).resolve().parent
PLAN_STATE = AQUI.parent / "lib" / "plan_state.py"
RESOLVE_DIR = AQUI.parent / "skills" / "visual" / "resolve-dir.sh"
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
ESTADO = Path(os.environ.get("ANUNCIO_ACAO_STATE", CLAUDE_DIR / "state" / "anuncio-acao"))

# PROMESSA — 1a pessoa, intencao de agir. "o proximo passo e X" descreve e nao entra:
# relatorio que LISTA o que falta e o comportamento certo, nao o defeito.
PROMESSA = re.compile(
    r"\b("
    r"sigo\s+(para|pro|pra|com|adiante|agora|em\s+frente)"
    r"|seguimos\s+(para|pro|pra|com)"
    r"|sigo\s*[.!]"
    r"|vou\s+(para|pro|pra|seguir|comecar|começar|iniciar|partir|atacar|rodar"
    r"|implementar|fazer|executar|abrir|montar|escrever|aplicar|continuar)"
    r"|parto\s+(para|pro|pra)"
    r"|passo\s+(para|pro|pra)\s+(a|o|as|os)\b"
    r"|continuo\s+(com|para|pro|pra|na|no)"
    r"|prossigo\s+(com|para|pro|pra)"
    r"|em\s+seguida[,\s]+(vou|faço|faco|sigo|rodo|abro)"
    r"|agora\s+(vou|sigo|parto|passo\s+para)"
    r"|na\s+sequência[,\s]+(vou|sigo)"
    r"|na\s+sequencia[,\s]+(vou|sigo)"
    r")\b",
    re.IGNORECASE)

# ESPERA — o agente devolveu a bola ao usuario. Turno que pede aval nao e turno que
# fugiu do trabalho: devolve-lo seria atropelar a decisao que ele foi buscar.
ESPERA = re.compile(
    r"\b("
    r"confirma|confirme|me\s+diga|me\s+diz|aguardo|qual\s+(deles|dos|opção|opcao|caminho)"
    r"|quer\s+que\s+eu|posso\s+(seguir|prosseguir|continuar|aplicar|commitar|rodar)"
    r"|você\s+(decide|escolhe|prefere)|sua\s+(decisão|decisao|ordem|escolha)"
    r"|aprova|aprovar\?|falta\s+(você|decidir)|assim\s+que\s+você"
    r"|se\s+(você\s+)?(quiser|preferir|mandar)|quando\s+você\s+mandar"
    r")\b",
    re.IGNORECASE)


def batida(motivo, sid="", extra=None):
    """Toda passagem vira linha. Gate que arma em silencio nao se audita depois."""
    try:
        ESTADO.mkdir(parents=True, exist_ok=True)
        with (ESTADO / "batidas.log").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": int(time.time()), "sessao": str(sid)[:8],
                                 "motivo": motivo, "trecho": extra},
                                ensure_ascii=False) + "\n")
    except OSError:
        pass


def ultimo_texto(transcript):
    """O texto da ultima mensagem do assistente. Sidechain (subagente) nao conta."""
    try:
        linhas = Path(transcript).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return None
    for ln in reversed(linhas):
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(rec, dict) or rec.get("isSidechain"):
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        c = msg.get("content")
        if isinstance(c, str):
            return c.strip() or None
        if isinstance(c, list):
            t = "\n".join(b.get("text", "") for b in c
                          if isinstance(b, dict) and b.get("type") == "text").strip()
            if t:
                return t
    return None


def planos_abertos(cwd):
    """Os planos ativos com passo em aberto. Lista vazia desarma o gate.

    Devolve (planos, de_reserva). `de_reserva` sai do CODIGO DE SAIDA 3 do
    resolve-dir.sh — o stderr dele e capturado e descartado aqui, entao o texto
    do aviso nao chegaria a lugar nenhum; o `returncode` chega, e daqui ele vai
    para o `reason` do bloqueio, que e o que o modelo le.
    """
    if not PLAN_STATE.is_file() or not RESOLVE_DIR.is_file():
        return [], False
    try:
        r = subprocess.run(["bash", str(RESOLVE_DIR), cwd, "plans"],
                           capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        plans_dir = (r.stdout or "").strip()
        de_reserva = r.returncode == 3
    except (subprocess.SubprocessError, OSError):
        return [], False
    if not plans_dir or not os.path.isdir(plans_dir):
        return [], de_reserva
    try:
        r = subprocess.run([sys.executable, str(PLAN_STATE), "--dir", plans_dir,
                            "open", "--json"], capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL, start_new_session=True)
        abertos = json.loads((r.stdout or "").strip() or "[]")
    except (subprocess.SubprocessError, OSError, ValueError):
        return [], de_reserva
    if not isinstance(abertos, list):
        return [], de_reserva
    return ([p for p in abertos
             if isinstance(p, dict) and (p.get("total", 0) - p.get("done", 0)) > 0],
            de_reserva)


def main():
    if os.environ.get("ANUNCIO_ACAO") == "0":
        batida("kill-switch")
        sys.exit(0)
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        sys.exit(0)

    sid = payload.get("session_id", "")
    # `stop_hook_active` NAO cala este gate. O campo e do EVENTO, nao deste hook: basta
    # QUALQUER hook de Stop ter devolvido o turno (o `delivery-audit.sh` do intent-guard
    # devolve) pra ele chegar `true` aqui — e ai este gate saia sem nem ler o texto.
    # Foi o que aconteceu: uma sessao inteira sem julgar uma frase, calado pelo vizinho.
    # O laco quem impede e o cap proprio, por (sessao, projeto), que ja existe abaixo —
    # esse conta as devolucoes DESTE gate, que e o que a protecao anti-laco precisa.
    if payload.get("stop_hook_active"):
        batida("stop_hook_active — julga assim mesmo", sid)

    texto = ultimo_texto(payload.get("transcript_path", ""))
    if not texto:
        sys.exit(0)

    cauda = texto[-CAUDA_CHARS:]
    if not PROMESSA.search(cauda):
        sys.exit(0)                       # o caso comum: sai calado, custo zero
    if ESPERA.search(cauda) or cauda.rstrip().endswith("?"):
        batida("espera o usuario", sid)
        sys.exit(0)

    abertos, de_reserva = planos_abertos(payload.get("cwd") or os.getcwd())
    if not abertos:
        batida("sem plano aberto", sid)
        sys.exit(0)

    # Cap por (sessao, projeto): o harness ja tem o dele, este existe pra desistir
    # ANTES, e pra desistir em silencio nunca — a batida diz que desistiu.
    # `hash()` de str e randomizado por processo (PYTHONHASHSEED): a chave mudaria a
    # cada turno e o cap nunca contaria. Digest estavel, como o resto do repo faz.
    ESTADO.mkdir(parents=True, exist_ok=True)
    phash = hashlib.sha1((payload.get("cwd") or "").encode("utf-8")).hexdigest()[:12]
    chave = ESTADO / ("n-%s-%s" % (str(sid)[:16] or "sem-sessao", phash))
    try:
        n = int(chave.read_text())
    except (OSError, ValueError):
        n = 0
    if n >= MAX_DEVOLUCOES:
        batida("desistiu", sid)
        sys.exit(0)
    try:
        chave.write_text(str(n + 1))
    except OSError:
        pass

    p = abertos[0]
    falta = p.get("total", 0) - p.get("done", 0)
    proxima = (p.get("next") or {}).get("id") or "o próximo passo"
    trecho = " ".join(cauda.split())[-160:]
    batida("devolveu", sid, trecho)

    reserva = ("\n\n⚠️ Este plano veio da RESERVA, nao deste diretorio: \"%s\" nao tem "
               "marcador de projeto. Confirme com o usuario que e o plano certo."
               % (payload.get("cwd") or os.getcwd())) if de_reserva else ""

    print(json.dumps({"decision": "block", "reason": (
        "VOCÊ ANUNCIOU E NÃO EXECUTOU.\n\n"
        "O turno terminou prometendo continuar, e a ação não veio. Isso não é um "
        "detalhe de estilo: medido em 2026-08-02, todos os turnos que fecharam com "
        "anúncio da próxima etapa pararam ali (2 de 2), contra nenhum dos 42 que "
        "fecharam sem anúncio.\n\n"
        "O que você escreveu no fim: \"…%s\"\n"
        "O plano \"%s\" tem %d passo(s) em aberto; o próximo é %s.%s\n\n"
        "Execute agora, neste mesmo turno. O relatório de fechamento sai SEM frase "
        "de transição — a primeira ação da etapa seguinte vai junto dele.\n"
        "Se você precisa de uma decisão do usuário, pergunte de forma explícita em "
        "vez de anunciar." % (trecho, p.get("title", p.get("id", "")), falta, proxima,
                              reserva)
    )}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
