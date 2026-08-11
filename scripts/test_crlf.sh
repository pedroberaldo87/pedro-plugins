#!/bin/bash
# test_crlf.sh — RED→GREEN da issue 2 (CRLF).
# Trava: todos os .sh rastreados em LF + .gitattributes com eol=lf e cobrindo a si.
#
# ⚠️ CRLF em `.sh` não é questão de estilo: `#!/bin/bash\r` faz o shell procurar um
# interpretador cujo nome termina em carriage return, e o erro que sai não menciona
# o CR. O hook simplesmente não roda.
#
# ⚠️ A CONTAGEM É FEITA EM PYTHON, e não por `git ls-files | xargs grep`. O
# pipeline acusou `154 de 154` no runner do Windows — um resultado que se refuta
# sozinho, porque este próprio arquivo é `.sh` e ESTAVA rodando quando acusou. O
# `xargs` do MSYS e o `grep` do Git Bash não concordam sobre o que é fim de linha
# na hora de casar `$'\r'`, e a resposta que sai não é a do disco. Quem responde
# "este byte está no arquivo?" é quem lê os bytes.
FAIL=0

RESULTADO=$(git ls-files -z '*.sh' | python3 -c '
import sys
alvos = [x for x in sys.stdin.buffer.read().split(b"\0") if x.strip()]
ruins = []
for nome in alvos:
    caminho = nome.decode("utf-8", "replace")
    try:
        with open(caminho, "rb") as fh:
            if b"\r\n" in fh.read():
                ruins.append(caminho)
    except OSError:
        pass          # arquivo rastreado e ausente do disco não é problema DESTE teste
print(len(alvos))
for r in ruins:
    print(r)
')
TOTAL=$(printf '%s' "$RESULTADO" | head -1)
RUINS=$(printf '%s' "$RESULTADO" | tail -n +2)
N=$(printf '%s' "$RUINS" | grep -c . || true)

if [ "$N" -gt 0 ]; then
  echo "FAIL $N de $TOTAL .sh rastreados estão com CRLF (mostrando até 10):"
  printf '%s\n' "$RUINS" | head -10 | sed 's/^/  /'
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
# e `*.py`; com o `core.autocrlf=true` que o Git for Windows traz de fábrica, ELE
# sairia do checkout com CRLF, a linha viraria `eol=lf\r`, o valor deixaria de ser
# válido e o git não normalizaria mais nada. É o defeito circular: o arquivo que
# impede a conversão seria a primeira vítima dela.
if git check-attr eol -- .gitattributes | grep -q 'eol: lf'; then
  echo "ok   o .gitattributes cobre a si mesmo (eol: lf)"
else
  echo "FAIL o .gitattributes NÃO se cobre — ele mesmo vira CRLF e derruba a regra"
  echo "     conserto: a linha \`.gitattributes text eol=lf\`, DEPOIS da regra geral"
  FAIL=1
fi

# E a regra tem que ser GERAL: por extensão só protege o que alguém lembrou de
# escrever, e `.mjs`, `.yml` e `.json` já tinham ficado de fora.
if grep -qE '^\* +text' .gitattributes; then
  echo "ok   a regra vale para todo arquivo de texto, não só para extensão listada"
else
  echo "FAIL sem regra geral — extensão nova nasce desprotegida"
  FAIL=1
fi

exit $FAIL
