#!/bin/bash
# pretooluse-sovai-motor.sh — no /sovai o motor é Workflow, e só ele.
#
# PreToolUse em Agent. Nega o disparo de sub-agente ENQUANTO o /sovai estiver
# armado, e é mudo fora dele.
#
# Por que existe: a SKILL.md do sovai dizia que "o guard PreToolUse(Agent)
# acorda a cada disparo" — e não acordava. O guard que existe é o do
# `guardrails`, e ele foi escrito pra PROTEGER Agent Teams: a regra 3 dele
# libera explicitamente "tarefa one-off sem team_name", que é exatamente a
# forma pela qual o sovai descambava. A skill se apoiava numa proteção que
# não existia — prosa descrevendo mecanismo ausente.
#
# Duas saídas, e a diferença entre elas é um arquivo:
#
#   A) sinal ausente  -> exit 0, mudo. Não é sovai; sub-agente aqui é assunto
#      do guard do guardrails, não deste.
#   B) sinal presente -> DENY, mandando rodar a tool Workflow.
#
# O sinal é por SESSÃO (`ativo-<session_id>`): o marcador global era o defeito
# que já mordeu o context-guard e o scope-cop — uma sessão em sovai faria toda
# sessão paralela perder o direito de despachar sub-agente.
#
# FAIL-OPEN em toda borda de infra (sem jq, sem session_id, sem raiz de estado):
# gate que trava a sessão por infra é pior que gate nenhum.
#
# ⚠️ O QUE AINDA NÃO FOI MEDIDO, e a rede que cobre isso.
# Se a tool `Workflow` spawnasse os agentes dela pelo mesmo caminho de
# `PreToolUse(Agent)`, este gate mataria o próprio motor que ele existe pra
# proteger — e mataria numa missão longa, com o dono ausente, que é o cenário
# mais caro de todos. É INFERIDO que não passa (o script do motor abre agente
# com `agent()`, do runtime do Workflow), NÃO confirmado: o hook nasceu nesta
# sessão e hook novo só vale depois de reinstalar o plugin.
#
# Por isso o cap, que é o contrato anti-loop do repo (patterns.md §1.3): depois
# de MAX_BLOQUEIOS negações na mesma sessão o gate DESISTE e libera. Se a
# inferência estiver errada, a missão degrada em vez de travar. Gate que trava
# de verdade com o dono ausente é pior que gate nenhum.
#
# Para confirmar e então poder apertar: com o sinal ligado, rode um Workflow de
# um agente só e veja se ele completa. Completou → a inferência valia.

# Kill-switch (contrato dos hooks deste repo): quando o gate atrapalha num
# momento ruim, a saída não pode ser editar o script.
[ "${SOVAI_GATE:-1}" = "0" ] && exit 0

command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)

[ "$TOOL" = "Agent" ] || exit 0
[ -n "$SESSION" ] || exit 0          # sem sessão não há sinal a consultar

# Estado mutável mora fora do plugin: ${CLAUDE_PLUGIN_ROOT} é cache reescrito a
# cada bump de versão. Mesma raiz que os outros plugins do marketplace usam.
ESTADO="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/sovai"
SINAL="$ESTADO/ativo-$SESSION"

[ -f "$SINAL" ] || exit 0

# Cap: o gate degrada, nunca trava. Contador por sessão, no mesmo diretório de
# estado — e sanitizado, porque lixo no arquivo não pode virar erro de shell.
MAX_BLOQUEIOS=3
CONTA="$ESTADO/bloqueios-$SESSION"
N=0
[ -f "$CONTA" ] && N=$(cat "$CONTA" 2>/dev/null)
[ "$N" -eq "$N" ] 2>/dev/null || N=0
if [ "$N" -ge "$MAX_BLOQUEIOS" ]; then
  # Desistir não pode ser silencioso (patterns.md §1.3): deixa rastro.
  printf '%s desistiu apos %s bloqueios · sessao=%s\n' \
    "$(date -u +%FT%TZ)" "$MAX_BLOQUEIOS" "$SESSION" >> "$ESTADO/desistencias.log" 2>/dev/null
  exit 0
fi
printf '%s' "$((N + 1))" > "$CONTA" 2>/dev/null

RAZAO='⛔ No /sovai o motor é Workflow, não sub-agente.

Esta missão está em modo sovai, e nele a execução roda como um Workflow
determinístico — os freios (parada, paralelismo, fidelidade ao plano) são
lógica do script, não "lembrar a regra a cada volta".

Dispare a tool Workflow com o script de decompõe→executa→revisa que está em
skills/sovai/SKILL.md, seção "Execução". Agent Teams também não serve aqui:
o pipeline é fechado.

Se este bloqueio estiver errado, o desligamento é SOVAI_GATE=0.'

jq -n --arg r "$RAZAO" \
  '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",permissionDecisionReason:$r}}'
exit 0
