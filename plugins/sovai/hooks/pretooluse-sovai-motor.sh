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
# ✅ MEDIDO em 2026-08-02 — o motor NÃO passa por aqui.
# Se a tool `Workflow` spawnasse os agentes dela pelo mesmo caminho de
# `PreToolUse(Agent)`, este gate mataria o próprio motor que ele existe pra
# proteger — e mataria numa missão longa, com o dono ausente, que é o cenário
# mais caro de todos. Era INFERIDO que não passa; hoje é CONFIRMADO:
#
#   com `ativo-<sid>` aceso, um Workflow de um agente completou — 11 chamadas
#   de ferramenta, 117s, e o contador `bloqueios-<sid>` NÃO se moveu (ficou na
#   única negação, que foi uma chamada manual deste hook feita pra medir).
#
# O cap FICA, e não por dúvida sobre isto: ele é o contrato anti-loop do repo
# (patterns.md §1.3), e cobre o caso de o runtime do Workflow mudar de caminho
# numa versão futura. Depois de MAX_BLOQUEIOS negações na mesma sessão o gate
# DESISTE e libera — a missão degrada em vez de travar. Gate que trava de
# verdade com o dono ausente é pior que gate nenhum.
#
# ⚠️ O QUE CONTINUA SEM REDE: sinal órfão. Não há poda por idade, e sessão que
# morre sem apagar `ativo-<sid>` fica sem despachar sub-agente até o fim. Medido
# na mesma rodada: 3 sinais acesos, 2 de sessões de OUTROS projetos ainda vivas.
# O sinal é por sessão, então uma não contamina a outra — o estrago é local.

# Kill-switch (contrato dos hooks deste repo): quando o gate atrapalha num
# momento ruim, a saída não pode ser editar o script.
[ "${SOVAI_GATE:-1}" = "0" ] && exit 0

# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# Sem os dois o gate não julga — e aí ele AVISA, nunca sai calado (issue #5).
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
type hj_campo >/dev/null 2>&1 || exit 0
hj_leitor >/dev/null 2>&1 || { hj_avisa "pretooluse-sovai-motor"; exit 0; }

INPUT=$(cat 2>/dev/null)
TOOL=$(hj_campo "$INPUT" tool_name)
SESSION=$(hj_campo "$INPUT" session_id)

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

hj_deny "$RAZAO"
exit 0
