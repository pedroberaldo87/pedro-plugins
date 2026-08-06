#!/bin/bash
# Suite do pretooluse-graphify-guard.sh — o TEXTO de cada ramo, não a detecção.
#
# O hook tem dois ramos de saída e eles NÃO enquadram a mesma situação:
#   GRAPHIFY_DENY=1 → deny: ESTE hook barrou a busca. "refaça esta busca" faz sentido.
#   default (warn)  → additionalContext: este hook não barrou nada, e é só isso que ele
#                     sabe. Mandar "refaça esta busca" é instrução pra um bloqueio que
#                     ele não deu; afirmar que a busca rodou ("os resultados abaixo") é
#                     palpite — PreToolUse fala ANTES da ferramenta e outro gate pode
#                     negar a mesma chamada (o project-doc nega, com matcher mais largo;
#                     o caso "dois gates no MESMO payload" lá embaixo mede isso).
#                     O texto do aviso fica no que é verdade no instante: busca cega,
#                     há grafo, confirme lá antes de concluir.
#
# Isolamento: projeto falso em mktemp com graphify-out/graph.json, sentinel por sessão
# única (limpo no trap). O graphify-detect.sh real roda — é barato e determinístico aqui.

HOOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pretooluse-graphify-guard.sh"
# O hook grava no temporário DO SISTEMA — a suíte pergunta pelo mesmo caminho que
# ele, em vez de assumir /tmp (que nem sempre é o temporário da máquina).
# shellcheck source=/dev/null
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-tmpdir.sh"
TMPD=$(td_tmpdir)
TMP="$(mktemp -d)"
SESSIONS=""
SESS=""
# O id da sessão nasce AQUI, no shell pai. Dentro de run() ele morria: run é chamada
# em substituição de comando (`OUT="$(run …)"`), que é subshell, e a atribuição a
# SESSIONS não sobrevivia — o trap iterava sobre vazio e o cleanup era no-op.
nova_sessao() { SESS="gg-$$-$RANDOM"; SESSIONS="$SESSIONS $SESS"; }
cleanup() {
  rm -rf "$TMP"
  for s in $SESSIONS; do rm -f "$TMPD/claude-graphify-guard-$s"; done
  # o caso dos dois gates roda o doc-guard de verdade, que também escreve lá
  rm -f "$TMPD"/claude-doc-guard-gg-$$-* "$TMPD"/claude-doc-guard-count-gg-$$-* 2>/dev/null
  # cinto e suspensório: poda pelo padrão desta rodada (PID), caso algum caso futuro
  # volte a criar sessão de dentro de um subshell.
  rm -f "$TMPD"/claude-graphify-guard-gg-$$-* 2>/dev/null
}
trap cleanup EXIT

PASS=0; FAIL=0
check() {
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1))
  else FAIL=$((FAIL + 1)); printf '  ✗ %s — esperava %s, veio %s\n' "$1" "$3" "$2" >&2; fi
}
has() { case "$1" in *"$2"*) echo sim ;; *) echo nao ;; esac; }

# --- projeto falso COM grafo ---
PROJ="$TMP/proj"
mkdir -p "$PROJ/graphify-out"
printf '{"nodes":[],"edges":[]}\n' > "$PROJ/graphify-out/graph.json"

run() { # $1=session_id (de nova_sessao) $2=GRAPHIFY_DENY  → stdout cru do hook
  jq -nc --arg s "$1" --arg c "$PROJ" \
    '{session_id:$s, cwd:$c, tool_name:"Grep", tool_input:{pattern:"foo", path:$c}}' \
    | GRAPHIFY_DENY="$2" bash "$HOOK" 2>/dev/null
}

run_sem_env() { # $1=session_id — sem a variável NO AMBIENTE → o caminho real de produção
  jq -nc --arg s "$1" --arg c "$PROJ" \
    '{session_id:$s, cwd:$c, tool_name:"Grep", tool_input:{pattern:"foo", path:$c}}' \
    | env -u GRAPHIFY_DENY bash "$HOOK" 2>/dev/null
}

