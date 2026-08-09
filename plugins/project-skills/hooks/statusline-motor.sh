#!/bin/sh
# statusline-motor.sh — a linha do motor ACIMA da barra, sem tirar nada dela.
#
# Por que existe: o narrador do andamento fala por `systemMessage`, que rola junto
# com a conversa. Quem volta ao terminal uma hora depois não vê nenhuma daquelas
# linhas — a barra de status é a única superfície que FICA, e até aqui ela não
# dizia se havia missão rodando.
#
# O QUE ELE É: mais um elo da cadeia da statusLine, no mesmo formato do
# `context-guard-writer.sh` — lê o payload no stdin, IMPRIME a linha do motor, e
# encaminha o payload INTACTO para quem desenha a barra. Como a linha do motor sai
# antes, ela aparece ACIMA; como o payload segue byte a byte, o que o renderizador
# desenha continua idêntico.
#
#   statusLine.command → context-guard-writer → statusline-motor → hud
#
# QUEM DESENHA A BARRA vem nos ARGUMENTOS deste script, nunca de
# CLAUDE_STATUSLINE_FORWARD: esse é o nome pelo qual ESTE script é chamado, e ler
# a própria variável faria a cadeia se chamar em círculo.
#
#   sh statusline-motor.sh "node .../hud/dist/index.js"
#
# O ESTADO É LIDO DO DISCO (`~/.claude/andamento/`, mais a pasta antiga
# `~/.claude/sovai/` enquanto houver missão viva lá), nunca perguntado a ninguém: quem
# renderiza a barra não tem acesso ao motor, e a barra é redesenhada a cada tecla.
# Sem `ativo-<sid>` não há motor vivo, a linha não sai, e a barra fica exatamente
# a que sempre foi.
#
# FAIL-OPEN em toda borda: erro nosso não pode apagar a barra do dono. Nada nosso
# vai para o stdout além da linha — stdout AQUI é a barra.

# Kill-switch (contrato dos hooks deste repo).
if [ "${SOVAI_STATUSLINE:-1}" = "0" ]; then
  [ -n "$*" ] && eval "$@"
  exit 0
fi

INPUT=$(cat 2>/dev/null)

HJ_DIR="${0%/*}"; [ "$HJ_DIR" = "$0" ] && HJ_DIR="."
# O `[ -f ]` antes do source não é zelo: em `sh` POSIX, dar source num arquivo que
# não existe ABORTA o script — e abortar aqui apagaria a barra inteira do dono por
# causa de um leitor de JSON ausente.
if [ -f "$HJ_DIR/hook-json.sh" ]; then
  # shellcheck source=/dev/null
  . "$HJ_DIR/hook-json.sh" 2>/dev/null
fi

if type hj_py >/dev/null 2>&1 && PY=$(hj_py 2>/dev/null); then
  # O módulo mora no plugin das skills de projeto, achado pelo NOME dele — nunca
  # pela posição no disco. Ausente = sem linha, e a barra segue intacta.
  RAIZ="${CLAUDE_PLUGIN_ROOT:-$(cd "$HJ_DIR/.." && pwd)}"
  ANDAMENTO_PY=$(CLAUDE_PLUGIN_ROOT="$RAIZ" bash "$HJ_DIR/resolve-plugin.sh" project-skills lib/andamento.py 2>/dev/null)
  [ -n "$ANDAMENTO_PY" ] || { [ -n "$*" ] && printf '%s' "$INPUT" | eval "$@"; exit 0; }
  LINHA=$(printf '%s' "$INPUT" | "$PY" -c '
import json, os, sys

sys.path.insert(0, os.path.dirname(sys.argv[1]))
import andamento

try:
    evento = json.loads(sys.stdin.read() or "{}")
except ValueError:
    raise SystemExit
linha = andamento.linha_motor(evento.get("session_id") or "")
if linha:
    sys.stdout.write(linha)
' "$ANDAMENTO_PY" 2>/dev/null)
  [ -n "$LINHA" ] && printf '%s\n' "$LINHA"
fi

# A barra, byte a byte como ela sempre foi.
[ -n "$*" ] && printf '%s' "$INPUT" | eval "$@"
exit 0
