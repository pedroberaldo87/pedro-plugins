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
  echo "FAIL .gitattributes ausente (criar: * text=auto eol=lf)"; FAIL=1
fi

# REGRESSÃO 2026-08-11: o arquivo tem que cobrir a SI MESMO. Ele listava só `*.sh`
# e `*.py`; no Windows, com o `core.autocrlf=true` de fábrica, ELE saía do checkout
# com CRLF, a linha virava `eol=lf\r`, o valor deixava de ser válido e o git não
# normalizava NADA — 154 de 154 `.sh` com CRLF no runner. É o defeito circular: o
# arquivo que impede a conversão é a primeira vítima dela.
if git check-attr eol -- .gitattributes | grep -q 'eol: lf'; then
  echo "ok   o .gitattributes cobre a si mesmo (eol: lf)"
else
  echo "FAIL o .gitattributes NÃO se cobre — ele mesmo vira CRLF e derruba a regra"
  echo "     conserto: uma linha \`.gitattributes text eol=lf\`, DEPOIS da regra geral"
  FAIL=1
fi

# E a regra tem que ser GERAL: por extensão só protege o que alguém lembrou de
# escrever, e `.mjs`, `.yml` e `.json` já tinham ficado de fora.
if grep -qE '^\* +text' .gitattributes; then
  echo "ok   a regra vale para todo arquivo de texto, não só para extensão listada"
else
  echo "FAIL sem regra geral (`* text=auto eol=lf`): extensão nova nasce desprotegida"
  FAIL=1
fi
exit $FAIL