echo "── ramo deny (GRAPHIFY_DENY=1): a busca não rodou ──"
nova_sessao; OUT_DENY="$(run "$SESS" 1)"
check "deny nega a busca" \
  "$(printf '%s' "$OUT_DENY" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)" "deny"
R_DENY="$(printf '%s' "$OUT_DENY" | jq -r '.hookSpecificOutput.permissionDecisionReason // ""' 2>/dev/null)"
check "deny manda refazer a busca (ela foi barrada, então faz sentido)" \
  "$(has "$R_DENY" "refaça esta busca")" "sim"
check "deny aponta o projeto do grafo" "$(has "$R_DENY" "$PROJ")" "sim"

echo "── ramo aviso (default): este hook não barrou — e não sabe mais que isso ──"
nova_sessao; OUT_WARN="$(run "$SESS" 0)"
check "aviso não bloqueia" \
  "$(printf '%s' "$OUT_WARN" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)" "allow"
R_WARN="$(printf '%s' "$OUT_WARN" | jq -r '.hookSpecificOutput.additionalContext // ""' 2>/dev/null)"
check "o aviso chega mesmo (additionalContext não-vazio)" \
  "$(if [ -n "$R_WARN" ]; then echo tem; else echo vazio; fi)" "tem"
# O finding: instrução pra um bloqueio que não aconteceu.
check "aviso NÃO manda refazer uma busca que não foi barrada" \
  "$(has "$R_WARN" "refaça esta busca")" "nao"
# E o simétrico: um PreToolUse fala ANTES da ferramenta rodar — ele não sabe se a
# chamada vai ser negada por outro gate. Nenhum dos dois ramos pode afirmar o que a
# ferramenta fez ou vai devolver.
check "aviso NÃO afirma que a busca escapou do bloqueio" \
  "$(has "$R_WARN" "NÃO foi barrada")" "nao"
check "aviso NÃO promete resultados que podem nunca chegar" \
  "$(has "$R_WARN" "resultados abaixo")" "nao"
check "aviso pede confirmação no grafo antes de concluir" \
  "$(has "$R_WARN" "antes de concluir")" "sim"
check "aviso nomeia a busca cega, que é o que o hook de fato enxerga" \
  "$(has "$R_WARN" "Busca cega (grep/glob/find)")" "sim"

echo "── produção: GRAPHIFY_DENY AUSENTE do ambiente é o MESMO aviso ──"
# Os casos acima sempre setam a variável. O caminho que roda 100% das vezes na máquina
# é o outro: a variável nem existe, e quem decide é o ${GRAPHIFY_DENY:-0} do fonte.
# Sem este caso, trocar o teste do fonte por [ -n "$GRAPHIFY_DENY" ] deixa a suíte verde
# e faz produção passar a NEGAR toda primeira busca de sessão.
nova_sessao; OUT_PROD="$(run_sem_env "$SESS")"
check "sem a env var, não bloqueia (o default é aviso, não deny)" \
  "$(printf '%s' "$OUT_PROD" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)" "allow"
check "sem a env var, o texto é o mesmo do ramo de aviso" \
  "$(printf '%s' "$OUT_PROD" | jq -r '.hookSpecificOutput.additionalContext // ""' 2>/dev/null)" "$R_WARN"

echo "── anti-tautologia: os dois ramos seguem entregando o caminho do grafo ──"
check "aviso ensina o comando graphify query" "$(has "$R_WARN" "graphify query")" "sim"
check "deny ensina o comando graphify query" "$(has "$R_DENY" "graphify query")" "sim"
check "aviso aponta o projeto do grafo" "$(has "$R_WARN" "$PROJ")" "sim"

