#!/usr/bin/env python3
"""A esteira tem UMA casa, e ninguém reconstrói os globs de cabeça (F17.3).

A seleção completa das suítes morava só dentro do `portability.yml`. Quem
precisava dela fora do CI reconstruía a lista — e em 2026-08-13 a casca do
`/sprint` reconstruiu errado: passou `run_suites.py` pelado ao motor, que rodou
ZERO suítes e declarou a corrida verde.

O que esta suíte cobra não é o conteúdo dos globs (esse muda quando o repo muda),
é a UNICIDADE: um lugar escreve a lista, os outros a invocam.

    python3 scripts/test_suite_casa_unica.py
"""

import glob
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASA = os.path.join(RAIZ, "scripts", "suite.sh")
ok = falhas = 0


def check(nome, cond, detalhe=""):
    global ok, falhas
    if cond:
        ok += 1
        print("  ✓ %s" % nome)
    else:
        falhas += 1
        print("  ✗ %s%s" % (nome, ("\n      %s" % detalhe) if detalhe else ""))


def texto(caminho):
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


print("F17.3 — a esteira tem uma casa só")

check("a casa existe e é executável", os.path.exists(CASA) and os.access(CASA, os.X_OK),
      CASA)

casa = texto(CASA)
# Os globs que definem a esteira. Contamos os que a casa declara para poder exigir
# que ninguém MAIS os declare — o número sai daqui, nunca escrito à mão.
# Só conta como glob DA ESTEIRA o que traz CAMINHO (`plugins/*/lib/test_*.py`).
# `test_*.py` solto é padrão de NOME — o `find` genérico que o motor escreve no
# prompt para projeto que não declara suíte —, e confundir os dois faria esta
# suíte acusar o motor de reconstruir uma esteira que ele nem conhece.
GLOB_RE = re.compile(r"'([^']*/[^']*test_\*\.(?:py|sh))'")
da_casa = set(GLOB_RE.findall(casa))
check("a casa declara os globs da esteira", len(da_casa) >= 5,
      "achei %d: %s" % (len(da_casa), sorted(da_casa)))

# ── A unicidade, e o que ela REALMENTE proíbe ─────────────────────────────────
# Não é ter glob de teste em outro arquivo: o portão de commit (`release-gate.sh`,
# check J) roda de propósito um RECORTE da esteira — só quando o commit toca hook
# ou script —, e esse recorte é deliberado e documentado, não uma segunda esteira.
# Recortar é legítimo; DIVERGIR não é. O que reprova aqui é glob de suíte que
# existe fora da casa e que a casa NÃO tem: aí as duas listas já andaram para
# lados diferentes, e é dessa divergência silenciosa que a esteira fica com buraco
# (a suíte roda no commit e não roda no CI, ou o contrário).
EXECUTAVEIS = (".sh", ".yml", ".yaml", ".py", ".js")
IGNORA = {os.path.join(RAIZ, "scripts", "suite.sh"),
          os.path.join(RAIZ, "scripts", "test_suite_casa_unica.py"),
          # o rodador cita os globs no próprio texto de uso (docstring)
          os.path.join(RAIZ, "scripts", "run_suites.py"),
          # o cobrador de órfãs monta uma esteira DE MENTIRA no arnês dele; os
          # globos que ele escreve lá são cenário de teste, não segunda casa.
          os.path.join(RAIZ, "scripts", "test_suites_orfas.py")}
divergentes = []
for base, dirs, arqs in os.walk(RAIZ):
    dirs[:] = [d for d in dirs
               if d not in {".git", "node_modules", "__pycache__", "graphify-out", ".venv"}]
    for a in arqs:
        p = os.path.join(base, a)
        if p in IGNORA or not a.endswith(EXECUTAVEIS):
            continue
        try:
            t = texto(p)
        except (OSError, UnicodeDecodeError):
            continue
        fora = set(GLOB_RE.findall(t)) - da_casa
        if fora:
            divergentes.append((os.path.relpath(p, RAIZ), sorted(fora)))
check("nenhum glob de suíte vive fora da casa (recorte pode; divergir não)",
      not divergentes, "divergência: %s" % divergentes)

# ── O CI usa a casa (senão a casa é enfeite) ──────────────────────────────────
ci = texto(os.path.join(RAIZ, ".github", "workflows", "portability.yml"))
check("o CI invoca a casa em vez de repetir os globs", "scripts/suite.sh" in ci,
      "portability.yml não chama scripts/suite.sh")

# ── O CLAUDE.md aponta a casa (é de lá que a casca do /sprint lê) ─────────────
claude_md = texto(os.path.join(RAIZ, ".claude", "CLAUDE.md"))
check("o CLAUDE.md nomeia a casa", "scripts/suite.sh" in claude_md,
      "sem o ponteiro, a casca volta a reconstruir de cabeça")

# ── E a casa REALMENTE seleciona (não é um arquivo que só existe) ─────────────
# ⚠️ NÃO se roda a esteira aqui. A versão anterior chamava `suite.sh --timeout 1`
# achando que o teto de 1s a faria voltar rápido — mas o teto é POR SUÍTE, não da
# rodada, e as 135 continuam saindo. O teste pendurava e morria nos 120s dele
# (medido em 2026-08-14). O que interessa é a SELEÇÃO, e ela se mede expandindo os
# globos da casa aqui mesmo, sem disparar processo nenhum.
alvos = set()
for g in da_casa:
    alvos |= {p for p in glob.glob(g) if os.path.isfile(p)}
check("a casa seleciona suítes de verdade", len(alvos) > 50,
      "os globos da casa expandem para %d arquivo(s)" % len(alvos))

# E a seleção cobre TUDO que o git rastreia como suíte — a esteira em duas fases
# não pode ter deixado ninguém de fora ao dividir os globos.
r = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=RAIZ, timeout=60,
                   stdin=subprocess.DEVNULL, start_new_session=True)
rastreadas = {f for f in r.stdout.split()
              if re.search(r"(^|/)test_[^/]*\.(py|sh)$", f)}
fora = sorted(rastreadas - alvos)
check("nenhuma suíte rastreada ficou fora da esteira", not fora,
      "de fora: %s" % fora[:6])

print("\nsuite-casa-única: %d ok, %d falhas" % (ok, falhas))
sys.exit(1 if falhas else 0)
