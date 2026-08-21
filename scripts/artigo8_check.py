#!/usr/bin/env python3
"""artigo8_check.py — o cobrador do Artigo 8: o comando da skill roda COMO ESTÁ ESCRITO.

Por que existe
--------------
O Artigo 8 era o único sem cobrador — e o com mais violações. A exigência dele é
simples: todo comando dentro de um `SKILL.md` tem que rodar a partir da pasta do
projeto de QUEM INSTALOU, sem o agente adivinhar nada. Três padrões quebram isso:

  A1-caminho-local   `plugins/<x>/lib/…` — caminho que só existe NESTE repositório
  A2-placeholder     `<algo>` que o próprio arquivo nunca define
  A3-variavel-vazia  `$VAR` que ninguém deriva no bloco (a raiz do plugin chega
                     vazia quando o agente roda o comando por conta própria, e o
                     comando vira `python3 /lib/plan_state.py` — arquivo nenhum)

O que conta como comando: bloco cercado ```bash/```sh/```shell E a crase em linha
de prosa (`python3 …`) — que é a forma DOMINANTE de comando nas skills deste repo.
Crase só vira comando quando começa com um executável de terminal; `nome-do-plugin`
e `plugin.json` continuam sendo prosa.

⚠️ Isto é grep, não verdade: cada achado diz ONDE OLHAR. Por isso a saída carrega
sempre arquivo:linha e a linha literal.

Reprova só o que PIORA contra o retrato — a dívida antiga passa, o padrão NOVO
barra. Mesma disciplina do contrato dos hooks.

Isenção: `artigo8-ok: <motivo>` na linha (ou dentro de um comentário `#` dela).

Uso
---
  python3 scripts/artigo8_check.py            # relatório humano e REGRAVA o retrato
  python3 scripts/artigo8_check.py --check    # compara com o retrato, sai 1 se piorou
  python3 scripts/artigo8_check.py --json     # a medida crua

O retrato é catraca de DUAS mãos: `--check` reprova o achado novo e, quando nada
piorou mas alguma dívida foi consertada, ABAIXA o retrato sozinho — senão o texto
reintroduzido depois voltaria a passar de graça.

Só stdlib.
"""

import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(RAIZ, ".claude", "artigo8.baseline.json")

ISENCAO = re.compile(r"artigo8-ok:\s*\S")
# Bloco de comando: só ``` bash / ```sh / ```shell. ```python e ```json não são
# comando pra rodar no terminal de quem instalou.
ABRE = re.compile(r"^\s*```(bash|sh|shell)\s*$")
FECHA = re.compile(r"^\s*```\s*$")

# Crase em linha de prosa: `…`. Só vira comando quando ABRE com um executável de
# terminal — `plugin.json` e `nome-do-plugin` são prosa, não comando.
RE_INLINE = re.compile(r"`([^`\n]+)`")
RE_VERBO = re.compile(
    r"^\s*(?:sudo\s+|env\s+)?(?:python3?|bash|sh|zsh|node|npm|npx|git|claude|curl|wget"
    r"|grep|rg|sed|awk|cat|head|tail|ls|find|jq|chmod|mkdir|cp|mv|rm|touch|open|make"
    r"|pytest|ruff|pip3?|export|source|\./[\w./-]+)\b")

RE_CAMINHO_LOCAL = re.compile(r"(?<![\w/.-])plugins/[\w.-]+/")
# Placeholder: `<algo>`. Fora: redirecionamento (`< arq`, `<<EOF`), comparação
# (`<=`), tag HTML e seta (`<-`). Só conta o que começa com letra.
RE_PLACEHOLDER = re.compile(r"<([a-zA-Z][\w .|-]*)>")
RE_VAR = re.compile(r"\$\{?([A-Z][A-Z0-9_]*)\}?")

