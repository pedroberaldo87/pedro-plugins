#!/usr/bin/env bash
# test_release_gate_prazo.sh — o portão não morre calado (F17.1) e o deadline
# cabe no teto do hook (F17.5).
#
# Por que esta suíte existe, medido em 2026-08-14: o release-gate levava 4min57 a
# 8min50 e o teto do hook estava em 60s desde 31/07. O harness o matava antes de
# ele imprimir qualquer coisa, e PreToolUse que não responde é fail-open — todo
# commit desde que o portão ficou lento entrou SEM verificação nenhuma. Foi assim
# que `cfc1090` publicou o espelho do lixeiro quebrado. Ninguém media o portão
# contra o próprio teto: ele cresceu de 192 para 565 linhas e nada acusou.
#
#   bash .claude/hooks/test_release_gate_prazo.sh
set -uo pipefail

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PORTAO="$RAIZ/.claude/hooks/release-gate.sh"
PAYLOAD='{"tool_input":{"command":"git commit -m teste"}}'
ok=0; falhas=0

check() {
  if [ "$2" = "1" ]; then ok=$((ok+1)); printf '  ✓ %s\n' "$1"
  else falhas=$((falhas+1)); printf '  ✗ %s\n' "$1"; [ -n "${3:-}" ] && printf '      %s\n' "$3"
  fi
}

echo "F17.1 — o portão recusa quando não consegue medir"

# ⚠️ O PORTÃO SÓ TRABALHA COM ARQUIVO NO COMMIT. Ele sai cedo em
# `[ -n "$FILES" ] || exit 0` quando não há staged nem modificado — e aí nunca
# chega ao bloco do prazo. A primeira versão desta suíte não sabia disso e passou
# POR ACIDENTE: a árvore estava suja na hora em que foi escrita. Com a árvore
# limpa ela reprovou, e quem pegou foi a guarda de saúde do motor.
#
# A SEGUNDA versão sabia, e foi pior: ela sujava o `release-gate.sh` DE VERDADE
# para criar o estado, restaurando no trap. Com duas execuções concorrentes — o
# motor rodando a esteira enquanto eu rodava à mão — as iscas empilharam e o
# portão de produção foi de 565 para 1392 linhas, com 760 de lixo COMMITADO.
# Teste que escreve em arquivo de produção não tem restauração segura: basta
# outro processo ler no meio.
#
# Esta versão monta um REPOSITÓRIO DE MENTIRA. O portão descobre a raiz pelo
# `git rev-parse` do diretório em que roda e só age se achar o `marketplace.json`
# — as duas coisas são baratas de fabricar, e ali ele pode sujar à vontade.
FALSO="$(mktemp -d "${TMPDIR:-/tmp}"/prazo-repo-XXXXXX)"
trap 'rm -rf "$FALSO"' EXIT
git -C "$FALSO" init -q
mkdir -p "$FALSO/.claude-plugin" "$FALSO/.claude/hooks"
echo '{"plugins":[]}' > "$FALSO/.claude-plugin/marketplace.json"
echo "conteudo" > "$FALSO/arquivo.txt"
git -C "$FALSO" add -A
git -C "$FALSO" -c user.email=t@t -c user.name=t commit -qm inicial
# O modificado que faz o portão trabalhar em vez de sair cedo.
echo "mudou" >> "$FALSO/arquivo.txt"
# O `settings.json` de mentira dá o teto que o F17.5 confere no repo de verdade.
cat > "$FALSO/.claude/settings.json" <<'JSON'
{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[
  {"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/release-gate.sh","timeout":600}]}]}}
JSON

SUJOS=$(git -C "$FALSO" diff --name-only | wc -l | tr -d ' ')
check "a suíte montou o repositório de mentira que o portão precisa" \
      "$([ "$SUJOS" -gt 0 ] && echo 1 || echo 0)" \
      "sem arquivo modificado o portão sai antes do prazo e o teste mediria nada"

# Deadline de 1s força o estouro no primeiro ponto de verificação, sem esperar os
# minutos reais. É o mesmo caminho do estouro de verdade — muda só o relógio.
SAIDA=$(cd "$FALSO" && printf '%s' "$PAYLOAD" | PORTAO_DEADLINE_S=1 bash "$PORTAO" 2>&1)
CODIGO=$?
check "estourado o prazo, o portão RECUSA (exit 2)" "$([ "$CODIGO" = "2" ] && echo 1 || echo 0)" "exit=$CODIGO"
case "$SAIDA" in
  *"NÃO TER CONSEGUIDO MEDIR"*) check "a recusa diz que ele não MEDIU (não que achou defeito)" 1 ;;
  *) check "a recusa diz que ele não MEDIU (não que achou defeito)" 0 "${SAIDA:0:200}" ;;
esac
case "$SAIDA" in
  *"Já tinha medido:"*) check "a recusa nomeia o que já foi medido" 1 ;;
  *) check "a recusa nomeia o que já foi medido" 0 "${SAIDA:0:200}" ;;
