# O que cada módulo exporta (data/<canal>/metrics/*.json)

Todos têm `_meta` (module, channel, generated_at). Fontes: **privado** = studio_export (subset top-N do export manual, enviesado pra cima — declarar); **público** = catálogo completo (view_count snapshot — declarar viés; cortes ≥90d onde houver pre×pos).

- **canal.json** — dims do canal (inscritos, views totais, nº vídeos, formatos). Gerado por `explore/00_canal.py`.
- **drivers.json** — descritivos + correlações por formato, modelos RF (random_state fixo) por alvo (visualizacoes/receita_brl/inscritos), mudanças de sinal entre formatos, spot_checks. Privado.
- **segmentacao.json** — split LIVE/VIDEO/SHORT (retenção/CTR/RPM medianos, Mann-Whitney), clustering KMeans com k por silhueta (curva exportada). Privado.
- **categoricos.json** — testes Kruskal/Mann-Whitney por tipo/competição/resultado/dia, público e privado, pre×pos com corte de idade. Misto.
- **textmining.json** — termos×CTR (lifts com n e p), sinais estruturais de título (emoji-assinatura, interrogação, número, caps, len), marcadores por formato. Privado + sinais no público.
- **funil.json** — etapas medianas por formato (impressões→CTR→views/impressão→retenção→watch), quadrantes CTR×impressões com cortes exportados, faixas de duração por quartis. Privado.
- **temporal.json** — safras anuais (público E privado, rotulados), YoY, série diária do canal (privada), monetização (pareto, RPM/CPM/CTR por ano), anomalias RF. Misto.
- **outlier.json** — score de outlier (resíduo RF em MAD) por formato no catálogo completo; over/under-performers, recorte pós-marco. Público.

Explorações (`data/<canal>/explore/*.json`, protótipo mas fonte legítima):
- **antes_depois.json** — cadência/mix/atraso/duração/horários pre×pos do marco.
- **safras.json** — safras semanais/mensais, pre×pos maduros (≥90d) com deltas exportados, regularidade semanal, trimestres pós.
- **likes_rate.json** — decomposição mix×taxa da queda de likes/1k, robustez à maturidade, likes absolutos.

## Validar prosa que cita explore/ + metrics/

O CLI aceita um diretório; pra citar das duas pastas, combine os conjuntos:

```python
from pathlib import Path
from raiox.validate import collect_valid_numbers, strip_html, validate_text
valid = collect_valid_numbers(Path('data/<canal>/metrics'), Path('benchmarks.yaml'))
valid |= collect_valid_numbers(Path('data/<canal>/explore'), None)
orphans = validate_text(strip_html(Path('<peça>.html').read_text()), valid)
# orphans == [] => aprovado
```

Regra de citação: número derivado (delta, razão, %) só pode ir pra prosa se o módulo exportou o derivado — recalcular na prosa REPROVA de propósito.
