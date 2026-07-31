#!/bin/bash
# posttooluse-push-branch.sh — a pergunta no momento em que você ainda lembra.
#
# Dispara depois de um `git push` bem-sucedido numa branch que NÃO é o tronco.
# É o instante em que a branch acabou de entregar e você ainda sabe o que ela
# era — meses depois, olhando uma lista de 15 nomes, ninguém sabe.
#
# A pilha de branches não se forma por preguiça: se forma porque merge não é o
# último passo do ciclo. Este hook põe a pergunta no ciclo.
#
# CONTRATO DE GATE (.claude/docs/patterns.md → §5.3):
#   canal      systemMessage — INFORMA, nunca bloqueia
#   cap        1 pergunta por (branch, sessão) — perguntar a cada push é ruído
#   desligar   BRANCHES_GATE=0
#   fail-open  sem jq, sem python3, fora de repo, push que falhou → exit 0 calado

[ "${BRANCHES_GATE:-1}" = "0" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
PY3=$(command -v python3 2>/dev/null)
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
printf '%s' "$CMD" | grep -qE '(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*\bpush\b' || exit 0

# Push que falhou não fecha ciclo nenhum. O campo varia por versão do harness,
# então a ausência dele é tratada como "deu certo" (fail-open na direção calada).
# ⚠️ NÃO usar `.a // .b // "true"` aqui: no jq o `//` devolve o lado direito
# quando o esquerdo é null OU **false**, então success:false virava "true" e o
# hook perguntava depois de um push que falhou. Comparação explícita.
FALHOU=$(printf '%s' "$INPUT" | jq -r '
  if (.tool_response.success == false) or (.tool_result.success == false)
  then "sim" else "nao" end' 2>/dev/null)
[ "$FALHOU" = "sim" ] && exit 0

SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BS="$SCRIPT_DIR/../lib/branch_state.py"
[ -f "$BS" ] || exit 0

ROOT=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$ROOT" ] || exit 0
BRANCH=$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)
[ -n "$BRANCH" ] && [ "$BRANCH" != "HEAD" ] || exit 0

# Estado da branch atual, pela mesma medida do /branches.
INFO=$("$PY3" "$BS" --repo "$ROOT" list --json 2>/dev/null) || exit 0
[ -n "$INFO" ] || exit 0
LINHA=$(printf '%s' "$INFO" | jq -r --arg b "$BRANCH" '
  if .base == $b then empty
  else (.branches[]? | select(.name == $b)
        | "\(.category)\t\(.ahead)\t\(.behind)") end' 2>/dev/null)
# Vazio = estamos no tronco, ou a branch sumiu da listagem. Nos dois casos, cala.
[ -n "$LINHA" ] || exit 0

CAT=$(printf '%s' "$LINHA" | cut -f1)
AHEAD=$(printf '%s' "$LINHA" | cut -f2)
BASE=$(printf '%s' "$INFO" | jq -r '.base' 2>/dev/null)

# Branch cujo conteúdo JÁ está no tronco não precisa de pergunta — precisa de
# faxina, e disso o /branches cuida. Aqui só interessa a que ainda tem trabalho.
[ "$CAT" = "unique" ] || exit 0

PHASH=$(printf '%s' "$ROOT" | cksum | cut -d' ' -f1)
BHASH=$(printf '%s' "$BRANCH" | cksum | cut -d' ' -f1)
SENTINEL="${TMPDIR:-/tmp}/claude-branch-ask-$(id -u)-${SESSION}-${PHASH}-${BHASH}"
[ -f "$SENTINEL" ] && exit 0
touch "$SENTINEL" 2>/dev/null
find "${TMPDIR:-/tmp}" -maxdepth 1 -name "claude-branch-ask-$(id -u)-*" -mtime +1 -delete 2>/dev/null

MSG="🌿 **Push feito em \`${BRANCH}\`** — ${AHEAD} commit(s) à frente de \`${BASE}\`, e o conteúdo ainda não está lá. Enquanto você lembra do que esta branch é: **merge no ${BASE} agora**, ou ela fica aberta de propósito? (branch esquecida vira as 15 que reclamam no deploy · \`/branches\` lista as que já dá pra apagar · desligar: \`BRANCHES_GATE=0\`)"

jq -n --arg m "$MSG" '{systemMessage:$m}' 2>/dev/null
exit 0
