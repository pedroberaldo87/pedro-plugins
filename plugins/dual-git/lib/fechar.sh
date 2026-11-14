#!/usr/bin/env bash
# fechar.sh — grava e envia o que mudou em `.claude/`. Chamado por `devgit fechar "<mensagem>"`
# com a raiz do projeto como primeiro argumento.
#
# É o fechamento que as skills (documentação, registro de sessão, publicação) rodam no
# fim: um comando só, em vez da receita `add` + `commit` + `push` copiada em prosa em
# cada uma.
#
# Só `.claude/` entra. No repositório único o git é o do projeto inteiro, e um `add -A`
# solto levaria o código junto; por isso o `add` e o `commit` vão com o caminho `.`
# (relativo a `.claude/`), e o que outra pessoa deixou preparado fora dela fica como estava.
#
# Sai com 0 quando o privado ficou sem mudança e sem commit por enviar (inclusive quando
# não havia nada a fazer), 1 quando sobrou algo (sem remoto, push recusado), 2 quando não
# consegue nem começar (mensagem ausente).
set -u
r="$1"; shift
msg="${1:-}"
[ -n "$msg" ] || { echo "devgit fechar: falta a mensagem do commit — devgit fechar \"docs: …\"" >&2; exit 2; }
if [ "${DUALGIT_UNICO:-0}" = 1 ]; then
  g() { git -C "$r/.claude" -c core.quotePath=false "$@"; }
else
  g() { git --git-dir="$r/.git/dev.git" --work-tree="$r/.claude" -C "$r/.claude" -c core.quotePath=false "$@"; }
fi

g add -A -- . || exit 1
if ! g diff --cached --quiet -- .; then
  g commit -q -m "$msg" -- . || { echo "devgit fechar: o commit falhou" >&2; exit 1; }
  echo "devgit fechar: commit $(g rev-parse --short HEAD) — $msg"
fi

if ! g rev-parse -q --verify '@{u}' >/dev/null 2>&1; then
  if [ -z "$(g remote)" ]; then
    echo "devgit fechar: sem remoto — o commit ficou só neste disco (devgit remote add origin <url> && devgit push -u origin main)" >&2
    exit 1
  fi
  g push -q -u origin HEAD || { echo "devgit fechar: o push foi recusado" >&2; exit 1; }
else
  [ "$(g rev-list --count '@{u}..HEAD')" -eq 0 ] || g push -q || { echo "devgit fechar: o push foi recusado" >&2; exit 1; }
fi
echo "devgit fechar: privado em dia ($(g rev-list --count '@{u}..HEAD') commit(s) por enviar, $(g status --porcelain -- . | wc -l | tr -d ' ') arquivo(s) sem commit)"
