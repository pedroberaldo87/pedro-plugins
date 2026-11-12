#!/usr/bin/env python3
"""test_lixeiro_modos.py — o estado do lixeiro é só do dono (P12).

O registro da sessão guarda os comandos que abriram servidor/túnel (até 400 caracteres cada,
com o que estiver na linha de comando) e o colhido.jsonl guarda a linha de comando de tudo
que o lixeiro encerrou. Segredo passado por flag fica ali depois que o processo morre —
então a pasta nasce 0700 e os arquivos 0600, mesmo com umask aberto, e o que já existia
frouxo é apertado na próxima escrita.

Modo POSIX não se mede no Windows (o chmod ali só mexe no bit de leitura): lá a suíte
só confere que a gravação continua funcionando.

Roda com:  python3 plugins/lixeiro/lib/test_lixeiro_modos.py
"""
import os
import shutil
import stat
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

TMP = tempfile.mkdtemp(prefix="lixeiro-modos-")
os.environ["CLAUDE_CONFIG_DIR"] = TMP

import lixeiro  # noqa: E402

POSIX = os.name != "nt"
PASSOU = 0
FALHAS = []


def check(nome, cond, detalhe=""):
    global PASSOU
    if cond:
        print("  ok · %s" % nome)
        PASSOU += 1
    else:
        print("  FALHOU · %s %s" % (nome, detalhe))
        FALHAS.append(nome)


def modo(p):
    try:
        return stat.S_IMODE(os.stat(p).st_mode)
    except OSError:
        return -1


REG = {"session_id": "sessao-modos", "dono_pid": None,
       "anotacoes": [{"pid": 1, "cmd": "tunnel --token exemplo"}]}
ITENS = [{"pid": 123, "cmd": "tunnel --token exemplo"}]

try:
    antigo = os.umask(0o000)           # o pior caso: o processo cria tudo aberto
    try:
        lixeiro.grava_registro(REG)
        lixeiro.registra_colheita(ITENS)
    finally:
        os.umask(antigo)

    pasta = lixeiro.state_dir()
    reg = lixeiro.registro_path("sessao-modos")
    log = lixeiro.log_path()
    check("o registro foi gravado", os.path.isfile(reg))
    check("o colhido.jsonl foi gravado", os.path.isfile(log))
    check("o registro volta lido", lixeiro.le_registro("sessao-modos").get("anotacoes") == REG["anotacoes"])
    if POSIX:
        check("pasta do estado 0700", modo(pasta) == 0o700, "— é %o" % modo(pasta))
        check("registro da sessão 0600", modo(reg) == 0o600, "— é %o" % modo(reg))
        check("colhido.jsonl 0600", modo(log) == 0o600, "— é %o" % modo(log))
        check("não sobrou .tmp do registro", not os.path.exists(reg + ".tmp"))

        # estado antigo e frouxo: a próxima escrita aperta
        os.chmod(pasta, 0o755)
        os.chmod(reg, 0o644)
        os.chmod(log, 0o644)
        lixeiro.grava_registro(REG)
        lixeiro.registra_colheita(ITENS)
        check("pasta 0755 pré-existente é apertada para 0700", modo(pasta) == 0o700, "— é %o" % modo(pasta))
        check("registro 0644 pré-existente é apertado para 0600", modo(reg) == 0o600, "— é %o" % modo(reg))
        check("colhido.jsonl 0644 pré-existente é apertado para 0600", modo(log) == 0o600, "— é %o" % modo(log))
        n = len(open(log, encoding="utf-8").read().splitlines())
        check("o log continua acrescentando (2 linhas)", n == 2, "— tem %d" % n)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\nlixeiro modos: %d ok, %d falha(s)" % (PASSOU, len(FALHAS)))
sys.exit(1 if FALHAS else 0)
