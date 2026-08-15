#!/bin/bash
# test_reserva_de_arquivos.sh — suíte da reserva de arquivos entre motores.
#
# Roda o script DE VERDADE e olha a decisão que sai no stdout. Nada de
# recalcular a regra aqui: recalcular à mão foi o que mascarou o bug de path na
# 1ª rodada do plan-gate.
#
#   bash plugins/project-skills/hooks/test_reserva_de_arquivos.sh

HOOK="$(cd "$(dirname "$0")" && pwd)/reserva-de-arquivos.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

OK=0
FALHA=0

check() {
  local nome="$1" cond="$2" extra="${3:-}"
  if [ "$cond" = "1" ]; then
    OK=$((OK + 1)); echo "  ok   $nome"
  else
    FALHA=$((FALHA + 1)); echo "  FALHA $nome ${extra}"
  fi
}

roda() { # $@ = argumentos do script
  CLAUDE_CONFIG_DIR="$TMP" bash "$HOOK" "$@" 2>/dev/null
}

# A decisão vem pelo JSON, como no gate do motor — não por grep de string solta.
nega() {
  printf '%s' "$1" \
    | jq -e '.hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1 \
    && echo 1 || echo 0
}

SID="sessao-de-teste-1"
ESTADO="$TMP/andamento"
RESERVAS="$ESTADO/reservas"

echo "[reserva de arquivos entre motores do sprint]"

# 1 · o primeiro motor reserva em silêncio
OUT=$(roda reservar "$SID" motor-a plugins/x/a.sh plugins/x/b.sh)
check "o primeiro motor reserva e o script fica mudo" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
check "a reserva vira arquivo fora do plugin, na raiz de config" \
  "$([ -f "$RESERVAS/${SID}__motor-a.files" ] && echo 1 || echo 0)"
check "a reserva guarda uma linha por caminho" \
  "$([ "$(wc -l < "$RESERVAS/${SID}__motor-a.files")" -eq 2 ] && echo 1 || echo 0)"

# 2 · O CRITÉRIO: segundo motor com lista que CRUZA é recusado
OUT=$(roda reservar "$SID" motor-b plugins/x/b.sh plugins/y/c.sh)
check "segundo motor com lista que CRUZA é RECUSADO" "$(nega "$OUT")" "saiu: $OUT"
check "a recusa nomeia o arquivo em disputa" \
  "$(printf '%s' "$OUT" | grep -q 'plugins/x/b.sh' && echo 1 || echo 0)" "saiu: $OUT"
check "a recusa nomeia o motor dono da reserva" \
  "$(printf '%s' "$OUT" | grep -q 'motor-a' && echo 1 || echo 0)" "saiu: $OUT"
check "a recusa mostra o desligamento" \
  "$(printf '%s' "$OUT" | grep -q 'SPRINT_RESERVA=0' && echo 1 || echo 0)"
check "quem recusa não deixa reserva pela metade" \
  "$([ ! -f "$RESERVAS/${SID}__motor-b.files" ] && echo 1 || echo 0)"
check "quem recusa sai com exit 0 (o veredito vem do JSON)" \
  "$(roda reservar "$SID" motor-b plugins/x/b.sh >/dev/null; [ $? -eq 0 ] && echo 1 || echo 0)"

# 3 · lista disjunta passa — o gate separa quem se encosta, não serializa a sessão
OUT=$(roda reservar "$SID" motor-c plugins/z/d.sh)
check "lista DISJUNTA passa (não serializa a sessão)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 4 · o mesmo motor pode reescrever a própria lista
OUT=$(roda reservar "$SID" motor-a plugins/x/a.sh plugins/x/b.sh plugins/x/e.sh)
check "o próprio motor não se recusa (re-registra a lista dele)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 5 · liberar devolve os arquivos pro próximo
roda liberar "$SID" motor-a
check "liberar apaga a reserva" \
  "$([ ! -f "$RESERVAS/${SID}__motor-a.files" ] && echo 1 || echo 0)"
OUT=$(roda reservar "$SID" motor-b plugins/x/b.sh)
check "depois de liberada, o arquivo aceita novo dono" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
roda liberar "$SID" motor-b

# 6 · RESERVA ÓRFÃ EXPIRA. Motor que morre sem liberar recusaria todo motor
# seguinte PARA SEMPRE — é o defeito do sinal `ativo-<sid>` com outro nome.
ORFA="$RESERVAS/${SID}__motor-morto.files"
printf 'plugins/x/a.sh\n' > "$ORFA"
touch -t 202001010000 "$ORFA"
OUT=$(roda reservar "$SID" motor-novo plugins/x/a.sh)
check "reserva mais velha que o limite deixa de recusar" \
  "$([ "$(nega "$OUT")" = "0" ] && echo 1 || echo 0)" "saiu: $OUT"
