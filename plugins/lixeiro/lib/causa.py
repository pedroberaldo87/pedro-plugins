#!/usr/bin/env python3
"""causa.py — o que sobrou aberto, por que sobrou, e o quanto custa consertar.

POR QUE EXISTE. O lixeiro encerra o que ficou de pé, e até aqui parava nisso: a
máquina limpava e o defeito continuava, então na sessão seguinte tudo voltava. Em
2026-08-08 esse ciclo produziu **2125 processos `python3` órfãos** numa máquina, e
ninguém tinha como ligar aquilo ao código que os abriu.

Este módulo é a metade que faltava, e ele NÃO julga nem conserta — entrega material:

    investiga(procs)     de qual arquivo veio cada sobra, e por que ela sobrou
    alcance(arquivos)    o dígito que o juiz precisa ter na mão para decidir

QUEM JULGA É OUTRO, de propósito. A proposta de conserto sai de um agente, e quem
mede o alcance é este programa — número medido por quem não propôs. Juiz que avalia
o próprio trabalho não é juiz, e a régua fixa em tabela erra calada no caso torto.

FAIL-OPEN em toda borda: sem `ps`, sem git, sem arquivo — devolve vazio e cala. O
lixeiro é limpeza, e limpeza que derruba a sessão do dono é pior que sujeira.
"""

import json
import os
import subprocess
import sys

# CANAIS DE TEXTO EM UTF-8, SEMPRE. No Windows eles nascem na codificação do sistema
# (cp1252) e o payload do evento — que chega por stdin — é UTF-8: sem isto, todo
# acento do pedido do usuário chega corrompido ao gate, e emoji derruba a escrita.
for _canal in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_canal, "reconfigure"):
        try:
            _canal.reconfigure(encoding="utf-8")
        except Exception:
            pass

# Os padrões vêm da CÓPIA LOCAL de `_shared/padroes_vazamento.py`, nunca de outro
# plugin: o lixeiro roda em máquina onde o /check-skills pode não estar instalado, e
# limpeza que depende de outro plugin para funcionar não é limpeza — é acoplamento.
# A cópia é vendorada por `scripts/sync-shared.sh`; editá-la à mão é o que a fonte
# única existe para impedir (os três consumidores divergiram no dia em que nasceram).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from padroes_vazamento import ISENTO, RISCO  # noqa: E402


def _texto(caminho):
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def culpado(comando, raizes):
    """O arquivo do repositório que aparece no comando do processo, ou None.

    A ligação é por CAMINHO porque é a única que existe: o processo órfão perdeu o
    pai, então não há árvore para subir — o que sobra é o texto do comando dele.
    """
    for t in comando.split():
        limpo = t.strip("'\"")
        if not limpo.endswith((".py", ".mjs", ".js", ".sh")):
            continue
        if os.path.isfile(limpo):
            return limpo
        for r in raizes:
            cand = os.path.join(r, limpo)
            if os.path.isfile(cand):
                return cand
    return None


def investiga(sobras, raizes=()):
    """[{pid, comando, arquivo, linha, motivo}] — por que cada sobra sobrou.

    `sobras` = [{pid, comando}], o que o lixeiro encontrou de pé. Sobra sem arquivo
    identificável entra na lista com `arquivo: None` — "não sei de onde veio" é
    resultado honesto, e some-la esconderia justamente o caso difícil.
    """
    fora = []
    for s in sobras:
        cmd = s.get("comando") or s.get("cmd") or ""
        arq = culpado(cmd, raizes)
        achado = {"pid": s.get("pid"), "comando": cmd[:200],
                  "arquivo": arq, "linha": None, "motivo": None}
        if arq:
            txt = _texto(arq)
            linhas = txt.splitlines()
            # o rótulo curto é do relatório de lista; aqui vale o HUMANO, porque
            # quem lê esta saída precisa entender a consequência, não catalogar
            for padrao, _curto, motivo in RISCO:
                m = padrao.search(txt)
                if not m:
                    continue
                ln = txt.count("\n", 0, m.start()) + 1
                if ISENTO.search("\n".join(linhas[max(0, ln - 2):ln])):
                    continue
                achado["linha"], achado["motivo"] = ln, motivo
                break
        if achado["motivo"] is None:
            achado["motivo"] = ("não deu para dizer pelo código — o comando não aponta "
                                "arquivo deste repositório, ou o arquivo não traz padrão conhecido")
        fora.append(achado)
    return fora


