---
name: raiox
description: Use when Pedro wants to run the RAIOX channel analysis — "roda o raiox", "/raiox", "analisa o canal X", "atualiza os números do massini", "onboarda o canal Y no raiox", "pergunta ao raio-x". Orchestrates the viu-raiox pipeline end-to-end for one channel - public fetch, fact store, lifetime export loader, gates, the diagnostic chapters, validated documents (peça/one-pager/planilha) and the raiox ask Q&A. Code-only numbers, ever.
---

# RAIOX — análise replicável de canal YouTube

## O que é

Motor de inteligência de canal do VIU Studio. Repo: `/Users/pedroberaldo/PROGRAMACAO/VIU/VIUSTUDIO-RAIOX` (pacote `viu-raiox`, venv `.venv`, CLI `raiox`). Cada canal é um YAML em `channels/<key>.yaml` — replicar a análise para outro canal = criar o YAML + responder o checklist de onboarding (abaixo), nunca editar `.py` (se precisar editar código pra canal novo, é bug de replicabilidade: reporte).

**Honesty Rule (inviolável):** todo número citável nasce como FATO JSON gerado por código (`explore/relatorio/<canal>/fatos/`, com ID e selo CONFIRMADO×INFERIDO); séries de gráfico nascem como CSV (`series/` + manifest). LLM nunca origina número — rotula taxonomia (write-once), redige e responde, sempre reprovável pelo `raiox validate` (número órfão, contradição de direção, gráfico divergente do CSV). Formato triplo LIVE/SHORT/VIDEO; antes×depois é correlação, nunca atribuição causal; top-500 do Studio é SUBSET (somas nunca representam o canal — G3).

## Checklist de onboarding de influenciador (Pedro responde 1× por canal)

REGRA DA METODOLOGIA: **o que se replica é a PERGUNTA, nunca a resposta** — a grade do Massini (pré/pós-jogo, M&M, Bom dia Massa) vale só para o Massini e jamais é template para outro canal.

1. **Quais são os programas/atrações da grade deste influenciador?** (nomes, dias, status)
2. **Existe marco/era?** (data em que o VIU assumiu; outros marcos relevantes)
3. **Quem são os rivais/clássicos?** (para a taxonomia de confrontos)
4. **Quais competições/eventos importam?** (e quais MOMENTOS — títulos, finais — para o benchmark)
5. **Quem são os pares comparáveis do setor?** (cesta do benchmark — pré-registrada e validada)
6. **Qual o modelo comercial com o VIU?** (fee? % de patrocínio? produção? — define as defesas)

As respostas viram blocos do YAML (`programas:`, `marcos:`, `taxonomia.rivais_classico`, `benchmark:`) — detalhe em `references/channel-onboarding.md`.

## Estado v0.2 (o que existe e roda — sessão 2026-06-11)

- Loader do export lifetime do Studio (49 colunas, 2 réguas de views, schema gate G6 com relatório).
- Gates executáveis: G3 cobertura, G9 reconciliação entre exports; G13 (benchmark externo) embutido no c8.
- Capítulos do diagnóstico c1-c8 + síntese → fatos JSON + séries CSV + `series_manifest.json` (anti-órfão).
- Documentos: defesas/prova de valor/roadmap (markdown) + peça 3 atos e one-pager (HTML com gráficos nascidos dos CSVs, contrato data-series/data-hash) + planilha-mestre XLSX.
- `raiox ask`: Q&A com busca por código e redator agnóstico (backends `claude-cli` e `api`).
- Fixture sintética nos testes: o motor roda ponta a ponta num canal que não é o Massini (env `RAIOX_CHANNELS_DIR`/`RAIOX_DATA_DIR`/`RAIOX_RELATORIO_DIR`).

## Execução (repo root, `.venv/bin/python -m raiox.cli` ou `raiox`)

```
raiox catalog  --channel <key>        # catálogo público completo (gasta quota; reusar raw <7d)
raiox shorts   --channel <key>        # probe de redirect p/ marcar SHORTs
raiox facts    --channel <key>        # fact store DuckDB
raiox lifetime --channel <key>        # export lifetime 49col + série diária (G6)
raiox gates    --channel <key>        # G3 cobertura + G9 reconciliação
raiox capitulo --channel <key>        # capítulos c1..c8 + sintese -> fatos/séries
raiox peca     --channel <key>        # peça 3 atos + one-pager (audit-out/)
raiox planilha --channel <key>        # planilha-mestre XLSX do manifest
raiox ask      --channel <key> "pergunta" [--backend claude-cli|api] [--mostrar-fatos]
raiox validate <arquivo> --metrics explore/relatorio/<key>/fatos \
               --series-dir explore/relatorio/<key>/series      # prosa E gráficos
raiox conformidade --channel <key>    # GATE do deck: jargão/rodapé/estrutura vs Constituição
.venv/bin/python -m pytest tests/ -q   # após qualquer mudança de código
```

Regras de operação:
- Anomalia no stdout (join não fecha, G6/G9 falham) = parar e investigar, nunca seguir.
- Capítulo 8 (benchmark) nasce DRAFT: cesta e momentos pré-registrados no YAML e validados com Pedro ANTES de qualquer conclusão ir para peça.
- Validações que dependem de Pedro não bloqueiam: computar provisório carimbado DRAFT, acumular perguntas autocontidas, entregar no final.
- Todo documento com número passa pelo `raiox validate` antes de chegar a Pedro; peça/one-pager também com `--series-dir`.
- **GATE OBRIGATÓRIO do deck (não opcional):** gerou/regenerou o deck (`raiox slides`) → ele PASSA pelo gate de conformidade antes de chegar a Pedro. Porta dura `raiox conformidade --channel <key>` (REPROVA jargão/rodapé ausente) **e** o loop multi-agente `Workflow({name: "slides-conformidade", args: {channel: "<key>"}})` (Opus revisa contra a Constituição → Opus planeja → Sonnet implementa só no motor de apresentação → Opus re-revisa → Opus adjudicator decide; assintótico, dois-motores hard-fail). NÃO usa nem mexe no qa-loop. Engine no projeto: `.claude/workflows/slides-conformidade.js`; doutrina em `.claude/docs/apresentacao.md › Cumprimento`.

## Cadência

Mensal por canal: re-fetch + lifetime (se houver export novo) + capitulo + peca (delta). Trimestral: revisar benchmark (2º snapshot da cesta mede a efemeridade de cada par).

## Referências (lazy-load)

- `references/channel-onboarding.md` — checklist + YAML completo de canal novo.
- `references/metrics-spec.md` — módulos legados (drivers/segmentacao/...) e como citar.
- OAuth/Analytics: `docs/OAUTH-SETUP.md` no repo viu-raiox.
