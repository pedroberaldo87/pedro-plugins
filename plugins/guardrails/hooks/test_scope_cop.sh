#!/bin/bash
# Suite do scope-cop.sh — o CANAL DE SAÍDA de cada modo, não o julgamento.
#
# O juiz é um `claude -p` (não-determinístico e caro). Aqui ele é substituído por
# um binário falso no PATH que devolve sempre o mesmo veredito — o que se testa é
# o que o hook FAZ com o veredito, que é determinístico.
#
# Isolamento total: HOME aponta pra um mktemp, então nem o log, nem o modo, nem o
# blockstreak reais são tocados.

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scope-cop.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0; FAIL=0
check() {
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1))
  else FAIL=$((FAIL + 1)); printf '  ✗ %s — esperava %s, veio %s\n' "$1" "$3" "$2" >&2; fi
}

# --- juiz falso: sempre "block", pra exercitar o ramo que avisa/bloqueia ---
mkdir -p "$TMP/bin"
cat > "$TMP/bin/claude" <<'FAKE'
#!/bin/bash
echo '{"verdict":"block","reason":"mexeu no container inteiro, não só no botão"}'
FAKE
chmod +x "$TMP/bin/claude"

# --- transcript com um pedido de UI (sem isso o hook sai por SKIP:no-ui-request) ---
TRANSCRIPT="$TMP/transcript.jsonl"
jq -nc '{type:"user", message:{content:"muda a cor do botão do header"}}' > "$TRANSCRIPT"

# --- arquivo de UI de verdade (extensão policiada, fora das isenções) ---
UI_FILE="$TMP/app.tsx"
printf 'export const App = () => <div className="header" />\n' > "$UI_FILE"

payload() { # $1=session
  jq -nc --arg s "$1" --arg t "$TRANSCRIPT" --arg f "$UI_FILE" \
    '{session_id:$s, transcript_path:$t, tool_name:"Edit",
      tool_input:{file_path:$f, old_string:"className=\"header\"", new_string:"className=\"header xl\""}}'
}

run() { # $1=modo  $2=session → stdout cru do hook
  mkdir -p "$TMP/home/.claude/guardrails"
  printf '%s' "$1" > "$TMP/home/.claude/guardrails/scope-cop.mode"
  # `env -u`: o HOOK_DIR deriva de ${CLAUDE_CONFIG_DIR:-$HOME/.claude}, então a env var
  # da máquina que roda o teste vazaria o estado real pra dentro da suíte.
  printf '%s' "$(payload "$2")" \
    | env -u CLAUDE_CONFIG_DIR HOME="$TMP/home" PATH="$TMP/bin:$PATH" bash "$HOOK" 2>/dev/null
}

echo "── modo warn: o aviso tem que CHEGAR no usuário ──"
OUT_WARN="$(run warn "warn-$$")"

# additionalContext em PreToolUse chega ao Claude, mas o transcript FILTRA o
# attachment hook_additional_context — o usuário não vê nada. systemMessage não é
# filtrado. Sem ele, "warn" entrega ao usuário o mesmo silêncio do "off", e o
# cabeçalho do hook ("Aviso é honesto; silêncio não") vira mentira.
check "warn emite systemMessage (o único canal que o usuário enxerga)" \
  "$(printf '%s' "$OUT_WARN" | jq -r 'if (.systemMessage // "") == "" then "vazio" else "tem" end' 2>/dev/null)" "tem"
check "warn segue emitindo additionalContext (o canal do Claude)" \
  "$(printf '%s' "$OUT_WARN" | jq -r 'if (.hookSpecificOutput.additionalContext // "") == "" then "vazio" else "tem" end' 2>/dev/null)" "tem"
case "$OUT_WARN" in *"não só no botão"*) R=sim ;; *) R=nao ;; esac
check "o aviso cita o motivo concreto do juiz" "$R" "sim"
check "warn NÃO bloqueia a edição" \
  "$(printf '%s' "$OUT_WARN" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)" "allow"

echo "── modo deny: segue negando (nada de regressão) ──"
OUT_DENY="$(run deny "deny-$$")"
check "deny nega a edição" \
  "$(printf '%s' "$OUT_DENY" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)" "deny"

