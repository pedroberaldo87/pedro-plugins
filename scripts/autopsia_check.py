#!/usr/bin/env python3
"""autopsia_check.py — a lei da autópsia deixa de ser só texto.

A skill `improve-workflow` carrega duas regras que hoje só existem em prosa: a
TRAVA que o segundo par de olhos aplica (com a ordem de derrubar) e a PROIBIÇÃO
de tocar arquivo do projeto durante a rodada. Prosa some numa reescrita e nada
acusa — a rodada seguinte fica sem refutador e com licença para editar.

Aqui as duas viram cobrança mecânica sobre o texto:

  A · as frases fixas estão no arquivo (a trava, a ordem, a proibição);
  B · nenhum bloco executável da skill escreve na árvore do projeto.

Uso:  python3 scripts/autopsia_check.py [caminho/do/SKILL.md]
Sai 1 com o achado impresso; 0 calado quando a lei está de pé.
"""

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_PADRAO = os.path.join(RAIZ, "plugins", "improve-workflow",
                            "skills", "improve-workflow", "SKILL.md")

# As frases são checadas em minúsculas: o texto as usa em negrito e no meio de
# frase, e o que não pode sumir é a REGRA, não a caixa das letras.
FRASES = [
    ("a trava de robustez",
     "reprove toda proposta que troque robustez por economia"),
    ("a ordem de derrubar", "tente derrubar cada afirmação"),
    ("a proibição de tocar o projeto",
     "nenhum arquivo do projeto muda durante a apura"),
]

# A isenção é do TOKEN que a prosa da skill declara — `<run>`, o run pedido pelo
# nome —, nunca do operador `>`. Isentar o operador (exigindo espaço antes dele)
# deixava passar `<plugin visual>`, que o shell lê como par de redirecionamentos.
DECLARADOS = ("<run>",)

# Mesma régua da bancada do plugin (`lib/test_improve_workflow_skill.py:sujeira`).
ESCRITA = ("git commit", "git add", "git checkout", "git stash",
           "rm ", "mv ", "tee ", r">>?\s*\S")

# Qualquer `<…>` que sobre depois de tirar os declarados é placeholder mudo: no
# bloco executável ele não é marcador inerte, é comando que o shell tenta rodar.
PLACEHOLDER = r"<[^<>\n]+>"


def checar(caminho):
    """Devolve a lista de achados (vazia = a lei está de pé)."""
    try:
        with open(caminho, encoding="utf-8") as f:
            texto = f.read()
    except OSError as e:
        return ["não deu para ler %s: %s" % (caminho, e)]

    achados = []
    baixo = texto.lower()
    for nome, frase in FRASES:
        if frase not in baixo:
            achados.append("%s:1 — sumiu do texto %s: %r" % (caminho, nome, frase))

    blocos = re.findall(r"```bash\n(.*?)```", texto, re.S)
    if not blocos:
        achados.append("%s:1 — a skill não tem bloco de comando (a rodada perdeu o corpo)"
                       % caminho)
    for bloco in blocos:
        # Some o token declarado sem mexer nas posições, para a linha continuar certa.
        limpo = bloco
        for token in DECLARADOS:
            limpo = limpo.replace(token, "_" * len(token))
        for padrao, queixa in ([(p, "escreve na árvore") for p in ESCRITA]
                               + [(PLACEHOLDER, "nomeia por placeholder mudo")]):
            m = re.search(padrao, limpo)
            if m:
                linha = texto[:texto.index(bloco) + m.start()].count("\n") + 1
                achados.append("%s:%d — bloco da rodada %s: %r"
                               % (caminho, linha, queixa, m.group(0)))
    return achados


def main(argv):
    caminho = argv[1] if len(argv) > 1 else SKILL_PADRAO
    if not os.path.exists(caminho):
        return 0                                  # fail-open: skill ausente não acusa
    achados = checar(caminho)
    if not achados:
        return 0
    print("A LEI DA AUTÓPSIA FUROU:")
    for a in achados:
        print("   " + a)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
