#!/bin/bash
# test_plan_gate.sh — suíte do gate de plano + do escape verbal.
# Roda isolado em /tmp; não toca projeto nenhum. Uso: bash test_plan_gate.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$SCRIPT_DIR/pretooluse-plan-gate.sh"
ESC="$SCRIPT_DIR/userpromptsubmit-plan-escape.sh"
PASS=0; FAIL=0
SESSION="test-$$"

ok()   { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  ✗ %s\n     esperado: %s\n     obtido:   %s\n' "$1" "$2" "$3"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"; rm -f /tmp/claude-plan-gate-*-'"$SESSION"'-* /tmp/claude-doc-guard-'"$SESSION"'-*' EXIT

# --- fixtures -------------------------------------------------------------
BARE="$TMP/projeto-sem-doc"        # git repo, zero documentação
mkdir -p "$BARE" && (cd "$BARE" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)

DOCD="$TMP/projeto-com-doc"        # git repo com CLAUDE.md v2 + .claude/docs/
mkdir -p "$DOCD/.claude/docs" && (cd "$DOCD" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf '<!-- project-doc:v2 gen=3.8 -->\n# Project Reference\n<!-- project-doc:v2:end -->\n' > "$DOCD/CLAUDE.md"
printf -- '---\ngenerated: 2026-07-26\nscope:\n  - x.py\ndoc-sig: a/b@gen=3.8#deadbeef\n---\n# Arch\n' > "$DOCD/.claude/docs/architecture.md"
# A constituição do projeto e as etapas do acordo são pré-requisito do CASO B/C
# (F3.2 / F5.3) — sem elas o gate recusa antes de chegar ao nudge de leitura.
# `approved` é a marca do de acordo no contrato autoral; `ready` é só "escrito".
aprovado() { printf -- '---\nauthored-by: human\nstatus: approved\napproved: 2026-08-03\nscope: []\n---\n# %s\n' "$2" > "$1"; }
aprovado "$DOCD/.claude/docs/quality-goals.md" Metas
aprovado "$DOCD/.claude/docs/architecture-intent.md" "Arquitetura pretendida"
aprovado "$DOCD/.claude/docs/journeys.md" Jornadas

AUTH="$TMP/projeto-so-autoral"     # start-doc começou, índice ainda não existe
mkdir -p "$AUTH/.claude/docs" && (cd "$AUTH" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf -- '---\nauthored-by: human\nstatus: draft\n---\n# Metas\n' > "$AUTH/.claude/docs/quality-goals.md"

# MESMO helper que os hooks usam. Recalcular a chave à mão aqui foi exatamente
# o que mascarou o bug de path na 1ª rodada — o teste tem que falar a mesma língua.
. "$SCRIPT_DIR/lib-project-root.sh"
phash() { project_hash "$(project_root "$1")"; }

gate() { # gate <tool> <cwd>
  printf '{"tool_name":"%s","session_id":"%s","cwd":"%s"}' "$1" "$SESSION" "$2" | bash "$GATE" 2>/dev/null
}
escape() { # escape <prompt> <cwd>
  printf '{"prompt":%s,"session_id":"%s","cwd":"%s"}' "$(printf '%s' "$1" | jq -Rs .)" "$SESSION" "$2" | bash "$ESC" 2>/dev/null
}
# Saída VAZIA = hook saiu 0 sem opinar = allow. `jq` sobre stdin vazio não emite
# nada (nem o `// "allow"`), então o default tem que ser tratado aqui.
decision() {
  [ -z "$1" ] && { echo allow; return; }
  printf '%s' "$1" | jq -r '.hookSpecificOutput.permissionDecision // "allow"' 2>/dev/null
}
reason()   { printf '%s' "$1" | jq -r '.hookSpecificOutput.permissionDecisionReason // ""' 2>/dev/null; }

# A régua de forma do repo, perfil "hook" — a mesma que o gerador de página usa.
# A cópia vendorada do próprio plugin (fonte em _shared/, vendorada por sync-shared.sh):
# o plugin instalado só enxerga a própria pasta.
REGUA_DIR="$SCRIPT_DIR/../lib"
# estilo_hook <texto> — imprime os erros de estilo; saída vazia = passou na régua.
estilo_hook() {
  [ -f "$REGUA_DIR/regua_texto.py" ] || { echo "régua não encontrada em $REGUA_DIR"; return; }
  MSG_TXT="$1" python3 - "$REGUA_DIR" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1])
from regua_texto import erros_de_estilo
linhas = [l for l in os.environ["MSG_TXT"].splitlines() if l.strip()]
for e in erros_de_estilo(linhas, "msg", "hook"):
    print(e)
PY
}

echo "── Gate de plano ──"

# 1) projeto sem doc -> DENY mandando /start-doc
OUT=$(gate EnterPlanMode "$BARE"); D=$(decision "$OUT")
[ "$D" = "deny" ] && ok "sem doc: EnterPlanMode negado" || bad "sem doc: EnterPlanMode negado" deny "$D"
case "$(reason "$OUT")" in *"/start-doc"*) ok "sem doc: a mensagem manda rodar /start-doc" ;;
  *) bad "sem doc: mensagem cita /start-doc" "cita /start-doc" "$(reason "$OUT" | head -c 60)" ;; esac

