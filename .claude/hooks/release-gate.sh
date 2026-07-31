#!/usr/bin/env bash
# release-gate.sh — gate mecânico de release do monorepo pedro-plugins.
#
# PreToolUse(Bash): intercepta `git commit` e checa os invariantes que hoje só
# existiam como prosa no CLAUDE.md (vendoring, espelho de versão, bump, testes).
# Zero token, ~50ms. FAIL-OPEN em erro de infra (sem git/python3, fora do repo):
# só bloqueia com evidência concreta na mão.
set -uo pipefail

INPUT=$(cat 2>/dev/null) || exit 0
CMD=$(printf '%s' "$INPUT" | python3 -c \
  'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' 2>/dev/null) || exit 0

# só reage a git commit; `git commit --amend`/`-am` incluídos
printf '%s' "$CMD" | grep -qE '(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*commit' || exit 0

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

# B+C · espelho plugin.json↔marketplace.json e bump esquecido
PYOUT=$(cd "$ROOT" && printf '%s\n' "$FILES" | python3 -c '
import json, subprocess, sys, os, re

files = [l.strip() for l in sys.stdin if l.strip()]
mk = {e["name"]: e.get("version") for e in json.load(open(".claude-plugin/marketplace.json"))["plugins"]}
viol = []

def head_json(path):
    try:
        return json.loads(subprocess.run(["git", "show", "HEAD:" + path],
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

    # B · espelho
    if mk.get(pname) != pver:
        viol.append("❌ ESPELHO QUEBRADO — %s: plugin.json=%s · marketplace.json=%s\n"
                    "   → iguale as duas (o cliente lê a do marketplace)"
                    % (pname, pver, mk.get(pname)))

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
