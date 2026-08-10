#!/usr/bin/env python3
"""O medidor da vistoria — um comando roda os 9 cobradores que já existem no repo.

Cada cobrador já sabe medir a sua parte e já sabe dizer onde dói; o que não
existia era um lugar onde as nove saídas viram a MESMA coisa. É isso aqui: um
JSON só, uma lista de achados no formato de `achado.py`, cada um carregando o
trecho cru que o cobrador viu. Achado sem prova é recusado na porta pelo
validador — não vira item fraco na lista.

Uso:
    python3 plugins/vistoria/lib/medidor.py            # resumo por cobrador
    python3 plugins/vistoria/lib/medidor.py --json     # {achados, _descartes}

Cobrador que quebra não derruba a medição (fail-open, como o resto do repo):
ele sai do JSON e aparece no resumo como "não medido".

stdlib only (requisito do repo).
"""

import importlib.util
import json
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from achado import AchadoInvalido, achado  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

PLANOS = os.path.join(ROOT, ".claude", "plans")


# O OUTRO LADO DA TRAVA DE REENTRÂNCIA (a marca nasce em `scripts/plano_vs_codigo.py`).
# Em 2026-08-08 o encontro destes dois programas virou bomba de forks — 2125 processos
# órfãos numa máquina. O ciclo: o `plano_vs_codigo` executa o `pronto` de cada passo, o
# `pronto` do passo F11.7 manda rodar ESTE medidor, e este medidor roda os nove
# cobradores — um deles sendo o `plano_vs_codigo`. Voltava ao topo, sem fundo.
# Aqui a marca é LIDA: estando acesa, este medidor está sendo chamado de dentro de um
# critério, e fechar a volta é o que ele não pode fazer.
REENTRANCIA = "PLANO_VS_CODIGO_RODANDO"

# 90s: o medidor consolida nove cobradores, e o mais lento varre o repositório inteiro.
# Sem teto, cobrador travado segura a rodada para sempre — foi assim que a bomba passou
# despercebida por minutos.
TIMEOUT = 90


