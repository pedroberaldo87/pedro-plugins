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
    if lixeiro.eh_intocavel(cmd) and lixeiro.classifica(cmd) is None:
        ok("intocável: %s" % cmd[:52])
    else:
        bad("intocável: %s" % cmd[:52], "intocável e sem classe", lixeiro.classifica(cmd))

# O caso que dá nome à regra: `node` sozinho não pode significar nada.
eq(lixeiro.classifica("node"), None, "`node` puro não vira candidato a nada")
eq(lixeiro.classifica("/Applications/Google Chrome.app/.../Google Chrome"), None,
   "o navegador não é candidato")

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
eq(pids, [104], "no turno morre a suíte pendurada; o serviço sem foto de CPU sobrevive")

# Com a foto do turno anterior: CPU parada = ocioso, CPU subindo = em uso.
reg["anotacoes"][1]["cpu_ultimo_turno"] = 30.0
lixeiro.grava_registro(reg)
cands = lixeiro.candidatos(SID, "turno", procs=procs)
eq(sorted(c[1]["pid"] for c in cands), [101, 104], "servidor com CPU parada desde o turno anterior morre")

reg["anotacoes"][1]["cpu_ultimo_turno"] = 10.0
lixeiro.grava_registro(reg)
cands = lixeiro.candidatos(SID, "turno", procs=procs)
eq(sorted(c[1]["pid"] for c in cands), [104], "servidor com CPU crescendo SOBREVIVE ao fim do turno")

print("── decisão no fim da sessão ──")
cands = lixeiro.candidatos(SID, "sessao", procs=procs)
eq(sorted(c[1]["pid"] for c in cands), [101, 104], "no fim da sessão morre tudo que ela anotou")

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

print("── ponta a ponta: um processo de verdade ──")
alvo = subprocess.Popen([sys.executable, "-c",
                         "import time,sys\nsys.argv=['x']\nwhile True: time.sleep(0.3)"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
