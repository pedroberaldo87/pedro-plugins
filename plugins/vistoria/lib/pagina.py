#!/usr/bin/env python3
"""A página de achados da vistoria — prova colada, um checkbox por achado.

Entra o JSON do medidor pelo `stdin`, sai um HTML em `.claude/vistoria/` e o
caminho dele no `stdout`. A página existe para uma coisa só: o dono marcar o que
vira passo do plano. Por isso cada achado carrega o trecho cru que o cobrador
viu — decidir sem a prova na frente é o que esta ferramenta não faz.

`.claude/vistoria/` e nunca `/tmp`: o scope-cop já mordeu página escrita fora do
projeto.

O destino NÃO é adivinhado: `--dir` é obrigatório. Um padrão calculado a partir da
posição deste arquivo aponta para dentro do cache do plugin quando instalado — a
página do dono nasceria na pasta do autor da skill. Sem `--dir`, o programa recusa.

Uso:
    python3 plugins/vistoria/lib/medidor.py --json \
        | python3 plugins/vistoria/lib/pagina.py --dir .claude/vistoria

O texto autoral da página (título, linha de abertura, nome de cada seção) passa
pela régua compartilhada, no perfil `pagina`. O que veio do cobrador — `onde`,
`o_que`, `prova` — é saída crua colada verbatim: cortá-la para caber num teto
destruiria a prova, que é a razão de a página existir.

stdlib only (requisito do repo).
"""

import argparse
import datetime
import html
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from regua_texto import erros_de_estilo  # noqa: E402

TITULO = "Vistoria do marketplace"
ABERTURA = "Marque o achado que vira passo do plano; a prova de cada um abre com um clique."
# Os três níveis do `quality-goals.md`: a linha do achado fica visível, o corpo nasce
# fechado, e a prova nasce fechada dentro do corpo. Sem exceção de tamanho.
CORPO = "onde e qual regra"
PROVA = "a prova crua"

CSS = """
body{background:#12141a;color:#e6e8ee;font:15px/1.55 -apple-system,Segoe UI,sans-serif;
margin:0;padding:32px}
main{max-width:900px;margin:0 auto}
h1{font-size:24px;margin:0 0 4px}
p.abertura{color:#9aa2b1;margin:0 0 28px}
h2{font-size:16px;margin:32px 0 12px;color:#8ab4ff;border-bottom:1px solid #262a33;
padding-bottom:6px}
.achado{background:#181b22;border:1px solid #262a33;border-radius:8px;padding:12px 14px;
margin:10px 0}
.achado label{display:flex;gap:10px;align-items:flex-start;cursor:pointer}
.onde{color:#9aa2b1;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.grav{font-size:11px;text-transform:uppercase;letter-spacing:.06em;margin-left:8px}
.alta{color:#ff7b72}.media{color:#e3b341}.baixa{color:#7ee787}
details{margin:8px 0 0 26px}
summary{color:#8ab4ff;font-size:12px;cursor:pointer}
pre{background:#0d0f14;border:1px solid #262a33;border-radius:6px;margin:10px 0 0;
padding:10px;overflow-x:auto;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
color:#c9d1d9;white-space:pre-wrap}
"""


def _e(v):
    return html.escape(str(v if v is not None else ""))


def texto_autoral(lentes):
    """O que a página escreve por conta própria — e só isso entra na régua."""
    return [TITULO, ABERTURA, CORPO, PROVA] + \
        ["%s — %d achado(s)" % (n, len(a)) for n, a in lentes]


def erros_da_pagina(lentes):
    """A régua compartilhada sobre o texto autoral. Lista vazia = a página pode sair."""
    errs = []
    for i, campo in enumerate(texto_autoral(lentes)):
        errs += erros_de_estilo(campo, "pagina bloco %d" % i, "pagina")
    return errs


def por_lente(achados):
    """Os achados agrupados pela lente que os produziu, na ordem de chegada."""
    grupos = {}
    for a in achados:
        grupos.setdefault(a.get("cobrador") or "sem lente", []).append(a)
    return sorted(grupos.items(), key=lambda kv: (-len(kv[1]), kv[0]))


def html_de(lentes, total):
    partes = ["<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">",
              "<title>%s</title><style>%s</style></head><body><main>" % (_e(TITULO), CSS),
              "<h1>%s</h1>" % _e(TITULO),
              "<p class=\"abertura\">%s</p>" % _e(ABERTURA)]
    n = 0
    for nome, achados in lentes:
        partes.append("<h2>%s — %d achado(s)</h2>" % (_e(nome), len(achados)))
        for a in achados:
            n += 1
            grav = _e(a.get("gravidade") or "media")
            partes.append(
                "<div class=\"achado\"><label>"
                "<input type=\"checkbox\" name=\"achado\" value=\"%d\">"
                "<span><strong>%s</strong><span class=\"grav %s\">%s</span></span>"
                "</label>"
                "<details><summary>%s</summary>"
                "<div class=\"onde\">%s · %s</div>"
                "<details><summary>%s</summary><pre>%s</pre></details>"
                "</details></div>"
                % (n, _e(a.get("o_que")), grav, grav, _e(CORPO), _e(a.get("onde")),
                   _e(a.get("regra")), _e(PROVA), _e(a.get("prova"))))
    partes.append("</main></body></html>")
    assert n == total, "a página perdeu achado no caminho: %d de %d" % (n, total)
    return "".join(partes)


def escreve(achados, saida):
    lentes = por_lente(achados)
    errs = erros_da_pagina(lentes)
    if errs:
        raise ValueError("o texto da página não passa na régua: " + "; ".join(errs))
    os.makedirs(saida, exist_ok=True)
    caminho = os.path.join(saida, "vistoria-%s.html"
                           % datetime.date.today().isoformat())
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(html_de(lentes, len(achados)))
    return caminho


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True,
                    help="onde gravar (obrigatório: destino adivinhado cai no cache "
                         "do plugin quando instalado)")
    args = ap.parse_args(argv)
    dados = json.load(sys.stdin)
    achados = dados.get("achados", dados) if isinstance(dados, dict) else dados
    print(escreve(achados, args.dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
