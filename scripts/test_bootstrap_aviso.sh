#!/bin/bash
# test_bootstrap_aviso.sh — RED→GREEN da issue 5 (fail-open silencioso).
# Trava: o bootstrap avisa (systemMessage) quando jq/python3 falta, em vez de
# deixar o gate sair calado com o plugin 'enabled'.
# Invocação REAL (não token-grep): roda o sessionstart-deps.sh com PATH sem jq
# e com um stub de python3 que não executa (o da Microsoft Store), e exige que
# a saída seja JSON válido com systemMessage no TOPO — dentro de
# hookSpecificOutput o harness ignora o campo.
FAIL=0
BASH_BIN="$(command -v bash)"
PY="$(command -v python3 || command -v python)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
FAKEBIN="$TMP/bin"
mkdir -p "$FAKEBIN"
# stub executável mas que não roda: engana o command -v, não engana o --version
printf '#!/bin/sh\nexit 127\n' > "$FAKEBIN/python3"
chmod +x "$FAKEBIN/python3"
# PATH só com o stub: jq some e python3 não executa → o aviso TEM que sair.
# O payload leva um session_id novo a cada rodada porque o hook só avisa 1x por
# sessão (sentinel) — sem isso a segunda execução seguida sairia calada.
PAYLOAD="{\"session_id\":\"teste-aviso-$$-$(date +%s)\",\"source\":\"startup\"}"
OUT="$(printf '%s' "$PAYLOAD" | PATH="$FAKEBIN" BOOTSTRAP_DEPS_GATE=1 "$BASH_BIN" \
  plugins/bootstrap/hooks/sessionstart-deps.sh)"
if printf '%s' "$OUT" | "$PY" -c '
import json, sys
s = sys.stdin.read().strip()
try:
    d = json.loads(s)
except Exception:
    sys.exit(1)
sys.exit(0 if d.get("systemMessage") else 1)
'; then
  echo "ok   bootstrap avisa dependência faltante"
else
  echo "FAIL bootstrap não avisa dependência faltante (issue 5)"; FAIL=1
fi

# O aviso agora viaja em todo plugin com hooks: 2ª execução na MESMA sessão tem
# que sair calada, senão quem instala 12 plugins leva 12 avisos iguais.
OUT2="$(printf '%s' "$PAYLOAD" | PATH="$FAKEBIN" BOOTSTRAP_DEPS_GATE=1 "$BASH_BIN" \
  plugins/bootstrap/hooks/sessionstart-deps.sh)"
if [ -z "$OUT2" ]; then
  echo "ok   aviso sai 1x por sessão, não 1x por plugin"
else
  echo "FAIL aviso repetido na mesma sessão"; FAIL=1
fi
exit $FAIL
