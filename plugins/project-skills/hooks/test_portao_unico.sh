#!/usr/bin/env bash
# test_portao_unico.sh — o portão único de ExitPlanMode (F14.5 · F18.2).
#
# Antes da fusão TRÊS plugins respondiam ao evento (intent-guard, project-doc,
# visual) — três devoluções encadeadas para o mesmo plano. Agora o único
# registro é o pretooluse-plan-gate.sh da família, que CHAMA os outros dois por
# nome de plugin, na ordem pedido → página, com fail-open por peça.
#
# Duas metades: (a) o REGISTRO — o medidor oficial devolve exatamente 1
# respondente; (b) a ORQUESTRAÇÃO — o portão propaga o bloqueio de cada peça
# (exit 2 e permissionDecision:deny) e é fail-open com peça ausente.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ok   $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL $1"; }

# (a) registro: 1 respondente, e é o da família
OUT=$(python3 scripts/hook_contract.py --responde ExitPlanMode 2>/dev/null)
echo "$OUT" | grep -q "TOTAL: 1" && ok "o medidor devolve UM respondente ao ExitPlanMode" \
                                 || bad "respondente único (TOTAL: 1) — saiu: $(echo "$OUT" | tail -1)"
echo "$OUT" | grep -q "project-skills pretooluse-plan-gate.sh" \
  && ok "o respondente é o portão da família" || bad "o respondente é o portão da família"

# (b) orquestração: um portão de mentira no lugar de cada peça
TMP=$(mktemp -d "${TMPDIR:-/tmp}/portao-unico-XXXXXX")
trap 'rm -rf "$TMP"' EXIT
GATE="plugins/project-skills/hooks/pretooluse-plan-gate.sh"
# extrai só o bloco do portão: roda o hook real com um resolve-plugin FALSO no PATH
# do plugin — mais simples: chama o hook com CLAUDE_PLUGIN_ROOT apontando pra uma
# cópia onde resolve-plugin.sh devolve as peças de mentira.
mkdir -p "$TMP/fam/hooks" "$TMP/ig/hooks" "$TMP/vi/hooks"
cp plugins/project-skills/hooks/hook-json.sh "$TMP/fam/hooks/"
cp "$GATE" "$TMP/fam/hooks/pretooluse-plan-gate.sh"
cat > "$TMP/fam/hooks/resolve-plugin.sh" <<RES
#!/usr/bin/env bash
case "\$1" in
  intent-guard) echo "$TMP/ig/hooks/plan-gate.sh" ;;
  visual)       echo "$TMP/vi/hooks/pre-exitplan-visualize.sh" ;;
  *) exit 1 ;;
esac
RES
chmod +x "$TMP/fam/hooks/resolve-plugin.sh"
EVENTO='{"tool_name":"ExitPlanMode","session_id":"sess-portao","cwd":"'"$TMP"'"}'
roda() { printf '%s' "$EVENTO" | CLAUDE_PLUGIN_ROOT="$TMP/fam" bash "$TMP/fam/hooks/pretooluse-plan-gate.sh" 2>"$TMP/err"; }

# peça 1 bloqueia por exit 2 → o portão propaga o motivo e o código
printf '#!/usr/bin/env bash\necho "PEDIDO DESCOBERTO SEM COBERTURA" >&2\nexit 2\n' > "$TMP/ig/hooks/plan-gate.sh"
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/vi/hooks/pre-exitplan-visualize.sh"
SAIDA=$(roda); RC=$?
[ "$RC" -eq 2 ] && grep -q "PEDIDO DESCOBERTO" "$TMP/err" \
  && ok "bloqueio por exit 2 da 1ª peça propaga com o motivo" \
  || bad "propagação do exit 2 (rc=$RC)"

# peça 2 bloqueia por deny → o portão repassa o JSON
printf '#!/usr/bin/env bash\nexit 0\n' > "$TMP/ig/hooks/plan-gate.sh"
printf '#!/usr/bin/env bash\necho "{\\"hookSpecificOutput\\":{\\"permissionDecision\\":\\"deny\\",\\"permissionDecisionReason\\":\\"falta a pagina\\"}}"\nexit 0\n' > "$TMP/vi/hooks/pre-exitplan-visualize.sh"
SAIDA=$(roda); RC=$?
[ "$RC" -eq 0 ] && printf '%s' "$SAIDA" | grep -q '"deny"' \
  && ok "bloqueio por deny da 2ª peça repassa o JSON" \
  || bad "propagação do deny (rc=$RC · $SAIDA)"

# peças ausentes → fail-open: o portão segue pro próprio julgamento sem morrer
rm "$TMP/ig/hooks/plan-gate.sh" "$TMP/vi/hooks/pre-exitplan-visualize.sh"
SAIDA=$(roda); RC=$?
[ "$RC" -ne 2 ] && ok "peça ausente não derruba o portão (fail-open)" \
                || bad "fail-open com peça ausente (rc=$RC)"

# chave de desligar
printf '#!/usr/bin/env bash\necho NUNCA >&2\nexit 2\n' > "$TMP/ig/hooks/plan-gate.sh"
SAIDA=$(printf '%s' "$EVENTO" | CLAUDE_PLUGIN_ROOT="$TMP/fam" PLAN_PORTAO_UNICO=0 bash "$TMP/fam/hooks/pretooluse-plan-gate.sh" 2>"$TMP/err"); RC=$?
grep -q NUNCA "$TMP/err" && bad "PLAN_PORTAO_UNICO=0 desliga a orquestração" \
                         || ok "PLAN_PORTAO_UNICO=0 desliga a orquestração"

echo; echo "── $PASS passou · $FAIL falhou ──"
[ "$FAIL" -eq 0 ]
