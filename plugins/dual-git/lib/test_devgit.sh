#!/usr/bin/env bash
# Suíte do dual-git — bash puro, sem framework (padrão do repo).
#
# Cada bloco reproduz numa pasta temporária, com git real, uma das falhas que o
# modelo existe para impedir: `.git` dentro de `.claude/` (a raiz do projeto some
# para quem procura o `.git` mais próximo), caminho que muda de sentido conforme a
# pasta, privado caindo no público dentro de um worktree, e `git add -f` /
# `--no-verify` levando material interno para o repositório público.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$(cd "$HERE/../bin" && pwd)"
OK=0; FALHA=0

check() {
  if [ "$2" = "$3" ]; then OK=$((OK+1)); printf '  ok   %s\n' "$1"
  else FALHA=$((FALHA+1)); printf '  FAIL %s\n       esperado=%s\n       obtido  =%s\n' "$1" "$3" "$2"; fi
}

BASE=$(mktemp -d "${TMPDIR:-/tmp}/dual-git-test.XXXXXX")
BASE=$(cd "$BASE" && pwd -P)
trap 'rm -rf "$BASE"' EXIT
# git isolado da configuração de quem roda (hooksPath global, templates, assinatura)
. "$HERE/lib-lar-fingido.sh"
lar_fingido_exporta "$BASE/home"; mkdir -p "$BASE/home"
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
export PATH="$BIN:$PATH"

# novo_projeto <pasta> <conteúdo do .gitignore do público>
novo_projeto() {
  mkdir -p "$1/src" "$1/.claude/notas"
  ( cd "$1" && git init -q -b main && printf '%s\n' "$2" > .gitignore \
    && echo code > src/app.js && git add -A && git commit -qm init \
    && git init -q -b main --bare .git/dev.git \
    && git --git-dir=.git/dev.git config core.bare false \
    && git --git-dir=.git/dev.git config core.worktree ../../.claude )
}

echo "[fora de projeto dual git]"
mkdir -p "$BASE/solta"
( cd "$BASE/solta" && devgit status >/dev/null 2>&1 ); check "fora de repositório sai com 2" "$?" "2"
mkdir -p "$BASE/sem/x"; ( cd "$BASE/sem" && git init -q )
( cd "$BASE/sem" && devgit status >/dev/null 2>&1 ); check "repositório sem privado sai com 2" "$?" "2"

echo
echo "[forma simples: o público ignora .claude/ inteira]"
P="$BASE/p1"; novo_projeto "$P" ".claude/"
echo d > "$P/.claude/notas/a.md"; echo n > "$P/.claude/CLAUDE.md"
check "não nasce .git dentro de .claude/" "$(ls -a "$P/.claude" | grep -c '^\.git$')" "0"
( cd "$P" && devgit add notas/a.md )
( cd "$P/src" && devgit add CLAUDE.md )
check "add relativo a .claude/ da raiz e de src/" "$(cd "$P" && devgit ls-files --cached | tr '\n' ' ')" "CLAUDE.md notas/a.md "
echo e > "$P/.claude/notas/b.md"
( cd "$P/.claude/notas" && devgit add b.md )
check "add relativo à pasta, de dentro de .claude/notas" "$(cd "$P" && devgit ls-files --cached | tr '\n' ' ')" "CLAUDE.md notas/a.md notas/b.md "
( cd "$P" && devgit commit -qm notas )
check "status porcelana igual da raiz, de src/ e de .claude/notas" \
  "$(cd "$P" && devgit status --porcelain)|$(cd "$P/src" && devgit status --porcelain)|$(cd "$P/.claude/notas" && devgit status --porcelain)" "||"
check "status -sb igual da raiz e de .claude/notas" \
  "$(cd "$P" && devgit status -sb)" "$(cd "$P/.claude/notas" && devgit status -sb)"
check "de dentro de .claude/notas, git acha a raiz do público" "$(cd "$P/.claude/notas" && git rev-parse --show-toplevel)" "$P"
check "o público não rastreia nada de .claude/" "$(cd "$P" && git ls-files .claude | wc -l | tr -d ' ')" "0"
check "o público segue limpo" "$(cd "$P" && git status --porcelain)" ""