# 2) ExitPlanMode também é barrado (a rede — é a ponta comprovadamente hookável)
D=$(decision "$(gate ExitPlanMode "$BARE")")
[ "$D" = "deny" ] && ok "sem doc: ExitPlanMode também negado" || bad "sem doc: ExitPlanMode negado" deny "$D"

# 3) nega SEMPRE — sem cap. 5 tentativas seguidas, todas negadas.
ALL_DENY=1
for _ in 1 2 3 4 5; do [ "$(decision "$(gate EnterPlanMode "$BARE")")" = "deny" ] || ALL_DENY=0; done
[ "$ALL_DENY" = 1 ] && ok "sem doc: nega nas 5 tentativas (sem cap de nudges)" \
                    || bad "sem doc: nega sempre" "5 denies" "houve allow"

# 4) autoral iniciado mas sem índice -> ainda nega, com mensagem diferente
OUT=$(gate EnterPlanMode "$AUTH")
[ "$(decision "$OUT")" = "deny" ] && ok "autoral parcial: ainda negado" || bad "autoral parcial: negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"1 de 5"*) ok "autoral parcial: reporta 1 de 5 documentos" ;;
  *) bad "autoral parcial: conta os autorais" "1 de 5" "$(reason "$OUT" | head -c 60)" ;; esac

# 5) tem doc, não lida -> DENY mandando ler
OUT=$(gate EnterPlanMode "$DOCD")
[ "$(decision "$OUT")" = "deny" ] && ok "com doc não lida: negado" || bad "com doc não lida: negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"não foi lida"*) ok "com doc não lida: manda ler" ;;
  *) bad "com doc não lida: manda ler" "'não foi lida'" "$(reason "$OUT" | head -c 60)" ;; esac

# 6) tem doc E foi lida (sentinel do posttooluse-doc-read) -> passa mudo
SENT="/tmp/claude-doc-guard-${SESSION}-$(phash "$DOCD")"; : > "$SENT"
OUT=$(gate EnterPlanMode "$DOCD")
[ -z "$OUT" ] && ok "com doc lida: passa em silêncio" || bad "com doc lida: passa" "vazio" "$OUT"
rm -f "$SENT"

# 7) cap de 3 no caso 'doc não lida' (contrato anti-loop do repo)
rm -f "/tmp/claude-plan-gate-count-${SESSION}-$(phash "$DOCD")"
R=""; for _ in 1 2 3 4; do R="$R$(decision "$(gate EnterPlanMode "$DOCD")")|"; done
[ "$R" = "deny|deny|deny|allow|" ] && ok "com doc não lida: cap de 3 nudges, depois libera" \
                                   || bad "cap de 3 nudges" "deny|deny|deny|allow|" "$R"

# 8) ferramenta que não é de plano -> ignora
OUT=$(gate Edit "$BARE")
[ -z "$OUT" ] && ok "tool fora do escopo (Edit): ignorado" || bad "tool fora do escopo" "vazio" "$OUT"

# 9) fora de projeto ($HOME) -> não gateia
OUT=$(gate EnterPlanMode "$HOME")
[ -z "$OUT" ] && ok "\$HOME: não é projeto, não gateia" || bad "\$HOME não gateia" "vazio" "$OUT"

