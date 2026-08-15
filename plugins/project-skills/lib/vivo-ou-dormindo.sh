#!/usr/bin/env bash
# vivo-ou-dormindo.sh — responde se há TRABALHO VIVO na máquina, e responde
# medindo, nunca olhando.
#
# Por que existe: quem pergunta "tem build rodando?" costuma tirar UMA foto
# (`%CPU` do `ps`, ou o olho do agente na lista de processos) e chamar de
# medida. Foto não separa o processo que trabalha do que está pendurado há uma
# hora: os dois aparecem na lista, e o `%CPU` de uma foto é a média desde que o
# processo nasceu, não o que ele faz agora. Aqui a pergunta é respondida por
# DIFERENÇA: o tempo de CPU ACUMULADO (`ps -o time=`, que só anda quando o
# processo executa) é lido em DUAS amostras separadas por alguns segundos, e o
# veredito é o que mudou entre elas.
#
# Uso:  bash vivo-ou-dormindo.sh [segundos-entre-amostras] [--grupo PGID]
#       (default: 3 segundos; sem `--grupo`, mede a máquina inteira)
#
# Imprime UMA palavra em stdout:
#   vivo        — algum processo de build/servidor consumiu CPU entre as amostras
#   dormindo    — mediu, e ninguém andou (exit 0)
#   nao-medido  — NÃO conseguiu medir (`ps` ausente/mudo). Exit 2, e o motivo vai
#                 em stderr. Medidor que não mediu nunca devolve `vivo`: quem
#                 consome trata `nao-medido` como ausência de sinal de vida, jamais
#                 como sinal verde.
set -u

# O TEMPO DO `ps` VEM COM PONTO DECIMAL, E O `awk` O LÊ PELO LOCALE. Em locale de
# vírgula (pt_BR, de_DE, fr_FR…) o `awk` corta a string no ponto: `"33.94"` vira
# `33`, e a fração de segundo — que é TUDO o que separa duas amostras a 3s de
# distância — some. Medido nesta máquina (LANG=pt_BR.UTF-8):
#
#   echo "33.94" | awk '{printf "%d", $1*100}'  →  3300   (locale pt)
#   echo "33.94" | awk '{printf "%d", $1*100}'  →  3394   (LC_ALL=C)
#
# E o `ps` real devolve exatamente tempos onde só a fração anda: `0:00.43` →
# `0:00.48`. Sem isto, as duas amostras dão o mesmo inteiro, o delta é zero, e o
# medidor responde "dormindo" com o processo trabalhando — desarmando o vigia
# justamente na máquina de quem usa. `LC_ALL=C` só afeta a leitura de número aqui.
export LC_ALL=C

ESPERA="${1:-3}"

# ESCOPO OPCIONAL: um GRUPO de processos, em vez da máquina inteira.
#
#   bash vivo-ou-dormindo.sh 3 --grupo 41234
#
# Quem pergunta "esta tarefa que eu disparei está trabalhando?" não pode aceitar
# como resposta o vizinho: numa esteira com oito suítes em paralelo, a máquina
# está SEMPRE viva, e o veredito global nunca acusaria a que pendurou. Com o
# grupo, a mesma medição por diferença responde só pela árvore daquele disparo —
# e aí o filtro por NOME sai de cena, porque a árvore é dela por definição, rode
# ela o interpretador que rodar.
GRUPO=""
if [ "${2:-}" = "--grupo" ]; then GRUPO="${3:-}"; fi

# Nomes de processo que caracterizam trabalho de construção/servidor. Nome sozinho
# nunca é veredito — ele só escolhe QUEM medir; quem decide é o delta de CPU.
PADRAO='node|npm|pnpm|yarn|bun|deno|vite|webpack|esbuild|tsc|jest|vitest|python|pytest|ruby|rails|cargo|rustc|go|java|gradle|maven|mvn|make|cc1|clang|gcc|swift|xcodebuild|docker|next|nuxt|astro|turbo'

amostra() {
  # pid<tab>centesimos-de-segundo-de-CPU-acumulados, um por processo que interessa.
  ps -eo pid=,pgid=,time=,args= 2>/dev/null | awk -v pad="$PADRAO" -v grupo="$GRUPO" '
    {
      pid = $1; pg = $2; t = $3
      cmd = ""; for (i = 4; i <= NF; i++) cmd = cmd " " $i
      # minúsculas e sufixo de versão: o mesmo interpretador aparece como
      # `python`, `python3.14` e `.../MacOS/Python` na mesma máquina.
      if (grupo != "") { if (pg != grupo) next }
      else if (tolower(cmd) !~ ("(^| |/)(" pad ")[0-9.]*([ /]|$)")) next
      gsub("-", ":", t)                                   # [DD-]HH:MM:SS[.ss]
      n = split(t, p, ":")
      seg = 0; for (i = 1; i <= n; i++) seg = seg * 60 + p[i]
      printf "%s\t%d\n", pid, seg * 100
    }'
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

amostra > "$TMP/a"
if [ ! -s "$TMP/a" ]; then
  echo "nao-medido"
  echo "vivo-ou-dormindo: a primeira amostra saiu vazia (ps ausente, mudo, ou nenhum processo de build/servidor na maquina)" >&2
  exit 2
fi

sleep "$ESPERA"
amostra > "$TMP/b"
if [ ! -s "$TMP/b" ]; then
  echo "nao-medido"
  echo "vivo-ou-dormindo: a segunda amostra saiu vazia - sem duas amostras nao ha diferenca para medir" >&2
  exit 2
fi

# Andou quem existe nas DUAS amostras com tempo de CPU maior na segunda. Processo
# que so aparece na segunda nao conta: dele nao ha diferenca, so uma foto.
awk -F'\t' 'NR == FNR { ant[$1] = $2; next }
             ($1 in ant) && $2 > ant[$1] { print "vivo"; achou = 1; exit }
             END { if (!achou) print "dormindo" }' "$TMP/a" "$TMP/b"
