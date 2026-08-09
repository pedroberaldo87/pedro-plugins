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
#   bash plugins/project-skills/hooks/test_sovai_skill.sh              # tudo
#   bash plugins/project-skills/hooks/test_sovai_skill.sh <SKILL.md>   # só as asserções

SKILL_PADRAO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../skills/sprint" && pwd)/SKILL.md"  # acopla-ok: teste roda no monorepo, não na máquina de quem instala
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
N_LEI_CAMINHO="o #2 lê a lei no caminho que a concepção produz"
N_LEI_MARCA="o motor congela a marca da lei na 1ª volta"
N_LEI_AVISO="lei trocada no meio da missão vira aviso, nunca troca calada"
N_CONCEP_KIND="o schema declara o kind 'concepcao'"
N_CONCEP_AVISO="o script manda o gap de concepção pro relatório"

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
check "$N_PROMPT_SPEC" "$(tem "$SKEL" 'reviewBuildPrompt({ planPath: ARGS.planPath')"
check "o confirm-pass também recebe a spec" \
  "$(tem "$SKEL" 'confirmBuildPrompt({ planPath: ARGS.planPath')"

echo "2 · o BUILD_REVIEW carrega o gap de spec"
check "o schema BUILD_REVIEW existe" "$([ -n "$REVIEW" ] && echo 1 || echo 0)"
check "$N_KIND_SPEC" "$(tem "$REVIEW" "kind: 'spec'")"
check "o gap de spec vale mesmo com a decomposição cumprida" \
  "$(tem "$REVIEW" 'mesmo com a decomposição cumprida')"
check "o gap de spec nasce >= severityFloor" "$(tem "$REVIEW" 'severityFloor')"
check "$N_FILTRO_SPEC" "$(tem "$SKEL" "g.kind === 'spec'")"

echo "3 · a constituição do projeto é citada"
check "$N_LEI_CAMINHO" \
  "$(tem "$REVISOR" '.claude/docs/constituicao.md')"
check "o #2 lê o quality-goals.md do projeto" \
  "$(tem "$REVISOR" '.claude/docs/quality-goals.md')"
check "a régua nunca é copiada pra dentro da skill" \
  "$(tem "$REVISOR" 'nunca copiado para dentro desta skill')"
check "projeto sem o arquivo não vira gap (fail-open)" \
  "$(tem "$REVISOR" 'ausência de constituição não é gap')"
check "o schema declara o kind 'constituicao'" "$(tem "$REVIEW" "'constituicao'")"
check "o motor manda ler o arquivo na rodada" "$(tem "$SKEL" 'quality-goals.md')"
check "o #2 mede a obra contra o esquema aprovado" \
  "$(tem "$REVISOR" '.claude/docs/blueprint.md')"
check "o #2 mede a obra contra a lista de funcionalidades aprovada" \
  "$(tem "$REVISOR" '.claude/docs/features.md')"
check "o desenho só entra quando está aprovado" \
  "$(tem "$REVISOR" 'status: approved')"

echo "4 · o eixo requisito/pronto"
check "o schema DECOMP existe" "$([ -n "$DECOMP" ] && echo 1 || echo 0)"
check "$N_DECOMP_CAMPOS" "$(tem "$DECOMP" 'requisito, pronto')"
check "os dois campos são obrigatórios" "$(tem "$DECOMP" 'são obrigatórios')"
check "os dois saem copiados da spec" "$(tem "$DECOMP" 'copiados da spec')"
check "o schema BUILD_REVIEW tem o kind 'rastreio'" "$(tem "$REVIEW" "'rastreio'")"
check "o #2 reprova tarefa sem os dois campos" \
  "$(tem "$REVISOR" 'sem `requisito` ou sem `pronto`')"
check "o script segura o gap de rastreio no filtro" "$(tem "$SKEL" "g.kind === 'rastreio'")"

echo "5 · a marca da lei é congelada no começo da missão"
check "o schema BUILD_REVIEW devolve a marca da lei" "$(tem "$REVIEW" 'lawMark')"
check "a marca é do corpo do arquivo lido na rodada" \
  "$(tem "$REVIEW" 'cksum')"
check "$N_LEI_MARCA" "$(tem "$SKEL" 'lawMark = review.lawMark')"
check "$N_LEI_AVISO" "$(tem "$SKEL" 'a lei do projeto mudou durante a missão')"
check "a marca fixada chega ao revisor das rodadas seguintes" \
  "$(tem "$SKEL" 'lawMark })')"
check "o #2 mede contra a marca fixada, não contra o texto novo" \
  "$(tem "$REVISOR" 'marca da lei')"

echo "6 · a execução avisa que a entrevista errou, sem mexer no documento"
check "o #2 sinaliza a concepção contradita pelo que saiu" \
  "$(tem "$REVISOR" 'a concepção está errada')"
check "o aviso propõe reabrir a etapa" "$(tem "$REVISOR" 'reabrir a etapa')"
check "o aviso indica a linha correcao-pendente, que quem grava é o dono" \
  "$(tem "$REVISOR" 'correcao-pendente:')"
check "o revisor nunca reescreve o documento aprovado" \
  "$(tem "$REVISOR" 'nunca reescreve documento')"
check "$N_CONCEP_KIND" "$(tem "$REVIEW" "'concepcao'")"
check "o gap de concepção não segura a obra (não há o que consertar no código)" \
  "$(tem "$REVIEW" 'não segura a obra')"
check "$N_CONCEP_AVISO" "$(tem "$SKEL" "kind === 'concepcao')")"

# Com argumento a suíte é só a verificação — é assim que a sabotagem a chama.
if [ -n "$1" ]; then
  echo
  if [ "$FALHA" -eq 0 ]; then echo "OK ($OK checks)"; exit 0; fi
  echo "FALHOU ($FALHA de $((OK + FALHA)))"
  exit 1
fi

echo "7 · sabotagem: tirar a linha que carrega a afirmação deixa a suíte vermelha"

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
sabota "spec no prompt"     'reviewBuildPrompt({ planPath: ARGS.planPath' "$N_PROMPT_SPEC"
sabota "filtro do script"   'const holdsBuild ='                       "$N_FILTRO_SPEC"
sabota "schema BUILD_REVIEW" '- `BUILD_REVIEW` —'                      "$N_KIND_SPEC"
sabota "schema DECOMP"      '- `DECOMP` —'                             "$N_DECOMP_CAMPOS"
sabota "pino da marca da lei" 'lawMark = review.lawMark'               "$N_LEI_MARCA"
sabota "aviso da lei trocada" 'a lei do projeto mudou durante a missão' "$N_LEI_AVISO"
sabota "aviso da concepção errada" "kind === 'concepcao'))"           "$N_CONCEP_AVISO"

echo
if [ "$FALHA" -eq 0 ]; then
  echo "OK ($OK checks)"
  exit 0
fi
echo "FALHOU ($FALHA de $((OK + FALHA)))"
exit 1
