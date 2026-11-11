# Auditoria dos scripts dos plugins (gerado por lib/script_audit.py — nao edite)

Regra gerada so para o script **citado por skill ou hook** e **sem executar comando, carregar codigo ou usar rede**. Os demais continuam pedindo aprovacao.

Scripts analisados: 112 · liberados: 50 · executam comando/carregam codigo: 38 · usam rede: 2 · ilegiveis: 0

| plugin | script | citado | classe | escreve arquivo | por que |
|---|---|---|---|---|---|
| 2op | `lib/quem_serviu.py` | sim | liberado | não | — |
| archify | `skills/archify/bin/archify.mjs` | sim | executa | sim | child_process; import(`; import(p; spawnSync |
| archify | `skills/archify/grao-de-modulo.py` | sim | executa | não | import subprocess |
| archify | `skills/archify/recipes/scenarios.mjs` | não | executa | não | 'cluster' |
| archify | `skills/archify/renderers/architecture/grid.mjs` | não | puro, nao citado | não | — |
| archify | `skills/archify/renderers/architecture/render-architecture.mjs` | sim | liberado | sim | — |
| archify | `skills/archify/renderers/dataflow/render-dataflow.mjs` | sim | liberado | sim | — |
| archify | `skills/archify/renderers/lifecycle/render-lifecycle.mjs` | sim | liberado | sim | — |
| archify | `skills/archify/renderers/sequence/render-sequence.mjs` | sim | liberado | sim | — |
| archify | `skills/archify/renderers/shared/cli.mjs` | não | puro, nao citado | sim | — |
| archify | `skills/archify/renderers/shared/generated-validators.mjs` | sim | liberado | não | — |
| archify | `skills/archify/renderers/shared/geometry.mjs` | não | puro, nao citado | não | — |
| archify | `skills/archify/renderers/shared/layout-report.mjs` | não | puro, nao citado | não | — |
| archify | `skills/archify/renderers/shared/utils.mjs` | não | puro, nao citado | não | — |
| archify | `skills/archify/renderers/shared/validator.mjs` | sim | liberado | não | — |
| archify | `skills/archify/renderers/workflow/render-workflow.mjs` | sim | liberado | sim | — |
| archify | `skills/archify/scripts/check-render-output.mjs` | sim | liberado | não | — |
| archify | `skills/archify/scripts/generate-validators.mjs` | sim | liberado | sim | — |
| archify | `skills/archify/scripts/render-examples.mjs` | sim | executa | não | child_process |
| bootstrap | `lib/bash_posix.py` | não | executa | sim | import subprocess |
| bootstrap | `lib/cfgjson.py` | sim | executa | sim | lib/script_audit.py: import subprocess |
| bootstrap | `lib/conformance.py` | sim | liberado | sim | — |
| bootstrap | `lib/lar_fingido.py` | não | puro, nao citado | não | — |
| bootstrap | `lib/regua_texto.py` | não | puro, nao citado | não | — |
| branches | `lib/branch_state.py` | sim | executa | sim | import subprocess |
| branches | `lib/regua_texto.py` | sim | liberado | não | — |
| check-skills | `lib/padroes_vazamento.py` | não | puro, nao citado | não | — |
| check-skills | `lib/varredura.py` | sim | executa | não | import subprocess |
| fallow | `lib/audit.py` | sim | executa | não | import subprocess |
| fallow | `lib/regua_texto.py` | não | puro, nao citado | não | — |
| fallow | `lib/report.py` | sim | executa | sim | import subprocess |
| gauntlet | `lib/fecho_check.py` | sim | executa | sim | import subprocess |
| graphify-guard | `lib/regua_texto.py` | sim | liberado | não | — |
| guardrails | `hooks/pretooluse-artefato-regua.py` | sim | executa | não | import importlib |
| guardrails | `lib/askq_lint.py` | sim | liberado | não | — |
| guardrails | `lib/regua_texto.py` | sim | liberado | não | — |
| handoff | `lib/bash_posix.py` | não | executa | sim | import subprocess |
| handoff | `lib/casa_da_doc.py` | não | puro, nao citado | não | — |
| handoff | `lib/collect_engine.py` | não | puro, nao citado | não | — |
| handoff | `lib/extract_ata.py` | sim | liberado | sim | — |
| improve-workflow | `lib/bash_posix.py` | não | executa | sim | import subprocess |
| improve-workflow | `lib/lar_fingido.py` | não | puro, nao citado | não | — |
| improve-workflow | `lib/medidor.py` | sim | liberado | não | — |
| improve-workflow | `lib/plano_saida.py` | sim | executa | sim | import importlib; import subprocess; lib/bash_posix.py: import subprocess |
| improve-workflow | `lib/proposta.py` | sim | liberado | não | — |
| improve-workflow | `lib/registro.py` | sim | liberado | sim | — |
| improve-workflow | `lib/sobras.py` | sim | liberado | não | — |
| intent-guard | `lib/ledger.py` | sim | executa | sim | import subprocess |
| lixeiro | `lib/causa.py` | sim | executa | não | import subprocess |
| lixeiro | `lib/lixeiro.py` | sim | executa | sim | import ctypes; import subprocess |
| lixeiro | `lib/padroes_vazamento.py` | não | puro, nao citado | não | — |
| project-skills | `lib/andamento.py` | sim | liberado | sim | — |
| project-skills | `lib/auditoria_plano.py` | sim | liberado | não | — |
| project-skills | `lib/bash_posix.py` | não | executa | sim | import subprocess |
| project-skills | `lib/caminho_igual.py` | não | puro, nao citado | não | — |
| project-skills | `lib/casa_da_doc.py` | sim | liberado | não | — |
| project-skills | `lib/cobertura.py` | sim | liberado | não | — |
| project-skills | `lib/collect_engine.py` | sim | liberado | não | — |
| project-skills | `lib/completude.py` | sim | executa | sim | lib/plan_state.py: import subprocess; lib/precheck_largada.py: import subprocess; lib/bash_posix.py: import subprocess |
| project-skills | `lib/curadoria_features.py` | sim | liberado | sim | — |
| project-skills | `lib/decisoes_estruturais.py` | sim | liberado | não | — |
| project-skills | `lib/decisoes_seladas.py` | sim | liberado | sim | — |
| project-skills | `lib/doc_lint.py` | sim | executa | sim | import subprocess; lib/pattern_check.py: import subprocess; lib/doc_load.py: import subprocess; lib/organism.py: import subprocess … |
| project-skills | `lib/doc_load.py` | sim | executa | não | import subprocess |
| project-skills | `lib/graph_map.py` | sim | liberado | não | — |
| project-skills | `lib/historico.py` | sim | liberado | sim | — |
| project-skills | `lib/journal.py` | sim | executa | sim | import subprocess |
| project-skills | `lib/lar_fingido.py` | não | puro, nao citado | não | — |
| project-skills | `lib/ledger_corridas.py` | sim | liberado | sim | — |
| project-skills | `lib/orfaos.py` | sim | executa | não | import subprocess |
| project-skills | `lib/organism.py` | sim | executa | não | import subprocess |
| project-skills | `lib/pattern_check.py` | sim | executa | sim | import subprocess; lib/doc_load.py: import subprocess; lib/organism.py: import subprocess; lib/journal.py: import subprocess |
| project-skills | `lib/plan_entrada.py` | sim | liberado | sim | — |
| project-skills | `lib/plan_state.py` | sim | executa | sim | import subprocess; lib/precheck_largada.py: import subprocess; lib/bash_posix.py: import subprocess |
| project-skills | `lib/precheck_largada.py` | sim | executa | sim | import subprocess; lib/plan_state.py: import subprocess; lib/bash_posix.py: import subprocess |
| project-skills | `lib/rastreio_etapas.py` | sim | liberado | não | — |
| project-skills | `lib/regua_pronto.py` | sim | liberado | não | — |
| project-skills | `lib/regua_texto.py` | sim | liberado | não | — |
| project-skills | `lib/retomada.py` | sim | liberado | não | — |
| project-skills | `skills/doc-touch/grao-de-modulo.py` | sim | executa | não | import subprocess |
| project-skills | `skills/qa-loop/references/motor.js` | sim | liberado | não | — |
| project-skills | `skills/qa-loop/references/r8_tiers.py` | sim | liberado | sim | — |
| project-skills | `skills/sprint/references/motor.js` | sim | liberado | não | — |
| project-skills | `skills/sprint/references/r8_tiers.py` | sim | liberado | sim | — |
| sec | `lib/regua_texto.py` | não | puro, nao citado | não | — |
| sec | `lib/sec.py` | sim | executa | sim | import subprocess; import urllib.error; import urllib.request |
| ship | `lib/regua_texto.py` | sim | liberado | não | — |
| slides | `lib/md2deck.py` | sim | liberado | sim | — |
| slides | `lib/regua_texto.py` | não | puro, nao citado | não | — |
| slides | `skills/slides/scripts/check_fidelity.py` | sim | liberado | não | — |
| slides | `skills/slides/scripts/check_provenance.py` | sim | liberado | não | — |
| vision | `vision_mcp.py` | não | rede | não | import urllib.error; import urllib.request |
| vistoria | `fixtures/e/exemplo.py` | não | puro, nao citado | não | — |
| vistoria | `fixtures/e/exemplo_test.py` | não | puro, nao citado | não | — |
| vistoria | `lib/achado.py` | sim | liberado | não | — |
| vistoria | `lib/bash_posix.py` | não | executa | sim | import subprocess |
| vistoria | `lib/fio_morto.py` | sim | liberado | sim | — |
| vistoria | `lib/inventario.py` | sim | liberado | não | — |
| vistoria | `lib/medidor.py` | sim | executa | não | import importlib; import subprocess |
| vistoria | `lib/pagina.py` | sim | liberado | sim | — |
| vistoria | `lib/plano_saida.py` | sim | executa | sim | import importlib; import subprocess; lib/bash_posix.py: import subprocess |
| vistoria | `lib/regua_texto.py` | não | puro, nao citado | não | — |
| vistoria | `lib/suite_congela.py` | sim | liberado | sim | — |
| visual | `hooks/bash_posix.py` | não | executa | sim | import subprocess |
| visual | `hooks/lar_fingido.py` | não | puro, nao citado | não | — |
| visual | `hooks/stop-anuncio-sem-acao.py` | sim | executa | sim | import subprocess; lib/bash_posix.py: import subprocess; hooks/bash_posix.py: import subprocess |
| visual | `lib/bash_posix.py` | não | executa | sim | import subprocess |
| visual | `lib/clareza.py` | sim | liberado | sim | — |
| visual | `lib/regua_audit.py` | não | executa | sim | import subprocess; lib/visual_page.py: import subprocess; lib/bash_posix.py: import subprocess; hooks/bash_posix.py: import subprocess |
| visual | `lib/regua_texto.py` | não | puro, nao citado | não | — |
| visual | `lib/visual_page.py` | sim | executa | sim | import subprocess; lib/bash_posix.py: import subprocess; hooks/bash_posix.py: import subprocess |
| visual | `server/visual_server.mjs` | sim | rede | sim | from 'node:http' |
