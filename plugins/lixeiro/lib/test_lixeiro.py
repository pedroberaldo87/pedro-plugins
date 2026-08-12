#!/usr/bin/env python3
"""test_lixeiro.py — suíte do motor de coleta de processos.

O que ela existe para impedir, em ordem de gravidade:
  1. o mecanismo matar a própria sessão (o pior desfecho possível)
  2. matar processo que o usuário abriu à mão (falso positivo)
  3. matar o servidor que o próximo turno ia usar
  4. deixar de matar o lixo óbvio (falso negativo — o mais barato dos quatro)

Roda isolada: o estado vai para um diretório temporário e nenhum processo real
é encerrado, exceto os que a própria suíte abre.
"""

import os
import re
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

TMP = tempfile.mkdtemp(prefix="lixeiro-test-")
os.environ["CLAUDE_CONFIG_DIR"] = TMP

import lixeiro  # noqa: E402

PASS = 0
FAIL = 0


def ok(msg):
    global PASS
    PASS += 1
    print("  ✓ %s" % msg)


def bad(msg, esperado, obtido):
    global FAIL
    FAIL += 1
    print("  ✗ %s\n     esperado: %s\n     obtido:   %s" % (msg, esperado, obtido))


def eq(got, want, msg):
    if got == want:
        ok(msg)
    else:
        bad(msg, repr(want), repr(got))


def proc(pid, cmd, idade=300, cpu=1.0, ppid=1, rss=100000):
    return {"pid": pid, "ppid": ppid, "idade": idade, "cpu": cpu, "rss": rss, "cmd": cmd}


def _leitor(*leituras):
    """`ps` respondendo uma leitura por chamada — a última se repete. É assim que
    a suíte encena o que muda ENTRE duas leituras: a CPU que sobe, e o número de
    processo que passou a ser de outro programa."""
    fila = list(leituras)

    def ler():
        return fila.pop(0) if len(fila) > 1 else fila[0]
    return ler


print("── classificação: efêmero, serviço, intocável ──")
eq(lixeiro.classifica("python -m pytest tests/ -q"), "efemero", "pytest é efêmero")
eq(lixeiro.classifica("node .../node_modules/.bin/vitest run x.test.ts"), "efemero", "vitest run é efêmero")
eq(lixeiro.classifica("node .../.bin/tsc -b"), "efemero", "compilação é efêmera")
eq(lixeiro.classifica("node /proj/node_modules/.bin/vite --port 5199"), "servico", "vite é serviço")
eq(lixeiro.classifica("next-server (v16.2.11)"), "servico", "servidor do next é serviço")
eq(lixeiro.classifica("python3 -m http.server 8000"), "servico", "servidor http é serviço")
eq(lixeiro.classifica("git status"), None, "comando comum não é abridor")
eq(lixeiro.classifica("ls -la"), None, "listar arquivo não é abridor")

print("── intocáveis: a lista que nunca recebe sinal ──")
for cmd in ["/opt/homebrew/bin/limactl hostagent --pidfile x",
            "qemu-system-aarch64 -m 2048",
            "claude bg-spare --bg-spare /tmp/cc-daemon-501/x.sock",
            "node ~/.claude/plugins/cache/pedro-plugins/visual/1.15.0/server/visual_server.mjs",
            "com.docker.backend"]:
    if lixeiro.eh_intocavel(cmd) and lixeiro.classifica(cmd) == "intocavel":
        ok("intocável: %s" % cmd[:52])
    else:
        bad("intocável: %s" % cmd[:52], "intocável e classe 'intocavel'", lixeiro.classifica(cmd))

# O guarda-costas protege o PROGRAMA claude, não o diretório de configuração dele.
# O harness põe `~/.claude/…` na linha de TODO comando que lança (snapshot de shell,
# arquivo de cwd); se o padrão casar nesse caminho, nada que a sessão abre é colhível.
for cmd in ["/Users/quem-instalou/.local/bin/claude --resume abc --dangerously-skip-permissions",  # public-ok: conta ficticia; o teste existe pra provar que o caminho ABSOLUTO do harness e reconhecido — trocar por ~ mata o caso
            "claude bg-spare --bg-spare /tmp/cc-daemon-501/x.sock",
            "node ~/.claude/local/node_modules/.bin/claude"]:
    if lixeiro.eh_intocavel(cmd):
        ok("a sessão do próprio Claude segue protegida: %s" % cmd[:52])
    else:
        bad("a sessão do próprio Claude segue protegida", "intocável", cmd)

HARNESS = ("/bin/zsh -c source /Users/quem-instalou/.claude/shell-snapshots/snapshot-zsh-17.sh "  # public-ok: conta ficticia; o teste existe pra provar que o caminho ABSOLUTO do harness e reconhecido — trocar por ~ mata o caso
           "2>/dev/null || true && eval 'python -m pytest tests/ -q' < /dev/null "
           "&& pwd -P >| /tmp/claude-4a6f-cwd")
for cmd in [HARNESS,
            "python3 .claude/servir.py 8765",
            "node /proj/node_modules/.bin/vite --port 5199  # cwd /Users/quem-instalou/.claude/x"]:  # public-ok: conta ficticia; o teste existe pra provar que o caminho ABSOLUTO do harness e reconhecido — trocar por ~ mata o caso
    if lixeiro.eh_intocavel(cmd):
        bad("o processo lançado pelo harness não é intocável", "colhível", cmd[:70])
    else:
        ok("o caminho de configuração não blinda: %s" % cmd[:52])

eq(lixeiro.classifica(HARNESS), "efemero", "a suíte lançada pelo harness volta a ser efêmera")

# O caso que dá nome à regra: `node` sozinho não pode significar nada.
eq(lixeiro.classifica("node"), None, "`node` puro não vira candidato a nada")
eq(lixeiro.classifica("/Applications/Google Chrome.app/.../Google Chrome"), None,
   "o navegador não é candidato")

print("── os três que subiam processo e não eram reconhecidos ──")
# Até esta rodada, os três voltavam None de `classifica` — e o que não tem classe
# nunca é anotado, logo nunca tem procedência e nunca aparece com dono. São, na
# prática, as formas mais comuns de subir processo numa sessão.
eq(lixeiro.classifica("docker compose up -d"), "intocavel",
   "docker compose up é reconhecido (e segue sem receber sinal)")
eq(lixeiro.classifica("ssh -L 8080:localhost:8080 -N deploy@srv"), "servico",
   "túnel ssh com redirecionamento de porta é serviço")
eq(lixeiro.classifica("node server.js"), "servico", "servidor por arquivo é serviço")
eq(lixeiro.classifica("node /proj/api/index.mjs"), "servico", "…com caminho e .mjs também")

