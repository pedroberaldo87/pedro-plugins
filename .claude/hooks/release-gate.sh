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

# K · número de contagem afirmado no README contra o repositório.
# O README é a vitrine e afirma quantidade (quantos plugins, quantos ligados de fábrica,
# quantos hooks pedem jq, quantos plugins registram hook e quantos registros dão). Nada
# conferia isso: quando este check nasceu, as CINCO afirmações estavam defasadas de uma
# vez (19→21, 17→19, 46→68, 10→12, 34→54), porque plugin novo entra e a prosa fica.
# Escopo: só quando o commit mexe no README ou numa das fontes que alimentam esses números.
RCT="$ROOT/scripts/readme_counts_check.py"
if [ -f "$RCT" ] && printf '%s\n' "$FILES" | grep -qE '^(README\.md$|\.claude-plugin/marketplace\.json$|plugins/bootstrap/config/manifest\.json$|plugins/[^/]+/hooks/)'; then
  if ! KOUT=$(cd "$ROOT" && python3 "$RCT" 2>&1); then
    VIOL="${VIOL}
❌ README DEFASADO — número afirmado na vitrine não bate com o repositório:
$(printf '%s' "$KOUT" | head -30)
   → régua: python3 scripts/readme_counts_check.py"
  fi
fi

# L · função nova que caminho nenhum do produto invoca.
# Nasceu de defeito medido: de quatro passos reprovados numa rodada, TRÊS tinham código
# bom — bem escrito, com teste próprio — que nenhum lugar da árvore chamava. Peça que não
# roda não prova critério nenhum, e como ela nunca é executada, nenhuma suíte fica vermelha
# por causa dela: sem este check o defeito só aparece na revisão humana.
# Só o eixo sem-chamador entra aqui (--motivo): os motivos sonda e nao-declarado acusam
# arquivo não rastreado, e trabalho em andamento de outra pessoa travaria este commit.
# Escopo: só quando o commit traz .py — é onde o fiscal lê as funções (AST).
FDB="$ROOT/scripts/fiscal_de_bancada.py"
if [ -f "$FDB" ] && printf '%s\n' "$FILES" | grep -qE '\.py$'; then
  if ! LOUT=$(cd "$ROOT" && python3 "$FDB" --motivo sem-chamador "$ROOT" 2>&1); then
    VIOL="${VIOL}
❌ PEÇA SEM CHAMADOR — função nova que nenhum arquivo da árvore invoca:
$(printf '%s' "$LOUT" | head -20)
   → ligue no caminho real (quem chama), ou apague.
   → régua: python3 scripts/fiscal_de_bancada.py --motivo sem-chamador"
  fi
fi

# M · aviso que só existe no canal que todo consumidor joga fora.
# Nasceu do mesmo defeito medido que o L: a recusa da reserva de arquivos era escrita no
# canal de erro, e TODO caminho que chamava o script fechava a chamada com `2>/dev/null`.
# O aviso existia no código, tinha teste, e não chegava a ninguém — e como ele nunca é
# lido, nada fica vermelho por causa dele. Aviso em canal descartado é aviso que não existe.
# Escopo: só quando o commit traz .py ou .sh — é onde o fiscal procura a escrita no canal.
if [ -f "$FDB" ] && printf '%s\n' "$FILES" | grep -qE '\.(py|sh|bash)$'; then
  if ! MOUT=$(cd "$ROOT" && python3 "$FDB" --motivo aviso-no-vazio "$ROOT" 2>&1); then
    VIOL="${VIOL}
❌ AVISO NO VAZIO — aviso escrito no canal que todos os consumidores descartam:
$(printf '%s' "$MOUT" | head -20)
   → escreva o aviso no canal que quem chama LÊ, ou tire o 2>/dev/null de quem chama.
   → régua: python3 scripts/fiscal_de_bancada.py --motivo aviso-no-vazio"
  fi
fi

