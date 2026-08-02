#!/bin/bash
# test_sovai_skill.sh — suíte do CONTRATO do revisor #2 na SKILL.md do sovai.
#
# O defeito que isto impede: o #2 revisava contra a decomposição do #1, que é a
# obra do próprio motor — circuito fechado, onde quem decompõe errado é aprovado
# errado. A suíte cobra as quatro afirmações que fecham esse circuito: a spec
# chega ao revisor, o BUILD_REVIEW carrega o gap de spec, a constituição do
# projeto (quality-goals.md) é lida, e o eixo requisito/pronto existe.
#
# Anti-tautologia: a verificação ACEITA O CAMINHO DO ARQUIVO como argumento. Com
# isso a suíte copia a SKILL.md pro TMPDIR, apaga a linha que carrega cada
# afirmação, roda a verificação contra a cópia e EXIGE reprovação. Sem o
# argumento não haveria como sabotar, e o teste provaria só que ele mesmo roda.
#
#   bash plugins/sovai/hooks/test_sovai_skill.sh              # tudo
#   bash plugins/sovai/hooks/test_sovai_skill.sh <SKILL.md>   # só as asserções

SKILL_PADRAO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../skills/sovai" && pwd)/SKILL.md"
ALVO="${1:-$SKILL_PADRAO}"

if [ ! -f "$ALVO" ]; then
  echo "  FALHA arquivo inexistente: $ALVO" >&2
  exit 1
fi

OK=0
FALHA=0

check() { # nome, 1|0
  if [ "$2" = "1" ]; then
    OK=$((OK + 1)); echo "  ok   $1"
  else
    FALHA=$((FALHA + 1)); echo "  FALHA $1"
  fi
}

secao() { # arquivo, marcador de início, marcador de fim (literais)
  awk -v ini="$2" -v fim="$3" '
    !dentro && index($0, ini) { dentro = 1 }
    dentro && !index($0, ini) && index($0, fim) { exit }
    dentro { print }
  ' "$1"
}

tem() { # conteúdo, agulha literal
  printf '%s' "$1" | grep -qF -- "$2" && echo 1 || echo 0
}

# Nomes dos checks que cada sabotagem tem que derrubar — os mesmos strings entram
# na asserção e na sabotagem, senão o par se desencontra em silêncio.
N_JULGA_SPEC="o #2 julga contra a spec"
N_PROMPT_SPEC="o motor passa a spec no prompt do revisor"
N_FILTRO_SPEC="o script segura o gap de spec no filtro"
N_KIND_SPEC="o schema declara o kind 'spec'"
N_DECOMP_CAMPOS="a tarefa carrega requisito e pronto"

REVISOR="$(secao "$ALVO" '- **OPUS #2 — Revisor de construção.**' '- **DIAGNÓSTICO')"
SKEL="$(secao "$ALVO" '// args (da casca)' '**Schemas (JSON Schema')"
DECOMP="$(secao "$ALVO" '- `DECOMP` —' '- `TASK_RESULT`')"
REVIEW="$(secao "$ALVO" '- `BUILD_REVIEW` —' 'O `stopReason`')"

echo "[contrato do revisor #2 — $ALVO]"

echo "1 · a spec chega ao revisor"
check "o papel do #2 existe" "$([ -n "$REVISOR" ] && echo 1 || echo 0)"
check "$N_JULGA_SPEC" "$(tem "$REVISOR" 'contra a spec')"
check "a spec chega ao #2 pelo planPath/planText" "$(tem "$REVISOR" '`planPath`/`planText`')"
check "a decomposição do #1 deixa de ser a fonte da verdade" \
  "$(tem "$REVISOR" 'não fonte da verdade')"
check "$N_PROMPT_SPEC" "$(tem "$SKEL" 'reviewBuildPrompt({ planPath: args.planPath')"
check "o confirm-pass também recebe a spec" \
  "$(tem "$SKEL" 'confirmBuildPrompt({ planPath: args.planPath')"

echo "2 · o BUILD_REVIEW carrega o gap de spec"
check "o schema BUILD_REVIEW existe" "$([ -n "$REVIEW" ] && echo 1 || echo 0)"
check "$N_KIND_SPEC" "$(tem "$REVIEW" "kind: 'spec'")"
check "o gap de spec vale mesmo com a decomposição cumprida" \
  "$(tem "$REVIEW" 'mesmo com a decomposição cumprida')"
