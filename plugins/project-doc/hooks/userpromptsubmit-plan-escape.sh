#!/bin/bash
# userpromptsubmit-plan-escape.sh — o escape VERBAL do gate de plano.
#
# O pretooluse-plan-gate.sh nega SEMPRE quando o projeto não tem documentação.
# A decisão de projeto (2026-07-26) foi: nega sempre, a não ser que o usuário
# verbalize que é para ignorar. Hook não lê a conversa — então quem ouve a
# frase é este, no UserPromptSubmit, e ele grava um sentinel que o gate honra.
#
# Escopo: por SESSÃO x PROJETO (arquivo em /tmp chaveado por session_id — arquivo
# global vazaria entre sessões concorrentes; ver o bug do context-guard).
# Vale pelo resto da sessão: o usuário verbaliza uma vez, não a cada plano.
#
# Fail-open: qualquer erro -> exit 0, sem sentinel (o gate segue negando, que é
# o lado seguro: na dúvida a documentação continua obrigatória).
#
# Frases aceitas (case-insensitive). Deliberadamente IMPERATIVAS.
#   ignora/pula/dispensa/esquece a doc · planeja/faz o plano/segue sem (a) doc
#   --sem-doc  ·  #sem-doc      (token explícito e GARANTIDO — citado no deny do gate)
# Revogar: --com-doc  ·  "exige a doc"  (apaga o sentinel e o gate volta a valer)
#
# TRÊS ARMADILHAS QUE A REVISÃO PEGOU (2026-07-26) — não afrouxe sem reproduzir:
#   1. SEM fronteira de palavra, "esta+va sem documentação" e "con+segue sem doc"
#      liberavam o gate. São CONSTATAÇÕES, não ordens. Daí o `(^|[^[:alnum:]])`
#      obrigatório antes de todo verbo.
#   2. "ignora a doc DO React" / "pula a documentação DA lib" — frases banais em
#      qualquer sessão de código — liberavam o gate do PROJETO. Daí o EXTERNAL_RE:
#      doc seguida de "do/da/de <coisa>" é doc de TERCEIRO, não a nossa.
#   3. Ambiguidade resolve pro lado SEGURO: casou os dois ⇒ NÃO libera. Quem quer
#      liberar mesmo assim usa `--sem-doc`, que é inequívoco por construção.

command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null)
PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
SESSION=$(printf '%s' "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$PROMPT" ] && exit 0
[ -z "$CWD" ] && CWD="$PWD"

B='(^|[^[:alnum:]])'                                   # fronteira de palavra à esquerda
DOC='(doc|docs|documenta[çc][ãa]o|documentacao)([^[:alnum:]]|$)'
ART='(a|o|as|os|essa|esse|esta|este|minha|nossa)[[:space:]]+'

# imperativo + doc     |  verbo de andamento + "sem" + doc      |  token explícito
ESCAPE_RE="${B}(ignor(a|ar|e)|pul(a|ar|e)|dispens(a|ar|e)|desconsider(a|ar|e)|esquec(e|er|a)|deixa)[[:space:]]+(${ART})?${DOC}|${B}(planej(a|ar|e)|faz(er)?[[:space:]]+o[[:space:]]+plano|seg(ue|uir)|vai|toca|manda)[[:space:]]+sem[[:space:]]+(${ART})?${DOC}|(--sem-doc)|(#sem-doc)"

# doc de TERCEIRO ("a doc do React") — nunca é ordem sobre a doc DESTE projeto.
EXTERNAL_RE="(doc|docs|documenta[çc][ãa]o|documentacao)[[:space:]]+(do|da|dos|das|de)[[:space:]]+[[:alnum:]]"

# REVOGAÇÃO — a válvula pra um falso-positivo que sobrou. Sem ela, uma frase mal
# interpretada desligaria o gate pelo resto da sessão sem volta.
REVOKE_RE="(--com-doc)|${B}(exig(e|ir)|volta[[:space:]]+a[[:space:]]+exigir|restaura)[[:space:]]+(${ART})?${DOC}"

if printf '%s' "$PROMPT" | grep -qiE "$REVOKE_RE"; then
  REVOKING=1
else
  REVOKING=0
  printf '%s' "$PROMPT" | grep -qiE "$ESCAPE_RE" || exit 0
  # Ambíguo (fala de doc de terceiro E casa o escape) ⇒ lado seguro: não libera.
  if printf '%s' "$PROMPT" | grep -qiE "$EXTERNAL_RE"; then
    printf '%s' "$PROMPT" | grep -qiE '(--sem-doc)|(#sem-doc)' || exit 0
  fi
fi

# Mesma resolução de raiz do gate — o sentinel TEM que casar a chave, por isso
# os dois usam o mesmo helper em vez de cada um reimplementar a subida.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/lib-project-root.sh" 2>/dev/null || exit 0
PROJ=$(project_root "$CWD") || exit 0
[ -z "$PROJ" ] && exit 0

PHASH=$(project_hash "$PROJ")
ESCAPE="/tmp/claude-plan-gate-escape-${SESSION}-${PHASH}"

if [ "$REVOKING" = "1" ]; then
  [ -f "$ESCAPE" ] || exit 0            # não estava liberado — nada a revogar, cala
  rm -f "$ESCAPE" 2>/dev/null
  CTX="🔒 Escape do gate de documentação REVOGADO para ${PROJ}. O gate volta a exigir documentação antes de qualquer plano."
  jq -n --arg ctx "$CTX" \
    '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$ctx}}'
  exit 0
fi

# Já estava liberado — não repete o aviso (senão polui todo prompt seguinte).
[ -f "$ESCAPE" ] && exit 0

printf '%s\n' "$PROJ" > "$ESCAPE" 2>/dev/null || exit 0

CTX="🔓 Escape do gate de documentação ATIVADO para ${PROJ} nesta sessão — o usuário autorizou explicitamente planejar sem documentação. O gate de plano não vai mais barrar aqui. Ainda assim: registre no plano que ele foi feito SEM doc de referência, e ofereça \`/start-doc\` ao final. Se isto foi engano, o usuário revoga com \`--com-doc\`."

jq -n --arg ctx "$CTX" \
  '{hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:$ctx}}'
exit 0
