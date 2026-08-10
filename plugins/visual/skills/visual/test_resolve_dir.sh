#!/bin/bash
# test_resolve_dir.sh — a reserva do resolve-dir.sh é POR PASTA, e ela se anuncia.
#
# Dois fatos, um teste cada:
#   1. duas pastas sem marcador de projeto resolvem para destinos DIFERENTES
#      (e a mesma pasta resolve sempre pro mesmo destino — nada de data/sorteio);
#   2. quando o destino veio da reserva, o aviso chega por um canal que quem
#      chama NÃO descarta — o código de saída 3. Os quatro consumidores do
#      script chamam com `2>/dev/null`, então aviso só no stderr é aviso no
#      vazio; o teste do stderr fica, mas ele é o texto, não o sinal. O stdout
#      continua sendo UM caminho absoluto, que é o contrato de quem chama.
#   3. o consumidor de verdade repassa o aviso: o hook sessionstart-plan.sh
#      põe a ressalva no `additionalContext`, que é o texto que o modelo lê.
#
# Uso: bash plugins/visual/skills/visual/test_resolve_dir.sh

set -u
SCRIPT="$(cd "$(dirname "$0")" && pwd)/resolve-dir.sh"
FALHAS=0

ok()   { printf '  ok   %s\n' "$1"; }
falha() { printf '  FALHA %s\n     %s\n' "$1" "$2"; FALHAS=$((FALHAS + 1)); }

BASE=$(mktemp -d)
trap 'rm -rf "$BASE"' EXIT
export HOME="$BASE/home"
mkdir -p "$HOME/Desktop" "$BASE/solto/site-do-cliente" "$BASE/solto/outro-projeto"

# roda o script isolando stdout de stderr
OUT_A=$(bash "$SCRIPT" "$BASE/solto/site-do-cliente" plans 2>"$BASE/err-a")
ERR_A=$(cat "$BASE/err-a")
OUT_B=$(bash "$SCRIPT" "$BASE/solto/outro-projeto" plans 2>/dev/null)
OUT_A2=$(bash "$SCRIPT" "$BASE/solto/site-do-cliente" plans 2>/dev/null)

echo "== reserva por pasta =="
if [ "$OUT_A" != "$OUT_B" ]; then
  ok "duas pastas sem marcador → destinos diferentes ($OUT_A ≠ $OUT_B)"
else
  falha "duas pastas sem marcador caem no MESMO destino" "ambas → $OUT_A"
fi

if [ "$OUT_A" = "$OUT_A2" ]; then
  ok "a mesma pasta resolve sempre pro mesmo destino"
else
  falha "destino instável para a mesma pasta" "$OUT_A vs $OUT_A2"
fi

