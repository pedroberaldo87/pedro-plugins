#!/bin/bash
# resolve-dir.sh — decide ONDE um artefato de skill é salvo, no projeto de quem usa.
#
# ⚠️ FONTE DA VERDADE: `_shared/resolve-dir.sh`. As cópias dentro dos plugins são
# vendoradas por `scripts/sync-shared.sh` — editar a cópia deixa as outras defasadas.
#
# Cascata de 3 níveis (para no primeiro que bater):
#   1. Raiz do repositório git  → <raiz-git>/.claude/<subdir>
#   2. Projeto reconhecido por marcador (package.json, CLAUDE.md, etc.),
#      subindo a partir do cwd e parando ANTES de $HOME → <dir>/.claude/<subdir>
#   3. Reserva no Desktop → ~/Desktop/claude-<subdir>/<pasta>-<id-estável>
#      A identidade da pasta de origem entra no caminho: sem ela TODA pasta sem
#      marcador caía no MESMO pote e uma sessão via o plano de outro projeto como
#      se fosse dela. O <id-estável> é o cksum do caminho de origem — a mesma
#      pasta resolve sempre pro mesmo destino, sem data, sorteio nem contador.
#      Quando a reserva é usada, o script sai com CÓDIGO 3 (o stdout continua
#      sendo só o caminho, e o texto do aviso continua indo pro stderr).
#      O código de saída é o canal que vale: TODO consumidor deste script chama
#      com `2>/dev/null`, então avisar só no stderr é avisar no vazio. Quem lê o
#      resultado precisa saber que ele não veio de projeto, e é o `$?` que conta.
#      Nível 1 e nível 2 saem com 0. Consumidor que ignora o `$?` continua
#      funcionando igual — o contrato do stdout não mudou.
#
# Uso:   resolve-dir.sh <cwd> [subdir]
#        subdir default = "visual". Passe "plans" para o store de planos
#        (ver lib/plan_state.py) ou "archify" para os diagramas do /archify —
#        mesma cascata, outro diretório. Cada família de artefato tem a própria
#        pasta: misturar diagrama com relatório e plano é o que faz o usuário
#        não achar o que gerou ontem.
#        O subdir pode ter BARRA: "docs/fluxos" resolve para a pasta  casa-ok: nomeia o argumento literal que o chamador passa
#        `fluxos` dentro da casa da doc — a casa canônica versionada dos
#        diagramas de fluxo. Na reserva a barra vira traço
#        (~/Desktop/claude-docs-fluxos/<pasta>-<id>), senão a gaveta por pasta
#        de origem se parte em duas e o "claude-docs" vira pote comum.
# Saída: caminho absoluto do diretório-alvo no stdout (já criado com mkdir -p).
#        Código de saída: 0 = veio de projeto · 3 = veio da RESERVA.
#
# Quem chama: o hook pre-exitplan-visualize.sh, a invocação manual do /visual, o
# motor de plano e a skill /archify — todos por aqui, pra nunca divergirem.

CWD="${1:-$PWD}"
SUB="${2:-visual}"
DESKTOP="$HOME/Desktop/claude-${SUB//\//-}"

resolve() {
  # Nível 1 — raiz do repositório git (robusto: cobre worktrees/submodules)
  if [ -d "$CWD" ]; then
    git_root=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$git_root" ]; then
      # Worktree LIGADO: o .claude/ é do repositório PRINCIPAL. O worktree nasce
      # sem ele (.claude/ é ignorado pelo git, então `git worktree add` entrega a
      # pasta vazia) e quem resolve pelo topo do worktree escreve num pote vazio
      # — foi assim que 5 commits de trabalho não marcaram passo nenhum no plano.
      common=$(git -C "$CWD" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
      principal=$(dirname "$common")
      if [ -n "$common" ] && [ "$principal" != "$git_root" ] && [ -d "$principal" ]; then
        printf '%s\n' "$principal/.claude/$SUB"
        return 0
      fi
      printf '%s\n' "$git_root/.claude/$SUB"
      return 0
    fi
  fi

  # Nível 2 — sobe procurando marcador de projeto, parando antes de $HOME e /
  dir="$CWD"
  while [ -n "$dir" ] && [ "$dir" != "/" ] && [ "$dir" != "$HOME" ]; do
    if [ -e "$dir/package.json" ] || [ -e "$dir/CLAUDE.md" ] || \
       [ -e "$dir/pyproject.toml" ] || [ -e "$dir/Cargo.toml" ] || \
       [ -e "$dir/go.mod" ] || [ -d "$dir/graphify-out" ] || [ -d "$dir/.git" ]; then
      printf '%s\n' "$dir/.claude/$SUB"
      return 0
    fi
    dir=$(dirname "$dir")
  done

  # Nível 3 — reserva, uma gaveta POR PASTA DE ORIGEM
  origem="${CWD%/}"; [ -z "$origem" ] && origem="/"
  nome=$(basename "$origem" 2>/dev/null | tr -c '[:alnum:]._-' '-' | tr -s '-')
  nome="${nome%-}"; [ -z "$nome" ] && nome="sem-nome"
  id=$(printf '%s' "$origem" | cksum | cut -d' ' -f1)
  printf '%s\n' "$DESKTOP/$nome-$id"
  # O texto vai pro stderr; o SINAL vai no código de saída. Quem chama descarta o
  # stderr (todos descartam), então é o 3 que carrega o aviso até o consumidor.
  printf '⚠️  resolve-dir: "%s" não é (nem está dentro de) um projeto reconhecido — %s veio da RESERVA %s, não deste projeto.\n' \
    "$origem" "$SUB" "$DESKTOP/$nome-$id" >&2
  return 3
}

TARGET=$(resolve); DE_RESERVA=$?
mkdir -p "$TARGET" 2>/dev/null
printf '%s\n' "$TARGET"
exit "$DE_RESERVA"