echo "── modo off: silêncio total ──"
check "off não emite nada" "$(run off "off-$$")" ""

echo "── modo desconhecido: default deny, mas nunca em silêncio ──"
# Desde que o modo virou fonte de verdade de 3 estados, um erro de digitação
# ("wanr", "ask") entrega o gate MAIS severo justamente a quem pediu o mais brando.
# Cair no default é o certo; cair calado não é.
LOG="$TMP/home/.claude/guardrails/scope-cop.log"
: > "$LOG"
OUT_TYPO="$(run wanr "typo-$$")"
check "modo com erro de digitação cai no default deny" \
  "$(printf '%s' "$OUT_TYPO" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)" "deny"
check "o valor ignorado deixa rastro no log" \
  "$(grep -c 'MODE:invalido' "$LOG" 2>/dev/null | tr -d ' ')" "1"
case "$(cat "$LOG" 2>/dev/null)" in *wanr*) R=sim ;; *) R=nao ;; esac
check "o log nomeia QUAL valor foi ignorado" "$R" "sim"

: > "$LOG"
run deny "valido-$$" >/dev/null
run "" "vazio-$$" >/dev/null
check "modo válido e arquivo vazio (máquina nova) não viram alerta" \
  "$(grep -c 'MODE:invalido' "$LOG" 2>/dev/null | tr -d ' ')" "0"

echo "── kill-switch SCOPE_COP_GATE=0: desliga sem editar o arquivo ──"
# Propriedade 3 do contrato dos hooks (patterns.md §1.2): toda trava se desliga por
# env var no formato <NOME>_GATE=0. O scope-cop tinha como ÚNICO interruptor um
# arquivo fora do repo (~/.claude/guardrails/scope-cop.mode) — quem lê a tabela
# conclui que a env var existe, e num momento ruim tenta desligar com ela.
run_gate() { # $1=modo  $2=session  $3=valor de SCOPE_COP_GATE → stdout cru
  mkdir -p "$TMP/home/.claude/guardrails"
  printf '%s' "$1" > "$TMP/home/.claude/guardrails/scope-cop.mode"
  printf '%s' "$(payload "$2")" \
    | env -u CLAUDE_CONFIG_DIR HOME="$TMP/home" PATH="$TMP/bin:$PATH" \
        SCOPE_COP_GATE="$3" bash "$HOOK" 2>/dev/null
}
OUT_G0="$(run_gate deny "gate0-$$" 0)"; RC_G0=$?
check "com SCOPE_COP_GATE=0 nem o modo deny fala" "$OUT_G0" ""
# Silêncio só prova obediência junto com rc 0: hook quebrado também sai calado.
check "…e sai 0 (mudo por desligamento, não por erro)" "$RC_G0" "0"
check "com SCOPE_COP_GATE=1 o deny segue negando (o gate não morreu)" \
  "$(printf '%s' "$(run_gate deny "gate1-$$" 1)" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)" "deny"

echo "── o cabeçalho não pode prometer pasta que o código não usa ──"
# HOOK_DIR deriva de ${CLAUDE_CONFIG_DIR:-$HOME/.claude}. Com a env var setada, modo,
# log e blockstreak NÃO moram em ~/.claude/guardrails — comentário que jura o
# contrário manda o leitor procurar a auditoria na pasta errada (e é o mesmo defeito
# silencioso que a linha 32 do hook existe pra evitar).
check "nenhuma menção hardcoded a ~/.claude/guardrails no fonte" \
  "$(grep -c '~/\.claude/guardrails' "$HOOK" | tr -d ' ')" "0"

echo "── anti-tautologia ──"
# Sabota o juiz falso pra devolver "pass" e exige que o modo warn fique MUDO. Sem
# isto, um hook que sempre falasse passaria nos checks de warn acima.
cat > "$TMP/bin/claude" <<'FAKE'
#!/bin/bash
echo '{"verdict":"pass","reason":"ok"}'
FAKE
chmod +x "$TMP/bin/claude"
check "com veredito pass o warn não avisa nada" "$(run warn "pass-$$")" ""

printf '── %d passou · %d falhou ──\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