esac
# Sem o caminho de saída escrito, quem apanha da trava a contorna — e contornar
# desliga tudo, que é a lição da linha 17 do próprio portão.
case "$SAIDA" in
  *"scripts/suite.sh"*) check "a recusa diz o que fazer a seguir" 1 ;;
  *) check "a recusa diz o que fazer a seguir" 0 "${SAIDA:0:200}" ;;
esac

# O par que faz o caso acima morder: sem ele, um portão que recusasse SEMPRE
# passaria nos quatro checks.
#
# ⚠️ O controle NÃO roda o portão inteiro. Rodar com a trava desligada custaria os
# 5-9 minutos que a própria trava existe para denunciar, e esta suíte roda na
# esteira de todo push — o remédio ficaria mais caro que a doença. O que se mede
# aqui é a MECÂNICA do prazo, extraída do arquivo e exercitada isolada: é o mesmo
# recurso do `test_motor_bancada.py`, que roda o laço do motor num harness em vez
# de disparar a missão de verdade.
HARNESS=$(mktemp)
# Extrai do portão real o bloco do prazo (da declaração do início até a chave que
# fecha a função). Extrair em vez de reescrever é o que faz o teste medir o
# arquivo que roda em produção, e não uma cópia que envelhece à parte.
sed -n '/^PORTAO_INICIO=\$SECONDS/,/^}$/p' "$PORTAO" > "$HARNESS"
BLOCO_LINHAS=$(wc -l < "$HARNESS" | tr -d ' ')
check "o bloco do prazo foi extraído do portão de verdade" \
      "$([ "$BLOCO_LINHAS" -gt 10 ] && echo 1 || echo 0)" "linhas extraídas: $BLOCO_LINHAS"

# a) Prazo LONGO: dois checkpoints seguidos passam sem recusar.
SAIDA0=$(cd "$RAIZ" && PORTAO_DEADLINE_S=9999 bash -c "
  $(cat "$HARNESS")
  portao_prazo 'primeiro'
  portao_prazo 'segundo'
  echo CHEGOU-AO-FIM" 2>&1)
case "$SAIDA0" in
  *CHEGOU-AO-FIM*) check "dentro do prazo, os checkpoints não recusam nada" 1 ;;
  *) check "dentro do prazo, os checkpoints não recusam nada" 0 "${SAIDA0:0:200}" ;;
esac

# b) Trava DESLIGADA (0): idem — é o escape declarado, e ele tem que funcionar.
SAIDA1=$(cd "$RAIZ" && PORTAO_DEADLINE_S=0 bash -c "
  $(cat "$HARNESS")
  portao_prazo 'primeiro'
  echo CHEGOU-AO-FIM" 2>&1)
case "$SAIDA1" in
  *CHEGOU-AO-FIM*) check "com a trava desligada (0) nada é recusado por prazo" 1 ;;
  *) check "com a trava desligada (0) nada é recusado por prazo" 0 "${SAIDA1:0:200}" ;;
esac
rm -f "$HARNESS"

echo
echo "F17.5 — o medidor dos medidores: o deadline cabe no teto do hook"

# Estático e barato: lê os dois números e compara. Não roda o portão.
LEITURA=$(python3 - "$RAIZ" <<'PY'
import json, os, re, sys
raiz = sys.argv[1]
teto = 0
try:
    d = json.load(open(os.path.join(raiz, ".claude", "settings.json"), encoding="utf-8"))
    for grupo in d.get("hooks", {}).get("PreToolUse", []):
        for h in grupo.get("hooks", []):
            if "release-gate" in h.get("command", ""):
                teto = int(h.get("timeout", 0))
except Exception:
    pass
texto = open(os.path.join(raiz, ".claude", "hooks", "release-gate.sh"), encoding="utf-8").read()
m = re.search(r"PORTAO_MARGEM=\$\{PORTAO_MARGEM_S:-(\d+)\}", texto)
margem = int(m.group(1)) if m else -1
print("%d %d" % (teto, margem))
PY
)
TETO=${LEITURA% *}; MARGEM=${LEITURA#* }
check "o teto do hook é legível no settings.json" "$([ "$TETO" -gt 0 ] && echo 1 || echo 0)" "teto=$TETO"
check "o portão declara a margem" "$([ "$MARGEM" -ge 0 ] && echo 1 || echo 0)" "margem=$MARGEM"
# O deadline derivado (teto − margem) tem que ser positivo E menor que o teto:
# margem maior que o teto zeraria o deadline, e deadline zero é a trava DESLIGADA
# — o portão voltaria a morrer calado sem ninguém perceber.
check "o deadline derivado cabe no teto e não é zero" \
      "$([ "$MARGEM" -lt "$TETO" ] && [ $((TETO - MARGEM)) -gt 0 ] && echo 1 || echo 0)" \
      "teto=$TETO margem=$MARGEM → deadline=$((TETO - MARGEM))"

printf '\nrelease-gate-prazo: %d ok, %d falhas\n' "$ok" "$falhas"
[ "$falhas" -eq 0 ]
