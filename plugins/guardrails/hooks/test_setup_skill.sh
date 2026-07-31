#!/bin/bash
# Suite do bloco de LIMPEZA da skill guardrails:setup.
#
# A skill é markdown, mas o passo de limpeza é um bloco bash EXECUTÁVEL — este
# teste extrai o bloco marcado com o sentinel `# guardrails-setup: aposenta-orfaos`
# do SKILL.md e roda ele de verdade contra um HOME falso.
#
# O que está em jogo: ~/.claude/hooks/scope-cop.mode é um arquivo ÓRFÃO (pertence
# ao hook hand-rolled `pretooluse-scope-cop.sh`, que não está registrado em nenhum
# settings.json). Aquele script testa só `off` e depois faz MODE=deny INCONDICIONAL:
# o "warn" escrito ali viraria DENY se ele voltasse a ser registrado. A limpeza
# RENOMEIA (nunca apaga) os arquivos de estado órfãos — e não pode encostar no
# estado VIVO, que mora em ~/.claude/guardrails/.

SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")/../skills/setup" && pwd)/SKILL.md"
TMP="$(mktemp -d)"
# Sem raiz temporária não há suíte: cada `rm -rf "$TMP/..."` daqui viraria um caminho
# absoluto real (`/home`). Aborta antes de armar o trap e antes do primeiro rm.
if [ -z "$TMP" ] || [ ! -d "$TMP" ]; then
  echo "  ✗ mktemp -d falhou — sem raiz temporária, a suíte não roda" >&2
  exit 1
fi
trap 'rm -rf "${TMP:?}"' EXIT

PASS=0; FAIL=0
check() { # nome, obtido, esperado
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1))
  else FAIL=$((FAIL + 1)); printf '  ✗ %s — esperava %s, veio %s\n' "$1" "$3" "$2" >&2; fi
}

