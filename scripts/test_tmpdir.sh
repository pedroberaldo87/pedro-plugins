#!/bin/bash
# test_tmpdir.sh — RED→GREEN do temporário (W-3).
# Trava: hook que grava sentinel tem que honrar TMPDIR. Numa máquina onde /tmp
# não existe, não é gravável, ou é compartilhado entre contas, o caminho fixo
# "/tmp/..." escrito no hook grava no lugar errado (ou não grava).
# Red hoje: doc-guard e context-guard escrevem "/tmp/..." literal — o sentinel
# nasce em /tmp mesmo com TMPDIR apontando para outro lugar.
#
# Rode da raiz do repositório: bash scripts/test_tmpdir.sh
command -v jq >/dev/null 2>&1 || { echo "skip jq ausente"; exit 0; }

DOC_READ="plugins/project-doc/hooks/posttooluse-doc-read.sh"
CG_WRITER="plugins/context-guard/hooks/context-guard-writer.sh"
CG_GUARD="plugins/context-guard/hooks/context-guard.sh"
for f in "$DOC_READ" "$CG_WRITER" "$CG_GUARD"; do
  [ -f "$f" ] || { echo "skip $f não encontrado (rode da raiz do repo)"; exit 0; }
done

# TMPDIR próprio + projeto de mentira, ambos descartáveis.
TMPDIR_TEST=$(mktemp -d)
PROJ=$(mktemp -d)
trap 'rm -rf "$TMPDIR_TEST" "$PROJ"' EXIT
mkdir -p "$PROJ/.claude/docs"
printf '# proj\n' > "$PROJ/CLAUDE.md"
printf '# arch\n' > "$PROJ/.claude/docs/architecture.md"

S="tmpdirtest-$$"
export TMPDIR="$TMPDIR_TEST"
FAIL=0

# /tmp é symlink no macOS (aponta para /private/tmp) e o find não atravessa
# symlink dado como argumento — sem resolver, o lado "não vazou" fica verde
# sozinho e o teste não prova nada.
SLASH_TMP=$(cd /tmp 2>/dev/null && pwd -P) || SLASH_TMP=/tmp

# Um caso = um sentinel: roda o hook, exige o arquivo sob TMPDIR e a AUSÊNCIA
# do mesmo arquivo em /tmp. Os dois lados importam — gravar nos dois lugares
# continua sendo vazamento para /tmp.
verifica() {
  nome="$1"; padrao="$2"
  achou_tmpdir=$(find "$TMPDIR_TEST" -maxdepth 1 -name "$padrao" 2>/dev/null | head -1)
  achou_slash_tmp=$(find "$SLASH_TMP" -maxdepth 1 -name "$padrao" 2>/dev/null | head -1)
  if [ -z "$achou_tmpdir" ]; then
    echo "FAIL $nome — nada sob TMPDIR ($padrao)"; FAIL=1
  else
    echo "ok   $nome — sentinel sob TMPDIR"
  fi
  if [ -n "$achou_slash_tmp" ]; then
    echo "FAIL $nome — vazou para /tmp: $achou_slash_tmp"
    # Some o que vazou (todos, não só o primeiro): o teste não pode ir deixando
    # sentinel de sessão fantasma em /tmp a cada rodada.
    find "$SLASH_TMP" -maxdepth 1 -name "$padrao" -exec rm -f {} + 2>/dev/null
    FAIL=1
  else
    echo "ok   $nome — nada em /tmp"
  fi
}

# 1) doc-guard: ler a doc grava o sentinel que libera a busca cega.
printf '{"tool_name":"Read","session_id":"%s","cwd":"%s","tool_input":{"file_path":"%s/.claude/docs/architecture.md"}}' \
  "$S" "$PROJ" "$PROJ" | bash "$DOC_READ" >/dev/null 2>&1
verifica "doc-guard (sentinel de doc lida)" "claude-doc-guard-${S}*"

# 2) context-guard writer: o statusLine grava o context% da sessão.
printf '{"session_id":"%s","context_window":{"used_percentage":91}}' "$S" \
  | bash "$CG_WRITER" >/dev/null 2>&1
verifica "context-guard (estado de context%)" "claude-context-pct-${S}"

# 3) context-guard gate: grava o sentinel de "já avisei nesta sessão".
printf '{"session_id":"%s","tool_name":"Skill","tool_input":{"skill":"handoff"}}' "$S" \
  | bash "$CG_GUARD" >/dev/null 2>&1
verifica "context-guard (sentinel de aviso)" "claude-context-warned-${S}"

# Limpa o que sobrou sob o TMPDIR de teste é responsabilidade do trap.
[ "$FAIL" = "0" ] && echo "VERDE — TMPDIR honrado pelos hooks" || echo "VERMELHO — hooks ignoram TMPDIR"
exit "$FAIL"
