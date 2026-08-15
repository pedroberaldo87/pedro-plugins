#!/usr/bin/env python3
"""Suíte da skill spec-to-plan — o aviso vem antes da criação, e o id é próprio.

Duas coisas se provam aqui: que o TEXTO da skill manda imprimir os planos abertos
antes de gravar o plano novo (ordem no arquivo, não só presença das duas frases), e
que o programa que ela chama REALMENTE recusa reaproveitar id existente — a segunda é
comportamento rodado, não citação.
"""

import importlib
import json
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, os.pardir, os.pardir, os.pardir))
SKILL = os.path.join(AQUI, os.pardir, "skills", "plan", "SKILL.md")
PLAN_STATE = os.path.join(RAIZ, "plugins", "project-skills", "lib", "plan_state.py")

FALHAS = []


def check(rotulo, cond):
    print(("  ok   " if cond else "  FAIL ") + rotulo)
    if not cond:
        FALHAS.append(rotulo)


print("a skill spec-to-plan")
existe = os.path.isfile(SKILL)
check("existe o arquivo da skill", existe)
texto = open(SKILL, encoding="utf-8").read() if existe else ""

pos_open = texto.find("plan_state.py open")
pos_init = texto.find("plan_state.py init")
check("manda imprimir os planos abertos", pos_open != -1)
check("manda gravar o plano", pos_init != -1)
check("o aviso vem ANTES da gravacao", -1 < pos_open < pos_init)
check("diz que o id e proprio do plano", "id proprio" in texto or "id próprio" in texto)
check("diz que o init recusa renomear id existente",
      "recusa" in texto and "renomear id existente" in texto)


print("a ida ao mapa da regua")
# A "linha da ida" e a que manda extrair o CONTEUDO da regua antes da primeira
# tarefa. Sem cobrador, a proxima edicao tira a linha e ninguem percebe. O modulo
# citado sai do proprio texto (nada de caminho cravado): o que a skill nomeia tem
# que existir ao lado desta suite, com as funcoes que ela manda chamar.
MODULO = re.search(r"import (\w+) as c", texto)
check("manda montar o mapa da regua antes de escrever tarefa", MODULO is not None)
# Ancora na CHAMADA (`import <mod> as c`), nunca no nome do arquivo: `plan_state.py`
# aparece ja no passo 1 (a linha `open`), e ali a posicao seria a do aviso, nao a da ida —
# o check da ordem passava por construcao. Coberto pela mutacao L do test_mutacao_plano.py.
pos_mapa = texto.find("import %s as c" % MODULO.group(1)) if MODULO else -1
check("a ida vem ANTES da gravacao do plano", -1 < pos_mapa < pos_init)

if MODULO:
    alvo = os.path.join(AQUI, MODULO.group(1) + ".py")
    check("o programa citado existe: %s" % os.path.basename(alvo), os.path.isfile(alvo))
    if os.path.isfile(alvo):
        sys.path.insert(0, AQUI)
        mod = importlib.import_module(MODULO.group(1))
        funcs = sorted(set(re.findall(r"c\.(le_\w+|_\w+_do_projeto)", texto)))
        check("a ida chama alguma leitura do mapa", len(funcs) >= 1)
        for f in funcs:
            check("%s existe em %s" % (f, os.path.basename(alvo)), hasattr(mod, f))


print("a oferta da frente (R-23)")
# A oferta vem ANTES da gravacao — depois dela a frente nao entra mais no JSON.
pos_frente = texto.find("ofereça a frente")
check("a skill oferece a frente", pos_frente != -1)
check("a oferta vem ANTES da gravacao", -1 < pos_frente < pos_init)
check("a branch e a oferta padrao, no formato feature/<slug>",
      "Branch é a oferta padrão" in texto and "feature/<slug>" in texto)
check("a worktree e so para paralelo real", "paralelo real" in texto)
check("a recusa se grava em limites",
      "Recusou" in texto and '"limites"' in texto)
check("recusa gravada cala a oferta ate o dono pedir",
      "a oferta se cala" in texto and "só volta a oferecer se o dono pedir" in texto)


print("a caca das cinco classes (R-21)")
# A passada vem ANTES da gravacao — decisao achada depois do init nao entra no plano.
pos_caca = texto.find("as cinco classes")
check("a skill manda fazer a passada das cinco classes", pos_caca != -1)
check("a passada vem ANTES da gravacao", -1 < pos_caca < pos_init)
for classe in ("Ato do dono", "Escolha sem critério", "Máquina", "Tranca", "Disputa"):
    check("a classe %s esta nomeada" % classe, ("**%s**" % classe) in texto)
# Classe sem lugar no JSON e classe que ninguem sabe gravar.
for campo in ("espera_dono", "decidido", "pendencia"):
    check("a passada diz onde gravar: %s" % campo, ("`%s`" % campo) in texto)