echo
echo "[forma mista: exceção pública fica fora do privado]"
M="$BASE/p2"; novo_projeto "$M" ".claude/*
!.claude/CLAUDE.md"
echo pub > "$M/.claude/CLAUDE.md"; echo d > "$M/.claude/notas/a.md"; echo s > "$M/.claude/nota.md"
( cd "$M" && git add .claude/CLAUDE.md && git commit -qm idx && devgit add -A )
check "o privado não pega a exceção do público" "$(cd "$M" && devgit ls-files --cached | tr '\n' ' ')" "nota.md notas/a.md "
check "nenhum arquivo com dois donos" \
  "$(cd "$M" && comm -12 <(git ls-files .claude | sed 's|^\.claude/||' | sort) <(devgit ls-files | sort))" ""

echo
echo "[worktree do público]"
( cd "$P" && git worktree add -q "$BASE/wt" -b outra )
( cd "$BASE/wt" && devgit status >/dev/null 2>&1 ); check "dentro do worktree sai com 2" "$?" "2"

echo
echo "[trava contra vazamento]"
git init -q --bare "$BASE/remoto.git"
( cd "$P" && git remote add origin "$BASE/remoto.git" && git push -q -u origin main 2>/dev/null )
saida=$(cd "$P" && devgit-trava); check "instala os dois hooks" "$?" "0"
check "os dois ficam executáveis" "$( [ -x "$P/.git/hooks/pre-commit" ] && [ -x "$P/.git/hooks/pre-push" ] && echo sim)" "sim"
antes=$(cd "$P" && git rev-parse HEAD)
( cd "$P" && git add -f .claude/notas/a.md && git commit -qm vaza >/dev/null 2>&1 ); rc=$?
check "git add -f de arquivo interno: commit recusado" "$rc" "1"
check "HEAD não andou" "$(cd "$P" && git rev-parse HEAD)" "$antes"
( cd "$P" && git reset -q )
printf '# termos\n\nservidor-secreto.exemplo\n' > "$P/.claude/public-terms.txt"
echo "url = servidor-secreto.exemplo" > "$P/src/cfg.js"
( cd "$P" && git add src/cfg.js && git commit -qm termo >/dev/null 2>&1 ); check "termo da lista privada: commit recusado" "$?" "1"
( cd "$P" && git commit -qm termo --no-verify >/dev/null 2>&1 )
( cd "$P" && git push -q origin main >/dev/null 2>&1 ); check "commit com --no-verify: push recusado" "$?" "1"
( cd "$P" && git reset -q --hard HEAD~1 )
echo "limpo" > "$P/src/ok.js"
( cd "$P" && git add src/ok.js && git commit -qm ok >/dev/null 2>&1 ); check "commit limpo passa" "$?" "0"
( cd "$P" && git push -q origin main >/dev/null 2>&1 ); check "push limpo passa" "$?" "0"
( cd "$P" && devgit-trava >/dev/null ); check "reinstalar atualiza sem recusar" "$?" "0"

echo
echo "[trava respeita hook de outra ferramenta e core.hooksPath]"
H="$BASE/p3"; novo_projeto "$H" ".claude/"
printf '#!/bin/sh\necho outro\n' > "$H/.git/hooks/pre-push"
( cd "$H" && devgit-trava >/dev/null 2>&1 ); check "hook alheio: recusa" "$?" "1"
check "hook alheio continua intacto" "$(sed -n 2p "$H/.git/hooks/pre-push")" "echo outro"
( cd "$H" && git config core.hooksPath ganchos && devgit-trava >/dev/null )
check "com core.hooksPath, instala na pasta configurada" "$( [ -x "$H/ganchos/pre-commit" ] && echo sim)" "sim"

if command -v zsh >/dev/null 2>&1; then
  echo
  echo "[chamado a partir do zsh]"
  check "devgit responde igual no zsh e no bash" \
    "$(cd "$P/.claude/notas" && zsh -c 'devgit ls-files')" "$(cd "$P/.claude/notas" && devgit ls-files)"
fi

echo
echo "dual-git: $OK ok, $FALHA falha(s)"
[ "$FALHA" -eq 0 ]
