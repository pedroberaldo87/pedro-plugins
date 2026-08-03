#!/bin/bash
# stop-doc-touch.sh — sugestão ATIVA do doc-touch no fim da resposta (v3.11).
# Se a sessão editou arquivos cobertos pelo scope de docs project-doc, sugere
# rodar /doc-touch — informativo puro (nunca bloqueia), 1× por (sessão×projeto),
# só com ≥2 arquivos mapeados. Desligável: DOC_TOUCH_SUGGEST=0.
# Fail-open: qualquer erro → exit 0.

[ "${DOC_TOUCH_SUGGEST:-1}" = "0" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
PY3=$(command -v python3 2>/dev/null)
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
# Evita loop: Stop disparado por stop_hook já ativo → sai.
ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$ACTIVE" = "true" ] && exit 0
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

# Projeto = git root com doc project-doc (sobe do cwd).
PROJ="$CWD"
while [ -n "$PROJ" ] && [ "$PROJ" != "/" ]; do
  [ -d "$PROJ/.claude/docs" ] && break
  PROJ=$(dirname "$PROJ")
done
[ -d "$PROJ/.claude/docs" ] || exit 0

# Throttle: 1 sugestão por (sessão×projeto).
PHASH=$(printf '%s' "$PROJ" | cksum | cut -d' ' -f1)
SENTINEL="${TMPDIR:-/tmp}/claude-doc-touch-$(id -u)-${SESSION}-${PHASH}"
[ -f "$SENTINEL" ] && exit 0
# Marca ANTES dos gates: o caso comum é "nada a sugerir", e sem marcar aqui o
# hook re-executava o touch-plan (git diff + enumeração de docs) ao fim de CADA
# resposta da sessão. TMPDIR+uid evitam colisão de sentinel entre usuários.
touch "$SENTINEL" 2>/dev/null

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PC="$SCRIPT_DIR/../lib/pattern_check.py"
[ -f "$PC" ] || exit 0

PLAN=$("$PY3" "$PC" --project-root "$PROJ" --touch-plan --json 2>/dev/null)
[ -z "$PLAN" ] && exit 0
# pending_docs = os que AINDA precisam de touch (exclui os já atualizados nesta
# sessão). Sem isso o hook re-sugere depois de um touch bem-sucedido, porque o
# git diff segue mostrando os arquivos enquanto o trabalho não é commitado.
NDOCS=$(printf '%s' "$PLAN" | jq -r '(.pending_docs // (.docs|keys)) | length' 2>/dev/null)
NFILES=$(printf '%s' "$PLAN" | jq -r '[(.pending_docs // (.docs|keys))[] as $d | .docs[$d].files[]] | unique | length' 2>/dev/null)
case "$NDOCS" in ''|*[!0-9]*) exit 0 ;; esac
case "$NFILES" in ''|*[!0-9]*) exit 0 ;; esac
# Só sugere com sinal razoável: ≥1 doc E ≥2 arquivos mapeados.
[ "$NDOCS" -ge 1 ] || exit 0
[ "$NFILES" -ge 2 ] || exit 0

DOCLIST=$(printf '%s' "$PLAN" | jq -r '(.pending_docs // (.docs|keys)) | .[:5] | join(", ")' 2>/dev/null)

# Cabeçalho com emoji e um bullet por ideia: o canal é terminal puro, e uma linha
# de 177 caracteres com a lista de docs no meio não se lê no fim de um turno.
MSG="📝 doc-touch: ${NFILES} arquivo(s) tocados, cobertos por ${NDOCS} doc(s)
• Docs afetadas: ${DOCLIST}
• Rode /doc-touch pra atualizar a doc incrementalmente, sem re-mineração."

# A régua do canal (perfil `hook`, de quality-goals.md). Defeito de forma não cala uma
# sugestão: o motivo vai pro stderr e o texto sai assim mesmo. Régua ausente → silêncio.
REGUA="$SCRIPT_DIR/../lib/regua_texto.py"
[ -f "$REGUA" ] && printf '%s\n' "$MSG" | "$PY3" "$REGUA" --perfil hook --onde "sugestão de doc-touch" - || :

jq -n --arg m "$MSG" '{systemMessage:$m}' 2>/dev/null
exit 0