check("toda pendencia caçada nasce com a prova que a implica",
      "a prova que a implica" in texto)
check("impedimento de memoria nao vira pendencia",
      "de memória" in texto and "não há pendência a gravar" in texto)

# F12.7 — o agente alegava dependencia do dono sem fazer o trabalho que torna a
# decisao decidivel. A proibicao e o mandado de investigar ficam POR ESCRITO na skill.
check("adiar decisao por falta de material esta proibido",
      "Decidir depois é opção, nunca necessidade" in texto
      and "Falta de material não adia decisão" in texto)
check("manda investigar ate a decisao ficar decidivel",
      "Investigar até a decisão ficar decidível" in texto)
check("pendencia sem investigacao esta nomeada como etapa encoberta",
      "sem investigação é etapa encoberta" in texto)
check("a desculpa de deixar pendente por falta de material esta refutada",
      "falta material para decidir, deixo pendente para o dono" in texto)

# F12.8 — uma passada so ja deixou decisao escondida duas vezes. O rito e REPETIR ate
# uma rodada voltar vazia, e a condicao de saida fica por escrito na skill.
pos_repetir = texto.find("repita até uma rodada voltar vazia")
check("a skill manda repetir a caca ate uma rodada voltar vazia", pos_repetir != -1)
check("o rito de repetir vem ANTES da gravacao", -1 < pos_repetir < pos_init)
check("achou decisao nova, roda a passada de novo do primeiro passo",
      "rode a passada de novo, do primeiro passo" in texto)
check("a rodada vazia e a condicao de saida do passo",
      "sem nenhuma\ndecisão nova" in texto and "condição de saída" in texto)
check("rodada vazia nao e rodada pulada",
      "Rodada vazia não é rodada pulada" in texto)
check("a desculpa de uma passada so esta refutada",
      "já fiz a passada uma vez, está caçado" in texto)


# A secao de racionalizacoes: a desculpa fica REFUTADA no texto antes de o modelo
# da-la. Sem cobrador, a proxima edicao a apaga e ninguem percebe.
print("as racionalizacoes estao refutadas por escrito")
check("a skill tem a secao de racionalizacoes", "## Racionalizações" in texto)
check("a desculpa de escrever o plano direto esta refutada",
      "escrevo o plano direto" in texto)
check("a desculpa do pronto generico esta refutada",
      "pode ser genérico" in texto)
check("a desculpa de dispensar a auditoria esta refutada",
      "dispenso a auditoria" in texto)
check("a desculpa do passo grande demais esta refutada",
      "quem executar se vira" in texto)


print("o programa que a skill chama")
PLANO = {
    "id": "2026-01-01-teste",
    "title": "Plano de teste da suite",
    "requisitos": [{"id": "S-1", "titulo": "Um requisito", "ca": "um criterio de aceite"}],
    "phases": [{"id": "F1", "title": "Uma fase", "items": [{
        "id": "F1.1", "title": "Uma tarefa que faz uma coisa",
        "desc": "A tarefa existe para a suite ter o que gravar.",
        "requisito": "S-1", "pronto": "o comando roda e devolve zero", "status": "todo"}]}],
}

with tempfile.TemporaryDirectory() as d:
    def roda(plano):
        f = os.path.join(d, "in.json")
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(plano, fh, ensure_ascii=False)
        return subprocess.run([sys.executable, PLAN_STATE, "--dir", d, "init", "--file", f],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              start_new_session=True)

    primeiro = roda(PLANO)
    check("grava o plano novo", primeiro.returncode == 0)

    outro = json.loads(json.dumps(PLANO))
    outro["phases"][0]["items"][0]["title"] = "Outra tarefa com outro nome"
    segundo = roda(outro)
    check("recusa reaproveitar o id com outro conteudo", segundo.returncode != 0)
    check("a recusa diz por que", "recusado" in (segundo.stdout + segundo.stderr))

    # As DUAS saidas da oferta da frente sao gravaveis de verdade — citacao na skill
    # que o gravador recusasse seria instrucao morta.
    aceita = json.loads(json.dumps(PLANO))
    aceita["id"] = "2026-01-02-frente-aceita"
    aceita["frente"] = {"branch": "feature/frente-aceita", "worktree": d}
    r = roda(aceita)
    check("grava o plano com a frente aceita", r.returncode == 0)

    recusada = json.loads(json.dumps(PLANO))
    recusada["id"] = "2026-01-03-frente-recusada"
    recusada["limites"] = [{"limite": "sem branch de frente: o plano corre na árvore atual",
                            "motivo": "o dono recusou a oferta ao montar o plano"}]
    r = roda(recusada)
    check("grava a recusa da frente como limite", r.returncode == 0)

print("FALHAS: %d" % len(FALHAS))
sys.exit(1 if FALHAS else 0)