echo "── Escape verbal ──"

esc_file() { echo "/tmp/claude-plan-gate-escape-${SESSION}-$(phash "$BARE")"; }

# 10) frases imperativas liberam
for P in "ignora a doc" "pula a documentação" "pode planejar sem doc" "dispensa a doc" "--sem-doc" "vai sem documentacao"; do
  rm -f "$(esc_file)"
  escape "$P" "$BARE" >/dev/null
  [ -f "$(esc_file)" ] && ok "escape reconhece: \"$P\"" || bad "escape reconhece \"$P\"" "sentinel criado" "nada"
done

# 11) CONSTATAÇÃO não libera (o falso-positivo que mataria o gate)
for P in "esse projeto está sem documentação" "a documentação não existe aqui" "queria ver a doc"; do
  rm -f "$(esc_file)"
  escape "$P" "$BARE" >/dev/null
  [ ! -f "$(esc_file)" ] && ok "escape NÃO dispara em: \"$P\"" || bad "escape não dispara \"$P\"" "sem sentinel" "criou sentinel"
done

# 12) fim-a-fim: verbalizou -> o gate passa a liberar
rm -f "$(esc_file)"
[ "$(decision "$(gate EnterPlanMode "$BARE")")" = "deny" ] && ok "e2e: antes de verbalizar, o plano é barrado" \
                                                          || bad "e2e: antes do escape" deny allow
escape "ignora a doc" "$BARE" >/dev/null
OUT=$(gate EnterPlanMode "$BARE")
[ -z "$OUT" ] && ok "e2e: depois de verbalizar, o plano passa" || bad "e2e: escape libera o gate" "vazio" "$OUT"

# 13) o escape avisa o modelo uma vez só
rm -f "$(esc_file)"
A=$(escape "ignora a doc" "$BARE"); B=$(escape "ignora a doc" "$BARE")
{ [ -n "$A" ] && [ -z "$B" ]; } && ok "escape avisa 1×, depois cala" || bad "escape avisa uma vez" "1º com saída, 2º vazio" "1º='$A' 2º='$B'"

echo "── Regressões da revisão de 2026-07-26 ──"

# R1) CONSTATAÇÃO não pode liberar. Sem fronteira de palavra, "esta+VA sem doc" e
#     "con+SEGUE sem doc" liberavam o gate. São os falsos-positivos que o Opus achou.
for P in "esse projeto estava sem documentação" "o repo ficava sem documentação nenhuma" \
         "o time não consegue sem documentação" "esse módulo chegava sem doc" \
         "a gente estava sem doc até ontem"; do
  rm -f "$(esc_file)"; escape "$P" "$BARE" >/dev/null
  [ ! -f "$(esc_file)" ] && ok "constatação NÃO libera: \"$P\"" \
                         || bad "constatação não libera \"$P\"" "sem sentinel" "LIBEROU"
done

# R2) Doc de TERCEIRO não é ordem sobre a doc deste projeto.
for P in "ignora a doc do React, usa o código real" "ignora a documentação do Stripe, ela está errada" \
         "pula a documentação da lib e olha o fonte"; do
  rm -f "$(esc_file)"; escape "$P" "$BARE" >/dev/null
  [ ! -f "$(esc_file)" ] && ok "doc de terceiro NÃO libera: \"$P\"" \
                         || bad "doc de terceiro não libera \"$P\"" "sem sentinel" "LIBEROU"
done

# R3) Falsos-NEGATIVOS que travavam o usuário (o CASO A nega sem cap).
for P in "planeja sem a documentação" "pode planejar sem a doc" "esquece a doc" \
         "faz o plano sem doc" "segue sem a doc" "ignora essa doc" "deixa a doc pra lá"; do
  rm -f "$(esc_file)"; escape "$P" "$BARE" >/dev/null
  [ -f "$(esc_file)" ] && ok "escape reconhece: \"$P\"" \
                       || bad "escape reconhece \"$P\"" "sentinel criado" "nada"
done

# R4) --sem-doc vence a ambiguidade (é o token garantido citado na mensagem do deny).
rm -f "$(esc_file)"; escape "ignora a doc do React --sem-doc" "$BARE" >/dev/null
[ -f "$(esc_file)" ] && ok "--sem-doc vence a ambiguidade" || bad "--sem-doc vence" "sentinel" "nada"

