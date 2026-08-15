#!/bin/bash
# test_entrada_no_arranque.sh — o arranque da sessão drena a fila de entrada do plano,
# MAS só quando não há motor vivo.
#
# Roda o hook DE VERDADE, com o payload que o harness manda. O que se cobra aqui é o
# par: com motor aceso ele ADIA (e o arquivo continua na fila); sem motor ele
# INCORPORA e arquiva. Testar só o caminho feliz deixaria passar exatamente a corrida
# que a fila existe para evitar.
#
#   bash plugins/visual/hooks/test_entrada_no_arranque.sh

HOOK="$(cd "$(dirname "$0")" && pwd)/sessionstart-plan.sh"
# O temporário sai da receita única: `mktemp -d` pelado devolve o `/tmp` do Git Bash,
# que o python3 nativo do Windows resolve como `C:\tmp\...` e não acha (ver
# .claude/reports/causas-windows-2026-08-15.md).
. "$(cd "$(dirname "$0")" && pwd)/lib-tmpdir.sh" 2>/dev/null
TMP="$(mktemp -d "$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")/entrada-XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

OK=0; FALHA=0
check() {
  if [ "$2" = "1" ]; then OK=$((OK + 1)); echo "  ok   $1"
  else FALHA=$((FALHA + 1)); echo "  FALHA $1 ${3:-}"; fi
}

PROJ="$TMP/proj"
PLANS="$PROJ/.claude/plans"
CFG="$TMP/cfg"
mkdir -p "$PLANS/entrada" "$CFG/andamento" "$PROJ/.git"

python3 - "$PLANS" <<'PY'
import json, os, sys
d = sys.argv[1]
json.dump({"id": "p-arranque", "title": "plano de teste", "status": "active",
           "requisitos": [{"id": "S-1", "titulo": "r", "ca": "c"}],
           "phases": [{"id": "F1", "title": "fase", "items": [
               {"id": "F1.1", "title": "a", "desc": "d", "requisito": "S-1", "pronto": "p"}]}]},
          open(os.path.join(d, "p-arranque.plan.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
json.dump({"para_o_plano": "p-arranque",
           "itens_novos": [{"id": "F1.9", "fase": "F1", "title": "veio da fila",
                            "desc": "d", "requisito": "S-1", "pronto": "p"}]},
          open(os.path.join(d, "entrada", "nova.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
PY

payload() { printf '{"session_id":"sessao-teste","cwd":"%s"}' "$PROJ"; }
roda() { payload | CLAUDE_CONFIG_DIR="$CFG" bash "$HOOK" 2>&1; }
ids() {
  python3 -c "
import json,sys
d=json.load(open('$PLANS/p-arranque.plan.json',encoding='utf-8'))
print(' '.join(i['id'] for ph in d['phases'] for i in ph['items']))"
}

echo "[fila de entrada no arranque da sessão]"

# A) motor vivo — de OUTRA sessão, que é o caso perigoso: drenar aqui corromperia
#    o plano que aquele motor está marcando agora.
: > "$CFG/andamento/ativo-outra-sessao"
OUT=$(roda)
check "com motor vivo, avisa que adiou" \
  "$(printf '%s' "$OUT" | grep -q 'motor está vivo' && echo 1 || echo 0)" "saiu: $OUT"
check "com motor vivo, o arquivo CONTINUA na fila" \
  "$([ -f "$PLANS/entrada/nova.json" ] && echo 1 || echo 0)"
check "com motor vivo, o plano NÃO foi tocado" \
  "$([ "$(ids)" = "F1.1" ] && echo 1 || echo 0)" "ids: $(ids)"

# B) sem motor — agora é seguro
rm -f "$CFG/andamento"/ativo-*
OUT=$(roda)
check "sem motor, incorpora o passo da fila" \
  "$(printf '%s' "$OUT" | grep -q 'F1.9' && echo 1 || echo 0)" "saiu: $OUT"
check "o passo aparece no plano" \
  "$(printf '%s' "$(ids)" | grep -q 'F1.9' && echo 1 || echo 0)" "ids: $(ids)"
check "o arquivo sai da fila" \
  "$([ ! -f "$PLANS/entrada/nova.json" ] && echo 1 || echo 0)"
check "e é ARQUIVADO, não apagado (o registro do que entrou vale)" \
  "$([ -f "$PLANS/entrada/incorporados/nova.json" ] && echo 1 || echo 0)"

# C) rodar de novo com a fila vazia não pode reclamar nem sujar a saída
OUT=$(roda)
check "fila vazia não emite ruído sobre entrada" \
  "$(printf '%s' "$OUT" | grep -qc 'fila de entrada' >/dev/null; \
     [ "$(printf '%s' "$OUT" | grep -c 'incorporado')" = "0" ] && echo 1 || echo 0)"

# D) fail-open: o hook nunca pode derrubar o arranque da sessão
printf '{ nao e json' | CLAUDE_CONFIG_DIR="$CFG" bash "$HOOK" >/dev/null 2>&1
check "payload quebrado não derruba o arranque (fail-open)" \
  "$([ $? -eq 0 ] && echo 1 || echo 0)"

echo
if [ "$FALHA" -eq 0 ]; then echo "OK ($OK checks)"; exit 0; fi
echo "FALHOU ($FALHA de $((OK + FALHA)))"
exit 1
