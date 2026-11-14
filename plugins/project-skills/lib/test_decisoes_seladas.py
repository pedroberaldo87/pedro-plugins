#!/usr/bin/env python3
"""O cobrador do registro de decisões seladas (F22.6 · R-32).

O critério do passo, literal: o registro existe com índice de UMA linha por
decisão, e quem vai perguntar o consulta antes — coberto por PERGUNTA REPETIDA
reproduzida, onde a segunda volta respondida do registro, sem chegar ao dono.

A jornada reproduzida aqui é a que parou 4 corridas em dias diferentes: alguém
pergunta, o dono responde, a resposta é selada — e a MESMA pergunta volta. Só a
chave exata (a frase selada, normalizada) é respondida do disco; a pergunta
reescrita vai ao dono COM a sugestão da fala selada ao lado (7fab4b4e: o registro
é um arquivo do repositório e não decide por casamento frouxo). O contador
`foi_ao_dono` é a prova: ele sobe quando a pergunta atravessa o registro.

    python3 plugins/project-skills/lib/test_decisoes_seladas.py
"""
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
REGISTRO = os.path.join(AQUI, "decisoes_seladas.py")

from decisoes_seladas import caminho, consultar, selar, sugerir  # noqa: E402

ok = falhas = 0


def checa(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


def cli(*args):
    r = subprocess.run([sys.executable, REGISTRO] + list(args),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60, stdin=subprocess.DEVNULL,
                       start_new_session=True)
    return r.returncode, r.stdout, r.stderr


raiz = tempfile.mkdtemp(prefix="seladas-")

# ── 1 · A PERGUNTA REPETIDA (o caminho que o passo cobra) ────────────────────
foi_ao_dono = []


sugestoes_vistas = []


def perguntar(pergunta, resposta_do_dono, fonte):
    """O rito completo: consulta o registro ANTES; só a chave exata responde. O que não achou
    vai ao dono — com as sugestões do registro na tela, para ele decidir."""
    achadas = consultar(raiz, pergunta)
    if achadas:
        return achadas[0], False
    sugestoes_vistas.append(sugerir(raiz, pergunta))
    foi_ao_dono.append(pergunta)
    selar(raiz, fala=resposta_do_dono, fonte=fonte, data="2026-08-19")
    return resposta_do_dono, True


FALA = "tudo que puder decidir no final, decido no final"

primeira, subiu1 = perguntar(
    "posso adiar a escolha do provedor de inferência para o final?",
    FALA, "colheita da execução 12")
checa("1ª pergunta chega ao dono (o registro está vazio)", subiu1, repr(primeira))

segunda, subiu2 = perguntar(
    "essa decisão do destino de deploy pode ficar para o final?",
    FALA, "outra corrida")
checa("2ª pergunta (reescrita) chega ao dono: o registro não responde por casamento frouxo",
      subiu2, repr(segunda))
checa("mas chega COM a fala selada como sugestão",
      len(sugestoes_vistas[-1]) == 1 and FALA in sugestoes_vistas[-1][0], repr(sugestoes_vistas))
terceira, subiu3 = perguntar(FALA, FALA, "a mesma frase, pela terceira vez")
checa("a chave exata NÃO chega ao dono", not subiu3, repr(terceira))
checa("a 3ª é respondida pela linha do registro", FALA in terceira, repr(terceira))
checa("o dono foi incomodado duas vezes, não três", len(foi_ao_dono) == 2, repr(foi_ao_dono))

# ── 2 · UMA LINHA POR DECISÃO, E A FRASE-CHAVE INTEIRA NELA ──────────────────
with open(caminho(raiz), encoding="utf-8") as fh:
    corpo = fh.read()
linhas = [ln for ln in corpo.splitlines() if ln.startswith("- [")]
checa("o registro existe no projeto, não no plugin",
      caminho(raiz).endswith(os.path.join(".claude", "decisoes-seladas.md")), caminho(raiz))
checa("índice de uma linha por decisão", len(linhas) == 1, repr(linhas))
checa("a frase-chave inteira mora numa linha só (o grep acha)",
      any(FALA in ln for ln in linhas), repr(linhas))

selar(raiz, fala=FALA, fonte="repetida de propósito")
checa("selar a mesma fala duas vezes não dobra a linha",
      len([ln for ln in open(caminho(raiz), encoding="utf-8") if ln.startswith("- [")]) == 1)

erro = None
try:
    selar(raiz, fala="uma metade\ne a outra metade", fonte="x")
except ValueError as e:
    erro = str(e)
checa("fala partida em duas linhas é recusada", erro is not None, repr(erro))

# ── 3 · PERGUNTA NOVA CONTINUA INDO AO DONO ─────────────────────────────────
nova, subiu_nova = perguntar("qual paleta de cor a tela de placar usa?",
                             "azul e branco", "conversa de hoje")
checa("pergunta que o registro não cobre chega ao dono", subiu_nova, repr(nova))
checa("e vai sem sugestão nenhuma", sugestoes_vistas[-1] == [], repr(sugestoes_vistas[-1]))
checa("duas decisões, duas linhas",
      len([ln for ln in open(caminho(raiz), encoding="utf-8") if ln.startswith("- [")]) == 2)

# ── 4 · A LINHA DE COMANDO (é por ela que hook e prompt consultam) ──────────
rc, saida, _ = cli("consultar", raiz, FALA)
checa("consultar por comando devolve 0 quando a chave exata já tem decisão", rc == 0, saida)
checa("e imprime a linha selada", FALA in saida, saida)

rc, saida, _ = cli("consultar", raiz, "dá pra decidir isso no final da corrida?")
checa("consultar por comando devolve 1 quando só há sugestão", rc == 1, saida)
checa("e imprime a sugestão marcada, sem passar por resposta",
      "SUGESTÃO" in saida and FALA in saida, saida)

rc, _, err = cli("consultar", raiz, "quantos servidores o cliente contratou?")
checa("consultar sem decisão devolve 1 (a pergunta segue ao dono)", rc == 1, err)

rc, saida, _ = cli("indice", raiz)
checa("o índice imprime uma linha por decisão",
      rc == 0 and len(saida.strip().splitlines()) == 2, repr(saida))

rc, _, err = cli("selar", raiz, "--fala", "   ", "--fonte", "nenhuma")
checa("selar decisão sem fala é recusado por comando", rc == 2, err)

# ── 5 · A CONSULTA ESTÁ LIGADA A QUEM PERGUNTA ──────────────────────────────
# Quem manda consultar antes de perguntar é a régua única (`regua-de-pergunta.md`),
# e ela é vendorada para o lado de cada skill que pergunta — inclusive o /sprint,
# onde mora o motor. Cópia sem a linha = papel que volta a perguntar duas vezes.
REGUAS = {
    "a fonte compartilhada": os.path.join(AQUI, "..", "..", "..", "_shared",
                                          "regua-de-pergunta.md"),
    "a cópia ao lado do motor do /sprint": os.path.join(
        AQUI, "..", "skills", "sprint", "regua-de-pergunta.md"),
}
for nome, arq in REGUAS.items():
    texto = open(arq, encoding="utf-8").read() if os.path.isfile(arq) else ""
    checa("%s manda consultar o registro antes de perguntar" % nome,
          "decisoes_seladas.py" in texto and "consultar" in texto, arq)
    checa("%s traz o comando de selar a resposta nova" % nome,
          "selar" in texto and "--fala" in texto, arq)

print("test_decisoes_seladas: %d ok, %d falha(s)" % (ok, falhas))
sys.exit(1 if falhas else 0)
