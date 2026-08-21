#!/bin/bash
# PostToolUse hook: quando o contexto DESTA sessão passa do threshold, DISPARA o handoff.
# Lê context% de <temporário>/claude-context-pct-<session_id> (escrito pelo wrapper de statusLine
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
# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "context-guard"; exit 0; }
# Diretório temporário DO SISTEMA — perguntado, nunca assumido (ver lib-tmpdir.sh).
# shellcheck source=/dev/null
. "$HJ_DIR/lib-tmpdir.sh" 2>/dev/null
TMPD=$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
MODE_FILE="${HOME}/.claude/context-guard/mode"
[ -f "$MODE_FILE" ] && [ "$(tr -d '[:space:]' < "$MODE_FILE" 2>/dev/null)" = "off" ] && exit 0

THRESHOLD="${CLAUDE_CONTEXT_THRESHOLD:-80}"

INPUT=$(cat)
# session_id chaveia TANTO o estado quanto o sentinel por sessão.
SESSION_ID=$(hj_campo_ou "$INPUT" session_id "")
# payload sem sessão: liberado — o sentinela "unknown" seria compartilhado entre sessões (o defeito do context-guard v1.1)
[ -n "$SESSION_ID" ] || exit 0
STATE="${TMPD}/claude-context-pct-${SESSION_ID}"
SENTINEL="${TMPD}/claude-context-warned-${SESSION_ID}"

[ -f "$SENTINEL" ] && exit 0

# Já no meio de um handoff? Então NÃO interrompe. Marca o sentinel (a missão do guard —
# provocar um handoff — já está sendo cumprida) e sai. Sinal: a chamada de tool menciona
# "handoff" (Skill tool com skill=handoff, ou qualquer tool tocando um arquivo HANDOFF).
# Detecção liberal de propósito: um falso-positivo só cala o guard (nag), nunca bloqueia.
if printf '%s' "$(hj_campo_json "$INPUT" tool_input)" | grep -qi 'handoff'; then
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