# --- extrai o bloco bash marcado pelo sentinel ---
BLOCO="$TMP/limpeza.sh"
awk '
  /# guardrails-setup: aposenta-orfaos/ { dentro=1 }
  dentro && /^```$/ { exit }
  dentro { print }
' "$SKILL" > "$BLOCO"

if [ ! -s "$BLOCO" ]; then
  echo "  ✗ SKILL.md não tem o bloco '# guardrails-setup: aposenta-orfaos'" >&2
  echo "── 0 ok, 1 falha ──" >&2
  exit 1
fi

# --- HOME falso: órfãos em .claude/hooks/, estado VIVO em .claude/guardrails/ ---
monta_home() {
  rm -rf "${TMP:?}/home"
  mkdir -p "$TMP/home/.claude/hooks" "$TMP/home/.claude/guardrails"
  printf 'warn' > "$TMP/home/.claude/hooks/scope-cop.mode"
  printf 'linha de log antiga\n' > "$TMP/home/.claude/hooks/scope-cop.log"
  printf '2' > "$TMP/home/.claude/hooks/scope-cop.blockstreak"
  printf '#!/bin/bash\n' > "$TMP/home/.claude/hooks/pretooluse-scope-cop.sh"
  printf 'warn' > "$TMP/home/.claude/guardrails/scope-cop.mode"
}

# `env -u`: a raiz de config agora deriva de ${CLAUDE_CONFIG_DIR:-$HOME/.claude}, então
# a suíte só é hermética se a env var da máquina que roda o teste não vazar pra cá.
roda() { env -u CLAUDE_CONFIG_DIR HOME="$TMP/home" bash "$BLOCO" >/dev/null 2>&1; echo $?; }

existe() { [ -e "$1" ] && echo sim || echo nao; }

echo "── limpeza aposenta os órfãos de ~/.claude/hooks/ ──"
monta_home
RC="$(roda)"
check "bloco de limpeza sai 0" "$RC" "0"

check "aposenta_o_mode_orfao_sem_apagar (original sai)" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.mode")" "nao"
check "aposenta_o_mode_orfao_sem_apagar (.obsoleto entra)" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.mode.obsoleto")" "sim"
check "aposenta_o_mode_orfao_sem_apagar (conteúdo preservado)" \
  "$(cat "$TMP/home/.claude/hooks/scope-cop.mode.obsoleto" 2>/dev/null)" "warn"
check "aposenta_o_log_orfao" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.log.obsoleto")" "sim"
check "aposenta_o_blockstreak_orfao" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.blockstreak.obsoleto")" "sim"

echo "── o estado VIVO do plugin é intocável ──"
# Renomear ~/.claude/guardrails/scope-cop.mode faria o hook cair no default deny:
# a limpeza dos órfãos não pode virar mudança de modo pelas costas.
check "nao_toca_no_mode_vivo_do_plugin (arquivo fica)" \
  "$(existe "$TMP/home/.claude/guardrails/scope-cop.mode")" "sim"
check "nao_toca_no_mode_vivo_do_plugin (valor fica 'warn')" \
  "$(cat "$TMP/home/.claude/guardrails/scope-cop.mode" 2>/dev/null)" "warn"
check "nao_renomeia_o_script_hand_rolled (deleção é do usuário)" \
  "$(existe "$TMP/home/.claude/hooks/pretooluse-scope-cop.sh")" "sim"

echo "── idempotência e máquina limpa ──"
RC2="$(roda)"
check "segunda rodada sai 0" "$RC2" "0"
check "segunda rodada não sobrescreve o .obsoleto" \
  "$(cat "$TMP/home/.claude/hooks/scope-cop.mode.obsoleto" 2>/dev/null)" "warn"

echo "── arquivado anterior nunca é sobrescrito ──"
# O .obsoleto é ARQUIVO de auditoria (o scope-cop.log real na máquina do usuário tem
# centenas de KB). Se o hook hand-rolled voltar a rodar e recriar o órfão, a rodada
# seguinte da limpeza NÃO pode apagar o arquivado da rodada anterior — a invariante
# é "RENOMEIA (nunca apaga), preservando o conteúdo".
printf 'deny' > "$TMP/home/.claude/hooks/scope-cop.mode"
RC4="$(roda)"
check "rodada com órfão recriado sai 0" "$RC4" "0"
check "nao_sobrescreve_arquivado_anterior (1º arquivado intacto)" \
  "$(cat "$TMP/home/.claude/hooks/scope-cop.mode.obsoleto" 2>/dev/null)" "warn"
check "nao_sobrescreve_arquivado_anterior (órfão recriado sai)" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.mode")" "nao"
check "nao_sobrescreve_arquivado_anterior (2º conteúdo também arquivado)" \
  "$(cat "$TMP/home/.claude/hooks/scope-cop.mode".obsoleto.* 2>/dev/null)" "deny"

rm -rf "${TMP:?}/home"; mkdir -p "$TMP/home"
RC3="$(roda)"
check "máquina sem ~/.claude/hooks sai 0" "$RC3" "0"

echo "── com CLAUDE_CONFIG_DIR setado, a limpeza aposenta os órfãos DE LÁ ──"
# Mesma regra do lib/conformance.py:CLAUDE_DIR. Com $HOME fixo, quem seta a env var
# teria a limpeza mexendo numa pasta que não é a config real: o órfão de verdade
# ficaria intacto (e o setup diria que rodou) e um homônimo fora da config seria
# aposentado sem motivo.
rm -rf "${TMP:?}/home" "${TMP:?}/cfg"
mkdir -p "$TMP/home/.claude/hooks" "$TMP/cfg/hooks"
printf 'warn' > "$TMP/cfg/hooks/scope-cop.mode"
printf 'nao mexer' > "$TMP/home/.claude/hooks/scope-cop.mode"
RC5="$(HOME="$TMP/home" CLAUDE_CONFIG_DIR="$TMP/cfg" bash "$BLOCO" >/dev/null 2>&1; echo $?)"
check "com CLAUDE_CONFIG_DIR a limpeza sai 0" "$RC5" "0"
check "aposenta_o_orfao_da_config_real (CLAUDE_CONFIG_DIR)" \
  "$(existe "$TMP/cfg/hooks/scope-cop.mode.obsoleto")" "sim"
check "nao_encosta_no_HOME_quando_a_config_mora_noutro_lugar" \
  "$(cat "$TMP/home/.claude/hooks/scope-cop.mode" 2>/dev/null)" "nao mexer"

echo "── rename que falha não pode ser reportado como sucesso ──"
# O relatório do passo 6 da skill ("os arquivos de estado velhos viraram *.obsoleto")
# é lido pelo usuário como fato consumado. Se o `mv` falhar (permissão, disco cheio,
# volume read-only) e o bloco ainda imprimir "aposentado: …" e sair 0, o setup MENTE:
# o órfão continua lá com o mesmo nome do arquivo vivo — exatamente a armadilha que
# este passo existe pra desarmar.
monta_home
MVSTUB="$TMP/mvstub"; mkdir -p "$MVSTUB"
printf '#!/bin/bash\nexit 1\n' > "$MVSTUB/mv"; chmod +x "$MVSTUB/mv"
SAIDA_MV="$(env -u CLAUDE_CONFIG_DIR HOME="$TMP/home" PATH="$MVSTUB:$PATH" bash "$BLOCO" 2>/dev/null)"
RC7=$?
check "rename_que_falha_faz_o_bloco_sair_nao_zero" \
  "$([ "$RC7" != "0" ] && echo sim || echo nao)" "sim"
check "rename_que_falha_nao_imprime_aposentado" \
  "$(printf '%s' "$SAIDA_MV" | grep -c 'aposentado:' | tr -d ' ')" "0"
check "rename_que_falha_deixa_o_orfao_onde_estava" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.mode")" "sim"

echo "── órfão fora da lista enumerada fica onde está ──"
# A lista é ENUMERADA e o critério é homonímia com o estado VIVO do plugin em
# $CFG/guardrails/. `scope-cop.review-due` é órfão do mesmo hook hand-rolled, mas o
# plugin não tem nenhum arquivo com esse nome — não há o que confundir. Ele fica, e o
# porquê fica ESCRITO no bloco: omissão silenciosa não se distingue de esquecimento.
monta_home
printf '2026-07-05\n' > "$TMP/home/.claude/hooks/scope-cop.review-due"
RC8="$(roda)"
check "rodada com órfão fora da lista sai 0" "$RC8" "0"
check "nao_aposenta_orfao_sem_homonimo_vivo (review-due fica)" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.review-due")" "sim"
check "nao_aposenta_orfao_sem_homonimo_vivo (conteúdo intacto)" \
  "$(cat "$TMP/home/.claude/hooks/scope-cop.review-due" 2>/dev/null)" "2026-07-05"
check "nao_aposenta_orfao_sem_homonimo_vivo (sem .obsoleto)" \
  "$(existe "$TMP/home/.claude/hooks/scope-cop.review-due.obsoleto")" "nao"
check "a_omissao_do_review_due_esta_registrada_no_bloco" \
  "$([ "$(grep -c 'review-due' "$BLOCO")" -gt 0 ] && echo sim || echo nao)" "sim"

echo "── a própria suíte não pode remover nada com \$TMP vazio ──"
# SC2115: se o `mktemp -d` falhar, TMP fica vazio e todo `rm -rf "$TMP/home"` daqui
# vira `rm -rf /home`. Roda ESTA suíte de novo com um `mktemp` que sempre falha e um
# `rm` que só registra o que receberia — com a raiz temporária ausente, nada pode ser
# removido: a suíte tem que abortar antes do primeiro rm.
STUB="$TMP/stub"; mkdir -p "$STUB"
printf '#!/bin/bash\nexit 1\n' > "$STUB/mktemp"
{ echo '#!/bin/bash'; echo "printf '%s\\n' \"\$@\" >> '$TMP/rm.log'"; echo 'exit 0'; } > "$STUB/rm"
chmod +x "$STUB/mktemp" "$STUB/rm"
: > "$TMP/rm.log"
RC6="$(PATH="$STUB:$PATH" bash "${BASH_SOURCE[0]}" >/dev/null 2>&1; echo $?)"
check "aborta_quando_o_mktemp_falha (sai != 0)" \
  "$([ "$RC6" != "0" ] && echo sim || echo nao)" "sim"
check "nao_remove_nada_sem_raiz_temporaria (rm nunca chamado)" \
  "$(wc -l < "$TMP/rm.log" | tr -d ' ')" "0"

printf '── %s ok, %s falha(s) ──\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
