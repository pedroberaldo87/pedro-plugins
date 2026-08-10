#!/usr/bin/env python3
"""Suíte do fecho_check — as fixtures REPRODUZEM as falhas que motivaram a skill.

A mais importante é `sessao_que_falhou`: sete peças entregues, zero vereditos. Se esta
suíte deixasse de pegá-la, a skill inteira perderia o motivo de existir — por isso ela
é o primeiro caso, e por isso existe também uma fixture SAUDÁVEL: sem ela, a suíte
passaria por vacuidade, acusando tudo.

    python3 plugins/gauntlet/lib/test_fecho_check.py
"""

import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fecho_check as fc  # noqa: E402

FAILS = []


def check(label, cond):
    print(("  ok   " if cond else "  FAIL ") + label)
    if not cond:
        FAILS.append(label)


def escreve(caminho, dado):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as fh:
        if isinstance(dado, (dict, list)):
            json.dump(dado, fh, ensure_ascii=False, indent=1)
        else:
            fh.write(dado)


def monta_missao(raiz, pecas=("hero",), com_veredito=True, aprovado=True):
    """A missão saudável mínima. Cada teste a estraga de um jeito só.

    A OBRA nasce FORA do diretório da missão, como numa missão de verdade: obra dentro
    da missão escondia que a base do caminho estava sendo adivinhada.
    """
    m = os.path.join(raiz, "missao")
    projeto = os.path.join(raiz, "projeto")
    os.makedirs(projeto, exist_ok=True)
    escreve(os.path.join(m, "recon", "registros", "alvo-hero.png"), "PIXELS-DO-ALVO")
    # A ficha ENXUTA (decisão do dono, 2026-08-09): só o essencial é obrigatório.
    # `lei` é opcional — o modo com constituição entra por ela.
    escreve(os.path.join(m, "rito.json"), {
        "objetivo": "bater o alvo em acabamento",
        "alvos": ["https://exemplo.invalid"],
        "sonda": {"preparar": "servir", "registrar": "printar", "alvo": "abrir a url",
                  "teste_registro": "recon/registros/alvo-hero.png"},
        "eixos": [{"nome": "ritmo da entrada", "gesto": "rolar ate o fim",
                   "registro": "recon/registros/alvo-hero.png"}],
        "lei": ["a mensagem aprovada é intocável"],
        "orcamento": {"rodadas_por_peca": 3, "teto_de_pecas": 4},
        "raiz": projeto,
    })
    escreve(os.path.join(m, "decomposicao.json"), {
        "pecas": [{"id": p, "eixos": ["ritmo da entrada"], "arquivos": ["src/%s.ts" % p]}
                  for p in pecas],
    })
    viu = {}
    for p in pecas:
        r1 = os.path.join(m, "pecas", p, "r1")
        obra = os.path.join(projeto, "obra-%s.txt" % p)
        escreve(obra, "a obra de %s, versao 1" % p)
        escreve(os.path.join(r1, "nosso.png"), "PIXELS-NOSSOS-%s" % p)
        escreve(os.path.join(r1, "alvo.png"), "PIXELS-DO-ALVO")
        # A entrega é ALEGAÇÃO do construtor: caminho + marca de cada artefato.
        escreve(os.path.join(r1, "entrega.json"), {
            "peca": p, "rodada": 1, "resumo": "a primeira passada",
            # O orgulho é aspiração de briefing, nunca contrato — a fixture o traz
            # porque o construtor saudável o escreve, não porque o fecho o exija.
            "orgulho": "a entrada respira antes de falar, coisa que o alvo não faz",
            "artefatos": [{"caminho": "obra-%s.txt" % p, "marca": fc.marca(obra)}],
        })
        cam_e = os.path.join(r1, "entrega.json")
        viu[p] = fc.marca(cam_e)
        if com_veredito:
            escreve(os.path.join(r1, "veredito.json"), {
                "peca": p, "rodada": 1,
                "status": "aprovado" if aprovado else "reprovado",
                # Aprovar É a declaração de impressão: o juiz diz que ficou
                # boquiaberto e o diz em frase de gente, ou o fecho recusa.
                "impressionado": bool(aprovado),
                "frase": "a nossa entrada respira melhor que a do alvo" if aprovado else "",
                "eixo": "ritmo da entrada",
                "gap": "" if aprovado else "a entrada do alvo respira mais",
                "entrega": fc.marca(cam_e),
                "registros": {"nosso": "pecas/%s/r1/nosso.png" % p,
                              "alvo": "pecas/%s/r1/alvo.png" % p},
            })
    escreve(os.path.join(m, "diretor.json"), {
        "status": "aprovado",
        # A barra do juiz de peça, no conjunto: o diretor também declara impressão.
        "impressionado": True,
        "frase": "o conjunto tem uma mão só, e ela é mais firme que a do alvo",
        "viu": viu,
    })
    # A missão passou pela abertura: a régua fica ancorada, e mudá-la depois é acusado.
    escreve(os.path.join(m, "rito-aprovado.marca"), fc.marca(os.path.join(m, "rito.json")))
    return m


