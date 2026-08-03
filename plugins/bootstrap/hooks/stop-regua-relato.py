#!/usr/bin/env python3
"""Stop hook: a regua de estilo cobra o relato DIGITADO no terminal.

O canal do CLI era o unico fora do alcance da regua. Todo texto que passa por um
gerador (pagina, plano, slide, texto de hook) e medido antes de sair; o relato que
o modelo digita na resposta chegava ao dono sem passar por regua nenhuma — e e
justamente ele que o dono le em toda parada de turno.

DIVISAO DE TRABALHO com o stop-prose-ceiling.py, para nao haver guarda em dobro:
  teto de prosa  -> VOLUME (quantas linhas)
  esta regua     -> os BULLETS (as linhas que abrem com •, - ou *)

Perfil 'pagina', por derivacao e nao por escolha: o regua_texto.py define esse
perfil como «pagina, relatorio, diagnostico», e o relato de fim de turno e um
relatorio. NAO e o perfil 'hook' — aquele proibe ** e crase porque o canal do
emissor de hook nao renderiza markdown, e o canal do CLI renderiza.

Bloco de codigo e PROVA e fica fora, como no vizinho: saida crua e literal por
obrigacao e nao tem teto de caractere nem de frase.

FAIL-OPEN em tudo que for infra: regua ausente, payload ilegivel, transcript que
nao abre. Guarda que trava a sessao por infra e pior que guarda nenhum.

Bloqueia com exit 2. Trava anti-loop: 2 bloqueios por resposta.
Kill-switch: REGUA_RELATO=0.
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

MAX_BLOQUEIOS = 2
CLAUDE_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
# var propria de estado, no mesmo padrao do juiz vizinho: da pra isolar o teste sem
# mexer no CLAUDE_CONFIG_DIR real de quem roda.
ESTADO = Path(os.environ.get("REGUA_RELATO_STATE",
                             CLAUDE_DIR / "state" / "regua-relato"))

# A regua e vendorada em lib/ (ver scripts/sync-shared.sh) — a copia NUNCA se edita.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

# Linha que e bullet: marcador + espaco. O espaco exigido e o que separa "- item"
# de "**Gate verde**: ...", que abre com `*` e nao e lista.
_BULLET = re.compile(r"^([•\-*])\s+(.*)$")
# Sobra de regra horizontal ou de tabela depois de tirar o marcador — desenho, nao redacao.
_SO_TRACO = re.compile(r"^[-*_|\s]*$")


def sair(msg=None, codigo=0):
    if msg:
        print(msg, file=sys.stderr)
    sys.exit(codigo)


def batida(motivo, bullets=None, sid=""):
    """Registra TODA execucao, nao so as que barram — igual ao teto de prosa.

    Sem isto, 'a regua nao rodou' e 'a regua rodou e aprovou' sao indistinguiveis.
    """
    try:
        ESTADO.mkdir(parents=True, exist_ok=True)
        with (ESTADO / "batidas.log").open("a") as f:
            f.write(json.dumps({"ts": int(time.time()), "sessao": str(sid)[:8],
                                "motivo": motivo, "bullets": bullets}) + "\n")
    except OSError:
        pass  # fail-open: registro nunca trava a sessao


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
        c = msg.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            t = "\n".join(b.get("text", "") for b in c
                          if isinstance(b, dict) and b.get("type") == "text").strip()
            if t:
                return t
    return None


def bullets_do_texto(texto):
    """Os bullets autorais: tira a prova colada e devolve o texto sem o marcador."""
    sem_codigo = re.sub(r"```.*?```", "", texto, flags=re.S)
    achados = []
    for ln in sem_codigo.splitlines():
        m = _BULLET.match(ln.strip())
        if not m:
            continue
        corpo = m.group(2).strip()
        if corpo and not _SO_TRACO.match(corpo):
            achados.append(corpo)
    return achados


def main():
    if os.environ.get("REGUA_RELATO") == "0":
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

    itens = bullets_do_texto(texto)
    if not itens:
        batida("sem bullets", sid=sid)
        sair()

    try:
        from regua_texto import erros_de_estilo
    except ImportError:
        batida("regua ausente", bullets=len(itens), sid=sid)
        sair()  # fail-open: vendoring quebrado nao trava a sessao

    # UMA chamada com a LISTA inteira, nunca uma por bullet: a quarta checagem da
    # constituicao (quality-goals.md, "Maximo 6 bullets por bloco") so dispara
    # quando o valor chega como lista — `lista = isinstance(v, (list, tuple))` no
    # regua_texto.py. Bullet a bullet, 20 bullets curtos passavam limpos, e as
    # outras tres checagens saem iguais nos dois modos (so o rotulo muda).
    problemas = erros_de_estilo(itens, "relato", "pagina")

    if not problemas:
        batida("aprovou", bullets=len(itens), sid=sid)
        sair()

    batida("barrou", bullets=len(itens), sid=sid)

    # anti-loop, chaveado por sessao + hash da resposta inteira
    ESTADO.mkdir(parents=True, exist_ok=True)
    chave = hashlib.sha1((str(sid) + texto).encode()).hexdigest()[:16]
    contador = ESTADO / chave
    n = int(contador.read_text()) if contador.exists() else 0
    if n >= MAX_BLOQUEIOS:
        # Bloquear pra sempre trava a sessao, entao a regua desiste — mas nunca em
        # silencio: o registro e o que mostra quantas vezes a regua foi furada.
        with (ESTADO / "bypass.log").open("a") as f:
            f.write(json.dumps({"session": str(sid)[:8], "bullets": len(itens),
                                "problemas": problemas}, ensure_ascii=False) + "\n")
        sair()
    contador.write_text(str(n + 1))

    sair(
        "BULLETS REPROVADOS PELA REGUA:\n  " + "\n  ".join(problemas) + "\n\n"
        "Regime informacao rapida: bullet e uma frase que carrega um fato, nao paragrafo picado.\n"
        "Ate 140 caracteres, uma frase por bullet, no maximo 6 por bloco, sem abrir com conectivo.\n\n"
        "Assim um bullet passa:\n"
        "  - Gate verde pos-calibracao: typecheck limpo, unit 981, integracao 1427/0.\n\n"
        "Bloco de codigo e PROVA e fica fora da regua — corte a prosa, nunca a prova.\n"
        "O que nao couber vira /visual em HTML.\n"
        "Reescreva a resposta inteira; nao acrescente um resumo no fim.",
        2,
    )


if __name__ == "__main__":
    main()