# R5) REVOGAÇÃO — a válvula pro falso-positivo que sobrar.
rm -f "$(esc_file)"; escape "--sem-doc" "$BARE" >/dev/null
[ -f "$(esc_file)" ] || bad "setup da revogação" "sentinel" "nada"
OUT=$(escape "--com-doc" "$BARE")
{ [ ! -f "$(esc_file)" ] && [ -n "$OUT" ]; } && ok "--com-doc revoga e avisa" \
                                            || bad "--com-doc revoga" "sentinel apagado + aviso" "nao revogou"
[ "$(decision "$(gate EnterPlanMode "$BARE")")" = "deny" ] && ok "após revogar, o gate volta a barrar" \
                                                          || bad "gate volta após revogar" deny allow
rm -f "$(esc_file)"

# R6) CLAUDE.md escrito à mão SEM .claude/docs/ era negado PARA SEMPRE, com mensagem
#     mentindo "sem CLAUDE.md". Documentação à mão É documentação: vira CASO B (com cap).
HAND="$TMP/projeto-md-manual"
mkdir -p "$HAND" && (cd "$HAND" && git init -q .)
printf '# Meu projeto\nAnotações à mão.\n' > "$HAND/CLAUDE.md"
rm -f "/tmp/claude-plan-gate-count-${SESSION}-$(phash "$HAND")"
OUT=$(gate EnterPlanMode "$HAND")
[ "$(decision "$OUT")" = "deny" ] && ok "CLAUDE.md manual: negado (manda ler)" || bad "CLAUDE.md manual negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in
  *"escrito à mão"*) ok "CLAUDE.md manual: mensagem reconhece o arquivo (não mente)" ;;
  *) bad "mensagem do CLAUDE.md manual" "cita 'escrito à mão'" "$(reason "$OUT" | head -c 70)" ;;
esac
R=""; for _ in 1 2 3; do R="$R$(decision "$(gate EnterPlanMode "$HAND")")|"; done
[ "$R" = "deny|deny|allow|" ] && ok "CLAUDE.md manual: tem cap (não nega pra sempre)" \
                              || bad "CLAUDE.md manual tem cap" "deny|deny|allow|" "$R"

