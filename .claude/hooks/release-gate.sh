#!/usr/bin/env bash
# release-gate.sh — gate mecânico de release do monorepo pedro-plugins.
#
# PreToolUse(Bash): intercepta `git commit` e checa os invariantes que hoje só
# existiam como prosa no CLAUDE.md (vendoring, espelho de versão, bump, testes).
# Zero token, ~50ms. FAIL-OPEN em erro de infra (sem git/python3, fora do repo):
# só bloqueia com evidência concreta na mão.
set -uo pipefail

INPUT=$(cat 2>/dev/null) || exit 0

# O gatilho não pode depender da FORMA do comando. O grep ancorado em início-de-linha
# (ou logo depois de ; & |) que morava aqui deixava passar `env FOO=1 git commit`,
# `(git commit …)`, `bash -c "git commit …"` e `VAR=x git commit` — e com eles saíam,
# calados, os oito checks abaixo. Foi assim que 7 de 9 commits de uma rodada foram
# sem bump. Ele também disparava em `git log --grep commit`, que não commita nada:
# falso positivo ensina a contornar, e contornar desliga tudo.
# Aqui o comando é QUEBRADO em tokens (inclusive por (, ), ; e aspas, que é o que
# recupera as quatro formas) e o subcomando do git é lido de verdade, pulando as
# opções globais e os valores delas.
GATILHO=$(printf '%s' "$INPUT" | python3 -c '
import json, re, sys

try:
    cmd = json.load(sys.stdin).get("tool_input", {}).get("command", "") or ""
except Exception:
    sys.exit(1)

toks = [t for t in re.split(r"""[\s;&|()<>"'"'"'`]+""", cmd) if t]
GLOBAL_VALOR = {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
COMMIT_VALOR = {"-m", "--message", "-F", "--file", "-C", "--reuse-message",
                "-c", "--reedit-message", "--author", "--date", "-t",
                "--template", "--fixup", "--squash", "--trailer"}

for i, t in enumerate(toks):
    if t != "git" and not t.endswith("/git"):
        continue
    j = i + 1
    while j < len(toks) and toks[j].startswith("-"):
        j += 2 if toks[j] in GLOBAL_VALOR else 1
    if j >= len(toks) or toks[j] != "commit":
        continue
    # As aspas somem no split, então a mensagem vira token solto e um "--amend"
    # escrito DENTRO dela passaria por flag. Só as opções coladas no subcomando
    # contam: o primeiro token que não é opção nem valor de opção encerra.
    amend, k = False, j + 1
    while k < len(toks) and toks[k].startswith("-"):
        if toks[k] == "--amend":
            amend = True
            break
        k += 2 if toks[k] in COMMIT_VALOR else 1
    print("amend" if amend else "commit")
    sys.exit(0)
sys.exit(1)
' 2>/dev/null) || exit 0
[ -n "$GATILHO" ] || exit 0

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$ROOT/.claude-plugin/marketplace.json" ] || exit 0   # não é este monorepo

# arquivos que vão no commit: staged ∪ tracked-modificados (cobre `git commit -a`).
# Untracked NÃO entra: sem `git add` ele não é commitado — incluí-lo dava
# falso-positivo com estado de runtime (ex.: visual/skills/visual/config.json).
FILES=$( { git -C "$ROOT" diff --cached --name-only
           git -C "$ROOT" diff --name-only; } 2>/dev/null | sort -u )
[ -n "$FILES" ] || exit 0

VIOL=""

# A · vendoring de _shared/ (o único "build" do monorepo)
if [ -x "$ROOT/scripts/sync-shared.sh" ] || [ -f "$ROOT/scripts/sync-shared.sh" ]; then
  if ! OUT=$(bash "$ROOT/scripts/sync-shared.sh" --check 2>&1); then
    VIOL="${VIOL}
❌ VENDORING EM DRIFT — cópia de _shared/ divergiu da fonte:
${OUT}
   → corrija na FONTE (_shared/<arquivo>) e rode: bash scripts/sync-shared.sh"
  fi
fi

# A2 · contrato R8 servido de uma fonte só. Nasceu de defeito medido em 2026-08-03:
# trocar seis tiers custou 45 substituições em dois SKILL.md, três saíram invertidas e
# duas passaram por dois verificadores — porque o número morava em quinze lugares.
if [ -f "$ROOT/_shared/r8_tiers.py" ]; then
  if ! OUT=$(python3 "$ROOT/_shared/r8_tiers.py" check 2>&1); then
    VIOL="${VIOL}
❌ CONTRATO R8 FURADO — o tier voltou a ser carimbado fora da fonte:
${OUT}
   → o valor vive em _shared/r8-tiers.json e chega ao motor por args;
     o SKILL.md cita o KNOB, nunca o número. Isenção: 'r8-ok: <motivo>' na linha."
  fi
fi

# B+C · espelho plugin.json↔marketplace.json e bump esquecido
PYOUT=$(cd "$ROOT" && printf '%s\n' "$FILES" | GATE_AMEND="$GATILHO" python3 -c '
import json, subprocess, sys, os, re

files = [l.strip() for l in sys.stdin if l.strip()]
_cat = json.load(open(".claude-plugin/marketplace.json"))["plugins"]
mk = {e["name"]: e.get("version") for e in _cat}
mk_desc = {e["name"]: e.get("description") for e in _cat}
viol = []

# Em `--amend` o HEAD É o commit que está sendo reescrito: comparar com ele acusava
# BUMP ESQUECIDO de uma version que já estava dentro do próprio commit. O antes de
# verdade é HEAD~1. (Amend do commit raiz: `git show` falha e nada é acusado.)
BASE = "HEAD~1:" if os.environ.get("GATE_AMEND") == "amend" else "HEAD:"

def head_json(path):
    try:
        return json.loads(subprocess.run(["git", "show", BASE + path],
                                         capture_output=True, text=True, check=True).stdout)
    except Exception:
        return None

touched = sorted({m.group(1) for m in (re.match(r"plugins/([^/]+)/", f) for f in files) if m})

for name in touched:
    mf = "plugins/%s/.claude-plugin/plugin.json" % name
    if not os.path.exists(mf):
        continue
    cur = json.load(open(mf))
    pname, pver = cur.get("name", name), cur.get("version")

    # C · bump: plugin tocado cuja version é idêntica à do HEAD
    old = head_json(mf)
    if old is not None and old.get("version") == pver:
        viol.append("❌ BUMP ESQUECIDO — %s mudou mas version continua %s\n"
                    "   → suba a version em %s E espelhe em .claude-plugin/marketplace.json"
                    % (name, pver, mf))

    # B · espelho da VERSION
    if mk.get(pname) != pver:
        viol.append("❌ ESPELHO QUEBRADO — %s: plugin.json=%s · marketplace.json=%s\n"
                    "   → iguale as duas (o cliente lê a do marketplace)"
                    % (pname, pver, mk.get(pname)))

    # B2 · espelho da DESCRIPTION. Nasceu de erro medido em 2026-08-02: quatro
    # descricoes foram reescritas SO no marketplace.json, e `claude plugin details`
    # mostra a do plugin.json — a vitrine nova nunca chegaria a quem instala.
    # So cobra o plugin TOCADO neste commit: 6 dos 19 ja divergiam antes, e barrar
    # divida antiga trava trabalho alheio (mesma regra do public_repo_check --staged).
    cdesc, mdesc = cur.get("description"), mk_desc.get(pname)
    if cdesc and mdesc and cdesc != mdesc:
        viol.append("❌ DESCRIPTION DIVERGENTE — %s\n"
                    "   plugin.json  (%d chars): %s...\n"
                    "   marketplace  (%d chars): %s...\n"
                    "   → `claude plugin details` mostra a do plugin.json; a listagem do\n"
                    "     catalogo mostra a do marketplace. As duas sao lidas: iguale."
                    % (pname, len(cdesc), cdesc[:60], len(mdesc), mdesc[:60]))

print("\n".join(viol))
' 2>/dev/null)
[ -n "$PYOUT" ] && VIOL="${VIOL}
${PYOUT}"

# D · testes dos plugins tocados (stdlib, segundos)
for name in $(printf '%s\n' "$FILES" | sed -n 's#^plugins/\([^/]*\)/.*#\1#p' | sort -u); do
  for t in "$ROOT/plugins/$name/lib/"test_*.py; do
    [ -f "$t" ] || continue
    if ! OUT=$(cd "$ROOT" && python3 "$t" 2>&1); then
      VIOL="${VIOL}
❌ TESTE VERMELHO — ${t#$ROOT/}
$(printf '%s' "$OUT" | tail -15)"
    fi
  done
done

# D2 · suíte de _shared/ — a FONTE do código vendorado.
# O check D varre plugins/<nome>/lib/test_*.py e o F varre plugins/<nome>/hooks/test_*.sh:
# nenhum dos dois globs casa com _shared/test_*.py. A suíte que DEFINE o comportamento do
# código compartilhado (os perfis da régua de estilo) nunca rodava no commit, e o único
# jeito de ela valer era alguém lembrar de chamá-la à mão. Aqui ela passa a valer por
# derivação. Roda quando o commit toca _shared/ — no resto do tempo custa zero.
if printf '%s\n' "$FILES" | grep -qE '^_shared/'; then
  for t in "$ROOT/_shared/"test_*.py; do
    [ -f "$t" ] || continue
    if ! OUT=$(cd "$ROOT" && python3 "$t" 2>&1); then
      VIOL="${VIOL}
❌ TESTE VERMELHO — ${t#$ROOT/}
$(printf '%s' "$OUT" | tail -15)"
    fi
  done
fi

# E · contrato dos hooks — só o que PIOROU vs o retrato congelado.
# Comparar com o baseline (e não exigir zero) é o que impede a regra de apodrecer:
# os achados que já existiam e foram aceitos não travam ninguém, mas hook novo
# que bloqueia sem teto, sem botão de desligar ou com binário fixo é barrado.
# Só roda quando o commit toca hook — o resto do tempo custa zero.
if printf '%s\n' "$FILES" | grep -qE '^plugins/[^/]+/hooks/'; then
  HC="$ROOT/scripts/hook_contract.py"
  BASE="$ROOT/.claude/hook-contract.baseline.json"
  if [ -f "$HC" ] && [ -f "$BASE" ]; then
    if ! OUT=$(cd "$ROOT" && python3 "$HC" --baseline "$BASE" --fail-on high 2>&1); then
      VIOL="${VIOL}
❌ CONTRATO DE HOOK — achado NOVO de gravidade alta (o que já existia não conta):
$(printf '%s' "$OUT" | sed -n '3,30p')
   → conserte, ou aceite conscientemente e recongele o retrato:
     python3 scripts/hook_contract.py --json > .claude/hook-contract.baseline.json
   → o contrato está em .claude/docs/patterns.md → \"Contrato dos hooks\""
    fi
  fi

  # E2 · orçamento do fim de turno — mesma ideia, outra régua: o que ele mede não é
  # a FORMA do hook, é quanto o conjunto cospe no Stop. Teto absoluto não serve, o
  # total já encostou nos 6 de referência; o que barra é a DERIVA, que é o defeito
  # que originou o teto (cada autor dentro do seu, o conjunto sem dono).
  SB="$ROOT/.claude/stop-budget.baseline.json"
  if [ -f "$HC" ] && [ -f "$SB" ]; then
    if ! OUT=$(cd "$ROOT" && python3 "$HC" --stop-budget --baseline "$SB" 2>&1); then
      VIOL="${VIOL}
❌ FIM DE TURNO ENGORDOU — o Stop passou a cuspir mais que no retrato:
$(printf '%s' "$OUT" | sed -n '/ENGORDOU/,$p')"
    fi
  fi
fi

# G · literal de gen defasado nos MARKERS das skills do project-doc.
# A HARD RULE do bump de gen é um checklist de 5 passos feito à mão, e já falhou: depois
# do bump 3.7→3.8 o nested-pointers.md continuou carimbando gen=3.7, e doc fora do padrão
# faz todo hook do plugin gritar. A própria skill oferecia o grep como "régua mecânica" —
# aqui ela deixa de ser opcional.
# Só olha gen= DENTRO de comentário HTML (é o que vai carimbado na doc gerada). Menção em
# prosa a um gen antigo ("doc `gen=3.6` fica stale") é legítima e NÃO é violação — hoje há
# 4 dessas no repo, e barrá-las ensinaria a ignorar o gate.
if printf '%s\n' "$FILES" | grep -qE '^plugins/project-doc/'; then
  GOUT=$(cd "$ROOT" && python3 - <<'PY' 2>/dev/null
import os, re, sys
pc = "plugins/project-doc/lib/pattern_check.py"
m = re.search(r'^CURRENT_GEN\s*=\s*"([\d.]+)"', open(pc, encoding="utf-8").read(), re.M) \
    if os.path.exists(pc) else None
if not m:
    sys.exit(0)                      # fail-open: sem gen resolvível, não acusa
gen, viol = m.group(1), []
for base, _, arqs in os.walk("plugins/project-doc/skills"):
    for a in arqs:
        p = os.path.join(base, a)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for lineno, linha in enumerate(txt.splitlines(), 1):
            for com in re.findall(r"<!--.*?(?:-->|$)", linha):
                for achado in re.findall(r"gen=(\d+\.\d+)", com):
                    if achado != gen:
                        viol.append("   %s:%d — marker carimba gen=%s (o código está em %s)"
                                    % (p, lineno, achado, gen))
if viol:
    print("\n".join(viol))
PY
)
  if [ -n "$GOUT" ]; then
    VIOL="${VIOL}
❌ GEN DEFASADO NO MARKER — a doc gerada nasceria fora do padrão:
${GOUT}
   → alinhe o literal com CURRENT_GEN de plugins/project-doc/lib/pattern_check.py
   → régua: grep -rn 'gen=[0-9]\+\.[0-9]\+' plugins/project-doc/skills/"
  fi
fi

# H · dado pessoal em arquivo que vai pro repo público.
# Este marketplace é público e instalado por terceiros: nome do dono, caminho da máquina
# dele, nome de cliente ou credencial não podem entrar no índice. Regra em prosa não pega
# (o CLAUDE.md pedia isso e 368 ocorrências entraram assim mesmo) — código pega.
# Só olha o que ESTE commit traz, não o repo inteiro: dívida antiga não trava ninguém,
# mas ocorrência nova é barrada na porta.
PRC="$ROOT/scripts/public_repo_check.py"
if [ -f "$PRC" ]; then
  if ! POUT=$(cd "$ROOT" && python3 "$PRC" --staged 2>&1); then
    VIOL="${VIOL}
❌ DADO PESSOAL NO COMMIT — o repositório é público:
$(printf '%s' "$POUT" | head -20)
   → régua: python3 scripts/public_repo_check.py --staged"
  fi
fi

# I · gerador de página que não passa pela régua de estilo.
# A régua (_shared/regua_texto.py, vinda de quality-goals.md) só vale para o texto
# que passa por ela: gerador novo monta HTML, emite texto autoral e nasce fora da
# regra sem que nada acuse — foi assim que cada gerador inventou a própria forma.
# Só olha o que ESTE commit traz: os 4 geradores que já estavam fora não travam
# ninguém (mesma regra do check H), mas gerador tocado agora é barrado na porta.
RCC="$ROOT/scripts/regua_call_check.py"
if [ -f "$RCC" ]; then
  if ! ROUT=$(cd "$ROOT" && python3 "$RCC" --staged 2>&1); then
    VIOL="${VIOL}
❌ PÁGINA SEM RÉGUA — o arquivo monta HTML e não chama a régua de estilo:
$(printf '%s' "$ROUT" | head -20)
   → régua: python3 scripts/regua_call_check.py --staged"
  fi
fi

# F · suites shell dos plugins tocados (as .py já foram no gate D)
for name in $(printf '%s\n' "$FILES" | sed -n 's#^plugins/\([^/]*\)/.*#\1#p' | sort -u); do
  for t in "$ROOT/plugins/$name/hooks/"test_*.sh; do
    [ -f "$t" ] || continue
    if ! OUT=$(cd "$ROOT" && bash "$t" 2>&1); then
      VIOL="${VIOL}
❌ TESTE VERMELHO — ${t#$ROOT/}
$(printf '%s' "$OUT" | tail -15)"
    fi
  done
done

[ -n "$VIOL" ] || exit 0

cat >&2 <<EOF
🚧 release-gate (pedro-plugins) BLOQUEOU o commit:
${VIOL}

Conserte e commite de novo. (Gate mecânico: .claude/hooks/release-gate.sh)
EOF
exit 2