check "a reserva expirada é APAGADA, não só ignorada" \
  "$([ ! -f "$ORFA" ] && echo 1 || echo 0)"
check "a expiração deixa rastro em log (não é silenciosa)" \
  "$([ -s "$ESTADO/reservas-expiradas.log" ] && echo 1 || echo 0)"
roda liberar "$SID" motor-novo

VIVA="$RESERVAS/${SID}__motor-vivo.files"
printf 'plugins/x/viva.sh\n' > "$VIVA"
OUT=$(roda reservar "$SID" motor-tardio plugins/x/viva.sh)
check "reserva recém-feita continua recusando (a poda não come a viva)" \
  "$(nega "$OUT")" "saiu: $OUT"

# 7 · reserva de OUTRA sessão não vaza pra esta
OUT=$(roda reservar "outra-sessao" motor-a plugins/x/viva.sh)
check "reserva de outra sessão não recusa esta" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 8 · kill-switch
OUT=$(CLAUDE_CONFIG_DIR="$TMP" SPRINT_RESERVA=0 bash "$HOOK" reservar "$SID" motor-x plugins/x/viva.sh 2>/dev/null)
check "SPRINT_RESERVA=0 cala a reserva" "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 9 · fail-open nas bordas de infra
OUT=$(roda reservar "$SID")
check "sem motor, não recusa (fail-open)" "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(roda reservar "$SID" motor-y)
check "sem lista, não recusa (fail-open)" "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(roda verbo-que-não-existe "$SID" motor-y plugins/x/viva.sh)
check "verbo desconhecido não recusa (fail-open)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(CLAUDE_CONFIG_DIR="$TMP" PATH="/nonexistent" bash "$HOOK" reservar "$SID" motor-z plugins/x/viva.sh 2>/dev/null)
check "sem jq nem python3 no PATH, não recusa (fail-open)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"

# 10 · id com `/` não escreve fora do diretório de estado
roda reservar "../fuga" motor-a plugins/x/fuga.sh
check "id com ../ não escapa do diretório de reservas" \
  "$([ ! -e "$ESTADO/../fuga__motor-a.files" ] && [ -n "$(ls "$RESERVAS" 2>/dev/null)" ] && echo 1 || echo 0)"

# 11 · QUEM CHAMA. Peça que nenhum caminho do produto invoca não protege nada — e foi
# exatamente esse o estado desta reserva até 2026-08-06: escrita, testada e órfã. Aqui se
# cobra o par: a skill manda rodar ESTE script com ESTES verbos, e os verbos que ela manda
# são os que o script atende de verdade.
SKILL="$(cd "$(dirname "$0")/../../project-skills/skills/sprint" && pwd)/SKILL.md"  # acopla-ok: teste roda no monorepo, não na máquina de quem instala
check "a skill do motor manda RESERVAR antes de executar" \
  "$(grep -q 'reserva-de-arquivos.sh reservar' "$SKILL" && echo 1 || echo 0)"
check "a skill do motor manda LIBERAR ao entregar" \
  "$(grep -q 'reserva-de-arquivos.sh)" liberar' "$SKILL" && echo 1 || echo 0)"

# O CENÁRIO DO CRITÉRIO, ponta a ponta: dois motores da mesma sessão, o segundo com uma
# lista que cruza a do primeiro — rodando os verbos que a skill nomeia, nesta ordem.
roda liberar "$SID" motor-vivo
VERBO_RESERVAR=$(grep -o 'reserva-de-arquivos.sh reservar' "$SKILL" | head -1 | awk '{print $2}')
OUT=$(roda "$VERBO_RESERVAR" "$SID" motor-1 plugins/w/comum.sh plugins/w/so-dele.sh)
check "motor 1 dispara e reserva (pelo verbo que a skill manda rodar)" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
OUT=$(roda "$VERBO_RESERVAR" "$SID" motor-2 plugins/w/comum.sh plugins/w/so-do-2.sh)
check "motor 2, com lista que CRUZA, é RECUSADO ao disparar" "$(nega "$OUT")" "saiu: $OUT"
roda liberar "$SID" motor-1
OUT=$(roda "$VERBO_RESERVAR" "$SID" motor-2 plugins/w/comum.sh)
check "motor 1 liberou ao entregar, e o motor 2 passa a disparar" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
roda liberar "$SID" motor-2
printf 'plugins/x/viva.sh\n' > "$VIVA"

