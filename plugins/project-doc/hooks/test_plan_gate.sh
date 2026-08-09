#!/bin/bash
# test_plan_gate.sh — suíte do gate de plano + do escape verbal.
# Roda isolado em /tmp; não toca projeto nenhum. Uso: bash test_plan_gate.sh

# Os hooks gravam no temporário DO SISTEMA — a suíte pergunta pelo mesmo caminho
# que eles, em vez de assumir /tmp.
# shellcheck source=/dev/null
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib-tmpdir.sh"
TMPD=$(td_tmpdir)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE="$SCRIPT_DIR/pretooluse-plan-gate.sh"
ESC="$SCRIPT_DIR/userpromptsubmit-plan-escape.sh"
PASS=0; FAIL=0
SESSION="test-$$"

ok()   { PASS=$((PASS+1)); printf '  ✓ %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  ✗ %s\n     esperado: %s\n     obtido:   %s\n' "$1" "$2" "$3"; }

TMP=$(mktemp -d)
# Cache falso de plugin: o nome de invocação da rodada se DESCOBRE (resolve-skill.sh),
# e a suíte não pode depender do que ESTA máquina tem instalado.
FAKE_CACHE="$TMP/cfg/plugins/cache/mkt/project-skills/1.0.0"
mkdir -p "$FAKE_CACHE/lib" "$FAKE_CACHE/skills/doc" "$FAKE_CACHE/skills/doc-touch"
# ...e o IRMÃO de onde ela vem também se acha por NOME (Artigo 9), nunca por posição.
RS_SRC=$(CLAUDE_PLUGIN_ROOT="$SCRIPT_DIR/.." "$SCRIPT_DIR/resolve-plugin.sh" \
           project-skills lib/resolve-skill.sh) || {
  printf 'SKIP: project-skills não está nesta máquina\n'; exit 0; }
cp "$RS_SRC" "$FAKE_CACHE/lib/"
: > "$FAKE_CACHE/skills/doc/SKILL.md"; : > "$FAKE_CACHE/skills/doc-touch/SKILL.md"
unset CLAUDE_PLUGIN_ROOT
export CLAUDE_CONFIG_DIR="$TMP/cfg"
trap 'rm -rf "$TMP"; rm -f "$TMPD"/claude-plan-gate-*-'"$SESSION"'-* "$TMPD"/claude-doc-guard-'"$SESSION"'-*' EXIT

# --- fixtures -------------------------------------------------------------
BARE="$TMP/projeto-sem-doc"        # git repo, zero documentação
mkdir -p "$BARE" && (cd "$BARE" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)

DOCD="$TMP/projeto-com-doc"        # git repo com CLAUDE.md v2 + .claude/docs/
mkdir -p "$DOCD/.claude/docs" && (cd "$DOCD" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf '<!-- project-doc:v2 gen=3.8 -->\n# Project Reference\n<!-- project-doc:v2:end -->\n' > "$DOCD/CLAUDE.md"
printf -- '---\ngenerated: 2026-07-26\nscope:\n  - x.py\ndoc-sig: a/b@gen=3.8#deadbeef\n---\n# Arch\n' > "$DOCD/.claude/docs/architecture.md"
# As metas de qualidade do projeto e as etapas do acordo são pré-requisito do CASO B/C
# (F3.2 / F5.3) — sem elas o gate recusa antes de chegar ao nudge de leitura.
# `approved` é a marca do de acordo no contrato autoral; `ready` é só "escrito".
aprovado() { printf -- '---\nauthored-by: human\nstatus: approved\napproved: 2026-08-03\nscope: []\n---\n# %s\n' "$2" > "$1"; }
aprovado "$DOCD/.claude/docs/quality-goals.md" Metas
aprovado "$DOCD/.claude/docs/architecture-intent.md" "Arquitetura pretendida"
aprovado "$DOCD/.claude/docs/journeys.md" Jornadas
aprovado "$DOCD/.claude/docs/blueprint.md" Esquema
aprovado "$DOCD/.claude/docs/features.md" Funcionalidades

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

# 4b) S-105 — dispensa deliberada x ausência silenciosa. Um teste por lado, sobre o
#     MESMO projeto sem documentação: o que muda é só o arquivo da dispensa.
DISP="$TMP/projeto-dispensado"
mkdir -p "$DISP/.claude/docs" && (cd "$DISP" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)

# lado 1 — ausência: dispensa escrita SEM motivo não é dispensa, e o gate nomeia o arquivo
printf -- '---\nauthored-by: human\n---\n# Dispensa\n' > "$DISP/.claude/docs/dispensa.md"
OUT=$(gate EnterPlanMode "$DISP")
[ "$(decision "$OUT")" = "deny" ] && ok "dispensa sem motivo: continua sendo ausência, negado" \
                                  || bad "dispensa sem motivo negada" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"dispensa.md"*) ok "dispensa sem motivo: a mensagem nomeia o arquivo" ;;
  *) bad "mensagem nomeia dispensa.md" "cita dispensa.md" "$(reason "$OUT" | head -c 80)" ;; esac
