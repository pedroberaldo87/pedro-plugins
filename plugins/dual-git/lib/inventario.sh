#!/usr/bin/env bash
# inventario.sh — o que NENHUM dos dois repositórios guarda, e o que isso significa
# se a pasta do projeto sair do disco. Chamado por `devgit inventario` com a raiz do
# projeto como primeiro argumento.
#
# Lê o que o público ignora (`git status --ignored`) e o que o privado ignora (o mesmo,
# dentro de `.claude/`), e dá a cada caminho uma classe:
#
#   regenerável   volta sozinho (dependências, caches, saída de ferramenta)    pode sumir
#   ponteiro      arquivo que só aponta para .claude/ e é regenerado por comando  pode sumir
#   rascunho      print, página de decisão, desenho avulso de sessão           pode sumir
#   segredo       .env, chave, pasta secrets/                                  precisa de destino
#   dado          banco local                                                  precisa de destino
#   desconhecido  nenhuma regra reconhece                                      trava a saída
#
# Cada projeto ajusta a classe em `.claude/inventario.txt`, que vale ANTES das regras
# daqui. Uma regra por linha, `<padrão> <classe> [destino]`, com o padrão no formato do
# shell e casado contra o caminho a partir da raiz (pasta termina em `/`). O destino diz
# onde a cópia de um segredo ou dado mora fora do disco; o resto da linha depois da
# classe é o destino. Linha em branco e linha começando com `#` são ignoradas.
#
#   exemplo-local.db  regenerável
#   tmp-*/            rascunho
#   .env              segredo   gerenciador-de-senhas:meu-app/.env
#
# Sai com 0 só quando tudo pode sumir ou tem destino; com 1 quando sobra segredo ou dado
# sem destino, ou desconhecido — a pasta ainda não pode sair do disco.
# Limite: o inventário confia no destino escrito; não confere se a cópia existe lá.
set -u
r="$1"
pub() { git -C "$r" -c core.quotePath=false "$@"; }
priv() { git --git-dir="$r/.git/dev.git" --work-tree="$r/.claude" -C "$r/.claude" -c core.quotePath=false "$@"; }
regras="$r/.claude/inventario.txt"

# classe_de <caminho a partir da raiz> → "<classe>\t<destino ou vazio>"
classe_de() {
  local p="$1" pat cl dest nome
  if [ -f "$regras" ]; then
    while read -r pat cl dest; do
      case "$pat" in ''|'#'*) continue ;; esac
      # shellcheck disable=SC2254
      case "$p" in $pat) printf '%s\t%s\n' "$cl" "$dest"; return ;; esac
    done < "$regras"
  fi
  case "$p" in
    .claude/secrets/*) echo segredo; return ;;
    .claude/.project-doc/backups/|.claude/.project-doc/staging*/|.claude/worktrees/) echo regenerável; return ;;
    .claude/visual/|.claude/prints/|.claude/archify/|.claude/intent/) echo rascunho; return ;;
    .github/copilot-instructions.md) echo ponteiro; return ;;
  esac
  nome="${p%/}"; nome="${nome##*/}"
  case "$nome" in
    .env|.env.*|*.pem|*.key|*.p12|*.pfx|*.keystore|secrets) echo segredo ;;
    node_modules|.venv|venv|__pycache__|*.pyc|.pytest_cache|.mypy_cache|.ruff_cache|.cache|.next|.nuxt|dist|build|coverage|graphify-out|.playwright-mcp|*.cache.json|.DS_Store|Thumbs.db) echo regenerável ;;
    *.db|*.sqlite|*.sqlite3|*.db-wal|*.db-shm|*.db-journal) echo dado ;;
    AGENTS.md|GEMINI.md|.cursorrules|.windsurfrules|.clinerules) echo ponteiro ;;
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.mp4|*.webm|*.log) echo rascunho ;;
    *) echo desconhecido ;;
  esac
}

saida=$(mktemp); trap 'rm -f "$saida"' EXIT

# grava <classe\tdestino> <caminho> — uma linha "classe\tcaminho\tdestino" na saída
grava() { printf '%s\t%s\t%s\n' "${1%%	*}" "$2" "$(printf '%s' "$1" | cut -s -f2-)" >> "$saida"; }

# anota <caminho a partir da raiz> <como listar o conteúdo, se for pasta sem regra>
anota() {
  local p="$1" cd cl
  cd=$(classe_de "$p"); cl="${cd%%	*}"
  if [ "$cl" = desconhecido ] && [ "${p%/}" != "$p" ]; then
    # pasta que nenhuma regra reconhece: classifica o que tem dentro, arquivo a arquivo
    case "$2" in
      pub)  pub ls-files -z -o -i --exclude-standard -- "$p" ;;
      priv) priv ls-files -z -o -i --exclude-standard -- "${p#.claude/}" | while IFS= read -r -d '' f; do printf '.claude/%s\0' "$f"; done ;;
    esac | while IFS= read -r -d '' f; do grava "$(classe_de "$f")" "$f"; done
    return
  fi
  grava "$cd" "$p"
}

pub status --porcelain -z --ignored | while IFS= read -r -d '' e; do
  case "$e" in '!! '*) ;; *) continue ;; esac
  p="${e#!! }"
  [ "$p" = ".claude/" ] && continue          # é a pasta de trabalho do privado
  anota "$p" pub
done
# repositório único: o .claude/ já entrou na lista de cima, pelo próprio git
[ "${DUALGIT_UNICO:-0}" = 1 ] || priv status --porcelain -z --ignored | while IFS= read -r -d '' e; do
  case "$e" in '!! '*) ;; *) continue ;; esac
  anota ".claude/${e#!! }" priv
done

ordem() { case "$1" in desconhecido) echo 1;; segredo) echo 2;; dado) echo 3;; regenerável) echo 4;; ponteiro) echo 5;; rascunho) echo 6;; *) echo 7;; esac; }
while IFS="$(printf '\t')" read -r cl p dest; do printf '%s\t%s\t%s\t%s\n' "$(ordem "$cl")" "$cl" "$p" "$dest"; done < "$saida" \
  | sort -t "$(printf '\t')" -k1,1n -k3,3 | while IFS="$(printf '\t')" read -r _ cl p dest; do
      # alinha por LETRA, não por byte: printf %-13s conta o "á" de regenerável como dois
      printf '%s%*s %s%s\n' "$cl" $(( 13 - $(printf '%s' "$cl" | wc -m) )) '' "$p" "${dest:+  → $dest}"
    done

conta() { awk -F'\t' -v c="$1" '$1==c' "$saida" | wc -l | tr -d ' '; }
sem_destino() { awk -F'\t' -v c="$1" '$1==c && $3==""' "$saida" | wc -l | tr -d ' '; }
echo
resumo=""
for c in desconhecido segredo dado regenerável ponteiro rascunho; do
  n=$(conta "$c"); [ "$n" -gt 0 ] && resumo="$resumo · $c $n"
done
echo "${resumo# · }"
falta=$(( $(conta desconhecido) + $(sem_destino segredo) + $(sem_destino dado) ))
if [ "$falta" -gt 0 ]; then
  echo "pode sair do disco: NÃO — $(sem_destino segredo) segredo(s) e $(sem_destino dado) dado(s) sem destino, $(conta desconhecido) desconhecido(s) sem classe (.claude/inventario.txt)"
  exit 1
fi
echo "pode sair do disco: sim — o que fica para trás volta sozinho, pode sumir ou tem destino"
exit 0
