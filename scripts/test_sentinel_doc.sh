#!/bin/bash
# test_sentinel_doc.sh — RED→GREEN do furo B (sentinel por-doc no monorepo).
# Trava: ler a doc do app A NÃO destrava busca cega no app B.
# Red hoje: o sentinel é por-projeto — ler A libera busca em B.
# Estrutura do monorepo real: docs em $PROJ/.claude/docs/apps/{app}.md.  # casa-ok: fixture de teste, o literal e o dado do caso
H="plugins/project-skills/hooks/pretooluse-doc-guard.sh"
R="plugins/project-skills/hooks/posttooluse-doc-read.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.claude/docs/apps" "$TMP/apps/a" "$TMP/apps/b"  # casa-ok: fixture de teste, o literal e o dado do caso
printf '# proj\n' > "$TMP/CLAUDE.md"
printf '# a\n' > "$TMP/.claude/docs/apps/a.md"  # casa-ok: fixture de teste, o literal e o dado do caso
printf '# b\n' > "$TMP/.claude/docs/apps/b.md"  # casa-ok: fixture de teste, o literal e o dado do caso
printf '# index\n' > "$TMP/.claude/docs/index.md"  # casa-ok: fixture de teste, o literal e o dado do caso
S="sent-$$"

# 1) lê a doc do app A (grava sentinel do projeto + por-doc de A)
printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s/.claude/docs/apps/a.md"}}' "$S" "$TMP" "$TMP" | bash "$R" >/dev/null 2>&1  # casa-ok: fixture de teste, o literal e o dado do caso

# 2) busca cega em apps/B → DEVE negar (o sentinel de B não foi gravado)
OUT=$(printf '{"tool_name":"Grep","session_id":"%s","cwd":"%s","tool_input":{"path":"%s/apps/b"}}' \
  "$S" "$TMP" "$TMP" | bash "$H")
if echo "$OUT" | grep -qE 'permissionDecision"[[:space:]]*:[[:space:]]*"deny'; then
  echo "ok   busca em B negada (sentinel por-doc)"
else
  echo "FAIL busca em B passou — furo B aberto"; exit 1
fi

# 2b) busca cega NA RAÍZ do monorepo (grep -r foo .) → DEVE negar: varre todos
#     os apps, e ler a doc do app A não destrava a raiz (furo B parcial R5)
OUT=$(printf '{"tool_name":"Bash","session_id":"%s","cwd":"%s","tool_input":{"command":"grep -r foo ."}}' \
  "$S" "$TMP" | bash "$H")
if echo "$OUT" | grep -qE 'permissionDecision"[[:space:]]*:[[:space:]]*"deny'; then
  echo "ok   busca na raiz negada (exige índice)"
else
  echo "FAIL busca na raiz passou — furo B parcial aberto"; exit 1
fi

# 2c) lê o índice da raiz → busca na raiz libera (sentinel por-doc do índice)
printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s/.claude/docs/index.md"}}' "$S" "$TMP" "$TMP" | bash "$R" >/dev/null 2>&1  # casa-ok: fixture de teste, o literal e o dado do caso
OUT=$(printf '{"tool_name":"Bash","session_id":"%s","cwd":"%s","tool_input":{"command":"grep -r foo ."}}' \
  "$S" "$TMP" | bash "$H")
if echo "$OUT" | grep -qE 'permissionDecision"[[:space:]]*:[[:space:]]*"deny'; then
  echo "FAIL busca na raiz negada mesmo após ler o índice"; exit 1
else
  echo "ok   busca na raiz liberada após ler o índice"
fi

# 3) busca em apps/A → deve passar (sentinel de A existe)
OUT=$(printf '{"tool_name":"Grep","session_id":"%s","cwd":"%s","tool_input":{"path":"%s/apps/a"}}' \
  "$S" "$TMP" "$TMP" | bash "$H")
if echo "$OUT" | grep -qE 'permissionDecision"[[:space:]]*:[[:space:]]*"deny'; then
  echo "FAIL busca em A negada (deveria passar)"; exit 1
else
  echo "ok   busca em A liberada"
fi