# Artigo 6: o aviso da dispensa é texto de hook — teto BULLET_MAX=140 de `_shared/regua_texto.py`.
# `awk` mede bytes, não caracteres: acento conta a mais, então a conta é conservadora.
DLEN=$(awk -F'ESC_HINT="' '/\[ -f "\$DISPENSA" \] && ESC_HINT=/{sub(/"$/,"",$2); gsub(/\\/,"",$2); print length($2)}' "$GATE")
[ "${DLEN:-999}" -le 140 ] && ok "aviso da dispensa cabe na régua ($DLEN ≤ 140)" \
                           || bad "aviso da dispensa na régua" "≤140" "$DLEN"

# lado 2 — dispensa: com `motivo:` no frontmatter o gate libera, e em silêncio
printf -- '---\nauthored-by: human\nmotivo: protótipo descartável de uma tarde\n---\n# Dispensa\n' > "$DISP/.claude/docs/dispensa.md"
OUT=$(gate EnterPlanMode "$DISP")
[ -z "$OUT" ] && ok "dispensa com motivo: passa em silêncio" || bad "dispensa com motivo passa" "vazio" "$OUT"

# e ela dura: nada de sentinel de sessão, o arquivo vale em sessão nova
OUT=$(printf '{"tool_name":"EnterPlanMode","session_id":"outra-%s","cwd":"%s"}' "$$" "$DISP" | bash "$GATE" 2>/dev/null)
[ -z "$OUT" ] && ok "dispensa com motivo: vale em outra sessão" || bad "dispensa entre sessões" "vazio" "$OUT"

# 5) tem doc, não lida -> DENY mandando ler
OUT=$(gate EnterPlanMode "$DOCD")
[ "$(decision "$OUT")" = "deny" ] && ok "com doc não lida: negado" || bad "com doc não lida: negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"não foi lida"*) ok "com doc não lida: manda ler" ;;
  *) bad "com doc não lida: manda ler" "'não foi lida'" "$(reason "$OUT" | head -c 60)" ;; esac

# 6) tem doc E foi lida (sentinel do posttooluse-doc-read) -> passa mudo
SENT="$TMPD/claude-doc-guard-${SESSION}-$(phash "$DOCD")"; : > "$SENT"
OUT=$(gate EnterPlanMode "$DOCD")
[ -z "$OUT" ] && ok "com doc lida: passa em silêncio" || bad "com doc lida: passa" "vazio" "$OUT"
rm -f "$SENT"

# 7) cap de 3 no caso 'doc não lida' (contrato anti-loop do repo)
rm -f "$TMPD/claude-plan-gate-count-${SESSION}-$(phash "$DOCD")"
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

esc_file() { echo "$TMPD/claude-plan-gate-escape-${SESSION}-$(phash "$BARE")"; }

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
rm -f "$TMPD/claude-plan-gate-count-${SESSION}-$(phash "$HAND")"
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
SENT="$TMPD/claude-doc-guard-${SESSION}-$(phash "$DOCD")"; : > "$SENT"
OUT=$(gate EnterPlanMode "$DOCD/")
[ -z "$OUT" ] && ok "cwd com barra final: sentinel ainda casa" || bad "barra final casa" "vazio" "denied"
rm -f "$SENT"

