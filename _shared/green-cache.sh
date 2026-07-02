#!/usr/bin/env bash
# green-cache.sh — registro compartilhado de "suite de testes passou verde neste
# estado exato da árvore". FONTE-DA-VERDADE em _shared/; cópias vendoradas via
# scripts/sync-shared.sh (ship/hooks e qa-loop/lib). Feito pra ser SOURCED.
#
# Consumidores: Fase Gate do qa-loop (grava), ship §2.5 (consulta+grava),
# hook pre-deploy-test-check.sh do ship (consulta+grava).
#
# Semântica (não-negociável):
#   - Fail-open na direção SEGURA: qualquer erro → MISS → a suite roda.
#   - Gate vermelho NUNCA grava.
#   - Chave = tree-hash do git incluindo untracked (index temporário) —
#     qualquer edição, arquivo novo ou remoção muda a chave e invalida o hit.
#   - TTL 24h POR LINHA (epoch gravado no registro, não mtime do arquivo —
#     um mark novo no mesmo arquivo não pode ressuscitar registro vencido):
#     deps/.env vivem fora da árvore, o TTL limita essa exposição. Prune de
#     arquivos >7d no mark.
#
# Estado em ~/.claude/green-suite/ (NUNCA dentro do plugin — o cache
# ${CLAUDE_PLUGIN_ROOT} é reescrito a cada bump de versão).
#
# API:
#   green_tree_hash  <root>                  # imprime o sha; exit 1 em erro
#   green_cache_check <root> [scope]         # exit 0 = HIT (scope ou 'full')
#   green_cache_mark  <root> <scope> <writer># TSV: scope\tepoch\tiso-ts\twriter
# scope: "full" ou "app:<nome>". "full" satisfaz qualquer consulta.

GREEN_SUITE_DIR="${GREEN_SUITE_DIR:-$HOME/.claude/green-suite}"
GREEN_SUITE_TTL_SECS="${GREEN_SUITE_TTL_SECS:-86400}"

# Hash determinístico da árvore INTEIRA (tracked + untracked, respeitando
# .gitignore), sem tocar o index real nem o working tree. `git stash create`
# e `HEAD + diff` não servem: ignoram untracked → falso HIT.
green_tree_hash() {
  local root tmp_idx hash
  root=$(git -C "${1:-.}" rev-parse --show-toplevel 2>/dev/null) || return 1
  tmp_idx=$(mktemp "${TMPDIR:-/tmp}/green-idx.XXXXXX") || return 1
  hash=$(
    export GIT_INDEX_FILE="$tmp_idx"
    git -C "$root" read-tree HEAD 2>/dev/null   # repo sem commit → index vazio, segue
    git -C "$root" add -A -- . >/dev/null 2>&1 || exit 1
    git -C "$root" write-tree 2>/dev/null
  ) || { rm -f "$tmp_idx"; return 1; }
  rm -f "$tmp_idx"
  [ -n "$hash" ] && printf '%s\n' "$hash"
}

# Nome do arquivo de registro pra (projeto × estado da árvore).
_green_cache_file() {
  local root="$1" phash thash
  root=$(git -C "$root" rev-parse --show-toplevel 2>/dev/null) || return 1
  phash=$(printf '%s' "$root" | cksum | cut -d' ' -f1) || return 1
  thash=$(green_tree_hash "$root") || return 1
  printf '%s/%s-%s\n' "$GREEN_SUITE_DIR" "$phash" "$thash"
}

# exit 0 = HIT: existe registro do scope (ou 'full') pra este exato estado da
# árvore, com menos de TTL (idade da LINHA). Qualquer erro → exit 1 (MISS).
green_cache_check() {
  local root="${1:-.}" scope="${2:-full}" f now
  f=$(_green_cache_file "$root") || return 1
  [ -f "$f" ] || return 1
  now=$(date +%s)
  awk -F'\t' -v now="$now" -v ttl="$GREEN_SUITE_TTL_SECS" -v scope="$scope" '
    ($1 == "full" || $1 == scope) && ($2 + 0) > 0 && (now - $2) < ttl { hit = 1 }
    END { exit hit ? 0 : 1 }' "$f" 2>/dev/null
}

# Grava "scope passou verde" pro estado atual da árvore. Chamar SÓ com a suite
# 100% verde — vermelho nunca grava. writer identifica quem gravou no relatório.
green_cache_mark() {
  local root="${1:-.}" scope="${2:-full}" writer="${3:-unknown}" f ts
  f=$(_green_cache_file "$root") || return 1
  mkdir -p "$GREEN_SUITE_DIR" 2>/dev/null || return 1
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  printf '%s\t%s\t%s\t%s\n' "$scope" "$(date +%s)" "$ts" "$writer" >> "$f" || return 1
  find "$GREEN_SUITE_DIR" -type f -mtime +7 -delete 2>/dev/null || true
  return 0
}
