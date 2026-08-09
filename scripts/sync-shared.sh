#!/usr/bin/env bash
# sync-shared.sh — vendora _shared/ para dentro de cada plugin consumidor.
#
# Por que vendoring e não import em runtime: o Claude Code isola plugins na
# instalação — só plugins/<nome>/ vai pro cache, sem variável cross-plugin. O
# código compartilhado é COPIADO antes do commit (o "build" deste monorepo).
# Fonte-da-verdade = _shared/; as cópias nos plugins são derivadas.
#
# Uso:
#   scripts/sync-shared.sh           # vendora (copia _shared/ -> cada plugin)
#   scripts/sync-shared.sh --check   # NÃO copia; falha (exit 1) se houver drift
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/_shared"

# Cada spec é "destino::arquivo" — qual arquivo de _shared/ vai pra qual subpasta.
# Mapa explícito (não "todos os FILES em todos os CONSUMERS") porque consumidores
# diferentes vendoram arquivos diferentes: a engine de coleta vai pro lib/ do
# handoff+project-doc; a tabela R8 vai pro references/ do sprint+qa-loop.
SPECS=(
  "plugins/handoff/lib::collect_engine.py"
  "plugins/project-skills/lib::collect_engine.py"
  # O contrato R8: os DADOS (.json) + o servidor (.py) + a vista humana (.md, gerada
  # do json). A skill instalada só enxerga a própria pasta, então a casca lê o tier
  # da cópia local e passa em args — nenhum SKILL.md carimba o valor.
  "plugins/project-skills/skills/sprint/references::r8-tiers.json"
  "plugins/project-skills/skills/qa-loop/references::r8-tiers.json"
  "plugins/project-skills/skills/sprint/references::r8_tiers.py"
  "plugins/project-skills/skills/qa-loop/references::r8_tiers.py"
  "plugins/project-skills/skills/sprint/references::r8-tiers.md"
  "plugins/project-skills/skills/qa-loop/references::r8-tiers.md"
  # Os cinco antipadrões de teste: a mesma lista serve quem REVISA o construído
  # (/qa-loop) e quem escreve o critério de pronto no plano (/visual). Contrato
  # único — nenhum dos dois SKILL.md repete o texto, os dois apontam pra cópia.
  "plugins/project-skills/skills/qa-loop/references::antipadroes-de-teste.md"
  "plugins/visual/skills/visual/references::antipadroes-de-teste.md"
  # A régua de POR ONDE a pergunta chega: nasceu dentro do /grill-me e vale pra toda
  # skill que pergunta ao dono. Cada SKILL.md consumidor só aponta pra cópia local —
  # o texto mora aqui. Quem cobra: _shared/test_regua_de_pergunta.py.
  "plugins/grill-me/skills/grill-me::regua-de-pergunta.md"
  "plugins/project-skills/skills/start::regua-de-pergunta.md"
  "plugins/handoff/skills/handoff::regua-de-pergunta.md"
  "plugins/lixeiro/skills/faxina::regua-de-pergunta.md"
  "plugins/visual/skills/visual::regua-de-pergunta.md"
  "plugins/project-skills/skills/sprint::regua-de-pergunta.md"
  "plugins/project-skills/skills/qa-loop::regua-de-pergunta.md"
  "plugins/slides/skills/slides::regua-de-pergunta.md"
  "plugins/improve/skills/improve::regua-de-pergunta.md"
  # O contrato da família de skills de documentação: onde cada documento mora,
  # qual frontmatter ele carrega e quem tem direito de escrevê-lo. Quatro
  # consumidores — as duas que ESCREVEM documento e as duas que leem a lei que
  # elas produzem. Quem cobra: scripts/test_contrato_familia.py.
  "plugins/project-skills/skills/start::contrato-familia.md"
  "plugins/project-skills/skills/doc::contrato-familia.md"
  "plugins/project-skills/skills/sprint::contrato-familia.md"
  "plugins/project-skills/skills/qa-loop::contrato-familia.md"
  # Os padrões de disparo que vazam processo. Três consumidores — o cobrador do
  # repositório (scripts/), a quinta lente do /check-skills e a investigação do
  # /lixeiro — e eles JÁ divergiram no dia em que nasceram: um tinha `disown` na
  # lista, outro não. Régua de segurança em três cópias vira três réguas.
  "plugins/check-skills/lib::padroes_vazamento.py"
  "plugins/lixeiro/lib::padroes_vazamento.py"
  "scripts::padroes_vazamento.py"
  "plugins/visual/lib::regua_texto.py"
  "plugins/branches/lib::regua_texto.py"
  "plugins/fallow/lib::regua_texto.py"
  "plugins/slides/lib::regua_texto.py"
  "plugins/vistoria/lib::regua_texto.py"
  # Os emissores de hook: o .sh chama a régua pela linha de comando, e o plugin
  # instalado só enxerga a própria pasta — sem cópia aqui, a régua some em produção.
  "plugins/bootstrap/lib::regua_texto.py"
  "plugins/guardrails/lib::regua_texto.py"
  "plugins/project-skills/lib::regua_texto.py"
  "plugins/ship/lib::regua_texto.py"
  "plugins/graphify-guard/lib::regua_texto.py"
  "plugins/project-skills/lib::regua_texto.py"
  # O resolvedor de diretório de artefato: cada skill que ESCREVE arquivo no projeto
  # do usuário resolve o destino por aqui, com o próprio subdiretório. Vendorado
  # porque o plugin instalado só enxerga a própria pasta.
  "plugins/visual/skills/visual::resolve-dir.sh"
  "plugins/archify/skills/archify::resolve-dir.sh"
  # O programa do plano resolve o diretório dos planos pela mesma cascata, e a
  # cópia mora ao lado dele em lib/ — o plugin instalado só enxerga a própria pasta.
  "plugins/project-skills/lib::resolve-dir.sh"
  # O resolvedor de plugin IRMÃO por nome: quem precisa de um arquivo de outro plugin
  # pergunta por nome em vez de apontar `../<irmão>/`, que só resolve rodando do
  # repositório. A cópia mora ao lado da skill que a chama, porque o plugin instalado
  # só enxerga a própria pasta.
  "plugins/project-skills/skills/sprint::resolve-plugin.sh"
  "plugins/project-skills/skills/qa-loop::resolve-plugin.sh"
  "plugins/project-skills/skills/start::resolve-plugin.sh"
  "plugins/improve-workflow/skills/improve-workflow::resolve-plugin.sh"
  "plugins/project-skills/lib::resolve-plugin.sh"
  "plugins/ship/hooks::green-cache.sh"
  "plugins/project-skills/lib::green-cache.sh"
  # O leitor de JSON dos hooks: todo hook que DECIDE lendo o payload do evento
  # sourceia a cópia da própria pasta (o plugin instalado não enxerga a de fora).
  "plugins/bootstrap/hooks::hook-json.sh"
  "plugins/branches/hooks::hook-json.sh"
  "plugins/context-guard/hooks::hook-json.sh"
  "plugins/graphify-guard/hooks::hook-json.sh"
  "plugins/guardrails/hooks::hook-json.sh"
  "plugins/intent-guard/hooks::hook-json.sh"
  "plugins/lixeiro/hooks::hook-json.sh"
  "plugins/project-skills/hooks::hook-json.sh"
  "plugins/ship/hooks::hook-json.sh"
  "plugins/project-skills/hooks::hook-json.sh"
  "plugins/visual/hooks::hook-json.sh"
  # O resolvedor do diretório temporário: viaja com todo plugin que tem script
  # gravando estado por-sessão fora do projeto. O plugin instalado só enxerga a
  # própria pasta, então a cópia mora ao lado de quem a sourceia.
  "plugins/branches/hooks::lib-tmpdir.sh"
  "plugins/context-guard/hooks::lib-tmpdir.sh"
  "plugins/graphify-guard/hooks::lib-tmpdir.sh"
  "plugins/guardrails/hooks::lib-tmpdir.sh"
  "plugins/handoff/hooks::lib-tmpdir.sh"
  "plugins/intent-guard/hooks::lib-tmpdir.sh"
  "plugins/project-skills/hooks::lib-tmpdir.sh"
  "plugins/ship/hooks::lib-tmpdir.sh"
  "plugins/project-skills/hooks::lib-tmpdir.sh"
  "plugins/visual/hooks::lib-tmpdir.sh"
  # O green-cache do qa-loop mora em lib/, não em hooks/ — a cópia acompanha ele.
  # O aviso de dependência ausente: UMA cópia só, no bootstrap. Os outros doze
  # plugins que avisam acham esta pelo NOME do plugin (resolve-plugin.sh), em vez
  # de carregar treze cópias do mesmo script. Um sentinel por sessão evita o aviso
  # repetido — quem chegar primeiro fala, os outros saem calados.
  "plugins/bootstrap/hooks::sessionstart-deps.sh"
  # E o resolvedor que os leva até ela: este sim viaja com cada um dos doze, porque
  # o plugin instalado só enxerga a própria pasta.
  "plugins/branches/hooks::resolve-plugin.sh"
  "plugins/context-guard/hooks::resolve-plugin.sh"
  "plugins/gauntlet/hooks::resolve-plugin.sh"
  "plugins/graphify-guard/hooks::resolve-plugin.sh"
  "plugins/guardrails/hooks::resolve-plugin.sh"
  "plugins/handoff/hooks::resolve-plugin.sh"
  "plugins/intent-guard/hooks::resolve-plugin.sh"
  "plugins/lixeiro/hooks::resolve-plugin.sh"
  "plugins/project-skills/hooks::resolve-plugin.sh"
  "plugins/ship/hooks::resolve-plugin.sh"
  "plugins/project-skills/hooks::resolve-plugin.sh"
  "plugins/visual/hooks::resolve-plugin.sh"
)

check_mode=0
[[ "${1:-}" == "--check" ]] && check_mode=1

status=0
for spec in "${SPECS[@]}"; do
  dest="${spec%%::*}"
  f="${spec##*::}"
  src="$SRC/$f"
  dst="$ROOT/$dest/$f"
  if [[ ! -f "$src" ]]; then
    echo "ERRO: fonte ausente: _shared/$f" >&2
    exit 2
  fi
  if [[ $check_mode -eq 1 ]]; then
    if ! cmp -s "$src" "$dst"; then
      echo "DRIFT: $dest/$f difere de _shared/$f"
      status=1
    fi
  else
    mkdir -p "$ROOT/$dest"
    cp "$src" "$dst"
    echo "vendored: _shared/$f -> $dest/$f"
  fi
done

if [[ $check_mode -eq 1 ]]; then
  [[ $status -eq 0 ]] && echo "OK: cópias vendored idênticas a _shared/"
else
  echo "OK: vendoring concluído (${#SPECS[@]} cópia(s))."
fi
exit $status
