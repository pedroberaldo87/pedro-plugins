#!/usr/bin/env bash
# Testes dos hooks do bootstrap: teto de prosa + preservação de chave no snapshot.
# Tudo em diretório temporário — nunca toca na config real nem no repo.
#
#   bash plugins/bootstrap/hooks/test_bootstrap_hooks.sh
set -uo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$AQUI/stop-prose-ceiling.py"
JUIZ="$AQUI/stop-forma-relato.py"
SNAPSHOT="$AQUI/lib/snapshot.sh"
APPLY="$AQUI/lib/apply.sh"
OK=0; FAIL=0

check() { # nome, esperado, obtido
  if [ "$2" = "$3" ]; then OK=$((OK+1)); echo "  ok   $1";
  else FAIL=$((FAIL+1)); echo "  FAIL $1 — esperado '$2', obtido '$3'"; fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export CLAUDE_CONFIG_DIR="$TMP/claude"
mkdir -p "$CLAUDE_CONFIG_DIR"
# teto de linhas e opt-in: quem roda o teste pode ter a var ligada no ambiente
unset PROSE_CEILING_MAX
# desinstalação é opt-in: se quem roda o teste tiver a var ligada, o caso 2 mentiria
unset BOOTSTRAP_UNINSTALL_UNMANAGED

# monta um transcript com o texto dado e devolve o exit code do hook
roda_hook() { # texto, session_id
  local t="$TMP/tr-$RANDOM.jsonl"
  python3 -c '
import json,sys
open(sys.argv[1],"w").write(json.dumps({"type":"assistant","message":{"role":"assistant",
    "content":[{"type":"text","text":sys.argv[2]}]}})+"\n")' "$t" "$1"
  echo "{\"transcript_path\":\"$t\",\"session_id\":\"$2\"}" | python3 "$HOOK" >/dev/null 2>&1
  echo $?
}

echo "test_bootstrap_hooks.sh"
echo "-- teto de prosa"

CURTA="Gate verde: unit 981 · integracao 1427/0. Mantenho 30 ou troco pra 15?"
check "resposta curta e densa passa" 0 "$(roda_hook "$CURTA" s1)"

LONGA="$(python3 -c 'print("\n".join(f"linha {i}" for i in range(12)))')"
check "12 linhas de prosa barram com PROSE_CEILING_MAX=6" 2 \
  "$(PROSE_CEILING_MAX=6 roda_hook "$LONGA" s2)"
# PREMISSA: o teto nasce ligado. Este teste ja afirmou o contrario ("passam sem a
# var"), e foi exatamente essa versao que deixou o guarda inerte por uma sessao
# inteira. Nenhum valor da env var pode desligar — so o kill-switch, que e visivel.
check "12 linhas barram SEM env var (teto e premissa)" 2 "$(roda_hook "$LONGA" s2b)"
check "PROSE_CEILING_MAX=0 nao desliga" 2 "$(PROSE_CEILING_MAX=0 roda_hook "$LONGA" s2c)"
check "PROSE_CEILING_MAX invalido cai no padrao" 2 "$(PROSE_CEILING_MAX=abc roda_hook "$LONGA" s2d)"
check "PROSE_CEILING_MAX=20 so AJUSTA o numero" 0 "$(PROSE_CEILING_MAX=20 roda_hook "$LONGA" s2e)"

# prova colada nao conta no teto — corte da prova e a falha mais grave
PROVA="$(python3 -c '
F="`"*3
print("Resultado aqui.\n"+F+"\n"+"\n".join(f"saida {i}" for i in range(20))+"\n"+F+"\nProximo passo.")')"
check "20 linhas de PROVA + 2 de prosa passam" 0 "$(roda_hook "$PROVA" s3)"

check "retorica no meio barra" 2 "$(roda_hook "Feito.
Vale notar que o cache foi invalidado." s4)"

# orcamento por resposta: mesmo prefixo NAO pode dividir contador
P="Resultado do gate verde pos-calibracao com todos os testes passando."
A="$P
$(python3 -c 'print("\n".join(f"A {i}" for i in range(12)))')"
B="$P
$(python3 -c 'print("\n".join(f"B {i}" for i in range(12)))')"
PROSE_CEILING_MAX=6 roda_hook "$A" scol >/dev/null
PROSE_CEILING_MAX=6 roda_hook "$A" scol >/dev/null
PROSE_CEILING_MAX=6 roda_hook "$A" scol >/dev/null
check "resposta diferente com mesmo inicio tem orcamento proprio" 2 \
  "$(PROSE_CEILING_MAX=6 roda_hook "$B" scol)"

check "PROSE_CEILING=0 desliga" 0 "$(PROSE_CEILING=0 PROSE_CEILING_MAX=6 roda_hook "$LONGA" s5)"

# ---------------------------------------------------------------------------
# Pergunta fechada exige veredito na 1a linha; pergunta aberta pede explicacao
# e nao pode cobrar veredito nenhum. As duas regras foram provadas a mao numa
# sessao e nunca viraram teste — e regra sem teste e a que volta a quebrar.
# ---------------------------------------------------------------------------
echo "-- veredito na 1a linha (pergunta fechada x aberta)"

# monta um transcript com pergunta do usuario + resposta do assistente
roda_dialogo() { # pergunta, resposta, session_id
  local t="$TMP/dlg-$RANDOM.jsonl"
  python3 -c '
import json,sys
with open(sys.argv[1],"w") as f:
    f.write(json.dumps({"type":"user","message":{"role":"user",
        "content":[{"type":"text","text":sys.argv[2]}]}})+"\n")
    f.write(json.dumps({"type":"assistant","message":{"role":"assistant",
        "content":[{"type":"text","text":sys.argv[3]}]}})+"\n")' "$t" "$1" "$2"
  echo "{\"transcript_path\":\"$t\",\"session_id\":\"$3\"}" | python3 "$HOOK" >/dev/null 2>&1
  echo $?
}

SEM_VEREDITO="Rodei a bateria inteira no repo.
O resultado esta no bloco de prova abaixo."

# 4 fechadas: as duas primeiras sem veredito barram, as duas com veredito passam
check "fechada sem veredito barra"        2 "$(roda_dialogo "voce rodou o teste?" "$SEM_VEREDITO" v1)"
check "fechada 'confirma' sem veredito barra" 2 \
  "$(roda_dialogo "confirma que a arvore esta limpa?" "$SEM_VEREDITO" v2)"
check "fechada com 'Sim' na 1a linha passa" 0 \
  "$(roda_dialogo "voce rodou o teste?" "Sim, rodei a bateria inteira.
A prova esta abaixo." v3)"
check "fechada com 'Nao' na 1a linha passa" 0 \
  "$(roda_dialogo "o teste passou?" "Nao, falhou em 2 casos.
Os dois estao no bloco abaixo." v4)"

# 4 abertas: pedem explicacao, entao nenhuma cobra veredito
# as 4 abertas tambem disparam a fechada de proposito: so passam se a exclusao
# de pergunta aberta estiver viva. Sem isso o caso passaria por nao casar nada.
check "aberta 'como' vence a fechada"     0 "$(roda_dialogo "como voce rodou o teste?" "$SEM_VEREDITO" v5)"
check "aberta 'por que' vence a fechada"  0 "$(roda_dialogo "por que voce rodou o teste?" "$SEM_VEREDITO" v6)"
check "aberta 'qual' vence a fechada"     0 "$(roda_dialogo "qual comando voce rodou?" "$SEM_VEREDITO" v7)"
check "aberta 'o que' vence a fechada"    0 "$(roda_dialogo "o que voce rodou?" "$SEM_VEREDITO" v8)"

# ---------------------------------------------------------------------------
# O juiz de FORMA. Chama modelo, entao so 3 casos e so quando ha `claude`.
# CUIDADO MEDIDO: isolar por CLAUDE_CONFIG_DIR tira a credencial do `claude -p`
# junto, o juiz cai no fail-open e APROVA TUDO — os 3 casos "passavam" em 1,7s.
# Por isso o estado sai por FORMA_RELATO_STATE e o CLAUDE_CONFIG_DIR do teste e
# removido so nesta chamada.
# ---------------------------------------------------------------------------
echo "-- juiz de forma do relato"

roda_juiz() { # texto, session_id
  local t="$TMP/juiz-$RANDOM.jsonl"
  python3 -c '
import json,sys
open(sys.argv[1],"w").write(json.dumps({"type":"assistant","message":{"role":"assistant",
    "content":[{"type":"text","text":sys.argv[2]}]}})+"\n")' "$t" "$1"
  echo "{\"transcript_path\":\"$t\",\"session_id\":\"$2\"}" | \
    env -u CLAUDE_CONFIG_DIR FORMA_RELATO_STATE="$TMP/forma-$2" python3 "$JUIZ" >/dev/null 2>&1
  echo $?
}

if command -v claude >/dev/null 2>&1; then
  # conversa curta nao e relato: nao ha bloco de prova, entao nem chama modelo
  check "resposta curta nao gasta modelo" 0 "$(roda_juiz "Feito." j1)"
  grep -q '"motivo": "nao e relato"' "$TMP/forma-j1/batidas.log" \
    && { OK=$((OK+1)); echo "  ok   curta registrada como 'nao e relato'"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL curta devia bater 'nao e relato'"; }

  BOM="O teste passa: 1 de 1 verde.
O conserto foi trocar o dicionario vazio pelo mapa de configuracao real.

\`\`\`
\$ pytest
1 passed
\`\`\`"
  RUIM="Deixa eu explicar o que aconteceu aqui. O processo foi bastante complexo.
Vale notar que eu precisei investigar bastante antes de qualquer conclusao.
Em outras palavras, o handleRequestPayload chamava parseConfigMap com dict vazio.
Dito isso, acredito que podemos seguir com a correcao proposta abaixo.
Espero que isso esclareca a situacao.

\`\`\`
\$ pytest
1 passed
\`\`\`

Enfim, no final das contas o resultado e que o teste passou."

  check "relato bom passa"    0 "$(roda_juiz "$BOM" j2)"
  check "relato ruim reprova" 2 "$(roda_juiz "$RUIM" j3)"
  # fail-open por juiz mudo aprova tudo: so vale como verde se ele REALMENTE julgou
  grep -q '"motivo": "julgou"' "$TMP/forma-j2/batidas.log" \
    && { OK=$((OK+1)); echo "  ok   o juiz respondeu de verdade (nao foi fail-open)"; } \
    || { FAIL=$((FAIL+1)); echo "  FAIL juiz mudo — o verde acima nao vale"; }
  check "FORMA_RELATO=0 desliga o juiz" 0 "$(FORMA_RELATO=0 roda_juiz "$RUIM" j4)"
else
  echo "  skip  juiz de forma (claude ausente no PATH)"
fi
check "transcript inexistente e fail-open" 0 \
  "$(echo '{"transcript_path":"/nao/existe.jsonl","session_id":"s6"}' | python3 "$HOOK" >/dev/null 2>&1; echo $?)"

# ---------------------------------------------------------------------------
# Máquina de mentira: $HOME temporário + um `claude` falso no início do PATH.
# apply.sh lê $HOME/.claude/plugins/known_marketplaces.json com $HOME FIXO (não
# honra CLAUDE_CONFIG_DIR) e chama `claude plugin install/enable/disable` de
# verdade — então a única forma de provar a receita sem mexer nesta máquina é
# trocar o HOME e o binário. O falso responde ao `plugin list` com o fixture e
# registra toda OUTRA invocação no log.
# ---------------------------------------------------------------------------
FAKEHOME="$TMP/home"; BIN="$TMP/bin"; LOG="$TMP/claude.log"; LISTA="$TMP/plugin-list.txt"
mkdir -p "$FAKEHOME/.claude/plugins" "$BIN"
: > "$LOG"

cat > "$FAKEHOME/.claude/plugins/known_marketplaces.json" <<'JSON'
{
  "claude-plugins-official": {"source": {"source": "github", "repo": "anthropics/claude-plugins-official"}},
  "ponytail": {"source": {"source": "git", "url": "https://github.com/DietrichGebert/ponytail.git"}}
}
JSON

# formato exato que o awk do apply/snapshot espera. terceiro-fantasma está num
# marketplace GERENCIADO e fora do manifest — é candidato a uninstall.
cat > "$LISTA" <<'TXT'
Installed plugins:
  ❯ bootstrap@pedro-plugins
    Version: 1.8.0
    Scope: user
    Status: ✔ enabled
  ❯ terceiro-fantasma@claude-plugins-official
    Version: 0.1.0
    Scope: user
    Status: ✔ enabled
TXT

cat > "$BIN/claude" <<'SH'
#!/usr/bin/env bash
if [ "${1:-}" = "plugin" ] && [ "${2:-}" = "list" ]; then
  cat "$FAKE_LIST"; exit 0
fi
echo "$*" >> "$FAKE_LOG"
exit 0
SH
chmod +x "$BIN/claude"

# roda um script do bootstrap contra a máquina de mentira
na_maquina_falsa() { # repo, script
  local repo="$1"; shift
  HOME="$FAKEHOME" PATH="$BIN:$PATH" FAKE_LIST="$LISTA" FAKE_LOG="$LOG" \
    PEDRO_PLUGINS_REPO="$repo" bash "$@"
}

echo "-- snapshot preserva chave mantida a mao"
if command -v jq >/dev/null 2>&1; then
  # sem .git o snapshot sai em silêncio na linha 27 e o caso passaria vazio
  REPO="$TMP/repo-chave"; mkdir -p "$REPO/plugins/bootstrap/config" "$REPO/.git"
  MF="$REPO/plugins/bootstrap/config/manifest.json"
  cat > "$MF" <<'JSON'
{"version":1,"description":"x","marketplaces":[],
 "skills":{"permitidas":["a"]},
 "chave_que_ninguem_conhece":{"fica":true}}
JSON
  na_maquina_falsa "$REPO" "$SNAPSHOT" >/dev/null 2>&1
  check "chave arbitraria sobrevive ao snapshot" "true" \
    "$(jq -r 'has("chave_que_ninguem_conhece")' "$MF")"
  check "skills sobrevive ao snapshot" "true" "$(jq -r 'has("skills")' "$MF")"
else
  echo "  skip  snapshot (jq ausente)"
fi

echo "-- apply.sh entrega a receita e nao desinstala nada"
if command -v jq >/dev/null 2>&1; then
  # o repo de mentira carrega o manifest REAL — é ele que está sendo provado
  REPO3="$TMP/repo"; mkdir -p "$REPO3/plugins/bootstrap/config" "$REPO3/.git"
  MF3="$REPO3/plugins/bootstrap/config/manifest.json"
  cp "$AQUI/../config/manifest.json" "$MF3"

  na_maquina_falsa "$REPO3" "$APPLY" > "$TMP/apply.out" 2>&1
  ESPERADO_INSTALL="$(jq -r '[.marketplaces[] | select(.name=="pedro-plugins") | .plugins[]] | length - 1' "$MF3")"
  check "maquina so com bootstrap instala o resto do pedro-plugins" "$ESPERADO_INSTALL" \
    "$(grep -c '^plugin install .*@pedro-plugins$' "$LOG")"
  check "o marketplace proprio entra pela URL do manifest" 1 \
    "$(grep -c '^plugin marketplace add https://github.com/pedroberaldo87/pedro-plugins.git$' "$LOG")"
  # candidato reconhecido (senao o caso seguinte passaria vazio) e nao removido
  check "terceiro fora do manifest e apenas reportado" 1 \
    "$(grep -c 'DESLIGADA.*terceiro-fantasma@claude-plugins-official' "$TMP/apply.out")"
  check "nenhum uninstall no log" 0 "$(grep -c '^plugin uninstall' "$LOG")"
else
  echo "  skip  apply (jq ausente)"
fi

echo "-- round-trip: o snapshot devolve o manifest inteiro"
if command -v jq >/dev/null 2>&1; then
  SNAP1="$(na_maquina_falsa "$REPO3" "$SNAPSHOT" 2>/dev/null)"
  SNAP2="$(na_maquina_falsa "$REPO3" "$SNAPSHOT" 2>/dev/null)"
  MKT='.marketplaces[] | select(.name=="pedro-plugins")'
  check "1a rodada reescreve" "changed" "$SNAP1"
  check "pedro-plugins continua com 19 plugins" 19 "$(jq "[$MKT | .plugins[]] | length" "$MF3")"
  check "graphify-guard continua desligado" "false" \
    "$(jq -r "$MKT | .plugins[] | select(.name==\"graphify-guard\") | .enabled" "$MF3")"
  check "intent-guard continua desligado" "false" \
    "$(jq -r "$MKT | .plugins[] | select(.name==\"intent-guard\") | .enabled" "$MF3")"
  check "2a rodada e idempotente" "unchanged" "$SNAP2"
else
  echo "  skip  round-trip (jq ausente)"
fi

echo
echo "$OK ok · $FAIL FAIL"
[ "$FAIL" -eq 0 ]
