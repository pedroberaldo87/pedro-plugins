#!/bin/bash
# test_crlf.sh — RED→GREEN da issue 2 (CRLF).
# Trava: todos os .sh rastreados em LF + .gitattributes com eol=lf.
#
# ⚠️ O CRLF é defeito de PRODUTO, não de estilo: `#!/bin/bash\r` faz o shell
# procurar um interpretador com um carriage return no nome, e a mensagem que sai
# ("bad interpreter") não menciona o CR. Hook com CRLF simplesmente não roda.
#
# O DIAGNÓSTICO É PARTE DA TRAVA. Até 2026-08-11 este teste imprimia `head -3` e
# nada mais: no Windows ele acusou três arquivos de `.claude/hooks/` e a leitura
# natural foi "são esses três" — quando `head -3` é o CORTE, não a medida. Sem o
# total, não dá para distinguir "três arquivos escaparam" de "todos os .sh estão
# convertidos e estes são os três primeiros em ordem alfabética", que pedem
# consertos opostos. Agora ele diz quantos são, de quantos, e mostra até dez.
FAIL=0
TOTAL=$(git ls-files '*.sh' | wc -l | tr -d ' ')
FOUND=$(git ls-files '*.sh' | xargs grep -l $'\r' 2>/dev/null)
N=$(printf '%s' "$FOUND" | grep -c . || true)
if [ -n "$FOUND" ]; then
  echo "FAIL $N de $TOTAL .sh rastreados estão com CRLF (mostrando até 10):"
  echo "$FOUND" | head -10 | sed 's/^/  /'
  [ "$N" -gt 10 ] && echo "  … e mais $((N - 10))"
  FAIL=1
else
  echo "ok   todos os $TOTAL .sh rastreados em LF"
fi
if [ -f .gitattributes ] && grep -q 'eol=lf' .gitattributes; then
  echo "ok   .gitattributes com eol=lf"
else
  echo "FAIL .gitattributes ausente (criar: *.sh text eol=lf)"; FAIL=1
fi
exit $FAIL
