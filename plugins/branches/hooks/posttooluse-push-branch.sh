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
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "posttooluse-push-branch"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
"$PY3" --version >/dev/null 2>&1 || exit 0
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
CMD=$(hj_campo "$INPUT" tool_input.command)
printf '%s' "$CMD" | grep -qE '(^|[;&|]|&&)[[:space:]]*git[[:space:]]+.*\bpush\b' || exit 0

# Push que falhou não fecha ciclo nenhum. O campo varia por versão do harness,
# então a ausência dele é tratada como "deu certo" (fail-open na direção calada).
# ⚠️ NÃO usar `.a // .b // "true"` aqui: no jq o `//` devolve o lado direito
# quando o esquerdo é null OU **false**, então success:false virava "true" e o
# hook perguntava depois de um push que falhou. Comparação explícita.
hj_eh_falso "$INPUT" tool_response.success && exit 0
hj_eh_falso "$INPUT" tool_result.success && exit 0

SESSION=$(hj_campo_ou "$INPUT" session_id unknown)
CWD=$(hj_campo "$INPUT" cwd)
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
# A varredura é no `python3` que este hook já exige, não no `jq`: em máquina sem
# `jq` o aviso de branch sumia inteiro (issue #5).
LINHA=$(printf '%s' "$INFO" | "$PY3" -c 'import json,sys
try:
    d = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)
b = sys.argv[1]
if d.get("base") != b:
    for x in d.get("branches") or []:
        if x.get("name") == b:
            print("%s\t%s\t%s" % (x.get("category"), x.get("ahead"), x.get("behind")))
            break' "$BRANCH" 2>/dev/null)
# Vazio = estamos no tronco, ou a branch sumiu da listagem. Nos dois casos, cala.
[ -n "$LINHA" ] || exit 0

CAT=$(printf '%s' "$LINHA" | cut -f1)
AHEAD=$(printf '%s' "$LINHA" | cut -f2)
BASE=$(hj_campo "$INFO" base)

# Branch cujo conteúdo JÁ está no tronco não precisa de pergunta — precisa de
# faxina, e disso o /branches cuida. Aqui só interessa a que ainda tem trabalho.
[ "$CAT" = "unique" ] || exit 0

PHASH=$(printf '%s' "$ROOT" | cksum | cut -d' ' -f1)
BHASH=$(printf '%s' "$BRANCH" | cksum | cut -d' ' -f1)
SENTINEL="${TMPDIR:-/tmp}/claude-branch-ask-$(id -u)-${SESSION}-${PHASH}-${BHASH}"
[ -f "$SENTINEL" ] && exit 0
touch "$SENTINEL" 2>/dev/null
find "${TMPDIR:-/tmp}" -maxdepth 1 -name "claude-branch-ask-$(id -u)-*" -mtime +1 -delete 2>/dev/null

# Cabeçalho com emoji e um bullet por ideia, porque o canal é texto puro: `**` chega
# literal na tela, e linha de 300 caracteres vira parágrafo no meio do terminal.
MSG="🌿 Push feito em ${BRANCH} — ${AHEAD} commit(s) à frente de ${BASE}
• O conteúdo ainda não está no ${BASE}, e você lembra AGORA do que esta branch é.
• Merge no ${BASE} agora, ou ela fica aberta de propósito?
• Branch esquecida vira as 15 que reclamam no deploy — /branches lista as que já dá pra apagar.
• Desligar: BRANCHES_GATE=0"

# A régua do canal (perfil `hook`, de quality-goals.md). Defeito de forma não cala um
# aviso: o motivo vai pro stderr (debug log do harness) e o texto sai assim mesmo.
# Régua ausente → silêncio, nunca queda — mesmo fail-open do resto do arquivo.
REGUA="$SCRIPT_DIR/../lib/regua_texto.py"
[ -f "$REGUA" ] && printf '%s\n' "$MSG" | "$PY3" "$REGUA" --perfil hook --onde "push de branch" - || :

hj_msg "$MSG"
exit 0
