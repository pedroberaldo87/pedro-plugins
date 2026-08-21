#!/usr/bin/env python3
"""O teto de texto nas mensagens de hook — o cobrador que o Artigo 6 pedia.

A regra (docs/constituicao.md · Artigo 6): mensagem que um hook emite a um humano  # casa-ok: citação da lei em prosa de docstring, não caminho executado
passa pela regra de texto (`_shared/regua_texto.py`, perfil hook: 140 por linha).
A checagem I (`regua_call_check.py`) cobre só gerador Python; este arquivo fecha o
furo declarado no artigo para os hooks shell.

O que ele mede: em toda linha de `plugins/*/hooks/*.sh` e `.claude/hooks/*.sh` que
emite mensagem (hj_deny/hj_block/hj_msg_ctx/hj_ctx/hj_avisa/systemMessage ou a
atribuição de MSG/CTX), o texto LITERAL entre aspas — sem expansões `$…` — é
separado nas quebras (`\\n` e reais) e cada linha emitida tem teto de 160
caracteres (o 140 do perfil + folga de marcação, porque expansão removida não
conta e marcação não conta na regra).

O que ele NÃO pega (declarado, Artigo 4): continuação de string multilinha sem o
token na mesma linha-fonte, e mensagem montada por concatenação em variável fora
do padrão. Isenção legítima: `msg-ok: <motivo>` na linha.
"""
import glob
import os
import re
import sys
import tempfile

TETO = 160
GATILHO = re.compile(
    r"hj_deny|hj_block|hj_msg_ctx|hj_ctx|hj_avisa|systemMessage|"
    r"^\s*(?:CTX|MSG|CP_MSG|ESC_HINT|STALEMSG|DOCLIST|APPMSG|OOPMSG|RELEASE_HINT)[A-Z_]*=")
ASPAS = re.compile(r'"((?:[^"\\]|\\.)*)"')
EXPANSAO = re.compile(r"\$\{[^}]*\}|\$\([^)]*\)|\$[A-Za-z_][A-Za-z0-9_]*")


def achados_do_arquivo(caminho):
    out = []
    try:
        linhas = open(caminho, encoding="utf-8", errors="replace").readlines()
    except OSError:
        return out
    for i, ln in enumerate(linhas, 1):
        if not GATILHO.search(ln) or "msg-ok:" in ln:
            continue
        for bloco in ASPAS.findall(ln):
            bloco = EXPANSAO.sub("", bloco)
            for emitida in re.split(r"\\n|\n", bloco):
                if len(emitida) > TETO:
                    out.append((caminho, i, len(emitida), emitida[:80]))
    return out


def varre(raiz="."):
    arquivos = sorted(glob.glob(os.path.join(raiz, "plugins", "*", "hooks", "*.sh"))
                      + glob.glob(os.path.join(raiz, ".claude", "hooks", "*.sh")))
    achados = []
    for f in arquivos:
        achados.extend(achados_do_arquivo(f))
    return arquivos, achados


def autoteste():
    # o teste que já falhou: uma mensagem de 300 tem que reprovar, uma curta não
    with tempfile.TemporaryDirectory() as d:
        ruim = os.path.join(d, "ruim.sh")
        open(ruim, "w", encoding="utf-8").write('hj_deny "' + "x" * 300 + '"\n')
        assert achados_do_arquivo(ruim), "linha de 300 tinha que reprovar"
        bom = os.path.join(d, "bom.sh")
        open(bom, "w", encoding="utf-8").write('hj_deny "curta.\\n- bullet curto."\n')
        assert not achados_do_arquivo(bom), "mensagem em bullets curtos tinha que passar"
        isento = os.path.join(d, "isento.sh")
        open(isento, "w", encoding="utf-8").write('hj_deny "' + "x" * 300 + '"  # msg-ok: prova\n')
        assert not achados_do_arquivo(isento), "isenção msg-ok tinha que calar"


def main():
    autoteste()
    raiz = sys.argv[1] if len(sys.argv) > 1 else "."
    arquivos, achados = varre(raiz)
    if not arquivos:
        print("regua-hook-msgs: nenhum hook para medir — não medi.")
        return 1
    for f, i, n, trecho in achados:
        print("  %s:%d — %d caracteres emitidos (teto %d): %s…" % (f, i, n, TETO, trecho))
    if achados:
        print("regua-hook-msgs: %d linha(s) de mensagem acima do teto." % len(achados))
        return 1
    print("regua-hook-msgs: OK — %d hooks medidos, nenhuma mensagem acima do teto." % len(arquivos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
