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
# comparado com o que o próprio git diz da raiz: no Windows ele responde C:/…, não /tmp/…
check "de dentro de .claude/notas, git acha a raiz do público" \
  "$(cd "$P/.claude/notas" && git rev-parse --show-toplevel)" "$(cd "$P" && git rev-parse --show-toplevel)"
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

# com_remoto <pasta> — dá ao projeto um remoto `origin` em pasta local, com a main enviada
com_remoto() {
  git init -q --bare "$1.remoto.git"
  ( cd "$1" && git remote add origin "$1.remoto.git" && git push -q -u origin main 2>/dev/null )
}
# no_remoto <pasta> <ref> — quantos caminhos de .claude/ ou .env a ref do remoto já viu
no_remoto() {
  git --git-dir="$1.remoto.git" log "$2" --name-only --format= 2>/dev/null | grep -cE '^(\.claude/|\.env$)'
}

echo
echo "[devgit chamado por um hook do público]"
# O git exporta GIT_INDEX_FILE para o hook. Herdado, o privado gravava na área de
# preparação do público e o commit do público abortava com "invalid object".
K="$BASE/p4"; novo_projeto "$K" ".claude/"; echo interno > "$K/.claude/notas/s.md"
printf '#!/bin/sh\ndevgit add -A\n' > "$K/.git/hooks/pre-commit"; chmod +x "$K/.git/hooks/pre-commit"
( cd "$K" && echo x >> src/app.js && git commit -qam "muda" >/dev/null 2>&1 ); check "o commit do público passa" "$?" "0"
check "o público não ganhou arquivo interno" "$(cd "$K" && git ls-tree -r --name-only HEAD | tr '\n' ' ')" ".gitignore src/app.js "
check "o privado recebeu o arquivo" "$(cd "$K" && devgit ls-files | tr '\n' ' ')" "notas/s.md "
check "com GIT_DIR e GIT_INDEX_FILE no ambiente, devgit segue no privado" \
  "$(cd "$K" && GIT_DIR=.git GIT_INDEX_FILE="$K/.git/index" devgit ls-files | tr '\n' ' ')" "notas/s.md "

echo
echo "[exceção pública escrita com barra inicial]"
E="$BASE/p5"; novo_projeto "$E" "/.claude/*
!/.claude/CLAUDE.md"
echo pub > "$E/.claude/CLAUDE.md"; echo d > "$E/.claude/notas/a.md"
( cd "$E" && git add .claude/CLAUDE.md && git commit -qm idx && devgit add -A )
check "nenhum arquivo com dois donos" \
  "$(cd "$E" && comm -12 <(git ls-files .claude | sed 's|^\.claude/||' | sort) <(devgit ls-files | sort))" ""


echo
echo "[projeto sem .claude/.gitignore: segredo e worktree ficam fora mesmo assim]"
S="$BASE/p8"; novo_projeto "$S" ".claude/"
mkdir -p "$S/.claude/secrets"; echo "SENHA=abc12345" > "$S/.claude/secrets/ops.env"; echo d > "$S/.claude/notas/a.md"
( cd "$S" && git worktree add -q .claude/worktrees/w -b w && devgit add -A 2>/dev/null )
check "devgit add -A pega só o material interno" "$(cd "$S" && devgit ls-files --cached | tr '\n' ' ')" "notas/a.md "

echo
echo "[caminho escrito a partir da raiz do projeto]"
aviso=$(cd "$E" && devgit add .claude/notas/a.md 2>&1 >/dev/null | head -1)
check "avisa que o caminho é relativo a .claude/" "$aviso" "devgit: caminho é relativo a .claude/ — escreva 'notas/a.md', não '.claude/notas/a.md'"

echo
echo "[trava de saída confere o que está sendo ENVIADO, não a branch em uso]"
T="$BASE/p6"; novo_projeto "$T" ".claude/
.env"; com_remoto "$T"; ( cd "$T" && devgit-trava >/dev/null )
( cd "$T" && echo "SENHA=abc12345" > .env && git add -f .env && git commit -qm entra --no-verify \
  && git rm -q --cached .env && git commit -qm sai --no-verify && git push -q origin main >/dev/null 2>&1 )
