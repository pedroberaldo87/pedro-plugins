#!/bin/sh
# pretooluse-espera-com-guarda.sh — espera por processo em segundo plano só
# passa quando tem TETO e checagem de que o processo ainda vive.
#
# Por que existe: no /sovai o dono está ausente. Um comando que espera para
# sempre (`while ! grep ... ; do sleep 5; done`, `until [ -s saida ]`, `tail -f`)
# parece vivo enquanto o processo que ele espera já morreu — e morre calado.
# A missão fica pendurada horas sem ninguém por perto pra ver. A regra 7 do
# contrato de execução já dizia isso em prosa; prosa não recusa comando.
#
# A regra é uma só, e são duas condições, não uma:
#
#   TETO   — a espera tem um número de voltas ou um `timeout`, então ela ACABA
#            mesmo quando o que ela espera nunca chega.
#   VIVO   — a cada volta o comando confere que o processo ainda existe
#            (`kill -0`, `pgrep`, `ps -p`, `wait`), então ele percebe a morte
#            em vez de esperar um resultado que não vem mais.
#
# Falta UMA das duas ⇒ DENY. Teto sem checagem de vida ainda queima o teto
# inteiro esperando um morto; checagem de vida sem teto ainda pendura para
# sempre quando o processo trava vivo. As duas juntas, ou nenhuma serve.
#
# PreToolUse em Bash. Mudo em todo comando que não é espera.
#
# FAIL-OPEN em toda borda de infra (sem leitor de JSON, sem comando no payload):
# gate que trava a sessão por infra é pior que gate nenhum.

# Kill-switch (contrato dos hooks deste repo).
[ "${SOVAI_ESPERA:-1}" = "0" ] && exit 0

HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
# Sem como EMITIR a recusa não há recusa a fazer — libera.
type hj_deny >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "pretooluse-espera-com-guarda"; exit 0; }

INPUT=$(cat 2>/dev/null)
TOOL=$(hj_campo "$INPUT" tool_name)
[ "$TOOL" = "Bash" ] || exit 0

# ESCOPO — este gate só vale DENTRO de uma missão do /sovai. Fora dela o dono
# está na frente do terminal e um `tail -f app.log` dele é trabalho legítimo;
# recusar isso obrigaria o desligamento global SOVAI_ESPERA=0, que apagaria
# junto a proteção lá dentro. O sinal de missão ativa é o mesmo que o gate
# vizinho do mesmo evento consulta (pretooluse-sovai-motor.sh).
SESSION=$(hj_campo "$INPUT" session_id)
[ -n "$SESSION" ] || exit 0
# Estado mutável mora fora do plugin: ${CLAUDE_PLUGIN_ROOT} é cache reescrito a
# cada bump de versão.
[ -f "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai/ativo-$SESSION" ] || exit 0

CMD=$(hj_campo "$INPUT" tool_input.command)
[ -n "$CMD" ] || exit 0

# Uma linha só: o comando vem multilinha e todo casamento aqui é por trecho,
# não por linha — `while` numa linha e `sleep` na outra é a MESMA espera.
UMA=$(printf '%s' "$CMD" | tr '\n' ' ')

# 1 · isto é uma ESPERA? Duas formas, e só elas:
#     a) laço (`while`/`until`) que dorme entre as voltas
#     b) `tail -f`, que por construção não termina
EH_ESPERA=0
if printf '%s' "$UMA" | grep -Eq '(^|[;&|( ])(while|until)([ (]|$)' &&
   printf '%s' "$UMA" | grep -Eq '(^|[;&|( ])sleep[ ]'; then
  EH_ESPERA=1
fi
printf '%s' "$UMA" | grep -Eq '(^|[;&|( ])tail[ ].*-[a-zA-Z]*f' && EH_ESPERA=1

[ "$EH_ESPERA" = "1" ] || exit 0

# 2 · tem TETO? Contagem de voltas explícita, `seq`, ou um `timeout` por fora.
TEM_TETO=0
printf '%s' "$UMA" | grep -Eq '(^|[;&|( ])timeout[ ]' && TEM_TETO=1
printf '%s' "$UMA" | grep -Eq '(^|[;&|( ])seq[ ]' && TEM_TETO=1
printf '%s' "$UMA" | grep -Eq '\-(lt|le|gt|ge)[ ]' && TEM_TETO=1

# 3 · confere se o processo VIVE?
TEM_VIVO=0
printf '%s' "$UMA" | grep -Eq 'kill[ ]+-0|(^|[;&|( ])pgrep([ ]|$)|(^|[;&|( ])ps[ ]+-[a-zA-Z]*[po]|(^|[;&|( ])wait([ ]|$)|jobs[ ]+-r' && TEM_VIVO=1

[ "$TEM_TETO" = "1" ] && [ "$TEM_VIVO" = "1" ] && exit 0

FALTA=""
[ "$TEM_TETO" = "0" ] && FALTA="$FALTA
  ✗ TETO — nada limita o número de voltas, então esta espera pode não acabar."
[ "$TEM_VIVO" = "0" ] && FALTA="$FALTA
  ✗ VIVO — nada confere se o processo esperado ainda existe. Se ele morrer,
    você espera para sempre um resultado que não vem mais."

hj_deny "⛔ Esta espera não tem guarda.
$FALTA

Processo que morre em segundo plano NÃO avisa: a espera continua e PARECE viva.
Com o dono ausente, isso pendura a missão inteira sem ninguém por perto pra ver.

O caminho preferido é não esperar: rode a suíte/o build em PRIMEIRO PLANO e com
escopo. Se a espera for mesmo necessária, ela precisa das DUAS guardas juntas:

  for _ in \$(seq 1 60); do
    kill -0 \"\$PID\" 2>/dev/null || break   # o processo morreu: para agora
    [ -s saida.txt ] && break
    sleep 2
  done

Se este bloqueio estiver errado, o desligamento é SOVAI_ESPERA=0."
exit 0
