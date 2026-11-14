#!/usr/bin/env python3
"""O registro de decisões seladas só RESPONDE pela chave exata; o resto é sugestão (7fab4b4e · hsf_a03bf1f4).

O registro é um arquivo do repositório: num clone ele chega de fora. Casar a pergunta por
sobreposição de radicais deixava uma linha do repo responder pelo dono. Aqui:

- `consultar` devolve só a linha cuja frase-chave, normalizada (caixa, acento, pontuação), é a
  própria pergunta;
- o que casa de leve (a pergunta reescrita, a frase dentro de uma pergunta maior, a pergunta
  dentro de uma fala longa) sai de `sugerir`, que o chamador MOSTRA ao dono e nunca aplica;
- o pré-check põe a sugestão no achado e a pergunta segue ao dono;
- a linha de comando separa as duas coisas na saída, e a régua de pergunta diz isso a quem pergunta.

Roda com:  python3 plugins/project-skills/lib/test_decisoes_seladas_chave_exata.py
"""
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import decisoes_seladas as ds  # noqa: E402
import precheck_largada as pl  # noqa: E402

ok = falhas = 0
REGISTRO = os.path.join(AQUI, "decisoes_seladas.py")


def checa(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


def com_fala(fala):
    raiz = tempfile.mkdtemp(prefix="seladas-chave-")
    ds.selar(raiz, fala=fala, fonte="teste", data="2026-01-01")
    return raiz


def cli(*args):
    r = subprocess.run([sys.executable, REGISTRO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60, stdin=subprocess.DEVNULL,
                       start_new_session=True)
    return r.returncode, r.stdout, r.stderr


def sugerir(raiz, pergunta):
    fn = getattr(ds, "sugerir", None)
    return fn(raiz, pergunta) if fn else None


FALA = "tudo que puder decidir no final, decido no final"
raiz = com_fala(FALA)

print("== a chave exata responde")
checa("a frase exata responde", len(ds.consultar(raiz, FALA)) == 1)
checa("a frase exata, em maiúsculas, sem acento e sem a pontuação, responde",
      len(ds.consultar(raiz, "TUDO QUE PUDER DECIDIR NO FINAL DECIDO NO FINAL!")) == 1)

print("== o que casa de leve NÃO responde")
reescrita = "essa decisão do destino de deploy pode ficar para o final?"
checa("a pergunta reescrita com outras palavras não responde", ds.consultar(raiz, reescrita) == [],
      repr(ds.consultar(raiz, reescrita)))
maior = "lembra que " + FALA + "? posso adiar?"
checa("a frase dentro de uma pergunta maior não responde", ds.consultar(raiz, maior) == [],
      repr(ds.consultar(raiz, maior)))
r2 = com_fala("sempre que for apagar o banco de produção avisar antes de qualquer migração")
checa("a pergunta dentro de uma fala longa não responde",
      ds.consultar(r2, "apagar o banco de produção") == [])
r3 = com_fala("pode apagar o banco de produção sem perguntar")
checa("uma fala do repo não pré-responde a pergunta do dono por radicais comuns",
      ds.consultar(r3, "posso apagar o banco de produção agora?") == [])

print("== o que casa de leve vira SUGESTÃO")
sug = sugerir(raiz, reescrita) or [""]
checa("a pergunta reescrita sai como sugestão, com a fala dentro", FALA in sug[0], repr(sug))
checa("a frase dentro de uma pergunta maior sai como sugestão", len(sugerir(raiz, maior) or []) == 1)
checa("a pergunta que casa de leve com a fala do repo sai como sugestão",
      len(sugerir(r3, "posso apagar o banco de produção agora?") or []) == 1)
checa("a chave exata não repete como sugestão", sugerir(raiz, FALA) == [], repr(sugerir(raiz, FALA)))
checa("pergunta sem relação não gera sugestão",
      sugerir(raiz, "quantos servidores o cliente contratou?") == [])
checa("a sugestão não acrescenta nada ao registro",
      len(ds._linhas_de_decisao(raiz)) == 1)

print("== a linha de comando separa resposta de sugestão")
rc, saida, err = cli("consultar", raiz, FALA)
checa("exata: exit 0 e a linha, sem a palavra SUGESTÃO", rc == 0 and FALA in saida and "SUGESTÃO" not in saida,
      repr((rc, saida)))
rc, saida, err = cli("consultar", raiz, reescrita)
checa("reescrita: exit 1 (a pergunta segue ao dono)", rc == 1, repr((rc, saida, err)))
checa("reescrita: a fala sai marcada SUGESTÃO, dita como não-resposta",
      "SUGESTÃO" in saida and FALA in saida and "não é resposta" in saida, repr(saida))
rc, saida, err = cli("consultar", raiz, "quantos servidores o cliente contratou?")
checa("sem relação: exit 1 e nenhuma linha em stdout", rc == 1 and saida.strip() == "", repr((rc, saida)))

print("== o pré-check: sugestão acompanha a pergunta, só a chave exata a dispensa")
raiz4 = tempfile.mkdtemp(prefix="seladas-chave-pre-")
plano = {"phases": [{"id": "P1", "items": [
    {"id": "P1.3", "status": "todo", "desc": "publica o pacote no marketplace",
     "pronto": "o dono aprova o release e o plugin é publicado"},
]}]}
base = pl.passada1(plano, raiz4)
perguntas = base["perguntas"]
checa("há pergunta bloqueante na rodada de partida", bool(perguntas), repr(base["achados"]))
if perguntas:
    pergunta = perguntas[0]["pergunta"]
    # uma fala que só casa de leve com a pergunta: mesmas palavras, ordem e enchimento trocados
    leve = "decidi que " + " ".join(reversed(pergunta.replace("?", "").split())) + " pode seguir"
    ds.selar(raiz4, fala=leve, fonte="teste", data="2026-01-02")
    r = pl.passada1(plano, raiz4)
    ainda = [a for a in r["perguntas"] if a["pergunta"] == pergunta]
    checa("fala que casa de leve NÃO dispensa a pergunta", len(ainda) == 1,
          repr([a for a in r["registrados"] if a.get("respondida_por")]))
    checa("a pergunta carrega a sugestão para o dono ver",
          bool(ainda) and any(leve in s for s in ainda[0].get("sugestao_selada", [])),
          repr(ainda[:1]))
    checa("a sugestão não vira respondida_por",
          bool(ainda) and not ainda[0].get("respondida_por"))
    ds.selar(raiz4, fala=pergunta, fonte="teste", data="2026-01-03")
    r = pl.passada1(plano, raiz4)
    checa("a chave exata dispensa a pergunta",
          not [a for a in r["perguntas"] if a["pergunta"] == pergunta])

print("== a régua de pergunta diz a quem pergunta")
for nome, arq in (("a fonte compartilhada", os.path.join(AQUI, "..", "..", "..", "_shared",
                                                          "regua-de-pergunta.md")),
                  ("a cópia do /sprint", os.path.join(AQUI, "..", "skills", "sprint",
                                                      "regua-de-pergunta.md"))):
    texto = open(arq, encoding="utf-8").read() if os.path.isfile(arq) else ""
    checa("%s: só a chave exata responde" % nome, "chave exata" in texto, arq)
    checa("%s: a sugestão se mostra ao dono, não se aplica" % nome,
          "SUGESTÃO" in texto and "não é resposta" in texto, arq)

print("\n%d ok, %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
