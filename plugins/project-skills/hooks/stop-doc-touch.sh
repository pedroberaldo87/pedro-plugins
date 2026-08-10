#!/bin/bash
# stop-doc-touch.sh — sugestão ATIVA do doc-touch no fim da resposta (v3.11).
# Se a sessão editou arquivos cobertos pelo scope de docs project-doc, sugere
# rodar /doc-touch — informativo puro (nunca bloqueia), 1× por (sessão×projeto),
# só com ≥2 arquivos mapeados. Desligável: DOC_TOUCH_SUGGEST=0.
# Fail-open: qualquer erro → exit 0.

[ "${DOC_TOUCH_SUGGEST:-1}" = "0" ] && exit 0
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "stop-doc-touch"; exit 0; }
PY3=$(command -v python3 2>/dev/null)
"$PY3" --version >/dev/null 2>&1 || exit 0
[ -z "$PY3" ] && exit 0

INPUT=$(cat 2>/dev/null)
SESSION=$(hj_campo_ou "$INPUT" session_id unknown)
# Evita loop: Stop disparado por stop_hook já ativo → sai.
ACTIVE=$(hj_campo "$INPUT" stop_hook_active)
[ "$ACTIVE" = "true" ] && exit 0
CWD=$(hj_campo "$INPUT" cwd)
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
# A conta sai do `python3` que este hook já exige, não do `jq`: com `jq`
# obrigatório a sugestão sumia inteira na máquina sem ele (issue #5).
RESUMO=$(printf '%s' "$PLAN" | "$PY3" -c 'import json,sys
try:
    d = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)
docs = d.get("pending_docs")
if not isinstance(docs, list):
    docs = list((d.get("docs") or {}).keys())
arqs = []
for nome in docs:
    for f in ((d.get("docs") or {}).get(nome) or {}).get("files") or []:
        if f not in arqs:
            arqs.append(f)
print(len(docs))
print(len(arqs))
print(", ".join(docs[:5]))' 2>/dev/null)
NDOCS=$(printf '%s\n' "$RESUMO" | sed -n 1p)
NFILES=$(printf '%s\n' "$RESUMO" | sed -n 2p)
case "$NDOCS" in ''|*[!0-9]*) exit 0 ;; esac
case "$NFILES" in ''|*[!0-9]*) exit 0 ;; esac
# Só sugere com sinal razoável: ≥1 doc E ≥2 arquivos mapeados.
[ "$NDOCS" -ge 1 ] || exit 0
[ "$NFILES" -ge 2 ] || exit 0

DOCLIST=$(printf '%s\n' "$RESUMO" | sed -n 3p)

# Cabeçalho com emoji e um bullet por ideia: o canal é terminal puro, e uma linha
# de 177 caracteres com a lista de docs no meio não se lê no fim de um turno.
. "$SCRIPT_DIR/lib-rodada.sh" 2>/dev/null && rodada_doc "$PROJ"
MSG="📝 doc-touch: ${NFILES} arquivo(s) tocados, cobertos por ${NDOCS} doc(s)
• Docs afetadas: ${DOCLIST}
• Rode /${RODADA_CMD:-doc-touch} pra atualizar a doc
• ${RODADA_MOTIVO:-atraso não medido}"

# A régua do canal (perfil `hook`, de quality-goals.md). Defeito de forma não cala uma
# sugestão: o motivo vai pro stderr e o texto sai assim mesmo. Régua ausente → silêncio.
REGUA="$SCRIPT_DIR/../lib/regua_texto.py"
[ -f "$REGUA" ] && printf '%s\n' "$MSG" | "$PY3" "$REGUA" --perfil hook --onde "sugestão de doc-touch" - || :

hj_msg "$MSG"
exit 0
