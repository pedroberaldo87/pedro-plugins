#!/bin/bash
# test_paths_normalize.sh — RED→GREEN do fix de paths (issue 4) e do shell POSIX.
# Trava três coisas:
#   Windows: CLAUDE_PLUGIN_ROOT com backslash → normaliza para '/'.
#   macOS:   sem backslash → no-op, o path fica intocado.
#   TODO shell: a normalização roda sob sh/dash/bash/zsh — `${var//x/y}` é bashism
#               e dá "Bad substitution" no /bin/sh do Linux, matando TODO hook.
# E o requisito de distribuição: todo hooks.json usa o prefixo exato que foi testado
# aqui, e o exporta — para o script chamado ver o caminho JÁ normalizado por dentro.

FAIL=0
check() {
  if [ "$1" = "$2" ]; then echo "ok   $3"
  else echo "FAIL $3 — got '$1', want '$2'"; FAIL=1; fi
}

# O prefixo CANÔNICO — é esta string, caractere a caractere, que tem que estar nos
# hooks.json. Testar uma coisa e distribuir outra foi o furo da versão anterior.
NORM='CLAUDE_PLUGIN_ROOT=$(printf '"'"'%s'"'"' "$CLAUDE_PLUGIN_ROOT" | tr '"'"'\\'"'"' /); export CLAUDE_PLUGIN_ROOT;'

WIN='C:\Users\quem-instalou\.claude\plugins\cache\visual\1.19.5'
WANT='C:/Users/quem-instalou/.claude/plugins/cache/visual/1.19.5'  # public-ok: conta fictícia, é o caminho Windows sob teste
MAC='/home/quem-instalou/.claude/plugins/cache/visual/1.19.5'  # public-ok: conta fictícia, é o caminho POSIX sob teste

# 1+2) a normalização, sob CADA shell que pode executar um hook
for SH in sh dash bash zsh; do
  command -v "$SH" >/dev/null 2>&1 || { echo "ok   $SH ausente nesta máquina — pulado"; continue; }
  OUT=$(CLAUDE_PLUGIN_ROOT="$WIN" "$SH" -c "$NORM"' echo "$CLAUDE_PLUGIN_ROOT"' 2>&1)
  check "$OUT" "$WANT" "$SH · backslash → forward-slash"
  OUT=$(CLAUDE_PLUGIN_ROOT="$MAC" "$SH" -c "$NORM"' echo "$CLAUDE_PLUGIN_ROOT"' 2>&1)
  check "$OUT" "$MAC" "$SH · forward-slash intocado (no-op)"
done

# 3) a variável tem que chegar EXPORTADA ao script chamado — é isso que faz os
#    scripts que releem ${CLAUDE_PLUGIN_ROOT} por dentro verem o caminho normalizado.
OUT=$(CLAUDE_PLUGIN_ROOT="$WIN" sh -c "$NORM"' sh -c '"'"'echo "$CLAUDE_PLUGIN_ROOT"'"'"'' 2>&1)
check "$OUT" "$WANT" 'a variável normalizada é exportada para o processo filho'

# 4) distribuição: nenhum hooks.json chama ${CLAUDE_PLUGIN_ROOT} cru...
CRU=$(grep -rl '\${CLAUDE_PLUGIN_ROOT}/' plugins/*/hooks/hooks.json 2>/dev/null)
if [ -n "$CRU" ]; then
  echo "FAIL hooks.json ainda usam root cru:"; echo "$CRU" | sed 's/^/     /'; FAIL=1
else
  echo "ok   nenhum hooks.json usa o root cru"
fi

# 5) ...e nenhum usa a substituição de string do bash, que morre no /bin/sh do Linux
BASHISM=$(grep -rl 'CLAUDE_PLUGIN_ROOT//' plugins/*/hooks/hooks.json 2>/dev/null)
if [ -n "$BASHISM" ]; then
  echo "FAIL hooks.json usam \${var//x/y} (bashism — Bad substitution no sh POSIX):"
  echo "$BASHISM" | sed 's/^/     /'; FAIL=1
else
  echo "ok   nenhum hooks.json depende de sintaxe exclusiva do bash"
fi

# 6) todo comando que invoca script do plugin carrega o prefixo canônico INTEIRO —
#    inclusive o `export`, sem o qual o script chamado relê a variável NÃO normalizada
SEMNORM=0
for HJ in plugins/*/hooks/hooks.json; do
  MISS=$(python3 - "$HJ" "$NORM" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
pref = sys.argv[2]
for ev, entries in (d.get('hooks') or {}).items():
    for entry in entries:
        for h in entry.get('hooks') or []:
            c = h.get('command', '')
            if 'CLAUDE_PLUGIN_ROOT' in c and not c.startswith(pref):
                print('%s: %s' % (ev, c[:70]))
PY
)
  if [ -n "$MISS" ]; then
    SEMNORM=1; FAIL=1
    echo "FAIL $HJ tem comando sem o prefixo canônico completo (com export):"
    echo "$MISS" | sed 's/^/     /'
  fi
done
[ "$SEMNORM" = "0" ] && echo "ok   todo comando com CLAUDE_PLUGIN_ROOT abre pelo prefixo canônico completo"

# 7) existência: cada script referenciado resolve para um arquivo real
MISSANY=0
for HJ in plugins/*/hooks/hooks.json; do
  PLUG=$(basename "$(dirname "$(dirname "$HJ")")")
  MISSING=$(grep -oE '/hooks/[A-Za-z0-9_.-]+\.(sh|py)' "$HJ" \
    | sed -E 's|^/hooks/||' | sort -u \
    | while read -r s; do [ -f "plugins/$PLUG/hooks/$s" ] || echo "$s"; done)
  if [ -n "$MISSING" ]; then
    MISSANY=1; FAIL=1
    echo "FAIL $HJ referencia script inexistente:"; echo "$MISSING" | sed 's/^/     /'
  fi
done
[ "$MISSANY" = "0" ] && echo "ok   todo script referenciado nos hooks.json existe"

exit $FAIL