# R9) E2E REAL do sentinel: quem escreve é o posttooluse-doc-read.sh, por RECORTE DE
#     STRING do file_path — não pelo helper. Se as duas derivações divergirem, o gate
#     nunca libera. O teste antigo era tautológico (escrevia o sentinel com o helper).
rm -f "$TMPD/claude-doc-guard-${SESSION}-$(phash "$DOCD")" "$TMPD/claude-plan-gate-count-${SESSION}-$(phash "$DOCD")"
[ "$(decision "$(gate EnterPlanMode "$DOCD")")" = "deny" ] || bad "E2E setup: deveria negar antes do Read" deny allow
printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s"}}' \
  "$SESSION" "$DOCD" "$DOCD/.claude/docs/architecture.md" | bash "$SCRIPT_DIR/posttooluse-doc-read.sh" >/dev/null 2>&1
OUT=$(gate EnterPlanMode "$DOCD")
[ -z "$OUT" ] && ok "E2E: Read real -> posttooluse escreve -> gate libera" \
              || bad "E2E posttooluse->gate" "vazio (liberado)" "ainda nega — CHAVE DIVERGIU"

# R10) E2E pela raiz: Read no CLAUDE.md da raiz também resolve.
rm -f "$TMPD/claude-doc-guard-${SESSION}-$(phash "$DOCD")" "$TMPD/claude-plan-gate-count-${SESSION}-$(phash "$DOCD")"
printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s"}}' \
  "$SESSION" "$DOCD" "$DOCD/CLAUDE.md" | bash "$SCRIPT_DIR/posttooluse-doc-read.sh" >/dev/null 2>&1
OUT=$(gate EnterPlanMode "$DOCD")
[ -z "$OUT" ] && ok "E2E: Read no CLAUDE.md da raiz também libera" \
              || bad "E2E raiz" "vazio" "ainda nega"

echo "── Acordo: metas de qualidade e etapas (F3.2 / F5.3) ──"

# ACORDO — fixture própria: doc minerada completa, acordo a ser montado passo a passo.
ACC="$TMP/projeto-acordo"
mkdir -p "$ACC/.claude/docs" && (cd "$ACC" && git init -q . && git commit -q --allow-empty -m x 2>/dev/null)
printf '<!-- project-doc:v2 gen=3.8 -->\n# Project Reference\n<!-- project-doc:v2:end -->\n' > "$ACC/CLAUDE.md"
printf -- '---\ngenerated: 2026-07-26\nscope:\n  - x.py\n---\n# Arch\n' > "$ACC/.claude/docs/architecture.md"
acc_reset() { rm -f "$TMPD/claude-plan-gate-count-${SESSION}-$(phash "$ACC")" \
                    "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")" \
                    "$TMPD/claude-plan-gate-escape-${SESSION}-$(phash "$ACC")"; }
acc_reset

# A1) doc existe, metas de qualidade do projeto NÃO -> recusa nomeando o motivo (F3.2)
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

# A3) metas de qualidade EM ABERTO (draft) também são recusadas
printf -- '---\nauthored-by: human\nstatus: draft\nscope: []\n---\n# Metas\n[PENDENTE]\n' > "$ACC/.claude/docs/quality-goals.md"
acc_reset
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "quality-goals.md draft: negado (aberto não é acordado)" \
                                  || bad "quality-goals draft negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"em aberto"*) ok "quality-goals.md draft: mensagem diz que está em aberto" ;;
  *) bad "mensagem do draft" "'em aberto'" "$(reason "$OUT" | head -c 70)" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa por metas de qualidade: a mensagem passa na régua (perfil hook)" \
            || bad "régua da mensagem de metas de qualidade" "sem erros de estilo" "$E"

# A3b) F1.3 — "constituição" é o nome de .claude/docs/constituicao.md, o arquivo contra
#      o qual os revisores medem. A recusa por quality-goals.md tem que chamá-lo pelo
#      que ele é (as metas de qualidade); dois arquivos com o mesmo nome de lei mandam
#      o leitor abrir o errado.
case "$(reason "$OUT")" in *[Cc]onstitui*) bad "recusa por quality-goals não chama o arquivo de constituição" "sem 'constituição'" "$(reason "$OUT" | head -c 90)" ;;
  *) ok "recusa por quality-goals: não usa o nome constituição" ;; esac
case "$(reason "$OUT")" in *"metas de qualidade"*) ok "recusa por quality-goals: chama de metas de qualidade" ;;
  *) bad "nomeia as metas de qualidade" "'metas de qualidade'" "$(reason "$OUT" | head -c 90)" ;; esac

