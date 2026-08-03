#!/bin/bash
# pretooluse-graphify-guard.sh — safety net.
# When a blind search (Grep/Glob, or Bash running grep|rg|find|...) is about to run in a project
# that has a graphify graph, DENY it once per session and redirect to `graphify query`.
# Covers the monorepo-container case: even when cwd is a container (e.g. /VIU) with no graph of its
# own, it inspects the search path tokens and descends to find graphs in subprojects.
# Fail-open: any error → exit 0 (search proceeds).

# Kill-switch (2026-07-27, contrato dos hooks): quando este gate atrapalha
# num momento ruim, a saída não pode ser editar o script.
[ "${GRAPHIFY_GATE:-1}" = "0" ] && exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CWD" ] && CWD="$PWD"

# Build the list of candidate dirs that this search might touch. Always include CWD; add the
# explicit search path (Grep/Glob) or any path-like token from the command (Bash).
CANDS="$CWD"
case "$TOOL" in
  Grep|Glob)
    P=$(printf '%s' "$INPUT" | jq -r '.tool_input.path // empty' 2>/dev/null)
    [ -n "$P" ] && CANDS="$CANDS
$P"
    ;;
  Bash)
    CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
    # only intercept blind text/file search; everything else (incl. `graphify ...`) passes
    printf '%s' "$CMD" | grep -Eq '(^|[^[:alnum:]_])(grep|egrep|fgrep|rg|ripgrep|ag|ack|find)([^[:alnum:]_]|$)' || exit 0
    # add command tokens that exist as paths, so `grep -r x subprojeto/` fires from the parent dir
    for tok in $CMD; do
      case "$tok" in -*) continue ;; esac
      cand="$tok"; case "$cand" in /*) : ;; *) cand="$CWD/$tok" ;; esac
      [ -e "$cand" ] && CANDS="$CANDS
$cand"
    done
    ;;
  *)
    exit 0
    ;;
esac

# Once-per-session: if we've already nudged, let everything through.
SENTINEL="/tmp/claude-graphify-guard-${SESSION}"
[ -f "$SENTINEL" ] && exit 0

# Poda: sessão morre e o sentinel fica. Mesma janela e mesma forma do irmão
# (guardrails/hooks/scope-cop.sh). Restrita ao PRÓPRIO padrão de nome — nunca
# glob amplo em /tmp. Gatilho: roda em toda busca interceptada até que um nudge seja
# emitido — quem corta é o sentinel da linha acima, e ele só nasce quando o hook de
# fato avisa. Num projeto sem grafo o nudge nunca acontece (o exit do PROJ vazio sai
# sem queimar o sentinel), então aqui é a sessão inteira, uma passada por busca cega.
# Custo medido em 2026-07-30: ~6ms por chamada com ~1500 entradas em /tmp — aceito.
# A barra final em "/tmp/" é obrigatória: no macOS /tmp é symlink pra private/tmp e
# o find físico (-P, o default) não desce por um symlink dado como ponto de partida —
# sem a barra ele casa zero arquivo e a poda vira no-op silencioso.
find /tmp/ -maxdepth 1 -name 'claude-graphify-guard-*' -mtime +1 -delete 2>/dev/null

# Nearest ancestor of a dir that owns a graph (cheap: stat while walking up).
find_graph_up() {
  local d="$1"
  case "$d" in /*) : ;; *) d="$CWD/$d" ;; esac
  while [ -n "$d" ] && [ "$d" != "/" ]; do
    [ -f "$d/graphify-out/graph.json" ] && { printf '%s' "$d"; return 0; }
    d=$(dirname "$d")
  done
  return 1
}

# 1) check each candidate by walking up
PROJ=""
while IFS= read -r c; do
  [ -z "$c" ] && continue
  p=$(find_graph_up "$c") && { PROJ="$p"; break; }
done <<EOF
$CANDS
EOF

# 2) container fallback: descend from CWD to catch graphs living in subprojects
if [ -z "$PROJ" ]; then
  LINE0=$(bash "$SCRIPT_DIR/graphify-detect.sh" "$CWD" 2>/dev/null | head -1)
  [ -n "$LINE0" ] && PROJ=$(printf '%s' "$LINE0" | cut -f2)
fi

# No graph covers this search → let it through WITHOUT burning the sentinel.
[ -z "$PROJ" ] && exit 0

LINE=$(bash "$SCRIPT_DIR/graphify-detect.sh" --one "$PROJ" 2>/dev/null)
[ -z "$LINE" ] && exit 0

STATE=$(printf '%s' "$LINE" | cut -f3)
N=$(printf '%s' "$LINE" | cut -f4)
DATE=$(printf '%s' "$LINE" | cut -f5)

# We're about to nudge — mark it so the rest of the session is silent.
touch "$SENTINEL" 2>/dev/null

# A crase saiu do texto e o caminho do projeto ganhou linha própria: o canal é terminal
# puro (o `graphify --update` chegava com as crases na tela), e o caminho colado num
# cabeçalho estoura sozinho o teto de 140 caracteres da régua deste canal.
STALE=""
if [ "$STATE" = "stale" ]; then
  STALE="
• ⚠️ Grafo defasado: ${N} arquivo(s) desde ${DATE} — ofereça graphify --update antes de confiar nele."
fi
COMANDOS="• graphify query \"o que você procura\" — ou graphify explain \"Nó\" / graphify path \"A\" \"B\""

# Dois textos porque os dois ramos enquadram situações diferentes: no deny ESTE hook
# barrou a busca (cabe "refaça"). No aviso ele não barrou — mas também não pode afirmar
# que a busca rodou nem prometer resultado: PreToolUse fala ANTES da ferramenta, e outro
# gate pode negar a mesma chamada (medido: o project-doc nega esta mesma primeira busca
# da sessão, com matcher mais largo). O aviso fica só no que é verdade no instante em que
# ele fala: a busca é cega, há grafo em ${PROJ}, confirme lá antes de concluir. Sem
# consultar o vizinho — espaço infinito, e o hook não precisa saber quem mais opinou.
MSG_DENY="🕸️ Busca cega barrada — este projeto tem knowledge graph graphify
• Antes de grep/glob/find, consulte o grafo.
• Vá até ele: cd ${PROJ}
${COMANDOS}${STALE}
• Se o grafo não cobrir o que precisa, refaça esta busca — aviso único por sessão."
MSG_WARN="🕸️ Busca cega (grep/glob/find) num projeto que tem knowledge graph graphify
• Confirme no grafo antes de concluir qualquer coisa a partir dela.
• Vá até ele: cd ${PROJ}
${COMANDOS}${STALE}
• Este aviso é único por sessão."

# A régua do canal (perfil `hook` de `lib/regua_texto.py`, vinda de quality-goals.md):
# sem markdown, cabeçalho com emoji, uma ideia por linha, 6 linhas de orçamento. Cobra
# só o texto que VAI SAIR; o do outro ramo é cobrado na suíte. Defeito de forma não cala
# o aviso: o motivo vai pro stderr e o texto sai assim mesmo. Sem python3 ou sem a
# régua vendorada → silêncio, nunca queda (mesmo fail-open do resto do arquivo).
REGUA="$SCRIPT_DIR/../lib/regua_texto.py"
PY3=$(command -v python3 2>/dev/null)
regua_hook() { [ -n "$PY3" ] && [ -f "$REGUA" ] && printf '%s\n' "$1" | "$PY3" "$REGUA" --perfil hook --onde "$2" - || :; }

# conformance: default-warn — o caminho de deny existe, mas só com GRAPHIFY_DENY=1
# AVISO, não deny. O project-doc já nega a primeira busca da sessão com matcher mais
# largo (Grep|Glob|Bash|Agent contra Grep|Glob|Bash daqui) e mensagem quase idêntica —
# medido em 2026-07-30: dois denies e dois round-trips antes de qualquer trabalho
# começar, duas vezes na mesma sessão. O enquadramento continua chegando inteiro; o
# que sai é o segundo bloqueio. Um gate por ferramenta é o suficiente.
# Voltar a bloquear: GRAPHIFY_DENY=1.
if [ "${GRAPHIFY_DENY:-0}" = "1" ]; then
  regua_hook "$MSG_DENY" "deny do graphify-guard"
  jq -n --arg r "$MSG_DENY" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
else
  # Sem systemMessage de propósito: este aviso é endereçado ao MODELO, que é quem roda o
  # `graphify query` — o usuário não tem o que fazer com ele, e um systemMessage por sessão
  # em todo projeto com grafo vira ruído recorrente (§5.3, propriedade 1).
  regua_hook "$MSG_WARN" "aviso do graphify-guard"
  jq -n --arg r "$MSG_WARN" \
    '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$r}}'
fi
exit 0
