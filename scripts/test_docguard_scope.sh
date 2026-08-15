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
# Os gêmeos rodam no MESMO bash que esta bateria: no Windows o `bash` do PATH é o
# do WSL, e chamá-lo por nome trocaria o interpretador no meio do caminho — o hook
# rodaria noutro sistema de arquivos, onde o projeto de mentira abaixo nem existe.
BASH_BIN="${BASH:-bash}"
# O temporário DO SISTEMA, perguntado e não assumido: `/tmp` literal é caminho do
# SHELL, e o projeto de mentira precisa existir também para quem é nativo.
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
. "$AQUI/../_shared/lib-tmpdir.sh"
TMPD="$(td_tmpdir)"
# O GRAFO É DO TESTE, NUNCA O DO REPOSITÓRIO. O gêmeo `graphify-guard` só age onde
# acha `graphify-out/graph.json` subindo a partir do `cwd` — e `graphify-out/` está
# no .gitignore (linha 53). Na máquina de quem escreveu ele existe, então a bateria
# passava; no runner limpo ele não existe, o hook saía calado, e os 17 casos de
# "busca cega tem que bloquear" reprovavam com `0 denies` — sem que nada dissesse
# que a causa era um artefato ausente. O teste monta o seu, e mede o ESCOPO da regra
# em vez de medir o que estava no disco de quem rodou.
SCOPE_CWD="$(mktemp -d "$TMPD/scope-XXXXXX")"
# CADA GÊMEO TEM O SEU PRÉ-REQUISITO, e o projeto de mentira traz os dois:
#   graphify-guard → graphify-out/graph.json  (subindo a partir do cwd)
#   doc-guard      → .claude/docs/ + CLAUDE.md (a doc que ele manda ler)
# Sem eles o hook sai CALADO — que é o comportamento certo dele, e o errado para
# uma bateria que mede ESCOPO de regra.
mkdir -p "$SCOPE_CWD/graphify-out" "$SCOPE_CWD/.claude/docs"
printf '{"nodes":[],"edges":[]}' > "$SCOPE_CWD/graphify-out/graph.json"
printf '# Projeto de mentira\n' > "$SCOPE_CWD/CLAUDE.md"
printf '# Projeto de mentira\n' > "$SCOPE_CWD/.claude/CLAUDE.md"
printf '# arquitetura de mentira\n' > "$SCOPE_CWD/.claude/docs/architecture.md"
# Regex e não texto fixo: a decisão é JSON, e desde o fallback sem `jq` ela é montada
# COMPACTA (`"permissionDecision":"deny"`). Casar o espaço do `jq -n` media formatação,
# não decisão.
DENY='permissionDecision"[[:space:]]*:[[:space:]]*"deny'
# O python que RESPONDE, não o primeiro que o PATH oferecer: no Windows o
# `python3.exe` do PATH pode ser o stub da Store, que existe e não roda — e um
# gerador de payload mudo devolveria `0 denies` em TODO caso, reprovando a regra
# certa por causa do interpretador.
for c in python3 python; do
  P="$(command -v "$c" 2>/dev/null)" || continue
  [ -n "$P" ] && "$P" --version >/dev/null 2>&1 && { PY="$P"; break; }
done
[ -n "$PY" ] || { echo "↷ pulada: nenhum python funcional nesta máquina"; exit 0; }

# O graphify-guard avisa uma vez por sessão e queima um sentinel em /tmp; sem sessão
# nova por chamada, o 2º caso da bateria sairia calado e a suíte ficaria verde à toa.
trap 'rm -f "$TMPD/claude-graphify-guard-${S_BASE}-"* 2>/dev/null; rm -rf "$SCOPE_CWD" 2>/dev/null' EXIT

deny_count() { # $1=hook  $2=comando
  S="${S_BASE}-${RANDOM}${RANDOM}"
  rm -f "$TMPD/claude-graphify-guard-$S" 2>/dev/null
  # MSYS_NO_PATHCONV/MSYS2_ARG_CONV_EXCL: no Windows o bash do Git reescreve todo
  # argumento que COMEÇA com `/` para caminho do Windows antes de entregá-lo a um
  # programa nativo — o caso `/usr/bin/grep x` chegava ao Python como
  # `C:/Program Files/Git/usr/bin/grep x` e o hook, com razão, não bloqueava. O
  # que se mede aqui é a regra, não o tradutor de caminho do ambiente.
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' \
  "$PY" -c "import json,sys;print(json.dumps({'tool_name':'Bash','session_id':'$S','cwd':'$SCOPE_CWD','tool_input':{'command':sys.argv[1]}}))" \
    "$2" | GRAPHIFY_DENY=1 "$BASH_BIN" "$1" 2>/dev/null | grep -cE "$DENY"
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