# A4) O CASO S-4.1 — projeto NOVO: os 5 autorais fechados e NENHUMA etapa de acordo
#     iniciada. Enquanto a cobrança exigia que um dos documentos já existisse, este
#     projeto passava batido — é justamente quem mais precisa ser barrado.
for d in quality-goals constraints context solution-strategy glossary; do
  aprovado "$ACC/.claude/docs/${d}.md" "$d"
done
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
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
# F1.3 — a ordem citada na recusa por etapa também não pode batizar as metas de
# qualidade de constituição.
case "$(reason "$OUT")" in *[Cc]onstitui*) bad "recusa por etapa não chama a 1ª etapa de constituição" "sem 'constituição'" "$(reason "$OUT" | head -c 90)" ;;
  *) ok "recusa por etapa: não usa o nome constituição" ;; esac

# A5) O CRITÉRIO DE PRONTO — arquitetura fechada e as jornadas em aberto: o plano é
#     NEGADO, e a mensagem nomeia a etapa que falta. A etapa 2 é o architecture-intent
#     (o desenho pretendido); solution-strategy é da etapa 1, junto com os 5 autorais.
aprovado "$ACC/.claude/docs/architecture-intent.md" "Arquitetura pretendida"
printf -- '---\nauthored-by: human\nstatus: draft\nscope: []\n---\n# Jornadas\n[PENDENTE]\n' > "$ACC/.claude/docs/journeys.md"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
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
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
case "$(reason "$(gate EnterPlanMode "$ACC")")" in *"jornadas (journeys.md)"*) ok "etapa PULADA conta como em aberto" ;;
  *) bad "etapa pulada" "'jornadas (journeys.md)'" "não cobrou" ;; esac

# A8) escape verbal libera também a recusa por etapa
acc_reset
escape "--sem-doc" "$ACC" >/dev/null
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "escape verbal libera a recusa por etapa" || bad "escape libera etapa" "vazio" "ainda nega"

# A8b) S-5 — a QUINTA etapa: funcionalidades (features.md). Ela é derivada das quatro
#      anteriores, e enquanto não está acordada o plano implementa a lista que o dono
#      nunca curou. As quatro fechadas e só ela em aberto: o plano é NEGADO, nomeando-a.
acc_reset
aprovado "$ACC/.claude/docs/journeys.md" Jornadas
printf -- '---\nauthored-by: human\nstatus: draft\nscope: []\n---\n# Funcionalidades\n[PENDENTE]\n' > "$ACC/.claude/docs/features.md"
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "funcionalidades em aberto: plano negado (S-5)" \
                                  || bad "funcionalidades em aberto: negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"funcionalidades (features.md)"*) ok "funcionalidades em aberto: a mensagem nomeia a etapa" ;;
  *) bad "mensagem nomeia a etapa" "'funcionalidades (features.md)'" "$(reason "$OUT" | head -c 90)" ;; esac
case "$(reason "$OUT")" in *"jornadas (journeys.md)"*) bad "não cita etapa já fechada" "sem 'jornadas (journeys.md)'" "cobrou etapa fechada" ;;
  *) ok "funcionalidades em aberto: a etapa já fechada não é cobrada" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa por funcionalidades: a mensagem passa na régua (perfil hook)" \
            || bad "régua da mensagem de funcionalidades" "sem erros de estilo" "$E"

# A8c) etapa 5 PULADA (o documento nem existe) é igual a etapa em aberto
rm -f "$ACC/.claude/docs/features.md"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
case "$(reason "$(gate EnterPlanMode "$ACC")")" in *"funcionalidades (features.md)"*) ok "features.md ausente conta como em aberto" ;;
  *) bad "etapa 5 pulada" "'funcionalidades (features.md)'" "não cobrou" ;; esac

# A8d) S-70 — a etapa do ESQUEMA (blueprint.md): o desenho de como o sistema funciona.
#      As cinco primeiras etapas aprovadas e só o blueprint ausente: o plano é NEGADO,
#      e a recusa nomeia a etapa. Sem isso a lista de funcionalidades seria derivada de
#      um desenho que ninguém bateu o martelo.
acc_reset
aprovado "$ACC/.claude/docs/journeys.md" Jornadas
aprovado "$ACC/.claude/docs/features.md" Funcionalidades
rm -f "$ACC/.claude/docs/blueprint.md"
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "blueprint.md ausente: plano negado (S-70)" \
                                  || bad "blueprint ausente: negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"esquema (blueprint.md)"*) ok "blueprint.md ausente: a mensagem nomeia a etapa" ;;
  *) bad "mensagem nomeia a etapa" "'esquema (blueprint.md)'" "$(reason "$OUT" | head -c 90)" ;; esac
