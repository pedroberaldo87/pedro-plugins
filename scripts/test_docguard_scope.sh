#!/bin/bash
# test_docguard_scope.sh — RED→GREEN do escopo do doc-guard.
# Trava DUAS decisões:
#   (A) o filtro não dispara em TEXTO — `echo "use grep"` passa (furo A, red hoje).
#   (B) posição de comando não é só início de linha — prefixo de variável, prefixo de
#       caminho, crase, $( ), abre-chave de bloco e do/then também são posição de comando.
#   (C) leitura direta NÃO é busca cega — `cat`/`ls -R`/`python3` passam (decisão por design).
#   (D) a bateria roda contra os DOIS gêmeos — a regra de escopo é byte-a-byte igual nos
#       dois hooks, e um teste que só exercita um deixa a divergência futura passar (foi
#       assim que o furo reabriu uma vez). O graphify-guard roda com GRAPHIFY_DENY=1
#       porque em produção o ramo dele é aviso; o que se mede aqui é o ESCOPO, não o ramo.
# E o núcleo: busca cega (`grep -r`, `find`) continua bloqueada.
HOOKS="plugins/project-skills/hooks/pretooluse-doc-guard.sh
plugins/graphify-guard/hooks/pretooluse-graphify-guard.sh"
S_BASE="scope-test-$$"
# Regex e não texto fixo: a decisão é JSON, e desde o fallback sem `jq` ela é montada
# COMPACTA (`"permissionDecision":"deny"`). Casar o espaço do `jq -n` media formatação,
# não decisão.
DENY='permissionDecision"[[:space:]]*:[[:space:]]*"deny'
PY="$(command -v python3 || command -v python)"

# O graphify-guard avisa uma vez por sessão e queima um sentinel em /tmp; sem sessão
# nova por chamada, o 2º caso da bateria sairia calado e a suíte ficaria verde à toa.
trap 'rm -f "/tmp/claude-graphify-guard-${S_BASE}-"* 2>/dev/null' EXIT

deny_count() { # $1=hook  $2=comando
  S="${S_BASE}-${RANDOM}${RANDOM}"
  rm -f "/tmp/claude-graphify-guard-$S" 2>/dev/null
  "$PY" -c "import json,sys;print(json.dumps({'tool_name':'Bash','session_id':'$S','cwd':'$PWD','tool_input':{'command':sys.argv[1]}}))" \
    "$2" | GRAPHIFY_DENY=1 bash "$1" 2>/dev/null | grep -cE "$DENY"
}

FAIL=0
for H in $HOOKS; do
echo "── gêmeo: $H ──"
# NÃO-busca-cega: deve passar (0 denies)
for c in 'cat config.json' 'ls -R src' 'python3 -c "print(1)"' 'echo "use grep here"' 'echo "find the file"'; do
  n=$(deny_count "$H" "$c")
  [ "$n" = "0" ] && echo "ok   passa: $c" || { echo "FAIL bloqueado: $c ($n denies)"; FAIL=1; }
done
# Busca cega: deve ser bloqueada (1 deny)
# Caso tab real (indentação de linha de comando multilinha): o $'\t' vira um tab de
# verdade e [[:space:]] casa no BSD e no GNU — grep indentado por tab não pode passar.
for c in 'grep -rn foo src/' 'rg --files src' 'find . -name "*.py"' 'cat x | grep foo' \
         'sudo grep -rn foo src/' 'time rg foo src/' 'xargs grep foo src/' \
         'xargs -I{} grep' 'xargs -n1 grep' 'sudo -u root grep' 'env X=1 grep' 'time -p grep' \
         $'echo start\n\tgrep -rn foo src/' \
         'VAR=1 grep x' 'FOO=1 BAR=2 grep x' 'VAR=1 sudo grep x' \
         '/usr/bin/grep x' './scripts/grep x' '../bin/rg foo' \
         '`grep foo`' 'echo $(grep foo)' '{ grep foo; }' \
         'for f in *; do grep foo $f; done' 'if true; then grep foo x; fi' \
         'ls | { grep foo; }'; do
  n=$(deny_count "$H" "$c")
  [ "$n" = "1" ] && echo "ok   bloqueado: $c" || { echo "FAIL não bloqueado: $c ($n denies)"; FAIL=1; }
done
done

exit $FAIL
