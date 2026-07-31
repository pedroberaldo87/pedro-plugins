#!/bin/bash
# PostToolUse hook: quando o contexto DESTA sessão passa do threshold, DISPARA o handoff.
# Lê context% de /tmp/claude-context-pct-<session_id> (escrito pelo wrapper de statusLine
# da mesma sessão). Dispara uma vez por sessão — sentinel por-sessão evita repetição.
#
# Regra do gate (v1.3.0): se já estamos NO MEIO de um handoff, não interrompe — deixa o
# handoff terminar. Senão, instrui o Claude a rodar o /handoff agora. Usa decision:block
# (alimenta o reason de volta pro modelo → ele EXECUTA o handoff) em vez de continue:false
# (que só parava tudo e obrigava o usuário a digitar /handoff na mão).
#
# Kill-switch: crie ~/.claude/context-guard/mode com "off" pra desligar o guard globalmente
# (sem editar settings nem reload). Espelha o scope-cop do guardrails.
# Sem jq não dá pra ler o session_id — o guard leria contexto da sessão errada.
command -v jq >/dev/null 2>&1 || exit 0
MODE_FILE="${HOME}/.claude/context-guard/mode"
[ -f "$MODE_FILE" ] && [ "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" = "off" ] && exit 0

THRESHOLD="${CLAUDE_CONTEXT_THRESHOLD:-80}"

INPUT=$(cat)
# session_id chaveia TANTO o estado quanto o sentinel por sessão.
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
STATE="/tmp/claude-context-pct-${SESSION_ID}"
SENTINEL="/tmp/claude-context-warned-${SESSION_ID}"

[ -f "$SENTINEL" ] && exit 0

# Já no meio de um handoff? Então NÃO interrompe. Marca o sentinel (a missão do guard —
# provocar um handoff — já está sendo cumprida) e sai. Sinal: a chamada de tool menciona
# "handoff" (Skill tool com skill=handoff, ou qualquer tool tocando um arquivo HANDOFF).
# Detecção liberal de propósito: um falso-positivo só cala o guard (nag), nunca bloqueia.
if printf '%s' "$INPUT" | jq -e '(.tool_input // {} | tostring) | test("handoff"; "i")' >/dev/null 2>&1; then
  touch "$SENTINEL"
  exit 0
fi

PCT=$(cat "$STATE" 2>/dev/null)
[ -z "$PCT" ] && exit 0

PCT_INT="${PCT%.*}"

if [ "$PCT_INT" -ge "$THRESHOLD" ] 2>/dev/null; then
  touch "$SENTINEL"
  printf '{"decision":"block","reason":"⚠️ CONTEXTO EM %s%%. Rode o /handoff AGORA (skill handoff, modo SALVAR) pra preservar a sessão antes de continuar o trabalho."}\n' "$PCT_INT"
fi
