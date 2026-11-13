#!/usr/bin/env python3
"""Escrita de estado sem seguir symlink (cf35688f · hsf_38d27434).

Um clone pode trazer, versionado, um symlink no nome de um arquivo de estado. Os escritores
abriam o caminho com `open(…, "w")` e gravavam através do link — fora do projeto. Esta suíte
planta o link em CADA ponto de escrita e exige: nada cai no alvo de fora, e o alvo continua
byte a byte como estava.

Pontos: neblina (grava e anexa), precheck.json (grava e rodada N+1), ledger.json e
findings.jsonl do journal, a marca de sessão do plan_state, e a pasta-symlink que sai da raiz.

Roda com:  python3 plugins/project-skills/lib/test_escrita_segura.py
"""
import json
import os
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
os.environ["PROJECT_DOC_SALT_FILE"] = os.path.join(tempfile.mkdtemp(prefix="escseg-salt-"),
                                                   "journal.salt")

import journal  # noqa: E402
import plan_state as ps  # noqa: E402
import precheck_largada as pl  # noqa: E402
from escrita_segura import (EscritaRecusada, anexa_texto_seguro,  # noqa: E402
                            grava_texto_seguro)

ok = falhas = 0
ALVO_ORIGINAL = "NAO-MEXER\n"


def checa(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s %s" % (nome, detalhe))


def nova_arena():
    base = tempfile.mkdtemp(prefix="escseg-")
    raiz = os.path.join(base, "repo")
    fora = os.path.join(base, "fora")
    os.makedirs(raiz)
    os.makedirs(fora)
    return raiz, fora


def alvo_intacto(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return fh.read() == ALVO_ORIGINAL


def planta_link(raiz, rel, fora, nome="alvo.txt"):
    """Cria `raiz/rel` como symlink para `fora/nome` (que já existe, com o conteúdo original)."""
    alvo = os.path.join(fora, nome)
    with open(alvo, "w", encoding="utf-8") as fh:
        fh.write(ALVO_ORIGINAL)
    link = os.path.join(raiz, rel)
    os.makedirs(os.path.dirname(link), exist_ok=True)
    os.symlink(alvo, link)
    return alvo


def recusa(fn):
    """True se `fn` levantou recusa (OSError/PlanError) — a escrita foi barrada."""
    try:
        fn()
    except (OSError, ps.PlanError):
        return True
    return False


print("== escrita_segura (o núcleo)")
raiz, fora = nova_arena()
alvo = planta_link(raiz, "a.txt", fora)
checa("grava recusa symlink", recusa(lambda: grava_texto_seguro(os.path.join(raiz, "a.txt"), "x")))
checa("anexa recusa symlink", recusa(lambda: anexa_texto_seguro(os.path.join(raiz, "a.txt"), "x")))
checa("alvo do link intacto", alvo_intacto(alvo))
normal = os.path.join(raiz, "n.txt")
grava_texto_seguro(normal, "um\n")
anexa_texto_seguro(normal, "dois\n")
with open(normal, encoding="utf-8") as fh:
    checa("arquivo comum grava e anexa", fh.read() == "um\ndois\n")
checa("grava deixa só o arquivo (sem .tmp)", sorted(os.listdir(raiz)) == ["a.txt", "n.txt"],
      str(sorted(os.listdir(raiz))))
os.chmod(normal, 0o640)
grava_texto_seguro(normal, "tres\n")
if os.name == "posix":
    checa("modo antigo preservado", (os.stat(normal).st_mode & 0o777) == 0o640)

print("== pasta-symlink que sai da raiz")
raiz, fora = nova_arena()
os.makedirs(os.path.join(raiz, ".claude"))
os.symlink(fora, os.path.join(raiz, ".claude", ".sprint"))
r = recusa(lambda: grava_texto_seguro(os.path.join(raiz, ".claude", ".sprint", "precheck.json"),
                                      "{}", raiz=raiz))
checa("pasta que sai da raiz é recusada", r)
checa("nada caiu fora", os.listdir(fora) == [], str(os.listdir(fora)))

print("== precheck_largada: neblina.md")
raiz, fora = nova_arena()
alvo = planta_link(raiz, ".claude/neblina.md", fora)
checa("anotar_neblina recusa o link", recusa(lambda: pl.anotar_neblina(raiz, "algo estranho", "sem forma")))
checa("anotar_neblina: alvo intacto", alvo_intacto(alvo))

raiz, fora = nova_arena()
pl.anotar_neblina(raiz, "algo estranho", "sem forma")
neb = pl.casa_da_neblina(raiz)
real = os.path.join(fora, "neblina-real.md")
os.replace(neb, real)                       # o arquivo vira link: dono troca por symlink
os.symlink(real, neb)
with open(real, encoding="utf-8") as fh:
    antes = fh.read()
checa("declarar_fora_de_escopo recusa o link",
      recusa(lambda: pl.declarar_fora_de_escopo(raiz, "algo estranho", "motivo")))
with open(real, encoding="utf-8") as fh:
    checa("declarar_fora_de_escopo: alvo intacto", fh.read() == antes)

print("== precheck_largada: precheck.json")
raiz, fora = nova_arena()
alvo = planta_link(raiz, ".claude/.sprint/precheck.json", fora)
plano = {"id": "p", "steps": []}
checa("grava_relatorio recusa o link", recusa(lambda: pl.grava_relatorio(raiz, plano, {})))
checa("grava_relatorio: alvo intacto", alvo_intacto(alvo))

raiz, fora = nova_arena()
pl.grava_relatorio(raiz, plano, {})
rel = pl.casa_do_relatorio(raiz)
real = os.path.join(fora, "rel-real.json")
os.replace(rel, real)
os.symlink(real, rel)
with open(real, encoding="utf-8") as fh:
    antes = fh.read()
checa("aplica_rodada_seguinte recusa o link",
      recusa(lambda: pl.aplica_rodada_seguinte(raiz, plano, {"perguntas": []}, [])))
with open(real, encoding="utf-8") as fh:
    checa("aplica_rodada_seguinte: alvo intacto", fh.read() == antes)

raiz, fora = nova_arena()
os.makedirs(os.path.join(raiz, ".claude"))
os.symlink(fora, os.path.join(raiz, ".claude", ".sprint"))
checa("grava_relatorio recusa pasta-symlink", recusa(lambda: pl.grava_relatorio(raiz, plano, {})))
checa("grava_relatorio: nada caiu fora", os.listdir(fora) == [], str(os.listdir(fora)))

print("== decisoes_seladas: decisoes-seladas.md")
from decisoes_seladas import selar  # noqa: E402
raiz, fora = nova_arena()
alvo = planta_link(raiz, ".claude/decisoes-seladas.md", fora)
checa("selar recusa o link", recusa(lambda: selar(raiz, "tudo no final", "teste")))
checa("selar: alvo intacto", alvo_intacto(alvo))

print("== journal: ledger.json e findings.jsonl")
raiz, fora = nova_arena()
alvo = planta_link(raiz, ".claude/.project-doc/ledger.json", fora)
checa("save_ledger recusa o link", recusa(lambda: journal.save_ledger(raiz, {"mined_sessions": {}})))
checa("save_ledger: alvo intacto", alvo_intacto(alvo))

raiz, fora = nova_arena()
alvo = planta_link(raiz, ".claude/.project-doc/findings.jsonl", fora)
checa("append_events recusa o link", recusa(lambda: journal.append_events(raiz, [{"k": 1}])))
checa("append_events: alvo intacto", alvo_intacto(alvo))

raiz, fora = nova_arena()
journal.save_ledger(raiz, {"mined_sessions": {}, "last_commit": None})
journal.append_events(raiz, [{"k": 1}])
with open(journal.ledger_path(raiz), encoding="utf-8") as fh:
    checa("save_ledger comum continua gravando", json.load(fh)["mined_sessions"] == {})
with open(journal.journal_path(raiz), encoding="utf-8") as fh:
    checa("append_events comum continua gravando", json.loads(fh.read().strip()) == {"k": 1})

print("== plan_state: marca de sessão em pasta temporária compartilhada")
tmp = tempfile.mkdtemp(prefix="escseg-tmp-")
fora = tempfile.mkdtemp(prefix="escseg-out-")
antigo = tempfile.tempdir
tempfile.tempdir = tmp
try:
    diretorio = os.path.join(tmp, "plans")
    os.makedirs(diretorio)
    sentinel = ps._sentinel_sessao(diretorio, "sessao-x")
    assert sentinel
    alvo = os.path.join(fora, "alvo.txt")
    with open(alvo, "w", encoding="utf-8") as fh:
        fh.write(ALVO_ORIGINAL)
    os.symlink(alvo, sentinel)
    ps._marca_sessao(diretorio, "plano-a", sid="sessao-x")
    checa("_marca_sessao não escreve através do link", alvo_intacto(alvo))
    os.unlink(sentinel)
    ps._marca_sessao(diretorio, "plano-a", sid="sessao-x")
    checa("_marca_sessao comum continua gravando", ps._plano_da_sessao(diretorio, "sessao-x") == "plano-a")
finally:
    tempfile.tempdir = antigo

print("\n%d ok, %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
