#!/usr/bin/env bash
# suite.sh — A ESTEIRA DESTE REPOSITÓRIO, EM UM LUGAR SÓ.
#
# Por que este arquivo existe (F17.3): a seleção completa das suítes morava
# DENTRO de `.github/workflows/portability.yml` e em mais nenhum lugar. Quem
# precisava rodar a esteira fora do CI — uma pessoa no terminal, a casca do
# `/sprint` montando o `suiteCmd` do motor — tinha que reconstruir os nove globs
# de cabeça. Em 2026-08-13 a casca não reconstruiu: passou `python3
# scripts/run_suites.py` pelado ao motor, que rodou ZERO suítes, declarou a
# corrida verde e queimou 87 minutos sem marcar um passo.
#
# A régua da casa é a mesma do vendoring e do catálogo: um fato, uma fonte. Aqui
# a fonte é este arquivo; o `portability.yml` o invoca, o CLAUDE.md o aponta, e o
# motor o recebe como `suiteCmd`.
#
#   bash scripts/suite.sh                  # a esteira inteira
#   bash scripts/suite.sh --timeout 120    # argumentos extras vão para o rodador
#   bash scripts/suite.sh --flake          # cobrador de paralelismo: a mesma seleção
#                                          # duas vezes ao mesmo tempo, reprovando só
#                                          # quem muda de veredito entre as duas
#
# Rodada FILTRADA (diagnóstico) não é assunto deste arquivo: ela se faz chamando
# `scripts/run_suites.py` direto com os globs do recorte, e não vale como esteira
# verde — dizer o contrário seria a mesma mentira do glob vazio.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

PY="${PYTHON:-python3}"

# SEM TETO DE RELÓGIO: VIGIA DE PROGRESSO. O teto fixo media a MÁQUINA, não o
# código — `scripts/test_docguard_scope.sh` levava 349s sozinha e estourava 300s com
# a máquina ocupada, e três largadas do /sprint morreram por suíte que só estava
# lenta. Quem decide agora é o `run_suites.py`: a cada janela ele pergunta se a suíte
# ainda anda (CPU na árvore dela, medida por `_shared/vivo-ou-dormindo.sh`, ou saída
# crescendo), e só mata quem fica parada nos dois sinais. Suíte lenta e saudável
# roda até o fim; suíte pendurada morre em minutos, com nome. A janela default
# (120s) vale — subir número aqui era o remendo que o vigia veio substituir.
# ── UMA FASE SÓ: NÃO HÁ MAIS SUÍTE QUE DISPUTE ESTADO ───────────────────────
#
# Até 2026-08-20 as suítes do `intent-guard` rodavam em SÉRIE, numa segunda fase,
# porque exercitam hooks que gravam estado por sessão no temporário do sistema com
# ids CRAVADOS no código (`dasid`, `cksid`, `pgsid`…). Serializar era remendo, e o
# próprio cabeçalho de então já dizia por quê: a colisão é da CHAVE, não da ordem —
# duas esteiras de pé (duas sessões de agente no mesmo repositório, ou o CI ao lado
# do terminal) continuavam pisando uma na outra, e a suíte acusada mudava a cada
# rodada. A medição de 2026-08-20 (três esteiras ao mesmo tempo) mostrou as três
# seriais caindo assim, cada rodada numa asserção diferente.
#
# A causa foi consertada onde ela nasce: o rodador dá a CADA suíte um temporário
# próprio (`scripts/run_suites.py:roda`, `TMPDIR`/`TMP`/`TEMP`), e com casa própria
# o id fixo deixa de importar. Sem disputa, não há o que serializar — a lista
# encolheu a zero e a segunda fase saiu junto. Se um dia voltar a existir suíte que
# dispute recurso compartilhado, o `SUITE_PULA` do rodador continua de pé para
# tirá-la da fase paralela; o que não volta é esconder disputa em ordem de execução.

