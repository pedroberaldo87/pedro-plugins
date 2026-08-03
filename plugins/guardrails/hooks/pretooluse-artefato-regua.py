#!/usr/bin/env python3
"""A PORTA da régua: nega escrever artefato de leitura que sai em prosa corrida.

Por que ao lado da REDE (`bootstrap/hooks/stop-regua-relato.py`), e não em vez
dela: os dois alcançam coisas diferentes e nenhum alcança as duas. A rede pega o
relatório que eu DIGITO no terminal e nunca vê arquivo; esta porta pega o arquivo
e nunca vê o terminal. O item F3.1 nomeia o caso do terminal, e o "Toca em" da
fase nomeia o contrato das skills que produzem artefato — ficar com um só
deixaria metade do requisito sem lastro.

Alcance deliberadamente estreito: `.md` e `.html` dentro de `.claude/visual/` ou
`.claude/reports/`. Documentação, código e config ficam de fora — a régua governa
artefato de LEITURA, não todo texto do repositório.

Fail-open em tudo que não é violação (sem régua vendorada, JSON estranho, caminho
fora do alcance): sai 0 mudo. Gate de forma que derruba a escrita por causa da
própria falha é pior que a prosa que ele evitaria.

Desliga: ARTEFATO_REGUA=0
"""
import importlib.util
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
REGUA = os.path.join(os.path.dirname(AQUI), "lib", "regua_texto.py")

DIRS = ("/.claude/visual/", "/.claude/reports/")
EXTS = (".md", ".html")
# Linha que abre com um destes não é redação: é comando, título, tabela, markup
# ou citação. Medir isso viraria ruído de sintaxe, não achado de prosa.
NAO_REDACAO = ("$", "#", "|", "<", "!", ">")


def alcanca(caminho):
    return caminho.endswith(EXTS) and any(d in caminho for d in DIRS)


def linhas_de_redacao(texto):
    """Só o que a régua deve medir: prosa fora de bloco de código.

    A constituição isenta prova literal, e prova mora em ``` — medir lá dentro
    reprovaria a saída crua que o artefato existe pra carregar.
    """
    out, cerca = [], False
    for ln in texto.splitlines():
        s = ln.strip()
        if s.startswith("```"):
            cerca = not cerca
            continue
        if cerca or not s or s.startswith(NAO_REDACAO):
            continue
        out.append(s.lstrip("-*• "))
    return out


def problemas_de(texto, caminho):
    if not os.path.exists(REGUA):
        return []
    # HTML emitido pelo visual_page.py já passou pela régua na origem.
    if caminho.endswith(".html") and "visual_page.py" in texto:
        return []
    linhas = linhas_de_redacao(texto)
    if not linhas:
        return []
    spec = importlib.util.spec_from_file_location("regua_texto", REGUA)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return []
    return mod.erros_de_estilo(linhas, "o artefato", "pagina")


def main():
    if os.environ.get("ARTEFATO_REGUA") == "0":
        return 0
    try:
        ev = json.load(sys.stdin)
    except Exception:
        return 0
    ti = ev.get("tool_input") or {}
    caminho = ti.get("file_path") or ""
    if not alcanca(caminho):
        return 0
    # Write manda o arquivo inteiro; Edit manda só o pedaço novo.
    texto = ti.get("content") or ti.get("new_string") or ""
    if not texto.strip():
        return 0

    probs = problemas_de(texto, caminho)
    if not probs:
        return 0

    sys.stderr.write(
        "⛔ artefato recusado pela régua de forma\n\n  "
        + "\n  ".join(probs[:6])
        + "\n\n📄 Quebre em bullets de uma frase, até 140 caracteres, sem abrir com\n"
          "   conectivo de continuação.\n"
          "📎 Saída crua vai dentro de bloco de código — lá a régua não entra,\n"
          "   porque prova é literal por obrigação.\n"
          "🔓 Escapar nesta sessão: ARTEFATO_REGUA=0\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
