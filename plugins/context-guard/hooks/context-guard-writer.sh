#!/bin/bash
# StatusLine middleware: extracts context% to a PER-SESSION state file, then forwards
# to the original statusLine command. Set CLAUDE_STATUSLINE_FORWARD to the original
# command (e.g. "node /path/to/hud/dist/index.js").
#
# ⚠️ PER-SESSION state (não global): o statusLine de QUALQUER sessão renderiza no mesmo
# host; um arquivo global (claude-context-pct, sem sufixo) era sobrescrito pela última sessão a
# renderizar, então uma sessão cheia (80%) fazia o guard bloquear TODAS as outras. O
# estado agora é <temporário>/claude-context-pct-<session_id> — cada sessão só lê o próprio %.
INPUT=$(cat)

# Leitor do payload: `jq` quando existe, `python3` (stdlib json) quando não.
# ⚠️ Aqui o stdout É a statusLine — o aviso de leitor ausente sai só pelo stderr,
# senão ele vira lixo escrito na barra do usuário.
# `${0%/*}` e não `dirname`: o probe roda antes de saber se há PATH utilizável.
HJ_SELF="$(printf '%s' "$0" | tr '\\' /)"   # \ -> / : no Windows $0 vem com barra invertida
HJ_DIR="${HJ_SELF%/*}"; [ "$HJ_DIR" = "$HJ_SELF" ] && HJ_DIR="."
# shellcheck source=/dev/null
. "$HJ_DIR/hook-json.sh" 2>/dev/null
# Diretório temporário DO SISTEMA — perguntado, nunca assumido (ver lib-tmpdir.sh).
# shellcheck source=/dev/null
. "$HJ_DIR/lib-tmpdir.sh" 2>/dev/null
TMPD=$(td_tmpdir 2>/dev/null || printf '%s' "${TMPDIR:-/tmp}")
if type hj_campo >/dev/null 2>&1 && hj_leitor >/dev/null 2>&1; then
  PCT=$(hj_campo "$INPUT" context_window.used_percentage)
  SID=$(hj_campo "$INPUT" session_id)
  # Sem session_id → não grava (fail-safe: guard sem arquivo da sessão = não dispara).
  [ -n "$PCT" ] && [ -n "$SID" ] && printf '%s' "$PCT" > "${TMPD}/claude-context-pct-${SID}"

  # ── o uso da JANELA DE 5H ────────────────────────────────────────────────
  # Mesmo payload, outro campo. Sem isto, decidir "parar antes de estourar o
  # limite" vira regra de três com o relógio: assume-se consumo proporcional ao
  # tempo decorrido, que é falso — uma hora de leitura e uma hora de fan-out
  # gastam ordens de grandeza diferentes.
  #
  # ⚠️ Estado GLOBAL de propósito, ao contrário do context% acima: a janela de 5h
  # é da CONTA, não da sessão. Toda sessão da máquina compartilha o mesmo teto, e
  # é isso que torna o número útil para quem for decidir parar.
  FIVE=$(hj_campo_json "$INPUT" five_hour)
  if [ -n "$FIVE" ] && [ "$FIVE" != "null" ]; then
    CG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/context-guard"
    mkdir -p "$CG_DIR" 2>/dev/null
    F_PCT=$(hj_campo "$INPUT" five_hour.used_percentage)
    [ -n "$F_PCT" ] || F_PCT=$(hj_campo "$INPUT" five_hour.utilization)
    [ -n "$F_PCT" ] || F_PCT="null"
    F_RESET=$(hj_campo "$INPUT" five_hour.resets_at)
    if [ -n "$F_RESET" ]; then F_RESET=$(hj_esc "$F_RESET"); else F_RESET="null"; fi
    printf '{"pct":%s,"resets_at":%s,"lido_em":"%s"}\n' \
      "$F_PCT" "$F_RESET" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      > "$CG_DIR/five-hour.json.tmp" 2>/dev/null \
      && mv -f "$CG_DIR/five-hour.json.tmp" "$CG_DIR/five-hour.json" 2>/dev/null
  fi
else
  printf '⚠️ context-guard-writer: sem jq nem python3 — não gravei o %% de contexto.\n' >&2
fi

if [ -n "$CLAUDE_STATUSLINE_FORWARD" ]; then
  printf '%s' "$INPUT" | eval "$CLAUDE_STATUSLINE_FORWARD"
fi