# Variáveis que o terminal de QUALQUER máquina já tem — usá-las não é adivinhar.
VARS_DO_AMBIENTE = {
    "HOME", "PWD", "OLDPWD", "PATH", "USER", "SHELL", "TMPDIR", "TMP", "TEMP",
    "EDITOR", "LANG", "PS1", "RANDOM", "PYTHONPATH", "USERPROFILE", "APPDATA",
}
# Atribuição no PRÓPRIO bloco: `X=…`, `export X=…`, `read X`, `for X in`.
# re.M porque o bloco é julgado como texto de VÁRIAS linhas: sem ele, `^` só casava no
# começo do bloco inteiro e toda variável derivada da segunda linha em diante era acusada
# de vazia — o falso-positivo que fechou a porta de commit em 21/08.
RE_ATRIBUI = re.compile(
    r"(?:^|[;&|]|\bexport\s+|\bfor\s+|\bread\s+|\blocal\s+)\s*([A-Z][A-Z0-9_]*)\s*(?:=|\bin\b)",
    re.M)


def skills(root):
    """Todo .md executável por agente: SKILL.md, os references/ e os .md vendorados
    na pasta da skill — a varredura é do repo, não de uma lista. O alcance cresceu
    em 2026-08-21 (achado do pente fino): comando quebrado em references/ e em cópia
    vendorada quebra igual, e ficava fora do retrato."""
    vistos = set()
    tudo = (glob.glob(os.path.join(root, "plugins", "*", "skills", "*", "SKILL.md")) +
            glob.glob(os.path.join(root, "skills", "*", "SKILL.md")) +
            glob.glob(os.path.join(root, "plugins", "*", "skills", "*", "references", "*.md")) +
            glob.glob(os.path.join(root, "plugins", "*", "skills", "*", "*.md")))
    return sorted(f for f in tudo if not (f in vistos or vistos.add(f)))


def blocos(linhas):
    """Os blocos de comando de um arquivo: [(linha_inicial, [linhas do corpo])]."""
    out, corpo, ini = [], None, 0
    for i, ln in enumerate(linhas, 1):
        if corpo is None:
            if ABRE.match(ln):
                corpo, ini = [], i + 1
            continue
        if FECHA.match(ln):
            out.append((ini, corpo))
            corpo = None
            continue
        corpo.append(ln)
    return out


def inline(linhas, dentro):
    """Os comandos em crase de prosa: [(linha, trecho)] — fora dos blocos cercados."""
    out = []
    for i, ln in enumerate(linhas, 1):
        if i in dentro:
            continue
        for trecho in RE_INLINE.findall(ln):
            if RE_VERBO.match(trecho):
                out.append((i, trecho))
    return out


def define_no_arquivo(texto_fora, nome):
    """O arquivo define o placeholder? Basta ele aparecer FORA do bloco de comando
    — é lá que a prosa da skill diz o que pôr no lugar."""
    return ("<%s>" % nome) in texto_fora