def _dono_do_arquivo(caminho):
    """('proprio'|'terceiro'|'desconhecido', nome) — de quem é o arquivo.

    Plugin de terceiro é o limite mais duro que existe aqui: o conserto não sobrevive
    à próxima atualização dele, e mexer no código de outro sem avisar é o oposto do
    que este programa deveria fazer.
    """
    p = os.path.abspath(caminho)
    marca = os.sep + "plugins" + os.sep + "cache" + os.sep
    if marca in p:
        resto = p.split(marca, 1)[1].split(os.sep)
        market = resto[0] if resto else "?"
        return ("proprio" if market == "pedro-plugins" else "terceiro", market)
    return ("proprio" if os.sep + "pedro-plugins" + os.sep in p else "desconhecido", "")


def _roda_em_hook(caminho, raiz):
    """O arquivo é chamado por algum hooks.json? Hook roda em TODA sessão."""
    nome = os.path.basename(caminho)
    for base, _, arqs in os.walk(raiz):
        if "node_modules" in base or "__pycache__" in base:
            continue
        if "hooks.json" not in arqs:
            continue
        if nome in _texto(os.path.join(base, "hooks.json")):
            return True
    return False


def alcance(arquivos, raiz=None, linhas_mudadas=0):
    """O dígito que o juiz recebe. Este programa MEDE; quem decide é outro.

    Nenhum campo aqui é veredito: são fatos que mudam a resposta, e a separação é o
    ponto — juiz que também mediu tende a confirmar a própria medida.
    """
    raiz = raiz or os.getcwd()
    donos = [_dono_do_arquivo(a) for a in arquivos]
    return {
        "arquivos": len(arquivos),
        "linhas_mudadas": linhas_mudadas,
        "de_terceiro": [n for (t, n) in donos if t == "terceiro"],
        "em_hook": [a for a in arquivos if _roda_em_hook(a, raiz)],
        "tem_suite": [a for a in arquivos if _suite_de(a)],
        "sem_suite": [a for a in arquivos if not _suite_de(a)],
    }


def _suite_de(arquivo):
    """A suíte que cobre este arquivo, ou None. `test_<nome>.py` ao lado é a regra."""
    d, nome = os.path.dirname(arquivo), os.path.basename(arquivo)
    if nome.startswith("test_"):
        return arquivo
    for cand in ("test_" + nome, "test_" + os.path.splitext(nome)[0] + ".py"):
        p = os.path.join(d, cand)
        if os.path.isfile(p):
            return p
    return None


def suite_verde(arquivo):
    """(rodou, verde, saida) — a rede que segura o conserto aplicado no ato.

    Correção automática sem suíte é como a bomba de 2026-08-08 nasceu: cada peça
    estava certa sozinha e ninguém rodou o conjunto.
    """
    s = _suite_de(arquivo)
    if not s:
        return (False, False, "nenhuma suíte cobre %s" % os.path.basename(arquivo))
    try:
        r = subprocess.run([sys.executable, s], stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
                           start_new_session=True, cwd=os.path.dirname(s) or None)
    except (OSError, subprocess.SubprocessError) as e:
        return (True, False, "a suíte não rodou: %s" % e)
    return (True, r.returncode == 0, (r.stdout or r.stderr or "")[-800:])


def main(argv=None):
    """Uso: causa.py investiga|alcance — lê o JSON no stdin, escreve o JSON no stdout."""
    modo = (argv or sys.argv[1:] or ["investiga"])[0]
    try:
        entrada = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        entrada = {}
    if modo == "alcance":
        print(json.dumps(alcance(entrada.get("arquivos") or [],
                                 entrada.get("raiz"),
                                 entrada.get("linhas_mudadas") or 0),
                         ensure_ascii=False, indent=1))
    else:
        print(json.dumps(investiga(entrada.get("sobras") or [],
                                   entrada.get("raizes") or []),
                         ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
