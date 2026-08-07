#!/bin/bash
# sessionstart-plan.sh — ressuscita o plano aberto no começo da sessão.
#
# O plano vive em <raiz>/.claude/plans/<id>.plan.json (ver lib/plan_state.py).
# Depois de um /clear ou de um handoff, a conversa some mas o arquivo fica —
# este hook é o que faz o Claude novo SABER que ele existe, em vez de reconstruir
# o plano de cabeça (que é como fase muda de nome e plano é dado como concluído
# sem estar).
#
# Também deixa o MARCO da sessão em TMPDIR: o stop-plan-nudge.sh compara o mtime
# do arquivo do plano com ele pra saber se alguma fase foi marcada NESTA sessão.
#
# Fail-open: qualquer erro → exit 0, sem saída.

# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "sessionstart-plan"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
"$PY3" --version >/dev/null 2>&1 || exit 0
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
SESSION=$(hj_campo_ou "$INPUT" session_id unknown)
CWD=$(hj_campo "$INPUT" cwd)
[ -z "$CWD" ] && CWD="$PWD"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAN_STATE="$SCRIPT_DIR/../lib/plan_state.py"
[ -f "$PLAN_STATE" ] || exit 0

# O `$?` do resolve-dir é o aviso: 3 = o diretório veio da RESERVA (~/Desktop),
# não deste projeto. O stderr dele morre no 2>/dev/null desta mesma linha, então
# sem ler o código o plano de fora entraria no contexto sem nenhuma ressalva.
PLANS_DIR=$(bash "$SCRIPT_DIR/../skills/visual/resolve-dir.sh" "$CWD" plans 2>/dev/null); DE_RESERVA=$?
[ -n "$PLANS_DIR" ] || exit 0

# O marco tem que existir MESMO sem plano aberto: o usuário pode criar o plano no
# meio da sessão, e sem marco o nudge do Stop não teria com o que comparar.
PHASH=$(printf '%s' "$PLANS_DIR" | cksum | cut -d' ' -f1)
touch "${TMPDIR:-/tmp}/claude-plan-mark-$(id -u)-${SESSION}-${PHASH}" 2>/dev/null

# FILA DE ENTRADA — passo que ficou esperando o motor soltar o arquivo do plano.
# Enquanto um motor roda, ele ESCREVE no .plan.json (marca o que fechou); editar o
# mesmo arquivo por baixo dele é a corrida clássica, e a saída foi enfileirar em
# .claude/plans/entrada/. Só que "incorporo depois" é promessa, e promessa não é
# mecanismo: sessão que cai deixa o passo no disco e ninguém o lê. Aqui a promessa
# vira comando, no único instante em que ela é segura.
#
# ⚠️ NÃO drena com motor vivo — nem desta sessão, nem de OUTRA. O sinal `ativo-<sid>`
# do /sovai é o que denuncia isso, e ele é por sessão: basta UM aceso para adiar.
# Drenar no meio de uma execução seria reintroduzir a corrida que a fila evita.
ENTRADA="$PLANS_DIR/entrada"
if [ -d "$ENTRADA" ] && [ -n "$(ls "$ENTRADA"/*.json 2>/dev/null)" ]; then
  SOVAI_ESTADO="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"
  MOTOR_VIVO=$(ls "$SOVAI_ESTADO"/ativo-* 2>/dev/null | head -1)
  ENTRADA_PY="$SCRIPT_DIR/../lib/plan_entrada.py"
  if [ -n "$MOTOR_VIVO" ]; then
    printf '📥 há passo(s) na fila de entrada do plano, e um motor está vivo — adiado.\n' >&2
  elif [ -f "$ENTRADA_PY" ]; then
    DRENO=$("$PY3" "$ENTRADA_PY" --dir "$PLANS_DIR" 2>&1)
    printf '%s\n' "$DRENO" >&2
  fi
fi

SUMMARY=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" open --json 2>/dev/null)
[ -z "$SUMMARY" ] && exit 0
[ "$SUMMARY" = "[]" ] && exit 0

# A lista sai do `python3` que este hook já exige, não do `jq`: com `jq`
# obrigatório o plano aberto não ressuscitava na máquina sem ele (issue #5).
LIST=$(printf '%s' "$SUMMARY" | "$PY3" -c 'import json,sys
try:
    planos = json.loads(sys.stdin.read() or "[]")
except Exception:
    sys.exit(0)
for p in planos:
    linha = "- **%s** — %s/%s passos" % (p.get("title"), p.get("done"), p.get("total"))
    n = p.get("next")
    if n:
        linha += " · agora: %s %s" % (n.get("id"), n.get("title"))
    print(linha + "\n  arquivo: .claude/plans/%s" % p.get("path"))' 2>/dev/null)
[ -z "$LIST" ] && exit 0

# A cobertura entra aqui porque este hook NÃO passa pelo `brief` — ele monta o
# texto do `open --json`. Sem isto, o número apareceria no fim do turno e não no
# começo da sessão, que é justamente quando o Claude novo decide o que fazer.
# As duas primeiras linhas são o resumo e o aviso de "sem documento de requisitos".
# Vazio (2+ planos ativos, sem plano) → nada; fail-open como o resto do hook.
COB=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" cobertura 2>/dev/null | head -2)
[ -n "$COB" ] && LIST="${LIST}

🔎 Cobertura requisito↔tarefa: ${COB}"

# O aviso da reserva entra no MESMO texto que o modelo lê — canal que ninguém
# descarta. Sem ele, "neste projeto" seria mentira: o plano veio do Desktop.
RESERVA_AVISO=""
[ "$DE_RESERVA" = "3" ] && RESERVA_AVISO="⚠️ Este plano NÃO veio deste projeto: '$CWD' não tem marcador de projeto, então ele saiu da RESERVA em $PLANS_DIR. Confirme com o usuário antes de tratá-lo como o plano daqui.

"

CTX=$(cat <<EOF
${RESERVA_AVISO}📋 Há plano(s) de implementação ABERTO(S) neste projeto:

${LIST}

Este arquivo é a fonte da verdade do plano — NÃO reconstrua o plano de memória e
NÃO renomeie as fases. Antes de continuar o trabalho:

  python3 \${CLAUDE_PLUGIN_ROOT}/lib/plan_state.py render --format text

Ao concluir um passo, marque com a prova junto (o tique é recusado sem ela):

  python3 \${CLAUDE_PLUGIN_ROOT}/lib/plan_state.py tick F2.3 --evidencia "<comando · saída · sha>"

Terminou tudo? \`plan_state.py close\`. Página de acompanhamento: \`plan_state.py page --mode track\`.
EOF
)

hj_ctx SessionStart "$CTX"
exit 0
