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

# ── A casa da doc em docs/ na raiz: é o que a mensagem de bloqueio manda ler.
# Medido em 2026-11-05: ler docs/kommo-sync.md não liberava, e a busca seguia negada.  # casa-ok: fixture de teste, o literal e o dado do caso
le() { printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s"}}' "$S" "$1" "$2" | bash "$R" 2>/dev/null; }
negada() {
  printf '{"tool_name":"Grep","session_id":"%s","cwd":"%s","tool_input":{"path":"%s"}}' "$S" "$1" "$1" | bash "$H" \
    | grep -qE 'permissionDecision"[[:space:]]*:[[:space:]]*"deny'
}
novo_projeto() {
  local p; p=$(mktemp -d "$TMP/proj.XXXXXX")
  mkdir -p "$p/docs/sub" "$p/src/docs"
  printf '# proj\n' > "$p/CLAUDE.md"
  printf '# a\n' > "$p/docs/a.md"
  printf '# n\n' > "$p/docs/sub/n.md"
  printf '# x\n' > "$p/src/docs/x.md"
  printf '%s' "$p"
}

# 4) lê um arquivo de docs/ → busca libera; antes de ler, nega
P=$(novo_projeto)
negada "$P" && echo "ok   sem leitura, busca negada" || { echo "FAIL busca passou sem ler a doc"; exit 1; }
SAIDA=$(le "$P" "$P/docs/a.md")
negada "$P" && { echo "FAIL ler docs/a.md não liberou a busca"; exit 1; } || echo "ok   ler docs/a.md libera a busca"  # casa-ok: fixture de teste, o literal e o dado do caso

# 5) o aviso de doc defasada/indeterminada também vale para quem lê em docs/
case "$SAIDA" in
  *DEFASADA*|*INDETERMINADO*) echo "ok   aviso de staleness sai na leitura de docs/" ;;
  *) echo "FAIL leitura de docs/ não avisou staleness"; exit 1 ;;
esac

# 6) subpasta da casa também libera
P=$(novo_projeto); le "$P" "$P/docs/sub/n.md" >/dev/null
negada "$P" && { echo "FAIL ler docs/sub/n.md não liberou"; exit 1; } || echo "ok   subpasta de docs/ libera"  # casa-ok: fixture de teste, o literal e o dado do caso

# 7) pasta docs/ que NÃO é a casa não libera (src/docs/ de outro uso)
P=$(novo_projeto); le "$P" "$P/src/docs/x.md" >/dev/null
negada "$P" && echo "ok   src/docs/x.md não libera" || { echo "FAIL src/docs/ liberou a busca"; exit 1; }

# 8) casa na .claude/docs com prosa solta em docs/: ler a prosa não libera, ler a casa libera  # casa-ok: fixture de teste, o literal e o dado do caso
P=$(novo_projeto); mkdir -p "$P/.claude/docs"  # casa-ok: fixture de teste, o literal e o dado do caso
printf -- '---\nproject: p\n---\n# f\n' > "$P/.claude/docs/f.md"  # casa-ok: fixture de teste, o literal e o dado do caso
le "$P" "$P/docs/a.md" >/dev/null
negada "$P" && echo "ok   prosa em docs/ não libera quando a casa é outra" || { echo "FAIL prosa fora da casa liberou"; exit 1; }
le "$P" "$P/.claude/docs/f.md" >/dev/null  # casa-ok: fixture de teste, o literal e o dado do caso
negada "$P" && { echo "FAIL ler a casa velha não liberou"; exit 1; } || echo "ok   casa velha segue liberando"