# E o reconhecimento tem que chegar no registro: `anota` é o que o hook de
# PostToolUse chama, e o que não é anotado não existe para o motor.
SID_N = "sessao-reconhecimento"
for cmd, classe in [("docker compose up -d", "intocavel"),
                    ("ssh -L 8080:localhost:8080 -N deploy@srv", "servico"),
                    ("node server.js", "servico")]:
    eq(lixeiro.anota(SID_N, cmd, "/proj/x"), classe, "anotado com classe %s: %s" % (classe, cmd[:34]))
eq(len(lixeiro.le_registro(SID_N)["anotacoes"]), 3, "os três ficaram gravados no registro da sessão")

# O que NÃO pode acontecer junto: o docker anotado virar candidato a encerramento.
_procs_dk = [proc(4242, "com.docker.backend compose up -d", idade=10)]
eq(lixeiro.candidatos(SID_N, "sessao", procs=_procs_dk), [],
   "docker anotado NUNCA vira candidato — classificar não é autorizar")

# E o que já não era abridor continua não sendo.
eq(lixeiro.classifica("ssh deploy@srv"), None, "ssh para trabalhar (sem túnel) não é abridor")
eq(lixeiro.classifica("ssh -l deploy srv"), None, "o -l minúsculo do ssh não vira túnel")

print("── leitura do tempo: idade e CPU ──")
eq(lixeiro._seg_etime("02:44:38"), 9878, "idade em horas")
eq(lixeiro._seg_etime("40:03"), 2403, "idade em minutos")
eq(lixeiro._seg_etime("04-11:22:36"), 4 * 86400 + 11 * 3600 + 22 * 60 + 36, "idade em dias")
eq(lixeiro._seg_cputime("0:25.99"), 25.99, "cpu em minutos")
eq(lixeiro._seg_cputime("211:58.88"), 211 * 60 + 58.88, "cpu acima de uma hora")

print("── casamento: a anotação só casa o processo que ELA abriu ──")
SID = "sessao-de-teste"
agora = time.time()
anot_vite = {"cmd": "npm run dev", "cwd": "/proj/loja-exemplo", "classe": "servico",
             "em": agora - 60, "cpu_ultimo_turno": None}
# o servidor "ocioso" precisa de idade > 120s para virar candidato; a anotação
# do turno anterior é mais velha que ele, como acontece de verdade
anot_vite_velha = dict(anot_vite, em=agora - 400)

p_meu = proc(101, "node /proj/loja-exemplo/node_modules/.bin/vite --port 5199", idade=50)
p_vizinho = proc(102, "node /outro/ProjetoAlheio/node_modules/.bin/vite --port 4000", idade=50)
p_velho = proc(103, "node /proj/loja-exemplo/node_modules/.bin/vite --port 5199", idade=9878)

eq(lixeiro.casa(anot_vite, p_meu), True, "casa o servidor do projeto anotado")
eq(lixeiro.casa(anot_vite, p_vizinho), False, "NÃO casa o mesmo programa em outro projeto")
eq(lixeiro.casa(anot_vite, p_velho), False, "NÃO casa processo mais velho que a anotação")

anot_pytest = {"cmd": "python -m pytest tests/", "cwd": "/proj/relatorio-exemplo", "classe": "efemero",
               "em": agora - 120, "cpu_ultimo_turno": None}
eq(lixeiro.casa(anot_pytest, proc(104, "/proj/relatorio-exemplo/.venv/bin/python -m pytest tests/ -q", idade=100)),
   True, "casa a suíte do projeto anotado")
eq(lixeiro.casa(anot_pytest, proc(105, "/outro/proj/.venv/bin/python -m pytest tests/ -q", idade=100)),
   False, "NÃO casa a suíte de outro projeto")
eq(lixeiro.casa(anot_vite, proc(106, "limactl hostagent --pidfile x", idade=10)),
   False, "intocável nunca casa, mesmo dentro da janela")

print("── trava de suicídio: nada acima do hook na árvore morre ──")
meu_pid = os.getpid()
procs_falsos = [
    proc(meu_pid, "python3 test_lixeiro.py", ppid=900),
    proc(900, "bash -c hook", ppid=901),
    proc(901, "claude", ppid=1),
]
cadeia = lixeiro.ancestrais(meu_pid, procs_falsos)
eq(meu_pid in cadeia, True, "o próprio processo está na cadeia protegida")
eq(900 in cadeia, True, "o pai (o hook) está protegido")
eq(901 in cadeia, True, "o avô (a sessão) está protegido")
eq(102 in cadeia, False, "processo alheio NÃO entra na cadeia protegida")

print("── decisão no fim do turno ──")
reg = {"session_id": SID, "dono_pid": meu_pid, "anotacoes": [
    dict(anot_pytest), dict(anot_vite_velha),
]}
lixeiro.grava_registro(reg)

procs = [proc(104, "/proj/relatorio-exemplo/.venv/bin/python -m pytest tests/ -q", idade=100),
         proc(101, "node /proj/loja-exemplo/node_modules/.bin/vite --port 5199", idade=300, cpu=30.0)]
cands = lixeiro.candidatos(SID, "turno", procs=procs)
pids = sorted(c[1]["pid"] for c in cands)
eq(pids, [], "sem foto de CPU do turno anterior NADA morre — nem a suíte, nem o serviço")

# Com a foto do turno anterior: CPU parada = ocioso, CPU subindo = em uso.
# A anotação da suíte envelhece junto com a do serviço, senão a janela de `casa`
# recusaria o processo de 300s e o teste passaria por não casar, não por decidir.
reg["anotacoes"][0]["em"] = agora - 400
reg["anotacoes"][0]["cpu_ultimo_turno"] = 1.0
reg["anotacoes"][1]["cpu_ultimo_turno"] = 30.0
# A foto tem que ser VELHA: a janela de ocioso é de relógio, e é ela que estes
# dois testes querem exercer já satisfeita, para julgarem só a CPU.
reg["anotacoes"][0]["cpu_visto_em"] = agora - 300
reg["anotacoes"][1]["cpu_visto_em"] = agora - 300
# A foto é de UM processo: sem o pid dela, a leitura seria de outro bicho.
reg["anotacoes"][0]["cpu_pid"] = 104
reg["anotacoes"][1]["cpu_pid"] = 101
lixeiro.grava_registro(reg)
procs_velhos = [dict(procs[0], idade=300), procs[1]]
cands = lixeiro.candidatos(SID, "turno", procs=procs_velhos)
eq(sorted(c[1]["pid"] for c in cands), [101, 104], "suíte e servidor com CPU parada desde o turno anterior morrem")

reg["anotacoes"][1]["cpu_ultimo_turno"] = 10.0
lixeiro.grava_registro(reg)
cands = lixeiro.candidatos(SID, "turno", procs=procs_velhos)
eq(sorted(c[1]["pid"] for c in cands), [104], "servidor com CPU crescendo SOBREVIVE ao fim do turno")

