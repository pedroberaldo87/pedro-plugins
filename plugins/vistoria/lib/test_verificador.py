#!/usr/bin/env python3
"""Suíte do verificador — o segundo agente que tenta DERRUBAR o achado.

O ponto do passo é este: o validador do schema (`lib/achado.py`) garante que o achado
tem prova colada, nunca que a prova é VERDADEIRA. Os dois casos aqui passam inteiros
pelo validador — e só um deles sobrevive ao verificador.

  1. achado plantado falso — citação que não existe no arquivo citado → derrubado,
     motivo 'citação não encontrada';
  2. achado da fixture a — as duas citações batem no disco e o `guard.sh` roda de
     verdade e recusa → CONFIRMADO.

    python3 plugins/vistoria/lib/test_verificador.py

stdlib only (requisito do repo).
"""

import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from achado import achado, erros_de_achado  # noqa: E402

PLUGIN = os.path.dirname(AQUI)
PAUTA = os.path.join(PLUGIN, "skills", "vistoria", "references", "pauta-verificador.md")

CITACAO = re.compile(r"^\s*([\w./-]+\.\w+):(\d+):?\s?(.*)$")

falhas = []


def checa(nome, cond, detalhe=""):
    print("  %s %s%s" % ("ok  " if cond else "FALHA", nome,
                         "" if cond else " — " + detalhe))
    if not cond:
        falhas.append(nome)


def citacoes(a):
    """As citações 'arquivo:linha: trecho' que o achado cola em `onde` e `prova`."""
    achadas = []
    for campo in ("onde", "prova"):
        for linha in str(a.get(campo, "")).splitlines():
            m = CITACAO.match(linha)
            if m:
                achadas.append((m.group(1), int(m.group(2)), m.group(3).strip()))
    return achadas


def verifica(a, raiz, entrada=None):
    """V1 e V2 da pauta do verificador: (veredito, motivo).

    O verificador recebe SÓ o achado e os arquivos citados — nada do contexto do leitor.
    """
    errs = erros_de_achado(a)
    if errs:
        return "derrubado", "achado inválido: " + "; ".join(errs)

    citadas = citacoes(a)
    if not citadas:
        return "derrubado", "citação não encontrada: o achado não cola arquivo:linha"

    # V1 — a citação existe mesmo no arquivo citado?
    for arquivo, numero, trecho in citadas:
        caminho = os.path.join(raiz, arquivo)
        if not os.path.exists(caminho):
            return "derrubado", "citação não encontrada: %s não existe" % arquivo
        linhas = open(caminho, encoding="utf-8").read().splitlines()
        if numero < 1 or numero > len(linhas):
            return "derrubado", "citação não encontrada: %s:%d fora do arquivo" % (arquivo, numero)
        if trecho and trecho not in linhas[numero - 1]:
            return "derrubado", "citação não encontrada: %s:%d não contém %r" % (arquivo, numero, trecho)

    # V2 — o programa acusado recusa mesmo? Roda, não lê.
    if entrada is not None:
        for arquivo, _n, _t in citadas:
            if arquivo.endswith(".sh"):
                saida = subprocess.run(["bash", os.path.join(raiz, arquivo), entrada],
                                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                                       stdin=subprocess.DEVNULL, start_new_session=True)
                if saida.returncode == 0:
                    return "derrubado", "o programa citado não recusa: %s saiu 0" % arquivo

    return "CONFIRMADO", ""


ACHADO_FALSO = achado(
    cobrador="leitor",
    regra="P1-instrucao-recusada",
    gravidade="alta",
    onde="fixtures/a/SKILL.md:11",
    o_que="a instrução manda esperar a suíte e o guard recusa a espera",
    prova=('fixtures/a/SKILL.md:11: Antes de responder, rode a suíte inteira\n'
           'fixtures/a/guard.sh:10:     echo "recusado: interromper a espera é obrigatório" >&2'),
)

ACHADO_A = achado(
    cobrador="leitor",
    regra="P1-instrucao-recusada",
    gravidade="alta",
    onde="fixtures/a/SKILL.md:11",
    o_que="a instrução manda esperar a suíte terminar; o guard.sh ao lado recusa a espera",
    prova=('fixtures/a/SKILL.md:11: Antes de responder, rode a suíte inteira e '
           '**espere ela terminar**. Só depois de a\n'
           'fixtures/a/guard.sh:10:     echo "recusado: esperar a suíte terminar é '
           'proibido nesta sessão" >&2'),
)

ENTRADA_A = "rode a suíte inteira e espere ela terminar"


def main():
    print("Verificador")
    checa("a pauta do verificador existe", os.path.exists(PAUTA), PAUTA)

    # Os dois achados são bem formados: o schema não separa o falso do verdadeiro.
    checa("o achado plantado falso passa pelo validador do schema",
          not erros_de_achado(ACHADO_FALSO), str(erros_de_achado(ACHADO_FALSO)))
    checa("o achado da fixture a passa pelo validador do schema",
          not erros_de_achado(ACHADO_A), str(erros_de_achado(ACHADO_A)))

    veredito, motivo = verifica(ACHADO_FALSO, PLUGIN, entrada=ENTRADA_A)
    checa("o achado plantado falso é derrubado", veredito == "derrubado", veredito)
    checa("o motivo da queda é 'citação não encontrada'",
          motivo.startswith("citação não encontrada"), motivo)

    veredito, motivo = verifica(ACHADO_A, PLUGIN, entrada=ENTRADA_A)
    checa("o achado da fixture a sobrevive como CONFIRMADO",
          veredito == "CONFIRMADO", "%s — %s" % (veredito, motivo))

    # O verificador RODA o guard: com entrada que o guard deixa passar, o achado cai.
    veredito, motivo = verifica(ACHADO_A, PLUGIN, entrada="rode o lint")
    checa("achado cai quando o programa citado não recusa a entrada",
          veredito == "derrubado" and motivo.startswith("o programa citado não recusa"),
          "%s — %s" % (veredito, motivo))

    print("\n%s (%d falha(s))" % ("VERDE" if not falhas else "VERMELHO", len(falhas)))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