# N · acoplamento novo entre plugins (Artigo 9: nada amarra o NOME nem a QUANTIDADE).
# Plugin que aponta para o irmão por posição (a raiz do plugin mais `/../<irmão>`) ou que manda
# rodar arquivo de outro plugin quebra na máquina de quem instalou — o cache do harness
# instala cada plugin em pasta própria. Contagem cravada em prosa envelhece sem avisar.
# Diferente do H, este cobrador não tem --staged: ele varre todo arquivo rastreado e só sai 1
# quando aparece achado FORA de .claude/desacoplamento.baseline.json — dívida antiga passa,
# acoplamento novo reprova.
# Escopo: só quando o commit traz um dos formatos que ele lê.
DSC="$ROOT/scripts/desacoplamento_check.py"
if [ -f "$DSC" ] && printf '%s\n' "$FILES" | grep -qE '\.(md|sh|py|json|yml)$'; then
  if ! NOUT=$(cd "$ROOT" && python3 "$DSC" 2>&1); then
    VIOL="${VIOL}
❌ ACOPLAMENTO NOVO — o arquivo amarra o nome de outro plugin ou crava uma contagem:
$(printf '%s' "$NOUT" | head -20)
   → régua: python3 scripts/desacoplamento_check.py"
  fi
fi

# P · disparo de processo que pode deixar filho para trás.
# Em 2026-08-08 uma máquina acumulou 2125 `python3` órfãos: 155 pontos do repositório
# disparavam processo sem fechar stdin (o filho herda o terminal e espera para sempre) e
# sem grupo próprio (o timeout mata o filho e o NETO sobrevive). Um ciclo entre dois
# scripts transformou o vazamento em bomba de forks. O conserto foi mecânico e o risco de
# regressão também é: basta alguém escrever `subprocess.run(...)` do jeito antigo.
# Escopo: só quando o commit traz Python.
VZC="$ROOT/scripts/vazamento_check.py"
if [ -f "$VZC" ] && printf '%s\n' "$FILES" | grep -qE '\.py$'; then
  if ! POUT=$(cd "$ROOT" && python3 "$VZC" 2>&1); then
    VIOL="${VIOL}
❌ VAZAMENTO DE PROCESSO — o disparo pode deixar filho rodando depois de terminar:
$(printf '%s' "$POUT" | head -20)
   → régua: python3 scripts/vazamento_check.py"
  fi
fi

# Q · cópia de trabalho parada no disco, que vira caminho de execução silencioso.
# Em 2026-08-08, 14 de 41 marcações do motor rodaram binário que não era o da árvore:
# os agentes procuraram o arquivo pelo NOME e o `find` alcançou as cópias em
# .claude/worktrees/. Sete passaram por um validador 548 linhas mais velho, SEM as
# funções de recusa. As cópias nasceram antes de a regra proibi-las — a regra proibiu
# criar novas e não varreu as velhas.
# SEM RECORTE por arquivo tocado: a cópia não aparece no diff de commit nenhum.
WOC="$ROOT/scripts/worktree_orfao_check.py"
if [ -f "$WOC" ]; then
  if ! QOUT=$(cd "$ROOT" && python3 "$WOC" 2>&1); then
    VIOL="${VIOL}
❌ CÓPIA DE TRABALHO PARADA — quem busca arquivo pelo nome acha ela antes do original:
$(printf '%s' "$QOUT" | head -12)
   → régua: python3 scripts/worktree_orfao_check.py"
  fi
fi

# R · description que só serve a quem já sabe que a skill existe.
# Apelido (`"/faxina"`, `"sovai"`) é achado por quem lembra do nome. Quem NÃO lembra que a
# skill existe só é atendido se a description disser em que SITUAÇÃO DE TRABALHO ela entra
# — o molde é a de `sprint`, `Use quando o usuário disser …`. Quantas skills do marketplace
# ainda são só lista de gatilho se descobre com o próprio comando abaixo, nunca de memória:
#   python3 plugins/check-skills/lib/varredura.py --situacao-repo .
# Escopo: só quando o commit traz um SKILL.md.
VAR="$ROOT/plugins/check-skills/lib/varredura.py"
if [ -f "$VAR" ] && printf '%s\n' "$FILES" | grep -qE '/SKILL\.md$'; then
  if ! ROUT2=$(cd "$ROOT" && python3 "$VAR" --situacao-repo "$ROOT" 2>&1); then
    VIOL="${VIOL}
