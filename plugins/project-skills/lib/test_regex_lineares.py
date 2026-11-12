#!/usr/bin/env python3
"""Regex lineares (P11) — texto hostil não pode fazer o motor girar.

Cada padrão abaixo era quadrático (ou exponencial) numa entrada que um repositório
de terceiros controla: uma linha de doc, um arquivo versionado, um passo de plano,
um glob do organism.yaml, a mensagem de um commit. A prova é de TEMPO, medida num
processo filho com teto — assim a suíte reprova depressa em vez de pendurar quando o
padrão volta a ser lento — e de SEMÂNTICA, porque reescrever padrão não pode mudar
o que ele reconhece em texto normal.

Roda com:  python3 plugins/project-skills/lib/test_regex_lineares.py
"""
import os
import random
import string
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# o scrub etiqueta segredos com o sal da instalação: aqui ele mora num arquivo descartável
os.environ["PROJECT_DOC_SALT_FILE"] = os.path.join(
    tempfile.mkdtemp(prefix="pdregex-"), "journal.salt")

TETO_S = 1.0          # cada entrada hostil tem que terminar abaixo disto
LIMITE_FILHO_S = 8    # o filho é morto aqui: padrão lento reprova, não pendura
PASSED = 0
FALHAS = []


def check(name, cond, detail=""):
    """Não para na primeira falha: o relatório mostra TODOS os padrões lentos de uma vez."""
    global PASSED
    if not cond:
        print("  FALHOU · %s %s" % (name, detail))
        FALHAS.append(name)
        return
    print("  ok · %s" % name)
    PASSED += 1


def mede(corpo):
    """Roda `corpo` num filho (com os módulos importados) e devolve os segundos de CPU que
    ELE gastou, sem contar o import (CPU, não relógio: a máquina de teste fica carregada). None = estourou o limite do filho."""
    prog = (
        "import sys, time, random, string\n"
        "sys.path.insert(0, %r)\n"
        "import doc_lint, organism, journal\n"
        "import precheck_largada as p\n"
        "t0 = time.process_time()\n"
        "%s\n"
        "print(time.process_time() - t0)\n"
    ) % (HERE, corpo)
    try:
        r = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True,
                           timeout=LIMITE_FILHO_S, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None
    if r.returncode != 0:
        print(r.stderr[-600:])
        sys.exit(1)
    return float(r.stdout.strip().splitlines()[-1])


def rapido(nome, corpo):
    t = mede(corpo)
    check("%s (< %.0fs)" % (nome, TETO_S), t is not None and t < TETO_S,
          "— levou %s" % ("mais de %ds" % LIMITE_FILHO_S if t is None else "%.2fs" % t))


# ── doc_lint: os dois padrões do finding (ponteiro arquivo:N e leitura de env) ──
rapido("doc_lint.POINTER_RE: linha pontilhada de 300 KB",
       "doc_lint.POINTER_RE.findall('a.' * 150000)")
rapido("doc_lint.POINTER_RE: linha de hífens de 300 KB",
       "doc_lint.POINTER_RE.findall('-' * 300000)")
rapido("doc_lint.ENV_READ_PATTERNS: arquivo de 512 KB só de quebras de linha",
       "[r.findall('\\n' * 524288) for r in doc_lint.ENV_READ_PATTERNS]")
rapido("doc_lint.ENV_READ_PATTERNS: 512 KB de espaço em branco",
       "[r.findall(' \\n' * 262144) for r in doc_lint.ENV_READ_PATTERNS]")
rapido("doc_lint.COUNT_RE: corrida de 300 KB de dígitos",
       "doc_lint.COUNT_RE.findall('1' * 300000)")

# ── precheck_largada: caminho, período e medida num passo de plano sem teto ──
rapido("precheck._CAMINHO: 300 KB de uma palavra só",
       "p._CAMINHO.findall('a' * 300000)")
rapido("precheck._CAMINHO: 300 KB de segmentos sem extensão",
       "p._CAMINHO.findall('a/' * 150000)")
rapido("precheck._CAMINHO: 300 KB de segmentos com ponto",
       "p._CAMINHO.findall('a.' * 150000)")
rapido("precheck._PERIODO: corrida de 300 KB de dígitos",
       "p._PERIODO.findall('1' * 300000)")
rapido("precheck._MEDIDAS: corrida de 300 KB de dígitos",
       "p._MEDIDAS.findall('1' * 300000)")

# ── organism: glob com vários `**/` contra um caminho que não casa ─────────────
rapido("organism._matches: 12 `**/` num caminho de 40 segmentos",
       "organism._matches('**/' * 12 + 'zzz', 'a/' * 40 + 'b')")
rapido("organism._matches: `**/` intercalado com `*` num caminho longo",
       "organism._matches('**/a*/' * 8 + 'zzz.py', 'a/' * 2000 + 'b')")
rapido("organism._matches: caminho de 200 KB contra `**/x`",
       "organism._matches('**/x', 'a/' * 100000 + 'b')")

# ── journal.scrub: tokens demais, sinais demais, marcadores demais ─────────────
GERA_TOKENS = ("random.seed(7); al = string.ascii_letters + string.digits; "
               "txt = ' '.join(''.join(random.choice(al) for _ in range(20)) for _ in range(%d)); ")
rapido("journal.scrub: 15 mil tokens aleatórios distintos (~315 KB)",
       GERA_TOKENS % 15000 + "journal.scrub(txt)")