def _json_de(*args):
    """Roda um script do repo e devolve o JSON que ele imprime.

    `stdin` fechado, sessão própria e `killpg` pelo mesmo motivo do outro lado: o
    `timeout` do subprocess mata o filho direto e deixa o NETO vivo, e comando que
    herda o terminal fica pendurado sem nunca estourar teto nenhum.
    """
    p = None
    try:
        p = subprocess.Popen([sys.executable] + [os.path.join(ROOT, args[0])] + list(args[1:]),
                             cwd=ROOT, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8", errors="replace", start_new_session=True)
        out, _ = p.communicate(timeout=TIMEOUT)
        return json.loads(out)
    finally:
        if p is not None and p.poll() is None:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except OSError:
                p.kill()
            try:
                p.wait(timeout=5)
            except Exception:
                pass


# O que o cobrador viu e NÃO conseguiu provar. Sai do lote e vai para o rodapé da
# página: lote que encolhe em silêncio é decisão tomada sobre uma lista incompleta.
DESCARTES = []


def _talvez(**kw):
    """Achado só com trecho próprio. Sem prova, vira descarte e devolve None.

    Antes daqui o tradutor caía na mensagem do cobrador quando o trecho vinha
    vazio (`prova=quote or msg`) — o achado saía repetindo a própria acusação, e
    prova que ecoa a acusação não é prova.
    """
    try:
        return achado(**kw)
    except AchadoInvalido as e:
        DESCARTES.append({"cobrador": kw.get("cobrador"), "onde": kw.get("onde"),
                          "o_que": kw.get("o_que"), "motivo": str(e)})
        return None


def _com_prova(itens):
    """O lote sem os que viraram descarte."""
    return [a for a in itens if a is not None]


def _importa(rel, nome):
    """Importa um módulo do repo pelo caminho — cobrador que não tem --json."""
    spec = importlib.util.spec_from_file_location(nome, os.path.join(ROOT, rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hook_contract():
    d = _json_de("scripts/hook_contract.py", "--json")
    return _com_prova(
        _talvez(cobrador="hook-contract", regra=f["rule"],
                gravidade={"high": "alta", "med": "media"}.get(f["sev"], "baixa"),
                onde="%s:%s" % (f["who"], f["line"]),
                o_que=f["msg"], prova=f["quote"])
        for f in d["findings"])


def desacoplamento():
    d = _json_de("scripts/desacoplamento_check.py", "--json", "--todos")
    return [achado(cobrador="desacoplamento", regra=f["forma"],
                   onde="%s:%s" % (f["arquivo"], f["linha"]),
                   o_que="afirmação acoplada ao código: %s" % f["alvo"],
                   prova=f["trecho"])
            for f in d["todos"]]


def public_repo():
    d = _json_de("scripts/public_repo_check.py", "--json")
    return [achado(cobrador="public-repo", regra=f["rule"], gravidade="alta",
                   onde="%s:%s" % (f["file"], f["line"]),
                   o_que=f["what"], prova=f["excerpt"])
            for f in d["findings"]]


def regua_call():
    d = _json_de("scripts/regua_call_check.py", "--json")
    return [achado(cobrador="regua-call", regra=f["signal"],
                   onde="%s:%s" % (f["file"], f["line"]),
                   o_que="monta página e não chama a régua de texto",
                   prova=f["excerpt"])
            for f in d["findings"]]


def readme_counts():
    d = _json_de("scripts/readme_counts_check.py", "--json")
    return _com_prova(
        _talvez(cobrador="readme-counts", regra=f["id"],
                onde="%s:%s" % (f["onde"], f["linha"]),
                o_que=f["msg"], prova=f.get("trecho"))
        for f in d["achados"])


def suites_orfas():
    mod = _importa("scripts/suites_orfas.py", "suites_orfas")
    fora, _tests, pats = mod.orfas(ROOT)
    return [achado(cobrador="suites-orfas", regra="fora-da-esteira", onde=t,
                   o_que="suíte rastreada que nenhum globo da esteira roda",
                   prova="%s não casa nenhum de %d globo(s)" % (t, len(pats)))
            for t in (fora or [])]


def plano_vs_codigo():
    # A volta que fechava o ciclo. Estando a marca acesa, quem nos chamou FOI o
    # `plano_vs_codigo` (por um critério que manda rodar este medidor): rodá-lo de
    # novo recomeça a recursão. Lista vazia é o resultado certo — este cobrador já
    # está rodando lá em cima, e o achado dele sai por lá.
    if os.environ.get(REENTRANCIA):
        return []
    d = _json_de("scripts/plano_vs_codigo.py", "--json")
    return [achado(cobrador="plano-vs-codigo", regra="divergente", gravidade="alta",
                   onde="%s#%s" % (f["plano"], f["id"]),
                   o_que="o `pronto` diverge do código: %s" % f["title"],
                   prova=f["pronto"])
            for f in d if f["veredito"] == "divergente"]


def _passos_abertos():
    """Os passos ainda não feitos dos planos do projeto, com o texto do `pronto`."""
    if not os.path.isdir(PLANOS):
        return []
    abertos = []
    for nome in sorted(os.listdir(PLANOS)):
        if not nome.endswith(".plan.json"):
            continue
        with open(os.path.join(PLANOS, nome), encoding="utf-8") as fh:
            plano = json.load(fh)

        def anda(o):
            if isinstance(o, dict):
                if o.get("id") and o.get("pronto") and o.get("status") != "done":
                    abertos.append((nome, o["id"], o["pronto"]))
                for v in o.values():
                    anda(v)
            elif isinstance(o, list):
                for v in o:
                    anda(v)

        anda(plano)
    return abertos


def regua_pronto():
    mod = _importa("plugins/project-skills/lib/regua_pronto.py", "regua_pronto")  # acopla-ok: auto-vistoria do proprio repo, roda da raiz e nao viaja
    achados = []
    for nome, pid, pronto in _passos_abertos():
        errs = mod.erros_de_pronto(pronto, pid)
        for e in errs:
            achados.append(achado(cobrador="regua-pronto", regra="pronto-de-bancada",
                                  onde="%s#%s" % (nome, pid), o_que=e, prova=pronto))
    return achados


def conformance():
    d = _json_de("plugins/bootstrap/lib/conformance.py", "--json")  # acopla-ok: auto-vistoria do proprio repo, roda da raiz e nao viaja
    return [achado(cobrador="conformance", regra=f["area"], onde=f["area"],
                   o_que=f["o_que"], prova=f["evidencia"])
            for f in d["desvios"]]


COBRADORES = (
    ("hook-contract", hook_contract),
    ("desacoplamento", desacoplamento),
    ("public-repo", public_repo),
    ("regua-call", regua_call),
    ("readme-counts", readme_counts),
    ("suites-orfas", suites_orfas),
    ("plano-vs-codigo", plano_vs_codigo),
    ("regua-pronto", regua_pronto),
    ("conformance", conformance),
)


def mede(quais=None):
    """Roda os cobradores e devolve (achados, falhas) — falha é cobrador não medido."""
    achados, falhas = [], {}
    del DESCARTES[:]
    for nome, fn in COBRADORES:
        if quais and nome not in quais:
            continue
        try:
            achados.extend(fn())
        except Exception as e:                    # cobrador quebrado não derruba a medição
            falhas[nome] = "%s: %s" % (type(e).__name__, e)
    return achados, falhas


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    quer_json = "--json" in argv
    quais = [a for a in argv if not a.startswith("--")]

    achados, falhas = mede(quais or None)

    if quer_json:
        # Envelope, não lista crua: é por `_descartes` que a página monta o rodapé.
        print(json.dumps({"achados": achados, "_descartes": DESCARTES},
                         ensure_ascii=False, indent=1))
        return 0

    por_cobrador = {}
    for a in achados:
        por_cobrador[a["cobrador"]] = por_cobrador.get(a["cobrador"], 0) + 1
    print("vistoria: %d achado(s) de %d cobrador(es)"
          % (len(achados), len(COBRADORES) - len(falhas)))
    for nome, _fn in COBRADORES:
        if nome in falhas:
            print("  %-16s → não medido (%s)" % (nome, falhas[nome]))
        else:
            print("  %-16s → %d" % (nome, por_cobrador.get(nome, 0)))
    if DESCARTES:
        print("  %d descartado(s) por falta de prova (vão no rodapé da página)"
              % len(DESCARTES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