echo "── grafo defasado: o alerta de stale entra nos DOIS ramos ──"
# o fragmento de stale é montado uma vez e colado nos dois textos — se um ramo perder
# a cola, o usuário confia num grafo velho sem saber.
sleep 1; printf '# novo\n' > "$PROJ/novo.md"
nova_sessao; S_WARN="$(run "$SESS" 0 | jq -r '.hookSpecificOutput.additionalContext // ""' 2>/dev/null)"
nova_sessao; S_DENY="$(run "$SESS" 1 | jq -r '.hookSpecificOutput.permissionDecisionReason // ""' 2>/dev/null)"
check "aviso avisa que o grafo está defasado" "$(has "$S_WARN" "Grafo defasado")" "sim"
check "deny avisa que o grafo está defasado" "$(has "$S_DENY" "Grafo defasado")" "sim"
rm -f "$PROJ/novo.md"

echo "── a régua do canal de texto (perfil hook), nos DOIS ramos ──"
# Este hook não fala com o usuário (invariante 6: nada de systemMessage) — fala com o
# MODELO, por additionalContext. O canal continua sendo texto puro: crase e `**` chegam
# literais, e uma linha de 409 caracteres é o que ele cuspia antes de 2026-08-03. Quem
# cobra é a MESMA régua do gerador de página, pelo perfil `hook`. Vazio = passou.
REGUA="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/regua_texto.py"
regua() { printf '%s\n' "$1" | python3 "$REGUA" --perfil hook --onde "$2" - 2>&1 || :; }
check "a régua está vendorada no plugin (instalado, ele só enxerga a própria pasta)" \
  "$(if [ -f "$REGUA" ]; then echo tem; else echo falta; fi)" "tem"
check "o aviso REAL (additionalContext) passa na régua" "$(regua "$R_WARN" aviso)" ""
check "o deny REAL passa na régua" "$(regua "$R_DENY" deny)" ""
check "o mesmo aviso com markdown é RECUSADO" \
  "$(regua "$(printf '%s' "$R_WARN" | sed 's/graphify --update/`graphify --update`/; s/Busca cega/**Busca cega**/')" aviso | grep -c markdown | tr -d ' ')" "1"
check "o mesmo aviso sem emoji no cabeçalho é RECUSADO" \
  "$(regua "$(printf '%s' "$R_WARN" | sed 's/^🕸️ //')" aviso | grep -c emoji | tr -d ' ')" "1"
# O ramo stale acrescenta uma linha: o orçamento de 6 do canal tem que sobreviver a ela.
check "com o grafo defasado o aviso continua passando na régua" "$(regua "$S_WARN" aviso)" ""
check "com o grafo defasado o deny continua passando na régua" "$(regua "$S_DENY" deny)" ""

echo "── contrato com o conformance.py: a marca default-warn não pode sumir ──"
check "o fonte mantém '# conformance: default-warn'" \
  "$(grep -c '^# conformance: default-warn' "$HOOK")" "1"

echo "── público do aviso é o MODELO: sem systemMessage, e o porquê registrado ──"
# A invariante 6 do contrato é CONDICIONAL — systemMessage é pra "quem precisa ser
# visto pelo usuário". Aqui não precisa: o texto manda consultar o grafo, e quem roda
# `graphify query` é o modelo. Sem o registro no fonte, a próxima leitura trata a
# ausência do systemMessage como esquecimento e "conserta" um ruído por sessão.
check "aviso não emite systemMessage (o destinatário é o modelo, não o usuário)" \
  "$(printf '%s' "$OUT_WARN" | jq -r 'has("systemMessage")' 2>/dev/null)" "false"
check "o fonte registra POR QUE o ramo de aviso não leva systemMessage" \
  "$(grep -c 'este aviso é endereçado ao MODELO' "$HOOK")" "1"

