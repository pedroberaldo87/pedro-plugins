#!/usr/bin/env python3
"""As travas que a reescrita de 2026-08-06 instalou no motor do sovai.

Cada check aqui corresponde a um passo do plano `2026-08-06-a-metodologia-vira-mecanismo`
e cobra a MECANICA, nao a boa intencao: a frase tem que estar no lugar que o motor le
(o esqueleto JS ou o texto que o papel recebe), nao numa secao de filosofia.

O que este arquivo NAO cobre, e por que: a metade de EXECUCAO de cada passo — o motor
rodando de ponta a ponta contra um plano de mentira. Isso e teste de integracao e nao cabe
aqui; o que este arquivo garante e que a LOGICA esta escrita no script, com a direcao
segura. Os dois se somam; nenhum substitui o outro. F9.10, F9.12, F9.13, F9.14 e F9.15 ja
tem a metade de bancada: `test_motor_bancada.py` executa o esqueleto e afere o ARQUIVO do
plano, o desligamento por teto de gasto, a derrubada pelo vigia, a onda verde salva no
historico e a onda vermelha que nao salva e denuncia a suite que quebrou.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "project-skills", "skills", "sprint", "SKILL.md")
# A COPIA vendorada, nao a fonte em _shared/: e ela que viaja com o plugin instalado, e
# e ela que o bloco da skill chama.
RESOLVEDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "..", "project-skills", "skills", "sprint", "resolve-plugin.sh")

FAILS = []
TOTAL = [0]


def check(label, cond):
    TOTAL[0] += 1
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s" % label)
        FAILS.append(label)


def esqueleto(texto):
    """So o bloco ```javascript do motor — regra que vale pro SCRIPT nao pode ser
    cobrada em prosa solta, senao 'esta escrito' vira 'esta mencionado'."""
    # O MAIOR bloco javascript, nao o primeiro: a skill tem mais de um exemplo em JS
    # (o bloco de esforco do F9.1 vem antes), e pegar o primeiro media o arquivo errado.
    blocos = re.findall(r"```javascript\n(.*?)\n```", texto, re.S)
    return max(blocos, key=len) if blocos else ""


def conversao_do_script(js):
    """A linha do esqueleto que normaliza o parametro — extraida do proprio SKILL.md,
    para que o teste rode O QUE ESTA ESCRITO la, e nao uma copia que envelhece."""
    m = re.search(r"^const ARGS = .*$", js, re.M)
    return m.group(0) if m else ""


def bloco_da_fila(js):
    """O trecho do esqueleto que decide QUEM entra na fila — do `parado` ao
    `esperandoVoce`. Recortado do proprio SKILL.md pelo mesmo motivo do
    `conversao_do_script`: o teste roda o que esta escrito la, nao uma copia."""
    i = js.find("const parado = new Set(")
    j = js.find(".map(t => ({ taskId: t.id, motivo: esperaChain.get(t.id) }))")
    if i < 0 or j < 0:
        return ""
    return js[i:j + len(".map(t => ({ taskId: t.id, motivo: esperaChain.get(t.id) }))")]


def chamada_do_auditor(js):
    """A chamada do `auditorPrompt` no esqueleto — do nome ao `schema: AUDITOR`. A lente
    invertida e a lista do que havia a mao valem para o SCRIPT: cobra-las na prosa deixa o
    auditor sendo chamado sem elas."""
    i = js.find("auditorPrompt(")
    j = js.find("schema: AUDITOR", i)
    return js[i:j] if i >= 0 and j >= 0 else ""


def roda_a_fila(bloco, decomp_js, blockers_js="[]"):
    """Executa o bloco da fila com uma decomposicao de mentira e devolve o que
    saiu — a fila e a lista de espera. Sem Node o check nao inventa aprovacao."""
    if not bloco:
        return {"erro": "SEM-BLOCO"}
    if not shutil.which("node"):
        return {"erro": "SEM-NODE"}
    prog = ("const blockers = %s; const decomp = %s;\n%s\n"
            "console.log(JSON.stringify({ fila: todo.map(t => t.id), esperandoVoce }))\n"
            % (blockers_js, decomp_js, bloco))
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    if out.returncode != 0:
        return {"erro": out.stderr.strip()[:200]}
    try:
        return json.loads(out.stdout.strip())
    except ValueError:
        return {"erro": "saida ilegivel: %s" % out.stdout.strip()[:200]}


def bloco_da_tranca(js):
    """O trecho do esqueleto que trata tarefa em arquivo sob tranca (F8.5) — do
    `protegidas` ate o comeco da revisao. Recortado do proprio SKILL.md pelo mesmo
    motivo dos outros: o teste roda o que esta escrito la, nao uma copia."""
    i = js.find("const protegidas = new Set(")
    j = js.find("// REVISAR — Opus #2")
    if i < 0 or j < 0 or j < i:
        return ""
    return js[i:j]


def roda_a_tranca(bloco, decomp_js, results_js):
    """Executa o bloco da tranca com uma decomposicao e respostas de mentira, e devolve
    o que saiu — os bloqueios e os resultados depois do tratamento."""
    if not bloco:
        return {"erro": "SEM-BLOCO"}
    if not shutil.which("node"):
        return {"erro": "SEM-NODE"}
    prog = ("const blockers = []; const decomp = %s; const results = %s;\n%s\n"
            "console.log(JSON.stringify({ blockers, results }))\n"
            % (decomp_js, results_js, bloco))
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    if out.returncode != 0:
        return {"erro": out.stderr.strip()[:200]}
    try:
        return json.loads(out.stdout.strip())
    except ValueError:
        return {"erro": "saida ilegivel: %s" % out.stdout.strip()[:200]}


def bloco_da_regua(js):
    """O trecho do esqueleto que roda a regua do `pronto` sobre cada tarefa (F8.2) — da
    chamada do papel ate o corte da lista. Recortado do proprio SKILL.md pelo mesmo
    motivo dos outros: o teste roda o que esta escrito la, nao uma copia."""
    i = js.find("const regua = await agent(reguaPrompt(")
    fim = "decomp.tasks = decomp.tasks.filter(t => !bancada.has(t.id))"
    j = js.find(fim)
    if i < 0 or j < 0 or j < i:
        return ""
    return js[i:j + len(fim)]


def roda_a_regua(bloco, decomp_js, regua_js):
    """Executa o bloco da regua com uma decomposicao de mentira e o veredito que o papel
    devolveria, e diz o que sobrou: as tarefas que seguem para o executor e os bloqueios."""
    if not bloco:
        return {"erro": "SEM-BLOCO"}
    if not shutil.which("node"):
        return {"erro": "SEM-NODE"}
    prog = ("const blockers = []; const decomp = %s;\n"
            "const ARGS = { repoRoot: '/raiz', model: 'opus' };\n"
            "const T = { mechanical: { effort: 'low' } };\n"
            "const REGUA = 'schema'; const reguaPrompt = x => JSON.stringify(x);\n"
            "const agent = async () => (%s);\n"
            "(async () => {\n%s\n"
            "console.log(JSON.stringify({ blockers, fila: decomp.tasks.map(t => t.id) }))\n"
            "})()\n" % (decomp_js, regua_js, bloco))
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    if out.returncode != 0:
        return {"erro": out.stderr.strip()[:200]}
    try:
        return json.loads(out.stdout.strip())
    except ValueError:
        return {"erro": "saida ilegivel: %s" % out.stdout.strip()[:200]}


def veredito_da_regua_real(pronto, onde):
    """O que o programa de verdade (`regua_pronto.py`, do plugin visual) diz do criterio.
    Sem isto o teste provaria so o encanamento: o criterio de mentira usado no caso de
    bancada tem que ser um que a regua REAL reprova, senao o cenario e faz-de-conta."""
    prog = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "project-skills", "lib", "regua_pronto.py")
    if not os.path.exists(prog):
        return None
    out = subprocess.run([sys.executable, prog, "--onde", onde, "-"],
                         input=pronto, capture_output=True, text=True, start_new_session=True)
    return out.returncode


def bloco_da_compilacao(texto):
    """O bloco ```bash do passo que compila os alvos ANTES do motor (F9.34). Recortado
    da secao dele, para que o teste rode o passo que a casca roda — nao uma copia."""
    sec = texto.split("### A compilação cara é paga UMA vez")[-1].split("\n### ")[0]
    blocos = re.findall(r"```bash\n(.*?)\n```", sec, re.S)
    return blocos[0] if blocos else ""


def roda_a_compilacao(bloco, raiz):
    """Roda o passo da casca contra um projeto de mentira cujo compilador ANOTA se
    compilou do zero (FULL) ou aproveitou o cache (INCR). Devolve o que saiu no
    `buildWarm` e o registro do compilador depois da SEGUNDA compilacao — a do
    executor, que roda o mesmo comando depois do passo da casca."""
    if not bloco:
        return {"erro": "SEM-BLOCO"}
    compilador = os.path.join(raiz, "compilar.sh")
    registro = os.path.join(raiz, "registro.txt")
    with open(compilador, "w") as f:
        f.write('#!/bin/sh\n'
                'if [ -d "$PWD/.cache-de-build" ]; then echo INCR >> "$PWD/registro.txt"\n'
                'else mkdir "$PWD/.cache-de-build"; echo FULL >> "$PWD/registro.txt"; fi\n')
    os.chmod(compilador, 0o755)
    amb = dict(os.environ)
    amb.update({"CLAUDE_CONFIG_DIR": os.path.join(raiz, "config"),
                "CLAUDE_CODE_SESSION_ID": "sessao-de-teste",
                "SOVAI_REPO_ROOT": raiz,
                "SOVAI_BUILD_CMD": "./compilar.sh"})
    casca = subprocess.run(["sh", "-c", bloco], capture_output=True, text=True, env=amb, stdin=subprocess.DEVNULL, start_new_session=True)
    if casca.returncode != 0:
        return {"erro": casca.stderr.strip()[:200]}
    # A compilacao do EXECUTOR: o mesmo comando, depois do passo da casca.
    subprocess.run(["sh", "-c", "./compilar.sh"], cwd=raiz, capture_output=True, env=amb, stdin=subprocess.DEVNULL, start_new_session=True)
    with open(registro) as f:
        passadas = f.read().split()
    return {"saida": casca.stdout.strip(), "passadas": passadas}


def bloco_da_colheita(trecho):
    """O bloco ```bash que manda colher, recortado do trecho que o recebe (o passo 4 da
    Persistencia ou a definicao do papel). O teste roda O QUE ESTA ESCRITO la — comparar
    a string com ela mesma trava o defeito em vez de pega-lo, que era o buraco antigo."""
    blocos = re.findall(r"```bash\n(.*?)\n *```", trecho, re.S)
    achados = [b for b in blocos if "colhe-turno" in b]
    return textwrap.dedent(achados[0]) if achados else ""


def planta_o_lixeiro(raiz, layout, quebra=False):
    """Monta a arvore que o comando vai ter que resolver e devolve o CLAUDE_PLUGIN_ROOT.

    `cache` = o layout REAL do marketplace instalado (`<marketplace>/<plugin>/<versao>/`,
    verificado em ~/.claude/plugins/cache), com DUAS versoes do lixeiro para cobrar a
    escolha da mais alta. `repo` = rodando do repositorio, onde o lixeiro e irmao direto.
    `ausente` = maquina sem lixeiro.

    A copia vendorada do `resolve-plugin.sh` entra na arvore junto: e ELA que o bloco
    chama, e sem ela o teste provaria o resolvedor de mentira em vez do que viaja com o
    plugin instalado."""
    stub = ('import sys\n'
            'sys.stderr.write("QUEBROU\\n")\n'
            'sys.exit(1)\n' if quebra else
            'import sys\n'
            'print("COLHEU", __file__, " ".join(sys.argv[1:]))\n')

    def poe(caminho):
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w") as f:
            f.write(stub)

    if layout == "cache":
        root = os.path.join(raiz, "pedro-plugins", "sovai", "1.13.0")
        for v in ("1.9.0", "1.10.0", "1.8.2"):
            poe(os.path.join(raiz, "pedro-plugins", "lixeiro", v, "lib", "lixeiro.py"))
    elif layout == "repo":
        root = os.path.join(raiz, "plugins", "sovai")
        poe(os.path.join(raiz, "plugins", "lixeiro", "lib", "lixeiro.py"))
    else:
        root = os.path.join(raiz, "pedro-plugins", "sovai", "1.13.0")
    os.makedirs(root, exist_ok=True)
    destino = os.path.join(root, "skills", "sprint", "resolve-plugin.sh")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    shutil.copy(RESOLVEDOR, destino)
    return root


def roda_a_colheita(bloco, layout, quebra=False):
    """Executa o comando da skill contra a arvore plantada. Devolve o codigo de saida e
    o que saiu — e o par que separa 'lixeiro nao instalado' (calado) de 'resolvi o
    caminho e o comando quebrou' (visivel)."""
    if not bloco:
        return {"erro": "SEM-BLOCO"}
    raiz = tempfile.mkdtemp(prefix="sovai-colheita-")
    try:
        root = planta_o_lixeiro(raiz, layout, quebra)
        amb = dict(os.environ)
        amb.update({"CLAUDE_PLUGIN_ROOT": root,
                    "CLAUDE_CODE_SESSION_ID": "sessao-de-teste",
                    # A ultima tentativa do resolvedor varre o cache da MAQUINA. Sem
                    # apontar o cache para a arvore de mentira, o caso `ausente` acharia
                    # o lixeiro de verdade de quem roda o teste e provaria o contrario.
                    "CLAUDE_CONFIG_DIR": os.path.join(raiz, "config")})
        out = subprocess.run(["bash", "-c", bloco], capture_output=True, text=True,
                             env=amb, stdin=subprocess.DEVNULL, start_new_session=True)
        return {"rc": out.returncode,
                "saida": (out.stdout + out.stderr).strip()}
    finally:
        shutil.rmtree(raiz, ignore_errors=True)


def roda_em_node(conv, entrada):
    """Executa a linha de conversao com um `args` de mentira. Sem Node na maquina o
    check nao inventa aprovacao: devolve o motivo, e o teste falha."""
    if not conv:
        return "SEM-CONVERSAO"
    if not shutil.which("node"):
        return "SEM-NODE"
    prog = "const args = %s;\n%s\nconsole.log(ARGS.severityFloor)\n" % (entrada, conv)
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    return out.stdout.strip() if out.returncode == 0 else "ERRO: %s" % out.stderr.strip()


def main():
    texto = open(SKILL_MD, encoding="utf-8").read()
    js = esqueleto(texto)
    check("o esqueleto do motor foi encontrado", len(js) > 2000)

    print("F8.2 — o criterio e julgado antes de soltar quem executa")
    check("criterio ruim vira bloqueio, nao tarefa", "kind: 'criterio'" in texto)
    check("a regua e sobre a ORIGEM do valor, nao o caminho do arquivo",
          "regerar o entregável a partir do dado real" in texto
          and "injetar valor inventado" in texto)
    # O defeito: o julgamento so existia como instrucao ao #1. Instrucao em prosa nao
    # recusa nada — o que se cobra aqui e o SCRIPT rodando a regua e emitindo o bloqueio.
    check("o SCRIPT roda a regua, nao so a prosa", "reguaPrompt" in js)
    check("a regua roda ANTES de soltar executor",
          "reguaPrompt" in js and "agent(execPrompt" in js
          and js.index("reguaPrompt") < js.index("agent(execPrompt"))
    check("o julgamento e do programa, nao de quem le",
          "regua_pronto.py" in texto and "`REGUA`" in texto)
    check("o veredito chega por schema, nao por texto solto", "schema: REGUA" in js)

    bloco = bloco_da_regua(js)
    check("o bloco da regua foi encontrado no esqueleto", len(bloco) > 200)
    ruim = ("o numero de agentes aparece no relatorio final em "
            ".claude/visual/relatorio.html")
    bom = ("a pagina e regerada a partir do plano em disco e abre sem erro "
           "no navegador")
    check("o criterio ruim do caso e reprovado pela regua REAL",
          veredito_da_regua_real(ruim, "F1") == 1)
    check("o criterio bom do caso passa na regua REAL",
          veredito_da_regua_real(bom, "F2") == 0)

    decomp = json.dumps({"tasks": [
        {"id": "F1", "requisito": "S-14", "pronto": ruim, "files": ["a.py"]},
        {"id": "F2", "requisito": "S-9", "pronto": bom, "files": ["b.py"]}]})
    saiu = roda_a_regua(bloco, decomp,
                        json.dumps({"reprovados": [
                            {"task_id": "F1", "motivo": "F1: o critério fecha com o valor DENTRO do entregável"}]}))
    check("a tarefa de criterio-bancada NAO chega ao executor",
          saiu.get("fila") == ["F2"])
    check("o bloqueio sai com kind 'criterio' e o taskId",
          any(b.get("kind") == "criterio" and b.get("taskId") == "F1"
              for b in saiu.get("blockers", [])))
    check("o bloqueio diz que ninguem foi solto e o que reescrever",
          any("nenhum executor foi solto" in b.get("whyNeedsYou", "")
              and "S-14" in b.get("whyNeedsYou", "")
              for b in saiu.get("blockers", [])))
    # Fail-open, mesma direcao da reserva: gate mudo nao pode travar a missao inteira.
    mudo = roda_a_regua(bloco, decomp, "null")
    check("papel mudo nao recusa ninguem (fail-open)",
          mudo.get("fila") == ["F1", "F2"] and mudo.get("blockers") == [])

    print("F9.1 — o esforco vai escrito DENTRO do texto do script")
    check("a skill manda gerar o bloco como constante literal",
          "não leia de args.tiers" in texto or "não leia de `args.tiers`" in texto)
    check("a skill diz por que o canal em tempo de execucao caiu",
          "chegava `undefined`" in texto and "matava o motor na primeira volta" in texto)
    # O defeito era o esqueleto fazer o contrario do que o texto manda: a trava cobra o
    # SCRIPT, nao a prosa. Leitura em tempo de execucao nao pode sobrar em lugar nenhum.
    check("o esqueleto NAO le o esforco dos parametros", "ARGS.tiers" not in js)
    check("o esqueleto traz a constante literal com as seis etapas",
          re.search(r"const T = \{[\s\S]{0,400}?decompose: \{effort:'high'\}", js) is not None
          and all(e in js for e in ("coordinate: {effort:'medium'}", "executor: {effort:'medium'}",
                                    "mechanical: {effort:'low'}", "diagnose: {effort:'medium'}",
                                    "finalize: {effort:'medium'}")))

    print("F9.2 — o motor CHAMA a reserva antes de executar")
    # A peca existia e nenhum motor a chamava. O que se cobra aqui e a CHAMADA no
    # SCRIPT, nao a mencao em prosa: mecanismo descrito e nao invocado foi o defeito.
    check("o motor consulta a reserva no script", "reservaPrompt" in js)
    check("a consulta vem ANTES de soltar executor",
          "reservaPrompt" in js and "agent(execPrompt" in js
          and js.index("reservaPrompt") < js.index("agent(execPrompt"))
    check("o que se reserva e a lista de arquivos da onda",
          "arquivosDaOnda" in js and "t.files || []" in js)
    check("recusado, a onda NAO sai",
          re.search(r"reserva\?\.recusado[\s\S]{0,600}?\bbreak\b", js) is not None)
    check("o bloqueio nomeia os arquivos em disputa", "reserva.arquivos" in js)
    check("a skill nomeia o script e o verbo que o motor roda",
          "reserva-de-arquivos.sh reservar" in texto)
    check("o veredito chega por schema, nao por texto solto",
          "RESERVA" in js and "`RESERVA`" in texto)
    check("quem entrega LIBERA a reserva", "reserva-de-arquivos.sh)\" liberar" in texto)
    check("a sessao e o motor chegam ao script pelo args",
          "ARGS.sessionId" in js and "ARGS.motorId" in js)

    print("F9.4/F9.5/F9.8 — as tres regras de quem executa")
    check("conferir no disco e o PRIMEIRO passo",
          "CONFIRA NO DISCO ANTES DE IMPLEMENTAR" in texto)
    check("formatar o projeto inteiro aparece como proibido",
          "FORMATAR O PROJETO INTEIRO É PROIBIDO" in texto)
    check("os comandos proibidos sao nomeados, nao so a categoria",
          "prettier --write ." in texto and "ruff format ." in texto)
    check("a sonda nasce fora do alcance da suite",
          "SONDA DE DEPURAÇÃO NASCE FORA DO ALCANCE DA SUÍTE" in texto)
    check("os nomes que a suite coleta sao nomeados",
          "test_*.py" in texto and "*.spec.ts" in texto)
    check("quem revisa segue a MESMA regra da sonda",
          "O revisor manda a sonda dele para fora do alvo da suíte" in texto)

    print("F9.9 — a janela de tempo da sessao nao da pra observar")
    check("a skill separa as duas coisas",
          "O quanto de conversa já foi usado" in texto
          and "Quanto tempo falta na janela da sessão" in texto)
    check("a skill diz a estrategia de parada que sobra",
          "a estratégia de parada, então, não é temporal" in texto.lower()
          or "A estratégia de parada, então, não é temporal" in texto)

    print("F9.10 — o motor escreve no plano o que fez")
    check("o script tica o plano, e no SCRIPT (nao na prosa)", "tickPlanPrompt" in js)
    check("a marcacao leva a prova do executor",
          "evidencia:" in js and "files_touched" in js)
    check("so tica quem devolveu done", "filter(x => x?.done" in js)
    # Sem o comando escrito, `tickPlanPrompt` e um papel sem acao: o marcador nao tem o
    # que rodar e o plano continua parado. O que roda o comando de verdade e o
    # test_motor_bancada.py; aqui se cobra que ele EXISTE na skill.
    # O comando deixou de trazer o caminho cravado (F9.51): ele agora nasce de uma BUSCA
    # pelo nome do plugin, numa linha, e roda na seguinte com a variavel. Cobrar
    # `plan_state.py --dir` na mesma linha do `tick` reprovava justamente o conserto —
    # e o `<plano>` que estava aqui nem era argumento que o programa aceita.
    check("a skill nomeia o comando que marca o plano",
          "resolve-plugin.sh" in texto and "lib/plan_state.py" in texto
          and "tick <taskId> --evidencia" in texto)
    check("a prova gravada e a do executor, nao redigida por quem marca",
          "nunca redigida por quem marca" in texto)

    print("F9.12 — disjuntor por consumo")
    check("o teto existe como knob", "tokenBudget" in js)
    # Casa a linha DO DISJUNTOR, nao a aparicao do nome em qualquer lugar: `gastoInicial`
    # tambem aparece no `return`, entao procurar o nome solto deixava passar um disjuntor
    # medindo o gasto do TURNO em vez do da missao. Furo achado por mutacao, 2026-08-06.
    check("o motor mede o DELTA da missao, nao o gasto do turno",
          re.search(r"const gasto = gastoAgora\(\) - gastoInicial", js) is not None)
    check("estourou, ele PARA", re.search(r"desligadoPor = 'orcamento'[\s\S]{0,400}?\bbreak\b", js) is not None)
    check("o relatorio diz quanto gastou e em que rodada",
          "gastou ${gasto} de ${tokenBudget}" in js)
    # O numero tem que chegar ao relatorio FINAL tambem: desligar sem dizer o quanto
    # queimou deixa o dono sem saber se relanca com teto maior ou se corta a missao.
    check("o gasto entra no relatorio final, nao so no bloqueio",
          "o `gasto` (quanto a missão queimou" in texto)

    print("F9.13 + F9.24 — vigia por tempo, que separa demora de travamento")
    check("o limite de silencio existe", "silenceLimitMs" in js)
    check("a condicao e DUPLA: mudo E sem trabalho vivo",
          "mudo > silenceLimitMs && !suite?.trabalhoVivo" in js)
    check("trabalho vivo esta no schema que a suite devolve", "trabalhoVivo" in texto)
    check("o vigia derruba parando o laco",
          re.search(r"desligadoPor = 'vigia'[\s\S]{0,400}?\bbreak\b", js) is not None)
    check("o blocker distingue travamento de demora",
          "travamento, não demora" in js)

    print("F9.14 + F9.15 — ponto de salvamento por onda, e onda vermelha nao salva")
    check("a suite roda ao fim de CADA onda, dentro do laco", "runSuitePrompt" in js)
    check("onda verde vira checkpoint", "suite.green" in js and "checkpointPrompt" in js)
    check("onda vermelha NAO vira checkpoint",
          js.index("checkpointPrompt") < js.index("a suíte quebrou na rodada"))
    check("a skill nomeia o comando que grava a onda no historico",
          re.search(r"git -C <raiz> add -A && git -C <raiz> commit .*<r>", texto) is not None)
    check("o salvamento e local: o push e uma vez, no fim", "Commit **local e só**" in texto)
    check("a suite morta tambem nao salva (direcao segura)",
          "a suíte da rodada ${r} não respondeu" in js)
    check("o relato diz QUAL suite quebrou", "suite.failing?.join" in js)

    print("F9.16 — quem julga prova que leu a coisa inteira")
    check("o veredito exige a ancora do fim", "âncora do fim" in texto)
    check("veredito sem ancora e RECUSADO", "é **recusado**" in texto)
    check("a ancora entra no schema do executor", "**`anchor`**" in texto)

    print("F9.18 + F9.21 — auditor com a lente invertida")
    check("bloqueio repetido convoca auditor, nao encerra",
          "não encerra nada sozinho" in texto)
    check("o onus e do auditor provar que NAO da", "lente invertida" in texto)
    check("o auditor lista o que o executor nem tentou",
          "quais o executor nem tentou" in texto)
    check("os dois desfechos estao escritos",
          "derruba** a alegação devolve a tarefa ao loop" in texto
          and "confirma** encerra a tarefa como impedimento real" in texto)
    # A prova aqui e a CHAMADA no esqueleto, nao a mencao na prosa: a lente invertida e a
    # lista do que havia a mao so chegam no auditor se forem argumento do `auditorPrompt`.
    chamada = chamada_do_auditor(js)
    check("a chamada do auditor existe no esqueleto", chamada != "")
    check("a chamada carrega o onus invertido (provar que NAO da)",
          "onus:" in chamada and "não dá" in chamada)
    check("a chamada carrega a lista do que havia a mao",
          "ferramentas: x.ferramentas" in chamada)
    check("a chamada cobra o que o executor nem tentou",
          "naoTentou" in chamada)

    print("F9.19 — o relatorio separa impedimento de falta de tempo")
    check("as duas listas saem separadas do motor",
          "impedidos" in js and "naoDeuTempo" in js)
    check("cada impedimento carrega o motivo", "motivo: b.what" in js)
    check("a diferenca entre os dois esta escrita",
          "impedimento não sai com mais tempo" in js)

    print("F9.20 — quem depende de passo parado nasce parado")
    check("o bloqueio se propaga por transitividade",
          "cresceu" in js and "dependsOn" in js and "parado.add(t.id)" in js)
    check("quem espera sai da fila de execucao",
          "!parado.has(t.id)" in js and "esperando" in js)

    print("F8.4 — passo que espera um ato do dono nao e tentado, e quem depende espera junto")
    check("o campo esta declarado no schema do decompositor",
          "esperaDono?: string" in texto)
    check("o decompositor COPIA do plano, nao julga",
          "o `espera_dono` do passo no `.plan.json` vira `esperaDono`" in texto)
    check("a espera tem secao propria no relatorio, fora de Bloqueios",
          "### Esperando você (não é falha)" in texto)
    # A METADE DE EXECUCAO: o bloco da fila roda de verdade, com uma decomposicao em que
    # F1 espera o dono, F2 depende de F1 e F3 nao depende de ninguem. Cobrar so a frase
    # deixaria passar um motor que escreve a regra e solta o executor assim mesmo.
    bloco = bloco_da_fila(js)
    decomp = ("{ tasks: ["
              "{ id: 'F1', esperaDono: 'publicar o site' },"
              "{ id: 'F2', dependsOn: ['F1'] },"
              "{ id: 'F3', dependsOn: [] }] }")
    saiu = roda_a_fila(bloco, decomp)
    check("o bloco da fila foi encontrado e rodou", "erro" not in saiu)
    check("o passo que espera o dono NAO entra na fila", saiu.get("fila") == ["F3"])
    ev = {x["taskId"]: x["motivo"] for x in saiu.get("esperandoVoce", [])}
    check("os DOIS saem como espera, nao somem", sorted(ev) == ["F1", "F2"])
    check("o motivo de quem espera nomeia o ATO do dono",
          "publicar o site" in ev.get("F1", ""))
    check("o motivo de quem depende nomeia de QUEM depende",
          "F1" in ev.get("F2", "") and "espera você" in ev.get("F2", ""))
    # Tarefa parada por `blocker` ja sai em `impedidos`: repetir aqui mandaria o dono
    # agir duas vezes pelo mesmo motivo.
    so_blocker = roda_a_fila(bloco, "{ tasks: [{ id: 'F1' }] }", "[{ taskId: 'F1' }]")
    check("bloqueio comum sai da fila mas NAO vira espera",
          so_blocker.get("fila") == [] and so_blocker.get("esperandoVoce") == [])

    print("F8.5 — tarefa em arquivo sob tranca entrega proposta, e o criterio inverte")
    check("o campo esta declarado no schema do decompositor",
          "protegido?: string" in texto)
    check("a regua da tranca e de DISCO, nao de julgamento",
          "`status: approved` no frontmatter é arquivo sob tranca" in texto)
    check("a tarefa protegida CONTINUA na fila (ao contrario da que espera o dono)",
          "Tarefa `protegido` **entra na fila**" in texto)
    check("o executor recebe a regra por escrito, no texto que ele le",
          "ARQUIVO SOB TRANCA: O ENTREGÁVEL É A PROPOSTA, NÃO A EDIÇÃO" in texto)
    check("o antes e o depois sao exigidos LITERAIS",
          "`antes` = o trecho que está no disco hoje, copiado caractere por caractere"
          in texto)
    check("o campo entra no schema do executor",
          "proposta?: { arquivo, antes, depois }" in texto)
    check("o revisor recebe git diff vazio como o resultado CERTO",
          "`git diff` vazio no arquivo protegido é o resultado CERTO" in texto)
    check("furar a tranca REPROVA (a inversao vale pros dois lados)",
          "arquivo protegido que **aparece** no `git diff` é gap de `kind: 'spec'`"
          in texto)
    # A CHAMADA no script: lista que o motor monta e nao entrega ao #2 e inversao que
    # so existe na prosa — o revisor continuaria medindo pela regua normal.
    check("o motor entrega a lista de protegidas ao revisor, no SCRIPT",
          "protegidas: [...protegidas]" in js)
    # A METADE DE EXECUCAO: o bloco roda de verdade, com uma tarefa protegida que voltou
    # com proposta completa e outra que voltou so com resumo.
    tranca = bloco_da_tranca(js)
    decomp_t = ("{ tasks: [{ id: 'P1', protegido: 'docs/visao.md tem status: approved' },"
                "{ id: 'P2', protegido: 'docs/visao.md tem status: approved' },"
                "{ id: 'N1' }] }")
    results_t = ("[{ task_id: 'P1', done: true, summary: 'ajustar a meta',"
                 "   proposta: { arquivo: 'docs/visao.md', antes: 'LINHA VELHA', depois: 'LINHA NOVA' } },"
                 " { task_id: 'P2', done: true, summary: 'trocar o titulo' },"
                 " { task_id: 'N1', done: true, summary: 'codigo normal' }]")
    saiu = roda_a_tranca(tranca, decomp_t, results_t)
    check("o bloco da tranca foi encontrado e rodou", "erro" not in saiu)
    feito = {x["task_id"]: x["done"] for x in saiu.get("results", [])}
    check("proposta COMPLETA conta como entregue", feito.get("P1") is True)
    check("proposta sem antes/depois NAO conta como entregue", feito.get("P2") is False)
    check("tarefa normal passa intacta pelo bloco", feito.get("N1") is True)
    blq = {b.get("taskId"): b for b in saiu.get("blockers", [])}
    check("a proposta chega ao dono com o ANTES e o DEPOIS literais",
          "LINHA VELHA" in blq.get("P1", {}).get("whyNeedsYou", "")
          and "LINHA NOVA" in blq.get("P1", {}).get("whyNeedsYou", ""))
    check("o bloqueio nomeia o arquivo sob tranca",
          "docs/visao.md" in blq.get("P1", {}).get("what", ""))
    check("git diff vazio sai como CERTO tambem pro dono",
          "CERTO" in blq.get("P1", {}).get("whyNeedsYou", ""))
    check("quem voltou sem os dois lados vira bloqueio, com o motivo",
          "sem proposta com antes e depois literais" in blq.get("P2", {}).get("what", ""))
    # O `taskId` no bloqueio e o que faz a tarefa nascer PARADA na volta seguinte
    # (`parado` e semeado por `blockers.map(b => b.taskId)`): sem ele o motor jogaria o
    # executor contra a mesma tranca de novo.
    check("o bloqueio carrega o taskId, entao a tarefa nao e re-tentada contra a tranca",
          sorted(blq) == ["P1", "P2"])
    check("tarefa nao protegida nao vira bloqueio", "N1" not in blq)

    print("F9.23 — o vigia narra na tela principal")
    check("a narracao e REGUA, nao lista de eventos",
          "Toda mudança de estado vira uma linha" in texto)
    check("rodada sem mudanca fica calada", "fica calada" in texto)
    check("as linhas vem do modulo, nao de prosa improvisada",
          "lib/andamento.py" in texto)
    check("a estimativa por media global esta PROIBIDA por escrito",
          "Nunca estime por média global" in texto)
    check("a medicao que sustenta a proibicao esta colada",
          "660,4s" in texto and "299 transcritos" in texto)
    check("o detector descartado esta registrado com o numero",
          "0 de 282 agentes" in texto)

    print("F9.29 — um executor lento nao segura a rodada inteira parada")
    check("o teto por executor existe como knob", "tetoExecutorMin" in js)
    # O teto so e teto se chegar em quem tem relogio: o script nao tem (o vigia le a hora
    # de ARGS.now). Teto que ficasse so no script nao seria teto de ninguem — por isso o
    # que se cobra aqui e o `tetoMin` DENTRO de todo execPrompt, nao a constante solta.
    check("o teto chega a TODO executor pelo prompt",
          len(re.findall(r"execPrompt\(\{ task: t, tetoMin: tetoExecutorMin, buildWarm \}", js)) == 3)
    check("quem estourou o teto NAO conta como resultado",
          re.search(r"const results = respostas\.filter\(x => !x\.espera\)", js) is not None)
    check("a rodada fecha com quem voltou (o resto do laco usa `results`)",
          "respostas" in js and js.index("const results = respostas") < js.index("reviewBuildPrompt"))
    check("quem esperou volta pro decompositor na volta seguinte",
          "esperaIds" in js and re.search(r"missing: \[\.\.\.new Set\(\[\.\.\.\(review\.missingTasks \|\| \[\]\), \.\.\.esperaIds", js) is not None)
    check("quem esperou sai como falta de TEMPO, com o motivo",
          "passou do teto de ${tetoExecutorMin} min do executor" in js)
    check("o executor recebe a regra por escrito, no texto que ele le",
          "PASSOU DO TETO, PARE E DEVOLVA `espera: true`" in texto)
    check("o campo entra no schema do executor", "**`espera`**" in texto)

    print("F9.28 — o parametro pode chegar como texto, e o motor converte antes de usar")
    check("a conversao esta no SCRIPT, no topo",
          re.search(r"typeof args === 'string' \? JSON\.parse\(args\) : args", js) is not None)
    check("a conversao vem ANTES do primeiro uso do parametro",
          "ARGS =" in js and "ARGS.severityFloor" in js
          and js.index("ARGS =") < js.index("ARGS.severityFloor"))
    check("nenhum uso solto de args. sobrou no script", "args." not in js)
    # As DUAS formas, executadas de verdade: a linha do script roda em Node com o
    # parametro em texto e em objeto, e nos dois casos o campo tem que chegar.
    conv = conversao_do_script(js)
    for forma, entrada in (("texto", '\'{"severityFloor":"P0"}\''),
                           ("objeto", '{ severityFloor: "P0" }')):
        check("com o parametro em %s, o campo chega" % forma,
              roda_em_node(conv, entrada) == "P0")

    print("F9.38 — o caminhao do lixo passa no fim do motor, e junto do checkpoint")
    # O criterio e "a chamada existe no CAMINHO, nao so na prosa": por isso tudo aqui
    # e medido no esqueleto (`js`), e so a definicao do papel e cobrada no texto.
    chamadas = [m.start() for m in re.finditer(r"await agent\(colheitaPrompt\(", js)]
    check("o motor chama a colheita no script", len(chamadas) == 1)
    # Ponto 1 (dentro do motor): no ramo da onda VERDE, junto do checkpoint. Recorte
    # pelas fronteiras reais do ramo — do `checkpointPrompt` ao `} else {` que o fecha.
    i = js.find("await agent(checkpointPrompt(")
    j = js.find("  } else {", i) if i >= 0 else -1
    ramo_verde = js[i:j] if i >= 0 and j > i else ""
    check("a chamada esta JUNTO do checkpoint, no ramo da onda verde",
          "await agent(colheitaPrompt(" in ramo_verde)
    check("o papel roda com effort mecanico, como os outros papeis de registro",
          re.search(r"colheitaPrompt\([^)]*\),\n\s*\{ model: ARGS\.model, effort: T\.mechanical\.effort", js) is not None)
    # E o motor NAO dispara mais um agente depois do laco: agente disparado depois do
    # disjuntor desfaria o desligamento por teto (e `test_motor_bancada.py` afere isso
    # executando o esqueleto). Por isso a ultima passada e bash, na Persistencia.
    fim = js.rfind("\nreturn {")
    check("nenhuma colheita por agente depois do laco das ondas",
          fim > 0 and chamadas and chamadas[-1] < js.index(ramo_verde) + len(ramo_verde))
    # Ponto 2 (fim do motor, antes do relatorio): o passo 4 da Persistencia, em bash —
    # o unico caminho que alcanca a missao que fechou vermelha, foi derrubada pelo vigia
    # ou desligada pelo teto. Cobrado no passo, nao numa frase solta: o recorte vai do
    # cabecalho da Persistencia ao da secao seguinte.
    persist = texto.split("## Persistência")[-1].split("## Relatório Final")[0]
    # O comando tem que RODAR como esta escrito. Aferir a string literal contra ela
    # mesma nao prova nada. `${CLAUDE_PLUGIN_ROOT}/../lixeiro/...`  # acopla-ok: narrativa
    # era o comando antigo: passava nesse check e NAO resolvia em install real, porque o cache
    # do marketplace guarda `<marketplace>/<plugin>/<versao>/` — falta um nivel E a versao.
    # Por isso daqui pra baixo o bloco e EXECUTADO contra uma arvore de mentira, e quem
    # resolve o caminho e a copia vendorada do `resolve-plugin.sh` (o irmao entra pelo
    # NOME; posicao no disco nao e mais argumento de ninguem — Artigo 9).
    bloco = bloco_da_colheita(persist)
    check("a Persistencia manda colher num bloco EXECUTAVEL, nao em prosa",
          "colhe-turno" in bloco)
    check("nenhum placeholder sobrou no lugar do caminho do lixeiro",
          "<plugin lixeiro>" not in texto)
    check("a colheita vem DEPOIS do commit/push, ainda ANTES do relatorio",
          bool(bloco) and persist.index("Commit + push") < persist.index(bloco.split("\n")[0]))
    # Layout de INSTALL (`<marketplace>/<plugin>/<versao>/`): o caminho tem que resolver,
    # e entre as versoes do cache tem que sair a mais ALTA (1.10.0 > 1.9.0 > 1.8.2).
    r = roda_a_colheita(bloco, "cache")
    check("no layout do cache do marketplace, o comando ACHA o lixeiro e roda",
          r.get("rc") == 0 and "COLHEU" in r.get("saida", ""))
    check("entre as versoes do cache, resolve a mais ALTA",
          "/lixeiro/1.10.0/lib/lixeiro.py" in r.get("saida", ""))
    check("o lixeiro recebe colhe-turno e a sessao desta missao",
          "colhe-turno --sessao sessao-de-teste" in r.get("saida", ""))
    # Layout de REPOSITORIO (irmao direto, sem segmento de versao): tem que resolver
    # tambem, senao a skill so funciona instalada.
    r_repo = roda_a_colheita(bloco, "repo")
    check("rodando do repositorio, o irmao direto tambem resolve",
          r_repo.get("rc") == 0 and "COLHEU" in r_repo.get("saida", ""))
    # As duas falhas, separadas: ausencia sai calada (e a regra escrita), comando
    # quebrado avisa. O `|| true` de antes achatava as duas na mesma cara.
    r_sem = roda_a_colheita(bloco, "ausente")
    check("lixeiro ausente nao derruba o passo", r_sem.get("rc") == 0)
    check("lixeiro ausente segue CALADO, sem barulho no relatorio",
          r_sem.get("saida") == "")
    r_quebra = roda_a_colheita(bloco, "cache", quebra=True)
    check("comando quebrado tambem nao derruba o passo", r_quebra.get("rc") == 0)
    check("comando quebrado AVISA, citando o caminho que resolveu",
          "/lixeiro/1.10.0/lib/lixeiro.py" in r_quebra.get("saida", ""))
    # A definicao do papel: sem o comando real, o script chamaria um papel que nao sabe
    # o que rodar — e o "manda colher" voltaria a ser prosa.
    check("o papel esta definido, com o motor do lixeiro nomeado",
          "`colheitaPrompt`" in texto and "lixeiro lib/lixeiro.py" in texto)
    # Artigo 9: o irmao entra pelo NOME, nunca pela posicao no disco.
    check("nenhum caminho de irmao POR POSICAO sobrou na skill",
          "/../lixeiro" not in texto)  # acopla-ok: e a AUSENCIA do caminho que se cobra
    papel = texto.split("- `colheitaPrompt`")[-1].split("- `BUILD_REVIEW`")[0]
    check("o papel manda o MESMO comando executavel do passo 4",
          bool(bloco) and bloco_da_colheita(papel) == bloco)
    check("a colheita e a SELETIVA do turno, nunca a da sessao inteira",
          "colhe-turno" in bloco and "colhe-sessao" not in bloco)
    check("a regra do lixeiro esta escrita: so colhe o que foi ANOTADO",
          "Só é candidato o processo cuja ABERTURA foi anotada" in texto)
    check("lixeiro ausente na maquina nao derruba a missao", "não é falha" in papel)

    print("F9.34 — a compilacao cara e paga uma vez, pela casca, antes do motor")
    bloco_build = bloco_da_compilacao(texto)
    check("o passo existe como bloco EXECUTAVEL na casca, nao em prosa",
          "$SOVAI_BUILD_CMD" in bloco_build and "BUILD_WARM" in bloco_build)
    # O passo so serve se vier ANTES do disparo: compilar depois do Workflow e pagar
    # a compilacao duas vezes, uma delas por tarefa.
    check("o passo vem antes do esqueleto do motor",
          texto.index("### A compilação cara é paga UMA vez") < texto.index("### Esqueleto do motor"))
    # A metade de EXECUCAO: o passo roda de verdade contra um projeto de mentira, e a
    # segunda compilacao — a do executor — tem que aproveitar o cache. Se o passo
    # limpasse (clean / rm -rf do diretorio de build), ela sairia FULL de novo.
    raiz = tempfile.mkdtemp(prefix="sovai-build-")
    try:
        r = roda_a_compilacao(bloco_build, raiz)
        check("a casca compila os alvos e declara o cache quente",
              r.get("saida") == "buildWarm=true")
        check("o EXECUTOR nao recompila do zero: a casca pagou FULL, ele pegou INCR",
              r.get("passadas") == ["FULL", "INCR"])
    finally:
        shutil.rmtree(raiz, ignore_errors=True)
    check("o passo proibe limpar o cache por escrito",
          "NUNCA limpe antes nem depois" in bloco_build)
    check("compilacao que falha nao trava a missao (fail-open)",
          "BUILD_WARM=false" in bloco_build)
    check("o estado fica fora do repositorio, na raiz de config do Claude",
          'SOVAI_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"' in bloco_build)
    # E o aviso chega a QUEM COMPILA: valor que para no script nao impede `clean` nenhum.
    check("o knob chega ao motor pelo args", "const buildWarm = ARGS.buildWarm === true" in js)
    check("o executor recebe a regra por escrito, no texto que ele le",
          "CACHE QUENTE: NÃO RECOMPILE DO ZERO" in texto and "`buildWarm`" in texto)

    print()
    if FAILS:
        print("FALHOU: %d" % len(FAILS))
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("OK (%d checks)" % TOTAL[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
