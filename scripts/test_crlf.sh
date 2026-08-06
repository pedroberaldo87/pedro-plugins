#!/bin/bash
# test_crlf.sh — RED→GREEN da issue 2 (CRLF).
# Trava: todos os .sh rastreados em LF + .gitattributes com eol=lf.
# Red hoje: .gitattributes não existe.
FAIL=0
FOUND=$(git ls-files '*.sh' | xargs grep -l $'\r' 2>/dev/null)
if [ -n "$FOUND" ]; then
  echo "FAIL .sh com CRLF:"; echo "$FOUND" | head -3 | sed 's/^/  /'; FAIL=1
else
  echo "ok   todos os .sh rastreados em LF"
fi
if [ -f .gitattributes ] && grep -q 'eol=lf' .gitattributes; then
  echo "ok   .gitattributes com eol=lf"
else
  echo "FAIL .gitattributes ausente (criar: *.sh text eol=lf)"; FAIL=1
fi
exit $FAIL