def tmp():
    d = tempfile.mkdtemp(prefix="gauntlet-fix-")
    return d


print("O CHÃO — a fixture saudável passa (senão a suíte acusa tudo por vacuidade)")
d = tmp()
m = monta_missao(d)
check("rito completo não tem furo", fc.erros_do_rito(m) == [])
check("missão saudável fecha", fc.erros_do_fecho(m) == [])
shutil.rmtree(d)

print()
print("RÉGUA, NUNCA RECEITA — eixo com medida no nome é o vetor da cópia")
d = tmp()
m = monta_missao(d)
rito = json.load(open(os.path.join(m, "rito.json")))
rito["eixos"].append({"nome": "a página mora numa moldura de 32px",
                      "gesto": "printar o topo",
                      "registro": "recon/registros/alvo-hero.png"})
escreve(os.path.join(m, "rito.json"), rito)
furos = fc.erros_do_rito(m)
check("o rito recusa o eixo com medida no nome",
      any("MEDIDA no nome" in f for f in furos))
rito["eixos"][-1]["nome"] = "a página inteira mora dentro de uma moldura"
rito["eixos"][-1]["numero"] = "moldura de 32px medida no alvo"
escreve(os.path.join(m, "rito.json"), rito)
check("o mesmo número no campo `numero` passa — lá ele é prova de nível",
      fc.erros_do_rito(m) == [])
shutil.rmtree(d)

print()
print("A FALHA CENTRAL — sete peças entregues, zero juízes")
d = tmp()
sete = ("hero", "marcas", "contato", "precos", "rodape", "menu", "prova")
m = monta_missao(d, pecas=sete, com_veredito=False)
furos = fc.erros_do_fecho(m)
check("o fecho é recusado", furos != [])
check("as SETE peças são nomeadas, uma a uma",
      sum(1 for f in furos if "não há veredito" in f) == 7)
mapa = fc.desenha_mapa(m)
check("o mapa diz 'entregue, SEM JUÍZO' em cada uma",
      mapa.count("entregue, SEM JUÍZO") == 7)
shutil.rmtree(d)

