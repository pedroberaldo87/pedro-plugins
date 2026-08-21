#!/usr/bin/env python3
"""O cobrador do pré-check de largada — passadas 1 (F22.1), 2 (F22.2) e 3 (F22.3) · R-32.

O critério do passo, literal: a passada roda sobre um PLANO DE VERDADE e acha
decisão não-declarada PLANTADA em teste; o achado sai como PERGUNTA ao dono, nunca
como palpite gravado; a suíte cobre o caminho mecânico.

Por isso as três frentes aqui: um plano plantado com uma decisão não-declarada de
cada tipo mecânico, a prova de que o módulo não escreve nada (o plano no disco sai
byte a byte igual ao que entrou), e a passada rodando sobre o `.plan.json` real do
projeto quando ele está no disco — ele é ignorado pelo git, então a frente é
condicional; o que não é condicional é o caminho mecânico.

    python3 plugins/project-skills/lib/test_precheck_largada.py
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
MODULO = os.path.join(AQUI, "precheck_largada.py")

from decisoes_seladas import selar  # noqa: E402
from precheck_largada import (ADIAVEL, BLOQUEANTE, anotar_neblina,  # noqa: E402
                              casa_da_neblina, declarar_fora_de_escopo,
                              neblina_aberta, passada1, passada2, passada3,
                              passada4, pergunta_precisa, pode_fechar,
                              confere_largada, grava_relatorio, marca,
                              rodada_seguinte, triar)

ok = falhas = 0


def checa(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ok   %s" % nome)
    else:
        falhas += 1
        print("  FAIL %s  %s" % (nome, detalhe))


def _erra(fn, *a):
    """Roda e diz se levantou ValueError — o registro recusa item sem motivo."""
    try:
        fn(*a)
    except ValueError:
        return True
    return False


def por_check(r, nome):
    return [a for a in r["achados"] if a["check"] == nome]


raiz = tempfile.mkdtemp(prefix="precheck-")
os.makedirs(os.path.join(raiz, "docs"))
with open(os.path.join(raiz, "docs", "blueprint.md"), "w", encoding="utf-8") as f:
    f.write("---\nstatus: approved\n---\n\nO desenho aprovado pelo dono.\n")
with open(os.path.join(raiz, "docs", "rascunho.md"), "w", encoding="utf-8") as f:
    f.write("# sem tranca nenhuma\n")

# ── O PLANO PLANTADO: uma decisão não-declarada de cada tipo mecânico ────────
PLANO = {"phases": [{"id": "P1", "items": [
    {"id": "P1.1", "status": "done",
     "desc": "toca docs/blueprint.md sem protegido",  # casa-ok: texto do plano FALSO do teste, não é caminho de doc deste projeto
     "pronto": "o passo já feito não é varrido por esta passada"},
    {"id": "P1.2", "status": "todo",
     "desc": "reescreve o desenho em docs/blueprint.md",  # casa-ok: texto do plano FALSO do teste, não é caminho de doc deste projeto
     "pronto": "o desenho novo está no arquivo"},
    {"id": "P1.3", "status": "todo",
     "desc": "publica o pacote no marketplace",
     "pronto": "o dono aprova o release e o plugin é publicado"},
    {"id": "P1.4", "status": "todo",
     "desc": "o agente não alcança a máquina do servidor",
     "pronto": "o serviço responde na máquina remota"},
    {"id": "P1.5", "status": "todo",
     "desc": "o vigia dispara sozinho",
     "pronto": "o vigia acorda a cada 5 s e grava a leitura",
     "decidido": {"escolha": "usar cron, que tem grão de 1 min",
                  "porque": "é o que a máquina oferece"}},
    {"id": "P1.6", "status": "todo",
     "desc": "o cliente sobe lendo a partir de lib/config_do_cliente.py",
     "pronto": "o cliente sobe com a configuração real"},
    {"id": "P1.7", "status": "todo",
     "desc": "o compose injeta $MINHA_CHAVE_SECRETA no serviço",
     "pronto": "o serviço sobe com o valor vindo do ambiente"},
]}]}

antes = json.dumps(PLANO, ensure_ascii=False, sort_keys=True)
r = passada1(PLANO, raiz)

checa("a passada varre só os passos ABERTOS (o feito fica de fora)",
      "P1.1" not in r["passos_abertos"] and len(r["passos_abertos"]) == 6,
      repr(r["passos_abertos"]))

# ── 1 · CAMINHO MECÂNICO, CHECAGEM A CHECAGEM ───────────────────────────────
tranca = por_check(r, "tranca")
checa("arquivo sob tranca sem `protegido` vira achado",
      [a["passo"] for a in tranca] == ["P1.2"], repr(tranca))
checa("a prova da tranca é o frontmatter lido do DISCO",
      bool(tranca) and "status: approved" in tranca[0]["prova"], repr(tranca))

ato = por_check(r, "ato_do_dono")
checa("`pronto` que pede ato do dono sem espera_dono vira achado",
      [a["passo"] for a in ato] == ["P1.3"], repr(ato))

imp = por_check(r, "impedimento")
checa("impedimento afirmado de memória vira pedido de COMANDO",
      [a["passo"] for a in imp] == ["P1.4"] and "comando" in imp[0]["pergunta"],
      repr(imp))

ar = por_check(r, "aritmetica")
checa("par pronto × decidido impossível por aritmética vira achado (5s × 60s)",
      [a["passo"] for a in ar] == ["P1.5"] and "5" in ar[0]["pergunta"], repr(ar))

pre = por_check(r, "precondicao")
checa("pré-condição consumida e ausente do disco vira achado",
      [a["passo"] for a in pre] == ["P1.6"], repr(pre))

reg = por_check(r, "regua_pronto")
checa("a régua do `pronto` é reusada, não reescrita",
      all(a["classe"] == BLOQUEANTE for a in reg), repr(reg))

# O segredo se confere por grep na árvore rastreada — sem git, a checagem não
# inventa veredito (fail-open da casa). Aqui a raiz temporária não é repositório.
subprocess.run(["git", "init", "-q", raiz], check=False, capture_output=True,
               stdin=subprocess.DEVNULL, start_new_session=True)
r_git = passada1(PLANO, raiz)
seg = por_check(r_git, "segredo")
checa("variável citada com zero ocorrência na árvore vira achado",
      [a["passo"] for a in seg] == ["P1.7"], repr(seg))
checa("a prova do segredo é o grep, com o número medido",
      bool(seg) and "0 arquivos" in seg[0]["prova"], repr(seg))

# ── 2 · O ACHADO É PERGUNTA, NUNCA PALPITE GRAVADO ──────────────────────────
checa("o módulo não escreve NADA no plano que recebeu",
      json.dumps(PLANO, ensure_ascii=False, sort_keys=True) == antes)
checa("todo achado sai com pergunta e prova",
      all(a["pergunta"].strip() and a["prova"].strip() for a in r["achados"]),
      repr([a for a in r["achados"] if not a["prova"].strip()]))
checa("o bloqueante vai ao dono e nada além do bloqueante vira pergunta",
      all(a["classe"] == BLOQUEANTE for a in r["perguntas"])
      and len(r["perguntas"]) + len(r["registrados"]) == len(r["achados"]))
campos = {"decidido", "pendencia", "espera_dono", "protegido"}
checa("nenhum passo aberto ganhou campo de decisão por palpite",
      not any(campos & set(i) for f in PLANO["phases"] for i in f["items"]
              if i["id"] != "P1.5"))

# ── 3 · O REGISTRO SELADO É CONSULTADO ANTES DA PERGUNTA ────────────────────
pergunta_do_dono = r["perguntas"][0]["pergunta"]
selar(raiz, fala=pergunta_do_dono, fonte="colheita de teste", data="2026-08-19")
r2 = passada1(PLANO, raiz)
ainda = [a for a in r2["perguntas"] if a["pergunta"] == pergunta_do_dono]
checa("pergunta já respondida no registro selado NÃO volta ao dono",
      not ainda, repr(ainda))
respondida = [a for a in r2["registrados"] if a.get("respondida_por")]
checa("ela sai registrada com a fala do dono que a responde",
      bool(respondida) and pergunta_do_dono in respondida[0]["respondida_por"],
      repr(respondida))

# ── 4 · O ADIÁVEL NÃO PERGUNTA ──────────────────────────────────────────────
ADIA = {"phases": [{"id": "Q", "items": [
    {"id": "Q.1", "status": "todo", "desc": "cria lib/coisa_nova.py",
     "pronto": "o arquivo lib/coisa_nova.py nasce com a função"},
    {"id": "Q.2", "status": "todo", "desc": "sobe lendo a partir de lib/coisa_nova.py",
     "pronto": "o consumidor usa a função"},
]}]}
ra = passada1(ADIA, raiz)
adiaveis = [a for a in ra["achados"] if a["classe"] == ADIAVEL]
checa("pré-condição que OUTRO passo aberto produz é ADIÁVEL, não pergunta",
      [a["passo"] for a in adiaveis] == ["Q.2"]
      and not [a for a in ra["perguntas"] if a["check"] == "precondicao"],
      repr(ra["achados"]))

# ── 5 · O PLANO DE VERDADE ──────────────────────────────────────────────────
RAIZ_PROJ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
# O plano ESCOLHIDO é o que tem passo aberto, nunca "o último da lista": ordem
# alfabética entrega plano FECHADO (autopsia-2026-08-09) e a checagem reprovava por
# um motivo que não é o que ela mede.
def _com_passo_aberto(caminhos):
    for c in reversed(caminhos):
        try:
            with open(c, encoding="utf-8") as f:
                p = json.load(f)
        except Exception:
            continue
        if any(i.get("status") == "todo" for fa in p.get("phases", []) for i in fa.get("items", [])):
            return c, p
    return None, None


_todos = sorted(glob.glob(os.path.join(RAIZ_PROJ, ".claude", "plans", "*.plan.json")))
_escolhido, real = _com_passo_aberto(_todos)
reais = [_escolhido] if _escolhido else []
if reais:
    rr = passada1(real, RAIZ_PROJ)
    checa("a passada roda sobre um plano de verdade e devolve os passos abertos",
          isinstance(rr["achados"], list) and rr["passos_abertos"], reais[-1])
    checa("nenhum achado do plano real sai sem pergunta ao dono",
          all(a["pergunta"].strip() for a in rr["achados"]))
else:
    print("  --   plano real ausente (.claude/plans é ignorado pelo git) — frente pulada")

# ── 6 · A LINHA DE COMANDO ──────────────────────────────────────────────────
arq = os.path.join(raiz, "plantado.plan.json")
with open(arq, "w", encoding="utf-8") as f:
    json.dump(PLANO, f, ensure_ascii=False)
p = subprocess.run([sys.executable, MODULO, arq, "--raiz", raiz],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=120, stdin=subprocess.DEVNULL,
                   start_new_session=True)
checa("o comando sai 1 quando há pergunta em aberto", p.returncode == 1, p.stderr)
checa("a saída do comando é o relatório em JSON",
      bool(json.loads(p.stdout or "{}").get("perguntas")), p.stdout[:200])

# ── 7 · PASSADA 2 · A SEQUÊNCIA (F22.2) ─────────────────────────────────────
# O plano plantado: cada defeito de encadeamento aparece SÓ na ordem, nunca no
# passo lido sozinho.
SEQ = {"phases": [
    {"id": "S1", "items": [
        {"id": "S1.1", "status": "todo", "desc": "o consumidor sobe lendo a partir de "
         "lib/artefato_de_b.py", "pronto": "o consumidor usa o artefato",
         "files": ["lib/consumidor.py"]},
        {"id": "S1.2", "status": "todo", "desc": "escreve o artefato",
         "pronto": "o arquivo nasce", "files": ["lib/artefato_de_b.py"]},
        {"id": "S1.3", "status": "todo", "desc": "mexe no motor",
         "pronto": "o motor muda", "files": ["lib/motor.py"], "parallelizable": True},
        {"id": "S1.4", "status": "todo", "desc": "mexe no motor por outro lado",
         "pronto": "o motor muda de novo", "files": ["lib/motor.py"],
         "parallelizable": True},
        {"id": "S1.5", "status": "todo", "desc": "aplica a migration",
         "pronto": "o banco sobe", "files": ["db/125_indice.sql"]},
    ]},
    {"id": "S2", "items": [
        {"id": "S2.1", "status": "todo", "desc": "aplica a migration anterior",
         "pronto": "a tabela existe", "files": ["db/124_tabela.sql"]},
        {"id": "S2.2", "status": "todo", "desc": "fecha a frente",
         "pronto": "o relatório da frente cita S2.3 fechado", "files": ["lib/fecho.py"]},
        {"id": "S2.3", "status": "todo", "desc": "o último passo da corrida",
         "pronto": "o portão entra por último", "files": ["lib/portao.py"],
         "dependsOn": ["S2.2"]},
        {"id": "S2.4", "status": "todo", "desc": "depende de quem vem depois",
         "pronto": "roda", "files": ["lib/tarde.py"], "dependsOn": ["S2.5"]},
        {"id": "S2.5", "status": "todo", "desc": "o passo tardio",
         "pronto": "roda", "files": ["lib/tardio.py"]},
    ]},
]}

antes_seq = json.dumps(SEQ, ensure_ascii=False, sort_keys=True)
rs = passada2(SEQ, raiz)


def por_check2(nome):
    return [a for a in rs["achados"] if a["check"] == nome]


dep = por_check2("dependencia_nao_declarada")
checa("A precisa do artefato de B sem dependsOn e isso vira decisão de ordem",
      [(a["passo"], "S1.2" in a["pergunta"]) for a in dep] == [("S1.1", True)],
      repr(dep))
checa("a prova da dependência nomeia quem consome, quem produz e o dependsOn vazio",
      bool(dep) and "S1.2 produz lib/artefato_de_b.py" in dep[0]["prova"]
      and "dependsOn(S1.1)=[]" in dep[0]["prova"], repr(dep))

quente = por_check2("arquivo_quente")
checa("o detector de arquivo quente pega dois paralelos no mesmo arquivo",
      [a["passo"] for a in quente] == ["S1.3"] and "S1.4" in quente[0]["pergunta"]
      and "lib/motor.py" in quente[0]["prova"], repr(quente))

crit = por_check2("dependencia_de_criterio")
checa("critério satisfazível só depois do passo que a ordem manda por último",
      [a["passo"] for a in crit] == ["S2.2"] and "S2.3" in crit[0]["pergunta"],
      repr(crit))

ordem = por_check2("ordem_contraditoria")
checa("dependência declarada apontando para passo posterior vira achado",
      [a["passo"] for a in ordem] == ["S2.4"] and "S2.5" in ordem[0]["pergunta"],
      repr(ordem))

art = por_check2("ordem_de_artefatos")
checa("125 declarado antes de 124 vira achado de ordem de aplicação",
      [a["passo"] for a in art] == ["S1.5"]
      and "db/124_tabela.sql" in art[0]["pergunta"], repr(art))

checa("a passada 2 não escreve NADA no plano que recebeu",
      json.dumps(SEQ, ensure_ascii=False, sort_keys=True) == antes_seq)
checa("todo achado da passada 2 sai com pergunta e prova, e o bloqueante pergunta",
      all(a["pergunta"].strip() and a["prova"].strip() for a in rs["achados"])
      and len(rs["perguntas"]) + len(rs["registrados"]) == len(rs["achados"]))

# O plano SEM defeito de sequência não inventa achado.
LIMPO = {"phases": [{"id": "L", "items": [
    {"id": "L.1", "status": "todo", "desc": "cria o artefato",
     "pronto": "o arquivo nasce", "files": ["lib/limpo.py"]},
    {"id": "L.2", "status": "todo", "desc": "sobe lendo a partir de lib/limpo.py",
     "pronto": "usa", "files": ["lib/usa.py"], "dependsOn": ["L.1"]},
    {"id": "L.3", "status": "todo", "desc": "mexe em lib/a.py",
     "pronto": "muda", "files": ["lib/a.py"], "parallelizable": True},
    {"id": "L.4", "status": "todo", "desc": "mexe em lib/b.py",
     "pronto": "muda", "files": ["lib/b.py"], "parallelizable": True},
]}]}
checa("plano com a sequência em ordem não gera achado nenhum",
      passada2(LIMPO, raiz)["achados"] == [], repr(passada2(LIMPO, raiz)["achados"]))

# O registro selado vale igual na passada 2.
pergunta_seq = rs["perguntas"][0]["pergunta"]
selar(raiz, fala=pergunta_seq, fonte="colheita de teste", data="2026-08-21")
rs2 = passada2(SEQ, raiz)
checa("pergunta de sequência já selada não volta ao dono",
      not [a for a in rs2["perguntas"] if a["pergunta"] == pergunta_seq],
      repr(rs2["perguntas"][:1]))

arq2 = os.path.join(raiz, "sequencia.plan.json")
with open(arq2, "w", encoding="utf-8") as f:
    json.dump(SEQ, f, ensure_ascii=False)
p2 = subprocess.run([sys.executable, MODULO, arq2, "--raiz", raiz, "--passada", "2"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=120, stdin=subprocess.DEVNULL,
                    start_new_session=True)
checa("o comando --passada 2 sai 1 e imprime o relatório da sequência",
      p2.returncode == 1 and json.loads(p2.stdout or "{}").get("perguntas"),
      p2.stderr or p2.stdout[:200])

# ── PASSADA 3 · A CASA MEDIDA POR EXECUÇÃO (F22.3) ──────────────────────────
# Aqui nada é lido de plano: os comandos RODAM. A casa é um repositório git de
# verdade (a prova da esteira é chaveada pelo hash da árvore, e sem git não há
# hash), e as esteiras são scripts plantados que respondem o que o caso pede.
casa = tempfile.mkdtemp(prefix="precheck3-")
# O registro da prova mora FORA da árvore medida — dentro dela, o próprio arquivo
# de prova mudaria o hash e nenhuma prova jamais casaria.
os.environ["GREEN_SUITE_DIR"] = tempfile.mkdtemp(prefix="precheck3-green-")
subprocess.run(["git", "init", "-q", casa], check=True, timeout=60,
               stdin=subprocess.DEVNULL, start_new_session=True)
subprocess.run(["git", "-C", casa, "config", "user.email", "t@t"], check=True, timeout=60,
               stdin=subprocess.DEVNULL, start_new_session=True)
subprocess.run(["git", "-C", casa, "config", "user.name", "t"], check=True, timeout=60,
               stdin=subprocess.DEVNULL, start_new_session=True)
with open(os.path.join(casa, "leia.md"), "w", encoding="utf-8") as f:
    f.write("a árvore da largada\n")
subprocess.run(["git", "-C", casa, "add", "-A"], check=True, timeout=60,
               stdin=subprocess.DEVNULL, start_new_session=True)
subprocess.run(["git", "-C", casa, "commit", "-qm", "largada"], check=True, timeout=60,
               stdin=subprocess.DEVNULL, start_new_session=True)

VERDE = 'echo "155 suíte(s) · 0 problema(s)"'
VERMELHA = 'echo "155 suíte(s) · 3 problema(s)"; exit 1'
VAZIA = 'echo "0 suíte(s) · 0 problema(s)"'


def checks(r, nome):
    return [a for a in r["achados"] if a["check"] == nome]


def suja(tag):
    """Mexe na árvore: hash novo ⇒ MISS no green-cache ⇒ a esteira RODA de verdade."""
    with open(os.path.join(casa, "sujeira-%s.txt" % tag), "w", encoding="utf-8") as f:
        f.write(tag)


def tem_prova():
    return subprocess.run(
        ["bash", "-c", ". %s; green_cache_check %s full"
         % (os.path.join(AQUI, "green-cache.sh"), casa)],
        timeout=60, stdin=subprocess.DEVNULL, start_new_session=True).returncode == 0


# CASO 1 · a esteira está VERMELHA.
suja("vermelha")
r1 = passada3(casa, suite_cmd=VERMELHA, teto_suite=60)
checa("esteira vermelha vira pergunta bloqueante",
      [a["classe"] for a in checks(r1, "esteira")] == [BLOQUEANTE]
      and any(a["check"] == "esteira" for a in r1["perguntas"]), repr(r1["achados"]))
checa("a prova da esteira vermelha cola o rc e a saída crua",
      "rc=1" in checks(r1, "esteira")[0]["prova"]
      and "3 problema" in checks(r1, "esteira")[0]["prova"],
      repr(checks(r1, "esteira")[0]["prova"]))

checa("a esteira vermelha NÃO grava prova nenhuma", tem_prova() is False)

# CASO 2 · não existe prova gravada para ESTA árvore. Isso NÃO fecha a porta: quem
# mede é esta passada, e é ela que grava a prova quando a esteira sai verde. Exigir
# prova de terceiro aqui tornava a largada insatisfazível fora deste repositório.
suja("verde")
r2 = passada3(casa, suite_cmd=VERDE, teto_suite=60)
checa("MISS no green-cache NÃO fecha a porta — a passada mede em casa",
      checks(r2, "prova_da_arvore") == [] and checks(r2, "esteira") == [],
      repr(r2["achados"]))
# A passada MEDE, mas NÃO grava no depósito de prova compartilhado: o comando da
# esteira aqui é o que a largada declarou, e o depósito tem contrato — só a esteira
# INTEIRA grava a prova de escopo total, que depois satisfaz toda consulta.
checa("a passada NÃO grava prova no depósito compartilhado", tem_prova() is False,
      repr(r2["arvore"]))

# CASO 2b · a prova existe para a árvore de AGORA, gravada por QUEM rodou a esteira
# inteira (o hook do ship, o qa-loop): a esteira não roda de novo.
subprocess.run(["bash", "-c", ". %s; green_cache_mark %s full teste"
                % (os.path.join(AQUI, "green-cache.sh"), casa)],
               check=True, timeout=60, stdin=subprocess.DEVNULL, start_new_session=True)
r2b = passada3(casa, suite_cmd=VERMELHA, teto_suite=60)
checa("com a prova gravada, a esteira é PULADA e a passada diz que reaproveitou",
      [a["classe"] for a in checks(r2b, "esteira")] == [ADIAVEL]
      and "reaproveitada" in checks(r2b, "esteira")[0]["prova"]
      and r2b["perguntas"] == [], repr(r2b["achados"]))

# CASO 2c · a árvore não é MEDÍVEL (raiz fora do git): o gate que não consegue medir
# tem que DIZER que não mediu (Artigo 4) — e não fechar a porta de toda largada.
sem_git = tempfile.mkdtemp(prefix="precheck-sem-git-")
r2c = passada3(sem_git, suite_cmd=VERDE, teto_suite=60)
checa("árvore não medível vira ADIÁVEL que diz que NÃO MEDIU, não bloqueante",
      [a["classe"] for a in checks(r2c, "prova_da_arvore")] == [ADIAVEL]
      and "não deu para MEDIR" in checks(r2c, "prova_da_arvore")[0]["pergunta"]
      and checks(r2c, "prova_da_arvore")[0] not in r2c["perguntas"], repr(r2c["achados"]))

# CASO 3 · o comando da esteira mede ZERO suítes e sai verde (o glob vazio).
suja("vazia")
r3 = passada3(casa, suite_cmd=VAZIA, teto_suite=60)
checa("suiteCmd que mede zero suítes reprova mesmo saindo verde",
      [a["classe"] for a in checks(r3, "suite_mede")] == [BLOQUEANTE]
      and any(a["check"] == "suite_mede" for a in r3["perguntas"]), repr(r3["achados"]))
checa("suiteCmd vazio é pergunta, não silêncio",
      [a["check"] for a in passada3(casa, suite_cmd="")["perguntas"]][:1] == ["esteira"])

# O gate de commit que não responde dentro do teto.
suja("gate")
rg = passada3(casa, suite_cmd=VERDE, gate_cmd="sleep 5", teto_suite=60, teto_gate=1)
checa("gate de commit que estoura o teto vira pergunta",
      [a["classe"] for a in checks(rg, "gate_de_commit")] == [BLOQUEANTE],
      repr(rg["achados"]))
suja("gatev")
rgv = passada3(casa, suite_cmd=VERDE, gate_cmd="exit 3", teto_suite=60)
checa("gate de commit que reprova a árvore vira pergunta",
      "rc=3" in checks(rgv, "gate_de_commit")[0]["prova"], repr(rgv["achados"]))

# Veredito instável: a mesma esteira mudando de veredito entre duas rodadas.
sino = os.path.join(casa, "sino")
INSTAVEL = ('if [ -f %s ]; then echo "155 suíte(s) · 1 problema(s)"; exit 1; '
            'else : > %s; echo "155 suíte(s) · 0 problema(s)"; fi' % (sino, sino))
suja("instavel")
ri = passada3(casa, suite_cmd=INSTAVEL, teto_suite=60, rodadas=2)
checa("veredito que muda entre duas rodadas reprova",
      [a["classe"] for a in checks(ri, "veredito_estavel")] == [BLOQUEANTE],
      repr(checks(ri, "veredito_estavel")))
checa("com uma rodada só, o medidor DIZ que não mediu a estabilidade",
      [a["classe"] for a in checks(r2, "veredito_estavel")] == [ADIAVEL],
      repr(checks(r2, "veredito_estavel")))

# O alvo da largada: dois planos ativos e nenhum alvo declarado não larga.
planos = os.path.join(casa, "planos")
os.makedirs(planos)
for pid in ("A", "B"):
    with open(os.path.join(planos, "%s.plan.json" % pid), "w", encoding="utf-8") as f:
        json.dump({"id": pid, "status": "active", "phases": []}, f)
ra = passada3(casa, suite_cmd=VERDE, planos=planos, teto_suite=60)
checa("dois planos ativos sem alvo declarado fecham a porta",
      [a["classe"] for a in checks(ra, "alvo_da_largada")] == [BLOQUEANTE],
      repr(checks(ra, "alvo_da_largada")))
checa("com o alvo declarado, a porta do alvo abre",
      checks(passada3(casa, suite_cmd=VERDE, planos=planos, alvo="A",
                      teto_suite=60), "alvo_da_largada") == [])

checa("todo achado da passada 3 sai com pergunta e prova",
      all(a["pergunta"].strip() and a["prova"].strip()
          for r in (r1, r2, r2b, r3, rg, ri, ra) for a in r["achados"]))

# O ADIÁVEL CHEGA AO ARTEFATO (Artigo 4). O que se mede é o RELATÓRIO no disco e o
# texto que a casca imprime — não o valor de retorno da passada, que ninguém lê.
adi = tempfile.mkdtemp(prefix="precheck-adiavel-")
PLANO_ADI = {"id": "AD", "phases": [{"items": [
    {"id": "F1.1", "desc": "um passo", "pronto": "a suíte passa"}]}]}
rel_adi = grava_relatorio(adi, PLANO_ADI,
                          {"3": passada3(adi, suite_cmd=VERDE, teto_suite=60)})
with open(os.path.join(adi, ".claude", ".sprint", "precheck.json"), encoding="utf-8") as f:
    do_disco = json.load(f)
checa("o achado ADIÁVEL vai para o relatório GRAVADO, não morre no retorno",
      any(a["check"] == "prova_da_arvore" for a in do_disco.get("adiadas") or []),
      repr(do_disco))
v_adi = confere_largada(adi, PLANO_ADI)
checa("a casca larga, mas o texto NOMEIA os adiados e cita o primeiro por extenso",
      v_adi["larga"] is True and "ADIADO" in v_adi["texto"]
      and ("%d achado" % len(do_disco["adiadas"])) in v_adi["texto"]
      and do_disco["adiadas"][0]["pergunta"] in v_adi["texto"], repr(v_adi))
checa("o veredito do relatório com adiável continua livre",
      rel_adi["veredito"] == "livre", repr(rel_adi["veredito"]))

# ── PASSADA 4 · A VIZINHANÇA (F22.4) ────────────────────────────────────────
# Os dois cenários caros são REPRODUZIDOS, não simulados por mock: um motor vivo
# com reserva de arquivo dentro da mesma árvore (o estado que
# `reserva-de-arquivos.sh` escreve), e uma guarda de PreToolUse de verdade, com
# hooks.json e script, que responde `deny` ao comando do passo.
viz = tempfile.mkdtemp(prefix="precheck4-")
os.makedirs(os.path.join(viz, "scripts"))
with open(os.path.join(viz, "scripts", "suite.sh"), "w", encoding="utf-8") as f:
    f.write("echo ok\n")

# O motor vizinho: reserva viva apontando para um arquivo DESTA árvore, com o
# aviso `ativo-<sid>` aceso — exatamente o par que o sprint deixa no disco.
estado = tempfile.mkdtemp(prefix="precheck4-estado-")
os.makedirs(os.path.join(estado, "reservas"))
with open(os.path.join(estado, "reservas", "sessX__motor-b.files"), "w",
          encoding="utf-8") as f:
    f.write("%s\n" % os.path.join(viz, "scripts", "suite.sh"))
with open(os.path.join(estado, "ativo-sessX"), "w", encoding="utf-8") as f:
    f.write("sprint\n")

# A guarda de verdade: plugin plantado na árvore, hooks.json com PreToolUse de
# Bash, e um script que NEGA quem citar a esteira.
guarda = os.path.join(viz, "plugins", "vigia", "hooks")
os.makedirs(guarda)
with open(os.path.join(guarda, "hooks.json"), "w", encoding="utf-8") as f:
    json.dump({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command",
         "command": 'sh "$CLAUDE_PLUGIN_ROOT/hooks/nega.sh"'}]}]}}, f)
with open(os.path.join(guarda, "nega.sh"), "w", encoding="utf-8") as f:
    f.write('#!/bin/sh\nIN=$(cat)\ncase "$IN" in *suite.sh*) printf \'{"hookSpecific'
            'Output":{"hookEventName":"PreToolUse","permissionDecision":"deny",'
            '"permissionDecisionReason":"a esteira nao roda por fora"}}\';; esac\n')

PLANO4 = {"phases": [{"id": "F", "items": [
    {"id": "V.1", "status": "todo",
     "desc": "roda a esteira com `bash scripts/suite.sh`",
     "files": ["scripts/suite.sh"],
     "pronto": "a esteira sai verde"},
    {"id": "V.2", "status": "todo",
     "desc": "o CI do projeto tem que ficar verde antes do passo seguinte",
     "pronto": "o pipeline verde no painel"},
    {"id": "V.3", "status": "todo", "desc": "sobe o servidor em localhost:8123",
     "pronto": "responde em localhost:8123"},
    {"id": "V.4", "status": "todo", "desc": "sobe o painel em localhost:8123",
     "pronto": "a página abre"},
]}]}

r4 = passada4(PLANO4, viz, base_estado=estado)

checa("motor vivo na MESMA árvore vira pergunta, com a reserva como prova",
      [a["classe"] for a in checks(r4, "motor_vivo")] == [BLOQUEANTE]
      and "suite.sh" in checks(r4, "motor_vivo")[0]["prova"]
      and "ativo-sessX aceso" in checks(r4, "motor_vivo")[0]["prova"],
      repr(checks(r4, "motor_vivo")))

checa("a guarda de PreToolUse que NEGA o comando do passo vira pergunta",
      [(a["classe"], a["passo"]) for a in checks(r4, "guarda_nega")] == [(BLOQUEANTE, "V.1")]
      and "deny" in checks(r4, "guarda_nega")[0]["prova"],
      repr(checks(r4, "guarda_nega")))

checa("recurso externo sem espera_dono sai como achado NOMEADO",
      [(a["passo"], a["classe"]) for a in checks(r4, "recurso_externo")] == [("V.2", BLOQUEANTE)],
      repr(checks(r4, "recurso_externo")))

checa("dois passos na mesma porta fixa não largam juntos",
      [a["classe"] for a in checks(r4, "porta_compartilhada")] == [BLOQUEANTE]
      and "8123" in checks(r4, "porta_compartilhada")[0]["prova"],
      repr(checks(r4, "porta_compartilhada")))

checa("tudo isso vai ao dono como PERGUNTA, com prova colada",
      all(a["pergunta"].strip() and a["prova"].strip() for a in r4["achados"])
      and len(r4["perguntas"]) == len(r4["achados"]), repr(r4["perguntas"]))

# Com o passo já declarando a espera, o recurso externo para de perguntar.
PLANO4E = json.loads(json.dumps(PLANO4))
PLANO4E["phases"][0]["items"][1]["espera_dono"] = "o dono roda o CI"
checa("com espera_dono declarado, o recurso externo cala",
      checks(passada4(PLANO4E, viz, base_estado=estado), "recurso_externo") == [])

# A regra de exclusividade do CLAUDE.md virando checagem de `ps`: com a regra
# escrita e o processo JÁ de pé, a passada acusa.
with open(os.path.join(viz, "CLAUDE.md"), "w", encoding="utf-8") as f:
    f.write("# regra da casa\n\nNunca duas suítes ao mesmo tempo na mesma máquina.\n")
ESTEIRA_VIZINHA = os.path.join(viz, "scripts", "esteira-vizinha.sh")
with open(ESTEIRA_VIZINHA, "w", encoding="utf-8") as f:
    f.write("sleep 37\n")
vizinho = subprocess.Popen(["sh", ESTEIRA_VIZINHA], stdin=subprocess.DEVNULL,
                           start_new_session=True)
try:
    PLANO4P = {"phases": [{"id": "F", "items": [
        {"id": "V.9", "status": "todo",
         "desc": "roda a esteira com `sh scripts/esteira-vizinha.sh`",
         "pronto": "o comando termina"}]}]}
    rx = passada4(PLANO4P, viz, base_estado=estado)
    checa("regra 'nunca duas ao mesmo tempo' + processo de pé = pergunta",
          [a["classe"] for a in checks(rx, "exclusividade")] == [BLOQUEANTE]
          and "esteira-vizinha.sh" in checks(rx, "exclusividade")[0]["prova"],
          repr(checks(rx, "exclusividade")))
finally:
    vizinho.kill()
    vizinho.wait(timeout=10)

# Reserva EXPIRADA é motor morto: não disputa nada.
velha = os.path.join(estado, "reservas", "sessX__motor-b.files")
os.utime(velha, (0, 0))
checa("reserva expirada não conta como motor vivo",
      checks(passada4(PLANO4, viz, base_estado=estado), "motor_vivo") == [])


# ── NEBLINA (F22.9) · a suspeita sem forma vira registro, não pergunta ──────
neb = tempfile.mkdtemp(prefix="neblina-")
PRECISA = {"passo": "F1.2", "check": "precondicao", "classe": BLOQUEANTE,
           "pergunta": "o passo parte de docs/x.md, que não está no disco — quem "  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
                       "produz esse arquivo antes da largada?",
           "prova": "docs/x.md: não existe"}  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
SEM_FORMA = {"passo": "?", "check": "cheiro", "classe": BLOQUEANTE,
             "pergunta": "tem algo estranho aqui", "prova": ""}

checa("pergunta precisa passa no teste", pergunta_precisa(PRECISA) == [],
      repr(pergunta_precisa(PRECISA)))
checa("suspeita sem forma acusa as três faltas",
      len(pergunta_precisa(SEM_FORMA)) == 3, repr(pergunta_precisa(SEM_FORMA)))

t = triar(neb, [PRECISA, SEM_FORMA], data="2026-08-21")
checa("só a precisa vira pergunta ao dono",
      [a["passo"] for a in t["perguntas"]] == ["F1.2"], repr(t["perguntas"]))
checa("a sem forma vira registro de neblina, não some",
      len(t["neblina"]) == 1 and "tem algo estranho aqui" in t["neblina"][0]["linha"],
      repr(t["neblina"]))

arq = casa_da_neblina(neb)
conteudo = open(arq, encoding="utf-8").read()
checa("o registro mora na casa do projeto, fora do plugin",
      arq.endswith(os.path.join(".claude", "neblina.md"))
      and os.path.isfile(arq) and AQUI not in arq, arq)
checa("a suspeita cabe inteira numa linha só (grep acha)",
      any('"tem algo estranho aqui"' in ln for ln in conteudo.splitlines()), conteudo)

checa("suspeita repetida não duplica linha",
      triar(neb, [SEM_FORMA], data="2026-08-21")
      and len([ln for ln in open(arq, encoding="utf-8")
               if "tem algo estranho aqui" in ln]) == 1, conteudo)

# O fecho do loop: neblina aberta segura; declarada fora de escopo libera.
checa("loop NÃO fecha com neblina aberta", pode_fechar(neb) == (False, neblina_aberta(neb))
      and not pode_fechar(neb)[0] and len(pode_fechar(neb)[1]) == 1,
      repr(pode_fechar(neb)))
checa("declarar fora de escopo exige motivo",
      _erra(declarar_fora_de_escopo, neb, "tem algo estranho aqui", ""))
checa("declarar fora de escopo acha a linha",
      declarar_fora_de_escopo(neb, "tem algo estranho aqui", "outro plano cuida"))
checa("loop fecha com cada item declarado fora de escopo",
      pode_fechar(neb) == (True, []), repr(pode_fechar(neb)))

vazio = tempfile.mkdtemp(prefix="neblina-vazia-")
checa("loop fecha com neblina vazia (registro nem existe)",
      pode_fechar(vazio) == (True, []), repr(pode_fechar(vazio)))

anotar_neblina(neb, "segunda suspeita sem forma", "não traz prova visível", "F2.1")
checa("neblina nova reabre o fecho",
      pode_fechar(neb)[0] is False and len(pode_fechar(neb)[1]) == 1,
      repr(pode_fechar(neb)))

# ── RODADA N+1 (F22.7) · a rodada que parte das RESPOSTAS ───────────────────
# Duas respostas à MESMA rodada: uma que revela nome novo (gera decorrência) e
# uma que só confirma (não gera nada). E depois a rodada seguinte às respostas
# sem decorrência — a que FECHA o loop.
rod = tempfile.mkdtemp(prefix="rodada-")

REVELA = {"passo": "F1.2", "check": "precondicao",
          "pergunta": "o passo parte de docs/x.md, que não está no disco — quem "  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
                      "produz esse arquivo antes da largada?",
          "prova": "docs/x.md: não existe",  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
          "resposta": "quem produz é o passo F0.9, que grava docs/x.md a partir de "  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
                      "scripts/gera-x.sh"}
CONFIRMA = {"passo": "F1.3", "check": "tranca",
            "pergunta": "o passo toca docs/x.md, que está aprovado e trancado — "  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
                        "entrega proposta ou você destranca o arquivo?",
            "prova": "docs/x.md: status: approved no frontmatter",  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
            "resposta": "isso mesmo, entrega proposta"}

r7 = rodada_seguinte(rod, [REVELA, CONFIRMA])
checa("a rodada N+1 lê as duas respostas sem tocar no plano",
      [l["passo"] for l in r7["leitura"]] == ["F1.2", "F1.3"], repr(r7["leitura"]))
checa("a resposta que traz nome novo gera pergunta decorrente",
      [a["passo"] for a in r7["perguntas"]] == ["F1.2"]
      and "scripts/gera-x.sh" in " ".join(a["pergunta"] for a in r7["perguntas"]),
      repr(r7["perguntas"]))
checa("a resposta que só confirma não gera decorrência",
      r7["leitura"][1]["confirmou"] is True
      and [a for a in r7["achados"] if a["passo"] == "F1.3"] == [],
      repr(r7["leitura"][1]))
checa("com decorrência aberta o loop NÃO fecha", r7["fechou"] is False, repr(r7))

# A resposta que DESCONFIRMA a prova da rodada anterior também é decorrência.
rd = rodada_seguinte(rod, [dict(REVELA, resposta="não existe passo nenhum que "
                                                 "produza esse arquivo")])
checa("resposta que derruba a prova anterior vira pergunta",
      [a["check"] for a in rd["perguntas"]] == ["desconfirmado"], repr(rd["perguntas"]))

# E o achado `desconfirmado` vira PROPOSTA (F22.8) — o passo apontado pelo id, a
# resposta do dono citada LITERAL, e nenhuma escrita no plano.
checa("o desconfirmado vira proposta apontando o passo e citando a resposta",
      len(rd["propostas"]) == 1
      and rd["propostas"][0]["passo"] == "F1.2"
      and rd["propostas"][0]["citacao"] == "não existe passo nenhum que produza "
                                           "esse arquivo"
      and "não existe passo nenhum que produza esse arquivo" in rd["propostas"][0]["texto"]
      and "F1.2" in rd["propostas"][0]["texto"],
      repr(rd["propostas"]))
checa("resposta que nega a existência propõe REMOVER o passo",
      rd["propostas"][0]["acao"] == "remover", repr(rd["propostas"][0]))
rr = rodada_seguinte(rod, [dict(REVELA, resposta="na verdade quem produz é outro "
                                                 "passo, o F0.4")])
checa("resposta que contraria sem negar existência propõe REESCREVER",
      [p["acao"] for p in rr["propostas"]] == ["reescrever"], repr(rr["propostas"]))
# O FALSO-POSITIVO que a proposta trazia (F22.8): "nenhum" solto dentro de uma
# CONFIRMAÇÃO virava proposta de remover o passo que o dono acabou de confirmar.
rc_ok = rodada_seguinte(rod, [dict(REVELA, resposta="não, nenhum problema — o passo "
                                                    "está certo")])
checa("resposta que confirma com 'não, nenhum problema' NÃO vira proposta",
      rc_ok["propostas"] == [] and rc_ok["leitura"][0]["desconfirmou"] is False
      and rc_ok["fechou"] is True, repr(rc_ok))

checa("a proposta não escreve no plano — o retorno é só dado",
      all(isinstance(p, dict) for p in rr["propostas"])
      and [a for a in rr["propostas"] if a["check"] != "desconfirmado"] == [],
      repr(rr["propostas"]))

# A rodada SEGUINTE, feita da resposta sem decorrência: fecha o loop.
FECHA = {"passo": "F1.2", "check": "revelado",
         "pergunta": "a resposta trouxe scripts/gera-x.sh, que não estava na rodada "
                     "anterior — o passo passa a depender disso, ou isso fica fora "
                     "da largada?",
         "prova": "resposta: quem produz é o passo F0.9, que grava docs/x.md a "  # casa-ok: caminho ficticio dentro de fixture, nao caminho operacional
                  "partir de scripts/gera-x.sh",
         "resposta": "fica fora da largada, sim"}
r8 = rodada_seguinte(rod, [FECHA])
checa("rodada sem decorrência nenhuma FECHA o loop",
      r8["fechou"] is True and r8["perguntas"] == [] and r8["leitura"][0]["confirmou"],
      repr(r8))

# ── F22.5 · quem mediu grava, quem larga confere ────────────────────────────
# O cenário é reproduzido inteiro: plano no disco, relatório gravado a partir do
# retorno das passadas, e a casca conferindo antes de armar o motor.
PLANO_L = {"id": "PL", "phases": [{"items": [
    {"id": "F1.1", "desc": "escreve o módulo", "pronto": "a suíte passa"},
    {"id": "F1.2", "desc": "outro passo", "pronto": "o arquivo existe",
     "status": "done"}]}]}
ABERTA = {"passo": "F1.1", "check": "ato_do_dono", "classe": BLOQUEANTE,
          "pergunta": "o `pronto` do F1.1 pede aprovação do dono — quem aprova?",
          "prova": "pronto: a suíte passa"}
TOMADA = {"passo": "F1.1", "check": "tranca", "classe": BLOQUEANTE,
          "pergunta": "o passo toca documento aprovado — reabre a etapa?",
          "prova": "docs/x.md: status approved",  # casa-ok: caminho ficticio de fixture
          "respondida_por": "reabre, sim"}

lar = tempfile.mkdtemp(prefix="precheck-largada-")

v = confere_largada(lar, PLANO_L)
checa("sem relatório nenhum, a casca RECUSA largar",
      v["larga"] is False and v["motivo"] == "ausente", repr(v))

rel = grava_relatorio(lar, PLANO_L, {"1": {"perguntas": [ABERTA],
                                           "registrados": [TOMADA]}})
checa("o relatório grava a marca, o veredito e a lista de decisões TOMADAS",
      rel["veredito"] == "em-aberto" and [t["check"] for t in rel["tomadas"]] == ["tranca"]
      and rel["marca"]["plano"] and "arvore" not in rel["marca"], repr(rel))
checa("a casa do relatório é .claude/.sprint/, fora do plugin",
      os.path.exists(os.path.join(lar, ".claude", ".sprint", "precheck.json")),
      os.listdir(lar))

v = confere_largada(lar, PLANO_L)
checa("com decisão em aberto a casca RECUSA e diz QUAL decisão falta",
      v["larga"] is False and v["motivo"] == "decisao-em-aberto"
      and ABERTA["pergunta"] in v["texto"] and "F1.1" in v["texto"], repr(v))

rel = grava_relatorio(lar, PLANO_L, {"1": {"perguntas": [],
                                           "registrados": [TOMADA]}})
v = confere_largada(lar, PLANO_L)
checa("com relatório fresco e nada em aberto, a casca ACEITA largar",
      v["larga"] is True and v["motivo"] == "livre" and rel["veredito"] == "livre",
      repr(v))

# A MARCA é imune ao próprio progresso: fechar passo aberto muda o plano (menos
# passos), mas TICAR o que já estava fechado não muda nada.
PLANO_TICADO = json.loads(json.dumps(PLANO_L))
PLANO_TICADO["phases"][0]["items"][1]["status"] = "done"
checa("tique de passo já fechado NÃO vence o relatório",
      confere_largada(lar, PLANO_TICADO)["larga"] is True,
      repr(marca(PLANO_TICADO, lar)))

PLANO_MUDADO = json.loads(json.dumps(PLANO_L))
PLANO_MUDADO["phases"][0]["items"][0]["pronto"] = "a suíte passa e o gate aprova"
v = confere_largada(lar, PLANO_MUDADO)
checa("passo ABERTO reescrito VENCE o relatório, e a recusa diz que foi o plano",
      v["larga"] is False and v["motivo"] == "vencido" and v["mudou"] == ["plano"],
      repr(v))

# A ÁRVORE NÃO ENTRA NA MARCA (R-32): mexer no disco não vence o relatório — só o
# plano e o registro selado vencem. E a marca não mede nada, então não tem como
# medir errado e gravar constante nenhuma para o lado do "passou".
with open(os.path.join(lar, "mexido.txt"), "w", encoding="utf-8") as f:
    f.write("arquivo novo depois da medição\n")
checa("mexer na árvore NÃO vence o relatório, e a marca não carrega hash de árvore",
      confere_largada(lar, PLANO_L)["larga"] is True
      and list(marca(PLANO_L, lar)) == ["plano"], repr(marca(PLANO_L, lar)))

# Decisão nova selada entra na marca: o registro selado é parte do que foi medido.
selar(lar, "de agora em diante o gate roda antes", "dono")
v = confere_largada(lar, PLANO_L)
checa("decisão selada nova VENCE o relatório", v["motivo"] == "vencido", repr(v))

# E pela linha de comando, que é como a casca chama: recusa sai 3.
plano_arq = os.path.join(lar, "PL.plan.json")
with open(plano_arq, "w", encoding="utf-8") as f:
    json.dump(PLANO_L, f)
rc = subprocess.run([sys.executable, MODULO, plano_arq, "--raiz", lar, "--confere"],
                    capture_output=True, text=True)
checa("o CLI --confere sai 3 quando recusa", rc.returncode == 3, rc.stderr[-300:])


# ── F22.8 · a ROTA da proposta até o dono ───────────────────────────────────
# Proposta que só volta como valor de retorno não chega em ninguém. A rota é a que a
# casca percorre: a rodada N+1 pela linha de comando GRAVA o relatório, e o `--confere`
# do bloco 1 RECUSA a largada nomeando o passo e citando a resposta do dono.
rot = tempfile.mkdtemp(prefix="rota-")
plano_rot = os.path.join(rot, "PL.plan.json")
with open(plano_rot, "w", encoding="utf-8") as f:
    json.dump(PLANO_L, f)
resp_arq = os.path.join(rot, "respostas.json")
with open(resp_arq, "w", encoding="utf-8") as f:
    json.dump([{"passo": "F1.1", "check": "ato_do_dono",
                "pergunta": "o `pronto` do F1.1 pede aprovação do dono — quem aprova?",
                "prova": "pronto: a suíte passa",
                "resposta": "na verdade a suíte não cobre esse passo"}], f)
# A rodada N+1 RESPONDE o relatório das 4 passadas — sem ele não há o que responder,
# e o comando recusa em vez de fabricar um relatório novo.
rc = subprocess.run([sys.executable, MODULO, plano_rot, "--raiz", rot,
                     "--respostas", resp_arq], capture_output=True, text=True)
checa("a rodada N+1 sem relatório nenhum RECUSA (sai 3)",
      rc.returncode == 3 and "rode `--relatorio` antes" in rc.stderr, rc.stderr[-300:])

subprocess.run([sys.executable, MODULO, plano_rot, "--raiz", rot, "--relatorio",
                "--suite", "echo '3 suíte(s) · 0 problema(s)'"],
               capture_output=True, text=True)
_casa_rot = os.path.join(rot, ".claude", ".sprint", "precheck.json")
with open(_casa_rot, encoding="utf-8") as f:
    _rel_antes = json.load(f)
# Uma pergunta de pé no relatório — é ela que a rodada N+1 não pode fazer sumir.
_rel_antes["abertas"].append({"passo": "F9.9", "check": "ato_do_dono",
                              "pergunta": "quem aprova o F9.9?", "prova": "pronto: …",
                              "passada": "1"})
_rel_antes["veredito"] = "em-aberto"
with open(_casa_rot, "w", encoding="utf-8") as f:
    json.dump(_rel_antes, f, ensure_ascii=False)

# Respostas VAZIAS não podem esvaziar o relatório: era assim que a rodada N+1 abria a
# porta que as 4 passadas fecharam — ela REGRAVAVA o arquivo inteiro com o próprio
# resultado, e as perguntas de pé sumiam junto.
vazio_arq = os.path.join(rot, "vazio.json")
with open(vazio_arq, "w", encoding="utf-8") as f:
    json.dump([], f)
subprocess.run([sys.executable, MODULO, plano_rot, "--raiz", rot,
                "--respostas", vazio_arq], capture_output=True, text=True)
with open(os.path.join(rot, ".claude", ".sprint", "precheck.json"), encoding="utf-8") as f:
    _rel_vazio = json.load(f)
checa("rodada N+1 com respostas VAZIAS não apaga as perguntas de pé",
      len(_rel_vazio["abertas"]) == len(_rel_antes["abertas"])
      and len(_rel_antes["abertas"]) > 0,
      "antes %d · depois %d" % (len(_rel_antes["abertas"]), len(_rel_vazio["abertas"])))

rc = subprocess.run([sys.executable, MODULO, plano_rot, "--raiz", rot,
                     "--respostas", resp_arq], capture_output=True, text=True)
saida = json.loads(rc.stdout or "{}")
with open(os.path.join(rot, ".claude", ".sprint", "precheck.json"), encoding="utf-8") as f:
    rel_rot = json.load(f)
checa("a rodada N+1 pela linha de comando GRAVA a proposta no relatório",
      rc.returncode == 1
      and [pr["passo"] for pr in rel_rot["propostas"]] == ["F1.1"]
      and rel_rot["propostas"][0]["citacao"] == "na verdade a suíte não cobre esse passo"
      and saida["propostas"][0]["acao"] == "reescrever",
      rc.stdout[-400:] + rc.stderr[-200:])
rc = subprocess.run([sys.executable, MODULO, plano_rot, "--raiz", rot, "--confere"],
                    capture_output=True, text=True)
v = json.loads(rc.stdout or "{}")
checa("o --confere RECUSA a largada enquanto a proposta não for decidida",
      rc.returncode == 3 and v["motivo"] == "proposta-pendente"
      and "F1.1" in v["texto"]
      and "na verdade a suíte não cobre esse passo" in v["texto"],
      rc.stdout[-400:] + rc.stderr[-200:])


print("test_precheck_largada: %d ok, %d falha(s)" % (ok, falhas))
sys.exit(1 if falhas else 0)