case "$OUT_A" in
  /*) ok "stdout é um caminho absoluto (contrato de quem chama)" ;;
  *)  falha "stdout não é caminho absoluto" "$OUT_A" ;;
esac

if [ "$(printf '%s' "$OUT_A" | wc -l | tr -d ' ')" = "0" ] && [ -d "$OUT_A" ]; then
  ok "stdout é UMA linha só e o diretório foi criado"
else
  falha "stdout com mais de uma linha, ou diretório não criado" "$OUT_A"
fi

echo "== o canal do aviso (o que sobrevive ao 2>/dev/null de quem chama) =="
# Descartar o stderr EXATAMENTE como os quatro consumidores fazem. Se o único
# aviso fosse o texto do stderr, aqui não sobraria nada — e é esse o defeito.
bash "$SCRIPT" "$BASE/solto/site-do-cliente" plans >/dev/null 2>/dev/null
COD_RESERVA=$?
if [ "$COD_RESERVA" = "3" ]; then
  ok "reserva sai com código 3 mesmo com o stderr descartado"
else
  falha "sem sinal de reserva depois do 2>/dev/null" "código de saída: $COD_RESERVA"
fi

echo "== o texto do aviso =="
case "$ERR_A" in
  *RESERVA*) ok "o aviso diz que o resultado veio da reserva" ;;
  *) falha "sem aviso de reserva no stderr" "stderr: [${ERR_A}]" ;;
esac

case "$ERR_A" in
  *"$BASE/solto/site-do-cliente"*) ok "o aviso nomeia a pasta de origem" ;;
  *) falha "o aviso não diz de qual pasta veio" "stderr: [${ERR_A}]" ;;
esac

echo "== projeto de verdade não aciona a reserva =="
mkdir -p "$BASE/projeto"
: > "$BASE/projeto/CLAUDE.md"
OUT_P=$(bash "$SCRIPT" "$BASE/projeto" plans 2>"$BASE/err-p")
if [ "$OUT_P" = "$BASE/projeto/.claude/plans" ]; then
  ok "marcador de projeto continua vencendo (nível 2 intacto)"
else
  falha "nível 2 mudou de comportamento" "esperado $BASE/projeto/.claude/plans, veio $OUT_P"
fi
if [ ! -s "$BASE/err-p" ]; then
  ok "projeto reconhecido não emite aviso de reserva"
else
  falha "aviso de reserva em projeto reconhecido" "$(cat "$BASE/err-p")"
fi
bash "$SCRIPT" "$BASE/projeto" plans >/dev/null 2>/dev/null
COD_PROJ=$?
if [ "$COD_PROJ" = "0" ]; then
  ok "projeto reconhecido sai com código 0"
else
  falha "projeto reconhecido saiu com código de reserva" "código: $COD_PROJ"
fi

# ── o consumidor de verdade ─────────────────────────────────────────────────
# Peça que ninguém invoca não cumpre critério nenhum: aqui roda o HOOK, com o
# payload que o harness manda, e se confere que a ressalva chegou no texto que o
# modelo lê (`additionalContext`). É por este caminho que o aviso vale.
echo "== o consumidor repassa o aviso (sessionstart-plan.sh) =="
# O HOOK É PROCURADO POR NOME, NUNCA PELA POSIÇÃO. Ele morava em
# plugins/visual/hooks/ e mudou para project-skills na fusão da família (1f575e9);
# o caminho relativo daqui ficou apontando a pasta velha e este bloco passou a
# reprovar em SILÊNCIO — a suíte inteira do repositório ficou vermelha por isso,
# e o vermelho só apareceu quando o motor do /sprint enumerou os testes por
# comando. É o mesmo defeito que o F14.2 já tinha cobrado uma vez.
_REPO="$(cd "$(dirname "$0")/../../../.." && pwd)"
HOOK="$(find "$_REPO/plugins" -name sessionstart-plan.sh -type f 2>/dev/null | head -1)"
PLAN_STATE="$(find "$_REPO/plugins" -path '*/lib/plan_state.py' -type f 2>/dev/null | head -1)"  # acopla-ok: teste roda no monorepo, não na máquina de quem instala
if [ ! -f "$HOOK" ] || [ ! -f "$PLAN_STATE" ] || ! command -v python3 >/dev/null 2>&1; then
  falha "hook ou plan_state.py ausente" "$HOOK / $PLAN_STATE"
else
  RESERVA_DIR=$(bash "$SCRIPT" "$BASE/solto/site-do-cliente" plans 2>/dev/null)
  cat > "$BASE/p.json" <<'JSON'
{"id": "plano-de-fora", "title": "Plano de fora",
 "requisitos": [{"id": "S-1", "titulo": "o usuário sabe de onde veio o plano",
                 "ca": "a ressalva aparece no contexto", "epico": "E1 — Origem"}],
 "phases": [{"id": "F1", "title": "Fase um", "items": [
   {"id": "F1.1", "title": "passo um", "desc": "um passo qualquer, só pra haver plano aberto",
    "pronto": "quando o teste ler o contexto do hook", "requisito": "S-1"}]}]}
JSON
  python3 "$PLAN_STATE" --dir "$RESERVA_DIR" init --file "$BASE/p.json" >/dev/null 2>&1
  CTX_OUT=$(printf '{"session_id":"tst-reserva","cwd":"%s"}' "$BASE/solto/site-do-cliente" \
            | bash "$HOOK" 2>/dev/null)
  case "$CTX_OUT" in
    *RESERVA*) ok "a ressalva da reserva chegou no additionalContext do hook" ;;
    *) falha "o hook mostrou o plano sem dizer que ele veio da reserva" "saída: [${CTX_OUT}]" ;;
  esac

  # E o contrário: em projeto de verdade, nada de ressalva — aviso que sempre
  # aparece vira ruído e o leitor aprende a pular.
  python3 "$PLAN_STATE" --dir "$BASE/projeto/.claude/plans" init --file "$BASE/p.json" >/dev/null 2>&1
  CTX_P=$(printf '{"session_id":"tst-projeto","cwd":"%s"}' "$BASE/projeto" | bash "$HOOK" 2>/dev/null)
  case "$CTX_P" in
    *RESERVA*) falha "ressalva de reserva em projeto reconhecido" "saída: [${CTX_P}]" ;;
    *plano*|*Plano*) ok "em projeto reconhecido o hook mostra o plano sem ressalva" ;;
    *) falha "o hook não emitiu o plano do projeto reconhecido" "saída: [${CTX_P}]" ;;
  esac
fi

echo
if [ "$FALHAS" -eq 0 ]; then
  echo "TODOS OS TESTES PASSARAM"
  exit 0
fi
echo "$FALHAS teste(s) falharam"
exit 1