print()
print("O JULGAMENTO SEM PROVA — cada forma de burlar o par de registros")
d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
del dado["registros"]["alvo"]
escreve(v, dado)
check("veredito com um registro só é nulo",
      any("par de registros" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["registros"]["alvo"] = dado["registros"]["nosso"]
escreve(v, dado)
check("o mesmo arquivo nos dois lados é acusado",
      any("não houve comparação" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
escreve(os.path.join(m, "pecas", "hero", "r1", "alvo.png"), "PIXELS-NOSSOS-hero")
check("dois arquivos diferentes com o mesmo conteúdo são acusados",
      any("mesmo conteúdo" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
escreve(os.path.join(m, "pecas", "hero", "r1", "nosso.png"), "")
check("registro vazio é acusado",
      any("está vazio" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("A OBRA EM MOVIMENTO — julgar o que já não existe")
d = tmp()
m = monta_missao(d)
escreve(os.path.join(os.path.dirname(m), "projeto", "obra-hero.txt"), "versao 2")
check("obra alterada depois do juízo é acusada",
      any("mudou depois de julgado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
os.remove(os.path.join(os.path.dirname(m), "projeto", "obra-hero.txt"))
check("artefato que sumiu é acusado",
      any("sumiu" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
os.remove(os.path.join(m, "pecas", "hero", "r1", "entrega.json"))
check("veredito sem manifesto de entrega é acusado",
      any("não há manifesto" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["entrega"] = "0000000000000000"
escreve(v, dado)
check("veredito ancorado em OUTRA entrega é acusado como requentado",
      any("requentado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
e = os.path.join(m, "pecas", "hero", "r1", "entrega.json")
dado = json.load(open(e, encoding="utf-8"))
dado["artefatos"][0]["marca"] = "0000000000000000"
escreve(e, dado)
check("construtor que MENTE no manifesto é pego pela recomputação",
      any("mudou depois de julgado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("O DEFEITO ENTRE PEÇAS — o eixo que ninguém possui")
d = tmp()
m = monta_missao(d)
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["eixos"].append({"nome": "consistencia tipografica", "gesto": "medir os dois",
                      "registro": "recon/registros/alvo-hero.png"})
escreve(os.path.join(m, "rito.json"), rito)
escreve(os.path.join(m, "rito-aprovado.marca"), fc.marca(os.path.join(m, "rito.json")))
check("eixo que nenhuma peça possui é acusado",
      any("eixo sem dono" in f for f in fc.erros_do_fecho(m)))
d2 = json.load(open(os.path.join(m, "decomposicao.json"), encoding="utf-8"))
d2["eixos_do_diretor"] = ["consistencia tipografica"]
escreve(os.path.join(m, "decomposicao.json"), d2)
check("o mesmo eixo, dado ao diretor, deixa de ser furo",
      not any("eixo sem dono" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("O VETO DO DONO — o aprovado que evaporaria em silêncio")
d = tmp()
m = monta_missao(d)
fechadas, desconhecidas = fc.grava_veto(m, "tira a animacao", ["hero"])
check("o programa avisa que o veto toca coisa JÁ FECHADA", fechadas == ["hero"])
check("e não inventa peça que a decomposição não conhece",
      fc.grava_veto(m, "outro", ["nao-existe"])[1] == ["nao-existe"])
check("veto sobre peça fechada, sem retrabalho, recusa o fecho",
      any("não foi retrabalhado" in f for f in fc.erros_do_fecho(m)))
vetos = [json.loads(ln) for ln in open(os.path.join(m, "vetos.jsonl"), encoding="utf-8")]
vetos[0]["mantido"] = True
escreve(os.path.join(m, "vetos.jsonl"),
        "\n".join(json.dumps(v, ensure_ascii=False) for v in vetos) + "\n")
check("o dono dizendo `mantém` fecha o assunto",
      not any("não foi retrabalhado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("A RENDIÇÃO — `marginal` é relato, e não fecha peça com rodada sobrando")
d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["status"] = "marginal"
dado["impressionado"] = False
dado["gap"] = "o que sobra e ganho pequeno demais"
escreve(v, dado)
# A fixture dá 3 rodadas por peça e só 1 foi usada: fechar aqui é a rendição medida
# em 2026-08-09 (duas peças fechadas na rodada 1 de 4, com 45% do orçamento intacto).
furos = fc.erros_do_fecho(m)
check("`marginal` com rodada sobrando é recusado nomeando a peça",
      any("hero" in f and "não fecha peça" in f for f in furos))
check("e a recusa manda propor caminho NOVO",
      any("caminho NOVO" in f for f in furos))
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["orcamento"]["rodadas_por_peca"] = 1
escreve(os.path.join(m, "rito.json"), rito)
escreve(os.path.join(m, "rito-aprovado.marca"), fc.marca(os.path.join(m, "rito.json")))
check("com o orçamento esgotado, o mesmo `marginal` fecha — é a única saída dele",
      fc.erros_do_fecho(m) == [])
dado["gap"] = ""
escreve(v, dado)
check("mas `marginal` sem dizer o gap é acusado",
      any("reprovou sem dizer o gap" in f for f in fc.erros_do_fecho(m)))
dado["status"] = "quase la"
dado["gap"] = "x"
escreve(v, dado)
check("status fora do vocabulário é acusado",
      any("não diz aprovado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("O JUIZ BOQUIABERTO — aprovar É a declaração de impressão")
d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
del dado["impressionado"]
escreve(v, dado)
check("veredito sem `impressionado` é recusado com mensagem que o nomeia",
      any("não declara `impressionado`" in f for f in fc.erros_do_fecho(m)))
dado["impressionado"] = False
escreve(v, dado)
check("aprovado com `impressionado: false` é contradição acusada",
      any("aprovou sem estar boquiaberto" in f for f in fc.erros_do_fecho(m)))
dado["impressionado"] = True
del dado["frase"]
escreve(v, dado)
check("aprovado sem a frase de gente é recusado",
      any("falta a `frase`" in f for f in fc.erros_do_fecho(m)))
dado["frase"] = "a nossa entrada respira melhor que a do alvo"
dado["impressionado"] = "sim"
escreve(v, dado)
check("`impressionado` que não é true/false é acusado",
      any("true ou false" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("DADO MALFORMADO — recusa com mensagem, nunca com estouro")
# Os três payloads reais que estouravam TypeError na missão de 2026-08-09:
# registros.nosso como lista, eixo como bloco, gap como bloco.
d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["registros"]["nosso"] = ["pecas/hero/r1/nosso.png", "pecas/hero/r1/outro.png"]
escreve(v, dado)
try:
    furos = fc.erros_do_fecho(m)
    check("registros.nosso como LISTA recusa com mensagem",
          any("registros.nosso" in f and "não é texto" in f for f in furos))
except TypeError:
    check("registros.nosso como LISTA recusa com mensagem", False)
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["status"] = "reprovado"
dado["impressionado"] = False
dado["eixo"] = {"nome": "ritmo da entrada"}
dado["gap"] = {"texto": "a entrada do alvo respira mais"}
escreve(v, dado)
try:
    furos = fc.erros_do_fecho(m)
    check("eixo como BLOCO recusa com mensagem",
          any("`eixo` do veredito não é texto" in f for f in furos))
    check("gap como BLOCO recusa com mensagem",
          any("`gap` do veredito não é texto" in f for f in furos))
except TypeError:
    check("eixo como BLOCO recusa com mensagem", False)
    check("gap como BLOCO recusa com mensagem", False)
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
escreve(v, ["nao", "sou", "um", "bloco"])
check("veredito que não é bloco nenhum recusa com mensagem",
      any("não é um bloco de campos" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("O DIRETOR — o conjunto")
d = tmp()
m = monta_missao(d)
os.remove(os.path.join(m, "diretor.json"))
check("sem o diretor o fecho é recusado",
      any("não passou pelo conjunto" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

# "Each sub-agent utterly wowed" vale no CONJUNTO: diretor aprovando morno é a barra
# fatiada voltando pela última porta — cada peça boquiaberta e a missão fechando "no
# nível". A mesma exigência do juiz de peça, agora nele.
d = tmp()
m = monta_missao(d)
dj = json.load(open(os.path.join(m, "diretor.json"), encoding="utf-8"))
del dj["impressionado"]
escreve(os.path.join(m, "diretor.json"), dj)
check("diretor que aprova sem declarar impressão é recusado",
      any("diretor aprovou o conjunto sem declarar" in f for f in fc.erros_do_fecho(m)))
dj["impressionado"] = True
del dj["frase"]
escreve(os.path.join(m, "diretor.json"), dj)
check("diretor impressionado sem a frase de gente é recusado",
      any("falta a `frase` do diretor" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("O ORGULHO DO CONSTRUTOR — aspiração de briefing, nunca papelada de fecho")
# Régua do original: "never let the builder grade itself" — a autoavaliação do
# construtor não é contrato, e entrega sem o campo NÃO é recusada.
d = tmp()
m = monta_missao(d)
e = os.path.join(m, "pecas", "hero", "r1", "entrega.json")
ent = json.load(open(e, encoding="utf-8"))
del ent["orgulho"]
escreve(e, ent)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
ver = json.load(open(v, encoding="utf-8"))
ver["entrega"] = fc.marca(e)
escreve(v, ver)
escreve(os.path.join(m, "diretor.json"),
        {"status": "aprovado", "impressionado": True, "frase": "uma mão só",
         "viu": {"hero": fc.marca(e)}})
check("entrega sem `orgulho` fecha normalmente — quem julga é o crítico, nunca o autor",
      fc.erros_do_fecho(m) == [])
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
escreve(os.path.join(m, "diretor.json"),
        {"status": "aprovado", "impressionado": True, "frase": "uma mão só",
         "viu": {"hero": "0000000000000000"}})
check("diretor que olhou versão superada é acusado — sem relógio nenhum",
      any("versão superada" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("A ABERTURA — nada resolvido em tempo de execução")
d = tmp()
m = monta_missao(d)
for campo in ("alvos", "sonda", "eixos"):
    rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
    del rito[campo]
    p = os.path.join(d, "so-%s" % campo)
    os.makedirs(p, exist_ok=True)
    escreve(os.path.join(p, "rito.json"), rito)
    check("sem `%s` a missão não começa" % campo,
          any("sem `%s` não há gauntlet" % campo in f for f in fc.erros_do_rito(p)))
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
del rito["sonda"]["registrar"]
p = os.path.join(d, "sonda-manca")
os.makedirs(p, exist_ok=True)
escreve(os.path.join(p, "rito.json"), rito)
check("sonda sem o comando que produz o registro é acusada",
      any("a sonda não declara `registrar`" in f for f in fc.erros_do_rito(p)))
# Achado no piloto: peça que já é observável (um documento) não tem o que preparar, e
# exigir comando ali faria o dono inventar um.
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["sonda"]["preparar"] = ""
p4 = os.path.join(d, "preparar-vazio")
os.makedirs(p4, exist_ok=True)
escreve(os.path.join(p4, "rito.json"), rito)
os.makedirs(os.path.join(p4, "recon", "registros"), exist_ok=True)
escreve(os.path.join(p4, "recon", "registros", "alvo-hero.png"), "PIXELS")
check("`preparar` vazio passa — documento já é observável",
      not any("preparar" in f for f in fc.erros_do_rito(p4)))
rito2 = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito2["sonda"]["registrar"] = ""
p5 = os.path.join(d, "registrar-vazio")
os.makedirs(p5, exist_ok=True)
escreve(os.path.join(p5, "rito.json"), rito2)
check("mas `registrar` vazio é acusado — sem ele não há par",
      any("não há par" in f for f in fc.erros_do_rito(p5)))
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["eixos"][0]["registro"] = "recon/registros/nao-existe.png"
p = os.path.join(d, "eixo-sem-prova")
os.makedirs(p, exist_ok=True)
escreve(os.path.join(p, "rito.json"), rito)
check("eixo cujo registro não está no disco é acusado",
      any("não está no disco" in f for f in fc.erros_do_rito(p)))
# Aconteceu de verdade: o reconhecimento gravou o caminho ABSOLUTO, e com ele foi o nome
# da conta da máquina para um arquivo do projeto. O arquivo existe — e é por isso que só
# procurar no disco não acusava nada.
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["eixos"][0]["registro"] = os.path.join(m, "recon", "registros", "alvo-hero.png")
p6 = os.path.join(d, "eixo-com-caminho-absoluto")
os.makedirs(p6, exist_ok=True)
escreve(os.path.join(p6, "rito.json"), rito)
escreve(os.path.join(p6, "recon", "registros", "alvo-hero.png"), "PIXELS")
check("eixo com registro em caminho absoluto é acusado, mesmo com o arquivo no disco",
      any("é caminho absoluto" in f for f in fc.erros_do_rito(p6)))
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["eixos"][0]["registro"] = "../fora/alvo-hero.png"
p7 = os.path.join(d, "eixo-fora-da-missao")
os.makedirs(p7, exist_ok=True)
escreve(os.path.join(p7, "rito.json"), rito)
escreve(os.path.join(d, "fora", "alvo-hero.png"), "PIXELS")
check("e o registro que sai da missão por `..` também é acusado",
      any("aponta para fora da missão" in f for f in fc.erros_do_rito(p7)))
# O contraditório: o caminho relativo bem-formado é ACHADO, senão a recusa acima seria
# só severidade e não discriminação.
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
p8 = os.path.join(d, "eixo-relativo")
os.makedirs(p8, exist_ok=True)
escreve(os.path.join(p8, "rito.json"), rito)
escreve(os.path.join(p8, "recon", "registros", "alvo-hero.png"), "PIXELS")
check("o registro relativo à missão é achado pelo conferidor",
      not any("registro do eixo" in f for f in fc.erros_do_rito(p8)))
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
del rito["sonda"]["teste_registro"]
p2 = os.path.join(d, "sonda-nao-testada")
os.makedirs(p2, exist_ok=True)
escreve(os.path.join(p2, "rito.json"), rito)
check("sonda que nunca rodou é acusada — o teste dela é um registro no disco",
      any("não foi testada" in f for f in fc.erros_do_rito(p2)))
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
p3 = os.path.join(d, "sonda-muda")
os.makedirs(p3, exist_ok=True)
escreve(os.path.join(p3, "rito.json"), rito)
escreve(os.path.join(p3, "recon", "registros", "alvo-hero.png"), "")
check("sonda que rodou e não produziu nada é acusada",
      any("não produziu registro" in f for f in fc.erros_do_rito(p3)))
sinal = os.path.join(d, "ativo")
escreve(sinal, "")
check("segunda missão com uma de pé é recusada",
      any("já há uma missão de pé" in f for f in fc.erros_do_rito(m, sinal)))
check("e sem o sinal aceso a mesma missão passa", fc.erros_do_rito(m, sinal + "-x") == [])
# A ficha enxuta (decisão do dono, 2026-08-09): a fixture saudável já não traz `tipo`,
# `congelado`, `liberado` nem `material` — o chão prova que sem eles a missão começa.
# O que este caso acrescenta: `lei` também é opcional, e a disputa LIVRE passa sem ela.
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
del rito["lei"]
p9 = os.path.join(d, "disputa-livre")
os.makedirs(p9, exist_ok=True)
escreve(os.path.join(p9, "rito.json"), rito)
escreve(os.path.join(p9, "recon", "registros", "alvo-hero.png"), "PIXELS-DO-ALVO")
check("disputa livre — rito sem `lei` — passa a abertura",
      fc.erros_do_rito(p9) == [])
shutil.rmtree(d)

print()
print("PENDENTES — a foto da falha central tirada EM VOO, para a trava do guarda")
d = tmp()
m = monta_missao(d, pecas=("hero", "marcas"), com_veredito=False)
check("entrega sem veredito entra na lista, peça a peça",
      fc.pecas_pendentes(m) == ["hero", "marcas"])
shutil.rmtree(d)

d = tmp()
m = monta_missao(d, pecas=("hero", "marcas"))
check("peça julgada não é pendência", fc.pecas_pendentes(m) == [])
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["status"] = "quase la"
escreve(v, dado)
check("veredito com status fora do vocabulário conta como SEM juiz",
      fc.pecas_pendentes(m) == ["hero"])
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
shutil.rmtree(os.path.join(m, "pecas", "hero"))
check("peça sem rodada nenhuma não é pendência — ainda não houve entrega",
      fc.pecas_pendentes(m) == [])
check("missão sem decomposição devolve lista vazia — fail-open do guarda",
      fc.pecas_pendentes(os.path.join(d, "nao-existe")) == [])
shutil.rmtree(d)

print()
print("A RODADA INTERMEDIÁRIA — a entrega sem juiz que a rodada seguinte encobria")
d = tmp()
m = monta_missao(d)
# r1 fica entregue e SEM veredito; r2 nasce entregue e julgada, como se o construtor
# tivesse seguido em frente. Medido em 2026-08-09: o fecho dizia "todo pedaço julgado".
r1 = os.path.join(m, "pecas", "hero", "r1")
r2 = os.path.join(m, "pecas", "hero", "r2")
shutil.copytree(r1, r2)
os.remove(os.path.join(r1, "veredito.json"))
check("a rodada entregue e não julgada é acusada, mesmo com a seguinte aprovada",
      any("nenhum juiz a julgou" in f for f in fc.erros_do_fecho(m)))
check("e a trava enxerga a peça em voo, em vez de achar que está tudo julgado",
      fc.pecas_pendentes(m) == ["hero"])
shutil.rmtree(d)

# O contraditório: no laço NORMAL toda rodada anterior foi reprovada, e reprovar é
# gravar veredito — então este check não pode acusar a missão de várias rodadas.
d = tmp()
m = monta_missao(d)
r1 = os.path.join(m, "pecas", "hero", "r1")
r2 = os.path.join(m, "pecas", "hero", "r2")
shutil.copytree(r1, r2)
for cam, num in ((r1, 1), (r2, 2)):
    ent = json.load(open(os.path.join(cam, "entrega.json"), encoding="utf-8"))
    ent["rodada"] = num
    escreve(os.path.join(cam, "entrega.json"), ent)
    ver = json.load(open(os.path.join(cam, "veredito.json"), encoding="utf-8"))
    ver["rodada"] = num
    ver["entrega"] = fc.marca(os.path.join(cam, "entrega.json"))
    ver["registros"] = {"nosso": "pecas/hero/r%d/nosso.png" % num,
                        "alvo": "pecas/hero/r%d/alvo.png" % num}
    if num == 1:
        ver["status"] = "reprovado"
        ver["gap"] = "a entrada do alvo respira mais"
    escreve(os.path.join(cam, "veredito.json"), ver)
escreve(os.path.join(m, "diretor.json"),
        {"status": "aprovado", "impressionado": True, "frase": "uma mão só",
         "viu": {"hero": fc.marca(os.path.join(r2, "entrega.json"))}})
check("mas a rodada reprovada e depois consertada fecha normalmente",
      fc.erros_do_fecho(m) == [])
shutil.rmtree(d)

print()
print("A RODADA TRANSPLANTADA — o caminho mais barato de fraude")
d = tmp()
m = monta_missao(d, pecas=("hero", "marcas"))
shutil.rmtree(os.path.join(m, "pecas", "hero", "r1"))
shutil.copytree(os.path.join(m, "pecas", "marcas", "r1"),
                os.path.join(m, "pecas", "hero", "r1"))
check("rodada copiada de outra peça é acusada — a âncora vem junto, o nome não",
      any("transplantado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["rodada"] = 7
escreve(v, dado)
check("veredito que diz ser de outra rodada é acusado",
      any("diz ser da rodada" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("A PEÇA QUE SAIU DA DECOMPOSIÇÃO — o reprovado que evaporaria por outra porta")
d = tmp()
m = monta_missao(d, pecas=("hero", "marcas"), aprovado=False)
dec = json.load(open(os.path.join(m, "decomposicao.json"), encoding="utf-8"))
dec["pecas"] = [p for p in dec["pecas"] if p["id"] != "hero"]
escreve(os.path.join(m, "decomposicao.json"), dec)
check("trabalho no disco que a decomposição não conhece mais é acusado",
      any("não a conhece mais" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("A RÉGUA — ela não pode mudar no meio da missão")
d = tmp()
m = monta_missao(d)
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["eixos"] = []
escreve(os.path.join(m, "rito.json"), rito)
check("tirar um eixo depois de julgado é acusado — a barra não se rebaixa calada",
      any("a régua mudou" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
os.remove(os.path.join(m, "rito-aprovado.marca"))
check("missão que nunca passou pela abertura é acusada",
      any("nunca passou pela abertura" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("A LEI EM DOCUMENTO — ela mora fora do rito, e a âncora do rito não a cobre")
d = tmp()
m = monta_missao(d)
lei_doc = os.path.join(os.path.dirname(m), "projeto", "constituicao.md")
escreve(lei_doc, "Art. 1 — a mensagem aprovada é intocável.")
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["lei"] = ["constituicao.md"]
escreve(os.path.join(m, "rito.json"), rito)
escreve(os.path.join(m, "rito-aprovado.marca"), fc.marca(os.path.join(m, "rito.json")))
check("lei em documento sem âncora é acusada — o `rito` é quem ancora",
      any("nunca foi ancorada" in f for f in fc.erros_do_fecho(m)))
fc.ancora_leis(m)
check("ancorada e intocada, a missão fecha", fc.erros_do_fecho(m) == [])
escreve(lei_doc, "Art. 1 — a mensagem pode mudar.")
check("lei que mudou durante a missão é acusada — mostre ao dono antes de fechar",
      any("mudou durante a missão" in f for f in fc.erros_do_fecho(m)))
os.remove(lei_doc)
check("lei que sumiu do disco é acusada",
      any("sumiu do disco depois da abertura" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
check("lei em texto verbatim não exige âncora — o rito-aprovado.marca já a congela",
      fc.erros_do_fecho(m) == [])
shutil.rmtree(d)

print()
print("O ARSENAL — a entrega declara o que usou, ou o dono não tem o que vetar")
d = tmp()
m = monta_missao(d)
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["arsenal"] = ["## website\n- biblioteca-de-efeitos"]
escreve(os.path.join(m, "rito.json"), rito)
escreve(os.path.join(m, "rito-aprovado.marca"), fc.marca(os.path.join(m, "rito.json")))
check("missão com arsenal e entrega calada sobre o que usou é acusada",
      any("não declara `arsenal_usado`" in f for f in fc.erros_do_fecho(m)))
e = os.path.join(m, "pecas", "hero", "r1", "entrega.json")
dado = json.load(open(e, encoding="utf-8"))
dado["arsenal_usado"] = []
escreve(e, dado)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
ver = json.load(open(v, encoding="utf-8"))
ver["entrega"] = fc.marca(e)
escreve(v, ver)
escreve(os.path.join(m, "diretor.json"),
        {"status": "aprovado", "impressionado": True, "frase": "uma mão só",
         "viu": {"hero": fc.marca(e)}})
check("lista vazia é resposta — `não usei nada` fecha",
      fc.erros_do_fecho(m) == [])
shutil.rmtree(d)

print()
print("A OBRA MORA NO PROJETO, NÃO NA MISSÃO — a base do caminho é declarada")
d = tmp()
m = monta_missao(d)
check("artefato relativo resolve contra a raiz do projeto, e a missão saudável fecha",
      fc.erros_do_fecho(m) == [])
rito = json.load(open(os.path.join(m, "rito.json"), encoding="utf-8"))
rito["raiz"] = os.path.join(d, "lugar-errado")
escreve(os.path.join(m, "rito.json"), rito)
escreve(os.path.join(m, "rito-aprovado.marca"), fc.marca(os.path.join(m, "rito.json")))
check("apontada para a raiz errada, a obra some — e é acusado",
      any("sumiu" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("O MAPA — parada declarada não é reprovação")
d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["status"] = "marginal"
dado["gap"] = "o que sobra e pouco"
escreve(v, dado)
mapa = fc.desenha_mapa(m)
check("`marginal` sai como parada por ganho pequeno, não como reprovada",
      "ganho pequeno" in mapa and "reprovada" not in mapa)
shutil.rmtree(d)

print()
print("O SINAL — só o fecho verde o apaga")
d = tmp()
m = monta_missao(d, aprovado=False)
sinal = os.path.join(d, "ativo-sessao")
escreve(sinal, "")
escreve(os.path.join(d, "bloqueios-sessao"), "")
saida = fc.main(["fecho", m, "--sinal", sinal])
check("o fecho vermelho não toca o sinal", saida == 1 and os.path.isfile(sinal))
check("e não toca o registro de bloqueios da sessão",
      os.path.isfile(os.path.join(d, "bloqueios-sessao")))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
sinal = os.path.join(d, "ativo-sessao")
escreve(sinal, "")
escreve(os.path.join(d, "bloqueios-sessao"), "")
saida = fc.main(["fecho", m, "--sinal", sinal])
check("o fecho verde apaga o sinal", saida == 0 and not os.path.exists(sinal))
check("e apaga com ele os bloqueios da mesma sessão",
      not os.path.exists(os.path.join(d, "bloqueios-sessao")))
shutil.rmtree(d)

print()
print("A MARCA — o que ela sobrevive")
d = tmp()
a = os.path.join(d, "a.txt")
escreve(a, "conteudo")
antes = fc.marca(a)
os.utime(a, (0, 0))
check("a marca não muda quando só a DATA muda (clone, checkout, cópia)",
      fc.marca(a) == antes)
escreve(a, "conteudo mexido")
check("a marca muda quando o CONTEÚDO muda", fc.marca(a) != antes)
check("arquivo que não existe não tem marca", fc.marca(os.path.join(d, "x")) is None)
shutil.rmtree(d)

# ── ENCERRAR NÃO É APROVAR, E LEVA O ESTADO INTEIRO ──────────────────────────
# Dois defeitos medidos em 2026-08-10, com a barra do dono na tela mostrando
# "Gauntlet · Missão há 10h25" de uma disputa que ninguém ia retomar:
#
# (1) o apagamento vivia SÓ no caminho do fecho verde — disputa parada pelo dono,
#     abandonada, ou com fecho recusado por furo ficava com o sinal aceso até a
#     expiração de 12h;
# (2) ele levava só `ativo-` e `bloqueios-`, deixando os outros seis para trás —
#     e a onda velha reaparecia na barra de quem reusasse o mesmo id de sessão.
print()
print("encerrar não é aprovar")
d = tempfile.mkdtemp()
SID = "sessao-x"
PREFIXOS = ("ativo-", "bloqueios-", "onda-", "placar-", "doc-", "sinal-",
            "trabalho-", "motorid-")
for pre in PREFIXOS:
    escreve(os.path.join(d, pre + SID), "gauntlet\n")
sinal = os.path.join(d, "ativo-" + SID)

check("o encerra apaga o ESTADO INTEIRO, não só o sinal",
      sorted(fc.apaga_sinal(sinal)) == sorted(p.rstrip("-") for p in PREFIXOS))
check("nada da sessão sobra no disco",
      not [x for x in os.listdir(d) if SID in x])

# o caminho de linha de comando, que é por onde a skill chama
for pre in PREFIXOS:
    escreve(os.path.join(d, pre + SID), "gauntlet\n")
rc = fc.main(["encerra", os.path.join(d, "missao-que-nao-existe"), "--sinal", sinal])
check("o `encerra` sai 0 SEM exigir fecho verde nem missão válida", rc == 0)
check("e o disco fica limpo por esse caminho também",
      not [x for x in os.listdir(d) if SID in x])
check("`encerra` sem --sinal é recusado, não apaga às cegas",
      fc.main(["encerra", d]) == 2)
shutil.rmtree(d)

print()
if FAILS:
    print("fecho_check: %d falha(s)" % len(FAILS))
    for f in FAILS:
        print("  - %s" % f)
    sys.exit(1)
print("fecho_check: tudo verde")
