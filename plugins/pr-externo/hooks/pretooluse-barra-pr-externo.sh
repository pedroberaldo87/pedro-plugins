#!/bin/bash
# PreToolUse(Bash): barra a abertura de pull request em repositório de TERCEIRO
# enquanto o dossiê do pr-externo tiver portão fechado.
#
# Só age em comando que pode abrir PR; todo o resto sai em silêncio. Quem julga é o
# motor (lib/pr_externo.py hook), que devolve: 0 segue · 2 barra · 3 pede confirmação.
# Qualquer outro código (o motor quebrou) vira PEDIDO DE CONFIRMAÇÃO ao usuário:
# a trava nunca libera calada o que não conseguiu julgar.
#
# Sem python3 o gate não julga — e AVISA, nunca sai calado.
# Kill-switch: PR_EXTERNO_GATE=0 no ambiente da sessão (quem desliga é o usuário;
# prefixo no próprio comando não chega aqui).
[ "${PR_EXTERNO_GATE:-1}" = "0" ] && exit 0

EU="$(printf '%s' "$0" | tr '\\' /)"
DIR="${EU%/*}"; [ "$DIR" = "$EU" ] && DIR="."

ENTRADA=$(cat)
case "$ENTRADA" in
  *pr*create*|*pr*new*|*pulls*|*pull-request*) ;;
  *) exit 0 ;;
esac

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "⚠️ pr-externo: sem python3, a trava de PR para repositório de terceiro NÃO rodou." >&2
  exit 0
fi

pergunta() { # texto -> entrega a decisão ao usuário, na tela
  printf '%s' "$1" | "$PY" -c 'import json,sys; print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":sys.stdin.read().strip()[:1500]}}, ensure_ascii=False))'
  exit 0
}

MOTIVO=$(printf '%s' "$ENTRADA" | "$PY" "$DIR/../lib/pr_externo.py" hook 2>&1 >/dev/null)
COD=$?
[ "$COD" = "0" ] && exit 0
[ "$COD" = "3" ] && pergunta "$MOTIVO"
[ "$COD" = "2" ] || pergunta "pr-externo: a trava falhou ao julgar este comando (código $COD), e ele pode abrir um PR em repositório de terceiro. $MOTIVO"

# Teto de devoluções, por sessão e por motivo: a trava não pode prender o agente num
# laço de tentativas. Passado o teto ela para de barrar e ENTREGA A DECISÃO AO USUÁRIO,
# com o motivo — nunca libera calada. Motivo novo (outro portão, outro PR) zera a conta.
MAX_BLOQUEIOS=2
SESSION_ID=$(printf '%s' "$ENTRADA" | "$PY" -c 'import json,re,sys; print(re.sub(r"[^A-Za-z0-9_-]", "", str(json.load(sys.stdin).get("session_id", "")))[:64])' 2>/dev/null)
CHAVE=$(printf '%s' "$MOTIVO" | cksum | tr -c '0-9' '_')
COUNT_FILE="${TMPDIR:-/tmp}/pr-externo-${SESSION_ID:-sem-sessao}-${CHAVE}.count"
COUNT=$(cat "$COUNT_FILE" 2>/dev/null || echo 0)
case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
if [ "$COUNT" -ge "$MAX_BLOQUEIOS" ]; then
  pergunta "Já barrei este PR $COUNT vezes nesta sessão pelo mesmo motivo; agora a decisão é sua. $MOTIVO"
  exit 0
fi
echo $((COUNT + 1)) > "$COUNT_FILE" 2>/dev/null
printf '%s\n' "$MOTIVO" >&2
exit 2