def julga(caminho, src, rel):
    linhas = src.splitlines()
    achados = []
    dentro = set()
    for ini, corpo in blocos(linhas):
        for k in range(len(corpo)):
            dentro.add(ini + k)
    # A prosa que DEFINE o placeholder não pode ser o próprio comando em crase.
    def sem_comando(ln):
        return RE_INLINE.sub(lambda m: " " if RE_VERBO.match(m.group(1)) else m.group(0), ln)
    fora = "\n".join(sem_comando(ln)
                     for i, ln in enumerate(linhas, 1) if i not in dentro)

    # (linha, texto julgado, variáveis atribuídas ali, linha inteira p/ a isenção)
    trechos = [(ini + k, ln, set(RE_ATRIBUI.findall("\n".join(corpo))), ln)
               for ini, corpo in blocos(linhas) for k, ln in enumerate(corpo)]
    trechos += [(n, t, set(RE_ATRIBUI.findall(t)), linhas[n - 1])
                for n, t in inline(linhas, dentro)]
    trechos.sort(key=lambda t: t[0])

    for n, ln, atribuidas, inteira in trechos:
        if ISENCAO.search(inteira):
            continue
        crua = ln.strip()
        if crua.startswith("#") or not crua:
            continue

        def achado(regra, msg):
            achados.append(dict(rule=regra, who=rel, line=n, msg=msg, quote=crua[:140]))

        m = RE_CAMINHO_LOCAL.search(ln)
        if m:
            achado("A1-caminho-local",
                   "caminho `%s…` só existe neste repositório — na máquina de quem "
                   "instala o plugin mora no cache do harness" % m.group(0))
        for ph in RE_PLACEHOLDER.findall(ln):
            if not define_no_arquivo(fora, ph):
                achado("A2-placeholder-orfao",
                       "placeholder <%s> não é definido em lugar nenhum do arquivo — "
                       "o agente teria que adivinhar" % ph)
        for var in RE_VAR.findall(ln):
            if var in VARS_DO_AMBIENTE or var in atribuidas:
                continue
            achado("A3-variavel-vazia",
                   "$%s não é derivada no bloco e não vem do ambiente — chega vazia e "
                   "o comando roda contra caminho errado" % var)
    return achados


def varre(root=None):
    root = root or RAIZ   # lido na hora: a suíte troca a raiz para varrer um repo de mentira
    achados = []
    for caminho in skills(root):
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        # relpath com barra POSIX: o `who` entra na CHAVE do retrato, e chave com o
        # separador do sistema fez os achados antigos virarem "novos" no Windows.
        achados += julga(caminho, src,
                         os.path.relpath(caminho, root).replace(os.sep, "/"))
    achados.sort(key=lambda f: (f["who"], f["line"], f["rule"]))
    return {"skills": len(skills(root)), "findings": achados}


def chave(f):
    """A identidade de um achado — sem a linha, que anda a cada edição do texto."""
    return (f["who"], f["rule"], f["quote"])


def report(res, novos=None):
    alvo = novos if novos is not None else res["findings"]
    cab = "Artigo 8 — %d skills varridas, %d achado(s)%s" % (
        res["skills"], len(alvo), " NOVO(s) vs o retrato" if novos is not None else "")
    out = [cab, ""]
    if not alvo:
        out.append("Nada novo. Todo comando de skill roda como está escrito.")
        return "\n".join(out) + "\n"
    for f in alvo:
        out.append("%s:%d  %s" % (f["who"], f["line"], f["rule"]))
        out.append("    %s" % f["msg"])
        out.append("    │ %s" % f["quote"])
    out.append("")
    out.append("Isenção legítima: `artigo8-ok: <motivo>` na linha.")
    out.append("Aceitar conscientemente: python3 scripts/artigo8_check.py (regrava o retrato).")
    return "\n".join(out) + "\n"


def grava(res):
    with open(BASELINE, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main(argv):
    res = varre()
    if "--json" in argv:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    if "--check" in argv:
        try:
            with open(BASELINE, encoding="utf-8") as fh:
                velho = {chave(f) for f in json.load(fh)["findings"]}
        except (OSError, ValueError, KeyError):
            print("retrato ausente ou ilegível: %s — nada a comparar" % BASELINE)
            return 0
        novos = [f for f in res["findings"] if chave(f) not in velho]
        print(report(res, novos))
        if novos:
            return 1
        # Catraca DESCE: dívida consertada sai do retrato na hora. Sem isto, o teto
        # fica congelado no tamanho antigo e o mesmo texto reintroduzido depois passa.
        consertados = len(velho) - len({chave(f) for f in res["findings"]})
        if consertados > 0:
            grava(res)
            print("retrato ABAIXADO: %d ponto(s) consertado(s) saíram de %s"
                  % (consertados, os.path.relpath(BASELINE, RAIZ)))
        return 0
    grava(res)
    print(report(res))
    print("retrato regravado: %s" % os.path.relpath(BASELINE, RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
