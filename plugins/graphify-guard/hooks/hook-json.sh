#!/bin/sh
# hook-json.sh — ler o payload do evento e escrever a decisão SEM exigir `jq`.
#
# Por que existe: o campo que DECIDE (session_id, tool_input.command,
# stop_hook_active) só era legível com `jq`. Em máquina sem `jq` o gate saía 0
# antes de olhar o payload — para o harness isso é indistinguível de "o gate
# rodou e liberou". O inventário está em `jq-pontos-de-decisao.md`, na casa da doc.
#
# Ordem: `jq` quando existe (é o caminho já testado e mais rápido), senão o
# `python3` que todo motor deste marketplace já exige. Sem os dois, quem chama
# usa `hj_avisa` — a regra é FALAR, nunca calar.
#
# CAMINHO: pontuado, com índice de lista como mais um segmento —
# `tool_input.command`, `hits.0.id`. Vale nos dois motores.
#
# ⚠️ Fonte da verdade: `_shared/hook-json.sh`. As cópias em `plugins/*/hooks/`
# são vendoradas por `scripts/sync-shared.sh` — nunca edite a cópia.

HJ_PY=""

# hj_py — caminho de um python3 que EXECUTA (existir no PATH não basta: no
# Windows o stub da Store existe e não roda). Vazio + status 1 se não há.
hj_py() {
  if [ -n "$HJ_PY" ]; then printf '%s' "$HJ_PY"; return 0; fi
  for _hj_c in python3 python; do
    _hj_p=$(command -v "$_hj_c" 2>/dev/null) || _hj_p=""
    if [ -n "$_hj_p" ] && "$_hj_p" --version >/dev/null 2>&1; then HJ_PY="$_hj_p"; break; fi
  done
  [ -n "$HJ_PY" ] || return 1
  printf '%s' "$HJ_PY"
}

# hj_leitor — qual leitor de JSON está disponível (`jq` ou `python3`); 1 se nenhum.
hj_leitor() {
  if command -v jq >/dev/null 2>&1; then printf 'jq'; return 0; fi
  if hj_py >/dev/null 2>&1; then printf 'python3'; return 0; fi
  return 1
}

# _hj_jq SUFIXO — o programa jq que desce o caminho recebido em `--arg p`.
# `getpath` (e não `.a.b`) porque é ele que aceita índice de lista vindo como texto.
_hj_jq() {
  printf 'getpath($p | split(".") | map(if test("^[0-9]+$") then tonumber else . end))%s' "$1"
}

# O trecho de python que desce o mesmo caminho, compartilhado pelos leitores.
HJ_DESCE='import json,sys
try:
    d = json.loads(sys.stdin.read() or "{}")
except Exception:
    sys.exit(0)
for k in sys.argv[1].split("."):
    if isinstance(d, dict):
        d = d.get(k)
    elif isinstance(d, list) and k.isdigit() and int(k) < len(d):
        d = d[int(k)]
    else:
        d = None
'

# hj_campo PAYLOAD CAMINHO — o valor de um campo. Mesma semântica de
# `jq -r '.X // empty'`: ausente, nulo ou `false` devolvem vazio.
hj_campo() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -r --arg p "$2" "$(_hj_jq ' // empty')" 2>/dev/null
    return 0
  fi
  _hj_py=$(hj_py) || return 1
  printf '%s' "$1" | "$_hj_py" -c "$HJ_DESCE"'
if d is None or d is False:
    out = ""
elif d is True:
    out = "true"
elif isinstance(d, str):
    out = d
else:
    out = json.dumps(d, ensure_ascii=False)
sys.stdout.write(out)' "$2" 2>/dev/null
}

# hj_campo_ou PAYLOAD CAMINHO PADRAO — o mesmo, com valor de reserva quando o
# campo vem vazio (o `jq -r '.X // "unknown"'`).
hj_campo_ou() {
  _hj_v=$(hj_campo "$1" "$2") || return 1
  [ -n "$_hj_v" ] || _hj_v="$3"
  printf '%s' "$_hj_v"
}

# hj_eh_falso PAYLOAD CAMINHO — status 0 quando o campo é o booleano `false`.
# Existe porque `hj_campo` (como o `// empty` do jq) devolve vazio tanto para
# ausente quanto para `false`, e há gate em que os dois significam o oposto.
hj_eh_falso() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -e --arg p "$2" "$(_hj_jq ' == false')" >/dev/null 2>&1
    return $?
  fi
  _hj_py=$(hj_py) || return 1
  printf '%s' "$1" | "$_hj_py" -c "$HJ_DESCE"'
sys.exit(0 if d is False else 1)' "$2" 2>/dev/null
}

