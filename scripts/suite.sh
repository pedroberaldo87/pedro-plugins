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
#
# Rodada FILTRADA (diagnóstico) não é assunto deste arquivo: ela se faz chamando
# `scripts/run_suites.py` direto com os globs do recorte, e não vale como esteira
# verde — dizer o contrário seria a mesma mentira do glob vazio.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

PY="${PYTHON:-python3}"

# TETO POR SUÍTE: 600s, não 300s. Medido em 2026-08-14 sob carga real (o motor do
# /sprint rodando junto): `scripts/test_docguard_scope.sh` leva 349s SOZINHA nesta
# máquina, e `plugins/project-skills/hooks/test_plan_hooks.sh` leva 109s livre mas
# estourou 300s com a máquina ocupada. As duas saíam como TIMEOUT, a esteira ficava
# vermelha, e a guarda de saúde do motor fechava a porta — três largadas seguidas.
#
# Teto que a suíte mais lenta não alcança é teto que mede a MÁQUINA, não o código:
# na máquina livre ele passa, na ocupada ele reprova, e o veredito vira sorteio. O
# número aqui é o dobro da suíte mais lenta medida — quando alguma passar disso, o
# certo é acelerar a suíte, não subir o teto de novo em silêncio.
# ── DUAS FASES: o grosso em paralelo, e o punhado que DISPUTA ESTADO em série ──
#
# As suítes do `intent-guard` exercitam hooks que gravam estado por sessão em
# `$TMPDIR` e leem o ledger do repositório — com ids de sessão fixos. Rodando ao
# mesmo tempo, uma pisa na outra: medido em 2026-08-14, em série passam sempre, em
# paralelo caem ora uma, ora outra, ora nenhuma. Seis camadas de isolamento já
# entraram (lar fingido, mock do juiz, limpeza antes e depois, artefato fora do
# tree-hash, teto de git de 60s), e ainda sobrava disputa.
#
# ⚠️ Isto NÃO é lista de teste ignorado: elas rodam, inteiras, e reprovam a esteira
# se falharem. O que muda é o COMO — recurso compartilhado se serializa, não se
# sorteia. O dia em que elas ficarem independentes de verdade, esta lista encolhe;
# enquanto não ficarem, o veredito delas é honesto em vez de aleatório. A frente
# que as torna independentes é a fase F19 do plano.
# A lista das seriais é UMA linha, e o resto se deduz dela: o glob de hooks segue
# sendo `plugins/*/hooks/test_*.sh` e o rodador simplesmente PULA quem está aqui.
# Enumerar plugin a plugin, que foi a primeira tentativa, cria globo vazio a cada
# plugin sem suíte de hook (o `handoff` é um) — e globo vazio reprova, com razão.
SERIAIS='plugins/intent-guard/hooks/test_*.sh'

RC=0
SUITE_PULA="$SERIAIS" "$PY" scripts/run_suites.py --timeout 600 "$@" \
  --py 'plugins/*/lib/test_*.py' \
       '_shared/test_*.py' \
       'scripts/test_*.py' \
       'plugins/*/hooks/test_*.py' \
  --sh 'plugins/*/hooks/test_*.sh' \
       'plugins/*/lib/test_*.sh' \
       'scripts/test_*.sh' \
       '.claude/hooks/test_*.sh' \
       'plugins/*/skills/*/test_*.sh' || RC=$?

echo
echo "── as que disputam estado, agora em SÉRIE ──────────────────────────────"
"$PY" scripts/run_suites.py --timeout 600 --jobs 1 --sh "$SERIAIS" || RC=$?

exit $RC
