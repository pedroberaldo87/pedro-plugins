<!-- FONTE DA VERDADE: _shared/r8-tiers.md — NÃO editar as cópias vendoradas
     (plugins/*/skills/*/references/r8-tiers.md). Edite aqui e rode
     scripts/sync-shared.sh. O --check falha (exit 1) se uma cópia divergir. -->

# Tier por etapa (R8) — contrato único dos motores `/sovai` e `/qa-loop`

Os dois motores (decompõe→executa→revisa do `/sovai`; revisa→planeja→conserta do
`/qa-loop`) usam **a mesma tabela de tier por etapa** e **os mesmos nomes de knob**.
Trocar o tier de uma etapa aqui vale pros dois — é um contrato, não duas listas.
Cada skill mantém, no próprio SKILL.md, só a coluna **"Onde no motor"** (como cada
tier se aplica ao motor dela); o resto desta tabela é comum e mora aqui.

| Etapa do fluxo | Modelo | Effort | Knob |
|---|---|---|---|
| Planejamento inicial e decomposição | Opus | `xhigh` | `decompose_model` |
| Coordenação rotineira dos agentes | Opus | `high` | `coordinate_model` |
| Execução das tarefas | Sonnet | `high` | `executor_model` |
| Operações mecânicas e bem delimitadas | Sonnet | `medium` | `mechanical_model` |
| Diagnóstico após falhas repetidas | Opus | `xhigh` | `diagnose_model` |
| Revisão final e integração | Opus | `xhigh` | `finalize_model` |

## Semântica dos knobs (genérica — vale pros dois motores)

- **`decompose_model`** (Opus `xhigh`) — rodada 1: planejamento inicial / decomposição do problema inteiro. O sweep mais pesado, uma vez.
- **`coordinate_model`** (Opus `high`) — rodadas 2+: coordenação rotineira, processa só o **delta** do feedback. Não é mais "decomposição inicial".
- **`executor_model`** (Sonnet `high`) — execução das tarefas, uma por vez (ou em paralelo quando há independência real). Tarefa padrão (`complexity` ausente ou `'standard'`).
- **`mechanical_model`** (Sonnet `medium`) — operação bem delimitada (renomear, mover arquivo, 1 config, 1 valor — sem julgamento amplo): `complexity: 'mechanical'`. Não precisa do julgamento caro.
- **`diagnose_model`** (Opus `xhigh`) — após **churn** (a mesma tarefa/função reaparece falhando por ≥ `churn_threshold` rodadas): investiga a **causa raiz**, não repete o remendo.
- **`finalize_model`** (Opus `xhigh`) — **confirm-pass dedicado** antes de declarar pronto/limpo: re-checa do zero e **não confia** no veredito mais barato (`coordinate_model`) da rodada que pareceu pronta.

## Regra de tier por rodada

- **Rodada 1** = `decompose_model` (Opus `xhigh`, planejamento inicial).
- **Rodadas 2+** = `coordinate_model` (Opus `high`, coordenação rotineira, só o delta).
- **CONFIRM** e **DIAGNOSE** são **sempre dedicados** (`finalize_model` / `diagnose_model`, Opus `xhigh`), independentemente da rodada — nunca herdam o tier mais barato da rodada que os disparou.
