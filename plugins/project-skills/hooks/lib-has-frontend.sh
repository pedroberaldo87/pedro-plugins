#!/bin/bash
# lib-has-frontend.sh — detecta se um projeto tem interface (frontend/mobile).
# Feito para ser SOURCED (não executa nada por conta própria).
#
# POR QUE EXISTE (achado F2.2 do plano design-como-doc-autoral): design.md só faz
# sentido pra quem TEM tela. Backend puro, CLI e este próprio marketplace não devem
# ser cobrados por um documento de design que não se aplica — cobrança que não cabe
# ensina a ignorar cobrança (mesma lição do §5.3 dos hooks).
#
# Heurística barata, sem git ls-files pesado além do necessário: extensão de
# arquivo de UI, index.html, framework conhecido no package.json, ou projeto mobile
# nativo (iOS/Android). Falso negativo é aceitável (silêncio a mais); falso
# positivo cobraria doc de quem não precisa — por isso os sinais são conservadores.

# has_frontend <dir> — retorna 0 (tem interface) ou 1 (não tem / indeterminado).
has_frontend() {
  local dir="$1"
  [ -n "$dir" ] && [ -d "$dir" ] || return 1

  # A pasta de doc fica FORA da conta (F13.3): protótipo aprovado mora em
  # .claude/docs/prototipo/ e é documentação da interface, não a interface —
  # contá-lo faria todo projeto backend com protótipo ser cobrado por design.md.
  git -C "$dir" ls-files 2>/dev/null | grep -vE '^\.claude/' | grep -qE '\.(tsx|jsx|vue|svelte)$' && return 0
  git -C "$dir" ls-files 2>/dev/null | grep -vE '^\.claude/' | grep -qE '(^|/)index\.html$' && return 0
  git -C "$dir" ls-files 2>/dev/null | grep -vE '^\.claude/' | grep -qE '\.(swift|kt)$' && return 0

  if [ -f "$dir/package.json" ]; then
    grep -qE '"(react|react-dom|vue|svelte|next|@angular/core|solid-js|preact)"' "$dir/package.json" 2>/dev/null && return 0
  fi

  return 1
}
