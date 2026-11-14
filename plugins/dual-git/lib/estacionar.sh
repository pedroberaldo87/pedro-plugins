#!/usr/bin/env bash
# estacionar.sh — tira a pasta do projeto do disco, só se nada se perder. Chamado por
# `devgit estacionar [--mover]` com a raiz do projeto como primeiro argumento.
#
# Três portões (ação A7 do modelo dual git), todos obrigatórios:
#   1. o público está inteiro no remoto — sem mudança local, sem stash, sem commit
#      que remoto nenhum tenha, sem worktree extra;
#   2. o privado também;
#   3. `devgit inventario` sai com 0 — todo segredo e dado tem destino.
# Antes de conferir, busca os dois remotos (`fetch --prune`): sem rede, recusa, porque
# não há como saber se o remoto tem tudo.
#
# Sem `--mover`, só confere e diz se pode. Com `--mover` e os três limpos, grava uma
# ficha fora do projeto (os dois endereços, os commits e o destino dos segredos) e
# manda a pasta para a Lixeira — nunca apaga. Sai com 0 quando pode (ou moveu), 1
# quando algum portão recusa, 2 quando não consegue conferir ou mover.
#
# Limite: etiqueta (tag) local não enviada não é conferida.
set -u
r="$1"; shift
mover=0
for a in "$@"; do
  case "$a" in
    --mover) mover=1 ;;
    *) echo "devgit estacionar: opção desconhecida '$a' (só existe --mover)" >&2; exit 2 ;;
  esac
done
pub() { git -C "$r" -c core.quotePath=false "$@"; }
priv() { git --git-dir="$r/.git/dev.git" --work-tree="$r/.claude" -C "$r/.claude" -c core.quotePath=false "$@"; }
aqui="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
recusas=0
recusa() { recusas=$((recusas+1)); printf '  ⛔ %s\n' "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/       /'; }

# portao <nome> <função git> — confere um dos dois repositórios
portao() {
  local nome="$1" g="$2" x
  echo "[$nome]"
  if [ -z "$($g remote)" ]; then recusa "sem remoto: não há cópia fora do disco"; return; fi
  if ! $g fetch -q --all --prune 2>/dev/null; then
    echo "devgit estacionar: não consegui buscar o remoto do $nome — sem rede não dá para conferir" >&2; exit 2
  fi
  x=$($g status --porcelain); [ -n "$x" ] && recusa "mudança que não está em commit:" "$x"
  x=$($g stash list); [ -n "$x" ] && recusa "stash guardado:" "$x"
  x=$($g log --branches --not --remotes --format='%h %s'); [ -n "$x" ] && recusa "commit que remoto nenhum tem:" "$x"
  # HEAD solto (sem branch) não entra em --branches
  x=$($g log HEAD --not --remotes --branches --format='%h %s' 2>/dev/null); [ -n "$x" ] && recusa "commit sem branch:" "$x"
  [ "$recusas" -eq "${antes:-0}" ] && echo "  ✓ inteiro no remoto"
}

antes=0; portao público pub
if [ "$(pub worktree list --porcelain | grep -c '^worktree ')" -gt 1 ]; then
  recusa "o público tem worktree extra (o trabalho dele não sai com esta pasta):" "$(pub worktree list | sed 1d)"
fi
if [ "${DUALGIT_UNICO:-0}" = 1 ]; then echo "[privado]"; echo "  (repositório único: .claude/ foi conferida junto com o público)"
else antes=$recusas; portao privado priv; fi

echo "[inventário]"
inv=$(bash "$aqui/inventario.sh" "$r"); rc=$?
if [ "$rc" -ne 0 ]; then recusa "inventário recusa:" "$(printf '%s\n' "$inv" | tail -1)"; else echo "  ✓ $(printf '%s\n' "$inv" | tail -1)"; fi

echo
if [ "$recusas" -gt 0 ]; then
  echo "pode sair do disco: NÃO — $recusas recusa(s) acima. A pasta continua onde está."
  exit 1
fi
if [ "$mover" -eq 0 ]; then
  echo "pode sair do disco: sim. Para mover para a Lixeira: devgit estacionar --mover"
  exit 0
fi

# ficha fora do projeto: é ela que diz de onde trazer de volta
nome=$(basename "$r"); quando=$(date +%Y-%m-%dT%H%M%S)
fichas="$HOME/.claude/dual-git/estacionados"; mkdir -p "$fichas"
ficha="$fichas/$nome-$quando.md"
{
  echo "# $nome — estacionado em $quando"
  echo
  echo "- pasta original: $r"
  echo "- público: $(pub remote get-url origin 2>/dev/null) · branch $(pub branch --show-current) · commit $(pub rev-parse --short HEAD)"
  if [ "${DUALGIT_UNICO:-0}" = 1 ]; then echo "- privado: (repositório único)"
  else echo "- privado: $(priv remote get-url origin 2>/dev/null) · branch $(priv branch --show-current) · commit $(priv rev-parse --short HEAD)"; fi
  echo
  echo "## Destinos de segredo e dado"
  # do arquivo de regras, não da saída do inventário: um segredo ausente do disco agora
  # (ex.: clone novo) não aparece no inventário, mas o destino dele continua valendo
  [ -f "$r/.claude/inventario.txt" ] && awk '$1 !~ /^#/ && ($2=="segredo" || $2=="dado") && NF>=3 {d=$0; sub(/^[^ \t]+[ \t]+[^ \t]+[ \t]+/,"",d); print "    " $1 "  →  " d}' "$r/.claude/inventario.txt"
  echo
  echo "## Trazer de volta"
  echo "Receita A5 do modelo dual git (clone do público, privado em .git/dev.git), \`devgit-trava\`, e cada destino acima devolvido ao seu caminho."
} > "$ficha"

if command -v trash >/dev/null 2>&1; then
  trash -s "$r" || { echo "devgit estacionar: a Lixeira recusou a pasta; ficha em $ficha" >&2; exit 2; }
elif [ -d "$HOME/.local/share/Trash/files" ]; then
  mv "$r" "$HOME/.local/share/Trash/files/$nome-$quando" || { echo "devgit estacionar: não consegui mover; ficha em $ficha" >&2; exit 2; }
else
  echo "devgit estacionar: não achei a Lixeira deste sistema; nada foi movido. Ficha em $ficha" >&2; exit 2
fi
echo "movido para a Lixeira: $r"
echo "ficha: $ficha"
echo "(a pasta onde você estava deixou de existir — saia dela: cd ~)"
exit 0
