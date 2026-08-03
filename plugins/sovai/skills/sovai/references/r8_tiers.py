#!/usr/bin/env python3
"""O contrato R8 servido de um lugar só.

O drift que este módulo existe pra matar foi medido em 2026-08-03: trocar seis
valores custou 45 substituições em dois SKILL.md, três saíram invertidas e duas
sobreviveram a dois verificadores. A causa não era descuido — era o número morar
em quinze lugares.

Três usos, todos lendo o mesmo JSON:

    args    — o dicionário que a casca passa ao Workflow (o script usa
              `args.tiers.executor.effort`, nunca um literal)
    render  — a tabela em markdown, pra `r8-tiers.md` deixar de ser digitado
    check   — falha se o markdown divergir do JSON, ou se um SKILL.md
              voltar a carimbar um effort literal

Uso:
    python3 _shared/r8_tiers.py args
    python3 _shared/r8_tiers.py render
    python3 _shared/r8_tiers.py check [--fix]
"""
import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
JSON_PATH = os.path.join(AQUI, "r8-tiers.json")

# Onde o markdown gerado mora. As cópias vendoradas saem daqui por sync-shared.sh.
MD_PATH = os.path.join(AQUI, "r8-tiers.md")

# Um SKILL.md pode citar o NOME do knob à vontade; o que ele não pode é carimbar
# o valor. É essa linha que impede o número de voltar a morar em quinze lugares.
#
# O `model:` na mesma linha é o que separa uma chamada de agente de um campo
# `effort` qualquer: o /fallow tem um `effort: "low"` no relatório dele, que não
# tem nada com o R8 e não pode ser barrado por um check de outro assunto.
LITERAL = re.compile(
    r"model:\s*['\"][^'\"]+['\"][^\n]{0,40}?effort:\s*['\"](?:low|medium|high|xhigh|max)['\"]"
    r"|effort:\s*['\"](?:low|medium|high|xhigh|max)['\"][^\n]{0,40}?model:\s*['\"]")
NIVEL_SOLTO = re.compile(
    r"(?:decompose|coordinate|executor|mechanical|diagnose|finalize)_model"
    r"[^\n]{0,40}?`(?:low|medium|high|xhigh|max)`"
)

INICIO = "<!-- TABELA GERADA — r8_tiers.py render. Editar aqui não adianta. -->"
FIM = "<!-- FIM DA TABELA GERADA -->"


def carrega():
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def para_args(d=None):
    """O que a casca passa ao Workflow. Só o que o script precisa decidir."""
    d = d or carrega()
    return {
        "model": d["model"],
        "tiers": {k: {"effort": v["effort"]} for k, v in d["tiers"].items()},
    }


def render(d=None):
    """A tabela markdown, derivada do JSON. Ninguém digita isto à mão."""
    d = d or carrega()
    linhas = [
        INICIO,
        "",
        "| Etapa do fluxo | Modelo | Effort | Knob |",
        "|---|---|---|---|",
    ]
    for nome, t in d["tiers"].items():
        linhas.append("| %s | %s | `%s` | `%s_model` |"
                      % (t["etapa"], d["model"].capitalize(), t["effort"], nome))
    linhas += ["", "**Quando cada uma entra, e por quê:**", ""]
    for nome, t in d["tiers"].items():
        linhas.append("- **`%s_model`** (%s `%s`) — %s. %s."
                      % (nome, d["model"].capitalize(), t["effort"],
                         t["quando"], t["porque"][0].upper() + t["porque"][1:]))
    linhas += ["", "**Regra por rodada:**", ""]
    linhas += ["- " + r for r in d["regra_por_rodada"]]
    linhas += ["", "**Por que estes números:**", ""]
    linhas += ["- " + r for r in d["fundamento"]]
    linhas += ["", FIM]
    return "\n".join(linhas)


def _corpo_md(texto):
    i, j = texto.find(INICIO), texto.find(FIM)
    if i < 0 or j < 0:
        return None
    return texto[i:j + len(FIM)]


def aplica_no_md():
    """Reescreve o bloco gerado dentro de r8-tiers.md. Devolve True se mudou."""
    with open(MD_PATH, encoding="utf-8") as f:
        texto = f.read()
    novo = render()
    atual = _corpo_md(texto)
    if atual is None:
        raise SystemExit("⛔ r8-tiers.md não tem o marcador da tabela gerada:\n   %s" % INICIO)
    if atual == novo:
        return False
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write(texto.replace(atual, novo))
    return True


def _skill_mds():
    for base, _, arqs in os.walk(os.path.join(RAIZ, "plugins")):
        for a in arqs:
            if a == "SKILL.md":
                yield os.path.join(base, a)


def check(fix=False):
    erros = []

    with open(MD_PATH, encoding="utf-8") as f:
        atual = _corpo_md(f.read())
    if atual != render():
        if fix and aplica_no_md():
            print("↻ r8-tiers.md regenerado do JSON")
        else:
            erros.append("r8-tiers.md diverge do r8-tiers.json — rode: "
                         "python3 _shared/r8_tiers.py check --fix")

    for caminho in _skill_mds():
        rel = os.path.relpath(caminho, RAIZ)
        with open(caminho, encoding="utf-8") as f:
            for n, linha in enumerate(f, 1):
                if "r8-ok:" in linha:
                    continue
                for padrao, o_que in ((LITERAL, "effort literal"),
                                      (NIVEL_SOLTO, "nível ao lado de um knob")):
                    m = padrao.search(linha)
                    if m:
                        erros.append(
                            "%s:%d carimba %s (%s) — o valor vive em "
                            "_shared/r8-tiers.json e chega por args; cite o knob, não o número"
                            % (rel, n, o_que, m.group(0).strip()))
                        break

    if erros:
        print("⛔ contrato R8 furado:")
        for e in erros:
            print("   " + e)
        return 1
    print("OK: R8 servido de _shared/r8-tiers.json, sem cópia carimbada em SKILL.md")
    return 0


def _demo():
    """Checagem runnable mínima — falha se a derivação quebrar."""
    d = carrega()
    a = para_args(d)
    assert set(a["tiers"]) == set(d["tiers"]), "args perdeu um knob"
    assert a["tiers"]["executor"]["effort"] == d["tiers"]["executor"]["effort"]
    assert a["model"] == "opus", "R8 é all-Opus por contrato"
    md = render(d)
    for nome, t in d["tiers"].items():
        assert "`%s_model`" % nome in md, "%s sumiu da tabela" % nome
        assert "`%s`" % t["effort"] in md, "%s perdeu o effort" % nome
    assert LITERAL.search("{ model: 'opus', effort: 'high' }"), "regex não pega o literal"
    assert not LITERAL.search("usa o tier de `decompose`"), "regex acusa menção legítima"
    print("demo ok: args, render e regex derivam do JSON")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "args":
        print(json.dumps(para_args(), ensure_ascii=False, indent=2))
    elif cmd == "render":
        print(render())
    elif cmd == "demo":
        _demo()
    elif cmd == "check":
        sys.exit(check(fix="--fix" in sys.argv))
    else:
        raise SystemExit(__doc__)