echo "── poda: sentinel de sessão morta não pode viver pra sempre no temporário ──"
# O sentinel é o ÚNICO freio do hook no modo aviso (o deny não freia mais porque a
# busca não para). Sessão morre e o arquivo fica: 55 acumulados desde 26/07 até o
# dia em que este teste nasceu. Poda por mtime, limitada ao PRÓPRIO padrão de nome.
old_mtime() { date -v-3d +%Y%m%d%H%M 2>/dev/null || date -d '3 days ago' +%Y%m%d%H%M; }
S_OLD="$TMPD/claude-graphify-guard-gg-velho-$$"
S_NEW="$TMPD/claude-graphify-guard-gg-vivo-$$"
ALHEIO="$TMPD/claude-vizinho-de-outro-hook-$$"
: > "$S_OLD"; touch -t "$(old_mtime)" "$S_OLD"
: > "$S_NEW"                                   # outra aba, sessão viva
: > "$ALHEIO"; touch -t "$(old_mtime)" "$ALHEIO"
nova_sessao; run "$SESS" 0 >/dev/null
existe() { if [ -e "$1" ]; then echo ficou; else echo apagado; fi; }
check "poda apaga sentinel antigo do próprio padrão" "$(existe "$S_OLD")" "apagado"
check "poda NÃO apaga sentinel recente (sessão viva em outra aba)" "$(existe "$S_NEW")" "ficou"
check "poda NÃO alarga o glob pra outros arquivos do temporário" "$(existe "$ALHEIO")" "ficou"
rm -f "$S_OLD" "$S_NEW" "$ALHEIO"

echo "── dois gates no MESMO payload: o graphify não sabe se a busca vai rodar ──"
# No molde do teste_escritor_e_leitor_concordam: roda os DOIS programas de verdade.
# O project-doc declara Grep|Glob|Bash|Agent (matcher mais largo que o Grep|Glob|Bash
# daqui) e NEGA a mesma primeira busca da sessão. Num projeto que tem grafo E doc — o
# caso comum — a busca é barrada e o additionalContext do graphify chega assim mesmo.
# Texto que afirma "não foi barrada" / "os resultados abaixo" vira mentira exatamente aí.
# Nada disso acopla o graphify ao project-doc: o hook não passa a consultar o vizinho,
# só para de afirmar coisa que nenhum PreToolUse tem como saber.
DOC_GUARD="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../project-doc/hooks" && pwd)/pretooluse-doc-guard.sh"
check "o doc-guard existe no disco (gate ausente sai calado — não confundir com gate mudo)" \
  "$(if [ -f "$DOC_GUARD" ]; then echo tem; else echo falta; fi)" "tem"
DUPLO="$TMP/duplo"
mkdir -p "$DUPLO/graphify-out" "$DUPLO/.claude/docs"
printf '{"nodes":[],"edges":[]}\n' > "$DUPLO/graphify-out/graph.json"
printf '<!-- project-doc:v2 -->\n# Proj\n' > "$DUPLO/CLAUDE.md"
printf '# arch\n' > "$DUPLO/.claude/docs/architecture.md"
payload_duplo() { jq -nc --arg s "$1" --arg c "$DUPLO" \
  '{session_id:$s, cwd:$c, tool_name:"Grep", tool_input:{pattern:"foo", path:$c}}'; }
nova_sessao; SD="$SESS"
D_DOC="$(payload_duplo "$SD" | bash "$DOC_GUARD" 2>/dev/null \
         | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null)"
D_GG="$(payload_duplo "$SD" | GRAPHIFY_DENY=0 bash "$HOOK" 2>/dev/null \
        | jq -r '.hookSpecificOutput.additionalContext // ""' 2>/dev/null)"
check "o doc-guard NEGA essa mesma primeira busca" "$D_DOC" "deny"
check "com a busca negada pelo vizinho, o aviso não diz que ela não foi barrada" \
  "$(has "$D_GG" "NÃO foi barrada")" "nao"
check "com a busca negada pelo vizinho, o aviso não promete resultados abaixo" \
  "$(has "$D_GG" "resultados abaixo")" "nao"