check "o gap de spec nasce >= severityFloor" "$(tem "$REVIEW" 'severityFloor')"
check "$N_FILTRO_SPEC" "$(tem "$SKEL" "g.kind === 'spec'")"

echo "3 · a constituição do projeto é citada"
check "o #2 lê o quality-goals.md do projeto" \
  "$(tem "$REVISOR" '.claude/docs/quality-goals.md')"
check "a régua nunca é copiada pra dentro da skill" \
  "$(tem "$REVISOR" 'nunca copiado para dentro desta skill')"
check "projeto sem o arquivo não vira gap (fail-open)" \
  "$(tem "$REVISOR" 'ausência de constituição não é gap')"
check "o schema declara o kind 'constituicao'" "$(tem "$REVIEW" "'constituicao'")"
check "o motor manda ler o arquivo na rodada" "$(tem "$SKEL" 'quality-goals.md')"

echo "4 · o eixo requisito/pronto"
check "o schema DECOMP existe" "$([ -n "$DECOMP" ] && echo 1 || echo 0)"
check "$N_DECOMP_CAMPOS" "$(tem "$DECOMP" 'requisito, pronto')"
check "os dois campos são obrigatórios" "$(tem "$DECOMP" 'são obrigatórios')"
check "os dois saem copiados da spec" "$(tem "$DECOMP" 'copiados da spec')"
check "o schema BUILD_REVIEW tem o kind 'rastreio'" "$(tem "$REVIEW" "'rastreio'")"
check "o #2 reprova tarefa sem os dois campos" \
  "$(tem "$REVISOR" 'sem `requisito` ou sem `pronto`')"
check "o script segura o gap de rastreio no filtro" "$(tem "$SKEL" "g.kind === 'rastreio'")"

# Com argumento a suíte é só a verificação — é assim que a sabotagem a chama.
if [ -n "$1" ]; then
  echo
  if [ "$FALHA" -eq 0 ]; then echo "OK ($OK checks)"; exit 0; fi
  echo "FALHOU ($FALHA de $((OK + FALHA)))"
  exit 1
fi

echo "5 · sabotagem: tirar a linha que carrega a afirmação deixa a suíte vermelha"

TMP="$(mktemp -d)"
if [ -z "$TMP" ] || [ ! -d "$TMP" ]; then
  echo "  FALHA mktemp -d falhou — sem raiz temporária não há sabotagem" >&2
  exit 1
fi
trap 'rm -rf "${TMP:?}"' EXIT

sabota() { # rótulo, agulha da linha a remover, nome do check que tem que reprovar
  local copia="$TMP/sabotado.md" saida rc
  grep -vF -- "$2" "$ALVO" > "$copia"
  if [ "$(wc -l < "$copia")" -eq "$(wc -l < "$ALVO")" ]; then
    check "sabotagem [$1] removeu a linha alvo" "0"
    return
  fi
  check "sabotagem [$1] removeu a linha alvo" "1"
  saida="$(bash "${BASH_SOURCE[0]}" "$copia" 2>&1)"; rc=$?
  check "sabotagem [$1] deixa a suíte vermelha" "$([ "$rc" -ne 0 ] && echo 1 || echo 0)"
  check "sabotagem [$1] reprova '$3'" \
    "$(printf '%s' "$saida" | grep -qF "FALHA $3" && echo 1 || echo 0)"
}

sabota "papel do #2"        '- **OPUS #2 — Revisor de construção.**'   "$N_JULGA_SPEC"
sabota "spec no prompt"     'reviewBuildPrompt({ planPath: args.planPath' "$N_PROMPT_SPEC"
sabota "filtro do script"   'const holdsBuild ='                       "$N_FILTRO_SPEC"
sabota "schema BUILD_REVIEW" '- `BUILD_REVIEW` —'                      "$N_KIND_SPEC"
sabota "schema DECOMP"      '- `DECOMP` —'                             "$N_DECOMP_CAMPOS"

echo
if [ "$FALHA" -eq 0 ]; then
  echo "OK ($OK checks)"
  exit 0
fi
echo "FALHOU ($FALHA de $((OK + FALHA)))"
exit 1