rapido("journal.scrub: 60 mil palavras-sinal seguidas",
       "journal.scrub('token ' * 60000)")
rapido("journal.scrub: 300 KB de marcadores de abertura sem fecho",
       "journal.scrub('\\u2039 ' * 150000)")

# ── semântica: o que o padrão reconhecia em texto normal continua reconhecido ──
print("  — semântica preservada —")
POINTER_CASOS = [
    ("veja src/app.py:42 e pronto", [("src/app.py", "42")]),
    ("[src/app.py:7]", [("[src/app.py", "7")]),   # o `[` entra no grupo, como sempre entrou
    ("`lib/a.b/c-d.ts:3` e `x.py:9`", [("lib/a.b/c-d.ts", "3"), ("x.py", "9")]),
    ("/abs/dir/file.json:10", []),   # path absoluto: o `(?<![\w/])` sempre o recusou
    ("app/[id]/page.tsx:12", [("app/[id]/page.tsx", "12")]),
    ("Node.js:20 e Next.js:14", []),
    ("main.py:1:util.sh:2", [("main.py", "1"), ("util.sh", "2")]),
    ("sem ponteiro algum", []),
]
import doc_lint  # noqa: E402
for texto, esperado in POINTER_CASOS:
    achou = doc_lint.POINTER_RE.findall(texto)
    check("POINTER_RE %r" % texto, achou == esperado, "— veio %r" % (achou,))

ENV_TEXTO = ("  - DB_HOST=localhost\n"
             "\n\n   SECRET_KEY=abc\n"
             "ENV   APP_MODE production\n"
             "  Environment=\"UNIT_VAR=1\"\n"
             "-\nLATER_VAR=2\n"
             "x = os.getenv('PY_VAR')\n")
lidas = set()
for rx in doc_lint.ENV_READ_PATTERNS:
    lidas.update(rx.findall(ENV_TEXTO))
check("ENV_READ_PATTERNS lê compose, .env, Dockerfile, systemd e código",
      {"DB_HOST", "SECRET_KEY", "APP_MODE", "UNIT_VAR", "PY_VAR"} <= lidas, "— veio %r" % sorted(lidas))

import precheck_largada as p  # noqa: E402
from caminho_igual import igual  # noqa: E402


def mesmos_caminhos(achados, esperados):
    return len(achados) == len(esperados) and all(igual(a, b) for a, b in zip(achados, esperados))


check("_CAMINHO acha caminho com diretório e extensão",
      mesmos_caminhos(p._CAMINHO.findall("edita lib/a.py e pkg/x/y.md hoje"), ["lib/a.py", "pkg/x/y.md"]))
check("_CAMINHO ainda acha o caminho que vem depois de uma barra solta",
      mesmos_caminhos(p._CAMINHO.findall("a//b/c.py"), ["b/c.py"]))
check("_PERIODO lê número + unidade", p._periodos("a cada 30 minutos ou 2h") == [1800, 7200])
check("_PERIODO ignora dígito dentro de palavra", p._periodos("v10x") == [])

import organism  # noqa: E402
GLOB_CASOS = [
    ("**/*.py", "a/b/c.py", True),
    ("**/*.py", "c.py", True),
    ("**/*.py", "a/b/c.js", False),
    ("src/**/x.py", "src/x.py", True),
    ("src/**/x.py", "src/a/b/x.py", True),
    ("src/**/x.py", "other/a/x.py", False),
    ("src/*.py", "src/a.py", True),
    ("src/*.py", "src/a/b.py", False),
    ("lib/foo.py", "lib/foo.py", True),
    ("lib/foo.py", "lib/foo.pyc", False),
    ("a/**", "a/b/c", True),
    ("a/**", "b/a/c", False),
    ("*", "x", True),
    ("*", "x/y", False),
    ("**", "x/y/z", True),
    ("a?b", "a?b", True),
    ("a?b", "axb", False),
    ("a[1]", "a[1]", True),
    ("a.b", "axb", False),
    ("**/**/x", "x", True),
    ("**/a/**/b", "q/a/r/b", True),
    ("**/a/**/b", "q/a/r/c", False),
]
for glob, caminho, esperado in GLOB_CASOS:
    check("glob %r × %r → %s" % (glob, caminho, esperado),
          organism._matches(glob, caminho) is esperado)

import journal  # noqa: E402
s, sec = journal.scrub("password secret aB3xK9mPq2LwZ7vT4n agora")
check("scrub continua redigindo segredo em prosa", "aB3xK9mPq2LwZ7vT4n" not in s and sec)
random.seed(3)
al = string.ascii_letters + string.digits
tok = "".join(random.choice(al) for _ in range(24))
s, _ = journal.scrub("a x %s y %s z" % (tok, tok))
check("scrub continua marcando token opaco duas vezes, sem sobrepor",
      s == "a x %s‹revisar?› y %s‹revisar?› z" % (tok, tok), "— veio %r" % s)

s, sec = journal.scrub("\u2039 is a token hunter2xyz! \u2039cofre:X:1\u203a")
check("scrub: um `\u2039` solto não esconde o segredo que vem depois", "hunter2xyz!" not in s and sec, "— veio %r" % s)

print("\ntest_regex_lineares: %d ok, %d falha(s)" % (PASSED, len(FALHAS)))
sys.exit(1 if FALHAS else 0)