# 12 · A MORTE POR FORA. TaskStop mata o motor no meio: ele nunca chega no `liberar`, e a
# reserva órfã (nova, longe da expiração) recusaria o próximo motor da sessão por até 12h.
# Quem solta é a receita do RETORNO da chamada, na casca — e é ela, LITERAL, que roda aqui:
# o laço sai do bloco "2) NO RETORNO" da skill por recorte, não é reescrito à mão.
# O recorte pega SÓ a linha que solta a reserva — a de cima resolve o caminho do hook
# pelo resolvedor, e aqui o hook é o do repositório, entregue por env.
RECEITA=$(awk '/# 2\) NO RETORNO da chamada/,/^```$/' "$SKILL" \
  | grep -F 'bash "$RESERVA_SH" liberar')
check "a receita do retorno traz o comando que libera a reserva do motor morto" \
  "$([ -n "$RECEITA" ] && echo 1 || echo 0)"

printf 'plugins/m/morto.sh\n' > "$RESERVAS/${SID}__motor-morto-por-fora.files"
printf 'plugins/m/viva.sh\n'  > "$RESERVAS/${SID}__motor-ainda-vivo.files"
OUT=$(roda reservar "$SID" motor-seguinte plugins/m/morto.sh)
check "com a reserva órfã de pé, o próximo motor É RECUSADO (o defeito existe)" \
  "$(nega "$OUT")" "saiu: $OUT"

CLAUDE_CONFIG_DIR="$TMP" CLAUDE_CODE_SESSION_ID="$SID" RESERVA_SH="$HOOK" \
  MOTOR_MORTO=motor-morto-por-fora bash -c "$RECEITA" >/dev/null 2>&1
check "a receita do retorno apaga a reserva da execução morta" \
  "$([ ! -f "$RESERVAS/${SID}__motor-morto-por-fora.files" ] && echo 1 || echo 0)"
# O P0 que a versão anterior desta receita trazia: ela varria a sessão INTEIRA e soltava
# também a reserva de um motor VIVO — dois motores voltavam ao mesmo arquivo, que é
# exatamente o que este hook existe para impedir.
check "a reserva do motor que segue VIVO na mesma sessão sobrevive" \
  "$([ -f "$RESERVAS/${SID}__motor-ainda-vivo.files" ] && echo 1 || echo 0)"
OUT=$(roda reservar "$SID" motor-seguinte plugins/m/viva.sh)
check "e por isso o arquivo do motor vivo continua recusando o próximo" \
  "$(nega "$OUT")" "saiu: $OUT"
OUT=$(roda reservar "$SID" motor-seguinte plugins/m/morto.sh)
check "depois da receita, o arquivo do motor morto passa" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "saiu: $OUT"
roda liberar "$SID" motor-seguinte
roda liberar "$SID" motor-ainda-vivo

# reserva de OUTRA sessão não é tocada pela receita desta
printf 'plugins/m/morto.sh\n' > "$RESERVAS/outra-sessao__motor-morto-por-fora.files"
CLAUDE_CONFIG_DIR="$TMP" CLAUDE_CODE_SESSION_ID="$SID" RESERVA_SH="$HOOK" \
  MOTOR_MORTO=motor-morto-por-fora bash -c "$RECEITA" >/dev/null 2>&1
check "a receita não solta reserva de outra sessão" \
  "$([ -f "$RESERVAS/outra-sessao__motor-morto-por-fora.files" ] && echo 1 || echo 0)"
rm -f "$RESERVAS/outra-sessao__motor-morto-por-fora.files"

# 13 · anti-tautologia: sabotar o cruzamento tem que fazer a suíte reprovar
SAB="$TMP/sabotado.sh"
sed 's/^  CRUZOU=.*grep -F -x -f.*$/  CRUZOU=""/' "$HOOK" > "$SAB"
OUT=$(CLAUDE_CONFIG_DIR="$TMP" bash "$SAB" reservar "$SID" motor-sab plugins/x/viva.sh 2>/dev/null)
check "reserva sabotada (não olha o cruzamento) DEIXA de recusar" \
  "$([ -z "$OUT" ] && echo 1 || echo 0)" "o sabotado ainda recusou — o teste #2 é tautológico"

echo
if [ "$FALHA" -eq 0 ]; then
  echo "OK ($OK checks)"
  exit 0
fi
echo "FALHOU ($FALHA de $((OK + FALHA)))"
exit 1
