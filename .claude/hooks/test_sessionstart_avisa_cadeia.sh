#!/bin/bash
# Suíte do aviso de código velho. O caso central reproduz a falha de 2026-08-09:
# o repositório em 0.4.0 e a máquina rodando 0.3.2, sem nada acusar.
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
HOOK="$AQUI/sessionstart-avisa-cadeia.sh"
RAIZ_REPO="$(cd "$AQUI/../.." && pwd)"
FALHAS=0
ok()  { printf '  ok   %s\n' "$1"; }
bad() { printf '  FAIL %s\n' "$1"; FALHAS=$((FALHAS+1)); }

LAB=$(mktemp -d)
# Um repositório de mentira, com o mesmo formato do de verdade.
mkdir -p "$LAB/repo/plugins/alfa/.claude-plugin" "$LAB/repo/.claude-plugin" \
         "$LAB/repo/scripts" "$LAB/repo/_shared" "$LAB/casa/plugins"
cp "$RAIZ_REPO/scripts/cadeia_check.py" "$LAB/repo/scripts/"
cp "$RAIZ_REPO/_shared/hook-json.sh" "$LAB/repo/_shared/"
printf '{"name":"alfa","version":"0.4.0"}' > "$LAB/repo/plugins/alfa/.claude-plugin/plugin.json"
printf '{"plugins":[{"name":"alfa","version":"0.4.0"}]}' > "$LAB/repo/.claude-plugin/marketplace.json"
velha() {
  printf '{"repos":{"alfa@pedro-plugins":[{"installPath":"/c/alfa/%s"}]}}' "$1" \
    > "$LAB/casa/plugins/installed_plugins.json"
}
roda() {
  printf '{"session_id":"%s"}' "$1" | \
    CLAUDE_PROJECT_DIR="$LAB/repo" CLAUDE_CONFIG_DIR="$LAB/casa" TMPDIR="$LAB/tmp" \
    bash "$HOOK" 2>&1
}
mkdir -p "$LAB/tmp"

echo "A FALHA DE ORIGEM — repositório em 0.4.0, máquina rodando 0.3.2"
velha "0.3.2"
SAIDA=$(roda "s1")
case "$SAIDA" in
  *"código VELHO"*) ok "o arranque avisa" ;;
  *)                bad "o arranque avisa (veio: ${SAIDA:0:70})" ;;
esac
case "$SAIDA" in
  *0.3.2*0.4.0*|*0.4.0*0.3.2*) ok "e o aviso traz as duas versões" ;;
  *)                           bad "e o aviso traz as duas versões" ;;
esac
case "$SAIDA" in
  *systemMessage*) ok "e chega ao DONO, não só ao modelo" ;;
  *)               bad "e chega ao dono (systemMessage)" ;;
esac

# O aviso não pode morrer com o leitor de JSON: sem ele o recado vai pro stderr, que
# o harness mostra. Emudecer aqui reproduziria o defeito que o hook existe pra evitar.
rm -f "$LAB/tmp/cadeia-avisou-s1b" 2>/dev/null
mv "$LAB/repo/_shared/hook-json.sh" "$LAB/hook-json.guardado"
SAIDA=$(roda "s1b")
case "$SAIDA" in
  *"código VELHO"*) ok "e sem o leitor de JSON ele ainda fala, pelo stderr" ;;
  *)                bad "sem o leitor de JSON ele emudece" ;;
esac
mv "$LAB/hook-json.guardado" "$LAB/repo/_shared/hook-json.sh"

echo
echo "UMA VEZ POR SESSÃO — aviso repetido a cada arranque vira ruído"
SAIDA=$(roda "s1")
[ -z "$SAIDA" ] && ok "a segunda chamada da MESMA sessão é muda" \
                || bad "a segunda chamada é muda (veio: ${SAIDA:0:50})"
SAIDA=$(roda "s2")
case "$SAIDA" in
  *"código VELHO"*) ok "mas uma sessão nova é avisada de novo" ;;
  *)                bad "uma sessão nova é avisada de novo" ;;
esac

echo
echo "EM DIA — quem está atualizado não ouve nada"
velha "0.4.0"
SAIDA=$(roda "s3")
[ -z "$SAIDA" ] && ok "máquina em dia não gera aviso" || bad "máquina em dia é muda"

echo
echo "FAIL-OPEN — sem material para julgar, ele cala"
SAIDA=$(printf '{"session_id":"s4"}' | CLAUDE_PROJECT_DIR="$LAB/vazio" TMPDIR="$LAB/tmp" bash "$HOOK" 2>&1)
[ -z "$SAIDA" ] && ok "fora do repositório, silêncio" || bad "fora do repositório, silêncio"
velha "0.3.2"
SAIDA=$(printf '{"session_id":"s5"}' | CLAUDE_PROJECT_DIR="$LAB/repo" CLAUDE_CONFIG_DIR="$LAB/casa" \
  TMPDIR="$LAB/tmp" CADEIA_GATE=0 bash "$HOOK" 2>&1)
[ -z "$SAIDA" ] && ok "com CADEIA_GATE=0 ele não fala" || bad "kill-switch"

rm -rf "$LAB"
echo
if [ "$FALHAS" -gt 0 ]; then
  echo "aviso de cadeia: $FALHAS falha(s)"
  exit 1
fi
echo "aviso de cadeia: tudo verde"