# O RETRATO DA ÁRVORE ANTES DE MEDIR. A prova do fim vale para o estado que foi
# MEDIDO, não para o que estiver no disco quando a última suíte terminar — e as duas
# coisas divergem sempre que alguém edita durante a rodada (outra sessão trabalhando
# no mesmo repositório, ou o próprio motor entre uma onda e outra). Sem este retrato,
# uma edição no meio da esteira faria a prova ser gravada para uma árvore que nunca
# rodou inteira: verde emprestado, que é a doença que esta mesma esteira existe para
# matar. Falha em ler o hash ⇒ fica vazio ⇒ a comparação do fim não bate ⇒ não grava.
ARVORE_ANTES=""
if [ -f "$RAIZ/_shared/green-cache.sh" ]; then
  . "$RAIZ/_shared/green-cache.sh" 2>/dev/null || true
  type green_tree_hash >/dev/null 2>&1 && ARVORE_ANTES=$(green_tree_hash "$RAIZ" 2>/dev/null || true)
fi

RC=0
"$PY" scripts/run_suites.py "$@" \
  --py 'plugins/*/lib/test_*.py' \
       '_shared/test_*.py' \
       'scripts/test_*.py' \
       'plugins/*/hooks/test_*.py' \
  --sh 'plugins/*/hooks/test_*.sh' \
       'plugins/*/lib/test_*.sh' \
       'scripts/test_*.sh' \
       '.claude/hooks/test_*.sh' \
       'plugins/*/skills/*/test_*.sh' || RC=$?

# ── A PROVA VIAJA COM A ÁRVORE ──────────────────────────────────────────────
# Esteira verde ⇒ grava "full" no green-cache (chave = tree-hash
# da árvore inteira, untracked incluso). É esta prova que o gate de commit
# consome para não re-medir o que a esteira acabou de medir — sem ela o portão
# re-rodava tudo a cada commit (medido em 2026-08-14: 20min nesta máquina, 1084s
# só de scripts/test_docguard_scope.sh, e o canal de quem commita morria antes
# do veredito). Um fato, uma fonte: só a esteira INTEIRA grava "full" — rodada
# filtrada chama run_suites.py direto, não passa por aqui, e por isso não vira
# prova (mesma régua do cabeçalho). Vermelho nunca grava; erro no cache não
# muda o RC — a prova é atalho do portão, o veredito é da esteira.
#
# E a árvore tem que ser A MESMA do começo ao fim: se ela mudou no meio, o que a
# esteira mediu não é o que está no disco agora, e gravar seria emprestar verde a
# código que ninguém rodou. Nesse caso não grava e DIZ que não gravou — medidor que
# não pôde medir avisa, nunca cala (Art. 4).
# `--flake` NÃO grava prova: lá o veredito verde significa "nenhuma suíte instável",
# e não "a esteira passou" — suíte que falha nas duas rodadas sai zero. Emprestar
# verde a partir dele seria a mesma mentira do glob vazio.
if [ "$RC" -eq 0 ] && [[ " $* " != *" --flake "* ]] && [ -f "$RAIZ/_shared/green-cache.sh" ]; then
  . "$RAIZ/_shared/green-cache.sh" 2>/dev/null || true
  if type green_cache_mark >/dev/null 2>&1; then
    ARVORE_DEPOIS=$(green_tree_hash "$RAIZ" 2>/dev/null || true)
    if [ -n "$ARVORE_ANTES" ] && [ "$ARVORE_ANTES" = "$ARVORE_DEPOIS" ]; then
      green_cache_mark "$RAIZ" full suite.sh >/dev/null 2>&1 || true
      echo "prova da esteira gravada para a árvore ${ARVORE_ANTES%"${ARVORE_ANTES#???????}"}"
    else
      echo "esteira verde, mas a ÁRVORE MUDOU durante a rodada — prova NÃO gravada"
      echo "  (o que foi medido não é o que está no disco; rode de novo com a árvore parada)"
    fi
  fi
fi

exit $RC