print("── a suíte EM ANDAMENTO sobrevive ao fim do turno ──")
# O estrago de 2026-08-11: `cargo test` lançado em segundo plano morria no fim do
# mesmo turno, às vezes 6 segundos depois de começar. Três provas, uma por caminho.
reg["anotacoes"][0]["cpu_ultimo_turno"] = 1.0
reg["anotacoes"][1]["cpu_ultimo_turno"] = 10.0
lixeiro.grava_registro(reg)
eq([c[1]["pid"] for c in lixeiro.candidatos(SID, "turno", procs=[dict(procs[0], idade=6)])],
   [], "suíte com 6 segundos de vida NÃO é candidata")
eq([c[1]["pid"] for c in lixeiro.candidatos(SID, "turno",
                                            procs=[dict(procs[0], idade=300, cpu=90.0)])],
   [], "suíte queimando CPU desde o turno anterior SOBREVIVE")
# O lançador parado que segura o filho ocupado: `zsh -c … cargo test` fica esperando
# com CPU zero enquanto a suíte trabalha. Quem responde é a CPU da ÁRVORE.
lancador = proc(200, "/bin/zsh -c cd /proj/relatorio-exemplo && python -m pytest tests/ -q",
                idade=300, cpu=0.1)
filho = proc(201, "/proj/relatorio-exemplo/.venv/bin/python -m pytest tests/ -q",
             idade=300, cpu=88.0, ppid=200)
# A foto tem que ser DO LANÇADOR e velha: senão ele escaparia pela trava do pid ou
# pela do relógio, e este teste não julgaria a CPU da árvore, que é o que ele quer.
reg["anotacoes"][0]["cpu_pid"] = 200
reg["anotacoes"][0]["cpu_ultimo_turno"] = 0.1
reg["anotacoes"][0]["cpu_visto_em"] = agora - 300
lixeiro.grava_registro(reg)
eq([c[1]["pid"] for c in lixeiro.candidatos(SID, "turno", procs=[lancador, filho], agora=agora)],
   [], "lançador parado com filho trabalhando SOBREVIVE — vale a CPU da árvore")
# E o mesmo lançador com o filho PARADO morre — senão o teste acima passaria por
# nada nunca ser candidato, em vez de por a árvore estar ocupada.
eq([c[1]["pid"] for c in lixeiro.candidatos(
    SID, "turno", procs=[lancador, dict(filho, cpu=0.0)], agora=agora)],
   [200], "…e com a árvore inteira parada, ele morre")

print("── ocioso se conta no relógio, não em turnos ──")
# Dois turnos podem estar a segundos um do outro. Se a janela fosse "desde o turno
# anterior", a suíte parada esperando o banco subir morreria em 3 segundos.
reg["anotacoes"][0]["cpu_ultimo_turno"] = 1.0
reg["anotacoes"][0]["cpu_visto_em"] = agora - 3
reg["anotacoes"][0]["cpu_pid"] = 104     # o bloco anterior deixou a foto no lançador
lixeiro.grava_registro(reg)
eq([c[1]["pid"] for c in lixeiro.candidatos(SID, "turno", procs=procs_velhos, agora=agora)],
   [], "parada há 3 segundos NÃO é candidata, mesmo com a CPU imóvel")
reg["anotacoes"][0]["cpu_visto_em"] = agora - 300
lixeiro.grava_registro(reg)
eq([c[1]["pid"] for c in lixeiro.candidatos(SID, "turno", procs=procs_velhos, agora=agora)],
   [104], "parada há 300 segundos morre")

# E a foto só se renova quando ele trabalhou: renovar a cada turno zeraria o
# relógio do ocioso para sempre numa conversa de turnos curtos.
reg["anotacoes"][0]["cpu_visto_em"] = agora - 300
lixeiro.grava_registro(reg)
lixeiro.marca_cpu(SID, procs=procs_velhos, agora=agora)
eq(lixeiro.le_registro(SID)["anotacoes"][0]["cpu_visto_em"], agora - 300,
   "CPU imóvel NÃO renova a foto — o relógio do ocioso continua correndo")
lixeiro.marca_cpu(SID, procs=[dict(procs_velhos[0], cpu=99.0)], agora=agora)
eq(lixeiro.le_registro(SID)["anotacoes"][0]["cpu_visto_em"], agora,
   "CPU que subiu renova a foto e zera o relógio")

print("── a foto vale para UM processo, não para a anotação ──")
# A mesma anotação casa mais de um processo ao longo da sessão: a suíte roda de
# novo, o servidor reinicia. O segundo nasce com a CPU zerada, e comparado contra
# a foto do primeiro pareceria "parado" — morrendo no meio do serviço.
reg["anotacoes"][0]["cpu_ultimo_turno"] = 300.0
reg["anotacoes"][0]["cpu_visto_em"] = agora - 300
reg["anotacoes"][0]["cpu_pid"] = 104
lixeiro.grava_registro(reg)
_outro = [dict(procs_velhos[0], pid=555, cpu=5.0)]
eq([c[1]["pid"] for c in lixeiro.candidatos(SID, "turno", procs=_outro, agora=agora)],
   [], "processo NOVO na mesma anotação não é julgado pela foto do anterior")
lixeiro.marca_cpu(SID, procs=_outro, agora=agora)
_reg = lixeiro.le_registro(SID)["anotacoes"][0]
eq((_reg["cpu_pid"], _reg["cpu_ultimo_turno"], _reg["cpu_visto_em"]), (555, 5.0, agora),
   "…e a foto passa a ser dele, com o relógio zerado")

print("── o número do processo é reconferido antes do sinal ──")
# Entre ler a tabela e sinalizar passa tempo (no fim de sessão, mais: a medição ao
# vivo dorme no meio). Se o alvo morreu e o sistema reaproveitou o número dele,
# o sinal iria para um inocente.
SID_RECI = "sessao-pid-reciclado"
lixeiro.grava_registro({"session_id": SID_RECI, "dono_pid": meu_pid, "anotacoes": [
    {"cmd": "python -m pytest tests/", "cwd": "/proj/reciclado", "classe": "efemero",
     "em": agora - 60, "cpu_ultimo_turno": None}]})
