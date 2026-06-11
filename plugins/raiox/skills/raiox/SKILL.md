---
name: raiox
description: Use when Pedro wants to run the RAIOX channel analysis — "roda o raiox", "/raiox", "analisa o canal X", "atualiza os números do massini", "onboarda o canal Y no raiox". Orchestrates the viu-raiox pipeline end-to-end for one channel - public fetch, fact store, the 7 analysis modules, and orphan-number validation. v0 is the code-only rail (no LLM in the numbers, ever).
---

# RAIOX — análise replicável de canal YouTube

## O que é

Motor de inteligência de canal do VIU Studio. Repo: `/Users/pedroberaldo/PROGRAMACAO/VIU/VIUSTUDIO-RAIOX` (pacote `viu-raiox`, venv `.venv`, CLI `raiox`). Cada canal é um YAML em `channels/<key>.yaml` — replicar a análise para outro canal = criar o YAML, nunca editar `.py` (se precisar editar código pra um canal novo, isso é bug de replicabilidade: reporte).

**Honesty Rule (inviolável):** todo número citável nasce em JSON gerado por código (`data/<canal>/metrics/`, `data/<canal>/explore/`). LLM nunca origina número — só seleciona e narra. `raiox validate` reprova prosa com número órfão. Formato triplo LIVE/SHORT/VIDEO em toda análise. Antes×depois é **correlação temporal, nunca atribuição causal**. `view_count` público é snapshot — declarar viés; cortes de maturidade ≥90d onde comparar períodos.

## Estado v0 (o que existe e roda)

- Trilho 100% código: fetch público → facts → 7 módulos (`drivers`, `segmentacao`, `categoricos`, `textmining`, `funil`, `temporal`, `outlier`) → validate. 48 testes (paridade v1 inclusa).
- Dados privados: via export manual do Studio (CSV), apontado no YAML (`studio_export_csv`, `studio_series_csv`). OAuth Analytics está montado mas **bloqueado por acesso** (ver `docs/OAUTH-SETUP.md` no repo).
- **Fase C pendente** (não prometa): curadoria LLM com subagentes-lente, templates dos 3 outputs (posicionamento/case/relatório recorrente com delta). A peça de posicionamento existente (`audit-out/massini/2026-06-11/posicionamento.html`) é artefato manual v0.1, não template.

## Execução

Todos os comandos a partir do repo root, com `.venv/bin/python -m raiox.cli` (ou `raiox` se instalado).

### Passo 1 — Resolver o canal
Argumento do usuário → `channel_key` (ex.: "massini"). Confira que `channels/<key>.yaml` existe. Se não existir, é **onboarding**: siga `references/channel-onboarding.md` e valide com Pedro a taxonomia antes de rodar.

### Passo 2 — Fetch (público, gasta quota)
Reusar `data/<canal>/raw/<data>/` mais recente por padrão. Só re-fetch se Pedro pedir números atualizados ou se o raw tiver >7 dias e a análise for de entrega:
```
raiox catalog --channel <key>     # catálogo completo (Data API, key do Social lida em runtime)
raiox shorts  --channel <key>     # probe de redirect p/ marcar SHORTs
```

### Passo 3 — Fact store
```
raiox facts --channel <key>
```
Confira o stdout: nº de vídeos, join export×catálogo (se houver CSV privado), divergência da heurística. Anomalia = parar e investigar, não seguir.

### Passo 4 — Módulos
```
raiox compute --channel <key>                      # todos os 7
raiox compute --channel <key> --modules funil      # ou subset
```
Saída: `data/<canal>/metrics/*.json`. Módulo com dado indisponível **declara** (`indisponivel`) — nunca silencia; reporte isso a Pedro.

### Passo 5 — Validação de qualquer prosa/peça
Toda prosa ou HTML com números do canal passa pelo validador antes de ir a Pedro:
```
raiox validate <arquivo> --metrics data/<canal>/metrics --benchmarks benchmarks.yaml
```
Números de `explore/` também são fonte legítima — se citar, validar com as duas pastas (ver bloco em `references/metrics-spec.md`).

### Passo 6 — Testes (após qualquer mudança de código)
```
.venv/bin/python -m pytest tests/ -q
```

## Cadência

Default: mensal por canal (re-fetch + compute + leitura dos deltas). Trimestral: revisar `benchmarks.yaml` (fontes externas datadas, com rótulo de confiança — baixa nunca vai pra peça sem rótulo).

## Referências (lazy-load)

- `references/channel-onboarding.md` — criar `channels/<key>.yaml` pra canal novo (Task 8 do plano).
- `references/metrics-spec.md` — o que cada módulo exporta e como citar.
- OAuth/Analytics: `docs/OAUTH-SETUP.md` **no repo viu-raiox** (roteiro de gerência de brand account).
