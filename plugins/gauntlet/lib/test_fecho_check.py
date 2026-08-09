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
            "artefatos": [{"caminho": "obra-%s.txt" % p, "marca": fc.marca(obra)}],
        })
        cam_e = os.path.join(r1, "entrega.json")
        viu[p] = fc.marca(cam_e)
        if com_veredito:
            escreve(os.path.join(r1, "veredito.json"), {
                "peca": p, "rodada": 1,
                "status": "aprovado" if aprovado else "reprovado",
                "eixo": "ritmo da entrada",
                "gap": "" if aprovado else "a entrada do alvo respira mais",
                "entrega": fc.marca(cam_e),
                "registros": {"nosso": "pecas/%s/r1/nosso.png" % p,
                              "alvo": "pecas/%s/r1/alvo.png" % p},
            })
    escreve(os.path.join(m, "diretor.json"), {"status": "aprovado", "viu": viu})
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
vetos = [json.loads(l) for l in open(os.path.join(m, "vetos.jsonl"), encoding="utf-8")]
vetos[0]["mantido"] = True
escreve(os.path.join(m, "vetos.jsonl"),
        "\n".join(json.dumps(v, ensure_ascii=False) for v in vetos) + "\n")
check("o dono dizendo `mantém` fecha o assunto",
      not any("não foi retrabalhado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

print()
print("A PARADA POR RETORNO DECRESCENTE — ela tem que ser CAMPO, não prosa")
d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8"))
dado["status"] = "marginal"
dado["gap"] = "o que sobra e ganho pequeno demais"
escreve(v, dado)
check("`marginal` fecha a peça — é parada declarada, não falha",
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
print("O DIRETOR — o conjunto")
d = tmp()
m = monta_missao(d)
os.remove(os.path.join(m, "diretor.json"))
check("sem o diretor o fecho é recusado",
      any("não passou pelo conjunto" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
escreve(os.path.join(m, "diretor.json"),
        {"status": "aprovado", "viu": {"hero": "0000000000000000"}})
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
print("A RODADA TRANSPLANTADA — o caminho mais barato de fraude")
d = tmp()
m = monta_missao(d, pecas=("hero", "marcas"))
import shutil as _sh
_sh.rmtree(os.path.join(m, "pecas", "hero", "r1"))
_sh.copytree(os.path.join(m, "pecas", "marcas", "r1"), os.path.join(m, "pecas", "hero", "r1"))
check("rodada copiada de outra peça é acusada — a âncora vem junto, o nome não",
      any("transplantado" in f for f in fc.erros_do_fecho(m)))
shutil.rmtree(d)

d = tmp()
m = monta_missao(d)
v = os.path.join(m, "pecas", "hero", "r1", "veredito.json")
dado = json.load(open(v, encoding="utf-8")); dado["rodada"] = 7
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
dado["status"] = "marginal"; dado["gap"] = "o que sobra e pouco"
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

print()
if FAILS:
    print("fecho_check: %d falha(s)" % len(FAILS))
    for f in FAILS:
        print("  - %s" % f)
    sys.exit(1)
print("fecho_check: tudo verde")