_antes = [proc(900, "/proj/reciclado/.venv/bin/python -m pytest tests/ -q", idade=30)]
_depois = [proc(900, "/Applications/Navegador.app/Contents/MacOS/Navegador", idade=1)]
_real_procs = lixeiro.processos
_real_espera = lixeiro.OCIOSO_ESPERA
_real_encerra = lixeiro.encerra
lixeiro.OCIOSO_ESPERA = 0
# O que se mede é a CHAMADA, não o efeito: um `os.kill` num número que não existe
# falha calado, e o teste passaria com ou sem a trava — tautologia. Aqui o sinal é
# espionado, e nenhum processo de verdade corre risco.
_sinalizados = []
lixeiro.encerra = lambda pid, **kw: (_sinalizados.append(pid), "TERM")[1]
try:
    # a 1ª leitura acha a suíte; da 2ª em diante o número 900 já é de outro programa
    lixeiro.processos = _leitor(_antes, _depois)
    lixeiro.colhe(SID_RECI, "sessao")
    eq(_sinalizados, [], "pid cujo COMANDO mudou entre a leitura e o sinal NÃO é sinalizado")
    # e o controle: com o comando intacto, o sinal sai — senão o teste acima
    # passaria por nada nunca ser sinalizado.
    lixeiro.processos = _leitor(_antes, _antes)
    lixeiro.colhe(SID_RECI, "sessao")
    eq(_sinalizados, [900], "…e o mesmo processo, ainda ele, é sinalizado normalmente")
finally:
    lixeiro.processos = _real_procs
    lixeiro.OCIOSO_ESPERA = _real_espera
    lixeiro.encerra = _real_encerra

print("── duas suítes do mesmo projeto: uma foto para cada ──")
# Sem isto, as duas anotações fotografavam o MESMO processo e a segunda suíte
# ficava para sempre sem foto própria — ou seja, nunca era colhida.
SID_DUAS = "sessao-duas-suites"
_anot = {"cmd": "python -m pytest tests/", "cwd": "/proj/duas", "classe": "efemero",
         "em": agora - 400, "cpu_ultimo_turno": None}
lixeiro.grava_registro({"session_id": SID_DUAS, "dono_pid": meu_pid,
                        "anotacoes": [dict(_anot), dict(_anot)]})
_duas = [proc(301, "/proj/duas/.venv/bin/python -m pytest tests/ -q", idade=200, cpu=7.0),
         proc(302, "/proj/duas/.venv/bin/python -m pytest tests/ -q", idade=200, cpu=9.0)]
lixeiro.marca_cpu(SID_DUAS, procs=_duas, agora=agora)
eq(sorted(a.get("cpu_pid") for a in lixeiro.le_registro(SID_DUAS)["anotacoes"]), [301, 302],
   "cada anotação fotografou um processo diferente")
# E a foto não troca de dono no turno seguinte — senão o relógio do ocioso zerava
# a cada rodada e o lixo nunca completaria a janela.
# O caso que separa reivindicar de simplesmente distribuir na ordem: as fotos
# estão CRUZADAS em relação à ordem da lista. Sem a reivindicação, a distribuição
# devolveria [301, 302] e as duas trocariam de processo — zerando o relógio do
# ocioso a cada turno, e com ele a chance de o lixo um dia ser colhido.
_r = lixeiro.le_registro(SID_DUAS)
_r["anotacoes"][0]["cpu_pid"], _r["anotacoes"][1]["cpu_pid"] = 302, 301
lixeiro.grava_registro(_r)
lixeiro.marca_cpu(SID_DUAS, procs=_duas, agora=agora + 10)
eq([a.get("cpu_pid") for a in lixeiro.le_registro(SID_DUAS)["anotacoes"]],
   [302, 301], "no turno seguinte cada uma continua com o SEU processo, não com o da vez")

print("── decisão no fim da sessão ──")
cands = lixeiro.candidatos(SID, "sessao", procs=procs)
eq(sorted(c[1]["pid"] for c in cands), [101, 104], "no fim da sessão morre tudo que ela anotou")

print("── no fim da sessão, o que está trabalhando é medido AO VIVO ──")
_procs_t = [proc(700, "x", cpu=10.0), proc(701, "y", cpu=10.0, ppid=700), proc(702, "z", cpu=5.0)]
_leituras = [_procs_t, [proc(700, "x", cpu=10.0), proc(701, "y", cpu=44.0, ppid=700),
                        proc(702, "z", cpu=5.0)]]
_real_procs = lixeiro.processos
lixeiro.processos = lambda: _leituras[1]
try:
    ocupados = lixeiro.trabalhando([700, 702], procs=_leituras[0], espera=0)
finally:
    lixeiro.processos = _real_procs
eq(700 in ocupados, True, "pai parado com FILHO queimando CPU conta como trabalhando")
eq(702 in ocupados, False, "processo que não gastou CPU nenhuma não é dado como ativo")
eq(lixeiro.trabalhando([], espera=0), set(), "sem pids não mede nada")

# E a colheita de fim de sessão precisa USAR essa medida, não só tê-la disponível:
# é o caminho que o /clear dispara, e ele não tem canal para avisar o que matou.
SID_FIM = "sessao-fim-de-sessao"
RAIZ_FIM = os.path.join(TMP, "proj-fim")
os.makedirs(RAIZ_FIM, exist_ok=True)
CMD_FIM = "%s/.venv/bin/python -m pytest tests/ -q" % RAIZ_FIM
lixeiro.grava_registro({"session_id": SID_FIM, "dono_pid": meu_pid, "anotacoes": [
    {"cmd": "python -m pytest tests/", "cwd": RAIZ_FIM, "classe": "efemero",
     "em": time.time() - 60, "cpu_ultimo_turno": None}]})
def _arvore(cpu_do_filho):
    # O lançador parado (800) segurando o trabalhador (801), como `cargo test`
    return [proc(800, CMD_FIM, idade=30, cpu=10.0),
            proc(801, CMD_FIM, idade=30, cpu=cpu_do_filho, ppid=800)]


_real_procs = lixeiro.processos
_real_espera = lixeiro.OCIOSO_ESPERA
lixeiro.OCIOSO_ESPERA = 0
try:
    # três leituras: a de `candidatos`, e as duas da medição ao vivo
    lixeiro.processos = _leitor(_arvore(10.0), _arvore(10.0), _arvore(99.0))
    eq(lixeiro.colhe(SID_FIM, "sessao", dry_run=True), [],
       "no fim da sessão, a suíte TRABALHANDO é poupada")
    lixeiro.processos = _leitor(_arvore(10.0), _arvore(10.0), _arvore(10.0))
    eq(sorted(m["pid"] for m in lixeiro.colhe(SID_FIM, "sessao", dry_run=True)), [800, 801],
       "…e a suíte PARADA no fim da sessão morre, como sempre morreu")
finally:
    lixeiro.processos = _real_procs
    lixeiro.OCIOSO_ESPERA = _real_espera

print("── o registro ──")
os.environ["CLAUDE_CONFIG_DIR"] = TMP
eq(lixeiro.anota("s2", "npm run dev", "/proj/x", dono_pid=meu_pid), "servico", "anota servidor")
eq(lixeiro.anota("s2", "git status", "/proj/x"), None, "não anota comando comum")
eq(len(lixeiro.le_registro("s2")["anotacoes"]), 1, "só o abridor entrou no registro")
eq(lixeiro.le_registro("s2")["dono_pid"], meu_pid, "o dono da sessão fica gravado")

