#!/bin/bash
# Pre-ExitPlanMode hook: blocks plan presentation in the CLI until an HTML
# visual exists for the CURRENT SESSION's plan.
#
# Key design: scoped by session_id. Does NOT search plan files by mtime
# (which would match plans from other sessions). The plan content comes
# directly from tool_input.plan in the hook input, so there's no file
# discovery step at all.
#
# Input (stdin, JSON): session_id, cwd, transcript_path, tool_name,
# tool_input{plan}, hook_event_name.

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | /opt/homebrew/bin/jq -r '.session_id // empty')
PLAN_CONTENT=$(echo "$INPUT" | /opt/homebrew/bin/jq -r '.tool_input.plan // empty')

# Fallbacks — if session_id is missing (shouldn't happen), let it pass
if [ -z "$SESSION_ID" ]; then
  exit 0
fi

SESSION_SHORT="${SESSION_ID:0:8}"
VISUAL_DIR="$HOME/Desktop/claude-visual"
mkdir -p "$VISUAL_DIR"

# Is there a visual tagged with this session, modified in last 5 min?
RECENT_VISUAL=$(find "$VISUAL_DIR" -maxdepth 1 -name "*sess-${SESSION_SHORT}*.html" -mmin -5 2>/dev/null | head -1)

if [ -n "$RECENT_VISUAL" ]; then
  open "$RECENT_VISUAL" 2>/dev/null || true
  cat >&2 << FEEDBACK
📊 Visual HTML da sessão atual já existe: $RECENT_VISUAL
Aberto no browser. Prossiga com a apresentação do plano.
FEEDBACK
  exit 0
fi

# No visual for this session — block and instruct Claude
TODAY=$(date +%Y-%m-%d)
SUGGESTED_FILENAME="${TODAY}-sess-${SESSION_SHORT}-plan.html"
SUGGESTED_PATH="$VISUAL_DIR/${SUGGESTED_FILENAME}"

cat >&2 << FEEDBACK
📊 VISUAL GATE — plano desta sessão precisa virar HTML antes de ir pro CLI.

Session ID: $SESSION_ID (prefix: $SESSION_SHORT)

CONTEÚDO DO PLANO (fonte de verdade — use ESTE conteúdo literal, NÃO leia arquivos .md de outras sessões):

--- BEGIN PLAN ---
$PLAN_CONTENT
--- END PLAN ---

Passos obrigatórios ANTES de chamar ExitPlanMode de novo:

1. Invoque a skill 'visual' (Skill tool com name='visual')
2. Use o conteúdo do plano acima como input (não busque em ~/.claude/plans/)
3. Renderize usando o template da skill 'visual' (Skill tool resolve o path)
4. Salve em: $SUGGESTED_PATH
   (o filename DEVE conter "sess-${SESSION_SHORT}" — o hook reconhece por isso)
5. Abra com: open "$SUGGESTED_PATH"
6. SÓ DEPOIS chame ExitPlanMode de novo.

Regras não-negociáveis:
- NÃO apresente o plano ao Pedro no CLI ainda.
- NÃO resuma o plano em texto na resposta.
- NÃO use o conteúdo de qualquer .md encontrado — use APENAS o PLAN entre os marcadores acima.
FEEDBACK
exit 2