# R7) FAIL-OPEN de infra: helper ilegível NÃO é "projeto sem doc".
FAKE="$TMP/hooks-quebrados"
mkdir -p "$FAKE"
cp "$SCRIPT_DIR"/*.sh "$FAKE/" 2>/dev/null
mkdir -p "$TMP/hooks-quebrados-lib" && cp -r "$SCRIPT_DIR/../lib" "$TMP/hooks-quebrados-lib/lib" 2>/dev/null
chmod 000 "$FAKE/doc-detect.sh"
OUT=$(printf '{"tool_name":"EnterPlanMode","session_id":"%s","cwd":"%s"}' "$SESSION" "$DOCD" | bash "$FAKE/pretooluse-plan-gate.sh" 2>/dev/null)
chmod 644 "$FAKE/doc-detect.sh"
[ -z "$OUT" ] && ok "doc-detect ilegível: fail-OPEN (não nega às cegas)" \
              || bad "fail-open com helper ilegível" "vazio" "$(printf '%s' "$OUT" | head -c 60)"

# R8) Barra final no cwd não pode quebrar a chave do sentinel.
SENT="/tmp/claude-doc-guard-${SESSION}-$(phash "$DOCD")"; : > "$SENT"
OUT=$(gate EnterPlanMode "$DOCD/")
[ -z "$OUT" ] && ok "cwd com barra final: sentinel ainda casa" || bad "barra final casa" "vazio" "denied"
rm -f "$SENT"

# R9) E2E REAL do sentinel: quem escreve é o posttooluse-doc-read.sh, por RECORTE DE
#     STRING do file_path — não pelo helper. Se as duas derivações divergirem, o gate
#     nunca libera. O teste antigo era tautológico (escrevia o sentinel com o helper).
rm -f "/tmp/claude-doc-guard-${SESSION}-$(phash "$DOCD")" "/tmp/claude-plan-gate-count-${SESSION}-$(phash "$DOCD")"
[ "$(decision "$(gate EnterPlanMode "$DOCD")")" = "deny" ] || bad "E2E setup: deveria negar antes do Read" deny allow
printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s"}}' \
  "$SESSION" "$DOCD" "$DOCD/.claude/docs/architecture.md" | bash "$SCRIPT_DIR/posttooluse-doc-read.sh" >/dev/null 2>&1
OUT=$(gate EnterPlanMode "$DOCD")
[ -z "$OUT" ] && ok "E2E: Read real -> posttooluse escreve -> gate libera" \
              || bad "E2E posttooluse->gate" "vazio (liberado)" "ainda nega — CHAVE DIVERGIU"

# R10) E2E pela raiz: Read no CLAUDE.md da raiz também resolve.
rm -f "/tmp/claude-doc-guard-${SESSION}-$(phash "$DOCD")" "/tmp/claude-plan-gate-count-${SESSION}-$(phash "$DOCD")"
printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s"}}' \
  "$SESSION" "$DOCD" "$DOCD/CLAUDE.md" | bash "$SCRIPT_DIR/posttooluse-doc-read.sh" >/dev/null 2>&1
OUT=$(gate EnterPlanMode "$DOCD")
[ -z "$OUT" ] && ok "E2E: Read no CLAUDE.md da raiz também libera" \
              || bad "E2E raiz" "vazio" "ainda nega"

echo "── Acordo: constituição e etapas (F3.2 / F5.3) ──"

# ACORDO — fixture própria: doc minerada completa, acordo a ser montado passo a passo.
ACC="$TMP/projeto-acordo"
mkdir -p "$ACC/.claude/docs" && (cd "$ACC" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf '<!-- project-doc:v2 gen=3.8 -->\n# Project Reference\n<!-- project-doc:v2:end -->\n' > "$ACC/CLAUDE.md"
printf -- '---\ngenerated: 2026-07-26\nscope:\n  - x.py\n---\n# Arch\n' > "$ACC/.claude/docs/architecture.md"
acc_reset() { rm -f "/tmp/claude-plan-gate-count-${SESSION}-$(phash "$ACC")" \
                    "/tmp/claude-doc-guard-${SESSION}-$(phash "$ACC")" \
                    "/tmp/claude-plan-gate-escape-${SESSION}-$(phash "$ACC")"; }
acc_reset

# A1) doc existe, constituição do projeto NÃO -> recusa nomeando o motivo (F3.2)
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "sem quality-goals.md: negado (F3.2 — hoje calava)" \
                                  || bad "sem quality-goals: negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"quality-goals.md"*) ok "sem quality-goals.md: a mensagem nomeia o documento" ;;
  *) bad "mensagem nomeia quality-goals.md" "cita quality-goals.md" "$(reason "$OUT" | head -c 70)" ;; esac

# A2) recusa não tem cap — 5 tentativas, 5 denies
ALL_DENY=1
for _ in 1 2 3 4 5; do [ "$(decision "$(gate EnterPlanMode "$ACC")")" = "deny" ] || ALL_DENY=0; done
[ "$ALL_DENY" = 1 ] && ok "sem quality-goals.md: recusa nas 5 (sem cap)" \
                    || bad "sem quality-goals sem cap" "5 denies" "houve allow"

# A3) constituição EM ABERTO (draft) também é recusada
printf -- '---\nauthored-by: human\nstatus: draft\nscope: []\n---\n# Metas\n[PENDENTE]\n' > "$ACC/.claude/docs/quality-goals.md"
acc_reset
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "quality-goals.md draft: negado (aberto não é acordado)" \
                                  || bad "quality-goals draft negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"em aberto"*) ok "quality-goals.md draft: mensagem diz que está em aberto" ;;
  *) bad "mensagem do draft" "'em aberto'" "$(reason "$OUT" | head -c 70)" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa por constituição: a mensagem passa na régua (perfil hook)" \
            || bad "régua da mensagem de constituição" "sem erros de estilo" "$E"

# A4) O CASO S-4.1 — projeto NOVO: os 5 autorais fechados e NENHUMA etapa de acordo
#     iniciada. Enquanto a cobrança exigia que um dos documentos já existisse, este
#     projeto passava batido — é justamente quem mais precisa ser barrado.
for d in quality-goals constraints context solution-strategy glossary; do
  aprovado "$ACC/.claude/docs/${d}.md" "$d"
done
acc_reset
: > "/tmp/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "projeto novo sem architecture-intent: negado (S-4.1)" \
                                  || bad "projeto novo negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"arquitetura (architecture-intent.md)"*) ok "projeto novo: a mensagem nomeia architecture-intent.md" ;;
  *) bad "nomeia architecture-intent.md" "'arquitetura (architecture-intent.md)'" "$(reason "$OUT" | head -c 90)" ;; esac
case "$(reason "$OUT")" in *"jornadas (journeys.md)"*) ok "projeto novo: a mensagem nomeia journeys.md" ;;
  *) bad "nomeia journeys.md" "'jornadas (journeys.md)'" "$(reason "$OUT" | head -c 90)" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa por etapa: a mensagem passa na régua (perfil hook)" \
            || bad "régua da mensagem de etapa" "sem erros de estilo" "$E"

# A5) O CRITÉRIO DE PRONTO — arquitetura fechada e as jornadas em aberto: o plano é
#     NEGADO, e a mensagem nomeia a etapa que falta. A etapa 2 é o architecture-intent
#     (o desenho pretendido); solution-strategy é da etapa 1, junto com os 5 autorais.
aprovado "$ACC/.claude/docs/architecture-intent.md" "Arquitetura pretendida"
printf -- '---\nauthored-by: human\nstatus: draft\nscope: []\n---\n# Jornadas\n[PENDENTE]\n' > "$ACC/.claude/docs/journeys.md"
acc_reset
: > "/tmp/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "jornadas em aberto: plano negado (F5.3)" \
                                  || bad "jornadas em aberto: negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"jornadas (journeys.md)"*) ok "jornadas em aberto: a mensagem nomeia a etapa" ;;
  *) bad "mensagem nomeia a etapa" "'jornadas (journeys.md)'" "$(reason "$OUT" | head -c 90)" ;; esac
# a etapa FECHADA não pode aparecer na lista de abertas (a ordem citada na
# mensagem menciona "arquitetura", por isso a busca é pelo par nome+arquivo)
case "$(reason "$OUT")" in *"arquitetura (architecture-intent.md)"*) bad "não cita etapa já fechada" "sem 'arquitetura (architecture-intent.md)'" "cobrou etapa fechada" ;;
  *) ok "jornadas em aberto: a etapa já fechada não é cobrada" ;; esac

# A6) ExitPlanMode — a rede também barra
D=$(decision "$(gate ExitPlanMode "$ACC")")
[ "$D" = "deny" ] && ok "jornadas em aberto: ExitPlanMode também negado" || bad "ExitPlanMode negado" deny "$D"

# A7) etapa pulada (documento nem existe) é igual a etapa em aberto
rm -f "$ACC/.claude/docs/journeys.md"
acc_reset
: > "/tmp/claude-doc-guard-${SESSION}-$(phash "$ACC")"
case "$(reason "$(gate EnterPlanMode "$ACC")")" in *"jornadas (journeys.md)"*) ok "etapa PULADA conta como em aberto" ;;
  *) bad "etapa pulada" "'jornadas (journeys.md)'" "não cobrou" ;; esac

# A8) escape verbal libera também a recusa por etapa
acc_reset
escape "--sem-doc" "$ACC" >/dev/null
: > "/tmp/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "escape verbal libera a recusa por etapa" || bad "escape libera etapa" "vazio" "ainda nega"

# A9) OS 7 DOCUMENTOS FECHADOS COMO O /start-doc MANDA (status: approved + approved:)
#     -> o gate cala. É o impasse que o contrato autoral e o gate tinham: o contrato
#     grava `approved` e o gate cobrava `ready`, e nada fechava o acordo.
acc_reset
aprovado "$ACC/.claude/docs/journeys.md" Jornadas
: > "/tmp/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "os 7 documentos approved: passa em silêncio" || bad "7 approved passa" "vazio" "$(reason "$OUT" | head -c 90)"
acc_reset

echo
printf '%s\n' "── $PASS passou · $FAIL falhou ──"
[ "$FAIL" -eq 0 ]