❌ SKILL SEM SITUAÇÃO — a description não diz em que momento de trabalho a skill entra:
$(printf '%s' "$ROUT2" | head -20)
   → escreva uma frase de situação (molde: plugins/project-skills/skills/sprint/SKILL.md)
   → régua: python3 plugins/check-skills/lib/varredura.py --situacao-repo ."
  fi
fi

# O · plano e código discordando: passo ABERTO cujo critério de pronto já se cumpre.
# Os quatro irmãos deste cobrador (H, I, L, M, N) já estavam aqui e este não — ele rodava
# e acusava sem que portão nenhum o consultasse. Passo que fica "todo" depois de o trabalho
# ter entrado no código faz a sessão seguinte refazer tudo do zero, e é o commit o momento
# em que o código muda: é aqui que a discordância nasce.
# SEM RECORTE por arquivo tocado, de propósito: `.claude/plans/` é ignorado pelo git
# (registro de trabalho não é produto), então plano nenhum aparece em $FILES — recortar
# por ele deixaria o check calado para sempre. Custo medido em 2026-08-07: ~0,6s.
PVC="$ROOT/scripts/plano_vs_codigo.py"
if [ -f "$PVC" ]; then
  if ! OOUT=$(cd "$ROOT" && python3 "$PVC" 2>&1); then
    VIOL="${VIOL}
❌ PLANO ATRASADO — passo aberto cujo critério de pronto o disco já cumpre:
$(printf '%s' "$OOUT" | head -20)
   → tique o passo com a prova (plan_state.py tick), ou conserte o critério.
   → régua: python3 scripts/plano_vs_codigo.py"
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

# J · as suítes que nenhum glob de plugin casa: as de scripts/ e as .py dentro de hooks/.
# Os checks D, D2 e F varrem plugins/<n>/lib/*.py, _shared/*.py e plugins/<n>/hooks/*.sh —
# `grep -n 'scripts/test_' .claude/hooks/release-gate.sh` não devolvia nada, e as suítes de
# portabilidade (Artigo 3 da constituição) tinham medidor sem cobrador no commit.
# Mesmo gerador do .github/workflows/portability.yml, com a MESMA asserção de quantidade:
# glob que deixou de casar arquivo não pode ficar verde sem rodar nada (Artigo 5).
# Escopo: só quando o commit toca hook, script ou .gitattributes. Medido em 2026-08-06, o
# bloco leva ~100s (80s são de scripts/test_bootstrap_aviso.sh) — em todo commit seria
# proibitivo, e é exatamente esse o recorte que o Artigo 3 pede.
if printf '%s\n' "$FILES" | grep -qE '^(scripts/|plugins/[^/]+/hooks/|\.claude/hooks/|\.gitattributes$)'; then
  roda_suites() {
    runner="$1"; shift
    for pat in "$@"; do
      n=0
      for t in "$ROOT"/$pat; do
        [ -f "$t" ] || continue
        n=$((n + 1))
        if ! OUT=$(cd "$ROOT" && "$runner" "$t" 2>&1); then
          VIOL="${VIOL}
❌ TESTE VERMELHO — ${t#$ROOT/}
$(printf '%s' "$OUT" | tail -15)"
        fi
      done
      [ "$n" -gt 0 ] && continue
      VIOL="${VIOL}
❌ GLOB VAZIO — nenhum arquivo casou em ${pat}
   → suíte renomeada ou apagada deixaria o gate verde sem rodar nada.
     Conserte o padrão no check J de .claude/hooks/release-gate.sh"
    done
  }
  roda_suites python3 'plugins/*/hooks/test_*.py'
  roda_suites bash    'scripts/test_*.sh'
  # `lib/test_*.sh` é o tipo que nenhum dos dois globs de plugin casava: o D varre
  # `lib/test_*.py` e o F varre `hooks/test_*.sh`. Suíte shell dentro de `lib/` caía
  # no vão entre eles — foi o que aconteceu com a do resolvedor de skill, que o
  # `suites_orfas.py` acusou como órfã no dia em que nasceu.
  roda_suites bash    'plugins/*/lib/test_*.sh'
fi

[ -n "$VIOL" ] || exit 0

cat >&2 <<EOF
🚧 release-gate (pedro-plugins) BLOQUEOU o commit:
${VIOL}

Conserte e commite de novo. (Gate mecânico: .claude/hooks/release-gate.sh)
EOF
exit 2