print("── órfão: sessão cujo dono não existe mais ──")
lixeiro.grava_registro({"session_id": "s-morta", "dono_pid": 2 ** 22,
                        "anotacoes": [dict(anot_vite)]})
orfas = lixeiro.sessoes_orfas()
eq("s-morta" in orfas, True, "sessão com dono inexistente é órfã")
eq("s2" in orfas, False, "sessão com dono vivo NÃO é órfã")

print("── órfã com processo TRABALHANDO: poupa, e o registro fica ──")
# O registro da órfã é a única procedência que a próxima varredura terá. Se ele
# fosse apagado junto da colheita que POUPOU o processo (por estar trabalhando),
# o servidor viraria para sempre "sem dono conhecido" — invisível a toda colheita.
CMD_ORFA = "/proj/orfa-viva/.venv/bin/python -m pytest tests/ -q"
lixeiro.grava_registro({"session_id": "s-orfa-viva", "dono_pid": 2 ** 22, "anotacoes": [
    {"cmd": "python -m pytest tests/", "cwd": "/proj/orfa-viva", "classe": "efemero",
     "em": time.time() - 60, "cpu_ultimo_turno": None}]})
_real_procs = lixeiro.processos
_real_espera = lixeiro.OCIOSO_ESPERA
_real_encerra = lixeiro.encerra
lixeiro.OCIOSO_ESPERA = 0
_mortes = []
lixeiro.encerra = lambda pid, **kw: (_mortes.append(pid), "TERM")[1]


def _cpu_subindo():
    """`ps` cuja CPU do 950 SOBE a cada leitura — trabalhando, sempre, não importa
    quantas leituras o caminho consome nem em que ordem as sessões são varridas."""
    cpu = [0.0]

    def ler():
        cpu[0] += 10.0
        return [proc(950, CMD_ORFA, idade=30, cpu=cpu[0])]
    return ler


try:
    lixeiro.processos = _cpu_subindo()
    lixeiro.colhe_orfaos(exceto="s2")
    eq(_mortes, [], "o processo da órfã que está TRABALHANDO não recebe sinal")
    eq(os.path.exists(lixeiro.registro_path("s-orfa-viva")), True,
       "…e o registro dela SOBREVIVE — é a procedência da próxima varredura")
    # O contrafactual: parado (CPU imóvel), morre — o caminho antigo continua valendo.
    lixeiro.processos = lambda: [proc(950, CMD_ORFA, idade=30, cpu=10.0)]
    lixeiro.colhe_orfaos(exceto="s2")
    eq(_mortes, [950], "a mesma órfã com o processo PARADO é colhida")
finally:
    lixeiro.processos = _real_procs
    lixeiro.OCIOSO_ESPERA = _real_espera
    lixeiro.encerra = _real_encerra
try:
    os.remove(lixeiro.registro_path("s-orfa-viva"))
except OSError:
    pass