check "mesmo assim o aviso segue apontando o projeto do grafo" "$(has "$D_GG" "$DUPLO")" "sim"
check "mesmo assim o aviso segue ensinando o graphify query" "$(has "$D_GG" "graphify query")" "sim"

echo "── sem grafo: silêncio total (nem aviso, nem sentinel queimado) ──"
NOGRAPH="$TMP/vazio"; mkdir -p "$NOGRAPH"
check "projeto sem graphify-out não gera saída" \
  "$(jq -nc --arg c "$NOGRAPH" '{session_id:"gg-nograph-'"$$"'", cwd:$c, tool_name:"Grep", tool_input:{pattern:"foo", path:$c}}' \
     | GRAPHIFY_DENY=0 bash "$HOOK" 2>/dev/null)" ""

echo "── poda: o gatilho é TODA busca interceptada até o nudge, não 'a primeira' ──"
# Quem corta a poda é o sentinel, e o sentinel só nasce quando o hook de fato avisa
# (o `touch` acontece depois de achar um grafo). Num projeto SEM grafo o hook sai antes
# disso — nada corta, e a poda roda em TODA busca cega, a sessão inteira. Quem lê no
# fonte "roda só antes do primeiro nudge" dimensiona o custo como uma vez por sessão.
# Sessão literal (não `nova_sessao`): aqui o sentinel não nasce, e o check de higiene
# lá embaixo compara SESSIONS com os sentinels que existem de verdade.
SP="gg-podadupla-$$"
V1="$TMPD/claude-graphify-guard-gg-velho1-$$"
V2="$TMPD/claude-graphify-guard-gg-velho2-$$"
busca_sem_grafo() {
  jq -nc --arg s "$SP" --arg c "$NOGRAPH" \
    '{session_id:$s, cwd:$c, tool_name:"Grep", tool_input:{pattern:"foo", path:$c}}' \
    | GRAPHIFY_DENY=0 bash "$HOOK" >/dev/null 2>&1
}
: > "$V1"; touch -t "$(old_mtime)" "$V1"
busca_sem_grafo
check "1ª busca já roda a poda" "$(existe "$V1")" "apagado"
check "…e não queima o sentinel da sessão (não houve nudge)" \
  "$(existe "$TMPD/claude-graphify-guard-$SP")" "apagado"
: > "$V2"; touch -t "$(old_mtime)" "$V2"
busca_sem_grafo
check "2ª busca da MESMA sessão roda a poda DE NOVO (o sentinel nunca nasceu)" \
  "$(existe "$V2")" "apagado"
rm -f "$V1" "$V2" "$TMPD/claude-graphify-guard-$SP"
# E o fonte tem que contar esse gatilho, com o custo que ele carrega por chamada.
check "o fonte não descreve mais a poda como coisa de uma vez por sessão" \
  "$(grep -c 'só antes do primeiro nudge' "$HOOK")" "0"
check "o fonte registra o gatilho real (toda busca interceptada até o nudge)" \
  "$(grep -c 'toda busca interceptada' "$HOOK")" "1"
check "o fonte registra o custo medido por chamada" "$(grep -c '~6ms' "$HOOK")" "1"

echo "── higiene da própria suíte: o trap precisa ter o que podar ──"
# `SESSIONS="$SESSIONS $s"` morava DENTRO de run(), que é chamada em substituição de
# comando (`OUT_DENY="$(run 1)"`) — subshell. A atribuição morria com ela, o trap
# iterava sobre variável vazia e o cleanup era no-op: 129 sentinels acumulados em
# /tmp no dia em que este caso nasceu. O id nasce no shell PAI (nova_sessao).
check "o cleanup conhece TODO sentinel que esta rodada criou" \
  "$(set -- $SESSIONS; echo $#)" \
  "$(ls -d "$TMPD"/claude-graphify-guard-gg-$$-* 2>/dev/null | wc -l | tr -d ' ')"

printf '── %d passou · %d falhou ──\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
