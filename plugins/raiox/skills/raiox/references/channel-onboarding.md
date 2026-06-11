# Onboarding de canal novo no RAIOX

Replicar = criar UM arquivo: `channels/<key>.yaml`. Nenhum `.py` é editado — se a análise exigir mudança de código para o canal funcionar, isso é bug de replicabilidade (reportar a Pedro, não contornar).

## 1 · Resolver o channel_id

A carteira do VIU vive na base Supabase do app Social (`influencers`/`platforms`; `platforms.external_id` = channel_id do YouTube). Acesso REST com a `SUPABASE_SERVICE_ROLE_KEY` lida em runtime de `/Users/pedroberaldo/PROGRAMACAO/VIU/VIUSTUDIO-TOOLS/apps/social/.env.local` — nunca expor nem copiar a key. Alternativa: pegar o channel_id direto da URL do canal.

## 2 · Escrever o YAML

Copie `channels/massini.yaml` como gabarito. Campos:

```yaml
channel_key: <key>              # slug curto, vira pasta data/<key>/
channel_id: UC...               # id real do canal
name: <Nome do Canal>
nicho: <futebol | comedy | ...>
entidade_ancora: <Palmeiras|...> # entidade central do conteúdo (vira stopword no textmining)

marcos:
  agency_start: YYYY-MM-DD      # quando o VIU assumiu (divide pre/pos em TODA análise)
  analysis_start: YYYY-MM-DD    # início do bloco "fase madura"

taxonomia:                      # regex declarativa; ordem importa, 1º match ganha
  rivais_classico: [...]        # adversários que contam como clássico
  emojis_assinatura: ["🚨"]     # emojis-assinatura do canal (flag urgencia)
  tipos:
    <TIPO>: [<aliases maiúsculos sem acento>]
  tipo_default: <TIPO-PADRÃO>
  competicoes:
    <Nome>: [<aliases>]

# privado (opcional — só se houver export manual do Studio)
studio_export_csv: "<path do CSV 'Dados da tabela'>"
studio_export_label: "<YYYY-MM-DD-descricao>"
studio_series_csv: "<path do 'Total.csv' (série diária)>"
studio_series_label: "<YYYY-MM-DD-serie-canal>"
```

A taxonomia é a parte que exige cabeça de domínio: levante os padrões de título do canal (amostra de ~50 títulos reais) ANTES de escrever os aliases. Valide com Pedro antes do primeiro `compute` — taxonomia é write-once (gravada como fact).

## 3 · Rodar e auditar

```
raiox catalog --channel <key> && raiox shorts --channel <key>
raiox facts --channel <key>
raiox compute --channel <key>
```

Auditoria mínima do primeiro run:
- `facts` stdout: total de vídeos bate com o canal real? join privado (se houver) fechou?
- Resíduo da taxonomia: % de vídeos com `residuo=true` alto (>20%) = taxonomia pobre, melhorar aliases antes de seguir.
- Degradações declaradas (`indisponivel` nos JSONs) são esperadas sem dados privados — relatar, nunca silenciar.