case "$(reason "$OUT")" in *"funcionalidades (features.md)"*) bad "não cita etapa já fechada" "sem 'funcionalidades (features.md)'" "cobrou etapa fechada" ;;
  *) ok "blueprint ausente: a etapa já fechada não é cobrada" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa por esquema: a mensagem passa na régua (perfil hook)" \
            || bad "régua da mensagem de esquema" "sem erros de estilo" "$E"

# A9) OS 8 DOCUMENTOS FECHADOS COMO O /start-doc MANDA (status: approved + approved:)
#     -> o gate cala. É o impasse que o contrato autoral e o gate tinham: o contrato
#     grava `approved` e o gate cobrava `ready`, e nada fechava o acordo.
acc_reset
aprovado "$ACC/.claude/docs/journeys.md" Jornadas
aprovado "$ACC/.claude/docs/blueprint.md" Esquema
aprovado "$ACC/.claude/docs/features.md" Funcionalidades
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "os 8 documentos approved: passa em silêncio" || bad "8 approved passa" "vazio" "$(reason "$OUT" | head -c 90)"
acc_reset

# A10) O CRITÉRIO DE PRONTO (S-4) — TODOS os outros documentos acordados e só a LEI em
#      rascunho: o plano é negado, e a recusa nomeia a constituição. Ela é o documento
#      contra o qual os revisores medem, e em conflito com qualquer outro doc ela ganha:
#      plano medido por lei que o dono não sancionou vale o que vale o rascunho.
printf -- '---\nauthored-by: human\nstatus: draft\nscope: []\n---\n# A constituição\n' > "$ACC/.claude/docs/constituicao.md"
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "só a lei em rascunho: plano NEGADO (S-4)" \
                                  || bad "lei em rascunho nega o plano" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"constituicao.md"*) ok "lei em rascunho: a recusa nomeia o arquivo constituicao.md" ;;
  *) bad "recusa nomeia constituicao.md" "'constituicao.md'" "$(reason "$OUT" | head -c 120)" ;; esac
case "$(reason "$OUT")" in *[Cc]onstitui[çc]*) ok "lei em rascunho: a recusa chama a lei de constituição" ;;
  *) bad "recusa chama de constituição" "'constituição'" "$(reason "$OUT" | head -c 120)" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa pela lei: a mensagem passa na régua (perfil hook)" \
            || bad "régua da mensagem da lei" "sem erros de estilo" "$E"

# A11) a lei acordada devolve o silêncio — a recusa é sobre o de acordo, não sobre existir.
aprovado "$ACC/.claude/docs/constituicao.md" "A constituição"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "lei acordada: volta a passar em silêncio" || bad "lei acordada passa" "vazio" "$(reason "$OUT" | head -c 90)"

# A12) projeto SEM constituição não é barrado por ela: nenhuma skill gera esse documento,
#      então cobrá-lo de quem não o tem seria recusa sem saída.
rm -f "$ACC/.claude/docs/constituicao.md"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "sem constituicao.md: o gate não inventa a cobrança" || bad "sem lei passa" "vazio" "$(reason "$OUT" | head -c 90)"
acc_reset

echo "── Marca do texto aprovado (F2.2 / S-2) ──"

# MESMO helper que o gate usa para calcular a marca — recalcular a fórmula à mão
# aqui deixaria o teste passar com um gate que mede outra coisa.
. "$SCRIPT_DIR/lib-doc-mark.sh"

# aprovado_marcado <arquivo> <titulo> <corpo> — o de acordo COM a marca do texto,
# como o /start-doc grava. A marca é calculada antes e escrita depois: se ela fosse
# do arquivo inteiro, gravá-la já a invalidaria.
aprovado_marcado() {
  printf -- '---\nauthored-by: human\nstatus: approved\napproved: 2026-08-06\nscope: []\n---\n# %s\n%s\n' "$2" "$3" > "$1"
  M=$(doc_marca "$1")
  printf -- '---\nauthored-by: human\nstatus: approved\napproved: 2026-08-06\napproved-sig: %s\nscope: []\n---\n# %s\n%s\n' "$M" "$2" "$3" > "$1"
}