print("── ponta a ponta: um processo de verdade ──")
alvo = subprocess.Popen([sys.executable, "-c",
                         "import time,sys\nsys.argv=['x']\nwhile True: time.sleep(0.3)"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
time.sleep(0.4)
if lixeiro.vivo(alvo.pid):
    ok("o processo de teste subiu (pid %d)" % alvo.pid)
    sinal = lixeiro.encerra(alvo.pid, grace=2.0)
    alvo.poll()   # colhe o filho: sem isso ele fica zumbi e `vivo()` diz que vive
    if sinal in ("TERM", "KILL") and alvo.returncode is not None:
        ok("encerra() derrubou o processo com %s" % sinal)
    else:
        bad("encerra() derruba o processo", "TERM ou KILL e processo morto", sinal)
else:
    bad("o processo de teste subiu", "vivo", "morreu antes")
try:
    alvo.kill()
except OSError:
    pass

print("── encerrar sobe até a raiz órfã: a árvore inteira cai ──")
# Uma árvore de verdade, com raiz órfã: o lançador sai na hora e o bash de dentro
# é adotado pelo init, com três filhos pendurados nele. Encerrar UMA FOLHA tem
# que derrubar a raiz e os irmãos — matar só a folha deixa o pai de pé.
#
# ⚠️ ESTE BLOCO É POSIX POR CONSTRUÇÃO, e no Windows ele era PERIGOSO, não só
# inútil: lá não há adoção pelo processo 1, `nohup` não existe, e o `$!` que o
# bash do Git responde é um pseudo-pid dele, não um pid do sistema. O `os.kill(p, 9)`
# da limpeza virava TerminateProcess sobre um número qualquer — encerrando um
# processo alheio da máquina, escolhido por colisão. A suíte morria sem uma linha
# de traceback, e o job só dizia "exit code 1".
if os.name != "posix":
    print("  ↷ pulado: árvore órfã depende de adoção pelo processo 1 (só POSIX)")
else:
    lanc = subprocess.run(
        ["bash", "-c",
         "nohup bash -c 'sleep 300 & sleep 300 & sleep 300 & wait' >/dev/null 2>&1 & echo $!"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, start_new_session=True)
    raiz_pid = int(lanc.stdout.strip() or 0)
    time.sleep(1.0)
    tabela = lixeiro.processos()
    folhas = [p["pid"] for p in tabela if p["ppid"] == raiz_pid]
    raiz_ppid = next((p["ppid"] for p in tabela if p["pid"] == raiz_pid), None)
    if len(folhas) == 3 and raiz_ppid == 1:
        ok("a árvore subiu: raiz órfã %d (pai %d) com 3 filhos" % (raiz_pid, raiz_ppid))
        eq(lixeiro.raiz_orfa(folhas[0], tabela), raiz_pid, "a folha aponta para a raiz órfã da árvore")
        lixeiro.encerra(folhas[0], grace=2.0)
        time.sleep(0.5)
        sobrou = [p for p in [raiz_pid] + folhas if lixeiro.vivo(p)]
        eq(sobrou, [], "encerrar a folha derrubou a árvore inteira — nada sobrou")
    else:
        bad("a árvore de teste subiu", "raiz órfã (pai 1) com 3 filhos",
            "raiz %d, pai %r, filhos %r" % (raiz_pid, raiz_ppid, folhas))
    for p in [raiz_pid] + folhas:
        try:
            os.kill(p, 9)
        except OSError:
            pass

print("── fail-safe: sem leitura de processos, ninguém morre ──")
eq(lixeiro.candidatos(SID, "sessao", procs=[]), [], "lista vazia de processos não gera candidato")

print("── inventário: lista, nunca encerra ──")
inv = lixeiro.inventario(idade_min=0)
if isinstance(inv, list):
    ok("inventário devolve lista (%d itens nesta máquina)" % len(inv))
    intocaveis = [i for i in inv if i["classe"] == "intocavel"]
    if all(i.get("procedencia") for i in inv):
        ok("todo item do inventário declara a procedência")
    else:
        bad("todo item declara procedência", "campo preenchido", "faltando")
    ok("intocáveis aparecem no inventário como relatório: %d" % len(intocaveis))
else:
    bad("inventário devolve lista", "list", type(inv))

print("── varredura: o inventário acusa o que a anotação não viu ──")
# A anotação pega no pulo — e o que ela deixa passar (comando que o harness não
# viu, processo que trocou de linha de comando, servidor que soltou do pai) some
# do inventário, porque só entrava quem tem classe. A varredura procura ESSES,
# e a prova que ela exige é procedência minerada, nunca nome de programa.
SID_V = "sessao-varredura"
DONO_V = 7000
lixeiro.grava_registro({"session_id": SID_V, "dono_pid": DONO_V, "anotacoes": [
    {"cmd": "npm run dev", "cwd": "/proj/varredura", "classe": "servico",
     "em": time.time() - 30, "cpu_ultimo_turno": None},
]})
procs_v = [
    proc(DONO_V, "claude --resume abc", idade=9000, ppid=1),
    # o que a anotação VIU
    proc(7001, "node /proj/varredura/node_modules/.bin/vite --port 5199", idade=20, ppid=DONO_V),
    # o que ela NÃO viu: longa vida, sem classe, nascido dentro da sessão
    proc(7002, "/opt/homebrew/bin/servidorzinho --porta 9", idade=9000, ppid=DONO_V, rss=204800),
    # ruído da máquina: longa vida, sem classe e sem procedência nenhuma
    proc(7003, "/Applications/Navegador.app/Contents/MacOS/Navegador", idade=90000, ppid=1, rss=512000),
]
inv_v = {i["pid"]: i for i in lixeiro.inventario(idade_min=0, idade_suspeito=3600, procs=procs_v)}
eq(inv_v.get(7002, {}).get("classe"), "suspeito",
   "processo de longa vida sem anotação aparece como suspeito no inventário")
eq(inv_v.get(7002, {}).get("procedencia"), "sem anotação — achado pela varredura",
   "…e separado, na procedência, de quem tem dono conhecido")
eq(bool(inv_v.get(7002, {}).get("pista")), True, "o suspeito diz por que foi apontado")
eq(inv_v.get(7001, {}).get("classe"), "servico", "o que a anotação viu mantém a classe dele")
eq(inv_v.get(7001, {}).get("procedencia"), "anotado", "…e continua com procedência anotada")
eq(7003 in inv_v, False,
   "sem linhagem de sessão nem pasta de projeto, não vira suspeito (nome nunca é critério)")
eq(inv_v.get(DONO_V, {}).get("classe"), "intocavel",
   "a própria sessão consta como intocável, nunca como suspeita")

print("── órfão de família não prevista: aparece rotulado, em vez de sumir ──")
# Processo velho cujo PAI SUMIU (adotado pelo init): não tem linhagem para
# consultar e o programa é inventado — nenhuma classe casa. Antes ele era
# descartado em silêncio. Agora entra pela procedência que sobra: o caminho do
# projeto anotado está no próprio comando dele.
procs_o = [
    proc(DONO_V, "claude --resume abc", idade=9000, ppid=1),
    # binário inventado, de nome que classe nenhuma conhece, com o pai perdido
    proc(7004, "/proj/varredura/.venv/bin/rodadordejobs --fila 3", idade=9000, ppid=1, rss=204800),
    # mesmo abandono, mas sem projeto anotado no comando: continua fora
    proc(7005, "/opt/inventado/bin/coisadesconhecida --loop", idade=9000, ppid=1, rss=204800),
]
inv_o = {i["pid"]: i for i in lixeiro.inventario(idade_min=0, idade_suspeito=3600, procs=procs_o)}
eq(inv_o.get(7004, {}).get("classe"), "sem classe conhecida",
   "órfão que não casa classe nenhuma aparece rotulado 'sem classe conhecida'")
eq(inv_o.get(7004, {}).get("pista"),
   "o pai sumiu e o comando aponta para um projeto que a sessão tocou",
   "…e diz por que foi apontado: o projeto anotado, nunca o nome do programa")
eq(7005 in inv_o, False,
   "órfão sem projeto anotado no comando continua fora (nome nunca é critério)")

print("── rascunho de sessão que não existe mais: procedência sem anotação ──")
# O servidor que subiu dentro do rascunho de uma sessão continua de pé depois que
# ela morreu. Nenhuma anotação o explica (o harness não viu o comando), o nome do
# programa não pode ser critério — mas a PASTA de trabalho dele carrega o id da
# sessão dona, e sessão que não existe mais não tem mais a quem servir.
SID_MORTA = "3f2a1b0c-1111-2222-3333-444455556666"
SID_VIVA = "9e8d7c6b-1111-2222-3333-444455556666"
RASCUNHO = "/private/tmp/claude-501/-Users-quem-instalou-proj/%s/scratchpad"
CLAUDE_VIVO = 7100
procs_r = [
    proc(CLAUDE_VIVO, "/Users/quem-instalou/.local/bin/claude --resume abc", idade=9000, ppid=1),  # public-ok: conta ficticia; o teste existe pra provar que o caminho ABSOLUTO do harness e reconhecido — trocar por ~ mata o caso
    # servidor no rascunho da sessão MORTA: pai perdido, nenhuma anotação
    proc(7101, "python3 -m http.server 8000", idade=9000, ppid=1, rss=204800),
    # mesmo caso, mas a sessão dona do rascunho está viva: NÃO é órfão
    proc(7102, "python3 -m http.server 8001", idade=9000, ppid=CLAUDE_VIVO, rss=204800),
    # programa que classe nenhuma conhece, no rascunho da sessão morta
    proc(7103, "/opt/inventado/bin/coisadesconhecida --loop", idade=9000, ppid=1, rss=204800),
]
# A pasta de trabalho real vem do `lsof`; aqui ela é injetada no cache que
# `cwd_de` consulta primeiro, para a suíte não depender de processo de verdade.
lixeiro._CWD_CACHE[7101] = RASCUNHO % SID_MORTA
lixeiro._CWD_CACHE[7102] = RASCUNHO % SID_VIVA
lixeiro._CWD_CACHE[7103] = (RASCUNHO % SID_MORTA) + "/sonda"
eq(lixeiro.sessao_do_rascunho(RASCUNHO % SID_MORTA), SID_MORTA,
   "o id da sessão é lido do caminho do rascunho")
eq(lixeiro.sessao_do_rascunho("/Users/quem-instalou/proj/scratchpad"), None,  # public-ok: conta ficticia; o teste existe pra provar que o caminho ABSOLUTO do harness e reconhecido — trocar por ~ mata o caso
   "pasta chamada 'scratchpad' fora do rascunho do harness não vale como procedência")
eq(lixeiro.orfao_de_rascunho(7101, procs_r), SID_MORTA,
   "processo no rascunho de sessão inexistente é órfão daquela sessão")
eq(lixeiro.orfao_de_rascunho(7102, procs_r), None,
   "…e o do rascunho de sessão que ainda vive NÃO é órfão")
inv_r = {i["pid"]: i for i in lixeiro.inventario(idade_min=0, idade_suspeito=3600, procs=procs_r)}
eq(inv_r.get(7101, {}).get("procedencia"), "órfão — rascunho de sessão que não existe mais",
   "o inventário declara a procedência do servidor da sessão morta")
eq(inv_r.get(7102, {}).get("procedencia"), "sem dono conhecido",
   "o servidor da sessão viva continua sem procedência (não é acusado por acaso)")
eq(inv_r.get(7103, {}).get("pista"), "trabalha no rascunho de uma sessão que não existe mais",
   "processo sem classe no rascunho morto aparece pela varredura, em vez de sumir")

print("── o inventário pesa a ÁRVORE, não o processo sozinho ──")
# Um lançador de 5 MB segurando 590 MB de filhos ficava no fim da lista, atrás de
# qualquer processo gordo isolado — e o dono nunca via os 590 MB que fechá-lo
# devolve. O peso que ordena passa a ser o da árvore inteira.
LEVE = 8000        # o pai: 5 MB
procs_a = [
    proc(LEVE, "node /proj/arvore/node_modules/.bin/vite --port 5199", idade=9000, ppid=1, rss=5120),
    proc(8001, "esbuild --serve", idade=9000, ppid=LEVE, rss=302080),      # 295 MB
    proc(8002, "esbuild --serve", idade=9000, ppid=8001, rss=302080),      # 295 MB, neto
    proc(8010, "python3 -m http.server 8000", idade=9000, ppid=1, rss=102400),  # 100 MB sozinho
]
inv_a = lixeiro.inventario(idade_min=0, idade_suspeito=3600, procs=procs_a)
por_pid_a = {i["pid"]: i for i in inv_a}
eq(por_pid_a.get(LEVE, {}).get("rss_mb"), 5, "o peso do processo sozinho continua aparecendo")
eq(por_pid_a.get(LEVE, {}).get("arvore_mb"), 595,
   "…e ao lado dele vem o peso da árvore (5 MB + 295 + 295, o neto incluído)")
eq(por_pid_a.get(8010, {}).get("arvore_mb"), 100, "quem não tem filho pesa o que sempre pesou")
ordem_a = [i["pid"] for i in inv_a]
eq(ordem_a.index(LEVE) < ordem_a.index(8010), True,
   "o pai leve com filhos pesados vem ANTES do processo gordo sozinho")

print("── o registro não se apaga na mesma rodada em que foi escrito ──")
# A anotação aponta para um projeto que não existe nesta máquina: ela não casa
# processo nenhum. Antes, a limpeza do fim de turno a descartava já na primeira
# rodada — o motor anotava e apagava a própria procedência de uma vez.
SID_G = "sessao-graca"
lixeiro.grava_registro({"session_id": SID_G, "dono_pid": meu_pid, "anotacoes": [
    {"cmd": "npm run dev", "cwd": "/proj/que-nao-existe-em-lugar-nenhum",
     "classe": "servico", "em": time.time(), "cpu_ultimo_turno": None},
]})
# Pelo caminho de verdade: é o que `stop-colhe-turno.sh` chama.
lixeiro.main(["lixeiro.py", "colhe-turno", "--sessao", SID_G])
eq(len(lixeiro.le_registro(SID_G)["anotacoes"]), 1,
   "anotação que não casou nada SOBREVIVE à primeira rodada")
lixeiro.main(["lixeiro.py", "colhe-turno", "--sessao", SID_G])
eq(len(lixeiro.le_registro(SID_G)["anotacoes"]), 0,
   "e some na rodada seguinte, quando a falta de processo se confirma")

print("── a família: processos idênticos numa linha só ──")
# Quinze trabalhadores do mesmo compilador são UMA decisão. O que o usuário
# precisa ver é a contagem e a soma da memória, não quinze linhas iguais.
IGUAL = "node /proj/node_modules/.bin/esbuild --service=0.21.5"
ITENS = [{"pid": 900 + i, "cmd": IGUAL, "rss_mb": 40, "arvore_mb": 40,
          "idade_min": 30 + i, "cpu_s": 1.0, "classe": "efemero",
          "procedencia": "anotado"} for i in range(15)]
ITENS.append({"pid": 800, "cmd": "node /proj/node_modules/.bin/vite --port 5199",
              "rss_mb": 120, "arvore_mb": 300, "idade_min": 90, "cpu_s": 3.0,
              "classe": "servico", "procedencia": "sem dono conhecido"})

GRUPOS = lixeiro.agrupa(ITENS)
eq(len(GRUPOS), 2, "16 processos viram 2 famílias")
familia = [g for g in GRUPOS if g["cmd"] == IGUAL][0]
eq(familia["n"], 15, "a família traz a CONTAGEM dos idênticos")
eq(familia["rss_mb"], 600, "e a SOMA da memória própria (15 × 40 MB)")
eq(familia["idade_min"], 44, "a idade da família é a do mais velho")
eq(len(familia["pids"]), 15, "os pids ficam inteiros — é o que o encerra recebe")
# Somar a árvore contaria o mesmo filho duas vezes quando um membro está dentro
# do outro; a família fica com o pior caso real, não com a soma inflada.
eq(familia["arvore_mb"], 40, "a árvore não soma dentro da família: fica o maior")
solo = [g for g in GRUPOS if g["cmd"] != IGUAL][0]
eq(solo["n"], 1, "processo sem irmão idêntico continua sozinho")
eq([g["n"] for g in GRUPOS], [15, 1], "a família mais pesada vem primeiro")
# Procedência diferente é decisão diferente: não se juntam nem com comando igual.
eq(len(lixeiro.agrupa([
    {"pid": 1, "cmd": IGUAL, "rss_mb": 10, "arvore_mb": 10, "idade_min": 5,
     "cpu_s": 0.0, "classe": "efemero", "procedencia": "anotado"},
    {"pid": 2, "cmd": IGUAL, "rss_mb": 10, "arvore_mb": 10, "idade_min": 5,
     "cpu_s": 0.0, "classe": "efemero", "procedencia": "sem dono conhecido"}])), 2,
   "mesmo comando com procedência diferente NÃO vira uma decisão só")

TEXTO = lixeiro.resumo_terminal(ITENS)
LINHAS = [ln for ln in TEXTO.splitlines() if ln.strip()]
if len(LINHAS) < 20:
    ok("o terminal cabe em %d linhas para 16 processos (sem página)" % len(LINHAS))
else:
    bad("o resumo cabe no terminal", "menos de 20 linhas", len(LINHAS))
if "15×" in TEXTO and "600 MB" in TEXTO:
    ok("a linha da família mostra contagem e soma: 15× / 600 MB")
else:
    bad("contagem e soma na linha da família", "15× e 600 MB", TEXTO[:200])
if TEXTO.count(IGUAL) == 1:
    ok("o comando idêntico aparece UMA vez, não quinze")
else:
    bad("comando idêntico numa linha só", 1, TEXTO.count(IGUAL))
eq(lixeiro.resumo_terminal([]), "Nada de pé para faxinar.", "sem processo, diz isso e para")

# E o caminho do produto: a skill chama `resumo` pela linha de comando. Sem esta
# porta, a função acima não é invocada por caminho nenhum.
_SAIDA = subprocess.run([sys.executable, os.path.join(AQUI, "lixeiro.py"), "resumo",
                         "--idade-min", "999999999"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                        env=dict(os.environ, CLAUDE_CONFIG_DIR=TMP), stdin=subprocess.DEVNULL, start_new_session=True)
if _SAIDA.returncode == 0 and _SAIDA.stdout.strip():
    ok("`lixeiro.py resumo` responde pela linha de comando (o que a skill chama)")
else:
    bad("`lixeiro.py resumo` responde", "rc 0 e texto", (_SAIDA.returncode, _SAIDA.stderr[:120]))

print("── os rótulos da skill são os que o motor emite ──")
# A skill /faxina ensina o usuário a ler `classe` e `procedencia` citando os
# rótulos LITERAIS. Eles nascem escritos à mão em `inventario` e em `suspeitos`:
# trocar um lá dentro deixava a skill mentindo em silêncio, porque nenhum teste
# lia o SKILL.md. Aqui as duas listas se conferem, e nas DUAS direções — rótulo
# emitido que a skill não cita reprova, e rótulo citado que ninguém emite também.
SKILL = os.path.join(AQUI, "..", "skills", "faxina", "SKILL.md")
_TXT = open(SKILL, encoding="utf-8").read()
# A seção do contrato: do parágrafo da `classe` até o fim da lista de procedência.
_ABRE, _FECHA = "A `classe` tem", "Essa faixa é o ponto"
if _ABRE in _TXT and _FECHA in _TXT:
    ok("a skill ainda traz a seção que explica classe e procedência")
    _TRECHO = _TXT[_TXT.index(_ABRE):_TXT.index(_FECHA)]
    # Nomes de CAMPO e de opção não são rótulo — o que se compara é o valor.
    _META = {"classe", "procedencia", "pista", "--idade-suspeito"}
    CITADOS = set(re.findall(r"`([^`\n]+)`", _TRECHO)) - _META

    # Uma máquina plantada que produz os quatro caminhos de procedência e as
    # cinco classes de uma vez. Nenhum processo de verdade participa.
    SID_C = "sessao-contrato"
    DONO_C = 7300
    lixeiro.grava_registro({"session_id": SID_C, "dono_pid": DONO_C, "anotacoes": [
        {"cmd": "python -m pytest tests/ -q", "cwd": "/proj/contrato",
         "classe": "efemero", "em": time.time() - 30, "cpu_ultimo_turno": None},
    ]})
    procs_c = [
        # a própria sessão: intocável, e nunca suspeita
        proc(DONO_C, "/Users/quem-instalou/.local/bin/claude --resume xyz", idade=9000, ppid=1),  # public-ok: conta ficticia; o teste existe pra provar que o caminho ABSOLUTO do harness e reconhecido — trocar por ~ mata o caso
        # o que a anotação viu: classe do comando + procedência anotada
        proc(7301, "python -m pytest /proj/contrato/tests -q", idade=20, ppid=DONO_C),
        # serviço vivo que anotação nenhuma explica
        proc(7302, "node /proj/contrato/node_modules/.bin/vite --port 5199",
             idade=9000, ppid=1, rss=204800),
        # serviço no rascunho de uma sessão que não existe mais
        proc(7303, "python3 -m http.server 8000", idade=9000, ppid=1, rss=204800),
        # sem classe, nascido dentro da sessão morta: a faixa dos suspeitos
        proc(7304, "/opt/homebrew/bin/servidorzinho --porta 9", idade=9000,
             ppid=DONO_C, rss=204800),
        # sem classe, pai sumido, projeto anotado no próprio comando
        proc(7305, "/proj/contrato/.venv/bin/rodadordejobs --fila 3",
             idade=9000, ppid=1, rss=204800),
    ]
    lixeiro._CWD_CACHE[7303] = RASCUNHO % SID_MORTA
    inv_c = lixeiro.inventario(idade_min=0, idade_suspeito=3600, procs=procs_c)
    EMITIDOS = {i["classe"] for i in inv_c} | {i["procedencia"] for i in inv_c}

    # A plantação tem que exercitar o vocabulário inteiro; se ela parar de
    # produzir um caminho, a comparação abaixo vira teatro.
    eq(len(EMITIDOS), 9, "a máquina plantada produz as 5 classes e as 4 procedências")
    orfas = EMITIDOS - CITADOS
    mortas = CITADOS - EMITIDOS
    if not orfas:
        ok("todo rótulo que o motor emite está escrito na skill (%d)" % len(EMITIDOS))
    else:
        bad("rótulo emitido que a skill não ensina", "nenhum", sorted(orfas))
    if not mortas:
        ok("todo rótulo que a skill ensina o motor ainda emite (%d)" % len(CITADOS))
    else:
        bad("rótulo citado na skill que ninguém emite", "nenhum", sorted(mortas))
else:
    bad("a skill traz a seção de classe e procedência", "%r … %r" % (_ABRE, _FECHA),
        "âncora não encontrada em %s" % SKILL)

print("── prova anti-tautologia ──")
# Sabota a trava de intocável e exige que a decisão MUDE. Sem isto, a suíte pode
# estar afirmando nada — o precedente está no test_pre_deploy.sh do ship.
_orig = lixeiro.INTOCAVEL
lixeiro.INTOCAVEL = []
try:
    sabotado = lixeiro.casa(anot_vite, proc(106, "limactl hostagent --pidfile x", idade=10))
    # com a trava fora, o intocável deixa de ser barrado POR ELA (pode ainda
    # não casar por classe/marca — o que importa é a trava ter efeito medível)
    barrado_por_classe = lixeiro.classifica("limactl hostagent --pidfile x") != "servico"
    if barrado_por_classe:
        ok("sem a trava, limactl não vira serviço por acaso — a barreira de classe segura")
    else:
        eq(sabotado, True, "sem a trava de intocável a decisão muda (a trava tem efeito)")
finally:
    lixeiro.INTOCAVEL = _orig

print("")
print("lixeiro: %d ok, %d falhas" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