check "arquivo ignorado que entrou e saiu antes do push: recusado" "$?" "1"
check "o remoto não recebeu" "$(no_remoto "$T" main)" "0"
( cd "$T" && git reset -q --hard origin/main )
( cd "$T" && git switch -q -c lateral && echo n > .claude/notas/a.md && git add -f .claude/notas/a.md \
  && git commit -qm interno --no-verify && git switch -q main && git push -q origin lateral >/dev/null 2>&1 )
check "branch que não é a atual, com arquivo interno: recusada" "$?" "1"
check "o remoto não ganhou a branch" "$(git --git-dir="$T.remoto.git" rev-parse -q --verify lateral >/dev/null && echo tem || echo nao)" "nao"
( cd "$T" && echo ok > src/b.js && git add src/b.js && git commit -qm limpo >/dev/null && git push -q origin main >/dev/null 2>&1 )
check "push limpo passa mesmo com outra branch local suja" "$?" "0"
( cd "$T" && git push -q origin main >/dev/null 2>&1 ); check "push sem nada a enviar passa" "$?" "0"
( cd "$T" && sh .git/hooks/pre-push </dev/null >/dev/null 2>&1 ); check "rodada à mão, acusa a branch suja não enviada" "$?" "1"
( cd "$T" && git branch -q -D lateral && sh .git/hooks/pre-push </dev/null >/dev/null 2>&1 ); check "rodada à mão, sem pendência, passa" "$?" "0"
( cd "$T" && mkdir -p .claude/notas && echo n > ".claude/notas/ação nova.md" && git add -f ".claude/notas/ação nova.md" && git commit -qm x >/dev/null 2>&1 )
check "nome com espaço e acento: commit recusado" "$?" "1"
( cd "$T" && git commit -qm x --no-verify && git push -q origin main >/dev/null 2>&1 )
check "nome com espaço e acento: push recusado" "$?" "1"
( cd "$T" && git reset -q --hard origin/main )

echo
echo "[trava de saída: termo privado fora do conteúdo da branch atual]"
mkdir -p "$T/.claude"   # o reset acima levou a pasta junto com o arquivo forçado
printf '# termos\r\nservidor-secreto.exemplo\r\n' > "$T/.claude/public-terms.txt"
( cd "$T" && echo y >> src/app.js && git commit -qam "deploy em servidor-secreto.exemplo" >/dev/null && git push -q origin main >/dev/null 2>&1 )
check "termo na mensagem do commit: push recusado (lista com fim de linha do Windows)" "$?" "1"
( cd "$T" && git reset -q --hard origin/main && git checkout -q --detach \
  && echo "url=servidor-secreto.exemplo" > src/cfg.js && git add src/cfg.js && git commit -qm cfg --no-verify \
  && git push -q origin HEAD:main >/dev/null 2>&1 )
check "commit sem branch: push recusado" "$?" "1"
( cd "$T" && git switch -q main && git reset -q --hard origin/main \
  && git switch -q -c lado && echo lado > src/app.js && git commit -qam lado \
  && git switch -q main && echo principal > src/app.js && git commit -qam principal )
( cd "$T" && git merge -q lado >/dev/null 2>&1; echo "url=servidor-secreto.exemplo" > src/app.js \
  && git add src/app.js && git commit -qm merge --no-verify && git push -q origin main >/dev/null 2>&1 )
check "termo escrito na resolução de um merge: push recusado" "$?" "1"
( cd "$T" && git reset -q --hard HEAD~1 && git merge -q lado >/dev/null 2>&1; echo resolvido > src/app.js \
  && git add src/app.js && git commit -qm merge >/dev/null && git push -q origin main >/dev/null 2>&1 )
check "merge limpo passa" "$?" "0"
printf '# só comentário\n\n' > "$T/.claude/public-terms.txt"
( cd "$T" && echo z >> src/b.js && git commit -qam "lista sem termo" >/dev/null 2>&1 && git push -q origin main >/dev/null 2>&1 )
check "lista de termos só com comentário não recusa nada" "$?" "0"

