#!/bin/bash
# lib-project-root.sh — resolução ÚNICA da raiz do projeto para o gate de plano.
# Feito para ser SOURCED (não executa nada por conta própria).
#
# POR QUE EXISTE: o PHASH (cksum da raiz) é a chave dos sentinels em /tmp. Se dois
# hooks derivarem a raiz de formas diferentes, eles geram chaves diferentes e o
# sentinel de um nunca é visto pelo outro — falha silenciosa, o gate nunca libera.
#
# Foi exatamente o bug que a suíte pegou: `git rev-parse --show-toplevel` devolve o
# caminho FÍSICO (/private/var/...), enquanto o posttooluse-doc-read.sh deriva a raiz
# recortando a STRING do file_path (/var/...). No macOS /var é symlink de /private/var
# ⇒ hashes diferentes ⇒ o sentinel de leitura nunca resolveria o gate.
#
# REGRA: NUNCA canonicalize (nada de `git rev-parse`, `realpath`, `pwd -P`). Trabalhe
# com a string que o harness mandou, igual ao doc-guard (find_doc_up) e ao
# posttooluse-doc-read.sh. Consistência vale mais que "correção" de path aqui.

# project_root <cwd> — imprime a raiz, ou nada. Retorna 1 se não achou.
#   1º) ancestral mais próximo com CLAUDE.md ou .claude/CLAUDE.md  → casa o PHASH
#       do posttooluse-doc-read.sh (é ele quem escreve o sentinel de leitura).
#   2º) senão, ancestral mais próximo com marcador de projeto — cobre o caso
#       "projeto sem documentação nenhuma", onde só importa gate e escape
#       concordarem entre si.
project_root() {
  local d="$1" m
  [ -n "$d" ] || return 1
  # Barra final é o MESMO modo de falha entrando pelo outro lado: "/a/b" e "/a/b/"
  # dão cksum diferente e o sentinel não casa. Normalizar a barra é a única
  # normalização permitida aqui (não muda o caminho, só a grafia).
  while [ "${d}" != "/" ] && [ "${d%/}" != "${d}" ]; do d="${d%/}"; done

  local walk="$d"
  while [ -n "$walk" ] && [ "$walk" != "/" ] && [ "$walk" != "$HOME" ]; do
    if [ -f "$walk/CLAUDE.md" ] || [ -f "$walk/.claude/CLAUDE.md" ]; then
      printf '%s' "$walk"; return 0
    fi
    walk=$(dirname "$walk")
  done

  walk="$d"
  while [ -n "$walk" ] && [ "$walk" != "/" ] && [ "$walk" != "$HOME" ]; do
    for m in .git package.json pyproject.toml Cargo.toml go.mod .claude; do
      if [ -e "$walk/$m" ]; then printf '%s' "$walk"; return 0; fi
    done
    walk=$(dirname "$walk")
  done

  return 1
}

# project_hash <root> — a chave dos sentinels. Mesma fórmula do doc-guard.
project_hash() { printf '%s' "$1" | cksum | cut -d' ' -f1; }