# M0) a marca é do CORPO: gravar o frontmatter não a muda, editar o texto muda.
aprovado_marcado "$ACC/.claude/docs/journeys.md" Jornadas "O usuário entra pela home."
M_ANTES=$(doc_marca "$ACC/.claude/docs/journeys.md")
[ "$M_ANTES" = "$(doc_marca_registrada "$ACC/.claude/docs/journeys.md")" ] \
  && ok "a marca gravada é a do corpo (o frontmatter não entra)" \
  || bad "marca do corpo" "$M_ANTES" "$(doc_marca_registrada "$ACC/.claude/docs/journeys.md")"

# M1) documento aprovado, marca batendo: o gate segue calado (os 7 fechados).
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "aprovado com marca íntegra: passa em silêncio" \
              || bad "aprovado com marca íntegra passa" "vazio" "$(reason "$OUT" | head -c 90)"

# M2) O CRITÉRIO DE PRONTO — editar o corpo do documento APROVADO reabre a etapa.
printf 'O usuário entra pelo painel, e não mais pela home.\n' >> "$ACC/.claude/docs/journeys.md"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "corpo editado depois do de acordo: plano NEGADO (S-2)" \
                                  || bad "editar aprovado nega o plano" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"jornadas (journeys.md)"*) ok "corpo editado: a mensagem nomeia a etapa reaberta" ;;
  *) bad "nomeia a etapa reaberta" "'jornadas (journeys.md)'" "$(reason "$OUT" | head -c 90)" ;; esac
case "$(reason "$OUT")" in *"depois do de acordo"*) ok "corpo editado: a mensagem diz que o texto mudou depois do de acordo" ;;
  *) bad "mensagem da divergência" "'depois do de acordo'" "$(reason "$OUT" | head -c 120)" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa por marca divergente: a mensagem passa na régua (perfil hook)" \
            || bad "régua da mensagem de marca" "sem erros de estilo" "$E"

# M3) reaprovar (regravar a marca sobre o texto de agora) fecha a etapa de novo.
aprovado_marcado "$ACC/.claude/docs/journeys.md" Jornadas "O usuário entra pelo painel."
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "reaprovar o texto novo fecha a etapa de novo" \
              || bad "reaprovar fecha" "vazio" "$(reason "$OUT" | head -c 90)"

# M4) as metas de qualidade também são medidas pela marca, com motivo próprio.
aprovado_marcado "$ACC/.claude/docs/quality-goals.md" Metas "Escaneabilidade antes de completude."
printf 'Completude antes de escaneabilidade.\n' >> "$ACC/.claude/docs/quality-goals.md"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "quality-goals.md editado depois do de acordo: negado" \
                                  || bad "quality-goals editado negado" deny "$(decision "$OUT")"
case "$(reason "$OUT")" in *"depois do de acordo"*) ok "quality-goals.md editado: a mensagem dá o motivo certo" ;;
  *) bad "motivo do quality-goals editado" "'depois do de acordo'" "$(reason "$OUT" | head -c 120)" ;; esac
E=$(estilo_hook "$(reason "$OUT")")
[ -z "$E" ] && ok "recusa por marca em quality-goals: passa na régua (perfil hook)" \
            || bad "régua da mensagem de marca em quality-goals" "sem erros de estilo" "$E"

# M5) RETROCOMPAT — documento aprovado ANTES de a marca existir (sem approved-sig)
#     continua fechado. Cobrar marca de quem nunca a gravou barraria todo projeto
#     já acordado, o oposto do que o gate existe pra fazer.
aprovado "$ACC/.claude/docs/quality-goals.md" Metas
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "aprovado sem approved-sig: continua fechado (retrocompat)" \
              || bad "retrocompat sem marca" "vazio" "$(reason "$OUT" | head -c 90)"

