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
# handoff+project-doc; a tabela R8 vai pro references/ do sovai+qa-loop.
SPECS=(
  "plugins/handoff/lib::collect_engine.py"
  "plugins/project-doc/lib::collect_engine.py"
  # O contrato R8: os DADOS (.json) + o servidor (.py) + a vista humana (.md, gerada
  # do json). A skill instalada só enxerga a própria pasta, então a casca lê o tier
  # da cópia local e passa em args — nenhum SKILL.md carimba o valor.
  "plugins/sovai/skills/sovai/references::r8-tiers.json"
  "plugins/qa-loop/skills/qa-loop/references::r8-tiers.json"
  "plugins/sovai/skills/sovai/references::r8_tiers.py"
  "plugins/qa-loop/skills/qa-loop/references::r8_tiers.py"
  "plugins/sovai/skills/sovai/references::r8-tiers.md"
  "plugins/qa-loop/skills/qa-loop/references::r8-tiers.md"
  # Os cinco antipadrões de teste: a mesma lista serve quem REVISA o construído
  # (/qa-loop) e quem escreve o critério de pronto no plano (/visual). Contrato
  # único — nenhum dos dois SKILL.md repete o texto, os dois apontam pra cópia.
  "plugins/qa-loop/skills/qa-loop/references::antipadroes-de-teste.md"
  "plugins/visual/skills/visual/references::antipadroes-de-teste.md"
  # A régua de POR ONDE a pergunta chega: nasceu dentro do /grill-me e vale pra toda
  # skill que pergunta ao dono. Cada SKILL.md consumidor só aponta pra cópia local —
  # o texto mora aqui. Quem cobra: _shared/test_regua_de_pergunta.py.
  "plugins/grill-me/skills/grill-me::regua-de-pergunta.md"
  "plugins/project-doc/skills/start-doc::regua-de-pergunta.md"
  "plugins/handoff/skills/handoff::regua-de-pergunta.md"
  "plugins/lixeiro/skills/faxina::regua-de-pergunta.md"
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
  # Os emissores de hook: o .sh chama a régua pela linha de comando, e o plugin
  # instalado só enxerga a própria pasta — sem cópia aqui, a régua some em produção.
  "plugins/bootstrap/lib::regua_texto.py"
  "plugins/guardrails/lib::regua_texto.py"
  "plugins/project-doc/lib::regua_texto.py"
  "plugins/ship/lib::regua_texto.py"
  "plugins/graphify-guard/lib::regua_texto.py"
  # O resolvedor de diretório de artefato: cada skill que ESCREVE arquivo no projeto
  # do usuário resolve o destino por aqui, com o próprio subdiretório. Vendorado
  # porque o plugin instalado só enxerga a própria pasta.
  "plugins/visual/skills/visual::resolve-dir.sh"
  "plugins/archify/skills/archify::resolve-dir.sh"
  # O resolvedor de plugin IRMÃO por nome: quem precisa de um arquivo de outro plugin
  # pergunta por nome em vez de apontar `../<irmão>/`, que só resolve rodando do
  # repositório. A cópia mora ao lado da skill que a chama, porque o plugin instalado
  # só enxerga a própria pasta.
  "plugins/sovai/skills/sovai::resolve-plugin.sh"
  "plugins/qa-loop/skills/qa-loop::resolve-plugin.sh"
  "plugins/project-doc/skills/start-doc::resolve-plugin.sh"
  "plugins/ship/hooks::green-cache.sh"
  "plugins/qa-loop/lib::green-cache.sh"
  # O leitor de JSON dos hooks: todo hook que DECIDE lendo o payload do evento
  # sourceia a cópia da própria pasta (o plugin instalado não enxerga a de fora).
  "plugins/bootstrap/hooks::hook-json.sh"
  "plugins/branches/hooks::hook-json.sh"
  "plugins/context-guard/hooks::hook-json.sh"
  "plugins/graphify-guard/hooks::hook-json.sh"
  "plugins/guardrails/hooks::hook-json.sh"
  "plugins/intent-guard/hooks::hook-json.sh"
  "plugins/lixeiro/hooks::hook-json.sh"
  "plugins/project-doc/hooks::hook-json.sh"
  "plugins/ship/hooks::hook-json.sh"
  "plugins/sovai/hooks::hook-json.sh"
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
  "plugins/project-doc/hooks::lib-tmpdir.sh"
  "plugins/ship/hooks::lib-tmpdir.sh"
  "plugins/sovai/hooks::lib-tmpdir.sh"
  "plugins/visual/hooks::lib-tmpdir.sh"
  # O green-cache do qa-loop mora em lib/, não em hooks/ — a cópia acompanha ele.
  "plugins/qa-loop/lib::lib-tmpdir.sh"
  # O aviso de dependência ausente: quem instala UM plugin sozinho também precisa
  # saber que o gate dele ficou mudo, então o hook viaja com todo plugin que tem
  # hooks — não só com o bootstrap. Um sentinel por sessão evita o aviso repetido.
  "plugins/bootstrap/hooks::sessionstart-deps.sh"
  "plugins/branches/hooks::sessionstart-deps.sh"
  "plugins/context-guard/hooks::sessionstart-deps.sh"
  "plugins/graphify-guard/hooks::sessionstart-deps.sh"
  "plugins/guardrails/hooks::sessionstart-deps.sh"
  "plugins/handoff/hooks::sessionstart-deps.sh"
  "plugins/intent-guard/hooks::sessionstart-deps.sh"
  "plugins/lixeiro/hooks::sessionstart-deps.sh"
  "plugins/project-doc/hooks::sessionstart-deps.sh"
  "plugins/ship/hooks::sessionstart-deps.sh"
  "plugins/sovai/hooks::sessionstart-deps.sh"
  "plugins/visual/hooks::sessionstart-deps.sh"
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