# hj_campo_json PAYLOAD CAMINHO — o valor como JSON compacto (o `jq -c '.X'`).
hj_campo_json() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -c --arg p "$2" "$(_hj_jq ' // empty')" 2>/dev/null
    return 0
  fi
  _hj_py=$(hj_py) || return 1
  printf '%s' "$1" | "$_hj_py" -c "$HJ_DESCE"'
if d is None or d is False:
    sys.exit(0)
sys.stdout.write(json.dumps(d, separators=(",", ":"), ensure_ascii=False))' "$2" 2>/dev/null
}

# hj_tamanho PAYLOAD CAMINHO — quantos itens tem a lista (ou chaves o objeto).
# Vazio ou ausente devolve 0.
hj_tamanho() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -r --arg p "$2" "$(_hj_jq ' | if . == null then 0 else length end')" 2>/dev/null
    return 0
  fi
  _hj_py=$(hj_py) || return 1
  printf '%s' "$1" | "$_hj_py" -c "$HJ_DESCE"'
sys.stdout.write(str(len(d)) if isinstance(d, (list, dict, str)) else "0")' "$2" 2>/dev/null
}

# hj_itens PAYLOAD CAMINHO — cada item da lista em uma linha, JSON compacto
# (o `jq -c ".X[]?"`, que é o formato que os motores em python consomem).
hj_itens() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -c --arg p "$2" "$(_hj_jq '[]?')" 2>/dev/null
    return 0
  fi
  _hj_py=$(hj_py) || return 1
  printf '%s' "$1" | "$_hj_py" -c "$HJ_DESCE"'
for it in (d if isinstance(d, list) else []):
    sys.stdout.write(json.dumps(it, separators=(",", ":"), ensure_ascii=False) + "\n")' "$2" 2>/dev/null
}

# hj_lista PAYLOAD CAMINHO — os itens de uma lista de textos juntados por
# vírgula (o `join(", ")` do jq).
hj_lista() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -r --arg p "$2" "$(_hj_jq ' | if . == null then "" else map(tostring) | join(", ") end')" 2>/dev/null
    return 0
  fi
  _hj_py=$(hj_py) || return 1
  printf '%s' "$1" | "$_hj_py" -c "$HJ_DESCE"'
sys.stdout.write(", ".join(str(x) for x in d) if isinstance(d, list) else "")' "$2" 2>/dev/null
}

# Os formatos de saída de hook, montados sem `jq -n`. Decidir sem poder EMITIR a
# decisão seria fallback pela metade.
# hj_esc TEXTO — o texto virado string JSON, com as aspas (o `--arg` do `jq`).
hj_esc() {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$1" | jq -Rs . 2>/dev/null
    return 0
  fi
  _hj_py=$(hj_py) || return 1
  printf '%s' "$1" | "$_hj_py" -c 'import json,sys
sys.stdout.write(json.dumps(sys.stdin.read(), ensure_ascii=False))' 2>/dev/null
}

# hj_deny MOTIVO — o bloqueio do PreToolUse.
hj_deny() {
  _hj_r=$(hj_esc "$1") || return 1
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":%s}}\n' "$_hj_r"
}

# hj_ctx EVENTO TEXTO — contexto para o modelo, sem bloquear.
hj_ctx() {
  _hj_r=$(hj_esc "$2") || return 1
  printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":%s}}\n' "$1" "$_hj_r"
}

# hj_msg TEXTO — recado ao usuário.
hj_msg() {
  _hj_r=$(hj_esc "$1") || return 1
  printf '{"systemMessage":%s}\n' "$_hj_r"
}

# hj_msg_ctx EVENTO TEXTO — o mesmo texto para os dois públicos: o usuário
# (systemMessage) e o modelo (additionalContext).
hj_msg_ctx() {
  _hj_r=$(hj_esc "$2") || return 1
  printf '{"systemMessage":%s,"hookSpecificOutput":{"hookEventName":"%s","additionalContext":%s}}\n' \
    "$_hj_r" "$1" "$_hj_r"
}

# hj_block MOTIVO — o bloqueio de Stop / PostToolUse (o canal `decision`).
hj_block() {
  _hj_r=$(hj_esc "$1") || return 1
  printf '{"decision":"block","reason":%s}\n' "$_hj_r"
}

# hj_avisa NOME — sem `jq` E sem `python3` não há como ler o evento. Sair calado
# aqui é o defeito que este arquivo existe para corrigir: o gate tem que dizer
# que não julgou.
hj_avisa() {
  printf '⚠️ %s: sem jq nem python3 — não li o evento e não decidi.\n' "$1" >&2
  printf '{"systemMessage":"⚠️ %s: sem jq nem python3 — o gate não decidiu."}\n' "$1"
}