# M6) FAIL-OPEN de infra: helper da marca ausente não pode reabrir etapa nenhuma.
#     (o gate roda de uma cópia sem o lib-doc-mark.sh)
NOMARK="$TMP/hooks-sem-marca"
mkdir -p "$NOMARK" && cp "$SCRIPT_DIR"/*.sh "$NOMARK/" 2>/dev/null
mkdir -p "$TMP/hooks-sem-marca-lib" && cp -r "$SCRIPT_DIR/../lib" "$TMP/hooks-sem-marca-lib/lib" 2>/dev/null
rm -f "$NOMARK/lib-doc-mark.sh"
aprovado_marcado "$ACC/.claude/docs/journeys.md" Jornadas "O usuário entra pelo painel."
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(printf '{"tool_name":"EnterPlanMode","session_id":"%s","cwd":"%s"}' "$SESSION" "$ACC" | bash "$NOMARK/pretooluse-plan-gate.sh" 2>/dev/null)
[ -z "$OUT" ] && ok "sem lib-doc-mark.sh: fail-open (não reabre etapa às cegas)" \
              || bad "fail-open sem o helper da marca" "vazio" "$(printf '%s' "$OUT" | head -c 90)"
acc_reset

echo "── Correção pendente em etapa acordada (F3.2) ──"

# A correção mora no FRONTMATTER: o corpo é o texto aprovado, e mexer nele reabriria a
# etapa pela marca (S-2). Inserir depois da 1ª linha (`---`) deixa o corpo intacto.
mensagem() { printf '%s' "$1" | jq -r '.systemMessage // ""' 2>/dev/null; }
corrigir() { # corrigir <arquivo> <texto>
  awk -v t="$2" 'NR==1 { print; print "correcao-pendente: " t; next } { print }' "$1" > "$1.tmp" \
    && mv "$1.tmp" "$1"
}

# C0) baseline: as etapas fechadas, sem correção nenhuma -> o gate cala.
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ -z "$OUT" ] && ok "sem correção pendente: segue passando em silêncio" \
              || bad "baseline da correção" "vazio" "$(printf '%s' "$OUT" | head -c 90)"

# C1) O CRITÉRIO DE PRONTO — correção registrada num documento aprovado NÃO congela o
#     planejamento (antes, registrá-la no corpo derrubava a aprovação inteira).
corrigir "$ACC/.claude/docs/journeys.md" "o painel virou a porta de entrada"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" != "deny" ] && ok "correção pendente: o plano NÃO é barrado (F3.2)" \
                                   || bad "correção não barra" "allow" "$(reason "$OUT" | head -c 90)"

# C2) e ela APARECE NA CONTAGEM, nomeando o documento.
M=$(mensagem "$OUT")
case "$M" in *"1 correção pendente"*) ok "correção pendente: sai na contagem (1)" ;;
  *) bad "contagem da correção" "'1 correção pendente'" "$(printf '%s' "$M" | head -c 90)" ;; esac
case "$M" in *"journeys.md"*) ok "correção pendente: a contagem nomeia o documento" ;;
  *) bad "contagem nomeia o documento" "journeys.md" "$(printf '%s' "$M" | head -c 90)" ;; esac

# C3) a régua vale também para o aviso que não barra
E=$(estilo_hook "$M")
[ -z "$E" ] && ok "aviso de correção pendente: passa na régua (perfil hook)" \
            || bad "régua do aviso de correção" "sem erros de estilo" "$E"

# C3b) a correção é escrita com o vocabulário de lacuna da skill (`[PENDENTE]`), e no
#      FRONTMATTER isso não pode derrubar a aprovação — o marcador só reabre no corpo.
corrigir "$ACC/.claude/docs/architecture-intent.md" "[PENDENTE] confirmar o limite do motor"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" != "deny" ] && ok "correção com [PENDENTE] no frontmatter: não reabre a etapa" \
                                   || bad "[PENDENTE] no frontmatter não reabre" "allow" "$(reason "$OUT" | head -c 90)"

# C4) correções em documentos diferentes somam na contagem
corrigir "$ACC/.claude/docs/quality-goals.md" "falta o exemplo de trade-off"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
M=$(mensagem "$(gate EnterPlanMode "$ACC")")
case "$M" in *"3 correções pendentes"*) ok "três correções: a contagem soma os documentos" ;;
  *) bad "soma da contagem" "'3 correções pendentes'" "$(printf '%s' "$M" | head -c 90)" ;; esac

# C5) `[PENDENTE]` no CORPO continua reabrindo a etapa — correção pendente é a do
#     frontmatter, e lacuna de texto não escrito não pode virar uma delas por engano.
#     (quality-goals.md aqui não tem approved-sig, então quem nega só pode ser o corpo)
printf '[PENDENTE]\n' >> "$ACC/.claude/docs/quality-goals.md"
acc_reset
: > "$TMPD/claude-doc-guard-${SESSION}-$(phash "$ACC")"
OUT=$(gate EnterPlanMode "$ACC")
[ "$(decision "$OUT")" = "deny" ] && ok "[PENDENTE] no corpo do aprovado: ainda nega" \
                                  || bad "[PENDENTE] no corpo nega" deny "$(decision "$OUT")"
acc_reset

echo "── Doc defasada: a rodada é medida, não perguntada (S-144) ──"
# Fixture stale: mesmo projeto do CASO B, com x.py commitado e depois mexido, e a
# doc carimbada com data velha. O gate ainda não viu Read nenhum → nudge de leitura,
# que é onde vive o aviso de defasagem.
STL="$TMP/projeto-stale"
cp -a "$DOCD" "$STL"; rm -rf "$STL/.git"
(cd "$STL" && git init -q . && git config user.email t@e.dev && git config user.name T)
printf 'x = 1\n' > "$STL/x.py"
(cd "$STL" && git add -A >/dev/null 2>&1 && git commit -q -m x)
stale_msg() { # <data-do-generated> → systemMessage/reason do gate
  printf -- '---\ngenerated: %s\nscope:\n  - x.py\ndoc-sig: a/b@gen=3.8#deadbeef\n---\n# Arch\n' "$1" > "$STL/.claude/docs/architecture.md"
  rm -f "$TMPD"/claude-plan-gate-count-"$SESSION"-"$(phash "$STL")"
  gate EnterPlanMode "$STL" | jq -r '.hookSpecificOutput.permissionDecisionReason // empty' 2>/dev/null
}
M=$(stale_msg 2026-01-01)
printf '%s' "$M" | grep -q 'DEFASADA' && ok "doc velha: o gate acusa a defasagem" \
                                      || bad "gate acusa defasagem" DEFASADA "$M"
printf '%s' "$M" | grep -q '/project-skills:doc ' && ok "doc velha: manda a rodada COMPLETA, com o plugin descoberto" \
                                          || bad "rodada completa" /project-skills:doc "$M"
printf '%s' "$M" | grep -qE 'tem [0-9]+ dias' && ok "doc velha: mostra o número que sustentou a escolha" \
                                              || bad "número medido" "tem N dias" "$M"
# A rodada é a skill, e a skill não existe no plugin que a suíte está testando:
# nome escrito à mão (`/project-doc`) é pedido de skill inexistente.
printf '%s' "$M" | grep -q '/project-doc' && bad "não escreve o nome morto" "sem /project-doc" "$M" \
                                          || ok "doc velha: não escreve o nome de skill que não existe"
# Sem resolvedor na máquina, o aviso ainda NOMEIA a rodada — só sem o prefixo.
M=$(CLAUDE_CONFIG_DIR="$TMP/vazio" stale_msg 2026-01-01)
printf '%s' "$M" | grep -qE '/doc ANTES de planejar' && ok "sem resolvedor: cai no nome cru da skill" \
                                                    || bad "fail-open do resolvedor" "/doc ANTES" "$M"
M=$(stale_msg "$(date +%Y-%m-%d)")
printf '%s' "$M" | grep -q '/project-skills:doc-touch' && ok "doc de hoje: manda a rodada CURTA, com o plugin descoberto" \
                                        || bad "rodada curta" /project-skills:doc-touch "$M"
printf '%s' "$M" | grep -qE 'tem [0-9]+ dias' && ok "doc de hoje: mostra o número que sustentou a escolha" \
                                              || bad "número medido" "tem N dias" "$M"

# O aviso de defasagem é texto de canal de terminal: a régua do Artigo 6 o cobra.
M=$(stale_msg 2026-01-01)
AVISO=$(printf '%s' "$M" | sed -n '/A DOC ESTÁ DEFASADA/,$p')
REGUA_TXT=$(printf '%s\n' "$AVISO" | python3 "$SCRIPT_DIR/../lib/regua_texto.py" --perfil hook --onde aviso - 2>&1)
[ -z "$REGUA_TXT" ] && ok "o aviso de defasagem passa na régua do perfil hook" \
                    || bad "aviso na régua" "sem motivo" "$REGUA_TXT"

echo
printf '%s\n' "── $PASS passou · $FAIL falhou ──"
[ "$FAIL" -eq 0 ]