echo
echo "[trava não se instala onde já há arquivo ignorado rastreado]"
G="$BASE/p7"; novo_projeto "$G" ".claude/
*.log"; com_remoto "$G"
# o arquivo já estava no remoto antes de a trava existir — o caso de quem adota o modelo
( cd "$G" && echo amostra > a.log && git add -f a.log && git commit -qm "de proposito" && git push -q origin main 2>/dev/null )
( cd "$G/src" && devgit-trava >/dev/null 2>&1 ); check "recusa instalar, mesmo chamada de subpasta" "$?" "1"
check "não deixou hook nenhum" "$(ls "$G/.git/hooks" | grep -cE '^pre-(commit|push)$')" "0"
( cd "$G" && git rm -q --cached a.log && git commit -qm limpa && cd src && devgit-trava >/dev/null )
check "depois de resolvido, instala na raiz a partir da subpasta" "$( [ -x "$G/.git/hooks/pre-push" ] && echo sim)" "sim"
( cd "$G" && git push -q origin main >/dev/null 2>&1 )
check "o commit que só REMOVE o arquivo ignorado passa no push" "$?" "0"

echo
echo "[inventário: o que nenhum dos dois repositórios guarda]"
I="$BASE/p9"; novo_projeto "$I" ".claude/
.env
*.db
node_modules/
*.png
AGENTS.md
.github/copilot-instructions.md
misterio/
nota de ação.txt"
( cd "$I" && mkdir -p node_modules/x .github misterio .claude/secrets .claude/visual \
  && echo s > .env && echo d > app.db && echo m > node_modules/x/i.js && echo p > print.png \
  && echo a > AGENTS.md && echo c > .github/copilot-instructions.md && echo ? > misterio/coisa.bin \
  && echo e > "nota de ação.txt" && echo k > .claude/secrets/ops.env && echo v > .claude/visual/p.html \
  && printf 'visual/\n' > .claude/.gitignore )
inv=$(cd "$I/src" && devgit inventario); rc=$?
linha() { printf '%s\n' "$inv" | awk -v p="$1" '{c=$1; $1=""; sub(/^ +/,""); if ($0==p) print c}'; }
check ".env é segredo" "$(linha .env)" "segredo"
check "banco é dado" "$(linha app.db)" "dado"
check "node_modules é regenerável" "$(linha node_modules/)" "regenerável"
check "print é rascunho" "$(linha print.png)" "rascunho"
check "AGENTS.md é ponteiro" "$(linha AGENTS.md)" "ponteiro"
check "pasta ignorada sem regra é aberta: o arquivo de dentro é ponteiro" "$(linha .github/copilot-instructions.md)" "ponteiro"
check "arquivo sem regra é desconhecido" "$(linha misterio/coisa.bin)" "desconhecido"
check "nome com espaço e acento sai inteiro" "$(linha 'nota de ação.txt')" "desconhecido"
check "segredo do privado aparece com o caminho a partir da raiz" "$(linha .claude/secrets/)" "segredo"
check "página de decisão do privado é rascunho" "$(linha .claude/visual/)" "rascunho"
check "a pasta do privado não aparece como ignorada do público" "$(linha .claude/)" ""
check "com segredo, dado e desconhecido: sai com 1" "$rc" "1"
check "desconhecido vem primeiro" "$(printf '%s\n' "$inv" | head -1 | awk '{print $1}')" "desconhecido"
printf '# classes deste projeto\n\napp.db regenerável\nmisterio/* rascunho\nnota*.txt rascunho\n.env regenerável\n.claude/secrets/ regenerável\n' > "$I/.claude/inventario.txt"
inv=$(cd "$I" && devgit inventario); rc=$?
check "o arquivo do projeto reclassifica antes das regras" "$(linha app.db)" "regenerável"
check "padrão com curinga classifica a pasta inteira de uma vez" "$(linha misterio/)" "rascunho"
check "tudo pode sumir: sai com 0" "$rc" "0"
check "e diz que pode sair do disco" "$(printf '%s\n' "$inv" | tail -1 | cut -c1-24)" "pode sair do disco: sim "

if command -v zsh >/dev/null 2>&1; then
  echo
  echo "[chamado a partir do zsh]"
  check "devgit responde igual no zsh e no bash" \
    "$(cd "$P/.claude/notas" && zsh -c 'devgit ls-files')" "$(cd "$P/.claude/notas" && devgit ls-files)"
fi

echo
echo "dual-git: $OK ok, $FALHA falha(s)"
[ "$FALHA" -eq 0 ]
