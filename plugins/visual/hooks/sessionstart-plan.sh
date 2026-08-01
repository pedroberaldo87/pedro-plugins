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

command -v jq >/dev/null 2>&1 || exit 0
PY3=$(command -v python3 2>/dev/null)
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAN_STATE="$SCRIPT_DIR/../lib/plan_state.py"
[ -f "$PLAN_STATE" ] || exit 0

PLANS_DIR=$(bash "$SCRIPT_DIR/../skills/visual/resolve-dir.sh" "$CWD" plans 2>/dev/null)
[ -n "$PLANS_DIR" ] || exit 0

# O marco tem que existir MESMO sem plano aberto: o usuário pode criar o plano no
# meio da sessão, e sem marco o nudge do Stop não teria com o que comparar.
PHASH=$(printf '%s' "$PLANS_DIR" | cksum | cut -d' ' -f1)
touch "${TMPDIR:-/tmp}/claude-plan-mark-$(id -u)-${SESSION}-${PHASH}" 2>/dev/null

SUMMARY=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" open --json 2>/dev/null)
[ -z "$SUMMARY" ] && exit 0
[ "$SUMMARY" = "[]" ] && exit 0

LIST=$(printf '%s' "$SUMMARY" | jq -r '
  .[] | "- **\(.title)** — \(.done)/\(.total) passos" +
        (if .next then " · agora: \(.next.id) \(.next.title)" else "" end) +
        "\n  arquivo: .claude/plans/\(.path)"' 2>/dev/null)
[ -z "$LIST" ] && exit 0

# A cobertura entra aqui porque este hook NÃO passa pelo `brief` — ele monta o
# texto do `open --json`. Sem isto, o número apareceria no fim do turno e não no
# começo da sessão, que é justamente quando o Claude novo decide o que fazer.
# As duas primeiras linhas são o resumo e o aviso de "sem documento de requisitos".
# Vazio (2+ planos ativos, sem plano) → nada; fail-open como o resto do hook.
COB=$("$PY3" "$PLAN_STATE" --dir "$PLANS_DIR" cobertura 2>/dev/null | head -2)
[ -n "$COB" ] && LIST="${LIST}

🔎 Cobertura requisito↔tarefa: ${COB}"

CTX=$(cat <<EOF
📋 Há plano(s) de implementação ABERTO(S) neste projeto:

${LIST}

Este arquivo é a fonte da verdade do plano — NÃO reconstrua o plano de memória e
NÃO renomeie as fases. Antes de continuar o trabalho:

  python3 \${CLAUDE_PLUGIN_ROOT}/lib/plan_state.py render --format text

Ao concluir um passo, marque com a prova junto (o tique é recusado sem ela):

  python3 \${CLAUDE_PLUGIN_ROOT}/lib/plan_state.py tick F2.3 --evidencia "<comando · saída · sha>"

Terminou tudo? \`plan_state.py close\`. Página de acompanhamento: \`plan_state.py page --mode track\`.
EOF
)

jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}' 2>/dev/null
exit 0
